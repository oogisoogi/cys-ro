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
}

pub const CANDIDATE_FILE: &str = "candidate.json";

impl Candidate {
    pub fn from_outcome(o: &super::feed::FeedOutcome) -> Option<Candidate> {
        Some(Candidate { asset: o.asset.clone()?, version: o.version.clone().unwrap_or_default(), release_seq: o.release_seq?, installed_revoked: o.installed_revoked, notes_ko: o.notes_ko.clone() })
    }
}

pub struct RealOps {
    pub env: Env,
    pub token: String,
    /// S0 후보(행 포함) — 러너 시작 전에 호출자가 채운다(복구기 = `candidate.json`).
    pub cand: Candidate,
    pub old_version: String,
    q1: Option<super::quiesce::Token>,
    b0: Option<Baseline>,
}

fn fail(code: ErrCode, step: &str, d: impl Into<String>) -> Fail {
    Fail::new(code, step, d)
}

impl RealOps {
    pub fn new(env: Env, token: String, cand: Candidate, old_version: String) -> RealOps {
        RealOps { env, token, cand, old_version, q1: None, b0: None }
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

    /// 자식 명령(위임 토큰 동반).
    fn child(&self, exe: &Path, args: &[&str]) -> Result<std::process::Output, Fail> {
        let mut c = crate::hidden_command(exe);
        c.args(args).env(super::lock::ENV_TXN, &self.token).stdin(std::process::Stdio::null());
        c.output().map_err(|e| fail(ErrCode::RotateFailed, "child", format!("{}: {e}", exe.display())))
    }

    fn rotate(&self, exe: &Path, stop_only: bool) -> Step {
        let mut args = vec!["rotate", "--skip-drain", "--txn", self.token.as_str()];
        if stop_only {
            args.push("--stop-only");
        }
        let o = self.child(exe, &args)?;
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

    fn doctor_fail(&self, exe: &Path) -> std::collections::BTreeSet<String> {
        self.child(exe, &["doctor", "--json"])
            .ok()
            .and_then(|o| serde_json::from_slice::<Value>(&o.stdout).ok())
            .map(|v| doctor_fails(&v))
            .unwrap_or_default()
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
                .map(|s| SeatKey {
                    surface_uuid: format!("role:{}", s["role"].as_str().unwrap_or("")),
                    role: s["role"].as_str().unwrap_or("").to_string(),
                    dept: s["agent"].as_str().unwrap_or("").to_string(),
                    session_id: s["registered_session_id"].as_str().unwrap_or("").to_string(),
                })
                .collect()
        })
        .unwrap_or_default()
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
                let ok = kr.key_ids().iter().any(|k| kr.verify(super::keys::Purpose::WinAsset, k, &bytes, &sig, now).is_ok());
                if !ok {
                    return Err(fail(ErrCode::WinA2SigBad, "S2", "A2 서명 불일치"));
                }
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
            // 롤백 자산(N7 · §3-7 ②): 설치판 본문·설치기가 installers\<seq>\ 에 있어야 한다(검증은 확보 단계 몫 — 없으면 보류).
            let dir = self.installers_dir(j.from_release_seq);
            let inst = dir.join("setup.exe");
            let (sha, _) = super::snapshot::sha256_file(&inst).map_err(|_| fail(ErrCode::NoRollbackAsset, "S8", "설치판 설치기 없음"))?;
            j.prev_installer = Some(PrevInstaller { path: inst.to_string_lossy().to_string(), sha256: sha, release_seq: j.from_release_seq });
        }
        j.snapshot_dir = root.to_string_lossy().to_string();
        j.snapshot_manifest_sha256 = shas.join(",");
        // N7 「직전 실측 백업량」(MA3) — 다음 틱의 공간식 재료.
        let bytes: u64 = ["state", "cys"]
            .iter()
            .filter_map(|n| std::fs::read_to_string(root.join(n).join(super::snapshot::MANIFEST_FILE)).ok())
            .filter_map(|t| super::snapshot::parse_manifest(&t).ok())
            .map(|m| m.values().map(|(_, n)| *n).sum::<u64>())
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
            Os::Mac => super::mac::judge_canonical(super::mac::bundle_ident(&self.env.canonical_app).as_ref(), &new, &old),
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
            (self.env.old_cys.clone(), Expect { release_seq: o.release_seq, build_id: o.build_id, target: o.target, ..Default::default() })
        } else {
            let a = self.asset()?;
            let bp = a.bundled_pack.as_ref().map(|p| PackId { version: p.version.clone(), digest: p.digest.clone() }).unwrap_or_default();
            (self.new_cys(), Expect { release_seq: a.release_seq, build_id: a.build_id.clone(), target: a.target.clone(), bundled_pack: bp, ..Default::default() })
        };
        let ident = super::mac::bundle_ident_exe(&exe).unwrap_or_default();
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
            daemon_build_id: identify["build_id"].as_str().unwrap_or(&ident.build_id).to_string(),
            platform_mark: String::new(),
            ping_ok_streak: ping,
            cysd_procs: 1,
            seats: self.seats()?,
            drain_seats: None,
            restore_rc: 0,
            doctor_fail: self.doctor_fail(&exe),
            user: verify::collect_user_tree(&self.env.cys_root).map_err(|e| fail(ErrCode::VerifyFailed, "V5", e))?,
            forbidden_jobs: vec![],
            features: b0.features.clone(),
            merge_pending_new: vec![],
            pack: if rollback { self.pack_id() } else { exp.bundled_pack.clone() },
            hold_last_seq: super::hold::last_seq_readonly(&self.env.update_dir).unwrap_or(0),
            hold_delivered_seq: 0,
            hold_lost: 0,
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
            super::snapshot::verify(&root.join(name)).map_err(|e| fail(ErrCode::RollbackBlocked, "RB_PREPARED", e))?;
        }
        Ok(())
    }

    fn rb_swap(&mut self, j: &Journal) -> Step {
        let found = self.canonical(j);
        match self.env.os {
            Os::Mac => {
                let prev = j
                    .prev_bundle
                    .as_ref()
                    .map(|p| PathBuf::from(&p.path))
                    .ok_or_else(|| fail(ErrCode::RecoverAnomaly, "RB_SWAPPED", "prev_bundle 없음"))?;
                super::mac::rb_swap(&self.env.canonical_app, &prev, found)
            }
            Os::Win => {
                if found == Canon::Old && self.old_payload_ok(j) {
                    return Ok(());
                }
                let pi = j.prev_installer.as_ref().ok_or_else(|| fail(ErrCode::NoRollbackAsset, "RB_SWAPPED", "설치판 설치기 기록 없음"))?;
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
        let q = super::snapshot::quarantine_dir(&self.env.update_dir, &j.txn_id);
        let payload: std::collections::BTreeSet<String> = self
            .asset()
            .ok()
            .and_then(|a| a.payload_manifest.as_ref())
            .map(|m| m.iter().map(|e| super::payload::norm(&e.path)).collect())
            .unwrap_or_default();
        let st_prot = move |rel: &str| super::snapshot::is_excluded(rel) || payload.contains(&super::payload::norm(rel));
        super::snapshot::restore(&self.env.daemon_state_dir, &root.join("state"), &q.join("state"), &st_prot)
            .map_err(|e| fail(ErrCode::RollbackBlocked, "RB_RESTORED", e))?;
        let cys_prot = |rel: &str| !RealOps::cys_filter(rel);
        super::snapshot::restore(&self.env.cys_root, &root.join("cys"), &q.join("cys"), &cys_prot)
            .map_err(|e| fail(ErrCode::RollbackBlocked, "RB_RESTORED", e))?;
        Ok(())
    }

    fn recover_pack(&mut self) -> Step {
        crate::pack::recover_pack_journal().map(|_| ()).map_err(|e| fail(ErrCode::RollbackFailed, "PACK", e))
    }

    fn reconstruct(&mut self) -> Step {
        // §3-11 저널 손상 재구성: 정식 자리 실물이 설치판(옛) 또는 후보(새) 중 정확히 하나와 같으면 확정.
        let old = self.expect_old();
        let new = self.expect_new().ok();
        match self.env.os {
            Os::Mac => {
                let found = super::mac::bundle_ident(&self.env.canonical_app);
                match (&found, &new) {
                    (Some(f), _) if f == &old => Ok(()),
                    (Some(f), Some(n)) if f == n => Ok(()),
                    _ => Err(fail(ErrCode::JournalCorrupt, "reconstruct", "정식 자리 번들 = 어느 판과도 불일치")),
                }
            }
            Os::Win => {
                let older = load_installer_manifest(&self.installers_dir(old.release_seq));
                match older {
                    Some(m) if super::payload::verify_install(&self.env.install_dir, &m, None).ok() => Ok(()),
                    _ => Err(fail(ErrCode::JournalCorrupt, "reconstruct", "설치 폴더 = 수용 매니페스트 불일치")),
                }
            }
        }
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
pub fn load_installer_manifest(dir: &Path) -> Option<Vec<super::feed::PayloadEntry>> {
    let v: Value = serde_json::from_slice(&std::fs::read(dir.join("release.json")).ok()?).ok()?;
    let rows = v.get("assets").and_then(Value::as_array).cloned().or_else(|| v.get("platforms").and_then(Value::as_object).map(|o| o.values().cloned().collect()))?;
    rows.into_iter()
        .find(|r| r.get("target").and_then(Value::as_str) == Some(super::buildinfo::TARGET) || r.get("payload_manifest").is_some())
        .and_then(|r| serde_json::from_value(r.get("payload_manifest")?.clone()).ok())
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
        std::os::unix::fs::symlink("f", d.join("a/l")).unwrap();
        assert_ne!(tree_sha(&d).unwrap(), h2);
    }
}
