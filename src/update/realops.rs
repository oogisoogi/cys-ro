//! 러너 실행층 — 실 맥·윈(설계 AUTO-UPDATE-118 §3-1 ~ §3-12 의 부작용 전부). 상태기계·되감기 판단은 [`super::runner`] 가 하고, 여기는
//! 각 단계의 실물 동작만 한다(멱등 · 실패 = [`Fail`] 사전 코드).
//!
//! - 데몬 RPC·좌석 사실은 호출자(cys 바이너리)가 주입한다([`Env::rpc`]) — lib 는 소켓 클라이언트를 갖지 않는다.
//! - 자식 명령(`drain`·`rotate --stop-only|--skip-drain --txn`·`build-info`)은 전부 위임 토큰을 인자 + env `CYS_UPDATE_TXN` 으로 넘긴다(§3-2).
//! - ★실 설치본·실 `~/.cys` 에 닿는 경로는 전부 [`Env`] 의 칸에서 온다 — 시험·VM 은 그 칸을 격리 폴더로 준다(§7-2).
//! - 정직: 이 파일의 전 단계를 한 번에 도는 실행은 VM M1~M3 · 윈 W1~W4 몫이다(이 맥에서 실 교체 0 · 단계별 순수 부품은 각 모듈 시험).

use super::errors::ErrCode;
use super::journal::{Journal, Os, PrevInstaller};
use super::runner::{Canon, Fail, Kind, Ops, Step};
use super::verify::{self, Baseline, Expect, PackId, Post, SeatKey};
use serde_json::{json, Value};
use std::path::{Path, PathBuf};

pub type Rpc = Box<dyn Fn(&str, Value) -> Result<Value, String>>;

pub struct Env {
    pub os: Os,
    /// 갱신 상태 폴더(저널·잠금·보류 로그·백업).
    pub update_dir: PathBuf,
    /// `~/.cys`(팩·사용자 트리 뿌리).
    pub cys_root: PathBuf,
    /// 데몬 상태 폴더(맥 `~/.local/state/cys` · 윈 `%LOCALAPPDATA%\cys` — 윈은 설치 폴더와 같다).
    pub daemon_state_dir: PathBuf,
    /// 맥 정식 자리 번들(`/Applications/cysr.app` · 시험 = `CYS_UPDATE_APP_PATH`).
    pub canonical_app: PathBuf,
    /// 윈 설치 폴더.
    pub install_dir: PathBuf,
    pub channel: String,
    /// 지금(옛) 판 `cys` 실행 파일 — 러너 사본(설치본 밖).
    pub old_cys: PathBuf,
    pub rpc: Rpc,
    /// S5 정착 창(초).
    pub settle_secs: u64,
    pub dry_run: bool,
}

/// 후보(S0 판정에서 뽑은 것 · 복구기가 다시 읽을 수 있게 `candidate.json` 으로 남긴다).
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct Candidate {
    pub asset: super::feed::Asset,
    pub version: String,
    pub release_seq: u64,
    pub installed_revoked: bool,
    #[serde(default)]
    pub notes_ko: Option<String>,
    /// ★2판(codex 1R C11): 수용 기록 재료(S11 durable commit) + U 서명 본문(base64)·서명 — 없으면 S11 이 실패한다(DONE 0).
    #[serde(default)]
    pub feed_rev: Option<u64>,
    #[serde(default)]
    pub envelope_sha256: Option<String>,
    #[serde(default)]
    pub envelope_signed_at: Option<i64>,
    #[serde(default)]
    pub release_b64: Option<String>,
    #[serde(default)]
    pub release_sig_b64: Option<String>,
}

pub const CANDIDATE_FILE: &str = "candidate.json";

impl Candidate {
    pub fn from_outcome(o: &super::feed::FeedOutcome) -> Option<Candidate> {
        Some(Candidate {
            asset: o.asset.clone()?,
            version: o.version.clone().unwrap_or_default(),
            release_seq: o.release_seq?,
            installed_revoked: o.installed_revoked,
            notes_ko: o.notes_ko.clone(),
            feed_rev: o.feed_rev,
            envelope_sha256: o.envelope_sha256.clone(),
            envelope_signed_at: o.envelope_signed_at,
            release_b64: o.release_b64.clone(),
            release_sig_b64: o.release_sig_b64.clone(),
        })
    }
}

/// 보존 자산 파일 이름(`installers/<seq>/`).
pub const REL_BODY: &str = "release.json";
pub const REL_SIG: &str = "release.json.minisig";
pub const SETUP: &str = "setup.exe";
pub const SETUP_SIG: &str = "setup.exe.sig";

/// 재검증된 보존 판(★2판 C10).
#[derive(Debug, Clone)]
pub struct VerifiedRelease {
    pub manifest: Vec<super::feed::PayloadEntry>,
    /// 설치기 sha256(`need_installer` 일 때만).
    pub setup_sha256: Option<String>,
}

/// ★2판(codex 1R C10): `installers/<seq>/` 를 **쓸 때마다** 재검증 — U 서명 본문(서식·키·서명) · 본문 seq = 폴더 seq · 이 대상 행 ·
/// (`need_installer`) 설치기 바이트 sha256 = 본문 행 · A2 서명. 하나라도 어긋나면 Err(임의 파일을 놓아도 신뢰하지 않는다).
pub fn verify_installer_dir(dir: &Path, seq: u64, need_installer: bool) -> Result<VerifiedRelease, String> {
    let body = std::fs::read(dir.join(REL_BODY)).map_err(|e| format!("{REL_BODY}: {e}"))?;
    let sig = std::fs::read(dir.join(REL_SIG)).map_err(|e| format!("{REL_SIG}: {e}"))?;
    let kr = super::keys::UpdateKeyring::embedded()?;
    verify_installer_dir_with(dir, seq, need_installer, &body, &sig, &kr)
}

pub fn verify_installer_dir_with(
    dir: &Path,
    seq: u64,
    need_installer: bool,
    body: &[u8],
    sig: &[u8],
    kr: &super::keys::UpdateKeyring,
) -> Result<VerifiedRelease, String> {
    let rb = super::feed::verify_release_body(body, sig, "cysr", kr)?;
    if rb.release_seq != seq {
        return Err(format!("본문 seq {} ≠ 폴더 {seq}", rb.release_seq));
    }
    let a = rb.assets.values().find(|a| a.target == super::buildinfo::TARGET).ok_or("이 대상 행 없음")?;
    let manifest = a.payload_manifest.clone().unwrap_or_default();
    let setup_sha256 = if need_installer {
        let bytes = std::fs::read(dir.join(SETUP)).map_err(|e| format!("{SETUP}: {e}"))?;
        if super::feed::sha256_hex(&bytes) != a.sha256 {
            return Err("설치기 sha256 ≠ 본문 행".into());
        }
        let s = std::fs::read(dir.join(SETUP_SIG)).map_err(|e| format!("{SETUP_SIG}: {e}"))?;
        if kr.verify_any(super::keys::Purpose::WinAsset, &bytes, &s, rb.signed_at).is_err() {
            return Err("설치기 A2 서명 불일치".into());
        }
        Some(a.sha256.clone())
    } else {
        None
    };
    Ok(VerifiedRelease { manifest, setup_sha256 })
}

pub struct RealOps {
    pub env: Env,
    pub token: String,
    /// S0 후보(행 포함) — 러너 시작 전에 호출자가 채운다(복구기 = `candidate.json`).
    pub cand: Candidate,
    pub old_version: String,
    q1: Option<super::quiesce::Token>,
    b0: Option<Baseline>,
    /// ★2판 C9: 마지막 `rotate` 자식의 실제 종료 코드(V3 restore_rc — 상수 0 대신).
    last_rotate_rc: Option<i32>,
}

fn fail(code: ErrCode, step: &str, d: impl Into<String>) -> Fail {
    Fail::new(code, step, d)
}

impl RealOps {
    pub fn new(env: Env, token: String, cand: Candidate, old_version: String) -> RealOps {
        RealOps { env, token, cand, old_version, q1: None, b0: None, last_rotate_rc: None }
    }

    fn asset(&self) -> Result<&super::feed::Asset, Fail> {
        Ok(&self.cand.asset)
    }

    fn stage_dir(&self, j: &Journal) -> PathBuf {
        self.env.update_dir.join("stage").join(&j.txn_id)
    }

    fn installers_dir(&self, seq: u64) -> PathBuf {
        self.env.update_dir.join("installers").join(seq.to_string())
    }

    /// 자식 명령(위임 토큰 동반 · ★2판 C1: 인자 `--txn` 과 env 를 함께 — 위임 계약 ⓪).
    fn child(&self, exe: &Path, args: &[&str]) -> Result<std::process::Output, Fail> {
        let mut c = crate::hidden_command(exe);
        c.args(args);
        let participant = matches!(args.first(), Some(&("rotate" | "init-pack" | "pack-update" | "pack-plan")));
        if participant && !args.contains(&"--txn") {
            c.args(["--txn", self.token.as_str()]);
        }
        c.env(super::lock::ENV_TXN, &self.token).stdin(std::process::Stdio::null());
        c.output().map_err(|e| fail(ErrCode::RotateFailed, "child", format!("{}: {e}", exe.display())))
    }

    fn rotate(&mut self, exe: &Path, stop_only: bool) -> Step {
        let mut args = vec!["rotate", "--skip-drain", "--txn", self.token.as_str()];
        if stop_only {
            args.push("--stop-only");
        }
        let o = self.child(exe, &args)?;
        if !stop_only {
            self.last_rotate_rc = Some(o.status.code().unwrap_or(-1));
        }
        if o.status.success() {
            Ok(())
        } else {
            Err(fail(ErrCode::RotateFailed, if stop_only { "S7" } else { "S10" }, format!("rotate rc {:?}", o.status.code())))
        }
    }

    /// 새 판 `cys` 경로.
    fn new_cys(&self) -> PathBuf {
        match self.env.os {
            Os::Mac => self.env.canonical_app.join("Contents/MacOS/cys"),
            Os::Win => self.env.install_dir.join("cys.exe"),
        }
    }

    fn expect_new(&self) -> Result<super::mac::Ident, Fail> {
        let a = self.asset()?;
        Ok(super::mac::Ident { release_seq: a.release_seq, build_id: a.build_id.clone(), target: a.target.clone() })
    }

    fn expect_old(&self) -> super::mac::Ident {
        let b = super::buildinfo::build_info();
        super::mac::Ident { release_seq: b.release_seq, build_id: b.build_id.clone(), target: b.target.to_string() }
    }

    fn token_now(&self) -> Result<super::quiesce::Token, Fail> {
        let v = (self.env.rpc)("update.seat_token", json!({"txn": self.token})).map_err(|e| fail(ErrCode::RotateFailed, "S5", e))?;
        serde_json::from_value(v).map_err(|e| fail(ErrCode::RotateFailed, "S5", e.to_string()))
    }

    /// 좌석 키 집합(V3 · B0) — 재기동으로 바뀌는 surface 번호 대신 역할·등록 세션·에이전트.
    fn seats(&self) -> Result<std::collections::BTreeSet<SeatKey>, Fail> {
        let org = (self.env.rpc)("org.status", json!({})).map_err(|e| fail(ErrCode::VerifyFailed, "V3", e))?;
        Ok(seats_from_org(&org))
    }

    /// ★2판(codex 1R C9): doctor 실행·판독 실패를 「FAIL 0」 으로 접지 않는다 — 관측 실패 = `doctor_unavailable` FAIL 1건(V4 실패 ·
    /// 기준선에서도 실패였으면 새 FAIL 아님).
    fn doctor_fail(&self, exe: &Path) -> std::collections::BTreeSet<String> {
        self.child(exe, &["doctor", "--json"])
            .ok()
            .and_then(|o| serde_json::from_slice::<Value>(&o.stdout).ok())
            .filter(|v| v["checks"].is_array())
            .map(|v| doctor_fails(&v))
            .unwrap_or_else(|| ["doctor_unavailable".to_string()].into())
    }

    /// ★2판 C9: 기판 표지 실측 — 맥 = 정식 자리 번들 CDHash(codesign -dvvv) · 윈 = 설치 폴더 cys.exe sha256. 관측 실패 = Err.
    fn platform_mark(&self) -> Result<String, Fail> {
        match self.env.os {
            Os::Mac => {
                let out = crate::hidden_command("/usr/bin/codesign")
                    .args(["-dvvv"])
                    .arg(&self.env.canonical_app)
                    .output()
                    .map_err(|e| fail(ErrCode::VerifyFailed, "V1", e.to_string()))?;
                let text = format!("{}{}", String::from_utf8_lossy(&out.stdout), String::from_utf8_lossy(&out.stderr));
                super::macupdate::parse_cdhash(&text).ok_or_else(|| fail(ErrCode::VerifyFailed, "V1", "CDHash 판독 불가"))
            }
            Os::Win => super::snapshot::sha256_file(&self.env.install_dir.join("cys.exe")).map(|(s, _)| s).map_err(|e| fail(ErrCode::VerifyFailed, "V1", e)),
        }
    }

    /// ★2판 C9: 금지 내장 잡 실측 = 데몬 `schedule.status` 의 잡 id ∩ [`verify::FORBIDDEN_JOBS`] · 판독 실패 = `observe_failed`(V6 실패).
    fn forbidden_jobs(&self) -> Vec<String> {
        match (self.env.rpc)("schedule.status", json!({})) {
            Ok(v) => v["jobs"]
                .as_array()
                .map(|a| {
                    a.iter()
                        .filter_map(|j| j["id"].as_str())
                        .filter(|id| verify::FORBIDDEN_JOBS.contains(id))
                        .map(str::to_string)
                        .collect()
                })
                .unwrap_or_else(|| vec!["observe_failed".into()]),
            Err(_) => vec!["observe_failed".into()],
        }
    }

    fn pack_id(&self) -> PackId {
        let p = self.env.cys_root.join("pack");
        let version = std::fs::read_to_string(p.join("VERSION")).map(|s| s.trim().to_string()).unwrap_or_default();
        let digest = std::fs::read_to_string(p.join(".pack-digest")).map(|s| s.trim().to_string()).unwrap_or_default();
        PackId { version, digest }
    }

    fn snapshot_roots(&self) -> Vec<(&'static str, PathBuf)> {
        vec![("state", self.env.daemon_state_dir.clone()), ("cys", self.env.cys_root.clone())]
    }

    /// `~/.cys` 뿌리 안에서 스냅샷 대상(§3-5 표 「팩」·「사용자 소유 트리」 행) — 그 밖(계정 폴더·대화 기록·갱신 폴더)은 뺀다.
    pub fn cys_filter(rel: &str) -> bool {
        let first = rel.split('/').next().unwrap_or_default();
        first == "pack"
            || first.starts_with("pack-dept-")
            || first.starts_with(".pack-")
            || first == "local"
            || matches!(first, ".install-manifest.json" | ".last-app-version" | ".pending-restore" | ".pack-accepted.json")
    }

    /// 상태 폴더 안 보호·제외 판정(윈 = 페이로드 매니페스트 경로도 보호 · ⓐ).
    /// S11 보존(★2판 C11): `installers/.<seq>.tmp` 에 본문·서명(+윈 설치기·서명)을 쓰고 재검증한 뒤 `installers/<seq>` 로 rename.
    /// 이미 있고 재검증 통과 = 그대로(멱등).
    fn preserve_release(&self, j: &Journal) -> Step {
        let f = |d: String| fail(ErrCode::RotateFailed, "S11", d);
        let seq = self.cand.release_seq;
        let need_inst = self.env.os == Os::Win;
        let dst = self.installers_dir(seq);
        if verify_installer_dir(&dst, seq, need_inst).is_ok() {
            return Ok(());
        }
        let e = base64::engine::general_purpose::STANDARD;
        use base64::Engine;
        let body = e.decode(self.cand.release_b64.as_deref().ok_or_else(|| f("후보에 서명 본문 없음".into()))?.trim()).map_err(|x| f(x.to_string()))?;
        let sig = e.decode(self.cand.release_sig_b64.as_deref().ok_or_else(|| f("후보에 본문 서명 없음".into()))?.trim()).map_err(|x| f(x.to_string()))?;
        let parent = dst.parent().ok_or_else(|| f("installers 부모 없음".into()))?;
        let tmp = parent.join(format!(".{seq}.tmp"));
        let _ = std::fs::remove_dir_all(&tmp);
        super::ensure_private_dir(&tmp).map_err(f)?;
        super::journal::durable_write(&tmp.join(REL_BODY), &body).map_err(f)?;
        super::journal::durable_write(&tmp.join(REL_SIG), &sig).map_err(f)?;
        if need_inst {
            let stage = self.stage_dir(j);
            super::snapshot::durable_copy(&stage.join(SETUP), &tmp.join(SETUP)).map_err(f)?;
            super::snapshot::durable_copy(&stage.join(SETUP_SIG), &tmp.join(SETUP_SIG)).map_err(f)?;
        }
        verify_installer_dir(&tmp, seq, need_inst).map_err(|e| f(format!("보존본 재검증: {e}")))?;
        if dst.exists() {
            std::fs::remove_dir_all(&dst).map_err(|e| f(e.to_string()))?;
        }
        std::fs::rename(&tmp, &dst).map_err(|e| f(e.to_string()))?;
        super::journal::sync_dir(parent).map_err(f)
    }

    /// 상태 폴더 + `~/.cys`(팩·사용자 트리) 파일 단위 복원(RB_RESTORED · 재구성 공용).
    fn restore_trees(&self, root: &Path, step: &str, qkey: &str, want_st: Option<&str>, want_cy: Option<&str>) -> Step {
        let q = super::snapshot::quarantine_dir(&self.env.update_dir, qkey);
        let payload: std::collections::BTreeSet<String> = self
            .asset()
            .ok()
            .and_then(|a| a.payload_manifest.as_ref())
            .map(|m| m.iter().map(|e| super::payload::norm(&e.path)).collect())
            .unwrap_or_default();
        let st_prot = move |rel: &str| super::snapshot::is_excluded(rel) || payload.contains(&super::payload::norm(rel));
        super::snapshot::restore(&self.env.daemon_state_dir, &root.join("state"), &q.join("state"), &st_prot, want_st)
            .map_err(|e| fail(ErrCode::RollbackBlocked, step, e))?;
        let cys_prot = |rel: &str| !RealOps::cys_filter(rel);
        super::snapshot::restore(&self.env.cys_root, &root.join("cys"), &q.join("cys"), &cys_prot, want_cy)
            .map_err(|e| fail(ErrCode::RollbackBlocked, step, e))?;
        Ok(())
    }

    fn state_filter(&self) -> impl Fn(&str) -> bool + '_ {
        let payload: std::collections::BTreeSet<String> = self
            .asset()
            .ok()
            .and_then(|a| a.payload_manifest.as_ref())
            .map(|m| m.iter().map(|e| super::payload::norm(&e.path)).collect())
            .unwrap_or_default();
        move |rel: &str| !super::snapshot::is_excluded(rel) && !payload.contains(&super::payload::norm(rel))
    }
}

/// `org.status` → 좌석 키(순수 · 끝난 좌석 제외).
pub fn seats_from_org(org: &Value) -> std::collections::BTreeSet<SeatKey> {
    org["surfaces"]
        .as_array()
        .map(|a| {
            a.iter()
                .filter(|s| s["exited"].as_bool() != Some(true))
                // ★2판(codex 1R C9): 데몬 재기동을 넘는 surface 고유 id 가 org.status 에 없다(surface_id·display_no 는 재기동마다
                //   바뀜) — 좌석 주소 = 역할(role · 배선 권위)이고 `surface_uuid` 칸에는 그 사실을 `role:` 접두로 적는다(UUID 인 척 0).
                //   `dept` = 행의 `dept`(없으면 빈 값 — 에이전트 이름을 넣지 않는다) · 에이전트 이름은 `session_id` 와 함께 따로 대조.
                .map(|s| SeatKey {
                    surface_uuid: format!("role:{}", s["role"].as_str().unwrap_or("")),
                    role: s["role"].as_str().unwrap_or("").to_string(),
                    dept: s["dept"].as_str().unwrap_or("").to_string(),
                    session_id: format!(
                        "{}|{}",
                        s["agent"].as_str().unwrap_or(""),
                        s["registered_session_id"].as_str().unwrap_or("")
                    ),
                })
                .collect()
        })
        .unwrap_or_default()
}

/// ★3판(Fable 2R N2): V2 「cysd 1개」 = **이 설치본 본부 소켓이 스스로 밝힌 데몬 1개** — `system.identify.daemon_pid` 가 살아 있고 이름이
/// cysd(.exe)이며 같은 사용자일 때 1 · 그 밖(응답 없음·죽음·다른 이름) 0. 부서 데몬·다른 설치본 데몬은 계수 밖(이 맥 `pgrep -x cysd` = 21 ·
/// 2판의 「이 사용자 cysd 전수」 는 부서가 있는 기계에서 V2·RB_VERIFIED 를 결정론으로 떨어뜨렸다).
pub fn hq_daemon_count(identify: &Value) -> u32 {
    use sysinfo::{Pid, ProcessRefreshKind, ProcessesToUpdate, System, UpdateKind};
    let Some(pid) = identify["daemon_pid"].as_u64().and_then(|p| u32::try_from(p).ok()) else { return 0 };
    let mut sys = System::new();
    let me = Pid::from_u32(std::process::id());
    let them = Pid::from_u32(pid);
    sys.refresh_processes_specifics(ProcessesToUpdate::Some(&[me, them]), true, ProcessRefreshKind::nothing().with_user(UpdateKind::Always));
    let Some(p) = sys.process(them) else { return 0 };
    let n = p.name().to_string_lossy();
    let named = n == "cysd" || n.eq_ignore_ascii_case("cysd.exe");
    let same_user = match (sys.process(me).and_then(|x| x.user_id()), p.user_id()) {
        (Some(a), Some(b)) => a == b,
        _ => true, // 판정 불가(윈 일부) = 이름·생존으로만
    };
    u32::from(named && same_user)
}

/// `cys doctor --json` → FAIL 항목 id 집합(순수).
pub fn doctor_fails(v: &Value) -> std::collections::BTreeSet<String> {
    let mut out = std::collections::BTreeSet::new();
    for c in v["checks"].as_array().into_iter().flatten() {
        let st = c["status"].as_str().or_else(|| c["result"].as_str()).unwrap_or("");
        if st.eq_ignore_ascii_case("fail") {
            if let Some(id) = c["id"].as_str().or_else(|| c["name"].as_str()) {
                out.insert(id.to_string());
            }
        }
    }
    out
}

impl Ops for RealOps {
    fn os(&self) -> Os {
        self.env.os
    }

    fn fetch(&mut self, j: &mut Journal) -> Step {
        let a = self.asset()?.clone();
        let stage = self.stage_dir(j);
        super::ensure_private_dir(&stage).map_err(|e| fail(ErrCode::DiskLow, "S2", e))?;
        let name = if self.env.os == Os::Win { "setup.exe" } else { "asset.zip" };
        let dst = stage.join(name);
        let ok = super::snapshot::sha256_file(&dst).map(|(s, n)| s == a.sha256 && n == a.size).unwrap_or(false);
        if !ok {
            let got = super::net::fetch(&a.url, super::url::Hop::AssetFirst, a.size).map_err(|e| match e {
                super::net::NetErr::Refused(u) => fail(u.code, "S2", u.detail),
                super::net::NetErr::Unreachable(d) => fail(ErrCode::DlSizeMismatch, "S2", d),
            })?;
            if got.bytes.len() as u64 != a.size {
                return Err(fail(ErrCode::DlSizeMismatch, "S2", format!("{} ≠ {}", got.bytes.len(), a.size)));
            }
            let part = stage.join(format!("{name}.part"));
            super::journal::durable_write(&part, &got.bytes).map_err(|e| fail(ErrCode::DiskLow, "S2", e))?;
            let (s, _) = super::snapshot::sha256_file(&part).map_err(|e| fail(ErrCode::DlShaMismatch, "S2", e))?;
            if s != a.sha256 {
                let _ = std::fs::remove_file(&part);
                return Err(fail(ErrCode::DlShaMismatch, "S2", "sha256"));
            }
            std::fs::rename(&part, &dst).map_err(|e| fail(ErrCode::DiskLow, "S2", e.to_string()))?;
            let _ = super::journal::sync_dir(&stage);
        }
        match self.env.os {
            Os::Mac => {
                // ★2판(master#3f846d60 ②): 정식 경로가 링크·디렉터리 아님 = 여기(S2 · 아무것도 안 바꿈)서 보류 종결.
                super::mac::real_path(&self.env.canonical_app, "S2")?;
                let staged = super::mac::staged_path(&self.env.canonical_app, a.release_seq);
                if !staged.exists() {
                    let names = zip_names(&dst).map_err(|e| fail(ErrCode::ArchiveRefused, "S2", e))?;
                    super::mac::check_entry_names(&names).map_err(|e| fail(ErrCode::ArchiveRefused, "S2", e))?;
                    let tmp = stage.join("unpacked");
                    let _ = std::fs::remove_dir_all(&tmp);
                    let o = crate::hidden_command("/usr/bin/ditto").args(["-x", "-k"]).arg(&dst).arg(&tmp).output();
                    if !o.map(|o| o.status.success()).unwrap_or(false) {
                        return Err(fail(ErrCode::ArchiveRefused, "S2", "ditto 풀기 실패"));
                    }
                    super::mac::check_extracted_tree(&tmp, a.max_unpacked).map_err(|e| fail(ErrCode::ArchiveRefused, "S2", e))?;
                    let entries: Vec<PathBuf> = std::fs::read_dir(&tmp).map_err(|e| fail(ErrCode::ArchiveRefused, "S2", e.to_string()))?.filter_map(|e| e.ok()).map(|e| e.path()).collect();
                    let app = super::macupdate::sole_app_bundle(&entries).map_err(|e| fail(ErrCode::ArchiveRefused, "S2", e.to_string()))?;
                    let _ = crate::hidden_command("/usr/bin/xattr").arg("-cr").arg(&app).output();
                    std::fs::rename(&app, &staged).map_err(|e| fail(ErrCode::MacAppsNotWritable, "S2", e.to_string()))?;
                }
                super::mac::verify_bundle(&staged, a.cdhash.as_deref().unwrap_or(""), &self.expect_new()?)?;
                // stage 새 바이너리의 pack-plan 게이트(사전 판정 · §3-6 S2)
                let o = self.child(&staged.join("Contents/MacOS/cys"), &["pack-plan", "--json"])?;
                if !o.status.success() {
                    return Err(fail(ErrCode::BuildInfoMismatch, "S2", "pack-plan 게이트"));
                }
                j.stage_path = staged.to_string_lossy().to_string();
                j.stage_tree_sha256 = tree_sha(&staged).map_err(|e| fail(ErrCode::ArchiveRefused, "S2", e))?;
            }
            Os::Win => {
                let bytes = std::fs::read(&dst).map_err(|e| fail(ErrCode::DlShaMismatch, "S2", e.to_string()))?;
                if !bytes.starts_with(b"MZ") {
                    return Err(fail(ErrCode::ArchiveRefused, "S2", "실행 파일 아님"));
                }
                let sig_url = a.a2_sig_url.clone().ok_or_else(|| fail(ErrCode::WinA2SigBad, "S2", "a2_sig_url 없음"))?;
                let sig = super::net::fetch(&sig_url, super::url::Hop::AssetFirst, 4096).map_err(|_| fail(ErrCode::WinA2SigBad, "S2", "서명 미도달"))?.bytes;
                let kr = super::keys::UpdateKeyring::embedded().map_err(|e| fail(ErrCode::WinA2SigBad, "S2", e))?;
                let now = super::clock::wall_now();
                let ok = kr.verify_any(super::keys::Purpose::WinAsset, &bytes, &sig, now).is_ok();
                if !ok {
                    return Err(fail(ErrCode::WinA2SigBad, "S2", "A2 서명 불일치"));
                }
                // ★2판 C11: 서명도 stage 에 둔다(S11 이 installers/<seq>/ 로 함께 보존 · 쓸 때마다 재검증)
                super::journal::durable_write(&stage.join(SETUP_SIG), &sig).map_err(|e| fail(ErrCode::DiskLow, "S2", e))?;
                let pm = a.payload_manifest.clone().ok_or_else(|| fail(ErrCode::WinPayloadMismatch, "S2", "payload_manifest 없음"))?;
                j.payload_manifest_sha256 = super::payload::manifest_sha256(&pm);
                j.stage_path = dst.to_string_lossy().to_string();
                j.stage_tree_sha256 = a.sha256.clone();
            }
        }
        j.release_seq = a.release_seq;
        j.from_release_seq = super::buildinfo::release_seq();
        j.target = a.target.clone();
        Ok(())
    }

    fn quiesce(&mut self, _j: &Journal) -> Step {
        let v = (self.env.rpc)("update.quiesce", json!({"txn": self.token, "ttl_secs": super::quiesce::DEFAULT_TTL_SECS}))
            .map_err(|e| fail(ErrCode::RotateFailed, "S3", e))?;
        serde_json::from_value::<super::quiesce::Token>(v).map_err(|e| fail(ErrCode::RotateFailed, "S3", e.to_string()))?;
        Ok(())
    }

    fn drain(&mut self, _j: &Journal) -> Step {
        let o = self.child(&self.env.old_cys, &["drain", "--verify", "--timeout", "60"])?;
        let v: Value = serde_json::from_slice(&o.stdout).map_err(|_| fail(ErrCode::RotateFailed, "S4", "drain 결과 없음"))?;
        if v["total"].as_u64() == Some(0) || v["all_saved"].as_bool() == Some(true) {
            self.q1 = Some(self.token_now()?);
            Ok(())
        } else {
            Err(fail(ErrCode::RotateFailed, "S4", "all_saved 아님"))
        }
    }

    fn recheck(&mut self, _j: &Journal) -> Step {
        std::thread::sleep(std::time::Duration::from_secs(self.env.settle_secs));
        let t2 = self.token_now()?;
        let t1 = self.q1.clone().ok_or_else(|| fail(ErrCode::RotateFailed, "S5", "S4 토큰 없음"))?;
        let why = super::quiesce::recheck_diff(&t1, &t2);
        if why.is_empty() {
            self.q1 = Some(t2);
            Ok(())
        } else {
            Err(fail(ErrCode::RotateFailed, "S5", why.join(" · ")))
        }
    }

    fn baseline(&mut self, j: &Journal) -> Step {
        let b = Baseline {
            seats: self.seats()?,
            doctor_fail: self.doctor_fail(&self.env.old_cys.clone()),
            user: verify::collect_user_tree(&self.env.cys_root).map_err(|e| fail(ErrCode::VerifyFailed, "S5b", e))?,
            features: super::buildinfo::FEATURES.iter().map(|s| s.to_string()).collect(),
            hold_seq: super::hold::last_seq_readonly(&self.env.update_dir).unwrap_or(0),
            pack: self.pack_id(),
            platform_mark: self.platform_mark()?.to_string(),
        };
        super::quiesce::write_json(&self.env.update_dir, "attempt.json", &json!({"txn_id": j.txn_id, "baseline": b}))
            .map_err(|e| fail(ErrCode::DiskLow, "S5b", e))?;
        self.b0 = Some(b);
        Ok(())
    }

    fn confirm(&mut self, _j: &Journal) -> Step {
        reconfirm(&self.env.update_dir, &self.env.channel, &self.cand)
    }

    fn stop(&mut self, _j: &Journal) -> Step {
        if self.env.os == Os::Win {
            // S7~S9b 동안 Global\cys-installer 를 쥔다(옛 설치기 ⓪ = exit 5 · 우리 1.1.8+ 설치기는 ⓪-a 토큰으로 위임 수용)
            super::win_install::hold_installer_mutex().map_err(|e| fail(ErrCode::WinLaunchBlocked, "S7", e))?;
        }
        self.rotate(&self.env.old_cys.clone(), true)
    }

    fn snapshot(&mut self, j: &mut Journal) -> Step {
        let root = super::snapshot::backup_root(&self.env.update_dir).join(super::snapshot::snapshot_name(j.from_release_seq, &j.txn_id));
        let mut shas = Vec::new();
        for (name, src) in self.snapshot_roots() {
            let dst = root.join(name);
            let sha = if dst.join(super::snapshot::MANIFEST_FILE).exists() {
                super::snapshot::verify(&dst)
            } else if name == "cys" {
                super::snapshot::take(&src, &dst, &RealOps::cys_filter)
            } else {
                let f = self.state_filter();
                super::snapshot::take(&src, &dst, &f)
            }
            .map_err(|e| fail(ErrCode::DiskLow, "S8", e))?;
            shas.push(format!("{name}:{sha}"));
        }
        if self.env.os == Os::Win {
            // 롤백 자산(N7 · §3-7 ②): 설치판 본문·설치기가 installers\<seq>\ 에 있어야 한다 — ★2판 C10: 그 자리에서 U 본문 서명·설치기
            //   sha256·A2 서명을 다시 검증한 것만(현장 해시를 신뢰하지 않는다).
            let dir = self.installers_dir(j.from_release_seq);
            let inst = dir.join(SETUP);
            let v = verify_installer_dir(&dir, j.from_release_seq, true).map_err(|e| fail(ErrCode::NoRollbackAsset, "S8", format!("설치판 롤백 자산: {e}")))?;
            let sha = v.setup_sha256.unwrap_or_default();
            j.prev_installer = Some(PrevInstaller { path: inst.to_string_lossy().to_string(), sha256: sha, release_seq: j.from_release_seq });
        }
        j.snapshot_dir = root.to_string_lossy().to_string();
        j.snapshot_manifest_sha256 = shas.join(",");
        // N7 「직전 실측 백업량」(MA3) — 다음 틱의 공간식 재료.
        let bytes: u64 = ["state", "cys"]
            .iter()
            .filter_map(|n| std::fs::read_to_string(root.join(n).join(super::snapshot::MANIFEST_FILE)).ok())
            .filter_map(|t| super::snapshot::parse_manifest(&t).ok())
            .map(|m| m.values().map(|e| e.size).sum::<u64>())
            .sum();
        let _ = super::notify::update_state(&self.env.update_dir, |m| {
            m.insert("last_backup_bytes".into(), json!(bytes));
        });
        Ok(())
    }

    fn commit_check(&mut self, j: &Journal) -> Step {
        reconfirm(&self.env.update_dir, &self.env.channel, &self.cand)?;
        if let Some(t1) = self.q1.clone() {
            // 데몬은 섰다 — 세대 토큰은 S5 에서 확정 · 보류 로그 증가만 다시 본다(정지 뒤 보류 = 0 이어야 함)
            let now = super::hold::last_seq_readonly(&self.env.update_dir).unwrap_or(u64::MAX);
            if now > t1.hold_seq {
                return Err(fail(ErrCode::RotateFailed, "S8b", "보류 로그 증가"));
            }
        }
        if self.env.os == Os::Mac {
            let now = tree_sha(Path::new(&j.stage_path)).map_err(|e| fail(ErrCode::ArchiveRefused, "S8b", e))?;
            if now != j.stage_tree_sha256 {
                return Err(fail(ErrCode::ArchiveRefused, "S8b", "stage 트리 바뀜"));
            }
        }
        Ok(())
    }

    fn canonical(&mut self, _j: &Journal) -> Canon {
        let (Ok(new), old) = (self.expect_new(), self.expect_old()) else { return Canon::Unknown };
        match self.env.os {
            // ★3판(Fable 2R m2): 번들 바이너리(build-info) 실행 전 서명·DR 핀 — 실패 = 판독 불가
            Os::Mac => {
                if super::mac::verify_signature_pin(&self.env.canonical_app).is_err() {
                    return Canon::Unknown;
                }
                super::mac::judge_canonical(super::mac::bundle_ident(&self.env.canonical_app).as_ref(), &new, &old)
            }
            Os::Win => {
                let pm = self.asset().ok().and_then(|a| a.payload_manifest.clone()).unwrap_or_default();
                if !pm.is_empty() && super::payload::verify_install(&self.env.install_dir, &pm, None).ok() {
                    Canon::New
                } else {
                    Canon::Old
                }
            }
        }
    }

    fn swap(&mut self, j: &mut Journal) -> Step {
        if self.env.dry_run {
            return Err(fail(ErrCode::RotateFailed, "S9", "CYS_UPDATE_DRY_RUN — 교체 0"));
        }
        match self.env.os {
            Os::Mac => {
                let staged = PathBuf::from(&j.stage_path);
                let from = j.from_release_seq;
                let mut prev = None;
                super::mac::swap_forward(&self.env.canonical_app, &staged, from, &mut |p, renamed| {
                    prev = Some((p.to_path_buf(), renamed));
                    Ok(())
                })?;
                let old = self.expect_old();
                if let Some((p, renamed)) = prev {
                    j.prev_bundle = Some(super::journal::PrevBundle { path: p.to_string_lossy().to_string(), build_id: old.build_id, file_id: String::new(), renamed });
                }
                Ok(())
            }
            Os::Win => super::win_install::run_installer(Path::new(&j.stage_path), &self.env.install_dir, &self.token, &j.stage_tree_sha256),
        }
    }

    fn payload_ok(&mut self, j: &Journal) -> Step {
        let a = self.asset()?.clone();
        let pm = a.payload_manifest.clone().unwrap_or_default();
        let old = load_installer_manifest(&self.installers_dir(j.from_release_seq));
        let check = |dir: &Path| super::payload::verify_install(dir, &pm, old.as_deref());
        let mut r = check(&self.env.install_dir);
        if !r.stale_old_only.is_empty() {
            if let Some(old) = old.as_deref() {
                super::payload::delete_old_only(&self.env.install_dir, old, &pm).map_err(|e| fail(ErrCode::WinPayloadMismatch, "S9b", e))?;
            }
            r = check(&self.env.install_dir);
        }
        if !r.ok() {
            // 같은 설치기 **1회** 재실행 → 다시 대조(폭주 방지 — 재시도 상한 1)
            super::win_install::run_installer(Path::new(&j.stage_path), &self.env.install_dir, &self.token, &j.stage_tree_sha256)?;
            r = check(&self.env.install_dir);
            if !r.ok() {
                return Err(fail(ErrCode::WinPayloadMismatch, "S9b", format!("{} 누락 {} 불일치 {} 구판 잔존", r.missing.len(), r.mismatched.len(), r.stale_old_only.len())));
            }
        }
        match super::mac::bundle_ident_exe(&self.new_cys()) {
            Some(i) if i == self.expect_new()? => {}
            other => return Err(fail(ErrCode::BuildInfoMismatch, "S9b", format!("{other:?}"))),
        }
        let o = self.child(&self.new_cys(), &["pack-plan", "--json"])?;
        if !o.status.success() {
            return Err(fail(ErrCode::BuildInfoMismatch, "S9b", "pack-plan 게이트"));
        }
        Ok(())
    }

    fn start_new(&mut self, _j: &Journal) -> Step {
        super::win_install::release_installer_mutex(); // S9b 끝 = 뮤텍스 놓음(§3-7 ⑦)
        self.rotate(&self.new_cys(), false)
    }

    fn post_verify(&mut self, j: &Journal, rollback: bool) -> Step {
        let b0 = match &self.b0 {
            Some(b) => b.clone(),
            None => {
                let v: Value = super::quiesce::read_json(&self.env.update_dir, "attempt.json").ok_or_else(|| fail(ErrCode::VerifyFailed, "V0", "기준선 없음"))?;
                serde_json::from_value(v["baseline"].clone()).map_err(|e| fail(ErrCode::VerifyFailed, "V0", e.to_string()))?
            }
        };
        let (exe, exp) = if rollback {
            let o = self.expect_old();
            (
                self.env.old_cys.clone(),
                Expect { release_seq: o.release_seq, build_id: o.build_id, target: o.target, platform_mark: b0.platform_mark.clone(), ..Default::default() },
            )
        } else {
            let a = self.asset()?;
            let bp = a.bundled_pack.as_ref().map(|p| PackId { version: p.version.clone(), digest: p.digest.clone() }).unwrap_or_default();
            // ★2판 C9: 기판 표지 기대 = 본문 행(맥 cdhash · 윈 페이로드 매니페스트의 cys.exe sha256)
            let mark = match self.env.os {
                Os::Mac => a.cdhash.clone().unwrap_or_default(),
                Os::Win => a
                    .payload_manifest
                    .as_ref()
                    .and_then(|m| m.iter().find(|e| super::payload::norm(&e.path) == "cys.exe").map(|e| e.sha256.clone()))
                    .unwrap_or_default(),
            };
            (
                self.new_cys(),
                Expect { release_seq: a.release_seq, build_id: a.build_id.clone(), target: a.target.clone(), bundled_pack: bp, platform_mark: mark, ..Default::default() },
            )
        };
        // ★2판(codex 1R C9): 아래 칸은 전부 **독립 관측**이다 — 상수·기준선 복사·기대값 복사 0. 관측 실패는 그 V 의 실패로 닫힌다.
        let bi = self.child(&exe, &["build-info", "--json"]).ok().filter(|o| o.status.success()).and_then(|o| serde_json::from_slice::<Value>(&o.stdout).ok());
        let ident = super::mac::Ident {
            release_seq: bi.as_ref().and_then(|v| v["release_seq"].as_u64()).unwrap_or(0),
            build_id: bi.as_ref().and_then(|v| v["build_id"].as_str()).unwrap_or("").to_string(),
            target: bi.as_ref().and_then(|v| v["target"].as_str()).unwrap_or("").to_string(),
        };
        let features: std::collections::BTreeSet<String> = bi
            .as_ref()
            .and_then(|v| v["features"].as_array())
            .map(|a| a.iter().filter_map(|x| x.as_str().map(str::to_string)).collect())
            .unwrap_or_default();
        let platform_mark = self.platform_mark().map(|m| m.to_string()).unwrap_or_else(|f| format!("관측 실패: {}", f.detail));
        let hold_now = super::hold::last_seq_readonly(&self.env.update_dir);
        let delivered = std::fs::read(self.env.update_dir.join(super::quiesce::INGESTED_FILE))
            .ok()
            .and_then(|b| serde_json::from_slice::<Value>(&b).ok())
            .and_then(|v| v["delivered_hold_seq"].as_u64())
            .unwrap_or(0);
        let identify = (self.env.rpc)("system.identify", json!({})).unwrap_or(Value::Null);
        let mut ping = 0;
        for _ in 0..3 {
            if (self.env.rpc)("system.ping", json!({})).is_ok() {
                ping += 1;
            }
        }
        let post = Post {
            release_seq: ident.release_seq,
            build_id: ident.build_id.clone(),
            target: ident.target.clone(),
            // 데몬이 build_id 를 말하지 않으면 빈 값(설치본 값으로 메우지 않는다 → V1 불일치)
            daemon_build_id: identify["build_id"].as_str().unwrap_or("").to_string(),
            platform_mark,
            ping_ok_streak: ping,
            cysd_procs: hq_daemon_count(&identify),
            seats: self.seats()?,
            drain_seats: None,
            restore_rc: self.last_rotate_rc.unwrap_or(-1),
            doctor_fail: self.doctor_fail(&exe),
            user: verify::collect_user_tree(&self.env.cys_root).map_err(|e| fail(ErrCode::VerifyFailed, "V5", e))?,
            forbidden_jobs: self.forbidden_jobs(),
            features,
            merge_pending_new: vec![],
            pack: self.pack_id(),
            hold_last_seq: hold_now.unwrap_or(0),
            hold_delivered_seq: delivered,
            // 보류 로그 판독 불가 = 관측 실패 = 사라짐 1 이상으로 닫음 · 판독됨 = 기준선보다 줄어든 seq 수(seq 단조라 줄 소실 = 후퇴)
            hold_lost: hold_now.map(|n| b0.hold_seq.saturating_sub(n)).unwrap_or(1),
        };
        let _ = j;
        let checks = verify::judge(&b0, &post, &exp, rollback);
        if verify::passed(&checks) {
            Ok(())
        } else {
            let bad: Vec<String> = checks.iter().filter(|c| !c.ok).map(|c| format!("{} {}", c.id, c.detail)).collect();
            let id = checks.iter().find(|c| !c.ok).map(|c| c.id).unwrap_or("V?");
            let code = if id == "V1" { ErrCode::BuildInfoMismatch } else { ErrCode::VerifyFailed };
            Err(fail(code, id, bad.join(" · ")))
        }
    }

    fn commit(&mut self, j: &Journal) -> Step {
        // ★2판(codex 1R C11): DONE 의 필수 선행 = ① 새 판 서명 본문(+윈 설치기·A2 서명)을 installers/<seq>/ 에 원자 보존·재검증
        //   ② 수용 기록(feed_rev·봉투 sha256·signed_at · 설치 seq = 새 판) durable 쓰기. 실패 = Err(호출자가 롤백) · stage 는 그 뒤에 지운다.
        self.preserve_release(j)?;
        let c = &self.cand;
        let acc = super::feed::AcceptedFeed {
            feed_rev: c.feed_rev.ok_or_else(|| fail(ErrCode::RotateFailed, "S11", "후보에 feed_rev 없음"))?,
            envelope_sha256: c.envelope_sha256.clone().ok_or_else(|| fail(ErrCode::RotateFailed, "S11", "후보에 봉투 sha256 없음"))?,
            feed_release_seq: c.release_seq,
            installed_release_seq: c.release_seq,
            signed_at: c.envelope_signed_at.ok_or_else(|| fail(ErrCode::RotateFailed, "S11", "후보에 signed_at 없음"))?,
            at: super::clock::wall_now(),
        };
        super::feed::write_accepted(&super::check::accepted_path(&self.env.update_dir, "cysr", &self.env.channel), &acc)
            .map_err(|e| fail(ErrCode::RotateFailed, "S11", format!("수용 기록: {e}")))?;
        let _ = std::fs::remove_dir_all(self.stage_dir(j));
        let names: Vec<String> = std::fs::read_dir(super::snapshot::backup_root(&self.env.update_dir))
            .map(|rd| rd.filter_map(|e| e.ok()).map(|e| e.file_name().to_string_lossy().to_string()).collect())
            .unwrap_or_default();
        let fresh = super::snapshot::snapshot_name(j.from_release_seq, &j.txn_id);
        let never: std::collections::BTreeSet<String> = [fresh.clone()].into();
        for n in super::snapshot::prune_plan(&names, 2, true, &never) {
            let _ = std::fs::remove_dir_all(super::snapshot::backup_root(&self.env.update_dir).join(n));
        }
        if self.env.os == Os::Mac {
            if let Some(pb) = &j.prev_bundle {
                // 세대 2: 옛 번들은 다음 성공 갱신 때 지운다(지금 것은 롤백 근거) — 이번 것은 남긴다.
                let _ = pb;
            }
        }
        Ok(())
    }

    fn release(&mut self, j: &Journal) {
        super::win_install::release_installer_mutex();
        let _ = (self.env.rpc)("update.release", json!({"txn": self.token}));
        let _ = std::fs::remove_dir_all(self.stage_dir(j));
        if self.env.os == Os::Mac {
            let _ = std::fs::remove_dir_all(super::mac::staged_path(&self.env.canonical_app, j.release_seq));
        }
    }

    fn start_old(&mut self, _j: &Journal) -> Step {
        let exe = match self.env.os {
            Os::Mac => self.env.canonical_app.join("Contents/MacOS/cys"),
            Os::Win => self.env.old_cys.clone(),
        };
        self.rotate(&exe, false)
    }

    fn rb_prepare(&mut self, j: &Journal) -> Step {
        let _ = self.child(&self.new_cys(), &["drain", "--verify", "--timeout", "60"]);
        let _ = self.rotate(&self.new_cys(), true);
        let root = PathBuf::from(&j.snapshot_dir);
        for (name, _) in self.snapshot_roots() {
            let got = super::snapshot::verify(&root.join(name)).map_err(|e| fail(ErrCode::RollbackBlocked, "RB_PREPARED", e))?;
            // ★2판(codex 1R C6): 저널이 S8 에 고정한 뿌리별 매니페스트 sha256 과 상수시간 비교(사본+매니페스트를 함께 바꾼 백업 거부).
            let want = journal_snapshot_sha(j, name).ok_or_else(|| fail(ErrCode::RollbackBlocked, "RB_PREPARED", format!("저널에 {name} 매니페스트 sha 없음")))?;
            if !super::snapshot::digest_eq(&got, &want) {
                return Err(fail(ErrCode::RollbackBlocked, "RB_PREPARED", format!("{name} 매니페스트 sha256 ≠ 저널 고정값")));
            }
        }
        Ok(())
    }

    fn rb_swap(&mut self, j: &Journal) -> Step {
        let found = self.canonical(j);
        match self.env.os {
            Os::Mac => {
                // ★2판(codex 1R C7): 정식 자리 = 옛 판이면 prev_bundle 없이 즉시 끝(kill@S9:after · 교환 전 죽음). 새 판이면 옛 번들을
                //   교환 전에 정해진 후보(저널 기록 · old 자리 · stage 자리) 중 신원이 옛 판과 같은 **유일한** 것으로 찾는다.
                if found == Canon::Old {
                    return Ok(());
                }
                let recorded = j.prev_bundle.as_ref().map(|p| PathBuf::from(&p.path));
                let cands: Vec<(PathBuf, Option<super::mac::Ident>)> =
                    super::mac::prev_candidates(&self.env.canonical_app, Path::new(&j.stage_path), j.from_release_seq, recorded.as_deref())
                        .into_iter()
                        .map(|c| {
                            // ★3판 m2: 서명·DR 핀 실패 후보 = 실행하지 않고 판독 불가(후보 제외와 같음)
                            let id = if super::mac::verify_signature_pin(&c).is_ok() { super::mac::bundle_ident(&c) } else { None };
                            (c, id)
                        })
                        .collect();
                let prev = super::mac::pick_unique_old(&cands, &self.expect_old())
                    .ok_or_else(|| fail(ErrCode::RecoverAnomaly, "RB_SWAPPED", format!("옛 번들 후보 판정 불가({}개)", cands.len())))?;
                super::mac::rb_swap(&self.env.canonical_app, &prev, found)
            }
            Os::Win => {
                if found == Canon::Old && self.old_payload_ok(j) {
                    return Ok(());
                }
                let pi = j.prev_installer.as_ref().ok_or_else(|| fail(ErrCode::NoRollbackAsset, "RB_SWAPPED", "설치판 설치기 기록 없음"))?;
                // ★2판 C10: 실행 직전 재검증(본문 서명·설치기 sha256·A2) — 저널 sha 와도 같아야 한다(실행은 그 sha 로 쥔 핸들).
                let v = verify_installer_dir(&self.installers_dir(j.from_release_seq), j.from_release_seq, true)
                    .map_err(|e| fail(ErrCode::NoRollbackAsset, "RB_SWAPPED", format!("설치판 롤백 자산: {e}")))?;
                if v.setup_sha256.as_deref() != Some(pi.sha256.as_str()) {
                    return Err(fail(ErrCode::NoRollbackAsset, "RB_SWAPPED", "설치판 설치기 sha256 ≠ 저널"));
                }
                super::win_install::run_installer(Path::new(&pi.path), &self.env.install_dir, &self.token, &pi.sha256)?;
                let newer = self.asset()?.payload_manifest.clone().unwrap_or_default();
                if let Some(older) = load_installer_manifest(&self.installers_dir(j.from_release_seq)) {
                    super::payload::delete_old_only(&self.env.install_dir, &newer, &older).map_err(|e| fail(ErrCode::RollbackFailed, "RB_SWAPPED", e))?;
                }
                if self.old_payload_ok(j) {
                    Ok(())
                } else {
                    Err(fail(ErrCode::RollbackFailed, "RB_SWAPPED", "옛 매니페스트 전수 불일치"))
                }
            }
        }
    }

    fn rb_restore(&mut self, j: &Journal) -> Step {
        let root = PathBuf::from(&j.snapshot_dir);
        let want_st = journal_snapshot_sha(j, "state");
        let want_cy = journal_snapshot_sha(j, "cys");
        if want_st.is_none() || want_cy.is_none() {
            return Err(fail(ErrCode::RollbackBlocked, "RB_RESTORED", "저널 매니페스트 sha 없음"));
        }
        self.restore_trees(&root, "RB_RESTORED", &j.txn_id, want_st.as_deref(), want_cy.as_deref())
    }

    fn recover_pack(&mut self, j: &Journal) -> Step {
        crate::pack::recover_pack_journal().map(|_| ()).map_err(|e| fail(ErrCode::RollbackFailed, "PACK", e))?;
        // ★2판(codex 1R C14): 팩 저널 복구만으로 PACK_DONE 을 쓰지 않는다 — 사용자 트리 해시 대조·복원까지 성공해야.
        let q = super::snapshot::quarantine_dir(&self.env.update_dir, &j.txn_id);
        pack_user_tree_restore(&self.env.cys_root, &j.stage_tree_sha256, Path::new(&j.snapshot_dir), &q)
            .map_err(|e| fail(ErrCode::RollbackFailed, "PACK", e))
    }

    fn reconstruct(&mut self) -> Step {
        // §3-11 저널 손상 재구성: 정식 자리 실물이 설치판(옛) 또는 후보(새) 중 정확히 하나와 같으면 확정.
        // ★2판(codex 1R C13): ① 맥 = 번들 바이너리를 실행(build-info)하기 **전에** codesign 엄격 + DR 핀 · 새 판으로 판정되면 cdhash 까지
        //   (verify_bundle 3겹) ② 윈 = 수용 본문은 서명 재검증된 것만(load_installer_manifest = verify_installer_dir) ③ 옛 판으로 판정되면
        //   팩·사용자 트리·상태 폴더를 그 판의 최신 검증 스냅샷으로 복원한 뒤에만 종결(복원 중 죽은 경우 · 스냅샷 없음 = S8 전 = 무변경).
        let rj = |d: String| fail(ErrCode::JournalCorrupt, "reconstruct", d);
        let old = self.expect_old();
        let new = self.expect_new().ok();
        let is_old = match self.env.os {
            Os::Mac => {
                let canon = super::mac::real_path(&self.env.canonical_app, "reconstruct").map_err(|f| rj(f.detail))?;
                super::mac::verify_signature_pin(&canon).map_err(|f| rj(format!("서명 검증 전 실행 거부: {}", f.detail)))?;
                let found = super::mac::bundle_ident(&canon);
                match (&found, &new) {
                    (Some(f), _) if f == &old => true,
                    (Some(f), Some(n)) if f == n => {
                        super::mac::verify_bundle(&canon, self.cand.asset.cdhash.as_deref().unwrap_or(""), n).map_err(|f| rj(f.detail))?;
                        false
                    }
                    _ => return Err(rj("정식 자리 번들 = 어느 판과도 불일치".into())),
                }
            }
            Os::Win => {
                let older = load_installer_manifest(&self.installers_dir(old.release_seq));
                let newer = self.asset().ok().and_then(|a| a.payload_manifest.clone()).filter(|m| !m.is_empty());
                match (older, newer) {
                    (Some(m), _) if super::payload::verify_install(&self.env.install_dir, &m, None).ok() => true,
                    (_, Some(m)) if super::payload::verify_install(&self.env.install_dir, &m, None).ok() => false,
                    _ => return Err(rj("설치 폴더 = 서명 검증된 수용 매니페스트와 불일치".into())),
                }
            }
        };
        if is_old {
            // ★3판(Fable 2R N3): 「가장 최근 스냅샷으로 상태 폴더까지 덮기」 → 이번 시도(attempt.json txn)의 스냅샷과 **대조** → 어긋날 때만
            //   데몬을 내리고 `~/.cys` 의 팩·사용자 트리만 복원(상태 폴더·app-notify.* 무접촉).
            let (old_cys, upd, root) = (self.env.old_cys.clone(), self.env.update_dir.clone(), self.env.cys_root.clone());
            let mut stop = || self.rotate(&old_cys, true);
            reconstruct_trees(&upd, &root, old.release_seq, &mut stop).map_err(|f| rj(f.detail))?;
        }
        Ok(())
    }

    fn record(&mut self, j: Option<&Journal>, kind: Kind, f: Option<&Fail>) {
        let (kname, code) = match kind {
            Kind::Ok => ("ok", ErrCode::Ok),
            Kind::Deferred => ("deferred", f.map(|f| f.code).unwrap_or(ErrCode::Ok)),
            Kind::Rollback => ("rollback", ErrCode::RollbackOk),
            Kind::RollbackFailed => ("rollback_failed", ErrCode::RollbackFailed),
            Kind::PackOk => ("pack_ok", ErrCode::Ok),
            Kind::JournalCorrupt => ("journal_corrupt", ErrCode::JournalCorrupt),
            Kind::SeatsBlocked => ("seats_blocked", ErrCode::JournalCorrupt),
        };
        let a = Some(self.cand.asset.clone());
        let o = super::notify::Outcome {
            kind: kname,
            code: if kind == Kind::Rollback { f.map(|f| f.code).unwrap_or(ErrCode::RollbackOk) } else { code },
            component: "cysr".into(),
            channel: self.env.channel.clone(),
            target: a.as_ref().map(|a| a.target.clone()).unwrap_or_default(),
            release_seq: j.map(|j| j.release_seq).unwrap_or(0),
            from_release_seq: super::buildinfo::release_seq(),
            from_version: self.old_version.clone(),
            to_version: self.cand.version.clone(),
            force_permanent: f.map(|f| matches!(f.step.as_str(), "V5" | "V7")).unwrap_or(false),
            detail: f.map(|f| super::errors::clip(&f.detail)).unwrap_or_default(),
            notes_ko: self.cand.notes_ko.clone(),
        };
        let now = super::clock::wall_now();
        let rid = format!("{}:{}", j.map(|j| j.txn_id.as_str()).unwrap_or("-"), kname);
        let stamp = super::clock::now_stamp();
        let _ = super::notify::update_state(&self.env.update_dir, |m| super::notify::apply(m, &o, &rid, now, Some(&stamp)));
        if kind != Kind::Deferred {
            if let Some(cd) = super::notify::counsel_dir() {
                let _ = super::notify::append_update(&cd, &o.from_version, &o.to_version, kname, now);
            }
            super::notify::signal(&self.env.cys_root.join("pack"), if kind == Kind::Ok { ErrCode::Ok } else { o.code });
        }
    }
}

impl RealOps {
    fn old_payload_ok(&self, j: &Journal) -> bool {
        load_installer_manifest(&self.installers_dir(j.from_release_seq))
            .map(|m| super::payload::verify_install(&self.env.install_dir, &m, None).ok())
            .unwrap_or(false)
    }
}

/// S6·S8b 재확인: 봉투·폐기문을 다시 받아 같은 `release_seq` · halt 아님 · 후보 폐기 아님 · 설치판 폐기 무변화.
// ── ★2판(codex 1R C14): 팩 참가자 ↔ 전역 상태기 ─────────────────────────────────────────────

fn user_snapshot_filter(root: &Path) -> impl Fn(&str) -> bool + '_ {
    move |rel: &str| {
        let first = rel.split('/').next().unwrap_or_default();
        (first == "local" || first.starts_with("pack")) && (root.join(rel).is_dir() || verify::is_user_path(rel))
    }
}

/// (★2판 C14 · ⚠CLI 미배선 — 윈 CI T8 뒤 철회: 앱 기동 init-pack 마다 PACK_APPLY 가 데몬 부팅을 막고 설치기와 겹친다 · HANDOFF §5 ⓗ 📌)
/// 팩을 바꾸는 트랜잭션 소유자가 바꾸기 전에 부른다: 비종결 저널이 있으면 거부(복구 먼저) ·
/// 사용자 트리 사본(`backup/pack-<txn>/user`)과 요약 해시를 저널 PACK_APPLY 에 고정(`stage_tree_sha256` = 해시 · `snapshot_dir` = 사본).
pub fn pack_txn_begin(update_dir: &Path, txn_id: &str, epoch: u64, cys_root: &Path) -> Result<(), String> {
    use super::journal::{self, ReadOutcome, State};
    match journal::read(update_dir) {
        ReadOutcome::Ok(j) if !j.state.is_terminal() => return Err(format!("복구 대기 저널 {}", j.state.name())),
        ReadOutcome::Corrupt(e) | ReadOutcome::Degraded(_, e) => return Err(format!("저널 손상 {e}")),
        _ => {}
    }
    let digest = verify::user_tree_digest(cys_root)?;
    let snap = super::snapshot::backup_root(update_dir).join(format!("pack-{txn_id}")).join("user");
    let _ = std::fs::remove_dir_all(&snap);
    super::snapshot::take(cys_root, &snap, &user_snapshot_filter(cys_root))?;
    journal::advance(update_dir, txn_id, epoch, State::Locked, |_| {}).map_err(|e| format!("{e:?}"))?;
    journal::advance(update_dir, txn_id, epoch, State::PackApply, |n| {
        n.stage_tree_sha256 = digest.clone();
        n.snapshot_dir = snap.to_string_lossy().to_string();
    })
    .map_err(|e| format!("{e:?}"))?;
    Ok(())
}

/// 성공 종결 — PACK_DONE + 사용자 트리 사본 정리.
pub fn pack_txn_end(update_dir: &Path, txn_id: &str, epoch: u64) -> Result<(), String> {
    super::journal::advance(update_dir, txn_id, epoch, super::journal::State::PackDone, |_| {}).map_err(|e| format!("{e:?}"))?;
    let _ = std::fs::remove_dir_all(super::snapshot::backup_root(update_dir).join(format!("pack-{txn_id}")));
    Ok(())
}

/// PACK 복구 뒤 사용자 트리 검증·복원(순수에 가까움 · 시험 대상): 지금 해시 = 고정값이면 끝 · 아니면 사본으로 사용자 경로만 복원(나머지
/// 보호) → 다시 같아야 Ok.
pub fn pack_user_tree_restore(cys_root: &Path, want_digest: &str, snap: &Path, quarantine: &Path) -> Result<(), String> {
    if want_digest.is_empty() {
        return Err("저널에 사용자 트리 해시 없음".into());
    }
    if verify::user_tree_digest(cys_root)? == want_digest {
        return Ok(());
    }
    super::snapshot::restore(cys_root, snap, quarantine, &|rel: &str| !verify::is_user_path(rel), None)?;
    if verify::user_tree_digest(cys_root)? != want_digest {
        return Err("복원 뒤 사용자 트리 해시 불일치".into());
    }
    Ok(())
}

/// 재구성 복원 보호 경로(`~/.cys` 기준): 팩·사용자 트리 밖(`cys_filter` 거짓) · 갱신 폴더 · 앱 알림 장부(`app-notify.json`·`.lock` —
/// 어떤 경우에도 복원 금지 · U4 접점).
pub fn reconstruct_protected(rel: &str) -> bool {
    let name = rel.rsplit('/').next().unwrap_or_default();
    !RealOps::cys_filter(rel) || rel.split('/').next() == Some("update") || name == "app-notify.json" || name == "app-notify.lock"
}

/// ★3판(Fable 2R N3): 손상 저널 재구성의 트리 단계 — 원천 = **이번 시도**(`attempt.json` 의 txn_id)의 `backup/<seq>-<txn>/cys` 만(옛 시도의
/// 스냅샷 0 · 없으면 대조할 것 없음 = 무변경) · 대조(`snapshot::diff`) → 전부 같음 = 손대지 않음(Ok(false)) · 어긋남 = `stop()`(데몬 정지 ·
/// 실패 = 복원 0) 뒤 팩·사용자 트리만 복원(격리 키 = `reconstruct-<벽시계>`) → Ok(true). 상태 폴더는 대상이 아니다.
pub fn reconstruct_trees(update_dir: &Path, cys_root: &Path, old_seq: u64, stop: &mut dyn FnMut() -> Step) -> Result<bool, Fail> {
    let f = |d: String| fail(ErrCode::JournalCorrupt, "reconstruct", d);
    let Some(txn) = super::quiesce::read_json::<Value>(update_dir, "attempt.json").and_then(|v| v["txn_id"].as_str().map(str::to_string)) else {
        return Ok(false);
    };
    let snap = super::snapshot::backup_root(update_dir).join(super::snapshot::snapshot_name(old_seq, &txn)).join("cys");
    if !snap.join(super::snapshot::MANIFEST_FILE).exists() {
        return Ok(false);
    }
    let plan = super::snapshot::diff(cys_root, &snap, &reconstruct_protected).map_err(f)?;
    if plan.iter().all(|a| matches!(a, super::snapshot::Action::Keep(_) | super::snapshot::Action::Protected(_))) {
        return Ok(false);
    }
    stop().map_err(|e| f(format!("복원 전 데몬 정지 실패: {}", e.detail)))?;
    let q = super::snapshot::quarantine_dir(update_dir, &format!("reconstruct-{}", super::clock::wall_now()));
    super::snapshot::restore(cys_root, &snap, &q.join("cys"), &reconstruct_protected, None).map_err(f)?;
    Ok(true)
}

/// ★2판 C13: 판 `seq` 의 스냅샷(`backup/<seq>-<txn>`) 중 두 뿌리가 모두 검증되는 가장 최근 것(수정 시각) — 저널 손상 재구성용.
pub fn latest_verified_snapshot(update_dir: &Path, seq: u64) -> Option<PathBuf> {
    let root = super::snapshot::backup_root(update_dir);
    let mut c: Vec<(std::time::SystemTime, PathBuf)> = std::fs::read_dir(&root)
        .ok()?
        .filter_map(|e| e.ok())
        .filter(|e| e.file_name().to_string_lossy().split_once('-').map(|(s, _)| s == seq.to_string()).unwrap_or(false))
        .filter_map(|e| Some((e.metadata().ok()?.modified().ok()?, e.path())))
        .collect();
    c.sort();
    c.into_iter().rev().map(|(_, p)| p).find(|p| ["state", "cys"].iter().all(|n| super::snapshot::verify(&p.join(n)).is_ok()))
}

/// 저널 `snapshot_manifest_sha256`(= `state:<sha>,cys:<sha>`)에서 뿌리 하나의 값.
pub fn journal_snapshot_sha(j: &Journal, name: &str) -> Option<String> {
    j.snapshot_manifest_sha256.split(',').find_map(|kv| kv.split_once(':').filter(|(k, _)| *k == name).map(|(_, v)| v.to_string()))
}

pub fn reconfirm(dir: &Path, channel: &str, first: &Candidate) -> Step {
    let now = super::clock::wall_now();
    let id = super::buildinfo::read_install_id(dir);
    let (res, _) = super::check::fetch_and_verify(dir, channel, now, id.as_deref().map(super::feed::rollout_bucket));
    let o = res.map_err(|e| fail(ErrCode::RotateFailed, "S6", e))?;
    same_decision(first, &o)
}

/// 재확인 판정(순수).
pub fn same_decision(first: &Candidate, again: &super::feed::FeedOutcome) -> Step {
    if again.halt {
        return Err(fail(ErrCode::RotateFailed, "S6", "halt"));
    }
    if again.verdict != super::feed::Verdict::Apply {
        return Err(fail(again.code, "S6", format!("판정 {}", again.verdict.as_str())));
    }
    if again.release_seq != Some(first.release_seq) || again.installed_revoked != first.installed_revoked {
        return Err(fail(ErrCode::RotateFailed, "S6", "release_seq·폐기 바뀜"));
    }
    Ok(())
}

/// 설치판 본문(`installers\<seq>\release.json` 의 이 기판 행 `payload_manifest`).
/// 보존 판 본문의 페이로드 매니페스트 — ★2판 C10: 서명 재검증을 통과한 본문만(폴더 이름 = seq).
pub fn load_installer_manifest(dir: &Path) -> Option<Vec<super::feed::PayloadEntry>> {
    let seq: u64 = dir.file_name()?.to_str()?.parse().ok()?;
    verify_installer_dir(dir, seq, false).ok().map(|v| v.manifest).filter(|m| !m.is_empty())
}

/// zip 항목 이름(`unzip -Z1`).
fn zip_names(zip: &Path) -> Result<Vec<String>, String> {
    let o = crate::hidden_command("/usr/bin/unzip").arg("-Z1").arg(zip).output().map_err(|e| e.to_string())?;
    if !o.status.success() {
        return Err("unzip -Z1 실패".into());
    }
    Ok(String::from_utf8_lossy(&o.stdout).lines().map(str::to_string).collect())
}

/// 폴더 트리 해시(상대 경로·파일 sha256 정렬 목록의 sha256 · 심링크 = 대상 문자열).
pub fn tree_sha(root: &Path) -> Result<String, String> {
    use sha2::{Digest, Sha256};
    let mut h = Sha256::new();
    let mut stack = vec![(root.to_path_buf(), String::new())];
    let mut rows = Vec::new();
    while let Some((d, pre)) = stack.pop() {
        for e in std::fs::read_dir(&d).map_err(|e| e.to_string())? {
            let e = e.map_err(|e| e.to_string())?;
            let rel = format!("{pre}/{}", e.file_name().to_string_lossy());
            let md = std::fs::symlink_metadata(e.path()).map_err(|e| e.to_string())?;
            if md.file_type().is_symlink() {
                rows.push(format!("L {rel} {}", std::fs::read_link(e.path()).map_err(|e| e.to_string())?.display()));
            } else if md.is_dir() {
                stack.push((e.path(), rel));
            } else {
                rows.push(format!("F {rel} {}", super::snapshot::sha256_file(&e.path())?.0));
            }
        }
    }
    rows.sort();
    for r in rows {
        h.update(r.as_bytes());
        h.update(b"\n");
    }
    Ok(format!("{:x}", h.finalize()))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn seats_from_org_ignores_surface_numbers_and_exited() {
        let org = json!({"surfaces": [
            {"surface_id": 5, "role": "master", "agent": "claude", "registered_session_id": "s1"},
            {"surface_id": 6, "role": "worker-2", "agent": "claude", "registered_session_id": "s2", "exited": true},
        ]});
        let after = json!({"surfaces": [{"surface_id": 91, "role": "master", "agent": "claude", "registered_session_id": "s1"}]});
        assert_eq!(seats_from_org(&org), seats_from_org(&after), "재기동으로 번호가 바뀌어도 같은 좌석");
        // ★2판 C9: dept = 행의 dept(에이전트 이름 아님) · 같은 역할이라도 에이전트가 바뀌면 다른 좌석
        let k = seats_from_org(&json!({"surfaces": [{"role": "worker-1", "dept": "edu", "agent": "claude", "registered_session_id": "s9"}]}));
        let k = k.into_iter().next().unwrap();
        assert_eq!((k.dept.as_str(), k.session_id.as_str()), ("edu", "claude|s9"));
        let codex = json!({"surfaces": [{"surface_id": 5, "role": "master", "agent": "codex", "registered_session_id": "s1"}]});
        assert_ne!(seats_from_org(&org), seats_from_org(&codex), "에이전트 교체 = 다른 좌석");
    }

    /// ★2판 C9: 관측 실패를 통과로 접지 않는다 — doctor 판독 불가 = FAIL 1건 · 이 사용자 cysd 수 = 실측(시험 프로세스엔 0).
    #[cfg(unix)]
    #[test]
    fn observations_fail_closed() {
        use std::os::unix::fs::PermissionsExt;
        let d = std::env::temp_dir().join(format!("cys-u2-obs-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&d);
        std::fs::create_dir_all(&d).unwrap();
        let exe = d.join("fake-cys");
        std::fs::write(&exe, "#!/bin/sh\necho not-json\n").unwrap();
        std::fs::set_permissions(&exe, std::fs::Permissions::from_mode(0o755)).unwrap();
        let mut env = crate::update::auto::build_env(d.clone(), "stable");
        env.rpc = Box::new(|_, _| Err("데몬 없음".into()));
        let a: crate::update::feed::Asset = serde_json::from_value(json!({"url": "", "size": 0, "sha256": "", "max_unpacked": 0, "target": "x", "release_seq": 1})).unwrap();
        let cand = Candidate { asset: a, version: String::new(), release_seq: 1, installed_revoked: false, notes_ko: None, feed_rev: None,
            envelope_sha256: None, envelope_signed_at: None, release_b64: None, release_sig_b64: None };
        let ops = RealOps::new(env, "t:1".into(), cand, String::new());
        assert_eq!(ops.doctor_fail(&exe).into_iter().collect::<Vec<_>>(), vec!["doctor_unavailable"]);
        assert_eq!(ops.forbidden_jobs(), vec!["observe_failed"], "schedule.status 판독 불가 = V6 실패");
        let _ = std::fs::remove_dir_all(&d);
    }

    #[test]
    fn doctor_fail_set_and_cys_filter() {
        let v = json!({"checks": [{"id": "a", "status": "FAIL"}, {"id": "b", "status": "ok"}, {"name": "c", "result": "fail"}]});
        assert_eq!(doctor_fails(&v).into_iter().collect::<Vec<_>>(), vec!["a", "c"]);
        for yes in ["pack/agents.json", "pack-dept-edu/x", ".pack-tmp/y", "local/a", ".pending-restore", ".pack-accepted.json"] {
            assert!(RealOps::cys_filter(yes), "{yes}");
        }
        for no in ["claude/x", "update/journal.json", "state/x", "round/a"] {
            assert!(!RealOps::cys_filter(no), "{no}");
        }
    }

    /// ★2판 C14: PACK_APPLY 중 죽음(사용자 파일이 바뀌고 새 사용자 파일이 생김) → 복구 = 사용자 트리 해시 대조 → 사본으로 사용자 경로만
    /// 복원(팩 본문 무접촉 · 새 사용자 파일 격리) → 해시 일치 · 저널 PACK_APPLY 고정값 · 성공 종결 = PACK_DONE + 사본 정리.
    #[test]
    fn pack_txn_pins_user_tree_and_recovery_restores_it() {
        let d = std::env::temp_dir().join(format!("cys-u2-packtxn-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&d);
        let (upd, root) = (d.join("update"), d.join("cys"));
        for (p, b) in [("local/me.md", "mine"), ("pack/soul.md", "S"), ("pack/agents.json", r#"{"agents":{}}"#), ("pack/lib/x.py", "v1")] {
            std::fs::create_dir_all(root.join(p).parent().unwrap()).unwrap();
            std::fs::write(root.join(p), b).unwrap();
        }
        let want = verify::user_tree_digest(&root).unwrap();
        pack_txn_begin(&upd, "t1", 1, &root).unwrap();
        let j = super::super::journal::read(&upd).journal().cloned().unwrap();
        assert_eq!((j.state, j.stage_tree_sha256.as_str()), (super::super::journal::State::PackApply, want.as_str()));
        assert!(pack_txn_begin(&upd, "t2", 2, &root).unwrap_err().contains("복구 대기"), "비종결 저널 위 새 팩 트랜잭션 거부");
        // 도중 죽음: 사용자 파일 덮임 · 새 사용자 파일 · 팩 본문 변경
        std::fs::write(root.join("local/me.md"), "clobbered").unwrap();
        std::fs::write(root.join("local/new.md"), "n").unwrap();
        std::fs::write(root.join("pack/lib/x.py"), "v2").unwrap();
        pack_user_tree_restore(&root, &j.stage_tree_sha256, Path::new(&j.snapshot_dir), &d.join("q")).unwrap();
        assert_eq!(std::fs::read_to_string(root.join("local/me.md")).unwrap(), "mine");
        assert!(!root.join("local/new.md").exists() && d.join("q/local/new.md").exists(), "새 사용자 파일 = 격리");
        assert_eq!(std::fs::read_to_string(root.join("pack/lib/x.py")).unwrap(), "v2", "팩 본문 = 팩 저널 몫(무접촉)");
        assert!(pack_user_tree_restore(&root, "", Path::new(&j.snapshot_dir), &d.join("q")).is_err(), "고정값 없음 = 실패");
        pack_txn_end(&upd, "t1", 1).unwrap();
        assert_eq!(super::super::journal::read(&upd).journal().unwrap().state, super::super::journal::State::PackDone);
        let _ = std::fs::remove_dir_all(&d);
    }

    /// ★3판 N3: 재구성 = 이번 시도 스냅샷과 대조 — ① 일치 트리 = 손대지 않음(데몬 정지도 0) ② 어긋난 팩만 복원(데몬 정지 1회 ·
    /// 사용자 파일·상태 폴더·app-notify.* 무접촉) ③ 옛 시도 스냅샷은 원천 아님 ④ 정지 실패 = 복원 0.
    #[test]
    fn reconstruct_compares_then_restores_only_mismatched_pack() {
        let d = std::env::temp_dir().join(format!("cys-u2-recon-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&d);
        let (upd, root) = (d.join("update"), d.join("cys"));
        for (p, b) in [("pack/lib/x.py", "v1"), ("local/me.md", "mine"), ("update/app-notify.json", "N0"), ("update/app-notify.lock", "L0")] {
            std::fs::create_dir_all(root.join(p).parent().unwrap()).unwrap();
            std::fs::write(root.join(p), b).unwrap();
        }
        std::fs::create_dir_all(&upd).unwrap();
        super::super::quiesce::write_json(&upd, "attempt.json", &json!({"txn_id": "tnow"})).unwrap();
        let snap = super::super::snapshot::backup_root(&upd).join("8-tnow").join("cys");
        super::super::snapshot::take(&root, &snap, &RealOps::cys_filter).unwrap();
        // 옛 시도 스냅샷(다른 내용) — 원천이 되면 안 된다
        std::fs::write(root.join("pack/lib/x.py"), "ancient").unwrap();
        super::super::snapshot::take(&root, &super::super::snapshot::backup_root(&upd).join("8-told").join("cys"), &RealOps::cys_filter).unwrap();
        std::fs::write(root.join("pack/lib/x.py"), "v1").unwrap();
        let mut stops = 0;
        // ① 일치 = 무변경 · 정지 0
        assert_eq!(reconstruct_trees(&upd, &root, 8, &mut || { stops += 1; Ok(()) }).unwrap(), false);
        assert_eq!(stops, 0);
        // ② 팩만 어긋남 + 앱 알림 장부 변화 → 팩만 복원 · 장부 무접촉
        std::fs::write(root.join("pack/lib/x.py"), "v2-new").unwrap();
        std::fs::write(root.join("update/app-notify.json"), "N1").unwrap();
        std::fs::write(root.join("update/app-notify.lock"), "L1").unwrap();
        assert_eq!(reconstruct_trees(&upd, &root, 8, &mut || { stops += 1; Ok(()) }).unwrap(), true);
        assert_eq!(stops, 1, "복원 전 데몬 정지 1회");
        assert_eq!(std::fs::read_to_string(root.join("pack/lib/x.py")).unwrap(), "v1", "이번 시도 스냅샷(옛 시도 아님)");
        assert_eq!(std::fs::read_to_string(root.join("local/me.md")).unwrap(), "mine");
        assert_eq!(std::fs::read_to_string(root.join("update/app-notify.json")).unwrap(), "N1", "app-notify 무접촉");
        assert_eq!(std::fs::read_to_string(root.join("update/app-notify.lock")).unwrap(), "L1", ".lock 복원 금지");
        // ④ 정지 실패 = 복원 0
        std::fs::write(root.join("pack/lib/x.py"), "v3").unwrap();
        assert!(reconstruct_trees(&upd, &root, 8, &mut || Err(fail(ErrCode::RotateFailed, "S7", "x"))).is_err());
        assert_eq!(std::fs::read_to_string(root.join("pack/lib/x.py")).unwrap(), "v3", "정지 못 하면 덮지 않음");
        let _ = std::fs::remove_dir_all(&d);
    }

    /// ★2판 C13: 재구성 복원 원천 = 그 판의 스냅샷 중 두 뿌리가 검증되는 최신 것(손상·다른 판 제외).
    #[test]
    fn latest_verified_snapshot_skips_corrupt_and_other_seq() {
        let d = std::env::temp_dir().join(format!("cys-u2-lvs-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&d);
        let src = d.join("src");
        std::fs::create_dir_all(&src).unwrap();
        std::fs::write(src.join("a"), "1").unwrap();
        let root = super::super::snapshot::backup_root(&d);
        for name in ["8-old", "8-new", "9-x"] {
            for r in ["state", "cys"] {
                super::super::snapshot::take(&src, &root.join(name).join(r), &|_| true).unwrap();
            }
            std::thread::sleep(std::time::Duration::from_millis(20));
        }
        std::fs::write(root.join("8-new/cys/files/a"), "X").unwrap(); // 최신 것 손상
        assert_eq!(latest_verified_snapshot(&d, 8), Some(root.join("8-old")));
        assert_eq!(latest_verified_snapshot(&d, 9), Some(root.join("9-x")));
        assert_eq!(latest_verified_snapshot(&d, 7), None);
        let _ = std::fs::remove_dir_all(&d);
    }

    /// ★3판 N2: 부서 데몬처럼 cysd 이름 프로세스가 여럿이어도 V2 = 본부 소켓이 밝힌 pid 1개만 센다 · 죽은 pid·다른 이름·응답 없음 = 0.
    #[cfg(unix)]
    #[test]
    fn v2_counts_only_the_hq_daemon_identified_by_socket() {
        let d = std::env::temp_dir().join(format!("cys-u2-v2-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&d);
        std::fs::create_dir_all(&d).unwrap();
        let fake = d.join("cysd");
        std::fs::copy("/bin/sleep", &fake).unwrap();
        let mut kids: Vec<std::process::Child> = (0..2).map(|_| std::process::Command::new(&fake).arg("30").spawn().unwrap()).collect();
        // 부하 중엔 exec 직후 이름이 늦게 보인다(전수 병렬 1회 적색) — 3초까지 기다린다
        let mut n = 0;
        for _ in 0..60 {
            n = hq_daemon_count(&json!({"daemon_pid": kids[0].id()}));
            if n == 1 {
                break;
            }
            std::thread::sleep(std::time::Duration::from_millis(50));
        }
        assert_eq!(n, 1, "가짜 cysd 2개 있어도 본부 1");
        assert_eq!(hq_daemon_count(&json!({})), 0, "응답 없음");
        let sleeper = std::process::Command::new("/bin/sleep").arg("30").spawn().unwrap();
        assert_eq!(hq_daemon_count(&json!({"daemon_pid": sleeper.id()})), 0, "이름 cysd 아님");
        for k in kids.iter_mut().chain(std::iter::once(&mut { sleeper })) {
            let _ = k.kill();
            let _ = k.wait();
        }
        assert_eq!(hq_daemon_count(&json!({"daemon_pid": kids[1].id()})), 0, "죽은 pid");
        let _ = std::fs::remove_dir_all(&d);
    }

    /// ★2판 C10: installers/<seq>/ = 쓸 때마다 재검증 — U 서명 본문 · seq · 설치기 sha256 = 본문 행 · A2 서명. 임의 파일·변조 = 거부.
    #[test]
    fn installer_dir_is_reverified_on_every_use() {
        use crate::update::feed::fixture::body_json;
        use crate::update::keys::testkit::Keys;
        let k = Keys::new();
        let kr = k.keyring();
        let d = std::env::temp_dir().join(format!("cys-u2-inst-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&d);
        std::fs::create_dir_all(&d).unwrap();
        let setup = b"MZ-setup".to_vec();
        let mut body = body_json(&k, 8);
        for a in body["assets"].as_object_mut().unwrap().values_mut() {
            a["sha256"] = json!(crate::update::feed::sha256_hex(&setup));
        }
        let bb = body.to_string().into_bytes();
        let sig = k.u.sign(&bb);
        std::fs::write(d.join(SETUP), &setup).unwrap();
        std::fs::write(d.join(SETUP_SIG), k.a2.sign(&setup)).unwrap();
        let v = verify_installer_dir_with(&d, 8, true, &bb, &sig, &kr).unwrap();
        assert_eq!(v.setup_sha256.as_deref(), Some(crate::update::feed::sha256_hex(&setup).as_str()));
        assert!(verify_installer_dir_with(&d, 9, true, &bb, &sig, &kr).unwrap_err().contains("seq"), "폴더 seq 다름");
        assert!(verify_installer_dir_with(&d, 8, true, &bb, &k.f.sign(&bb), &kr).is_err(), "U 아닌 키 서명");
        std::fs::write(d.join(SETUP), b"MZ-evil").unwrap();
        assert!(verify_installer_dir_with(&d, 8, true, &bb, &sig, &kr).unwrap_err().contains("sha256"), "임의 설치기");
        std::fs::write(d.join(SETUP), &setup).unwrap();
        std::fs::write(d.join(SETUP_SIG), k.u.sign(&setup)).unwrap();
        assert!(verify_installer_dir_with(&d, 8, true, &bb, &sig, &kr).unwrap_err().contains("A2"), "A2 아닌 서명");
        assert!(verify_installer_dir_with(&d, 8, false, &bb, &sig, &kr).is_ok(), "본문만(맥·매니페스트) = 설치기 무관");
        let _ = std::fs::remove_dir_all(&d);
    }

    #[test]
    fn tree_sha_changes_with_content_and_links() {
        let d = std::env::temp_dir().join(format!("cys-u2-tree-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&d);
        std::fs::create_dir_all(d.join("a")).unwrap();
        std::fs::write(d.join("a/f"), "1").unwrap();
        let h1 = tree_sha(&d).unwrap();
        std::fs::write(d.join("a/f"), "2").unwrap();
        let h2 = tree_sha(&d).unwrap();
        assert_ne!(h1, h2);
        #[cfg(unix)]
        {
            std::os::unix::fs::symlink("f", d.join("a/l")).unwrap();
            assert_ne!(tree_sha(&d).unwrap(), h2);
        }
    }
}
