# 1.1.16 통합 — 갈래별 남은 것 · 통합 때 볼 시험

원천 = `lane-facts.md`(같은 폴더) 각 갈래의 「3. 남은 것 / 📌」 절과 「2. 통합 때 볼 것」 절. 기준판 = dea2e1853.
출처는 lane-facts 가 적은 `파일:줄@커밋` 을 약어 없이 풀어 썼다(lane-facts 가 줄 번호를 안 준 곳은 그렇게 표시).
「(처리됨)」·「(뒤에 해소)」 표시는 lane-facts 원문이 그렇게 적은 경우만 붙였다 — 빠뜨리지 않으려고 이미 닫힌 항목도 행으로 남겼다.
「추출자 추론」 = lane-facts 를 만든 추출 좌석이 diff 를 읽고 짐작한 것(갈래 인계서에 없는 말 · 실행 안 해 봄).

---

## 표 1. 갈래별 남은 것

| 갈래 | 남은 것(원문 요지, 수치·이름 보존) | 출처 |
|---|---|---|
| debt-u | 📌1 윈 S2 미리 빌드 — (처리됨 06e3990f6 · master#1519072c) | HANDOFF.cysr-1116-debt-u-1119.md:129@e0953c7e0 |
| debt-u | 📌2 우분투 CI 이미지가 26.04 로 바뀐 것 — 다른 시험·스크립트의 GNU coreutils 가정(argv0·옵션) 훑기 → 「찾음 1 · 고치지 않음」: `src/update/realops.rs:1798` `fake_cysd_bin()`(#[cfg(unix)]) = /bin/sleep 을 cysd 이름으로 복사 → ubuntu 26.04 에서 돌리면 같은 결함 · 우리 크레이트 리눅스 cargo test 레인 0 → 지금 붉을 일 없음 | HANDOFF.cysr-1116-debt-u-1119.md:130, :152@e0953c7e0 |
| debt-u | 📌3 범주 3 에서 안 고친 것(기능 줄·팩 지침): `cysjavis-pack/agents.json:3·8` · `MASTER_DIRECTIVE.md:462` · `WORKER_DIRECTIVE.md:258` · `skills/appbuild-plan-debate`·`computer-control` SKILL.md → 델타 「그대로(1.1.17 기록)」 | HANDOFF.cysr-1116-debt-u-1119.md:131, :151@e0953c7e0 |
| debt-u | 📌4 같은 꼴 남은 자리(주석·문자열) → 고침 f79d6cdac · 8줄 · ⚠저장소 전반 master# 표식 420줄(이미 공개 B 에 328) · 「박사님」 146줄(B 에 137) = 일괄 정리는 별도 결정 | HANDOFF.cysr-1116-debt-u-1119.md:132, :150@e0953c7e0 |
| debt-u | 📌5 다음 공개 후보 목록에 `docs/integ-1116/ci_pack_steps.py` · `pubcand.sh` 추가 → 지킴 폴더 docs/integ-1116 경로는 허용 목록에 올 수 없음(rc 2) → 공개 안 됨 · 공개할 제품 시험 `scripts/tests/test_gen_released_hashes_extra_ref.py` 1 = 다음 후보 때 허용 목록에 더할 것 | HANDOFF.cysr-1116-debt-u-1119.md:133, :149, :64@e0953c7e0 |
| debt-u | 📌6 ci_step WARN 기준 = 게이트 시작 상태 — (처리됨 575ced14f) | HANDOFF.cysr-1116-debt-u-1119.md:134@e0953c7e0 |
| debt-u | 📌7 test_capgate_hook_shell · test_role_authority_shell 로컬 간헐 — 시간 의존 원인 규명 티켓 → 델타 「손대지 않음 · 새 좌석(flaky) 몫」 | HANDOFF.cysr-1116-debt-u-1119.md:135, :153@e0953c7e0 |
| debt-u | 📌8 pubcand 를 제외 목록(blocklist) 대신 B 기반 공개 허용 목록으로 → 고침 9ad430656 | HANDOFF.cysr-1116-debt-u-1119.md:136, :148@e0953c7e0 |
| debt-u | codex 2R: TODO 「[ ] H. codex 2R(수렴 확인) = master 대기열」 미체크 — 그러나 델타 3 에서 codex 2R(0172b7138 · BLOCK) master 처분 집행 · 「검토 왕복은 이번으로 끝(codex 3R 없음)」 | WORKER_TODO.cysr-1116-debt-u-1119.md:10@e0953c7e0 · HANDOFF.cysr-1116-debt-u-1119.md:195-197@e0953c7e0 |
| debt-u | 알려진 한계 ① push 차단 최장 접두 우회(codex B1) — 「그런 설정을 둔 기계에서 쓰기 전에 같은 명령으로 확인할 것」 | HANDOFF.cysr-1116-debt-u-1119.md:210-214@e0953c7e0 |
| debt-u | 알려진 한계 ② PUB_WITHHELD_OUT 운영자 경로 — 「저장소 안(`.git/` 등)을 가리키지 말 것」 | HANDOFF.cysr-1116-debt-u-1119.md:210-214@e0953c7e0 |
| debt-u | 알려진 한계 ③ ci_pack_steps 잡 수준 env 표류 — 「다음 판에서 env·시한 의미까지 PyYAML 로 대조」 | HANDOFF.cysr-1116-debt-u-1119.md:210-214@e0953c7e0 |
| debt-u | 알려진 한계 ④ r34 시한 오라클 완전성(부하로 런처가 30s 넘게 걸리면 거짓 붉음) | HANDOFF.cysr-1116-debt-u-1119.md:210-214@e0953c7e0 |
| debt-u | WORKER_TODO debt-u2 = 전 항목 [x] | WORKER_TODO.cysr-1116-debt-u2-1120.md:5-15@e0953c7e0 |
| flaky | 1차-1 동반 3종(refl·owner·role_authority)은 N=10 씩만 잼(20 아님) → 2차 ④ 에서 해소 | HANDOFF.cysr-1116-flaky-1120.md:88-94, :149@7dd80224e |
| flaky | 1차-2 `test_phoenix_c6_reap` 단독 시한 초과는 다루지 않았다 · 그 좌석에 「첫 실행 지연」 대조 권함 → 2차 ①: 첫 실행 탓 아님(원인 추적 = 조각 5 좌석 몫) | HANDOFF.cysr-1116-flaky-1120.md:88-94, :139@7dd80224e |
| flaky | 1차-3 같은 꼴(새 스텁 + 시한)이 이 5개 밖 팩 시험에도 있을 수 있다 → 2차 ② 14개 파일 고침 | HANDOFF.cysr-1116-flaky-1120.md:88-94, :108-135@7dd80224e |
| flaky | 1차-4 제품 쪽 관찰(고치지 않음): 실제 설치 직후·판 올림 직후 첫 `cys` 실행이 해소기 2초 시한에 걸려 env 폴백으로 강등될 수 있음 → 2차 ③ 실측 「해소기(2s) 차가움 20회 중 1회 env 폴백(master)」 · 「master#64fd3812 결정 = A안 → debt-d 이관 · B안 안 함」 | HANDOFF.cysr-1116-flaky-1120.md:88-94, :142, :145@7dd80224e · WORKER_TODO.cysr-1116-flaky-1120.md:26@7dd80224e |
| flaky | 1차-5 부하 주입 1회(04:34:45~04:49:15 · 4+2 프로세스 · load 최고 27) — 그 시간대 다른 좌석의 붉음은 재대조가 필요하다 | HANDOFF.cysr-1116-flaky-1120.md:94@7dd80224e |
| flaky | 📌(2차)-1 dept_name_guard `test_create_spawn_loser_preserves_live_winner` 전체 파일 실행 중 1회 붉음(load 18.2) · 단독 묶음 40회 미재현 | HANDOFF.cysr-1116-flaky-1120.md:157-161@7dd80224e |
| flaky | 📌(2차)-2 python `Popen.wait/communicate` 시한·Rust 시험 쪽 스텁은 이번 계측 밖 — 같은 꼴이 남았을 수 있음 | HANDOFF.cysr-1116-flaky-1120.md:157-161@7dd80224e |
| flaky | 📌(2차)-3 제품 preflight C82 가 만드는 cys 스텁도 첫 실행 비용을 시한 안에서 치른다(0.61s/5s · 여유 큼) | HANDOFF.cysr-1116-flaky-1120.md:157-161@7dd80224e |
| ccopen | 📌 절 없음. 좌석이 지시 밖으로 정한 것: `ui.open_panel`(말로 열기)은 「연다」로 둠 — 막으려면 `ccopen.ts` 표의 한 줄을 `notify` 로 바꾸면 됨(시험 ① 이 같이 바뀜) → master 확인 필요 | HANDOFF.cysr-1116-cc-autoopen.md:58-59@88def9658 |
| ccopen | 밝힌 단점: `--wait` 항목은 데몬 방치 스캔 (a) 대상이 아님 → master 가 끝내 안 보면 사람에게 화면 전환이 안 가고, 요청한 워커는 `--wait` 시간 초과(exit 3)로 끝나 master 에 「막힘」을 올림 | HANDOFF.cysr-1116-cc-autoopen.md:56@88def9658 |
| ccopen | 07:3x CC 등장 원인 미확정 — 후보 (가) 11-19 17:12:26 멈춤 때 이미 열려 있던 CC / (나) 의도 않은 클릭 · 「다음에 또 뜨면 `~/.cys/cc-open.log` 마지막 줄의 `cause=` 가 이 둘을 가른다」 | HANDOFF.cysr-1116-cc-autoopen.md:39-42@88def9658 |
| ccopen | 문구 불일치: 커밋·TODO 는 「자동 열기 = approval.stalled 만」인데 표 7행 `ui.open_panel` 도 열고, 시험 ① 은 「데몬 출처 자동 열기 = `approval.stalled`·`ui.open_panel` 둘뿐」 | WORKER_TODO.cysr-1116-cc-autoopen-1120.md:7@88def9658 · HANDOFF.cysr-1116-cc-autoopen.md:18-19, :63@88def9658 |
| ccopen | WORKER_TODO cc-autoopen = 전 항목 [x] | WORKER_TODO.cysr-1116-cc-autoopen-1120.md:3-9@88def9658 |
| asset-skills | 판 대조: 본부 좌석이 링크하는 팩 스킬 69 은 설치 팩 1.1.14 파일이다 | docs/HANDOFF-1116-asset-skills.md:67@1ff82d08a |
| asset-skills | notebook-source-pack 의 명령 정본 nlm-skill 은 팩에 싣지 않음(판정 = 링크) · 좌석에 없으면 `nlm skill install claude-code` 를 한 번 돌린다 | docs/HANDOFF-1116-asset-skills.md:69@1ff82d08a |
| asset-skills | 본부 원본은 그대로: `~/.claude/skills` 의 실디렉토리와 `~/.cys/local` 링크는 그대로 | docs/HANDOFF-1116-asset-skills.md:70@1ff82d08a |
| asset-skills | D4(범위 밖 · master 처리): skill-revisions 제안 43건 미적용(→ 뒤에 skill-revisions 갈래가 처리) · INDEX 「미반영」 2건 실제 반영됨 · 비밀 파일 deny 규칙 미적용 · INDEX `assets/…` 경로 2건 | docs/HANDOFF-1116-asset-skills.md:71@1ff82d08a |
| asset-skills | 이월: ppt-styles · portrait-cutout 은 설치 팩에 없다 — C84 WARN 「pack 스킬 미설치(5)」는 그때 사라진다 | HANDOFF-asset-skills.md:39@1ff82d08a |
| asset-skills | 이월: 의존물 위치 `~/.cys/deps/<스킬>` | HANDOFF-asset-skills.md:40-42@1ff82d08a |
| asset-skills | 이월: `javis_asset_fetch.py` 는 팩에서 뺐다(⑵ 원문 0건) · 코드는 9100fb07 에 있음 · 되살릴 때 codex 1R 지적 5건을 먼저 고친다 | HANDOFF-asset-skills.md:44@1ff82d08a |
| asset-skills | dept-1 예산 = 미측정(OAuth 만료) | HANDOFF-asset-skills.md:33@1ff82d08a |
| asset-skills | skill-fold: 증류 — 팩 메모리 편입은 master 판단 | HANDOFF-1112-skill-fold.md:160@1ff82d08a |
| asset-skills | skill-fold: 더 줄이려면 = 벤더 설명 수정(오너 결정) | HANDOFF-1112-skill-fold.md:73@1ff82d08a |
| skill-revisions | 43건 전수 처분 = 반영 21 · 일부 반영 2 · 이미 해소 4 · 안 함 8 · 새 기능 📌 4 · 박사님께 4 | docs/HANDOFF-skill-revisions-1120.md:8@f9ed0fcac · docs/SKILL-REVISIONS-1120.md:12-20@f9ed0fcac |
| skill-revisions | 📌 B5 narrated-motion(`tools/s2m_cues.py`) 큐마다 바깥 wav `engine: file` — A1·A3 로 say 를 공개본에서 막았으니 공개본을 만들 도구 길이 비어 있음 → 다음 티켓 1순위 권고 | docs/HANDOFF-skill-revisions-1120.md:31@f9ed0fcac · docs/SKILL-REVISIONS-1120.md:74@f9ed0fcac |
| skill-revisions | 📌 B6 transcription · caption-align(카탈로그) whisper.cpp 를 카탈로그 공급자로 — 「새 기능 · 팩 카탈로그 = 고위험 편성」 · master 결정 | docs/SKILL-REVISIONS-1120.md:75@f9ed0fcac · docs/HANDOFF-skill-revisions-1120.md:31@f9ed0fcac |
| skill-revisions | 📌 B7 video-verify · narrated-motion · motion-graphics-prompt 보고서 폴더의 검사 도구 5종을 스킬 자산으로 · master 결정 | docs/SKILL-REVISIONS-1120.md:76@f9ed0fcac |
| skill-revisions | 📌 B8 video-report-deck JetBrains Mono 글꼴 동봉 — 「라이선스 원문(OFL 1.1 로 알려짐) 미확인」 · master 결정 | docs/SKILL-REVISIONS-1120.md:77@f9ed0fcac |
| skill-revisions | 박사님께 B1 생성 음악 1순위(돈·새 길) | docs/HANDOFF-skill-revisions-1120.md:32@f9ed0fcac · docs/SKILL-REVISIONS-1120.md:70@f9ed0fcac |
| skill-revisions | 박사님께 B2 힉스필드 구독 | docs/SKILL-REVISIONS-1120.md:71@f9ed0fcac |
| skill-revisions | 박사님께 B3 Firefly 크레딧 — 뒤에 「B3(master 처분 · A안)」으로 일반 문구 반영 | docs/SKILL-REVISIONS-1120.md:72, :138@f9ed0fcac |
| skill-revisions | 박사님께 B4 공개본 목소리 유료 vs 사람 녹음·로컬 | docs/SKILL-REVISIONS-1120.md:73@f9ed0fcac |
| skill-revisions | 기억 카드 숫자 2건(License.html 67줄 · Supertonic 6파일) = master 몫 | docs/HANDOFF-skill-revisions-1120.md:33@f9ed0fcac · docs/SKILL-REVISIONS-1120.md:83-84@f9ed0fcac |
| skill-revisions | tools 기본값: 브리프는 −1 dBTP, `workflow-checklist.md` 납품 기준은 −2 dBTP — 어느 값으로 맞출지 확인 필요(권고 −2) | docs/HANDOFF-skill-revisions-1120.md:34@f9ed0fcac · docs/SKILL-REVISIONS-1120.md:85@f9ed0fcac |
| skill-revisions | 검증 편성: 독립 검증 좌석 + codex 1R 은 master 가 붙인다 · 이 좌석은 지적 1회 고침 대기 → (두 회차 모두 뒤에 처리됨) | docs/HANDOFF-skill-revisions-1120.md:35@f9ed0fcac · docs/SKILL-REVISIONS-1120.md:107-139@f9ed0fcac |
| skill-revisions | R6 audio-post-mix 설명 = 안 함(master 결정 = 다음 설명 손질 때) | docs/SKILL-REVISIONS-1120.md:120, :139@f9ed0fcac |
| skill-revisions | 독립 검증 R7~R10 = 「이번 지시 범위 밖(안 함)」 → 뒤에 codex 회차에서 2312 R7–R10 반영 | docs/SKILL-REVISIONS-1120.md:121, :134-137@f9ed0fcac |
| skill-revisions | 안 함: pixabay_music 카탈로그 문구 | docs/SKILL-REVISIONS-1120.md:86@f9ed0fcac |
| skill-revisions | 안 함: D3 video-stitch 자막 발동어 | docs/SKILL-REVISIONS-1120.md:87@f9ed0fcac |
| skill-revisions | 안 함: D6 | docs/SKILL-REVISIONS-1120.md:88@f9ed0fcac |
| skill-revisions | 안 함: §3 목록 관찰 | docs/SKILL-REVISIONS-1120.md:89@f9ed0fcac |
| b23 | 배달·승인·순환 판정은 바꾸지 않았다(표시 전용 · 그림자 단계) — 「blocked 면 입력 거절 · done 이면 배달 간격 단축」은 후속 판단 | HANDOFF.cysr-1116-borrow23-1119.md:89@33a72a906 |
| b23 | ③ 기본값 근거의 한계: 표준 벤치 4회차 · 「기본 자산 전체」 켬/끔 비교라 부트만 떼어 잰 값이 아님 | HANDOFF.cysr-1116-borrow23-1119.md:91@33a72a906 |
| b23 | 기록·안 고침 V-6 clear 직후 unknown 틈(0.68s~7s) | HANDOFF.cysr-1116-borrow23-1119.md:112@33a72a906 |
| b23 | 기록·안 고침 V-7 done 「봄」 = 사람 입력만 | HANDOFF.cysr-1116-borrow23-1119.md:112@33a72a906 |
| b23 | 기록·안 고침 V-8 윈 ConPTY PASSTHROUGH 없음 → 실기 판별 대기 | HANDOFF.cysr-1116-borrow23-1119.md:112@33a72a906 |
| b23 | 기록·안 고침 V-9 질의 응답 위조 길(DSR 계급) | HANDOFF.cysr-1116-borrow23-1119.md:112@33a72a906 |
| b23 | 기록·안 고침 (다) 「화면 입력 대기가 7501 idle/working 을 이김」 = 1.1.17 기록 | HANDOFF.cysr-1116-borrow23-1119.md:112@33a72a906 |
| b23 | Claude 좌석 안 도구 출력 ESC 흐름 = 미측정 | HANDOFF.cysr-1116-borrow23-1119.md:112@33a72a906 |
| b23 | 검증 좌석이 알린 부작용(codex 관리형 데몬이 0.170 을 스스로 받음) = master 판단 사안 | HANDOFF.cysr-1116-borrow23-1119.md:113@33a72a906 |
| b23 | codex 2R(②③ 고침분) = master 대기열 → (뒤에 §9 에서 처리) | HANDOFF.cysr-1116-borrow23-1119.md:132@33a72a906 |
| b23 | §8-1 「(다음)」 V-4 배선 시험 → 14af54e9c 로 반영 | HANDOFF.cysr-1116-borrow23-1119.md:121@33a72a906 |
| b23 | §8-1 「(다음)」 V-3 후속 — ④ 문단 줄 수를 기준과 같게(§2 줄 번호 핀 · 상한 래칫 MASTER 86,949 · CEO 102,435) → 70b83cfc5 로 반영 | HANDOFF.cysr-1116-borrow23-1119.md:122@33a72a906 |
| b23 | 알려진 한계 §9-1: 같은 청크 질의 뒤 보고(codex 2R 2번 — 고치지 않음, 표시 전용) | HANDOFF.cysr-1116-borrow23-1119.md:149-153@33a72a906 |
| b23 | 알려진 한계 §9-1: 전경 그룹 모를 때(Windows) | HANDOFF.cysr-1116-borrow23-1119.md:149-153@33a72a906 |
| b23 | 알려진 한계 §9-1: 전경 그룹 묶음 경계 | HANDOFF.cysr-1116-borrow23-1119.md:149-153@33a72a906 |
| b23 | 알려진 한계 §9-1: 환경값 위조 차단 범위(가짜 `cys`/소켓은 여전히 가능) | HANDOFF.cysr-1116-borrow23-1119.md:149-153@33a72a906 |
| b23 | 알려진 한계 §9-1: 옛 cys(1.1.15 설치본 — `daemon boot-fleet` 없음) + 새 팩 = python 은 full 로 감 | HANDOFF.cysr-1116-borrow23-1119.md:149-153@33a72a906 |
| debt-d | §4(첫 좌석)-1 §3 결과 판독 → (§3-1 에서 처리됨) | HANDOFF.cysr-1116-debt-d-1119.md:85-93@e5c0d229f |
| debt-d | §4-2 뮤턴트 J1116-V9-NO-MARKER · V21-NO-PENDING · V25-KEEP · V4-OFF · F3-OFF + S4-4 · B5 · B7 | HANDOFF.cysr-1116-debt-d-1119.md:85-93@e5c0d229f |
| debt-d | §4-3 B2 고침(처리됨 60bc82c6a) · V2-2 · V2-3(처리됨 31e4d290c) · V2-4 시험 · (B1 = 📌) | HANDOFF.cysr-1116-debt-d-1119.md:85-93@e5c0d229f |
| debt-d | §4-4 전체 게이트 → (§7-3/§9-2 에서 처리됨) | HANDOFF.cysr-1116-debt-d-1119.md:85-93@e5c0d229f |
| debt-d | §4-5 codex 1R → (처리됨 → REVISE → 고침) | HANDOFF.cysr-1116-debt-d-1119.md:85-93@e5c0d229f |
| debt-d | §4-6 설치기 맥 동형 시험 = 함수 단위만 · 설치기 전체 묶음 안 돌림 | HANDOFF.cysr-1116-debt-d-1119.md:85-93@e5c0d229f |
| debt-d | §6 📌1 LSMinimumSystemVersion 10.13 → 11.0(진입점 minos) 여부 = 오너 결정(x64 판 minos 실측 먼저) | HANDOFF.cysr-1116-debt-d-1119.md:103-110@e5c0d229f |
| debt-d | §6 📌2 맥 sudo 실행 설치기·CLI → root 데몬 가능(launchd kickstart gui/0 실패 → 형제 기동) — 정정 지시가 권한 낮추기를 철회해 넣지 않음 | HANDOFF.cysr-1116-debt-d-1119.md:103-110@e5c0d229f |
| debt-d | §6 📌3 부서 데몬(cys-dept 파이썬)이 관리자 설치기 아래서 뜨면 같은 High 상속 — 작업 경유 아님 | HANDOFF.cysr-1116-debt-d-1119.md:103-110@e5c0d229f |
| debt-d | §6 📌4 작업 스케줄러 Highest + 다른 cysd 경로(판 이동) = daemon install 이 Highest 로 재등록 시도 → 일반 창이면 실패(rc 22) | HANDOFF.cysr-1116-debt-d-1119.md:103-110@e5c0d229f |
| debt-d | §6 📌5 B6: claude 도구 허락 창이 늘 가로줄 아래인지 실화면 실측 | HANDOFF.cysr-1116-debt-d-1119.md:103-110@e5c0d229f |
| debt-d | §6 📌6 poison 원인 확인 = 윈 phoenix 로그의 「기동 실패」 줄 원문 | HANDOFF.cysr-1116-debt-d-1119.md:103-110@e5c0d229f |
| debt-d | §1 표 📌 V10 LSMinimumSystemVersion | HANDOFF.cysr-1116-debt-d-1119.md:21@e5c0d229f |
| debt-d | §1 표 📌 V2-2 nofollow → (뒤에 처리됨) | HANDOFF.cysr-1116-debt-d-1119.md:33@e5c0d229f |
| debt-d | §1 표 📌 V2-3 → (뒤에 처리됨) | HANDOFF.cysr-1116-debt-d-1119.md:34@e5c0d229f |
| debt-d | §1 표 V2-4 「고칠 것 없음 · 시험 0 = 남음」 | HANDOFF.cysr-1116-debt-d-1119.md:35@e5c0d229f |
| debt-d | §1 표 B1 census → proc-macro2 「안 함(남음) … 자체 codex 라운드 필요」 | HANDOFF.cysr-1116-debt-d-1119.md:41@e5c0d229f |
| debt-d | §1 표 📌 poison × Login expired | HANDOFF.cysr-1116-debt-d-1119.md:44@e5c0d229f |
| debt-d | §1 표 미등재 팩 시험 = 「등재 = ci-branch·release·pack-release 3레인 5루프 + lane-parity-rehearsal UNREGISTERED_OK 지우기(debt-u 좌석 ci-branch 정렬과 충돌 지점)」 | HANDOFF.cysr-1116-debt-d-1119.md:43@e5c0d229f |
| debt-d | 안 고침: V5 F2(나) · minor ②(맞바꿈) | HANDOFF.cysr-1116-debt-d-1119.md:39-40@e5c0d229f |
| debt-d | 안 고침: V5 minor ①(회귀 위험) | HANDOFF.cysr-1116-debt-d-1119.md:39-40@e5c0d229f |
| debt-d | §7-4-1 「판정 대기 5」 가르기 → (§8 에서 처리됨) | HANDOFF.cysr-1116-debt-d-1119.md:158-166@e5c0d229f |
| debt-d | §7-4-2 codex 2R = master 대기열 | HANDOFF.cysr-1116-debt-d-1119.md:158-166@e5c0d229f |
| debt-d | §7-4-3 B1 · 미등재 팩 시험 등재 = 손대지 않음 | HANDOFF.cysr-1116-debt-d-1119.md:158-166@e5c0d229f |
| debt-d | §7-4-4 설치기 가지 무접촉 | HANDOFF.cysr-1116-debt-d-1119.md:158-166@e5c0d229f |
| debt-d | §7-5 📌1 추가2 「작업 기동 실패 → 형제 직접 기동(Medium 데몬)」 유지 vs 거부 = 오너 결정 | HANDOFF.cysr-1116-debt-d-1119.md:158-166@e5c0d229f |
| debt-d | §7-5 📌2 H-CLT 격리 → (e1d75b0bd 로 고침) | HANDOFF.cysr-1116-debt-d-1119.md:158-166@e5c0d229f |
| debt-d | §7-5 📌3 S4-4 정규화 minor(명령 안 공백·│·❯ 차이) → §8 ④ 「📌3 정규화 = 1.1.17 기록」 | HANDOFF.cysr-1116-debt-d-1119.md:158-166, :174@e5c0d229f |
| debt-d | §7-5 📌4 runner_run_level 엄격 Err → §8 ④ 「📌4 엄격 Err 수용」 | HANDOFF.cysr-1116-debt-d-1119.md:158-166, :174@e5c0d229f |
| debt-d | §8-2 codex 2R 범위(대기열): 1R 고침 3(d94094a9c · 667506fac · 0461f82aa) + 31e4d290c(V2-2·3) + 60bc82c6a(B2) + e1d75b0bd(H-CLT 격리) · 질문지 = scratchpad `codex-r2-prompt.md`(H-CLT 1줄 덧붙일 것) · 사본 폴더는 HEAD 로 다시 떠야 함 · §9-4 ⑤ 덧붙일 것: c30a6e097(②) · 4d6495204(⑤) · habitat 07ec7ca(⑤) | HANDOFF.cysr-1116-debt-d-1119.md:182-183, :221@e5c0d229f |
| debt-d | codex 3R 실시(BLOCK) → 31ae4b724 에서 처분 | HANDOFF.cysr-1116-debt-d-1119.md:223-228@e5c0d229f |
| debt-d | §9-3 윈 실기(master) ⓐ 작업 /Run 실패 대역(`schtasks /Change /TN cysd /DISABLE`) → `cys ping` = 재시도 3회 로그 → 형제 기동 → `%USERPROFILE%\.cys\state\daemon-integrity-fallback.json` · `cys doctor` daemon-integrity 경고 1줄 | HANDOFF.cysr-1116-debt-d-1119.md:211@e5c0d229f |
| debt-d | §9-3 윈 실기 ⓑ 작업 다시 켬 → `cys rotate`(또는 앱 [재시작]) → 작업 경유 · 표식 삭제 · doctor OK | HANDOFF.cysr-1116-debt-d-1119.md:211@e5c0d229f |
| debt-d | §9-3 윈 실기 ⓒ NSIS 설치 로그에 `[daemon prime] 미리 데우기: …` 1줄 | HANDOFF.cysr-1116-debt-d-1119.md:211@e5c0d229f |
| debt-d | §9-4 📌1 설치기 가지 `TICKET=` 공개 용어 적중(bootstrap.sh 243 · 4094 · bootstrap.ps1) — 「발행 전 문구 정리 필요」 | HANDOFF.cysr-1116-debt-d-1119.md:216-221@e5c0d229f |
| debt-d | §9-4 📌2 ② 실패 갈래 첫 응답 대기 최대 약 18초(8+4+4 + 실행 실패 쉼 1×2) → 형제 4초(종전 8초) | HANDOFF.cysr-1116-debt-d-1119.md:216-221@e5c0d229f |
| debt-d | §9-4 📌3 우리 코드 밖 작업 경유 데몬 = 표식 파일 남음(doctor pid 대조로 무시) | HANDOFF.cysr-1116-debt-d-1119.md:216-221@e5c0d229f |
| debt-d | §9-4 📌4 앱 갈래 작업 데몬 「받지만 답 없음」 = 형제 안 띄움 | HANDOFF.cysr-1116-debt-d-1119.md:216-221@e5c0d229f |
| debt-d | §9-4 📌5 codex 2R 대기열 덧붙임 | HANDOFF.cysr-1116-debt-d-1119.md:216-221@e5c0d229f |
| debt-d | §7-2 안 고침 ⓐ 추가2 「작업 기동 실패 → 형제 직접 기동(Medium)」(📌 오너) | HANDOFF.cysr-1116-debt-d-1119.md:131@e5c0d229f |
| debt-d | §7-2 안 고침 ⓑ S4-4 minor 정규화 = 기록 | HANDOFF.cysr-1116-debt-d-1119.md:131@e5c0d229f |
| debt-d | TODO 미체크 `[ ] B1` | WORKER_TODO.cysr-1116-debt-d-1119.md:15-16@e5c0d229f |
| debt-d | TODO 미체크 `[ ] B2` — 실제로는 60bc82c6a 로 처리됨(TODO 낡음) | WORKER_TODO.cysr-1116-debt-d-1119.md:15-16@e5c0d229f |
| debt-d | TODO 미체크 `[ ] 미등재 팩 시험 44개 등재 판단` | WORKER_TODO.cysr-1116-debt-d-1119.md:24@e5c0d229f |
| debt-d | TODO 마감 미체크 `[ ] 시험 기준선 대비` · `[ ] 뮤턴트` · `[ ] HANDOFF·【확인요청】`(첫 좌석 뒤로 TODO 갱신 안 됨 · 후임 3 블록은 전부 [x]) | WORKER_TODO.cysr-1116-debt-d-1119.md:31-34, :38-41@e5c0d229f |
| seatkeep | 최종 남은 것 ① codex q/09(16:37 · T6a+T6b · e7253d6c9 까지 포함될지 master 확인) 판정 처분 1회 | HANDOFF.cysr-1116-seatkeep-1119.md:392-401@9b591371b |
| seatkeep | 최종 남은 것 ② 측정 대기 — 실 업데이터 S6 점검·되감기 종료 VM · drain 분리 실물 · A13 릴리스 빌드 · 자동 복원 재실행 실물 | HANDOFF.cysr-1116-seatkeep-1119.md:392-401@9b591371b |
| seatkeep | codex T4 5R = master 대기열(범위 `e20850fae..ddae58a5f -- src/ scripts/seatkeep-adopt-e2e.py`) | HANDOFF.cysr-1116-seatkeep-1119.md:61, :176@9b591371b |
| seatkeep | codex 1R T5 + 독립 검증(범위 `63c332520..d2ca1de03`) → 독립 검증 「T4 BLOCK · T5 ACCEPT · 노브 끔 ACCEPT」 → 뒤에 B1/B2/빈칸/M1/M2/m1 고침 | HANDOFF.cysr-1116-seatkeep-1119.md:220, :224@9b591371b |
| seatkeep | T6b codex: 「업데이터 축 고위험 → 독립 검증 좌석 + codex 1R 권고 · 범위 `f138da04e^..e3afb8a67`」 → skt6 REVISE 처분 | HANDOFF.cysr-1116-seatkeep-1119.md:371, :374-390@9b591371b |
| seatkeep | 다음 단계(미실행): T7 윈도우 → D1 꼬리 ≤1KiB 유실 · 슬레이브 보유 탐침 → 노브 기본 켬 판단(T1·T5·D1 닫힌 뒤 숫자) · 📌 전사 SIGKILL 1초 유실(이월 ④) · A13 릴리스 빌드 숫자 | HANDOFF.cysr-1116-seatkeep-1119.md:372, :108@9b591371b |
| seatkeep | 📌 SIGKILL 시 전사 최대 1초 유실 — 고치는 길 = PROCESSED 를 「전사 COMMIT 뒤」로 늦추기 또는 COMMIT 주기 단축 · 범위 밖 | HANDOFF.cysr-1116-seatkeep-1119.md:134@9b591371b |
| seatkeep | 📌 m3 거절 문구 「동세대 발급분」 = 기록(원작자 문구 · 안 바꿈) | HANDOFF.cysr-1116-seatkeep-1119.md:233@9b591371b · docs/seatkeep/T5-DESIGN.md:98@9b591371b |
| seatkeep | 검증 좌석 덧붙임 📌 ⓐ 업데이터가 「옛 번들 지우기 → 새로 복사」 사이에 cysd 를 띄우면 `proc_pidpath` 실패 → 미결 | HANDOFF.cysr-1116-seatkeep-1119.md:246@9b591371b |
| seatkeep | 검증 좌석 덧붙임 📌 ⓑ KERN_PROCARGS2 로 같은 사용자가 토큰 env 를 읽을 수 있음(T3 부터 · 경계 안) | HANDOFF.cysr-1116-seatkeep-1119.md:246@9b591371b |
| seatkeep | 검증 좌석 덧붙임 📌 ⓒ 입양 기록 둘이 같은 비-worker 역할이면 latest-wins | HANDOFF.cysr-1116-seatkeep-1119.md:246@9b591371b |
| seatkeep | 📌 holder 상한 `CYS_SEATKEEP_MAX_HOLDERS` 기본 64 | docs/seatkeep/T6-DESIGN.md:104@9b591371b · HANDOFF.cysr-1116-seatkeep-1119.md:298, :330@9b591371b |
| seatkeep | 📌 서명 기반 대조 = 경계 밖 위협 모델이 생기면 B | HANDOFF.cysr-1116-seatkeep-1119.md:344@9b591371b |
| seatkeep | 📌 옛 번들 정리를 넣으면 「산 seatkeep 이 그 번들을 쓰는 동안 지우지 않기」 같이 필요 | HANDOFF.cysr-1116-seatkeep-1119.md:345@9b591371b |
| seatkeep | 📌【질문】 `sibling_daemon_path` 링크 미해석 → e7253d6c9 로 해소 | HANDOFF.cysr-1116-seatkeep-1119.md:379, :398@9b591371b |
| seatkeep | skt6 기록(안 고침) 경미 5 되감기 종료 「새 판 바이너리가 되감기를 이끌 때만 돈다 · 1.1.16→1.1.15 되감기(1.1.15 러너)는 덮지 않음 · A9ⓑ 는 「부분 해결」」 | HANDOFF.cysr-1116-seatkeep-1119.md:381-387@9b591371b |
| seatkeep | skt6 기록(안 고침) 경미 7 `.cysr.app.new-<seq>` 한계 | HANDOFF.cysr-1116-seatkeep-1119.md:381-387@9b591371b |
| seatkeep | skt6 기록(안 고침) 경미 10 drain 면제 = 교체 전 목록 | HANDOFF.cysr-1116-seatkeep-1119.md:381-387@9b591371b |
| seatkeep | skt6 기록(안 고침) 기록 11 holder 상한 느슨 | HANDOFF.cysr-1116-seatkeep-1119.md:381-387@9b591371b |
| seatkeep | skt6 기록(안 고침) ⓐ = 형제 안 아무 cys-seatkeep | HANDOFF.cysr-1116-seatkeep-1119.md:381-387@9b591371b |
| seatkeep | T6 설계 §4/§5 안 함: T1(대화 임대) · 강제 진행 rotate · 윈도우(T7) · 노브 기본 켬 판단 | docs/seatkeep/T6-DESIGN.md:93-94@9b591371b |
| seatkeep | T4 설계 §4 안 함: A7 관문 전부(`screen_exact`) · A14 · A15 동시 복원 경합(T1 몫) | docs/seatkeep/T4-DESIGN.md:35-41@9b591371b |
| seatkeep | 측정 대기: 실 업데이터 S7→S9→S10 · 되감기(RB_PREPARED → start_old) = VM 실기 · 자동 복원 재실행 실물(phoenix) 미측정 · A13 = 디버그 빌드 숫자 | HANDOFF.cysr-1116-seatkeep-1119.md:357, :289, :331@9b591371b |
| skt1 | §9 남는 한계 1 등록 실패 창(§12/§13 고침으로 대체) | HANDOFF.cysr-1116-skt1-1119.md:131-138@b03d1cd70 |
| skt1 | §9 남는 한계 2 계통 판독 불가(None) = 옮김(§12/§13 고침으로 대체) | HANDOFF.cysr-1116-skt1-1119.md:131-138@b03d1cd70 |
| skt1 | §9 남는 한계 3 비-claude = 데몬 관측 기준(§12/§13 고침으로 대체) | HANDOFF.cysr-1116-skt1-1119.md:131-138@b03d1cd70 |
| skt1 | §9 남는 한계 4 훅 없는 claude 좌석 | HANDOFF.cysr-1116-skt1-1119.md:131-138@b03d1cd70 |
| skt1 | §9 남는 한계 5 등록 직후·수집기 핀 전 창 실 e2e 없음 | HANDOFF.cysr-1116-skt1-1119.md:131-138@b03d1cd70 |
| skt1 | §9 남는 한계 6 헬퍼(`claude -p`) 등록 실 e2e 없음 | HANDOFF.cysr-1116-skt1-1119.md:131-138@b03d1cd70 |
| skt1 | §10 📌1 노브 기본값 → master#e08a16c0 ① = 켬 유지(`CYS_SESSION_LEASE` 없으면 켬) · ③ rc 93 공유 = 유지 | HANDOFF.cysr-1116-skt1-1119.md:140-145@b03d1cd70 |
| skt1 | §10 📌2 session_lease_e2e CI 레인 없음 → master#e08a16c0 ② = 등재함(ci-branch 맥 레인 · 스레드 2 · 시한 20분 · 로컬 실측 422s · 빌드 포함 472s) | HANDOFF.cysr-1116-skt1-1119.md:140-145@b03d1cd70 |
| skt1 | §10 📌3 rc 93 공유: 조각 1 `EXIT_RESUME_HELD` 와 임대 `EXIT_SESSION_LIVENESS_UNKNOWN` 이 같은 값 — 따로 가르려면 새 rc(94) 배정 = 계약 변경 | HANDOFF.cysr-1116-skt1-1119.md:140-145@b03d1cd70 |
| skt1 | §10 📌4 기존 e2e 의 「설치본 cys 로 등록」 사실(§7)은 원 T1 의 r5b RV 판정 근거를 약하게 만듦 — 이번 고침 뒤 RV 는 시험 cys 로 초록 | HANDOFF.cysr-1116-skt1-1119.md:140-145@b03d1cd70 |
| skt1 | §12-5 한계 1 훅의 `cys` 가 아예 안 돈 좌석 안 대화 전환 = 옛 결속 남음(1.1.15 와 같음) | HANDOFF.cysr-1116-skt1-1119.md:279-286@b03d1cd70 |
| skt1 | §12-5 한계 2 등록이 확정 뒤 닿는 진짜 동시 | HANDOFF.cysr-1116-skt1-1119.md:279-286@b03d1cd70 |
| skt1 | §12-5 한계 3 거짓 막힘(93): 계통 argv 못 읽는 기계 · 윈 codex 좌석(lsof 없음) · 훅 없는 claude · 부하 큰 기계 판독 시한 | HANDOFF.cysr-1116-skt1-1119.md:279-286@b03d1cd70 |
| skt1 | §12-5 한계 4 옛 판 cys(launch_sent 칸을 모름)가 같은 임대 폴더를 쓰면 다른 좌석 등록이 이어받을 수 있음(1.1.16 안에서는 모든 cys 가 같은 판) | HANDOFF.cysr-1116-skt1-1119.md:279-286@b03d1cd70 |
| skt1 | §12-5 한계 5 Tauri 「복원됨」 증거는 작성자가 좌석 뿌리 자손인지 안 봄 | HANDOFF.cysr-1116-skt1-1119.md:279-286@b03d1cd70 |
| skt1 | §12-5 한계 6 데몬: claude 좌석의 좌석 밖 등록(caller 없음)은 종전대로 핀을 움직임 | HANDOFF.cysr-1116-skt1-1119.md:279-286@b03d1cd70 |
| skt1 | §12-7 📌1 기본 켬 유지 쪽(확신도 중상) · 단점 = 부하 큰 기계 판독 시한 93 증가 가능 → 「정상 복원 ≈70회」 같은 조건 재측 권고 | HANDOFF.cysr-1116-skt1-1119.md:292-296@b03d1cd70 |
| skt1 | §12-7 📌2 현장 끔 스위치 = 여전히 환경변수뿐(USER-MANUAL 1줄 추가) — 파일 스위치(앱·phoenix 일괄)는 기능 추가라 📌 | HANDOFF.cysr-1116-skt1-1119.md:292-296@b03d1cd70 |
| skt1 | §12-7 📌3 codex 2R 질문 후보 → (§13 에서 처리) | HANDOFF.cysr-1116-skt1-1119.md:292-296@b03d1cd70 |
| skt1 | §13-3 한계 1 같은 사용자 위조(보안 경계 밖 · 고치지 않음) | HANDOFF.cysr-1116-skt1-1119.md:333-341@b03d1cd70 |
| skt1 | §13-3 한계 2 lsof 오인(최상위 codex 가 판독 순간 T 만 열면 「T」) | HANDOFF.cysr-1116-skt1-1119.md:333-341@b03d1cd70 |
| skt1 | §13-3 한계 3 Return 뒤 틈(수 ms) | HANDOFF.cysr-1116-skt1-1119.md:333-341@b03d1cd70 |
| skt1 | §13-3 한계 4 확인 실패 뒤 붙인 글: Return 0 으로 멈춘 좌석에 기동 글이 붙은 채 남음 — 빈 좌석 닫기(`only_if_empty`)가 거절하면 그 좌석이 남음(누가 Return 을 치면 실행 · 안내 줄 출력 · 측정 없음) | HANDOFF.cysr-1116-skt1-1119.md:333-341@b03d1cd70 |
| skt1 | §13-3 한계 5 Tauri 판정 뒤 틈 | HANDOFF.cysr-1116-skt1-1119.md:333-341@b03d1cd70 |
| skt1 | §13-3 한계 6 거짓 93 이 늘어난 곳(감수 · master ①): 계통 argv 를 못 읽는 기계의 모든 대화 전환 · 조상 사슬이 끊긴 등록 … | HANDOFF.cysr-1116-skt1-1119.md:333-341@b03d1cd70 |
| skt1 | §13-3 한계 7 §12-5 의 1·4·6 그대로 | HANDOFF.cysr-1116-skt1-1119.md:333-341@b03d1cd70 |
| skt1 | §13-4 lease 켬이 1.1.15 보다 작성자 둘을 늘리는 경로는 찾지 못함(확신도 중상) · lsof 쪽은 한계 1·2 가 남음(거짓 통과 가능 · 같은 사용자 위조 또는 관측 시점) | HANDOFF.cysr-1116-skt1-1119.md:345@b03d1cd70 |
| skt1 | §3 손 안 댄 것: ⓓ `run_sidecar_restore_judged` 안쪽 15초 대기 회차 확인(피해 미확인 · 그대로) · `worker`/`worker-N` 불일치 통과 | HANDOFF.cysr-1116-skt1-1119.md:56@b03d1cd70 |
| skt1 | (원 가지 이월) ⚠닿는 줄 1 — `launch_idem_key` 가 잇는 기동의 멱등 키에 `-s<대화>` 를 노브와 무관하게 붙임 · 끔에서 1.1.14 와 똑같게 하려면 이 접미를 `sl::enabled()` 안에 넣어야 함(1줄 · 이 좌석은 안 고침 = master 판단) | docs/HANDOFF-seatkeep-t1.md:44@b03d1cd70 |
| skt1 | (원 가지 이월) ⚠앱(Tauri·UI)은 노브를 아예 읽지 않음 → `CYS_SESSION_LEASE=off` 에서도 T1 의 앱 변경(복원 알림)이 전부 돎 | docs/HANDOFF-seatkeep-t1.md:45@b03d1cd70 |
| skt1 | (원 가지 이월) 알려진 한계 #7(1.1.16 후보): 앱을 종료했다 다시 열면 pending 감시와 30분 안내가 사라짐 · 릴리스 노트 후보 | docs/DESIGN-seatkeep-t1-r4.md:80-87@b03d1cd70 · docs/HANDOFF-seatkeep-t1.md:180, :204@b03d1cd70 |
| skt1 | (원 가지 이월) 데몬 티켓 후보: cysd 자동 복원 자식 `child.wait()` 무제한(`src/bin/cysd/main.rs` `loop_auto_restore` 계열) | docs/HANDOFF-seatkeep-t1.md:236@b03d1cd70 · docs/DESIGN-seatkeep-t1-r4.md:29, :91@b03d1cd70 |
| skt1 | (원 가지 이월) 다음 티켓 후보 C(업데이트 절차·데몬 쪽 관문 — 옛 사이드카와 새 판 복원 겹침, 실 앱 업데이트로 빈도 1회 측정 먼저) · F1 「같은 폴더 claude → 93」 차단 | docs/HANDOFF-seatkeep-t1.md:354-357@b03d1cd70 |
| skt1 | (원 가지 이월) T1 밖 P1 · P2 · Q1 · Q2 | docs/HANDOFF-seatkeep-t1.md:399-403@b03d1cd70 |
| skt1 | USER-MANUAL.md +6(기준 516줄 근처): 복원 전 같은 대화의 다른 터미널 세션을 닫으라는 경고 + `CYS_SESSION_LEASE=off cys restore` 끔 안내(「이 스위치는 그 명령을 실행한 환경에만 걸리고 앱의 자동 복원에는 걸리지 않습니다」) | USER-MANUAL.md(기준 :516)@b03d1cd70 — lane-facts 에 머리 줄 번호 없음 |
| s79 | 📌1 결과 미리보기(쪽 그림 · PRD S5 「미리보기」) — 안 넣음(파일 읽기 길이 새로 필요) | HANDOFF.cysr-1116-s79-1119.md:208@f51261ee0 |
| s79 | 📌2 대화 화면을 안 켠 실행 동안 끝난 스킬 결과는 못 받음(사건 구독이 대화 화면 수명에 묶임 = S4-3·I3 와 같은 뿌리) — s2 의 I3·S4-3 단일 수집으로 닫을 수 있음(배선 시) | HANDOFF.cysr-1116-s79-1119.md:209@f51261ee0 |
| s79 | 📌3 맨글 띄어쓰기 경로는 두 후보(이은 것 + 끊긴 것)가 둘 다 실재하면 카드 둘 | HANDOFF.cysr-1116-s79-1119.md:210@f51261ee0 |
| s79 | 📌4 `result_open` 윈도 실기 미확인(`\\?\` 머리 벗기기 · x64 실행 금지라 정적으로만) | HANDOFF.cysr-1116-s79-1119.md:211@f51261ee0 |
| s79 | 📌5 CI 새 스텝 실측 0(CI 금지) — 첫 실행에서 headless shell 받기 시간 · `chromium.launch()` 기본 경로 확인 필요 | HANDOFF.cysr-1116-s79-1119.md:212@f51261ee0 |
| s79 | 📌6 s79_gate · chat_gate · confirm_gate 는 여전히 CI 미배선(이번 배선 = cc_popover_z 하나만 지시) | HANDOFF.cysr-1116-s79-1119.md:213@f51261ee0 |
| s79 | 📌7 codex 2R(고친 뒤) 안 함 → 뒤에 2R/3R/4R 실시 · 4R = 「마지막 회차 · 5R 없음」 | HANDOFF.cysr-1116-s79-1119.md:214, :112, :140, :171@f51261ee0 |
| s79 | 알려진 한계: TOCTOU | HANDOFF.cysr-1116-s79-1119.md:135@f51261ee0 |
| s79 | 알려진 한계: 맥 홈 아래 네트워크 마운트 판별 안 함 | HANDOFF.cysr-1116-s79-1119.md:136@f51261ee0 |
| s79 | 알려진 한계: 4낱말 넘는 띄어쓰기 맨글 경로 = 카드 0 | HANDOFF.cysr-1116-s79-1119.md:137@f51261ee0 |
| s79 | 알려진 한계: 허용 목록 파일 내용(스크립트·매크로)은 처리기 몫 | HANDOFF.cysr-1116-s79-1119.md:138@f51261ee0 |
| s79 | 알려진 한계: HTML·SVG 능동 내용 — 안내 문구 안 넣음 | HANDOFF.cysr-1116-s79-1119.md:168@f51261ee0 |
| s79 | 알려진 한계: `open -a Finder` 실창 미탐침 | HANDOFF.cysr-1116-s79-1119.md:169@f51261ee0 |
| s79 | 알려진 한계: 같은 사용자 경계 | HANDOFF.cysr-1116-s79-1119.md:194@f51261ee0 |
| s2 | 📌1 (독립 검증 F3) 대화 화면만 쓰는 동안 빈 탭 자리표(맨 셸 1개)가 데몬에 남음(런타임 없음 = 화면 줄 수 모름 = 닫지 않음 규칙) — 데몬 쪽 출력 흔적(`line_count`)으로 판정할지 설계 판단 | HANDOFF.cysr-1116-s2-1119.md:249@06711fbc9 |
| s2 | 📌2 (codex 1R M4 나머지) 본부 slug 를 main.ts 가 기동 때 못 받으면 대화 화면 두 처리기가 사건을 버림 — main.ts 재조회 길(eventSock 해석 실패 때)에 기댐 · 확실히 하려면 viewsIngest 에서 slug null 이면 1회 재조회(작업 화면 invoke 가 늘어 tickrec OFF 대조가 바뀜 — 판단 필요) | HANDOFF.cysr-1116-s2-1119.md:251@06711fbc9 |
| s2 | 📌3 (codex 1R m6) 입양 후보 선계산의 한 틱 지연 — 엄격 동치가 필요하면 await 뒤마다 다시 판정 | HANDOFF.cysr-1116-s2-1119.md:252@06711fbc9 |
| s2 | 📌4 (codex 1R M2) F20 ① → 「2R 에서 고침(§3-3 2R-M2)」 — 닫힘 | HANDOFF.cysr-1116-s2-1119.md:254@06711fbc9 |
| s2 | 📌5 설계 §5-3 persist.ts(판 번호 · 단일 작성자 모듈) — 조각 8 과 함께 | HANDOFF.cysr-1116-s2-1119.md:255, :235@06711fbc9 |
| s2 | 📌6 숨은 화면에서 짠 좌열 몫(§4-6) — 작업 화면 첫 진입 때 한 번 다시 맞출지(사용자 배치 존중과 충돌 · 설계 판단) | HANDOFF.cysr-1116-s2-1119.md:256@06711fbc9 |
| s2 | 📌7 실물 측정 대기: 좌석 12개 대화 → 작업 첫 진입 시간(맥·윈) · 웹뷰 메모리(대화 1시간 vs 작업 1시간) · 웹뷰 멈춤 주입 → 데몬 자가치유(§2-2 게이트⑤) · Tauri 박동 `views_tick_beat`(§2-2 장치 — 이 조각에서 안 만듦) | HANDOFF.cysr-1116-s2-1119.md:257@06711fbc9 |
| s2 | 📌8 (4R 회차) 접힘(wrapped) 무시 = 고치지 않음(master ⑥) · 놓침 복구는 같은 커서로 다시 그리기라 사람이 스크롤해 읽던 위치가 바닥으로 돌아감 · 놓침 복구 상한 3 = 연속 홍수 좌석은 기록 없이 붙고 안내 · ED3 은 §3-7 ③ 대로 「지움 = 잘림 아님」(master 지시와 다름 · 확인 요청) | HANDOFF.cysr-1116-s2-1119.md:259@06711fbc9 |
| s2 | 📌9-① (3R 한계) 파서 세대 하위 13비트만(8,192 배수) | HANDOFF.cysr-1116-s2-1119.md:260@06711fbc9 |
| s2 | 📌9-② (3R 한계) ED 3 미처리 → 4R 에서 고침 | HANDOFF.cysr-1116-s2-1119.md:260@06711fbc9 |
| s2 | 📌9-③ (3R 한계) 밀려난 행 `\r\n` 이어 씀 — 폭 바꾸면 다시 접히지 않음 | HANDOFF.cysr-1116-s2-1119.md:260@06711fbc9 |
| s2 | 📌9-④ (3R 한계) 다시 불러오기 = abort 된 옛 스트림 사건이 비운 화면 맨 앞에 끼일 수 있음(드묾) | HANDOFF.cysr-1116-s2-1119.md:260@06711fbc9 |
| s2 | 📌9-⑤ (3R 한계) 진입당 3회 다 쓰면 그 진입 동안 「(없음)」 칸 | HANDOFF.cysr-1116-s2-1119.md:260@06711fbc9 |
| s2 | 📌9-⑥ (3R 한계) 「사건 기록」 = UI 안 고리(`seatHistoryEvents` · 64) + console.warn 뿐 | HANDOFF.cysr-1116-s2-1119.md:260@06711fbc9 |
| s2 | 📌9-⑦ (3R 한계) 윈 ConPTY = 같은 reader·파서(정적) · 실기 측정 대기 | HANDOFF.cysr-1116-s2-1119.md:260@06711fbc9 |
| s2 | §4 master 확인 후보 1 「작업 화면이 안 보임」 판정 = 어댑터 mount/unmount | HANDOFF.cysr-1116-s2-1119.md:229-236@06711fbc9 |
| s2 | §4 master 확인 후보 2 작업 화면에서는 보이지 않는 탭 좌석도 즉시 런타임(미룸은 대화 화면에서만) | HANDOFF.cysr-1116-s2-1119.md:229-236@06711fbc9 |
| s2 | §4 master 확인 후보 3 판정 순수 함수 = 소켓 단위 | HANDOFF.cysr-1116-s2-1119.md:229-236@06711fbc9 |
| s2 | §4 master 확인 후보 4 decideSockPre 사본 갱신 걷음(M5·M7 동치) | HANDOFF.cysr-1116-s2-1119.md:229-236@06711fbc9 |
| s2 | §4 master 확인 후보 5 persist.ts 안 만듦 → 📌 | HANDOFF.cysr-1116-s2-1119.md:229-236@06711fbc9 |
| s2 | §4 master 확인 후보 6 숨은 화면 좌열 몫 기본값 25% → 📌 관찰 | HANDOFF.cysr-1116-s2-1119.md:229-236@06711fbc9 |
| s2 | codex 1R m6 = 기록(고치지 않음) | HANDOFF.cysr-1116-s2-1119.md:113@06711fbc9 |
| s2 | 4R ⑥ wrapped = 고치지 않음(master) | HANDOFF.cysr-1116-s2-1119.md:212@06711fbc9 |
| s5 | §8-1 P1 원자 조건부 닫기 → §11 에서 승인·처리됨 | HANDOFF.cysr-1116-s5-1119.md:134-143, :157, :186-196@305f08930 |
| s5 | §8-2 설계 개정 §6-2 성공 판정 — 코드는 됨 · 설계 문서 문구는 §10-2 · 「설계 문서 고침 = master」 → 아직 열림: master 가 P2-DESIGN 고쳐야 함 | HANDOFF.cysr-1116-s5-1119.md:165-170, :158@305f08930 |
| s5 | §8-3 launch-agent 멱등 재사용이 기동 줄을 clear_first 없이 침 → §11-3 에서 처리(rc 92) | HANDOFF.cysr-1116-s5-1119.md:134-143@305f08930 |
| s5 | §8-4 깨움 말의 「차례 기다림」 줄과 깨우기 띠가 둘 다 보임 — 걷기(조각 10)에서 정리 후보 → §10-1 #4 「1.1.17 기록(조각 10 걷기 몫)」 · 열림(미룸) | HANDOFF.cysr-1116-s5-1119.md:160@305f08930 |
| s5 | §8-5 마스터 띠와 확인 대기 띠가 따로 보임 — 설계 「한 번에 하나」 문장 개정 후보 → 1.1.17 기록 · 열림(미룸) | HANDOFF.cysr-1116-s5-1119.md:160@305f08930 |
| s5 | §8-6 실물 앱 팀 부트 체인(spawn_orchestra_boot) 뒤 CSO·워커 수 · 새 프로필 첫 기동 관문 · 윈 실기 = master 실기(「할 일 없음」) · 열림: master 실기 | HANDOFF.cysr-1116-s5-1119.md:141, :161@305f08930 |
| s5 | §8-7 codex 3R → §14 에서 처리(BLOCK → 5b8abd7c6) · 5b8abd7c6 뒤 codex 4R 필요 여부는 인계서에 없음(열림/미기재) | HANDOFF.cysr-1116-s5-1119.md:134-143@305f08930 |
| s5 | §8-8 `test_phoenix_c6_reap` 기준판 대조 → 처리됨: 기준선과 같음 | HANDOFF.cysr-1116-s5-1119.md:226-227@305f08930 |
| s5 | §11-8-1 기존 결함(기준판 재현): 에이전트 죽음 → 60초 뒤 멱등 재반환으로 role 을 다시 쥐지 않음(마스터 0) → §12(00bc7131d)에서 고침 · §12-0 이 화면 관련 주장 정정 | HANDOFF.cysr-1116-s5-1119.md:229-232, :242-243@305f08930 |
| s5 | §11-8-2 launch-agent 재사용 거절의 「30초 안 사람 입력」은 넣지 않음(브리프 = 초안만) — 기록된 결정 · 조치 없음 | HANDOFF.cysr-1116-s5-1119.md:229-232@305f08930 |
| s5 | §11-8-3 codex 3R = master 대기열 → §14 에서 처리 | HANDOFF.cysr-1116-s5-1119.md:229-232@305f08930 |
| s5 | §13 F1 / F2 고침(58b3fbbd8) | HANDOFF.cysr-1116-s5-1119.md:262-293@305f08930 |
| s5 | ⚠열림·master 결정: 이력 객체 개인 문자열 — 0442fe4e5·6a02f2d0a·00bc7131d·58b3fbbd8 의 `docs/ui-p2/evidence/s5/real-daemon-s5b.txt`(화면 줄 사용자@호스트 1곳) · 6a02f2d0a·00bc7131d·58b3fbbd8 의 `mut_p1_ts.py`(사용자 이름 든 절대 경로 2곳) — 머리에서는 지웠으나 이력에 남음 → 공개 미러로 가기 전 이력 정리(스쿼시·재작성) = master 결정 | HANDOFF.cysr-1116-s5-1119.md:290@305f08930 |
| s5 | F2 귀결(동작 메모): 그 사이 마스터 0(사망 60초 뒤 회수) · 화면은 꺼짐 띠 + 다시 켜기 = 초안 막힘 안내 → 사람이 글을 지우거나 보내면 다음 복원·다시 켜기가 진행 | HANDOFF.cysr-1116-s5-1119.md:274@305f08930 |
| s5 | §14 한계: 실물 phoenix 는 초안 없는 빈 좌석을 좌석 내 재연결로 살려 회수 갈래까지 가지 않음 — phoenix 가 만드는 조건부 회수 인자 꼴은 D9 로, 그 CLI 명령의 데몬 판정은 `toctou_real.py` 직접 호출로만 실물 확인 | HANDOFF.cysr-1116-s5-1119.md:305@305f08930 |
| s5 | codex 1R M7 = 「부분」 — 남은 표식이 전체 초기화 뒤 「멈춰 있어요」 띠를 보일 수 있음 · 무해 판정 | HANDOFF.cysr-1116-s5-1119.md:110@305f08930 |
| s6 | 📌 P1 실물 대화 1회(시험 프로필): 「갈래 셋」 일을 맡기면 마스터가 CORE 요지만으로 `⟪팀 제안⟫` 을 내는가 · 팀 폴더에서 띄우고 seat-group 하는가 → 「1.1.16 전 측정」 → 뒤에 측정함(⟪팀 제안⟫ = 냄 · 팀 폴더 = 함 · seat-group = 함 · ⟪팀 만드는 중⟫ = 안 냄) | HANDOFF.cysr-1116-s6-1119.md:113@94ddcd1cf · docs/1116-s6/P1-measure.md:19-25@94ddcd1cf |
| s6 | 📌 P2 6b 실물 1기(시험 프로필 데몬): 두 팀 좌석으로 몫·정지·묶음 실제 배달 → 「1.1.16 전 측정」 · 아직 열림(측정 대기) | HANDOFF.cysr-1116-s6-1119.md:114, :100@94ddcd1cf |
| s6 | 📌 P3 CEO 좌석 주입에서 「절 목차」 블록이 상한(8,800)에 밀려 빠짐 — 이 티켓 전부터(8,401자 · 브리지 1,500자 가정) → 「1.1.17 또는 별 티켓」 | HANDOFF.cysr-1116-s6-1119.md:115@94ddcd1cf |
| s6 | 📌 P4 「★」 절(§14 뒤)이 주입 목차(toc_block)에 아예 안 나옴 — 이번엔 CORE 요지로만 우회 → 「별 티켓(주입기)」 | HANDOFF.cysr-1116-s6-1119.md:116@94ddcd1cf |
| s6 | 📌 P5 ⑧ 도우미 상한은 `role:"worker"` 요청만 셈(번호 붙은 역할 `worker-3` 등 = 기존 active-limit 과 같은 한계) → 「1.1.17」 | HANDOFF.cysr-1116-s6-1119.md:117@94ddcd1cf |
| s6 | 📌 P6 대화 화면 「팀 만드는 중」 표식은 대화 화면을 연 뒤 기록만 읽음 · 연 시점보다 앞에 낸 표식은 놓침(30분 상한이라 영향 작음) → 「1.1.17」 | HANDOFF.cysr-1116-s6-1119.md:118@94ddcd1cf |
| s6 | 📌 P7 맡긴 일 카드는 누를 수 없음(시안은 버튼 · FR-L4 엿보기 = 범위 밖) → 「조각 다음」 | HANDOFF.cysr-1116-s6-1119.md:119@94ddcd1cf |
| s6 | 📌 P8 데몬 재시작 = 정지·꼬리표·보고 시각 비움(DAEMON-6b.md §4 전부) · 앱 사람 묶음 기록을 데몬이 모름 → 「기록」 (m4 로 일부 바뀜: 재시작 때 `team.pause_lost` 1회 냄) | HANDOFF.cysr-1116-s6-1119.md:120@94ddcd1cf · docs/1116-s6/DAEMON-6b.md:127@94ddcd1cf |
| s6 | 📌 P9 대화 화면 사건 구독이 이제 셋(조각 3 listen · 조각 4 listenDaemon(조각 6 메뉴바가 같이 씀)) — 통합 인계서 I3 과 같은 성격 → 「1.1.17」 | HANDOFF.cysr-1116-s6-1119.md:121@94ddcd1cf |
| s6 | §9 📌① 기존 전체 상한 `CYS_MAX_ACTIVE_WORKERS` 의 셈~삽입 경합(원작자 코드 · M4 와 같은 꼴) | HANDOFF.cysr-1116-s6-1119.md:168@94ddcd1cf · docs/1116-s6/DAEMON-6b.md:212-213@94ddcd1cf |
| s6 | §9 📌② 역할 주차 TTL 은 데몬 정지 크레딧을 안 받고 이제 팀 정지 크레딧만 받음(비대칭 · 브리프 「역할 주차 같은 처리」 그대로 따름) | HANDOFF.cysr-1116-s6-1119.md:168@94ddcd1cf · docs/1116-s6/DAEMON-6b.md:212-213@94ddcd1cf |
| s6 | 메모리 증류: 「★ 절(§14 뒤)은 주입 목차 밖 → 새 마스터에게 안 닿음 · CORE 요지로」 — 기존 메모리 pack-directive-rule-must-reach-core-summary 에 한 줄 덧붙임(이 좌석이 함) | HANDOFF.cysr-1116-s6-1119.md:123@94ddcd1cf |
| s6 | 지침 고침 제안(제안만 · 적용 안 함): `⟪팀 만드는 중: <팀 이름>⟫` 줄을 「팀(좌석 묶음)을 만들기로 한 그 답의 첫 줄(도우미를 띄우는 도구보다 먼저 글로 냄 · 만들다 막혀도 그 답에 씀 — 화면은 30분 안에 묶음이 안 생기면 카드를 내림)」로 + MASTER_CORE 요지 줄 · 「(+약 60 B · 바이트 예산 ⑦ 다시 상향 필요)」 | docs/1116-s6/P1-measure.md:31-35@94ddcd1cf · HANDOFF.cysr-1116-s6-1119.md:89@94ddcd1cf |
| s6 | B1 한계(일부러 둠): 좌석에서 떨어져 나간 워커 자식은 같은 UID 로 `operator.token` 을 읽어(`cys seat-group-pause --operator`) 팀을 멈출 수 있음 — 바깥 유출 0 · 재개로 되돌림 · 같은 사용자 경계 · 감사 = `team.paused`/`team.resumed` 사건의 `via`(`master_seat`\|`operator_token`) · `caller_pid` · `caller_surface` | HANDOFF.cysr-1116-s6-1119.md:175@94ddcd1cf |
| s6 | 남은 위험: 꼬리표·보고 시각은 메모리에만 | docs/1116-s6/DAEMON-6b.md:71@94ddcd1cf |
| s6 | 남은 위험: ⑦ 은 큐 경로에만 적용 — 직접 `cys send` 와 `send-key --queued` 는 몫·꼬리표 밖 | docs/1116-s6/DAEMON-6b.md:73@94ddcd1cf |
| s6 | 남은 위험: 「⑨ 보류 항목이 오래 남으면 `queue.starved`(600초)가 정지 팀 항목으로 울릴 수 있다」 | docs/1116-s6/DAEMON-6b.md:74@94ddcd1cf |
| s6 | 남은 위험 M1: 「writer 가 이미 쓰기로 확정한 배달 1건은 나간다」 | docs/1116-s6/DAEMON-6b.md:211@94ddcd1cf |
| s6 | 남은 위험 M4: 「같은 팀 생성은 줄을 선다 … 60초 넘게 안 끝나면 다음은 `team_worker_admission_busy`」 | docs/1116-s6/DAEMON-6b.md:212@94ddcd1cf |
| s6 | 남은 위험 m6: 「한 팀이 머리표만 붙여 보내면 그 팀은 전체 100 까지 채울 수 있다」 | docs/1116-s6/DAEMON-6b.md:136@94ddcd1cf |
| s6 | 남은 위험 i7: 「앱 seatrows 의 같은 규칙은 lead 가 따로 바꾼다」 — 낡음: ab15c7d5b 가 `seatrows.fixedRank` 를 바꿈 (전체 위험 목록 원문 = DAEMON-6b.md §4 :70-77 · §5-5 :131-137 · §6-4 :209-214 · §7-3 :249-251) | docs/1116-s6/DAEMON-6b.md:137@94ddcd1cf · HANDOFF.cysr-1116-s6-1119.md:136@94ddcd1cf |
| s6 | TODO G 「[ ] G. codex 1R — master 대기열」 미체크 — 그러나 codex 1R·2R 처분(H §9·§10)으로 대체됨 · 「codex 3R 없음」 · T6b TODO 는 전부 체크 | WORKER_TODO.cysr-1116-s6-1119.md:14@94ddcd1cf · docs/1116-s6/DAEMON-6b.md:216@94ddcd1cf · WORKER_TODO.cysr-1116-s6b-1120.md:2-11@94ddcd1cf |

---

## 표 2. 갈래가 통합 때 보라고 한 시험(부하성·기준선 붉음)

성격 칸: **부하성** = 시간 문턱·부하에 따라 붉음 / **기준선 붉음** = 기준판 dea2e1853 에서도 붉음 / **간헐** = 원인 미확정 흔들림 / 그 밖(환경성·통합 핀·추출자 추론)은 그대로 적었다.

| 갈래 | 시험 이름 | 성격 | 출처 |
|---|---|---|---|
| debt-u | run_bootstrap_health H-CLT-1 · H-CLT-2 | 기준선 붉음 | HANDOFF.cysr-1116-debt-u-1119.md:115-116@e0953c7e0 |
| debt-u | 시간 문턱 L1295(ps 1.5s) | 부하성(부하 낮을 때 초록) | HANDOFF.cysr-1116-debt-u-1119.md:115-116@e0953c7e0 |
| debt-u | 시간 문턱 L1337 | 부하성(부하 낮을 때 초록) | HANDOFF.cysr-1116-debt-u-1119.md:115-116@e0953c7e0 |
| debt-u | phoenix c6_reap S5 | 부하성(부하 낮을 때 초록) | HANDOFF.cysr-1116-debt-u-1119.md:115-116@e0953c7e0 |
| debt-u | health H-LIFE-1 · H-LIFE-2 · H-OBS-3 | 부하성(부하 낮을 때 초록) | HANDOFF.cysr-1116-debt-u-1119.md:115-116@e0953c7e0 |
| debt-u | test_capgate_hook_shell(매번 다른 시험: stale_cache_is_requeried · role_query_never_spawns_a_daemon · colliding_socket_slugs… · cache_lives_in_the_shared_0700_directory) — 단독 6회 중 2회 붉음 | 간헐(기준선 · 이 가지 변경 0) → flaky 갈래가 고침 | HANDOFF.cysr-1116-debt-u-1119.md:120@e0953c7e0 |
| debt-u | test_role_authority_shell 「A env master / rc2」(다른 갈래 「30-second backoff expires」) — 단독 6회 중 1회 붉음 | 간헐(기준선) → flaky 갈래가 고침 | HANDOFF.cysr-1116-debt-u-1119.md:117@e0953c7e0 |
| debt-u | r34 시한 측정(r34 시한 오라클) — 부하로 런처가 30s 넘게 걸리면 거짓 붉음 · uptime 1분 < 15 때 단독 재실행으로 대조 | 부하성 | HANDOFF.cysr-1116-debt-u-1119.md:141, :214@e0953c7e0 |
| flaky | test_dept_name_guard `test_create_spawn_loser_preserves_live_winner`(경쟁 스폰 승자 응답 대기 · load 18.2 · 단독 20회 고치기 전 0/20 · 고친 뒤 0/20) — debt-u 가 고친 같은 고정물 | 간헐(미재현 · 원인 이름 안 붙임) | HANDOFF.cysr-1116-flaky-1120.md:130@7dd80224e |
| flaky | capgate `test_failed_query_backs_off`(첫 호출 뒤 훅 3회가 5초 백오프 창 안에 끝나야 함 · 고친 판 70회 0건) | 부하성(극부하 때 이론상 가능) | HANDOFF.cysr-1116-flaky-1120.md:84@7dd80224e |
| flaky | owner 시험(남는 여유 = 1.6 − 1.0 − python 기동 ≈ 0.3~0.5초 · 고친 판 10회 0건) | 부하성 | HANDOFF.cysr-1116-flaky-1120.md:85@7dd80224e |
| flaky | `test_resource_gate_product_cpu` `test_9b_hung_lookup`(「ps timeout 1.5 s」가 「deadline 3.0 s」보다 먼저) | 부하성 | HANDOFF.cysr-1116-flaky-1120.md:117@7dd80224e |
| flaky | `test_phoenix_c6_reap`(`queue.parked` 관측 `until` 8초 창 · daemon_ready True · 잔재 0 · 첫 실행 탓 아님) | 부하성 의심 · 원인 추적 = 조각 5 좌석 몫 | HANDOFF.cysr-1116-flaky-1120.md:139@7dd80224e |
| flaky | 부하 주입 시간대(04:34:45~04:49:15 · load 최고 27) 다른 좌석의 시간 문턱 시험 전부 | 부하성(거짓 붉음 · 재대조 필요) | HANDOFF.cysr-1116-flaky-1120.md:94@7dd80224e · WORKER_TODO.cysr-1116-flaky-1120.md:18@7dd80224e |
| ccopen | bun test 5초 시한 시험 views/msgharness · tickrec · toastaxis T-1 퍼즈(load 50~70 · `--timeout 120000` 재실행 초록) | 부하성 | HANDOFF.cysr-1116-cc-autoopen.md:83@88def9658 |
| ccopen | race 게이트 R9e 순서 단언(기준판 번들 1회째도 rc 1 「Element is not attached」 · 2회째 PASS) | 간헐(기준선도 같음) | HANDOFF.cysr-1116-cc-autoopen.md:69@88def9658 |
| ccopen | cc_resize · office_cc 게이트 | 실행 못 함(playwright 1223 브라우저 없음) | HANDOFF.cysr-1116-cc-autoopen.md:68@88def9658 |
| ccopen | ccopen.test.ts ④ 배선 전수(`onDaemonEvent` 안 여는 호출 = 2개) · tsc(openFeed cause 필수) — 다른 갈래가 main.ts 에 `setCcOpen(true…)`/`openFeed(...)` 를 `CC_OPEN_CAUSES` 원인 없이 더하면 붉음 | 통합 핀 | HANDOFF.cysr-1116-cc-autoopen.md:63@88def9658 · ui/src/ccopen.test.ts:36@88def9658 |
| ccopen | Rust 시험: src-tauri/src/main.rs 제품부의 `"            log_cc_open,"` 개수 == 1 핀 | 통합 핀(병합 중 재정렬·중복 등록 시 붉음) | lane-facts ccopen §2(diff 기준 · 줄 번호 없음) |
| asset-skills | vendor-check BLOCK(insane-search 4파일 드리프트) | 기준선 붉음 | docs/HANDOFF-1116-asset-skills.md:68@1ff82d08a · HANDOFF-1112-skill-fold.md:134, :145@1ff82d08a |
| asset-skills | H-ASSET-1(`scripts/asset_ledger_check.py` · 본부 기계 HOME 원천 대조) | 기계 상태 의존(11-20 뒤 새 스킬·자산이 `docs/ASSET-LEDGER.md` 에 없으면 붉음) | docs/HANDOFF-1116-asset-skills.md:72@1ff82d08a · scripts/asset_ledger_check.py:20-24@f9ed0fcac |
| asset-skills | skillScan ppt-styles BLOCK(HIGH = check_pptx.py 의 subprocess · insane-search·transcription 과 같은 등급) | 기존 등급(기준선 같은 꼴) | HANDOFF-asset-skills.md:46@1ff82d08a |
| skill-revisions | `javis_registry.py verify` 를 `CYS_PACK_DIR=<저장소 팩>` 으로만 돌리면 「드리프트 · 손편집 의심」 FAIL(반드시 `--root cysjavis-pack verify`) | 측정 함정(거짓 붉음) | docs/HANDOFF-skill-revisions-1120.md:24@f9ed0fcac |
| skill-revisions | korean-humanizer 앞머리 `yaml.safe_load` 실패 | 기준선 붉음 | docs/HANDOFF-skill-revisions-1120.md:28@f9ed0fcac · docs/SKILL-REVISIONS-1120.md:102@f9ed0fcac |
| skill-revisions | asset_ledger 「139/140」 수치(H-ASSET-1) | 기계 상태 의존 | lane-facts skill-revisions §2 → docs/HANDOFF-1116-asset-skills.md:72@1ff82d08a |
| b23 | `trash::tests::test_gui_input_latency_during_slow_preview`(지연 3배 문턱 · 290ms vs 기준 55ms · 단독 통과 2회) | 부하성 | HANDOFF.cysr-1116-borrow23-1119.md:63@33a72a906 |
| b23 | `dbg_r12_init_pack_wires_profile_skill_links`(cys · 1회차 혼합 트리 실패 → 단독 통과) | 부하성/간헐 | HANDOFF.cysr-1116-borrow23-1119.md:64@33a72a906 |
| b23 | UI bun 시험 1개(시간 문턱 5,000ms 에 5,432ms) | 부하성 | HANDOFF.cysr-1116-borrow23-1119.md:66@33a72a906 |
| b23 | `test_hook_r34`(시한 1s · 3.0s 상한에 3.1~3.4s) — 같은 시각 기준 트리도 붉음(FAIL 4 대 3 · 부하 30) | 부하성 + 기준선 붉음 | HANDOFF.cysr-1116-borrow23-1119.md:70, :129@33a72a906 |
| b23 | `test_role_authority`(backoff.log 미생성) | 부하성 | HANDOFF.cysr-1116-borrow23-1119.md:70@33a72a906 |
| b23 | `test_role_authority_shell` | 부하성 | HANDOFF.cysr-1116-borrow23-1119.md:70@33a72a906 |
| b23 | `test_owner_desk`(병렬 flush 경합) | 부하성 | HANDOFF.cysr-1116-borrow23-1119.md:70@33a72a906 |
| b23 | `test_resource_gate_product_cpu`(`ps timeout 1.5 s` 시간 문턱) | 부하성 | HANDOFF.cysr-1116-borrow23-1119.md:129@33a72a906 |
| b23 | cysd `seat_proc::seatkeep_*` 4(좌석 생성 `expect("seatkeep 좌석")` 실패 · 이 가지가 안 바꾼 파일 · 단독 6/6 통과 · 부하 19.6) | 부하성 | HANDOFF.cysr-1116-borrow23-1119.md:164@33a72a906 |
| b23 | cysd `send_settle_tests` 2(분리 보류 시점 · 단독 통과) | 부하성 | HANDOFF.cysr-1116-borrow23-1119.md:164@33a72a906 |
| b23 | `test_event_inject`(④ 문단 4→5줄로 §2 줄 번호 밀림 → 복구 · 「§2 줄 번호 핀(CEO 482–524)」 · 지침 §0-B④ 문단은 4줄 유지 필요) | 갈래 원인 · 고침(통합 핀) | HANDOFF.cysr-1116-borrow23-1119.md:129@33a72a906 · 커밋 70b83cfc5 메시지 |
| debt-d | cysd `seat_proc` `seatkeep_input_ack_stall` · `seatkeep_input_ack_waits`(`handshake_timeout` · load 30~41 → 167 · 직전 머리 1ac7017d1 기준도 같은 문구로 붉음) | 부하성 + 기준선 붉음 | HANDOFF.cysr-1116-debt-d-1119.md:203@e5c0d229f |
| debt-d | cysd `send_settle` `fv1_paused`(held 단언) | 부하성(기준 재현 미확인) | HANDOFF.cysr-1116-debt-d-1119.md:203@e5c0d229f |
| debt-d | cys-app adv1 · adv2 · adv7 · adv9(동시 부하 → 단독 6/6 초록) | 부하성 | HANDOFF.cysr-1116-debt-d-1119.md:201@e5c0d229f |
| debt-d | `test_hook_r34`(1초 시한 단언 RCF-3 · RCF-4a · NZ-3 · DL-1b · WIN-2 · 3.2~4.3s · load 7 이상/9~12 · 기준점 diff 0 · prime_exec 처방 후보) | 부하성(이 가지 회귀 아님) | HANDOFF.cysr-1116-debt-d-1119.md:151, :173@e5c0d229f |
| debt-d | `test_owner_desk` R8Codex2R app_flush 0≠1 | flaky 갈래(55e7e7e99 prime_exec) 통합으로 사라질 붉음 | HANDOFF.cysr-1116-debt-d-1119.md:153, :173@e5c0d229f |
| debt-d | `test_role_authority` backoff.log FileNotFound | flaky 갈래 통합으로 사라질 붉음 | HANDOFF.cysr-1116-debt-d-1119.md:153, :173@e5c0d229f |
| debt-d | `test_v116_auto_restore_status`(`target/debug/cysd`·`cys` 0바이트·644 → `cargo build --bin cysd/cys` 뒤 3/3 초록) | 환경성 | HANDOFF.cysr-1116-debt-d-1119.md:150, :173@e5c0d229f |
| debt-d | `test_resource_gate_product_cpu` 9c(「ps timeout 1.5 s」 · 3/3 초록 load 5~10) | 부하성 의심 | HANDOFF.cysr-1116-debt-d-1119.md:152, :173@e5c0d229f |
| debt-d | capgate_hook_shell · inject_context_role_seat · refl_inject_context_role_canon(단독 재실행 초록) | 간헐 | HANDOFF.cysr-1116-debt-d-1119.md:147@e5c0d229f |
| debt-d | boot-health H-CLT-1 · H-CLT-2(훅 프리루드가 실설치 `/Applications/cys.app/.../python3` 를 집음) → e1d75b0bd 고침 | 기준선 붉음(고침) | HANDOFF.cysr-1116-debt-d-1119.md:146, :172@e5c0d229f |
| debt-d | 미등재 팩 시험 격리 실행 붉음·멈춤 5: agora_known_authentic rc 1(제작 맥 전용 · zip 필요) · dept_creds_seed rc 142(120초 상한 멈춤) · preflight_phase1_checks rc 2 · verify_gate rc 2(격리 env JAVIS_ROOT·CYS_PROBE_RUNS 요구) · seat_revival rc 1(aliased_harness_root) | 환경성(격리 실행) | HANDOFF.cysr-1116-debt-d-1119.md:47-54@e5c0d229f |
| debt-d | `debt_d3_app_autostart_task_first_on_windows_and_mac_path_byte_same`(`ensure_daemon_on` 2521 bytes · FNV 0x266f54791e1ed93e 핀 — 다른 갈래가 ensure_daemon_on 고치면 붉음) | 통합 핀(추출자 추론) | src-tauri/src/main.rs:16563-16590@e5c0d229f |
| debt-d | governance.rs `h_machine_hold_tests` B7 핀(`WriteReq::InjectRefusing {` 생산자 = `{"handlers::dispatch_method"}` 하나뿐) | 통합 핀(추출자 추론) | governance.rs 기준 ~37559@dea2e1853(lane-facts) |
| debt-d | watch_wake B7 핀(`approval_or_gate_pending(daemon, s.id) \|\| crate::governance::approval_screen_now(&s)` · `agy_door_refuses_machine_cr(&s, false)` 글자 요구) | 통합 핀(추출자 추론) | lane-facts debt-d §2(줄 번호 없음) |
| debt-d | S4-4 핀(`check_approvals` 몸통에 `approval_rebind_stale(daemon, &s)`) | 통합 핀(추출자 추론) | lane-facts debt-d §2(줄 번호 없음) |
| debt-d | lib census `cys::hidden_command("schtasks")` 개수 = 5(「schtasks 6→5」) | 통합 핀 | HANDOFF.cysr-1116-debt-d-1119.md:194@e5c0d229f |
| debt-d | cysd main.rs `auto_restore_tests` 핀(`install_from_iter_with(PACK_ALL.iter()` · `setup_isolated_config_dir(true);`) | 통합 핀(추출자 추론) | src/bin/cysd/main.rs:5454-5461@e5c0d229f |
| seatkeep | `state::tests::dbg_r12_seat_profile_wired_before_agent_exec`(여기선 통과) | 기준선 붉음 | HANDOFF.cysr-1116-seatkeep-1119.md:86-87@9b591371b |
| seatkeep | `state::tests::dbg_r12_update_lane_restore_seat_gets_link_before_exec`(여기선 통과) | 기준선 붉음 | HANDOFF.cysr-1116-seatkeep-1119.md:86-87@9b591371b |
| seatkeep | `seat_proc::tests::seatkeep_input_ack_*` ×2(stall · waits · 3초 handshake 시한 `handshake_timeout`) | 부하성(debt-d 와 같은 기준선 흔들림) | HANDOFF.cysr-1116-seatkeep-1119.md:84, :87, :267, :306, :351, :353@9b591371b |
| seatkeep | `seatkeep_stalled_consumer_does_not_block_close` 외 `seatkeep_*`(`handshake_timeout`) | 부하성 | HANDOFF.cysr-1116-seatkeep-1119.md:84, :87, :267, :306, :351, :353@9b591371b |
| seatkeep | `fv1_paused_daemon_…` | 부하성 | HANDOFF.cysr-1116-seatkeep-1119.md:267@9b591371b |
| seatkeep | `settle_hold_denies_…` | 부하성 | HANDOFF.cysr-1116-seatkeep-1119.md:306@9b591371b |
| seatkeep | `ingest_drain_throughput_bench`(941 vs 466ms) | 부하성 | HANDOFF.cysr-1116-seatkeep-1119.md:306@9b591371b |
| seatkeep | 앞 회차: boot_supervisor c6c·h5 5 · channels c6b·h3 6 · PoisonError 2 · 10초 시한 1 — 37개 부하 6 단독 재실행 37/37 통과 | 부하성 | HANDOFF.cysr-1116-seatkeep-1119.md:84-85@9b591371b |
| seatkeep | 팩 `test_hook_r34`(1초 시한) | 부하성 + 기준선 같음 | HANDOFF.cysr-1116-seatkeep-1119.md:157-166@9b591371b |
| seatkeep | 팩 `test_pyseal_negative_specimen` rc 2(ⓒ UNMEASURED — PATH 에 in-tree 비번들 python 없음) | 기준선 붉음(같음) | HANDOFF.cysr-1116-seatkeep-1119.md:157-166@9b591371b |
| seatkeep | 팩 `test_owner_desk` R8Codex2R flush request_id 0≠1 (+ R9Codex3R) | 기준선 붉음(같음) | HANDOFF.cysr-1116-seatkeep-1119.md:157-166@9b591371b |
| seatkeep | 팩 `test_role_authority` | 간헐 | HANDOFF.cysr-1116-seatkeep-1119.md:157-166@9b591371b |
| seatkeep | 팩 `test_inject_context_role_seat` | 간헐 | HANDOFF.cysr-1116-seatkeep-1119.md:157-166@9b591371b |
| seatkeep | 팩 `test_refl_inject_context_role_canon` | 간헐 | HANDOFF.cysr-1116-seatkeep-1119.md:157-166@9b591371b |
| seatkeep | 팩 `test_session_start_hook` 13a-c | 부하성 | HANDOFF.cysr-1116-seatkeep-1119.md:157-166@9b591371b |
| seatkeep | lib `raw_command_new_census_is_frozen`(`RAW_COMMAND_NEW_FROZEN` `("src/bin/cys.rs", 15)` · pkill→kill + 새 pgrep = 제품 cys.rs 날 `Command::new` +1) — 갈래는 `lib update::` 만 돌림 · (현 통합 가지 커밋 bfb52cbd2 제목 = 「동결표 … seatkeep cys.rs 15→16」) | 통합 붉음 예상(추출자 추론) | src/bin/cys.rs:21176, :23257@9b591371b · src/lib.rs(줄 번호 없음) · HANDOFF.cysr-1116-seatkeep-1119.md:352@9b591371b |
| skt1 | cysd `seat_proc::tests::seatkeep_*` handshake_timeout(기준선 3330 ok · 3 붉음 · 부하 8 단독 5/5 초록) | 기준선 붉음 · 부하성 | HANDOFF.cysr-1116-skt1-1119.md:94@b03d1cd70 |
| skt1 | 팩 `test_pyseal_negative_specimen`(UNMEASURED · rc 2 · CI 러너엔 비번들 python 있음) | 기준선 붉음(두 판 같은 사유 · 러너 환경) | HANDOFF.cysr-1116-skt1-1119.md:105@b03d1cd70 |
| skt1 | 팩 `test_owner_desk` `R8Codex2R.test_app_flush_per_item_budget_and_request_id`(예산 시간 문턱 · 단독도 두 판 붉음 · 부하 8~9) | 기준선 붉음 · 부하성 | HANDOFF.cysr-1116-skt1-1119.md:106@b03d1cd70 |
| skt1 | 팩 `test_hook_r34`(HEAD = WIN-2 3.00s · 기준선 = RCF-3·RCF-4a 1s 시한) | 기준선 붉음 · 부하성 | HANDOFF.cysr-1116-skt1-1119.md:107@b03d1cd70 |
| skt1 | 팩 `test_session_start_hook`(HEAD 팩 회차만 붉음 → 단독 두 판 초록) | 간헐 | HANDOFF.cysr-1116-skt1-1119.md:108@b03d1cd70 |
| skt1 | 팩 `test_role_authority`(붉은 사례 매번 다름 8a · 8f · 15e · 8n · G10-7c · 모두 스텁 cys 첫 실행) | 간헐(두 판 공통) | HANDOFF.cysr-1116-skt1-1119.md:109@b03d1cd70 |
| skt1 | 팩 `test_v116_auto_restore_status`(PermissionError: 기준선 target/debug/cysd) | 기준선만 붉음 | HANDOFF.cysr-1116-skt1-1119.md:110@b03d1cd70 |
| skt1 | `test_phoenix_w2_untomb_fullcycle` · `test_phoenix_e2e_replacement`(`aliased_harness_root` · 별칭 없는 TMPDIR = 8/8 · 7/7 PASS) | 환경성(TMPDIR=/tmp 별칭) | HANDOFF.cysr-1116-skt1-1119.md:277@b03d1cd70 |
| skt1 | `test_phoenix_c6_reap`(`S5 bounded observation timed out` 3/3 붉음) | 관계 미확정 · 측정 대기 | HANDOFF.cysr-1116-skt1-1119.md:277@b03d1cd70 |
| skt1 | e2e `session_lease_e2e` R1 · DD(load 118~143 에서 「정상 조건 rc 93 = 0」 단언 붉음 · 단독 2/2 초록 · 판독 시한 초과 후보) | 부하성(미확정) | HANDOFF.cysr-1116-skt1-1119.md:255, :259, :283@b03d1cd70 |
| skt1 | cys bin `b360_tests::p1_*` 9 붉음(가짜 데몬이 빈 `system.identify` 응답 → 임대 93) → 78b90a2e8 고침 | 갈래 원인 · 고침 | HANDOFF.cysr-1116-skt1-1119.md:93@b03d1cd70 |
| skt1 | (원 가지 이력) cys bin 병렬 스택 넘침 → 시험 보조가 복원 루프를 32MB 스택 스레드에서 돌림 | 이력(고침) | docs/HANDOFF-seatkeep-t1.md:209, :427-428@b03d1cd70 |
| skt1 | `spawn_policy_tests::raw_command_new_census_is_frozen`(cargo --lib · `src/session_lease_cli.rs:494` 날 `Command::new(lsof)` · 동결표에 session_lease_cli.rs 칸 없음) | 통합 붉음 예상(추출자 추론 · H-A) | src/session_lease_cli.rs:494@b03d1cd70 · src/lib.rs:7674@b03d1cd70 |
| skt1 | ② 이후 전체 묶음 미측정: 전체 `--lib` · 전체 `--bin cys` · 전체 `--bin cysd` · 전체 `-p cys-app --bins` · CI 팩 단계 전체(검체 153 · phoenix 관련 31 검체만 돌림) | 미측정(추출자 추론 H-B + 갈래 명시) | HANDOFF.cysr-1116-skt1-1119.md:277@b03d1cd70 · WORKER_TODO.cysr-1116-skt1-1119.md:27@b03d1cd70 |
| s79 | `tickrec.test` 「최악 장면」 5초 상한(부하 30 병렬 때 붉음 · 단독 기준판 4.31s · HEAD 2.85s 둘 다 21/0 · 부하 23~26 때 7.6초) | 부하성 | HANDOFF.cysr-1116-s79-1119.md:54, :189@f51261ee0 |
| s79 | 팩 step 03 `test_role_authority_shell` H6b(1122초) — 기준판도 붉음(4건 · 다른 항목) | 기준선 붉음 · 부하성 | HANDOFF.cysr-1116-s79-1119.md:100@f51261ee0 |
| s79 | 팩 `test_pyseal_census` — 1차 step08 이 작업트리에 남긴 health-full.json 오염(지움) | 작업트리 오염 | HANDOFF.cysr-1116-s79-1119.md:100@f51261ee0 |
| s79 | 팩 `test_hook_r34` RCF-3 · WIN-2(1초 시한에 3.2초 · 기준판 2·1 FAIL · HEAD 1·0 FAIL) | 부하성 + 기준선 붉음 | HANDOFF.cysr-1116-s79-1119.md:100, :107@f51261ee0 |
| s79 | step 09 `c6_reap` 「S5 bounded observation timed out」(기준판 저부하 rc 1 AssertionError) | 기준선 붉음 | HANDOFF.cysr-1116-s79-1119.md:106@f51261ee0 |
| s79 | step 08 `test_role_bootstrap_hook` B-1 훅 시간 초과(부하 19 · 단독 둘 다 rc 0) | 부하성 | HANDOFF.cysr-1116-s79-1119.md:105@f51261ee0 |
| s79 | step 08 H-CLT-1 · H-CLT-2(「integ 인계 기준선(이 기기 python 해소)」) | 기준선 붉음 | HANDOFF.cysr-1116-s79-1119.md:105@f51261ee0 |
| s79 | step 08 H-SECRET-1 = 갈래 결함 → 116da5367 고침 | 갈래 원인 · 고침 | HANDOFF.cysr-1116-s79-1119.md:105@f51261ee0 |
| s79 | step 10 `test_session_start_hook` 3a · 3b(단독 둘 다 rc 0) | 부하성 | HANDOFF.cysr-1116-s79-1119.md:107@f51261ee0 |
| s79 | step 02 / 09 rustup 기본 툴체인 없음 | 환경성 | HANDOFF.cysr-1116-s79-1119.md:99, :106@f51261ee0 |
| s2 | 팩 `test_hook_r34` WIN-2 / RCF-3 | 부하성 + 기준선 붉음(같은 사유) | HANDOFF.cysr-1116-s2-1119.md:97-100@06711fbc9 |
| s2 | 팩 `test_role_authority_shell` K1 · K2b-3 | 간헐(1회 흔들림) | HANDOFF.cysr-1116-s2-1119.md:97-100@06711fbc9 |
| s2 | 팩 `test_resource_gate_product_cpu` 9b · 9c(`ps timeout 1.5 s` ↔ 기대 `deadline 3.0 s`) | 부하성(시한 흔들림) | HANDOFF.cysr-1116-s2-1119.md:97-100@06711fbc9 |
| s2 | 팩 `test_capgate_hook_shell`(작업트리 3/5 붉음 · 기준선 0/3 → 독립 검증: 훅 2초 마감 · 기준선도 2/5 붉음 · 「이 갈래 고칠 것 아님(master)」) | 간헐 → 독립 검증 판정 환경성(기준선도 붉음) | HANDOFF.cysr-1116-s2-1119.md:97-100, :137@06711fbc9 |
| s2 | cysd `a_spawned_pty_child_does_not_inherit_the_lock_fd` | 부하성(3R · 단독·4R 전체 초록 · 기준선 대조 안 함) | HANDOFF.cysr-1116-s2-1119.md:194@06711fbc9 |
| s2 | cysd `reclaim_commit_aborts_on_every_race_without_partial_effect` | 부하성(같음) | HANDOFF.cysr-1116-s2-1119.md:194@06711fbc9 |
| s2 | cysd `v116_send_text_agent_launch_passes_vacant_seat_guard_only_for_seat_bin` | 부하성(같음) | HANDOFF.cysr-1116-s2-1119.md:194@06711fbc9 |
| s2 | cysd `seatkeep_input_ack_stall_ends_seat_when_consumer_never_resumes` | 부하성(같음) | HANDOFF.cysr-1116-s2-1119.md:194@06711fbc9 |
| s2 | cysd `seatkeep_input_ack_waits_while_consumer_runs_and_stdin_unread` | 부하성(같음) | HANDOFF.cysr-1116-s2-1119.md:194@06711fbc9 |
| s2 | cysd `k17_refuse_mode_return_raises_settle_marker_but_cancel_key_does_not` | 부하성(같음) | HANDOFF.cysr-1116-s2-1119.md:194@06711fbc9 |
| s2 | bun `tickrec.test.ts` 「최악 장면」(부하 32 에서 15.9 · 12.2초 · 부하 6 단독 1.58초 초록) | 부하성 | HANDOFF.cysr-1116-s2-1119.md:58@06711fbc9 |
| s2 | `with(scope)` 하네스 시험 roleactivity · deptprogresswiring · closecallbacks · kbrestore · b230scroll — 새 자유 변수 넣으면 대역 목록에도(관측 51건 붉음) | 통합 핀 | HANDOFF.cysr-1116-s2-1119.md:282@06711fbc9 |
| s2 | 소스 핀이 고리 본문 식별자까지 잡음(`await closePane(sid, ws.socket);`) | 통합 핀 | HANDOFF.cysr-1116-s2-1119.md:283@06711fbc9 |
| s5 | `test_phoenix_c6_reap`(기준판 2회 · 이 가지 1회 모두 AssertionError 「S5 bounded observation timed out」 test_phoenix_c6_reap.py:166 · 5회차도 같음) | 기준선 붉음 | HANDOFF.cysr-1116-s5-1119.md:93, :226-227, :304@305f08930 |
| s5 | `test_hook_r34`(DL-1b 시한) | 기준선 붉음(같음) | HANDOFF.cysr-1116-s5-1119.md:93@305f08930 |
| s5 | 팩 `test_role_authority` · `test_role_authority_shell` · `test_owner_desk` · `test_pyseal_negative_specimen` · `test_capgate_hook_shell` · `test_refl_inject_context_role_canon`(첫 단독 3 붉음 → 둘째 단독 6/6 초록 · 기준 작업트리도 초록) | 부하성 | HANDOFF.cysr-1116-s5-1119.md:93@305f08930 |
| s5 | cysd `seat_proc::seatkeep_input_ack_waits_while_consumer_runs_and_stdin_unread`(handshake_timeout) | 부하성 | HANDOFF.cysr-1116-s5-1119.md:85@305f08930 |
| s5 | cysd `seat_proc::tests::seatkeep_input_ack_stall_ends_seat_when_consumer_never_resumes` · `seatkeep_input_ack_waits_while_consumer_runs_and_stdin_unread` · `seatkeep_stalled_consumer_does_not_block_close`(seat_proc_tests.rs:384/307 「seatkeep 이 접속을 거절: handshake_timeout」) | 부하성(시한형) | HANDOFF.cysr-1116-s5-1119.md:256@305f08930 |
| s5 | cysd 16건 연쇄 붉음(앞 시험이 `ACL_ENV_LOCK` 을 쥔 채 10초 시한으로 죽어 PoisonError 연쇄 · s5 시험 `s5_1116_human_input_seq_paired…` · `s5_1116_close_if_quiet_atomic_conditions` 도 `ACL_ENV_LOCK` 사용) | 부하성 | HANDOFF.cysr-1116-s5-1119.md:85@305f08930 |
| s5 | cysd `send_settle_tests::b16_fix::b16fix_human_refuse_event_carries_request_id_of_response`(b16_fix_tests.rs:211) | 부하성(시한형) | HANDOFF.cysr-1116-s5-1119.md:284@305f08930 |
| s5 | cysd `send_settle_tests::k17_refuse_mode_return_raises_settle_marker_but_cancel_key_does_not` | 부하성(시한형) | HANDOFF.cysr-1116-s5-1119.md:312@305f08930 |
| s5 | `handlers::tests::wp5_queue_list_hides_expired_unless_requested`(원작자 시험 · 고정물에 `paste_opened_at = Some(now)` 1줄 추가 · `paste_open_now` 뜻 변경 — 다른 갈래 시험이 `in_paste=true` 만 두고 `input_paste_open=true` 기대하면 붉음) | 통합 핀 | HANDOFF.cysr-1116-s5-1119.md:311@305f08930 |
| s5 | UI `tickrec.test` 「링 200칸 … 최악 장면」 5초 | 부하성 | HANDOFF.cysr-1116-s5-1119.md:87@305f08930 |
| s5 | run_bootstrap_health H-CLT-1 · H-CLT-2(호스트 환경) | 기준선 붉음 | HANDOFF.cysr-1116-s5-1119.md:288@305f08930 |
| s5 | run_bootstrap_health B-2 `test_bootstrap_chain`(300초 시한) | 부하성 | HANDOFF.cysr-1116-s5-1119.md:287@305f08930 |
| s6 | `ui/src/tickrec.test.ts` 최악 장면 덤프 5초 | 부하성(단독 초록) | HANDOFF.cysr-1116-s6-1119.md:61, :106@94ddcd1cf |
| s6 | `test_session_start_hook` 19b | 부하성(단독 초록) | HANDOFF.cysr-1116-s6-1119.md:71, :106@94ddcd1cf |
| s6 | seatkeep `seat_proc::tests::seatkeep_input_ack_stall_ends_seat_when_consumer_never_resumes` · `seatkeep_input_ack_waits_while_consumer_runs_and_stdin_unread` · `seatkeep_stalled_consumer_does_not_block_close`(「seatkeep 이 접속을 거절: {"reason":"handshake_timeout"}」 seat_proc_tests.rs:384·307 · 통합 인계서 §4-1 과 같은 이름·문구) | 부하성 | docs/1116-s6/DAEMON-6b.md:51@94ddcd1cf · HANDOFF.cysr-1116-s6-1119.md:64, :177@94ddcd1cf |
| s6 | `test_role_authority_shell`(단독 HEAD·기준선 둘 다 rc 0) | 부하성 | HANDOFF.cysr-1116-s6-1119.md:71, :106@94ddcd1cf |
| s6 | codex 1R 회차 `seat_proc::…seatkeep_stalled_consumer_does_not_block_close` · `…_input_ack` | 부하성 | HANDOFF.cysr-1116-s6-1119.md:165@94ddcd1cf |
| s6 | `send_settle_tests::{fv1_paused_daemon_gives_no_settle_proof_but_keeps_hold, settle_hold_denies_text_while_submit_cr_inflight_then_admits, settle_proven_denial_events_are_rate_limited_per_sender}`(send_settle 83건 묶음 기준판 90b2160c7 = 83/0 · 이 판 = 83/0) | 부하성(흔들림) | HANDOFF.cysr-1116-s6-1119.md:165@94ddcd1cf |
| s6 | `trash::tests::the_frontier_release_rate_stays_within_the_declared_envelope` | 부하성(흔들림) | HANDOFF.cysr-1116-s6-1119.md:165@94ddcd1cf |
| s6 | `test_pyseal_negative_specimen`(UNMEASURED · 비번들 python 없음 · 기준선 dea2e1853 같은 사유 rc 2) | 기준선 붉음 | HANDOFF.cysr-1116-s6-1119.md:71@94ddcd1cf |
| s6 | `test_cso_directive_rev` 상한 ⑦(MASTER 86,625 → 87,810 · CEO 102,111 → 103,296 · +1,185 B — b23 과 손 병합 필요) | 통합 핀(바이트 예산) | HANDOFF.cysr-1116-s6-1119.md:42@94ddcd1cf |
