# HANDOFF — 1.1.10 선 병합 + codex 3R 잔여 3 + 팩 디렉티브 수정 지점 (TICKET=cysr-1110-backlog-merge)

2026-10-10 · 좌석 318(worker-4) · 가지 `fix/1110-backlog` · 브리프 = master 2026-10-10 12:2x(master#08817fee) · push 0(올리는 것은 master)

## 0. 델타(이 티켓이 바꾼 것)

| 순서 | 커밋 | 무엇 |
|---|---|---|
| A | `dadb7490` | 병합: origin/int/1110-upstream `70ed3f26` → fix/1110-backlog(부모 `4d0fd0c6` · `70ed3f26`). 텍스트 충돌 0. 양쪽이 다 고친 파일 1(`src/bin/cys.rs` · 자동 병합 · 구역 분리 — 이쪽 = restore claim 잠금과 그 시험 / 저쪽 = 승인·doctor·schedule·pack-heal 등 · 저쪽 diff 에 restore_claim 0줄). 저쪽 85파일 / 이쪽 17파일 |
| C1·C3 | `7b4464e1` | `ui/src/publicdocs.test.ts`: 「Antigravity 줄 = 같은 줄에 휴면」 을 DOCS 11개 전체로 + 줄 규칙 2(백틱 정확 일치 3토큰 `reporter:"agy"` · `agy-statusline` · `agy_csrf_required` 줄 = 같은 줄에 휴면). `USER-MANUAL.md` RPC 가산분 절 3줄 → 「이력 · 이 판 휴면」 |
| C2 | `cf012121` | `docs/upstream/HANDOFF-1110.md`: 2R 이관 기록 줄(:142)은 그대로 · 바로 아래 대조 1줄(:143) |
| B2 | `46021d70` | `cysjavis-pack/directives/WORKER_DIRECTIVE.md:82` 종료 규칙 1줄(§1 의 4번) |
| B3 | `6b3bcd75` | `cysjavis-pack/bin/tests/run_bootstrap_health.py:14961~15059` 검체 `H-SH-PKILL-1`(팩·scripts 셸의 `pkill -f` 실행 줄 0) |
| B1 | 코드 0 | 아래 §2 — 설치본 live 파일 2줄의 before/after(집행 = master) |

- 첫 병합 `af4df8ca`(둘째 부모 73a86f1e)는 master#073cd7e8 정정(origin 머리 = 70ed3f26)에 따라 버리고 `4d0fd0c6` 에서 처음부터 다시 병합했다. 두 병합의 차이 = `docs/upstream/HANDOFF-1110.md` 1줄.

## 1. 게이트

실행 조건(두 번 다 같다): 맥 · 이 작업 트리(다른 좌석 쓰기 0) · 좌석 `CYS_*` env 전부 제거 · 단계마다 새 임시 HOME · 순차 1회 · 스냅샷 도구 아님.

| 단계 | A 병합 `dadb7490`(13:01~13:34) | 최종 머리 `6b3bcd75`(13:52~15:39 · 중간에 기계 절전) |
|---|---|---|
| Rust lib `cargo test --lib` | 1077 / 0(무시 2 · 342초) | 1차 1076 / **1**(절전 중 실행 — 아래) → 깨어 있는 상태 재실행 **1077 / 0**(무시 2 · 341초) |
| `--bin cys` | 612 / 0(188초 · 1.1.10 선 610 + restore_claim 시험 2) | 612 / 0(188초) |
| `--bin cysd` 전수 | 2600 / 0(무시 8 · 447초) | 2600 / 0(무시 8 · 398초) |
| `-p cys-app` | 303 / 0(무시 2 · 1.1.10 선 302 + updnotice 시험 1) | 303 / 0(무시 2) |
| ui `bun test` | 2917 pass / 85 skip / 0 fail(3002 시험 · 92 파일) | 같음 |
| publicdocs | 17 / 0(expect 232) | 17 / 0(expect 262) |
| tsc(typescript@7.0.2 · tsconfig.check.json) | rc 0 · 오류 0 | rc 0 · 오류 0 |
| `gen_ceo_template.py --check` | GREEN(드리프트 0 · 95201 bytes) | 같음 |
| 팩 시험 파일(파일마다 새 HOME) | 66 / 66 rc 0(첫 회 61 + 러너 오분류 5 재실행 · §4) | 77 중 76 rc 0 · 1 = `test_pyseal_negative_specimen` UNMEASURED(이 맥 환경성 · 아래) |
| phoenix 3종 같은 HOME 순차 | c6 7/7 · e2e 7/7 · f1 63/63 · 그 HOME 에 `.cys` 0 | 같음 |
| `test_update_publish` | rc 0 | rc 0 |
| boot-health | 162 PASS / 2 FAIL / 1 SKIP | **163** PASS / 2 FAIL / 1 SKIP(차이 = `H-SH-PKILL-1` PASS 1줄뿐 · 전 검체 id·판정 대조) |
| secret-scan `--all` | clean(1655 파일) | clean(1655 파일 · 이 문서 커밋 뒤 다시 잼) |
| 프로세스 | 게이트 전후 cysd 목록 변화 0 | 같음 |

- **절전과 lib 1건**: 기계가 14:12:52~15:17:47 절전이었다(`pmset -g log` 의 Entering Sleep 5건). 그 사이에 걸친 lib 1차에서 `claude_tui::tests::claude_tui_ledger_lock_is_exclusive_and_clears_stale_locks` 1건이 「잡힌 동안은 얻지 못한다」 로 적이었다 — 이 시험은 잠금을 쥔 채 2초 대기를 재는데, 원장 잠금은 mtime 이 60초 넘은 것을 「죽은 프로세스의 낡은 잠금」 으로 치우게 돼 있어 절전으로 벽시계가 건너뛰면 쥔 잠금이 낡은 것으로 보인다. 깨어 있는 상태 재실행(15:34~15:39 · 그 사이 Entering Sleep 0건) = 1077 / 0 · 그 시험 ok. `src/claude_tui.rs` 는 이 티켓이 건드리지 않았다(마지막 변경 = 1.1.10 선 abec4fb7). 시험이 절전에 약하다는 관찰로만 남긴다(수정 0).

- 실행하지 않은 것: 윈 컴파일·실기 · 팩 전수(ci-branch 131종) · `test_agora_known_authentic`(`CYS_AGORA_ZIP_DIR` 필요).
- boot-health 의 FAIL 2(`H-CLT-1`·`H-CLT-2`)는 이 맥 환경성이다 — 티켓 이전 기준 실행(전임 HANDOFF-1110-backlog)과 FAIL 사유 문맥·전 검체 id·판정이 같다. 최종 머리에서는 새 검체 1(`H-SH-PKILL-1`)이 PASS 로 더해진다.
- `test_pyseal_negative_specimen` 은 이 맥에서 `UNMEASURED ⓒ`(rc 2)다 — in-tree 로 `.pyc` 를 쓰는 비번들 python 이 없다(`/usr/bin/python3` 은 Apple 패치로 캐시가 홈 아래). 변경 전 `dadb7490` 사본에서도 같은 줄 = 이 티켓과 무관.

## 2. 팩 디렉티브 수정 지점(B1·B2) — live 집행은 master

**전제 정정(브리프 §0 넷째 줄 · master#73311db8 수용)**: 설치본 `~/.cys/pack/directives/WORKER_DIRECTIVE.md` 는 「합성 결과」가 아니라 **오너가 손으로 고친 live 파일**이다.

| 파일 | 줄 | sha256 앞 12 | 비고 |
|---|---|---|---|
| `~/.cys/pack/directives/WORKER_DIRECTIVE.md` | 333 | `21202c44641a` | live · mtime 09-20 20:02 · §6-9~6-12 · 최상위 채널 규칙 보유 |
| `~/.cys/pack/directives/WORKER_DIRECTIVE.md.new` | 277 | `64f660fa413c` | 팩 갱신이 live 를 덮지 않고 옆에 둔 것 = 저장소 원본(이 티켓 전)과 바이트 동일 |
| `~/.cys/pack/.pristine/directives/WORKER_DIRECTIVE.md` | 153 | `3821adefba7a` | 07-14 |

- 저장소 전 이력에 §6-9 는 없다(`git log --all -S'판정·승인 불변식' -- cysjavis-pack` = 0건). 저장소 합성기는 `scripts/gen_ceo_template.py` 하나이고 입력은 `MASTER_DIRECTIVE.md` 뿐이다(→ `CEO_TEMPLATE.md`). WORKER_DIRECTIVE 는 합성 대상이 아니다.
- 그래서 B1 은 저장소 무변경이고, 아래 원문대로 live 를 고치는 것은 master 몫이다(워커는 실 홈 쓰기 금지). 아래 줄 번호·원문은 위 sha(`21202c44641a`)의 live 기준이다 — 집행 전에 sha 를 다시 보라.

### B1-① live `:179` — §6-9 불변식 5(b) 의 ⑶

before(원문 그대로 · 한 줄):

```text
    **(b) 입력줄로 온 재승인 + master-send 원장 대조 성립** — 줄머리 **master-send 표식**(래퍼 자동 부착 = 이것이 곧 NONCE · ⛔서식 견본을 여기 적지 않는다 — 실물은 원장에서만 확인. 2026-09-12 CSO 규명: 옛 자리표시자를 워커가 6hex로 채워 자기 위조한 사고)을 `~/.claude/channels/.master-send-ledger.jsonl`에서 조회해 ⑴nonce 일치 ⑵대상 = 자기 surface ⑶제출 판정 yes ⑷시각이 내 ② push 이후 — **넷 전부** 충족 시 재승인 성립. **근거**: 원장도 워커 컨텍스트 밖의 append-only 기록이고 고스트는 원장에 쓸 수 없다 — body_sha256·제출 판정까지 붙어 인박스 줄보다 강한 증거다(420 판정 채택·2026-08-09).
```

after(바뀌는 곳 = 「⑶제출 판정 yes」 한 군데):

```text
    **(b) 입력줄로 온 재승인 + master-send 원장 대조 성립** — 줄머리 **master-send 표식**(래퍼 자동 부착 = 이것이 곧 NONCE · ⛔서식 견본을 여기 적지 않는다 — 실물은 원장에서만 확인. 2026-09-12 CSO 규명: 옛 자리표시자를 워커가 6hex로 채워 자기 위조한 사고)을 `~/.claude/channels/.master-send-ledger.jsonl`에서 조회해 ⑴nonce 일치 ⑵대상 = 자기 surface ⑶제출 판정 = `submitted` yes 또는 queued ∧ `verdict_by`=session_jsonl_nonce ⑷시각이 내 ② push 이후 — **넷 전부** 충족 시 재승인 성립. **근거**: 원장도 워커 컨텍스트 밖의 append-only 기록이고 고스트는 원장에 쓸 수 없다 — body_sha256·제출 판정까지 붙어 인박스 줄보다 강한 증거다(420 판정 채택·2026-08-09).
```

### B1-② live `:236` — §6-12 수신 규율의 4요건

before:

```text
  조회 → nonce·대상·제출판정·시각 4요건)를 통과해야 지시다. 대조가 안 되면 **이행 금지 + master 질의.**
```

after:

```text
  조회 → nonce·대상·제출판정(yes 또는 queued ∧ verdict_by=session_jsonl_nonce)·시각 4요건)를 통과해야 지시다. 대조가 안 되면 **이행 금지 + master 질의.**
```

- 근거(발신 원장 실측 2026-10-10 13:5x · `type=send ∧ kind=body`): `submitted=queued ∧ verdict_by=session_jsonl_nonce` = 266건 · `queued ∧ verdict_by=empty_x2` = 1건. queued 는 수신 좌석이 턴 중이라 입력이 대기열로 들어간 도착이고, `session_jsonl_nonce` 는 그 좌석 세션 jsonl 의 user 레코드에서 표식을 실제로 본 판정이다. 그래서 queued 는 **verdict_by 조건과 함께일 때만** 성립으로 본다(empty_x2 단독은 도착 증거가 아니다).
- 이 티켓에서 받은 master 발신 7건 중 3건(#073cd7e8 · #aac63fe1 · #53691800)이 queued 였고, 앞 티켓(cysr-1110-backlog)에서도 3건이 그랬다 — 지금 문구(「yes」 만)대로면 정상 지시를 워커가 매번 예외로 해석해야 한다.

### B2 — 종료 규칙 1줄

저장소 팩(커밋 `46021d70` · `cysjavis-pack/directives/WORKER_DIRECTIVE.md:82`)에 넣은 줄:

```text
4. **프로세스 종료는 자기 pid/pgid 만.** `pkill -f`·`killall`·이름 일치 종료는 금지다 — 이름으로 고르면 같은 이름의 남의 프로세스(다른 좌석·설치본 데몬)까지 죽는다. 옵션은 패턴 앞에 둔다(macOS `pkill` 은 패턴 뒤 인자를 옵션이 아니라 추가 패턴으로 읽는다 · 2026-10-10 09:00 master·CSO 동시 사망 사고).
```

live 삽입 위치 = live `:79` 뒤(§1 의 3번 다음 · 지금 `:80` 은 빈 줄 · `:81` 은 `## 2.` 제목). 앞뒤 줄 원문:

```text
3. 장시간 서버는 master에 보고한다. 터미널의 watchdog이 중복·과부하를 감시하고 있다 —
   `watchdog.duplicate_procs` 경보의 주인공이 되지 마라.
    ← 여기에 위 1줄

## 2. ★전(全) 기능 오케스트레이션 (워커=내부 오케스트레이터)
```

- live 가 오너 수정본이라 다음 팩 갱신에서도 이 줄은 `.new` 로만 간다. live 발효 = master 가 위 1줄을 직접 넣는다.
- 실측(읽기 전용 `pgrep` · 내 `sleep 987` 1개 · pid 로 정리): 옵션 앞 `pgrep -f 'sleep 987'` = 내 pid 1개 / 옵션 뒤 `pgrep 'sleep 987' -f` = **무관한 pid 2개**(내 것 아님 — `-f` 가 패턴으로 읽혔다) / `man pkill` 시놉시스 = `pattern ...`.

## 3. C 의 판정 기록

- **C2 방향 정정(master#aac63fe1)**: 브리프는 `HANDOFF-1110.md` 의 2R 이관 기록을 「휴면 코드 / Windows / pack flaky / agy RPC 이력」 으로 고치라고 했으나, 그 줄(「feed_sweep · schedule · Windows · flaky pack」)이 2R 보고서 실물과 일치했다. 브리프의 목록은 master 의 3R 프롬프트 요약 오기였다 → 줄은 그대로 두고 대조 1줄만 더했다. 2R WARN 4·5(feed_sweep 400바이트 창 · schedule 검체 id)는 **닫힌 것이 아니다**.
- **C1 음성 대조**: 설명서 수정 전 = 줄 규칙 1 통과(소문자 agy 라 못 봄) · 줄 규칙 2 적 `[1900, 1901, 1902]`.
- **C1·C3 뮤턴트**: README 에 현행형 Antigravity 줄 = 적(README 547 · 같은 주입 × 옛 시험 = 17/0 통과) · 줄 규칙 1 끔 = 적 · 줄 규칙 2 끔 = 적 · 설명서 1900 줄 휴면 지움 = 적 `[1900]` · agy-statusline 줄 휴면 지움 = 적 `[1902]` · 살아 있는 소문자 agy 줄 추가 = 17/0.
- **C3 문구 근거**: `src/bin/cys.rs` 상태줄 래퍼가 agy 페이로드를 휴면 때 push 0 · `src/bin/cysd/accounts.rs` 의 agy 계정 귀속·행 생성·부트 복원이 전부 `agy_lane_enabled` 뒤. `statusline-outside` 는 살아 있는 값이라 따로 한 줄로 뗐다.

## 4. 함정(다음 사람에게)

- **origin 추적 참조가 안 따라온다**: `git fetch origin` 이 출력 없이 끝나도 `origin/int/1110-upstream` 이 옛 sha 에 머물 수 있다. `git ls-remote origin refs/heads/<가지>` 로 원격 실물을 보고 `git fetch origin <가지>` 로 지정해 받는다. 번들 git 은 https 헬퍼가 없어 `/usr/bin/git` 을 쓴다.
- **새 팩 시험 파일 = CI 3레인 5개 루프 동시 등재**가 계약이다(`scripts/lane-parity-rehearsal.sh` 3단계 · 「등재를 미룬다」 는 사유가 아니다). 정적 lint 는 boot-health 검체로 넣으면 ci-branch 전량 레인이 자동 편입한다(`H-CI-COVER-1` 이 배선을 잰다).
- **스크립트형 팩 시험을 `python3 -m unittest` 로 부르면 rc 5(0건 실행)**: 마지막 줄에 OK 토큰이 찍혀도 rc 는 5다. `__main__` 유무로 고르면 5개(`test_capgate_remeasure_order` · `test_dept_ticket_deficit_zero` · `test_preflight_nlm_pin` · `test_preflight_only_dispatch` · `test_preflight_settings_fifo`)를 잘못 고른다 → rc 5 면 스크립트로 다시 부른다.
- **격리 env 가 필수인 시험 2**: `test_preflight_phase1_checks` · `test_verify_gate` 는 `JAVIS_ROOT`·`CYS_PROBE_RUNS` 없이 rc 2(REFUSE)다.
- **boot-health 잔재**: 실행 뒤 `cysjavis-pack/bin/tests/` 아래 `X:\Prog Files\javis_bootstrap.py/` 폴더가 남는다(작업 트리 미추적 1줄) — 지운다.
- **app 시험 준비물**(gitignore): `src-tauri/binaries/{cys,cysd}-aarch64-apple-darwin`(이 트리 debug 빌드 사본) · 빈 `src-tauri/resources/pack.tar.gz` · `pack-manifest.json`(`{}`) · `src-tauri/runtime/.keep` · `ui/dist/index.html` → `cargo test -p cys-app -- --test-threads=1` → 끝나면 지운다. `ui/node_modules` 는 1.1.10 선 트리에서 APFS 복제(`cp -c -R`).

## 5. 남은 일(이 티켓 밖 · 별 티켓)

- **live 디렉티브 3곳 집행**(§2 · master): `:179` · `:236` 치환 + `:79` 뒤 1줄.
- **파이썬의 `pkill -f` 6곳**: `cysjavis-pack/bin/javis_phoenix_harness.py` 5곳(`pkill -9 -f "sleep 600"` · :1273 · :1298 · :1463 · :1491 · :1679) · `cysjavis-pack/bin/tests/test_d1_dept_ready_probe.py:84`(`/usr/bin/pkill -f <고유 표지>`). 고치려면 하네스 종료 경로를 pid/pgid 로 다시 써야 한다. `H-SH-PKILL-1` 은 셸만 본다.
- **성찰 보고서 「주인 이해 회복」 절**(전임 HANDOFF-1110-backlog §2 둘째 항목): jarvis-agora(데스크 코드 · 다른 저장소) `agora/counsel.py` 의 WEEKLY_PROMPT_ADDENDUM · _weekly_report_md — 이 저장소 범위 밖.
- **2R WARN 4·5**(feed_sweep 400바이트 창 · schedule 검체 id) = 기록 유지 · 미해소.
- 전임 HANDOFF-1110-backlog §4 관찰 7건은 그대로다(수정 0).

## 6. 재현 명령

```bash
STRIP() { env | grep -o '^CYS_[A-Z0-9_]*' | sed 's/^/-u /'; }
ISO() { env $(STRIP) -u CLAUDE_CONFIG_DIR HOME=$(mktemp -d) "$@"; }
( cd ui && ISO bun test src/publicdocs.test.ts )                                   # 17/0
( cd cysjavis-pack/bin/tests && ISO python3 run_bootstrap_health.py --only H-SH-PKILL-1,H-CI-COVER-1 )
python3 scripts/gen_ceo_template.py --check
ISO cargo test --bin cysd manual_                                                  # 설명서 include_str 핀 6/0
```
