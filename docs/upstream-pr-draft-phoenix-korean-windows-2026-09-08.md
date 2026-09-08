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

## Notes / limits (honest)

- The Windows CI step is **wired but has never executed** in this branch. What is measured today is
  the macOS hostile-locale reproduction plus the mutation check.
- `chcp 949` in the Windows step is a *strengthening*, not the basis of the verdict: the smoke gives
  its child `PYTHONUTF8=0` and `PYTHONIOENCODING=cp949` directly, so the axis survives even if `chcp`
  has no effect on Python's locale codec on that runner.
- A separate observation from the same customer machine — `topology.json` had no `master` entry even
  though `cys list` showed `role=master` — is **not** addressed by this PR. It has its own candidate
  mechanisms and is not an encoding problem. It is tracked separately.
