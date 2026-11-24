//! 「자동 보고」 켜기/끄기·첫 안내의 Rust 쪽(1.1.10 · TICKET=cysr-1110-counsel-off → 1.1.19 · cysr-1119-s10b AG4·AG5).
//!
//! ★(1.1.19 · DESIGN §8-3 AG4·AG5 · D-13) 상단 「상담소」 창의 글 목록(`counsel_room_list` = 아고라 클라이언트 `agora read`)·
//!   배지(`counsel_unread` = `mailbox/unread.json`)·「아고라」 보기 창(`open_agora_window`)은 화면과 함께 뺐다 — 핀·명부 판독·읽기 하네스 포함.
//!   (1.1.18 판 원문 = git `838f24421:src-tauri/src/counsel.rs`.)
//! ★앱은 아고라 설정을 직접 쓰지 않는다 — 팩 `javis_counsel.py` 의 앱 동사(`auto-status` · `auto-set on|off` · `notice-seen`)를 부르고
//!   그 JSON 한 줄만 받는다. 끄기 = 동봉 클라이언트 `agora counsel off` 그대로(1.1.18 set_auto).

use crate::{inject_runtime_path, BOOT_PY_CANDIDATES};
use cys::SpawnPolicy as _;
use serde_json::{json, Value};
use std::io::Read as _;
use std::path::{Path, PathBuf};

/// 아고라 설정 폴더 — 환경 `AGORA_CONFIG_DIR`(비어 있지 않으면) · 아니면 `<홈>/.config/agora`
/// (맥 `~/.config/agora` · 윈 `%USERPROFILE%\.config\agora` = 클라이언트 `participant.DEFAULT_DIR` 와 같은 식).
pub(crate) fn config_dir_from(env: Option<&str>, home: &Path) -> PathBuf {
    match env.map(str::trim) {
        Some(v) if !v.is_empty() => PathBuf::from(v),
        _ => home.join(".config").join("agora"),
    }
}

fn config_dir() -> PathBuf {
    config_dir_from(std::env::var("AGORA_CONFIG_DIR").ok().as_deref(), &cys::home_dir())
}

/// 격리 실행에서 지우는 환경(codex 1R BLOCK 2) — `-I` 가 PYTHON* 를 무시하지만 자식 env 에도 남기지 않는다(이중).
const PY_ENV_STRIP: &[&str] = &["PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP", "PYTHONUSERBASE", "PYTHONINSPECT", "PYTHONEXECUTABLE"];

// ── 「상담소 끄기/켜기」·첫 안내(1.1.10 · TICKET=cysr-1110-counsel-off) ─────────────────────────────
/// 팩 동사 1회 상한 — 팩 쪽 최악 = 설치 잠금 기다림 60초 + `agora counsel on|off` 30초 + 회수 10초.
const PACK_VERB_TIMEOUT: std::time::Duration = std::time::Duration::from_secs(150);
/// 팩 동사 출력 상한(정상 = JSON 한 줄 · 수십 바이트).
const PACK_VERB_STDOUT_CAP: u64 = 64 * 1024;

/// 팩 앱 동사 명령 조립 — 1.1.18 `read_command`(1.1.19 삭제)와 같던 격리(-I · -B · -X utf8 · PYTHON* 지움) · AGORA_CONFIG_DIR·CYS_PACK_DIR 를 못 박는다.
pub(crate) fn pack_verb_command(py: &str, pack: &Path, cfg: &Path, args: &[&str]) -> std::process::Command {
    let mut cmd = std::process::Command::new(py);
    inject_runtime_path(&mut cmd);
    for k in PY_ENV_STRIP {
        cmd.env_remove(k);
    }
    cmd.env("AGORA_CONFIG_DIR", cfg).env(cys::pack::ENV_PACK_DIR, pack);
    cmd.args(["-I", "-B", "-X", "utf8"]);
    cmd.arg(pack.join("bin").join("javis_counsel.py")).args(args);
    cmd.stdin(std::process::Stdio::null())
        .stdout(std::process::Stdio::piped())
        .stderr(std::process::Stdio::null());
    cmd.spawn_policy(cys::ChildLifetime::Attached);
    cmd
}

/// 팩 동사 1회 → 마지막 줄의 JSON 객체. 실패는 `{"error": …}`(UI 는 「확인하지 못했어요」로 그린다 · 끄기 단추는 그대로 둔다).
pub(crate) fn run_pack_verb(pack: &Path, cfg: &Path, args: &[&str]) -> Value {
    if !pack.join("bin").join("javis_counsel.py").is_file() {
        return json!({"error": "no-pack"});
    }
    for py in BOOT_PY_CANDIDATES {
        let mut child = match pack_verb_command(py, pack, cfg, args).spawn() {
            Ok(c) => c,
            Err(_) => continue,
        };
        let Some(out) = child.stdout.take() else { return json!({"error": "stdout"}) };
        let reader = std::thread::spawn(move || {
            let mut buf = Vec::new();
            let _ = out.take(PACK_VERB_STDOUT_CAP).read_to_end(&mut buf);
            buf
        });
        let deadline = std::time::Instant::now() + PACK_VERB_TIMEOUT;
        loop {
            match child.try_wait() {
                Ok(Some(_)) => break,
                Ok(None) if std::time::Instant::now() < deadline => std::thread::sleep(std::time::Duration::from_millis(50)),
                _ => {
                    let _ = child.kill();
                    let _ = child.wait();
                    return json!({"error": "timeout"});
                }
            }
        }
        let buf = reader.join().unwrap_or_default();
        let text = String::from_utf8_lossy(&buf);
        return text
            .lines()
            .rev()
            .find(|l| !l.trim().is_empty())
            .and_then(|l| serde_json::from_str::<Value>(l).ok())
            .filter(Value::is_object)
            .unwrap_or_else(|| json!({"error": "output"}));
    }
    json!({"error": "no-python"})
}

async fn pack_verb(args: Vec<&'static str>) -> Value {
    let (pack, cfg) = (cys::pack::pack_dir(), config_dir());
    tokio::task::spawn_blocking(move || run_pack_verb(&pack, &cfg, &args))
        .await
        .unwrap_or_else(|_| json!({"error": "join"}))
}

/// {auto, notice_seen, needs_notice} — 화면 설정 「자동 보고」 줄의 켜짐/꺼짐 · 첫 안내 창을 띄울지(1.1.19 · 옛 상담소 창 자리).
#[tauri::command]
pub(crate) async fn counsel_auto_status() -> Value {
    pack_verb(vec!["auto-status"]).await
}

/// 「자동 보고 끄기」(on=false) · 「자동 보고 켜기」(on=true)(1.1.18 「상담소 끄기/켜기」) — 결과 = 바뀐 뒤의 {auto, …}(못 켜면 auto=false · error).
#[tauri::command]
pub(crate) async fn counsel_auto_set(on: bool) -> Value {
    pack_verb(vec!["auto-set", if on { "on" } else { "off" }]).await
}

/// 첫 안내 창을 닫았다(안내문이 이 기기 화면에 떴다) — 이 표식 전에는 팩이 보내지 않는다.
#[tauri::command]
pub(crate) async fn counsel_notice_seen() -> Value {
    pack_verb(vec!["notice-seen"]).await
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn pack_verb_command_is_isolated_and_pins_dirs() {
        let cmd = pack_verb_command("python3", Path::new("/p"), Path::new("/c"), &["auto-set", "off"]);
        let args: Vec<String> = cmd.get_args().map(|a| a.to_string_lossy().to_string()).collect();
        let script = Path::new("/p").join("bin").join("javis_counsel.py").to_string_lossy().to_string();
        assert_eq!(args, ["-I", "-B", "-X", "utf8", script.as_str(), "auto-set", "off"]);
        let envs: std::collections::HashMap<String, Option<String>> = cmd
            .get_envs()
            .map(|(k, v)| (k.to_string_lossy().to_string(), v.map(|v| v.to_string_lossy().to_string())))
            .collect();
        for k in PY_ENV_STRIP {
            assert_eq!(envs.get(*k), Some(&None), "{k} 는 자식 env 에서 지운다");
        }
        assert_eq!(envs.get("AGORA_CONFIG_DIR"), Some(&Some("/c".to_string())));
        assert_eq!(envs.get("CYS_PACK_DIR"), Some(&Some("/p".to_string())));
    }

    #[test]
    fn run_pack_verb_takes_the_last_json_line_and_reports_failures() {
        let d = tempfile_lite::Dir::new("packverb");
        let pack = d.path().join("pack");
        std::fs::create_dir_all(pack.join("bin")).unwrap();
        assert_eq!(run_pack_verb(&pack, d.path(), &["auto-status"]), json!({"error": "no-pack"}));
        let script = pack.join("bin").join("javis_counsel.py");
        std::fs::write(
            &script,
            "import os, sys\n\
ok = sys.argv[1:] == ['auto-set', 'off'] and sys.flags.isolated == 1 and os.environ.get('AGORA_CONFIG_DIR')\n\
print('noise')\n\
print('{\"auto\": false, \"notice_seen\": true, \"needs_notice\": false}' if ok else '{\"bad\": 1}')\n",
        )
        .unwrap();
        assert_eq!(
            run_pack_verb(&pack, d.path(), &["auto-set", "off"]),
            json!({"auto": false, "notice_seen": true, "needs_notice": false})
        );
        std::fs::write(&script, "print('not json')\n").unwrap();
        assert_eq!(run_pack_verb(&pack, d.path(), &["auto-status"]), json!({"error": "output"}));
    }

    #[test]
    fn config_dir_env_wins_else_home_dot_config_agora() {
        let home = Path::new("/h");
        assert_eq!(config_dir_from(Some("/x/ag"), home), PathBuf::from("/x/ag"));
        assert_eq!(config_dir_from(Some("  "), home), home.join(".config").join("agora"));
        assert_eq!(config_dir_from(None, home), home.join(".config").join("agora"));
        // 윈 동등성: 같은 식(홈 = %USERPROFILE%) — 구분자만 플랫폼 것.
        let wh = Path::new("C:\\wh");
        assert_eq!(config_dir_from(None, wh), wh.join(".config").join("agora"));
    }

    #[test]
    fn open_url_allows_our_two_hosts_exactly_not_subdomains() {
        assert!(crate::host_in_allowlist("agora.godmeyou.kr", &[]));
        assert!(crate::host_in_allowlist("jarvis-install.godmeyou.kr", &[]));
        for bad in ["godmeyou.kr", "evil.agora.godmeyou.kr", "agora.godmeyou.kr.evil.com", "x.jarvis-install.godmeyou.kr", "agora.godmeyou.krx"] {
            assert!(!crate::host_in_allowlist(bad, &[]), "{bad}");
        }
        // 사용자정보(@) 위장 = 실제 호스트 evil.invalid 로 판정된다.
        assert!(crate::url_host_allowed(&format!("https://agora.godmeyou.kr{}evil.invalid/", "@")).is_err());
        assert!(crate::url_host_allowed("http://agora.godmeyou.kr/").is_err(), "https 만");
        assert!(crate::url_host_allowed("https://jarvis-install.godmeyou.kr/").is_ok());
    }

    /// 시험 전용 임시 폴더(의존성 0 · 끝나면 지운다).
    mod tempfile_lite {
        pub struct Dir(std::path::PathBuf);
        impl Dir {
            pub fn new(tag: &str) -> Self {
                let n = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_nanos();
                let p = std::env::temp_dir().join(format!("cysr-{tag}-{}-{n}", std::process::id()));
                std::fs::create_dir_all(&p).unwrap();
                Dir(p)
            }
            pub fn path(&self) -> &std::path::Path {
                &self.0
            }
        }
        impl Drop for Dir {
            fn drop(&mut self) {
                let _ = std::fs::remove_dir_all(&self.0);
            }
        }
    }
}
