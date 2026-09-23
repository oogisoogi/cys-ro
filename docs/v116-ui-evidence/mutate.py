import subprocess, sys, os, json
UI='/Users/oogisoogi/axdev/.wt/cys-v116-ui/ui'
env=dict(os.environ, PATH=os.path.expanduser('~/.bun/bin')+':'+os.environ['PATH'])
M=[
 ('M1a','src/closeguard.ts','return exited !== true;','return exited === false;','src/closeguard.test.ts'),
 ('M1b','src/main.ts','      if (ws === current() && ws.tree && collectSids(ws.tree).includes(sid)) setFocus(sid);\n      return;\n','      if (ws === current() && ws.tree && collectSids(ws.tree).includes(sid)) setFocus(sid);\n','src/closeguard.test.ts'),
 ('M1c','src/main.ts','term.write("\\r\\n\\x1b[31m[surface exited]\\x1b[0m\\r\\n", snapToBottom);','term.write("\\r\\n\\x1b[31m[surface exited]\\x1b[0m\\r\\n", snapToBottom); exitedPaneKeys.add(paneKey(sid, socket));','src/closeguard.test.ts'),
 ('M1d','src/main.ts','    if (!ws.tree || !collectSids(ws.tree).includes(sid)) return;\n  }\n','  }\n','src/closeguard.test.ts'),
 ('M2a','src/exitedsweep.ts','for (const k of swept) pending.delete(k);','for (const k of swept) pending.delete(k); pending.clear();','src/exitedsweep.test.ts'),
 ('M2b','src/exitedsweep.ts','if (now - arm.armedAt > SWEEP_ARM_TTL_MS) return null;\n  return arm.pending.get','if (now - arm.armedAt >= SWEEP_ARM_TTL_MS) return null;\n  return arm.pending.get','src/exitedsweep.test.ts'),
 ('M2c','src/main.ts','exitedSweepArm = settleSweep(sweepArm, sweptSockets, Date.now());','exitedSweepArm = settleSweep(sweepArm, [...(sweepArm?.pending ?? [])], Date.now());','src/exitedsweep.test.ts'),
 ('M1e','src/main.ts','    if (ccOpen) setCcOpen(false);\n','','src/closeguard.test.ts'),
 ('M1f','src/main.ts','  if (closingPaneKeys.has(key)) return;\n','','src/closeguard.test.ts'),
 ('M1g','src/main.ts','        else exitedPaneKeys.delete(paneKey(s.surface_id, sk));\n','','src/closeguard.test.ts'),
 ('M2d','src/main.ts','const sweepSids = sweepScope ? sockSids.filter((sid) => sweepScope.has(sid)) : [];','const sweepSids = sweepScope ? sockSids : [];','src/exitedsweep.test.ts'),
 ('M5e','src/main.ts','        found.push({ path: p, text: t });\n        break;\n','        found.push({ path: p, text: t });\n','src/restorebrief.test.ts'),
 ('M5f','src/restorebrief.ts','const okFull = (t: string) => notAfter === undefined || t <= notAfter;','const okFull = (t: string) => true;','src/restorebrief.test.ts'),
 ('X1','src/main.ts','  if (!collectSids(ws.tree).includes(sid)) return;\n  const key','  const key','src/closeguard.test.ts'),
 ('X5','src/main.ts','const sweepScope = sweepScopeFor(sweepArm, sk ?? "", Date.now());','const sweepScope = sweepScopeFor(sweepArm, "", Date.now());','src/exitedsweep.test.ts'),
 ('X7','src/main.ts','if (sweepArm && exitedSweepArm === sweepArm) exitedSweepArm = settleSweep(','if (sweepArm) exitedSweepArm = settleSweep(','src/exitedsweep.test.ts'),
 ('M6a','src/style.css','display: flex; flex-direction: column; gap: 8px; z-index: 950;','display: flex; flex-direction: column; gap: 8px; z-index: 99;','src/alertlayer.test.ts'),
 ('M6b','src/style.css','position: fixed; top: calc(var(--topbar-h, 38px) + 12px); right: 16px; z-index: 900;','position: fixed; right: 16px; bottom: 16px; z-index: 900;','src/alertlayer.test.ts'),
 ('M7a','src/headerlabels.ts','return ver ? `엔진 v${ver}` : "엔진 연결됨";','return ver ? `엔진 v${ver} pid=${status.daemon_pid}` : "엔진 연결됨";','src/headerlabels.test.ts'),
 ('M7b','src/main.ts','    info.title = daemonInfoTitle(status); // (D4 #5) 전문(pid·소켓 경로)은 툴팁으로\n','','src/headerlabels.test.ts'),
 ('M8a','index.html','title="파일 목록 — 선택한 창의 폴더">파일</button>','title="파일 목록 — 선택한 창의 폴더">Files</button>','src/topbarlabels.test.ts'),
 ('M8b','src/main.ts','const EXITED_TITLE_SUFFIX = " (끝남)";','const EXITED_TITLE_SUFFIX = " [exited]";','src/topbarlabels.test.ts'),
 ('M9a','src/wsname.ts','  if (masterSids && masterSids.size) {','  if (false && masterSids && masterSids.size) {','src/wsname.test.ts'),
 ('M9b','src/wsname.ts','  if (prevName === untitled && v === shownBefore) return untitled;\n','','src/wsname.test.ts'),
 ('M9c','src/main.ts','label.textContent = deptPlaceholderLabel({ pending: ws.pending, name: wsLabel(ws) });','label.textContent = deptPlaceholderLabel(ws);','src/wsname.test.ts'),
 ('M3a','src/main.ts','    top.style.flex = "";\n','','src/closeguard.test.ts'),
 ('M3b','src/main.ts','    top.style.flex = "";\n','    if (tree.type !== "pane") top.style.flex = "";\n','src/closeguard.test.ts'),
 ('M4a','index.html','    <button id="btn-close"','    <button id="btn-new" title="새 surface (⌘T)">+ New</button>\n    <button id="btn-close"','src/closeguard.test.ts'),
 ('M4b','src/main.ts','{ label: "오른쪽에 새 창 (⌘D)", action: () => void actionSplit("row") }','{ label: "오른쪽에 새 창 (⌘D)", action: () => void actionSplit("col") }','src/closeguard.test.ts'),
 ('M5a','src/restorebrief.ts','return [canon, ...stateCandidates(cwd, home).filter((p) => p !== canon)];','return [...stateCandidates(cwd, home).filter((p) => p !== canon)];','src/restorebrief.test.ts'),
 ('M5b','src/restorebrief.ts','if (best === null || at > best.at)','if (best === null || at >= best.at)','src/restorebrief.test.ts'),
 ('M5d','src/restorebrief.ts','    if (!hasBriefSections(f.text)) continue;\n','','src/restorebrief.test.ts'),
 ('M5c','src/main.ts','const [canonPath, ...chain] = briefStatePaths(master.live_cwd, home);','const [canonPath, ...chain] = briefStatePaths(null, home);','src/restorebrief.test.ts'),
]
only=sys.argv[1:] 
res=[]
for mid,f,old,new,test in M:
    if only and mid not in only: continue
    p=os.path.join(UI,f); src=open(p).read()
    assert src.count(old)==1,(mid,src.count(old))
    open(p,'w').write(src.replace(old,new))
    try:
        r=subprocess.run(['bun','test',test],cwd=UI,env=env,capture_output=True,text=True)
        out=r.stdout+r.stderr
        fails=[l for l in out.splitlines() if l.startswith('(fail)')]
        res.append((mid,'KILLED' if fails else 'SURVIVED',fails))
        if os.environ.get('KEEP')==mid: input('kept; enter to restore')
    finally:
        open(p,'w').write(src)
for mid,st,fails in res:
    print(mid,st)
    for x in fails: print('   ',x[:150])
