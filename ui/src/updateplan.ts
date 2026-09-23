// 업데이트 분기 판정 — 순수 함수 (옵션 2 · 오너 승인 2026-07-14).
// 목적: "본체+팩 동시 존재 & 바이너리 호환"일 때 팩 무중단 경로가 본체 알림에
// 가려지던 간극을 닫는다(pack-and-binary 분기 신설).
// ★T5 개정(오너 2026-07-15 실험): 본체 인앱 패치 설치(install_update) 재배선 —
// binary·pack-and-binary 문구가 "홈페이지 다운로드"에서 "Update 버튼 패치 설치"로
// 바뀌었고 updateplan.test.ts 핀도 함께 갱신됐다(의도적 계약 변경).
// 계약: ①분기 구조(5분기)는 불변 ②silent 경로는 토스트만
// (모달 금지 — 시작 시 자동 체크가 온보딩 화면에 끼어들지 않게, 성찰 불변식).

export type UpdateInputs = {
  binVersion: string | null; // 새 본체 버전(없으면 null) — fail-safe 보존 상태 기준
  packVersion: string | null; // 새 팩 버전(없으면 null)
  binaryTooOld: boolean; // 팩 min_binary_version > 설치 바이너리
  binCheckFailed: boolean;
  packCheckFailed: boolean;
};

export type UpdatePlan = {
  kind: "pack-and-binary" | "binary" | "pack" | "binary-required" | "none" | "unknown";
  badge: string; // 배지 텍스트("" = 배지 갱신 안 함·유지)
  ok: boolean; // 중립 스타일(.ok) 여부
  title: string; // 배지 title
  toastMsg: string; // silent 토스트 본문(없으면 "")
};

export function updatePlan(i: UpdateInputs): UpdatePlan {
  if (i.binVersion && i.packVersion && !i.binaryTooOld) {
    // ★옵션 2: 팩 무중단을 가리지 않는다 — 팩은 지금(↻·재시작 없음), 본체는 패치 설치(T5 개정).
    return {
      kind: "pack-and-binary",
      badge: "↻",
      ok: false,
      title: `새 자비스 구성 ${i.packVersion} 은 재시작 없이 적용 · 새 앱 ${i.binVersion} 도 설치 가능`,
      toastMsg:
        `새 자비스 구성 ${i.packVersion} 은 상단 「업데이트」로 재시작 없이 적용됩니다. ` +
        `새 앱 ${i.binVersion} 도 같은 단추로 설치하며, 설치 뒤 다시 켜지면 하던 창이 돌아옵니다.`,
    };
  }
  if (i.binVersion) {
    // 본체 패치 설치(T5 개정 — 오너 2026-07-15): Update 버튼 클릭 시 인앱 패치 설치.
    return {
      kind: "binary",
      badge: "!",
      ok: false,
      title: `새 앱 ${i.binVersion} — 상단 「업데이트」로 설치`,
      toastMsg: `새 앱 ${i.binVersion} 이 나왔습니다. 상단 「업데이트」를 누르면 설치하고, 다시 켜지면 하던 창이 돌아옵니다.`,
    };
  }
  if (i.packVersion && !i.binaryTooOld) {
    return {
      kind: "pack",
      badge: "↻",
      ok: false,
      title: `새 자비스 구성 ${i.packVersion} — 재시작 없이 적용`,
      toastMsg: `새 자비스 구성 ${i.packVersion} 이 있습니다. 상단 「업데이트」를 누르면 재시작 없이 적용됩니다.`,
    };
  }
  if (i.packVersion && i.binaryTooOld) {
    return {
      kind: "binary-required",
      badge: "!",
      ok: false,
      title: `새 자비스 구성 ${i.packVersion} — 앱을 먼저 새 판으로 받아 주세요`,
      toastMsg:
        `새 자비스 구성 ${i.packVersion} 은 더 새로운 앱이 있어야 적용됩니다. ` +
        `설치 사이트에서 앱을 먼저 받아 주세요: https://jarvis-install.godmeyou.kr`,
    };
  }
  if (!i.binCheckFailed && !i.packCheckFailed) {
    return {
      kind: "none",
      badge: "0",
      ok: true,
      title: "최신 버전 — 대기 중인 업데이트 없음",
      toastMsg: "",
    };
  }
  // 체크 실패 + 보존 상태 없음 = 상태 불명 — 배지 유지('최신' 오단정 금지, 종전 fail-safe).
  return { kind: "unknown", badge: "", ok: false, title: "", toastMsg: "" };
}
