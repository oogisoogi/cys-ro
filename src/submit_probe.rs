//! 제출 실측 판정기 — `cys`(CLI)와 `cysd`(데몬)가 **같은 술어**를 쓰도록 둔 공용 모듈.
//!
//! 무언가를 좌석 입력줄에 주입한 뒤 「제출됐다」·「제출 안 됐다」·「못 쟀다」를 배타적으로 가른다
//! (추정 금지). 원형은 `src/bin/cys.rs` 의 `SubmitProbe`/`submit_probe`/`input_region_anchored`
//! 이고, 그 셋을 여기로 올리면서 현행 Claude Code 입력창 앵커(`❯`)를 더했다 — 지금 Claude Code
//! 입력창은 가로줄(────) 사이의 「❯ 」 한 줄이라 옛 앵커(`╭`·줄머리 `> `)만으로는 늘 `Unmeasured`
//! 였다(09-21 실기). 두 바이너리가 각자 사본을 들면 한쪽만 고쳐지는 표류가 나므로 사본을 두지 않는다.

/// 제출 실측 3상태.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum SubmitProbe {
    /// 입력창 앵커를 찾았고 그 안에 sentinel 이 없다 = 제출 실측.
    Submitted,
    /// 입력창 앵커를 찾았고 그 안에 sentinel 이 잔류한다 = 미제출 실측.
    NotSubmitted,
    /// 입력창 앵커를 못 찾았다 = 측정 실패. **미제출과 구별되는 별도 상태**다.
    Unmeasured,
}

/// 현행 Claude Code 입력줄 앵커(agents.json claude `ready_marker` 와 같은 글자).
pub const CHEVRON_ANCHOR: char = '❯';

/// Claude Code 가 긴 붙여넣기를 입력창에 접어 보여 줄 때의 표지(`[Pasted text #1 +N lines]`).
/// 입력창 안에 이것이 보이면 본문(sentinel)이 화면에 없어도 **아직 보내지 않은 글**이다 —
/// 복원 첫 기동(절대지침 전문 + [RESTORE] 한 전송)이 정확히 이 모양이다(891 지적 · 09-21).
pub const PASTED_FOLD_MARK: &str = "[Pasted text";

/// 화면에서 「현재 입력창 영역」을 잘라낸다 — 마지막 입력 앵커(입력 박스 상단 `╭` · 줄머리 `> `
/// 프롬프트 · `❯`) 이후 끝까지. 반환 = (영역, **앵커를 실제로 찾았는가**). 앵커가 없으면 전체
/// 화면을 돌려주지만 그때의 매치는 「입력창에 잔류한다」가 아니라 「입력창이 어디인지 모른다」다.
pub fn input_region_anchored(screen: &str) -> (&str, bool) {
    let box_top = screen.rfind('╭');
    let prompt = if screen.starts_with("> ") {
        Some(0)
    } else {
        screen.rfind("\n> ").map(|i| i + 1)
    };
    let chevron = screen.rfind(CHEVRON_ANCHOR);
    match box_top.into_iter().chain(prompt).chain(chevron).max() {
        Some(i) => (&screen[i..], true),
        None => (screen, false),
    }
}

/// 제출 여부 실측 — 반환 = (3상태, 의심 여부). `의심` = 화면 어디든 sentinel 이 공백 제거 매치 →
/// **행동**(Return 재전송)의 트리거로만 쓰고 **판정**에는 쓰지 않는다(`cys.rs` 원형과 같은 계약).
pub fn submit_probe(screen: &str, sentinel: &str) -> (SubmitProbe, bool) {
    let needle = flat(sentinel);
    if needle.is_empty() {
        return (SubmitProbe::Unmeasured, false);
    }
    let suspect = flat(screen).contains(&needle);
    let (region, anchored) = input_region_anchored(screen);
    if !anchored {
        return (SubmitProbe::Unmeasured, suspect);
    }
    // 접힌 붙여넣기 — sentinel 대조보다 앞이다(본문이 화면에 없으니 대조는 늘 「제출」로 틀린다).
    if flat(region).contains(&needle) || region.contains(PASTED_FOLD_MARK) {
        (SubmitProbe::NotSubmitted, true)
    } else {
        (SubmitProbe::Submitted, false)
    }
}

/// 입력줄이 비었는가 — `Some(true)` 비었다 · `Some(false)` 무언가 있다 · `None` 못 쟀다(앵커 없음).
/// 앵커가 있는 **그 한 줄**만 본다(입력창 아래 상태표시줄은 입력이 아니다). 테두리 글자·앵커 자체는
/// 내용으로 세지 않는다.
pub fn input_line_empty(screen: &str) -> Option<bool> {
    let (region, anchored) = input_region_anchored(screen);
    if !anchored {
        return None;
    }
    let first = region.lines().next().unwrap_or("");
    let content: String = first
        .chars()
        .filter(|c| !c.is_whitespace() && !matches!(c, '╭' | '╮' | '│' | '─' | '>' | '❯'))
        .collect();
    Some(content.is_empty())
}

fn flat(t: &str) -> String {
    t.chars().filter(|c| !c.is_whitespace()).collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    const LINE: &str = "[cys-감시] surface:47(worker) 확인하라";

    fn claude_screen(input: &str) -> String {
        format!("이전 대화\n● 응답\n────────────\n❯ {input}\n────────────\n  ⏵⏵ bypass permissions on\n")
    }

    #[test]
    fn chevron_input_box_is_an_anchor() {
        assert_eq!(submit_probe(&claude_screen(LINE), LINE).0, SubmitProbe::NotSubmitted);
        let sent = format!("> {LINE}\n● 처리 중\n{}", claude_screen(""));
        assert_eq!(submit_probe(&sent, LINE), (SubmitProbe::Submitted, false));
    }

    #[test]
    fn legacy_anchors_keep_their_verdicts() {
        let boxed = format!("위\n╭───╮\n│ > {LINE} │\n╰───╯");
        assert_eq!(submit_probe(&boxed, LINE).0, SubmitProbe::NotSubmitted);
        let bare = format!("출력\n> {LINE}");
        assert_eq!(submit_probe(&bare, LINE).0, SubmitProbe::NotSubmitted);
    }

    #[test]
    fn no_anchor_is_unmeasured_not_unsubmitted() {
        let (p, suspect) = submit_probe(&format!("앵커 없는 화면 {LINE}"), LINE);
        assert_eq!(p, SubmitProbe::Unmeasured);
        assert!(suspect, "의심 신호는 행동용으로 살아 있어야 한다");
        assert_eq!(submit_probe("x", "   ").0, SubmitProbe::Unmeasured);
    }

    #[test]
    fn folded_paste_in_the_input_box_is_not_submitted() {
        // sentinel 본문은 화면 어디에도 없다 — 접힌 표지만 입력창에 있다.
        let folded = claude_screen("[Pasted text #1 +214 lines]");
        assert_eq!(submit_probe(&folded, LINE).0, SubmitProbe::NotSubmitted);
        assert_eq!(input_line_empty(&folded), Some(false));
        // 대조군: 같은 표지가 입력창 **위**(이미 보낸 대화)에만 있으면 제출이다.
        let sent = format!("> [Pasted text #1 +214 lines]\n● 처리 중\n{}", claude_screen(""));
        assert_eq!(submit_probe(&sent, LINE).0, SubmitProbe::Submitted);
    }

    #[test]
    fn input_line_empty_reads_only_the_anchor_line() {
        assert_eq!(input_line_empty(&claude_screen("")), Some(true));
        assert_eq!(input_line_empty(&claude_screen("미제출 지시")), Some(false));
        assert_eq!(input_line_empty("앵커 없음"), None);
    }
}
