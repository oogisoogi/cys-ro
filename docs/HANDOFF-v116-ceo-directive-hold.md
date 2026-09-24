# HANDOFF — v116-ceo-directive-hold (부서를 만든 기계가 master 지침 개정을 못 받는 결함)

TICKET=v116-ceo-directive-hold · 브랜치 `fix/v116-ceo-directive-hold` ← 기점 adf50d44 · 작성 worker-42(surface:1090) · 2026-09-24
설계 = `docs/DESIGN-v116-ceo-directive-hold.md`(원인 재현 · 선택지 표 · 권고 · 이종 검증 기록)
master 판정 = [master#260dc93d] ⑴ⓑ⁺+ⓕ ⑵ⓔ 추가 ⑶8b 교체(별도 커밋) ⑷ⓧ1 포함 · ⓧ2 기록만 · ⓧ3 = 1.1.7 후보

---

## 1. 무엇이 고장이었나 · 무엇을 고쳤나

| 경로 | 증상 | 원인(대조군 통과) | 고친 곳 |
|---|---|---|---|
| 1 (1085 VM-B) | 1.1.4 이하에서 부서를 만든 기계를 단추로 갱신하면 master 지침이 `.new` 로 보류 → 새 지침 영구 미적용 | 단추 갱신은 **옛 앱 안의 `cys pack-update`** 가 새 팩을 먼저 판정(1.1.5 `src-tauri/src/main.rs` `install_pack_update` → `resolve_sidecar`). 옛 코드엔 D1-ⓑ 가 없어 MASTER 를 `.new` 로 두고 CEO_TEMPLATE(System)만 갱신 → manifest[CEO] 전진 → 재시작 뒤 새 판 init-pack 의 D1-ⓑ(manifest[CEO]==디스크) 영구 불성립 | **ⓑ⁺** `src/pack.rs` `ceo_derived_override`: 근거 = manifest[CEO] ∨ 승격 영수증 해시 ∨ 역대 발행 CEO 해시 표 · 구제 시 영수증 전진 · vendor 바이트 그대로인 `.new` 정리 |
| 2 (1098 교회 부서 시범) | 부서 없는 기계에 옛 승격의 `.pre-ceo` 가 남으면, 승격 때 현행 판 미백업 · 알림 꺼짐 · 부서를 다 닫으면 **옛 판 부활**(같은 판번 init-pack 은 0 written · 무신호) | cys-dept 가 「`.pre-ceo` 존재」를 「유효 백업 존재」로 간주(`[ -f .pre-ceo ] \|\| cp` · `_auto` · 부트 게이트) | **ⓕ** `cysjavis-pack/bin/cys-dept` `pre_ceo_is_stale`(긍정 증거: md≠CEO ∧ CEO ⊇ md ∧ 영수증≠sha(md)) → 락 보유 시 `.pre-ceo.stale-<시각>` 로 보존 후 새 백업 · `_auto`·부트 게이트도 같은 판정 |
| 2 사후 | 이미 강등돼 옛 판이 된 기계 | manifest[MASTER] ≠ 디스크라 D1 미수정 판정 불성립 | **ⓔ** `decide_file_action`: MASTER 한 파일 한정 — 디스크가 **손대지 않은 옛 발행 표준본**(역대 발행 MASTER 해시 표)이면 RefreshUser · `.pre-ceo` 동반 전진도 같은 표로 |
| ⓧ1 | 두 번째 부서 생성 때 손본 CEO 사본을 백업 없이 덮음 | `_swap` 의 `cp ceo md` | **ⓧ1** `_swap`: 유효 백업이 이미 있고 md≠영수증이면 덮기 전 `MASTER_DIRECTIVE.md.pre-ceo-<시각>` 보존 · MASTER 교체 = tmp+mv 원자화 |

- 역대 발행 해시 표 = `src/released_directive_hashes.rs`(생성기 `scripts/gen_released_directive_hashes.py` · 태그 v0.14.* · v1.* + 작업 트리 · `--check`). **지침 원문(CEO_TEMPLATE·MASTER_DIRECTIVE)을 고치면 반드시 재생성** — 안 하면 `released_tables_cover_current_embed` 적색.
- 형상 표 = `cysjavis-pack/bin/tests/fixtures/ceo_directive_shapes.json`(7형상) — Rust `ceo_directive_shapes_installer` 와 `test_ceo_pending_gate.py` 12) 가 **같이 읽는다**(master 판정 ⑴).

## 2. 효과 시점
- 1.1.5 → 1.1.6: 옛 1.1.5 사이드카가 1.1.6 팩을 먼저 판정(1.1.5 D1-ⓑ 보유 → 1.1.5 에서 승격한 기계는 여기서 정상 처리). 이미 `.new` 가 쌓인 기계(1.1.4 이하 승격)는 **재시작 때 1.1.6 init-pack** 이 영수증·발행 표로 구제.
- cys-dept(ⓕ·ⓧ1)는 팩 파일이라 1.1.6 팩 적용 직후부터(다음 부서 생성·10분 틱) 적용.

## 3. 커밋
(아래 §9 의 `git log adf50d44..HEAD` 참조 — 최종 해시는 【확인요청】 본문)

## 4. 재현(격리 HOME · 라이브 ~/.cys 무접촉)
| 형상 | 수리 전(adf50d44) | 수리본 |
|---|---|---|
| 1.1.2 승격 → 1.1.2 `pack-update --from 발행 v1.1.5` → init-pack(`scratch/repro.sh`) | MASTER=4d29(1.1.2 CEO) · .new=ea31 · 구제 0 | MASTER=9f4e(1.1.5 CEO) · .pre-ceo=ea31 · .new 제거 · 영수증=9f4e · `.bak-1.1.5` · 2회째 변화 0 |
| 대조군(팩 적용 바이너리만 새 판) | .new 없음 · MASTER=9f4e | — |
| 1098 형상(`scratch/repro2.sh`) promote → down | 승격 뒤 .pre-ceo=9e93(낡음) · 강등 뒤 MASTER=9e93(옛 판) | 승격 뒤 .pre-ceo=ea31(현행) · `.pre-ceo.stale-*`=9e93 보존 · 강등 뒤 MASTER=ea31 |

## 5. 시험
- Rust: `d1b_rescues_ceo_copy_after_old_sidecar_advanced_manifest`(기준선 적색 a0feb5fa → 초록) · `ceo_directive_shapes_installer`(7형상 × 멱등 2회) · `released_tables_cover_current_embed` · 기존 `d1_user_owned_refresh_merge_and_ceo_derivative` 초록 유지.
- bash(cys-dept): `test_ceo_pending_gate.py` 8b(기대 교체 6f04ec51 · 수리 전 적색 실측) · 11a-d(기준선 적색 313699e3 → 초록) · 11e·11f(agy 반례 가드) · 12)(형상 표 5형상 × 멱등 2회 + 1098 강등). bash 3.2.57 ALL PASS · bash 5(PortableGit) 【미측정 — 이 맥에 없음 · push 뒤 윈 CI】.

## 6. 함정(다음 사람)
- 좌석 셸의 `CYS_CYS_BIN` 이 시험에 새면 cys-dept 가 스텁 대신 **설치본 cys** 를 부르고, 그 cys 가 가짜 HOME 에 **고아 cysd** 를 띄운다(오늘 실사고 · 98bc233c 로 시험 setup 이 CYS_* 전부 제거). 시험·검토자는 `env -i`.
- 시험 발행 해시 주입은 **CEO 표·MASTER 표 따로**(`TEST_RELEASED_CEO_EXTRA` / `_MASTER_EXTRA`) — 섞으면 표준본이 CEO 사본으로 오판된다(실측).
- 형상 시험이 `PACK_ENV_LOCK` 을 쥔 채 패닉하면 다른 pack 시험이 PoisonError 로 연쇄 적색 — 첫 실패만 보라.
- `.new` 정리는 **vendor 바이트와 완전 일치**할 때만(사용자가 `.new` 를 손봤으면 무접촉).

## 7. 남은 것 · 곁 항목
- ⓧ2(손수정 CEO 사본 기계는 새 CEO 문안을 `.new` 로도 못 받음) = 설계상 정상 · 기록만(master 판정).
- ⓧ3(윈 mkdir 락 실패 시 무락 강행) = 1.1.7 후보(master). agy C1 NOTE: **잔존 mkdir 락 디렉터리**가 있으면 이후 승격이 전부 무락 경로 → ⓕ 가 생략된다. 그 기계도 ⓧ1(덮기 전 보존)과 ⓔ(다음 init-pack 에서 옛 발행 표준본 갱신)가 뒤를 받친다.
- CRLF `.new` 잔재(agy C1 NOTE): LF 봉인(2026-08-23) 이전 윈 빌드가 쓴 `.new` 는 바이트 불일치로 정리 안 됨 — 파일만 남고 원장 항목 없음(무해 · 기록만).
- 윈 실기 0 · 윈 bash 5 【미측정】.

## 7-1. 9단계 성찰(코드 · C 완료 전 1회) — 항목별
| 단계 | 적용 | 한 일 / 바뀐 것 |
|---|---|---|
| 1 의도 | 적용 | 「승격 기계도 개정 지침 수신 + 쌓인 기계 구제 + 강등 시 옛 판 부활 차단 · 정책 무접촉」 — 구현이 이 한 문장 밖으로 나간 줄 없음(승격 정책·확인 창 무변경 · 지침 원문 무변경). |
| 2 설계안 대조 | 적용 | §5 권고 1~6 전부 구현. 설계와 달라진 것 1: 시험 주입을 CEO/MASTER 표별로 분리(한 목록이면 표준본이 CEO 사본으로 오판 — 실측 적색). |
| 3 파급(30년차) | 적용 | 호출부 = `ceo_derived_override` 2곳(install_into · plan_install) 모두 영수증 전달 · `decide_file_action` ⓔ 가지는 MASTER 한 파일 한정. prune = manifest 등재 파일만 → 새 백업(`.pre-ceo.stale-*` · `.pre-ceo-<시각>`) 불가침. `.pre-ceo*` 이름을 훑는 제품 코드 0건(grep). **남은 파급 1(기록만)**: pack-update 롤백 저널은 `.new` 는 복원하지만 `.pre-ceo` 전진(1.1.5 D1-ⓑ 부터)·영수증 전진은 저널 밖 — 롤백 시 `.pre-ceo`=더 새 표준 · 영수증 불일치 → C03 은 핀 폴백으로 승격 판정 유지 · 다음 설치에서 발행 표로 재구제(해로움 없음 · 1.1.6 재시작 경로 init-pack 은 비트랜잭션). |
| 4 결함 재조사 | 적용 | 뮤턴트 생존 2건(R7 · B5) = 시험 공백 → 형상 1개·시험 1개 보강 뒤 12/12. |
| 5 결정론 치환 | 적용 | 발행 해시 표 = 생성기 + `--check` + cargo 시험 강제(손 편집 0). 판정 전부 바이트 해시·부분 문자열 결정론. |
| 6 적대 A/B/C | 적용 | agy B R1(BLOCK 3 → 반영) · R2 ACCEPT · agy C1 ACCEPT(NOTE 3) · Opus 적대(결과 §10) · 블라인드 합격 20/20. |
| 7 언어 | 부분 | 저장소 관례(한국어 주석) 유지 — 외과적 변경 원칙 우선. |
| 8 필요성 | 적용 | 뺀 것: ⓐ·ⓒ(파급) · ⓓ(ⓑ⁺와 중복) · 롤백 저널 확장(위 3 · 마감 직전 저널 구조 변경 위험 > 이득). |
| 9 저장 | 적용 | 설계 = DESIGN · 구현 뒤 상태 = 이 HANDOFF. |

## 7-2. 완료 뒤 정밀 디버깅(실 바이너리 · 격리 HOME)
| 경계 | 결과 |
|---|---|
| 승격 보류(ceo-pending · 부트 마커 없음) 중 1.1.2 사이드카 갱신 → 수리본 init-pack → 부트 뒤 10분 틱 | 1.1.2 사이드카는 **미승격 표준본에도** `.new`(ea31) 를 남김(1.1.2 = D1 없음) → 수리본 init-pack 이 MASTER=ea31 로 갱신 · `.new` 제거 → 틱 승격 = MASTER 9f4e · .pre-ceo ea31 · pending 해소 |
| 영수증 없는 **v1.1.0 CEO 실물 바이트** 사본(aff914) + v1.1.0 표준 .pre-ceo(63963a) | 발행 표 실해시로 구제: MASTER=9f4e · .pre-ceo=ea31(발행 MASTER 표로 전진) · 영수증 생성 9f4e |
| 부서 2개 → 하나 닫음 → 둘 다 닫음 | 하나 닫음 = 승격 유지 · 둘 다 닫음 = MASTER ea31(현행) · 백업 정리 |
| 강등 직후 갱신 · 갱신 2회 연속 | 형상 표 demoted-* 2형상 · 모든 형상 2회 멱등(Rust) · repro fixed-v112-then-fix 2회째 변화 0 |
| 손수정 사본 · 핀 삭제 | 형상 표 hand-edited-ceo · pinless-edit(설치기 무접촉 · cys-dept 덮기 전 보존) |
| 윈 bash | bash 3.2.57 ALL PASS · bash 5(PortableGit) 【미측정】 |
| 표적 뮤테이션 | 12/12 KILLED(R1~R7 · B1~B5 · 첫 판 10/12 → 생존 2 보강 뒤 2/2) |
| 어디까지 뒤졌나 | 설치기 판정 2곳(install_into · plan_install) · decide_file_action User 가지 · .pre-ceo 동반 · .new/원장 정리 · 롤백 저널 · prune · cys-dept 승격/강등/틱/락 3갈래 · C03 영수증 판정 연계 · 발행 해시 표 생성·강제 · 형상 8종 |

## 8. 4군
(【확인요청】 본문과 동일 — 최종 수치로 채움)

## 9. 재현 명령
```
S=~/axdev/.wt/v116-ceo-directive-hold-scratch
$S/repro.sh <case> $S/target-v112/debug/cys <수리본 cys>     # 경로 1
$S/repro2.sh <case> <수리본 cys>                               # 경로 2
python3 cysjavis-pack/bin/tests/test_ceo_pending_gate.py
CARGO_TARGET_DIR=$PWD/target cargo test --lib -- ceo_ d1 released_
python3 $S/mutants.py                                          # 뮤턴트(작업트리 무접촉 · scratch/mut worktree)
```

## 10. 검증 기록(성찰·이종·적대·블라인드·뮤턴트)
| 단계 | 검증자(모델) | 판정 | 처리 |
|---|---|---|---|
| B 설계 R1 | agy(타사) | BLOCK 3 | ①ⓕ 부정 증거 술어 → 긍정 증거로 · ③락 미보유 시 새 동작 생략 · ②종전 결함 기록 (DESIGN §8) |
| B 설계 R2 | agy | ACCEPT(새 반례 0) | — |
| C 구현 R1 | agy | ACCEPT(NOTE 3: 잔존 mkdir 락 · 손본 표준본 무접촉 · CRLF .new 잔재) | 기록만(§7) |
| C 구현 R1 | Opus 5.5 적대 서브에이전트(jsonl model = claude-opus-5-5 × 65) | **REVISE** — F1 부분 포함 판정이 개행 누락·CRLF CEO 사본·잘린 표준본을 표준 원본으로 오판(회귀 · 재현 있음) · F2 승격 없는 강등이 옛 판·손본 표준본을 덮음(재현 있음) · NOTE F3~F11 | 기준선 적색 8d39c38a(26 FAIL 실측) → 수리 cee0ec7a(ALL PASS): F1 동등 비교(구분선 뒤 본문 == md · 시험 13 구분선 계약) · F2 강등 = 승격 긍정 증거 있을 때만 · F3 보존본 중복 금지·tmp 정리 · F5 발행 표 = 태그 전부(44종) · F6 손본 .new 보호 · F7 고유 tmp · F8 원자 강등 · F9 flock 실패=무락. 불채택: F4(ⓔ = master 승인 정책 · .bak 로 되돌림 가능) · F10(CEO_TEMPLATE = System 등급 · 사용자 편집 비대상) · F11(promote-ceo post-verify 「.pre-ceo 존재=성공」 = 종전 결함 · 곁 항목) |
| C 구현 R2 | Opus 5.5 적대(같은 검토자 · 자기 반례 재실행 · cee0ec7a) | **REVISE** — 1R 반례 전부 해소 · 새 회귀 N1(강등 판정이 한글 핀 「단일소유 강제」까지 요구 → CEO 제목 편집·CP949 저장 사본은 강등 생략 = 영구 CEO) · NOTE N2(강등이 손본 CEO 사본을 백업 없이 덮음 · 종전) · N3(생성기 개발 태그 포함) · N4(보존본 이름 초 단위 충돌) | 기준선 적색 6a57b5ae(6 FAIL) → 수리 ad0c9b38(ALL PASS): 강등 표지 = ASCII 'master of master'(시험 13b = CEO 에만·표준 0회) · 강등 전 보존 · 발행 계열 태그만 · 이름 -pid |
| C 구현 R3 | Opus 5.5 적대 | (진행 중 · ad0c9b38) | |
| C 구현 R2 | agy | (진행 중 · ad0c9b38) | |
| 합격 시험(규칙 ⑤) | 구현 미열람 Opus 5.5 서브에이전트(jsonl model = claude-opus-5-5 × 25) | **20/20 PASS**(S1~S6 · 실 바이너리 · 발행 v1.1.5 팩) · 수리본(cee0ec7a 재빌드)에서 같은 스크립트 재실행 = **20/20 PASS** | 모호점 5건 기록(HEAD 지침 = v1.1.5 와 바이트 동일이라 판별력 일부 제한 등) · 스크립트 `scratch/blind/acceptance.py` · 결과 `scratch/blind/rerun-cee0ec7a.out` · ad0c9b38 재실행 예정 |
| 뮤턴트 | scratch/mutants.py | 1차 10/12 → 생존 2(R7·B5) 보강 → 12/12 · cee0ec7a 16개 = 14/16(생존 R8·B7) → 보강(형상 vmb-user-edited-new · 시험 11h) · ad0c9b38 18개(B8·B9 추가) 재실행(진행 중) | |
| 정본 게이트 | gate_runner(워크플로 run 블록 원문) | 80e7b628·cee0ec7a 실행은 이후 수리로 무효화 → 내 실행만 중단(잔여 자식 1개 = 스스로 종료 확인) → **ad0c9b38 재실행(진행 중)** · 기준 adf50d44 실패 = D07b.test_phoenix_c6_reap 1건 | |
