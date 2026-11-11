//! agy(Antigravity CLI) 좌석 문 — cysr 이 agy 좌석을 띄우는 길을 **기본 닫음** · 사람이 화면에서만 연다.
//!
//! ★왜(TICKET=cysr-agy-policy-exposure · 설계 = 저장소 뿌리 `DESIGN-agy-policy-exposure.md`):
//!   구글 Antigravity FAQ(2026-11-11 재열람) 「Wrapping agy inside third-party coding agents or applications …
//!   is not supported under consumer plans.」 · 약관 6항 「Using third party software … to access the Service … is a
//!   breach of this Agreement … grounds for suspension or termination」. cysr 의 「제미나이 검토자」 = cysr 이 agy 를
//!   자기 창에 띄우고 지침을 타이핑해 넣고 Claude 지휘자가 계속 지시를 넣는 꼴이라 **개인 요금제 사용자의 구글 계정이
//!   정지될 수 있다**. 그러나 기업 요금제 등 허용된 환경의 전문가는 써야 하므로 기능을 지우지 않고 **기본값만 닫는다**.
//!
//! ★문을 여는 길은 하나 — 앱 화면(명령 팔레트 → 확인 창에서 경고 문구를 읽고 [열기])이 [`write_door`] 로 문 파일을
//!   쓴다. **`cys` CLI·데몬·팩 스크립트·스킬·복원기에는 쓰기 경로가 없다**(이 모듈 시험 `only_the_gui_writes_the_door`
//!   가 소스로 고정). 환경 변수로는 열리지 않는다 — 환경 변수는 Claude 가 명령 앞에 한 줄 붙여 열 수 있고, 여는
//!   순간 사람에게 경고를 보일 자리가 없기 때문이다(시험 `env_never_opens_the_door`).
//!
//! ★정직한 한계(operator.token 과 같은 등급 · 독립 검증 966 · codex 3R 반영): 이것은 **보안 경계가 아니라 실수 경로 차단**이다.
//!   ① 같은 OS 사용자로 도는 프로세스는 문 파일을 직접 쓸 수 있다(표지 값은 공개 상수) — 팩 훅 `guard.sh` 는 평소 명령의 쓰기만 막는다.
//!   ② 문 자리는 `home_dir()`(유닉스 = `HOME` 우선)이다 — `HOME` 을 바꾸면 다른 폴더의 문을 보지만 그 문 파일을 쓰는 단계가 ①의 훅에 걸린다
//!      (환경 변수 **하나만으로** 열리는 길은 없다 · 시험 `env_never_opens_the_door` 의 범위). 경로를 계정 홈에 고정하지 않은 까닭 =
//!      격리 시험(하네스·단위)이 `HOME` 으로 격리하고, 윈도우 홈도 환경 변수다.
//!   ③ 판정은 **명령 문자열**을 읽는다 — 기계 입구는 낱말 검사(셸 무해석 · 이름이 글자로 있으면 어떤 꼴이든 거부)에 실체 한 단계 확인
//!      (심링크 · 셸에 넘긴·셔뱅 스크립트 파일 한 번 읽기 · r6)을 더한다. 남는 것(두 단계 이상 간접·실행 중 조립·별칭·사본·맨 셸 좌석에
//!      글자로 쳐 넣기 · guard 의 꼬아 쓰기)은 `docs/agy-door-evidence/ENTRY-MODES.md` §6 「이 판에서 막지 않는 것」 한 곳에 적는다.
//!   실행 시점 차단(실행 파일 실체 감시)·앱 서명에 묶은 문은 다음 판 설계 과제(master 1.1.15 범위 판단 · USER-MANUAL 「알려진 한계」).
//!
//! leaf 모듈 — cys 도메인 모듈에 의존하지 않는다(`home_dir` 만 · 판정은 순수 함수).

use std::path::{Path, PathBuf};

/// 거부 사유 코드 — `cys agent-detect` 의 reason 머리 · 기동 거부 오류 문자열 머리 · 복원 건너뜀 줄에 같은 낱말.
pub const REFUSE_CODE: &str = "agy_consumer_policy";

/// 기동 거부 종료 코드(launch-agent) — 성공(0)·실패(1)·관문 보류(78)와 다른 전용 값. 복원·부트 소비부가 이것을
/// 「실패」가 아니라 「정책상 건너뜀」으로 읽는다(76 = 저장소 전수 grep 미사용 값).
pub const EXIT_AGY_POLICY_REFUSED: i32 = 76;

/// 문 파일 이름(`~/.cys/` 아래). 팩 훅 `guard.sh` 가 이 이름을 쓰기 금지 대상으로 안다 — 바꾸면 그 훅도 함께.
pub const DOOR_FILE: &str = "agy-seat-door.json";

/// 문 파일이 「사람이 경고를 읽고 열었다」는 표지 — 이 값이 정확히 있어야만 열림이다(빈 파일·손으로 만든 `{}` 는 닫힘).
pub const DOOR_ACK: &str = "agy-consumer-plan-warning-v1";

/// 여는 순간 사람에게 보이는 경고 — 앱 확인 창 본문의 **유일한 정본**(src-tauri `agy_seat_door_warning` 가 그대로 넘긴다 · UI 사본 0).
pub const OPEN_WARNING: &str = "개인 요금제(무료·Google AI Pro·Ultra)로 로그인한 agy 를 cysr 이 띄우고 Claude 가 부리면, \
구글 약관상 계정이 정지될 수 있습니다. 기업 요금제(Gemini Enterprise 등)처럼 이런 사용이 허용된 경우에만 여세요. \
(Gemini API 열쇠로 agy 가 아닌 다른 프로그램을 쓰는 경우는 이 문과 상관없습니다.)";

// ── 판정 방식은 둘이다(TICKET=cysr-agy-door-r5 · codex 4R 처분 · 경계 표 = `docs/agy-door-evidence/ENTRY-MODES.md`) ──
//   ① 기계 입구(일정·채널·계정 어댑터·launch-agent/restore/boot 의 어댑터 cmd·new-surface --cmd·round-log·phoenix 오라클) =
//      [`names_agy`] **낱말 검사** — 셸 구조를 해석하지 않는다. 따옴표·괄호·역슬래시·경로 구분자를 전부 구분자로 보고,
//      agy 실행 파일 이름과 같은 낱말이 **어디에든** 있으면 agy. 인용·치환·래퍼(call·start·watch·flock …) 우회가 성립하지
//      않는 대신 거짓 양성(프롬프트 속 「agy」 낱말)을 받아들인다 — 거부 글이 까닭과 푸는 법을 말한다.
//   ② 에이전트 자기 Bash(guard)·`cys run -- <argv>` = [`runs_agy`] **실행 자리 검사** — 사람·에이전트가 그 자리에서 쓰는
//      문장이라 프롬프트(`claude -p agy`)를 막지 않는다. 따옴표 속 치환 등 남는 우회는 「알려진 한계」(선의의 실수 범위 밖).

/// 판정 입력 상한(바이트) — 넘으면 기계 입구는 문 닫힘에서 거부 · 실행 자리 판정은 agy 로 본다(codex 4R minor 8 · 안전 쪽).
pub const MAX_JUDGE_BYTES: usize = 64 * 1024;
/// argv 판정의 인자 개수 상한 — 빈 인자는 길이 합에 거의 안 잡히므로 개수로도 자른다(codex 5R minor 8).
pub const MAX_JUDGE_ARGS: usize = 4096;
/// 실행 자리 판정의 치환 본문 수 상한 — 넘으면 구조를 읽지 않고 agy 낱말 유무로 안전 쪽 판정(codex 4R minor 8).
const MAX_SUBSTS: usize = 64;

/// 기계 입구 판정에서 지우는 인용·이스케이프 글자 — 셸·cmd 가 이름 안에서 걷어 내는 글자(`a''gy` · `ag\y` · `a^gy` · ``a``gy``).
const SPLICE_CHARS: [char; 5] = ['\'', '"', '\\', '^', '`'];

/// ① 기계 입구 낱말 검사(순수) — cmd 안에 agy 실행 파일 이름과 같은 낱말이 있는가.
///   낱말 = 영숫자·`.`·`_`·`-` 의 연속(그 밖 글자는 전부 구분자) · 대소문자 접기 · 끝 점 무시 · `.exe/.cmd/.bat/.ps1/.com` 제거 ·
///   줄표로 시작하는 낱말은 끝이 이름이어도 참(옵션에 붙은 값 `env -Sagy`).
///   원문과 「인용·이스케이프 글자를 지운 꼴」 둘 다 본다. 상한을 넘는 입력은 읽지 않고 참(안전 쪽).
pub fn names_agy(cmd: &str) -> bool {
    if cmd.len() > MAX_JUDGE_BYTES {
        return true;
    }
    let lc = cmd.to_lowercase();
    let spliced: String = lc.chars().filter(|c| !SPLICE_CHARS.contains(c)).collect();
    [lc.as_str(), spliced.as_str()].iter().any(|s| {
        s.split(|c: char| !(c.is_alphanumeric() || matches!(c, '.' | '_' | '-'))).any(|w| {
            let w = strip_ext(w.trim_end_matches('.'));
            // 줄표로 시작하는 낱말은 옵션 글자에 값이 붙은 꼴일 수 있다(`env -vSagy` · `${X:-agy}`) — 끝이 이름이면 agy.
            is_agy_name(&w) || (w.starts_with('-') && (w.ends_with("agy") || w.ends_with("antigravity")))
        })
    })
}

/// ② 실행 자리 검사(순수) — cmd 의 모든 명령 단위(`;`·`&&`·`|`·줄바꿈 · `sh -c` · `cmd /c` · `powershell -Command` · `find -exec` ·
/// 명령/프로세스 치환 본문 · here-string)에서 실행될 프로그램을 찾고, 그중 하나라도 `agy`/`antigravity` 면 참.
/// 안전망: 조회 전용 프로그램(echo·which·command -v·PowerShell 출력 명령 등)과 프롬프트 CLI(claude·codex)가 아니면
/// **낱말 하나 전체가** agy 이름이기만 해도(인용 여부 무관 · `call "C:\…\agy.cmd"`) 참 — 공백 든 프롬프트 글 속 agy 는 세지 않음.
/// 상한을 넘는 입력은 참(안전 쪽).
pub fn runs_agy(cmd: &str) -> bool {
    cmd.len() > MAX_JUDGE_BYTES || scan(cmd, 0).iter().any(|p| is_agy_word(p))
}

/// 해석된 **실행 파일 경로**(또는 이름)가 agy 인가 — 좌석 식별·감지 오라클용(③ 파일 이름 검사). 경로의 폴더 이름(예: 사용자
/// 이름이 `agy`)으로 오판하지 않게 **마지막 이름만** 본다 — 공백이 든 경로(`/Users/agy/Application Support/claude`)도 경로다
/// (codex 5R minor 7 · 명령 문자열은 [`names_agy`] 가 맡는다). 심링크면 해소한 실제 경로의 마지막 이름으로도 본다(codex 5R blocking 1 ⓐ).
pub fn program_is_agy(bin: &str) -> bool {
    let b = bin.trim();
    is_agy_word(b) || locate(b).is_some_and(|p| real_name_is_agy(&p))
}

/// [`program_is_agy`] + 문 상태 — 비어 있으면 어댑터 키 `gemini` 로 추정. 문이 닫혀 있고 agy 면 참.
pub fn program_refused(agent_key: &str, bin: &str) -> bool {
    program_refused_with(agent_key, bin, door_open())
}

pub fn program_refused_with(agent_key: &str, bin: &str, door_open: bool) -> bool {
    !door_open && if bin.trim().is_empty() { agent_key.eq_ignore_ascii_case("gemini") } else { program_is_agy(bin) }
}

/// 이 어댑터가 agy 인가 — **기계 입구 판정**(①). cmd 가 없거나 비었을 때만 어댑터 키 `gemini`(출하 어댑터 = agy)로 추정한다.
/// 낱말 검사 뒤에 실체 한 단계 확인([`resolves_to_agy`] — 심링크 · 셸에 넘긴 스크립트 파일 · 셔뱅 글 파일)을 더 한다(codex 5R blocking 1).
pub fn is_agy_adapter(agent_key: &str, cmd: Option<&str>) -> bool {
    match cmd {
        Some(c) if !c.trim().is_empty() => names_agy(c) || resolves_to_agy(c),
        _ => agent_key.eq_ignore_ascii_case("gemini"),
    }
}

/// 좌석 **종류**(생성 때 한 번 확정 · 데몬 `Surface.agy_kind`) — 선언 agent 이름이나 좌석 cmd 가 agy 를 가리키는가(문 상태와 무관).
/// 기계 입구 판정(①)과 같은 규칙: cmd 낱말 검사 · 선언 이름 낱말 검사 · cmd 가 없으면 선언 키 `gemini`(codex 5R blocking 3).
pub fn seat_kind_is_agy(agent: Option<&str>, cmd: Option<&str>) -> bool {
    is_agy_adapter(agent.unwrap_or(""), cmd) || agent.is_some_and(names_agy)
}

/// 데몬 `surface.create` 판정(PTY 를 만들기 **전** · 서버가 권위 · codex 5R blocking 2) — 문이 닫혀 있고 [`seat_kind_is_agy`] 면 거부 문안.
pub fn create_refusal(agent: Option<&str>, cmd: Option<&str>) -> Option<String> {
    create_refusal_with(agent, cmd, door_open())
}

pub fn create_refusal_with(agent: Option<&str>, cmd: Option<&str>, door_open: bool) -> Option<String> {
    (!door_open && seat_kind_is_agy(agent, cmd)).then(|| policy_text() + &machine_hint(cmd))
}

// ── 실체 한 단계 확인(TICKET=cysr-agy-door-r6 · codex 5R blocking 1 ⓐⓑ) ──
//   낱말 검사는 「이름이 명령 글자에 없는」 꼴을 못 본다. 그중 흔한 두 꼴만 한 단계 줄인다:
//   ⓐ 실행 자리 프로그램이 심링크(이름 바꾼 링크)면 실제 파일의 마지막 이름 ⓑ `sh|bash|zsh|… <파일>` · `source`/`.` · 셔뱅 있는 글 파일을
//   직접 실행 = 그 파일을 **한 번만** 읽어(64KiB 상한) 셔뱅 줄 낱말 + 본문 실행 자리에 agy 가 있는가. 두 단계 이상 간접·실행 중 조립·
//   별칭·환경 변수는 보지 않는다(ENTRY-MODES.md 「이 판에서 막지 않는 것」). 못 읽은 파일은 통과시키고 [`unread_scripts`] 로 알린다.

/// 셸에 넘긴 스크립트 파일 표지(실행 자리 판정 결과 안에서만 쓰는 내부 값 — 이 뒤가 파일 경로).
const SCRIPT_MARK: &str = "\u{1}script:";

/// 실행 파일 찾기 — 경로 꼴(`/` · `\` · `~/`)이면 그 파일, 맨 이름이면 `PATH` 폴더에서. 없으면 None.
fn locate(prog: &str) -> Option<PathBuf> {
    let p = prog.trim();
    if p.is_empty() || p.len() > 4096 {
        return None;
    }
    let p = match p.strip_prefix("~/") {
        Some(rest) => crate::home_dir().join(rest),
        None => PathBuf::from(p),
    };
    if p.components().count() > 1 || p.is_absolute() {
        return p.is_file().then_some(p);
    }
    search_path().into_iter().map(|d| d.join(&p)).find(|c| c.is_file())
}

/// 프로그램 찾기용 `PATH` 폴더 — ★이 모듈에서 환경 변수를 읽는 유일한 자리이며 문 상태와는 무관하다(시험 `env_never_opens_the_door`).
fn search_path() -> Vec<PathBuf> {
    std::env::var_os("PATH").map(|v| std::env::split_paths(&v).collect()).unwrap_or_default()
}

/// 셸에 넘긴 스크립트 파일은 셸처럼 현재 폴더 기준 경로를 먼저 본다(없으면 `PATH`).
fn locate_target(t: &str, script: bool) -> Option<PathBuf> {
    if script {
        let p = match t.strip_prefix("~/") { Some(r) => crate::home_dir().join(r), None => PathBuf::from(t) };
        if p.is_file() {
            return Some(p);
        }
    }
    locate(t)
}

/// 실제 파일(심링크 해소)의 마지막 이름이 agy 인가.
fn real_name_is_agy(p: &Path) -> bool {
    std::fs::canonicalize(p).is_ok_and(|r| is_agy_word(&r.to_string_lossy()))
}

/// 글 파일 한 번 읽기(상한 64KiB · 넘거나 못 읽으면 None).
fn read_script(p: &Path) -> Option<String> {
    let m = std::fs::metadata(p).ok()?;
    if !m.is_file() || m.len() > MAX_JUDGE_BYTES as u64 {
        return None;
    }
    String::from_utf8(std::fs::read(p).ok()?).ok()
}

/// 스크립트 본문(이미 읽은 글)이 agy 를 실행하는가 — 셔뱅 줄은 낱말 검사 · 본문은 **셸 글일 때만**(`sh x` 로 넘긴 파일 또는 셔뱅이
/// 셸) 줄 머리 `#` 주석을 걷고 실행 자리 검사(더 깊이 읽지 않는다). 파이썬 등 다른 언어 본문은 셸로 읽으면 거짓 양성이 나므로 셔뱅 줄만.
fn script_body_runs_agy(body: &str, run_by_shell: bool) -> bool {
    let (shebang, rest) = match body.strip_prefix("#!") {
        Some(b) => b.split_once('\n').unwrap_or((b, "")),
        None => ("", body),
    };
    if names_agy(shebang) {
        return true;
    }
    let shell_text = run_by_shell || shebang.split_whitespace().take(2).any(|w| SHELLS.contains(&basename_lc(w).as_str()));
    let code: String = rest.lines().filter(|l| !l.trim_start().starts_with('#')).collect::<Vec<_>>().join("\n");
    shell_text && runs_agy(&code)
}

/// 셸 글을 읽는 프로그램(셸 갈래 · 셔뱅 판정 공용).
const SHELLS: [&str; 10] = ["sh", "bash", "zsh", "dash", "ksh", "csh", "tcsh", "fish", "mksh", "yash"];

/// 판정할 파일 하나 → Some(agy 인가) · 읽을 대상이 아니면(바이너리·셔뱅 없음) Some(false) · 못 읽음 = None.
fn file_runs_agy(p: &Path, must_read: bool) -> Option<bool> {
    if real_name_is_agy(p) {
        return Some(true);
    }
    let head = std::fs::File::open(p).ok().and_then(|mut f| {
        let mut b = [0u8; 2];
        std::io::Read::read_exact(&mut f, &mut b).ok().map(|_| b)
    });
    if !must_read && head != Some(*b"#!") {
        return Some(false);   // 셔뱅 없는 실행 파일(바이너리 등) = 이름만 본다
    }
    read_script(p).map(|b| script_body_runs_agy(&b, must_read))
}

/// 실행 자리 프로그램 목록(내부 값 걸러 냄) → (판정 대상 파일, 반드시 읽을 스크립트인가).
fn resolve_targets(cmd: &str) -> Vec<(String, bool)> {
    if cmd.len() > MAX_JUDGE_BYTES {
        return Vec::new();
    }
    scan(cmd, 0)
        .into_iter()
        .filter(|p| p != STDIN_SHELL && p != "?" && !p.is_empty())
        .map(|p| match p.strip_prefix(SCRIPT_MARK) {
            Some(s) => (s.to_string(), true),
            None => (p, false),
        })
        .collect()
}

/// ⓐⓑ 실체 한 단계 확인 — 실행 자리 프로그램(심링크 해소 이름) 또는 셸에 넘긴·셔뱅 스크립트 파일 안 실행 자리에 agy 가 있으면 참.
pub fn resolves_to_agy(cmd: &str) -> bool {
    resolve_targets(cmd).iter().any(|(t, must)| locate_target(t, *must).and_then(|p| file_runs_agy(&p, *must)).unwrap_or(false))
}

/// 문이 닫혀 있을 때 판정하려 했으나 **못 읽은** 스크립트 파일(통과시켰음 — 원장·출력에 표시할 것). 문 열림이면 빈 목록.
pub fn unread_scripts(cmd: &str) -> Vec<String> {
    if door_open() {
        return Vec::new();
    }
    resolve_targets(cmd)
        .into_iter()
        .filter(|(t, must)| *must && locate_target(t, true).is_none_or(|p| file_runs_agy(&p, true).is_none()))
        .map(|(t, _)| t)
        .collect()
}

fn is_agy_name(p: &str) -> bool {
    p == "agy" || p == "antigravity"
}

/// 낱말이 agy 실행 파일 이름인가 — 경로·확장자를 걷고, 셸 이스케이프(`ag\y`)를 지운 꼴도 본다.
fn is_agy_word(t: &str) -> bool {
    // 셸 이스케이프(`ag\y`) · cmd 의 캐럿(`a^gy`) · zsh 등호 확장(`=agy`)을 걷어 낸 꼴까지 본다.
    let t = t.strip_prefix('=').unwrap_or(t);
    is_agy_name(&basename_lc(t)) || is_agy_name(&basename_lc(&t.replace(['\\', '^'], "")))
}

/// 리다이렉트 낱말이면 건너뛸 낱말 수(대상이 붙어 있으면 1 · 연산자만이면 대상까지 2) — `>/dev/null agy` · `2>&1 agy` · `< f agy`.
fn redirect_skip(t: &Tok) -> Option<usize> {
    if t.quoted {
        return None;
    }
    let s = t.text.trim_start_matches(|c: char| c.is_ascii_digit());
    let op_len = ["&>>", ">>", "&>", ">&", "<&", "<<", ">", "<", ">|"].iter().find(|o| s.starts_with(**o))?.len();
    if s.starts_with("<<<") {
        return None;   // here-string 은 셸 갈래가 읽는다
    }
    Some(if s.len() == op_len { 2 } else { 1 })
}

fn mentions_agy(s: &str) -> bool {
    s.to_ascii_lowercase().replace('\\', "").split(|c: char| !(c.is_ascii_alphanumeric() || c == '_' || c == '-')).any(is_agy_name)
}

#[derive(Clone)]
struct Tok {
    text: String,
    quoted: bool,
}

/// 명령/프로세스 치환 본문을 뽑고 바깥 문에서는 자리표시로 바꾼다(`$(…)`·`<(…)`·`>(…)`·백틱 · 홑따옴표 안은 치환 아님).
/// 짝이 안 맞으면 None(호출부가 안전 쪽으로 판정).
fn extract_subst(s: &str) -> Option<(String, Vec<String>)> {
    let c: Vec<char> = s.chars().collect();
    let (mut outer, mut bodies, mut i, mut sq) = (String::new(), Vec::new(), 0usize, false);
    while i < c.len() {
        let ch = c[i];
        if sq {
            outer.push(ch);
            if ch == '\'' {
                sq = false;
            }
            i += 1;
            continue;
        }
        if ch == '\'' {
            sq = true;
            outer.push(ch);
            i += 1;
            continue;
        }
        if ch == '\\' && i + 1 < c.len() {
            outer.push(ch);
            outer.push(c[i + 1]);
            i += 2;
            continue;
        }
        if (ch == '$' || ch == '<' || ch == '>') && c.get(i + 1) == Some(&'(') {
            let (mut d, mut j) = (1, i + 2);
            while j < c.len() && d > 0 {
                match c[j] {
                    '(' => d += 1,
                    ')' => d -= 1,
                    _ => {}
                }
                j += 1;
            }
            if d != 0 || bodies.len() >= MAX_SUBSTS {
                return None;
            }
            bodies.push(c[i + 2..j - 1].iter().collect());
            outer.push_str(" __subst__ ");
            i = j;
            continue;
        }
        if ch == '`' {
            let j = (i + 1..c.len()).find(|&k| c[k] == '`' && c[k - 1] != '\\')?;
            if bodies.len() >= MAX_SUBSTS {
                return None;
            }
            bodies.push(c[i + 1..j].iter().collect());
            outer.push_str(" __subst__ ");
            i = j + 1;
            continue;
        }
        outer.push(ch);
        i += 1;
    }
    Some((outer, bodies))
}

/// 셸 비슷한 나누기(순수) — 인용 밖의 `;` `&` `|` `(` `)` 줄바꿈에서 명령 단위를 끊고 단위 안은 낱말로 · 낱말마다 인용 여부.
/// 역슬래시: 뒤가 줄바꿈이면 줄 이음(둘 다 버림) · 뒤가 공백·따옴표면 이스케이프 · 그 밖은 글자 그대로(윈도우 경로 `C:\x\agy.cmd`).
fn lex(s: &str) -> Vec<Vec<Tok>> {
    let (mut segs, mut out, mut cur, mut any, mut quoted) = (Vec::new(), Vec::<Tok>::new(), String::new(), false, false);
    let mut it = s.chars().peekable();
    let mut q: Option<char> = None;
    fn flush(out: &mut Vec<Tok>, cur: &mut String, any: &mut bool, quoted: &mut bool) {
        if *any || !cur.is_empty() {
            out.push(Tok { text: std::mem::take(cur), quoted: *quoted });
            *any = false;
            *quoted = false;
        }
    }
    while let Some(c) = it.next() {
        match q {
            Some(qc) if c == qc => q = None,
            Some(_) => cur.push(c),
            None if c == '\\' && it.peek() == Some(&'\n') => {
                it.next();
            }
            None if c == '\\' && matches!(it.peek(), Some(n) if n.is_whitespace() || *n == '"' || *n == '\'') => {
                cur.push(it.next().unwrap());
                any = true;
            }
            None if c == '\'' || c == '"' => {
                if cur == "$" {
                    cur.clear();   // ANSI-C `$'…'` — 따옴표 앞 `$` 는 이름의 일부가 아니다
                }
                q = Some(c);
                any = true;
                quoted = true;
            }
            // 리다이렉트 속 `&`(`2>&1` · `&>f`)는 명령 경계가 아니다
            None if c == '&' && (cur.ends_with('>') || cur.ends_with('<') || it.peek() == Some(&'>')) => cur.push(c),
            None if matches!(c, ';' | '&' | '|' | '(' | ')' | '\n') => {
                flush(&mut out, &mut cur, &mut any, &mut quoted);
                if !out.is_empty() {
                    segs.push(std::mem::take(&mut out));
                }
            }
            None if c.is_whitespace() => flush(&mut out, &mut cur, &mut any, &mut quoted),
            None => cur.push(c),
        }
    }
    flush(&mut out, &mut cur, &mut any, &mut quoted);
    if !out.is_empty() {
        segs.push(out);
    }
    segs
}

fn is_assignment(w: &str) -> bool {
    let Some((k, _)) = w.split_once('=') else { return false };
    !k.is_empty() && k.chars().all(|c| c.is_ascii_alphanumeric() || c == '_') && !k.starts_with(|c: char| c.is_ascii_digit())
}

/// cmd 문자열 → 실행될 프로그램 이름들(소문자 · 경로·확장자 제거) — 깊이 4 넘으면 agy 낱말 유무로 안전 쪽 판정.
fn scan(cmd: &str, depth: u8) -> Vec<String> {
    if depth > 4 {
        return if mentions_agy(cmd) { vec!["agy".into()] } else { vec!["?".into()] };
    }
    let Some((outer, bodies)) = extract_subst(cmd) else {
        return if mentions_agy(cmd) { vec!["agy".into()] } else { vec!["?".into()] };
    };
    let mut out: Vec<String> = bodies.iter().flat_map(|b| scan(b, depth + 1)).collect();
    for seg in lex(&outer) {
        out.extend(seg_programs(&seg, depth));
    }
    // `echo agy | sh` — 표준 입력을 스크립트로 읽는 셸이 있고 문에 agy 낱말이 있으면 agy(파이프 내용은 정적으로 못 읽음 · 안전 쪽)
    if out.iter().any(|p| p == STDIN_SHELL) && mentions_agy(cmd) {
        out.push("agy".into());
    }
    out
}

const STDIN_SHELL: &str = "<stdin-shell>";

/// 조회·출력만 하는 프로그램 — 인자 속 agy 낱말을 실행으로 세지 않는다(PowerShell 출력·조회 명령 포함 · codex 4R major 5).
const NON_EXEC: [&str; 27] = ["echo", "printf", "which", "type", "whereis", "test", "[", "ls", "cat", "grep", "rg", "man",
                               "file", "stat", "head", "tail", "wc", "write-output", "write-host", "get-command", "get-help",
                               "test-path", "get-content", "get-childitem", "get-item", "select-string", "where.exe"];

/// 프롬프트 CLI — 인자는 사람 말(프롬프트)이지 실행할 프로그램이 아니다(`claude -p agy` · `codex exec agy` · codex 4R major 5).
/// 단 다른 프로그램을 실행·등록하는 하위 명령(`mcp` · codex `sandbox`/`debug`)이 보이면 이 면제를 쓰지 않는다(안전망으로).
fn prompt_cli_exempt(base: &str, rest: &[Tok]) -> bool {
    let runs_other = |t: &Tok| !t.quoted && matches!(t.text.as_str(), "mcp" | "sandbox" | "debug");
    matches!(base, "claude" | "codex") && !rest.iter().any(runs_other)
}

fn seg_programs(w: &[Tok], depth: u8) -> Vec<String> {
    let (mut progs, nonexec) = program_of(w, depth);
    if !nonexec
        && !progs.iter().any(|p| is_agy_word(p))
        // ★codex 4R blocking 3: 인용된 낱말도 본다(`call "C:\\…\\agy.cmd"` · `watch "/opt/agy"`) — 낱말 하나 **전체**가 agy 이름일 때만
        //   (공백 든 프롬프트 글 「agy 를 설명해」는 이름이 아니다).
        && w.iter().any(|t| !(!t.quoted && is_assignment(&t.text)) && redirect_skip(t).is_none() && is_agy_word(&t.text))
    {
        progs.push("agy".into());
    }
    progs
}

/// cmd.exe·PowerShell 은 뒤 글 전체를 명령줄로 다시 읽는다 — 인용을 덧씌우지 않고 이어 붙인다.
fn join_plain(w: &[Tok]) -> String {
    w.iter().map(|t| t.text.as_str()).collect::<Vec<_>>().join(" ")
}

fn join(w: &[Tok]) -> String {
    w.iter().map(|t| if t.text.contains(char::is_whitespace) { format!("'{}'", t.text.replace('\'', "")) } else { t.text.clone() })
        .collect::<Vec<_>>()
        .join(" ")
}

/// 래퍼별 「값을 먹는」 짧은 옵션 글자 · 긴 옵션 이름 · 명령 앞에 버릴 위치 인자 수.
fn wrapper_spec(base: &str) -> Option<(&'static str, &'static [&'static str], usize)> {
    Some(match base {
        "command" | "nohup" | "setsid" => ("", &[], 0),
        "exec" => ("a", &[], 0),
        "nice" => ("n", &["--adjustment"], 0),
        "time" => ("of", &["--output", "--format"], 0),
        "caffeinate" => ("tw", &[], 0),
        "stdbuf" => ("ioe", &["--input", "--output", "--error"], 0),
        "timeout" | "gtimeout" => ("sk", &["--signal", "--kill-after"], 1),
        "sudo" => ("ughpCDrtTUR", &["--user", "--group", "--host", "--prompt", "--close-from", "--chdir", "--role",
                                    "--type", "--command-timeout", "--other-user", "--chroot"], 0),
        "doas" => ("uC", &[], 0),
        "xargs" => ("ILnPsEdaJRS", &["--replace", "--max-lines", "--max-args", "--max-procs", "--max-chars", "--eof",
                                     "--delimiter", "--arg-file"], 0),
        "script" => ("Ft", &[], 1),
        "arch" => ("", &["-arch", "-e"], 0),
        "busybox" => ("", &[], 0),
        "repeat" => ("", &[], 1),   // zsh `repeat N 명령`
        _ => return None,
    })
}

/// 명령 단위 하나 → (실행될 프로그램들, 바깥 안전망 생략인가 = 조회 전용 · 프롬프트 CLI · 안쪽 명령을 이미 따로 판정한 위임
/// (`sh -c`·`cmd /c`·`powershell -Command`·`env -S`·`find -exec`·`su -c`·`script -c`·here-string)).
fn program_of(w: &[Tok], depth: u8) -> (Vec<String>, bool) {
    // 예약어 · zsh 앞말(noglob·nocorrect·builtin·coproc·`-`)
    const KW: [&str; 15] = ["!", "{", "}", "then", "do", "else", "elif", "if", "while", "until", "noglob", "nocorrect",
                            "builtin", "coproc", "-"];
    let mut i = 0;
    while i < w.len() {
        let t = &w[i].text;
        if (!w[i].quoted && is_assignment(t)) || (!w[i].quoted && KW.contains(&t.as_str())) {
            i += 1;
            continue;
        }
        if let Some(n) = redirect_skip(&w[i]) {
            i += n;
            continue;
        }
        let base = basename_lc(t);
        let rest = &w[i + 1..];
        if base == "env" {
            i += 1;
            while i < w.len() {
                let a = w[i].text.as_str();
                if is_assignment(a) {
                    i += 1;
                    continue;
                }
                if a == "--" {
                    i += 1;
                    break;
                }
                if let Some(long) = a.strip_prefix("--") {
                    let (name, val) = match long.split_once('=') { Some((n, v)) => (n, Some(v)), None => (long, None) };
                    // GNU env 는 긴 옵션의 모호하지 않은 앞부분을 받는다(`--split`·`--spl`) — s 로 시작하는 긴 옵션은 split-string 뿐.
                    if !name.is_empty() && "split-string".starts_with(name) {
                        let (v, next) = match val { Some(v) => (v.to_string(), i + 1), None => (w.get(i + 1).map(|t| t.text.clone()).unwrap_or_default(), i + 2) };
                        return (scan(&format!("{v} {}", join(w.get(next..).unwrap_or(&[]))), depth + 1), true);
                    }
                    let takes = val.is_none() && ["unset", "chdir", "argv0"].iter().any(|o| o.starts_with(name) && name.len() >= 2);
                    i += if takes { 2 } else { 1 };
                    continue;
                }
                if a.len() > 1 && a.starts_with('-') {
                    // 짧은 옵션 묶음 `-ivS<문>` · `-iS <문>` · `-u NAME` · `-uNAME`
                    let cl = &a[1..];
                    let mut consumed_next = false;
                    for (k, ch) in cl.char_indices() {
                        let r = &cl[k + ch.len_utf8()..];
                        if ch == 'S' {
                            let (v, next) = if r.is_empty() { (w.get(i + 1).map(|t| t.text.clone()).unwrap_or_default(), i + 2) } else { (r.to_string(), i + 1) };
                            return (scan(&format!("{v} {}", join(w.get(next..).unwrap_or(&[]))), depth + 1), true);
                        }
                        if matches!(ch, 'u' | 'C' | 'P' | 'a') {
                            consumed_next = r.is_empty();
                            break;
                        }
                    }
                    i += if consumed_next { 2 } else { 1 };
                    continue;
                }
                break;
            }
            continue;
        }
        if base == "su" {
            if let Some(k) = rest.iter().position(|t| t.text == "-c" || t.text == "--command") {
                return (rest.get(k + 1).map(|t| scan(&t.text, depth + 1)).unwrap_or_default(), true);
            }
        }
        if SHELLS.contains(&base.as_str()) {
            // here-string(`bash <<< '문'`) = 표준 입력 스크립트
            if let Some(k) = rest.iter().position(|t| t.text.starts_with("<<<")) {
                let v = rest[k].text[3..].to_string();
                let v = if v.is_empty() { rest.get(k + 1).map(|t| t.text.clone()).unwrap_or_default() } else { v };
                return (scan(&v, depth + 1), true);
            }
            // `-c` = 정확히 한 줄표 묶음 안의 c(`-c`·`-lc`) — `--norc` 같은 긴 옵션은 -c 가 아니다 · -o/-O 는 값을 먹는다.
            let mut j = 0;
            while j < rest.len() {
                let a = rest[j].text.as_str();
                if a == "--" || !(a.starts_with('-') || a.starts_with('+')) {
                    break;
                }
                if a.starts_with("--") {
                    j += if matches!(a, "--rcfile" | "--init-file") { 2 } else { 1 };
                    continue;
                }
                if matches!(a, "-o" | "+o" | "-O" | "+O") {
                    j += 2;
                    continue;
                }
                if a[1..].contains('c') {
                    let mut k = j + 1;
                    while k < rest.len() && rest[k].text.starts_with('-') && rest[k].text != "-" {
                        k += 1;
                    }
                    let Some(body) = rest.get(k) else { return (vec![], true) };
                    let mut progs = scan(&body.text, depth + 1);
                    // ★codex 5R major 4: `sh -c 'exec "$@"' sh agy` — 글이 위치 인자(`$0`·`$1`…·`$@`·`$*`)를 쓰면 위치 인자가 명령이 된다.
                    //   $1 부터를 명령 단위로 판정하고, $0 을 포함한 위치 인자 낱말 하나 전체가 agy 이름이면 agy(안전망).
                    let pos = &rest[k + 1..];
                    if uses_positional(&body.text) && !pos.is_empty() {
                        if pos.len() > 1 {
                            progs.extend(seg_programs(&pos[1..], depth + 1));
                        }
                        if pos.iter().any(|t| is_agy_word(&t.text)) {
                            progs.push("agy".into());
                        }
                    }
                    return (progs, true);
                }
                j += 1;
            }
            // 스크립트 파일 없이 뜬 셸 = 표준 입력을 실행한다(파이프 `… | sh`)
            let script = rest[j.min(rest.len())..].iter().find(|t| redirect_skip(t).is_none());
            return (match script {
                Some(f) => vec![w[i].text.clone(), format!("{SCRIPT_MARK}{}", f.text)],
                None => vec![STDIN_SHELL.into()],
            }, false);
        }
        if matches!(base.as_str(), "source" | ".") {
            // `source x.sh` · `. ./x.sh` — 이 셸이 그 파일을 읽어 실행한다(실체 한 단계 확인의 대상 · codex 5R blocking 1 ⓑ)
            if let Some(f) = rest.iter().find(|t| redirect_skip(t).is_none()) {
                return (vec![w[i].text.clone(), format!("{SCRIPT_MARK}{}", f.text)], false);
            }
        }
        if base == "cmd" {
            // cmd.exe /c 문 · /k 문 — 뒤 전부가 실행될 명령
            if let Some(k) = rest.iter().position(|t| t.text.eq_ignore_ascii_case("/c") || t.text.eq_ignore_ascii_case("/k")) {
                return (scan(&join_plain(&rest[k + 1..]), depth + 1), true);
            }
            return (vec![w[i].text.clone()], false);
        }
        if matches!(base.as_str(), "powershell" | "pwsh") {
            let mut k = 0;
            while k < rest.len() {
                let a = rest[k].text.to_ascii_lowercase();
                if a.starts_with('-') && a.len() >= 2 && "-file".starts_with(&a) && a != "-" {
                    return (rest.get(k + 1).map(|t| vec![t.text.clone()]).unwrap_or_default(), true);
                }
                if a.starts_with('-') && a.len() >= 2 && "-command".starts_with(&a) {
                    return (scan(&join_plain(&rest[k + 1..]), depth + 1), true);
                }
                if !a.starts_with('-') {
                    return (scan(&join_plain(&rest[k..]), depth + 1), true);   // 옵션 없이 온 글 = -Command 와 같다
                }
                k += 1;
            }
            return (vec![w[i].text.clone()], false);
        }
        if base == "find" {
            if let Some(k) = rest.iter().position(|t| matches!(t.text.as_str(), "-exec" | "-execdir" | "-ok" | "-okdir")) {
                let end = rest[k + 1..].iter().position(|t| t.text == ";" || t.text == "+").map(|e| k + 1 + e).unwrap_or(rest.len());
                return (seg_programs(&rest[k + 1..end], depth), true);
            }
            return (vec![w[i].text.clone()], true);
        }
        if base == "command" && rest.iter().take_while(|t| t.text.starts_with('-')).any(|t| t.text.contains('v') || t.text.contains('V')) {
            return (vec![], true);   // command -v/-V = 조회
        }
        if NON_EXEC.contains(&base.as_str()) || prompt_cli_exempt(&base, rest) {
            return (vec![w[i].text.clone()], true);
        }
        if let Some((short, long, positional)) = wrapper_spec(&base) {
            i += 1;
            if base == "script" {
                // 리눅스 script -c '<문>' — 값이 실행될 명령
                if let Some(k) = w[i..].iter().position(|a| a.text == "-c" || a.text == "--command") {
                    return (w.get(i + k + 1).map(|t| scan(&t.text, depth + 1)).unwrap_or_default(), true);
                }
            }
            while i < w.len() {
                let a = w[i].text.as_str();
                if a == "--" {
                    i += 1;
                    break;
                }
                if long.contains(&a) {
                    i += 2;
                    continue;
                }
                if a.starts_with("--") {
                    let name = a.split('=').next().unwrap_or(a);
                    i += if !a.contains('=') && long.contains(&name) { 2 } else { 1 };
                    continue;
                }
                if a.len() > 1 && a.starts_with('-') {
                    let cl = &a[1..];
                    let mut consumed_next = false;
                    for (k, ch) in cl.char_indices() {
                        if short.contains(ch) {
                            consumed_next = cl[k + ch.len_utf8()..].is_empty();
                            break;
                        }
                    }
                    i += if consumed_next { 2 } else { 1 };
                    continue;
                }
                break;
            }
            i += positional.min(w.len().saturating_sub(i));
            continue;
        }
        // 실행 프로그램은 원래 낱말 그대로 돌려준다(경로 포함 — 실체 확인이 파일을 찾는다 · 판정은 `is_agy_word` 가 마지막 이름으로).
        return (if base.is_empty() { vec![] } else { vec![w[i].text.clone()] }, false);
    }
    (vec![], false)
}

/// 셸 글이 위치 인자를 쓰는가 — `$0`…`$9` · `${1}` · `$@` · `$*` · `${@}` (codex 5R major 4).
fn uses_positional(s: &str) -> bool {
    let c: Vec<char> = s.chars().collect();
    (0..c.len()).any(|i| {
        c[i] == '$' && {
            let n = if c.get(i + 1) == Some(&'{') { c.get(i + 2) } else { c.get(i + 1) };
            n.is_some_and(|n| n.is_ascii_digit() || *n == '@' || *n == '*')
        }
    })
}

fn basename_lc(tok: &str) -> String {
    strip_ext(&tok.rsplit(['/', '\\']).next().unwrap_or(tok).to_ascii_lowercase())
}

/// 윈도 실행 확장자 하나를 걷는다(소문자 입력).
fn strip_ext(base: &str) -> String {
    for ext in [".exe", ".cmd", ".bat", ".ps1", ".com"] {
        if let Some(s) = base.strip_suffix(ext) {
            return s.to_string();
        }
    }
    base.to_string()
}

/// 문 파일 자리 — `~/.cys/agy-seat-door.json`(본부·부서 공통 · 사람 하나의 결정).
pub fn door_path() -> PathBuf {
    door_path_under(&crate::home_dir())
}

pub fn door_path_under(home: &Path) -> PathBuf {
    home.join(".cys").join(DOOR_FILE)
}

/// 문 본문이 열림인가(순수) — `{"open": true, "ack": DOOR_ACK}` 일 때만. 그 밖(빈 본문·JSON 아님·ack 다름)은 닫힘.
pub fn door_body_is_open(body: &str) -> bool {
    match serde_json::from_str::<serde_json::Value>(body) {
        Ok(v) => v["open"].as_bool() == Some(true) && v["ack"].as_str() == Some(DOOR_ACK),
        Err(_) => false,
    }
}

/// 이 자리의 문이 열려 있는가 — 일반 파일(심링크 아님)이고 본문이 열림일 때만. 판독 실패 = 닫힘(안전 쪽).
pub fn door_open_at(path: &Path) -> bool {
    match std::fs::symlink_metadata(path) {
        Ok(m) if m.file_type().is_file() => std::fs::read_to_string(path).is_ok_and(|b| door_body_is_open(&b)),
        _ => false,
    }
}

/// 지금 문이 열려 있는가. ★환경 변수는 보지 않는다(모듈 머리 · 시험 `env_never_opens_the_door`).
pub fn door_open() -> bool {
    door_open_at(&door_path())
}

/// 문 쓰기 — **앱 화면(src-tauri) 전용**. 열기 = 표지 달린 본문 · 닫기 = 파일 삭제(없으면 그대로 성공).
/// 반환 = 쓰기 직후 **같은 임계 구역 안에서** 읽은 문 상태(codex 4R minor 7).
/// ★`cys` CLI·데몬·팩은 부르지 않는다(시험 `only_the_gui_writes_the_door`).
pub fn write_door(open: bool) -> Result<bool, String> {
    write_door_at(&door_path(), open)
}

/// 문 변경 직렬화(프로세스 전역) — 열기 A 가 임시본을 쓰고 멈춘 사이 닫기 B 가 끝나고, 그 뒤 A 의 이름 바꾸기가 문을 다시
/// 여는 경합(「나중에 누른 닫기」가 지는 fail-open · codex 4R minor 7)을 막는다.
static DOOR_LOCK: std::sync::Mutex<()> = std::sync::Mutex::new(());
static DOOR_TMP_SEQ: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(0);

pub fn write_door_at(path: &Path, open: bool) -> Result<bool, String> {
    let _g = DOOR_LOCK.lock().unwrap_or_else(|e| e.into_inner());
    // 앱 두 벌(다른 프로세스) 사이의 직렬화 = 옆 잠금 파일의 OS 배타 잠금(codex 5R minor 6) — 프로세스가 죽으면 OS 가 푼다.
    if let Some(dir) = path.parent() {
        std::fs::create_dir_all(dir).map_err(|e| format!("{}: {e}", dir.display()))?;
    }
    let lock_path = path.with_file_name(format!("{DOOR_FILE}.lock"));
    let lock_file = std::fs::OpenOptions::new().create(true).truncate(false).write(true).open(&lock_path)
        .map_err(|e| format!("{}: {e}", lock_path.display()))?;
    lock_file.lock().map_err(|e| format!("{}: {e}", lock_path.display()))?;
    if !open {
        return match std::fs::remove_file(path) {
            Ok(()) => Ok(door_open_at(path)),
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(door_open_at(path)),
            Err(e) => Err(format!("{}: {e}", path.display())),
        };
    }
    let at = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);
    let body = serde_json::json!({"open": true, "ack": DOOR_ACK, "opened_at_epoch": at, "by": "cysr-app"});
    // 고유 임시본(프로세스·순번) — 같은 이름을 두 쓰기가 나눠 쓰지 않는다.
    let seq = DOOR_TMP_SEQ.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
    let tmp = path.with_file_name(format!("{DOOR_FILE}.{}.{seq}.tmp", std::process::id()));
    std::fs::write(&tmp, format!("{body}\n")).map_err(|e| format!("{}: {e}", tmp.display()))?;
    if let Err(e) = std::fs::rename(&tmp, path) {
        let _ = std::fs::remove_file(&tmp);
        return Err(format!("{}: {e}", path.display()));
    }
    Ok(door_open_at(path))
}

/// 기동 거부 문안(왕초보가 읽는 말) — **기계 입구**(낱말 검사 ①): agy 어댑터이고 문이 닫혀 있으면 Some.
pub fn launch_refusal(agent_key: &str, cmd: Option<&str>) -> Option<String> {
    launch_refusal_with(agent_key, cmd, door_open())
}

/// **실행 자리** 판정(②) 거부 문안 — 에이전트 자기 Bash(팩 훅 guard 가 `cys agy-door-check --cmd` 로 부른다).
pub fn exec_refusal(cmd: &str) -> Option<String> {
    exec_refusal_with(cmd, door_open())
}

pub fn exec_refusal_with(cmd: &str, door_open: bool) -> Option<String> {
    (!door_open && runs_agy(cmd)).then(policy_text)
}

/// argv(이미 나뉜 실행 인자 — `cys run -- <argv>`) 판. 문자열로 다시 이어 붙이지 않는다(codex 2R: 인용 재조립은
/// 따옴표가 든 인자에서 해석이 어긋난다). 어댑터 키가 없으므로 실행 프로그램으로만 판정한다.
pub fn launch_refusal_argv(argv: &[String]) -> Option<String> {
    launch_refusal_argv_with(argv, door_open())
}

pub fn launch_refusal_argv_with(argv: &[String], door_open: bool) -> Option<String> {
    if door_open {
        return None;
    }
    // 상한 = Σ(길이+1)(구분자 몫) + 인자 개수(빈 인자 대량 입력 · codex 5R minor 8) — 넘으면 안전 쪽(codex 4R minor 8).
    if argv.len() > MAX_JUDGE_ARGS || argv.iter().map(|a| a.len() + 1).sum::<usize>() > MAX_JUDGE_BYTES {
        return Some(policy_text());
    }
    // argv 원소 = 이미 나뉜 인자 — 공백이 든 원소는 인용된 한 낱말과 같다(프롬프트 글 속 agy 는 안전망에 안 걸림).
    let toks: Vec<Tok> = argv.iter().map(|a| Tok { text: a.clone(), quoted: a.contains(char::is_whitespace) }).collect();
    let is_agy = toks
        .split(|t| matches!(t.text.as_str(), ";" | "&&" | "||" | "|" | "&"))
        .flat_map(|seg| seg_programs(seg, 0))
        .any(|p| is_agy_word(&p));
    is_agy.then(policy_text)
}

/// 정책 본문(두 판정 공통 머리) — 거부 사유 코드로 시작한다(phoenix·acceptance·guard 가 이 머리로 소비).
fn policy_text() -> String {
    format!(
        "{REFUSE_CODE}: cysr 은 Antigravity(agy) 좌석을 띄우지 않습니다 — 개인 요금제에서 다른 프로그램이 agy 를 \
         부리면 구글 약관상 계정이 정지될 수 있기 때문입니다. agy 를 직접 쓰려면 새 탭에서 `agy` 를 치세요(괜찮습니다). \
         기업 요금제 등 허용된 경우에만, 사람이 앱 명령 팔레트의 「Antigravity(agy) 좌석 열기」로 열 수 있습니다."
    )
}

/// 기계 입구 거부의 덧말 — 낱말 검사는 거짓 양성을 받아들이므로 까닭과 푸는 법을 왕초보 말로 말한다.
fn machine_hint(cmd: Option<&str>) -> String {
    match cmd {
        Some(c) if c.len() > MAX_JUDGE_BYTES => format!(
            " (이 명령은 {}바이트로 너무 길어서 — 상한 {MAX_JUDGE_BYTES}바이트 — 안을 살피지 않고 막았습니다. 명령을 짧게 \
             줄여 다시 등록하세요. agy 를 쓰려던 것이라면, 앱에서 문을 연 뒤 사람이 직접 실행하세요.)",
            c.len()
        ),
        Some(c) if !c.trim().is_empty() => " (자동으로 도는 명령 — 일정·채널·계정·복원 같은 것 — 은 셸 문법을 해석하지 않고, \
             글자 안에 「agy」라는 낱말이 하나라도 있으면 막습니다. agy 를 실행하려던 게 아니라 설명 글 등에 그 낱말이 \
             들어 있을 뿐이라면, 그 낱말을 다른 말(예: 「안티그래비티」)로 바꿔 다시 등록하세요.)"
            .to_string(),
        _ => String::new(),
    }
}

/// [`launch_refusal`] 의 순수판(문 상태 주입).
pub fn launch_refusal_with(agent_key: &str, cmd: Option<&str>, door_open: bool) -> Option<String> {
    (!door_open && is_agy_adapter(agent_key, cmd)).then(|| policy_text() + &machine_hint(cmd))
}

/// 복원 건너뜀 한 줄(실패로 세지 않는다) — agy 어댑터이고 문이 닫혀 있으면 Some.
pub fn restore_skip_line(role: &str, agent_key: &str, cmd: Option<&str>) -> Option<String> {
    restore_skip_line_with(role, agent_key, cmd, door_open())
}

pub fn restore_skip_line_with(role: &str, agent_key: &str, cmd: Option<&str>, door_open: bool) -> Option<String> {
    (!door_open && is_agy_adapter(agent_key, cmd)).then(|| {
        format!(
            "· {role}: 건너뜀({REFUSE_CODE}) — 구글 개인 요금제 약관 때문에 cysr 은 Antigravity(agy) 좌석을 다시 띄우지 \
             않습니다. 고장이 아닙니다 · 검토가 필요하면 Claude 대체 검토자가 대신합니다."
        )
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    /// 두 판정 모두 agy 로 본다(실행 자리에서 잡히는 꼴은 기계 입구 낱말 검사에서도 잡혀야 한다 · ② ⊆ ①).
    fn both(c: &str) -> bool {
        runs_agy(c) && names_agy(c)
    }

    fn td(name: &str) -> PathBuf {
        let d = std::env::temp_dir().join(format!("cys-agy-door-{name}-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&d);
        std::fs::create_dir_all(&d).unwrap();
        d
    }

    #[test]
    fn codex_1r_parser_cases() {
        for agy in ["FOO=/tmp agy", "FOO=\"a b\" agy -p x", "env FOO=1 agy", "env -u X agy", "nohup env A=1 /x/agy",
                    "\"/Applications/My Tools/agy\" --x", "C:\\npm\\agy.bat", "sh -c 'agy -p hi'", "bash -lc \"FOO=1 agy\""] {
            assert!(both(agy), "{agy}");
        }
        assert!(!runs_agy("CLAUDE_CONFIG_DIR=/tmp/agy claude"), "실행 자리: 대입 값 속 agy 는 프로그램이 아니다");
        assert!(names_agy("CLAUDE_CONFIG_DIR=/tmp/agy claude"), "기계 입구: 낱말이 있으면 거부(받아들인 거짓 양성)");
        assert!(!is_agy_adapter("gemini", Some("gemini --api-key-mode")), "같은 키라도 실행 프로그램이 agy 가 아니면 막지 않는다");
        assert!(is_agy_adapter("gemini", None), "cmd 가 없을 때만 키로 추정");
    }

    #[test]
    fn independent_rereview_parser_cases() {
        // 독립 재검(2R 반영분) 재현 — 전부 문 닫힘에서 agy 로 판정돼야 한다
        for agy in ["env -vSagy", "env -iSagy", "env -vS'agy -p'", "env -ivS agy", "env --split=agy", "env --spl=agy",
                    "env --unset FOO agy", "env --chdir /tmp agy", "env --argv0 x agy", "env -u FOO -C /tmp agy",
                    "cd /x && agy", "cd /x; agy", "cd /x || agy", "true | agy", "(cd /x; agy)", "bash -c 'cd /x && agy'",
                    "bash --norc -c agy", "bash --rcfile /x -lc agy", "exec -a name agy", "caffeinate -t 10 agy",
                    "caffeinate -w 123 agy", "caffeinate -dims agy", "stdbuf -o L agy", "stdbuf -oL agy", "timeout 5 agy",
                    "timeout -s KILL 5 agy", "gtimeout --signal=TERM 5 agy", "xargs agy", "xargs -n1 agy", "sudo agy",
                    "sudo -u root -E agy", "doas -u me agy", "script -q /dev/null agy", "script -c 'agy -p'",
                    "arch -arm64 agy", "arch -arch arm64 agy", "nice -n 5 agy", "nice -10 agy", "command -p agy",
                    "echo $(agy)", "cat <(agy)", "echo `agy`", "if true; then agy; fi", "! agy", "{ agy; }"] {
            assert!(both(agy), "{agy}");
            assert!(launch_refusal_with("claude", Some(agy), false).is_some(), "키가 claude 여도 cmd 가 agy 면 거부: {agy}");
        }
        for ok in ["claude --dangerously-skip-permissions", "env -u FOO claude", "env -iS 'claude --x'", "cd /x && claude",
                   "bash --norc -c claude", "timeout 5 claude", "sudo -u me codex", "claude 2>&1", "echo agy",
                   "CLAUDE_CONFIG_DIR=/tmp/agy claude", "codex exec -s read-only"] {
            assert!(!runs_agy(ok), "{ok}");
        }
        let argv = |v: &[&str]| v.iter().map(|s| s.to_string()).collect::<Vec<_>>();
        assert!(launch_refusal_argv_with(&argv(&["env", "-iSagy"]), false).is_some());
        assert!(launch_refusal_argv_with(&argv(&["timeout", "5", "agy"]), false).is_some());
        assert!(launch_refusal_argv_with(&argv(&["true", "&&", "agy"]), false).is_some());
    }

    #[test]
    fn every_other_entry_is_gated_source_pin() {
        // 독립 검증 B1·B2·M3: 문 판정 없이 셸 문을 실행하던 입구 — 판정 줄을 지우면 붉다(배선 핀).
        let root = Path::new(env!("CARGO_MANIFEST_DIR"));
        let pins: [(&str, &str); 15] = [
            ("src/bin/cysd/schedule.rs", "if let Some(m) = cys::agy_door::launch_refusal(\"\", Some(command)) {"),
            ("src/bin/cysd/channels.rs", "if let Some(m) = cys::agy_door::launch_refusal(\"\", Some(bridge_cmd)) {"),
            ("src/bin/cysd/accounts.rs", "if cys::agy_door::launch_refusal(\"\", Some(&cmd)).is_some() {"),
            ("src/bin/cysd/handlers.rs", "let by_meta = meta.as_ref().is_some_and(|(k, bin)| cys::agy_door::program_refused(k, bin));"),
            ("src/bin/cysd/handlers.rs", "let by_kind = surface.agy_kind && !cys::agy_door::door_open();"),
            ("src/bin/cysd/handlers.rs", "if let Some(m) = cys::agy_door::create_refusal(declared_agent.as_deref(), param_str(&params, \"cmd\").as_deref()) {"),
            ("src/bin/cysd/handlers.rs", "if !human_typed_q && agy_door_blocks_auto_send(&surface, &params, &text) {"),
            ("src/bin/cysd/state.rs", "agy_kind: cys::agy_door::seat_kind_is_agy(agent.as_deref(), cmd_for_kind.as_deref()),"),
            ("src/bin/cysd/handlers.rs", "&& cys::agy_door::launch_refusal(\"\", Some(text)).is_some())"),
            ("src/bin/cysd/schedule.rs", "if let Some(m) = cys::agy_door::launch_refusal(\"\", Some(cmd)) {"),
            ("src/bin/cys.rs", "if let Some(m) = command.as_deref().and_then(|c| cys::agy_door::launch_refusal(\"\", Some(c))) {"),
            ("src/bin/cys.rs", "if let Some(m) = cmd.as_deref().and_then(|c| cys::agy_door::launch_refusal(\"\", Some(c))) {"),
            ("cysjavis-pack/bin/javis_orchestra.py", "_refuse = agy_door_refusal(args.from_cmd)"),
            ("cysjavis-pack/bin/javis_orchestra.py", "[cys, \"agy-door-check\", \"--machine\", \"--cmd\", cmd]"),
            ("src/bin/cysd/handlers.rs", "if !human_typed {\n                if agy_door_blocks_auto_send(&surface, &params, &text) {"),
        ];
        for (f, needle) in pins {
            let src = std::fs::read_to_string(root.join(f)).unwrap();
            assert!(src.contains(needle), "{f}: 문 판정 줄 부재 — {needle}");
        }
        // 발화 판정은 셸 스폰보다 앞
        let sch = std::fs::read_to_string(root.join("src/bin/cysd/schedule.rs")).unwrap();
        let f = sch.find("async fn fire_command").unwrap();
        assert!(sch[f..].find("launch_refusal").unwrap() < sch[f..].find("command_shell()").unwrap());
    }

    #[test]
    fn verify_966_reducible_bypasses() {
        // 독립 검증(966) §3 「목록으로 줄일 수 있는 부류」 · 출하 키 gemini cmd 앞 리다이렉트
        for agy in [">/dev/null agy", "2>&1 agy", "</dev/null agy", ">/dev/null ~/.local/bin/agy --dangerously-skip-permissions",
                    "&>/dev/null agy", "noglob agy", "nocorrect agy", "builtin exec agy", "coproc agy", "repeat 1 agy", "=agy",
                    "- agy", "csh -c 'agy'", "tcsh -c 'agy -p'", "fish -c 'agy'", "su -c 'agy' me", "busybox sh -c 'agy'",
                    "$'agy'", "a^gy", "echo agy | sh", "printf agy | bash -s", "echo hi\nagy", "start agy", "call agy",
                    "wsl agy", "watch agy", "flock /tmp/l agy", "tmux new -d agy", "screen -dm agy", "npx @google/antigravity",
                    "sh -o errexit -c agy"] {
            assert!(both(agy), "{agy}");
        }
        assert!(launch_refusal_with("gemini", Some(">/dev/null ~/.local/bin/agy --dangerously-skip-permissions"), false).is_some());
        for ok in ["claude 2>&1", "claude >/tmp/agy.log", "cat x | sh", "echo agy | grep a", "claude --dangerously-skip-permissions 2>/dev/null"] {
            assert!(!runs_agy(ok), "{ok}");
        }
    }

    #[test]
    fn codex_3r_executors_and_false_positives() {
        for agy in ["cmd.exe /c agy", "cmd /C \"agy -p x\"", "powershell.exe -Command agy", "pwsh -c agy",
                    "powershell -File C:\\x\\agy.ps1", "powershell agy", "find . -maxdepth 0 -exec agy ';'",
                    "bash -O extglob -c agy", "bash -o pipefail -c 'agy'", "bash <<< agy", "bash <<<'agy -p'",
                    "cd /tmp && \\\nagy", "ag\\y", "/x/ag\\y -p", "unknownwrapper --flag agy", "claude -p \"$(agy)\""] {
            assert!(both(agy), "{agy}");
        }
        for ok in ["claude -p \"$(cat docs/agy.md)\"", "command -v agy", "which agy", "claude -p \"agy 를 설명해\"",
                   "ls ~/.local/bin/agy", "claude --settings '/x/agy-notes/worker.json'", "echo '$(agy)'"] {
            assert!(!runs_agy(ok), "{ok}");
        }
        let argv = |v: &[&str]| v.iter().map(|s| s.to_string()).collect::<Vec<_>>();
        for a in [argv(&["cmd.exe", "/c", "agy"]), argv(&["powershell.exe", "-Command", "agy"]),
                  argv(&["find", ".", "-exec", "agy", ";"]), argv(&["bash", "-O", "extglob", "-c", "agy"])] {
            assert!(launch_refusal_argv_with(&a, false).is_some(), "{a:?}");
        }
        assert!(launch_refusal_argv_with(&argv(&["command", "-v", "agy"]), false).is_none());
    }

    #[test]
    fn codex_2r_env_split_string() {
        for agy in ["env -S agy", "env -S 'agy -p hi'", "env -S'FOO=1 agy'", "env --split-string='agy x'",
                    "env --split-string agy", "env -i -S agy", "/usr/bin/env -S \"nohup agy\"", "env -S 'env -S agy'"] {
            assert!(both(agy), "{agy}");
        }
        assert!(!runs_agy("env -S 'claude --x'"));
        let argv = |v: &[&str]| v.iter().map(|s| s.to_string()).collect::<Vec<_>>();
        for a in [argv(&["agy"]), argv(&["env", "-S", "agy -p 'it''s'"]), argv(&["/x/agy", "it's"]),
                  argv(&["nohup", "env", "A=1", "agy"]), argv(&["sh", "-c", "agy"])] {
            assert!(launch_refusal_argv_with(&a, false).is_some(), "{a:?}");
            assert!(launch_refusal_argv_with(&a, true).is_none(), "문 열림이면 거부 없음 {a:?}");
        }
        assert!(launch_refusal_argv_with(&argv(&["claude", "-p", "agy 를 설명해"]), false).is_none(), "인용된(공백 든) 프롬프트 글 속 agy 는 프로그램이 아니다");
        assert!(launch_refusal_argv_with(&argv(&["claude", "agy"]), false).is_none(), "프롬프트 CLI 의 인자 = 사람 말(codex 4R major 5)");
        assert!(launch_refusal_argv_with(&argv(&["mytool", "agy"]), false).is_some(), "맨 낱말 agy = 안전망(codex 3R · 열거 못 한 실행 래퍼 대비)");
        assert!(launch_refusal_argv_with(&argv(&["echo", "it's", "agy"]), false).is_none());
    }

    #[test]
    fn agy_adapter_by_key_or_program() {
        assert!(is_agy_adapter("gemini", None));
        assert!(is_agy_adapter("Gemini", Some("")), "읽을 수 없는 cmd = 키 추정");
        for c in ["~/.local/bin/agy --dangerously-skip-permissions", "FOO=1 BAR=\"x\" /opt/x/agy -p hi",
                  r"C:\Users\x\AppData\Roaming\npm\agy.cmd", "antigravity.exe"] {
            assert!(is_agy_adapter("rv", Some(c)) && runs_agy(c), "{c}");
        }
        assert!(!is_agy_adapter("claude", Some("claude --dangerously-skip-permissions")));
        assert!(!is_agy_adapter("codex", Some("codex")));
        assert!(!is_agy_adapter("rv", Some("/opt/agyx/bin/claude")), "디렉터리 이름이 agyx — agy 낱말 아님");
        assert!(!is_agy_adapter("rv", None));
    }

    #[test]
    fn door_closed_unless_marked_body() {
        assert!(!door_body_is_open(""));
        assert!(!door_body_is_open("{}"));
        assert!(!door_body_is_open(r#"{"open": true}"#), "표지 없는 손 파일은 닫힘");
        assert!(!door_body_is_open(r#"{"open": "true", "ack": "agy-consumer-plan-warning-v1"}"#));
        assert!(!door_body_is_open(r#"{"open": false, "ack": "agy-consumer-plan-warning-v1"}"#));
        assert!(door_body_is_open(r#"{"open": true, "ack": "agy-consumer-plan-warning-v1"}"#));
    }

    #[test]
    fn write_then_read_then_close() {
        let d = td("rw");
        let p = door_path_under(&d);
        assert!(!door_open_at(&p), "기본 = 닫힘(파일 없음)");
        assert!(write_door_at(&p, true).unwrap(), "열기 반환 = 열림");
        assert!(door_open_at(&p));
        assert!(!write_door_at(&p, false).unwrap(), "닫기 반환 = 닫힘");
        assert!(!door_open_at(&p) && !p.exists());
        assert!(!write_door_at(&p, false).unwrap()); // 이미 닫힘 = 성공
        let _ = std::fs::remove_dir_all(&d);
    }

    #[cfg(unix)]
    #[test]
    fn symlinked_door_is_closed() {
        let d = td("ln");
        let real = d.join("real.json");
        std::fs::write(&real, format!(r#"{{"open": true, "ack": "{DOOR_ACK}"}}"#)).unwrap();
        let p = door_path_under(&d);
        std::fs::create_dir_all(p.parent().unwrap()).unwrap();
        std::os::unix::fs::symlink(&real, &p).unwrap();
        assert!(!door_open_at(&p), "심링크 문 = 닫힘");
        let _ = std::fs::remove_dir_all(&d);
    }

    #[test]
    fn env_never_opens_the_door() {
        // 이 모듈은 환경 변수를 한 번도 읽지 않는다(소스 고정) — Claude 가 명령 앞에 붙이는 한 줄로 열리는 길 0.
        //   예외 하나 = 프로그램 찾기용 `PATH`(`search_path` · codex 5R blocking 1 ⓐ — 문 상태와 무관 · 그 함수 밖에서는 0).
        let src = include_str!("agy_door.rs");
        let body = src.split("#[cfg(test)]").next().unwrap();
        let sp = body.find("fn search_path()").expect("search_path");
        let sp_end = sp + body[sp..].find("\n}\n").unwrap();
        assert!(body[sp..sp_end].contains("var_os(\"PATH\")") && body[sp..sp_end].matches("var_os").count() == 1, "PATH 밖을 읽는다");
        let rest = format!("{}{}", &body[..sp], &body[sp_end..]);
        assert!(!rest.contains("env::var") && !rest.contains("env_compat") && !rest.contains("var_os"), "문 판정이 환경 변수를 읽는다");
    }

    #[test]
    fn refusal_and_skip_follow_the_door() {
        assert!(launch_refusal_with("gemini", None, false).is_some_and(|m| m.starts_with(REFUSE_CODE)));
        assert!(launch_refusal_with("gemini", None, true).is_none(), "문을 열면 종전대로");
        assert!(launch_refusal_with("claude", Some("claude"), false).is_none(), "agy 아닌 어댑터는 무관");
        assert!(restore_skip_line_with("reviewer-gemini", "gemini", None, false).is_some_and(|l| l.contains(REFUSE_CODE)));
        assert!(restore_skip_line_with("reviewer-gemini", "gemini", None, true).is_none());
        assert!(restore_skip_line_with("worker", "claude", Some("claude"), false).is_none());
    }

    #[test]
    fn only_the_gui_writes_the_door() {
        // ★문 쓰기(`write_door`)를 부르는 제품 코드는 앱 화면 백엔드(src-tauri) 하나뿐이어야 한다 —
        //   cys CLI·데몬·팩(지침·스킬·복원기·훅)에는 문을 여는 길이 0 이다(⑤ Claude 가 스스로 여는 길 0).
        let root = Path::new(env!("CARGO_MANIFEST_DIR"));
        let mut offenders = Vec::new();
        let mut stack = vec![root.join("src"), root.join("cysjavis-pack")];
        while let Some(dir) = stack.pop() {
            let Ok(rd) = std::fs::read_dir(&dir) else { continue };
            for e in rd.flatten() {
                let p = e.path();
                if p.is_dir() {
                    stack.push(p);
                    continue;
                }
                if p.file_name().is_some_and(|n| n == "agy_door.rs") {
                    continue;
                }
                let Ok(s) = std::fs::read_to_string(&p) else { continue };
                if s.contains("write_door") || s.contains("agy_seat_door_set") {
                    offenders.push(p.display().to_string());
                }
            }
        }
        assert!(offenders.is_empty(), "앱 화면 밖에서 문을 여는 코드: {offenders:?}");
        let gui = std::fs::read_to_string(root.join("src-tauri/src/main.rs")).unwrap();
        assert!(gui.contains("agy_door::write_door("), "앱 화면이 문을 여는 유일한 입구여야 한다");
    }

    // ── TICKET=cysr-agy-door-r5(codex 4R 처분) ──

    /// 변이 생성 — 이름(2) × 대소문자(3) × 확장자(7) × 경로 머리(6) × 인용·치환 꼴(10) × 명령 문맥(17).
    fn mutations() -> Vec<String> {
        let mut out = Vec::new();
        for name in ["agy", "antigravity"] {
            let cases = [name.to_string(), name.to_ascii_uppercase(),
                         name.char_indices().map(|(i, c)| if i % 2 == 0 { c.to_ascii_uppercase() } else { c }).collect()];
            for n in cases {
                for ext in ["", ".exe", ".cmd", ".bat", ".ps1", ".com", ".EXE"] {
                    for pre in ["", "/opt/", "./", "~/.local/bin/", r"C:\Users\u\AppData\Roaming\npm\", r".\"] {
                        let exe = format!("{pre}{n}{ext}");
                        for q in ["{}", "'{}'", "\"{}\"", "$'{}'", "`{}`", "$({})", "<({})", "\"$({})\"", "{}.", "${X:-{}}"] {
                            let w = q.replace("{}", &exe);
                            for ctx in ["{}", "{} -p hi", "call {}", "start \"\" {}", "watch {}", "flock /tmp/l {}",
                                        "true $(printf ')'); {}", "cmd /c {}", "powershell -Command \"& {}\"", "x=1; {}",
                                        "nohup {} &", "sudo -u me {}", "echo hi | {}", "find . -exec {} ';'", "{}>/dev/null",
                                        "claude -p {}", "env -S {}"] {
                                out.push(ctx.replace("{}", &w));
                            }
                        }
                    }
                }
            }
        }
        // 이름 안에 셸·cmd 가 걷어 내는 글자를 끼운 꼴(`a''gy` · `ag\y` · `a^gy` · ``a``gy``) — 원문엔 글자가 이어져 있지 않다.
        for sp in ["''", "\"\"", "\\", "^", "``"] {
            for (a, b) in [("a", "gy"), ("ag", "y"), ("anti", "gravity")] {
                for ctx in ["{}", "call {}", "watch \"{}\"", "cmd /c {}"] {
                    out.push(ctx.replace("{}", &format!("{a}{sp}{b}")));
                }
            }
        }
        out
    }

    #[test]
    fn machine_word_check_catches_every_mutation() {
        let all = mutations();
        assert!(all.len() > 30_000, "변이 수 {}", all.len());
        let passed: Vec<&String> = all.iter().filter(|c| !names_agy(c)).collect();
        assert!(passed.is_empty(), "이름이 글자로 들어 있는데 통과 {}건(변이 {}): {:?}", passed.len(), all.len(), &passed[..passed.len().min(5)]);
        for c in all.iter().step_by(97) {
            assert!(launch_refusal_with("", Some(c), false).is_some(), "{c}");
            assert!(launch_refusal_with("", Some(c), true).is_none(), "문 열림 = 종전대로 {c}");
        }
    }

    #[test]
    fn machine_word_check_codex_4r_reproductions() {
        // codex 4R blocking 2(치환 괄호 깊이) · blocking 3(call·start·watch·flock 의 인용된 agy)
        for c in ["true $(printf ')'); \"/opt/agy\"", r#"call "C:\Users\u\AppData\Roaming\npm\agy.cmd""#,
                  r#"start "" "C:\Users\u\AppData\Roaming\npm\agy.cmd""#, "watch \"/opt/agy\"", "flock /tmp/l \"/opt/agy\""] {
            assert!(names_agy(c), "{c}");
            assert!(launch_refusal_with("", Some(c), false).is_some_and(|m| m.starts_with(REFUSE_CODE)), "{c}");
        }
        // 실행 자리(guard)에서도 낱말 하나 전체가 agy 경로면 인용돼 있어도 잡는다(blocking 3)
        for c in [r#"call "C:\Users\u\AppData\Roaming\npm\agy.cmd""#, r#"start "" "C:\x\agy.cmd""#, "watch \"/opt/agy\"",
                  "flock /tmp/l \"/opt/agy\""] {
            assert!(runs_agy(c), "{c}");
        }
        // 받아들인 거짓 양성(기계 입구) — 낱말만 있어도 거부 · 실행 자리 판정은 막지 않는다
        for c in ["claude -p agy", "codex exec agy", "echo agy", "claude -p \"agy 를 설명해\"", "command -v agy",
                  "CLAUDE_CONFIG_DIR=/tmp/agy claude"] {
            assert!(names_agy(c), "기계 입구 거짓 양성(받아들임): {c}");
            assert!(!runs_agy(c), "실행 자리는 막지 않는다: {c}");
        }
        // 낱말이 아닌 것(기계 입구도 통과)
        for c in ["claude -p \"$(cat docs/agy.md)\"", "/opt/agyx/bin/claude", "claude --settings '/x/agy-notes/w.json'",
                  "claude >/tmp/agy.log", "agyx", "pagy", "agy_", "agy-cli", "안티그래비티 검토", "agy를"] {
            assert!(!names_agy(c), "{c}");
        }
    }

    #[test]
    fn exec_position_false_positives_codex_4r_major_5() {
        for ok in ["claude -p agy", "codex exec agy", "claude --dangerously-skip-permissions -p agy", "codex exec -s read-only agy",
                   "powershell -Command Write-Output 'agy'", "pwsh -c \"Write-Host agy\"", "powershell Get-Command agy",
                   "echo agy", "claude -p \"agy 를 설명해\""] {
            assert!(!runs_agy(ok), "{ok}");
            assert!(exec_refusal_with(ok, false).is_none(), "{ok}");
        }
        let argv = |v: &[&str]| v.iter().map(|s| s.to_string()).collect::<Vec<_>>();
        for a in [argv(&["claude", "-p", "agy"]), argv(&["codex", "exec", "agy"]), argv(&["powershell", "-Command", "Write-Output", "agy"])] {
            assert!(launch_refusal_argv_with(&a, false).is_none(), "{a:?}");
        }
        // 프롬프트 CLI 면제는 다른 프로그램을 실행·등록하는 하위 명령에는 쓰지 않는다
        for agy in ["claude mcp add gem -- agy", "claude mcp add gem -- \"/opt/agy\"", "codex sandbox macos agy",
                    "codex debug seatbelt /opt/agy", "claude -p hi; agy", "claude -p \"$(agy)\""] {
            assert!(runs_agy(agy), "{agy}");
        }
        assert!(launch_refusal_argv_with(&argv(&["claude", "mcp", "add", "g", "--", "agy"]), false).is_some());
    }

    #[test]
    fn judge_input_caps_codex_4r_minor_8() {
        let big = format!("claude -p '{}'", "x".repeat(MAX_JUDGE_BYTES));
        assert!(names_agy(&big) && runs_agy(&big), "상한 초과 = 안전 쪽");
        let m = launch_refusal_with("", Some(&big), false).unwrap();
        assert!(m.starts_with(REFUSE_CODE) && m.contains("너무 길어서"), "{}", &m[m.len().saturating_sub(200)..]);
        assert!(launch_refusal_with("", Some(&big), true).is_none(), "문 열림 = 판정 안 함");
        assert!(launch_refusal_argv_with(&["claude".into(), "x".repeat(MAX_JUDGE_BYTES + 1)], false).is_some());
        let ok = format!("{}{}", "echo $(true); ".repeat(MAX_SUBSTS + 1), "claude -p hi");
        assert!(!runs_agy(&ok), "치환 수 초과 + agy 낱말 없음 = 통과");
        let bad = format!("{}{}", "echo $(true); ".repeat(MAX_SUBSTS + 1), "claude -p 'agy docs'");
        assert!(runs_agy(&bad), "치환 수 초과 + agy 낱말 = 안전 쪽(구조를 읽지 않는다)");
    }

    #[test]
    fn refusal_texts_tell_why_and_how() {
        let m = launch_refusal_with("", Some("claude -p 'review agy door'"), false).unwrap();
        assert!(m.starts_with(REFUSE_CODE) && m.contains("낱말") && m.contains("다른 말") && m.contains("좌석 열기"), "{m}");
        let e = exec_refusal_with("agy -p x", false).unwrap();
        assert!(e.starts_with(REFUSE_CODE) && !e.contains("낱말"), "실행 자리 거부는 낱말 덧말이 없다: {e}");
        let k = launch_refusal_with("gemini", None, false).unwrap();
        assert!(!k.contains("낱말"), "어댑터 키 추정 거부는 덧말 없음");
    }

    #[test]
    fn program_path_checks_name_only() {
        assert!(program_is_agy("/x/agy") && program_is_agy(r"C:\npm\AGY.CMD") && program_is_agy("antigravity"));
        assert!(!program_is_agy("/Users/agy/.local/bin/claude"), "폴더 이름(사용자 이름 agy)으로 오판하지 않는다");
        assert!(program_refused_with("gemini", "", false) && !program_refused_with("gemini", "", true));
        assert!(!program_refused_with("claude", "/usr/local/bin/claude", false));
    }

    #[test]
    fn door_open_close_race_serialized_codex_4r_minor_7() {
        // 여러 스레드가 열기/닫기를 섞어 누른다 — 쓰기마다 ⑴ 실패 0(고유 임시본) ⑵ 반환 상태 = 그 쓰기가 원한 상태
        //   (같은 임계 구역 안에서 읽음 = 그 사이 다른 쓰기가 끼지 않았다) ⑶ 끝난 뒤 임시본 0.
        let d = td("race");
        let p = door_path_under(&d);
        let errs = std::sync::Arc::new(std::sync::Mutex::new(Vec::<String>::new()));
        let hs: Vec<_> = (0..8)
            .map(|t| {
                let (p, errs) = (p.clone(), errs.clone());
                std::thread::spawn(move || {
                    for k in 0..150 {
                        let want = (t + k) % 2 == 0;
                        match write_door_at(&p, want) {
                            Ok(got) if got == want => {}
                            Ok(got) => errs.lock().unwrap().push(format!("t{t} k{k}: want {want} got {got}")),
                            Err(e) => errs.lock().unwrap().push(format!("t{t} k{k}: {e}")),
                        }
                    }
                })
            })
            .collect();
        for h in hs {
            h.join().unwrap();
        }
        let errs = errs.lock().unwrap();
        assert!(errs.is_empty(), "경합 결함 {}건: {:?}", errs.len(), &errs[..errs.len().min(5)]);
        let left: Vec<_> = std::fs::read_dir(p.parent().unwrap()).unwrap().flatten()
            .filter(|e| e.file_name().to_string_lossy().ends_with(".tmp")).map(|e| e.file_name()).collect();
        assert!(left.is_empty(), "임시본 잔존 {left:?}");
        // 다른 프로세스(앱 두 벌)가 쓰는 중인 임시본(종전 고정 이름)을 건드리지 않는다 — 고유 임시본
        let foreign = p.with_extension("json.tmp");
        std::fs::write(&foreign, "foreign-in-flight").unwrap();
        write_door_at(&p, true).unwrap();
        assert_eq!(std::fs::read_to_string(&foreign).ok().as_deref(), Some("foreign-in-flight"), "남의 임시본을 덮거나 옮겼다");
        std::fs::remove_file(&foreign).unwrap();
        // 마지막에 누른 닫기가 이긴다
        write_door_at(&p, true).unwrap();
        assert!(!write_door_at(&p, false).unwrap() && !door_open_at(&p));
        let _ = std::fs::remove_dir_all(&d);
    }

    // ── TICKET=cysr-agy-door-r6(codex 5R 처분) ──

    #[test]
    fn create_gate_and_seat_kind_codex_5r_blocking_2_3() {
        // 데몬 surface.create 판정(서버 권위) — cmd · 선언 agent 둘 다 낱말 검사
        for (agent, cmd) in [(None, Some("agy")), (None, Some("~/.local/bin/agy --x")), (Some("agy"), None), (Some("gemini"), None),
                             (Some("claude"), Some("true $(printf ')'); \"/opt/agy\"")), (Some("antigravity"), Some("bash"))] {
            assert!(seat_kind_is_agy(agent, cmd), "{agent:?} {cmd:?}");
            assert!(create_refusal_with(agent, cmd, false).is_some_and(|m| m.starts_with(REFUSE_CODE)), "{agent:?} {cmd:?}");
            assert!(create_refusal_with(agent, cmd, true).is_none(), "문 열림 = 종전대로");
        }
        for (agent, cmd) in [(None, None), (None, Some("sleep 30")), (Some("claude"), None), (Some("gemini"), Some("gemini --api"))] {
            assert!(!seat_kind_is_agy(agent, cmd) && create_refusal_with(agent, cmd, false).is_none(), "{agent:?} {cmd:?}");
        }
    }

    #[test]
    fn sh_c_positional_args_codex_5r_major_4() {
        for agy in ["sh -c 'exec \"$@\"' sh agy", "bash -c '\"$@\"' x agy -p hi", "zsh -c 'exec $1' z /opt/agy", "dash -c '$0' agy",
                    "env FOO=1 sh -c 'exec \"$@\"' sh agy", "sh -c 'exec \"${@}\"' sh env agy", "bash -lc 'exec \"$*\"' b agy",
                    "sh -c '\"$@\"' sh sh -c 'agy -p'"] {
            assert!(runs_agy(agy), "{agy}");
            assert!(names_agy(agy), "{agy}");
        }
        let argv = |v: &[&str]| v.iter().map(|s| s.to_string()).collect::<Vec<_>>();
        assert!(launch_refusal_argv_with(&argv(&["sh", "-c", "exec \"$@\"", "sh", "agy"]), false).is_some(), "cys run -- sh -c 'exec \"$@\"' sh agy");
        assert!(launch_refusal_argv_with(&argv(&["/usr/bin/env", "bash", "-c", "exec \"$@\"", "b", "/opt/agy"]), false).is_some());
        // 위치 인자가 자료일 뿐인 정상 꼴 · 위치 인자를 안 쓰는 글
        for ok in ["sh -c 'echo \"$1\"' sh agy-notes", "sh -c 'cat \"$1\"' sh docs/agy.md", "sh -c 'claude -p hi' sh agy-x"] {
            assert!(!runs_agy(ok), "{ok}");
        }
        assert!(launch_refusal_argv_with(&argv(&["sh", "-c", "echo \"$1\"", "sh", "agy-notes"]), false).is_none());
        assert!(uses_positional("a $1") && uses_positional("${@}") && uses_positional("$*") && !uses_positional("$HOME $x"));
    }

    #[test]
    fn too_long_text_does_not_prescribe_scripts_codex_5r_major_5() {
        let big = format!("claude -p '{}'", "x".repeat(MAX_JUDGE_BYTES));
        let m = launch_refusal_with("", Some(&big), false).unwrap();
        assert!(!m.contains("스크립트") && !m.contains("파일로"), "우회(스크립트 파일)를 처방한다: {m}");
        assert!(m.contains("줄여") && m.contains("사람이 직접"), "{m}");
    }

    #[test]
    fn exe_path_vs_command_string_codex_5r_minor_7() {
        // 실행 파일 경로(공백 든 경로 포함) = 마지막 이름만 · 명령 문자열 = 낱말 검사(서로 다른 함수)
        assert!(!program_is_agy("/Users/agy/Application Support/claude"), "공백 든 경로의 폴더 이름 agy 는 프로그램이 아니다");
        assert!(!program_is_agy(r"C:\Users\agy\App Data\claude.exe"));
        assert!(program_is_agy("/Users/me/Application Support/agy") && program_is_agy(r"C:\Program Files\x\agy.cmd"));
        assert!(!program_refused_with("claude", "/Users/agy/Application Support/claude", false));
        assert!(names_agy("/Users/agy/Application Support/claude"), "명령 문자열로 읽으면 기계 입구는 막는다(받아들인 거짓 양성)");
    }

    #[test]
    fn argv_cap_counts_separators_and_args_codex_5r_minor_8() {
        let empties = vec![String::new(); MAX_JUDGE_ARGS + 1];
        assert!(launch_refusal_argv_with(&empties, false).is_some(), "빈 인자 대량 = 안전 쪽");
        let near = vec!["x".to_string(); MAX_JUDGE_BYTES / 2];   // Σ(1+1) = 상한 → 개수 상한도 넘음
        assert!(launch_refusal_argv_with(&near, false).is_some());
        let ok = vec!["echo".to_string(), "hi".to_string()];
        assert!(launch_refusal_argv_with(&ok, false).is_none());
    }

    #[cfg(unix)]
    #[test]
    fn symlink_and_one_level_script_codex_5r_blocking_1() {
        use std::os::unix::fs::PermissionsExt;
        let d = td("resolve");
        let fake = d.join("agy");
        std::fs::write(&fake, "#!/bin/sh\nexit 0\n").unwrap();
        std::fs::set_permissions(&fake, std::fs::Permissions::from_mode(0o755)).unwrap();
        let link = d.join("gem-review");
        std::os::unix::fs::symlink(&fake, &link).unwrap();
        let ds = d.display();
        // ⓐ 심링크 = 실제 이름
        assert!(resolves_to_agy(&format!("{ds}/gem-review -p hi")), "심링크");
        assert!(launch_refusal_with("", Some(&format!("{ds}/gem-review -p hi")), false).is_some());
        assert!(program_is_agy(&link.to_string_lossy()), "좌석 메타 실행 파일이 심링크");
        // ⓑ 셸에 넘긴 스크립트 · 셔뱅 글 파일 직접 실행 · source
        let job = d.join("review.sh");
        std::fs::write(&job, format!("# runs the reviewer\ncd /tmp\nexec {ds}/agy -p hi\n")).unwrap();
        for c in [format!("sh {}", job.display()), format!("bash -e {}", job.display()), format!("zsh {}", job.display()),
                  format!("source {}", job.display()), format!(". {}", job.display())] {
            assert!(resolves_to_agy(&c), "{c}");
            assert!(launch_refusal_with("", Some(&c), false).is_some(), "{c}");
        }
        let direct = d.join("nightly");
        std::fs::write(&direct, "#!/bin/bash\nset -e\nagy -p hi\n").unwrap();
        std::fs::set_permissions(&direct, std::fs::Permissions::from_mode(0o755)).unwrap();
        assert!(resolves_to_agy(&direct.to_string_lossy()), "셔뱅 셸 글 파일 직접 실행");
        let env_she = d.join("viaenv");
        std::fs::write(&env_she, "#!/usr/bin/env agy\n-p hi\n").unwrap();
        assert!(resolves_to_agy(&env_she.to_string_lossy()), "셔뱅 줄 자체가 agy");
        // 정상 꼴(거짓 양성 없음): 스크립트가 agy 를 말만 함 · 파이썬 글(셸로 안 읽음) · 주석 · 두 단계 간접은 보지 않음(한계)
        let talk = d.join("talk.sh");
        std::fs::write(&talk, "#!/bin/sh\n# agy\necho agy\nclaude -p 'agy 검토'\n").unwrap();
        assert!(!resolves_to_agy(&format!("sh {}", talk.display())), "말만 하는 스크립트");
        let py = d.join("tool.py");
        std::fs::write(&py, "#!/usr/bin/env python3\nagy = 1\nprint(agy)\n").unwrap();
        std::fs::set_permissions(&py, std::fs::Permissions::from_mode(0o755)).unwrap();
        assert!(!resolves_to_agy(&py.to_string_lossy()), "파이썬 본문은 셸로 읽지 않는다");
        let two = d.join("outer.sh");
        std::fs::write(&two, format!("sh {}\n", job.display())).unwrap();
        assert!(!resolves_to_agy(&format!("sh {}", two.display())), "두 단계 간접 = 이 판에서 막지 않는 것");
        // 못 읽는 스크립트 = 통과 + 표시
        let missing = format!("sh {ds}/nope.sh");
        assert!(!resolves_to_agy(&missing));
        assert!(resolve_targets(&missing).iter().any(|(t, m)| *m && t.ends_with("nope.sh")));
        let _ = std::fs::remove_dir_all(&d);
    }

    #[test]
    fn false_positive_table_codex_5r_item_5() {
        // codex 5R 「문제없다」 ⑤ — 기계 입구 낱말 검사의 거짓 양성(받아들임) vs 실행 파일 경로(③)에서 줄어든 것
        for c in ["grep agy log", "cat docs/agy/README", "/Users/agy/bin/claude -p hi"] {
            assert!(names_agy(c), "기계 입구 = 여전히 막힘(받아들인 거짓 양성): {c}");
            assert!(!runs_agy(c), "실행 자리 = 통과: {c}");
        }
        assert!(!program_is_agy("/Users/agy/bin/claude") && !program_is_agy("/Users/agy/Application Support/claude"), "③ 실행 파일 경로 = 통과");
    }

    #[test]
    fn door_write_waits_for_os_lock_codex_5r_minor_6() {
        // 다른 앱 프로세스가 옆 잠금 파일을 쥐고 있으면(같은 프로세스의 다른 열린 파일 = OS 에겐 다른 잠금 주체) 문 쓰기는 기다린다.
        let d = td("oslock");
        let p = door_path_under(&d);
        std::fs::create_dir_all(p.parent().unwrap()).unwrap();
        let other = std::fs::OpenOptions::new().create(true).truncate(false).write(true)
            .open(p.with_file_name(format!("{DOOR_FILE}.lock"))).unwrap();
        other.lock().unwrap();
        let p2 = p.clone();
        let h = std::thread::spawn(move || write_door_at(&p2, true));
        std::thread::sleep(std::time::Duration::from_millis(400));
        assert!(!door_open_at(&p), "다른 잠금 주체가 쥐고 있는 동안 문이 바뀌었다(앱 두 벌 경합 미직렬화)");
        other.unlock().unwrap();
        assert!(h.join().unwrap().unwrap() && door_open_at(&p));
        let _ = std::fs::remove_dir_all(&d);
    }

    #[test]
    fn sh_c_positional_mutations_r6() {
        // 새 꼴 변이(r6 · 5R major 4): 셸 7 × 플래그 3 × 위치 인자 참조 9 × 이름 6 — 문자열(guard)·argv(`cys run`) 둘 다 거부 ·
        //   대조 = 같은 틀에서 위치 인자가 자료(조회 명령 · agy 아닌 이름)면 통과.
        let argv = |v: &[String]| v.to_vec();
        let (mut n, mut bad) = (0usize, Vec::new());
        for sh in ["sh", "bash", "zsh", "dash", "/bin/sh", "/usr/bin/env bash", "env -i sh"] {
            for fl in ["-c", "-lc", "-ec"] {
                for r in ["$@", "\"$@\"", "$*", "\"$*\"", "$1", "${1}", "${@}", "exec \"$@\"", "$0"] {
                    for name in ["agy", "/opt/agy", "AGY", "agy.exe", "antigravity", "~/.local/bin/agy"] {
                        let (p0, p1) = if r == "$0" { (name.to_string(), None) } else { ("sh".to_string(), Some(name.to_string())) };
                        let mut v: Vec<String> = sh.split(' ').map(str::to_string).collect();
                        v.extend([fl.to_string(), r.to_string(), p0.clone()]);
                        v.extend(p1.clone());
                        let line = format!("{sh} {fl} '{r}' {p0} {}", p1.clone().unwrap_or_default());
                        n += 1;
                        if !runs_agy(&line) || launch_refusal_argv_with(&argv(&v), false).is_none() {
                            bad.push(line);
                        }
                    }
                    for data in ["agy-notes", "docs/agy.md", "agyx"] {
                        let line = format!("{sh} {fl} 'echo {r}' sh {data}");
                        if runs_agy(&line) {
                            bad.push(format!("거짓 양성: {line}"));
                        }
                    }
                }
            }
        }
        assert!(n == 7 * 3 * 9 * 6 && bad.is_empty(), "변이 {n} · 실패 {}: {:?}", bad.len(), &bad[..bad.len().min(5)]);
    }
}
