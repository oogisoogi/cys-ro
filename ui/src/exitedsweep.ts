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
///   ① armed(복원 완료 뒤 그 소켓이 아직 쓸리지 않았다 — 아래 sweepArmedFor) ② 데몬 기록이 exited=true 다.
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

// ── 무장 상태(TICKET=v116-ui-close · D4 #17) ──────────────────────────────────
// ★왜 불리언 하나가 아닌가: 종전 무장은 `exitedSweepArmed` 한 개였고 **패스가 끝나면 무조건** 내렸다.
//   그 패스에서 어느 부서 소켓의 조회가 in-flight 가드로 건너뛰어지거나 시간초과로 실패하면, 그 소켓은
//   한 번도 쓸리지 않았는데 무장이 사라져 [exited] 옛 창이 다음 복원까지 남았다(헤드리스 재현: 조회 실패
//   주입 → 7초 뒤에도 잔존). 그래서 무장을 「아직 쓸리지 않은 소켓들」로 들고, **조회가 성공해 청소 줄을
//   지난 소켓만** 뺀다 — 실패한 소켓은 다음 틱이 다시 시도한다.
// ★술어는 그대로다: 여전히 exitedSweepTargets(데몬 기록 exited=true 인 것만)가 친다. 무장이 길어져도
//   산 창을 닫는 경로는 생기지 않는다.

/**
 * 무장 상한(ms) — in-flight 재시도 간격(60초) × 5. 이보다 오래 응답 없는 소켓은 포기한다(영구 무장 0).
 * ⚠윈도는 재시도 간격이 배율(winScaled)로 늘어나 같은 5분 안의 재시도 횟수가 그만큼 줄어든다(순수 모듈이라
 *   배율을 모른다 · 상한 자체는 플랫폼 공통 5분).
 */
export const SWEEP_ARM_TTL_MS = 5 * 60_000;

/**
 * 무장 = 소켓 키(`socket ?? ""`) → **무장 시점에 그 소켓 화면에 있던 창 번호**(스냅숏) + 무장 시각. null = 무장 없음.
 * ★스냅숏인 이유(Fable 적대 MINOR-5): 무장이 최대 5분까지 살아 있으므로, 「지금 exited 인 창 전부」를 치면 복원
 *   **뒤에** 사용자가 끝낸 창까지 마지막 화면째 쓸어 간다(머리주석의 「읽을 권리」와 충돌). 옛 자리 = 복원이 끝난
 *   그 순간 화면에 있던 창 — 이 정의를 코드에 박는다.
 */
export type SweepArm = { pending: ReadonlyMap<string, ReadonlySet<number>>; armedAt: number } | null;

/** 복원 완료 시점에 무장한다 — (소켓 키, 그 탭의 창 번호들) 목록. 같은 소켓 탭이 여럿이면 합친다. 없으면 무장 없음. */
export function armSweep(entries: Iterable<readonly [string, readonly number[]]>, now: number): SweepArm {
  const pending = new Map<string, Set<number>>();
  for (const [k, sids] of entries) {
    const set = pending.get(k) ?? new Set<number>();
    for (const sid of sids) set.add(sid);
    pending.set(k, set);
  }
  return pending.size ? { pending, armedAt: now } : null;
}

/** 이 소켓을 이번 패스에서 쓸 때 칠 수 있는 창 번호(스냅숏). 무장 아님·대상 소켓 아님·상한 초과 = null. */
export function sweepScopeFor(arm: SweepArm, socketKey: string, now: number): ReadonlySet<number> | null {
  if (!arm) return null;
  if (now - arm.armedAt > SWEEP_ARM_TTL_MS) return null;
  return arm.pending.get(socketKey) ?? null;
}

/** 이 소켓을 이번 패스에서 쓸어야 하는가(무장 중 · 대상 소켓 · 상한 안). */
export function sweepArmedFor(arm: SweepArm, socketKey: string, now: number): boolean {
  return sweepScopeFor(arm, socketKey, now) !== null;
}

/**
 * 패스가 끝난 뒤의 무장. 이번 패스에서 **청소 줄까지 도달한** 소켓(`swept`)만 뺀다.
 * 전부 빠졌거나 상한이 지났으면 null(무장 해제).
 */
export function settleSweep(arm: SweepArm, swept: Iterable<string>, now: number): SweepArm {
  if (!arm) return null;
  if (now - arm.armedAt > SWEEP_ARM_TTL_MS) return null;
  const pending = new Map(arm.pending);
  for (const k of swept) pending.delete(k);
  return pending.size ? { pending, armedAt: arm.armedAt } : null;
}

// ★B16 배치는 여기 있지 않다(2026-09-20 결선): `ui/src/formation.ts` 의 `formationIfRowOnly` 가
//   정본이고, 이 모듈의 스윕이 **먼저** 돌아 닫은 뒤 `refreshPaneTitles` 가 새 roleBySid 로 그 함수를
//   부른다. 순서(닫기 → 배치)가 계약이다 — 닫힌 sid 가 roleBySid 에 섞이면 그 좌석이 열을 하나 차지한다.
//   (초판에는 `applyB16Placement()` 이음매가 있었다. fix/v110-panetitle 516d39d8 가 오면서 그 자리에
//    진짜 함수가 들어왔으므로 이음매는 지운다 — 「미편입」을 돌려주는 함수가 남아 있으면 거짓말이 된다.)
