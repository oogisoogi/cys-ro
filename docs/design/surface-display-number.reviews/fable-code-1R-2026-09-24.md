# Fable 적대 코드 검증 1R — v116-num ②데몬(커밋 8b8e90d1 · 기준 526325bf)

- 검증자: Fable 서브에이전트(읽기 전용 · `git show 8b8e90d1:` 로만 읽음 — 작업 트리는 뮤테이션 실행 중)
- 표적(master 지정): T-A 부팅 순서 · T-B 락 범위 · T-C 경보 식별
- 원문(판정문 전문 그대로 옮김):

VERDICT: REVISE
발견 8건 (HIGH 0 · MED 2 · LOW 6) — 메커니즘(락 범위·부팅 순서·경보 식별) 결함 0. REVISE 사유 = T12 미이행(Windows 시험 격리 결함) + 부팅 ⑴ 실패 시 읽을 수 있는 시드까지 버리는 경로 잔존.

## 발견

**[MED-1] recall.rs:428-440 (surface_numbers_boot ⑴)** · 결함: `open_db` 실패 = 무조건 `seed 0`. `open_db`는 `PRAGMA journal_mode=WAL` + 4개 `CREATE … IF NOT EXISTS`(recall.rs:24-64)를 한 배치로 실행하므로, **읽기는 되는데 쓰기가 막힌 DB**에서 실패한다. 재현: ⓐ 1.1.5 DB(surface_numbers 표 없음)를 읽기 전용/가득 찬 디스크에서 첫 기동 → CREATE 실패 → seed 0 → 내부 번호 1부터 재발급. ⓑ 읽기 전용 + 비-WAL DB → PRAGMA 실패 → 같음. 귀결: 1.1.5의 `max_surface_id`(스키마 없이 `Connection::open` 후 SELECT만)는 이 경우 시드를 살렸으므로 **I0 회귀**. `seed_failed` 경보는 난다(조용하지 않음) — 그러나 경보 뒤에 lines·chains·surface_numbers를 평문 연결로 한 번 더 읽는 폴백이 없다. 【관측】 코드는 설계 §3-2 「⑴ 실패 → 있었으면 seed_failed · 시드 0+1」 그대로다 — 결함은 설계 문장에 있고 구현이 그대로 옮겼다. 시험 `t2_readonly_db_keeps_snapshot_and_alarms_write_io_once`(state.rs:9042)는 **전체 스키마를 먼저 만든 뒤** 읽기 전용으로 바꾸므로 이 경로를 밟지 않는다. 처방: ⑴ 실패 && existed 이면 `Connection::open` 평문 연결로 ⑵를 그대로 수행(표 없음은 갈래별 Failed로 흡수됨).

**[MED-2] state.rs:2857-2884 (`pipe_slug`·`state_dir` windows) × state.rs:8558-8567 (`iso_sock`) × handlers.rs:18665-18675 (`iso`)** · 결함: Windows에서 `state_dir`는 소켓 **파일명 슬러그**만 쓴다(`cysd.sock` → `cysdsock`, 디렉터리 무시). 모든 v116 시험이 `<고유 temp dir>/cysd.sock`을 쓰므로 Windows에서는 **전부 `%LOCALAPPDATA%\cys\cysdsock\transcripts.db` 하나를 공유**한다. 재현: Windows에서 `cargo test --bin cysd v116_num_tests` → `t2_fresh_install_seed_one_no_alarm`(seed==1) · `t2_seed_includes_surface_numbers_x10`(==778) · `t11_two_sockets_are_independent`(hq/dept 같은 슬러그 → 같은 DB) · `t2_unreadable_db_alarms_seed_failed`(garbage 파일이 공용 DB를 파괴) 상호 오염. 귀결: 설계 §9 T12 「같은 시험 묶음이 윈도 CI에서 초록」 **미달** — 【관측】 windows-health.yml:199-230은 `--lib factory_reset::`과 `--bin cys d5_env_injection`만 돌리고 `--bin cysd`는 안 돌린다 → T12는 실행된 적이 없다(ci-branch.yml은 macos-latest). 제품 로직 결함은 아님(부서 데몬 격리는 pipe 이름이 다르므로 유효). 처방: 시험 소켓 파일명에 태그·시퀀스 포함(`{tag}-{seq}.sock`) + T12를 「미실행」으로 정직 표기하거나 windows-health에 레인 추가.

**[LOW-1] state.rs:3310-3313 (`numbers_alarm` note)** · `"write_io" | "pk_conflict" if surface_id.is_some()` 팔이 먼저 잡아 **pk_conflict(좌석 쓰기 = 항상 surface_id 있음)의 note가 write_io와 동일 문장**이 된다. :3313 「PK 충돌 — I0 위반」 팔은 도달 불가(pk_conflict는 :3847에서만, 항상 `Some(id)`). `kind` 필드로는 구분되나 설계 §3-2 ⑤ 「디스크 가득 문구로 뭉개지 않는다」의 사람 문구 부분이 미이행. 【관측】

**[LOW-2] state.rs:9141 (t13)** · `assert!(!s1.numbers_row_owned || s1.numbers_row_owned, …)` — 항진식(공허한 단언). 의도(「write_io면 row_owned 유지 true」)라면 `assert!(s1.numbers_row_owned)`여야 한다. 【관측】

**[LOW-3] state.rs:3826-3833** · `DisplaySpawnGuard`가 INSERT **뒤**에 만들어진다. INSERT(:3828-3831)는 `?`가 없어 정상 경로엔 문제 없으나, 그 안에서 panic이 나면 `holders[n]=Live(id)`가 되돌려지지 않아 번호 n이 이 실행 동안 영구 막힘. 처방 = guard를 :3826 직후에 만들고 `row_owned`는 필드 갱신으로. 또 :4152(맵 insert)~:4178(`armed=false`) 사이에 panic(poison unwrap :4172)이 나면 좌석은 맵에 있는데 holder는 prev로 되돌려져 I2 구멍. 【추정 · poison 전용 경로 · 실현 가능성 극소】

**[LOW-4] state.rs:1119-1123 (`DisplayAlloc::new`)·1152-1176** · holders 길이(1000)를 검증하지 않는 pub 생성자. 짧은 벡터로 만들면 `assign/release/revert`의 인덱스 panic이 **락 안**에서 나 poison → `note_surface_closed`(:3349 `.unwrap()`)가 close_surface 말미에서 panic. 제품 경로는 `holders_from_rows`(항상 1000)만 쓰므로 도달 불가. 【관측】 poison 처리 = guard Drop만 `into_inner`, 나머지 3곳 unwrap.

**[LOW-5] recall.rs:472-486** · `COMMIT` 실패를 무시(`let _`). 실패하면 읽기 트랜잭션이 열린 채 ⑶ UPDATE가 그 안에서 실행되고 `conn` drop 시 롤백 — 경보 없이 고아 기록이 사라진다(다음 부팅에 다시 고아로 잡히므로 보수적). 【추정 · 읽기 전용 트랜잭션의 COMMIT 실패는 실질적으로 발생 조건이 없음】

**[LOW-6] governance.rs:4973 × governance.rs:304·4761 (reap 루프)** · close_surface 안의 동기 UPDATE(busy_timeout 5초)는 좌석당 최대 5초. 설계는 「한 건 5초」로 수용했으나 reap/watchdog **루프**(:304, :4761)가 N좌석을 연속 닫으면 prune 중 N×5초 정체. 데드락 아님·기능 정지 아님. 【추정 · prune 지속시간 실측 없음】

## 표적 판정

**T-A 부팅 순서 — 성립(MED-1 예외 명시).**
- ⓪ `existed`(recall.rs:426) → ⑴ `open_db`(:428) → ⑵ `BEGIN DEFERRED` 스냅샷·표마다 Ok/Failed(:442-472 · `numbers_ok` 갈래 분리 :455-457) → ⑶ 고아 UPDATE는 COMMIT 뒤·별도·`alarms.push(write_io)`만(:478-486 · ⑵ 결과 유지) → ⑷ 경보는 `Arc::new(Daemon{…})` + `seed_consumption` 뒤(state.rs:3295-3298). 【관측】
- recall 쓰기 스레드: `surface_numbers_boot`(state.rs:3216)가 **반환한 뒤** 구조체 리터럴의 `recall_tx: spawn_writer`(:3271)가 평가된다(필드 순서 평가 · boot의 `conn`은 함수 반환 시 drop). 이후 writer의 `open_db`와 좌석 INSERT는 별 연결·busy_timeout 5초(rusqlite 0.32.1 기본 · Cargo.lock:3347)로 직렬화. 【관측】
- 두 번째 데몬: main.rs:1145-1175 `_lock_file`(flock · main 수명) → :1277 `Daemon::new`. Windows는 :1178-1191 파이프 선점이 먼저. deadman 인수는 `reclaim_from_dead_holder`가 holder를 kill한 뒤(deadman.rs:151-157)라 산 데몬 둘이 같은 DB에 ⑶을 하는 경로 없음. 【관측】
- 시드가 낮아지는 경로: 손상 DB → seed_failed(시험 :8996) · 읽기 전용(전체 스키마) → 시드 유지 + write_io(시험 :9042) · 가득 찬 디스크(전체 스키마) → 같음. **잔존 = MED-1(스키마 미완 + 쓰기 불가 조합)** — 경보는 나므로 「조용히」는 아니다.

**T-B 락 범위 — 성립.**
- `allocate_display`(state.rs:3333-3344): 락 안 = `next_id.fetch_add`(:3336) + `assign`(메모리) 만 · `numbers_alarm`(bus.publish)은 블록 밖(:3340). DB 0 · 다른 락 0. 【관측】
- `note_surface_closed`(:3347-3358): 락 임시 guard는 문장 끝에서 drop → DB UPDATE는 락 밖. `resolve_display`(:3361-3383): surfaces guard는 `if let` 문장 종료(edition 2021 · :3362-3369)에서 drop된 뒤 display_alloc(:3371) — 중첩 없음. guard Drop(:1199-1220): display_alloc 임시 guard 문장 종료 후 DB. 【관측】
- surfaces/roles를 쥔 채 display_alloc을 잡는 경로: `allocate_display`는 create 진입 첫 줄(:3826 · 호출부 handlers.rs:3328-3334 「락 미보유 구간」) · `note_surface_closed`는 close_surface의 surfaces/roles 블록 종료(governance.rs:4931) 뒤 :4973. grep `display_alloc` 6곳(state.rs:1206·3335·3349·3371 + 시험) 외 없음. 역방향(display_alloc 안에서 surfaces) 없음. 【관측】
- INSERT :3828-3831 < openpty :3842 < spawn :3986 — 락 밖·PTY 전(소스 핀 시험 :8724). 【관측】
- guard(:3833)가 덮는 `?`: openpty :3842 · spawn_command :3986 · try_clone_reader :4001 · take_writer :4005 — 전부 guard 뒤·맵 등록(:4152) 전. 그 구간에 `.lock()` 0(grep). `armed=false` :4178 = surfaces/roles 블록 닫힘(:4177) 직후·`?` 없음. Drop은 unwind에서도 실행(Cargo.toml에 `panic=abort` 없음). 【관측】 잔여 = LOW-3.
- Poison: guard Drop만 `into_inner`, 나머지 unwrap(LOW-4 · 락 안 코드에 panic 경로 없음).

**T-C 경보 식별 — 성립(LOW-1 문구 예외).**
- kind 5종 정확히: `exhausted`·`suspended`(assign :1141-1150) · `pk_conflict`·`write_io`(create :3845-3851) · `seed_failed`·`write_io`(boot recall.rs:434·474·484). 좌석 쓰기·할당 경보 = `Some(id)`(:3341·3847·3850) · 부팅 경보 = `None`(:3297). 【관측】
- 부팅당 종류별 1회: `seed_failed`는 :434(return) 또는 :474(join) 중 한 번 · `write_io` :484 한 번. 【관측】
- exhausted 진입 시만: `exhausted_alarmed` set(:1148) · Number 픽 시 리셋(:1138) · 속성 시험 run_chain :8786-8788이 「진입 때만」을 매 단계 단언. suspended 1회: `suspended=true` 뒤 early return(:1133-1135). 【관측】
- pk_conflict 좌석: `row_owned=false`(:3846) → `numbers_row_owned`(:4138) → `note_surface_closed` :3350 분기 생략 · guard Drop :1212 생략 · 시험 :9150-9165. 【관측】

## 추가 표적
- 4군 ④(보이는 번호 → 파괴 RPC): `resolve_surface_id`(handlers.rs:318-324) 무변경 · `parse_surface_ref` 무변경(lib.rs 시험 :4831-4859) · 파괴 7 RPC 전부 `resolve_surface_id` 경유(handlers.rs:4318·3623·3997·7461·7552·4399·5258) · `display_no`를 요청에서 읽는 곳 = :3087-3090 하나(t3b 핀) · 저장소 전체 grep에서 state/handlers/recall 밖 `display_no` 0(cys.rs 0). **경로 없음.** 【관측】
- 4군 ③(생성 막힘 새 경로): INSERT 실패 → 경보만·좌석 생성(:3845-3851 · 시험 :9129) · Exhausted/I1Guard → None·생성(:1141-1150). 새 차단 경로 0. 지연만(busy 5초 · LOW-6). 【관측】
- Windows: 제품 차이 = `state_dir`(:2869-2884)만 · 대응표는 같은 transcripts.db · `socket` 칸은 pipe 문자열. 시험 격리 결함 = MED-2.
- 시험 대 뮤턴트: M1~M8(t1 :8610-8659 — ⑸ `NOW-W`→50이 M3를, ⑾ 미래 closed_at→51이 M8을 잡음) · M7·M10(:8664-8684) · M9(:8946-8952 + recall :1649-1650) · M11(소스 핀 :8724) · M11b(:8998) · M11c(:8956) · M11d(:8987) · M11e(:9042) · M12(t3 :18685 — 내부 17=보이는 17 산 좌석을 세워 벗김 뮤턴트가 실제 좌석에 닿게 함 · 비공허) · M13(t3b :18714) · M18(:18783-18789) · M20(recall t10 :1522) · M21(t11 :9096) · M24(t13 :9129) · M26(:8881) — 전부 적색 가능한 실단언. 공허 = LOW-2 한 줄. t3b의 arm 경계 탐지(`\n        \"`)는 arm 안에 8칸 들여쓴 문자열 리터럴이 오면 조기 절단될 수 있음(현재 arm들엔 없음 · 【추정】).

## 확인한 것(결함 아님)
- state.rs:1048-1050 `display_candidate` saturating · u16 산술(:1075 최대 1997) 오버플로 없음.
- state.rs:1086-1105 holders_from_rows: spawn_failed 건너뜀·범위 밖 무시·최대 sid·고아=Closed(boot_now).
- state.rs:3114-3116 `create_dir_all(dir)`이 boot(:3216) 전 — `existed`가 디렉터리 부재로 오판되지 않음.
- state.rs:4204-4205 `surface.created` payload에 display_no.
- state.rs:4023 Surface 구조체 리터럴 단일(다른 생성자 없음 · 필드 누락 컴파일 불가).
- governance.rs:4885-4975 close_surface = 맵 제거 유일 지점(`surfaces.*remove(` grep 3파일 0건 외).
- recall.rs:518-545 INSERT PK 충돌 판별 `SQLITE_CONSTRAINT_PRIMARYKEY` extended code · :549-563 UPDATE `closed_at IS NULL` 가드(이미 닫힌 행·boot_orphan 행 덮지 않음).
- recall.rs:1522-1552 t10 prune 무접촉 · :1642-1650 시드 3갈래 e2e.
- handlers.rs:3086-3122 resolve_display: 범위 필터 → 산 좌석만 Ok · 닫힌 번호는 last 안내만 · `ago_label` 음수 0초(:327-335).
- handlers.rs:3061-3066 identify `caller_display_no` · :3287-3288 idempotent_reuse 응답 · :3490·:3562·:6766 list/create/org.status 필드.
- lib.rs:2733-2751 `parse_display_ref` 문법(앞자리 0·전각·`surface:#` 거부) · `parse_surface_ref` 무변경.
- main.rs:1145-1175 startup 락 수명 = main 스코프(조기 drop 없음).
