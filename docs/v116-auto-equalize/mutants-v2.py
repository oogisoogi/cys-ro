import subprocess, sys, pathlib, re
SNAP = pathlib.Path(sys.argv[1]) / "ui"
M = [
 ("M1 사양1 좌열 서브트리 보존", "src/formation.ts", "left.every((s) => subSids.includes(s))) keptLeft = sub;", "left.every((s) => subSids.includes(s))) keptLeft = null;"),
 ("M2 사양2 위아래 기둥을 한 줄로 편다(v1 회귀)", "src/formation.ts", "    if (p) rowUnits(p, units);\n  }\n  // 맞출 수 있는가", "    if (p) units.push(...sidsInOrder(p).map(pane));\n  }\n  // 맞출 수 있는가"),
 ("M3 사양2 기둥끼리 균등 안 함(반씩 접기)", "src/formation.ts", "b: evenRow(workers) };", "b: workers.reduceRight((acc, u) => ({ type: \"split\" as const, dir: \"row\" as const, ratio: 0.5, a: u, b: acc })) };"),
 ("M4 사양3 after 기둥 오른쪽 → 맨 끝", "src/formation.ts", "} else if (i >= 0) workers.splice(i + 1, 0, pane(sid));", "} else if (i >= 0) workers.push(pane(sid));"),
 ("M5 사양3 세로 분할 → 새 기둥", "src/formation.ts", "if (i >= 0 && dir === \"col\") {", "if (i >= 0 && dir === \"never\") {"),
 ("M6 사양3 after=좌열 → 맨 끝", "src/formation.ts", "else if (after !== undefined && isLeft(after) && seen.has(after)) workers.unshift(pane(sid));", "else if (after !== undefined && isLeft(after) && seen.has(after)) workers.push(pane(sid));"),
 ("M7 사양4 기둥 안 닫기 → 기둥 통째 삭제(형제 안 받음)", "src/formation.ts", "  if (a && b) return a === n.a && b === n.b ? n : { ...n, a, b };\n  return a ?? b;\n}", "  if (a && b) return a === n.a && b === n.b ? n : { ...n, a, b };\n  return a && b ? a : n.type === \"split\" && n.dir === \"col\" ? null : (a ?? b);\n}"),
 ("M8 사양4 잘린 가로 조각을 안 펼침", "src/formation.ts", "    if (p) rowUnits(p, units);\n  }\n  // 맞출 수 있는가", "    if (p) units.push(p);\n  }\n  // 맞출 수 있는가"),
 ("M9 규칙5 워커 수 = 좌석 수(v1)", "src/formation.ts", "const prevRest = rowUnits(tree).filter((u) => !sidsInOrder(u).some((s) => inLeft.includes(s))).length;", "const prevRest = new Set(inOrder).size - inLeft.length;"),
 ("M10 규칙5 새 규칙값 = 좌석 수", "src/formation.ts", "if (untouched || share === null) share = leftColumnShare(workers.length);", "if (untouched || share === null) share = leftColumnShare(workers.flatMap((u) => sidsInOrder(u)).length);"),
 ("M11 처리표 무정렬 → 그대로 진행(표준 쪽으로)", "src/formation.ts", "if (!fits) return minimalChange(tree, change, drop);", "if (!fits && false) return minimalChange(tree, change, drop);"),
 ("M12 무정렬 세로 분할 → 가로", "src/formation.ts", "({ type: \"split\", dir: dir ?? \"row\", ratio: 0.5, a: old, b: p })", "({ type: \"split\", dir: \"row\", ratio: 0.5, a: old, b: p })"),
 ("M13 무정렬 루트 덧붙임 몫 1/2", "src/formation.ts", "t = { type: \"split\", dir: \"row\", ratio: k / (k + 1), a: t, b: p };", "t = { type: \"split\", dir: \"row\", ratio: 0.5, a: t, b: p };"),
 ("M14 맞춤 판정 = 좌열 좌석 품음만(섞임 허용)", "src/formation.ts", "return !us.some(isLeft) || us.every(isLeft);", "return true || us.every(isLeft);"),
 ("M15 사양5 팔레트 세로 분할 삭제", "src/main.ts", "    { id: \"act:split-col\", title: \"세로 분할\", keywords: \"split col 분할\", action: () => actionSplit(\"col\") },\n", ""),
 ("M16 사양5 ⌘⇧D → row", "src/main.ts", "    actionSplit(\"col\"); // 세로 분할(대상 창 아래", "    actionSplit(\"row\"); // 세로 분할(대상 창 아래"),
 ("M17 actionSplit 방향 버림", "src/main.ts", "arrangeWs(ws, { add: [{ sid, after: target, dir }] });", "arrangeWs(ws, { add: [{ sid, after: target }] });"),
 ("M18 사양1 좌열 사람 몫 무시", "src/formation.ts", "        if (direct && cs >= DRAG_MIN && cs <= DRAG_MAX) {", "        if (false && direct && cs >= DRAG_MIN && cs <= DRAG_MAX) {"),
]
tests = ["src/autoarrange.test.ts", "src/formation.test.ts", "src/closeguard.test.ts", "src/adoptlayout.test.ts", "src/exitedsweep.test.ts"]
res = []
for name, f, old, new in M:
    p = SNAP / f; src = p.read_text()
    c = src.count(old)
    if c != 1: res.append((name, f"NOT-APPLIED(count={c})")); continue
    p.write_text(src.replace(old, new))
    try:
        assert p.read_text() != src
        r = subprocess.run(["bun", "test", *tests], cwd=SNAP, capture_output=True, text=True, timeout=300)
        out = r.stdout + r.stderr
        fails = re.findall(r"^\(fail\) (.*)$", out, re.M)
        crash = bool(re.search(r"SyntaxError|Cannot find|error: (?!expect)", out)) and not fails
        res.append((name, ("CRASH" if crash else "KILLED" if r.returncode != 0 else "SURVIVED") + f" rc={r.returncode} fails={len(fails)} " + (fails[0][:110] if fails else "")))
    finally:
        p.write_text(src)
for n, v in res: print(f"{n}: {v}")
print("KILLED", sum(v.startswith("KILLED") for _, v in res), "/", len(res))
