# cys v0.14.30 리베이스 + 자체 배포 체제 준비 보고서

- **TICKET**: `cys-fork-rebase-v0.14.30`
- **작업자**: worker-5@surface:646 · 2026-09-08 (KST)
- **저장소**: `~/cys-terminal-src` · 새 브랜치 `rebase/v0.14.30`(구 `fix/phoenix-korean-windows`·`rebase/v0.14.27` 보존)
- **CI 미러**: `fix/rebase-v0.14.30`(같은 커밋 · master 판정 ⒞+동명 미러 — 워크플로 무수정)
- **절차 정본**: `~/axdev/master/CYS-UPDATE-POLICY.md` §0(⛔벤더 dmg 직접 설치 금지 · 유일 경로 = 포크 리베이스)
- **형식 승계**: `docs/rebase-v0.14.27-report-2026-08-28.md`

---

## 0. 한 줄 결론

upstream **249커밋**(v0.14.27 → v0.14.30)을 편입하고 그 위에 우리 커밋 **37개를 전부 되살렸다**
(스킵 0 · 드롭 0 · 라인 손실 0). 충돌은 2곳뿐이었고 **판단이 갈리는 충돌은 0건**이었다.
테스트는 **신규 실패 0건**(rust 1689/0 · ui 810/0 · typecheck 0오류), 피닉스 S3 프로브·적대 로케일
스모크·뮤테이션 검산 전부 초록이다. 배포 체제는 endpoint 교체 + master 공개키 삽입 + 감사표까지
끝냈고, **⛔릴리스 태그·Release 발행·설치는 손대지 않았다**(master/박사님 게이트).

---

## 1. 완료 기준 대비 결과 (티켓 §1 · 전부 실측)

| # | 완료 기준 | 결과 | 근거(실행한 명령·출력) |
|---|---|---|---|
| 1 | 브랜치 `rebase/v0.14.30` = v0.14.30 위 우리 37커밋 · origin push | ✅ **충족** | `git rev-list --count v0.14.30..HEAD` → **37** · `git ls-remote origin rebase/v0.14.30` = 로컬 HEAD 일치. force·삭제 0. §2 |
| 2 | 커스텀 생존 대조표 37행 | ✅ **충족** | §2 표 · `git range-diff` 35건 `=` · 2건 `!`(충돌 해소분, 라인수 동일) |
| 3 | 피닉스 프로브 `[4]~[6b]` + 적대 로케일 스모크 재실행 초록 | ✅ **충족** | 프로브 `PASS`(exit 0) · 스모크 `ran=7 pass=7 fail=0` · 뮤테이션 4/4 KILLED. §4 |
| 4 | `cargo test` 전수 = 신규 실패 0건 | ✅ **충족** | 우리 **1689 passed / 0 failed** vs pristine v0.14.30 **1645 / 0** = 우리 테스트 **+44 순증 · 신규 실패 0**. §3 |
| 5 | CI ci-branch·windows-health 초록 | ✅ **충족**(ci-branch `34234945537` 최종 커밋 초록 · windows-health `34230947584` 초록) | run id·경과 = §6 |
| 6 | 배포 체제 ⓐ endpoint ⓑ 워크플로 감사표 ⓒ H-SECRET-1 ⓓ 버전 | ✅ **충족** | §5(ⓐ·ⓑ) · §5-3(ⓒ · secret-scan clean 955파일) · `scripts/version-check.sh` = **8곳 일치 0.14.30** |
| 7 | 맥 빌드 `--bundles app` + `cys-local` 서명 | ✅ **충족** | `BUILD_EXIT=0` · `CFBundleShortVersionString`=**0.14.30** · `Authority=cys-local` · `--verify --deep --strict` exit 0 · `spctl` rejected/origin=cys-local(정상). §7 |
| 8 | 보고서 | ✅ | 이 문서 |

---

## 2. 커스텀 생존 대조표 (37/37 · 스킵 0 · 드롭 0)

절차: `git checkout -b rebase/v0.14.30 fix/phoenix-korean-windows` → `git rebase --onto v0.14.30 v0.14.27`

측정법 2축(둘 다 결정론):
- **축1 `git range-diff v0.14.27..fix/phoenix-korean-windows v0.14.30..rebase/v0.14.30`** —
  **35건이 `=`**(내용 동일) · **2건만 `!`**(#19·#29 = 아래 §2-A 충돌 해소분).
  그 2건의 `!` 도 **차이는 전부 context 줄**이고 우리가 더한 `+` 줄은 하나도 다르지 않다.
- **축2 numstat 전건 대조** — 원본 커밋과 이식 커밋의 **파일수·삽입·삭제가 37건 전부 일치**.
  (0.14.27 리베이스 때는 2건이 달랐다. 이번엔 **0건**이다.)

| # | 원본 → 이식 | 기능(무엇을 지키는 커밋인가) | 닿는 파일 | 원본 | 이식 | 판정 |
|---|---|---|---|---|---|---|
| 1 | `48c8877`→`3811465` | feat(ui): 페인 제목 폰트 통일·확대 + 역할점 작동중에만 깜빡 | appearance.ts · main.ts · style.css | 26+/9- (3f) | 26+/9- (3f) | 동일 |
| 2 | `c48c3ba`→`d5c7b6a` | feat(ui): 영역별 폰트 커스터마이징 — 제목/본문/메뉴 크기·굵기·제목색=역할색 | main.ts · style.css | 54+/5- (2f) | 54+/5- (2f) | 동일 |
| 3 | `61a8604`→`ba2fad6` | fix(ui): 제목 앞짤림·usage 제거·UI크롬 확대·font-smoothing | style.css | 8+/6- (1f) | 8+/6- (1f) | 동일 |
| 4 | `adaa8c1`→`cc7d20c` | fix(ui): unify reviewer role-dot color + enlarge dot 8→10px | appearance.ts · style.css | 2+/2- (2f) | 2+/2- (2f) | 동일 |
| 5 | `ade617c`→`d707edf` | fix(ui): move 정렬 button to leftmost (separate from close — prevent misclick) | index.html | 1+/1- (1f) | 1+/1- (1f) | 동일 |
| 6 | `bc0be40`→`e1f319a` | fix(ui): 역할점 영구 깜빡 수정 — stale 자기보고 불신 + 판정 데이터원 교체 | appearance.test.ts · appearance.ts · main.ts | 74+/22- (3f) | 74+/22- (3f) | 동일 |
| 7 | `e65ae2b`→`539e553` | feat(ui): 정렬 커스텀 레이아웃 — 4열 균등(master·CSO·워커수직·리뷰어수직) | index.html · main.ts | 24+/30- (2f) | 24+/30- (2f) | 동일 |
| 8 | `eb57363`→`cea6914` | feat(ui): 폰트 굵기 세밀화 — 4단계 → 100~800 8단계(variable 대응) | main.ts | 7+/1- (1f) | 7+/1- (1f) | 동일 |
| 9 | `49a2077`→`5176348` | fix(tauri): dev 빌드 정체성 분리 — 도크 유령 타일 제거 | fix-dock-ghost-tile-2026-07-20.md · tauri.dev.conf.json | 45+/0- (2f) | 45+/0- (2f) | 동일 |
| 10 | `d64f64a`→`63c6b11` | docs(ui): 레이아웃 커스텀 영구화 재설계 초안(codex 적대검토 대기) | design-layout-persistence-2026-07-20.md | 152+/0- (1f) | 152+/0- (1f) | 동일 |
| 11 | `385cdba`→`9eb39bc` | docs(ui): 레이아웃 persist 설계 v2 — codex BLOCK 9지적 전면 반영 | design-layout-persistence-2026-07-20.md · fix-dock-ghost-tile-2026-07-20.md | 136+/112- (2f) | 136+/112- (2f) | 동일 |
| 12 | `c07dc25`→`d4261d0` | docs(ui): 레이아웃 설계 v3 — master 07-20 phasing·검토주체 반영 | design-layout-persistence-2026-07-20.md | 49+/21- (1f) | 49+/21- (1f) | 동일 |
| 13 | `4b9bb65`→`11225f4` | fix(ui): 정렬 = 개수 무관 1행 가로 균등 — 역할별 열 묶음 폐기 | index.html · main.ts | 15+/36- (2f) | 15+/36- (2f) | 동일 |
| 14 | `19768b6`→`88c99fc` | feat(ui): usage sidebar + model-only statusline + menu scale — v0.15.0, first release as our own product | cys.rs · index.html · appearance.test.ts · appearance.ts 외 4 | 1087+/34- (8f) | 1087+/34- (8f) | 동일 |
| 15 | `8367dcd`→`d5a1b23` | fix(usage): 사이드바 사용량 원천 = 계정 저장소 · Fable 필드경로 · 모델을 제목으로 · named CTX | main.rs · cys.rs · handlers.rs · main.rs 외 7 | 1034+/57- (11f) | 1034+/57- (11f) | 동일 |
| 16 | `2c4240d`→`74269d9` | feat(usage): OAuth usage API 편입 — Fable 주간 실게이지 · codex 행 비표시 | main.rs · accounts.rs · main.rs · main.ts 외 3 | 669+/6- (7f) | 669+/6- (7f) | 동일 |
| 17 | `cc86817`→`345f1ca` | fix(usage): Fable 자체 집계 줄 삭제 · named CTX 디스크 지속 (오너 육안 2건) | accounts.rs · handlers.rs · named.rs · state.rs 외 4 | 462+/215- (8f) | 462+/215- (8f) | 동일 |
| 18 | `b1b0d5c`→`b24632e` | fix(usage): 페인 CTX 서열 = master → cso → 그 밖의 이름 → 번호 (역할 랭크 명시) | wsusage.test.ts · wsusage.ts | 59+/4- (2f) | 59+/4- (2f) | 동일 |
| 19 | `b4bf3b6`→`e6c0d1a` | fix(ops): 운영 마찰 3결함 — read-screen 정지 scrollback · 침묵 발신거부 · 종료 후 role 잔존 | cys.rs · governance.rs · handlers.rs · state.rs | 716+/30- (4f) | 716+/30- (4f) | 동일 |
| 20 | `7a9c2b2`→`ff15e4e` | fix(usage): 페인 CTX 행별 관측 나이 병기 · 푸터 「갱신」→「가장 낡음」 (오너 실문의) | main.ts · style.css · wsbar.test.ts · wsbar.ts 외 2 | 183+/5- (6f) | 183+/5- (6f) | 동일 |
| 21 | `ac8b6d9`→`b58af00` | fix(usage): 사이드바 사용량 패널 글자 20px 고정 — 두 배율 비연동 (오너 지시) | main.ts · style.css · wsbar.test.ts · wsbar.ts | 96+/28- (4f) | 96+/28- (4f) | 동일 |
| 22 | `84739e4`→`a587202` | fix(wsbar): 사이드바 글자 배율 하나로 헤더·목록·사용량 패널을 함께 조절 (오너 지시) | index.html · main.ts · style.css · wsbar.test.ts 외 1 | 245+/76- (5f) | 245+/76- (5f) | 동일 |
| 23 | `f0a91d0`→`fafe2cf` | fix(wsbar): 사이드바 기준 크기 서열 교정 — 목록 제목 > 상단 버튼 = 사용량 패널 (오너 캡처 판정) | style.css · wsbar.test.ts · wsbar.ts | 150+/32- (3f) | 150+/32- (3f) | 동일 |
| 24 | `d396327`→`9da0d66` | fix(wsbar): 알약 버튼 3종만 한 단계 축소 — ▶CEO·▶부서장·＋부서 16→14px (오너 실기기 판정) | style.css · wsbar.test.ts | 53+/2- (2f) | 53+/2- (2f) | 동일 |
| 25 | `64ae329`→`95c615e` | fix(wsbar): ▶CEO·▶부서장 버튼 복원 — upstream P2(3685af9) 제거분을 포크에서 되살림 (master 판정 C) | index.html · main.ts | 37+/1- (2f) | 37+/1- (2f) | 동일 |
| 26 | `de1e428`→`75ae1e0` | docs: 이월 미추적 작업기록 4종 편입 + 로컬 운영물 gitignore (티켓 §2) | .gitignore · backlog-exited-surface-auto-reap-2026-07-13.md · impl-pane-title-numbering-2026-07-27.md · rebase-v0.14.10-report-2026-08-02.md 외 1 | 809+/0- (5f) | 809+/0- (5f) | 동일 |
| 27 | `aca2c29`→`64a82b8` | fix(ui): 앰비언트 선언에 it.each 추가 — 타입 게이트를 기준선(0건)으로 되돌린다 | bun-env.d.ts | 8+/0- (1f) | 8+/0- (1f) | 동일 |
| 28 | `60c7d0b`→`8fb4f04` | docs: v0.14.27 리베이스·빌드·서명 보고서 | rebase-v0.14.27-report-2026-08-28.md | 382+/0- (1f) | 382+/0- (1f) | 동일 |
| 29 | `07ab986`→`229df16` | fix(phoenix): 로케일 코덱 독립화 + 데몬 스폰 인코딩 패리티 | ci-branch.yml · windows-health.yml · javis_backup.py · javis_event.py 외 8 | 719+/53- (12f) | 719+/53- (12f) | 동일 |
| 30 | `7f032b0`→`9084253` | docs: S5 초안 2 + S3 조사 결과 | installer-remedy-proposal-pythonutf8-2026-09-08.md · s3-master-role-not-persisted-findings-2026-09-08.md · upstream-pr-draft-phoenix-korean-windows-2026-09-08.md | 339+/0- (3f) | 339+/0- (3f) | 동일 |
| 31 | `3d6eb01`→`511c14c` | fix(phoenix): agy R1 반영 — stdio 처리기를 surrogateescape 로 · chcp 인과 정정 | windows-health.yml · lib.rs | 34+/13- (2f) | 34+/13- (2f) | 동일 |
| 32 | `0137582`→`e3540f6` | docs(evidence): agy 이종 검증 판정 원문 2R 박제 | agy-verdicts-phoenix-korean-windows-2026-09-08.md | 57+/0- (1f) | 57+/0- (1f) | 동일 |
| 33 | `a0009a8`→`465420e` | docs: S6 판정 — Windows 자동가동 등록은 env 를 실을 수 없다 | s6-windows-autostart-env-capability-2026-09-08.md | 111+/0- (1f) | 111+/0- (1f) | 동일 |
| 34 | `7022b92`→`262e395` | fix(pack): import guard 회귀 봉합 — setattr(sys,…) 제거 · 증거 디렉터리 오배치 정정 | javis_backup.py · javis_event.py · javis_phoenix.py · javis_state_snapshot.py 외 2 | 98+/45- (6f) | 98+/45- (6f) | 동일 |
| 35 | `7e95a49`→`cc01eac` | fix(topology): 살아있지 않다는 이유로 역할 기록을 지우지 않는다 | s3_coldboot_probe.py · s3_topology_mutants.py · governance.rs | 432+/33- (3f) | 432+/33- (3f) | 동일 |
| 36 | `a7b54a0`→`7e468cd` | wip(s3): agy R1(BLOCK 4건) 반영 — 손상 3분류·역할 유일성·영속 직렬화 | upstream-pr-draft-phoenix-korean-windows-2026-09-08.md · s3_topology_mutants.py · governance.rs · state.rs | 292+/15- (4f) | 292+/15- (4f) | 동일 |
| 37 | `22eb46d`→`f44101c` | feat(surface): new-surface --agent 선언 플래그 — 설치기가 세운 master 를 부활 대상으로 | agy-verdicts-phoenix-s3-master-persist-2026-09-08.md · upstream-pr-draft-phoenix-korean-windows-2026-09-08.md · s3_coldboot_probe.py · s3_topology_mutants.py 외 3 | 442+/33- (7f) | 442+/33- (7f) | 동일 |

### 2-A. 충돌 2곳 — 둘 다 「덧붙임 인접」이었다 (판정 여지 0)

두 충돌 모두 `src/bin/cysd/handlers.rs` 의 **`mod tests` 안 같은 자리**에서 났다. upstream 이
그 위치에 새 시험을 넣었고 우리도 그 위치에 새 시험을 넣었다 — **같은 줄을 다르게 고친 것이
아니라 같은 자리에 서로 다른 것을 덧붙인** 형태다. 충돌 원칙(브리프 §3 「같은 파일 다른 줄 =
둘 다」) 그대로 **양쪽을 보존**했다.

| 충돌 | 우리 커밋 | upstream 쪽 | 해소 |
|---|---|---|---|
| ① | `b4bf3b6`→`e6c0d1a` 운영 마찰 3결함(read-screen 정지 scrollback 외) | `boot_enqueue_authorizes_gui_only_with_the_operator_token`(H-ENQ-GUI-1) | 두 시험 함수를 나란히 보존 |
| ② | `07ab986`→`229df16` 피닉스 S1·S2 | `optional_lease_is_cas_checked_before_any_side_effect`(B3-4/T3-1) 외 lease 검체군 | 두 블록을 나란히 보존 |

검증: 해소 후 `numstat` 이 원본과 **동일**(4f 716+/30- · 12f 719+/53-)하고, 그 파일이 든 두 검체군이
`cargo test --bin cysd` 에서 **956 passed / 0 failed** 로 함께 돈다(양쪽이 살아 있다는 실행 증거).

### 2-B. upstream Windows 인코딩 처방 vs 우리 S1·S2 — **상보다, 중복·사문화 아님**

브리프 §2 가 지목한 대조 항목이다. upstream v0.14.28~30 에는 `bc01f43`
(ci(release): build 잡에 PYTHONUTF8) 등 Windows 인코딩 처방이 들어 있다. 우리 S1(로케일 코덱
독립화)·S2(데몬 스폰 인코딩 패리티)와 **같은 병을 두 곳에서 고친 것이 아닌가**를 파일 단위로 쟀다.

| 축 | pristine v0.14.30 | 우리 트리 | 판정 |
|---|---|---|---|
| `.github/workflows/release.yml` | PYTHONUTF8 **5곳**(bc01f43 = 잡 레벨 1줄) | 동일 5곳(우리 수정 0) | **벤더 것 그대로 편입** |
| `.github/workflows/windows-health.yml` | 1곳(잡 레벨) | **3곳** — 우리가 「불사조 인코딩 독립성 스모크(적대 로케일)」 스텝 추가 | **상보** — 우리 스텝은 자식 env 를 `PYTHONUTF8=0`·`PYTHONIOENCODING=cp949` 로 **덮어** 잡 레벨 UTF-8 을 무력화하고 결함을 재현한다(주석에 그 인과가 명시돼 있다) |
| `src/lib.rs` | 12곳 — `spawn_env_pairs`(층2·셸 경유)에만 PYTHONUTF8 | **20곳** — 층1 `python_command` + `PYTHONIOENCODING` 축 추가 | **상보** — upstream 은 층2만 덮었고 우리는 층1(콜드부트 피닉스 스폰)과 stdio 축을 덮는다 |
| `cysjavis-pack/bin/javis_runtime_seal.py` `_widen_stdio` | 있음(도구 자신을 고치는 형태) | 동일(우리 수정 0) | 중복 아님 — 벤더가 「스크립트 1개의 예외」로 남긴 것 |

⇒ **죽은 코드가 되는 쪽은 없다.** 근거: ⑴재적용 후에도 `python_encoding_contract`·
`role_bearing_surface_is_persisted…` 검체가 살아 있고(§4 뮤테이션에서 M3·M4 가 **KILLED**),
⑵우리가 더한 스텝·상수는 upstream 이 손대지 않은 자리에만 있다(위 표의 곳 수 차이가 전부 우리 순증).

---

## 3. 테스트·타입 게이트 — 기준선 대조 (신규 실패 0건)

기준선은 태그를 **별도 worktree**(`~/cys-pristine-v0.14.30`)로 꺼내 `bun install --frozen-lockfile`
까지 한 뒤 같은 명령으로 실측했다(설치 전엔 모듈 미해결 파생 오류가 대조를 오염시킨다 — 08-02 선례).

| 축 | pristine v0.14.30 (기준선) | 우리 `rebase/v0.14.30` | 판정 |
|---|---|---|---|
| `cargo test --bins --lib` · lib | 491 passed / 0 failed / 1 ignored | **492** / 0 / 1 | +1 |
| 〃 · `src/bin/cys.rs` | 238 / 0 | **241** / 0 | +3 |
| 〃 · `src/bin/cysd/main.rs` | 916 / 0 / 1 ignored | **956** / 0 / 1 | +40 |
| 〃 합계 | **1645 / 0 failed** (exit 0) | **1689 / 0 failed** (exit 0) | **신규 실패 0 · 우리 테스트 44건 순증** |
| `bun test` (ui) | 706 pass / 0 fail (22파일) | **810** pass / 0 fail (23파일) | **신규 실패 0 · 104건 순증** |
| `bunx tsc -p tsconfig.check.json` | exit 0 · 오류 **0건** | exit 0 · 오류 **0건** | **신규 0건** |

### 3-A. ★정직 표기 — 기준선의 「적색 1건」은 병렬 간섭이었다(측정 방법의 결함)

1차 측정에서 pristine 쪽 `tests::doctor_fix_then_rediag_ok` 가 **1건 적색**이었다
(`잔여 락 수리됨: Warn != Ok`). 그때 우리 트리 스위트를 **동시에** 돌리고 있었다.

- **단독 재현 3회 = 3/3 통과**(`cargo test --bin cys doctor_fix_then_rediag_ok`).
- 그래서 기준선을 **단독·`--no-fail-fast`** 로 다시 재서 위 표의 수치를 얻었다 → **0 failed**.
- ★교훈(측정 규율): 두 스위트를 동시에 돌리면 **기준선 자체가 오염**된다. 이 저장소의 doctor 검체는
  프로세스 전역 상태(락 홀더 pid 판정)를 만지므로 병렬 실행에 취약하다. **대조 측정은 직렬로.**
- 이 1건을 "upstream 선재 실패"로 적지 않은 이유가 이것이다 — **재현되지 않는 것을 사실로 적지 않는다.**

---

## 4. 피닉스 축 재검증 (프로브 · 스모크 · 뮤테이션)

### 4-1. S3 콜드부트 프로브 `scripts/s3_coldboot_probe.py` — **PASS(exit 0)**

격리 하네스(자기 tmp 소켓·tmp 팩·`CYS_NO_AUTOSTART=1` · PGID 그룹 종료)로 라이브 무접촉.

| 단계 | 재는 것 | 결과 |
|---|---|---|
| `[4]` | 콜드부트 뒤 **살아있지 않은 master 기록이 살아남는가** | **PASS**(살아남음) · 묘비 축도 PASS |
| `[5]` | `cys restore` / `--include-master` 동작 | 관측(하네스의 fakeagent 기동 실패는 설계된 값 — 판정축 아님) |
| `[6]` | 설치기 경로 `new-surface --agent` 가 **기록되는가** | **PASS**(master 엔트리 `agent=fakeagent`) · 대조군(무플래그) PASS |
| `[6b]` | 콜드부트 뒤 `restore --include-master` 가 **master 를 부활 대상에 넣는가** | **PASS**(「agent 미상」 제외 없음) |

★**함정 실증 1건(브리프 §2 이월 그대로 재발할 뻔했다)**: 첫 실행은 `[4]`·`[6]`·`[6b]` 가 전부
**FAIL** 로 나왔다. 원인은 코드가 아니라 **`target/debug/cys`·`cysd` 가 8월 28일 빌드본**이었던 것
(=우리 S3 커밋 이전 바이너리). `cargo test --bins` 는 **테스트 하네스**를 만들 뿐 평시 바이너리를
갱신하지 않는다. `cargo build --bins` 로 22:34 빌드본을 만든 뒤 재실행해 위 PASS 를 얻었다.
⇒ **프로브 앞에 반드시 `cargo build --bins`.** (이월 문구 「변이 빌드를 프로브 앞에 — 옛 target/debug
재기 = 거짓 KILLED」의 쌍둥이 함정이며, 이번엔 거짓 FAIL 로 나타났다.)

### 4-2. 적대 로케일 인코딩 스모크 — **7/7 PASS(exit 0)**

`python3 cysjavis-pack/bin/javis_phoenix_encoding_smoke.py`
· 적대 env = `PYTHONUTF8=0 LC_ALL=C PYTHONCOERCECLOCALE=0 PYTHONIOENCODING=cp949`
· 케이스: log_em_dash · journal_utf8_read · journal_corrupt_read · journal_roundtrip ·
  topology_read · roster_status_valid · desired_roster_read → `ran=7 pass=7 fail=0`

### 4-3. 뮤테이션 검산 — **4/4 KILLED(exit 0)** = 축이 공허하지 않다

`python3 scripts/phoenix_encoding_mutants.py`

| 뮤턴트 | 되돌린 수리 | 잡은 검사 | 판정 |
|---|---|---|---|
| M1 | `reconfigure` 제거 | phoenix 인코딩 스모크 rc=1 | **KILLED** |
| M2 | `open(encoding=)` 제거 | phoenix 인코딩 스모크 rc=1 | **KILLED** |
| M3 | 데몬 ENV 주입 제거 | `cargo test python_encoding_contract` rc=101 | **KILLED** |
| M4 | create 영속 제거 | `cargo test role_bearing_surface_is_persisted` rc=101 | **KILLED** |

### 4-4. ★이월 2건은 리베이스로 바뀌지 않는다 — 그대로 표기

- `set_meta` 로 절대경로가 덮이는 **전이 구간의 정합성은 무시험**이다(단순 Mutex 치환이라 위험은
  낮다고 보지만 재지 않았다).
- 격리 프로브는 **실제 재부팅이 아니라 데몬 프로세스 그룹 `kill -9` 근사**다. 실제 재부팅 실측은
  박사님 노트북 몫이다.

---

## 5. 자체 배포 체제 준비 (티켓 §1-4 · 신규 범위)

### 5-1. ⓐ 업데이트 endpoint 교체 + 서명 공개키 (커밋 `b88307c` → `e459d31`)

`src-tauri/tauri.conf.json` `plugins.updater`:

| 항목 | 이전(벤더) | 지금(우리) |
|---|---|---|
| `endpoints[0]` | `github.com/idoforgod/cys-terminal/releases/latest/download/latest.json` | **`github.com/oogisoogi/cys-terminal/releases/latest/download/latest.json`** |
| `pubkey` | 벤더 키(`39E60A70…` 라벨) | **master 생성 신규 키**(키 id **54FBA04AD0E0F49D**) |

- ⚠**endpoint 교체가 없으면 벤더 판이 우리 수정을 덮는다**(정책 §0 · 맥 사고 3회 계보).
- 키 형식 실측: base64 디코드 = `untrusted comment: minisign public key: 54FBA04AD0E0F49D` +
  키라인 42바이트·알고리즘 `Ed`, 주석의 id 와 키라인 파생 id 가 **일치**.
- **파생 배선(중요)**: `build.rs:161-176` 이 이 pubkey 를 **단일 SOT** 로 읽어
  `cysjavis-pack/trusted-keys.json` 의 부트스트랩 엔트리(`"pubkey": ""`)에 주입 →
  `OUT_DIR/pack_keyring.rs` 로 방출 → `src/packsig.rs` 의 팩 서명 검증이 그것을 쓴다.
  실측: 새 `pack_keyring.rs`(22:27:09 생성)에 신규 키가 들어갔고 `packsig` 게이트 초록.

★**`<<MASTER_PUBKEY>>` 표식은 빌드 중립이 아니다(실증)**: 표식이 든 커밋(`b88307c`)의 CI
`cargo test --lib` 이 **결정론으로 적색**이었다 —
`packsig::tests::embedded_keyring_parses_with_bootstrap_pubkey` →
`부트스트랩 pubkey 로드 실패: "pubkey base64 디코드 실패: Invalid symbol 62, offset 16"`
(`<` = 0x3C). ⇒ 표식은 **키를 기다리는 짧은 구간에만** 트리에 있을 수 있고, 그 구간의 CI 적색은
정상이다. master 의 키 도착 직후 `e459d31` 로 채워 해소했다.

★**key_id 라벨 정정 — master 판정으로 집행(커밋 `9375c1a`).** 키링·워크플로가 쓰던 라벨이
벤더 값 `39E60A702949D6C3` 이었다. **검증 자체는 성립했지만**(manifest 도 같은 리터럴을 쓰므로 조회가
맞고, minisign 은 서명에 박힌 키 id 를 **공개키 자신과** 대조하므로 우리 키쌍끼리는 통과한다)
**라벨과 실물이 어긋나면 사람이 「벤더 키가 신뢰된다」고 읽는다** — master 판정 = 결함.
⇒ 5곳을 실제 키 id `54FBA04AD0E0F49D` 로 동기했다:
`cysjavis-pack/trusted-keys.json`(키링 SOT) · `release.yml` `KEY_ID`(manifest.key_id 생산자) ·
`pack-release.yml` `KEY_ID` · `src/packsig.rs` 부트스트랩 조회 핀 · `src/bin/cys.rs` manifest 방출 핀.
라벨은 **조회 키**라 생산자와 소비자가 같은 값이어야 하므로 5곳을 함께 바꾸는 것이 유일한 정합 경로다.
실측: `cargo test --lib packsig` **16 passed / 0 failed** · `cargo test --bin cys pack_manifest_emits`
**1 passed / 0 failed**.

### 5-2. ⓑ 릴리스 워크플로 감사표 (우리 포크에서 돌기 위한 조건)

| 워크플로 | 트리거 | 필요한 시크릿 | 우리 포크에서 걸리는 것 | 판정 |
|---|---|---|---|---|
| `release.yml` | tag `v*` · dispatch | `TAURI_SIGNING_PRIVATE_KEY`(필수) · `APPLE_CERTIFICATE_B64` · `APPLE_CERTIFICATE_PASSWORD` · `APPLE_KEYCHAIN_PASSWORD` · `APPLE_SIGNING_IDENTITY` · `APPLE_ID` · `APPLE_PASSWORD` · `APPLE_TEAM_ID` · `GITHUB_TOKEN`(자동) | ①맥 잡의 인증서 반입 스텝에 **부재 시 우회 조건이 없다**(`if:` 가드 없음) → Apple 시크릿 없이 태그를 밀면 **맥 잡이 hard-fail** ②~~`env.SRC_REPO` 가 벤더 레포~~ → **교체 완료**(커밋 `9375c1a`) | ①은 **조건부 skip 게이트**로 hard-fail 만 제거(§5-7) — 발행하려면 시크릿이 여전히 필요 |
| `windows-build.yml` | branch `feat/windows-x64-dist`·`fix/**` · dispatch | 없음 | 없음 — NSIS 산출물은 `target/<triple>/release/bundle/nsis/cys_*_x64-setup.exe` 로 고정 수집 | ✅ 그대로 사용 가능(이번 미러 push 로 실제 기동됨) |
| `release-publish.yml` | dispatch 전용(`tag`+`release_bundle_sha256`+`confirm=PUBLISH`) | `GITHUB_TOKEN` | ~~`SRC_REPO` 벤더~~ → **교체 완료**(`:89`,`:114` + 사용례 주석 `:28`) | ⛔공개 승격 경로 — **박사님/master 게이트** |
| `pack-release.yml` | tag `pack-v*` | `TAURI_SIGNING_PRIVATE_KEY` · `GITHUB_TOKEN` | ~~`SRC_REPO` 벤더~~ → **교체 완료** · `gh release create -R $SRC_REPO` 가 이제 우리 레포 | ⛔팩 릴리스 경로 — 태그 push 는 master 게이트 |
| `ci-branch.yml` | branch `feat/**`·`fix/**` · dispatch | 없음 | `rebase/**` 미포함(§6) | ✅ 미러 브랜치로 해소 |
| `windows-health.yml` | branch `feat/**`·`fix/**` · tag `v*` · dispatch | 없음 | 〃 (트리거 확대는 검체 `H-CI-TAG-1` 이 금지) | ✅ 미러 브랜치로 해소 |

- **latest.json 생성**: 맥은 `createUpdaterArtifacts`(.app.tar.gz + .sig + latest.json), Windows 는
  `tauri-action` 이 같은 릴리스의 latest.json 에 `platforms.windows-x86_64` 를 **병합**한다
  (`release.yml:120-121`·`:802-806`). ⇒ **updater 가 보는 latest.json 은 릴리스 자산 1개**이고,
  §5-1 의 endpoint 가 그것을 가리킨다.
- **태그 규약**: 앱 = `v0.14.30`(우리 후속은 patch 증가 · upstream 재개 시 그 태그 merge 후 우리 번호가
  항상 ≥ upstream). 팩 = `pack-v*`(별도 레인).
- ⛔**이번 티켓에서 실제 태그 push·Release 발행·시크릿 등록은 0건이다**(master/박사님 게이트).

### 5-3. ⓒ H-SECRET-1 정리 — 발행 차단 게이트를 초록으로 (커밋 `78ac6e8`)

우리가 배포자가 되면서 `scripts/secret-scan.sh` 의 PUBLIC 발행 게이트가 우리 범위가 됐다.

| 측정 | pristine v0.14.30 | 우리(정리 전) | 우리(정리 후) |
|---|---|---|---|
| `scripts/secret-scan.sh --all` | **clean · 933파일 · exit 0** | **27건 발견 · exit 1** | **clean · 955파일 · exit 0** |

⇒ **27건은 전부 우리 포크가 들여온 것**(upstream 선재 0건)이다. 파일별 처방:

| 파일 | 건수 | 성격 | 처방 |
|---|---|---|---|
| `src/bin/cysd/named.rs` | 10 | ★**유일한 런타임 건** — 기본 보고자 매핑이 개인 홈경로 리터럴 2개 | `DEFAULT_MAP_REL`(홈 상대) + `dirs::home_dir()` 해소. **오너 기계 해소값은 종전과 글자 그대로 동일**. 홈 부재 = 빈 목록(이름을 지어내지 않는다) |
| docs 2종(pane-title-numbering impl·verdict) | 7 | 붙여넣은 CLI 출력 | `/Users/user` 더미로 치환 |
| `src/bin/cys.rs` | 4 | statusline 픽스처(통과 경로 · 매핑 의존 없음) | 더미 경로 |
| `src/bin/cysd/handlers.rs` | 2 | `usage_report_named` 검체 — **기본 매핑에 의존**한다 | cwd 도 `dirs::home_dir()` 에서 해소(리터럴로 두면 홈이 다른 러너에서 판별 실패 → 검체가 무측정이 된다) |
| `ui/src/wsusage.test.ts` | 3 | 오너 이메일 | `owner@example.com` |
| `src/bin/cysd/accounts.rs` | 1 | 주석의 토큰 접두 리터럴 | `sk-ant-…` 로 축약 |

★**제외 목록에 파일을 추가하는 길은 쓰지 않았다** — 그것은 계측기가 자기 판정 대상을 줄이는 것이고
H-SECRET-1 ⓒ(자기 면제 동결)가 명시적으로 금지한다.

★**정직 표기 — 이 커밋이 지우지 못하는 것**: 현재 트리는 깨끗해졌지만, **이미 공개된 기존 브랜치·
이력**(`origin/fix/phoenix-korean-windows` 등 · `named.rs` 만 9건 실측)의 같은 문자열은 그대로 있다.
이 저장소는 **PUBLIC** 이다. 이력에서 지우는 것은 force-push/이력 재작성 영역이라 **워커 금지선**이며
**박사님 게이트로 상신**했다(master 판정 2026-09-08). 앞으로의 유입은 이 게이트가 CI 에서 막는다.

### 5-4. ⓓ 버전 규약 — `0.14.30` 승계

`bash scripts/version-check.sh` → **✅ 8곳 일치: 0.14.30**(Cargo.toml · src-tauri/Cargo.toml ·
tauri.conf.json · ui/package.json · dist-win/cys-x64.wxs · Cargo.lock 2엔트리 등).
저장소에 `0.15.0` 앱 판본 잔존 **0건**(남은 `0.15.0` 문자열은 preflight 경계 검체와 curl_cffi 문서로
앱 판본과 무관). 리베이스 기점이 upstream 태그라 별도 bump 가 필요 없었다.

### 5-6. 배포자 전환 마감 — SRC_REPO 교체 (커밋 `9375c1a` · master 판정 집행)

발행 대상 상수를 우리 포크로 바꿨다: `release.yml:23` · `pack-release.yml:23` ·
`release-publish.yml:89,114`(+ 사용례 주석 `:28`) → **`oogisoogi/cys-terminal`**.
이유는 §5-1 과 같은 것 하나다 — **updater endpoints 와 발행 대상이 같은 레포여야** 우리 릴리스가
우리 앱에 닿는다. 엇갈리면 벤더 판이 우리 수정을 덮는다.

★**예외 1건(의도적으로 벤더를 가리킨다)**: `release.yml` 의 CRT 게이트 **음성 대조 픽스처**
`…/idoforgod/cys-terminal/releases/download/v0.14.0/cys_0.14.0_x64-setup.exe`. 이것은 배포 대상이
아니라 **불변 과거 산출물**(VCRUNTIME 감염 실물)로 게이트의 true-positive 를 증명하는 검체다.
우리 포크엔 v0.14.0 자산이 없어 우리 레포로 바꾸면 **404 로 그 게이트가 죽는다**. 그 자리에
「의도적으로 벤더를 가리킨다」는 주석을 남겨 다음 사람이 '고치지' 못하게 했다.

문법 검사: `actionlint` 부재 → PyYAML 파싱으로 대체 실측(3파일 파싱 OK · jobs 목록 확인).
⛔워크플로 실행·태그 push·Release 발행 = **0건**.

### 5-7. 맥 서명 시크릿 조건부 게이트 (r2 · master 지시)

`release.yml` 맥 레그는 `APPLE_*` 시크릿을 **전제**로 짜여 있어, 시크릿 없는 상태로 태그를 밀면
`import-macos-signing-certificate.sh` 가 잡을 통째로 죽였다(태그 레인 hard-fail). 프리플라이트 스텝
(`id: macsign`)이 7종 존재를 재고, 부재면 맥 전용 3스텝(인증서 반입 · 빌드/공증/정규화 · Gatekeeper
게이트)과 **수집·업로드 스텝의 맥 레그**를 skip 한다(Windows 레그는 무관하게 계속 간다).

★**이 게이트가 하지 않는 것을 명시한다**: **맥 없는 릴리스를 발행 가능하게 만들지 않는다.**
`scripts/release-verify.py` `REQUIRED_ASSETS` 가 DMG 2종을 요구하므로 공개 승격은 여전히 차단된다 —
그것이 설계 의도다(「macOS 업데이터가 죽은 묶음」의 통과 금지). 그래서 skip 경로는 조용하지 않다:
`::warning` + job summary 에 부재 시크릿 목록과 「이 태그는 공개 승격 불가」를 남긴다.

검증: PyYAML 파싱 OK(build 잡 25스텝 · 가드 4곳 확인) · 판정 셸은 러너와 같은 **bash 3.2** 에서
3분기(전부 존재 / 전부 부재 / 일부 부재) 실측 통과.

### 5-5. 추가 봉합 1건 — pyseal 센서스 (커밋 `ca4d65b`)

CI 실측(run 34230927538 · job macos-rust-pack): `FAIL ⓑ 참조 파일 집합 21개 고정 — 실측 22 ·
신규 ['cysjavis-pack/bin/javis_phoenix_encoding_smoke.py']`. 우리 S1 커밋이 들여온 파일이 **봉인 니들**
(바이트코드 쓰기를 끄는 env 변수 — 정확한 상수는 `test_pyseal_census.py` 의 `REF_NEEDLES` 가 정본)을
보유하는데 핀 목록에 없었다.
**봉인 점검 결과 = 새 python 진입점이자 강제점이 맞다**(`sys.executable` 로 자기 자식을 띄우고 그
자식 env 에 그 봉인 변수를 `"1"` 로 건다 · `:56`). 규약대로 근거 주석과 함께 등재했다.
· ★**이 보고서가 니들 상수를 리터럴로 적지 않는 이유**(2026-09-09 실측): 센서스는 확장자 13종
  **전수 스캔**이라 `.md` 도 센다 — 초판은 §5-5 에 그 상수를 인용했다가 **이 문서 자신이**
  참조 파일 집합을 22→23 으로 늘려 ci-branch 를 적색으로 만들었다(run `34241773714`).
  핀을 우회한 것이 아니라 **상수의 정본을 한 곳(`REF_NEEDLES`)으로 두고 문서는 가리키기만** 한다.
  (등재 경로도 규약상 유효하지만 그것은 팩 파일 수정 = 동봉 팩·번들이 바뀌므로, 이미 서명된
  번들과의 정합을 지키기 위해 docs 전용 처방을 택했다 — master 판정 2026-09-09.)
· 부기(로컬 전용 잡음): 이 센서스는 **파일시스템 walk** 라 `.gitignore` 를 따르지 않아 로컬
  `.briefs/`(추적 0건)를 신규로 센다. CI 체크아웃엔 없으므로 핀 값 **22** 가 정본이다.

---

## 6. CI — run id·경과 (실측)

★**함정 1건(구조적)**: `ci-branch`·`windows-health` 는 **`rebase/**` 를 push 트리거로 갖지 않는다**
(둘 다 `feat/**`·`fix/**` 전용, windows-health 는 추가로 tag `v*`). 즉 통합 브랜치를 `rebase/…` 로
밀면 **CI 가 자동으로 돌지 않는다**. master 판정 = **워크플로 무수정 + 동명 미러**
(`H-CI-TAG-1` 이 windows-health 트리거 확대를 금지하므로) → 같은 커밋을 `fix/rebase-v0.14.30` 으로
non-force 미러 push 한다. **향후 규약: 통합 브랜치 `rebase/vX` + CI 미러 `fix/rebase-vX`.**

| run id | 워크플로 | 대상 커밋 | 결과 | 내용 |
|---|---|---|---|---|
| `34230927538` | ci-branch(dispatch) | `f44101c` | ❌ failure | boot-health-full: `H-SECRET-1` 1건(pass 148/fail 1/skip 1) · macos-rust-pack: pyseal 참조 파일 핀 22≠21 |
| `34231730452` | ci-branch(dispatch) | `b88307c` | ❌ failure | 위 2건 해소 확인(**boot-health-full·nsis-hook-harness 초록**) · 남은 1건 = `<<MASTER_PUBKEY>>` 표식이 `cargo test --lib` 을 깨뜨림(§5-1) |
| `34230947584` | windows-health(dispatch) | `f44101c` | ✅ **success** | Windows 실기 레인 초록 |
| `34232768407` | ci-branch(push·미러) | `e459d31` | ✅ **success** | 적색 3건 봉합 후 첫 전건 초록 |
| `34234945537` | ci-branch(push·미러) | **`9375c1a`(최종)** | ✅ **success** | key_id·SRC_REPO 정정 반영본 초록 |
| `34232768251` | windows-health(push·미러) | `e459d31` | ✅ **success** | Windows 실기 레인 |
| `34234946110` | windows-health(push·미러) | **`9375c1a`(최종)** | ✅ **success** | 〃 — **최종 커밋에서 요구 2종(ci-branch·windows-health) 모두 초록** |
| `34232768385` | windows-build(push·미러) | `e459d31` | ✅ success | `fix/**` 트리거로 함께 기동(브리프 요구 항목 아님 — 부수 관측) |
| `34234945170` | windows-build(push·미러) | `9375c1a` | ⚠ a1 failure → a2 재실행 | 실패 지점 = `T4-14 이미지 잠금 업그레이드 회귀` 스텝의 **미가드 예외**: `The process cannot access the file 'C:\Users\runneradmin\AppData\Local\cys\cys.exe' because it is being used by another process` = 하네스 자신의 파일 잠금 경합. 같은 워크플로가 직전 커밋(`e459d31`)에서 초록이었고, 이 커밋의 diff(7파일)에 windows-build 가 참조하는 것이 **0건**(`KEY_ID`·`SRC_REPO`·`trusted-keys` 참조 0)이라 **플레이크로 판단**하고 재실행했다 |

⇒ **적색 3건은 전부 원인이 규명되고 봉합됐다**(H-SECRET-1 → `78ac6e8` · pyseal 핀 → `ca4d65b` ·
pubkey 표식 → `e459d31`). ★**검체를 고쳐 초록으로 만든 것은 하나도 없다** — 러너 헤더 계약 ④
(첫 행동은 원인 규명) 그대로, 세 건 모두 **원인 쪽**을 고쳤다.

---

## 7. 맥 빌드·서명

- 명령(08-28 선례·장기기억 `tauri-local-build-traps-cys` 준수):
  `unset NODE_OPTIONS` · `PATH=~/.cargo/bin:~/.bun/bin:$PATH` ·
  `bunx @tauri-apps/cli@2 build --bundles app --config '{"bundle":{"createUpdaterArtifacts":false}}'`
  (updater 서명키 hard-fail 회피 · dmg osascript 함정 회피 = `.app` 만)
- 서명: `codesign --force --deep --sign cys-local` → `codesign -dv` · `spctl` 첨부
- ⛔**설치(`/Applications/cys.app` 교체)는 master 몫**(백업 → ditto → canary).

### 7-1. 빌드 결과 (실측)

```
BUILD_START=2026-09-08T22:40:05+0900
BUILD_END  =2026-09-08T22:41:05+0900      (60초 — target/ 캐시 온난)
BUILD_EXIT =0
Finished 1 bundle at: target/release/bundle/macos/cys.app
```

| 항목 | 값 |
|---|---|
| `Info.plist` `CFBundleShortVersionString` | **0.14.30** ✅ |
| 사이드카 `cys --version` | `cys 0.14.30` |
| 사이드카 `cysd --version` | `[cysd] v0.14.30 cys-fix-w2-gen-0.14.4` |
| 동봉 팩 | `Contents/Resources/pack.tar.gz` · **2,774,399 B** · **464파일** |
| 산출 mtime | `Contents/MacOS/*` = **9월 8일 22:40~22:41**(stale 산출물 오판 차단 축2) |

### 7-2. UI 커스텀 임베드 확인 (strings 로는 확인 불가 — `ui/dist` 축)

Tauri 는 프런트엔드를 brotli 로 압축 임베드하므로 바이너리 `strings` 로는 UI 마커가 0건 나온다
(장기기억 `tauri-ui-embed-freshness-verification`). `ui/dist` 안의 우리 커스텀 마커 실재로 대조한다:
`cys-title-size` 3 · `cys-term-weight` 4 · `cys-title-color-role` 2 · `cys-menu-weight` 3 ·
`wsbar-font` 22 · **`btn-master-start` 4 · `btn-dept-master` 3**(=▶CEO·▶부서장 복원분이 번들에 실재).

### 7-3. 서명·검증 (실측)

```
codesign --force --deep --sign cys-local target/release/bundle/macos/cys.app   → exit 0
codesign -dv --verbose=4:
    Identifier=com.cysjavis.terminal
    Format=app bundle with Mach-O thin (arm64)
    CDHash=d8b53a3343f51b62d3840a83adc77d4e405d79f4
    Authority=cys-local
    Signed Time=Sep 8, 2026 at 22:41:30
    Sealed Resources version=2 rules=13 files=4559
codesign --verify --deep --strict → exit 0 (valid on disk)
spctl -a -vv → rejected · origin=cys-local  (exit 3 — 로컬 인증서라 정상. 08-28 과 동일)
```

⚠`spctl` 의 `rejected` 는 **결함이 아니다** — Developer ID 공증본이 아니라 로컬 `cys-local` 서명이라
게이트키퍼 평가에서 거부되는 것이 정상이며, 설치는 `ditto` 로 한다(정책 §5 경로 B).

---

## 8. 금지선·게이트 준수 (티켓 §4 · 워커 헌장 제0조)

| 금지선 | 상태 | 근거 |
|---|---|---|
| `/Applications/cys.app` 교체 · `~/.cys/pack` 수정 · init-pack · pack-merge | **미실행** | 작업 전 구간 라이브 무접촉. 시험·프로브는 격리 하네스(tmp 소켓·tmp 팩·`CYS_NO_AUTOSTART=1`)에서만 |
| force-push · 기존 브랜치 삭제 · upstream PR/이슈 | **0건** | push 는 `rebase/v0.14.30`(신규) + `fix/rebase-v0.14.30`(신규 미러) 둘뿐이고 전부 non-force |
| 서명 키쌍 생성 · 시크릿 등록 | **0건** | 키쌍은 master 가 생성 · 워커는 **공개키 문자열만** 받아 삽입. 개인키·시크릿 무접촉 |
| 릴리스 태그 push · GitHub Release 발행 | **0건** | §5-2 감사표만 작성 |
| 라이브 데몬·`~/.claude` | **무접촉** | 보고는 인박스 append-only 헬퍼로만 |
| 저장소 push(비가역) | **2단계 핸드셰이크** | ①master 지시 → ②워커 「실행 직전 확인 요청」 push(22:12:33) → ③재승인 `[master#69296c6e]` 원장 4요건 대조(nonce·surface:646·submitted=yes·시각 22:12:50 > ②) → ④실행 |

## 9. 남은 것 (master 판정·집행 대기)

1. ~~키링 `key_id` 라벨~~ → **해소**(master 판정 = 수정 · 커밋 `9375c1a` · 5곳 동기). §5-1
2. ~~릴리스 워크플로 `SRC_REPO`~~ → **해소**(master 판정 = 수정 · 커밋 `9375c1a` · 음성 대조 픽스처
   1건만 의도적으로 벤더 유지). §5-6
3. **맥 서명·공증 시크릿** — master 판정으로 **조건부 skip 게이트를 넣었다**(§5-7). 이제 시크릿이
   없어도 태그 레인이 죽지 않는다. 다만 ★**맥 자산 없는 태그는 여전히 공개 승격이 불가능하다**
   (`release-verify.py` REQUIRED_ASSETS 가 DMG 2종을 요구 — 설계된 차단). **실제 발행 전 APPLE_* 7종
   등록이 필요하다**(master/박사님).
4. **박사님 게이트** — 공개 이력에 남은 개인정보 27건(이력 재작성 = force-push 영역). §5-3
5. **master 집행** — 빌드 산출 `.app` 의 설치(백업 → ditto → canary) · 릴리스 태그 `v0.14.30`.
6. **측정 밖(정직)** — `set_meta` 전이 구간 무시험 · 프로브는 실제 재부팅이 아닌 `kill -9` 근사. §4-4
