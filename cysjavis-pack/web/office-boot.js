/* office-boot.js — 오피스 HUD 조용한 실패 제거 (W1-c · classic script, 모듈 아님)
 *
 * office3d.html의 ES 모듈 첫 줄 `import * as THREE from '/vendor/three.module.js'`가
 * 404면 모듈 전체가 죽어 "연결 중…" 정적 텍스트만 남는 침묵 실패가 됐다(실사고).
 * 이 스크립트는 브리지가 </head> 직전에 주입하는 classic script로, 그 침묵을 깨고
 * 복구 안내 배너를 띄운다. 외부 의존 0 · office3d.html 본문 무접촉.
 *
 * THREE 성공 신호(본문 무접촉): office3d.html은 <canvas id="scene">를 정적으로
 * 항상 포함하므로(본문 118행) '캔버스 존재'는 성공 신호가 될 수 없다. 대신
 * renderer.setSize(innerWidth,innerHeight)(본문 325·329행)가 성공 시 캔버스의
 * 인라인 style.width를 '<px>'로, 백버퍼 width를 화면폭*pixelRatio(>300)로 채운다 —
 * 둘 다 비파괴 판독이 가능한 성공 지문이다.
 */
(function () {
  "use strict";

  // iframe(CC 임베드) 이중 표출 가드 — 최상위 프레임에서만 동작
  if (window.top !== window) return;

  var BANNER_ID = "office-boot-banner";
  var MSG = "⚠ 오피스 자산 유실 — " +
            "터미널에서  cysr init-pack --force  " +
            "실행 후 새로고침";

  // THREE 렌더 성공 여부 — setSize가 남기는 비파괴 지문으로 판정(본문 무접촉)
  function threeIsUp() {
    var c = document.getElementById("scene") ||
            (document.querySelector ? document.querySelector("canvas") : null);
    if (!c) return false;
    var styled = c.style && c.style.width !== "" && c.style.width != null;
    var buffered = typeof c.width === "number" && c.width > 300;
    return !!(styled || buffered);
  }

  function showBanner() {
    if (!document.body) {  // <head> 실행 시점엔 body 미파싱 — DOM 준비 후 재시도
      document.addEventListener("DOMContentLoaded", showBanner, { once: true });
      return;
    }
    if (document.getElementById(BANNER_ID)) return;   // 중복 생성 가드
    if (threeIsUp()) return;                           // 그새 렌더됐으면 취소

    var b = document.createElement("div");
    b.id = BANNER_ID;
    b.setAttribute("role", "alert");
    b.textContent = MSG;
    var s = b.style;
    s.position = "fixed";
    s.top = "0";
    s.left = "0";
    s.right = "0";
    s.zIndex = "2147483647";
    s.padding = "12px 16px";
    s.background = "#7a1420";
    s.color = "#ffe8ea";
    s.font = "600 14px/1.4 'SF Mono',Menlo,monospace";
    s.textAlign = "center";
    s.letterSpacing = "0.02em";
    s.boxShadow = "0 2px 12px rgba(0,0,0,.5)";
    s.borderBottom = "1px solid #b0303f";
    document.body.appendChild(b);
  }

  // 빠른 경로: 모듈/자산 로드 실패 포착. 리소스 로드 에러는 window.onerror로
  // 버블하지 않으므로 캡처 단계 리스너로 잡는다(three.module.js 404 포함).
  // 리소스 로드 에러는 message가 없다 — 런타임 예외(message 有)와 구별해
  // 자산 로드 실패만 즉시 배너 트리거하고, 실제 렌더 성공 시엔 무시한다.
  window.addEventListener("error", function (e) {
    var isResourceError = e && !e.message &&
      e.target && e.target !== window &&
      (e.target.tagName === "SCRIPT" || e.target.tagName === "LINK" ||
       e.target.src || e.target.href);
    if (isResourceError && !threeIsUp()) showBanner();
  }, true);

  // 백스톱: 3초 내 THREE 미렌더면(에러 이벤트 무발생 침묵 실패 포함) 배너.
  setTimeout(function () {
    if (!threeIsUp()) showBanner();
  }, 3000);
})();
