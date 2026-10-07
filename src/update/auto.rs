//! `cys self-update` 집행 동사(★U2 · 설계 AUTO-UPDATE-118 §3-1 · §3-10 · §3-11 · §7-3 W2⑥).
//!
//! - `--auto --spawn` = 내장 잡 본체(6시간) — install_id 보장 · 복구기 등록(멱등) · 러너 사본에서 러너를 띄우고 **즉시 반환**.
//! - `--run` = 러너 — 지터 대기 → (비종결 저널이면 복구 먼저) → 판정(S0 · 게이트 N1~N14) → `apply` 일 때만 잠금 + 상태기계.
//! - `--recover` = 복구기(LaunchAgent RunAtLoad · 로그온 작업) — 잠금을 잡고 저널을 종결한다(없으면 조용히 끝).
//! - `--verify-payload --json` = 윈 S9b 전수 대조만 따로(진단 · W2 ⑥ · W4).
//! 데몬 RPC 는 cys 바이너리가 [`set_rpc`] 로 넣는다(lib 은 소켓 클라이언트가 없다).

use super::check;
use super::journal::Os;
use super::realops::{Candidate, Env, RealOps, CANDIDATE_FILE};
use super::runner::{Outcome, Runner};
use serde_json::{json, Value};
use std::path::PathBuf;
use std::sync::OnceLock;

pub type RpcFn = fn(&str, Value) -> Result<Value, String>;
static RPC: OnceLock<RpcFn> = OnceLock::new();

pub fn set_rpc(f: RpcFn) {
    let _ = RPC.set(f);
}

fn rpc_box() -> super::realops::Rpc {
    let f = RPC.get().copied();
    Box::new(move |m, p| match f {
        Some(f) => f(m, p),
        None => Err("rpc 미배선".into()),
    })
}

pub const ENV_NO_JITTER: &str = "CYS_UPDATE_NO_JITTER";
pub const ENV_SETTLE: &str = "CYS_UPDATE_SETTLE_SECS";
/// 윈 시험 폴더 설치(W2~W4 · 디버그 빌드만): 설치 폴더 = 상태 폴더 규칙을 시험 폴더 안에서 재현.
pub const ENV_INSTALL_DIR: &str = "CYS_UPDATE_INSTALL_DIR";

/// 설치 폴더(윈) — 기본 = 데몬 상태 폴더(설계 L4 · 설치 폴더 = 상태 폴더) · 디버그 빌드는 [`ENV_INSTALL_DIR`] 덮어쓰기.
pub fn install_dir() -> PathBuf {
    if cfg!(debug_assertions) {
        if let Some(v) = std::env::var_os(ENV_INSTALL_DIR).filter(|v| !v.is_empty()) {
            return PathBuf::from(v);
        }
    }
    daemon_state_dir()
}

fn os() -> Os {
    if cfg!(windows) {
        Os::Win
    } else {
        Os::Mac
    }
}

/// 데몬 상태 폴더(cysd `state_dir` 와 같은 규칙: 유닉스 = 소켓 부모 · 윈 = `%LOCALAPPDATA%\cys`).
pub fn daemon_state_dir() -> PathBuf {
    if cfg!(windows) {
        PathBuf::from(std::env::var("LOCALAPPDATA").unwrap_or_else(|_| ".".into())).join("cys")
    } else {
        crate::socket_path().parent().map(|p| p.to_path_buf()).unwrap_or_else(|| PathBuf::from("."))
    }
}

pub fn build_env(update_dir: PathBuf, channel: &str) -> Env {
    let pack = crate::pack::pack_dir();
    let cys_root = pack.parent().map(|p| p.to_path_buf()).unwrap_or_else(|| pack.clone());
    let state = daemon_state_dir();
    let canonical_app = crate::env_compat("CYS_UPDATE_APP_PATH").map(PathBuf::from).unwrap_or_else(|| PathBuf::from("/Applications/cysr.app"));
    let old_cys = super::launch::runner_copy_path(&update_dir);
    let settle = if cfg!(debug_assertions) { std::env::var(ENV_SETTLE).ok().and_then(|v| v.parse().ok()).unwrap_or(20) } else { 20 };
    Env {
        os: os(),
        update_dir,
        cys_root,
        install_dir: if cfg!(windows) { install_dir() } else { state.clone() },
        daemon_state_dir: if cfg!(windows) { install_dir() } else { state },
        canonical_app,
        channel: channel.to_string(),
        old_cys,
        rpc: rpc_box(),
        settle_secs: settle,
        dry_run: crate::env_compat("CYS_UPDATE_DRY_RUN").as_deref() == Some("1"),
        counsel_dir: super::notify::counsel_dir(),
    }
}

fn print(json_out: bool, v: &Value, line: &str) {
    if json_out {
        println!("{v}");
    } else {
        println!("{line}");
    }
}

/// `--auto --spawn`(잡 본체 · 600초 시한 안 · 즉시 반환).
pub fn auto_spawn(json_out: bool) -> i32 {
    let dir = match super::buildinfo::state_dir() {
        Ok(d) => d,
        Err(e) => {
            print(json_out, &json!({"spawned": false, "detail": e}), "spawned=false");
            return 3;
        }
    };
    let cfg = check::read_config(&dir).unwrap_or_default();
    if !cfg.auto {
        print(json_out, &json!({"spawned": false, "detail": "update.auto off"}), "spawned=false (off)");
        return 0;
    }
    // install_id 운영 생성 배선(2R M5 · B8 이관) — 판정 전에 원자 생성(손상 = 판정 불가 · 러너도 같은 rc).
    if let Err(e) = super::buildinfo::ensure_install_id(&dir) {
        print(json_out, &json!({"spawned": false, "detail": e}), "spawned=false (install_id)");
        return 3;
    }
    let Ok(cur) = std::env::current_exe() else { return 3 };
    // ★2판(codex 1R C18): 복구기 등록 실패·러너 기동 실패 = 형식 있는 0 아닌 rc(스케줄러가 성공으로 적고 6시간 미루던 길 차단).
    //   복구기 없이 러너를 띄우지 않는다(러너도 N14 로 보류할 뿐 — 실패를 지금 드러낸다).
    if let Err(e) = super::launch::ensure_recover_agent(&dir, &cur) {
        print(json_out, &json!({"spawned": false, "code": "update.recover_agent_failed", "detail": e}), "spawned=false (recover agent)");
        return RC_RECOVER_AGENT;
    }
    let runner = match super::launch::ensure_runner_copy(&dir, &cur) {
        Ok(r) => r,
        Err(e) => {
            print(json_out, &json!({"spawned": false, "detail": e}), "spawned=false (runner copy)");
            return 3;
        }
    };
    let r = super::launch::spawn_runner(&dir, &runner, &["self-update", "--run"]);
    let ok = r.is_ok();
    let v = json!({"spawned": ok, "runner": runner, "detail": r.err(), "code": if ok { Value::Null } else { json!("update.spawn_failed") }});
    print(json_out, &v, &format!("spawned={}", v["spawned"]));
    if ok {
        0
    } else {
        RC_SPAWN
    }
}

/// `--auto --spawn` rc(★2판 C18): 복구기 등록 실패.
pub const RC_RECOVER_AGENT: i32 = 4;
/// `--auto --spawn` rc(★2판 C18): 러너 기동 실패.
pub const RC_SPAWN: i32 = 5;

/// 복구기의 후보 = 러너가 S2 전에 남긴 `candidate.json`(S11 재료 = feed_rev·봉투 sha256·signed_at·서명 본문 포함). ★후속 2판(agy 1R #1 실측):
/// 복구기는 S2·S3 를 다시 밟지 않지만 후보는 **이 파일에서 복원된다**(「늘 비어 있다」 는 파일이 없을 때만) · 없음·손상 = 빈 후보 → 새 판
/// 판정 자체가 불가(정식 자리 = 후보 판 대조가 새 판 판정의 조건) = 상태만으로 판정하는 갈래(보류 정리·옛 판 재구성)만.
pub(crate) fn recovery_candidate(dir: &std::path::Path) -> Option<Candidate> {
    Some(match super::quiesce::read_json::<Candidate>(dir, CANDIDATE_FILE).and_then(|c| if super::mutant("U2-CANDVERIFY") { Some(c) } else { verified_candidate(c) }) {
        Some(c) => c,
        None => {
            // 후보 기록 없음 = S2 전(아무것도 안 바뀜) 또는 손상 — 상태만으로 판정하는 갈래(보류 정리·재구성)는 빈 후보로 충분하다.
            let a: super::feed::Asset = serde_json::from_value(json!({"url": "", "size": 0, "sha256": "", "max_unpacked": 0, "target": super::buildinfo::TARGET, "release_seq": 0})).ok()?;
            Candidate {
                asset: a,
                version: String::new(),
                release_seq: 0,
                installed_revoked: false,
                notes_ko: None,
                feed_rev: None,
                envelope_sha256: None,
                envelope_signed_at: None,
                release_b64: None,
                release_sig_b64: None,
            }
        }
    })
}

/// ★후속 3판(Opus 2R M1): candidate.json 은 날 JSON 이라 믿지 않는다 — 안의 U 서명 본문(`release_b64`·`release_sig_b64`)을 다시 검증하고
/// 그 본문의 이 기판 행으로 자산(sha256·크기·페이로드 매니페스트 …)·판·release_seq 를 **다시 만든다**(파일의 asset 칸은 버림). 본문 없음·
/// 서명 실패·이 기판 행 없음·판 어긋남 = None(빈 후보 = 새 판 판정 불가). S11 재료(feed_rev·봉투 sha256·signed_at)는 수용 기록에만 쓰인다.
fn verified_candidate(c: Candidate) -> Option<Candidate> {
    use base64::Engine;
    let e = base64::engine::general_purpose::STANDARD;
    let body = e.decode(c.release_b64.as_deref()?.trim()).ok()?;
    let sig = e.decode(c.release_sig_b64.as_deref()?.trim()).ok()?;
    let kr = super::keys::UpdateKeyring::embedded().ok()?;
    let rb = super::feed::verify_release_body(&body, &sig, "cysr", &kr).ok()?;
    if rb.release_seq != c.release_seq {
        return None;
    }
    let asset = rb.assets.values().find(|a| a.target == super::buildinfo::TARGET)?.clone();
    Some(Candidate { asset, version: rb.version.clone(), release_seq: rb.release_seq, ..c })
}

/// ★후속 3판 ②: 첫 보류가 N7 이고 윈이면 `fill`(보관소 받기) 1회 → 성공 = `recheck` 로 다시 판정 · 실패 = 보고 그대로 + 사유(Some).
/// 그 밖(맥 · 다른 게이트 보류 · apply) = 받기 0.
pub(crate) fn retry_after_n7_fill(
    report: Value,
    rc: i32,
    windows: bool,
    fill: impl FnOnce() -> Result<bool, String>,
    recheck: impl FnOnce() -> (Value, i32),
) -> (Value, i32, Option<String>) {
    let n7_only = report["decision"] == "hold" && report["gates"]["first_hold"]["id"] == "N7";
    if !windows || !n7_only || super::mutant("U2-N7FILL") {
        return (report, rc, None);
    }
    match fill() {
        Ok(_) => {
            let (r, c) = recheck();
            (r, c, None)
        }
        Err(e) => {
            eprintln!("[update] N7 보류 — {e}");
            (report, rc, Some(e))
        }
    }
}

/// ★후속 4판 ①(Opus 3R n1): N7 보관소 받기는 **전역 잠금을 쥔 동안에만** 쓴다 — `installers/<seq>` 와 임시 폴더 `.<seq>.tmp` 는 설치 링크
/// (U5 · 잠금을 쥔 설치 스크립트가 cys 에 위임)와 같은 자리라, 잠금 밖에서 쓰면 사용자가 설치 링크를 다시 붙인 순간 두 쪽이 같은 임시
/// 폴더를 쓴다(설치 링크 실패 · 오류 화면). 잠금이 잡혀 있으면 받기 0 + 사유(= 사유 있는 보류 · 다음 주기 재시도). 잠금은 받기 뒤 놓는다.
pub(crate) fn fill_under_lock(dir: &std::path::Path, fill: impl FnOnce() -> Result<bool, String>) -> Result<bool, String> {
    let _guard = if super::mutant("U2-N7LOCK") {
        None
    } else {
        Some(super::lock::acquire(dir, "runner").map_err(|e| format!("설치판 롤백 자산 받기 보류 — 갱신 잠금 사용 중({e})"))?)
    };
    fill()
}

/// 러너 · 복구기 공통: 비종결 저널이면 복구부터(잠금 = 복구기 몫 · 잡혀 있으면 조용히 끝).
fn recover_if_needed(dir: &std::path::Path, channel: &str) -> Option<Outcome> {
    let read = super::journal::read(dir);
    let pending = match &read {
        super::journal::ReadOutcome::Absent => false,
        super::journal::ReadOutcome::Ok(j) => !j.state.is_terminal(),
        _ => true,
    };
    if !pending {
        return None;
    }
    let guard = match super::lock::acquire(dir, "recover") {
        Ok(g) => g,
        Err(_) => return Some(Outcome::Nothing), // 다른 소유자가 이끄는 중
    };
    let cand = recovery_candidate(dir)?;
    let tok = guard.token();
    let mut ops = RealOps::new(build_env(dir.to_path_buf(), channel), tok.render(), cand, env!("CARGO_PKG_VERSION").to_string());
    let mut r = Runner::new(dir, &tok.txn_id, tok.epoch, &mut ops);
    let o = r.recover();
    drop(guard);
    Some(o)
}

/// `--recover`.
pub fn recover(json_out: bool) -> i32 {
    let Ok(dir) = super::buildinfo::state_dir() else { return 3 };
    let channel = check::read_config(&dir).map(|c| c.channel).unwrap_or_else(|_| "stable".into());
    let o = recover_if_needed(&dir, &channel);
    print(json_out, &json!({"recovered": format!("{o:?}")}), &format!("recover={o:?}"));
    match o {
        Some(Outcome::SeatsBlocked(_)) | Some(Outcome::RollbackFailed(_)) => 2,
        _ => 0,
    }
}

/// `--run`(러너 본체).
pub fn run(json_out: bool, hooks: &check::Hooks) -> i32 {
    let rc = run_inner(json_out, hooks);
    if let Ok(dir) = super::buildinfo::state_dir() {
        super::win_task::delete_runner_task(&dir); // 일회 작업 — 끝나면 지운다(윈)
    }
    rc
}

fn run_inner(json_out: bool, hooks: &check::Hooks) -> i32 {
    let Ok(dir) = super::buildinfo::state_dir() else { return 3 };
    let cfg = check::read_config(&dir).unwrap_or_default();
    let no_jitter = cfg!(debug_assertions) && std::env::var(ENV_NO_JITTER).as_deref() == Ok("1");
    if !no_jitter {
        let id = super::buildinfo::read_install_id(&dir).unwrap_or_default();
        let wait = super::launch::initial_wait_secs(super::clock::mono_ms() / 1000, super::launch::jitter_secs(&id, super::launch::JITTER_MAX_SECS));
        std::thread::sleep(std::time::Duration::from_secs(wait));
    }
    if let Some(o) = recover_if_needed(&dir, &cfg.channel) {
        print(json_out, &json!({"phase": "recover", "outcome": format!("{o:?}")}), &format!("recover={o:?}"));
        return 0; // 복구한 틱은 새 교체를 시작하지 않는다(다음 틱)
    }
    // S0 — 판정(--check 와 같은 계산 · 결정 apply 일 때만 교체)
    let (report, rc) = check::run_check(&dir, &crate::pack::pack_dir(), hooks);
    // ★후속 3판 ②(설계 §3-7 ② · master#c72a59df): 윈 N7 이 **유일한** 보류(첫 보류 = N7 · 순서상 마지막 게이트)면 이 주기에서 보관소 받기 →
    //   다시 판정. 실패 = 사유 있는 보류(last_defer.detail · 다음 주기 재시도 · 영구 아님).
    // ★후속 4판 ①(Opus 3R n1): 받기 = 전역 잠금 안(`fill_under_lock`) — installers/<seq>·`.<seq>.tmp` 는 설치 링크(U5)와 같은 자리다.
    let (report, rc, n7_fill) = retry_after_n7_fill(
        report,
        rc,
        cfg!(windows),
        || fill_under_lock(&dir, || super::realops::fill_rollback_assets_net(&dir, super::buildinfo::release_seq())),
        || check::run_check(&dir, &crate::pack::pack_dir(), hooks),
    );
    let decision = report["decision"].as_str().unwrap_or("").to_string();
    // ★3판(Fable 2R M4 · 설계 §3-8): 본체가 최신이고 게이트가 통과면 팩 단독 갱신(러너 트랜잭션 안 · PACK_APPLY/PACK_ROLLBACK).
    // ★4판(M6): 게이트 = 팩 단독 부분열(`pack_gates` = evaluate_pack_only) — 본체 전체 게이트(N6·N7·N14)를 재사용하지 않는다.
    if wants_pack_only(&report) {
        let o = pack_only(&dir, &cfg.channel);
        print(json_out, &json!({"phase": "pack", "outcome": format!("{o:?}")}), &format!("pack={o:?}"));
        return match o {
            Outcome::PackDone | Outcome::Nothing | Outcome::Deferred(_) => 0,
            _ => 2,
        };
    }
    if decision != "apply" {
        let _ = super::notify::update_state(&dir, |m| {
            if decision == "hold" {
                m.insert("last_defer".into(), json!({"code": report["gates"]["first_hold"]["code"], "gate": report["gates"]["first_hold"]["id"], "at": super::clock::wall_now(), "detail": n7_fill.clone().unwrap_or_default()}));
            }
            if decision == "stop_seats" || report["feed"]["installed_revoked"].as_bool() == Some(true) {
                // ★U4 접점: 설치판 폐기 = last_result kind installed_revoked(결과 id = 설치판 seq 고정 → 앱이 결과당 1회만 알림)
                let seq = super::buildinfo::release_seq();
                let o = super::notify::Outcome {
                    kind: "installed_revoked",
                    code: super::errors::ErrCode::InstalledRevoked,
                    component: "cysr".into(),
                    channel: cfg.channel.clone(),
                    target: super::buildinfo::TARGET.into(),
                    release_seq: seq,
                    from_release_seq: seq,
                    from_version: env!("CARGO_PKG_VERSION").into(),
                    to_version: String::new(),
                    force_permanent: false,
                    detail: String::new(),
                    notes_ko: None,
                };
                super::notify::apply(m, &o, &format!("installed_revoked:{seq}"), super::clock::wall_now(), None);
            }
        });
        if decision == "stop_seats" {
            // ★2판 C12 → ★3판 M3: 집행 = 표지(그 판 데몬이 새 좌석 생성 거부 · 기존 좌석 유지 · 새 판이면 자동 해제). 완화 폐기
            //   (advisory)의 자동 RB 는 HANDOFF-U2 §5 ⓐ(미구현 · 정직).
            let seq = super::buildinfo::release_seq();
            let rc2 = enforce_stop_seats(&dir, seq);
            print(json_out, &json!({"phase": "decide", "decision": decision, "stop_seats_enforced": rc2 == 0}), &format!("decision={decision} enforced={}", rc2 == 0));
            return rc2;
        }
        print(json_out, &json!({"phase": "decide", "decision": decision}), &format!("decision={decision}"));
        return if rc == 3 { 3 } else { 0 };
    }
    let now = super::clock::wall_now();
    let id = super::buildinfo::read_install_id(&dir).unwrap_or_default();
    let (res, _) = check::fetch_and_verify(&dir, &cfg.channel, now, Some(super::feed::rollout_bucket(&id)));
    let Some(cand) = res.ok().as_ref().and_then(Candidate::from_outcome) else {
        return 3;
    };
    let guard = match super::lock::acquire(&dir, "runner") {
        Ok(g) => g,
        Err(e) => {
            print(json_out, &json!({"phase": "lock", "detail": e.to_string()}), "txn_busy");
            return 0;
        }
    };
    if super::quiesce::write_json(&dir, CANDIDATE_FILE, &cand).is_err() {
        return 3;
    }
    let tok = guard.token();
    let mut ops = RealOps::new(build_env(dir.clone(), &cfg.channel), tok.render(), cand, env!("CARGO_PKG_VERSION").to_string());
    let mut r = Runner::new(&dir, &tok.txn_id, tok.epoch, &mut ops);
    let o = r.run();
    drop(guard);
    print(json_out, &json!({"phase": "run", "outcome": format!("{o:?}")}), &format!("run={o:?}"));
    match o {
        Outcome::Done | Outcome::Deferred(_) | Outcome::PackDone | Outcome::Nothing => 0,
        Outcome::RolledBack(_) => 1,
        _ => 2,
    }
}

/// ★4판(codex·Fable 3R M4/M6): 러너 분기(순수) — 본체 최신 + **팩 단독 게이트**(설계 §3-8 부분열) 통과 = 팩 경로.
pub fn wants_pack_only(report: &Value) -> bool {
    let key = if super::mutant("U2-PACKGATE") { "gates" } else { "pack_gates" };
    report["decision"].as_str() == Some("uptodate") && report[key]["pass"].as_bool() == Some(true)
}

/// 팩 단독 갱신 1회(잠금 = 러너 · 후보 = 빈 행 — 팩 경로는 본체 자산을 쓰지 않는다).
pub fn pack_only(dir: &std::path::Path, channel: &str) -> Outcome {
    let guard = match super::lock::acquire(dir, "runner") {
        Ok(g) => g,
        Err(_) => return Outcome::Nothing,
    };
    let Ok(a) = serde_json::from_value::<super::feed::Asset>(json!({"url": "", "size": 0, "sha256": "", "max_unpacked": 0, "target": super::buildinfo::TARGET, "release_seq": 0}))
    else {
        return Outcome::Nothing;
    };
    let cand = Candidate {
        asset: a,
        version: String::new(),
        release_seq: 0,
        installed_revoked: false,
        notes_ko: None,
        feed_rev: None,
        envelope_sha256: None,
        envelope_signed_at: None,
        release_b64: None,
        release_sig_b64: None,
    };
    let tok = guard.token();
    let mut ops = RealOps::new(build_env(dir.to_path_buf(), channel), tok.render(), cand, env!("CARGO_PKG_VERSION").to_string());
    let o = Runner::new(dir, &tok.txn_id, tok.epoch, &mut ops).run_pack();
    drop(guard);
    o
}

/// ★3판(Fable 2R M3 · 설계 §3-10 ③): stop_seats 집행 = 표지 durable 기록뿐 — 데몬이 그 판에서 **새 좌석 생성**을 거부한다(cysd
/// `surface.create` · 기존 좌석·부팅 유지 · 2판의 `rotate --stop-only --skip-drain` 전체 정지 = 설계 초과 → 철회). 0 = 기록 · 2 = 기록 실패.
pub fn enforce_stop_seats(dir: &std::path::Path, seq: u64) -> i32 {
    if super::runner::seats_stop_seq(dir) == Some(seq) {
        return 0;
    }
    match super::quiesce::write_json(dir, super::runner::SEATS_STOP_FILE, &json!({"release_seq": seq, "at": super::clock::wall_now()})) {
        Ok(()) => 0,
        Err(_) => 2,
    }
}

/// ★2판(codex 1R C15): 대조 매니페스트 = **지금 설치판**(build-info release_seq) 것만 — 후보 기록은 그 판과 seq 가 같을 때만 쓰고
/// (B→A 롤백 뒤 남은 B 후보로 A 설치본을 재던 거짓 진단 차단) 아니면 `installers\<설치판 seq>\release.json`.
/// ★후속 4판 ②(Opus 3R n2): 후보 기록 = 서명 재검증 입구 [`recovery_candidate`](본문 행으로 자산을 다시 만듦) — 날 candidate.json 의
/// 매니페스트 칸은 믿지 않는다(변조 = 서명 실패 = 빈 후보 → 설치판 본문 · 그것도 없으면 진단 거부).
pub fn pick_payload_manifest(dir: &std::path::Path, installed_seq: u64) -> Option<Vec<super::feed::PayloadEntry>> {
    recovery_candidate(dir)
        .filter(|c| c.release_seq == installed_seq && c.asset.release_seq == installed_seq)
        .and_then(|c| c.asset.payload_manifest)
        .filter(|m| !m.is_empty())
        .or_else(|| super::realops::load_installer_manifest(&dir.join("installers").join(installed_seq.to_string())))
}

/// `--verify-payload --json`(윈 S9b 진단): 설치 폴더 = 지금 판 매니페스트 전수 대조(후보가 있으면 그 판 · 없으면 설치판 본문).
pub fn verify_payload(json_out: bool) -> i32 {
    let Ok(dir) = super::buildinfo::state_dir() else { return 3 };
    let install = install_dir();
    let manifest = pick_payload_manifest(&dir, super::buildinfo::release_seq());
    let Some(m) = manifest else {
        print(json_out, &json!({"ok": false, "detail": "대조할 매니페스트 없음"}), "ok=false (no manifest)");
        return 3;
    };
    let r = super::payload::verify_install(&install, &m, None);
    let v = json!({"ok": r.ok(), "install_dir": install, "manifest_sha256": super::payload::manifest_sha256(&m), "report": r});
    print(json_out, &v, &format!("ok={} checked={} missing={} mismatched={}", r.ok(), r.checked, r.missing.len(), r.mismatched.len()));
    if r.ok() {
        0
    } else {
        2
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// ★후속 3판 ②: 러너 S0 — 윈 + 첫 보류 N7 = 보관소 받기 1회 → 성공 = 다시 판정 · 실패 = 같은 보류 + 사유 · 맥·다른 게이트 보류 = 받기 0.
    /// 뮤턴트 U2-N7FILL(받기 끔 = 3판 전 = 사유 없는 영구 보류) = 적.
    #[test]
    fn n7_hold_on_windows_triggers_archive_fill_then_recheck_or_reasoned_hold() {
        let hold = |id: &str| json!({"decision": "hold", "gates": {"first_hold": {"id": id, "code": "update.no_rollback_asset"}}});
        let calls = std::cell::Cell::new(0);
        let (r, _, why) = retry_after_n7_fill(hold("N7"), 0, true, || { calls.set(calls.get() + 1); Ok(true) }, || (json!({"decision": "apply"}), 0));
        assert_eq!((r["decision"].as_str(), why, calls.get()), (Some("apply"), None, 1), "받아 채움 → 다시 판정 = apply");
        let (r, _, why) = retry_after_n7_fill(hold("N7"), 0, true, || Err("설치판 롤백 자산 받기(보관소): 미도달".into()), || panic!("실패면 재판정 0"));
        assert!(r["decision"] == "hold" && why.as_deref().map(|w| w.contains("보관소")).unwrap_or(false), "사유 있는 보류");
        let (_, _, why) = retry_after_n7_fill(hold("N7"), 0, false, || panic!("맥 = 받기 0"), || panic!());
        assert!(why.is_none());
        let (_, _, why) = retry_after_n7_fill(hold("N5"), 0, true, || panic!("다른 게이트 보류 = 받기 0"), || panic!());
        assert!(why.is_none());
    }

    /// ★후속 4판 ①: N7 보관소 받기 = 전역 잠금 안에서만 — 남(설치 링크 등)이 잠금을 쥐었으면 받기 진입 0 + 사유 · 받는 동안 잠금 잡힘 ·
    /// 받은 뒤 놓음. 뮤턴트 U2-N7LOCK(잠금 없이 받기 = 4판 전) = 적.
    #[test]
    fn n7_archive_fill_writes_only_while_holding_the_global_lock() {
        use super::super::lock;
        let d = std::env::temp_dir().join(format!("cys-u2-n7lock-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&d);
        let held = lock::acquire(&d, "install-link").unwrap();
        let entered = std::cell::Cell::new(false);
        let r = fill_under_lock(&d, || {
            entered.set(true);
            Ok(true)
        });
        assert!(!entered.get(), "남이 쥔 잠금 = 받기 진입 0");
        assert!(r.as_ref().err().map(|e| e.contains("잠금")).unwrap_or(false), "사유 있는 보류: {r:?}");
        drop(held);
        let r = fill_under_lock(&d, || {
            assert_eq!(lock::is_held(&d), Some(true), "받는 동안 = 잠금 안");
            Ok(true)
        });
        assert_eq!(r, Ok(true));
        assert_eq!(lock::is_held(&d), Some(false), "받은 뒤 잠금 놓음");
        let _ = std::fs::remove_dir_all(&d);
    }

    /// ★4판(codex·Fable 3R M4/M6): 러너 분기 = 팩 단독 부분열 — 배터리(N6)·롤백 자산(N7)·복구기(N14) 보류여도 본체 최신이면 팩 경로 ·
    /// 팩 부분열 게이트(N2 사람 입력 등) 보류면 팩도 안 감 · 본체 판정이 uptodate 아니면 팩 경로 0. 뮤턴트 U2-PACKGATE(본체 게이트 재사용) = 적색.
    #[test]
    fn pack_route_uses_pack_only_gate_subset() {
        use super::super::gates::{self, Power};
        let mut f = gates::all_pass_facts();
        f.power = Some(Power { adapter: false, battery_pct: Some(5) });
        f.rollback_assets_ok = Some(false);
        f.recover_agent_ok = Some(false);
        let rep = |f: &gates::Facts, decision: &str| json!({"decision": decision, "gates": gates::evaluate(f), "pack_gates": gates::evaluate_pack_only(f)});
        assert!(!gates::evaluate(&f).pass, "본체 게이트 = 보류(N6·N7·N14)");
        assert!(wants_pack_only(&rep(&f, "uptodate")), "팩 = 재시작 없음 → 전원·롤백 자산·복구기 무관");
        assert!(!wants_pack_only(&rep(&f, "hold")), "본체 판정이 uptodate 아님 = 팩 경로 0");
        let mut g = gates::all_pass_facts();
        g.auto_enabled = Some(false); // N1 = 팩 부분열 안
        assert!(!wants_pack_only(&rep(&g, "uptodate")), "팩 부분열 보류 = 팩도 안 감");
    }

    /// 시험: 서명된 후보(이 기판 행의 페이로드 매니페스트 = `path`) — 파일의 asset 칸은 `file_path` 로 따로 적는다(변조 흉내).
    fn signed_cand(k: &super::super::keys::testkit::Keys, seq: u64, path: &str, file_path: &str, sig_ok: bool) -> Candidate {
        use base64::Engine;
        let row = |p: &str| json!([{"path": p, "size": 1, "sha256": "a".repeat(64)}]);
        let mut body = super::super::feed::fixture::body_json(k, seq);
        body["assets"][super::super::buildinfo::TARGET]["payload_manifest"] = row(path);
        let bb = body.to_string().into_bytes();
        let e = base64::engine::general_purpose::STANDARD;
        let asset: super::super::feed::Asset = serde_json::from_value(json!({"url": "", "size": 0, "sha256": "", "max_unpacked": 0,
            "target": super::super::buildinfo::TARGET, "release_seq": seq, "payload_manifest": row(file_path)})).unwrap();
        Candidate {
            asset,
            version: format!("1.1.{seq}"),
            release_seq: seq,
            installed_revoked: false,
            notes_ko: None,
            feed_rev: None,
            envelope_sha256: None,
            envelope_signed_at: None,
            release_b64: Some(e.encode(&bb)),
            release_sig_b64: Some(e.encode(if sig_ok { k.u.sign(&bb) } else { k.f.sign(&bb) })),
        }
    }

    /// ★2판 C15: B→A 롤백 뒤 남은 B 후보(seq 9)로 A 설치본(seq 8)을 재지 않는다 — 설치판 seq 의 본문만.
    #[test]
    fn verify_payload_uses_installed_release_manifest_only() {
        use super::super::keys::testkit::Keys;
        let _l = super::super::TEST_ENV_LOCK.lock().unwrap_or_else(|e| e.into_inner());
        let d = std::env::temp_dir().join(format!("cys-u2-vp-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&d);
        std::fs::create_dir_all(d.join("installers/8")).unwrap();
        let k = Keys::new();
        std::fs::write(d.join("kr.json"), k.keyring_json()).unwrap();
        let _e = (
            crate::pack::EnvGuard::set("CYS_UPDATE_TEST_KEYRING", d.join("kr.json")),
            crate::pack::EnvGuard::set("CYS_UPDATE_NOW", super::super::feed::fixture::NOW.to_string()),
        );
        let row = |p: &str| json!([{"path": p, "size": 1, "sha256": "a".repeat(64)}]);
        super::super::quiesce::write_json(&d, CANDIDATE_FILE, &signed_cand(&k, 9, "B.exe", "B.exe", true)).unwrap();
        let rel = json!({"assets": [{"target": super::super::buildinfo::TARGET, "payload_manifest": row("A.exe")}]});
        std::fs::write(d.join("installers/8/release.json"), rel.to_string()).unwrap();
        // 롤백 뒤(설치판 8) = B 후보를 쓰지 않는다 · 서명 없는 release.json 은 ★2판 C10 재검증에서 거부(서명된 본문 경로 =
        // realops::tests::installer_dir_is_reverified_on_every_use)
        assert!(pick_payload_manifest(&d, 8).is_none(), "B 후보로 A 를 재지 않음 · 서명 없는 본문 = 신뢰 0");
        assert_eq!(pick_payload_manifest(&d, 9).unwrap()[0].path, "B.exe", "후보 = 설치판일 때만");
        assert!(pick_payload_manifest(&d, 7).is_none());
        let _ = std::fs::remove_dir_all(&d);
    }

    /// ★후속 4판 ②(Opus 3R n2): `--verify-payload` 의 후보 = 서명 재검증 입구 — 파일의 매니페스트 칸 변조는 무시(서명 본문 행) ·
    /// 본문 서명 실패·본문 없음 = 후보 불신(설치판 본문도 없으면 진단 거부 = 매니페스트 없음). 뮤턴트 U2-CANDVERIFY(재검증 끔) = 적.
    #[test]
    fn verify_payload_rejects_tampered_candidate_manifest() {
        use super::super::keys::testkit::Keys;
        let _l = super::super::TEST_ENV_LOCK.lock().unwrap_or_else(|e| e.into_inner());
        let d = std::env::temp_dir().join(format!("cys-u2-vpt-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&d);
        std::fs::create_dir_all(&d).unwrap();
        let k = Keys::new();
        std::fs::write(d.join("kr.json"), k.keyring_json()).unwrap();
        let _e = (
            crate::pack::EnvGuard::set("CYS_UPDATE_TEST_KEYRING", d.join("kr.json")),
            crate::pack::EnvGuard::set("CYS_UPDATE_NOW", super::super::feed::fixture::NOW.to_string()),
        );
        super::super::quiesce::write_json(&d, CANDIDATE_FILE, &signed_cand(&k, 9, "cys.exe", "EVIL.exe", true)).unwrap();
        assert_eq!(pick_payload_manifest(&d, 9).unwrap()[0].path, "cys.exe", "파일 칸 변조 무시 = 서명 본문 행");
        super::super::quiesce::write_json(&d, CANDIDATE_FILE, &signed_cand(&k, 9, "cys.exe", "EVIL.exe", false)).unwrap();
        assert!(pick_payload_manifest(&d, 9).is_none(), "본문 서명 실패 = 진단 거부");
        let mut unsigned = signed_cand(&k, 9, "cys.exe", "EVIL.exe", true);
        unsigned.release_b64 = None;
        unsigned.release_sig_b64 = None;
        super::super::quiesce::write_json(&d, CANDIDATE_FILE, &unsigned).unwrap();
        assert!(pick_payload_manifest(&d, 9).is_none(), "서명 본문 없음 = 진단 거부");
        let _ = std::fs::remove_dir_all(&d);
    }
}
