# HANDOFF — TICKET=cysr-118-keyring (1.1.8 키링에 갱신 공개키 4종 기입 · R·U·F·A2)

좌석 = surface:1296(297) · cwd = ~/axdev/.wt/cys-118-keyring · 가지 `keys/keyring-118` off `6614cb7b`
브리프 = `~/axdev/master/briefs/2026-10-07-cysr-118-keyring.md` · 발주 master#3ee6fcf2(원장 일치 18:37) · 상한 1h
입력 = 공개키만(`~/axdev/master/keys-118/{r.pub,u.pub,f.key.pub}` · A2 = tauri.conf.json) · 개인키 접근 0 · 미러 push = `fix/keyring-118` 만 · 본 가지 병합 = master
전제 확인: U1 팩 용도 거르기 실재(`src/packsig.rs:113 pack_purpose_keyring` · 시험 `pack_keyring_excludes_update_purpose_keys`)

## TODO
- [ ] 1. HANDOFF-U3 §1 ② 스크립트 그대로 R·U·F 항목 생성 + A2 항목(purpose win-asset · pubkey = tauri.conf 값 그대로) · 기존 pack 키 2개 무변경
      해소 판정: `git diff -- cysjavis-pack/trusted-keys.json` = 4항목 추가만(기존 2항목 바이트 동일)
- [ ] 2. 검증 — key id 4종 서로 다름 · key_id = pubkey_key_id(pubkey) · 입력 파일 헤더 id 와 일치
      해소 판정: 대조 스크립트 출력 4행 OK
- [ ] 3. 시험 — packsig 단위 · update 모듈 전수 · `cys build-info --json` keyring_ids 4개 · 키링·release-verify 파이썬(test_a2_key_id_matches_tauri_conf) · 팩 용도 거르기 · secret-scan
      해소 판정: 각 명령 출력 수치
- [ ] 4. 커밋 → 미러 fix/keyring-118 push 1회 → 3런 success → 【확인요청】(diff · 수치 · key id 표)
      해소 판정: gh run list 3런 success
