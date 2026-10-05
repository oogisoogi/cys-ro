# ★§0 델타 v2 (03:2x · CTX 약 59% = 매듭) — v1 이후: D13 b2374dc7(awaken status 레인 표기) 끝 · D23 triage(코드 무변경): release.yml 은 PACK_MIN_BINARY=1.1.7 로 `cys pack-manifest --min-binary-version` 을 넘기지만 `cys pack-manifest` 기본값은 `min_binary_version=""`(src/bin/cys.rs:30183 시험 핀 · :24041 기록) → 윈 디스크의 manifest 는 릴리스 산출이 아니라 **설치기/로컬 emit 이 인자 없이 만든 것**으로 추정(윈 실기: 그 파일의 생성 경로·mtime·`source` 필드 회신) · 맥 ~/.cys/pack 에는 pack-manifest.json 자체가 없음(실측) → 스큐 가드가 맥·윈 모두 이 파일에 기대지 않는지 Rust 쪽(w1) 확인 필요. 남은 일 = v1 §2 에서 D13·D23 뺀 나머지.

# HANDOFF — 1.1.8 W 결함 묶음 ② 팩 python·훅·부서 (TICKET=cysr-118-w2-pack · surface:1285 · 가지 w2/pack-118)

> 브리프 = master#64aeea16(10-06 02:26) + 추가 master#4888ba40(CI phoenix) · #b7b758e6(CI T9) · #8e8a26d6(D16 스윕 처방·D15=A) · #0565035e(CI create_progress) · #6757d42c(M5 코퍼스 모양) · #2a338f43(D3·D2·D13 이관).
> 원장 = `docs/merge/W2-LEDGER.md`(항목별 판정·파일·시험·소요). 갱신 2026-10-06 03:2x · 리드 CTX 약 58%(jsonl).

## §0 델타 v1 — 후임이 바로 이어 갈 것
1. **끝난 것(커밋 15 · off 3ea970bb · push 0)**: D14 fda3906f · D16 3e0e4977 · D15(python 반) 1c8dc7ce · CI phoenix_f1 6a6edce2 · CI T9 45123933 · D16-M2/M3 6f027a86 · J-📌7ⓐ 시험 · D21 f4b4d5d2 · D11-b 41ee2932 · D4/D9-b 307966cb · D16-M5 2cac92b1 · D16-M4 37d14221 · D3 ab2237ba · CI create_progress a4b79374 · D2 ef920829.
   master 쪽 문서 쓰기(저장소 밖): DECISION-TABLE-118 §0-7 K-W2a(CYS_DEPT_CAP 폐지 유지) · §0-8 K-W2b(D16 스윕 처방) · BACKLOG-118 D16-M7(1.1.9) · D16-M14(master 집행) 행.
2. **남은 일(브리프 §2 순서)**:
   - **D13**(awaken status 레인 명시 출력 · master#2a338f43 이관 · `bin/javis_awaken.py status` · 보고서 win-report §D13 L282) — 미착수.
   - **D9-b 나머지**: 훅 rc≠0 을 **파일에 남기기**(D15 출처 원칙 · 훅 오류 로그 없음이 윈 rc127 미판정의 원인) — 미착수. CYS_PY 해소 쪽은 307966cb 로 끝.
   - **D10+D9+D12 triage**(윈 훅 PATH 상속 · core_inject rc127 · C82) — 미착수 · 실측 불가분은 윈 실기 문안으로.
   - **D6**(지침 주입 제출 확인 길이 무관 / 파일+짧은 지시) — 미착수 · 주입 경로가 Rust(데몬)인지 먼저 확인(팩 몫이면 javis_phoenix·cycle_autopilot 쪽).
   - **D8+D7**(부서 부트 completed_degraded + preflight 판정 보고 + FAIL 행 절단 제외) — 미착수(javis_bootstrap / cys-dept 부트 보고).
   - **D18**(틱 경로 윈 핸들 WinError 6 · javis_dept_request 닫기 틱) — 미착수.
   - **D23 triage**(윈 manifest min_binary_version 빈 값 · release.yml) — 미착수.
   - **끝 = 팩 163(+신규 시험) 격리 재측정 → 【확인요청】**.
3. **범위 밖이라 보고만 할 것(결정필요 묶음)**: D15 Rust 반(= w1 이관 결정 A · 키 규칙 정본 = 1c8dc7ce `javis_mission._anomaly_key`·필드 ts/surface/prompt_sha) · D16-M5 Rust 사본(285 · 할 일 7개 = 03:15 인박스) · D19-b(doctor tombstone = src/bin/cys.rs:9020) · D11-b Rust 몫(cys.rs:10205 옛 「v0.14.30 재설치」 문구 · doctor FAIL↔preflight WARN 등급) · D26(MSYS 경로 변환 — 팩 래퍼 없음 · 전역 MSYS_NO_PATHCONV 는 정당한 변환까지 끔 → cys send 쪽(Rust) 복원 권고) · W-b(bootstrap.ps1 이 이 저장소에 없음 — 위치 질의) · AU-📌14(부서장 전용 지침 파일 없음 = MASTER_DIRECTIVE/CEO_TEMPLATE 몫 · bulk/publish 칸 코드 미구현) · create_progress 서브가 찾은 제품 의심 2(예약 유예 25초 < boot_wait 120초 → 중복 데몬 창 · launch 실패 줄 stderr 부재).
4. **측정 함정(이 세션 실측)**:
   - 격리 래퍼 = `/private/tmp/claude-501/s118/w2/isoenv.sh`(짧은 HOME/TMPDIR t2) · 팩 시험기 = `.../w2/packtests.py <WT> <목록파일> -<태그>` · 바이너리 = `~/axdev/.wt/cys-118-merge/target/debug/{cys,cysd}`(같은 커밋 3ea970bb 빌드 · 이 작업트리 target 없음).
   - ★**래퍼의 CYS_CYS_BIN·CYS_CYSD_BIN·CYS_NO_AUTOSTART 덮어쓰기가 test_dept_team_token 을 17 FAIL 로 만든다**(원작자 「소켓 미기동」 분류의 실체) — `env -u` 셋 빼면 23/23. create_progress 도 깨끗한 env(`env -i PATH=… HOME=<짧은> TMPDIR=<짧은>`)에서 재야 한다.
   - 기준판(3ea970bb · 스크래치 작업트리 `/private/tmp/claude-501/s118/w2/base`) 팩 전체 = 163 중 14 적색: 환경 8 + 원작자 4(dept_create_progress·name_guard·team_token·session_start_hook 18e) + **test_dbg_d3_d11_shared_profile_hooks · test_hook_r34**(이 래퍼에서 적색 · 원인 미조사).
   - 고아 디버그 데몬: 측정 뒤 `pgrep -f cys-118-merge/target/debug/cysd` 중 `HOME=/private/tmp/claude-501/s118/w2` 만 kill(이번 세션 0건).
5. **윈 실기 문안(【확인요청】에 실을 것)**: D14(재시작 뒤 master 좌석 SESSION_STATE 출처 = 팩 round · 옛 install-jarvis/_round 기록이 정본으로 1회 복사되는가) · D21(묘비 부서 `cys-dept dept-1 -- cys list` → cysd 프로세스 0) · D11-b(`cys doctor` runtime-seal = OK 또는 「런타임 관리 N건」 · **전수 추가 6/누락 5 목록 회신** — 좁은 이름 집합이 맞는지) · D4/D9-b(`cys-dept list` 가 python3 없는/Store 별칭 기계에서 성공) · D3(`javis_resource_gate.py check` nodes = 본부+부서 좌석 · depts active≥1) · D2(report_gate 사유 = not_applicable:windows · ack 배지 INFO).
6. 서브 규율: Bash 에 rm·sh -c 금지 · git 쓰기 금지(리드만 커밋) · 같은 파일 두 서브 금지.
