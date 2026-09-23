// headerlabels.ts — 상단바 좌측 라벨 문구의 순수 판정자(TICKET=cysr-ui-polish-101 ⓐⓑ · main.ts 는 배선만 한다).
//
// ⓐ 앱 판번 상시 표시: 종전엔 판번이 데몬≠앱 스큐 박스에서만 보여 평시 참가자 지원(「몇 판이세요?」)이
//    불가했다. 좌상단 「cysr」 옆에 앱 판번을 늘 두고, build_id 는 툴팁으로만 준다(자리 절약).
// ⓑ 데몬 라벨: 데몬이 재기동되면 pid 가 바뀐다 — 라벨은 시작 1회가 아니라 재연결마다 이 함수로 다시 쓴다.

export function appVersionLabel(ver: string): string {
  return ver ? `v${ver}` : "";
}

export function appVersionTitle(ver: string, buildId: string): string {
  return `cysr 앱 판번 v${ver} · build ${buildId || "unknown"}`;
}

// ⓒ 데몬 판번 상시 표시(B15 · TICKET=v110-darwin-update): 종전엔 데몬 판번이 **앱과 다를 때만**
//    스큐 배지에 나타났다 — 같을 때는 어디에도 없어 "지금 도는 데몬이 몇 판인가"를 물으면 답이 없었다.
//    앱 판번(app-ver)이 늘 보이는 것과 짝을 맞춘다. 데몬이 판번을 주지 않는 구판이면 **종전 문구 그대로**
//    (없는 값을 지어내지 않는다 — 빈 v 표기 금지).
// ⓓ(v116-ui-close · D4 #5) 상단바에는 **판번만** 싣는다. 종전 라벨 `daemon v… pid=… sock=/Users/<이름>/…` 은
//    내부 용어(daemon·pid·sock)와 사용자 폴더 경로가 모든 캡처·피드백에 상시 노출됐다(VM s0). 지원에 필요한 전문은
//    툴팁(daemonInfoTitle)으로 옮긴다 — 정보를 지우지 않고 자리만 바꾼다(마우스를 올리면 그대로 보인다).
type DaemonStatus = { daemon_pid?: unknown; socket_path?: unknown; version?: unknown };

/** 상단바 라벨 — 「엔진 v1.1.6」. 판번을 주지 않는 구판 데몬이면 「엔진 연결됨」(없는 값을 지어내지 않는다 · 빈 v 금지). */
export function daemonInfoLabel(status: DaemonStatus): string {
  const ver = typeof status.version === "string" ? status.version.trim() : "";
  return ver ? `엔진 v${ver}` : "엔진 연결됨";
}

/** 라벨 툴팁 — 종전 라벨 전문(지원용: 판번·pid·소켓 경로). */
export function daemonInfoTitle(status: DaemonStatus): string {
  const ver = typeof status.version === "string" ? status.version.trim() : "";
  const v = ver ? `v${ver} ` : "";
  return `daemon ${v}pid=${status.daemon_pid} sock=${status.socket_path}`;
}

// 자동 교대가 보류된 사유를 사람 문장으로(B15 「불가하면 토스트만 + 사유 표기」).
// 입력은 rotate_daemon 이 낸 오류 문자열 그대로 — 계약은 접두 `live_sessions:`(install_update 와 공유).
export function holdReasonText(raw: string): string {
  const m = /live_sessions:(\S+)/.exec(raw ?? "");
  if (!m) return "데몬 교대에 실패했습니다(사유 미상) — 다음 점검에서 다시 시도합니다.";
  if (m[1] === "unknown") return "세션 수를 확인하지 못해 교대를 보류했습니다(확인 실패 = 보류).";
  return `작업 세션 ${m[1]}개가 살아 있어 교대를 보류했습니다(세션 보존 우선).`;
}
