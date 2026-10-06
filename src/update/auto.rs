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
    let cand: Candidate = match super::quiesce::read_json(dir, CANDIDATE_FILE) {
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
    };
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
    let decision = report["decision"].as_str().unwrap_or("").to_string();
    // ★3판(Fable 2R M4 · 설계 §3-8): 본체가 최신이고 게이트가 통과면 팩 단독 갱신(러너 트랜잭션 안 · PACK_APPLY/PACK_ROLLBACK).
    if decision == "uptodate" && report["gates"]["pass"].as_bool() == Some(true) {
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
                m.insert("last_defer".into(), json!({"code": report["gates"]["first_hold"]["code"], "gate": report["gates"]["first_hold"]["id"], "at": super::clock::wall_now()}));
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

/// 팩 단독 갱신 1회(잠금 = 러너 · 후보 = 빈 행 — 팩 경로는 본체 자산을 쓰지 않는다).
fn pack_only(dir: &std::path::Path, channel: &str) -> Outcome {
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
pub fn pick_payload_manifest(dir: &std::path::Path, installed_seq: u64) -> Option<Vec<super::feed::PayloadEntry>> {
    super::quiesce::read_json::<Candidate>(dir, CANDIDATE_FILE)
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

    /// ★2판 C15: B→A 롤백 뒤 남은 B 후보(seq 9)로 A 설치본(seq 8)을 재지 않는다 — 설치판 seq 의 본문만.
    #[test]
    fn verify_payload_uses_installed_release_manifest_only() {
        let d = std::env::temp_dir().join(format!("cys-u2-vp-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&d);
        std::fs::create_dir_all(d.join("installers/8")).unwrap();
        let row = |p: &str| json!([{"path": p, "size": 1, "sha256": "a".repeat(64)}]);
        let asset: super::super::feed::Asset = serde_json::from_value(json!({"url": "", "size": 0, "sha256": "", "max_unpacked": 0,
            "target": super::super::buildinfo::TARGET, "release_seq": 9, "payload_manifest": row("B.exe")})).unwrap();
        let c = Candidate {
            asset,
            version: "B".into(),
            release_seq: 9,
            installed_revoked: false,
            notes_ko: None,
            feed_rev: None,
            envelope_sha256: None,
            envelope_signed_at: None,
            release_b64: None,
            release_sig_b64: None,
        };
        super::super::quiesce::write_json(&d, CANDIDATE_FILE, &c).unwrap();
        let rel = json!({"assets": [{"target": super::super::buildinfo::TARGET, "payload_manifest": row("A.exe")}]});
        std::fs::write(d.join("installers/8/release.json"), rel.to_string()).unwrap();
        // 롤백 뒤(설치판 8) = B 후보를 쓰지 않는다 · 서명 없는 release.json 은 ★2판 C10 재검증에서 거부(서명된 본문 경로 =
        // realops::tests::installer_dir_is_reverified_on_every_use)
        assert!(pick_payload_manifest(&d, 8).is_none(), "B 후보로 A 를 재지 않음 · 서명 없는 본문 = 신뢰 0");
        assert_eq!(pick_payload_manifest(&d, 9).unwrap()[0].path, "B.exe", "후보 = 설치판일 때만");
        assert!(pick_payload_manifest(&d, 7).is_none());
        let _ = std::fs::remove_dir_all(&d);
    }
}
