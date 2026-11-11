# HANDOFF · TICKET=cysr-agy-policy-exposure — agy 좌석 문(2단계 구현)

- 지시: master#aba34fa5(11-11 10:49 · 원장 대조 성립) · 1단계 설계 = `DESIGN-agy-policy-exposure.md`(813f3291)
- 가지 `fix/agy-policy-exposure` ← v1.1.14 `270e3e21` · 로컬 커밋만(push 0)
- 작업 = worker-10(surface:1942)

## 끝난 것(커밋)

| 커밋 | 내용 |
|---|---|
| 33236d7f | leaf `src/agy_door.rs`(판정·문 파일·문안·76) · launch-agent/boot_agent_on_surface/restore 1줄씩 · agent-detect `apply_agy_door` · src-tauri `agy_seat_door_get/warning/set` · ui 팔레트 「Antigravity(agy) 좌석 열기/닫기」(열 때만 확인 창) |
| c67fe476 | phoenix `agy_door_split`(오라클이 agy_consumer_policy 면 부활 대상 제외 · claude 만이면 호출 0) · guard.sh `[AGY-DOOR]` · `test_agy_door.py` 12 · CI 5 루프 등재 |
| 62b1f8d2 | MASTER §7 머리 2줄(바이트 래칫 때문에 같은 파일 이력 괄호·§13 중복 문단 삭제 → 순 −6B · 상한 낮춤) · CEO 재합성 · CORE §7·§13 해시+요지 · WORKER §11 · 토론 스킬 · README/설명서 |
| d82dc75b | new-surface 우회 길 차단 · `agy_door_wiring_tests` 3 · 발행 해시 표 · H-SEAT-4AXIS 창 경계 수정 · `docs/agy-door-evidence/acceptance.py`+결과 |

## 결정(지시 없이 내린 것)
- 문 = **앱 화면(명령 팔레트 확인 창) → `~/.cys/agy-seat-door.json`**. 환경 변수 안 씀: Claude 가 명령 앞 한 줄로 열 수 있고(⑤ 불가) 여는 순간 사람에게 경고를 보일 자리가 없다.
- 어댑터 판정 = 키 `gemini` **또는** cmd 실행 파일 `agy`/`antigravity`(키 개명 우회 차단). ⚠ API 열쇠로 gemini 키를 쓰는 사용자도 막힘 → 그 사람은 문을 열면 된다.
- 종료 코드 76(저장소 미사용 값).

## 실측(합격)
- `python3 docs/agy-door-evidence/acceptance.py`(cargo build --bin cys --bin cysd 선행 · 약 10분): 격리 하네스 데몬 + 가짜 agy/claude/codex · 실 agy 실행 0 → **14/14 PASS**(문 닫힘 11 입구 agy 생성 0 · 사람 직접 agy +1 · 문 열림 launch/restore 종전대로)
- 뮤턴트: M1(launch-agent 줄 삭제)·M2(boot_agent_on_surface 줄 삭제) → 각각 배선 핀 적색. M1 은 실측에선 2중 방어(boot_agent_on_surface)가 agy 를 막아 rig 초록(핀이 잡음).

## 함정
- 팩 훅 시험은 `CYS_PACK_DIR` 가 있으면 설치본 훅으로 위임된다 → `env -u CYS_PACK_DIR` 또는 `CYS_HOOK_LANE_GUARD=0`.
- phoenix 하네스 시험 2개(e2e_replacement·w2_untomb)는 TMPDIR 별칭에서 `aliased_harness_root` → `bash scripts/ci/phoenix-host-gate.sh <시험>` 로 돌린다.
- MASTER 바이트 래칫(test_cso_directive_rev) — 지침에 글을 더하면 같은 파일에서 그만큼 줄여야 한다. 고치면 `gen_ceo_template.py` · `core_inject.py verify` · `gen_released_directive_hashes.py` 셋 다.
- run_bootstrap_health 의 H-CLT-1/2 는 셸의 `CYS_*` env 누출로 붉을 수 있다(확인 중 — 아래 미완).

## codex 1R(12:10~12:20 · BLOCK) 처리
- 반영(f2f5536e · 그 뒤 커밋): blocking 2 = `cys run -- agy` 우회 차단 · cmd 해석을 셸 문법으로(인용·대입·env 래퍼·sh -c·.bat · 대입 값 속 agy 오판 해소) / major = 실행 프로그램이 정본·키 gemini 추정은 cmd 없을 때만 · guard 읽기 허용에서 git 제외 · bash 백스톱에도 [AGY-DOOR] · phoenix 가 fresh rc 76 을 정책 건너뜀으로 소비(재시도·실패 계상 밖) / minor = Write 거부를 실제 문 파일명으로
- **미반영(2R 몫)**: ① acceptance.py 판정이 agy 실행 횟수 차이만 봄 → 입구별 기대 rc·사유 단언 추가 필요(E6 rc=1·E7 launch_failed·E8 rc=78 이 PASS 로 기록됨 — 차단은 맞으나 「도달」 증명이 약함) ② phoenix 최종 결과의 manual_seats 에 정책 제외 역할이 「빈 좌석·사람이 실행」으로 다시 들어감(codex minor · javis_phoenix.py:3410 부근) ③ guard 가 `sed -n 1p <문 파일>`·`python3 -m json.tool` 같은 읽기도 막음(codex minor · 거짓 양성 · 안전 쪽)
- verdict 원문 = 세션 scratchpad `codex/verdict.json`(커밋 안 함)

## 2R 몫 처리(master#38e5ce91 순환 재개 · 12:36~)
| 커밋 | 내용 |
|---|---|
| 14d6f11a | 1R 미반영 3건 — acceptance 입구별 rc·사유 단언 · phoenix manual_seats 정책 제외(+agy_policy_skipped_roles) · guard sed/json.tool 읽기 허용 · 결과 파일 비식별(H-SECRET-1 적색 해소) |
| ebfd6611 | codex 2R(BLOCK) 반영 — env -S 우회 · cys run argv 판정 · sed 스크립트 자리 검증 · 백스톱 복합 명령 거부 · phoenix 첫 restore 건너뜀 줄 즉시 소비(재스폰 계수 되돌림 · 차단기 리셋 · fresh 끔 경로) · ②E5 역할 블록 결속 · 문서 파일 과차단 해소 · 구조 보존 비식별 |

- codex 2R(13:2x · gpt-6.1-sol · read-only): verdict **BLOCK** · 1R 9건 중 닫힘 4 · 미닫힘 5 · 새 지적 blocking 1·major 4·minor 2 → 전부 ebfd6611 반영
  (원문 = 세션 scratchpad codex2/verdict.json · 커밋 안 함). ⚠반영분에 대한 codex 재검(3R)은 **안 돌림** — 다음 검증 좌석 몫.
- 실측(최종 코드 ebfd6611 바이너리): acceptance **15/15 PASS**(판정 = 횟수+rc+사유+역할 결속 · 결과 파일 비식별) · test_agy_door 15 ·
  test_agy_door_phoenix_loop OK(뮤턴트 2 적색) · guard/phoenix 단위 31 + host-gate 3 PASS · H-SECRET-1 PASS
- health 전체(깨끗한 env · 14d6f11a 이전 트리): 166 PASS / 3 FAIL — H-SECRET-1 = 이 가지 결함(해소) · **H-CLT-1/2 = 기존 결함**:
  기준판 270e3e21 도 깨끗한 셸에서 같은 적색 → env 누출 가설 기각. 원인 = 검체 샌드박스(_u15_sandbox)가 `CYS_TEST_SYSROOT` 를 안 주고,
  이 기계에 `/Applications/cys.app` 가 실재해 `_lib.sh:205` 탐침이 진짜 앱 python 을 고름(검체 비밀폐 · 이 티켓 범위 밖 · 📌 master 판단).
- cargo: 이전 세션 전체 실행(acceptance 와 동시) 3 FAIL(trash background_walk · native_publication 2) → 단독 재실행 3/3 ok(부하 민감) ·
  test_phoenix_c6_reap 도 동시 실행에서만 시간 초과 · 무부하 재실행 PASS. 최종 전체 실행(bc27f1ca · CARGO_BUILD_JOBS=4 · --test-threads=4 · 15:20~16:20 · 부하 9.7→15.9) = rc 0 · app 337 · lib 1213 · cys 759 · cysd 3227 · 통합 11+4 · 실패 0 · 2R 실행 중 나온 cys bin 스택 넘침(a3_strip_hook_digits…)은 단독 3/3 ok · 이번 전체 실행 ok(병렬 부하 민감).

## 독립 재검(codex 한도 소진 · master#fe668845 대체 규칙)
- 대상 = ebfd6611(2R 반영분) · 맥락 없는 서브에이전트(읽기 전용 · 커밋 차이 + 잠금 기준만) · verdict **BLOCK**
  · 고침 확인: 2R 반영 7건 중 닫힘 5(sed 스크립트 · phoenix 소비 · ②E5 결속 · 문서 과차단 · redact) · 미닫힘 2(env 묶음 옵션 · 백스톱 `<(`)
  · 새 지적: blocking 1(판정이 첫 단순 명령·짧은 래퍼 목록만 봄 — `cd x && agy`·`bash --norc -c agy`·`timeout 5 agy`·`sudo agy` 등 통과)
    · major 2(fix 6 회귀 = 붙여 쓴 낱말 · 파이썬 경로 명령/프로세스 치환) · minor 1(rg --pre · 스크립트 파일 간접)
- 1회 고침 = bc27f1ca(전부 반영 · 스크립트 파일 간접은 한계 주석으로 명시) · ⚠고침분 재검은 안 돌림
- 사후 codex 필요 = **예**(실행 정책·훅 거부 규칙 = 보안 경계 성격) · master 가 11-13 06:47 뒤 · 그 전 발행 묶음 제외

## 3R 라운드(master#a078504c · #3dde347c · 16:5x~)
| 커밋 | 내용 |
|---|---|
| 753a3dbc | ②E5 결정화 — 앞 입구 역할 묘비 → restore 대상 gemini 하나 · rc 0 |
| dfa3e561 | codex 3R 일부 — 판정 = 치환 본문 재귀·cmd /c·powershell·find -exec·셸 -o/-O·here-string·줄 이음·맨 낱말 안전망 · guard 문 이름 정확 판정 + 치환 재귀 |
| 7ed51a57 | 독립 검증 966 B1(일정 등록·발화 · 채널 · 계정 어댑터 · round-log) · B2(숨은 `cys agy-door-check` + guard [AGY-RUN] · cys send 실행문) · M1 줄일 수 있는 부류(리다이렉트 머리 · zsh 앞말 · csh/fish/su · `$'agy'` · `a^gy` · 파이프 셸) · M3(데몬 send_text: 문 닫힘 + agy 좌석 + 사람 자판 아님 → 거부) · codex 3R phoenix 차단기 순서 |
| f740c3f5 | 설명서·DESIGN §7·모듈 머리 「알려진 한계」 · OPEN_WARNING API 열쇠 한 줄 · 지침·스킬 3파일(REVIEWER 는 래칫 고정이라 그대로) |
| d6efdf5e | guard R8(python json.load 읽기) 거짓 양성 |

- codex 3R(스냅샷 753a3dbc · 17:0x 완주 · 한도 재소진 전) = BLOCK → 처분: 실행자 누락·거짓 양성·phoenix 차단기·결과 파일 미갱신·확장자 과차단 = 고침 / `HOME` 경로 = 부분 수용(문구·시험 정정 + 다른 폴더 문 파일 쓰기 거부 시험 · 경로 고정은 기각: 격리 시험이 HOME 으로 격리 · 윈도우 홈도 환경 변수) / 「열거식 파서로는 ① 불가」 = master 범위 판단대로 줄일 수 있는 부류만 + 한계 문서화
- 966 재현 3종(내 빌드로 경로만 바꿔 재실행): 우회 77꼴 = 막힘 57 · 우회 15(전부 원리상 못 막는 부류: 변수 2·중괄호/글롭 3·스크립트 파일 3·인터프리터 3·사본·심링크·실행 시점 조립 2) · 판정만 37꼴 = 37 막힘 / guard 문 꼴 = 거부 20 · 통과 18(위장 쓰기 7 = 범위 밖 · 읽기 9 정상 · X3·X4 간접)
- 남긴 것(이유): REVIEWER_DIRECTIVE(바이트 래칫 고정 · 리뷰어 일반 서술) · 거부문 머리 코드 `agy_consumer_policy:`(phoenix·acceptance·guard 가 이 낱말로 소비 — 문구만 바꾸면 계약 파손) · `antigravity .`(m5 · PLAUSIBLE · 편집기 실행기 이름 미확인)

- 최종 실측(4ba55981 · 18:24~19:39): acceptance 21/21 × 동시 5회 5/5(부하 20→26 · 순차 5회는 1회 55분 실측이라 상한 안 불가 → 동시) ·
  e2e 무판정 입구 rig = 막힘 7/9(D2 맨 셸 cys send · D3a 글롭 어댑터 = 원리상 부류) · door_forge = 위장 쓰기 3 열림(범위 밖) · 실패 주입 7 닫힘 ·
  팩 32 + host-gate 2 PASS · cargo: app 337 · lib 1216 · cys 759 · cysd 3226/1(pending_requests c8registry = SQLite Locked · 단독 2/2 통과 · 미수정 모듈) · 통합 15
- 4ba55981: 7ed51a57 의 clap 변형 AgyDoorCheck 가 aid_s5_reap_due 시험을 단독에서도 스택 넘침시킴(변형 뺀 대조 = 통과) → clap 앞 수동 분기

## 함정(추가)
- ★최상위 clap `Command` 에 변형을 더하면 시험 스레드(2MB)에서 clap 파싱이 스택을 넘는다(이 판 실측 · 선례 = 갱신 동사·rotate) — 새 숨은 동사는 clap 앞에서 떼어 낸다.
- acceptance ②E5: `cys restore` 에 역할 필터가 없어 E6 이 남긴 reviewer-codex 좌석까지 되살린다 — rc 0/1 비결정(실측 1·0·0) → 역할 블록으로 판정.
- 데몬을 띄우는 시험(acceptance·c6_reap·host-gate)과 전체 cargo 를 동시에 돌리면 시간 초과 거짓 적색이 난다 — 순차로.
- macOS 에 `timeout` 없음 · zsh 는 `$VAR` 를 낱말로 안 나눔(명령을 변수에 담아 실행 금지).

## 미완
- 독립 검증 좌석(master 몫) · 사후 codex(11-13 06:47 뒤 · bc27f1ca 기준) · push 0

## r5 라운드(TICKET=cysr-agy-door-r5 · 후임 surface:1994 · 22:29~ · codex 4R BLOCK 처분)
- 지시 = spawn 브리프(원장 22:28:59 · 대상 1994) + master#7f3602d7(미커밋 acceptance.py 처분)
- **판정 방식 분리**(설계 변경 · 4R 2·3·5): 기계 입구 = `names_agy` 낱말 검사(셸 무해석 · 거짓 양성 받아들임 · 거부 글 덧말) /
  guard·`cys run` = `runs_agy` 실행 자리 검사(프롬프트 CLI·PowerShell 출력 면제 · 인용된 낱말 전체 agy 경로 안전망 · 위임 뒤 바깥 안전망 생략) /
  해석된 실행 파일 = `program_is_agy`(이름만 — 사용자 이름 agy 오판 방지). 표 = `docs/agy-door-evidence/ENTRY-MODES.md`.
- 4R 1 phoenix: 대상이 정책 건너뜀뿐이면 차단기 읽기·쓰기 0(P6 · M5) · 4R 4 데몬: human ∧ ¬machine_origin 이면 토큰 판독 실패여도 통과 +
  원장 `agy_door: 토큰 미확인 통과`(E19) · 4R 7 문 쓰기 프로세스 전역 Mutex + 고유 임시본 + 임계 구역 안 상태 반환 · 4R 8 64KiB·치환 64 상한.
- 4R 6 하네스: 앞 좌석의 **미커밋** acceptance.py 변경(E12~E16 + 묘비 rc) = 발견 6 원인(커밋 누락) → 보강 후 커밋(E13 데몬 schedule.error 사유 ·
  E17 거짓 양성 안내 · E18a/b 4R 2·3 재현 · E19 · 묘비 (rc,출력) 결과 항목 · provenance(커밋·dirty·sha256)) · `run_concurrent.sh` = 동시 N회 원시 기록.

### 함정(r5)
- 낱말 검사에서 `-` 를 낱말 글자로 두면 `env -vSagy`·`${X:-agy}` 가 빠진다 → 「줄표로 시작하는 낱말은 끝이 이름이어도 agy」 규칙.
- guard 안전망을 인용 낱말까지 넓히면 `powershell -Command Write-Output 'agy'` 의 바깥 단위에서 다시 걸린다 → 위임 갈래는 바깥 안전망 생략(true).
- 뮤턴트·acceptance 를 같은 작업 트리에서 겹쳐 돌리면 provenance dirty_paths 가 오염된다 — 순차로.
