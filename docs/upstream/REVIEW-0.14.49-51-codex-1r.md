# REVIEW-0.14.49-51-codex-1r — ⓓ 보안 경계 codex 1R 원문(전재 · 무편집)

> TICKET=cysr-1110-vendor · 대상 = 병합 ba38b6aa · 호출 = `~/.claude/channels/codex-call.sh --effort high`(22:01:13~22:07:54 KST · rc 0) · 의뢰문 = `javis_orchestra.py review-prompt` + 질문 Q1~Q4.
> 정본 JSON 은 codex 쓰기 루트 밖이라 저장되지 않았다(원문 말미) — 이 파일이 원문 사본이다.


verdict: `REVISE`  
revision: `ba38b6aab4f1f543cc836f37df1f41cf716630b4`

[문제점]

- `blocking` — hooks 보고가 팩 밖 파일을 읽을 수 있습니다. 매니페스트의 `hooks/../../...`가 접두 검사만 통과해 `pack_dir.join()`에 들어가며, 디스크 심링크도 따라갑니다. [src/pack.rs:2489](/Users/oogisoogi/cys-terminal-src-wt/rebase-01451/src/pack.rs:2489), [src/pack.rs:2353](/Users/oogisoogi/cys-terminal-src-wt/rebase-01451/src/pack.rs:2353)
- `blocking` — 휴지통 루트는 RPC 진입에서 한 번만 검사되고, 비동기 삭제 시 경로를 다시 해석합니다. 루트/부모 교체 TOCTOU로 격리 루트 밖 동명 디렉터리에 `rename`·`remove_dir_all`이 도달할 수 있습니다. [trash.rs:1243](/Users/oogisoogi/cys-terminal-src-wt/rebase-01451/src/bin/cysd/trash.rs:1243), [trash.rs:971](/Users/oogisoogi/cys-terminal-src-wt/rebase-01451/src/bin/cysd/trash.rs:971), [trash.rs:1018](/Users/oogisoogi/cys-terminal-src-wt/rebase-01451/src/bin/cysd/trash.rs:1018)
- `major` — UI 타이핑 확인은 IPC 경계에 결박되지 않습니다. Tauri 삭제 명령은 `confirm_id/names/digest`만 받고 토큰을 자동 부착하므로 WebView 호출자가 미리보기 후 타이핑 없이 삭제를 호출할 수 있습니다. [main.rs:5152](/Users/oogisoogi/cys-terminal-src-wt/rebase-01451/src-tauri/src/main.rs:5152), [trashconfirm.ts:27](/Users/oogisoogi/cys-terminal-src-wt/rebase-01451/ui/src/trashconfirm.ts:27), [trash.rs:1977](/Users/oogisoogi/cys-terminal-src-wt/rebase-01451/src/bin/cysd/trash.rs:1977)
- `major` — `destroy_dept`의 `name`과 `CYS_TRASH_STAMP`가 경로 성분으로 검증되지 않습니다. `../` 입력으로 격리 목적지를 `cys-trash` 밖으로 정규화할 수 있습니다. [javis_org.py:714](/Users/oogisoogi/cys-terminal-src-wt/rebase-01451/cysjavis-pack/bin/javis_org.py:714), [javis_org.py:795](/Users/oogisoogi/cys-terminal-src-wt/rebase-01451/cysjavis-pack/bin/javis_org.py:795), [cys-dept:368](/Users/oogisoogi/cys-terminal-src-wt/rebase-01451/cysjavis-pack/bin/cys-dept:368)
- `major` — 공유 `.producer` 표식의 소유권 판정은 원자적이지 않습니다. 판독 실패는 `cur=None`으로 접히며, read-then-replace 경합으로 다른 생산자의 열린 창을 덮을 수 있습니다. [javis_org.py:680](/Users/oogisoogi/cys-terminal-src-wt/rebase-01451/cysjavis-pack/bin/javis_org.py:680), [cys-dept:301](/Users/oogisoogi/cys-terminal-src-wt/rebase-01451/cysjavis-pack/bin/cys-dept:301)
- `major` — 공장 초기화도 계획과 실행 사이 부모 경로를 재검증하지 않고 `rename`합니다. 확인창 대기 중 루트가 심링크로 교체되면 계획과 다른 객체를 옮길 수 있습니다. [factory_reset.rs:1622](/Users/oogisoogi/cys-terminal-src-wt/rebase-01451/src/factory_reset.rs:1622), [factory_reset.rs:1656](/Users/oogisoogi/cys-terminal-src-wt/rebase-01451/src/factory_reset.rs:1656)

[논쟁점]

- Q1은 통과합니다. 판독 실패는 `try_load_records`의 `Err`로 전파되고 `mutate_records`가 쓰기 없이 중단합니다. BOM+유효 JSON은 두 경로가 동일하게 읽으며, 스케줄 건너뜀은 두 저장소의 안정된 원자료 모두에서 접두 흔적이 없을 때만 열립니다. [approval.rs:818](/Users/oogisoogi/cys-terminal-src-wt/rebase-01451/src/bin/cysd/approval.rs:818), [approval.rs:924](/Users/oogisoogi/cys-terminal-src-wt/rebase-01451/src/bin/cysd/approval.rs:924), [schedule.rs:1871](/Users/oogisoogi/cys-terminal-src-wt/rebase-01451/src/bin/cysd/schedule.rs:1871)
- hooks 보고 자체에는 팩·소유권표·서명 상태 쓰기가 없습니다. FIFO·장치는 거부되지만 위 심링크/매니페스트 경로 문제가 남습니다.
- 비활성 Windows 빌드의 삭제는 꺼집니다. [trash.rs:1434](/Users/oogisoogi/cys-terminal-src-wt/rebase-01451/src/bin/cysd/trash.rs:1434), [Cargo.toml:26](/Users/oogisoogi/cys-terminal-src-wt/rebase-01451/Cargo.toml:26)
- `reap`은 휴지통을 삭제하지 않고 `TRASH-OLD`만 출력합니다. 남은 실제 휴지통 `remove_dir_all`은 오너 삭제 집행 경로뿐입니다. 공장 초기화의 삭제 호출은 임시 캐시·센티널·launchd plist·팩 심링크 정리에 한정됩니다. [cys-dept:3444](/Users/oogisoogi/cys-terminal-src-wt/rebase-01451/cysjavis-pack/bin/cys-dept:3444), [factory_reset.rs:1813](/Users/oogisoogi/cys-terminal-src-wt/rebase-01451/src/factory_reset.rs:1813)
- 충돌 해소는 `HOLD`와 `TRASH-OLD`, `expect_gen`과 rc=12를 함께 보존했습니다. 결함은 `.producer` 병합 안전장치가 실제 동시성을 봉인하지 못한 부분입니다.

[다음 단계 조언]

1. hooks rel의 `..`·절대경로를 거부하고 심링크를 `Unreadable`로 분류하십시오.
2. 휴지통 및 factory-reset 작업을 디렉터리 핸들 상대 no-follow 연산으로 결박하십시오.
3. 파괴 IPC에 네이티브 단회 확인 nonce를 추가하거나 인간 확인이 보안 경계가 아님을 합격 기준에서 명시하십시오.
4. 부서명·stamp를 검증하고 `.producer`를 잠금 또는 생산자별 표식으로 바꾸십시오.

정본 JSON은 저장되지 않았습니다. 요청 경로가 현재 허용된 쓰기 루트 밖이라 파일 추가가 정책상 거부됐고, 최종 확인에서도 파일이 없었습니다:

`/Users/oogisoogi/.cys/pack/round/_reviews/cysr-1110-vendor___보안_경계_검토___원작자_v0.14.49_51_병합_ba38b6aa_의_상태_스키마_판독_팩_소유권_삭제_로-r1-reviewer1.json`
