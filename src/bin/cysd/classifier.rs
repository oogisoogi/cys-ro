//! 에이전트 훅 이벤트 분류기 — (source, event, tool) → (wire 이벤트명, 사람 주의 필요 여부).
//!
//! 이벤트 이름 문자열을 그대로 비교하지 않고 **의미**(승인 대기·도구 시작·응답 …)로 먼저 옮긴 뒤,
//! 의미에서 wire 이름을 정한다. 그래야 「도구 시작」 을 「승인 요청」 으로 잘못 알리는 일이 구조적으로
//! 막힌다. ★이 분류기는 에이전트를 막지 않는다 — 주의 신호만 붙인다(차단 여부는 팩 정책).
//! (TICKET=cysr-117-impl-lead ⑲: 우리 표 기반으로 재작성 · 전후 동치 = 시험 `golden_classify_full_table_is_frozen`.)

/// 사람 주의가 필요한지를 가르는 의미. 알림·차단은 이 의미로만 정한다.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Meaning {
    /// 실제 승인 대기 — 주의 필요.
    Approval,
    /// 전용 승인 이벤트가 따로 있는 에이전트의 도구 시작 — 기록용.
    ToolStart,
    /// 전용 승인 이벤트가 없는 에이전트의 도구 시작 — 상태를 바꾸는 도구면 승인으로 올린다.
    ToolStartUnsure,
    ToolEnd,
    PromptSubmit,
    Response,
    SubagentResponse,
    SessionStart,
    SessionEnd,
    Notice,
    /// 모르는 이벤트 — 기록용(주의 신호로 올리지 않는 쪽이 안전).
    Unknown,
}

use Meaning::*;

/// 공통 줄 — 알려진 에이전트(claude·codex)가 같이 쓰는 이름과 의미.
/// CLI 가 훅 이름을 `PRE_TOOL`·`POST_TOOL`·`STOP`·`SUBAGENT_STOP` 으로 바꿔 보내므로(cys.rs
/// `hook_to_event_params`) 원래 이름과 바뀐 이름을 **둘 다** 싣는다 — 한쪽만 두면 그 단계의 이벤트가
/// 전부 Unknown 으로 떨어진다.
const KNOWN_AGENT_COMMON: &[(&str, Meaning)] = &[
    ("PreToolUse", ToolStart),
    ("PRE_TOOL", ToolStart),
    ("PostToolUse", ToolEnd),
    ("POST_TOOL", ToolEnd),
    ("UserPromptSubmit", PromptSubmit),
    ("SessionStart", SessionStart),
    ("SessionEnd", SessionEnd),
    ("Stop", Response),
    ("STOP", Response),
    ("SubagentStop", SubagentResponse),
    ("SUBAGENT_STOP", SubagentResponse),
    ("Notification", Notice),
];

/// claude 만의 줄 — 승인 요청은 진짜 승인 대기다.
const CLAUDE_ONLY: &[(&str, Meaning)] = &[("PermissionRequest", Approval)];

/// codex 만의 줄 — codex 의 승인 요청은 **기록용**이다(막으면 「대신 승인」 자동 검토를 멈춘다).
const CODEX_ONLY: &[(&str, Meaning)] = &[
    ("PermissionRequest", ToolStart),
    ("beforeShellExecution", ToolStart),
];

/// 표에 없는 에이전트(gemini·agy 등)의 줄 — 도구 시작 말고는 승인 신호가 없어 「불확실」 로 둔다.
/// 바뀐 이름(`PRE_TOOL` 등)은 싣지 않는다 — 이 에이전트들은 원래 이름으로만 온다.
const OTHER_AGENT: &[(&str, Meaning)] = &[
    ("PreToolUse", ToolStartUnsure),
    ("beforeShellExecution", ToolStartUnsure),
    ("PermissionRequest", Approval),
    ("PostToolUse", ToolEnd),
    ("UserPromptSubmit", PromptSubmit),
    ("SessionStart", SessionStart),
    ("SessionEnd", SessionEnd),
    ("Stop", Response),
    ("SubagentStop", SubagentResponse),
    ("Notification", Notice),
];

/// 자기만의 승인 wire 이벤트가 있는 도구 — 그 이름 그대로 주의 신호로 보낸다.
const OWN_APPROVAL_TOOLS: &[&str] = &["ExitPlanMode", "AskUserQuestion"];

/// 상태를 바꿔 승인을 받아야 하는 도구(19개). 읽기 전용(Read·Grep·Glob·Task·WebFetch·WebSearch·
/// LS·TodoWrite)은 일부러 뺐다. 대소문자는 구분한다(소문자 별칭을 쓰는 에이전트는 아직 없다).
const STATE_CHANGING_TOOLS: &[&str] = &[
    "Bash",
    "Write",
    "Edit",
    "MultiEdit",
    "NotebookEdit",
    "apply_patch",
    "shell",
    "terminal",
    "run_command",
    "write_to_file",
    "replace_file_content",
    "multi_replace_file_content",
    "manage_task",
    "schedule",
    "ask_permission",
    "invoke_subagent",
    "define_subagent",
    "manage_subagents",
    "generate_image",
];

/// 공개 진입점 — usage.event 핸들러가 부른다. 반환 = (wire hook_event_name, 주의 필요).
pub fn classify(source: &str, event: &str, tool_name: &str) -> (String, bool) {
    let (name, attention) = to_wire(meaning_of(source, event), tool_name);
    (name.to_string(), attention)
}

/// (source, event) → 의미. 알려진 에이전트는 자기 줄 → 공통 줄 순서로 찾고, 어디에도 없으면
/// Unknown 이다(다른 에이전트 표로 넘어가지 않는다). 모르는 에이전트는 OTHER_AGENT 표만 본다.
fn meaning_of(source: &str, event: &str) -> Meaning {
    let lookup = |rows: &[(&str, Meaning)]| rows.iter().find(|(e, _)| *e == event).map(|r| r.1);
    let own: &[(&str, Meaning)] = match source {
        "claude" => CLAUDE_ONLY,
        "codex" => CODEX_ONLY,
        _ => return lookup(OTHER_AGENT).unwrap_or(Unknown),
    };
    lookup(own).or_else(|| lookup(KNOWN_AGENT_COMMON)).unwrap_or(Unknown)
}

/// 의미 → (wire 이름, 주의 필요). 도구에 따라 갈리는 것은 승인·불확실 두 의미뿐이다.
fn to_wire(meaning: Meaning, tool: &str) -> (&str, bool) {
    let own_approval = OWN_APPROVAL_TOOLS.iter().find(|t| **t == tool).copied();
    match meaning {
        Approval => own_approval.map_or(("PermissionRequest", true), |t| (t, true)),
        ToolStartUnsure => match own_approval {
            Some(t) => (t, true),
            None if STATE_CHANGING_TOOLS.contains(&tool) => ("PermissionRequest", true),
            None => ("PreToolUse", false),
        },
        ToolStart | Unknown => ("PreToolUse", false),
        ToolEnd => ("PostToolUse", false),
        PromptSubmit => ("UserPromptSubmit", false),
        Response => ("Stop", false),
        SubagentResponse => ("SubagentStop", false),
        SessionStart => ("SessionStart", false),
        SessionEnd => ("SessionEnd", false),
        Notice => ("Notification", false),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// ⑲(TICKET=cysr-117-impl-lead) 재작성 전후 동치 핀 — source × event × tool 전 조합의 분류 결과를
    /// 한 줄씩 이어 sha256 으로 박는다. 골든 값은 재작성 **전**(v1.1.6 = 76d2b5e9) 코드로 산출했다.
    /// 재작성이 한 조합이라도 바꾸면 적색 — 그때는 재작성이 틀린 것이다(골든을 고치지 마라).
    fn classify_table_digest() -> (usize, String) {
        use sha2::{Digest, Sha256};
        const SOURCES: &[&str] = &["claude", "codex", "gemini", "agy", "grok", "kiro", ""];
        const EVENTS: &[&str] = &[
            "PermissionRequest", "PreToolUse", "PostToolUse", "PRE_TOOL", "POST_TOOL",
            "UserPromptSubmit", "SessionStart", "SessionEnd", "Stop", "STOP", "SubagentStop",
            "SUBAGENT_STOP", "Notification", "beforeShellExecution", "stop", "pretooluse",
            "Unknown", "",
        ];
        const TOOLS: &[&str] = &[
            "Bash", "Write", "Edit", "MultiEdit", "NotebookEdit", "apply_patch", "shell",
            "terminal", "run_command", "write_to_file", "replace_file_content",
            "multi_replace_file_content", "manage_task", "schedule", "ask_permission",
            "invoke_subagent", "define_subagent", "manage_subagents", "generate_image",
            "ExitPlanMode", "AskUserQuestion", "Read", "Grep", "Glob", "Task", "WebFetch",
            "WebSearch", "LS", "TodoWrite", "bash", "write", "", "Unknown",
        ];
        let mut h = Sha256::new();
        let mut n = 0usize;
        for s in SOURCES {
            for e in EVENTS {
                for t in TOOLS {
                    let (w, a) = classify(s, e, t);
                    h.update(format!("{s}|{e}|{t}=>{w},{a}\n").as_bytes());
                    n += 1;
                }
            }
        }
        let d: [u8; 32] = h.finalize().into();
        (n, d.iter().map(|b| format!("{b:02x}")).collect())
    }

    #[test]
    fn golden_classify_full_table_is_frozen() {
        let (n, digest) = classify_table_digest();
        assert_eq!(n, 7 * 18 * 33);
        assert_eq!(digest, "a8cdbec6441e0305dbb2d1d2f26edb8aa63e8aa59f71621ca976dde11e3643b5", "분류표가 바뀌었다(재작성 동치 위반)");
    }

    #[test]
    fn claude_pretool_is_non_actionable() {
        assert_eq!(
            classify("claude", "PreToolUse", "Bash"),
            ("PreToolUse".into(), false)
        );
    }

    /// ★E-a 경로: 데몬이 실제로 받는 값은 CLI 변환명(PRE_TOOL/POST_TOOL). 병기 키가 없으면
    /// Unknown으로 떨어져 분류가 무력화된다(reviewer §4 치명 교정 핀).
    #[test]
    fn claude_cli_converted_names_are_classified() {
        assert_eq!(
            classify("claude", "PRE_TOOL", "Bash"),
            ("PreToolUse".into(), false)
        );
        assert_eq!(
            classify("claude", "POST_TOOL", "Bash"),
            ("PostToolUse".into(), false)
        );
        assert_eq!(
            classify("claude", "STOP", ""),
            ("Stop".into(), false)
        );
        assert_eq!(
            classify("claude", "SUBAGENT_STOP", ""),
            ("SubagentStop".into(), false)
        );
    }

    #[test]
    fn codex_cli_converted_names_are_classified() {
        assert_eq!(
            classify("codex", "PRE_TOOL", "shell"),
            ("PreToolUse".into(), false)
        );
        assert_eq!(
            classify("codex", "POST_TOOL", "shell"),
            ("PostToolUse".into(), false)
        );
    }

    /// 미등록 source(gemini/agy)의 side-effecting pre-tool → approval escalate.
    #[test]
    fn generic_side_effecting_escalates() {
        assert_eq!(
            classify("gemini", "PreToolUse", "Bash"),
            ("PermissionRequest".into(), true)
        );
        assert_eq!(
            classify("gemini", "PreToolUse", "run_command"),
            ("PermissionRequest".into(), true)
        );
    }

    #[test]
    fn generic_read_only_stays_telemetry() {
        assert_eq!(
            classify("gemini", "PreToolUse", "Read"),
            ("PreToolUse".into(), false)
        );
    }

    /// ★#4985: codex PermissionRequest는 의도적 telemetry(블로킹하면 'Approve for me' 차단).
    #[test]
    fn codex_permission_is_non_actionable() {
        assert_eq!(
            classify("codex", "PermissionRequest", "Bash"),
            ("PreToolUse".into(), false)
        );
    }

    #[test]
    fn claude_permission_is_actionable() {
        assert_eq!(
            classify("claude", "PermissionRequest", "Bash"),
            ("PermissionRequest".into(), true)
        );
    }

    #[test]
    fn dedicated_exit_plan_mode_and_ask_user_question() {
        assert_eq!(
            classify("claude", "PermissionRequest", "ExitPlanMode"),
            ("ExitPlanMode".into(), true)
        );
        assert_eq!(
            classify("claude", "PermissionRequest", "AskUserQuestion"),
            ("AskUserQuestion".into(), true)
        );
    }

    #[test]
    fn unknown_event_is_safe_default() {
        assert_eq!(
            classify("claude", "FutureEvent", "X"),
            ("PreToolUse".into(), false)
        );
    }

    /// 상태를 바꾸는 도구 19개 정확 일치 박제 — 읽기 전용은 제외 확인.
    #[test]
    fn all_19_side_effecting_tools_match() {
        let side = [
            "Bash",
            "Write",
            "Edit",
            "MultiEdit",
            "NotebookEdit",
            "apply_patch",
            "shell",
            "terminal",
            "run_command",
            "write_to_file",
            "replace_file_content",
            "multi_replace_file_content",
            "manage_task",
            "schedule",
            "ask_permission",
            "invoke_subagent",
            "define_subagent",
            "manage_subagents",
            "generate_image",
        ];
        assert_eq!(side.len(), 19);
        for t in side {
            assert!(STATE_CHANGING_TOOLS.contains(&t), "{t} should be side-effecting");
        }
        for t in ["Read", "Grep", "Glob", "Task", "WebFetch", "WebSearch", "LS", "TodoWrite", ""] {
            assert!(!STATE_CHANGING_TOOLS.contains(&t), "{t} must not be side-effecting");
        }
    }
}
