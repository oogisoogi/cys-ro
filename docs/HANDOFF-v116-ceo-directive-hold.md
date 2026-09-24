# HANDOFF — v116-ceo-directive-hold (부서를 만든 기계가 master 지침 개정을 못 받는 결함)

TICKET=v116-ceo-directive-hold · 브랜치 `fix/v116-ceo-directive-hold` ← 기점 adf50d44 · 작성 worker-42(surface:1090) · 2026-09-24
설계 = `docs/DESIGN-v116-ceo-directive-hold.md`(원인 재현 · 선택지 표 · 권고 · 이종 검증 기록)
master 판정 = [master#260dc93d] ⑴ⓑ⁺+ⓕ ⑵ⓔ 추가 ⑶8b 교체(별도 커밋) ⑷ⓧ1 포함 · ⓧ2 기록만 · ⓧ3 = 1.1.7 후보

---

## 1. 무엇이 고장이었나 · 무엇을 고쳤나

| 경로 | 증상 | 원인(대조군 통과) | 고친 곳 |
|---|---|---|---|
| 1 (1085 VM-B) | 1.1.4 이하에서 부서를 만든 기계를 단추로 갱신하면 master 지침이 `.new` 로 보류 → 새 지침 영구 미적용 | 단추 갱신은 **옛 앱 안의 `cys pack-update`** 가 새 팩을 먼저 판정(1.1.5 `src-tauri/src/main.rs` `install_pack_update` → `resolve_sidecar`). 옛 코드엔 D1-ⓑ 가 없어 MASTER 를 `.new` 로 두고 CEO_TEMPLATE(System)만 갱신 → manifest[CEO] 전진 → 재시작 뒤 새 판 init-pack 의 D1-ⓑ(manifest[CEO]==디스크) 영구 불성립 | **ⓑ⁺** `src/pack.rs` `ceo_derived_override`: 근거 = manifest[CEO] ∨ 승격 영수증 해시 ∨ 역대 발행 CEO 해시 표 · 구제 시 영수증 전진 · vendor 바이트 그대로인 `.new` 정리 |
| 2 (1098 교회 부서 시범) | 부서 없는 기계에 옛 승격의 `.pre-ceo` 가 남으면, 승격 때 현행 판 미백업 · 알림 꺼짐 · 부서를 다 닫으면 **옛 판 부활**(같은 판번 init-pack 은 0 written · 무신호) | cys-dept 가 「`.pre-ceo` 존재」를 「유효 백업 존재」로 간주(`[ -f .pre-ceo ] \|\| cp` · `_auto` · 부트 게이트) | **ⓕ** `cysjavis-pack/bin/cys-dept` `pre_ceo_is_stale`(긍정 증거: md≠CEO ∧ 영수증≠sha(md) ∧ **md 가 손대지 않은 표준본 = 정확 일치**(§12 · B)) → 락 보유 시 `.pre-ceo.stale-<시각>` 로 보존 후 새 백업 · `_auto`·부트 게이트도 같은 판정 |
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
| C 구현 R2 | agy(ad0c9b38) | REVISE — 발행 해시 생성기가 태그 없는 얕은 클론·CRLF 작업트리에 의존(얕은 클론에서 돌리면 표가 현재 판 1줄로 덮여 이력 소실) | dfdb92e4: 태그 0개면 생성·검사 거부 exit 3 · 작업 트리 CRLF→LF(실측: 거부 rc 3 · --check OK) |
| C 구현 R3 | Opus 5.5 적대(ad0c9b38) | **REVISE** — N1~N4 해소 · 새 회귀 M1(강등 기본값이 「증거 없으면 복원 안 함」 → 빈 파일·부재·UTF-16 md 가 영구히 빈 지침 · 기점은 복원) | 기준선 적색 dfdb92e4(7 FAIL) → 3cd6e36a: 강등 기본값 = 복원 · 건너뛰기 = 표준본 ASCII 긍정 증거일 때만 · 시험 13c |
| C 구현 R3 | agy(3cd6e36a) | BLOCK 3 — ①Keep 분기가 손본 .new 를 vendor 로 재기록 ②손본 CEO 사본 Keep 시 manifest 미전진 ③손본 표준본 + 갱신 .new + 낡은 .pre-ceo → 부서 생성이 .new 로 통과 → 낡은 백업 미인정 → 강등이 옛 판 복원 | ③ 수용: 기준선 적색(8 FAIL) → b87bbf07: 낡은 백업 판정 = 본문 동등 ∨ 표준본 ASCII 긍정 증거(CEO 구분선 표지 배제 · 시험 13d) · ①② = `git diff adf50d44..HEAD` 대조로 종전 설치기 동작(이 티켓 밖 · 기록만 · ②는 사용자 수정 보존 설계, 반복 설치 멱등은 형상 시험 2회로 고정) |
| C 구현 R4 | Opus 5.5 적대(b87bbf07) | **REVISE** — M1 해소 · 새 반례 P1(표준본 판정 `ceo_md_is_standard` 가 1행 머리말만 봐서 **잘린 표준본**을 온전한 표준본으로 판정 → R2b 승격→강등 = 잘린 md 가 새 백업·진짜 백업 .stale- · R2c 바로 강등 = 복원 생략 → 부서 0개에 잘린 4096B 지침 · 기점 정상 · R2b 는 b87bbf07 회귀, R2c 는 cee0ec7a 부터) · NOTE P2(머리글 지운 CEO 사본 + CP949 → 한글 구분선 표지 grep 불발 → 표준본 오판) | **미해결 → §11** |
| C 구현 R4 | agy | (진행 중 · b87bbf07) | |
| 합격 시험(규칙 ⑤) | 구현 미열람 Opus 5.5 서브에이전트(jsonl model = claude-opus-5-5 × 25) | **20/20 PASS**(S1~S6 · 실 바이너리 · 발행 v1.1.5 팩) · 수리본(cee0ec7a 재빌드)에서 같은 스크립트 재실행 = **20/20 PASS** | 모호점 5건 기록(HEAD 지침 = v1.1.5 와 바이트 동일이라 판별력 일부 제한 등) · 스크립트 `scratch/blind/acceptance.py` · 결과 `scratch/blind/rerun-{cee0ec7a,ad0c9b38,3cd6e36a,b87bbf07}.out` = 매번 20/20 |
| 뮤턴트 | scratch/mutants.py | 1차 10/12 → 생존 2(R7·B5) 보강 → 12/12 · cee0ec7a 16개 = 14/16(생존 R8·B7) → 보강(형상 vmb-user-edited-new · 시험 11h) · ad0c9b38 18개(B8·B9 추가) 재실행(진행 중) | |
| 정본 게이트 | gate_runner(워크플로 run 블록 원문) | 80e7b628·cee0ec7a 실행은 이후 수리로 무효화 → 내 실행만 중단(잔여 자식 1개 = 스스로 종료 확인) → **ad0c9b38 재실행(진행 중)** · 기준 adf50d44 실패 = D07b.test_phoenix_c6_reap 1건 | |

## 11. 미해결(수렴 전) — 다음 사람이 여기서 시작
- **P1(REVISE · 재현 있음)**: `cysjavis-pack/bin/cys-dept` `ceo_md_is_standard` 가 「파일이 끝까지 온전한가」를 안 본다.
  - 재현 = `~/axdev/.wt/v116-ceo-directive-hold-scratch/adv-opus/repro_dept.py`(R2b · R2c · `REAL=1` = 실 발행 바이트 · md = 표준본 앞 4096B).
  - 입력 발생 경로 = 1.1.5 이하 강등 `cp .pre-ceo md`(비원자)가 끊김 → md 잘림 · .pre-ceo·영수증 잔존(M1 빈 파일과 같은 계열).
  - 검토자 수정안 = 표준본 증거에 「잘리지 않음」 추가: LF 정규화한 md 가 `.pre-ceo` · CEO 구분선 뒤 본문 · `.new` 중 하나의 **진접두(strict prefix)** 면 손상본 → ⓕ 는 낡은 백업으로 보지 않고, 강등은 건너뛰지 않는다(비어 있지 않으면 보존 뒤 복원). 형상 표에 R2b·R2c 두 형상 추가 → 기준선 적색 먼저(규칙 ④).
  - 추가 뮤턴트 = 진접두 검사 제거.
- **P2(NOTE · 두 조건 겹침)**: 머리글 지운 CEO 사본 + CP949 저장 → 한글 표지 '운영 계약 전문]' 불발. 수정안 = 표준본 증거에 「UTF-8 로 디코드 가능」 추가(python 한 줄) 또는 구분선 ASCII 부분(`\n---\n\n# [`) 검사.
- ★설계 성찰(후임 판단 재료): 「md 내용으로 표준본/CEO 사본을 가르는」 휴리스틱이 라운드마다 새 경계(개행·CRLF·잘림·빈 파일·인코딩·머리글 삭제)를 만났다(F1→N1→M1→③→P1). 대안 = 판정을 **정확 일치**로만(현행 표준 본문 · 역대 발행 MASTER 해시 표 — 설치기가 팩 안에 해시 목록 파일을 떨구면 bash 도 읽을 수 있다) 하고, 그 밖은 종전 동작 + 보존본. 이 경우 agy C3 ③(손본 표준본)은 「보존본에 남고 강등은 옛 판」으로 후퇴한다 — master 판정 사안.
- 수집 중이던 것: agy C4 재실행(첫 실행 rc 137 SIGKILL · 원인 미상 · 내가 죽인 것 아님) · 뮤턴트 22개(b87bbf07 · scratch/mutants5.out) · 정본 게이트(b87bbf07 · ~/msv-scratch/v116rv/results/ceo-b87bbf07-*).

### 11-1. master 판정 [master#eebe2815](17:1x) — 후임이 할 일
- **P1 = A(1.1.6)**: 「잘리지 않음」 조건(LF 정규화 md 가 `.pre-ceo` · CEO 구분선 뒤 본문 · `.new` 의 **진접두**면 손상본 → ⓕ 는 낡은 백업으로 보지 않음 · 강등은 건너뛰지 않음 = 비어 있지 않으면 보존 뒤 복원) + **P2** = 표준본 증거에 「UTF-8 디코드 가능」. 규칙 ④: 형상 표에 R2b(승격→강등)·R2c(바로 강등)·P2(머리글 지운 CEO 사본 CP949) 형상 → **기준선 적색 먼저** → 수리 → 뮤턴트(진접두 검사 제거 · UTF-8 조건 제거 추가) → Opus 적대·agy 재검증.
- ★**멈춤 규칙**: 다음 검토 라운드에서 내용 휴리스틱 경계 반례가 또 나오면(6번째) 휴리스틱 수선을 멈추고 **B(정확 일치)** 로 전환 — 그때 master 에 올린다.
- **1.1.7 후보(기록만)**: 승격 시점에 바꾼 MASTER·쓴 CEO 의 sha256 을 옆 파일로 남기고 강등 때 그 해시로 「손대지 않음」을 판정(역대 발행 해시 목록은 옛 승격분에만) — 휴리스틱 계보를 끝내는 구조 수리.
- 실행 주체 = 후임(순환 뒤) · 이 워커는 수집(agy C4 재실행 · 정본 게이트 b87bbf07)만 마치고 【매듭】 · 새 Claude 서브에이전트 금지.

### 11-2. 수집 결과(17:3x · 코드 b87bbf07)
- **정본 게이트 전체**(gate_runner · 워크플로 run 블록 원문 · 격리 HOME/TMPDIR `~/msv-scratch/v116rv/{home,tmp}-ceo-170537` · 결과 `~/msv-scratch/v116rv/results/ceo-b87bbf07-170537`): 98 단계 · compare_runs(기준 adf50d44) = **대상 실패 3 · 기준 실패 3 · 신규 0 · 해소 0** · rc≠0 스텝 = D07b.test_phoenix_c6_reap(기준과 동일) · D02 Secret/PII scan 0 · D11 팩 내용 스캔 0 · B01 boot-health-full 0 · A12/A13/A14 · D07c/d/e · X01 cargo 0 · D06 bun 0. 비교표 = `scratch/gate-compare.md`.
- **뮤턴트** 22/22 KILLED(b87bbf07 · 가짜 KILLED 0 — 러너가 directives 미복사로 끝에서 죽던 결함은 b010a1c5 무렵 발견·수정).
- **agy C4**(b87bbf07): 1차 rc 137(SIGKILL · 원인 미상 · 내가 죽인 것 아님) · 2차 429 사용량 한도 · 3차 = **BLOCK 1** — 잔존 mkdir 락(무락 강행 · `_locked=0`)이면 ⓕ 가 생략돼 낡은 .pre-ceo 가 남고 강등이 옛 판 복원. ⇒ 설계상 절충(agy B1 ③: 무락 창에서 .pre-ceo 를 옮기면 동시 승격이 백업을 서로 덮음)과 종전 결함 ⓧ3(무락 강행 · master 1.1.7 후보)의 교차점 · 내용 휴리스틱 경계가 아니므로 멈춤 규칙 대상 아님 · 현재 방어 = 그 경로에서도 ⓧ1 이 현행 md 를 `.pre-ceo-<시각>` 로 보존(데이터는 남음) · **master 판정 필요**(선택지: ⓧ3 를 1.1.6 으로 당겨 잔존 락 감지 · 또는 1.1.7 유지).
- 판정 JSON = `scratch/reviews/agy-{B-r1,B-r2,C-r1,C-r2,C-r3,C-r4}.json` · Opus = `scratch/adv-opus/verdict{,-r2,-r3,-r4}.json` · 블라인드 = `scratch/blind/rerun-*.out`.

## 12. B 전환(정확 일치) — 멈춤 규칙 발동 뒤 · 후임 라운드 [master#6fce3767] → [master#2da27fe2]

### 12-1. 경과
| 커밋 | 내용 |
|---|---|
| f50e97e1 | P1·P2 기준선 적색(b87bbf07 에서 24 FAIL) |
| 23510540 · 7e08378f | master 판정 A(진접두 + UTF-8) 수리 · ref 단독 형상 · B8 보강 — 결정론 초록(형상 24 · 뮤턴트 20/20 · 블라인드 20/20 · 블라인드 P1/P2 142/0) |
| — | ★agy C5 = 6번째 휴리스틱 경계(진접두는 「잘린 파일」과 「더 긴 판의 앞부분인 온전한 파일」을 못 가름 · 결정론 재현 `scratch/c5/repro_c5.py` A·B) → 멈춤 규칙 → master 판정 B · Opus R5(7e08378f · 참고)도 같은 계열 Q1·Q2(CRLF 가 `\r` 에서 끊김)·Q3 |
| 536b5d29 | B 기준선 적색(7e08378f 에서 bash 18 FAIL · Rust 1 FAIL) |
| 185fa5b9 | B 구현 |
| 0f5b899f | Opus R6 S1·S2 시험 구멍 보강(발행 목록 가운데 줄 형상 LF·CRLF · 뮤턴트 Y6·Y2 KILLED) · 제품 코드 무변경 |

### 12-2. B 명세(cys-dept `ceo_md_is_standard`)
- 「md 가 손대지 않은 표준 MASTER」 증거 = 줄끝만 LF 로 맞춘 md 바이트가 **①CEO_TEMPLATE 구분선 뒤 본문 ②역대 발행 MASTER 해시 목록** 중 하나와 정확히 같을 때만. 빈 파일·판독 불능 = 증거 없음. 내용 휴리스틱(머리말·표지 grep·진접두·UTF-8) 전부 제거(시험 13b 가 표지 grep 부재를 고정).
- 발행 해시 목록 = **새 팩 파일 `cysjavis-pack/directives/RELEASED_MASTER_DIRECTIVE.sha256`**(System 등급 · 매 설치 강제 갱신). 생성기 `scripts/gen_released_directive_hashes.py` 가 Rust 표(`src/released_directive_hashes.rs`)와 **함께** 쓰고 `--check` 가 둘 다 본다. cargo 시험 `released_master_hash_pack_file_matches_table` = 임베드(pack-manifest 원천 PACK+PACK_SKILLS)에 있음 · Rust 표와 같은 집합 · System · `install_into` 가 디스크에 떨굼. ★지침 원문을 고치면 생성기 재실행(안 하면 cargo·--check 적색).
- `.new` 는 근거가 아니다(브리프 대비 변경 · master 보고 18:44): 손대지 않은 `.new` 는 현행 발행 바이트라 ①② 가 덮고(뮤턴트 X2 생존 = 중복), 사용자가 병합하려고 손본 `.new`(F6)와 같다는 것은 증거가 아니다.

### 12-3. 알려진 한계(master 승인 · 형상 표 `known_limitation` 으로 고정)
| 형상 | B 결과 | 기점 adf50d44 | 비고 |
|---|---|---|---|
| 손본 표준본 + 옛 승격의 낡은 .pre-ceo (형상 edited-standard-held · edited-standard-with-new-stale-pre-ceo · R5 T1/T1d) | 강등이 **.pre-ceo(옛 판) 복원** · 편집본은 `.pre-ceo-<시각>` 보존 | 옛 판 복원 · 편집본 **실종** | 옛 판이 발행본이면 다음 init-pack 의 ⓔ 가 현행 표준으로 올린다(편집은 보존본에만) |
| 끝 개행만 지운 현행본 · UTF-8 BOM 저장본(형상 current-standard-eol-stripped-stale-pre-ceo-close · R5 T2 · B1) | 같음 | 같음(실종) | 편집기 저장 습관 — 정확 일치 밖 |
| 위 형상 + **미부트 기계**(R5 T1n) | 낡은 .pre-ceo 가 유효 백업으로 보여 **승격 보류 게이트도 건너뜀**(자동 승격 알림도 꺼짐) | 같음 | 원래 1098 결함의 이 하위 형상은 B 에서 남는다 · 1.1.7 구조안(아래)이 끝낸다 |
- agy C4 BLOCK(잔존 mkdir 락 = 무락 강행 경로에서 ⓕ 생략 → 강등이 옛 판 복원 · 현행 md 는 `.pre-ceo-<시각>` 보존) = **1.1.7 ⓧ3 티켓이 해소 · master 20:2x 판정 [master#9ccc9fdb]**(발행 차단 4종 아님 · 선재 결함 ⓧ3 과 드문 교차).
- 1.1.7 후보(기록만 · master): 승격 시점에 바꾼 MASTER·쓴 CEO 의 sha256 을 옆 파일로 남기고 강등 때 그 해시로 「손대지 않음」을 판정 — 위 한계 전부를 「승격 때 실제로 백업한 바이트」 기준으로 푼다.
- CRLF 로만 바꾼 현행 표준(문면 동일)은 LF 정규화로 표준본(형상 current-standard-crlf-stale-pre-ceo-close · 뮤턴트 X4).

### 12-4. 검증 기록(B)
| 단계 | 검증자(모델) | 대상 | 판정 | 처리 |
|---|---|---|---|---|
| A 수리 결정론 | 시험·뮤턴트 | 7e08378f | 형상 24 · 뮤턴트 20/20 · 블라인드 20/20 · 블라인드 P1/P2(구현 미열람 Opus · jsonl model = claude-opus-5-5 ×20) 142/0 · b87bbf07 105/37 | B 로 대체 |
| C5 | agy(타사) | 7e08378f | **REVISE**(heuristic_boundary · 진접두가 추가형 신판·끝 개행 삭제본을 손상본으로 오판) | 결정론 재현 `scratch/c5/repro_c5.py` → 멈춤 규칙 → B |
| R5 | Opus 5.5 적대(jsonl model = claude-opus-5-5 ×42) | 7e08378f | REVISE(Q1 손본 표준본 경계 · Q2 CRLF `\r` 끊김 · Q3 추가형 신판 · Q4 뮤턴트 생존 3) | 참고(대상 커밋 바뀜) · Q2·Q3 = B 형상으로 흡수 · Q1 = 알려진 한계 |
| B 기준선 | 시험 | 7e08378f | bash 18 FAIL · Rust 1 FAIL | 536b5d29 |
| C6 | agy | 185fa5b9 | **ACCEPT**(NOTE 2: 목록 판독 실패 = fail-closed 무손실 · Rust 시험은 cys-dept 로직 비보호 = bash 형상·13b 가 보호) | 기록 |
| R6 | Opus 5.5 적대(jsonl model = claude-opus-5-5 ×103) | 185fa5b9 | REVISE(S1 시험 구멍 = 뮤턴트 Y6 목록 첫 줄만 읽기 생존 · 구체 입력 v1.1.4 가운데 줄) · NOTE S2~S5 · 데이터 손실 경로 0 | 0f5b899f(형상 2 · Y6·Y2 KILLED · Y3·Y4 등가) |
| 블라인드 B(규칙 ⑤) | 구현 미열람 Opus 5.5(jsonl model = claude-opus-5-5 ×34) | 185fa5b9 빌드 | **234/0** · 대조 7e08378f 23 FAIL(옛 발행본+추가형 .new · CRLF `\r` 잘림 · 알려진 한계 3 · 목록 없는 팩) | 모호점 4(승격 보류 게이트 명세 누락 · 목록 부재 시 fail-closed 의도 · 복원 이동/복사 · 시각 형식) |
| 뮤턴트(bash) | scratch/mutants.py | 0f5b899f | B1 B2 B10 B6 B6b X1 X3 X4 X5 X6 Y1 Y2 Y5 Y6 Y7 B9 B7a B7b B3 B4 B5 = KILLED · Y3·Y4 = 등가(주석 줄·빈 md 는 어떤 해시와도 불일치) · X2 = 규칙 제거(.new 근거) | Rust 코드 무변경(pack.rs 는 시험 1개 추가뿐) → b87bbf07 Rust 뮤턴트 8/8 유효 |
| S3 배포 창(Opus R6 NOTE) | — | — | pack-update 는 사전순 제자리 쓰기라 `bin/cys-dept` 가 `directives/RELEASED_MASTER_DIRECTIVE.sha256` 보다 먼저 바뀌는 창 존재 → 그 창의 판정 = 증거 없음(보존 뒤 복원 · fail-closed) · init-pack 은 staging 뒤 교체라 창 없음 | 기록만 |
| S4 생성기 태그(Opus R6 NOTE) | — | — | 브랜치에서 workflow_dispatch 한 사전 릴리스 3개는 태그 패턴 밖이나 모두 팩 이전 판 → 현재 누락 0 · v1.0.0~v1.1.5 · rel115 pack · 오너 설치본 MASTER·.bak-1.1.5 목록 포함 확인 | 기록만 |

### 12-5. 최종(코드 = 0f5b899f)
- **결정론(최종 빌드 0f5b899f · 동시 실행 없음 · scratch/final-verify.sh)**: 블라인드 S1~S6 20/20 · 블라인드 B 234/0(내 재실행) · 블라인드 P1/P2 142/0 · dept 형상 30 ALL PASS · Rust pack:: 117/117(185fa5b9 · 이후 Rust 무변경) · 생성기 --check OK · doc-contract OK · bash 뮤턴트 전부 KILLED(등가 Y3·Y4 제외).
- **타사**: agy C6 ACCEPT(185fa5b9) · **agy C7 ACCEPT(0f5b899f 결박 · NOTE 2 = C6 와 같음)**. Opus R6 REVISE(시험 구멍) = 0f5b899f 에서 해소(같은 모델 ACCEPT 는 독립 증거로 세지 않음 · 규칙 ②).
- **정본 게이트**(gate_runner · `~/msv-scratch/v116rv/results/ceo-0f5b899f-192808` · 98 단계): compare_runs 기준 adf50d44 = 대상 실패 5 · 기준 3 · **신규 2 = 둘 다 D07b.test_phoenix_w2_untomb_fullcycle**(본 줄 + 하위 항목) · D02 Secret/PII 0 · D11 팩 스캔 0 · B01 0 · X01 cargo 0 · D06 0.
  - w2_untomb 판정 = **기존 간헐 실패(이 티켓 무관)**: 증상 `FAIL ① live 역할 desired 엔트리 등재 | roster=[]` → ref None TypeError. 격리 재실행 HEAD 3회 중 2회 실패 · **교차 A/B**(`scratch/w2ab.sh` · 같은 부하) HEAD 1/3 실패 · b87bbf07(이번 라운드 이전) 1/3 실패 · 기존 결과 이력에서 526325bf(기점의 조상 · 이 티켓 변경 없음) 3회 중 1회·2efaf0a7 3회 중 2회 실패. 이 티켓 변경(cys-dept · 시험 · 팩 파일 1 · 생성기)은 phoenix 경로 무접촉.
- 프로세스 위생: 내가 띄운 게이트 2회 중단(7e08378f · 185fa5b9 — 대상 커밋 변경) = 부모 사슬(내 claude 67113) 확인한 pid 만 TERM · agy C5 가 띄운 고아 cysd 2개 = 소켓 경로(scratch/demo_env)·agy 전사로 귀속 확인 뒤 TERM · 현재 내 소유 잔여 0.

## 13. A-Z14 수리 — `promote-ceo` 사후 검증 거짓 「승격 완료」(TICKET=v116-ceo-hold-az14 · 후임 worker surface:1104 · 2026-09-25)

- 원 지적 = 동일 모델 검증 실험 A-Z14(Fable 5.1) · 1100 재현 `~/axdev/master/reports/same-model-verification-2026-09-24/scoring/followup/az14.sh`(판정 표 = 같은 보고서 폴더 `04-experiment-report.md` §10).
- 원인(재확인): 게이트(`ceo_promote` 부트 게이트)는 `pre_ceo_valid`(낡은 백업 제외)인데 사후 검증(`promote-ceo`)은 「`cmp md ceo` 또는 `.pre-ceo` 존재」 → 낡은 `.pre-ceo` + 미부트에서 보류(pending · md 무교체)를 exit 0 으로 보고 → GUI 「✅ CEO 승격 완료」.
- ★브리프 처방(「게이트와 같은 판정」)만으로는 부족했다: 부트 완료 + 손본 표준본 + 낡은 `.pre-ceo`(형상 `edited-standard-held`)는 유효 백업처럼 보여 게이트를 지나고 `_swap` 에서 상위집합 검사로 보류되는데, 사후 검증을 `pre_ceo_valid` 로 바꿔도 여전히 exit 0(뮤턴트 M2 · 시험 14e 로 실측). → **확정 = md == CEO 템플릿 실측**, 게이트 술어는 보류 사유 문구에만.
- 상태 표(종료 코드 · cys-dept 문구 · GUI 알림) = DESIGN §9.
- 곁 수리: `ceo_receipt_matches` 가 영수증 부재·판독 불가 때 `No such file`·`Permission denied` 셸 오류 줄을 stderr 로 흘렸다(`<` 리다이렉트 실패는 뒤 `2>/dev/null` 로 안 묻힘) — GUI 알림 원문에 그대로 실렸다 → 존재·판독 먼저 확인(시험 14d·14i · 판정 뜻 불변).
- 기준선 적색 ba8b0d1f(114be35b 제품 코드 · 7 FAIL: 형상 2 × 2회 · 14a · 14d · 14e).
- 뮤턴트(사본 · 작업트리 무접촉 · `scratch/mut_az14.py`): 1차(26a19acb) 5/5 KILLED → Opus R1 이 사유 분기 생존 4(A·F·G·H) 적발 → 보강 뒤 bash **11/11 KILLED**(J = Opus R2 · M1 존재 판정 되돌림 · M2 게이트 술어만 · M3/M4 보류 exit 5→0 · M5/M6 영수증 검사 제거 · A 부트 분기 삭제 · F 템플릿 존재 검사 제거 · G 부트 마커만 · H 그 밖 문구를 부트 표지로) · UI 7/7(U1 부트 안내 삭제 · U2 등급 고정 · U3 원문 태그 노출 · U4 사유 무시 · U5 보류 등급 health · U6 사유 검색 느슨화 · U7 재실행 부트 문구) · Rust 1/1(사유 항상 other).
- 범위 밖(기록만 · DESIGN §9 말미): `promote-if-pending` 은 보류여도 exit 0(알림 = 「CEO 승격 처리」+원문) · 팔레트 「재실행」 노출 게이트 `ceo_promotion_drift` 도 `.pre-ceo` 존재 판정. 거짓 「완료」는 아님.
- 이월 범위 밖(브리프): A-Z31(rollback 저널에 `.pre-ceo`·영수증 없음) = 1.1.7 · agy C4(잔존 mkdir 락) = 1.1.7 ⓧ3.
- master 기준선 114be35b-m 신규 적색 2(B01 H-SECRET-1 · D02 PATH) = §12-5 의 실계정 절대경로 1줄 → `~/…` 로 뜻 보존 치환(원문 보관 문서 아님 · 치환 전 파일 sha256 `49996f795c7f640678af19c2d83d37b98e1199f72f830af1f0f29e82c77eb553`).

### 13-1. 9단계 성찰(A-Z14 · 1회)
| 단계 | 적용 | 한 일 / 바뀐 것 |
|---|---|---|
| 1 의도 | 적용 | 「promote-ceo 가 한 일을 그대로 보고한다(보류를 완료로 말하지 않는다)」 — 승격·강등·게이트 동작 자체는 무변경(ceo_promote 본문 무접촉 · 영수증 판독 함수는 판정 뜻 불변). |
| 2 설계 대조 | 적용 | 브리프 처방 = 「사후 검증이 게이트와 같은 판정」. 실측 반례(14e · 뮤턴트 M2)로 그것만으로는 거짓 0 이 남아 **md 실측 확정 + 게이트 술어는 사유 문구에만**으로 바꿨다(【판단】으로 보고). |
| 3 파급(30년차) | 적용 | promote-ceo 호출자 = GUI approve_ceo_promotion(Allow·팔레트 재실행) · 시험 · 문서 안내. 부서 생성(launch/create/allocate)·틱(promote-if-pending)은 ceo_promote 를 직접 불러 사후 검증 비경유 → 무접촉. exit 0→5 로 바뀌는 형상 = 종전에 거짓 0 이던 형상뿐(템플릿 부재 + .pre-ceo 포함). |
| 4 결함 재조사 | 적용 | 곁 결함 1 발견·수리(영수증 부재 `No such file` 줄이 GUI 원문에 실림 · 14d). 범위 밖 2 기록(promote-if-pending 무사후검증 · ceo_promotion_drift 존재 판정). |
| 5 결정론 | 적용 | 판정 = cmp 바이트 비교 · 태그 = 문자열 상수(Rust 시험이 UI 소스와 대조). |
| 6 적대 A/B/C | 적용 | agy R1 · Opus R1(§13-2). |
| 7 언어 | 부분 | 저장소 관례(한국어 주석) 유지. |
| 8 필요성 | 적용 | 뺀 것: promote-if-pending 사후 검증 추가 · drift 게이트 술어 교체(거짓 「완료」 아님 · 브리프 범위 밖). |
| 9 저장 | 적용 | DESIGN §9 · 이 절. |

### 13-2. 적대 검토 기록(A-Z14)
| 라운드 | 검토자(모델) | 대상 | 판정 | 처리 |
|---|---|---|---|---|
| R1 | agy(타사) · `scratch/az14-review/agy-r1.json` | 26a19acb | ACCEPT(NOTE 5 · 결함 0) | — |
| R1 | Opus 5.5 적대 서브에이전트 · `scratch/az14-review/opus-r1.json` | 26a19acb | **REVISE 2** — ①사유 분기 무고정(변이 A·F·G·H 생존 · 14c 단언이 게이트의 「미부트」 줄로 채워짐) ②UI 보류 문구 부트 안내·등급 무고정 · NOTE: 경합 exit 5 · 템플릿 부재 승격 기계 0→5 · 영수증 권한 000 셸 오류 줄 · 「자세히」 원문 태그 노출 · 재실행 보류 문구가 부트 사유에 「새 설정」 · Allow 보류가 상위집합 사유에도 부트 권유 · DESIGN 재실행 칸 누락 | 전부 수용(경합 · 템플릿 부재 0→5 = 알려진 한계로 DESIGN §9 기록): 사후 검증 사유 표지 · Rust 사유 하위 태그(boot/other) · UI 도우미가 등급·원문까지 결정 · 영수증 `-r` · 시험 14c/14e 표지 단언 · 14f(템플릿 부재 · 발행 표준본) · 14h(유효 백업처럼 보이는 옛 판 + 미부트 = 그 밖) · 14i(권한 000) → 뮤턴트 bash 10/10 · UI 5/5 · Rust 1/1 |
| R2 | Opus 5.5(같은 검토자 · 자기 반례·변이 재실행) · `scratch/az14-review/opus-r2.json` | 9ca55326 | **REVISE 1**(제품 코드는 옳음) — 변이 J(사후 검증 elif 의 부트 마커 항 제거 = 부트 완료 기계의 상위집합 보류에 「부트 필요」 → GUI 거짓 부트 안내) 생존 · NOTE: UI `includes("boot")` 변이 등가 · 재실행 부트 보류 「다시 눌러」 대상이 팔레트에서 「CEO 승격 진행」으로 바뀜 | 시험 9d(부트 완료 + 스텁 템플릿 = 「그 밖」 표지) · UI 그 밖 원문에 `.master-bootstrapped` 섞기 · 재실행 부트 보류 문구 = 「명령 팔레트의 「CEO 승격 진행」을 눌러 주세요」 → bash 11/11 · UI 7/7 KILLED(J · U6 · U7 포함) |
