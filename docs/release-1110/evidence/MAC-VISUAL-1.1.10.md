# 맥 실앱 확인 — 상담소 끄기/켜기·첫 안내 (TICKET=cysr-1110-visual · 2026-10-23 07:33~07:48 KST)

발행 노트 초안 「하루 한 번, 문제를 빨리 찾기 위한 짧은 보고를 보냅니다」 절의 【발행 전 확인】 중 **맥 몫**의 실측 기록이다.
윈도우 몫은 이 문서와 무관하게 남아 있다.

## 무엇을 띄웠나

- 빌드: 가지 `fix/1110-counsel-off` — 첫 실행 `76048bd1`, 수리 뒤 재실행 `98a63c92`(꺼짐 안내문 수리 · 아래 4행).
  `scripts/bundle-prep.sh`(ui·cys·cysd·동봉 팩) + `cargo build --release -p cys-app --features tauri/custom-protocol`.
- 격리(실 설치본 /Applications/cys.app · ~/.cys · 실행 중 cysd 와 섞이지 않게):
  - `env -i` 로 시작해 HOME · 팩 · 설정 · 소켓(/tmp 짧은 경로) · 갱신기 상태 · 아고라 설정 폴더를 전부 임시 폴더로 지정.
  - 앱 식별자만 `com.cysjavis.terminal.isocheck` 로 바꿔 빌드(`TAURI_CONFIG`) — 같은 식별자면 「한 개만 실행」 장치가
    실 설치본의 `/tmp/com_cysjavis_terminal_si.sock` 에 붙어 실 앱을 건드린다(플러그인 원본 `tauri-plugin-single-instance-2.4.2/src/platform_impl/macos.rs:60-70`).
    화면·문구·동작 코드는 그대로다.
  - 번들은 임시 폴더 아래 `Applications/cysr.app` 에 두었다(정규 위치 판정 `src-tauri/src/main.rs:909-912` 통과용).
    격리 cysd 를 먼저 띄워 두어 launchd 위임·등록 경로가 실 서비스에 손대지 않게 했다
    (실측: 앱 로그 `launchd autoregister: DeferredDaemonRunning` → 재실행 `AlreadyRegistered` · plist 는 격리 HOME 안에만 생김).
  - 보낼 곳은 전부 가짜 주소(`127.0.0.1:18917`, 받은 요청을 한 줄씩 적는 작은 서버): 도움 서버(`CYS_FEEDBACK_BASE`) ·
    아고라 릴레이(격리 `config.json` 의 relay.url) · 갱신 주소. 갱신기 id 도 격리 폴더의 가짜 값.
- 화면 확인: 접근성 트리(그 앱 pid 만 — `AXUIElementCreateApplication`)로 글자·단추를 읽고 눌렀다.
  사진은 이 좌석에 화면 기록 권한이 없어 박사님(첫 안내 창)·master(상담소 창)가 찍었다.

## 결과 표

| # | 항목 | 기대 | 실측 | 캡처 | 확신도 |
|---|---|---|---|---|---|
| 1 | 첫 안내 창 | 앱 시작 5초 뒤 「상담소 안내」 창 · 승인 문구 글자 그대로 · 단추 「확인」·「상담소 끄기」 | 떴다(앱 v1.1.10 · 엔진 v1.1.10 · 시작 뒤 첫 확인 때 이미 떠 있었다 — 정확한 초는 재지 않음). 문구 = 팩 `HELP_NOTICE` 와 같은 글자 · 단추 둘 | `(비공개 보관) mac-first-notice-owner-eye-20261023-0739.png`(박사님 눈 확인·캡처 07:39) | High |
| 2 | 안내 전 미전송 | 안내 표식이 생기기 전에는 보내지 않는다 | 앱이 뜬 뒤 안내를 닫기 전까지 가짜 서버 수신 = 내 연결 확인 1건(`GET /ping`)뿐 · `auto-status` = `needs_notice: true` | — | High |
| 3 | 「확인」 뒤 | 「봤음」 표식(`counsel/help-notice.json`) · 켜짐 유지 · 창 닫힘 | 표식 생김(`shown` 시각 + 같은 문구) · `{"auto": true, "notice_seen": true, "needs_notice": false}` · 안내 창 사라짐 | — | High |
| 4 | 켜짐일 때 실제로 1통 가는가(양성 대조) | 같은 날 첫 판에 하루 보고 1통 | `tick` 1회 → 가짜 서버 `POST /api/report` 1건(kind=daily · installer_version 1.1.10 · os mac · 응답 200) · `tick.log` 에 `help ran` + `help-notice` 한 줄 | — | High |
| 5 | 상담소 창 · 켜짐 | 맨 위 「자동 보고: 켜짐」 + 「상담소 끄기」 · 아래 승인 문구 | 그대로 | `(비공개 보관) mac-counsel-panel-on-20261023.png`(끄기→켜기 왕복 뒤) | High |
| 6 | 「상담소 끄기」 | 「자동 보고: 꺼짐」 + 「상담소 켜기」 · 설정 `counsel.auto=false`(동봉 클라이언트 `agora counsel off`) | 그대로 · `tick.log` `auto-set want=off auto=false client=true` | `(비공개 보관) mac-counsel-panel-off-20261023.png` | High |
| 6a | 꺼짐일 때 아래 안내문 | (master 눈 검수 지적) 꺼졌는데 「끄려면 ‘상담소 끄기’를 누르세요」가 그대로 → 꺼짐일 때만 「지금은 보내지 않습니다. 다시 켜려면 ‘상담소 켜기’를 누르세요.」 | 수리 `98a63c92` 뒤 재실행에서 꺼짐 = 새 문장 · 켜짐 = 승인 문구 그대로(접근성 트리 둘 다 확인) | `(비공개 보관) mac-counsel-panel-off-fixed-20261023.png`(master 눈 검수 통과) | High |
| 7 | 끈 뒤 보내기 0 | 꺼진 동안은 몇 판을 돌려도 0통 | 그날 표식(`help-state.json`)을 지워 「오늘 이미 보냄」이 가리지 못하게 한 뒤 `tick` 2판(수리 전) + 3판(수리 뒤) = 가짜 서버 새 수신 **0건** · 각 판 아고라 출력 `{"보냄": 0, "상담소_자동_전달": "꺼짐"}` · `help_report()` 직접 호출 = `off` | — | High |
| 8 | 「상담소 켜기」 | 「자동 보고: 켜짐」 + 「상담소 끄기」로 돌아온다 · `counsel.auto=true` | 그대로 · `tick.log` `auto-set want=on auto=true client=true` | `(비공개 보관) mac-counsel-panel-on-20261023.png` | High |
| 9 | 실 설치본 무접촉 | 실 cysd · launchd · 팩 · 아고라 설정 · LaunchAgents · /Applications 무변화 | 전후 대조: launchd cysd PID 989 그대로 · 실 팩 `.pack-version` 1.1.9 그대로 · 실 `~/.config/agora/config.json` sha1 `1bb463e2…` 그대로 · `~/Library/LaunchAgents` 목록 그대로 · `/Applications/cys.app` 안 새 파일 0 · 보낸 갱신기 id = 격리 가짜 값(실 id 와 다름) | — | High |

### 표 밖에서 본 것(사실만)

- 상담소 창의 「상담소 글을 가져오지 못했어요 …」 줄과 우하단 알림 2개(런타임 python 없음 · Claude Code CLI 없음)는
  격리 탓이다(릴레이가 가짜 주소 · 번들에 런타임을 넣지 않음 · PATH 에 claude 없음). 이번 확인 대상과 무관.
- 실 `~/.cys/update/state.json` 이 07:41 에 `{}` 로 다시 쓰였다. 격리 앱의 갱신기 상태 폴더는 격리 HOME 쪽이었다
  (`txn.part.lock` 07:37 생성 실측 · `src/update/buildinfo.rs:96-102` = `dirs::home_dir()` 기준). 실 쪽 기록은 실 앱의 주기 작업으로 본다 — 확신도 Med(직접 귀속 실측 없음).
- 맥 WebKit 은 HOME 을 바꿔도 실 `~/Library` 에 앱별 폴더를 만든다: `~/Library/WebKit/cys-app`·`~/Library/Caches/cys-app`(07:36:53 생성) ·
  `~/Library/WebKit/com.cysjavis.terminal.isocheck`·`~/Library/Caches/com.cysjavis.terminal.isocheck`(07:37:58 생성). 실 앱 폴더(`com.cysjavis.terminal`)는 손대지 않았다. 지우기는 master 판단.
- 이 좌석에서 System Events(osascript)로 pid 를 지정해 창을 물으면 같은 실행 파일 이름(cys-app)의 실 설치본 창이 돌아왔다(읽기만 · 누르기 0). 그래서 pid 직접 접근성 도구만 썼다.


> 사진 4장은 화면에 실제 계정·기기 이름이 찍혀 있어 저장소에 두지 않는다 — master 쪽 비공개 보관.
