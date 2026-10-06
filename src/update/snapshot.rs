//! 스냅샷 · 백업 · 파일 단위 복원(설계 AUTO-UPDATE-118 §3-5 · 1R BLOCK 4·10·12 · 3R 신규 BLOCK 4 · MA3 · 세대 2).
//!
//! - 백업 = 뿌리마다 **「전체 − 명시 제외」**([`EXCLUDE`]) 파일 사본 + `MANIFEST.sha256`(파일별 sha256·크기). 목록을 모르는 새
//!   DB·JSON·WAL 은 자동으로 포함된다(모르는 것이 빠지는 일 0 · fail-safe).
//! - 사본 쓰기 = 같은 폴더 임시 파일 → fsync → rename → 부모 폴더 fsync(📌12′ ③) · 끝나면 사본 **전부를 다시 읽어** 대조하고
//!   매니페스트 자체의 sha256 을 돌려준다(저널 `snapshot_manifest_sha256` · S8 완료 조건).
//! - 복원 = 폴더째 rename 0 · 파일마다 [`plan_restore`] 표(같음 = 건너뜀 · 다름/없음 = 원자 교체 · 매니페스트 밖 보호 경로 = 무접촉 ·
//!   매니페스트 밖 그 밖 = 격리(지우지 않음)) → 전수 재대조.
//! - ★설계와 다른 점(정직 · HANDOFF-U2 §2): 설계 표는 팩·사용자 트리를 tar(.tar.gz)로 적었으나, 복원 규칙(§3-5 「파일 단위」)이
//!   매니페스트 기반이라 세 뿌리 모두 같은 「파일 사본 + 매니페스트」 꼴로 둔다(풀기 단계 0 · 같은 검증·복원 함수 하나).

use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};
use std::io::{Read, Write};
use std::path::{Path, PathBuf};

pub const MANIFEST_FILE: &str = "MANIFEST.sha256";
pub const FILES_DIR: &str = "files";

/// 제외 규칙 1개.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Rule {
    /// 뿌리 바로 아래 이름(파일·폴더) 정확 일치.
    Top(&'static str),
    /// 뿌리 바로 아래 이름의 접두(예: `transcripts.db` → `-wal`·`-shm` 함께).
    TopPrefix(&'static str),
    /// 어느 깊이든 경로 성분 이름 정확 일치(폴더면 그 아래 전부).
    AnyComponent(&'static str),
    /// 파일 이름 접미(어느 깊이든).
    Suffix(&'static str),
}

/// ★상태 폴더 「명시 제외」 — 코드 상수 1곳(설계 §3-5 · 이름 추가 = 코드 리뷰 사안). 각 항목 = 「갱신이 쓰지 않는다 + 되돌리면 사용자
/// 기록이 사라진다」 근거. 실측 = 이 맥 `~/.local/state/cys` 39항목 · 1,637,320 KiB(2026-10-06 20:2x `du -sk`) 중 아래 제외분
/// ≈ 1.36 GiB(transcripts.db 1,334,472 + -wal 27,652 + -shm 64 · cysd.log 31,580 · phoenix 576 · *.log 수 KiB) → 제외 뒤 ≈ 0.27 GiB.
pub const EXCLUDE: &[(Rule, &str)] = &[
    (Rule::TopPrefix("transcripts.db"), "대화 기록(recall 원장) — 갱신이 쓰지 않고 되돌리면 그 사이 대화가 사라진다 · 실측 1.3 GiB"),
    (Rule::Top("phoenix"), "phoenix 저장분(좌석 부활 사본) — 되돌리면 정비 모드 뒤 좌석 부활 근거가 과거로 간다"),
    (Rule::Top("phoenix-embed"), "phoenix 저장분 짝"),
    (Rule::Top("claude"), "Claude 대화 기록·계정 폴더 — 갱신이 쓰지 않는다"),
    (Rule::Top("transcripts"), "대화 기록 폴더(있으면)"),
    (Rule::Top("recall"), "recall 원장(있으면)"),
    (Rule::Top("update"), "갱신 자신의 폴더 — 저널·보류 로그·잠금 = 스냅샷 밖 원장(§3-3 · 되돌리면 hold: 항목이 과거로 간다)"),
    (Rule::AnyComponent("logs"), "로그 폴더 — 되돌리면 갱신 동안의 기록이 사라진다"),
    (Rule::Suffix(".log"), "로그 파일 — 같음"),
    (Rule::Top("cys.sock"), "소켓(정규 파일 아님 · 데몬이 만든다)"),
];

/// `rel` = `/` 구분 상대 경로.
pub fn is_excluded(rel: &str) -> bool {
    excluded_by(EXCLUDE, rel)
}

pub fn excluded_by(rules: &[(Rule, &str)], rel: &str) -> bool {
    let comps: Vec<&str> = rel.split('/').filter(|c| !c.is_empty()).collect();
    let Some(first) = comps.first() else { return true };
    let last = comps.last().copied().unwrap_or_default();
    rules.iter().any(|(r, _)| match r {
        Rule::Top(n) => first == n,
        Rule::TopPrefix(p) => first.starts_with(p),
        Rule::AnyComponent(n) => comps.iter().any(|c| c == n),
        Rule::Suffix(s) => last.ends_with(s),
    })
}

pub fn sha256_file(p: &Path) -> Result<(String, u64), String> {
    let mut f = std::fs::File::open(p).map_err(|e| format!("{}: {e}", p.display()))?;
    let mut h = Sha256::new();
    let mut buf = vec![0u8; 1 << 16];
    let mut n = 0u64;
    loop {
        let k = f.read(&mut buf).map_err(|e| format!("{}: {e}", p.display()))?;
        if k == 0 {
            break;
        }
        h.update(&buf[..k]);
        n += k as u64;
    }
    Ok((format!("{:x}", h.finalize()), n))
}

/// 정규 파일 목록(상대 경로 정렬). 심링크·소켓·장치는 따라가지도 싣지도 않는다(바깥을 가리키는 링크로 남의 파일을 덮는 길 0).
/// `filter` 가 false 인 경로는 뺀다(폴더면 그 아래 전부).
pub fn list_files(root: &Path, filter: &dyn Fn(&str) -> bool) -> Result<Vec<String>, String> {
    let mut out = Vec::new();
    if !root.exists() {
        return Ok(out);
    }
    let mut stack = vec![(root.to_path_buf(), String::new())];
    while let Some((dir, prefix)) = stack.pop() {
        let rd = std::fs::read_dir(&dir).map_err(|e| format!("{}: {e}", dir.display()))?;
        for ent in rd {
            let ent = ent.map_err(|e| e.to_string())?;
            let name = ent.file_name().to_string_lossy().to_string();
            let rel = if prefix.is_empty() { name.clone() } else { format!("{prefix}/{name}") };
            if !filter(&rel) {
                continue;
            }
            let ft = ent.file_type().map_err(|e| e.to_string())?;
            if ft.is_dir() {
                stack.push((ent.path(), rel));
            } else if ft.is_file() {
                out.push(rel);
            }
        }
    }
    out.sort();
    Ok(out)
}

/// ★2판(codex 1R C5): 스냅샷 항목 목록 = 정규 파일 **+ 심링크**(따라가지 않고 링크 자체 · 「전체 − 제외」 에서 조용히 빠지던 것).
/// 소켓·장치는 싣지 않는다. 폴더는 실 폴더만 내려간다(링크된 폴더 = 링크 항목 하나).
pub fn list_entries(root: &Path, filter: &dyn Fn(&str) -> bool) -> Result<Vec<String>, String> {
    let mut out = Vec::new();
    if !root.exists() {
        return Ok(out);
    }
    let mut stack = vec![(root.to_path_buf(), String::new())];
    while let Some((dir, prefix)) = stack.pop() {
        let rd = std::fs::read_dir(&dir).map_err(|e| format!("{}: {e}", dir.display()))?;
        for ent in rd {
            let ent = ent.map_err(|e| e.to_string())?;
            let name = ent.file_name().to_string_lossy().to_string();
            let rel = if prefix.is_empty() { name.clone() } else { format!("{prefix}/{name}") };
            if !filter(&rel) {
                continue;
            }
            let ft = ent.file_type().map_err(|e| e.to_string())?;
            if ft.is_dir() {
                stack.push((ent.path(), rel));
            } else if ft.is_file() || ft.is_symlink() {
                out.push(rel);
            }
        }
    }
    out.sort();
    Ok(out)
}

/// 원자 파일 쓰기(같은 폴더 임시 → fsync → rename → 부모 fsync). ★2판 C5: 원본 권한 비트를 옮기지 못하면 Err(보존 실패 = 실패).
pub fn durable_copy(src: &Path, dst: &Path) -> Result<(String, u64), String> {
    let parent = dst.parent().ok_or("부모 없음")?;
    std::fs::create_dir_all(parent).map_err(|e| format!("{}: {e}", parent.display()))?;
    let tmp = parent.join(format!(".{}.cys-tmp", dst.file_name().map(|n| n.to_string_lossy().to_string()).unwrap_or_default()));
    let mut r = std::fs::File::open(src).map_err(|e| format!("{}: {e}", src.display()))?;
    let mut w = std::fs::File::create(&tmp).map_err(|e| format!("{}: {e}", tmp.display()))?;
    let mut h = Sha256::new();
    let mut buf = vec![0u8; 1 << 16];
    let mut n = 0u64;
    loop {
        let k = r.read(&mut buf).map_err(|e| e.to_string())?;
        if k == 0 {
            break;
        }
        h.update(&buf[..k]);
        w.write_all(&buf[..k]).map_err(|e| format!("{}: {e}", tmp.display()))?;
        n += k as u64;
    }
    w.sync_all().map_err(|e| format!("fsync {}: {e}", tmp.display()))?;
    drop(w);
    let md = std::fs::metadata(src).map_err(|e| format!("{}: {e}", src.display()))?;
    if let Err(e) = std::fs::set_permissions(&tmp, md.permissions()) {
        let _ = std::fs::remove_file(&tmp);
        return Err(format!("권한 보존 {}: {e}", dst.display()));
    }
    std::fs::rename(&tmp, dst).map_err(|e| format!("rename {}: {e}", dst.display()))?;
    super::journal::sync_dir(parent)?;
    Ok((format!("{:x}", h.finalize()), n))
}

/// 항목 종류(★2판 C5).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Kind {
    File,
    Link,
}

/// 매니페스트 항목: sha256(파일 = 내용 · 링크 = 링크 대상 경로 바이트) · 크기 · 종류 · 권한 비트(유닉스 `mode & 0o7777` · 링크·윈 = 0).
/// 소유권(uid)은 싣지 않는다 — 백업·복원 모두 같은 사용자 프로세스가 자기 폴더에 쓰므로 새로 만든 파일의 소유자는 늘 그 사용자다.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Entry {
    pub sha: String,
    pub size: u64,
    pub kind: Kind,
    pub mode: u32,
}

/// 매니페스트 = 상대 경로 → 항목.
pub type Manifest = BTreeMap<String, Entry>;

/// 한 줄 = `<sha>  <크기>  <f|l><8진 권한>  <경로>`.
pub fn render_manifest(m: &Manifest) -> String {
    m.iter()
        .map(|(p, e)| format!("{}  {}  {}{:o}  {p}\n", e.sha, e.size, if e.kind == Kind::Link { 'l' } else { 'f' }, e.mode))
        .collect()
}

pub fn parse_manifest(text: &str) -> Result<Manifest, String> {
    let mut m = Manifest::new();
    for (i, line) in text.lines().enumerate() {
        let mut it = line.splitn(4, "  ");
        let (Some(s), Some(n), Some(km), Some(p)) = (it.next(), it.next(), it.next(), it.next()) else {
            return Err(format!("매니페스트 {}번째 줄 형식", i + 1));
        };
        let n: u64 = n.parse().map_err(|_| format!("매니페스트 {}번째 줄 크기", i + 1))?;
        let kind = match km.as_bytes().first() {
            Some(b'f') => Kind::File,
            Some(b'l') => Kind::Link,
            _ => return Err(format!("매니페스트 {}번째 줄 종류", i + 1)),
        };
        let mode = u32::from_str_radix(&km[1..], 8).map_err(|_| format!("매니페스트 {}번째 줄 권한", i + 1))?;
        if s.len() != 64 || !s.bytes().all(|b| b.is_ascii_hexdigit()) || p.is_empty() || p.split('/').any(|c| c == ".." || c.is_empty()) || mode > 0o7777 {
            return Err(format!("매니페스트 {}번째 줄 값", i + 1));
        }
        if m.insert(p.to_string(), Entry { sha: s.to_string(), size: n, kind, mode }).is_some() {
            return Err(format!("매니페스트 경로 중복 {p}"));
        }
    }
    Ok(m)
}

fn sha_hex(b: &[u8]) -> String {
    format!("{:x}", Sha256::digest(b))
}

fn mode_of(md: &std::fs::Metadata) -> u32 {
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        md.permissions().mode() & 0o7777
    }
    #[cfg(not(unix))]
    {
        let _ = md;
        0
    }
}

fn link_target_bytes(p: &Path) -> Result<Vec<u8>, String> {
    let t = std::fs::read_link(p).map_err(|e| format!("{}: {e}", p.display()))?;
    Ok(t.to_string_lossy().as_bytes().to_vec())
}

/// 지금 경로의 항목 실측(lstat · 링크를 따라가지 않는다). 없음 = Ok(None).
pub fn observe(p: &Path) -> Result<Option<Entry>, String> {
    let md = match std::fs::symlink_metadata(p) {
        Ok(m) => m,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(None),
        Err(e) => return Err(format!("{}: {e}", p.display())),
    };
    if md.file_type().is_symlink() {
        let t = link_target_bytes(p)?;
        return Ok(Some(Entry { sha: sha_hex(&t), size: t.len() as u64, kind: Kind::Link, mode: 0 }));
    }
    if !md.is_file() {
        return Ok(Some(Entry { sha: String::new(), size: 0, kind: Kind::File, mode: u32::MAX }));
    }
    let (sha, size) = sha256_file(p)?;
    Ok(Some(Entry { sha, size, kind: Kind::File, mode: mode_of(&md) }))
}

/// 링크를 원자적으로 만든다(같은 폴더 임시 링크 → rename · 기존 파일·링크를 대체 · 링크를 따라 쓰지 않는다).
fn durable_symlink(target: &Path, dst: &Path) -> Result<(), String> {
    let parent = dst.parent().ok_or("부모 없음")?;
    std::fs::create_dir_all(parent).map_err(|e| format!("{}: {e}", parent.display()))?;
    let tmp = parent.join(format!(".{}.cys-tmpl", dst.file_name().map(|n| n.to_string_lossy().to_string()).unwrap_or_default()));
    let _ = std::fs::remove_file(&tmp);
    #[cfg(unix)]
    std::os::unix::fs::symlink(target, &tmp).map_err(|e| format!("링크 {}: {e}", dst.display()))?;
    #[cfg(windows)]
    std::os::windows::fs::symlink_file(target, &tmp).map_err(|e| format!("링크(윈) {}: {e}", dst.display()))?;
    std::fs::rename(&tmp, dst).map_err(|e| format!("rename {}: {e}", dst.display()))?;
    super::journal::sync_dir(parent)
}

/// 항목 하나를 `src` → `dst` 로 옮겨 쓰고(파일 = 내용+권한 · 링크 = 같은 대상) 기대 항목과 실측이 같은지 확인한다.
fn put_entry(src: &Path, dst: &Path, want: &Entry) -> Result<(), String> {
    match want.kind {
        Kind::File => {
            durable_copy(src, dst)?;
        }
        Kind::Link => {
            let t = std::fs::read_link(src).map_err(|e| format!("{}: {e}", src.display()))?;
            durable_symlink(&t, dst)?;
        }
    }
    match observe(dst)? {
        Some(got) if got == *want => Ok(()),
        got => Err(format!("보존 불일치 {} (기대 {want:?} · 실측 {got:?})", dst.display())),
    }
}

/// 뿌리 하나 백업: `src` 의 「전체 − 제외」(`filter` true 만 · 파일+링크) → `dst/files/…` + `dst/MANIFEST.sha256` → **전수 재독 대조** →
/// 매니페스트 sha256. 데몬이 선 상태에서만 부른다(S7 뒤 · 한 시점). ★2판 C5: 링크·권한 비트까지 싣고 보존 실패 = Err(S8 실패).
pub fn take(src: &Path, dst: &Path, filter: &dyn Fn(&str) -> bool) -> Result<String, String> {
    if dst.join(MANIFEST_FILE).exists() {
        return Err(format!("이미 있는 스냅샷 {} — 덮지 않는다", dst.display()));
    }
    let files = list_entries(src, filter)?;
    let mut m = Manifest::new();
    for rel in &files {
        let Some(e) = observe(&src.join(rel))? else { continue }; // 그사이 사라짐(데몬 정지 뒤라 드묾)
        if e.mode == u32::MAX {
            continue;
        }
        put_entry(&src.join(rel), &dst.join(FILES_DIR).join(rel), &e)?;
        m.insert(rel.clone(), e);
    }
    std::fs::create_dir_all(dst).map_err(|e| e.to_string())?;
    let text = render_manifest(&m);
    super::journal::durable_write(&dst.join(MANIFEST_FILE), text.as_bytes())?;
    verify(dst)
}

/// 백업 검증(BLOCK 12 · ★2판 C5): 매니페스트를 읽고 사본 **전부를 다시 읽어**(lstat · 링크·권한 포함) 대조 → 매니페스트 sha256.
pub fn verify(dst: &Path) -> Result<String, String> {
    let text = std::fs::read_to_string(dst.join(MANIFEST_FILE)).map_err(|e| format!("매니페스트 읽기: {e}"))?;
    let m = parse_manifest(&text)?;
    for (rel, want) in &m {
        if observe(&dst.join(FILES_DIR).join(rel))?.as_ref() != Some(want) {
            return Err(format!("백업 불일치 {rel}"));
        }
    }
    Ok(sha_hex(text.as_bytes()))
}

/// ★2판(codex 1R C6): 재계산한 매니페스트 sha256 과 저널 고정값의 상수시간 비교(길이 다름 = 거짓).
pub fn digest_eq(a: &str, b: &str) -> bool {
    a.len() == b.len() && a.bytes().zip(b.bytes()).fold(0u8, |acc, (x, y)| acc | (x ^ y)) == 0
}

/// 복원 동작(§3-5 표).
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Action {
    /// 매니페스트에 있고 sha256 같음 — 건너뜀(멱등).
    Keep(String),
    /// 매니페스트에 있고 다르거나 없음 — 스냅샷 사본으로 원자 교체.
    Replace(String),
    /// 매니페스트 밖 · 보호 경로 — 손대지 않는다.
    Protected(String),
    /// 매니페스트 밖 · 보호 아님(새 판이 만든 상태 파일) — 지우지 않고 격리.
    Quarantine(String),
}

/// 복원 계획(순수): `live` = 지금 그 뿌리의 항목(없으면 키 없음 · 종류·권한 포함 — 내용이 같아도 권한·종류가 다르면 교체) ·
/// `protected` = 보호 경로 판정(ⓐ 새·옛 페이로드 매니페스트 · ⓑ EXCLUDE · ⓒ 갱신 원장).
pub fn plan_restore(snap: &Manifest, live: &BTreeMap<String, Entry>, protected: &dyn Fn(&str) -> bool) -> Vec<Action> {
    let mut out = Vec::new();
    for (rel, want) in snap {
        match live.get(rel) {
            Some(l) if l == want => out.push(Action::Keep(rel.clone())),
            // ★4판(N3′ 새 판 재구성): 보호 경로는 백업에 있어도 덮지 않는다(기존 호출자는 보호 경로를 백업에 담지 않으므로 무변화)
            _ if protected(rel) => out.push(Action::Protected(rel.clone())),
            _ => out.push(Action::Replace(rel.clone())),
        }
    }
    for rel in live.keys().filter(|r| !snap.contains_key(*r)) {
        if protected(rel) {
            out.push(Action::Protected(rel.clone()));
        } else if super::mutant("U2-QUAR") {
            out.push(Action::Keep(rel.clone()));
        } else {
            out.push(Action::Quarantine(rel.clone()));
        }
    }
    out
}

/// ★3판(Fable 2R N3): 복원 계획만(백업 재대조 → 표) — 바꾸는 것 0. 「일치하면 손대지 않는다」 판정용.
pub fn diff(live_root: &Path, snap_dir: &Path, protected: &dyn Fn(&str) -> bool) -> Result<Vec<Action>, String> {
    diff_in(live_root, snap_dir, &|_| true, protected)
}

/// [`diff`] 의 범위 한정판(★4판 Fable 3R n3): `scope` 밖(폴더면 그 아래 전체)은 읽지도 해시하지도 않는다 — 스냅샷이 범위 안만 담았을 때
/// (`~/.cys` 의 팩·사용자 트리) 갱신 폴더 백업·대화 기록까지 해시하던 낭비 제거. 범위 밖 = 보호와 같은 결과(무접촉).
pub fn diff_in(live_root: &Path, snap_dir: &Path, scope: &dyn Fn(&str) -> bool, protected: &dyn Fn(&str) -> bool) -> Result<Vec<Action>, String> {
    verify(snap_dir).map_err(|e| format!("rollback_blocked: {e}"))?;
    let snap = parse_manifest(&std::fs::read_to_string(snap_dir.join(MANIFEST_FILE)).map_err(|e| e.to_string())?)?;
    let mut live = BTreeMap::new();
    for rel in list_entries(live_root, scope)? {
        if let Some(e) = observe(&live_root.join(&rel))? {
            live.insert(rel.clone(), e);
        }
    }
    Ok(plan_restore(&snap, &live, protected))
}

/// 뿌리 하나 복원: 백업을 먼저 재대조(불일치 = 덮지 않고 Err = `update.rollback_blocked` · ★2판 C6: `expect` = 저널이 고정한 매니페스트
/// sha256 — 다르면 같은 Err) → 표 적용 → 매니페스트 전수 재대조(링크·권한 포함).
pub fn restore(
    live_root: &Path,
    snap_dir: &Path,
    quarantine_root: &Path,
    protected: &dyn Fn(&str) -> bool,
    expect: Option<&str>,
) -> Result<Vec<Action>, String> {
    restore_in(live_root, snap_dir, quarantine_root, &|_| true, protected, expect)
}

/// [`restore`] 의 범위 한정판(★4판 n3 — [`diff_in`] 과 같은 `scope`).
pub fn restore_in(
    live_root: &Path,
    snap_dir: &Path,
    quarantine_root: &Path,
    scope: &dyn Fn(&str) -> bool,
    protected: &dyn Fn(&str) -> bool,
    expect: Option<&str>,
) -> Result<Vec<Action>, String> {
    let got = verify(snap_dir).map_err(|e| format!("rollback_blocked: {e}"))?;
    if let Some(want) = expect {
        if !digest_eq(&got, want) {
            return Err("rollback_blocked: 매니페스트 sha256 ≠ 저널 고정값".into());
        }
    }
    let snap = parse_manifest(&std::fs::read_to_string(snap_dir.join(MANIFEST_FILE)).map_err(|e| e.to_string())?)?;
    let mut live = BTreeMap::new();
    for rel in list_entries(live_root, scope)? {
        if let Some(e) = observe(&live_root.join(&rel))? {
            live.insert(rel.clone(), e);
        }
    }
    let plan = plan_restore(&snap, &live, protected);
    for a in &plan {
        match a {
            Action::Replace(rel) => {
                put_entry(&snap_dir.join(FILES_DIR).join(rel), &live_root.join(rel), &snap[rel])?;
            }
            Action::Quarantine(rel) => {
                let to = quarantine_root.join(rel);
                std::fs::create_dir_all(to.parent().ok_or("부모 없음")?).map_err(|e| e.to_string())?;
                if std::fs::rename(live_root.join(rel), &to).is_err() {
                    // 다른 볼륨 = 복사 후 지움(격리는 되돌릴 수 있어야 하므로 사본이 먼저 durable)
                    let e = observe(&live_root.join(rel))?.ok_or("격리 대상 사라짐")?;
                    put_entry(&live_root.join(rel), &to, &e)?;
                    std::fs::remove_file(live_root.join(rel)).map_err(|e| e.to_string())?;
                }
            }
            Action::Keep(_) | Action::Protected(_) => {}
        }
    }
    for (rel, want) in snap.iter().filter(|(rel, _)| !protected(rel)) {
        if observe(&live_root.join(rel))?.as_ref() != Some(want) {
            return Err(format!("복원 뒤 불일치 {rel}"));
        }
    }
    Ok(plan)
}

/// 세대 정리(📌10 · 세대 2): `backup_root` 아래 스냅샷 폴더 이름 `<from_seq>-<txn>` 중 **검증을 마친** 것이 `keep` 개를 넘으면 가장
/// 낡은 것부터 지운다. `fresh_verified` = 방금 만든 새 백업이 검증을 마쳤는가 — 아니면 옛 세대를 하나도 지우지 않는다.
pub fn prune_plan(names: &[String], keep: usize, fresh_verified: bool, never: &BTreeSet<String>) -> Vec<String> {
    if !fresh_verified {
        return Vec::new();
    }
    let mut v: Vec<(u64, &String)> = names
        .iter()
        .filter_map(|n| n.split_once('-').and_then(|(s, _)| s.parse::<u64>().ok()).map(|s| (s, n)))
        .collect();
    v.sort();
    let excess = v.len().saturating_sub(keep);
    v.into_iter().take(excess).map(|(_, n)| n.clone()).filter(|n| !never.contains(n)).collect()
}

/// N7 공간식(MA3): 자산 + `max_unpacked` + 직전 실측 백업량(첫 회 = 대상 크기 합 실측) + 복원 여유(`max_unpacked` 한 번 더) + 예약 2 GiB.
pub const RESERVE_BYTES: u64 = 2 * 1024 * 1024 * 1024;
pub fn space_needed(asset: u64, max_unpacked: u64, backup_estimate: u64) -> u64 {
    asset.saturating_add(max_unpacked).saturating_add(backup_estimate).saturating_add(max_unpacked).saturating_add(RESERVE_BYTES)
}

/// 백업 예상량 = `filter` 를 통과하는 정규 파일 크기 합(첫 회 실측).
pub fn estimate(root: &Path, filter: &dyn Fn(&str) -> bool) -> Result<u64, String> {
    let mut sum = 0u64;
    for rel in list_entries(root, filter)? {
        sum = sum.saturating_add(std::fs::symlink_metadata(root.join(&rel)).map(|m| m.len()).unwrap_or(0));
    }
    Ok(sum)
}

/// 여유 공간(바이트) — 판정 불가 = None(N7 = 보류).
pub fn free_space(path: &Path) -> Option<u64> {
    #[cfg(unix)]
    {
        use std::os::unix::ffi::OsStrExt;
        let c = std::ffi::CString::new(path.as_os_str().as_bytes()).ok()?;
        // SAFETY: 유효한 NUL 종단 경로 · 출력 구조체는 스택.
        let mut s: libc::statvfs = unsafe { std::mem::zeroed() };
        if unsafe { libc::statvfs(c.as_ptr(), &mut s) } != 0 {
            return None;
        }
        Some((s.f_bavail as u64).saturating_mul(s.f_frsize as u64))
    }
    #[cfg(windows)]
    {
        use std::os::windows::ffi::OsStrExt;
        use windows_sys::Win32::Storage::FileSystem::GetDiskFreeSpaceExW;
        let w: Vec<u16> = path.as_os_str().encode_wide().chain(std::iter::once(0)).collect();
        let mut avail: u64 = 0;
        // SAFETY: NUL 종단 경로 · 출력 포인터는 지역 변수.
        let ok = unsafe { GetDiskFreeSpaceExW(w.as_ptr(), &mut avail, std::ptr::null_mut(), std::ptr::null_mut()) };
        if ok == 0 {
            None
        } else {
            Some(avail)
        }
    }
}

/// 스냅샷 폴더 이름(세대 정렬 키 = 출발 seq).
pub fn snapshot_name(from_seq: u64, txn_id: &str) -> String {
    format!("{from_seq}-{txn_id}")
}

pub fn backup_root(update_dir: &Path) -> PathBuf {
    update_dir.join("backup")
}

pub fn quarantine_dir(update_dir: &Path, txn_id: &str) -> PathBuf {
    update_dir.join("rb-quarantine").join(txn_id)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn tmp(tag: &str) -> PathBuf {
        let d = std::env::temp_dir().join(format!("cys-u2-snap-{tag}-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&d);
        std::fs::create_dir_all(&d).unwrap();
        d
    }
    fn put(root: &Path, rel: &str, body: &str) {
        let p = root.join(rel);
        std::fs::create_dir_all(p.parent().unwrap()).unwrap();
        std::fs::write(p, body).unwrap();
    }

    #[test]
    fn exclude_rules_cover_measured_state_entries_and_unknown_files_are_included() {
        for x in ["transcripts.db", "transcripts.db-wal", "transcripts.db-shm", "cysd.log", "phoenix/a", "update/journal.json", "x/logs/y", "boot-supervisor.log", "cys.sock"] {
            assert!(is_excluded(x), "{x}");
        }
        // 목록 밖의 새 DB·WAL·JSON = 자동 포함(fail-safe)
        for x in ["analytics.db", "analytics.db-wal", "queue-state.json", "brand-new.db-wal", "schedule_state.json", "office-bridge/bin"] {
            assert!(!is_excluded(x), "{x}");
        }
        // 각 항목에 근거가 있다(빈 사유 0)
        assert!(EXCLUDE.iter().all(|(_, why)| !why.trim().is_empty()));
    }

    #[test]
    fn take_verify_restore_file_level_table() {
        let d = tmp("tvr");
        let live = d.join("live");
        put(&live, "a.json", "A");
        put(&live, "db/x.db-wal", "W");
        put(&live, "cysd.log", "L0");
        put(&live, "update/journal.json", "J0");
        let snap = d.join("snap");
        let f = |r: &str| !is_excluded(r);
        let msha = take(&live, &snap, &f).unwrap();
        assert_eq!(verify(&snap).unwrap(), msha);
        let m = parse_manifest(&std::fs::read_to_string(snap.join(MANIFEST_FILE)).unwrap()).unwrap();
        assert_eq!(m.keys().cloned().collect::<Vec<_>>(), vec!["a.json", "db/x.db-wal"]);
        // 새 판이 바꾸고 만든 것
        put(&live, "a.json", "A2");
        std::fs::remove_file(live.join("db/x.db-wal")).unwrap();
        put(&live, "new-state.json", "N");
        put(&live, "cysd.log", "L1");
        put(&live, "update/journal.json", "J1");
        let prot = |r: &str| is_excluded(r);
        let q = d.join("q");
        let plan = restore(&live, &snap, &q, &prot, None).unwrap();
        assert!(plan.contains(&Action::Replace("a.json".into())));
        assert!(plan.contains(&Action::Replace("db/x.db-wal".into())));
        assert!(plan.contains(&Action::Quarantine("new-state.json".into())));
        assert!(plan.contains(&Action::Protected("cysd.log".into())));
        assert_eq!(std::fs::read_to_string(live.join("a.json")).unwrap(), "A");
        assert_eq!(std::fs::read_to_string(live.join("db/x.db-wal")).unwrap(), "W");
        assert_eq!(std::fs::read_to_string(live.join("cysd.log")).unwrap(), "L1", "보호 경로 무접촉");
        assert_eq!(std::fs::read_to_string(live.join("update/journal.json")).unwrap(), "J1", "원장 무접촉");
        assert!(!live.join("new-state.json").exists());
        assert_eq!(std::fs::read_to_string(q.join("new-state.json")).unwrap(), "N", "지우지 않고 격리");
        // 멱등: 다시 돌리면 전부 Keep/Protected
        let again = restore(&live, &snap, &q, &prot, None).unwrap();
        assert!(again.iter().all(|a| matches!(a, Action::Keep(_) | Action::Protected(_))), "{again:?}");
    }

    #[test]
    fn corrupted_backup_is_never_restored() {
        let d = tmp("bad");
        let live = d.join("live");
        put(&live, "a", "A");
        let snap = d.join("snap");
        take(&live, &snap, &|_| true).unwrap();
        put(&snap, "files/a", "X"); // 사본 변조
        put(&live, "a", "NEW");
        let e = restore(&live, &snap, &d.join("q"), &|_| false, None).unwrap_err();
        assert!(e.starts_with("rollback_blocked"), "{e}");
        assert_eq!(std::fs::read_to_string(live.join("a")).unwrap(), "NEW", "불일치 백업으로 덮지 않는다");
    }

    #[test]
    fn existing_snapshot_is_not_overwritten_and_symlinks_are_not_followed() {
        let d = tmp("ex");
        let live = d.join("live");
        put(&live, "a", "A");
        #[cfg(unix)]
        std::os::unix::fs::symlink("/etc/hosts", live.join("link")).unwrap();
        let snap = d.join("snap");
        take(&live, &snap, &|_| true).unwrap();
        let m = parse_manifest(&std::fs::read_to_string(snap.join(MANIFEST_FILE)).unwrap()).unwrap();
        #[cfg(unix)]
        {
            // ★2판 C5: 링크는 따라가지 않고 링크 자체로 싣는다(대상 /etc/hosts 내용 0)
            assert_eq!(m.len(), 2);
            assert_eq!(m["link"].kind, Kind::Link);
            assert_eq!(std::fs::read_link(snap.join(FILES_DIR).join("link")).unwrap(), PathBuf::from("/etc/hosts"));
        }
        assert!(take(&live, &snap, &|_| true).is_err());
    }

    /// ★2판 C5·C6: 실행 비트·링크가 사라지면 복원이 되살린다 · 권한만 다른 같은 내용도 교체 · 사본+매니페스트를 함께 바꾼 백업은
    /// 내부 verify 는 통과해도 저널 고정 sha 와 달라 거부.
    #[cfg(unix)]
    #[test]
    fn links_and_modes_survive_and_journal_digest_pins_backup() {
        use std::os::unix::fs::PermissionsExt;
        let d = tmp("modes");
        let live = d.join("live");
        put(&live, "bin/run.sh", "#!/bin/sh");
        std::fs::set_permissions(live.join("bin/run.sh"), std::fs::Permissions::from_mode(0o755)).unwrap();
        std::os::unix::fs::symlink("bin/run.sh", live.join("run")).unwrap();
        let snap = d.join("snap");
        let pinned = take(&live, &snap, &|_| true).unwrap();
        let m = parse_manifest(&std::fs::read_to_string(snap.join(MANIFEST_FILE)).unwrap()).unwrap();
        assert_eq!((m["bin/run.sh"].mode, m["run"].kind), (0o755, Kind::Link));
        // 새 판이 실행 비트를 지우고 링크를 파일로 바꿈
        std::fs::set_permissions(live.join("bin/run.sh"), std::fs::Permissions::from_mode(0o644)).unwrap();
        std::fs::remove_file(live.join("run")).unwrap();
        put(&live, "run", "plain");
        let plan = restore(&live, &snap, &d.join("q"), &|_| false, Some(&pinned)).unwrap();
        assert!(plan.contains(&Action::Replace("bin/run.sh".into())), "같은 내용 · 권한만 다름 = 교체");
        assert_eq!(std::fs::metadata(live.join("bin/run.sh")).unwrap().permissions().mode() & 0o7777, 0o755);
        assert_eq!(std::fs::read_link(live.join("run")).unwrap(), PathBuf::from("bin/run.sh"));
        // 사본과 매니페스트를 함께 바꿈 = 내부 verify 통과 · 저널 고정값과 다름 = 거부
        put(&snap, "files/bin/run.sh", "evil");
        let mut m2 = m.clone();
        let (s2, n2) = sha256_file(&snap.join("files/bin/run.sh")).unwrap();
        m2.get_mut("bin/run.sh").unwrap().sha = s2;
        m2.get_mut("bin/run.sh").unwrap().size = n2;
        std::fs::write(snap.join(MANIFEST_FILE), render_manifest(&m2)).unwrap();
        std::fs::set_permissions(snap.join("files/bin/run.sh"), std::fs::Permissions::from_mode(0o755)).unwrap();
        assert!(verify(&snap).is_ok(), "내부 검증은 통과");
        let e = restore(&live, &snap, &d.join("q"), &|_| false, Some(&pinned)).unwrap_err();
        assert!(e.contains("저널 고정값"), "{e}");
        assert_eq!(std::fs::read_to_string(live.join("bin/run.sh")).unwrap(), "#!/bin/sh", "덮지 않음");
    }

    /// ★2판 C16(실 부작용 안 경계): 백업 도중 죽음 = 사본 일부·임시 파일만 있고 MANIFEST 없음 → 다시 take = 완주·검증(반쪽 사본을 백업으로
    /// 인정하지 않음) · MANIFEST 가 생긴 뒤엔 덮지 않음(재개는 verify 로).
    #[test]
    fn snapshot_interrupted_mid_copy_resumes_cleanly() {
        let d = tmp("midcopy");
        let live = d.join("live");
        put(&live, "a", "A");
        put(&live, "b/c", "C");
        let snap = d.join("snap");
        // 첫 파일만 복사되고 둘째 파일 임시본이 남은 채 죽음
        put(&snap, "files/a", "A");
        put(&snap, "files/b/.c.cys-tmp", "C-torn");
        assert!(verify(&snap).is_err(), "MANIFEST 없음 = 백업 아님");
        let m = take(&live, &snap, &|_| true).unwrap();
        assert_eq!(verify(&snap).unwrap(), m);
        let man = parse_manifest(&std::fs::read_to_string(snap.join(MANIFEST_FILE)).unwrap()).unwrap();
        assert_eq!(man.keys().cloned().collect::<Vec<_>>(), vec!["a", "b/c"], "임시본은 매니페스트 밖");
        assert!(take(&live, &snap, &|_| true).is_err(), "완성된 백업은 덮지 않음");
    }

    #[test]
    fn generations_keep_two_and_never_prune_before_fresh_verified() {
        let names: Vec<String> = ["3-a", "1-b", "2-c"].iter().map(|s| s.to_string()).collect();
        assert_eq!(prune_plan(&names, 2, true, &BTreeSet::new()), vec!["1-b".to_string()]);
        assert!(prune_plan(&names, 2, false, &BTreeSet::new()).is_empty(), "새 백업 검증 전 옛 세대 삭제 0");
        let never: BTreeSet<String> = ["1-b".to_string()].into();
        assert!(prune_plan(&names, 2, true, &never).is_empty(), "지금 설치판 것은 안 지움");
    }

    #[test]
    fn space_formula_and_free_space_reads() {
        assert_eq!(space_needed(10, 20, 30), 10 + 20 + 30 + 20 + RESERVE_BYTES);
        assert!(free_space(&std::env::temp_dir()).unwrap_or(0) > 0);
    }

    #[test]
    fn manifest_parser_rejects_traversal_and_dupes() {
        let s = "a".repeat(64);
        assert!(parse_manifest(&format!("{s}  1  f644  ../x\n")).is_err());
        assert!(parse_manifest(&format!("{s}  1  f644  x\n{s}  1  f644  x\n")).is_err());
        assert!(parse_manifest(&format!("{s}  q  f644  x\n")).is_err());
        assert!(parse_manifest(&format!("{s}  1  z644  x\n")).is_err(), "종류");
        assert!(parse_manifest(&format!("{s}  1  f99999  x\n")).is_err(), "권한");
        assert!(parse_manifest(&format!("{s}  1  x\n")).is_err(), "2판 전 형식 = 거부");
        assert_eq!(parse_manifest(&format!("{s}  1  l0  a b\n")).unwrap()["a b"].kind, Kind::Link);
    }
}
