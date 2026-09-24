// exitbanner.ts — 좌석 종료 배너 「[surface exited]」 를 화면 **내용 맨 아래**에 쓰는 순서·위치 (TICKET=v116-exited-banner)
//
// ★왜 커서 자리가 아닌가(박사님 09-24 「맨 아래가 아니라 중간에 나온다」 · 헤드리스 c17 재현):
//   종전 배너는 `\r\n` 으로 **커서가 있던 줄의 다음 줄**에 쓰였다. 좌석 프로그램이 커서를 화면 중간
//   (Claude Code 입력 상자 · 대체 화면 TUI 의 입력 칸)에 둔 채 끝나면, 그 아래 테두리·안내 줄 위에
//   배너가 덮어써져 중간에 떴다. 대조군(커서 위치만 바꿈)에서 배너가 맨 아래로 가는 것을 확인했다.
// ★왜 대체 화면을 풀지 않는가(1049l 미포함 — trackfilter reset 과 같은 편): 풀면 죽은 TUI 의 마지막
//   화면(오류 문구일 수 있다)이 사라지고 옛 주 화면이 나온다. 배너는 지금 보이는 화면의 내용 뒤에 붙인다.

const BANNER_TEXT = "\x1b[31m[surface exited]\x1b[0m";
export const EXITED_BANNER = `\r\n${BANNER_TEXT}\r\n`;
// 대체 화면이 가득(마지막 행에 내용)일 때의 판 — 배너 자리를 만드는 앞 줄바꿈 1번만. 대체 화면엔 스크롤백이 없어
// 마지막 행에서의 줄바꿈 1번마다 맨 윗줄이 영구히 사라진다 — 가득일 때 1줄이 최소 손실이다(opus 적대 1R MINOR-1: 종전 2줄).
export const EXITED_BANNER_ALT_LAST = `\r\n${BANNER_TEXT}`;

// 배너 앞에 푸는 상태 — 죽은 앱이 남긴 스크롤 영역(DECSTBM)이 있으면 절대 좌표 이동이 영역 안에 갇히거나
// (원점 모드 DECOM 이 켜진 경우) 영역 밖 마지막 줄의 줄바꿈이 스크롤되지 않아 배너가 그 줄을 덮어쓴다.
// 영역을 전체 화면으로 되돌리면 DECOM 이 켜져 있어도 원점 = 1행이라 따로 끄지 않는다(헤드리스 ⒠ 로 확인 —
// `ESC[?6l` 을 더한 판과 결과 같음). 종료 이벤트 뒤에는 같은 터미널에 출력이 다시 오지 않는다(makePane 멱등 ·
// 스트림은 makePane 에서만 시작) — 그래서 이 해제가 산 앱의 그리기를 깨지 않는다. 커서를 원점으로 보내므로 이동은 늘 쓴다.
const RESET_MARGINS = "\x1b[r";

export type ScreenView = { rows: number; cursorY: number; line: (y: number) => string; alt?: boolean };

// y > above 인 행 중 마지막 내용 줄 — 없으면 above.
function lastContentRow(v: ScreenView, above: number): number {
  for (let y = v.rows - 1; y > above; y--) {
    if (v.line(y).trim() !== "") return y;
  }
  return above;
}

/// (주 화면) 배너 바로 앞 줄(0-기준 화면 행) — 커서 줄과 「그 아래 마지막 내용 줄」 중 더 아래.
/// 커서 아래에 내용이 없으면 커서 줄 그대로(종전과 같은 자리 — 멀쩡한 화면은 바뀌지 않는다).
export function bannerRow(v: ScreenView): number {
  return lastContentRow(v, v.cursorY);
}

/// 주 화면 = 종전 배너(앞뒤 줄바꿈)를 bannerRow 뒤에 — 밀려난 줄은 스크롤백으로 간다.
/// 대체 화면 = 커서와 무관하게 「마지막 내용 줄 바로 다음 행」에 줄바꿈 없이 쓴다 — 스크롤백이 없어 줄바꿈이 곧
/// 윗줄 영구 손실이기 때문이다(opus 2R MINOR-3 · agy 2R: 마지막 행이 비었는데 뒤 줄바꿈·커서 줄 줄바꿈으로 1줄을 잃던 경우).
/// 가득일 때만 앞 줄바꿈 1번(최소 손실 1줄). 죽은 창이라 배너 뒤 커서 자리는 쓸모가 없다.
export function exitedBannerSeq(v: ScreenView): string {
  if (v.alt) {
    const last = lastContentRow(v, -1);
    if (last === v.rows - 1) return `${RESET_MARGINS}\x1b[${v.rows};1H${EXITED_BANNER_ALT_LAST}`;
    return `${RESET_MARGINS}\x1b[${last + 2};1H${BANNER_TEXT}`;
  }
  return `${RESET_MARGINS}\x1b[${bannerRow(v) + 1};1H${EXITED_BANNER}`;
}

type Line = { translateToString(trimRight?: boolean): string };
export type ExitTerm = {
  rows: number;
  buffer: { active: { type?: string; baseY: number; cursorY: number; getLine(y: number): Line | undefined } };
  write(data: string | Uint8Array, callback?: () => void): void;
};
export type ExitFilter = { flush(): Uint8Array; reset(): string };

/// 종료 쓰기 순서(스펙 D4 ③ 유지): ①필터 잔여 carry 방류 ②정합기 reset(필터 우회 직접 기록) ③배너.
/// ③의 위치 판독은 ①②와 앞서 대기열에 쌓인 출력이 **해석된 뒤**(write 콜백)에 한다 — 먼저 읽으면
/// 아직 그려지지 않은 화면을 보고 틀린 줄을 고른다. 판독이 실패해도(창 파괴 등) 배너는 1회 쓴다.
export function writeExitedBanner(term: ExitTerm, filter: ExitFilter, done?: () => void): void {
  const rest = filter.flush();
  if (rest.length > 0) term.write(rest);
  term.write(filter.reset(), () => {
    let seq = EXITED_BANNER;
    try {
      const buf = term.buffer.active;
      seq = exitedBannerSeq({ rows: term.rows, cursorY: buf.cursorY, line: (y) => buf.getLine(buf.baseY + y)?.translateToString(true) ?? "", alt: buf.type === "alternate" });
    } catch {
      /* 판독 실패 — 종전 자리(커서 다음 줄)로 강등 */
    }
    term.write(seq, done);
  });
}
