# worker-3 TODO — TICKET=cysr-test-gatekeeper-crash-1118 (브리프 원장 master#cf6b2e31 15:41:44 · surface:2215)
cwd = /Users/oogisoogi/axdev/.wt/cys-1116-gkfix · 가지 fix/test-gatekeeper-crash ← fd9f0cc7
⛔ 시험 실행 금지(빌드 --no-run 1회만) · push 금지

- [x] 1. 방아쇠 시험 audit_code_path_matches_security_framework 고침(ⓐ fake ips 0 ⓑ syspolicyd 0 ⓒ 매번 만들고 지우기 없음)
- [x] 2. 형제 스윕(src·scripts/tests·cysjavis-pack/bin/tests·ui) 목록
- [x] 3. 제품 경로 점검(업데이터·seatkeep·sec::code_path_of_pid) 읽기만
- [x] 4. 반복 실행 규칙 문서화
- [x] 5. 깊이: 11-12·13·16 syspolicyd 충돌 대조(reflog·셸 기록)
- [ ] 6. --no-run 빌드 1회 · 커밋 · 【확인요청】
- [x] 6a. --no-run 빌드 rc 0 · 커밋 5f2a60e1
- [x] 7. 【결정필요】 형제 SAME 4곳 같은 처방 착수 여부 = master 답 대기
## 2차 (master#525cdee3 15:54:30 · 상한 +90분)
- [x] A. native_publication_transition_tests.rs 고정 자리 빌드
- [x] B. realops.rs fake_cysd_bin 고정 자리
- [x] C. tests/rotate_autorestore_hold.rs (cc 가짜 claude · cys/cysd 복사 · owner cc 2개)
- [x] D. tests/update_drainhold_e2e.rs cc 가짜 claude
- [x] E. 조건부 3곳(test_update_publish · parity_todo_decl · parity_todo_scan)
- [x] F. 문서 주의 2곳(installer-atomic-demo spctl · gktool scan) 수동·VM 전용 1줄
- [x] G. --no-run 빌드(lib·bin cysd·통합) 각 1회 · 커밋 · 【확인요청 2】
## 3차·4차
- [x] 3ba23763 임시 원문 .c (master#db2ad12f)
- [x] 37943fe1 rah-bin 바이트 비교 + 하드 링크 (master#52c34a03) · 【확인요청 4】 16:58:48
- [x] build.rs A 채택(master#c40b4251) · 5d5e7979 · 【확인요청 5】
- [x] build.rs 문서 줄 자리 정리 fc7c16a0 · HANDOFF · 【완료】
