# Upstream PR 본문 초안 — Phoenix cold-boot dies on Korean Windows (cp949)

> **상태 = 초안(draft)입니다. 발신하지 않았습니다.** upstream(`idoforgod/cys-terminal`)으로의 PR 발신은
> 오너 게이트입니다(외부 발행). 이 문서는 그 게이트에 올릴 본문과 근거를 담을 뿐입니다.
> 작성 = TICKET=cys-phoenix-korean-windows · 2026-09-08 · 대상 커밋 `07ab986`(포크 로컬).
>
> **아직 채워지지 않은 칸이 하나 있습니다**: 아래 "CI evidence" 의 Windows 러너 링크입니다.
> 이 브랜치는 push 되지 않았으므로 Windows CI 가 **한 번도 돌지 않았습니다**. 링크를 비운 채로
> 보내지 마시고, push 후 실제 run URL 을 채우거나 그 칸을 통째로 지우고 "not yet run" 이라고
> 적으십시오 — 돌지 않은 러너를 근거처럼 보이게 두는 것이 가장 나쁜 선택입니다.

---

## Title

`fix(phoenix): make cold-boot restore independent of the locale codec (Korean Windows / cp949)`

## Summary (EN)

On a Korean Windows machine, `javis_phoenix.py restore --auto` dies during cold boot and **no role is
ever revived**. Python's default text codec there is the console/ANSI code page (`cp949`), not UTF-8,
and the phoenix journal and `topology.json` are written as UTF-8.

The failure is a two-step chain, and the second step is what makes it fatal:

1. `load_journal()` calls `json.load(open(p))`. With the locale codec that raises
   `UnicodeDecodeError: 'cp949' codec can't decode byte 0xe2` — `0xe2` is the first byte of the
   UTF-8 em dash `—` that appears in our own log/journal text.
2. The handler for that exception calls `log()`, which does `sys.stdout.write(...)` on a message that
   itself contains `—`. That raises `UnicodeEncodeError: 'cp949' codec can't encode character '—'`.

So **the error path dies in the same way the happy path did**. There is no diagnostic left behind and
the restore chain stops. Revived roles: 0.

There is a quieter variant of the same defect: `read_topology()` catches the exception and returns
`{"entries": []}`. The daemon then honestly reports "0 dead roles to revive" while the topology file
on disk is perfectly fine. A silent wrong answer is worse than the crash.

Two spawn layers had drifted apart as well. `spawn_env_pairs()` (shell-mediated spawns: panes,
scheduled jobs, hooks) already forced `PYTHONUTF8=1`. `python_command()` — the factory used for
*direct* Python spawns — did not, and cold-boot auto-restore (`run_auto_restore_once`) goes through
that factory. The guard existed, but not on the path that mattered.

### Why CI did not catch this

`windows-latest` runners use an English code page (`cp1252`), which **can** encode `—`. macOS and
Linux runners are UTF-8. The bug needs a locale codec that is neither UTF-8 nor able to represent the
characters we actually print — that is exactly the customer's machine and none of our runners.

## 요약 (KR)

한국어 Windows 에서 콜드부트 부활이 0 건이 됩니다. 그 기계의 파이썬 기본 텍스트 코덱이 콘솔
코드페이지(`cp949`)인데 저널·`topology.json` 은 UTF-8 이기 때문입니다.

연쇄는 두 단계이고, **두 번째가 이 결함을 치명적으로 만듭니다**:

1. `load_journal()` 의 `json.load(open(p))` 가 `UnicodeDecodeError: 'cp949' … 0xe2` 로 실패합니다
   (`0xe2` = 우리가 직접 쓰는 「—」의 UTF-8 첫 바이트).
2. 그 예외를 처리하려는 `log()` 의 `sys.stdout.write` 가 같은 「—」에서
   `UnicodeEncodeError: 'cp949' codec can't encode character '—'` 로 다시 죽습니다.

즉 **오류 경로가 정상 경로와 똑같이 죽습니다.** 진단조차 남지 않고 부활이 멈춥니다.

조용한 쌍둥이도 있습니다: `read_topology()` 는 같은 예외를 삼키고 `entries=[]` 를 돌려줍니다.
그러면 데몬은 디스크의 토폴로지가 멀쩡한데도 "부활 대상 죽은 역할 0" 이라고 **정직하게 틀린
보고**를 합니다. 조용한 오답이 크래시보다 나쁩니다.

스폰 층도 갈라져 있었습니다. `spawn_env_pairs()`(셸 경유 — pane·스케줄 잡·훅)는 이미
`PYTHONUTF8=1` 을 실었지만, **직스폰 팩토리** `python_command()` 는 싣지 않았고, 콜드부트
auto-restore 가 바로 그 팩토리를 탑니다. 가드는 있었으나 정작 필요한 경로에 없었습니다.

## Reproduction

No Korean Windows machine is required. The disease is "the default locale codec is not UTF-8", and
that can be produced anywhere:

```bash
# 1) plant a journal that contains a UTF-8 em dash
printf '{"ticket_id":"t","roles":{"master":{"note":"부활 대상 죽은 역할 0 \xe2\x80\x94"}}}' > journal-t.json

# 2) run with a non-UTF-8 locale codec
PYTHONUTF8=0 LC_ALL=C PYTHONCOERCECLOCALE=0 PYTHONIOENCODING=cp949 \
  python3 -c 'import json; print(json.load(open("journal-t.json")))'
# -> UnicodeDecodeError: 'ascii' codec can't decode byte 0xe2   (macOS/Linux)
# -> UnicodeDecodeError: 'cp949' codec can't decode byte 0xe2   (Korean Windows)
```

On the customer machine the codec name is `cp949`; on macOS with `LC_ALL=C` it is `US-ASCII`. The
codec differs, the disease does not.

The repository now carries this as an executable check:

```bash
python3 cysjavis-pack/bin/javis_phoenix_encoding_smoke.py
```

It runs seven cases in a child process forced into a hostile locale, and it isolates itself in a
temp directory (no daemon, no live state).

## What changed

**Pack Python — stop depending on the locale codec** (`cysjavis-pack/bin/`)
- `javis_phoenix.py` pins `sys.stdout`/`sys.stderr` to `utf-8` with `errors="backslashreplace"` at
  import time, with a `TextIOWrapper` fallback for runtimes without `reconfigure`.
- Every text-mode `open()` now names `encoding="utf-8"` — reads and writes, including the `open()`
  calls embedded in the generated `manual_restore.sh`, because that script runs on the very machine
  that is already sick.
- Same sweep for the siblings phoenix executes: `javis_state_snapshot.py`, `javis_backup.py`,
  `javis_event.py`. Their self-tests pass.
- `subprocess` calls that read **our own** UTF-8 tools now name `encoding="utf-8", errors="replace"`.
  Calls to **Windows native tools** (`schtasks`, `taskkill`) are deliberately left alone — their
  output *is* the console code page, and forcing UTF-8 there would corrupt correct Korean output.

We did **not** rewrite the log strings to avoid `—`. Changing the wording only moves the failure to
the next non-ASCII character someone types.

**Daemon — make both spawn layers carry the same contract** (`src/`)
- `cys::python_command()` now injects `PYTHONUTF8=1` and `PYTHONIOENCODING`.
- `spawn_env_pairs()` gains the matching `PYTHONIOENCODING` pair.
- The office bridge (a `tokio` builder that cannot use the factory) consumes the same constants.
- The value is `utf-8:backslashreplace`, not bare `utf-8`. Bare `utf-8` implies `strict`, and a
  strict stdout raises the moment we print a filename that was read with `surrogateescape` — which
  would reintroduce the very failure through a different door.

**Tests**
- `javis_phoenix_encoding_smoke.py` — 7 cases under a hostile locale. Before the fix: 7/7 red.
  After: 7/7 green.
- `python_encoding_contract_is_identical_in_both_spawn_layers` (Rust) — pins that the two spawn
  layers carry the *same* values, so removing the pair from either one turns it red.
- `scripts/phoenix_encoding_mutants.py` — mutation check. Reverting each fix must make its check
  red; all mutants are killed.
- CI: one step on the macOS lane (`ci-branch.yml`) and one on the Windows lane
  (`windows-health.yml`, preceded by `chcp 949`).

## CI evidence

<!-- ⚠ 채우거나 지우십시오. 이 브랜치는 아직 push 되지 않아 Windows 러너가 0회 돌았습니다. -->
- macOS lane: `<run URL>`
- Windows lane: `<run URL>`

## Second defect in the same report: the fleet record deletes itself (S3)

The same customer report carried a second symptom: after a reboot, `topology.json` had the four
department roles but **no `master`**, even though `cys list` had shown `role=master` right after
install. `tombstones` was empty, and `updated_at` was the cold-boot timestamp **+9 seconds** — the
file had been rewritten just after boot, and `master` was gone from that rewrite.

### Cause

`persist_topology` built `entries` as pure **actual-state**: only seats that are alive *right now*
and hold a role *right now*. Right after a cold boot there are zero seats, so the moment anything
creates a single seat, persistence runs and **every role that is not currently alive disappears from
the file**.

Reproduced in isolation (`scripts/s3_coldboot_probe.py`, step [4]): plant five roles
(`master`, `cso`, two reviewers, `worker`), start the daemon, create **one** seat (`cso`) — the file
is left holding `cso` alone. That is the customer's end state.

The damage is self-amplifying: once the record is gone, **the next boot has nothing left to restore
from**. A role can be lost by one unlucky ordering and can never come back on its own.

### Fix

Narrow the deletion condition to **intentional deletion only** — which is the direction this project
already committed to with "deliberate removal outweighs forced revival". An entry is preserved when
it was in the previous persisted file, is not currently live, and is not tombstoned.

Revival policy is untouched. This change only protects the record; what gets revived is still decided
by `run_restore` / phoenix, and those still skip tombstoned roles. **Tombstones still win** — a
deliberately retired role is not preserved.

### Verification

- Isolated probe (its own temp dir, own socket, own pack; process-group teardown; no live daemon,
  app or `~/.cys` touched): preservation axis PASS, tombstone axis PASS.
- The characterization test that had pinned the old behaviour is replaced by an invariant test, with
  the reason recorded in place so a future reader can see why it was turned around.
- Mutants 3/3 killed (`scripts/s3_topology_mutants.py`): remove the preservation, ignore tombstones,
  drop the live-dedupe.
- `cargo test --bin cysd` 830 pass · `--lib` 414 pass.

### What this does NOT fix (read this before assuming the symptom is gone)

**`master` still will not come back on that machine**, for a second and independent reason. The
installer creates it with `cys new-surface --role master --cmd <claude>`, and that path never records
an agent — `agent_meta` is only ever written by `surface.set_meta`, which `cys launch-agent` calls and
`new-surface` does not. So the entry carries `"agent": null`, and `run_restore` skips it:

```
· master: agent 미상 — 건너뜀 (claim-role로 등록된 pane)        # with --include-master
· master: 제외 (restore 실행자가 보통 master — --include-master로 포함)   # without it
```

Both messages are reproduced in the isolated probe (step [5]). Preserving the record is necessary but
not sufficient; the second half is an installer/CLI contract question and is being decided separately.

## 두 번째 결함 — 함대 기록이 스스로를 지운다 (S3 · 한국어)

같은 제보에 두 번째 증상이 있었습니다. 재부팅 뒤 `topology.json` 에 부서 역할 4개는 있는데
**`master` 만 없었습니다.** 설치 직후 `cys list` 는 `role=master` 를 보여줬는데도 그렇습니다.
묘비는 비어 있었고 `updated_at` 은 콜드부트 **+9초** — 부팅 직후 파일이 다시 쓰였고 그 재기록에서
master 가 빠진 것입니다.

**원인**: `persist_topology` 의 `entries` 는 순수 actual-state 였습니다. 지금 살아 있고 지금 역할을
쥔 좌석만 조립합니다. 콜드부트 직후에는 좌석이 0이므로, 무엇이든 좌석을 **하나만** 만들어도 그
순간 영속이 돌고 **살아있지 않은 역할이 전부 파일에서 사라집니다.**
격리 재현: 5역할을 심고 좌석 하나(`cso`)만 만들자 파일에 `cso` 하나만 남았습니다.
★자기증폭이 본체입니다 — 한 번 사라지면 **다음 부팅엔 되살릴 근거조차 없습니다.**

**수리**: 삭제 조건을 **의도 삭제(묘비) 하나로** 좁혔습니다. 이 저장소가 이미 세운 「의도삭제 >
강제부활」과 같은 방향입니다. 부활 정책은 건드리지 않았고, 묘비는 그대로 이깁니다.

**이 수리가 고치지 못하는 것**: 그 기계에서 **master 는 여전히 돌아오지 않습니다.** 설치기가
`cys new-surface --role master --cmd <claude>` 로 세우는데 그 경로는 agent 를 기록하지 않기
때문입니다(`agent_meta` 는 `surface.set_meta` 만 쓰고, 그것을 부르는 것은 `launch-agent` 이지
`new-surface` 가 아닙니다). 그래서 엔트리가 `"agent": null` 이고 `run_restore` 가 건너뜁니다.
기록 보존은 필요조건이지 충분조건이 아니며, 나머지 절반은 설치기·CLI 계약 문제로 따로 판단합니다.

## Notes / limits (honest)

- The Windows CI step is **wired but has never executed** in this branch. What is measured today is
  the macOS hostile-locale reproduction plus the mutation check.
- `chcp 949` in the Windows step is a *strengthening*, not the basis of the verdict: the smoke gives
  its child `PYTHONUTF8=0` and `PYTHONIOENCODING=cp949` directly, so the axis survives even if `chcp`
  has no effect on Python's locale codec on that runner.
- A separate observation from the same customer machine — `topology.json` had no `master` entry even
  though `cys list` showed `role=master` — is **not** addressed by this PR. It has its own candidate
  mechanisms and is not an encoding problem. It is tracked separately.
