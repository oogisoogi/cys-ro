// 전문가 모드 — 조직 단추(▶CEO·▶부서장·＋부서)를 기본 화면에서 치우는 설정의 **판정부**.
// (박사님 판정 2026-09-20 = 854 보고서 권고 ⓑ′ 그대로 · TICKET=v110-sidebar)
//
// ★왜 순수 모듈인가: 「기본값이 꺼짐이다」는 화면을 열어 봐야 아는 사실이 아니라 **판정 한 줄**이다.
//   main.ts 안에서 localStorage 를 직접 비교하면 그 한 줄을 기계가 잴 수 없고(DOM·Tauri 필요),
//   기본값이 조용히 뒤집혀도 아무 시험이 빨개지지 않는다. 그래서 읽기·쓰기 둘 다 여기로 모은다.
//
// ★저장값을 불리언이 아니라 문자열로 다루는 이유: localStorage 는 문자열만 담고, 빈 문자열·"false"·
//   "undefined"·옛 판본이 남긴 쓰레기 값이 실제로 들어온다. 「참인 값의 목록」을 정확히 하나("1")로
//   좁히고 나머지 전부를 꺼짐으로 접으면, 읽히지 않는 값이 **안전한 쪽(꺼짐)** 으로 떨어진다.

/** localStorage 키 — 이 키 하나가 전문가 모드의 전부다(설정 파일·데몬 상태 없음). */
export const EXPERT_KEY = "cys-expert-mode";

/**
 * 저장된 원시 문자열 → 켜짐 여부.
 * 기본값은 **꺼짐**이다: 미설정(null)·빈 값·해석 불가 값은 전부 false 로 접힌다.
 * ⚠ "true"·"on"·"yes" 를 참으로 받아 주지 않는다 — 참인 표기를 늘리면 「무엇이 저장돼 있으면
 *   켜지는가」가 두 곳(여기와 쓰는 쪽)에서 갈리고, 그 갈림은 화면에만 나타난다.
 */
export function expertModeOn(raw: string | null | undefined): boolean {
  return raw === "1";
}

/** 켜짐 여부 → 저장할 원시 문자열. expertModeOn 과 왕복이 성립해야 한다(시험이 그 왕복을 잰다). */
export function expertModeRaw(on: boolean): string {
  return on ? "1" : "0";
}
