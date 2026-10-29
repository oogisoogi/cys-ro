# HANDOFF — TICKET=cys-ctx-home-ancestor (1.1.11 · 2026-10-30)

브랜치 `fix/1111-ctx-home-ancestor` ← int/1111 `fec48a8a`. 좌석 surface:1722(723 · worker-3).
커밋 `c805cfdc`(수리) · `c12b49f9`(codex 1R REVISE 반영) — origin push = master(c12b49f9) · int/1111 병합 = 1.1.11 묶음 때 master.

## 1. 무엇이 바뀌었나

| 항목 | 종전 | 지금 | 자리 |
|---|---|---|---|
| 작업기억 상향탐색(셸) | cwd 에서 `/` 까지 올라가 첫 `_round/SESSION_STATE.md` 를 실음 → `$HOME/_round`(본부 좌석 기억)가 `_round` 없는 모든 $HOME 아래 세션에 실림 | cwd ≠ 루트일 때 루트(`$HOME`·`$ROOT`=`CYS_ROOT`)에 닿으면 중단 · 루트 기억은 cwd == 루트일 때만 | `cysjavis-pack/hooks/inject-context.sh` L2 · 키 `_ic_pkey` |
| 옛 자리 후보(python 쌍둥이 · master adopt) | 같은 탐색 → master 가 다른 프로젝트 cwd 면 본부 기억을 팩 round/ 정본으로 **복사**(영속 오염) | 같은 경계 | `cysjavis-pack/bin/javis_session.py` `root_key` · `legacy_candidates` |
| 경로 키 | (없음) | Windows(MSYS cygpath 실재 · python nt)만 `\`→`/` · `/d/…`→`d:/…` · 대소문자 무시 / POSIX 는 꼬리 `/` 만 제거 · 대소문자 보존 | 위 두 곳 |
| 시험 | — | 신규 `test_inject_context_home_ancestor.py` 22건 · CI 목록 5곳(ci-branch ×2 · release ×2 · pack-release ×1) | `cysjavis-pack/bin/tests/` · `.github/workflows/` |

유지(손실 0): 본부 좌석 cwd==$HOME · 루트 아래 프로젝트 `_round`(하위 폴더 상향 발견 포함) · 루트 밖 cwd · ACTIVE_PROJECT 폴백 · 부서 레인 · master 정본 경로.
손실: `$HOME/_round` 를 $HOME 아래 모든 프로젝트 공용 기억으로 의도해 쓰던 경우 → 그 프로젝트에선 「미발견」(대체 = ACTIVE_PROJECT 또는 프로젝트 `_round`).

## 2. 검증

- 신규 22/22 · 뮤턴트 4/4 적색(셸 경계 5 FAIL · py 경계 2 · py 키 1 · 셸 키 1).
- 관련 회귀 10종 + `javis_session --self-test` 초록.
- codex 1R REVISE(py 키 `/d/CYS`≠`D:/CYS` · 셸 키 POSIX 대소문자 충돌) → 2R ACCEPT.
- 「주입 2회」 = `~/.claude/settings.json` SessionStart 가 래퍼 `cmux-inject-context.sh`(끝에서 팩 훅 재실행) + 팩 훅 직접을 둘 다 등록 → 직접 항목 제거는 master 집행 완료(10-30).

## 3. 남은 것

- **Windows 실기 미검증 1** — 경로 키는 단위 시험(K1·K1b·P4)만. 윈 Git Bash 에서 cwd `C:/Users/<u>/proj`(자기 `_round` 없음) · HOME `/c/Users/<u>` 로 훅을 돌려 `~/_round` 본문이 안 실리는지 1회 확인 필요.
