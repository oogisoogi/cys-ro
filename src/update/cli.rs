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
            let dir = buildinfo::state_dir();
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
            let installed = match (installed_release_seq, component.as_str()) {
                (Some(n), _) => n,
                (None, "cysr") => buildinfo::release_seq(),
                (None, _) => return undetermined("--installed-release-seq 필요".into()),
            };
            let target = target.unwrap_or_else(|| if component == "cysr" { buildinfo::TARGET.into() } else { "any".into() });
            let dir = buildinfo::state_dir();
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
                keyring: &keyring,
                installed_release_seq: installed,
                target: &target,
                rollout_bucket: bucket,
            };
            let o = feed::verify_feed(&inp);
            let signed_ok = !matches!(o.verdict, Verdict::Reject | Verdict::Undetermined);
            let mut v = o.to_json();
            if record && signed_ok {
                let rec = (|| -> Result<(), String> {
                    check::bump_trusted(&dir, o.revocations.as_ref().map(|r| r.rev), o.trusted_signed_at)?;
                    if o.verdict == Verdict::Uptodate {
                        let a = AcceptedFeed {
                            feed_rev: o.feed_rev.unwrap_or(0),
                            release_seq: installed,
                            signed_at: o.envelope_signed_at.unwrap_or(0),
                            at: t_now,
                        };
                        feed::write_accepted(&acc_path, &a)?;
                    }
                    Ok(())
                })();
                v["recorded"] = serde_json::json!(rec.is_ok());
                if let Err(e) = rec {
                    v["record_error"] = serde_json::json!(e);
                }
            }
            print(json, &v, &format!("{} {} [{}] {}", o.verdict.as_str(), o.code, o.step, o.detail));
            o.verdict.rc()
        }
    }
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

    /// `cys update-verify` 종단(시험 키 · 격리 상태 폴더 · 디버그 시험 키링 env): 판정·rc·`--record` 앵커·후퇴 거부.
    #[test]
    fn update_verify_end_to_end_with_record() {
        use super::super::feed::fixture::*;
        use super::super::keys::testkit::Keys;
        let _k = super::super::TEST_ENV_LOCK.lock().unwrap_or_else(|e| e.into_inner());
        let d = std::env::temp_dir().join(format!("cys-u1-cli-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&d);
        std::fs::create_dir_all(d.join("st")).unwrap();
        let k = Keys::new();
        std::fs::write(d.join("kr.json"), k.keyring_json()).unwrap();
        let _e = (
            crate::pack::EnvGuard::set("CYS_UPDATE_STATE_DIR", d.join("st")),
            crate::pack::EnvGuard::set("CYS_UPDATE_TEST_KEYRING", d.join("kr.json")),
            crate::pack::EnvGuard::set("CYS_UPDATE_NOW", NOW.to_string()),
        );
        let write = |feed_rev: u64, seq: u64, rev: u64| {
            let s = sign_all(&k, &envelope_json(&k, &body_json(&k, seq), feed_rev), &revocations_json(&k, rev, serde_json::json!([])));
            std::fs::write(d.join("e.json"), &s.env).unwrap();
            std::fs::write(d.join("e.sig"), &s.env_sig).unwrap();
            std::fs::write(d.join("r.json"), &s.rev).unwrap();
            std::fs::write(d.join("r.sig"), &s.rev_sig).unwrap();
        };
        let run_v = |installed: u64, record: bool| {
            run(
                UpdCmd::UpdateVerify {
                    component: "cysr".into(),
                    channel: "stable".into(),
                    envelope: d.join("e.json"),
                    sig: d.join("e.sig"),
                    revocations: d.join("r.json"),
                    revocations_sig: d.join("r.sig"),
                    installed_release_seq: Some(installed),
                    target: Some("macos-arm64".into()),
                    record,
                    json: true,
                },
                &check::Hooks { seats: &|| None, pending_approvals: &|| None },
            )
        };
        write(5, 9, 2);
        assert_eq!(run_v(8, false), 0, "apply");
        assert!(!d.join("st/trusted.json").exists(), "--record 없으면 쓰기 0");
        assert_eq!(run_v(9, true), 0, "uptodate + record");
        let acc = feed::read_accepted(&check::accepted_path(&d.join("st"), "cysr", "stable")).unwrap().unwrap();
        assert_eq!((acc.feed_rev, acc.release_seq), (5, 9));
        let t = check::read_trusted(&d.join("st")).unwrap();
        assert_eq!(t.revocations_rev, Some(2));
        // 순번 역행(feed_rev 4 < 수용 5) = 거부 rc 2 · 폐기문 rev 후퇴(1 < 2) = 거부 rc 2
        write(4, 9, 2);
        assert_eq!(run_v(8, true), 2);
        write(6, 10, 1);
        assert_eq!(run_v(9, true), 2);
        // 서명 깨짐 = rc 2
        write(6, 10, 2);
        let mut e = std::fs::read(d.join("e.json")).unwrap();
        let i = e.len() / 2;
        e[i] ^= 1;
        std::fs::write(d.join("e.json"), e).unwrap();
        assert_eq!(run_v(9, false), 2);
        // 시계 의심(신뢰 시각보다 1시간 과거) = rc 3
        write(6, 10, 2);
        check::bump_trusted(&d.join("st"), None, Some(NOW + 3600)).unwrap();
        assert_eq!(run_v(9, false), 3);
        let _ = std::fs::remove_dir_all(&d);
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
