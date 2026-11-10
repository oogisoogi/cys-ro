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
    use std::io::{Read, Write};
    use std::os::unix::io::AsRawFd;
    use std::os::unix::net::{UnixListener, UnixStream};
    use std::path::PathBuf;
    use std::sync::mpsc::{sync_channel, SyncSender};
    use std::sync::{Arc, Mutex};
    use std::time::{Duration, Instant};

    const DEFAULT_TAIL: usize = 1 << 20;
    const INPUT_IDS_KEPT: usize = 4096;
    const HELLO_TIMEOUT: Duration = Duration::from_secs(3);
    /// 모든 자식이 끝났는데 조종자가 없을 때, 종료 기록을 남기고 나가기까지 기다리는 시간.
    const EXIT_GRACE: Duration = Duration::from_secs(2);
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

    struct Seat {
        id: u32,
        child_pid: i32,
        master: Mutex<Box<dyn MasterPty + Send>>,
        writer: Mutex<Box<dyn Write + Send>>,
    }

    struct SeatOut {
        tail: VecDeque<u8>,
        total: u64,
        exit: Option<Value>,
        exit_acked: bool,
        reader_done: bool,
    }

    impl SeatOut {
        fn tail_start(&self) -> u64 {
            self.total - self.tail.len() as u64
        }
    }

    struct Controller {
        gen: u64,
        peer: Peer,
        tx: SyncSender<Vec<u8>>,
    }

    struct State {
        out: Vec<SeatOut>,
        controller: Option<Controller>,
        gen: u64,
        last_peer: Option<(Peer, f64)>,
        no_controller_since: Option<Instant>,
        input_ids: (VecDeque<u64>, HashSet<u64>),
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
    }

    fn peer_json(p: &Peer) -> Value {
        json!({"pid": p.pid, "pidversion": p.pidversion, "euid": p.euid,
               "exe": p.exe.as_ref().map(|e| e.to_string_lossy().into_owned()),
               "start_us": registry::process_start_us(p.pid)})
    }

    impl Keep {
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

        fn write_exit_record(&self, st: &State) {
            let v: Vec<Value> = st
                .out
                .iter()
                .enumerate()
                .filter_map(|(i, o)| o.exit.clone().map(|e| json!({"seat": i, "exit": e, "acked": o.exit_acked})))
                .collect();
            if v.iter().all(|e| e["acked"] == json!(true)) && !v.is_empty() {
                let _ = std::fs::remove_file(&self.paths.exit);
                return;
            }
            let _ = registry::write_atomic(&self.paths.exit, &json!({"id": self.args.id, "seats": v}));
        }
    }

    pub fn run() -> i32 {
        let args = match parse_args() {
            Ok(a) => a,
            Err(e) => {
                eprintln!("cys-seatkeep: {e}");
                return 2;
            }
        };
        // 조종자(cysd)와 다른 세션 — 조종자가 죽어도 이 프로세스에 SIGHUP 이 오지 않는다.
        unsafe { libc::setsid() };
        let paths = Paths::new(&args.dir, &args.id);
        if let Err(e) = paths.ensure_dir() {
            eprintln!("cys-seatkeep: 상태 폴더: {e}");
            return 3;
        }
        let ledger = match Ledger::open(&paths.log) {
            Ok(l) => l,
            Err(e) => {
                eprintln!("cys-seatkeep: 교체 기록 열기 실패: {e}");
                return 3;
            }
        };
        let policy = Policy { controller_exe: args.controller_exe.clone(), requirement: args.requirement.clone(), lock: args.lock.clone() };
        let boot_id = registry::boot_id();
        let start_us = registry::process_start_us(std::process::id() as i32);

        // ① 준비 — 자식보다 먼저 등록부에 「준비」를 쓴다(조종자가 이 사이에 죽어도 새 조종자가 찾을 수 있게).
        let prepare = json!({"phase": "prepare", "id": args.id, "pid": std::process::id(), "start_us": start_us,
                             "boot_id": boot_id, "sock": paths.sock.to_string_lossy(), "core": proto::CORE_VERSION,
                             "at": registry::now_epoch()});
        if let Err(e) = registry::write_atomic(&paths.entry, &prepare) {
            eprintln!("cys-seatkeep: 등록부 준비 실패: {e}");
            return 3;
        }

        // ② 소켓 — 같은 id 의 산 seatkeep 이 있으면 물러난다. 죽은 소켓 파일만 지운다.
        if paths.sock.exists() {
            if UnixStream::connect(&paths.sock).is_ok() {
                eprintln!("cys-seatkeep: 같은 id 의 seatkeep 이 살아 있다");
                return 4;
            }
            let _ = std::fs::remove_file(&paths.sock);
        }
        let listener = match UnixListener::bind(&paths.sock) {
            Ok(l) => l,
            Err(e) => {
                eprintln!("cys-seatkeep: 소켓 열기 실패: {e}");
                return 3;
            }
        };
        use std::os::unix::fs::PermissionsExt;
        let _ = std::fs::set_permissions(&paths.sock, std::fs::Permissions::from_mode(0o600));

        // ③ 자식 기동
        let mut seats = Vec::new();
        let mut children: Vec<Box<dyn Child + Send + Sync>> = Vec::new();
        let mut readers = Vec::new();
        for i in 0..args.seats {
            let pair = match native_pty_system().openpty(PtySize { rows: 35, cols: 120, pixel_width: 0, pixel_height: 0 }) {
                Ok(p) => p,
                Err(e) => {
                    eprintln!("cys-seatkeep: openpty: {e}");
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
                    eprintln!("cys-seatkeep: spawn: {e}");
                    return 5;
                }
            };
            drop(pair.slave);
            let child_pid = child.process_id().unwrap_or(0) as i32;
            let reader = match pair.master.try_clone_reader() {
                Ok(r) => r,
                Err(e) => {
                    eprintln!("cys-seatkeep: reader: {e}");
                    return 5;
                }
            };
            let writer = match pair.master.take_writer() {
                Ok(w) => w,
                Err(e) => {
                    eprintln!("cys-seatkeep: writer: {e}");
                    return 5;
                }
            };
            seats.push(Seat { id: i, child_pid, master: Mutex::new(pair.master), writer: Mutex::new(writer) });
            children.push(child);
            readers.push(reader);
        }

        let keep = Arc::new(Keep {
            st: Mutex::new(State {
                out: (0..args.seats)
                    .map(|_| SeatOut { tail: VecDeque::new(), total: 0, exit: None, exit_acked: false, reader_done: false })
                    .collect(),
                controller: None,
                gen: 0,
                last_peer: None,
                no_controller_since: Some(Instant::now()),
                input_ids: (VecDeque::new(), HashSet::new()),
            }),
            ledger: Mutex::new(ledger),
            paths,
            policy,
            seats,
            boot_id,
            start_us,
            args,
        });

        for (i, r) in readers.into_iter().enumerate() {
            let k = Arc::clone(&keep);
            std::thread::spawn(move || read_loop(k, i, r));
        }
        for (i, c) in children.into_iter().enumerate() {
            let k = Arc::clone(&keep);
            std::thread::spawn(move || wait_loop(k, i, c));
        }

        // 시험 전용 지연(A14① — 기동~확정 사이 창을 넓힌다). 제품 경로에는 이 변수가 없다.
        if let Some(ms) = std::env::var("CYS_SEATKEEP_TEST_COMMIT_DELAY_MS").ok().and_then(|v| v.parse::<u64>().ok()) {
            std::thread::sleep(Duration::from_millis(ms));
        }
        // ④ 확정
        if let Err(e) = registry::write_atomic(&keep.paths.entry, &keep.entry("committed")) {
            eprintln!("cys-seatkeep: 등록부 확정 실패: {e}");
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
            let (offset, tx) = {
                let mut st = keep.st.lock().unwrap_or_else(|e| e.into_inner());
                let o = &mut st.out[i];
                let offset = o.total;
                o.total += n as u64;
                o.tail.extend(&buf[..n]);
                let cap = keep.args.tail_bytes;
                if o.tail.len() > cap {
                    let drop_n = o.tail.len() - cap;
                    o.tail.drain(..drop_n);
                }
                // 꼬리 갱신과 조종자 채널 복제를 같은 임계 구역에서 한다 — 붙기(attach)의 꼬리 재생과 겹치거나 빠지지 않는다.
                (offset, st.controller.as_ref().map(|c| c.tx.clone()))
            };
            if let Some(tx) = tx {
                let _ = tx.send(proto::frame(proto::OUTPUT, keep.seats[i].id, &proto::output_payload(offset, &buf[..n])));
            }
        }
        keep.st.lock().unwrap_or_else(|e| e.into_inner()).out[i].reader_done = true;
    }

    fn wait_loop(keep: Arc<Keep>, i: usize, mut child: Box<dyn Child + Send + Sync>) {
        let status = child.wait();
        let exit = match status {
            Ok(s) => json!({"code": s.exit_code(), "signal": s.signal(), "at": registry::now_epoch()}),
            Err(e) => json!({"error": e.to_string(), "at": registry::now_epoch()}),
        };
        // 마지막 출력이 읽히도록 잠깐 기다린다(최대 300ms).
        let until = Instant::now() + Duration::from_millis(300);
        while Instant::now() < until {
            if keep.st.lock().unwrap_or_else(|e| e.into_inner()).out[i].reader_done {
                break;
            }
            std::thread::sleep(Duration::from_millis(10));
        }
        let tx = {
            let mut st = keep.st.lock().unwrap_or_else(|e| e.into_inner());
            st.out[i].exit = Some(exit.clone());
            keep.write_exit_record(&st);
            st.controller.as_ref().map(|c| c.tx.clone())
        };
        let _ = keep.log(json!({"event": "child_exit", "seat": i, "exit": exit}));
        if let Some(tx) = tx {
            let _ = tx.send(proto::json_frame(proto::EXITED, keep.seats[i].id, &exit));
        }
    }

    fn reject(keep: &Keep, mut s: UnixStream, reason: &str, peer: Option<&Peer>) {
        let _ = keep.log(json!({"event": "reject", "reason": reason, "peer": peer.map(peer_json)}));
        let _ = proto::write_all(&mut s, &proto::json_frame(proto::REJECT, ALL_SEATS, &json!({"reason": reason})));
        let _ = s.shutdown(std::net::Shutdown::Both);
    }

    fn accept_loop(keep: Arc<Keep>, listener: UnixListener) {
        for conn in listener.incoming() {
            let Ok(s) = conn else { continue };
            let k = Arc::clone(&keep);
            // 확인은 접속마다 별 스레드 — 느린 접속자가 다른 접속을 막지 않는다. 조종자 자리는 아래 임계 구역이 하나로 지킨다.
            std::thread::spawn(move || handshake(k, s));
        }
    }

    fn handshake(keep: Arc<Keep>, mut s: UnixStream) {
        let peer = match peer::authorize(s.as_raw_fd(), &keep.policy) {
            Ok(p) => p,
            Err((reason, p)) => return reject(&keep, s, reason, p.as_ref()),
        };
        // 살아 있는 조종자가 있으면 거절(허더의 「마지막 접속자 탈취」 반대). HELLO 를 읽기 전에도 한 번 본다.
        if keep.st.lock().unwrap_or_else(|e| e.into_inner()).controller.is_some() {
            return reject(&keep, s, "controller_alive", Some(&peer));
        }
        let _ = s.set_read_timeout(Some(HELLO_TIMEOUT));
        let hello: Value = match proto::read_frame(&mut s) {
            Ok(Some((proto::HELLO, _, p))) => serde_json::from_slice(&p).unwrap_or(Value::Null),
            _ => return reject(&keep, s, "no_hello", Some(&peer)),
        };
        if hello["core"].as_u64() != Some(proto::CORE_VERSION as u64) {
            return reject(&keep, s, "core_mismatch", Some(&peer));
        }
        let _ = s.set_read_timeout(None);
        let Ok(write_half) = s.try_clone() else { return };
        let (tx, rx) = sync_channel::<Vec<u8>>(256);
        let gen;
        {
            let mut st = keep.st.lock().unwrap_or_else(|e| e.into_inner());
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
                drop(st);
                eprintln!("cys-seatkeep: 교체 기록 실패 — 접속 거절: {e}");
                return reject(&keep, s, "ledger_write_failed", Some(&peer));
            }
            st.gen = gen;
            st.no_controller_since = None;
            // WELCOME + 좌석별 꼬리 재생을 같은 임계 구역에서 채널에 넣는다(read_loop 주석 참조).
            let seats: Vec<Value> = keep
                .seats
                .iter()
                .zip(st.out.iter())
                .map(|(seat, o)| json!({"seat": seat.id, "child_pid": seat.child_pid, "total": o.total,
                                         "tail_start": o.tail_start(), "exit": o.exit}))
                .collect();
            let welcome = json!({"core": proto::CORE_VERSION, "gen": gen, "pid": std::process::id(),
                                 "start_us": keep.start_us, "boot_id": keep.boot_id, "seats": seats});
            let _ = tx.try_send(proto::json_frame(proto::WELCOME, ALL_SEATS, &welcome));
            for (i, o) in st.out.iter().enumerate() {
                let from = resume[i.to_string()].as_u64().unwrap_or(0).max(o.tail_start()).min(o.total);
                let skip = (from - o.tail_start()) as usize;
                let bytes: Vec<u8> = o.tail.iter().skip(skip).copied().collect();
                if !bytes.is_empty() {
                    let _ = tx.try_send(proto::frame(proto::OUTPUT, keep.seats[i].id, &proto::output_payload(from, &bytes)));
                }
                if let Some(e) = &o.exit {
                    let _ = tx.try_send(proto::json_frame(proto::EXITED, keep.seats[i].id, e));
                }
            }
            st.controller = Some(Controller { gen, peer: peer.clone(), tx: tx.clone() });
        }
        drop(tx);
        {
            let mut w = write_half;
            std::thread::spawn(move || {
                for f in rx {
                    if proto::write_all(&mut w, &f).is_err() {
                        break;
                    }
                }
                let _ = w.shutdown(std::net::Shutdown::Both);
            });
        }
        serve(&keep, s, gen);
        let mut st = keep.st.lock().unwrap_or_else(|e| e.into_inner());
        if st.controller.as_ref().map(|c| c.gen) == Some(gen) {
            let c = st.controller.take().unwrap();
            let now = registry::now_epoch();
            st.last_peer = Some((c.peer.clone(), now));
            st.no_controller_since = Some(Instant::now());
            drop(st);
            let _ = keep.log(json!({"event": "disconnect", "gen": gen, "peer": peer_json(&c.peer)}));
        }
    }

    fn reply(keep: &Keep, gen: u64, frame: Vec<u8>) {
        let tx = {
            let st = keep.st.lock().unwrap_or_else(|e| e.into_inner());
            st.controller.as_ref().filter(|c| c.gen == gen).map(|c| c.tx.clone())
        };
        if let Some(tx) = tx {
            let _ = tx.send(frame);
        }
    }

    fn seat_index(keep: &Keep, seat: u32) -> Option<usize> {
        keep.seats.iter().position(|s| s.id == seat)
    }

    fn alive(keep: &Keep, i: usize) -> bool {
        keep.st.lock().unwrap_or_else(|e| e.into_inner()).out[i].exit.is_none()
    }

    fn serve(keep: &Keep, mut s: UnixStream, gen: u64) {
        loop {
            let (kind, seat, payload) = match proto::read_frame(&mut s) {
                Ok(Some(f)) => f,
                _ => return,
            };
            // 세대 울타리: 이 연결이 더 이상 조종자가 아니면 어떤 명령도 집행하지 않는다.
            if keep.st.lock().unwrap_or_else(|e| e.into_inner()).controller.as_ref().map(|c| c.gen) != Some(gen) {
                return;
            }
            match kind {
                proto::INPUT => {
                    let Some(i) = seat_index(keep, seat) else { continue };
                    let Some((id, bytes)) = proto::split_input(&payload) else { continue };
                    let dup = id != 0 && keep.st.lock().unwrap_or_else(|e| e.into_inner()).input_ids.1.contains(&id);
                    if !dup {
                        if !alive(keep, i) {
                            continue;
                        }
                        let ok = {
                            let mut w = keep.seats[i].writer.lock().unwrap_or_else(|e| e.into_inner());
                            w.write_all(bytes).and_then(|_| w.flush()).is_ok()
                        };
                        if !ok {
                            continue; // 수신 확인 없음 = 조종자는 「모름」으로 다룬다(자동 재전송 금지)
                        }
                        if id != 0 {
                            let mut st = keep.st.lock().unwrap_or_else(|e| e.into_inner());
                            let ids = &mut st.input_ids;
                            if ids.1.insert(id) {
                                ids.0.push_back(id);
                                if ids.0.len() > INPUT_IDS_KEPT {
                                    if let Some(old) = ids.0.pop_front() {
                                        ids.1.remove(&old);
                                    }
                                }
                            }
                        }
                    }
                    reply(keep, gen, proto::frame(proto::INPUT_ACK, seat, &proto::input_ack_payload(id, dup)));
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
                    for i in targets(keep, seat) {
                        // 회수된 자식에는 보내지 않는다(pid 재사용 대상 오타격 방지).
                        if alive(keep, i) {
                            unsafe { libc::killpg(keep.seats[i].child_pid, sig as i32) };
                        }
                    }
                }
                proto::RELEASE => {
                    let _ = keep.log(json!({"event": "release", "gen": gen, "seat": seat}));
                    for i in targets(keep, seat) {
                        if alive(keep, i) {
                            unsafe { libc::killpg(keep.seats[i].child_pid, libc::SIGHUP) };
                        }
                    }
                }
                proto::FOREGROUND => {
                    let Some(i) = seat_index(keep, seat) else { continue };
                    let pg = keep.seats[i].master.lock().unwrap_or_else(|e| e.into_inner()).process_group_leader();
                    reply(keep, gen, proto::json_frame(proto::FOREGROUND_IS, seat, &json!({"pgid": pg})));
                }
                proto::EXIT_ACK => {
                    let mut st = keep.st.lock().unwrap_or_else(|e| e.into_inner());
                    for i in targets(keep, seat) {
                        if st.out[i].exit.is_some() {
                            st.out[i].exit_acked = true;
                        }
                    }
                    keep.write_exit_record(&st);
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

    /// 모든 자식이 끝나고 ⓐ 조종자가 전부 받았다고 답했거나 ⓑ 조종자 없이 유예가 지나면 끝낸다.
    /// ⓑ 의 경우 `<id>.exit` 를 남긴다(새 조종자가 소비).
    fn supervise(keep: Arc<Keep>) -> i32 {
        loop {
            std::thread::sleep(Duration::from_millis(100));
            let done = {
                let st = keep.st.lock().unwrap_or_else(|e| e.into_inner());
                let all_exited = st.out.iter().all(|o| o.exit.is_some());
                let all_acked = st.out.iter().all(|o| o.exit_acked);
                let orphan_long = st.controller.is_none() && st.no_controller_since.map(|t| t.elapsed() >= EXIT_GRACE).unwrap_or(false);
                all_exited && (all_acked || orphan_long)
            };
            if done {
                let acked = keep.st.lock().unwrap_or_else(|e| e.into_inner()).out.iter().all(|o| o.exit_acked);
                let _ = std::fs::remove_file(&keep.paths.sock);
                let _ = registry::write_atomic(&keep.paths.entry, &keep.entry("exited"));
                let _ = keep.log(json!({"event": "seatkeep_exit", "exit_record_kept": !acked}));
                return 0;
            }
        }
    }
}
