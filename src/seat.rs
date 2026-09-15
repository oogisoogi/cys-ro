//! 좌석별 폴더(TICKET=cys-seat-folders · 2026-09-15) — 자식 좌석(cso·worker-N)이 마스터 좌석 폴더
//! 아래 **자기 폴더**에서 뜨게 한다:
//!
//! ```text
//! <마스터 좌석 폴더>/cso/          ← cso
//! <마스터 좌석 폴더>/workers/w1/   ← worker (worker-1 도 같은 자리)
//! <마스터 좌석 폴더>/workers/wN/   ← worker-N
//! ```
//!
//! master·리뷰어·그 밖의 역할은 좌석 폴더를 만들지 않는다(마스터 좌석 폴더 그대로).
//!
//! ## 두 구현 · 한 골든 표
//! python `cysjavis-pack/bin/javis_seat.py`(편성·피닉스 경로)와 이 모듈(`cys boot` 경로)이 같은 규칙을
//! 갖는다. 사본이 갈리면 경로마다 다른 폴더에서 좌석이 뜨므로, 두 쪽 시험이 **같은 골든 표**
//! `cysjavis-pack/templates/seat-layout.json` 을 읽는다 — 한쪽만 바꾸면 그쪽 시험이 적색이다.
//!
//! ## 좌석 폴더를 만들 때 함께 하는 일
//! ⓐ 얇은 `CLAUDE.md` — 팩 템플릿(`templates/seat-CLAUDE.md`)을 역할로 채워 **없을 때만** 만든다.
//! ⓑ 폴더 신뢰 시드 — 좌석 프로필 설정의 `projects[<좌석 폴더>].hasTrustDialogAccepted=true` 를
//!    **키가 없을 때만** 쓴다(계약 = [`crate::pack::plan_first_run_seed`] 그대로). Claude Code 는
//!    신뢰를 부모 폴더에서 상속하지만 **git 저장소 루트에서 멈춘다**(2.1.272 실측) — 좌석 폴더가
//!    git 저장소가 되면 상속이 끊기므로 상속 + 시드 이중이다. 설정 파일이 없으면 만들지 않는다.
//!
//! ## 실패는 좌석을 막지 않는다
//! 폴더를 못 만들면 [`SeatPrep::Failed`] — 호출부는 종전 cwd 로 띄운다. CLAUDE.md·신뢰 시드 실패는
//! [`SeatOutcome`] 의 상태 값으로만 남는다(상속이 여전히 1선이다).

use std::path::{Path, PathBuf};

/// 팩 루트 기준 좌석 CLAUDE.md 템플릿 경로.
pub const TEMPLATE_REL: &str = "templates/seat-CLAUDE.md";
/// 좌석 폴더에 시드하는 파일 이름.
pub const SEAT_CLAUDE_MD: &str = "CLAUDE.md";
/// 신뢰 시드 전 원본 백업(없을 때만 만든다 — 첫 시드 이전 상태를 보존한다).
pub const SEAT_TRUST_BACKUP: &str = ".claude.json.seat-seed.bak";
/// 교체 직전 파일이 바뀌었을 때 계획을 다시 세우는 최대 횟수(살아 있는 claude 세션과의 경합).
const CAS_TRIES: usize = 3;

/// 역할 → 좌석 폴더 상대경로(`/` 구분) 또는 `None`(좌석 폴더 없음). **순수** · 골든 표 핀.
pub fn seat_subdir(role: &str) -> Option<String> {
    let role = role.trim();
    if role == "cso" {
        return Some("cso".to_string());
    }
    if role == "worker" {
        return Some("workers/w1".to_string());
    }
    let n = role.strip_prefix("worker-")?;
    if n.is_empty() || n.len() > 4 || !n.bytes().all(|b| b.is_ascii_digit()) {
        return None;
    }
    let n: u32 = n.parse().ok()?;
    if n == 0 {
        return None;
    }
    Some(format!("workers/w{n}"))
}

/// 역할 → 정본 디렉티브 파일명. **순수**.
pub fn directive_file(role: &str) -> Option<&'static str> {
    let role = role.trim();
    for (prefix, name) in [
        ("master", "MASTER_DIRECTIVE.md"),
        ("cso", "CSO_DIRECTIVE.md"),
        ("worker", "WORKER_DIRECTIVE.md"),
        ("reviewer", "REVIEWER_DIRECTIVE.md"),
    ] {
        if role == prefix || role.starts_with(&format!("{prefix}-")) {
            return Some(name);
        }
    }
    None
}

/// 좌석 폴더의 기준으로 쓸 수 없는 폴더인가(빈 값·홈·파일시스템 루트). **순수**.
///
/// 홈·루트 밑에 `cso/`·`workers/` 를 만들면 사용자 폴더를 어지럽힌다 — '기준 없음'으로 접는다.
pub fn home_like(base: &Path, home: &Path) -> bool {
    if base.as_os_str().is_empty() {
        return true;
    }
    let b = lexical_normalize(base);
    b == lexical_normalize(home) || b.parent().is_none()
}

/// 경로의 `.`·`..` 를 **어휘적으로** 접는다(파일 접촉 0) — python `os.path.normpath` 와 같은 방향.
///
/// ★왜(codex 1R #3): 정규화 없이 비교하면 `<HOME>/x/..` 가 홈으로 판정되지 않아 홈 아래에
///   `cso/`·`workers/` 가 생겼다(python 은 normpath 로 거부 — 두 구현이 갈렸다).
pub fn lexical_normalize(p: &Path) -> PathBuf {
    use std::path::Component;
    let mut out = PathBuf::new();
    for c in p.components() {
        match c {
            Component::CurDir => {}
            Component::ParentDir => {
                // ★codex 2R #3: `..` 는 **실제 이름**만 지운다. 루트·드라이브 접두 위에서는 무시(루트의
                //   부모는 루트 — python normpath 동형), 앞선 `..` 위에서는 그대로 쌓는다(상대경로).
                match out.components().next_back() {
                    Some(Component::Normal(_)) => {
                        out.pop();
                    }
                    Some(Component::RootDir) | Some(Component::Prefix(_)) => {}
                    _ => out.push(".."),
                }
            }
            other => out.push(other.as_os_str()),
        }
    }
    out
}

/// (마스터 좌석 폴더, 역할) → 좌석 폴더 경로 또는 `None`. **순수**(파일 접촉 0).
pub fn seat_dir(base: &Path, role: &str, home: &Path) -> Option<PathBuf> {
    let sub = seat_subdir(role)?;
    if home_like(base, home) {
        return None;
    }
    let mut p = lexical_normalize(base);
    for c in sub.split('/') {
        p.push(c);
    }
    Some(p)
}

/// 템플릿의 `{{ROLE}}`·`{{DIRECTIVE}}` 를 채운다. **순수**.
pub fn render_claude_md(template: &str, role: &str) -> String {
    template
        .replace("{{ROLE}}", role)
        .replace("{{DIRECTIVE}}", directive_file(role).unwrap_or("WORKER_DIRECTIVE.md"))
}

fn key_form(p: &Path) -> String {
    let s = p.to_string_lossy().into_owned();
    if cfg!(windows) {
        // canonicalize 는 Windows 에서 `\\?\` 접두 경로를 준다 — claude 의 키 표기에는 없다.
        let s = s.strip_prefix(r"\\?\").unwrap_or(&s).to_string();
        s.replace('\\', "/")
    } else {
        s
    }
}

/// 신뢰 시드에 쓸 `projects` 키 — 경로 그대로 + (다르면) 실경로. Windows 는 `/` 구분.
///
/// Claude Code 는 키를 `/` 로 정규화해 대조한다(Windows 에서 `\`→`/`). 심볼릭 링크 밑 폴더는 어느
/// 표기로 조회될지 몰라 둘 다 쓴다(여분 키는 무해).
pub fn trust_keys(dir: &Path) -> Vec<String> {
    let mut keys: Vec<String> = Vec::new();
    let mut cands = vec![dir.to_path_buf()];
    if let Ok(c) = std::fs::canonicalize(dir) {
        cands.push(c);
    }
    for p in cands {
        let k = key_form(&p);
        if !k.is_empty() && !keys.contains(&k) {
            keys.push(k);
        }
    }
    keys
}

/// 신뢰 시드 결과.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum TrustSeed {
    /// 키를 추가했고 되읽기로 확인했다.
    Seeded(Vec<String>),
    /// 이미 키가 있다(값이 false 여도 덮지 않는다).
    NothingToDo,
    /// 설정 파일이 없다 — 만들지 않는다.
    ConfigAbsent,
    /// 보존 방향 거부(파싱 불가·모르는 형태·심볼릭 링크·백업 실패).
    Refused(String),
    /// 쓰기 실패 또는 경합 한도 초과.
    Failed(String),
    /// 썼지만 되읽기에서 확인되지 않았다.
    Unverified(Vec<String>),
}

impl TrustSeed {
    /// 사람용 짧은 라벨(python `javis_seat.seed_trust` 상태 값과 같은 어휘).
    pub fn label(&self) -> &'static str {
        match self {
            TrustSeed::Seeded(_) => "seeded",
            TrustSeed::NothingToDo => "nothing",
            TrustSeed::ConfigAbsent => "config-absent",
            TrustSeed::Refused(_) => "refused",
            TrustSeed::Failed(_) => "failed",
            TrustSeed::Unverified(_) => "unverified",
        }
    }
}

#[cfg(unix)]
fn file_mode(path: &Path) -> Option<u32> {
    use std::os::unix::fs::MetadataExt;
    std::fs::metadata(path).ok().map(|m| m.mode() & 0o7777)
}

#[cfg(not(unix))]
fn file_mode(_path: &Path) -> Option<u32> {
    None
}

/// 신뢰 시드 IO — `cfg_file`(`.claude.json`)에 `keys` 의 신뢰 키를 **없을 때만** 추가한다.
///
/// ★교체 직전 재대조: 이 파일은 살아 있는 claude 세션들도 쓴다(잠금을 잡지 않는다). 읽은 바이트와
///   교체 직전 바이트가 다르면 계획을 다시 세운다([`CAS_TRIES`] 회).
/// ⚠**원자적 비교-교체가 아니다**(codex 1R #1): 재대조와 rename 사이에 claude 가 저장하면 그 저장은
///   이 교체에 덮여 사라지고 결과는 여전히 `Seeded` 다. 창을 좁힐 뿐이며, claude 가 잠금을 잡지 않는
///   한 닫을 수 없다(기존 첫기동 시드 `pack::seed_first_run_gates_at` 도 같은 창을 갖는다). ★교체 대상이
///   **설정 파일 전체**라 유실 범위도 신뢰 키에 한정되지 않는다 — 그 순간 claude 가 쓴 다른 프로젝트
///   설정·세션 기록까지 사라질 수 있다(codex 2R #1 정정).
pub fn seed_trust(cfg_file: &Path, keys: &[String]) -> TrustSeed {
    use crate::pack::{plan_first_run_seed, AuthPremise};
    let is_link = std::fs::symlink_metadata(cfg_file)
        .map(|m| m.file_type().is_symlink())
        .unwrap_or(false);
    if is_link {
        return TrustSeed::Refused(format!("symlink 거부: {}", cfg_file.display()));
    }
    if !cfg_file.is_file() {
        return TrustSeed::ConfigAbsent;
    }
    for _ in 0..CAS_TRIES {
        let b0 = match std::fs::read(cfg_file) {
            Ok(b) => b,
            Err(e) => return TrustSeed::Refused(format!("{} 읽기 불가 — 보존: {e}", cfg_file.display())),
        };
        let existing: serde_json::Value = match serde_json::from_slice(&b0) {
            Ok(v) => v,
            Err(e) => return TrustSeed::Refused(format!("{} 파싱 불가 — 보존: {e}", cfg_file.display())),
        };
        let plan = plan_first_run_seed(&existing, keys, AuthPremise::Unproven);
        if let Some(why) = plan.refused {
            return TrustSeed::Refused(why);
        }
        if plan.added.is_empty() {
            return TrustSeed::NothingToDo;
        }
        let backup = cfg_file
            .parent()
            .unwrap_or_else(|| Path::new("."))
            .join(SEAT_TRUST_BACKUP);
        if !backup.exists() {
            if let Err(e) = std::fs::copy(cfg_file, &backup) {
                return TrustSeed::Refused(format!("백업 실패 — 시드 보류: {e}"));
            }
        }
        let body = match serde_json::to_vec_pretty(&plan.next) {
            Ok(b) => b,
            Err(e) => return TrustSeed::Failed(e.to_string()),
        };
        if std::fs::read(cfg_file).ok().as_deref() != Some(b0.as_slice()) {
            continue;
        }
        let mode = file_mode(cfg_file).or(Some(0o600));
        if let Err(e) = crate::pack::write_atomic_mode(cfg_file, &body, mode) {
            return TrustSeed::Failed(format!("{}: {e}", cfg_file.display()));
        }
        let verified = std::fs::read(cfg_file)
            .ok()
            .and_then(|b| serde_json::from_slice::<serde_json::Value>(&b).ok())
            .map(|v| {
                let re = plan_first_run_seed(&v, keys, AuthPremise::Unproven);
                re.refused.is_none() && re.added.is_empty()
            })
            .unwrap_or(false);
        return if verified {
            TrustSeed::Seeded(plan.added)
        } else {
            TrustSeed::Unverified(plan.added)
        };
    }
    TrustSeed::Failed(format!(
        "교체 직전 파일이 {CAS_TRIES}회 연속 바뀌었다(동시 쓰기 경합) — 상속에 맡긴다"
    ))
}

/// 좌석 CLAUDE.md 시드 결과.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum MdSeed {
    Seeded,
    /// 이미 있다 — 덮지 않는다.
    Kept,
    /// 팩에 템플릿이 없다 — 지어내지 않는다.
    TemplateAbsent,
    Failed(String),
}

impl MdSeed {
    pub fn label(&self) -> &'static str {
        match self {
            MdSeed::Seeded => "seeded",
            MdSeed::Kept => "kept",
            MdSeed::TemplateAbsent => "template-absent",
            MdSeed::Failed(_) => "failed",
        }
    }
}

fn seed_claude_md(seat: &Path, role: &str, pack_dir: &Path) -> MdSeed {
    let path = seat.join(SEAT_CLAUDE_MD);
    if std::fs::symlink_metadata(&path).is_ok() {
        return MdSeed::Kept;
    }
    let Ok(template) = std::fs::read_to_string(pack_dir.join(TEMPLATE_REL)) else {
        return MdSeed::TemplateAbsent;
    };
    match std::fs::OpenOptions::new().write(true).create_new(true).open(&path) {
        Ok(mut f) => {
            use std::io::Write;
            match f.write_all(render_claude_md(&template, role).as_bytes()) {
                Ok(()) => MdSeed::Seeded,
                Err(e) => MdSeed::Failed(e.to_string()),
            }
        }
        Err(e) if e.kind() == std::io::ErrorKind::AlreadyExists => MdSeed::Kept,
        Err(e) => MdSeed::Failed(e.to_string()),
    }
}

/// 좌석 폴더 준비 결과.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SeatOutcome {
    pub dir: PathBuf,
    pub created: bool,
    pub claude_md: MdSeed,
    pub trust: TrustSeed,
}

impl SeatOutcome {
    /// 한 줄 요약(python `javis_seat.describe` 와 같은 모양).
    pub fn summary(&self) -> String {
        format!(
            "좌석 폴더={}({}) · CLAUDE.md={} · 신뢰={}",
            self.dir.display(),
            if self.created { "신설" } else { "기존" },
            self.claude_md.label(),
            self.trust.label()
        )
    }
}

/// [`ensure_seat`] 의 결과.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SeatPrep {
    /// 좌석 폴더 대상이 아니다(역할·기준 폴더) — 호출부는 종전 cwd 를 쓴다.
    NotSeat,
    /// 폴더를 만들지 못했다 — 호출부는 종전 cwd 를 쓴다.
    Failed(String),
    Ready(SeatOutcome),
}

/// 좌석 폴더를 준비한다(폴더 생성 → CLAUDE.md 시드 → 신뢰 시드).
pub fn ensure_seat(
    base: &Path,
    role: &str,
    home: &Path,
    pack_dir: &Path,
    cfg_file: &Path,
) -> SeatPrep {
    let Some(dir) = seat_dir(base, role, home) else {
        return SeatPrep::NotSeat;
    };
    let created = !dir.is_dir();
    if let Err(e) = std::fs::create_dir_all(&dir) {
        return SeatPrep::Failed(format!("좌석 폴더 생성 실패({}): {e}", dir.display()));
    }
    let claude_md = seed_claude_md(&dir, role, pack_dir);
    let trust = seed_trust(cfg_file, &trust_keys(&dir));
    SeatPrep::Ready(SeatOutcome { dir, created, claude_md, trust })
}

#[cfg(test)]
mod tests {
    use super::*;

    const LAYOUT: &str = include_str!("../cysjavis-pack/templates/seat-layout.json");
    const TEMPLATE: &str = include_str!("../cysjavis-pack/templates/seat-CLAUDE.md");

    fn scratch(name: &str) -> PathBuf {
        let p = std::env::temp_dir().join(format!("cys-seat-{}-{name}", std::process::id()));
        let _ = std::fs::remove_dir_all(&p);
        std::fs::create_dir_all(&p).unwrap();
        p
    }

    #[test]
    fn seat_subdir_matches_the_golden_table_shared_with_python() {
        let v: serde_json::Value = serde_json::from_str(LAYOUT).unwrap();
        let cases = v["cases"].as_array().unwrap();
        assert!(cases.len() >= 10, "골든 표 사례가 {}건 — 공허 통과 차단", cases.len());
        for c in cases {
            let role = c[0].as_str().unwrap();
            let want = c[1].as_str().map(str::to_string);
            assert_eq!(seat_subdir(role), want, "role={role:?}");
        }
    }

    #[test]
    fn template_names_role_and_directive_without_internal_terms() {
        assert!(TEMPLATE.lines().count() <= 10, "얇은 CLAUDE.md 는 10줄 이내");
        let out = render_claude_md(TEMPLATE, "worker-2");
        assert!(out.contains("worker-2") && out.contains("WORKER_DIRECTIVE.md"), "{out}");
        assert!(!out.contains("{{"), "자리표시자가 남았다: {out}");
    }

    #[test]
    fn home_or_root_base_makes_no_seat_folder() {
        let home = Path::new("/srv/seat-home");
        assert_eq!(seat_dir(home, "cso", home), None);
        assert_eq!(seat_dir(Path::new("/"), "cso", home), None);
        assert_eq!(
            seat_dir(Path::new("/srv/seat-home/JarvisHome"), "worker-3", home),
            Some(PathBuf::from("/srv/seat-home/JarvisHome/workers/w3"))
        );
        assert_eq!(seat_dir(Path::new("/srv/seat-home/JarvisHome"), "master", home), None);
    }

    #[test]
    fn ensure_seat_creates_folder_md_and_trust_and_is_idempotent() {
        let t = scratch("ensure");
        let base = t.join("JarvisHome");
        let pack = t.join("pack");
        std::fs::create_dir_all(pack.join("templates")).unwrap();
        std::fs::write(pack.join(TEMPLATE_REL), "role={{ROLE}} dir={{DIRECTIVE}}\n").unwrap();
        let cfg = t.join("profile").join(".claude.json");
        std::fs::create_dir_all(cfg.parent().unwrap()).unwrap();
        std::fs::write(
            &cfg,
            r#"{"oauthAccount":{"k":1},"projects":{"/elsewhere":{"hasTrustDialogAccepted":false}}}"#,
        )
        .unwrap();
        let home = Path::new("/nonexistent-home");

        let SeatPrep::Ready(o) = ensure_seat(&base, "cso", home, &pack, &cfg) else {
            panic!("cso 좌석이 준비되지 않았다");
        };
        assert_eq!(o.dir, base.join("cso"));
        assert!(o.created && o.dir.is_dir());
        assert_eq!(o.claude_md, MdSeed::Seeded);
        assert!(matches!(o.trust, TrustSeed::Seeded(_)), "{:?}", o.trust);
        assert_eq!(
            std::fs::read_to_string(o.dir.join(SEAT_CLAUDE_MD)).unwrap(),
            "role=cso dir=CSO_DIRECTIVE.md\n"
        );
        let v: serde_json::Value = serde_json::from_slice(&std::fs::read(&cfg).unwrap()).unwrap();
        for k in trust_keys(&o.dir) {
            assert_eq!(v["projects"][&k]["hasTrustDialogAccepted"], true, "키 {k}");
        }
        assert_eq!(v["oauthAccount"]["k"], 1, "다른 키 보존");
        assert_eq!(v["projects"]["/elsewhere"]["hasTrustDialogAccepted"], false, "기존 false 보존");
        assert!(cfg.parent().unwrap().join(SEAT_TRUST_BACKUP).is_file(), "원본 백업");

        std::fs::write(o.dir.join(SEAT_CLAUDE_MD), "사용자 수정\n").unwrap();
        let SeatPrep::Ready(o2) = ensure_seat(&base, "cso", home, &pack, &cfg) else {
            panic!("두 번째 준비 실패");
        };
        assert!(!o2.created);
        assert_eq!(o2.claude_md, MdSeed::Kept);
        assert_eq!(o2.trust, TrustSeed::NothingToDo);
        assert_eq!(std::fs::read_to_string(o2.dir.join(SEAT_CLAUDE_MD)).unwrap(), "사용자 수정\n");
        let _ = std::fs::remove_dir_all(&t);
    }

    #[test]
    fn home_check_normalizes_dot_segments_before_comparing() {
        let home = Path::new("/srv/seat-home");
        assert_eq!(
            seat_dir(Path::new("/srv/seat-home/x/.."), "cso", home),
            None,
            "`<HOME>/x/..` 는 홈이다 — 홈 아래에 좌석 폴더를 만들면 안 된다(codex 1R #3)"
        );
        assert_eq!(
            seat_dir(Path::new("/srv/seat-home/./JH/../JH"), "cso", home),
            Some(PathBuf::from("/srv/seat-home/JH/cso"))
        );
        assert!(home_like(Path::new("/a/.."), home), "루트로 접히는 기준은 거부");
        // ★codex 2R #3: 루트 위 `..` 는 무시(루트의 부모는 루트) — `/../srv/seat-home` 는 홈이다.
        assert!(home_like(Path::new("/../srv/seat-home"), home), "루트 위 `..` 로 홈 차단 우회");
        assert_eq!(lexical_normalize(Path::new("/../a/b")), PathBuf::from("/a/b"));
        // 선행 `..` 는 지우지 않고 쌓는다(상대경로가 다른 위치로 바뀌면 안 된다).
        assert_eq!(lexical_normalize(Path::new("../../project")), PathBuf::from("../../project"));
        assert_eq!(lexical_normalize(Path::new("a/../../b")), PathBuf::from("../b"));
    }

    #[test]
    fn absent_config_is_not_created_and_master_is_not_a_seat() {
        let t = scratch("absent");
        let base = t.join("JarvisHome");
        let cfg = t.join("no-profile").join(".claude.json");
        let home = Path::new("/nonexistent-home");
        let SeatPrep::Ready(o) = ensure_seat(&base, "worker", home, &t.join("no-pack"), &cfg) else {
            panic!("worker 좌석이 준비되지 않았다");
        };
        assert_eq!(o.dir, base.join("workers").join("w1"));
        assert_eq!(o.trust, TrustSeed::ConfigAbsent);
        assert_eq!(o.claude_md, MdSeed::TemplateAbsent);
        assert!(!cfg.parent().unwrap().exists(), "설정 폴더를 만들었다");
        assert_eq!(ensure_seat(&base, "master", home, &t, &cfg), SeatPrep::NotSeat);
        let _ = std::fs::remove_dir_all(&t);
    }
}
