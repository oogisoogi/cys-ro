//! 디렉터리 **핸들 기준** 파일 연산(unix · libc 직호출) — 경로를 다시 해석하지 않는 rename·제거.
//!
//! ★왜 있나(codex 1R · TICKET=cysr-1110-trash-harden B2·M4): 경로로 검사하고 경로로 집행하면 그 사이
//! 같은 UID 프로세스가 뿌리·부모를 심링크로 바꿔쳐 **검사하지 않은 객체**에 rename·제거가 닿는다(TOCTOU).
//! 여기 연산은 열어 둔 디렉터리 핸들에 묶이고(`fstatat`·`renameat`·`openat`·`unlinkat`), 디렉터리
//! 열기는 전부 `O_NOFOLLOW` 다(`open_dir_follow` 만 예외 — 부모 경로의 정상 심링크용이며 호출자가
//! 연 뒤 신원을 대조한다). 도메인 개념(휴지통·초기화)을 모르는 leaf 다.
//! ★윈도우: 안정 std 에 대응 API(openat 계열·file index)가 없다 — 이 모듈은 unix 전용이고, 호출자가
//! 윈도우 경로에 그 한계를 표식으로 적는다.
use std::ffi::{CStr, CString};
use std::io;
use std::os::fd::{AsFd, AsRawFd, BorrowedFd, FromRawFd, OwnedFd};
use std::os::unix::ffi::OsStrExt as _;
use std::path::Path;

const DIR_FLAGS: libc::c_int =
    libc::O_RDONLY | libc::O_DIRECTORY | libc::O_NOFOLLOW | libc::O_CLOEXEC;

fn cstr(b: &[u8]) -> io::Result<CString> {
    CString::new(b).map_err(|_| io::Error::from(io::ErrorKind::InvalidInput))
}
fn check(rc: libc::c_int) -> io::Result<libc::c_int> {
    if rc < 0 {
        Err(io::Error::last_os_error())
    } else {
        Ok(rc)
    }
}
pub fn id_of(st: &libc::stat) -> (u64, u64) {
    (st.st_dev as u64, st.st_ino as u64)
}
fn is_dir(st: &libc::stat) -> bool {
    (st.st_mode & libc::S_IFMT) == libc::S_IFDIR
}
/// 디렉터리를 연다 — 마지막 성분이 심링크거나 디렉터리가 아니면 실패한다.
pub fn open_dir(p: &Path) -> io::Result<OwnedFd> {
    let c = cstr(p.as_os_str().as_bytes())?;
    let fd = check(unsafe { libc::open(c.as_ptr(), DIR_FLAGS) })?;
    Ok(unsafe { OwnedFd::from_raw_fd(fd) })
}
/// 디렉터리를 **따라가며** 연다(경로의 정상 심링크 — 예: macOS `/var` → `/private/var`).
/// ★호출자는 연 뒤 `id_of(&fstat(..))` 로 계획 때의 신원과 대조해야 한다 — 대조 없이 쓰지 마라.
pub fn open_dir_follow(p: &Path) -> io::Result<OwnedFd> {
    let c = cstr(p.as_os_str().as_bytes())?;
    let fd = check(unsafe {
        libc::open(c.as_ptr(), libc::O_RDONLY | libc::O_DIRECTORY | libc::O_CLOEXEC)
    })?;
    Ok(unsafe { OwnedFd::from_raw_fd(fd) })
}
fn open_dir_at(dir: BorrowedFd, name: &[u8]) -> io::Result<OwnedFd> {
    let c = cstr(name)?;
    let fd = check(unsafe { libc::openat(dir.as_raw_fd(), c.as_ptr(), DIR_FLAGS) })?;
    Ok(unsafe { OwnedFd::from_raw_fd(fd) })
}
pub fn fstat(fd: &OwnedFd) -> io::Result<libc::stat> {
    let mut st: libc::stat = unsafe { std::mem::zeroed() };
    check(unsafe { libc::fstat(fd.as_raw_fd(), &mut st) })?;
    Ok(st)
}
pub fn lstat_at(dir: &impl AsFd, name: &[u8]) -> io::Result<libc::stat> {
    let c = cstr(name)?;
    let mut st: libc::stat = unsafe { std::mem::zeroed() };
    check(unsafe {
        libc::fstatat(dir.as_fd().as_raw_fd(), c.as_ptr(), &mut st, libc::AT_SYMLINK_NOFOLLOW)
    })?;
    Ok(st)
}
pub fn rename_at(dir: &OwnedFd, from: &[u8], to: &[u8]) -> io::Result<()> {
    rename_between(dir, from, dir, to)
}
/// 두 핸들 사이 rename(`renameat`) — 원본·목적지 모두 이름 한 성분이다(경로 재해석 없음).
pub fn rename_between(src: &OwnedFd, from: &[u8], dst: &OwnedFd, to: &[u8]) -> io::Result<()> {
    let (f, t) = (cstr(from)?, cstr(to)?);
    check(unsafe { libc::renameat(src.as_raw_fd(), f.as_ptr(), dst.as_raw_fd(), t.as_ptr()) })
        .map(|_| ())
}
fn unlink_at(dir: BorrowedFd, name: &[u8], is_dir: bool) -> io::Result<()> {
    let c = cstr(name)?;
    let flag = if is_dir { libc::AT_REMOVEDIR } else { 0 };
    check(unsafe { libc::unlinkat(dir.as_raw_fd(), c.as_ptr(), flag) }).map(|_| ())
}
/// 디렉터리 핸들의 자식 이름 전수(`.`·`..` 제외). 먼저 다 읽고 지운다 — 읽는 중에 지우면
/// readdir 결과가 POSIX 상 미정이다. ★readdir 의 오류와 끝은 구별하지 않는다: 덜 읽혔다면
/// 마지막 `unlinkat(AT_REMOVEDIR)` 가 ENOTEMPTY 로 실패해 **오류로 올라온다**(더 지우는 쪽이 아니다).
fn list(dir: BorrowedFd) -> io::Result<Vec<Vec<u8>>> {
    let dup = check(unsafe { libc::fcntl(dir.as_raw_fd(), libc::F_DUPFD_CLOEXEC, 0) })?;
    let dp = unsafe { libc::fdopendir(dup) };
    if dp.is_null() {
        let e = io::Error::last_os_error();
        unsafe { libc::close(dup) };
        return Err(e);
    }
    let mut out = Vec::new();
    loop {
        let ent = unsafe { libc::readdir(dp) };
        if ent.is_null() {
            break;
        }
        let n = unsafe { CStr::from_ptr((*ent).d_name.as_ptr()) }.to_bytes();
        if n != b"." && n != b".." {
            out.push(n.to_vec());
        }
    }
    unsafe { libc::closedir(dp) };
    Ok(out)
}
/// 하위 내용 제거 — 디렉터리는 `O_NOFOLLOW` 로 열고 장치가 `dev` 와 다르면 **멈춘다**
/// (인증이 본 집합을 넓히지 않는다 · C-R1 을 구조로 지킨다). 심링크는 링크 자체만 지운다.
fn remove_contents(dir: BorrowedFd, dev: u64) -> io::Result<()> {
    for n in list(dir)? {
        let st = lstat_at(&dir, &n)?;
        if is_dir(&st) {
            let sub = open_dir_at(dir, &n)?;
            if id_of(&fstat(&sub)?).0 != dev {
                return Err(io::Error::other("장치 경계를 만났다 — 제거를 멈춘다"));
            }
            remove_contents(sub.as_fd(), dev)?;
            drop(sub);
            unlink_at(dir, &n, true)?;
        } else {
            unlink_at(dir, &n, false)?;
        }
    }
    Ok(())
}
/// `parent` 아래 `name` 을 통째로 지운다 — 연 객체의 신원이 `expect` 가 아니면 아무것도 지우지 않는다.
pub fn remove_tree_at(parent: &OwnedFd, name: &[u8], expect: (u64, u64)) -> io::Result<()> {
    let fd = open_dir_at(parent.as_fd(), name)?;
    if id_of(&fstat(&fd)?) != expect {
        return Err(io::Error::other("연 객체가 미리보기의 항목이 아니다 — 지우지 않는다"));
    }
    remove_contents(fd.as_fd(), expect.0)?;
    drop(fd);
    // 마지막 rmdir 직전 — 그 이름이 아직 그 객체인가(바꿔친 빈 디렉터리를 지우지 않는다).
    if id_of(&lstat_at(parent, name)?) != expect {
        return Err(io::Error::other("마지막 단계에서 이름이 다른 객체를 가리킨다 — 멈춘다"));
    }
    unlink_at(parent.as_fd(), name, true)
}
