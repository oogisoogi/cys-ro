# HANDOFF — TICKET=cysr-1111-fable-fixes (2026-10-23 · worker-1111fable)

- 기점 = `int/1111` `abc137c0` · 가지 = `fix/1111-fable-fixes` · 다른 가지(`fix/1111-backlog-misc`) 무접촉.
- 출처 = Fable 적대 검토 `~/axdev/master/reports/fable-debug-1022/cysr-1111.md`(치명 0 · 높음 0 · 중간 2 · 낮음 5 — 전부 읽음).
- 비가역(push·태그·릴리스) 0 · 실제 open·설치기 실행 0 · 남의 프로세스 종료 0.

## 0. 한눈에

| 번호 | 심각도 | 처분 | 커밋 | 시험(수리 전 적 → 녹 · 뮤턴트) |
|---|---|---|---|---|
| F1 | 중간 | **수리** — 순환 유휴 판정을 물리 행 재료로 | `857cd6d2` | `f1_cycle_idle_reads_physical_rows_of_a_wrapped_composer` · 적(ⓐ Idle 기대 ← HumanDraft) → 녹 · 원 코드 복원 뮤턴트 적 |
| F2 | 중간 | **수리** — 윈 생산자 생존 = `state::pid_alive` + WIN-FIELD 3행 | `11e774eb` | pid 매핑 검체 전 플랫폼화 + 윈 갈래 본문 핀 · 뮤턴트(윈 갈래 `None`) 적 · win-typecheck rc 0 |
| F3 | 낮음 | **수리** — 총줄수 = P+N 단언 | `6f5cc09c` | `test_24_guard_fails_closed_on_unclassified_output_format` · 적(따옴표 + 같은 태그 공개 = rc 0) → 녹 · 17/17 |
| F4ⓑ | 낮음 | **수리** — prune 을 ConstrainedLanguage 에서도 돌게 | `58684e16` | 하네스 N11 inst4 · 적(removed=0 · 잔재 남음) → 녹(removed=3) · N1~N11 OK |
| F4ⓐ | 낮음 | **처분** — 정상 분류(WIN-FIELD FABLE-F4a) | 문서 | — |
| F5 | 낮음 | **처분** — 정상 분류(WIN-FIELD FABLE-F5) · 코드 변경 0 | 문서 | — |
| F6 | 낮음 | **보류 · 【결정필요】** — 기존 시험이 반대 설계를 고정 | — | §2 |
| F7 | 낮음 | **보류** — 문안은 master 결정 원문(adv-fixes #11) | — | §2 |

## 1. 수리 상세

### F1 — 좌석 순환 유휴 판정(`src/bin/cys.rs` `cycle_target_observation`)
- 원인: 마커 해소(`pick_marker_leading_on_screen`)와 편집 영역 판정(`cycle_target_state` 의 `screen`)이 `text`(`contents()`)를 읽었다.
  윈 fullscreen 좌석은 꽉 찬 괘선 뒤 composer 가 이어 붙어 `────…❯ …` 한 줄이 된다(WINQ-2 와 같은 뿌리).
- ★Fable 보고와 다른 점(재현으로 확인): 보고는 「영구 미발동(fail-closed)」 한 방향만 적었다. 시험으로 재 보니 **두 방향**이다.
  - ⓐ 앞 전사에 선두 `❯` 행(지난 지시 문면)이 있으면 그 행이 「마지막 선두 마커 행」으로 잡혀 초안으로 읽힌다 →
    빈 composer 인데 `HumanDraft`(rc 85) → 순환 영구 보류. (보고의 방향)
  - ⓑ 선두 `❯` 행이 화면에 없으면 마커 없음 축 → 계수 0/0 · 정적이면 `Idle` → **화면에만 있는 초안 위에 clear 가 나갈 수 있다**
    (보고에 없던 방향 · fail-open). 사람 축 계수(`pending_input_human_bytes`)가 1바이트라도 있으면 첫 분기가 잡으므로
    실제 노출은 「계수 0 인데 화면에 초안」인 프레임에 한한다.
- 수리: `let layout = screen.as_ref().zip(screen_text).map(|(r, t)| carry_layout(r, t));` → 마커 해소·`cycle_target_state` 에 `layout`.
  관문·모달 판독(`gate_or_modal_foreground`)은 `text` 그대로(이번 가지 세 소비처와 같은 규칙). 구 데몬(`layout_text` 키 없음) = 종전 재료.
- 시험: 두 경우 각각 ① 물리 행 화면 자체의 판정 = 기대값(전제) ② `{"text": 이어 붙은 화면, "layout_text": 물리 행}` 판정 = 기대값(수리 단언)
  ③ 이어 붙은 화면만 = 기대값 아님(윈 증상을 재는지의 전제) + 배선 핀(관문 판독 재료 불변 · `carry_layout(r, t)` 실재).
- 한계: ConPTY 가 실제로 이어 보내는지는 윈 실기로만 확정(WINQ-2 와 같은 한계) → WIN-FIELD FABLE-F1.

### F2 — 윈 휴지통 생산자 생존(`src/bin/cysd/trash.rs` `real_alive`)
- 원인: `#[cfg(not(unix))]` 갈래가 모든 pid 에 `None` → `.producer-*` 상태 `open` 항목은 생산자가 죽었어도 `Undeterminable` →
  `producer_blocks` → 「크기 미리 보기」가 `R_PRODUCER_ACTIVE` 로 영구 거부(맥은 같은 항목이 `InterruptedOpen` 통과).
- 수리: 윈 갈래 = `Some(crate::state::pid_alive(pid))`. 그 함수는 이미 있던 윈 구현(OpenProcess(SYNCHRONIZE) + 0ms 대기 ·
  접근 거부·대기 실패 = 「있다」 · 그 밖의 열기 실패 = 「없다」 · 윈에서도 도는 `channels.rs` 브리지 생존 판정이 쓰는 같은 함수). Fable 이 제안한 `sysinfo` 대신 이것을
  쓴 이유 = 새 판정 코드를 만들지 않고 저장소의 윈 pid 생존 정본 하나를 쓴다.
- 판정 방향: pid 재사용 = 「살아 있다」 오판 = 거부 쪽(맥과 같다). ⚠「접근 거부 외 열기 실패 = 없다」는 맥보다 한 칸 넓다
  (맥 `kill(0)` 은 ESRCH 만 없음 · 그 밖은 `None`). 귀결 = 그런 항목이 `InterruptedOpen` 으로 크기가 재진다 —
  **윈 삭제는 여전히 꺼짐**(`delete_supported`)이라 지워지지는 않는다. 윈 삭제를 켜는 판에서는 이 한 칸을 다시 볼 것(해석).
- 화면 효과(해석 · 윈 실기 전): `list_payload` 의 `deletable = !interrupted && !producer_blocks(..)` 이라 그런 줄이 윈에서
  고를 수 있게 된다(크기 미리 보기 대상). 칩 = `producer did not finish (interrupted)`.
- 시험: `list_maps_a_live_and_a_dead_producer_pid_to_running_and_interrupted`(종전 `_unix` · `#[cfg(unix)]`)를 전 플랫폼으로 풀었다 —
  그 검체 주석이 「D2 가 고쳐지면 `cfg` 없이 전 플랫폼으로 돌아온다」고 예고한 그대로. 맥 빌드는 윈 갈래를 컴파일하지 않으므로
  같은 검체에 윈 갈래 본문 핀을 더했다(뮤턴트 = 윈 갈래 `None` 복원 → 적 「윈 생존 판정이 pid_alive 가 아니다(D2 회귀)」).
  관련 주석 3곳(「윈은 None」)을 현행에 맞췄다.
- WIN-FIELD: `docs/release-1111/WIN-FIELD-1.1.11.md` FABLE-F2(실기 절차) · FABLE-F2b(윈 `RootDir` 신원 (0,0) = B2 검사 무효 · 기록).
  ★1.1.11 용 WIN-FIELD 파일이 저장소에 없어 **씨앗 파일을 새로 만들었다**(지시 없이 내린 판단 — 발행 준비 티켓이 다른 가지 항목과 합친다).

### F3 — 릴리스 draft-guard(`.github/workflows/release.yml`)
- 수리: 분류 전 `T="$(printf '%s\n' "$N" | grep -c . || true)"` · `[ "$T" -ne $((P + N)) ]` 이면 `::error::분류되지 않은 줄 …` exit 1.
  (`N` 이 뒤에서 draft 수로 재사용되므로 T 는 그 전에 잰다.) 빈 출력 = T 0 = P+N 0 = 진행 그대로.
- 시험: 가짜 gh 에 `FAKE_JQ_RAW=0`(jq 비-raw = 따옴표 출력) · `FAKE_EOL=\r\n` 모드 추가. 같은 태그 공개 + 따옴표 = rc 1 ·
  같은 태그 공개 + CRLF = rc 1 · 같은 태그 없음 + 따옴표 = rc 0. 수리 전 첫 단언 적(rc 0 = Fable 의 fail-open 재현).

### F4ⓑ — 설치기 dist-info 정리(`src-tauri/nsis/cys-runtime-prune.ps1`)
- 재현(pwsh 7.6.6 · 세션 언어 모드를 ConstrainedLanguage 로 강제 · 하네스 N10 과 같은 방법):
  ① 원본 = `cys-runtime-prune: stopped (메서드를 호출할 수 없습니다…)` · `removed=0` · 잔재 남음.
  ② `[IO.File]::ReadAllText` 만 고치면 → 항목마다 `failed` — 원인 줄 = `foreach ($e in $Dir.GetFileSystemInfos())`(DirectoryInfo 메서드).
  ③ 둘 다 고치면 → `removed=1 failed=0` · 잔재 0 · 배포본 dist-info 유지.
- ★Fable 수리안과 다른 점: `[regex]::Matches`·`[regex]::Replace`·`[string]::IsNullOrEmpty` 는 코어 형식이라 ConstrainedLanguage 에서 **허용**된다(실측 ③) —
  regex 교체는 하지 않았다. 바꾼 것 = `Get-Content -LiteralPath $man -Raw` · `Get-ChildItem -LiteralPath $Dir.FullName -Force`(한 층 · `-Recurse` 없음 ·
  재분석 지점은 들어가기 전에 본다 = 종전과 같은 자기 걸음) · `$e.PSIsContainer`. 머리 주석에 「ConstrainedLanguage 에서도 돌아야 한다」 1줄. 순수 ASCII 유지.
- 시험: 하네스 `scripts/tests/nsis-hook-compile/run.sh` N11 에 inst4(같은 픽스처)를 ConstrainedLanguage 로 정리 → 요약 `removed=3 failed=0` · 잔재 0 단언.
- 한계: Windows PowerShell 5.1 실측 0(맥 pwsh 7.6) → WIN-FIELD FABLE-F4.

## 2. 처분(코드 변경 0)

| 번호 | 처분 | 근거 |
|---|---|---|
| F4ⓐ | 정상 분류 · WIN-FIELD FABLE-F4a | Fable 「수리 대상이 아니라 체크리스트 1줄」 그대로 |
| F5 | 정상 분류 · WIN-FIELD FABLE-F5 | Fable 권고 「다음 판 · 문서/코드 중 택1」 → 문서. 코드 수리(②에서 fresh 면 무행동 성공)는 NSIS 훅 + 모델 `place()` 미러 둘을 함께 바꿔야 한다 |
| F6 | **보류 · 【결정필요】** | 아래 |
| F7 | 보류 | adv-fixes #11 이 「문안 = master 결정 원문」으로 올린 항목 — 워커가 문안을 정하지 않는다. Fable 제안 = `previewOnly` 갈래 머리말 「크기를 재지 못한 항목(데몬이 거부했습니다):」(`ui/src/trashconfirm.ts:452`) |

### F6 【결정필요】 — `cys-dept` 승자 대기 실패 뒤 정리
- 사실: 기존 시험 `cysjavis-pack/bin/tests/test_d1_dept_ready_probe.py` `test_live_lock_holder_that_never_answers_fails_within_the_stall_budget` 이
  **「산 승자가 락만 쥐고 응답하지 않아 실패한 뒤 등록이 지워진다」를 단언**한다(`assertFalse(self._reg_has_probe(), "기동 실패 뒤 등록이 남았다 — 원복 미이행")`).
  Fable 수리안(ⓑ 승자가 살아 있으면 `reg_remove` 건너뜀)은 이 단언을 뒤집는다 = 설계 변경이다.
- 선택지:
  - A. Fable 안 전부 — ⓐ 우리 pid 가 이미 죽은 것을 본 경우 `kill` 건너뜀 ⓑ 승자가 살아 있으면 등록 유지(「등록 있는 산 데몬 = `cys-dept down` 으로 회수」 원칙과 맞음) · 위 시험 단언 반전.
  - B. ⓐ만 — 죽은 것을 본 pid 에 `kill` 을 보내지 않는다(pid 재사용 오살상 창 제거 · 시험 단언 무변경). 등록 정리는 지금대로.
  - C. 현행 유지(문서만).
- 권고 = **B**. 이유: ⓐ는 무관 프로세스 SIGTERM(최대 120초 창)이라는 실해이고 설계 논점이 없다. ⓑ는 「응답 못 하는 승자를 등록에 남길지」라는
  설계 판단이라 adv-fixes #7 도 그렇게 남겼다. 미결 시 영향 = 없음(이번 판 동작 = 1.1.11 후보 그대로 · 창은 승자 대기 경로에서만 열린다).

## 3. 검증(맥)

(게이트 숫자는 아래 표 — 커밋 후 작업트리 = 커밋 내용)

| 묶음 | 결과 |
|---|---|
| `cargo test --offline -p cys-terminal --lib` | **1101** pass · 0 fail(2 ignored) |
| `--bin cys` | **629** pass · 0 fail(기준선 628 + 신규 F1 1) |
| `--bin cysd` | **2709** pass · 0 fail(9 ignored · 이번 판은 플레이크 0 · F2 는 맥에서 이미 돌던 검체의 cfg 만 풀어 개수 무변) |
| ui `bun test` · `bun run typecheck` | **3186 pass · 85 skip · 0 fail**(98 파일) · typecheck rc 0(`ui/node_modules` 는 `1111-advfix` 에서 APFS 복제 `cp -cR` · gitignore · 복제 전 첫 실행은 타입 선언 부재로 TS7006 2건 = 환경 산물) |
| `sh scripts/win-typecheck.sh` | rc 0 · 오류 0 · 경고 65(기준선 65 · trash.rs 는 기존 `:1057` 1건뿐) |
| `scripts/tests/test_release_trigger_split.py` | 17/17 OK |
| `scripts/tests/nsis-hook-compile/run.sh` | N1~N11 OK(makensis · pwsh 7.6.6) |
| 팩 py 전건 189(시험마다 짧은 임시 HOME · `env -i` = `CYS_*` 상속 0 · `JAVIS_ROOT`/`CYS_PROBE_RUNS`/`CYS_UPDATE_STATE_DIR` 격리 · `CYS_FEEDBACK_BASE=127.0.0.1:9` · 동시 4 · 약 8분) | **187 rc 0** · 적 2 = `test_agora_known_authentic`(기준선 적 · 「제작 맥 전용」) · `test_dept_team_token`(rc 2 = 시험 자신의 「CYS_PACK_DIR 를 격리 경로로」 거부 = 실행 조건 산물 → `CYS_PACK_DIR=<임시>` 로 단독 재실행 **23 OK**). 이번 가지는 팩 파일 변경 0 |

## 4. 남은 것·한계(정직)
- 윈 실기 0 — F1·F2·F4 는 맥 합성 화면·맥 pwsh·맥 빌드 본문 핀까지가 증거다(WIN-FIELD-1.1.11 6행).
- F2 의 「접근 거부 외 열기 실패 = 없다」 한 칸(§1 F2) — 삭제 꺼진 동안은 크기 측정에만 영향.
- 증류: 「pwsh ConstrainedLanguage 에서 막히는 것은 코어 밖 정적 호출·메서드뿐 — [regex]·[string] 은 허용」 1건(§1 F4ⓑ 실측)을 기억 후보로 master 에 올린다.
