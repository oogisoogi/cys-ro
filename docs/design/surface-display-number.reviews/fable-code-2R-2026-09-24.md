# Fable 적대 코드 검증 2R — v116-num(커밋 f657c1e0 · 직전 8b8e90d1)

- 검증자: Fable 서브에이전트(읽기 전용 · `git show f657c1e0:` 로만 읽음)
- 원문(판정문 전문):

VERDICT: REVISE
발견 6건 (HIGH 0 · MED 1 · LOW 5) — 락 범위·부팅 순서·경보 식별·4군 ③④ 메커니즘 결함 0. REVISE 사유 = ③표시 층의 시험 강도를 주장하는 뮤턴트 7건이 이 커밋에 **실행 기록 없이** 스크립트에만 추가됨(증거 부재) + 1R MED-1 처방으로 코드가 바뀐 뒤 설계 문장이 그대로 남아 코드와 어긋남.

## 발견

**[MED-1] scripts/v116_num_mutants.py:136-155 × docs/design/surface-display-number.reviews/mutants-daemon-r1-2026-09-24.txt** · 결함: 이 커밋이 새로 추가한 뮤턴트 7건(M11f 평문 읽기 포기 · M15 제목에 내부 번호 · M15b 「—」 비번호칸 · M18 없는 번호를 마지막 주인으로 · M19 `#017` 허용 · M22 기계 출력 줄에 보이는 번호 · M23 stderr 소켓 줄 제거)이 증거 파일에 **한 줄도 없다** — 증거 파일은 종전 24건(M1~M26 중 24)만 담고, 커밋 메시지도 「뮤턴트 1차 24/24」로 정직하게 1차만 말한다. 귀결: 설계 §9 T6(M15·M15b)·T9(M18·M19·M23)·T3c(M22)·MED-1(M11f)의 「적색이 되어야 할 뮤턴트」가 **도구 출력으로 확인되지 않은 주장** 상태. 【관측】 검수자 추적으로는 7건 모두 죽을 것으로 보인다(M15b: `v116_no_display_number_is_dash_slot`의 `initial_title(1049, Some(50), …, "— · worker1")`가 「50 · — · worker1」이 되어 적색 · `stale_number_tail("— · x")`·`retitle_with_model("— · worker2")` 도 적색 · M22: T3c 핀 `arm.contains("println!(\"{}\", r[\"surface_ref\"]")` 적색 · M11f: `t2_readonly_v115…` 시드 1≠121 적색 · 각 OLD 문자열은 f657c1e0 소스에 실재 — cys.rs:3050 · :1467 · handlers.rs:3383 · :3106-3107 · lib.rs:2744 · recall.rs:431). 단 M15b 에 대해 그 시험의 **첫 단언** `initial_title(1500, None, …, Some("— · worker2")) == None` 은 죽이지 못한다(②갈래 `starts_with_number` 가 `is_number_slot` 아닌 `strip_prefix` 를 쓰므로 뮤턴트에서도 None) — 나머지 단언이 잡으니 시험 전체는 유효. 【추정 · 실행 전】 처방: 7건 실행 후 증거 파일 추가(M23 은 E2E_CLI 레인).

**[LOW-1] docs/design/surface-display-number.md:96(§3-2 부팅 행 「실패 처리」) · §5 표 · §9 T12 행** · 결함: 코드는 ⑴ 실패 && existed 이면 평문 연결로 ⑵ 를 읽고(recall.rs:429-436) 스키마 실패를 부팅 `write_io`(recall.rs:493-495) 로 낸다. 설계 문장은 여전히 「⑴ 실패 → 있었으면 `seed_failed` 1회 · holders 비움 · 시드 0+1」이고, §5 `write_io` 정의에 「스키마 못 세움」 원인이 없고, T12 행은 커밋 메시지(「윈도 CI 는 cysd 시험 레인이 없어 미실행」)와 달리 「CI(windows)」 시험으로 남아 있다. 이 커밋의 stat 에 docs/design/*.md 변경 0. 귀결: 다음 검증자·구현자가 설계를 읽으면 코드가 설계 위반으로 보인다(1R 이 「결함은 설계 문장에 있다」고 짚은 그 문장). 【관측】

**[LOW-2] src/bin/cysd/panetitle.rs:29-31** · `NO_NUMBER` 주석이 「앱(ui/src/panetitle.ts NO_DISPLAY_NO)과 같은 글자여야 한다」고 계약을 걸지만 f657c1e0 에 `ui/src/panetitle.ts` 가 없다(`git ls-tree f657c1e0 ui/src/` 0건 · ui 전체 `display_no` grep 0건 · main.ts:2396 `isAutoTitle` 은 여전히 내부 번호 `surface \d+`). 계약의 상대가 미병합 브랜치(설계 §4-1 「fix/v116-ui」)다 — 병합 순서가 바뀌면 두 글자가 달라져도 아무 시험이 잡지 않는다. 【관측】

**[LOW-3] src/bin/cys.rs:29319-29331 (`human_surface_args_go_through_resolver`)** · 핀이 `&sref`·`&env`·`ENV_SURFACE_ID`·`parse_surface_ref(s).ok_or_else` 를 **문자열로** 제외한다. 새 사람 입력 자리를 `let sref = surface.unwrap(); parse_surface_ref(&sref)` 로 쓰면 핀을 통과한다. 현재 f657c1e0 의 직접 호출 12곳(:1438 · :2991 · :3072 · :3939 · :11607 · :12862 · :19299 등)은 전부 환경변수 폴백으로 확인됐으므로 지금은 참이다 — 핀의 강도 문제. 【관측】

**[LOW-4] scripts/v116_num_e2e.py:157-160 · src/bin/cys.rs:29299-29307** · 설계 T9 「없는 `#N` → 뒤따르는 명령 RPC 0회(**데몬 쪽 요청 로그로 확인**)」 — E2E 는 rc·문구·산 좌석 수 불변만 재고, 단위 시험은 문법 밖 `#` 의 오류 문구만 잰다. 데몬 요청 계수는 어디에도 없다. 구조로는 성립한다(cys.rs:1462-1463 `request(...)?` · :900-906 반환 · :3394/:3407/:3779/:3823 `and_then` 단락) — 시험 강도 결손. 【관측】

**[LOW-5] src/bin/cysd/recall.rs:493-495 × state.rs:3318 (`_ => "대응표 쓰기 실패"`)** · 스키마를 못 세운 부팅 `write_io` 의 사람 문구가 「대응표 쓰기 실패」다. 실제 사실은 「대응표를 못 **만들었다**(읽기는 됨)」 — kind·`error: "schema: …"` 로 구분은 되나 note 는 고아 UPDATE 실패와 같은 문장. §3-2 ⑤ 「문구로 뭉개지 않는다」의 약한 판본. 【관측】

## 1R 발견 처리 판정

- **MED-1 — 해소(코드) · 설계 문장 미갱신(→ LOW-1).** recall.rs:429-436 ⑴ 실패 && existed → `Connection::open` 평문 → ⑵ 그대로. 새 결함 검사: ① 삼키는 오류는 오직 `table == "surface_numbers" && schema_err.is_some() && "no such table"`(:459-464) — 표가 없으면 행도 없으므로 **삼켜서 낮아지는 시드가 구성상 없다.** lines·chains 의 「no such table」·「file is not a database」·「database is locked」은 전부 `failed` → `seed_failed`(t2_unreadable :9004-9015 유지). ② 평문 open 도 실패 → `seed_failed` + 시드 0(:432-435). ③ 읽기 성공 + 스키마 실패 → `write_io`(:493-495) · 고아 UPDATE 실패도 `write_io` → `push_alarm`(:512-520) 이 kind 별 1건으로 병합(t2_readonly_non_wal :9112-9145 가 1회 단언). ④ 부팅당 1회: `surface_numbers_boot` 호출 1곳(state.rs:3216 계열) · alarms 발행은 `Arc::new` 뒤(state.rs:3295-3298). ⑤ 부분 실패 배치(lines·chains 생성 뒤 surface_numbers 생성 전 디스크 가득)도 「표 없음 = 행 없음」이라 흡수가 옳고 신호는 write_io 로 남는다.
- **MED-2 — 해소(시험 격리) · T12 정직 표기는 부분.** iso_sock(state.rs:8568-8577)·iso(handlers.rs:18660-18668) 소켓 **파일 이름**에 tag·pid·seq. `pipe_slug`(state.rs:2859-2865) 는 `-`·`_` 를 남기므로 슬러그 충돌 없음. T12 미실행 표기는 커밋 메시지에만(설계 §9 는 그대로 → LOW-1).
- **LOW-1 — 해소.** state.rs:3313 `"pk_conflict"` 팔이 먼저 · `"write_io" if surface_id.is_some()` 분리 · 부팅 write_io 는 `_` 팔.
- **LOW-2 — 해소.** state.rs:9225 `assert!(s1.numbers_row_owned, …)`.
- **LOW-3 — 해소.** guard 가 INSERT 앞(state.rs:3824) · `armed=false` 가 `surfaces.insert` 직후·락 안(:4160-4163). 그 둘 사이 `?`·return 0 확인. unwind 시 안쪽 블록의 `surfaces`/`roles` 가드가 함수 스코프의 `spawn_guard` 보다 먼저 drop 되므로 guard Drop(display_alloc 락 · :1199-1220)이 surfaces 를 쥔 채 도는 경로 없음.
- **LOW-4 — 해소.** `DisplayAlloc::new` resize(:1119-1123 · 긴 벡터는 절단 — 제품 경로 `holders_from_rows` 는 항상 1000) · `into_inner` 3곳(:3338 · :3352-3355 · :3377). `resolve_display` 의 surfaces 락 `unwrap`(:3369) 은 저장소 관행 그대로.
- **LOW-5 — 미해소(변경 없음 · 1R 에서 【추정·발생 조건 없음】으로 둔 항목).** recall.rs:485 `let _ = COMMIT`.
- **LOW-6 — 미해소(변경 없음 · 설계가 5초/건으로 수용 · 실측 없음).**

## 표적별 판정

**부팅 순서 — 성립.** ⓪ existed(recall.rs:427) → ⑴ open_db(:429) → ⑴′ 평문 폴백(:431-436) → ⑵ `BEGIN DEFERRED` 스냅샷 · 표별 Ok/Failed(:444-482) → `COMMIT`(:485) → 경보 조립(:486-495) → ⑶ 고아 UPDATE 는 rows 에 고아가 있을 때만·실패해도 ⑵ 유지(:498-507) → 반환. 시드가 낮아지는 경로 전수: 손상 파일 → seed_failed(시험 :9004) · 읽기 전용 1.1.5 → 시드 유지+write_io(신규 :9079) · 비-WAL 읽기 전용 → 시드·holders 유지(신규 :9112) · 전체 스키마 읽기 전용 → 유지(:9048) · 평문 open 도 실패 → seed_failed. **조용히 낮아지는 새 경로 0.** 【관측】

**락 범위 — 성립.** 이 커밋의 락 관련 변경은 (a) `lock().unwrap()`→`unwrap_or_else(into_inner)` 3곳(락 범위 불변) (b) `armed=false` 위치 이동(필드 쓰기 · 락 0). `allocate_display`(:3336-3346) 락 안 = fetch_add+assign 만 · `numbers_alarm` 은 블록 밖. INSERT(:3826-3838) < openpty(:3841) — 락 밖. guard Drop 이 surfaces/roles 를 쥔 채 실행되는 경로: 없음(위 LOW-3 판정). 【관측】

**경보 식별 — 성립.** kind 5종 불변 · 좌석 경보 `Some(id)`(:3343 · :3833 · :3836) · 부팅 경보 `None`(:3297) · 부팅 종류별 1회 = `push_alarm` 병합(recall.rs:512-520 · 시험 :9142 「종류별 1회」) · `pk_conflict` 문구 분리(:3313) · `count_kind(al, kind, with_sid)`(:8592-8596) 가 좌석/부팅을 갈라 센다. 문구 약점 = LOW-5. 【관측】

**4군 ④(보이는 번호 → 다른 산 좌석) — 불성립(경로 없음).** CLI: `resolve_surface_arg`(cys.rs:1461-1473) 가 `#N` 을 `surface.resolve_display` 로만 풀고, 데몬은 `surfaces` 맵의 **지금 좌석**만 Ok(state.rs:3366-3375 · handlers.rs:3078-3116 · 닫힌 번호는 `display_not_live` + 안내만) → 뒤따르는 명령은 **내부 번호**로 간다. 맨숫자는 종전대로 내부 번호(:1473) · `#` 로 시작하는 문법 밖은 RPC 0회 거부(:1469-1471). 데몬 입구 `parse_surface_ref`(lib.rs:2723) 무변경 · `display_no` 를 **읽는** 곳 = handlers.rs:3088 하나(t3b 핀 :18718-18740 · 파괴 RPC 7개 본문 `display_no` 0). 제목(panetitle) · `cys list no=`(cys.rs:3058-3063) · `identify caller_display_no` · `surface.created` payload(state.rs:4204-4205) 는 전부 **출력**이며 입력으로 되돌아오는 배선 없음. 해석~명령 사이 TOCTOU 는 I0(내부 번호 비재사용)로 「없음」 종결(E2E `닫힌 #2 재지정 → 거부 · 산 좌석 수 불변` PASS). 【관측】

**4군 ③(생성 막힘 새 경로) — 불성립(새 경로 0).** guard 이동 뒤에도 INSERT 결과는 `match` 로 삼키고 `?` 없음(:3826-3838) · `DisplayAlloc::new` resize 는 panic 경로 제거 방향 · `resolve_surface_arg` 실패는 CLI 종료만(데몬 부작용 0) · `cys list` 새 칸은 4번 자리(cys.rs:3058) — 팩 파서 9곳이 0~3·마지막 칸만 쓰는 것을 T14(test_v116_num_cys_list_compat.py · 앞/뒤 배치 음성 대조 포함)가 잰다. 추가 확인: javis_idle_audit.py:142-155 는 공백 토큰 `surface:`·`pid=` 로 읽어 무영향 · javis_cycle_verifier.py:685 `parts[4]`·javis_boot_node.py:794 `cols[3]`·javis_resource_gate.py:637 은 `cys list` 소비자가 아님(feed·queue·ps 원장). windows-build.yml:653-673 은 `-match 'role=master'` 만. 【관측】

## 확인한 것(결함 아님)
- panetitle.rs:35-37 `is_number_slot` · :40-42 `title_number` · :197-201 `starts_with_number(&str)` · :255-262 `stale_number_tail` · :233-251 `is_machine_title` 의 「surface {sid}」 판별이 **내부 번호**(데몬 기본 제목 생산자와 동형) · :281-309 4갈래에서 `sid` 는 그 판별 한 곳에만 쓰임.
- panetitle.rs 시험 이관 32곳: `Some(sid)` 로 sid∈{5,7,8,9,11,12,36,37,38,41,44,45,60,61,62,73,87,297,874} 전부 ≤999 → I1 에서 보이는 번호=내부 번호이므로 종전 단언 의미 보존 · 내부≠보이는 구분은 신규 :672-727(1049↔50 · None↔「—」)이 진다.
- handlers.rs:3381-3389 `initial_title(s.id, s.display_no, …)` 호출 1곳 · :6612 `retitle_with_model` 은 sid 무관 · 신규 시험 :18793-18804(1049 → 「50 · worker1」).
- handlers.rs:3288 · :3491 · :3564 · :6768 `display_no` 출력 필드 · :3078-3116 resolve_display 범위 필터 후 산 좌석만 Ok.
- cys.rs:900-906 reap · :1435 target_surface · :1449 parse_explicit_surface · :3394 queue clear · :3407 deliver · :3779 close · :3823 attach — 좌석 인자 입구 전부 해석기 경유 · 환경변수 폴백 12곳은 `parse_surface_ref` 직접(원래 내부 번호) · `Command::Run`(19298)·`Recall`(3894)·`feed push`(3936)도 명시 인자만 해석기.
- cys.rs:1476-1485 `socket_label`(윈도 파이프 접두 제거 · 부모 디렉터리 이름) · :3050 new-surface 출력 줄 `surface_ref` 불변 · :13240/:13264 launch-agent `surface_ref(sid)` 2곳 · T3c 핀 :29280-29294.
- state.rs:1084-1104 `holders_from_rows` 범위 필터 · :1119-1123 resize · :1199-1220 guard Drop `row_owned` 분기.
- E2E 증거(e2e-cli · e2e-t5-t11): T9 12/12 · T14 칸 자리 · identify · T3c · 1,050 좌석 생성 0 실패 · 대조군 생존 · 부서/본부 `#1` 분리.
