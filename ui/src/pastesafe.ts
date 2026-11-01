// 사람 붙여넣기 본문 살균 — 순수 함수(main.ts 는 배선만 한다 · pastesafe.test.ts 가 고정).
//
// 【왜】 xterm.js 의 term.paste 는 줄바꿈 변환과 앞뒤 표지 부착만 하고 본문을 보지 않는다(5.5.0 · 6.0.0 동일).
// 그래서 복사한 글에 눈에 안 보이는 `ESC[201~` 가 있으면 괄호 붙여넣기가 거기서 끝나고 뒤 글자가 키 입력이 된다.
// `^C` 를 끼워도 같다. 격리 zsh 5.9 에서 둘 다 명령이 실행됐다(TICKET=cysr-ghsa-check · Ghostty GHSA-4jxv 부류).
// 기계 주입 경로의 src/paste_fence.rs 는 이 길을 지나지 않는다.
//
// 【무엇을】 C0 제어문자(탭·LF·CR 제외) · DEL · C1(U+0080~009F)을 공백으로 바꾼다. ESC 와 U+009B 가 사라지므로
// 7비트·8비트 표지가 함께 무력화된다. 지우지 않고 공백으로 두는 것은 앞뒤 글자가 붙어 새 낱말이 되지 않게 하기 위해서다.
//
// 【안 하는 것】 줄바꿈은 남긴다. 괄호 붙여넣기를 안 쓰는 프로그램에 줄바꿈을 붙여넣으면 그대로 실행된다
// (Ghostty GHSA-4hwh 부류 · 확인 창은 이 단위 범위 밖).
const PASTE_UNSAFE = /[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]/g;

export function sanitizePaste(text: string): string {
  return text.replace(PASTE_UNSAFE, " ");
}
