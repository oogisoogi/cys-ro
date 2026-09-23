// 출력 따라가기(바닥 고정) 판정 — 순수 모듈. DOM·xterm·Tauri 0줄(유닛 테스트가 이 파일을 그대로 부른다).
//
// ★v115-restore(B1 ①): 옛 배선은 휠 이벤트마다 rAF 에서 `follow = atBottom()` 으로 재판정했다.
// 트랙패드의 소량 델타(1줄 미만)는 첫 프레임에 뷰포트가 안 움직여 atBottom()=true 가 되고, 그 즉시
// follow 가 되살아나 스트리밍 write 의 바닥 스냅이 사용자를 끌어내렸다(「위로 못 올라간다」).
// 새 계약: 위로 휠을 준 뒤에는 「아래로 휠(그 뒤 바닥 실측) 또는 키 입력」이 있을 때만 재고정한다.

/**
 * 휠 한 번(또는 키 입력 한 번)이 처리된 뒤의 follow 값.
 * @param prevFollow 직전 follow
 * @param deltaY 이 휠의 deltaY(키 입력이면 무시) — 음수 = 위로, 양수 = 아래로, 0 = 가로 휠
 * @param atBottom xterm 이 휠을 처리한 뒤(rAF) 뷰포트가 바닥인가
 * @param keyInput 사용자 키 입력(프롬프트 사용 의사)인가
 */
export function nextFollow(prevFollow: boolean, deltaY: number, atBottom: boolean, keyInput: boolean): boolean {
  if (keyInput) return true;
  if (deltaY < 0) return false; // 위로 = 해제 유지 — 첫 프레임 atBottom 을 믿지 않는다
  if (deltaY > 0) return prevFollow || atBottom; // 아래로 = 바닥에 닿았을 때 재고정
  return prevFollow; // 가로 휠 = 무변
}

/** B1 ② 안내 문구 — 처음 쓰는 사람이 읽는다(내부 용어 0). */
export const FOLD_HINT_TITLE = "더 위의 내용";
export const FOLD_HINT_BODY = "더 위의 내용은 클로드가 접어 두었습니다 — Ctrl+O 로 전체 보기";

/**
 * 「맨 위 도달」 안내를 지금 띄울까. 앱 세션당 1회.
 * ★(v116-ui-close · D4 #6) 올라갈 **위 내용이 실제로 있었을 때만** — `baseY > 0`(스크롤된 줄이 있다) · 일반 화면(normal)
 *   버퍼. 종전엔 `viewportY <= 0` 만 봐서, 스크롤백이 없는 짧은 셸·vim·less 창에서 **첫 위 휠 한 번**에 곧바로
 *   「클로드가 접어 두었습니다」가 떴다(클로드와 무관한 창에서도) — 그리고 세션당 1회 몫을 써 버려, 정작 필요한
 *   때(긴 클로드 출력의 맨 위)엔 안 떴고 대체 화면 전용 안내(altscroll)의 자리도 먼저 차지했다.
 * @param alreadyShown 이 세션에서 이미 띄웠는가
 * @param deltaY 이 휠의 deltaY
 * @param viewportY xterm 이 휠을 처리한 뒤의 뷰포트 첫 줄(0 = 스크롤백 맨 위)
 * @param baseY 스크롤백 줄 수(0 = 위로 올라갈 내용 없음)
 * @param bufferType 활성 버퍼("normal" | "alternate") — 대체 화면은 altscroll 안내 소관
 */
export function shouldShowFoldHint(
  alreadyShown: boolean,
  deltaY: number,
  viewportY: number,
  baseY: number,
  bufferType: string,
): boolean {
  return !alreadyShown && deltaY < 0 && viewportY <= 0 && baseY > 0 && bufferType === "normal";
}
