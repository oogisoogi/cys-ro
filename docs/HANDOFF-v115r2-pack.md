# HANDOFF — cysr 1.1.5 6차 트랙 PACK (TICKET=v115r2-pack · 2026-09-23)

> 범위 = 결함 정본 `~/axdev/master/reports/cysr-115-2026-09-22/DEFECTS-2026-09-23.md` 의
> **D1·D2·D3·D4**. 기준 커밋 = `848b3f69`(5차 절단 = 태그 v1.1.5). 판번 bump 없음.

## 0. 한 줄 요약
갱신 설치가 **사용자가 손대지 않은 팩 파일까지 `.new` 에 가둬 두던 것**(D1)을 열고,
좌석이 읽는 프로필에 스킬을 등록하고(D2), CLT 없는 맥의 `python3` 판정을 고치고(D3),
좌석 `CLAUDE_CONFIG_DIR` 을 **스폰 합류점 한 곳**에서 못박았다(D4).

---

## 1. D1 — 갱신 시 사용자 소유 팩 파일 미적용 (차단)

### 무엇이 깨져 있었나
`decide_file_action` 의 user-owned 가지(`src/pack.rs`)는 **디스크 ≠ 임베드면 수정 여부를 묻지
않고 무조건 보존 + `.new` 병치**였다. 그래서 사용자 수정이 **0건인 기계에서도** 신판
디렉티브가 영구 미적용이었다(윈 1.1.3→1.1.5 `.new` 4건 · 맥 S2 1.0.2→1.1.5 동형).

### 무엇을 했나
| 축 | 수리 | 위치 |
|---|---|---|
| ⓐ 미수정 갱신 | 디스크 해시 == 설치 manifest 해시면 `FileAction::RefreshUser` — 신판 적용 + `<rel>.bak-<판번>` 백업 | `src/pack.rs` decide_file_action user 가지 |
| ⓑ 제품 파생본 | CEO 승격 사본(= `cp CEO_TEMPLATE.md MASTER_DIRECTIVE.md` · `bin/cys-dept:1005` 실측 = 바이트 동일 = 결정론)은 **신판 CEO_TEMPLATE** 으로 전진 + `.pre-ceo` 동반 갱신 | `ceo_derived_override()` + install_into 치환 |
| 혼합 설정 | `schedule.json`·`acl.json` 은 **더하기만 하는 병합**(디스크 값·순서 불가침 · vendor 신규만 말미 append) · `.pristine` 이 있으면 **3-way**(오너가 지운 항목은 되살리지 않는다) | `merge_user_json()` · `FileAction::MergeUser` |

- 백업 슬롯을 `.user` 가 아니라 **`.bak-<판번>`** 으로 둔 이유: `.user` 는 "내 수정본"의 자리이고
  부트 요약이 그 개수를 **사용자 커스텀 보존 건수**로 센다 — 수정 0건 파일을 섞으면 그 수치가 거짓이 된다.
- `.bak-<판번>` 은 매니페스트 비등재라 prune 불가침이고, `apply_pack_transactional` 의 저널
  side_paths 에 편입해 rollback 원자성을 지킨다.
- 병합을 **말미 append** 로 둔 이유: acl 은 "위에서부터 첫 매칭 승리"라 앞에 끼우면 오너가 확정한
  정책을 vendor 기본값이 가로챈다. 그리고 base(`.pristine/<rel>` = 마지막으로 적용한 vendor 원본)가
  있으면 **base 에 이미 있던 항목은 더하지 않는다** — 오너가 일부러 지운 deny 규칙이 갱신마다
  되살아나 정책을 뒤집는 것을 막는다. base 가 없으면(레거시) 2-way 로 폴백한다(그때는 '삭제'와
  '원래 없었음'을 구별할 재료가 없어 전달 쪽이 안전측).
- CEO 치환분은 매니페스트·pristine 에 **vendor 원본(MASTER) 해시**를 남긴다. 두 칸의 뜻이
  "마지막으로 적용한 **vendor** 판"이고, 승격본이 무엇인지는 CEO_TEMPLATE 칸이 이미 말하기 때문이다.
  치환본 해시를 넣으면 `.pre-ceo` 와 대조할 기준이 사라져 **첫 갱신 한 번만** 강등 백업이 전진하고
  그 뒤로 영원히 낡는다(시험 ⑤-b · 뮤턴트 D1-M7 이 그 축).
- 병합본의 매니페스트 해시는 **임베드 해시**를 그대로 쓴다 — 병합본 해시를 넣으면 다음 판이
  그것을 '미수정'으로 읽고 vendor 로 덮어 사용자 항목이 소실된다(재설치 멱등 시험 ⑤가 그 핀).

### 옛 판정을 지우지 않았다
`install_force_preserves_user_acl_and_parks_vendor_new`(W-ACL · 오너 승인 2026-08-01)는
"보존 + `.new` 주차"를 고정하고 있었다. **보존 축(①)은 그대로 두고** 전달 축(②)만 `.new` →
병합으로 다시 겨눴고, 옛 판정과 개정 사유를 그 시험 doc 에 병기했다.

### 시험
- `cargo test --lib d1_user_owned_refresh_merge_and_ceo_derivative` — 시나리오 4 + 재설치 멱등 ⑤.
- 뮤턴트 7종(가지 제거·해시 비교 뒤집기·백업 생략·CEO 파생 판정 뒤집기·병합 제거·**순서 함정 복귀**·
  **매니페스트에 치환본 기록**) — 하네스 = `scripts/d1_pack_refresh_mutants.py`(D2·D3·D4 뮤턴트 3종 동봉).
- ★라운드 중 스스로 잡은 결함 1건: 초판은 파생본 판정 기준을 **루프 중** `manifest` 에서 읽었는데,
  PACK_ALL 이 사전순이라 `CEO_TEMPLATE.md` 가 `MASTER_DIRECTIVE.md` **앞**에서 이미 신판 해시로
  전진해 있었다 — 판정이 **실제 설치에서 한 번도 발화하지 않는** 형상이었다. 시험 픽스처의 순서가
  실물과 달라 초록이 그것을 덮고 있었다. 픽스처를 실물 순서로 바꾸고 뮤턴트(D1-M6)로 박았다.

---

## 2. D2 — dept-by-chat 스킬 미등록 (차단)

### 실체
① `dept-by-chat` 이 preflight 의 **어느 심링크 목록에도 없었다** ②그리고 더 넓은 결함:
스킬 링크 검사(C26·C27·C29)와 보드 카탈로그 검사가 제 손으로 `$HOME/.claude*` 만 훑었다 —
좌석이 실제로 읽는 프로필은 `~/.cys/claude`·`~/.cys/claude-<부서>` 라, **스킬 53종이 좌석에서
한 종도 안 보였다**(914 축3 실측: `~/.cys/claude/skills` 폴더 자체가 없음).

### 수리
- `discover_skill_profiles()` 신설 — 훅 등록이 이미 쓰던 `discover_claude_settings()`(CLAUDE_CONFIG_DIR·
  CYS_ACCOUNT_DIR 포함) 단일 SOT 에서 프로필 디렉터리를 파생. 소비처 4곳 교체.
- `HARNESS_SKILLS` 에 `dept-by-chat` 편입.
- `javis_dept_request.py` 훅 안내문의 맨 `python3` → `sys.executable` 절대경로(D3 와 같은 축).
- `skills/dept-by-chat/SKILL.md` 본문의 `python3 "$D"` 8곳도 `"$PY" "$D"` 로 — 머리에서
  팩 해소기(`hooks/_lib.sh` `cys_resolve_py`)를 한 번 부르고 `${CYS_PY:-python3}` 로 폴백한다.
  (훅이 주는 「도구 = …」 줄과 스킬 본문이 **둘 다** 스텁을 피하게 만든 것 — 한쪽만 고치면
  모델이 읽는 쪽에 따라 결과가 갈린다.)

### 시험
`test_v115_dept.py :: D2SkillProfiles` 4건 + 뮤턴트 1(SOT 를 좁은 글로브로 되돌리기).
★`test_v115_dept` 는 **어느 CI 레인에도 등재돼 있지 않았다**(= 게이트가 아니었다) — 3완전 레인에 등재했다.

---

## 3. D3 — CLT 없는 맥의 python3 스텁 판정

A5 세션 env 게이트(`cys_export_bundle_py_env`)가 "PATH **어딘가에** 진짜 파이썬이 있는가"
(`_cys_path_py_darwin`)로 판정했다. 그 술어는 스텁을 건너뛰고 뒤 후보를 찾아 rc0 을 내는데,
좌석 셸은 언제나 **첫 일치**를 실행한다 — 그래서 비발동 + 좌석 `python3` = 스텁이었다.
→ `_cys_shell_py3_is_stub()`(command -v python3 **첫 해석**이 스텁인가 · 부재도 참) 신설·게이트 교체.
시험 = `test_py_resolver_clt_stub.py` 케이스 16(a 발동 / b 대조군 무접촉 / c 부재도 발동) + 뮤턴트 1.

---

## 4. D4 — 좌석 config dir 통일

### 정직 고지 — 「미주입 지점」은 **확정하지 못했다**
브리프가 지목한 기동 경로 3개를 소스로 전수 확인한 결과 **셋 다 주입한다**:
- `cys launch-agent`(unix) = `render_launch` 가 `CLAUDE_CONFIG_DIR="…" claude …` 인라인 접두를 만든다(`src/bin/cys.rs:10446~10470`).
- `javis_boot_node` = 승계·신규 모두 `cys launch-agent` 호출(`:1492`).
- `javis_formation._ensure_master_seat` = `cys new-surface --role master`(**빈 셸**) → `_boot_node` 입양 → 같은 launch-agent.
- GUI 버튼도 `cys launch-agent --role master`(`src-tauri/src/main.rs:4804·5263`).

자기 좌석 실측으로 그 접두가 실제로 먹는 것도 확인했다(`CLAUDE_CONFIG_DIR=~/.cys/claude`).

그러나 **접두를 타지 않는 좌석이 실재한다**는 것은 격리 데몬으로 실측했다(아래 시험 표):
`cys new-surface`(빈 셸 좌석)의 pane 은 수리 전 `CLAUDE_CONFIG_DIR` **0건**이었다. formation 이
master 자리를 확보할 때 정확히 이 빈 셸을 먼저 세우므로(`_ensure_master_seat`), 그 셸에서 claude 가
뜨는 형상이면 개인 프로필을 읽는다 — 914 S1 과 정합한다. 다만 **S1 이 실제로 그 경로였는지**는
부모 사슬 기록이 없어 여전히 【미측정】이다(macOS 는 남의 프로세스 env 를 안 보여 준다).

### 그래서 한 일 = 경로를 찾는 대신 **합류점을 못박았다**
`src/bin/cysd/state.rs` 의 pane 스폰 함수는 5경로(create RPC·launch-agent·boot·restore·schedule)의
**단일 합류점**이다(저장소 자신이 seat 토큰 주입 주석에서 그렇게 선언한다). 여기서
`CLAUDE_CONFIG_DIR = ${CYS_ACCOUNT_DIR:-$HOME/.cys/claude}`(= `cys::resolve_claude_config_dir`,
agents.json 템플릿과 같은 해소기)를 좌석 env 로 박았다 — 본부=`~/.cys/claude`, 부서=그 부서 계정 dir.
**호출자 env 오버레이보다 앞**이라 restore 가 기록한 원 계정 dir·Windows launch-agent 해소값이 이긴다.

⇒ 인라인 접두를 타지 않고 뜬 claude(좌석 셸에서 직접 실행 포함)도 이제 cys 프로필을 읽는다.

### 되돌아오는 부수효과(감춤 없음)
좌석의 **일반 셸**에도 이 env 가 선다. cys 좌석에서 개인용 claude 를 띄우면 이제 cys 프로필을
쓰므로 그 프로필의 로그인이 필요하다(맥 Keychain 은 config dir 경로 단위). cys 좌석 = cys 소유라는
기존 격리 방침과 같은 방향이지만, 박사님이 반대 방향을 원하시면 되돌릴 자리는 이 한 줄이다.

### B2(recap off)와의 관계
`C83` 은 **의도적으로** `~/.cys/claude*` 에만 기입한다(v115-review 발견 5 — 개인 프로필 무접촉).
∴ 본부 master 의 recap 미적용은 C83 을 넓혀서가 아니라 **D4 로** 닫힌다. C83 은 건드리지 않았다.

### 시험 — 구조 핀 + **격리 데몬 실측(전/후 대조)**
- `cargo test --bin cysd d4_spawn_confluence…` = 합류점 주입 존재 + 오버레이와의 선후 **구조 핀**.
- ★**실측**(격리 cysd + `cys new-surface --cmd 'env > …'` · 라이브 무접촉 · 상속 차단 `env -u CLAUDE_CONFIG_DIR`):

| 판 | 데몬 env | 좌석(pane) 실측 `CLAUDE_CONFIG_DIR` |
|---|---|---|
| **수리 전**(그 한 줄 제거 후 재빌드 = 대조군) | — | **0건**(부재 — 914 S1 형상 재현) |
| 수리본 | 기본 | `<HOME>/.cys/claude` |
| 수리본 | `CYS_ACCOUNT_DIR=<부서 계정>` | `<부서 계정>`(부서 프로필로 자동 갈림) |

  ⚠1차 대조군은 **내 셸의 `CLAUDE_CONFIG_DIR` 이 데몬에 상속돼** 오염됐다(값이 내 계정 dir 로 나왔다) —
  `env -u` 로 상속을 끊은 뒤에야 「0건」이 나왔다. 측정 입력부터 검증해야 한다는 같은 규율의 재발이다.
- ★이 실측이 D4 의 **미주입 지점도 좁혀 준다**: `cys new-surface`(= `javis_formation._ensure_master_seat`
  가 master 자리를 확보할 때 쓰는 **빈 셸** 경로)의 pane 은 수리 전 `CLAUDE_CONFIG_DIR` 이 **0건**이었다.
  그 셸에서 claude 가 뜨면(입양 실패·사람이 직접 실행) 개인 프로필을 읽는다 — S1 형상과 정합한다.
  다만 914 S1 이 실제로 그 경로였는지는 여전히 【미측정】(부모 사슬 기록이 없다).

---

## 5. 이월 (다음 사람이 먼저 할 것)
1. **D4 실측**: VM 에서 ①설치기 직후 본부 master ②갱신 뒤 복원 master ③부서장 좌석의
   `CLAUDE_CONFIG_DIR` 을 다시 재고, 그래도 `~/.claude` 인 좌석이 있으면 그 좌석의 **부모 사슬**을
   남겨라(어느 경로가 띄웠는지가 그 한 줄에 있다). 이번 수리는 그 경로가 무엇이든 덮지만,
   "무엇이었나"는 아직 모른다.
2. **ⓒ 오버레이 구조 전환**(디렉티브 = 시스템 소유 + `~/.cys/local/directives/*.local.md`)은
   1.1.6 이월 — 이번 판 금지(브리프 명시). ⓐⓑ 는 그 전환이 와도 그대로 상위 호환이다.
3. `.bak-<판번>` 누적 정리 정책 없음 — 판을 거듭하면 백업이 쌓인다(설계상 무해하나 다음 판에서
   보존 개수 상한을 정하는 게 낫다).
4. `agents.json` 은 user-owned 이지만 병합 대상에 **넣지 않았다**(브리프 범위 = schedule·acl).
   같은 병(어댑터 신규 키 미도달)이 있는지 다음 라운드에 확인하라.
5. **cysd 병렬 시험의 사전 적색**(내 변경과 무관 · 【관측】): 이 기계에서 `cargo test --bin cysd`
   를 **병렬**로 돌리면 `handlers::tests::w3_*` 계열에서 50건이 적색이 된다. `--test-threads=1`
   로는 **1013 전건 초록**이고, 실패의 대부분은 `ACL_ENV_LOCK` 의 `PoisonError` 연쇄(첫 패닉 1건이
   나머지를 물들인다)다. 그 첫 패닉이 무엇인지는 이번 라운드에 **못 붙잡았다**(재현할 때마다
   다른 테스트가 먼저 죽는다 · 기계 부하 동시 가동 중). 기준선 대조(848b3f69)도 미수행 —
   다음 사람이 깨끗한 러너에서 한 번 재라.
6. **`test_v115_dept` 레인 등재**를 이번에 했다 — 그 스위트가 앞으로 CI 에서 실제로 돈다.
   지금은 29건 초록이지만, 이 스위트가 러너에서 처음 도는 것이므로 **첫 CI 에서 환경 의존
   적색이 날 수 있다**(로컬 초록 ≠ 러너 초록). 그때 스위트를 레인에서 빼지 말고 그 케이스를 고쳐라.
