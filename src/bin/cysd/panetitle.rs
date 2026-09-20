//! 페인 제목의 모델 조각 — 「번호 · 모델 · 특성」의 가운데 한 칸을 데몬이 관리한다.
//!
//! 오너 요청 2026-08-07: 「푸터에 모델만 있으니 어색하다. 모델은 제목에 넣자.
//! 페인번호 + 모델 + 제목키워드 형식」.
//!
//! ★왜 데몬인가(정적 1회 기록이 아닌 이유): 모델은 세션 중에 `/model`로 바뀐다. 기동 시 한 번
//! 적어 넣으면 그 순간부터 제목이 거짓말을 한다 — 화면에는 Opus라고 적혀 있는데 실제로는
//! Sonnet이 도는 상태가 조용히 이어진다. 데몬은 statusline의 usage.report를 매 턴 받으므로,
//! 그 model 값으로 조각을 갱신하면 제목이 **관측을 따라간다**.
//!
//! ★소유권 경계: 번호와 특성은 pack의 javis_panetitle.py가 정한다(surface.rename). 이 모듈은
//! **가운데 한 칸만** 건드리고 그 두 조각은 원문 그대로 옮긴다. 두 주인이 같은 문자열을 쓰지만
//! 서로 다른 칸을 쓰므로 충돌하지 않는다 — panetitle.py는 「번호로 시작하면 무접촉」이라
//! 우리가 넣은 모델 조각을 지우지 않는다(그 스크립트의 멱등 규칙이 그대로 우리를 보호한다).

/// 제목에 넣는 모델 조각의 닫힌 어휘.
///
/// ★열린 어휘(display_name을 그대로 넣기)를 쓰지 않는 이유: 조각을 **다시 알아볼 수 있어야**
/// 다음 갱신 때 교체가 되는데, 아무 문자열이나 허용하면 「특성」 칸과 구별할 수 없다.
/// 그러면 모델이 바뀔 때마다 조각이 하나씩 늘어난다(372 · Opus · Sonnet · cys-terminal-src).
/// 닫힌 어휘는 그 재귀 오염을 구조적으로 막는다.
const MODEL_FAMILIES: [&str; 4] = ["Opus", "Sonnet", "Haiku", "Fable"];

/// 구분자 — javis_panetitle.py가 쓰는 것과 같아야 한다(제목은 두 주인이 공유하는 문자열이다).
const SEP: &str = " · ";

/// statusline의 `model.display_name` → 제목 조각.
///
/// 아는 계열이 없으면 None이다. ★모르는 모델에 이름을 붙여 주지 않는다 —
/// 없는 값을 지어내는 것은 관측이 아니라 창작이다(오너 지시: 모델 미관측이면 조각 생략).
pub fn model_segment(display_name: &str) -> Option<&'static str> {
    let low = display_name.to_lowercase();
    MODEL_FAMILIES
        .iter()
        .copied()
        .find(|f| low.contains(&f.to_lowercase()))
}

/// 조각 하나가 모델 칸인가 — 닫힌 어휘와 **완전 일치**로만 판정한다.
///
/// ★부분 일치를 쓰면 「opus-notes」라는 폴더명이 모델 조각으로 오인돼 특성이 지워진다.
fn is_model_segment(seg: &str) -> bool {
    MODEL_FAMILIES.iter().any(|f| f.eq_ignore_ascii_case(seg))
}

/// 제목의 모델 조각을 관측된 모델로 맞춘다.
///
/// 반환 None = **바꿀 것이 없다**(호출자는 rename을 건너뛴다). 멱등이 이 함수의 계약이다 —
/// 매 턴 statusline이 들어오므로, 같은 값에 매번 rename을 쏘면 초당 몇 번씩 제목을 다시 쓰게 된다.
///
/// 무접촉 조건(하나라도 걸리면 None):
///  · 제목이 「숫자 ·」로 시작하지 않는다 ⇒ 번호 규칙 밖이다. 사용자가 지은 이름·자동 제목
///    (`surface 12`)·빈 제목이 여기 해당한다. ★남의 이름을 우리 규칙으로 덮지 않는다.
///  · 이미 원하는 모양이다.
pub fn retitle_with_model(title: &str, model: Option<&str>) -> Option<String> {
    let parts: Vec<&str> = title.split(SEP).collect();
    let num = parts.first()?;
    // 번호 규칙 안인지 — 첫 조각이 숫자만이어야 한다. 빈 제목·자동 제목은 여기서 걸러진다.
    if num.is_empty() || !num.chars().all(|c| c.is_ascii_digit()) {
        return None;
    }
    // 기존 모델 조각(있으면) 제거 — 두 번째 칸만 후보다. 뒤쪽 칸은 특성의 일부일 수 있다.
    let mut rest: Vec<&str> = parts[1..].to_vec();
    if rest.first().is_some_and(|s| is_model_segment(s)) {
        rest.remove(0);
    }
    let desired = model.and_then(model_segment);
    let mut out: Vec<&str> = vec![num];
    if let Some(m) = desired {
        out.push(m);
    }
    out.extend(rest);
    let next = out.join(SEP);
    if next == title {
        return None; // 멱등 — 같은 값에 rename을 쏘지 않는다
    }
    Some(next)
}


// ── 번호·역할특성 칸 (B14 · 오너 관측 2026-09-19 · master 판정 2026-09-20) ──────────────
//
// 오너 관측(참가자 기기 cysr 1.0.2 실기): 「페인 제목에 서피스 번호·모델 표시·역할 키워드가 없다」.
// 결함은 셋이 아니라 **하나**였다 — CLI 가 짓는 제목(`{role}-{agent} · {폴더}`)에 번호가 없고,
// 위 `retitle_with_model` 은 「첫 조각이 숫자가 아니면 무접촉」이라(§retitle_with_model) 모델 칸까지
// 함께 사라진다. ⇒ 번호가 도미노의 첫 조각이다. 여기서 번호를 붙이면 모델 칸은 다음 statusline
// 턴에 코드 변경 0으로 따라 붙는다.
//
// ★왜 create 핸들러인가: 번호는 **id 를 배정하는 이 자리**에서만 알 수 있다(CLI 는 create 응답을
// 받기 전까지 모르므로 사후 rename 이 필요했다). 그리고 이 한 자리가 생성 경로 전부를 덮는다 —
// `cys launch-agent` 와 `cys restore` 는 둘 다 run_launch_agent_opts 의 같은 create 를 지나고,
// GUI 가 만드는 좌석도 같은 RPC 를 지난다. 「부팅 경로·복원 경로에 각각 배선」이 실은 한 곳이다.
//
// ★무접촉 4조건(master 판정 조건 4) — 아래 `initial_title` 이 지킨다:
//   ① role 이 없으면 무접촉(역할 없는 GUI 셸은 UI 가 live_cwd 를 실시간 표시한다 — 제목을 박으면
//      그 추적이 죽는다. ui/src/main.ts 의 isAutoTitle 참조).
//   ② 이미 숫자로 시작하면 무접촉(멱등 · 우리 기기 javis_panetitle.py 가 먼저 붙인 제목과 충돌 0).
//   ③ exited 무접촉 — 이 자리에서는 **구조적으로 성립**한다(방금 만든 좌석은 exited 일 수 없다).
//      분기를 만들지 않는 이유: 영원히 안 밟히는 가드는 검증도 안 되는 장식이다.
//   ④ 사용자가 지정한 이름은 보존한다 — 지우지 않고 **번호만 앞에 붙인다**.
//
// ★우리 기기의 `javis_panetitle.py` 와 **문자열 동형**이어야 한다(두 주인이 같은 답을 내야 제목이
// 흔들리지 않는다). 그래서 범용 폴더명 denylist·role 서수 접기 규칙을 그 스크립트에서 그대로 옮긴다.

/// 범용 폴더명 denylist — 여기 있으면 「특성」으로 인정하지 않고 role 폴백으로 간다(소문자 비교).
/// whitelist 가 아닌 이유: 새 프로젝트를 만들 때마다 등록시키지 않기 위해서다.
/// (javis_panetitle.py GENERIC_DIRS 와 같은 목록 — 갈라지면 두 주인이 다른 제목을 낸다.)
const GENERIC_DIRS: [&str; 48] = [
    "documents", "downloads", "desktop", "tmp", "applications", "src", "bin",
    "library", "movies", "music", "pictures", "public", "users", "home", "root",
    "var", "opt", "usr", "etc", "lib", "share", "private", "volumes", "system",
    "work", "workspace", "workspaces", "projects", "project", "repos", "repo",
    "code", "dev", "temp", "test", "tests", "build", "dist", "target", "out",
    "node_modules", "docs", "doc", "scripts", "script", "config", "data",
    "new",
];

/// 홈 디렉터리 이름(계정마다 다르다)도 특성이 아니다 — 실행 시점에 판정한다.
fn is_generic_dir(base: &str) -> bool {
    let low = base.to_lowercase();
    if GENERIC_DIRS.contains(&low.as_str()) || low == "untitled" || low == "folder" {
        return true;
    }
    cys::home_dir()
        .file_name()
        .map(|h| h.to_string_lossy().to_lowercase() == low)
        .unwrap_or(false)
}

/// role 값에서 **서수만** 읽어 폴백 특성을 만든다. role 자체는 바꾸지 않는다.
/// worker-3 → worker3 · cso-2 → cso2 · reviewer-codex → reviewer-codex(숫자 없는 하이픈은 보존).
/// (javis_panetitle.py role_fallback 의 `re.sub(r"-(\d)", r"\1", role)` 와 같은 규칙.)
fn role_fallback(role: &str) -> String {
    let b: Vec<char> = role.trim().chars().collect();
    let mut out = String::with_capacity(b.len());
    let mut i = 0;
    while i < b.len() {
        if b[i] == '-' && b.get(i + 1).is_some_and(|c| c.is_ascii_digit()) {
            i += 1; // 하이픈만 버리고 숫자는 남긴다
            continue;
        }
        out.push(b[i]);
        i += 1;
    }
    out
}

/// 역할명 자체가 특성인 역할인가 — master·cso(및 그 서수판)(master 판정 2026-09-20).
/// ★왜 이 둘만인가: 좌석 폴더 표(templates/seat-layout.json)에서 master 는 좌석 하위폴더가 없어
/// 본부 루트를 그대로 쓴다 — 그 폴더 이름은 그 노드가 무엇인지 말해 주지 않는다. cso 는 좌석
/// 폴더 이름이 마침 "cso" 라 두 규칙의 답이 같다(동형 유지). worker 는 좌석 폴더(w1·w2…)나
/// 워크플로우 폴더가 곧 특성이므로 종전 규칙 그대로다.
fn role_is_its_own_characteristic(role: &str) -> bool {
    let r = role.trim();
    r == "master" || r == "cso" || r.starts_with("master-") || r.starts_with("cso-")
}

/// 특성 한 단어. cwd basename 이 범용명이면 role 폴백.
fn characteristic(role: &str, cwd: Option<&str>) -> String {
    if role_is_its_own_characteristic(role) {
        return role_fallback(role);
    }
    let base = cwd
        .map(|s| s.trim_end_matches(['/', '\\']))
        .and_then(|s| s.rsplit(['/', '\\']).next())
        .filter(|f| !f.is_empty())
        // Windows 드라이브 루트(`C:\` → 트림 후 `C:`)는 폴더명이 아니다.
        .filter(|f| !(f.len() == 2 && f.ends_with(':') && f.as_bytes()[0].is_ascii_alphabetic()))
        .filter(|f| !is_generic_dir(f));
    match base {
        Some(f) => f.to_string(),
        None => role_fallback(role),
    }
}

/// 이미 「이 surface 의 번호」로 시작하는가 = 규칙 충족 = 무동작 대상.
/// (javis_panetitle.py is_conforming 과 같은 판정 — 번호 뒤는 공백이거나 끝이어야 한다.
///  숫자만 대조하면 87 이 874 를 통과시킨다.)
fn starts_with_number(sid: u64, title: &str) -> bool {
    let t = title.trim_start();
    let n = sid.to_string();
    t.strip_prefix(n.as_str())
        .is_some_and(|rest| rest.is_empty() || rest.starts_with(' '))
}

/// 기계가 지은 제목인가 — 「사람이 지은 이름」과 가르는 판정. 두 생산자를 **정확히** 대조한다.
/// ★추측이 아니라 대조인 이유: 두 문자열 모두 이 저장소 안에 정의가 있다.
///   ⑴데몬 기본값 `surface {id}`(state.rs — title 미지정 시) · UI 도 이것을 자동 제목으로 본다
///     (ui/src/main.ts `isAutoTitle`).
///   ⑵CLI `workflow_title()`(src/bin/cys.rs) 의 `{role}-{agent}` / `{role}-{agent} · {폴더}`.
/// role·agent 를 둘 다 알고 있으므로 `{role}-{agent}` 는 지어낸 패턴이 아니라 그 함수의 정의다.
fn is_machine_title(title: &str, sid: u64, role: &str, agent: Option<&str>) -> bool {
    if title == format!("surface {sid}") {
        return true;
    }
    let Some(agent) = agent else { return false };
    let head = format!("{role}-{agent}");
    title == head || title.starts_with(&format!("{head}{SEP}"))
}

/// 첫 조각이 **숫자만**인가 — 그렇다면 뒤따르는 나머지를 돌려준다(낡은 번호 판정).
/// `None` = 번호로 시작하지 않는다. `Some("")` = 번호만 있고 뒤가 없다.
fn stale_number_tail(title: &str) -> Option<&str> {
    let t = title.trim_start();
    match t.split_once(SEP) {
        Some((head, tail)) if !head.is_empty() && head.chars().all(|c| c.is_ascii_digit()) => {
            Some(tail)
        }
        None if !t.is_empty() && t.chars().all(|c| c.is_ascii_digit()) => Some(""),
        _ => None,
    }
}

/// 새로 태어난 좌석의 제목을 정한다. `None` = 건드리지 않는다.
///
/// 모델 칸은 여기서 넣지 않는다 — create 시점에는 관측이 없기 때문이다(없는 값을 지어내지 않는다).
/// 첫 statusline 턴에 `retitle_with_model` 이 「번호 · 모델 · 특성」으로 완성한다.
pub fn initial_title(
    sid: u64,
    role: Option<&str>,
    cwd: Option<&str>,
    requested: Option<&str>,
    agent: Option<&str>,
) -> Option<String> {
    let role = role.map(str::trim).filter(|r| !r.is_empty())?; // ①role 없으면 무접촉
    let canonical = format!("{sid}{SEP}{}", characteristic(role, cwd));
    match requested.map(str::trim).filter(|t| !t.is_empty()) {
        // ②이미 이 번호로 시작 = 멱등(우리 기기 javis_panetitle.py 선착분 포함)
        Some(t) if starts_with_number(sid, t) => None,
        // 기계가 지은 제목(데몬 기본값·CLI workflow_title) = 우리가 대체한다
        Some(t) if is_machine_title(t, sid, role, agent) => Some(canonical),
        // 다른 번호로 시작 = **낡은 번호**(다른 좌석에서 물려받은 제목·수기 이관). 번호 칸만
        // 갈아 끼우고 뒤는 원문 그대로 옮긴다 — 안 그러면 「60 · 285 · research」처럼 번호가 쌓인다.
        Some(t) if stale_number_tail(t).is_some() => match stale_number_tail(t) {
            Some(tail) if !tail.is_empty() => Some(format!("{sid}{SEP}{tail}")),
            _ => Some(canonical),
        },
        // ④사람이 지은 이름 = 지우지 않는다. 번호만 앞에 붙인다.
        Some(t) => Some(format!("{sid}{SEP}{t}")),
        // 제목 미지정 = 규칙대로
        None => Some(canonical),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn inserts_model_between_number_and_keyword() {
        assert_eq!(
            retitle_with_model("372 · cys-terminal-src", Some("Opus 4.1")).as_deref(),
            Some("372 · Opus · cys-terminal-src")
        );
    }

    #[test]
    fn idempotent_when_already_correct() {
        // ★매 턴 statusline이 들어온다 — 같은 값에 None을 돌려주지 않으면 제목을 계속 다시 쓴다.
        assert_eq!(retitle_with_model("372 · Opus · cys-terminal-src", Some("Opus 4.1")), None);
    }

    #[test]
    fn follows_model_switch() {
        // /model 전환 추종 — 조각이 늘어나지 않고 교체된다.
        assert_eq!(
            retitle_with_model("372 · Opus · cys-terminal-src", Some("Claude Sonnet 5")).as_deref(),
            Some("372 · Sonnet · cys-terminal-src")
        );
        // 두 번 바꿔도 조각은 계속 하나다(재귀 오염 없음).
        assert_eq!(
            retitle_with_model("372 · Sonnet · cys-terminal-src", Some("Fable 5")).as_deref(),
            Some("372 · Fable · cys-terminal-src")
        );
    }

    #[test]
    fn unknown_model_adds_nothing() {
        // 지어내기 금지 — 모르는 이름은 조각을 만들지 않는다.
        assert_eq!(retitle_with_model("372 · cys-terminal-src", Some("gpt-5.6-sol")), None);
        assert_eq!(model_segment("gpt-5.6-sol"), None);
    }

    #[test]
    fn no_model_observed_leaves_title_alone() {
        // 셸 페인 등 모델 미관측 — 조각 생략.
        assert_eq!(retitle_with_model("371 · scripts", None), None);
    }

    #[test]
    fn no_model_observed_strips_stale_segment() {
        // 관측이 끊겼는데 옛 조각이 남아 있으면 지운다 — 없는 것을 있다고 적어 두지 않는다.
        assert_eq!(
            retitle_with_model("371 · Opus · scripts", None).as_deref(),
            Some("371 · scripts")
        );
    }

    #[test]
    fn leaves_user_named_titles_untouched() {
        // 번호 규칙 밖 = 남의 이름. 우리 규칙으로 덮지 않는다.
        assert_eq!(retitle_with_model("내 작업창", Some("Opus 4.1")), None);
        assert_eq!(retitle_with_model("surface 12", Some("Opus 4.1")), None);
        assert_eq!(retitle_with_model("", Some("Opus 4.1")), None);
    }

    #[test]
    fn keyword_containing_family_word_is_not_eaten() {
        // ★부분 일치였다면 여기서 특성이 지워졌다 — 완전 일치 판정의 존재 이유.
        assert_eq!(
            retitle_with_model("372 · opus-notes", Some("Opus 4.1")).as_deref(),
            Some("372 · Opus · opus-notes")
        );
    }

    #[test]
    fn number_only_title_gets_model() {
        assert_eq!(
            retitle_with_model("372", Some("Opus 4.1")).as_deref(),
            Some("372 · Opus")
        );
    }

    // ── B14 양방향 강제발화 (master 판정 조건 4 · 2026-09-20) ────────────────────────
    // 「반드시 바뀌어야 하는 것」과 「반드시 안 건드려야 하는 것」을 함께 잰다. 한쪽만 재면
    // 아무것도 안 바꾸는 구현(또는 전부 덮는 구현)이 통과한다 — 거울상을 막는 것이 이 짝의 목적이다.

    const CLAUDE: Option<&str> = Some("claude");

    #[test]
    fn b14_must_change_daemon_default_title_gets_number_and_characteristic() {
        // 데몬 기본값 `surface {id}` — GUI·수동 생성 좌석이 여기 해당한다.
        assert_eq!(
            initial_title(874, Some("worker-5"), Some("/Users/x/axdev/.wt/cys-seat-folders"),
                          Some("surface 874"), CLAUDE).as_deref(),
            Some("874 · cys-seat-folders")
        );
    }

    #[test]
    fn b14_must_change_cli_workflow_title_is_replaced() {
        // ★오너가 참가자 기기에서 실제로 본 제목(2026-09-19 윈 캡처) = 이 입력이다.
        assert_eq!(
            initial_title(870, Some("worker"), Some("/Users/x/cys-terminal-src"),
                          Some("worker-claude · cys-terminal-src"), CLAUDE).as_deref(),
            Some("870 · cys-terminal-src")
        );
        // 폴더를 알 수 없어 role-agent 만 있는 판본
        assert_eq!(
            initial_title(12, Some("worker-2"), Some("/"), Some("worker-2-claude"), CLAUDE).as_deref(),
            Some("12 · worker2")
        );
    }

    #[test]
    fn b14_must_change_master_and_cso_use_role_name() {
        // master 판정 2026-09-20: master·cso 의 특성은 폴더가 아니라 역할명이다.
        assert_eq!(
            initial_title(30, Some("master"), Some("/Users/x/hq"),
                          Some("master-claude · hq"), CLAUDE).as_deref(),
            Some("30 · master")
        );
        // cso 는 좌석 폴더 이름이 마침 "cso" 라 두 규칙의 답이 같다(동형 유지 — seat-layout.json).
        assert_eq!(
            initial_title(31, Some("cso"), Some("/Users/x/hq/cso"),
                          Some("cso-claude · cso"), CLAUDE).as_deref(),
            Some("31 · cso")
        );
    }

    #[test]
    fn b14_must_change_generic_folder_falls_back_to_role() {
        // javis_panetitle.py 동형 — 범용 폴더명은 특성이 아니다(서수는 보존).
        assert_eq!(
            initial_title(72, Some("worker-3"), Some("/Users/x/Documents"),
                          Some("worker-3-claude · Documents"), CLAUDE).as_deref(),
            Some("72 · worker3")
        );
        // src(범용)는 걸리고 cys-terminal-src(고유)는 안 걸린다
        assert_eq!(
            initial_title(73, Some("worker"), Some("/Users/x/y/src"),
                          Some("worker-claude · src"), CLAUDE).as_deref(),
            Some("73 · worker")
        );
    }

    #[test]
    fn b14_must_change_home_folder_is_not_a_characteristic() {
        // 홈 디렉터리 이름은 계정마다 달라 하드코딩할 수 없다 — 실행 시점에 판정한다.
        let home = cys::home_dir().to_string_lossy().to_string();
        assert_eq!(
            initial_title(293, Some("worker-3"), Some(home.as_str()),
                          Some("worker-3-claude"), CLAUDE).as_deref(),
            Some("293 · worker3")
        );
    }

    #[test]
    fn b14_must_change_no_title_requested() {
        assert_eq!(
            initial_title(44, Some("master"), Some("/Users/x/hq"), None, None).as_deref(),
            Some("44 · master")
        );
    }

    #[test]
    fn b14_must_change_stale_number_is_swapped_not_stacked() {
        // 다른 좌석의 번호를 물고 온 제목 — 번호 칸만 갈린다(번호가 쌓이면 안 된다).
        assert_eq!(
            initial_title(60, Some("worker-2"), Some("/Users/x/research"),
                          Some("285 · research"), CLAUDE).as_deref(),
            Some("60 · research")
        );
        // 모델 칸이 이미 붙어 있던 제목도 조각 구조가 보존된다.
        assert_eq!(
            initial_title(61, Some("worker"), Some("/Users/x/research"),
                          Some("285 · Opus · research"), CLAUDE).as_deref(),
            Some("61 · Opus · research")
        );
        // 번호만 있고 뒤가 없으면 규칙대로 다시 짓는다.
        assert_eq!(
            initial_title(62, Some("worker"), Some("/Users/x/research"), Some("285"), CLAUDE).as_deref(),
            Some("62 · research")
        );
    }

    #[test]
    fn b14_must_not_change_roleless_surface() {
        // ①역할 없는 GUI 셸 — UI 가 live_cwd 를 실시간 표시한다. 제목을 박으면 그 추적이 죽는다.
        assert_eq!(initial_title(7, None, Some("/Users/x/anywhere"), Some("surface 7"), None), None);
        assert_eq!(initial_title(8, Some(""), Some("/Users/x/anywhere"), Some("surface 8"), None), None);
        assert_eq!(initial_title(9, Some("   "), Some("/Users/x/anywhere"), None, None), None);
    }

    #[test]
    fn b14_must_not_change_already_numbered() {
        // ②멱등 — 우리 기기 javis_panetitle.py 가 먼저 붙인 제목과 충돌 0.
        assert_eq!(
            initial_title(874, Some("worker-5"), Some("/Users/x/axdev/.wt/cys-seat-folders"),
                          Some("874 · Opus · cys-seat-folders"), CLAUDE),
            None
        );
        assert_eq!(
            initial_title(11, Some("worker"), Some("/Users/x/y"), Some("11"), CLAUDE),
            None
        );
    }

    #[test]
    fn b14_must_not_change_user_named_title_keeps_its_words() {
        // ④사람이 지은 이름 — 이미 번호가 있으면 통째로 보존.
        assert_eq!(
            initial_title(297, Some("worker"), Some("/Users/x/cys-terminal-src"),
                          Some("297 박사님 지시 대기창"), CLAUDE),
            None
        );
        // 번호가 없으면 **지우지 않고 번호만 앞에 붙인다**(지우는 구현이었다면 여기서 빨개진다).
        assert_eq!(
            initial_title(60, Some("worker"), Some("/Users/x/research"),
                          Some("내 작업창"), CLAUDE).as_deref(),
            Some("60 · 내 작업창")
        );
    }

    #[test]
    fn b14_number_boundary_is_not_a_prefix_match() {
        // ★비대칭을 둘 다 잰다. 접두 일치로 완화한 구현은 **이 방향에서만** 빨개진다:
        //   sid=87 이 「874 · …」를 「이미 내 번호로 시작한다」고 읽어 남의 번호를 그대로 둔다.
        assert_eq!(
            initial_title(87, Some("worker"), Some("/Users/x/research"),
                          Some("874 · research"), CLAUDE).as_deref(),
            Some("87 · research")
        );
        // 반대 방향(짧은 번호가 앞에 오는 경우)도 교체된다.
        assert_eq!(
            initial_title(874, Some("worker"), Some("/Users/x/research"),
                          Some("87 · research"), CLAUDE).as_deref(),
            Some("874 · research")
        );
        // 경계가 공백이면 내 번호다 — 무접촉.
        assert_eq!(
            initial_title(87, Some("worker"), Some("/Users/x/research"),
                          Some("87 · research"), CLAUDE),
            None
        );
    }

    #[test]
    fn b14_hands_off_to_the_model_owner() {
        // create 시점에는 모델 관측이 없다 — 번호·특성만 세우고, 첫 statusline 턴에 모델 칸이 붙는다.
        let created = initial_title(870, Some("worker"), Some("/Users/x/cys-terminal-src"),
                                    Some("worker-claude · cys-terminal-src"), CLAUDE).unwrap();
        assert_eq!(created, "870 · cys-terminal-src");
        assert_eq!(
            retitle_with_model(&created, Some("Claude Opus 5")).as_deref(),
            Some("870 · Opus · cys-terminal-src")
        );
        // 그리고 그 결과는 다시 무접촉이다(두 주인이 서로를 지우지 않는다).
        assert_eq!(
            initial_title(870, Some("worker"), Some("/Users/x/cys-terminal-src"),
                          Some("870 · Opus · cys-terminal-src"), CLAUDE),
            None
        );
    }
}
