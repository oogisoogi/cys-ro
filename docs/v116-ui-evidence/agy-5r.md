BLOCK(MINOR: `p`의 타입이 `Record<string, unknown>`이므로 `p.dept`는 `unknown` 타입으로 추론됩니다. 이를 `seatName`의 세 번째 인자로 그대로 넘기면 TypeScript 컴파일 에러(TS2345)가 발생할 수 있습니다. `typeof p.dept === 'string' ? p.dept : undefined`처럼 타입 검사나 단언이 필요합니다.)

---
[worker-13 판정 · 기각] 주장 = 「p.dept(unknown) 를 seatName 3번째 인자로 넘기면 TS2345」. 사실 아님:
- ui/src/alertcopy.ts:24 `export function seatName(no: number | null, role: unknown, dept?: unknown): string` — 인자 형이 unknown.
- `bunx tsc -p tsconfig.check.json` = 기존 7건과 동일(줄 번호 제외 diff 0) · alertcopy 관련 오류 0건(01:5x 실측).
- 2R MINOR(부서 접두 누락)의 닫힘 자체에는 이의 없음 → agy 수렴(새 사실 결함 0).
