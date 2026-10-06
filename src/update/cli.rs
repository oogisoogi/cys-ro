//! 갱신 CLI 3동사 — `cys update-verify` · `cys build-info` · `cys self-update --check [--json]`(설계 AUTO-UPDATE-118 §6-2 · §4-2 · §8 U1).
//!
//! ★최상위 `Command` 열거형에 동사를 더하지 않는다: 최상위 clap 파생 코드가 커지면 원작자 j3 시험이 기본 2MB 시험 스레드에서
//! 스택 넘침이 난다(1.1.8 W1 실측 · 변형 1개로도 재현). 그래서 `main` 이 `Cli::parse()` **앞에서** 이 모듈의 [`dispatch`] 를
//! 먼저 부르고, 첫 동사가 셋 중 하나면 여기 따로 둔 작은 파서로 처리한다(나머지는 종전 그대로). 동사 철자는 설계 그대로라
//! T3(파이썬)가 `cys update-verify …` 로 부르는 계약이 같다.

use super::buildinfo;
use super::check;
use super::clock;
use super::feed::{self, AcceptedFeed, FeedInput, Verdict};
use super::keys::UpdateKeyring;
use clap::{Parser, Subcommand};
use std::ffi::OsString;
use std::path::PathBuf;

pub const VERBS: [&str; 3] = ["update-verify", "build-info", "self-update"];

#[derive(Parser, Debug)]
#[command(name = "cys", bin_name = "cysr", disable_version_flag = true)]
struct UpdCli {
    #[command(subcommand)]
    cmd: UpdCmd,
}

#[derive(Subcommand, Debug)]
enum UpdCmd {
    /// 피드 두 겹(봉투 F · 본문 U) + 폐기문(R) 검증 — 판정 JSON(rc 0 판정 · 2 거부 · 3 판정 불가). 검증 함수는 이것 하나뿐.
    #[command(name = "update-verify")]
    UpdateVerify {
        #[arg(long)]
        component: String,
        #[arg(long)]
        channel: String,
        #[arg(long)]
        envelope: PathBuf,
        #[arg(long)]
        sig: PathBuf,
        #[arg(long)]
        revocations: PathBuf,
        #[arg(long = "revocations-sig")]
        revocations_sig: PathBuf,
        /// 설치판 release_seq(cysr = 이 바이너리 내장값이 기본 · agora-client = 필수)
        #[arg(long = "installed-release-seq")]
        installed_release_seq: Option<u64>,
        /// 기판 행(기본 = 이 바이너리 기판 · agora-client = any)
        #[arg(long)]
        target: Option<String>,
        /// 서명이 전부 맞으면 단조 앵커(폐기문 rev · 신뢰 시각)를 올리고, uptodate 면 수용 기록 feed_rev 를 올린다
        #[arg(long)]
        record: bool,
        /// 출발 seq 열거(발행 게이트·refresh-feed): 본문이 허용하는 출발 seq(`max(min_from,1)` ~ 후보) 각각을 판정한다 — 설치판
        /// 주장 없이(가짜 0 금지). `--installed-release-seq`·`--record` 와 함께 못 쓴다.
        #[arg(long = "enumerate-installed")]
        enumerate_installed: bool,
        #[arg(long)]
        json: bool,
    },
    /// 이 바이너리의 빌드 신원 {version, build_id, release_seq, target, features, bundled_pack, keyring_ids}
    #[command(name = "build-info")]
    BuildInfo {
        #[arg(long)]
        json: bool,
    },
    /// 자동 갱신 — 이 판(1.1.8 U1)은 `--check`(판정만 · 교체 0)뿐이다
    #[command(name = "self-update")]
    SelfUpdate {
        #[arg(long)]
        check: bool,
        #[arg(long)]
        json: bool,
    },
}

/// argv 에서 전역 `--socket <v>`/`--socket=<v>` 를 걷어 내고 첫 동사를 찾는다 — 갱신 동사가 아니면 None.
fn split_args(args: &[OsString]) -> Option<(Vec<OsString>, Option<OsString>)> {
    let mut out = vec![args.first().cloned().unwrap_or_else(|| "cys".into())];
    let mut socket = None;
    let mut i = 1;
    let mut verb_seen = false;
    while i < args.len() {
        let a = &args[i];
        let s = a.to_string_lossy();
        if !verb_seen && s == "--socket" {
            socket = args.get(i + 1).cloned();
            i += 2;
            continue;
        }
        if !verb_seen {
            if let Some(v) = s.strip_prefix("--socket=") {
                socket = Some(v.into());
                i += 1;
                continue;
            }
            if !VERBS.contains(&s.as_ref()) {
                return None;
            }
            verb_seen = true;
        }
        out.push(a.clone());
        i += 1;
    }
    verb_seen.then_some((out, socket))
}

/// 갱신 동사 파서의 clap 정의 — `cys actions` 카탈로그가 최상위 정의와 함께 싣는다(1R MINOR).
pub fn command() -> clap::Command {
    <UpdCli as clap::CommandFactory>::command()
}

/// 첫 동사가 갱신 동사인가(전역 `--socket` 건너뜀).
pub fn claims(args: &[OsString]) -> bool {
    split_args(args).is_some()
}

/// 첫 동사가 갱신 동사면 처리하고 종료 코드를 돌려준다. 아니면 None(종전 CLI 로).
pub fn dispatch(args: &[OsString], hooks: &check::Hooks) -> Option<i32> {
    let (argv, socket) = split_args(args)?;
    if let Some(s) = socket {
        std::env::set_var(crate::ENV_SOCKET, s);
    }
    let cli = match UpdCli::try_parse_from(&argv) {
        Ok(c) => c,
        Err(e) => {
            let _ = e.print();
            return Some(if e.use_stderr() { 2 } else { 0 });
        }
    };
    Some(run(cli.cmd, hooks))
}

fn now() -> i64 {
    // 시험·T3 하네스용 시각 고정 — 디버그 빌드에서만(출시 빌드 = 벽시계).
    if cfg!(debug_assertions) {
        if let Some(t) = std::env::var("CYS_UPDATE_NOW").ok().and_then(|v| v.parse().ok()) {
            return t;
        }
    }
    clock::wall_now()
}

fn print(json: bool, v: &serde_json::Value, line: &str) {
    if json {
        println!("{v}");
    } else {
        println!("{line}");
    }
}

fn run(cmd: UpdCmd, hooks: &check::Hooks) -> i32 {
    match cmd {
        UpdCmd::BuildInfo { json } => {
            let b = buildinfo::build_info();
            let v = serde_json::to_value(&b).unwrap_or_default();
            print(json, &v, &format!("{} build_id={} release_seq={} target={}", b.version, b.build_id, b.release_seq, b.target));
            0
        }
        UpdCmd::SelfUpdate { check: true, json } => {
            // ★1R B1: 운영 상태 폴더를 못 정하면 판정 불가(rc 3 · `.` 후퇴 0).
            let dir = match buildinfo::state_dir() {
                Ok(d) => d,
                Err(e) => {
                    let v = serde_json::json!({"decision": "undetermined", "code": "update.verify_failed", "step": "state_dir", "detail": e});
                    print(json, &v, &format!("decision=undetermined {e}"));
                    return 3;
                }
            };
            let (v, rc) = check::run_check(&dir, &crate::pack::pack_dir(), hooks);
            let hold = v["gates"]["first_hold"]["id"].as_str().unwrap_or("-").to_string();
            print(json, &v, &format!("decision={} feed={} first_hold={hold} (교체 0 · 판정만)", v["decision"], v["feed"]["verdict"]));
            rc
        }
        UpdCmd::SelfUpdate { check: false, .. } => {
            eprintln!("cys self-update: 이 판은 --check(판정만)만 있습니다 — 교체·자동 실행은 다음 판(U2)에서 들어옵니다.");
            2
        }
        UpdCmd::UpdateVerify {
            component,
            channel,
            envelope,
            sig,
            revocations,
            revocations_sig,
            installed_release_seq,
            target,
            record,
            enumerate_installed,
            json,
        } => {
            let undetermined = |detail: String| {
                let v = serde_json::json!({"verdict": "undetermined", "code": "update.verify_failed", "step": "input", "detail": detail});
                print(json, &v, &format!("undetermined update.verify_failed {detail}"));
                3
            };
            let read = |p: &PathBuf| std::fs::read(p).map_err(|e| format!("{}: {e}", p.display()));
            let (env, env_sig, rev, rev_sig) = match (read(&envelope), read(&sig), read(&revocations), read(&revocations_sig)) {
                (Ok(a), Ok(b), Ok(c), Ok(d)) => (a, b, c, d),
                (Err(e), ..) | (_, Err(e), ..) | (_, _, Err(e), _) | (_, _, _, Err(e)) => return undetermined(e),
            };
            if enumerate_installed && (installed_release_seq.is_some() || record) {
                let detail = "--enumerate-installed 는 --installed-release-seq·--record 와 함께 못 쓴다";
                let v = serde_json::json!({"verdict": "reject", "code": "update.verify_failed", "step": "input", "detail": detail});
                print(json, &v, &format!("reject update.verify_failed {detail}"));
                return 2;
            }
            // ★1R B4: cysr 의 설치판 seq 는 이 바이너리 내장값뿐 — 호출자 주장(낮춰 부른 seq 로 다운그레이드 판정)은 거부(rc 2).
            //   외부 seq 는 바이너리 밖에 사는 agora-client 만 받는다.
            let installed = match (installed_release_seq, component.as_str()) {
                (Some(_), "cysr") if !super::mutant("B4") => {
                    let detail = "cysr 은 --installed-release-seq 를 받지 않는다(내장 release_seq 만)";
                    let v = serde_json::json!({"verdict": "reject", "code": "update.verify_failed", "step": "input", "detail": detail});
                    print(json, &v, &format!("reject update.verify_failed {detail}"));
                    return 2;
                }
                (Some(n), _) => n,
                // 열거 모드는 이 값을 쓰지 않는다(`verify_feed_enumerate` 가 출발 seq 를 본문에서 정한다).
                (None, _) if enumerate_installed => 0,
                (None, "cysr") => buildinfo::release_seq(),
                (None, _) => return undetermined("--installed-release-seq 필요".into()),
            };
            let target = target.unwrap_or_else(|| if component == "cysr" { buildinfo::TARGET.into() } else { "any".into() });
            let dir = match buildinfo::state_dir() {
                Ok(d) => d,
                Err(e) => return undetermined(e),
            };
            let trusted = check::read_trusted(&dir);
            let (accepted_rev, last_trusted) = match &trusted {
                Ok(t) => (t.revocations_rev, t.last_trusted_time),
                Err(e) => return undetermined(e.clone()),
            };
            let acc_path = check::accepted_path(&dir, &component, &channel);
            let keyring = match UpdateKeyring::embedded() {
                Ok(k) => k,
                Err(e) => return undetermined(e),
            };
            let t_now = now();
            let bucket = buildinfo::read_install_id(&dir).map(|id| feed::rollout_bucket(&id));
            let inp = FeedInput {
                component: &component,
                channel: &channel,
                envelope: &env,
                envelope_sig: &env_sig,
                revocations: &rev,
                revocations_sig: &rev_sig,
                now: t_now,
                clock_suspect: clock::clock_suspect(t_now, last_trusted, None),
                accepted: feed::read_accepted(&acc_path),
                accepted_rev,
                last_trusted_time: last_trusted,
                keyring: &keyring,
                installed_release_seq: installed,
                target: &target,
                rollout_bucket: bucket,
            };
            if enumerate_installed {
                return run_enumerate(&inp, json);
            }
            let o = feed::verify_feed(&inp);
            let mut v = o.to_json();
            let mut rc = o.verdict.rc();
            if record {
                // ★1R B3: R 검증을 통과한 폐기문은 **판정과 무관하게**(뒤 단계 거부·판정 불가여도) 원문·서명째 내구 기록하고 신뢰
                //   시각을 올린다. 수용 기록(feed_rev·봉투 sha256)은 uptodate 일 때만. 기록 실패 = rc 3(조용한 rc 0 금지).
                let strict = !super::mutant("B3r");
                let signed_ok = !matches!(o.verdict, Verdict::Reject | Verdict::Undetermined);
                let rec = (|| -> Result<bool, String> {
                    let mut wrote = false;
                    if let Some(r) = o.revocations.as_ref().filter(|_| strict || signed_ok) {
                        check::record_revocations(&dir, &rev, &rev_sig, r.rev, r.signed_at)?;
                        check::bump_trusted(&dir, o.trusted_signed_at)?;
                        wrote = true;
                    }
                    if o.verdict == Verdict::Uptodate {
                        let a = AcceptedFeed {
                            feed_rev: o.feed_rev.ok_or("uptodate 인데 feed_rev 없음")?,
                            envelope_sha256: o.envelope_sha256.clone().ok_or("uptodate 인데 봉투 sha256 없음")?,
                            feed_release_seq: o.release_seq.ok_or("uptodate 인데 release_seq 없음")?,
                            installed_release_seq: installed,
                            signed_at: o.envelope_signed_at.ok_or("uptodate 인데 봉투 signed_at 없음")?,
                            at: t_now,
                        };
                        feed::write_accepted(&acc_path, &a)?;
                        wrote = true;
                    }
                    Ok(wrote)
                })();
                v["recorded"] = serde_json::json!(matches!(rec, Ok(true)));
                if let Err(e) = rec {
                    v["record_error"] = serde_json::json!(e);
                    if strict {
                        rc = 3;
                    }
                }
            }
            print(json, &v, &format!("{} {} [{}] {}", o.verdict.as_str(), o.code, o.step, o.detail));
            rc
        }
    }
}

/// `--enumerate-installed` — 서명 단계 실패 = 그 결과·rc · 아니면 출발 seq 마다 판정을 싣고 rc = 가장 나쁜 것(판정 불가 3 > 거부 2 > 0).
/// 후보 직전까지의 출발 seq 가 하나도 없거나(min_from ≥ 후보) 후보 자신이 uptodate 가 아니면 거부(2).
fn run_enumerate(inp: &FeedInput, json: bool) -> i32 {
    let en = match feed::verify_feed_enumerate(inp) {
        Ok(en) => en,
        Err(o) => {
            let mut v = o.to_json();
            v["mode"] = "enumerate".into();
            print(json, &v, &format!("{} {} [{}] {}", o.verdict.as_str(), o.code, o.step, o.detail));
            return o.verdict.rc();
        }
    };
    let mut rc = 0;
    let mut problems = Vec::new();
    let mut rows = Vec::new();
    for (seq, o) in &en.results {
        rc = rc.max(o.verdict.rc());
        if *seq == en.release_seq && !matches!(o.verdict, Verdict::Uptodate | Verdict::InstalledRevoked) && o.verdict.rc() == 0 {
            rc = rc.max(2);
            problems.push(format!("후보 자신({seq}) 판정 {}", o.verdict.as_str()));
        }
        let mut row = o.to_json();
        row["installed_release_seq"] = (*seq).into();
        rows.push(row);
    }
    if !en.results.iter().any(|(s, _)| *s < en.release_seq) {
        rc = rc.max(2);
        problems.push(format!("허용 출발 seq 없음(min_from {} ≥ 후보 {})", en.min_from_release_seq, en.release_seq));
    }
    let verdict = match rc {
        0 => "ok",
        2 => "reject",
        _ => "undetermined",
    };
    let v = serde_json::json!({
        "mode": "enumerate",
        "verdict": verdict,
        "release_seq": en.release_seq,
        "min_from_release_seq": en.min_from_release_seq,
        "problems": problems,
        "results": rows,
    });
    let seqs: Vec<String> = en.results.iter().map(|(s, o)| format!("{s}={}", o.verdict.as_str())).collect();
    print(json, &v, &format!("enumerate {verdict} {}", seqs.join(" ")));
    rc
}

#[cfg(test)]
mod tests {
    use super::*;

    fn a(v: &[&str]) -> Vec<OsString> {
        v.iter().map(OsString::from).collect()
    }

    #[test]
    fn split_args_only_claims_update_verbs() {
        assert!(split_args(&a(&["cys", "send", "x"])).is_none());
        assert!(split_args(&a(&["cys"])).is_none());
        assert!(split_args(&a(&["cys", "--socket", "/s", "list"])).is_none());
        let (argv, s) = split_args(&a(&["cys", "--socket", "/s", "build-info", "--json"])).unwrap();
        assert_eq!(argv, a(&["cys", "build-info", "--json"]));
        assert_eq!(s, Some("/s".into()));
        let (argv, s) = split_args(&a(&["cys", "--socket=/t", "self-update", "--check"])).unwrap();
        assert_eq!(argv, a(&["cys", "self-update", "--check"]));
        assert_eq!(s, Some("/t".into()));
        // 동사 뒤의 --socket 은 인자 그대로(동사 파서가 거부)
        let (argv, _) = split_args(&a(&["cys", "update-verify", "--socket", "x"])).unwrap();
        assert_eq!(argv.len(), 4);
    }

    /// 아고라 클라이언트 피드(시험 키) — 외부 seq 를 받는 유일한 부품이라 `--record` 종단은 이것으로 돈다(1R B4).
    fn agora_signed(k: &super::super::keys::testkit::Keys, feed_rev: u64, seq: u64, rev: serde_json::Value) -> super::super::feed::fixture::Signed {
        use super::super::feed::fixture::*;
        let mut body = body_json(k, seq);
        body["component"] = "agora-client".into();
        body["requires"] = serde_json::json!({"min_cysr_release_seq": 1, "python": ">=3.9"});
        body["assets"] = serde_json::json!({"any": {
            "url": format!("https://jarvis.godmeyou.kr/install/agora-client-0.1.{seq}.zip"), "size": 10, "sha256": "ab".repeat(32),
            "max_unpacked": 100, "target": "any", "build_id": format!("agora{seq}"), "release_seq": seq, "features": []}});
        let mut env = envelope_json(k, &body, feed_rev);
        env["component"] = "agora-client".into();
        sign_all(k, &env, &rev)
    }

    struct E2e {
        d: PathBuf,
        _e: (crate::pack::EnvGuard, crate::pack::EnvGuard, crate::pack::EnvGuard),
        _k: std::sync::MutexGuard<'static, ()>,
    }

    impl E2e {
        fn new(tag: &str, k: &super::super::keys::testkit::Keys) -> E2e {
            use super::super::feed::fixture::NOW;
            let lock = super::super::TEST_ENV_LOCK.lock().unwrap_or_else(|e| e.into_inner());
            let d = std::env::temp_dir().join(format!("cys-u1-cli-{tag}-{}", std::process::id()));
            let _ = std::fs::remove_dir_all(&d);
            std::fs::create_dir_all(d.join("st")).unwrap();
            std::fs::write(d.join("kr.json"), k.keyring_json()).unwrap();
            let e = (
                crate::pack::EnvGuard::set("CYS_UPDATE_STATE_DIR", d.join("st")),
                crate::pack::EnvGuard::set("CYS_UPDATE_TEST_KEYRING", d.join("kr.json")),
                crate::pack::EnvGuard::set("CYS_UPDATE_NOW", NOW.to_string()),
            );
            E2e { d, _e: e, _k: lock }
        }
        fn put(&self, s: &super::super::feed::fixture::Signed) {
            std::fs::write(self.d.join("e.json"), &s.env).unwrap();
            std::fs::write(self.d.join("e.sig"), &s.env_sig).unwrap();
            std::fs::write(self.d.join("r.json"), &s.rev).unwrap();
            std::fs::write(self.d.join("r.sig"), &s.rev_sig).unwrap();
        }
        fn run(&self, component: &str, installed: Option<u64>, record: bool) -> i32 {
            self.run_mode(component, installed, record, false)
        }
        fn run_mode(&self, component: &str, installed: Option<u64>, record: bool, enumerate_installed: bool) -> i32 {
            run(
                UpdCmd::UpdateVerify {
                    component: component.into(),
                    channel: "stable".into(),
                    envelope: self.d.join("e.json"),
                    sig: self.d.join("e.sig"),
                    revocations: self.d.join("r.json"),
                    revocations_sig: self.d.join("r.sig"),
                    installed_release_seq: installed,
                    target: Some("macos-arm64".into()),
                    record,
                    enumerate_installed,
                    json: true,
                },
                &check::Hooks { seats: &|| None, pending_approvals: &|| None },
            )
        }
        fn st(&self) -> PathBuf {
            self.d.join("st")
        }
    }

    impl Drop for E2e {
        fn drop(&mut self) {
            let _ = std::fs::remove_dir_all(&self.d);
        }
    }

    /// `cys update-verify` 종단(시험 키 · 격리 상태 폴더 · 디버그 시험 키링 env): 판정·rc·`--record` 앵커·후퇴 거부.
    #[test]
    fn update_verify_end_to_end_with_record() {
        use super::super::feed::fixture::*;
        use super::super::keys::testkit::Keys;
        let k = Keys::new();
        let t = E2e::new("rec", &k);
        let rev = |n: u64| revocations_json(&k, n, serde_json::json!([]));
        t.put(&agora_signed(&k, 5, 9, rev(2)));
        assert_eq!(t.run("agora-client", Some(8), false), 0, "apply");
        assert!(!t.st().join("trusted.json").exists(), "--record 없으면 쓰기 0");
        assert_eq!(t.run("agora-client", Some(9), true), 0, "uptodate + record");
        let acc = feed::read_accepted(&check::accepted_path(&t.st(), "agora-client", "stable")).unwrap().unwrap();
        assert_eq!((acc.feed_rev, acc.feed_release_seq, acc.installed_release_seq), (5, 9, 9));
        assert_eq!(acc.envelope_sha256, feed::sha256_hex(&std::fs::read(t.d.join("e.json")).unwrap()));
        assert_eq!(check::read_trusted(&t.st()).unwrap().revocations_rev, Some(2));
        // 순번 역행(feed_rev 4 < 수용 5) = 거부 rc 2 · 폐기문 rev 후퇴(1 < 2) = 거부 rc 2
        t.put(&agora_signed(&k, 4, 9, rev(2)));
        assert_eq!(t.run("agora-client", Some(8), true), 2);
        t.put(&agora_signed(&k, 6, 10, rev(1)));
        assert_eq!(t.run("agora-client", Some(9), true), 2);
        // 서명 깨짐 = rc 2
        t.put(&agora_signed(&k, 6, 10, rev(2)));
        let mut e = std::fs::read(t.d.join("e.json")).unwrap();
        let i = e.len() / 2;
        e[i] ^= 1;
        std::fs::write(t.d.join("e.json"), e).unwrap();
        assert_eq!(t.run("agora-client", Some(9), false), 2);
        // 시계 의심(신뢰 시각보다 1시간 과거) = rc 3
        t.put(&agora_signed(&k, 6, 10, rev(2)));
        check::bump_trusted(&t.st(), Some(NOW + 3600)).unwrap();
        assert_eq!(t.run("agora-client", Some(9), false), 3);
    }

    /// ★1R B4 뮤테이션: cysr 에 `--installed-release-seq` = 거부 rc 2(내장 seq 만) — 가드를 끄면 낮춰 부른 seq 로 apply(rc 0).
    #[test]
    fn b4_cysr_refuses_caller_installed_seq() {
        use super::super::feed::fixture::*;
        use super::super::keys::testkit::Keys;
        let k = Keys::new();
        let t = E2e::new("b4", &k);
        let mut body = body_json(&k, 9);
        body["min_from_release_seq"] = 0.into(); // 로컬 빌드 내장 seq = 0 도 출발 판으로 허용
        t.put(&sign_all(&k, &envelope_json(&k, &body, 5), &revocations_json(&k, 1, serde_json::json!([]))));
        assert_eq!(t.run("cysr", Some(1), false), 2, "cysr 외부 seq 주장 = 거부");
        assert_eq!(t.run("cysr", None, false), 0, "내장 seq(로컬 빌드 0) 로는 판정");
    }

    /// ★1R B3(CLI) 뮤테이션: 후보가 거부(ⓙ 폐기)돼도 `--record` 는 R 검증을 통과한 새 폐기문을 원문째 기록한다 · 기록 실패 = rc 3.
    #[test]
    fn b3r_record_revocations_regardless_of_verdict() {
        use super::super::feed::fixture::*;
        use super::super::keys::testkit::Keys;
        let k = Keys::new();
        let t = E2e::new("b3r", &k);
        let revoked = serde_json::json!([{"component": "agora-client", "release_seq": 10, "severity": "advisory"}]);
        t.put(&agora_signed(&k, 5, 10, revocations_json(&k, 3, revoked)));
        assert_eq!(t.run("agora-client", Some(9), true), 2, "후보 10 폐기 = 거부");
        let tr = check::read_trusted(&t.st()).unwrap();
        assert_eq!(tr.revocations_rev, Some(3), "거부 판정이어도 새 폐기문 rev 기록");
        assert_eq!(std::fs::read(t.st().join(check::REV_COPY)).unwrap(), std::fs::read(t.d.join("r.json")).unwrap());
        // 같은 rev 3 인데 다른 원문 = 기록 실패 → rc 3(조용한 rc 0 금지)
        let other = serde_json::json!([{"component": "agora-client", "release_seq": 99}]);
        t.put(&agora_signed(&k, 6, 10, revocations_json(&k, 3, other)));
        assert_eq!(t.run("agora-client", Some(10), true), 3, "기록 실패 = 판정 불가");
    }

    /// ★U3 1R #11: `--enumerate-installed` — cysr 도 설치판 주장 없이 출발 seq 전부 판정(rc 0) · 설치 seq·record 동반 = 거부 ·
    /// 허용 출발 seq 없음(min_from ≥ 후보) = 거부 · 출발 seq 하나라도 거부 = 거부.
    #[test]
    fn enumerate_installed_cli_rc() {
        use super::super::feed::fixture::*;
        use super::super::keys::testkit::Keys;
        let k = Keys::new();
        let t = E2e::new("enum", &k);
        let put = |min_from: u64, revoked: serde_json::Value| {
            let mut b = body_json(&k, 9);
            b["min_from_release_seq"] = min_from.into();
            t.put(&sign_all(&k, &envelope_json(&k, &b, 5), &revocations_json(&k, 1, revoked)));
        };
        put(6, serde_json::json!([]));
        assert_eq!(t.run_mode("cysr", None, false, true), 0, "출발 6·7·8 apply + 9 uptodate");
        assert_eq!(t.run_mode("cysr", Some(8), false, true), 2, "설치 seq 동반");
        assert_eq!(t.run_mode("cysr", None, true, true), 2, "--record 동반");
        assert!(!t.st().join("trusted.json").exists(), "열거 모드는 쓰기 0");
        put(9, serde_json::json!([]));
        assert_eq!(t.run_mode("cysr", None, false, true), 2, "허용 출발 seq 없음");
        put(6, serde_json::json!([{"component": "cysr", "release_seq": 9}]));
        assert_eq!(t.run_mode("cysr", None, false, true), 2, "후보 폐기 = 모든 출발 seq 거부");
    }

    #[test]
    fn parser_accepts_design_spelling() {
        let c = UpdCli::try_parse_from(a(&["cys", "update-verify", "--component", "cysr", "--channel", "stable",
            "--envelope", "e", "--sig", "s", "--revocations", "r", "--revocations-sig", "rs", "--json"])).unwrap();
        assert!(matches!(c.cmd, UpdCmd::UpdateVerify { json: true, record: false, .. }));
        assert!(UpdCli::try_parse_from(a(&["cys", "self-update", "--check", "--json"])).is_ok());
        assert!(UpdCli::try_parse_from(a(&["cys", "update-verify", "--component", "cysr"])).is_err(), "필수 인자");
    }
}
