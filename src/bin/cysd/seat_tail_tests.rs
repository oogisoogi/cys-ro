//! TICKET=cysr-seatkeep-t3 · 독립 검증 D1 = **알려진 한계(known_limit)** 관측 시험(master#6e60316b 결정 B) — 「멈춘 조종자 아래에서
//! 좌석 자식이 출력을 남기고 끝나면」 직접 PTY 와 seatkeep 조종자 종속 모드가 **다르게** 동작한다는 것을 고정한다. 동작이 바뀌면
//! (고쳐지든 나빠지든) 붉어진다. ⚠ T4 에서 A(seatkeep 이 슬레이브를 쥐고 회수 뒤 비우고 닫기) 또는 다른 길로 고치면 노브 켬 갈래를
//! 「모자람 0」으로 뒤집는다.
//!
//! 기제(관측 각 2/2 + 공개 XNU 소스 대조 · codex 1R ③ 표현으로 정정): 독자가 마스터 `read()` 안에 잠들어 있으면 자식의 **첫 write 가 그
//! 독자를 깨워 그 덩이를 read 로 옮기고**(커널 큐에 보존된 것이 아니다 · 탐침 501/500), **나머지 출력 큐(t_outq)는 마지막 슬레이브 참조가
//! 닫힐 때 버려진다**. 조건은 「세션 우두머리 종료」 자체가 아니라 「마지막 슬레이브 close(회수·WNOWAIT 무관 — 회수보다 앞선 fd close/TTY
//! 정리에서 정해짐)」다. 다만 세션 우두머리가 제어 터미널을 쥔 채 끝나면 커널이 그 터미널을 REVOKEALL 로 회수해(아래 kern_exit.c) 다른
//! 프로세스가 쥔 슬레이브 열림까지 닫힐 수 있다 — T4 의 「슬레이브 보유」는 이 점을 먼저 검증해야 한다.
//! 소스(apple-oss-distributions/xnu `f6217f89` = xnu-12377.1.9 · 2025-10-16 · 줄 = 그 판):
//!   `bsd/kern/tty_dev.c` `ptcread` 642·680·691·700(슬레이브가 열려 있을 때만 t_outq 를 `q_to_b` 로 복사 · 아니면 685 EOF) ·
//!   `ptsclose` 350(`t_timeout = 60`)·355(`l_close` = ttylclose)·356(`ttyclose`)·361(`ptsstop`) ·
//!   `bsd/kern/tty.c` `ttylclose` 1993~1994(`ttywflush` 실패면 `ttyflush(FREAD|FWRITE)`) · `ttyclose` 418(무조건 `ttyflush(FREAD|FWRITE)`) ·
//!   `ttyflush` 1840(`FLUSHQ(&tp->t_outq)`) · `bsd/kern/kern_exit.c` 2287·2312·2330·2336(세션 우두머리: SIGHUP → `ttywait` → `VNOP_REVOKE REVOKEALL`).
//!   【추정 · 미실측】 끝나는 우두머리 안의 `ttywait`(PCATCH 잠·t_timeout 0 = 무기한)가 곧바로 깨지는 까닭(직전 자기 그룹 SIGHUP 로 보류 신호?)은
//!   소스로 확정하지 못했다 — 관측(멈춘 독자 아래서 자식이 끝나고 꼬리를 잃음)과 맞는 설명일 뿐이다.
//! 직접 PTY cysd 는 읽기 스레드가 `read()` 안에서 멈춰(SIGSTOP 등) 첫 덩이를 받는다. seatkeep 조종자 종속 모드는 역압 때 읽기 스레드가
//! Condvar(`read()` 밖)에서 기다리므로, 그 사이 자식이 커널 버퍼(실측 1,024바이트)만큼 쓰고 끝나면 그 큐를 커널이 버린다
//! (seatkeep 이 읽은 적이 없다 — 받는 쪽을 열어 둔 실험에서 EXITED final_offset = cysd 가 받은 바이트).
//!
//! 띠에 기대지 않는 방법: 좌석 자식(perl)은 1초 쉰 뒤 비차단 `syswrite` 로 번호 줄을 쓰다가 **1초 동안 한 바이트도 못 쓰면**(앞 단계가
//! 전부 참) 지금까지 쓴 바이트 수를 파일에 적고 끝난다 — 마지막 바이트는 반드시 커널 PTY 버퍼에 있다. 시험은 그동안 읽지 않고, 자식이
//! 끝난 뒤 DRAIN(2초)+1.5초를 기다렸다가 EOF 까지 읽는다.
//! - 노브 켬(seatkeep `--controller-bound`) = 모자람 > 0 이고 ≤ 커널 버퍼 한 덩이(1,024).
//! - 노브 끔(직접 PTY 기준 동작) = cysd 의 멈춘 읽기 스레드 대신 **`read()` 안에서 멈춘 독자**(마스터 fd 사본을 읽는 `cat` 을 자식이 쓰기 전에
//!   SIGSTOP · 기다린 뒤 SIGCONT = 멈췄다 풀린 cysd)를 두고, 자식은 **보통 프로그램처럼 막히는 쓰기**로 256KiB 를 쓴다 → 멈춘 동안 자식은
//!   커널 버퍼(약 1KiB)에서 막혀 끝나지 못하고(단언) · 풀린 뒤 모자람 0.
//! ⚠ 관측(각 2/2): 직접 PTY 에서도 자식이 「커널 버퍼가 찰 때까지만 쓰고 끝나는」 꼴(위 비차단 자식)이면 같은 1,024바이트를 잃는다(멈춘
//!   독자는 첫 줄 102바이트만 받음) — 커널 한계는 같고, **다른 것은 멈춘 조종자 아래에서 자식이 막히기 전까지 쓸 수 있는 양**이다(직접 ≈ 커널
//!   버퍼 · seatkeep ≈ 큐 256KiB + 앞 단계). 그래서 직접 PTY 에서는 막혀서 못 끝나는 폭발이 seatkeep 아래에서는 끝까지 써지고 끝나며 꼬리를
//!   잃는다(검증 좌석 tailloss 2463줄 = 이 꼴).
#![cfg(unix)]

use crate::state::{now_epoch, Daemon};
use portable_pty::{CommandBuilder, PtySize};
use std::io::Read;
use std::time::{Duration, Instant};

/// 커널 PTY 출력 버퍼 한 덩이(이 맥 실측 — 직접 PTY 에서 「1초 진척 없음」까지 쓴 양 1,014 + ONLCR 10 = 1,024).
const KERNEL_CHUNK: u64 = 1024;

/// 좌석 자식: 1초 쉼(시험이 기준 독자를 세울 시간) → 비차단으로 번호 줄 → 1초 진척 없음 → 「쓴 바이트 · 그중 \n 수 · 마지막 번호」 → 끝.
const CHILD: &str = r#"use Fcntl; select(undef, undef, undef, 1.0); my $fl = fcntl(STDOUT, F_GETFL, 0); fcntl(STDOUT, F_SETFL, $fl | O_NONBLOCK);
my ($tot, $nl, $i, $stall) = (0, 0, 0, 0); my $p = 'x' x 89; my $pend = '';
while (1) {
  if ($pend eq '') { $i++; $pend = sprintf("%010d %s\n", $i, $p); }
  my $w = syswrite(STDOUT, $pend);
  if (!defined $w) { die "write: $!" unless $!{EAGAIN}; $stall++; last if $stall >= 50; select(undef, undef, undef, 0.02); next; }
  $stall = 0; my $done = substr($pend, 0, $w); $tot += $w; $nl += ($done =~ tr/\n//); $pend = substr($pend, $w);
}
open(my $f, '>', $ARGV[0]) or die; print $f "$tot $nl $i\n"; close $f; exit 0"#;

/// 노브 끔 갈래의 자식: 1초 쉼 → 막히는 쓰기로 256KiB 남짓(2,600줄) → 「쓴 바이트 · \n 수 · 마지막 번호」 → 끝.
const CHILD_BLOCKING: &str = r#"select(undef, undef, undef, 1.0); my ($tot, $nl) = (0, 0); my $p = 'x' x 89; $| = 1;
for my $i (1..2600) { my $l = sprintf("%010d %s
", $i, $p); print $l; $tot += length $l; $nl++ }
open(my $f, '>', $ARGV[0]) or die; print $f "$tot $nl 2600
"; close $f; exit 0"#;

/// 좌석 자식이 끝났는가(사라졌거나 좀비) — 직접 PTY 에서는 이 시험 프로세스의 자식이라 회수 전까지 좀비로 남는다.
fn gone(pid: u32) -> bool {
    let out = std::process::Command::new("ps").args(["-o", "stat=", "-p", &pid.to_string()]).output();
    match out {
        Ok(o) => {
            let st = String::from_utf8_lossy(&o.stdout).trim().to_string();
            st.is_empty() || st.starts_with('Z')
        }
        Err(_) => false,
    }
}

#[test]
fn seat_tail_known_limit_stalled_controller_child_exit() {
    let knob = crate::seat_proc::seatkeep_enabled();
    let dir = std::env::temp_dir().join(format!("cys-tail-{}-{}", std::process::id(), now_epoch().to_bits() % 1_000_000));
    std::fs::create_dir_all(&dir).unwrap();
    let daemon = Daemon::new(dir.join("cysd.sock"));
    let opened = crate::seat_proc::open(&daemon, PtySize { rows: 24, cols: 120, pixel_width: 0, pixel_height: 0 }).expect("PTY 열기");
    let truth = dir.join("truth");
    let mut b = CommandBuilder::new("/usr/bin/perl");
    b.args(["-e", if knob { CHILD } else { CHILD_BLOCKING }, truth.to_str().unwrap()]);
    b.cwd(&dir);
    let mut sp = opened.spawn(b).expect("좌석 기동");
    let pid = sp.pid;
    // 노브 끔: 직접 PTY cysd 의 「read() 안에서 멈춘 읽기 스레드」 대역 — 마스터 fd 사본을 stdin 으로 읽는 cat 을 read() 안에서 멈춘다.
    let mut stand_in: Option<std::process::Child> = None;
    let stand_out = dir.join("stand_in.out");
    if !knob {
        use std::os::unix::io::FromRawFd;
        let fd = sp.master.as_raw_fd().expect("직접 PTY 마스터 fd");
        let dupfd = unsafe { libc::dup(fd) };
        assert!(dupfd >= 0, "dup 실패");
        let c = std::process::Command::new("/bin/cat")
            .stdin(unsafe { std::process::Stdio::from_raw_fd(dupfd) })
            .stdout(std::fs::File::create(&stand_out).expect("대역 출력 파일"))
            .spawn()
            .expect("cat");
        std::thread::sleep(Duration::from_millis(300)); // 자식은 1초 쉬는 중 = 출력 없음 → cat 은 read() 안에서 잔다
        unsafe { libc::kill(c.id() as i32, libc::SIGSTOP) };
        stand_in = Some(c);
    }
    let (mut r, _w) = sp.take_io().expect("읽기 얼굴");
    if !knob {
        // 직접 PTY: 멈춘 독자 아래에서 자식은 커널 버퍼에서 막혀 끝나지 못한다 — 6초 동안 살아 있어야 한다(이것이 seatkeep 과 다른 점).
        std::thread::sleep(Duration::from_secs(6));
        assert!(!gone(pid) && !truth.exists(), "직접 PTY 인데 멈춘 독자 아래에서 자식이 끝났다(커널 버퍼보다 큰 폭발)");
        if let Some(c) = stand_in.as_ref() {
            unsafe { libc::kill(c.id() as i32, libc::SIGCONT) };
        }
    }
    // ① 읽지 않는다 — 자식이 끝날 때까지(진실 파일 + 프로세스 사라짐). 노브 켬 = 「1초 진척 없음」으로 끝남.
    let deadline = Instant::now() + Duration::from_secs(60);
    while !(truth.exists() && gone(pid)) {
        assert!(Instant::now() < deadline, "자식이 60초 안에 안 끝남");
        std::thread::sleep(Duration::from_millis(20));
    }
    let t: Vec<u64> = std::fs::read_to_string(&truth).unwrap().split_whitespace().map(|x| x.parse().unwrap()).collect();
    let (wrote, newlines) = (t[0], t[1]);
    // ② 꼬리는 커널 PTY 버퍼에 있다 — 읽지 않고 DRAIN(2초)을 넘겨 기다린다.
    std::thread::sleep(Duration::from_millis(3500));
    // ③ 다시 읽는다 — EOF 까지(상한 60초). 노브 끔 = 멈춘 대역(cat)을 풀어 그것이 읽게 한다(cysd 의 읽기 스레드가 풀리는 것과 같음).
    let mut got_len: Option<u64> = None;
    if let Some(mut c) = stand_in.take() {
        let t0 = Instant::now();
        while c.try_wait().ok().flatten().is_none() && t0.elapsed() < Duration::from_secs(20) {
            std::thread::sleep(Duration::from_millis(20));
        }
        let _ = c.kill();
        let _ = c.wait();
        got_len = Some(std::fs::metadata(&stand_out).map(|m| m.len()).unwrap_or(0));
    }
    let (tx, rx) = std::sync::mpsc::channel();
    std::thread::spawn(move || {
        let mut got = Vec::new();
        let mut buf = vec![0u8; 64 * 1024];
        loop {
            match r.read(&mut buf) {
                Ok(0) | Err(_) => break,
                Ok(n) => got.extend_from_slice(&buf[..n]),
            }
        }
        let _ = tx.send(got);
    });
    let got = if got_len.is_some() { Vec::new() } else { rx.recv_timeout(Duration::from_secs(60)).expect("다시 읽기가 60초 안에 EOF 에 닿지 않음") };
    let got_len = got_len.unwrap_or(got.len() as u64);
    crate::seat_proc::kill_and_reap(&std::sync::Mutex::new(sp.child));
    let _ = std::fs::remove_dir_all(&dir);
    let want = wrote + newlines; // PTY 의 ONLCR = \n 마다 \r 1바이트
    let missing = want.saturating_sub(got_len);
    eprintln!("T3TAIL knob={} wrote={wrote} want={want} got={got_len} missing={missing}", if knob { "on" } else { "off" });
    assert!(got_len <= want, "쓴 것보다 많이 받음");
    if knob {
        assert!(wrote > 64 * KERNEL_CHUNK, "커널 버퍼를 한참 넘겨 써야 seatkeep 큐·역압이 걸린 것이다(시험 전제 · 쓴 {wrote})");
        // 알려진 한계(D1) — T4 에서 고치면 이 줄을 `assert_eq!(missing, 0)` 으로 뒤집는다.
        assert!(missing > 0 && missing <= KERNEL_CHUNK, "알려진 한계 모양이 바뀜: 모자람 {missing}(기대 1..={KERNEL_CHUNK})");
    } else {
        assert_eq!(missing, 0, "직접 PTY(read() 안의 멈춘 독자)는 꼬리를 잃지 않는다");
    }
}
