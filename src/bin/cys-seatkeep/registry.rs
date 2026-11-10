//! seatkeep 등록부 · 교체 기록 · 종료 기록 — T2 시제품(DESIGN.md §4-1 · master 판단 11-11 ②).
//!
//! 파일(모두 `<dir>/seatkeep/` 아래 · 폴더 0700):
//! - `<id>.json`  등록부 항목. 「준비(prepare)」 → 「확정(committed)」 → 「끝남(exited)」. 원자적 교체(임시 파일 + rename).
//! - `<id>.log`   조종자 받기·끊김·거절 기록. **덧붙이기 전용으로만 연다**(O_APPEND). 쓰기 실패 = 접속을 받지 않는다.
//! - `<id>.exit`  자식 종료 기록. 조종자의 EXIT_ACK 까지 보존(받으면 지운다 · 못 받으면 남겨 새 조종자가 소비).
//! - `<id>.sock`  조종자 접속 소켓(0600).

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
}

impl Paths {
    pub fn new(state_dir: &Path, id: &str) -> Paths {
        let dir = state_dir.join("seatkeep");
        Paths {
            entry: dir.join(format!("{id}.json")),
            log: dir.join(format!("{id}.log")),
            exit: dir.join(format!("{id}.exit")),
            sock: dir.join(format!("{id}.sock")),
            dir,
        }
    }

    pub fn ensure_dir(&self) -> std::io::Result<()> {
        std::fs::create_dir_all(&self.dir)?;
        std::fs::set_permissions(&self.dir, std::fs::Permissions::from_mode(0o700))
    }
}

/// 임시 파일에 쓰고 fsync 뒤 rename — 읽는 쪽은 옛 내용이나 새 내용 중 하나만 본다.
pub fn write_atomic(path: &Path, value: &serde_json::Value) -> std::io::Result<()> {
    let tmp = path.with_extension(format!("tmp.{}", std::process::id()));
    {
        let mut f = OpenOptions::new().write(true).create(true).truncate(true).mode(0o600).open(&tmp)?;
        f.write_all(value.to_string().as_bytes())?;
        f.sync_all()?;
    }
    std::fs::rename(&tmp, path)
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
