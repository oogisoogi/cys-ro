//! cys-seatkeep — 좌석 보유 장치 T2 시제품(TICKET=cysr-seatkeep-t2 · 맥 · **cysd 미연결**).
//!
//! 설계 = `~/axdev/master/reports/2026-11-11-cysr-holder-design/DESIGN.md`(권고 (가2) 좌석당 보유 장치 ·
//! 코드 이름 seatkeep · master 판단 11-11 · 정정 11-11) · 브리프 = 같은 폴더 `briefs-draft/T2.md`.
//!
//! 하는 일(정책 0): PTY 열기·자식 기동(setsid+TIOCSCTTY — vendor portable-pty 그대로) · 항상 읽기 · 꼬리 ·
//! 누적 출력 오프셋 · 입력 쓰기(입력 id + 수신 확인 + 중복 제거) · 크기 · 신호 · 전경 그룹 질의 · 자식 회수 ·
//! 종료 기록 · 조종자 교체 기록. 화면 해석·배달·승인 판단은 **하지 않는다**. 미응답 단말 질의 응답기도 없다
//! (DESIGN §7-8 결정 전 · master 판단).
//!
//! 막히지 않는 규칙(codex 1R #1 #2 · 독립 검증 D1 반영): 상태 잠금을 쥔 채 막히는 호출을 하지 않는다. 조종자에게
//! 가는 프레임은 잠금 안에서 막히지 않는 큐에 넣기만 한다. 조종자가 늦으면 **밀린 바이트**가 상한(OUT_QUEUE_BYTES)을
//! 넘는 출력은 큐에 넣지 않고 꼬리에 둔 채 「밀림」으로 표시했다가, 쓰기 스레드가 큐를 비우면 꼬리에서 그 오프셋부터
//! 따라잡아 보낸다(꼬리에서 이미 밀려난 부분은 오프셋 건너뜀 = 유실로 보인다). 조종자를 내보내는 기준은 **멈춘 시간**뿐이다
//! — 소켓 쓰기가 CTL_WRITE_TIMEOUT 동안 한 바이트도 못 나가면 연결을 닫는다(tmux control.c 의 「시간으로 판정」과 같은 모양).
//! PTY 입력 쓰기는 좌석별 입력 스레드가 한다 — 자식이 입력을 안 읽어도 serve 는 끊김을 계속 보고 조종자 자리를 풀 수 있다.
//!
//! 쓰임: `cys-seatkeep --dir <상태폴더> --id <seatkeep id> --controller-exe <경로> --lock <잠금파일>
//!        [--requirement <코드서명 요구사항>] [--seats N] [--tail-bytes N] [--rows R --cols C]
//!        [--controller-bound | --adoptable] -- <명령> [인자…]`
//! `--rows/--cols` = 자식 PTY 첫 크기(기본 35×120 · T3 — cysd 가 좌석 크기로 띄운다).
//! `--controller-bound`(조종자 종속 모드 · T3 master#77162b13 — 옛 `--end-on-controller-loss` 를 넓힘) = seatkeep 이 직접 PTY 처럼 투명하다:
//!   ⑴ 조종자 연결이 끊기면(또는 기동 뒤 `FIRST_CONTROLLER_MAX` 안에 아무도 안 붙으면) 기록 1줄을 남기고 스스로 끝난다 → PTY 마스터가
//!      닫혀 커널이 좌석에 SIGHUP(= cysd 가 직접 PTY 를 쥐던 지금과 같은 좌석 수명 · master#c125bc97 ②).
//!      띄운 부모(cysd)가 사라져도 같다 — 부모 감시(kqueue)를 자식 기동 **앞에서** 시작하고, 기동 때 부모가 이미 없으면(ppid 1) PTY·자식을
//!      만들지 않고 rc 8 로, 기동 중이면 자식 기동 직전·직후 확인에서 rc 8 로 끝난다(codex 1R #1). 끝내는 길이 여럿이어도 기록은 1줄(종료 소유자 1명 · #4).
//!   ⑵ 조종자가 밀리면(못 보낸 출력이 BOUND_QUEUE_BYTES(256KiB) 에 닿으면) **PTY 를 읽지 않는다** — 커널 PTY 버퍼가 차서 자식의 쓰기가 멈춘다
//!      (직접 PTY 를 쥔 조종자가 늦게 읽을 때와 같은 역압 · 「밀림」·꼬리 따라잡기·유실 없음). 첫 조종자가 붙기 전에는 꼬리가 차면 멈춘다.
//!   ⑶ 쓰기 기한(CTL_WRITE_TIMEOUT)으로 내보내지 않는다(`write_stalled` 없음) — 연결이 살아 있는 한 기다린다(멈춘 조종자 아래서 자식도
//!      멈춰 산다 = 직접 PTY 와 같음). 제어 큐 상한(CTL_QUEUE_BYTES · `control_queue_full`)은 그대로다 — 제어 프레임은 조종자 요청의 답이라
//!      멈춘 조종자 아래서 쌓일 길이 없고, 넘치면 규약 위반으로 보고 끊김과 같이 끝낸다.
//! `--adoptable`(입양 모드 · T4 TICKET=cysr-1116-seatkeep-1119 · `--controller-bound` 와 함께 쓸 수 없다) = ⑵⑶ 은 종속 모드와 같고 ⑴ 만 뺀다:
//!   조종자가 끊겨도(cysd 강제 종료·교체) 좌석을 쥔 채 다음 조종자(같은 실행 파일 · 데몬 잠금 보유자)를 기다린다 = 「데몬이 죽어도 좌석이 산다」.
//!   조종자 없는 동안은 **옛 조종자가 처리를 끝냈다고 알린 오프셋**(PROCESSED) 뒤 출력이 꼬리(`--tail-bytes`)를 넘기 전까지만 PTY 를 읽는다
//!   — 그 뒤로는 역압(자식이 멈춤) → 새 조종자가 꼬리를 재생받으면 아무 조종자도 처리 못 한 출력의 유실 0. 끊길 때 이미 꼬리 밖으로 밀려난
//!   미처리분(옛 조종자 쪽 대기열이 꼬리보다 컸던 경우)만 잃으며, 새 조종자가 `disc_total` < `tail_start` 로 그 크기를 안다.
//!   첫 조종자가 `FIRST_CONTROLLER_MAX` 안에 안 붙으면 종속 모드처럼 끝낸다(cysd 가 기동~첫 인사 사이에 죽으면 아무도 이 좌석을 모른다).
//!   부모 감시(kqueue)·기동 단계 부모 확인은 하지 않는다(부모가 사라지는 것이 정상 경로).
//! 두 인자가 다 없으면 T2 동작 그대로(조종자 없이 좌석을 계속 쥔다 · 4MiB 큐 → 밀림 → 꼬리 따라잡기 · write_stalled 10초 — 입양은 T4).
//! `--seats N`(N>1) = 「판별 1개」 비교 변형(좌석 N개를 한 프로세스가 쥠) — 비용 비교 전용 · 제품 경로 아님.

#[cfg(unix)]
mod peer;
#[cfg(unix)]
mod proto;
#[cfg(unix)]
mod registry;

#[cfg(not(unix))]
fn main() {
    eprintln!("cys-seatkeep: 이 시제품은 유닉스(맥) 전용이다 — 윈도우는 T7");
    std::process::exit(2);
}

#[cfg(unix)]
fn main() {
    std::process::exit(imp::run());
}

#[cfg(unix)]
mod imp {
    use crate::peer::{self, Peer, Policy};
    use crate::proto;
    use crate::registry::{self, Ledger, Paths};
    use portable_pty::{native_pty_system, Child, CommandBuilder, MasterPty, PtySize};
    use serde_json::{json, Value};
    use std::collections::{HashSet, VecDeque};
    use std::fs::File;
    use std::io::{Read, Write};
    use std::net::Shutdown;
    use std::os::unix::io::AsRawFd;
    use std::os::unix::net::{UnixListener, UnixStream};
    use std::path::PathBuf;
    use std::sync::atomic::{AtomicBool, AtomicU8, AtomicUsize, Ordering};
    use std::sync::mpsc::{channel, sync_channel, Receiver, Sender, SyncSender};
    use std::sync::{Arc, Condvar, Mutex, MutexGuard};
    use std::time::{Duration, Instant};

    /// stderr 쓰기 — 실패해도 패닉하지 않는다(eprintln! 은 stderr 실패에서 패닉한다 · 독립 검증 D4).
    macro_rules! warn {
        ($($t:tt)*) => {{
            use std::io::Write as _;
            let _ = writeln!(std::io::stderr(), $($t)*);
        }};
    }

    const DEFAULT_TAIL: usize = 1 << 20;
    /// 꼬리 상한 — 재생은 REPLAY_CHUNK 단위로 나눠 보내므로 프레임 상한과 무관하지만 메모리 상한은 둔다.
    const MAX_TAIL: usize = 64 << 20;
    /// 꼬리 재생 프레임 1개의 바이트 상한(오프셋 8바이트 + 이것 ≤ proto::MAX_PAYLOAD).
    const REPLAY_CHUNK: usize = 1 << 20;
    /// 조종자 큐에 쌓아 둘 실시간 출력의 바이트 상한(좌석마다). 넘는 출력은 꼬리에 두고 「밀림」으로 표시했다가 따라잡는다.
    /// 값 근거(11-11 실측): 보통 좌석 출력은 초당 수 KB(A13 noisy = 초당 약 11KB/좌석) → 4MiB 는 수 분 분량이라 조종자가
    /// 수백 ms 멈춰도 밀리지 않는다. 쏟는 좌석(`yes` 초당 약 150MB)에서는 약 27ms 분량 — 그 이상 멈추면 밀림 경로로 가고
    /// 내보내지지는 않는다. 메모리 상한 = 좌석당 4MiB(40좌석이 동시에 전부 밀려도 160MiB · 평소 0).
    const OUT_QUEUE_BYTES: usize = 4 << 20;
    /// 조종자 종속 모드(`--controller-bound` ⑵)의 큐 상한 — 여기 닿으면 PTY 읽기를 멈추고 반 아래로 내려가면 다시 읽는다.
    /// OUT_QUEUE_BYTES(4MiB)보다 작게 둔다: 이미 PTY 에서 읽어 둔 바이트는 ^C 의 커널 출력 비우기(직접 PTY 는 ^C 뒤 0바이트)가
    /// 닿지 않아 ^C 뒤에도 화면에 흐르고, 조종자가 다시 읽기 시작한 뒤 자식이 움직이기까지 이만큼을 먼저 비워야 한다(재개 지연).
    /// 값 근거 = T3 실측 표(HANDOFF 「조종자 종속 모드」 — 4MiB 와 이 값의 ^C 뒤 바이트 · 재개 지연 · 폭주 처리량).
    const BOUND_QUEUE_BYTES: usize = 256 << 10;
    /// 제어 프레임(WELCOME·EXITED·INPUT_ACK·FOREGROUND_IS) 큐 바이트 상한 — 조종자가 요청을 쏟으면서 답을 느리게 읽으면
    /// 넘는다 → 그 조종자를 내보낸다(codex 2R #2 · 출력과 달리 꼬리에 둘 곳이 없으므로).
    const CTL_QUEUE_BYTES: usize = 1 << 20;
    /// 따라잡기 때 한 번에 큐에 넣는 조각 크기.
    const CATCHUP_CHUNK: usize = 256 << 10;
    /// 조종자 소켓 쓰기가 이 시간 동안 한 바이트도 못 나가면(멈춘 조종자) 연결을 닫는다. 쓰기 진척이 있으면 재설정된다.
    const CTL_WRITE_TIMEOUT: Duration = Duration::from_secs(10);
    /// 종료 기록을 디스크에 못 남기는 상태가 이만큼 이어지면(상태 폴더가 사라짐 등) stderr 에 기록을 남기고 끝낸다(독립 검증 D9).
    const EXIT_PERSIST_MAX: Duration = Duration::from_secs(30);
    const INPUT_IDS_KEPT: usize = 4096;
    /// 좌석별 아직 PTY 에 못 쓴 입력 바이트 상한. 넘는 INPUT 은 받지 않는다(수신 확인 없음 = 조종자는 「모름」).
    const INPUT_QUEUE_BYTES: usize = 1 << 20;
    /// 핸드셰이크(신원 확인 ~ HELLO ~ 수락) 전체의 절대 기한.
    const HELLO_TIMEOUT: Duration = Duration::from_secs(3);
    const HELLO_MAX: usize = 4096;
    const MAX_PENDING_HANDSHAKES: usize = 16;
    /// 모든 자식이 끝났는데 조종자가 없을 때, 종료 기록을 남기고 나가기까지 기다리는 시간.
    const EXIT_GRACE: Duration = Duration::from_secs(2);
    /// 자식 회수 뒤 PTY 의 마지막 출력을 기다리는 상한. 넘기면 EXITED 에 `output_open: true` 를 적는다.
    const DRAIN: Duration = Duration::from_secs(2);
    const COMMIT_TRIES: u64 = 3;
    /// `--controller-bound` 일 때 기동 뒤 첫 조종자를 기다리는 상한(cysd 의 기동~WELCOME 상한 10초보다 길게).
    const FIRST_CONTROLLER_MAX: Duration = Duration::from_secs(15);
    const ALL_SEATS: u32 = u32::MAX;
    /// `--controller-bound` 에서 부모(cysd)가 자식 기동 **전에** 사라졌을 때의 끝 코드(codex 1R #1) — PTY·자식을 만들지 않는다.
    const RC_PARENT_LOST: i32 = 8;
    /// `--controller-bound` 에서 부모 감시를 세우지 못함(감시 스레드 생성 실패 · 맥에서 kqueue 등록 실패) — 감시 없이 좌석을 띄우지 않는다
    /// (codex 3R #1 fail-closed). PTY·파일·자식 전에 끝낸다.
    const RC_WATCH_UNAVAILABLE: i32 = 9;

    /// 부모 감시 준비 결과(codex 3R #1).
    #[derive(Debug, Clone, Copy, PartialEq)]
    enum Watch {
        /// 등록 끝남(맥 = kqueue NOTE_EXIT · 그 밖 유닉스 = 폴링 시작)
        Ready,
        /// 등록 때 이미 상실(ESRCH · 등록 뒤 getppid 바뀜)
        Gone,
        /// 감시를 세우지 못함 → 부르는 쪽이 fail-closed
        Unavailable,
    }

    /// 부모 감시(codex 1R #1)가 부모 상실을 봤다 — 기동 단계(Keep 이 생기기 전)의 확인 자리가 읽는다.
    static PARENT_GONE: AtomicBool = AtomicBool::new(false);
    /// 부모 감시가 준비(Ready) 뒤에 감시를 잃었다(맥 kqueue 대기 실패 · codex r4 #1) — 폴링으로 대신하지 않고 fail-closed:
    /// 기동 단계면 주 스레드가 확인 자리에서 끝내고(rc 9) · Keep 이 생긴 뒤면 감시가 부모 상실과 같은 길(`end_for_controller_loss`)로 끝낸다.
    static WATCH_LOST: AtomicBool = AtomicBool::new(false);
    /// 기동이 끝나 Keep 이 생기면 여기 둔다 — 부모 감시가 상실을 보면 이것으로 바로 끝낸다(supervise 100ms 를 기다리지 않음).
    static KEEP: std::sync::OnceLock<Arc<Keep>> = std::sync::OnceLock::new();
    /// 기동 잠금(codex r4b #1) — 주 스레드는 첫 좌석의 「마지막 확인」부터 자식 spawn·`KEEP` 두기까지 쥐고, 감시는 「`WATCH_LOST` 표시 + `KEEP` 확인」을
    /// 쥐고 한다. 두 구간이 서로 끼어들 수 없으므로: 표시가 먼저면 주 스레드의 마지막 확인이 그것을 보고 spawn 하지 않고(rc 9),
    /// spawn 이 먼저면 감시는 잠금을 얻은 때 `KEEP` 을 반드시 보고 끝낸다(부모 상실과 같은 길). 잠금의 풀기→얻기가 양쪽 쓰기를 보이게 하므로
    /// `OnceLock` 의 게시(AcqRel)·확인(Acquire) 순서에 기대지 않는다. 감시 쪽 구간 안에서는 다른 잠금을 잡지 않는다(순서 역전 없음).
    static LAUNCH: Mutex<()> = Mutex::new(());
    /// 종료 집행 앞 진단 출력이 기다리는 상한(codex r4b #2) — stderr 를 아무도 안 읽어도 이만큼 뒤에는 끝을 진행한다.
    const WARN_EXIT_WAIT: Duration = Duration::from_millis(200);

    /// 종료 집행 **앞**의 진단 출력(codex r4b #2) — stderr 쓰기를 따로 스레드에서 하고 `WARN_EXIT_WAIT` 까지만 기다린다.
    /// stderr 가 막혀 있으면(가득 찬 파이프 · cysd 가 stderr 를 그대로 물려줌) 그 스레드만 막히고 종료는 그대로 간다.
    /// 스레드를 못 띄우면 쓰지 않는다.
    fn warn_before_exit(msg: String) {
        let (tx, rx) = channel::<()>();
        let spawned = std::thread::Builder::new().name("seatkeep-exit-warn".into()).spawn(move || {
            warn!("{msg}");
            let _ = tx.send(());
        });
        if spawned.is_ok() {
            let _ = rx.recv_timeout(WARN_EXIT_WAIT);
        }
    }

    /// 부모 감시를 **자식 기동 앞에서** 시작한다(codex 1R #1). 고른 길 = kqueue `EVFILT_PROC/NOTE_EXIT`(맥):
    /// 부모가 죽는 순간 깨어나 폴링 지연이 없고, 잰 뒤 등록 전에 이미 죽었으면 등록이 ESRCH 로 실패해 그 틈도 닫힌다
    /// (감시 스레드 폴링은 주기만큼 늦고 그 틈을 따로 메워야 한다 — kqueue 를 못 쓰는 곳에서만 20ms 폴링으로 대신한다).
    /// 감시가 「등록 끝남 · 이미 상실 · 폴링으로 대신 준비됨」 중 하나를 알릴 때까지 돌아오지 않는다(codex 2R #1 — 등록 전 스케줄 틈:
    /// 스레드가 아직 안 돌았는데 주 스레드가 자식을 띄우던 창). 알림이 안 오면(감시 스레드가 못 뜸) 기다리지 않고 돌아온다 —
    /// 그 경우에도 기동 확인 자리는 `getppid` 를 직접 본다(`parent_gone_early`).
    fn watch_parent(parent: i32) -> Watch {
        let (ready_tx, ready_rx) = std::sync::mpsc::channel::<Watch>();
        // 시험 전용(codex 3R #1 — 감시 스레드 생성 실패 흉내). 디버그 빌드에서만 읽는다.
        #[cfg(debug_assertions)]
        if std::env::var("CYS_SEATKEEP_TEST_WATCH_FAIL").ok().as_deref() == Some("spawn") {
            return Watch::Unavailable;
        }
        let spawned = std::thread::Builder::new().name("seatkeep-parent-watch".into()).spawn(move || {
            // 시험 전용 지연(codex 2R #1 재현 — 감시 스레드가 늦게 스케줄됨). 디버그 빌드에서만 읽는다.
            #[cfg(debug_assertions)]
            if let Some(ms) = std::env::var("CYS_SEATKEEP_TEST_WATCH_DELAY_MS").ok().and_then(|v| v.parse::<u64>().ok()) {
                std::thread::sleep(Duration::from_millis(ms));
            }
            if !wait_parent_gone(parent, &ready_tx) {
                return; // 감시를 못 세움(Unavailable 을 이미 알림) — 상실 표시를 하지 않는다(주 스레드가 끝낸다)
            }
            let _ = ready_tx.send(Watch::Gone);
            // 시험 전용 지연(codex 2R #1 재현 — 상실을 본 뒤 표시가 늦음 · 폴링 대신 창과 같은 꼴). 디버그 빌드에서만 읽는다.
            #[cfg(debug_assertions)]
            if let Some(ms) = std::env::var("CYS_SEATKEEP_TEST_GONE_DELAY_MS").ok().and_then(|v| v.parse::<u64>().ok()) {
                std::thread::sleep(Duration::from_millis(ms));
            }
            PARENT_GONE.store(true, Ordering::SeqCst);
            if let Some(k) = KEEP.get() {
                end_for_controller_loss(k, "parent_lost");
            }
        });
        match spawned {
            // 첫 알림 = 준비 결과(등록 끝남 · 이미 상실 · 못 세움). 알림 없이 채널이 닫히면(스레드가 죽음) 못 세움으로 본다.
            Ok(_) => ready_rx.recv().unwrap_or(Watch::Unavailable),
            Err(_) => Watch::Unavailable,
        }
    }

    /// 부모 `parent` 가 사라질 때까지 막힌다. 감시가 준비되면(등록 끝남 · 폴링 시작 직전) `ready` 로 알린다
    /// (상실로 곧바로 돌아오는 길은 부르는 쪽이 알린다).
    /// 돌려주는 값 = 감시를 세웠는가(거짓 = `Unavailable` 을 알렸음 · 맥에서 kqueue 를 못 씀). 참이면 상실까지 막혔다가 돌아온다.
    fn wait_parent_gone(parent: i32, ready: &std::sync::mpsc::Sender<Watch>) -> bool {
        #[cfg(target_os = "macos")]
        unsafe {
            // 시험 전용 고장 흉내(디버그 빌드만): kqueue = 첫 kqueue() 실패 · gone = 등록이 ESRCH(이미 상실) ·
            // kevent = 등록·Ready 뒤 대기 kevent() 실패(CYS_SEATKEEP_TEST_KEVENT_FAIL_DELAY_MS 뒤 · codex r4 #1).
            #[cfg(debug_assertions)]
            let forced = std::env::var("CYS_SEATKEEP_TEST_WATCH_FAIL").ok().unwrap_or_default();
            #[cfg(not(debug_assertions))]
            let forced = String::new();
            let kq = if forced == "kqueue" { -1 } else { libc::kqueue() };
            // 맥에서 kqueue 를 못 쓰면 폴링으로 대신하지 않는다(codex 3R #1 — 20ms 폴링 + 기동 확인은 안전 보장으로 세지 않음) → fail-closed.
            if kq < 0 {
                let _ = ready.send(Watch::Unavailable);
                return false;
            }
            {
                let mut ev: libc::kevent = std::mem::zeroed();
                ev.ident = parent as usize;
                ev.filter = libc::EVFILT_PROC;
                ev.flags = libc::EV_ADD | libc::EV_ONESHOT;
                ev.fflags = libc::NOTE_EXIT;
                let reg = if forced == "gone" { -1 } else { libc::kevent(kq, &ev, 1, std::ptr::null_mut(), 0, std::ptr::null()) };
                if reg < 0 {
                    // ESRCH = 등록 전에 이미 죽음. 그 밖의 실패 = 감시를 못 세움(fail-closed · codex 3R #1).
                    let gone = forced == "gone" || std::io::Error::last_os_error().raw_os_error() == Some(libc::ESRCH);
                    libc::close(kq);
                    if gone {
                        return true;
                    }
                    let _ = ready.send(Watch::Unavailable);
                    return false;
                } else {
                    // 잰 뒤 등록 전에 죽고 pid 가 재사용됐으면 남의 프로세스를 보고 있다 — 지금 부모가 그대로인지 한 번 더 본다.
                    if libc::getppid() != parent {
                        libc::close(kq);
                        return true;
                    }
                    let _ = ready.send(Watch::Ready);
                    #[cfg(debug_assertions)]
                    if forced == "kevent" {
                        if let Some(ms) = std::env::var("CYS_SEATKEEP_TEST_KEVENT_FAIL_DELAY_MS").ok().and_then(|v| v.parse::<u64>().ok()) {
                            std::thread::sleep(Duration::from_millis(ms));
                        }
                    }
                    loop {
                        let mut out: libc::kevent = std::mem::zeroed();
                        let n = if forced == "kevent" { -1 } else { libc::kevent(kq, std::ptr::null(), 0, &mut out, 1, std::ptr::null()) };
                        if n > 0 && out.fflags & libc::NOTE_EXIT != 0 {
                            libc::close(kq);
                            return true;
                        }
                        if n < 0 && (forced == "kevent" || std::io::Error::last_os_error().raw_os_error() != Some(libc::EINTR)) {
                            libc::close(kq);
                            // 등록 뒤 대기 실패 = 감시를 잃음(codex r4 #1) — 폴링으로 내려가지 않는다(fail-closed).
                            // 갈래: Keep 이 아직 없으면(기동 단계) 표시만 → 주 스레드의 기동 확인 자리가 끝낸다(자식 전 = rc 9 · 자식 뒤 = 같은 rc 9
                            // + end_early 정리 = 부모 상실과 같은 길) · Keep 이 있으면 여기서 부모 상실과 같은 길로 끝낸다.
                            // 「표시 + Keep 확인」은 기동 잠금(LAUNCH) 안에서 한다(codex r4b #1) — 주 스레드의 「마지막 확인 ~ spawn ~ Keep 두기」와
                            // 서로 끼어들 수 없다. 진단 출력은 하지 않는다(codex r4b #2 — 종료가 stderr 소비에 기대지 않게 · 까닭은 기록 watch_lost 1줄).
                            let keep = {
                                let _g = LAUNCH.lock().unwrap_or_else(|e| e.into_inner());
                                WATCH_LOST.store(true, Ordering::SeqCst);
                                test_trace("mark");
                                KEEP.get().cloned()
                            };
                            if let Some(k) = keep {
                                end_for_controller_loss(&k, "watch_lost");
                            }
                            return false;
                        }
                    }
                }
            }
        }
        // 맥 밖 유닉스 = 폴링(제품 경로 아님 · 맥은 위에서 모든 갈래가 돌아간다 — 등록 뒤 실패도 폴링으로 오지 않는다).
        #[cfg(not(target_os = "macos"))]
        {
            let _ = ready.send(Watch::Ready);
            while unsafe { libc::getppid() } == parent {
                std::thread::sleep(Duration::from_millis(20));
            }
            true
        }
    }

    /// 기동 단계 확인(자식 기동 직전·직후 · Keep 만들기 직전) — 조종자 종속 모드에서 부모가 사라졌는가.
    /// 감시 표시뿐 아니라 지금 부모를 직접 본다(codex 2R #1 — 감시가 상실을 봤지만 아직 표시 전 · 폴링 대신 20ms 창).
    fn parent_gone_early(args: &Args, parent: i32) -> bool {
        args.controller_bound && (PARENT_GONE.load(Ordering::SeqCst) || unsafe { libc::getppid() } != parent)
    }

    /// 시험 전용 순서 기록(codex r4b #1 — 「감시 상실 표시」와 「자식 spawn」 중 무엇이 먼저였나) — `CYS_SEATKEEP_TEST_TRACE_FILE` 에 한 줄씩 덧붙인다.
    /// 디버그 빌드에서만 읽는다(릴리스 = 빈 함수).
    #[cfg(debug_assertions)]
    fn test_trace(what: &str) {
        if let Ok(f) = std::env::var("CYS_SEATKEEP_TEST_TRACE_FILE") {
            use std::io::Write as _;
            if let Ok(mut fh) = std::fs::OpenOptions::new().create(true).append(true).open(f) {
                let _ = writeln!(fh, "{what}");
            }
        }
    }
    #[cfg(not(debug_assertions))]
    fn test_trace(_what: &str) {}

    /// 기동 단계 확인 — 준비 뒤 감시를 잃었는가(codex r4 #1 · fail-closed).
    fn watch_lost_early(args: &Args) -> bool {
        args.controller_bound && WATCH_LOST.load(Ordering::SeqCst)
    }

    /// 역압 모드(⑵ PTY 읽기 멈춤 · ⑶ 쓰기 기한 없음) — 종속 모드와 입양 모드 공통.
    fn backpressure(args: &Args) -> bool {
        args.controller_bound || args.adoptable
    }

    struct Args {
        dir: PathBuf,
        id: String,
        controller_exe: PathBuf,
        lock: PathBuf,
        requirement: Option<String>,
        seats: u32,
        tail_bytes: usize,
        rows: u16,
        cols: u16,
        /// `--controller-bound` — 조종자 종속 모드(맨 위 설명 ⑴⑵⑶).
        controller_bound: bool,
        /// `--adoptable` — 입양 모드(맨 위 설명 · ⑵⑶ 만 · T4).
        adoptable: bool,
        cmd: Vec<String>,
    }

    fn parse_args() -> Result<Args, String> {
        let mut it = std::env::args().skip(1);
        let (mut dir, mut id, mut exe, mut lock, mut req) = (None, None, None, None, None);
        let (mut seats, mut tail_bytes) = (1u32, DEFAULT_TAIL);
        let (mut rows, mut cols, mut controller_bound, mut adoptable) = (35u16, 120u16, false, false);
        let mut cmd = Vec::new();
        while let Some(a) = it.next() {
            match a.as_str() {
                "--dir" => dir = it.next().map(PathBuf::from),
                "--id" => id = it.next(),
                "--controller-exe" => exe = it.next().map(PathBuf::from),
                "--lock" => lock = it.next().map(PathBuf::from),
                "--requirement" => req = it.next(),
                "--seats" => seats = it.next().and_then(|v| v.parse().ok()).ok_or("--seats 숫자")?,
                "--tail-bytes" => tail_bytes = it.next().and_then(|v| v.parse().ok()).ok_or("--tail-bytes 숫자")?,
                "--rows" => rows = it.next().and_then(|v| v.parse().ok()).filter(|v| (1..=1000).contains(v)).ok_or("--rows 1..=1000")?,
                "--cols" => cols = it.next().and_then(|v| v.parse().ok()).filter(|v| (1..=1000).contains(v)).ok_or("--cols 1..=1000")?,
                "--controller-bound" => controller_bound = true,
                "--adoptable" => adoptable = true,
                "--" => {
                    cmd = it.by_ref().collect();
                }
                other => return Err(format!("모르는 인자: {other}")),
            }
        }
        let id = id.ok_or("--id 필요")?;
        if id.is_empty() || !id.chars().all(|c| c.is_ascii_alphanumeric() || c == '-' || c == '_') {
            return Err("--id 는 영숫자·-·_ 만".into());
        }
        if cmd.is_empty() {
            return Err("-- 뒤에 명령 필요".into());
        }
        if seats == 0 || seats > 512 {
            return Err("--seats 1..=512".into());
        }
        if tail_bytes == 0 || tail_bytes > MAX_TAIL {
            return Err(format!("--tail-bytes 1..={MAX_TAIL}"));
        }
        if controller_bound && adoptable {
            return Err("--controller-bound 와 --adoptable 은 함께 쓸 수 없다".into());
        }
        Ok(Args {
            dir: dir.ok_or("--dir 필요")?,
            id,
            controller_exe: exe.ok_or("--controller-exe 필요")?,
            lock: lock.ok_or("--lock 필요")?,
            requirement: req,
            seats,
            tail_bytes,
            rows,
            cols,
            controller_bound,
            adoptable,
            cmd,
        })
    }

    struct InputJob {
        id: u64,
        gen: u64,
        bytes: Vec<u8>,
    }

    struct Seat {
        id: u32,
        child_pid: i32,
        master: Mutex<Box<dyn MasterPty + Send>>,
        input: SyncSender<InputJob>,
    }

    struct SeatOut {
        tail: VecDeque<u8>,
        total: u64,
        /// 자식이 끝났음을 보았다(회수 직전에 잠금 안에서 세운다) — 이 뒤로는 그 pid·그룹에 신호를 보내지 않는다.
        reaped: bool,
        /// 회수 결과(내부). 조종자에게 알리는 것은 `exit`(아래)다.
        exit_status: Option<Value>,
        /// 알린 종료(마지막 출력 뒤 · final_offset 포함). Some = EXITED 를 냈다.
        exit: Option<Value>,
        exit_acked: bool,
        reader_done: bool,
        input_pending: usize,
        /// 입양 모드: 마지막 조종자가 끊긴 때 그 조종자가 **처리를 끝냈다고 알린** 누적 오프셋(`processed` · codex T4 1R #4) — 조종자 없는
        /// 동안 읽기 상한의 기준 · 새 조종자의 재생 나눔. 조종자가 붙으면 None.
        disc_total: Option<u64>,
        /// 조종자가 알린 처리 완료 오프셋(PROCESSED 최댓값 · ≤ total).
        processed: u64,
    }

    impl SeatOut {
        fn tail_start(&self) -> u64 {
            self.total - self.tail.len() as u64
        }
    }

    struct Controller {
        gen: u64,
        peer: Peer,
        /// 막히지 않는 큐(크기 제한은 아래 `queued` 바이트로 한다).
        tx: Sender<Vec<u8>>,
        /// 큐에 있고 아직 소켓에 못 쓴 바이트(넣을 때 +, 쓰기 스레드가 쓴 뒤 −).
        queued: Arc<AtomicUsize>,
        /// 그중 제어 프레임(OUTPUT 아닌 것) 바이트.
        ctl_queued: Arc<AtomicUsize>,
        /// 내보내기용 소켓 사본 — shutdown 하면 serve 의 읽기와 쓰기 스레드가 함께 끝난다.
        shut: UnixStream,
        /// 좌석별 「밀림」 시작 오프셋 — Some 이면 그 오프셋부터는 꼬리에만 있고 아직 이 조종자에게 안 갔다.
        behind: Vec<Option<u64>>,
        /// 밀린 좌석이 하나라도 있는가(쓰기 스레드가 잠금 없이 보는 표시).
        behind_flag: Arc<AtomicBool>,
        /// 좌석별 EXITED 를 이 조종자에게 보냈는가(밀린 좌석의 EXITED 는 따라잡기가 끝난 뒤 보낸다 — 순서 보존).
        exited_sent: Vec<bool>,
        /// 쓰기 스레드가 멈춤·오류로 연결을 닫았다(끊김 기록에 실림).
        evicted: bool,
    }

    struct State {
        out: Vec<SeatOut>,
        controller: Option<Controller>,
        gen: u64,
        last_peer: Option<(Peer, f64)>,
        no_controller_since: Option<Instant>,
        input_ids: (VecDeque<u64>, HashSet<u64>),
        /// 미확인 종료 기록이 디스크에 있는가(없을 게 없으면 참). 거짓이면 조종자 없이 끝내지 않는다.
        exit_record_ok: bool,
        exit_record_warned: bool,
        /// 종료 기록 쓰기가 처음 실패한 때(성공하면 지움) — EXIT_PERSIST_MAX 판정용.
        exit_record_fail_since: Option<Instant>,
    }

    struct Keep {
        args: Args,
        paths: Paths,
        policy: Policy,
        seats: Vec<Seat>,
        st: Mutex<State>,
        ledger: Mutex<Ledger>,
        boot_id: String,
        start_us: Option<u64>,
        pending_hs: AtomicUsize,
        /// 프로세스 시작(단조) — `--controller-bound` 첫 조종자 상한.
        started: Instant,
        /// `--controller-bound` 역압: PTY 읽기를 멈추고 기다리는 읽기 스레드를 깨운다(상태 잠금 `st` 와 짝).
        room: Condvar,
        /// 그 기다리는 읽기 스레드 수 — 쓰기 스레드가 잠금 없이 보고 0 이 아닐 때만 잠금을 잡아 깨운다.
        room_waiters: AtomicUsize,
        /// 기동 때의 부모 pid — `--controller-bound` 에서 이것이 바뀌면(부모 = cysd 가 죽음) 첫 조종자 전이라도 끝낸다(D2).
        parent_pid: i32,
        /// 종료 소유자(codex 1R #4) — 끝내는 길(연결 끊김 · 부모 감시 · supervise)이 동시에 와도 기록·등록부 쓰기는 이긴 1명만.
        exit_owner: AtomicBool,
        /// 같은 id 의 두 번째 seatkeep 을 막는 잠금 — 프로세스가 끝날 때까지 쥔다.
        _id_lock: File,
    }

    fn lock_st(keep: &Keep) -> MutexGuard<'_, State> {
        keep.st.lock().unwrap_or_else(|e| e.into_inner())
    }

    fn peer_json(p: &Peer) -> Value {
        json!({"pid": p.pid, "pidversion": p.pidversion, "euid": p.euid,
               "exe": p.exe.as_ref().map(|e| e.to_string_lossy().into_owned()),
               "start_us": registry::process_start_us(p.pid)})
    }

    impl Keep {
        /// 교체 기록 1줄. 잠금 순서 = 상태(st) → 기록(ledger) — 반대로 잡는 곳은 없다.
        fn log(&self, mut v: Value) -> Result<(), registry::LineError> {
            v["t"] = json!(registry::now_epoch());
            v["seatkeep"] = json!(self.args.id);
            v["seatkeep_pid"] = json!(std::process::id());
            self.ledger.lock().unwrap_or_else(|e| e.into_inner()).line(&v)
        }

        fn entry(&self, phase: &str) -> Value {
            json!({
                "phase": phase,
                "id": self.args.id,
                "pid": std::process::id(),
                "start_us": self.start_us,
                "boot_id": self.boot_id,
                "sock": self.paths.sock.to_string_lossy(),
                "core": proto::CORE_VERSION,
                "mode": if self.args.seats == 1 { "per-seat" } else { "per-build" },
                "seats": self.seats.iter().map(|s| json!({"seat": s.id, "pid": s.child_pid,
                         "start_us": registry::process_start_us(s.child_pid)})).collect::<Vec<_>>(),
                "at": registry::now_epoch(),
            })
        }

        /// 알린 종료들을 `<id>.exit` 에 영속한다(전부 확인되면 지운다). 결과를 상태에 남긴다 — 실패면
        /// supervise 가 다시 쓰고, 성공 전에는 조종자 없이 끝내지 않는다(codex 1R #5).
        fn persist_exit_record(&self, st: &mut State) {
            let v: Vec<Value> = st
                .out
                .iter()
                .enumerate()
                .filter_map(|(i, o)| o.exit.clone().map(|e| json!({"seat": i, "exit": e, "acked": o.exit_acked})))
                .collect();
            if v.is_empty() {
                st.exit_record_ok = true;
                st.exit_record_fail_since = None;
                return;
            }
            if v.iter().all(|e| e["acked"] == json!(true)) {
                // 지울 것뿐 — 보존할 미확인 기록이 없으니 실패해도 끝내는 것을 막지 않는다(기록만 남김).
                match std::fs::remove_file(&self.paths.exit) {
                    Ok(()) => {}
                    Err(e) if e.kind() == std::io::ErrorKind::NotFound => {}
                    Err(e) => {
                        let _ = self.log(json!({"event": "exit_record_remove_failed", "error": e.to_string()}));
                    }
                }
                st.exit_record_ok = true;
                st.exit_record_fail_since = None; // 보존할 미확인 기록이 없다 — 앞선 실패 시각을 다음 실패에 쓰지 않는다(codex 2R #5)
                return;
            }
            match registry::write_atomic(&self.paths.exit, &json!({"id": self.args.id, "seats": v})) {
                Ok(()) => {
                    st.exit_record_ok = true;
                    st.exit_record_fail_since = None;
                }
                Err(e) => {
                    st.exit_record_ok = false;
                    st.exit_record_fail_since.get_or_insert_with(Instant::now);
                    if !st.exit_record_warned {
                        st.exit_record_warned = true;
                        warn!("cys-seatkeep: 종료 기록 쓰기 실패(다시 시도함): {e}");
                        let _ = self.log(json!({"event": "exit_record_write_failed", "error": e.to_string()}));
                    }
                }
            }
        }
    }

    /// 조종자에게 프레임 1개 — **상태 잠금 안에서만** 부른다(순서 보존 · 막히지 않음 · 제어 프레임용).
    fn send_ctl(keep: &Keep, st: &mut State, frame: Vec<u8>) {
        let Some(c) = st.controller.as_mut() else { return };
        if !enqueue(&c.tx, &c.queued, &c.ctl_queued, frame) {
            evict_ctl_full(keep, c);
        }
    }

    /// 제어 큐가 상한에 닿았다 — 이 조종자를 내보낸다(읽기·쓰기 양쪽을 깨워 정리로 이어짐 · 기록은 한 번만).
    fn evict_ctl_full(keep: &Keep, c: &mut Controller) {
        if !c.evicted {
            c.evicted = true;
            let _ = c.shut.shutdown(Shutdown::Both);
            let (gen, peer) = (c.gen, peer_json(&c.peer));
            let _ = keep.log(json!({"event": "evict", "gen": gen, "reason": "control_queue_full", "peer": peer}));
        }
    }

    /// 큐에 넣는 **단 하나의 길** — 바이트 셈(전체 · 제어)을 함께 올린다. 쓰기 스레드가 `written` 으로 같은 규칙대로 내린다.
    /// 제어 프레임(OUTPUT 아닌 것)은 여기서 상한을 잰다: 넣으면 제어 바이트가 CTL_QUEUE_BYTES 를 넘는 프레임은 넣지 않고
    /// (셈 불변) 거짓을 돌려준다 — 부르는 쪽이 최초 재생이면 접속 거절, 활성 연결이면 내보낸다(codex 3R #1: 전에는 send_ctl
    /// 만 재서 catch_up 의 EXITED · 최초 WELCOME·EXITED 가 상한을 우회했다). 넣는 곳은 모두 상태 잠금 안(또는 아직 아무도
    /// 모르는 새 큐)이라 검사와 셈 올리기 사이에 다른 넣기가 끼지 않는다(쓰기 스레드는 내리기만 한다).
    #[must_use]
    fn enqueue(tx: &Sender<Vec<u8>>, queued: &AtomicUsize, ctl_queued: &AtomicUsize, frame: Vec<u8>) -> bool {
        if frame[0] != proto::OUTPUT {
            if ctl_queued.load(Ordering::SeqCst) + frame.len() > CTL_QUEUE_BYTES {
                return false;
            }
            ctl_queued.fetch_add(frame.len(), Ordering::SeqCst);
        }
        queued.fetch_add(frame.len(), Ordering::SeqCst);
        // 실패 = 쓰기 스레드가 이미 끝났다(소켓 오류·멈춤 기한) — serve 가 곧 끊김을 정리한다.
        let _ = tx.send(frame);
        true
    }

    /// 쓰기 스레드가 프레임 1개를 소켓에 쓴 뒤 — 셈을 내리고, **내린 뒤에** 밀림 표시를 본다(send_output 은 「표시를 세운 뒤
    /// 큐를 본다」 · 둘 중 하나는 반드시 상대의 쓰기를 본다 · codex 2R #1). 참 = 큐가 반 아래이고 밀린 좌석이 있다 → 따라잡기.
    fn written(queued: &AtomicUsize, ctl_queued: &AtomicUsize, behind_flag: &AtomicBool, frame: &[u8]) -> bool {
        queued.fetch_sub(frame.len(), Ordering::SeqCst);
        if frame[0] != proto::OUTPUT {
            ctl_queued.fetch_sub(frame.len(), Ordering::SeqCst);
        }
        behind_flag.load(Ordering::SeqCst) && queued.load(Ordering::SeqCst) < OUT_QUEUE_BYTES / 2
    }

    /// 새 조종자의 첫 큐(WELCOME + 꼬리 재생 + 알린 종료)를 같은 길(enqueue)로 채운다. 제어 상한을 넘으면 None — 접속 거절.
    fn queue_initial(frames: Vec<Vec<u8>>, queued: &AtomicUsize, ctl_queued: &AtomicUsize) -> Option<(Sender<Vec<u8>>, Receiver<Vec<u8>>)> {
        let (tx, rx) = channel::<Vec<u8>>();
        for f in frames {
            if !enqueue(&tx, queued, ctl_queued, f) {
                return None;
            }
        }
        Some((tx, rx))
    }

    /// 실시간 출력 — 밀린 바이트가 상한을 넘거나 이 좌석이 이미 밀려 있으면 큐에 넣지 않고 「밀림」으로 둔다
    /// (데이터는 꼬리에 있다 · 쓰기 스레드가 큐를 비우면 catch_up 이 그 오프셋부터 보낸다).
    fn send_output(keep: &Keep, st: &mut State, i: usize, offset: u64, bytes: &[u8]) {
        let Some(c) = st.controller.as_mut() else { return };
        if c.behind[i].is_some() {
            return;
        }
        // 조종자 종속 모드(⑵) = 밀림이 없다 — 늘 큐에 넣고, 큐가 상한에 닿으면 읽기 스레드가 PTY 읽기를 멈춘다(`wait_for_room`).
        // 큐가 상한을 넘는 폭 = 읽기 스레드마다 읽기 버퍼 1개(READ_BUF)뿐이다.
        if !backpressure(&keep.args) && c.queued.load(Ordering::SeqCst) + bytes.len() > OUT_QUEUE_BYTES {
            c.behind[i] = Some(offset);
            c.behind_flag.store(true, Ordering::SeqCst);
            // 깨우기 유실 방지(codex 2R #1): 쓰기 스레드가 표시를 세우기 전에 큐를 다 비우고 잠들었으면 아무도 따라잡지 않는다.
            // 표시를 세운 뒤(SeqCst) 큐를 다시 봐서 이미 반 아래면 여기서 바로 따라잡는다 — 쓰기 스레드는 「줄인 뒤 표시를 본다」,
            // 여기는 「표시를 세운 뒤 큐를 본다」이므로 둘 중 하나는 반드시 상대의 쓰기를 본다.
            if c.queued.load(Ordering::SeqCst) < OUT_QUEUE_BYTES / 2 {
                catch_up(keep, st);
            }
            return;
        }
        send_ctl(keep, st, proto::frame(proto::OUTPUT, keep.seats[i].id, &proto::output_payload(offset, bytes)));
    }

    /// 밀린 좌석을 꼬리에서 따라잡는다(상태 잠금 안 · 큐 상한까지만). 꼬리에서 이미 밀려난 앞부분은 건너뛴다(오프셋이
    /// 뛰어 조종자에게는 유실로 보인다). 따라잡기가 끝난 좌석에 알린 종료가 있으면 그 뒤에 EXITED 를 보낸다.
    fn catch_up(keep: &Keep, st: &mut State) {
        let State { out, controller, .. } = st;
        let Some(c) = controller.as_mut() else { return };
        let mut frames = Vec::new();
        let mut any_behind = false;
        let mut budget = OUT_QUEUE_BYTES.saturating_sub(c.queued.load(Ordering::SeqCst));
        for (i, o) in out.iter().enumerate() {
            let Some(from) = c.behind[i] else { continue };
            let mut from = from.max(o.tail_start());
            while from < o.total && budget > 0 {
                let n = ((o.total - from) as usize).min(CATCHUP_CHUNK).min(budget.max(1));
                let skip = (from - o.tail_start()) as usize;
                let bytes: Vec<u8> = o.tail.range(skip..skip + n).copied().collect();
                frames.push(proto::frame(proto::OUTPUT, keep.seats[i].id, &proto::output_payload(from, &bytes)));
                budget = budget.saturating_sub(n);
                from += n as u64;
            }
            if from >= o.total {
                c.behind[i] = None;
                if let (Some(e), false) = (&o.exit, c.exited_sent[i]) {
                    frames.push(proto::json_frame(proto::EXITED, keep.seats[i].id, e));
                    c.exited_sent[i] = true;
                }
            } else {
                c.behind[i] = Some(from);
                any_behind = true;
            }
        }
        c.behind_flag.store(any_behind, Ordering::SeqCst);
        for f in frames {
            // 밀린 좌석의 EXITED 도 제어 상한을 탄다(codex 3R #1) — 넘으면 이 조종자를 내보낸다(뒤 프레임은 의미 없음).
            if !enqueue(&c.tx, &c.queued, &c.ctl_queued, f) {
                evict_ctl_full(keep, c);
                break;
            }
        }
    }

    /// 세대가 같은 조종자에게만 보낸다(옛 조종자의 요청에 대한 답이 새 조종자에게 가지 않게).
    fn send_gen(keep: &Keep, st: &mut State, gen: u64, frame: Vec<u8>) {
        if st.controller.as_ref().map(|c| c.gen) == Some(gen) {
            send_ctl(keep, st, frame);
        }
    }

    /// 회수하지 않고 끝남만 본다(WNOWAIT) — 이 사이 pid 는 좀비로 남아 재사용되지 않는다.
    fn wait_exit_nowait(pid: i32) -> bool {
        loop {
            let mut info: libc::siginfo_t = unsafe { std::mem::zeroed() };
            let rc = unsafe { libc::waitid(libc::P_PID, pid as libc::id_t, &mut info, libc::WEXITED | libc::WNOWAIT) };
            if rc == 0 {
                return true;
            }
            if std::io::Error::last_os_error().raw_os_error() != Some(libc::EINTR) {
                return false;
            }
        }
    }

    fn kill_children(keep: &Keep, sig: i32) {
        let st = lock_st(keep);
        for (i, s) in keep.seats.iter().enumerate() {
            if !st.out[i].reaped && s.child_pid > 0 {
                unsafe { libc::killpg(s.child_pid, sig) };
            }
        }
    }

    pub fn run() -> i32 {
        // 띄운 부모(조종자 종속 모드 = cysd) — 가장 먼저 잰다(독립 검증 D2 · supervise 가 바뀌는지 본다).
        let parent_pid = unsafe { libc::getppid() };
        let args = match parse_args() {
            Ok(a) => a,
            Err(e) => {
                warn!("cys-seatkeep: {e}");
                return 2;
            }
        };
        // 조종자 종속 모드(codex 1R #1): 띄운 부모가 이미 없으면(기동 때 1 = launchd 아래) PTY·자식을 만들기 전에 끝낸다.
        // 있으면 감시를 지금(자식 기동 앞) 시작하고, 아래 기동 단계마다 확인한다.
        if args.controller_bound {
            if parent_pid <= 1 {
                warn!("cys-seatkeep: 띄운 부모(조종자)가 기동 전에 사라짐(ppid {parent_pid}) — 좌석을 만들지 않고 끝낸다");
                return RC_PARENT_LOST;
            }
            // 시험 전용(codex 2R #1 시험이 「부모를 잰 뒤」를 기다리는 표지). 디버그 빌드에서만 읽는다.
            #[cfg(debug_assertions)]
            if let Ok(f) = std::env::var("CYS_SEATKEEP_TEST_PARENT_SEEN_FILE") {
                let _ = std::fs::write(f, parent_pid.to_string());
            }
            // Ready 만 진행한다(codex r4 #2 — Gone 도 상태 폴더·잠금·장부·등록부를 만들기 전에 끝).
            match watch_parent(parent_pid) {
                Watch::Ready => {}
                Watch::Gone => {
                    warn!("cys-seatkeep: 띄운 부모(조종자)가 감시 등록 때 이미 사라짐 — 좌석을 만들지 않고 끝낸다");
                    return RC_PARENT_LOST;
                }
                Watch::Unavailable => {
                    warn!("cys-seatkeep: 부모(조종자) 감시를 세우지 못함 — 감시 없이 좌석을 만들지 않고 끝낸다");
                    return RC_WATCH_UNAVAILABLE;
                }
            }
        }
        // 조종자(cysd)와 다른 세션 — 조종자가 죽어도 이 프로세스에 SIGHUP 이 오지 않는다. 실패 = 그 보장이 없으니 시작하지 않는다.
        if unsafe { libc::setsid() } == -1 {
            warn!("cys-seatkeep: setsid 실패(이미 그룹 대표로 띄워졌는가): {}", std::io::Error::last_os_error());
            return 3;
        }
        let paths = Paths::new(&args.dir, &args.id);
        // 맥 소켓 경로 한도 = sun_path[104](NUL 포함) — 어떤 파일도 만들기 전에 잰다(prepare 잔재 방지 · 독립 검증 D5).
        {
            use std::os::unix::ffi::OsStrExt;
            if paths.sock.as_os_str().as_bytes().len() >= 104 {
                warn!("cys-seatkeep: 소켓 경로가 너무 길다({}바이트 ≥ 104): {}", paths.sock.as_os_str().as_bytes().len(), paths.sock.display());
                return 2;
            }
        }
        if let Err(e) = paths.ensure_dir() {
            warn!("cys-seatkeep: 상태 폴더: {e}");
            return 3;
        }
        // ⓪ id 잠금 — 같은 id 의 두 번째 seatkeep 은 어떤 파일도 건드리기 전에 물러난다(동시 기동 포함 · codex 1R #6).
        let id_lock = match registry::lock_id(&paths.idlock) {
            Ok(f) => f,
            Err(e) => {
                warn!("cys-seatkeep: 같은 id 의 seatkeep 이 있다(잠금 {}): {e}", paths.idlock.display());
                return 4;
            }
        };
        // 앞선 기동이 남긴 미확인 종료 기록이 있으면 이 id 를 다시 쓰지 않는다 — 덮으면 그 기록이 사라진다(codex 1R #12).
        if paths.exit.exists() {
            warn!("cys-seatkeep: 미소비 종료 기록 {} — 조종자가 소비하기 전에는 이 id 를 다시 쓰지 않는다", paths.exit.display());
            return 4;
        }
        let ledger = match Ledger::open(&paths.log) {
            Ok(l) => l,
            Err(e) => {
                warn!("cys-seatkeep: 교체 기록 열기 실패: {e}");
                return 3;
            }
        };
        let policy = Policy { controller_exe: args.controller_exe.clone(), requirement: args.requirement.clone(), lock: args.lock.clone() };
        // 자기 신원 성분(부팅 id · 시작 시각)이 없으면 등록부가 pid 재사용과 구분되지 않는다 — 시작하지 않는다.
        let boot_id = registry::boot_id();
        let start_us = registry::process_start_us(std::process::id() as i32);
        if boot_id.is_empty() || start_us.is_none() {
            warn!("cys-seatkeep: 자기 신원(부팅 id·시작 시각)을 못 읽음 — 시작하지 않는다");
            return 3;
        }

        // ① 준비 — 자식보다 먼저 등록부에 「준비」를 쓴다(조종자가 이 사이에 죽어도 새 조종자가 찾을 수 있게).
        let prepare = json!({"phase": "prepare", "id": args.id, "pid": std::process::id(), "start_us": start_us,
                             "boot_id": boot_id, "sock": paths.sock.to_string_lossy(), "core": proto::CORE_VERSION,
                             "at": registry::now_epoch()});
        if let Err(e) = registry::write_atomic(&paths.entry, &prepare) {
            warn!("cys-seatkeep: 등록부 준비 실패: {e}");
            return 3;
        }

        // ② 소켓 — id 잠금을 쥐었으니 남아 있는 소켓 파일은 죽은 것이다.
        let _ = std::fs::remove_file(&paths.sock);
        let listener = match UnixListener::bind(&paths.sock) {
            Ok(l) => l,
            Err(e) => {
                warn!("cys-seatkeep: 소켓 열기 실패: {e}");
                return 3;
            }
        };
        use std::os::unix::fs::PermissionsExt;
        let _ = std::fs::set_permissions(&paths.sock, std::fs::Permissions::from_mode(0o600));

        // ③ 자식 기동
        let mut seats = Vec::new();
        let mut children: Vec<Box<dyn Child + Send + Sync>> = Vec::new();
        let mut readers = Vec::new();
        let mut inputs: Vec<(Receiver<InputJob>, Box<dyn Write + Send>)> = Vec::new();
        // 기동 잠금(codex r4b #1) — 첫 좌석의 마지막 확인 앞에서 잡아 Keep 두기·그 뒤 확인까지 쥔다(LAUNCH 설명).
        let mut launch: Option<MutexGuard<'static, ()>> = None;
        for i in 0..args.seats {
            // 시험 전용 지연(codex 1R #1 재현 — 부모를 잰 뒤 자식 기동 전 창을 넓힌다). 디버그 빌드에서만 읽는다.
            #[cfg(debug_assertions)]
            if let Some(ms) = std::env::var("CYS_SEATKEEP_TEST_SPAWN_DELAY_MS").ok().and_then(|v| v.parse::<u64>().ok()) {
                std::thread::sleep(Duration::from_millis(ms));
            }
            if launch.is_none() {
                launch = Some(LAUNCH.lock().unwrap_or_else(|e| e.into_inner()));
            }
            // 자식 기동 직전 — 부모가 사라졌으면 이 좌석을 만들지 않는다(codex 1R #1) · 감시를 잃었어도 같다(codex r4 #1 · rc 9).
            if parent_gone_early(&args, parent_pid) {
                return end_early_parent_lost(&args, &paths, ledger, &seats);
            }
            if watch_lost_early(&args) {
                return end_early(&args, &paths, ledger, &seats, "watch_lost", RC_WATCH_UNAVAILABLE);
            }
            // 시험 전용 틈(codex r4b #1 재현 — 「마지막 확인」을 통과한 뒤 spawn 전에 멈춘다). 디버그 빌드에서만 읽는다.
            #[cfg(debug_assertions)]
            if let Some(ms) = std::env::var("CYS_SEATKEEP_TEST_SPAWN_GAP_MS").ok().and_then(|v| v.parse::<u64>().ok()) {
                std::thread::sleep(Duration::from_millis(ms));
            }
            let pair = match native_pty_system().openpty(PtySize { rows: args.rows, cols: args.cols, pixel_width: 0, pixel_height: 0 }) {
                Ok(p) => p,
                Err(e) => {
                    warn!("cys-seatkeep: openpty: {e}");
                    return 5;
                }
            };
            let mut cb = CommandBuilder::new(&args.cmd[0]);
            cb.args(&args.cmd[1..]);
            // 작업 폴더 = 상속 그대로(독립 검증 D7): 조종자(cysd)가 폴더를 확인하고 그 폴더에서 seatkeep 을 띄웠다 — 여기서 다시 찾지
            // 않는다(`current_dir()` 경로 → portable-pty 의 「폴더가 아니면 HOME」 다시 찾기는 그 사이 폴더·HOME 이 지워지면 ENOENT).
            // "." = 지금 들어가 있는 그 폴더(지워졌어도 들어가 있는 동안은 유효) — 직접 PTY 가 확인 즉시 exec 하는 것과 같은 결과.
            cb.cwd(".");
            cb.env("CYS_SEATKEEP_SEAT", i.to_string());
            test_trace("spawn");
            let child = match pair.slave.spawn_command(cb) {
                Ok(c) => c,
                Err(e) => {
                    // 그래도 실패하고 작업 폴더가 사라졌으면 이유를 붙여 따로 끝낸다(rc 7 · cysd 가 문구로 알린다).
                    if !std::path::Path::new(".").is_dir() {
                        warn!("cys-seatkeep: spawn: 작업 폴더가 사라짐: {e}");
                        return 7;
                    }
                    warn!("cys-seatkeep: spawn: {e}");
                    return 5;
                }
            };
            drop(pair.slave);
            let child_pid = child.process_id().unwrap_or(0) as i32;
            let reader = match pair.master.try_clone_reader() {
                Ok(r) => r,
                Err(e) => {
                    warn!("cys-seatkeep: reader: {e}");
                    return 5;
                }
            };
            let writer = match pair.master.take_writer() {
                Ok(w) => w,
                Err(e) => {
                    warn!("cys-seatkeep: writer: {e}");
                    return 5;
                }
            };
            let (itx, irx) = sync_channel::<InputJob>(256);
            seats.push(Seat { id: i, child_pid, master: Mutex::new(pair.master), input: itx });
            children.push(child);
            readers.push(reader);
            inputs.push((irx, writer));
            // 자식 기동 직후 — 그 사이 부모가 사라졌으면 곧바로 끝낸다(마스터가 닫혀 방금 띄운 좌석에 SIGHUP · 확정·감독 없음).
            if parent_gone_early(&args, parent_pid) {
                return end_early_parent_lost(&args, &paths, ledger, &seats);
            }
            if watch_lost_early(&args) {
                return end_early(&args, &paths, ledger, &seats, "watch_lost", RC_WATCH_UNAVAILABLE);
            }
        }

        let keep = Arc::new(Keep {
            st: Mutex::new(State {
                out: (0..args.seats)
                    .map(|_| SeatOut {
                        tail: VecDeque::new(),
                        total: 0,
                        reaped: false,
                        exit_status: None,
                        exit: None,
                        exit_acked: false,
                        reader_done: false,
                        disc_total: None,
                        processed: 0,
                        input_pending: 0,
                    })
                    .collect(),
                controller: None,
                gen: 0,
                last_peer: None,
                no_controller_since: Some(Instant::now()),
                input_ids: (VecDeque::new(), HashSet::new()),
                exit_record_ok: true,
                exit_record_warned: false,
                exit_record_fail_since: None,
            }),
            ledger: Mutex::new(ledger),
            paths,
            policy,
            seats,
            boot_id,
            start_us,
            args,
            pending_hs: AtomicUsize::new(0),
            started: Instant::now(),
            room: Condvar::new(),
            room_waiters: AtomicUsize::new(0),
            parent_pid,
            exit_owner: AtomicBool::new(false),
            _id_lock: id_lock,
        });
        // 부모 감시가 이제부터 바로 끝낼 수 있게 둔다 — 두기 전에 상실을 봤으면(감시는 Keep 이 없어 기록만 함) 여기서 끝낸다.
        // 부모 상실 감시 = 「상실 표시 → Keep 확인」 · 여기 = 「Keep 두기 → 상실 확인」(+ supervise 100ms 폴링이 뒷받침) — 둘 다면 종료 소유자 1명.
        // 감시 상실(watch_lost)은 기동 잠금 안이라 이 확인 자리까지 표시가 설 수 없다(뒷받침 확인으로만 둔다 · codex r4b #1).
        let _ = KEEP.set(Arc::clone(&keep));
        if parent_gone_early(&keep.args, keep.parent_pid) {
            end_for_controller_loss(&keep, "parent_lost");
        }
        if watch_lost_early(&keep.args) {
            end_for_controller_loss(&keep, "watch_lost");
        }
        // 여기서 기동 잠금을 푼다 — 그 사이 감시가 상실을 봤으면 이제 잠금을 얻어 Keep 을 보고 끝낸다(spawn 직후 상실과 같은 길).
        drop(launch);

        for (i, r) in readers.into_iter().enumerate() {
            let k = Arc::clone(&keep);
            std::thread::spawn(move || read_loop(k, i, r));
        }
        for (i, c) in children.into_iter().enumerate() {
            let k = Arc::clone(&keep);
            std::thread::spawn(move || wait_loop(k, i, c));
        }
        for (i, (rx, w)) in inputs.into_iter().enumerate() {
            let k = Arc::clone(&keep);
            std::thread::spawn(move || input_loop(k, i, rx, w));
        }

        // 시험 전용 지연(A14① — 기동~확정 사이 창을 넓힌다). 디버그 빌드에서만 읽는다 — 릴리스(제품) 빌드에는 이 문장이 없다(T2 인계 10 · T3).
        #[cfg(debug_assertions)]
        if let Some(ms) = std::env::var("CYS_SEATKEEP_TEST_COMMIT_DELAY_MS").ok().and_then(|v| v.parse::<u64>().ok()) {
            std::thread::sleep(Duration::from_millis(ms));
        }
        // ④ 확정 — 실패하면 다시 시도하고, 끝내 못 쓰면 자식을 정리하고 끝낸다(등록부 밖 작성자 금지 · codex 1R #7).
        let mut committed = false;
        for k in 0..COMMIT_TRIES {
            match registry::write_atomic(&keep.paths.entry, &keep.entry("committed")) {
                Ok(()) => {
                    committed = true;
                    break;
                }
                Err(e) => {
                    warn!("cys-seatkeep: 등록부 확정 실패({}/{COMMIT_TRIES}): {e}", k + 1);
                    std::thread::sleep(Duration::from_millis(100 * (k + 1)));
                }
            }
        }
        if !committed {
            let _ = keep.log(json!({"event": "commit_failed"}));
            kill_children(&keep, libc::SIGHUP);
            std::thread::sleep(Duration::from_millis(500));
            kill_children(&keep, libc::SIGKILL);
            let _ = std::fs::remove_file(&keep.paths.sock);
            return 3;
        }
        let _ = keep.log(json!({"event": "spawned", "seats": keep.seats.iter().map(|s| json!({"seat": s.id, "pid": s.child_pid})).collect::<Vec<_>>()}));

        {
            let k = Arc::clone(&keep);
            std::thread::spawn(move || accept_loop(k, listener));
        }
        supervise(keep)
    }

    /// 기동 단계(Keep 이 생기기 전)에 부모 상실을 봤다 — 기록 1줄 · 등록부 `ended_controller_lost` · 소켓 삭제 뒤 RC_PARENT_LOST.
    /// 이미 띄운 좌석이 있으면 이 프로세스가 끝나며 마스터가 닫혀 SIGHUP(end_for_controller_loss 와 같은 경로 · 자식에게 신호 안 보냄).
    /// 이 단계에서 끝내는 쪽은 주 스레드 하나뿐이다(감시는 Keep 이 없으면 표시만 한다) — 종료 소유자 다툼 없음.
    fn end_early_parent_lost(args: &Args, paths: &Paths, ledger: Ledger, seats: &[Seat]) -> i32 {
        end_early(args, paths, ledger, seats, "parent_lost", RC_PARENT_LOST)
    }

    /// 기동 단계 끝(부모 상실 · 감시 잃음 codex r4 #1) — 같은 정리 길: 기록 1줄(`why`) · 소켓 삭제 · 등록부 `ended_controller_lost` · `rc`.
    fn end_early(args: &Args, paths: &Paths, mut ledger: Ledger, seats: &[Seat], why: &str, rc: i32) -> i32 {
        let pids: Vec<i32> = seats.iter().map(|s| s.child_pid).collect();
        let _ = ledger.line(&json!({"event": "seatkeep_exit", "reason": why, "phase": "starting", "spawned": pids,
                                    "t": registry::now_epoch(), "seatkeep": args.id, "seatkeep_pid": std::process::id()}));
        let _ = std::fs::remove_file(&paths.sock);
        let _ = registry::write_atomic(&paths.entry, &json!({"phase": "ended_controller_lost", "id": args.id, "pid": std::process::id(),
                                                              "core": proto::CORE_VERSION, "spawned": pids, "at": registry::now_epoch()}));
        // 종료 집행(= 이 프로세스가 끝나 마스터가 닫힘) 앞이므로 stderr 소비에 기대지 않는다(codex r4b #2).
        warn_before_exit(format!("cys-seatkeep: 기동 중 끝냄({why}) — 좌석 {}개 띄운 상태에서 끝낸다", pids.len()));
        rc
    }

    /// PTY 읽기 버퍼 크기.
    const READ_BUF: usize = 16 * 1024;

    /// `--controller-bound` ⑵ 역압 — PTY 를 읽기 **전에** 조종자에게 못 보낸 출력이 상한에 닿았으면 읽지 않고 기다린다.
    /// 그동안 커널 PTY 버퍼가 차서 자식의 쓰기가 멈춘다(직접 PTY 를 쥔 조종자가 늦게 읽을 때와 같다 · 입력·신호 길은 막지 않는다).
    /// 상한 = BOUND_QUEUE_BYTES 에 닿으면 멈추고, 반(BOUND_QUEUE_BYTES/2) 아래로 내려가면 다시 읽는다. 첫 조종자가 붙기 전(gen 0)에는
    /// 꼬리가 아직 아무에게도 안 간 출력이므로 꼬리의 남은 칸만큼만 읽고, 꼬리가 차면 멈춘다(첫 WELCOME 재생이 꼬리를 큐로 옮긴다).
    /// 돌려주는 값 = 이번에 읽어도 되는 바이트 수(1..=READ_BUF).
    /// 깨우기 유실 방지: 기다리는 쪽은 「`room_waiters` 를 올린 뒤 큐를 본다」, 쓰기 스레드는 「큐를 내린 뒤 `room_waiters` 를 본다」
    /// (둘 다 SeqCst) — 둘 중 하나는 반드시 상대의 쓰기를 본다(`written` 의 밀림 표시와 같은 모양). 깨우는 쪽은 상태 잠금을 잡고 깨운다.
    fn wait_for_room(keep: &Keep, i: usize) -> usize {
        let mut st = lock_st(keep);
        keep.room_waiters.fetch_add(1, Ordering::SeqCst);
        let mut limit = BOUND_QUEUE_BYTES;
        let room = loop {
            let room = match st.controller.as_ref() {
                Some(c) if c.queued.load(Ordering::SeqCst) >= limit => 0,
                Some(_) => READ_BUF,
                None if st.gen == 0 => keep.args.tail_bytes.saturating_sub(st.out[i].tail.len()).min(READ_BUF),
                // 입양 모드: 조종자를 잃은 뒤 출력이 꼬리를 넘기 전까지만 읽는다(넘으면 역압 — 다음 조종자가 붙을 때 깨운다).
                None if keep.args.adoptable => {
                    let o = &st.out[i];
                    let since = o.total.saturating_sub(o.disc_total.unwrap_or(o.total));
                    (keep.args.tail_bytes as u64).saturating_sub(since).min(READ_BUF as u64) as usize
                }
                None => READ_BUF, // 조종자를 잃었다 — 곧 끝난다(end_for_controller_loss)
            };
            if room > 0 {
                break room;
            }
            limit = BOUND_QUEUE_BYTES / 2;
            st = keep.room.wait(st).unwrap_or_else(|e| e.into_inner());
        };
        keep.room_waiters.fetch_sub(1, Ordering::SeqCst);
        room
    }

    /// 쓰기 스레드가 프레임 1개를 쓴 뒤 — 조종자 종속 모드에서 기다리는 읽기 스레드가 있고 큐가 반 아래면 깨운다.
    fn wake_readers(keep: &Keep, queued: &AtomicUsize) {
        if backpressure(&keep.args) && keep.room_waiters.load(Ordering::SeqCst) > 0 && queued.load(Ordering::SeqCst) < BOUND_QUEUE_BYTES / 2 {
            let _st = lock_st(keep);
            keep.room.notify_all();
        }
    }

    fn read_loop(keep: Arc<Keep>, i: usize, mut r: Box<dyn Read + Send>) {
        let mut buf = [0u8; READ_BUF];
        loop {
            let room = if backpressure(&keep.args) { wait_for_room(&keep, i) } else { READ_BUF };
            let n = match r.read(&mut buf[..room]) {
                Ok(0) | Err(_) => break,
                Ok(n) => n,
            };
            // 꼬리 갱신과 조종자 송신을 같은 임계 구역에서 한다 — 붙기(attach)의 꼬리 재생과 겹치거나 빠지지 않는다.
            // 송신은 try_send 뿐이라 여기서 막히지 않는다(조종자가 안 읽어도 자식 출력은 계속 꼬리에 쌓인다).
            let mut st = lock_st(&keep);
            let o = &mut st.out[i];
            let offset = o.total;
            o.total += n as u64;
            o.tail.extend(&buf[..n]);
            let cap = keep.args.tail_bytes;
            if o.tail.len() > cap {
                let drop_n = o.tail.len() - cap;
                o.tail.drain(..drop_n);
            }
            send_output(&keep, &mut st, i, offset, &buf[..n]);
        }
        let mut st = lock_st(&keep);
        st.out[i].reader_done = true;
        publish_exit(&keep, &mut st, i, false);
    }

    /// 회수된 종료를 조종자에게 알린다 — 마지막 출력 뒤에(읽기가 끝났거나 DRAIN 이 지났을 때) 한 번만.
    /// EXITED·종료 기록에 `final_offset`(그때까지의 누적 출력)과 `output_open`(PTY 를 쥔 다른 프로세스가 있어
    /// 출력이 더 올 수 있음)을 적는다(codex 1R #11).
    fn publish_exit(keep: &Keep, st: &mut State, i: usize, force: bool) {
        let o = &st.out[i];
        if o.exit.is_some() {
            return;
        }
        let Some(mut e) = o.exit_status.clone() else { return };
        if !(o.reader_done || force) {
            return;
        }
        e["final_offset"] = json!(o.total);
        e["output_open"] = json!(!o.reader_done);
        st.out[i].exit = Some(e.clone());
        keep.persist_exit_record(st);
        // 이 좌석이 밀려 있으면 EXITED 는 따라잡기가 끝난 뒤(catch_up)에 — 마지막 출력보다 먼저 가지 않게.
        let behind = st.controller.as_ref().map(|c| c.behind[i].is_some()).unwrap_or(false);
        if !behind {
            send_ctl(keep, st, proto::json_frame(proto::EXITED, keep.seats[i].id, &e));
            if let Some(c) = st.controller.as_mut() {
                c.exited_sent[i] = true;
            }
        }
    }

    fn wait_loop(keep: Arc<Keep>, i: usize, mut child: Box<dyn Child + Send + Sync>) {
        let pid = keep.seats[i].child_pid;
        // ① 끝남만 본다(회수 안 함). ② 신호 금지 표시를 잠금 안에서 세운다. ③ 그 뒤에야 회수한다.
        // SIGNAL·RELEASE 는 같은 잠금 안에서 이 표시를 보고 killpg 하므로, 회수된(재사용될 수 있는) pid 를 치지 않는다(codex 1R #3).
        let status = reap_marked(&keep, i, pid, child.as_mut());
        let exit = match status {
            Ok(s) => json!({"code": s.exit_code(), "signal": s.signal(), "at": registry::now_epoch()}),
            Err(e) => json!({"error": e.to_string(), "at": registry::now_epoch()}),
        };
        {
            let mut st = lock_st(&keep);
            st.out[i].exit_status = Some(exit.clone());
            publish_exit(&keep, &mut st, i, false);
        }
        let _ = keep.log(json!({"event": "child_exit", "seat": i, "exit": exit}));
        std::thread::sleep(DRAIN);
        let mut st = lock_st(&keep);
        publish_exit(&keep, &mut st, i, true);
    }

    /// SIGNAL 집행 — **상태 잠금을 쥔 채로** 부른다(회수 표시와 신호 사이에 회수가 끼지 않게). `target`:
    /// 없음·`"group"` = killpg(T2 동작) · `"leader"` = 리더 pid 에만 kill(T3 D7 결정 B — 직접 PTY `Child::kill` 과 같은 대상) ·
    /// 그 밖 = 거절(신호 0). 순서 = 값 검사 → 회수 표시 → pid 검사 → 신호.
    fn signal_seat(keep: &Keep, st: &State, i: usize, sig: i32, target: Option<&str>) -> &'static str {
        let leader = match target {
            None | Some("group") => false,
            Some("leader") => true,
            Some(_) => return "bad_target",
        };
        if st.out[i].reaped {
            return "reaped";
        }
        let pid = keep.seats[i].child_pid;
        if pid <= 0 {
            return "no_pid";
        }
        if leader {
            unsafe { libc::kill(pid, sig) };
        } else {
            unsafe { libc::killpg(pid, sig) };
        }
        "sent"
    }

    /// 회수 순서(codex 1R #3 · M09): 끝남만 보고(WNOWAIT) → 잠금 안에서 신호 금지 표시 → 그 뒤에 회수. 시험(`reap_marks_before_reaping`)이
    /// 회수 순간에 표시가 이미 서 있는지를 가짜 자식으로 직접 본다 — 부하와 무관한 결정적 시험(T3 · T2 인계 2).
    fn reap_marked(keep: &Keep, i: usize, pid: i32, child: &mut (dyn Child + Send + Sync)) -> std::io::Result<portable_pty::ExitStatus> {
        if !wait_exit_nowait(pid) {
            warn!("cys-seatkeep: waitid({pid}) 실패: {} — 회수 경로로 넘어간다", std::io::Error::last_os_error());
        }
        lock_st(&keep).out[i].reaped = true;
        let status = child.wait();
        status
    }

    /// 좌석별 PTY 입력 쓰기 — 자식이 안 읽으면 여기만 막히고 serve 는 막히지 않는다(codex 1R #2).
    /// 수신 확인(INPUT_ACK) = PTY 에 다 썼다. 못 쓰면 확인 없음(조종자는 「모름」 · 자동 재전송 금지).
    fn input_loop(keep: Arc<Keep>, i: usize, rx: Receiver<InputJob>, mut w: Box<dyn Write + Send>) {
        for job in rx {
            let reaped = lock_st(&keep).out[i].reaped;
            let ok = !reaped && w.write_all(&job.bytes).and_then(|_| w.flush()).is_ok();
            let mut st = lock_st(&keep);
            st.out[i].input_pending = st.out[i].input_pending.saturating_sub(job.bytes.len());
            if !ok {
                if job.id != 0 {
                    forget_input(&mut st.input_ids, job.id);
                }
                continue;
            }
            send_gen(&keep, &mut st, job.gen, proto::frame(proto::INPUT_ACK, keep.seats[i].id, &proto::input_ack_payload(job.id, false)));
        }
    }

    fn remember_input(ids: &mut (VecDeque<u64>, HashSet<u64>), id: u64) {
        if ids.1.insert(id) {
            ids.0.push_back(id);
            if ids.0.len() > INPUT_IDS_KEPT {
                if let Some(old) = ids.0.pop_front() {
                    ids.1.remove(&old);
                }
            }
        }
    }

    fn forget_input(ids: &mut (VecDeque<u64>, HashSet<u64>), id: u64) {
        if ids.1.remove(&id) {
            ids.0.retain(|x| *x != id);
        }
    }

    /// 거절 + 기록. 기록에 현재 세대·현재 조종자·직전 조종자와 끊긴 시각을 함께 남긴다(브리프 §1-4 · codex 1R #14).
    /// 상태 잠금을 쥔 채 부르지 않는다.
    fn reject(keep: &Keep, mut s: UnixStream, reason: &str, peer: Option<&Peer>) {
        let (gen, cur, prev) = {
            let st = lock_st(keep);
            (
                st.gen,
                st.controller.as_ref().map(|c| json!({"gen": c.gen, "peer": peer_json(&c.peer)})),
                st.last_peer.as_ref().map(|(p, at)| json!({"peer": peer_json(p), "disconnected_at": at})),
            )
        };
        let _ = keep.log(json!({"event": "reject", "reason": reason, "peer": peer.map(peer_json),
                                "gen": gen, "controller": cur, "prev": prev}));
        let _ = proto::write_all(&mut s, &proto::json_frame(proto::REJECT, ALL_SEATS, &json!({"reason": reason})));
        let _ = s.shutdown(Shutdown::Both);
    }

    /// 핸드셰이크 끝맺음 상태(handshake-timeout): 진행 중 · 끝남(수락 또는 거절 기록) · 감시가 시간 초과로 끝냄.
    const HS_RUNNING: u8 = 0;
    const HS_FINISHED: u8 = 1;
    const HS_TIMED_OUT: u8 = 2;

    /// 핸드셰이크 도중의 거절 — 끝맺음을 잡았을 때만 기록·REJECT(감시가 시간 초과로 이미 끝냈으면 두 번째 줄을 남기지 않는다).
    fn reject_once(keep: &Keep, s: UnixStream, done: &AtomicU8, reason: &str, peer: Option<&Peer>) {
        if done.compare_exchange(HS_RUNNING, HS_FINISHED, Ordering::SeqCst, Ordering::SeqCst).is_ok() {
            reject(keep, s, reason, peer);
        }
    }

    /// 기한 감시의 거절(codex 3R #3) — 상태·기록 잠금과 무관하게 **먼저** 짧은 REJECT 를 유한 쓰기(200ms)로 보내고 소켓을 닫는다
    /// (수락 준비가 상태 잠금을 쥔 채 늦어도 조종자는 기한 안에 답을 받는다). 기록은 그 뒤 — 상태는 `try_lock` 으로만 본다(못 보면 칸 null).
    fn reject_timeout(keep: &Keep, mut s: UnixStream) {
        let _ = s.set_write_timeout(Some(Duration::from_millis(200)));
        let _ = proto::write_all(&mut s, &proto::json_frame(proto::REJECT, ALL_SEATS, &json!({"reason": "handshake_timeout"})));
        let _ = s.shutdown(Shutdown::Both);
        let (gen, cur) = match keep.st.try_lock() {
            Ok(st) => (json!(st.gen), st.controller.as_ref().map(|c| json!({"gen": c.gen, "peer": peer_json(&c.peer)}))),
            Err(_) => (Value::Null, None),
        };
        let _ = keep.log(json!({"event": "reject", "reason": "handshake_timeout", "peer": Value::Null, "gen": gen, "controller": cur}));
    }

    fn accept_loop(keep: Arc<Keep>, listener: UnixListener) {
        for conn in listener.incoming() {
            let Ok(s) = conn else { continue };
            let k = Arc::clone(&keep);
            // 확인은 접속마다 별 스레드 — 느린 접속자가 다른 접속을 막지 않는다. 조종자 자리는 아래 임계 구역이 하나로 지킨다.
            std::thread::spawn(move || handshake(k, s));
        }
    }

    /// 진행 중 핸드셰이크 수(상한 MAX_PENDING_HANDSHAKES) — 끝나면(어느 길로든) 하나 줄인다.
    struct Pending<'a>(&'a AtomicUsize);
    impl Drop for Pending<'_> {
        fn drop(&mut self) {
            self.0.fetch_sub(1, Ordering::SeqCst);
        }
    }

    fn handshake(keep: Arc<Keep>, mut s: UnixStream) {
        // 동시 상한 — 느린 접속이 스레드·fd 를 쌓아 인증을 막지 못하게(codex 1R #13).
        if keep.pending_hs.fetch_add(1, Ordering::SeqCst) >= MAX_PENDING_HANDSHAKES {
            keep.pending_hs.fetch_sub(1, Ordering::SeqCst);
            return reject(&keep, s, "busy", None);
        }
        let pending = Pending(&keep.pending_hs);
        // 절대 기한 — 읽기마다의 기한이 아니라 핸드셰이크 전체. 기한이 지나면 소켓을 닫아 아래 읽기를 끝낸다.
        // 끝맺음은 하나만(handshake-timeout · master#5b9e1d26): 감시가 먼저 「시간 초과」를 잡으면 `reject handshake_timeout` 1줄
        // (+REJECT 프레임)을 남기고 닫는다 — 그 뒤 핸드셰이크는 수락(accept)도 거절 기록도 하지 않는다. 수락 쪽이 먼저 「끝남」을
        // 잡으면 감시는 아무것도 안 한다(전: 감시가 기록 없이 닫고, 핸드셰이크는 닫힌 소켓을 늦게 수락 → 조종자 종속이면 곧 controller_lost).
        let done = Arc::new(AtomicU8::new(HS_RUNNING));
        if let Ok(s2) = s.try_clone() {
            let (d, k) = (Arc::clone(&done), Arc::clone(&keep));
            std::thread::spawn(move || {
                std::thread::sleep(HELLO_TIMEOUT);
                if d.compare_exchange(HS_RUNNING, HS_TIMED_OUT, Ordering::SeqCst, Ordering::SeqCst).is_ok() {
                    reject_timeout(&k, s2);
                }
            });
        }
        let peer = match peer::authorize(s.as_raw_fd(), &keep.policy) {
            Ok(p) => p,
            Err((reason, p)) => return reject_once(&keep, s, &done, reason, p.as_ref()),
        };
        // 살아 있는 조종자가 있으면 거절(허더의 「마지막 접속자 탈취」 반대). HELLO 를 읽기 전에도 한 번 본다.
        if lock_st(&keep).controller.is_some() {
            return reject_once(&keep, s, &done, "controller_alive", Some(&peer));
        }
        let _ = s.set_read_timeout(Some(HELLO_TIMEOUT));
        let hello: Value = match proto::read_frame_max(&mut s, HELLO_MAX) {
            Ok(Some((proto::HELLO, _, p))) => serde_json::from_slice(&p).unwrap_or(Value::Null),
            _ => return reject_once(&keep, s, &done, "no_hello", Some(&peer)),
        };
        if hello["core"].as_u64() != Some(proto::CORE_VERSION as u64) {
            return reject_once(&keep, s, &done, "core_mismatch", Some(&peer));
        }
        // 시험 전용 지연(handshake-timeout 재현 — HELLO 를 읽은 뒤 두 번째 신원 확인이 느린 경우 · 실측된 느린 자리).
        // 디버그 빌드에서만 읽는다.
        #[cfg(debug_assertions)]
        if let Some(ms) = std::env::var("CYS_SEATKEEP_TEST_AUTH_DELAY_MS").ok().and_then(|v| v.parse::<u64>().ok()) {
            std::thread::sleep(Duration::from_millis(ms));
        }
        // 확인~HELLO 사이에 잠금을 놓았거나 신원이 바뀌었으면 받지 않는다 — 확인과 수락 사이 틈을 좁힌다(codex 1R #10).
        let peer = match peer::authorize(s.as_raw_fd(), &keep.policy) {
            // (pid · pidversion · 출생 시각) 셋 다 같아야 — 토큰은 「지금 그 pid 의 프로세스」라서(peer.rs ⚠) 처음 확인한
            // 그 프로세스가 아직 그 소켓의 마지막 사용자인지를 이 짝으로 본다. 출생 시각을 못 읽으면(None) 같다고 보지 않는다.
            Ok(p2) if p2.pid == peer.pid && p2.pidversion == peer.pidversion && p2.start_us.is_some() && p2.start_us == peer.start_us => p2,
            Ok(p2) => return reject_once(&keep, s, &done, "peer_changed", Some(&p2)),
            Err((reason, p)) => return reject_once(&keep, s, &done, reason, p.as_ref()),
        };
        let _ = s.set_read_timeout(None);
        let (Ok(write_half), Ok(shut)) = (s.try_clone(), s.try_clone()) else {
            return reject_once(&keep, s, &done, "socket_clone_failed", Some(&peer));
        };
        // 안 읽는 조종자: 소켓 쓰기가 이 기한을 넘으면 쓰기 스레드가 끝나며 연결을 닫는다(codex 1R #1).
        // 조종자 종속 모드(⑶)는 기한이 없다 — 연결이 살아 있는 한 기다린다(멈춘 조종자 = 자식도 역압으로 멈춤 · write_stalled 없음).
        if !backpressure(&keep.args) {
            let _ = write_half.set_write_timeout(Some(CTL_WRITE_TIMEOUT));
        }
        let rx;
        let gen;
        let queued = Arc::new(AtomicUsize::new(0));
        let ctl_queued = Arc::new(AtomicUsize::new(0));
        let behind_flag = Arc::new(AtomicBool::new(false));
        {
            let mut st = lock_st(&keep);
            // 감시가 이미 시간 초과로 끝냈으면(준비 전) 조용히 물러난다 — 늦은 accept 줄을 쓰지 않는다(그쪽이 reject 를 기록했다).
            if done.load(Ordering::SeqCst) != HS_RUNNING {
                return;
            }
            if st.controller.is_some() {
                drop(st);
                return reject_once(&keep, s, &done, "controller_alive", Some(&peer));
            }
            gen = st.gen + 1;
            // 교체 기록이 먼저다 — 기록 없이 조종자를 받지 않는다(사후 적발 장치가 무력해지지 않게).
            let prev = st.last_peer.as_ref().map(|(p, at)| json!({"peer": peer_json(p), "disconnected_at": at}));
            let reason = if prev.is_none() { "first" } else { "takeover_after_disconnect" };
            let resume = &hello["resume"];
            let lost: Vec<Value> = st
                .out
                .iter()
                .enumerate()
                .map(|(i, o)| {
                    let from = resume[i.to_string()].as_u64().unwrap_or(0);
                    json!({"seat": i, "resume_from": from, "tail_start": o.tail_start(), "total": o.total,
                           "lost_bytes": o.tail_start().saturating_sub(from)})
                })
                .collect();
            // WELCOME + 좌석별 꼬리 재생(REPLAY_CHUNK 로 나눔) + 알린 종료 — 전부 먼저 모아 그 수만큼 칸을 더 잡는다
            // (소비 스레드 시작 전에 고정 칸에 넣다가 조용히 버리던 결함 · codex 1R #8 #9). 재생 OUTPUT 은 크기와 무관하게 전부
            // 넣는다(꼬리 상한 64MiB 안 · 그동안 새 출력은 밀림 경로로 간다) · 제어 프레임은 제어 상한을 탄다 — 넘으면
            // 교체 기록 전에 접속을 거절한다(codex 3R #1 · accept 줄 없이 끝나 A16 셈이 맞는다).
            let seats: Vec<Value> = keep
                .seats
                .iter()
                .zip(st.out.iter())
                // `disc_total`(T4 · 입양 모드만 값 · 그 밖 null) = 직전 조종자가 끊긴 때의 누적 출력 — 새 조종자는 그 앞 재생을 「옛 조종자가
                // 이미 본 화면」(화면만 다시 그림)으로, 그 뒤를 「아무도 못 본 새 출력」(전사·응답까지)으로 나눈다.
                .map(|(seat, o)| json!({"seat": seat.id, "child_pid": seat.child_pid, "total": o.total,
                                         "tail_start": o.tail_start(), "exit": o.exit, "disc_total": o.disc_total}))
                .collect();
            let welcome = json!({"core": proto::CORE_VERSION, "gen": gen, "pid": std::process::id(),
                                 "start_us": keep.start_us, "boot_id": keep.boot_id, "seats": seats});
            let mut frames = vec![proto::json_frame(proto::WELCOME, ALL_SEATS, &welcome)];
            let mut exited_sent = vec![false; st.out.len()];
            for (i, o) in st.out.iter().enumerate() {
                let from = resume[i.to_string()].as_u64().unwrap_or(0).max(o.tail_start()).min(o.total);
                let skip = (from - o.tail_start()) as usize;
                let bytes: Vec<u8> = o.tail.iter().skip(skip).copied().collect();
                for (k, chunk) in bytes.chunks(REPLAY_CHUNK).enumerate() {
                    let off = from + (k * REPLAY_CHUNK) as u64;
                    frames.push(proto::frame(proto::OUTPUT, keep.seats[i].id, &proto::output_payload(off, chunk)));
                }
                if let Some(e) = &o.exit {
                    frames.push(proto::json_frame(proto::EXITED, keep.seats[i].id, e));
                    exited_sent[i] = true;
                }
            }
            // 시험 전용 지연(codex 2R #3 재현 — 수락 준비가 느림 · 상태 잠금을 쥔 채). 디버그 빌드에서만 읽는다.
            #[cfg(debug_assertions)]
            if let Some(ms) = std::env::var("CYS_SEATKEEP_TEST_ACCEPT_DELAY_MS").ok().and_then(|v| v.parse::<u64>().ok()) {
                std::thread::sleep(Duration::from_millis(ms));
            }
            let Some((tx, r)) = queue_initial(frames, &queued, &ctl_queued) else {
                drop(st);
                warn!("cys-seatkeep: 첫 재생의 제어 프레임이 상한({CTL_QUEUE_BYTES}바이트)을 넘음 — 접속 거절");
                return reject_once(&keep, s, &done, "control_queue_full", Some(&peer));
            };
            if let Err(e) = keep.log(json!({"event": "accept", "gen": gen, "reason": reason, "peer": peer_json(&peer),
                                             "prev": prev, "replay": lost})) {
                // accept 줄이 온전히 남은 경우(fsync 만 실패)에만 「받지 않았다」 줄을 덧붙인다 — 짧은 쓰기를 되돌렸거나 쓰기 전에
                // 실패했으면 남은 accept 가 없으니 덧붙이면 A16 셈(accept − accept_aborted)이 실제보다 작아진다(codex 2R #3).
                // 판정값은 이번 호출의 오류에 실려 온다(codex 3R #2 — 앞선 실패의 값이 남지 않는다).
                if e.kept_line {
                    let _ = keep.log(json!({"event": "accept_aborted", "gen": gen, "error": e.to_string()}));
                }
                drop(st);
                warn!("cys-seatkeep: 교체 기록 실패 — 접속 거절: {e}");
                return reject_once(&keep, s, &done, "ledger_write_failed", Some(&peer));
            }
            // 수락 쪽 끝맺음(codex 2R #3) = 조종자를 실제로 거는 이 자리 — 준비(재생 프레임·accept 기록)는 그 앞에서 끝낸다. 감시가 그사이
            // 시간 초과로 이겼으면 준비를 버리고 `accept_aborted handshake_timeout` 을 덧붙여 물러난다(A16 셈: accept − accept_aborted).
            if done.compare_exchange(HS_RUNNING, HS_FINISHED, Ordering::SeqCst, Ordering::SeqCst).is_err() {
                let _ = keep.log(json!({"event": "accept_aborted", "gen": gen, "reason": "handshake_timeout"}));
                return;
            }
            st.gen = gen;
            st.no_controller_since = None;
            for o in st.out.iter_mut() {
                o.disc_total = None;
            }
            let n = st.out.len();
            st.controller = Some(Controller {
                gen,
                peer: peer.clone(),
                tx,
                queued: Arc::clone(&queued),
                ctl_queued: Arc::clone(&ctl_queued),
                shut,
                behind: vec![None; n],
                behind_flag: Arc::clone(&behind_flag),
                exited_sent,
                evicted: false,
            });
            // 첫 조종자를 기다리며 꼬리가 차서 멈춘 읽기 스레드(조종자 종속 모드)는 따로 깨우지 않는다 — 큐의 첫 프레임(WELCOME)을
            // 쓰기 스레드가 쓴 뒤 `wake_readers` 가 깨운다(그때 큐 = 재생분뿐이고, 반 아래로 내려가면 깨운다).
            rx = r;
        }
        drop(pending);
        {
            let mut w = write_half;
            let k = Arc::clone(&keep);
            std::thread::spawn(move || {
                for f in rx {
                    if let Err(e) = proto::write_all(&mut w, &f) {
                        // 쓰기 기한(CTL_WRITE_TIMEOUT) 동안 진척 0 = 멈춘 조종자 → 내보냄으로 기록하고 닫는다.
                        // 그 밖의 오류(EPIPE 등) = 조종자가 이미 끊었다 → 기록 없이 닫는다(끊김은 serve 쪽이 기록).
                        if matches!(e.kind(), std::io::ErrorKind::WouldBlock | std::io::ErrorKind::TimedOut) {
                            let mut st = lock_st(&k);
                            if let Some(c) = st.controller.as_mut().filter(|c| c.gen == gen) {
                                if !c.evicted {
                                    c.evicted = true;
                                    let peer = peer_json(&c.peer);
                                    let _ = k.log(json!({"event": "evict", "gen": gen, "reason": "write_stalled", "error": e.to_string(), "peer": peer}));
                                }
                            }
                        }
                        break;
                    }
                    // 큐가 반 아래로 비면 밀린 좌석을 따라잡는다(조종자 종속 모드 = 역압으로 멈춘 읽기 스레드를 깨운다).
                    let catch = written(&queued, &ctl_queued, &behind_flag, &f);
                    wake_readers(&k, &queued);
                    if catch {
                        let mut st = lock_st(&k);
                        if st.controller.as_ref().map(|c| c.gen) == Some(gen) {
                            catch_up(&k, &mut st);
                        }
                    }
                }
                let _ = w.shutdown(Shutdown::Both);
            });
        }
        serve(&keep, s, gen);
        let mut st = lock_st(&keep);
        if st.controller.as_ref().map(|c| c.gen) == Some(gen) {
            let c = st.controller.take().unwrap();
            let now = registry::now_epoch();
            st.last_peer = Some((c.peer.clone(), now));
            st.no_controller_since = Some(Instant::now());
            // 입양 모드: 끊긴 때의 누적 출력을 좌석마다 적어 둔다(조종자 없는 동안 읽기 상한 = 이 뒤로 꼬리 크기까지 · `wait_for_room`).
            for o in st.out.iter_mut() {
                o.disc_total = Some(o.processed.min(o.total));
            }
            let _ = keep.log(json!({"event": "disconnect", "gen": gen, "peer": peer_json(&c.peer), "evicted": c.evicted}));
            if keep.args.controller_bound {
                drop(st);
                end_for_controller_loss(&keep, "controller_lost");
            }
        }
    }

    /// `--controller-bound` ⑴: 기록 1줄 · 등록부 `ended` · 소켓 삭제 뒤 프로세스를 끝낸다 → 커널이 PTY 마스터의 모든 사본을 닫아
    /// 좌석(세션 우두머리)에 SIGHUP — cysd 가 마스터를 쥐던 때 cysd 가 죽은 것과 같은 경로(DESIGN §1-2). 자식에게 신호를 보내지 않는다.
    fn end_for_controller_loss(keep: &Keep, why: &str) -> ! {
        if !record_controller_loss(keep, why) {
            lose_exit()
        }
        std::process::exit(0)
    }

    /// 종료 소유자가 된다(codex 1R #4) — 처음 부른 1명만 참. 진 쪽은 기록하지 않고 `lose_exit` 로 이긴 쪽의 끝을 기다린다.
    fn claim_exit(keep: &Keep) -> bool {
        keep.exit_owner.compare_exchange(false, true, Ordering::SeqCst, Ordering::SeqCst).is_ok()
    }

    /// 진 쪽 — 이긴 쪽이 프로세스를 끝낼 때까지 이 스레드를 세운다(기록·등록부·소켓 무접촉).
    fn lose_exit() -> ! {
        loop {
            std::thread::park();
        }
    }

    /// 조종자 상실 끝의 기록 몫 — 이겼으면 기록 1줄 · 소켓 삭제 · 등록부 `ended_controller_lost` 를 하고 참, 졌으면 아무것도 안 하고 거짓.
    fn record_controller_loss(keep: &Keep, why: &str) -> bool {
        if !claim_exit(keep) {
            return false;
        }
        let _ = keep.log(json!({"event": "seatkeep_exit", "reason": why}));
        let _ = std::fs::remove_file(&keep.paths.sock);
        let _ = registry::write_atomic(&keep.paths.entry, &keep.entry("ended_controller_lost"));
        true
    }

    /// 조종자 종속 모드에서 기동 때의 부모가 사라졌는가(부모 pid 가 바뀜). 인자 없는 모드(T2)는 늘 거짓.
    /// 기동 때 이미 부모가 1(launchd)이면 = 띄운 cysd 가 seatkeep 이 첫 줄을 돌기 전에 죽었다(조종자 종속 모드는 cysd 만 띄운다) → 잃음.
    fn parent_lost(keep: &Keep) -> bool {
        keep.args.controller_bound && (keep.parent_pid <= 1 || unsafe { libc::getppid() } != keep.parent_pid)
    }

    fn seat_index(keep: &Keep, seat: u32) -> Option<usize> {
        keep.seats.iter().position(|s| s.id == seat)
    }

    fn serve(keep: &Keep, mut s: UnixStream, gen: u64) {
        loop {
            let (kind, seat, payload) = match proto::read_frame(&mut s) {
                Ok(Some(f)) => f,
                _ => return,
            };
            // 세대 울타리: 이 연결이 더 이상 조종자가 아니면 어떤 명령도 집행하지 않는다.
            if lock_st(keep).controller.as_ref().map(|c| c.gen) != Some(gen) {
                return;
            }
            match kind {
                proto::INPUT => {
                    let Some(i) = seat_index(keep, seat) else { continue };
                    let Some((id, bytes)) = proto::split_input(&payload) else { continue };
                    let mut st = lock_st(keep);
                    if id != 0 && st.input_ids.1.contains(&id) {
                        // 이미 받은 id(썼거나 쓰는 중) — 다시 쓰지 않고 dup=1 로 답한다.
                        send_gen(keep, &mut st, gen, proto::frame(proto::INPUT_ACK, seat, &proto::input_ack_payload(id, true)));
                        continue;
                    }
                    if st.out[i].reaped || st.out[i].input_pending + bytes.len() > INPUT_QUEUE_BYTES {
                        continue; // 받지 않음 = 확인 없음(조종자는 「모름」 · 자동 재전송 금지)
                    }
                    let n = bytes.len();
                    if keep.seats[i].input.try_send(InputJob { id, gen, bytes: bytes.to_vec() }).is_ok() {
                        st.out[i].input_pending += n;
                        if id != 0 {
                            remember_input(&mut st.input_ids, id);
                        }
                    }
                }
                proto::RESIZE => {
                    let Some(i) = seat_index(keep, seat) else { continue };
                    let v: Value = serde_json::from_slice(&payload).unwrap_or(Value::Null);
                    let (Some(cols), Some(rows)) = (v["cols"].as_u64(), v["rows"].as_u64()) else { continue };
                    let _ = keep.seats[i].master.lock().unwrap_or_else(|e| e.into_inner()).resize(PtySize {
                        rows: rows.clamp(1, 1000) as u16,
                        cols: cols.clamp(1, 1000) as u16,
                        pixel_width: 0,
                        pixel_height: 0,
                    });
                }
                proto::SIGNAL => {
                    let v: Value = serde_json::from_slice(&payload).unwrap_or(Value::Null);
                    let Some(sig) = v["sig"].as_i64() else { continue };
                    if !matches!(sig as i32, libc::SIGINT | libc::SIGTERM | libc::SIGHUP | libc::SIGKILL | libc::SIGQUIT | libc::SIGWINCH | libc::SIGCONT | libc::SIGSTOP) {
                        continue;
                    }
                    // T3 확장 칸 `target`(proto.rs 머리) — 칸이 있으면 결과를 답한다 · 문자열이 아니면 모르는 값과 같이 거절.
                    let target: Option<Option<&str>> = v.get("target").map(|t| t.as_str().or(Some("\u{0}")));
                    // 회수 표시를 보는 것과 신호를 같은 잠금 안에서 — 회수된 자식(pid 재사용 대상)에는 보내지 않는다.
                    let mut st = lock_st(keep);
                    for i in targets(keep, seat) {
                        let result = signal_seat(keep, &st, i, sig as i32, target.flatten());
                        if target.is_some() {
                            let body = json!({"sig": sig, "target": v["target"], "result": result});
                            send_gen(keep, &mut st, gen, proto::json_frame(proto::SIGNAL_RESULT, keep.seats[i].id, &body));
                        }
                    }
                }
                proto::RELEASE => {
                    let _ = keep.log(json!({"event": "release", "gen": gen, "seat": seat}));
                    let st = lock_st(keep);
                    for i in targets(keep, seat) {
                        if !st.out[i].reaped {
                            unsafe { libc::killpg(keep.seats[i].child_pid, libc::SIGHUP) };
                        }
                    }
                }
                proto::FOREGROUND => {
                    let Some(i) = seat_index(keep, seat) else { continue };
                    let pg = keep.seats[i].master.lock().unwrap_or_else(|e| e.into_inner()).process_group_leader();
                    let mut st = lock_st(keep);
                    send_gen(keep, &mut st, gen, proto::json_frame(proto::FOREGROUND_IS, seat, &json!({"pgid": pg})));
                }
                proto::PROCESSED if payload.len() >= 8 => {
                    let off = u64::from_le_bytes(payload[..8].try_into().unwrap_or([0; 8]));
                    let mut st = lock_st(keep);
                    for i in targets(keep, seat) {
                        let o = &mut st.out[i];
                        o.processed = o.processed.max(off.min(o.total));
                    }
                }
                proto::EXIT_ACK => {
                    let mut st = lock_st(keep);
                    for i in targets(keep, seat) {
                        if st.out[i].exit.is_some() {
                            st.out[i].exit_acked = true;
                        }
                    }
                    keep.persist_exit_record(&mut st);
                }
                _ => {}
            }
        }
    }

    fn targets(keep: &Keep, seat: u32) -> Vec<usize> {
        if seat == ALL_SEATS {
            (0..keep.seats.len()).collect()
        } else {
            seat_index(keep, seat).into_iter().collect()
        }
    }

    /// 모든 자식이 끝나고(알린 종료 기준) ⓐ 조종자가 전부 받았다고 답했거나 ⓑ 조종자 없이 유예가 지나고 종료 기록이
    /// 디스크에 있으면 끝낸다. ⓑ 의 경우 `<id>.exit` 를 남긴다(새 조종자가 소비). 기록을 못 쓰면 끝내지 않고 다시 쓴다.
    fn supervise(keep: Arc<Keep>) -> i32 {
        loop {
            std::thread::sleep(Duration::from_millis(100));
            // `--controller-bound`(D2): 부모(cysd)가 죽으면 부모 pid 가 바뀐다(launchd 등으로 입양) — 첫 조종자가 붙기 전이라도 100ms 안에
            // 끝낸다. 직접 PTY 는 cysd 가 죽는 순간 마스터가 닫혀 좌석이 HUP 이므로 같은 결과(전에는 FIRST_CONTROLLER_MAX 15초까지 무감독).
            if parent_lost(&keep) {
                end_for_controller_loss(&keep, "parent_lost");
            }
            let mut st = lock_st(&keep);
            if !st.exit_record_ok && st.out.iter().any(|o| o.exit.is_some() && !o.exit_acked) {
                keep.persist_exit_record(&mut st);
            }
            let all_exited = st.out.iter().all(|o| o.exit.is_some());
            let all_acked = st.out.iter().all(|o| o.exit_acked);
            let orphan_long = st.controller.is_none() && st.no_controller_since.map(|t| t.elapsed() >= EXIT_GRACE).unwrap_or(false);
            // 종료 기록을 EXIT_PERSIST_MAX 넘게 못 남기면(상태 폴더가 사라짐 등) stderr 에 기록을 남기고 rc 6 으로 끝낸다 —
            // 소켓도 사라졌을 수 있어 어떤 조종자도 확인해 줄 수 없는 영구 고아가 되지 않게(독립 검증 D9).
            // `--controller-bound`: 기동 뒤 아무 조종자도 붙지 않은 채 상한이 지나면 끝낸다(cysd 가 기동~HELLO 사이에 죽은 경우).
            if backpressure(&keep.args) && st.gen == 0 && st.controller.is_none() && keep.started.elapsed() >= FIRST_CONTROLLER_MAX {
                drop(st);
                end_for_controller_loss(&keep, "no_first_controller");
            }
            let persist_given_up = !st.exit_record_ok && st.exit_record_fail_since.map(|t| t.elapsed() >= EXIT_PERSIST_MAX).unwrap_or(false);
            if all_exited && !all_acked && orphan_long && persist_given_up {
                let v: Vec<Value> = st.out.iter().enumerate().map(|(i, o)| json!({"seat": i, "exit": o.exit, "acked": o.exit_acked})).collect();
                drop(st);
                if !claim_exit(&keep) {
                    lose_exit()
                }
                warn!("cys-seatkeep: 종료 기록을 {}초 동안 못 남김 — 여기 남기고 끝낸다: {}", EXIT_PERSIST_MAX.as_secs(), json!({"id": keep.args.id, "seats": v}));
                let _ = keep.log(json!({"event": "seatkeep_exit", "exit_record_kept": false, "exit_record_to_stderr": true}));
                let _ = std::fs::remove_file(&keep.paths.sock);
                return 6;
            }
            if all_exited && (all_acked || (orphan_long && st.exit_record_ok)) {
                // PTY 를 아직 쥔 프로세스가 있던 좌석 — 여기서 끝내면 그 뒤 출력은 받지 못한다(기록으로 남김).
                let open: Vec<usize> = st.out.iter().enumerate().filter(|(_, o)| !o.reader_done).map(|(i, _)| i).collect();
                drop(st);
                if !claim_exit(&keep) {
                    lose_exit()
                }
                let _ = std::fs::remove_file(&keep.paths.sock);
                let _ = registry::write_atomic(&keep.paths.entry, &keep.entry("exited"));
                let _ = keep.log(json!({"event": "seatkeep_exit", "exit_record_kept": !all_acked, "output_open_seats": open}));
                return 0;
            }
        }
    }

    /// codex 3R 「단위 회귀 시험 없음」 4곳 — 깨우기 경합(가능한 범위) · 제어 큐 포화 · 실패 시각 초기화.
    /// (fsync/길이 읽기 실패 구분은 registry.rs 의 가짜 기록 파일 시험.)
    #[cfg(test)]
    mod tests {
        use super::*;

        fn tmpdir(tag: &str) -> PathBuf {
            let d = std::env::temp_dir().join(format!("sk-main-{tag}-{}", std::process::id()));
            let _ = std::fs::remove_dir_all(&d);
            std::fs::create_dir_all(&d).unwrap();
            d
        }

        /// 자식 없는 좌석 n 개(실제 PTY · child_pid 0 — 신호를 보내는 길은 타지 않는다).
        fn test_keep(tag: &str, n: u32) -> (Keep, PathBuf) {
            let d = tmpdir(tag);
            let args = Args {
                dir: d.clone(),
                id: "t".into(),
                controller_exe: PathBuf::from("/nonexistent"),
                lock: d.join("ctl.lock"),
                requirement: None,
                seats: n,
                tail_bytes: MAX_TAIL,
                rows: 10,
                cols: 10,
                controller_bound: false,
                adoptable: false,
                cmd: vec!["/bin/true".into()],
            };
            let paths = Paths::new(&d, "t");
            paths.ensure_dir().unwrap();
            let id_lock = registry::lock_id(&paths.idlock).unwrap();
            let ledger = Ledger::open(&paths.log).unwrap();
            let seats = (0..n)
                .map(|i| {
                    let pair = native_pty_system().openpty(PtySize { rows: 10, cols: 10, pixel_width: 0, pixel_height: 0 }).unwrap();
                    let (itx, _irx) = sync_channel::<InputJob>(1);
                    Seat { id: i, child_pid: 0, master: Mutex::new(pair.master), input: itx }
                })
                .collect();
            let st = State {
                out: (0..n)
                    .map(|_| SeatOut { tail: VecDeque::new(), total: 0, reaped: false, exit_status: None, exit: None,
                                       exit_acked: false, reader_done: false, input_pending: 0, disc_total: None, processed: 0 })
                    .collect(),
                controller: None,
                gen: 0,
                last_peer: None,
                no_controller_since: None,
                input_ids: (VecDeque::new(), HashSet::new()),
                exit_record_ok: true,
                exit_record_warned: false,
                exit_record_fail_since: None,
            };
            let policy = Policy { controller_exe: args.controller_exe.clone(), requirement: None, lock: args.lock.clone() };
            let keep = Keep { args, paths, policy, seats, st: Mutex::new(st), ledger: Mutex::new(ledger), boot_id: "b".into(),
                              start_us: Some(1), pending_hs: AtomicUsize::new(0), started: Instant::now(),
                              room: Condvar::new(), room_waiters: AtomicUsize::new(0), parent_pid: 0,
                              exit_owner: AtomicBool::new(false), _id_lock: id_lock };
            (keep, d)
        }

        /// 조종자 + 그 큐의 받는 쪽 + 소켓 맞은편(내보내면 EOF 를 읽는다).
        fn test_controller(n: usize) -> (Controller, Receiver<Vec<u8>>, UnixStream) {
            let (ours, theirs) = UnixStream::pair().unwrap();
            let (tx, rx) = channel();
            let c = Controller {
                gen: 1,
                peer: Peer { pid: 1, pidversion: 0, euid: 0, exe: None, start_us: None },
                tx,
                queued: Arc::new(AtomicUsize::new(0)),
                ctl_queued: Arc::new(AtomicUsize::new(0)),
                shut: ours,
                behind: vec![None; n],
                behind_flag: Arc::new(AtomicBool::new(false)),
                exited_sent: vec![false; n],
                evicted: false,
            };
            (c, rx, theirs)
        }

        fn ledger_events(keep: &Keep) -> Vec<(String, String)> {
            std::fs::read_to_string(&keep.paths.log)
                .unwrap_or_default()
                .lines()
                .filter_map(|l| serde_json::from_str::<Value>(l).ok())
                .map(|v| (v["event"].as_str().unwrap_or("").to_string(), v["reason"].as_str().unwrap_or("").to_string()))
                .collect()
        }

        fn peer_closed(mut theirs: UnixStream) -> bool {
            theirs.set_read_timeout(Some(Duration::from_secs(2))).unwrap();
            let mut b = [0u8; 1];
            matches!(theirs.read(&mut b), Ok(0))
        }

        #[test]
        fn enqueue_caps_control_frames_only() {
            let (tx, rx) = channel();
            let (q, cq) = (AtomicUsize::new(0), AtomicUsize::new(CTL_QUEUE_BYTES - 10));
            let exited = proto::json_frame(proto::EXITED, 0, &json!({"code": 0, "final_offset": 0}));
            assert!(exited.len() > 10);
            assert!(!enqueue(&tx, &q, &cq, exited), "제어 상한을 넘는 제어 프레임은 넣지 않는다");
            assert_eq!((q.load(Ordering::SeqCst), cq.load(Ordering::SeqCst)), (0, CTL_QUEUE_BYTES - 10), "셈 불변");
            assert!(rx.try_recv().is_err());
            // 딱 상한까지는 들어간다.
            let fit = proto::frame(proto::INPUT_ACK, 0, &vec![0u8; 10 - 9]);
            assert!(enqueue(&tx, &q, &cq, fit));
            assert_eq!(cq.load(Ordering::SeqCst), CTL_QUEUE_BYTES);
            // 출력 프레임은 제어 상한과 무관(출력은 밀림 경로가 맡는다).
            let out = proto::frame(proto::OUTPUT, 0, &proto::output_payload(0, &vec![b'x'; 2 << 20]));
            assert!(enqueue(&tx, &q, &cq, out));
            assert_eq!(cq.load(Ordering::SeqCst), CTL_QUEUE_BYTES);
        }

        #[test]
        fn queue_initial_over_control_cap_is_refused() {
            // 최초 재생(WELCOME·EXITED)도 같은 길 — 제어 바이트가 상한을 넘으면 None(= 접속 거절).
            let big = proto::frame(proto::WELCOME, ALL_SEATS, &vec![b' '; CTL_QUEUE_BYTES / 2]);
            let (q, cq) = (AtomicUsize::new(0), AtomicUsize::new(0));
            assert!(queue_initial(vec![big.clone(), big.clone(), big], &q, &cq).is_none());
            let (q, cq) = (AtomicUsize::new(0), AtomicUsize::new(0));
            let small = proto::frame(proto::WELCOME, ALL_SEATS, b"{}");
            let out = proto::frame(proto::OUTPUT, 0, &proto::output_payload(0, &vec![b'x'; 3 << 20]));
            let (_tx, rx) = queue_initial(vec![small, out], &q, &cq).expect("상한 안 = 받는다");
            assert_eq!(rx.try_iter().count(), 2);
        }

        #[test]
        fn catch_up_exited_over_control_cap_evicts() {
            // codex 3R #1 그 순서: FOREGROUND_IS 답으로 제어 큐가 상한 직전 → 밀린 좌석이 끝남 → catch_up 의 EXITED.
            let (keep, d) = test_keep("cuexit", 2);
            let (c, rx, theirs) = test_controller(2);
            {
                let mut st = lock_st(&keep);
                st.out[0].exit = Some(json!({"code": 0, "final_offset": 0}));
                st.controller = Some(c);
                let c = st.controller.as_mut().unwrap();
                c.behind[0] = Some(0);
                c.behind_flag.store(true, Ordering::SeqCst);
                c.ctl_queued.store(CTL_QUEUE_BYTES - 1, Ordering::SeqCst);
                c.queued.store(CTL_QUEUE_BYTES - 1, Ordering::SeqCst);
                catch_up(&keep, &mut st);
                let c = st.controller.as_ref().unwrap();
                assert!(c.evicted, "상한을 넘는 EXITED = 내보냄");
                assert!(c.ctl_queued.load(Ordering::SeqCst) <= CTL_QUEUE_BYTES, "제어 큐는 상한을 넘지 않는다");
            }
            assert!(rx.try_recv().is_err(), "넘는 프레임은 큐에 없다");
            assert!(peer_closed(theirs), "연결이 닫혔다");
            assert!(ledger_events(&keep).contains(&("evict".into(), "control_queue_full".into())));
            let _ = std::fs::remove_dir_all(&d);
        }

        #[test]
        fn send_ctl_over_control_cap_evicts_once() {
            let (keep, d) = test_keep("sendctl", 1);
            let (c, _rx, theirs) = test_controller(1);
            {
                let mut st = lock_st(&keep);
                c.ctl_queued.store(CTL_QUEUE_BYTES, Ordering::SeqCst);
                st.controller = Some(c);
                for _ in 0..3 {
                    send_ctl(&keep, &mut st, proto::frame(proto::FOREGROUND_IS, 0, b"{}"));
                }
                assert!(st.controller.as_ref().unwrap().evicted);
            }
            assert!(peer_closed(theirs));
            let n = ledger_events(&keep).iter().filter(|e| e.0 == "evict").count();
            assert_eq!(n, 1, "내보냄 기록은 한 번");
            let _ = std::fs::remove_dir_all(&d);
        }

        #[test]
        fn send_output_going_behind_with_drained_queue_catches_up_itself() {
            // 깨우기 경합(가능한 범위): 쓰기 스레드가 큐를 다 비우고 「표시 없음」을 본 뒤 잠든 상태 = 큐 0 · 표시 거짓.
            // 그때 밀림으로 가는 출력은 표시를 세운 뒤 큐를 다시 보고 스스로 따라잡아야 한다(안 하면 영영 밀린 채).
            let (keep, d) = test_keep("wake", 1);
            let (c, rx, _theirs) = test_controller(1);
            let n = OUT_QUEUE_BYTES + 1;
            {
                let mut st = lock_st(&keep);
                st.out[0].tail.extend(std::iter::repeat(b'y').take(n));
                st.out[0].total = n as u64;
                st.controller = Some(c);
                let bytes = vec![b'y'; n];
                send_output(&keep, &mut st, 0, 0, &bytes);
                let c = st.controller.as_ref().unwrap();
                assert_eq!(c.behind[0], Some(OUT_QUEUE_BYTES as u64), "큐 상한까지 보내고 나머지는 밀림");
            }
            let sent: usize = rx.try_iter().map(|f| f.len() - 9 - 8).sum();
            assert_eq!(sent, OUT_QUEUE_BYTES, "밀림으로 간 즉시 꼬리에서 따라잡았다");
            let _ = std::fs::remove_dir_all(&d);
        }

        /// 조종자 종속 모드(`--controller-bound`) 시험용 — 같은 Keep 에 인자만 켠다.
        fn test_keep_bound(tag: &str, tail: usize) -> (Keep, PathBuf) {
            let (mut keep, d) = test_keep(tag, 1);
            keep.args.controller_bound = true;
            keep.args.tail_bytes = tail;
            (keep, d)
        }

        #[test]
        fn bound_send_output_never_goes_behind() {
            // ⑵ 조종자 종속 모드 = 밀림이 없다 — 4MiB 를 넘는 출력도 큐에 넣는다(멈춤은 읽기 쪽 wait_for_room 몫 · 유실 0).
            let (keep, d) = test_keep_bound("bnd-nobehind", MAX_TAIL);
            let (c, rx, _theirs) = test_controller(1);
            let n = OUT_QUEUE_BYTES + 1;
            {
                let mut st = lock_st(&keep);
                st.out[0].tail.extend(std::iter::repeat(b'y').take(n));
                st.out[0].total = n as u64;
                st.controller = Some(c);
                send_output(&keep, &mut st, 0, 0, &vec![b'y'; n]);
                let c = st.controller.as_ref().unwrap();
                assert_eq!(c.behind[0], None, "조종자 종속 모드는 밀림으로 가지 않는다");
                assert!(!c.behind_flag.load(Ordering::SeqCst));
            }
            let sent: usize = rx.try_iter().map(|f| f.len() - 9 - 8).sum();
            assert_eq!(sent, n, "전부 큐에 들어갔다");
            let _ = std::fs::remove_dir_all(&d);
        }

        #[test]
        fn bound_parent_loss_is_seen_only_in_bound_mode() {
            // D2: 기동 때의 부모 pid 와 지금 부모가 다르면(부모 사망 → 입양) 조종자 종속 모드에서만 「잃음」.
            let me = unsafe { libc::getppid() };
            let (mut keep, d) = test_keep_bound("bnd-parent", MAX_TAIL);
            keep.parent_pid = me;
            assert!(!parent_lost(&keep), "부모 그대로 = 잃지 않음");
            keep.parent_pid = me + 1_000_000;
            assert!(parent_lost(&keep), "부모가 바뀜 = 잃음");
            keep.parent_pid = 1;
            assert!(parent_lost(&keep), "기동 때 이미 launchd 아래 = 잃음(띄운 cysd 가 먼저 죽음)");
            keep.args.controller_bound = false;
            assert!(!parent_lost(&keep), "인자 없는 모드(T2)는 보지 않는다");
            let _ = std::fs::remove_dir_all(&d);
        }

        /// codex 1R #4: 연결 끊김(controller_lost)과 부모 상실(parent_lost)이 같은 틈에 끝내러 들어와도 `seatkeep_exit` 는 1줄 ·
        /// 이긴 쪽 1명만 참. 매 회차 두 스레드를 장벽으로 동시에 출발시킨다(200회).
        #[test]
        fn exit_owner_is_single_under_simultaneous_entry() {
            for round in 0..200 {
                let (keep, d) = test_keep_bound(&format!("owner-{round}"), MAX_TAIL);
                let keep = Arc::new(keep);
                let bar = Arc::new(std::sync::Barrier::new(2));
                let hs: Vec<_> = ["controller_lost", "parent_lost"]
                    .into_iter()
                    .map(|why| {
                        let (k, b) = (Arc::clone(&keep), Arc::clone(&bar));
                        std::thread::spawn(move || {
                            b.wait();
                            record_controller_loss(&k, why)
                        })
                    })
                    .collect();
                let won: Vec<bool> = hs.into_iter().map(|h| h.join().unwrap()).collect();
                assert_eq!(won.iter().filter(|w| **w).count(), 1, "회차 {round}: 이긴 쪽 1명 {won:?}");
                let exits = ledger_events(&keep).into_iter().filter(|(e, _)| e == "seatkeep_exit").count();
                assert_eq!(exits, 1, "회차 {round}: seatkeep_exit 기록 1줄");
                let _ = std::fs::remove_dir_all(&d);
            }
        }

        #[test]
        fn bound_reads_only_tail_room_before_first_controller() {
            // 첫 조종자 전(gen 0) = 꼬리는 아직 아무에게도 안 간 출력 → 꼬리의 남은 칸만큼만 읽는다(앞부분이 꼬리에서 밀려나지 않게).
            let (keep, d) = test_keep_bound("bnd-tail", 100_000);
            assert_eq!(wait_for_room(&keep, 0), READ_BUF, "빈 꼬리 = 읽기 버퍼 전부");
            lock_st(&keep).out[0].tail.extend(std::iter::repeat(b'y').take(100_000 - 100));
            assert_eq!(wait_for_room(&keep, 0), 100, "남은 칸만큼만");
            assert_eq!(keep.room_waiters.load(Ordering::SeqCst), 0);
            let _ = std::fs::remove_dir_all(&d);
        }

        #[test]
        fn bound_reader_waits_at_cap_and_wakes_below_half() {
            // 큐가 상한이면 PTY 를 읽지 않고 기다린다 → 쓰기 스레드가 반 아래로 비운 뒤 wake_readers 로 깨운다.
            let (keep, d) = test_keep_bound("bnd-wait", MAX_TAIL);
            let keep = Arc::new(keep);
            let (c, _rx, _theirs) = test_controller(1);
            let queued = Arc::clone(&c.queued);
            queued.store(BOUND_QUEUE_BYTES, Ordering::SeqCst);
            lock_st(&keep).controller = Some(c);
            let (tx, got) = channel();
            let k = Arc::clone(&keep);
            std::thread::spawn(move || {
                let _ = tx.send(wait_for_room(&k, 0));
            });
            assert!(got.recv_timeout(Duration::from_millis(300)).is_err(), "상한에서는 읽지 않고 기다린다");
            assert_eq!(keep.room_waiters.load(Ordering::SeqCst), 1);
            queued.store(BOUND_QUEUE_BYTES / 2, Ordering::SeqCst);
            wake_readers(&keep, &queued);
            assert!(got.recv_timeout(Duration::from_millis(300)).is_err(), "반(되읽기 문턱)까지는 계속 기다린다");
            queued.store(BOUND_QUEUE_BYTES / 2 - 1, Ordering::SeqCst);
            wake_readers(&keep, &queued);
            assert_eq!(got.recv_timeout(Duration::from_secs(5)).expect("반 아래에서 깨어난다"), READ_BUF);
            assert_eq!(keep.room_waiters.load(Ordering::SeqCst), 0);
            let _ = std::fs::remove_dir_all(&d);
        }

        #[test]
        fn written_checks_flag_after_lowering_count() {
            // 쓰기 스레드 쪽 절반: 셈을 **내린 뒤** 표시를 본다 — 내리기 전 값으로 보면 반 아래로 막 내려간 순간을 놓친다.
            let flag = AtomicBool::new(true);
            let f = proto::frame(proto::OUTPUT, 0, &proto::output_payload(0, &[b'z'; 100]));
            let (q, cq) = (AtomicUsize::new(OUT_QUEUE_BYTES / 2 + f.len() - 1), AtomicUsize::new(0));
            assert!(written(&q, &cq, &flag, &f), "이 프레임을 쓰고 반 아래 = 따라잡기");
            flag.store(false, Ordering::SeqCst);
            let (q, cq) = (AtomicUsize::new(f.len()), AtomicUsize::new(0));
            assert!(!written(&q, &cq, &flag, &f), "밀린 좌석이 없으면 안 깨운다");
            let ack = proto::frame(proto::INPUT_ACK, 0, &[0u8; 9]);
            let (q, cq) = (AtomicUsize::new(ack.len()), AtomicUsize::new(ack.len()));
            let _ = written(&q, &cq, &flag, &ack);
            assert_eq!((q.load(Ordering::SeqCst), cq.load(Ordering::SeqCst)), (0, 0), "제어 셈도 함께 내린다");
        }

        #[test]
        fn exit_record_fail_time_is_reset_on_every_resolution() {
            use std::os::unix::fs::PermissionsExt;
            let (keep, d) = test_keep("failtime", 1);
            let dir = keep.paths.dir.clone();
            let ro = |on: bool| std::fs::set_permissions(&dir, std::fs::Permissions::from_mode(if on { 0o500 } else { 0o700 })).unwrap();
            let mut st = lock_st(&keep);
            st.out[0].exit = Some(json!({"code": 0, "final_offset": 0}));
            // ① 쓰기 실패 → 실패 시각
            ro(true);
            keep.persist_exit_record(&mut st);
            ro(false);
            assert!(!st.exit_record_ok);
            let t1 = st.exit_record_fail_since.expect("실패 시각");
            // ② 쓰기 성공 → 지움
            keep.persist_exit_record(&mut st);
            assert!(st.exit_record_ok && st.exit_record_fail_since.is_none(), "쓰기 성공");
            // ③ 다시 실패 → 새 시각(앞 시각을 이어 쓰지 않음) → 전부 확인됨 → 지움
            std::thread::sleep(Duration::from_millis(20));
            ro(true);
            keep.persist_exit_record(&mut st);
            ro(false);
            let t2 = st.exit_record_fail_since.expect("실패 시각");
            assert!(t2 > t1, "새 실패는 새 시각");
            st.out[0].exit_acked = true;
            keep.persist_exit_record(&mut st);
            assert!(st.exit_record_ok && st.exit_record_fail_since.is_none(), "전부 확인됨");
            // ④ 다시 실패 → 알린 종료가 없어짐(빈 목록) → 지움
            st.out[0].exit_acked = false;
            ro(true);
            keep.persist_exit_record(&mut st);
            ro(false);
            assert!(st.exit_record_fail_since.is_some());
            st.out[0].exit = None;
            keep.persist_exit_record(&mut st);
            assert!(st.exit_record_ok && st.exit_record_fail_since.is_none(), "보존할 기록 없음");
            drop(st);
            let _ = std::fs::remove_dir_all(&d);
        }

        impl std::fmt::Debug for Keep {
            fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
                f.write_str("Keep")
            }
        }

        /// M09 결정적 시험(T3 · T2 인계 2): **회수하는 그 순간** 신호 금지 표시(`reaped`)가 이미 서 있어야 한다.
        /// 가짜 자식의 `wait()`(= 실제 회수 자리)가 그때의 표시를 읽어 둔다 — 실행 순서를 시험이 쥐므로 부하·잠·재시도와 무관하다.
        /// 표시가 회수 뒤로 밀리면(M09 뮤턴트 = 회수 후 300ms 늦춤) 이 시험이 매번 붉다. SIGNAL·RELEASE 는 같은 잠금 안에서
        /// 이 표시를 보고 killpg 하므로(serve), 「표시가 회수보다 먼저」가 곧 「회수된 pid 에 신호 0」이다.
        #[test]
        fn reap_marks_before_reaping() {
            #[derive(Debug)]
            struct Spy(Arc<Keep>, Arc<std::sync::atomic::AtomicU8>);
            impl portable_pty::ChildKiller for Spy {
                fn kill(&mut self) -> std::io::Result<()> {
                    Ok(())
                }
                fn clone_killer(&self) -> Box<dyn portable_pty::ChildKiller + Send + Sync> {
                    Box::new(Spy(Arc::clone(&self.0), Arc::clone(&self.1)))
                }
            }
            impl Child for Spy {
                fn try_wait(&mut self) -> std::io::Result<Option<portable_pty::ExitStatus>> {
                    Ok(None)
                }
                fn wait(&mut self) -> std::io::Result<portable_pty::ExitStatus> {
                    // 회수 순간: 표시를 읽는다(1 = 서 있음 · 2 = 아직 안 섬). 잠금을 잡을 수 있어야 한다(쥔 채 회수하지 않음).
                    let marked = self.0.st.try_lock().map(|st| st.out[0].reaped).unwrap_or(false);
                    self.1.store(if marked { 1 } else { 2 }, Ordering::SeqCst);
                    Ok(portable_pty::ExitStatus::with_exit_code(0))
                }
                fn process_id(&self) -> Option<u32> {
                    None
                }
            }
            for _ in 0..10 {
                let (keep, d) = test_keep("m09", 1);
                let keep = Arc::new(keep);
                let seen = Arc::new(std::sync::atomic::AtomicU8::new(0));
                let mut spy = Spy(Arc::clone(&keep), Arc::clone(&seen));
                // pid 0 = waitid 는 실패(ECHILD)하고 경고 뒤 회수 경로로 간다 — 표시·회수 순서만 본다.
                let st = reap_marked(&keep, 0, 0, &mut spy);
                assert!(st.is_ok());
                assert_eq!(seen.load(Ordering::SeqCst), 1, "회수하는 순간 신호 금지 표시가 아직 안 섰다(회수된 pid 에 killpg 가능)");
                assert!(lock_st(&keep).out[0].reaped);
                drop(spy);
                let _ = std::fs::remove_dir_all(&d);
            }
        }

        fn alive(pid: i32) -> bool {
            if unsafe { libc::kill(pid, 0) } != 0 {
                return false;
            }
            let o = std::process::Command::new("ps").args(["-o", "stat=", "-p", &pid.to_string()]).output().unwrap();
            let t = String::from_utf8_lossy(&o.stdout).trim().to_string();
            !(t.is_empty() || t.starts_with('Z'))
        }

        /// 새 프로세스 그룹의 리더 `sh` + 같은 그룹의 손자 `sleep`. (리더 pid, 손자 pid, 리더 Child).
        fn group_with_grandchild(d: &std::path::Path) -> (i32, i32, std::process::Child) {
            use std::os::unix::process::CommandExt;
            let f = d.join("gc.pid");
            let mut cmd = std::process::Command::new("/bin/sh");
            cmd.arg("-c").arg(format!("sleep 300 & echo $! > '{}'; wait", f.display())).process_group(0);
            let child = cmd.spawn().unwrap();
            let t = Instant::now();
            let gc = loop {
                if let Some(p) = std::fs::read_to_string(&f).ok().and_then(|t| t.trim().parse::<i32>().ok()) {
                    break p;
                }
                assert!(t.elapsed() < Duration::from_secs(5), "손자 pid 를 못 받음");
                std::thread::sleep(Duration::from_millis(10));
            };
            (child.id() as i32, gc, child)
        }

        /// D7 결정 B(master#fe07cc6a) ⑴ 모르는 target = 거절(신호 0 · 그룹으로 내려가지 않음) ⑵ 회수 표시 뒤 = 신호 0 · "reaped"
        /// ⑶ "leader" = 리더에만(같은 그룹 손자 생존 — leader 갈래를 killpg 로 되돌리는 뮤턴트면 손자가 죽어 붉다) ⑷ 칸 없음·"group" = 그룹.
        #[test]
        fn signal_target_leader_group_and_refusal() {
            let (mut keep, d) = test_keep("sigtgt", 1);
            let (leader, gc, mut child) = group_with_grandchild(&d);
            keep.seats[0].child_pid = leader;
            let st = lock_st(&keep);
            for bad in ["foo", "Leader", "", "\u{0}"] {
                assert_eq!(signal_seat(&keep, &st, 0, libc::SIGKILL, Some(bad)), "bad_target", "{bad:?}");
            }
            std::thread::sleep(Duration::from_millis(100));
            assert!(alive(leader) && alive(gc), "거절된 요청이 신호를 보냈다");
            drop(st);
            // ⑵ 회수 표시가 서면 leader·group 어느 쪽도 보내지 않는다(M09 와 같은 틀 — 표시를 시험이 직접 세운다).
            lock_st(&keep).out[0].reaped = true;
            {
                let st = lock_st(&keep);
                assert_eq!(signal_seat(&keep, &st, 0, libc::SIGKILL, Some("leader")), "reaped");
                assert_eq!(signal_seat(&keep, &st, 0, libc::SIGKILL, None), "reaped");
            }
            std::thread::sleep(Duration::from_millis(100));
            assert!(alive(leader) && alive(gc), "회수 표시 뒤에 신호가 나갔다");
            lock_st(&keep).out[0].reaped = false;
            // ⑶ leader = 리더만
            {
                let st = lock_st(&keep);
                assert_eq!(signal_seat(&keep, &st, 0, libc::SIGKILL, Some("leader")), "sent");
            }
            let _ = child.wait();
            std::thread::sleep(Duration::from_millis(200));
            assert!(alive(gc), "leader 신호가 같은 그룹 손자까지 쳤다(그룹 = killpg 뮤턴트)");
            // ⑷ group = 그룹(리더가 없어도 그룹이 살아 있으면 pgid 가 유효)
            {
                let st = lock_st(&keep);
                assert_eq!(signal_seat(&keep, &st, 0, libc::SIGKILL, Some("group")), "sent");
            }
            let t = Instant::now();
            while alive(gc) && t.elapsed() < Duration::from_secs(3) {
                std::thread::sleep(Duration::from_millis(20));
            }
            assert!(!alive(gc), "group 신호가 그룹에 안 닿음");
            // pid 0(모름)에는 어떤 신호도 보내지 않는다(kill(0) = 내 그룹이 되는 것 차단).
            keep.seats[0].child_pid = 0;
            let st = lock_st(&keep);
            assert_eq!(signal_seat(&keep, &st, 0, libc::SIGWINCH, Some("leader")), "no_pid");
            assert_eq!(signal_seat(&keep, &st, 0, libc::SIGWINCH, None), "no_pid");
            drop(st);
            let _ = std::fs::remove_dir_all(&d);
        }

        // ── codex 1R #1: 조종자 종속 모드에서 부모(cysd)가 자식 기동 전·기동 중에 사라지면 좌석을 만들지 않는다 ──
        // 실제 seatkeep 실행 파일을 띄운다(디버그 빌드 `target/debug/cys-seatkeep` — `cargo build --bin cys-seatkeep` 뒤에 돌린다).
        // 「가짜 cysd」 = /bin/sh 부모 하나(seatkeep 을 낳고 wait) — 그 부모를 SIGKILL 해 cysd 사망을 흉내 낸다.

        #[cfg(target_os = "macos")]
        fn sk_exe() -> PathBuf {
            let me = std::env::current_exe().unwrap();
            let exe = me.parent().unwrap().parent().unwrap().join("cys-seatkeep");
            assert!(exe.is_file(), "seatkeep 실행 파일 없음(먼저 cargo build --bin cys-seatkeep): {}", exe.display());
            exe
        }

        #[cfg(target_os = "macos")]
        fn wait_until(limit: Duration, mut f: impl FnMut() -> bool) -> bool {
            let t = Instant::now();
            while t.elapsed() < limit {
                if f() {
                    return true;
                }
                std::thread::sleep(Duration::from_millis(10));
            }
            f()
        }

        #[cfg(target_os = "macos")]
        fn ps_field(pid: i32, field: &str) -> String {
            let o = std::process::Command::new("ps").args(["-o", &format!("{field}="), "-p", &pid.to_string()]).output().unwrap();
            String::from_utf8_lossy(&o.stdout).trim().to_string()
        }

        /// seatkeep 인자(조종자 종속 · 자식 = 표식 파일을 쓰고 30초 잔다 — 한 번이라도 떴으면 표식이 남는다).
        #[cfg(target_os = "macos")]
        fn bound_sk_args(d: &std::path::Path, marker: &std::path::Path) -> Vec<String> {
            vec![sk_exe().to_string_lossy().into_owned(), "--dir".into(), d.to_string_lossy().into_owned(), "--id".into(), "p".into(),
                 "--controller-exe".into(), "/nonexistent".into(), "--lock".into(), d.join("ctl.lock").to_string_lossy().into_owned(),
                 "--controller-bound".into(), "--".into(), "/bin/sh".into(), "-c".into(),
                 format!("echo ran > '{}'; exec sleep 30", marker.display())]
        }

        #[cfg(target_os = "macos")]
        fn read_pidfile(f: &std::path::Path) -> i32 {
            assert!(wait_until(Duration::from_secs(5), || std::fs::read_to_string(f).map(|t| t.trim().parse::<i32>().is_ok()).unwrap_or(false)), "pid 파일");
            std::fs::read_to_string(f).unwrap().trim().parse().unwrap()
        }

        /// 판정문 재현 그대로: seatkeep 을 첫 실행 전에 SIGSTOP → 부모(cysd) 종료 → SIGCONT. seatkeep 이 처음 재는 부모가 이미 1(launchd).
        /// 고침 전 = PTY·자식을 띄우고 등록부 확정까지 한 뒤에야 parent_lost(표식 생김). 고친 뒤 = 어떤 파일·자식도 만들기 전에 끝(RC_PARENT_LOST).
        #[cfg(target_os = "macos")]
        #[test]
        fn bound_parent_gone_before_first_instruction_spawns_nothing() {
            let d = tmpdir("pgone0");
            let marker = d.join("child-ran");
            let pidf = d.join("c.pid");
            // 부모 P(sh) → C(sh: 스스로 SIGSTOP · 깨면 seatkeep 으로 exec — pid 그대로라 「첫 실행 전에 멈춘 seatkeep」과 같다).
            let mut p = std::process::Command::new("/bin/sh")
                .arg("-c")
                .arg(r#"/bin/sh -c 'kill -STOP $$; exec "$@"' sk "$@" & echo $! > "$PIDF"; wait"#)
                .arg("p")
                .args(bound_sk_args(&d, &marker))
                .env("PIDF", &pidf)
                .spawn()
                .unwrap();
            let c = read_pidfile(&pidf);
            assert!(wait_until(Duration::from_secs(5), || ps_field(c, "stat").starts_with('T')), "C 가 멈추지 않음");
            let _ = p.kill();
            let _ = p.wait();
            assert!(wait_until(Duration::from_secs(5), || ps_field(c, "ppid") == "1"), "부모 종료 뒤 입양(ppid 1) 안 됨: {}", ps_field(c, "ppid"));
            unsafe { libc::kill(c, libc::SIGCONT) };
            assert!(wait_until(Duration::from_secs(10), || !alive(c)), "seatkeep 이 끝나지 않음");
            std::thread::sleep(Duration::from_millis(500));
            assert!(!marker.exists(), "부모가 이미 없는데 좌석 자식이 떴다(codex 1R #1)");
            let paths = Paths::new(&d, "p");
            assert!(!paths.entry.exists(), "등록부를 썼다(준비·확정) — 어떤 파일도 만들기 전에 끝나야 한다");
            let _ = std::fs::remove_dir_all(&d);
        }

        /// 부모를 잰 뒤(살아 있음) 자식 기동 전에 부모가 죽는 창 — 시험 지연(CYS_SEATKEEP_TEST_SPAWN_DELAY_MS)으로 넓힌다.
        /// 고친 뒤 = 기동 직전 확인에서 끝 · 기록 1줄(parent_lost · starting · spawned []) · 표식 없음.
        #[cfg(target_os = "macos")]
        #[test]
        fn bound_parent_dies_before_spawn_spawns_nothing() {
            let d = tmpdir("pgone1");
            let marker = d.join("child-ran");
            let pidf = d.join("s.pid");
            let mut p = std::process::Command::new("/bin/sh")
                .arg("-c")
                .arg(r#""$@" & echo $! > "$PIDF"; wait"#)
                .arg("p")
                .args(bound_sk_args(&d, &marker))
                .env("PIDF", &pidf)
                .env("CYS_SEATKEEP_TEST_SPAWN_DELAY_MS", "1500")
                .spawn()
                .unwrap();
            let sk = read_pidfile(&pidf);
            let paths = Paths::new(&d, "p");
            assert!(wait_until(Duration::from_secs(5), || paths.entry.exists()), "준비 기록 없음");
            let _ = p.kill();
            let _ = p.wait();
            assert!(wait_until(Duration::from_secs(5), || !alive(sk)), "seatkeep 이 끝나지 않음");
            std::thread::sleep(Duration::from_millis(300));
            assert!(!marker.exists(), "부모가 죽은 뒤 좌석 자식이 떴다(codex 1R #1)");
            let log = std::fs::read_to_string(&paths.log).unwrap_or_default();
            let exits: Vec<Value> = log.lines().filter_map(|l| serde_json::from_str::<Value>(l).ok()).filter(|v| v["event"] == "seatkeep_exit").collect();
            assert_eq!(exits.len(), 1, "seatkeep_exit 1줄: {log}");
            assert_eq!(exits[0]["reason"], "parent_lost");
            assert_eq!(exits[0]["spawned"], json!([]), "자식을 하나도 띄우지 않았어야 한다: {log}");
            assert!(!log.lines().filter_map(|l| serde_json::from_str::<Value>(l).ok()).any(|v| v["event"] == "spawned"), "확정(spawned) 기록이 있다: {log}");
            let _ = std::fs::remove_dir_all(&d);
        }

        /// codex 2R #1 시험대: 「가짜 cysd」(sh) 아래 seatkeep 을 띄우고 seatkeep 이 뜬 지 0.3초 뒤 부모를 죽인다 → 끝날 때까지 기다린 뒤
        /// (표식 = 좌석 자식이 한 번이라도 떴는가 · 기록의 seatkeep_exit 줄들)을 돌려준다. `envs` = 시험 지연 훅.
        #[cfg(target_os = "macos")]
        fn parent_dies_early(tag: &str, envs: &[(&str, &str)]) -> (bool, Vec<Value>, Duration) {
            let d = tmpdir(tag);
            let marker = d.join("child-ran");
            let pidf = d.join("s.pid");
            let mut cmd = std::process::Command::new("/bin/sh");
            cmd.arg("-c").arg(r#""$@" & echo $! > "$PIDF"; wait"#).arg("p").args(bound_sk_args(&d, &marker)).env("PIDF", &pidf);
            for (k, v) in envs {
                cmd.env(k, v);
            }
            let marker_wait = envs.iter().any(|(k, _)| *k == "WAIT_MARKER_BEFORE_KILL");
            let seen = d.join("parent-seen");
            cmd.env("CYS_SEATKEEP_TEST_PARENT_SEEN_FILE", &seen);
            let mut p = cmd.spawn().unwrap();
            let sk = read_pidfile(&pidf);
            // 부모를 잰 뒤에 죽인다(부하로 seatkeep 첫 줄이 늦어도 같은 창을 친다).
            assert!(wait_until(Duration::from_secs(10), || seen.exists()), "seatkeep 이 부모를 재지 않음");
            if marker_wait {
                assert!(wait_until(Duration::from_secs(10), || marker.exists()), "자식이 안 떴다(이 시험은 기동 뒤 창)");
            }
            let t_kill = Instant::now();
            let _ = p.kill();
            let _ = p.wait();
            assert!(wait_until(Duration::from_secs(15), || !alive(sk)), "seatkeep 이 끝나지 않음");
            let took = t_kill.elapsed();
            std::thread::sleep(Duration::from_millis(300));
            let ran = marker.exists();
            let log = std::fs::read_to_string(Paths::new(&d, "p").log).unwrap_or_default();
            let exits = log.lines().filter_map(|l| serde_json::from_str::<Value>(l).ok()).filter(|v| v["event"] == "seatkeep_exit").collect();
            let _ = std::fs::remove_dir_all(&d);
            (ran, exits, took)
        }

        /// codex 2R #1 ① 등록 전 스케줄 틈: 감시 스레드가 늦게 돈다(CYS_SEATKEEP_TEST_WATCH_DELAY_MS 3초) · 자식은 뜨고 등록부 확정 중
        /// (CYS_SEATKEEP_TEST_COMMIT_DELAY_MS 5초 · supervise 아직 안 돎)에 부모가 죽는다. 고친 뒤 = 주 스레드가 감시 준비(등록)를 기다린 뒤
        /// 진행했으므로 감시가 곧바로 끝낸다(1.5초 안). 고치기 전 = 감시가 아직 등록 전이라 늦게(≈ 지연 끝) 또는 확정 뒤에야 끝난다.
        #[cfg(target_os = "macos")]
        #[test]
        fn bound_watcher_late_schedule_still_ends_at_once() {
            let (_ran, exits, took) = parent_dies_early("pgone3", &[("CYS_SEATKEEP_TEST_WATCH_DELAY_MS", "3000"),
                ("CYS_SEATKEEP_TEST_COMMIT_DELAY_MS", "5000"), ("WAIT_MARKER_BEFORE_KILL", "1")]);
            assert!(took < Duration::from_millis(1500), "부모 사망 뒤 끝나기까지 {took:?} — 감시가 등록 전이었다(codex 2R #1) · 기록 {exits:?}");
            assert_eq!(exits.len(), 1, "seatkeep_exit 1줄: {exits:?}");
            assert_eq!(exits[0]["reason"], "parent_lost");
        }

        /// codex 3R #1: 부모 감시를 세우지 못하면(감시 스레드 생성 실패 · 맥 kqueue 실패 — 디버그 훅 CYS_SEATKEEP_TEST_WATCH_FAIL)
        /// 감시 없이 진행하지 않는다 = PTY·파일·자식 전에 rc 9(fail-closed). 고치기 전 = 그대로 진행해 좌석 자식이 뜸.
        #[cfg(target_os = "macos")]
        #[test]
        fn bound_watch_unavailable_fails_closed() {
            for mode in ["spawn", "kqueue"] {
                let d = tmpdir(&format!("wfail-{mode}"));
                let marker = d.join("child-ran");
                let args = bound_sk_args(&d, &marker);
                let mut sk = std::process::Command::new(&args[0]).args(&args[1..]).env("CYS_SEATKEEP_TEST_WATCH_FAIL", mode).spawn().unwrap();
                let t = Instant::now();
                let mut rc = None;
                while t.elapsed() < Duration::from_secs(10) {
                    if let Ok(Some(st)) = sk.try_wait() {
                        rc = st.code();
                        break;
                    }
                    std::thread::sleep(Duration::from_millis(20));
                }
                if rc.is_none() {
                    let _ = sk.kill();
                    let _ = sk.wait();
                }
                std::thread::sleep(Duration::from_millis(300));
                let ran = marker.exists();
                let entry = Paths::new(&d, "p").entry.exists();
                let _ = std::fs::remove_dir_all(&d);
                assert_eq!(rc, Some(RC_WATCH_UNAVAILABLE), "{mode}: 감시를 못 세웠는데 rc {rc:?}");
                assert!(!ran && !entry, "{mode}: 감시 없이 진행(자식 {ran} · 등록부 {entry})");
            }
        }

        /// seatkeep 을 디버그 훅 환경과 함께 직접 띄워(부모 = 이 시험 프로세스 · 살아 있음) 끝날 때까지(최대 `limit`) 기다린다.
        /// 돌려주는 값 = (rc · 끝나기까지 · 상태 폴더 파일 이름들(표식 제외) · seatkeep_exit 줄들). 끝나지 않으면 SIGKILL 하고 rc None.
        #[cfg(target_os = "macos")]
        fn run_sk_with(tag: &str, script: &str, envs: &[(&str, &str)], limit: Duration) -> (Option<i32>, Duration, Vec<String>, Vec<Value>, PathBuf) {
            run_sk_io(tag, script, envs, limit, None)
        }

        /// `run_sk_with` + seatkeep 의 stderr 를 `stderr` 로 준다(codex r4b #2 — 가득 찬 파이프). 환경값의 `{D}` = 상태 폴더.
        #[cfg(target_os = "macos")]
        fn run_sk_io(tag: &str, script: &str, envs: &[(&str, &str)], limit: Duration, stderr: Option<std::process::Stdio>)
            -> (Option<i32>, Duration, Vec<String>, Vec<Value>, PathBuf) {
            let d = tmpdir(tag);
            let mut args = bound_sk_args(&d, &d.join("unused"));
            *args.last_mut().unwrap() = script.replace("{D}", &d.to_string_lossy());
            let mut cmd = std::process::Command::new(&args[0]);
            cmd.args(&args[1..]);
            for (k, v) in envs {
                cmd.env(k, v.replace("{D}", &d.to_string_lossy()));
            }
            if let Some(s) = stderr {
                cmd.stderr(s);
            }
            let mut sk = cmd.spawn().unwrap();
            let t = Instant::now();
            let mut rc = None;
            while t.elapsed() < limit {
                if let Ok(Some(st)) = sk.try_wait() {
                    rc = st.code();
                    break;
                }
                std::thread::sleep(Duration::from_millis(20));
            }
            let took = t.elapsed();
            if rc.is_none() {
                let _ = sk.kill();
                let _ = sk.wait();
            }
            std::thread::sleep(Duration::from_millis(300));
            let log = std::fs::read_to_string(Paths::new(&d, "p").log).unwrap_or_default();
            let exits = log.lines().filter_map(|l| serde_json::from_str::<Value>(l).ok()).filter(|v| v["event"] == "seatkeep_exit").collect();
            let mut files: Vec<String> = Vec::new();
            for e in walk(&d) {
                let rel = e.strip_prefix(&d).unwrap().to_string_lossy().into_owned();
                if !rel.starts_with("child-") {
                    files.push(rel);
                }
            }
            files.sort();
            (rc, took, files, exits, d)
        }

        #[cfg(target_os = "macos")]
        fn walk(d: &std::path::Path) -> Vec<PathBuf> {
            let mut out = Vec::new();
            if let Ok(rd) = std::fs::read_dir(d) {
                for e in rd.flatten() {
                    let p = e.path();
                    if p.is_dir() {
                        out.extend(walk(&p));
                    }
                    out.push(p);
                }
            }
            out
        }

        /// codex r4 #2: 감시 등록 때 이미 상실(Watch::Gone · 디버그 훅 WATCH_FAIL=gone = 등록 ESRCH 흉내) → 상태 폴더·잠금·장부·등록부를
        /// 만들기 전에 rc 8(흔적 0). 고치기 전(Unavailable 만 처리) = 계속 진행해 .lock·.log·등록부를 만든 뒤 기동 확인에서 rc 8.
        #[cfg(target_os = "macos")]
        #[test]
        fn bound_watch_gone_ends_before_any_file() {
            let (rc, _, files, exits, d) = run_sk_with("wgone", "echo $$ > '{D}/child-ran'; exec sleep 30",
                &[("CYS_SEATKEEP_TEST_WATCH_FAIL", "gone"), ("CYS_SEATKEEP_TEST_SPAWN_DELAY_MS", "300")], Duration::from_secs(10));
            let ran = d.join("child-ran").exists();
            let _ = std::fs::remove_dir_all(&d);
            assert_eq!(rc, Some(RC_PARENT_LOST), "Gone 인데 rc {rc:?}");
            assert!(!ran, "Gone 인데 좌석 자식이 떴다");
            assert!(files.is_empty() && exits.is_empty(), "Gone 인데 상태 파일을 만들었다: {files:?} · 기록 {exits:?}");
        }

        /// codex r4 #1 ⑴: 등록·Ready 뒤 kqueue 대기 kevent() 가 실패(디버그 훅 WATCH_FAIL=kevent · 지연 0) + 자식 기동 지연 300ms →
        /// 폴링으로 내려가지 않고 자식 전에 끝(rc 9 · 자식 표식 0 · 기록 watch_lost spawned []). 고치기 전 = 맥에서도 20ms 폴링으로 내려가
        /// (부모가 살아 있으니) 자식이 뜬다.
        #[cfg(target_os = "macos")]
        #[test]
        fn bound_watch_wait_failure_before_spawn_fails_closed() {
            let (rc, _, _files, exits, d) = run_sk_with("wkev1", "echo $$ > '{D}/child-ran'; exec sleep 30",
                &[("CYS_SEATKEEP_TEST_WATCH_FAIL", "kevent"), ("CYS_SEATKEEP_TEST_KEVENT_FAIL_DELAY_MS", "0"),
                  ("CYS_SEATKEEP_TEST_SPAWN_DELAY_MS", "300")], Duration::from_secs(10));
            let ran = d.join("child-ran").exists();
            let _ = std::fs::remove_dir_all(&d);
            assert_eq!(rc, Some(RC_WATCH_UNAVAILABLE), "감시 대기 실패인데 rc {rc:?} · 기록 {exits:?}");
            assert!(!ran, "감시를 잃었는데 좌석 자식이 떴다(폴링 대신) · 기록 {exits:?}");
            assert!(exits.len() == 1 && exits[0]["reason"] == "watch_lost" && exits[0]["spawned"] == json!([]), "기록: {exits:?}");
        }

        /// codex r4 #1 ⑵: 좌석이 돌던 중(Keep 뒤) kevent 대기 실패(지연 1.5초) → 부모 상실과 같은 길(end_for_controller_loss)로 곧바로 끝:
        /// 기록 watch_lost 1줄 · 좌석 자식(SIGHUP) 사라짐. 고치기 전 = 폴링으로 내려가 좌석이 계속 돈다(부모 생존).
        #[cfg(target_os = "macos")]
        #[test]
        fn bound_watch_wait_failure_after_start_ends_like_parent_loss() {
            let (rc, took, _files, exits, d) = run_sk_with("wkev2", "echo $$ > '{D}/child-ran'; exec sleep 30",
                &[("CYS_SEATKEEP_TEST_WATCH_FAIL", "kevent"), ("CYS_SEATKEEP_TEST_KEVENT_FAIL_DELAY_MS", "1500")], Duration::from_secs(10));
            let child: i32 = std::fs::read_to_string(d.join("child-ran")).ok().and_then(|t| t.trim().parse().ok()).unwrap_or(0);
            let child_gone = child > 0 && wait_until(Duration::from_secs(5), || !alive(child));
            if child > 0 && !child_gone {
                unsafe { libc::kill(child, libc::SIGKILL) };
            }
            let _ = std::fs::remove_dir_all(&d);
            assert!(child > 0, "이 시험은 좌석이 뜬 뒤의 창이다(자식 표식 없음) · 기록 {exits:?}");
            assert!(rc.is_some() && took < Duration::from_secs(8), "감시를 잃었는데 seatkeep 이 안 끝남(폴링 대신) rc {rc:?} · {took:?}");
            assert!(exits.len() == 1 && exits[0]["reason"] == "watch_lost", "기록 watch_lost 1줄: {exits:?}");
            assert!(child_gone, "좌석 자식이 끝나지 않음");
        }

        /// codex r4b #1 재현 순서: Ready → 주 스레드가 자식 직전 「마지막 확인」을 통과하고 멈춤(디버그 틈 SPAWN_GAP 1초) → 그 틈에 감시 kevent
        /// 대기 실패(지연 200ms). 닫혀야 하는 성질 = 「상실 표시가 선 뒤에는 spawn 이 없다 · spawn 이 먼저면 감시가 Keep 을 보고 끝낸다」.
        /// 잼 = 순서 기록(TRACE: mark·spawn)에서 mark 가 spawn 앞이면 붉음 · 끝 = 감시의 Keep 길(watch_lost · `phase: starting` 없음) · 8초 안 ·
        /// 좌석 자식 사라짐. 고치기 전 = 감시가 Keep 없이 표시만 하고 떠난 뒤 주 스레드가 spawn(mark → spawn · 사후 검사 rc 9 spawned [pid]).
        /// 커널 오류가 틈 안에 돌아오는 것 자체는 물리적으로 못 막는다 — 그 경우의 끝 = 「spawn 직후 상실」과 같은 결과(이 시험이 그것을 잰다).
        #[cfg(target_os = "macos")]
        #[test]
        fn bound_watch_lost_in_spawn_gap_never_marks_before_spawn() {
            let (rc, took, _files, exits, d) = run_sk_with("wgap", "echo $$ > '{D}/child-ran'; exec sleep 30",
                &[("CYS_SEATKEEP_TEST_WATCH_FAIL", "kevent"), ("CYS_SEATKEEP_TEST_KEVENT_FAIL_DELAY_MS", "200"),
                  ("CYS_SEATKEEP_TEST_SPAWN_GAP_MS", "1000"), ("CYS_SEATKEEP_TEST_TRACE_FILE", "{D}/child-trace")], Duration::from_secs(10));
            let trace = std::fs::read_to_string(d.join("child-trace")).unwrap_or_default();
            let order: Vec<&str> = trace.lines().collect();
            let child: i32 = std::fs::read_to_string(d.join("child-ran")).ok().and_then(|t| t.trim().parse().ok()).unwrap_or(0);
            let child_gone = child <= 0 || wait_until(Duration::from_secs(5), || !alive(child));
            if child > 0 && !child_gone {
                unsafe { libc::kill(child, libc::SIGKILL) };
            }
            let _ = std::fs::remove_dir_all(&d);
            assert_eq!(order.iter().filter(|w| **w == "mark").count(), 1, "상실 표시 1회 · 순서 {order:?}");
            let (m, s) = (order.iter().position(|w| *w == "mark"), order.iter().position(|w| *w == "spawn"));
            assert!(!matches!((m, s), (Some(m), Some(s)) if m < s), "상실 표시 뒤에 spawn 이 일어났다(codex r4b #1) · 순서 {order:?} · 기록 {exits:?}");
            assert!(rc.is_some() && took < Duration::from_secs(8), "감시를 잃었는데 seatkeep 이 안 끝남 rc {rc:?} · {took:?}");
            assert!(exits.len() == 1 && exits[0]["reason"] == "watch_lost", "기록 watch_lost 1줄: {exits:?}");
            if s.is_some() {
                // spawn 이 먼저였다 = 감시가 Keep 을 보고 끝냈어야 한다(기동 단계 끝 `phase: starting` 이 아님).
                assert!(exits[0].get("phase").is_none(), "spawn 이 먼저인데 감시가 Keep 을 못 보고 떠났다: {exits:?}");
            }
            assert!(child_gone, "좌석 자식이 끝나지 않음");
        }

        /// stderr 를 아무도 안 읽는 가득 찬 파이프로 만든다(쓰기 끝 = 막힘 모드로 되돌림 · 읽기 끝은 부르는 쪽이 쥔다).
        #[cfg(target_os = "macos")]
        fn full_pipe() -> (std::os::fd::OwnedFd, std::process::Stdio) {
            use std::os::fd::FromRawFd;
            let mut fds = [0i32; 2];
            assert_eq!(unsafe { libc::pipe(fds.as_mut_ptr()) }, 0);
            let (r, w) = (fds[0], fds[1]);
            unsafe {
                // 같은 시험 프로세스의 다른 시험이 띄우는 자식에게 새지 않게(seatkeep 쪽 stderr 는 dup2 라 그대로 물림).
                libc::fcntl(r, libc::F_SETFD, libc::FD_CLOEXEC);
                libc::fcntl(w, libc::F_SETFD, libc::FD_CLOEXEC);
                let fl = libc::fcntl(w, libc::F_GETFL);
                libc::fcntl(w, libc::F_SETFL, fl | libc::O_NONBLOCK);
                let buf = [b'x'; 4096];
                while libc::write(w, buf.as_ptr() as *const libc::c_void, buf.len()) > 0 {}
                while libc::write(w, buf.as_ptr() as *const libc::c_void, 1) > 0 {}
                assert_eq!(libc::write(w, buf.as_ptr() as *const libc::c_void, 1), -1, "파이프가 안 찼다");
                libc::fcntl(w, libc::F_SETFL, fl);
                (std::os::fd::OwnedFd::from_raw_fd(r), std::process::Stdio::from(std::os::fd::OwnedFd::from_raw_fd(w)))
            }
        }

        /// codex r4b #2: stderr = 아무도 안 읽는 가득 찬 파이프(cysd 가 stderr 를 그대로 물려주는 꼴 · seat_proc.rs) 인 채 감시 상실 →
        /// 종료가 stderr 쓰기에서 멈추지 않는다. ⑴ 좌석이 돌던 중(Keep 뒤 · kevent 지연 1.5초) = 8초 안 rc · 기록 watch_lost · 소켓 없음 ·
        /// 좌석 자식 사라짐 ⑵ 기동 단계(자식 전 · 지연 0 + 자식 기동 지연 300ms) = 8초 안 rc 9 · 기록 watch_lost spawned [] · 소켓 없음.
        /// 고치기 전 = 감시가 상실 표시 뒤 `warn!`(동기 stderr 쓰기)에서 영구히 멈춘다(⑴ 좌석 계속 돎 · ⑵ end_early 의 끝 warn 에서도 멈춤).
        #[cfg(target_os = "macos")]
        #[test]
        fn bound_watch_lost_ends_even_if_stderr_blocks() {
            for (tag, envs, want_rc) in [
                ("wfull1", vec![("CYS_SEATKEEP_TEST_WATCH_FAIL", "kevent"), ("CYS_SEATKEEP_TEST_KEVENT_FAIL_DELAY_MS", "1500")], None),
                ("wfull2", vec![("CYS_SEATKEEP_TEST_WATCH_FAIL", "kevent"), ("CYS_SEATKEEP_TEST_KEVENT_FAIL_DELAY_MS", "0"),
                                ("CYS_SEATKEEP_TEST_SPAWN_DELAY_MS", "300")], Some(RC_WATCH_UNAVAILABLE)),
            ] {
                let (_keep_reader, stderr) = full_pipe();
                let (rc, took, files, exits, d) = run_sk_io(tag, "echo $$ > '{D}/child-ran'; exec sleep 30", &envs, Duration::from_secs(8), Some(stderr));
                let child: i32 = std::fs::read_to_string(d.join("child-ran")).ok().and_then(|t| t.trim().parse().ok()).unwrap_or(0);
                let child_gone = child <= 0 || wait_until(Duration::from_secs(5), || !alive(child));
                if child > 0 && !child_gone {
                    unsafe { libc::kill(child, libc::SIGKILL) };
                }
                let _ = std::fs::remove_dir_all(&d);
                assert!(rc.is_some(), "{tag}: stderr 가 막히니 감시 상실 뒤 seatkeep 이 안 끝남({took:?}) · 기록 {exits:?} · 파일 {files:?}");
                if let Some(w) = want_rc {
                    assert_eq!(rc, Some(w), "{tag}: rc");
                    assert!(child <= 0, "{tag}: 자식 전 감시 상실인데 좌석 자식이 떴다");
                } else {
                    assert!(child > 0, "{tag}: 이 갈래는 좌석이 뜬 뒤의 창이다(자식 표식 없음)");
                }
                assert!(exits.len() == 1 && exits[0]["reason"] == "watch_lost", "{tag}: 기록 watch_lost 1줄: {exits:?}");
                assert!(!files.iter().any(|f| f.ends_with("p.sock")), "{tag}: 소켓이 남았다: {files:?}");
                assert!(child_gone, "{tag}: 좌석 자식이 끝나지 않음");
            }
        }

        /// codex 2R #1 ② 감시가 상실을 본 뒤 표시가 늦은 창(폴링 대신 20ms 창과 같은 꼴): CYS_SEATKEEP_TEST_GONE_DELAY_MS 4초 ·
        /// 자식 기동 직전 확인은 1.5초(CYS_SEATKEEP_TEST_SPAWN_DELAY_MS). 고친 뒤 = 기동 확인이 getppid 를 직접 봐서 끝(자식 0).
        #[cfg(target_os = "macos")]
        #[test]
        fn bound_parent_gone_seen_directly_before_flag() {
            let (ran, exits, _) = parent_dies_early("pgone4", &[("CYS_SEATKEEP_TEST_GONE_DELAY_MS", "4000"), ("CYS_SEATKEEP_TEST_SPAWN_DELAY_MS", "1500")]);
            assert!(!ran, "감시 표시 전이라 좌석 자식이 떴다(codex 2R #1 직접 확인 없음) · 기록 {exits:?}");
            // 부하로 seatkeep 첫 줄이 부모 사망보다 늦으면 기동 때 ppid 1 → 파일 없이 rc 8(기록 0줄)도 맞는 끝이다.
            assert!(exits.is_empty() || (exits.len() == 1 && exits[0]["reason"] == "parent_lost" && exits[0]["spawned"] == json!([])),
                    "seatkeep_exit = 0줄 또는 parent_lost·spawned [] 1줄: {exits:?}");
        }

        /// 자식 기동 뒤 · 등록부 확정 중(시험 지연 CYS_SEATKEEP_TEST_COMMIT_DELAY_MS 3초)에 부모가 죽음 — supervise 는 아직 안 돈다.
        /// 고친 뒤 = 부모 감시(kqueue)가 바로 끝냄(지연 3초를 기다리지 않음 · 확정 기록 없음). 고침 전 = 지연 + 확정 + 100ms 뒤.
        #[cfg(target_os = "macos")]
        #[test]
        fn bound_parent_dies_during_commit_ends_at_once() {
            let d = tmpdir("pgone2");
            let marker = d.join("child-ran");
            let pidf = d.join("s.pid");
            let mut p = std::process::Command::new("/bin/sh")
                .arg("-c")
                .arg(r#""$@" & echo $! > "$PIDF"; wait"#)
                .arg("p")
                .args(bound_sk_args(&d, &marker))
                .env("PIDF", &pidf)
                .env("CYS_SEATKEEP_TEST_COMMIT_DELAY_MS", "3000")
                .spawn()
                .unwrap();
            let sk = read_pidfile(&pidf);
            assert!(wait_until(Duration::from_secs(5), || marker.exists()), "자식이 안 떴다(이 시험은 기동 뒤 창)");
            let _ = p.kill();
            let _ = p.wait();
            let t = Instant::now();
            assert!(wait_until(Duration::from_secs(10), || !alive(sk)), "seatkeep 이 끝나지 않음");
            let took = t.elapsed();
            assert!(took < Duration::from_millis(1500), "부모 사망 뒤 끝나기까지 {took:?} — 확정 지연(3초)을 기다렸다");
            let paths = Paths::new(&d, "p");
            let log = std::fs::read_to_string(&paths.log).unwrap_or_default();
            let exits: Vec<Value> = log.lines().filter_map(|l| serde_json::from_str::<Value>(l).ok()).filter(|v| v["event"] == "seatkeep_exit").collect();
            assert_eq!(exits.len(), 1, "seatkeep_exit 1줄: {log}");
            assert_eq!(exits[0]["reason"], "parent_lost");
            assert!(!log.lines().filter_map(|l| serde_json::from_str::<Value>(l).ok()).any(|v| v["event"] == "spawned"), "확정(spawned) 기록이 있다: {log}");
            let _ = std::fs::remove_dir_all(&d);
        }

        /// handshake-timeout 시험대: 조종자 = 이 시험 프로세스(실행 파일 · 잠금 = 「pid 출생시각」 + flock). seatkeep 은 HELLO 를 읽은 뒤
        /// 두 번째 신원 확인을 시험 지연 CYS_SEATKEEP_TEST_AUTH_DELAY_MS(3.6초)로 늦춘다(실측된 느린 자리 · 기한 3초 넘김).
        /// `hold` = 조종자가 첫 답을 받은 뒤에도 연결을 1.5초 쥐고 있는가(실제 cysd 처럼 → 늦은 확인이 성공해 늦은 수락 길까지 감).
        /// 돌려줌 = (조종자가 받은 첫 프레임의 REJECT 이유 · 기록 「event:reason」 목록 · 끝에 seatkeep 생존).
        #[cfg(target_os = "macos")]
        fn slow_handshake(tag: &str, hold: bool) -> (Option<String>, Vec<String>, bool) {
            let (r, k, a, _) = slow_handshake_with(tag, hold, &[("CYS_SEATKEEP_TEST_AUTH_DELAY_MS", "3600")]);
            (r, k, a)
        }

        #[cfg(target_os = "macos")]
        fn slow_handshake_with(tag: &str, hold: bool, envs: &[(&str, &str)]) -> (Option<String>, Vec<String>, bool, Duration) {
            use std::os::unix::io::AsRawFd as _;
            // 핸드셰이크 시험끼리는 한 번에 하나 — 신원 조회(Security)가 동시 호출 수에 비례해 느려져(실측) 시간 경계가 흔들린다.
            static SERIAL: Mutex<()> = Mutex::new(());
            let _serial = SERIAL.lock().unwrap_or_else(|e| e.into_inner());
            let d = tmpdir(tag);
            let lock = d.join("ctl.lock");
            let mut lf = std::fs::OpenOptions::new().create(true).read(true).write(true).open(&lock).unwrap();
            assert_eq!(unsafe { libc::flock(lf.as_raw_fd(), libc::LOCK_EX | libc::LOCK_NB) }, 0);
            let me = std::process::id() as i32;
            write!(lf, "{} {}", me, registry::process_start_us(me).unwrap()).unwrap();
            lf.flush().unwrap();
            let me_exe = std::env::current_exe().unwrap();
            let mut sk = std::process::Command::new(sk_exe())
                .args(["--dir", d.to_str().unwrap(), "--id", "h", "--controller-exe", me_exe.to_str().unwrap(),
                       "--lock", lock.to_str().unwrap(), "--controller-bound", "--", "/bin/sleep", "30"])
                .envs(envs.iter().copied())
                .spawn()
                .unwrap();
            let paths = Paths::new(&d, "h");
            assert!(wait_until(Duration::from_secs(5), || std::fs::read_to_string(&paths.entry).map(|t| t.contains("committed")).unwrap_or(false)),
                    "확정 기록 없음");
            let mut c = UnixStream::connect(&paths.sock).unwrap();
            proto::write_all(&mut c, &proto::json_frame(proto::HELLO, 0, &json!({"core": proto::CORE_VERSION, "resume": {}}))).unwrap();
            let t_hello = Instant::now();
            c.set_read_timeout(Some(Duration::from_secs(10))).unwrap();
            let first = proto::read_frame(&mut c);
            let first_after = t_hello.elapsed();
            if hold {
                // 늦은 두 번째 확인이 조종자가 붙어 있는 동안 끝나게(조회가 수 초까지 늘어도) — 그래야 늦은 수락 길까지 간다.
                std::thread::sleep(Duration::from_millis(6000));
            }
            drop(c);
            // 늦은 길(지연 뒤 두 번째 확인 · 수락 준비)이 끝날 때까지 — 신원 조회는 부하에서 수 초까지 늘어난다(실측 · HANDOFF).
            std::thread::sleep(Duration::from_millis(4000));
            let alive = matches!(sk.try_wait(), Ok(None));
            let kinds: Vec<String> = std::fs::read_to_string(&paths.log).unwrap_or_default().lines()
                .filter_map(|l| serde_json::from_str::<Value>(l).ok())
                .map(|v| format!("{}:{}", v["event"].as_str().unwrap_or(""), v["reason"].as_str().unwrap_or("")))
                .collect();
            let _ = sk.kill();
            let _ = sk.wait();
            let _ = std::fs::remove_dir_all(&d);
            let rej = match &first {
                Ok(Some((k, _, p))) if *k == proto::REJECT => serde_json::from_slice::<Value>(p).ok().and_then(|v| v["reason"].as_str().map(str::to_string)),
                _ => None,
            };
            (rej, kinds, alive, first_after)
        }

        /// handshake-timeout(master#5b9e1d26 ⑵) ① 조종자가 연결을 쥐고 기다리는 경우(실제 cysd 꼴): 감시가 `reject handshake_timeout`
        /// 1줄 + REJECT 프레임을 남기고 닫으며, 늦게 끝난 확인은 수락하지 않는다(조종자 종속 seatkeep 이 controller_lost 로 끝나지 않음).
        /// 고치기 전(= 시험 뮤턴트 M5-prefix) = EOF · 기록 accept → disconnect → seatkeep_exit controller_lost.
        #[cfg(target_os = "macos")]
        #[test]
        fn handshake_timeout_is_recorded_once_and_blocks_late_accept() {
            let (rej, kinds, alive) = slow_handshake("hs-timeout-hold", true);
            eprintln!("[hs-hold] rej={rej:?} kinds={kinds:?} alive={alive}");
            assert_eq!(rej.as_deref(), Some("handshake_timeout"), "조종자가 받은 첫 프레임 = REJECT handshake_timeout(기록 없는 닫힘 아님) · 기록 {kinds:?}");
            assert_eq!(kinds.iter().filter(|k| k.starts_with("reject:")).collect::<Vec<_>>(), vec!["reject:handshake_timeout"], "거절 기록 1줄: {kinds:?}");
            assert!(!kinds.iter().any(|k| k.starts_with("accept:")), "시간 초과 뒤 늦은 수락: {kinds:?}");
            // 조종자가 한 번도 걸리지 않았다 = disconnect·controller_lost 없음(15초 첫 조종자 상한 no_first_controller 끝은 정상 · 시험이 길다).
            assert!(!kinds.iter().any(|k| k.starts_with("disconnect:") || k == "seatkeep_exit:controller_lost"), "늦은 수락 → controller_lost: alive={alive} {kinds:?}");
        }

        /// codex 2R #3: 두 번째 확인은 기한 전에 끝났지만(지연 없음) 수락 준비(상태 잠금 안 · CYS_SEATKEEP_TEST_ACCEPT_DELAY_MS 4초)가 기한을
        /// 넘긴다 → 끝맺음은 조종자를 실제로 거는 자리에서 잡으므로 감시가 이긴다: 조종자 = REJECT handshake_timeout · 기록 = accept 뒤
        /// accept_aborted handshake_timeout · 조종자 걸림 0(disconnect·seatkeep_exit 없음). 고치기 전 = 들머리에서 끝맺음을 잡아 감시는 아무것도
        /// 안 하고 늦게 WELCOME(「3초 전체」 약속 위반 · reject 없음).
        #[cfg(target_os = "macos")]
        #[test]
        fn handshake_timeout_during_accept_preparation_aborts_accept() {
            // 부하로 두 번의 신원 조회가 이미 3초를 넘기면 시간 초과가 준비 「전」에 와서 이 시나리오가 안 생긴다(그때는 조용히 물러남이
            // 맞는 동작 · 위 ① 시험 몫) — 준비 「중」 시간 초과가 실제로 생긴 회차(accept 줄 있음)를 최대 3번까지 찾는다.
            let mut got = None;
            for round in 0..3 {
                let r = slow_handshake_with(&format!("hs-timeout-prep{round}"), true, &[("CYS_SEATKEEP_TEST_ACCEPT_DELAY_MS", "6000")]);
                let reached = r.1.iter().any(|k| k.starts_with("accept:")) || r.0.is_none();
                eprintln!("[hs-prep] 회차 {round} reached={reached} {r:?}");
                if reached {
                    got = Some(r);
                    break;
                }
            }
            let (rej, kinds, alive, first_after) = got.expect("3회 모두 준비 전에 시간 초과(신원 조회가 3초 넘음 · 부하) — 이 시나리오에 닿지 못함");
            assert_eq!(rej.as_deref(), Some("handshake_timeout"), "첫 프레임 = REJECT handshake_timeout(늦은 WELCOME 아님) · 기록 {kinds:?}");
            // codex 3R #3: 수락 준비가 상태 잠금을 6초 쥐어도 REJECT 는 기한(HELLO_TIMEOUT 3초) + 허용 오차 1.5초 안에 온다.
            assert!(first_after < HELLO_TIMEOUT + Duration::from_millis(1500), "REJECT 가 상태 잠금 뒤에서 늦음: {first_after:?}");
            assert_eq!(kinds.iter().filter(|k| k.starts_with("reject:")).collect::<Vec<_>>(), vec!["reject:handshake_timeout"], "{kinds:?}");
            assert_eq!(kinds.iter().filter(|k| *k == "accept_aborted:handshake_timeout").count(), 1, "accept 뒤 accept_aborted 1줄: {kinds:?}");
            assert!(!kinds.iter().any(|k| k.starts_with("disconnect:") || k == "seatkeep_exit:controller_lost"), "조종자가 걸렸다: alive={alive} {kinds:?}");
        }

        /// ② 조종자가 REJECT 를 받자마자 끊는 경우: 늦게 끝난 두 번째 확인은 실패하지만(상대 없음) 두 번째 거절 줄을 남기지 않는다.
        #[cfg(target_os = "macos")]
        #[test]
        fn handshake_timeout_then_hangup_leaves_one_reject() {
            let (rej, kinds, alive) = slow_handshake("hs-timeout-drop", false);
            assert_eq!(rej.as_deref(), Some("handshake_timeout"), "기록 {kinds:?}");
            assert_eq!(kinds.iter().filter(|k| k.starts_with("reject:")).collect::<Vec<_>>(), vec!["reject:handshake_timeout"], "거절 기록 1줄: {kinds:?}");
            assert!(!kinds.iter().any(|k| k.starts_with("accept:") || k.starts_with("disconnect:") || k == "seatkeep_exit:controller_lost"), "alive={alive} {kinds:?}");
        }
    }
}
