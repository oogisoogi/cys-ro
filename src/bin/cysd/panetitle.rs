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
//! ★소유권 경계(2026-09-20 B14 이후 개정 — 구 서술 「번호와 특성은 pack 이 정한다」는 낡았다):
//! 번호·특성은 **이 모듈이** 좌석 생성 시 정하고(§initial_title), 모델 칸은 관측마다 갱신한다
//! (§retitle_with_model). 우리 맥에만 있는 pack 스크립트 `javis_panetitle.py`(저장소 밖·사용자본)가
//! 같은 문자열을 만지지만, 그 스크립트도 이 모듈도 「이미 번호로 시작하면 무접촉」이라 서로를
//! 지우지 않는다. ⚠단 그 스크립트의 특성 규칙은 아직 cwd basename 이다(v1.1.1 규칙 미정렬 —
//! 우리 맥에서 그것을 돌리면 옛 규칙 제목이 된다. docs/HANDOFF-v110-panetitle.md §7-6-3).

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


// ── 번호·역할특성 칸 (B14 2026-09-19/20 · ★v1.1.1 규칙 개정 2026-09-21) ────────────────────
//
// 오너 관측(참가자 기기 cysr 1.1.0 갱신 실기 2026-09-21 08:15 캡처):
//   「현재 머리글을 보면 번호+모델 이후 내용이 너무 길다. master, cso 하나면 충분하고, 워커도
//    맡은 역할 키워드 1나면 된다. 없으면 worker1이고」
// 그때 실측된 제목 = 「38 · Opus · master-claude · install-jarvis」 — 네 칸이다.
//
// ★1.1.0 규칙의 무엇이 길게 만들었나(원인 두 겹 · 둘 다 코드 실측):
//   ⑴ 특성을 **cwd basename** 에서 뽑았다 ⇒ 폴더 이름이 제목에 들어온다(`install-jarvis`).
//   ⑵ `cys launch-agent` 의 surface.create 페이로드에 **agent 키가 없다**(src/bin/cys.rs:12635)
//      ⇒ create 시점 `agent_meta` 가 None ⇒ 종전 `is_machine_title` 이 agent 를 못 얻어 CLI 가 지은
//      `master-claude · install-jarvis` 를 **사람이 지은 이름**으로 읽고 번호만 앞에 붙였다.
//      그래서 role-agent 결합명까지 통째로 살아남았다(무접촉 ④ 가 의도대로 작동한 결과다).
//
// ★v1.1.1 규칙 — 특성은 **role 하나에서만** 나온다(cwd 미참조):
//   master → `master` · cso → `cso` · worker-eduscan → `eduscan` · worker-research → `research`
//   worker → `worker1` · worker-3 → `worker3` · reviewer-codex → `codex` · reviewer → `reviewer1`
//   결과 = 「38 · Opus · master」「36 · Opus · cso」「37 · Opus · worker1」「41 · Sonnet · eduscan」
//
// ★무접촉 4조건(1.1.0 에서 그대로 승계 — 규칙이 바뀌어도 경계는 안 바뀐다):
//   ① role 이 없으면 무접촉(역할 없는 GUI 셸은 UI 가 live_cwd 를 실시간 표시한다).
//   ② 이미 이 번호로 시작하면 무접촉(멱등 · 우리 기기 javis_panetitle.py 선착분 포함).
//   ③ exited 무접촉 — 이 자리에서는 구조적으로 성립(방금 만든 좌석은 exited 일 수 없다).
//   ④ 사람이 지은 이름은 지우지 않는다 — 번호만 앞에 붙인다.

/// 알려진 에이전트 이름 — **닫힌 어휘**(모델 조각과 같은 철학 §MODEL_FAMILIES).
///
/// 쓰임은 한 곳뿐이다: `agent` 를 모르는 채로 CLI 가 지은 `{role}-{agent}` 제목을 알아보는 것.
/// ★열린 판정(하이픈 뒤 아무 단어나 = 에이전트)을 쓰지 않는 이유: 사람이 지은 `worker-메모`
/// 같은 이름을 기계 제목으로 오인해 지운다(무접촉 ④ 위반). 닫힌 어휘는 그 방향을 막는다.
/// ★어휘가 낡으면(새 에이전트 추가) 판정이 false 로 떨어져 제목이 **사람 이름처럼 보존**된다 —
/// 길어질 뿐 잃는 것은 없다(안전 방향). 항구 처방은 호출부가 agent 를 싣는 것이다(위 ⑵).
const AGENT_NAMES: [&str; 4] = ["claude", "gemini", "codex", "grok"];

/// role 문자열을 「머리 · 꼬리」로 가른다(첫 하이픈 기준). `worker-eduscan` → (worker, eduscan).
fn split_role(role: &str) -> (&str, &str) {
    let r = role.trim();
    match r.split_once('-') {
        Some((head, tail)) => (head, tail),
        None => (r, ""),
    }
    // ★여기서 trim 하지 않는다 — `characteristic_inner` 가 조립 전에 `one_word` 로 정화하므로
    //   `master - 2` 의 `master `(공백 포함)는 거기서 `master` 가 된다(agy R1 문제점 2-1 은
    //   그 정화로 닫힌다). trim 을 여기 또 두면 **뮤테이션으로 구별되지 않는 중복**이 된다 —
    //   실제로 그 판본에서 trim 제거 뮤턴트가 SURVIVED 였다(등가 뮤턴트).
}

/// 특성 한 단어 — **role 에서만** 나온다(v1.1.1 · cwd 미참조).
///
/// · master·cso = 역할명 자체가 특성이다(좌석 폴더 이름은 그 노드가 무엇인지 말해 주지 않는다).
/// · 그 밖의 역할 = 꼬리가 키워드면 키워드, 없거나 숫자면 「머리+서수」.
///   서수가 곧 「생성 순」인 이유: role 서수(worker-2·worker-3)를 배정하는 쪽이 생성 순으로 준다.
pub fn characteristic(role: &str) -> String {
    characteristic_inner(role)
}

/// 「한 단어」 계약의 강제 — **남길 글자를 정해** 그 밖을 버린다(금지 목록이 아니라 허용 구조).
///
/// ★실 입력에는 무동작이다(우리 생산자가 내는 role 은 영숫자·하이픈뿐). 그런데도 두는 이유:
/// 데몬은 role 문자열의 글자를 **검증하지 않는다**(`surface.create` 의 `--role` 은 임의 문자열 ·
/// 저장소 전수 grep 에서 role charset 검증 0건). 공백이 섞이면 제목 한 칸이 두 낱말이 되고,
/// 구분자(` · `)가 섞이면 **없던 칸이 하나 생겨** 모델 칸 판정(§retitle_with_model)이 엉뚱한
/// 조각을 집는다.
/// ★왜 「공백 제거」가 아니라 허용 구조인가(agy R1 문제점 2-3 수용): 제로폭 공백(U+200B)은
/// Rust 의 `is_whitespace` 가 공백으로 보지 않아 **눈에 안 보이는 특성**이 그대로 통과했다.
/// 금지 목록을 늘리는 길은 그런 글자가 나올 때마다 다시 뚫린다 — 남길 글자를 정하면 닫힌다.
/// 하이픈은 남긴다: `eduscan-daily` 같은 키워드는 공백이 없으므로 여전히 한 낱말이다.
fn one_word(s: &str) -> String {
    s.chars()
        .filter(|c| c.is_alphanumeric() || *c == '-' || *c == '_')
        .collect()
}

fn characteristic_inner(role: &str) -> String {
    let (head, tail) = split_role(role);
    // ★정화는 **조립 전**에 한다 — 뒤에 하면 `·` 같은 role 이 서수 `1` 만 남겨 「5 · 1」이 된다
    //   (지을 이름이 없는데 있는 척하는 것 = 없는 값을 지어내는 것).
    let (head, tail) = (one_word(head), one_word(tail));
    if head.is_empty() {
        return String::new(); // 지을 이름이 없다 → 호출자가 무접촉으로 간다
    }
    let (head, tail) = (head.as_str(), tail.as_str());
    let tail_is_ordinal = !tail.is_empty() && tail.chars().all(|c| c.is_ascii_digit());
    if head == "master" || head == "cso" {
        // master-2 → master2 · master → master (숫자 아닌 꼬리는 버린다 — 한 단어가 계약이다)
        return if tail_is_ordinal { format!("{head}{tail}") } else { head.to_string() };
    }
    if tail.is_empty() {
        return format!("{head}1"); // worker → worker1 · reviewer → reviewer1
    }
    if tail_is_ordinal {
        return format!("{head}{tail}"); // worker-3 → worker3
    }
    tail.to_string() // worker-eduscan → eduscan · reviewer-gemini → gemini
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

/// CLI `workflow_title()` 이 쓰는 cwd basename — **그 함수와 문자열 동형**이어야 한다
/// (src/bin/cys.rs `workflow_title`: 후행 구분자 트림 → 마지막 조각 → 빈 값·윈도 드라이브 루트 제외).
fn cwd_basename(cwd: Option<&str>) -> Option<&str> {
    cwd.map(|s| s.trim_end_matches(['/', '\\']))
        .and_then(|s| s.rsplit(['/', '\\']).next())
        .filter(|f| !f.is_empty())
        // 윈도 드라이브 루트(`C:\` → 트림 후 `C:`)는 폴더명이 아니다.
        .filter(|f| !(f.len() == 2 && f.ends_with(':') && f.as_bytes()[0].is_ascii_alphabetic()))
}

/// 기계가 지은 제목인가 — 「사람이 지은 이름」과 가르는 판정.
///
/// ★판정 방식 = **생산자 출력의 정확 재구성**이다(추측·접두 휴리스틱이 아니다). 두 생산자 모두
/// 이 저장소 안에 정의가 있다:
///   ⑴데몬 기본값 `surface {id}`(state.rs — title 미지정 시 · UI 의 `isAutoTitle` 과 같은 문자열).
///   ⑵CLI `workflow_title()`(src/bin/cys.rs) = `{role}-{agent}` 또는 `{role}-{agent} · {cwd basename}`.
///
/// ★agent 는 **선택**이다: 알면 그 이름 하나로, 모르면(현 launch-agent 페이로드 — §7-2 ⑵)
/// 닫힌 어휘 §AGENT_NAMES 를 차례로 넣어 재구성한다.
/// ★cwd 는 **알아보는 데만** 쓴다(특성을 짓는 데는 안 쓴다 — v1.1.1 규칙). 이 대조가 없으면
/// 사람이 지은 `worker-claude · 회의록` 이 기계 제목으로 오인돼 「회의록」이 지워진다
/// (agy R1 문제점 1 — 접두 휴리스틱의 실제 반례였다). 전체 일치는 그 방향을 구조적으로 막는다.
/// ★재구성이 빗나가면(다른 cwd·새 에이전트) 판정은 false 로 떨어져 제목이 **사람 이름처럼 보존**
/// 된다 — 길어질 뿐 잃는 것은 없다(안전 방향).
fn is_machine_title(title: &str, sid: u64, role: &str, agent: Option<&str>, cwd: Option<&str>) -> bool {
    if title == format!("surface {sid}") {
        return true;
    }
    let folder = cwd_basename(cwd);
    let single: [&str; 1];
    let names: &[&str] = match agent {
        Some(a) => {
            single = [a];
            &single
        }
        None => &AGENT_NAMES,
    };
    names.iter().any(|a| {
        let head = format!("{role}-{a}");
        title == head || folder.is_some_and(|f| title == format!("{head}{SEP}{f}"))
    })
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
    let want = characteristic(role);
    if want.is_empty() {
        // 지을 이름이 없으면 짓지 않는다(없는 값을 지어내지 않는다 — 모델 칸과 같은 원칙).
        return None;
    }
    let canonical = format!("{sid}{SEP}{want}");
    let machine = |t: &str| is_machine_title(t, sid, role, agent, cwd);
    match requested.map(str::trim).filter(|t| !t.is_empty()) {
        // ②이미 이 번호로 시작 = 멱등. 단 **번호 뒤가 기계 제목이면 단축**한다 — 1.1.0 이 지은
        // 「38 · Opus · master-claude · install-jarvis」가 번호를 갖고 있다는 이유로 영구히
        // 방치되면 이 티켓의 목적이 그 기기에서 달성되지 않는다(agy R1 문제점 3 수용).
        // 모델 칸은 있는 그대로 옮긴다(그 칸의 주인은 retitle_with_model 이다).
        Some(t) if starts_with_number(sid, t) => match split_number_and_model(t) {
            Some((model, body)) if machine(body) => {
                let next = join_title(sid, model, &want);
                (next != t).then_some(next)
            }
            _ => None,
        },
        // 기계가 지은 제목(데몬 기본값·CLI workflow_title) = 우리가 대체한다
        Some(t) if machine(t) => Some(canonical),
        // 다른 번호로 시작 = **낡은 번호**(다른 좌석에서 물려받은 제목·수기 이관). 번호 칸만
        // 갈아 끼우고 뒤는 원문 그대로 옮긴다 — 안 그러면 「60 · 285 · research」처럼 번호가 쌓인다.
        // 뒤가 기계 제목이면 그때도 규칙대로 다시 짓는다(위 ②와 같은 이유).
        Some(t) if stale_number_tail(t).is_some() => match stale_number_tail(t) {
            Some(tail) if !tail.is_empty() => Some(match split_model_head(tail) {
                (model, body) if machine(body) => join_title(sid, model, &want),
                _ => format!("{sid}{SEP}{tail}"),
            }),
            _ => Some(canonical),
        },
        // ④사람이 지은 이름 = 지우지 않는다. 번호만 앞에 붙인다.
        Some(t) => Some(format!("{sid}{SEP}{t}")),
        // 제목 미지정 = 규칙대로
        None => Some(canonical),
    }
}

/// 「번호 · [모델 ·] 본문」에서 모델 칸(있으면)과 본문을 갈라 준다. 번호가 없으면 None.
fn split_number_and_model(title: &str) -> Option<(Option<&str>, &str)> {
    let (_num, rest) = title.trim_start().split_once(SEP)?;
    Some(split_model_head(rest))
}

/// 첫 조각이 모델 칸이면 떼어 낸다.
fn split_model_head(rest: &str) -> (Option<&str>, &str) {
    match rest.split_once(SEP) {
        Some((head, tail)) if is_model_segment(head) => (Some(head), tail),
        _ => (None, rest),
    }
}

/// 「번호 · [모델 ·] 특성」 조립.
fn join_title(sid: u64, model: Option<&str>, characteristic: &str) -> String {
    match model {
        Some(m) => format!("{sid}{SEP}{m}{SEP}{characteristic}"),
        None => format!("{sid}{SEP}{characteristic}"),
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
    // ── v1.1.1 특성 규칙 표 (오너 원문 2026-09-21 08:2x · master 판정 [master#6f1fee58]) ──────
    // role × 키워드 유무 × 손수정 을 한 표로 잰다. 표가 곧 계약이다.

    #[test]
    fn v111_characteristic_table() {
        let cases: [(&str, &str); 15] = [
            // (role,            기대 특성)
            ("master", "master"),
            ("master-2", "master2"),
            ("master - 2", "master2"),     // head·tail trim (agy R1 2-1)
            ("cso", "cso"),
            ("cso-2", "cso2"),
            ("worker", "worker1"),         // 키워드 없음 → worker1
            ("worker-2", "worker2"),       // 서수 = 생성 순
            ("worker-3", "worker3"),
            ("worker-eduscan", "eduscan"), // 맡은 역할 키워드 1단어
            ("worker-research", "research"),
            ("worker-eduscan-daily", "eduscan-daily"), // 하이픈은 한 낱말의 일부
            ("reviewer", "reviewer1"),     // 다른 role · 키워드 없음
            ("reviewer-gemini", "gemini"), // master 판정 A 채택(문면 reviewer1 보다 규칙 우선)
            ("reviewer-codex", "codex"),
            ("worker-교육", "교육"),        // 비-ASCII 키워드는 보존된다(허용 구조 = 영숫자)
        ];
        for (role, want) in cases {
            assert_eq!(characteristic(role), want, "role={role}");
        }
    }

    #[test]
    fn v111_characteristic_is_one_word_always() {
        // 계약은 「한 단어」다 — 공백도 구분자도 보이지 않는 글자도 없어야 한다.
        // ★role 글자는 데몬이 검증하지 않는다(임의 문자열) — 그래서 이상한 role 도 함께 잰다.
        //   제로폭 공백(U+200B)은 Rust 의 is_whitespace 가 공백으로 보지 않는다(agy R1 2-3).
        for role in [
            "master", "cso", "worker", "worker-2", "worker-eduscan", "reviewer-gemini",
            "my worker", "worker- 2", "a · b", "worker-\u{a0}x", "worker-\u{200b}x", "worker-a\tb",
        ] {
            let c = characteristic(role);
            assert!(!c.contains(' '), "role={role:?} 특성에 공백: {c:?}");
            assert!(!c.contains(SEP), "role={role:?} 특성에 구분자: {c:?}");
            assert!(
                c.chars().all(|ch| ch.is_alphanumeric() || ch == '-' || ch == '_'),
                "role={role:?} 특성에 허용 밖 글자: {c:?}"
            );
        }
        // ★실 입력에는 무동작이다 — 정화가 정상 role 의 답을 바꾸지 않는다.
        assert_eq!(characteristic("worker-eduscan"), "eduscan");
        // 지을 이름이 하나도 안 남으면 빈 문자열 — initial_title 이 그때 무접촉으로 간다.
        assert_eq!(characteristic("·"), "");
        assert_eq!(initial_title(5, Some("·"), Some("/Users/x/y"), Some("surface 5"), None), None);
    }

    const CLAUDE: Option<&str> = Some("claude");
    const JARVIS: Option<&str> = Some("/Users/x/install-jarvis");

    // ── 양방향 강제발화 — 「반드시 바뀌어야 하는 것」과 「반드시 안 건드려야 하는 것」 ────────
    // 한쪽만 재면 아무것도 안 바꾸는 구현(또는 전부 덮는 구현)이 통과한다.

    #[test]
    fn v111_must_change_owner_observed_windows_titles() {
        // ★오너가 참가자 기기에서 실제로 본 제목(2026-09-21 08:15 윈 캡처) = 이 입력이다.
        //   agent 가 None 인 것이 그 기기의 실상이다(launch-agent 페이로드에 agent 키 없음).
        assert_eq!(
            initial_title(38, Some("master"), JARVIS, Some("master-claude · install-jarvis"), None)
                .as_deref(),
            Some("38 · master")
        );
        assert_eq!(
            initial_title(36, Some("cso"), JARVIS, Some("cso-claude · install-jarvis"), None)
                .as_deref(),
            Some("36 · cso")
        );
        assert_eq!(
            initial_title(37, Some("worker"), JARVIS, Some("worker-claude · install-jarvis"), None)
                .as_deref(),
            Some("37 · worker1")
        );
        // agent 를 아는 경로(정확 대조)도 같은 답을 낸다.
        assert_eq!(
            initial_title(41, Some("worker-eduscan"), Some("/Users/x/axdev/eduscan"),
                          Some("worker-eduscan-claude · eduscan"), CLAUDE).as_deref(),
            Some("41 · eduscan")
        );
        // ★1.1.0 결함의 직접 강제발화 — cwd 로 **특성을 짓는** 구현이었다면 폴더명이 여기 남는다.
        assert_eq!(
            initial_title(73, Some("worker"), Some("/Users/x/cys-terminal-src"),
                          Some("worker-claude · cys-terminal-src"), CLAUDE).as_deref(),
            Some("73 · worker1")
        );
        // 폴더를 알 수 없어 role-agent 만 있는 판본(workflow_title 의 폴백)
        assert_eq!(
            initial_title(12, Some("worker-2"), Some("/"), Some("worker-2-claude"), CLAUDE).as_deref(),
            Some("12 · worker2")
        );
    }

    #[test]
    fn v111_must_change_legacy_numbered_title_is_shortened() {
        // ★1.1.0 이 지은 네 칸 제목은 **번호를 갖고 있다** — 그 이유로 영구 방치되면 이 티켓의
        //   목적이 그 기기에서 달성되지 않는다(agy R1 문제점 3 수용). 모델 칸은 그대로 옮긴다.
        assert_eq!(
            initial_title(38, Some("master"), JARVIS,
                          Some("38 · Opus · master-claude · install-jarvis"), None).as_deref(),
            Some("38 · Opus · master")
        );
        // 모델 칸이 없던 판본도 같은 자리에서 단축된다.
        assert_eq!(
            initial_title(37, Some("worker"), JARVIS,
                          Some("37 · worker-claude · install-jarvis"), None).as_deref(),
            Some("37 · worker1")
        );
        // 낡은 번호 + 기계 꼬리도 규칙대로 다시 짓는다(번호는 내 것으로).
        assert_eq!(
            initial_title(60, Some("worker"), JARVIS,
                          Some("285 · Opus · worker-claude · install-jarvis"), None).as_deref(),
            Some("60 · Opus · worker1")
        );
    }

    #[test]
    fn v111_must_change_daemon_default_title() {
        // 데몬 기본값 `surface {id}` — GUI·수동 생성 좌석이 여기 해당한다.
        assert_eq!(
            initial_title(874, Some("worker-5"), Some("/Users/x/axdev/.wt/cys-seat-folders"),
                          Some("surface 874"), CLAUDE).as_deref(),
            Some("874 · worker5")
        );
    }

    #[test]
    fn v111_must_change_no_title_requested() {
        assert_eq!(
            initial_title(44, Some("master"), JARVIS, None, None).as_deref(),
            Some("44 · master")
        );
        assert_eq!(
            initial_title(45, Some("reviewer-codex"), JARVIS, None, Some("codex")).as_deref(),
            Some("45 · codex")
        );
    }

    #[test]
    fn v111_must_change_stale_number_is_swapped_not_stacked() {
        // 다른 좌석의 번호를 물고 온 제목 — 번호 칸만 갈린다(번호가 쌓이면 안 된다).
        assert_eq!(
            initial_title(60, Some("worker-2"), Some("/Users/x/research"), Some("285 · research"),
                          CLAUDE).as_deref(),
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
            initial_title(62, Some("worker"), Some("/Users/x/research"), Some("285"), CLAUDE)
                .as_deref(),
            Some("62 · worker1")
        );
    }

    #[test]
    fn v111_must_not_change_roleless_surface() {
        // ①역할 없는 GUI 셸 — UI 가 live_cwd 를 실시간 표시한다. 제목을 박으면 그 추적이 죽는다.
        assert_eq!(initial_title(7, None, Some("/Users/x/anywhere"), Some("surface 7"), None), None);
        assert_eq!(initial_title(8, Some(""), Some("/Users/x/anywhere"), Some("surface 8"), None), None);
        assert_eq!(initial_title(9, Some("   "), Some("/Users/x/anywhere"), None, None), None);
    }

    #[test]
    fn v111_must_not_change_already_numbered() {
        // ②멱등 — 우리 기기 javis_panetitle.py 가 먼저 붙인 제목(cwd 규칙)과 충돌 0.
        assert_eq!(
            initial_title(874, Some("worker-5"), Some("/Users/x/axdev/.wt/cys-seat-folders"),
                          Some("874 · Opus · cys-seat-folders"), CLAUDE),
            None
        );
        assert_eq!(
            initial_title(11, Some("worker"), Some("/Users/x/y"), Some("11"), CLAUDE),
            None
        );
        // 규칙이 이미 완성된 제목도 그대로다(두 주인이 서로를 지우지 않는다).
        assert_eq!(
            initial_title(38, Some("master"), JARVIS, Some("38 · Opus · master"), CLAUDE),
            None
        );
    }

    #[test]
    fn v111_must_not_change_user_named_title_keeps_its_words() {
        // ④사람이 지은 이름 — 이미 번호가 있으면 통째로 보존.
        assert_eq!(
            initial_title(297, Some("worker"), Some("/Users/x/cys-terminal-src"),
                          Some("297 박사님 지시 대기창"), CLAUDE),
            None
        );
        // 번호가 없으면 **지우지 않고 번호만 앞에 붙인다**(지우는 구현이었다면 여기서 빨개진다).
        assert_eq!(
            initial_title(60, Some("worker"), Some("/Users/x/research"), Some("내 작업창"), CLAUDE)
                .as_deref(),
            Some("60 · 내 작업창")
        );
        // ★생산자 출력 **정확 재구성**의 존재 이유(agy R1 문제점 1) — 접두 휴리스틱이었다면
        //   이 사람 이름이 「60 · worker1」로 지워지고 「회의록」이 사라진다.
        assert_eq!(
            initial_title(60, Some("worker"), JARVIS, Some("worker-claude · 회의록"), None).as_deref(),
            Some("60 · worker-claude · 회의록")
        );
        assert_eq!(
            initial_title(60, Some("worker"), JARVIS, Some("worker-메모"), None).as_deref(),
            Some("60 · worker-메모")
        );
        // 번호가 이미 있는 사람 이름도 단축 대상이 아니다(번호 뒤가 기계 제목이 아니다).
        assert_eq!(
            initial_title(60, Some("worker"), JARVIS, Some("60 · worker-claude · 회의록"), None),
            None
        );
    }

    #[test]
    fn v111_number_boundary_is_not_a_prefix_match() {
        // ★비대칭을 둘 다 잰다. 접두 일치로 완화한 구현은 **이 방향에서만** 빨개진다:
        //   sid=87 이 「874 · …」를 「이미 내 번호로 시작한다」고 읽어 남의 번호를 그대로 둔다.
        assert_eq!(
            initial_title(87, Some("worker"), Some("/Users/x/research"), Some("874 · research"),
                          CLAUDE).as_deref(),
            Some("87 · research")
        );
        assert_eq!(
            initial_title(874, Some("worker"), Some("/Users/x/research"), Some("87 · research"),
                          CLAUDE).as_deref(),
            Some("874 · research")
        );
        // 경계가 공백이면 내 번호다 — 무접촉.
        assert_eq!(
            initial_title(87, Some("worker"), Some("/Users/x/research"), Some("87 · research"), CLAUDE),
            None
        );
    }

    #[test]
    fn v111_hands_off_to_the_model_owner() {
        // create 시점에는 모델 관측이 없다 — 번호·특성만 세우고, 첫 statusline 턴에 모델 칸이 붙는다.
        let created =
            initial_title(38, Some("master"), JARVIS, Some("master-claude · install-jarvis"), None)
                .unwrap();
        assert_eq!(created, "38 · master");
        assert_eq!(
            retitle_with_model(&created, Some("Claude Opus 5")).as_deref(),
            Some("38 · Opus · master")
        );
        // 그리고 그 결과는 다시 무접촉이다(두 주인이 서로를 지우지 않는다).
        assert_eq!(
            initial_title(38, Some("master"), JARVIS, Some("38 · Opus · master"), CLAUDE),
            None
        );
    }
}
