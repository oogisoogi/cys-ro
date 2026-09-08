# S6 판정 — Windows 자동가동 등록이 환경변수를 실을 수 있는가

> TICKET=cys-phoenix-korean-windows S6 · 2026-09-08 · **소스 판정만**(Windows 실기 실행 0).
> 묻는 것: 설치기 처방 **C안(실행 지점만 좁게 env 를 준다)** 이 성립하는가.

## 판정 (1줄)

**C 는 안 된다 — 정확히는 「한 번 심을 수는 있으나 벤더가 다음 버전에 지운다」.**
등록은 `schtasks /Create /XML` 이고 그 XML 의 실행부는 `<Exec><Command>cysd.exe</Command></Exec>`
**exe 직접 등록**이라 env 를 실을 자리가 없고, 래퍼로 바꿔 심어도 벤더의 GUI 온보딩이
`cys daemon install` 을 **버전마다** 다시 불러 `/F` 로 통째 덮어쓴다.

## 근거 (전부 이 저장소 소스)

### ① 등록 형태 = XML · exe 직접 · 인자 없음

`src/bin/cys.rs:11281~11288` (`DaemonAction::Install`, `#[cfg(windows)]`):

```rust
let xml = cysd_task_xml(&daemon, &user);
write_utf16le_bom(&xml_path, &xml)?;
std::process::Command::new("schtasks")
    .args(["/Create", "/XML"]).arg(&xml_path)
    .args(["/TN", TASK, "/F"])      // TASK = "cysd"
```

★**`/TR` 경로는 쓰지 않는다.** 명령줄 등록에는 `RestartOnFailure` 플래그가 없어 XML 로 갔다
(`cys.rs:1855` 주석). 그러니 「설치기가 `/TR` 문자열을 손보면 된다」는 접근은 애초에 대상이 없다.

`cysd_task_xml`(`cys.rs:1888~1938`)의 실행부 전문:

```xml
  <Actions Context="Author">
    <Exec>
      <Command>{cysd.exe 절대경로}</Command>
    </Exec>
  </Actions>
```

`<Arguments>` 도 `<WorkingDirectory>` 도 없다. 래퍼 셸도 없다 — **데몬 exe 직접 등록**이다.

### ② 작업 스케줄러 스키마에 환경변수 요소가 없다

Task Scheduler `Exec` 요소가 갖는 자식은 `Command` · `Arguments` · `WorkingDirectory` 셋뿐이고,
Task 스키마 어디에도 환경변수 항목이 없다. 그래서 **등록 정의만으로는 env 를 실을 수 없다.**
작업은 로그온 시점의 그 사용자 환경 블록을 상속할 뿐이다.

⚠이 문단은 **Windows 문서·스키마 근거**이며 이 맥 개발기에서 실측한 것이 아니다(§4 실측 규율).
반증 가능한 형태로 적어 둔다 — Windows 실기에서 `schtasks /Query /XML` 로 확인 가능하다.

### ③ 그래서 C 를 하려면 `<Command>` 를 래퍼로 바꿔야 한다

유일하게 남는 방법은 벤더가 등록한 태스크를 설치기가 다시 써서

```xml
<Command>cmd.exe</Command>
<Arguments>/c set PYTHONUTF8=1 &amp;&amp; "…\cysd.exe"</Arguments>
```

로 만드는 것이다. 즉 **설치기가 벤더의 등록 내용을 덮어쓰는 일**이 된다.

### ④ ★그리고 벤더가 그것을 다시 지운다 — 이것이 결정적이다

`src-tauri/src/main.rs:4013~4023` (`maybe_windows_onboard`):

```rust
let mut reg = std::process::Command::new(&cys);
reg.arg("daemon").arg("install");     // = schtasks /Create /XML … /F  (통째 재작성)
```

그리고 이 온보딩을 건너뛰는 조건은 `gui_onboarded_path()` 마커가 **현재 바이너리 버전과 정확히
일치**할 때뿐이다(`main.rs:3226~3240` doc: "마커 내용이 현재 바이너리 버전과 정확히 일치할 때만
스킵. 부재·불일치·읽기 실패 = 실행").

⇒ **앱 버전이 오를 때마다 온보딩이 다시 돌고, 태스크 정의가 원본으로 되돌아간다.**
설치기가 심은 래퍼는 그때 조용히 사라지고, **사라졌다는 신호가 어디에도 남지 않는다.**
「임시 처방이 다음 업데이트에 말없이 풀리는」 형태이며, 그것은 처방이 없는 것보다 나쁘다 —
사람은 처방이 걸려 있다고 믿고 있기 때문이다.

### ⑤ 다른 앵커는 없다

레지스트리 Run 키 경로는 이 저장소 소스에 **0건**이다(`src/`·`src-tauri/src` 전수 grep).
Windows 자동가동 앵커는 작업 스케줄러 태스크 `cysd` 하나뿐이다.
GUI 의 `ensure_daemon`(`main.rs:4108~`)도 `Command::new(program)` 으로 cysd 를 띄울 뿐
`.env(...)` 를 싣지 않으므로, 그 경로 역시 자기 프로세스 환경(=사용자 환경 블록)을 물려줄 뿐이다.

## 설치기가 손댈 자리를 굳이 묻는다면

**레지스트리 Run 키가 아니라 작업 스케줄러 태스크 `cysd` 의 `<Actions><Exec><Command>` 다.**
(`/TR` 아님 — 그 경로는 쓰이지 않는다.) 다만 위 ④ 때문에 **권할 수 없다.**

## 그래서 남는 선택지

| 안 | 판정 |
|---|---|
| **C** 실행지점 한정 | ⛔**불가**(유지 불가) — 근거 ①~④ |
| **B** 사용자 환경변수 | 가능·지속됨. 대가 = 그 사용자의 다른 파이썬 전체가 UTF-8 모드가 된다(cp949 파일을 인코딩 인자 없이 읽던 프로그램이 깨진다) |
| **D** 우리 포크 빌드 배포 | 부작용 0·근본 수리. 대가 = 서명·배포·유지보수를 우리가 진다 |
| **A** 대기 | 그때까지 한국어 Windows 참가자는 부활이 계속 0 |

★한 가지 덧붙입니다. **우리 포크에는 이 처방이 아예 필요 없습니다** — 커밋 `07ab986`/`3d6eb01`
이후 `python_command`·`spawn_env_pairs` 두 층이 파이썬 자식에게 직접 `PYTHONUTF8` 을 싣기
때문입니다. 즉 B 든 C 든 **오직 벤더 배포본을 위한 임시 조치**이고, PR 이 배포에 실리는 순간
전부 걷어내야 하는 것들입니다. 그 관점에서 보면 **A(대기) 와 D(포크 배포) 의 대비**가 실질적인
선택이고, B 는 그 사이를 메우되 남의 컴퓨터에 값을 치르는 안입니다.

## 이 문서가 재지 못한 것

- Windows 실기에서 `schtasks /Query /XML` 로 스키마 사실(②)을 확인하지 않았다.
- 래퍼 등록이 `RestartOnFailure`·`IgnoreNew` 같은 다른 설정과 실제로 어떻게 상호작용하는지
  실행해 보지 않았다. ④ 때문에 C 를 권하지 않으므로 재지 않았다 — **필요해지면 재야 한다.**
