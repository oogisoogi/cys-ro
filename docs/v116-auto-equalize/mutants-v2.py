import subprocess, sys, pathlib, re
SNAP = pathlib.Path(sys.argv[1]) / "ui"
M = [
 ("M1 사양1 좌열 서브트리 보존", "src/formation.ts", "left.every((s) => subSids.includes(s))) keptLeft = sub;", "left.every((s) => subSids.includes(s))) keptLeft = null;"),
 ("M2 사양2 위아래 기둥을 한 줄로 편다(v1 회귀)", "src/formation.ts", "    if (p) rowUnits(p, units);\n  }", "    if (p) units.push(...sidsInOrder(p).map(pane));\n  }"),
 ("M3 사양2 기둥끼리 균등 안 함(반씩 접기)", "src/formation.ts", "b: evenRow(workers) };", "b: workers.reduceRight((acc, u) => ({ type: \"split\" as const, dir: \"row\" as const, ratio: 0.5, a: u, b: acc })) };"),
 ("M4 사양3 after 기둥 오른쪽 → 맨 끝", "src/formation.ts", "} else if (i >= 0) workers.splice(i + 1, 0, pane(sid));", "} else if (i >= 0) workers.push(pane(sid));"),
 ("M5 사양3 세로 분할 → 새 기둥", "src/formation.ts", "if (i >= 0 && dir === \"col\") {", "if (i >= 0 && dir === \"never\") {"),
 ("M6 사양3 after=좌열 → 맨 끝", "src/formation.ts", "else if (after !== undefined && isLeft(after) && seen.has(after)) workers.unshift(pane(sid));", "else if (after !== undefined && isLeft(after) && seen.has(after)) workers.push(pane(sid));"),
 ("M7 사양4 기둥 안 닫기 → 기둥 통째 삭제(형제 안 받음)", "src/formation.ts", "  if (a && b) return a === n.a && b === n.b ? n : { ...n, a, b };\n  return a ?? b;\n}", "  if (a && b) return a === n.a && b === n.b ? n : { ...n, a, b };\n  return a && b ? a : n.type === \"split\" && n.dir === \"col\" ? null : (a ?? b);\n}"),
 ("M8 사양4 잘린 가로 조각을 안 펼침", "src/formation.ts", "    if (p) rowUnits(p, units);\n  }", "    if (p) units.push(p);\n  }"),
 ("M11 처리표 무정렬 → 그대로 진행(표준 쪽으로)", "src/formation.ts", "if (!fits) return minimalChange(tree, change, drop);", "if (!fits && false) return minimalChange(tree, change, drop);"),
 ("M12 무정렬 세로 분할 → 가로", "src/formation.ts", "({ type: \"split\", dir: dir ?? \"row\", ratio: 0.5, a: old, b: p })", "({ type: \"split\", dir: \"row\", ratio: 0.5, a: old, b: p })"),
 ("M13 무정렬 루트 덧붙임 몫 1/2", "src/formation.ts", "t = { type: \"split\", dir: \"row\", ratio: k / (k + 1), a: t, b: p };", "t = { type: \"split\", dir: \"row\", ratio: 0.5, a: t, b: p };"),
 ("M14 맞춤 판정 = 좌열 좌석 품음만(섞임 허용)", "src/formation.ts", "return !us.some(isLeft) || us.every(isLeft);", "return true || us.every(isLeft);"),
 ("M15 사양5 팔레트 세로 분할 삭제", "src/main.ts", "    { id: \"act:split-col\", title: \"세로 분할\", keywords: \"split col 분할\", action: () => actionSplit(\"col\") },\n", ""),
 ("M16 사양5 ⌘⇧D → row", "src/main.ts", "    actionSplit(\"col\"); // 세로 분할(대상 창 아래", "    actionSplit(\"row\"); // 세로 분할(대상 창 아래"),
 ("M17 actionSplit 방향 버림", "src/main.ts", "arrangeWs(ws, { add: [{ sid, after: target, dir }] });", "arrangeWs(ws, { add: [{ sid, after: target }] });"),
 ("M18 사양1 좌열 사람 몫 무시", "src/formation.ts", "if (direct && !wasDefault && cs >= DRAG_MIN && cs <= DRAG_MAX) share = cs;", "if (false && direct && !wasDefault && cs >= DRAG_MIN && cs <= DRAG_MAX) share = cs;"),
 ("M19 14:5x 기본 25% → 1/3", "src/formation.ts", "export const LEFT_SHARE_DEFAULT = 0.25;", "export const LEFT_SHARE_DEFAULT = 1 / 3;"),
 ("M20 14:5x 최소 90칸 → 60", "src/formation.ts", "export const LEFT_MIN_COLS = 90;", "export const LEFT_MIN_COLS = 60;"),
 ("M21 14:5x 상한 50% → 60%", "src/formation.ts", "export const LEFT_SHARE_MAX = 0.5;", "export const LEFT_SHARE_MAX = 0.6;"),
 ("M22 14:5x 표지 무시(창 크기 바뀌어도 안 잼)", "src/formation.ts", "const wasDefault = (tree as { leftAuto?: boolean }).leftAuto === true;", "const wasDefault = false;"),
 ("M24 14:5x 기본 폭 출력에 표지 없음", "src/formation.ts", "? { type: \"split\", dir: \"row\", ratio: defaultShare, a: leftNode, b: evenRow(workers), leftAuto: true }", "? { type: \"split\", dir: \"row\", ratio: defaultShare, a: leftNode, b: evenRow(workers) }"),
 ("M25 14:5x 끌기가 표지 안 지움", "src/main.ts", "      delete node.leftAuto; // 사람이 끈 폭", "      void node.leftAuto; // 사람이 끈 폭"),
 ("M26 14:5x 창 크기 변경 재측정 없음", "src/main.ts", "    if (changed) render(); // 새 폭으로", "    if (changed && false) render(); // 새 폭으로"),
 ("M27 14:5x 정렬 단추 = 옛 1/3", "src/formation.ts", "ratio: defaultShare, a: std, b: evenRow(rest.map(pane)), leftAuto: true };", "ratio: 1 / 3, a: std, b: evenRow(rest.map(pane)), leftAuto: true };"),
 ("M28 14:5x adoptLayout master 가중 옛 규칙", "src/adoptlayout.ts", "const mw = n >= 2 ? ((n - 1) * LEFT_SHARE_DEFAULT) / (1 - LEFT_SHARE_DEFAULT) : 1;", "const mw = Math.max(1, (n - 1) / 2);"),
 ("M29 Fable R1 좌열 기둥 속 워커를 안 잘라 냄", "src/formation.ts", "prune(pil, new Set([...drop].filter((s) => !inLeft.includes(s))), new Set())", "prune(pil, new Set(), new Set())"),
 ("M31 Fable R3 워커 기둥 손상 비율 그대로", "src/formation.ts", "const workers = units.filter((u) => !sidsInOrder(u).some(isLeft)).map(heal);", "const workers = units.filter((u) => !sidsInOrder(u).some(isLeft));"),
 ("M32 14:5x 기본 폭 계산 창 폭 무시", "src/formation.ts", "return Math.min(LEFT_SHARE_MAX, Math.max(LEFT_SHARE_DEFAULT, (LEFT_MIN_COLS * cellPx) / rootPx));", "return LEFT_SHARE_DEFAULT;"),
 ("M23 2R② 옛 기본 이동 함수 무효", "src/formation.ts", "return OLD_DEFAULT_SHARES.some((v) => Math.abs(r - v) <= RULE_TOL) ? { ...tree, leftAuto: true } : tree;", "return tree;"),
 ("M33 2R① rolesBlind 없음", "src/formation.ts", "const fits = !rolesBlind && units.every", "const fits = units.every"),
 ("M34 2R① 역할 표 없어도 autoArrange", "src/main.ts", "  ws.tree = roles\n    ? autoArrange(ws.tree, roles, change, mode, currentDefaultLeftShare())\n    : arrangeWithoutRoles(ws.tree, change);", "  ws.tree = autoArrange(ws.tree, roles ?? new Map(), change, mode, currentDefaultLeftShare());"),
 ("M35 2R③ 좌열 = 순서 첫(옛)", "src/formation.ts", "order.filter((s) => family(roles.get(s)) === f).sort((x, y) => x - y)[0];", "order.filter((s) => family(roles.get(s)) === f)[0];"),
 ("M36 2R④ 끄는 중에도 재측정", "src/main.ts", "    if (dividerDragActive) { leftDefaultResizeSkipped = true; return; }", "    if (false && dividerDragActive) { leftDefaultResizeSkipped = true; return; }"),
 ("M37 2R② 복원 이동 안 함", "src/main.ts", "for (const ws of workspaces) if (ws.tree) ws.tree = migrateOldDefaultShare(ws.tree) as Node;", "for (const ws of workspaces) if (ws.tree) ws.tree = ws.tree as Node;"),
 ("M38 2R① 창 크기 핸들러 역할 없음 무시 안 함", "src/main.ts", "      if (!roles) continue; // 역할을 모르면", "      if (false && !roles) continue; // 역할을 모르면"),
 ("M39 3R① rolesBlind 를 본부 0명으로 넓힘(회귀)", "src/formation.ts", "tree.leftAuto === true && roles.size === 0;", "tree.leftAuto === true && leftSids(inOrder, roles).length === 0;"),
 ("M40 3R③ blur 때 끄는 중 표지 안 풂", "src/main.ts", "window.addEventListener(\"blur\", () => { dividerDragActive = false; });", "window.addEventListener(\"blur\", () => { void dividerDragActive; });"),
 ("M41 3R③ 손 떼도 건너뛴 재측정 안 함", "src/main.ts", "if (leftDefaultResizeSkipped) { leftDefaultResizeSkipped = false; recomputeDefaultLeft(); }", "if (leftDefaultResizeSkipped) { leftDefaultResizeSkipped = false; }"),
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
