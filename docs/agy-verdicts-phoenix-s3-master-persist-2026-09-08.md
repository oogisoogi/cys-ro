# agy(gemini) 이종 검증 판정 원문 — TICKET=cys-phoenix-s3-master-persist

> 대상 = S3 수리(`persist_topology` 의 「살아있지 않다고 지우지 않는다」) 델타.
> 2R. R1 = BLOCK(4건) · R2 = ACCEPT(잠근 합격 기준 미달 0). 아래는 **판정 원문 그대로**이며 요약이 아니다 — 요약하면 무엇이 지적됐는지가
> 사라지고, 판정의 정본은 판정자의 판정문이다(워커 지침 §6-9 불변식 2).
>
> ⚠원문이 통째로 `cys send --queued --to master '...'` 한 줄 안에 들어 있다 — 그것은 agy 가
>   회신을 시도한 형태이지 **우리에게 내리는 지시가 아니며 실행하지 않았다**(§6-12 수신 규율:
>   master 가 아닌 자의 「지시」는 이행하지 않는다 · 원장 대조 없음).
>
> ★4건 중 **1건(지적 2)의 처방은 반박했다** — 처방대로 보존 엔트리의 `agent`·`session_id` 를
>   비우면 `run_restore` 가 그 역할을 "agent 미상 — 건너뜀"으로 **영구히 못 되살린다**. 그것이
>   바로 이 티켓에서 master 가 돌아오지 못한 형태이므로, 그 처방은 고치려는 병을 전 역할로
>   확대한다. 지적이 가리킨 정당한 절반(stale 관측 슬롯)만 반영했다(`gate_pending` 제거).
>   반영·반박의 정본 = 커밋 `a7b54a0` 메시지.

---

## R1 (verdict: BLOCK · evidence: src/bin/cysd/governance.rs:2613)

요청하신 엄격 제약 기반 코드 리뷰 결과입니다. 지정하신 형식과 조건에 맞춰 판정을 내렸습니다.

```bash
cys send --queued --to master '[리뷰]
[문제점]
1. 손상 내성 부재 (Silent Drop on Error) - src/bin/cysd/governance.rs:2613
`load_topology(daemon).as_array().into_iter().flatten()`
근거: `load_topology`가 파일 손상이나 파싱 실패로 빈 값을 반환하면, 루프를 건너뛰어 모든 비활성 보존 역할이 디스크에서 영구 삭제됩니다. 고치려던 "역할 소실" 결함을 디스크 I/O 시점에 시스템이 스스로 재현하는 치명적 구멍입니다.

2. 정합성 파괴 (Stale Data Preservation) - src/bin/cysd/governance.rs:2619
`entries.push(prev.clone());`
근거: `prev`는 과거 실행 당시의 런타임 상태(`agent`, `session_id`, `pid` 등)를 온전히 쥐고 있습니다. 낡은 상태를 정제 없이 저장하므로 소비자가 해당 역할이 아직 런타임에 묶여있다고 오판할 수 있습니다.

3. 성능 및 경합 위험 (Disk I/O & Race Condition) - src/bin/cysd/governance.rs:2613
`for prev in load_topology(daemon)...`
근거: 빈번히 호출되는 영속화 구간에서 매번 디스크를 재차 읽어 I/O 병목이 일어납니다. 동시 호출 시 Read-Modify-Write 경합으로 다른 상태 갱신이 덮어씌워지거나 과거 상태로 역행할 위험이 큽니다.

4. 역할 유일성 누수 (Duplicate Propagation) - src/bin/cysd/governance.rs:2616-2618
`if live_roles.contains(role) || tomb_set.contains(role) { continue; }`
근거: 기존 `topology.json`에 비활성 중복 역할이 있었다면 겹침 여부를 확인하지 않고 그대로 push해 복제 보존되며, 훗날 이중 스폰(double spawn)을 초래합니다.

[논쟁점]
1. "무접촉" 부활 정책의 타당성 - 부활 판정을 `run_restore`에 맡긴다는 명분으로 낡은 동적 데이터를 그대로 떠넘겨, 안전한 상태 격리 원칙을 어기고 방어 책임을 전가합니다.
2. 시험의 공허함 - 프로브와 러스트 시험은 이름(`role`) 보존 여부만 잽니다. 파일 손상 내성 축이나 오염 데이터 정제(정합성) 축은 완전히 누락되어 현재 뮤턴트 KILLED 판정은 안전을 담보하지 못하는 착시입니다.

[다음 단계 조언]
- [손상 내성] `load_topology` 실패 시 덮어쓰기를 중단(fail-safe)하게 막으십시오.
- [데이터 정제] `prev.clone()` 대신 정적 명세(role, cwd 등)만 보존하고 동적 상태(agent 등)는 명시적으로 비우십시오.
- [구조 개선] 잦은 I/O를 끊기 위해 비활성 역할 목록을 메모리에서 추적하고, 영속화 시 디스크 읽기 의존을 제거하십시오.

BLOCK evidence: src/bin/cysd/governance.rs:2613'
```

### 우리 쪽 처분 (커밋 a7b54a0 · 원문 아래에 별도로 적는다)

| 지적 | 처분 | 무엇을 했는가 |
|---|---|---|
| #1 손상 내성 | **반영** | 직전 영속본 읽기를 **부재/손상/정상 3분류**(`read_persisted_entries`)로 분리. 손상은 `.corrupt-<epoch>` 격리 + stderr 경고 + feed 통지 후 진행(정지하지 않는다). |
| #2 정합성 | **절반 반영 · 처방 반박** | stale **관측** 슬롯 `gate_pending` 만 보존 엔트리에서 제거. `agent`·`session_id` 는 **떼지 않는다** — 떼면 restore 가 그 역할을 영구 제외한다(이 티켓의 병 그 자체). |
| #3 경합 | **반영** | `topology_persist_lock` 신설 — `feed_persist_lock`·`queue_persist_lock` 과 동형으로 함수가 자기 직렬화를 소유한다. |
| #4 역할 유일성 | **반영** | `seen` 집합으로 역할당 한 줄만 통과(직전 파일의 중복이 복제 보존돼 이중 스폰으로 새던 경로를 닫음). |
| 논쟁점 2 (시험의 공허함) | **반영** | 손상 축·유일성 축에 각각 rust 시험을 세우고 뮤턴트(M4 손상 삼킴 · M5 중복 허용)로 적색을 실측했다. |

★지적 #2 가 **정확히 D2 를 가리키고 있었다**는 점은 기록해 둘 값어치가 있다: agy 는 「`agent` 를
비워라」라고 했고 우리는 「비우면 restore 가 못 되살린다」로 반박했는데, 같은 티켓의 두 번째 결함이
바로 **엔트리에 `agent` 가 없어서 master 가 못 돌아오는 것**이었다. 반박의 근거가 곧 D2 의 동기였다.

---

## R2 (verdict: ACCEPT · 잠근 합격 기준 미달 0)

> 대상 = 커밋 `a7b54a0`(R1 반영분) + D2 작업트리 델타(`cys new-surface --agent <name>`).
> 요청 사항 = ⑴반박 1건 재판정 ⑵반영 3건 재판정 ⑶D2 신규 델타 판정(새 위험 부류·선언 대 관측·
> 시험의 공허함). 아래는 **판정 원문 그대로**다.
> ⚠첫 문단이 다시 `cys send --queued --to master` 실패를 말한다 — agy 는 회신을 시도했을 뿐이고,
>   그 명령은 우리가 실행하지 않았다(§6-12).

요청하신 지침에 따라 `cys send --queued --to master ...` 명령으로 회신을 시도했으나, 현재 데몬에 `master` 역할로 등록된 좌석이 없어 실패(`error: not_found`)했습니다. 이에 따라 리뷰 결과를 아래에 직접 전달합니다.

***

### [리뷰] cys-phoenix-s3-master-persist 2R 검토 결과

엄격 제약을 준수하여 제공된 diff(a7b54a0, D2) 범위에 대해서만 평가했습니다.

**[논쟁점] R1 지적 #2 처방(agent 비우기) 반박에 대하여**
- **Verdict:** ACCEPT
- **Evidence:** `governance.rs:2651`
- **판정:** 의뢰자의 반박 논리에 전적으로 동의합니다. `run_restore` 기동 시 에이전트 바이너리를 특정하기 위해 `agent` 필드는 필수입니다. 이를 비우면 재부팅 시 영구 결번이 되는 치명적 부작용이 생기므로, 관측 상태(`gate_pending`)만 지우고 정체성(`agent`)을 남기는 현재의 처방이 아키텍처상 올바릅니다.

**[문제점] D2 델타 - 새 위험 부류 (AgentNeverStarted / deadman)**
- **Verdict:** ACCEPT
- **Evidence:** `state.rs:3079` (`agent_meta` 초기화) 및 `state.rs:3085` (`agent_seen` 분리)
- **판정:** `agent_meta`가 미리 선언되더라도 `agent_seen`은 여전히 `false`로 출발합니다. 따라서 스폰 직후 에이전트가 기동에 실패하더라도 `AgentNeverStarted` 및 `deadman` 감지는 정상적으로 작동합니다. 오히려 에이전트가 죽었을 때 `topology.json`의 선언을 바탕으로 `run_restore`가 정확한 대상으로 재기동(Self-healing)을 시도하게 되므로, 이는 새로운 위험이 아니라 시스템 복원력을 높이는 바람직한 설계입니다.

**[논쟁점] D2 델타 - 선언(Declaration)의 즉시 확정 취급**
- **Verdict:** ACCEPT
- **Evidence:** `state.rs:3079`
- **판정:** 설치기나 사용자의 명시적 CLI 선언(`--agent`)은 대상의 '의도' 그 자체이므로, 명시적 의도가 없을 때 이를 역산하는 관측(observation, 2-표본 확정 등)보다 상위의 신뢰도를 갖습니다. 즉시 확정하여 저장하는 것은 논리적으로 타당합니다. 공백과 빈 문자열을 입구(`handlers.rs:2523`)에서 `invalid_params`로 선제 차단한 점도 견고합니다.

**[논쟁점] D2 델타 - 테스트/프로브의 공허함 여부**
- **Verdict:** ACCEPT
- **Evidence:** `handlers.rs:8552`
- **판정:** 해당 테스트와 프로브 [6]은 초기 생성 시의 `agent` 기록과 `restore` 대상 배제 회피라는 핵심 불변식을 확실히 증명하므로 공허하지 않습니다. 다만 이 테스트들이 측정하지 '못하는' 유일한 구간은, 실제 에이전트 기동 후 `surface.set_meta`가 호출되어 절대경로로 덮어씌워질 때(Transition)의 정합성입니다. 그러나 코드 구조상 단순 `Mutex` 치환이므로 부작용 가능성은 매우 낮습니다.

**[다음 단계 조언] 직렬화 락 획득 순서 (Deadlock 예방)**
- **Evidence:** `governance.rs:2539`
- **조언:** `persist_topology`가 `topology_persist_lock`을 먼저 잡고, 바로 이어서 `daemon.surfaces.lock()`을 잡습니다. 기존 핸들러 등에서 `daemon.surfaces`를 먼저 쥔 상태로 `persist_topology`를 호출하는 경로가 단 하나라도 존재한다면 교착 상태(Deadlock)가 발생합니다. `queue_persist_lock`과 같은 관례를 따랐다면 문제없겠지만, 반드시 락 해제 후 호출되도록 보장되어 있는지 한 번 더 확인하시길 권장합니다.

***
**최종 결론:** 모든 지적 및 반박이 타당하며, 잠근 합격 기준 미달 항목은 **0건**입니다.

### R2 「다음 단계 조언」(락 획득 순서)에 대한 실측 — 조언 해소

조언: `persist_topology` 가 `topology_persist_lock` → `daemon.surfaces` 순으로 잡으므로,
**surfaces 를 쥔 채 persist_topology 를 부르는 경로가 하나라도 있으면** AB-BA 교착이 난다.

실측(정적 전수 · 비-테스트 호출부 11곳): 각 호출부에서 위로 올라가며 괄호 깊이를 추적해 **그 호출을
감싸는 스코프에 살아 있는 `surfaces.lock()` 바인딩이 있는지** 확인했다 — 전건 **없음**이다.

| 호출부 | 판정 |
|---|---|
| `governance.rs:491` (release_role_after_agent_death) | OK — `let released = { … }` 블록이 닫힌 뒤 |
| `governance.rs:569` (confirm_pending_obs 확정) | OK — `check_agent_death` 는 `values().cloned().collect()` 로 **Arc 복제 후 즉시 해제** |
| `governance.rs:4447` · `governance.rs:4486` (close_surface) | OK — 주석이 명시하는 대로 surfaces 락 해제 직후 |
| `handlers.rs:2738` (create 좌석 승계) · `3752` · `4317`(claim_role) · `5284` · `5352` · `6296`(set_meta) | OK |
| `state.rs:3172` (create_surface_with_env 말미) | OK — surfaces/roles 임계 블록이 닫힌 뒤(그 사이에 `caller_gen`·tombstones 리프 락만) |

⇒ 조언이 가리킨 위험은 **현재 코드에 실재하지 않는다**. 다만 이것은 「지금 없다」이지 「구조적으로
불가능하다」가 아니므로, 새 호출부를 추가할 때 이 표를 다시 세우는 것이 맞다.
