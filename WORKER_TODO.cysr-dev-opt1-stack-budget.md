# WORKER_TODO — TICKET=cysr-dev-opt1-stack-budget (worker-3 · surface:2014)
발주 = master [master#dd7821a1] 2026-11-12 08:33 · 가지 fix/1115-dev-opt1-stack-budget ← 270e3e21 · 상한 10:03

- [x] 0. 작업 폴더(~/axdev/.wt/cys-dev-opt1-budget) · 기준선 폴더(scratchpad wt-base · 270e3e21)
- [x] 1. A: Cargo.toml [profile.dev.package.cys-terminal] opt-level = 1
- [x] 1b. debug-assertions·overflow-checks 켜짐 확인 1줄
- [x] 2. D: cli_stack_budget_tests(상시 · macOS · ≤ 1 MiB)
- [x] 3. HANDOFF: 기존 우회 목록(지우지 않음) · B 구조 해법 1절
- [x] 4a. 시험 opt1: --bin cys · --bin cysd · --lib 전체 각 1회
- [x] 4b. 기준선 270e3e21: 같은 3종 · 실패 이름 대조
- [x] 4c. 부하 재현 150회 0 넘침
- [x] 4d. 뮤턴트 2(opt-level 줄 제거 → 붉음 · 예산 100 KB → 붉음)
- [x] 5. 디버그 깨끗한 빌드 시간 전후
- [x] 6. 커밋 + 인박스 【확인요청】
