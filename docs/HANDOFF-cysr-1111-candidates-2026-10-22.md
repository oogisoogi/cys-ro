# HANDOFF — cysr-1111-candidates (1.1.10 검토가 「다음 판」으로 넘긴 후보 · 1.1.11 후보 가지 · 2026-10-22)

- 좌석: worker-4@surface:1554 · 가지 `fix/1111-candidates`
- 브리프: master spawn 04:18:49(원장 `kind:brief` · 본문 sha256 `60c31596…` = 브리프 파일 rstrip 해시 일치 실측)
- 기준: `1c2f3a14` → rebase `e80e8834`(master#b97afe79) → rebase **`7f15c059`**(master#80944f88 · 원장 대조 성립 둘 다) · **충돌 0**(두 번 다)
- push · 태그 · 판번 · 설치 · 발행 = 0 · rel/1.1.10 가지 쓰기 = 0 · 화면 흐름 변경 = 0(문면·판정만)

## 1. 방법

1. 출처 6종 Read — review-a HANDOFF §3(다음 판 후보) · review-b HANDOFF §2·§5 · 1.1.10 HANDOFF 4종(winqueue §7·§8 · minor §0·§2 · trash-harden §2·§3 · vendor §6). refresh-feed 404 는 브리프대로 뺐다(552 몫 · 7f15c059 에 들어감).
2. 후보마다 HEAD 코드 재확인 — 읽기 전용 하위 에이전트 3갈래(휴지통 · 큐/거버넌스 · 계정/갱신/시험환경). 결함으로 고른 항목은 **내가 코드를 다시 읽고** 재현 시험을 먼저 적어 빨강을 실측했다.
3. 결함(사용자가 겪음)만 수리: 재현 시험 → 수리 → 녹 → 뮤턴트 1 → 커밋 1. 개선·정책은 손대지 않고 §3 표에 「1.1.11 판단 대상」.

## 2. 수리 5건(각각 빨강 → 녹 → 뮤턴트 빨강 실측 · 항목당 커밋 1)

| # | 커밋 | 무엇이 틀렸나 | 사용자가 언제 겪나 | 시험(빨강 → 녹 · 뮤턴트) |
|---|---|---|---|---|
| W1 | `df25c44c` | 맥 `launch-agent` 가 claude 의 fullscreen 을 보면 「D5 env 가 settings tui 키 등으로 우회된 상태 … tui 키 제거」 라고 안내했다. Claude Code 는 `CLAUDE_CODE_DISABLE_ALTERNATE_SCREEN` 을 `tui` 보다 **먼저** 본다(`src/claude_tui.rs` `Hc()` 판독 · 33-37행) — env=1 이 닿았다면 tui 키로는 fullscreen 이 안 된다. 처방이 아무것도 바꾸지 못했다. | 맥에서 좌석 claude 가 fullscreen 으로 떠 WARN 을 본 사용자가 settings 의 tui 키를 지워도 그대로다 | `cys.rs` `alt_screen_notice_truth_table` 에 문안 핀 2(「tui 키 등으로 우회」 부재 · env 이름 + agents.json 안내 존재). 원 문안 = 적 · 뮤턴트(agents.json 안내 제거) = 적 |
| C4 | `fcae6004` | 휴지통 뿌리를 핸들로 못 연 까닭을 가리지 않고 전부 `trash_root_changed` → 화면 「휴지통 폴더가 미리보기 뒤 바뀌었습니다(다른 폴더·링크)」. 뿌리가 그냥 **지워진**(ENOENT) 경우도 바꿔치기로 말했다. | 휴지통 탭을 열어 둔 사이 격리 폴더가 지워지고(손으로·다른 도구) 미리보기·삭제를 누르면 「링크로 바뀌었다」는 거짓 경보 | `trash::tests::c4_a_deleted_root_is_reported_missing_not_changed`(명령 경로 + 미리보기 경로) · `ui/src/trashconfirm.test.ts` 문면 핀. 수리 전 = 적(`trash_root_changed`) · 뮤턴트(`root_missing` 항상 false) = 적 |
| C1 | `af5763c8` | 확인 문구 정규화가 화면(`resetconfirm.ts` `normalize("NFC")`)은 완전 NFC · 네이티브(lib `normalize_confirm_phrase`)는 한글 음절 합성만. 이름 하나 지우기의 요구 문구 = 디스크 이름 그대로라 분해형 라틴(`café`) 이름은 화면 통과 → 네이티브 `phrase_mismatch` **매번**. | Finder·손으로 만든 폴더처럼 NFD 이름이 휴지통에 있으면 그 항목은 GUI 에서 하나만 골라서는 영원히 못 지운다(여럿 골라 「삭제 N」 으로만 우회) | `factory_reset::tests::confirm_phrase_normalization_accepts_lookalikes` 에 분해형 라틴 2줄. 수리 전 = 적(`"cafe\u{301}"` ≠ `"café"`) · 뮤턴트(정규화를 항등으로) = 적 |
| R8 | `c9ca20e1` | `javis_dept_request.py` `_move_to_trash` 가 휴지통 항목을 `formation-%Y%m%d-%H%M%S`(지역 시각)로 지었다. 데몬 `stamp_epoch_from_name` 은 마지막 `-` 조각만 보는데 그것이 6자리라 두 형식(epoch 초 · `%Y%m%dT%H%M%SZ`) 어디에도 안 맞음. | 편성 원장 청소가 휴지통에 넣은 항목은 휴지통 탭에서 「들어간 시점: 알 수 없음」 · 「오래됨」 표시가 영원히 안 붙는다 | `test_dept_b11_lock` `TestRequestSide.test_1111_r8_trash_entry_name_carries_a_stamp_the_daemon_reads`. 수리 전 = 적(`formation-20261022-043618`) · 뮤턴트(gmtime→localtime · KST 9시간 어긋남) = 적 · `trash.rs` `r2_old_is_read_from_the_name_stamp_in_both_formats` 에 formation 이름 핀 1줄(교차 언어 결박) |
| B4 | `67f862df` | `cysd accounts.rs` `report_outside_at` ② 가 프로필을 고를 때 어휘 일치(d/projects 아래)와 정규화 일치(canonicalize(d)/projects)를 **한 회차**에 받았다 → `~/.claude-acct2 → ~/.claude` 같은 통째 별칭이 열거(read_dir · 순서 비결정)에서 먼저 나오면 `~/.claude/projects/…` 보고가 별칭으로 잡힘. | 프로필 폴더를 통째 별칭으로 둔 기기에서 기본 계정의 cys 바깥 claude 사용량이 사용량 칸에 안 뜨거나(별칭에 신원 파일 없음 = identity_unresolved) 프로필 표기만 별칭으로 뜬다. 다른 계정에 숫자가 붙지는 않는다 | `accounts::tests::outside_profile_pick_prefers_the_lexical_dir_over_a_whole_dir_alias`. 수리 전 = 적(별칭 선택) · 뮤턴트(첫 회차도 정규화 허용) = 적 |

수리 방식 요약
- W1: 문안 1개(맥 분기). 「env 가 이 claude 에 닿지 않은 상태 · Claude Code 는 이 env 를 tui 보다 먼저 본다 · agents.json claude env 에 이 키가 0 등 다른 값으로 적혀 있는지 확인(사용자 값이 있으면 cys 는 기본값을 넣지 않는다 — 그 경우에만 settings tui 키가 판정에 참여)」. 근거 = `lib.rs` `inject_claude_alt_screen_default_for`(키 부재 시에만 주입 · 사용자 값 불가침) · `d5_gate_for_os("macos") = true`.
- C4: 새 코드 `trash_root_missing`(`R_ROOT_MISSING` · `ROOT_MISSING_MSG`) + `NamesOutcome::RootMissing`. `io::ErrorKind::NotFound` 만 부재로 가른다(그 밖 — 심링크·디렉터리 아님·권한 — 은 종전 `trash_root_changed`). 자리 4 = 미리보기 순회 전 · 순회 후 대조 · 명령 진입(`delete`) · `execute_one` 겉면. 윈 `RootDir::open` 은 `root_sane` 검사 전에 `symlink_metadata` 로 부재를 NotFound 로 먼저 낸다. 화면 = 「휴지통 폴더가 없어졌습니다(지워짐) — 지우지 않았습니다.」 · 행동 안내 `none`(다시 미리보기를 해도 같은 결과라). **멈추는 쪽은 종전과 같다**(지우지 않음).
- C1: `normalize_confirm_phrase` 의 첫 단계 = `icu_normalizer::ComposingNormalizerBorrowed::new_nfc().normalize(input)`. `compose_hangul`(직접 구현)은 쓰는 곳이 없어져 지웠다. src-tauri `trash_normalize_phrase` 주석의 「한계」 문단을 갱신. 공장 초기화 CLI 확인 문구도 같은 함수라 같은 관용을 얻는다(화면이 이미 받던 것까지만 넓힘).
- R8: 스탬프 `time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())`. 팩 쪽이라 옛 바이너리(1.1.8/1.1.9 데몬)도 이미 읽는 형식이다. `.producer` 표식 · `trash.rs:275` 생산자 목록 기재는 이번 범위 밖(§3 개선).
- B4: 선택 본문을 순수 함수 `pick_outside_profile(dirs, raw, canon)` 로 뽑고(시험이 열거 순서를 고정하려고) 회차를 둘로 — 어휘 일치 전부 → 없을 때만 정규화 일치. 그 밖의 판정(밖 링크 거절 · 상대경로 · ③ 모호성 검사)은 그대로.

★지시 없이 내린 판단 1건 — C1 의 **`icu_normalizer` 직접 의존 승격**: 이미 `Cargo.lock` 에 2.2.0 으로 전이 존재(`idna_adapter` 경유) · `default-features = false, features = ["compiled_data"]`(기본 feature 는 lock 에 없는 `utf16_iter` 를 끌어와 `--offline` 실패 — 실측) · 새 크레이트 내려받기 0 · `Cargo.lock` 변화 = 의존 간선 1줄. 관례 = `Cargo.toml` 의 flate2/tar 「직접 의존 승격」 주석. 종전 주석의 「★의존성 0 · 한글만」 설계를 뒤집는 것이라 적는다. 되돌리려면 화면 쪽을 한글 합성만으로 좁히는 길이 있으나 그러면 그 항목은 화면에서도 못 지운다(사용자 손해) — 그래서 네이티브를 넓혔다.

## 3. 후보 전체 분류표

분류: **결함** = 사용자가 겪는 잘못된 동작·문면 / **개선** = 사용자 영향 0(기록·진단·시험·방어)이거나 새 기능 / **정책** = 오너·master 판단 · 화면 흐름 · 보안 / **실기** = 윈 실기 없이는 판정 불가.
출처 약호: Ra = review-a HANDOFF §3 · Rb = review-b HANDOFF §2·§5 · WQ = winqueue · MI = minor · TH = trash-harden · VE = vendor.

| # | 출처 | 후보 | 재확인 결과(HEAD) | 분류 | 처리 |
|---|---|---|---|---|---|
| W1 | WQ §7 | 맥 fullscreen WARN 「tui 키 등으로 우회」 문안 | 실재 · env 가 tui 보다 먼저(`claude_tui.rs:33-37`) | 결함 | **수리 `df25c44c`** |
| C4 | Ra C(trash.rs:1715) | 뿌리 삭제를 「다른 폴더·링크로 바뀜」으로 | 실재 · 4자리 같은 붕괴 | 결함 | **수리 `fcae6004`** |
| C1 | Ra C(main.rs:5142 · factory_reset.rs:2050) | 화면 NFC ↔ 네이티브 한글만 | 실재 · 디스크 이름이 NFD 일 때만 | 결함 | **수리 `af5763c8`** |
| R8 | Rb R8 · §5-4 | formation-* 나이 미표시 | 실재 · 생산자는 넷째(`javis_dept_request.py:1409`) | 결함 | **수리 `c9ca20e1`**(스탬프만) · `.producer` 표식·생산자 목록 기재 = 개선(1.1.11 판단 대상) |
| B4 | Ra B(accounts.rs:1455) | 통째 별칭 첫 일치 귀속 | 실재 · 이 기기 설정에는 해당 없음(acct2 는 실 디렉터리 · projects/ 만 링크) | 결함(희소) | **수리 `67f862df`** |
| A1 | Ra A(governance.rs:6365) | 좌석 닫힘 큐 폐기 토스트에 좌석 번호 | payload 에 role 없음 · 화면은 이미 `seatNo` 를 계산함 · 1줄 + 서명 변경 | 개선 | 1.1.11 판단 대상 |
| A2 | Ra A(placeholderclose.ts:55) | 윈 자리표가 ConPTY 재배치 뒤 안 닫힘 | 기제 판독만 · 맥에서 재현 불가(ConPTY 가 soft wrap 인지 hard CRLF 인지는 윈 바이트 사본으로만) · 실패 방향 = 안 닫힘(안전) | 실기 | 1.1.11 판단 대상 · 윈 실기 확인점(88열 미만 리사이즈 뒤 `placeholderScreenLines`) |
| A3 | Ra A(governance.rs:10010) | `layout_why` 진단이 틱과 다른 마커 · 자리표+선택행에서 `marker_row_text` 오표기 | 둘 다 실재(⒜ 진단 `pick_marker_for_screen` ↔ 틱 `observe_prompt_ext:9477-9483` 의 커서행 우선 ⒝ `readiness.rs:1467-1473` 자리표 면제 누락). 보이는 곳 = `queue-blocked.json` 만(UI·CLI 무표시 · WIN-FIELD 절차의 운영자) | 개선(진단 전용 · 사용자 영향 0) | 1.1.11 판단 대상 — 윈 축2 사본 수리 티켓 전에 고치면 그 진단이 맞는 규칙을 가리킨다(권고) |
| A4 | Ra A(state.rs:7967) | `parked_overflow` 묘비 surface 가 나가는 좌석 | 실재 · 소비자 0(`javis_mission.py` 는 sha 불일치로 무해 · `javis_snapshot.py` 는 origin 만) · 항목별 출처가 ParkedQueue 에 없음(배치 하나에 from_surface 1개) | 개선(기록) | 1.1.11 판단 대상 |
| B1 | Ra B(cys-dept:365) | `CYS_TRASH_STAMP` 검증이 teardown 뒤 | 그 변수는 시험·검증된 값 전달만 씀(제품 경로 설정 0 — grep 실측) | 개선(시험 경로) | 1.1.11 판단 대상 |
| B2 | Ra B(javis_org.py:708) | `isdigit()` 가 유니코드 숫자 통과 | 실재(`'²'.isdigit()` True 실측) · 손으로 env 를 줄 때만 | 개선(시험 경로) | 1.1.11 판단 대상 — `re.fullmatch(r"[0-9]+", ts)` 1줄 |
| B3 | Ra B(test_update_publish.py:76) | hdiutil detach 재시도 `-force` 없음 · rmtree | 시험 하네스 전용(release.yml:931 · pack-release.yml:684 의 매체 탐침) | 개선(시험) | 1.1.11 판단 대상 |
| C2 | Ra C(dirat.rs:137) | 하위 객체 동시 소실 → partial · `.deleting-*` 잔여 · 안내 「새 미리보기」 | 설계 판단(잔여 삭제 경로를 만들지 · 문구를 바꿀지) | 정책 | 1.1.11 판단 대상 |
| C3 | Ra C(trash.rs:1741) | `producer_active` 거부 원장의 boundary 가 `.producer` 고정 | 실재 · 원장(`DELETE-LEDGER.jsonl`)과 미리보기 응답 `refused[].boundary` 에만 — 화면은 그 칸을 안 그림(`main.ts:1775·1808`) | 개선(감사 기록) | 1.1.11 판단 대상 |
| C5 | Ra C(main.ts:1965 · main.rs:5175) | 네이티브 확인 미발급(mutex 오염) → 「삭제」 무소식 종료 | 실재 · 도달 = 다른 곳의 panic 이 그 잠금을 잡은 채 났을 때뿐(맵 연산 3개는 panic 없음) | 개선(방어 · 도달 곤란) | 1.1.11 판단 대상 — `ready()` 에 `confirm_nonce` 가드 + `refuse("confirm_unbound")`(권고) |
| D1 | Ra D(refresh-feed.yml) | 봉투 읽기 실패를 404 와 같이 녹 | — | (제외) | 브리프대로 뺌 · 7f15c059 에 수리 포함(552) |
| D2 | Ra D(release.yml · pack-release.yml) | 발행 창 동안 `update.binary_too_old` 상담 신호 중복 제거 없음 · 판번 안 올린 가지의 수동 release.yml 실행 적 | 신호 생성 = 바이너리(1.1.8/1.1.9 에도 있음) · 기록 = 팩 `javis_counsel.py write_signals`(중복 제거 없음 · 2MB 상한) · 로컬 화면 소비자 0 · 상담 송신기가 같은 줄을 count 로 접음(설계 문서) · 하루 ~4줄 | 개선(소음) | 1.1.11 판단 대상 — 고친다면 **팩**에서(옛 바이너리에도 닿는다) · `test_javis_counsel` 에 시험 |
| D3 | Ra D(style.css:506) | 메뉴 80% 에서 화면 설정 팝오버 8px | 박사님 「절반」 지시의 결과 | 정책 | 1.1.11 판단 대상 |
| D4 | Ra D(#topbar) | 윈 좁은 폭 상단 넘침 | WIN-FIELD MENU-1~3 이 다룸 | 실기 | 윈 실기 |
| R5 | Rb R5 · §5-1 | 지침 바이트 래칫이 원작자 재기준선으로 느슨 | 시험 전용 · 사용자 영향 0 · review-a·b 가 7f15c059 에 다 들어왔으므로 이제 조일 수 있는 시점 | 개선(시험) | 1.1.11 판단 대상 |
| R9 | Rb R9 · §5-3 | 윈 생존 판정 불가 → `open` 표식 항목 영구 차단 | 윈 삭제 꺼짐이라 지금 0 · `trash_win_validated` 를 켜는 판의 선결 | 정책(그 feature 켜는 판의 선결) | 1.1.11 판단 대상 |
| Rb-2 | Rb §5-2 | 허락 요청 OS 알림(원작자 R2)을 켤지 | 1.1.9 동작으로 되돌려 둠(Q2=B) | 정책 | 1.1.11 판단 대상 |
| Rb-3 | Rb §5-3 | 윈 휴지통 삭제 켜기 선결 셋(R9 · 확인창 문장을 `delete_supported` 로 · reap 자동 S8) | — | 정책 | 1.1.11 판단 대상 |
| Rb-5 | Rb §5-5 | 저장소 뿌리의 추적 파일 `1` | 원작자 잔재로 보임(review-b 판독) | 정책(지울지) | 1.1.11 판단 대상 |
| WQ-1 | WQ §7 | 맥 = 윈 모델(D5 env 대신 settings `tui:"default"` 선기록) | 기동 모델 변경 · 맥 함대 실기 필요 | 정책 | 1.1.11 판단 대상 |
| WQ-2 | WQ §7 | 축2 윈 화면 사본 → 픽스처 → 레이아웃 규칙 수리 | 윈 사본이 선결 | 실기 | 윈 실기(WIN-FIELD 절차) — A3 를 먼저 고치면 진단이 맞는 규칙을 가리킨다 |
| WQ-3 | WQ §7 | 자리표 「기동 직후 기준선 대비 증가분」 판정 | A2 실기 결과에 달림 | 실기 | 윈 실기 뒤 |
| WQ-4 | WQ §7 | ⑷ 거부 규칙을 진짜 자기 선언(`cs == sid`)으로 좁힐지 | 보안 판단 | 정책 | 1.1.11 판단 대상 |
| WQ-5 | WQ §8 | 휠이 타이핑 가드를 갱신(스크롤 중 3초 직접 send 보류) | review-a R1(`b75d8b25`)이 대체화면 휠을 가드에서 뺌 — 7f15c059 에 포함 | (종결) | 이미 수리됨 |
| WQ-6 | WQ §8 | cursor 모드(옵트인) 휠 = 화살표 → 사람 초안으로 셈 | 의도된 보수(그 옵트인 사용자에게 축1 정지가 남음) | 정책 | 1.1.11 판단 대상 |
| MI-3·6·7 | MI §0 | ③ 윈 `powershell -Command` 판정 · ⑥ runtime-seal 「추가 1」 · ⑦ dept-awakening-seed WARN | 셋 다 「윈 실기 필요」 | 실기 | 윈 실기 |
| MI-cysd | MI §2 | `alert_route` drill 1건 부하 흔들림(원인 미판독) | 이번 전건에서 재발 여부 §4 참조 | 개선(시험) | 1.1.11 판단 대상 |
| TH-1 | TH §3 | M1-B: WebView 밖 OS 네이티브 확인창 | 확인 단계 +1(체감 변화) · 선행 = CSP·원격 로드·devtools 출하 설정 실측 | 정책(화면 흐름) | 1.1.11 판단 대상 |
| TH-2 | TH §3 | `trash.rs`·`factory_reset.rs` 윈 경로 핸들 결박 | 안정 std 에 openat·file index 없음 | 개선(API 대기) | 1.1.11 판단 대상 |
| VE-1 | VE §6-1 | TOAST 축 스위치(`ALERTS_QUIET` · `ALERT_PROSE_QUIET`)를 켤지 | 박사님 화면 정책 | 정책 | 1.1.11 판단 대상 |
| VE-2 | VE §6-2 | 복원 카드(`maybeShowRestoreBrief`)가 TOAST 축 밖 | 스위치를 켤 때 함께 | 정책 | VE-1 과 함께 |
| VE-3 | VE §6-3 | About 「based on cys 0.14.51」 표기 | 어디에도 없음(새 기능) | 개선(새 기능) | 1.1.11 판단 대상 |
| T1 | VE §6-4 | `test_dept_team_token` 18 적 | 제품 결함 아님 — cys pane 안에서 돌리면 앱이 내보낸 `CYS_CYS_BIN` 이 시험의 가짜 cys 보다 앞서 실 설치본(team-token 휴면)이 답함. `env -u CYS_CYS_BIN -u CYS_CYSD_BIN` 이면 23/23 녹(하위 에이전트 실측) · CI 는 그 변수가 없어 녹 · 형제 시험(`test_team_create_u16.py:109` · `test_dept_notice_lane.py:45`)은 이미 pop 함 | 개선(시험 환경) | 1.1.11 판단 대상 — `make_env` pop 목록에 2개 추가(권고 · 팩 전건 적 18 이 사라진다) |
| VE-5 | VE §6-5 | S8 휴지통 · TOAST 래퍼 · HUD 다리 윈 실기 0 | — | 실기 | 윈 실기 |
| Ra-D2b | Ra D | 판번 안 올린 가지의 수동 release.yml 실행 「Verify signed pack」 적 | 태그 실행은 판번을 먼저 올리므로 녹 | 개선(CI) | 1.1.11 판단 대상 |

## 4. 시험 전건(이 가지 최종 트리 `67f862df` · 맥 · 2026-10-22)

| 묶음 | 결과 | 비고 |
|---|---|---|
| `cargo test --offline -p cys-terminal` | lib **1100** 통과 · `--bin cys` **627** · `--bin cysd` **2701** · **실패 0**(ignored 2 · 9) · rc 0 | 기준 7f15c059 대비 신규 = cysd +2(C4 · B4) · lib·cys 는 기존 시험에 단언 추가 · MI 의 `alert_route` drill 흔들림 재발 0(고부하 load 5~6 에서) |
| ui `bun test` | **3260 pass · 0 fail** · 85 skip | |
| ui `bunx tsc -p tsconfig.check.json` | rc 0 | (`npx tsc` 는 이 작업트리에 typescript 미설치로 못 돌았다 — package.json 의 `typecheck` 스크립트대로 bunx) |
| `sh scripts/win-typecheck.sh` | **rc 0** · 오류 0 · 경고 65 | master#80944f88 지시 · C4 가 윈 cfg(`RootDir::open` 비유닉스 갈래)에 닿음 |
| 팩 py 관련(격리 env `env -u CYS_CYS_BIN -u CYS_CYSD_BIN CYS_PACK_DIR=$(mktemp -d)` · CI 꼴) | `test_dept_b11_lock` 13 OK · `test_dept_request` 112 OK · `test_trash_old_marking` PASS · `test_producer_marker` PASS · `test_d1_4_orphan_reap` 21 OK · `test_dept_name_guard` 1회째 적 1 → 2회째 75 녹 | name_guard 의 적 1 은 이름을 못 적었다(출력 꼬리만 봄) · 이번 수리는 그 시험이 보는 경로를 안 건드림(`git diff 7f15c059 -- cysjavis-pack` = `javis_dept_request.py` 스탬프 1줄 + b11 시험) · 기존 HANDOFF 들이 같은 파일의 경쟁 승자 타이밍 플레이크를 기록 |
| 릴리스 시험(Cargo.toml 의존 1줄 변경분) | `test_version_sot_mutation` rc 0 · `test_ci_branch_cysd_step` rc 0 | |
| 팩 py 189종 전건 | **미실행** | 수리가 팩에 닿은 곳은 `javis_dept_request.py` 1줄 — 그 모듈을 부르는 시험(dept_request · b11 · name_guard)만 돌렸다 |
| src-tauri 크레이트 시험 | **미실행** | 주석만 변경(§5) |

## 5. 남은 것·한계(정직)

- 윈 실기 0. C4 의 윈 `RootDir::open` 갈래는 `sh scripts/win-typecheck.sh` **rc 0**(오류 0 · 경고 65)로 타입만 확인했다. 내가 만진 파일의 윈 경고는 `trash.rs:1032 execute_one never used` 1건 — 그 함수의 속성·호출자는 이번에 안 바꿨다(본문의 거부 코드 1줄만) · 기준 `7f15c059` 에서도 같은 함수가 같은 속성(`#[allow(clippy::too_many_arguments)]` 만)이라 선존 경고로 판독(기준 트리 win-typecheck 는 다시 돌리지 않았다).
- C1 의 src-tauri 크레이트 시험은 미실행 — 그 크레이트는 주석만 바뀌었고 판정은 lib `normalize_confirm_phrase` 를 그대로 부른다(lib 시험이 덮음). 화면(JS `String.prototype.normalize`)과 ICU4X 2.2 의 유니코드 판이 다르면 아주 새 문자에서 갈릴 수 있다(실패 방향 = 지우지 않음).
- R8: 이미 휴지통에 들어간 옛 이름 `formation-YYYYmmdd-HHMMSS` 항목은 그대로 「알 수 없음」(삭제·목록은 종전처럼 됨). 옛 이름까지 읽히게 하려면 데몬 파서에 지역 시각 형식을 더해야 한다(DST 경계 · 손으로 만든 같은 꼴 폴더도 날짜가 붙음) — 하지 않았다.
- B4: 시험 홈을 정규화 경로로 두지 않으면(맥 `/var → /private/var`) 결함이 가려져 원 코드에서도 녹이 났다 — 처음 쓴 시험이 그랬고 고쳐서 빨강을 냈다.
- 분류표의 「재확인 결과」 중 하위 에이전트가 읽은 파일:줄은 HEAD(1c2f3a14 기준 읽기)값이다 — 수리한 5건은 내가 직접 다시 읽었다. 그 밖의 행은 다음 판 착수 시 재측정.
