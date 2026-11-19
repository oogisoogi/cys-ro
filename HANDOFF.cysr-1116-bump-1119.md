# HANDOFF — cysr-1116-bump-1119 (판 올림 1.1.16 + ui-test 고침)

- 브리프 = `~/axdev/master/briefs/2026-11-19-cysr-1116-bump.md`(master#7fd78531) · 답 = master#693ca661
- 가지 = integ/1116 · 출발 3ff732f64 · 판 올림 커밋 = 8a901ab40 · push·태그·CI 0

## 끝난 것
| 항목 | 내용 | 확인 |
|---|---|---|
| ui-test 붉은 칸 | `USER-MANUAL.md` 크롬 문단 「업데이트할 때부터」 → 「새 판으로 갱신될 때부터」(eacc7c8e6 유입) | `bun test` 3747 pass · 88 skip · 0 fail(기준 3ff732f64 = 3746/88/1) |
| 판 올림 1.1.14 → 1.1.16 | 1.1.14 판 올림 3d5f97234 와 같은 8파일 · 같은 자리(Cargo.toml · src-tauri/Cargo.toml · tauri.conf.json · ui/package.json · dist-win/cys.wxs · cys-x64.wxs · Cargo.lock 2줄 · docs/index.html 7줄) | `version-check.sh v1.1.16` rc 0 · `cargo metadata --locked --offline` rc 0 |
| 되돌리기 문서 | `docs/RELEASE-ROLLBACK.md:101` 1-b 제목 「1.1.16 → 1.1.15」 → 「1.1.16 → 1.1.14」 · 본문 「1.1.15 는 레인 저널을」 → 「1.1.14 는」(skip-update PLAN §1 행 28) | 문서 |
| 공개 점검 제품 3파일 | `cysr-public-check-1118/REPORT.md:42-43` — `javis_owner.py:5-6`·`test_owner_desk.py:4` 날짜 붙은 워크숍 사용기 → 일반 설명 · `USER-MANUAL.md` agy 문단의 `ENTRY-MODES.md`(public-exclude.txt:59) 참조 2곳 제거 | `test_owner_desk` 52 OK |
| 닿는 게이트 단계 | `GATE_ONLY` = gen-ceo · gen-hashes · secret-scan · pack-secrets · pack-test_bootv2_doc_contract · pack-test_owner_desk · script-test_* · health · ui-test · ui-install · ui-tsc · ui-build | gate_rc=1 · 붉은 단계 1 = health(H-CLT-1·2 · 기준선과 사유 전문 일치) · 나머지 전부 rc 0 · ui-test 3747/0 · 보호 계수 불변(syspolicyd 21 · fake 87) · 결과 폴더 `~/axdev/.wt/cys-1116-integ-bump-gate/summary.txt` |

## 조건부 — 1.1.15 를 건너뛰기로 정해지면(11-20 19:17 발행 판정 · master#693ca661 「지금 고치지 않는다」)
1.1.16 으로 바꿀 사용자 표기 3곳:
- `USER-MANUAL.md:171` 「(1.1.15) `Control Center` 단추는 처음에는 꺼져 있습니다」
- `USER-MANUAL.md:182` 「안내 글이 바뀌면(1.1.15 — 보내는 항목을 빠짐없이 적도록 고침)」
- `docs/agy-door-evidence/ENTRY-MODES.md:142` 「## 6. 한계 — 이 판(1.1.15)에서 막지 않는 것」
그대로 두는 것: `src/pack.rs:5578·5584·5658` 「1.1.15 이전 판이 남긴…」 안내(master#693ca661).

⚠ 반대로 1.1.15 를 내기로 정해지면: 이 커밋의 `docs/RELEASE-ROLLBACK.md:101` 고침(1.1.14 출발)은 되돌린다(1.1.16 → 1.1.15 가 맞아짐) · 판번 1.1.16 은 그대로.

## 1.1.15 건너뜀에 걸리는 자리(실측 · 11-19)
- release_seq(PLAN §1 행 2): 저장소 변수 `CYSR_RELEASE_SEQ` = **6**(`gh variable list -R oogisoogi/cys-ro` · 11-06 07:43 KST 설정) · 보관소 `6.json` 200 · `7.json` 404 → 1.1.16 = seq 7 · **태그 전 변수 7 로 올림 = 바깥 쓰기(master 게이트)** · 트리 안 수정 자리 0(`release.yml:41` 이 vars 를 읽음).
- 발행 지침 해시 표(행 12): 태그 = v1.1.14 까지 · v1.1.15 태그 없음 → 재생성 불요 · `gen_released_directive_hashes.py --check` rc 0(이 게이트 gen-hashes).
- 날짜 칸 11-21: 1.1.14 판 올림 자리에 날짜 줄 0(3d5f97234 diff) · 1.1.16 발행 노트 초안 트리에 없음 → 넣은 곳 0.

## 판 번호 전수(git grep 「1.1.1[45]」 · 보고만)
- 1.1.14: 코드·시험 결합 0 — 전부 주석(이력)·e2e 대역 값(`ui/e2e/seatrows_gate.py:66` 등 `version:'1.1.14'`)·크롬 표지 시험 자료(`src/pack.rs:13857·13888`).
- 1.1.15: 위 조건부 3곳 + 코드 주석·저널 안내 문구(그대로).

## 남은 위험
- Rust 쪽(build · lib · bin-cys · bin-cysd · cys-app · it-*)은 이 티켓에서 다시 돌리지 않았다 — 판번(CARGO_PKG_VERSION)·USER-MANUAL(include_str 3곳 `src/bin/cys.rs:49824` · `src/bin/cysd/accounts.rs:4363~4413`)이 바뀌어 재컴파일 범위 → master 전체 게이트.
- health H-CLT-1·2 붉음 = 기준선(3ff732f64)과 사유 전문 일치(허용 기준선).
