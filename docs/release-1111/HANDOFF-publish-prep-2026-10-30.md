# HANDOFF — cysr 1.1.11 발행 준비 (TICKET=cysr-1111-publish-prep · cysr-1111-c6-reap · 2026-10-30~31 · worker-rel surface:1752)

브리프 = `~/axdev/master/briefs/2026-10-30-cysr-1111-publish-prep.md` · 판정 = master#e9af822d · #1be35b1b · #8fd148bb · #10b2531d · #b45fa9ea · #75c7ef79.
정본 = 같은 폴더 `CHECKLIST-1.1.11-publish.md`(§G 증거 · §H 12커밋 · §I 게이트 · §J BACKLOG) · 초안 = `RELEASE-NOTES-1.1.11.draft.md` · `KAKAO-1111.draft.md`.

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
