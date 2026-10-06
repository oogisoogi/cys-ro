# TODO-U2 — TICKET=cysr-118-u2-runner (브리프 [master#71f53d34] · 착수 2026-10-06 20:3x)
설계 정본 = ~/axdev/master/reports/cysr-118-plan/DESIGN-AUTOUPDATE-118.md · 가지 u2/runner-118 off e2515bb0
상한: 코드 쓰기 몫 6h · 매 2h 【진행】 · VM·실기 = 문안만 · push 0(미러 fix/u2-runner-118 = CI 전용 허락)

- [x] 0. 실측: 이 맥 상태 폴더(~/.local/state/cys · ~/.cys) 목록·크기 → EXCLUDE 근거·제외 뒤 크기(읽기 전용)
- [x] 1. §3-1 러너: 틱 진입(N1~N14 소비) · 맥 Survivor · 윈 작업 스케줄러(COM+SDDL) · publish:true 잡 보류 · 러너 사본 · 지터
- [x] 2. §3-3 정비 모드 RPC(update.quiesce/release) · 보류 로그 소비(정확히 한 번 · ACK 재독 · B8 crash 행렬) · hold_ingested 원자 이관 · delivering · rotate --stop-only/--skip-drain --txn
- [x] 3. §3-5 스냅샷 「전체 − 제외」 · MANIFEST 검증 · 파일 단위 복원 · 격리 · 세대 2 · N7 공간식
- [x] 4. §3-6 맥 교체: macupdate 이동 · RENAME_SWAP 실물 판정 · DR 핀(이관 문법) · prev_bundle
- [x] 5. §3-7 윈 교체: run_installer_wait · CREATE_SUSPENDED · S9b 전수(payload-exclude 공유) · 신판 전용 삭제 · 본문·설치기 보존 · 뮤텍스 · --verify-payload
- [x] 6. §3-9 V1~V9 · §3-10 RB 하위 상태·installed_revoked · §3-11 복구기(N14)·부팅 가드·저널 손상 재구성·PACK_APPLY/ROLLBACK · 내장 잡
- [x] 7. install_id 운영 생성 배선 · §3-12 last_result + counsel/updates.jsonl
- [ ] 8. 시험: 단위 · 강제 종료 행렬 · 격리 env · 뮤테이션 4축 · Rust 3묶음+cys-app · VM M1~M3 문안 · 윈 W1~W4 요청문
- [ ] 9. 커밋 묶음 · HANDOFF-U2.md · 【확인요청】
  (6 중 installed_revoked ② 자동 롤백 = 미구현 · HANDOFF-U2 §5 ⓐ)
