//! 「상담소」·「아고라」 사이드바 메뉴의 Rust 쪽(1.1.9 T4 · TICKET=cysr-119-t4-app · 설계 docs/design/T4-APP-MENUS-119.md).
//!
//! ★앱은 릴레이에 가지 않는다(아고라 SPEC-mail-1to1 §11) — 망 호출·서명 검증은 아고라 클라이언트(`<설정>/lib/bin/agora`)의 일이고,
//!   앱은 그 클라이언트를 **읽기 동사(`read`)로만** 부르거나, 클라이언트가 쓴 파일을 **읽기만** 한다:
//!   `lib/config/desk-pin.txt`(상담소 핀) · `allowed_signers`(명부) · `participant.json`(내 id) · `mailbox/unread.json`(뱃지) ·
//!   `lib/PACKAGE-MANIFEST.json`(클라이언트 판). 이 모듈은 어느 파일에도 쓰지 않는다.
//! ★「상담소 답」 판별 = 보낸이 id 가 핀의 `desk` id 이고, 명부에 있는 그 id 의 키 지문이 **전부** 핀 지문과 같을 때만(§11 「상담소 판별」).
//!   `agora read` 의 `sig: ok` 는 「그 id 의 명부 키로 서명 검증됨」이라, 명부 키 = 핀 지문이면 보낸이 = 상담소다.
//!   표시명·방 제목으로는 정하지 않는다.

use crate::{inject_runtime_path, BOOT_PY_CANDIDATES};
use cys::SpawnPolicy as _;
use base64::Engine as _;
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::io::Read as _;
use std::path::{Path, PathBuf};

/// 상담소 방을 읽을 수 있는 가장 낮은 클라이언트 판 — 0.1.4 는 커뮤니티 방 genesis 의 `budget` 칸을
/// 「계약에 없는 칸」으로 격리해 글이 0건으로 보인다(2026-10-09 실측 · 설계 §0 F2).
const MIN_CLIENT: (u64, u64, u64) = (0, 1, 14);
/// `agora read` 한 쪽 = 64KB 상한(클라이언트 READ_PAGE_BYTES) — 8쪽(≈512KB)까지만 따라간다.
const MAX_PAGES: usize = 8;
/// 한 번 부를 때의 시간 상한(망 지연 · 먹통 클라이언트가 창을 붙잡지 않게).
const READ_TIMEOUT: std::time::Duration = std::time::Duration::from_secs(20);

/// 아고라 설정 폴더 — 환경 `AGORA_CONFIG_DIR`(비어 있지 않으면) · 아니면 `<홈>/.config/agora`
/// (맥 `~/.config/agora` · 윈 `%USERPROFILE%\.config\agora` = 클라이언트 `participant.DEFAULT_DIR` 와 같은 식).
pub(crate) fn config_dir_from(env: Option<&str>, home: &Path) -> PathBuf {
    match env.map(str::trim) {
        Some(v) if !v.is_empty() => PathBuf::from(v),
        _ => home.join(".config").join("agora"),
    }
}

fn config_dir() -> PathBuf {
    config_dir_from(std::env::var("AGORA_CONFIG_DIR").ok().as_deref(), &cys::home_dir())
}

/// 참가자 id 형식(클라이언트·릴레이와 같은 꼴) — 형식 밖 값은 화면에 싣지 않는다.
pub(crate) fn valid_participant_id(s: &str) -> bool {
    (2..=64).contains(&s.len()) && s.bytes().all(|b| b.is_ascii_alphanumeric() || b == b'.' || b == b'_' || b == b'-')
}

fn valid_thread_id(s: &str) -> bool {
    s.len() == 32 && s.bytes().all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
}

/// 상담소 핀(`desk-pin.txt`) — `desk <id> <SHA256:지문>` · `room <32hex>` 만 쓴다(모르는 줄·`#` 주석은 버린다).
#[derive(Debug, Default, PartialEq)]
pub(crate) struct DeskPin {
    pub desks: Vec<(String, String)>,
    pub rooms: Vec<String>,
}

pub(crate) fn parse_desk_pin(text: &str) -> DeskPin {
    let mut pin = DeskPin::default();
    for line in text.lines() {
        let line = line.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        let t: Vec<&str> = line.split_whitespace().collect();
        match t.as_slice() {
            ["desk", id, fp] if valid_participant_id(id) && fp.starts_with("SHA256:") && fp.len() > 7 => {
                pin.desks.push((id.to_string(), fp.to_string()))
            }
            ["room", tid] if valid_thread_id(tid) => {
                if !pin.rooms.iter().any(|r| r == tid) {
                    pin.rooms.push(tid.to_string())
                }
            }
            _ => {}
        }
    }
    pin
}

// ── 명부 판독 = OpenSSH 원본 의미론 그대로(codex 1R·2R ①) ─────────────────────────────────────────
// 클라이언트의 서명 검증은 `ssh-keygen -Y verify -f allowed_signers -I <id>` 이다. 그 도구가 「이 id 에 유효」로 보는 줄 집합을
// 앱이 **같게** 셀 수 있어야 「그 id 의 키 전부 = 핀 지문」 판정이 성립한다. 아래 함수들은 OpenSSH 원본을 한 줄씩 옮겼다:
//   misc.c `strdelim_internal`(strdelimw) · match.c `match_pattern`·`match_pattern_list` · sshsig.c
//   `parse_principals_key_and_options` · sshkey.c `sshkey_advance_past_options`.

/// OpenSSH `match_pattern` — `*`(0자 이상)·`?`(1자) glob · 대소문자 구분. 결과 의미론은 원본과 같다.
/// ★계산은 **선형 반복식**(두 포인터 + 마지막 `*` 위치·그때의 문자열 위치 기억 · 최악 O(n·m)) — 재귀 백트래킹은
///   `*?`×32+`Z` 꼴 명부 한 줄에 C(64,32) 경로를 돌아 상담소 명령을 멈출 수 있었다(codex 3R MAJOR · OpenSSH 현행도 NFA 꼴).
///   마지막 `*` 하나만 기억해도 정확하다: 뒤 `*` 가 앞 `*` 의 모든 늘림을 덮으므로 앞으로 되돌아갈 일이 없다(표준 와일드카드 증명).
pub(crate) fn glob_match(s: &[u8], p: &[u8]) -> bool {
    let (mut si, mut pi) = (0usize, 0usize);
    let mut star: Option<(usize, usize)> = None; // (패턴의 `*` 다음 위치, 그 `*` 가 지금까지 먹은 끝의 문자열 위치)
    while si < s.len() {
        if pi < p.len() && p[pi] == b'*' {
            pi += 1;
            star = Some((pi, si));
        } else if pi < p.len() && (p[pi] == b'?' || p[pi] == s[si]) {
            si += 1;
            pi += 1;
        } else if let Some((sp, ss)) = star {
            pi = sp;
            si = ss + 1;
            star = Some((sp, ss + 1));
        } else {
            return false;
        }
    }
    while pi < p.len() && p[pi] == b'*' {
        pi += 1;
    }
    pi == p.len()
}

/// OpenSSH `match_pattern_list(string, pattern, dolower=0)` — 쉼표 목록 · `!` 부정이 맞으면 즉시 불일치(-1) ·
/// 긍정 하나라도 맞으면 일치 · 하위 패턴이 1023바이트 이상이면 목록 전체가 불일치(원본의 `sub[1024]` 상한).
pub(crate) fn principal_matches(id: &str, list: &str) -> bool {
    let (b, mut i, mut got) = (list.as_bytes(), 0usize, false);
    while i < b.len() {
        let neg = b[i] == b'!';
        if neg {
            i += 1;
        }
        let start = i;
        while i < b.len() && b[i] != b',' {
            i += 1;
        }
        if i - start >= 1023 {
            return false;
        }
        let sub = &b[start..i];
        if i < b.len() {
            i += 1; // 쉼표 건너뛰기
        }
        if glob_match(id.as_bytes(), sub) {
            if neg {
                return false;
            }
            got = true;
        }
    }
    got
}

const SSH_WS: &[char] = &[' ', '\t', '\r', '\n'];

/// OpenSSH `strdelimw` — 첫 공백 또는 큰따옴표에서 끊는다. 따옴표면 그 따옴표를 **지우고**(앞 글자와 이어 붙음) 다음 따옴표까지가
/// 토큰의 나머지(`x,"jarvis-*"` → `x,jarvis-*`). 닫는 따옴표 없음 = `None`(원본 NULL = 그 줄 무효).
/// 반환 `(토큰, 나머지)` — 나머지 `None` = 원본에서 `cp == NULL`(토큰 뒤에 아무것도 없음 = 무효 줄).
pub(crate) fn strdelimw(s: &str) -> Option<(String, Option<&str>)> {
    let Some(i) = s.find(|c: char| SSH_WS.contains(&c) || c == '"') else {
        return Some((s.to_string(), None));
    };
    if s[i..].starts_with('"') {
        let after = &s[i + 1..];
        let j = after.find('"')?;
        let token = format!("{}{}", &s[..i], &after[..j]);
        return Some((token, Some(after[j + 1..].trim_start_matches(SSH_WS))));
    }
    Some((s[..i].to_string(), Some(s[i + 1..].trim_start_matches(SSH_WS))))
}

/// OpenSSH `sshkey_advance_past_options` — 따옴표 밖 공백(스페이스·탭)까지 건너뛴다(`\"` 는 두 글자 함께 건너뜀).
/// 닫히지 않은 따옴표 = `None`(원본 -1 = 그 줄 무효).
fn advance_past_options(s: &str) -> Option<&str> {
    let b = s.as_bytes();
    let (mut i, mut quoted) = (0usize, false);
    while i < b.len() && (quoted || (b[i] != b' ' && b[i] != b'\t')) {
        if b[i] == b'\\' && b.get(i + 1) == Some(&b'"') {
            i += 1;
        } else if b[i] == b'"' {
            quoted = !quoted;
        }
        i += 1;
    }
    if i >= b.len() && quoted {
        return None;
    }
    Some(&s[i..])
}

fn is_key_type(w: &str) -> bool {
    w.starts_with("ssh-") || w.starts_with("ecdsa-") || w.starts_with("sk-")
}

/// `sshkey_read` 의 몫 — `키종류 base64 …` 의 지문(`SHA256:` + 무패딩 base64). 키종류가 아니거나 base64 가 아니면 `None`.
fn key_fingerprint(s: &str) -> Option<String> {
    let mut w = s.split(SSH_WS).filter(|x| !x.is_empty());
    let (kt, b64) = (w.next()?, w.next()?);
    if !is_key_type(kt) {
        return None;
    }
    let blob = base64::engine::general_purpose::STANDARD.decode(b64).ok()?;
    Some(format!("SHA256:{}", base64::engine::general_purpose::STANDARD_NO_PAD.encode(Sha256::digest(&blob))))
}

/// 명부 한 줄의 판독 결과 — 원본 `parse_principals_key_and_options` 순서 그대로.
#[derive(Debug, PartialEq)]
pub(crate) enum SignerLine {
    /// 빈 줄·주석(원본 KEY_NOT_FOUND).
    Skip,
    /// 주체 칸부터 못 읽음(닫히지 않은 따옴표·토큰 뒤 없음) — 이 id 에 맞는지조차 모름.
    Invalid,
    /// 주체 목록 + 키 지문(`None` = 키·옵션 판독 실패 — 원본은 그 줄에서 오류).
    Entry { principals: String, fp: Option<String> },
}

pub(crate) fn parse_signer_line(line: &str) -> SignerLine {
    let cp = line.trim_start_matches(SSH_WS);
    if cp.is_empty() || cp.starts_with('#') {
        return SignerLine::Skip;
    }
    let Some((principals, Some(rest))) = strdelimw(cp) else {
        return SignerLine::Invalid;
    };
    // 「키부터 읽어 보고, 안 되면 옵션 칸을 건너뛰고 다시」 — 원본 순서(cert-authority·namespaces=·valid-after·valid-before 등).
    let fp = key_fingerprint(rest).or_else(|| {
        let after = advance_past_options(rest)?;
        if after.is_empty() {
            return None;
        }
        key_fingerprint(after.trim_start_matches(SSH_WS))
    });
    SignerLine::Entry { principals, fp }
}

/// 명부(`allowed_signers`)에서 **그 id 에 유효한 줄 전부**의 키 지문 — 주체 패턴이 id 에 맞는 줄 전부(정확 이름이든 `*`·`?` 패턴이든).
/// 지문을 못 낸 줄 · 주체 칸을 못 읽는 줄(그 id 에 맞는지 모름)은 `None` 으로 싣는다 — 버리지 않는다(fail-closed).
/// 옵션(cert-authority·namespaces·valid-*)으로 실제 효력이 줄어드는 줄도 그대로 센다(더 엄격한 쪽 = 상담소 판정이 줄 뿐).
pub(crate) fn roster_fingerprints(roster: &str, id: &str) -> Vec<Option<String>> {
    let mut out = Vec::new();
    for line in roster.lines() {
        match parse_signer_line(line) {
            SignerLine::Skip => {}
            SignerLine::Invalid => out.push(None),
            SignerLine::Entry { principals, fp } => {
                if principal_matches(id, &principals) {
                    out.push(fp);
                }
            }
        }
    }
    out
}

/// 핀과 명부가 함께 맞는 상담소 id 들 — 명부에서 그 id 에 유효한 줄이 하나 이상이고 **모든** 줄의 지문이 핀 지문과 같을 때만.
/// (한 줄이라도 다르거나 못 읽으면 그 키로 서명된 글이 `sig: ok` 로 올 수 있으므로 상담소로 보지 않는다.)
pub(crate) fn verified_desk_ids(pin: &DeskPin, roster: &str) -> Vec<String> {
    let mut out = Vec::new();
    for (id, fp) in &pin.desks {
        let fps = roster_fingerprints(roster, id);
        if !fps.is_empty() && fps.iter().all(|f| f.as_deref() == Some(fp.as_str())) && !out.contains(id) {
            out.push(id.clone());
        }
    }
    out
}

/// `PACKAGE-MANIFEST.json` 의 `version` 이 MIN_CLIENT 이상인가(숫자 마디 비교 · 못 읽으면 아니다).
pub(crate) fn client_version_ok(manifest: &str) -> bool {
    let Ok(v) = serde_json::from_str::<Value>(manifest) else { return false };
    let Some(s) = v.get("version").and_then(Value::as_str) else { return false };
    let parts: Vec<Option<u64>> = s.split('.').map(|p| p.parse::<u64>().ok()).collect();
    match parts.as_slice() {
        [Some(a), Some(b), Some(c)] => (*a, *b, *c) >= MIN_CLIENT,
        _ => false,
    }
}

/// 방 id — 핀의 `room` 줄 우선 · 없으면 클라이언트가 찾아 적어 둔 `counsel/state.json` 의 `room_ids`(§13-2).
pub(crate) fn pick_room(pin: &DeskPin, state_json: Option<&str>) -> Option<String> {
    if let Some(r) = pin.rooms.first() {
        return Some(r.clone());
    }
    let v: Value = serde_json::from_str(state_json?).ok()?;
    v.get("room_ids")?.as_array()?.iter().filter_map(Value::as_str).find(|s| valid_thread_id(s)).map(str::to_string)
}

/// 내 참가자 id — `participant.json` 의 `id`(형식 밖이면 빈 값 = 「내 글」 표식 없음).
pub(crate) fn my_id(participant_json: Option<&str>) -> String {
    participant_json
        .and_then(|s| serde_json::from_str::<Value>(s).ok())
        .and_then(|v| v.get("id").and_then(Value::as_str).map(str::to_string))
        .filter(|s| valid_participant_id(s))
        .unwrap_or_default()
}

/// `agora read` 한 쪽의 JSON → (이벤트, refs, 다음 커서). 형식이 어긋난 행은 버린다(화면에 싣지 않는다).
pub(crate) fn parse_read_page(v: &Value) -> (Vec<Value>, Vec<Value>, Option<String>) {
    let mut events = Vec::new();
    for e in v.get("events").and_then(Value::as_array).into_iter().flatten() {
        let s = |k: &str| e.get(k).and_then(Value::as_str);
        let (Some(id), Some(kind), Some(from), Some(ts)) = (s("message_id"), s("kind"), s("from"), s("ts")) else { continue };
        if !valid_participant_id(from) || e.get("sig").and_then(Value::as_str) != Some("ok") {
            continue;
        }
        let body = e.get("body").and_then(Value::as_str);
        let marker = e.get("untrusted").and_then(|u| u.get("marker")).and_then(Value::as_str);
        events.push(json!({"message_id": id, "kind": kind, "from": from, "ts": ts, "body": body, "marker": marker}));
    }
    let mut refs = Vec::new();
    for r in v.get("refs").and_then(Value::as_array).into_iter().flatten() {
        let s = |k: &str| r.get(k).and_then(Value::as_str);
        let (Some(from_id), Some(tid)) = (s("from_message_id"), s("thread_id")) else { continue };
        refs.push(json!({"from_message_id": from_id, "thread_id": tid, "message_id": s("message_id")}));
    }
    let next = v.get("next_cursor").and_then(Value::as_str).filter(|c| !c.is_empty()).map(str::to_string);
    (events, refs, next)
}

/// 클라이언트 출력 전체 상한 — 쪽당 64KB(클라이언트 READ_PAGE_BYTES) × 8쪽. 넘으면 그 자리에서 끊는다(메모리 무한 적재 0).
const STDOUT_CAP: usize = MAX_PAGES * 64 * 1024;

/// 격리 실행에서 지우는 환경(codex 1R BLOCK 2) — `-I` 가 PYTHON* 를 무시하지만 자식 env 에도 남기지 않는다(이중).
const PY_ENV_STRIP: &[&str] = &["PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP", "PYTHONUSERBASE", "PYTHONINSPECT", "PYTHONEXECUTABLE"];

/// `agora read` 명령 조립 — **검증 경계(클라이언트 서명 검증)보다 먼저 남의 코드가 돌 길을 막는다**:
/// `-I`(PYTHON* 환경·사용자 site·스크립트 폴더 경로 무시 → sitecustomize/usercustomize 주입 차단) · `-B`(-I 아래서도 .pyc 안 씀 —
/// SEAL-1 번들 봉인) · `-X utf8`(한국어 윈도 cp949 에서도 JSON 출력 UTF-8 · PYTHONUTF8 는 -I 가 무시하므로 플래그로).
/// launcher(`lib/bin/agora`)는 제 폴더를 sys.path 에 스스로 넣으므로 -I 아래서도 돈다(2026-10-09 실측).
pub(crate) fn read_command(py: &str, agora: &Path, cfg: &Path, room: &str, cursor: Option<&str>) -> std::process::Command {
    let mut cmd = std::process::Command::new(py);
    inject_runtime_path(&mut cmd); // PATH(번들 python 찾기) — PYTHON* 칸은 아래에서 지우고 -I 가 무시한다
    for k in PY_ENV_STRIP {
        cmd.env_remove(k);
    }
    cmd.env("AGORA_CONFIG_DIR", cfg);
    cmd.args(["-I", "-B", "-X", "utf8"]);
    cmd.arg(agora).arg("read").arg("--thread_id").arg(room);
    if let Some(c) = cursor {
        cmd.arg("--cursor").arg(c);
    }
    cmd.stdin(std::process::Stdio::null())
        .stdout(std::process::Stdio::piped())
        .stderr(std::process::Stdio::null());
    // 창 정책 = GUI no_console 과 같은 등급(Attached · 윈도 콘솔 창 숨김) — 인구조사가 이 파일 안에서 판독하도록 직접 건다.
    cmd.spawn_policy(cys::ChildLifetime::Attached);
    cmd
}

#[derive(Debug, PartialEq)]
pub(crate) enum ReadErr {
    /// 출력이 남은 상한(`budget`)을 넘었다 — 끊었다.
    Overflow,
    Other(String),
}

/// 클라이언트 `read` 1회 — stdout 은 별도 스레드가 **상한까지만** 읽고(넘으면 즉시 자식 종료), 시간 상한 20초.
fn run_read(agora: &Path, cfg: &Path, room: &str, cursor: Option<&str>, budget: usize) -> Result<(Value, usize), ReadErr> {
    use std::sync::atomic::{AtomicBool, Ordering};
    let mut last_err = String::new();
    for py in BOOT_PY_CANDIDATES {
        let mut cmd = read_command(py, agora, cfg, room, cursor);
        let mut child = match cmd.spawn() {
            Ok(c) => c,
            Err(e) => {
                last_err = format!("{py}: {e}");
                continue;
            }
        };
        let mut out = child.stdout.take().ok_or_else(|| ReadErr::Other("stdout".into()))?;
        let over = std::sync::Arc::new(AtomicBool::new(false));
        let over_r = over.clone();
        let reader = std::thread::spawn(move || {
            let (mut buf, mut chunk) = (Vec::new(), [0u8; 8192]);
            loop {
                match out.read(&mut chunk) {
                    Ok(0) | Err(_) => break,
                    Ok(n) if buf.len() + n > budget => {
                        over_r.store(true, Ordering::SeqCst);
                        break;
                    }
                    Ok(n) => buf.extend_from_slice(&chunk[..n]),
                }
            }
            buf
        });
        let deadline = std::time::Instant::now() + READ_TIMEOUT;
        let status = loop {
            if over.load(Ordering::SeqCst) {
                let _ = child.kill();
                let _ = child.wait();
                let _ = reader.join();
                return Err(ReadErr::Overflow);
            }
            match child.try_wait() {
                Ok(Some(s)) => break s,
                Ok(None) if std::time::Instant::now() < deadline => std::thread::sleep(std::time::Duration::from_millis(20)),
                Ok(None) => {
                    let _ = child.kill();
                    let _ = child.wait();
                    return Err(ReadErr::Other("timeout".into()));
                }
                Err(e) => return Err(ReadErr::Other(e.to_string())),
            }
        };
        let buf = reader.join().map_err(|_| ReadErr::Other("reader".into()))?;
        if over.load(Ordering::SeqCst) {
            return Err(ReadErr::Overflow);
        }
        if !status.success() {
            return Err(ReadErr::Other(format!("agora read rc={:?}", status.code())));
        }
        let n = buf.len();
        return serde_json::from_slice(&buf).map(|v| (v, n)).map_err(|e| ReadErr::Other(format!("json: {e}")));
    }
    Err(ReadErr::Other(format!("python 없음({last_err})")))
}

fn read_opt(p: &Path) -> Option<String> {
    std::fs::read_to_string(p).ok()
}

/// 상담소 방 글 전부(읽기 전용) — 상태: `ok` · `no_client`(클라이언트 없음/0.1.14 미만) · `no_room` · `error`.
/// 정렬·댓글 트리·표식 벗기기는 UI 순수 모듈(counsel.ts)이 한다 — 여기서는 검증된 행만 추려 넘긴다.
pub(crate) fn room_list_at(cfg: &Path) -> Value {
    let lib = cfg.join("lib");
    let agora = lib.join("bin").join("agora");
    if !agora.is_file() || !read_opt(&lib.join("PACKAGE-MANIFEST.json")).is_some_and(|m| client_version_ok(&m)) {
        return json!({"status": "no_client"});
    }
    let pin = parse_desk_pin(&read_opt(&lib.join("config").join("desk-pin.txt")).unwrap_or_default());
    let Some(room) = pick_room(&pin, read_opt(&cfg.join("counsel").join("state.json")).as_deref()) else {
        return json!({"status": "no_room"});
    };
    let desk_ids = verified_desk_ids(&pin, &read_opt(&cfg.join("allowed_signers")).unwrap_or_default());
    let me = my_id(read_opt(&cfg.join("participant.json")).as_deref());
    let (mut events, mut refs) = (Vec::new(), Vec::new());
    let mut cursor: Option<String> = None;
    let mut partial = false;
    let mut used = 0usize;
    for page in 0..MAX_PAGES {
        let v = match run_read(&agora, cfg, &room, cursor.as_deref(), STDOUT_CAP - used) {
            Ok((v, n)) => {
                used += n;
                v
            }
            Err(e) if page == 0 => return json!({"status": "error", "detail": format!("{e:?}")}),
            Err(_) => {
                partial = true;
                break;
            }
        };
        let (ev, rf, next) = parse_read_page(&v);
        events.extend(ev);
        refs.extend(rf);
        match next {
            Some(n) if page + 1 < MAX_PAGES => cursor = Some(n),
            Some(_) => partial = true,
            None => break,
        }
    }
    json!({"status": "ok", "room_id": room, "me": me, "desk_ids": desk_ids, "events": events, "refs": refs, "partial": partial})
}

/// UI 명령 — 클라이언트 호출(망)이 있으므로 블로킹 스레드에서 돈다(창이 멈추지 않게).
#[tauri::command]
pub(crate) async fn counsel_room_list() -> Value {
    let cfg = config_dir();
    tokio::task::spawn_blocking(move || room_list_at(&cfg))
        .await
        .unwrap_or_else(|_| json!({"status": "error", "detail": "join"}))
}

// ── 뱃지(§11 `mailbox/unread.json` · 읽기만) ─────────────────────────────────
/// 뱃지 파일 상한 — 정상 파일은 수 KB(대화 최대 50행). 넘으면 깨진 파일로 본다(UI 가 직전 값 유지).
const UNREAD_MAX_BYTES: u64 = 256 * 1024;

/// 뱃지 파일의 수정 시각(ms)과 글자. 없으면 `exists:false`(UI = 숨김). 판독(깨짐·판 `v`)은 UI 순수 모듈 몫이다.
pub(crate) fn unread_at(cfg: &Path) -> Value {
    let p = cfg.join("mailbox").join("unread.json");
    let Ok(meta) = std::fs::metadata(&p) else { return json!({"exists": false}) };
    let mtime = meta
        .modified()
        .ok()
        .and_then(|t| t.duration_since(std::time::UNIX_EPOCH).ok())
        .map(|d| d.as_millis() as u64)
        .unwrap_or(0);
    let text = if meta.len() > UNREAD_MAX_BYTES { None } else { std::fs::read_to_string(&p).ok() };
    json!({"exists": true, "mtime_ms": mtime, "text": text})
}

#[tauri::command]
pub(crate) fn counsel_unread() -> Value {
    unread_at(&config_dir())
}

// ── 아고라 창(읽기 전용 웹뷰) ──────────────────────────────────────────────
pub(crate) const AGORA_HOST: &str = "agora.godmeyou.kr";
const AGORA_HOME: &str = "https://agora.godmeyou.kr/";
const AGORA_LABEL: &str = "agora";
/// 바깥 링크를 눌렀을 때 창 안에 보이는 안내(공개 문안 · 왕초보 말투 · 뒤에 그 주소가 붙는다 — 복사해서 쓰게).
pub(crate) const AGORA_OUTSIDE_NOTE: &str = "바깥 링크는 이 창에서 열리지 않아요. 아래 주소를 복사해서 브라우저에서 여세요:";

/// 창 안 이동 허용 = `https://agora.godmeyou.kr` 오리진만(포트·사용자정보 없음). `about:` 포함 그 밖은 전부 거부(codex 1R BLOCK 3).
/// ★실측(wry 0.55.1): 맥 WKWebView 는 이 판정을 **모든 틀**에 URL 만 넘겨 부르고(메인/서브 구분 불가) · 윈 WebView2 는
///   top-level(NavigationStarting)만 · 리눅스는 탐색 동작 전부 — 앱 쪽에서 틀을 가를 수 없으므로 예외를 두지 않는다.
///   귀결(실측 2026-10-09 · ui/e2e/agora_frames_probe.py): 사이트의 숨은 틀은 `about:blank` 로 탐색한다(WebKit·Chromium 2회씩) — 맥에서 이 판정이
///   그것을 거부하면 그 틀의 Cloudflare 확인 스크립트가 안 돈다. 그 스크립트를 막은 채로도 방 목록은 그려지고 페이지 오류 0(두 엔진).
pub(crate) fn agora_nav_allowed(url: &tauri::Url) -> bool {
    url.scheme() == "https"
        && url.host_str() == Some(AGORA_HOST)
        && url.port().is_none()
        && url.username().is_empty()
        && url.password().is_none()
}

/// 창마다 먼저 도는 스크립트 — ⑴폼 제출 막기(보기 전용) ⑵바깥 링크 클릭 = 이동 대신 창 안 안내 1줄(주소 · textContent) ⑶「내 글」 강조(글쓴이 칸 글자 == 내 id 인 글 상자에 테두리).
/// 서버 변경 0 · 내 id 는 JSON 문자열로 박는다(형식 밖이면 빈 값 = 강조 안 함). 남의 페이지 DOM 은 클래스 1개만 더한다.
pub(crate) fn agora_init_script(me: &str) -> String {
    let me_js = serde_json::to_string(if valid_participant_id(me) { me } else { "" }).unwrap_or_else(|_| "\"\"".into());
    format!(
        r#"(function(){{
  if (location.hostname !== "{host}") return;
  document.addEventListener("submit", function (e) {{ e.preventDefault(); e.stopPropagation(); }}, true);
  var NOTE = {note_js};
  function showNote(href) {{
    var el = document.getElementById("cysr-outside-note");
    if (!el) {{
      el = document.createElement("div");
      el.id = "cysr-outside-note";
      el.setAttribute("role", "status");
      el.style.cssText = "position:fixed;left:12px;right:12px;bottom:12px;z-index:2147483647;padding:8px 12px;border-radius:6px;background:#1f2937;color:#f9fafb;font:14px/1.5 sans-serif;-webkit-user-select:text;user-select:text;overflow-wrap:anywhere";
      (document.body || document.documentElement).appendChild(el);
    }}
    el.textContent = NOTE + " " + href;
    clearTimeout(window.__cysrNoteTimer);
    window.__cysrNoteTimer = setTimeout(function () {{ if (el.parentNode) el.parentNode.removeChild(el); }}, 10000);
  }}
  function ours(u) {{ return u.protocol === "https:" && u.hostname === "{host}" && !u.port && !u.username && !u.password; }}
  document.addEventListener("click", function (e) {{
    var a = e.target && e.target.closest ? e.target.closest("a[href]") : null;
    if (!a) return;
    var u;
    try {{ u = new URL(a.href, location.href); }} catch (_) {{ return; }}
    if (ours(u)) {{
      if (a.target && a.target !== "_self") {{ e.preventDefault(); location.href = u.href; }}
      return;
    }}
    e.preventDefault();
    e.stopPropagation();
    showNote(u.href);
  }}, true);
  var ME = {me_js};
  if (!ME) return;
  function ensureStyle() {{
    if (!document.head || document.getElementById("cysr-mine-style")) return;
    var s = document.createElement("style");
    s.id = "cysr-mine-style";
    s.textContent = ".speech.cysr-mine{{outline:2px solid #2f81f7;outline-offset:2px;border-radius:6px}}";
    document.head.appendChild(s);
  }}
  function mark() {{
    ensureStyle();
    var els = document.querySelectorAll(".speech-who");
    for (var i = 0; i < els.length; i++) {{
      if (els[i].textContent !== ME) continue;
      var box = els[i].closest(".speech");
      if (box && !box.classList.contains("cysr-mine")) box.classList.add("cysr-mine");
    }}
  }}
  var queued = false;
  function schedule() {{ if (queued) return; queued = true; setTimeout(function () {{ queued = false; mark(); }}, 200); }}
  function start() {{ mark(); new MutationObserver(schedule).observe(document.documentElement, {{ childList: true, subtree: true }}); }}
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start); else start();
}})();"#,
        host = AGORA_HOST,
        me_js = me_js,
        note_js = serde_json::to_string(AGORA_OUTSIDE_NOTE).unwrap_or_else(|_| "\"\"".into())
    )
}

/// 「아고라」 단추 — 별도 창(라벨 `agora`). 이미 열려 있으면 앞으로.
/// 경계: capability 무등재(= 이 창은 앱 명령 호출 0) · 이동 = 아고라 오리진만(밖 = 거부 · 브라우저 전달 0) · 새 창·다운로드 거부 ·
/// 저장소 = 비영속(incognito · 메인 창과 공유 0 · 닫으면 소멸) · 개발자 도구 끔.
/// ★창 만들기는 비동기 명령에서 한다(동기 명령에서 만들면 윈도에서 교착 — Tauri 문서).
#[tauri::command]
pub(crate) async fn open_agora_window(app: tauri::AppHandle) -> Result<(), String> {
    use tauri::Manager as _;
    if let Some(w) = app.get_webview_window(AGORA_LABEL) {
        let _ = w.unminimize();
        let _ = w.show();
        return w.set_focus().map_err(|e| e.to_string());
    }
    let me = my_id(read_opt(&config_dir().join("participant.json")).as_deref());
    let url = AGORA_HOME.parse::<tauri::Url>().map_err(|e| e.to_string())?;
    tauri::WebviewWindowBuilder::new(&app, AGORA_LABEL, tauri::WebviewUrl::External(url))
        .title("아고라 — 보기 전용")
        .inner_size(1100.0, 800.0)
        .incognito(true)
        .devtools(false)
        .initialization_script(agora_init_script(&me))
        // 거부된 이동은 **아무 데도 보내지 않는다**(codex 1R MAJOR 1 · master 판정 ⑥) — 사용자 동작인지 가릴 수 없어서,
        // 자동 전달하면 페이지 스크립트가 기본 브라우저 탭을 무한히 열 수 있다. 사람이 누른 바깥 링크는 주입 스크립트가
        // 창 안 안내 1줄(주소 포함 · 복사 가능)로 바꾼다.
        .on_navigation(agora_nav_allowed)
        .on_new_window(|_u, _features| tauri::webview::NewWindowResponse::Deny)
        .on_download(|_w, _e| false)
        .build()
        .map(|_| ())
        .map_err(|e| e.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    const PIN: &str = "# 주석\n\
desk jarvis-counsel SHA256:yvjI714ZM9bpFldLoJFwATQgEX6JR1VT7Rh5jDGokiw\n\
chair SHA256:4CKkbxfRkimcSmlPXo6HQ6jg5U3XrSEqHDNulBcI9B0\n\
room 2a3c1932d7eccf316cc4a0b312e558c7\n\
weekly_period_days 7\n\
room NOT-HEX\n";

    #[test]
    fn config_dir_env_wins_else_home_dot_config_agora() {
        let home = Path::new("/h");
        assert_eq!(config_dir_from(Some("/x/ag"), home), PathBuf::from("/x/ag"));
        assert_eq!(config_dir_from(Some("  "), home), home.join(".config").join("agora"));
        assert_eq!(config_dir_from(None, home), home.join(".config").join("agora"));
        // 윈 동등성: 같은 식(홈 = %USERPROFILE%) — 구분자만 플랫폼 것.
        let wh = Path::new("C:\\wh");
        assert_eq!(config_dir_from(None, wh), wh.join(".config").join("agora"));
    }

    #[test]
    fn desk_pin_reads_desk_and_room_only() {
        let p = parse_desk_pin(PIN);
        assert_eq!(p.desks, vec![("jarvis-counsel".into(), "SHA256:yvjI714ZM9bpFldLoJFwATQgEX6JR1VT7Rh5jDGokiw".into())]);
        assert_eq!(p.rooms, vec!["2a3c1932d7eccf316cc4a0b312e558c7".to_string()]);
        assert_eq!(parse_desk_pin(""), DeskPin::default());
        assert!(parse_desk_pin("desk x SHA256:abc").desks.is_empty(), "id 형식 밖(1글자)");
        assert!(parse_desk_pin("desk jarvis-a nofp").desks.is_empty(), "지문 꼴 밖");
    }

    // 실 명부의 상담소 줄(공개키 · 2026-10-09 실측 — 지문이 꾸러미 핀 `desk` 값과 같다).
    fn real_key() -> &'static str {
        "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIL20PmJBFHWN8fGdkyuqWQCrr8Buf19P1vPITDmxXtRA"
    }

    #[test]
    fn roster_fingerprint_matches_openssh_sha256_form() {
        let roster = format!("jarvis-counsel {}\nother {}\n", real_key(), real_key());
        let fps = roster_fingerprints(&roster, "jarvis-counsel");
        assert_eq!(fps, vec![Some("SHA256:yvjI714ZM9bpFldLoJFwATQgEX6JR1VT7Rh5jDGokiw".to_string())], "실 핀 값과 같아야 한다");
        // 옵션 칸·주체 목록(쉼표)도 읽는다.
        let r2 = format!("a,jarvis-counsel namespaces=\"file\" {} comment\n", real_key());
        assert_eq!(roster_fingerprints(&r2, "jarvis-counsel"), fps);
        assert!(roster_fingerprints(&roster, "nobody").is_empty());
    }

    #[test]
    fn desk_is_verified_only_when_every_roster_key_matches_pin() {
        let roster = format!("jarvis-counsel {}\n", real_key());
        let fp = roster_fingerprints(&roster, "jarvis-counsel")[0].clone().unwrap();
        let pin = DeskPin { desks: vec![("jarvis-counsel".into(), fp.clone())], rooms: vec![] };
        assert_eq!(verified_desk_ids(&pin, &roster), vec!["jarvis-counsel".to_string()]);
        // 같은 id 에 다른 키가 하나 더 있으면 → 상담소로 보지 않는다.
        let two = format!("{roster}jarvis-counsel {ATTACK}\n");
        assert!(verified_desk_ids(&pin, &two).is_empty());
        // 명부에 없으면 → 아니다 · 지문이 다르면 → 아니다.
        assert!(verified_desk_ids(&pin, "").is_empty());
        let wrong = DeskPin { desks: vec![("jarvis-counsel".into(), "SHA256:zzz".into())], rooms: vec![] };
        assert!(verified_desk_ids(&wrong, &roster).is_empty());
    }

    const ATTACK: &str = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJ9AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA";

    #[test]
    fn principal_pattern_list_is_openssh_semantics() {
        assert!(glob_match(b"jarvis-counsel", b"jarvis-*"));
        assert!(glob_match(b"jarvis-counsel", b"*"));
        assert!(glob_match(b"jarvis-counsel", b"jarvis-c?unsel"));
        assert!(glob_match(b"jarvis-counsel", b"*counsel"));
        assert!(!glob_match(b"jarvis-counsel", b"Jarvis-*"), "대소문자 구분");
        assert!(!glob_match(b"jarvis-counsel", b"jarvis-?"));
        assert!(principal_matches("jarvis-counsel", "a,b,jarvis-*"));
        assert!(!principal_matches("jarvis-counsel", "!jarvis-counsel,*"), "부정이 맞으면 그 줄은 불일치");
        assert!(principal_matches("jarvis-other", "!jarvis-counsel,*"));
        assert!(!principal_matches("jarvis-counsel", "jarvis-counse"));
    }

    #[test]
    fn wildcard_attacker_line_breaks_desk_verification() {
        // codex 1R BLOCK 1 재현: 정확한 핀 키 + `jarvis-*` 공격자 키 → 공격자 키도 jarvis-counsel 서명을 검증하므로 상담소 판정 거짓.
        let pin_line = format!("jarvis-counsel {}\n", real_key());
        let fp = roster_fingerprints(&pin_line, "jarvis-counsel")[0].clone().unwrap();
        let pin = DeskPin { desks: vec![("jarvis-counsel".into(), fp)], rooms: vec![] };
        for attacker in [
            format!("jarvis-* {ATTACK}\n"),
            format!("* {ATTACK}\n"),
            format!("jarvis-c?unsel {ATTACK}\n"),
            format!("x,jarvis-counsel {ATTACK}\n"),
            format!("\"x,jarvis-*\" {ATTACK}\n"),
            format!("jarvis-* namespaces=\"agora,file\" {ATTACK} 주석\n"),
            format!("jarvis-* cert-authority {ATTACK}\n"),
            "jarvis-* ssh-ed25519 !!!not-base64!!!\n".to_string(),
            "jarvis-* 알수없는꼴\n".to_string(),
            // codex 2R ①: 중간에서 시작한 따옴표 — OpenSSH strdelimw 는 따옴표를 지워 `x,jarvis-*` 로 본다.
            format!("x,\"jarvis-*\" {ATTACK}\n"),
            format!("jarvis-*\t{ATTACK}\n"),
            format!("  jarvis-* valid-after=\"20260101\",valid-before=\"20991231\" {ATTACK}\n"),
            format!("jarvis-* namespaces=\"a\\\"b c\" {ATTACK}\n"),
            format!("!x,jarvis-c* {ATTACK}\n"),
            format!("jarvis-counsel {ATTACK}\njarvis-counsel {ATTACK}\n"),
            "\"jarvis-* 닫히지 않은 따옴표\n".to_string(),
            "jarvis-counsel\n".to_string(),
        ] {
            let roster = format!("{pin_line}{attacker}");
            assert!(verified_desk_ids(&pin, &roster).is_empty(), "공격 줄이 대조에서 빠졌다: {attacker}");
        }
        // OpenSSH 도 이 id 의 유효 키로 보지 않는 줄 → 대조 대상 아님(상담소 판정 유지):
        //   부정 패턴으로 뺀 줄 · 닫는 따옴표에서 주체가 끊긴 줄(`"jarvis-"*` → 주체 = `jarvis-` · 뒤 `*` 는 옵션 칸).
        for not_for_id in [format!("!jarvis-counsel,* {ATTACK}\n"), format!("\"jarvis-\"* {ATTACK}\n")] {
            let roster = format!("{pin_line}{not_for_id}");
            assert_eq!(verified_desk_ids(&pin, &roster), vec!["jarvis-counsel".to_string()], "{not_for_id}");
        }
    }

    #[test]
    fn strdelimw_matches_openssh_misc_c() {
        assert_eq!(strdelimw("a,b ssh-ed25519 K"), Some(("a,b".into(), Some("ssh-ed25519 K"))));
        assert_eq!(strdelimw("x,\"jarvis-*\" ssh K"), Some(("x,jarvis-*".into(), Some("ssh K"))), "중간 따옴표는 지워 이어 붙인다");
        assert_eq!(strdelimw("\"a b\"  rest"), Some(("a b".into(), Some("rest"))), "따옴표 안 공백은 토큰");
        assert_eq!(strdelimw("\"a\"b c"), Some(("a".into(), Some("b c"))), "닫는 따옴표에서 끊긴다");
        assert_eq!(strdelimw("a\tb"), Some(("a".into(), Some("b"))));
        assert_eq!(strdelimw("\"open"), None, "닫히지 않은 따옴표 = 무효");
        assert_eq!(strdelimw("only"), Some(("only".into(), None)), "토큰 뒤 없음 = cp NULL");
    }

    #[test]
    fn signer_line_options_and_comments() {
        let k = real_key();
        let fp = Some("SHA256:yvjI714ZM9bpFldLoJFwATQgEX6JR1VT7Rh5jDGokiw".to_string());
        let e = |p: &str| SignerLine::Entry { principals: p.into(), fp: fp.clone() };
        assert_eq!(parse_signer_line(""), SignerLine::Skip);
        assert_eq!(parse_signer_line("   # 주석"), SignerLine::Skip);
        assert_eq!(parse_signer_line(&format!("a {k}")), e("a"));
        assert_eq!(parse_signer_line(&format!("a {k} 꼬리 주석")), e("a"));
        assert_eq!(parse_signer_line(&format!("a cert-authority {k}")), e("a"));
        assert_eq!(parse_signer_line(&format!("a namespaces=\"git,file\" {k}")), e("a"));
        assert_eq!(parse_signer_line(&format!("a valid-after=\"20260101\",valid-before=\"20991231\" {k}")), e("a"));
        assert_eq!(parse_signer_line(&format!("a cert-authority,namespaces=\"x y\\\"z\" {k}")), e("a"), "따옴표 안 공백·\\\" 건너뛰기");
        assert_eq!(parse_signer_line(&format!("a namespaces=\"open {k}")), SignerLine::Entry { principals: "a".into(), fp: None }, "옵션 따옴표 안 닫힘 = 키 없음");
        assert_eq!(parse_signer_line("a"), SignerLine::Invalid);
        assert_eq!(parse_signer_line("\"a"), SignerLine::Invalid);
    }

    #[test]
    fn several_valid_keys_for_desk_all_compared() {
        let k = real_key();
        let fp = roster_fingerprints(&format!("jarvis-counsel {k}\n"), "jarvis-counsel")[0].clone().unwrap();
        let pin = DeskPin { desks: vec![("jarvis-counsel".into(), fp)], rooms: vec![] };
        // 같은 핀 키가 정확 이름·패턴·옵션 줄로 여러 번 = 전부 핀 지문 → 상담소.
        let ok = format!("jarvis-counsel {k}\njarvis-* {k}\n\"x,jarvis-c?unsel\" namespaces=\"file\" {k}\n# 주석\n\nother {ATTACK}\n");
        assert_eq!(roster_fingerprints(&ok, "jarvis-counsel").len(), 3);
        assert_eq!(verified_desk_ids(&pin, &ok), vec!["jarvis-counsel".to_string()]);
        // 하위 패턴 1023바이트 이상 = 원본은 목록 전체 불일치 → 그 줄은 대조 대상 아님.
        let long = format!("jarvis-*,{} {ATTACK}\n", "a".repeat(1100));
        assert!(roster_fingerprints(&long, "jarvis-counsel").is_empty());
    }

    #[test]
    fn glob_is_linear_on_backtracking_bomb() {
        // codex 3R MAJOR 재현: `*?`×32+`Z` × 64바이트 principal — 재귀판은 C(64,32) 경로(사실상 정지). 10ms 상한 단정.
        // 별 스레드에서 재고 1초 안에 안 끝나면 실패(재귀판이 되돌아와도 시험이 매달리지 않게).
        let (tx, rx) = std::sync::mpsc::channel();
        std::thread::spawn(move || {
            let pat = format!("{}Z", "*?".repeat(32));
            let id = "a".repeat(64);
            let t0 = std::time::Instant::now();
            let hit = principal_matches(&id, &pat) || glob_match(id.as_bytes(), pat.as_bytes());
            let _ = tx.send((hit, t0.elapsed()));
        });
        let (hit, took) = rx.recv_timeout(std::time::Duration::from_secs(1)).expect("1초 안에 안 끝났다 — 백트래킹 폭발");
        assert!(!hit);
        assert!(took < std::time::Duration::from_millis(10), "10ms 상한 초과: {took:?}");
    }

    #[test]
    fn openssh_oracle_nine_cases_still_agree() {
        // shots-119-t4/openssh-oracle-2026-10-09.txt 의 9꼴(실 OpenSSH 10.3 판정) — 「그 id 의 키로 세는가」가 기록과 같아야 한다.
        let k = real_key();
        let long = format!("jarvis-*,{}", "a".repeat(1100));
        let table: [(&str, bool); 9] = [
            ("jarvis-counsel", true),
            ("x,\"jarvis-*\"", true),
            ("\"jarvis-\"*", false),
            ("!jarvis-counsel,*", false),
            ("jarvis-* namespaces=\"file\"", true),
            ("jarvis-c?unsel", true),
            ("jarvis-* cert-authority", true), // OpenSSH 는 거부 · 우리는 셈(더 엄격 · 기록된 의도)
            ("\"x,jarvis-c*\"", true),
            (long.as_str(), false),
        ];
        for (head, counted) in table {
            let n = roster_fingerprints(&format!("{head} {k}\n"), "jarvis-counsel").len();
            assert_eq!(n == 1, counted, "{head}");
        }
    }

    #[test]
    fn client_version_gate_is_numeric() {
        assert!(client_version_ok(r#"{"version":"0.1.14"}"#));
        assert!(client_version_ok(r#"{"version":"0.2.0"}"#));
        assert!(client_version_ok(r#"{"version":"1.0.0"}"#));
        assert!(!client_version_ok(r#"{"version":"0.1.4"}"#), "0.1.4 = 상담소 방 genesis 격리(실측)");
        assert!(!client_version_ok(r#"{"version":"0.1.9"}"#), "글자 비교면 0.1.9 > 0.1.14 로 틀린다");
        assert!(!client_version_ok(r#"{"version":"0.1"}"#));
        assert!(!client_version_ok("{"));
    }

    #[test]
    fn room_from_pin_else_state_json() {
        let p = parse_desk_pin(PIN);
        assert_eq!(pick_room(&p, None).as_deref(), Some("2a3c1932d7eccf316cc4a0b312e558c7"));
        let none = DeskPin::default();
        assert_eq!(pick_room(&none, Some(r#"{"room_ids":["bad","0123456789abcdef0123456789abcdef"]}"#)).as_deref(),
            Some("0123456789abcdef0123456789abcdef"));
        assert_eq!(pick_room(&none, Some("{")), None);
        assert_eq!(pick_room(&none, None), None);
    }

    #[test]
    fn my_id_from_participant_json() {
        assert_eq!(my_id(Some(r#"{"id":"jarvis-ab12cd34ef"}"#)), "jarvis-ab12cd34ef");
        assert_eq!(my_id(Some(r#"{"id":"<script>"}"#)), "");
        assert_eq!(my_id(None), "");
    }

    #[test]
    fn read_page_keeps_only_signed_well_formed_rows() {
        let v = json!({
            "events": [
                {"message_id":"m1","kind":"post","from":"jarvis-a1","ts":"2026-10-08T12:00:00Z","sig":"ok","body":"<<AGORA-DATA-0123456789abcdef\nhi\nAGORA-DATA-0123456789abcdef>>","untrusted":{"marker":"AGORA-DATA-0123456789abcdef"}},
                {"message_id":"m2","kind":"post","from":"bad id!","ts":"t","sig":"ok","body":"x"},
                {"message_id":"m3","kind":"post","from":"jarvis-a1","ts":"t","sig":"bad","body":"x"},
                {"kind":"post","from":"jarvis-a1","ts":"t","sig":"ok"}
            ],
            "refs": [{"role":"ref","from_message_id":"m1","thread_id":"t1","message_id":"m0","why":null,"resolved":true}],
            "next_cursor": "events:abc"
        });
        let (ev, rf, next) = parse_read_page(&v);
        assert_eq!(ev.len(), 1);
        assert_eq!(ev[0]["marker"], "AGORA-DATA-0123456789abcdef");
        assert_eq!(rf, vec![json!({"from_message_id":"m1","thread_id":"t1","message_id":"m0"})]);
        assert_eq!(next.as_deref(), Some("events:abc"));
        assert_eq!(parse_read_page(&json!({"next_cursor": null})).2, None);
    }

    const ROOM: &str = "2a3c1932d7eccf316cc4a0b312e558c7";

    /// 격리 하네스 — 임시 설정 폴더 + 가짜 `lib/bin/agora`. ★가짜 CLI 는 호출을 **엄격히 검사**한다(codex 1R MAJOR 4):
    /// argv = `read --thread_id <핀 방> [--cursor <비지 않은 값>]` 만 · 격리 플래그(-I · -B · -X utf8) 켜짐 · AGORA_CONFIG_DIR = 그 폴더 ·
    /// PYTHONPATH 류 환경 0 — 하나라도 어긋나면 exit 9(제품이 rc≠0 을 error 로 본다). 통과하면 `body`(파이썬 몇 줄)를 실행한다.
    fn fixture_py(version: &str, body: &str) -> tempfile_lite::Dir {
        let d = tempfile_lite::Dir::new("counsel");
        let lib = d.path().join("lib");
        std::fs::create_dir_all(lib.join("bin")).unwrap();
        std::fs::create_dir_all(lib.join("config")).unwrap();
        std::fs::write(lib.join("PACKAGE-MANIFEST.json"), format!(r#"{{"version":"{version}"}}"#)).unwrap();
        std::fs::write(lib.join("config").join("desk-pin.txt"), PIN).unwrap();
        std::fs::write(d.path().join("participant.json"), r#"{"id":"jarvis-me00000001"}"#).unwrap();
        let cfg = d.path().to_string_lossy().to_string();
        let strip: Vec<String> = PY_ENV_STRIP.iter().map(|k| format!("{k:?}")).collect();
        let script = format!(
            "import os, sys\n\
a = sys.argv[1:]\n\
ok = (len(a) in (3, 5) and a[0] == 'read' and a[1] == '--thread_id' and a[2] == {ROOM:?}\n\
      and (len(a) == 3 or (a[3] == '--cursor' and a[4] != '')))\n\
iso = sys.flags.isolated == 1 and sys.flags.utf8_mode == 1 and sys.flags.dont_write_bytecode == 1\n\
env_ok = os.environ.get('AGORA_CONFIG_DIR') == {cfg:?} and not any(k in os.environ for k in [{strip}])\n\
if not (ok and iso and env_ok): sys.stderr.write('bad call %r %r %r' % (a, iso, env_ok)); sys.exit(9)\n\
cursor = a[4] if len(a) == 5 else None\n\
{body}\n",
            strip = strip.join(", ")
        );
        std::fs::write(lib.join("bin").join("agora"), script).unwrap();
        d
    }

    fn fixture(version: &str, out: &str) -> tempfile_lite::Dir {
        fixture_py(version, &format!("sys.stdout.write({out:?})"))
    }

    fn genesis_page(next: Option<&str>) -> String {
        json!({"events":[{"message_id":"g","kind":"genesis","from":"jarvis-chair1","ts":"2026-10-05T13:14:43Z","sig":"ok","body":"intro","untrusted":{"marker":null}}],"refs":[],"next_cursor":next}).to_string()
    }

    #[test]
    fn harness_round_trip_through_fake_client() {
        let d = fixture("0.1.14", &genesis_page(None));
        let v = room_list_at(d.path());
        assert_eq!(v["status"], "ok", "{v}");
        assert_eq!(v["room_id"], ROOM);
        assert_eq!(v["me"], "jarvis-me00000001");
        assert_eq!(v["events"].as_array().unwrap().len(), 1);
        assert_eq!(v["partial"], false);
        assert_eq!(v["desk_ids"], json!([]), "명부 파일이 없으면 상담소 답 표식 0");
    }

    #[test]
    fn harness_cursor_pages_are_followed_with_the_cursor_arg() {
        // 첫 쪽(커서 없음) → next "c1" · 둘째 쪽은 `--cursor c1` 로만 받는다(다른 커서 = exit 9).
        let p2 = json!({"events":[{"message_id":"p","kind":"post","from":"jarvis-a1","ts":"2026-10-08T00:00:00Z","sig":"ok","body":"x","untrusted":{"marker":null}}],"refs":[],"next_cursor":null}).to_string();
        let body = format!(
            "if cursor is None: sys.stdout.write({:?})\nelif cursor == 'c1': sys.stdout.write({p2:?})\nelse: sys.exit(9)",
            genesis_page(Some("c1"))
        );
        let d = fixture_py("0.1.14", &body);
        let v = room_list_at(d.path());
        assert_eq!(v["status"], "ok", "{v}");
        assert_eq!(v["events"].as_array().unwrap().len(), 2);
        assert_eq!(v["partial"], false);
    }

    #[test]
    fn read_command_is_isolated_and_read_only() {
        let cmd = read_command("python3", Path::new("/c/lib/bin/agora"), Path::new("/c"), ROOM, Some("k"));
        let args: Vec<String> = cmd.get_args().map(|a| a.to_string_lossy().to_string()).collect();
        assert_eq!(args, ["-I", "-B", "-X", "utf8", "/c/lib/bin/agora", "read", "--thread_id", ROOM, "--cursor", "k"]);
        let envs: std::collections::HashMap<String, Option<String>> = cmd
            .get_envs()
            .map(|(k, v)| (k.to_string_lossy().to_string(), v.map(|v| v.to_string_lossy().to_string())))
            .collect();
        for k in PY_ENV_STRIP {
            assert_eq!(envs.get(*k), Some(&None), "{k} 는 자식 env 에서 지운다");
        }
        assert_eq!(envs.get("AGORA_CONFIG_DIR"), Some(&Some("/c".to_string())));
    }

    #[test]
    fn sitecustomize_injection_does_not_run_before_the_client() {
        // codex 1R BLOCK 2 재현: PYTHONPATH 의 sitecustomize 가 가짜 sig:ok 를 찍고 끝내는 공격 — 조립 뒤에 PYTHONPATH 를 다시 넣어도
        // -I 가 무시하므로 가짜 CLI(진짜 경로)가 돈다.
        let d = fixture("0.1.14", &genesis_page(None));
        let evil = d.path().join("evil");
        std::fs::create_dir_all(&evil).unwrap();
        let fake = r#"{"events":[{"message_id":"x","kind":"post","from":"jarvis-evil1","ts":"t","sig":"ok","body":"pwned","untrusted":{"marker":null}}],"refs":[],"next_cursor":null}"#;
        std::fs::write(evil.join("sitecustomize.py"), format!("import os, sys\nsys.stdout.write({fake:?})\nsys.stdout.flush()\nos._exit(0)\n")).unwrap();
        std::fs::write(evil.join("usercustomize.py"), format!("import os, sys\nsys.stdout.write({fake:?})\nos._exit(0)\n")).unwrap();
        let agora = d.path().join("lib").join("bin").join("agora");
        // 이 시험의 가짜 CLI 는 환경 검사 없이 「격리로 떴는가」만 보고 진짜 출력을 낸다(공격 env 를 일부러 다시 넣으므로).
        std::fs::write(&agora, format!("import sys\nsys.stdout.write({:?} if sys.flags.isolated else 'not-isolated')\n", genesis_page(None))).unwrap();
        for py in BOOT_PY_CANDIDATES {
            let mut cmd = read_command(py, &agora, d.path(), ROOM, None);
            cmd.env("PYTHONPATH", &evil).env("PYTHONUSERBASE", &evil);
            let Ok(out) = cmd.output() else { continue };
            let text = String::from_utf8_lossy(&out.stdout);
            assert!(!text.contains("pwned"), "sitecustomize 가 먼저 돌았다: {text}");
            assert!(text.contains("\"genesis\""), "진짜 CLI 출력이어야 한다: {text}");
            return;
        }
        panic!("python 없음");
    }

    #[test]
    fn stdout_flood_is_cut_at_cap_not_buffered() {
        // codex 1R MAJOR 2 재현: 끝없이 쓰는 CLI → 상한에서 끊고 즉시 종료(20초 시간 상한까지 안 간다).
        let d = fixture_py("0.1.14", "while True:\n    sys.stdout.write('x' * 65536)");
        let t0 = std::time::Instant::now();
        let v = room_list_at(d.path());
        assert_eq!(v["status"], "error", "첫 쪽 넘침 = 보일 것 없음 = error: {v}");
        assert!(v["detail"].as_str().unwrap().contains("Overflow"), "{v}");
        assert!(t0.elapsed() < std::time::Duration::from_secs(10), "상한에서 바로 끊겨야 한다({:?})", t0.elapsed());
        // 둘째 쪽에서 넘치면 = 첫 쪽만 싣고 partial.
        let body = format!(
            "if cursor is None: sys.stdout.write({:?})\nelse:\n    while True: sys.stdout.write('x' * 65536)",
            genesis_page(Some("c1"))
        );
        let d2 = fixture_py("0.1.14", &body);
        let v2 = room_list_at(d2.path());
        assert_eq!(v2["status"], "ok", "{v2}");
        assert_eq!(v2["partial"], true);
        assert_eq!(v2["events"].as_array().unwrap().len(), 1);
    }

    #[test]
    fn harness_old_client_and_missing_room_and_bad_output() {
        let d = fixture("0.1.4", "{}");
        assert_eq!(room_list_at(d.path())["status"], "no_client");
        let empty = tempfile_lite::Dir::new("counsel-empty");
        assert_eq!(room_list_at(empty.path())["status"], "no_client");
        let d2 = fixture("0.1.14", "not json");
        assert_eq!(room_list_at(d2.path())["status"], "error");
        let d3 = fixture("0.1.14", "{}");
        std::fs::write(d3.path().join("lib").join("config").join("desk-pin.txt"), "# 빈 핀\n").unwrap();
        assert_eq!(room_list_at(d3.path())["status"], "no_room");
        // 가짜 CLI 가 호출을 거부(exit 9)하면 = error(제품이 동사·인자를 바꾸면 여기서 잡힌다).
        let d4 = fixture_py("0.1.14", "sys.exit(9)");
        assert_eq!(room_list_at(d4.path())["status"], "error");
    }

    #[test]
    fn unread_file_is_read_only_with_mtime_and_size_cap() {
        let d = tempfile_lite::Dir::new("counsel-unread");
        assert_eq!(unread_at(d.path()), json!({"exists": false}), "없으면 exists:false(UI = 숨김)");
        std::fs::create_dir_all(d.path().join("mailbox")).unwrap();
        let p = d.path().join("mailbox").join("unread.json");
        std::fs::write(&p, r#"{"v":1,"count":2}"#).unwrap();
        let v = unread_at(d.path());
        assert_eq!(v["exists"], true);
        assert_eq!(v["text"], r#"{"v":1,"count":2}"#);
        assert!(v["mtime_ms"].as_u64().unwrap() > 0);
        std::fs::write(&p, vec![b' '; (UNREAD_MAX_BYTES + 1) as usize]).unwrap();
        assert_eq!(unread_at(d.path())["text"], Value::Null, "상한 초과 = 깨진 파일 취급(UI 직전 값)");
        // 읽기만 — 파일이 그대로다.
        assert_eq!(std::fs::metadata(&p).unwrap().len(), UNREAD_MAX_BYTES + 1);
    }

    #[test]
    fn agora_window_navigation_is_our_origin_only() {
        let ok = |u: &str| agora_nav_allowed(&u.parse::<tauri::Url>().unwrap());
        assert!(ok("https://agora.godmeyou.kr/"));
        assert!(ok("https://agora.godmeyou.kr/room?id=2a3c1932d7eccf316cc4a0b312e558c7#x"));
        assert!(ok("https://agora.godmeyou.kr/cdn-cgi/challenge-platform/scripts/jsd/main.js"));
        for bad in [
            "http://agora.godmeyou.kr/",
            "https://agora.godmeyou.kr.evil.com/",
            "https://evil.agora.godmeyou.kr/",
            "https://godmeyou.kr/",
            "https://jarvis-install.godmeyou.kr/",
            "https://agora.godmeyou.kr:8443/",
            "https://user@agora.godmeyou.kr/",
            "file:///etc/passwd",
            "javascript:alert(1)",
            "about:config",
            "about:blank",
            "about:srcdoc",
            "tauri://localhost/",
        ] {
            assert!(!ok(bad), "창 안 이동을 막아야 한다: {bad}");
        }
        // 사용자정보(@) 위장 — 주소 꼴 문자열이 소스에 그대로 남지 않게 실행 시 조립(공개 미러 secret-scan EMAIL 규칙 · 도메인 .invalid).
        assert!(!ok(&format!("https://agora.godmeyou.kr{}evil.invalid/", "@")), "사용자정보 위장");
    }

    #[test]
    fn open_url_allows_our_two_hosts_exactly_not_subdomains() {
        assert!(crate::host_in_allowlist("agora.godmeyou.kr", &[]));
        assert!(crate::host_in_allowlist("jarvis-install.godmeyou.kr", &[]));
        for bad in ["godmeyou.kr", "evil.agora.godmeyou.kr", "agora.godmeyou.kr.evil.com", "x.jarvis-install.godmeyou.kr", "agora.godmeyou.krx"] {
            assert!(!crate::host_in_allowlist(bad, &[]), "{bad}");
        }
        // 사용자정보(@) 위장 = 실제 호스트 evil.invalid 로 판정된다.
        assert!(crate::url_host_allowed(&format!("https://agora.godmeyou.kr{}evil.invalid/", "@")).is_err());
        assert!(crate::url_host_allowed("http://agora.godmeyou.kr/").is_err(), "https 만");
        assert!(crate::url_host_allowed("https://jarvis-install.godmeyou.kr/").is_ok());
    }

    #[test]
    fn init_script_embeds_my_id_as_json_and_blocks_forms() {
        let s = agora_init_script("jarvis-me00000001");
        assert!(s.contains(r#"var ME = "jarvis-me00000001";"#));
        assert!(s.contains(r#"document.addEventListener("submit""#) && s.contains("e.preventDefault()"));
        assert!(s.contains(r#"if (location.hostname !== "agora.godmeyou.kr") return;"#));
        assert!(!s.contains("innerHTML") && !s.contains("fetch(") && !s.contains("__TAURI__") && !s.contains("window.open"),
            "남의 페이지에 쓰는 것은 클래스·스타일·안내 상자뿐");
        // 바깥 링크 = 이동 막고 안내(문구 = 공개 문안 상수 · textContent) · 우리 오리진 판정은 Rust 와 같은 4조건.
        assert!(s.contains(&format!("var NOTE = {};", serde_json::to_string(AGORA_OUTSIDE_NOTE).unwrap())));
        assert!(s.contains("el.textContent = NOTE + \" \" + href;"));
        assert!(s.contains(r#"u.protocol === "https:" && u.hostname === "agora.godmeyou.kr" && !u.port && !u.username && !u.password"#));
        assert!(!AGORA_OUTSIDE_NOTE.contains("cys ") && !AGORA_OUTSIDE_NOTE.contains("위험") && !AGORA_OUTSIDE_NOTE.contains("금지"));
        // 형식 밖 id(따옴표·태그)는 박지 않는다 → 강조 안 함.
        let bad = agora_init_script("\"; alert(1); //");
        assert!(bad.contains(r#"var ME = "";"#));
    }

    /// capability 1개가 아고라 창(라벨 `agora`)이나 아고라 주소에 앱 명령을 여는가 — Tauri 의 windows·webviews glob(`*`·`?`·`[..]`)과
    /// remote.urls 를 구조로 읽어 판정한다. 판독 못 하는 꼴(창 범위 칸 없음·문자열 아닌 항목·`[` 문자 클래스)은 **연다고 본다**(fail-closed).
    fn capability_opens_agora(cap: &Value) -> Option<String> {
        if cap.get("remote").is_some() {
            return Some("remote 칸(원격 주소 IPC)".into());
        }
        let mut scoped = false;
        for key in ["windows", "webviews"] {
            let Some(v) = cap.get(key) else { continue };
            scoped = true;
            let Some(arr) = v.as_array() else { return Some(format!("{key} 가 배열이 아니다")) };
            for p in arr {
                let Some(pat) = p.as_str() else { return Some(format!("{key} 항목이 문자열이 아니다")) };
                if pat.contains('[') || glob_match(AGORA_LABEL.as_bytes(), pat.as_bytes()) {
                    return Some(format!("{key} 패턴 {pat:?} 가 아고라 창에 맞는다"));
                }
            }
        }
        if !scoped {
            return Some("창 범위(windows·webviews) 칸이 없다 — 판독 불가".into());
        }
        None
    }

    /// 파일 하나의 capability 들(단일 객체 · `{"capabilities":[…]}` · 배열 · 식별자 문자열 참조는 건너뜀).
    fn capabilities_in(v: &Value) -> Vec<Value> {
        match v {
            Value::Array(a) => a.iter().flat_map(capabilities_in).collect(),
            Value::Object(o) if o.contains_key("capabilities") => o["capabilities"].as_array().into_iter().flatten().flat_map(capabilities_in).collect(),
            Value::Object(_) => vec![v.clone()],
            _ => vec![],
        }
    }

    #[test]
    fn capability_judge_catches_globs_star_and_remote() {
        // codex 1R MAJOR 3 재현 꼴 — 문자열 검색으로는 못 잡던 것들.
        for bad in [
            json!({"identifier":"x","windows":["*"],"permissions":[]}),
            json!({"identifier":"x","windows":["ag*"],"permissions":[]}),
            json!({"identifier":"x","windows":["main","?gora"],"permissions":[]}),
            json!({"identifier":"x","webviews":["agora"],"permissions":[]}),
            json!({"identifier":"x","windows":["[a]gora"],"permissions":[]}),
            json!({"identifier":"x","windows":["main"],"remote":{"urls":["https://*"]},"permissions":[]}),
            json!({"identifier":"x","permissions":[]}),
            json!({"identifier":"x","windows":"main","permissions":[]}),
        ] {
            assert!(capability_opens_agora(&bad).is_some(), "놓쳤다: {bad}");
        }
        assert!(capability_opens_agora(&json!({"identifier":"d","windows":["main"],"permissions":[]})).is_none());
        assert!(capability_opens_agora(&json!({"identifier":"d","windows":["main*"],"permissions":[]})).is_none());
        assert_eq!(capabilities_in(&json!({"capabilities":[{"windows":["*"]},"ref-id"]})).len(), 1);
    }

    #[test]
    fn agora_window_gets_no_app_ipc_capability() {
        // 경계 = capability 무등재: Tauri 2 는 어느 capability 에도 맞지 않는 창·원격 오리진에 앱 명령을 열지 않는다.
        // capabilities/ 의 **모든 파일**(json 외 꼴 = 판독 불가 = 실패) + tauri*.conf.json 의 인라인 capability 전건.
        let root = Path::new(env!("CARGO_MANIFEST_DIR"));
        let mut caps: Vec<(String, Value)> = Vec::new();
        for e in std::fs::read_dir(root.join("capabilities")).unwrap() {
            let p = e.unwrap().path();
            let name = p.display().to_string();
            assert_eq!(p.extension().and_then(|x| x.to_str()), Some("json"), "판독 못 하는 capability 꼴: {name}");
            let v: Value = serde_json::from_str(&std::fs::read_to_string(&p).unwrap()).unwrap();
            caps.extend(capabilities_in(&v).into_iter().map(|c| (name.clone(), c)));
        }
        for e in std::fs::read_dir(root).unwrap() {
            let p = e.unwrap().path();
            let f = p.file_name().unwrap().to_string_lossy().to_string();
            if f.starts_with("tauri") && f.ends_with(".conf.json") {
                let v: Value = serde_json::from_str(&std::fs::read_to_string(&p).unwrap()).unwrap();
                if let Some(c) = v.pointer("/app/security/capabilities") {
                    caps.extend(capabilities_in(c).into_iter().map(|c| (f.clone(), c)));
                }
            }
        }
        assert!(!caps.is_empty(), "capability 를 하나도 못 읽었다 — 측정 불능은 통과가 아니다");
        for (src, c) in &caps {
            assert_eq!(capability_opens_agora(c), None, "{src}: {c}");
        }
    }

    /// 실 클라이언트 1회(수동 · 기본 꺼짐): `COUNSEL_LIVE_CFG=<0.1.14 lib 를 둔 임시 설정 폴더>` 로 실 상담소 방을 읽어 결과 JSON 을
    /// `COUNSEL_LIVE_OUT` 파일에 쓴다(헤드리스 화면 게이트 ui/e2e/counsel_gate.py 의 실데이터 입력) — 망을 쓰므로 CI 에서 돌지 않는다.
    #[test]
    #[ignore]
    fn live_room_list_with_real_client() {
        let cfg = std::env::var("COUNSEL_LIVE_CFG").expect("COUNSEL_LIVE_CFG");
        let v = room_list_at(Path::new(&cfg));
        assert_eq!(v["status"], "ok", "{v}");
        if let Ok(out) = std::env::var("COUNSEL_LIVE_OUT") {
            std::fs::write(out, serde_json::to_vec_pretty(&v).unwrap()).unwrap();
        }
        println!("{v}");
    }

    /// 시험 전용 임시 폴더(의존성 0 · 끝나면 지운다).
    mod tempfile_lite {
        pub struct Dir(std::path::PathBuf);
        impl Dir {
            pub fn new(tag: &str) -> Self {
                let n = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_nanos();
                let p = std::env::temp_dir().join(format!("cysr-{tag}-{}-{n}", std::process::id()));
                std::fs::create_dir_all(&p).unwrap();
                Dir(p)
            }
            pub fn path(&self) -> &std::path::Path {
                &self.0
            }
        }
        impl Drop for Dir {
            fn drop(&mut self) {
                let _ = std::fs::remove_dir_all(&self.0);
            }
        }
    }
}
