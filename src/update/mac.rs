//! 맥 교체 — 압축 항목 검사 · 검증 3겹(codesign 봉인 · DR 핀 · CDHash + build-info) · `RENAME_SWAP` 1회 · 실물 판정 · `prev_bundle`
//! (설계 AUTO-UPDATE-118 §3-6 · BLOCK 3·7·14 · 3R MAJOR 1 · §3-10 RB_SWAPPED · §3-11 S9 맥).
//!
//! - ★DR 핀 문법(U3 실측 이관): 설계 문면 `-R='=designated => …'` 는 이 macOS 에서 **문법 오류**(`line 1:1: unexpected token: =`) →
//!   `-R='identifier "com.cysjavis.terminal" and certificate leaf = H"<40hex>"'` 를 쓴다([`dr_requirement`]).
//! - ★CDHash 가 읽혀도 서명된 번들이 아니다(애플 실리콘 링커가 Mach-O 를 자동 서명) → `codesign --verify --deep --strict` 필수.
//! - 볼륨이 RENAME_SWAP 을 지원하지 않으면 **보류**(`update.mac_swap_unsupported`) — rename 2회 길로 내려가지 않는다(그 사이 정식 이름이
//!   비는 창 = BLOCK 3 실패 장면).

use super::errors::ErrCode;
use super::runner::{Canon, Fail};
use std::path::{Path, PathBuf};

pub const BUNDLE_ID: &str = "com.cysjavis.terminal";
/// 바이너리 내장 DR 핀(leaf 인증서 SHA-1 · 피드가 바꿀 수 없다 · 추가·폐기는 R 서명 폐기문으로만 — §4-3).
pub const DR_PIN_LEAFS: &[&str] = &["a426231e7dc737ee1d74962b346c23d3acacb18d"];

/// `RENAME_SWAP`(libc) · `RENAME_NOFOLLOW_ANY`(macOS 13+ `sys/stdio.h` 0x10 — libc 크레이트 미정의라 여기 둔다).
pub const RENAME_SWAP: u32 = 0x2;
pub const RENAME_NOFOLLOW_ANY: u32 = 0x10;

pub fn dr_requirement(leaf_sha1: &str) -> String {
    format!("identifier \"{BUNDLE_ID}\" and certificate leaf = H\"{leaf_sha1}\"")
}

/// 정식 자리 옆 stage 이름(같은 부모 = 같은 볼륨).
pub fn staged_path(canonical: &Path, release_seq: u64) -> PathBuf {
    sibling(canonical, &format!(".cysr.app.new-{release_seq}"))
}

pub fn old_path(canonical: &Path, release_seq: u64) -> PathBuf {
    sibling(canonical, &format!(".cysr.app.old-{release_seq}"))
}

fn sibling(canonical: &Path, name: &str) -> PathBuf {
    canonical.parent().map(|p| p.join(name)).unwrap_or_else(|| PathBuf::from(name))
}

/// 압축 항목 이름 검사(BLOCK 14 · 풀기 전): 절대경로 · `..` 성분 · NUL · 역슬래시 거부.
pub fn check_entry_names(names: &[String]) -> Result<(), String> {
    for n in names {
        if n.starts_with('/') || n.contains('\0') || n.contains('\\') || n.split('/').any(|c| c == "..") {
            return Err(format!("압축 항목 거부 {n:?}"));
        }
    }
    Ok(())
}

/// 푼 트리 검사(풀기 뒤 · 교체 전): 심링크는 트리 **안**을 가리켜야 하고(바깥 = 거부) · 누적 크기 ≤ `max_unpacked`.
pub fn check_extracted_tree(root: &Path, max_unpacked: u64) -> Result<u64, String> {
    let canon_root = root.canonicalize().map_err(|e| e.to_string())?;
    let mut total = 0u64;
    let mut stack = vec![root.to_path_buf()];
    while let Some(d) = stack.pop() {
        for ent in std::fs::read_dir(&d).map_err(|e| e.to_string())? {
            let ent = ent.map_err(|e| e.to_string())?;
            let p = ent.path();
            let md = std::fs::symlink_metadata(&p).map_err(|e| e.to_string())?;
            if md.file_type().is_symlink() {
                let t = std::fs::read_link(&p).map_err(|e| e.to_string())?;
                let resolved = if t.is_absolute() { t.clone() } else { p.parent().unwrap_or(root).join(&t) };
                let norm = normalize(&resolved);
                if !norm.starts_with(&canon_root) && !norm.starts_with(root) {
                    return Err(format!("바깥을 가리키는 심링크 {} → {}", p.display(), t.display()));
                }
            } else if md.is_dir() {
                stack.push(p);
            } else {
                total = total.saturating_add(md.len());
                if total > max_unpacked {
                    return Err(format!("누적 크기 {total} > max_unpacked {max_unpacked}"));
                }
            }
        }
    }
    Ok(total)
}

fn normalize(p: &Path) -> PathBuf {
    let mut out = PathBuf::new();
    for c in p.components() {
        match c {
            std::path::Component::ParentDir => {
                out.pop();
            }
            std::path::Component::CurDir => {}
            other => out.push(other),
        }
    }
    out
}

/// `RENAME_SWAP | RENAME_NOFOLLOW_ANY` 1회. 미지원(ENOTSUP·EINVAL) = Err([`ErrCode::MacSwapUnsupported`]) · 권한(EACCES·EPERM·EROFS) =
/// [`ErrCode::MacAppsNotWritable`] · 그 밖 = `RotateFailed`(일시).
pub fn rename_swap(a: &Path, b: &Path) -> Result<(), Fail> {
    #[cfg(target_os = "macos")]
    {
        use std::os::unix::ffi::OsStrExt;
        let ca = std::ffi::CString::new(a.as_os_str().as_bytes()).map_err(|e| Fail::new(ErrCode::RotateFailed, "S9", e.to_string()))?;
        let cb = std::ffi::CString::new(b.as_os_str().as_bytes()).map_err(|e| Fail::new(ErrCode::RotateFailed, "S9", e.to_string()))?;
        let flags = if super::mutant("U2-NOFOLLOW") { RENAME_SWAP } else { RENAME_SWAP | RENAME_NOFOLLOW_ANY };
        // SAFETY: NUL 종단 경로 두 개 · 플래그는 커널이 검증한다.
        let rc = unsafe { libc::renamex_np(ca.as_ptr(), cb.as_ptr(), flags) };
        if rc == 0 {
            return Ok(());
        }
        let e = std::io::Error::last_os_error();
        let code = match e.raw_os_error() {
            Some(libc::ENOTSUP) | Some(libc::EINVAL) => ErrCode::MacSwapUnsupported,
            Some(libc::EACCES) | Some(libc::EPERM) | Some(libc::EROFS) => ErrCode::MacAppsNotWritable,
            _ => ErrCode::RotateFailed,
        };
        Err(Fail::new(code, "S9", format!("renamex_np {} ↔ {}: {e}", a.display(), b.display())))
    }
    #[cfg(not(target_os = "macos"))]
    {
        let _ = (a, b);
        Err(Fail::new(ErrCode::MacSwapUnsupported, "S9", "맥 전용"))
    }
}

/// 번들 신원(build-info 의 비교 칸).
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct Ident {
    pub release_seq: u64,
    pub build_id: String,
    pub target: String,
}

/// 번들 안 `cys build-info --json` 읽기(판독 불가 = None).
pub fn bundle_ident(bundle: &Path) -> Option<Ident> {
    let exe = bundle.join("Contents/MacOS/cys");
    let out = std::process::Command::new(&exe).args(["build-info", "--json"]).env_remove("CYS_UPDATE_STATE_DIR").output().ok()?;
    if !out.status.success() {
        return None;
    }
    let v: serde_json::Value = serde_json::from_slice(&out.stdout).ok()?;
    Some(Ident {
        release_seq: v.get("release_seq")?.as_u64()?,
        build_id: v.get("build_id")?.as_str()?.to_string(),
        target: v.get("target")?.as_str()?.to_string(),
    })
}

/// 실물 판정(순수): 정식 자리 신원이 새 판과 정확히 같으면 New · 옛 판과 같으면 Old · 그 밖·판독 불가 = Unknown.
pub fn judge_canonical(found: Option<&Ident>, new: &Ident, old: &Ident) -> Canon {
    match found {
        Some(f) if f == new => Canon::New,
        Some(f) if f == old => Canon::Old,
        _ => Canon::Unknown,
    }
}

/// 저널 없는 복구(§3-6 ④): 후보 `.cysr.app.new-*`·`.cysr.app.old-*` 중 신원이 `from` 과 같은 **유일한** 번들. 둘 이상·0 = None(사람 필요).
pub fn pick_unique_old(cands: &[(PathBuf, Option<Ident>)], from: &Ident) -> Option<PathBuf> {
    let hits: Vec<&PathBuf> = cands.iter().filter(|(_, i)| i.as_ref() == Some(from)).map(|(p, _)| p).collect();
    if hits.len() == 1 {
        Some(hits[0].clone())
    } else {
        None
    }
}

fn run(cmd: &str, args: &[&str]) -> (bool, String) {
    match std::process::Command::new(cmd).args(args).output() {
        Ok(o) => (o.status.success(), format!("{}{}", String::from_utf8_lossy(&o.stdout), String::from_utf8_lossy(&o.stderr))),
        Err(e) => (false, e.to_string()),
    }
}

/// 검증 3겹(§3-6 ②): ① `codesign --verify --deep --strict` ② DR 핀(내장 leaf 중 하나) ③ CDHash = 본문 · build-info = 본문 행.
pub fn verify_bundle(bundle: &Path, expect_cdhash: &str, expect: &Ident) -> Result<(), Fail> {
    let b = bundle.to_string_lossy().to_string();
    let (ok, out) = run("/usr/bin/codesign", &["--verify", "--deep", "--strict", &b]);
    if !ok {
        return Err(Fail::new(ErrCode::MacCodesignFail, "S2", out));
    }
    let pinned = DR_PIN_LEAFS.iter().any(|leaf| run("/usr/bin/codesign", &["--verify", &format!("-R={}", dr_requirement(leaf)), &b]).0);
    if !pinned {
        return Err(Fail::new(ErrCode::MacDrMismatch, "S2", "DR 핀 불일치"));
    }
    let (_, dv) = run("/usr/bin/codesign", &["-dvvv", &b]);
    let cd = super::macupdate::parse_cdhash(&dv);
    if super::macupdate::verify_cdhash(cd.as_deref(), expect_cdhash).is_err() {
        return Err(Fail::new(ErrCode::MacCdhashMismatch, "S2", format!("cdhash {cd:?}")));
    }
    match bundle_ident(bundle) {
        Some(i) if &i == expect => Ok(()),
        other => Err(Fail::new(ErrCode::BuildInfoMismatch, "S2", format!("{other:?}"))),
    }
}

/// S9 앞으로 교환(멱등 = 정식 자리가 이미 새 판이면 호출자가 부르지 않는다): `staged` ↔ `canonical` → 교환 직후 `on_swapped(prev_bundle 자리,
/// renamed:false)` 기록 → `staged`(이제 옛 번들) → `.cysr.app.old-<from_seq>` rename → `on_swapped(…, renamed:true)`.
/// 정식 이름에는 늘 완전한 번들 하나가 있다(rename 2회 길 없음).
pub fn swap_forward(
    canonical: &Path,
    staged: &Path,
    from_seq: u64,
    on_swapped: &mut dyn FnMut(&Path, bool) -> Result<(), Fail>,
) -> Result<PathBuf, Fail> {
    rename_swap(staged, canonical)?;
    on_swapped(staged, false)?;
    let old = old_path(canonical, from_seq);
    if old.exists() {
        return Err(Fail::new(ErrCode::RecoverAnomaly, "S9", format!("{} 이미 있음", old.display())));
    }
    std::fs::rename(staged, &old).map_err(|e| Fail::new(ErrCode::RotateFailed, "S9", e.to_string()))?;
    if let Some(p) = canonical.parent() {
        let _ = super::journal::sync_dir(p);
    }
    on_swapped(&old, true)?;
    Ok(old)
}

/// RB_SWAPPED(맥): 정식 자리 실물이 이미 옛 판이면 아무것도 안 함 · 새 판이면 옛 번들(`prev`)과 RENAME_SWAP 1회.
pub fn rb_swap(canonical: &Path, prev: &Path, found: Canon) -> Result<(), Fail> {
    match found {
        Canon::Old => Ok(()),
        Canon::New => rename_swap(prev, canonical),
        Canon::Unknown => Err(Fail::new(ErrCode::RecoverAnomaly, "RB_SWAPPED", "정식 자리 판독 불가")),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn d(tag: &str) -> PathBuf {
        let p = std::env::temp_dir().join(format!("cys-u2-mac-{tag}-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&p);
        std::fs::create_dir_all(&p).unwrap();
        p
    }

    #[test]
    fn dr_requirement_uses_the_syntax_that_parses_on_this_macos() {
        let r = dr_requirement(DR_PIN_LEAFS[0]);
        assert!(!r.starts_with('='), "=designated => 접두 = 문법 오류(U3 실측)");
        assert_eq!(r, "identifier \"com.cysjavis.terminal\" and certificate leaf = H\"a426231e7dc737ee1d74962b346c23d3acacb18d\"");
        // 이 맥의 codesign 이 요구 문법을 받아들이는지(번들 없이 파서만 — `-R` 을 빈 파일에 대고 「문법 오류」 문구가 아닌지 본다)
        if cfg!(target_os = "macos") {
            let f = d("dr").join("x");
            std::fs::write(&f, b"x").unwrap();
            let (_, out) = run("/usr/bin/codesign", &["--verify", &format!("-R={r}"), &f.to_string_lossy()]);
            assert!(!out.contains("unexpected token"), "{out}");
            let (_, bad) = run("/usr/bin/codesign", &["--verify", &format!("-R==designated => {r}"), &f.to_string_lossy()]);
            assert!(bad.contains("unexpected token") || bad.contains("syntax"), "옛 문법은 오류여야 한다: {bad}");
        }
    }

    #[test]
    fn entry_names_and_tree_checks() {
        assert!(check_entry_names(&["cysr.app/Contents/Info.plist".into()]).is_ok());
        for bad in ["/etc/x", "a/../../x", "a\0b", "a\\b"] {
            assert!(check_entry_names(&[bad.to_string()]).is_err(), "{bad:?}");
        }
        let t = d("tree");
        std::fs::create_dir_all(t.join("A.app/Contents")).unwrap();
        std::fs::write(t.join("A.app/Contents/f"), vec![0u8; 100]).unwrap();
        std::os::unix::fs::symlink("Contents/f", t.join("A.app/inner")).unwrap();
        assert_eq!(check_extracted_tree(&t, 1000).unwrap(), 100);
        assert!(check_extracted_tree(&t, 50).is_err(), "누적 크기 초과");
        std::os::unix::fs::symlink("/etc/hosts", t.join("A.app/out")).unwrap();
        assert!(check_extracted_tree(&t, 1000).unwrap_err().contains("바깥"));
    }

    #[test]
    fn canonical_judgement_is_exact_identity() {
        let n = Ident { release_seq: 9, build_id: "B".into(), target: "darwin-aarch64".into() };
        let o = Ident { release_seq: 8, build_id: "A".into(), target: "darwin-aarch64".into() };
        assert_eq!(judge_canonical(Some(&n), &n, &o), Canon::New);
        assert_eq!(judge_canonical(Some(&o), &n, &o), Canon::Old);
        let mut x = n.clone();
        x.build_id = "B2".into();
        assert_eq!(judge_canonical(Some(&x), &n, &o), Canon::Unknown, "같은 seq 다른 build_id = 판독 불가");
        assert_eq!(judge_canonical(None, &n, &o), Canon::Unknown);
        let c = vec![(PathBuf::from("/A/.cysr.app.new-9"), Some(o.clone())), (PathBuf::from("/A/.cysr.app.old-8"), Some(n.clone()))];
        assert_eq!(pick_unique_old(&c, &o), Some(PathBuf::from("/A/.cysr.app.new-9")));
        let c2 = vec![(PathBuf::from("/a"), Some(o.clone())), (PathBuf::from("/b"), Some(o.clone()))];
        assert_eq!(pick_unique_old(&c2, &o), None, "둘 이상 = 사람 필요");
    }

    /// 실 RENAME_SWAP(이 맥 APFS 임시 폴더 · 번들 흉내 폴더) — 교환 직후 prev_bundle 기록 → old 이름 → 정식 이름은 늘 존재 · 롤백은
    /// 실물 판정이라 두 번 불러도 옛 판 그대로.
    #[cfg(target_os = "macos")]
    #[test]
    fn swap_forward_then_rb_swap_is_idempotent_on_real_apfs() {
        let t = d("swap");
        let canon = t.join("cysr.app");
        std::fs::create_dir_all(&canon).unwrap();
        std::fs::write(canon.join("v"), "old").unwrap();
        let staged = staged_path(&canon, 9);
        std::fs::create_dir_all(&staged).unwrap();
        std::fs::write(staged.join("v"), "new").unwrap();
        let mut log = vec![];
        let old = swap_forward(&canon, &staged, 8, &mut |p, renamed| {
            assert!(canon.join("v").exists(), "정식 이름이 비는 순간 0");
            log.push((p.to_path_buf(), renamed));
            Ok(())
        })
        .unwrap();
        assert_eq!(std::fs::read_to_string(canon.join("v")).unwrap(), "new");
        assert_eq!(std::fs::read_to_string(old.join("v")).unwrap(), "old");
        assert_eq!(log, vec![(staged.clone(), false), (old.clone(), true)]);
        let found = |c: &Path| if std::fs::read_to_string(c.join("v")).unwrap() == "new" { Canon::New } else { Canon::Old };
        rb_swap(&canon, &old, found(&canon)).unwrap();
        assert_eq!(std::fs::read_to_string(canon.join("v")).unwrap(), "old");
        rb_swap(&canon, &old, found(&canon)).unwrap();
        assert_eq!(std::fs::read_to_string(canon.join("v")).unwrap(), "old", "RB_SWAPPED 두 번 = 옛 판 그대로");
        // 심링크 경로 성분 = RENAME_NOFOLLOW_ANY 로 거부
        let link = t.join("link.app");
        std::os::unix::fs::symlink(&canon, &link).unwrap();
        assert!(rename_swap(&old, &link.join("v")).is_err());
    }
}
