# `~/.cys/policy.json` — 좌석 정책 키 (1.1.8)

파일이 없거나 키가 없으면 아래 「기본값」으로 동작한다. 고친 뒤에는 **좌석을 재기동해야** 기동 인자에 반영된다.

| 키 | 뜻 | 기본값 | 근거 |
|---|---|---|---|
| `deny_self_approve` | 승인 요청을 낸 좌석·pane 밖 미귀속 프로세스의 `allow` 를 막는다 | `true` | §3.2 자기승인 차단 |
| `rc_allowed_roles` | Remote Control(폰 노출)을 켜도 되는 좌석 역할명 목록. 목록 **밖** 역할(과 부서 데몬 좌석 전부)은 기동 인자 `--settings` 로 `remoteControlAtStartup:false` + `disableRemoteControl:true` 가 붙고, 기동 뒤 대화 기록에서 RC 켜짐이 보이면 데몬이 끈다 | `["master"]` | BACKLOG D25 · master 결정 [master#99924a73] |
| `seat_permissions_allow` | claude 좌석 기동 인자 `--settings` 의 `permissions.allow` 로 싣는 목록(분류기 오탐 완화 장치) | 없음(빈 목록) | BACKLOG D24ⓒ · 효과 미검증 → 기본 0 |

- **워커에서 RC 를 켜려면** `rc_allowed_roles` 에 그 좌석의 역할명(`cysr list` 의 `role=`)을 넣고 좌석을 재기동한다. 역할명은 `worker-N` 처럼 번호가 붙을 수 있다 — 재기동 뒤 번호가 바뀌면 목록도 고쳐야 한다.
- 사용자 `~/.claude.json`·`~/.claude/settings.json` 의 `remoteControlAtStartup` 값은 cysr 이 고치지 않는다(좌석 기동 인자가 그 값보다 이긴다 — `disableRemoteControl` 은 어느 출처든 true 면 이기는 병합 규칙).
- agents.json 의 claude `cmd` 에 이미 `--settings` 를 넣어 두었으면 cysr 은 둘째 `--settings` 를 붙이지 않는다(그때는 기동 뒤 감시만 동작).
- 좌석 기동 설정 파일 = `~/.cys/seat-settings/<역할>.json`(기동 때마다 다시 쓴다).
