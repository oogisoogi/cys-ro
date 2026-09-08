# S3 조사 결과 — `topology.json` 에 master 역할이 없다 (원인 미확정)

> TICKET=cys-phoenix-korean-windows S3 · 2026-09-08 · **원인 확정 못 했습니다.**
> 아래는 ⑴반증된 가설 ⑵실재가 증명된 기전 ⑶판별에 필요한 단 하나의 측정입니다.
> 수리는 **판별 뒤**입니다 — 후보마다 옳은 조치가 다르고, 그중 하나는 「고치면 안 되는 것」입니다.

## 0. 관측된 사실 (오너 실기 · 한국어 Windows · 2026-09-08)

- 설치기가 `cys new-surface --role master --cwd … --cmd <claude>` 로 master 를 세웠다.
- `[10/11]` 이 `cys list` 로 `role=master` 를 실측했다(「함대가 섰습니다: master · cso · worker」).
- 그런데 `topology.json` 의 `role` 항목은 `cso` · `reviewer-claude-1` · `reviewer-claude-2` ·
  `worker` 4건뿐 — **master 가 없다.**
- 앱 「재시작」(`cys restore --include-master`)이 부서 노드는 기억째 살리는데 master 만 못 살린다.

## 1. 반증된 가설 — 「create 아크에 영속이 없다」

첫 가설은 **`surface.create` 핸들러가 persist_topology 를 부르지 않는다** 였습니다. 근거로
`handlers.rs` 의 create 분기에는 좌석 승계(takeover) 갈래 안에만 영속 호출이 있고, 다른 영속
트리거(`tombstone.set`·`system.claim_role`·`status.set`·`reinject.mark`·`surface.set_meta`)는
전부 좌석 생성과 무관한 후속 사건이라는 사실이 있었습니다.

**이 가설은 틀렸습니다.** 핸들러에 영속을 더한 뒤 그 수리를 되돌리는 뮤턴트를 걸었더니
**테스트가 초록으로 살아남았습니다**(SURVIVED). 조사해 보니 영속의 실제 소유자는 한 층 아래였습니다:

```rust
// src/bin/cysd/state.rs — create_surface_with_env 말미
if role.is_some() {
    crate::governance::persist_topology(self);
}
```

즉 역할을 달고 태어난 좌석은 **이미 create 시점에 영속됩니다.** 핸들러에 더했던 호출은 수리가
아니라 중복 쓰기였고 되돌렸습니다. ★뮤테이션이 아니었으면 이 오진이 「수리 완료」로 보고됐을
것입니다 — 통과만 보고는 알 수 없었습니다.

## 2. 실재가 증명된 기전 — 에이전트 사망이 기록을 지운다

`topology.json` 의 `entries` 는 **actual-state** 입니다. `persist_topology` 는 「지금 살아 있고
지금 역할을 쥔」 좌석만 조립합니다(`governance.rs:2538~` · `!exited` 필터 + `role.is_some()` 필터).

그런데 에이전트가 유예를 넘겨 사라지면 `release_role_after_agent_death`(`governance.rs:472~`)가
역할 딱지를 회수하고(`*srole = None`) **곧바로 영속합니다**. 그 순간 그 역할은 저장본에서
사라집니다. 좌석(셸)은 살아 있고, **묘비도 남지 않습니다**(묘비는 `OwnerClose` 일 때만).

⇒ 이후 `cys restore` 는 그 역할을 되살릴 수도, 왜 없는지 설명할 수도 없습니다.
**「사고사는 부활시킨다」는 원칙이 겨냥한 바로 그 사건이 기록 자체를 지우는 구조입니다.**

이 기전이 실재함은 특성 시험으로 못박았습니다:
`governance::tests::agent_death_erases_the_role_from_persisted_topology_without_a_tombstone`.

⚠**이 시험은 「그 기계에서 실제로 이것이었다」를 증명하지 않습니다.** 기전의 실재만 증명합니다.

## 3. 남은 후보 셋과, 각각에 옳은 조치

| # | 후보 | 코드 위치 | 옳은 조치 |
|---|---|---|---|
| A | 에이전트 사망 → 역할 회수 → 영속(묘비 없음) | `governance.rs:472~` `release_role_after_agent_death` | **설계 논의 필요** — actual-state 를 desired-state 로 바꾸는 변경이라 좀비 부활 위험과 맞바꿔야 함. 워커 단독 판단 금지 |
| B | 사람이 master 좌석을 닫음 → **묘비** | `governance.rs:4290~` `close_surface`(`CloseCause::OwnerClose`) | ⛔**고치면 안 됨.** 묘비가 영속·부활보다 우선한다는 1급 원칙(의도삭제 > 강제부활)의 정상 동작이다 |
| C | exited 좌석 회수(reap) | `reap_exited_surfaces` | reap 은 묘비를 안 남기고 phoenix 의 `desired_roster` 가 되살리는 설계 — 그 경로가 살아 있었는지 확인 필요 |

## 4. 판별 측정 — **딱 하나면 갈립니다**

**오너 기계 `topology.json` 의 `tombstones` 배열에 `"master"` 가 있는지 읽어 주십시오.**

```powershell
# 자리: %LOCALAPPDATA%\cys\topology.json  (Rust state_dir 규약)
Get-Content "$env:LOCALAPPDATA\cys\topology.json" | ConvertFrom-Json |
  Select-Object -ExpandProperty tombstones
```

- **`master` 가 있다 → 후보 B.** 정상 동작입니다. 고칠 것이 없고, 대신 「왜 master 좌석이
  닫혔는가」와 「묘비를 되돌리는 방법」을 안내하면 됩니다(역할을 다시 기동하면 묘비가 풀립니다 —
  `state.rs` 의 `tombstones.remove(&rr)`).
- **비어 있다 → 후보 A 또는 C.** 그때는 `cysd.log` 의 `role.released`
  (`reason: "agent_exited"`) 발행 여부가 A 와 C 를 다시 가릅니다.

⚠**오너의 원 조사는 `Select-String 'role'` 이었습니다** — 그것은 `entries` 안의 `"role":` 키만
훑으므로 **묘비는 문자열 배열이라 애초에 걸리지 않습니다.** 「없다」로 읽힌 것이 실은 「안 봤다」일
수 있습니다. 이 한 칸을 재기 전에는 A·B·C 중 무엇도 확정할 수 없습니다.

## 5. 이 티켓의 인코딩 수리와 어떻게 얽히는가

두 결함은 서로를 가립니다. 피닉스에는 이 침식을 보상하려고 만든 장치가 이미 있습니다 —
`desired_roster`(관측으로만 늘고 묘비로만 주는 단조 로스터). 그런데 **그 장치를 유지하는 주체가
피닉스 자신**이고, 피닉스는 인코딩 결함으로 콜드부트에서 죽어 있었습니다.

⇒ 보상 장치를 돌리는 프로세스가 죽어 있었으므로 보상이 한 번도 일어나지 않았습니다.
**S1·S2 수리만으로 이 증상이 상당 부분 사라질 수 있습니다** — 살아난 피닉스가 desired_roster 를
유지하기 시작하면, topology 침식과 무관하게 master 를 되살릴 수 있기 때문입니다.
그러니 판별 측정은 **수리된 빌드를 그 기계에 올리기 전에** 받는 편이 좋습니다. 올린 뒤에는
증상이 사라져 원인이 영영 확정되지 않습니다.
