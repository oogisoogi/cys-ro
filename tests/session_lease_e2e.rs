//! TICKET=cysr-seatkeep-t1 — 「한 대화에 작성자 하나」 실 `cys` · 실 `cysd` · 가짜 claude · 격리 HOME · 격리 소켓.
//! 라이브 데몬·`~/.cys`·`~/.claude` 무접촉(환경 전부 비우고 HOME·CYS_SOCKET·TMPDIR 을 상자 안으로).
//! 프로세스 종료 = 이 시험이 띄운 상자 안 가짜 claude(실행 파일 경로가 상자 안인 것)의 pid 만.
#![cfg(unix)]

use serde_json::{json, Value};
use std::io::{Read, Write};
use std::os::unix::net::UnixStream;
use std::path::PathBuf;
use std::process::{Command, Output, Stdio};
use std::time::{Duration, Instant};

const CYS: &str = env!("CARGO_BIN_EXE_cys");
const FAKE_CLAUDE: &str = concat!(env!("CARGO_MANIFEST_DIR"), "/tests/fixtures/fake_claude.c");
const ROLE: &str = "tw1";

struct Box_ {
    base: PathBuf,
    sock: PathBuf,
    path: String,
    sid: String,
    role: String,
    /// 상자 폴더를 지울 주인인가(같은 HOME 을 나눠 쓰는 두 번째 데몬 = 아님).
    owns_base: bool,
    /// 가짜 claude 가 등록을 하지 않는다(`FAKE_NO_REG` · 데몬 env 로 좌석에 전달 · 훅 부재 좌석).
    no_reg: bool,
    /// 가짜 claude 가 이 파일이 생길 때까지 등록을 미룬다(`FAKE_REG_GATE` · 정상 기동 직후 등록 전 창 · r5b).
    reg_gate: Option<PathBuf>,
    /// 가짜 claude 가 이 파일이 생기면 좌석 안 `claude -p` 헬퍼를 띄워 새 대화로 등록한다(`FAKE_HELPER_GATE` · 독립 검증 V1).
    helper_gate: Option<PathBuf>,
    /// 이 상자가 띄운 데몬 pid 들(내림 대조 · master#4199fa4f).
    daemons: std::cell::RefCell<Vec<i32>>,
    /// 이 시험이 마지막에 손으로 쓴 저장 핀(파일 본문 · 그때의 live) — [`Box_::write_saved_pin`] 의 「덜 끝난 영속 없음」 판정 ⑵.
    pin_written: std::cell::RefCell<Option<(String, Vec<(String, Option<String>)>)>>,
    /// 좌석 셸(`CYS_SHELL` · 데몬 env 로 전달) — None = 데몬 기본(TICKET=cysr-1118-seat ② 줄 편집 없는 셸 재현).
    seat_shell: Option<PathBuf>,
}

impl Box_ {
    /// 상자 + 가짜 claude + 저장 토폴로지(역할 1개 · 대화 `sid` · 그 jsonl 실재).
    fn new(tag: &str) -> Self {
        warn_old_orphans();
        let base = PathBuf::from(format!("/tmp/cys-sle-{}-{tag}", std::process::id()));
        let _ = std::fs::remove_dir_all(&base);
        std::fs::create_dir_all(base.join("home")).unwrap();
        let base = base.canonicalize().unwrap();
        for d in ["run", "sbin", "proj"] {
            std::fs::create_dir_all(base.join(d)).unwrap();
        }
        assert!(Command::new("/usr/bin/cc").args(["-w", "-o"]).arg(base.join("sbin/claude")).arg(FAKE_CLAUDE).status().unwrap().success());
        let path = format!(
            "{}:{}:{}",
            base.join("sbin").display(),
            PathBuf::from(CYS).parent().unwrap().display(),
            std::env::var("PATH").unwrap_or_default()
        );
        let sid = format!("5e55{:04x}-0000-4000-8000-{:012x}", std::process::id() & 0xffff, tag.bytes().fold(7919u64, |a, b| a.wrapping_mul(131).wrapping_add(b as u64)) & 0xffff_ffff_ffff); // 상자마다 다른 대화(병렬 시험끼리 안 겹침)
        let proj = base.join("proj");
        let cfg = base.join("home/.claude");
        let slug: String = proj.to_string_lossy().chars().map(|c| if c.is_ascii_alphanumeric() { c } else { '-' }).collect();
        let pd = cfg.join("projects").join(slug);
        std::fs::create_dir_all(&pd).unwrap();
        write_saved_jsonl(&pd.join(format!("{sid}.jsonl")), &sid);
        let entries = vec![json!({"role": ROLE, "agent": "claude", "cwd": proj, "session_id": sid,
                                  "claude_config_dir": cfg})];
        std::fs::write(base.join("run/topology.json"), json!({"entries": entries}).to_string()).unwrap();
        Self { sock: base.join("run/cysd.sock"), base, path, sid, role: ROLE.into(), owns_base: true, no_reg: false, reg_gate: None, helper_gate: None, daemons: Default::default(), pin_written: Default::default(), seat_shell: None }
    }

    /// 같은 상자(같은 HOME = 같은 임대 폴더 · 같은 프로젝트 폴더)의 **두 번째 데몬**(소켓·상태 폴더 `run2`).
    /// 저장 토폴로지 = 역할 `role` 이 대화 `sid`(없으면 새 대화 + jsonl)를 잇는다.
    fn second(&self, role: &str, sid: Option<&str>) -> Self {
        let run = self.base.join("run2");
        std::fs::create_dir_all(&run).unwrap();
        let sid = sid.map(String::from).unwrap_or_else(|| format!("5e56{}", &self.sid[4..]));
        let proj = self.base.join("proj");
        let cfg = self.base.join("home/.claude");
        let slug: String = proj.to_string_lossy().chars().map(|c| if c.is_ascii_alphanumeric() { c } else { '-' }).collect();
        let jsonl = cfg.join("projects").join(slug).join(format!("{sid}.jsonl"));
        if !jsonl.exists() {
            write_saved_jsonl(&jsonl, &sid);
        }
        let entries = vec![json!({"role": role, "agent": "claude", "cwd": proj, "session_id": sid, "claude_config_dir": cfg})];
        std::fs::write(run.join("topology.json"), json!({"entries": entries}).to_string()).unwrap();
        Self { sock: run.join("cysd.sock"), base: self.base.clone(), path: self.path.clone(), sid, role: role.into(), owns_base: false, no_reg: self.no_reg, reg_gate: self.reg_gate.clone(), helper_gate: self.helper_gate.clone(), daemons: Default::default(), pin_written: Default::default(), seat_shell: self.seat_shell.clone() }
    }

    /// 이 대화의 임대 파일(상자 HOME 의 임대 폴더 · 키 = sha256("v1\0" + 소문자 id)).
    fn lease_file(&self) -> PathBuf {
        use sha2::{Digest, Sha256};
        let mut h = Sha256::new();
        h.update(b"v1\0");
        h.update(self.sid.trim().to_ascii_lowercase().as_bytes());
        let hex: String = h.finalize().iter().map(|b| format!("{b:02x}")).collect();
        self.base.join("home/.local/state/cys/session-leases").join(format!("{hex}.lease"))
    }

    /// 저장 핀(topology.json)을 손으로 쓴다 — **데몬의 덜 끝난 영속이 없을 때만**(TICKET=cysr-1116-leasee2e-1121 2차 · C9 run 44868392427 IR).
    /// 데몬은 역할 쥠·핀 바뀜마다 topology.json 을 다시 쓴다(`persist_topology` · 메모리 반영 → 파일 쓰기 순). 시험이 메모리 쪽 변화
    /// (topology live)를 보자마자 S 핀을 쓰면 아직 덜 끝난 그 영속이 뒤에 착지해 S 를 지운다 → `--resume-saved` 가 저장 핀 = W 의 대화로 읽고
    /// 「다른 좌석이 저장 대화를 잇고 있다」 rc 93(CI 관측 · 로컬 = 등록 관측 주기 1ms 로 재현).
    /// 덜 끝난 영속 없음 = ⑴ 파일이 live 역할마다 같은 session_id(데몬이 마지막으로 쓴 것이 지금 메모리) · 또는 ⑵ 파일이 이 시험이 마지막에 쓴
    /// 그대로이고 그 뒤 live 가 안 바뀜(데몬이 다시 쓸 계기 없음 · RN 반복처럼 연달아 쓰는 자리).
    fn write_saved_pin(&self, topo: Value) {
        let file = self.sock.parent().unwrap().join("topology.json");
        let live_now = || -> Vec<(String, Option<String>)> {
            self.rpc("system.topology").ok().and_then(|v| v["live"].as_array().cloned()).unwrap_or_default()
                .iter().filter_map(|e| Some((e["role"].as_str()?.to_string(), e["session_id"].as_str().map(String::from)))).collect()
        };
        let t = Instant::now();
        let mut last = String::new();
        loop {
            let live = live_now();
            let raw = std::fs::read_to_string(&file).unwrap_or_default();
            let disk: Value = serde_json::from_str(&raw).unwrap_or(Value::Null);
            let on_disk = |r: &str| disk["entries"].as_array().into_iter().flatten().find(|e| e["role"].as_str() == Some(r)).map(|e| e["session_id"].as_str().map(String::from));
            let caught_up = live.iter().all(|(r, sid)| on_disk(r) == Some(sid.clone()));
            let untouched = self.pin_written.borrow().as_ref().is_some_and(|(c, l)| *c == raw && *l == live);
            if caught_up || untouched {
                break;
            }
            last = format!("live={live:?} · 파일={}", raw.chars().take(600).collect::<String>());
            assert!(t.elapsed() < Duration::from_secs(20), "데몬 영속(topology.json)이 메모리를 따라잡지 않음(20s): {last}");
            std::thread::sleep(Duration::from_millis(50));
        }
        let body = topo.to_string();
        std::fs::write(&file, &body).unwrap();
        *self.pin_written.borrow_mut() = Some((body, live_now()));
    }

    fn cmd(&self, args: &[&str]) -> Command {
        let mut c = Command::new(CYS);
        c.args(args)
            .env_clear()
            .env("PATH", &self.path)
            .env("HOME", self.base.join("home"))
            .env("TMPDIR", &self.base)
            .env("CYS_SOCKET", &self.sock)
            .env("CYS_NO_AUTORESTORE", "1")
            .stdin(Stdio::null());
        // 대조군: 노브를 상자 안 cys·cysd 까지 넘긴다(env_clear 뒤라 명시).
        if let Ok(v) = std::env::var("CYS_SESSION_LEASE") {
            c.env("CYS_SESSION_LEASE", v);
        }
        if self.no_reg {
            c.env("FAKE_NO_REG", "1");
        }
        if let Some(g) = &self.reg_gate {
            c.env("FAKE_REG_GATE", g);
        }
        if let Some(g) = &self.helper_gate {
            c.env("FAKE_HELPER_GATE", g);
        }
        if let Some(sh) = &self.seat_shell {
            c.env("CYS_SHELL", sh);
        }
        // 가짜 claude 의 등록 명령 = 이 시험이 지은 cys(절대 경로) — 좌석 셸은 로그인 셸이라 PATH 가 재정렬돼 맨 `cys` 가
        //   설치본(/usr/local/bin/cys · T1 없음)으로 풀렸다(skt1 실측: 등록이 T1 follow 를 한 번도 안 거침).
        c.env("FAKE_CYS", CYS);
        c
    }

    fn cys(&self, args: &[&str]) -> Output {
        self.cmd(args).output().unwrap()
    }

    fn rpc(&self, method: &str) -> Result<Value, String> {
        self.rpcp(method, json!({}))
    }

    fn rpcp(&self, method: &str, params: Value) -> Result<Value, String> {
        let mut s = UnixStream::connect(&self.sock).map_err(|e| e.to_string())?;
        s.set_read_timeout(Some(Duration::from_secs(10))).map_err(|e| e.to_string())?;
        let mut line = serde_json::to_vec(&json!({"id": 1, "method": method, "params": params})).unwrap();
        line.push(b'\n');
        s.write_all(&line).map_err(|e| e.to_string())?;
        let mut got = Vec::new();
        let mut buf = [0u8; 65536];
        while !got.ends_with(b"\n") {
            match s.read(&mut buf) {
                Ok(0) => break,
                Ok(n) => got.extend_from_slice(&buf[..n]),
                Err(e) => return Err(e.to_string()),
            }
        }
        let v: Value = serde_json::from_slice(&got).map_err(|e| e.to_string())?;
        Ok(v["result"].clone())
    }

    fn up(&self) {
        let o = self.cys(&["identify"]);
        let t = Instant::now();
        let dpid = loop {
            if let Some(p) = self.rpc("system.identify").ok().and_then(|v| v["daemon_pid"].as_u64()) {
                break p as i32;
            }
            assert!(t.elapsed() < Duration::from_secs(180), "identify: {}", String::from_utf8_lossy(&o.stderr));
            std::thread::sleep(Duration::from_millis(200));
        };
        self.arm_reaper(dpid);
    }

    /// 시험 프로세스가 어떻게 끝나든(성공·실패·중단·시한 초과 SIGKILL — Drop 이 안 도는 경우 포함) 이 상자의 데몬을 내린다(master#4199fa4f):
    /// 시험과 따로 사는 감시 셸이 시험 pid 가 사라지면 그 데몬 pid(출생 시각 같을 때만 · pid 재사용 방지)를 그룹째 TERM → 3초 뒤 KILL.
    fn arm_reaper(&self, dpid: i32) {
        let lstart = |p: i32| Command::new("/bin/ps").args(["-p", &p.to_string(), "-o", "lstart="]).output().map(|o| String::from_utf8_lossy(&o.stdout).trim().to_string()).unwrap_or_default();
        let born = lstart(dpid);
        if born.is_empty() {
            return;
        }
        let script = r#"while kill -0 "$1" 2>/dev/null; do sleep 1; done; [ "$(ps -p "$2" -o lstart= 2>/dev/null | sed 's/^ *//;s/ *$//')" = "$3" ] || exit 0; kill -TERM -"$2" 2>/dev/null; kill -TERM "$2" 2>/dev/null; sleep 3; kill -KILL -"$2" 2>/dev/null; kill -KILL "$2" 2>/dev/null"#;
        let _ = Command::new("/bin/sh")
            .args(["-c", script, "cys-sle-reaper", &std::process::id().to_string(), &dpid.to_string(), &born])
            .stdin(Stdio::null())
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .spawn();
        self.daemons.borrow_mut().push(dpid);
    }

    /// 이 상자 HOME 을 물려받은 남은 프로세스 전부(좌석 셸·대기 셸·늦게 뜬 데몬) — pid 로만 끈다(이름 일치 종료 아님 · `mine` = 환경 HOME 이 이 상자).
    fn kill_box_leftovers(&self) {
        let ps = Command::new("/bin/ps").args(["-axo", "pid="]).output().unwrap();
        let me = std::process::id() as i32;
        for p in String::from_utf8_lossy(&ps.stdout).lines().filter_map(|l| l.trim().parse::<i32>().ok()) {
            if p != me && self.mine(p) {
                unsafe { libc::kill(p, libc::SIGKILL) };
            }
        }
    }

    /// 상자 안 가짜 claude 전부(인자 무관).
    fn fakes(&self) -> Vec<i32> {
        let exe = self.base.join("sbin/claude");
        let ps = Command::new("/bin/ps").args(["-axo", "pid=,command="]).output().unwrap();
        String::from_utf8_lossy(&ps.stdout)
            .lines()
            .filter(|l| l.contains(&exe.to_string_lossy().to_string()) || l.split_whitespace().nth(1) == Some("claude"))
            .filter_map(|l| l.split_whitespace().next()?.parse().ok())
            .filter(|p| self.mine(*p))
            .collect()
    }

    /// 이 대화를 `--resume` 으로 쥔 상자 안 가짜 claude pid 들(실행 파일 = 상자의 sbin/claude 인 것만).
    fn writers(&self) -> Vec<i32> {
        let exe = self.base.join("sbin/claude");
        let ps = Command::new("/bin/ps").args(["-axo", "pid=,command="]).output().unwrap();
        String::from_utf8_lossy(&ps.stdout)
            .lines()
            .filter(|l| l.contains(&exe.to_string_lossy().to_string()) || l.split_whitespace().nth(1) == Some("claude"))
            .filter(|l| l.contains(&format!("--resume {}", self.sid)))
            .filter_map(|l| l.split_whitespace().next()?.parse().ok())
            .filter(|p| self.mine(*p))
            .collect()
    }

    /// 그 pid 의 환경 HOME 이 이 상자인가(남의 프로세스를 세지도 죽이지도 않는다).
    fn mine(&self, pid: i32) -> bool {
        let o = Command::new("/bin/ps").args(["-E", "-p", &pid.to_string(), "-o", "command="]).output().unwrap();
        String::from_utf8_lossy(&o.stdout).contains(&format!("HOME={}", self.base.join("home").display()))
    }

    /// 기다렸다가 작성자 수를 센다(기동이 끝날 시간).
    fn settle_writers(&self, secs: u64) -> Vec<i32> {
        let t = Instant::now();
        let mut last = self.writers();
        while t.elapsed() < Duration::from_secs(secs) {
            std::thread::sleep(Duration::from_millis(500));
            last = self.writers();
        }
        last
    }

    fn kill_writers(&self) {
        for p in self.fakes() {
            unsafe { libc::kill(p, libc::SIGTERM) };
        }
        let t = Instant::now();
        while !self.fakes().is_empty() && t.elapsed() < Duration::from_secs(10) {
            std::thread::sleep(Duration::from_millis(200));
        }
    }

    /// 작성자가 죽은 뒤 데몬이 그 좌석을 「빈 좌석」으로 볼 때까지(watchdog 틱 지연).
    fn wait_seat_empty(&self) {
        let t = Instant::now();
        while t.elapsed() < Duration::from_secs(20) {
            let topo = self.rpc("system.topology").unwrap_or(Value::Null);
            let seat = topo["live"].as_array().into_iter().flatten()
                .find(|e| e["role"].as_str() == Some(self.role.as_str())).and_then(|e| e["seat"].as_str().map(String::from));
            if seat.as_deref() == Some("empty") || seat.is_none() {
                return;
            }
            std::thread::sleep(Duration::from_millis(300));
        }
    }

    /// 이 역할의 살아 있는 좌석 id 들.
    fn role_seats(&self) -> Vec<u64> {
        let l = self.rpc("surface.list").unwrap_or(Value::Null);
        l["surfaces"].as_array().or_else(|| l.as_array()).into_iter().flatten()
            .filter(|s| s["role"].as_str().is_some_and(|r| r.starts_with(self.role.as_str())) && s["exited"].as_bool() != Some(true))
            .filter_map(|s| s["surface_id"].as_u64())
            .collect()
    }

    /// 판을 비운다 — 작성자를 끄고, 빈 셸이 된 그 역할 좌석을 데몬의 「빈 좌석 회수」(only_if_empty · 묘비 0)로 닫는다.
    fn reset(&self) {
        self.kill_writers();
        let mut last = String::new();
        let t = Instant::now();
        while t.elapsed() < Duration::from_secs(20) {
            let seats = self.role_seats();
            if seats.is_empty() {
                return;
            }
            for sid in seats {
                let r = self.rpcp("surface.close", json!({"surface_id": sid, "cause": "reap", "only_if_empty": true}));
                last = format!("{r:?}");
            }
            std::thread::sleep(Duration::from_millis(500));
        }
        let l = self.rpc("surface.list").unwrap_or(Value::Null);
        panic!("좌석 정리 실패: {:?} · 마지막 응답 {last} · 목록 {}", self.role_seats(), l.to_string().chars().take(1500).collect::<String>());
    }

    fn fake_log(&self) -> String {
        std::fs::read_to_string(self.base.join("home/fake.log")).unwrap_or_default()
    }

    fn down(&self) {
        // 응답하는 데몬 + up 때 적어 둔 데몬(응답이 없어도) — 내려가지 않으면 KILL(master#4199fa4f).
        let mut pids = self.daemons.borrow().clone();
        if let Some(p) = self.rpc("system.identify").ok().and_then(|v| v["daemon_pid"].as_u64()) {
            pids.push(p as i32);
        }
        pids.sort();
        pids.dedup();
        for p in &pids {
            unsafe { libc::kill(*p, libc::SIGTERM) };
        }
        let t = Instant::now();
        while (UnixStream::connect(&self.sock).is_ok() || pids.iter().any(|p| unsafe { libc::kill(*p, 0) } == 0 && self.mine(*p)))
            && t.elapsed() < Duration::from_secs(10)
        {
            std::thread::sleep(Duration::from_millis(100));
        }
        for p in &pids {
            if unsafe { libc::kill(*p, 0) } == 0 && self.mine(*p) {
                unsafe { libc::kill(*p, libc::SIGKILL) };
            }
        }
    }
}

impl Drop for Box_ {
    fn drop(&mut self) {
        if !self.owns_base {
            self.down();
            return;
        }
        self.kill_writers();
        self.down();
        self.kill_box_leftovers();
        for _ in 0..30 {
            let _ = std::fs::remove_dir_all(&self.base);
            std::thread::sleep(Duration::from_millis(100));
            if !self.base.exists() {
                break;
            }
        }
    }
}

/// 저장 대화의 jsonl — 지난 회차에 쓴 파일답게 mtime 을 1시간 전으로 둔다(TICKET=cysr-1116-leasee2e-1121).
/// 데몬 usage 수집기의 휴리스틱 발견(`discover_claude_transcript`)은 좌석 생성 5초 전 이후 mtime 의 jsonl 중 최신을 그 좌석의 대화로
/// 1회 핀한다. 방금 쓴 S 는 그 창 안이라, 새 좌석 W 의 가짜 claude 가 자기 대화 T 의 파일을 쓰기 **전**에 수집기가 돌면(느린 CI 러너의
/// 로그인 셸 프로필) W 가 S 로 핀됐다 → topology live 에 「W = S」 → `--resume-saved` 가 「다른 좌석이 저장 대화를 잇고 있다」(93 · 임대 0)
/// · rv 전제(등록 전 핀 없음)가 깨졌다(CI 44850374411). 실제 저장 대화는 작성자가 끝난 옛 파일이다 — 시험 상자도 그 모양으로 세운다.
fn write_saved_jsonl(p: &std::path::Path, sid: &str) {
    std::fs::write(p, format!("{{\"type\":\"user\",\"sessionId\":\"{sid}\"}}\n")).unwrap();
    let old = std::time::SystemTime::now() - Duration::from_secs(3600);
    std::fs::File::options().write(true).open(p).unwrap().set_modified(old).unwrap();
}

/// 시험 시작 때 옛 회차가 남긴 상자 프로세스(환경 HOME = /tmp/cys-sle-<다른 pid>-…)가 있으면 경고만(끄지 않음 · 남의 회차일 수 있다 · master#4199fa4f).
fn warn_old_orphans() {
    static ONCE: std::sync::Once = std::sync::Once::new();
    ONCE.call_once(|| {
        let me = format!("cys-sle-{}-", std::process::id());
        let Ok(o) = Command::new("/bin/ps").args(["-E", "-axo", "pid=,ppid=,command="]).output() else { return };
        let old: Vec<String> = String::from_utf8_lossy(&o.stdout)
            .lines()
            .filter(|l| l.contains("HOME=/private/tmp/cys-sle-") || l.contains("HOME=/tmp/cys-sle-"))
            .filter(|l| !l.contains(&me))
            .map(|l| l.split_whitespace().take(3).collect::<Vec<_>>().join(" "))
            .collect();
        if !old.is_empty() {
            eprintln!("⚠ session_lease_e2e: 옛 회차 상자 프로세스 {}개가 남아 있음(고아 의심 · pid ppid 명령): {old:?}", old.len());
        }
    });
}

fn out(o: &Output) -> String {
    format!("rc={:?}\n{}\n{}", o.status.code(), String::from_utf8_lossy(&o.stdout), String::from_utf8_lossy(&o.stderr))
}

/// 결함 ① 남은 모양 — 같은 데몬에서 작성자만 죽은 뒤 600초 안에 다시 복원하면 같은 대화를 잇는다(자기 claim 을 남으로 읽지 않는다).
#[test]
fn same_daemon_rerestore_within_600s_keeps_the_conversation() {
    let b = Box_::new("r1");
    b.up();
    let first = b.cys(&["restore"]);
    let w = b.settle_writers(6);
    assert_eq!(w.len(), 1, "첫 복원이 대화를 잇지 않았다: {}\n{}", out(&first), b.fake_log());
    b.kill_writers();
    b.wait_seat_empty();
    let mut rounds = Vec::new();
    let rr: usize = std::env::var("SLE_RR").ok().and_then(|v| v.parse().ok()).unwrap_or(3);
    let (mut rc93, mut secs) = (0usize, Vec::new());
    for i in 0..rr {
        let t0 = Instant::now();
        let o = b.cys(&["restore"]);
        secs.push(t0.elapsed().as_secs_f64());
        if o.status.code() == Some(93) {
            rc93 += 1;
        }
        let w = b.settle_writers(6);
        rounds.push(format!("#{i} writers={} {}", w.len(), out(&o).lines().filter(|l| l.contains(ROLE) || l.starts_with("rc=")).collect::<Vec<_>>().join(" | ")));
        b.kill_writers();
        b.wait_seat_empty();
    }
    let lost = rounds.iter().filter(|r| !r.contains("writers=1")).count();
    secs.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let q = |p: f64| secs[((secs.len() as f64 - 1.0) * p).round() as usize];
    eprintln!("R1 SUMMARY lease={} rounds={rr} lost={lost} rc93={rc93} restore_secs median={:.3} p95={:.3} max={:.3}",
              std::env::var("CYS_SESSION_LEASE").unwrap_or_else(|_| "on".into()), q(0.5), q(0.95), q(1.0));
    assert_eq!(rc93, 0, "정상 조건 재복원에서 판정 불가(rc 93) {rc93}/{rr}");
    assert_eq!(lost, 0, "600초 안 재복원에서 대화를 잃었다 {lost}/{rr}:\n{}\n--- fake.log\n{}", rounds.join("\n"), b.fake_log());
}

/// TICKET=cysr-1118-seat ② — 강제 종료된 claude 가 끄지 못한 포커스 보고 모드(ESC[?1004h)가 뷰어에 남아, 포커스가 바뀔 때마다
/// GUI 가 `ESC[O`/`ESC[I` 를 맨 셸 입력줄로 보낸 좌석(rc8 P2 「[O[Iclaude」 실측 꼴). 그 좌석에서 재연결 복원이 성공해야 한다 —
/// 같은 좌석(in-seat) · 작성자 1 · fresh 폴백 0.
#[test]
fn residual_focus_report_bytes_do_not_break_in_seat_reconnect() {
    let mut b = Box_::new("rf1");
    // 잔재가 글자 그대로 입력줄에 남는 셸(윈 PowerShell 실측 꼴의 맥 재현) — 줄 편집기 없음 = tty 정규 모드(ESC 도 글자 · ^U = VKILL).
    //   zsh·readline 은 ESC[O/ESC[I 를 키 열로 삼켜 이 결함이 맥 기본 셸에선 드러나지 않는다(대조 실측 11-23: 고침 없이도 초록).
    let sh = b.base.join("sbin/noedit-sh");
    std::fs::write(&sh, "#!/bin/bash\nexec /bin/bash --noprofile --norc --noediting -i\n").unwrap();
    assert!(Command::new("/bin/chmod").arg("755").arg(&sh).status().unwrap().success());
    b.seat_shell = Some(sh);
    b.up();
    let first = b.cys(&["restore"]);
    assert_eq!(b.settle_writers(6).len(), 1, "첫 복원이 대화를 잇지 않았다: {}\n{}", out(&first), b.fake_log());
    let seats = b.role_seats();
    assert_eq!(seats.len(), 1, "좌석 {seats:?}");
    let seat = seats[0];
    b.kill_writers();
    b.wait_seat_empty();
    // 뷰어(xterm.js 5.5 sendFocus 잔류)가 보내는 바이트 — GUI `send_input` 과 같은 인자(human · quiet).
    for _ in 0..2 {
        let r = b.rpcp("surface.send_text", json!({"surface_id": seat, "text": "\u{1b}[O\u{1b}[I", "quiet": true, "human": true,
                                                   "queued": false, "clear_first": false, "machine_origin": false}));
        assert!(r.as_ref().is_ok_and(|v| !v.is_null()), "포커스 바이트 주입 실패: {r:?}");
        std::thread::sleep(Duration::from_millis(150));
    }
    let o = b.cys(&["restore"]);
    let w = b.settle_writers(6);
    let log = b.fake_log();
    assert!(out(&o).contains("좌석 내 재연결"), "in-seat 경로가 아니다: {}", out(&o));
    assert_eq!(w.len(), 1, "잔류 포커스 바이트 좌석에서 재연결이 대화를 잇지 못했다: {}\n--- fake.log\n{log}", out(&o));
    assert!(!out(&o).contains("fresh 기동으로 폴백"), "fresh 폴백: {}", out(&o));
    let last = log.lines().rev().find(|l| l.starts_with("sid=")).unwrap_or("");
    assert!(last.contains(&format!("surface={seat} ")), "같은 좌석에서 이어야 한다(surface:{seat}): {last}");
}

/// 두 복원 입구 동시 실행 — `cys restore` ∥ `cys launch-agent --resume-saved` 가 같은 대화를 동시에 이으면 작성자는 하나.
#[test]
fn two_restore_entries_at_once_leave_one_writer() {
    let b = Box_::new("r3");
    b.up();
    let n = std::env::var("SLE_ROUNDS").ok().and_then(|v| v.parse().ok()).unwrap_or(5);
    let mut bad = Vec::new();
    let (mut lost, mut double, mut orphan) = (0usize, 0usize, 0usize);
    for i in 0..n {
        let a = b.cmd(&["restore"]).stdout(Stdio::piped()).stderr(Stdio::piped()).spawn().unwrap();
        let proj = b.base.join("proj").to_string_lossy().into_owned();
        let c = b.cmd(&["launch-agent", "--role", ROLE, "--agent", "claude", "--resume-saved", "--cwd", &proj]).stdout(Stdio::piped()).stderr(Stdio::piped()).spawn().unwrap();
        let (oa, oc) = (a.wait_with_output().unwrap(), c.wait_with_output().unwrap());
        let w = b.settle_writers(6);
        let pin = b.rpc("system.topology").ok().and_then(|t| {
            t["saved"].as_array()?.iter().find(|e| e["role"].as_str() == Some(ROLE))?["session_id"].as_str().map(String::from)
        });
        match w.len() {
            0 => lost += 1,
            1 => {}
            _ => double += 1,
        }
        if pin.as_deref() != Some(b.sid.as_str()) {
            orphan += 1;
        }
        if w.len() != 1 {
            bad.push(format!("#{i} writers={} restore[{}] launch[{}]", w.len(), out(&oa).replace('\n', " / "), out(&oc).replace('\n', " / ")));
        }
        b.reset();
    }
    eprintln!("R3 SUMMARY lease={} rounds={n} lost={lost} double={double} orphan_pin={orphan}",
              std::env::var("CYS_SESSION_LEASE").unwrap_or_else(|_| "on".into()));
    bad.truncate(3);
    assert!(lost + double + orphan == 0, "두 입구 동시 실행에서 작성자 ≠ 1: {}/{n}\n{}", bad.len(), bad.join("\n"));
}

/// master#388727f0 ① · codex 1R B3 — 부서 데몬 2개(소켓 2 · **같은 HOME = 같은 임대 폴더**).
/// ⑴ 정상 조건: 두 데몬이 각자 자기 대화만 동시에 재복원(작성자만 죽인 뒤) `SLE_DD` 회 — rc 93 = 0 · 소실 0.
/// ⑵ 맞는 93: A 데몬의 좌석이 띄운 대화 임대가 작성자 미확인(결과 불명 ⑪ · 쓰기가 아직 안 닿음 = argv 증거도 없음)일 때
///    B 데몬에서 그 대화를 `--resume-saved` 하면 — A 데몬이 살아 있는 동안 93(other-gen-alive) · 띄우지 않음.
/// ⑶ A 데몬이 죽은 뒤에는 같은 시도가 인수해 잇는다(rc 0 · 작성자 1).
#[test]
fn two_daemons_sharing_a_home_never_false_block_and_refuse_a_live_foreign_seat() {
    let a = Box_::new("dd");
    a.up();
    let b = a.second("tw2", None);
    b.up();
    let n: usize = std::env::var("SLE_DD").ok().and_then(|v| v.parse().ok()).unwrap_or(3);
    let (mut rc93, mut lost, mut bad) = (0usize, 0usize, Vec::new());
    for i in 0..n {
        let pa = a.cmd(&["restore"]).stdout(Stdio::piped()).stderr(Stdio::piped()).spawn().unwrap();
        let pb = b.cmd(&["restore"]).stdout(Stdio::piped()).stderr(Stdio::piped()).spawn().unwrap();
        let (oa, ob) = (pa.wait_with_output().unwrap(), pb.wait_with_output().unwrap());
        rc93 += [&oa, &ob].iter().filter(|o| o.status.code() == Some(93)).count();
        std::thread::sleep(Duration::from_secs(6));
        let (wa, wb) = (a.writers(), b.writers());
        let l = usize::from(wa.len() != 1) + usize::from(wb.len() != 1);
        lost += l;
        if l > 0 || oa.status.code() == Some(93) || ob.status.code() == Some(93) {
            bad.push(format!("#{i} A writers={} [{}] B writers={} [{}]", wa.len(), out(&oa).replace('\n', " / "), wb.len(), out(&ob).replace('\n', " / ")));
        }
        a.kill_writers(); // 상자 안 가짜 claude 전부(두 데몬 것)
        a.wait_seat_empty();
        b.wait_seat_empty();
    }
    eprintln!("DD SUMMARY lease={} rounds={n} restores={} lost={lost} rc93={rc93}",
              std::env::var("CYS_SESSION_LEASE").unwrap_or_else(|_| "on".into()), n * 2);
    bad.truncate(3);
    assert_eq!(rc93, 0, "두 데몬 정상 조건에서 판정 불가(거짓 막힘):\n{}", bad.join("\n"));
    assert_eq!(lost, 0, "두 데몬 정상 조건에서 대화를 잃었다:\n{}", bad.join("\n"));
    if std::env::var("CYS_SESSION_LEASE").is_ok_and(|v| v == "off") {
        return; // ⑵⑶ 은 임대 판정 시험
    }

    // ⑵ A 가 대화를 띄운 뒤 결과 불명으로 남은 모양 — 작성자 미확인 · A 의 좌석·세대 그대로 · argv 증거 없음(작성자 프로세스 없음).
    let o = a.cys(&["restore"]);
    assert_eq!(a.settle_writers(6).len(), 1, "⑵ 전제: A 가 대화를 잇지 않았다 {}", out(&o));
    a.kill_writers();
    a.wait_seat_empty();
    let f = a.lease_file();
    let mut l: Value = serde_json::from_str(&std::fs::read_to_string(&f).expect("⑵ 전제: 임대 파일")).unwrap();
    assert!(l["daemon_gen"].as_str().is_some() && l["surface_id"].as_u64().is_some(), "⑵ 전제: 좌석·세대 기록 {l}");
    l["writer"] = Value::Null;
    l["state"] = json!("unknown");
    std::fs::write(&f, l.to_string()).unwrap();
    let b_same = a.second("tw1x", Some(&a.sid)); // B 데몬 저장 토폴로지를 「tw1x 가 A 의 대화를 잇는다」로 바꿈(같은 run2)
    let proj = a.base.join("proj").to_string_lossy().into_owned();
    let o = b_same.cys(&["launch-agent", "--role", "tw1x", "--agent", "claude", "--resume-saved", "--cwd", &proj]);
    let w = b_same.settle_writers(4);
    assert_eq!(o.status.code(), Some(93), "⑵ 살아 있는 A 데몬 좌석의 결과 불명 임대를 B 가 넘겨받았다: {}", out(&o));
    assert!(String::from_utf8_lossy(&o.stderr).contains("other-gen-alive"), "⑵ 사유: {}", out(&o));
    assert!(w.is_empty(), "⑵ 거절했는데 작성자가 떴다");
    eprintln!("DD B3 live-foreign-daemon rc=93 ok");

    // ⑶ A 데몬이 죽으면 그 좌석도 함께 내려갔다(T1) → 인수해 잇는다.
    a.down();
    let o = b_same.cys(&["launch-agent", "--role", "tw1x", "--agent", "claude", "--resume-saved", "--cwd", &proj]);
    let w = b_same.settle_writers(6);
    assert_eq!((o.status.code(), w.len()), (Some(0), 1), "⑶ 죽은 데몬의 임대를 인수하지 못했다: {}", out(&o));
    eprintln!("DD B3 dead-foreign-daemon takeover ok");
    drop(b_same);
    drop(b);
}

/// 마지막 stdout 줄의 좌석(`surface:N`) — launch-agent stdout 계약(마지막 줄 = 좌석).
fn seat_of(o: &Output) -> Option<u64> {
    String::from_utf8_lossy(&o.stdout).lines().rev().find_map(|l| l.trim().strip_prefix("surface:")?.parse().ok())
}

/// codex(post) #2 — rc 0 마무리의 좌석 = **그 기동이 만든 좌석**(역할 이름 조회 아님).
/// 살아 있는 `worker`(W1 · 새 대화)가 있을 때 `launch-agent --resume-saved --role worker` → 데몬은 새 좌석을 `worker-N` 으로 바꿔 띄운다(dedup_worker_role)
/// → 임대는 새 좌석(W2)을 가리키고 그 좌석의 작성자(W2 의 claude)를 적어야 한다. 역할 이름으로 찾으면 W1(작성자 없음)을 적는다.
/// `SLE_RN` 회(기본 1) — 매 회 W1·W2 를 새로 띄우고 정리한다.
#[test]
fn resume_saved_into_a_renamed_worker_seat_records_the_seat_it_made() {
    if std::env::var("CYS_SESSION_LEASE").is_ok_and(|v| v == "off") {
        return; // 임대 판정 시험
    }
    let a = Box_::new("rn");
    let b = a.second("worker", Some(&a.sid));
    b.up();
    let proj = a.base.join("proj").to_string_lossy().into_owned();
    let n: usize = std::env::var("SLE_RN").ok().and_then(|v| v.parse().ok()).unwrap_or(1);
    for i in 0..n {
        // W1 = `worker` 를 쥔 빈 셸(에이전트 없음 · 판정문 재현 그대로) — worker 는 승계 대상이 아니라(privileged_role = master|cso) 새 좌석은 worker-N.
        let w1 = b.rpcp("surface.create", json!({"role": "worker", "cwd": proj, "rows": 24, "cols": 80}))
            .ok().and_then(|r| r["surface_id"].as_u64()).unwrap_or_else(|| panic!("#{i} W1 빈 셸 만들기"));
        // W1 생성이 영속본의 `worker` 칸을 W1(대화 없음)로 덮었다 — 저장 핀 S 를 되돌려 「launch-agent 가 핀 S 를 읽은 뒤 W1 이 `worker` 를 쥔」
        // 창(핀 판독 ↔ surface.create 사이)을 결정론으로 만든다(데몬 `system.topology` 의 saved = 매번 디스크 판독).
        let cfg = a.base.join("home/.claude");
        b.write_saved_pin(json!({"entries": [{"role": "worker", "agent": "claude", "cwd": proj, "session_id": a.sid, "claude_config_dir": cfg}]}));
        let o2 = b.cys(&["launch-agent", "--role", "worker", "--agent", "claude", "--resume-saved", "--cwd", &proj]);
        let w2 = seat_of(&o2).unwrap_or_else(|| panic!("#{i} W2 기동: {}", out(&o2)));
        assert_eq!(o2.status.code(), Some(0), "#{i} W2 rc: {}", out(&o2));
        assert_ne!(w1, w2, "#{i} 전제: W2 는 새 좌석 {}", out(&o2));
        let writers = b.settle_writers(3);
        assert_eq!(writers.len(), 1, "#{i} 전제: W2 가 저장 대화를 이었다 {}\n{}", out(&o2), b.fake_log());
        let l: Value = serde_json::from_str(&std::fs::read_to_string(b.lease_file()).expect("임대 파일")).unwrap();
        assert_eq!(l["surface_id"].as_u64(), Some(w2), "#{i} 임대가 만든 좌석(W2 = surface:{w2})이 아니라 다른 좌석(W1 = surface:{w1})을 가리킨다: {l}");
        assert_eq!(l["writer"]["pid"].as_i64(), Some(writers[0] as i64), "#{i} 임대 작성자 ≠ W2 의 claude: {l}");
        // 전문가 칸(브리프 §5): W1 을 닫은 직후 · W2 의 SessionStart 등록 전(가짜 claude = 훅 없음 = 등록 0) 창에서 세 번째 좌석이 같은 대화를 잡는가 — `SLE_RN3` 회(기본 3).
        let _ = b.rpcp("surface.close", json!({"surface_id": w1, "cause": "reap", "only_if_empty": true}));
        let n3: usize = std::env::var("SLE_RN3").ok().and_then(|v| v.parse().ok()).unwrap_or(3);
        for j in 0..n3 {
            b.write_saved_pin(json!({"entries": [{"role": "worker", "agent": "claude", "cwd": proj, "session_id": a.sid, "claude_config_dir": cfg}]}));
            let o3 = b.cys(&["launch-agent", "--role", "worker", "--agent", "claude", "--resume-saved", "--cwd", &proj]);
            let w = b.writers();
            // ★1.1.16 편입(skt1): 조각 1 의 `launch_pin_verdict` 가 임대보다 먼저 「다른 좌석이 저장 대화를 잇고 있다」(rc 93 · 새 대화 0)로
            //   멈출 수 있다 — 어느 관문이 막든 새 좌석 0 · 작성자 1 이 이 시험의 불변식이다(92 = 임대 · 93 = 조각 1 보류).
            assert!(matches!(o3.status.code(), Some(92 | 93)) && w.len() == 1, "#{i}.{j} 세 번째 좌석이 W2 가 잇는 대화를 잡았다(작성자 {w:?}): rc={:?} {}", o3.status.code(), out(&o3));
            if let Some(w3) = seat_of(&o3) {
                panic!("#{i}.{j} 거절했는데 좌석 surface:{w3} 이 생겼다: {}", out(&o3));
            }
        }
        if n3 > 0 {
            eprintln!("RN3 #{i} third-seat refusals={n3} writers=1");
        }
        // 정리 — 작성자 끄고 두 좌석 회수(빈 셸 only_if_empty · 묘비 0).
        b.kill_writers();
        for sid in [w1, w2] {
            let t = Instant::now();
            let alive = |b: &Box_| {
                let l = b.rpc("surface.list").unwrap_or(Value::Null);
                l["surfaces"].as_array().or_else(|| l.as_array()).into_iter().flatten()
                    .any(|s| s["surface_id"].as_u64() == Some(sid) && s["exited"].as_bool() != Some(true))
            };
            while alive(&b) {
                assert!(t.elapsed() < Duration::from_secs(20), "#{i} 좌석 surface:{sid} 정리 실패");
                let _ = b.rpcp("surface.close", json!({"surface_id": sid, "cause": "reap", "only_if_empty": true}));
                std::thread::sleep(Duration::from_millis(500));
            }
        }
        let _ = std::fs::remove_file(b.lease_file());
    }
    eprintln!("RN SUMMARY rounds={n} ok");
    drop(b);
}

/// r4 A(codex 3R ①②) — 멱등 키에 대화 ID: 평범한 `launch-agent`(새 대화 T)가 역할 R·cwd X 좌석 W 를 세운 뒤 120초(데몬 create_idem) 안에
/// 저장 대화 S 의 `--resume-saved` 가 같은 R·X 로 와도 W 를 재반환받지 않는다 → 새 좌석에서 S 를 잇는다(rc 0 · S 작성자 1 · 임대 = 새 좌석).
/// 고치기 전(키에 대화 없음): W 재반환 → 기동 건너뜀 → rc 0 인데 S 작성자 0(거짓 성공) · 임대가 W 를 가리킴.
#[test]
fn a_saved_conversation_never_gets_another_conversations_seat_back() {
    if std::env::var("CYS_SESSION_LEASE").is_ok_and(|v| v == "off") {
        return; // 임대 판정 시험
    }
    let b = Box_::new("ir");
    b.up();
    let proj = b.base.join("proj").to_string_lossy().into_owned();
    let o1 = b.cys(&["launch-agent", "--role", ROLE, "--agent", "claude", "--cwd", &proj]);
    let w = seat_of(&o1).unwrap_or_else(|| panic!("W 기동: {}", out(&o1)));
    let t = Instant::now();
    while b.fakes().is_empty() && t.elapsed() < Duration::from_secs(10) {
        std::thread::sleep(Duration::from_millis(200));
    }
    assert_eq!((b.fakes().len(), b.writers().len()), (1, 0), "전제: W 에 새 대화(T) claude 하나 · S 작성자 0 {}", out(&o1));
    // r5(codex r4 #1 대조군): W 가 **대화 T 로 등록된** 정상 흐름 — 등록(SessionStart 훅이 하는 `usage.register`)을 시험이 대신 하고 데몬 핀이 T 가 될 때까지.
    let cfg = b.base.join("home/.claude");
    register_conversation(&b, w, "7e7e0000-0000-4000-8000-00000000000a");
    b.write_saved_pin(json!({"entries": [{"role": ROLE, "agent": "claude", "cwd": proj, "session_id": b.sid, "claude_config_dir": cfg}]}));
    let o2 = b.cys(&["launch-agent", "--role", ROLE, "--agent", "claude", "--resume-saved", "--cwd", &proj]);
    let writers = b.settle_writers(3);
    let w2 = seat_of(&o2);
    let lease = std::fs::read_to_string(b.lease_file()).ok();
    eprintln!("IR rc={:?} W=surface:{w} W2={w2:?} writers={} lease={lease:?}", o2.status.code(), writers.len());
    assert!(!String::from_utf8_lossy(&o2.stderr).contains("멱등 재반환된 자리에 에이전트가 이미 살아 있다"), "다른 대화(T) 좌석 W 를 재반환받았다: {}", out(&o2));
    assert_eq!((o2.status.code(), writers.len()), (Some(0), 1), "S 를 새 좌석에서 잇지 않았다: {}\n{}", out(&o2), b.fake_log());
    assert!(w2.is_some_and(|x| x != w), "새 좌석이 아니다: {}", out(&o2));
    let l: Value = serde_json::from_str(&lease.expect("임대 파일")).unwrap();
    assert_eq!((l["surface_id"].as_u64(), l["writer"]["pid"].as_i64()), (w2, Some(writers[0] as i64)), "임대 = 새 좌석 · 작성자 = 그 claude: {l}");
}

/// 좌석 `w` 를 대화 `t` 로 등록(SessionStart 훅의 `usage.register` 를 시험이 대신) — 데몬 topology live 의 그 좌석 session_id 가 `t` 가 될 때까지.
fn register_conversation(b: &Box_, w: u64, t: &str) {
    let cfg = b.base.join("home/.claude");
    let proj = b.base.join("proj");
    let slug: String = proj.to_string_lossy().chars().map(|c| if c.is_ascii_alphanumeric() { c } else { '-' }).collect();
    let tj = cfg.join("projects").join(slug).join(format!("{t}.jsonl"));
    std::fs::write(&tj, format!("{{\"type\":\"user\",\"sessionId\":\"{t}\"}}\n")).unwrap();
    let r = b.rpcp("usage.register", json!({"surface_id": w, "transcript": tj}));
    let t0 = Instant::now();
    loop {
        let topo = b.rpc("system.topology").unwrap_or(Value::Null);
        let got = topo["live"].as_array().into_iter().flatten()
            .find(|e| e["surface_id"].as_u64() == Some(w)).and_then(|e| e["session_id"].as_str().map(String::from));
        if got.as_deref() == Some(t) {
            return;
        }
        assert!(t0.elapsed() < Duration::from_secs(30), "전제: 좌석 surface:{w} 등록이 {t} 로 안 바뀜(register {r:?} · 지금 {got:?})");
        std::thread::sleep(Duration::from_millis(300));
    }
}

/// r5(codex r4 #1 · blocking) — 같은 역할의 살아 있는 좌석 W 가 **어느 대화를 쓰는지 모를 때**(등록 없음 · argv 에 대화 없음 =
/// 옛 키로 새 대화로 뜬 뒤 좌석 안 `/resume S` · 훅 부재) 저장 대화 S 의 `--resume-saved` 는 새 좌석 W2 를 만들지 않는다 —
/// W 가 이미 S 를 쓰고 있을 수 있다(작성자 둘). 판정 불가 rc 93 · 새 좌석 0 · 새 작성자 0 · 임대 = W 를 가리킨 「결과 불명」.
/// 고치기 전: 키가 달라 새 좌석 W2 → S 를 잇는 claude 가 하나 더(rc 0).
#[test]
fn a_live_seat_of_unknown_conversation_is_not_given_a_second_writer() {
    if std::env::var("CYS_SESSION_LEASE").is_ok_and(|v| v == "off") {
        return; // 임대 판정 시험
    }
    let mut b = Box_::new("uw");
    b.no_reg = true; // 데몬을 띄우기 전에 — 좌석 env 는 데몬 env 를 물려받는다
    b.up();
    let proj = b.base.join("proj").to_string_lossy().into_owned();
    let o1 = b.cys(&["launch-agent", "--role", ROLE, "--agent", "claude", "--cwd", &proj]);
    let w = seat_of(&o1).unwrap_or_else(|| panic!("W 기동: {}", out(&o1)));
    let t = Instant::now();
    while b.fakes().is_empty() && t.elapsed() < Duration::from_secs(10) {
        std::thread::sleep(Duration::from_millis(200));
    }
    assert_eq!(b.fakes().len(), 1, "전제: W 에 claude 하나 {}", out(&o1));
    let topo = b.rpc("system.topology").unwrap_or(Value::Null);
    let reg = topo["live"].as_array().into_iter().flatten().find(|e| e["surface_id"].as_u64() == Some(w)).map(|e| e["session_id"].clone());
    assert_eq!(reg, Some(Value::Null), "전제: W 등록 없음(훅 부재) {topo}");
    let cfg = b.base.join("home/.claude");
    b.write_saved_pin(json!({"entries": [{"role": ROLE, "agent": "claude", "cwd": proj, "session_id": b.sid, "claude_config_dir": cfg}]}));
    let o2 = b.cys(&["launch-agent", "--role", ROLE, "--agent", "claude", "--resume-saved", "--cwd", &proj]);
    std::thread::sleep(Duration::from_secs(3));
    let seats = b.role_seats();
    let lease = std::fs::read_to_string(b.lease_file()).ok();
    eprintln!("UW rc={:?} W=surface:{w} seats={seats:?} fakes={} lease={lease:?}", o2.status.code(), b.fakes().len());
    assert_eq!(o2.status.code(), Some(93), "등록 없는 살아 있는 좌석 옆에 S 를 띄웠다(작성자 둘 가능): {}", out(&o2));
    assert_eq!((seats, b.fakes().len(), b.writers().len()), (vec![w], 1, 0), "새 좌석·새 작성자가 생겼다: {}", out(&o2));
    assert!(seat_of(&o2).is_none(), "거절인데 stdout 좌석 줄: {}", out(&o2));
    let l: Value = serde_json::from_str(&lease.expect("임대 파일(결과 불명 유지)")).unwrap();
    assert_eq!((l["state"].as_str(), l["surface_id"].as_u64()), (Some("unknown"), Some(w)), "임대 = W 를 가리킨 결과 불명: {l}");
    // 그 좌석이 살아 있는 동안 다음 시도도 띄우지 않는다(임대가 W 를 가리킴 = 92) · W 가 내려가면 인수해 잇는다.
    let o3 = b.cys(&["launch-agent", "--role", ROLE, "--agent", "claude", "--resume-saved", "--cwd", &proj]);
    assert_eq!((o3.status.code(), b.role_seats().len()), (Some(92), 1), "W 살아 있는데 재시도가 띄웠다: {}", out(&o3));
    b.kill_writers();
    b.wait_seat_empty();
    let _ = b.rpcp("surface.close", json!({"surface_id": w, "cause": "reap", "only_if_empty": true}));
    let t = Instant::now();
    while b.role_seats().contains(&w) && t.elapsed() < Duration::from_secs(20) {
        std::thread::sleep(Duration::from_millis(300));
    }
    let o4 = b.cys(&["launch-agent", "--role", ROLE, "--agent", "claude", "--resume-saved", "--cwd", &proj]);
    let wr = b.settle_writers(3);
    assert_eq!((o4.status.code(), wr.len()), (Some(0), 1), "W 가 내려간 뒤 인수하지 못했다: {}", out(&o4));
}

/// 좌석 `w` 의 데몬 등록 대화(topology live session_id · 없으면 None).
fn registered_of(b: &Box_, w: u64) -> Option<String> {
    let topo = b.rpc("system.topology").unwrap_or(Value::Null);
    topo["live"].as_array().into_iter().flatten()
        .find(|e| e["surface_id"].as_u64() == Some(w)).and_then(|e| e["session_id"].as_str().map(String::from))
}

/// r5b(master 재검증 ⓐ) — 정상 기동 직후(W 가 새 대화 T 로 떴지만 SessionStart 등록 **전**) 저장 대화 S 를 복원하면 #1 방어로 93
/// (임대 = W 를 가리킨 결과 불명) · 그 뒤 W 가 **실제 등록 경로**(가짜 claude 의 `cys usage-register` = 훅과 같은 길 · 임대 follow 포함)로
/// T 임이 드러나면 S 재시도는 새 좌석으로 복원된다(rc 0 · S 작성자 1 · W 는 T 그대로).
/// 고치기 전: 임대가 W(살아 있음)를 가리킨 채 남아 W 가 사는 동안 92 만 반복(빠져나오는 길 = W 닫기·데몬 재시작).
#[test]
fn a_seat_revealed_as_another_conversation_frees_the_saved_restore() {
    if std::env::var("CYS_SESSION_LEASE").is_ok_and(|v| v == "off") {
        return; // 임대 판정 시험
    }
    let mut b = Box_::new("rv");
    let gate = b.base.join("reg-gate");
    b.reg_gate = Some(gate.clone()); // 데몬을 띄우기 전에 — 좌석 env 는 데몬 env 를 물려받는다
    b.up();
    let proj = b.base.join("proj").to_string_lossy().into_owned();
    let o1 = b.cys(&["launch-agent", "--role", ROLE, "--agent", "claude", "--cwd", &proj]);
    let w = seat_of(&o1).unwrap_or_else(|| panic!("W 기동: {}", out(&o1)));
    let t = Instant::now();
    while b.fakes().is_empty() && t.elapsed() < Duration::from_secs(10) {
        std::thread::sleep(Duration::from_millis(200));
    }
    // 가짜 claude 는 등록을 자식 셸(이름 session-start.sh)에 미뤄 둔다 · S 작성자는 0.
    assert_eq!((b.fakes().is_empty(), b.writers().len(), registered_of(&b, w)), (false, 0, None), "전제: W 에 claude · 등록 전 {}", out(&o1));
    let cfg = b.base.join("home/.claude");
    let pin_s = || { b.write_saved_pin(json!({"entries": [{"role": ROLE, "agent": "claude", "cwd": proj, "session_id": b.sid, "claude_config_dir": cfg}]})); };
    pin_s();
    let o2 = b.cys(&["launch-agent", "--role", ROLE, "--agent", "claude", "--resume-saved", "--cwd", &proj]);
    assert_eq!((o2.status.code(), b.role_seats(), b.writers().len()), (Some(93), vec![w], 0), "전제: 등록 전 W 옆 = 93 · 새 좌석 0: {}", out(&o2));
    // W 가 등록한다(훅과 같은 길) — 데몬 등록이 S 아닌 대화 T 가 될 때까지.
    std::fs::write(&gate, "").unwrap();
    let t0 = Instant::now();
    let reg_t = loop {
        if let Some(r) = registered_of(&b, w) {
            break r;
        }
        assert!(t0.elapsed() < Duration::from_secs(30), "전제: W 등록이 안 보임");
        std::thread::sleep(Duration::from_millis(200));
    };
    assert_ne!(reg_t, b.sid, "전제: W 는 S 가 아닌 대화로 등록");
    std::thread::sleep(Duration::from_millis(500)); // 등록 명령의 임대 follow 가 끝날 틈(rc 와 무관 · 출력 0)
    let lease_before = std::fs::read_to_string(b.lease_file()).ok();
    pin_s();
    let o3 = b.cys(&["launch-agent", "--role", ROLE, "--agent", "claude", "--resume-saved", "--cwd", &proj]);
    let writers = b.settle_writers(3);
    let w2 = seat_of(&o3);
    let lease = std::fs::read_to_string(b.lease_file()).ok();
    eprintln!("RV rc={:?} W=surface:{w} reg={reg_t} W2={w2:?} writers={} lease_before={lease_before:?} lease={lease:?}", o3.status.code(), writers.len());
    assert_eq!((o3.status.code(), writers.len()), (Some(0), 1), "W 가 다른 대화(T)로 드러났는데 S 복원이 풀리지 않았다: {}\n{}", out(&o3), b.fake_log());
    assert!(w2.is_some_and(|x| x != w), "새 좌석이 아니다: {}", out(&o3));
    assert_eq!(registered_of(&b, w).as_deref(), Some(reg_t.as_str()), "W 는 T 그대로");
    let l: Value = serde_json::from_str(&lease.expect("임대 파일")).unwrap();
    assert_eq!((l["surface_id"].as_u64(), l["writer"]["pid"].as_i64()), (w2, Some(writers[0] as i64)), "임대 = 새 좌석 · 작성자 = 그 claude: {l}");
}

/// r5b-2(master 재검증 b444f7fa · 탐침 t1-c45d7932-hp-probe.rs 편입) — 훅 없는 좌석 W(등록 0) 옆 S 복원 = 93(임대 unknown@W) 뒤,
/// 같은 프로젝트 폴더에 W 와 무관한 다른 대화 T 의 jsonl 이 생기면 데몬 휴리스틱(mtime 최신)이 W 의 topology `session_id` 를 T 로 **1회 핀**한다.
/// 그것은 등록(소유 증거)이 아니다 → S 재시도는 계속 막힌다(rc 92 · 새 좌석 0 · 작성자 0). 풀림은 등록 경로(`registered_session_id`)일 때만.
/// 고치기 전(c45d7932): 휴리스틱 핀을 등록으로 읽어 rc 0 · 새 좌석 W2(작성자 둘 가능).
#[test]
fn a_heuristic_pin_on_a_hookless_seat_never_frees_the_saved_restore() {
    if std::env::var("CYS_SESSION_LEASE").is_ok_and(|v| v == "off") {
        return; // 임대 판정 시험
    }
    let mut b = Box_::new("hp");
    b.no_reg = true; // 데몬을 띄우기 전에 — 좌석 env 는 데몬 env 를 물려받는다
    b.up();
    let proj = b.base.join("proj").to_string_lossy().into_owned();
    let o1 = b.cys(&["launch-agent", "--role", ROLE, "--agent", "claude", "--cwd", &proj]);
    let w = seat_of(&o1).unwrap_or_else(|| panic!("W 기동: {}", out(&o1)));
    let t = Instant::now();
    while b.fakes().is_empty() && t.elapsed() < Duration::from_secs(10) {
        std::thread::sleep(Duration::from_millis(200));
    }
    assert_eq!((b.fakes().len(), registered_of(&b, w)), (1, None), "전제: W 에 claude 하나 · 핀 없음 {}", out(&o1));
    let cfg = b.base.join("home/.claude");
    let pin_s = || { b.write_saved_pin(json!({"entries": [{"role": ROLE, "agent": "claude", "cwd": proj, "session_id": b.sid, "claude_config_dir": cfg}]})); };
    pin_s();
    let o2 = b.cys(&["launch-agent", "--role", ROLE, "--agent", "claude", "--resume-saved", "--cwd", &proj]);
    assert_eq!((o2.status.code(), b.role_seats(), b.writers().len()), (Some(93), vec![w], 0), "전제: 등록 없는 W 옆 = 93 · 새 좌석 0: {}", out(&o2));
    // 같은 프로젝트 폴더에 W 와 무관한 대화 T 의 jsonl(다른 좌석이 같은 저장소에서 쓰는 대화를 흉내).
    let tid = "7a7a7a7a-0000-4000-8000-000000000001";
    let slug: String = b.base.join("proj").to_string_lossy().chars().map(|c| if c.is_ascii_alphanumeric() { c } else { '-' }).collect();
    std::fs::write(cfg.join("projects").join(&slug).join(format!("{tid}.jsonl")), format!("{{\"type\":\"user\",\"sessionId\":\"{tid}\"}}\n")).unwrap();
    let t0 = Instant::now();
    while registered_of(&b, w).is_none() && t0.elapsed() < Duration::from_secs(45) {
        std::thread::sleep(Duration::from_millis(500));
    }
    assert_eq!(registered_of(&b, w).as_deref(), Some(tid), "전제: 데몬 휴리스틱이 W 를 T 로 핀(등록 아님)");
    pin_s();
    let o3 = b.cys(&["launch-agent", "--role", ROLE, "--agent", "claude", "--resume-saved", "--cwd", &proj]);
    let writers = b.settle_writers(3);
    let seats = b.role_seats();
    eprintln!("HP rc={:?} W=surface:{w} pin={tid} W2={:?} seats={seats:?} writers={}", o3.status.code(), seat_of(&o3), writers.len());
    assert_eq!((o3.status.code(), seats, writers.len()), (Some(92), vec![w], 0), "휴리스틱 핀(등록 아님)을 등록으로 읽고 풀었다: {}", out(&o3));
    assert!(seat_of(&o3).is_none(), "거절인데 stdout 좌석 줄: {}", out(&o3));
}

/// r5b-2 ②(master#a07afa3f · #1 방어의 같은 꼴) — 훅 없는 좌석 W 가 S 복원 **전에** 이미 데몬 휴리스틱으로 무관한 대화 T 에 핀돼 있으면,
/// 그 핀은 등록(소유 증거)이 아니다 → #1 방어(같은 역할 미등록 좌석 = 93 · 새 좌석 0)가 그대로 걸려야 한다.
/// 고치기 전(c45d7932): topology `session_id`(휴리스틱 핀 포함)를 「등록됨」으로 읽어 93 없이 새 좌석 W2(작성자 둘 가능).
#[test]
fn a_hookless_seat_pinned_by_heuristic_before_restore_is_still_unverified() {
    if std::env::var("CYS_SESSION_LEASE").is_ok_and(|v| v == "off") {
        return; // 임대 판정 시험
    }
    let mut b = Box_::new("hq");
    b.no_reg = true;
    b.up();
    let proj = b.base.join("proj").to_string_lossy().into_owned();
    let o1 = b.cys(&["launch-agent", "--role", ROLE, "--agent", "claude", "--cwd", &proj]);
    let w = seat_of(&o1).unwrap_or_else(|| panic!("W 기동: {}", out(&o1)));
    let t = Instant::now();
    while b.fakes().is_empty() && t.elapsed() < Duration::from_secs(10) {
        std::thread::sleep(Duration::from_millis(200));
    }
    let cfg = b.base.join("home/.claude");
    let tid = "7a7a7a7a-0000-4000-8000-000000000002";
    let slug: String = b.base.join("proj").to_string_lossy().chars().map(|c| if c.is_ascii_alphanumeric() { c } else { '-' }).collect();
    std::fs::write(cfg.join("projects").join(&slug).join(format!("{tid}.jsonl")), format!("{{\"type\":\"user\",\"sessionId\":\"{tid}\"}}\n")).unwrap();
    let t0 = Instant::now();
    while registered_of(&b, w).is_none() && t0.elapsed() < Duration::from_secs(45) {
        std::thread::sleep(Duration::from_millis(500));
    }
    assert_eq!((b.fakes().len(), registered_of(&b, w).as_deref()), (1, Some(tid)), "전제: W 에 claude 하나 · 휴리스틱 핀 T(등록 아님)");
    b.write_saved_pin(json!({"entries": [{"role": ROLE, "agent": "claude", "cwd": proj, "session_id": b.sid, "claude_config_dir": cfg}]}));
    let o2 = b.cys(&["launch-agent", "--role", ROLE, "--agent", "claude", "--resume-saved", "--cwd", &proj]);
    let writers = b.settle_writers(3);
    let seats = b.role_seats();
    eprintln!("HQ rc={:?} W=surface:{w} pin={tid} W2={:?} seats={seats:?} writers={}", o2.status.code(), seat_of(&o2), writers.len());
    assert_eq!((o2.status.code(), seats, writers.len()), (Some(93), vec![w], 0), "휴리스틱 핀만 있는 훅 없는 좌석 옆에 S 를 띄웠다: {}", out(&o2));
    assert!(seat_of(&o2).is_none(), "거절인데 stdout 좌석 줄: {}", out(&o2));
}

/// 좌석 `w` 의 데몬 **등록** 칸(org.status `registered_session_id`) — topology `session_id`(휴리스틱 핀 포함)와 다르다.
fn daemon_registered(b: &Box_, w: u64) -> Option<String> {
    let st = b.rpc("org.status").unwrap_or(Value::Null);
    st["surfaces"].as_array().into_iter().flatten()
        .find(|e| e["surface_id"].as_u64() == Some(w)).and_then(|e| e["registered_session_id"].as_str().map(String::from))
}

/// 등록 전 W 옆 S 복원 = 93(임대 unknown@W)까지 — FR·SR 공통 앞부분. 돌려주는 값 = (W · 저장 핀 다시 쓰기).
fn unknown_at_w(b: &Box_, proj: &str) -> u64 {
    let o1 = b.cys(&["launch-agent", "--role", ROLE, "--agent", "claude", "--cwd", proj]);
    let w = seat_of(&o1).unwrap_or_else(|| panic!("W 기동: {}", out(&o1)));
    let t = Instant::now();
    while b.fakes().is_empty() && t.elapsed() < Duration::from_secs(10) {
        std::thread::sleep(Duration::from_millis(200));
    }
    pin_saved(b, proj);
    let o2 = b.cys(&["launch-agent", "--role", ROLE, "--agent", "claude", "--resume-saved", "--cwd", proj]);
    assert_eq!((o2.status.code(), b.role_seats(), b.writers().len()), (Some(93), vec![w], 0), "전제: 등록 전 W 옆 = 93 · 새 좌석 0: {}", out(&o2));
    let l: Value = serde_json::from_str(&std::fs::read_to_string(b.lease_file()).expect("임대 파일")).unwrap();
    assert_eq!((l["state"].as_str(), l["surface_id"].as_u64()), (Some("unknown"), Some(w)), "전제: 임대 unknown@W: {l}");
    w
}

fn pin_saved(b: &Box_, proj: &str) {
    let cfg = b.base.join("home/.claude");
    b.write_saved_pin(json!({"entries": [{"role": ROLE, "agent": "claude", "cwd": proj, "session_id": b.sid, "claude_config_dir": cfg}]}));
}

/// skt1(codex r5c #1-2 · blocking) — 좌석 밖 사람·도구의 **가짜 등록**(`cys usage-register --surface W --transcript /…/T.jsonl` · 발신 좌석 없음 =
/// 데몬 소유 게이트 통과)은 unknown@W 를 풀지 않는다 — W 의 작성자 신원과 묶이지 않은 등록 문자열이다. S 재시도 = 92 · 새 좌석 0 · 작성자 0.
/// 고치기 전(7434ebfe): 풀림 조건 = 데몬 등록 문자열 ≠ S → 풀림 → #1 방어도 등록 T 를 보고 통과 → rc 0 · W2(작성자 둘 가능).
#[test]
fn an_outside_fake_registration_never_frees_the_saved_restore() {
    if std::env::var("CYS_SESSION_LEASE").is_ok_and(|v| v == "off") {
        return; // 임대 판정 시험
    }
    let mut b = Box_::new("fr");
    b.reg_gate = Some(b.base.join("reg-gate-never")); // W 는 스스로 등록하지 않는다(그 파일은 만들지 않음)
    b.up();
    let proj = b.base.join("proj").to_string_lossy().into_owned();
    let w = unknown_at_w(&b, &proj);
    let fake_t = b.base.join("elsewhere/7f7f0000-0000-4000-8000-0000000000f1.jsonl"); // 존재하지 않는 파일 · 좌석과 무관한 폴더
    let o = b.cys(&["usage-register", "--surface", &w.to_string(), "--transcript", &fake_t.to_string_lossy()]);
    assert!(o.status.success(), "전제: 좌석 밖 가짜 등록이 데몬에 받아들여진다: {}", out(&o));
    assert_eq!(daemon_registered(&b, w).as_deref(), Some("7f7f0000-0000-4000-8000-0000000000f1"), "전제: 데몬 등록 칸 = 가짜 T");
    pin_saved(&b, &proj);
    let o3 = b.cys(&["launch-agent", "--role", ROLE, "--agent", "claude", "--resume-saved", "--cwd", &proj]);
    let writers = b.settle_writers(3);
    let seats = b.role_seats();
    eprintln!("FR rc={:?} W=surface:{w} W2={:?} seats={seats:?} writers={}", o3.status.code(), seat_of(&o3), writers.len());
    assert_eq!((o3.status.code(), seats, writers.len()), (Some(92), vec![w], 0), "가짜 등록으로 unknown@W 를 풀었다(r5c #1-2): {}", out(&o3));
}

/// skt1(codex r5c #1-1 · blocking) — **낡은 등록**: unknown@W → W 의 최상위 claude 가 T 로 정상 등록(결속) → 그 claude 만 끝나고 같은 좌석에
/// 훅 없는 claude 가 새로 뜸(좌석 안 `/resume S` 와 구별 불가 · 데몬 등록 칸엔 옛 T 가 남음) → S 재시도 = 92(옛 결속의 작성자 죽음 = 증거 소멸).
/// 고치기 전(7434ebfe): 남은 등록 T 로 풀림 → #1 방어도 등록 T 로 통과 → rc 0 · W2.
#[test]
fn a_stale_registration_after_an_agent_swap_never_frees_the_saved_restore() {
    if std::env::var("CYS_SESSION_LEASE").is_ok_and(|v| v == "off") {
        return; // 임대 판정 시험
    }
    let mut b = Box_::new("sr");
    let gate = b.base.join("reg-gate");
    b.reg_gate = Some(gate.clone());
    b.up();
    let proj = b.base.join("proj").to_string_lossy().into_owned();
    let w = unknown_at_w(&b, &proj);
    std::fs::write(&gate, "").unwrap(); // W 의 최상위 claude 가 훅 길로 T 를 등록(임대 follow = 결속)
    let t0 = Instant::now();
    let reg_t = loop {
        if let Some(r) = daemon_registered(&b, w) {
            break r;
        }
        assert!(t0.elapsed() < Duration::from_secs(30), "전제: W 등록이 안 보임");
        std::thread::sleep(Duration::from_millis(200));
    };
    std::thread::sleep(Duration::from_millis(500));
    let old = b.fakes();
    assert_eq!(old.len(), 1, "전제: W 의 claude 하나: {old:?}");
    b.kill_writers();
    // 같은 좌석에 훅 없는 claude(등록 0 · argv 에 S 없음)를 사람이 친 것처럼.
    let exe = b.base.join("sbin/claude");
    std::thread::sleep(Duration::from_millis(800)); // 셸 프롬프트가 돌아올 틈
    // 사람 타이핑 길(human = 앱 키 입력과 같은 길 · 에이전트 쓰기 관문을 안 탐) — 줄 끝 CR 까지 한 번에.
    let st = b.rpcp("surface.send_text", json!({"surface_id": w, "text": format!("FAKE_NO_REG=1 '{}'\r", exe.display()), "human": true}));
    let sk = "human-cr";
    let t1 = Instant::now();
    while (b.fakes().is_empty() || b.fakes() == old) && t1.elapsed() < Duration::from_secs(20) {
        std::thread::sleep(Duration::from_millis(200));
    }
    let alive = || b.rpc("surface.list").ok().and_then(|l| l["surfaces"].as_array()?.iter().find(|s| s["surface_id"].as_u64() == Some(w))?["agent_alive"].as_bool());
    let t2 = Instant::now();
    while alive() != Some(true) && t2.elapsed() < Duration::from_secs(30) {
        std::thread::sleep(Duration::from_millis(300));
    }
    assert_eq!((b.fakes().len(), alive(), daemon_registered(&b, w).as_deref()), (1, Some(true), Some(reg_t.as_str())),
        "전제: W 에 새 claude(등록 0) · 데몬 등록 칸 = 옛 T · send_text={st:?} send_key={sk} 화면={}", out(&b.cys(&["read-screen", "--surface", &w.to_string()])));
    pin_saved(&b, &proj);
    let o3 = b.cys(&["launch-agent", "--role", ROLE, "--agent", "claude", "--resume-saved", "--cwd", &proj]);
    let writers = b.settle_writers(3);
    let seats = b.role_seats();
    eprintln!("SR rc={:?} W=surface:{w} oldT={reg_t} W2={:?} seats={seats:?} writers={}", o3.status.code(), seat_of(&o3), writers.len());
    assert_eq!((o3.status.code(), seats, writers.len()), (Some(92), vec![w], 0), "에이전트 교체 뒤 낡은 등록으로 unknown@W 를 풀었다(r5c #1-1): {}", out(&o3));
}

/// 상자 임대 폴더에서 작성자 pid `pid` 가 쥔 작성 중(held) 임대의 대화 id 들.
fn held_by(b: &Box_, pid: i32) -> Vec<String> {
    let dir = b.base.join("home/.local/state/cys/session-leases");
    let mut v: Vec<String> = std::fs::read_dir(&dir).into_iter().flatten().flatten()
        .filter(|e| e.path().extension().and_then(|x| x.to_str()) == Some("lease"))
        .filter_map(|e| serde_json::from_str::<Value>(std::fs::read_to_string(e.path()).ok()?.trim()).ok())
        .filter(|l| l["state"] == "held" && l["writer"]["pid"].as_i64() == Some(pid as i64))
        .filter_map(|l| l["id"].as_str().map(String::from))
        .collect();
    v.sort();
    v
}

/// skt1(독립 검증 V1 · r5c #1-3 행동 시험) — 좌석 W 의 최상위 claude 가 T 로 결속된 뒤 **좌석 안 `claude -p` 헬퍼**가 자기 대화 H 를
/// 훅 이름 셸에서 등록해도(데몬 등록 칸 = H) 결속은 T 그대로다 — 계통(에이전트 실행 2개)이 「좌석 최상위 훅 아님」이라 follow·등록 앞 결속 해제
/// 둘 다 하지 않는다. 고치기 전(계통 거름 없음 · 또는 계통 수집 누락): 결속이 H 로 옮겨지고 T 임대가 지워짐(T 복원 = 작성자 둘 가능).
#[test]
fn a_helper_registration_inside_the_seat_never_moves_the_binding() {
    if std::env::var("CYS_SESSION_LEASE").is_ok_and(|v| v == "off") {
        return; // 임대 판정 시험
    }
    let mut b = Box_::new("hr");
    let gate = b.base.join("reg-gate");
    let hgate = b.base.join("helper-gate");
    b.reg_gate = Some(gate.clone());
    b.helper_gate = Some(hgate.clone());
    b.up();
    let proj = b.base.join("proj").to_string_lossy().into_owned();
    let o1 = b.cys(&["launch-agent", "--role", ROLE, "--agent", "claude", "--cwd", &proj]);
    let w = seat_of(&o1).unwrap_or_else(|| panic!("W 기동: {}", out(&o1)));
    let t = Instant::now();
    while b.fakes().is_empty() && t.elapsed() < Duration::from_secs(10) {
        std::thread::sleep(Duration::from_millis(200));
    }
    std::fs::write(&gate, "").unwrap(); // 최상위 claude 의 SessionStart 등록(T) = 결속
    let t0 = Instant::now();
    let reg_t = loop {
        if let Some(r) = daemon_registered(&b, w) {
            break r;
        }
        assert!(t0.elapsed() < Duration::from_secs(30), "전제: W 등록이 안 보임");
        std::thread::sleep(Duration::from_millis(200));
    };
    // 최상위 claude = 헬퍼 대기 자식(fork · 같은 argv)의 부모 — 결속 작성자는 그 하나다.
    let t1 = Instant::now();
    let top = loop {
        let tops: Vec<i32> = b.fakes().into_iter().filter(|p| held_by(&b, *p) == vec![reg_t.clone()]).collect();
        if tops.len() == 1 {
            break tops[0];
        }
        assert!(t1.elapsed() < Duration::from_secs(20), "전제: 최상위 claude 의 T 결속이 안 생김 · fakes={:?} · {}", b.fakes(), b.fake_log());
        std::thread::sleep(Duration::from_millis(200));
    };
    std::fs::write(&hgate, "").unwrap(); // 좌석 안 헬퍼가 새 대화 H 를 등록
    let t2 = Instant::now();
    let reg_h = loop {
        match daemon_registered(&b, w) {
            Some(r) if r != reg_t => break r,
            _ => {}
        }
        assert!(t2.elapsed() < Duration::from_secs(30), "전제: 헬퍼 등록이 데몬에 안 보임 · {}", b.fake_log());
        std::thread::sleep(Duration::from_millis(200));
    };
    std::thread::sleep(Duration::from_millis(800)); // 등록 명령의 임대 처리(출력 0)가 끝날 틈
    let held = held_by(&b, top);
    eprintln!("HR W=surface:{w} top={top} T={reg_t} H={reg_h} held={held:?}");
    assert_eq!(held, vec![reg_t.clone()], "좌석 안 헬퍼 등록(H={reg_h})이 최상위 작성자의 결속 T 를 옮기거나 풀었다(r5c #1-3 · V1)");
    let all_h: Vec<i32> = b.fakes().into_iter().filter(|p| held_by(&b, *p).contains(&reg_h)).collect();
    assert!(all_h.is_empty(), "헬퍼 대화 H 가 누군가의 결속이 됐다: {all_h:?}");
}
