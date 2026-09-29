// ①(TICKET=cysr-117-impl-lead · MUST-DO-117 ①) 부서 목록(list_depts) 판독 — 실패를 「부서 0」 으로 접지 않는다.
// 종전 `.catch(() => ({ depts: {} }))` 는 레지스트리를 못 읽은 것과 부서가 없는 것을 구분하지 못해, 재시작·
// 판번 교대가 부서를 조용히 건너뛰었다. 못 읽음은 이유와 함께 돌려주고 호출부가 사람에게 알린다.

export type DeptEntry = { socket?: string };
export type DeptRegistry = { depts: Record<string, DeptEntry>; unreadable: string | null };

export async function readDeptRegistry(
  invokeFn: (cmd: string) => Promise<unknown>,
): Promise<DeptRegistry> {
  let raw: unknown;
  try {
    raw = await invokeFn("list_depts");
  } catch (e) {
    return { depts: {}, unreadable: String(e) };
  }
  const depts = (raw as { depts?: unknown } | null)?.depts ?? {};
  if (typeof depts !== "object" || depts === null || Array.isArray(depts)) {
    return { depts: {}, unreadable: "형식이 {\"depts\":{…}} 가 아님" };
  }
  return { depts: depts as Record<string, DeptEntry>, unreadable: null };
}

export function deptRegistryUnreadableNote(reason: string): string {
  return `부서 목록(depts.json)을 읽을 수 없어 부서 데몬은 건드리지 않았습니다 — 파일을 확인하세요(${reason}).`;
}
