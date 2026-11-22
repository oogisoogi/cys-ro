//! seatkeep 등록부 · 교체 기록 · 종료 기록 — T2 시제품(DESIGN.md §4-1 · master 판단 11-11 ②).
//!
//! 파일(모두 `<dir>/seatkeep/` 아래 · 폴더 0700):
//! - `<id>.json`  등록부 항목. 「준비(prepare)」 → 「확정(committed)」 → 「끝남(exited)」. 원자적 교체(임시 파일 + rename).
//! - `<id>.log`   조종자 받기·끊김·거절 기록. **덧붙이기 전용으로만 연다**(O_APPEND). 쓰기 실패 = 접속을 받지 않는다.
//! - `<id>.exit`  자식 종료 기록. 조종자의 EXIT_ACK 까지 보존(받으면 지운다 · 못 받으면 남겨 새 조종자가 소비).
//! - `<id>.sock`  조종자 접속 소켓(0600).
//! - `<id>.lock`  id 잠금(flock) — 같은 id 의 seatkeep 은 동시에 하나만. 프로세스가 끝나면 풀린다.

use std::fs::{File, OpenOptions};
use std::io::Write;
use std::os::unix::fs::{OpenOptionsExt, PermissionsExt};
use std::path::{Path, PathBuf};

pub struct Paths {
    pub dir: PathBuf,
    pub entry: PathBuf,
    pub log: PathBuf,
    pub exit: PathBuf,
    pub sock: PathBuf,
    pub idlock: PathBuf,
}

impl Paths {
    pub fn new(state_dir: &Path, id: &str) -> Paths {
        let dir = state_dir.join("seatkeep");
        Paths {
            entry: dir.join(format!("{id}.json")),
            log: dir.join(format!("{id}.log")),
            exit: dir.join(format!("{id}.exit")),
            sock: dir.join(format!("{id}.sock")),
            idlock: dir.join(format!("{id}.lock")),
            dir,
        }
    }

    /// 상태 폴더 준비. `seatkeep` 폴더가 이미 있으면 **심볼릭 링크가 아닌 진짜 폴더**이고 소유자가 나여야 한다 —
    /// 링크를 따라가 남의 폴더를 0700 으로 바꾸거나 그 안에 쓰지 않는다(독립 검증 D6).
    pub fn ensure_dir(&self) -> std::io::Result<()> {
        use std::os::unix::fs::MetadataExt;
        if let Some(parent) = self.dir.parent() {
            std::fs::create_dir_all(parent)?;
        }
        match std::fs::symlink_metadata(&self.dir) {
            Ok(m) => {
                if !m.file_type().is_dir() {
                    return Err(std::io::Error::other(format!("{} 는 폴더가 아니다(심볼릭 링크·파일 거부)", self.dir.display())));
                }
                if m.uid() != unsafe { libc::geteuid() } {
                    return Err(std::io::Error::other(format!("{} 의 소유자가 내가 아니다", self.dir.display())));
                }
            }
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => match std::fs::create_dir(&self.dir) {
                Ok(()) => {}
                // 다른 seatkeep 이 같은 순간에 처음 만들었다(좌석 여럿 동시 기동 · T3 실측) — 그 폴더를 같은 검사로 다시 본다.
                Err(e) if e.kind() == std::io::ErrorKind::AlreadyExists => return self.ensure_dir(),
                Err(e) => return Err(e),
            },
            Err(e) => return Err(e),
        }
        std::fs::set_permissions(&self.dir, std::fs::Permissions::from_mode(0o700))
    }
}

static TMP_SEQ: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(0);

/// 임시 파일에 쓰고 fsync 뒤 rename, 그다음 폴더 fsync — 읽는 쪽은 옛 내용이나 새 내용 중 하나만 본다.
/// 임시 파일 이름 = 대상 파일 이름 전체 + pid + 호출 번호, `create_new` — 같은 프로세스 안에서 `<id>.json` 과
/// `<id>.exit` 를 동시에 써도 서로의 임시 파일을 덮거나 옮기지 않는다(codex 1R #4: 옛 `with_extension` 은 둘 다
/// `<id>.tmp.<pid>` 였다).
pub fn write_atomic(path: &Path, value: &serde_json::Value) -> std::io::Result<()> {
    let name = path.file_name().map(|n| n.to_string_lossy().into_owned()).unwrap_or_default();
    let seq = TMP_SEQ.fetch_add(1, std::sync::atomic::Ordering::SeqCst);
    let tmp = path.with_file_name(format!(".{name}.tmp.{}.{seq}", std::process::id()));
    let res = (|| {
        let mut f = OpenOptions::new().write(true).create_new(true).mode(0o600).open(&tmp)?;
        f.write_all(value.to_string().as_bytes())?;
        f.sync_all()?;
        drop(f);
        std::fs::rename(&tmp, path)?;
        if let Some(dir) = path.parent() {
            File::open(dir)?.sync_all()?;
        }
        Ok(())
    })();
    if res.is_err() {
        let _ = std::fs::remove_file(&tmp);
    }
    res
}

/// id 잠금 — 비차단 배타 flock. 이미 잡혀 있으면 오류(WouldBlock). 돌려준 File 을 쥐고 있는 동안 유효.
pub fn lock_id(path: &Path) -> std::io::Result<File> {
    use std::os::unix::io::AsRawFd;
    let f = OpenOptions::new().read(true).write(true).create(true).mode(0o600).custom_flags(libc::O_NOFOLLOW).open(path)?;
    if unsafe { libc::flock(f.as_raw_fd(), libc::LOCK_EX | libc::LOCK_NB) } != 0 {
        return Err(std::io::Error::last_os_error());
    }
    Ok(f)
}

/// 교체 기록 줄 쓰기 실패. `kept_line` = 그 줄이 파일에 온전히 남았는가(= 쓰기는 끝났고 fsync 만 실패) — **이번 호출의 값**이다
/// (codex 3R #2: 공유 칸으로 두면 앞선 fsync 실패의 「참」이 뒤 호출의 다른 실패(길이 읽기 등)에 남아 `accept` 없는
/// `accept_aborted` 를 만든다).
#[derive(Debug)]
pub struct LineError {
    pub error: std::io::Error,
    pub kept_line: bool,
}

impl std::fmt::Display for LineError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        self.error.fmt(f)
    }
}

/// 교체 기록이 파일에 하는 일 — 실제 파일과 단위 시험의 실패 주입용 가짜가 같은 길을 탄다.
pub trait LedgerFile: Write {
    fn size(&self) -> std::io::Result<u64>;
    fn truncate(&mut self, len: u64) -> std::io::Result<()>;
    fn sync(&mut self) -> std::io::Result<()>;
}

impl LedgerFile for File {
    fn size(&self) -> std::io::Result<u64> {
        Ok(self.metadata()?.len())
    }
    fn truncate(&mut self, len: u64) -> std::io::Result<()> {
        self.set_len(len)
    }
    fn sync(&mut self) -> std::io::Result<()> {
        self.sync_data()
    }
}

/// 교체 기록. 덧붙이기 전용 열기 — 이 프로세스는 자기 기록을 고쳐 쓸 수 없다(예외: 아래 짧은 쓰기 되돌림 = 자기가 방금
/// 덧붙이다 만 조각만 잘라 낸다). 심볼릭 링크는 따라가지 않는다(독립 검증 D6).
pub struct Ledger<F: LedgerFile = File> {
    file: F,
    /// 짧은 쓰기 조각을 잘라 내지 못한 채 남아 있다 → 다음 줄을 줄바꿈으로 시작해 조각과 이어 붙지 않게 한다.
    torn: bool,
}

impl Ledger<File> {
    pub fn open(path: &Path) -> std::io::Result<Ledger> {
        let file = OpenOptions::new().append(true).create(true).mode(0o600).custom_flags(libc::O_NOFOLLOW).open(path)?;
        // 앞 기동이 남긴 조각(마지막 바이트가 줄바꿈이 아님)이 있으면 첫 줄을 줄바꿈으로 시작한다(codex 2R #4 — 표시가
        // 메모리에만 있으면 재기동 뒤 첫 줄이 조각에 이어 붙는다).
        let torn = {
            use std::io::{Read, Seek, SeekFrom};
            let mut r = OpenOptions::new().read(true).custom_flags(libc::O_NOFOLLOW).open(path)?;
            let len = r.metadata()?.len();
            let mut last = [b'\n'];
            if len > 0 {
                r.seek(SeekFrom::Start(len - 1))?;
                r.read_exact(&mut last)?;
            }
            last[0] != b'\n'
        };
        Ok(Ledger { file, torn })
    }
}

impl<F: LedgerFile> Ledger<F> {
    /// 한 줄(JSON) 덧붙이고 fsync. 실패는 호출자에게 그대로 — 기록 없이 접속을 받지 않기 위해서다.
    /// 짧은 쓰기(디스크 가득 등)로 줄 앞부분만 써졌으면 쓰기 전 길이로 잘라 낸다 — 다음 진짜 줄이 그 조각에 이어 붙어
    /// 읽을 수 없게 되는 것을 막는다(독립 검증 D2). 잘라 내기도 실패하면 다음 줄을 줄바꿈으로 시작한다.
    /// 실패의 `kept_line` 은 fsync 실패(줄 전체가 쓰인 뒤)에서만 참이다 — 길이 읽기 실패·짧은 쓰기는 거짓.
    pub fn line(&mut self, value: &serde_json::Value) -> Result<(), LineError> {
        let mut s = String::new();
        if self.torn {
            s.push('\n');
        }
        s.push_str(&value.to_string());
        s.push('\n');
        let len0 = self.file.size().map_err(|error| LineError { error, kept_line: false })?;
        if let Err(error) = self.file.write_all(s.as_bytes()) {
            if self.file.truncate(len0).is_err() {
                self.torn = true;
            }
            return Err(LineError { error, kept_line: false });
        }
        self.torn = false;
        self.file.sync().map_err(|error| LineError { error, kept_line: true })
    }
}

/// 이 기동의 부팅 id(재부팅 뒤 pid 재사용과 구분하는 성분). 맥 = `kern.bootsessionuuid`.
pub fn boot_id() -> String {
    #[cfg(target_os = "macos")]
    {
        let mut buf = [0u8; 64];
        let mut len = buf.len();
        let name = b"kern.bootsessionuuid\0";
        let rc = unsafe {
            libc::sysctlbyname(
                name.as_ptr() as *const libc::c_char,
                buf.as_mut_ptr() as *mut libc::c_void,
                &mut len,
                std::ptr::null_mut(),
                0,
            )
        };
        if rc == 0 && len > 0 {
            return String::from_utf8_lossy(&buf[..len]).trim_end_matches('\0').to_string();
        }
        String::new()
    }
    #[cfg(not(target_os = "macos"))]
    {
        std::fs::read_to_string("/proc/sys/kernel/random/boot_id").map(|s| s.trim().to_string()).unwrap_or_default()
    }
}

/// 프로세스 시작 시각(마이크로초) — pid 재사용 판별 성분. 맥 = proc_pidinfo(PROC_PIDTBSDINFO).
pub fn process_start_us(pid: i32) -> Option<u64> {
    #[cfg(target_os = "macos")]
    {
        let mut info: libc::proc_bsdinfo = unsafe { std::mem::zeroed() };
        let size = std::mem::size_of::<libc::proc_bsdinfo>() as i32;
        let rc = unsafe {
            libc::proc_pidinfo(pid, libc::PROC_PIDTBSDINFO, 0, &mut info as *mut _ as *mut libc::c_void, size)
        };
        if rc != size {
            return None;
        }
        Some(info.pbi_start_tvsec * 1_000_000 + info.pbi_start_tvusec)
    }
    #[cfg(not(target_os = "macos"))]
    {
        let _ = pid;
        None
    }
}

pub fn now_epoch() -> f64 {
    std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).map(|d| d.as_secs_f64()).unwrap_or(0.0)
}

#[cfg(test)]
mod tests {
    use super::*;

    /// T3 실측 회귀: 좌석 여럿이 동시에 처음 뜨면 `seatkeep` 폴더 만들기가 경합해 한쪽이 `File exists` 로 rc 3 이었다.
    /// 같은 새 폴더에 8 스레드가 동시에 `ensure_dir` — 전부 성공해야 한다(30회).
    #[test]
    fn ensure_dir_is_race_safe_on_first_creation() {
        for round in 0..30 {
            let base = tmpdir(&format!("race{round}"));
            let barrier = std::sync::Arc::new(std::sync::Barrier::new(8));
            let hs: Vec<_> = (0..8)
                .map(|k| {
                    let (b, base) = (std::sync::Arc::clone(&barrier), base.clone());
                    std::thread::spawn(move || {
                        let p = Paths::new(&base, &format!("s{k}"));
                        b.wait();
                        p.ensure_dir()
                    })
                })
                .collect();
            for h in hs {
                h.join().unwrap().expect("동시 첫 만들기에서 실패");
            }
            let _ = std::fs::remove_dir_all(&base);
        }
    }

    fn tmpdir(tag: &str) -> PathBuf {
        let d = std::env::temp_dir().join(format!("sk-reg-{tag}-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&d);
        std::fs::create_dir_all(&d).unwrap();
        d
    }

    #[test]
    fn ledger_appends_and_keeps_old_lines() {
        let d = tmpdir("ledger");
        let p = d.join("x.log");
        Ledger::open(&p).unwrap().line(&serde_json::json!({"a": 1})).unwrap();
        Ledger::open(&p).unwrap().line(&serde_json::json!({"a": 2})).unwrap();
        let s = std::fs::read_to_string(&p).unwrap();
        assert_eq!(s.lines().count(), 2);
        assert!(s.starts_with("{\"a\":1}"));
        let _ = std::fs::remove_dir_all(&d);
    }

    #[test]
    fn ledger_reopen_after_fragment_starts_new_line() {
        // codex 2R #4 회귀: 앞 기동이 남긴 조각(줄바꿈 없음) 뒤 재기동 첫 줄은 조각에 이어 붙지 않는다.
        let d = tmpdir("frag");
        let p = d.join("x.log");
        std::fs::write(&p, "{\"event\":\"accept\",\"ge").unwrap();
        Ledger::open(&p).unwrap().line(&serde_json::json!({"event": "accept", "gen": 2})).unwrap();
        let s = std::fs::read_to_string(&p).unwrap();
        let ok: Vec<_> = s.lines().filter(|l| serde_json::from_str::<serde_json::Value>(l).is_ok()).collect();
        assert_eq!(ok.len(), 1, "온전한 줄 1개가 읽혀야 한다: {s:?}");
        let _ = std::fs::remove_dir_all(&d);
    }

    /// 실패 주입용 가짜 기록 파일(codex 3R #2 — fsync·길이 읽기·짧은 쓰기 실패를 구분하는 단위 시험).
    #[derive(Default)]
    struct FakeFile {
        buf: Vec<u8>,
        fail_size: bool,
        /// Some(n) = 앞으로 n 바이트만 써지고 그다음 쓰기는 ENOSPC.
        write_room: Option<usize>,
        fail_truncate: bool,
        fail_sync: bool,
    }

    impl Write for FakeFile {
        fn write(&mut self, b: &[u8]) -> std::io::Result<usize> {
            let n = match self.write_room {
                Some(0) => return Err(std::io::Error::from_raw_os_error(libc::ENOSPC)),
                Some(r) => b.len().min(r),
                None => b.len(),
            };
            if let Some(r) = self.write_room.as_mut() {
                *r -= n;
            }
            self.buf.extend_from_slice(&b[..n]);
            Ok(n)
        }
        fn flush(&mut self) -> std::io::Result<()> {
            Ok(())
        }
    }

    impl LedgerFile for FakeFile {
        fn size(&self) -> std::io::Result<u64> {
            if self.fail_size {
                return Err(std::io::Error::from_raw_os_error(libc::EIO));
            }
            Ok(self.buf.len() as u64)
        }
        fn truncate(&mut self, len: u64) -> std::io::Result<()> {
            if self.fail_truncate {
                return Err(std::io::Error::from_raw_os_error(libc::EIO));
            }
            self.buf.truncate(len as usize);
            Ok(())
        }
        fn sync(&mut self) -> std::io::Result<()> {
            if self.fail_sync {
                return Err(std::io::Error::from_raw_os_error(libc::EIO));
            }
            Ok(())
        }
    }

    fn fake_ledger() -> Ledger<FakeFile> {
        Ledger { file: FakeFile::default(), torn: false }
    }

    fn parsed_lines(b: &[u8]) -> usize {
        String::from_utf8_lossy(b).lines().filter(|l| serde_json::from_str::<serde_json::Value>(l).is_ok()).count()
    }

    #[test]
    fn line_fsync_failure_keeps_line() {
        let mut l = fake_ledger();
        l.file.fail_sync = true;
        let e = l.line(&serde_json::json!({"event": "accept"})).unwrap_err();
        assert!(e.kept_line, "fsync 만 실패 = 줄은 온전히 남았다");
        assert_eq!(parsed_lines(&l.file.buf), 1);
    }

    #[test]
    fn line_kept_flag_is_per_call() {
        // codex 3R #2 그 순서: fsync 실패(참) → 다음 기록 성공 → 다음 accept 가 길이 읽기에서 실패 = 거짓이어야 한다.
        let mut l = fake_ledger();
        l.file.fail_sync = true;
        assert!(l.line(&serde_json::json!({"n": 1})).unwrap_err().kept_line);
        l.file.fail_sync = false;
        l.line(&serde_json::json!({"n": 2})).unwrap();
        l.file.fail_size = true;
        let e = l.line(&serde_json::json!({"event": "accept"})).unwrap_err();
        assert!(!e.kept_line, "길이 읽기 실패 = 줄을 쓰지도 않았다");
        assert_eq!(parsed_lines(&l.file.buf), 2);
        // 반대 순서도: 길이 읽기 실패(거짓) 바로 뒤의 fsync 실패는 참.
        l.file.fail_size = false;
        l.file.fail_sync = true;
        assert!(l.line(&serde_json::json!({"n": 3})).unwrap_err().kept_line);
    }

    #[test]
    fn line_short_write_rolled_back_is_not_kept() {
        let mut l = fake_ledger();
        l.line(&serde_json::json!({"n": 1})).unwrap();
        let before = l.file.buf.clone();
        l.file.write_room = Some(5);
        let e = l.line(&serde_json::json!({"event": "accept", "gen": 2})).unwrap_err();
        assert!(!e.kept_line);
        assert_eq!(l.file.buf, before, "짧은 쓰기 조각은 잘라 낸다");
    }

    #[test]
    fn line_short_write_not_rolled_back_next_line_is_clean() {
        let mut l = fake_ledger();
        l.line(&serde_json::json!({"n": 1})).unwrap();
        l.file.write_room = Some(5);
        l.file.fail_truncate = true;
        let e = l.line(&serde_json::json!({"event": "accept", "gen": 2})).unwrap_err();
        assert!(!e.kept_line);
        l.file.write_room = None;
        l.line(&serde_json::json!({"n": 3})).unwrap();
        assert_eq!(parsed_lines(&l.file.buf), 2, "조각 뒤 다음 줄은 줄바꿈으로 시작해 읽힌다: {:?}", String::from_utf8_lossy(&l.file.buf));
    }

    #[test]
    fn atomic_write_replaces() {
        let d = tmpdir("atomic");
        let p = d.join("e.json");
        write_atomic(&p, &serde_json::json!({"phase": "prepare"})).unwrap();
        write_atomic(&p, &serde_json::json!({"phase": "committed"})).unwrap();
        assert!(std::fs::read_to_string(&p).unwrap().contains("committed"));
        let _ = std::fs::remove_dir_all(&d);
    }

    #[test]
    fn atomic_writes_to_sibling_files_do_not_collide() {
        // codex 1R #4 회귀: 같은 프로세스의 두 스레드가 <id>.json · <id>.exit 를 동시에 계속 써도 서로를 덮지 않는다.
        let d = tmpdir("collide");
        let (a, b) = (d.join("s.json"), d.join("s.exit"));
        let (a2, b2) = (a.clone(), b.clone());
        let t1 = std::thread::spawn(move || {
            for i in 0..300 {
                write_atomic(&a2, &serde_json::json!({"who": "entry", "i": i})).unwrap();
            }
        });
        let t2 = std::thread::spawn(move || {
            for i in 0..300 {
                write_atomic(&b2, &serde_json::json!({"who": "exit", "i": i})).unwrap();
            }
        });
        t1.join().unwrap();
        t2.join().unwrap();
        assert!(std::fs::read_to_string(&a).unwrap().contains("\"entry\""));
        assert!(std::fs::read_to_string(&b).unwrap().contains("\"exit\""));
        let left: Vec<_> = std::fs::read_dir(&d).unwrap().filter_map(|e| e.ok()).filter(|e| e.file_name().to_string_lossy().contains(".tmp.")).collect();
        assert!(left.is_empty(), "임시 파일이 남으면 안 된다");
        let _ = std::fs::remove_dir_all(&d);
    }

    #[test]
    fn id_lock_is_exclusive() {
        let d = tmpdir("idlock");
        let p = d.join("x.lock");
        let first = lock_id(&p).unwrap();
        assert!(lock_id(&p).is_err(), "두 번째는 거절");
        drop(first);
        // 같은 시험 프로세스의 다른 시험이 그 순간 fork 하면 자식이 exec 전까지 잠금 fd 사본(같은 열린 파일 = 같은 flock)을 잠깐 쥔다 —
        // 놓임은 곧 온다. 최대 2초 다시 시도(seatkeep-t3-fix2: 자식을 띄우는 시험이 늘어 부하에서 1/3 실패 관측 · 2026-11-13).
        let t = std::time::Instant::now();
        let mut again = lock_id(&p);
        while again.is_err() && t.elapsed() < std::time::Duration::from_secs(2) {
            std::thread::sleep(std::time::Duration::from_millis(20));
            again = lock_id(&p);
        }
        assert!(again.is_ok(), "첫째가 놓으면 다시 잡힌다");
        let _ = std::fs::remove_dir_all(&d);
    }

    #[test]
    fn dir_is_owner_only() {
        let d = tmpdir("perm");
        let paths = Paths::new(&d, "s1");
        paths.ensure_dir().unwrap();
        let mode = std::fs::metadata(&paths.dir).unwrap().permissions().mode() & 0o777;
        assert_eq!(mode, 0o700);
        let _ = std::fs::remove_dir_all(&d);
    }

    #[cfg(target_os = "macos")]
    #[test]
    fn own_start_time_is_readable() {
        assert!(process_start_us(std::process::id() as i32).is_some());
        assert!(!boot_id().is_empty());
    }
}
