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

export function daemonInfoLabel(status: { daemon_pid?: unknown; socket_path?: unknown }): string {
  return `daemon pid=${status.daemon_pid} sock=${status.socket_path}`;
}
