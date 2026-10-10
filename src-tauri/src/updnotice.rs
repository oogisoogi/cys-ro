//! 자동 갱신 결과 알림 — 앱은 **읽고 보여 주기만** 한다(1.1.8 U4 · 설계 AUTO-UPDATE-118 §3-12 · 📌18).
//!
//! 갱신을 결정·집행하는 것은 데몬 러너(U2)이고, 그 결과는 상태 폴더의 `state.json` 에 남는다(쓰는 이 = 러너 하나).
//! 앱은 그 파일을 **읽기만** 하고, 「몇 번 보여 줬나」 장부는 같은 폴더의 앱 전용 파일 `app-notify.json` 에만 쓴다
//! (파일당 쓰는 이 하나 — 러너와 앱이 서로의 기록을 덮지 않는다 · master#971bdf3c 결정 A).
//!
//! 접점 칸(앱이 읽는 것 · master#971bdf3c 로 U2 에 같은 정의 전달):
//!   `state.json.last_result = {result_id, kind ∈ ok|rollback_ok|rollback_failed|installed_revoked, release_seq, version?, notes_ko?}`
//!   `state.json.seats_blocked = {reason: "journal_unrecoverable"}`
//! 앱 장부(`app-notify.json` · 칸 이름은 설계 그대로): `{pending_notification: {result_id, shown_count}?, last_notified_result_id?,
//!   rollback_failed_last_shown_at?}`.
//!
//! 알림 순서(§3-12 · 표시와 기록 사이에 앱이 죽어도 끝없이 반복되지 않게):
//!   ① `last_result` 를 읽고 `last_notified_result_id ≠ result_id` 이면
//!   ② **표시 전에** `pending_notification{result_id, shown_count+1}` 을 원자 기록(이 기록이 실패하면 보여 주지 않는다)
//!   ③ 토스트 표시(화면 · 텍스트 노드로만)
//!   ④ 표시 뒤 `last_notified_result_id = result_id` 원자 기록.
//!   ③~④ 사이에 죽으면 다음 기동 때 `shown_count` 를 보고 **최대 1번 더**(합계 ≤ 2) 보여 주고 ④ 로 닫는다.
//!   롤백 실패만 닫힌 뒤에도 **하루 1회** 다시 보여 준다(`rollback_failed_last_shown_at` — 이것도 표시 전에 기록).
//!
//! ★(2판 · codex 1R ①) 장부의 읽기→판정→쓰기는 **한 덩어리로 직렬화**한다 — 프로세스 안 뮤텍스 + 상태 폴더의 `app-notify.lock`
//!   파일 잠금(`File::lock` · 다른 앱 인스턴스까지). 임시 파일은 호출마다 `create_new` 로 새 이름을 쓴다(고정 PID 이름은 두 호출이
//!   서로의 임시 파일을 truncate 한다 — `src/pack.rs` 의 같은 꼴 실사고). 병렬 두 호출이 둘 다 `shown_count=0` 을 읽어
//!   합계 2 를 넘기는 길이 이것으로 닫힌다.

use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::path::Path;

/// 러너가 쓰는 상태 파일(앱은 읽기만).
pub const STATE_FILE: &str = "state.json";
/// 앱 전용 장부(앱만 쓴다).
pub const ACK_FILE: &str = "app-notify.json";
/// 결과당 최대 표시 횟수(첫 표시 + ③~④ 사이 충돌 뒤 1회 = 2 · 설계 「중복 최대 1회」).
pub const MAX_SHOWS: u32 = 2;
/// 롤백 실패 재안내 간격(초) — 하루 1회.
pub const ROLLBACK_FAILED_REPEAT_SECS: i64 = 86_400;
/// 릴리스 노트(`notes_ko`) 표시 상한(글자) — 설계 §6-1 「문자열 ≤80자 · 알림 1줄」 · 발행·검증 쪽 `cys::update::feed::NOTES_MAX_CHARS` 와 같은 값
/// (아래 시험이 두 값을 대조한다 · codex 1R ⑥).
pub const NOTES_MAX_CHARS: usize = 80;
/// 앱 장부 직렬화용 잠금 파일(앱만 쓴다 · 내용 없음) — codex 1R ① 처방(읽기→판정→쓰기 한 덩어리).
pub const LOCK_FILE: &str = "app-notify.lock";

/// 토스트 id — 롤백 실패만 안내용 수명(10분)·만료 배너를 받는다(ui/src/toastttl.ts 의 정확 일치 목록과 값이 같다).
pub const TOAST_ID_RESULT: &str = "update-result";
pub const TOAST_ID_ROLLBACK_FAILED: &str = "update-rollback-failed";

/// 알림 문구 표(§3-12 · 왕초보 말투 1문장 · 위협·공포 낱말 0 — 아래 시험이 낱말을 잰다).
pub const TEXT_OK_WITH_VERSION: &str = "자비스가 새 판({v})으로 바뀌었어요. 하던 일은 그대로 이어집니다.";
pub const TEXT_OK: &str = "자비스가 새 판으로 바뀌었어요. 하던 일은 그대로 이어집니다.";
pub const TEXT_ROLLBACK_OK: &str = "새 판으로 바꾸다가 잘 안 돼서 원래 판으로 돌려 두었어요. 지금처럼 쓰시면 됩니다.";
pub const TEXT_ROLLBACK_FAILED: &str =
    "자비스를 다시 설치하면 바로 쓸 수 있어요. 처음 설치할 때 쓴 링크 한 줄을 다시 붙여 넣어 주세요.";
pub const TEXT_INSTALLED_REVOKED: &str = "안전을 위해 새 판이 곧 들어올 예정이에요. 지금처럼 쓰시면 됩니다.";
/// 📌18 좌석 0 상태 — 토스트가 아니라 창 안 고정 안내 1줄(닫기 단추 없음 · 상태가 풀리면 사라짐).
pub const TEXT_SEATS_BLOCKED: &str =
    "자비스가 잠깐 쉬고 있어요. 처음 설치할 때 쓴 링크 한 줄을 다시 붙여 넣으시면 바로 다시 쓸 수 있어요.";
/// 토스트 제목(짧은 이름표 — 같은 규칙).
pub const TITLE_OK: &str = "자비스 새 판";
pub const TITLE_ROLLBACK_OK: &str = "자비스 판 안내";
pub const TITLE_ROLLBACK_FAILED: &str = "자비스 다시 쓰기 안내";
pub const TITLE_INSTALLED_REVOKED: &str = "자비스 새 판 안내";
/// 릴리스 노트를 붙일 때의 머리말.
pub const NOTES_LEAD: &str = "달라진 점: ";

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Kind {
    Ok,
    RollbackOk,
    RollbackFailed,
    InstalledRevoked,
}

impl Kind {
    fn parse(s: &str) -> Option<Kind> {
        match s {
            "ok" => Some(Kind::Ok),
            "rollback_ok" => Some(Kind::RollbackOk),
            "rollback_failed" => Some(Kind::RollbackFailed),
            "installed_revoked" => Some(Kind::InstalledRevoked),
            _ => None,
        }
    }
}

/// `pending_notification` — 표시 **전에** 기록한 「이 결과를 몇 번째로 보여 주는 중」.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Pending {
    pub result_id: String,
    pub shown_count: u32,
}

/// 앱 장부(`app-notify.json`).
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct Ack {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub pending_notification: Option<Pending>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub last_notified_result_id: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub rollback_failed_last_shown_at: Option<i64>,
}

/// 보여 줄 토스트 1개(화면은 이 값을 텍스트 노드로만 그린다).
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct Toast {
    pub toast_id: &'static str,
    pub result_id: String,
    pub title: &'static str,
    pub body: String,
}

/// 판정 결과 — 부작용 없는 순수 값(장부 쓰기는 [`take_at`] 이 한다).
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Plan {
    /// 보여 줄 것이 없다.
    Nothing,
    /// 이미 최대 횟수만큼 보여 줬다 — 보여 주지 않고 ④ 로 닫기만 한다.
    Close { result_id: String },
    /// ② `ack` 를 먼저 기록한 뒤 ③ `toast` 를 보여 준다.
    Show { ack: Ack, toast: Toast },
}

/// result_id 형식 — 1~64자 · 영숫자와 `._:-` 만(장부 열쇠 · 화면에는 나가지 않는다).
pub fn valid_result_id(s: &str) -> bool {
    !s.is_empty() && s.chars().count() <= 64 && s.chars().all(|c| c.is_ascii_alphanumeric() || matches!(c, '.' | '_' | ':' | '-'))
}

/// 표시용 판 문자열 — `1.1.9` 꼴(숫자 마디 1~4개 · 20자 이하)만 받는다. 아니면 괄호째 뺀다.
pub fn display_version(v: Option<&str>) -> Option<&str> {
    let v = v?;
    let ok = !v.is_empty()
        && v.len() <= 20
        && v.split('.').count() <= 4
        && v.split('.').all(|p| !p.is_empty() && p.bytes().all(|b| b.is_ascii_digit()));
    ok.then_some(v)
}

/// 화면에 내보내면 안 되는 글자 — 제어문자(Cc) · 줄 나눔 2종 · 방향 바꿈 제어(겉보기와 다른 순서로 읽히게 하는 글자).
pub fn is_forbidden_char(c: char) -> bool {
    c.is_control()
        || matches!(
            c,
            '\u{2028}' | '\u{2029}' | '\u{200E}' | '\u{200F}' | '\u{061C}' | '\u{202A}'..='\u{202E}' | '\u{2066}'..='\u{2069}'
        )
}

/// `notes_ko` 검증 — 발행·검증 쪽 판정(`cys::update::feed::check_notes_ko` — ≤80자 · 제어문자 0 · 금지 어휘 0 · 비어 있지 않음)을
/// **그대로 한 벌** 쓰고, 화면에는 줄 나눔·방향 바꿈 글자까지 더 막는다. 하나라도 걸리면 **통째로 거부**(None · 고쳐서 보여 주지 않는다).
pub fn sanitize_notes(n: Option<&str>) -> Option<&str> {
    let n = n?;
    if cys::update::feed::check_notes_ko(n).is_err() || n.chars().any(is_forbidden_char) {
        return None;
    }
    let t = n.trim();
    (!t.is_empty() && t.chars().count() <= NOTES_MAX_CHARS).then_some(t)
}

fn toast_for(kind: Kind, result_id: &str, last: &Value) -> Toast {
    let (toast_id, title, body) = match kind {
        Kind::Ok => {
            let mut body = match display_version(last.get("version").and_then(Value::as_str)) {
                Some(v) => TEXT_OK_WITH_VERSION.replace("{v}", v),
                None => TEXT_OK.to_string(),
            };
            if let Some(n) = sanitize_notes(last.get("notes_ko").and_then(Value::as_str)) {
                // 알림 1줄(설계 §6-1) — 줄바꿈 없이 같은 줄에 잇는다.
                body.push(' ');
                body.push_str(NOTES_LEAD);
                body.push_str(n);
            }
            (TOAST_ID_RESULT, TITLE_OK, body)
        }
        Kind::RollbackOk => (TOAST_ID_RESULT, TITLE_ROLLBACK_OK, TEXT_ROLLBACK_OK.to_string()),
        Kind::RollbackFailed => (TOAST_ID_ROLLBACK_FAILED, TITLE_ROLLBACK_FAILED, TEXT_ROLLBACK_FAILED.to_string()),
        Kind::InstalledRevoked => (TOAST_ID_RESULT, TITLE_INSTALLED_REVOKED, TEXT_INSTALLED_REVOKED.to_string()),
    };
    Toast { toast_id, result_id: result_id.to_string(), title, body }
}

/// ①② 판정(순수). `state` = `state.json` 전체(읽지 못했으면 호출부가 판정하지 않는다) · `ack` = 앱 장부 · `now` = 유닉스 초.
pub fn plan(state: &Value, ack: &Ack, now: i64) -> Plan {
    let Some(last) = state.get("last_result").filter(|v| v.is_object()) else {
        return Plan::Nothing;
    };
    let Some(result_id) = last.get("result_id").and_then(Value::as_str).filter(|s| valid_result_id(s)) else {
        return Plan::Nothing;
    };
    let Some(kind) = last.get("kind").and_then(Value::as_str).and_then(Kind::parse) else {
        return Plan::Nothing;
    };
    // 필수 칸 `release_seq`(설계 §3-12 last_result 정의) — 정수 ≥1 이 아니면 결과 기록으로 믿지 않는다(codex 1R ⑤).
    if last.get("release_seq").and_then(Value::as_u64).filter(|n| *n >= 1).is_none() {
        return Plan::Nothing;
    }
    // 이미 닫힌 결과 — 롤백 실패만 하루 1회 다시(그 밖은 끝).
    if ack.last_notified_result_id.as_deref() == Some(result_id) {
        if kind != Kind::RollbackFailed {
            return Plan::Nothing;
        }
        let due = match ack.rollback_failed_last_shown_at {
            None => true,
            // 시계가 하루 넘게 뒤로 간 기록(미래 시각)은 믿지 않고 다시 보여 준다 — 그 밖의 뒤로 감은 기다린다.
            Some(at) => now - at >= ROLLBACK_FAILED_REPEAT_SECS || at - now > ROLLBACK_FAILED_REPEAT_SECS,
        };
        if !due {
            return Plan::Nothing;
        }
        let mut next = ack.clone();
        next.rollback_failed_last_shown_at = Some(now);
        return Plan::Show { ack: next, toast: toast_for(kind, result_id, last) };
    }
    // 아직 닫히지 않은 결과 — 몇 번째 표시인가.
    let prior = match &ack.pending_notification {
        Some(p) if p.result_id == result_id => p.shown_count,
        _ => 0,
    };
    if prior >= MAX_SHOWS {
        return Plan::Close { result_id: result_id.to_string() };
    }
    let mut next = ack.clone();
    next.pending_notification = Some(Pending { result_id: result_id.to_string(), shown_count: prior + 1 });
    if kind == Kind::RollbackFailed {
        next.rollback_failed_last_shown_at = Some(now);
    }
    Plan::Show { ack: next, toast: toast_for(kind, result_id, last) }
}

/// ④ — 표시가 끝난 결과를 닫는다(순수). 그 결과의 대기 표지만 지운다(다른 결과의 표지는 둔다).
pub fn close(ack: &Ack, result_id: &str) -> Ack {
    let mut next = ack.clone();
    next.last_notified_result_id = Some(result_id.to_string());
    if next.pending_notification.as_ref().map(|p| p.result_id == result_id).unwrap_or(false) {
        next.pending_notification = None;
    }
    next
}

/// 📌18 — `seats_blocked.reason == "journal_unrecoverable"` 이면 창 안 고정 안내 문구(그 밖·판독 불가 = None).
pub fn seats_blocked_text(state: &Value) -> Option<&'static str> {
    (state.pointer("/seats_blocked/reason").and_then(Value::as_str) == Some("journal_unrecoverable")).then_some(TEXT_SEATS_BLOCKED)
}

// ── 파일 ─────────────────────────────────────────────────────────────────────────────

/// `state.json` 읽기 — 없음 = Ok(None) · 읽기·해석 실패 = Err(호출부는 아무것도 보여 주지 않는다 · 추측 금지).
pub fn read_state(dir: &Path) -> Result<Option<Value>, String> {
    match std::fs::read(dir.join(STATE_FILE)) {
        Ok(b) => serde_json::from_slice(&b).map(Some).map_err(|e| format!("state.json 판독 불가: {e}")),
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(None),
        Err(e) => Err(e.to_string()),
    }
}

/// 앱 장부 읽기 — 없음·깨짐 = 빈 장부(다음 쓰기가 통째로 바꾼다 · 깨진 장부로 멈추지 않는다).
pub fn read_ack(dir: &Path) -> Ack {
    std::fs::read(dir.join(ACK_FILE)).ok().and_then(|b| serde_json::from_slice(&b).ok()).unwrap_or_default()
}

/// 원자 쓰기 — 같은 폴더 임시 파일 → fsync → rename → (유닉스) 폴더 fsync.
pub fn write_ack(dir: &Path, ack: &Ack) -> std::io::Result<()> {
    use std::io::Write;
    let bytes = serde_json::to_vec(ack).map_err(|e| std::io::Error::new(std::io::ErrorKind::Other, e))?;
    // 호출마다 새 이름(pid · 단조 일련 · 나노초) + create_new — 남의 임시 파일을 열어 truncate 하지 않는다.
    static SEQ: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(0);
    let seq = SEQ.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
    let nanos = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).map(|d| d.subsec_nanos()).unwrap_or(0);
    let tmp = dir.join(format!(".{ACK_FILE}.tmp-{}-{seq}-{nanos}", std::process::id()));
    let res = (|| {
        let mut f = std::fs::OpenOptions::new().write(true).create_new(true).open(&tmp)?;
        f.write_all(&bytes)?;
        f.sync_all()?;
        drop(f);
        std::fs::rename(&tmp, dir.join(ACK_FILE))?;
        #[cfg(unix)]
        std::fs::File::open(dir)?.sync_all()?;
        Ok(())
    })();
    if res.is_err() {
        let _ = std::fs::remove_file(&tmp);
    }
    res
}

/// 장부 임계 구역의 프로세스 안 뮤텍스(같은 앱 프로세스의 스레드끼리).
static ACK_MUTEX: std::sync::Mutex<()> = std::sync::Mutex::new(());

/// 장부 임계 구역 — 프로세스 안 뮤텍스 + `app-notify.lock` 배타 파일 잠금(블로킹) 안에서 `f` 를 돈다. 잠금을 못 잡으면 Err(호출부 = 아무것도 안 함).
fn with_ack_lock<T>(dir: &Path, f: impl FnOnce() -> T) -> std::io::Result<T> {
    let _g = ACK_MUTEX.lock().unwrap_or_else(|e| e.into_inner());
    let lf = std::fs::OpenOptions::new().create(true).truncate(false).write(true).open(dir.join(LOCK_FILE))?;
    lf.lock()?;
    let out = f();
    let _ = lf.unlock();
    Ok(out)
}

/// ①② 집행 — 판정하고, 보여 줄 것이면 **표시 전에** 장부를 기록한 뒤 토스트를 돌려준다.
/// 기록이 실패하면 보여 주지 않는다(None) — 기록 없이 보여 주면 「중복 ≤ 1」 상한이 사라진다.
/// 이미 최대 횟수면 ④ 로 닫고 None.
pub fn take_at(dir: &Path, now: i64) -> Option<Toast> {
    // 판정할 것이 없으면 잠금 파일도 만들지 않는다(갱신 기록이 없는 기기의 상태 폴더를 건드리지 않게).
    let state = read_state(dir).ok()??;
    with_ack_lock(dir, || {
        let ack = read_ack(dir);
        #[cfg(test)]
        let _cs = cs_probe::enter(dir);
        match plan(&state, &ack, now) {
            Plan::Nothing => None,
            Plan::Close { result_id } => {
                let _ = write_ack(dir, &close(&ack, &result_id));
                None
            }
            Plan::Show { ack: next, toast } => write_ack(dir, &next).ok().map(|_| toast),
        }
    })
    .ok()
    .flatten()
}

/// ④ 집행 — 표시 뒤 닫기. 형식이 틀린 id 는 기록하지 않는다.
pub fn done_at(dir: &Path, result_id: &str) -> bool {
    if !valid_result_id(result_id) {
        return false;
    }
    with_ack_lock(dir, || {
        let ack = read_ack(dir);
        #[cfg(test)]
        let _cs = cs_probe::enter(dir);
        write_ack(dir, &close(&ack, result_id)).is_ok()
    })
    .unwrap_or(false)
}

/// 📌18 집행 — 판독 불가·없음 = None.
pub fn seats_blocked_at(dir: &Path) -> Option<&'static str> {
    read_state(dir).ok()?.as_ref().and_then(seats_blocked_text)
}

/// ★(3판 · codex 2R MAJOR① → 4판 · Fable 3R MINOR-2) 시험 전용 임계 구역 탐침 — 장부를 **읽은 뒤 · 쓰기 전**(`take_at`·`done_at` 의 그 자리)에 선다.
/// 상태 폴더에 `.cs-probe` 가 있을 때만 움직인다(그 밖 = 아무것도 안 함 · 제품 빌드에는 없다).
///   · 들어오면 `.cs-in-<나노초>-<pid>-<스레드>` 를 만들고, 그 파일은 **쓰기가 끝날 때**(가드 Drop)까지 남는다.
///   · 다른 참가자가 함께 들어와 있으면(겹침 = 잠금이 뚫림) `.cs-overlap` 을 남긴다.
///   · 그리고 시험이 `.cs-go` 를 놓을 때까지 그 자리에 선다 — 시험은 그 사이 두 잠금이 실제로 잡혀 있는지를 **비차단 시도**로 잰다
///     ([`mutex_is_held`] · [`lock_file_is_held`]). 시간 유예(옛 300ms)에 기대지 않는다: 잠금이 빠진 뮤턴트는 시도가 성공해 곧바로 적색이다.
/// 정직: 맥(flock · 실측)의 파일 잠금은 열린 파일 단위라 같은 프로세스의 다른 fd 도 막는다(윈 LockFileEx 도 핸들 단위 —
///   실측 = windows-build 레인 updnotice 스텝). 그래서 파일 잠금 보유는 같은 프로세스 스레드에서도, 다른 프로세스에서도 잴 수 있다.
#[cfg(test)]
pub(crate) mod cs_probe {
    use std::path::{Path, PathBuf};
    use std::time::{Duration, Instant};

    pub(crate) const CFG: &str = ".cs-probe";
    pub(crate) const OVERLAP: &str = ".cs-overlap";
    const GO: &str = ".cs-go";
    /// 안전판 — 시험이 `.cs-go` 를 놓지 못하고 죽어도 참가자가 영원히 서 있지 않게(판정에는 쓰지 않는다).
    const DEADLINE: Duration = Duration::from_secs(15);

    pub(crate) struct Inside(Option<PathBuf>);
    impl Drop for Inside {
        fn drop(&mut self) {
            if let Some(p) = self.0.take() {
                let _ = std::fs::remove_file(p);
            }
        }
    }

    fn inside(dir: &Path) -> usize {
        std::fs::read_dir(dir)
            .map(|r| r.filter_map(|e| e.ok()).filter(|e| e.file_name().to_string_lossy().starts_with(".cs-in-")).count())
            .unwrap_or(0)
    }

    pub(crate) fn enter(dir: &Path) -> Inside {
        if !dir.join(CFG).exists() {
            return Inside(None);
        }
        let nanos = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).map(|d| d.as_nanos()).unwrap_or(0);
        let tid: String = format!("{:?}", std::thread::current().id()).chars().filter(char::is_ascii_digit).collect();
        let me = dir.join(format!(".cs-in-{nanos:024}-{}-{tid}", std::process::id()));
        std::fs::write(&me, b"").unwrap();
        if inside(dir) > 1 {
            let _ = std::fs::write(dir.join(OVERLAP), b"");
        }
        let t0 = Instant::now();
        while !dir.join(GO).exists() && t0.elapsed() < DEADLINE {
            std::thread::sleep(Duration::from_millis(2));
        }
        Inside(Some(me))
    }

    /// 누군가 임계 구역 안에 서 있을 때까지 기다린다(신호 = 그 참가자의 `.cs-in-` 파일).
    pub(crate) fn wait_someone_inside(dir: &Path) {
        let t0 = Instant::now();
        while inside(dir) == 0 {
            assert!(t0.elapsed() < DEADLINE, "참가자가 임계 구역에 들어오지 않았다");
            std::thread::sleep(Duration::from_millis(2));
        }
    }

    /// 서 있는 참가자들을 놓아 준다(이후 들어오는 참가자도 서지 않는다).
    pub(crate) fn go(dir: &Path) {
        std::fs::write(dir.join(GO), b"").unwrap();
    }

    /// 프로세스 뮤텍스가 지금 누군가에게 잡혀 있는가(비차단 시도 · 같은 프로세스에서만 의미).
    pub(crate) fn mutex_is_held() -> bool {
        matches!(super::ACK_MUTEX.try_lock(), Err(std::sync::TryLockError::WouldBlock))
    }

    /// `app-notify.lock` 파일 잠금이 지금 누군가(이 프로세스의 다른 fd · 다른 프로세스)에게 잡혀 있는가(새 fd 로 비차단 시도).
    pub(crate) fn lock_file_is_held(dir: &Path) -> bool {
        let f = std::fs::OpenOptions::new().create(true).truncate(false).write(true).open(dir.join(super::LOCK_FILE)).unwrap();
        match f.try_lock() {
            Ok(()) => {
                let _ = f.unlock();
                false
            }
            Err(std::fs::TryLockError::WouldBlock) => true,
            Err(e) => panic!("잠금 시도 자체가 실패: {e:?}"),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    /// 사용자 문구에 쓰지 않는 낱말(설계 §3-12 · CI 어휘 검사 대상).
    const BANNED_WORDS: [&str; 5] = ["오류", "실패", "위험", "손상", "경고"];

    fn tmpdir(tag: &str) -> std::path::PathBuf {
        let d = std::env::temp_dir().join(format!("u4-updnotice-{tag}-{}-{}", std::process::id(), line!()));
        let _ = std::fs::remove_dir_all(&d);
        std::fs::create_dir_all(&d).unwrap();
        d
    }
    fn st(id: &str, kind: &str) -> Value {
        json!({"last_result": {"result_id": id, "kind": kind, "release_seq": 7}})
    }
    fn put_state(d: &Path, v: &Value) {
        std::fs::write(d.join(STATE_FILE), serde_json::to_vec(v).unwrap()).unwrap();
    }

    /// ①~④ 순서와 상한 — 첫 표시 → (④ 없이 죽음) → 한 번 더 → (또 죽음) → 보여 주지 않고 닫음. 합계 ≤ 2.
    #[test]
    fn order_and_duplicate_cap_survive_crashes_between_show_and_close() {
        let d = tmpdir("cap");
        put_state(&d, &st("r-1", "ok"));
        // 1회차: ② 기록 → 토스트
        let t1 = take_at(&d, 1000).expect("첫 표시");
        assert_eq!(read_ack(&d).pending_notification, Some(Pending { result_id: "r-1".into(), shown_count: 1 }), "② = 표시 전에 shown_count 1 기록");
        assert_eq!(read_ack(&d).last_notified_result_id, None, "④ 는 아직이다");
        assert_eq!(t1.result_id, "r-1");
        // ③~④ 사이 충돌(done 없음) → 2회차: 한 번 더
        let t2 = take_at(&d, 1001).expect("충돌 뒤 1번 더");
        assert_eq!(t2.body, t1.body);
        assert_eq!(read_ack(&d).pending_notification.unwrap().shown_count, 2);
        // 또 충돌 → 3회차: 보여 주지 않고 ④ 로 닫는다
        assert_eq!(take_at(&d, 1002), None, "합계 2 를 넘지 않는다");
        let a = read_ack(&d);
        assert_eq!(a.last_notified_result_id.as_deref(), Some("r-1"));
        assert_eq!(a.pending_notification, None);
        assert_eq!(take_at(&d, 1003), None, "닫힌 뒤엔 다시 없다");
        let _ = std::fs::remove_dir_all(&d);
    }

    /// 정상 경로 — 표시 → ④ → 다음 기동엔 없음 · 새 결과는 다시 1회.
    #[test]
    fn normal_path_shows_once_then_new_result_shows_again() {
        let d = tmpdir("normal");
        put_state(&d, &st("r-1", "rollback_ok"));
        let t = take_at(&d, 10).expect("표시");
        assert_eq!(t.body, TEXT_ROLLBACK_OK);
        assert!(done_at(&d, &t.result_id));
        assert_eq!(read_ack(&d).pending_notification, None, "④ 가 대기 표지를 지운다");
        assert_eq!(take_at(&d, 11), None);
        put_state(&d, &st("r-2", "installed_revoked"));
        let t = take_at(&d, 12).expect("새 결과 = 새 알림");
        assert_eq!((t.result_id.as_str(), t.body.as_str()), ("r-2", TEXT_INSTALLED_REVOKED));
        assert_eq!(read_ack(&d).pending_notification.unwrap().shown_count, 1, "다른 결과의 대기 횟수를 이어 세지 않는다");
        let _ = std::fs::remove_dir_all(&d);
    }

    /// ★1.1.10 ⑪(master#c6c3784a · 알림 수신 멱등 키 = 경로 A `last_notified_result_id`): 러너가 **같은 result_id** 를 다시
    /// 투입해도(state.json 재기록 · 바이트가 달라도 = release_seq·notes_ko 가 바뀌어도) 표시는 1회 — 닫힌 결과는 id 로만 가른다.
    /// 롤백 실패는 설계상 하루 1회 재안내라 제외(rollback_failed_repeats_once_a_day_only 가 잰다).
    #[test]
    fn same_result_id_delivered_twice_is_shown_once() {
        for kind in ["ok", "rollback_ok", "installed_revoked"] {
            let d = tmpdir(kind);
            put_state(&d, &st("r-dup", kind));
            let mut shown = 0;
            if let Some(t) = take_at(&d, 100) {
                shown += 1;
                assert!(done_at(&d, &t.result_id), "{kind}: ④ 닫기");
            }
            // 같은 id 재투입 — 다른 바이트(release_seq·notes_ko 변경)로 파일을 새로 쓴다.
            put_state(&d, &json!({"last_result": {"result_id": "r-dup", "kind": kind, "release_seq": 8,
                                                   "version": "1.1.10", "notes_ko": "다시 기록"}}));
            for now in [101, 100 + ROLLBACK_FAILED_REPEAT_SECS + 1] {
                if take_at(&d, now).is_some() {
                    shown += 1;
                }
            }
            assert_eq!(shown, 1, "{kind}: 같은 result_id 재투입이 다시 표시됐다");
            assert_eq!(read_ack(&d).last_notified_result_id.as_deref(), Some("r-dup"));
            let _ = std::fs::remove_dir_all(&d);
        }
    }

    /// ② 가 실패하면 ③ 도 없다(잠금은 잡히는데 장부 쓰기만 실패 — 장부 자리에 비지 않은 폴더 · 2판: 아래 읽기 전용 시험은 잠금 단계에서 먼저 끝나
    /// 이 경로를 밟지 않으므로 따로 둔다 · 뮤턴트 M7).
    #[test]
    fn no_show_when_only_the_ledger_write_fails() {
        let d = tmpdir("ackdir");
        put_state(&d, &st("r-1", "ok"));
        std::fs::create_dir_all(d.join(ACK_FILE).join("x")).unwrap();
        assert_eq!(take_at(&d, 5), None, "장부를 못 쓰면(rename 실패) 보여 주지 않는다");
        assert!(d.join(LOCK_FILE).exists(), "잠금 단계는 지났다(이 시험이 쓰기 실패 경로를 밟는다는 증거)");
        let stray: Vec<_> = std::fs::read_dir(&d).unwrap().filter_map(|e| e.ok()).map(|e| e.file_name().to_string_lossy().into_owned()).filter(|n| n.contains(".tmp-")).collect();
        assert!(stray.is_empty(), "실패한 임시 파일은 지운다: {stray:?}");
        let _ = std::fs::remove_dir_all(&d);
    }

    /// ② 가 실패하면 ③ 도 없다 — 기록 없이 보여 주면 상한이 사라진다.
    #[cfg(unix)]
    #[test]
    fn no_show_when_the_pre_show_record_cannot_be_written() {
        use std::os::unix::fs::PermissionsExt;
        let d = tmpdir("ro");
        put_state(&d, &st("r-1", "ok"));
        std::fs::set_permissions(&d, std::fs::Permissions::from_mode(0o555)).unwrap();
        let shown = take_at(&d, 5);
        std::fs::set_permissions(&d, std::fs::Permissions::from_mode(0o755)).unwrap();
        assert_eq!(shown, None, "장부를 못 쓰면 보여 주지 않는다");
        let _ = std::fs::remove_dir_all(&d);
    }

    /// 롤백 실패 — 닫힌 뒤에도 하루 1회만 다시.
    #[test]
    fn rollback_failed_repeats_once_a_day_only() {
        let d = tmpdir("daily");
        put_state(&d, &st("r-9", "rollback_failed"));
        let t = take_at(&d, 100_000).expect("첫 표시");
        assert_eq!((t.toast_id, t.body.as_str()), (TOAST_ID_ROLLBACK_FAILED, TEXT_ROLLBACK_FAILED));
        assert!(done_at(&d, "r-9"));
        assert_eq!(take_at(&d, 100_000 + 3600), None, "1시간 뒤 = 없음");
        assert_eq!(take_at(&d, 100_000 + ROLLBACK_FAILED_REPEAT_SECS - 1), None, "하루 직전 = 없음");
        assert!(take_at(&d, 100_000 + ROLLBACK_FAILED_REPEAT_SECS).is_some(), "하루 = 다시 1회");
        assert_eq!(take_at(&d, 100_000 + ROLLBACK_FAILED_REPEAT_SECS + 60), None, "그날 두 번째 = 없음(표시 전 기록)");
        // 다른 종류는 닫힌 뒤 하루가 지나도 다시 나오지 않는다
        put_state(&d, &st("r-10", "ok"));
        take_at(&d, 1).unwrap();
        done_at(&d, "r-10");
        assert_eq!(take_at(&d, 10_000_000), None);
        let _ = std::fs::remove_dir_all(&d);
    }

    /// 판정 표(순수) — 형식이 틀리면 아무것도 보여 주지 않는다.
    #[test]
    fn plan_refuses_malformed_or_unknown_results() {
        let a = Ack::default();
        assert_eq!(plan(&json!({}), &a, 0), Plan::Nothing);
        assert_eq!(plan(&json!({"last_result": null}), &a, 0), Plan::Nothing);
        assert_eq!(plan(&json!({"last_result": "x"}), &a, 0), Plan::Nothing);
        assert_eq!(plan(&st("r-1", "weird"), &a, 0), Plan::Nothing, "모르는 종류 = 무음");
        assert_eq!(plan(&st("", "ok"), &a, 0), Plan::Nothing);
        assert_eq!(plan(&st("a b", "ok"), &a, 0), Plan::Nothing, "공백 든 id");
        assert_eq!(plan(&st(&"x".repeat(65), "ok"), &a, 0), Plan::Nothing, "65자");
        assert!(matches!(plan(&st(&"x".repeat(64), "ok"), &a, 0), Plan::Show { .. }), "64자는 된다");
        assert!(!done_at(&std::env::temp_dir(), "a/b"), "④ 도 형식이 틀린 id 는 쓰지 않는다");
    }

    /// 필수 칸 `release_seq` — 정수 ≥1 만 결과 기록으로 믿는다(codex 1R ⑤ · 반례 = 누락·0·음수·문자열·소수).
    #[test]
    fn release_seq_must_be_a_positive_integer() {
        let mk = |seq: Option<Value>| {
            let mut last = json!({"result_id": "r-1", "kind": "ok"});
            if let Some(v) = seq {
                last["release_seq"] = v;
            }
            json!({"last_result": last})
        };
        let a = Ack::default();
        for (why, seq) in [("누락", None), ("0", Some(json!(0))), ("음수", Some(json!(-1))), ("문자열", Some(json!("7"))), ("소수", Some(json!(1.5))), ("null", Some(Value::Null))] {
            assert_eq!(plan(&mk(seq), &a, 0), Plan::Nothing, "release_seq {why} = 알림 0");
        }
        assert!(matches!(plan(&mk(Some(json!(1))), &a, 0), Plan::Show { .. }), "1 = 통과");
        assert!(matches!(plan(&mk(Some(json!(u64::MAX))), &a, 0), Plan::Show { .. }), "큰 정수 = 통과");
    }

    /// 탐침 폴더 — `.cs-probe` 를 놓아 임계 구역 탐침을 켠다.
    fn probe_dir(tag: &str, id: &str, kind: &str) -> std::path::PathBuf {
        let d = tmpdir(tag);
        put_state(&d, &st(id, kind));
        std::fs::write(d.join(cs_probe::CFG), b"").unwrap();
        d
    }
    fn ledger(d: &Path) -> Ack {
        serde_json::from_slice(&std::fs::read(d.join(ACK_FILE)).unwrap()).expect("장부가 유효 JSON 이어야 한다(서로 truncate 금지)")
    }
    fn assert_no_overlap_no_temp(d: &Path, what: &str) {
        assert!(!d.join(cs_probe::OVERLAP).exists(), "{what}: 두 참가자가 장부 읽기→쓰기 구간에 함께 섰다(잠금이 뚫림)");
        let stray: Vec<_> = std::fs::read_dir(d).unwrap().filter_map(|e| e.ok()).map(|e| e.file_name().to_string_lossy().into_owned()).filter(|n| n.contains(".tmp-")).collect();
        assert!(stray.is_empty(), "{what}: 임시 파일 잔존 {stray:?}");
    }

    /// ★(3판 · codex 2R MAJOR① → 4판 신호화) 같은 프로세스 두 스레드 — A 가 장부를 **읽고 쓰기 전**(탐침)에 서 있는 동안
    /// ⑴ 프로세스 뮤텍스와 `app-notify.lock` 파일 잠금이 **둘 다** 잡혀 있는지 비차단 시도로 잰다(M11 · M11a · M11b 적색 — 시간 가정 0)
    /// ⑵ B 가 들어오려 한다 → A 를 놓으면 B 는 A 의 기록을 읽는다 → 표시 정확히 2 · 장부 2 · 세 번째 기동 = 닫힘(0).
    #[test]
    fn threads_take_one_at_a_time_inside_the_ledger_section() {
        let d = probe_dir("cs-threads-tt", "r-tt", "ok");
        let a = {
            let d = d.clone();
            std::thread::spawn(move || take_at(&d, 1).is_some() as usize)
        };
        cs_probe::wait_someone_inside(&d);
        let (mutex, file) = (cs_probe::mutex_is_held(), cs_probe::lock_file_is_held(&d));
        let b = {
            let d = d.clone();
            std::thread::spawn(move || take_at(&d, 1).is_some() as usize)
        };
        cs_probe::go(&d);
        let shown = a.join().unwrap() + b.join().unwrap();
        assert!(mutex, "임계 구역 안인데 프로세스 뮤텍스가 잡혀 있지 않다");
        assert!(file, "임계 구역 안인데 app-notify.lock 파일 잠금이 잡혀 있지 않다");
        assert_no_overlap_no_temp(&d, "스레드 take×2");
        assert_eq!(shown, 2, "두 기동의 표시 합계는 정확히 2");
        assert_eq!(ledger(&d).pending_notification.map(|p| p.shown_count), Some(2), "장부 = 실제 표시 수(잃어버린 갱신 0)");
        let _ = std::fs::remove_file(d.join(cs_probe::CFG));
        assert!(take_at(&d, 2).is_none(), "상한 2 를 채운 뒤의 기동은 보여 주지 않는다");
        assert_eq!(ledger(&d).last_notified_result_id.as_deref(), Some("r-tt"));
        let _ = std::fs::remove_dir_all(&d);
    }

    /// ★(3판 · codex 2R MAJOR① ⓒ → 4판 신호화) take 가 장부를 읽고 쓰기 전에 서 있는 동안 done(④ 닫기) 이 들어오려 한다.
    /// 잠금이 있으면 순서 = take(표시 1 · 대기 1) → done(닫힘) → 뒤 기동 0 ⇒ 표시 합계 **정확히 1**(0 이면 적색 · 2 면 적색).
    #[test]
    fn take_then_done_inside_the_section_shows_exactly_once() {
        let d = probe_dir("cs-threads-td", "r-td", "installed_revoked");
        let t = {
            let d = d.clone();
            std::thread::spawn(move || take_at(&d, 1).is_some() as usize)
        };
        cs_probe::wait_someone_inside(&d);
        let (mutex, file) = (cs_probe::mutex_is_held(), cs_probe::lock_file_is_held(&d));
        let c = {
            let d = d.clone();
            std::thread::spawn(move || done_at(&d, "r-td"))
        };
        cs_probe::go(&d);
        let first = t.join().unwrap();
        assert!(c.join().unwrap(), "닫기 기록 성공");
        assert!(mutex && file, "take 가 임계 구역 안인데 잠금이 비었다(뮤텍스 {mutex} · 파일 {file})");
        assert_no_overlap_no_temp(&d, "스레드 take+done");
        let _ = std::fs::remove_file(d.join(cs_probe::CFG));
        let later = (0..3).filter(|_| take_at(&d, 2).is_some()).count();
        assert_eq!(first + later, 1, "표시 합계는 정확히 1(take {first} + 뒤 기동 {later})");
        let a = ledger(&d);
        assert_eq!(a.last_notified_result_id.as_deref(), Some("r-td"));
        assert!(a.pending_notification.is_none(), "닫힌 결과의 대기 표지가 되살아나면 안 된다: {:?}", a.pending_notification);
        let _ = std::fs::remove_dir_all(&d);
    }

    /// 자식 프로세스 진입점 — 부모 시험이 `U4_CS_CHILD_DIR` 을 주고 이 시험 하나만 다시 부른다. 환경변수가 없으면(보통 실행) 아무것도 안 한다.
    #[test]
    fn cross_process_child_entry() {
        let Some(dir) = std::env::var_os("U4_CS_CHILD_DIR").map(std::path::PathBuf::from) else {
            return;
        };
        let shown = take_at(&dir, 1).is_some();
        std::fs::write(dir.join("child-shown"), if shown { "1" } else { "0" }).unwrap();
    }

    /// ★(3판 · codex 2R MAJOR① ⓐ → 4판 신호화) 두 **프로세스**(앱 창 둘) — 프로세스 뮤텍스는 프로세스 경계를 못 넘으므로 `app-notify.lock` 만이 막는다.
    /// 자식(이 시험 바이너리를 `current_exe()` 로 다시 띄움)이 장부를 읽고 쓰기 전에 서 있는 동안(신호 = 자식의 `.cs-in-` 파일)
    /// 부모가 **다른 프로세스에서** 파일 잠금을 비차단 시도한다 → 잡혀 있어야 한다(M11b 적색 · 시간 가정 0). 이어 부모도 들어오려 하고 자식을 놓는다
    /// → 표시 정확히 2 · 장부 2 · 세 번째 = 닫힘.
    #[test]
    fn two_processes_take_one_at_a_time_through_the_lock_file() {
        let d = probe_dir("cs-procs", "r-xp", "ok");
        let mut child = std::process::Command::new(std::env::current_exe().unwrap())
            .args(["--exact", "updnotice::tests::cross_process_child_entry", "--test-threads=1", "--quiet"])
            .env("U4_CS_CHILD_DIR", &d)
            .stdout(std::process::Stdio::null())
            .spawn()
            .expect("시험 바이너리 재호출");
        cs_probe::wait_someone_inside(&d);
        let held_across_processes = cs_probe::lock_file_is_held(&d);
        let parent = {
            let d = d.clone();
            std::thread::spawn(move || take_at(&d, 1).is_some() as usize)
        };
        cs_probe::go(&d);
        let ok = child.wait().unwrap().success();
        let parent = parent.join().unwrap();
        assert!(held_across_processes, "자식이 임계 구역 안인데 다른 프로세스에서 app-notify.lock 을 잡을 수 있었다(파일 잠금 없음)");
        assert!(ok, "자식 프로세스 시험 실패");
        let child_shown: usize = std::fs::read_to_string(d.join("child-shown")).expect("자식이 결과를 남겨야 한다").trim().parse().unwrap();
        assert_eq!(child_shown, 1, "먼저 들어간 자식이 첫 표시");
        assert!(!d.join(cs_probe::OVERLAP).exists(), "두 프로세스가 장부 읽기→쓰기 구간에 함께 섰다(파일 잠금이 뚫림)");
        assert_eq!(child_shown + parent, 2, "두 앱 창의 표시 합계는 정확히 2");
        assert_eq!(ledger(&d).pending_notification.map(|p| p.shown_count), Some(2), "장부 = 실제 표시 수(잃어버린 갱신 0)");
        let _ = std::fs::remove_file(d.join(cs_probe::CFG));
        assert!(take_at(&d, 2).is_none(), "상한 2 를 채운 뒤의 기동은 보여 주지 않는다");
        let _ = std::fs::remove_dir_all(&d);
    }

    /// 판 표시 — 숫자 마디만 · 아니면 괄호째 뺀다.
    #[test]
    fn version_is_shown_only_when_it_looks_like_a_version() {
        let mk = |v: Value| json!({"last_result": {"result_id": "r", "kind": "ok", "release_seq": 1, "version": v}});
        let body = |v: Value| match plan(&mk(v), &Ack::default(), 0) {
            Plan::Show { toast, .. } => toast.body,
            p => panic!("{p:?}"),
        };
        assert_eq!(body(json!("1.1.9")), "자비스가 새 판(1.1.9)으로 바뀌었어요. 하던 일은 그대로 이어집니다.");
        for bad in [json!("1.1.9-rc1"), json!("v1.1.9"), json!(""), json!("1..9"), json!("1.2.3.4.5"), json!(119), json!("<b>1</b>")] {
            assert_eq!(body(bad.clone()), TEXT_OK, "{bad}");
        }
    }

    /// `notes_ko` — 금지 글자(제어·줄 나눔·방향 바꿈)·금지 어휘가 하나라도 있으면 통째로 거부 · 80자 상한 · 정상이면 **같은 줄**에(설계 §6-1 「알림 1줄」).
    #[test]
    fn notes_with_control_chars_are_refused_whole() {
        let mk = |n: &str| json!({"last_result": {"result_id": "r", "kind": "ok", "release_seq": 1, "notes_ko": n}});
        let body = |n: &str| match plan(&mk(n), &Ack::default(), 0) {
            Plan::Show { toast, .. } => toast.body,
            p => panic!("{p:?}"),
        };
        assert_eq!(body("  창 정렬이 빨라졌어요  "), format!("{TEXT_OK} {NOTES_LEAD}창 정렬이 빨라졌어요"));
        assert!(!body("창 정렬이 빨라졌어요").contains('\n'), "알림은 한 줄 — 노트를 붙여도 줄바꿈 0");
        for bad_word in ["오류 수정", "실패 줄임", "위험 제거", "손상 복구", "경고 정리"] {
            assert_eq!(body(bad_word), TEXT_OK, "금지 어휘 = 통째 거부: {bad_word}");
        }
        for bad in ["a\nb", "a\rb", "a\u{0}b", "a\u{1b}[31mb", "a\u{7f}b", "a\u{85}b", "a\u{2028}b", "a\u{2029}b", "a\u{202E}b", "a\u{2066}b", "a\u{200F}b", "a\u{061C}b", "\t", "   "] {
            assert_eq!(body(bad), TEXT_OK, "거부돼야 한다: {bad:?}");
        }
        assert_eq!(NOTES_MAX_CHARS, 80, "설계 §6-1 notes_ko ≤80자");
        assert_eq!(NOTES_MAX_CHARS, cys::update::feed::NOTES_MAX_CHARS, "발행·검증 쪽 상한과 같은 값");
        assert_eq!(body(&"가".repeat(80)).chars().count(), TEXT_OK.chars().count() + 1 + NOTES_LEAD.chars().count() + 80, "80자 = 통과");
        assert_eq!(body(&"가".repeat(81)), TEXT_OK, "81자 = 거부(codex 1R ⑥ 반례)");
        // 노트는 성공 알림에만 붙는다
        let rb = json!({"last_result": {"result_id": "r", "kind": "rollback_ok", "release_seq": 1, "notes_ko": "x"}});
        assert!(matches!(plan(&rb, &Ack::default(), 0), Plan::Show { toast, .. } if toast.body == TEXT_ROLLBACK_OK));
    }

    /// 문구 표 — 위협·공포 낱말 0 · 한 문장(줄바꿈 0) · 설계 §3-12 표와 글자 그대로.
    #[test]
    fn notice_texts_are_plain_and_match_the_design_table() {
        let all = [
            TEXT_OK_WITH_VERSION, TEXT_OK, TEXT_ROLLBACK_OK, TEXT_ROLLBACK_FAILED, TEXT_INSTALLED_REVOKED, TEXT_SEATS_BLOCKED,
            TITLE_OK, TITLE_ROLLBACK_OK, TITLE_ROLLBACK_FAILED, TITLE_INSTALLED_REVOKED, NOTES_LEAD,
        ];
        for t in all {
            for w in BANNED_WORDS {
                assert!(!t.contains(w), "사용자 문구에 「{w}」: {t}");
            }
            assert!(!t.contains('\n'), "한 줄이어야 한다: {t}");
            for w in ["업데이트", "Update", "update"] {
                assert!(!t.contains(w), "알림 문구에 「{w}」 — 1.1.8 앱에는 업데이트 단추·문구가 남지 않는다: {t}");
            }
        }
        assert_eq!(TEXT_OK_WITH_VERSION.replace("{v}", "1.1.9"), "자비스가 새 판(1.1.9)으로 바뀌었어요. 하던 일은 그대로 이어집니다.");
    }

    /// 📌18 — 사유가 정확히 journal_unrecoverable 일 때만 · 판독 불가 = 무음(추측 금지).
    #[test]
    fn seats_blocked_notice_only_for_unrecoverable_journal() {
        assert_eq!(seats_blocked_text(&json!({"seats_blocked": {"reason": "journal_unrecoverable"}})), Some(TEXT_SEATS_BLOCKED));
        for v in [json!({}), json!({"seats_blocked": null}), json!({"seats_blocked": {"reason": "stop_seats"}}), json!({"seats_blocked": {}}), json!({"seats_blocked": "journal_unrecoverable"})] {
            assert_eq!(seats_blocked_text(&v), None, "{v}");
        }
        let d = tmpdir("seats");
        assert_eq!(seats_blocked_at(&d), None, "state.json 없음");
        std::fs::write(d.join(STATE_FILE), b"{not json").unwrap();
        assert_eq!(seats_blocked_at(&d), None, "판독 불가");
        assert_eq!(take_at(&d, 0), None, "판독 불가면 토스트도 없다");
        put_state(&d, &json!({"seats_blocked": {"reason": "journal_unrecoverable"}}));
        assert_eq!(seats_blocked_at(&d), Some(TEXT_SEATS_BLOCKED));
        put_state(&d, &json!({}));
        assert_eq!(seats_blocked_at(&d), None, "상태가 풀리면 사라진다");
        let _ = std::fs::remove_dir_all(&d);
    }

    /// 앱은 state.json 을 쓰지 않는다 — 바이트 그대로 · 장부는 따로 · 임시 파일 잔존 0.
    #[test]
    fn app_never_writes_state_json_and_leaves_no_temp_files() {
        let d = tmpdir("ro-state");
        let raw = br#"{"last_result":{"result_id":"r-1","kind":"ok","release_seq":3},"failures":{"k":{"class":"transient","count":1,"next_at":9}}}"#;
        std::fs::write(d.join(STATE_FILE), raw).unwrap();
        let t = take_at(&d, 1).unwrap();
        done_at(&d, &t.result_id);
        assert_eq!(std::fs::read(d.join(STATE_FILE)).unwrap(), raw.to_vec(), "state.json 은 바이트 그대로");
        let names: Vec<String> = std::fs::read_dir(&d).unwrap().map(|e| e.unwrap().file_name().to_string_lossy().into_owned()).collect();
        let mut names = names;
        names.sort();
        assert_eq!(names, vec![ACK_FILE.to_string(), LOCK_FILE.to_string(), STATE_FILE.to_string()], "임시 파일이 남지 않는다(장부·잠금·상태 셋뿐)");
        // 깨진 장부는 빈 장부로 읽고 다음 쓰기가 통째로 바꾼다
        std::fs::write(d.join(ACK_FILE), b"garbage").unwrap();
        assert_eq!(read_ack(&d), Ack::default());
        let _ = std::fs::remove_dir_all(&d);
    }

    /// 장부 칸 이름 = 설계 그대로(병합 때 U2 와 맞추는 접점).
    #[test]
    fn ack_field_names_are_the_design_names() {
        let a = Ack {
            pending_notification: Some(Pending { result_id: "r".into(), shown_count: 1 }),
            last_notified_result_id: Some("q".into()),
            rollback_failed_last_shown_at: Some(5),
        };
        assert_eq!(
            serde_json::to_value(&a).unwrap(),
            json!({"pending_notification": {"result_id": "r", "shown_count": 1}, "last_notified_result_id": "q", "rollback_failed_last_shown_at": 5})
        );
    }
}
