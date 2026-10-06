#!/usr/bin/env python3
"""U4 뮤테이션(1.1.8 · 설계 §3-12 · 📌18) — 원본을 고쳐 대상 시험을 돌려 적색(rc!=0)을 확인하고 원본을 바이트 그대로 되돌린다.

사용: python3 scripts/tests/u4-mutants.py   (리포 안 어디서든)
  · Rust 시험은 격리 래퍼를 앞에 붙여 돌릴 수 있다 — 환경변수 U4_ISOENV=<래퍼 경로>(없으면 cargo 를 그대로 부른다).
  · bun 은 PATH 또는 ~/.bun/bin 에서 찾는다.
  · 생존 뮤턴트가 하나라도 있으면 exit 1.
"""
import subprocess, sys, os
W=subprocess.run(["git","rev-parse","--show-toplevel"],capture_output=True,text=True,cwd=os.path.dirname(os.path.abspath(__file__))).stdout.strip()
RS=f"{W}/src-tauri/src/updnotice.rs"; TS=f"{W}/ui/src/main.ts"
RUST=([os.environ["U4_ISOENV"]] if os.environ.get("U4_ISOENV") else [])+["cargo","test","-p","cys-app","updnotice"]
BUN=["env",f"PATH={os.environ['HOME']}/.bun/bin:{os.environ.get('PATH','/usr/bin:/bin')}","bun","test","src/updateresult.test.ts"]
M=[
 ("M1 ②표시 전 기록 생략(순서 바꿈)",RS,"Plan::Show { ack: next, toast } => write_ack(dir, &next).ok().map(|_| toast),","Plan::Show { toast, .. } => Some(toast),",RUST,W),
 ("M2 shown_count 미증가",RS,"shown_count: prior + 1 });","shown_count: prior });",RUST,W),
 ("M3 중복 무제한",RS,"if prior >= MAX_SHOWS {","if false && prior >= MAX_SHOWS {",RUST,W),
 ("M4 롤백 실패 하루 1회 → 매번",RS,"Some(at) => now - at >= ROLLBACK_FAILED_REPEAT_SECS ||","Some(at) => now - at >= 0 ||",RUST,W),
 ("M5 notes 제어문자·금지 어휘·상한 통과",RS,"if cys::update::feed::check_notes_ko(n).is_err() || n.chars().any(is_forbidden_char) {","if false {",RUST,W),
 ("M6 좌석 0 사유 무시",RS,'.and_then(Value::as_str) == Some("journal_unrecoverable")).then_some',".and_then(Value::as_str).is_some()).then_some",RUST,W),
 ("M7 기록 실패해도 표시",RS,"Plan::Show { ack: next, toast } => write_ack(dir, &next).ok().map(|_| toast),","Plan::Show { ack: next, toast } => { let _ = write_ack(dir, &next); Some(toast) }",RUST,W),
 ("M8 UI ③④ 뒤바꿈",TS,'    stickyToast(n.toastId, "feed", n.title, n.body);\n    await invoke("update_result_notice_done", { resultId: n.resultId });\n','    await invoke("update_result_notice_done", { resultId: n.resultId });\n    stickyToast(n.toastId, "feed", n.title, n.body);\n',BUN,f"{W}/ui"),
 ("M9 UI 고정 안내 innerHTML",TS,'  el.textContent = text ?? "";\n  el.hidden = text === null;','  el.innerHTML = text ?? "";\n  el.hidden = text === null;',BUN,f"{W}/ui"),
 ("M11 (2판) 장부 잠금 없음 — 경쟁(둘 다 제거)",RS,"    let _g = ACK_MUTEX.lock().unwrap_or_else(|e| e.into_inner());\n    #[cfg(test)]\n    cs_probe::arrive(dir);\n    let lf = std::fs::OpenOptions::new().create(true).truncate(false).write(true).open(dir.join(LOCK_FILE))?;\n    lf.lock()?;\n","    let _ = &ACK_MUTEX;\n    #[cfg(test)]\n    cs_probe::arrive(dir);\n    let lf = std::fs::OpenOptions::new().create(true).truncate(false).write(true).open(dir.join(LOCK_FILE))?;\n    let _ = &lf;\n",RUST,W),
 ("M11a (3판) 프로세스 뮤텍스만 없음",RS,"    let _g = ACK_MUTEX.lock().unwrap_or_else(|e| e.into_inner());\n","    let _ = &ACK_MUTEX;\n",RUST,W),
 ("M11b (3판) 파일 잠금만 없음 — 두 프로세스",RS,"    lf.lock()?;\n","    let _ = &lf;\n",RUST,W),
 ("M12 (2판) release_seq 검사 없음",RS,"    if last.get(\"release_seq\").and_then(Value::as_u64).filter(|n| *n >= 1).is_none() {","    if false {",RUST,W),
 ("M13 (2판) UI 역순 응답 적용",f"{W}/ui/src/updateresult.ts","    if (mine !== gen) return;\n","",BUN,f"{W}/ui"),
 ("M14 (2판) UI 고정 안내 폴링 없음",TS,"  setInterval(() => void refreshSeatsBlockedNote(), SEATS_NOTE_POLL_MS);\n","",BUN,f"{W}/ui"),
 ("M10 UI 모르는 토스트 id 통과",f"{W}/ui/src/updateresult.ts","if (toastId !== UPDATE_RESULT_TOAST_ID && toastId !== UPDATE_ROLLBACK_FAILED_TOAST_ID) return null;","if (typeof toastId !== \"string\") return null;",BUN,f"{W}/ui"),
]
bad=0
for name,path,old,new,cmd,cwd in M:
    orig=open(path,"rb").read(); s=orig.decode()
    assert s.count(old)==1,(name,s.count(old))
    open(path,"wb").write(s.replace(old,new).encode())
    try:
        r=subprocess.run(cmd,cwd=cwd,capture_output=True,text=True,timeout=900)
    finally:
        open(path,"wb").write(orig)
    red = r.returncode!=0
    print(f"{'OK  ' if red else 'LIVE'} {name} rc={r.returncode}")
    if not red: bad+=1
print("생존 뮤턴트", bad, "/", len(M)); sys.exit(1 if bad else 0)
