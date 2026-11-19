//! ★(1.1.16 · TICKET=cysr-1116-borrow23-1119 · 차용 ②) Program Status Protocol — OSC 7501 의 단말 쪽.
//!
//! 무엇: 프로그램(Claude Code 등)이 자기 상태를 `ESC ] 7501 ; state=…:kind=…:app=…:msg=<base64> ST` 로 직접 알린다.
//!   데몬은 ⑴ 프로그램이 시작할 때 묻는 지원 질의 `ESC ] 7501 ; ? ST` 에 같은 바이트로 답하고 ⑵ 보고를 좌석별로 저장해
//!   ⑶ 화면 판정(`activity.rs`) 대신 그 값을 `display_activity` 에 싣는다. 규격 = 공개 문서(Rex Program Status ·
//!   rev 0.2~0.4 — 응답 문자열·키 변화 없음) · 코드 차용 없이 규격 문면대로 새로 썼다.
//!
//! 왜: 화면 판정기는 격리 시험 내내 `unknown` 이었다(11-01 허더 대조 0/25). 그리고 **답을 하면 Claude 가 제목 표지(◐◑✳)를
//!   그리지 않는다**(11-19 격리 실측: 제목 OSC 6→3 · 제목이 대화 주제로 바뀌어 `ClaudeR1` 이 NoMatch) — 그래서 답하는 순간부터는
//!   이 보고가 유일한 상태 출처다. 답하지 않은 좌석(Codex·옛 Claude·끈 기계)은 종전 화면 판정 그대로다.
//!
//! 실측(11-19 · Claude Code 2.1.328 · 격리 PTY · 사용자 설정 미적재): 질의에 **답하지 않으면 보고 0건** · 답하면
//!   `blocked:kind=permission:msg="trust this folder"` → `clear` → `idle` → `working` → (`working:msg="Writing probe.txt"`) →
//!   `done` · 권한 창 = `blocked:kind=permission:msg="approve Write: …"` → Esc → `idle` · `/exit` = `clear` ×2. 종결자는 BEL.
//!
//! 안전: 보고는 전부 **믿을 수 없는 프로그램 출력**이다 — 한도 하나라도 넘거나, 본문이 해독되지 않거나, 해독된 글에 제어 문자가
//!   있으면 통째로 버린다(반만 적용하지 않는다). 데몬이 PTY 로 되쓰는 것은 질의 응답 고정 바이트뿐이다(보고 내용은 절대 되쓰지
//!   않는다). 이 값은 **표시 전용**이다 — 큐·배달·승인·순환 판정을 바꾸지 않는다(그림자 단계 · `activity.rs` 머리의 네 금지와 같다).
//!   되돌리기: `CYS_PROGRAM_STATUS=0`(질의에 답하지 않고 보고도 읽지 않는다 = 1.1.15 와 같은 동작).

use std::collections::BTreeMap;
use std::time::Instant;

/// 규격 한도(문서 Limits 절). 하나라도 넘으면 그 보고는 통째로 버린다.
pub(crate) const MAX_SEQUENCE: usize = 4096;
const MAX_KEY: usize = 16;
const MAX_APP: usize = 32;
const MAX_ID: usize = 128;
const MAX_SEGMENT: usize = 32;
const MAX_DEPTH: usize = 8;
const MAX_TITLE_ENCODED: usize = 256;
const MAX_TITLE_DECODED: usize = 192;
const MAX_MSG_ENCODED: usize = 2732;
const MAX_MSG_DECODED: usize = 2048;
/// 좌석 하나가 쥐는 기록 수(규격 = 최소 64 · 최대 256). 넘으면 가장 오래 갱신되지 않은 기록을 버린다.
pub(crate) const MAX_RECORDS: usize = 64;
/// 진단에 남기는 마지막 보고 원문 길이 상한(바이트).
const RAW_KEEP: usize = 256;

/// 질의 응답 머리 — 뒤에 질의가 쓴 종결자(BEL 또는 ESC \)를 그대로 붙인다.
pub(crate) const QUERY_REPLY_HEAD: &[u8] = b"\x1b]7501;?";

/// `CYS_PROGRAM_STATUS=0` 이면 끈다(질의 무응답 · 보고 무시). 그 밖(없음 포함) = 켬.
pub(crate) fn enabled_from(v: Option<&str>) -> bool {
    v.map(str::trim) != Some("0")
}

pub(crate) fn enabled() -> bool {
    enabled_from(std::env::var("CYS_PROGRAM_STATUS").ok().as_deref())
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum PState {
    Idle,
    Working,
    Done,
    Blocked,
    Error,
}

impl PState {
    pub(crate) fn as_str(self) -> &'static str {
        match self {
            PState::Idle => "idle",
            PState::Working => "working",
            PState::Done => "done",
            PState::Blocked => "blocked",
            PState::Error => "error",
        }
    }
    /// 요약 우선순위(클수록 급함): blocked > error > working > done > idle.
    fn urgency(self) -> u8 {
        match self {
            PState::Blocked => 4,
            PState::Error => 3,
            PState::Working => 2,
            PState::Done => 1,
            PState::Idle => 0,
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum Kind {
    Permission,
    Question,
    Auth,
}

impl Kind {
    pub(crate) fn as_str(self) -> &'static str {
        match self {
            Kind::Permission => "permission",
            Kind::Question => "question",
            Kind::Auth => "auth",
        }
    }
}

/// 검사를 전부 통과한 보고 하나. `state == None` = `clear`(기록을 지운다 · 기록이 가질 수 있는 상태가 아니다).
#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) struct Report {
    pub state: Option<PState>,
    /// 빈 문자열 = 뿌리 기록.
    pub id: String,
    pub kind: Option<Kind>,
    pub progress: Option<u8>,
    pub app: Option<String>,
    pub title: Option<String>,
    pub msg: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) enum Parsed {
    /// 지원 질의(`?`) — 답한다.
    Query,
    Report(Report),
    /// 규격이 버리라고 한 보고(한도 · 해독 실패 · 상태 없음 등). 사유는 진단용.
    Discard(&'static str),
}

fn trim_blank(s: &[u8]) -> &[u8] {
    let mut a = 0;
    let mut b = s.len();
    while a < b && matches!(s[a], b' ' | b'\t') {
        a += 1;
    }
    while b > a && matches!(s[b - 1], b' ' | b'\t') {
        b -= 1;
    }
    &s[a..b]
}

fn value_ok(v: &[u8]) -> bool {
    v.iter().all(|c| c.is_ascii_alphanumeric() || matches!(c, b'_' | b'.' | b',' | b'+' | b'/' | b'=' | b'-'))
}

fn segment_ok(s: &[u8]) -> bool {
    !s.is_empty() && s.len() <= MAX_SEGMENT && s.iter().all(|c| c.is_ascii_alphanumeric() || matches!(c, b'_' | b'.' | b'+' | b'-'))
}

fn id_ok(id: &[u8]) -> bool {
    if id.len() > MAX_ID {
        return false;
    }
    let segs: Vec<&[u8]> = id.split(|c| *c == b'/').collect();
    segs.len() <= MAX_DEPTH && segs.iter().all(|s| segment_ok(s))
}

fn b64_val(c: u8) -> Option<u8> {
    match c {
        b'A'..=b'Z' => Some(c - b'A'),
        b'a'..=b'z' => Some(c - b'a' + 26),
        b'0'..=b'9' => Some(c - b'0' + 52),
        b'+' => Some(62),
        b'/' => Some(63),
        _ => None,
    }
}

/// 엄격한 base64(패딩 선택) 해독 — 정규형만 받는다(버려지는 꼬리 비트가 0 이 아니면 거부). 실패 = None.
pub(crate) fn decode_b64_strict(v: &[u8]) -> Option<Vec<u8>> {
    let pad = v.iter().rev().take_while(|c| **c == b'=').count();
    if pad > 2 {
        return None;
    }
    let body = &v[..v.len() - pad];
    if body.len() % 4 == 1 {
        return None;
    }
    if pad > 0 && (body.len() + pad) % 4 != 0 {
        return None;
    }
    let mut out = Vec::with_capacity(body.len() * 3 / 4);
    let mut acc: u32 = 0;
    let mut bits = 0u32;
    for &c in body {
        let d = b64_val(c)?;
        acc = (acc << 6) | u32::from(d);
        bits += 6;
        if bits >= 8 {
            bits -= 8;
            out.push(((acc >> bits) & 0xff) as u8);
        }
    }
    // 정규형: 남은 비트는 0 이어야 한다(관대한 해독기가 버리는 비트를 우리는 거부한다).
    if bits > 0 && (acc & ((1u32 << bits) - 1)) != 0 {
        return None;
    }
    Some(out)
}

fn is_invisible(c: char) -> bool {
    matches!(c, '\u{061c}' | '\u{200b}'..='\u{200f}' | '\u{2028}'..='\u{202e}' | '\u{2060}' | '\u{2066}'..='\u{2069}' | '\u{feff}')
}

/// title/msg 값 → 평문. 길이 한도 · 엄격 base64 · UTF-8 · 제어 문자(C0·DEL·C1) 0 — 어긋나면 None(보고 통째 폐기).
/// 방향 바꿈·폭 0 문자는 지운다.
fn decode_text(v: &[u8], max_enc: usize, max_dec: usize) -> Option<String> {
    if v.len() > max_enc {
        return None;
    }
    let bytes = decode_b64_strict(v)?;
    if bytes.len() > max_dec {
        return None;
    }
    let s = String::from_utf8(bytes).ok()?;
    if s.chars().any(|c| c.is_control()) {
        return None;
    }
    Some(s.chars().filter(|c| !is_invisible(*c)).collect())
}

/// `7501;` 뒤 본문 하나를 판정한다. `seq_len` = 그 시퀀스 전체(ESC ] … 종결자) 바이트 수.
pub(crate) fn parse(body: &[u8], seq_len: usize) -> Parsed {
    if trim_blank(body) == b"?" {
        return Parsed::Query;
    }
    if seq_len > MAX_SEQUENCE {
        return Parsed::Discard("sequence too long");
    }
    let mut pairs: Vec<(&[u8], &[u8])> = Vec::new();
    for pair in body.split(|c| *c == b':') {
        let Some(eq) = pair.iter().position(|c| *c == b'=') else { continue };
        let key = trim_blank(&pair[..eq]);
        let val = trim_blank(&pair[eq + 1..]);
        if key.is_empty() || !key.iter().all(u8::is_ascii_lowercase) {
            continue; // 잘못된 키 = 그 쌍만 무시
        }
        if key.len() > MAX_KEY {
            return Parsed::Discard("key too long");
        }
        if !value_ok(val) {
            continue; // 값에 허용 밖 바이트 = 그 쌍만 무시
        }
        // ★(codex 1R MINOR ③) 한도는 **쌍마다** 본다 — 같은 키가 뒤에 또 와도 앞 쌍의 한도 위반은 보고 통째 폐기다.
        match key {
            b"id" if !id_ok(val) => return Parsed::Discard("bad id"),
            b"app" if val.len() > MAX_APP => return Parsed::Discard("app too long"),
            b"title" if decode_text(val, MAX_TITLE_ENCODED, MAX_TITLE_DECODED).is_none() => return Parsed::Discard("bad title"),
            b"msg" if decode_text(val, MAX_MSG_ENCODED, MAX_MSG_DECODED).is_none() => return Parsed::Discard("bad msg"),
            _ => {}
        }
        // 같은 키가 또 오면 뒤의 것이 이긴다.
        pairs.retain(|(k, _)| *k != key);
        pairs.push((key, val));
    }
    let get = |k: &str| pairs.iter().find(|(kk, _)| *kk == k.as_bytes()).map(|(_, v)| *v);
    let state = match get("state") {
        Some(b"idle") => Some(PState::Idle),
        Some(b"working") => Some(PState::Working),
        Some(b"done") => Some(PState::Done),
        Some(b"blocked") => Some(PState::Blocked),
        Some(b"error") => Some(PState::Error),
        Some(b"clear") => None,
        Some(_) => return Parsed::Discard("unknown state"),
        None => return Parsed::Discard("no state"),
    };
    let mut r = Report { state, id: String::new(), kind: None, progress: None, app: None, title: None, msg: None };
    if let Some(id) = get("id") {
        if !id_ok(id) {
            return Parsed::Discard("bad id");
        }
        r.id = String::from_utf8_lossy(id).into_owned();
    }
    if state == Some(PState::Blocked) {
        r.kind = match get("kind") {
            Some(b"permission") => Some(Kind::Permission),
            Some(b"question") => Some(Kind::Question),
            Some(b"auth") => Some(Kind::Auth),
            _ => None,
        };
    }
    if matches!(state, Some(PState::Working | PState::Blocked)) {
        if let Some(p) = get("progress") {
            if (1..=3).contains(&p.len()) && p.iter().all(u8::is_ascii_digit) {
                let n: u32 = std::str::from_utf8(p).ok().and_then(|s| s.parse().ok()).unwrap_or(u32::MAX);
                if n <= 100 {
                    r.progress = Some(n as u8);
                }
            }
        }
    }
    if let Some(app) = get("app") {
        if app.len() > MAX_APP {
            return Parsed::Discard("app too long");
        }
        if segment_ok(app) {
            r.app = Some(String::from_utf8_lossy(app).into_owned());
        }
    }
    if let Some(t) = get("title") {
        match decode_text(t, MAX_TITLE_ENCODED, MAX_TITLE_DECODED) {
            Some(s) => r.title = Some(s),
            None => return Parsed::Discard("bad title"),
        }
    }
    if let Some(m) = get("msg") {
        match decode_text(m, MAX_MSG_ENCODED, MAX_MSG_DECODED) {
            Some(s) => r.msg = Some(s),
            None => return Parsed::Discard("bad msg"),
        }
    }
    Parsed::Report(r)
}

// ---------------------------------------------------------------------------------------------
// 흐름 스캐너 — PTY 원시 바이트(청크 경계를 넘는다)에서 OSC 7501 · OSC 133;A(프롬프트 시작) · RIS(ESC c) 를 뽑는다.
// ---------------------------------------------------------------------------------------------

#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) enum Event {
    /// 7501 시퀀스 하나 — 본문(7501; 뒤) · 전체 길이 · BEL 종결 여부.
    Osc7501 { body: Vec<u8>, seq_len: usize, bel: bool },
    /// 새 셸 프롬프트 시작(OSC 133;A) — working·blocked 기록이 끝난다.
    PromptStart,
    /// 단말 완전 초기화(RIS) — 기록 전부 지움.
    Reset,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum ScanState {
    Ground,
    Esc,
    Osc,
    OscEsc,
}

/// 한 좌석 reader 스레드 전용 상태(유계 — OSC 본문은 [`MAX_SEQUENCE`] 바이트까지만 담고 넘치면 표시만 한다).
#[derive(Debug)]
pub(crate) struct Scanner {
    st: ScanState,
    buf: Vec<u8>,
    /// 지금 OSC 가 시작한 뒤 본 바이트 수(ESC ] 포함 · 담지 않은 것까지).
    seen: usize,
    overflow: bool,
}

impl Default for Scanner {
    fn default() -> Self {
        Scanner { st: ScanState::Ground, buf: Vec::new(), seen: 0, overflow: false }
    }
}

impl Scanner {
    fn finish(&mut self, bel: bool, out: &mut Vec<Event>) {
        let seq_len = self.seen + if bel { 1 } else { 2 };
        let body = std::mem::take(&mut self.buf);
        self.st = ScanState::Ground;
        if let Some(rest) = body.strip_prefix(b"7501;") {
            // 넘친 시퀀스는 본문을 다 담지 못했다 — 길이 한도로 버려지게 실제 길이를 넘긴다(질의로도 읽지 않는다).
            let rest = if self.overflow { Vec::new() } else { rest.to_vec() };
            out.push(Event::Osc7501 { body: rest, seq_len: if self.overflow { MAX_SEQUENCE + 1 } else { seq_len }, bel });
        } else if !self.overflow && (body == b"133;A" || body.starts_with(b"133;A;")) {
            out.push(Event::PromptStart);
        }
        self.overflow = false;
        self.seen = 0;
    }

    fn push_osc(&mut self, b: u8) {
        self.seen += 1;
        if self.buf.len() < MAX_SEQUENCE {
            self.buf.push(b);
        } else {
            self.overflow = true;
        }
    }

    /// 청크 하나를 먹고 완성된 사건을 낸다.
    pub(crate) fn feed(&mut self, chunk: &[u8]) -> Vec<Event> {
        let mut out = Vec::new();
        for &b in chunk {
            match self.st {
                ScanState::Ground => {
                    if b == 0x1b {
                        self.st = ScanState::Esc;
                    }
                }
                ScanState::Esc => match b {
                    b']' => {
                        self.st = ScanState::Osc;
                        self.buf.clear();
                        self.seen = 2;
                        self.overflow = false;
                    }
                    b'c' => {
                        self.st = ScanState::Ground;
                        out.push(Event::Reset);
                    }
                    0x1b => self.st = ScanState::Esc,
                    _ => self.st = ScanState::Ground,
                },
                ScanState::Osc => match b {
                    0x07 => self.finish(true, &mut out),
                    0x1b => self.st = ScanState::OscEsc,
                    // CAN·SUB = 시퀀스 취소(ECMA-48).
                    0x18 | 0x1a => {
                        self.st = ScanState::Ground;
                        self.buf.clear();
                    }
                    _ => self.push_osc(b),
                },
                ScanState::OscEsc => {
                    if b == b'\\' {
                        self.finish(false, &mut out);
                    } else {
                        // 종결 없이 새 이스케이프가 시작됐다 — 이 OSC 는 버리고 ESC 다음 바이트로 다시 읽는다.
                        self.buf.clear();
                        self.st = ScanState::Esc;
                        match b {
                            b']' => {
                                self.st = ScanState::Osc;
                                self.seen = 2;
                                self.overflow = false;
                            }
                            b'c' => {
                                self.st = ScanState::Ground;
                                out.push(Event::Reset);
                            }
                            0x1b => {}
                            _ => self.st = ScanState::Ground,
                        }
                    }
                }
            }
        }
        out
    }
}

/// 질의 응답 바이트(종결자는 질의가 쓴 것과 같게).
pub(crate) fn query_reply(bel: bool) -> Vec<u8> {
    let mut v = QUERY_REPLY_HEAD.to_vec();
    if bel {
        v.push(0x07);
    } else {
        v.extend_from_slice(b"\x1b\\");
    }
    v
}

// ---------------------------------------------------------------------------------------------
// 좌석별 저장소.
// ---------------------------------------------------------------------------------------------

#[derive(Clone, Debug)]
pub(crate) struct Record {
    pub state: PState,
    pub kind: Option<Kind>,
    pub progress: Option<u8>,
    pub app: Option<String>,
    pub title: Option<String>,
    pub msg: Option<String>,
    pub updated: Instant,
    /// 갱신 순번(가장 오래 갱신되지 않은 것을 버리는 기준 · Instant 동률 방지).
    tick: u64,
}

#[derive(Debug, Default)]
pub(crate) struct Store {
    records: BTreeMap<String, Record>,
    tick: u64,
    /// 판 계수 — 기록이 바뀔 때마다(적용 · clear · 지움) +1 · 줄지 않는다(`activity::wire_with` 순번 재료).
    pub version: u64,
    /// 이 좌석이 질의를 보냈고 우리가 답했다(= 답을 받은 프로그램은 화면 표지를 그리지 않는다).
    pub answered: u64,
    /// 관측기가 돌지 않아 답하지 않은 질의 수.
    pub unanswered: u64,
    pub reports: u64,
    pub discarded: u64,
    pub last_discard: Option<&'static str>,
    /// 마지막으로 **적용한** 보고 원문(진단 · 상한 [`RAW_KEEP`]) + 시각.
    pub last_raw: Option<(String, Instant)>,
    /// 마지막으로 기록을 지운 까닭(clear · 셸 프롬프트 · 에이전트 종료 · RIS) + 시각.
    pub last_wipe: Option<(&'static str, Instant)>,
}

impl Store {
    /// 보고 하나를 적용한다(통째 교체 · clear = 그 id 와 그 아래 전부 / id 없으면 전부).
    pub(crate) fn apply(&mut self, r: &Report, raw: &[u8], now: Instant) {
        self.reports += 1;
        self.version += 1;
        let keep = &raw[..raw.len().min(RAW_KEEP)];
        self.last_raw = Some((String::from_utf8_lossy(keep).into_owned(), now));
        let Some(state) = r.state else {
            if r.id.is_empty() {
                self.records.clear();
            } else {
                let prefix = format!("{}/", r.id);
                self.records.retain(|k, _| k != &r.id && !k.starts_with(&prefix));
            }
            self.last_wipe = Some(("clear report", now));
            return;
        };
        self.records.remove(&r.id);
        if self.records.len() >= MAX_RECORDS {
            if let Some(oldest) = self.records.iter().min_by_key(|(_, v)| v.tick).map(|(k, _)| k.clone()) {
                self.records.remove(&oldest);
            }
        }
        self.tick += 1;
        self.records.insert(
            r.id.clone(),
            Record {
                state,
                kind: r.kind,
                progress: r.progress,
                app: r.app.clone(),
                title: r.title.clone(),
                msg: r.msg.clone(),
                updated: now,
                tick: self.tick,
            },
        );
    }

    pub(crate) fn discard(&mut self, why: &'static str) {
        self.discarded += 1;
        self.last_discard = Some(why);
    }

    /// 프로세스가 끝났거나 새 셸 프롬프트가 떴다 — working·blocked 기록이 끝난다(규격). `all` 이면 전부(에이전트 종료 · RIS).
    pub(crate) fn wipe(&mut self, all: bool, why: &'static str, now: Instant) {
        let before = self.records.len();
        if all {
            self.records.clear();
        } else {
            self.records.retain(|_, v| !matches!(v.state, PState::Working | PState::Blocked));
        }
        if self.records.len() != before {
            self.last_wipe = Some((why, now));
            self.version += 1;
        }
    }

    pub(crate) fn len(&self) -> usize {
        self.records.len()
    }

    /// 보일 기록 하나 — 가장 급한 것(blocked > error > working > done > idle) · 같으면 가장 최근에 갱신된 것.
    pub(crate) fn summary(&self) -> Option<(&str, &Record)> {
        self.records
            .iter()
            .max_by_key(|(_, v)| (v.state.urgency(), v.tick))
            .map(|(k, v)| (k.as_str(), v))
    }
}

/// reader 한 청크의 처리 결과 — 호출부가 PTY 로 쓸 질의 응답(있으면).
#[derive(Debug, Default, PartialEq, Eq)]
pub(crate) struct Ingest {
    pub replies: Vec<Vec<u8>>,
    pub applied: usize,
}

/// 사건들을 저장소에 반영하고 낼 응답을 돌려준다(순수 — 시각 주입). `answer` = 지금 질의에 답해도 되는가
/// (화면 관측기가 **실제로 돌고 있을 때만** — 답하면 Claude 가 제목 표지를 지우는데, 관측기가 없으면 덧씌울 세대·순번도 없다).
/// 답하지 않은 질의는 `unanswered` 로 센다(진단).
pub(crate) fn ingest(store: &mut Store, events: Vec<Event>, now: Instant, answer: bool) -> Ingest {
    let mut out = Ingest::default();
    for ev in events {
        match ev {
            Event::Osc7501 { body, seq_len, bel } => match parse(&body, seq_len) {
                Parsed::Query if answer => {
                    store.answered += 1;
                    out.replies.push(query_reply(bel));
                }
                Parsed::Query => store.unanswered += 1,
                Parsed::Report(r) => {
                    store.apply(&r, &body, now);
                    out.applied += 1;
                }
                Parsed::Discard(why) => store.discard(why),
            },
            Event::PromptStart => store.wipe(false, "shell prompt (OSC 133;A)", now),
            Event::Reset => store.wipe(true, "terminal reset (RIS)", now),
        }
    }
    out
}

/// 좌석 줄에 보일 덧씌움 — `activity::wire` 가 화면 판정 대신 싣는다.
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct Overlay {
    pub state: PState,
    pub kind: Option<Kind>,
    pub app: Option<String>,
    pub msg: Option<String>,
    pub title: Option<String>,
    pub progress: Option<u8>,
    pub id: String,
    pub age_secs: f64,
    /// done·error 를 사람이 이미 봤다(그 기록 갱신 뒤에 사람 입력이 있었다) → 대기로 보인다.
    pub seen: bool,
    pub records: usize,
}

/// 저장소 + 사람 마지막 입력 시각 → 덧씌움(기록이 없으면 None = 화면 판정 그대로).
pub(crate) fn overlay(store: &Store, last_human_input: Option<Instant>, now: Instant) -> Option<Overlay> {
    let (id, rec) = store.summary()?;
    // ★(codex 1R MINOR ④) app 은 가장 가까운 조상 기록에서 물려받는다(규격 — 급한 자식 기록이 app 을 되풀이하지 않아도 이름이 남게).
    let app = rec.app.clone().or_else(|| {
        let mut cur = id;
        loop {
            cur = match cur.rfind('/') {
                Some(i) => &cur[..i],
                None if !cur.is_empty() => "",
                None => return None,
            };
            if let Some(a) = store.records.get(cur).and_then(|r| r.app.clone()) {
                return Some(a);
            }
            if cur.is_empty() {
                return None;
            }
        }
    });
    let seen = matches!(rec.state, PState::Done | PState::Error) && last_human_input.is_some_and(|h| h > rec.updated);
    Some(Overlay {
        state: rec.state,
        kind: rec.kind,
        app,
        msg: rec.msg.clone(),
        title: rec.title.clone(),
        progress: rec.progress,
        id: id.to_string(),
        age_secs: (now.saturating_duration_since(rec.updated).as_secs_f64() * 1000.0).round() / 1000.0,
        seen,
        records: store.len(),
    })
}

/// ★(1.1.16 · 차용 ② ⒞) 진단 — `surface.list` 의 `program_status_diag`(`cys daemon explain-state` 가 사람 말로 푼다).
/// 마지막 원문은 **검사를 통과해 적용한** 보고뿐이다(허용 문자 집합 = ASCII 영숫자와 `_.,+/=-:` · 제어 문자 0).
pub(crate) fn diag_wire(store: &Store, now: Instant) -> serde_json::Value {
    let age = |t: Instant| (now.saturating_duration_since(t).as_secs_f64() * 1000.0).round() / 1000.0;
    serde_json::json!({
        "answered_queries": store.answered,
        "unanswered_queries": store.unanswered,
        "reports": store.reports,
        "discarded": store.discarded,
        "last_discard": store.last_discard,
        "last_report": store.last_raw.as_ref().map(|(r, _)| r.as_str()),
        "last_report_age_secs": store.last_raw.as_ref().map(|(_, t)| age(*t)),
        "last_wipe": store.last_wipe.map(|(w, _)| w),
        "last_wipe_age_secs": store.last_wipe.map(|(_, t)| age(t)),
        "records": store.len(),
    })
}

/// 좌석 하나의 진단(락은 짧게 · 독살된 락도 읽는다).
pub(crate) fn diag(s: &crate::state::Surface) -> serde_json::Value {
    let store = s.program_status.lock().unwrap_or_else(|e| e.into_inner());
    diag_wire(&store, Instant::now())
}

#[cfg(test)]
#[path = "program_status_tests.rs"]
mod tests;
