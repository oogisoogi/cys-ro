//! TICKET=cysr-seatkeep-t3 · 좌석 프로세스 손잡이 단위 시험 — 노브 · 잠금 파일 형식(노브 끔 = 바이트까지 그대로) · 첫 칸 판독기 ·
//! 감사 토큰 경로 규칙(번들 주 실행 파일 = 번들 경로 · 실제 Security 프레임워크 대조).

use crate::seat_proc::*;

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
/// (`…/Python.app/Contents/MacOS/Python` → `…/Python.app`)을 가짜 번들로 재현한다. 실행 파일 = `/bin/sleep` 복사본.
/// pid 로 코드 객체를 얻어(`kSecGuestAttributePid`) 경로를 읽고, 규칙 함수의 답과 비교한다(번들 주 실행 파일 · 번들 안 비주 실행 파일 · 번들 밖).
#[cfg(target_os = "macos")]
#[test]
fn audit_code_path_matches_security_framework() {
    let root = std::env::temp_dir().join(format!("cys-t3-secpath-{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&root);
    let main = fake_bundle(&root, "Fake.app", "fakemain", Some("fakemain"));
    let helper = root.join("Fake.app/Contents/MacOS/fakehelper");
    std::fs::create_dir_all(root.join("plain")).unwrap();
    let plain = root.join("plain/fakeplain");
    for p in [&main, &helper, &plain] {
        std::fs::copy("/bin/sleep", p).unwrap();
    }
    for exe in [&main, &helper, &plain] {
        let mut child = std::process::Command::new(exe).arg("30").spawn().expect("복사본 기동");
        // 기동 직후 코드 객체가 아직 안 잡힐 수 있어 잠깐 기다린다.
        let mut got = None;
        for _ in 0..50 {
            got = sec::code_path_of_pid(child.id() as i32);
            if got.is_some() {
                break;
            }
            std::thread::sleep(std::time::Duration::from_millis(20));
        }
        let _ = child.kill();
        let _ = child.wait();
        let got = got.expect("Security 프레임워크가 경로를 못 줌");
        let canon = |p: &std::path::Path| std::fs::canonicalize(p).unwrap_or_else(|_| p.to_path_buf());
        assert_eq!(canon(&got), canon(&audit_code_path(exe)), "규칙 ≠ 실제({}): 실제 = {}", exe.display(), got.display());
    }
    let _ = std::fs::remove_dir_all(&root);
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
        fn CFRelease(cf: CFTypeRef);
    }
    #[link(name = "Security", kind = "framework")]
    extern "C" {
        static kSecGuestAttributePid: CFTypeRef;
        fn SecCodeCopyGuestWithAttributes(host: CFTypeRef, attrs: CFTypeRef, flags: u32, guest: *mut CFTypeRef) -> i32;
        fn SecCodeCopyStaticCode(code: CFTypeRef, flags: u32, out: *mut CFTypeRef) -> i32;
        fn SecCodeCopyPath(code: CFTypeRef, flags: u32, path: *mut CFTypeRef) -> i32;
    }
    const K_CF_NUMBER_SINT32: CFIndex = 3;
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
