//! TICKET=cysr-seatkeep-t1 — `cys` 쪽 임대 접착(데몬 조회 · 표시 줄 · rc). 판정 본체 = `cys::session_lease`(leaf).
//! `src/bin/cys.rs` 에 `#[path]` 한 줄로 붙는다 — cys.rs 의 기존 함수에는 호출 배선만 둔다(병합 충돌 축소).

use super::*;
use cys::session_lease::{self as sl, Decision, Evidence, Holder, Liveness, Store, World};

/// rc — 같은 대화를 살아 있는 다른 프로세스가 쓰는 중이라 띄우지 않음.
pub(crate) const EXIT_SESSION_WRITER_LIVE: i32 = 92;
/// rc — 그 대화의 작성자가 살아 있는지 판정하지 못해 띄우지 않음(「없음」으로 치지 않는다).
pub(crate) const EXIT_SESSION_LIVENESS_UNKNOWN: i32 = 93;

pub(crate) fn lease_store() -> Result<Store, String> {
    // 시험 빌드 가드(master#ae3bad7d · 11-11 사고: HOME 미격리 시험 5개가 실제 ~/.local/state/cys/session-leases 를 만들었다) —
    //   시험이 실제 계정 HOME 에서 임대 폴더를 열려 하면 디스크를 건드리기 **전에** 실패한다.
    #[cfg(test)]
    if let Some(why) = test_home_guard(&cys::home_dir(), test_real_home().as_deref()) {
        panic!("{why}");
    }
    let root = sl::default_root(&cys::home_dir(), cfg!(windows), std::env::var_os("LOCALAPPDATA").map(std::path::PathBuf::from));
    Store::open(&root)
}

/// 시험용: 이 계정의 실제 홈(passwd) — `CYS_TEST_REAL_HOME` 이 있으면 그것(가드 자신의 시험이 임시 폴더로 흉내 내는 길).
#[cfg(test)]
pub(crate) fn test_real_home() -> Option<std::path::PathBuf> {
    if let Some(v) = std::env::var_os("CYS_TEST_REAL_HOME") {
        return Some(v.into());
    }
    // 비-유닉스 = passwd 없음 → None(= 가드가 「실제 홈 모름 → 실패(안전 쪽)」로 처리 · TICKET=cysr-1116-wincompile-1121).
    #[cfg(not(unix))]
    return None;
    // SAFETY: getpwuid 는 정적 버퍼를 돌려준다 — 시험 전용 · 곧바로 복사.
    #[cfg(unix)]
    unsafe {
        let pw = libc::getpwuid(libc::getuid());
        if pw.is_null() || (*pw).pw_dir.is_null() {
            return None;
        }
        Some(std::ffi::CStr::from_ptr((*pw).pw_dir).to_string_lossy().into_owned().into())
    }
}

/// 시험용(순수): 지금 HOME 이 실제 홈이면 실패 사유. 실제 홈을 모르면 실패(안전 쪽).
#[cfg(test)]
pub(crate) fn test_home_guard(home: &std::path::Path, real: Option<&std::path::Path>) -> Option<String> {
    let canon = |p: &std::path::Path| std::fs::canonicalize(p).unwrap_or_else(|_| p.to_path_buf());
    match real {
        None => Some("session_lease 시험 가드: 실제 홈을 알 수 없어 임대 폴더를 열지 않음 — 시험은 HOME 을 임시 폴더로 격리하라".into()),
        Some(r) if canon(home) == canon(r) => Some(format!(
            "session_lease 시험 가드: 시험이 실제 HOME({}) 의 임대 폴더를 열려 함 — HOME 을 임시 폴더로 격리하라(11-11 사고 재발 방지)",
            home.display()
        )),
        Some(_) => None,
    }
}

/// 지금 데몬의 세대(`<pid>-<started_at>`) — 실패 = None.
fn current_gen() -> Option<String> {
    restore_daemon_gen()
}

/// 운영 세계 — 보유자 = 프로세스 신원 · 좌석 = 데몬 surface.list · 증거 = 데몬 live 세션 + argv 훑기.
pub(crate) struct CliWorld {
    exclude: Vec<u32>,
}

impl CliWorld {
    pub(crate) fn new() -> Self {
        CliWorld { exclude: sl::self_and_ancestors() }
    }
}

impl World for CliWorld {
    fn holder(&self, h: &Holder) -> Liveness {
        sl::probe_holder(h)
    }

    /// 작성자 신원이 아직 없는 임대의 좌석. T1 전제: 그 임대의 데몬이 죽었으면 좌석도 함께 내려갔다(SIGHUP · DESIGN §1-2).
    /// 세대가 다르다는 것만으로는 죽음이 아니다 — 임대 폴더는 사용자 단위라 살아 있는 다른 데몬(부서 데몬 등)의 임대도 보인다(codex 1R B3).
    /// ⚠좌석 보유 장치(T2~T4)가 켜지면 「데몬 죽음 = 좌석 죽음」 전제가 깨진다 — T4 입양이 임대를 다시 확인해야 한다(DESIGN T0 §3 단계 4).
    fn seat(&self, surface_id: u64, daemon_gen: Option<&str>, strict: bool) -> Liveness {
        let Some(now_gen) = current_gen() else {
            return Liveness::Undecided("daemon:unreachable".into());
        };
        // 세대 기록이 없는 임대 = 그 좌석이 어느 데몬 것인지 모름 → 판정 불가(지금 데몬의 목록으로 죽음을 단정하지 않는다 · codex 2R B3).
        let Some(g) = daemon_gen else {
            return Liveness::Undecided(format!("daemon:gen-unknown:{surface_id}"));
        };
        if g != now_gen {
            return other_gen_seat(g, surface_id, cys::process_observation::identity);
        }
        let Ok(list) = request("surface.list", json!({})) else {
            return Liveness::Undecided("daemon:unreachable".into());
        };
        // 원소 형식도 본다 — 번호 없는 원소가 있으면 「없음 = 죽음」을 단정할 수 없다.
        let Some(all) = list["surfaces"].as_array().filter(|a| a.iter().all(|s| s["surface_id"].as_u64().is_some())) else {
            return Liveness::Undecided("daemon:malformed-surface-list".into());
        };
        let found = all.iter().find(|s| s["surface_id"].as_u64() == Some(surface_id));
        // 판정에 쓰는 필드의 형식(데몬 계약: exited bool · seat occupied|empty|unknown · agent_alive bool|null) — 어긋나면 판정 불가(codex 3R).
        if found.is_some_and(|s| !list_entry_ok(s)) {
            return Liveness::Undecided("daemon:malformed-surface-list".into());
        }
        match found {
            None => Liveness::Dead,
            Some(s) if s["exited"].as_bool() == Some(true) => Liveness::Dead,
            // 결과 불명(strict): 빈 셸이어도 큐의 기동 명령이 아직 닿을 수 있다 → 확정 종료(소멸·exited)가 아니면 판정 불가.
            Some(s) if strict && s["seat"].as_str() == Some("empty") && s["agent_alive"].as_bool() != Some(true) => {
                Liveness::Undecided(format!("daemon:seat-empty-unconfirmed:{surface_id}"))
            }
            Some(s) if s["seat"].as_str() == Some("empty") && s["agent_alive"].as_bool() != Some(true) => Liveness::Dead,
            Some(_) => Liveness::Alive,
        }
    }

    /// 좌석의 **현재 대화 증거**(skt1 · codex r5c #1·#4) = [`seat_conversation_now`] — claude 좌석 = 작성자 신원으로 묶인 임대(등록 문자열 아님) ·
    /// 등록 경로 없는 에이전트(codex 등) = 데몬 관측(topology). 세대 다름·없음·판독 실패 = Err(풀 근거 없음 = 막음).
    fn seat_conversation(&self, surface_id: u64, daemon_gen: Option<&str>) -> Result<Option<String>, String> {
        let same_gen = || current_gen().is_some_and(|g| daemon_gen == Some(g.as_str()));
        if !same_gen() {
            return Err("daemon:other-gen".into());
        }
        let r = seat_conversation_now(surface_id, daemon_gen.unwrap_or_default())?;
        // 판독 사이 데몬이 바뀌었으면 그 값은 이 임대의 좌석 것이 아니다.
        if !same_gen() {
            return Err("daemon:other-gen".into());
        }
        Ok(r)
    }

    fn evidence(&self, norm: &str) -> Evidence {
        let topo = match request("system.topology", json!({})) {
            Ok(t) => t,
            Err(_) => return Evidence::Undecided("daemon:unreachable".into()),
        };
        // 형식 이상(live 가 배열 아님) = 판정 불가 — 빈 목록으로 치지 않는다(codex 1R B1).
        // 원소는 객체 · session_id 는 없거나 문자열(있는데 다른 형식 = 그 좌석의 대화를 모름).
        let Some(live) = topo["live"].as_array().filter(|a| a.iter().all(live_entry_ok)) else {
            return Evidence::Undecided("daemon:malformed-topology".into());
        };
        let seen = live.iter().find(|e| {
            e["seat"].as_str() != Some("empty")
                && e["session_id"].as_str().and_then(sl::norm_id).as_deref() == Some(norm)
        });
        if let Some(e) = seen {
            return Evidence::Seen(format!(
                "데몬 좌석 surface:{}(역할 {}) 가 이 대화를 잇는 중",
                e["surface_id"].as_u64().unwrap_or(0),
                e["role"].as_str().unwrap_or("?")
            ));
        }
        // ⚠codex 1R M4(낡은 argv)는 고치지 않는다(codex 2R blocking): 「다른 대화 임대의 작성자」라는 기록만으로는 그 작성자가 좌석 안
        //   /resume 으로 이 대화에 돌아왔는데 등록(SessionStart)이 아직 안 닿은 순간과 가를 수 없다 → 제외하면 작성자 둘의 창이 생긴다.
        //   남는 것 = 낡은 argv 의 거짓 막힘(92 · 사유 줄에 pid · 안전 쪽) — DESIGN §13 에 적음.
        // ★5회차(master 설계 2): 윈 주인 후보 이름 집합에 데몬 좌석 메타 agent_bin 을 더한다(agents.json 이 그 뒤 바뀌었어도 떠 있는 좌석의 실제 실행 파일) ·
        //   ★codex 5R H4(fail-closed): 판독 실패·형식 이상 = None → 이름 좁히기 전체 끔. 유닉스 = 이름 집합을 쓰지 않으므로 묻지 않는다(빈 목록).
        let seat_bins = if cfg!(windows) { seat_agent_bins(request("surface.list", json!({})).ok().as_ref()) } else { Some(Vec::new()) };
        // ★TICKET=cysr-1118-seat ①: 바깥 증거 ⓒ(claude 세션 등록 파일) — 명령줄에 대화 id 가 없는 작성자(`claude --continue` · 세션 안 `/resume`)를 본다.
        //   등록이 Seen 이면 argv 훑기 없이 막는다 · 그 밖은 둘을 합친다(하나라도 판정 불가면 판정 불가).
        let reg = sl::scan_registry(norm, &self.exclude, &cys::home_dir());
        if matches!(reg, Evidence::Seen(_)) {
            return reg;
        }
        sl::combine_evidence(sl::scan_argv(norm, &self.exclude, seat_bins.as_deref()), reg)
    }

    fn now(&self) -> u64 {
        sl::now_secs()
    }
}

/// `surface.list` 응답 → 좌석 메타 agent_bin 목록(순수 · codex 5R H4 fail-closed) — 응답 없음 · `surfaces` 가 배열 아님 · 좌석이 객체 아님 ·
/// agent_bin 이 문자열·null·없음 외의 값 · 빈 문자열 = None(= 이름 좁히기 끔). null·키 없음 = 에이전트 메타 없는 좌석(건너뜀).
pub(crate) fn seat_agent_bins(list: Option<&Value>) -> Option<Vec<String>> {
    let mut out = Vec::new();
    for s in list?.get("surfaces")?.as_array()? {
        match s.as_object()?.get("agent_bin") {
            None | Some(Value::Null) => {}
            Some(Value::String(b)) if !b.trim().is_empty() => out.push(b.clone()),
            Some(_) => return None,
        }
    }
    Some(out)
}

fn seat_word_ok(v: &Value) -> bool {
    matches!(v.as_str(), Some("occupied" | "empty" | "unknown"))
}

/// `system.topology` live 원소 계약(cysd handlers `system.topology`): surface_id 수 · seat 세 낱말 · session_id 키 있음(문자열 또는 null · 1.1.9~).
/// 빈 객체·필수 필드 결측·형식 이상 = 그 좌석이 어느 대화를 잇는지 모름 → 판정 불가(없음으로 치지 않는다 · codex 3R).
pub(crate) fn live_entry_ok(e: &Value) -> bool {
    e["surface_id"].as_u64().is_some()
        && seat_word_ok(&e["seat"])
        && e.get("session_id").is_some_and(|v| v.is_null() || v.is_string())
}

/// `surface.list` 원소 계약 중 좌석 생존 판정에 쓰는 필드: exited bool · seat 세 낱말 · agent_alive bool 또는 null(3값).
pub(crate) fn list_entry_ok(e: &Value) -> bool {
    e["exited"].is_boolean() && seat_word_ok(&e["seat"]) && e.get("agent_alive").is_some_and(|v| v.is_null() || v.is_boolean())
}

/// 지금 데몬과 세대가 다른 임대의 좌석 — 그 세대(`<pid>-<started_at>`)의 데몬이 죽음 확인이면 Dead(좌석도 함께 내려감),
/// 살아 있으면(같은 pid · 출생 ≤ started_at) 그 데몬 좌석을 이 데몬에서 볼 수 없으므로 판정 불가, 판독 실패도 판정 불가.
/// pid 재사용(출생이 started_at 보다 뒤) = 그 데몬은 죽음.
pub(crate) fn other_gen_seat(
    gen: &str,
    surface_id: u64,
    probe: impl Fn(u32) -> Result<cys::process_observation::Identity, cys::process_observation::Failure>,
) -> Liveness {
    use cys::process_observation::Failure;
    let parsed = gen.split_once('-').and_then(|(p, t)| Some((p.parse::<u32>().ok()?, t.parse::<f64>().ok()?)));
    let Some((pid, started)) = parsed else {
        return Liveness::Undecided(format!("daemon:other-gen-malformed:{surface_id}"));
    };
    match probe(pid) {
        Err(Failure::Dead) => Liveness::Dead,
        Ok(id) if (id.birth_seconds as f64) > started + 1.0 => Liveness::Dead,
        Ok(_) => Liveness::Undecided(format!("daemon:other-gen-alive:{pid}:{surface_id}")),
        Err(_) => Liveness::Undecided(format!("daemon:other-gen-probe:{pid}:{surface_id}")),
    }
}

/// 복원 입구의 임대 관문 결과.
pub(crate) enum LeaseGate {
    /// 노브 끔 · 대화 없음 — 종전 경로.
    Off,
    /// 진행(가드 = 이 호출이 잡은 임대 · None = 바깥 갈래가 이미 쥠).
    Proceed(Option<sl::Guard>),
    /// 띄우지 않음 — rc 와 사람이 읽는 줄.
    Refuse { rc: i32, line: String },
}

/// 사람·판독기가 읽는 줄의 대화 표기 = **전체 id**(skt1 · codex r5c #3 「첫 거절의 전체 대화 ID 보존」 — 앱은 이 값으로 대화 임대를 찾는다 ·
/// 종전 앞 8자는 다른 대화와 접두가 겹칠 수 있다). 이름은 호출 자리 변경을 줄이려 그대로 둔다.
fn short(id: &str) -> String {
    id.trim().to_string()
}

/// 대화 `sess` 를 이어도 되는가 — 좌석을 **만들기 전에** 부른다. 복원 입구 셋(restore · --resume-saved · node-recover) 공통.
/// `claim_dir` = 옛 판 복원기의 claim 폴더 — 60초 안 옛 claim 은 동률로 존중(master#388727f0 M3 = B · 세 입구 모두).
pub(crate) fn lease_gate(role: &str, sess: Option<&str>, surface_id: Option<u64>, cfg: Option<&str>, claim_dir: Option<&std::path::Path>) -> LeaseGate {
    if !sl::enabled() {
        return LeaseGate::Off;
    }
    let Some(id) = sess.and_then(sl::norm_id) else {
        return LeaseGate::Off;
    };
    let tie = match foreign_claim_fresh(sess.unwrap_or_default(), claim_dir) {
        Ok(t) => t,
        Err(r) => {
            return LeaseGate::Refuse {
                rc: EXIT_SESSION_LIVENESS_UNKNOWN,
                line: format!("· {role}: 대화 {} 작성자 생존 판정 불가({r}) — 띄우지 않음 · 확인: 옛 복원 claim 폴더의 그 파일을 확인하세요", short(&id)),
            }
        }
    };
    if tie {
        return LeaseGate::Refuse {
            rc: EXIT_SESSION_WRITER_LIVE,
            line: format!(
                "· {role}: 대화 {} — 옛 판 복원기가 {FOREIGN_CLAIM_TIE_SECS}초 안에 잡은 claim 이 있음 — 띄우지 않음(잠시 뒤 다시)",
                short(&id)
            ),
        };
    }
    let me = match sl::me() {
        Some(m) => m,
        None => {
            return LeaseGate::Refuse {
                rc: EXIT_SESSION_LIVENESS_UNKNOWN,
                line: format!(
                    "· {role}: 대화 {} 작성자 생존 판정 불가(probe:self) — 띄우지 않음 · 확인: `{}=off` 로 종전 방식을 쓰거나 master 에 알리세요",
                    short(&id),
                    sl::KNOB
                ),
            }
        }
    };
    let store = match lease_store() {
        Ok(s) => s,
        Err(r) => {
            let next = sl::next_action(&r, &id, &std::path::PathBuf::from("<임대 폴더>/x.lease"));
            return LeaseGate::Refuse {
                rc: EXIT_SESSION_LIVENESS_UNKNOWN,
                line: format!("· {role}: 대화 {} 작성자 생존 판정 불가({r}) — 띄우지 않음 · 확인: {next}", short(&id)),
            };
        }
    };
    // ★skt1(독립 검증 V6): 데몬 세대를 못 읽으면 잡지 않는다 — 세대 없는 임대는 이후 모든 복원이 `daemon:gen-unknown` 93 으로 읽고
    //   follow 도 승계하지 못해 손으로 지우기 전까지 그 대화가 영구 판정 불가가 됐다. 지금 멈추면 데몬이 답하는 다음 회차에 그대로 풀린다.
    let Some(gen) = current_gen() else {
        return LeaseGate::Refuse {
            rc: EXIT_SESSION_LIVENESS_UNKNOWN,
            line: format!(
                "· {role}: 대화 {} 작성자 생존 판정 불가(daemon:gen-unreadable) — 띄우지 않음 · 확인: `cys status` 로 데몬이 응답하는지 본 뒤 다시 실행하세요(임대는 만들지 않았습니다)",
                short(&id)
            ),
        };
    };
    let world = CliWorld::new();
    let cx = sl::AcquireCtx { me, surface_id, daemon_gen: Some(gen), cfg: cfg.map(String::from), world: &world };
    match sl::acquire(&store, &id, &cx) {
        Decision::Granted(g) => LeaseGate::Proceed(Some(g)),
        Decision::AlreadyMine => LeaseGate::Proceed(None),
        Decision::Live { who } => LeaseGate::Refuse {
            rc: EXIT_SESSION_WRITER_LIVE,
            line: format!("· {role}: 대화 {} — {who} — 띄우지 않음(같은 대화 작성자 둘 차단 · 새 대화로도 띄우지 않음)", short(&id)),
        },
        Decision::Undecided { reason, next } => LeaseGate::Refuse {
            rc: EXIT_SESSION_LIVENESS_UNKNOWN,
            line: format!("· {role}: 대화 {} 작성자 생존 판정 불가({reason}) — 띄우지 않음 · 확인: {next}", short(&id)),
        },
    }
}

/// 이 프로세스가 지금 그 대화의 임대를 **잡아서** 쥐고 있는가(인수·획득 회차) — 등록부 + 디스크의 현재 임대(codex 2R M2).
pub(crate) fn lease_mine(sess: Option<&str>) -> bool {
    sl::enabled() && sess.and_then(sl::norm_id).is_some_and(|n| lease_store().is_ok_and(|s| sl::is_mine_on_disk(&s, &n)))
}

/// 새 좌석이 정해진 직후(기동 명령 전) — 이 프로세스가 쥔 임대에 좌석을 적는다.
/// 적지 못하면 Err(`session_lease:` 머리 · 호출자 = 기동 중단 · rc 93) — 좌석 없는 기동 중 임대는 복원기가 끝난 뒤 「아무것도 안 떴다」로
/// 읽혀 넘겨진다(codex 2R major). 임대를 쥐지 않은 갈래(노브 끔 · 대화 없음 · 등록부 없음)는 할 일 없음.
pub(crate) fn lease_note_surface(sess: Option<&str>, surface_id: u64) -> Result<(), String> {
    let Some(n) = sess.and_then(sl::norm_id) else { return Ok(()) };
    if !sl::enabled() || !sl::is_mine(&n) {
        return Ok(());
    }
    let ok = lease_store().is_ok_and(|store| sl::set_surface_mine(&store, &n, surface_id, current_gen()));
    if ok {
        Ok(())
    } else {
        Err(format!("session_lease: 대화 {} 의 임대에 좌석 surface:{surface_id} 를 적지 못함(잠금 시한·쓰기 실패·임대가 넘어감) — 기동하지 않음", short(&n)))
    }
}

/// 좌석 `surface_id` 의 뿌리 pid(데몬 surface.list).
fn seat_root_pid(surface_id: u64) -> Option<u32> {
    let list = request("surface.list", json!({})).ok()?;
    list["surfaces"]
        .as_array()?
        .iter()
        .find(|s| s["surface_id"].as_u64() == Some(surface_id))?["pid"]
        .as_u64()
        .map(|p| p as u32)
}

/// 기동 뒤 그 좌석에서 대화를 쓰는 프로세스 — argv 에 그 id 가 있고 좌석 뿌리의 자손(또는 뿌리 자신)인 것.
pub(crate) fn lease_find_writer(surface_id: u64, sess: &str) -> Option<Holder> {
    use sysinfo::{ProcessRefreshKind, ProcessesToUpdate, System, UpdateKind};
    let norm = sl::norm_id(sess)?;
    let root = seat_root_pid(surface_id)?;
    for attempt in 0..3 {
        let mut sys = System::new();
        sys.refresh_processes_specifics(ProcessesToUpdate::All, true, ProcessRefreshKind::nothing().with_cmd(UpdateKind::Always));
        for (pid, p) in sys.processes() {
            let hit = p.cmd().iter().any(|a| {
                let a = a.to_string_lossy().to_ascii_lowercase();
                a == norm || a.ends_with(&format!("={norm}"))
            });
            if !hit {
                continue;
            }
            let pid = pid.as_u32();
            let mut cur = pid;
            for _ in 0..64 {
                if cur == root {
                    return cys::process_observation::identity(pid).ok().map(|i| sl::holder_of(&i));
                }
                match cys::process_observation::identity(cur) {
                    Ok(i) if i.parent > 1 => cur = i.parent,
                    _ => break,
                }
            }
        }
        if attempt < 2 {
            std::thread::sleep(std::time::Duration::from_millis(500));
        }
    }
    None
}

/// 기동 명령을 친 좌석(이 프로세스 안) → 그 기동이 저장 대화를 실제로 잇는가(`--resume` 접미 부착).
/// `boot_agent_on_surface` 가 기동 명령을 보내기 **직전에** 적는다(codex 6R): 그 뒤의 오류는 「안 떴다」가 아니라 결과 불명이고,
/// 접미 없이(새 대화로) 뜬 기동은 저장 대화의 임대를 쥐면 안 된다.
static LAUNCHED: std::sync::Mutex<Option<std::collections::HashMap<u64, bool>>> = std::sync::Mutex::new(None);

pub(crate) fn lease_note_launch(surface_id: u64, resumed: bool) {
    LAUNCHED.lock().unwrap_or_else(|e| e.into_inner()).get_or_insert_with(Default::default).insert(surface_id, resumed);
}

/// 시험 전용 — 프로세스 전역 기록 비우기(시험 사이 좌석 번호 기록이 새지 않게).
#[cfg(test)]
pub(crate) fn lease_forget_launches() {
    *LAUNCHED.lock().unwrap_or_else(|e| e.into_inner()) = None;
}

fn launched(surface_id: u64) -> Option<bool> {
    LAUNCHED.lock().unwrap_or_else(|e| e.into_inner()).as_ref().and_then(|m| m.get(&surface_id).copied())
}

/// 이 프로세스가 그 좌석에 **저장 대화를 잇는**(접미 부착) 기동 명령 글을 보냈는가(보낸 뒤의 오류 = 결과 불명).
/// 접미 없이(새 대화로) 보낸 기동은 아니다 — 그 좌석은 저장 대화의 작성자가 될 수 없다(codex 1R C1).
pub(crate) fn lease_launch_sent(surface_id: u64) -> bool {
    launched(surface_id) == Some(true)
}

/// 재반환 좌석 판정 결과를 실어 나르는 오류 머리(r4 A) — `run_launch_agent_opts` 가 rc 93 으로 바꾼다(그 좌석은 남의 것일 수 있어 닫지 않는다).
pub(crate) const ERR_REUSED_OTHER: &str = "session_lease:reused-other";
pub(crate) const ERR_REUSED_UNKNOWN: &str = "session_lease:reused-unknown";

/// 멱등 재반환(`idempotent_reuse`) + 에이전트가 살아 있어 기동을 건너뛴 좌석이 이 저장 대화를 잇는가(r4 A · codex 3R ①②③).
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) enum ReusedSeat {
    /// 이 실행이 이 대화의 임대를 쥐지 않음(노브 끔·대화 없음) — 종전(rc 0 건너뜀).
    NotLeased,
    /// 잇는 중 확인(등록 대화 = 이 대화 · 또는 그 좌석 자손 argv 에 이 대화) — 종전 rc 0 · 임대 = 그 좌석.
    Continues,
    /// 다른 대화를 잇는 중 확인(등록 대화 ≠ 이 대화) — rc 93 · 임대 되돌림(그 좌석은 이 대화를 안 쓴다).
    Other(String),
    /// 판정 불가(등록 없음 ∧ argv 없음 · topology 판독 실패) — rc 93 · 임대 유지(그 좌석이 이 대화를 쓰고 있을 수 있다 · 「다른 대화」로 단정하지 않는다).
    Unknown(&'static str),
}

/// 순수 판정 — `registered` = 데몬 topology live 의 그 좌석 `session_id`(`Ok(None)` = 등록 없음 · `Err` = 판독 실패) · `argv_writer` = 그 좌석 자손 argv 에 이 대화가 있는가.
/// ★r5(codex r4 #2): argv 는 낡을 수 있다(좌석 안 `/resume` 뒤에도 옛 인자가 남는다) → 「잇는 중일 수 있다」(임대 유지)의 근거일 뿐 —
/// 등록 충돌(등록 = 다른 대화)·판독 실패가 있으면 잇는 중(rc 0 성공)으로 올리지 않고 판정 불가(93 · 임대 유지).
/// 등록 없음 + argv 이 대화 = 잇는 중(충돌하는 관측이 없다 · 훅 부재 좌석의 같은 대화 재시도).
pub(crate) fn reused_seat_verdict(registered: Result<Option<&str>, ()>, argv_writer: bool, sess: &str) -> ReusedSeat {
    let me = sl::norm_id(sess);
    let Ok(raw) = registered else { return ReusedSeat::Unknown("topology-unreadable") };
    match raw.and_then(sl::norm_id) {
        Some(r) if Some(&r) == me.as_ref() => ReusedSeat::Continues,
        Some(_) if argv_writer => ReusedSeat::Unknown("registered-elsewhere-argv-here"),
        Some(_) => ReusedSeat::Other(short(raw.unwrap_or_default())),
        None if argv_writer => ReusedSeat::Continues,
        None => ReusedSeat::Unknown("seat-unregistered"),
    }
}

/// 좌석 하나의 현재 대화 증거가 어디서 왔나(사람 안내 · 판정에는 안 씀).
pub(crate) fn conversation_source(agent: Option<&str>) -> &'static str {
    if agent == Some("claude") {
        "작성자 결속(SessionStart 훅 등록 뒤 · 좌석 최상위 에이전트 신원)"
    } else {
        "에이전트 프로세스가 연 대화 파일(lsof · 등록 경로 없는 에이전트)"
    }
}

/// 좌석 `sid`(지금 데몬 세대 `gen`)의 현재 대화(skt1 · codex r5c #1·#2·#4) — 에이전트별 증거 표:
/// | 좌석 에이전트 | 증거 | 없음 |
/// |---|---|---|
/// | claude | 작성자 신원으로 묶인 작성 중 임대([`sl::seat_bound_conversation`] · `follow` 만 만든다 · 작성자 죽음 = 소멸) | Ok(None) |
/// | 그 밖(codex …) | 그 좌석 뿌리 자손의 에이전트 프로세스가 **지금 연** rollout 파일([`seat_agent_open_rollout`] · lsof) | Ok(None) |
/// | 모름(null) · 좌석 없음 · 판독 실패 | — | Err |
/// 데몬 `registered_session_id`(등록 문자열)·topology `session_id`(수집기 핀 — 좌석 밖 `usage-register` 가 덮을 수 있었다 · 휴리스틱 1회 핀)는
/// 「다른 대화」 증거로 쓰지 않는다(r5c #1 · codex 1R #3).
pub(crate) fn seat_conversation_now(sid: u64, gen: &str) -> Result<Option<String>, String> {
    let list = request("surface.list", json!({})).map_err(|_| "daemon:unreachable".to_string())?;
    let e = list["surfaces"].as_array().and_then(|a| a.iter().find(|s| s["surface_id"].as_u64() == Some(sid))).ok_or("seat-not-listed")?;
    match e["agent"].as_str() {
        Some("claude") => {
            let store = lease_store()?;
            sl::seat_bound_conversation(&store, sid, gen, &sl::probe_holder)
        }
        Some(_) => {
            let root = e["pid"].as_u64().ok_or("seat-root-unknown")? as u32;
            let bin = e["agent_bin"].as_str().unwrap_or_default();
            seat_agent_open_rollout(root, bin)
        }
        None => Err("seat-agent-unknown".into()),
    }
}

/// 등록 경로 없는 에이전트(codex) 좌석의 현재 대화 = 좌석 뿌리 `root` 자손 중 에이전트 실행(`bin`)이 **지금 연** rollout 파일의 대화 id
/// (skt1 · codex 1R #3 — 데몬 수집기의 결정론 경로 `discover_codex_rollout_lsof` 와 같은 꼴 · 가짜 등록이 닿지 못하는 증거).
/// Ok(None) = 에이전트는 있으나 연 rollout 없음 · Err = 에이전트 프로세스 못 찾음·lsof 불가(윈)·실패·서로 다른 대화 둘·id 판독 불가.
pub(crate) fn seat_agent_open_rollout(root: u32, bin: &str) -> Result<Option<String>, String> {
    use sysinfo::{ProcessRefreshKind, ProcessesToUpdate, System, UpdateKind};
    if cfg!(windows) {
        return Err("lsof-unsupported".into());
    }
    if bin.trim().is_empty() {
        return Err("seat-agent-bin-unknown".into());
    }
    let mut sys = System::new();
    sys.refresh_processes_specifics(ProcessesToUpdate::All, true, ProcessRefreshKind::nothing().with_cmd(UpdateKind::Always));
    let under_root = |pid: u32| {
        let mut cur = pid;
        for _ in 0..64 {
            if cur == root {
                return true;
            }
            match sys.process(sysinfo::Pid::from_u32(cur)).and_then(|p| p.parent()) {
                Some(pp) if pp.as_u32() > 1 => cur = pp.as_u32(),
                _ => return false,
            }
        }
        false
    };
    let all: Vec<u32> = sys
        .processes()
        .iter()
        .filter(|(_, p)| {
            let c: Vec<String> = p.cmd().iter().map(|a| a.to_string_lossy().into_owned()).collect();
            !c.is_empty() && sl::argv_is_agent_exec(&c.join(" "), bin)
        })
        .map(|(pid, _)| pid.as_u32())
        .filter(|p| *p != root && under_root(*p))
        .collect();
    let parent = |p: u32| sys.process(sysinfo::Pid::from_u32(p)).and_then(|x| x.parent()).map(|x| x.as_u32());
    let agents = top_agents(&all, root, parent);
    if agents.is_empty() {
        return Err("seat-agent-process-not-found".into());
    }
    let mut found: Option<String> = None;
    for pid in agents {
        // 앱 사이드카·launchd 의 PATH 에 /usr/sbin 이 없을 수 있다 — 맥 기본 자리를 먼저.
        let lsof = if std::path::Path::new("/usr/sbin/lsof").exists() { "/usr/sbin/lsof" } else { "lsof" };
        let out = std::process::Command::new(lsof).args(["-p", &pid.to_string(), "-Fn"]).output().map_err(|_| "lsof-failed".to_string())?;
        if !out.status.success() {
            return Err("lsof-failed".into());
        }
        let text = String::from_utf8_lossy(&out.stdout).into_owned();
        for path in text.lines().filter_map(|l| l.strip_prefix('n')).filter(|p| p.contains("/sessions/") && p.contains("rollout-") && p.ends_with(".jsonl")) {
            let id = rollout_session_id(std::path::Path::new(path)).ok_or("rollout-id-unreadable")?;
            match &found {
                Some(f) if *f != id => return Err("rollout-ambiguous".into()),
                _ => found = Some(id),
            }
        }
    }
    Ok(found)
}

/// 좌석 최상위 에이전트만(순수 · skt1 · codex 2R #3 오인 줄이기): 자기와 좌석 뿌리 사이에 다른 에이전트 실행이 있는 프로세스(그 에이전트의 자손 ·
/// argv 에 같은 이름 토큰을 가진 도구·헬퍼)는 그 좌석의 대화 증거가 아니다.
pub(crate) fn top_agents(all: &[u32], root: u32, parent: impl Fn(u32) -> Option<u32>) -> Vec<u32> {
    all.iter()
        .copied()
        .filter(|&p| {
            let mut cur = parent(p);
            for _ in 0..64 {
                match cur {
                    Some(c) if c == root || c <= 1 => return true,
                    Some(c) if all.contains(&c) => return false,
                    Some(c) => cur = parent(c),
                    None => return true,
                }
            }
            true
        })
        .collect()
}

/// codex rollout 첫 줄 `payload.id`(정규화 · 데몬 `extract_session_id("codex")` 와 같은 칸).
fn rollout_session_id(p: &std::path::Path) -> Option<String> {
    let f = std::fs::File::open(p).ok()?;
    let mut line = String::new();
    std::io::BufRead::read_line(&mut std::io::BufReader::new(f), &mut line).ok()?;
    let v: Value = serde_json::from_str(&line).ok()?;
    v["payload"]["id"].as_str().and_then(sl::norm_id)
}

/// 같은 역할 살아 있는 좌석 하나에 대한 #1 방어 판정(순수 · skt1 · codex r5c #2·#4).
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) enum RoleSeat {
    /// 그 역할의 살아 있는 좌석이 모두 다른 대화로 확인됐거나 이 대화를 쓸 수 없는 좌석(다른 에이전트)뿐 — 새 좌석 진행.
    Clear,
    /// 그 좌석의 현재 대화 증거가 **이 대화** — 새 좌석 0(작성자 둘).
    ThisConversation { seat: u64, by: &'static str },
    /// 그 좌석이 어느 대화를 쓰는지 확인 못 함 — 새 좌석 0(판정 불가).
    Unverified { seat: u64, why: String },
}

/// 같은 역할의 살아 있는 좌석이 이 대화(`sess`)를 쓰고 있을 수 있는가(순수 · r5 → skt1 · codex 1R #5).
/// - 판정 원천 = [`seat_conversation_now`] 의 현재 대화 증거 **하나**(claude = 작성자 결속 · 그 밖 = 에이전트가 연 파일): 이 대화 = 거절 ·
///   다른 대화 = 그 좌석 통과 · 없음·판독 불가 = 확인 못 함(93).
/// - 데몬 등록 문자열·topology 핀은 어느 쪽 신호로도 쓰지 않는다 — 「이 대화」 쪽으로 쓰면 헬퍼·낡은 등록 S 가 실제 결속 T 를 이겨
///   정상 복원을 좌석 수명 동안 막았고(codex 1R #5), 「다른 대화」 쪽으로 쓰면 가짜·헬퍼 등록이 풀었다(r5c #1). 등록 직후 결속 전 창(r5c #2)은
///   등록 **앞**의 결속 해제([`lease_transition_before_register`] = 그 사이 좌석 = 결속 없음 = 93)가 맡는다.
/// - `exclude` = 지금 기동하는 좌석 자신(기동 직전 재확인).
/// - 좌석 에이전트가 기동할 에이전트와 다르면(둘 다 앎) 그 좌석은 이 대화를 쓸 수 없다 — 건너뜀(r5c #4 의 다른 에이전트 좌석 고착).
/// - 생존 미상(null)·죽음 = 종전대로 넘어감(작성자가 아니다 · 넓히지 않음).
#[allow(clippy::too_many_arguments)]
pub(crate) fn role_seat_verdict(
    live: &[Value],
    role: &str,
    agent: &str,
    sess: &str,
    exclude: Option<u64>,
    alive: impl Fn(u64) -> Option<bool>,
    seat_agent: impl Fn(u64) -> Option<String>,
    current: impl Fn(u64) -> Result<Option<String>, String>,
) -> RoleSeat {
    let me = sl::norm_id(sess);
    for e in live.iter().filter(|e| e["role"].as_str() == Some(role)) {
        let Some(sid) = e["surface_id"].as_u64() else { continue };
        if Some(sid) == exclude || alive(sid) != Some(true) {
            continue;
        }
        let sa = seat_agent(sid);
        if sa.as_deref().is_some_and(|a| a != agent) {
            continue;
        }
        match current(sid) {
            Ok(Some(c)) if Some(&c) == me.as_ref() => return RoleSeat::ThisConversation { seat: sid, by: "current" },
            Ok(Some(_)) => continue,
            Ok(None) if sa.as_deref() == Some("claude") => return RoleSeat::Unverified { seat: sid, why: "seat-unbound".into() },
            Ok(None) => return RoleSeat::Unverified { seat: sid, why: "seat-unobserved".into() },
            Err(r) => return RoleSeat::Unverified { seat: sid, why: r },
        }
    }
    RoleSeat::Clear
}

/// 운영 판정 — 이 프로세스가 대화 임대를 쥔 잇는 기동에서만. Err = 판정 불가(topology·좌석 목록 판독 실패·형식 이상) ·
/// 특권 역할(master·cso*)은 데몬이 점유 좌석 승계를 거절하므로(claim_denied) 보지 않는다.
pub(crate) fn lease_role_seat_verdict(role: &str, agent: &str, sess: Option<&str>, exclude: Option<u64>) -> Result<RoleSeat, &'static str> {
    let Some(sess) = sess else { return Ok(RoleSeat::Clear) };
    if !lease_mine(Some(sess)) || role == "master" || role.starts_with("cso") {
        return Ok(RoleSeat::Clear);
    }
    let topo = request("system.topology", json!({})).map_err(|_| "topology-unreadable")?;
    let live = topo["live"].as_array().filter(|a| a.iter().all(live_entry_ok)).ok_or("topology-malformed")?;
    let surfaces = fetch_surfaces();
    let row = |sid: u64| surfaces.iter().find(|s| s["surface_id"].as_u64() == Some(sid));
    let alive = |sid: u64| row(sid).and_then(|s| s["agent_alive"].as_bool());
    let seat_agent = |sid: u64| row(sid).and_then(|s| s["agent"].as_str().map(String::from));
    // 같은 역할 · 살아 있음 · 같은(또는 모르는) 에이전트 좌석이 없으면 추가 판독 0(종전 비용 그대로).
    let candidate = |e: &Value| {
        e["role"].as_str() == Some(role)
            && e["surface_id"].as_u64().is_some_and(|s| Some(s) != exclude && alive(s) == Some(true) && seat_agent(s).is_none_or(|a| a == agent))
    };
    if !live.iter().any(candidate) {
        return Ok(RoleSeat::Clear);
    }
    let gen = current_gen().ok_or("daemon-gen-unreadable")?;
    Ok(role_seat_verdict(live, role, agent, sess, exclude, alive, seat_agent, |sid| seat_conversation_now(sid, &gen)))
}

/// 운영 판정 — 멱등 재반환 좌석 `sid` 의 현재 대화 증거([`seat_conversation_now`] · #1 방어와 같은 원천 · r5c #2)와 argv 를 본다.
pub(crate) fn lease_judge_reused_seat(sid: u64, sess: Option<&str>) -> ReusedSeat {
    let Some(sess) = sess else { return ReusedSeat::NotLeased };
    if !lease_mine(Some(sess)) {
        return ReusedSeat::NotLeased;
    }
    let registered = current_gen().ok_or(()).and_then(|g| seat_conversation_now(sid, &g).map_err(|_| ()));
    let argv_writer = lease_find_writer(sid, sess).is_some();
    reused_seat_verdict(registered.as_ref().map(|r| r.as_deref()).map_err(|_| ()), argv_writer, sess)
}

/// 기동 오류 뒤 임대 처분(codex 1R C1·C2) — 그 좌석의 「기동 글 수락」 기록 기준.
/// 잇는 기동 글 수락 뒤 = 유지(결과 불명) · 새 대화 기동 = 되돌림 · 기록 없음: 쓰기 결과 불명 = 유지(기동 글이 아직 쳐질 수 있다) ·
/// 그 밖(0바이트 거절 · 일반 오류) = 되돌림(기동 전 = 그 좌석에 작성자 없음 · 남기면 다음 복원이 거짓 93).
pub(crate) fn lease_settle_after_error(g: sl::Guard, seat: Option<u64>, write_unknown: bool) {
    match seat.and_then(launched) {
        Some(true) => lease_keep_unknown(g),
        Some(false) => g.release(),
        None if write_unknown => lease_keep_unknown(g),
        None => g.release(),
    }
}

/// rc 로 끝나는 기동(launch-agent · 복원 fresh)의 90·91 임대 처분 — 좌석 = 그 기동이 만든 좌석(90·91 은 좌석을 남긴다 · `run_launch_agent_opts` 의 반환값).
/// 좌석을 모르면 종전대로 유지(보수 — 기록을 대조할 수 없다).
/// ⚠역할 이름(`system.resolve_role`)으로 찾지 않는다 — 데몬은 `worker` 새 좌석을 `worker-N` 으로 바꿔 띄우므로(dedup_worker_role)
/// 그 이름이 남의 좌석(기록 없음)을 가리켜 잇는 기동 뒤 거절의 임대를 잘못 되돌릴 수 있다(작성자 둘).
pub(crate) fn lease_settle_kept_rc(g: sl::Guard, rc: i32, seat: Option<u64>) {
    match seat {
        None => lease_keep_unknown(g),
        Some(_) => lease_settle_after_error(g, seat, rc == EXIT_WRITE_OUTCOME_UNKNOWN),
    }
}

/// 기동 판정 → 임대 마무리. `seat` = 작성자를 찾을 좌석(모르면 None = 좌석으로 판정되도록 launching 유지).
pub(crate) fn lease_finish_ready(g: Option<sl::Guard>, seat: Option<u64>, sess: Option<&str>) {
    let Some(g) = g else { return };
    // 그 좌석의 기동이 저장 대화를 잇지 않았다(접미 없음 = 새 대화) → 이 대화의 임대를 쥐지 않는다(되돌림 · codex 6R).
    if seat.and_then(launched) == Some(false) {
        g.release();
        return;
    }
    let writer = match (seat, sess) {
        (Some(sid), Some(s)) => {
            g.set_surface(sid, current_gen());
            lease_find_writer(sid, s)
        }
        _ => None,
    };
    if let Err(r) = g.hold(writer) {
        eprintln!("[session_lease] 대화 {} 임대 마무리 기록 못 함({r}) — 이미 적힌 좌석 기준 판정으로 남음(보수)", short(sess.unwrap_or("?")));
    }
}

/// `cys usage-register` 성공 뒤(조건 ② — /clear · --continue · 새 대화 · 좌석 안 /resume): 그 좌석의 작성자 신원으로 임대를 옮긴다.
/// 출력 0(SessionStart 훅 출력이 대화 문맥에 들어가는 길 차단) · 실패해도 등록은 성공.
///
/// ★skt1(codex r5c #1): 이 follow 가 만든 작성 중 임대 = 그 좌석의 **현재 대화 증거**(`sl::seat_bound_conversation`)다 — 그래서 좌석 최상위
/// 에이전트의 SessionStart 훅이 아니라고 **증명된** 등록은 옮기지 않는다(데몬 `usage::lineage_proves_not_top_hook` 와 같은 판정):
/// 좌석 안 `claude -p` 헬퍼(에이전트 실행 2개 이상 — 종전엔 최상위 작성자가 헬퍼의 대화로 옮겨지고 원 대화 임대가 풀렸다) ·
/// 도구 셸의 직접 `cys usage-register`(에이전트 1개 · 훅 아래 아님). 좌석 밖 발신(뿌리에 닿지 않음 = 가짜 등록)은 종전대로 작성자 없음 = 무동작.
/// ★codex 1R #1: 옮기는 것은 계통이 [`sl::Lineage::ProvenTop`](최상위 에이전트 1개 + 그 아래 훅) 으로 **증명된** 등록뿐 — argv 판독 불가
/// (윈 MSYS 조상 단절 등)·에이전트 0 = 옮기지 않는다(결속 없음 = 같은 역할 복원 93 · 거짓 막힘 쪽 · 종전 = 옮김 → 헬퍼 등록이 결속을 덮었다).
pub(crate) fn lease_follow_on_register(surface_id: u64, transcript: &str) {
    if !sl::enabled() {
        return;
    }
    let tp = std::path::Path::new(transcript);
    if tp.is_dir() {
        return; // `.jsonl` 이름의 폴더 = 대화 파일이 아니다(r5c 2(v))
    }
    let Some(id) = tp.file_stem().and_then(|s| s.to_str()).and_then(sl::norm_id) else { return };
    let Ok(list) = request("surface.list", json!({})) else { return };
    let Some(row) = list["surfaces"].as_array().and_then(|a| a.iter().find(|s| s["surface_id"].as_u64() == Some(surface_id))).cloned() else { return };
    let Some(root) = row["pid"].as_u64().map(|p| p as u32) else { return };
    // 이 프로세스의 조상 중 「좌석 뿌리 자신이거나 부모가 좌석 뿌리인 것」 = 작성자(에이전트 · 또는 exec 안 한 래퍼).
    let mut cur = std::process::id();
    let mut writer = None;
    let mut chain: Vec<u32> = Vec::new(); // 발신의 부모 → 좌석 뿌리 순(계통 판정 재료)
    for _ in 0..64 {
        let Ok(i) = cys::process_observation::identity(cur) else { break };
        if cur != std::process::id() {
            chain.push(cur);
        }
        if i.pid == root || i.parent == root {
            writer = Some(sl::holder_of(&i));
            if i.pid != root {
                chain.push(root);
            }
            break;
        }
        if i.parent <= 1 {
            break;
        }
        cur = i.parent;
    }
    let Some(writer) = writer else { return };
    // 등록 명령 자신(이 프로세스)이 작성자로 잡히는 일은 없다 — 뿌리의 자식은 셸/에이전트다. 방어로 한 번 더.
    if writer.pid == std::process::id() {
        return;
    }
    if follow_lineage(&chain, row["agent_bin"].as_str().unwrap_or_default()) != sl::Lineage::ProvenTop {
        return;
    }
    let Ok(store) = lease_store() else { return };
    let _ = sl::follow(&store, &id, &writer, Some(surface_id), current_gen(), &CliWorld::new());
}

/// 계통(발신의 부모 → 좌석 뿌리 pid 들)의 argv → 3값(판독 실패 = Unknown).
fn follow_lineage(chain: &[u32], agent_bin: &str) -> sl::Lineage {
    let bin = agent_bin.rsplit(['/', '\\']).next().unwrap_or(agent_bin);
    sl::lineage_of(&chain_argv(chain), bin)
}

/// pid 들의 argv(공백 연결 · 못 읽음 = None).
fn chain_argv(chain: &[u32]) -> Vec<Option<String>> {
    use sysinfo::{Pid, ProcessRefreshKind, ProcessesToUpdate, System, UpdateKind};
    if chain.is_empty() {
        return Vec::new();
    }
    let pids: Vec<Pid> = chain.iter().map(|p| Pid::from_u32(*p)).collect();
    let mut sys = System::new();
    sys.refresh_processes_specifics(ProcessesToUpdate::Some(&pids), true, ProcessRefreshKind::nothing().with_cmd(UpdateKind::Always));
    let cmds: Vec<Option<String>> = pids
        .iter()
        .map(|p| {
            sys.process(*p).and_then(|pr| {
                let v: Vec<String> = pr.cmd().iter().map(|a| a.to_string_lossy().into_owned()).collect();
                (!v.is_empty()).then(|| v.join(" "))
            })
        })
        .collect();
    cmds
}

/// `cys usage-register` 가 데몬에 등록하기 **앞**(skt1 · codex 1R #2B): 이 발신이 좌석 최상위 에이전트의 SessionStart 훅으로 증명되면
/// 그 작성자에게 결속된 **다른 대화**의 임대를 결과 불명(좌석 유지)으로 바꾼다 — 등록이 실패해도(데몬 불통 등) 옛 결속이
/// 「이 좌석 = 옛 대화」 증거로 남아 같은 역할의 그 대화 복원을 통과시키지 않게. 데몬 없이 판정한다(작성자 = 조상 중 결속 임대의 작성자 ·
/// 계통 = 이 발신의 부모 → 그 작성자 argv · 에이전트 이름 = 좌석 목록 · 못 읽으면 claude(이 훅을 부르는 에이전트)). 출력 0.
pub(crate) fn lease_transition_before_register(surface_id: u64, transcript: &str) {
    if !sl::enabled() {
        return;
    }
    let tp = std::path::Path::new(transcript);
    if tp.is_dir() {
        return;
    }
    let Some(id) = tp.file_stem().and_then(|s| s.to_str()).and_then(sl::norm_id) else { return };
    let mut anc: Vec<(Holder, u32)> = Vec::new(); // 발신의 부모 → 위
    let mut cur = std::process::id();
    let mut complete = false; // 조상 사슬을 init 까지 읽었나(중간 판독 실패 = 작성자를 가릴 수 없다)
    for _ in 0..64 {
        let Ok(i) = cys::process_observation::identity(cur) else { break };
        if cur != std::process::id() {
            anc.push((sl::holder_of(&i), i.pid));
        }
        if i.parent <= 1 {
            complete = true;
            break;
        }
        cur = i.parent;
    }
    let bin = request("surface.list", json!({}))
        .ok()
        .and_then(|l| l["surfaces"].as_array().and_then(|a| a.iter().find(|s| s["surface_id"].as_u64() == Some(surface_id))).and_then(|r| r["agent_bin"].as_str().map(String::from)))
        .filter(|b| !b.trim().is_empty())
        .unwrap_or_else(|| "claude".into());
    let pids: Vec<u32> = anc.iter().map(|(_, p)| *p).collect();
    let cmds = chain_argv(&pids);
    let bin = bin.rsplit(['/', '\\']).next().unwrap_or(&bin).to_string();
    let Ok(store) = lease_store() else { return };
    sl::transition_unbind(&store, &id, &|w, seat| transition_targets(&anc, &cmds, &bin, complete, surface_id, w, seat));
}

/// 등록 앞 결속 해제 대상인가(순수 · skt1 · codex 2R #1 = 모르면 닫힌 쪽): 그 결속의 작성자가 이 발신의 조상이면 계통이 **헬퍼·도구 셸로 증명**(NotTop)
/// 된 때만 남기고 그 밖(ProvenTop · 판독 불가 Unknown)은 해제 — 해제의 귀결은 「이 좌석 결속 없음 = 같은 역할 복원 93」(거짓 막힘 쪽)이고,
/// 남기면 대화를 바꾼 좌석이 옛 대화로 읽혀 새 좌석이 열린다(작성자 둘). 조상 사슬을 끝까지 못 읽었으면(작성자를 못 가림) 이 좌석 번호의 결속을 해제.
pub(crate) fn transition_targets(anc: &[(Holder, u32)], cmds: &[Option<String>], bin: &str, complete: bool, surface_id: u64, w: &Holder, seat: Option<u64>) -> bool {
    match anc.iter().position(|(h, _)| h == w) {
        Some(k) => sl::lineage_of(&cmds[..=k], bin) != sl::Lineage::NotTop,
        None => !complete && seat == Some(surface_id),
    }
}

/// Return 직전 마지막 확인(skt1 · codex 2R #2) — [`sl::confirm_launch`] + 같은 역할 좌석 재판정(이 좌석 제외). Err = Return 0(`session_lease:` 머리).
pub(crate) fn lease_confirm_enter(role: &str, agent: &str, sess: Option<&str>, seat: u64) -> Result<(), String> {
    let Some(n) = sess.and_then(sl::norm_id) else { return Ok(()) };
    if !sl::enabled() || !sl::is_mine(&n) {
        return Ok(());
    }
    let store = lease_store().map_err(|r| format!("session_lease: 대화 {} Return 직전 확인 못 함({r}) — Return 0", short(&n)))?;
    let mut recheck = || match lease_role_seat_verdict(role, agent, sess, Some(seat)) {
        Ok(RoleSeat::Clear) => Ok(()),
        Ok(RoleSeat::ThisConversation { seat: w, .. }) => Err(format!("recheck:this-conversation:{w}")),
        Ok(RoleSeat::Unverified { seat: w, why }) => Err(format!("recheck:unverified:{w}:{why}")),
        Err(why) => Err(format!("recheck:{why}")),
    };
    sl::confirm_launch(&store, &n, &mut recheck).map_err(|r| {
        format!("session_lease: 대화 {} Return 직전 확인에서 멈춤({r}) — 기동 글은 붙였으나 실행 안 함 · 그 사이 다른 좌석이 이 대화로 들어왔거나 같은 역할 좌석의 대화를 확인 못 함", short(&n))
    })
}

/// 저장 대화를 잇는 기동 글을 치기 **직전**(`boot_agent_on_surface` · skt1 · codex 1R #2A): 같은 잠금 안에서 ① 임대가 아직 내 것(다른 좌석 최상위 훅의
/// 검증된 등록이 가져가지 않았다) ② 같은 역할 좌석 판정 재확인(이 좌석 제외) = Clear 일 때만 「확정」을 적는다. Err = 치지 않음(`session_lease:` 머리 ·
/// 호출자 = 빈 좌석 닫고 rc 93). 이 프로세스가 임대를 쥐지 않은 갈래 = 할 일 없음(Ok).
pub(crate) fn lease_commit_launch(role: &str, agent: &str, sess: Option<&str>, seat: u64) -> Result<(), String> {
    let Some(n) = sess.and_then(sl::norm_id) else { return Ok(()) };
    if !sl::enabled() || !sl::is_mine(&n) {
        return Ok(());
    }
    let store = lease_store().map_err(|r| format!("session_lease: 대화 {} 기동 직전 확정 못 함({r}) — 기동 글 0", short(&n)))?;
    let mut recheck = || match lease_role_seat_verdict(role, agent, sess, Some(seat)) {
        Ok(RoleSeat::Clear) => Ok(()),
        Ok(RoleSeat::ThisConversation { seat: w, .. }) => Err(format!("recheck:this-conversation:{w}")),
        Ok(RoleSeat::Unverified { seat: w, why }) => Err(format!("recheck:unverified:{w}:{why}")),
        Err(why) => Err(format!("recheck:{why}")),
    };
    sl::mark_launch_sent(&store, &n, &mut recheck).map_err(|r| {
        format!("session_lease: 대화 {} 기동 직전 재확인에서 멈춤({r}) — 기동 글 0 · 그 사이 다른 좌석이 이 대화로 들어갔거나 같은 역할 좌석의 대화를 확인 못 함", short(&n))
    })
}

/// 같은 좌석 재복원의 주입 표식(300초) — 임대를 **잡은** 회차(인수 포함)는 표식이 막아도 같은 표식을 새로 잡고 지나간다
/// (겹치는 두 복원 경로는 임대에서 하나만 이기므로 「겹침 막기」 몫을 임대가 대신한다). 임대 없는 겹침은 종전대로 막힌다.
pub(crate) fn inject_claim_or_lease(sid: u64, sess: Option<&str>) -> bool {
    if restore_inject_claim(sid) {
        return true;
    }
    if !lease_mine(sess) {
        return false;
    }
    let path = cys::daemon_state_dir(&cys::socket_path()).join(cys::restore_mark::mark_rel_path(sid));
    let _ = std::fs::write(&path, b""); // 시각 전진 = 같은 표식을 이 회차가 다시 잡음
    true
}

/// `cys restore` 항목 하나의 임대 판정.
pub(crate) enum LeasePick {
    /// 노브 끔 · 대화 없음 — 종전 claim 경로.
    Off,
    Go(Option<sl::Guard>),
    Refuse { rc: i32, line: String },
}

/// 옛 판 복원기가 방금(60초 안) 잡은 claim 인가 — 임대 파일이 없는 대화에서만(임대가 있으면 임대가 정본).
/// ⚠확인과 임대 획득은 한 잠금이 아니다 — 그 사이 옛 판이 claim 을 잡는 창(수십 ms)은 지원 범위 밖으로 설계 문서 「남는 창」에 적었다(M3 = B).
const FOREIGN_CLAIM_TIE_SECS: u64 = 60;

/// 임대 파일이 있어도 본다 — 옛 판은 임대를 모르므로 죽은 보유자의 임대를 넘겨받는 순간에도 옛 claim 이 진짜 경쟁자다(codex 2R M3).
/// Err = claim 을 읽지 못함(없음 아님 · NotFound 만 없음) — 판정 불가로 올린다. FIFO 등에서 멈추지 않게 비차단·심링크 불허로 연다.
fn foreign_claim_fresh(raw_id: &str, claim_dir: Option<&std::path::Path>) -> Result<bool, String> {
    let Some(d) = claim_dir else { return Ok(false) };
    let f = d.join(restore_claim_file_name(raw_id.trim()));
    let mut o = std::fs::OpenOptions::new();
    o.read(true);
    #[cfg(unix)]
    {
        use std::os::unix::fs::OpenOptionsExt;
        o.custom_flags(libc::O_NOFOLLOW | libc::O_NONBLOCK);
    }
    let mut h = match o.open(&f) {
        Ok(h) => h,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(false),
        Err(e) => return Err(format!("lease:claim:open:{}", e.raw_os_error().unwrap_or(0))),
    };
    if !h.metadata().map_err(|_| "lease:claim:fstat".to_string())?.is_file() {
        return Err("lease:claim:not-regular".into());
    }
    let mut c = String::new();
    std::io::Read::read_to_string(&mut h, &mut c).map_err(|_| "lease:claim:read".to_string())?;
    if c.split_whitespace().next().is_some_and(|tok| tok.starts_with('L')) {
        return Ok(false); // 임대를 아는 판이 쓴 claim — 판정은 임대가 한다
    }
    let Some(ep) = c.split_whitespace().nth(1).and_then(|v| v.parse::<u64>().ok()) else { return Ok(true) }; // 쓰는 중 = 점유
    Ok(restore_now_secs().saturating_sub(ep) < FOREIGN_CLAIM_TIE_SECS)
}

pub(crate) fn restore_lease_pick(
    role: &str,
    sess: Option<&str>,
    busy: &std::cell::RefCell<std::collections::HashSet<String>>,
    in_seat: Option<u64>,
    cfg: Option<&str>,
    claim_dir: Option<&std::path::Path>,
) -> LeasePick {
    if !sl::enabled() {
        return LeasePick::Off;
    }
    let (Some(raw), Some(norm)) = (sess, sess.and_then(sl::norm_id)) else { return LeasePick::Off };
    if busy.borrow().iter().any(|s| sl::norm_id(s).as_deref() == Some(norm.as_str())) {
        return LeasePick::Refuse {
            rc: EXIT_SESSION_WRITER_LIVE,
            line: format!("· {role}: 대화 {} — 이 복원 회차의 다른 항목이 이미 잇는 중 — 띄우지 않음", short(&norm)),
        };
    }
    match lease_gate(role, Some(raw), in_seat, cfg, claim_dir) {
        LeaseGate::Off => LeasePick::Off,
        LeaseGate::Proceed(g) => {
            busy.borrow_mut().insert(norm);
            LeasePick::Go(g)
        }
        LeaseGate::Refuse { rc, line } => LeasePick::Refuse { rc, line },
    }
}

/// 요약 줄 꼬리 — 낱말에 「실패」「재기동」「관문 보류」를 쓰지 않는다(Tauri 요약 파서가 첫 일치로 읽는다 · src-tauri main.rs:4266).
pub(crate) fn restore_lease_summary(live: usize, unknown: usize) -> String {
    if live == 0 && unknown == 0 {
        String::new()
    } else {
        format!(" · 대화 작성자 살아 있음 {live} · 생존 판정 불가 {unknown}")
    }
}

/// 복원 fresh 기동이 안쪽에서 거절(92 · 93)된 역할의 **표준 거절 줄**(순수 · r5 · codex r4 #3) — 관문 거절 줄과 같은 모양이라
/// phoenix `_LEASE_REFUSAL_RE`(javis_phoenix.py)·Tauri 재실측 판독이 같은 규칙으로 읽는다(그 역할을 재시도·새 대화로 띄우지 않음).
pub(crate) fn restore_inner_refusal_line(role: &str, sess: Option<&str>, rc: i32, seat: Option<u64>) -> String {
    let id = short(sess.unwrap_or("?"));
    let check = seat.map_or_else(|| "바로 위 [launch-agent] 줄의 좌석을 `cys read-screen` 으로 보세요".to_string(), |w| format!("`cys read-screen --surface surface:{w}`"));
    if rc == EXIT_SESSION_WRITER_LIVE {
        format!("· {role}: 대화 {id} — 그 대화를 잇는 좌석이 이미 있음 — 띄우지 않음 · 확인: {check}")
    } else {
        format!("· {role}: 대화 {id} 작성자 생존 판정 불가(seat-unverified) — 띄우지 않음 · 확인: {check} 로 그 좌석이 이 대화를 잇는지 보세요")
    }
}

/// 합산 rc 우선순위: 1(실패·관문) > 93 > 91 > 90 > 92 > 0(DESIGN §3).
pub(crate) fn restore_exit_code_lease(base: i32, fail_or_gated: usize, unknown_write: usize, live: usize, undecided: usize) -> i32 {
    if fail_or_gated > 0 {
        return base;
    }
    if undecided > 0 {
        return EXIT_SESSION_LIVENESS_UNKNOWN;
    }
    if unknown_write > 0 || base != 0 {
        return base;
    }
    if live > 0 {
        return EXIT_SESSION_WRITER_LIVE;
    }
    base
}

/// 결과 불명(⑪) 마무리 — 기록 실패는 진단 1줄(이미 적힌 좌석 기준 판정이 남는다 · 보수).
pub(crate) fn lease_keep_unknown(g: sl::Guard) {
    if let Err(r) = g.keep_unknown() {
        eprintln!("[session_lease] 결과 불명 기록 못 함({r}) — 이미 적힌 좌석 기준 판정으로 남음(보수)");
    }
}

/// node-recover 의 기동 결과 → 임대 마무리(순수에 가까움 · 시험 가능 · 독립 검증 F3).
/// 성공·관문 보류 = 작성자 기록 · 오류 = [`lease_settle_after_error`](잇는 기동 글 수락 뒤 = 유지 · 새 대화 = 되돌림 ·
/// 기록 없음 = 쓰기 결과 불명만 유지 · codex 6R · 1R C1·C2) · 그 밖 = 되돌림(가드 drop).
pub(crate) fn lease_settle_boot(result: &Result<BootVerdict, String>, seat: Option<u64>, g: Option<sl::Guard>, sess: Option<&str>) {
    match result {
        Ok(BootVerdict::Ready) | Ok(BootVerdict::GatePending { .. }) => lease_finish_ready(g, seat, sess),
        Err(e) => {
            if let Some(g) = g {
                lease_settle_after_error(g, seat, is_write_outcome_unknown(e))
            }
        }
        _ => drop(g),
    }
}

/// 새 좌석 기동 실패에서 좌석 닫기 결과 → 따로 낼 rc(순수 · 독립 검증 F3). 임대를 쥐고 기동 명령을 보냈는데 좌석을 못 닫음 = 91(임대 유지).
pub(crate) fn close_failure_rc(lease_sent: bool, close_failed: bool) -> Option<i32> {
    (lease_sent && close_failed).then_some(EXIT_WRITE_OUTCOME_UNKNOWN)
}

/// launch-agent 갈래(rc 로 끝나는 기동)의 임대 마무리 — `seat` = 그 기동이 만든 좌석(`run_launch_agent_opts` 반환값).
/// ⚠역할 이름으로 다시 찾지 않는다(codex 2R #2): 살아 있는 `worker` 가 있으면 새 좌석은 `worker-N` 이라 이름은 남의 좌석(작성자 없음)을 가리킨다.
pub(crate) fn lease_finish_by_rc(g: Option<sl::Guard>, rc: i32, seat: Option<u64>, sess: &str) {
    let Some(g) = g else { return };
    if rc == 0 || rc == cys::EXIT_GATE_PENDING {
        lease_finish_ready(Some(g), seat, Some(sess));
    } else if rc == EXIT_DIRECTIVE_REFUSED || rc == EXIT_WRITE_OUTCOME_UNKNOWN {
        lease_settle_kept_rc(g, rc, seat); // codex 1R C1·C2: 기동 전 0바이트 거절 · 새 대화 기동 = 되돌림
    } else if rc == EXIT_SESSION_LIVENESS_UNKNOWN && seat.is_some() {
        lease_keep_unknown(g); // r4 A: 재반환 좌석 판정 불가 = 그 좌석이 이 대화를 쓰고 있을 수 있다(좌석이 남은 93 은 이것뿐)
    }
    // 그 밖 = 가드 drop = 되돌림
}

/// `boot_agent_on_surface` 의 resume 갈래 불변식 — 노브 켬 · 대화 있음 · 이 프로세스가 임대를 안 쥠 = 거부 사유.
pub(crate) fn lease_resume_unheld(sess: Option<&str>) -> Option<String> {
    let norm = sess.and_then(sl::norm_id)?;
    if !sl::enabled() || lease_mine(sess) {
        return None;
    }
    Some(format!(
        "session_lease: 대화 {} 의 임대 없이 --resume 기동 요청 — 거부(이 입구가 대화 임대를 거치지 않았다 · `{}=off` 면 종전)",
        short(&norm),
        sl::KNOB
    ))
}
