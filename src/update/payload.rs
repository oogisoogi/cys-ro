//! 윈 설치 페이로드 전수 대조(S9b · 설계 AUTO-UPDATE-118 §3-7 ⑥ · 1R BLOCK 10·13 · 📌12″ P1·P2).
//!
//! - 「종료 코드만 믿지 않는다」: 설치 뒤·데몬 기동 전에 설치 폴더를 U 서명 `payload_manifest`(새 판) **모든 파일**의 크기·sha256 과
//!   대조하고, 두 U 서명 매니페스트의 차집합(구판에만 있는 경로)만 지운다 — 상태 파일은 어느 매니페스트에도 없으므로 손대지 않는다.
//! - 제외 규칙 = U3 `scripts/update/payload-exclude.txt` 를 **같은 파일로**(컴파일 때 `include_str!`) 로드한다 — 수집기
//!   (`update_common.py` `load_payload_excludes`)와 다른 집합이 될 길 0(codex U3 2R #18). 제외 경로는 대조도 삭제도 하지 않는다.

use super::feed::PayloadEntry;
use super::snapshot::sha256_file;
use std::collections::{BTreeMap, BTreeSet};
use std::path::Path;

/// U3 와 공유하는 제외 규칙 원문(같은 파일).
pub const EXCLUDE_TEXT: &str = include_str!("../../scripts/update/payload-exclude.txt");

/// 제외 경로 집합(소문자 · `/` 구분). 형식 = U3 `load_payload_excludes` 와 같다: `#` 주석 줄·빈 줄 무시 · 그 밖 줄은 `경로 # 사유`
/// (사유 필수 — 없으면 Err).
pub fn exclude_set(text: &str) -> Result<BTreeSet<String>, String> {
    let mut out = BTreeSet::new();
    for line in text.lines() {
        let s = line.trim();
        if s.is_empty() || s.starts_with('#') {
            continue;
        }
        let Some((p, why)) = s.split_once(" # ") else {
            return Err(format!("payload-exclude 줄에 사유(' # ') 없음: {s:?}"));
        };
        if why.trim().is_empty() {
            return Err(format!("payload-exclude 사유 빈 값: {s:?}"));
        }
        out.insert(norm(p.trim()));
    }
    Ok(out)
}

pub fn shared_excludes() -> BTreeSet<String> {
    // 컴파일 때 박힌 파일이 깨졌으면 빈 집합이 아니라 패닉(시험이 잡는다) — 출시 빌드도 같은 바이트라 형식은 시험이 보증.
    exclude_set(EXCLUDE_TEXT).expect("payload-exclude.txt 형식")
}

pub fn norm(p: &str) -> String {
    p.replace('\\', "/").to_lowercase()
}

/// S9b 결과.
#[derive(Debug, Clone, Default, PartialEq, Eq, serde::Serialize)]
pub struct Report {
    pub checked: usize,
    pub missing: Vec<String>,
    pub mismatched: Vec<String>,
    /// 구판 매니페스트에만 있고 아직 설치 폴더에 남은 경로.
    pub stale_old_only: Vec<String>,
}

impl Report {
    pub fn ok(&self) -> bool {
        self.missing.is_empty() && self.mismatched.is_empty() && self.stale_old_only.is_empty()
    }
}

/// 구판에만 있는 경로(대소문자 무시 차집합) — 제외 경로는 빼고.
pub fn old_only(old: &[PayloadEntry], new: &[PayloadEntry], excl: &BTreeSet<String>) -> Vec<String> {
    let new_set: BTreeSet<String> = new.iter().map(|e| norm(&e.path)).collect();
    old.iter()
        .filter(|e| !new_set.contains(&norm(&e.path)) && !excl.contains(&norm(&e.path)))
        .map(|e| e.path.clone())
        .collect()
}

fn path_in(dir: &Path, rel: &str) -> std::path::PathBuf {
    rel.split('/').fold(dir.to_path_buf(), |p, c| p.join(c))
}

/// 설치 폴더 전수 대조(읽기만).
pub fn verify_install(dir: &Path, new: &[PayloadEntry], old: Option<&[PayloadEntry]>) -> Report {
    let excl = shared_excludes();
    let mut r = Report::default();
    for e in new.iter().filter(|e| !excl.contains(&norm(&e.path))) {
        r.checked += 1;
        match sha256_file(&path_in(dir, &e.path)) {
            Err(_) => r.missing.push(e.path.clone()),
            Ok((s, n)) if s != e.sha256 || n != e.size => r.mismatched.push(e.path.clone()),
            Ok(_) => {}
        }
    }
    if let Some(old) = old {
        for p in old_only(old, new, &excl) {
            if path_in(dir, &p).exists() {
                r.stale_old_only.push(p);
            }
        }
    }
    r
}

/// 「구판에만 있는 경로」 삭제(P2 · 롤백 RB_SWAPPED 에서는 old/new 를 바꿔 부른다). 두 매니페스트 차집합 밖의 파일은 절대 안 지운다.
/// 지운 경로 목록.
pub fn delete_old_only(dir: &Path, old: &[PayloadEntry], new: &[PayloadEntry]) -> Result<Vec<String>, String> {
    let excl = shared_excludes();
    let mut gone = Vec::new();
    for p in old_only(old, new, &excl) {
        let f = path_in(dir, &p);
        match std::fs::symlink_metadata(&f) {
            Ok(md) if md.is_file() => {
                std::fs::remove_file(&f).map_err(|e| format!("{}: {e}", f.display()))?;
                gone.push(p);
            }
            Ok(_) => return Err(format!("구판 전용 경로가 정규 파일 아님 {p}")),
            Err(_) => {}
        }
    }
    if let Some(parent) = Some(dir) {
        let _ = super::journal::sync_dir(parent);
    }
    Ok(gone)
}

/// 매니페스트 정규 직렬화 sha256(저널 `payload_manifest_sha256`).
pub fn manifest_sha256(m: &[PayloadEntry]) -> String {
    use sha2::{Digest, Sha256};
    let sorted: BTreeMap<String, (&str, u64)> = m.iter().map(|e| (norm(&e.path), (e.sha256.as_str(), e.size))).collect();
    let mut h = Sha256::new();
    for (p, (s, n)) in sorted {
        h.update(format!("{s}  {n}  {p}\n").as_bytes());
    }
    format!("{:x}", h.finalize())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn e(path: &str, body: &str) -> PayloadEntry {
        use sha2::{Digest, Sha256};
        PayloadEntry { path: path.into(), size: body.len() as u64, sha256: format!("{:x}", Sha256::digest(body.as_bytes())) }
    }

    fn dir(tag: &str) -> std::path::PathBuf {
        let d = std::env::temp_dir().join(format!("cys-u2-payload-{tag}-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&d);
        std::fs::create_dir_all(&d).unwrap();
        d
    }

    /// ★U3 2R #18: S9b 와 수집기가 **같은 제외 집합**이다 — 같은 파일을 읽고, 수집기 파서(python)와 우리 파서의 결과가 같다.
    #[test]
    fn exclude_set_is_shared_with_u3_collector() {
        let ours = shared_excludes();
        assert!(ours.contains("uninstall.exe") && ours.contains("cys-install-failure.txt"));
        let disk = std::fs::read_to_string(concat!(env!("CARGO_MANIFEST_DIR"), "/scripts/update/payload-exclude.txt")).unwrap();
        assert_eq!(disk, EXCLUDE_TEXT, "include_str 사본 = 저장소 파일");
        let py = std::process::Command::new("python3")
            .args(["-I", "-c", "import sys,json;sys.path.insert(0,sys.argv[1]);import update_common as u;print(json.dumps(sorted(x.lower() for x in u.load_payload_excludes())))"])
            .arg(concat!(env!("CARGO_MANIFEST_DIR"), "/scripts/update"))
            .output();
        if let Ok(o) = py {
            if o.status.success() {
                let theirs: Vec<String> = serde_json::from_slice(&o.stdout).unwrap();
                assert_eq!(theirs, ours.iter().cloned().collect::<Vec<_>>(), "수집기 ↔ S9b 제외 집합 불일치");
            } else {
                panic!("수집기 파서 실행 실패: {}", String::from_utf8_lossy(&o.stderr));
            }
        }
        assert!(exclude_set("x.exe\n").is_err(), "사유 없는 줄 거부");
    }

    #[test]
    fn verify_install_full_match_and_mismatch_and_stale_old_only() {
        let d = dir("v");
        std::fs::write(d.join("cys.exe"), "NEW").unwrap();
        std::fs::create_dir_all(d.join("runtime")).unwrap();
        std::fs::write(d.join("runtime/a.dll"), "A").unwrap();
        std::fs::write(d.join("uninstall.exe"), "anything").unwrap();
        std::fs::write(d.join("state.db"), "user").unwrap();
        let new = vec![e("cys.exe", "NEW"), e("runtime/a.dll", "A"), e("uninstall.exe", "zzz")];
        let old = vec![e("cys.exe", "OLD"), e("runtime/old.dll", "O"), e("uninstall.exe", "q")];
        let r = verify_install(&d, &new, Some(&old));
        assert!(r.ok(), "{r:?} — uninstall.exe 는 공유 제외라 대조 안 함");
        std::fs::write(d.join("runtime/old.dll"), "O").unwrap();
        let r = verify_install(&d, &new, Some(&old));
        assert_eq!(r.stale_old_only, vec!["runtime/old.dll"]);
        std::fs::write(d.join("cys.exe"), "NEW!").unwrap();
        assert_eq!(verify_install(&d, &new, None).mismatched, vec!["cys.exe"]);
        std::fs::remove_file(d.join("runtime/a.dll")).unwrap();
        assert_eq!(verify_install(&d, &new, None).missing, vec!["runtime/a.dll"]);
    }

    /// 신판 전용 경로 삭제가 상태 파일·제외 파일을 건드리지 않는다(§7-1 3판 추가).
    #[test]
    fn delete_old_only_never_touches_state_or_excluded() {
        let d = dir("del");
        for (p, b) in [("cys.exe", "N"), ("new-only.dll", "X"), ("state.db", "S"), ("uninstall.exe", "U"), ("NEW-ONLY2.DLL", "Y")] {
            std::fs::write(d.join(p), b).unwrap();
        }
        // 롤백 방향: 「신판에만 있는 경로」 = old=신판 · new=구판
        let newer = vec![e("cys.exe", "N"), e("new-only.dll", "X"), e("uninstall.exe", "U"), e("new-only2.dll", "Y")];
        let older = vec![e("cys.exe", "O")];
        let gone = delete_old_only(&d, &newer, &older).unwrap();
        assert_eq!(gone.len(), 2, "{gone:?}");
        assert!(d.join("state.db").exists() && d.join("uninstall.exe").exists() && d.join("cys.exe").exists());
        assert!(!d.join("new-only.dll").exists());
    }

    #[test]
    fn manifest_sha_is_order_and_case_insensitive() {
        let a = vec![e("A.dll", "1"), e("b", "2")];
        let b = vec![e("b", "2"), e("a.DLL", "1")];
        assert_eq!(manifest_sha256(&a), manifest_sha256(&b));
    }
}
