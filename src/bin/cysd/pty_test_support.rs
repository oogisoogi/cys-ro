//! ★v116-flake-pty ⑵ — **시험 전용**: PTY 고갈(openpty ENXIO)을 제품 결함과 구별한다.
//!
//! 왜: 병렬 게이트가 겹치면 기기 전체의 PTY(`kern.tty.ptmx_max` · 이 기기 511)가 순간 바닥나
//! `openpty failed: … Device not configured`(os error 6)로 cysd 시험이 붉어졌다(2026-09-24 ·
//! X-7 7회째 7건 · 정본 게이트 D07c 2건 — 둘 다 다른 워커 cargo 시험 동시 가동 중). 그 적색은
//! 「제품이 좌석을 못 만든다」와 문구가 같아 결함과 구별되지 않았다.
//!
//! 무엇을 하나(좁게):
//!   · **ENXIO 일 때만** 상한 있는 재시도(백오프 · 매 재시도 stderr 1줄). 다른 에러는 한 번도
//!     재시도하지 않고 그대로 돌려준다 — 진짜 결함은 종전과 똑같이 붉다.
//!   · 상한을 넘기면 「PTY 고갈(…)」 문구로 실패한다. 단 **누가 PTY 를 쥐고 있는지**로 문구가 갈린다
//!     (적대 1R #1): 다른 프로세스가 상한의 1/4 이상을 쥐면 「환경」, 아니면 「자기 프로세스 n개 보유 —
//!     시험 점유 또는 제품 PTY 누수 의심 · 제품 결함 배제 불가」. 격리 러너(다른 PTY 보유자 없음)에서
//!     제품이 PTY 를 새면 후자로 드러난다 — 「제품 결함 아님」을 증거 없이 단정하지 않는다.
//!   · 재시도 줄은 libtest 출력 캡처를 우회해 stderr 로 직접 쓴다 — 재시도 뒤 통과한 시험도 흔적이 남는다.
//!
//! 범위(정직 고지): 감싼 곳 = 도우미 5종(make_surface · create_surface_rpc · create_surface_rpc_idem ·
//! create_rpc · watch_wake seat) + usage.rs 3곳 = 09-24 관측 ENXIO 실패 9건의 경로 전부. 그 밖 직접
//! `create_surface` 호출(governance·state·channels·boot_supervisor 시험 등)은 감싸지 않았다 — 거기서 난
//! ENXIO 는 종전처럼 원문(`openpty failed … Device not configured`) 적색이다(편입 충돌 회피 · 후속 후보).
//! 부수효과(정직 고지): 재시도 뒤 성공하면 실패한 시도가 surface id 1개씩을 소비하고, RPC 경로는
//! `surface.create_failed` 이벤트를 1건씩 남긴다 — id·이벤트 수를 단언하는 시험은 그때 다른 문구로 붉을 수
//! 있다(재시도 줄이 stderr 에 남으므로 원인 추적 가능).
//!
//! 제품 `state.rs` openpty 경로는 무접촉이다(이 모듈은 `#[cfg(test)]` 로만 컴파일된다).

use std::time::Duration;

/// 재시도 대기(합계 15초). 관측된 고갈 구간은 수십 초 단위였다(`pty-17cc0a68.log` · 300개 이상
/// 약 40초) — 짧은 순간 고갈은 흡수하고, 긴 고갈은 오래 붙들지 않고 환경 문구로 끝낸다.
pub(crate) const PTY_RETRY_BACKOFF: [Duration; 4] = [
    Duration::from_secs(1),
    Duration::from_secs(2),
    Duration::from_secs(4),
    Duration::from_secs(8),
];

/// `openpty` 가 ENXIO(os error 6 · Device not configured)로 실패했는가. 다른 errno 는 아니다.
pub(crate) fn is_pty_exhaustion(err: &str) -> bool {
    // 정확 일치만: `os error 6` 부분 문자열은 `os error 60`(ETIMEDOUT)에도 걸리므로 괄호까지 본다.
    //   실제 모양 = `openpty failed: failed to openpty: Os { code: 6, … }`(state.rs ∘ portable-pty `{:?}`).
    err.contains("openpty failed")
        && (err.contains("Os { code: 6,") || err.contains("(os error 6)"))
}

/// PTY 실측(최선 노력 · macOS): 기기 전체 열린 PTY · 상한 · **이 프로세스가 쥔 PTY**.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) struct PtyCensus {
    pub total: Option<usize>,
    pub max: Option<usize>,
    pub own: Option<usize>,
}

pub(crate) fn pty_census() -> PtyCensus {
    let total = std::fs::read_dir("/dev").ok().map(|it| {
        it.filter_map(|e| e.ok())
            .filter(|e| {
                let n = e.file_name();
                let n = n.to_string_lossy();
                n.len() > 4 && n.starts_with("ttys") && n[4..].chars().all(|c| c.is_ascii_digit())
            })
            .count()
    });
    let max = std::process::Command::new("sysctl")
        .args(["-n", "kern.tty.ptmx_max"])
        .output()
        .ok()
        .and_then(|o| String::from_utf8(o.stdout).ok())
        .and_then(|s| s.trim().parse().ok());
    // 이 프로세스의 PTY fd(마스터 /dev/ptmx · 슬레이브 /dev/ttysN) — lsof 한 번(재시도·실패 경로에서만 부른다).
    let own = std::process::Command::new("lsof")
        .args(["-a", "-p", &std::process::id().to_string(), "-Fn"])
        .output()
        .ok()
        .and_then(|o| String::from_utf8(o.stdout).ok())
        .map(|s| {
            s.lines()
                .filter(|l| l.starts_with("n/dev/ptmx") || l.starts_with("n/dev/ttys"))
                .count()
        });
    PtyCensus { total, max, own }
}

fn q(v: Option<usize>) -> String {
    v.map(|n| n.to_string()).unwrap_or_else(|| "?".into())
}

/// 상한을 넘긴 고갈의 실패 문구(순수) — 결함 실패와 문구가 갈리고, **누가 쥐었는지**로 한 번 더 갈린다.
/// 다른 프로세스 보유(= 전체 − 자기)가 상한의 1/4 이상일 때만 「환경」이라 부른다.
pub(crate) fn exhaustion_wording(what: &str, attempts: usize, err: &str, c: PtyCensus) -> String {
    let others = match (c.total, c.own) {
        (Some(t), Some(o)) => Some(t.saturating_sub(o)),
        _ => None,
    };
    let env = matches!((others, c.max), (Some(k), Some(m)) if k * 4 >= m);
    let head = if env {
        format!("PTY 고갈(환경) — 다른 프로세스가 {}개 보유 · 제품 결함 아님", q(others))
    } else {
        format!(
            "PTY 고갈(자기 프로세스 {}개 보유 — 시험 점유 또는 제품 PTY 누수 의심 · 제품 결함 배제 불가)",
            q(c.own)
        )
    };
    format!(
        "{head} · {what} · 시도 {attempts}회 · 열린 PTY {}/{} · 이 프로세스 {} · 원문: {err}",
        q(c.total),
        q(c.max),
        q(c.own)
    )
}

pub(crate) fn exhaustion_message(what: &str, attempts: usize, err: &str) -> String {
    exhaustion_wording(what, attempts, err, pty_census())
}

/// libtest 는 `eprintln!` 을 **통과한 시험에서 삼킨다** — 재시도 흔적은 fd 2 에 직접 쓴다(적대 1R #1).
fn log_uncaptured(line: &str) {
    use std::io::Write;
    let _ = std::io::stderr().write_all(format!("{line}\n").as_bytes());
}

/// 순수 재시도 루프(대기 함수 주입 — 단위 시험이 실제로 자지 않는다).
/// `f` 가 ENXIO 로 실패할 때만 `backoff` 길이만큼 다시 부른다. 반환 `(결과, 시도 수)`.
pub(crate) fn retry_with<T>(
    what: &str,
    backoff: &[Duration],
    mut sleep: impl FnMut(Duration),
    mut f: impl FnMut() -> Result<T, String>,
) -> (Result<T, String>, usize) {
    let mut attempts = 0usize;
    loop {
        attempts += 1;
        match f() {
            Ok(v) => return (Ok(v), attempts),
            Err(e) if !is_pty_exhaustion(&e) => return (Err(e), attempts),
            Err(e) => {
                let Some(d) = backoff.get(attempts - 1) else {
                    return (Err(exhaustion_message(what, attempts, &e)), attempts);
                };
                let c = pty_census();
                log_uncaptured(&format!(
                    "[pty-retry] {what}: openpty ENXIO — {}ms 뒤 재시도 {attempts}/{} · 열린 PTY {}/{} · 이 프로세스 {}",
                    d.as_millis(),
                    backoff.len(),
                    q(c.total),
                    q(c.max),
                    q(c.own)
                ));
                sleep(*d);
            }
        }
    }
}

/// 시험 도우미용 — `Daemon::create_surface` 류 호출을 감싼다.
pub(crate) fn retry_on_pty_exhaustion<T>(what: &str, f: impl FnMut() -> Result<T, String>) -> Result<T, String> {
    retry_with(what, &PTY_RETRY_BACKOFF, std::thread::sleep, f).0
}

/// 시험 도우미용 — `surface.create` RPC 응답(Value)을 감싼다. ENXIO 응답일 때만 재시도하고,
/// 상한을 넘기면 환경 문구로 panic 한다(그 응답을 호출자에게 넘기면 결함 적색과 문구가 같아진다).
/// ENXIO 가 아닌 응답(성공·거부·다른 실패)은 그대로 돌려준다.
pub(crate) fn rpc_retry_on_pty_exhaustion(
    what: &str,
    mut f: impl FnMut() -> serde_json::Value,
) -> serde_json::Value {
    let mut last = serde_json::Value::Null;
    let (r, _) = retry_with(what, &PTY_RETRY_BACKOFF, std::thread::sleep, || {
        let resp = f();
        let msg = resp.pointer("/error/message").and_then(|v| v.as_str()).unwrap_or("").to_string();
        last = resp;
        if is_pty_exhaustion(&msg) {
            Err(msg)
        } else {
            Ok(())
        }
    });
    if let Err(e) = r {
        panic!("{e}");
    }
    last
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::cell::Cell;

    /// ★실제 오류 모양으로 주입(master 결정 ① · 문자열 흉내 금지): 제품 경로는
    /// `state.rs` `format!("openpty failed: {e}")` ∘ 벤더 portable-pty `bail!("failed to openpty: {:?}",
    /// io::Error::last_os_error())` 이다 — 같은 두 단을 실제 `io::Error`(raw errno)로 거친다.
    fn openpty_err(errno: i32) -> String {
        // 메시지 전용 anyhow 오류의 Display 는 그 메시지 자체다(이 크레이트는 anyhow 비의존 — 신규 의존 없이 재현).
        let bail_msg = format!("failed to openpty: {:?}", std::io::Error::from_raw_os_error(errno));
        format!("openpty failed: {bail_msg}")
    }

    #[test]
    #[cfg(target_os = "macos")] // 오류 문구(strerror)가 OS 마다 다르다 — 관측 원문은 macOS(적대 1R #6)
    fn real_shape_matches_the_observed_failure_text() {
        // 09-24 X-7·D07c 로그 원문과 한 글자도 다르지 않아야 주입이 실물이다.
        assert_eq!(
            openpty_err(libc::ENXIO),
            "openpty failed: failed to openpty: Os { code: 6, kind: Uncategorized, message: \"Device not configured\" }"
        );
    }

    #[test]
    fn classifier_accepts_only_openpty_enxio() {
        assert!(is_pty_exhaustion(&openpty_err(libc::ENXIO)));
        // Display 모양(`… (os error 6)`)도 같은 errno 다.
        assert!(is_pty_exhaustion(&format!(
            "openpty failed: {}",
            std::io::Error::from_raw_os_error(libc::ENXIO)
        )));
        // 다른 errno 는 고갈이 아니다 — 60(ETIMEDOUT)은 `os error 6` 부분 문자열 함정의 검체.
        for errno in [libc::EACCES, libc::EMFILE, libc::ENFILE, libc::ENOENT, libc::EAGAIN, libc::ETIMEDOUT] {
            assert!(!is_pty_exhaustion(&openpty_err(errno)), "errno {errno} 를 PTY 고갈로 오분류");
            assert!(!is_pty_exhaustion(&format!(
                "openpty failed: {}",
                std::io::Error::from_raw_os_error(errno)
            )), "errno {errno}(Display) 오분류");
        }
        // openpty 가 아닌 곳의 ENXIO 는 이 모듈 관할이 아니다.
        assert!(!is_pty_exhaustion(&format!("spawn failed: {:?}", std::io::Error::from_raw_os_error(libc::ENXIO))));
        assert!(!is_pty_exhaustion(""));
    }

    /// ENXIO 두 번 뒤 성공 → 성공 · 시도 3 · 대기 2번(1s, 2s).
    #[test]
    fn transient_exhaustion_is_retried_then_succeeds() {
        let n = Cell::new(0);
        let slept = std::cell::RefCell::new(Vec::new());
        let (r, attempts) = retry_with("t", &PTY_RETRY_BACKOFF, |d| slept.borrow_mut().push(d), || {
            n.set(n.get() + 1);
            if n.get() <= 2 { Err(openpty_err(libc::ENXIO)) } else { Ok(7) }
        });
        assert_eq!(r, Ok(7));
        assert_eq!(attempts, 3);
        assert_eq!(*slept.borrow(), vec![Duration::from_secs(1), Duration::from_secs(2)]);
    }

    /// ★은폐 방지(master 결정 ②): ENXIO 가 아닌 오류(EACCES·EMFILE 등)는 **재시도 없이 즉시** 원문 그대로
    /// 실패한다. 「모든 오류 재시도」 뮤턴트는 attempts==1 · 대기 0 에서 죽는다.
    #[test]
    fn non_exhaustion_error_is_never_retried_and_passes_through_verbatim() {
        let mut cases: Vec<String> = [libc::EACCES, libc::EMFILE, libc::ENFILE, libc::ETIMEDOUT]
            .iter()
            .map(|&e| openpty_err(e))
            .collect();
        cases.push("role conflict".into());
        for e in cases {
            let n = Cell::new(0);
            let (r, attempts) = retry_with("t", &PTY_RETRY_BACKOFF, |_| panic!("대기하면 안 된다: {e}"), || {
                n.set(n.get() + 1);
                Err::<(), _>(e.clone())
            });
            assert_eq!(attempts, 1, "결함 에러를 재시도했다: {e}");
            assert_eq!(r, Err(e.clone()), "결함 에러 문구가 바뀌었다");
        }
    }

    /// ★상한(master 결정 ③): 재시도 총량(1+2+4+8초)이 끝나면 반드시 실패로 끝난다. 대기는 주입(실제로
    /// 자지 않음)이라 「무한 재시도」 뮤턴트는 50회째 호출에서 즉시 죽는다(시험 제한시간 무관).
    #[test]
    fn persistent_exhaustion_stops_at_cap_with_environment_wording() {
        let n = Cell::new(0);
        let total = Cell::new(Duration::ZERO);
        let (r, attempts) = retry_with("seat(master)", &PTY_RETRY_BACKOFF, |d| total.set(total.get() + d), || {
            n.set(n.get() + 1);
            assert!(n.get() <= 50, "재시도 상한이 없다(50회 초과)");
            Err::<(), _>(openpty_err(libc::ENXIO))
        });
        assert_eq!(attempts, PTY_RETRY_BACKOFF.len() + 1);
        assert_eq!(total.get(), Duration::from_secs(15), "재시도 총량이 1+2+4+8초가 아니다");
        let e = r.unwrap_err();
        assert!(e.starts_with("PTY 고갈("), "{e}");
        assert!(e.contains(" · seat(master) · 시도 5회 · 열린 PTY "), "{e}");
        assert!(e.contains(&openpty_err(libc::ENXIO)), "원문이 사라졌다: {e}");
    }

    /// ★적대 1R #1: 「환경」은 다른 프로세스가 쥔 증거가 있을 때만. 자기 프로세스가 대부분을 쥐면(격리 러너의
    /// 제품 PTY 누수 모양) 「제품 결함 배제 불가」로 적는다. 판정 모를 때도 「환경」이라 단정하지 않는다.
    #[test]
    fn wording_says_environment_only_when_other_processes_hold_ptys() {
        let e = openpty_err(libc::ENXIO);
        let w = |total, own| exhaustion_wording("t", 5, &e, PtyCensus { total, max: Some(511), own });
        // 다른 워커 병렬 시험이 300개 · 나는 200개 → 환경
        let env = w(Some(511), Some(200));
        assert!(env.starts_with("PTY 고갈(환경) — 다른 프로세스가 311개 보유 · 제품 결함 아님"), "{env}");
        // 격리 러너: 나 혼자 500개 → 누수 의심(환경 아님)
        let own = w(Some(511), Some(500));
        assert!(own.starts_with("PTY 고갈(자기 프로세스 500개 보유 — "), "{own}");
        assert!(own.contains("제품 결함 배제 불가") && !own.contains("제품 결함 아님"), "{own}");
        // 경계: 다른 프로세스 127(< 511/4) → 환경 아님 · 128 → 환경
        assert!(!w(Some(511), Some(384)).contains("(환경)"));
        assert!(w(Some(511), Some(383)).contains("(환경)"));
        // 실측 불가(lsof 실패 등) → 환경이라 단정하지 않는다
        let unk = w(Some(511), None);
        assert!(!unk.contains("(환경)") && unk.contains("이 프로세스 ?"), "{unk}");
    }

    #[test]
    fn rpc_wrapper_passes_non_exhaustion_responses_through() {
        for msg in ["not logged in".to_string(), openpty_err(libc::EMFILE)] {
            let resp = serde_json::json!({"ok": false, "error": {"code": "spawn_failed", "message": msg}});
            let n = Cell::new(0);
            let out = rpc_retry_on_pty_exhaustion("rpc", || {
                n.set(n.get() + 1);
                resp.clone()
            });
            assert_eq!(out, resp);
            assert_eq!(n.get(), 1, "ENXIO 아닌 응답을 재시도했다");
        }
    }

    /// ★적대 1R #1(자동 판정): 재시도 줄은 libtest 기본 캡처를 **뚫고** 나와야 한다 — 재시도 뒤 통과한
    /// 시험도 흔적을 남겨야 흡수된 PTY 압박이 보인다. 이 시험 바이너리를 기본 캡처로 한 시험만 재실행해
    /// 그 stderr 에 `[pty-retry]` 줄이 있는지 본다(`eprintln!` 로 되돌리면 캡처돼 사라진다 = 적색).
    #[test]
    fn retry_line_survives_libtest_output_capture() {
        let exe = std::env::current_exe().expect("현재 시험 바이너리");
        let out = std::process::Command::new(exe)
            .args(["--exact", "pty_test_support::tests::transient_exhaustion_is_retried_then_succeeds"])
            .output()
            .expect("시험 바이너리 재실행");
        let err = String::from_utf8_lossy(&out.stderr);
        let so = String::from_utf8_lossy(&out.stdout);
        assert!(out.status.success(), "재실행 시험 실패: {so}{err}");
        assert!(so.contains("1 passed"), "대상 시험이 돌지 않았다: {so}");
        assert_eq!(err.matches("[pty-retry] t: openpty ENXIO").count(), 2, "재시도 줄이 캡처에 삼켜졌다: {err}");
    }

    /// 실측이 실제로 돈다(macOS): 이 시험 프로세스가 PTY 하나를 열면 own 이 1 이상.
    #[test]
    #[cfg(target_os = "macos")]
    fn census_counts_this_process_ptys() {
        let c = pty_census();
        assert!(c.total.is_some() && c.max.is_some() && c.own.is_some(), "{c:?}");
        let pair = portable_pty::native_pty_system()
            .openpty(portable_pty::PtySize { rows: 24, cols: 80, pixel_width: 0, pixel_height: 0 });
        if let Ok(_pair) = pair {
            let c2 = pty_census();
            assert!(c2.own.unwrap_or(0) >= 1, "열린 PTY 를 못 셌다: {c2:?}");
        }
    }
}
