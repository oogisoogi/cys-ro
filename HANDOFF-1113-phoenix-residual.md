# HANDOFF — TICKET=cysr-1113-phoenix-residual (worker-phoenix · surface:1826 · 2026-11-06)

브리프 = `~/axdev/master/briefs/2026-11-06-cysr-1113-phoenix-residual.md`(원장 11930 · spawn 경로) · TODO = `~/.cys/pack/round/WORKER_PHOENIX_TODO.md`

## §0 지금 상태
- 가지 `fix/1113-phoenix-residual`(← 2ae7542a) · push 됨 · 머리 = 19f9c01b.
  - 06039cef 진단 줄(residual_diag) + ci-branch `phoenix-host-gate` 잡 + 레인 대조 ALLOWED `test_phoenix_` = {ci-branch, release}
  - a4eab473 원인 수리 + 시험 `test_phoenix_harness_sockpath.py`
  - c4338c70 판번 1.1.12 → 1.1.13(8곳 · Cargo.lock = `cargo update -w --offline` · docs/index.html · version-check 녹)
  - eb8d03e9 codex R1 REVISE 반영(진단은 경계가 거부한 소켓 무접촉 + 바이트 경계 시험) → codex R2 ACCEPT
  - 19f9c01b ★자기 회귀 수리: a4eab473 의 길이 거부가 소유 경계 `_harness_paths` 안에 있어 teardown 이 제 데몬을 pid 로도 못 끝냄
    (CI 42143954966 boot-health-full H-PY-PKILL-2 적 · 로컬 재현) → 전송 `_harness_rpc` 로 이동 · 판정 불변 · 뮤턴트 M7·M8 적발 → codex R3(델타) ACCEPT · issues 0
- CI(eb8d03e9): phoenix-host-gate 녹 · windows-build 녹 · windows-health 녹 · ci-branch 적 2잡 = H-PY-PKILL-2(위 수리) +
  macos-rust-pack `d7_prime_seat_cache_never_overwrites_a_tick_value` 「측정 전제 실패」(알려진 5초 플레이크 ·
  docs/release-1111/CHECKLIST-1.1.11-publish.md:551 · src/ 무변경).
- ★CI(19f9c01b · 1회차 · 재실행 0): ci-branch 42151681125 녹(phoenix-host-gate·boot-health-full·macos-rust-pack·ubuntu-pack-suite·ui-check·nsis-hook-harness 전 잡) · windows-build 42151681175 녹 · windows-health 42151681107 녹.
- 태그·rel/1.1.11 push·릴리스 = 손대지 않음 · master 수용([master#a0fe0340] 11-06 13:01) · 태그 v1.1.13 = 발행 후임 relprep3 조건부 사전 승인.

## §1 원인(확정)
- 러너 재현(06039cef · ci-branch 런 42143301492 · phoenix-host-gate 잡 127648638181) 진단 줄 원문 요지:
  `connect: OSError errno=None AF_UNIX path too long` · `sock.bytes 111 > max 103` · `pgrep -x cysd rc=1(없음)` · `unobserved_owned=["endpoint_unobserved"]`.
- 경로: release.yml 1.1.12 수리 `export TMPDIR="$(cd "${TMPDIR:-/tmp}" && pwd -P)"` → `/private/var/folders/<2>/<28>/T` →
  하네스 홈 `…/phoenix-harn-home-XXXXXXXX/.cys/state-harness/cys.sock` = 111바이트 > macOS sun_path 104(NUL 포함).
  별칭 그대로면 103바이트(겨우 들어감)였지만 그건 aliased_harness_root 로 거부 — 둘 중 어느 쪽이든 붉었다.
- 가설 a(c6_reap 잔여 cysd)·b(lsof 실패) = 러너 실측으로 기각.

## §2 환경 축 표(로컬 녹 vs 러너 적)
| 축 | 로컬(종전 27/27 녹) | 러너 태그 런 |
|---|---|---|
| TMPDIR | relprep 재현 = `/var/tmp/…`(짧음) 또는 셸 기본 | `/private/var/folders/<2>/<28>/T`(정규화 뒤) |
| 소켓 경로 길이 | ≤ 103 | 111 |
| 결과 | connect ENOENT → ping=False → clean | OSError(경로 길이) → endpoint_unobserved → FATAL |
| 잔여 cysd | — | 없음(pgrep rc 1) |

## §3 함정
- 하네스는 import 때 `mkdtemp(prefix="phoenix-harn-home-")` 를 만들고 지우지 않는다(종전부터) — 로컬 `$TMPDIR` 에 수십 개 쌓여 있음. 이 티켓 범위 밖 → §4 「1.1.14 후보」.
- `teardown()` 의 `_note_harness_children()` 는 try 밖이라 `_harness_paths` 거부가 트레이스백으로 샌다(종전부터 · aliased 때도 동일) — 그래서 길이 거부는 guard_isolation 에서 먼저 깔끔히 멈춘다.
- ci-branch 잡은 release 스텝의 phoenix 글롭 부분만 문면 그대로 옮겼다 — 두 블록을 같이 고칠 것.
- ★`_harness_paths` = **소유 정리 경계**(teardown·_capture_owned) — 접속 가능성(소켓 길이 등) 검사를 여기에 넣으면 정리가 막혀 프로세스가 샌다. 전송 검사는 `_harness_rpc` 에.
- 로컬 `run_bootstrap_health.py` 전체 = H-CLT-1·2 적(기저 2ae7542a 에서도 동일 · cys.app 안 호스트 한정 · CI 녹) — 이 티켓 무관.

## §4 이월
- 1.1.12 계획(reports/2026-11-02-cysr-1112-plan.md 1단계 가지들 inject-slim · skill-fold · native-research · mouse · rc-all-seats · asset-skills)은 판번이 **1.1.14** 로 밀린다(이 좌석 범위 밖).
- **1.1.14 후보**: 하네스가 스스로 만든 mkdtemp 홈(`phoenix-harn-home-*` · `$TMPDIR` 또는 정규 `/tmp`)을 종료 때 지우지 않아 잔해가 쌓인다 — 자기가 만든 홈만(명시 `PHOENIX_HARNESS_HOME` 은 제외) 정리 성공 뒤 지우는 수리 + 잔해 0 시험. 남의 잔해는 무접촉.
