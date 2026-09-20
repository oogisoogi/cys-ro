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

// ★B16 배치는 여기 있지 않다(2026-09-20 결선): `ui/src/formation.ts` 의 `formationIfRowOnly` 가
//   정본이고, 이 모듈의 스윕이 **먼저** 돌아 닫은 뒤 `refreshPaneTitles` 가 새 roleBySid 로 그 함수를
//   부른다. 순서(닫기 → 배치)가 계약이다 — 닫힌 sid 가 roleBySid 에 섞이면 그 좌석이 열을 하나 차지한다.
//   (초판에는 `applyB16Placement()` 이음매가 있었다. fix/v110-panetitle 516d39d8 가 오면서 그 자리에
//    진짜 함수가 들어왔으므로 이음매는 지운다 — 「미편입」을 돌려주는 함수가 남아 있으면 거짓말이 된다.)
