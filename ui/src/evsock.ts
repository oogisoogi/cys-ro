// 데몬 이벤트의 출처 소켓 판정 — 종료 소식(surface.exited/closed/reaped)으로 죽은 창을 지울 때
// 「어느 작업공간의 창인가」를 정하는 **판정부**(TICKET=cys-117-exitedpane-b1).
//
// ★왜 순수 모듈인가: 백엔드 전달기는 본부(기본) 데몬 이벤트에도 socket_slug 를 붙인다(main.rs
//   spawn_event_forwarder · 06-20 F3). 화면의 socketForSlug 표에는 부서 데몬 식별표만 들어가므로,
//   main.ts 처리기 안의 한 줄 판정이 본부 이벤트를 「미해결 식별표」로 보고 조기 return 했다 —
//   「종료 즉시 창 제거」가 본부에서 06-20 부터 한 번도 돌지 않았는데 아무 시험도 빨개지지 않았다.
//
// 판정 규칙(F4 보호 유지):
//   · 식별표 없음 → 기본 데몬(하위호환 · socket = undefined)
//   · 부서 표에 있음 → 그 부서 소켓
//   · 기본 데몬 식별표와 같음 → 본부(socket = undefined)
//   · 그 밖(알 수 없는 식별표) → 처리하지 않는다 — 기본 데몬으로 폴백하면 타 부서 같은 번호 창을 지운다.

export type EventSock = { ok: true; socket: string | undefined } | { ok: false };

export function eventSock(
  slug: unknown,
  deptSockets: ReadonlyMap<string, string>,
  defaultSlug: string | null,
): EventSock {
  if (!slug) return { ok: true, socket: undefined };
  const sock = deptSockets.get(String(slug));
  if (sock) return { ok: true, socket: sock };
  if (defaultSlug && String(slug) === defaultSlug) return { ok: true, socket: undefined };
  return { ok: false };
}
