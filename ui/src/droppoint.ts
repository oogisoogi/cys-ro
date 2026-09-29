// (1.1.7 ② · TICKET=cysr-117-impl-brand) OS 파일 드롭 좌표 → CSS px 환산(순수 · DOM 무접촉).
//
// ★플랫폼마다 단위가 다르다(Cargo.lock 의 wry 0.55.1 · tauri-runtime-wry 2.11.2 소스 실측):
//   · macOS — wry `wkwebview/drag_drop.rs` 가 `draggingLocation()`(포인트 = CSS px)을 그대로 싣는다.
//     tauri-runtime-wry `lib.rs` 는 환산 없이 `PhysicalPosition` 이라는 **이름만** 붙인다.
//     ⇒ 여기서 devicePixelRatio 로 또 나누면 Retina(2배)에서 좌표가 절반이 되어 오른쪽 창에 놓은 파일이
//       왼쪽 창으로 간다(오배달).
//   · Windows — wry `webview2/drag_drop.rs` 가 클라이언트 **물리 픽셀**을 싣는다 ⇒ dpr 로 나눈다(종전 동작).
//   · 그 밖(리눅스 등) — 실기 근거가 없어 종전 동작(나눔)을 유지한다.
export function dropPointToCss(
  pos: { x: number; y: number } | undefined,
  dpr: number | undefined,
  isMac: boolean,
): { x: number; y: number } | undefined {
  if (!pos) return undefined;
  if (isMac) return { x: pos.x, y: pos.y };
  const d = typeof dpr === "number" && Number.isFinite(dpr) && dpr > 0 ? dpr : 1;
  return { x: pos.x / d, y: pos.y / d };
}
