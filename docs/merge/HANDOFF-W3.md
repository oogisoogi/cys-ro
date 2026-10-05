# ★§0 델타 v1 (05:4x · 290 · TICKET=cysr-118-w3-cysd) — W3 후임 입력(가지 w3/cysd-118 off e49151a6)

1. **끝난 것(커밋 1)**: db1e6cf3 — cysd CI 적색 4건(run 37362054744 · job 111938771690 · 0c67af06) = 시험 하네스 경합 수리. master 판정 = 수용(master#36bf398b) · merge/v0.14.43 cherry-pick 완료(master 집행). 범위 판단(잠복 동형 28 함께 차단)도 수용.
2. **남은 것**: 없음 — CI 최종 판정 대기(master 가 push 1회 · macOS 러너 용량 부족으로 취소·지연 중 = 우리 결함 아님). CI 초록 뒤 master 【종결】.
3. **함정**: ① 로컬 평 프로파일에선 재현 안 됨(그래서 「로컬 초록」) — 아래 재현법을 써라 ② v116 실패는 연쇄(u8 패닉 → `ACL_ENV_LOCK` 오염 → v116 의 `.lock().unwrap()` PoisonError) · 단독 = 초록 · into_inner 1줄 전환은 master 판정으로 보류(외과 원칙) ③ 빈 셸 가드는 4군 ①(폭주 큐) 방지 장치 — 시험을 맞추려고 가드를 약화하지 마라 ④ 지침 3파일·실 팩·push 금지 그대로.

## 원인(파일:줄)
- 시험 좌석 = `$SHELL -lc 'sleep 30'`(`src/bin/cysd/state.rs` `create_surface` · macOS = `-lc`).
- 로그인 프로파일이 도는 찰나엔 뿌리 = 셸 · 자식 0 → `governance.rs:4021` `agent_seat_vacant_now` 참 → `handlers.rs:6240` 빈 셸 가드(`no_agent` · 큐 보류 prompt_unknown)가 typing/모달 가드보다 먼저 응답.
- 러너 프로파일이 무거워 창이 넓다. 4 시험·가드 코드는 5913f9fa..HEAD 무변경(W1 무관). 0c67af06 run 이 이 가지에서 cysd 스텝에 처음 도달한 run 이라 W1 뒤에 처음 보였다.
- 가드 판정 자체는 정확하다(관측 시점에 에이전트 대역 프로세스가 아직 없다) → 수리는 시험 전제(「산 sleep 30 좌석」)를 참으로 만드는 쪽.

## 재현법(로컬 100%)
```bash
S=<scratch>; mkdir -p $S/home-slow
printf '%s\n' 'i=0; while [ $i -lt 40000 ]; do i=$((i+1)); done' > $S/home-slow/.zprofile   # bash 면 .bash_profile
cargo test --bin cysd --no-run          # 바이너리 = target/debug/deps/cysd-<hash>
env -i HOME=$S/home-slow PATH=/usr/bin:/bin:/usr/sbin:/sbin SHELL=/bin/zsh CI=true \
  CYS_PACK_DIR=$(mktemp -d) target/debug/deps/cysd-<hash> --test-threads=1 \
  --skip hwmon::tests::snapshot_has_all_sections
```
- 프로파일 루프 ≈80ms(셸 내장만 → 자식 0 = 빈 좌석 창). zsh·bash 둘 다 CI 와 같은 4건 · 같은 단언 · 같은 줄(handlers 16977 `no_agent≠typing_guard` ×2 · 20768 PoisonError · return_absorb 1200).
- 전체 스위트로 돌리면 잠복 동형 전수 = 32건(전부 no_agent/빈 셸 보류).
- ⚠zsh 에서 시험 이름 여러 개를 변수로 넘길 땐 배열(`T=(a b c)` · `$T`) — 문자열 변수는 단어 분리가 안 돼 0건 필터된다.

## 수리(db1e6cf3 · 시험 코드만 · 15줄)
원작자 v115-ci-flake 선례(12곳)와 같은 `crate::governance::test_wait_seat_runs(&s, "sleep", &["30"])` 를 공용 픽스처 5자리에:
- `handlers.rs` `v7_pane` · `c_ceo_injection_sanitized_before_ledger`
- `return_absorb_tests.rs` `pane` · `send_settle_tests.rs` `pane`
- `schedule.rs` `deliver_push_branches_are_observable`
삭제·skip·ignore 0 · 제품 코드 0줄.

## 검증(격리 env · CI 플래그 동일)
| 측정 | 전 | 후 |
|---|---|---|
| 느린 프로파일 전체 | 2427/32 | 2459/0 |
| 평 격리 전체 | — | 2459/0 |
| 4건 ×3(느린 zsh·bash · 평) | 적색 | 전부 초록 |

환경 3(census·hwmon·b6_lsof)은 이 격리 측정에서 적색 아님(hwmon snapshot 은 CI 처럼 skip). CI 가 최종 판정자(러너 프로파일 그대로는 로컬 재현 불가 · 느린 조건은 상한 모형).

## T3-3 메모(윈 CI · BACKLOG 1.1.9 후보 · 이 티켓 범위 밖)
- 같은 가드 · 다른 촉발. `launch-agent` 는 셸 pane 에 에이전트 명령을 **타이핑**한다 → 스텁(PowerShell `Read-Host` 루프)이 뿌리 셸 안에서 돌아 자식 프로세스가 영영 없다 → **상시** vacant → `CCDPROBE` 가 `no_agent` 로 큐 보류 → 화면에 `CCDFRESH=` 없음(0c67af06·b71a43ce·e49151a6 비크리티컬 FAIL).
- 확신 Med(코드 판독 · 윈 실측 없음). 가드 판정은 정의대로 정확(등록 에이전트인데 프로세스 0) → 가드 약화 금지.
- 처방 후보 = 하네스 쪽(`windows-build.yml` T3-3 블록 안 · 그 블록의 「금지선」 주석 준수)에서 스텁을 자식 프로세스로 띄우기(예: `powershell -NoProfile -Command <루프>`).

## 증류
- `reference_cysd-test-seat-login-shell-race-repro`(재현법·수리·T3-3 구분).
