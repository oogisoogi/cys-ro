# HANDOFF — TICKET=cysr-1111-drainhold

가지 fix/1111-update-drain-hold · 기준 7ccab38c · 코드 머리 = 고침 1회 커밋 · 1차 수용 = master#a95a6294

## 끝난 것

- S4를 S3 앞으로 · S3 기준 토큰 꼬리 출력 정착 · 저장 뒤 새 좌석 보류 · S10 rc 25 = 성공 + `restore_partial` · V3 rc 표(rc 25 = 자리·좌석 수 대조).
- 끝-끝 시험 `tests/update_drainhold_e2e.rs`(맥 전용) · 회귀 전부 실패 0 · 윈 교차 타입체크 오류 0 · codex 1R 처분 완료.
- 근거 문서: `DESIGN-drainhold.md`(재현·러너 판정·구제 표·설계 비교·rc 표·남은 위험) · `CODEX-R1-drainhold.md`.

## master 처분 (master#a95a6294)

1. rc 25 + 자리 소실 = 롤백 유지.
2. V3 세션 대조 = 지금 완화하지 않음. 발행 전 실기 1회(살아 있는 실제 Claude 좌석이 S11까지)가 게이트. 코드상 세션 id 전후 동일성은 독립 확인 좌석이 먼저 추적.
3. 공개 문안 = A안(master 초안 · 박사님 확인).

## 고침 1회 (master#a9c54875)

1757 결함: 새 데몬이 등록 세션을 물려받지 않아 rc 0의 V3 1회 측정이 `claude|`(빈 세션)를 읽고 롤백. 수리 = `settled_seats`(세션만 빈 동안 60초까지 대기) · `verify::seat_match` · 상한 초과 = 자리 대조 + `state.json.session_unverified` · 채워졌는데 다름 = 실패. 가짜 좌석 = `tests/fixtures/fake_claude.c`(1757 대역 이식 + `FAKE_NEW_SID`). 실 rotate 시나리오 3개는 `tests/update_drainhold_e2e.rs`. 대본이 rc 25를 0으로 접으므로, 실제 rc 0 경합 재현은 `cys.rs` 복원 앞 임시 sleep 패치로 했다(커밋 안 함).

CI 등재(D4) = `ci-branch.yml` macos-rust-pack 의 `cargo test --test update_drainhold_e2e` 스텝(A10 대로 릴리스 레인은 1사이클 green 뒤 승격). 설계서 D8·D9 정정. D2·D5~D7 = 1.1.12. D3 = 판정만(코드 무변경).

## 미완 · 다음

- 대기: surface:1757 worker-drainverify 독립 확인(detached cac0c17b · codex 2R 포함). FINDINGS가 오면 **고침 1회**.
- 병합은 master 몫. rel/1.1.11이 앞서가 있으며 겹치는 파일 = `src/bin/cys.rs` 1줄 · `src/update/` 5개.
- push·태그·공개 문안 확정 = master 게이트.

## 함정

- `cargo`는 PATH에 없다: `export PATH="$HOME/.cargo/bin:$PATH"`. `CARGO_TARGET_DIR`은 이 작업 폴더의 `target`.
- `cargo test -p cys-app`은 CI 스텁이 있어야 빌드된다(`.github/workflows/ci-branch.yml` 「GUI env 대칭 핀」 스텝 · `--bins`).
- `lane-parity-rehearsal.sh`는 `bash`로 돌린다.
- `review-prompt` 산출물의 `cys send` 회신 줄은 codex 의뢰 전에 지운다(읽기 전용 샌드박스에서 cysd 자동기동을 시도한다).
- 끝-끝 시험의 교체·정지·스냅샷·S11은 대역이다.
- 끝-끝 시험은 시험마다 프로세스 env를 바꾸므로 `SERIAL`로 한 줄로 선다. 상한 초과 시나리오는 실제 60초를 기다린다.
- `cargo test`는 `CYS_*` 전체를 지운 env로 돌린다(`CYS_SURFACE_ID`·`CYS_ROLE`만 지운 1회에서 lock 시험 1건 실패 관측 · 원인 미확정).

## 재현

```bash
export PATH="$HOME/.cargo/bin:$PATH" CARGO_TARGET_DIR="$PWD/target"
env -u CYS_SURFACE_ID -u CYS_ROLE cargo test --test update_drainhold_e2e -- --nocapture
env -u CYS_SURFACE_ID -u CYS_ROLE cargo test --lib update::
```
