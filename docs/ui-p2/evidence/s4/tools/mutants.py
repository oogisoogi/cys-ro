#!/usr/bin/env python3
"""조각 4 뮤턴트 — 소스를 한 군데씩 바꿔 시험이 붉어지는지(TICKET=cysr-ui-slice4-1118 · fix2-1118 codex 1R 되돌림 뮤턴트 덧붙임).

각 뮤턴트: 바꿈 → `bun test src/views` 실패 수 → (e2e=True 면) build + confirm_gate 실패 수 → `git checkout -- <파일>` 원복 → 원복 확인.
전제: 작업트리가 커밋된 상태(원복 = git). 실행: python3 docs/ui-p2/evidence/s4/tools/mutants.py  (PY·CHROME_PATH 환경변수 = e2e 용)
"""
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
UI = ROOT / "ui"
J = "ui/src/views/judge/confirms.ts"
B = "ui/src/views/chat/band.ts"
C = "ui/src/views/confirm.ts"

# (이름, 파일, 바꿀 글, 새 글, e2e 도 돌릴까)
MUTANTS = [
    # 멈춤 판정
    ("멈춤: 마스터 좌석 없음 무시", J, 'if (absent && i.absentSince !== null && i.now - i.absentSince >= ABSENT_GRACE_MS) return i.masterSid === null ? "no_master" : "master_off";', 'if (absent && i.masterSid !== null && i.absentSince !== null && i.now - i.absentSince >= ABSENT_GRACE_MS) return "master_off";', False),
    ("멈춤: 꺼짐 무시", J, 'const absent = i.masterSid === null || i.masterAlive === false;', 'const absent = i.masterSid === null;', False),
    ("멈춤: deadman 무시", J, 'if (d && i.now - d.at <= DEADMAN_MAX_AGE_MS && !deadmanRevived(i)) return "deadman";', "", True),
    ("멈춤: deadman 풀림 판정 없음(한 번이면 영원히)", J, "if (d && i.now - d.at <= DEADMAN_MAX_AGE_MS && !deadmanRevived(i))", "if (d && i.now - d.at <= DEADMAN_MAX_AGE_MS)", False),
    ("멈춤: approval.stalled 무시", J, 'if (i.stalledIds.has(a.request_id)) return "stalled_event";', "", False),
    ("멈춤: 5분 규칙에서 마스터 소식 조건 뺌", J, " && i.masterIdleSecs !== null && i.masterIdleSecs * 1000 >= CONFIRM_STALL_MS", "", False),
    ("멈춤: 늘 멈춤(평소에도 직접 단추)", J, "export function itemStall(i: StallInput, a: FeedApproval): StallWhy | null {", 'export function itemStall(i: StallInput, a: FeedApproval): StallWhy | null {\n  if (a) return "quiet";', True),
    # 독립 검증(2160) 1회 고침 — F0~F9 · 시험 구멍 V3·W26·V14·V17·V18
    ("V3 풀림에서 꺼짐 확정 거르기 뺌(꺼진 마스터 출력도 풀림)", J, "return i.masterAlive !== false && i.masterSid !== undefined && i.masterSid !== null &&", "return i.masterSid !== undefined && i.masterSid !== null &&", False),
    ("F2 마스터 모름이어도 deadman 근거", J, "if (i.masterSid === undefined) return null; // 마스터 상태 모름", "if (false) return null; // 마스터 상태 모름", False),
    ("F2 deadman 나이 상한 뺌", J, "if (d && i.now - d.at <= DEADMAN_MAX_AGE_MS && !deadmanRevived(i))", "if (d && !deadmanRevived(i))", False),
    ("F2 deadman 걸쇠(풀림 보면 지움) 뺌", C, "if (this.deadman && deadmanRevived(this.stallInput())) this.deadman = null;", "", False),
    ("F0 좌석이 올린 approval 도 screen", J, 'const screen = f.daemon_issued === true || (f.daemon_issued === undefined && f.request_id.startsWith("daemon-"));', "const screen = true;", True),
    ("F0 itemStall 의 screen 거르기 뺌", J, "if (!a.screen) return null;", "", False),
    ("F1 slug 붙은 사건 전부 버림(옛 동작)", C, 'if (this.hqSlug === null || typeof e.socket_slug !== "string" || e.socket_slug === "" || e.socket_slug !== this.hqSlug) return;', "if (e.socket_slug) return;", True),
    ("F1 다른 slug 사건도 받음", C, 'if (this.hqSlug === null || typeof e.socket_slug !== "string" || e.socket_slug === "" || e.socket_slug !== this.hqSlug) return;', "", True),
    ("W26 못 나아가면 다 훑음(옛 동작)", C, "        // 못 나아감(아직 끝나지 않은 긴 줄 등) — 「다 훑음」으로 확정하지 않는다(모름 유지 · 다음 틱에 다시 · 검증 F3)\n        this.changed();", "        this.priorDone = true;\n        this.changed();", False),
    ("F3 건너뛴 긴 줄 = 모름 표시 뺌", C, 'if (typeof r.skipped_bytes === "number" && r.skipped_bytes > 0) this.lossy = true;', "", False),
    ("F4 해결 글 깎기 되살림(20번째 공백 잃음)", J, "const key = line.slice(RESOLVE_PREFIX.length, line.length - MARK_END.length);", "const key = line.slice(RESOLVE_PREFIX.length, line.length - MARK_END.length).trim();", False),
    ("F5 유예 뺌", J, "if (absent && i.absentSince !== null && i.now - i.absentSince >= ABSENT_GRACE_MS)", "if (absent)", False),
    ("F6 처리 직전 org 낡음 검사 뺌", C, "const stale = this.d.now() - t0 > ORG_MAX_MS;", "const stale = false;", False),
    ("F8 들여쓴·물결 울타리 무시(옛 동작)", J, r"const f = /^\s*(`{3,}|~{3,})/.exec(raw);", r"const f = /^(`{3,})/.exec(raw);", False),
    ("V14 꼴 깨진 시각 칸 = 건너뜀", J, 'if (typeof f.created_at !== "number" || !Number.isFinite(f.created_at)) return null;', 'if (typeof f.created_at !== "number" || !Number.isFinite(f.created_at)) continue;', False),
    ("V14 꼴 깨진 번호 칸 = 건너뜀", J, 'if (typeof f.request_id !== "string" || !f.request_id) return null;', 'if (typeof f.request_id !== "string" || !f.request_id) continue;', False),
    ("V17·V18 끝 너머 레코드도 앞 기록으로(위치 가르기 뺌)", C, "if (crossing && (rec.at as number) >= s.end) {", "if (false) {", False),
    # 펼침 조건
    ("펼침: 허락 펼침 조건 뺌(판정)", J, 'if (decision === "allow" && !expanded)', "if (false)", True),
    ("펼침: 멈춤 아닌 항목도 준비됨", J, 'if (item.kind !== "helper" || item.stall === null) return', 'if (item.kind !== "helper") return', False),
    ("펼침: 그리기가 펼침 여부 대신 늘 펼침으로 넘김", B, "const r = allowReady(it, expanded.has(it.key), dec);", "const r = allowReady(it, true, dec);", True),
    # (1차 실행에서 「판이 바뀌어도 펼침 유지 = 정리 줄 뺌」은 등가 뮤턴트였다 — 펼침 열쇠가 본문을 담아 정리 없이도 새 판은 접힘. 보호 지점 = 판 열쇠)
    ("펼침: 판 열쇠에서 본문·시각 뺌(같은 번호면 펼침 이어짐)", J, "return JSON.stringify([a.request_id, a.created_at, a.body, a.surface_id, a.fingerprint]);", "return a.request_id;", True),
    # 판 묶기
    ("판 묶기: 본문 대조 뺌", J, "a.created_at !== b.created_at || a.body !== b.body || a.surface_id !== b.surface_id", "a.created_at !== b.created_at || a.surface_id !== b.surface_id", True),
    ("판 묶기: 지문 대조 뺌", J, " || a.fingerprint !== b.fingerprint) return no(\"changed\");", ") return no(\"changed\");", False),
    ("판 묶기: 시각 대조 뺌", J, "a.created_at !== b.created_at || a.body !== b.body", "a.body !== b.body", False),
    ("판 묶기: 이미 처리됨(목록 없음) 통과", J, 'if (!a) return no("gone");', "if (!a) return { ok: true };", True),
    ("판 묶기: 재확인 때 멈춤 다시 보기 뺌", J, 'if (stallNow(a) === null) return no("not_stalled");', "", False),
    ("판 묶기: 처리 직전 재조회 대신 그리기 때 값", C, 'const rc = recheck(bound, fresh, (a) => (st.masterSid !== undefined && st.masterSid !== null && a.surface_id === st.masterSid ? null : itemStall(st, a)));', "const rc = { ok: true as const } as ReturnType<typeof recheck>;", True),
    ("판 묶기: 연타 막기 뺌", C, "if (this.deciding) return;\n    this.deciding = true;", "this.deciding = true;", False),
    # 신뢰 클릭
    ("신뢰 클릭: isTrusted 검사 뺌", B, "if (!e.isTrusted) return; // 사람이 실제로 누른 클릭만", "// 뺌", True),
    # 표식
    ("표식: 줄머리 대신 줄 어디든", J, "if (line.startsWith(ASK_PREFIX)) {", "if (line.includes(ASK_PREFIX)) {", False),
    ("표식: 사람(user) 글도 표식", J, 'if (r.role !== "assistant" || r.sidechain', "if (r.sidechain", False),
    ("표식: 앞 훑기 위치 모르면 확정 안 함 뺌", C, "if (crossing && recs.some((rec) => typeof rec.at !== \"number\" || !Number.isFinite(rec.at))) {", "if (false) {", False),
    # codex 1R(02:51 · e62e1fb0) 고침 되돌림 — 지적마다 「고침 뺌 = 옛 동작」 이 붉어야 한다(재현 시험 붉음→초록의 붉음 쪽)
    ("blocking: 지문 표지 없어도 직접 허락(canAllowDirect 늘 참)", J, "return a.screen && a.fingerprint !== null;", "return a.screen;", True),
    ("blocking: allowReady 지문 검사 뺌", J, 'if (decision === "allow" && !canAllowDirect(item.a)) return { ok: false, msg: ALLOW_AT_WORK_MSG };', "", False),
    ("blocking: decide 지문 가드 뺌", C, 'if (decision === "allow" && bound.fingerprint === null) {', "if (false) {", False),
    ("blocking: 그리기가 지문 없는 판에도 허락 단추", B, "if (!canAllowDirect(a)) {", "if (false) {", True),
    ("major 1: 생존 모름 관측도 deadman 근거(옛 동작)", J, "if (d && i.masterSid !== null && i.masterAlive === null) return null;", "", False),
    ("major 1: 풀림은 생존 확정만(옛 V3 조건)", J, "return i.masterAlive !== false && i.masterSid !== undefined", "return i.masterAlive === true && i.masterSid !== undefined", False),
    ("major 2: 판 열쇠에서 좌석 뺌", J, "JSON.stringify([a.request_id, a.created_at, a.body, a.surface_id, a.fingerprint])", "JSON.stringify([a.request_id, a.created_at, a.body, a.fingerprint])", True),
    ("major 2: 판 열쇠에서 지문 뺌", J, "JSON.stringify([a.request_id, a.created_at, a.body, a.surface_id, a.fingerprint])", "JSON.stringify([a.request_id, a.created_at, a.body, a.surface_id])", False),
    ("major 3: slug 없음·null·빈 사건 받음(옛 동작)", C, 'if (this.hqSlug === null || typeof e.socket_slug !== "string" || e.socket_slug === "" || e.socket_slug !== this.hqSlug) return;', 'if (e.socket_slug !== undefined && e.socket_slug !== null && e.socket_slug !== "" && (this.hqSlug === null || e.socket_slug !== this.hqSlug)) return;', False),
    ("major 4: 처리 직전 org 꼴 깨짐 통과", C, "if (org === undefined || stale || mo === undefined) {", "if (org === undefined || stale) {", False),
    ("major 4: 마스터 좌석 모름에도 직접 단추", J, "if (i.masterSid === undefined) return null; // 마스터 좌석 모름", "if (false) return null; // 마스터 좌석 모름", False),
    ("major 5: 기록만 해소도 「했어요」", C, "if (actuatedOf(res) !== null) this.notice", "if (true) this.notice", True),
    # codex 2R(6bbaae53 · 코드 ee510b85) 고침 되돌림
    ("2R major 1: masterOf 깨진 번호 행을 버리고 마스터 없음(옛 동작)", C, "if (live.some((r) => typeof r.surface_id !== \"number\" || !Number.isSafeInteger(r.surface_id))) return undefined;", "if (false) return undefined;", False),
    ("2R major 1: 주기 관측의 org 원문 마스터 행 대조 뺌", C, "if (org !== undefined && master !== undefined && masterOf(org) === undefined) master = undefined;", "", False),
    ("2R minor: 물음 글 깎기 되살림", J, "const text = line.slice(ASK_PREFIX.length, line.length - MARK_END.length);", "const text = line.slice(ASK_PREFIX.length, line.length - MARK_END.length).trim();", False),
    ("2R minor: resolveKey 깎기 되살림", J, "return Array.from(s).slice(0, RESOLVE_KEY_LEN).join(\"\");", "return Array.from(s.trim()).slice(0, RESOLVE_KEY_LEN).join(\"\");", False),
    ("major 6: 공백 정규화 되살림(앞 고침 F4)", J, "return key.length > 0 && Array.from(key).length >= need && question.startsWith(key);", "const n = (x: string) => x.replace(/\\s+/g, \" \").trim();\n  return n(key).length > 0 && Array.from(n(key)).length >= Math.min(RESOLVE_KEY_LEN, Array.from(n(question)).length) && n(question).startsWith(n(key));", False),
]


def run(cmd, cwd, env=None):
    p = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, shell=isinstance(cmd, str))
    return p.returncode, p.stdout + p.stderr


def bun_fails() -> int:
    _, out = run(["bun", "test", "src/views"], UI)
    m = re.search(r"(\d+) fail", out)
    return int(m.group(1)) if m else -1


def e2e_fails() -> int:
    rc, _ = run("sh build.sh", UI)
    if rc != 0:
        return -1
    env = dict(os.environ)
    rc, out = run(["cys", "run", "--", env.get("PY", "python3"), "ui/e2e/confirm_gate.py"], ROOT, env)
    return len(re.findall(r"^  FAIL ", out, re.M)) + (1 if "Traceback" in out else 0)


def main() -> int:
    if run(["git", "status", "--porcelain", "ui/src"], ROOT)[1].strip():
        print("작업트리가 깨끗하지 않음 — 먼저 커밋")
        return 2
    rows = []
    only = os.environ.get("MUT_ONLY")
    for name, f, old, new, e2e in MUTANTS:
        if only and only not in name:
            continue
        p = ROOT / f
        src = p.read_text(encoding="utf-8")
        if src.count(old) != 1:
            rows.append((name, "바꿀 글 못 찾음", "", ""))
            continue
        p.write_text(src.replace(old, new), encoding="utf-8")
        try:
            b = bun_fails()
            e = e2e_fails() if e2e else None
        finally:
            run(["git", "checkout", "--", f], ROOT)
        restored = p.read_text(encoding="utf-8") == src
        rows.append((name, b, e, restored))
        print(f"{name}: bun 붉음 {b} · e2e 붉음 {e} · 원복 {restored}", flush=True)
    run("sh build.sh", UI)
    red = sum(1 for r in rows if (isinstance(r[1], int) and r[1] > 0) or (isinstance(r[2], int) and r[2] > 0))
    print(f"\n뮤턴트 {len(rows)} 중 붉음 {red} · 원복 전부 {all(r[3] is True for r in rows)}")
    return 0 if red == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())
