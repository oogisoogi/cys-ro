# 우리 배선 영향표 — vendor v0.14.52 (B-360 · S-a C5b) 대비

조사 범위: `~/.claude/channels/*.sh|*.py`(하위 2단 포함 · `*.bak*`·`test-*`·`_cand*`·`.msc-drill-harness` 제외), `~/.cys/pack/bin/*`, `~/.cys/local/**`.
벤더 근거: `git -C ~/cys-terminal-src show v0.14.5{1,2}:<path>`(읽기 전용). 줄 번호는 모두 해당 태그의 파일 기준이다.
실측 근거로 쓴 읽기 전용 명령: `ps`, `cys list`, `.master-send-ledger.jsonl` 꼬리, bash 3.2 명령 치환 부모 pid 실험(§0-3).

---

## 0. 먼저 읽을 것 — 가장 크게 깨지는 한 가지

**0.14.52 에서는 에이전트 좌석에 `cys send "본문"`(Return 없음 · `--queued` 아님 · `--clear-first` 아님)을 보내면 0 바이트가 쓰인다.**
데몬이 본문을 **치지 않고 잡아 두고**(`held:"awaiting_submit"`), 같은 호출자의 `send-key Return` 이 60,000 ms 안에 와야 본문과 Return 을 한 작업으로 쓴다. 그런데 CLI 의 출력과 rc 는 예전과 똑같이 `OK` · 0 이다.

- 판정: `v0.14.52:src/bin/cysd/handlers.rs:7034-7050`(에이전트 좌석이면 `direct_agent_intent`, Held 면 `hold_direct_body` 로 되돌아감), `:3149-3173`(분류: clear_first → OwnedClear, 끝이 CR/LF → SelfSubmitting, submit → OwnedSubmit, **나머지는 Held**), `:3659-3721`(`hold_direct_body` — 0 바이트로 `{"sent":true,"request_id":…,"held":"awaiting_submit","window_ms":60000}` 응답).
- 창 길이: `v0.14.52:src/bin/cysd/submit_assoc.rs:21` `LEGACY_ASSOCIATION_WINDOW_MS = 60_000`.
- CLI: `v0.14.52:src/bin/cys.rs:6006-6011` — 직접 경로는 응답 내용을 보지 않고 `println!("OK{tag}")` 를 찍는다(0.14.51 도 `cys.rs:5349` 에서 같은 `OK`). 그래서 **stdout·rc 로는 「잡혀 있음」을 구별할 수 없다.**
- 에이전트 좌석의 범위: `agent_meta` 가 있는 좌석이다. 이 값은 claim-role 관측(`handlers.rs:754`), set_meta/launch-agent(`handlers.rs:11292`), 윈도우 2표본(`governance.rs:846`)에서 채워진다. 제품 코드에서 `agent_meta` 를 `None` 으로 되돌리는 곳은 **찾지 못했다**(grep 결과는 모두 `#[cfg(test)]` 블록 안 — `governance.rs` 시험 모듈은 13132행부터, `handlers.rs` 는 12752행부터). 그래서 **에이전트가 죽어 셸로 떨어진 좌석도 계속 에이전트 좌석으로 취급되는 것으로 보인다**(추론 — 실기에서는 확인하지 않음).
- 0.14.51 에서는 같은 요청이 곧바로 PTY 에 쓰이고(`WriteReq::Data/Program`) `{"sent":true}` 로 답했다(`v0.14.51:src/bin/cysd/handlers.rs:6210`).

### 0-1. 우리 스크립트가 왜 이것에 정면으로 걸리는가
우리 래퍼(master-send.sh · spawn-worker.sh · wake-daemon.sh)는 고스트 제안 방벽 때문에 **「본문이 화면 입력칸에 실린 것을 본 뒤에만 Return 을 보낸다」**. 0.14.52 에서는 본문이 Return 전에는 화면에 나타나지 않으므로, 가드가 「빈 입력줄」로 읽고 Return 을 보내지 않는다. 그러면 60초 뒤 데몬이 잡아 둔 본문을 버린다(`surface.submit_undelivered` · 쳐지지 않음 · 82a261d7 커밋 설명). 결과: **발신 rc 0, 원장에는 Return 미시도 또는 미제출이 남고, 본문은 사라진다.**

### 0-2. 「같은 호출자」의 정의 — 바인딩이 어긋나는 경우
`handlers.rs:3174-3195` `submit_caller_key` 가 정하는 호출자 키는 다음 순서다. ① 검증된 좌석(호출 pid 의 조상이 cys pane — `check_send_acl` → `resolve_caller_surface`, `handlers.rs:1895-1901`) ② 자기신고 `from` 좌석 번호(`CYS_SURFACE_ID` 숫자) ③ 그 둘이 없으면 **`cys` 프로세스의 부모 pid와 그 출생 시각**.
Return 쪽(`handlers.rs:7342-7380`)은 같은 키로 잡아 둔 본문을 찾는다. 키가 다르면 `NoBody` 가 되어 **옛 경로의 맨 Return 이 그대로 쳐진다.**

### 0-3. 실측: bash 3.2 의 명령 치환은 부모 pid 를 바꾼다
`/usr/bin/env bash` = `/bin/bash 3.2.57`(우리 세 래퍼의 shebang). 이 환경에서 직접 재 보았다.
```
3.2.57(1)-release main=4763
cmdsubst_parent=4764      ← $(…) 안에서 띄운 프로세스의 부모 = 서브셸
direct_parent=4763        ← 직접 띄운 프로세스의 부모 = 메인 셸
```
그래서 `_e="$("${CYS}" send …)"`(master-send.sh:421 · wake-daemon.sh:441 의 `err="$(bk_send …)"`)로 보낸 본문과, 직접 실행한 `"${CYS}" send-key … Return`(master-send.sh:426 · wake-daemon.sh:171)은 **pane 밖에서 부르면 호출자 키가 달라진다.** master 가 cmux pane 에 있으므로(원장 `backend` 와 `cys list` 에 master 좌석이 없음) master 가 부른 master-send.sh 는 ① 검증된 좌석으로 잡히지 않는다. 그 결과 blind 경로에서도 Return 이 본문에 붙지 않고 **빈 프롬프트에 맨 Return 이 들어간다** — 우리가 막으려던 고스트 제안 제출 경로와 같은 모양이다. (② `CYS_SURFACE_ID` 를 상속한 경우는 예외지만 cmux pane 에서는 해당하지 않을 것으로 추정 — 불명.)

### 0-4. 현재 실제로 cys 백엔드를 타는 비율
`~/.claude/channels/.master-send-ledger.jsonl` 마지막 400행의 `"backend"` 는 **cys 315 · cmux 79** 다(실측). wake 행은 `backend:"cmux"` 다(같은 원장 · `.wake-daemon.log` 의 `WAKE master surface:1 … → yes|queued`).

---

## 1. 영향표

범례: **예** = 0.14.52 바이너리에서 지금 코드 그대로 기능이 깨진다 · **조건부** = 특정 경로나 설정에서만 깨진다 · **아니오** = 깨지지 않는다(미세한 의미 변화는 비고) · **불명** = 근거로 가르지 못했다.
「출처」 열: 채널=`~/.claude/channels` · 팩-우리=팩 배포본 어디에도 없는 파일 · 팩-포크=우리 포크 v1.1.9 팩과 바이트 동일하지만 벤더 0.14.51/52 와는 다른 파일(§3).

| # | 호출부 파일:줄 | 출처 | 호출 명령 | 지금 읽는 값 | 0.14.52 뒤 값 | 깨지는가 | 고칠 방안 1줄 |
|---|---|---|---|---|---|---|---|
| 1 | `master-send.sh:420-425`(bk_send) → `:1184` 본문 · `:1194` 착지 판독 · `:1435` `safe_return` | 채널 | `cys send --surface S "$BODY"` → 화면 판독 → `cys send-key … Return` | send rc(0 = 보냄), 그 뒤 **입력줄에 본문이 보이는지**(`landed_line` · `read_input_line_v2`) | send rc 0 · stdout `OK` 그대로. 그러나 에이전트 좌석은 **0 바이트(held)** 라 입력줄이 비어 보임 → `safe_return` rc 2(「가드: …Return을 보내지 않았다」) → `RET=skipped_box_read_empty` → 60초 뒤 본문 폐기 | **예**(cys 백엔드 · 에이전트 좌석 = 원장 315/400) | cys 백엔드는 화면 착지 가드를 없애고 본문 끝에 CR 을 붙여(`"$BODY"$'\r'` → SelfSubmitting · `handlers.rs:3159,3163`, 꼬리 CR 은 울타리 밖에 남음 `handlers.rs` `direct_fence_bytes`/`split_submit_tail`) 한 번에 보낸 뒤 제출은 기존 nonce·jsonl 검증으로만 판정 — 또는 `--queued` 로 전환 |
| 2 | `master-send.sh:1042-1050` `stuck_probe`(조각 `bk_send` 뒤 `box_snap` 대조) | 채널 | `cys send` 조각 → 화면 대조 | 조각이 입력칸에 실렸는지 | 조각도 held 라 화면에 안 보임 → `PROBE_STATE` 미검증 → `residue_withhold`. 60초 안에 같은 호출자의 다음 본문이 오면 이전 조각을 대체(`superseded`) | **예**(잔존물 분기에서) | 조각 프로브는 Return 전에는 화면에 안 실리므로 cys 에이전트 좌석에서는 사용 금지 — `--clear-first`(OwnedClear 원자 Ctrl-U+붙여넣기+Return) 로 대체 검토 |
| 3 | `master-send.sh:1766-1790`(순환 뒤 복원 재주입: `bk_send "$RTEXT"` → `:1781` `safe_return`) | 채널 | `cys send` → 화면 판독 → Return | 위와 같음 + `text_in_transcript` | 위와 같음 → `REINJECT=unverified|failed` · 복원 포인터 유실 | **예**(cys 백엔드) | #1 과 같은 수리 |
| 4 | `master-send.sh:1395-1420`(`MSEND_BLIND_SUBMIT=1` blind 경로: 조건 없이 `bk_key Return` 1회) | 채널 | `cys send`(명령 치환) → `cys send-key Return`(직접) | send rc 0 → Return rc → 세션 jsonl nonce | ⓐ pane 밖 호출자(master=cmux)라면 §0-3 대로 호출자 키가 달라 **Return 이 본문에 붙지 않음** → 빈 프롬프트에 맨 Return + 본문 60초 뒤 폐기 ⓑ 붙더라도 Return 이 **rc 91**(write_outcome_unknown)일 수 있음 → `:1420` 이 `RET=failed` 로 끝내고 nonce 검증을 건너뜀(실제로는 쳐질 수 있음) | **조건부**(현재 유일 사용처 master-self-cycle.sh:368 의 대상 CSO 는 cmux 라 지금은 해당 없음 · cys 대상이면 예) | bk_send 를 명령 치환 없이 직접 호출(stderr 는 임시 파일로) — send 와 Return 의 부모 pid 를 같게; rc 91 은 「실패」가 아니라 「모름 = 재전송 금지 → nonce 검증 계속」으로 분기 |
| 5 | `master-send.sh:1462-1520`(자동 blind: `RET=skipped_box_read_empty` ∧ `LANDED=PROMPT_NOSEEN`) | 채널 | `cys send-key Return` | ❯ 미관측(NOSEEN)일 때만 | held 본문에서는 ❯ 가 보이고 빈칸 → `LANDED`≠NOSEEN → 이 분기에 들어오지 않음(#1 로 귀결). 들어오더라도 #4ⓐ 와 같은 키 불일치 | 아니오(#1 이 먼저 깨짐) | #1 수리 뒤 이 분기는 cys 백엔드에서 불필요해짐 |
| 6 | `spawn-worker.sh:1119-1146` `inject()`(`:1132` `$CYS send` → `:1133` `poll_true box_nonempty 8` → `:1143` C-u → `:1145` 재 send → `:1146` 미관측이면 Return 안 보냄) — 호출: `:1344` 각성 넛지 · `:1351` 브리프 | 채널 | `cys send --surface S "$text"` · `cys send-key C-u` | send rc 무시 · 입력칸에 실렸는지(8초 폴링 × 2) | 본문이 held 라 두 번 다 미관측 → `INJECT_STATE=absent` · Return 미전송 → **각성 넛지와 브리프가 모두 주입되지 않음**(`AWAKE_OK=false` · `BRIEF_OK=false`). 재 send 는 이전 본문을 대체 | **예**(새 워커는 launch-agent 의 set_meta 로 에이전트 좌석) | 화면 착지 폴링을 cys 에이전트 좌석에서는 버리고, 본문+CR(SelfSubmitting) 또는 `--queued` 1회 → 기존 `poll_jsonl_landed` 로만 판정 |
| 7 | `spawn-worker.sh:1085-1090` `self_exit`(C-c×2 → `:1089` `$CYS send "exit"` → `:1090` `safe_return_to`) | 채널 | `cys send "exit"` → 화면 확인 → Return | 입력칸에 `exit` 가 실렸는지 | 에이전트가 죽은 좌석도 `agent_meta` 가 남는 것으로 보여(§0) `exit` 가 held → 입력칸이 비어 보임 → Return 미전송 → **좀비 정리 실패** | **예**(추론: agent_meta 해제 경로 미발견) | 셸 정리는 `send "exit"$'\r'`(SelfSubmitting) 또는 `cys close-surface`/`reap-due` 로 |
| 8 | `spawn-worker.sh:1071-1077` `safe_return_to` · `:1127-1128,1143` C-u · `:1087-1088` C-c | 채널 | `cys send-key Return|C-u|C-c` | rc 무시 | C-u·C-c 는 옛 경로 그대로다(82a261d7: "Rejected: convert free Return / other keys to AgentJob now"). Return 은 #6·#7 때문에 보내지지 않음 | 아니오(키 자체) | — |
| 9 | `spawn-worker.sh:1269-1277`(`LA="$($CYS launch-agent …)"` → `surface:N` 파싱) | 채널 | `cys launch-agent --role R --agent A --cwd C` | rc 무시, stdout+stderr 의 마지막 `surface:N` | 0.14.52: 지침 쓰기가 REFUSED → **rc 90**, UNKNOWN → **rc 91**. 두 경우 모두 pane 을 남기고 `surface:N` 을 stdout 에 찍음(`cys.rs:19110-19153`). 0.14.51 에는 90/91 이 없었음 | 아니오(파싱은 그대로 성공) · 단 91 이면 지침이 늦게 쳐질 수 있는 좌석에 #6 이 덧주입함 | rc 90/91 을 읽어 kept-pane 경고를 원장에 남기고, 91 이면 `cys reinject --role R --check` 전에는 덧주입 금지 |
| 10 | `wake-daemon.sh:169-172`(bk_send/bk_ret) → `:441` `err="$(bk_send …)"` → `:446-452` 착지 판독 → `:470` Return | 채널 | `cys send` → 화면 → `cys send-key Return` | send rc · 입력칸이 정확히 우리 글인지 | cys 백엔드일 때 #1 과 같다: 착지 미관측 → `NOLAND` · `.unsent` 기억 → 다음 바퀴에 입력칸이 EMPTY 라 새 nonce 로 다시 보냄 → 그때마다 대체 → **영원히 제출되지 않음**. 키 불일치(§0-3)도 있음 | **조건부**: 기본값 `BACKEND="${WAKE_BACKEND:-cmux}"`(`:63`) · 지금 실행 중인 데몬(pid 11214)은 원장상 `backend:"cmux"` → 지금은 아니오, `WAKE_BACKEND=cys` 이면 예 | cys 백엔드 분기만 #1 처럼 본문+CR 또는 `--queued` 로 |
| 11 | `cso-active-monitor.sh:154` · `:194` | 채널 | `_to $T "$CYS" send --to master --queued "…"` | rc(0 = 성공, 아니면 인박스 폴백) | 큐 경로는 B-360 직접 경로 장벽을 지나지 않는다(eadce029: "The queued path, queue delivery, schedule push and channel inbox are not touched"). 큐 배달은 이제 Return 까지 쓰인 뒤에만 「전달」로 셈(bc82915e) — 넣는 쪽 응답은 그대로 | 아니오 | — |
| 12 | `cys-scan-dispatch.sh:74` | 채널 | `cys send --queued --surface S "$trig"` | rc | 같음(큐) | 아니오 | — |
| 13 | `usage-gate-loop.sh:5` · `weekly-burn-plan.sh:7` · `master-monitor-kit/monitor-budget.sh:1` | 채널 | `cys usage-accounts --json` | `accounts[].provider/label/rate[].label/used_pct/resets_at/in_use` | 변화 없음: `usage_accounts_output` 은 0.14.51/52 사이에서 바이트 동일(실측 diff), fb9eddf4 는 `local_json`(usage.accounts)을 건드리지 않음(§4) | 아니오 | — |
| 14 | cmux 바이너리 호출 일체: `daily-master-poke.sh:72` · `cso-self-cycle.sh:238` · `cso-system-sentinel.sh:154,171,195,263,268,286` · `master-cycle-exec.sh:445` · `acct-switch.sh:53,55,61` · `b3-remonitor-command.sh:31` · `drill-master-self-cycle-cmux.sh:205,227,415` | 채널 | `cmux send/send-key/close-surface` | — | cys 0.14.52 와 무관(바이너리 `/Applications/cmux.app/…/cmux`) | 아니오 | — |
| 15 | `.candidate-master-send.sh:342` 외 | 채널(후보본 · 비가동) | master-send.sh 와 같은 패턴 | — | #1 과 같음 | 조건부(채택하면 예) | 채택 전에 #1 수리를 함께 반영 |
| 16 | `javis_awaken.py:271-276` `send_return` | 팩-우리 | `cys send-key --surface S Return` → rc≠0 이면 `--queued` Return 1회 | rc | 이 모듈은 본문을 직접 보내지 않으므로 바인딩할 held 본문이 없음 → 맨 Return 은 옛 경로(장벽 없음 → 91 불가) | 아니오 | (91 이 오면 큐 Return 폴백이 Return 을 하나 더 넣으니, 91 은 폴백 대상에서 빼는 것이 안전) |
| 17 | `javis_awaken.py:354` · `javis_ctx_relay.py:160` · `javis_dept_request.py:1274,1400` | 팩-우리 | `cys send --queued …` | rc | 큐 경로 | 아니오 | — |
| 18 | `javis_boot_node.py:1717-1727`(launch-agent `--resume-saved`) | 팩-포크(우리 줄) | `cys launch-agent …` | rc 는 로그만(「실패 텍스트 무시·cys list 재조회」) · 좌석은 `role_surface_row` 재조회로 판정 | rc 90/91 이 추가돼도 pane 이 남으므로 재조회에 잡힘 → 뒤이어 `_awaken.ensure_awake`(Return 가능) · `inject`(`--queued`) | 아니오(흐름 유지) · 91 이면 늦게 쳐지는 지침과 각성 메시지가 겹칠 수 있음(불명) | rc 91 이면 awaken/inject 전에 `cys reinject --role R --check` 1회 |
| 19 | `javis_boot_node.py:1080,1207,1705` | 팩-포크(우리 줄) | `cys close-surface REF --reap` | rc | CLI arm 은 0.14.51 과 0.14.52 사이에서 텍스트 동일(`v0.14.52:cys.rs:6783-6797` — 두 태그의 arm 을 나란히 출력해 대조). 데몬 쪽만 닫기 직렬화와 오류 분류가 바뀜(d22de492: 보존된 닫기 실패가 not_found 로 둔갑하지 않음) — 오류는 그대로 rc 1 | 아니오 | (자동 정리라면 `cys reap-due` 로 옮기는 것이 벤더 방향) |
| 20 | `javis_phoenix.py:2772-2777` launch-agent fresh · `:2785-2796` `restore --no-resume` | 팩-포크(우리 줄) | `cys launch-agent` · `cys restore` | rc 는 jevent 기록만 · 판정은 `live_role_surfaces` 관측(`:3732-3745`, `:3676-3690`) | launch-agent 90/91 · restore 의 새 우선순위(실패 1 > 91 > 90 > 0 · `cys.rs:23055-23068`) | 아니오(rc 로 판정하지 않음) | 기록할 때 90/91 을 「pane 보존 · 재주입 보류」로 분류해 남기기 |
| 21 | `javis_phoenix.py:2970` `stage_reinject` → `:455-480` `classify_reinject_result` | 팩-포크(벤더 0.14.51 과 같은 줄) | `cys reinject --check --role R --surface S` | rc≠0 → `fail` | `run_reinject` 가 UNKNOWN 이면 rc 91(`cys.rs:23610` `exit_for_error`) → `fail` 로 분류 | 아니오(보수적 실패) · 다음 단계가 재시도하면 중복 위험(불명) | 91 을 별도 kind(`unknown`)로 분류해 재주입하지 않기 |
| 22 | `javis_phoenix.py:3116` C6(`close-surface --reap`) | 팩-포크(벤더 0.14.51 과 같은 줄) | `cys close-surface REF --reap` | rc | 벤더 0.14.52 `javis_phoenix.py:2540-2560` 은 `cys reap-due` 를 먼저 부르고 「기능 없음」일 때만 1회 옛 경로로 물러남 | 아니오(옛 경로는 여전히 동작) · 데몬의 「때가 됨」 정책을 우회 | 병합 때 벤더의 `c6_reap_stale_surfaces`(reap-due) 채택 |
| 23 | `javis_bootstrap.py:3500,3511`(`cys boot --json` / 텍스트) · `:2472-2505` `_boot_fatal_verdict` | 팩-포크 | `cys boot --json` | `roles[].outcome ∈ BOOT_FATAL_OUTCOMES=("failed","missing")`(`:570`) · mandatory | 새 outcome `recover_unknown` · `recover_unrecognised`(b5b044af) · `directive_unknown`(ab8afa64) — 치명 아님. launch 90/91 은 outcome `failed` 를 유지하고 `kept_pane` 필드를 더함(`cys.rs:14265-14271`) → 치명 판정은 예전과 같음. 다만 **벤더 0.14.52 부트스트랩은 이 UNKNOWN 들에 ready 표식을 보류**하고(`v0.14.52:…/javis_bootstrap.py:2550-2560` 표 · `:3879-3882` `CYS_KEPT_PANE_NOTICE=caller` · `:2919` `cys kept-pane-notice`) 우리 v1.1.9 부트스트랩에는 그 장치가 없음(grep 0) | **예(안전 축)**: 기능은 돌지만, 지침 도달이 「모름」인 좌석이 있어도 ready 를 선언함. 이 경우 kept-pane 통지는 `cys boot` 자신이 master 큐로 보냄(af41d65c) | 병합 때 벤더 3a5b7556 의 `_ready_decision`·`_boot_rows_withheld`·`_kept_pane_records_withheld` 채택(RELEASE.md:60 PACK_MIN_BINARY 0.14.52 와 짝) |
| 24 | `javis_bootstrap.py:2057-2079`(부서장 `launch-agent --role master`) | 팩-포크(벤더와 같은 논리) | `cys launch-agent` | `code != 0` → 「부서장 기동 실패 — claude CLI 설치 확인」 | 90/91 이면 pane 이 살아 있는데 설치 문제로 안내 | 아니오(벤더 0.14.52 `javis_bootstrap.py:2020-2040` 도 같은 판정) · 문구가 오도함 | 90/91 분기를 추가해 `cys reinject --role master --check` 를 안내 |
| 25 | `javis_cycle_autopilot.py:391-401` `push_line`/`escalate` | 팩-포크(벤더와 같은 줄) | `cys send --to R text` → `cys send-key --to R Return` | 두 rc 모두 0 이어야 성공 | Python 부모가 같으므로 Return 이 held 본문에 붙어 정상 제출됨. Return 이 rc 91 이면 `False,"send-key rc=91"`(실제로는 쳐질 수 있음) | 아니오 | 91 → 「모름」으로 기록(재시도 안 함 — 현재도 재시도 없음) |
| 26 | `javis_cycle_autopilot.py:848-865`(cycle-agent argv) → `:1817-1860` child_rc 처리 | 팩-포크 | `cys cycle-agent …` | rc 87/88 → held_noop, HELD_RCS(84/85) → 보류, 그 밖 → 사후검증 | UNKNOWN 이면 rc 91(`cys.rs:2248-2263` `cycle_agent_exit`) → 「그 밖」 → 자체 사후검증으로 종결(벤더 주석 `v0.14.52:cys.rs` 1687-1701 의 `EXIT_CLEAR_UNVERIFIED` 설명 블록: 「javis_cycle_autopilot 은 이 rc 를 `child_rc` 로 기록만 하고 자체 사후검증으로 종결」 — 80/81 에 대해 적은 문장이며 91 에 대한 명시는 아님) | 아니오 | (사후검증이 재사이클을 트리거하기 전에 91 을 보류 사유로 분류하면 더 안전) |
| 27 | `javis_cycle_autopilot.py:2372-2373`(검증자 pane 재사용) | 팩-포크(벤더와 같은 줄) | `cys send --surface REF cmdline` + `send-key Return` | 두 rc | 검증자 pane 은 `--cmd` 워처라 에이전트 좌석이 아님(추정) → 옛 경로 | 아니오(추정) | — |
| 28 | `javis_cycle_verifier.py:399-402` | 팩-포크(벤더와 같은 줄) | send + send-key Return | 두 rc | #25 와 같음 | 아니오 | — |
| 29 | `javis_hud_bridge.py:2011-2020` | 팩-포크(벤더 0.14.51:2120 과 같은 논리) | `cys [--socket] send --surface S -- text` + `send-key Return` | rc → 502 `send_failed` / `return_failed` | 정상이면 바인딩됨. Return 91 이면 502 `return_failed`(실제로는 쳐질 수 있음 → HUD 사용자가 다시 누르면 중복) | 아니오(벤더 책임) | 91 을 별도 응답으로 |
| 30 | `javis_resource_gate.py:2332` | 팩-포크 | `cys usage-accounts --json` | `accounts[]` | 변화 없음(#13) | 아니오 | — |
| 31 | `javis_phoenix.py:4974` | 팩-포크(벤더와 같은 줄) | `cys drain`(plain) | rc 기록 | 저장 신호 줄의 문구만 바뀜(11717c44 ①) | 아니오 | — |
| 32 | 큐 송신 일체(`javis_boot_node.py:827` · `javis_bootstrap.py:908,1655,2118` · `javis_channel_watch.py:158` · `javis_fleet_report.py:385` · `javis_formation.py:1350` · `javis_serena_probe.py:117` · `javis_wakeup.py:699` · `javis_report_gate.py:1761` · `javis_resource_gate.py:2843`) | 팩-포크 | `cys send --queued …` | rc | 큐 경로(#11) | 아니오 | — |
| 33 | `~/.cys/local/**`(10개 파일) | 로컬 | — | 실행 스크립트 없음(지침 md 1건이 `cys launch-agent` 를 문장으로 언급, proposals/*.patch 는 v0.13.20 패치) | — | 해당 없음 | — |
| 34 | 앱(int/1111) `ui/src/main.ts:8350-8362` drain-verify 결과 타입 | 앱 | `cys drain --verify` JSON | `outcome ∈ saved|timeout|delivery_failed|unverifiable|skipped_restoring` · `all_saved` | 새 outcome `unknown` + summary `unknown` 수(f45017d7). exit 는 91(`cys.rs:21008-21021`) — 앱은 JSON 이 진실원(주석) | 아니오(`all_saved=false` → 저장 안 됨으로 처리 · 문자열은 그대로 표시) | 타입에 `unknown` 추가와 「재실행 금지」 문구 |
| 35 | 앱(int/1111) pack-update 결과 파서 | 앱 | `cys pack-update` | int/1111 `src-tauri`·`ui/src` 에 `"pack-update"`·`parse_reinject_result` 없음(grep 0) | 벤더는 exit 3 규칙과 `unknown=` 토큰을 추가(c756c822 · `v0.14.52:src-tauri/src/main.rs:8403`) | 해당 없음(우리 앱은 호출 안 함) | — |

`cys node-recover` · `cys pack-update` · `cys reap-due` · `cys kept-pane-notice` 를 직접 부르는 우리 스크립트는 **없다**. 세 범위 전부를 grep 했고, 나온 것은 주석이나 문자열 표(`javis_idempotency.py:56-61` · `javis_mission.py:1259` · `javis_approval_queue.py:215`)뿐이다.

---

## 2. 벤더 의미 (0.14.52 소스 기준)

### 2-1. `sent` 필드
| 응답 자리 | 0.14.51 | 0.14.52 |
|---|---|---|
| `surface.send_text` 직접(셸 좌석 · 사람 · GUI 삽입) | `{"surface_id","sent":true}` 즉시 쓰기(`v0.14.51:handlers.rs:6210`) | 같은 모양 + 에이전트 작업이면 `request_id`(`v0.14.52:handlers.rs:7298-7302`) |
| `surface.send_text` 에이전트 좌석 · Return 없는 본문 | (위와 같음 — 즉시 씀) | **`sent:true` 인데 0 바이트** · `held:"awaiting_submit"` · `window_ms:60000` · `request_id`(`handlers.rs:3718-3720`) |
| `surface.send_text` 에이전트 좌석 · clear_first / 끝 CR·LF / submit:true | 즉시 씀 · `sent:true` | 장벽(쓰기 일지 기록)을 최대 2,000 ms 기다린 뒤 **PASSED 일 때만** `sent:true`(`handlers.rs:4022-4033` 주석 「`sent:true` only when the journal wrote the record」) · REFUSED/UNKNOWN 은 오류 응답 |
| `surface.send_key` Return 이 held 본문에 붙을 때 | — | 같은 장벽 판정 → PASSED 면 `{"sent":true,"request_id","bound":"token|legacy"}`(`handlers.rs:4032`) |
| `surface.send_key` Return 흡수 | `sent:false,absorbed:true`(`v0.14.51:3040`) | 같음(`v0.14.52:2952`) |
| eadce029 의 중간 필드 `journal_barrier` | — | **제거됨**(d27e1066: 「The field is removed」) |

CLI 는 `sent` 를 읽지 않는다. 직접 경로는 성공이면 `OK`(`cys.rs:6010`), 오류면 `error: …` 를 찍고 `exit_for_error` 로 끝난다(`cys.rs:6935-6942`).

### 2-2. 오류 코드 → exit
- 상수: `v0.14.52:src/lib.rs:666` `ERR_JOURNAL_UNAVAILABLE="journal_unavailable"`, `:672` `ERR_WRITE_OUTCOME_UNKNOWN="write_outcome_unknown"`(0.14.51 에는 둘 다 없다 — grep 0).
- 생산: `handlers.rs:4047-4076` `journal_barrier_verdict`. 세 결과이고 서로 합치지 않는다.
  - Passed → Ok(유일하게 `sent:true` 가능)
  - Refused → `journal_unavailable: zero bytes written … nothing was typed - it is safe to send it again`
  - Pending(예산 `agent_write.rs:1182` `JOURNAL_BARRIER_BUDGET_MS = 2_000` 초과) → `write_outcome_unknown: outcome unknown … it is still queued and may still be typed. Do NOT send it again …`
- CLI 판정은 부분 문자열로 한다: `cys.rs:1082-1091` `is_journal_refusal` / `is_write_outcome_unknown`. `cys.rs:1094-1100` `exit_for_error` 는 UNKNOWN → **91**, 나머지 → **1**(REFUSED 도 1 — 다시 보내도 안전하기 때문). `run()`(`cys.rs:6940`)과 `run_reinject`(`cys.rs:23610`)가 이것을 쓴다. 0.14.51 `run()` 은 모든 오류가 1 이었다(`v0.14.51:cys.rs:6268-6273`).

### 2-3. exit 90
`cys.rs:1672-1677` `EXIT_DIRECTIVE_REFUSED = 90` — 「launch-agent: 에이전트는 떴는데 지침이 쓰기 일지에서 거부됨(0 바이트). pane 은 **남긴다**(닫으면 돌아가는 에이전트를 죽이고, 다시 띄워도 같은 이유로 거부된다). 0(지침 미도달)도 1(되돌리고 pane 을 닫음)도 78(첫기동 관문)도 아니다.」
나오는 곳:
- launch-agent(`cys.rs:19100-19125` — launch 명령 쓰기가 거부됐으면 `[launch-agent] … kept: … empty shell` · 아니면 `… agent is running WITHOUT its directive`, 그 뒤 stdout 에 `surface:N`)
- restore 의 집계(`cys.rs:23055-23068` `restore_exit_code`: 실제 실패 1 > 91 > 90 > 0 · f789cfc2)
- restore in-seat(11717c44 ⑧)

node-recover 의 일지 REFUSED 는 90 이 아니라 **79**(`EXIT_RECOVER_REFUSED` · `cys.rs:1038`, 접기 `cys.rs:1061-1078`)다.

### 2-4. exit 91
`cys.rs:1679-1685` `EXIT_WRITE_OUTCOME_UNKNOWN = 91` — 「어떤 명령이든 직접 쓰기의 결과를 모름: 아직 큐에 있고 쳐질 수 있다 — **다시 보내지 마라**(두 번 쳐질 수 있다). 90 바로 뒤 · 92-99 미할당.」
나오는 곳:
- `cys send`/`send-key`/모든 직접 쓰기(`run()` · `cys.rs:6940`)
- `cycle-agent`(`cys.rs:2261`)
- launch-agent(`cys.rs:19127-19153`, pane 보존 · `cys reinject --role R --check` 안내)
- node-recover(`cys.rs:22750-22763` · ab8afa64. run_boot 는 91 을 `recover_unknown` 으로 받아 회수하지 않음 — `cys.rs:14492-14501` `boot_recover_disposition`: 1 만 Escalate · b5b044af)
- `drain --verify`(`cys.rs:21000-21021` `drain_verify_exit_code`: 전원 saved 0 · unknown 노드 있으면 91 · 그 밖 1. drain 에서는 91 이 1 보다 앞선다)
- restore(`cys.rs:23058-23068`, 여기서는 실제 실패 1 이 91 보다 앞선다)
- reinject(`cys.rs:23610`)

**pack-update 는 91 을 쓰지 않는다.** 실행 중 새 unknown 이 생기거나 실패가 있으면 3이다(`cys.rs:24008` `reinject_exit_code` · c756c822 「Rejected: 91 for pack-update | the app reads any non-zero but 3 as a failed update」).

### 2-5. 그 밖에 새로 생긴 것
- `cys reap-due <surface>`(`cys.rs:2453-2480`): stdout 은 데몬 JSON 그대로이고 `outcome ∈ reaped|gone|deferred(+reason)` 만 받는다. 오류는 rc 1.
- `cys kept-pane-notice --input <path|->`(숨김 · 3a5b7556 · `cys.rs:1553-1554`): exit 0 / 3(못 보냄) / 2(입력 불량).
- kept-pane 기록(v2): `<pack state base>/.kept-pane-records.jsonl`(f789cfc2 · 3a5b7556). 가장 바깥 명령(boot/restore/launch-agent/node-recover)이 끝날 때 master 큐로 `[kept-pane] key=#…` 통지를 **최대 1건** 보낸다(af41d65c). `CYS_KEPT_PANE_NOTICE=caller` + `CYS_KEPT_PANE_RECORDS_OUT` 짝이 있으면 보내지 않고 파일로 넘긴다.
- 데몬 경로를 끄는 스위치: held 경로(C5b)에서는 환경변수나 센티널 스위치를 **찾지 못했다**(`handlers.rs` send_text 경로 grep). 릴리스 노트의 되돌림 변수는 F-01 용 `CYS_DISPLAY_ACTIVITY=0` 하나뿐이다(`RELEASE_NOTES_0.14.52.md:18-19`).
- 릴리스 노트(`docs/RELEASE_NOTES_0.14.52.md` §1-4 · 75-90행)는 이 변화를 「직접 보내기: 자기 Return 이 없는 자동 본문은 치지 않고 잡아 두고 … 60,000 ms 안에 오면 본문 + Return 을 한 작업으로 씁니다」라고 적는다. 「셸 좌석 · 사람 키 · GUI 경로 삽입은 옛 경로 그대로」다. 다만 이 노트는 79개 커밋(`c98e5d5e` 기준) 초안이고 **90/91 의 뜻은 설명하지 않는다**(grep 0). 위 정의는 소스와 커밋 설명에서 가져왔다.

---

## 3. 팩 bin 출처 판정(실측)

`~/.cys/pack/.pack-version` = `1.1.9`. bin 파일 119개 가운데:
- 벤더 0.14.51 과 바이트 동일 48개, 0.14.52 와 동일 47개(대부분 겹침).
- 벤더와는 다르지만 **우리 포크 태그 `v1.1.9:cysjavis-pack/bin/` 과는 동일 110/119** — 이른바 「MODIFIED 56개」는 포크 팩이다.
- 어느 배포본에도 없는 순수 로컬 9개: `javis_hud_bridge.py.user`, `javis_memory_reindex.py`, `javis_panetitle.py`(+`.bak-dmac4-…`), `javis_reconstruct_state.py`, `javis_round_snapshot.py`, `javis_seedonce_guard.py`, `javis_state_snapshot.py.user`, `javis_view_bridge.py`. 이 가운데 대상 명령을 부르는 파일은 0개다(grep).
- 「팩-우리」(벤더 0.14.51/52 에 없는 파일): `javis_awaken.py` · `javis_counsel.py` · `javis_ctx_relay.py` · `javis_dept_request.py` · `javis_seat.py` 외 — 대상 명령 호출은 표 #16-#17 이 전부다.
- 포크 팩 파일의 호출 줄 가운데 벤더 0.14.51 에 **없는 줄**(= 우리가 쓴 줄): `javis_boot_node.py:1080,1207,1705,1717` · `javis_phoenix.py:2612,2772,2785,3706`(그 밖의 호출 줄은 벤더 0.14.51 에 같은 텍스트가 있음 — 비교 스크립트 실측).
- 벤더가 0.14.51→52 에서 고친 팩 bin(우리 포크가 받아야 하는 쪽): `javis_bootstrap.py`(+532) · `javis_lane.py` · `javis_phoenix.py`(reap-due) · `javis_phoenix_harness.py` · `javis_mission.py` · `javis_resource_gate.py` · `javis_state_snapshot.py`, 새 파일 `javis_intake.py` · `javis_computer_use.py`(`git diff --stat v0.14.51 v0.14.52 -- cysjavis-pack/bin`).

---

## 4. fb9eddf4(B-229 「계정 불일치·확인 필요」 묶음 제거 · 공지 ③)와 우리 앱층의 겹침

### 4-1. 벤더가 바꾼 것
- `ui/src/seatacct.ts`
  - `SEAT_ACCT_REASON.mismatch` 와 `SEAT_ACCT_MISMATCH_LABEL` 을 지웠다(옛 55-66행).
  - `buildWsAccountGroups` 에서 mismatch 묶음을 지우고 `if (sa.state === "mismatch") continue;` 로 아예 빼도록 했다(옛 152-200행).
  - `parseSeatAccount` 는 mismatch 상태를 알아보되 ID 를 계정으로 올리지 않는다.
- `src/bin/cysd/accounts.rs`
  - `SeatFolder::display_folder` 에서 Mismatch 를 None 으로 돌린다(1681-1701).
  - `seat_account_json` 의 Mismatch 응답에서 `account_id` 는 언제나 `null` 이다(2210-2224 · 옛값은 관측 폴더의 신원).
  - `seat_identity_view_in` 은 mismatch 만으로는 캐시를 데우지 않는다(1917-1925).
  - 경보 귀속과 `in_use` 는 그대로다(시험 `u229_mismatch_never_reads_or_refreshes_observed_identity` 가 `account_in_use` · `alert_rates_with` 가 바뀌지 않음을 단언).
- `ui/src/seatacct.test.ts` 7-13 · 131-164.
- **`usage.accounts`(`local_json`)는 건드리지 않았다.** `v0.14.51..v0.14.52 -- accounts.rs` 의 변경 커밋은 fb9eddf4 와 6b53ed5c 둘이고, 헝크 목록에 `local_json` 이 없다. CLI `usage_accounts_output` 은 바이트 동일하다(실측 diff).

### 4-2. 양쪽이 모두 건드린 파일 (`v0.14.51..int/1111` 대 fb9eddf4)
| 파일 | 우리(int/1111) 변경 | 벤더 fb9eddf4 | 겹침 |
|---|---|---|---|
| `ui/src/seatacct.ts` | 2줄 — 문구 `cys`→`cysr`(`unsupported` 사유 53행 · `acctTitle` 230행) | 55-66, 77-81, 152-200 | 같은 줄은 없음 |
| `ui/src/seatacct.test.ts` | 84행(문구) · 242행(`seatAccts.delete(` 개수 2→1 · 1.1.10 편입 주석) | 7-13, 131-164 | 같은 줄은 없음 |
| `src/bin/cysd/accounts.rs` | +1939줄 · 가까운 헝크: 1668(SeatIdentCache) · 1802/1812(collect_seat_rows) · 1964(assemble_seat_view) · 시험 6100/6117/6406 | 1581, 1681, 1757, 1917, 2196-2241, 시험 6105/6199/6324/6364/6383 | 1668 ↔ 1681, 6100 ↔ 6105 가 몇 줄 차이로 이웃함 |

**읽기 전용 3자 병합 시험**(`git merge-tree v0.14.51 int/1111 v0.14.52`, 옛 형식 · 객체를 쓰지 않음): 위 세 파일의 충돌 표지는 **0개**다. 같은 시험에서 충돌이 난 곳은 `src/bin/cysd/usage.rs` 1개(fb9eddf4 가 아니라 F-01 6b53ed5c 의 `agent_session_id` 핀 블록 ↔ 우리 dbg-D2 R2 등록 경로 세션 교체 블록), `handlers.rs` 10, `cys.rs` 17, `ui/src/main.ts` 16, `src-tauri/src/main.rs` 5 — 모두 다른 커밋에서 왔다.
⚠ 옛 형식 merge-tree 는 근사치다. 실제 리베이스 작업트리(`cys-terminal-src-wt/rebase-01452`)의 결과는 보지 않았다(지시대로 손대지 않음).

### 4-3. 우리 패널이 벤더가 없앤 필드를 쓰는가 — **쓰지 않는다**
- 우리 사이드바 사용량 패널 `ui/src/wsusage.ts`(int/1111 에만 있고 v0.14.52 에는 없음 — `git show v0.14.52:ui/src/wsusage.ts` → 없음)는 `usage.accounts` 의 `accounts[]`(`account_id` · `label` · `rate[]`(`used_pct`·`resets_at`·`stale`·`stale_reason`) · `updated_at` · `source` · `fresh_limit_secs` · `scoped`)를 쓴다(`wsusage.ts:220-312`). 이것은 계정 저장소의 행이고, 좌석별 `account` 객체(`state:"mismatch"`)가 아니다.
- `int/1111` 의 `wsusage.ts` · `usagebar.ts` · `main.ts` · `usage.rs` · `cys.rs` 에서 `mismatch|MISMATCH|recorded_profile|SeatFolder::Mismatch` 를 grep 하면 계정과 관련된 것은 **0건**이다. `cys.rs` 의 `*_mismatch` 는 lane/cwd/pack config 이고, `src-tauri` 는 phrase/version 이다.
- 우리 `main.ts` 가 `seatacct` 를 쓰는 곳은 부서 카드의 `buildWsAccountGroups(...)` 호출(`int/1111:ui/src/main.ts:235` import · `:5734`)뿐이다. 그래서 병합 뒤에는 부서 카드에서 「계정 불일치·확인 필요」 묶음이 사라지고 그 좌석은 아무 묶음에도 나오지 않는다(벤더가 의도한 동작). 「계정 확인 중」 묶음은 그대로다.
- 시험이 컴파일되는지: 벤더 u229 시험이 쓰는 도우미는 우리 쪽에 같은 시그니처로 있다 — `seat_usage_wire(u,&surface_id,alive,view,now,stale_secs)`(v52 2145 · int 2824), `note_rate_for_profile_at_resolved`(v52 649 · int 694), `ObservedUsage` 필드 10개 동일(v52 `usage.rs:93-` · int `usage.rs:101-`). `b3_login`/`b3_seat` 같은 시험 픽스처 쪽은 확인하지 않았다(불명).
- 결론: fb9eddf4 와 우리 앱층 사용자 정의(사이드바 토큰 사용량 패널 · `cys usage-accounts`)는 **데이터 축이 다르다**(좌석 표시 신원 ↔ 계정 저장소 rate). 같은 파일을 만지지만 같은 줄은 아니며, 우리 패널이 소비하는 필드는 하나도 지워지지 않았다. 우리 스크립트가 읽는 `cys usage-accounts --json`(표 #13 · #30) 출력도 바뀌지 않는다.

---

## 5. 불명으로 남긴 것
1. `agent_meta` 가 에이전트 종료 뒤에도 남는가 — 제품 코드에서 해제 경로를 찾지 못했다는 것만 확인했다(실기 미확인). 표 #7 의 판정이 여기에 달려 있다.
2. master(cmux pane)가 부른 래퍼에 `CYS_SURFACE_ID`(또는 `JAVIS_`/`AITERM_` 호환 키 · `lib.rs:379-385`)가 숫자로 상속되는가 — 상속되면 호출자 키는 Claimed 로 같아진다(§0-2 ②). 실측하지 않았다.
3. 지금 돌고 있는 wake-daemon 의 `WAKE_BACKEND` 환경값 — 프로세스 환경은 읽히지 않았다. 원장에 `backend:"cmux"` 가 있다는 것까지만 확인했다.
4. rc 91 의 실제 빈도(2,000 ms 장벽 예산 초과 = 바쁜 좌석) — 측정하지 않았다.
5. `send-key C-u`(사람 키가 아닌 CancelKey)가 잡아 둔 본문을 버리는가 — 커밋 설명은 「clear」라고만 적고, 그것이 clear_first 인지 C-u 인지 근거로 가르지 못했다.
