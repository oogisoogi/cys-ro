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

    pub fn ensure_dir(&self) -> std::io::Result<()> {
        std::fs::create_dir_all(&self.dir)?;
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
    let f = OpenOptions::new().read(true).write(true).create(true).mode(0o600).open(path)?;
    if unsafe { libc::flock(f.as_raw_fd(), libc::LOCK_EX | libc::LOCK_NB) } != 0 {
        return Err(std::io::Error::last_os_error());
    }
    Ok(f)
}

/// 교체 기록. 덧붙이기 전용 열기 — 이 프로세스는 자기 기록을 고쳐 쓸 수 없다.
pub struct Ledger {
    file: File,
}

impl Ledger {
    pub fn open(path: &Path) -> std::io::Result<Ledger> {
        let file = OpenOptions::new().append(true).create(true).mode(0o600).open(path)?;
        Ok(Ledger { file })
    }

    /// 한 줄(JSON) 덧붙이고 fsync. 실패는 호출자에게 그대로 — 기록 없이 접속을 받지 않기 위해서다.
    pub fn line(&mut self, value: &serde_json::Value) -> std::io::Result<()> {
        let mut s = value.to_string();
        s.push('\n');
        self.file.write_all(s.as_bytes())?;
        self.file.sync_data()
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
        assert!(lock_id(&p).is_ok(), "첫째가 놓으면 다시 잡힌다");
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
