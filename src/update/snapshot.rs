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

/// 원자 파일 쓰기(같은 폴더 임시 → fsync → rename → 부모 fsync).
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
    if let Ok(md) = std::fs::metadata(src) {
        let _ = std::fs::set_permissions(&tmp, md.permissions());
    }
    std::fs::rename(&tmp, dst).map_err(|e| format!("rename {}: {e}", dst.display()))?;
    super::journal::sync_dir(parent)?;
    Ok((format!("{:x}", h.finalize()), n))
}

/// 매니페스트 = 상대 경로 → (sha256, 크기).
pub type Manifest = BTreeMap<String, (String, u64)>;

pub fn render_manifest(m: &Manifest) -> String {
    m.iter().map(|(p, (s, n))| format!("{s}  {n}  {p}\n")).collect()
}

pub fn parse_manifest(text: &str) -> Result<Manifest, String> {
    let mut m = Manifest::new();
    for (i, line) in text.lines().enumerate() {
        let mut it = line.splitn(3, "  ");
        let (Some(s), Some(n), Some(p)) = (it.next(), it.next(), it.next()) else {
            return Err(format!("매니페스트 {}번째 줄 형식", i + 1));
        };
        let n: u64 = n.parse().map_err(|_| format!("매니페스트 {}번째 줄 크기", i + 1))?;
        if s.len() != 64 || !s.bytes().all(|b| b.is_ascii_hexdigit()) || p.is_empty() || p.split('/').any(|c| c == ".." || c.is_empty()) {
            return Err(format!("매니페스트 {}번째 줄 값", i + 1));
        }
        if m.insert(p.to_string(), (s.to_string(), n)).is_some() {
            return Err(format!("매니페스트 경로 중복 {p}"));
        }
    }
    Ok(m)
}

fn sha_hex(b: &[u8]) -> String {
    format!("{:x}", Sha256::digest(b))
}

/// 뿌리 하나 백업: `src` 의 「전체 − 제외」(`filter` true 만) → `dst/files/…` + `dst/MANIFEST.sha256` → **전수 재독 대조** →
/// 매니페스트 sha256. 데몬이 선 상태에서만 부른다(S7 뒤 · 한 시점).
pub fn take(src: &Path, dst: &Path, filter: &dyn Fn(&str) -> bool) -> Result<String, String> {
    if dst.join(MANIFEST_FILE).exists() {
        return Err(format!("이미 있는 스냅샷 {} — 덮지 않는다", dst.display()));
    }
    let files = list_files(src, filter)?;
    let mut m = Manifest::new();
    for rel in &files {
        let (s, n) = durable_copy(&src.join(rel), &dst.join(FILES_DIR).join(rel))?;
        m.insert(rel.clone(), (s, n));
    }
    std::fs::create_dir_all(dst).map_err(|e| e.to_string())?;
    let text = render_manifest(&m);
    super::journal::durable_write(&dst.join(MANIFEST_FILE), text.as_bytes())?;
    verify(dst)
}

/// 백업 검증(BLOCK 12): 매니페스트를 읽고 사본 **전부를 다시 읽어** 대조 → 매니페스트 sha256. 하나라도 어긋나면 Err.
pub fn verify(dst: &Path) -> Result<String, String> {
    let text = std::fs::read_to_string(dst.join(MANIFEST_FILE)).map_err(|e| format!("매니페스트 읽기: {e}"))?;
    let m = parse_manifest(&text)?;
    for (rel, (s, n)) in &m {
        let (s2, n2) = sha256_file(&dst.join(FILES_DIR).join(rel))?;
        if &s2 != s || &n2 != n {
            return Err(format!("백업 불일치 {rel}"));
        }
    }
    Ok(sha_hex(text.as_bytes()))
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

/// 복원 계획(순수): `live` = 지금 그 뿌리의 파일 → sha256(없으면 키 없음) · `protected` = 보호 경로 판정(ⓐ 새·옛 페이로드
/// 매니페스트 · ⓑ EXCLUDE · ⓒ 갱신 원장).
pub fn plan_restore(snap: &Manifest, live: &BTreeMap<String, String>, protected: &dyn Fn(&str) -> bool) -> Vec<Action> {
    let mut out = Vec::new();
    for (rel, (s, _)) in snap {
        match live.get(rel) {
            Some(l) if l == s => out.push(Action::Keep(rel.clone())),
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

/// 뿌리 하나 복원: 백업을 먼저 재대조(불일치 = 덮지 않고 Err = `update.rollback_blocked`) → 표 적용 → 매니페스트 전수 재대조.
/// `walk_filter` = 지금 뿌리에서 살펴볼 범위(보호 경로도 살펴보되 [`Action::Protected`] 로 무접촉).
pub fn restore(
    live_root: &Path,
    snap_dir: &Path,
    quarantine_root: &Path,
    protected: &dyn Fn(&str) -> bool,
) -> Result<Vec<Action>, String> {
    verify(snap_dir).map_err(|e| format!("rollback_blocked: {e}"))?;
    let snap = parse_manifest(&std::fs::read_to_string(snap_dir.join(MANIFEST_FILE)).map_err(|e| e.to_string())?)?;
    let mut live = BTreeMap::new();
    for rel in list_files(live_root, &|_| true)? {
        live.insert(rel.clone(), sha256_file(&live_root.join(&rel))?.0);
    }
    let plan = plan_restore(&snap, &live, protected);
    for a in &plan {
        match a {
            Action::Replace(rel) => {
                durable_copy(&snap_dir.join(FILES_DIR).join(rel), &live_root.join(rel))?;
            }
            Action::Quarantine(rel) => {
                let to = quarantine_root.join(rel);
                std::fs::create_dir_all(to.parent().ok_or("부모 없음")?).map_err(|e| e.to_string())?;
                if std::fs::rename(live_root.join(rel), &to).is_err() {
                    // 다른 볼륨 = 복사 후 지움(격리는 되돌릴 수 있어야 하므로 사본이 먼저 durable)
                    durable_copy(&live_root.join(rel), &to)?;
                    std::fs::remove_file(live_root.join(rel)).map_err(|e| e.to_string())?;
                }
            }
            Action::Keep(_) | Action::Protected(_) => {}
        }
    }
    for (rel, (s, _)) in &snap {
        if sha256_file(&live_root.join(rel))?.0 != *s {
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
    for rel in list_files(root, filter)? {
        sum = sum.saturating_add(std::fs::metadata(root.join(&rel)).map(|m| m.len()).unwrap_or(0));
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
        let plan = restore(&live, &snap, &q, &prot).unwrap();
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
        let again = restore(&live, &snap, &q, &prot).unwrap();
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
        let e = restore(&live, &snap, &d.join("q"), &|_| false).unwrap_err();
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
        assert_eq!(m.len(), 1, "심링크는 싣지 않는다");
        assert!(take(&live, &snap, &|_| true).is_err());
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
        assert!(parse_manifest(&format!("{s}  1  ../x\n")).is_err());
        assert!(parse_manifest(&format!("{s}  1  x\n{s}  1  x\n")).is_err());
        assert!(parse_manifest(&format!("{s}  q  x\n")).is_err());
    }
}
