# HANDOFF — cysr 1.1.6 T-REL (발행 도구 결함 2) · TICKET=v116-rel

- 워커 = worker-23(surface:1041 · 1041 cys-v116-rel) · worktree `~/axdev/.wt/cys-v116-rel` · 브랜치 `fix/v116-rel`(v1.1.5 = 526325bf 에서)
- 브리프 = `~/axdev/master/briefs/2026-09-24-v116-rel.md` · 계획서 = `master/reports/cysr-116-plan/PLAN-1.1.6.md` §1-9 X-6·X-7 · §3-1 T-REL
- ⛔ v1.1.5 드래프트·태그·릴리스 무접촉 · git push·태그·릴리스·CI 워크플로 수정 0

## §1 설계 성찰 9단계 (1회차)

정직 고지: X-6 은 코드(커밋 d16befd9·a111e1e7)가 먼저 나왔고 이 서면 성찰은 그 뒤에 적었다(설계는 착수 전 머릿속에서 했지만 서면이 아니었다 — 브리프의 「설계 1회」 순서를 어겼다). X-7 은 이 성찰을 적은 **뒤에** 코드를 쓴다.

| 단계 | 적용 | 이유 1줄 |
|---|---|---|
| 1 철학·원칙 재성찰 | 적용 | 발행 도구 = 자비스 설치·갱신의 입구 → 속도보다 「잘못된 판 배포 0」이 기준. 로컬 전용·GitHub 쓰기 0 원칙 유지(모의만). |
| 2 구체 설계안 | 적용 | X-6: ①2단계 생략 조건 = zip 속 exe sha = 현 exe sha ②4단계 zip 내부 exe 대조 1줄·불일치 rc 1 ③(master 판정 A) 1단계 캐시 = digest 일치만. X-7: 아래 §3. |
| 3 의도·영향 범위·변경 설계 | 적용 | 의도 1문장 = 「발행될 zip 이 발행될 exe 를 담았음을 도구가 증명한다」. 파급: release-postprocess.py 단일 파일 + 그 시험 파일(이미 ci-branch·release 두 레인에 편입 → CI 수정 불요). release-verify.py·release.yml 무접촉. |
| 4 설계 결함 재조사 | 적용 | 결함 발견 1건 → 편입: 대조가 참이 되려면 **로컬 exe 가 발행 자산**이어야 하는데 크기-같음 캐시가 그 전제를 깬다(.sig 412B 실측). master 판정 A 로 같은 파일에서 닫음. |
| 5 결정론 치환(할루시네이션 차단) | 적용 | 모든 판정이 sha256 비교 = 코드. 사람 눈 대조(당시 수동 처방 「zip 속 exe sha·SUMS 대조」)를 코드 1줄로 치환. |
| 6 적대 성찰(방어 불가 지점) | 적용 | 방어 불가였던 것: ⑴ 판독 불가 zip 을 「일치」로 접을 수 있나 → None=불일치로 설계 ⑵ 재생성기가 틀린 zip 을 만들면 → 대조가 --apply 전에 막음(test_64) ⑶ 받은 바이트가 digest 와 다르면 → rc 1. |
| 7 다른 관점(운영자) | 적용 | 운영자는 로그 1줄로 판단한다 → 생략/재생성/대조 줄에 sha 앞 16자·전체 64자를 그대로 인쇄. 수동 우회(백업 폴더 .9th·.10th 이동)가 더는 필요 없다. |
| 8 개선점 필요성 최종 점검 | 적용 | 넣지 않은 것: SUMS 자산 자체 검증 확장·release-verify 수정·RELEASE-PROCESS 문서 개정(master 문서) — 브리프 범위 밖. |
| 9 저장 후 구현 | 적용 | 이 파일이 저장본(순환 대비). |

## §2 X-6 — 원인·수정·시험

### 원인(파일:행 · 수정 전 = 526325bf)
- `scripts/release-postprocess.py:416-417` — `if zipname in by_name: print("zip 이미 릴리스에 있음 — 재생성 생략")` : 릴리스에 zip 이 **있기만 하면** 내용 무관 생략 → 옛 exe 담은 zip 이 6단계에서 그대로 재업로드.
- `:433-442` 자기 검증 — SUMS 각 줄을 **그 파일 자신**과만 대조 → zip 속 exe ↔ exe 행 불일치를 구조적으로 못 봄.
- `:392` 캐시 — 「있음 + 크기 같음」이면 재다운로드 생략 → 크기 같은 옛 바이트 사용.

### 실물 증거(【관측】 ~/cys-release-backup · 읽기 전용)
| 백업 | exe sha(앞 16) | zip 속 exe sha | SUMS exe 행 | 새 대조 |
|---|---|---|---|---|
| v1.1.5-assets.9th-1915 | ce995703cde97786 | **ae8bec159e1d9ec0**(5차 옛 exe) | ce995703… | ✗ 불일치(잡힘) |
| v1.1.5-assets.10th-0002 | 4aadb952d4988a34 | 4aadb952d4988a34 | 4aadb952… | ✓ 일치 |
| v1.1.5-assets(11차) | 66343d9f8be10c7c | 66343d9f8be10c7c | 66343d9f… | ✓ 일치 |

`.exe.sig` 크기: 9·10·11차 전부 412B, sha = bf3739d7… / b2507818… / 91db43ca… (크기 캐시면 항상 옛 서명 적중).

### 수정(커밋 d16befd9)
- `zip_member_sha` · `win_zip_crosscheck` · `asset_digest` · `cache_hit` 신설, main 2단계·4단계·1단계 배선.
- 2단계: 생략 = zip 속 exe sha = 현 exe sha 일 때만. 아니면 재생성(로그에 두 sha) → --apply 6단계가 기존 자산 DELETE 후 업로드 = 옛 자산 교체(기존 로직 재사용).
- 4단계: `  ✓/✗ zip 내부 대조: zip 속 <exe> sha=<64> · SUMS <exe> 행=<64> → 일치/불일치` · 불일치 rc 1(게이트·업로드 전).
- 1단계: 캐시 = 로컬 sha256 = 자산 digest 일 때만 · digest 없음/형식 불명/불일치 = 재다운로드 · 받은 바이트 ≠ digest = rc 1 · latest.json 예외 유지.

### 시험(커밋 a111e1e7 · `python3 scripts/tests/test_release_postprocess_gate.py`)
- 기존 60건 + 신규 12건(test_60~71) = 72건 OK. 기존 test_49 소스 핀만 새 판정식으로 갱신(의도 = latest.json 예외 존치 — 그대로).
- 모의 = token·api·download·업로드 urlopen 주입(모의 밖 호출은 AssertionError) · make-win-zip.py 실물 실행.
- 뮤턴트 8/8 KILLED: M1 대조 호출 제거 · M2 대조 비교 뒤집기 · M3 생략 조건 뒤집기 · M3b 옛 무조건 생략 복원 · M4 크기 캐시 복원 · M5 받은 뒤 digest 검사 제거 · M6 digest 없음=적중 · M7 latest.json 예외 제거.
- ⚠커밋 분리 부작용: d16befd9 단독 상태에서는 test_49 가 적색(핀 갱신이 다음 커밋 a111e1e7). 두 커밋을 함께 통합해야 한다.

## §3 X-7 — 원인·처방·시험

### X-7 설계 성찰(코드 전 · 9단계 요지)
- 1·3 의도 = 「병렬 기본 cysd 스위트가 참 신호만 낸다」 · 파급 = 시험 코드만(#[cfg(test)]) · 제품 코드 무접촉.
- 2·4 설계: 탐침으로 원인 확정 → 같은 변수의 락을 하나로(REAP_ENV_LOCK 격상 선례) → 독살 차단(into_inner). 결함 재조사 = 락 병합의 교착 위험 → 두 락 동시 보유 시험 0건 실측(스크립트 전수)으로 배제.
- 5 결정론: 원인은 추론이 아니라 탐침 출력(실패 시험이 읽은 경로)으로 확정.
- 6 적대: 「into_inner 만 하면 원인이 덮인다」 → 원인 수정을 1차로 두고 into_inner 는 2차(연쇄 차단)로만. poison 무시 뒤 잔류 상태 위험 → 락 데이터는 `()` · 각 시험이 쓰기 전 CYS_PACK_DIR 을 스스로 set.
- 7 운영자 관점: 절단마다 거짓 적색 44건 → 진짜 실패는 1건으로 보인다.
- 8 넣지 않은 것: 곁 관측 flake 2종(아래 §3-4) — 원인 다름 · 범위 밖.

### 원인(【관측】 · 로그 = 스크래치 x7/)
1. 기준선(526325bf 트리 · 수정 전) 병렬 기본 전 스위트 4회 중 3회 적색: base-2 44건 · base-3 38건 · probe-1 44건 · base-1 초록. 근원 패닉은 매번 ACL 시험 1건이 「거부돼야 할 전송이 허용」(`acl_denied` 기대 · `{"ok":true,"result":{"sent":true}}`): `non_owner_acl_verdict_and_payload_are_byte_identical`(handlers.rs:8812) · `owner_token_closes_machine_origin_gap…`(:9472) · `owner_promotion_that_flips_verdict_is_audited`(:9074). 나머지는 전부 `ACL_ENV_LOCK.lock().unwrap()` 의 PoisonError.
2. 탐침(임시 · 커밋 안 함 · 되돌림): `check_send_acl` 이 acl.json 을 못 읽을 때 경로를 찍게 함 → 실패한 ACL 시험의 출력:
   `X7PROBE acl missing: thread=Some("handlers::tests::owner_promotion_that_flips_verdict_is_audited") acl_path=…/T/cys-b1-pack-v113-alt-framed-79933-1790202260/acl.json`
   이 경로는 governance.rs `empty_pack_dir("v113-alt-framed")`(시험 `v113_alt_screen_framed_menu_row_still_blocks` → `run_alt_seat`)가 만든 **빈 팩**이다.
3. 원인 확정: `CYS_PACK_DIR` 을 handlers ACL 시험은 `ACL_ENV_LOCK`(handlers.rs:8260)으로, governance 큐 게이트 시험 15건은 `QUEUE_ENV_LOCK`(governance.rs:10081) + `QueueEnvGuard` 로 지켰다 — **같은 프로세스 전역 변수에 서로 다른 락 2개**. 큐 시험이 ACL 시험 도중 경로를 빈 팩으로 바꾸면 `check_send_acl`(handlers.rs:1154) 이 「정책 파일 없음 = 허용」 분기로 빠진다.
4. 「원래 실패하던 ACL 시험의 진짜 원인」 = **시험 환경 경합(시험 하네스 결함)** 이다. ACL 판정 로직·제품 결함이 아니다(제품 데몬에서 CYS_PACK_DIR 은 기동 때 한 번 정해진다). 특정 시험 1건의 결함도 아니다 — 근원 시험이 매번 다르다(3회 3종).
5. 곁 관측(범위 밖 · 기록만): handlers 시험만 따로 돌린 1회(abA-2)에서 `agent_meta_snapshot_is_consistent_across_list_and_status`(spawn failed ENOENT) · `a_spawned_pty_child_does_not_inherit_the_lock_fd`(락 fd 상속) 2건 적색 — ACL 과 무관한 다른 flake.

### 처방(커밋 65be8114 · 전부 #[cfg(test)])
- governance.rs: `#[cfg(test)] pub(crate) static PACK_DIR_ENV_LOCK` 신설(REAP_ENV_LOCK 바로 아래 · 같은 교리). 큐 시험의 사설 `QUEUE_ENV_LOCK` → `use super::PACK_DIR_ENV_LOCK as QUEUE_ENV_LOCK;`.
- handlers.rs: 사설 `ACL_ENV_LOCK` → `use crate::governance::PACK_DIR_ENV_LOCK as ACL_ENV_LOCK;` · 획득 66곳 `.lock().unwrap()` → `.lock().unwrap_or_else(|e| e.into_inner())`(큐 락 21곳·handlers.rs:11358 선례).
- 교착 점검: 함수 단위 전수 스캔 — ACL_ENV_LOCK·QUEUE_ENV_LOCK 을 다른 *_LOCK 과 함께 쥐는 함수 0건.
- `cargo fmt --check` Diff 수 = 3687(수정 전) = 3687(수정 후) — 새 서식 차이 0(저장소 자체가 fmt 비청정).
- 모듈 경계 문자열(`"\n#[cfg(test)]\nmod tests {"`)을 찾는 소스 계약 시험 3건 때문에 `mod tests` 선언은 건드리지 않았다(그래서 공용 락을 테스트 모듈 밖에 둠).

### 시험(완료 기준 = 병렬 기본 7회 연속 PoisonError 0 + 직렬 1회 초록)
로그 = 스크래치 `x7/fix-par-1..7.log` · `x7/fix-serial.log`(전건 보관). 트리 = 65be8114(X-7 처방 포함) 빌드.

| 실행 | 결과 | PoisonError | 소요 |
|---|---|---|---|
| 병렬 기본 1 | ok · 1044 passed · 0 failed · 1 ignored | 0 | 49.65s |
| 병렬 기본 2 | ok · 1044 / 0 | 0 | 53.65s |
| 병렬 기본 3 | ok · 1044 / 0 | 0 | 48.19s |
| 병렬 기본 4 | ok · 1044 / 0 | 0 | 48.09s |
| 병렬 기본 5 | ok · 1044 / 0 | 0 | 47.14s |
| 병렬 기본 6 | ok · 1044 / 0 | 0 | 51.25s |
| 병렬 기본 7 | ok · 1044 / 0 | 0 | 49.04s |
| 직렬(`--test-threads=1`) | ok · 1044 / 0 | 0 | 112.78s |

대조군(수정 전 · 같은 기계): 병렬 4회 중 3회 적색(44·38·44건) · 1회 초록 · 44.15–49.05s.
완료 기준 = **충족**(7회 연속 PoisonError 0 + 직렬 초록).

## §4 곁 S3 — gen_ceo_template worktree 대응(커밋 a18e88a7)
- `scripts/gen_ceo_template.py:94` `os.path.isdir(REPO_DIR/.git)` → `os.path.exists(...)`. worktree 의 `.git` 은 파일(`-rw-r--r-- 70B` 실측).
- 수정 전 이 worktree: `· 표지 핀 구판 축: skip(no-git — 신판 축만 단언)` / `표지 3핀(신판)`. 수정 후: `표지 3핀(신판+구판 1a90128)` GREEN.
- 음성 대조: 구판 본문을 핀 없는 문자열로 바꾸면 `check()` rc=1(「구판 템플릿(1a90128)에 부재」) = 축이 실제로 돈다.
- 관련 팩 시험 3종(test_ceo_pending_gate · test_content_pins_parity · test_bootv2_doc_contract) rc=0.

## §5 검증(이종 · 적대)

### agy 1R — X-6(수정 전문 붙임 · 파일 권한 없음 · 원문 = 스크래치 agy/x6-r1.md) = REJECT 4건
| # | 지적 | 판정 | 근거 |
|---|---|---|---|
| 1 | P1 digest 없으면 받은 뒤 무결성 검사 생략(fail-open) | 불채택 · 잔여 위험으로 보고 | master 판정 A 원문 = 「digest 없음 = 재다운로드」(차단 아님). 새로 받은 바이트는 릴리스 자산 그 자체(크기 대조 + TLS). master 실측 07:07 = v1.1.5 자산 14개 전부 digest 보유. |
| 2 | P3 test_61 의 `sums[ZIP] == sha(업로드 zip)` 단언은 새 zip 을 증명 못 함 | 기각(오독) | 바로 위 단언 `inner_sha(up[ZIP]) == sha(NEW_EXE)` 가 「올린 zip 이 새 exe 를 담았다」를 증명한다. 해당 줄은 SUMS↔업로드 정합 확인용. |
| 3 | P3 `zipname in by_name and` 중복 → 제거 뮤턴트 생존 | 동치 뮤턴트 · 무변경 | `inner` 가 그 경우 None 이라 거동 동일 — 시험 공백이 아니다. |
| 4 | P3 `ok = inner == row`(None 검사 제거) 뮤턴트 생존 | **채택** → 커밋 54efec0c | 판독 불가 × 행 없음 케이스 추가 → M8 KILLED. |

### agy 1R — X-7·S3(원문 = agy/x7-r1.md) = REJECT 5건
| # | 지적 | 판정 | 근거 |
|---|---|---|---|
| 1 | P1 pack.rs `PACK_ENV_LOCK` 경합 잔존 | 기각(범위 사실 오류) | cysd 시험 바이너리 `--list` = 1045건 중 `pack::` **0건** · cysd 소스에 PACK_ENV_LOCK 참조 0 — pack.rs 시험은 lib 시험 바이너리에서 돈다. |
| 2 | P2 진짜 패닉 뒤 잔류 경로를 QueueEnvGuard 가 복원 | 잔여 위험 기록 | 진짜 실패(이미 적색) 뒤에만 생긴다 · 종전에도 같은 가드 동작 · 수정 전엔 그 뒤 전부가 PoisonError 였다(악화 아님). |
| 3 | P2 재진입 자가 교착 | 기각(현재 0) · 잔여 주의 | 교차 모듈 헬퍼 호출 grep 0(양방향) · 두 락 동시 보유 함수 0. 앞으로 한 락이라 헬퍼에서 재획득하면 멈춘다 — 멈춤은 조용한 통과가 아니라 드러나는 실패다. |
| 4 | P3 직렬화로 느려짐 | 실측 수용 | 수정 전 44.2–49.1s(4회) → 수정 후 48.1–53.7s(5회 기준) · 약 +4s · 시간초과 0. |
| 5 | P2 쓰레기 `.git` 파일이면 스크립트 사망 | 기각(오독) | `git show` 실패 시 `returncode != 0 → None → skip` — 종전 비-repo 와 같은 경로. |

### Fable 적대 서브에이전트 1R — X-6 = ACCEPT(틀린 판 통과·옳은 판 차단 경로 0) · 커버리지 지적 8건
| # | 지적 | 판정 | 조치 |
|---|---|---|---|
| 1 | P2 「릴리스에 zip 없음」(매 절단 첫 경로) main 시험 0 · 가드 삭제 뮤턴트 생존 | 채택 | test_72(dry-run→--apply) · 뮤턴트 M9 KILLED |
| 2 | P3 대조 단위 계약 둘 다 None 칸 | 이미 반영(agy #4) | 54efec0c |
| 3 | P3 대조가 게이트 앞이라는 순서 무증명(모의가 윈도우 단독) | 채택 | test_74 소스 순서 핀 · M12 KILLED |
| 4 | P3 암호화 플래그·미지원 압축 zip → traceback(계약은 None) | 채택 | except 에 RuntimeError·NotImplementedError 추가(58f4ee3b) · test_75 · M10·M11 KILLED |
| 5 | P3 실제 릴리스에 digest 칸이 있는가 미관측 | 해소 | master 실측 07:07 `gh release view v1.1.5` = 자산 14개 전부 digest(sha256:…) |
| 6 | P3 유지 zip 의 --apply 시험 없음 | 채택 | test_73 |
| 7 | P3 「그 사이를 이 한 줄이 잇는다」 과대 서술 — 대조 줄은 2단계 성공 뒤 항상 참 | 채택(정직 정정) | docstring 정정: 실제로 닫은 것 = 2단계 조건 + digest 캐시 · 대조 줄 = 심층 방어·운영 증거 |
| 8 | P3 범위 밖: 릴리스 스냅샷 1회 → 1단계와 --apply 사이 CI 재업로드 시 옛 exe 박제 | 잔여 위험 기록 | 하류 release-verify.py 의 SUMS↔자산·signature 대조가 발행 전 최종 방어 |

### agy 2R — 1R 대응 델타(54efec0c·58f4ee3b·e9f859ea · 원문 agy/x6-r2.md) = **ACCEPT · 새 유효 지적 0(dry)**
- 확장된 except 가 삼킨 오류는 두 호출처 모두 fail-closed(2단계 = 재생성 · 4단계 = 차단) · test_75 픽스처가 실제 RuntimeError 를 낸다 · 뮤턴트 주장에 공허함 없음 · 로그 줄 None 처리 회귀 없음.

### 수렴 판정(정직 고지)
- X-6: agy 1R REJECT(유효 1 반영) → Fable 1R ACCEPT(정확성 결함 0 · 커버리지 5 반영) → agy 2R ACCEPT dry. 「서로 다른 검증자 dry」 중 **dry 는 agy 2R 1회**다 — Fable 은 반영 델타를 다시 보지 않았다(요청 시 Fable 2R 가능).
- X-7·S3: agy 1R REJECT 5건 = 기각 3(사실 근거 제시) · 잔여 기록 1 · 실측 수용 1 → 코드 변경 0. 재검증 라운드는 돌리지 않았다.

## §6 정밀 디버깅 패스(완료 뒤 1회)
- X-6 순서·경계 탐침(모의 하네스 · 임시 스크립트 · 커밋 안 함):
  - D1 dry-run → --apply 같은 백업 폴더: rc 0/0 · 업로드 zip = 새 exe · 옛 zip 2회 재다운로드(로컬 재생성본이 릴리스 digest 와 달라 캐시 불신 = 의도).
  - D2 --apply 뒤 재실행(릴리스 zip = 새 것): 「재생성 생략」 · zip 재다운로드 0(digest 캐시 적중).
  - D3 릴리스에 zip 없음: 생성 · 대조 ✓.
  - D4 exe 없음(zip 만): rc 1 · 업로드 0.
  - D5 엔트리 이름만 다른 zip(내용 같음): 판독 불가 → 재생성 → 대조 ✓.
- 실물 바이트(읽기 전용): 9차 백업 ✗ · 10차·11차 ✓(§2 표).
- 표적 뮤테이션: X-6 9/9 KILLED. X-7 = 락 재분리 뮤턴트(아래 §7).

## §7 X-7 표적 뮤턴트(락 재분리 · 임시 · 되돌림 확인)
- 뮤턴트 X7-M1: governance 큐 테스트의 별칭을 다시 사설 `static QUEUE_ENV_LOCK` 로(= 수정 전 락 2개 구조) · handlers 쪽 into_inner 는 그대로.
- 결과(로그 x7/mut-1.log): **1회차에 KILLED** — `FAILED. 1042 passed; 2 failed` · PoisonError **0**.
  - 근원 2건 = `owner_token_closes_machine_origin_gap…`(handlers.rs:9476) · `queue_deliver_denied_by_send_acl`(:15788) — 수정 전과 같은 「거부돼야 할 전송 허용」 부류.
  - 함의 2개: ⑴ 락 통합이 원인을 닫는다(되돌리면 즉시 재발) ⑵ into_inner 가 연쇄를 막는다 — 같은 원인이 **44건이 아니라 2건**으로 보인다(진짜 실패만 적색).
- 되돌림: `git checkout -- src/bin/cysd/governance.rs` · `git status` = HANDOFF 미추적만. ⚠`target/` 의 cysd 시험 바이너리는 마지막 빌드가 뮤턴트판이다 — 다음 `cargo test` 가 자동 재빌드한다.

## §8 4군 점검(cysr 개발 절대 앵커)
수정 파일 전수 = `scripts/release-postprocess.py` · `scripts/tests/test_release_postprocess_gate.py` · `src/bin/cysd/governance.rs`(#[cfg(test)] 만) · `src/bin/cysd/handlers.rs`(#[cfg(test)] 테스트 모듈 안만) · `scripts/gen_ceo_template.py` · 이 문서.
| 4군 | 닿는가 | 근거 |
|---|---|---|
| 폭주 큐 | 아니오 | 큐 제품 코드 무변경 — governance.rs 변경은 `#[cfg(test)]` static 1개 + 테스트 모듈 안 `use` 1줄(릴리스 빌드에 없다). |
| 무clear 100%+ | 아니오 | 컨텍스트·순환 경로 무접촉. |
| 자가치유 전멸 | 아니오 | 데몬 런타임 무접촉(cysd 변경은 전부 시험 빌드 전용). |
| 전 pane 사망 | 아니오 | PTY·좌석·배달 코드 무접촉. |
| 윈 설치파일 | **간접 · 개선 방향** | 설치 파일 바이트는 안 바꾼다. 발행 후처리가 **옛 exe 를 담은 zip 을 올리지 못하게** 막는 쪽(X-6) — 잘못된 윈 zip 배포 경로를 닫는다. 실제 --apply 는 이 티켓에서 0회(모의만). |

## §9 완료 전 성찰 9단계(2회차 · 구현·검증 뒤)
| 단계 | 적용 | 이유 1줄 |
|---|---|---|
| 1 철학·원칙 | 적용 | GitHub 쓰기 0 · v1.1.5 무접촉 · 실 --apply 0 유지(모의·읽기 전용 실물 대조만) 확인. |
| 2 설계안 대비 구현 | 적용 | 설계 3항(생략 조건·대조 줄·digest 캐시) 전부 구현 + 검증에서 나온 1항(판독 불가 종류 확장) 추가 — 추가분은 fail-closed 방향이라 범위 확장 아님(Fable 지적 채택). |
| 3 영향 범위 재점검 | 적용 | 파일 5개 전수(§8). 시험 파일은 이미 ci-branch·release 두 레인에 편입 → CI 워크플로 무수정으로 새 시험 13건이 돈다. |
| 4 설계 결함 재조사 | 적용 | 스스로 찾은 결함 1(digest 전제) + 검증자가 찾은 결함 3(둘 다 None · 첫 절단 경로 무시험 · 암호화 zip 크래시) → 전부 반영. |
| 5 결정론 치환 | 적용 | X-7 원인은 추정(【추정】 2 락)을 탐침 출력으로 확정 — 「도구 출력만 사실」. |
| 6 적대 성찰 | 적용 | 방어 불가였던 서술 1건(대조 줄이 사이를 잇는다) 정정. 남은 방어 불가 0 — 잔여 위험은 §10 에 명시. |
| 7 운영자 관점 | 적용 | 로그 줄: 생략/재생성/판독 불가/대조 ✓✗ 모두 sha 병기. 수동 우회(폴더 이동·zip 삭제 처방) 불요. |
| 8 필요성 최종 점검 | 적용 | into_inner 66곳은 「진짜 실패 1건 = 적색 1건」을 위해 필요 — 원인은 락 통합이 닫고, into_inner 는 가림막 제거만. |
| 9 저장 | 적용 | 이 문서 + 커밋 9개(아래 §10). |

## §10 종결 요약
### 커밋(브랜치 fix/v116-rel · 526325bf 위 · push 0)
| 커밋 | 종류 | 내용 |
|---|---|---|
| d16befd9 | 제품 | X-6 생략 조건·대조 1줄·digest 캐시 |
| a111e1e7 | 시험 | X-6 모의 릴리스 12건 + test_49 핀 갱신 |
| 65be8114 | 시험(하네스) | X-7 CYS_PACK_DIR 단일 락 + into_inner 66곳 |
| a18e88a7 | 제품(도구) | S3 exists(.git) |
| 54efec0c | 시험 | agy 1R #4 |
| 58f4ee3b | 제품 | Fable 1R #4·#7 |
| e9f859ea | 시험 | Fable 1R 4건 |
| (이 문서) | 문서 | HANDOFF |
⚠통합은 **묶음으로** — d16befd9 단독이면 test_49 적색(핀 갱신이 a111e1e7).

### 시험 표
| 묶음 | 기존 | 신규 | 결과 |
|---|---|---|---|
| test_release_postprocess_gate.py | 60 | 16(test_60~75) | 76/76 OK |
| X-6 뮤턴트 | — | 13 | 13/13 KILLED |
| cysd `cargo test --bin cysd` 병렬 기본 | 1044(+1 ignored) | 0 | 7/7 초록 · PoisonError 0 |
| cysd 직렬 | 1044 | 0 | 초록 |
| X-7 뮤턴트(락 재분리) | — | 1 | KILLED(1회차 · 2 failed · poison 0) |
| gen_ceo_template --check · 팩 시험 3종 | 4 | 0 | 전부 rc 0 · 구판 축 실행 |

### 잔여 위험(정직 고지)
1. digest 가 **없는** 자산은 받은 뒤 무결성 대조가 크기뿐이다(master 판정 A 설계 그대로 · 현 릴리스는 14/14 digest 보유).
2. 릴리스 목록 스냅샷은 실행 시작 1회 — 1단계와 --apply 사이 CI 재업로드는 못 본다(하류 release-verify.py 가 최종 방어).
3. X-7: 진짜 패닉 뒤 잔류 경로를 QueueEnvGuard 가 복원할 수 있다(진짜 실패 뒤에만) · 앞으로 한 락을 헬퍼에서 재획득하면 멈춘다(조용한 통과가 아닌 드러나는 멈춤).
4. X-7 과 무관한 다른 flake 2종 1회 관측(PTY 스폰 ENOENT · 락 fd 상속) — 범위 밖.
5. 실 GitHub `--apply` 는 이 티켓에서 0회. 실물 확인은 백업 바이트 읽기 전용 대조뿐.
