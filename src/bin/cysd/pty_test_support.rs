//! ★v116-flake-pty ⑵ — **시험 전용**: PTY 고갈(openpty ENXIO)을 제품 로직 실패와 구별한다.
//!
//! 왜: 병렬 게이트가 겹치면 기기 전체의 PTY(`kern.tty.ptmx_max` · 이 기기 511)가 순간 바닥나
//! `openpty failed: … Device not configured`(os error 6)로 cysd 시험이 붉어졌다(2026-09-24 ·
//! X-7 7회째 7건 · 정본 게이트 D07c 2건 — 둘 다 다른 워커 cargo 시험 동시 가동 중). 그 적색은
//! 「제품 단언이 틀렸다」와 구별되지 않는 모양(`expect("create surface")` 패닉 등)이었다.
//!
//! 무엇을 하나(좁게):
//!   · **ENXIO 일 때만** 상한 있는 재시도(1+2+4+8초). 다른 에러는 한 번도 재시도하지 않고 그대로
//!     돌려준다 — 진짜 결함은 종전과 똑같이 붉다.
//!   · 매 재시도는 libtest 출력 캡처를 **우회해** fd 2 에 1줄 남긴다 — 재시도 뒤 통과한 시험도 흔적이
//!     남아, 흡수된 PTY 압박이 초록 뒤에 숨지 않는다(적대 1R #1).
//!   · 상한을 넘기면 「PTY 고갈(openpty ENXIO) — 결함 판정 보류」 문구로 실패한다. ★「제품 결함 아님」은
//!     쓰지 않는다(적대 1R #1 · 2R #1·#2): PTY 는 셸 자식 등 **다른 프로세스**가 슬레이브를 쥐어도 살아
//!     있으므로, 제품이 자식을 못 거둬 PTY 를 새는 경우와 다른 병렬 시험이 겹친 경우를 시험 안에서 싸게
//!     가를 방법이 없다. 이 문구가 말하는 것은 「좌석 생성 자원 고갈로 멈췄다 — 제품 단언 실패가 아니다」
//!     까지이고, 원인(환경/누수)은 기기 PTY 수와 같은 시각의 동시 가동으로 사람이 가른다.
//!
//! 범위(정직 고지): 감싼 곳 = 도우미 5종(make_surface · create_surface_rpc · create_surface_rpc_idem ·
//! create_rpc · watch_wake seat) + usage.rs 3곳 = 09-24 관측 ENXIO 실패 9건의 경로 전부. 그 밖 직접
//! `create_surface` 호출(governance·state·channels·boot_supervisor 시험 등)은 감싸지 않았다 — 거기서 난
//! ENXIO 는 종전처럼 원문(`openpty failed … Device not configured`) 적색이다(편입 충돌 회피 · 후속 후보).
//! 부수효과(정직 고지): 재시도 뒤 성공하면 실패한 시도가 surface id 1개씩을 소비하고, RPC 경로는
//! `surface.create_failed` 이벤트를 1건씩 남긴다 — id·이벤트 수를 단언하는 시험은 그때 다른 문구로 붉을 수
//! 있다(재시도 줄이 fd 2 에 남으므로 원인 추적 가능).
//!
//! 제품 `state.rs` openpty 경로는 무접촉이다(이 모듈은 cfg(test) 로만 컴파일된다).

use std::time::Duration;

/// 재시도 대기(합계 15초). 관측된 고갈 구간은 수십 초 단위였다(`pty-17cc0a68.log` · 300개 이상
/// 약 40초) — 짧은 순간 고갈은 흡수하고, 긴 고갈은 오래 붙들지 않고 고갈 문구로 끝낸다.
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

/// 기기 전체 열린 PTY 수(`/dev/ttysN` 장치 노드) / 상한(`kern.tty.ptmx_max`) — 최선 노력(macOS · 못 재면 `?`).
/// 누가 쥐었는지는 세지 않는다(모듈 문서 — 시험 안에서 싸게 가를 수 없다).
pub(crate) fn pty_census() -> String {
    let total = std::fs::read_dir("/dev")
        .ok()
        .map(|it| {
            it.filter_map(|e| e.ok())
                .filter(|e| {
                    let n = e.file_name();
                    let n = n.to_string_lossy();
                    n.len() > 4 && n.starts_with("ttys") && n[4..].chars().all(|c| c.is_ascii_digit())
                })
                .count()
                .to_string()
        })
        .unwrap_or_else(|| "?".into());
    let max = std::process::Command::new("sysctl")
        .args(["-n", "kern.tty.ptmx_max"])
        .output()
        .ok()
        .filter(|o| o.status.success())
        .and_then(|o| String::from_utf8(o.stdout).ok())
        .map(|s| s.trim().to_string())
        .filter(|s| !s.is_empty())
        .unwrap_or_else(|| "?".into());
    format!("{total}/{max}")
}

/// 상한을 넘긴 고갈의 실패 문구(순수) — 제품 단언 실패와 문구가 갈리되, 원인 판정은 하지 않는다.
pub(crate) fn exhaustion_wording(what: &str, attempts: usize, err: &str, census: &str) -> String {
    format!(
        "PTY 고갈(openpty ENXIO) — 결함 판정 보류: 좌석 생성 자원 고갈로 멈췄다(제품 단언 실패 아님) · \
         원인(동시 병렬 시험 / 제품 PTY 누수)은 같은 시각 기기 PTY 수·동시 가동으로 가른다 · {what} · \
         시도 {attempts}회 · 기기 PTY {census} · 원문: {err}"
    )
}

/// libtest 는 `eprintln!` 을 **통과한 시험에서 삼킨다** — 재시도 흔적은 fd 2 에 직접 쓴다(적대 1R #1).
fn log_uncaptured(line: &str) {
    use std::io::Write;
    let _ = std::io::stderr().write_all(format!("{line}\n").as_bytes());
}

/// 순수 재시도 루프(대기·로그 주입 — 단위 시험은 실제로 자지 않고 게이트 로그를 더럽히지 않는다).
/// `f` 가 ENXIO 로 실패할 때만 `backoff` 길이만큼 다시 부른다. 반환 `(결과, 시도 수)`.
pub(crate) fn retry_with<T>(
    what: &str,
    backoff: &[Duration],
    mut sleep: impl FnMut(Duration),
    mut log: impl FnMut(&str),
    mut census: impl FnMut() -> String,
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
                    return (Err(exhaustion_wording(what, attempts, &e, &census())), attempts);
                };
                log(&format!(
                    "[pty-retry] {what}: openpty ENXIO — {}ms 뒤 재시도 {attempts}/{} · 기기 PTY {}",
                    d.as_millis(),
                    backoff.len(),
                    census()
                ));
                sleep(*d);
            }
        }
    }
}

/// 시험 도우미용 — `Daemon::create_surface` 류 호출을 감싼다.
pub(crate) fn retry_on_pty_exhaustion<T>(what: &str, f: impl FnMut() -> Result<T, String>) -> Result<T, String> {
    retry_with(what, &PTY_RETRY_BACKOFF, std::thread::sleep, log_uncaptured, pty_census, f).0
}

/// 시험 도우미용 — `surface.create` RPC 응답(Value)을 감싼다. ENXIO 응답일 때만 재시도하고,
/// 상한을 넘기면 고갈 문구로 panic 한다(그 응답을 호출자에게 넘기면 제품 단언 실패와 모양이 같아진다).
/// ENXIO 가 아닌 응답(성공·거부·다른 실패)은 그대로 돌려준다.
pub(crate) fn rpc_retry_on_pty_exhaustion(
    what: &str,
    mut f: impl FnMut() -> serde_json::Value,
) -> serde_json::Value {
    let mut last = serde_json::Value::Null;
    let (r, _) = retry_with(what, &PTY_RETRY_BACKOFF, std::thread::sleep, log_uncaptured, pty_census, || {
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
    use std::cell::{Cell, RefCell};

    /// ★실제 오류 모양으로 주입(master 결정 ① · 문자열 흉내 금지): 제품 경로는
    /// `state.rs` `format!("openpty failed: {e}")` ∘ 벤더 portable-pty `bail!("failed to openpty: {:?}",
    /// io::Error::last_os_error())` 이다 — 같은 두 단을 실제 `io::Error`(raw errno)로 거친다.
    fn openpty_err(errno: i32) -> String {
        // 메시지 전용 anyhow 오류의 Display 는 그 메시지 자체다(이 크레이트는 anyhow 비의존 — 신규 의존 없이 재현).
        let bail_msg = format!("failed to openpty: {:?}", std::io::Error::from_raw_os_error(errno));
        format!("openpty failed: {bail_msg}")
    }

    /// 단위 시험용 재시도: 대기·로그·실측을 모두 주입(게이트 로그에 가짜 `[pty-retry]` 줄 0 · 적대 2R #5).
    fn retry_quiet<T>(
        what: &str,
        slept: &RefCell<Vec<Duration>>,
        logs: &RefCell<Vec<String>>,
        f: impl FnMut() -> Result<T, String>,
    ) -> (Result<T, String>, usize) {
        retry_with(
            what,
            &PTY_RETRY_BACKOFF,
            |d| slept.borrow_mut().push(d),
            |l| logs.borrow_mut().push(l.to_string()),
            || "7/511".to_string(),
            f,
        )
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

    /// ENXIO 두 번 뒤 성공 → 성공 · 시도 3 · 대기 2번(1s, 2s) · 재시도 줄 2개(주입 로거로만).
    #[test]
    fn transient_exhaustion_is_retried_then_succeeds() {
        let n = Cell::new(0);
        let (slept, logs) = (RefCell::new(Vec::new()), RefCell::new(Vec::new()));
        let (r, attempts) = retry_quiet("t", &slept, &logs, || {
            n.set(n.get() + 1);
            if n.get() <= 2 { Err(openpty_err(libc::ENXIO)) } else { Ok(7) }
        });
        assert_eq!(r, Ok(7));
        assert_eq!(attempts, 3);
        assert_eq!(*slept.borrow(), vec![Duration::from_secs(1), Duration::from_secs(2)]);
        assert_eq!(logs.borrow().len(), 2);
        assert!(logs.borrow()[0].starts_with("[pty-retry] t: openpty ENXIO — 1000ms 뒤 재시도 1/4 · 기기 PTY 7/511"));
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
            let (slept, logs) = (RefCell::new(Vec::new()), RefCell::new(Vec::new()));
            let (r, attempts) = retry_quiet("t", &slept, &logs, || Err::<(), _>(e.clone()));
            assert_eq!(attempts, 1, "결함 에러를 재시도했다: {e}");
            assert!(slept.borrow().is_empty() && logs.borrow().is_empty(), "결함 에러에 대기·재시도 줄: {e}");
            assert_eq!(r, Err(e.clone()), "결함 에러 문구가 바뀌었다");
        }
    }

    /// ★상한(master 결정 ③): 재시도 총량(1+2+4+8초)이 끝나면 반드시 실패로 끝난다. 대기는 주입(실제로
    /// 자지 않음)이라 「무한 재시도」 뮤턴트는 50회째 호출에서 즉시 죽는다(시험 제한시간 무관).
    #[test]
    fn persistent_exhaustion_stops_at_cap_with_exhaustion_wording() {
        let n = Cell::new(0);
        let (slept, logs) = (RefCell::new(Vec::new()), RefCell::new(Vec::new()));
        let (r, attempts) = retry_quiet("seat(master)", &slept, &logs, || {
            n.set(n.get() + 1);
            assert!(n.get() <= 50, "재시도 상한이 없다(50회 초과)");
            Err::<(), _>(openpty_err(libc::ENXIO))
        });
        assert_eq!(attempts, PTY_RETRY_BACKOFF.len() + 1);
        assert_eq!(slept.borrow().iter().sum::<Duration>(), Duration::from_secs(15), "재시도 총량이 1+2+4+8초가 아니다");
        assert_eq!(logs.borrow().len(), PTY_RETRY_BACKOFF.len());
        let e = r.unwrap_err();
        assert!(e.starts_with("PTY 고갈(openpty ENXIO) — 결함 판정 보류"), "{e}");
        assert!(e.contains(" · seat(master) · 시도 5회 · 기기 PTY 7/511 · "), "{e}");
        assert!(e.contains(&openpty_err(libc::ENXIO)), "원문이 사라졌다: {e}");
    }

    /// ★적대 1R #1 · 2R #1·#2: 고갈 문구는 원인을 단정하지 않는다 — 「제품 결함 아님」·「환경」 판정 금지.
    #[test]
    fn exhaustion_wording_never_claims_a_cause() {
        let w = exhaustion_wording("t", 5, &openpty_err(libc::ENXIO), "511/511");
        for banned in ["제품 결함 아님", "(환경)"] {
            assert!(!w.contains(banned), "근거 없는 원인 단정 {banned:?}: {w}");
        }
        assert!(w.contains("제품 단언 실패 아님") && w.contains("제품 PTY 누수"), "{w}");
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

    /// 재실행 전용 탐침(기본 제외) — **실제 로거**로 재시도 2번을 낸다(대기는 0). 평소 시험 실행에서는 돌지
    /// 않아 게이트 로그에 가짜 재시도 줄을 남기지 않는다(적대 2R #5).
    #[test]
    #[ignore = "retry_line_survives_libtest_output_capture 가 재실행으로만 부른다"]
    fn probe_real_logger_retries_twice() {
        // 부모 시험이 부를 때만 오류를 주입한다 — 사람이 `--ignored` 로 돌려도 가짜 재시도 줄 0(agy 3R #2).
        if std::env::var("CYS_PTY_PROBE").as_deref() != Ok("1") {
            return;
        }
        let n = Cell::new(0);
        let (r, _) = retry_with("probe", &PTY_RETRY_BACKOFF, |_| {}, log_uncaptured, pty_census, || {
            n.set(n.get() + 1);
            if n.get() <= 2 { Err(openpty_err(libc::ENXIO)) } else { Ok(()) }
        });
        assert_eq!(r, Ok(()));
    }

    /// ★적대 1R #1(자동 판정): 재시도 줄은 libtest 기본 캡처를 **뚫고** 나와야 한다. 이 시험 바이너리로
    /// 탐침 하나만 기본 캡처로 재실행해 그 stderr 에 `[pty-retry] probe` 줄 2개가 있는지 본다
    /// (`eprintln!` 로 되돌리면 캡처돼 사라진다 = 적색). 상속된 `RUST_TEST_NOCAPTURE` 는 지운다 — 남으면
    /// 캡처가 꺼져 `eprintln!` 판도 통과한다(헛초록 · 적대 2R #6).
    #[test]
    fn retry_line_survives_libtest_output_capture() {
        let exe = std::env::current_exe().expect("현재 시험 바이너리");
        let out = std::process::Command::new(exe)
            .args(["--exact", "pty_test_support::tests::probe_real_logger_retries_twice", "--ignored"])
            .env_remove("RUST_TEST_NOCAPTURE")
            .env("CYS_PTY_PROBE", "1")
            .output()
            .expect("시험 바이너리 재실행");
        let err = String::from_utf8_lossy(&out.stderr);
        let so = String::from_utf8_lossy(&out.stdout);
        assert!(out.status.success(), "재실행 탐침 실패: {so}{err}");
        assert!(so.contains("1 passed"), "탐침이 돌지 않았다: {so}");
        assert_eq!(err.matches("[pty-retry] probe: openpty ENXIO").count(), 2, "재시도 줄이 캡처에 삼켜졌다: {err}");
    }

    #[test]
    #[cfg(target_os = "macos")]
    fn census_reads_device_count_and_max() {
        let c = pty_census();
        let (t, m) = c.split_once('/').expect("n/max 모양");
        assert!(t.parse::<usize>().is_ok() && m.parse::<usize>().unwrap_or(0) > 0, "{c}");
    }
}
