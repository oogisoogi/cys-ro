import subprocess, sys, os, json
UI='/Users/oogisoogi/axdev/.wt/cys-v116-ui/ui'
env=dict(os.environ, PATH=os.path.expanduser('~/.bun/bin')+':'+os.environ['PATH'])
M=[
 ('M1a','src/closeguard.ts','return exited !== true;','return exited === false;','src/closeguard.test.ts'),
 ('M1b','src/main.ts','      if (ws === current() && ws.tree && collectSids(ws.tree).includes(sid)) setFocus(sid);\n      return;\n','      if (ws === current() && ws.tree && collectSids(ws.tree).includes(sid)) setFocus(sid);\n','src/closeguard.test.ts'),
 ('M1c','src/main.ts','writeExitedBanner(term, trackFilter, snapToBottom);','writeExitedBanner(term, trackFilter, snapToBottom); exitedPaneKeys.add(paneKey(sid, socket));','src/closeguard.test.ts'),  # (v116-exited-banner) 배너 쓰기가 exitbanner.ts 로 옮겨 앵커 갱신
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
 ('M8b','src/panetitle.ts','export const EXITED_TITLE_PREFIX = "(끝남) ";','export const EXITED_TITLE_PREFIX = "[exited] ";','src/topbarlabels.test.ts'),
 ('M9a','src/wsname.ts','  if (masterSids && masterSids.size) {','  if (false && masterSids && masterSids.size) {','src/wsname.test.ts'),
 ('M9b','src/wsname.ts','  if (prevName === untitled && v === shownBefore) return untitled;\n','','src/wsname.test.ts'),
 ('M9c','src/main.ts','label.textContent = deptPlaceholderLabel({ pending: ws.pending, name: wsLabel(ws) });','label.textContent = deptPlaceholderLabel(ws);','src/wsname.test.ts'),
 ('M8c','src/updateplan.ts','이 있습니다. 상단 「업데이트」를 누르면 재시작 없이 적용됩니다.`,','이 있습니다. 상단 Update 버튼을 누르면 재시작 없이 적용됩니다.`,','src/topbarlabels.test.ts'),
 ('M9d','src/main.ts',"  if (bar.querySelector('.ws-name[contenteditable=\"true\"]')) return;\n",'','src/wsname.test.ts'),
 ('M9e','src/main.ts','        if (masterSids.size) {\n          const before','        if (true) {\n          const before','src/wsname.test.ts'),
 ('M9f','src/wsname.ts','base.reduce((a, b) => (b.id < a.id ? b : a)).id','base[0].id','src/wsname.test.ts'),
 ('M7c','src/style.css','  flex: none; white-space: nowrap; }','  flex: 0 1 auto; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }','src/headerlabels.test.ts'),
 ('M10a','src/scrollfollow.ts','viewportY <= 0 && baseY > 0 && bufferType === "normal"','viewportY <= 0 && bufferType === "normal"','src/scrollfollow.test.ts'),
 ('M10b','src/scrollfollow.ts','viewportY <= 0 && baseY > 0 && bufferType === "normal"','viewportY <= 0 && baseY > 0','src/scrollfollow.test.ts'),
 ('M11a','src/wsusage.ts','stale: age > SCOPED_STALE_SECS, // (D4 #11)','stale: age > USAGE_STALE_SECS, // (D4 #11)','src/wsusage.test.ts'),
 ('M11b','src/wsusage.ts','export const SCOPED_STALE_SECS = 240;','export const SCOPED_STALE_SECS = 400;','src/wsusage.test.ts'),
 ('M12a','src/main.ts','  restoreBriefBusy = true;\n  try {','  restoreBriefBusy = true;\n  restoreBriefShown = true;\n  try {','src/restorebrief.test.ts'),
 ('M12b','src/main.ts','  if (isMasterSeatSignal(name, payload) && !factoryResetting && !resetCompleted) maybeShowRestoreBrief();\n','','src/restorebrief.test.ts'),
 ('M12c','src/restorebrief.ts','(name === "role.claimed" || name === "surface.created") && payload.role === "master"','name === "role.claimed" && payload.role === "master"','src/restorebrief.test.ts'),
 ('M12d','src/main.ts','    restoreBriefAgain = true;\n','','src/restorebrief.test.ts'),
 ('M12e','src/restorebrief.ts','&& payload.role === "master";','&& payload.role != null;','src/restorebrief.test.ts'),
 ('M13a','src/panetitle.ts','return exited ? EXITED_TITLE_PREFIX + t : t;','return exited ? t + " (끝남)" : t;','src/panetitle.test.ts'),
 ('M13b','src/panetitle.ts','else t = liveCwd ? `${sid}${SEP}${cwdBase(liveCwd)}` : String(sid);','else t = liveCwd || "…";','src/panetitle.test.ts'),
 ('M13f','src/main.ts','        rt.titleEl.title = s.live_cwd ?? "";\n','','src/panetitle.test.ts'),
 ('M14a','src/wsusage.ts','  if (typeof v === "string" && v.trim() !== "") return Number(v);\n  return NaN;','  return Number(v);','src/wsusage-null.test.ts'),
 ('M14b','src/wsusage.ts','      const used = usedPctOf(g.used_pct);','      const used = Number(g.used_pct);','src/wsusage-null.test.ts'),
 ('M14c','src/main.ts','  const rates = (u.rate ?? []).filter((w) => Number.isFinite(usedPctOf(w.used_pct)));','  const rates = u.rate ?? [];','src/wsusage-null.test.ts'),
 ('M14d','src/main.ts','      if (!Number.isFinite(usedPctOf(w.used_pct))) continue; // (D4 #18) 미관측 창은 0% 후보가 아니다\n','','src/wsusage-null.test.ts'),
 ('M14e','src/main.ts','      const used = usedPctOf(r.used_pct); // (D4 #18)','      const used = Number(r.used_pct); // (D4 #18)','src/wsusage-null.test.ts'),
 ('M14f','src/main.ts','        if (r && r.stale !== true && !Number.isFinite(usedPctOf(r.used_pct))) r = undefined;\n','','src/wsusage-null.test.ts'),
 ('M14g','src/wsusage.ts','  return NaN;\n}','  return v === null ? NaN : 0;\n}','src/wsusage-null.test.ts'),
 ('M15a','src/alertcopy.ts','의 AI가 종료됐습니다. 창과 작업 폴더는 그대로 남아 있습니다. ${CHECK}','의 AI가 종료됐습니다. ${CHECK}','src/alertcopy.test.ts'),
 ('M15b','src/alertcopy.ts','한 번 정리할 때가 됐습니다.`,','한 번 정리할 때가 됐습니다. ${p.action ?? ""}`,','src/alertcopy.test.ts'),
 ('M15c','src/main.ts','    const c = approvalRequestCopy(no, ap);\n    toast("approval", c.title, c.body);','    const c = approvalRequestCopy(no, ap);\n    toast("approval", c.title, `${payload.role ?? ""} surface:${sid} — ${c.body}`);','src/alertcopy.test.ts'),
 ('M15d','src/alertcopy.ts','title: `🚨 ${friendlyRole(role)} 창 응답 없음`','title: `🚨 ${role} 창 응답 없음`','src/alertcopy.test.ts'),
 ('M15e','src/alertcopy.ts','  const m = /^surface:(\\d+)$/.exec(String(surfaceRef ?? ""));\n  return m ? Number(m[1]) : null;','  return null;','src/alertcopy.test.ts'),
 ('M15f','src/alertcopy.ts','title: "❌ AI가 꺼졌습니다",','title: "AI가 멈췄습니다",','src/alertcopy.test.ts'),
 ('M15g','src/alertcopy.ts','const act = DEADMAN_NO_WINDOW.has(axis) ? "상단 「↻ 재시작」을 누르면 창을 다시 세웁니다." : CHECK;','const act = CHECK;','src/alertcopy.test.ts'),
 ('M15h','src/main.ts','toast("alert", c.title, c.body, undefined, c.raw);','toast("alert", c.title, c.body);','src/alertcopy.test.ts'),
 ('M15i','src/main.ts','approvalStalledCopy(seatNo(null, payload.surface_ref), ap)','approvalStalledCopy(no, ap)','src/alertcopy.test.ts'),
 ('M15j','src/alertcopy.ts','  const why = DEADMAN_AXIS[axis] ?? "응답이 없습니다";','  const why = DEADMAN_AXIS[axis] ?? (p.reason ? `사유 ${clip(p.reason, 80)}` : "응답이 없습니다");','src/alertcopy.test.ts'),
 ('M16a','src/main.ts','  if (!raw) return;\n  const d = document.createElement("details");','  return;\n  const d = document.createElement("details");','src/toastraw.test.ts'),
 ('M16b','src/main.ts','"부서 완전 삭제 실패", `${nm} 부서는 삭제되지 않았습니다. 다시 시도해 주세요.`, undefined, String(e));','"부서 완전 삭제 실패", `${nm}: ${e} — 삭제되지 않았습니다.`);','src/toastraw.test.ts'),
 ('M16c','src/main.ts','detail: raw ? `${detail}\\n${RAW_DETAIL_LABEL}: ${raw}` : detail','detail','src/toastraw.test.ts'),
 ('M16d','src/main.ts','undefined, `${String(e)}\\n상태 확인: cys factory-reset --plan`);','undefined);','src/toastraw.test.ts'),
 ('M16e','src/updateplan.ts','title: `새 자비스 구성 ${i.packVersion} — 재시작 없이 적용`,','title: `팩 ${i.packVersion} (무중단·세션 유지)`,','src/toastraw.test.ts'),
 ('M16f','src/main.ts','    : `받은 파일이 진짜인지 확인한 뒤 앱을 바꾸고 다시 켭니다. 재시작 직전에 하던 대화를 저장하고, 다시 켜지면 창과 대화가 돌아옵니다. 저장 직전 몇 초 사이의 입력은 빠질 수 있습니다.`;','    : `저장(drain) 신호 후 다운로드·서명 검증·교체하고 앱을 재시작합니다.`;','src/toastraw.test.ts'),
 ('M16g','src/main.ts','  setToastRaw(el, raw);\n  el.style.cursor','  el.style.cursor','src/toastraw.test.ts'),
 ('M17a','src/main.ts','      sid.textContent = c.name ? c.name : String(c.surfaceId);','      sid.textContent = c.name ? c.name : tag ? `${tag}:${c.surfaceId}` : String(c.surfaceId);','src/ctxgroup.test.ts'),
 ('M17b','src/wsusage.ts','    if (showSocket && !r.name && r.socket !== last) {','    if (showSocket && !r.name) {','src/ctxgroup.test.ts'),
 ('M17c','src/wsusage.ts','    if (showSocket && !r.name && r.socket !== last) {','    if (showSocket && r.socket !== last) {','src/ctxgroup.test.ts'),
 ('M17d','src/main.ts','  return ws ? wsLabel(ws) : (deptNameFromSocket(socket)','  return ws ? String(ws.name) : (deptNameFromSocket(socket)','src/ctxgroup.test.ts'),
 ('M18a','src/main.ts','  noLabel = "취소",\n): Promise<boolean> {','  noLabel = "아니오",\n): Promise<boolean> {','src/confirmlabel.test.ts'),
 ('M15k','src/alertcopy.ts','  const prev = prevNo != null ? seatName(prevNo, null, p.dept) : "옛 창";','  const prev = prevNo != null ? `${prevNo}번 창` : "옛 창";','src/alertcopy.test.ts'),
 ('M13c','src/panetitle.ts','  if (t === stripExited(shownBefore).trim()) return null;\n','','src/panetitle.test.ts'),
 ('M13d','src/main.ts','const name = renameCommitTitle(titleEl.textContent || "", shownBefore, titleEl.dataset.ruleTitle ?? null);','const name = (titleEl.textContent || "").trim() as string | null;','src/panetitle.test.ts'),
 ('M13e','src/main.ts','        if (rule) rt.titleEl.dataset.ruleTitle = rule;\n','','src/panetitle.test.ts'),
 ('M13g','src/panetitle.ts','  return ruleTitle ?? "";','  return "";','src/panetitle.test.ts'),
 ('M13h','src/panetitle.ts','  const t = stripExited(typed).trim();','  const t = typed.trim();','src/panetitle.test.ts'),
 ('M13i','src/panetitle.ts','  return role && title && title.startsWith(`${sid}${SEP}`) ? title : null;','  return title && title.startsWith(`${sid}${SEP}`) ? title : null;','src/panetitle.test.ts'),
 ('M16h','src/main.ts','  d.open = wasOpen;\n','','src/toastraw.test.ts'),
 ('M14h','src/main.ts','if (r && r.stale !== true && !Number.isFinite(usedPctOf(r.used_pct))) r = undefined;','if (r && !Number.isFinite(usedPctOf(r.used_pct))) r = undefined;','src/wsusage-null.test.ts'),
 ('M14i','src/wsusage.ts','  if (typeof v === "string" && v.trim() !== "") return Number(v);','  if (typeof v === "string") return Number(v);','src/wsusage-null.test.ts'),
 ('M12f','src/main.ts','if (isMasterSeatSignal(name, payload) && !factoryResetting && !resetCompleted) maybeShowRestoreBrief();','if (isMasterSeatSignal(name, payload)) maybeShowRestoreBrief();','src/restorebrief.test.ts'),
 ('M17e','src/style.css','.wsu-ctx-group { margin-top: 4px; font-size: .9em;','.wsu-ctx-group { margin-top: 4px; font-size: 10px;','src/ctxgroup.test.ts'),
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
