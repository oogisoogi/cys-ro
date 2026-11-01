# HANDOFF — cysr 1.1.11 발행 준비 (TICKET=cysr-1111-publish-prep · cysr-1111-c6-reap · 2026-10-30~31 · worker-rel surface:1752)

브리프 = `~/axdev/master/briefs/2026-10-30-cysr-1111-publish-prep.md` · 판정 = master#e9af822d · #1be35b1b · #8fd148bb · #10b2531d · #b45fa9ea · #75c7ef79.
정본 = 같은 폴더 `CHECKLIST-1.1.11-publish.md`(§G 증거 · §H 12커밋 · §I 게이트 · §J BACKLOG · §K 태그 전 판정) · 초안 = `RELEASE-NOTES-1.1.11.draft.md` · `KAKAO-1111.draft.md`.

## 최신 상태(2026-11-01 · worker-relprep surface:1761 · TICKET=cysr-1111-relprep · cysr-1111-atomic-swap-fix) — 아래 옛 절보다 이 절이 우선

- **발행 = 11-07(토)**(master#6ac5d378) · 범위 = 현 1.1.11 + 수리 3 · 새 기능 0. ⛔seq 5 봉투 만료 11-06 22:14 KST 전에 재게시(master).
- 윈 r7 6회차 pack 소실 = `atomic_swap` 복사·삭제 폴백(1.1.10 과 같은 코드) → fix/1111-atomic-swap 1cc1a8fd · 이름 `pack.swap` 은 교체 중에만 있다. 겹침(rotate ②→④) = §J 1.1.12. ⚠윈 실제 잠금 시험은 CI windows-health 가 처음 돈다.
- **태그 머리 미정**: 「0fde41c6 고정」은 윈 r4 1번 실패(좌석 크롬 Job 안 · 재현 2/2)로 무효(master#c26704d3). 원격 rel/1.1.11 = 0fde41c6 · 태그 0.
- 0fde41c6 게이트 수치(대조 기준): 3런 41158073931 · 41158076438 · 41158078742 success · pre-tag rc 0 · 1-2b ANC-OK · phoenix 26/26 · CI 형식 cys 736/0 · 전체 = 체크리스트 §K · §K-8.
- **로컬 전용 문서 커밋**(0fde41c6 위): BACKLOG · §K · §K-8 · §K-9 · 노트 윈 크롬 1안 · 카톡 주석 · 이 HANDOFF. push = master 지시로만.
- 크롬 설계 교체(master#c110b17a · 박사님 11-01 「크롬은 권고대로 한다」): 설치·업데이트 때 미리 켜 두기 · 크롬 도구 = 본부 master 좌석만 · 57bce92e. 옛 C안·C+·윈 1안 = 이력.
- 병합 끝(master#415438c7): a431e8a3 = 57bce92e · c79011b9 = 90a372d2 · 로컬만. 다음 = master 가 push → dispatch 3런 → pre-tag · 1-2b · r7-0~7 · 맥 빌드 게이트 SEAL-3(§K-9) → 태그부터는 master/박사님 게이트. 워커는 대기.
- 미닫힘: r7 결과 표에 휴지통 줄 옮겨 적기(r4 15번 통과 승계 · §K-9) · r7-0~7(맥 = r7-4) · 맥 빌드 게이트 SEAL-3(§K-9) · 발행 뒤 첫 확인 = 4-1 핀 라이브 뒤 윈 노트북 공개 한 줄 설치 1회(공개 설치기 판 지정 없음 · §K-9) · 맨 `cargo test --bin cys` 넘침 060cb75b 0/2 ↔ 0fde41c6 2/2 원인 미상(발행 형식 밖 · §J) · release 스택 여유 미측정(§J) · 노트 자리 표시 = r7-2 기록 뒤.
- 닫힘: §K-1 감사 연장 = none(060cb75b..57bce92e · §K-9 · 코드 판독 · 내림 왕복 실측 0).
- 함정 추가: ⑦ `rel/**` 는 push 트리거 밖 → push 뒤 dispatch 필수(체크리스트 1-1) ⑧ 임시 트리를 `/private/tmp` 아래 두면 `dbg_r12…skill_links` 결정적 적·긴 TMPDIR 이면 SUN_LEN 7건 ⑨ a3 넘침은 단독·소묶음으로 재현 안 된다 → 비교는 맨 명령 전체(약 10분) ⑩ 맥에 `timeout` 없음 · 시험 줄과 `FAILED` 줄이 윈 로그에서 갈라져 찍혀 `... FAILED` grep 은 0 이 나온다.

## 끝난 것

| 항목 | 결과 |
|---|---|
| 머리 | 원격 c07cf341 · 로컬 +1(이 문서 · 체크리스트 c6·BACKLOG 줄 = 문서만) |
| 복구 1 | 공개 v1.1.10 12커밋 병합 6690f9a8(충돌 0) · 지표 16종 복귀 |
| 복구 2 | backlog-misc 130c8079 · fable-fixes dc9f1de7 · 고유 9커밋 조상 |
| 판번 빈칸 | `docs/index.html` 7줄(7ccab38c) |
| 로컬 게이트(dc9f1de7) | §I 전체 · lib 1133/0 · cys 736/0 · cysd 3222/0 · app 337/0 |
| CI | 7ccab38c windows-build 41066772814 success(r2 키트) · windows-health 41066777269 success · ci-branch 41066768654 진행 중 · c07cf341 = ci-branch 41075599499 · windows-build 41075604184 · windows-health 41075609134 진행 중 |
| c6 시험 | 67cd1370 · 직렬 13/13 |

## c6 판정

- line 147 적 = 원작자 Q7(`restored_queue`) 전제 ↔ 우리 D7⑵ 주차 → 시험을 `queue.parked`·`queue.inherited` 단언으로. 원작자 v0.14.52 원 시험 13/13 · 우리 원 시험 0/7.
- line 150 적 = 병렬 산물(병렬 두 묶음이 같은 초에 3회 · 직렬 13/13).
- line 168 적 = 1회뿐(line 147 을 빼기만 한 임시 사본 3회 중 1회) · 이후 재현 0(병렬 9회 · 직렬 13회). 주차 대기를 둔 수리 시험에서는 구조상 그 창을 지나지 않는다.
- ⚠미입증 후보: `state.rs:8362` 가 `exited` 를 세운 뒤 자식이 안 끝났으면 1초 자고 주차한다. 그 창에서 같은 역할을 잡으면 상속 0 → 주차분은 다음 claim 까지 남고 600초 뒤 `queue.dropped(parked_expired)`. 코드 판독만 있고 강제 재현 0 — 제품 결함으로 단정하지 않는다.
  재현안: 격리 데몬에서 자식이 SIGHUP 을 늦게 끝내는 좌석(trap) + 큐 1건 → `exited` 관측 즉시 같은 역할 new-surface → `queue.inherited` 유무.

## 남은 것 · 함정

1. ⛔태그 전: 최종 머리 CI 3종 녹 + `python3 scripts/pre-tag-ci-check.py <SHA> --wait 70`. 이번 7ccab38c 실행 = **rc 2(익명 API 한도 소진 · 판정 불가 ≠ 통과)** → 머리가 정해진 뒤 한 번만 · 한도 다른 시간대에.
2. 태그 전: 1-2b · 1-2c(phoenix 전건) · r3 키트 = 1754·1755 병합 뒤 master · 깨끗한 기기 · `--state-migration` 판정(§6 미판정) · 【발행 전 확인】 §8.
3. 함정: ① 게이트에서 cargo-app 준비(빈 사이드카)가 `target/debug/cys·cysd` 를 0바이트로 덮는다 → 그 뒤 phoenix 는 재빌드 필수(`rm` + `cargo build`). ② `cargo test --bin cys` 는 `--test-threads=1` 필수. ③ TMPDIR 을 홈 아래에 두면 `test_session_state_canon`·`test_intake_exit_contract` 거짓 적 · 기본 TMPDIR 이면 phoenix 3종이 별칭 거부 → 시험별로 갈라야 한다. ④ `test_hook_r34` = 고부하 시간 경계 플레이크. ⑤ `test_agora_known_authentic` = `CYS_AGORA_ZIP_DIR=~/axdev/ai-jarvis/site/install` 필요. ⑥ zsh 는 `$T:c` 를 수식자로 읽는다 · `echo ===` 실패 → 게이트는 bash 로.

## 재현

```
cd ~/cys-terminal-src-wt/rel-1111
cargo build --bin cys --bin cysd
CYS_PACK_DIR=<임시> python3 cysjavis-pack/bin/tests/test_phoenix_c6_reap.py
git merge-base --is-ancestor v1.1.10 HEAD && git merge-base --is-ancestor origin/main HEAD && echo ANC-OK
```
