//! 대화 소유 임대(lease) — 한 대화(session id)를 쓰는 작성자를 하나로 묶는 원자적 기록 · leaf(상위 의존 0).
//!
//! 설계 정본 = `docs/DESIGN-seatkeep-t1.md`(TICKET=cysr-seatkeep-t1 · master#78599b55 승인).
//! - 키 = `sha256("v1\0" + 정규화(id))` — 경로를 넣지 않는다(별칭·심링크·대소문자로 한 대화가 두 키가 되는 길 차단).
//! - **시간으로 풀지 않는다.** 보유자가 「죽음 확인」(pid 없음 · 같은 pid 다른 출생)일 때만 넘겨받는다.
//!   판정 불가면 띄우지 않는다(호출자가 rc 93) — 「없음」으로 치지 않는다.
//! - 보유자 신원 = (pid, 출생 초, 출생 마이크로초) — pid 단독 금지(재사용).
//! - fence = 그 키에서 잡을 때마다 +1. 갱신·해제는 내 fence 일 때만(늦게 깬 옛 복원기가 새 임대를 덮지 못함).
//!   ⚠fence 로 막을 수 있는 것은 이 파일뿐이다 — 대화 jsonl 쓰기는 fence 를 검사하지 않는다(Kleppmann 2016).
//!   작성자 하나는 「띄우기 전 판정」으로만 보장한다.
//! - 저장 = 사용자 단위 한 폴더(0700) · 파일 0600 · 심볼릭 링크를 따라가지 않는다 · 어긋나면 판정 불가(U4).

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::io::Write;
use std::path::{Path, PathBuf};
use std::sync::Mutex;
use std::time::{Duration, Instant};

pub const LEASE_VERSION: u32 = 1;
/// 노브 — `off`/`0`/`false`/`no` 면 종전(600초 claim 정본) 경로. 그 밖(없음 포함) = 켬.
pub const KNOB: &str = "CYS_SESSION_LEASE";

pub fn enabled_from(v: Option<&str>) -> bool {
    !matches!(v.map(|s| s.trim().to_ascii_lowercase()).as_deref(), Some("off" | "0" | "false" | "no"))
}

pub fn enabled() -> bool {
    enabled_from(std::env::var(KNOB).ok().as_deref())
}

/// 기본 저장 폴더(순수) — 유닉스 `<HOME>/.local/state/cys/session-leases` · 윈 `<LOCALAPPDATA>/cys/session-leases`.
pub fn default_root(home: &Path, windows: bool, localappdata: Option<PathBuf>) -> PathBuf {
    if windows {
        localappdata.unwrap_or_else(|| home.join("AppData").join("Local")).join("cys").join("session-leases")
    } else {
        home.join(".local").join("state").join("cys").join("session-leases")
    }
}

/// 정규화된 대화 id(앞뒤 공백 제거 · ASCII 소문자) — 빈 값 = None(판정 밖).
pub fn norm_id(id: &str) -> Option<String> {
    let t = id.trim();
    (!t.is_empty()).then(|| t.to_ascii_lowercase())
}

/// 임대 파일 이름(hex) — 정규화 id 의 sha256(판 접두 포함).
pub fn key_hex(norm: &str) -> String {
    use sha2::{Digest, Sha256};
    let mut h = Sha256::new();
    h.update(b"v1\0");
    h.update(norm.as_bytes());
    h.finalize().iter().map(|b| format!("{b:02x}")).collect()
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct Holder {
    pub pid: u32,
    pub birth_s: u64,
    pub birth_us: u64,
}

impl Holder {
    pub fn describe(&self) -> String {
        format!("pid {}(출생 {}.{:06})", self.pid, self.birth_s, self.birth_us)
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum State {
    /// 복원기가 잡고 기동 중(작성자 아직 모름).
    Launching,
    /// 작성자 확인.
    Held,
    /// 기동 쓰기 결과 불명(⑪) — 그 좌석이 이미 잇고 있을 수 있다. 풀지 않는다.
    Unknown,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct Lease {
    pub v: u32,
    pub id: String,
    pub fence: u64,
    /// 획득마다 새 값(재사용 없음) — 파일이 지워졌다 다시 생겨 fence 가 1 부터 다시 매겨져도 옛 가드가 새 임대를 「내 것」으로 못 본다(codex 1R M2 · ABA).
    /// 옛 기록(필드 없음) = 빈 값 — 어떤 가드의 토큰과도 같지 않다.
    #[serde(default)]
    pub token: String,
    pub state: State,
    pub writer: Option<Holder>,
    pub restorer: Option<Holder>,
    pub surface_id: Option<u64>,
    pub daemon_gen: Option<String>,
    pub cfg: Option<String>,
    pub at: u64,
    /// 복원기가 그 좌석에 **저장 대화를 잇는 기동 글을 치기로 확정**했다(skt1 · codex 1R #2 — [`mark_launch_sent`] 만 켠다 · 잠금 안).
    /// 확정 전 기동 중 임대는 다른 좌석 최상위 훅의 검증된 등록([`follow`])이 이긴다(그 좌석이 이미 이 대화로 들어갔다 · 복원기는 확정에서 멈춘다).
    /// 옛 기록(필드 없음) = false.
    #[serde(default)]
    pub launch_sent: bool,
    /// 확정 **뒤** 다른 좌석 최상위 훅의 등록이 이 대화로 들어왔다(skt1 · codex 2R #2) — 복원기는 Return 직전 [`confirm_launch`] 에서 보고 멈춘다.
    #[serde(default)]
    pub contested: bool,
}

/// 보유자 하나의 생존 판정.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Liveness {
    Alive,
    Dead,
    /// 판정 불가 — 사유 코드(`probe:…` 등).
    Undecided(String),
}

/// 바깥 증거(임대 밖의 작성자 흔적).
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Evidence {
    /// 작성자로 보이는 것 — 사람이 읽는 설명.
    Seen(String),
    /// 「없음」이 확정.
    NoneConfirmed,
    Undecided(String),
}

/// 판정에 필요한 바깥 세계 — 운영 = [`RealWorld`] 위에 호출자가 데몬 조회를 얹는다 · 시험 = 가짜.
pub trait World {
    fn holder(&self, h: &Holder) -> Liveness;
    /// 기동 중·결과 불명 임대의 좌석(작성자 신원이 아직 없을 때) — 같은 데몬 세대에서 그 좌석이 살아 있는가.
    /// `strict` = 결과 불명(⑪) 임대 — 큐에 남은 기동 명령이 아직 닿을 수 있으므로 「빈 좌석」 관측은 죽음이 아니다.
    /// 죽음 = 좌석 소멸 · exited · 그 데몬 죽음 확인만(codex 4R blocking).
    fn seat(&self, surface_id: u64, daemon_gen: Option<&str>, strict: bool) -> Liveness;
    /// 그 좌석의 데몬 **등록** 대화(정규화 id · SessionStart 훅의 등록 경로 값만 — 휴리스틱 핀은 등록이 아니다) — `Ok(Some)` = 등록됨 · `Ok(None)` = 등록 없음 · `Err` = 판독 불가(다른 데몬 세대 포함).
    /// 기본 = 판독 불가(보수 · 결과 불명 임대를 풀 근거 없음).
    fn seat_conversation(&self, _surface_id: u64, _daemon_gen: Option<&str>) -> Result<Option<String>, String> {
        Err("unsupported".into())
    }
    /// 임대를 잡은 **뒤에** 보는 바깥 증거(데몬 live 세션 · 프로세스 argv).
    fn evidence(&self, norm: &str) -> Evidence;
    fn now(&self) -> u64;
}

/// 판정 결과.
#[derive(Debug)]
pub enum Decision {
    Granted(Guard),
    /// 이 프로세스가 이미 같은 키를 쥐고 있다(바깥 갈래가 잡아 넘긴 것) — 새 가드 없이 진행.
    AlreadyMine,
    Live { who: String },
    Undecided { reason: String, next: String },
}

/// 사유 코드 → 사람이 풀 수 있는 다음 행동 1줄(조건 ③).
pub fn next_action(reason: &str, norm: &str, file: &Path) -> String {
    let short: String = norm.chars().take(8).collect();
    let (code, rest) = reason.split_once(':').unwrap_or((reason, ""));
    match code {
        "probe" if rest.starts_with("unsupported") => {
            format!("이 플랫폼은 생존 판정기가 없습니다 — `{KNOB}=off` 로 종전 방식을 쓰거나 master 에 알리세요")
        }
        "probe" => {
            let pid = reason.rsplit(':').next().unwrap_or("");
            format!("`ps -p {pid} -o pid,lstart,command` 로 그 프로세스를 확인하고, 이 대화를 쓰는 중이 아니면 끈 뒤 다시 실행하세요")
        }
        "lease" if rest.starts_with("malformed") => format!(
            "임대 파일 {} 를 열어 보고, 이 대화를 쓰는 프로세스가 없으면 지운 뒤 다시 실행하세요(지우면 그 대화의 보유 기록이 사라집니다)",
            file.display()
        ),
        "lease" if rest.starts_with("outcome-unknown") => {
            let sid = reason.rsplit(':').next().unwrap_or("?");
            format!("`cys read-screen --surface surface:{sid}` 로 그 좌석이 이 대화를 잇고 있는지 보고, 아니면 그 좌석을 닫은 뒤 다시 실행하세요")
        }
        // 쓰기 실패 중 종류·소유자 어긋남(심어 둔 링크 ELOOP=62 · kind:*)은 디스크가 아니라 폴더 점검으로(독립 재검 m6).
        "lease" if rest.starts_with("write") && !rest.contains("kind:") && !rest.contains("errno:62") => format!(
            "임대 파일을 쓰지 못했습니다(디스크 공간·쓰기 권한) — `df -h {}` 로 남은 공간을, `ls -ld {}` 로 폴더 권한을 확인한 뒤 다시 실행하세요",
            file.parent().map(|p| p.display().to_string()).unwrap_or_default(),
            file.parent().map(|p| p.display().to_string()).unwrap_or_default()
        ),
        "lease" if rest == "mine-stale" => "이 실행이 잡았던 대화 임대가 그 사이 다른 프로세스로 넘어갔습니다 — `cys status` 로 그 대화를 잇는 좌석을 확인한 뒤 필요하면 다시 실행하세요".into(),
        "lease" if rest == "lock:timeout" => {
            "다른 복원이 임대 잠금을 5초 넘게 쥐고 있습니다 — `ps -axo pid,command | grep -i 'cys '` 로 멈춘 복원을 확인·종료한 뒤 다시 실행하세요".into()
        }
        "lease" if rest.starts_with("lock:kind") => format!(
            "임대 파일 {} (또는 같은 폴더의 .lock)이 일반 파일·내 소유가 아닙니다 — 확인 후 그 파일을 지운 뒤 다시 실행하세요",
            file.display()
        ),
        "lease" => format!(
            "{} 폴더가 내 소유 · 0700 · 심볼릭 링크 아님인지 확인한 뒤 다시 실행하세요",
            file.parent().map(|p| p.display().to_string()).unwrap_or_default()
        ),
        "daemon" if rest.starts_with("seat-empty-unconfirmed") => {
            let sid = reason.rsplit(':').next().unwrap_or("?");
            format!("`cys read-screen --surface surface:{sid}` 로 그 좌석이 이 대화를 잇는지 보고, 아니면 그 좌석을 닫은 뒤 다시 실행하세요(빈 셸이어도 기동 명령이 늦게 닿을 수 있어 자동으로 넘기지 않습니다)")
        }
        "daemon" if rest.starts_with("other-gen") => {
            let mut it = rest.rsplit(':');
            let sid = it.next().unwrap_or("?");
            let pid = it.next().unwrap_or("?");
            format!(
                "이 대화의 임대는 다른 cys 데몬(pid {pid})의 좌석 surface:{sid} 에 있습니다 — 그 데몬 소켓으로 `cys list` 해 그 좌석이 이 대화를 잇는지 보고, 아니면 그 좌석을 닫은 뒤 다시 실행하세요"
            )
        }
        // ★skt1(독립 검증 V6): 세대 기록이 없는 임대(옛 판이 데몬 세대를 못 읽은 채 남긴 것) = 기다려도 풀리지 않는다 — 파일을 가리킨다.
        "daemon" if rest.starts_with("gen-unknown") => format!(
            "이 대화의 임대 {} 에 데몬 세대 기록이 없어 자동으로 풀리지 않습니다 — `cys list` 로 이 대화를 잇는 좌석이 없음을 확인한 뒤 그 파일을 지우고 다시 실행하세요(급하면 `{KNOB}=off` 로 종전 방식)",
            file.display()
        ),
        "daemon" => "`cys status` 로 데몬이 응답하는지 확인한 뒤 다시 실행하세요".into(),
        "scan" => format!("{} 로 이 대화를 쥔 프로세스를 확인한 뒤 다시 실행하세요", ps_hint(&short)),
        _ => format!("`cys status` 와 {} 로 확인한 뒤 다시 실행하세요", ps_hint(&short)),
    }
}

/// 이 대화 id 를 인자로 쥔 프로세스를 찾는 명령 1줄 — 윈 = PowerShell(Win32_Process) · 그 밖 = ps(TICKET=cysr-1116-win-restore-1121).
fn ps_hint(short: &str) -> String {
    if cfg!(windows) {
        format!("PowerShell `Get-CimInstance Win32_Process | Where-Object CommandLine -match '{short}' | Select-Object ProcessId,CommandLine`")
    } else {
        format!("`ps -axo pid,command | grep -i {short}`")
    }
}

// ───────────────────────── 저장소 ─────────────────────────

/// 이 프로세스가 지금 쥔 키 → (fence, token)(가드 수명 동안). 바깥 갈래가 잡은 것을 안쪽 공통 지점이 다시 잡지 않게.
static MINE: Mutex<Option<HashMap<String, (u64, String)>>> = Mutex::new(None);

fn mine_get(norm: &str) -> Option<(u64, String)> {
    MINE.lock().unwrap_or_else(|e| e.into_inner()).as_ref().and_then(|m| m.get(norm).cloned())
}

fn mine_set(norm: &str, fence: Option<(u64, String)>) {
    let mut g = MINE.lock().unwrap_or_else(|e| e.into_inner());
    let m = g.get_or_insert_with(HashMap::new);
    match fence {
        Some(f) => {
            m.insert(norm.to_string(), f);
        }
        None => {
            m.remove(norm);
        }
    }
}

/// 이 프로세스가 지금 그 키의 임대를 쥐고 있는가(가드 수명 동안 · 등록부만).
pub fn is_mine(norm: &str) -> bool {
    mine_get(norm).is_some()
}

/// 등록부에 더해 **디스크의 현재 임대**가 내 (fence, token) 인가 — 기동 권한을 주는 자리(AlreadyMine · `--resume` 직전)는 이것으로 본다(codex 2R M2).
/// 등록부가 남아 있어도 그 사이 임대가 남에게 넘어갔으면(follow · 인수) 내 것이 아니다.
pub fn is_mine_on_disk(store: &Store, norm: &str) -> bool {
    let Some((fence, token)) = mine_get(norm) else { return false };
    matches!(store.read(&store.file_of(norm)), Ok(Some(l)) if l.fence == fence && l.token == token)
}

/// 이 프로세스가 쥔 임대(내 fence)에 좌석을 적는다 — 새 좌석이 정해진 직후(기동 명령 전). 가드를 넘겨받지 못한 안쪽 갈래용.
pub fn set_surface_mine(store: &Store, norm: &str, surface_id: u64, daemon_gen: Option<String>) -> bool {
    let Some((fence, token)) = mine_get(norm) else { return false };
    let f = store.file_of(norm);
    let Ok(_g) = store.lock() else { return false };
    let Ok(Some(mut l)) = store.read(&f) else { return false };
    if l.fence != fence || l.token != token {
        return false;
    }
    l.surface_id = Some(surface_id);
    if daemon_gen.is_some() {
        l.daemon_gen = daemon_gen;
    }
    let ok = store.write(&f, &l).is_ok();
    store.event("seat", Some(&l), norm, if ok { "" } else { "write-failed" }, now_secs());
    ok
}

#[derive(Clone, Debug)]
pub struct Store {
    root: PathBuf,
}

impl Store {
    /// 폴더 확보 — 없으면 0700 으로 만들고, 있으면 종류(폴더 · 심링크 아님) · 소유자(나) · 권한(그룹/기타 0)을 확인한다.
    /// 어긋나면 Err(사유) = 판정 불가(U4).
    pub fn open(root: &Path) -> Result<Store, String> {
        #[cfg(unix)]
        {
            use std::os::unix::fs::{DirBuilderExt, MetadataExt, PermissionsExt};
            if std::fs::symlink_metadata(root).is_err() {
                let mut b = std::fs::DirBuilder::new();
                b.recursive(true).mode(0o700);
                b.create(root).map_err(|e| format!("lease:lock:mkdir:{}", e.raw_os_error().unwrap_or(0)))?;
            }
            let md = std::fs::symlink_metadata(root).map_err(|e| format!("lease:lock:stat:{}", e.raw_os_error().unwrap_or(0)))?;
            if md.file_type().is_symlink() || !md.is_dir() {
                return Err("lease:lock:not-a-plain-dir".into());
            }
            // SAFETY: geteuid 는 부작용 없는 조회.
            if md.uid() != unsafe { libc::geteuid() } {
                return Err("lease:lock:owner".into());
            }
            if md.mode() & 0o077 != 0 {
                std::fs::set_permissions(root, std::fs::Permissions::from_mode(0o700))
                    .map_err(|_| "lease:lock:mode".to_string())?;
            }
        }
        #[cfg(not(unix))]
        {
            if std::fs::symlink_metadata(root).is_err() {
                std::fs::create_dir_all(root).map_err(|e| format!("lease:lock:mkdir:{}", e.raw_os_error().unwrap_or(0)))?;
            }
            let md = std::fs::symlink_metadata(root).map_err(|e| format!("lease:lock:stat:{}", e.raw_os_error().unwrap_or(0)))?;
            // 윈: 재분석 지점(심링크·정션)은 symlink_metadata 에서 is_symlink 로 보인다.
            if md.file_type().is_symlink() || !md.is_dir() {
                return Err("lease:lock:not-a-plain-dir".into());
            }
        }
        Ok(Store { root: root.to_path_buf() })
    }

    pub fn root(&self) -> &Path {
        &self.root
    }

    pub fn file_of(&self, norm: &str) -> PathBuf {
        self.root.join(format!("{}.lease", key_hex(norm)))
    }

    fn lock(&self) -> Result<std::fs::File, String> {
        self.lock_within(LOCK_WAIT)
    }

    /// 시한 있는 잠금 — 무기한 기다리지 않는다(잠금을 쥔 채 멈춘 프로세스가 모든 복원을 세우지 않게).
    /// 넘으면 `lease:lock:timeout`(판정 불가 U4 · rc 93).
    fn lock_within(&self, limit: Duration) -> Result<std::fs::File, String> {
        let h = open_nofollow(&self.root.join(".lock"), true, false).map_err(|e| format!("lease:lock:open:{e}"))?;
        let t0 = Instant::now();
        loop {
            match h.try_lock() {
                Ok(()) => return Ok(h),
                Err(std::fs::TryLockError::WouldBlock) if t0.elapsed() < limit => std::thread::sleep(Duration::from_millis(20)),
                Err(std::fs::TryLockError::WouldBlock) => return Err("lease:lock:timeout".into()),
                Err(std::fs::TryLockError::Error(e)) => return Err(format!("lease:lock:flock:{}", e.raw_os_error().unwrap_or(0))),
            }
        }
    }

    /// Ok(None) = 없음 · Err = 깨짐(판정 불가 U3) 또는 읽기 실패.
    fn read(&self, f: &Path) -> Result<Option<Lease>, String> {
        let mut h = match open_nofollow(f, false, false) {
            Ok(h) => h,
            Err(e) if e == "notfound" => return Ok(None),
            // 종류·소유자 어긋남 = 저장소 이상(U4) — 깨진 내용(U3)과 가른다.
            Err(e) if e.starts_with("kind:") => return Err(format!("lease:lock:{e}")),
            Err(e) => return Err(format!("lease:malformed:open:{e}")),
        };
        let mut s = String::new();
        std::io::Read::read_to_string(&mut h, &mut s).map_err(|_| "lease:malformed:read".to_string())?;
        let l: Lease = serde_json::from_str(s.trim()).map_err(|_| "lease:malformed:json".to_string())?;
        if l.v != LEASE_VERSION {
            return Err(format!("lease:malformed:version:{}", l.v));
        }
        // 의미 검증: 작성 중(held)인데 작성자가 없는 기록 = 모순 → 판정 불가(codex 6R).
        if l.state == State::Held && l.writer.is_none() {
            return Err("lease:malformed:held-without-writer".into());
        }
        Ok(Some(l))
    }

    fn write(&self, f: &Path, l: &Lease) -> Result<(), String> {
        let tmp = f.with_extension(format!("tmp-{}", std::process::id()));
        let _ = std::fs::remove_file(&tmp);
        let mut h = open_nofollow(&tmp, true, true).map_err(|e| format!("lease:write:tmp:{e}"))?;
        let body = serde_json::to_string(l).map_err(|_| "lease:write:encode".to_string())?;
        if writeln!(h, "{body}").and_then(|_| h.sync_all()).is_err() || std::fs::rename(&tmp, f).is_err() {
            let _ = std::fs::remove_file(&tmp);
            return Err("lease:write:sync-rename".into());
        }
        // 폴더 항목도 디스크에 — 정전 때 rename 이 되감기지 않게(독립 검증 F7 · 실패는 판정을 막지 않음).
        // sync_all 은 애플에서 F_FULLFSYNC 라 폴더 설명자에서 실패·과비용일 수 있다 → 폴더엔 fsync(2) 직접(독립 재검 m7).
        #[cfg(unix)]
        if let Ok(d) = std::fs::File::open(&self.root) {
            use std::os::fd::AsRawFd;
            // SAFETY: 살아 있는 설명자에 대한 fsync — 결과는 판정을 막지 않는다.
            let _ = unsafe { libc::fsync(d.as_raw_fd()) };
        }
        Ok(())
    }

    /// 사건 1줄(덧붙이기 전용) — 기록 실패는 판정을 막지 않는다.
    pub fn event(&self, ev: &str, l: Option<&Lease>, norm: &str, reason: &str, now: u64) {
        let line = serde_json::json!({
            "at": now, "ev": ev, "key": key_hex(norm).get(..12), "fence": l.map(|l| l.fence),
            "state": l.map(|l| l.state), "writer": l.and_then(|l| l.writer.clone()),
            "restorer": l.and_then(|l| l.restorer.clone()), "surface_id": l.and_then(|l| l.surface_id),
            "reason": reason, "by": std::process::id(),
        });
        if let Ok(mut h) = open_append_nofollow(&self.root.join("events.log")) {
            let _ = writeln!(h, "{line}");
        }
    }
}

/// 시한 있는 잠금의 기본 시한(codex 1R · master 지시 「잠금 시한」).
const LOCK_WAIT: Duration = Duration::from_secs(5);

/// 연 파일 설명자 기준 확인 — 일반 파일 · 내 소유 · 그룹/기타 권한 0(넓으면 0600 으로 좁힘 · 실패 = 이상). 어긋남 = `kind:…`(U4).
#[cfg(unix)]
fn check_opened(h: &std::fs::File) -> Result<(), String> {
    use std::os::unix::fs::{MetadataExt, PermissionsExt};
    let md = h.metadata().map_err(|e| format!("kind:fstat:{}", e.raw_os_error().unwrap_or(0)))?;
    // SAFETY: geteuid 는 부작용 없는 조회.
    if opened_verdict(md.file_type().is_file(), md.uid(), unsafe { libc::geteuid() }, md.mode())? {
        h.set_permissions(std::fs::Permissions::from_mode(0o600)).map_err(|_| "kind:mode".to_string())?;
    }
    Ok(())
}

/// 연 파일 판정(순수 · 독립 검증 F5 M11) — Ok(true) = 권한이 넓어 0600 으로 좁혀야 함 · Err = 종류·소유자 어긋남(U4).
fn opened_verdict(is_file: bool, uid: u32, euid: u32, mode: u32) -> Result<bool, String> {
    if !is_file {
        return Err("kind:not-regular".into());
    }
    if uid != euid {
        return Err("kind:owner".into());
    }
    Ok(mode & 0o077 != 0)
}

/// 심볼릭 링크를 따라가지 않고 · FIFO 등에서 멈추지 않게(O_NONBLOCK) 열고 · 연 설명자로 종류·소유자를 확인한다(codex 1R M5).
#[cfg(unix)]
fn open_nofollow(p: &Path, create: bool, truncate_new: bool) -> Result<std::fs::File, String> {
    use std::os::unix::fs::OpenOptionsExt;
    let mut o = std::fs::OpenOptions::new();
    o.read(true).write(create).custom_flags(libc::O_NOFOLLOW | libc::O_NONBLOCK).mode(0o600);
    if create {
        o.create(true);
    }
    if truncate_new {
        o.create_new(true);
    }
    let h = o.open(p).map_err(|e| match e.kind() {
        std::io::ErrorKind::NotFound => "notfound".to_string(),
        _ => format!("errno:{}", e.raw_os_error().unwrap_or(0)),
    })?;
    check_opened(&h)?;
    Ok(h)
}

#[cfg(not(unix))]
fn open_nofollow(p: &Path, create: bool, truncate_new: bool) -> Result<std::fs::File, String> {
    if let Ok(md) = std::fs::symlink_metadata(p) {
        if md.file_type().is_symlink() {
            return Err("symlink".into());
        }
    }
    let mut o = std::fs::OpenOptions::new();
    o.read(true).write(create);
    if create {
        o.create(true);
    }
    if truncate_new {
        o.create_new(true);
    }
    let h = o.open(p).map_err(|e| match e.kind() {
        std::io::ErrorKind::NotFound => "notfound".to_string(),
        _ => format!("errno:{}", e.raw_os_error().unwrap_or(0)),
    })?;
    if !h.metadata().map_err(|_| "kind:fstat:0".to_string())?.is_file() {
        return Err("kind:not-regular".into());
    }
    Ok(h)
}

fn open_append_nofollow(p: &Path) -> std::io::Result<std::fs::File> {
    let mut o = std::fs::OpenOptions::new();
    o.append(true).create(true);
    #[cfg(unix)]
    {
        use std::os::unix::fs::OpenOptionsExt;
        o.custom_flags(libc::O_NOFOLLOW | libc::O_NONBLOCK).mode(0o600);
    }
    let h = o.open(p)?;
    #[cfg(unix)]
    check_opened(&h).map_err(std::io::Error::other)?;
    #[cfg(not(unix))]
    if !h.metadata()?.is_file() {
        return Err(std::io::Error::other("kind:not-regular"));
    }
    Ok(h)
}

// ───────────────────────── 판정 ─────────────────────────

/// 잠금 안 판정(순수에 가까움 · 세계 조회만) — Ok(이전 fence) = 잡아도 됨 · Err(Live/Undecided).
fn judge(existing: Option<&Lease>, me: &Holder, w: &dyn World) -> Result<u64, Decision> {
    let Some(l) = existing else { return Ok(0) };
    // 1) 작성자 신원이 있으면 그것이 정본.
    if let Some(wr) = &l.writer {
        if wr == me {
            return Ok(l.fence);
        }
        return match w.holder(wr) {
            Liveness::Alive => Err(Decision::Live { who: format!("{} 가 이 대화를 쓰는 중", wr.describe()) }),
            Liveness::Dead => Ok(l.fence),
            Liveness::Undecided(r) => Err(undecided(r)),
        };
    }
    // 2) 기동 중: 복원기가 살아 있으면 그것이 보유자.
    if l.state == State::Launching {
        if let Some(r) = &l.restorer {
            match w.holder(r) {
                Liveness::Alive => {
                    return Err(Decision::Live { who: format!("복원기 {} 가 이 대화를 기동하는 중", r.describe()) })
                }
                Liveness::Undecided(why) => return Err(undecided(why)),
                Liveness::Dead => {}
            }
        }
    }
    // 3) 기동 중(복원기 죽음) · 결과 불명: 좌석이 남아 있으면 그 좌석이 잇고 있을 수 있다.
    match l.surface_id {
        // 작성자 신원 없는 임대의 좌석은 언제나 엄격 판정(codex 4R·5R): 결과 불명은 물론, 기동 중인데 복원기가 죽은 것 =
        //   기동 명령을 친 뒤 결과를 적기 전에 급사했을 수 있다(셸이 아직 에이전트를 exec 하기 전 = 빈 셸 · argv 증거 없음).
        //   정상 흐름에서는 마무리(hold)나 등록(follow)이 작성자를 적으므로, 작성자 없이 남은 임대는 이미 비정상 → 확정 종료만 죽음.
        // 여기 닿는 임대는 작성자가 없다(작성자 있으면 위에서 끝남) → 상태와 무관하게 엄격(codex 6R).
        Some(sid) => match w.seat(sid, l.daemon_gen.as_deref(), true) {
            // ★r5b(master 재검증 ⓐ) → skt1(codex r5c #1): 결과 불명 임대의 좌석이 살아 있어도 **그 좌석의 현재 대화 증거가 다른 대화**면 그 좌석은
            //   이 대화를 쓰지 않는다 — #1 방어(같은 역할 좌석 확인 못 함 = 93)가 남긴 임대가 그 좌석이 사는 동안 92 로 굳지 않게.
            //   증거 = `World::seat_conversation`(운영 = 작성자 신원으로 묶인 임대 · 등록 경로 없는 에이전트는 데몬 관측) — 등록 문자열이 아니다
            //   (가짜·헬퍼·낡은 등록이 덮는다). 증거 없음·판독 불가 = 종전(살아 있음 = 막음).
            Liveness::Alive
                if l.state == State::Unknown
                    && matches!(w.seat_conversation(sid, l.daemon_gen.as_deref()), Ok(Some(c)) if norm_id(&c).is_some_and(|c| c != l.id)) =>
            {
                Ok(l.fence)
            }
            // r5b: 결과 불명 = 그 좌석이 어느 대화인지 아직 모름(등록 전 · 훅 없는 좌석) → 무엇을 하면 풀리는지 1줄.
            Liveness::Alive => Err(Decision::Live {
                who: format!(
                    "좌석 surface:{sid} 가 이 대화를 잇는 중일 수 있음({}){}",
                    state_word(l.state),
                    if l.state == State::Unknown {
                        format!(" · 확인: 그 좌석이 막 뜬 것이면 잠시 뒤 다시 실행하세요(그 좌석의 최상위 에이전트가 다른 대화를 쓴다고 확인되면 풀립니다 — claude = SessionStart 훅 등록 · 그 밖 = 데몬 관측 · 훅 없는 좌석·등록 실패는 기다려도 안 풀림) · 계속 막히면 `cys read-screen --surface surface:{sid}` 로 그 좌석이 이 대화를 잇는지 보고, 아니면 그 좌석을 닫은 뒤 다시 실행하세요")
                    } else {
                        String::new()
                    }
                ),
            }),
            Liveness::Dead => Ok(l.fence),
            // 다른 데몬의 좌석이면 그 사유 그대로(다음 행동이 「이 데몬의 같은 번호 좌석을 닫아라」로 잘못 가지 않게).
            Liveness::Undecided(r) if l.state == State::Unknown && !r.starts_with("daemon:other-gen") => {
                Err(undecided(format!("lease:outcome-unknown:{r}:{sid}")))
            }
            Liveness::Undecided(r) => Err(undecided(r)),
        },
        // 좌석을 만들기 전에 복원기가 죽었다 = 아무것도 안 떴다.
        None if l.state == State::Launching => Ok(l.fence),
        None => Err(undecided("lease:outcome-unknown:no-seat:?".into())),
    }
}

fn state_word(s: State) -> &'static str {
    match s {
        State::Launching => "기동 중",
        State::Held => "작성 중",
        State::Unknown => "기동 결과 불명",
    }
}

fn undecided(reason: String) -> Decision {
    Decision::Undecided { reason, next: String::new() }
}

fn fill_next(d: Decision, norm: &str, f: &Path) -> Decision {
    match d {
        Decision::Undecided { reason, .. } => {
            let next = next_action(&reason, norm, f);
            Decision::Undecided { reason, next }
        }
        o => o,
    }
}

pub struct AcquireCtx<'a> {
    pub me: Holder,
    pub surface_id: Option<u64>,
    pub daemon_gen: Option<String>,
    pub cfg: Option<String>,
    pub world: &'a dyn World,
}

/// 대화 `id` 의 임대를 잡는다(복원 입구 공통). ① 잠금 안 판정·기록(launching · fence+1) ② **잡은 뒤에** 바깥 증거 ③ 증거가 있으면 되돌림.
pub fn acquire(store: &Store, id: &str, cx: &AcquireCtx) -> Decision {
    let Some(norm) = norm_id(id) else {
        return Decision::Undecided { reason: "lease:malformed:empty-id".into(), next: String::new() };
    };
    let f = store.file_of(&norm);
    if mine_get(&norm).is_some() {
        if is_mine_on_disk(store, &norm) {
            return Decision::AlreadyMine;
        }
        // 등록부는 내 것이라는데 디스크는 아니다 — 늦은 가드 · 그 사이 넘어간 임대. 띄우지 않는다.
        return fill_next(undecided("lease:mine-stale".into()), &norm, &f);
    }
    let now = cx.world.now();
    let lease = {
        let _g = match store.lock() {
            Ok(g) => g,
            Err(r) => return fill_next(undecided(r), &norm, &f),
        };
        let existing = match store.read(&f) {
            Ok(l) => l,
            Err(r) => {
                store.event("refuse_unknown", None, &norm, &r, now);
                return fill_next(undecided(r), &norm, &f);
            }
        };
        let prev_lease = existing.clone();
        let prev = match judge(existing.as_ref(), &cx.me, cx.world) {
            Ok(p) => p,
            Err(d) => {
                let (ev, why) = match &d {
                    Decision::Live { who } => ("refuse_live", who.clone()),
                    Decision::Undecided { reason, .. } => ("refuse_unknown", reason.clone()),
                    _ => ("refuse", String::new()),
                };
                store.event(ev, existing.as_ref(), &norm, &why, now);
                return fill_next(d, &norm, &f);
            }
        };
        let l = Lease {
            v: LEASE_VERSION,
            id: norm.clone(),
            fence: prev + 1,
            token: new_token(),
            state: State::Launching,
            writer: None,
            restorer: Some(cx.me.clone()),
            surface_id: cx.surface_id,
            daemon_gen: cx.daemon_gen.clone(),
            cfg: cx.cfg.clone(),
            at: now,
            launch_sent: false,
            contested: false,
        };
        if let Err(r) = store.write(&f, &l) {
            return fill_next(undecided(r), &norm, &f);
        }
        store.event(if existing.is_some() { "takeover" } else { "acquire" }, Some(&l), &norm, "", now);
        (l, prev_lease)
    };
    let (lease, prev_lease) = lease;
    mine_set(&norm, Some((lease.fence, lease.token.clone())));
    let guard = Guard {
        store: store.clone(),
        norm: norm.clone(),
        file: f.clone(),
        fence: lease.fence,
        token: lease.token.clone(),
        done: false,
        prev: prev_lease,
    };
    match cx.world.evidence(&norm) {
        Evidence::NoneConfirmed => Decision::Granted(guard),
        Evidence::Seen(who) => {
            store.event("refuse_live", Some(&lease), &norm, &who, now);
            drop(guard); // 되돌림(내 fence 일 때만 지움)
            Decision::Live { who }
        }
        Evidence::Undecided(r) => {
            store.event("refuse_unknown", Some(&lease), &norm, &r, now);
            drop(guard);
            fill_next(undecided(r), &norm, &f)
        }
    }
}

/// 잡은 임대의 되돌림 가드 — `hold`·`keep_unknown`·`keep_launching` 을 부르지 않고 버려지면 내 fence 일 때만 지운다.
#[derive(Debug)]
pub struct Guard {
    store: Store,
    norm: String,
    file: PathBuf,
    fence: u64,
    token: String,
    done: bool,
    /// 잡기 전 기록(인수했으면 죽은 보유자의 것) — 되돌림은 지우지 않고 이것을 되돌려 놓는다(사건 이력·보유 기록 보존).
    prev: Option<Lease>,
}

impl Guard {
    pub fn fence(&self) -> u64 {
        self.fence
    }

    /// 내 임대(fence · token 둘 다 같음)일 때만.
    fn is_mine(&self, l: &Lease) -> bool {
        l.fence == self.fence && l.token == self.token
    }

    /// 내 임대일 때만 고친다(잠금 안). Err = 못 고침 — `not-mine`(그 사이 정상 승계 · follow) 과 잠금·판독·쓰기 실패를 가른다.
    /// 어느 쪽이든 사건 1줄을 남긴다(codex 2R·3R minor — 마무리 실패가 조용히 사라지지 않게).
    fn update(&self, ev: &str, f: impl FnOnce(&mut Lease)) -> Result<(), String> {
        let r = (|| {
            let _g = self.store.lock()?;
            let mut l = self.store.read(&self.file)?.ok_or_else(|| "lease:gone".to_string())?;
            if !self.is_mine(&l) {
                return Err("not-mine".to_string());
            }
            f(&mut l);
            self.store.write(&self.file, &l).map(|_| l)
        })();
        match r {
            Ok(l) => {
                self.store.event(ev, Some(&l), &self.norm, "", now_secs());
                Ok(())
            }
            Err(why) => {
                self.store.event(&format!("{ev}_failed"), None, &self.norm, &why, now_secs());
                Err(why)
            }
        }
    }

    /// 좌석이 정해졌다(새 좌석 생성 직후 · 기동 명령 전).
    pub fn set_surface(&self, surface_id: u64, daemon_gen: Option<String>) -> bool {
        self.update("seat", |l| {
            l.surface_id = Some(surface_id);
            if daemon_gen.is_some() {
                l.daemon_gen = daemon_gen;
            }
        })
        .is_ok()
    }

    /// 기동 성공 — 작성자를 찾았으면 held, 못 찾았으면 좌석으로 판정되도록 launching 유지(복원기는 곧 끝난다).
    /// Err(`not-mine`) = 좌석 작성자가 이미 이어받음(정상) → Ok 로 친다 · 그 밖 Err = 기록 못 함(이미 적힌 좌석 기준 판정이 남는다).
    pub fn hold(mut self, writer: Option<Holder>) -> Result<(), String> {
        let w = writer.clone();
        let r = self.update(if w.is_some() { "commit" } else { "commit_seat" }, |l| {
            // 기동 성공 마무리 = 기동 글을 이미 쳤다(skt1 · codex 1R #2) — 확정 뒤 임대는 다른 좌석 등록이 빼앗지 않는다.
            l.launch_sent = true;
            if l.writer.is_none() {
                l.writer = w;
            }
            if l.writer.is_some() {
                l.state = State::Held;
            }
        });
        self.finish();
        r.or_else(|e| if e == "not-mine" { Ok(()) } else { Err(e) })
    }

    /// 기동 쓰기 결과 불명(⑪) — 풀지 않는다. 결과는 [`Guard::hold`] 와 같은 뜻.
    pub fn keep_unknown(mut self) -> Result<(), String> {
        let r = self.update("keep_unknown", |l| {
            if l.state != State::Held {
                l.state = State::Unknown;
            }
        });
        self.finish();
        r.or_else(|e| if e == "not-mine" { Ok(()) } else { Err(e) })
    }

    pub fn release(mut self) {
        self.do_release("release");
    }

    fn do_release(&mut self, ev: &str) {
        if self.done {
            return;
        }
        if let Ok(_g) = self.store.lock() {
            if let Ok(Some(l)) = self.store.read(&self.file) {
                if self.is_mine(&l) {
                    match &self.prev {
                        // 되돌려 놓되 fence 는 내 것 이상으로(늦게 깬 옛 가드가 이 기록을 「내 것」으로 착각하지 않게).
                        Some(p) => {
                            let mut back = p.clone();
                            back.fence = self.fence;
                            let _ = self.store.write(&self.file, &back);
                        }
                        None => {
                            let _ = std::fs::remove_file(&self.file);
                        }
                    }
                    self.store.event(ev, Some(&l), &self.norm, "", now_secs());
                }
            }
        }
        self.finish();
    }

    fn finish(&mut self) {
        self.done = true;
        if mine_get(&self.norm).is_some_and(|(f, t)| f == self.fence && t == self.token) {
            mine_set(&self.norm, None);
        }
    }
}

impl Drop for Guard {
    fn drop(&mut self) {
        self.do_release("release_drop");
    }
}

/// 세션 등록 때 임대를 따라 옮긴다(조건 ② — /clear · --continue · 새 대화 · 좌석 안 /resume).
#[derive(Debug, PartialEq, Eq)]
pub enum Follow {
    Held,
    /// 살아 있는 남이 쥐고 있다 — 빼앗지 않는다(사건만).
    Conflict(String),
    Undecided(String),
}

pub fn follow(store: &Store, id: &str, writer: &Holder, surface_id: Option<u64>, daemon_gen: Option<String>, w: &dyn World) -> Follow {
    let Some(norm) = norm_id(id) else { return Follow::Undecided("lease:malformed:empty-id".into()) };
    let f = store.file_of(&norm);
    let now = w.now();
    let Ok(_g) = store.lock() else { return Follow::Undecided("lease:lock".into()) };
    let existing = match store.read(&f) {
        Ok(l) => l,
        Err(r) => {
            store.event("follow_unknown", None, &norm, &r, now);
            return Follow::Undecided(r);
        }
    };
    let take = match &existing {
        None => Ok(0),
        Some(l) if l.writer.as_ref() == Some(writer) => Ok(l.fence.saturating_sub(1)),
        // 이 좌석을 띄운 복원기의 임대(기동 중 · 결과 불명) — 그 좌석의 작성자가 이어받는다.
        // 좌석 번호는 데몬마다 따로 매겨진다 → 같은 데몬 세대(둘 다 있음 · 같음)일 때만 같은 좌석이다(codex 1R B2).
        // 세대가 없거나 다르면 승계가 아니라 일반 판정(judge)으로 간다.
        Some(l)
            if l.writer.is_none()
                && surface_id.is_some()
                && l.surface_id == surface_id
                && l.daemon_gen.is_some()
                && l.daemon_gen == daemon_gen =>
        {
            Ok(l.fence)
        }
        // ★skt1(codex 1R #2A): 다른 좌석 복원기의 기동 중 임대인데 **기동 글 확정 전** — 이 등록(좌석 최상위 훅으로 증명된 것만 follow 에 닿는다)의
        //   좌석이 이미 이 대화로 들어갔다. 복원기를 기다리면 그 좌석과 복원기 좌석이 둘 다 쓴다 → 이 작성자가 이어받고, 복원기는
        //   [`mark_launch_sent`] 에서 내 임대가 아님을 보고 기동 글을 치지 않는다(같은 잠금 = 둘 중 하나만 이긴다).
        //   확정 뒤(launch_sent)면 빼앗지 않는다(그 복원기 좌석이 이미 이 대화로 뜨는 중 · 아래 일반 판정 = 충돌 사건).
        Some(l) if l.writer.is_none() && l.state == State::Launching && !l.launch_sent => Ok(l.fence),
        Some(l) => match judge(Some(l), writer, w) {
            Ok(p) => Ok(p),
            Err(Decision::Live { who }) => Err(Follow::Conflict(who)),
            Err(Decision::Undecided { reason, .. }) => Err(Follow::Undecided(reason)),
            Err(_) => Err(Follow::Undecided("lease:judge".into())),
        },
    };
    let out = match take {
        Ok(prev) => {
            let l = Lease {
                v: LEASE_VERSION,
                id: norm.clone(),
                fence: prev + 1,
                token: new_token(),
                state: State::Held,
                writer: Some(writer.clone()),
                restorer: None,
                surface_id,
                daemon_gen,
                cfg: existing.as_ref().and_then(|l| l.cfg.clone()),
                at: now,
                launch_sent: false,
                contested: false,
            };
            match store.write(&f, &l) {
                Ok(()) => {
                    store.event("follow", Some(&l), &norm, "", now);
                    Follow::Held
                }
                Err(r) => Follow::Undecided(r),
            }
        }
        Err(o) => {
            let why = match &o {
                Follow::Conflict(w) => w.clone(),
                Follow::Undecided(r) => r.clone(),
                Follow::Held => String::new(),
            };
            store.event(if matches!(o, Follow::Conflict(_)) { "conflict_live" } else { "follow_unknown" }, existing.as_ref(), &norm, &why, now);
            // ★skt1(codex 2R #2): 확정 뒤 기동 중 임대 = 복원기가 아직 Return 을 안 쳤을 수 있다 — 표식을 남겨 Return 직전 확인에서 멈추게 한다.
            if let Some(mut l) = existing.clone().filter(|l| matches!(o, Follow::Conflict(_)) && l.writer.is_none() && l.state == State::Launching && l.launch_sent) {
                l.contested = true;
                if store.write(&f, &l).is_ok() {
                    store.event("contested", Some(&l), &norm, &why, now);
                }
            }
            o
        }
    };
    // 같은 작성자가 쥔 다른 대화의 임대는 내려놓는다(그 대화는 더 이상 이 프로세스가 쓰지 않는다).
    if let Ok(rd) = std::fs::read_dir(store.root()) {
        for e in rd.flatten() {
            let p = e.path();
            if p == f || p.extension().and_then(|x| x.to_str()) != Some("lease") {
                continue;
            }
            if let Ok(Some(l)) = store.read(&p) {
                if l.writer.as_ref() == Some(writer) {
                    let _ = std::fs::remove_file(&p);
                    store.event("follow_release_old", Some(&l), &l.id, "", now);
                }
            }
        }
    }
    out
}

// ───────────────────────── 좌석 대화의 신원 결속(skt1 · codex r5c #1~#4) ─────────────────────────

/// 좌석 `surface_id`(데몬 세대 `daemon_gen`)에 **작성자 신원으로 묶인** 대화 — 작성 중(held) 임대 가운데 그 좌석·그 세대를 적었고
/// 작성자(pid+출생)가 지금 살아 있는 것(순수에 가까움 · 판독만 · 잠금 없음 · `probe` = 작성자 생존 판정).
///
/// 왜 등록 문자열(데몬 `registered_session_id`)이 아닌가(codex r5c #1·#2): 그 칸은 발신자·최상위 에이전트·에이전트 교체를 보지 않는다 —
/// 좌석 밖 `cys usage-register` 의 가짜 등록 · 좌석 안 `claude -p` 헬퍼 등록이 덮고, 에이전트를 바꿔도 옛 값이 남는다.
/// 이 결속은 `follow`(SessionStart 등록 뒤 · 좌석 최상위 훅으로 증명된 것만 · cys `lease_follow_on_register`)만 만들고,
/// 작성자가 죽으면(에이전트 교체 · pid 재사용 = 출생 다름) 저절로 사라진다.
///
/// Ok(Some(id)) = 그 좌석의 산 작성자가 쓰는 대화 하나 · Ok(None) = 결속 없음 · Err = 판정 불가(폴더·임대 판독 실패 · 생존 판정 불가 ·
/// 산 결속이 둘 이상 = 모순). 다른 세대·세대 없는 임대는 이 좌석 것이 아니다(좌석 번호는 데몬마다 따로 매긴다).
pub fn seat_bound_conversation(store: &Store, surface_id: u64, daemon_gen: &str, probe: &dyn Fn(&Holder) -> Liveness) -> Result<Option<String>, String> {
    let rd = std::fs::read_dir(store.root()).map_err(|e| format!("lease:bound:readdir:{}", e.raw_os_error().unwrap_or(0)))?;
    let mut found: Option<String> = None;
    for e in rd {
        let p = e.map_err(|_| "lease:bound:readdir-entry".to_string())?.path();
        if p.extension().and_then(|x| x.to_str()) != Some("lease") {
            continue;
        }
        let Some(l) = store.read(&p)? else { continue };
        if l.state != State::Held || l.surface_id != Some(surface_id) || l.daemon_gen.as_deref() != Some(daemon_gen) {
            continue;
        }
        let Some(w) = &l.writer else { continue };
        match probe(w) {
            Liveness::Alive => {}
            Liveness::Dead => continue,
            Liveness::Undecided(r) => return Err(r),
        }
        match &found {
            Some(f) if *f != l.id => return Err(format!("lease:bound:ambiguous:{surface_id}")),
            _ => found = Some(l.id.clone()),
        }
    }
    Ok(found)
}

/// 대화 `id` 가 **산 작성자에게 결속돼** 있으면 (좌석 · 데몬 세대) — 앱의 「복원됨」 판정용(codex r5c #3 · 휴리스틱 핀·8자 접두 대신).
/// Ok(None) = 결속 없음(임대 없음 · 작성 중 아님 · 작성자 죽음 · 좌석 없음) · Err = 판정 불가.
pub fn held_by_live_writer(store: &Store, id: &str, probe: &dyn Fn(&Holder) -> Liveness) -> Result<Option<(u64, Option<String>)>, String> {
    Ok(held_proof(store, id, probe)?.map(|p| (p.surface_id, p.daemon_gen)))
}

/// 앱 「복원됨」 증거(skt1 · codex 1R #4) — 결속 임대의 신원 전체. topology 판독 **앞뒤로** 두 번 읽어 같을 때만 증거다
/// (사이에 `/clear`·에이전트 교체·follow 가 결속을 바꾸면 fence·token·writer 중 하나가 달라진다).
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct HeldProof {
    pub surface_id: u64,
    pub daemon_gen: Option<String>,
    pub fence: u64,
    pub token: String,
    pub writer: Holder,
}

/// [`held_by_live_writer`] 의 신원 전체판 — Ok(None)·Err 의 뜻은 같다.
pub fn held_proof(store: &Store, id: &str, probe: &dyn Fn(&Holder) -> Liveness) -> Result<Option<HeldProof>, String> {
    let Some(norm) = norm_id(id) else { return Ok(None) };
    let Some(l) = store.read(&store.file_of(&norm))? else { return Ok(None) };
    let (Some(w), Some(sid)) = (&l.writer, l.surface_id) else { return Ok(None) };
    if l.state != State::Held {
        return Ok(None);
    }
    match probe(w) {
        Liveness::Alive => Ok(Some(HeldProof { surface_id: sid, daemon_gen: l.daemon_gen.clone(), fence: l.fence, token: l.token.clone(), writer: w.clone() })),
        Liveness::Dead => Ok(None),
        Liveness::Undecided(r) => Err(r),
    }
}

/// 두 판독(topology 앞 · 뒤)이 같은 결속일 때만 그 결속(순수 · codex 1R #4 TOCTOU).
pub fn held_proof_stable(before: Option<HeldProof>, after: Option<HeldProof>) -> Option<HeldProof> {
    match (before, after) {
        (Some(a), Some(b)) if a == b => Some(a),
        _ => None,
    }
}

/// 복원기가 저장 대화를 잇는 기동 글을 **치기 직전** — 이 프로세스가 쥔 임대(내 fence·token)에 「확정」을 적는다(skt1 · codex 1R #2).
/// `recheck` = 같은 잠금 안에서 부르는 마지막 확인(같은 역할 좌석 판정 등 · Err = 치지 않음). 잠금 안이라 [`follow`]·[`transition_unbind`] 와
/// 직렬화된다 — 확정 전에 다른 좌석 최상위 훅이 이 대화를 등록했으면 그 follow 가 임대를 가져갔으므로 여기서 `lease:taken` 으로 멈춘다.
/// Err = 치지 않음(호출자 = 빈 좌석 닫고 rc 93). 임대를 쥐지 않은 갈래(노브 끔·대화 없음)는 호출하지 않는다.
pub fn mark_launch_sent(store: &Store, norm: &str, recheck: &mut dyn FnMut() -> Result<(), String>) -> Result<(), String> {
    let Some((fence, token)) = mine_get(norm) else { return Err("lease:not-held".into()) };
    let f = store.file_of(norm);
    let _g = store.lock()?;
    let mut l = store.read(&f)?.ok_or_else(|| "lease:gone".to_string())?;
    if l.fence != fence || l.token != token {
        store.event("launch_refused", Some(&l), norm, "lease:taken", now_secs());
        return Err("lease:taken".into());
    }
    if let Err(r) = recheck() {
        store.event("launch_refused", Some(&l), norm, &r, now_secs());
        return Err(r);
    }
    l.launch_sent = true;
    store.write(&f, &l)?;
    store.event("launch_sent", Some(&l), norm, "", now_secs());
    Ok(())
}

/// 기동 글을 붙인 뒤 **Return 직전**(skt1 · codex 2R #2) — 같은 잠금 안에서 ① 임대가 아직 내 것 ② 확정 표식 있음 ③ 확정 뒤 들어온 등록 충돌
/// (`contested`) 없음 ④ `recheck`(같은 역할 좌석 재판정) Ok 일 때만 Ok. Err = Return 을 치지 않음(붙인 글은 실행되지 않는다 · 호출자 = 빈 좌석 닫고 93).
pub fn confirm_launch(store: &Store, norm: &str, recheck: &mut dyn FnMut() -> Result<(), String>) -> Result<(), String> {
    let Some((fence, token)) = mine_get(norm) else { return Err("lease:not-held".into()) };
    let f = store.file_of(norm);
    let _g = store.lock()?;
    let l = store.read(&f)?.ok_or_else(|| "lease:gone".to_string())?;
    let why = if l.fence != fence || l.token != token {
        Some("lease:taken".to_string())
    } else if !l.launch_sent {
        Some("lease:not-committed".to_string())
    } else if l.contested {
        Some("lease:contested".to_string())
    } else {
        recheck().err()
    };
    if let Some(r) = why {
        store.event("enter_refused", Some(&l), norm, &r, now_secs());
        return Err(r);
    }
    store.event("enter", Some(&l), norm, "", now_secs());
    Ok(())
}

/// 좌석 최상위 에이전트가 대화를 바꾸려 한다(SessionStart 등록 **앞** · skt1 · codex 1R #2B) — 그 작성자(`is_my_writer` = 이 등록 발신의 조상 중
/// 좌석 최상위 작성자)에게 결속된 **다른 대화**의 작성 중 임대를 「결과 불명 · 좌석 유지 · 작성자 없음」으로 바꾼다.
/// 등록이 실패해도 옛 결속이 「이 좌석 = 옛 대화」 증거로 남지 않는다(그 좌석은 결속 없음 = 같은 역할 복원 93) · 등록·follow 가 성공하면
/// 새 결속이 생기고, 옛 대화의 결과 불명 임대는 [`judge`] 가 「그 좌석의 현재 대화가 다르다」로 푼다. 바꾼 수.
pub fn transition_unbind(store: &Store, new_id: &str, is_my_writer: &dyn Fn(&Holder, Option<u64>) -> bool) -> usize {
    let Some(new_norm) = norm_id(new_id) else { return 0 };
    let Ok(_g) = store.lock() else { return 0 };
    let Ok(rd) = std::fs::read_dir(store.root()) else { return 0 };
    let mut n = 0;
    for e in rd.flatten() {
        let p = e.path();
        if p.extension().and_then(|x| x.to_str()) != Some("lease") {
            continue;
        }
        let Ok(Some(mut l)) = store.read(&p) else { continue };
        if l.state != State::Held || l.id == new_norm || !l.writer.as_ref().is_some_and(|w| is_my_writer(w, l.surface_id)) {
            continue;
        }
        l.state = State::Unknown;
        l.writer = None;
        l.restorer = None;
        l.fence += 1;
        l.token = new_token();
        l.launch_sent = false;
        l.contested = false;
        l.at = now_secs();
        if store.write(&p, &l).is_ok() {
            store.event("transition_unknown", Some(&l), &l.id, "", now_secs());
            n += 1;
        }
    }
    n
}

/// 등록 발신 계통의 3값(skt1 · codex 1R #1) — 결속을 옮기는 것은 [`Lineage::ProvenTop`] 뿐이다(판독 불가 = 옮기지 않음).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Lineage {
    /// 에이전트 실행 정확히 1개(좌석 최상위) + 그 아래(발신 쪽)에 SessionStart 훅 스크립트.
    ProvenTop,
    /// 좌석 최상위 훅이 아니라고 증명(헬퍼 = 에이전트 2개 이상 · 도구 셸 직접 호출 = 훅 없음).
    NotTop,
    /// argv 하나라도 못 읽음 · 에이전트 0 · 에이전트 이름 모름 · 계통 없음.
    Unknown,
}

/// 계통(발신의 부모 → 좌석 뿌리 순 argv)의 3값(순수).
pub fn lineage_of(cmds: &[Option<String>], bin_base: &str) -> Lineage {
    if cmds.is_empty() || bin_base.trim().is_empty() {
        return Lineage::Unknown;
    }
    match lineage_counts(cmds, bin_base) {
        None | Some((0, _)) => Lineage::Unknown,
        Some((1, true)) => Lineage::ProvenTop,
        Some(_) => Lineage::NotTop,
    }
}

/// (에이전트 실행 수 · 첫 에이전트 아래 훅 스크립트 있음) — argv 하나라도 못 읽으면 None.
fn lineage_counts(cmds: &[Option<String>], bin_base: &str) -> Option<(usize, bool)> {
    let mut agents = 0usize;
    let mut hook_below_first_agent = false;
    for c in cmds {
        let c = c.as_deref()?;
        if argv_is_agent_exec(c, bin_base) {
            agents += 1;
        } else if agents == 0 && c.split_whitespace().any(|t| t.rsplit(['/', '\\']).next() == Some(SESSION_START_HOOK_SCRIPT)) {
            hook_below_first_agent = true;
        }
    }
    Some((agents, hook_below_first_agent))
}

/// argv 한 줄이 에이전트 `bin_base` 의 실행인가(순수 · cysd `governance::cmdline_matches_agent_exec` 와 같은 규칙 — 토큰 basename 이
/// 정확히 그 이름(윈 실행 확장자는 대소문자 무시) · `.js` 실행 스크립트면 확장자 뗀 이름 · 또는 `<bin>-cli`·`<bin>-code` 패키지 세그먼트의 `.js`).
pub fn argv_is_agent_exec(cmdline: &str, bin_base: &str) -> bool {
    fn strip_win(b: &str) -> (&str, bool) {
        match b.rfind('.') {
            Some(i) if i > 0 && ["cmd", "bat", "exe", "ps1", "com"].iter().any(|e| b[i + 1..].eq_ignore_ascii_case(e)) => (&b[..i], true),
            _ => (b, false),
        }
    }
    let bin_base = bin_base.rsplit(['/', '\\']).next().unwrap_or(bin_base);
    let (want, want_win) = strip_win(bin_base);
    if want.is_empty() {
        return false;
    }
    let (pkg_cli, pkg_code) = (format!("{want}-cli"), format!("{want}-code"));
    cmdline.split_whitespace().any(|tok| {
        let base = tok.rsplit(['/', '\\']).next().unwrap_or(tok);
        let (tb, tw) = strip_win(base);
        let hit = if tw || want_win { tb.eq_ignore_ascii_case(want) } else { tb == want };
        hit || base.strip_suffix(".js").is_some_and(|b| b == want)
            || (base.ends_with(".js") && tok.contains(['/', '\\']) && tok.split(['/', '\\']).any(|seg| seg == pkg_cli || seg == pkg_code))
    })
}

/// SessionStart 훅 스크립트 basename(cysd `governance::SESSION_START_HOOK_SCRIPT` 와 같은 글자).
pub const SESSION_START_HOOK_SCRIPT: &str = "session-start.sh";

/// 등록 발신의 계통(발신의 부모 → 좌석 뿌리 순 argv)이 **좌석 최상위 에이전트의 SessionStart 훅이 아니라고 증명**되는가(순수 · cysd
/// `usage::lineage_proves_not_top_hook` 와 같은 판정) — 에이전트 실행 2개 이상(좌석 안 `claude -p` 헬퍼 · codex r5c #1-3) · 에이전트 1개인데
/// 그 아래(발신 쪽)에 훅 스크립트 없음(도구 셸의 직접 `cys usage-register`). argv 를 하나라도 못 읽었으면 None(증명 아님 · 판정 불가).
pub fn lineage_proves_not_top_hook(cmds: &[Option<String>], bin_base: &str) -> Option<bool> {
    let (agents, hook_below_first_agent) = lineage_counts(cmds, bin_base)?;
    Some(agents >= 2 || (agents == 1 && !hook_below_first_agent))
}

// ───────────────────────── 운영 세계(프로세스) ─────────────────────────

/// 재사용 없는 획득 토큰(pid · 나노초 · 프로세스 안 순번).
fn new_token() -> String {
    static N: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(0);
    let nanos = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).map(|d| d.as_nanos()).unwrap_or(0);
    format!("{}-{nanos}-{}", std::process::id(), N.fetch_add(1, std::sync::atomic::Ordering::Relaxed))
}

pub fn now_secs() -> u64 {
    std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).map(|d| d.as_secs()).unwrap_or(0)
}

pub fn holder_of(id: &crate::process_observation::Identity) -> Holder {
    Holder { pid: id.pid, birth_s: id.birth_seconds, birth_us: id.birth_microseconds }
}

/// 이 프로세스의 신원.
pub fn me() -> Option<Holder> {
    crate::process_observation::identity(std::process::id()).ok().map(|i| holder_of(&i))
}

/// 보유자 생존 — 같은 pid · 같은 출생 = 살아 있음 · pid 없음 / 같은 pid 다른 출생(재사용) = 죽음 · 그 밖 = 판정 불가.
/// 판독 실패는 1초 안에서 3회까지 다시 본다(조건 ③ · 프로세스 종료와 겹친 일시 실패를 판정 불가로 치지 않게).
pub fn probe_holder(h: &Holder) -> Liveness {
    use crate::process_observation::{identity, Failure};
    let mut last = String::new();
    for i in 0..3 {
        match identity(h.pid) {
            Ok(id) => {
                return if id.birth_seconds == h.birth_s && id.birth_microseconds == h.birth_us {
                    Liveness::Alive
                } else {
                    Liveness::Dead
                };
            }
            Err(Failure::Dead) => return Liveness::Dead,
            Err(Failure::InvalidPid) => return Liveness::Undecided(format!("probe:invalid-pid:{}", h.pid)),
            Err(Failure::UnsupportedPlatform) => return Liveness::Undecided(format!("probe:unsupported:{}", h.pid)),
            Err(Failure::Unknown { stage, os_error }) => last = format!("probe:{stage}:{}:{}", os_error.unwrap_or(0), h.pid),
            Err(Failure::Malformed(m)) => last = format!("probe:malformed-{m}:{}", h.pid),
            Err(Failure::Changed) => last = format!("probe:changed:{}", h.pid),
        }
        if i < 2 {
            std::thread::sleep(Duration::from_millis(250));
        }
    }
    Liveness::Undecided(last)
}

/// 같은 사용자 프로세스 중 argv 에 그 대화 id 를 가진 것(나와 내 조상 · `exclude` 제외) — 바깥 증거 ⓑ.
/// 같은 사용자 · 좀비 아님 · 명령줄을 못 읽은 프로세스가 1초 안 재시도 뒤에도 남으면 판정 불가(U6) · 전체 훑기가 3초를 넘으면 판정 불가(U2).
pub fn scan_argv(norm: &str, exclude: &[u32]) -> Evidence {
    // SAFETY: getuid 는 부작용 없는 조회.
    #[cfg(unix)]
    let my_uid = Some(unsafe { libc::getuid() });
    #[cfg(not(unix))]
    let my_uid: Option<u32> = None;
    // ★TICKET=cysr-1116-win-restore-1121: 윈 = 「같은 사용자」 축(win_scan) 이 붙은 훑기 · 죽음 확인은 SYNCHRONIZE 없이(LIMITED + 종료 코드).
    #[cfg(windows)]
    return scan_argv_with(norm, exclude, my_uid, win_scan::snapshot, win_scan::probe_dead);
    #[cfg(not(windows))]
    scan_argv_with(norm, exclude, my_uid, || real_snapshot(my_uid), |p| crate::process_observation::identity(p).map(|_| ()))
}

/// 실제 프로세스 훑기 한 번(sysinfo) — 판정은 [`scan_argv_with`] 가 한다. (윈 = [`win_scan::snapshot`])
#[cfg_attr(windows, allow(dead_code))]
fn real_snapshot(my_uid: Option<u32>) -> Vec<ProcView> {
    use sysinfo::{ProcessRefreshKind, ProcessStatus, ProcessesToUpdate, System, UpdateKind};
    let kind = ProcessRefreshKind::nothing().with_cmd(UpdateKind::Always).with_user(UpdateKind::Always);
    let mut sys = System::new();
    sys.refresh_processes_specifics(ProcessesToUpdate::All, true, kind);
    // 두 번째 UID 판독기는 훑기 **뒤에**, 필요할 때 한 번만(UID 결측이 있을 때).
    #[cfg(unix)]
    let owner = std::cell::OnceCell::new();
    #[cfg(not(unix))]
    let _ = my_uid;
    sys.processes()
        .iter()
        .map(|(pid, p)| ProcView {
            pid: pid.as_u32(),
            #[cfg(unix)]
            uid: p.user_id().map(|u| **u).or_else(|| owner.get_or_init(|| OwnerUid::snapshot(my_uid.unwrap_or(0))).of(pid.as_u32())),
            #[cfg(not(unix))]
            uid: None,
            skip: matches!(p.status(), ProcessStatus::Zombie) || p.thread_kind().is_some(),
            foreign: false,
            cmd: p.cmd().iter().map(|a| a.to_string_lossy().into_owned()).collect(),
        })
        .collect()
}

/// 훑기 판정(훑기·생존 판독을 주입받음 — 시험 가능 · 독립 검증 F5 M12).
pub(crate) fn scan_argv_with(
    norm: &str,
    exclude: &[u32],
    my_uid: Option<u32>,
    mut snapshot: impl FnMut() -> Vec<ProcView>,
    probe: impl Fn(u32) -> Result<(), crate::process_observation::Failure>,
) -> Evidence {
    let started = Instant::now();
    let mut unreadable: Vec<u32> = Vec::new();
    for attempt in 0..3 {
        let view = snapshot();
        // 열거 실패(빈 목록 · 나 자신도 없음) = 관측 불완전 → 판정 불가(빈 목록을 「없음」으로 치지 않는다 · codex 2R B1).
        if !view.iter().any(|p| p.pid == std::process::id()) {
            return Evidence::Undecided("scan:enumerate".into());
        }
        let (hit, unr) = classify_argv(&view, norm, exclude, my_uid);
        if let Some(seen) = hit {
            return Evidence::Seen(seen);
        }
        if started.elapsed() > Duration::from_secs(3) {
            return Evidence::Undecided("scan:timeout".into());
        }
        // 명령줄을 못 읽은 프로세스 중 「죽음 확인」된 것만 셈에서 뺀다(끝나는 중이었음) — 판독 실패는 판정 불가로 남긴다(codex 1R B1).
        unreadable = drop_confirmed_dead(unr, &probe);
        if unreadable.is_empty() {
            return Evidence::NoneConfirmed;
        }
        if attempt < 2 {
            std::thread::sleep(Duration::from_millis(250));
        }
    }
    Evidence::Undecided(format!("scan:argv:{}", unreadable.first().copied().unwrap_or(0)))
}

/// 「남의 것 확인」 표지 — 두 번째 판독기가 내 UID 목록에 없다고 확인한 프로세스.
#[cfg(unix)]
const OTHER_UID: u32 = u32::MAX;

/// sysinfo 가 UID 를 못 준 프로세스(맥: 남의 프로세스는 task 정보·BSDINFO 조회가 모두 막힘 · 11-11 실측 pid 388 root · 573 _appleevents)의
/// 소유 판정 — 두 번째 판독기. 맥 = **훑기 뒤에** 받은 `proc_listpids(PROC_UID_ONLY, 내 UID)` 집합(권한 없이 읽힘):
/// 훑기에 보였고 아직 살아 있는 내 프로세스는 반드시 그 집합에 있으므로, 없으면 남의 것(또는 이미 끝남) · 리눅스 = `/proc/<pid>` 소유자.
/// 판독기 실패 = None(판정 불가 후보로 남음 — 「남의 것」으로 치지 않는다).
#[cfg(unix)]
struct OwnerUid {
    #[cfg(target_os = "macos")]
    mine: Option<std::collections::HashSet<u32>>,
    my_uid: u32,
}

#[cfg(unix)]
impl OwnerUid {
    fn snapshot(my_uid: u32) -> Self {
        #[cfg(target_os = "macos")]
        {
            const PROC_UID_ONLY: u32 = 4; // <libproc.h> — libc 크레이트에 상수 없음
            // SAFETY: 크기 조회(널 버퍼) 뒤 넉넉한 i32 버퍼를 넘긴다 · 반환 = 채운 바이트 수.
            let need = unsafe { libc::proc_listpids(PROC_UID_ONLY, my_uid, std::ptr::null_mut(), 0) };
            let mine = (need > 0).then(|| {
                let mut buf = vec![0i32; need as usize / 4 * 2 + 64];
                let n = unsafe { libc::proc_listpids(PROC_UID_ONLY, my_uid, buf.as_mut_ptr().cast(), (buf.len() * 4) as i32) };
                (n > 0 && (n as usize) < buf.len() * 4).then(|| buf[..n as usize / 4].iter().filter(|p| **p > 0).map(|p| *p as u32).collect())
            });
            OwnerUid { mine: mine.flatten(), my_uid }
        }
        #[cfg(not(target_os = "macos"))]
        {
            OwnerUid { my_uid }
        }
    }

    fn of(&self, pid: u32) -> Option<u32> {
        #[cfg(target_os = "macos")]
        {
            self.mine.as_ref().map(|s| if s.contains(&pid) { self.my_uid } else { OTHER_UID })
        }
        #[cfg(not(target_os = "macos"))]
        {
            use std::os::unix::fs::MetadataExt;
            let _ = self.my_uid;
            std::fs::metadata(format!("/proc/{pid}")).ok().map(|m| m.uid())
        }
    }
}

/// 훑기 한 번의 프로세스 한 줄(순수 판정용 · 시험 가능).
#[derive(Clone, Debug)]
pub(crate) struct ProcView {
    pub pid: u32,
    /// None = UID 판독 실패.
    pub uid: Option<u32>,
    /// 좀비 · 스레드.
    pub skip: bool,
    /// 이 사용자의 프로세스가 아님 확정(윈 = [`win_foreign`] · 유닉스 = 늘 false — UID 축이 같은 일을 한다).
    pub foreign: bool,
    /// 빈 값 = 명령줄을 못 읽음.
    pub cmd: Vec<String>,
}

// ───────── 윈 「같은 사용자」 축 (TICKET=cysr-1116-win-restore-1121 · master#5ff009c9) ─────────
// 결함: 윈은 UID 축이 없어(my_uid = None) SYSTEM·보호 프로세스까지 훑었고, 그 명령줄은 못 읽고(sysinfo = PEB 를 VM_READ 로 읽은 뒤에만 채움)
//   죽음 확인(OpenProcess LIMITED|SYNCHRONIZE)도 ACCESS_DENIED 라 남아 → 언제나 Undecided("scan:argv:<첫 읽기 불가 pid>") → 저장 대화가 있는
//   모든 역할 93(윈 실기 11-21 · 4좌석 · 주인 pid = csrss·lsass·Registry). 판정은 아래 순수 함수 · 사실 수집만 `win_scan`(윈 전용).

/// 프로세스 하나의 존재 — 핸들 열기 오류는 [`open_err_kind`] 로만 바꾼다(거부 = 남의 것 증거 아님 · master#d6185ede 규칙 3).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum WinOpen {
    Opened,
    /// ERROR_INVALID_PARAMETER — 그 pid 가 이미 없다.
    Gone,
    /// 그 밖 오류(ACCESS_DENIED 포함) — 남의 것으로 단정하지 않는다.
    Failed,
    /// 열렸으나 그 행의 사실을 못 믿음 — 핸들 생성 시각 ≠ 열거 표 CreateTime(100ns · pid 재사용) ∨ 핸들 토큰 SID 못 읽음
    /// (master#c699b44d 1 · codex 2R H1). 남의 것으로 치지 않는다(세션 규칙도 안 탐) = 대상 → 명령줄 못 읽으면 판정 불가.
    Unverified,
}

/// OpenProcess 오류 코드 → 존재 사실(순수 · 뮤턴트 MC). 87 = ERROR_INVALID_PARAMETER = 없음 · 그 밖 = 판독 실패.
pub(crate) fn open_err_kind(code: u32) -> WinOpen {
    if code == 87 {
        WinOpen::Gone
    } else {
        WinOpen::Failed
    }
}

/// 토큰 사용자 SID 대조 — 윈의 「uid 축」 정본.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum WinSid {
    Same,
    Other,
    /// 내 SID 나 그 프로세스 SID 를 못 얻었거나 무효 — 남의 것으로 치지 않는다.
    Unknown,
}

/// 원시 SID 바이트 형식(IsValidSid 와 같은 꼴 · 순수): 개정 1 · 하위 권한 ≤ 15 · 길이 = 8 + 4n.
pub(crate) fn sid_valid(b: &[u8]) -> bool {
    b.len() >= 8 && b[0] == 1 && b[1] <= 15 && b.len() == 8 + 4 * b[1] as usize
}

/// SID 대조(순수 · 뮤턴트 ME): 한쪽이라도 없음·무효 = 모름(「무효」와 「다름」을 가른다 · 규칙 5) · 바이트 같음 = 같음 · 그 밖 = 다름.
pub(crate) fn sid_verdict(me: Option<&[u8]>, them: Option<&[u8]>) -> WinSid {
    match (me, them) {
        (Some(a), Some(b)) if sid_valid(a) && sid_valid(b) => {
            if a == b {
                WinSid::Same
            } else {
                WinSid::Other
            }
        }
        _ => WinSid::Unknown,
    }
}

/// 죽음 확인(순수 · 뮤턴트 MD) — `open` = LIMITED 핸들 열기(Err = 오류 코드) · `exit` = GetExitCodeProcess(None = 실패).
/// 없음 = 죽음 · 종료 코드 ≠ STILL_ACTIVE(259) = 죽음 · 그 밖 실패 = 판독 실패(죽음 아님 · 규칙 5). 종료 코드 259 로 끝난 것 = 살아 있음(보호).
pub(crate) fn probe_verdict(open: Result<(), u32>, exit: Option<u32>) -> Result<(), crate::process_observation::Failure> {
    use crate::process_observation::Failure;
    match open {
        Err(code) if open_err_kind(code) == WinOpen::Gone => Err(Failure::Dead),
        Err(code) => Err(Failure::Unknown { stage: "OpenProcess(limited)", os_error: Some(code as i32) }),
        Ok(()) => match exit {
            None => Err(Failure::Unknown { stage: "GetExitCodeProcess", os_error: None }),
            Some(259) => Ok(()),
            Some(_) => Err(Failure::Dead),
        },
    }
}

/// 프로세스 하나에 대해 모은 윈 사실 — 세션 = SystemProcessInformation(핸들 없음) · SID = WTS(핸들 없음) → 없으면 LIMITED 핸들 토큰.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) struct WinFacts {
    pub open: WinOpen,
    pub sid: WinSid,
    /// None = 판독 실패(세션 규칙 꺼짐).
    pub session: Option<u32>,
    /// 생성 시각(FILETIME 100ns · 1601 기준) — 세션과 **같은 표**(SystemProcessInformation CreateTime)에서 · None = 못 읽음.
    /// 명령줄 판독 때 [`birth_matches`] 로 대조한다(pid 재사용 · master#d6185ede 규칙 8).
    pub birth: Option<u64>,
}

/// 출생 대조(순수 · 규칙 8 · master#c699b44d 2 · 뮤턴트 MB) — 열거 표(SystemProcessInformation) CreateTime 과 그 사실·명령줄을 읽은
/// 핸들의 GetProcessTimes 생성 시각이 **100ns 그대로** 같을 때만 참(초로 자르면 같은 1초 안의 pid 재사용을 같은 프로세스로 받는다 · codex 2R H2).
/// 둘 중 하나라도 없음 = 거짓(= 그 사실·명령줄을 쓰지 않음 → 판정 불가 쪽).
pub(crate) fn birth_matches(table_ticks: Option<u64>, handle_ticks: Option<u64>) -> bool {
    match (table_ticks, handle_ticks) {
        (Some(a), Some(b)) => a == b,
        _ => false,
    }
}

/// 핸들 하나로 본 것 — Ok = 열림(그 핸들의 생성 ticks · 그 핸들 토큰 SID 바이트 · 못 읽음 = None) · Err = OpenProcess 오류 코드.
pub(crate) type WinHandleView = Result<(Option<u64>, Option<Vec<u8>>), u32>;

/// ★수집 순서 불변식(master#d82fcb00 · 바꾸지 마라 — 시험 W21 `collect_rows` 호출 순서 · 뮤턴트 MO):
///   ① SPI 표(세션·CreateTime) → ② WTS 표(SID) → ③ OpenProcess(LIMITED) → ④ 그 핸들 GetProcessTimes CreationTime == ① CreateTime(100ns).
///   ④ 가 같으면 그 프로세스는 ①~③ 내내 같은 프로세스였다(살아 있는 동안 pid 는 재사용되지 않고, 재사용이면 CreateTime 이 달라진다) →
///   ①~③ 사이에 찍힌 ② 의 SID 도 그 프로세스의 것이다. ② 가 ③ 뒤로 가면 이 추론이 무너진다(② 가 새 주인을 볼 수 있음).

/// 열린 행(④ 출생 일치)의 SID 출처(순수 · 뮤턴트 MH1a·MWF) — 그 핸들 토큰 SID(형식 유효) 우선 · 토큰 실패면 ② WTS SID · 둘 다 없으면 None(= 모름).
pub(crate) fn sid_for_opened<'a>(token: Option<&'a [u8]>, wts: Option<&'a [u8]>) -> Option<&'a [u8]> {
    token.filter(|t| sid_valid(t)).or(wts)
}

/// 한 행의 사실 채택(순수 · master#c699b44d 1 → master#d82fcb00 정본 · codex 2R H1 · 뮤턴트 MH1b·MH1d·MH1e) — `spi` = ① 표의 (세션, CreateTime).
/// ⑴ 열림: ④ 핸들 생성 시각 == 표 CreateTime(100ns) → SID = [`sid_for_opened`](토큰 → WTS → 모름) · 어긋남(핸들·표 생성 시각 결측 포함) =
///   [`WinOpen::Unverified`](판정 불가 쪽 · 세션 규칙 안 탐). ⑵ 못 엶 = 오류 매핑 + ② WTS SID(출생 대조 불가 · 스냅샷 한계 · REPORT 7-5).
pub(crate) fn row_facts(spi: Option<(u32, Option<u64>)>, handle: WinHandleView, wts: Option<&[u8]>, me: Option<&[u8]>) -> WinFacts {
    let (session, birth) = spi.map_or((None, None), |(s, b)| (Some(s), b));
    match handle {
        Err(code) => WinFacts { open: open_err_kind(code), sid: sid_verdict(me, wts), session, birth },
        Ok((handle_birth, token)) => {
            if !birth_matches(birth, handle_birth) {
                WinFacts { open: WinOpen::Unverified, sid: WinSid::Unknown, session, birth }
            } else {
                WinFacts { open: WinOpen::Opened, sid: sid_verdict(me, sid_for_opened(token.as_deref(), wts)), session, birth }
            }
        }
    }
}

/// 윈 훑기 한 번의 수집 골격(순수 · 시험 W21) — 위 순서 불변식 ①②③④ 를 **이 함수 하나가** 강제한다:
/// `table`(①) → 내 세션 → `wts`(②) → 행마다 `handle`(③④ · 열기 + 그 핸들 생성 시각·토큰) → [`row_facts`]. ① 을 못 읽으면 None.
pub(crate) fn collect_rows(
    table: impl FnOnce() -> Option<std::collections::HashMap<u32, (u32, Option<u64>)>>,
    wts: impl FnOnce(Option<u32>) -> std::collections::HashMap<u32, Vec<u8>>,
    handle: impl Fn(u32) -> WinHandleView,
    me: Option<&[u8]>,
) -> Option<(Option<u32>, Vec<(u32, WinFacts)>)> {
    let table = table()?;
    let my_session = table.get(&std::process::id()).map(|&(s, _)| s);
    let wts = wts(my_session);
    let opened: Vec<(u32, (u32, Option<u64>), WinHandleView)> = table.iter().map(|(&pid, &spi)| (pid, spi, handle(pid))).collect();
    let rows = opened.into_iter().map(|(pid, spi, h)| (pid, row_facts(Some(spi), h, wts.get(&pid).map(Vec::as_slice), me))).collect();
    Some((my_session, rows))
}

/// WTSEnumerateProcessesExW 의 「모든 세션」 값.
pub(crate) const WTS_ANY_SESSION: u32 = 0xFFFF_FFFE;

/// WTS 표(순수 · master#c699b44d 3 · 검증 R2 ② · 뮤턴트 MW) — 모든 세션으로 먼저 부르고, 실패하면 **내 세션 id 로 한 번 더**.
/// 근거(문서 · 확신 중): 「The caller must be a member of the Administrators group to enumerate processes that are running under
/// another user session.」(learn.microsoft.com wtsapi32 WTSEnumerateProcessesExW) — 관리자 요구는 **다른** 사용자 세션에만 걸린다.
/// 비관리자가 내 세션으로 부르면 내 세션 SYSTEM 프로세스(winlogon) SID 까지 주는지는 실기 확인 전(REPORT 5 · 윈 실기 1).
pub(crate) fn wts_any_then_mine<M>(enumerate: impl Fn(u32) -> Option<M>, my_session: Option<u32>) -> Option<M> {
    enumerate(WTS_ANY_SESSION).or_else(|| my_session.and_then(&enumerate))
}

/// 윈 프로세스 분류(순수 · master#d6185ede 정본) — Some(true) = 남의 것(건너뜀) · Some(false) = 훑기 대상 · None = 사라짐(목록에서 뺌).
/// 1 SID 같음(확정) = 어떤 경우에도 남의 것 아님(세션·핸들 거부와 무관 — 세션 0 의 같은 사용자 claude(OpenSSH·예약 작업)를 건너뛰면 작성자 둘).
/// 2 남의 것 = pid 0·4 ∨ SID 다름(확정) ∨ (SID 모름 ∧ 세션 0 ∧ 내 세션 ≠ 0).
/// 3 그 밖(핸들 거부 단독 · SID 모름 ∧ 세션 0 아님) = 대상 — 명령줄을 못 읽으면 판정 불가(보호).
pub(crate) fn win_foreign(pid: u32, f: &WinFacts, my_session: Option<u32>) -> Option<bool> {
    if pid == 0 || pid == 4 {
        return Some(true);
    }
    if f.open == WinOpen::Gone {
        return None;
    }
    if f.open == WinOpen::Unverified {
        return Some(false);
    }
    match f.sid {
        WinSid::Same => Some(false),
        WinSid::Other => Some(true),
        WinSid::Unknown => Some(f.session == Some(0) && my_session.is_some_and(|m| m != 0)),
    }
}

/// 윈 훑기 한 줄 조립(순수 · 시험 가능) — 남의 것이 아니면 `self_read`(우리 LIMITED 핸들 하나 · 생성 ticks 와 명령줄을 같은 핸들에서)로 읽는다.
/// ★윈에서는 sysinfo 명령줄을 쓰지 않는다(master#c699b44d 2 · codex 2R H2 — sysinfo 첫 훑기 핸들이 끝난 앞 프로세스의 명령줄을 줄 수 있음).
/// 명령줄은 그 핸들의 생성 시각이 `f.birth`(열거 표 CreateTime)와 100ns 그대로 같을 때만 쓴다 · 다르거나 못 읽으면 빈 값(= 판정 불가 후보).
pub(crate) fn win_view(
    pid: u32,
    f: &WinFacts,
    my_session: Option<u32>,
    self_read: impl Fn(u32) -> Option<(u64, Vec<String>)>,
) -> Option<ProcView> {
    let foreign = win_foreign(pid, f, my_session)?;
    let cmd = if foreign {
        Vec::new()
    } else {
        match self_read(pid) {
            Some((born, argv)) if birth_matches(f.birth, Some(born)) => argv,
            _ => Vec::new(),
        }
    };
    Some(ProcView { pid, uid: None, skip: false, foreign, cmd })
}

/// 윈 사실 수집(얇은 FFI · 판정·오류 매핑은 위 순수 함수) — 핸들 열기는 `PROCESS_QUERY_LIMITED_INFORMATION` 만(SYNCHRONIZE 없음).
/// 행 목록 = SystemProcessInformation 표 하나(세션·CreateTime 도 같은 표) · 그 뒤 WTS(SID) · 행마다 LIMITED 핸들(생성 시각 대조 → 토큰 SID) ·
/// 명령줄 = 다시 LIMITED 핸들(생성 시각 대조 → 판독). 남는 한계(스냅샷): 못 연 행의 WTS SID 는 생성 시각에 묶이지 않는다 · 표 **뒤에**
/// 태어난 프로세스는 못 본다(REPORT 7-5).
#[cfg(windows)]
mod win_scan {
    use super::{collect_rows, probe_verdict, win_view, wts_any_then_mine, ProcView};
    use crate::process_observation::Failure;
    use std::collections::HashMap;
    use windows_sys::Wdk::System::SystemInformation::NtQuerySystemInformation;
    use windows_sys::Win32::Foundation::{CloseHandle, GetLastError, FILETIME, HANDLE};
    use windows_sys::Win32::Security::{GetTokenInformation, TokenUser, TOKEN_QUERY, TOKEN_USER};
    use windows_sys::Win32::System::RemoteDesktop::{WTSEnumerateProcessesExW, WTSFreeMemoryExW, WTSTypeProcessInfoLevel1, WTS_CURRENT_SERVER_HANDLE, WTS_PROCESS_INFO_EXW};
    use windows_sys::Win32::System::Threading::{GetCurrentProcess, GetExitCodeProcess, GetProcessTimes, OpenProcess, OpenProcessToken, PROCESS_QUERY_LIMITED_INFORMATION};
    use windows_sys::Win32::System::WindowsProgramming::SYSTEM_PROCESS_INFORMATION;

    const SYSTEM_PROCESS_INFORMATION_CLASS: i32 = 5;
    const STATUS_INFO_LENGTH_MISMATCH: i32 = 0xC000_0004_u32 as i32;

    pub(super) struct Owned(HANDLE);
    impl Drop for Owned {
        fn drop(&mut self) {
            // SAFETY: 이 값이 OpenProcess/OpenProcessToken 으로 받은 핸들을 소유한다.
            unsafe { CloseHandle(self.0) };
        }
    }

    pub(super) fn open(pid: u32) -> Result<Owned, u32> {
        // SAFETY: 평범한 Win32 호출 · null 반환은 아래에서 처리.
        let h = unsafe { OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, 0, pid) };
        if h.is_null() {
            // SAFETY: 직전 호출의 스레드 오류 값.
            return Err(unsafe { GetLastError() });
        }
        Ok(Owned(h))
    }

    /// PSID → 원시 바이트(형식 검사는 [`super::sid_valid`] 가 다시 한다).
    fn sid_bytes(psid: *mut core::ffi::c_void) -> Option<Vec<u8>> {
        if psid.is_null() {
            return None;
        }
        // SAFETY: OS 가 준 SID 포인터 — 머리 2바이트(개정 · 하위 권한 수)를 읽고 그 길이만큼만 복사한다.
        let n = unsafe { *(psid as *const u8).add(1) } as usize;
        if n > 15 {
            return None;
        }
        Some(unsafe { std::slice::from_raw_parts(psid as *const u8, 8 + 4 * n) }.to_vec())
    }

    /// 토큰 사용자 SID — None = 토큰을 못 열었거나 못 읽음.
    pub(super) fn token_sid(process: HANDLE) -> Option<Vec<u8>> {
        let mut tok: HANDLE = std::ptr::null_mut();
        // SAFETY: process = 유효한 프로세스 핸들(또는 의사 핸들) · tok = 출력 칸.
        if unsafe { OpenProcessToken(process, TOKEN_QUERY, &mut tok) } == 0 {
            return None;
        }
        let tok = Owned(tok);
        let mut need = 0u32;
        // SAFETY: 크기 조회(버퍼 없음).
        unsafe { GetTokenInformation(tok.0, TokenUser, std::ptr::null_mut(), 0, &mut need) };
        if need == 0 || need > 4096 {
            return None;
        }
        let mut buf = vec![0u64; (need as usize).div_ceil(8)];
        // SAFETY: buf 는 need 바이트 이상 · 정렬 8.
        if unsafe { GetTokenInformation(tok.0, TokenUser, buf.as_mut_ptr().cast(), (buf.len() * 8) as u32, &mut need) } == 0 {
            return None;
        }
        // SAFETY: buf 는 TOKEN_USER 로 시작한다.
        sid_bytes(unsafe { (*(buf.as_ptr() as *const TOKEN_USER)).User.Sid })
    }

    /// SYSTEM_PROCESS_INFORMATION 의 CreateTime 자리 — windows-sys 는 `Reserved1[48]`(구조체 8..56) 로 숨긴다.
    /// 원형(ntapi 0.4.3 ntexapi.rs = phnt): NextEntryOffset 0 · NumberOfThreads 4 · WorkingSetPrivateSize 8 · HardFaultCount 16 ·
    /// NumberOfThreadsHighWatermark 20 · CycleTime 24 · **CreateTime 32**(LARGE_INTEGER · FILETIME 100ns) · UserTime 40 · KernelTime 48 · ImageName 56.
    /// ∴ Reserved1[24..32]. 아래 두 단언이 windows-sys 배치(Reserved1 = 8 · ImageName = 56)가 원형과 같음을 컴파일 때 못 박는다.
    const CREATE_TIME_IN_RESERVED1: std::ops::Range<usize> = 24..32;
    const _: () = assert!(std::mem::offset_of!(SYSTEM_PROCESS_INFORMATION, Reserved1) == 8);
    const _: () = assert!(std::mem::offset_of!(SYSTEM_PROCESS_INFORMATION, ImageName) == 56);

    /// pid → (세션, 생성 시각 ticks)(SystemProcessInformation · 핸들 없음 · 같은 표). None = 표를 못 읽음 · 생성 시각 음수 = None.
    pub(super) fn nt_sessions() -> Option<HashMap<u32, (u32, Option<u64>)>> {
        let mut buf = vec![0u64; 1 << 16];
        for _ in 0..4 {
            let mut need = 0u32;
            // SAFETY: 쓰기 가능한 버퍼 · need = 필요한 크기.
            let st = unsafe { NtQuerySystemInformation(SYSTEM_PROCESS_INFORMATION_CLASS, buf.as_mut_ptr().cast(), (buf.len() * 8) as u32, &mut need) };
            if st == STATUS_INFO_LENGTH_MISMATCH {
                buf.resize((need as usize + 65_536).div_ceil(8), 0);
                continue;
            }
            if st < 0 {
                return None;
            }
            let total = buf.len() * 8;
            let base = buf.as_ptr() as *const u8;
            let mut off = 0usize;
            let mut m = HashMap::new();
            loop {
                if off + std::mem::size_of::<SYSTEM_PROCESS_INFORMATION>() > total {
                    return None;
                }
                // SAFETY: off..off+size_of 는 버퍼 안(위 검사) · 정렬은 가정하지 않고 값으로 복사한다
                // (sysinfo 0.33.1 windows/system.rs 292~294 와 같은 방식: 「read_unaligned is necessary to avoid misaligned pointer dereference」 · 검증 R2 하).
                let e = unsafe { std::ptr::read_unaligned(base.add(off) as *const SYSTEM_PROCESS_INFORMATION) };
                let mut ct = [0u8; 8];
                ct.copy_from_slice(&e.Reserved1[CREATE_TIME_IN_RESERVED1]);
                m.insert(e.UniqueProcessId as usize as u32, (e.SessionId, u64::try_from(i64::from_ne_bytes(ct)).ok()));
                if e.NextEntryOffset == 0 {
                    return Some(m);
                }
                off += e.NextEntryOffset as usize;
            }
        }
        None
    }

    /// pid → 사용자 SID(WTSEnumerateProcessesExW level 1 · 핸들 없음) — `session` = 세션 id 또는 [`super::WTS_ANY_SESSION`]. None = 호출 실패.
    pub(super) fn wts_sids(session: u32) -> Option<HashMap<u32, Vec<u8>>> {
        let mut level = 1u32;
        let mut p: *mut WTS_PROCESS_INFO_EXW = std::ptr::null_mut();
        let mut n = 0u32;
        // SAFETY: 출력 칸 둘 · 성공하면 p 를 WTSFreeMemoryExW 로 돌려준다.
        if unsafe { WTSEnumerateProcessesExW(WTS_CURRENT_SERVER_HANDLE, &mut level, session, (&mut p as *mut *mut WTS_PROCESS_INFO_EXW).cast(), &mut n) } == 0 || p.is_null() {
            return None;
        }
        // SAFETY: p 는 n 개 항목 배열.
        let rows = unsafe { std::slice::from_raw_parts(p, n as usize) };
        let m = rows.iter().filter_map(|e| sid_bytes(e.pUserSid).map(|b| (e.ProcessId, b))).collect();
        // SAFETY: 위에서 받은 배열을 그대로 돌려준다.
        unsafe { WTSFreeMemoryExW(WTSTypeProcessInfoLevel1, p.cast(), n) };
        Some(m)
    }

    /// 핸들 생성 시각(GetProcessTimes CreationTime · FILETIME 100ns) — None = 실패.
    fn creation_ticks(process: HANDLE) -> Option<u64> {
        let zero = FILETIME { dwLowDateTime: 0, dwHighDateTime: 0 };
        let (mut c, mut e, mut k, mut u) = (zero, zero, zero, zero);
        // SAFETY: 열린 핸들 · 쓰기 가능한 FILETIME 출력 넷.
        (unsafe { GetProcessTimes(process, &mut c, &mut e, &mut k, &mut u) } != 0).then(|| ((c.dwHighDateTime as u64) << 32) | c.dwLowDateTime as u64)
    }

    /// 행 하나의 ③④ — 열면 그 핸들에서 생성 시각·토큰 SID 를 읽는다(채택 여부 = [`super::row_facts`] · 순서 = [`collect_rows`]).
    fn handle_view(pid: u32) -> super::WinHandleView {
        open(pid).map(|h| (creation_ticks(h.0), token_sid(h.0)))
    }

    /// 한 행의 사실(윈 러너 시험용 · `collect_rows` 의 한 행과 같은 길) — 표·WTS 는 호출자가 ①② 순서로 먼저 읽어 넘긴다.
    #[cfg(test)]
    pub(super) fn facts(pid: u32, me: Option<&[u8]>, sessions: &HashMap<u32, (u32, Option<u64>)>, wts: &HashMap<u32, Vec<u8>>) -> super::WinFacts {
        super::row_facts(sessions.get(&pid).copied(), handle_view(pid), wts.get(&pid).map(Vec::as_slice), me)
    }

    /// LIMITED 핸들 하나의 (생성 ticks, 명령줄)(`process_observation::argv_limited`) — sysinfo 명령줄을 못 쓴 남의 것 아닌 프로세스만.
    pub(super) fn self_read(pid: u32) -> Option<(u64, Vec<String>)> {
        crate::process_observation::argv_limited(pid)
            .ok()
            .map(|(born, argv)| (born, argv.iter().map(|a| String::from_utf8_lossy(a).into_owned()).collect()))
    }

    /// 훑기 한 번 — 수집 순서(① 표 → ② WTS → ③④ 행마다 핸들)는 [`collect_rows`] 가 강제한다(순서 불변식 · [`super::sid_for_opened`] 위 주석).
    /// 행 = SystemProcessInformation 표(못 읽으면 빈 목록 → `scan:enumerate` 판정 불가) · 남의 것은 명령줄을 읽지 않는다.
    pub(super) fn snapshot() -> Vec<ProcView> {
        // SAFETY: GetCurrentProcess = 닫지 않는 의사 핸들.
        let me = token_sid(unsafe { GetCurrentProcess() });
        let Some((my_session, rows)) = collect_rows(
            nt_sessions,
            |my| wts_any_then_mine(wts_sids, my).unwrap_or_default(),
            handle_view,
            me.as_deref(),
        ) else {
            return Vec::new();
        };
        rows.into_iter().filter_map(|(pid, f)| win_view(pid, &f, my_session, self_read)).collect()
    }

    /// 죽음 확인(이 판정 한정 · SYNCHRONIZE 없음) — 판정은 [`probe_verdict`].
    pub(super) fn probe_dead(pid: u32) -> Result<(), Failure> {
        match open(pid) {
            Err(code) => probe_verdict(Err(code), None),
            Ok(h) => {
                let mut code = 0u32;
                // SAFETY: 열린 핸들 · 출력 칸 하나.
                let ok = unsafe { GetExitCodeProcess(h.0, &mut code) } != 0;
                probe_verdict(Ok(()), ok.then_some(code))
            }
        }
    }
}

/// 윈 러너 실시험(master#d6185ede 규칙 6 · 독립 검증 중-3 ⓐ~ⓔ) — `win_scan` 의 FFI 사실 수집을 **실제로** 지난다(맥·리눅스에서는 컴파일도 안 됨).
/// CI = windows-health 의 `cargo test --lib session_lease::win_tests::`(0 매치 = 붉음 · ci-branch FILTERED_CARGO_REQUIRED).
#[cfg(all(test, windows))]
mod win_tests {
    use super::win_scan::{facts, nt_sessions, open, probe_dead, self_read, token_sid, wts_sids};
    use super::{open_err_kind, scan_argv, win_foreign, wts_any_then_mine, Evidence, WinOpen, WinSid};
    use crate::process_observation::Failure;

    fn random_id(tag: &str) -> String {
        let n = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).map(|d| d.as_nanos()).unwrap_or(0);
        format!("{:x}-{:x}-{tag}", n, std::process::id())
    }

    /// ⓐ 나 자신 = 열림(= 핸들 생성 시각 == 표 CreateTime 100ns · CreateTime 오프셋 실증) · SID 같음 · 내 세션(Some) · 남의 것 아님 · 자체 판독 출생 == 표.
    #[test]
    fn self_facts_are_opened_same_sid_my_session_and_birth_matches() {
        let sessions = nt_sessions().expect("SystemProcessInformation 을 못 읽었다");
        let my_session = sessions.get(&std::process::id()).map(|&(s, _)| s);
        let wts = wts_any_then_mine(wts_sids, my_session).unwrap_or_default();
        // SAFETY: GetCurrentProcess = 닫지 않는 의사 핸들.
        let me_sid = token_sid(unsafe { windows_sys::Win32::System::Threading::GetCurrentProcess() });
        assert!(me_sid.is_some(), "내 토큰 SID 를 못 읽었다");
        let me = std::process::id();
        let f = facts(me, me_sid.as_deref(), &sessions, &wts);
        assert_eq!(f.open, WinOpen::Opened, "{f:?} — Unverified 면 표 CreateTime(Reserved1[24..32]) ≠ 핸들 GetProcessTimes(100ns) 또는 토큰 실패");
        assert_eq!(f.sid, WinSid::Same, "{f:?}");
        assert!(my_session.is_some() && f.session == my_session, "{f:?} · 표 = {my_session:?}");
        assert_eq!(win_foreign(me, &f, my_session), Some(false));
        let id = crate::process_observation::identity(me).expect("내 신원");
        let unix = f.birth.and_then(|t| t.checked_sub(116_444_736_000_000_000)).map(|t| (t / 10_000_000, (t % 10_000_000) / 10));
        assert_eq!(unix, Some((id.birth_seconds, id.birth_microseconds)), "표 CreateTime {:?} ↔ process_observation::identity", f.birth);
        let (born, argv) = self_read(me).expect("내 명령줄을 LIMITED 핸들로 못 읽었다");
        assert!(!argv.is_empty());
        assert_eq!(Some(born), f.birth, "자체 판독 핸들 출생 ≠ 표 CreateTime(100ns)");
    }

    /// ⓑ pid 4(System) = 남의 것.
    #[test]
    fn system_pid_4_is_foreign() {
        let sessions = nt_sessions().expect("SystemProcessInformation");
        let wts = wts_any_then_mine(wts_sids, sessions.get(&std::process::id()).map(|&(s, _)| s)).unwrap_or_default();
        // SAFETY: 의사 핸들.
        let me_sid = token_sid(unsafe { windows_sys::Win32::System::Threading::GetCurrentProcess() });
        let f = facts(4, me_sid.as_deref(), &sessions, &wts);
        let my_session = sessions.get(&std::process::id()).map(|&(s, _)| s);
        assert_eq!(win_foreign(4, &f, my_session), Some(true), "{f:?}");
        assert_eq!(sessions.get(&4).map(|&(s, _)| s), Some(0), "System 은 세션 0");
    }

    /// ⓒ 없는 pid = 없음(Gone) · 죽음 확인 = Dead · 목록에서 빠짐(None).
    #[test]
    fn missing_pid_is_gone_and_dead() {
        const NO: u32 = 0x7fff_fff0;
        let code = open(NO).err().expect("없는 pid 가 열렸다");
        assert_eq!(open_err_kind(code), WinOpen::Gone, "오류 코드 {code}");
        assert!(matches!(probe_dead(NO), Err(Failure::Dead)));
        let f = facts(NO, None, &Default::default(), &Default::default());
        assert_eq!(win_foreign(NO, &f, Some(1)), None, "{f:?}");
    }

    /// ⓓ 자식 프로세스(명령줄에 S) = Seen · 살아 있을 때 probe = Ok · 끝낸 뒤 = Dead.
    #[test]
    fn child_with_conversation_id_is_seen_then_dead() {
        let s = random_id("child");
        // PowerShell 은 -Command 뒤 인자를 이어 붙여 실행한다 → `#` 뒤 S 는 주석 · argv 에는 S 가 한 칸으로 남는다.
        // 숨김 헬퍼(spawn_policy 계수 동결 시험 `raw_command_new_census_is_frozen` 규율 · 윈 콘솔 창 숨김).
        let mut child = crate::hidden_command("powershell.exe")
            .args(["-NoProfile", "-NonInteractive", "-Command", "Start-Sleep -Seconds 60; #", &s])
            .stdin(std::process::Stdio::null())
            .stdout(std::process::Stdio::null())
            .stderr(std::process::Stdio::null())
            .spawn()
            .expect("powershell 자식");
        let pid = child.id();
        let seen = scan_argv(&s, &[]);
        let alive = probe_dead(pid);
        let _ = child.kill();
        let _ = child.wait();
        assert!(matches!(seen, Evidence::Seen(_)), "자식 {pid} 를 못 봤다: {seen:?}");
        assert_eq!(alive, Ok(()), "살아 있는 자식을 죽음/판독 실패로 봤다");
        assert!(matches!(probe_dead(pid), Err(Failure::Dead)), "끝난 자식을 죽음으로 못 봤다");
    }

    /// ⓔ 아무도 쥐지 않은 대화 = NoneConfirmed(「시스템 pid 때문에 Undecided」 재발 탐지 · 사고 원형).
    #[test]
    fn unheld_conversation_is_none_confirmed_on_a_real_box() {
        let s = random_id("nobody");
        assert_eq!(scan_argv(&s, &[]), Evidence::NoneConfirmed);
    }
}

/// (작성자로 보이는 것, 명령줄을 못 읽은 pid) — `my_uid` = None 이면 UID 로 거르지 않는다(윈).
/// UID 판독 실패는 「남의 것」으로 치지 않는다: 명령줄을 읽었으면 그대로 보고, 못 읽었으면 판정 불가 후보(codex 1R B1).
pub(crate) fn classify_argv(view: &[ProcView], norm: &str, exclude: &[u32], my_uid: Option<u32>) -> (Option<String>, Vec<u32>) {
    let mut unreadable = Vec::new();
    for p in view {
        if exclude.contains(&p.pid) || p.pid == std::process::id() || p.skip || p.foreign {
            continue;
        }
        if let (Some(me), Some(u)) = (my_uid, p.uid) {
            if u != me {
                continue;
            }
        }
        if p.cmd.is_empty() {
            unreadable.push(p.pid);
            continue;
        }
        let hit = p.cmd.iter().any(|a| {
            let a = a.to_ascii_lowercase();
            a == norm || a.ends_with(&format!("={norm}"))
        });
        if hit {
            let line: Vec<&str> = p.cmd.iter().take(4).map(String::as_str).collect();
            return (Some(format!("pid {}({}) 가 이 대화를 인자로 쥐고 있음", p.pid, line.join(" "))), unreadable);
        }
    }
    (None, unreadable)
}

/// 「죽음 확인」(Failure::Dead)만 뺀다 — 살아 있음 · 판독 실패(EPERM 등) · 미지원은 남긴다.
pub(crate) fn drop_confirmed_dead(
    mut pids: Vec<u32>,
    probe: impl Fn(u32) -> Result<(), crate::process_observation::Failure>,
) -> Vec<u32> {
    pids.retain(|p| !matches!(probe(*p), Err(crate::process_observation::Failure::Dead)));
    pids
}

/// 나와 내 조상 pid(최대 64단) — 바깥 증거에서 뺀다(복원기 자신·그 부모 셸·phoenix 등).
pub fn self_and_ancestors() -> Vec<u32> {
    let mut v = vec![std::process::id()];
    let mut p = std::process::id();
    for _ in 0..64 {
        match crate::process_observation::identity(p) {
            Ok(id) if id.parent > 1 && !v.contains(&id.parent) => {
                v.push(id.parent);
                p = id.parent;
            }
            _ => break,
        }
    }
    v
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::cell::RefCell;

    struct Fake {
        alive: RefCell<HashMap<u32, Liveness>>,
        seat: Liveness,
        evidence: Evidence,
        /// 좌석 등록 대화(r5b) — 기본 = 판독 불가.
        conv: Result<Option<String>, String>,
    }

    impl Fake {
        fn new() -> Self {
            Fake { alive: RefCell::new(HashMap::new()), seat: Liveness::Dead, evidence: Evidence::NoneConfirmed, conv: Err("unset".into()) }
        }
        fn set(&self, pid: u32, l: Liveness) {
            self.alive.borrow_mut().insert(pid, l);
        }
    }

    impl World for Fake {
        fn holder(&self, h: &Holder) -> Liveness {
            self.alive.borrow().get(&h.pid).cloned().unwrap_or(Liveness::Dead)
        }
        fn seat(&self, _s: u64, _g: Option<&str>, _strict: bool) -> Liveness {
            self.seat.clone()
        }
        fn seat_conversation(&self, _s: u64, _g: Option<&str>) -> Result<Option<String>, String> {
            self.conv.clone()
        }
        fn evidence(&self, _n: &str) -> Evidence {
            self.evidence.clone()
        }
        fn now(&self) -> u64 {
            1_000
        }
    }

    fn h(pid: u32) -> Holder {
        Holder { pid, birth_s: 100 + pid as u64, birth_us: 7 }
    }

    fn tmp(tag: &str) -> PathBuf {
        let d = std::env::temp_dir().join(format!("slt-{}-{tag}-{}", std::process::id(), now_secs()));
        let _ = std::fs::remove_dir_all(&d);
        d
    }

    fn cx<'a>(me: Holder, w: &'a Fake) -> AcquireCtx<'a> {
        AcquireCtx { me, surface_id: None, daemon_gen: None, cfg: None, world: w }
    }

    #[test]
    fn key_never_splits_one_conversation() {
        assert_eq!(norm_id("  ABC-def \n").as_deref(), Some("abc-def"));
        assert_eq!(key_hex(&norm_id("ABC").unwrap()), key_hex(&norm_id(" abc").unwrap()));
        assert_ne!(key_hex("abc"), key_hex("abd"));
        assert_eq!(norm_id("   "), None);
        // 경로는 키에 없다 — 같은 id 면 어떤 설정 폴더에서 와도 같은 파일.
        let s = Store { root: PathBuf::from("/x") };
        assert_eq!(s.file_of("abc"), s.file_of(&norm_id("ABC").unwrap()));
    }

    #[test]
    fn knob_defaults_on() {
        assert!(enabled_from(None));
        assert!(enabled_from(Some("on")));
        for v in ["off", "0", "false", "NO", " Off "] {
            assert!(!enabled_from(Some(v)), "{v}");
        }
    }

    #[test]
    fn live_writer_refuses_dead_writer_is_taken_over() {
        let d = tmp("lw");
        let s = Store::open(&d).unwrap();
        let w = Fake::new();
        let Decision::Granted(g) = acquire(&s, "S1", &cx(h(10), &w)) else { panic!("빈 자리") };
        g.hold(Some(h(20))).unwrap();
        w.set(20, Liveness::Alive);
        assert!(matches!(acquire(&s, "s1", &cx(h(11), &w)), Decision::Live { .. }), "살아 있는 작성자를 넘겼다");
        // pid 재사용 = 같은 pid 다른 출생 → 운영 판독기는 Dead 로 돌려준다(여기선 세계가 Dead).
        w.set(20, Liveness::Dead);
        let Decision::Granted(g2) = acquire(&s, "S1", &cx(h(12), &w)) else { panic!("죽은 작성자를 못 넘겨받음") };
        assert_eq!(g2.fence(), 2, "fence 가 오르지 않았다(첫 임대 1 → 인수 2)");
        drop(g2);
        // 되돌림 = 이전 기록(죽은 작성자 20)을 되돌려 놓음 · fence 는 내려가지 않음.
        let back = s.read(&s.file_of("s1")).unwrap().expect("되돌림이 기록을 지웠다");
        assert_eq!((back.writer, back.fence), (Some(h(20)), 2));
        let _ = std::fs::remove_dir_all(&d);
    }

    #[test]
    fn undecided_never_counts_as_none() {
        let d = tmp("ud");
        let s = Store::open(&d).unwrap();
        let w = Fake::new();
        let Decision::Granted(g) = acquire(&s, "S2", &cx(h(10), &w)) else { panic!() };
        g.hold(Some(h(30))).unwrap();
        w.set(30, Liveness::Undecided("probe:proc_pidinfo:1:30".into()));
        match acquire(&s, "S2", &cx(h(11), &w)) {
            Decision::Undecided { reason, next } => {
                assert!(reason.starts_with("probe:"), "{reason}");
                assert!(next.contains("ps -p 30"), "다음 행동 줄이 없다: {next}");
            }
            o => panic!("판정 불가를 다르게 쳤다: {o:?}"),
        }
        let _ = std::fs::remove_dir_all(&d);
    }

    #[test]
    fn evidence_after_acquire_rolls_back() {
        let d = tmp("ev");
        let s = Store::open(&d).unwrap();
        let mut w = Fake::new();
        w.evidence = Evidence::Seen("pid 9 가 이 대화를 인자로 쥐고 있음".into());
        assert!(matches!(acquire(&s, "S3", &cx(h(10), &w)), Decision::Live { .. }));
        assert!(!s.file_of("s3").exists(), "증거로 거절했는데 임대가 남았다");
        w.evidence = Evidence::Undecided("daemon:unreachable".into());
        assert!(matches!(acquire(&s, "S3", &cx(h(10), &w)), Decision::Undecided { .. }));
        assert!(!s.file_of("s3").exists());
        let _ = std::fs::remove_dir_all(&d);
    }

    #[test]
    fn unknown_outcome_holds_until_seat_is_dead() {
        let d = tmp("uk");
        let s = Store::open(&d).unwrap();
        let mut w = Fake::new();
        let Decision::Granted(g) = acquire(&s, "S4", &AcquireCtx { surface_id: Some(52), ..cx(h(10), &w) }) else { panic!() };
        g.keep_unknown().unwrap();
        // 복원기(10) 는 끝났다(세계에 없음 = Dead) · 좌석 판정 불가 → U7.
        w.seat = Liveness::Undecided("daemon:unreachable".into());
        match acquire(&s, "S4", &cx(h(11), &w)) {
            Decision::Undecided { reason, next } => {
                assert!(reason.starts_with("lease:outcome-unknown"), "{reason}");
                assert!(next.contains("surface:52"), "{next}");
            }
            o => panic!("{o:?}"),
        }
        w.seat = Liveness::Alive;
        assert!(matches!(acquire(&s, "S4", &cx(h(11), &w)), Decision::Live { .. }), "좌석이 살아 있는데 넘겼다");
        w.seat = Liveness::Dead;
        assert!(matches!(acquire(&s, "S4", &cx(h(11), &w)), Decision::Granted(_)), "좌석이 죽었는데 못 넘겨받음");
        let _ = std::fs::remove_dir_all(&d);
    }

    /// r5b(master 재검증 ⓐ): 결과 불명 임대의 좌석이 살아 있어도 등록이 **다른 대화**면 풀린다 · 등록 없음·판독 불가·같은 대화 = 막음 유지(#1) ·
    /// 기동 중(복원기 죽음) 임대는 넓히지 않는다(종전 그대로 막음).
    #[test]
    fn unknown_seat_registered_as_another_conversation_is_freed() {
        let d = tmp("ur");
        let s = Store::open(&d).unwrap();
        let mut w = Fake::new();
        let Decision::Granted(g) = acquire(&s, "R5B-S", &AcquireCtx { surface_id: Some(53), ..cx(h(10), &w) }) else { panic!() };
        g.keep_unknown().unwrap();
        w.seat = Liveness::Alive;
        for (conv, why) in [
            (Ok(None), "등록 없음"),
            (Err("daemon:unreachable".to_string()), "판독 불가"),
            (Ok(Some("r5b-s".to_string())), "같은 대화(대소문자)"),
            (Ok(Some(" ".to_string())), "빈 등록"),
        ] {
            w.conv = conv;
            assert!(matches!(acquire(&s, "R5B-S", &cx(h(11), &w)), Decision::Live { .. }), "{why}: 좌석이 이 대화를 쓰고 있을 수 있는데 풀었다");
        }
        w.conv = Ok(Some("T5".into()));
        assert!(matches!(acquire(&s, "R5B-S", &cx(h(11), &w)), Decision::Granted(_)), "다른 대화로 등록된 좌석인데 92 로 굳었다");
        // 기동 중(복원기 죽음 · 좌석 살아 있음 · 다른 대화 등록) = 종전대로 막음.
        let Decision::Granted(g2) = acquire(&s, "R5B-L", &AcquireCtx { surface_id: Some(54), ..cx(h(12), &Fake::new()) }) else { panic!() };
        std::mem::forget(g2); // launching 유지(되돌림 없이) · 복원기 12 는 세계에 없음 = 죽음
        mine_set("r5b-l", None);
        assert!(matches!(acquire(&s, "R5B-L", &cx(h(13), &w)), Decision::Live { .. }), "기동 중 임대까지 넓혔다");
        let _ = std::fs::remove_dir_all(&d);
    }

    #[test]
    fn launching_restorer_alive_refuses_and_stale_fence_cannot_clobber() {
        let d = tmp("lf");
        let s = Store::open(&d).unwrap();
        let w = Fake::new();
        let Decision::Granted(old) = acquire(&s, "S5", &cx(h(10), &w)) else { panic!() };
        // 같은 프로세스면 AlreadyMine — 다른 프로세스 흉내로 등록부만 비운다(가드 `old` 는 계속 산다).
        assert!(matches!(acquire(&s, "S5", &cx(h(10), &w)), Decision::AlreadyMine));
        mine_set("s5", None);
        w.set(10, Liveness::Alive);
        assert!(matches!(acquire(&s, "S5", &cx(h(11), &w)), Decision::Live { .. }), "기동 중인 복원기를 넘겼다");
        // 옛 복원기가 멈춘 사이 죽음 판정 → 새 복원기가 인수 · 늦게 깬 옛 가드는 새 임대를 덮거나 지우지 못한다.
        w.set(10, Liveness::Dead);
        let Decision::Granted(new) = acquire(&s, "S5", &cx(h(11), &w)) else { panic!() };
        old.hold(Some(h(99))).unwrap();
        let l = s.read(&s.file_of("s5")).unwrap().unwrap();
        assert_eq!(l.fence, new.fence());
        assert_eq!(l.writer, None, "옛 fence 가 새 임대를 덮었다");
        new.hold(Some(h(40))).unwrap();
        assert_eq!(s.read(&s.file_of("s5")).unwrap().unwrap().writer, Some(h(40)));
        let _ = std::fs::remove_dir_all(&d);
    }

    #[test]
    fn malformed_lease_is_undecided() {
        let d = tmp("mf");
        let s = Store::open(&d).unwrap();
        let w = Fake::new();
        std::fs::write(s.file_of("s6"), "not json\n").unwrap();
        match acquire(&s, "S6", &cx(h(10), &w)) {
            Decision::Undecided { reason, next } => {
                assert!(reason.starts_with("lease:malformed"), "{reason}");
                assert!(next.contains(".lease"), "{next}");
            }
            o => panic!("{o:?}"),
        }
        let _ = std::fs::remove_dir_all(&d);
    }

    #[cfg(unix)]
    #[test]
    fn store_refuses_symlink_and_foreign_mode_is_fixed() {
        use std::os::unix::fs::PermissionsExt;
        let d = tmp("sl");
        std::fs::create_dir_all(&d).unwrap();
        let real = d.join("real");
        std::fs::create_dir_all(&real).unwrap();
        let link = d.join("link");
        std::os::unix::fs::symlink(&real, &link).unwrap();
        assert!(Store::open(&link).unwrap_err().starts_with("lease:lock"), "심링크 폴더를 받았다");
        std::fs::set_permissions(&real, std::fs::Permissions::from_mode(0o755)).unwrap();
        Store::open(&real).unwrap();
        assert_eq!(std::fs::metadata(&real).unwrap().permissions().mode() & 0o777, 0o700);
        // 임대 파일 자리에 심링크 = 판정 불가(따라가지 않는다).
        let s = Store::open(&real).unwrap();
        std::os::unix::fs::symlink("/etc/hosts", s.file_of("s7")).unwrap();
        assert!(matches!(acquire(&s, "S7", &cx(h(10), &Fake::new())), Decision::Undecided { .. }));
        let _ = std::fs::remove_dir_all(&d);
    }

    /// codex 1R M5 — 임대 자리에 FIFO 가 있으면 열기에서 멈추지 않고 곧장 판정 불가(U4) · 폴더도 U4 · 넓은 권한은 0600 으로 좁힘.
    #[cfg(unix)]
    #[test]
    fn odd_lease_file_kinds_are_refused_without_hanging() {
        use std::os::unix::fs::PermissionsExt;
        let d = tmp("kind");
        let s = Store::open(&d).unwrap();
        let fifo = std::ffi::CString::new(s.file_of("k1").to_str().unwrap()).unwrap();
        // SAFETY: 유효한 C 문자열 경로.
        assert_eq!(unsafe { libc::mkfifo(fifo.as_ptr(), 0o600) }, 0);
        let t0 = Instant::now();
        match acquire(&s, "K1", &cx(h(10), &Fake::new())) {
            Decision::Undecided { reason, next } => {
                assert_eq!(reason, "lease:lock:kind:not-regular");
                assert!(next.contains("일반 파일"), "{next}");
            }
            o => panic!("FIFO 임대를 다르게 쳤다: {o:?}"),
        }
        assert!(t0.elapsed() < Duration::from_secs(2), "FIFO 열기에서 멈췄다");
        std::fs::create_dir(s.file_of("k2")).unwrap();
        assert!(matches!(acquire(&s, "K2", &cx(h(10), &Fake::new())), Decision::Undecided { reason, .. } if reason.starts_with("lease:lock:kind")));
        // 넓은 권한의 내 일반 파일 = 좁혀서 계속.
        let Decision::Granted(g) = acquire(&s, "K3", &cx(h(10), &Fake::new())) else { panic!() };
        g.hold(Some(h(30))).unwrap();
        std::fs::set_permissions(s.file_of("k3"), std::fs::Permissions::from_mode(0o644)).unwrap();
        let w = Fake::new();
        w.set(30, Liveness::Alive);
        assert!(matches!(acquire(&s, "K3", &cx(h(11), &w)), Decision::Live { .. }));
        assert_eq!(std::fs::metadata(s.file_of("k3")).unwrap().permissions().mode() & 0o777, 0o600);
        // 사건 기록 자리에 FIFO 가 있어도 멈추지 않는다(기록만 건너뜀).
        let ev = std::ffi::CString::new(d.join("events.log").to_str().unwrap()).unwrap();
        let _ = std::fs::remove_file(d.join("events.log"));
        assert_eq!(unsafe { libc::mkfifo(ev.as_ptr(), 0o600) }, 0);
        let t0 = Instant::now();
        s.event("t", None, "k4", "", 1);
        assert!(t0.elapsed() < Duration::from_secs(2), "사건 기록 FIFO 에서 멈췄다");
        let _ = std::fs::remove_dir_all(&d);
    }

    /// 잠금 시한 — 남이 잠금을 쥔 채 멈춰 있으면 무기한 기다리지 않고 lease:lock:timeout(U4 · 93).
    #[test]
    fn lock_wait_is_bounded() {
        let d = tmp("lk");
        let s = Store::open(&d).unwrap();
        let held = s.lock().unwrap(); // 다른 열기(설명자)라 같은 프로세스에서도 겹침
        let t0 = Instant::now();
        assert_eq!(s.lock_within(Duration::from_millis(200)).unwrap_err(), "lease:lock:timeout");
        assert!(t0.elapsed() >= Duration::from_millis(200) && t0.elapsed() < Duration::from_secs(2));
        assert!(next_action("lease:lock:timeout", "abc", &s.file_of("abc")).contains("5초"));
        drop(held);
        assert!(s.lock_within(Duration::from_millis(200)).is_ok(), "풀린 뒤에도 못 잡았다");
        let _ = std::fs::remove_dir_all(&d);
    }

    #[test]
    fn follow_moves_with_the_writer_and_never_steals_a_live_one() {
        let d = tmp("fw");
        let s = Store::open(&d).unwrap();
        let w = Fake::new();
        // 복원기가 좌석 52 로 띄운 대화 A → 좌석의 작성자가 등록 때 이어받는다.
        let gen = Some("77-1.5".to_string());
        let Decision::Granted(g) = acquire(&s, "A", &AcquireCtx { surface_id: Some(52), daemon_gen: gen.clone(), ..cx(h(10), &w) }) else { panic!() };
        g.hold(None).unwrap();
        w.set(10, Liveness::Alive); // 복원기가 아직 살아 있어도 같은 데몬 같은 좌석이면 이어받는다
        assert_eq!(follow(&s, "A", &h(50), Some(52), gen, &w), Follow::Held);
        // /clear → 새 대화 B: B 를 쥐고 A 는 내려놓는다(그래야 A 를 정당하게 이을 수 있다).
        assert_eq!(follow(&s, "B", &h(50), Some(52), None, &w), Follow::Held);
        assert!(!s.file_of("a").exists(), "옛 대화 임대를 안 내려놓았다");
        // 다른 프로세스가 B 를 쥐려 함(작성자 50 생존) → 빼앗지 않음.
        w.set(50, Liveness::Alive);
        assert!(matches!(follow(&s, "B", &h(60), Some(53), None, &w), Follow::Conflict(_)));
        assert_eq!(s.read(&s.file_of("b")).unwrap().unwrap().writer, Some(h(50)));
        // 그 상태에서 복원이 B 를 이으려 하면 거절.
        assert!(matches!(acquire(&s, "B", &cx(h(11), &w)), Decision::Live { .. }));
        let _ = std::fs::remove_dir_all(&d);
    }

    /// skt1(codex r5c #1·#3) — 좌석의 현재 대화 증거 = 산 작성자에게 묶인 작성 중 임대만: 작성자 죽음(에이전트 교체 · 낡은 등록) = 소멸 ·
    /// 다른 세대·다른 좌석 = 남의 것 · 산 결속 둘 = 모순(판정 불가) · 판독 불가 = Err. 앱의 「복원됨」 판독도 같은 결속(held_by_live_writer).
    #[test]
    fn seat_binding_is_the_live_writers_held_lease_only() {
        let d = tmp("sb");
        let s = Store::open(&d).unwrap();
        let w = Fake::new();
        let gen = "77-1.5";
        let probe = |h: &Holder| w.holder(h);
        assert_eq!(seat_bound_conversation(&s, 52, gen, &probe), Ok(None), "빈 폴더 = 결속 없음");
        // 좌석 52 의 최상위 에이전트 50 이 등록(follow)으로 T 를 쥠.
        assert_eq!(follow(&s, "T", &h(50), Some(52), Some(gen.into()), &w), Follow::Held);
        assert_eq!(seat_bound_conversation(&s, 52, gen, &probe), Ok(None), "작성자 죽음(기본) = 결속 소멸 — 낡은 등록이 다른 대화 증거가 됐다");
        w.set(50, Liveness::Alive);
        assert_eq!(seat_bound_conversation(&s, 52, gen, &probe), Ok(Some("t".into())));
        assert_eq!(seat_bound_conversation(&s, 53, gen, &probe), Ok(None), "다른 좌석");
        assert_eq!(seat_bound_conversation(&s, 52, "88-2.0", &probe), Ok(None), "다른 데몬 세대의 같은 번호");
        assert_eq!(held_by_live_writer(&s, "T", &probe), Ok(Some((52, Some(gen.into())))));
        assert_eq!(held_by_live_writer(&s, " t ", &probe), Ok(Some((52, Some(gen.into())))), "정규화");
        assert_eq!(held_by_live_writer(&s, "U", &probe), Ok(None));
        // 기동 중·결과 불명(작성자 없음) 임대는 결속이 아니다.
        let Decision::Granted(g) = acquire(&s, "S", &AcquireCtx { surface_id: Some(52), daemon_gen: Some(gen.into()), ..cx(h(10), &w) }) else { panic!() };
        g.keep_unknown().unwrap();
        assert_eq!(seat_bound_conversation(&s, 52, gen, &probe), Ok(Some("t".into())), "결과 불명 임대가 결속으로 셌다");
        assert_eq!(held_by_live_writer(&s, "S", &probe), Ok(None), "작성자 없는 임대를 「복원됨」으로 셌다");
        // 생존 판정 불가 = Err(풀 근거 없음).
        w.set(50, Liveness::Undecided("probe:x".into()));
        assert!(seat_bound_conversation(&s, 52, gen, &probe).is_err());
        assert!(held_by_live_writer(&s, "T", &probe).is_err());
        // 같은 좌석·세대에 산 작성자 결속 둘 = 모순.
        w.set(50, Liveness::Alive);
        w.set(51, Liveness::Alive);
        assert_eq!(follow(&s, "U", &h(51), Some(52), Some(gen.into()), &w), Follow::Held);
        assert!(seat_bound_conversation(&s, 52, gen, &probe).unwrap_err().starts_with("lease:bound:ambiguous"));
        // 깨진 임대 파일 = 판정 불가.
        std::fs::write(s.root().join("ff.lease"), "{").unwrap();
        assert!(seat_bound_conversation(&s, 99, gen, &probe).is_err());
        let _ = std::fs::remove_dir_all(&d);
    }

    /// skt1(codex r5c #1-3) — 등록 계통 판정(cysd `lineage_proves_not_top_hook` 와 같은 표): 최상위 에이전트의 훅 = 증명 아님(옮김) ·
    /// 중첩 헬퍼(에이전트 2) · 도구 셸 직접 호출(에이전트 1 · 훅 아래 아님) = 증명(옮기지 않음) · argv 못 읽음 = None.
    #[test]
    fn registration_lineage_tells_top_hook_from_helpers() {
        let c = |v: &[&str]| v.iter().map(|x| Some(x.to_string())).collect::<Vec<_>>();
        let top = c(&["/bin/sh -c sh /p/hooks/session-start.sh", "sh /p/hooks/session-start.sh", "/opt/bin/claude --resume x", "-zsh"]);
        assert_eq!(lineage_proves_not_top_hook(&top, "claude"), Some(false), "최상위 훅을 헬퍼로 봤다");
        let helper = c(&["sh /p/hooks/session-start.sh", "/opt/bin/claude -p hi", "/bin/bash -c claude -p hi", "/opt/bin/claude", "-zsh"]);
        assert_eq!(lineage_proves_not_top_hook(&helper, "claude"), Some(true), "중첩 claude -p 헬퍼 등록을 옮겼다(r5c #1-3)");
        let tool = c(&["/bin/zsh -c cys usage-register --transcript /x/T.jsonl", "/opt/bin/claude", "-zsh"]);
        assert_eq!(lineage_proves_not_top_hook(&tool, "claude"), Some(true), "도구 셸 직접 등록을 옮겼다");
        // 훅이 에이전트보다 루트 쪽(위)에 있는 것은 그 에이전트의 훅이 아니다.
        let above = c(&["/opt/bin/claude", "sh /p/hooks/session-start.sh", "-zsh"]);
        assert_eq!(lineage_proves_not_top_hook(&above, "claude"), Some(true));
        let mut unread = top.clone();
        unread[1] = None;
        assert_eq!(lineage_proves_not_top_hook(&unread, "claude"), None, "argv 미관측을 증명으로 셌다");
        assert_eq!(lineage_proves_not_top_hook(&c(&["sh session-start.sh", "-zsh"]), "claude"), Some(false), "에이전트 0 = 증명 아님");
        // 실행 판별(cysd cmdline_matches_agent_exec 와 같은 규칙).
        assert!(argv_is_agent_exec("node /u/lib/node_modules/@anthropic-ai/claude-code/cli.js", "claude"));
        assert!(argv_is_agent_exec("C:\\x\\CLAUDE.EXE --resume a", "claude.exe"));
        assert!(argv_is_agent_exec("/opt/claude.cmd", "claude"));
        assert!(!argv_is_agent_exec("cat /home/u/.claude/projects/claude.txt", "claude"));
        assert!(!argv_is_agent_exec("vim claude-notes.md", "claude"));
        assert!(!argv_is_agent_exec("anything", ""));
    }

    /// codex 1R B2 — 다른 데몬의 같은 좌석 번호는 승계가 아니다(살아 있는 복원기에게서 빼앗지 않음).
    #[test]
    fn follow_inherits_only_from_the_same_daemon_generation() {
        let d = tmp("fg");
        let s = Store::open(&d).unwrap();
        let mut w = Fake::new();
        let g_a = Some("100-1.5".to_string());
        let Decision::Granted(g) = acquire(&s, "G", &AcquireCtx { surface_id: Some(1), daemon_gen: g_a.clone(), ..cx(h(10), &w) }) else { panic!() };
        g.hold(None).unwrap();
        w.set(10, Liveness::Alive); // A 데몬 쪽 복원기 생존
        w.seat = Liveness::Alive; // 좌석 판정이 불리면 살아 있음
        // B 데몬의 surface:1 등록 → 승계 아님 → judge → 복원기 살아 있음 = 충돌.
        assert!(matches!(follow(&s, "G", &h(60), Some(1), Some("200-9.5".into()), &w), Follow::Conflict(_)), "다른 데몬 같은 번호가 이어받았다");
        // 세대 모름(None)도 승계 아님.
        assert!(matches!(follow(&s, "G", &h(61), Some(1), None, &w), Follow::Conflict(_)), "세대 없는 등록이 이어받았다");
        assert_eq!(s.read(&s.file_of("g")).unwrap().unwrap().writer, None, "임대가 바뀌었다");
        // 같은 세대 같은 좌석 = 승계.
        assert_eq!(follow(&s, "G", &h(62), Some(1), g_a, &w), Follow::Held);
        let _ = std::fs::remove_dir_all(&d);
    }

    /// skt1(codex 1R #2A) — 다른 좌석 최상위 훅의 등록(follow)은 **기동 글 확정 전** 복원기 임대를 이긴다(그 좌석이 이미 이 대화로 들어갔다) ·
    /// 복원기는 확정(`mark_launch_sent`)에서 임대가 넘어간 것을 보고 멈춘다 · 확정 뒤면 빼앗지 않는다(충돌) · 재확인 실패 = 확정 0.
    #[test]
    fn a_verified_registration_beats_an_uncommitted_restore_and_the_restorer_stops() {
        let d = tmp("cm");
        let s = Store::open(&d).unwrap();
        let w = Fake::new();
        let gen = Some("77-1.5".to_string());
        w.set(10, Liveness::Alive); // 복원기 생존
        let Decision::Granted(g) = acquire(&s, "CA", &AcquireCtx { surface_id: Some(52), daemon_gen: gen.clone(), ..cx(h(10), &w) }) else { panic!() };
        // 확정 전: 다른 좌석 60 의 최상위 claude 가 좌석 안 /resume CA → 등록 → 이어받음.
        assert_eq!(follow(&s, "CA", &h(50), Some(60), gen.clone(), &w), Follow::Held, "확정 전 복원기가 검증된 등록을 이겼다(작성자 둘 · codex 1R #2A)");
        assert_eq!(mark_launch_sent(&s, "ca", &mut || Ok(())), Err("lease:taken".into()), "임대가 넘어갔는데 복원기가 기동 글을 쳤다");
        assert_eq!(s.read(&s.file_of("ca")).unwrap().unwrap().writer, Some(h(50)));
        drop(g);
        assert_eq!(s.read(&s.file_of("ca")).unwrap().unwrap().writer, Some(h(50)), "늦은 가드가 넘어간 임대를 되돌렸다");
        // 재확인 실패 = 확정 0(기동 글 0) · 임대는 그대로 내 것(가드 drop 이 되돌린다).
        let Decision::Granted(g2) = acquire(&s, "CB", &AcquireCtx { surface_id: Some(53), daemon_gen: gen.clone(), ..cx(h(10), &w) }) else { panic!() };
        assert_eq!(mark_launch_sent(&s, "cb", &mut || Err("recheck:unverified:7:seat-unbound".into())), Err("recheck:unverified:7:seat-unbound".into()));
        assert!(!s.read(&s.file_of("cb")).unwrap().unwrap().launch_sent, "재확인이 실패했는데 확정을 적었다");
        // 확정 뒤: 다른 좌석 등록은 빼앗지 않는다(그 복원기 좌석이 이미 이 대화로 뜨는 중).
        assert_eq!(mark_launch_sent(&s, "cb", &mut || Ok(())), Ok(()));
        assert!(matches!(follow(&s, "CB", &h(51), Some(61), gen.clone(), &w), Follow::Conflict(_)), "확정 뒤 임대를 빼앗았다");
        g2.hold(None).unwrap();
        // 마무리(hold) = 기동 글을 친 것 — 확정 표식이 남는다(확정 없이 hold 된 옛 흐름도 빼앗기지 않게).
        assert!(s.read(&s.file_of("cb")).unwrap().unwrap().launch_sent);
        // 쥐지 않은 대화의 확정 = 거절.
        assert_eq!(mark_launch_sent(&s, "zz", &mut || Ok(())), Err("lease:not-held".into()));
        let _ = std::fs::remove_dir_all(&d);
    }

    /// skt1(codex 2R #2 · 순서 주입) — 확정(mark) 뒤 · Return 전에 다른 좌석 최상위 훅의 등록이 들어오면 follow 는 빼앗지 않되(충돌) 표식을 남기고,
    /// 복원기는 Return 직전 확인(`confirm_launch`)에서 멈춘다(붙인 기동 글은 실행되지 않음) · 표식 없으면 통과 · 재확인 실패도 멈춤.
    #[test]
    fn a_registration_between_commit_and_enter_stops_the_restorer_before_enter() {
        let d = tmp("ce");
        let s = Store::open(&d).unwrap();
        let w = Fake::new();
        let gen = Some("77-1.5".to_string());
        w.set(10, Liveness::Alive);
        let Decision::Granted(g) = acquire(&s, "CE", &AcquireCtx { surface_id: Some(52), daemon_gen: gen.clone(), ..cx(h(10), &w) }) else { panic!() };
        assert_eq!(mark_launch_sent(&s, "ce", &mut || Ok(())), Ok(()));
        assert_eq!(confirm_launch(&s, "ce", &mut || Ok(())), Ok(()), "아무 일 없는데 Return 을 막았다");
        // 확정 뒤 · Return 전: 좌석 60 의 최상위 claude 가 좌석 안 /resume CE → 등록 → 충돌 + 표식.
        assert!(matches!(follow(&s, "CE", &h(50), Some(60), gen.clone(), &w), Follow::Conflict(_)));
        assert!(s.read(&s.file_of("ce")).unwrap().unwrap().contested, "확정 뒤 등록을 흔적 없이 넘겼다(codex 2R #2)");
        assert_eq!(confirm_launch(&s, "ce", &mut || Ok(())), Err("lease:contested".into()), "확정 뒤 등록이 들어왔는데 Return 을 쳤다(작성자 둘)");
        drop(g);
        // 재확인 실패 = Return 0.
        let Decision::Granted(g2) = acquire(&s, "CF", &AcquireCtx { surface_id: Some(53), daemon_gen: gen.clone(), ..cx(h(10), &w) }) else { panic!() };
        assert_eq!(confirm_launch(&s, "cf", &mut || Ok(())), Err("lease:not-committed".into()), "확정 없이 Return 을 허락했다");
        assert_eq!(mark_launch_sent(&s, "cf", &mut || Ok(())), Ok(()));
        assert_eq!(confirm_launch(&s, "cf", &mut || Err("recheck:unverified:7:seat-unbound".into())), Err("recheck:unverified:7:seat-unbound".into()));
        drop(g2);
        let _ = std::fs::remove_dir_all(&d);
    }

    /// skt1(codex 1R #2B) — 등록 **앞** 결속 해제: 좌석 최상위 작성자가 대화를 바꾸려 하면 그 작성자의 다른 대화 결속은 결과 불명(좌석 유지)으로 —
    /// 등록이 실패해도 「이 좌석 = 옛 대화」 증거가 남지 않고(결속 없음 = 같은 역할 복원 93), 새 결속이 생기면 옛 대화 임대는 judge 가 푼다.
    #[test]
    fn a_conversation_switch_unbinds_the_old_conversation_before_registering() {
        let d = tmp("tu");
        let s = Store::open(&d).unwrap();
        let mut w = Fake::new();
        let gen = "77-1.5";
        w.set(50, Liveness::Alive);
        assert_eq!(follow(&s, "TT", &h(50), Some(52), Some(gen.into()), &w), Follow::Held);
        let probe = |x: &Holder| if *x == h(50) { Liveness::Alive } else { Liveness::Dead };
        assert_eq!(seat_bound_conversation(&s, 52, gen, &probe), Ok(Some("tt".into())));
        // 남의 작성자 · 같은 대화(compact) = 손대지 않음.
        assert_eq!(transition_unbind(&s, "SS", &|x, _| *x == h(99)), 0);
        assert_eq!(transition_unbind(&s, "TT", &|x, _| *x == h(50)), 0, "같은 대화 재등록에서 결속을 풀었다");
        // 좌석 안 /resume SS(등록 전) → TT 결속 = 결과 불명.
        assert_eq!(transition_unbind(&s, "SS", &|x, _| *x == h(50)), 1);
        let l = s.read(&s.file_of("tt")).unwrap().unwrap();
        assert_eq!((l.state, l.writer.clone(), l.surface_id), (State::Unknown, None, Some(52)), "옛 결속이 남았다(등록 실패 시 「다른 대화」 증거 · codex 1R #2B)");
        assert_eq!(seat_bound_conversation(&s, 52, gen, &probe), Ok(None), "등록 전 좌석이 옛 대화로 읽힌다");
        // TT 복원: 그 좌석이 살아 있고 현재 대화를 모름 = 막음 · 새 대화로 확인되면 풂.
        w.seat = Liveness::Alive;
        w.conv = Ok(None);
        assert!(matches!(acquire(&s, "TT", &cx(h(11), &w)), Decision::Live { .. }));
        w.conv = Ok(Some("ss".into()));
        assert!(matches!(acquire(&s, "TT", &cx(h(11), &w)), Decision::Granted(_)), "새 결속 뒤에도 옛 대화가 막혔다");
        let _ = std::fs::remove_dir_all(&d);
    }

    /// skt1(codex 1R #1) — 계통 3값: 결속을 옮기는 것은 ProvenTop(최상위 에이전트 1 + 그 아래 훅) 뿐 · 판독 불가·에이전트 0·이름 모름 = Unknown.
    #[test]
    fn lineage_moves_only_a_proven_top_hook() {
        let c = |v: &[&str]| v.iter().map(|x| Some(x.to_string())).collect::<Vec<_>>();
        assert_eq!(lineage_of(&c(&["sh /p/hooks/session-start.sh", "/u/bin/claude --resume x", "-zsh"]), "claude"), Lineage::ProvenTop);
        assert_eq!(lineage_of(&c(&["sh /p/session-start.sh", "claude -p hi", "bash -c x", "claude", "-zsh"]), "claude"), Lineage::NotTop, "헬퍼");
        assert_eq!(lineage_of(&c(&["bash -c cys", "claude", "-zsh"]), "claude"), Lineage::NotTop, "도구 셸");
        let mut unread = c(&["sh /p/session-start.sh", "claude"]);
        unread.insert(1, None);
        assert_eq!(lineage_of(&unread, "claude"), Lineage::Unknown, "argv 미관측을 최상위로 셌다(codex 1R #1)");
        assert_eq!(lineage_of(&c(&["sh session-start.sh", "-zsh"]), "claude"), Lineage::Unknown, "에이전트 0");
        assert_eq!(lineage_of(&c(&["sh session-start.sh", "claude"]), ""), Lineage::Unknown, "이름 모름");
        assert_eq!(lineage_of(&[], "claude"), Lineage::Unknown, "계통 없음");
    }

    /// skt1(codex 1R #4) — 앱 「복원됨」 증거 = topology 앞뒤 두 판독이 같은 결속(fence·token·작성자)일 때만.
    #[test]
    fn held_proof_must_be_the_same_on_both_sides_of_the_topology_read() {
        let p = |fence: u64, tok: &str, pid: u32| HeldProof { surface_id: 5, daemon_gen: Some("g".into()), fence, token: tok.into(), writer: h(pid) };
        assert_eq!(held_proof_stable(Some(p(2, "a", 50)), Some(p(2, "a", 50))), Some(p(2, "a", 50)));
        assert_eq!(held_proof_stable(Some(p(2, "a", 50)), None), None, "사이에 결속이 사라졌다(/clear·작성자 죽음)");
        assert_eq!(held_proof_stable(Some(p(2, "a", 50)), Some(p(3, "b", 50))), None, "사이에 다시 잡혔다");
        assert_eq!(held_proof_stable(Some(p(2, "a", 50)), Some(p(2, "a", 51))), None, "작성자가 바뀌었다");
        assert_eq!(held_proof_stable(None, Some(p(2, "a", 50))), None);
    }

    /// codex 1R M2 — follow 가 옛 대화 임대를 지운 뒤 같은 키를 다시 잡으면 fence 가 1 부터 다시 매겨진다.
    /// 그 사이 남은 옛 가드가 같은 fence 의 새 임대를 「내 것」으로 보고 지우거나 고치면 안 된다(ABA).
    #[test]
    fn stale_guard_cannot_touch_a_reacquired_lease_with_the_same_fence() {
        let d = tmp("aba");
        let s = Store::open(&d).unwrap();
        let w = Fake::new();
        let gen = Some("9-1.5".to_string());
        let Decision::Granted(old) = acquire(&s, "ABA", &AcquireCtx { surface_id: Some(5), daemon_gen: gen.clone(), ..cx(h(10), &w) }) else { panic!() };
        assert_eq!(old.fence(), 1);
        // 좌석 작성자가 이어받고(fence 2) → /clear 로 다른 대화로 옮기며 ABA 임대를 지운다.
        assert_eq!(follow(&s, "ABA", &h(50), Some(5), gen.clone(), &w), Follow::Held);
        assert_eq!(follow(&s, "OTHER", &h(50), Some(5), gen, &w), Follow::Held);
        assert!(!s.file_of("aba").exists());
        // 새 복원기가 다시 잡는다 — 파일이 없으니 fence 1 재사용.
        mine_set("aba", None); // 같은 프로세스 안 시험이라 등록부만 비운다(실제로는 다른 프로세스)
        let Decision::Granted(new) = acquire(&s, "ABA", &cx(h(11), &w)) else { panic!("재획득") };
        assert_eq!(new.fence(), 1, "시험 전제: fence 가 재사용돼야 ABA 상황");
        // 늦게 깬 옛 가드: 좌석 기록·되돌림 모두 새 임대를 건드리면 안 된다.
        assert!(!old.set_surface(99, None), "옛 가드가 새 임대를 고쳤다");
        drop(old);
        let l = s.read(&s.file_of("aba")).unwrap().expect("옛 가드가 새 임대를 지웠다");
        assert_eq!((l.restorer, l.surface_id), (Some(h(11)), None));
        assert!(new.set_surface(7, None), "새 가드가 자기 임대를 못 고쳤다");
        drop(new);
        mine_set("other", None);
        let _ = std::fs::remove_dir_all(&d);
    }

    /// codex 2R M2 — 등록부(MINE)가 남아 있어도 디스크 임대가 넘어갔으면 기동 권한(AlreadyMine · `--resume` 직전 확인)을 주지 않는다.
    #[test]
    fn registry_alone_never_grants_launch_after_the_lease_moved() {
        let d = tmp("mreg");
        let s = Store::open(&d).unwrap();
        let w = Fake::new();
        let gen = Some("8-1.5".to_string());
        let Decision::Granted(g) = acquire(&s, "MR", &AcquireCtx { surface_id: Some(4), daemon_gen: gen.clone(), ..cx(h(10), &w) }) else { panic!() };
        assert!(is_mine_on_disk(&s, "mr"));
        assert!(matches!(acquire(&s, "MR", &cx(h(10), &w)), Decision::AlreadyMine), "안쪽 갈래의 정상 재진입");
        // 좌석 작성자가 등록 때 이어받음(디스크 = 남의 것 · 등록부 = 아직 내 것).
        assert_eq!(follow(&s, "MR", &h(50), Some(4), gen, &w), Follow::Held);
        assert!(is_mine(&"mr".to_string()), "시험 전제: 등록부는 남아 있음");
        assert!(!is_mine_on_disk(&s, "mr"), "넘어간 임대를 디스크에서도 내 것으로 봤다");
        match acquire(&s, "MR", &cx(h(10), &w)) {
            Decision::Undecided { reason, .. } => assert_eq!(reason, "lease:mine-stale"),
            o => panic!("등록부만 보고 진행했다: {o:?}"),
        }
        drop(g);
        let _ = std::fs::remove_dir_all(&d);
    }

    /// codex 6R — 작성 중(held)인데 작성자 없는 기록 = 모순 → 판정 불가(빈 셸 관측으로 넘기는 예외를 막는다).
    #[test]
    fn held_without_writer_is_malformed() {
        let d = tmp("hw");
        let s = Store::open(&d).unwrap();
        std::fs::write(s.file_of("hw"), r#"{"v":1,"id":"hw","fence":2,"state":"held","writer":null,"restorer":null,"surface_id":3,"daemon_gen":"9-1.5","cfg":null,"at":1}"#).unwrap();
        match acquire(&s, "HW", &cx(h(10), &Fake::new())) {
            Decision::Undecided { reason, .. } => assert_eq!(reason, "lease:malformed:held-without-writer"),
            o => panic!("모순 기록을 받아들였다: {o:?}"),
        }
        let _ = std::fs::remove_dir_all(&d);
    }

    #[test]
    fn real_probe_sees_self_alive_and_reused_birth_dead() {
        let me = me().expect("내 신원");
        assert_eq!(probe_holder(&me), Liveness::Alive);
        let fake = Holder { birth_s: me.birth_s + 1, ..me.clone() };
        assert_eq!(probe_holder(&fake), Liveness::Dead, "같은 pid 다른 출생 = 재사용 = 죽음");
        // 없는 pid(아주 큰 값) = 죽음.
        assert_eq!(probe_holder(&Holder { pid: 0x7fff_fff0, birth_s: 1, birth_us: 0 }), Liveness::Dead);
    }

    /// TICKET=cysr-1116-win-restore-1121 — 윈 모양 열거 표(master#d6185ede 규칙 · 판정 함수 수준 · 맥·리눅스 CI 에서도 돈다).
    /// 사실 = 사실 수집이 실제로 줄 수 있는 조합만(세션 = 핸들 없는 SystemProcessInformation · SID = WTS 또는 LIMITED 토큰 · 둘 다 없으면 모름).
    #[test]
    fn win_shaped_argv_scan_table() {
        use crate::process_observation::Failure;
        const S: &str = "5e55aaaa-0000-4000-8000-000000000001";
        let me = std::process::id();
        // 생성 시각(FILETIME 100ns): 열거 표 = 자체 판독 핸들 = T0 — W18·W19 만 어긋나게 준다.
        const T0: u64 = 133_000_000_000_001_234;
        let fx = |open: WinOpen, sid: WinSid, session: Option<u32>| WinFacts { open, sid, session, birth: Some(T0) };
        let (o, f, g) = (WinOpen::Opened, WinOpen::Failed, WinOpen::Gone);
        let (same, other, unk) = (WinSid::Same, WinSid::Other, WinSid::Unknown);
        let argv = |v: &[&str]| v.iter().map(|x| x.to_string()).collect::<Vec<_>>();
        let no_read = |_p: u32| -> Option<Vec<String>> { None };
        // 행 = (pid, 사실) · 자체 판독 = (그 핸들 생성 ticks, argv) — 윈은 sysinfo 명령줄을 쓰지 않는다(master#c699b44d 2).
        let scan_st = |rows: Vec<(u32, WinFacts)>, my: Option<u32>, sr: &dyn Fn(u32) -> Option<(u64, Vec<String>)>, alive: &dyn Fn(u32) -> bool| {
            let mut v = vec![ProcView { pid: me, uid: None, skip: false, foreign: false, cmd: argv(&["cys.exe", "restore"]) }];
            v.extend(rows.into_iter().filter_map(|(pid, f)| win_view(pid, &f, my, sr)));
            let probe = |p: u32| -> Result<(), Failure> { if alive(p) { Ok(()) } else { Err(Failure::Dead) } };
            scan_argv_with(S, &[], None, move || v.clone(), probe)
        };
        // 출생이 맞는 보통 행(W1~W17·W11-real) — 행의 명령줄(비어 있지 않으면) = 그 pid 를 우리 LIMITED 핸들로 읽은 값(출생 T0) · 빈 값이면 `sr`.
        let scan = |rows: Vec<(u32, Vec<String>, WinFacts)>, my: Option<u32>, sr: &dyn Fn(u32) -> Option<Vec<String>>, alive: &dyn Fn(u32) -> bool| {
            let read: std::collections::HashMap<u32, Vec<String>> = rows.iter().filter(|r| !r.1.is_empty()).map(|r| (r.0, r.1.clone())).collect();
            scan_st(rows.into_iter().map(|(p, _, f)| (p, f)).collect(), my, &|p| read.get(&p).cloned().or_else(|| sr(p)).map(|a| (T0, a)), alive)
        };
        let alive = |_p: u32| true;
        let seen = |e: &Evidence| matches!(e, Evidence::Seen(_));
        let none = Evidence::NoneConfirmed;
        let und = |p: u32| Evidence::Undecided(format!("scan:argv:{p}"));
        // W1 같은 사용자 · 명령줄에 S → Seen · W2 S 없음 → 없음
        assert!(seen(&scan(vec![(3001, argv(&["claude", "--resume", S]), fx(o, same, Some(1)))], Some(1), &no_read, &alive)), "W1");
        assert_eq!(scan(vec![(3002, argv(&["claude"]), fx(o, same, Some(1)))], Some(1), &no_read, &alive), none, "W2");
        // W3 핸들 거부 ∧ SID 다름(WTS) → 건너뜀 · W3b 핸들 거부 단독(SID 모름 · 세션 1) → 판정 불가(규칙 3 · codex H2)
        assert_eq!(scan(vec![(668, vec![], fx(f, other, Some(1)))], Some(1), &no_read, &alive), none, "W3");
        assert_eq!(scan(vec![(669, vec![], fx(f, unk, Some(1)))], Some(1), &no_read, &alive), und(669), "W3b");
        // W4 세션 0 · SID 모름 · 나 = 세션 1 → 건너뜀(열림이든 거부든)
        assert_eq!(scan(vec![(900, vec![], fx(o, unk, Some(0))), (901, vec![], fx(f, unk, Some(0)))], Some(1), &no_read, &alive), none, "W4");
        // ★H1 뒤집기: SID 같음 ∧ 세션 0 ∧ 나 = 세션 1 · 명령줄에 S → Seen(세션 0 의 같은 사용자 claude = OpenSSH·예약 작업 · 규칙 1)
        assert!(seen(&scan(vec![(902, argv(&["claude", "--resume", S]), fx(o, same, Some(0)))], Some(1), &no_read, &alive)), "H1 같은 SID 세션 0");
        // 핸들 거부 ∧ SID 같음(WTS) ∧ 세션 0 → 건너뛰지 않는다 · 자체 판독도 같은 LIMITED 열기라 실제로는 거부 → 판정 불가(검증 R2 4-4 하 · 현실 사실 조합)
        assert_eq!(scan(vec![(903, vec![], fx(f, same, Some(0)))], Some(1), &no_read, &alive), und(903), "H1 거부돼도 SID 같음");
        // W5 나 = 세션 0(ssh) · SID 모름 세션 0 claude 에 S → Seen
        assert!(seen(&scan(vec![(904, argv(&["claude", "--resume", S]), fx(o, unk, Some(0)))], Some(0), &no_read, &alive)), "W5");
        // W6 pid 4 · W7 pid 0
        assert_eq!(scan(vec![(4, vec![], fx(f, unk, Some(0))), (0, vec![], fx(f, unk, Some(0)))], Some(1), &no_read, &alive), none, "W6·W7");
        // W8 같은 사용자 상승(sysinfo 빈 값 · 자체 판독 = S) → Seen · W9 자체 판독도 실패 → 판정 불가 유지
        let sr_s = |p: u32| -> Option<Vec<String>> { (p == 3008).then(|| argv(&["claude", "--resume", S])) };
        assert!(seen(&scan(vec![(3008, vec![], fx(o, same, Some(1)))], Some(1), &sr_s, &alive)), "W8");
        assert_eq!(scan(vec![(3009, vec![], fx(o, same, Some(1)))], Some(1), &no_read, &alive), und(3009), "W9");
        // W10 사라짐 → 빠짐 · 판독 사이 죽음 확인 → 빠짐
        assert_eq!(scan(vec![(3010, vec![], fx(g, unk, None))], Some(1), &no_read, &alive), none, "W10a");
        assert_eq!(scan(vec![(3011, vec![], fx(o, same, Some(1)))], Some(1), &no_read, &|p| p != 3011), none, "W10b");
        // W12 나 자신 없음
        assert_eq!(scan_argv_with(S, &[], None, Vec::new, |_p| Ok(())), Evidence::Undecided("scan:enumerate".into()), "W12");
        // W13 세션 못 읽음(None) ∧ SID 모름 → 판정 불가(세션 None 갈래) · 내 세션 모름 → 세션 0 건너뛰지 않음
        assert_eq!(scan(vec![(3013, vec![], fx(f, unk, None))], Some(1), &no_read, &alive), und(3013), "W13a");
        assert_eq!(scan(vec![(3014, vec![], fx(o, unk, Some(0)))], None, &no_read, &alive), und(3014), "W13b");
        // W14 SID 같음 · S → Seen · W15 SID 다름 · 열림 · S 포함 → 건너뜀 · W16 세션 1 SYSTEM(SID 다름) 명령줄 빈 값 → 건너뜀
        assert!(seen(&scan(vec![(3015, argv(&["claude", "--session-id", S]), fx(o, same, Some(1)))], Some(1), &no_read, &alive)), "W14");
        assert_eq!(scan(vec![(3016, argv(&["claude", "--resume", S]), fx(o, other, Some(1)))], Some(1), &no_read, &alive), none, "W15");
        assert_eq!(scan(vec![(1192, vec![], fx(f, other, Some(1)))], Some(1), &no_read, &alive), none, "W16");
        // W17 같은 사용자 상승 · 자체 판독 S 없음 → 없음
        let sr_other = |p: u32| -> Option<Vec<String>> { (p == 10748).then(|| argv(&["oCamTask.exe", "/start"])) };
        assert_eq!(scan(vec![(10748, vec![], fx(o, same, Some(1)))], Some(1), &sr_other, &alive), none, "W17");
        // W11-real 사고 12 pid(cause-check) — 비관리자 cys: 세션 0 서비스 10 = 핸들 거부 · SID 는 WTS 가 주거나(다름) 안 주거나(모름).
        let real = |winlogon_sid: WinSid| vec![
            (15912, vec![], fx(f, unk, Some(0))), (6240, vec![], fx(f, other, Some(0))), (2848, vec![], fx(f, unk, Some(0))),
            (4600, vec![], fx(f, unk, Some(0))), (2128, vec![], fx(f, other, Some(0))), (3420, vec![], fx(f, unk, Some(0))),
            (1140, vec![], fx(f, unk, Some(0))), (5092, vec![], fx(o, other, Some(0))), (5532, vec![], fx(f, unk, Some(0))),
            (2404, vec![], fx(f, unk, Some(0))), (1192, vec![], fx(f, winlogon_sid, Some(1))), (10748, vec![], fx(o, same, Some(1))),
        ];
        // ⓐ WTS 가 winlogon SID 를 준다(다름) → 없음(사고 해소) ⓑ 못 준다(모름 · 세션 1) → 판정 불가 = 보호(master#d6185ede 수용 · 실측으로 재결정)
        assert_eq!(scan(real(other), Some(1), &sr_other, &alive), none, "W11-real ⓐ");
        assert_eq!(scan(real(unk), Some(1), &sr_other, &alive), und(1192), "W11-real ⓑ");
        // ★W18 규칙 8(pid 재사용 · master#c699b44d 2) — 명령줄을 읽은 핸들의 생성 시각 ≠ 열거 표 CreateTime(100ns 그대로) → 쓰지 않는다(판정 불가 쪽).
        let sr_at = |born: u64| move |p: u32| -> Option<(u64, Vec<String>)> { (p == 3018).then(|| (born, vec!["claude".to_string(), "--resume".to_string(), S.to_string()])) };
        // W18a ★같은 초 · 다른 100ns(1 tick 뒤 태어난 같은 pid) → 판정 불가(초로 자르면 Seen/없음 으로 새는 자리 · codex 2R H2)
        assert_eq!(scan_st(vec![(3018, fx(o, same, Some(1)))], Some(1), &sr_at(T0 + 1), &alive), und(3018), "W18a 같은 초 다른 100ns");
        // W18b 출생 정확히 같음 → Seen · W18c 1초 뒤 → 판정 불가
        assert!(seen(&scan_st(vec![(3018, fx(o, same, Some(1)))], Some(1), &sr_at(T0), &alive)), "W18b");
        assert_eq!(scan_st(vec![(3018, fx(o, same, Some(1)))], Some(1), &sr_at(T0 + 10_000_000), &alive), und(3018), "W18c");
        // W18d 열거 표 생성 시각 없음(None) → 명령줄을 쓰지 않음
        assert_eq!(scan_st(vec![(3018, WinFacts { birth: None, ..fx(o, same, Some(1)) })], Some(1), &sr_at(T0), &alive), und(3018), "W18d");
        // W18f 남의 것(SID 다름)은 명령줄을 읽지 않음
        assert_eq!(scan_st(vec![(3018, fx(o, other, Some(1)))], Some(1), &sr_at(T0), &alive), none, "W18f");
        // 출생 대조 = 100ns 그대로(:2499 뒤집기 — 예전 「같은 초 = 같음」)
        assert!(birth_matches(Some(T0), Some(T0)), "정확히 같음");
        assert!(!birth_matches(Some(T0), Some(T0 + 1)) && !birth_matches(Some(T0 + 9_999_999), Some(T0)), "같은 초 · 다른 100ns = 다름");
        assert!(!birth_matches(None, Some(T0)) && !birth_matches(Some(T0), None) && !birth_matches(None, None), "없음 = 거짓");
        // ★W19 행 사실 채택(row_facts · master#c699b44d 1 · codex 2R H1) — 열린 행은 핸들 출생 == 표 CreateTime 일 때만 · 토큰 SID 가 WTS 보다 우선.
        let sid_me: Vec<u8> = vec![1, 2, 0, 0, 0, 0, 0, 5, 21, 0, 0, 0, 7, 0, 0, 0];
        let sid_sys: Vec<u8> = vec![1, 1, 0, 0, 0, 0, 0, 5, 18, 0, 0, 0]; // S-1-5-18
        let spi = Some((0u32, Some(T0)));
        let rf = |spi: Option<(u32, Option<u64>)>, h: WinHandleView, wts: Option<&[u8]>| row_facts(spi, h, wts, Some(&sid_me));
        let fs = |open: WinOpen, sid: WinSid| WinFacts { open, sid, session: Some(0), birth: Some(T0) };
        // W19a 열림 · 출생 같음 · 토큰 = 나 · WTS = SYSTEM(낡은 표) → 토큰 채택 = 같음
        assert_eq!(rf(spi, Ok((Some(T0), Some(sid_me.clone()))), Some(&sid_sys)), fs(o, same), "W19a 토큰이 WTS 를 이김");
        assert_eq!(rf(spi, Ok((Some(T0), Some(sid_sys.clone()))), Some(&sid_me)), fs(o, other), "W19a′ 토큰 = 다름");
        // W19b 열림 · 출생 1 tick 다름(pid 재사용) → Unverified(WTS·토큰 모두 안 씀)
        assert_eq!(rf(spi, Ok((Some(T0 + 1), Some(sid_me.clone()))), Some(&sid_sys)), fs(WinOpen::Unverified, unk), "W19b");
        assert_eq!(rf(spi, Ok((Some(T0 + 1), None)), Some(&sid_sys)), fs(WinOpen::Unverified, unk), "W19b′ 출생 어긋남 ∧ 토큰 실패 → WTS 로 메우지 않음");
        // W19c 출생 일치 ∧ 토큰 실패 → ② WTS SID 로 메움(master#d82fcb00 순서 + 출생) · 토큰 바이트 무효도 실패와 같음
        assert_eq!(rf(spi, Ok((Some(T0), None)), Some(&sid_me)), fs(o, same), "W19c 토큰 실패 → WTS = 나");
        assert_eq!(rf(spi, Ok((Some(T0), Some(vec![1, 3, 0, 0, 0, 0, 0, 5]))), Some(&sid_sys)), fs(o, other), "W19c′ 토큰 무효 → WTS");
        // ★W19h eausvc 모양(사고 pid 5092 · 비관리자 cys): 열림 · 토큰 실패 · WTS = SYSTEM · 출생 일치 → 남의 것 → 건너뜀(93 재발 막음)
        let eausvc = rf(spi, Ok((Some(T0), None)), Some(&sid_sys));
        assert_eq!(eausvc, fs(o, other), "W19h eausvc 사실");
        assert_eq!(scan_st(vec![(5092, eausvc)], Some(1), &|_p| None, &alive), none, "W19h eausvc 훑기 = 없음");
        // W19i 출생 일치 ∧ 토큰·WTS 둘 다 없음 → 모름(규칙 2 세션 갈래를 탄다: 세션 0 ∧ 나 = 1 → 남의 것 · 세션 1 → 대상)
        assert_eq!(rf(spi, Ok((Some(T0), None)), None), fs(o, unk), "W19i 모름");
        assert_eq!(scan_st(vec![(3020, fs(o, unk))], Some(1), &|_p| None, &alive), none, "W19i 세션 0 모름 = 남의 것");
        assert_eq!(scan_st(vec![(3021, WinFacts { session: Some(1), ..fs(o, unk) })], Some(1), &|_p| None, &alive), und(3021), "W19i′ 세션 1 모름 = 대상 → 판정 불가");
        assert_eq!(sid_for_opened(Some(&sid_me), Some(&sid_sys)), Some(&sid_me[..]), "토큰 우선");
        assert_eq!(sid_for_opened(None, Some(&sid_sys)), Some(&sid_sys[..]), "토큰 실패 → WTS");
        assert_eq!(sid_for_opened(None, None), None, "둘 다 없음 = 모름");
        // W19d 핸들 생성 시각 못 읽음 · 표에 그 pid 없음 → Unverified
        assert_eq!(rf(spi, Ok((None, Some(sid_me.clone()))), None), fs(WinOpen::Unverified, unk), "W19d");
        assert_eq!(rf(None, Ok((Some(T0), Some(sid_me.clone()))), None).open, WinOpen::Unverified, "W19d′");
        // W19e 못 엶 → 오류 매핑 + WTS
        assert_eq!(rf(spi, Err(5), Some(&sid_sys)), fs(f, other), "W19e 거부 + WTS 다름");
        assert_eq!(rf(spi, Err(5), None), fs(f, unk), "W19e′ 거부 + WTS 없음");
        assert_eq!(rf(spi, Err(87), Some(&sid_me)).open, g, "W19e″ 없음");
        // W19f Unverified ∧ 세션 0 ∧ 나 = 세션 1 → 건너뛰지 않음(세션 규칙 안 탐) → 판정 불가
        assert_eq!(scan_st(vec![(3019, fs(WinOpen::Unverified, unk))], Some(1), &|_p| None, &alive), und(3019), "W19f");
        // W19g ★codex H1 끝까지: SYSTEM 프로세스(표·WTS)가 끝나고 같은 pid 를 같은 사용자 holder 가 받음 → 핸들 = 새 프로세스(출생 T1)
        //   → Unverified → 대상 → 자체 판독도 T1 ≠ 표 → 판정 불가(예전: WTS SID 다름 → 남의 것 → 건너뜀 → 작성자 둘)
        let t1 = T0 + 50_000;
        let fh = rf(spi, Ok((Some(t1), Some(sid_me.clone()))), Some(&sid_sys));
        assert_eq!(scan_st(vec![(5000, fh)], Some(1), &|p| (p == 5000).then(|| (t1, argv(&["claude", "--resume", S]))), &alive), und(5000), "W19g codex H1");
        // ★W21 수집 순서 불변식 `collect_rows_order_spi_then_wts_then_handles`(master#d82fcb00 · 뮤턴트 MO): ① 표 → ② WTS(내 세션 id 와 함께) → ③④ 행마다 핸들.
        //   ② 가 ③ 뒤로 가면 「④ 출생 일치 ⇒ ② SID 도 같은 프로세스」 추론이 무너진다.
        let log = std::cell::RefCell::new(Vec::<String>::new());
        let tbl: std::collections::HashMap<u32, (u32, Option<u64>)> = [(me, (1, Some(T0))), (5092, (0, Some(T0)))].into_iter().collect();
        let got = collect_rows(
            || {
                log.borrow_mut().push("spi".into());
                Some(tbl.clone())
            },
            |my| {
                log.borrow_mut().push(format!("wts:{my:?}"));
                [(5092u32, sid_sys.clone())].into_iter().collect()
            },
            |pid| {
                log.borrow_mut().push(format!("open:{pid}"));
                if pid == 5092 { Ok((Some(T0), None)) } else { Ok((Some(T0), Some(sid_me.clone()))) }
            },
            Some(&sid_me),
        )
        .expect("표 있음");
        let l = log.borrow().clone();
        assert_eq!(&l[..2], ["spi".to_string(), "wts:Some(1)".to_string()], "W21 collect_rows_order_spi_then_wts_then_handles: {l:?}");
        assert!(l[2..].iter().all(|x| x.starts_with("open:")) && l.len() == 4, "W21 핸들은 WTS 뒤에만: {l:?}");
        assert_eq!(got.0, Some(1), "W21 내 세션 = 표");
        let rows: std::collections::HashMap<u32, WinFacts> = got.1.into_iter().collect();
        assert_eq!(rows[&5092], WinFacts { session: Some(0), ..fs(o, other) }, "W21 eausvc 행 = WTS SYSTEM");
        assert_eq!(rows[&me].sid, same, "W21 나 = 토큰");
        assert!(collect_rows(|| None, |_| unreachable!("표 없으면 WTS 안 부름"), |_| unreachable!(), None).is_none(), "W21 표 못 읽음 = None");
        // ★W20 WTS 표 = 모든 세션 → 실패하면 내 세션(master#c699b44d 3 · 검증 R2 ②)
        let calls = std::cell::RefCell::new(Vec::new());
        let en = |ok: &'static [u32]| {
            let calls = &calls;
            move |sess: u32| -> Option<u32> {
                calls.borrow_mut().push(sess);
                ok.contains(&sess).then_some(sess)
            }
        };
        assert_eq!(wts_any_then_mine(en(&[WTS_ANY_SESSION, 1]), Some(1)), Some(WTS_ANY_SESSION), "W20a 모든 세션 성공 = 그것");
        assert_eq!(calls.replace(Vec::new()), vec![WTS_ANY_SESSION], "W20a 두 번째 호출 없음");
        assert_eq!(wts_any_then_mine(en(&[1]), Some(1)), Some(1), "W20b 모든 세션 실패 + 내 세션 성공");
        assert_eq!(calls.replace(Vec::new()), vec![WTS_ANY_SESSION, 1], "W20b 내 세션으로 재호출");
        assert_eq!(wts_any_then_mine(en(&[]), Some(1)), None, "W20c 둘 다 실패");
        assert_eq!(wts_any_then_mine(en(&[1]), None), None, "W20d 내 세션 모름 = 재호출 없음");
        // 오류 → 사실 매핑(순수 · MC·MD·ME 를 지킨다)
        assert_eq!((open_err_kind(87), open_err_kind(5), open_err_kind(31)), (WinOpen::Gone, WinOpen::Failed, WinOpen::Failed), "MC open 오류 매핑");
        assert!(matches!(probe_verdict(Err(87), None), Err(Failure::Dead)), "MD 없음 = 죽음");
        assert!(matches!(probe_verdict(Err(5), None), Err(Failure::Unknown { .. })), "MD 거부 ≠ 죽음");
        assert!(matches!(probe_verdict(Ok(()), None), Err(Failure::Unknown { .. })), "MD 종료 코드 못 읽음 ≠ 죽음");
        assert_eq!(probe_verdict(Ok(()), Some(259)), Ok(()), "MD 살아 있음");
        assert!(matches!(probe_verdict(Ok(()), Some(0)), Err(Failure::Dead)), "MD 끝남");
        let sid_a: Vec<u8> = vec![1, 1, 0, 0, 0, 0, 0, 5, 18, 0, 0, 0]; // S-1-5-18
        let sid_b: Vec<u8> = vec![1, 2, 0, 0, 0, 0, 0, 5, 21, 0, 0, 0, 7, 0, 0, 0];
        let bad: Vec<u8> = vec![1, 3, 0, 0, 0, 0, 0, 5];
        assert_eq!(sid_verdict(Some(&sid_a), Some(&sid_a)), WinSid::Same, "ME 같음");
        assert_eq!(sid_verdict(Some(&sid_a), Some(&sid_b)), WinSid::Other, "ME 다름");
        assert_eq!(sid_verdict(Some(&sid_a), None), WinSid::Unknown, "ME 토큰 못 엶 = 모름");
        assert_eq!(sid_verdict(None, Some(&sid_a)), WinSid::Unknown, "ME 내 SID 모름");
        assert_eq!(sid_verdict(Some(&sid_a), Some(&bad)), WinSid::Unknown, "ME 무효 = 모름(다름 아님)");
        // N1 안내 문구
        let n = next_action("scan:argv:4", "5e55aaaa", Path::new("/x/y.lease"));
        if cfg!(windows) {
            assert!(n.contains("Get-CimInstance Win32_Process") && !n.contains("ps -axo"), "{n}");
        } else {
            assert!(n.contains("ps -axo pid,command | grep -i 5e55aaaa"), "{n}");
        }
    }

    /// codex 1R B1 — 명령줄 판독 실패를 「사라짐」으로 빼지 않는다 · UID 판독 실패를 남의 것으로 치지 않는다.
    #[test]
    fn argv_scan_never_turns_unreadable_into_none() {
        use crate::process_observation::Failure;
        let pv = |pid: u32, uid: Option<u32>, cmd: &[&str]| ProcView { pid, uid, skip: false, foreign: false, cmd: cmd.iter().map(|s| s.to_string()).collect() };
        // UID 판독 실패 + 명령줄 읽힘 + 그 대화 = 작성자로 본다(예전: 남의 것으로 건너뜀).
        let (hit, _) = classify_argv(&[pv(41, None, &["claude", "--resume", "abc"])], "abc", &[], Some(501));
        assert!(hit.is_some(), "UID 판독 실패를 남의 프로세스로 쳤다");
        // UID 판독 실패 + 명령줄 못 읽음 = 판정 불가 후보.
        let (hit, unr) = classify_argv(&[pv(42, None, &[])], "abc", &[], Some(501));
        assert!(hit.is_none());
        assert_eq!(unr, vec![42]);
        // 확인된 남의 UID 는 건너뜀 · 내 UID 의 다른 대화도 건너뜀.
        let (hit, unr) = classify_argv(&[pv(43, Some(0), &[]), pv(44, Some(501), &["x", "--resume=abd"])], "abc", &[], Some(501));
        assert!(hit.is_none() && unr.is_empty());
        // 재확인: 죽음 확인만 빠지고, 살아 있음·EPERM·변경·미지원은 남는다.
        let probe = |p: u32| match p {
            1 => Err(Failure::Dead),
            2 => Ok(()),
            3 => Err(Failure::Unknown { stage: "proc_pidinfo", os_error: Some(1) }),
            4 => Err(Failure::Changed),
            _ => Err(Failure::UnsupportedPlatform),
        };
        assert_eq!(drop_confirmed_dead(vec![1, 2, 3, 4, 5], probe), vec![2, 3, 4, 5]);
    }

    /// B1 두 번째 UID 판독기(실기) — 나 = 내 UID · launchd/init(pid 1, root) = 남의 것. sysinfo 가 UID 를 못 주는 남의 프로세스를
    /// 판정 불가로 남기면 모든 복원이 93 이 된다(11-11 실측: root nesessionmanager 1건으로 bench 100회 전부 거절).
    #[cfg(unix)]
    #[test]
    fn owner_uid_fallback_tells_mine_from_others() {
        // SAFETY: getuid 는 부작용 없는 조회.
        let me = unsafe { libc::getuid() };
        if me == 0 {
            return; // root 로 돌면 pid 1 도 내 것 — 시험 전제 밖
        }
        let o = OwnerUid::snapshot(me);
        assert_eq!(o.of(std::process::id()), Some(me));
        assert_ne!(o.of(1), Some(me), "root 프로세스를 내 것으로 쳤다");
        assert!(o.of(1).is_some(), "두 번째 판독기가 pid 1 을 판정하지 못했다");
    }

    /// 동시 인수 경합 — 죽은 작성자의 임대를 여러 스레드가 **같은 순간에**(장벽) 넘겨받으려 하고, 판정 중 생존 판독이 느리다(30ms).
    /// 잠금이 있으면 하나만 이긴다 · 잠금이 없으면(독립 검증 M16) 모두 같은 옛 기록을 읽고 판정하는 사이 겹쳐 여럿이 이긴다.
    #[test]
    fn concurrent_acquire_single_winner() {
        const DEAD: u32 = 999;
        let d = tmp("cc");
        let s = Store::open(&d).unwrap();
        // 죽은 작성자의 임대를 먼저 깐다(판정이 holder 를 부르게).
        let w0 = Fake::new();
        let Decision::Granted(g) = acquire(&s, "CC", &cx(h(1), &w0)) else { panic!() };
        g.hold(Some(h(DEAD))).unwrap();
        let n = 8;
        let wins = std::sync::Arc::new(std::sync::atomic::AtomicUsize::new(0));
        // 진 쪽은 모두 「살아 있는 보유자」(Live)여야 한다 — 잠금 없이 임시 파일 경합으로 쓰기 실패(판정 불가)가 나도 붉게(독립 재검 m5).
        let odd = std::sync::Arc::new(std::sync::atomic::AtomicUsize::new(0));
        let gate = std::sync::Arc::new(std::sync::Barrier::new(n));
        let ths: Vec<_> = (0..n)
            .map(|i| {
                let s = s.clone();
                let wins = wins.clone();
                let odd = odd.clone();
                let gate = gate.clone();
                std::thread::spawn(move || {
                    struct W;
                    impl World for W {
                        fn holder(&self, h: &Holder) -> Liveness {
                            std::thread::sleep(Duration::from_millis(30));
                            if h.pid == DEAD { Liveness::Dead } else { Liveness::Alive }
                        }
                        fn seat(&self, _s: u64, _g: Option<&str>, _strict: bool) -> Liveness { Liveness::Dead }
                        fn evidence(&self, _n: &str) -> Evidence { Evidence::NoneConfirmed }
                        fn now(&self) -> u64 { 1 }
                    }
                    gate.wait();
                    match acquire(&s, "CC", &AcquireCtx { me: h(100 + i as u32), surface_id: None, daemon_gen: None, cfg: None, world: &W }) {
                        Decision::Granted(g) => {
                            wins.fetch_add(1, std::sync::atomic::Ordering::SeqCst);
                            std::thread::sleep(Duration::from_millis(50));
                            let _ = g.hold(Some(h(200)));
                        }
                        Decision::Live { .. } | Decision::AlreadyMine => {}
                        Decision::Undecided { .. } => {
                            odd.fetch_add(1, std::sync::atomic::Ordering::SeqCst);
                        }
                    }
                })
            })
            .collect();
        for t in ths {
            t.join().unwrap();
        }
        assert_eq!(wins.load(std::sync::atomic::Ordering::SeqCst), 1, "동시 인수에서 여럿이 이겼다");
        assert_eq!(odd.load(std::sync::atomic::Ordering::SeqCst), 0, "동시 인수에서 판정 불가(쓰기 경합)가 났다");
        mine_set("cc", None);
        let _ = std::fs::remove_dir_all(&d);
    }

    /// 독립 검증 F5 — M05: 좌석 기록 없는 결과 불명 임대는 넘겨받지 않는다(판정 불가) · M11: 남의 소유 파일 = U4 · M12: 열거 실패 = 판정 불가 · F6: 쓰기 실패 다음 행동.
    #[test]
    fn verify_f5_holes_are_closed() {
        // M05
        let d = tmp("m05");
        let s = Store::open(&d).unwrap();
        std::fs::write(s.file_of("m05"), r#"{"v":1,"id":"m05","fence":1,"token":"t","state":"unknown","writer":null,"restorer":{"pid":2147483632,"birth_s":1,"birth_us":0},"surface_id":null,"daemon_gen":null,"cfg":null,"at":1}"#).unwrap();
        match acquire(&s, "M05", &cx(h(10), &Fake::new())) {
            Decision::Undecided { reason, .. } => assert!(reason.starts_with("lease:outcome-unknown"), "{reason}"),
            o => panic!("좌석 없는 결과 불명 임대를 넘겨받았다: {o:?}"),
        }
        let _ = std::fs::remove_dir_all(&d);
        // M11
        assert_eq!(opened_verdict(true, 501, 501, 0o600), Ok(false));
        assert_eq!(opened_verdict(true, 501, 501, 0o644), Ok(true));
        assert_eq!(opened_verdict(true, 0, 501, 0o600), Err("kind:owner".into()), "남의 소유 임대 파일을 받았다");
        assert_eq!(opened_verdict(false, 501, 501, 0o600), Err("kind:not-regular".into()));
        // M12 — 실제 판정 함수에 빈 열거 · 나 자신 없는 열거를 넣는다.
        let ok = |_p: u32| -> Result<(), crate::process_observation::Failure> { Ok(()) };
        assert_eq!(scan_argv_with("x", &[], Some(501), Vec::new, ok), Evidence::Undecided("scan:enumerate".into()), "빈 열거를 없음으로 쳤다");
        let other = || vec![ProcView { pid: 1, uid: Some(0), skip: false, foreign: false, cmd: vec!["launchd".into()] }];
        assert_eq!(scan_argv_with("x", &[], Some(501), other, ok), Evidence::Undecided("scan:enumerate".into()));
        let me = || vec![ProcView { pid: std::process::id(), uid: Some(501), skip: false, foreign: false, cmd: vec!["t".into()] }];
        assert_eq!(scan_argv_with("x", &[], Some(501), me, ok), Evidence::NoneConfirmed, "정상 열거");
        // F6
        let n = next_action("lease:write:tmp:errno:28", "abc", Path::new("/x/y/abc.lease"));
        assert!(n.contains("df -h /x/y"), "{n}");
    }
}

/// 조건 ③ 「복원 1건당 늘어난 시간」 — 임대 판정 구간(잠금 → 판정 → 기록 → argv 훑기 · 데몬 조회 제외)만 단조 시계로 잰다.
/// 실행: `cargo test --lib session_lease::bench -- --ignored --nocapture`(기본 시험에서 제외).
#[cfg(test)]
mod bench {
    use super::*;

    struct Real;
    impl World for Real {
        fn holder(&self, h: &Holder) -> Liveness { probe_holder(h) }
        fn seat(&self, _s: u64, _g: Option<&str>, _strict: bool) -> Liveness { Liveness::Dead }
        fn evidence(&self, n: &str) -> Evidence { scan_argv(n, &self_and_ancestors()) }
        fn now(&self) -> u64 { now_secs() }
    }

    #[test]
    #[ignore = "측정 전용"]
    fn lease_segment_timing() {
        let d = std::env::temp_dir().join(format!("slb-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&d);
        let s = Store::open(&d).unwrap();
        let mut ms: Vec<f64> = Vec::new();
        for i in 0..100 {
            let t0 = Instant::now();
            let cx = AcquireCtx { me: me().unwrap(), surface_id: None, daemon_gen: None, cfg: None, world: &Real };
            match acquire(&s, &format!("bench-{i}"), &cx) {
                Decision::Granted(g) => g.hold(None).unwrap(),
                o => panic!("{o:?}"),
            }
            ms.push(t0.elapsed().as_secs_f64() * 1000.0);
        }
        ms.sort_by(|a, b| a.partial_cmp(b).unwrap());
        let q = |p: f64| ms[((ms.len() as f64 - 1.0) * p).round() as usize];
        eprintln!("LEASE SEGMENT ms n=100 median={:.1} p95={:.1} max={:.1}", q(0.5), q(0.95), q(1.0));
        let _ = std::fs::remove_dir_all(&d);
    }
}
