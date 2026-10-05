//! 빌드 신원(`cys build-info --json`) · 갱신 상태 폴더 · `install_id`(설계 AUTO-UPDATE-118 §4-2 · §3-9 V1 · §4-6 단계 배포).
//!
//! `build-info` = `{version, build_id, release_seq, target, features, bundled_pack, keyring_ids}` — 전부 빌드 때 박힌 상수라
//! 데몬 접속·파일 읽기 없이 나온다. stage·설치본의 정확 대조(V1 · BLOCK 13) 재료이고, 발행 쪽(U3)도 릴리스 본문의
//! 행 `{build_id, release_seq, bundled_pack, features}` 를 **이 출력에서** 만든다(같은 정의 한 벌).

use serde::Serialize;
use std::path::PathBuf;

/// 이 바이너리의 기판 이름(릴리스 본문 `assets` 키와 같은 낱말).
pub const TARGET: &str = if cfg!(all(target_os = "macos", target_arch = "aarch64")) {
    "macos-arm64"
} else if cfg!(all(target_os = "macos", target_arch = "x86_64")) {
    "macos-x64"
} else if cfg!(all(windows, target_arch = "x86_64")) {
    "windows-x64"
} else if cfg!(all(windows, target_arch = "aarch64")) {
    "windows-arm64"
} else if cfg!(all(target_os = "linux", target_arch = "x86_64")) {
    "linux-x64"
} else {
    "unknown"
};

/// 앱 층 기능 ID 목록(§3-9 V7 — 갱신 뒤 ⊇ 갱신 전). **이 판에서는 비어 있다**: 목록과 「ID 마다 코드 실재」 CI 검사는
/// V7 을 쓰는 U2·U4 가 정본 목록을 받아 채운다(근거 없는 ID 를 지금 지어 넣지 않는다). 빈 목록 ⊇ 빈 목록 = 통과라
/// 첫 판에서 V7 이 거짓 실패를 내지 않는다.
pub const FEATURES: &[&str] = &[];

/// 바이너리에 박힌 `release_seq`(build.rs 가 `CYSR_RELEASE_SEQ` 로 주입 · 로컬 빌드 = 0).
pub fn release_seq() -> u64 {
    option_env!("CYSR_RELEASE_SEQ").and_then(|v| v.parse().ok()).unwrap_or(0)
}

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
pub struct BundledPackInfo {
    pub version: String,
    /// 임베드 팩 트리 해시(`pack::embedded_pack_hash` — phoenix identity 와 같은 값).
    pub digest: String,
}

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
pub struct BuildInfo {
    pub version: String,
    pub build_id: String,
    pub release_seq: u64,
    pub target: String,
    pub features: Vec<String>,
    pub bundled_pack: BundledPackInfo,
    /// 내장 갱신 키링의 `용도:key_id` 목록(이 판 = 빈 목록 · U3 기입 뒤 4개).
    pub keyring_ids: Vec<String>,
}

pub fn build_info() -> BuildInfo {
    BuildInfo {
        version: env!("CARGO_PKG_VERSION").to_string(),
        build_id: crate::pack::build_id().to_string(),
        release_seq: release_seq(),
        target: TARGET.to_string(),
        features: FEATURES.iter().map(|s| s.to_string()).collect(),
        bundled_pack: BundledPackInfo {
            version: env!("CARGO_PKG_VERSION").to_string(),
            digest: crate::pack::embedded_pack_hash(),
        },
        keyring_ids: super::keys::UpdateKeyring::embedded().map(|k| k.key_ids()).unwrap_or_default(),
    }
}

/// stage·설치본 빌드 신원 정확 대조(V1 · BLOCK 13) — `{release_seq, build_id, target}` 셋이 모두 같아야 한다.
pub fn matches_asset(info: &BuildInfo, asset: &super::feed::Asset) -> bool {
    info.release_seq == asset.release_seq && info.build_id == asset.build_id && info.target == asset.target
}

// ── 상태 폴더 ──────────────────────────────────────────────────────────────────────────

/// 갱신 상태 폴더 env(시험·격리 — §7-2).
pub const ENV_STATE_DIR: &str = "CYS_UPDATE_STATE_DIR";

/// 갱신 상태 폴더 — `CYS_UPDATE_STATE_DIR` > (맥·리눅스) `~/.cys/update` · (윈) `%LOCALAPPDATA%\cys-update`
/// (설치·상태 폴더 밖 — 설치기가 덮는 자리와 갈라 둔다 · §3).
///
/// ★시험 빌드에서 env 가 없으면 panic(실 `~/.cys` 쓰기 0 봉인 — `pack::pack_dir` 와 같은 원칙).
pub fn state_dir() -> PathBuf {
    if let Some(v) = std::env::var_os(ENV_STATE_DIR).filter(|v| !v.is_empty()) {
        return PathBuf::from(v);
    }
    #[cfg(test)]
    {
        panic!("U1 시험 격리 봉인 위반 — CYS_UPDATE_STATE_DIR 미설정 상태에서 update::state_dir() 호출");
    }
    #[allow(unreachable_code)]
    default_state_dir()
}

fn default_state_dir() -> PathBuf {
    #[cfg(windows)]
    {
        let base = std::env::var_os("LOCALAPPDATA").map(PathBuf::from).unwrap_or_else(|| PathBuf::from("."));
        base.join("cys-update")
    }
    #[cfg(not(windows))]
    {
        dirs::home_dir().unwrap_or_else(|| PathBuf::from(".")).join(".cys").join("update")
    }
}

/// `install_id` 파일(기기에서 처음 1회 무작위 · 개인정보 0 · §4-6 단계 배포 버킷 · §3-1 지터 씨앗).
pub fn install_id_path(dir: &std::path::Path) -> PathBuf {
    dir.join("install_id")
}

/// 128비트 무작위 16진 문자열(OS CSPRNG — 유닉스 `/dev/urandom` · 윈 `BCryptGenRandom`). 실패 = Err(예측 가능 폴백 0).
pub fn random_hex128() -> Result<String, String> {
    let mut b = [0u8; 16];
    fill_random(&mut b)?;
    Ok(b.iter().map(|x| format!("{x:02x}")).collect())
}

#[cfg(unix)]
fn fill_random(buf: &mut [u8]) -> Result<(), String> {
    use std::io::Read;
    std::fs::File::open("/dev/urandom")
        .and_then(|mut f| f.read_exact(buf))
        .map_err(|e| format!("/dev/urandom: {e}"))
}

#[cfg(windows)]
fn fill_random(buf: &mut [u8]) -> Result<(), String> {
    use windows_sys::Win32::Security::Cryptography::{BCryptGenRandom, BCRYPT_USE_SYSTEM_PREFERRED_RNG};
    // SAFETY: buf 는 유효한 가변 슬라이스 · 알고리즘 핸들 NULL + 시스템 선호 RNG 플래그.
    let st = unsafe {
        BCryptGenRandom(std::ptr::null_mut(), buf.as_mut_ptr(), buf.len() as u32, BCRYPT_USE_SYSTEM_PREFERRED_RNG)
    };
    if st == 0 {
        Ok(())
    } else {
        Err(format!("BCryptGenRandom 0x{st:x}"))
    }
}

/// `install_id` 읽기 — 없으면 만들어 원자 기록. 형식(32자 소문자 16진)이 깨져 있으면 덮지 않고 Err(조용한 버킷 이동 0).
pub fn ensure_install_id(dir: &std::path::Path) -> Result<String, String> {
    let p = install_id_path(dir);
    match std::fs::read_to_string(&p) {
        Ok(s) => {
            let s = s.trim().to_string();
            if s.len() == 32 && s.chars().all(|c| c.is_ascii_hexdigit() && !c.is_ascii_uppercase()) {
                Ok(s)
            } else {
                Err(format!("install_id 형식 손상 {}", p.display()))
            }
        }
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => {
            std::fs::create_dir_all(dir).map_err(|e| format!("{}: {e}", dir.display()))?;
            let id = random_hex128()?;
            crate::pack::write_atomic(&p, id.as_bytes()).map_err(|e| format!("{}: {e}", p.display()))?;
            Ok(id)
        }
        Err(e) => Err(format!("{}: {e}", p.display())),
    }
}

/// 읽기 전용 조회(만들지 않음).
pub fn read_install_id(dir: &std::path::Path) -> Option<String> {
    let s = std::fs::read_to_string(install_id_path(dir)).ok()?;
    let s = s.trim();
    (s.len() == 32 && s.chars().all(|c| c.is_ascii_hexdigit())).then(|| s.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn build_info_shape() {
        let b = build_info();
        assert_eq!(b.version, env!("CARGO_PKG_VERSION"));
        assert_eq!(b.release_seq, release_seq());
        assert_eq!(b.target, TARGET);
        assert_ne!(b.target, "unknown", "CI 기판(맥·윈·리눅스 x64)은 이름이 있어야 한다");
        assert_eq!(b.bundled_pack.digest, crate::pack::embedded_pack_hash());
        let j = serde_json::to_value(&b).unwrap();
        for k in ["version", "build_id", "release_seq", "target", "features", "bundled_pack", "keyring_ids"] {
            assert!(j.get(k).is_some(), "build-info 칸 {k} 부재(§4-2)");
        }
    }

    /// 로컬·시험 빌드(CYSR_RELEASE_SEQ 미지정) = 0 — 어떤 릴리스의 min_from(≥1)도 못 넘는다.
    #[test]
    fn local_build_release_seq_is_zero_unless_injected() {
        match option_env!("CYSR_RELEASE_SEQ") {
            Some("0") | None => assert_eq!(release_seq(), 0),
            Some(v) => assert_eq!(release_seq().to_string(), v),
        }
    }

    #[test]
    fn matches_asset_needs_all_three() {
        let b = build_info();
        let mut a: super::super::feed::Asset = serde_json::from_value(serde_json::json!({
            "url": "u", "size": 1, "sha256": "x", "max_unpacked": 1, "target": b.target,
            "build_id": b.build_id, "release_seq": b.release_seq
        }))
        .unwrap();
        assert!(matches_asset(&b, &a));
        a.release_seq += 1;
        assert!(!matches_asset(&b, &a));
        a.release_seq -= 1;
        a.build_id.push('x');
        assert!(!matches_asset(&b, &a));
    }

    #[test]
    fn install_id_created_once_and_corruption_not_overwritten() {
        let d = std::env::temp_dir().join(format!("cys-u1-iid-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&d);
        let a = ensure_install_id(&d).unwrap();
        assert_eq!(a.len(), 32);
        assert_eq!(ensure_install_id(&d).unwrap(), a, "두 번째 호출 = 같은 값");
        assert_eq!(read_install_id(&d), Some(a.clone()));
        std::fs::write(install_id_path(&d), "zz").unwrap();
        assert!(ensure_install_id(&d).is_err(), "손상 = 덮지 않음");
        assert_eq!(std::fs::read_to_string(install_id_path(&d)).unwrap(), "zz");
        let _ = std::fs::remove_dir_all(&d);
        assert_ne!(random_hex128().unwrap(), random_hex128().unwrap());
    }

    #[test]
    fn state_dir_honors_env() {
        let _l = crate::pack::EnvGuard::set(ENV_STATE_DIR, "/tmp/cys-u1-state");
        assert_eq!(state_dir(), PathBuf::from("/tmp/cys-u1-state"));
    }
}
