//! 갱신 시계 규칙(설계 AUTO-UPDATE-118 §4-5 · MA1 · 2R MAJOR 1 · N13).
//!
//! 기록 단위 = `{boot_id, mono_ms, wall}`. 같은 `boot_id` 면 경과 = 단조값 차(벽시계 무관). 재부팅으로 `boot_id` 가
//! 바뀌면 단조값은 이어지지 않으므로 타이머 성격에 따라 **보수 쪽**으로 고른다:
//!  · 「적어도 X 를 기다려야 하는」 타이머(72시간 정상·백오프·지터·첫 확인 15분) = [`elapsed_for_wait`]
//!    `max(0, min(벽시계 경과, 서명 시각 기준 경과))` · 벽시계가 의심스러우면 **0**(다시 기다림 = 늦어질 뿐 위험 0).
//!  · 「너무 오래됐으면 보류」 타이머(폐기문 30일 · 봉투 만료) = [`elapsed_for_staleness`] — 의심스러우면 **오래됐다**.
//!
//! `boot_id` = 부팅 시각(`sysinfo::System::boot_time()` · 재부팅하면 바뀐다 — `factory_reset.rs` 의 같은 정의를 공용으로 쓴다).
//! 단조값 = 맥 `CLOCK_MONOTONIC`(애플 정의: 잠자는 동안도 증가) · 리눅스 `CLOCK_BOOTTIME`(잠 포함) · 윈 `GetTickCount64`
//! (잠 포함). 잠 포함 여부가 OS 마다 달라도 아래 규칙은 같다(같은 부팅 안의 차만 쓴다).

use serde::{Deserialize, Serialize};

/// N13 — 벽시계가 마지막 신뢰 시각보다 이만큼 넘게 과거면 의심.
pub const SUSPECT_BEHIND_TRUSTED_SECS: i64 = 300;
/// N13 — HTTPS 응답 `Date` 와 이만큼 넘게 차이 나면 의심.
pub const SUSPECT_HTTP_DATE_SKEW_SECS: i64 = 3600;

/// 시각 기록 1개.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct Stamp {
    pub boot_id: u64,
    pub mono_ms: u64,
    pub wall: i64,
}

/// 지금 시각 기록.
pub fn now_stamp() -> Stamp {
    Stamp { boot_id: boot_id(), mono_ms: mono_ms(), wall: wall_now() }
}

/// 부팅 식별자(= 부팅 시각 epoch 초).
pub fn boot_id() -> u64 {
    sysinfo::System::boot_time()
}

pub fn wall_now() -> i64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs() as i64)
        .unwrap_or(0)
}

/// 단조 밀리초(이 부팅 안에서만 의미).
pub fn mono_ms() -> u64 {
    // ★1R MAJOR(M4): 맥 = 설계 정본 그대로 `mach_continuous_time`(잠자는 동안 포함) × timebase.
    #[cfg(target_os = "macos")]
    {
        // libSystem 선언을 직접 둔다(libc 의 mach_timebase_info 는 폐지 예고 경고 — mach2 크레이트를 새로 들이지 않으려고).
        #[repr(C)]
        struct MachTimebaseInfo {
            numer: u32,
            denom: u32,
        }
        extern "C" {
            fn mach_continuous_time() -> u64;
            fn mach_timebase_info(info: *mut MachTimebaseInfo) -> i32;
        }
        let mut tb = MachTimebaseInfo { numer: 0, denom: 0 };
        // SAFETY: tb 는 유효한 지역 구조체(mach_timebase_info_data_t 와 같은 배치) · mach_continuous_time 은 인자 없는 조회.
        let (rc, t) = unsafe { (mach_timebase_info(&mut tb), mach_continuous_time()) };
        if rc != 0 || tb.denom == 0 {
            return 0;
        }
        ((t as u128 * tb.numer as u128 / tb.denom as u128) / 1_000_000) as u64
    }
    #[cfg(all(unix, not(target_os = "macos")))]
    {
        mono_clock(libc::CLOCK_BOOTTIME)
    }
    #[cfg(windows)]
    {
        #[link(name = "kernel32")]
        extern "system" {
            fn GetTickCount64() -> u64;
        }
        // SAFETY: 인자 없는 시스템 조회.
        unsafe { GetTickCount64() }
    }
}

#[cfg(all(unix, not(target_os = "macos")))]
fn mono_clock(id: libc::clockid_t) -> u64 {
    let mut ts = libc::timespec { tv_sec: 0, tv_nsec: 0 };
    // SAFETY: ts 는 유효한 지역 변수.
    let rc = unsafe { libc::clock_gettime(id, &mut ts) };
    if rc != 0 {
        return 0;
    }
    (ts.tv_sec as u64).saturating_mul(1000) + (ts.tv_nsec as u64) / 1_000_000
}

/// N13 — 시계 의심 판정. `last_trusted` = 수용한 서명(봉투·폐기문)의 `signed_at` 최댓값 · `http_date` = HTTPS 응답 `Date`.
pub fn clock_suspect(wall_now: i64, last_trusted: Option<i64>, http_date: Option<i64>) -> bool {
    if let Some(t) = last_trusted {
        if wall_now < t - SUSPECT_BEHIND_TRUSTED_SECS {
            return true;
        }
    }
    if let Some(d) = http_date {
        if (wall_now - d).abs() > SUSPECT_HTTP_DATE_SKEW_SECS {
            return true;
        }
    }
    false
}

/// N13 — **받은 모든 HTTPS 응답의 `Date`** 를 본다(1R MAJOR M4: 하나만 보면 다른 응답의 큰 시각 차가 숨는다).
pub fn clock_suspect_dates(wall_now: i64, last_trusted: Option<i64>, dates: &[Option<i64>]) -> bool {
    if clock_suspect(wall_now, last_trusted, None) {
        return true;
    }
    let mut it = dates.iter().flatten();
    if super::mutant("M4") {
        return it.next().map(|d| clock_suspect(wall_now, None, Some(*d))).unwrap_or(false);
    }
    it.any(|d| clock_suspect(wall_now, None, Some(*d)))
}

/// 「기다림」 타이머의 경과(초). 같은 부팅 = 단조 차 · 재부팅 = `max(0, min(벽시계 경과, 서명 시각 기준 경과))` ·
/// 의심 또는 서명 시각 기준이 없으면 0.
pub fn elapsed_for_wait(then: &Stamp, now: &Stamp, wall_suspect: bool, last_trusted: Option<i64>) -> u64 {
    if then.boot_id == now.boot_id && now.mono_ms >= then.mono_ms {
        return (now.mono_ms - then.mono_ms) / 1000;
    }
    if wall_suspect {
        return 0;
    }
    let Some(t) = last_trusted else { return 0 };
    let by_wall = now.wall - then.wall;
    let by_trusted = t - then.wall;
    by_wall.min(by_trusted).max(0) as u64
}

/// 「낡음」 타이머의 경과(초). 같은 부팅 = 단조 차 · 재부팅 = `max(벽시계 경과, 서명 시각 기준 경과, 0)` · 의심 = 무한대(낡았다).
pub fn elapsed_for_staleness(then: &Stamp, now: &Stamp, wall_suspect: bool, last_trusted: Option<i64>) -> u64 {
    if then.boot_id == now.boot_id && now.mono_ms >= then.mono_ms {
        return (now.mono_ms - then.mono_ms) / 1000;
    }
    if wall_suspect {
        return u64::MAX;
    }
    let by_wall = now.wall - then.wall;
    let by_trusted = last_trusted.map(|t| t - then.wall).unwrap_or(i64::MIN);
    by_wall.max(by_trusted).max(0) as u64
}

/// HTTP `Date` 헤더(RFC 7231 IMF-fixdate · 예 `Tue, 06 Oct 2026 00:12:00 GMT`) → epoch 초.
pub fn parse_http_date(s: &str) -> Option<i64> {
    chrono::DateTime::parse_from_rfc2822(s.trim()).ok().map(|d| d.timestamp())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn st(boot: u64, mono_s: u64, wall: i64) -> Stamp {
        Stamp { boot_id: boot, mono_ms: mono_s * 1000, wall }
    }

    #[test]
    fn same_boot_uses_monotonic_and_ignores_wall_jumps() {
        let a = st(100, 1000, 5_000);
        let b = st(100, 1000 + 3600, 1_000); // 벽시계는 뒤로 4000초 점프
        assert_eq!(elapsed_for_wait(&a, &b, true, None), 3600);
        assert_eq!(elapsed_for_staleness(&a, &b, true, None), 3600);
    }

    /// §7-1 「boot_id 바뀜 경과 계산」.
    #[test]
    fn reboot_wait_is_conservative_and_staleness_is_pessimistic() {
        let a = st(100, 50_000, 1_000_000);
        let b = st(200, 30, 1_000_000 + 10_000); // 재부팅 · 벽시계 1만 초 경과
        // 서명 시각 기준 6000초만 증명됨 → 기다림 = 6000(작은 쪽)
        assert_eq!(elapsed_for_wait(&a, &b, false, Some(1_000_000 + 6_000)), 6_000);
        // 서명 시각 기준 없음 → 0(다시 기다림)
        assert_eq!(elapsed_for_wait(&a, &b, false, None), 0);
        // 시계 의심 → 0
        assert_eq!(elapsed_for_wait(&a, &b, true, Some(2_000_000)), 0);
        // 벽시계가 기록보다 과거 → 0(음수 아님)
        let c = st(300, 1, 900_000);
        assert_eq!(elapsed_for_wait(&a, &c, false, Some(900_000)), 0);
        // 낡음 = 큰 쪽 · 의심 = 무한대
        assert_eq!(elapsed_for_staleness(&a, &b, false, Some(1_000_000 + 6_000)), 10_000);
        assert_eq!(elapsed_for_staleness(&a, &b, true, None), u64::MAX);
        // 같은 boot_id 인데 단조값이 줄었다(있을 수 없음) → 재부팅 취급
        let d = st(100, 10, 1_000_000 + 50);
        assert_eq!(elapsed_for_wait(&a, &d, false, Some(1_000_000 + 50)), 50);
    }

    #[test]
    fn n13_clock_suspect_rules() {
        assert!(!clock_suspect(1_000, Some(1_200), None)); // 200초 과거 = 허용(≤300)
        assert!(clock_suspect(1_000, Some(1_301), None)); // 301초 과거 = 의심
        assert!(!clock_suspect(10_000, None, Some(10_000 + 3_600)));
        assert!(clock_suspect(10_000, None, Some(10_000 + 3_601)));
        assert!(clock_suspect(10_000, None, Some(10_000 - 3_601)));
        assert!(!clock_suspect(10_000, None, None));
    }

    /// ★1R M4 뮤테이션: 응답 4개 중 하나만 1시간 넘게 어긋나도 의심.
    #[test]
    fn m4_every_response_date_is_checked() {
        let now = 1_000_000;
        assert!(!clock_suspect_dates(now, None, &[Some(now), None, Some(now + 10)]));
        assert!(clock_suspect_dates(now, None, &[Some(now), Some(now - 7200), None, Some(now)]));
        assert!(clock_suspect_dates(now, Some(now + 400), &[]));
    }

    /// 맥 단조값 = mach_continuous_time 계열(잠 포함) — 같은 부팅 안에서 줄지 않고 벽시계와 같은 빠르기.
    #[test]
    fn mono_advances_like_wall() {
        let a = mono_ms();
        std::thread::sleep(std::time::Duration::from_millis(30));
        let b = mono_ms();
        assert!(b >= a + 25 && b < a + 5_000, "{a} → {b}");
    }

    #[test]
    fn http_date_parse() {
        assert_eq!(parse_http_date("Tue, 06 Oct 2026 00:12:00 GMT"), Some(1_791_245_520));
        assert_eq!(parse_http_date("not a date"), None);
    }

    #[test]
    fn live_clock_is_sane() {
        let a = now_stamp();
        let b = now_stamp();
        assert_eq!(a.boot_id, b.boot_id);
        assert!(b.mono_ms >= a.mono_ms);
        assert!(a.boot_id > 0 && a.wall > 1_700_000_000);
    }
}
