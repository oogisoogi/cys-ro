//! 맥 앱 내 업데이트(B7) — 우리 릴리스(oogisoogi/cys-ro)의 zip 을 받아 검증하고 설치본을 원자 교체한다.
//!
//! ★왜 tauri-plugin-updater 를 쓰지 않는가(실측 근거 · 2026-09-20)
//!   · 플러그인의 맥 설치 경로는 **tar.gz 전용**이다(`tauri-plugin-updater` 2.10.1
//!     `updater.rs:1233` — `tar::Archive::new(GzDecoder)`). 우리가 실제로 발행하는 맥 자산은
//!     `cysr-macos-arm64-v<판>.zip`(v1.0.2 실측 471,899,457 B) 이라 그 경로로는 풀리지 않는다.
//!   · 우리 맥 번들의 서명은 **cys-local 자체서명**이다(유료 공증 없음 = 절대 규칙). 그래서
//!     신뢰의 정박점이 minisign 서명이 아니라 **sha256 · 크기 · codesign 봉인 · CDHash** 넷이다.
//!   · 플러그인은 tar 최상위 이름을 버리고 **기존 번들 자리에 그대로** 넣는다(`updater.rs:1235·1302`)
//!     — 이름이 바뀌는 판(cys.app → cysr.app)에서 교체 결과가 옛 이름으로 남는다.
//!
//! ★이 모듈의 경계: 판정(순수 함수)과 집행(IO)을 가른다. 아래 `pure` 영역은 전부 시험 대상이고,
//!   집행 함수는 그 판정을 호출만 한다 — 검증이 「돌았는지」가 시험으로 고정된다.
//!
//! ★실행 금지 경계(TICKET=v110-darwin-update): 개발기에서 실제 교체를 실행하지 않는다.
//!   `CYS_UPDATE_APP_PATH`(교체 대상 번들) · `CYS_UPDATE_DRY_RUN=1`(검증까지만) 두 env 가 그
//!   격리 경로다 — 둘 다 **시험 전용**이며 기본값은 실제 설치본이다.

use serde_json::Value;
use std::path::{Path, PathBuf};

// ★집행 함수에도 최상위 `#[cfg(target_os = "macos")]` 를 걸지 않는다(main.rs BLOCK-B 핀과 같은 규율):
//   아이템을 지우면 호출부만 살아남아 다른 기판에서 E0425 로 즉사한다. 이 함수들은 std + sha2 만
//   쓰므로 어디서나 **컴파일**되고, 어느 기판에서 **도는지**는 install_update 의 분기가 정한다.

// ── 실패 분류 ────────────────────────────────────────────────────────────────
//
// ★코드 접두(`size_mismatch:` 등)를 붙이는 이유: UI·시험이 **문구가 아니라 코드**로 분기한다.
//   문구는 번역·첨삭으로 흔들리지만 코드는 계약이다(install_update 의 `live_sessions:` 선례와 동형).
#[derive(Debug, PartialEq, Eq)]
pub enum UpdateFail {
    /// 이 플랫폼 행이 원격 latest.json 에 없다 — 고장이 아니라 「이 판에 맥 자산이 없음」.
    NoRow(String),
    /// 행은 있으나 검증에 필요한 칸이 빠졌다(url·sha256·size·cdhash). fail-closed.
    Field(String),
    /// 받은 바이트 수가 매니페스트와 다르다.
    Size { expected: u64, actual: u64 },
    /// 내용 해시가 매니페스트와 다르다.
    Sha { expected: String, actual: String },
    /// codesign 봉인 검증 실패(자체서명이라도 봉인은 성립해야 한다).
    Signature(String),
    /// CDHash 가 매니페스트가 못박은 값과 다르다 = 서명은 성립하나 **다른 물건**이다.
    CdHash { expected: String, actual: String },
    /// 다운로드가 끝나지 못했다(네트워크 중단·curl 비정상 종료·파일 부재).
    Interrupted(String),
    /// 압축 해제·교체 단계 실패.
    Swap(String),
}

impl std::fmt::Display for UpdateFail {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            UpdateFail::NoRow(t) => write!(f, "no_darwin_row: 원격 latest.json 에 {t} 행이 없다"),
            UpdateFail::Field(k) => write!(
                f,
                "manifest_field: darwin 행에 {k} 가 없다 — 검증할 수 없으므로 설치하지 않는다"
            ),
            UpdateFail::Size { expected, actual } => write!(
                f,
                "size_mismatch: 받은 크기 {actual} B 가 매니페스트 {expected} B 와 다르다"
            ),
            UpdateFail::Sha { expected, actual } => write!(
                f,
                "sha_mismatch: 받은 sha256 {actual} 가 매니페스트 {expected} 와 다르다"
            ),
            UpdateFail::Signature(d) => write!(f, "signature_invalid: codesign 봉인 검증 실패 — {d}"),
            UpdateFail::CdHash { expected, actual } => write!(
                f,
                "cdhash_mismatch: 받은 CDHash {actual} 가 매니페스트 {expected} 와 다르다"
            ),
            UpdateFail::Interrupted(d) => write!(f, "download_interrupted: 다운로드가 끝나지 못했다 — {d}"),
            UpdateFail::Swap(d) => write!(f, "swap_failed: 설치본 교체 실패 — {d}"),
        }
    }
}

impl From<UpdateFail> for String {
    fn from(e: UpdateFail) -> String {
        e.to_string()
    }
}

// ── 순수 판정 ────────────────────────────────────────────────────────────────

/// 이 맥의 업데이터 타깃 키. latest.json `platforms` 의 행 이름과 같은 어휘를 쓴다
/// (윈도 경로가 `windows-x86_64` 를 쓰는 것과 동형 — 표시·문구 동형의 토대).
pub fn darwin_target() -> &'static str {
    if cfg!(target_arch = "x86_64") {
        "darwin-x86_64"
    } else {
        "darwin-aarch64"
    }
}

/// 검증에 필요한 네 값 — 하나라도 없으면 설치하지 않는다(fail-closed).
#[derive(Debug, PartialEq, Eq, Clone)]
pub struct DarwinAsset {
    pub url: String,
    pub sha256: String,
    pub size: u64,
    pub cdhash: String,
}

fn nonempty(v: &Value, key: &str) -> Result<String, UpdateFail> {
    v.get(key)
        .and_then(|x| x.as_str())
        .map(str::trim)
        .filter(|s| !s.is_empty())
        .map(str::to_string)
        .ok_or_else(|| UpdateFail::Field(key.to_string()))
}

/// latest.json 에서 이 타깃의 맥 자산을 뽑는다.
///
/// ★`signature` 칸은 **읽지 않는다**(우리 신뢰 정박점이 아니다). 그러나 그 칸이 매니페스트에
///   있어야 하는 이유는 따로 있다 — 플러그인의 `ReleaseManifestPlatform` 이 `url`+`signature`
///   둘 다를 요구하고 `RemoteReleaseInner` 가 `#[serde(untagged)]` 라서, darwin 행에 signature 가
///   없으면 **platforms 전체 역직렬화가 실패해 윈도 클라이언트까지 업데이트를 잃는다**.
///   그 관계는 `scripts/tests/test_darwin_update_row.py` 가 매니페스트 쪽에서 못박는다.
pub fn pick_darwin_asset(manifest: &Value, target: &str) -> Result<DarwinAsset, UpdateFail> {
    let row = manifest
        .get("platforms")
        .and_then(|p| p.get(target))
        .ok_or_else(|| UpdateFail::NoRow(target.to_string()))?;
    let size = row
        .get("size")
        .and_then(|x| x.as_u64())
        .filter(|n| *n > 0)
        .ok_or_else(|| UpdateFail::Field("size".to_string()))?;
    Ok(DarwinAsset {
        url: nonempty(row, "url")?,
        sha256: nonempty(row, "sha256")?.to_lowercase(),
        size,
        cdhash: nonempty(row, "cdhash")?.to_lowercase(),
    })
}

/// 판번 비교 — `remote > current` 인가. 숫자 구간만 본다(우리 판번은 x.y.z 고정).
/// 형식이 깨졌으면 **false**(모르면 받지 않는다 = 업데이트 강행 금지, check_update 와 같은 규율).
pub fn version_is_newer(remote: &str, current: &str) -> bool {
    fn parts(s: &str) -> Option<Vec<u64>> {
        let s = s.trim().trim_start_matches('v');
        // 프리릴리스·빌드 꼬리표는 버린다(우리 발행본에는 없다 — 있으면 숫자 구간만 비교).
        let core = s.split(['-', '+']).next()?;
        let v: Vec<u64> = core.split('.').map(|p| p.parse::<u64>().ok()).collect::<Option<_>>()?;
        if v.is_empty() {
            return None;
        }
        Some(v)
    }
    let (Some(r), Some(c)) = (parts(remote), parts(current)) else {
        return false;
    };
    let n = r.len().max(c.len());
    for i in 0..n {
        let a = r.get(i).copied().unwrap_or(0);
        let b = c.get(i).copied().unwrap_or(0);
        if a != b {
            return a > b;
        }
    }
    false
}

/// 무엇을 할지의 결론.
#[derive(Debug, PartialEq, Eq)]
pub enum DarwinVerdict {
    /// 받는다(새 판 또는 같은 판·다른 build_id).
    Install { version: String, notes: String, asset: DarwinAsset },
    /// 받지 않는다 — 사유(로그·시험용).
    Skip(&'static str),
    /// 판정 자체가 불가능하다(행 부재·칸 결손) — 사유를 그대로 올린다.
    Fail(UpdateFail),
}

/// 원격 매니페스트 → 결론. ★판번 게이트와 build_id 게이트의 관계는 윈도(check_update)와 같다:
/// 1순위 판번, 판번이 같을 때만 2순위 build_id. 다른 점은 이 판정이 **자기 손으로** 판번을
/// 비교한다는 것뿐이다(플러그인이 맥 행을 읽어 주지 않으므로).
pub fn decide_darwin_update(
    manifest: &Value,
    target: &str,
    current_version: &str,
    local_build_id: &str,
) -> DarwinVerdict {
    let Some(remote_version) = manifest.get("version").and_then(|v| v.as_str()) else {
        return DarwinVerdict::Skip("원격 latest.json 에 version 이 없다");
    };
    let remote_version = remote_version.trim().trim_start_matches('v').to_string();
    let newer = version_is_newer(&remote_version, current_version);
    if !newer {
        if remote_version != current_version.trim().trim_start_matches('v') {
            return DarwinVerdict::Skip("원격 판번이 설치본보다 낮다");
        }
        // 같은 판 — build_id 가 다를 때만 받는다(main.rs same_version_verdict 와 같은 규칙).
        let Some(remote_build) = manifest
            .get("build_id")
            .and_then(|v| v.as_str())
            .map(str::trim)
            .filter(|s| !s.is_empty())
        else {
            return DarwinVerdict::Skip("원격 build_id 없음 — 구판 latest.json 은 판번만 본다");
        };
        let local = local_build_id.trim();
        if local.is_empty() || local == "unknown" {
            return DarwinVerdict::Skip("내 build_id 를 모른다 — 헛업데이트 반복 방지");
        }
        if remote_build == local {
            return DarwinVerdict::Skip("같은 판·같은 build_id");
        }
    }
    match pick_darwin_asset(manifest, target) {
        Ok(asset) => DarwinVerdict::Install {
            version: remote_version,
            notes: manifest
                .get("notes")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_string(),
            asset,
        },
        Err(e) => DarwinVerdict::Fail(e),
    }
}

/// 받은 파일의 크기 검증.
pub fn verify_size(actual: u64, expected: u64) -> Result<(), UpdateFail> {
    if actual == expected {
        Ok(())
    } else {
        Err(UpdateFail::Size { expected, actual })
    }
}

/// 받은 파일의 내용 해시 검증(대소문자 무관·공백 허용).
pub fn verify_sha256(actual: &str, expected: &str) -> Result<(), UpdateFail> {
    let a = actual.trim().to_lowercase();
    let e = expected.trim().to_lowercase();
    if a == e {
        Ok(())
    } else {
        Err(UpdateFail::Sha { expected: e, actual: a })
    }
}

/// `codesign -dvvv` 출력(=stderr)에서 CDHash 를 뽑는다. 형식: `CDHash=<hex>`.
/// ★여러 줄이 나오는 판(아키텍처별)에서는 **첫 줄**을 쓴다 — 우리 번들은 단일 아키텍처다.
pub fn parse_cdhash(output: &str) -> Option<String> {
    output
        .lines()
        .map(str::trim)
        .find_map(|l| l.strip_prefix("CDHash="))
        .map(|h| h.trim().to_lowercase())
        .filter(|h| !h.is_empty())
}

/// CDHash 대조 — 못 읽었으면 **실패**다(측정 불가 ≠ 통과).
pub fn verify_cdhash(actual: Option<&str>, expected: &str) -> Result<(), UpdateFail> {
    let expected = expected.trim().to_lowercase();
    match actual.map(|a| a.trim().to_lowercase()) {
        Some(a) if a == expected => Ok(()),
        Some(a) => Err(UpdateFail::CdHash { expected, actual: a }),
        None => Err(UpdateFail::CdHash {
            expected,
            actual: "(읽지 못함)".to_string(),
        }),
    }
}

/// 다운로드가 **끝났는가**를 판정한다 — 크기 대조 이전의 축이다.
///
/// ★두 축을 갈라 두는 이유: 「중단」과 「크기 불일치」는 원인도 처방도 다르다. 중단은 다시 받으면
///   되고(네트워크), 크기 불일치는 **받은 물건이 다른 것**이다(자산 교체·매니페스트 낡음).
///   한 칸에 뭉치면 사용자는 둘 다 "다시 시도"로 읽고, 두 번째 경우엔 영원히 다시 시도한다.
pub fn classify_download(exit_code: Option<i32>, file_exists: bool) -> Result<(), UpdateFail> {
    match exit_code {
        Some(0) if file_exists => Ok(()),
        Some(0) => Err(UpdateFail::Interrupted("받은 파일이 없다".to_string())),
        Some(c) => Err(UpdateFail::Interrupted(format!(
            "curl 이 비정상 종료했다(code {c}) — 네트워크가 끊겼거나 자산이 없다"
        ))),
        // 시그널로 죽은 경우(코드 없음) — 사용자가 끊었거나 OS 가 죽였다.
        None => Err(UpdateFail::Interrupted(
            "다운로드가 신호로 종료됐다(코드 없음)".to_string(),
        )),
    }
}

/// codesign 봉인 검증 결과 판정. **성공이 아니면 전부 실패다** — 자체서명이라고 느슨하게 보지 않는다.
pub fn classify_codesign(success: bool, stderr: &str) -> Result<(), UpdateFail> {
    if success {
        Ok(())
    } else {
        Err(UpdateFail::Signature(stderr.trim().to_string()))
    }
}

/// 풀어 놓은 폴더의 최상위 항목들에서 교체에 쓸 `.app` **하나**를 고른다.
/// 0개·2개 이상은 실패다 — 「무엇을 설치하는지」가 애매한 채로 교체하지 않는다.
pub fn sole_app_bundle(entries: &[PathBuf]) -> Result<PathBuf, UpdateFail> {
    let apps: Vec<&PathBuf> = entries
        .iter()
        .filter(|p| p.extension().and_then(|e| e.to_str()) == Some("app"))
        .collect();
    match apps.len() {
        1 => Ok(apps[0].clone()),
        0 => Err(UpdateFail::Swap("압축 안에 .app 번들이 없다".to_string())),
        n => Err(UpdateFail::Swap(format!(
            "압축 안에 .app 번들이 {n} 개다 — 무엇을 설치할지 정할 수 없다"
        ))),
    }
}

/// 교체 직전 옛 번들을 옮겨 둘 자리 — **같은 부모 폴더**여야 rename 이 원자적이다
/// (다른 볼륨으로 옮기면 복사가 되고, 그 순간 「되돌릴 수 있다」는 전제가 깨진다).
pub fn backup_path(target: &Path, stamp: &str) -> PathBuf {
    let name = target
        .file_name()
        .and_then(|n| n.to_str())
        .unwrap_or("cysr.app");
    let parent = target.parent().unwrap_or_else(|| Path::new("/Applications"));
    parent.join(format!(".{name}.old-{stamp}"))
}

// ── 집행(IO) ─────────────────────────────────────────────────────────────────

/// 교체 대상 번들 경로. 기본은 **지금 돌고 있는 이 앱의 번들**이고,
/// `CYS_UPDATE_APP_PATH`(시험 전용)가 있으면 그것 — 개발기에서 라이브 설치본을 건드리지 않는 격리구다.
pub fn target_bundle(exe: &Path) -> Option<PathBuf> {
    if let Some(p) = cys::env_compat("CYS_UPDATE_APP_PATH") {
        return Some(PathBuf::from(p));
    }
    cys::app_bundle::enclosing_bundle(exe)
}

/// 검증만 하고 교체하지 않는 모드(개발기 시험용).
pub fn dry_run() -> bool {
    cys::env_compat("CYS_UPDATE_DRY_RUN").as_deref() == Some("1")
}

/// 파일 sha256(스트리밍).
pub fn sha256_file(p: &Path) -> Result<String, UpdateFail> {
    use sha2::{Digest, Sha256};
    use std::io::Read;
    let mut f = std::fs::File::open(p)
        .map_err(|e| UpdateFail::Interrupted(format!("받은 파일을 열 수 없다 — {e}")))?;
    let mut h = Sha256::new();
    let mut buf = vec![0u8; 1 << 20];
    loop {
        let n = f
            .read(&mut buf)
            .map_err(|e| UpdateFail::Interrupted(format!("받은 파일을 읽을 수 없다 — {e}")))?;
        if n == 0 {
            break;
        }
        h.update(&buf[..n]);
    }
    Ok(format!("{:x}", h.finalize()))
}

/// 원자 교체 — mv 2회(+실패 시 되돌리기 1회).
///
/// ★순서가 곧 실패 모드의 선택이다: **먼저 옛 것을 옆으로 옮기고(①), 새 것을 제자리에 넣는다(②).**
///   ②가 실패하면 ①을 되돌린다 — 어느 중간 지점에서 죽어도 「앱이 아예 없는 상태」로 남지 않는다.
///   (플러그인 경로의 실측 결함 ⓑ「rm -rf 가 먼저」와 정확히 반대다 — main.rs install_update 주석 참조.)
pub fn atomic_swap(target: &Path, staged: &Path, stamp: &str) -> Result<PathBuf, UpdateFail> {
    let backup = backup_path(target, stamp);
    if backup.exists() {
        let _ = std::fs::remove_dir_all(&backup);
    }
    // ① 옛 번들 → 백업(같은 부모 = 원자 rename)
    std::fs::rename(target, &backup).map_err(|e| {
        UpdateFail::Swap(format!(
            "옛 번들을 옆으로 옮기지 못했다({} → {}) — {e}",
            target.display(),
            backup.display()
        ))
    })?;
    // ② 새 번들 → 제자리
    if let Err(e) = std::fs::rename(staged, target) {
        // 되돌리기: 여기서 실패하면 그 사실까지 문구에 담는다(조용한 반쪽 상태 금지).
        let restored = std::fs::rename(&backup, target).is_ok();
        return Err(UpdateFail::Swap(format!(
            "새 번들을 제자리에 넣지 못했다 — {e} · 옛 번들 되돌리기 {}",
            if restored {
                "성공(설치본 보존)".to_string()
            } else {
                format!("실패 — 옛 번들은 {} 에 있다(손으로 되돌려라)", backup.display())
            }
        )));
    }
    Ok(backup)
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn manifest() -> Value {
        json!({
            "version": "1.1.0",
            "notes": "cysr 1.1.0",
            "build_id": "abcdef012345.20260920T0000Z",
            "platforms": {
                "windows-x86_64": {"signature": "sig", "url": "https://x/setup.exe"},
                "darwin-aarch64": {
                    "signature": "",
                    "url": "https://x/cysr-macos-arm64-v1.1.0.zip",
                    "sha256": "AABB",
                    "size": 471899457u64,
                    "cdhash": "DEADBEEF"
                }
            }
        })
    }

    #[test]
    fn picks_row_and_lowercases_hashes() {
        let a = pick_darwin_asset(&manifest(), "darwin-aarch64").unwrap();
        assert_eq!(a.sha256, "aabb");
        assert_eq!(a.cdhash, "deadbeef");
        assert_eq!(a.size, 471899457);
    }

    #[test]
    fn missing_row_is_absence_not_failure_wording() {
        let e = pick_darwin_asset(&manifest(), "darwin-x86_64").unwrap_err();
        assert_eq!(e, UpdateFail::NoRow("darwin-x86_64".into()));
        assert!(e.to_string().starts_with("no_darwin_row:"));
    }

    /// ★검증 칸이 빠진 행은 「설치」가 아니라 「거부」다 — 측정 불가를 통과로 읽지 않는다.
    #[test]
    fn missing_verification_field_is_fail_closed() {
        for drop in ["url", "sha256", "size", "cdhash"] {
            let mut m = manifest();
            m["platforms"]["darwin-aarch64"]
                .as_object_mut()
                .unwrap()
                .remove(drop);
            let e = pick_darwin_asset(&m, "darwin-aarch64").unwrap_err();
            assert_eq!(e, UpdateFail::Field(drop.to_string()), "{drop} 결손이 거부되지 않았다");
        }
    }

    #[test]
    fn zero_size_is_rejected() {
        let mut m = manifest();
        m["platforms"]["darwin-aarch64"]["size"] = json!(0);
        assert_eq!(
            pick_darwin_asset(&m, "darwin-aarch64").unwrap_err(),
            UpdateFail::Field("size".into())
        );
    }

    #[test]
    fn version_compare() {
        assert!(version_is_newer("1.1.0", "1.0.2"));
        assert!(version_is_newer("v1.0.3", "1.0.2"));
        assert!(!version_is_newer("1.0.2", "1.0.2"));
        assert!(!version_is_newer("1.0.1", "1.0.2"));
        assert!(version_is_newer("2.0", "1.9.9")); // 짧은 쪽은 0 으로 채워 비교한다
        assert!(!version_is_newer("망가진판", "1.0.2")); // 모르면 받지 않는다
        assert!(!version_is_newer("1.0.2", "망가진판"));
    }

    #[test]
    fn same_version_needs_different_build_id() {
        let m = manifest();
        // 같은 판 + 같은 build_id = 건너뜀
        assert_eq!(
            decide_darwin_update(&m, "darwin-aarch64", "1.1.0", "abcdef012345.20260920T0000Z"),
            DarwinVerdict::Skip("같은 판·같은 build_id")
        );
        // 같은 판 + 다른 build_id = 받는다
        assert!(matches!(
            decide_darwin_update(&m, "darwin-aarch64", "1.1.0", "999999999999.20260101T0000Z"),
            DarwinVerdict::Install { .. }
        ));
        // 같은 판 + 내 build_id 미상 = 건너뜀
        assert_eq!(
            decide_darwin_update(&m, "darwin-aarch64", "1.1.0", "unknown"),
            DarwinVerdict::Skip("내 build_id 를 모른다 — 헛업데이트 반복 방지")
        );
    }

    #[test]
    fn older_remote_is_skipped_and_newer_installs() {
        let m = manifest();
        assert_eq!(
            decide_darwin_update(&m, "darwin-aarch64", "1.2.0", "x"),
            DarwinVerdict::Skip("원격 판번이 설치본보다 낮다")
        );
        match decide_darwin_update(&m, "darwin-aarch64", "1.0.2", "x") {
            DarwinVerdict::Install { version, asset, .. } => {
                assert_eq!(version, "1.1.0");
                assert_eq!(asset.url, "https://x/cysr-macos-arm64-v1.1.0.zip");
            }
            other => panic!("새 판을 받지 않았다: {other:?}"),
        }
    }

    /// ★행 결손은 Skip 이 아니라 Fail 이다 — 「없음」과 「못 읽음」을 한 칸에 두지 않는다.
    #[test]
    fn newer_version_without_row_is_fail_not_skip() {
        let mut m = manifest();
        m["platforms"].as_object_mut().unwrap().remove("darwin-aarch64");
        assert_eq!(
            decide_darwin_update(&m, "darwin-aarch64", "1.0.2", "x"),
            DarwinVerdict::Fail(UpdateFail::NoRow("darwin-aarch64".into()))
        );
    }

    #[test]
    fn size_and_sha_gates() {
        assert!(verify_size(10, 10).is_ok());
        assert_eq!(
            verify_size(9, 10).unwrap_err(),
            UpdateFail::Size { expected: 10, actual: 9 }
        );
        assert!(verify_sha256("ABC", "abc").is_ok());
        assert!(verify_sha256("abc", "abd").unwrap_err().to_string().starts_with("sha_mismatch:"));
    }

    #[test]
    fn cdhash_parse_and_compare() {
        let out = "Executable=/tmp/cysr.app/Contents/MacOS/cys-app\nCDHash=0a1b2c3d\nSignature=adhoc\n";
        assert_eq!(parse_cdhash(out).as_deref(), Some("0a1b2c3d"));
        assert!(verify_cdhash(parse_cdhash(out).as_deref(), "0A1B2C3D").is_ok());
        assert_eq!(
            verify_cdhash(Some("ff"), "ee").unwrap_err(),
            UpdateFail::CdHash { expected: "ee".into(), actual: "ff".into() }
        );
        // ★못 읽은 것은 통과가 아니다.
        assert!(parse_cdhash("CDHash 없음").is_none());
        assert!(verify_cdhash(None, "ee").is_err());
    }

    /// 실패 5종 중 「중단」 — 종료코드·파일 유무 두 축으로 갈린다.
    #[test]
    fn download_interrupt_is_classified() {
        assert!(classify_download(Some(0), true).is_ok());
        assert!(matches!(
            classify_download(Some(0), false),
            Err(UpdateFail::Interrupted(_))
        ));
        let e = classify_download(Some(56), true).unwrap_err();
        assert!(e.to_string().starts_with("download_interrupted:"));
        assert!(e.to_string().contains("56"));
        // 시그널 사망(코드 없음)도 성공이 아니다 — 측정 불능을 통과로 읽지 않는다.
        assert!(classify_download(None, true).is_err());
    }

    /// 실패 5종 중 「서명」 — codesign 이 0 이 아니면 전부 거부다.
    #[test]
    fn codesign_failure_is_rejected() {
        assert!(classify_codesign(true, "").is_ok());
        let e = classify_codesign(false, "code object is not signed at all\n").unwrap_err();
        assert_eq!(
            e,
            UpdateFail::Signature("code object is not signed at all".to_string())
        );
        assert!(e.to_string().starts_with("signature_invalid:"));
    }

    #[test]
    fn sole_app_bundle_rules() {
        let one = vec![PathBuf::from("/t/cysr.app"), PathBuf::from("/t/readme.txt")];
        assert_eq!(sole_app_bundle(&one).unwrap(), PathBuf::from("/t/cysr.app"));
        assert!(sole_app_bundle(&[PathBuf::from("/t/readme.txt")]).is_err());
        let two = vec![PathBuf::from("/t/a.app"), PathBuf::from("/t/b.app")];
        assert!(sole_app_bundle(&two).unwrap_err().to_string().contains("2 개"));
    }

    /// 백업은 **같은 부모**에 둔다 — 다른 볼륨이면 rename 이 복사가 되고 되돌리기 전제가 깨진다.
    #[test]
    fn backup_stays_in_same_parent() {
        let b = backup_path(Path::new("/Applications/cysr.app"), "20260920T1900Z");
        assert_eq!(b.parent().unwrap(), Path::new("/Applications"));
        assert_eq!(
            b.file_name().unwrap().to_str().unwrap(),
            ".cysr.app.old-20260920T1900Z"
        );
    }
}
