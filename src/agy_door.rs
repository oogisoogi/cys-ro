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
//! ★정직한 한계(operator.token 과 같은 등급): 이것은 **보안 경계가 아니라 거버넌스 구분**이다. 같은 OS 사용자로 도는
//!   프로세스는 문 파일을 직접 쓸 수 있다. 닫는 것은 「지침을 따르는 정상 노드가 평시 경로로 문을 여는 길」이고,
//!   직접 쓰기는 팩 훅 `guard.sh` 가 막으며(시험 고정) 지침이 금지한다.
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
구글 약관상 계정이 정지될 수 있습니다. 기업 요금제(Gemini Enterprise 등)처럼 이런 사용이 허용된 경우에만 여세요.";

/// 이 어댑터가 agy 인가(순수). **실행 프로그램이 정본**이다 — cmd 에서 실제로 실행될 프로그램(대입·래퍼·인용·
/// `sh -c` · `;`·`&&`·`|` 로 이은 다음 명령까지)이 하나라도 `agy`/`antigravity` 면 agy. cmd 가 없거나 읽을 수 없을 때만
/// 어댑터 키 `gemini`(출하 어댑터 = agy)로 추정한다(codex 1R major: 키만 보면 같은 키로 Gemini API 등 다른 프로그램을 쓰는
/// 사용자까지 막힌다). ★명령 치환(`$(…)`·백틱·`<(…)`)이 섞인 cmd 에 agy 낱말이 있으면 해석하지 않고 agy 로 본다(안전 쪽 ·
/// 독립 재검 2R+).
pub fn is_agy_adapter(agent_key: &str, cmd: Option<&str>) -> bool {
    let Some(c) = cmd else { return agent_key.eq_ignore_ascii_case("gemini") };
    if has_substitution(c) && mentions_agy(c) {
        return true;
    }
    let progs = programs_in(c, 0);
    if progs.is_empty() {
        return agent_key.eq_ignore_ascii_case("gemini");
    }
    progs.iter().any(|p| is_agy_name(p))
}

fn is_agy_name(p: &str) -> bool {
    p == "agy" || p == "antigravity"
}

fn has_substitution(s: &str) -> bool {
    s.contains("$(") || s.contains('`') || s.contains("<(") || s.contains(">(")
}

fn mentions_agy(s: &str) -> bool {
    s.to_ascii_lowercase().split(|c: char| !(c.is_ascii_alphanumeric() || c == '_' || c == '-')).any(is_agy_name)
}

/// 셸 비슷한 나누기(순수) — 인용 밖의 `;` `&` `|` `(` `)` 줄바꿈에서 **명령 단위**를 끊고, 단위 안은 낱말로 나눈다.
/// 홑·겹따옴표 안 공백 보존 · 역슬래시는 따옴표 밖에서 뒤 글자가 공백·따옴표일 때만 이스케이프(윈도우 경로 `C:\x\agy.cmd`).
fn segments(s: &str) -> Vec<Vec<String>> {
    let (mut segs, mut out, mut cur, mut any) = (Vec::new(), Vec::new(), String::new(), false);
    let mut it = s.chars().peekable();
    let mut q: Option<char> = None;
    let flush = |out: &mut Vec<String>, cur: &mut String, any: &mut bool| {
        if *any || !cur.is_empty() {
            out.push(std::mem::take(cur));
            *any = false;
        }
    };
    while let Some(c) = it.next() {
        match q {
            Some(qc) if c == qc => q = None,
            Some(_) => cur.push(c),
            None if c == '\\' && matches!(it.peek(), Some(n) if n.is_whitespace() || *n == '"' || *n == '\'') => {
                cur.push(it.next().unwrap());
                any = true;
            }
            None if c == '\'' || c == '"' => {
                q = Some(c);
                any = true;
            }
            None if matches!(c, ';' | '&' | '|' | '(' | ')' | '\n') => {
                flush(&mut out, &mut cur, &mut any);
                if !out.is_empty() {
                    segs.push(std::mem::take(&mut out));
                }
            }
            None if c.is_whitespace() => flush(&mut out, &mut cur, &mut any),
            None => cur.push(c),
        }
    }
    flush(&mut out, &mut cur, &mut any);
    if !out.is_empty() {
        segs.push(out);
    }
    segs
}

fn is_assignment(w: &str) -> bool {
    let Some((k, _)) = w.split_once('=') else { return false };
    !k.is_empty() && k.chars().all(|c| c.is_ascii_alphanumeric() || c == '_') && !k.starts_with(|c: char| c.is_ascii_digit())
}

/// cmd 문자열 → 실제로 실행될 프로그램 이름들(소문자 · 경로·확장자 제거 · 명령 단위마다 하나) — 깊이 3.
fn programs_in(cmd: &str, depth: u8) -> Vec<String> {
    segments(cmd).iter().flat_map(|w| program_of(w, depth)).collect()
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
        _ => return None,
    })
}

fn program_of(w: &[String], depth: u8) -> Vec<String> {
    const KW: [&str; 10] = ["!", "{", "}", "then", "do", "else", "elif", "if", "while", "until"];
    let mut i = 0;
    while i < w.len() {
        let t = &w[i];
        if is_assignment(t) || KW.contains(&t.as_str()) {
            i += 1;
            continue;
        }
        let base = basename_lc(t);
        if base == "env" {
            i += 1;
            while i < w.len() {
                let a = w[i].as_str();
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
                    if !name.is_empty() && "split-string".starts_with(name) && depth < 3 {
                        let (v, next) = match val { Some(v) => (v.to_string(), i + 1), None => (w.get(i + 1).cloned().unwrap_or_default(), i + 2) };
                        let mut rest = segments(&v).into_iter().next().unwrap_or_default();
                        rest.extend(w.get(next..).unwrap_or(&[]).iter().cloned());
                        return program_of(&rest, depth + 1);
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
                        let rest = &cl[k + ch.len_utf8()..];
                        if ch == 'S' && depth < 3 {
                            let (v, next) = if rest.is_empty() { (w.get(i + 1).cloned().unwrap_or_default(), i + 2) } else { (rest.to_string(), i + 1) };
                            let mut more = segments(&v).into_iter().next().unwrap_or_default();
                            more.extend(w.get(next..).unwrap_or(&[]).iter().cloned());
                            return program_of(&more, depth + 1);
                        }
                        if matches!(ch, 'u' | 'C' | 'P' | 'a') {
                            consumed_next = rest.is_empty();
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
        if depth < 3 && matches!(base.as_str(), "sh" | "bash" | "zsh" | "dash" | "ksh") {
            // `-c` = 정확히 한 줄표 묶음 안의 c(`-c`·`-lc`) — `--norc` 같은 긴 옵션은 -c 가 아니다(독립 재검).
            let mut j = i + 1;
            while j < w.len() {
                let a = w[j].as_str();
                if a == "--" || !(a.starts_with('-') || a.starts_with('+')) {
                    break;
                }
                if a.starts_with("--") {
                    j += if matches!(a, "--rcfile" | "--init-file") { 2 } else { 1 };
                    continue;
                }
                if a[1..].contains('c') {
                    let mut k = j + 1;
                    while k < w.len() && w[k].starts_with('-') && w[k] != "-" {
                        k += 1;
                    }
                    return w.get(k).map(|inner| programs_in(inner, depth + 1)).unwrap_or_default();
                }
                j += 1;
            }
            return vec![base];
        }
        if let Some((short, long, positional)) = wrapper_spec(&base) {
            i += 1;
            if base == "script" && depth < 3 {
                // 리눅스 script -c '<문>' — 값이 실행될 명령
                if let Some(k) = w[i..].iter().position(|a| a == "-c" || a == "--command") {
                    return w.get(i + k + 1).map(|inner| programs_in(inner, depth + 1)).unwrap_or_default();
                }
            }
            while i < w.len() {
                let a = w[i].as_str();
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
        return if base.is_empty() { vec![] } else { vec![base] };
    }
    vec![]
}

fn basename_lc(tok: &str) -> String {
    let base = tok.rsplit(['/', '\\']).next().unwrap_or(tok).to_ascii_lowercase();
    for ext in [".exe", ".cmd", ".bat", ".ps1", ".com"] {
        if let Some(s) = base.strip_suffix(ext) {
            return s.to_string();
        }
    }
    base
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
/// ★`cys` CLI·데몬·팩은 부르지 않는다(시험 `only_the_gui_writes_the_door`).
pub fn write_door(open: bool) -> Result<(), String> {
    write_door_at(&door_path(), open)
}

pub fn write_door_at(path: &Path, open: bool) -> Result<(), String> {
    if !open {
        return match std::fs::remove_file(path) {
            Ok(()) => Ok(()),
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(()),
            Err(e) => Err(format!("{}: {e}", path.display())),
        };
    }
    if let Some(dir) = path.parent() {
        std::fs::create_dir_all(dir).map_err(|e| format!("{}: {e}", dir.display()))?;
    }
    let at = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);
    let body = serde_json::json!({"open": true, "ack": DOOR_ACK, "opened_at_epoch": at, "by": "cysr-app"});
    let tmp = path.with_extension("json.tmp");
    std::fs::write(&tmp, format!("{body}\n")).map_err(|e| format!("{}: {e}", tmp.display()))?;
    std::fs::rename(&tmp, path).map_err(|e| format!("{}: {e}", path.display()))
}

/// 기동 거부 문안(왕초보가 읽는 말) — agy 어댑터이고 문이 닫혀 있으면 Some.
pub fn launch_refusal(agent_key: &str, cmd: Option<&str>) -> Option<String> {
    launch_refusal_with(agent_key, cmd, door_open())
}

/// argv(이미 나뉜 실행 인자 — `cys run -- <argv>`) 판. 문자열로 다시 이어 붙이지 않는다(codex 2R: 인용 재조립은
/// 따옴표가 든 인자에서 해석이 어긋난다). 어댑터 키가 없으므로 실행 프로그램으로만 판정한다.
pub fn launch_refusal_argv(argv: &[String]) -> Option<String> {
    launch_refusal_argv_with(argv, door_open())
}

pub fn launch_refusal_argv_with(argv: &[String], door_open: bool) -> Option<String> {
    let is_agy = argv
        .split(|a| matches!(a.as_str(), ";" | "&&" | "||" | "|" | "&"))
        .flat_map(|seg| program_of(seg, 0))
        .any(|p| is_agy_name(&p));
    if is_agy { launch_refusal_with("", Some("agy"), door_open) } else { None }
}

/// [`launch_refusal`] 의 순수판(문 상태 주입).
pub fn launch_refusal_with(agent_key: &str, cmd: Option<&str>, door_open: bool) -> Option<String> {
    (is_agy_adapter(agent_key, cmd) && !door_open).then(|| {
        format!(
            "{REFUSE_CODE}: cysr 은 Antigravity(agy) 좌석을 띄우지 않습니다 — 개인 요금제에서 다른 프로그램이 agy 를 \
             부리면 구글 약관상 계정이 정지될 수 있기 때문입니다. agy 를 직접 쓰려면 새 탭에서 `agy` 를 치세요(괜찮습니다). \
             기업 요금제 등 허용된 경우에만, 사람이 앱 명령 팔레트의 「Antigravity(agy) 좌석 열기」로 열 수 있습니다."
        )
    })
}

/// 복원 건너뜀 한 줄(실패로 세지 않는다) — agy 어댑터이고 문이 닫혀 있으면 Some.
pub fn restore_skip_line(role: &str, agent_key: &str, cmd: Option<&str>) -> Option<String> {
    restore_skip_line_with(role, agent_key, cmd, door_open())
}

pub fn restore_skip_line_with(role: &str, agent_key: &str, cmd: Option<&str>, door_open: bool) -> Option<String> {
    (is_agy_adapter(agent_key, cmd) && !door_open).then(|| {
        format!(
            "· {role}: 건너뜀({REFUSE_CODE}) — 구글 개인 요금제 약관 때문에 cysr 은 Antigravity(agy) 좌석을 다시 띄우지 \
             않습니다. 고장이 아닙니다 · 검토가 필요하면 Claude 대체 검토자가 대신합니다."
        )
    })
}

#[cfg(test)]
mod tests {
    use super::*;

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
            assert!(is_agy_adapter("rv", Some(agy)), "{agy}");
        }
        assert!(!is_agy_adapter("claude", Some("CLAUDE_CONFIG_DIR=/tmp/agy claude")), "대입 값 속 agy 는 프로그램이 아니다");
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
            assert!(is_agy_adapter("", Some(agy)), "{agy}");
            assert!(launch_refusal_with("claude", Some(agy), false).is_some(), "키가 claude 여도 cmd 가 agy 면 거부: {agy}");
        }
        for ok in ["claude --dangerously-skip-permissions", "env -u FOO claude", "env -iS 'claude --x'", "cd /x && claude",
                   "bash --norc -c claude", "timeout 5 claude", "sudo -u me codex", "claude 2>&1", "echo agy",
                   "CLAUDE_CONFIG_DIR=/tmp/agy claude", "codex exec -s read-only"] {
            assert!(!is_agy_adapter("", Some(ok)), "{ok}");
        }
        let argv = |v: &[&str]| v.iter().map(|s| s.to_string()).collect::<Vec<_>>();
        assert!(launch_refusal_argv_with(&argv(&["env", "-iSagy"]), false).is_some());
        assert!(launch_refusal_argv_with(&argv(&["timeout", "5", "agy"]), false).is_some());
        assert!(launch_refusal_argv_with(&argv(&["true", "&&", "agy"]), false).is_some());
    }

    #[test]
    fn codex_2r_env_split_string() {
        for agy in ["env -S agy", "env -S 'agy -p hi'", "env -S'FOO=1 agy'", "env --split-string='agy x'",
                    "env --split-string agy", "env -i -S agy", "/usr/bin/env -S \"nohup agy\"", "env -S 'env -S agy'"] {
            assert!(is_agy_adapter("", Some(agy)), "{agy}");
        }
        assert!(!is_agy_adapter("", Some("env -S 'claude --x'")));
        let argv = |v: &[&str]| v.iter().map(|s| s.to_string()).collect::<Vec<_>>();
        for a in [argv(&["agy"]), argv(&["env", "-S", "agy -p 'it''s'"]), argv(&["/x/agy", "it's"]),
                  argv(&["nohup", "env", "A=1", "agy"]), argv(&["sh", "-c", "agy"])] {
            assert!(launch_refusal_argv_with(&a, false).is_some(), "{a:?}");
            assert!(launch_refusal_argv_with(&a, true).is_none(), "문 열림이면 거부 없음 {a:?}");
        }
        assert!(launch_refusal_argv_with(&argv(&["claude", "agy"]), false).is_none(), "인자 속 agy 는 프로그램이 아니다");
        assert!(launch_refusal_argv_with(&argv(&["echo", "it's", "agy"]), false).is_none());
    }

    #[test]
    fn agy_adapter_by_key_or_program() {
        assert!(is_agy_adapter("gemini", None));
        assert!(is_agy_adapter("Gemini", Some("")), "읽을 수 없는 cmd = 키 추정");
        assert!(is_agy_adapter("rv", Some("~/.local/bin/agy --dangerously-skip-permissions")));
        assert!(is_agy_adapter("rv", Some("FOO=1 BAR=\"x\" /opt/x/agy -p hi")));
        assert!(is_agy_adapter("rv", Some(r"C:\Users\x\AppData\Roaming\npm\agy.cmd")));
        assert!(is_agy_adapter("rv", Some("antigravity.exe")));
        assert!(!is_agy_adapter("claude", Some("claude --dangerously-skip-permissions")));
        assert!(!is_agy_adapter("codex", Some("codex")));
        assert!(!is_agy_adapter("rv", Some("/opt/agyx/bin/claude")), "디렉터리 이름이 agy 여도 실행 파일이 아니면 아님");
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
        write_door_at(&p, true).unwrap();
        assert!(door_open_at(&p));
        write_door_at(&p, false).unwrap();
        assert!(!door_open_at(&p) && !p.exists());
        write_door_at(&p, false).unwrap(); // 이미 닫힘 = 성공
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
        let src = include_str!("agy_door.rs");
        let body = src.split("#[cfg(test)]").next().unwrap();
        assert!(!body.contains("env::var") && !body.contains("env_compat") && !body.contains("var_os"), "문 판정이 환경 변수를 읽는다");
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
}
