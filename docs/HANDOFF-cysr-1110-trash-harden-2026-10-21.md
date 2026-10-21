# HANDOFF — cysr 1.1.10 휴지통·초기화 경로 결함 4건 설계급 수리 · TICKET=cysr-1110-trash-harden · 2026-10-21

가지 `fix/1110-trash-harden`(출발 = `rebase/v0.14.51` 의 `2b2179b7` → **rebase 후 기준 `8d81d780`**) · 작업트리 `~/cys-terminal-src-wt/1110-trash-harden` · 워커 worker-7(surface:1543) · push 0.
출처 = TICKET=cysr-1110-vendor(540) 의 codex 1R REVISE(병합 `ba38b6aa` 대상) 중 B2·M1·M3·M4. 540 이 B1·M2 를 고치는 중이라 그 둘은 이 가지에 없다.

## 0. 한눈에

| 결함 | 원인(출발 커밋 기준) | 수리 커밋 | 수리 전(RED 실측) → 후 |
|---|---|---|---|
| **B2** blocking — 휴지통 삭제 TOCTOU | 뿌리를 RPC 진입에서 한 번만 검사(`root_sane`)하고 배경 집행이 `root.join(name)` 을 단계마다 다시 해석 | `e5ce97b8` · codex 1R 반영 `53985c6c` · 2R 반영 `cd390154` | 뿌리를 바깥 심링크로 바꿔치면 **바깥 동명 디렉터리를 지우고도 `deleted_verified`**(제거 직전) · 바깥을 봉인 rename(봉인 직전) → 바깥 0 바이트 변화 |
| **M3** major — `.producer` 비원자 | 공유 파일 하나를 읽고-바꿔쓰기 · 판독 실패가 `None` 으로 접혀 남의 `open` 을 덮음 | `e5ce97b8`(쓰기 py·bash · 판독 Rust) · `53985c6c`(공장 초기화 쓰기) | 남의 열린 창이 내 `complete` 로 덮임 → 생산자마다 자기 파일 · 판독은 전부 모아 보수 판정 |
| **M4** major — 공장 초기화 rename | 확인창 대기 중 부모 경로 재검증 없이 `rename(path)` | `0d74fd79` · codex 1R 반영 `53985c6c` · 2R 반영 `cd390154` | `~/.cys` 를 바깥 심링크로 바꿔치면 **바꿔 넣은 쪽 `pack` 을 격리** → 계획 때 부모 신원 대조 · 어긋나면 이동 0 |
| **M1** major — 타이핑 확인 IPC 비결박 | 타이핑 확인이 화면에만 · `trash_delete` 가 `confirm_id/names/digest` 만 받음 | `668aee8f` · codex 1R 반영 `53985c6c` | 모달 없이 삭제 호출 가능 → 앱 네이티브 단회 확인 + 문구 재측정 뒤에만 데몬 전송(체감 변화 0 · A안) |

## 1. 무엇을 어떻게 고쳤나

### B2 — 휴지통 집행을 **뿌리 디렉터리 핸들**에 묶었다(`src/bin/cysd/trash.rs` · 공용 leaf `src/dirat.rs`)
- `RootDir`: 뿌리를 `O_DIRECTORY|O_NOFOLLOW` 로 한 번 연다. 미리보기 순회 **전후**의 뿌리 (dev, ino) 가 같아야 확인(`Confirm.root_id`)을 발급한다(다르면 잡 `Failed` · 새 코드 `trash_root_changed`).
- `trash.delete` RPC 진입에서 뿌리를 핸들로 열어 `root_id` 와 대조 → 다르면 의도 기록·집행 스레드 없이 거부. 집행 스레드는 그 핸들만 쓴다(경로 재해석 없음).
- 항목 신원 확인·봉인 rename·제거·사라짐 검증 = 전부 핸들 기준(`fstatat`·`renameat`·`openat`·`unlinkat`).
- 제거 순회(`cys::dirat::remove_tree_at`): 연 객체가 미리보기 항목 신원이 아니면 0 바이트 · 하위 디렉터리는 `O_NOFOLLOW` 로 열고 연 객체 신원 = 직전 lstat 신원 · 장치가 바뀌면 멈춤 · 뿌리와 **하위 디렉터리 모두** rmdir 직전 이름 재대조(하위는 codex 2R ①).
- ★codex 1R ①(C-R1 인증 집합 = 제거 집합): 봉인 뒤 대조 순회(`certify_entry_ids`)가 노드의 실제 (dev, ino) 를 모으고, 제거는 **그 집합에 든 노드만** 지운다. 대조 뒤 끼어든 객체(밖에서 옮겨 넣은 트리·새 파일)를 만나면 멈춘다(`partial` · `removal_error`).
- readdir 오류와 끝을 errno 로 구별, `closedir` 실패 전파(codex 1R ④).

### M3 — 생산자별 표식(`javis_org.py` · `cys-dept` · `factory_reset.rs` · 판독 `trash.rs`)
- 세 생산자가 모두 **자기 pid 의 파일 `.producer-<pid>` 만** 원자 교체로 쓴다. 남의 표식은 읽지도 덮지도 않는다(소유 판정 코드 제거).
- 판독(`producer_state`): 옛 공유 `.producer` + `.producer-*`(`*.tmp` 제외)를 모두 모아 순위 「돌고 있음 > 판정 불가 > 열린 채 죽음 > 정상 종료」로 판정. 하나라도 못 읽으면 판정 불가(= 막음).

### M4 — 공장 초기화 rename 을 계획 시점 부모 신원에 묶었다(`src/factory_reset.rs`)
- `PlanItem.parent_id` = 계획 때 부모 디렉터리 (dev, ino)(부모 경로의 정상 심링크 — 예: macOS `/var` — 는 따라가 끝 객체를 잰다).
- 집행: 부모를 열어 신원 대조 → 어긋나면 그 항목은 저널도 쓰지 않고 `failed`(사유에 「부모」) · 이동 0.
- 이동 = 부모 핸들 → 격리 폴더 핸들(`renameat`).
- ★codex 1R ③: 격리 폴더 `TrashDest` 핸들 하나로 **저널(openat append)·manifest·REPORT·표식(O_EXCL 임시 + renameat · 이름 충돌 시 새 번호 최대 8회)** 을 전부 쓴다 — 격리분과 복구 지도가 같은 폴더에 남는다. 경로로만 쓰는 하위 폴더(오너 설정 사본 · 훅 제거·agy 상태줄·claude tui 되돌림의 백업)는 쓰기 직전 경로 = 핸들 대조, 어긋나면 **그 분기 전부**를 건너뛰고 보고(설정 파일 무변경 · agy·tui 는 codex 2R ③).
- ★codex 2R ②: 지도 줄(저널·manifest)에 `to_rel`(격리 폴더 기준 한 성분 이름)을 **가산**했다. undo 는 `to_rel` 이 있으면 **지금 가리킨 격리 폴더** 기준으로 해석한다(옛 지도는 절대 `to`). 그래서 목적지 폴더가 옮겨져도 그 폴더를 `--undo` 로 가리키면 복구된다. ★codex 3R: 절대 `to` 폴백은 `to_rel` 칸이 **없을 때**(옛 지도)만이다. 칸이 있는데 `Path::components()` 가 정확히 보통 성분 하나가 아니면(빈 값·`.`·`..`·구분자·절대·문자열 아님·윈도우 드라이브 접두사) **지도 전체를 거부**한다(`4da85f2f`).
- **판단 1건(지시 없이 내린 것)**: 항목 **자체**의 신원은 묶지 않았다. 데몬이 원자 교체로 다시 쓰는 상태 파일(depts.json 등)은 계획~집행 사이 inode 가 정상적으로 바뀐다 — 묶으면 초기화가 그 파일을 남기는 회귀가 난다. 오너가 승인한 단위는 경로이고, 결함의 축(부모 바꿔치기)은 부모 신원이 닫는다.

### M1 — 타이핑 확인을 앱 네이티브 단회 확인에 묶었다(`src-tauri/src/main.rs` · `ui/src/main.ts`·`trashconfirm.ts`)
- master#9146f4c3 **A안**(체감 변화 0).
- `trash_preview_poll` 이 ready + confirm_id 를 돌려줄 때 네이티브가 확인(nonce)을 발급한다. 결박 대상 = confirm_id · digest · 정렬 이름 목록 · 발급 시각(300 s = 데몬 확인 수명).
- `trash_delete(…, confirmNonce, typed)`: 소켓을 고르기 **전에** nonce 를 꺼내고(단회) 결박 대조 + 입력 문구 재측정(lib `normalize_confirm_phrase` · 화면 `normalizePhrase` 와 같은 규칙 + 한글 조합) → 어긋나면 데몬에 0 바이트(Class 1 거부 `confirm_unbound`·`confirm_expired`·`phrase_mismatch`).
- ★codex 1R ②: confirm_id 당 살아 있는 확인은 **하나**다(재폴링하면 같은 nonce를 돌려준다). 한 번 꺼낸 confirm_id 는 묘비가 되어 재발급되지 않으므로, 실패 뒤 형제 nonce 로 다시 시도할 수 없다.
- 화면: 모달이 「삭제」 순간의 입력값을 돌려주고, 명령이 nonce·문구를 함께 보낸다. 새 거부 코드 3개의 문구를 더했다(전부 「지우지 않았습니다 + 다시 미리보기」).

## 2. 정직한 한계(합격 기준에 그대로 적는다)
1. **M1 — 오염된 WebView 는 막지 못한다.** 확인 문구는 이름에서 결정론으로 나온다(이름 1개 = 그 이름 · 여럿 = 「삭제 N」). 그래서 WebView 안의 스크립트는 nonce 를 받아 문구를 지어 보낼 수 있고, 이 관문은 **「사람이 쳤다」를 증명하지 않는다**. 닫는 것은 ⒜타이핑 모달을 거치지 않는 화면 경로(배선 실수·회귀) ⒝재사용 ⒞다른 목록으로의 바꿔치기 ⒟만료 뒤 사용이다.
2. **B2 — 파일 하나의 lstat↔unlinkat 창.** POSIX 에 「이 inode 일 때만 unlink」가 없다. 그 사이 이름을 바꿔 넣은 객체는 같은 UID 가 **봉인된 트리 안으로** 옮겨 넣은 것이어야 한다. 경로 바꿔치기로 트리 **밖**에 닿는 길은 핸들 결박이 닫는다.
3. **B2 — 인증·봉인 뒤 대조는 경로로 읽는다.** 읽기 전용이고 digest 에 모든 노드의 (dev, ino) 가 들어 있어, 바꿔친 경로를 읽으면 불일치 = 거부(봉인 상태로 멈춤)다. 지우는 쪽으로 가지 않는다.
4. **M4 — 하위 폴더(오너 설정 사본·백업)는 경로로 쓴다.** 직전 대조와 쓰기 사이 창이 남는다. agy 상태줄·claude tui 분기의 「대조 어긋남 → 건너뜀」에는 **전용 시험이 없다**(시험 루트에 그 두 대상이 없다 · 코드 읽기로만 확인).
5. **윈도우(표식)** — 안정 std 에 `openat` 계열·파일 신원(file index)이 없다. 휴지통 집행·제거 집합·M4 부모 결박은 경로 기반 그대로다. 윈도우 휴지통 삭제는 기본 꺼짐(`delete_supported` · 12.W 게이트). 공장 초기화 윈도우 경로는 결박 없이 종전과 같다.
6. **윈도우 교차 컴파일 미검증** — 이 맥에서 `cargo check --target x86_64-pc-windows-msvc` 는 `libsqlite3-sys` 빌드 스크립트(C 교차 컴파일러 부재)에서 멈췄다. cfg 분기는 읽어서 맞췄고(`dirat` 참조 전부 `cfg(unix)`) 실컴파일은 CI 윈도우 잡이 판정한다.
7. **certify_entry_ids 메모리** — 봉인 뒤 대조 동안 노드당 16 바이트(노드 상한 5,000,000 에서 약 80 MB · 집행 한 항목 동안만).

## 3. 다음 판 후보(이 티켓 밖 · master#9146f4c3)
- **M1-B: WebView 밖 OS 네이티브 확인창.** 삭제 직전 macOS 대화상자를 띄우면 오염된 WebView 도 우회할 수 없다. 확인 단계가 하나 늘어난다(체감 변화).
  - 위협 모형 — 누가 WebView 를 오염시킬 수 있는가: 앱이 로드하는 원격 콘텐츠·주입된 스크립트·개발자 도구·같은 UID 의 앱 번들 변조.
  - 우리 배포에서 그 경로가 실제로 열려 있는가는 **미측정**이다(CSP·원격 로드·devtools 출하 설정 실측이 선행 과제). 같은 UID 번들 변조는 이미 operator_token 파일 열람과 같은 급이다(trash.rs 머리 「정직한 한계」).
- `trash.rs`·`factory_reset.rs` 윈도우 경로의 핸들 결박(안정 API 생기면) · 12.W 검증과 함께.

## 4. 시험(RED → GREEN → 뮤턴트)
| 항목 | 시험 | RED(수리 전 실측) | 뮤턴트(수리 되돌림 → 빨강) |
|---|---|---|---|
| B2 봉인 직전 바꿔치기 | `trash::tests::b2_root_swapped_before_the_seal_never_renames_outside_the_vetted_root` | 바깥 동명 디렉터리를 봉인 rename | 경로 rename |
| B2 제거 직전 바꿔치기 | `…b2_root_swapped_before_the_removal_never_removes_outside_the_vetted_root` | 바깥을 지우고 `deleted_verified` | 경로 `remove_dir_all` |
| B2 명령 진입 뿌리 대조 | `…b2_delete_refuses_when_the_root_is_not_the_one_the_preview_walked` | (API 부재) | 신원 대조 제거 → `ok order_id` |
| B2 핸들 제거 신원 | `…b2_handle_removal_refuses_an_object_that_is_not_the_previewed_one` | (API 부재) | 경로 제거 |
| C-R1 대조 뒤 옮겨 넣기 | `…c_r1_a_tree_moved_in_after_the_compare_is_never_removed` | 53985c6c 전 코드 = 집합 무시 뮤턴트와 같은 동작 | 집합 무시 |
| M3 판독 | `…m3_reader_sees_every_per_producer_marker_and_the_legacy_one` | `Unknown`(기대 `ActiveOpen`) | `.producer` 만 읽기 |
| M3 쓰기(bash) | `cysjavis-pack/bin/tests/test_producer_marker.py` ⑧ 경합 | 남의 open 창이 내 complete 로 덮임 | 공유 이름 복귀 |
| M3 쓰기(py) | `javis_org.py --self-test` race 2건 | 같음 | 공유 이름 복귀 |
| M3 쓰기(Rust 초기화) | `factory_reset::tests::producer_marker_never_touches_another_producers_window` | — | — |
| M4 부모 바꿔치기 | `factory_reset::tests::m4_parent_swapped_after_the_plan_moves_nothing_from_the_impostor` | 바꿔 넣은 쪽 `pack` 을 격리 | 대조 끔 |
| M4 목적지 바꿔치기 | `…m4_destination_swapped_after_open_keeps_data_and_recovery_map_together`(지도 동거 + 옮겨진 폴더로 undo → 원위치) | (53985c6c 전 = 저널 경로 뮤턴트와 같음) | 저널 경로로 · undo 가 to_rel 무시 |
| 복구 지도 to_rel 검증 | `factory_reset::tests::undo_rejects_a_bad_to_rel_and_falls_back_only_when_it_is_absent` | (4da85f2f 전 = 폴백 뮤턴트와 같음) | 잘못된 값 폴백 |
| C-R1 하위 rmdir 바꿔치기 | `dirat::tests::a_subdir_swapped_during_emptying_is_not_rmdired` | (cd390154 전 = 재대조 끔 뮤턴트와 같음) | 재대조 끔 |
| M1 관문 | `tests::m1_a_delete_without_the_native_confirm_never_reaches_the_daemon` 외 3 | (API 부재 — 컴파일 적색) | 관문 호출 제거 · 문구 대조 끔 · 재발급 |
| M1 화면 | `ui/src/trashwiring.test.ts` · `trashconfirm.test.ts` | 3 적색 | 모달이 입력값 안 돌려줌 |

- ★**뮤턴트 1차 사고(기록)**: M1 첫 뮤턴트 실행에서 시험이 `trash_delete` 를 직접 불러, 관문이 빠진 상태로 **실물 기지 데몬 소켓**에 요청이 나갔다. 가짜 confirm_id 라 데몬이 거부했고, `~/.local/state/cys/DELETE-LEDGER.jsonl` 부재를 실측해 지운 것·기록된 것이 없음을 확인했다. 그 뒤 시험은 소켓에 닿지 않는 꼴(관문 함수 + 「관문이 소켓보다 먼저」 소스 순서 핀)로 고쳤다.

### 전건(HEAD 기준) — §6 에 결과 원문

## 5. 검증 라운드
- codex 1R(`668aee8f` 대상): **REVISE** — major 3 · minor 1 → 전부 수용 · `53985c6c`. 판정문 = `~/.cys/pack/round/_reviews/cysr-1110-trash-harden_보안_경계_삭제_로직__리뷰__B2_M1_M3_M4_수리-r1-reviewer1.json`(원문 `…-codex-r1.out.txt`).
- codex 2R(`53985c6c` 대상): **REVISE** — 1R ②·④ 닫힘 판정 · 남은 major 3(하위 rmdir 재대조 · 지도 절대 to · agy/tui 분기 대조 밖) · minor 1(임시 이름 재시도) → 전부 수용 · `cd390154`. 판정문 = `…-r2-reviewer1.json`(원문 `…-codex-r2.out.txt`).
- codex 3R(`cd390154` 대상): **REVISE** — 2R 4건 닫힘 판정 · 새 major 1(잘못된 to_rel 폴백·드라이브 접두사) → 수용 · `4da85f2f`. 판정문 = `…-r3-reviewer1.json`.
- codex 4R(`4da85f2f` 대상): **ACCEPT** — blocking·major 0 · minor 1(유닉스 `C:foo` 허용 양성 시험 없음) → 시험 추가 `36241868`. 판정문 = `…-r4-reviewer1.json`.
- ⇒ **수렴**: 1R REVISE(4건) → 2R REVISE(4건) → 3R REVISE(1건) → 4R ACCEPT. 판정문 4개 = `~/.cys/pack/round/_reviews/cysr-1110-trash-harden_*-r{1..4}-reviewer1.json` · 원문 `cysr-1110-trash-harden-codex-r{1..4}.out.txt`. ★codex 는 읽기 전용 제약이라 시험을 돌리지 않았다(정적 검토) — 실행 증거는 §6.

## 6. 결과 원문
### rebase(master#eb1c8465)
- `rebase/v0.14.51` **`8d81d780`** 위로 rebase 완료 → HEAD `87e69ddc`(커밋 8개 재적용). 충돌 2파일 = `javis_org.py` 자기검사 · `tests/test_producer_marker.py` — 둘 다 540 의 **M2 시험 블록을 그대로 보존**하고 내 M3 경합 시험을 나란히 둠(제품 코드 충돌 0 · `cys-dept`·`main.rs` 자동 병합). rebase 전 끝 = 로컬 가지 `backup/1110-trash-harden-pre-rebase`(`73b8b29d`).

### 시험 전건 — rebase 뒤 HEAD `87e69ddc`(직렬 1회 · 2026-10-21 23:4x~00:1x)
| 묶음 | 결과 |
|---|---|
| ui `bun test` | **3155 pass · 0 fail** |
| `cargo test --lib` | **1099 passed · 0 failed** · 2 ignored |
| `cargo test --bin cysd` | **2686 passed · 0 failed** · 9 ignored |
| `cargo test --bin cys` | **625 passed · 0 failed** |
| `src-tauri cargo test` | **309 passed · 0 failed** · 2 ignored |
| `tests/test_producer_marker.py` | RESULT: PASS(540 의 M2 도장 검증 포함) |
| `javis_org.py --self-test` | ok · failures [] |
| `tests/test_org_audit.py` | ALL PASS |
- 참고(rebase 전 HEAD `4da85f2f` 전건): lib·cysd·tauri 에 각 1 적색이 있었다 — `pack::released_tables_cover_current_embed` · `s5_escalation…source_pin`(글자 경계) · S8 토큰 부착 핀(`daemon_state_dir_for`·`run_sidecar_restore_report`). 셋 다 이 가지 diff 가 닿지 않는 입력이고 540 의 `d8e28331`·`38508fc4` 가 고친 것 — rebase 뒤 전부 초록.
- 시험 빌드 자리표시자(커밋 안 함 · 전부 .gitignore 대상): `src-tauri/binaries/cys{,d}-aarch64-apple-darwin`(빈 파일) · `src-tauri/resources/pack.tar.gz`·`pack-manifest.json` · `src-tauri/runtime/` · `ui/dist/index.html`.

### 변경 크기(`8d81d780..HEAD` · docs 제외)
- 12 파일 · **+1580 / −167**. Rust 는 생산 구역 **+882**(머리 주석 다수 포함) · 시험 모듈 **+529**. 새 파일 = `src/dirat.rs`(unsafe libc 래퍼 · unix 전용). 팩 3파일 +80 남짓 · ui 4파일 +43.

## 7. 1.1.10 편입 판단 근거
- 변경 크기: §6(생산 Rust +882 · unsafe 래퍼 1파일 신규).
- 시험 수: 새·바뀐 검체 = trash 6(B2 4 · C-R1 1 · M3 판독 1) · factory_reset 4(M4 부모 · M4 목적지+undo · to_rel 검증 · 표식) · dirat 1 · tauri 4(M1) · ui 2+1 · 팩 py 경합 5 check. 뮤턴트 = 라운드별 수리마다 1개 이상, 전부 빨강(§4).
- 회귀 위험 축:
  - ⒜휴지통 삭제 집행 — 정상 경로는 같은 순서(신원 재확인 → 봉인 → 대조 → 제거 → 검증)이고 연산만 핸들로 바뀌었다. 새 거부 3종(뿌리 신원 · 제거 집합 밖 · 경로 분기)은 전부 「지우지 않음」 쪽이다.
  - ⒝공장 초기화 — 부모 대조 실패와 목적지 경로 분기만 새 실패다. 정상 시험 45건이 그대로 통과한다.
  - ⒞휴지통 확인 모달 — 사용자 체감 0 이고, 명령 인자 2개가 늘었다. 화면과 네이티브가 함께 출하되어야 한다(구 화면 + 새 네이티브 = `confirm_unbound` 거부 · 지우지 않음).
  - ⒟생산자 표식 — 판독기가 옛 `.producer` 도 읽으므로 구 생산자와 섞여도 안전하다.
- **rebase**: 출발 = `2b2179b7`. 540 의 `rebase/v0.14.51` 은 계속 움직인다 — 편입 시 이 가지를 그 끝으로 rebase 해야 한다. 이 가지는 540 가지를 건드리지 않았다. 겹칠 가능성이 있는 파일은 `src/bin/cysd/trash.rs`·`src-tauri/src/main.rs`·`ui/src/main.ts`(540 의 B1·M2 범위와 대조 필요).
