[리뷰 의뢰 — 엄격 제약 준수 · 지정 범위만 · 읽기 전용]
저장소 = /private/tmp/claude-501/-Users-<사용자>-axdev--wt-cys-1116-integ/f735c79c-f628-4381-8653-1eb57b0995c2/scratchpad/cx (가지 integ/1116 · HEAD d858abb3 = merge commit). 쓰기 금지 · 서버·빌드·장시간 프로세스 금지 · 파일 읽기와 git 읽기 명령만.
검토 범위(이 범위만, 무관 파일·repo 배회 금지): 아래 remerge diff(자동 병합 결과 대비 사람이 한 충돌 해결 차이) + 그 해결이 닿는 곳:
  ui/src/views/core.ts · ui/src/views/index.ts · ui/src/views/chat/index.ts · ui/src/views/confirm.ts(onEvent·scanStep·startSession·resetSession·onTail 만) · ui/src/views/confirm.test.ts(키 이름 바꿈만) · src-tauri/src/viewcore.rs parse_transcript_chunk(+그 시험)
비교 기준: 부모1 = 75dc2640(조각 1+3 들어간 integ) · 부모2 = fa400dda(feat/ui-slice4 = 조각 1+4). `git show 75dc2640:<경로>` · `git show fa400dda:<경로>` 로 각 쪽 원본을 볼 수 있다.

과업: merge d858abb3 의 충돌 해결이 ① 두 쪽(조각 3 · 조각 4) 동작을 모두 살렸는지 ② 해결이 새 결함을 만들지 않았는지 적대 검토. 특히:
  - 조각 3 의 deps.listen(name, handler) 구독(core.startListening · onDaemonEvent · input.refused_at_write · queue 사건)과 조각 4 의 구독(원래 이름 listen(fn) → 해결에서 listenDaemon(fn) 으로 바꿈 · confirm.onEvent)이 둘 다 attach 에서 걸리고 detach 에서 풀리는가 · 자동 병합이 두 쪽에 같은 필드 unlisten 을 쓰게 만들었던 것을 unlisten / unlistenConfirm 으로 가른 것이 맞는가 · 경합(붙였다 뗐다)에서 새는 구독이 없는가
  - poll 의 세션 읽기 조건 합침: (활동 바뀜 ∧ (기다리는 말 ∨ 쉬게 됨)) ∨ (기다리는 말 ∧ 조회 사이 새 출력) — 두 쪽 조건의 합집합과 같은가
  - initOffset 의 ok 갈래에서 confirm.startSession 호출 위치(조각 3 의 세대·상한 구조 안) · stale/none 갈래에서 조각 4 가 기대하던 동작이 빠지지 않았나 · reset 갈래 두 줄
  - viewcore.rs: 조각 3 이 추가한 role:"link" 고리 레코드에 조각 4 의 줄 위치 at 을 실음 — 조각 4 confirm.ts scanStep 은 끝을 넘는 토막에 at 없는 레코드가 하나라도 있으면 「다 훑음」을 확정하지 않는다(그래서 넣음). 이 판단이 맞는가 · 다른 소비자(msgstep applyRecords · rematchPending · logOrder · confirm onTail/markersOf)가 link + at 조합에서 오동작하지 않는가
  - chat/index.ts: masterBubble(text, uuid) 를 logOrder 고리 안 두 곳에 · band.paint() 위치 · autos 줄
  - freshBounded 반환형에 feed·org 추가(실행 값은 원래도 실려 왔음)
판정 형식: 마지막 메시지 = 아래 JSON 하나만(다른 글 없이). score 금지. verdict enum + evidence(file:line).
{"verdict": "ACCEPT|REVISE|BLOCK|ESCALATE", "justification": "", "evidence": [{"claim": "", "ref": "file:line", "verified": true}], "issues": [{"severity": "blocking|major|minor", "where": "file:line", "what": "", "fix": ""}], "missing": [], "revision": "d858abb3"}

=== remerge diff (git show --remerge-diff d858abb3) ===
diff --git a/src-tauri/src/viewcore.rs b/src-tauri/src/viewcore.rs
remerge 충돌 (내용): src-tauri/src/viewcore.rs에 병합 충돌
index 120cd6ec..85a485e2 100644
--- a/src-tauri/src/viewcore.rs
+++ b/src-tauri/src/viewcore.rs
@@ -197,14 +197,10 @@ fn content_text(content: &Value) -> (Option<String>, Vec<String>) {
 }
 
 /// 세션 기록 덩이(순수) → (레코드들, 소비한 바이트). 줄 끝(`\n`)까지 온전한 줄만 읽고 마지막 미완 줄은 남긴다(다음 호출이 잇는다).
-<<<<<<< 75dc2640 (merge(integ · TICKET=cysr-1116-integ-1118): feat/ui-slice3 43b44ea4 — 화면 조각 1(3a012bf4) + 조각 3 보낸 말 단계 전부(독립 검증 고침 · codex 2R 고침))
-/// 레코드 = `{uuid, parent, role:"user"|"assistant", text(없으면 null), parts, ts, sidechain}` — user/assistant 전부(글 없는 고리 포함). 줄 파싱 실패는 건너뛴다(세기만).
+/// 레코드 = `{uuid, parent, role:"user"|"assistant", text(없으면 null), parts, ts, sidechain, at}` — user/assistant 전부(글 없는 고리 포함). 줄 파싱 실패는 건너뛴다(세기만).
 /// (조각 3 고침 · 검증 지적 B) 그 밖 종류(attachment·system 등)도 uuid 가 있으면 **글 없는 고리** `{uuid, parent, role:"link", text:null, …}` 로 넘긴다 —
 /// 진짜 기록은 사람 말과 첫 답 사이에 이런 레코드(훅이 덧붙인 글 등)가 끼어, 빼면 답의 부모 사슬이 끊긴다. 본문·종류 이름·시각은 넘기지 않는다(NFR-S3 · 글 0자).
-=======
-/// 레코드 = `{uuid, parent, role:"user"|"assistant", text(없으면 null), parts, ts, sidechain, at}` — user/assistant 전부(글 없는 고리 포함). 줄 파싱 실패는 건너뛴다(세기만).
 /// `at` = 그 줄이 시작하는 **덩이 안** 바이트 위치(`read_transcript_from` 이 파일 위치로 바꿈 · 조각 4 codex 1R minor — 앞 훑기·뒤 읽기 겹침을 위치로 가름).
->>>>>>> fa400dda (docs(ui · TICKET=cysr-ui-slice4-fix2-1118): HANDOFF §13 codex 1R·2R 고침 델타(지적별 처분 · 시험 숫자 전후 · 뮤턴트 56/56 · 📌 데몬 지문 계약) · TODO)
 pub(crate) fn parse_transcript_chunk(buf: &[u8]) -> (Vec<Value>, usize, usize) {
     let consumed = match buf.iter().rposition(|&b| b == b'\n') {
         Some(i) => i + 1,
@@ -236,6 +232,9 @@ pub(crate) fn parse_transcript_chunk(buf: &[u8]) -> (Vec<Value>, usize, usize) {
                     "parts": Value::Null,
                     "ts": Value::Null,
                     "sidechain": v["isSidechain"].as_bool().unwrap_or(false),
+                    // (통합 1116) 고리도 줄 위치를 싣는다 — 조각 4 앞 훑기는 끝을 넘는 토막에 위치 없는 레코드가 하나라도 있으면
+                    // 「다 훑음」을 확정하지 않으므로(confirm.ts scanStep), 위치 없는 고리가 끼면 띠가 「살펴보는 중」에 머문다. 위치 = 바이트 수(글 0자 · NFR-S3 그대로).
+                    "at": at,
                 }));
                 continue;
             }
@@ -562,6 +561,8 @@ mod tests {
         assert_eq!(recs[3]["parent"], "u2");
         assert!(recs[3]["text"].is_null() && recs[3]["parts"].is_null() && recs[3]["ts"].is_null());
         assert!(!recs[3].to_string().contains("비밀") && !recs[3].to_string().contains("hook_additional_context"), "고리에 본문·종류 이름 0");
+        // (통합 1116) 고리도 줄 시작 위치(조각 4 앞 훑기가 위치로 앞·뒤 기록을 가름)
+        assert_eq!(recs[3]["at"].as_u64(), Some((a.len() + 1 + b.len() + 1 + tool.len() + 1 + meta.len() + 1) as u64));
         assert_eq!(recs[0]["role"], "user");
         assert_eq!(recs[0]["text"], "안녕");
         assert_eq!(recs[1]["parent"], "u1");
diff --git a/ui/src/views/chat/index.ts b/ui/src/views/chat/index.ts
remerge 충돌 (내용): ui/src/views/chat/index.ts에 병합 충돌
index e6955176..69fe100e 100644
--- a/ui/src/views/chat/index.ts
+++ b/ui/src/views/chat/index.ts
@@ -6,11 +6,8 @@
 import type { ViewContext, ViewInstance, ViewModule } from "../contract";
 import { DUP, dupPending, errorCount, HEALTH_LABEL, lastSendStep, logOrder, needsClick, POLL_MS, SAME_DELIVERED_NOTE, sameTextDelivered, type ChatCore, type ChatState } from "../core";
 import { canRetry, STEP_LABEL, type Msg } from "../judge/msgstep";
-<<<<<<< 75dc2640 (merge(integ · TICKET=cysr-1116-integ-1118): feat/ui-slice3 43b44ea4 — 화면 조각 1(3a012bf4) + 조각 3 보낸 말 단계 전부(독립 검증 고침 · codex 2R 고침))
 import { AUTO_STEP_LABEL, type AutoMsg } from "../judge/autostep";
-=======
 import { createBand } from "./band";
->>>>>>> fa400dda (docs(ui · TICKET=cysr-ui-slice4-fix2-1118): HANDOFF §13 codex 1R·2R 고침 델타(지적별 처분 · 시험 숫자 전후 · 뮤턴트 56/56 · 📌 데몬 지문 계약) · TODO)
 
 function el<K extends keyof HTMLElementTagNameMap>(tag: K, cls?: string, text?: string): HTMLElementTagNameMap[K] {
   const e = document.createElement(tag);
@@ -116,7 +113,6 @@ export const chatView: ViewModule<ChatState, ChatCore> = {
       }
       return li;
     };
-<<<<<<< 75dc2640 (merge(integ · TICKET=cysr-1116-integ-1118): feat/ui-slice3 43b44ea4 — 화면 조각 1(3a012bf4) + 조각 3 보낸 말 단계 전부(독립 검증 고침 · codex 2R 고침))
     // (조각 3) 기계 문안(깨움 말·1회 안내) = 사람 말이 아니므로 말풍선이 아니라 한 줄 표지(§5-2 auto · 단계는 큐 사건으로만).
     const autoLine = (a: AutoMsg): HTMLLIElement => {
       const li = el("li", `cv-auto auto-${a.step}`, `자동 안내: ${AUTO_STEP_LABEL[a.step]}`);
@@ -124,10 +120,7 @@ export const chatView: ViewModule<ChatState, ChatCore> = {
       li.dataset.step = a.step;
       return li;
     };
-    const masterBubble = (text: string): HTMLLIElement => {
-=======
     const masterBubble = (text: string, uuid: string | null = null): HTMLLIElement => {
->>>>>>> fa400dda (docs(ui · TICKET=cysr-ui-slice4-fix2-1118): HANDOFF §13 codex 1R·2R 고침 델타(지적별 처분 · 시험 숫자 전후 · 뮤턴트 56/56 · 📌 데몬 지문 계약) · TODO)
       const li = el("li", "cv-msg cv-master");
       if (uuid) li.dataset.uuid = uuid; // (조각 4) 「대화에서 답하기」가 그 물음 자리를 찾는 표지
       li.append(el("div", "cv-who", "마스터"), el("div", "cv-text", text));
@@ -153,27 +146,18 @@ export const chatView: ViewModule<ChatState, ChatCore> = {
       notice.textContent = s.notice ?? "";
       const atBottom = log.scrollTop + log.clientHeight >= log.scrollHeight - 4;
       log.replaceChildren();
-<<<<<<< 75dc2640 (merge(integ · TICKET=cysr-1116-integ-1118): feat/ui-slice3 43b44ea4 — 화면 조각 1(3a012bf4) + 조각 3 보낸 말 단계 전부(독립 검증 고침 · codex 2R 고침))
       if (s.msgs.length === 0 && s.stray.length === 0 && s.autos.length === 0) log.append(empty);
       // (조각 3 고침 · 검증 지적 B) 어느 말에도 안 묶인 마스터 글은 시각순으로 사람 말 사이에 끼운다(사람 말들 뒤에 몰리지 않게).
       for (const it of logOrder(s.msgs, s.stray)) {
         if (it.kind === "stray") {
-          log.append(masterBubble(it.r.text));
+          log.append(masterBubble(it.r.text, it.r.uuid));
           continue;
         }
         log.append(bubble(it.m, s));
-        for (const r of it.m.replies) log.append(masterBubble(r.text));
+        for (const r of it.m.replies) log.append(masterBubble(r.text, r.uuid));
       }
       for (const a of s.autos) log.append(autoLine(a));
-=======
-      if (s.msgs.length === 0 && s.stray.length === 0) log.append(empty);
-      for (const m of s.msgs) {
-        log.append(bubble(m));
-        for (const r of m.replies) log.append(masterBubble(r.text, r.uuid));
-      }
-      for (const r of s.stray) log.append(masterBubble(r.text, r.uuid));
       band.paint(); // (조각 4) 말 목록을 다시 그린 뒤 — 답하는 물음 자리 표시를 다시 단다
->>>>>>> fa400dda (docs(ui · TICKET=cysr-ui-slice4-fix2-1118): HANDOFF §13 codex 1R·2R 고침 델타(지적별 처분 · 시험 숫자 전후 · 뮤턴트 56/56 · 📌 데몬 지문 계약) · TODO)
       if (atBottom) log.scrollTop = log.scrollHeight;
     };
     ctx.subscribe(paint);
diff --git a/ui/src/views/confirm.test.ts b/ui/src/views/confirm.test.ts
index 1153a034..ba63ab09 100644
--- a/ui/src/views/confirm.test.ts
+++ b/ui/src/views/confirm.test.ts
@@ -58,7 +58,7 @@ function harness(o: { prior?: Array<Record<string, unknown>>; chunk?: number } =
     store: { get: (k) => mem.get(k) ?? null, set: (k, v) => void mem.set(k, v), remove: (k) => void mem.delete(k) },
     working: (r) => r.working === true,
     defaultSlug: async () => "hq-slug-0001",
-    listen: (fn) => {
+    listenDaemon: (fn) => {
       listenCalls++;
       listeners.push(fn);
       return () => {
diff --git a/ui/src/views/core.ts b/ui/src/views/core.ts
remerge 충돌 (내용): ui/src/views/core.ts에 병합 충돌
index 64f4bc7b..fe9da2c3 100644
--- a/ui/src/views/core.ts
+++ b/ui/src/views/core.ts
@@ -11,13 +11,9 @@
 
 import { composeOutbound } from "./judge/outbound";
 import { approvalSeatsOf, masterRowOf, sendGate, type GateVerdict, type MasterRow } from "./judge/gate";
-<<<<<<< 75dc2640 (merge(integ · TICKET=cysr-1116-integ-1118): feat/ui-slice3 43b44ea4 — 화면 조각 1(3a012bf4) + 조각 3 보낸 말 단계 전부(독립 검증 고침 · codex 2R 고침))
 import { applyRecords, applyRefusedAtWrite, canRetry, mergeOutcome, READ_AFTER_MS, rematchPending, SENDING_SILENT_MS, settleSteps, SLOW_MS, stepFromOutcome, type Msg, type PendingRec, type Rec, type Reply, type Step } from "./judge/msgstep";
 import { applyQueueEvent, autoHoldRemainingMs, queueEventOf, type AutoMsg } from "./judge/autostep";
-=======
-import { applyRecords, canRetry, READ_AFTER_MS, settleSteps, stepFromOutcome, type Msg, type Rec, type Reply } from "./judge/msgstep";
 import { ConfirmBook } from "./confirm";
->>>>>>> fa400dda (docs(ui · TICKET=cysr-ui-slice4-fix2-1118): HANDOFF §13 codex 1R·2R 고침 델타(지적별 처분 · 시험 숫자 전후 · 뮤턴트 56/56 · 📌 데몬 지문 계약) · TODO)
 
 export const HOLD_KEY = "cys-chat-hold";
 /** 붙잡은 말 상한(설계 §5-3 · 넘으면 새 말을 받지 않고 안내). */
@@ -103,8 +99,9 @@ export interface Deps {
   store: Store;
   /** org.status 행 → 지금 답하는 중인가(appearance.nodeWorking) */
   working(row: Record<string, unknown>): boolean;
-  /** (조각 4) daemon-event 구독 — 대화 화면이 켜져 있을 때만(attach~detach). 없으면 사건 없이(멈춤 = org.status·5분 규칙만). */
-  listen?(fn: (ev: unknown) => void): () => void;
+  /** (조각 4) daemon-event 구독 — 대화 화면이 켜져 있을 때만(attach~detach). 없으면 사건 없이(멈춤 = org.status·5분 규칙만).
+   *  (통합 1116) 조각 3 의 `listen(name, handler)` 와 이름이 겹쳐 `listenDaemon` 으로 — 두 구독 모두 그대로 산다. */
+  listenDaemon?(fn: (ev: unknown) => void): () => void;
   /** (조각 4) 다른 화면으로(「작업 화면에서 보기」) — registry.choose. */
   goView?(id: string): void;
   /** (조각 4 · 검증 F1) 본부 데몬 socket_slug(Tauri default_socket_slug) — 사건의 slug 대조용 · 대화 화면이 켜질 때 1회. */
@@ -174,7 +171,6 @@ export class ChatCore {
   private readTimers = new Set<unknown>();
   private attached = false;
   private lastWorking: boolean | null = null;
-<<<<<<< 75dc2640 (merge(integ · TICKET=cysr-1116-integ-1118): feat/ui-slice3 43b44ea4 — 화면 조각 1(3a012bf4) + 조각 3 보낸 말 단계 전부(독립 검증 고침 · codex 2R 고침))
   /** (조각 3) 지난 조회 시각 — 「두 조회 사이 새 출력」 판정용 */
   private lastPollAt: number | null = null;
   /** (조각 3) 사건 구독 해제 함수 · 구독 세대(붙였다 뗐다 경합 방지) · 기본 데몬 소켓 이름(부서 데몬 사건과 좌석 번호가 겹침) */
@@ -187,11 +183,10 @@ export class ChatCore {
   private pendingUser: PendingRec[] = [];
   /** (codex 1R major) 세션 시작점 조회 세대 — 늦게 돌아온 옛 조회(시간 상한을 넘겼거나 뒤 조회가 이미 시작된 것)는 offset·세션을 바꾸지 못한다 */
   private initGen = 0;
-=======
   /** (조각 4) 확인 대기 장부 — 띠·표식·직접 허락. */
   readonly confirm: ConfirmBook;
-  private unlisten: (() => void) | null = null;
->>>>>>> fa400dda (docs(ui · TICKET=cysr-ui-slice4-fix2-1118): HANDOFF §13 codex 1R·2R 고침 델타(지적별 처분 · 시험 숫자 전후 · 뮤턴트 56/56 · 📌 데몬 지문 계약) · TODO)
+  /** (조각 4 · 통합 1116) 장부용 사건 구독 해제 — 조각 3 구독(unlisten)과 따로 든다(두 구독 모두 대화 화면 attach~detach 동안만). */
+  private unlistenConfirm: (() => void) | null = null;
 
   constructor(private readonly d: Deps) {
     this.loadHold();
@@ -226,7 +221,7 @@ export class ChatCore {
   /** 대화 화면이 켜짐 — 세션 기록 읽기 허용 · 시작 오프셋 잡기. */
   attach(): void {
     this.attached = true;
-    if (!this.unlisten && this.d.listen) this.unlisten = this.d.listen((ev) => this.confirm.onEvent(ev));
+    if (!this.unlistenConfirm && this.d.listenDaemon) this.unlistenConfirm = this.d.listenDaemon((ev) => this.confirm.onEvent(ev));
     if (this.d.defaultSlug)
       void this.d
         .defaultSlug()
@@ -239,8 +234,8 @@ export class ChatCore {
   /** 대화 화면이 내려감 — 읽기 예약 해제(공통층 상태·붙잡은 말은 그대로 · §4-3). */
   detach(): void {
     this.attached = false;
-    this.unlisten?.();
-    this.unlisten = null;
+    this.unlistenConfirm?.();
+    this.unlistenConfirm = null;
     for (const h of this.readTimers) this.d.clearTimeout(h);
     this.readTimers.clear();
     this.listenGen++;
@@ -395,7 +390,7 @@ export class ChatCore {
 
   /** (조각 3 고침 · 검증 지적 F) 재조회 전체에 시간 상한(OBS_MAX_MS · 조각 4 ORG_MAX_MS 와 같은 500ms) — 데몬이 살아 있지만 멈춰도 보내기·조회 고리가 멈추지 않게.
    *  넘으면 모름(마스터 undefined · 승인 대기 null → 문턱이 붙잡음 · 쓰기 0) + timedOut 표지. 늦게 온 답은 버린다. */
-  private async freshBounded(): Promise<{ master: MasterRow | null | undefined; approvals: number[] | null; obsAt: number; timedOut?: boolean }> {
+  private async freshBounded(): Promise<{ master: MasterRow | null | undefined; approvals: number[] | null; obsAt: number; timedOut?: boolean; feed?: unknown; org?: unknown }> {
     const r = await this.bounded(this.fetchFresh());
     return r === TIMED_OUT ? { master: undefined, approvals: null, obsAt: this.d.now(), timedOut: true } : r;
   }
@@ -643,18 +638,15 @@ export class ChatCore {
       void this.confirm.scanStep(); // (조각 4) 대화 화면을 연 때보다 앞 기록의 표식을 한 토막씩
       this.lastWorking = fresh.master ? fresh.master.working : null;
       const awaiting = this.s.msgs.some((m) => ["injected", "checking", "slow", "delivered", "replying"].includes(m.step));
-<<<<<<< 75dc2640 (merge(integ · TICKET=cysr-1116-integ-1118): feat/ui-slice3 43b44ea4 — 화면 조각 1(3a012bf4) + 조각 3 보낸 말 단계 전부(독립 검증 고침 · codex 2R 고침))
       // (조각 3 · 하네스 seed 370) 짧은 답(두 조회 사이 3초 안에 일 시작·끝)은 「활동 바뀜」으로 안 잡힌다 → 마스터 출력이 지난 조회 뒤에 있었으면(idle_secs) 그 틱도 읽는다.
       //   새 조회 0(이 조회 값만 씀) · 로컬 세션 파일 오프셋 읽기 · 기다리는 말이 있을 때만.
       const pollAt = this.d.now();
       const idle = fresh.master ? fresh.master.idle_secs : null;
       const outputSincePoll = this.lastPollAt !== null && typeof idle === "number" && idle * 1000 < pollAt - this.lastPollAt;
       this.lastPollAt = pollAt;
-      if (awaiting && ((prevWorking !== null && prevWorking !== this.lastWorking) || outputSincePoll)) void this.readTranscript(); // 활동이 바뀐 틱 · 새 출력이 있던 틱
-=======
-      // 활동이 바뀐 틱 1회 — (조각 4) 기다리는 말이 없어도 마스터가 **쉬게 된** 틱이면 읽는다(마스터가 스스로 낸 물음 표식 · 새 주기 조회 0)
-      if ((awaiting || this.lastWorking === false) && prevWorking !== null && prevWorking !== this.lastWorking) void this.readTranscript();
->>>>>>> fa400dda (docs(ui · TICKET=cysr-ui-slice4-fix2-1118): HANDOFF §13 codex 1R·2R 고침 델타(지적별 처분 · 시험 숫자 전후 · 뮤턴트 56/56 · 📌 데몬 지문 계약) · TODO)
+      // (조각 4) 기다리는 말이 없어도 마스터가 **쉬게 된** 틱이면 읽는다(마스터가 스스로 낸 물음 표식 · 새 주기 조회 0)
+      const changed = prevWorking !== null && prevWorking !== this.lastWorking;
+      if ((changed && (awaiting || this.lastWorking === false)) || (awaiting && outputSincePoll)) void this.readTranscript(); // 활동이 바뀐 틱 · 새 출력이 있던 틱
       else if (this.offset === null && fresh.master) void this.readTranscript(); // 마스터를 안 첫 틱에 세션 시작점을 잡아 둔다(보내기 길에서 그 RPC 를 빼려고)
       const now = this.d.now();
       this.markStale();
@@ -683,7 +675,6 @@ export class ChatCore {
    *  (codex 1R·2R major) 모든 시작점 조회에 상한(OBS_MAX_MS)과 세대를 건다 — 늦게 돌아온 옛 조회가 파일 끝으로 덮어 보낸 말 레코드를 건너뛰지 않게. */
   private async initOffset(): Promise<"ok" | "none" | "stale"> {
     const m = this.s.master;
-<<<<<<< 75dc2640 (merge(integ · TICKET=cysr-1116-integ-1118): feat/ui-slice3 43b44ea4 — 화면 조각 1(3a012bf4) + 조각 3 보낸 말 단계 전부(독립 검증 고침 · codex 2R 고침))
     if (!m) return "none";
     const gen = ++this.initGen; // 새 조회가 시작되면 앞선 조회의 늦은 결과는 버린다
     const r = (await this.bounded(this.d.invoke("chat_transcript", { socket: null, surfaceId: m.surface_id, afterOffset: 0, fromEnd: true }))) as
@@ -692,23 +683,12 @@ export class ChatCore {
     if (r === TIMED_OUT) {
       if (gen === this.initGen) this.initGen++; // 늦게 돌아와도 버리게
       return "stale";
-=======
-    if (!m) return;
-    try {
-      const r = (await this.d.invoke("chat_transcript", { socket: null, surfaceId: m.surface_id, afterOffset: 0, fromEnd: true })) as { status?: unknown; next_offset?: unknown; session_id?: unknown };
-      if (r?.status === "ok" && typeof r.next_offset === "number") {
-        this.offset = r.next_offset;
-        this.sessionId = typeof r.session_id === "string" ? r.session_id : null;
-        this.confirm.startSession(this.sessionId, m.surface_id, r.next_offset);
-      }
-    } catch {
-      /* 모름 — 다음 읽기에서 다시 */
->>>>>>> fa400dda (docs(ui · TICKET=cysr-ui-slice4-fix2-1118): HANDOFF §13 codex 1R·2R 고침 델타(지적별 처분 · 시험 숫자 전후 · 뮤턴트 56/56 · 📌 데몬 지문 계약) · TODO)
     }
     if (gen !== this.initGen) return "stale";
     if (r?.status === "ok" && typeof r.next_offset === "number") {
       this.offset = r.next_offset;
       this.sessionId = typeof r.session_id === "string" ? r.session_id : null;
+      this.confirm.startSession(this.sessionId, m.surface_id, r.next_offset);
       return "ok";
     }
     return "none";
@@ -754,11 +734,8 @@ export class ChatCore {
         if (r.reset === true) {
           // 파일이 줄었다(잘림·교체) — 다시 읽은 옛 레코드로 새 전달·답 근거를 만들지 않는다(codex 1R major). 끝에서 다시 시작.
           this.offset = null;
-<<<<<<< 75dc2640 (merge(integ · TICKET=cysr-1116-integ-1118): feat/ui-slice3 43b44ea4 — 화면 조각 1(3a012bf4) + 조각 3 보낸 말 단계 전부(독립 검증 고침 · codex 2R 고침))
           this.pendingUser = [];
-=======
           this.confirm.resetSession();
->>>>>>> fa400dda (docs(ui · TICKET=cysr-ui-slice4-fix2-1118): HANDOFF §13 codex 1R·2R 고침 델타(지적별 처분 · 시험 숫자 전후 · 뮤턴트 56/56 · 📌 데몬 지문 계약) · TODO)
           await this.initOffset();
           return;
         }
diff --git a/ui/src/views/index.ts b/ui/src/views/index.ts
remerge 충돌 (내용): ui/src/views/index.ts에 병합 충돌
index 45a5aced..83952da5 100644
--- a/ui/src/views/index.ts
+++ b/ui/src/views/index.ts
@@ -42,12 +42,10 @@ export function bootViews(deps: BootDeps): { core: ChatCore; registry: Registry<
     clearTimeout: (h) => clearTimeout(h as ReturnType<typeof setTimeout>),
     store,
     working: deps.working,
-<<<<<<< 75dc2640 (merge(integ · TICKET=cysr-1116-integ-1118): feat/ui-slice3 43b44ea4 — 화면 조각 1(3a012bf4) + 조각 3 보낸 말 단계 전부(독립 검증 고침 · codex 2R 고침))
     // (조각 3) 데몬 사건 구독 — main.ts 를 건드리지 않고 같은 Tauri 전역을 쓴다(core 가 대화 화면이 켜졌을 때만 부름 · 작업 화면 invoke 0 유지).
     listen: (name, handler) => (window as unknown as { __TAURI__: { event: { listen(n: string, h: (e: { payload: unknown }) => void): Promise<() => void> } } }).__TAURI__.event.listen(name, handler),
-=======
-    // (조각 4) 대화 화면이 켜져 있을 때만 core 가 부른다 — 작업 화면만 쓰면 구독 0(동작 변화 0).
-    listen: (fn) => {
+    // (조각 4) 대화 화면이 켜져 있을 때만 core 가 부른다 — 작업 화면만 쓰면 구독 0(동작 변화 0). (통합 1116) 조각 3 listen 과 이름이 겹쳐 listenDaemon.
+    listenDaemon: (fn) => {
       const ev = (window as unknown as { __TAURI__?: { event?: { listen?: (n: string, h: (e: { payload: unknown }) => void) => Promise<() => void> } } }).__TAURI__?.event;
       if (!ev?.listen) return () => {};
       let off: (() => void) | null = null;
@@ -63,7 +61,6 @@ export function bootViews(deps: BootDeps): { core: ChatCore; registry: Registry<
     },
     goView: (id) => void booted?.registry.choose(id),
     defaultSlug: async () => String(await deps.invoke("default_socket_slug")),
->>>>>>> fa400dda (docs(ui · TICKET=cysr-ui-slice4-fix2-1118): HANDOFF §13 codex 1R·2R 고침 델타(지적별 처분 · 시험 숫자 전후 · 뮤턴트 56/56 · 📌 데몬 지문 계약) · TODO)
   });
   const views: ViewDescriptor<ChatState, ChatCore>[] = [
     {
diff --git a/ui/src/views/views.css b/ui/src/views/views.css
remerge 충돌 (내용): ui/src/views/views.css에 병합 충돌
index 8ebee9b4..107e4ba6 100644
--- a/ui/src/views/views.css
+++ b/ui/src/views/views.css
@@ -68,12 +68,10 @@
     --cv-master: #222630;
   }
 }
-<<<<<<< 75dc2640 (merge(integ · TICKET=cysr-1116-integ-1118): feat/ui-slice3 43b44ea4 — 화면 조각 1(3a012bf4) + 조각 3 보낸 말 단계 전부(독립 검증 고침 · codex 2R 고침))
 /* (cysr-ui-slice3) 기계 문안 한 줄 표지 · 오래 걸려요 때 마스터 상태 줄 */
 .cv-auto { align-self: center; font-size: 18px; color: var(--cv-sub); padding: 4px 10px; }
 .cv-auto.auto-failed { color: var(--cv-err); }
 .cv-auto.auto-partial, .cv-auto.auto-slow, .cv-auto.auto-retrying { color: var(--cv-wait); }
-=======
 
 /* (cysr-ui-slice4) 확인 대기 띠 — 화면 맨 위 · 한 번에 하나 · 글자 18px 이상 · 누를 면 44px(§9-2) */
 .cv-band { border: 2px solid var(--cv-attn); border-radius: 10px; padding: 10px 14px; margin-bottom: 12px; background: #fff8f3; }
@@ -95,4 +93,3 @@
 .cv-answering[hidden] { display: none; }
 .cva-text { flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: var(--cv-ink); }
 .cv-asked { outline: 3px solid var(--cv-attn); outline-offset: 2px; }
->>>>>>> fa400dda (docs(ui · TICKET=cysr-ui-slice4-fix2-1118): HANDOFF §13 codex 1R·2R 고침 델타(지적별 처분 · 시험 숫자 전후 · 뮤턴트 56/56 · 📌 데몬 지문 계약) · TODO)
