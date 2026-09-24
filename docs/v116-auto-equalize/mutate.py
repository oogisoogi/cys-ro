import subprocess, sys, os, re
R=sys.argv[1]; BUN=os.path.expanduser('~/.bun/bin/bun')
F='ui/src/formation.ts'; M='ui/src/main.ts'
MUT=[
 ("M1 좌열 모양 가드 제거", F, 'const colShaped = sub.type === "pane" || (sub.dir === "col" && okRatio(sub.ratio));', 'const colShaped = okRatio(sub.type === "split" ? sub.ratio : undefined);'),
 ("M2 D1 C→A(규칙값 재계산 안 함)", F, 'untouched = prevRest > 0 && Math.abs(cs - leftColumnShare(prevRest)) <= RULE_TOL;', 'untouched = false;'),
 ("M3 D1 C→B(사람 값도 규칙값으로)", F, 'untouched = prevRest > 0 && Math.abs(cs - leftColumnShare(prevRest)) <= RULE_TOL;', 'untouched = prevRest > 0;'),
 ("M4 허용 오차 0.01→0.2", F, 'export const RULE_TOL = 0.01;', 'export const RULE_TOL = 0.2;'),
 ("M5 좌열 서브트리 보존 안 함", F, 'if (subSids.length === left.length && left.every((s) => subSids.includes(s))) keptLeft = sub;', 'if (false) keptLeft = sub;'),
 ("M6 remove 무시", F, 'for (const s of inOrder) if (!drop.has(s) && !order.includes(s)) order.push(s);', 'for (const s of inOrder) if (!order.includes(s)) order.push(s);'),
 ("M7 after 무시(늘 끝)", F, 'const i = after === undefined ? -1 : order.indexOf(after);', 'const i = -1;'),
 ("M8 정확 덮기 검사 제거", F, 'const exact = subSids.length === inLeft.length && inLeft.every((s) => subSids.includes(s));', 'const exact = true;'),
 ("M9 세로 분할 길 허용", F, '    if (n.dir !== "row") return null;\n', ''),
 ("M11 균등 comb → 0.5 감싸기", F, 'acc = { type: "split", dir: "row", ratio: 1 / (nodes.length - i), a: nodes[i], b: acc };', 'acc = { type: "split", dir: "row", ratio: 0.5, a: nodes[i], b: acc };'),
 ("M13 좌열 몫 가지 반대로", F, 'share *= inA ? r : 1 - r;', 'share *= inA ? 1 - r : r;'),
 ("M14 좌열 없을 때 master/cso 순서 뒤집기", F, 'const left = leftSids(order, roles);', 'const left = leftSids(order, roles).reverse();'),
 ("M15 새 창 0.5 감싸기 복귀", M, 'arrangeWs(ws, { add: [{ sid }] }); // 새 창도', 'ws.tree = ws.tree ? { type: "split", dir: "row", a: ws.tree, b: { type: "pane", sid } } : { type: "pane", sid }; // 새 창도'),
 ("M16 detachPane replaceNode 복귀", M, 'arrangeWs(ws, { remove: [sid] }); // 외부 닫힘', 'ws.tree = replaceNode(ws.tree, sid, () => null); // 외부 닫힘'),
 ("M17 틱 역할 표 갱신 제거", M, '      rememberRoles(sk, r.surfaces); // 자동 정렬 역할 표 — 이 틱', '      // 자동 정렬 역할 표 — 이 틱'),
 ("M18 정렬 단추 standard 누락", M, '.includes(sid)) }, "standard");', '.includes(sid)) });'),
 ("M19 역할 표 키 소켓 누락", M, 'arrangeRolesBySocket.get(ws.socket ?? "") ?? new Map()', 'new Map()'),
 ("M20 틱 입양 배치 호출 제거", M, '        arrangeWs(ws, { add: [{ sid: s.surface_id }] });\n        setRoleDot(rt', '        setRoleDot(rt'),
 ("M21 복원 입양 배치 제거", M, '        arrangeWs(ws, { add: [{ sid: s.surface_id }] });\n        ws.autoCreated', '        ws.autoCreated'),
 ("M22 머리 × 배치 제거", M, '    if (ws.tree) arrangeWs(ws, { remove: [sid] });\n    if (focusedSid === sid) focusedSid = collectSids(ws.tree)[0] ?? null;\n    render();\n  });', '    if (ws.tree) ws.tree = replaceNode(ws.tree, sid, () => null);\n    if (focusedSid === sid) focusedSid = collectSids(ws.tree)[0] ?? null;\n    render();\n  });'),
 ("M23 메뉴 「아래」 복귀", M, '    { label: "오른쪽에 새 창 (⌘D)", action: () => void actionSplit("row") },\n', '    { label: "오른쪽에 새 창 (⌘D)", action: () => void actionSplit("row") },\n    { label: "아래에 새 창 (⌘⇧D)", action: () => void actionSplit("col") },\n'),
 ("M24 F1 직계 조건 제거", F, 'const direct = tree.type === "split" && tree.dir === "row" && tree.a === sub;', 'const direct = true;'),
 ("M25 F1 끌기 범위 제거", F, 'if (direct && cs >= DRAG_MIN && cs <= DRAG_MAX) {', 'if (direct) {'),
 ("M26 F4 손상 비율 거부 제거", F, 'const okRatio = (r?: number) => r === undefined || (Number.isFinite(r) && r > 0 && r < 1);', 'const okRatio = (_r?: number) => true;'),
 ("M27 F4 승격 비율 이어받기 제거", F, 'else if (sub.type === "split" && left.length === 2', 'else if (false && sub.type === "split" && left.length === 2'),
 ("M28 F3 무변화 가드 제거", M, 'if (!effective && mode !== "standard") return;', 'void effective;'),
 ("M29 F3 × 탭 = current()", M, 'collectSids(w.tree).includes(sid)) ?? current();', 'collectSids(w.tree).includes(sid) && false) ?? current();'),
 ("M30 F2 입양 배치를 await 뒤로", M, '        arrangeWs(ws, { add: [{ sid: s.surface_id }] });\n        setRoleDot(rt.roleEl, s.role, surfaceWorking(s.surface_id, sk));', '        setRoleDot(rt.roleEl, s.role, surfaceWorking(s.surface_id, sk));\n        await Promise.resolve();\n        arrangeWs(ws, { add: [{ sid: s.surface_id }] });'),
]
TESTS=['src/autoarrange.test.ts','src/formation.test.ts','src/adoptlayout.test.ts','src/exitedsweep.test.ts','src/closeguard.test.ts']
base=subprocess.run([BUN,'test',*TESTS],cwd=R+'/ui',capture_output=True,text=True)
print('BASE rc',base.returncode, re.findall(r'(\d+) fail',base.stdout+base.stderr))
killed=0
for name,f,old,new in MUT:
    p=os.path.join(R,f); src=open(p).read()
    n=src.count(old)
    if n!=1: print(f'NOT-APPLIED {name} (count={n})'); continue
    try:
        open(p,'w').write(src.replace(old,new))
        assert open(p).read()!=src
        try:
            r=subprocess.run([BUN,'test',*TESTS],cwd=R+'/ui',capture_output=True,text=True,timeout=90)
        except subprocess.TimeoutExpired:
            print(f'HANG {name} (90s · 측정 무효 — KILLED 로 세지 않는다)', flush=True); continue
        out=r.stdout+r.stderr
        fails=re.findall(r'^\(fail\) (.*?)(?: \[[\d.]+ms\])?$',out,re.M)
        crash='SyntaxError' in out or 'error: ' in out and not fails
        if r.returncode!=0 and fails:
            killed+=1; print(f'KILLED {name} ← {len(fails)}: {fails[0][:90]}', flush=True)
        elif r.returncode!=0: print(f'CRASH {name}: {out[-200:]}')
        else: print(f'SURVIVED {name}')
    finally:
        open(p,'w').write(src)
print(f'killed {killed}/{len(MUT)}')
