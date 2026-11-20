//! TICKET=cysr-seatkeep-t3 · 좌석 프로세스 손잡이 단위 시험 — 노브 · 잠금 파일 형식(노브 끔 = 바이트까지 그대로) · 첫 칸 판독기 ·
//! 감사 토큰 경로 규칙(번들 주 실행 파일 = 번들 경로 · 실제 Security 프레임워크 대조).

use crate::seat_proc::*;

/// T6b D1 ⓐ: 업데이트 뒤 옛 번들 자리의 seatkeep 만 같은 신원 — 꼴이 정확해야 하고 부모 폴더가 같아야 한다.
#[test]
fn seatkeep_exe_ok_allows_only_sibling_old_bundle() {
    let p = |s: &str| std::path::PathBuf::from(s);
    let want = p("/Applications/cysr.app/Contents/MacOS/cys-seatkeep");
    assert!(seatkeep_exe_ok(&want, &want));
    assert!(seatkeep_exe_ok(&p("/Applications/.cysr.app.old-12/Contents/MacOS/cys-seatkeep"), &want));
    for bad in [
        "/Applications/.cysr.app.old-/Contents/MacOS/cys-seatkeep",
        "/Applications/.cysr.app.old-1x/Contents/MacOS/cys-seatkeep",
        "/Applications/.cysr.app.new-12/Contents/MacOS/cys-seatkeep",
        "/Users/x/.cysr.app.old-12/Contents/MacOS/cys-seatkeep",
        "/Applications/.cysr.app.old-12/Contents/MacOS/cysd",
        "/Applications/.cysr.app.old-12/Contents/Resources/cys-seatkeep",
        "/Applications/other.app/Contents/MacOS/cys-seatkeep",
    ] {
        assert!(!seatkeep_exe_ok(&p(bad), &want), "{bad}");
    }
    // 개발 빌드(번들 밖) = 정확히 같은 경로만.
    let dev = p("/w/target/debug/cys-seatkeep");
    assert!(!seatkeep_exe_ok(&p("/w/.cysr.app.old-1/Contents/MacOS/cys-seatkeep"), &dev));
}

/// T6a holder 상한 env 판정: 양의 정수만 · 그 밖 = 기본.
#[test]
fn holder_cap_env_parse() {
    assert_eq!(holder_cap_from(None), HOLDER_CAP_DEFAULT);
    assert_eq!(holder_cap_from(Some("1")), 1);
    assert_eq!(holder_cap_from(Some(" 8 ")), 8);
    assert_eq!(holder_cap_from(Some("0")), HOLDER_CAP_DEFAULT);
    assert_eq!(holder_cap_from(Some("x")), HOLDER_CAP_DEFAULT);
    assert_eq!(holder_cap_from(Some("-3")), HOLDER_CAP_DEFAULT);
}

#[test]
fn knob_only_exact_one_turns_on() {
    for (v, want) in [(None, false), (Some(""), false), (Some("0"), false), (Some("true"), false), (Some("yes"), false),
                      (Some("2"), false), (Some("1"), true), (Some(" 1 "), true), (Some("1\n"), true)] {
        assert_eq!(seatkeep_enabled_from(v), want, "{v:?}");
    }
}

/// 노브 끔 = 잠금 파일 내용이 지금과 바이트까지 같다(master#c125bc97 ①) · 켬 = `pid 출생시각µs`(seatkeep 짝 대조와 같은 값).
#[cfg(unix)]
#[test]
fn lock_record_is_one_field_unless_knob_on() {
    let pid = std::process::id();
    assert_eq!(crate::deadman::lock_record(pid, false), pid.to_string(), "노브 끔 = 옛 형식 그대로");
    let two = crate::deadman::lock_record(pid, true);
    let mut it = two.split_whitespace();
    assert_eq!(it.next(), Some(pid.to_string().as_str()));
    let start: u64 = it.next().expect("둘째 칸").parse().expect("숫자");
    #[cfg(target_os = "macos")]
    {
        let mut info: libc::proc_bsdinfo = unsafe { std::mem::zeroed() };
        let size = std::mem::size_of::<libc::proc_bsdinfo>() as i32;
        let rc = unsafe { libc::proc_pidinfo(pid as i32, libc::PROC_PIDTBSDINFO, 0, (&mut info as *mut libc::proc_bsdinfo).cast(), size) };
        assert_eq!(rc, size);
        assert_eq!(start, info.pbi_start_tvsec * 1_000_000 + info.pbi_start_tvusec, "seatkeep registry::process_start_us 와 같은 식");
    }
    let _ = start;
    assert!(it.next().is_none());
}

/// 실제 잠금 쓰기(`claim_lock`)가 노브에 따라 쓰는 바이트 — 이 시험 프로세스의 노브 값 그대로 대조한다(끔 = 한 칸).
#[cfg(unix)]
#[test]
fn claim_lock_bytes_follow_knob() {
    let d = std::env::temp_dir().join(format!("cys-t3-claim-{}-{}", std::process::id(), crate::state::now_epoch().to_bits() % 1_000_000));
    std::fs::create_dir_all(&d).unwrap();
    let lock = d.join("cys.lock");
    let mut f = std::fs::OpenOptions::new().create(true).write(true).read(true).open(&lock).unwrap();
    std::fs::write(&lock, "999999 123 garbage-longer-than-new").unwrap();
    crate::deadman::claim_lock(&mut f, &d);
    let text = std::fs::read_to_string(&lock).unwrap();
    let pid = std::process::id();
    if seatkeep_enabled() {
        assert!(text.starts_with(&format!("{pid} ")), "노브 켬 = 두 칸: {text:?}");
    } else {
        assert_eq!(text.as_bytes(), pid.to_string().as_bytes(), "노브 끔 = 바이트까지 옛 형식(앞 내용 잔재 0)");
    }
    assert_eq!(crate::deadman::read_holder_pid(&lock), Some(pid));
    let _ = std::fs::remove_dir_all(&d);
}

/// 독자 4곳이 같이 쓰는 첫 칸 판독기 — 옛 한 칸 · 새 두 칸 · 빈 파일 · 0 · 쓰레기.
#[test]
fn startup_lock_holder_pid_reads_first_field() {
    for (t, want) in [("4242", Some(4242)), ("  4242 \n", Some(4242)), ("4242 1731234567123456", Some(4242)),
                      ("4242 1731234567123456\n", Some(4242)), ("", None), ("0", None), ("0 123", None),
                      ("garbage", None), ("-1 2", None), ("4242x 1", None)] {
        assert_eq!(cys::startup_lock_holder_pid(t), want, "{t:?}");
    }
}

#[test]
fn seatkeep_exe_is_beside_cysd() {
    let p = seatkeep_exe_beside(std::path::Path::new("/Applications/cys.app/Contents/MacOS/cysd")).unwrap();
    assert_eq!(p, std::path::PathBuf::from("/Applications/cys.app/Contents/MacOS/cys-seatkeep"));
    let p = seatkeep_exe_beside(std::path::Path::new("/w/target/debug/cysd")).unwrap();
    assert_eq!(p, std::path::PathBuf::from("/w/target/debug/cys-seatkeep"));
    // 시험 빌드: 시험 실행 파일은 deps/ 안 → 한 단계 위
    let p = seatkeep_exe_beside(std::path::Path::new("/w/target/debug/deps/cysd-0123abcd")).unwrap();
    assert_eq!(p, std::path::PathBuf::from("/w/target/debug/cys-seatkeep"));
    // 새 배치(cargo 1.100 · TICKET=cysr-1116-maccysd-1121): 시험 실행 파일은 build/<패키지>/<해시>/out/ 안 → 프로필 폴더
    let p = seatkeep_exe_beside(std::path::Path::new("/w/target/debug/build/cys-terminal/17a9bf680c75da2b/out/cysd-17a9bf680c75da2b")).unwrap();
    assert_eq!(p, std::path::PathBuf::from("/w/target/debug/cys-seatkeep"));
    // 이름만 닮은 자리는 그대로(out 위가 build/<x>/<y> 꼴이 아님)
    let p = seatkeep_exe_beside(std::path::Path::new("/w/x/out/cysd")).unwrap();
    assert_eq!(p, std::path::PathBuf::from("/w/x/out/cys-seatkeep"));
}

fn fake_bundle(root: &std::path::Path, app: &str, exe: &str, plist_exe: Option<&str>) -> std::path::PathBuf {
    let macos = root.join(app).join("Contents/MacOS");
    std::fs::create_dir_all(&macos).unwrap();
    if let Some(name) = plist_exe {
        std::fs::write(
            root.join(app).join("Contents/Info.plist"),
            format!("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<plist version=\"1.0\">\n<dict>\n\t<key>CFBundleIdentifier</key>\n\t<string>local.cys.t3.fake</string>\n\t<key>CFBundleExecutable</key>\n\t<string>{name}</string>\n</dict>\n</plist>\n"),
        )
        .unwrap();
    }
    macos.join(exe)
}

#[test]
fn audit_code_path_rule() {
    let root = std::env::temp_dir().join(format!("cys-t3-bundle-{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&root);
    let main = fake_bundle(&root, "Fake.app", "fakemain", Some("fakemain"));
    assert_eq!(audit_code_path(&main), root.join("Fake.app"), "주 실행 파일 = 번들 경로");
    let helper = root.join("Fake.app/Contents/MacOS/helper");
    assert_eq!(audit_code_path(&helper), helper, "같은 MacOS 폴더의 다른 실행 파일(cysd 꼴) = 실행 파일 경로");
    let noplist = fake_bundle(&root, "NoPlist.app", "x", None);
    assert_eq!(audit_code_path(&noplist), noplist, "Info.plist 없음 = 실행 파일 경로");
    let notapp = root.join("Plain/Contents/MacOS/x");
    assert_eq!(audit_code_path(&notapp), notapp, ".app 아님 = 실행 파일 경로");
    let plain = std::path::Path::new("/w/target/debug/cysd");
    assert_eq!(audit_code_path(plain), plain.to_path_buf());
    let _ = std::fs::remove_dir_all(&root);
}

/// 규칙이 **실제 Security 프레임워크**(seatkeep 이 감사 토큰으로 쓰는 같은 API 계열)와 맞는가 — T2 가 본 Homebrew 파이썬 모양
/// (`…/Python.app/Contents/MacOS/Python` → `…/Python.app`)을 가짜 번들로 재현한다(번들 주 실행 파일 · 번들 안 비주 실행 파일 · 번들 밖).
///
/// ⛔**가짜 실행 파일을 실행하지 않는다**(TICKET=cysr-test-gatekeeper-crash-1118). 옛 판은 `/bin/sleep` 을 임시 폴더에 복사 → 실행 →
/// kill → 폴더 삭제를 매 실행 반복했다 — 복사본은 실행마다 「Code Signature Invalid」로 죽었고, 맥 보안 검사(syspolicyd)가 새 실행
/// 파일을 검사하는 도중 파일이 지워져 syspolicyd 가 SIGSEGV 로 죽고 → tccd·WindowServer 가 그것을 기다리다 맥이 멈췄다(11-18).
/// 그래서 지금은 ① 가짜 번들 = 정적 코드 객체(`SecStaticCodeCreateWithPath` · 실행 없음 · syspolicyd 를 부르지 않음)로 경로를
/// 읽고 ② 가짜 번들 파일은 target 아래 고정 자리에 한 번만 만들고 지우지 않는다 ③ 실행 경로(pid → 코드 객체) 쪽은 제자리
/// `/bin/sleep`(새로 만든 파일 아님) 한 번으로 「동적 답 = 정적 답 = 규칙」을 잇는다.
/// 잃는 것: 번들 주 실행 파일을 **실행 중인 프로세스로** pid 경로에서 대조하는 것(정적 경로와 같은 판정 규칙을 쓴다는 가정에 기댄다).
#[cfg(target_os = "macos")]
#[test]
fn audit_code_path_matches_security_framework() {
    let canon = |p: &std::path::Path| std::fs::canonicalize(p).unwrap_or_else(|_| p.to_path_buf());
    let root = secpath_fixture_root();
    let main = root.join("Fake.app/Contents/MacOS/fakemain");
    let helper = root.join("Fake.app/Contents/MacOS/fakehelper");
    let plain = root.join("plain/fakeplain");
    for exe in [&main, &helper, &plain] {
        let got = sec::static_code_path(exe).expect("Security 프레임워크가 정적 코드 경로를 못 줌");
        assert_eq!(canon(&got), canon(&audit_code_path(exe)), "규칙 ≠ 실제({}): 실제 = {}", exe.display(), got.display());
    }
    assert_eq!(canon(&audit_code_path(&main)), canon(&root.join("Fake.app")), "주 실행 파일 = 번들 경로(가짜 번들 모양이 살아 있다)");
    // 실행 경로 이음: 제자리 시스템 실행 파일(복사·삭제 없음)의 pid 답 = 정적 답 = 규칙.
    let sleep = std::path::Path::new("/bin/sleep");
    let mut child = std::process::Command::new(sleep).arg("30").spawn().expect("/bin/sleep 기동");
    let dynamic = sec::code_path_of_pid(child.id() as i32);
    let _ = child.kill();
    let _ = child.wait();
    let dynamic = dynamic.expect("Security 프레임워크가 pid 경로를 못 줌");
    let stat = sec::static_code_path(sleep).expect("정적 경로");
    assert_eq!(canon(&dynamic), canon(&stat), "pid 답 ≠ 정적 답");
    assert_eq!(canon(&stat), canon(&audit_code_path(sleep)), "정적 답 ≠ 규칙");
}

/// 가짜 번들 고정 자리 = `target/<profile>/cys-test-fixtures/t3-secpath/`(시험 실행 파일 = `target/<profile>/deps/…`).
/// 없을 때만 만들고(임시 이름에 복사 → 이름 바꾸기 = 동시 시험 프로세스끼리 반쪽 파일을 보지 않음) **지우지 않는다**. 실행하지 않는다.
#[cfg(target_os = "macos")]
fn secpath_fixture_root() -> std::path::PathBuf {
    let exe = std::env::current_exe().expect("시험 실행 파일 경로");
    let deps = exe.parent().expect("deps");
    let profile = if deps.file_name().map(|n| n == "deps").unwrap_or(false) { deps.parent().expect("profile") } else { deps };
    let root = profile.join("cys-test-fixtures/t3-secpath");
    let plist = root.join("Fake.app/Contents/Info.plist");
    if !plist.exists() {
        fake_bundle(&root, "Fake.app", "fakemain", Some("fakemain"));
    }
    std::fs::create_dir_all(root.join("plain")).unwrap();
    for rel in ["Fake.app/Contents/MacOS/fakemain", "Fake.app/Contents/MacOS/fakehelper", "plain/fakeplain"] {
        let dst = root.join(rel);
        if dst.exists() {
            continue;
        }
        let tmp = dst.with_extension(format!("part-{}", std::process::id()));
        std::fs::copy("/bin/sleep", &tmp).unwrap();
        if std::fs::rename(&tmp, &dst).is_err() {
            let _ = std::fs::remove_file(&tmp); // 다른 시험 프로세스가 먼저 놓았다 — 실행된 적 없는 반쪽 복사본만 치운다.
        }
    }
    root
}

#[cfg(target_os = "macos")]
mod sec {
    use std::ffi::{c_void, CStr};
    use std::os::raw::{c_char, c_long};
    type CFTypeRef = *const c_void;
    type CFIndex = c_long;
    #[repr(C)]
    struct KeyCb {
        _p: [usize; 6],
    }
    #[repr(C)]
    struct ValCb {
        _p: [usize; 5],
    }
    #[link(name = "CoreFoundation", kind = "framework")]
    extern "C" {
        static kCFTypeDictionaryKeyCallBacks: KeyCb;
        static kCFTypeDictionaryValueCallBacks: ValCb;
        fn CFNumberCreate(alloc: CFTypeRef, ty: CFIndex, v: *const c_void) -> CFTypeRef;
        fn CFDictionaryCreate(a: CFTypeRef, k: *const *const c_void, v: *const *const c_void, n: CFIndex, kcb: *const KeyCb, vcb: *const ValCb) -> CFTypeRef;
        fn CFURLGetFileSystemRepresentation(url: CFTypeRef, resolve: u8, buf: *mut u8, max: CFIndex) -> u8;
        fn CFURLCreateFromFileSystemRepresentation(alloc: CFTypeRef, buf: *const u8, len: CFIndex, is_dir: u8) -> CFTypeRef;
        fn CFRelease(cf: CFTypeRef);
    }
    #[link(name = "Security", kind = "framework")]
    extern "C" {
        static kSecGuestAttributePid: CFTypeRef;
        fn SecCodeCopyGuestWithAttributes(host: CFTypeRef, attrs: CFTypeRef, flags: u32, guest: *mut CFTypeRef) -> i32;
        fn SecCodeCopyStaticCode(code: CFTypeRef, flags: u32, out: *mut CFTypeRef) -> i32;
        fn SecCodeCopyPath(code: CFTypeRef, flags: u32, path: *mut CFTypeRef) -> i32;
        fn SecStaticCodeCreateWithPath(path: CFTypeRef, flags: u32, out: *mut CFTypeRef) -> i32;
    }
    const K_CF_NUMBER_SINT32: CFIndex = 3;
    /// 정적 코드 객체(파일 그대로 · 실행 없음)의 경로 — 번들 주 실행 파일이면 Security 가 번들로 잡아 번들 경로를 준다.
    pub fn static_code_path(exe: &std::path::Path) -> Option<std::path::PathBuf> {
        use std::os::unix::ffi::OsStrExt;
        let bytes = exe.as_os_str().as_bytes();
        unsafe {
            let url = CFURLCreateFromFileSystemRepresentation(std::ptr::null(), bytes.as_ptr(), bytes.len() as CFIndex, 0);
            if url.is_null() {
                return None;
            }
            let mut st: CFTypeRef = std::ptr::null();
            let rc = SecStaticCodeCreateWithPath(url, 0, &mut st);
            CFRelease(url);
            if rc != 0 || st.is_null() {
                return None;
            }
            let mut out: CFTypeRef = std::ptr::null();
            let rc = SecCodeCopyPath(st, 0, &mut out);
            CFRelease(st);
            if rc != 0 || out.is_null() {
                return None;
            }
            let mut buf = [0u8; 4096];
            let ok = CFURLGetFileSystemRepresentation(out, 1, buf.as_mut_ptr(), buf.len() as CFIndex);
            CFRelease(out);
            (ok != 0).then(|| std::path::PathBuf::from(CStr::from_ptr(buf.as_ptr() as *const c_char).to_string_lossy().into_owned()))
        }
    }
    pub fn code_path_of_pid(pid: i32) -> Option<std::path::PathBuf> {
        unsafe {
            let num = CFNumberCreate(std::ptr::null(), K_CF_NUMBER_SINT32, (&pid as *const i32).cast());
            let keys = [kSecGuestAttributePid];
            let vals = [num];
            let attrs = CFDictionaryCreate(std::ptr::null(), keys.as_ptr(), vals.as_ptr(), 1, &kCFTypeDictionaryKeyCallBacks, &kCFTypeDictionaryValueCallBacks);
            let mut code: CFTypeRef = std::ptr::null();
            let rc = SecCodeCopyGuestWithAttributes(std::ptr::null(), attrs, 0, &mut code);
            CFRelease(attrs);
            CFRelease(num);
            if rc != 0 || code.is_null() {
                return None;
            }
            let mut st: CFTypeRef = std::ptr::null();
            let rc = SecCodeCopyStaticCode(code, 0, &mut st);
            CFRelease(code);
            if rc != 0 || st.is_null() {
                return None;
            }
            let mut url: CFTypeRef = std::ptr::null();
            let rc = SecCodeCopyPath(st, 0, &mut url);
            CFRelease(st);
            if rc != 0 || url.is_null() {
                return None;
            }
            let mut buf = [0u8; 4096];
            let ok = CFURLGetFileSystemRepresentation(url, 1, buf.as_mut_ptr(), buf.len() as CFIndex);
            CFRelease(url);
            (ok != 0).then(|| std::path::PathBuf::from(CStr::from_ptr(buf.as_ptr() as *const c_char).to_string_lossy().into_owned()))
        }
    }
}

/// 독립 검증 D3 ⑴ — 붙은 소켓의 상대 pid 가 내가 띄운 seatkeep 이 아니면(가짜 소켓이 먼저 듣는 경우) 이유와 함께 거절한다.
#[cfg(target_os = "macos")]
#[test]
fn greet_refuses_socket_whose_peer_is_not_the_launched_seatkeep() {
    let (ours, theirs) = std::os::unix::net::UnixStream::pair().unwrap();
    // 상대 = 이 시험 프로세스 자신 · 「띄운 seatkeep」 pid 는 다른 값.
    let launched = std::process::id() + 1_000_000;
    let deadline = std::time::Instant::now() + std::time::Duration::from_secs(1);
    let e = super::seatkeep_mac::greet(ours, launched, deadline).expect_err("가짜 소켓을 받아들임");
    assert!(e.contains("상대 pid"), "소켓 상대 pid 대조로 거절해야 한다: {e}");
    drop(theirs);
}

/// 독립 검증 D3 ⑵ — 소켓 상대는 맞아도 WELCOME 의 pid 가 띄운 seatkeep 이 아니면 거절한다.
#[cfg(target_os = "macos")]
#[test]
fn greet_refuses_welcome_from_other_pid() {
    use std::io::Write as _;
    let (ours, mut theirs) = std::os::unix::net::UnixStream::pair().unwrap();
    let me = std::process::id(); // 소켓 상대 = 이 프로세스 = 「띄운 seatkeep」로 맞춘다
    let t = std::thread::spawn(move || {
        let _ = super::sk_proto::read_frame(&mut theirs); // HELLO
        let w = super::sk_proto::json_frame(super::sk_proto::WELCOME, u32::MAX, &serde_json::json!({"pid": me + 1, "seats": []}));
        let _ = theirs.write_all(&w);
        theirs
    });
    let deadline = std::time::Instant::now() + std::time::Duration::from_secs(5);
    let e = super::seatkeep_mac::greet(ours, me, deadline).expect_err("다른 pid 의 WELCOME 을 받아들임");
    assert!(e.contains("WELCOME pid"), "WELCOME pid 대조로 거절해야 한다: {e}");
    let _ = t.join();
}

/// 입양(T4) 뮤턴트 M6 시험대 — 등록부 pid·출생 시각까지 맞춘 가짜 서버(cys-seatkeep 이 아닌 실행 파일)는 HELLO 를 받기 전에 거절된다.
/// 가짜 = 이 시험 프로세스 자신이 듣는 소켓 → 소켓 상대 pid·출생 시각은 「판정 값」과 같다 · 남는 축 = 실행 파일(= 시험 바이너리 ≠ cysd 옆 cys-seatkeep).
/// 가짜는 HELLO 를 받으면 그럴듯한 WELCOME(pid = 자기 · 좌석 1개)으로 답한다 — 실행 파일 검사가 빠지면 입양이 성공해 붉어진다.
#[cfg(target_os = "macos")]
#[test]
fn adopt_connect_refuses_fake_server_that_is_not_seatkeep_exe() {
    use std::io::Write as _;
    let me = std::process::id();
    let dir = std::env::temp_dir().join(format!("cskm6-{me}-{}", crate::state::now_epoch().to_bits() % 1_000_000));
    std::fs::create_dir_all(&dir).unwrap();
    let sock = dir.join("f.sock");
    let listener = std::os::unix::net::UnixListener::bind(&sock).unwrap();
    let t = std::thread::spawn(move || {
        let (mut s, _) = listener.accept().unwrap();
        let _ = s.set_read_timeout(Some(std::time::Duration::from_secs(4)));
        let got_hello = matches!(super::sk_proto::read_frame(&mut s), Ok(Some((super::sk_proto::HELLO, _, _))));
        if got_hello {
            let w = super::sk_proto::json_frame(
                super::sk_proto::WELCOME,
                u32::MAX,
                &serde_json::json!({"pid": me, "seats": [{"child_pid": me, "total": 0, "tail_start": 0, "disc_total": 0}]}),
            );
            let _ = s.write_all(&w);
        }
        (got_hello, s)
    });
    let start = crate::seat_adopt::process_start_us(me).expect("이 시험 프로세스 출생 시각");
    let size = portable_pty::PtySize { rows: 24, cols: 80, pixel_width: 0, pixel_height: 0 };
    let r = super::seatkeep_mac::adopt_connect(&sock, me, start, size, "m6fake");
    let e = match r {
        Ok(_) => String::new(),
        Err(e) => e,
    };
    let (got_hello, s) = t.join().unwrap();
    drop(s);
    let _ = std::fs::remove_dir_all(&dir);
    assert!(e.contains("실행 파일") && e.contains('≠'), "cys-seatkeep 이 아닌 가짜 서버를 실행 파일 대조로 거절해야 한다(입양됨 = 빈 문자열): {e:?}");
    assert!(!got_hello, "실행 파일 대조는 HELLO 를 보내기 전이어야 한다(가짜에게 조종자 인사를 건넴)");
}

/// codex 1R #2 시험대: 출력 소비자(읽기 얼굴)가 멈춘 seatkeep 좌석. 노브와 무관하게 seatkeep 경로를 직접 띄운다(`SeatkeepPlan` · 실제
/// seatkeep 실행 파일 = `cargo build --bin cys-seatkeep` 뒤). 좌석 = 4MB 를 쏟은 뒤 입력을 되읽는 셸. 1.5초 쉬어 대기열이 차게 한다.
#[cfg(target_os = "macos")]
fn stalled_seat(tag: &str) -> (Spawned, Box<dyn std::io::Read + Send>, Box<dyn std::io::Write + Send>, i32, std::path::PathBuf) {
    let dir = std::env::temp_dir().join(format!("cskt-{tag}-{}-{}", std::process::id(), crate::state::now_epoch().to_bits() % 1_000_000));
    std::fs::create_dir_all(&dir).unwrap();
    let daemon = crate::state::Daemon::new(dir.join("cysd.sock"));
    let size = portable_pty::PtySize { rows: 24, cols: 80, pixel_width: 0, pixel_height: 0 };
    let plan = SeatkeepPlan::prepare(&daemon, size).expect("seatkeep 계획");
    let mut b = portable_pty::CommandBuilder::new("/bin/sh");
    b.args(["-c", "head -c 4000000 /dev/zero | tr '\\0' x; exec cat"]);
    b.cwd(&dir);
    let mut sp = Opened::Seatkeep(plan).spawn(b).expect("seatkeep 좌석");
    let (reader, writer) = sp.take_io().expect("얼굴");
    let keeper = sp.link().expect("연결").keeper_pid() as i32;
    std::thread::sleep(std::time::Duration::from_millis(1500));
    (sp, reader, writer, keeper, dir)
}

/// 시험 끝 정리 — seatkeep 이 끝나기를 기다리고(최대 10초) 남으면 SIGKILL.
#[cfg(target_os = "macos")]
fn reap_keeper(keeper: i32, dir: &std::path::Path) {
    let t = std::time::Instant::now();
    while unsafe { libc::kill(keeper, 0) } == 0 && t.elapsed() < std::time::Duration::from_secs(10) {
        std::thread::sleep(std::time::Duration::from_millis(50));
    }
    unsafe { libc::kill(keeper, libc::SIGKILL) };
    let _ = std::fs::remove_dir_all(dir);
}

/// codex 1R #2 ⑴: 출력 소비자가 멈춰 대기열이 가득 찬 뒤에도 입력 수신 확인(INPUT_ACK)이 막히지 않는다(쓰기 얼굴 write = 확인까지 기다림).
#[cfg(target_os = "macos")]
#[test]
fn seatkeep_stalled_consumer_does_not_block_input_ack() {
    use std::time::Duration;
    let (sp, reader, mut writer, keeper, dir) = stalled_seat("stall-ack");
    let (tx, rx) = std::sync::mpsc::channel();
    std::thread::spawn(move || {
        let r = std::io::Write::write_all(&mut writer, b"ping\n");
        let _ = tx.send(r.is_ok());
        writer
    });
    let acked = rx.recv_timeout(Duration::from_secs(5));
    let fg = sp.link().unwrap().foreground();
    drop(reader);
    drop(sp);
    unsafe { libc::kill(keeper, libc::SIGKILL) };
    reap_keeper(keeper, &dir);
    assert!(matches!(acked, Ok(true)), "출력 소비자가 멈춘 동안 입력 수신 확인이 5초 안에 안 옴: {acked:?}");
    eprintln!("[stall-ack] 전경 답(200ms 상한) = {fg:?}");
}

/// codex 1R #2 ⑵: 출력 소비자가 멈춘 채로 닫기(close_surface 의 kill 뒤 회수 = `kill_and_reap`)가 상한 안에 돌아온다 — EXITED 가
/// 상태에 닿는다(옛: 64조각 채널의 막히는 송신 뒤에 EXITED 가 묶여 영구 대기).
#[cfg(target_os = "macos")]
#[test]
fn seatkeep_stalled_consumer_does_not_block_close() {
    use std::time::{Duration, Instant};
    let (sp, reader, writer, keeper, dir) = stalled_seat("stall-close");
    let child = std::sync::Mutex::new(sp.child);
    let (tx, rx) = std::sync::mpsc::channel();
    let t = Instant::now();
    std::thread::spawn(move || {
        crate::seat_proc::kill_and_reap(&child);
        let _ = tx.send(());
    });
    let done = rx.recv_timeout(Duration::from_secs(5));
    let took = t.elapsed();
    if done.is_err() {
        unsafe { libc::kill(keeper, libc::SIGKILL) };
    }
    drop((reader, writer));
    reap_keeper(keeper, &dir);
    assert!(done.is_ok(), "출력 소비자가 멈춘 동안 닫기(kill_and_reap)가 5초 안에 안 돌아옴(EXITED 미반영)");
    eprintln!("[stall-close] 닫기 {took:?}");
}

/// codex 3R #2 시험대: 셸 스크립트 좌석(seatkeep 경로 직접 · `cargo build --bin cys-seatkeep` 뒤). `stty raw -echo` 로 입력 쓰기가 버려지지
/// 않고 막히게 한다(정규 모드는 줄 없이 찬 입력을 버릴 수 있다) — 자식이 stdin 을 안 읽는 동안 256KiB 입력은 PTY 입력 버퍼에서 반드시 막힌다.
#[cfg(target_os = "macos")]
fn script_seat(tag: &str, script: &str) -> (Spawned, Box<dyn std::io::Read + Send>, Box<dyn std::io::Write + Send>, i32, std::path::PathBuf) {
    let dir = std::env::temp_dir().join(format!("cskt-{tag}-{}-{}", std::process::id(), crate::state::now_epoch().to_bits() % 1_000_000));
    std::fs::create_dir_all(&dir).unwrap();
    let daemon = crate::state::Daemon::new(dir.join("cysd.sock"));
    let size = portable_pty::PtySize { rows: 24, cols: 80, pixel_width: 0, pixel_height: 0 };
    let plan = SeatkeepPlan::prepare(&daemon, size).expect("seatkeep 계획");
    let mut b = portable_pty::CommandBuilder::new("/bin/sh");
    b.args(["-c", script]);
    b.cwd(&dir);
    let mut sp = Opened::Seatkeep(plan).spawn(b).expect("seatkeep 좌석");
    let (reader, writer) = sp.take_io().expect("얼굴");
    let keeper = sp.link().expect("연결").keeper_pid() as i32;
    (sp, reader, writer, keeper, dir)
}

/// 입력 256KiB(100바이트 줄) — 원시 모드 PTY 입력 버퍼(수 KiB)보다 커서 자식이 안 읽으면 seatkeep 의 PTY 쓰기가 막힌다.
#[cfg(target_os = "macos")]
fn big_input() -> Vec<u8> {
    let line = [b"a".repeat(99), b"\n".to_vec()].concat();
    line.iter().copied().cycle().take(256 << 10).collect()
}

/// codex 3R #2 ①(master 결정 A안 + 만료 (나)): 출력 소비자가 끝내 재개하지 않는다 + 좌석은 출력을 쏟고 stdin 을 안 읽는다 → 입력 확인
/// 기다림 중 연결 스레드가 HARD 에서 막힌 순간부터 ACK_STALL_LIMIT(10초) 안에 호출자에게 TimedOut · seatkeep 끝(연결 끊김 → controller_lost)
/// · 좌석 프로세스 사라짐(= 막힌 입력이 나중에 적용될 곳이 없음). 옛 꼴(상한 없음)은 영구 대기.
#[cfg(target_os = "macos")]
#[test]
fn seatkeep_input_ack_stall_ends_seat_when_consumer_never_resumes() {
    use std::time::{Duration, Instant};
    let (mut sp, reader, mut writer, keeper, dir) = script_seat("ackstall", "stty raw -echo; exec yes 0123456789abcdef");
    let child = sp.pid as i32;
    let input = big_input();
    let (tx, rx) = std::sync::mpsc::channel();
    let t0 = Instant::now();
    std::thread::spawn(move || {
        let r = std::io::Write::write_all(&mut writer, &input);
        let _ = tx.send((r.map_err(|e| e.kind()), t0.elapsed()));
        writer
    });
    // 상한 10초 + 대기열이 HARD 까지 차는 시간 + 허용 오차(주기 250ms · 부하).
    let got = rx.recv_timeout(Duration::from_secs(16));
    let gone_by = Instant::now() + Duration::from_secs(5);
    let alive = |pid: i32| unsafe { libc::kill(pid, 0) } == 0;
    while (alive(keeper) || alive(child)) && Instant::now() < gone_by {
        std::thread::sleep(Duration::from_millis(50));
    }
    let (keeper_alive, child_alive) = (alive(keeper), alive(child));
    let exit = sp.child.try_wait().ok().flatten();
    if child_alive {
        unsafe { libc::kill(child, libc::SIGKILL) };
    }
    drop(reader);
    drop(sp);
    unsafe { libc::kill(keeper, libc::SIGKILL) };
    reap_keeper(keeper, &dir);
    eprintln!("[ackstall] 쓰기 = {got:?} · seatkeep 생존 {keeper_alive} · 좌석 생존 {child_alive} · 종료 = {exit:?}");
    let (r, took) = got.expect("소비자 정지 + stdin 안 읽음에서 쓰기가 16초 안에 안 돌아옴(상한 없음 = 영구 대기)");
    assert_eq!(r, Err(std::io::ErrorKind::TimedOut), "상한 만료는 호출자에게 TimedOut 이어야 한다");
    assert!(took >= Duration::from_secs(10), "상한(HARD 막힘부터 10초)보다 일찍 끝남: {took:?}");
    assert!(!keeper_alive, "상한 만료 뒤 seatkeep 이 5초 안에 안 끝남(controller_lost 경로 미작동)");
    assert!(!child_alive, "상한 만료 뒤 좌석 프로세스가 5초 안에 안 사라짐(입력이 나중에 적용될 수 있음)");
    assert!(exit.is_some(), "연결 끊김이 종료로 접히지 않음");
}

/// codex 3R #2 ②: 출력 소비는 정상인데 자식이 stdin 을 상한(10초)보다 오래(16초) 안 읽는다 → 상한 미발동 · 좌석이 죽지 않고 자식이 읽기
/// 시작하면 확인이 온다(직접 PTY 처럼 기다림). 「절대」 상한(B안)이면 여기서 좌석이 죽는다.
#[cfg(target_os = "macos")]
#[test]
fn seatkeep_input_ack_waits_while_consumer_runs_and_stdin_unread() {
    use std::time::{Duration, Instant};
    let (sp, mut reader, mut writer, keeper, dir) =
        script_seat("ackslow", "stty raw -echo; yes 0123456789abcdef & sleep 16; exec cat >/dev/null");
    let child = sp.pid as i32;
    let stop = std::sync::Arc::new(std::sync::atomic::AtomicBool::new(false));
    let st2 = std::sync::Arc::clone(&stop);
    let drained = std::thread::spawn(move || {
        let mut buf = vec![0u8; 1 << 16];
        let mut n_all: u64 = 0;
        while !st2.load(std::sync::atomic::Ordering::Relaxed) {
            match std::io::Read::read(&mut reader, &mut buf) {
                Ok(0) | Err(_) => break,
                Ok(n) => n_all += n as u64,
            }
        }
        n_all
    });
    let input = big_input();
    let (tx, rx) = std::sync::mpsc::channel();
    let t0 = Instant::now();
    std::thread::spawn(move || {
        let r = std::io::Write::write_all(&mut writer, &input);
        let _ = tx.send((r.map_err(|e| e.kind()), t0.elapsed()));
        writer
    });
    let got = rx.recv_timeout(Duration::from_secs(30));
    let alive = |pid: i32| unsafe { libc::kill(pid, 0) } == 0;
    let (keeper_alive, child_alive) = (alive(keeper), alive(child));
    stop.store(true, std::sync::atomic::Ordering::Relaxed);
    crate::seat_proc::kill_and_reap(&std::sync::Mutex::new(sp.child));
    unsafe { libc::kill(keeper, libc::SIGKILL) };
    let n_out = drained.join().unwrap_or(0);
    reap_keeper(keeper, &dir);
    eprintln!("[ackslow] 쓰기 = {got:?} · 소비한 출력 {n_out}바이트 · seatkeep 생존 {keeper_alive} · 좌석 생존 {child_alive}");
    let (r, took) = got.expect("자식이 읽기 시작한 뒤에도 30초 안에 확인이 안 옴");
    assert_eq!(r, Ok(()), "소비가 도는데 상한이 발동해 좌석이 끝남(절대 상한 꼴)");
    assert!(took >= Duration::from_secs(11), "입력 쓰기가 실제로 상한보다 오래 막히지 않음(시험이 판별력 없음): {took:?}");
    assert!(keeper_alive && child_alive, "확인 뒤 seatkeep·좌석이 살아 있어야 한다");
    assert!(n_out > 5 << 20, "출력 소비가 돌지 않음(판별력 없음): {n_out}");
}

/// T5: 진단 문구용 WELCOME 사본은 좌석 칸의 토큰을 지운다(실패 갈래 오류 문구에도 토큰 0) · 나머지 칸은 그대로.
#[cfg(target_os = "macos")]
#[test]
fn welcome_without_tokens_strips_only_the_token() {
    let w = serde_json::json!({"pid": 9, "seats": [{"seat": 0, "total": 5, "seat_token": "g-1.0123456789abcdef0123456789abcdef"}, {"seat": 1}]});
    let r = super::seatkeep_mac::welcome_without_tokens(&w);
    assert!(!r.to_string().contains("seat_token") && !r.to_string().contains("0123456789abcdef"), "{r}");
    assert_eq!(r["seats"][0]["total"], 5);
    assert_eq!(r["pid"], 9);
    assert_eq!(w["seats"][0]["seat_token"], "g-1.0123456789abcdef0123456789abcdef", "원본은 건드리지 않는다");
}
