# 윈 측정 의뢰 — hook-slim-1111 (팩 훅 속도·설정 마이그레이션) · 윈 master 집행용

> 맥 실측·구현은 worker-2(677)가 했다(가지 `fix/1111-hookslim`). 윈도우에서 같은 것을 재서 맥 숫자와 나란히 놓는다.
> **실 사용자 설정 파일에는 쓰지 않는다** — 1~3은 격리 HOME(시험용 임시 폴더)에서만 돈다. 4는 읽기만 한다.
> 유료·가입 0. 소요 약 20~30분.

## 0. 준비
- 저장소를 `fix/1111-hookslim`(또는 병합 뒤 int/1111) 로 맞추고 `cargo build --bin cys` 로 `target\debug\cys.exe` 를 만든다.
- Git for Windows 의 `bash.exe` 가 PATH 에 있어야 한다(팩 훅은 윈에서 `bash "<경로>"` 로 등록된다).
- 파이썬은 `py -3`.

## 1. 훅 실행 시간(변경 전·후) — 격리 HOME · 각 20회 p50/p95/max
```
git worktree add --detach ..\base-1110 eb4ef98c
py -3 -I scripts\bench_pack_hooks.py --shell bash --pack ..\base-1110\cysjavis-pack --transcript <아무 기록.jsonl 2~7MB> --out before_plain.json --n 20 --scenario plain
py -3 -I scripts\bench_pack_hooks.py --shell bash --pack cysjavis-pack            --transcript <같은 파일>            --out after_plain.json  --n 20 --scenario plain
py -3 -I scripts\bench_pack_hooks.py --shell bash --pack ..\base-1110\cysjavis-pack --transcript <같은 파일> --out before_seat.json --n 20 --scenario seat --round
py -3 -I scripts\bench_pack_hooks.py --shell bash --pack cysjavis-pack            --transcript <같은 파일> --out after_seat.json  --n 20 --scenario seat --round
```
- `plain` = 좌석 아닌 세션(사용자 개인 Claude). `seat` = cys 좌석 env. `--round` = 작업 폴더에 `_round` 가 있는 경우.
- 보낼 것: json 4개 전부(요약 금지 — 훅별 p50/p95/max·cold·rc·stdout 바이트가 다 들어 있다).
- 맥 기준값(10-27): 좌석 아님 변경 전 = 도구 훅 8~37ms · Stop 3개 50~71ms · inject-context 151ms(+1.4KB 주입) / 변경 후 = 전부 셸 기동 수준(설계 문서 §2 표).

## 2. 마이그레이션 상태표(S1~S11) — 실 바이너리 · 격리 HOME
```
py -3 cysjavis-pack\bin\tests\test_hook_slim.py --diff-out hookslim_win_diffs.md
```
- 기대: `HOOK-SLIM-OK`. 특히 S9(BOM·CRLF·역슬래시 명령·cp949 파일)를 윈 실물로 재는 것이 이 의뢰의 핵심이다.
- ⚠ 이 시험은 맥에서 만들었다 — 셸 단위 부분(FX·GT·DT)이 윈 경로 표기 때문에 깨지면 그 출력 전문을 그대로 보내 달라(수리는 677).
- 보낼 것: 전체 출력 + `hookslim_win_diffs.md`.

## 3. 답 뒤 대기(실 Claude Code) — 격리 팩 사본에 느린 대역을 넣어 동기/분리 비교
- 맥 절차(설계 문서 §4-3)와 같다: `reflect-scan.sh` 의 `javis_reflect.py` 를 8초 자는 대역으로 바꾼 팩 사본을 만들고,
  `claude -p "Reply with exactly: OK" --setting-sources project --settings <Stop 훅 1개짜리 json>` 를 `CYS_HOOK_STOP_SYNC=1`(동기) 와
  기본(분리)으로 각 2회. 맥 결과 = 동기 10.1·10.2초 → 분리 3.3·2.6초 · 분리 자식 산출물 4/4.
- 윈 특이점 확인: ① Git Bash 에 `nohup` 이 있는가(`command -v nohup`) — 없으면 분리는 `&` 만으로 돈다 ② claude 종료 뒤에도
  분리 자식이 살아서 산출물을 쓰는가(맥은 산다).

## 4. 실기 읽기 전용 대조(윈 노트북 실 설정 · 쓰기 0)
- `%USERPROFILE%\.claude\settings.json` 에 팩 훅(`.cys/pack/hooks/` 를 가리키는 command)이 몇 개인지, 사용자 훅이 몇 개인지,
  파일 첫 3바이트가 BOM 인지, 줄바꿈이 CRLF 인지 — 숫자만 보내 달라(내용 원문은 보내지 않는다).
- `%USERPROFILE%\.cys\state\hook-timing.log` 의 Stop 훅 경과 분포(훅별 n·1초 이상·10초 이상·최댓값).

## 5. 1.1.11 설치 뒤(병합·발행 뒤 윈 master 실기 때)
- 1.1.10 → 1.1.11 갱신 뒤 `%USERPROFILE%\.claude\settings.json` 의 팩 훅 0 · 사용자 훅·다른 키 그대로 · `.bak-cys-hookslim-<초>` 1개.
- `cys doctor` 의 hook 항목 = 「개인 프로필 팩 훅 0(옵트인 표지 없음 = 등록 안 함이 정상)」.
- 되돌리기 1줄: `copy %USERPROFILE%\.claude\settings.json.bak-cys-hookslim-<초> %USERPROFILE%\.claude\settings.json`
