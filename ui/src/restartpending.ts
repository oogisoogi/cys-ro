// 맥 새 판 교체 뒤 「다시 켜기 대기」 판정 — 순수 로직(main.ts 는 DOM·Tauri 배선만 한다).
//
// ★TICKET=v116-restart-toast(1085 VM 실기 · 2026-09-24): 교체 완료 알림(stickyToast "upd-restart")은
// 오너 정책(toastttl.ts 「종류 불문 소멸」)대로 60초 뒤 사라진다. 종전엔 그 뒤 누를 곳이 없어 사용자가
// 헤더 「업데이트」를 다시 누르고 → 도는 옛 앱이 같은 판을 또 「새 판」이라 판정해 → 전량 재다운로드·재교체를
// 반복했다. 이제 교체 완료 사실을 기억해 두고 헤더 단추가 「다시 켜기」가 된다(설치 재호출 0).
//
// 기억 수명 = 「교체를 마친 옛 앱이 살아 있는 동안」. sessionStorage 는 화면 새로고침(⌘R)엔 남고 앱이
// 재시작하면 비지만, 그래도 남는 경우를 막으려고 **저장 때의 앱 판번**을 짝으로 적어 두고 판번이 바뀌었으면
// (= 새 판으로 켜졌으면) 무효로 본다. 검증할 수 없는 기억(판번 조회 실패·깨진 값)도 무효 — 거짓 대기는
// 만들지 않고 종전 동작으로 물러난다.

/** sessionStorage 칸 이름. 모양이 바뀌면 끝 번호를 올린다(옛 값은 decode 가 무효로 본다). */
export const RESTART_PENDING_KEY = "cys-restart-pending-v1";

/** 헤더 단추 글자 — 평소 / 다시 켜기 대기. 대기 이름은 데몬만 다시 켜는 「↻ 재시작」과 겹치지 않는다. */
export const UPDATE_BUTTON_LABEL = "업데이트";
export const RESTART_BUTTON_LABEL = "다시 켜기";

/** 저장 값. version = 교체가 끝난 새 판 · appVersion = 저장할 때 돌던(옛) 앱 판번. */
export function encodeRestartPending(version: string, appVersion: string): string {
  return JSON.stringify({ version, appVersion });
}

/**
 * 저장 값 → 유효한 대기 판번(없으면 null).
 * 무효: 값 없음 · 깨진 JSON · 모양 틀림 · 지금 앱 판번을 모름 · 저장 때 판번 ≠ 지금 판번(재시작됨) ·
 * 대기 판번 == 지금 판번(이미 새 판으로 돈다).
 */
export function decodeRestartPending(raw: string | null, currentAppVersion: string | null): string | null {
  if (!raw || !currentAppVersion) return null;
  let v: unknown;
  try {
    v = JSON.parse(raw);
  } catch {
    return null;
  }
  if (!v || typeof v !== "object") return null;
  const { version, appVersion } = v as { version?: unknown; appVersion?: unknown };
  if (typeof version !== "string" || typeof appVersion !== "string" || !appVersion) return null;
  if (appVersion !== currentAppVersion) return null;
  if (version === currentAppVersion) return null;
  return version;
}

/** 헤더 단추를 눌렀을 때 할 일 — 대기가 있으면 다시 켜기, 없으면 종전대로 새로 확인. */
export function updateButtonAction(pendingVersion: string | null): "restart" | "check" {
  return pendingVersion === null ? "check" : "restart";
}

/** 교체 완료 알림(누르면 다시 켜기) 문구 — 공개 문구 규칙: 안내자 말투 · 괄호 0 · 한 문장에 행동 하나. */
export function restartReadyToast(version: string): { name: string; detail: string } {
  const which = version ? `새 앱 ${version}` : "새 앱";
  return {
    name: "✅ 새 앱 설치 완료",
    detail:
      `${which} 설치가 끝났습니다. 이 알림을 누르면 하던 대화를 저장하고 앱을 다시 켭니다. ` +
      `나중에 하시려면 위쪽 「${RESTART_BUTTON_LABEL}」 단추를 눌러 주세요.`,
  };
}

/** 「다시 켜기」 단추·배지 툴팁. */
export function restartPendingTitle(version: string): string {
  const which = version ? `새 앱 ${version}` : "새 앱";
  return `${which} 설치가 끝났습니다. 누르면 하던 대화를 저장하고 앱을 다시 켭니다.`;
}
