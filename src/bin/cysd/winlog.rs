//! ★(1.1.21 · TICKET=cysr-win-cysd-stderr-1126) 윈도우 cysd 표준 오류 → 로그 파일.
//!
//! 【무엇이 틀렸었나】 윈도우에서 cysd 를 띄우는 길은 셋이고 셋 다 표준 오류를 버렸다:
//!   ① 앱 형제 기동(`src-tauri/src/main.rs` `spawn_bundled_cysd` — 맥만 launchd 로그 파일에 잇고 그 밖은 `Stdio::null()`)
//!   ② 작업 스케줄러(`src/bin/cys.rs` `cysd_task_xml_at` — `<Exec><Command>` 로 cysd.exe 를 직접 실행 · 셸이 없어 밖에서 리디렉션할 자리가 없다.
//!      릴리스 cysd 는 `windows_subsystem = "windows"` 라 표준 핸들 자체를 받지 못한다)
//!   ③ CLI 자동 기동(`spawn_detached_daemon` → `SpawnPolicy::spawn_policy(Survivor)` 가 stdio 를 null 로 덮는다)
//!   그래서 「옛 오피스 서버가 남아 있음」(office-bridge) 같은 데몬 한 줄 알림을 윈도우에서 볼 길이 없었다.
//!   맥은 launchd `StandardErrorPath`(src/launchd.rs `log_path` = 소켓 폴더 옆 `cysd.log`)에 남는다.
//!
//! 【왜 데몬 안 한 곳인가】 ②는 밖에서 고칠 수 없고(작업 명령을 `cmd /c … 2>>` 로 감싸면 콘솔 창·작업 판정
//!   `<Command>{daemon}</Command>` 대조·RestartOnFailure 대상이 함께 바뀐다), ①③과 앞으로 생길 기동 길을 하나씩 고치면
//!   또 한 길이 빠진다. 데몬이 기동 첫머리에 **자기 표준 오류가 버려지는 곳인지** 스스로 보고 로그 파일로 붙는다 —
//!   모든 기동 길이 한 번에 덮인다. Rust 표준 라이브러리의 윈도우 stderr 는 쓸 때마다 `GetStdHandle` 을 다시 읽으므로
//!   `SetStdHandle` 한 번이면 `eprintln!`(main.rs 의 보호 매크로 포함)·패닉 메시지가 모두 그 파일로 간다.
//!
//! 【무엇을 건드리지 않는가】
//!   · 맥·리눅스: 이 파일의 붙이기·회전은 `#[cfg(windows)]` 뿐이다(순수 판정 함수만 모든 타깃에서 컴파일 = 맥 시험 대상).
//!   · 누가 **일부러** 받고 있는 표준 오류(콘솔 = 디버그 실행 · 파이프 = 시험·캡처 · 디스크 파일 = 사용자 `2>`)는 그대로 둔다.
//!     붙는 경우는 「없음(작업 스케줄러) · NUL 장치(null 로 덮인 기동) · 종류 모름」 셋뿐이다.
//!   · 표준 출력: 손대지 않는다 — `println!` 은 쓰기가 실패하면(디스크 가득) 패닉하고, 보호 매크로는 `eprintln!`·`eprint!` 에만 있다.
//!
//! 【자리·상한·권한】
//!   · 자리 = 데몬 상태 폴더(`state::state_dir` — `%LOCALAPPDATA%\cys` · 부서 = `…\cys\<슬러그>`) 의 `cysd.log` —
//!     맥 `launchd::log_path`(소켓 폴더 = 상태 폴더 옆 `cysd.log`)와 같은 이름·같은 폴더 규약. 초기화(`factory_reset` WIN_STATE_EXACT)·
//!     갱신 스냅샷(`update::snapshot` `.log` 제외)이 이미 이 이름을 안다.
//!   · 상한 = [`LOG_MAX_BYTES`](4 MiB · `boot_supervisor` 로그와 같은 값) · 회전 1겹([`PREV_NAME`] = `cysd.1.log` —
//!     `.log` 로 끝나야 스냅샷 제외 규칙 `Suffix(".log")` 에 걸린다) · 최대 ≈ 8 MiB + 점검 간격 동안 쌓인 양.
//!     회전은 **단일 인스턴스 게이트를 이긴 데몬만** 한다(패자가 승자의 파일을 밀어내지 않게) — 기동 직후 1회 + [`ROTATE_EVERY`] 마다.
//!   · 회전 안전(codex 1R REVISE 반영): ⑴ 새 파일을 못 열거나 표준 오류 교체가 실패하면 이름을 되돌리고, 되돌리기마저 실패하면 **더는 회전하지
//!     않는다**(다음 회전의 「옛 보존본 지우기」가 지금 쓰는 기록을 지우는 일이 되므로 — 크기 상한보다 기록 보존이 먼저) ⑵ 교체와 옛 핸들 닫기는
//!     표준 오류 잠금 안에서 한다 — 잠금을 쥐고 쓰는 모든 쓰기(eprintln!·보호 매크로)와 겹치지 않는다. 잠금 밖에서 쓰는 것은 기본 패닉 출력뿐이고,
//!     그것이 옛 핸들을 집어 든 채 닫힘까지(한 점검 주기 = 10분) 멈춰 있을 때만 그 한 줄을 잃는다(남은 위험 · 시간 상한이지 완료 동기화는 아니다).
//!     ⑶ 표준 오류를 **상속**하는 자식(auto-restore 로그 열기 실패 때의 `Stdio::inherit()` 폴백 등 — 「증거 보존 · null 금지」 의도의 기존 코드)은
//!     복제 핸들을 쥐므로 회전 뒤에도 옛 파일에 쓴다: POSIX 지우기 파일계면 다음 회전 뒤 그 자식의 줄은 이름 없는 파일로 가고(자식이 끝나면 회수),
//!     아니면 지우기 대기가 이름을 붙들어 그 자식이 끝날 때까지 회전이 실패·재시도된다(기록은 cur 에 계속 쌓인다). 맥 launchd 로그도 자식이 같은
//!     파일을 상속한다 — 자식 배선을 바꾸는 것은 이 티켓 범위 밖이다.
//!   · 권한 = `%LOCALAPPDATA%` 의 사용자 전용 ACL 을 상속한다(따로 ACL 을 걸지 않는다 · 같은 폴더의 transcripts.db·operator.token 과 같은 보호).
//!     싣는 내용은 맥 cysd.log 가 이미 싣는 것과 같은 줄들이다(같은 `eprintln!` 호출처 — 새로 더하는 줄은 붙음·회전 알림 두 종류뿐).
#![cfg_attr(not(windows), allow(dead_code))]

use std::path::{Path, PathBuf};

/// 데몬 로그 파일 이름(맥 launchd `log_path` 와 같은 이름).
pub const LOG_NAME: &str = "cysd.log";
/// 회전 1겹 보존본 이름 — `.log` 로 끝나야 갱신 스냅샷 제외(`Suffix(".log")`)에 걸린다.
pub const PREV_NAME: &str = "cysd.1.log";
/// 크기 상한(넘으면 회전) — `boot_supervisor::LOG_MAX_BYTES` 와 같은 값.
pub const LOG_MAX_BYTES: u64 = 4 * 1024 * 1024;
/// 회전 점검 간격(첫 점검은 게이트 통과 직후).
pub const ROTATE_EVERY: std::time::Duration = std::time::Duration::from_secs(600);

/// 기동 시점의 표준 오류가 어디로 가는가(윈도우 `GetStdHandle`·`GetFileType`·`GetConsoleMode` 판독 결과).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ErrSink {
    /// 핸들 없음(NULL·INVALID) — 작업 스케줄러가 GUI 서브시스템 cysd 를 띄운 경우.
    Missing,
    /// NUL 장치(문자 장치인데 콘솔이 아님) — `Stdio::null()` 로 덮인 기동(앱 형제·CLI 자동 기동).
    NulDevice,
    /// 콘솔 — 사람이 디버그 빌드를 창에서 띄웠다.
    Console,
    /// 파이프 — 시험·상위 프로세스가 받아 읽는다.
    Pipe,
    /// 디스크 파일 — 사용자가 `2>` 로 받는다.
    Disk,
    /// 콘솔도 NUL 도 아닌 문자 장치(LPT·COM 등) — 일부러 받는 장치로 보고 그대로 둔다.
    OtherDevice,
    /// 종류 모름(FILE_TYPE_UNKNOWN 등).
    Unknown,
}

/// 붙을 것인가(순수) — 버려지는 곳(없음·NUL·모름)일 때만. 누가 받고 있으면 그대로 둔다.
pub fn should_take_over(sink: ErrSink) -> bool {
    matches!(sink, ErrSink::Missing | ErrSink::NulDevice | ErrSink::Unknown)
}

/// (로그, 회전 보존본) 경로(순수).
pub fn log_paths(state_dir: &Path) -> (PathBuf, PathBuf) {
    (state_dir.join(LOG_NAME), state_dir.join(PREV_NAME))
}

/// 덧붙이기로 연다(폴더가 없으면 만든다 — 게이트 전이라 상태 폴더가 아직 없을 수 있다).
pub fn open_append(path: &Path) -> std::io::Result<std::fs::File> {
    if let Some(dir) = path.parent() {
        std::fs::create_dir_all(dir)?;
    }
    std::fs::OpenOptions::new().create(true).append(true).open(path)
}

/// 회전 한 번의 결과.
#[derive(Debug)]
pub enum Rotate {
    /// 상한 이하 — 아무것도 안 했다.
    Kept,
    /// `cur` → `prev` 로 옮기고 새 `cur` 를 열었다(호출자가 표준 오류를 이것으로 바꾼다).
    Rotated(std::fs::File),
    /// 실패. `restored` = 지금 쓰는 파일이 다시 `cur` 이름에 있다(아무것도 잃지 않음 · 다음 점검에서 다시 한다).
    /// `restored == false` = 지금 쓰는 파일이 `prev` 이름에 남았다 → 호출자는 **다시 회전하지 않는다**
    /// (다음 회전의 「옛 보존본 지우기」가 곧 지금 쓰는 기록을 지우는 일이 된다 · codex 1R major 1).
    Failed { err: std::io::Error, restored: bool },
}

/// 회전(파일 시스템만 만진다 · `open` 주입 = 시험에서 열기 실패를 넣는다): `cur_len`(지금 쓰는 핸들로 잰 크기)이 `cap` 을 넘으면
/// 옛 보존본을 지우고 `cur` → `prev` 로 이름을 바꾼 뒤 새 `cur` 를 연다. 새 파일을 못 열면 이름을 되돌린다.
pub fn rotate_if_over_with(
    cur_len: u64,
    cur: &Path,
    prev: &Path,
    cap: u64,
    open: impl Fn(&Path) -> std::io::Result<std::fs::File>,
) -> Rotate {
    if cur_len <= cap {
        return Rotate::Kept;
    }
    match std::fs::remove_file(prev) {
        Ok(()) => {}
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => {}
        Err(err) => return Rotate::Failed { err, restored: true },
    }
    if let Err(err) = std::fs::rename(cur, prev) {
        return Rotate::Failed { err, restored: true };
    }
    match open(cur) {
        Ok(f) => Rotate::Rotated(f),
        Err(err) => Rotate::Failed { err, restored: undo_rotation(cur, prev) },
    }
}

/// [`rotate_if_over_with`] 의 제품 판(열기 = [`open_append`]).
pub fn rotate_if_over(cur_len: u64, cur: &Path, prev: &Path, cap: u64) -> Rotate {
    rotate_if_over_with(cur_len, cur, prev, cap, open_append)
}

/// 회전 되돌리기 — `cur` 자리에 새로 생긴 빈 파일이 있으면 지우고 `prev` → `cur` 로 이름을 되돌린다. 되돌렸으면 `true`.
pub fn undo_rotation(cur: &Path, prev: &Path) -> bool {
    match std::fs::remove_file(cur) {
        Ok(()) => {}
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => {}
        Err(_) => return false,
    }
    std::fs::rename(prev, cur).is_ok()
}

/// 문자 장치의 이름으로 NUL 을 가른다(순수 · codex 1R minor 4): `\Device\Null` 이면 NUL(붙음) · 다른 이름이면 일부러 받는 장치(그대로) ·
/// 이름을 못 읽었으면 모름(붙음 — 콘솔이 아닌 문자 장치 표준 오류는 사실상 NUL 이고, 못 붙으면 원래 결함(기록 0)이 그대로 남는다).
pub fn classify_char_device(object_name: Option<&str>) -> ErrSink {
    match object_name {
        Some(n) if n.eq_ignore_ascii_case(r"\Device\Null") => ErrSink::NulDevice,
        Some(_) => ErrSink::OtherDevice,
        None => ErrSink::Unknown,
    }
}

/// 붙음 알림 한 줄(순수 · 로그 첫머리에서 어느 기동 길이었는지 가른다).
pub fn attach_line(sink: ErrSink, log: &Path) -> String {
    format!(
        "[cysd] 표준 오류 → {} (윈도우 · 기동 때 표준 오류 = {sink:?} · 상한 {} MiB · 회전 1겹 {PREV_NAME})",
        log.display(),
        LOG_MAX_BYTES / (1024 * 1024)
    )
}

#[cfg(windows)]
mod imp {
    use super::*;
    use std::io::Write as _;
    use std::os::windows::io::AsRawHandle;
    use std::sync::{Mutex, OnceLock};
    use windows_sys::Wdk::Foundation::{NtQueryObject, OBJECT_NAME_INFORMATION};
    use windows_sys::Win32::Foundation::{HANDLE, INVALID_HANDLE_VALUE};
    use windows_sys::Win32::Storage::FileSystem::{GetFileType, FILE_TYPE_CHAR, FILE_TYPE_DISK, FILE_TYPE_PIPE};
    use windows_sys::Win32::System::Console::{GetConsoleMode, GetStdHandle, SetStdHandle, STD_ERROR_HANDLE};

    /// NtQueryObject 정보 갈래 `ObjectNameInformation`(= 1 · windows-sys 0.59 에 상수 없음 · ntdll 공개 열거 값).
    const OBJECT_NAME_INFORMATION_CLASS: i32 = 1;

    /// 붙은 뒤의 상태.
    struct Owned {
        cur: std::fs::File,
        /// 직전 회전의 옛 파일 — 바꾼 순간 표준 오류 잠금 밖에서 옛 핸들을 이미 집어 든 쓰기(기본 패닉 출력)가 끝나도록 한 주기 더 살린다.
        retired: Option<std::fs::File>,
        cur_path: PathBuf,
        prev_path: PathBuf,
        warned: bool,
        /// 되돌리기에도 실패해 지금 쓰는 파일이 prev 이름에 남았다 — 다시 회전하지 않는다(기록을 지우지 않는 쪽).
        stuck: bool,
    }

    static OWNED: OnceLock<Mutex<Owned>> = OnceLock::new();

    /// 문자 장치 핸들의 커널 객체 이름(`\Device\Null` 등). 파이프에는 부르지 않는다(동기 파이프에서 멈출 수 있는 API) — 문자 장치에만.
    fn char_device_name(h: HANDLE) -> Option<String> {
        let mut buf = vec![0u64; 128]; // 1 KiB · 8바이트 정렬(UNICODE_STRING 포인터)
        let mut ret = 0u32;
        // SAFETY: 버퍼는 정렬·크기가 맞고, 성공(NTSTATUS >= 0) 때만 UNICODE_STRING 을 읽는다. 길이는 바이트 단위.
        let st = unsafe {
            NtQueryObject(h, OBJECT_NAME_INFORMATION_CLASS, buf.as_mut_ptr().cast(), (buf.len() * 8) as u32, &mut ret)
        };
        if st < 0 {
            return None;
        }
        let info = unsafe { &*(buf.as_ptr() as *const OBJECT_NAME_INFORMATION) };
        if info.Name.Buffer.is_null() {
            return None;
        }
        let units = unsafe { std::slice::from_raw_parts(info.Name.Buffer, (info.Name.Length / 2) as usize) };
        Some(String::from_utf16_lossy(units))
    }

    pub fn classify() -> ErrSink {
        // SAFETY: 표준 핸들 판독은 부작용이 없다. 핸들 값은 비교·조회에만 쓰고 닫지 않는다.
        let h: HANDLE = unsafe { GetStdHandle(STD_ERROR_HANDLE) };
        if h.is_null() || h == INVALID_HANDLE_VALUE {
            return ErrSink::Missing;
        }
        match unsafe { GetFileType(h) } {
            FILE_TYPE_DISK => ErrSink::Disk,
            FILE_TYPE_PIPE => ErrSink::Pipe,
            FILE_TYPE_CHAR => {
                let mut mode = 0u32;
                if unsafe { GetConsoleMode(h, &mut mode) } != 0 {
                    ErrSink::Console
                } else {
                    classify_char_device(char_device_name(h).as_deref())
                }
            }
            _ => ErrSink::Unknown,
        }
    }

    fn set_stderr(f: &std::fs::File) -> bool {
        // SAFETY: `f` 는 OWNED 가 데몬 수명 동안(회전 뒤에도 한 주기 더) 쥐고 있어 핸들이 먼저 닫히지 않는다.
        unsafe { SetStdHandle(STD_ERROR_HANDLE, f.as_raw_handle() as HANDLE) != 0 }
    }

    pub fn attach(state_dir: &Path) {
        let sink = classify();
        if !should_take_over(sink) {
            return;
        }
        let (cur_path, prev_path) = log_paths(state_dir);
        // 실패는 조용히 종전(버림) 그대로 — 로그를 못 열어도 부트는 막지 않는다(앱 맥 배선과 같은 fail-open).
        let Ok(cur) = open_append(&cur_path) else { return };
        if !set_stderr(&cur) {
            return;
        }
        // 표준 오류가 이미 이 파일을 가리키므로 파일을 닫으면 안 된다 — 두 번째 부름(없어야 정상)이면 버리지 말고 새게 둔다.
        let owned = Owned { cur, retired: None, cur_path: cur_path.clone(), prev_path, warned: false, stuck: false };
        if let Err(dup) = OWNED.set(Mutex::new(owned)) {
            std::mem::forget(dup);
        }
        eprintln!("{}", attach_line(sink, &cur_path));
    }

    fn rotate_once() {
        let Some(m) = OWNED.get() else { return };
        let Ok(mut g) = m.lock() else { return };
        {
            // 직전 회전의 옛 파일(= 지금 prev 이름의 파일)을 닫는다 — 표준 오류 잠금 안에서(잠금을 쥐고 쓰는 eprintln 류와 겹치지 않게).
            //   쥔 채로 두면 POSIX 지우기가 안 되는 파일계에서 prev 가 「지우기 대기」로 이름을 붙든 채 남아 아래 이름 바꾸기가 매번 실패한다.
            let _err = std::io::stderr().lock();
            g.retired = None;
        }
        if g.stuck {
            return;
        }
        let len = g.cur.metadata().map(|md| md.len()).unwrap_or(0);
        let (cur_path, prev_path) = (g.cur_path.clone(), g.prev_path.clone());
        match rotate_if_over(len, &cur_path, &prev_path, LOG_MAX_BYTES) {
            Rotate::Kept => {}
            Rotate::Rotated(newf) => {
                // ★표준 오류 잠금 안에서 바꾼다(codex 1R major 3): 잠금을 쥐고 쓰는 모든 쓰기(eprintln!·보호 매크로·writeln!(stderr()))는
                //   바꾸기 전에 끝났거나 바꾼 뒤 새 핸들을 읽는다. 잠금 밖 쓰기(기본 패닉 출력)만 옛 핸들을 집어 들 수 있어 옛 파일을 한 주기 더 산다.
                let mut err = std::io::stderr().lock();
                if set_stderr(&newf) {
                    let old = std::mem::replace(&mut g.cur, newf);
                    g.retired = Some(old);
                    g.warned = false;
                    let _ = writeln!(err, "[cysd] 로그 회전: {len} 바이트 > 상한 {LOG_MAX_BYTES} → 앞 기록은 {}", prev_path.display());
                } else {
                    // 표준 오류는 여전히 옛 핸들(= 이제 prev 이름) — 새 빈 파일을 버리고 이름을 되돌린다. 못 되돌리면 다시 회전하지 않는다.
                    drop(newf);
                    if !undo_rotation(&cur_path, &prev_path) {
                        g.stuck = true;
                        let _ = writeln!(err, "[cysd] 로그 회전 멈춤: 표준 오류 교체·이름 되돌리기 모두 실패 — 지금 기록은 {} 에 계속 쌓는다(지우지 않으려고 더는 회전하지 않음)", prev_path.display());
                    }
                }
            }
            Rotate::Failed { err: e, restored } => {
                let mut err = std::io::stderr().lock();
                if !restored {
                    g.stuck = true;
                    let _ = writeln!(err, "[cysd] 로그 회전 멈춤({e}) — 새 파일을 못 열고 이름도 못 되돌렸다 · 지금 기록은 {} 에 계속 쌓는다(지우지 않으려고 더는 회전하지 않음)", prev_path.display());
                } else if !g.warned {
                    g.warned = true;
                    let _ = writeln!(err, "[cysd] 로그 회전 실패({e}) — {} 를 그대로 계속 쓴다(다음 점검에서 다시 한다)", cur_path.display());
                }
            }
        }
    }

    pub fn spawn_rotation() {
        if OWNED.get().is_none() {
            return;
        }
        let _ = std::thread::Builder::new().name("cysd-log-rotate".into()).spawn(|| loop {
            rotate_once();
            std::thread::sleep(ROTATE_EVERY);
        });
    }
}

/// 기동 첫머리(어떤 로그 줄보다 먼저)에서 부른다 — 표준 오류가 버려지는 곳이면 로그 파일로 붙는다. 윈도우 밖에서는 아무것도 안 한다.
pub fn attach_if_discarded(state_dir: &Path) {
    #[cfg(windows)]
    imp::attach(state_dir);
    #[cfg(not(windows))]
    let _ = state_dir;
}

/// 단일 인스턴스 게이트를 이긴 뒤 부른다 — 붙어 있을 때만 회전 점검 스레드를 띄운다(패자는 회전하지 않는다).
pub fn spawn_rotation_if_attached() {
    #[cfg(windows)]
    imp::spawn_rotation();
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn take_over_only_where_stderr_is_discarded() {
        assert!(should_take_over(ErrSink::Missing), "작업 스케줄러(핸들 없음)");
        assert!(should_take_over(ErrSink::NulDevice), "Stdio::null 로 덮인 기동");
        assert!(should_take_over(ErrSink::Unknown));
        for kept in [ErrSink::Console, ErrSink::Pipe, ErrSink::Disk, ErrSink::OtherDevice] {
            assert!(!should_take_over(kept), "일부러 받는 표준 오류는 그대로: {kept:?}");
        }
    }

    #[test]
    fn paths_pair_with_mac_name_and_prev_is_excluded_from_update_snapshot() {
        let (cur, prev) = log_paths(Path::new("/x/cys"));
        assert_eq!(cur, Path::new("/x/cys/cysd.log"));
        assert_eq!(prev, Path::new("/x/cys/cysd.1.log"));
        // 갱신 스냅샷은 두 파일 모두 건드리지 않는다(되돌리면 갱신 동안의 기록이 사라진다).
        assert!(cys::update::snapshot::is_excluded(LOG_NAME));
        assert!(cys::update::snapshot::is_excluded(PREV_NAME));
    }

    #[test]
    fn rotate_moves_over_cap_file_to_prev_and_opens_fresh() {
        use std::io::Write as _;
        let d = std::env::temp_dir().join(format!("cysd-winlog-{}-{:?}", std::process::id(), std::thread::current().id()));
        let _ = std::fs::remove_dir_all(&d);
        let (cur, prev) = log_paths(&d);
        let mut f = open_append(&cur).expect("폴더째 만들어 연다");
        f.write_all(b"0123456789").unwrap();
        std::fs::write(&prev, b"old-prev").unwrap();
        // 상한 이하 = 그대로.
        assert!(matches!(rotate_if_over(10, &cur, &prev, 10), Rotate::Kept));
        assert_eq!(std::fs::read(&cur).unwrap(), b"0123456789");
        // 상한 초과 = 옛 보존본을 버리고 cur → prev · 새 cur 는 비어 있고 덧붙이기로 열린다.
        let Rotate::Rotated(mut fresh) = rotate_if_over(11, &cur, &prev, 10) else { panic!("회전") };
        assert_eq!(std::fs::read(&prev).unwrap(), b"0123456789");
        assert_eq!(std::fs::read(&cur).unwrap(), b"");
        fresh.write_all(b"new").unwrap();
        // 옛 핸들로 쓴 줄은 보존본으로 간다(회전 뒤 한 주기 동안 다른 스레드가 옛 핸들로 써도 잃지 않는다).
        f.write_all(b"+tail").unwrap();
        assert_eq!(std::fs::read(&cur).unwrap(), b"new");
        assert_eq!(std::fs::read(&prev).unwrap(), b"0123456789+tail");
        let _ = std::fs::remove_dir_all(&d);
    }

    /// codex 1R major 1: 이름을 옮긴 뒤 새 파일을 못 열면 이름을 되돌린다 — 지금 쓰는 기록이 cur 이름에 그대로 있어야 다음 회전이 그것을 지우지 않는다.
    #[test]
    fn rotate_open_failure_restores_the_live_file_name() {
        use std::io::Write as _;
        let d = std::env::temp_dir().join(format!("cysd-winlog-of-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&d);
        let (cur, prev) = log_paths(&d);
        let mut live = open_append(&cur).unwrap();
        live.write_all(b"live").unwrap();
        std::fs::write(&prev, b"oldest").unwrap();
        let r = rotate_if_over_with(99, &cur, &prev, 10, |_| Err(std::io::Error::other("주입: 열기 실패")));
        let Rotate::Failed { restored, .. } = r else { panic!("실패여야 한다: {r:?}") };
        assert!(restored, "되돌리기 성공이어야 한다");
        live.write_all(b"+more").unwrap();
        assert_eq!(std::fs::read(&cur).unwrap(), b"live+more", "지금 쓰는 기록이 cur 이름으로 돌아왔다");
        assert!(!prev.exists(), "가장 옛 보존본만 잃는다(지우기는 이름 옮기기 전 단계)");
        // 다시 회전하면 정상으로 돈다(멈춤 표시 없음).
        assert!(matches!(rotate_if_over(99, &cur, &prev, 10), Rotate::Rotated(_)));
        assert_eq!(std::fs::read(&prev).unwrap(), b"live+more");
        let _ = std::fs::remove_dir_all(&d);
    }

    /// 표준 오류 교체 실패 갈래의 되돌리기(윈도우 갈래가 쓰는 같은 함수): 새 빈 cur 를 지우고 prev → cur.
    #[test]
    fn undo_rotation_puts_prev_back_and_drops_fresh_empty_file() {
        let d = std::env::temp_dir().join(format!("cysd-winlog-undo-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&d);
        let (cur, prev) = log_paths(&d);
        std::fs::create_dir_all(&d).unwrap();
        std::fs::write(&prev, b"was-live").unwrap();
        std::fs::write(&cur, b"").unwrap();
        assert!(undo_rotation(&cur, &prev));
        assert_eq!(std::fs::read(&cur).unwrap(), b"was-live");
        assert!(!prev.exists());
        // prev 가 없으면(되돌릴 것 없음) 실패로 알린다 — 호출자는 멈춤으로 간다.
        assert!(!undo_rotation(&cur, &prev));
        let _ = std::fs::remove_dir_all(&d);
    }

    /// codex 1R minor 4: 콘솔이 아닌 문자 장치 중 NUL 만 붙는다.
    #[test]
    fn char_device_takes_over_only_for_nul() {
        assert_eq!(classify_char_device(Some(r"\Device\Null")), ErrSink::NulDevice);
        assert_eq!(classify_char_device(Some(r"\DEVICE\NULL")), ErrSink::NulDevice);
        assert_eq!(classify_char_device(Some(r"\Device\Parallel0")), ErrSink::OtherDevice);
        assert_eq!(classify_char_device(None), ErrSink::Unknown);
        assert!(should_take_over(classify_char_device(Some(r"\Device\Null"))));
        assert!(!should_take_over(classify_char_device(Some(r"\Device\Serial0"))));
    }

    #[test]
    fn attach_line_names_path_and_sink() {
        let l = attach_line(ErrSink::Missing, Path::new("/x/cys/cysd.log"));
        assert!(l.starts_with("[cysd] 표준 오류 → /x/cys/cysd.log"), "{l}");
        assert!(l.contains("Missing") && l.contains("4 MiB") && l.contains(PREV_NAME), "{l}");
    }
}
