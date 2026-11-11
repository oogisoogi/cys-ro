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

/// 이 어댑터가 agy 인가(순수). **실행 프로그램이 정본**이다 — cmd 의 모든 명령 단위(`;`·`&&`·`|`·줄바꿈 · `sh -c` ·
/// `cmd /c` · `powershell -Command` · `find -exec` · 명령/프로세스 치환 본문 · here-string)에서 실행될 프로그램을 찾고,
/// 그중 하나라도 `agy`/`antigravity` 면 agy. ★안전망(codex 3R): 조회 전용 프로그램(echo·which·command -v 등)이 아니면
/// **인용 안 된 낱말**이 agy 이름이기만 해도 agy 로 본다(열거 못 한 실행 래퍼 대비 · 인용된 프롬프트 글 속 agy 는 세지 않음).
/// cmd 가 없거나 프로그램을 하나도 못 읽을 때만 어댑터 키 `gemini`(출하 어댑터 = agy)로 추정한다.
pub fn is_agy_adapter(agent_key: &str, cmd: Option<&str>) -> bool {
    let Some(c) = cmd else { return agent_key.eq_ignore_ascii_case("gemini") };
    let progs = scan(c, 0);
    if progs.is_empty() {
        return agent_key.eq_ignore_ascii_case("gemini");
    }
    progs.iter().any(|p| is_agy_name(p))
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
            if d != 0 {
                return None;
            }
            bodies.push(c[i + 2..j - 1].iter().collect());
            outer.push_str(" __subst__ ");
            i = j;
            continue;
        }
        if ch == '`' {
            let j = (i + 1..c.len()).find(|&k| c[k] == '`' && c[k - 1] != '\\')?;
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

/// 조회·출력만 하는 프로그램 — 인자 속 agy 낱말을 실행으로 세지 않는다.
const NON_EXEC: [&str; 17] = ["echo", "printf", "which", "type", "whereis", "test", "[", "ls", "cat", "grep", "rg", "man",
                               "file", "stat", "head", "tail", "wc"];

fn seg_programs(w: &[Tok], depth: u8) -> Vec<String> {
    let (mut progs, nonexec) = program_of(w, depth);
    if !nonexec
        && !progs.iter().any(|p| is_agy_name(p))
        && w.iter().any(|t| !t.quoted && !is_assignment(&t.text) && redirect_skip(t).is_none() && is_agy_word(&t.text))
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

/// 명령 단위 하나 → (실행될 프로그램들, 조회 전용인가).
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
                        return (scan(&format!("{v} {}", join(w.get(next..).unwrap_or(&[]))), depth + 1), false);
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
                            return (scan(&format!("{v} {}", join(w.get(next..).unwrap_or(&[]))), depth + 1), false);
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
                return (rest.get(k + 1).map(|t| scan(&t.text, depth + 1)).unwrap_or_default(), false);
            }
        }
        if matches!(base.as_str(), "sh" | "bash" | "zsh" | "dash" | "ksh" | "csh" | "tcsh" | "fish" | "mksh" | "yash") {
            // here-string(`bash <<< '문'`) = 표준 입력 스크립트
            if let Some(k) = rest.iter().position(|t| t.text.starts_with("<<<")) {
                let v = rest[k].text[3..].to_string();
                let v = if v.is_empty() { rest.get(k + 1).map(|t| t.text.clone()).unwrap_or_default() } else { v };
                return (scan(&v, depth + 1), false);
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
                    return (rest.get(k).map(|t| scan(&t.text, depth + 1)).unwrap_or_default(), false);
                }
                j += 1;
            }
            // 스크립트 파일 없이 뜬 셸 = 표준 입력을 실행한다(파이프 `… | sh`)
            let script = rest[j.min(rest.len())..].iter().any(|t| redirect_skip(t).is_none());
            return (vec![if script { base } else { STDIN_SHELL.into() }], false);
        }
        if base == "cmd" {
            // cmd.exe /c 문 · /k 문 — 뒤 전부가 실행될 명령
            if let Some(k) = rest.iter().position(|t| t.text.eq_ignore_ascii_case("/c") || t.text.eq_ignore_ascii_case("/k")) {
                return (scan(&join_plain(&rest[k + 1..]), depth + 1), false);
            }
            return (vec![base], false);
        }
        if matches!(base.as_str(), "powershell" | "pwsh") {
            let mut k = 0;
            while k < rest.len() {
                let a = rest[k].text.to_ascii_lowercase();
                if a.starts_with('-') && a.len() >= 2 && "-file".starts_with(&a) && a != "-" {
                    return (rest.get(k + 1).map(|t| vec![basename_lc(&t.text)]).unwrap_or_default(), false);
                }
                if a.starts_with('-') && a.len() >= 2 && "-command".starts_with(&a) {
                    return (scan(&join_plain(&rest[k + 1..]), depth + 1), false);
                }
                if !a.starts_with('-') {
                    return (scan(&join_plain(&rest[k..]), depth + 1), false);   // 옵션 없이 온 글 = -Command 와 같다
                }
                k += 1;
            }
            return (vec![base], false);
        }
        if base == "find" {
            if let Some(k) = rest.iter().position(|t| matches!(t.text.as_str(), "-exec" | "-execdir" | "-ok" | "-okdir")) {
                let end = rest[k + 1..].iter().position(|t| t.text == ";" || t.text == "+").map(|e| k + 1 + e).unwrap_or(rest.len());
                return (program_of(&rest[k + 1..end], depth).0, false);
            }
            return (vec![base], true);
        }
        if base == "command" && rest.iter().take_while(|t| t.text.starts_with('-')).any(|t| t.text.contains('v') || t.text.contains('V')) {
            return (vec![], true);   // command -v/-V = 조회
        }
        if NON_EXEC.contains(&base.as_str()) {
            return (vec![base], true);
        }
        if let Some((short, long, positional)) = wrapper_spec(&base) {
            i += 1;
            if base == "script" {
                // 리눅스 script -c '<문>' — 값이 실행될 명령
                if let Some(k) = w[i..].iter().position(|a| a.text == "-c" || a.text == "--command") {
                    return (w.get(i + k + 1).map(|t| scan(&t.text, depth + 1)).unwrap_or_default(), false);
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
        return (if base.is_empty() { vec![] } else { vec![base] }, false);
    }
    (vec![], false)
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
    // argv 원소 = 이미 나뉜 인자 — 공백이 든 원소는 인용된 한 낱말과 같다(프롬프트 글 속 agy 는 안전망에 안 걸림).
    let toks: Vec<Tok> = argv.iter().map(|a| Tok { text: a.clone(), quoted: a.contains(char::is_whitespace) }).collect();
    let is_agy = toks
        .split(|t| matches!(t.text.as_str(), ";" | "&&" | "||" | "|" | "&"))
        .flat_map(|seg| seg_programs(seg, 0))
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
    fn every_other_entry_is_gated_source_pin() {
        // 독립 검증 B1·B2·M3: 문 판정 없이 셸 문을 실행하던 입구 — 판정 줄을 지우면 붉다(배선 핀).
        let root = Path::new(env!("CARGO_MANIFEST_DIR"));
        let pins: [(&str, &str); 7] = [
            ("src/bin/cysd/schedule.rs", "if let Some(m) = cys::agy_door::launch_refusal(\"\", Some(command)) {"),
            ("src/bin/cysd/channels.rs", "if let Some(m) = cys::agy_door::launch_refusal(\"\", Some(bridge_cmd)) {"),
            ("src/bin/cysd/accounts.rs", "if cys::agy_door::launch_refusal(\"\", Some(&cmd)).is_some() {"),
            ("src/bin/cysd/handlers.rs", "&& cys::agy_door::launch_refusal(key.as_deref().unwrap_or(\"\"), cmd).is_some()"),
            ("src/bin/cys.rs", "if let Some(m) = command.as_deref().and_then(|c| cys::agy_door::launch_refusal(\"\", Some(c))) {"),
            ("src/bin/cys.rs", "if let Some(m) = cmd.as_deref().and_then(|c| cys::agy_door::launch_refusal(\"\", Some(c))) {"),
            ("cysjavis-pack/bin/javis_orchestra.py", "_refuse = agy_door_refusal(args.from_cmd)"),
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
            assert!(is_agy_adapter("claude", Some(agy)), "{agy}");
        }
        assert!(launch_refusal_with("gemini", Some(">/dev/null ~/.local/bin/agy --dangerously-skip-permissions"), false).is_some());
        for ok in ["claude 2>&1", "claude >/tmp/agy.log", "cat x | sh", "echo agy | grep a", "claude --dangerously-skip-permissions 2>/dev/null"] {
            assert!(!is_agy_adapter("claude", Some(ok)), "{ok}");
        }
    }

    #[test]
    fn codex_3r_executors_and_false_positives() {
        for agy in ["cmd.exe /c agy", "cmd /C \"agy -p x\"", "powershell.exe -Command agy", "pwsh -c agy",
                    "powershell -File C:\\x\\agy.ps1", "powershell agy", "find . -maxdepth 0 -exec agy ';'",
                    "bash -O extglob -c agy", "bash -o pipefail -c 'agy'", "bash <<< agy", "bash <<<'agy -p'",
                    "cd /tmp && \\\nagy", "ag\\y", "/x/ag\\y -p", "unknownwrapper --flag agy", "claude -p \"$(agy)\""] {
            assert!(is_agy_adapter("claude", Some(agy)), "{agy}");
        }
        for ok in ["claude -p \"$(cat docs/agy.md)\"", "command -v agy", "which agy", "claude -p \"agy 를 설명해\"",
                   "ls ~/.local/bin/agy", "claude --settings '/x/agy-notes/worker.json'", "echo '$(agy)'"] {
            assert!(!is_agy_adapter("claude", Some(ok)), "{ok}");
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
            assert!(is_agy_adapter("", Some(agy)), "{agy}");
        }
        assert!(!is_agy_adapter("", Some("env -S 'claude --x'")));
        let argv = |v: &[&str]| v.iter().map(|s| s.to_string()).collect::<Vec<_>>();
        for a in [argv(&["agy"]), argv(&["env", "-S", "agy -p 'it''s'"]), argv(&["/x/agy", "it's"]),
                  argv(&["nohup", "env", "A=1", "agy"]), argv(&["sh", "-c", "agy"])] {
            assert!(launch_refusal_argv_with(&a, false).is_some(), "{a:?}");
            assert!(launch_refusal_argv_with(&a, true).is_none(), "문 열림이면 거부 없음 {a:?}");
        }
        assert!(launch_refusal_argv_with(&argv(&["claude", "-p", "agy 를 설명해"]), false).is_none(), "인용된(공백 든) 프롬프트 글 속 agy 는 프로그램이 아니다");
        assert!(launch_refusal_argv_with(&argv(&["claude", "agy"]), false).is_some(), "맨 낱말 agy = 안전망(codex 3R · 열거 못 한 실행 래퍼 대비)");
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
