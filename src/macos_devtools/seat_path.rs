//! 1.1.21 A ③ — **맥 좌석 셸 재선두**(`PATH_HELPER_ROOT`) 판정·생성·확인의 단일 정의처.
//!
//! 【왜】 CLT(명령어 라인 개발자 도구) 없는 맥의 좌석은 로그인 셸이다(`zsh -l` · `zsh -lc`). `/etc/zprofile`
//! 의 `path_helper` 가 `/usr/bin` 을 동봉 runtime 앞으로 되돌려, 에이전트가 치는 `git`·`python3` 이
//! 설치 창을 띄우는 셔임으로 풀린다. 좌석 안의 **중첩** 로그인 셸(codex 의 명령마다 `zsh -lc` · Claude
//! Code 스냅숏의 `zsh -c -l`)도 path_helper 를 다시 돌리므로 첫 셸만 고치는 장치로는 부족하다(설계 r3 ·
//! Fable r1 BLOCK). 그래서 강등을 일으키는 path_helper 자체를 좌석 env 로 다스린다 — path_helper 는
//! env `PATH_HELPER_ROOT` 가 있으면 `<root>/etc/paths`·`<root>/etc/paths.d` 를 읽는다(Apple 문서 없음 ·
//! 이 맥 27.2·VM 26.6.2 실측). 우리는 번들 밖 생성 dir 에 「시스템 `/etc/paths` 의 첫 `/usr/bin` 앞에
//! 고칠 dir 을 끼운 사본」 을 만들고 좌석 env 에 그 root 를 싣는다.
//!
//! 【계약 · 설계 DESIGN-A r7.2 §2-3】
//!   · 판정 = [`seat_path_verdict`] 한 함수 — cysd 좌석 스폰과 GUI 안내문이 같은 함수를 부른다.
//!   · 조건 순서 ①~⑧ 고정: ① macOS 아님 → None ② **물려받은 우리 값 걷기(항상 먼저)** ③ 롤백
//!     ④ 사용자 root 존중 ⑤ 고칠 도구 ⑥ 글자 검사 ⑦ root 세대 게시 ⑧ 결정론 확인(좌석마다 전체 비교).
//!   · `Applied` 일 때만 두 키(`PATH_HELPER_ROOT` + 짝 표식 `CYS_PATH_HELPER_ROOT`)를 싣는다. 그 밖은 종전
//!     동작이다(②에서 걷은 키만 빠진다). 진단 표지 `CYS_SEAT_PATH_VERDICT` 는 맥 좌석에 늘 싣는다(판정 재료 아님).
//!   · 게시된 세대 dir 은 **옮기지도 지우지도 않는다**(가리키는 좌석이 있을 수 있음) — 손상 세대는 그대로 두고
//!     다음 세대를 게시한다. 지우는 것은 10분 넘은 우리 임시 dir(`.tmp-*`)뿐이다.
//!   · 생성 자리(`base`)·시스템 `/etc` 뿌리·path_helper 경로는 [`SeatPathCtx`] 인자다 — 시험은 임시 dir 에서 돈다.

use std::collections::BTreeMap;
use std::ffi::{OsStr, OsString};
use std::io;
use std::path::{Path, PathBuf};
use std::time::{Duration, Instant, SystemTime};

/// path_helper 가 읽는 (문서 없는) env — 있으면 `<root>/etc/paths(.d)`·`manpaths(.d)` 를 읽는다.
pub const ENV_PATH_HELPER_ROOT: &str = "PATH_HELPER_ROOT";
/// 짝 표식 — 우리가 실은 `PATH_HELPER_ROOT` 와 **같은 값**(출처 표지 · ② 식별 재료).
pub const ENV_CYS_PATH_HELPER_ROOT: &str = "CYS_PATH_HELPER_ROOT";
/// 진단 표지(좌석 안 `echo $CYS_SEAT_PATH_VERDICT`) — 판정 재료가 아니다.
pub const ENV_CYS_SEAT_PATH_VERDICT: &str = "CYS_SEAT_PATH_VERDICT";
/// 축 롤백 노브 — `"0"` 만 끈다(마스터 `CYS_BOOT_GATES=0` 과 같은 엄격 비교).
pub const ENV_MAC_SEAT_PATH: &str = "CYS_MAC_SEAT_PATH";
/// 시스템 path_helper.
pub const SYSTEM_PATH_HELPER: &str = "/usr/libexec/path_helper";
/// 시스템 `/etc` 뿌리.
pub const SYSTEM_ETC: &str = "/etc";
/// 세대 이름 상한(`<h>`, `<h>.g2` … `<h>.g32`) — 넘으면 고유 이름 `<h>.x<pid>-<ns>`.
pub const GENERATIONS_MAX: u32 = 32;
/// path_helper 1회 상한(시간 초과는 그 자리에서 1회 다시 잰다).
pub const VERIFY_TIMEOUT: Duration = Duration::from_secs(1);
const TMP_PREFIX: &str = ".tmp-";
const TMP_STALE: Duration = Duration::from_secs(600);
/// ⑥ 글자 검사 — path_helper 출력은 `/etc/zprofile`·`/etc/profile` 이 **따옴표 없는 역따옴표**로 `eval` 한다. path_helper 는
/// `"`·`$`·`'` 만 백슬래시로 내고 역따옴표는 그대로 내 `eval` 이 실행한다(Fable 실측) · 줄바꿈은 파일 꼴을 깨고 콜론은 성분을
/// 쪼갠다 · 작은따옴표는 셸 큰따옴표 안에서 백슬래시가 남아 다른 dir 이 된다 · 출력은 IFS 로 쪼개졌다 한 칸 공백으로 다시
/// 붙으므로 탭과 **연속 공백**은 다른 dir 이 된다 · sh/bash 는 쪼갠 낱말에 경로 이름 확장을 하므로 `*`·`?`·`[` 도 뺀다
/// (Fable 코드 r1 minor — 실측: `My  Apps` 경로 = 판정 applied 인데 로그인 셸 git 은 /usr/bin/git).
pub const UNSAFE_PATH_CHARS: [char; 12] = ['`', '\\', '"', '$', ':', '\n', '\r', '\'', '\t', '*', '?', '['];

/// 사용자별 고정 생성 자리 `<home>/.cys/path-helper-root`(cysd·부서 데몬·GUI 공용).
pub fn path_helper_root_base(home: &Path) -> PathBuf {
    home.join(".cys").join("path-helper-root")
}

/// 롤백 판정(순수) — `CYS_BOOT_GATES=0`(마스터) 또는 `CYS_MAC_SEAT_PATH=0`(축).
pub fn mac_seat_path_rollback_from(boot_gates: Option<&str>, mac_seat_path: Option<&str>) -> bool {
    crate::boot_gates_master_off_from(boot_gates) || mac_seat_path == Some("0")
}

/// 좌석 env 손잡이 — cysd 는 pty `CommandBuilder`, GUI·시험은 맵, 부팅 scrub 은 프로세스 env 를 감싼다.
pub trait SeatEnv {
    fn get(&self, key: &str) -> Option<OsString>;
    fn set(&mut self, key: &str, val: &OsStr);
    fn remove(&mut self, key: &str);
}

/// 맵 env(GUI 판정·시험용).
impl SeatEnv for BTreeMap<String, OsString> {
    fn get(&self, key: &str) -> Option<OsString> {
        BTreeMap::get(self, key).cloned()
    }
    fn set(&mut self, key: &str, val: &OsStr) {
        self.insert(key.to_string(), val.to_os_string());
    }
    fn remove(&mut self, key: &str) {
        BTreeMap::remove(self, key);
    }
}

/// 판정 결과(설계 §2-3). 도구 이름 = `"python3"`·`"git"`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SeatPathVerdict {
    /// 두 키를 실었다. `fixed` = 고친 도구 · `unfixed` = CLT 에 없는데 못 고친 도구(동봉본 없음·글자 탈락).
    Applied {
        root: PathBuf,
        fixed: Vec<&'static str>,
        unfixed: Vec<&'static str>,
    },
    /// 고칠 dir 0. `unfixed` = CLT 에 없는데 동봉 실행 파일·runtime 이 없어 못 고친 도구(비면 = CLT 있음 · 진단은 같은 낱말 ·
    /// cysd 는 비지 않으면 로그 1줄 — Fable 코드 r1 minor).
    NotNeeded { unfixed: Vec<&'static str> },
    /// `CYS_BOOT_GATES=0` · `CYS_MAC_SEAT_PATH=0`.
    RolledBack,
    /// 사용자 `PATH_HELPER_ROOT` 존중(무접촉).
    UserRoot,
    /// 고칠 dir 이 전부 글자 검사 탈락.
    UnsafePath,
    /// 결정론 확인 실패(사유 = 고정 낱말 `timeout`·`mismatch`·`order`·`manpath`·`exec`).
    VerifyFailed(&'static str),
    /// 생성 오류(사유 = 고정 낱말 `write`·`read`·`generations`).
    Error(&'static str),
}

impl SeatPathVerdict {
    /// 진단 표지 값(고정 낱말만).
    pub fn diag(&self) -> String {
        match self {
            SeatPathVerdict::Applied { fixed, .. } => format!("applied:{}", fixed.join(",")),
            SeatPathVerdict::NotNeeded { .. } => "not-needed".into(),
            SeatPathVerdict::RolledBack => "rolled-back".into(),
            SeatPathVerdict::UserRoot => "user-root".into(),
            SeatPathVerdict::UnsafePath => "unsafe-path".into(),
            SeatPathVerdict::VerifyFailed(r) => format!("verify-failed:{r}"),
            SeatPathVerdict::Error(r) => format!("error:{r}"),
        }
    }
    /// 좌석에서 앱에 든 것으로 풀리는 도구(Applied 의 고친 도구 · 그 밖 = 빈 집합). 안내문이 쓴다.
    pub fn fixed_tools(&self) -> &[&'static str] {
        match self {
            SeatPathVerdict::Applied { fixed, .. } => fixed,
            _ => &[],
        }
    }
}

/// 판정 문맥(관측 층 인자). 시험은 임시 dir·가짜 path_helper 로 채운다.
#[derive(Debug, Clone)]
pub struct SeatPathCtx {
    /// `std::env::consts::OS` 꼴.
    pub os: String,
    /// ③ 롤백(데몬·GUI 프로세스 env 판독값).
    pub rollback: bool,
    /// 생성 자리(`<home>/.cys/path-helper-root`).
    pub base: PathBuf,
    /// 동봉 runtime 뿌리(`…/Contents/Resources/runtime` · 없으면 None = 개발 빌드 등).
    pub runtime_root: Option<PathBuf>,
    /// CLT 후보 표(`super::DEV_DIR_CANDIDATES`).
    pub dev_dir_candidates: Vec<PathBuf>,
    /// 시스템 `/etc` 뿌리(스냅숏 원천).
    pub etc_root: PathBuf,
    /// path_helper 실행 파일.
    pub path_helper: PathBuf,
    /// path_helper 1회 상한.
    pub verify_timeout: Duration,
}

impl SeatPathCtx {
    /// 이 프로세스(데몬·GUI)의 실제 문맥 — `exe_dir` = 실행 파일 부모(`runtime_bin_dirs` 와 같은 뿌리 탐색).
    pub fn for_process(exe_dir: &Path, home: &Path) -> Self {
        SeatPathCtx {
            os: std::env::consts::OS.to_string(),
            rollback: mac_seat_path_rollback_from(
                std::env::var(crate::ENV_BOOT_GATES).ok().as_deref(),
                std::env::var(ENV_MAC_SEAT_PATH).ok().as_deref(),
            ),
            base: path_helper_root_base(home),
            runtime_root: mac_runtime_root(exe_dir),
            dev_dir_candidates: super::DEV_DIR_CANDIDATES.iter().map(PathBuf::from).collect(),
            etc_root: PathBuf::from(SYSTEM_ETC),
            path_helper: PathBuf::from(SYSTEM_PATH_HELPER),
            verify_timeout: VERIFY_TIMEOUT,
        }
    }
}

/// `runtime_bin_dirs`(mac 갈래)와 같은 뿌리 — `exe_dir/../Resources/runtime` 우선, 개발 빌드 `exe_dir/runtime`.
pub fn mac_runtime_root(exe_dir: &Path) -> Option<PathBuf> {
    [
        exe_dir.parent().map(|p| p.join("Resources").join("runtime")),
        Some(exe_dir.join("runtime")),
    ]
    .into_iter()
    .flatten()
    .find(|rt| rt.is_dir())
}

/// 고칠 도구 표: (도구, PATH 에 세울 dir, 실행 가능 일반 파일이어야 하는 것들). git 은 감싸개가 부르는
/// 진짜 바이너리(`libexec/git-core/git`)도 함께 본다(Fable r4).
fn fix_table(rt: &Path) -> [(&'static str, PathBuf, Vec<PathBuf>); 2] {
    let py = rt.join("python").join("bin");
    let cysbin = rt.join("git").join("cysbin");
    [
        ("python3", py.clone(), vec![py.join("python3")]),
        (
            "git",
            cysbin.clone(),
            vec![
                cysbin.join("git"),
                rt.join("git").join("libexec").join("git-core").join("git"),
            ],
        ),
    ]
}

/// ② 식별 — 이 값이 **우리가 실은 root** 인가: 짝 표식과 같거나 `base` 바로 아래 이름(세대 `.g<n>`·`.x…` 포함).
/// 부팅 scrub 이 같은 함수를 쓴다(codex r4 minor).
pub fn is_our_path_helper_root(val: &OsStr, marker: Option<&OsStr>, base: &Path) -> bool {
    is_our_path_helper_root_opt(val, marker, Some(base))
}

/// `base` 를 모를 때(홈 없음) = 짝 표식 같음만으로 식별한다.
pub fn is_our_path_helper_root_opt(val: &OsStr, marker: Option<&OsStr>, base: Option<&Path>) -> bool {
    if val.is_empty() {
        return false;
    }
    if marker == Some(val) {
        return true;
    }
    let p = Path::new(val);
    match base {
        Some(b) => p.file_name().is_some() && p.parent() == Some(b),
        None => false,
    }
}

/// ② 물려받은 우리 값 걷기(어떤 판정보다 먼저·항상). 빈 값 `PATH_HELPER_ROOT=` 도 지운다(path_helper 실측:
/// 빈 값 = 시스템 값). 짝 표식만 있고 값이 다르면 표식만 지운다. 돌려주는 값 = 무엇을 지웠나(로그용).
pub fn scrub_inherited_ours(env: &mut dyn SeatEnv, base: &Path) -> (bool, bool) {
    scrub_inherited_ours_opt(env, Some(base))
}

/// [`scrub_inherited_ours`] 의 `base` 선택판 — 홈을 못 구했을 때도 ②를 건너뛰지 않는다(짝 표식 같음 · 빈 값만으로).
pub fn scrub_inherited_ours_opt(env: &mut dyn SeatEnv, base: Option<&Path>) -> (bool, bool) {
    let val = env.get(ENV_PATH_HELPER_ROOT);
    let marker = env.get(ENV_CYS_PATH_HELPER_ROOT);
    match val {
        Some(v) if v.is_empty() || is_our_path_helper_root_opt(&v, marker.as_deref(), base) => {
            env.remove(ENV_PATH_HELPER_ROOT);
            env.remove(ENV_CYS_PATH_HELPER_ROOT);
            (true, marker.is_some())
        }
        _ => {
            if marker.is_some() {
                env.remove(ENV_CYS_PATH_HELPER_ROOT);
                (false, true)
            } else {
                (false, false)
            }
        }
    }
}

fn is_executable_file(p: &Path) -> bool {
    super::is_executable_file(p)
}

/// 데몬 부팅 scrub(설계 §2-3) — ②와 **같은 식별**로 우리 것이면 두 root 키를 지우고, 진단 표지는 늘 지운다
/// (판정 재료가 아닌 우리 전용 키 · 좌석 안에서 뜬 데몬의 다른 자식(스케줄 잡 등)에 옛 값이 남지 않게 · Fable r4).
/// 돌려주는 값 = 지운 키(로그용).
pub fn scrub_boot_env(env: &mut dyn SeatEnv, base: &Path) -> Vec<&'static str> {
    let mut out = Vec::new();
    let (root, marker) = scrub_inherited_ours(env, base);
    if root {
        out.push(ENV_PATH_HELPER_ROOT);
    }
    if marker {
        out.push(ENV_CYS_PATH_HELPER_ROOT);
    }
    if env.get(ENV_CYS_SEAT_PATH_VERDICT).is_some() {
        env.remove(ENV_CYS_SEAT_PATH_VERDICT);
        out.push(ENV_CYS_SEAT_PATH_VERDICT);
    }
    out
}

/// 이 프로세스 env(데몬 부팅 scrub 용).
pub struct ProcessEnv;

impl SeatEnv for ProcessEnv {
    fn get(&self, key: &str) -> Option<OsString> {
        std::env::var_os(key)
    }
    fn set(&mut self, key: &str, val: &OsStr) {
        std::env::set_var(key, val);
    }
    fn remove(&mut self, key: &str) {
        std::env::remove_var(key);
    }
}

/// ⑥ 글자 검사 — 통과해야 path_helper 출력 문자열 = `eval` 결과(검증 문자열 비교가 곧 셸 결과).
pub fn path_chars_safe(dir: &Path) -> bool {
    match dir.to_str() {
        Some(s) => {
            !s.is_empty() && !s.contains("  ") && !s.chars().any(|c| UNSAFE_PATH_CHARS.contains(&c))
        }
        None => false,
    }
}

/// ★판정 본체(설계 §2-3 ①~⑧). `env` = 좌석 **최종** env(호출자 오버레이 → 데몬 env 를 다 반영한 것).
/// ②의 지움 · Applied 의 두 키 · 진단 표지를 `env` 에 직접 반영한다. 비-macOS = None(무접촉).
pub fn seat_path_verdict(ctx: &SeatPathCtx, env: &mut dyn SeatEnv) -> Option<SeatPathVerdict> {
    // ①
    if ctx.os != "macos" {
        return None;
    }
    // ②
    scrub_inherited_ours(env, &ctx.base);
    let v = verdict_after_scrub(ctx, env);
    if let SeatPathVerdict::Applied { root, .. } = &v {
        env.set(ENV_PATH_HELPER_ROOT, root.as_os_str());
        env.set(ENV_CYS_PATH_HELPER_ROOT, root.as_os_str());
    }
    env.set(ENV_CYS_SEAT_PATH_VERDICT, OsStr::new(&v.diag()));
    Some(v)
}

fn verdict_after_scrub(ctx: &SeatPathCtx, env: &dyn SeatEnv) -> SeatPathVerdict {
    // ③
    if ctx.rollback {
        return SeatPathVerdict::RolledBack;
    }
    // ④ (빈 값·우리 값은 ②에서 이미 걷혔다)
    if env.get(ENV_PATH_HELPER_ROOT).is_some() {
        return SeatPathVerdict::UserRoot;
    }
    // ⑤ 고칠 도구 — CLT 판정은 좌석 최종 env 의 DEVELOPER_DIR.
    let dev = env.get(super::ENV_DEVELOPER_DIR);
    let mut fix: Vec<(&'static str, PathBuf)> = Vec::new();
    let mut unfixed: Vec<&'static str> = Vec::new();
    let tools: Vec<(&'static str, Option<(PathBuf, Vec<PathBuf>)>)> = match &ctx.runtime_root {
        Some(rt) => fix_table(rt)
            .into_iter()
            .map(|(t, d, exes)| (t, Some((d, exes))))
            .collect(),
        None => vec![("python3", None), ("git", None)],
    };
    for (tool, plan) in tools {
        if super::clt_tool_present_in(dev.as_deref(), &ctx.dev_dir_candidates, tool) {
            continue;
        }
        match plan {
            Some((dir, exes)) if exes.iter().all(|e| is_executable_file(e)) => fix.push((tool, dir)),
            _ => unfixed.push(tool),
        }
    }
    if fix.is_empty() {
        return SeatPathVerdict::NotNeeded { unfixed };
    }
    // ⑥
    let mut safe: Vec<(&'static str, String)> = Vec::new();
    for (tool, dir) in fix {
        if path_chars_safe(&dir) {
            safe.push((tool, dir.to_string_lossy().into_owned()));
        } else {
            unfixed.push(tool);
        }
    }
    if safe.is_empty() {
        return SeatPathVerdict::UnsafePath;
    }
    let fix_dirs: Vec<String> = safe.iter().map(|(_, d)| d.clone()).collect();
    // ⑦
    let snap = match Snapshot::from_system(&ctx.etc_root, &fix_dirs) {
        Ok(s) => s,
        Err(r) => return SeatPathVerdict::Error(r),
    };
    let root = match publish_or_reuse(&ctx.base, &snap) {
        Ok(r) => r,
        Err(r) => return SeatPathVerdict::Error(r),
    };
    // ⑧
    let path = env.get("PATH");
    let manpath = env.get("MANPATH");
    if let Err(r) = verify_with_path_helper(
        &ctx.path_helper,
        path.as_deref(),
        manpath.as_deref(),
        &root,
        &fix_dirs,
        ctx.verify_timeout,
    ) {
        return SeatPathVerdict::VerifyFailed(r);
    }
    SeatPathVerdict::Applied {
        root,
        fixed: safe.iter().map(|(t, _)| *t).collect(),
        unfixed,
    }
}

// ───────────────────────── ⑦ 스냅숏 · 세대 게시 ─────────────────────────

/// `<root>/etc` 아래 파일 집합(상대 경로 바이트 → 내용). 키 = `paths` · `manpaths` · `paths.d/<이름>` ·
/// `manpaths.d/<이름>`. 생성 dir 은 `paths.d`·`manpaths.d` 를 (비어도) 늘 만든다.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Snapshot {
    pub files: BTreeMap<Vec<u8>, Vec<u8>>,
}

#[cfg(unix)]
fn os_bytes(s: &OsStr) -> Vec<u8> {
    use std::os::unix::ffi::OsStrExt;
    s.as_bytes().to_vec()
}
#[cfg(not(unix))]
fn os_bytes(s: &OsStr) -> Vec<u8> {
    s.to_string_lossy().as_bytes().to_vec()
}
#[cfg(unix)]
fn bytes_os(b: &[u8]) -> OsString {
    use std::os::unix::ffi::OsStrExt;
    OsStr::from_bytes(b).to_os_string()
}
#[cfg(not(unix))]
fn bytes_os(b: &[u8]) -> OsString {
    OsString::from(String::from_utf8_lossy(b).into_owned())
}

/// 시스템 `/etc/paths` 바이트에 고칠 dir 을 끼운다(순수): 첫 `/usr/bin` 줄 **바로 앞** · 그런 줄이 없으면 맨 앞.
/// 나머지 바이트는 그대로다.
pub fn paths_with_fix(system: &[u8], fix: &[String]) -> Vec<u8> {
    let mut ins: Vec<u8> = Vec::new();
    for f in fix {
        ins.extend_from_slice(f.as_bytes());
        ins.push(b'\n');
    }
    let mut out: Vec<u8> = Vec::with_capacity(system.len() + ins.len());
    let mut done = false;
    for line in system.split_inclusive(|b| *b == b'\n') {
        if !done {
            let body = line.strip_suffix(b"\n").unwrap_or(line);
            let trimmed = trim_ascii(body);
            if trimmed == b"/usr/bin" {
                out.extend_from_slice(&ins);
                done = true;
            }
        }
        out.extend_from_slice(line);
    }
    if !done {
        let mut front = ins;
        front.extend_from_slice(system);
        return front;
    }
    out
}

fn trim_ascii(b: &[u8]) -> &[u8] {
    let s = b.iter().position(|c| !c.is_ascii_whitespace()).unwrap_or(b.len());
    let e = b.iter().rposition(|c| !c.is_ascii_whitespace()).map(|i| i + 1).unwrap_or(s);
    &b[s..e.max(s)]
}

fn is_permission_denied(e: &io::Error) -> bool {
    e.kind() == io::ErrorKind::PermissionDenied
}

impl Snapshot {
    /// 시스템 `/etc` 뿌리에서 스냅숏을 뜬다 — path_helper 가 읽는 집합과 같게: `paths.d`·`manpaths.d` 의
    /// **lstat 일반 파일 전부**(점 파일 포함 · 심링크·하위 dir 제외 · 읽기 권한 오류 = 건너뜀 · Fable r3) +
    /// `manpaths`(있으면). `paths` 는 없으면 빈 바이트로 보고 고칠 dir 을 끼운다.
    pub fn from_system(etc_root: &Path, fix: &[String]) -> Result<Snapshot, &'static str> {
        let mut files: BTreeMap<Vec<u8>, Vec<u8>> = BTreeMap::new();
        let sys_paths = match std::fs::read(etc_root.join("paths")) {
            Ok(b) => b,
            Err(e) if e.kind() == io::ErrorKind::NotFound || is_permission_denied(&e) => Vec::new(),
            Err(_) => return Err("read"),
        };
        files.insert(b"paths".to_vec(), paths_with_fix(&sys_paths, fix));
        match std::fs::read(etc_root.join("manpaths")) {
            Ok(b) => {
                files.insert(b"manpaths".to_vec(), b);
            }
            Err(e) if e.kind() == io::ErrorKind::NotFound || is_permission_denied(&e) => {}
            Err(_) => return Err("read"),
        }
        for sub in ["paths.d", "manpaths.d"] {
            let rd = match std::fs::read_dir(etc_root.join(sub)) {
                Ok(rd) => rd,
                Err(e) if e.kind() == io::ErrorKind::NotFound || is_permission_denied(&e) => continue,
                Err(_) => return Err("read"),
            };
            for ent in rd {
                let ent = ent.map_err(|_| "read")?;
                let p = ent.path();
                let md = match std::fs::symlink_metadata(&p) {
                    Ok(m) => m,
                    Err(_) => continue,
                };
                if !md.file_type().is_file() {
                    continue;
                }
                match std::fs::read(&p) {
                    Ok(b) => {
                        let mut k = sub.as_bytes().to_vec();
                        k.push(b'/');
                        k.extend(os_bytes(&ent.file_name()));
                        files.insert(k, b);
                    }
                    Err(e) if is_permission_denied(&e) => continue,
                    Err(_) => return Err("read"),
                }
            }
        }
        Ok(Snapshot { files })
    }

    /// 결정론 직렬화(이름 = sha256 앞 16자의 재료).
    pub fn serialize(&self) -> Vec<u8> {
        let mut out = b"cys-path-helper-root-v1\0".to_vec();
        for (k, v) in &self.files {
            out.extend_from_slice(&(k.len() as u64).to_le_bytes());
            out.extend_from_slice(k);
            out.extend_from_slice(&(v.len() as u64).to_le_bytes());
            out.extend_from_slice(v);
        }
        out
    }

    /// 스냅숏 이름 `<h>` = sha256 앞 16자(hex).
    pub fn hash16(&self) -> String {
        use sha2::{Digest, Sha256};
        Sha256::digest(self.serialize())
            .iter()
            .take(8)
            .map(|b| format!("{b:02x}"))
            .collect()
    }

    /// 생성 dir 을 **엄격히** 읽는다 — `<dir>` 바로 아래는 `etc` 하나 · `etc` 아래는 `paths`·`manpaths`(일반
    /// 파일) · `paths.d`·`manpaths.d`(dir · 안은 일반 파일만). 그 밖의 무엇이든 있으면 None(= 같지 않음).
    fn read_generation(dir: &Path) -> Option<Snapshot> {
        let top: Vec<_> = std::fs::read_dir(dir).ok()?.collect::<Result<_, _>>().ok()?;
        if top.len() != 1 || top[0].file_name() != OsStr::new("etc") {
            return None;
        }
        let etc = dir.join("etc");
        if !std::fs::symlink_metadata(&etc).ok()?.file_type().is_dir() {
            return None;
        }
        let mut files: BTreeMap<Vec<u8>, Vec<u8>> = BTreeMap::new();
        let mut seen_dirs = 0;
        for ent in std::fs::read_dir(&etc).ok()? {
            let ent = ent.ok()?;
            let name = ent.file_name();
            let ft = std::fs::symlink_metadata(ent.path()).ok()?.file_type();
            match name.to_str() {
                Some("paths") | Some("manpaths") if ft.is_file() => {
                    files.insert(os_bytes(&name), std::fs::read(ent.path()).ok()?);
                }
                Some(sub @ ("paths.d" | "manpaths.d")) if ft.is_dir() => {
                    seen_dirs += 1;
                    for e2 in std::fs::read_dir(ent.path()).ok()? {
                        let e2 = e2.ok()?;
                        if !std::fs::symlink_metadata(e2.path()).ok()?.file_type().is_file() {
                            return None;
                        }
                        let mut k = sub.as_bytes().to_vec();
                        k.push(b'/');
                        k.extend(os_bytes(&e2.file_name()));
                        files.insert(k, std::fs::read(e2.path()).ok()?);
                    }
                }
                _ => return None,
            }
        }
        if seen_dirs != 2 {
            return None;
        }
        Some(Snapshot { files })
    }

    fn matches_dir(&self, dir: &Path) -> bool {
        Snapshot::read_generation(dir).as_ref() == Some(self)
    }

    fn materialize(&self, dir: &Path) -> io::Result<()> {
        let etc = dir.join("etc");
        std::fs::create_dir_all(etc.join("paths.d"))?;
        std::fs::create_dir_all(etc.join("manpaths.d"))?;
        for (k, v) in &self.files {
            std::fs::write(etc.join(bytes_os(k)), v)?;
        }
        Ok(())
    }
}

/// `<pid>-<ns><seq>` — macOS 시계는 마이크로초 해상도라 같은 프로세스의 두 스레드가 같은 ns 를 볼 수 있다
/// (경합 시험 실측) → 프로세스 안 순번을 붙여 임시·고유 이름이 겹치지 않게 한다.
fn unique_suffix() -> String {
    use std::sync::atomic::{AtomicU64, Ordering};
    static SEQ: AtomicU64 = AtomicU64::new(0);
    let ns = SystemTime::now()
        .duration_since(SystemTime::UNIX_EPOCH)
        .map(|d| d.as_nanos())
        .unwrap_or(0);
    format!("{}-{}{:04}", std::process::id(), ns, SEQ.fetch_add(1, Ordering::Relaxed) % 10_000)
}

/// 대상이 없을 때만 옮긴다(macOS = `renamex_np(RENAME_EXCL)`). 대상이 있으면 `AlreadyExists`.
fn rename_excl(from: &Path, to: &Path) -> io::Result<()> {
    #[cfg(target_os = "macos")]
    {
        use std::ffi::CString;
        use std::os::unix::ffi::OsStrExt;
        let f = CString::new(from.as_os_str().as_bytes())
            .map_err(|_| io::Error::from(io::ErrorKind::InvalidInput))?;
        let t = CString::new(to.as_os_str().as_bytes())
            .map_err(|_| io::Error::from(io::ErrorKind::InvalidInput))?;
        // SAFETY: 두 포인터는 이 블록 동안 사는 NUL 종료 C 문자열이다.
        let rc = unsafe { libc::renamex_np(f.as_ptr(), t.as_ptr(), libc::RENAME_EXCL) };
        if rc == 0 {
            return Ok(());
        }
        let e = io::Error::last_os_error();
        if e.raw_os_error() == Some(libc::EEXIST) || e.raw_os_error() == Some(libc::ENOTEMPTY) {
            return Err(io::Error::from(io::ErrorKind::AlreadyExists));
        }
        // 배타 rename 미지원 볼륨(man 2 renamex_np: ENOTSUP — 네트워크 홈·exFAT 등) → 실재 확인 + 일반 rename 으로 내려간다
        // (게시 dir 은 늘 비어 있지 않아 대상이 생겨 있으면 rename 이 ENOTEMPTY/EEXIST 로 거절 · 게시 뒤 재대조는 호출부 · Fable 코드 r1 minor).
        if e.raw_os_error() == Some(libc::ENOTSUP) {
            return rename_if_absent(from, to);
        }
        Err(e)
    }
    #[cfg(not(target_os = "macos"))]
    {
        rename_if_absent(from, to)
    }
}

/// 원자적 배타 rename 이 없을 때의 대체 — 대상 실재를 먼저 보고, 빈 dir 이 아닌 대상은 rename 이 ENOTEMPTY/EEXIST 로 거절한다.
fn rename_if_absent(from: &Path, to: &Path) -> io::Result<()> {
    {
        // 비-macOS(시험 호스트) — 원자적 배타 rename 이 없다. 대상 실재를 먼저 보고, 빈 dir 이 아닌 대상은
        // rename 이 ENOTEMPTY/EEXIST 로 거절한다(게시 dir 은 늘 `etc/` 를 가져 비어 있지 않다).
        if std::fs::symlink_metadata(to).is_ok() {
            return Err(io::Error::from(io::ErrorKind::AlreadyExists));
        }
        match std::fs::rename(from, to) {
            Ok(()) => Ok(()),
            Err(e) => {
                #[cfg(unix)]
                if e.raw_os_error() == Some(libc::EEXIST) || e.raw_os_error() == Some(libc::ENOTEMPTY) {
                    return Err(io::Error::from(io::ErrorKind::AlreadyExists));
                }
                Err(e)
            }
        }
    }
}

/// `.tmp-*` 중 10분 넘은 것만 지운다(우리 임시 dir · 게시 세대는 건드리지 않는다).
fn cleanup_stale_tmp(base: &Path) {
    let Ok(rd) = std::fs::read_dir(base) else { return };
    let now = SystemTime::now();
    for ent in rd.flatten() {
        let name = ent.file_name();
        if !name.to_string_lossy().starts_with(TMP_PREFIX) {
            continue;
        }
        let p = ent.path();
        let Ok(md) = std::fs::symlink_metadata(&p) else { continue };
        let old = md
            .modified()
            .ok()
            .and_then(|m| now.duration_since(m).ok())
            .map(|age| age > TMP_STALE)
            .unwrap_or(false);
        if !old {
            continue;
        }
        if md.file_type().is_dir() {
            let _ = std::fs::remove_dir_all(&p);
        } else {
            let _ = std::fs::remove_file(&p);
        }
    }
}

/// ⑦ root 세대 게시·재사용(설계 §2-3): 후보 `<h>`, `<h>.g2` … `<h>.g32` + `<h>.x*` 중 스냅숏과 같은 첫 dir 을
/// 재사용 → 없으면 `.tmp-<pid>-<ns>` 에 다 쓰고 아직 없는 첫 세대 이름으로 배타 rename(패배 = 그 dir 재대조 →
/// 같으면 재사용 · 다르면 다음 세대) → 상한을 넘으면 고유 이름 `<h>.x<pid>-<ns>`. 게시된 dir 은 옮기지도
/// 지우지도 않는다.
pub fn publish_or_reuse(base: &Path, snap: &Snapshot) -> Result<PathBuf, &'static str> {
    std::fs::create_dir_all(base).map_err(|_| "write")?;
    cleanup_stale_tmp(base);
    let h = snap.hash16();
    let mut names: Vec<String> = vec![h.clone()];
    names.extend((2..=GENERATIONS_MAX).map(|g| format!("{h}.g{g}")));
    let xprefix = format!("{h}.x");
    let x_existing = || -> Vec<PathBuf> {
        let mut v: Vec<PathBuf> = std::fs::read_dir(base)
            .map(|rd| {
                rd.flatten()
                    .filter(|e| e.file_name().to_string_lossy().starts_with(&xprefix))
                    .map(|e| e.path())
                    .collect()
            })
            .unwrap_or_default();
        v.sort();
        v
    };
    // 1단 — 재사용 훑기.
    for n in &names {
        let p = base.join(n);
        if std::fs::symlink_metadata(&p).is_ok() && snap.matches_dir(&p) {
            return Ok(p);
        }
    }
    for p in x_existing() {
        if snap.matches_dir(&p) {
            return Ok(p);
        }
    }
    // 2단 — 임시 dir 에 다 쓰고 게시.
    let mut tmp = base.join(format!("{TMP_PREFIX}{}", unique_suffix()));
    // 방금 쓴 것이 같게 읽히는지 자기 대조 — 늘 다르게 읽히는 볼륨(예: exFAT 의 AppleDouble `._*` 짝)에서 세대 dir 이
    // 좌석마다 쌓이지 않게 게시 전에 멈춘다(Fable 코드 r2 minor).
    if snap.materialize(&tmp).is_err() || !snap.matches_dir(&tmp) {
        let _ = std::fs::remove_dir_all(&tmp);
        return Err("write");
    }
    for n in &names {
        let p = base.join(n);
        if std::fs::symlink_metadata(&p).is_ok() {
            if snap.matches_dir(&p) {
                let _ = std::fs::remove_dir_all(&tmp);
                return Ok(p);
            }
            continue;
        }
        match rename_excl(&tmp, &p) {
            // 게시 직후 재대조 1회 — 다른 실행기가 (시계 점프 등으로) 우리 임시 dir 을 낡았다고 지우던 중이었으면 그 세대는
            // 그대로 두고(게시 dir 무접촉) 임시 dir 을 새로 써서 다음 세대로(Fable 코드 r1 minor).
            Ok(()) if snap.matches_dir(&p) => return Ok(p),
            Ok(()) => {
                tmp = base.join(format!("{TMP_PREFIX}{}", unique_suffix()));
                if snap.materialize(&tmp).is_err() {
                    let _ = std::fs::remove_dir_all(&tmp);
                    return Err("write");
                }
            }
            Err(e) if e.kind() == io::ErrorKind::AlreadyExists => {
                // 경합 패배 — 승자를 재대조한다.
                if snap.matches_dir(&p) {
                    let _ = std::fs::remove_dir_all(&tmp);
                    return Ok(p);
                }
            }
            Err(_) => {
                let _ = std::fs::remove_dir_all(&tmp);
                return Err("write");
            }
        }
    }
    let x = base.join(format!("{xprefix}{}", unique_suffix()));
    match rename_excl(&tmp, &x) {
        Ok(()) if !snap.matches_dir(&x) => Err("write"),
        Ok(()) => {
            eprintln!(
                "cys: path-helper-root 세대 상한 {GENERATIONS_MAX} 초과 — 고유 이름으로 게시 {}",
                x.display()
            );
            Ok(x)
        }
        Err(_) => {
            let _ = std::fs::remove_dir_all(&tmp);
            Err("generations")
        }
    }
}

// ───────────────────────── ⑧ 결정론 확인 ─────────────────────────

/// path_helper `-s` 출력 해석 결과.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PathHelperOut {
    pub path: Vec<String>,
    pub manpath: Option<String>,
}

/// `NAME="…"; export NAME;` 한 줄의 값(백슬래시 이스케이프 해제). 꼴이 다르면 None.
fn parse_assignment(line: &str, name: &str) -> Option<String> {
    let rest = line.strip_prefix(name)?.strip_prefix("=\"")?;
    let mut val = String::new();
    let mut chars = rest.chars();
    loop {
        match chars.next()? {
            '\\' => val.push(chars.next()?),
            '"' => break,
            c => val.push(c),
        }
    }
    let tail: String = chars.collect();
    if tail.trim() != format!("; export {name};") {
        return None;
    }
    Some(val)
}

/// path_helper `-s`(sh 꼴) 출력 해석(순수) — `PATH` 줄 필수 · `MANPATH` 줄 선택. 그 밖의 비지 않은 줄 = None.
pub fn parse_path_helper_output(out: &str) -> Option<PathHelperOut> {
    let mut path: Option<Vec<String>> = None;
    let mut manpath: Option<String> = None;
    for line in out.lines() {
        let line = line.trim();
        if line.is_empty() {
            continue;
        }
        if let Some(v) = parse_assignment(line, "PATH") {
            if path.is_some() {
                return None;
            }
            path = Some(v.split(':').map(str::to_string).collect());
        } else if let Some(v) = parse_assignment(line, "MANPATH") {
            if manpath.is_some() {
                return None;
            }
            manpath = Some(v);
        } else {
            return None;
        }
    }
    Some(PathHelperOut { path: path?, manpath })
}

/// 전체 비교(순수 · 설계 §2-3 합격 조건): (ⓑ 성분열 − 고칠 dir) == (ⓐ 성분열 − 고칠 dir) · ⓑ에 고칠 dir 이
/// 전부 정확히 1번씩 · 각각 ⓑ의 첫 `/usr/bin` 보다 앞 · MANPATH ⓑ == ⓐ.
pub fn verify(sys: &PathHelperOut, root: &PathHelperOut, fix: &[String]) -> Result<(), &'static str> {
    let strip = |v: &[String]| -> Vec<String> {
        v.iter().filter(|c| !fix.contains(c)).cloned().collect()
    };
    if strip(&root.path) != strip(&sys.path) {
        return Err("mismatch");
    }
    let usr_bin = root.path.iter().position(|c| c == "/usr/bin");
    for f in fix {
        if root.path.iter().filter(|c| *c == f).count() != 1 {
            return Err("mismatch");
        }
        let i = root.path.iter().position(|c| c == f).unwrap_or(usize::MAX);
        if let Some(u) = usr_bin {
            if i > u {
                return Err("order");
            }
        }
    }
    if root.manpath != sys.manpath {
        return Err("manpath");
    }
    Ok(())
}

/// path_helper 1회(관측 층): `env_clear` 뒤 좌석 `PATH`·`MANPATH`(있으면)와 (ⓑ면) `PATH_HELPER_ROOT` 만.
fn run_path_helper(
    ph: &Path,
    path: Option<&OsStr>,
    manpath: Option<&OsStr>,
    root: Option<&Path>,
    timeout: Duration,
) -> Result<String, &'static str> {
    use std::io::Read;
    use std::process::Stdio;
    // 창 정책 헬퍼 경유(원시 스폰 계수 동결 규약 · src/lib.rs spawn_policy_tests).
    let mut cmd = crate::hidden_command(ph);
    cmd.arg("-s").env_clear();
    if let Some(p) = path {
        cmd.env("PATH", p);
    }
    if let Some(m) = manpath {
        cmd.env("MANPATH", m);
    }
    if let Some(r) = root {
        cmd.env(ENV_PATH_HELPER_ROOT, r);
    }
    cmd.stdin(Stdio::null()).stdout(Stdio::piped()).stderr(Stdio::null());
    // 자기 프로세스 그룹 — 시간 초과 때 그 그룹만 끝낸다(자손이 stdout 을 쥐고 남지 않게 · 이름 일치 종료 0).
    #[cfg(unix)]
    {
        use std::os::unix::process::CommandExt;
        cmd.process_group(0);
    }
    let mut child = cmd.spawn().map_err(|_| "exec")?;
    let mut stdout = child.stdout.take().ok_or("exec")?;
    // 읽기는 따로 — 결과는 통로로 받고, 부모가 끝난 뒤에도 **같은 시한**까지만 기다린다(부모가 먼저 끝나고 자손이 stdout 을
    // 쥐고 남으면 EOF 가 늦다 · codex 코드 r1 minor).
    let (tx, rx) = std::sync::mpsc::channel::<Vec<u8>>();
    let reader = std::thread::spawn(move || {
        let mut buf = Vec::new();
        let _ = stdout.read_to_end(&mut buf);
        let _ = tx.send(buf);
    });
    let start = Instant::now();
    // 끝났는지 볼 때 **회수하지 않는다**(unix = waitid WNOWAIT) — 좀비가 그룹 id 를 쥐고 있어야 출력 대기 시간 초과 때
    // 그룹 종료가 남의 그룹(pid 재사용)에 닿지 않는다(codex 코드 r2 minor). 회수는 출력을 받은 뒤 `child.wait()`.
    loop {
        match exited_without_reaping(&mut child) {
            Ok(true) => break,
            Ok(false) if start.elapsed() >= timeout => {
                kill_group(&mut child);
                // 읽기 스레드는 기다리지 않는다(그룹 밖으로 샌 자손이 파이프를 쥐면 join 이 매달린다 — 시험 실측).
                drop(reader);
                return Err("timeout");
            }
            Ok(false) => std::thread::sleep(Duration::from_millis(2)),
            Err(_) => {
                kill_group(&mut child);
                drop(reader);
                return Err("exec");
            }
        }
    }
    let left = timeout.saturating_sub(start.elapsed());
    let buf = match rx.recv_timeout(left) {
        Ok(b) => b,
        Err(_) => {
            kill_group(&mut child);
            drop(reader);
            return Err("timeout");
        }
    };
    let status = child.wait().map_err(|_| "exec")?;
    if !status.success() {
        return Err("exec");
    }
    String::from_utf8(buf).map_err(|_| "exec")
}

/// 자식이 끝났는가 — unix 는 **회수하지 않고** 본다(`waitid(P_PID, WEXITED|WNOHANG|WNOWAIT)` · 좀비 유지 = pid·그룹 id 재사용 0).
fn exited_without_reaping(child: &mut std::process::Child) -> io::Result<bool> {
    #[cfg(unix)]
    {
        // SAFETY: siginfo 는 0 으로 채운 지역 값 · pid = 아직 회수하지 않은 우리 자식.
        let mut info: libc::siginfo_t = unsafe { std::mem::zeroed() };
        let rc = unsafe {
            libc::waitid(
                libc::P_PID,
                child.id() as libc::id_t,
                &mut info,
                libc::WEXITED | libc::WNOHANG | libc::WNOWAIT,
            )
        };
        if rc != 0 {
            return Err(io::Error::last_os_error());
        }
        // WNOHANG 에서 아직 안 끝났으면 si_pid = 0.
        #[cfg(target_os = "macos")]
        let pid = info.si_pid;
        #[cfg(not(target_os = "macos"))]
        let pid = unsafe { info.si_pid() };
        Ok(pid != 0)
    }
    #[cfg(not(unix))]
    {
        child.try_wait().map(|s| s.is_some())
    }
}

/// 우리가 띄운 자식의 프로세스 그룹(= 자식 pid)만 끝낸다.
fn kill_group(child: &mut std::process::Child) {
    #[cfg(unix)]
    {
        // SAFETY: 음수 pid = 그 프로세스 그룹. 그룹 id = 방금 `process_group(0)` 으로 띄운 자식 pid(자기 것만).
        let pgid = child.id() as libc::pid_t;
        if pgid > 0 {
            unsafe {
                libc::kill(-pgid, libc::SIGKILL);
            }
        }
    }
    let _ = child.kill();
    let _ = child.wait();
}

/// 시간 초과는 그 자리에서 1회 다시 잰다(부팅 때 좌석이 한꺼번에 뜰 때 · Fable r3).
fn run_path_helper_retry(
    ph: &Path,
    path: Option<&OsStr>,
    manpath: Option<&OsStr>,
    root: Option<&Path>,
    timeout: Duration,
) -> Result<String, &'static str> {
    match run_path_helper(ph, path, manpath, root, timeout) {
        Err("timeout") => run_path_helper(ph, path, manpath, root, timeout),
        r => r,
    }
}

/// ⑧ 결정론 확인(좌석마다 · 캐시 없음): ⓐ 시스템 · ⓑ `PATH_HELPER_ROOT=<root>` 두 출력 전체 비교.
pub fn verify_with_path_helper(
    ph: &Path,
    path: Option<&OsStr>,
    manpath: Option<&OsStr>,
    root: &Path,
    fix: &[String],
    timeout: Duration,
) -> Result<(), &'static str> {
    let a = run_path_helper_retry(ph, path, manpath, None, timeout)?;
    let b = run_path_helper_retry(ph, path, manpath, Some(root), timeout)?;
    let a = parse_path_helper_output(&a).ok_or("exec")?;
    let b = parse_path_helper_output(&b).ok_or("exec")?;
    verify(&a, &b, fix)
}

#[cfg(all(test, unix))]
mod tests {
    use super::*;
    use std::os::unix::fs::PermissionsExt;

    fn scratch(tag: &str) -> PathBuf {
        let base = std::env::temp_dir().join(format!("cys-phr-{tag}-{}", unique_suffix()));
        std::fs::create_dir_all(&base).unwrap();
        base
    }

    fn exe(p: &Path) {
        std::fs::create_dir_all(p.parent().unwrap()).unwrap();
        std::fs::write(p, b"#!/bin/sh\nexit 0\n").unwrap();
        std::fs::set_permissions(p, std::fs::Permissions::from_mode(0o755)).unwrap();
    }

    /// 가짜 동봉 runtime — python3 · 감싸개 · 진짜 git 자리.
    fn make_rt(rt: &Path, python: bool, wrapper: bool, core: bool) {
        std::fs::create_dir_all(rt.join("python").join("bin")).unwrap();
        std::fs::create_dir_all(rt.join("git").join("cysbin")).unwrap();
        if python {
            exe(&rt.join("python/bin/python3"));
        }
        if wrapper {
            exe(&rt.join("git/cysbin/git"));
        }
        if core {
            exe(&rt.join("git/libexec/git-core/git"));
        }
    }

    /// path_helper 흉내(sh) — `<root or etc>/paths` 줄 → 시작 PATH 의 나머지(중복 제거) · `-s` 꼴 출력.
    fn fake_path_helper(dir: &Path, etc: &Path) -> PathBuf {
        let p = dir.join("fake_path_helper");
        let body = format!(
            r#"#!/bin/sh
f="{etc}/paths"; [ -n "$PATH_HELPER_ROOT" ] && f="$PATH_HELPER_ROOT/etc/paths"
out=""
add() {{ case ":$out:" in *":$1:"*) ;; *) if [ -z "$out" ]; then out="$1"; else out="$out:$1"; fi;; esac; }}
while IFS= read -r l; do [ -n "$l" ] && add "$l"; done < "$f"
IFS=:; for c in $PATH; do [ -n "$c" ] && add "$c"; done
printf 'PATH="%s"; export PATH;\n' "$out"
[ -n "${{MANPATH+x}}" ] && printf 'MANPATH="%s"; export MANPATH;\n' "$MANPATH"
exit 0
"#,
            etc = etc.display()
        );
        std::fs::write(&p, body).unwrap();
        std::fs::set_permissions(&p, std::fs::Permissions::from_mode(0o755)).unwrap();
        p
    }

    fn script(dir: &Path, name: &str, body: &str) -> PathBuf {
        let p = dir.join(name);
        std::fs::write(&p, body).unwrap();
        std::fs::set_permissions(&p, std::fs::Permissions::from_mode(0o755)).unwrap();
        p
    }

    struct Fx {
        root: PathBuf,
        ctx: SeatPathCtx,
        rt: PathBuf,
    }

    /// 시험 문맥 — CLT 후보 = 빈 임시 자리(= CLT 없는 맥) · 시스템 /etc = 가짜.
    fn fx(tag: &str) -> Fx {
        let root = scratch(tag);
        let etc = root.join("etc");
        std::fs::create_dir_all(etc.join("paths.d")).unwrap();
        std::fs::write(etc.join("paths"), "/usr/local/bin\n/usr/bin\n/bin\n/usr/sbin\n/sbin\n").unwrap();
        std::fs::write(etc.join("paths.d").join("10-x"), "/opt/x/bin\n").unwrap();
        let rt = root.join("app").join("runtime");
        make_rt(&rt, true, true, true);
        let ph = fake_path_helper(&root, &etc);
        let ctx = SeatPathCtx {
            os: "macos".into(),
            rollback: false,
            base: root.join("home").join(".cys").join("path-helper-root"),
            runtime_root: Some(rt.clone()),
            dev_dir_candidates: vec![root.join("no-clt")],
            etc_root: etc,
            path_helper: ph,
            verify_timeout: VERIFY_TIMEOUT,
        };
        Fx { root, ctx, rt }
    }

    fn seat_env(rt: &Path) -> BTreeMap<String, OsString> {
        let mut m = BTreeMap::new();
        m.insert(
            "PATH".to_string(),
            OsString::from(format!(
                "{0}/python/bin:{0}/git/cysbin:{0}/git/bin:/usr/bin:/bin",
                rt.display()
            )),
        );
        m
    }

    fn g(m: &BTreeMap<String, OsString>, k: &str) -> Option<String> {
        m.get(k).map(|v| v.to_string_lossy().into_owned())
    }

    fn plant_clt(dir: &Path, tool: &str) {
        exe(&dir.join("usr/bin").join(tool));
    }

    // ── ① ──
    #[test]
    fn non_macos_is_untouched() {
        let mut f = fx("nonmac");
        f.ctx.os = "linux".into();
        let mut env = seat_env(&f.rt);
        env.insert(ENV_PATH_HELPER_ROOT.into(), "x".into());
        let before = env.clone();
        assert_eq!(seat_path_verdict(&f.ctx, &mut env), None);
        assert_eq!(env, before, "비-macOS 에서 env 를 건드렸다");
    }

    // ── ② × CLT 있음 · 롤백 · 경로 꼴 ──
    #[test]
    fn inherited_ours_is_scrubbed_before_every_verdict() {
        let f = fx("scrub");
        let ours_marker = f.root.join("elsewhere").into_os_string();
        let shapes: Vec<(OsString, Option<OsString>)> = vec![
            (ours_marker.clone(), Some(ours_marker.clone())), // 표식 같음
            (f.ctx.base.join("abcdef0123456789").into_os_string(), None), // 경로 꼴(표식 떨어짐)
            (f.ctx.base.join("abcdef0123456789.g3").into_os_string(), None),
            (f.ctx.base.join("abcdef0123456789.x1-2").into_os_string(), None),
            (OsString::new(), None), // 빈 값
        ];
        for (val, marker) in shapes {
            // CLT 있음 → 지우고 NotNeeded.
            let mut c = f.ctx.clone();
            let clt = f.root.join(format!("clt-{}", unique_suffix()));
            plant_clt(&clt, "python3");
            plant_clt(&clt, "git");
            c.dev_dir_candidates = vec![clt];
            let mut env = seat_env(&f.rt);
            env.insert(ENV_PATH_HELPER_ROOT.into(), val.clone());
            if let Some(m) = &marker {
                env.insert(ENV_CYS_PATH_HELPER_ROOT.into(), m.clone());
            }
            assert_eq!(seat_path_verdict(&c, &mut env), Some(SeatPathVerdict::NotNeeded { unfixed: vec![] }), "{val:?}");
            assert_eq!(g(&env, ENV_PATH_HELPER_ROOT), None, "{val:?} 우리 값이 남았다");
            assert_eq!(g(&env, ENV_CYS_PATH_HELPER_ROOT), None);
            assert_eq!(g(&env, ENV_CYS_SEAT_PATH_VERDICT).as_deref(), Some("not-needed"));
            // 롤백 → 지우고 RolledBack.
            let mut c2 = f.ctx.clone();
            c2.rollback = true;
            let mut env = seat_env(&f.rt);
            env.insert(ENV_PATH_HELPER_ROOT.into(), val.clone());
            if let Some(m) = &marker {
                env.insert(ENV_CYS_PATH_HELPER_ROOT.into(), m.clone());
            }
            assert_eq!(seat_path_verdict(&c2, &mut env), Some(SeatPathVerdict::RolledBack));
            assert_eq!(g(&env, ENV_PATH_HELPER_ROOT), None, "롤백 전에 우리 값을 안 걷었다");
            assert_eq!(g(&env, ENV_CYS_SEAT_PATH_VERDICT).as_deref(), Some("rolled-back"));
            // CLT 없음 → 지우고 새 root(Applied).
            let mut env = seat_env(&f.rt);
            env.insert(ENV_PATH_HELPER_ROOT.into(), val.clone());
            if let Some(m) = &marker {
                env.insert(ENV_CYS_PATH_HELPER_ROOT.into(), m.clone());
            }
            match seat_path_verdict(&f.ctx, &mut env) {
                Some(SeatPathVerdict::Applied { root, .. }) => {
                    assert_ne!(root.as_os_str(), val.as_os_str());
                    assert_eq!(root.parent(), Some(f.ctx.base.as_path()));
                    assert_eq!(g(&env, ENV_PATH_HELPER_ROOT), Some(root.to_string_lossy().into()));
                    assert_eq!(g(&env, ENV_CYS_PATH_HELPER_ROOT), Some(root.to_string_lossy().into()));
                }
                other => panic!("{val:?} → {other:?}"),
            }
        }
    }

    #[test]
    fn boot_scrub_uses_the_same_identification() {
        let base = PathBuf::from("/h/.cys/path-helper-root");
        let mk = |pairs: &[(&str, &str)]| -> BTreeMap<String, OsString> {
            pairs.iter().map(|(k, v)| (k.to_string(), OsString::from(*v))).collect()
        };
        // 표식 같음.
        let mut e = mk(&[(ENV_PATH_HELPER_ROOT, "/x/r"), (ENV_CYS_PATH_HELPER_ROOT, "/x/r"), (ENV_CYS_SEAT_PATH_VERDICT, "applied:git")]);
        assert_eq!(scrub_boot_env(&mut e, &base), vec![ENV_PATH_HELPER_ROOT, ENV_CYS_PATH_HELPER_ROOT, ENV_CYS_SEAT_PATH_VERDICT]);
        assert!(e.is_empty());
        // 표식만 떨어진 우리 root(경로 꼴) — codex r4 minor.
        let mut e = mk(&[(ENV_PATH_HELPER_ROOT, "/h/.cys/path-helper-root/0123456789abcdef.g2")]);
        assert_eq!(scrub_boot_env(&mut e, &base), vec![ENV_PATH_HELPER_ROOT]);
        // 사용자 값 = 무접촉(진단 표지만 지움).
        let mut e = mk(&[(ENV_PATH_HELPER_ROOT, "/mine"), (ENV_CYS_SEAT_PATH_VERDICT, "user-root")]);
        assert_eq!(scrub_boot_env(&mut e, &base), vec![ENV_CYS_SEAT_PATH_VERDICT]);
        assert_eq!(g(&e, ENV_PATH_HELPER_ROOT).as_deref(), Some("/mine"));
        // 아무것도 없음.
        let mut e = mk(&[("OTHER", "1")]);
        assert!(scrub_boot_env(&mut e, &base).is_empty());
        assert_eq!(e.len(), 1);
    }

    /// 홈을 모를 때(base 없음)의 ② — 짝 표식 같음·빈 값만 걷고 경로 꼴·사용자 값은 그대로(codex 코드 r3 시험 빈칸).
    #[test]
    fn scrub_without_home_uses_marker_and_empty_only() {
        let mk = |pairs: &[(&str, &str)]| -> BTreeMap<String, OsString> {
            pairs.iter().map(|(k, v)| (k.to_string(), OsString::from(*v))).collect()
        };
        let mut e = mk(&[(ENV_PATH_HELPER_ROOT, "/x/r"), (ENV_CYS_PATH_HELPER_ROOT, "/x/r")]);
        assert_eq!(scrub_inherited_ours_opt(&mut e, None), (true, true));
        assert!(e.is_empty());
        let mut e = mk(&[(ENV_PATH_HELPER_ROOT, "")]);
        assert_eq!(scrub_inherited_ours_opt(&mut e, None), (true, false));
        assert!(e.is_empty());
        let mut e = mk(&[(ENV_PATH_HELPER_ROOT, "/h/.cys/path-helper-root/abc")]);
        assert_eq!(scrub_inherited_ours_opt(&mut e, None), (false, false), "base 를 모르면 경로 꼴로는 못 가린다");
        assert_eq!(g(&e, ENV_PATH_HELPER_ROOT).as_deref(), Some("/h/.cys/path-helper-root/abc"));
        let mut e = mk(&[(ENV_PATH_HELPER_ROOT, "/mine"), (ENV_CYS_PATH_HELPER_ROOT, "/other")]);
        assert_eq!(scrub_inherited_ours_opt(&mut e, None), (false, true));
        assert_eq!(g(&e, ENV_PATH_HELPER_ROOT).as_deref(), Some("/mine"));
    }

    #[test]
    fn rollback_knobs_are_strict_zero() {
        assert!(mac_seat_path_rollback_from(Some("0"), None));
        assert!(mac_seat_path_rollback_from(None, Some("0")));
        assert!(!mac_seat_path_rollback_from(None, None));
        assert!(!mac_seat_path_rollback_from(Some("1"), Some("false")));
        assert!(!mac_seat_path_rollback_from(Some(" 0"), Some("")));
    }

    // ── ④ ──
    #[test]
    fn user_root_is_respected_and_stray_marker_dropped() {
        let f = fx("user");
        let mut env = seat_env(&f.rt);
        env.insert(ENV_PATH_HELPER_ROOT.into(), "/Users/someone/myroot".into());
        env.insert(ENV_CYS_PATH_HELPER_ROOT.into(), "/other".into());
        assert_eq!(seat_path_verdict(&f.ctx, &mut env), Some(SeatPathVerdict::UserRoot));
        assert_eq!(g(&env, ENV_PATH_HELPER_ROOT).as_deref(), Some("/Users/someone/myroot"));
        assert_eq!(g(&env, ENV_CYS_PATH_HELPER_ROOT), None, "값이 다른 짝 표식은 지워야 한다");
        assert_eq!(g(&env, ENV_CYS_SEAT_PATH_VERDICT).as_deref(), Some("user-root"));
        // base 의 손자(바로 아래 아님)는 우리 것이 아니다.
        let deeper = f.ctx.base.join("a").join("b");
        assert!(!is_our_path_helper_root(deeper.as_os_str(), None, &f.ctx.base));
        assert!(!is_our_path_helper_root(f.ctx.base.as_os_str(), None, &f.ctx.base));
    }

    // ── ⑤ ──
    #[test]
    fn partial_clt_and_missing_bundled_binaries() {
        // CLT 에 git 만 있음 → python3 만 고침.
        let f = fx("partial");
        let clt = f.root.join("clt");
        plant_clt(&clt, "git");
        let mut c = f.ctx.clone();
        c.dev_dir_candidates = vec![clt.clone()];
        let mut env = seat_env(&f.rt);
        match seat_path_verdict(&c, &mut env) {
            Some(SeatPathVerdict::Applied { fixed, unfixed, .. }) => {
                assert_eq!(fixed, vec!["python3"]);
                assert!(unfixed.is_empty());
                assert_eq!(g(&env, ENV_CYS_SEAT_PATH_VERDICT).as_deref(), Some("applied:python3"));
            }
            o => panic!("{o:?}"),
        }
        // DEVELOPER_DIR = 좌석 최종 env 값으로 판정한다.
        let mut env = seat_env(&f.rt);
        let dd = f.root.join("dd");
        plant_clt(&dd, "python3");
        plant_clt(&dd, "git");
        env.insert("DEVELOPER_DIR".into(), dd.into_os_string());
        assert_eq!(seat_path_verdict(&f.ctx, &mut env), Some(SeatPathVerdict::NotNeeded { unfixed: vec![] }));

        // 진짜 git(libexec)이 없는 손상 runtime → git 은 못 고친 도구.
        let f2 = fx("broken");
        std::fs::remove_file(f2.rt.join("git/libexec/git-core/git")).unwrap();
        let mut env = seat_env(&f2.rt);
        match seat_path_verdict(&f2.ctx, &mut env) {
            Some(SeatPathVerdict::Applied { fixed, unfixed, .. }) => {
                assert_eq!(fixed, vec!["python3"]);
                assert_eq!(unfixed, vec!["git"]);
            }
            o => panic!("{o:?}"),
        }
        // 동봉 실행 파일이 하나도 없음 → NotNeeded.
        let f3 = fx("empty");
        std::fs::remove_file(f3.rt.join("python/bin/python3")).unwrap();
        std::fs::remove_file(f3.rt.join("git/cysbin/git")).unwrap();
        let mut env = seat_env(&f3.rt);
        assert_eq!(
            seat_path_verdict(&f3.ctx, &mut env),
            Some(SeatPathVerdict::NotNeeded { unfixed: vec!["python3", "git"] }),
            "동봉본이 없어 못 고친 도구가 판정에 남아야 한다"
        );
        // runtime 없음(개발 빌드) → NotNeeded.
        let mut c4 = f3.ctx.clone();
        c4.runtime_root = None;
        let mut env = seat_env(&f3.rt);
        assert_eq!(
            seat_path_verdict(&c4, &mut env),
            Some(SeatPathVerdict::NotNeeded { unfixed: vec!["python3", "git"] })
        );
    }

    // ── ⑥ ──
    #[test]
    fn unsafe_path_chars_are_excluded() {
        // 기대 글자를 시험에 직접 적는다(상수 표에서 글자를 빼면 잡히게 · Fable 코드 r2).
        let want = ['`', '\\', '"', '$', ':', '\n', '\r', '\'', '\t', '*', '?', '['];
        for ch in want {
            assert!(UNSAFE_PATH_CHARS.contains(&ch), "글자 {ch:?} 가 표에서 빠졌다");
        }
        for ch in want {
            let f = fx("chars");
            let rt = f.root.join(format!("ap{ch}p")).join("runtime");
            make_rt(&rt, true, true, true);
            let mut c = f.ctx.clone();
            c.runtime_root = Some(rt.clone());
            let mut env = seat_env(&f.rt);
            assert_eq!(
                seat_path_verdict(&c, &mut env),
                Some(SeatPathVerdict::UnsafePath),
                "글자 {ch:?} 를 통과시켰다"
            );
            assert_eq!(g(&env, ENV_PATH_HELPER_ROOT), None);
        }
        assert!(path_chars_safe(Path::new("/Applications/cys app (2).app/x")));
        assert!(!path_chars_safe(Path::new("/Applications/My  Apps/cys.app/x")), "연속 공백(IFS 접기)");
        let f = fx("dblspace");
        let rt = f.root.join("My  Apps").join("runtime");
        make_rt(&rt, true, true, true);
        let mut c = f.ctx.clone();
        c.runtime_root = Some(rt);
        let mut env = seat_env(&f.rt);
        assert_eq!(seat_path_verdict(&c, &mut env), Some(SeatPathVerdict::UnsafePath));
    }

    // ── paths_with_fix ──
    #[test]
    fn paths_with_fix_inserts_before_first_usr_bin() {
        let fix = vec!["/A".to_string(), "/B".to_string()];
        assert_eq!(
            paths_with_fix(b"/usr/local/bin\n/usr/bin\n/bin\n", &fix),
            b"/usr/local/bin\n/A\n/B\n/usr/bin\n/bin\n".to_vec()
        );
        assert_eq!(paths_with_fix(b"/bin\n", &fix), b"/A\n/B\n/bin\n".to_vec(), "/usr/bin 없음 = 맨 앞");
        assert_eq!(
            paths_with_fix(b"/x\n/usr/bin\n/usr/bin\n", &fix),
            b"/x\n/A\n/B\n/usr/bin\n/usr/bin\n".to_vec(),
            "여럿이면 첫 줄 앞 한 번"
        );
        assert_eq!(paths_with_fix(b"  /usr/bin  ", &fix), b"/A\n/B\n  /usr/bin  ".to_vec());
        assert_eq!(paths_with_fix(b"", &fix), b"/A\n/B\n".to_vec());
    }

    // ── 파서 ──
    #[test]
    fn parse_path_helper_output_shapes() {
        let o = parse_path_helper_output("PATH=\"/a:/b\"; export PATH;\n").unwrap();
        assert_eq!(o.path, vec!["/a", "/b"]);
        assert_eq!(o.manpath, None);
        let o = parse_path_helper_output(
            "PATH=\"/a:/d\\\"q:/e\\$x\"; export PATH;\nMANPATH=\"/m:\"; export MANPATH;\n",
        )
        .unwrap();
        assert_eq!(o.path, vec!["/a", "/d\"q", "/e$x"]);
        assert_eq!(o.manpath.as_deref(), Some("/m:"));
        assert_eq!(parse_path_helper_output(""), None);
        assert_eq!(parse_path_helper_output("garbage\n"), None);
        assert_eq!(parse_path_helper_output("PATH=\"/a\"; export PATH;\nrm -rf x\n"), None);
        assert_eq!(parse_path_helper_output("PATH=\"/a; export PATH;"), None);
        assert_eq!(parse_path_helper_output("PATH=\"/a\"; export PATH;\nPATH=\"/b\"; export PATH;"), None);
    }

    // ── 전체 비교 ──
    #[test]
    fn verify_full_comparison() {
        let o = |p: &str, m: Option<&str>| PathHelperOut {
            path: p.split(':').map(str::to_string).collect(),
            manpath: m.map(str::to_string),
        };
        let fix = vec!["/F".to_string()];
        let sys = o("/usr/local/bin:/usr/bin:/bin:/F:/start", None);
        assert_eq!(verify(&sys, &o("/usr/local/bin:/F:/usr/bin:/bin:/start", None), &fix), Ok(()));
        assert_eq!(verify(&sys, &o("/usr/local/bin:/F:/usr/bin:/bin:/start:/extra", None), &fix), Err("mismatch"), "성분 추가");
        assert_eq!(verify(&sys, &o("/usr/local/bin:/F:/usr/bin:/start", None), &fix), Err("mismatch"), "성분 삭제");
        assert_eq!(verify(&sys, &o("/F:/usr/bin:/usr/local/bin:/bin:/start", None), &fix), Err("mismatch"), "순서");
        assert_eq!(verify(&sys, &o("/usr/local/bin:/usr/bin:/F:/bin:/start", None), &fix), Err("order"));
        assert_eq!(verify(&sys, &o("/usr/local/bin:/usr/bin:/bin:/start", None), &fix), Err("mismatch"), "fix 없음");
        assert_eq!(verify(&sys, &o("/F:/usr/local/bin:/F:/usr/bin:/bin:/start", None), &fix), Err("mismatch"), "fix 두 번");
        assert_eq!(verify(&sys, &o("/usr/local/bin:/F:/usr/bin:/bin:/start", Some("/m")), &fix), Err("manpath"));
        let sysm = o("/usr/bin:/F", Some("/m"));
        assert_eq!(verify(&sysm, &o("/F:/usr/bin", Some("/m")), &fix), Ok(()));
    }

    // ── 스냅숏 ──
    #[test]
    fn snapshot_reads_what_path_helper_reads() {
        let root = scratch("snap");
        let etc = root.join("etc");
        std::fs::create_dir_all(etc.join("paths.d").join("subdir")).unwrap();
        std::fs::create_dir_all(etc.join("manpaths.d")).unwrap();
        std::fs::write(etc.join("paths"), "/usr/bin\n").unwrap();
        std::fs::write(etc.join("manpaths"), "/usr/share/man\n").unwrap();
        std::fs::write(etc.join("paths.d").join(".dot"), "/dot\n").unwrap();
        std::fs::write(etc.join("paths.d").join("b"), "/b\n").unwrap();
        std::fs::write(etc.join("manpaths.d").join("m"), "/m\n").unwrap();
        std::os::unix::fs::symlink(etc.join("paths.d").join("b"), etc.join("paths.d").join("link")).unwrap();
        let locked = etc.join("paths.d").join("locked");
        std::fs::write(&locked, "/locked\n").unwrap();
        std::fs::set_permissions(&locked, std::fs::Permissions::from_mode(0o000)).unwrap();
        let readable_anyway = std::fs::read(&locked).is_ok(); // root 로 돌면 읽힌다
        let s = Snapshot::from_system(&etc, &["/F".to_string()]).unwrap();
        let keys: Vec<String> = s.files.keys().map(|k| String::from_utf8_lossy(k).into_owned()).collect();
        let mut want = vec!["manpaths", "manpaths.d/m", "paths", "paths.d/.dot", "paths.d/b"];
        if readable_anyway {
            want.push("paths.d/locked");
            want.sort();
        }
        assert_eq!(keys, want, "점 파일 포함 · 심링크·하위 dir 제외 · 읽기 오류 건너뜀");
        assert_eq!(s.files[&b"paths".to_vec()], b"/F\n/usr/bin\n".to_vec());
        std::fs::set_permissions(&locked, std::fs::Permissions::from_mode(0o644)).unwrap();
        // 직렬화는 결정론 · 바이트가 바뀌면 이름이 바뀐다.
        let s2 = Snapshot::from_system(&etc, &["/F".to_string()]).unwrap();
        if !readable_anyway {
            assert_ne!(s.hash16(), s2.hash16(), "읽기 가능해진 파일이 스냅숏에 안 들어갔다");
        }
        assert_eq!(s2.hash16(), Snapshot::from_system(&etc, &["/F".to_string()]).unwrap().hash16());
        assert_eq!(s2.hash16().len(), 16);
        // 빈 /etc(파일 없음)도 스냅숏이 된다.
        let e2 = root.join("empty-etc");
        std::fs::create_dir_all(&e2).unwrap();
        let s3 = Snapshot::from_system(&e2, &["/F".to_string()]).unwrap();
        assert_eq!(s3.files.len(), 1);
    }

    // ── 세대 게시 ──
    #[test]
    fn generations_create_reuse_and_skip_damaged() {
        let root = scratch("gen");
        let etc = root.join("etc");
        std::fs::create_dir_all(&etc).unwrap();
        std::fs::write(etc.join("paths"), "/usr/bin\n").unwrap();
        let base = root.join("base");
        let snap = Snapshot::from_system(&etc, &["/F".to_string()]).unwrap();
        let h = snap.hash16();
        let p1 = publish_or_reuse(&base, &snap).unwrap();
        assert_eq!(p1, base.join(&h));
        assert_eq!(publish_or_reuse(&base, &snap).unwrap(), p1, "재사용");
        // 손상(파일 추가) → 다음 세대 게시 · 손상 세대는 그대로.
        std::fs::write(p1.join("etc").join("paths.d").join("junk"), "/junk\n").unwrap();
        let p2 = publish_or_reuse(&base, &snap).unwrap();
        assert_eq!(p2, base.join(format!("{h}.g2")));
        assert!(p1.join("etc/paths.d/junk").exists(), "손상 세대를 지웠다/옮겼다");
        // 두 실행기 교차 — 같은 손상을 본 두 번째 실행기는 이미 게시된 g2 를 재사용한다.
        assert_eq!(publish_or_reuse(&base, &snap).unwrap(), p2);
        // g2 도 손상(바이트 변경) → g3.
        std::fs::write(p2.join("etc").join("paths"), "/evil\n").unwrap();
        assert_eq!(publish_or_reuse(&base, &snap).unwrap(), base.join(format!("{h}.g3")));
        // 임시 dir 남김 없음.
        let leftovers: Vec<_> = std::fs::read_dir(&base)
            .unwrap()
            .flatten()
            .filter(|e| e.file_name().to_string_lossy().starts_with(TMP_PREFIX))
            .collect();
        assert!(leftovers.is_empty());
    }

    #[test]
    fn generations_over_limit_get_unique_name_and_are_reused() {
        let root = scratch("genmax");
        let etc = root.join("etc");
        std::fs::create_dir_all(&etc).unwrap();
        std::fs::write(etc.join("paths"), "/usr/bin\n").unwrap();
        let base = root.join("base");
        let snap = Snapshot::from_system(&etc, &["/F".to_string()]).unwrap();
        let h = snap.hash16();
        std::fs::create_dir_all(&base).unwrap();
        for g in 1..=GENERATIONS_MAX {
            let n = if g == 1 { h.clone() } else { format!("{h}.g{g}") };
            std::fs::create_dir_all(base.join(n).join("bad")).unwrap();
        }
        let x = publish_or_reuse(&base, &snap).unwrap();
        assert!(x.file_name().unwrap().to_string_lossy().starts_with(&format!("{h}.x")), "{x:?}");
        assert_eq!(publish_or_reuse(&base, &snap).unwrap(), x, ".x 도 재사용 훑기에 든다");
    }

    #[test]
    fn write_failure_is_error_write() {
        let root = scratch("ro");
        let etc = root.join("etc");
        std::fs::create_dir_all(&etc).unwrap();
        std::fs::write(etc.join("paths"), "/usr/bin\n").unwrap();
        let base = root.join("base");
        std::fs::create_dir_all(&base).unwrap();
        std::fs::set_permissions(&base, std::fs::Permissions::from_mode(0o555)).unwrap();
        let snap = Snapshot::from_system(&etc, &["/F".to_string()]).unwrap();
        let probe = std::fs::create_dir(base.join("probe")).is_ok(); // root 로 돌면 써진다
        if !probe {
            assert_eq!(publish_or_reuse(&base, &snap), Err("write"));
        }
        std::fs::set_permissions(&base, std::fs::Permissions::from_mode(0o755)).unwrap();
    }

    #[test]
    fn concurrent_publishers_agree() {
        let root = scratch("race");
        let etc = root.join("etc");
        std::fs::create_dir_all(&etc).unwrap();
        std::fs::write(etc.join("paths"), "/usr/bin\n").unwrap();
        let base = root.join("base");
        let snap = Snapshot::from_system(&etc, &["/F".to_string()]).unwrap();
        for _ in 0..20 {
            let _ = std::fs::remove_dir_all(&base);
            let hs: Vec<_> = (0..2)
                .map(|_| {
                    let (b, s) = (base.clone(), snap.clone());
                    std::thread::spawn(move || publish_or_reuse(&b, &s))
                })
                .collect();
            let rs: Vec<_> = hs.into_iter().map(|h| h.join().unwrap().unwrap()).collect();
            assert_eq!(rs[0], rs[1], "두 게시자가 다른 dir 을 골랐다");
            let n = std::fs::read_dir(&base).unwrap().flatten().count();
            assert_eq!(n, 1, "세대가 둘 생겼거나 임시 dir 이 남았다");
        }
    }

    #[test]
    fn stale_tmp_is_cleaned_fresh_tmp_kept() {
        let root = scratch("tmp");
        let base = root.join("base");
        let old = base.join(".tmp-1-1");
        let fresh = base.join(".tmp-2-2");
        let other = base.join("keepme");
        for d in [&old, &fresh, &other] {
            std::fs::create_dir_all(d).unwrap();
        }
        let past = SystemTime::now() - Duration::from_secs(3600);
        std::fs::File::open(&old).unwrap().set_modified(past).unwrap();
        std::fs::File::open(&other).unwrap().set_modified(past).unwrap();
        cleanup_stale_tmp(&base);
        assert!(!old.exists());
        assert!(fresh.exists());
        assert!(other.exists(), "임시 dir 아닌 것을 지웠다");
    }

    // ── ⑧ 관측 ──
    #[test]
    fn verify_failures_have_fixed_reasons() {
        let f = fx("vf");
        // 시간 초과(재시도 1회 포함).
        let mut c = f.ctx.clone();
        c.path_helper = script(&f.root, "slow_ph", "#!/bin/sh\nsleep 5\n");
        c.verify_timeout = Duration::from_millis(150);
        let t0 = Instant::now();
        let mut env = seat_env(&f.rt);
        assert_eq!(seat_path_verdict(&c, &mut env), Some(SeatPathVerdict::VerifyFailed("timeout")));
        assert!(t0.elapsed() < Duration::from_secs(3));
        assert_eq!(g(&env, ENV_PATH_HELPER_ROOT), None);
        assert_eq!(g(&env, ENV_CYS_SEAT_PATH_VERDICT).as_deref(), Some("verify-failed:timeout"));
        // 실행 불가.
        let mut c = f.ctx.clone();
        c.path_helper = f.root.join("missing_ph");
        let mut env = seat_env(&f.rt);
        assert_eq!(seat_path_verdict(&c, &mut env), Some(SeatPathVerdict::VerifyFailed("exec")));
        // root 를 무시하는 path_helper(미래 macOS 가 env 를 버림) → 동봉 dir 이 /usr/bin 뒤 = order.
        let mut c = f.ctx.clone();
        let ignore = script(&f.root, "ignore_root_ph.sh", "");
        let real = std::fs::read_to_string(&f.ctx.path_helper).unwrap();
        std::fs::write(&ignore, real.replace("[ -n \"$PATH_HELPER_ROOT\" ] && ", "false && ")).unwrap();
        c.path_helper = ignore;
        let mut env = seat_env(&f.rt);
        assert_eq!(seat_path_verdict(&c, &mut env), Some(SeatPathVerdict::VerifyFailed("order")));
        assert_eq!(g(&env, ENV_PATH_HELPER_ROOT), None, "확인 실패인데 env 를 실었다");
        // 출력이 다르게 생김 → exec.
        let mut c = f.ctx.clone();
        c.path_helper = script(&f.root, "junk_ph", "#!/bin/sh\necho 'setenv PATH /x;'\n");
        let mut env = seat_env(&f.rt);
        assert_eq!(seat_path_verdict(&c, &mut env), Some(SeatPathVerdict::VerifyFailed("exec")));
    }

    /// 부모가 먼저 끝나고 자손이 stdout 을 쥐고 남아도 같은 시한에서 끊는다(codex 코드 r1 minor).
    #[test]
    fn verify_deadline_covers_stdout_held_by_a_grandchild() {
        let f = fx("grandchild");
        let mut c = f.ctx.clone();
        c.path_helper = script(&f.root, "fork_ph", "#!/bin/sh\n/bin/sleep 5 &\nexit 0\n");
        c.verify_timeout = Duration::from_millis(200);
        let t0 = Instant::now();
        let mut env = seat_env(&f.rt);
        assert_eq!(seat_path_verdict(&c, &mut env), Some(SeatPathVerdict::VerifyFailed("timeout")));
        assert!(t0.elapsed() < Duration::from_secs(2), "자손이 쥔 stdout 을 시한 없이 기다렸다: {:?}", t0.elapsed());
    }

    /// 변이 생존 보강(Fable 코드 r1): path_helper 자식 env 는 비운다 · 종료 코드 검사 · 시간 초과 때 자기 그룹(자손 포함)을 끝낸다.
    #[test]
    fn path_helper_child_env_exit_code_and_group_kill() {
        let f = fx("childenv");
        let real = std::fs::read_to_string(&f.ctx.path_helper).unwrap();
        // ⓐ env_clear: HOME 이 보이면 실패하는 path_helper.
        let mut c = f.ctx.clone();
        c.path_helper = script(&f.root, "noenv_ph", &real.replacen("#!/bin/sh\n", "#!/bin/sh\n[ -n \"$HOME$USER\" ] && exit 3\n", 1));
        let mut env = seat_env(&f.rt);
        assert!(matches!(seat_path_verdict(&c, &mut env), Some(SeatPathVerdict::Applied { .. })), "path_helper 자식에 데몬 env 가 샜다");
        // ⓑ 종료 코드: 맞는 출력을 내도 비0 이면 exec.
        let mut c = f.ctx.clone();
        c.path_helper = script(&f.root, "rc1_ph", &real.replace("exit 0\n", "exit 1\n"));
        let mut env = seat_env(&f.rt);
        assert_eq!(seat_path_verdict(&c, &mut env), Some(SeatPathVerdict::VerifyFailed("exec")));
        // ⓒ 그룹 종료: 시간 초과 때 자손도 끝난다.
        let pidf = f.root.join("gc.pid");
        let mut c = f.ctx.clone();
        c.path_helper = script(
            &f.root,
            "gc_ph",
            &format!("#!/bin/sh\n/bin/sleep 30 &\necho $! > '{}'\nwait\n", pidf.display()),
        );
        c.verify_timeout = Duration::from_millis(200);
        let mut env = seat_env(&f.rt);
        assert_eq!(seat_path_verdict(&c, &mut env), Some(SeatPathVerdict::VerifyFailed("timeout")));
        std::thread::sleep(Duration::from_millis(200));
        let pid: i32 = std::fs::read_to_string(&pidf).unwrap().trim().parse().unwrap();
        // SAFETY: 신호 0 = 존재 확인만.
        let alive = unsafe { libc::kill(pid, 0) } == 0;
        assert!(!alive, "시간 초과 뒤 자손 {pid} 이 살아 있다 — 자기 그룹 종료가 안 됐다");
    }

    /// 좌석 MANPATH 는 path_helper 두 호출 모두에 그대로 간다(Fable·codex 코드 r1·r2 — 전달 변이 생존).
    #[test]
    fn manpath_is_passed_to_both_path_helper_calls() {
        let f = fx("manpath");
        let real = std::fs::read_to_string(&f.ctx.path_helper).unwrap();
        let mut c = f.ctx.clone();
        // 받은 MANPATH 를 파일에 남기고, 없으면 실패하는 path_helper(호출마다 한 줄).
        let log = f.root.join("manpath.log");
        c.path_helper = script(
            &f.root,
            "man_ph",
            &real.replacen(
                "#!/bin/sh\n",
                &format!("#!/bin/sh\nprintf '%s\\n' \"${{MANPATH-<none>}}\" >> '{}'\n[ -z \"${{MANPATH+x}}\" ] && exit 4\n", log.display()),
                1,
            ),
        );
        let mut env = seat_env(&f.rt);
        env.insert("MANPATH".into(), "/m1:/m2".into());
        assert!(matches!(seat_path_verdict(&c, &mut env), Some(SeatPathVerdict::Applied { .. })));
        let got = std::fs::read_to_string(&log).unwrap();
        assert_eq!(got.lines().collect::<Vec<_>>(), vec!["/m1:/m2", "/m1:/m2"], "두 호출에 좌석 MANPATH 가 안 갔다");
        // MANPATH 없는 좌석 = 두 호출 모두 MANPATH 없음.
        let mut c2 = f.ctx.clone();
        let log2 = f.root.join("manpath2.log");
        c2.path_helper = script(
            &f.root,
            "man_ph2",
            &real.replacen("#!/bin/sh\n", &format!("#!/bin/sh\nprintf '%s\\n' \"${{MANPATH-<none>}}\" >> '{}'\n", log2.display()), 1),
        );
        let mut env = seat_env(&f.rt);
        assert!(matches!(seat_path_verdict(&c2, &mut env), Some(SeatPathVerdict::Applied { .. })));
        assert_eq!(std::fs::read_to_string(&log2).unwrap().lines().collect::<Vec<_>>(), vec!["<none>", "<none>"]);
    }

    /// 세대 dir 최상위 엄격 검사 — `etc` 밖에 무엇이 있으면 같은 세대로 보지 않는다.
    #[test]
    fn generation_top_level_must_be_only_etc() {
        let root = scratch("top");
        let etc = root.join("etc");
        std::fs::create_dir_all(&etc).unwrap();
        std::fs::write(etc.join("paths"), "/usr/bin\n").unwrap();
        let base = root.join("base");
        let snap = Snapshot::from_system(&etc, &["/F".to_string()]).unwrap();
        let p1 = publish_or_reuse(&base, &snap).unwrap();
        std::fs::write(p1.join("extra"), "x").unwrap();
        let p2 = publish_or_reuse(&base, &snap).unwrap();
        assert_ne!(p1, p2, "최상위에 남의 파일이 있는 세대를 재사용했다");
    }

    /// 진짜 path_helper 출력 견본(macOS 27.2 실측 꼴) — env 에서 온 성분은 날것 · 파일 성분의 `"`·`$` 는 백슬래시.
    #[test]
    fn parser_accepts_real_output_sample() {
        let out = "PATH=\"/usr/local/bin:/System/Cryptexes/App/usr/bin:/fixA:/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin:/start\"; export PATH;\nMANPATH=\"/usr/share/man:/usr/local/share/man:/x/man\"; export MANPATH;\n";
        let o = parse_path_helper_output(out).unwrap();
        assert_eq!(o.path.len(), 9);
        assert_eq!(o.path[2], "/fixA");
        assert_eq!(o.manpath.as_deref(), Some("/usr/share/man:/usr/local/share/man:/x/man"));
    }

    /// 시간 초과는 그 자리에서 1회 다시 잰다(첫 호출만 매달리는 path_helper → 재시도로 Applied · 표적 변이 「재시도 끔」 을 잡는 시험).
    #[test]
    fn verify_retries_a_single_timeout() {
        let f = fx("retry");
        let real = std::fs::read_to_string(&f.ctx.path_helper).unwrap();
        let mark = f.root.join("first-call-done");
        let body = real.replacen(
            "#!/bin/sh\n",
            &format!("#!/bin/sh\nif [ ! -e '{m}' ]; then : > '{m}'; sleep 5; fi\n", m = mark.display()),
            1,
        );
        let mut c = f.ctx.clone();
        c.path_helper = script(&f.root, "flaky_ph", &body);
        // 부하가 큰 병렬 시험 중에도 정상 호출이 시한 안에 들게 여유를 둔다(첫 호출은 5초 잠 = 반드시 넘김).
        c.verify_timeout = Duration::from_millis(1500);
        let mut env = seat_env(&f.rt);
        match seat_path_verdict(&c, &mut env) {
            Some(SeatPathVerdict::Applied { .. }) => {}
            o => panic!("한 번 매달린 path_helper 를 다시 재지 않았다: {o:?}"),
        }
        assert!(mark.exists());
    }

    #[test]
    fn applied_happy_path_with_emulated_path_helper() {
        let f = fx("ok");
        let mut env = seat_env(&f.rt);
        let v = seat_path_verdict(&f.ctx, &mut env).unwrap();
        let SeatPathVerdict::Applied { root, fixed, unfixed } = v else { panic!("{v:?}") };
        assert_eq!(fixed, vec!["python3", "git"]);
        assert!(unfixed.is_empty());
        assert_eq!(g(&env, ENV_CYS_SEAT_PATH_VERDICT).as_deref(), Some("applied:python3,git"));
        let paths = std::fs::read_to_string(root.join("etc/paths")).unwrap();
        assert_eq!(
            paths,
            format!(
                "/usr/local/bin\n{0}/python/bin\n{0}/git/cysbin\n/usr/bin\n/bin\n/usr/sbin\n/sbin\n",
                f.rt.display()
            )
        );
        assert_eq!(std::fs::read_to_string(root.join("etc/paths.d/10-x")).unwrap(), "/opt/x/bin\n");
        // 두 번째 좌석 = 같은 root 재사용.
        let mut env2 = seat_env(&f.rt);
        match seat_path_verdict(&f.ctx, &mut env2) {
            Some(SeatPathVerdict::Applied { root: r2, .. }) => assert_eq!(r2, root),
            o => panic!("{o:?}"),
        }
        // 시스템 /etc/paths.d 가 바뀌면 새 dir(새 좌석부터).
        std::fs::write(f.ctx.etc_root.join("paths.d").join("20-y"), "/opt/y\n").unwrap();
        let mut env3 = seat_env(&f.rt);
        match seat_path_verdict(&f.ctx, &mut env3) {
            Some(SeatPathVerdict::Applied { root: r3, .. }) => assert_ne!(r3, root),
            o => panic!("{o:?}"),
        }
    }

    // ── 맥 전용: 진짜 /usr/libexec/path_helper · 진짜 /etc · 셸 끝에서 끝 ──
    #[cfg(target_os = "macos")]
    fn real_ctx(tag: &str) -> (Fx, BTreeMap<String, OsString>) {
        let mut f = fx(tag);
        f.ctx.etc_root = PathBuf::from(SYSTEM_ETC);
        f.ctx.path_helper = PathBuf::from(SYSTEM_PATH_HELPER);
        let rt = f.rt.clone();
        let mut env = seat_env(&rt);
        env.insert(
            "PATH".into(),
            format!(
                "{0}/python/bin:{0}/git/cysbin:{0}/git/bin:{0}/uv:{0}/node/bin:/usr/bin:/bin:/usr/sbin:/sbin",
                rt.display()
            )
            .into(),
        );
        (f, env)
    }

    #[cfg(target_os = "macos")]
    #[test]
    fn real_path_helper_verifies_and_login_shells_resolve_bundled() {
        let (f, mut env) = real_ctx("real");
        // MANPATH 가 있는 좌석 — ⑧ 의 「MANPATH ⓑ == ⓐ」 가 진짜 path_helper 로 한 번은 돈다(Fable 코드 r1).
        env.insert("MANPATH".into(), "/x/man".into());
        let v = seat_path_verdict(&f.ctx, &mut env).unwrap();
        let SeatPathVerdict::Applied { root, .. } = v else { panic!("진짜 path_helper 확인 실패: {v:?}") };
        let home = f.root.join("fakehome");
        std::fs::create_dir_all(&home).unwrap();
        std::fs::write(home.join(".zshrc"), "whence -p git python3 > \"$HOME/rc.out\"\n").unwrap();
        let git = f.rt.join("git/cysbin/git").to_string_lossy().into_owned();
        let py_dir = f.rt.join("python/bin").to_string_lossy().into_owned();
        let seat_path = env["PATH"].clone();
        let run = |with_root: bool, prog: &str, args: &[&str]| -> String {
            let mut c = crate::hidden_command(prog);
            c.args(args).env_clear().env("HOME", &home).env("PATH", &seat_path);
            if with_root {
                c.env(ENV_PATH_HELPER_ROOT, &root);
            }
            let o = c.output().unwrap();
            String::from_utf8_lossy(&o.stdout).trim().to_string()
        };
        // 기대값 = 로그인 셸 PATH 에서 처음 실행 가능한 것(설치기·Homebrew 줄은 그대로 앞 — 셔임만 이긴다).
        let first_hit = |path: &str, tool: &str| -> String {
            path.split(':')
                .map(|d| Path::new(d).join(tool))
                .find(|p| is_executable_file(p))
                .map(|p| p.to_string_lossy().into_owned())
                .unwrap_or_default()
        };
        let login_path = run(true, "/bin/zsh", &["-lc", "print -r -- $PATH"]);
        let comps: Vec<&str> = login_path.split(':').collect();
        let usr_bin = comps.iter().position(|c| *c == "/usr/bin").unwrap();
        for d in [py_dir.as_str(), f.rt.join("git/cysbin").to_str().unwrap()] {
            let i = comps.iter().position(|c| *c == d).unwrap_or(usize::MAX);
            assert!(i < usr_bin, "{d} 가 /usr/bin 앞이 아니다: {login_path}");
        }
        let want_git = first_hit(&login_path, "git");
        let want_py = first_hit(&login_path, "python3");
        assert_ne!(want_git, "/usr/bin/git");
        assert_ne!(want_py, "/usr/bin/python3");
        assert_eq!(want_git, git, "이 맥 /usr/bin 앞에 다른 git 이 있다 — 시험 전제 확인");
        let cases: [(&str, &[&str]); 5] = [
            ("/bin/zsh", &["-lc", "whence -p git"]),
            ("/bin/zsh", &["-c", "-l", "whence -p git"]),
            ("/bin/bash", &["-lc", "command -v git"]),
            ("/bin/sh", &["-lc", "command -v git"]),
            ("/bin/zsh", &["-lc", "/bin/zsh -lc 'whence -p git'"]),
        ];
        for (prog, args) in cases {
            assert_eq!(run(true, prog, args), git, "{prog} {args:?}");
            assert_eq!(run(false, prog, args), "/usr/bin/git", "대조군 {prog} {args:?}");
        }
        assert_eq!(run(true, "/bin/zsh", &["-lc", "whence -p python3"]), want_py);
        // 대화형 로그인 좌석(zsh -l -i) — 사용자 .zshrc 안에서 본 해소.
        let _ = run(true, "/bin/zsh", &["-l", "-i", "-c", "true"]);
        let rc = std::fs::read_to_string(home.join("rc.out")).unwrap();
        assert_eq!(rc.lines().collect::<Vec<_>>(), vec![git.as_str(), want_py.as_str()]);
        // man 경로 불변.
        let man_a = run(false, "/bin/zsh", &["-lc", "echo ${MANPATH-unset}"]);
        let man_b = run(true, "/bin/zsh", &["-lc", "echo ${MANPATH-unset}"]);
        assert_eq!(man_a, man_b);
    }
}
