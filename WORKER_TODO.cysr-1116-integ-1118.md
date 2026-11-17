# WORKER_TODO — TICKET=cysr-1116-integ-1118 (surface:2168 · 가지 integ/1116 ← 3a095c4e)

- [x] 0. 인계서 5개 §0 Read (vendor · backlog · slice1 · slice3 · slice4)
- [x] 1a. merge --no-ff integ/1116-vendor 1c4c07f6
- [x] 1b. merge --no-ff integ/1116-backlog 8bdd08ad
- [x] 1c. merge --no-ff feat/ui-slice3 43b44ea4
- [x] 1d. merge --no-ff feat/ui-slice4 fa400dda (충돌 6파일 두 쪽 살리기 · HANDOFF 표)
- [x] 2. 팩 해시표 --check · 1.1.15(3a095c4e) MASTER/CEO sha256 포함 여부 처분
- [ ] 3. 기준선 사본(3a095c4e · 임시 폴더 밖) + 전체 시험(lib·cys·cysd·seatkeep·tests·팩 py·bun·tsc·viewcore·화면 게이트·secret-scan)
- [ ] 4. 승인 창 경합 재측정(chat_gate G · 8점)
- [ ] 5. 📌 모음(1.1.16/1.1.17 후보 목록)
- [x] 6. 충돌 덩어리 codex 1R(있으면)
- [ ] 7. HANDOFF.cysr-1116-integ.md + 커밋 + 【확인요청】 push
- [x] 1e. merge --no-ff fix/cc-popover-z d8210ab4 (master#b9752e56)
- [x] 0b. 재시작 고아 cysd 11291·22128 + phoenix 13554 종료(master#e28c3581)
- [x] 1f. merge --no-ff fix/restart-confirm 7df374bc (master#eaa2b355)
