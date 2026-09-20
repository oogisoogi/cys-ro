// exitedsweep.ts — 재시작·phoenix 복원 뒤 남은 「[surface exited]」 옛 자리의 자동 정리 판정
// (B17 · TICKET=v110-darwin-update · main.ts 는 배선만 한다).
//
// ★왜 기존 유령 수렴(wsreconcile.advanceGhostStrikes)으로는 안 되는가 — 두 축이 다르다:
//   · 유령 수렴은 데몬이 **기록 자체를 모르는** sid 를 친다(knownIds 밖).
//   · 복원 뒤 남는 자리는 데몬이 **알고 있다** — `exited: true` 인 기록으로. 그래서 유령 판정에
//     영원히 걸리지 않고, 화면에는 빨간 [surface exited] 배너만 남은 pane 이 계속 자리를 차지한다.
//   두 축을 한 함수에 뭉치지 않는다. 뭉치면 "모르는 것"과 "죽은 것"의 처방이 섞인다.
//
// ★왜 평시에 치지 않고 복원 직후 1회만 치는가: 사용자가 직접 끝낸 세션의 마지막 출력은 **읽을
//   권리**가 있다(끝나자마자 사라지면 무슨 일이 있었는지 못 본다). 복원 직후의 옛 자리는 그것과
//   다르다 — 새 자리가 이미 따로 섰고, 옛 자리는 아무도 보지 않는 잔재다.

export type SurfaceRow = { surface_id: number; exited?: boolean };

/// 칠 대상 sid 목록. 판정은 둘 다 참일 때만 나온다:
///   ① armed(복원 완료 직후 1회) ② 데몬 기록이 exited=true 다.
///
/// ★「데몬이 빈 목록을 돌려줘도 화면을 비우지 않는다」는 여기서 **가드가 아니라 술어의 방향**으로
///   성립한다. 유령 수렴은 "목록에 **없는** 것"을 치기 때문에 빈 목록이 곧 전멸 판정이 되어 명시
///   가드가 필요했다. 이쪽은 "목록에 **있고 exited 인** 것"만 치므로 빈 목록에서는 고를 것이 원리적으로
///   없다. (초판에는 `surfaces.length === 0` 가드가 있었는데, 뮤턴트 m9 가 그 줄을 지워도 아무 시험도
///   빨개지지 않음을 보여 줬다 — 지키는 일이 없는 줄이었다. 성질은 아래 시험이 직접 잰다.)
export function exitedSweepTargets(
  armed: boolean,
  treeSids: readonly number[],
  surfaces: readonly SurfaceRow[],
): number[] {
  if (!armed) return [];
  const exited = new Set(surfaces.filter((s) => s.exited === true).map((s) => s.surface_id));
  return treeSids.filter((sid) => exited.has(sid));
}

/// B16(새 자리 배치 규칙 — 왼쪽 열 master 위·cso 아래 4:1 · 오른쪽 worker)의 **이음매**.
///
/// ⛔지금은 적용하지 않는다. B16 규칙 코드는 `fix/v110-panetitle` 에서 오기로 돼 있는데 그 브랜치가
///   아직 없다(2026-09-20 실측: `git branch -a` 에 없음). 규칙을 여기서 즉흥으로 **지어내면** 나중에
///   진짜 규칙이 왔을 때 두 벌이 생긴다 — 그래서 자리만 남기고 「적용 안 했다」를 값으로 돌려준다.
///   (「안 했다」를 조용히 두지 않는 이유: 호출부가 그 값을 로그로 남겨야 다음 사람이 미편입을 본다.)
export type PlacementOutcome = { applied: boolean; reason: string };

export function applyB16Placement(): PlacementOutcome {
  return {
    applied: false,
    reason: "B16 배치 규칙 미편입(fix/v110-panetitle 부재) — 자리만 비워 둠. HANDOFF 참조.",
  };
}
