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
/// errno 를 0 으로 놓는다 — `readdir` 의 끝(NULL·errno 0)과 오류(NULL·errno≠0)를 가르기 위해서다.
fn clear_errno() {
    #[cfg(any(target_os = "macos", target_os = "ios", target_os = "freebsd"))]
    unsafe {
        *libc::__error() = 0;
    }
    #[cfg(any(target_os = "linux", target_os = "android"))]
    unsafe {
        *libc::__errno_location() = 0;
    }
}
/// 디렉터리 핸들의 자식 이름 전수(`.`·`..` 제외). 먼저 다 읽고 지운다 — 읽는 중에 지우면
/// readdir 결과가 POSIX 상 미정이다. 열거 오류(errno≠0)와 `closedir` 실패는 `Err` 다(codex 1R minor).
fn list(dir: BorrowedFd) -> io::Result<Vec<Vec<u8>>> {
    let dup = check(unsafe { libc::fcntl(dir.as_raw_fd(), libc::F_DUPFD_CLOEXEC, 0) })?;
    let dp = unsafe { libc::fdopendir(dup) };
    if dp.is_null() {
        let e = io::Error::last_os_error();
        unsafe { libc::close(dup) };
        return Err(e);
    }
    let mut out = Vec::new();
    let mut err: Option<io::Error> = None;
    loop {
        clear_errno();
        let ent = unsafe { libc::readdir(dp) };
        if ent.is_null() {
            let e = io::Error::last_os_error();
            if e.raw_os_error().unwrap_or(0) != 0 {
                err = Some(e);
            }
            break;
        }
        let n = unsafe { CStr::from_ptr((*ent).d_name.as_ptr()) }.to_bytes();
        if n != b"." && n != b".." {
            out.push(n.to_vec());
        }
    }
    // closedir 는 dup 한 fd 를 닫는다(소유권이 DIR 로 넘어갔다 — 따로 close 하지 않는다).
    if unsafe { libc::closedir(dp) } != 0 && err.is_none() {
        err = Some(io::Error::last_os_error());
    }
    match err {
        Some(e) => Err(e),
        None => Ok(out),
    }
}
/// 하위 내용 제거. ★인증 집합 = 제거 집합(C-R1 · codex 1R major): 노드마다 (dev, ino) 가 `allow`
/// (호출자가 인증 순회에서 모은 신원 집합)에 있어야 지운다 — 인증 뒤 끼어든 객체(밖에서 옮겨 넣은
/// 트리·새 파일)를 만나면 **그 자리에서 멈춘다**. 디렉터리는 `O_NOFOLLOW` 로 열고, 연 객체의 신원이
/// 직전 `lstat` 의 신원과 같아야 하며(사이 바꿔치기), 장치가 `dev` 와 다르면 멈춘다. 심링크는 링크 자체만.
/// ★남는 창(정직): 파일은 `lstat` 대조와 `unlinkat` 사이에 이름이 바뀌면 다른 객체를 지울 수 있다 —
/// POSIX 에 「이 inode 일 때만 unlink」가 없다. 그 객체는 같은 UID 가 **봉인된 트리 안으로** 옮겨 넣은
/// 것이어야 한다(경로 바꿔치기로 트리 밖에 닿는 길은 위 핸들 결박이 닫는다).
fn remove_contents(dir: BorrowedFd, dev: u64, allow: &dyn Fn((u64, u64)) -> bool) -> io::Result<()> {
    for n in list(dir)? {
        let st = lstat_at(&dir, &n)?;
        if !allow(id_of(&st)) {
            return Err(io::Error::other("인증 집합에 없는 객체를 만났다 — 제거를 멈춘다"));
        }
        if is_dir(&st) {
            let sub = open_dir_at(dir, &n)?;
            let sid = id_of(&fstat(&sub)?);
            if sid != id_of(&st) {
                return Err(io::Error::other("연 디렉터리가 확인한 객체가 아니다 — 제거를 멈춘다"));
            }
            if sid.0 != dev {
                return Err(io::Error::other("장치 경계를 만났다 — 제거를 멈춘다"));
            }
            remove_contents(sub.as_fd(), dev, allow)?;
            drop(sub);
            #[cfg(test)]
            if let Some(h) = *BEFORE_SUBDIR_RMDIR.lock().unwrap() {
                h(&dir, &n);
            }
            // ★codex 2R — 비운 뒤 rmdir **직전** 그 이름이 아직 그 객체인가(재귀 중 바꿔 넣은 빈
            //   디렉터리를 지우지 않는다 · 뿌리의 마지막 대조와 같은 규칙).
            if id_of(&lstat_at(&dir, &n)?) != sid {
                return Err(io::Error::other("rmdir 직전 이름이 다른 객체를 가리킨다 — 제거를 멈춘다"));
            }
            unlink_at(dir, &n, true)?;
        } else {
            unlink_at(dir, &n, false)?;
        }
    }
    Ok(())
}
/// `parent` 아래 `name` 을 통째로 지운다 — 연 객체의 신원이 `expect` 가 아니면 아무것도 지우지 않고,
/// 하위 노드는 `allow` 에 든 신원만 지운다(위 `remove_contents`).
pub fn remove_tree_at(
    parent: &OwnedFd,
    name: &[u8],
    expect: (u64, u64),
    allow: &dyn Fn((u64, u64)) -> bool,
) -> io::Result<()> {
    let fd = open_dir_at(parent.as_fd(), name)?;
    if id_of(&fstat(&fd)?) != expect {
        return Err(io::Error::other("연 객체가 미리보기의 항목이 아니다 — 지우지 않는다"));
    }
    remove_contents(fd.as_fd(), expect.0, allow)?;
    drop(fd);
    // 마지막 rmdir 직전 — 그 이름이 아직 그 객체인가(바꿔친 빈 디렉터리를 지우지 않는다).
    if id_of(&lstat_at(parent, name)?) != expect {
        return Err(io::Error::other("마지막 단계에서 이름이 다른 객체를 가리킨다 — 멈춘다"));
    }
    unlink_at(parent.as_fd(), name, true)
}
/// `dir` 아래 `name` 을 추가 쓰기로 연다(없으면 0644 로 만든다 · 마지막 성분이 심링크면 실패).
pub fn open_append_at(dir: &OwnedFd, name: &[u8]) -> io::Result<std::fs::File> {
    let c = cstr(name)?;
    let flags = libc::O_WRONLY | libc::O_CREAT | libc::O_APPEND | libc::O_NOFOLLOW | libc::O_CLOEXEC;
    let fd = check(unsafe { libc::openat(dir.as_raw_fd(), c.as_ptr(), flags, 0o644 as libc::c_uint) })?;
    Ok(std::fs::File::from(unsafe { OwnedFd::from_raw_fd(fd) }))
}
/// `dir` 아래 `name` 을 원자 교체로 쓴다 — 임시 이름을 `O_EXCL` 로 만들고 fsync 뒤 같은 핸들 안에서
/// `renameat`. 실패하면 임시 파일을 지운다.
pub fn write_atomic_at(dir: &OwnedFd, name: &[u8], bytes: &[u8]) -> io::Result<()> {
    use std::io::Write as _;
    use std::sync::atomic::{AtomicU64, Ordering};
    static SEQ: AtomicU64 = AtomicU64::new(0);
    let flags = libc::O_WRONLY | libc::O_CREAT | libc::O_EXCL | libc::O_NOFOLLOW | libc::O_CLOEXEC;
    // 이름이 이미 있으면(남이 둔 것 · 죽은 같은 pid 의 잔재) 새 번호로 몇 번 더 — 남의 파일은 건드리지 않는다.
    let mut attempt = 0;
    let (tmp, fd) = loop {
        let mut tmp = b".".to_vec();
        tmp.extend_from_slice(name);
        tmp.extend_from_slice(
            format!(".tmp-{}-{}", std::process::id(), SEQ.fetch_add(1, Ordering::Relaxed)).as_bytes(),
        );
        let c = cstr(&tmp)?;
        match check(unsafe { libc::openat(dir.as_raw_fd(), c.as_ptr(), flags, 0o644 as libc::c_uint) }) {
            Ok(fd) => break (tmp, fd),
            Err(e) if e.kind() == io::ErrorKind::AlreadyExists && attempt < 8 => attempt += 1,
            Err(e) => return Err(e),
        }
    };
    let mut f = std::fs::File::from(unsafe { OwnedFd::from_raw_fd(fd) });
    let r = f.write_all(bytes).and_then(|_| f.sync_all()).and_then(|_| rename_at(dir, &tmp, name));
    if r.is_err() {
        let _ = unlink_at(dir.as_fd(), &tmp, false);
    }
    r
}
/// 경로가 **지금** 이 핸들의 객체인가(마지막 성분이 심링크면 아니다). 경로로만 쓸 수 있는 자리의
/// 직전 대조용이다 — 대조와 쓰기 사이의 창은 남는다(호출자가 그 한계를 적는다).
pub fn path_is(dir: &OwnedFd, p: &Path) -> bool {
    match (std::fs::symlink_metadata(p), fstat(dir)) {
        (Ok(md), Ok(st)) => {
            use std::os::unix::fs::MetadataExt as _;
            !md.file_type().is_symlink() && (md.dev(), md.ino()) == id_of(&st)
        }
        _ => false,
    }
}

/// 시험 전용 — 하위 디렉터리를 비운 뒤 rmdir 직전에 끼어드는 자리(경쟁 시점을 시험이 정한다).
#[cfg(test)]
static BEFORE_SUBDIR_RMDIR: std::sync::Mutex<Option<fn(&BorrowedFd, &[u8])>> = std::sync::Mutex::new(None);

#[cfg(test)]
mod tests {
    use super::*;

    /// ★codex 2R — 재귀로 비우는 사이 그 이름을 **인증하지 않은 빈 디렉터리**로 바꿔 넣으면, 마지막
    /// rmdir 이 바꿔 넣은 쪽을 지우면 안 된다(멈추고 둘 다 남는다).
    #[test]
    fn a_subdir_swapped_during_emptying_is_not_rmdired() {
        let td = std::env::temp_dir().join(format!("cys-dirat-subswap-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&td);
        std::fs::create_dir_all(td.join("root/a")).unwrap();
        std::fs::write(td.join("root/a/f"), b"x").unwrap();
        fn swap(dir: &BorrowedFd, n: &[u8]) {
            if n == b"a" {
                let (a, b) = (cstr(b"a").unwrap(), cstr(b"a-away").unwrap());
                unsafe { libc::renameat(dir.as_raw_fd(), a.as_ptr(), dir.as_raw_fd(), b.as_ptr()) };
                unsafe { libc::mkdirat(dir.as_raw_fd(), a.as_ptr(), 0o755) };
            }
        }
        let parent = open_dir(&td).unwrap();
        let want = id_of(&lstat_at(&parent, b"root").unwrap());
        *BEFORE_SUBDIR_RMDIR.lock().unwrap() = Some(swap);
        let r = remove_tree_at(&parent, b"root", want, &|_| true);
        *BEFORE_SUBDIR_RMDIR.lock().unwrap() = None;
        let e = r.expect_err("바꿔 넣은 디렉터리를 지웠다");
        assert!(e.to_string().contains("rmdir 직전"), "{e}");
        assert!(td.join("root/a").is_dir(), "바꿔 넣은 빈 디렉터리가 사라졌다");
        assert!(td.join("root/a-away").is_dir());
        let _ = std::fs::remove_dir_all(&td);
    }
}
