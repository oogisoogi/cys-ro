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
        "scan" => format!("`ps -axo pid,command | grep -i {short}` 로 이 대화를 쥔 프로세스를 확인한 뒤 다시 실행하세요"),
        _ => format!("`cys status` 와 `ps -axo pid,command | grep -i {short}` 로 확인한 뒤 다시 실행하세요"),
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
    scan_argv_with(norm, exclude, my_uid, || real_snapshot(my_uid), |p| crate::process_observation::identity(p).map(|_| ()))
}

/// 실제 프로세스 훑기 한 번(sysinfo) — 판정은 [`scan_argv_with`] 가 한다.
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
    /// 빈 값 = 명령줄을 못 읽음.
    pub cmd: Vec<String>,
}

/// (작성자로 보이는 것, 명령줄을 못 읽은 pid) — `my_uid` = None 이면 UID 로 거르지 않는다(윈).
/// UID 판독 실패는 「남의 것」으로 치지 않는다: 명령줄을 읽었으면 그대로 보고, 못 읽었으면 판정 불가 후보(codex 1R B1).
pub(crate) fn classify_argv(view: &[ProcView], norm: &str, exclude: &[u32], my_uid: Option<u32>) -> (Option<String>, Vec<u32>) {
    let mut unreadable = Vec::new();
    for p in view {
        if exclude.contains(&p.pid) || p.pid == std::process::id() || p.skip {
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

    /// codex 1R B1 — 명령줄 판독 실패를 「사라짐」으로 빼지 않는다 · UID 판독 실패를 남의 것으로 치지 않는다.
    #[test]
    fn argv_scan_never_turns_unreadable_into_none() {
        use crate::process_observation::Failure;
        let pv = |pid: u32, uid: Option<u32>, cmd: &[&str]| ProcView { pid, uid, skip: false, cmd: cmd.iter().map(|s| s.to_string()).collect() };
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
        let other = || vec![ProcView { pid: 1, uid: Some(0), skip: false, cmd: vec!["launchd".into()] }];
        assert_eq!(scan_argv_with("x", &[], Some(501), other, ok), Evidence::Undecided("scan:enumerate".into()));
        let me = || vec![ProcView { pid: std::process::id(), uid: Some(501), skip: false, cmd: vec!["t".into()] }];
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
