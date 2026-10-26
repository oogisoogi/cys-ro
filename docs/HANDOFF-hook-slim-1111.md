# HANDOFF — hook-slim-1111 (1.1.11 · worker-2 677)

정본 설계·실측 = `docs/DESIGN-hook-slim-1111.md` · 윈 의뢰 = `docs/hook-slim-1111-win-measure-request.md` · 원작자 요약 = `docs/hook-slim-1111-author-summary.md`.

## 끝난 것
- 등록 조건 A(옵트인 표지) — Rust 4경로(데몬 기동·init-pack·doctor --fix·개인 프로필 병합) + 파이썬 `resolve_registration_targets` 같은 술어.
- 개인 프로필 팩 등록 제거(사용자 훅·다른 키 바이트 보존 · BOM/CRLF · 읽기 전용 존중 · 시각 붙은 사전 백업) — 제거 엔진 순서 보존 개편.
- B1 좌석 아닌 세션 즉시 탈출(팩 훅 11개) · Stop 관측 훅 분리 실행 · 선언 timeout 14행.
- 시험: Rust `hookslim` 9 · `test_hook_slim.py`(S1~S11·PF·FX·GT·DT) · 기존 검체 개정(아래) · 뮤턴트 `scripts/hookslim_mutants.py`.

## 시험 개정(계약이 바뀐 곳 — 리뷰 때 확인할 것)
- `run_bootstrap_health.py`: H-EXIT-8(신규 머신 폴백 = 표지 없음이면 계정 config) · `_HOOK_SEAT` 신설(좌석 본문을 재는 검체 10개 + `_a1_mock_env` 에만
  좌석 env 명시 — `_base_env` 의 「좌석 env 지움」 계약은 그대로) · H-WIN-2·G-PRELUDE 에 `CYS_HOOK_STOP_SYNC=1`(본문 동기 측정).
- `test_inject_context_role_seat.py` 11a/11b: 「신원·env 없는 세션 = 중립 문안 + 본부 작업기억(복원 생명선)」 → 「주입 0」(B1).
- `test_session_state_canon.py`·`test_inject_context_soul_l0.py`·`test_pack_guard_hooks_guidance.py`·`hooks/test_pre_dispatch.sh`: 좌석 env/동기 노브 명시.

## 함정
- 팩이 임시 폴더 아래면 preflight 는 등록을 통째로 끈다(`_path_under_tempdir`) — 「재부착 0」 시험은 HOME 을 임시 폴더 **밖**(`<repo>/target`)에 둬야
  의미가 있다(첫 판 PF 가 그래서 공허했다).
- `test_hook_r34` 의 시한 검체(RCF-3·RCF-4a·NZ-3·DL-1b)는 부하(load 4~6)에서 기준 커밋도 3회 중 2회 적색 — 기존 흔들림.
- 기준 커밋에서도 적색인 검진 4건: H-SECRET-1·H-WIN-16·H-CLT-1·H-CLT-2(환경·기존).
- commit-memory-nudge 는 Bash 본문에 `git commit` 문자열만 있어도 오발화한다(이 티켓 중 3회) — 별건.

## 1.1.12 BACKLOG
- **B2(master 02da1acc 지시)**: 원 계정 좌석(CLAUDE_CONFIG_DIR 없이 `~/.claude` 로 뜨는 좌석 · 우리 맥 14일 156세션)을 띄울 때 좌석 settings
  (`claude --settings ~/.cys/seat-settings/<역할>.json` — 이미 좌석 기동 줄에 붙어 있다 · 쓰는 곳 `lib.rs claude_seat_settings`)에 팩 훅을 싣고
  `~/.claude` 는 **완전 무팩**으로. 그러면 우리 맥도 표지가 필요 없다. 선행 검증: ① `--settings` 층의 hooks 가 프로필 settings 의 hooks 와 **합쳐지는지·
  같은 명령이 중복 발화하는지**(Claude Code 버전별 실측) ② launch-agent·restore·schedule·boot 5경로가 전부 그 파일을 붙이는지 ③ 좌석 프로필
  (`~/.cys/claude`)과 겹칠 때 중복 0.
- commit-memory-nudge 오탐(문자열 일치 → 실제 git commit 실행 판정).
- 1,059초 사례 원인 재추적(전원 로그가 남는 기간에 재발 시 `pmset -g log` 대조).

## 재현
```
cargo build --bin cys --bin cysd
cargo test --lib hookslim
python3 cysjavis-pack/bin/tests/test_hook_slim.py --diff-out /tmp/hookslim_diffs.md
python3 cysjavis-pack/bin/tests/run_bootstrap_health.py
python3 scripts/hookslim_mutants.py --rust
python3 -I scripts/bench_pack_hooks.py --pack cysjavis-pack --transcript <기록.jsonl> --out r.json --n 20 [--scenario seat --round]
```
