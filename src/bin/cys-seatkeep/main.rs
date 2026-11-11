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
//!        [--requirement <코드서명 요구사항>] [--seats N] [--tail-bytes N] -- <명령> [인자…]`
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
    use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering};
    use std::sync::mpsc::{channel, sync_channel, Receiver, Sender, SyncSender};
    use std::sync::{Arc, Mutex, MutexGuard};
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
    const ALL_SEATS: u32 = u32::MAX;

    struct Args {
        dir: PathBuf,
        id: String,
        controller_exe: PathBuf,
        lock: PathBuf,
        requirement: Option<String>,
        seats: u32,
        tail_bytes: usize,
        cmd: Vec<String>,
    }

    fn parse_args() -> Result<Args, String> {
        let mut it = std::env::args().skip(1);
        let (mut dir, mut id, mut exe, mut lock, mut req) = (None, None, None, None, None);
        let (mut seats, mut tail_bytes) = (1u32, DEFAULT_TAIL);
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
        Ok(Args {
            dir: dir.ok_or("--dir 필요")?,
            id,
            controller_exe: exe.ok_or("--controller-exe 필요")?,
            lock: lock.ok_or("--lock 필요")?,
            requirement: req,
            seats,
            tail_bytes,
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
        fn log(&self, mut v: Value) -> std::io::Result<()> {
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
    fn send_ctl(st: &mut State, frame: Vec<u8>) {
        let Some(c) = st.controller.as_mut() else { return };
        c.queued.fetch_add(frame.len(), Ordering::SeqCst);
        // 실패 = 쓰기 스레드가 이미 끝났다(소켓 오류·멈춤 기한) — serve 가 곧 끊김을 정리한다.
        let _ = c.tx.send(frame);
    }

    /// 실시간 출력 — 밀린 바이트가 상한을 넘거나 이 좌석이 이미 밀려 있으면 큐에 넣지 않고 「밀림」으로 둔다
    /// (데이터는 꼬리에 있다 · 쓰기 스레드가 큐를 비우면 catch_up 이 그 오프셋부터 보낸다).
    fn send_output(keep: &Keep, st: &mut State, i: usize, offset: u64, bytes: &[u8]) {
        let Some(c) = st.controller.as_mut() else { return };
        if c.behind[i].is_some() {
            return;
        }
        if c.queued.load(Ordering::SeqCst) + bytes.len() > OUT_QUEUE_BYTES {
            c.behind[i] = Some(offset);
            c.behind_flag.store(true, Ordering::SeqCst);
            return;
        }
        send_ctl(st, proto::frame(proto::OUTPUT, keep.seats[i].id, &proto::output_payload(offset, bytes)));
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
            c.queued.fetch_add(f.len(), Ordering::SeqCst);
            let _ = c.tx.send(f);
        }
    }

    /// 세대가 같은 조종자에게만 보낸다(옛 조종자의 요청에 대한 답이 새 조종자에게 가지 않게).
    fn send_gen(st: &mut State, gen: u64, frame: Vec<u8>) {
        if st.controller.as_ref().map(|c| c.gen) == Some(gen) {
            send_ctl(st, frame);
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
        let args = match parse_args() {
            Ok(a) => a,
            Err(e) => {
                warn!("cys-seatkeep: {e}");
                return 2;
            }
        };
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
        for i in 0..args.seats {
            let pair = match native_pty_system().openpty(PtySize { rows: 35, cols: 120, pixel_width: 0, pixel_height: 0 }) {
                Ok(p) => p,
                Err(e) => {
                    warn!("cys-seatkeep: openpty: {e}");
                    return 5;
                }
            };
            let mut cb = CommandBuilder::new(&args.cmd[0]);
            cb.args(&args.cmd[1..]);
            if let Ok(cwd) = std::env::current_dir() {
                cb.cwd(cwd);
            }
            cb.env("CYS_SEATKEEP_SEAT", i.to_string());
            let child = match pair.slave.spawn_command(cb) {
                Ok(c) => c,
                Err(e) => {
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
            _id_lock: id_lock,
        });

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

        // 시험 전용 지연(A14① — 기동~확정 사이 창을 넓힌다). 제품 경로에는 이 변수가 없다.
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

    fn read_loop(keep: Arc<Keep>, i: usize, mut r: Box<dyn Read + Send>) {
        let mut buf = [0u8; 16 * 1024];
        loop {
            let n = match r.read(&mut buf) {
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
            send_ctl(st, proto::json_frame(proto::EXITED, keep.seats[i].id, &e));
            if let Some(c) = st.controller.as_mut() {
                c.exited_sent[i] = true;
            }
        }
    }

    fn wait_loop(keep: Arc<Keep>, i: usize, mut child: Box<dyn Child + Send + Sync>) {
        let pid = keep.seats[i].child_pid;
        // ① 끝남만 본다(회수 안 함). ② 신호 금지 표시를 잠금 안에서 세운다. ③ 그 뒤에야 회수한다.
        // SIGNAL·RELEASE 는 같은 잠금 안에서 이 표시를 보고 killpg 하므로, 회수된(재사용될 수 있는) pid 를 치지 않는다(codex 1R #3).
        if !wait_exit_nowait(pid) {
            warn!("cys-seatkeep: waitid({pid}) 실패: {} — 회수 경로로 넘어간다", std::io::Error::last_os_error());
        }
        lock_st(&keep).out[i].reaped = true;
        let status = child.wait();
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
            send_gen(&mut st, job.gen, proto::frame(proto::INPUT_ACK, keep.seats[i].id, &proto::input_ack_payload(job.id, false)));
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
        let done = Arc::new(AtomicBool::new(false));
        if let Ok(s2) = s.try_clone() {
            let d = Arc::clone(&done);
            std::thread::spawn(move || {
                std::thread::sleep(HELLO_TIMEOUT);
                if !d.load(Ordering::SeqCst) {
                    let _ = s2.shutdown(Shutdown::Both);
                }
            });
        }
        let peer = match peer::authorize(s.as_raw_fd(), &keep.policy) {
            Ok(p) => p,
            Err((reason, p)) => return reject(&keep, s, reason, p.as_ref()),
        };
        // 살아 있는 조종자가 있으면 거절(허더의 「마지막 접속자 탈취」 반대). HELLO 를 읽기 전에도 한 번 본다.
        if lock_st(&keep).controller.is_some() {
            return reject(&keep, s, "controller_alive", Some(&peer));
        }
        let _ = s.set_read_timeout(Some(HELLO_TIMEOUT));
        let hello: Value = match proto::read_frame_max(&mut s, HELLO_MAX) {
            Ok(Some((proto::HELLO, _, p))) => serde_json::from_slice(&p).unwrap_or(Value::Null),
            _ => return reject(&keep, s, "no_hello", Some(&peer)),
        };
        if hello["core"].as_u64() != Some(proto::CORE_VERSION as u64) {
            return reject(&keep, s, "core_mismatch", Some(&peer));
        }
        // 확인~HELLO 사이에 잠금을 놓았거나 신원이 바뀌었으면 받지 않는다 — 확인과 수락 사이 틈을 좁힌다(codex 1R #10).
        let peer = match peer::authorize(s.as_raw_fd(), &keep.policy) {
            // (pid · pidversion · 출생 시각) 셋 다 같아야 — 토큰은 「지금 그 pid 의 프로세스」라서(peer.rs ⚠) 처음 확인한
            // 그 프로세스가 아직 그 소켓의 마지막 사용자인지를 이 짝으로 본다. 출생 시각을 못 읽으면(None) 같다고 보지 않는다.
            Ok(p2) if p2.pid == peer.pid && p2.pidversion == peer.pidversion && p2.start_us.is_some() && p2.start_us == peer.start_us => p2,
            Ok(p2) => return reject(&keep, s, "peer_changed", Some(&p2)),
            Err((reason, p)) => return reject(&keep, s, reason, p.as_ref()),
        };
        let _ = s.set_read_timeout(None);
        let Ok(write_half) = s.try_clone() else {
            return reject(&keep, s, "socket_clone_failed", Some(&peer));
        };
        // 안 읽는 조종자: 소켓 쓰기가 이 기한을 넘으면 쓰기 스레드가 끝나며 연결을 닫는다(codex 1R #1).
        let _ = write_half.set_write_timeout(Some(CTL_WRITE_TIMEOUT));
        let rx;
        let gen;
        let queued = Arc::new(AtomicUsize::new(0));
        let behind_flag = Arc::new(AtomicBool::new(false));
        {
            let mut st = lock_st(&keep);
            if st.controller.is_some() {
                drop(st);
                return reject(&keep, s, "controller_alive", Some(&peer));
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
            if let Err(e) = keep.log(json!({"event": "accept", "gen": gen, "reason": reason, "peer": peer_json(&peer),
                                             "prev": prev, "replay": lost})) {
                // 줄은 써졌는데 fsync 만 실패했을 수 있다 — 받지 않았다는 줄을 덧붙인다(A16 셈 = accept − accept_aborted).
                let _ = keep.log(json!({"event": "accept_aborted", "gen": gen, "error": e.to_string()}));
                drop(st);
                warn!("cys-seatkeep: 교체 기록 실패 — 접속 거절: {e}");
                return reject(&keep, s, "ledger_write_failed", Some(&peer));
            }
            st.gen = gen;
            st.no_controller_since = None;
            // WELCOME + 좌석별 꼬리 재생(REPLAY_CHUNK 로 나눔) + 알린 종료 — 전부 먼저 모아 그 수만큼 칸을 더 잡는다
            // (소비 스레드 시작 전에 고정 칸에 넣다가 조용히 버리던 결함 · codex 1R #8 #9).
            let seats: Vec<Value> = keep
                .seats
                .iter()
                .zip(st.out.iter())
                .map(|(seat, o)| json!({"seat": seat.id, "child_pid": seat.child_pid, "total": o.total,
                                         "tail_start": o.tail_start(), "exit": o.exit}))
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
            // 재생은 크기와 무관하게 전부 넣는다(꼬리 상한 64MiB 안) — 그동안 새 출력은 밀림 경로로 간다.
            let (tx, r) = channel::<Vec<u8>>();
            for f in frames {
                queued.fetch_add(f.len(), Ordering::SeqCst);
                let _ = tx.send(f);
            }
            let n = st.out.len();
            st.controller = Some(Controller {
                gen,
                peer: peer.clone(),
                tx,
                queued: Arc::clone(&queued),
                behind: vec![None; n],
                behind_flag: Arc::clone(&behind_flag),
                exited_sent,
                evicted: false,
            });
            rx = r;
        }
        done.store(true, Ordering::SeqCst);
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
                    queued.fetch_sub(f.len(), Ordering::SeqCst);
                    // 큐가 반 아래로 비면 밀린 좌석을 따라잡는다.
                    if behind_flag.load(Ordering::SeqCst) && queued.load(Ordering::SeqCst) < OUT_QUEUE_BYTES / 2 {
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
            let _ = keep.log(json!({"event": "disconnect", "gen": gen, "peer": peer_json(&c.peer), "evicted": c.evicted}));
        }
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
                        send_gen(&mut st, gen, proto::frame(proto::INPUT_ACK, seat, &proto::input_ack_payload(id, true)));
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
                    // 회수 표시를 보는 것과 killpg 를 같은 잠금 안에서 — 회수된 자식(pid 재사용 대상)에는 보내지 않는다.
                    let st = lock_st(keep);
                    for i in targets(keep, seat) {
                        if !st.out[i].reaped {
                            unsafe { libc::killpg(keep.seats[i].child_pid, sig as i32) };
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
                    send_gen(&mut st, gen, proto::json_frame(proto::FOREGROUND_IS, seat, &json!({"pgid": pg})));
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
            let mut st = lock_st(&keep);
            if !st.exit_record_ok && st.out.iter().any(|o| o.exit.is_some() && !o.exit_acked) {
                keep.persist_exit_record(&mut st);
            }
            let all_exited = st.out.iter().all(|o| o.exit.is_some());
            let all_acked = st.out.iter().all(|o| o.exit_acked);
            let orphan_long = st.controller.is_none() && st.no_controller_since.map(|t| t.elapsed() >= EXIT_GRACE).unwrap_or(false);
            // 종료 기록을 EXIT_PERSIST_MAX 넘게 못 남기면(상태 폴더가 사라짐 등) stderr 에 기록을 남기고 rc 6 으로 끝낸다 —
            // 소켓도 사라졌을 수 있어 어떤 조종자도 확인해 줄 수 없는 영구 고아가 되지 않게(독립 검증 D9).
            let persist_given_up = !st.exit_record_ok && st.exit_record_fail_since.map(|t| t.elapsed() >= EXIT_PERSIST_MAX).unwrap_or(false);
            if all_exited && !all_acked && orphan_long && persist_given_up {
                let v: Vec<Value> = st.out.iter().enumerate().map(|(i, o)| json!({"seat": i, "exit": o.exit, "acked": o.exit_acked})).collect();
                drop(st);
                warn!("cys-seatkeep: 종료 기록을 {}초 동안 못 남김 — 여기 남기고 끝낸다: {}", EXIT_PERSIST_MAX.as_secs(), json!({"id": keep.args.id, "seats": v}));
                let _ = keep.log(json!({"event": "seatkeep_exit", "exit_record_kept": false, "exit_record_to_stderr": true}));
                let _ = std::fs::remove_file(&keep.paths.sock);
                return 6;
            }
            if all_exited && (all_acked || (orphan_long && st.exit_record_ok)) {
                // PTY 를 아직 쥔 프로세스가 있던 좌석 — 여기서 끝내면 그 뒤 출력은 받지 못한다(기록으로 남김).
                let open: Vec<usize> = st.out.iter().enumerate().filter(|(_, o)| !o.reader_done).map(|(i, _)| i).collect();
                drop(st);
                let _ = std::fs::remove_file(&keep.paths.sock);
                let _ = registry::write_atomic(&keep.paths.entry, &keep.entry("exited"));
                let _ = keep.log(json!({"event": "seatkeep_exit", "exit_record_kept": !all_acked, "output_open_seats": open}));
                return 0;
            }
        }
    }
}
