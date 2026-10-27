//! 윈 작업 스케줄러 — 러너 일회 작업 · 복구기 로그온 작업(설계 AUTO-UPDATE-118 §3-1 · 1R MAJOR 8 · 2R MAJOR 4 · §3-11 · N14 · P4).
//!
//! - `schtasks.exe`·`cmd /c` 0 — **작업 스케줄러 COM**(`ITaskService`)으로 등록한다. windows-sys 0.59 에는 작업 스케줄러 인터페이스가
//!   없어서 vtable 을 직접 선언한다(taskschd.h 순서 · IDispatch 7칸 뒤). 정의는 XML 한 장(`RegisterTask`)으로 넣는다.
//! - 폴더 `\cysr\<install_id>` · 폴더와 작업에 명시 SDDL `D:P(A;;FA;;;SY)(A;;FA;;;<현재 사용자 SID>)`(상속 끊음).
//! - 등록 뒤 **COM 으로 정의를 다시 읽어** ① `Command` 경로 ② `Arguments` 를 윈 명령줄 규칙으로 되파싱한 배열 = 우리가 쓴 배열
//!   ③ 주체 SID · 로그온 형 ④ 폴더·작업 SDDL 을 **구조적으로** 대조한다(문자열 비교 아님) — 다르면 삭제 · `update.win_task_refused`.
//! - 사용자 권한으로 작업 생성이 되는지 = 【미확인 → W1 ⑤】(안 되면 설치기 변경 = 비가역 · master).
//! - ★1.1.11 수리(TICKET=win-selfupdate-recover · 윈 11 26200 ko-KR 표준 사용자 실측 2026-10-27 07:53): 등록 플래그에
//!   `TASK_DONT_ADD_PRINCIPAL_ACE(0x10)` 가 없으면 스케줄러가 작업 SD 의 **보호 P 를 떼고 주체 FR ACE 를 덧붙인다** →
//!   재독 대조가 매번 거부(1.1.10 윈 자동 갱신 전면 정지). 플래그 = [`register_flags`] · 거부 사유 = 칸별([`judge`]) ·
//!   거부 시 지우기 **전에** 사유·읽은 SDDL·XML 을 갱신 폴더 `win-task-refusal-<작업>.json` 에 남긴다(증거 보존).
//! - 순수 부분(인자 직렬화·되파싱 · XML 생성·읽기 · SDDL 구조 대조)은 모든 기판에서 시험한다.

use std::path::Path;

pub const FOLDER_ROOT: &str = "cysr";
pub const RUNNER_TASK: &str = "runner";
pub const RECOVER_TASK: &str = "recover";

/// Rust std 윈 인자 따옴표 규칙(= `CommandLineToArgvW` 가 되읽는 규칙)으로 인자 1개를 직렬화.
pub fn quote_arg(a: &str) -> String {
    if !a.is_empty() && !a.contains([' ', '\t', '\n', '\u{0b}', '"']) {
        return a.to_string();
    }
    let mut out = String::from("\"");
    let mut bs = 0usize;
    for c in a.chars() {
        match c {
            '\\' => bs += 1,
            '"' => {
                out.extend(std::iter::repeat('\\').take(bs * 2 + 1));
                out.push('"');
                bs = 0;
                continue;
            }
            _ => {}
        }
        if c != '\\' {
            out.extend(std::iter::repeat('\\').take(bs));
            bs = 0;
            out.push(c);
        }
    }
    out.extend(std::iter::repeat('\\').take(bs * 2));
    out.push('"');
    out
}

pub fn join_args(args: &[&str]) -> String {
    args.iter().map(|a| quote_arg(a)).collect::<Vec<_>>().join(" ")
}

/// `CommandLineToArgvW` 의 인자 규칙(프로그램 이름 칸이 아닌 부분) 되파싱(순수): 공백 구분 · `"` 토글 · `2n` 역슬래시+`"` = n 역슬래시 +
/// 토글 · `2n+1` 역슬래시+`"` = n 역슬래시 + 글자 `"` · 따옴표 안 `""` = 글자 `"`.
pub fn parse_args(s: &str) -> Vec<String> {
    let cs: Vec<char> = s.chars().collect();
    let mut out = Vec::new();
    let mut i = 0;
    while i < cs.len() {
        while i < cs.len() && (cs[i] == ' ' || cs[i] == '\t') {
            i += 1;
        }
        if i >= cs.len() {
            break;
        }
        let mut cur = String::new();
        let mut inq = false;
        while i < cs.len() {
            let c = cs[i];
            if !inq && (c == ' ' || c == '\t') {
                break;
            }
            if c == '\\' {
                let mut n = 0;
                while i < cs.len() && cs[i] == '\\' {
                    n += 1;
                    i += 1;
                }
                if i < cs.len() && cs[i] == '"' {
                    cur.extend(std::iter::repeat('\\').take(n / 2));
                    if n % 2 == 1 {
                        cur.push('"');
                        i += 1;
                    }
                } else {
                    cur.extend(std::iter::repeat('\\').take(n));
                }
                continue;
            }
            if c == '"' {
                if inq && i + 1 < cs.len() && cs[i + 1] == '"' {
                    cur.push('"');
                    i += 2;
                    continue;
                }
                inq = !inq;
                i += 1;
                continue;
            }
            cur.push(c);
            i += 1;
        }
        out.push(cur);
    }
    out
}

fn xml_escape(s: &str) -> String {
    s.replace('&', "&amp;").replace('<', "&lt;").replace('>', "&gt;").replace('"', "&quot;").replace('\'', "&apos;")
}

fn xml_unescape(s: &str) -> String {
    s.replace("&quot;", "\"").replace("&apos;", "'").replace("&gt;", ">").replace("&lt;", "<").replace("&amp;", "&")
}

/// 작업 정의 XML(순수). `logon_trigger` = 복구기(로그온 때 실행) · 아니면 트리거 없음(러너 = 등록 직후 Run).
pub fn task_xml(command: &Path, args: &[&str], user_sid: &str, logon_trigger: bool) -> String {
    let trig = if logon_trigger { format!("<Triggers><LogonTrigger><Enabled>true</Enabled><UserId>{}</UserId></LogonTrigger></Triggers>", xml_escape(user_sid)) } else { String::new() };
    format!(
        "<?xml version=\"1.0\" encoding=\"UTF-16\"?>\n<Task version=\"1.2\" xmlns=\"http://schemas.microsoft.com/windows/2004/02/mit/task\">\
<RegistrationInfo><Description>cysr auto-update</Description></RegistrationInfo>{trig}\
<Principals><Principal id=\"Author\"><UserId>{sid}</UserId><LogonType>InteractiveToken</LogonType><RunLevel>LeastPrivilege</RunLevel></Principal></Principals>\
<Settings><MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy><DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>\
<StopIfGoingOnBatteries>false</StopIfGoingOnBatteries><ExecutionTimeLimit>PT2H</ExecutionTimeLimit><Hidden>true</Hidden><Enabled>true</Enabled></Settings>\
<Actions Context=\"Author\"><Exec><Command>{cmd}</Command><Arguments>{a}</Arguments></Exec></Actions></Task>",
        sid = xml_escape(user_sid),
        cmd = xml_escape(&command.to_string_lossy()),
        a = xml_escape(&join_args(args)),
    )
}

/// 다시 읽은 정의의 비교 칸.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TaskDef {
    pub command: String,
    pub args: Vec<String>,
    pub user_id: String,
    pub logon_type: String,
    pub logon_trigger: bool,
}

fn tag<'a>(xml: &'a str, name: &str) -> Option<&'a str> {
    let open = format!("<{name}>");
    let s = xml.find(&open)? + open.len();
    let e = xml[s..].find(&format!("</{name}>"))? + s;
    Some(&xml[s..e])
}

/// XML → 비교 칸(순수 · 작업 스케줄러가 돌려주는 정규화 XML 도 같은 태그 이름을 쓴다).
pub fn parse_task_xml(xml: &str) -> Option<TaskDef> {
    let principals = tag(xml, "Principals")?;
    Some(TaskDef {
        command: xml_unescape(tag(xml, "Command")?.trim()),
        args: parse_args(&xml_unescape(tag(xml, "Arguments").unwrap_or(""))),
        user_id: xml_unescape(tag(principals, "UserId")?.trim()),
        logon_type: tag(principals, "LogonType").unwrap_or("").trim().to_string(),
        logon_trigger: xml.contains("<LogonTrigger"),
    })
}

/// 우리 SDDL(순수).
pub fn sddl_for(user_sid: &str) -> String {
    format!("D:P(A;;FA;;;SY)(A;;FA;;;{user_sid})")
}

/// `ITaskFolder::RegisterTask` 플래그 — `TASK_CREATE_OR_UPDATE`(6).
pub const TASK_CREATE_OR_UPDATE: i32 = 0x6;
/// `TASK_DONT_ADD_PRINCIPAL_ACE`(0x10) — 없으면 스케줄러가 작업 주체 허용 ACE 를 스스로 붙인다(MS 문서 · 윈 실측: `(A;;FR;;;나)` +
/// 보호 P 소실).
pub const TASK_DONT_ADD_PRINCIPAL_ACE: i32 = 0x10;

/// 등록 플래그(★1.1.11) = 생성·갱신 + 주체 ACE 추가 금지. 뮤턴트 `WT1` = 1.1.10 의 6 으로 되돌린다.
pub fn register_flags() -> i32 {
    if super::mutant("WT1") {
        TASK_CREATE_OR_UPDATE
    } else {
        TASK_CREATE_OR_UPDATE | TASK_DONT_ADD_PRINCIPAL_ACE
    }
}

/// SDDL 구조 대조(순수) — 판정은 1.1.10 과 같다: DACL 보호(P) · 허용 ACE 주체 집합 = {SY, 나} · 거부·그 밖 ACE 0 · 권한 = FA(또는
/// 같은 값의 16진). ★1.1.11: 어긋난 칸을 **전부** 사유로 돌려준다(첫 칸에서 멈추지 않음 — 윈 거부 원인 판독용).
pub fn sddl_check(sddl: &str, me: &str) -> Result<(), Vec<String>> {
    let Some(d) = sddl.find("D:") else { return Err(vec!["DACL(D:) 없음".into()]) };
    let dacl = sddl[d + 2..].split("S:").next().unwrap_or("");
    let flags_end = dacl.find('(').unwrap_or(dacl.len());
    let mut why = Vec::new();
    if !dacl[..flags_end].contains('P') {
        why.push(format!("보호(P) 없음 — 상속 열림(DACL 표지 {:?})", &dacl[..flags_end]));
    }
    let mut who = std::collections::BTreeSet::new();
    let mut seen = std::collections::BTreeMap::<String, usize>::new();
    for ace in dacl[flags_end..].split(['(', ')']).filter(|x| !x.is_empty()) {
        let f: Vec<&str> = ace.split(';').collect();
        if f.len() != 6 {
            why.push(format!("ACE 형식 손상 ({ace})"));
            continue;
        }
        if f[0] != "A" {
            why.push(format!("허용 아닌 ACE ({ace})"));
        } else if !(f[2] == "FA" || f[2].eq_ignore_ascii_case("0x1f01ff")) {
            why.push(format!("권한 FA 아님 ({ace})"));
        }
        *seen.entry(f[5].to_string()).or_default() += 1;
        who.insert(f[5].to_string());
    }
    for (sid, n) in &seen {
        if *n > 1 {
            why.push(format!("추가 ACE — 같은 주체 {sid} 가 {n}번"));
        }
    }
    let want: std::collections::BTreeSet<String> = [String::from("SY"), me.to_string()].into_iter().collect();
    if who != want {
        why.push(format!("주체 집합 {who:?} ≠ {{SY, 나={me}}}"));
    }
    // 판정 = 1.1.10 과 같게(추가 ACE 는 권한·집합이 맞으면 사유가 아니다 — 같은 주체 FA 중복은 종전에도 통과).
    let fatal = why.iter().any(|w| !w.starts_with("추가 ACE"));
    if fatal {
        Err(why)
    } else {
        Ok(())
    }
}

/// SDDL 구조 대조(순수 · 참/거짓) = [`sddl_check`] 통과.
pub fn sddl_exactly(sddl: &str, me: &str) -> bool {
    sddl_check(sddl, me).is_ok()
}

/// 정의 대조(순수) — 어긋난 칸을 전부 사유로.
pub fn def_check(got: &TaskDef, command: &Path, args: &[&str], me: &str, logon_trigger: bool) -> Result<(), Vec<String>> {
    let mut why = Vec::new();
    if got.command != command.to_string_lossy() {
        why.push(format!("Command 다름(읽음 {:?} · 기대 {:?})", got.command, command.to_string_lossy()));
    }
    if got.args != args.iter().map(|s| s.to_string()).collect::<Vec<_>>() {
        why.push(format!("Arguments 다름(읽음 {:?} · 기대 {args:?})", got.args));
    }
    if !got.user_id.eq_ignore_ascii_case(me) {
        why.push(format!("UserId 다름(읽음 {:?} · 기대 {me})", got.user_id));
    }
    if got.logon_type != "InteractiveToken" {
        why.push(format!("LogonType 다름(읽음 {:?})", got.logon_type));
    }
    if got.logon_trigger != logon_trigger {
        why.push(format!("로그온 트리거 {} (기대 {logon_trigger})", got.logon_trigger));
    }
    if why.is_empty() {
        Ok(())
    } else {
        Err(why)
    }
}

/// 대조(순수): 다시 읽은 정의·SDDL = 기대.
pub fn def_matches(got: &TaskDef, command: &Path, args: &[&str], me: &str, logon_trigger: bool) -> bool {
    def_check(got, command, args, me, logon_trigger).is_ok()
}

/// 재독 거부 — 사유(칸별)와 읽은 원문(증거). `read_error` = 읽기 자체가 실패(1.1.10 은 이것도 「불일치」로 뭉갰다).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Refusal {
    pub read_error: bool,
    pub reasons: Vec<String>,
    pub task_sddl: Option<String>,
    pub folder_sddl: Option<String>,
    pub xml: Option<String>,
}

impl Refusal {
    pub fn read(what: String) -> Refusal {
        Refusal { read_error: true, reasons: vec![format!("읽기 오류: {what}")], task_sddl: None, folder_sddl: None, xml: None }
    }

    /// 읽기 도중 실패해도 그때까지 읽은 원문은 증거로 남긴다(codex R1-02).
    pub fn with_read(mut self, xml: Option<&str>, task_sddl: Option<&str>, folder_sddl: Option<&str>) -> Refusal {
        self.xml = xml.map(str::to_string).or(self.xml);
        self.task_sddl = task_sddl.map(str::to_string).or(self.task_sddl);
        self.folder_sddl = folder_sddl.map(str::to_string).or(self.folder_sddl);
        self
    }

    /// 한 줄 사유(오류 문자열 · 잡 기록에 실린다).
    pub fn summary(&self) -> String {
        self.reasons.join(" · ")
    }

    /// 증거 파일 본문(지우기 전에 남김).
    pub fn evidence(&self, task: &str, at: i64) -> serde_json::Value {
        serde_json::json!({
            "task": task, "at": at, "read_error": self.read_error, "reasons": self.reasons,
            "task_sddl": self.task_sddl, "folder_sddl": self.folder_sddl, "xml": self.xml,
        })
    }
}

/// 재독 판정(순수 · 모든 기판에서 시험): 다시 읽은 XML·작업 SDDL·폴더 SDDL → 통과 또는 칸별 사유 + 원문.
pub fn judge(xml: &str, task_sddl: &str, folder_sddl: &str, command: &Path, args: &[&str], me: &str, logon_trigger: bool) -> Result<(), Refusal> {
    let mut reasons = Vec::new();
    match parse_task_xml(xml) {
        Some(def) => {
            if let Err(w) = def_check(&def, command, args, me, logon_trigger) {
                reasons.extend(w);
            }
        }
        None => reasons.push("작업 XML 해석 불가(Principals·Command·UserId 태그 없음)".into()),
    }
    if let Err(w) = sddl_check(task_sddl, me) {
        reasons.extend(w.into_iter().map(|x| format!("작업 SDDL: {x}")));
    }
    if let Err(w) = sddl_check(folder_sddl, me) {
        reasons.extend(w.into_iter().map(|x| format!("폴더 SDDL: {x}")));
    }
    if reasons.is_empty() {
        Ok(())
    } else {
        Err(Refusal {
            read_error: false,
            reasons,
            task_sddl: Some(task_sddl.to_string()),
            folder_sddl: Some(folder_sddl.to_string()),
            xml: Some(xml.to_string()),
        })
    }
}

/// 거부 증거 파일 경로(갱신 폴더 · 작업마다 마지막 1건).
pub fn refusal_evidence_path(update_dir: &Path, task: &str) -> std::path::PathBuf {
    update_dir.join(format!("win-task-refusal-{task}.json"))
}

/// 러너 일회 작업 등록 → 다시 읽어 대조 → 실행(즉시 반환).
pub fn run_once(update_dir: &Path, runner: &Path, args: &[&str]) -> Result<(), String> {
    #[cfg(windows)]
    {
        com::register_and_verify(update_dir, RUNNER_TASK, runner, args, false, true)
    }
    #[cfg(not(windows))]
    {
        let _ = (update_dir, runner, args);
        Err("윈 전용".into())
    }
}

/// 러너가 끝날 때 자기 작업을 지운다(best-effort).
pub fn delete_runner_task(update_dir: &Path) {
    #[cfg(windows)]
    {
        let _ = com::delete(update_dir, RUNNER_TASK);
    }
    #[cfg(not(windows))]
    let _ = update_dir;
}

pub fn register_recover_task(update_dir: &Path, runner: &Path) -> Result<(), String> {
    #[cfg(windows)]
    {
        com::register_and_verify(update_dir, RECOVER_TASK, runner, &["self-update", "--recover"], true, false)
    }
    #[cfg(not(windows))]
    {
        let _ = (update_dir, runner);
        Err("윈 전용".into())
    }
}

/// N14(윈): 복구기 로그온 작업 정의 재독 대조.
pub fn recover_task_ok(update_dir: &Path, runner: &Path) -> Option<bool> {
    #[cfg(windows)]
    {
        com::verify(update_dir, RECOVER_TASK, runner, &["self-update", "--recover"], true)
    }
    #[cfg(not(windows))]
    {
        let _ = (update_dir, runner);
        None
    }
}

#[cfg(windows)]
mod com {
    use super::*;
    use std::ffi::c_void;
    use windows_sys::core::{BSTR, GUID, HRESULT};
    use windows_sys::Win32::Foundation::{SysAllocString, SysFreeString};
    use windows_sys::Win32::System::Com::{CoCreateInstance, CoInitializeEx, CLSCTX_INPROC_SERVER, COINIT_MULTITHREADED};
    use windows_sys::Win32::System::Variant::{VARIANT, VT_BSTR, VT_EMPTY};

    const CLSID_TASK_SCHEDULER: GUID = GUID::from_u128(0x0f87369f_a4e5_4cfc_bd3e_73e6154572dd);
    const IID_ITASK_SERVICE: GUID = GUID::from_u128(0x2faba4c7_4da9_4013_9697_20cc3fd40f85);
    const TASK_LOGON_INTERACTIVE_TOKEN: i32 = 3;
    const SI_OWNER_DACL: i32 = 0x1 | 0x4;

    type Raw = *mut c_void;

    /// vtable 칸 하나를 꺼낸다(IUnknown 3 + IDispatch 4 = 7 부터 인터페이스 고유 메서드).
    unsafe fn slot(obj: Raw, idx: usize) -> *const c_void {
        let vt = *(obj as *const *const *const c_void);
        *vt.add(idx)
    }

    unsafe fn release(obj: Raw) {
        if !obj.is_null() {
            let f: extern "system" fn(Raw) -> u32 = std::mem::transmute(slot(obj, 2));
            f(obj);
        }
    }

    struct Bstr(BSTR);
    impl Bstr {
        fn new(s: &str) -> Bstr {
            let w: Vec<u16> = s.encode_utf16().chain(std::iter::once(0)).collect();
            // SAFETY: NUL 종단 와이드 문자열.
            Bstr(unsafe { SysAllocString(w.as_ptr()) })
        }
    }
    impl Drop for Bstr {
        fn drop(&mut self) {
            // SAFETY: SysAllocString 이 준 값(또는 null).
            unsafe { SysFreeString(self.0) }
        }
    }

    fn take_bstr(b: BSTR) -> String {
        if b.is_null() {
            return String::new();
        }
        // SAFETY: COM 이 돌려준 BSTR · 길이 앞머리 4바이트.
        let s = unsafe {
            let len = *(b as *const u32).sub(1) as usize / 2;
            String::from_utf16_lossy(std::slice::from_raw_parts(b, len))
        };
        // SAFETY: 호출자 소유 BSTR 해제.
        unsafe { SysFreeString(b) };
        s
    }

    fn empty() -> VARIANT {
        // SAFETY: VT_EMPTY = 모든 칸 0.
        let mut v: VARIANT = unsafe { std::mem::zeroed() };
        v.Anonymous.Anonymous.vt = VT_EMPTY;
        v
    }

    fn vbstr(b: &Bstr) -> VARIANT {
        let mut v = empty();
        v.Anonymous.Anonymous.vt = VT_BSTR;
        v.Anonymous.Anonymous.Anonymous.bstrVal = b.0;
        v
    }

    fn hr(h: HRESULT, what: &str) -> Result<(), String> {
        if h < 0 {
            Err(format!("{what} hr=0x{:08x}", h as u32))
        } else {
            Ok(())
        }
    }

    struct Com(Raw);
    impl Drop for Com {
        fn drop(&mut self) {
            // SAFETY: AddRef 된 인터페이스 포인터.
            unsafe { release(self.0) }
        }
    }

    fn service() -> Result<Com, String> {
        // SAFETY: COM 초기화(이미 됐으면 S_FALSE/RPC_E_CHANGED_MODE — 무시).
        unsafe { CoInitializeEx(std::ptr::null(), COINIT_MULTITHREADED as u32) };
        let mut p: Raw = std::ptr::null_mut();
        // SAFETY: 잘 알려진 CLSID/IID · 출력 포인터.
        hr(unsafe { CoCreateInstance(&CLSID_TASK_SCHEDULER, std::ptr::null_mut(), CLSCTX_INPROC_SERVER, &IID_ITASK_SERVICE, &mut p) }, "CoCreateInstance")?;
        let svc = Com(p);
        // ITaskService::Connect = 10
        let f: extern "system" fn(Raw, VARIANT, VARIANT, VARIANT, VARIANT) -> HRESULT = unsafe { std::mem::transmute(slot(svc.0, 10)) };
        hr(f(svc.0, empty(), empty(), empty(), empty()), "Connect")?;
        Ok(svc)
    }

    fn get_folder(svc: &Com, path: &str) -> Result<Com, String> {
        let b = Bstr::new(path);
        let mut p: Raw = std::ptr::null_mut();
        // ITaskService::GetFolder = 7
        let f: extern "system" fn(Raw, BSTR, *mut Raw) -> HRESULT = unsafe { std::mem::transmute(slot(svc.0, 7)) };
        hr(f(svc.0, b.0, &mut p), "GetFolder")?;
        Ok(Com(p))
    }

    fn create_folder(parent: &Com, name: &str, sddl: &str) -> Result<Com, String> {
        let b = Bstr::new(name);
        let s = Bstr::new(sddl);
        let mut p: Raw = std::ptr::null_mut();
        // ITaskFolder::CreateFolder = 11
        let f: extern "system" fn(Raw, BSTR, VARIANT, *mut Raw) -> HRESULT = unsafe { std::mem::transmute(slot(parent.0, 11)) };
        hr(f(parent.0, b.0, vbstr(&s), &mut p), "CreateFolder")?;
        Ok(Com(p))
    }

    fn folder_sddl(folder: &Com) -> Result<String, String> {
        let mut out: BSTR = std::ptr::null_mut();
        // ITaskFolder::GetSecurityDescriptor = 18
        let f: extern "system" fn(Raw, i32, *mut BSTR) -> HRESULT = unsafe { std::mem::transmute(slot(folder.0, 18)) };
        hr(f(folder.0, SI_OWNER_DACL, &mut out), "Folder.GetSecurityDescriptor")?;
        Ok(take_bstr(out))
    }

    fn get_task(folder: &Com, name: &str) -> Result<Com, String> {
        let b = Bstr::new(name);
        let mut p: Raw = std::ptr::null_mut();
        // ITaskFolder::GetTask = 13
        let f: extern "system" fn(Raw, BSTR, *mut Raw) -> HRESULT = unsafe { std::mem::transmute(slot(folder.0, 13)) };
        hr(f(folder.0, b.0, &mut p), "GetTask")?;
        Ok(Com(p))
    }

    fn read_task_xml(task: &Com) -> Result<String, String> {
        let mut x: BSTR = std::ptr::null_mut();
        // IRegisteredTask::get_Xml = 20
        let gx: extern "system" fn(Raw, *mut BSTR) -> HRESULT = unsafe { std::mem::transmute(slot(task.0, 20)) };
        hr(gx(task.0, &mut x), "get_Xml")?;
        Ok(take_bstr(x))
    }

    fn read_task_sddl(task: &Com) -> Result<String, String> {
        let mut s: BSTR = std::ptr::null_mut();
        // IRegisteredTask::GetSecurityDescriptor = 21
        let gs: extern "system" fn(Raw, i32, *mut BSTR) -> HRESULT = unsafe { std::mem::transmute(slot(task.0, 21)) };
        hr(gs(task.0, SI_OWNER_DACL, &mut s), "Task.GetSecurityDescriptor")?;
        Ok(take_bstr(s))
    }

    /// ★2판(윈 CI): 갱신 폴더는 호출자가 준다 — 여기서 `state_dir()` 을 다시 구하지 않는다(시험 격리 봉인 · `--check` 가 넘긴 폴더와
    /// 같은 install_id). 읽기(`create` 거짓)는 install_id 를 만들지 않는다.
    fn our_folder(dir: &Path, svc: &Com, create: bool, sddl: &str) -> Result<Com, String> {
        let id = if create {
            crate::update::buildinfo::ensure_install_id(dir)?
        } else {
            crate::update::buildinfo::read_install_id(dir).ok_or("install_id 없음")?
        };
        let path = format!("\\{FOLDER_ROOT}\\{id}");
        if let Ok(f) = get_folder(svc, &path) {
            return Ok(f);
        }
        if !create {
            return Err("작업 폴더 없음".into());
        }
        let root = get_folder(svc, "\\")?;
        let top = match get_folder(svc, &format!("\\{FOLDER_ROOT}")) {
            Ok(f) => f,
            Err(_) => create_folder(&root, FOLDER_ROOT, sddl)?,
        };
        create_folder(&top, &id, sddl)
    }

    /// 재독 대조(★1.1.11): 읽기 오류와 불일치를 가르고 칸별 사유·원문을 돌려준다.
    pub fn verify_detail(dir: &Path, name: &str, runner: &Path, args: &[&str], logon: bool) -> Result<(), Refusal> {
        let me = crate::update::current_user_sid_pub().map_err(Refusal::read)?;
        let svc = service().map_err(Refusal::read)?;
        let folder = our_folder(dir, &svc, false, "").map_err(Refusal::read)?;
        let task = get_task(&folder, name).map_err(Refusal::read)?;
        let xml = read_task_xml(&task).map_err(Refusal::read)?;
        let sddl = read_task_sddl(&task).map_err(|e| Refusal::read(e).with_read(Some(&xml), None, None))?;
        let fsddl = folder_sddl(&folder).map_err(|e| Refusal::read(e).with_read(Some(&xml), Some(&sddl), None))?;
        judge(&xml, &sddl, &fsddl, runner, args, &me, logon)
    }

    /// N14 용: 통과 = Some(true) · 불일치 = Some(false) · 읽기 오류 = None. 종전과 같은 것은 반환형과 N14 최종 불리언
    /// (`recover_task_ok` → `unwrap_or(false)`)이다 — Option 값은 두 경우가 바뀌었다(XML 해석 불가 None → Some(false) ·
    /// 폴더 SDDL 읽기 오류 Some(false) → None · 둘 다 N14 = 보류 그대로 · codex R1-03).
    pub fn verify(dir: &Path, name: &str, runner: &Path, args: &[&str], logon: bool) -> Option<bool> {
        match verify_detail(dir, name, runner, args, logon) {
            Ok(()) => Some(true),
            Err(r) if r.read_error => None,
            Err(_) => Some(false),
        }
    }

    pub fn delete(dir: &Path, name: &str) -> Result<(), String> {
        let svc = service()?;
        let folder = our_folder(dir, &svc, false, "")?;
        let b = Bstr::new(name);
        // ITaskFolder::DeleteTask = 15
        let f: extern "system" fn(Raw, BSTR, i32) -> HRESULT = unsafe { std::mem::transmute(slot(folder.0, 15)) };
        hr(f(folder.0, b.0, 0), "DeleteTask")
    }

    pub fn register_and_verify(dir: &Path, name: &str, runner: &Path, args: &[&str], logon: bool, run_now: bool) -> Result<(), String> {
        let me = crate::update::current_user_sid_pub()?;
        let sddl = sddl_for(&me);
        let svc = service()?;
        let folder = our_folder(dir, &svc, true, &sddl)?;
        let xml = task_xml(runner, args, &me, logon);
        let (bn, bx, bs) = (Bstr::new(name), Bstr::new(&xml), Bstr::new(&sddl));
        // ★codex R1-01: 같은 이름의 옛 작업이 있으면 먼저 지운다 — 갱신(TASK_UPDATE)에선 0x10 이 「옛 주체 ACE 를 지우지 않는다」
        //   (MS 문서)라 1.1.10 이 남긴 FR ACE 가 살아남을 수 있다. 새로 만들기만 하면 실측(0x16 = D:PAI 그대로)과 같은 경로다.
        //   없는 작업 지우기 실패는 무시(정상).
        let _ = delete(dir, name);
        let mut p: Raw = std::ptr::null_mut();
        // ITaskFolder::RegisterTask = 16
        let f: extern "system" fn(Raw, BSTR, BSTR, i32, VARIANT, VARIANT, i32, VARIANT, *mut Raw) -> HRESULT =
            unsafe { std::mem::transmute(slot(folder.0, 16)) };
        hr(f(folder.0, bn.0, bx.0, register_flags(), empty(), empty(), TASK_LOGON_INTERACTIVE_TOKEN, vbstr(&bs), &mut p), "RegisterTask")?;
        let task = Com(p);
        if let Err(r) = verify_detail(dir, name, runner, args, logon) {
            // 증거 먼저(지우면 사라진다) — 기록 실패는 거부 사유에 덧붙일 뿐 거부 자체를 바꾸지 않는다.
            let ev = refusal_evidence_path(dir, name);
            let wrote = crate::update::write_private(&ev, r.evidence(name, crate::update::clock::wall_now()).to_string().as_bytes());
            let _ = delete(dir, name);
            let note = match wrote {
                Ok(()) => format!(" · 증거 {}", ev.display()),
                Err(e) => format!(" · 증거 기록 실패 {e}"),
            };
            return Err(format!("update.win_task_refused: 다시 읽은 정의·SDDL 불일치 [{name}] {}{note}", r.summary()));
        }
        if run_now {
            let mut rt: Raw = std::ptr::null_mut();
            // IRegisteredTask::Run = 12
            let run: extern "system" fn(Raw, VARIANT, *mut Raw) -> HRESULT = unsafe { std::mem::transmute(slot(task.0, 12)) };
            hr(run(task.0, empty(), &mut rt), "Run")?;
            // SAFETY: Run 이 준 IRunningTask.
            unsafe { release(rt) };
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// §7-1 「작업 정의 재독 구조 대조(인자 공백·따옴표·역슬래시 사례)」.
    #[test]
    fn args_roundtrip_through_windows_rules() {
        let cases: Vec<Vec<&str>> = vec![
            vec!["self-update", "--run"],
            vec![r"C:\Program Files\x", "a b", ""],
            vec![r#"he said "hi""#, r"trailing\", r"C:\dir\\"],
            vec![r#"\\""#, "tab\there", r"a\\b\c"],
        ];
        for c in cases {
            let s = join_args(&c);
            assert_eq!(parse_args(&s), c.iter().map(|x| x.to_string()).collect::<Vec<_>>(), "{s}");
        }
        // 손으로 쓴 MS 문서 예(CommandLineToArgvW): `a\\\"b` = a\"b · `"ab\"c"` = ab"c · `a\\\\"b c" d` = a\\b c , d
        assert_eq!(parse_args(r#"a\\\"b"#), vec![r#"a\"b"#]);
        assert_eq!(parse_args(r#""ab\"c""#), vec![r#"ab"c"#]);
        assert_eq!(parse_args(r#"a\\\\"b c" d"#), vec![r"a\\b c", "d"]);
    }

    #[test]
    fn xml_roundtrip_and_tamper_detection() {
        let me = "S-1-5-21-1-2-3-1001";
        let runner = Path::new(r"C:\x\a b\cys-update\runner\cys.exe");
        let x = task_xml(runner, &["self-update", "--recover"], me, true);
        let d = parse_task_xml(&x).unwrap();
        assert!(def_matches(&d, runner, &["self-update", "--recover"], me, true));
        assert!(!def_matches(&d, runner, &["self-update", "--run"], me, true), "인자 다름");
        assert!(!def_matches(&d, runner, &["self-update", "--recover"], "S-1-5-21-9", true), "주체 다름");
        let t = parse_task_xml(&x.replace("InteractiveToken", "Password")).unwrap();
        assert!(!def_matches(&t, runner, &["self-update", "--recover"], me, true), "로그온 형 다름");
        assert!(!def_matches(&parse_task_xml(&task_xml(runner, &["self-update", "--recover"], me, false)).unwrap(), runner, &["self-update", "--recover"], me, true));
    }

    #[test]
    fn sddl_structural_compare() {
        let me = "S-1-5-21-1-2-3-1001";
        assert!(sddl_exactly(&sddl_for(me), me));
        assert!(sddl_exactly(&format!("O:{me}G:{me}D:PAI(A;;FA;;;{me})(A;;FA;;;SY)"), me), "순서·소유자 칸 무관");
        assert!(!sddl_exactly(&format!("D:(A;;FA;;;SY)(A;;FA;;;{me})"), me), "상속 안 끊음");
        assert!(!sddl_exactly(&format!("D:P(A;;FA;;;SY)(A;;FA;;;{me})(A;;FR;;;BU)"), me), "다른 주체");
        assert!(!sddl_exactly(&format!("D:P(A;;FA;;;SY)(A;;GR;;;{me})"), me), "권한 다름");
    }

    // ★1.1.11 윈 실측 픽스처(TICKET=win-selfupdate-recover · probe-cysr-task.ps1 · 2026-10-27 07:53 · 윈 11 26200 ko-KR · 표준 사용자 ·
    // Microsoft 계정). SID·PC 이름만 가명화했고 그 밖 바이트는 스케줄러가 돌려준 원문 그대로다(정규화 XML 은 우리가 보낸 것과 칸 순서·
    // 들여쓰기·SecurityDescriptor 칸·로그온 트리거 UserId 꼴이 다르다). 실행 대상만 System32 whoami.exe(무해) — 인자·주체·트리거 = 복구기.
    const PROBE_ME: &str = "S-1-5-21-1-2-3-1001";
    /// 플래그 6(1.1.10) 으로 등록한 작업 SD — 보호 P 소실 + 주체 FR ACE 덧붙음.
    const PROBE_TASK_SDDL_F6: &str = "O:S-1-5-21-1-2-3-1001D:(A;;FA;;;SY)(A;;FA;;;S-1-5-21-1-2-3-1001)(A;;FR;;;S-1-5-21-1-2-3-1001)";
    /// 플래그 0x16(★1.1.11) — 우리 SDDL 그대로(D:PAI).
    const PROBE_TASK_SDDL_F16: &str = "O:S-1-5-21-1-2-3-1001D:PAI(A;;FA;;;SY)(A;;FA;;;S-1-5-21-1-2-3-1001)";
    /// 같은 기기 `\cysr\<install_id>` 폴더 SD(1.1.10 이 만든 것 · 통과).
    const PROBE_FOLDER_SDDL: &str = "O:S-1-5-21-1-2-3-1001D:PAI(A;;FA;;;SY)(A;;FA;;;S-1-5-21-1-2-3-1001)";
    const PROBE_XML_F6: &str = r#"<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <SecurityDescriptor>D:P(A;;FA;;;SY)(A;;FA;;;S-1-5-21-1-2-3-1001)</SecurityDescriptor>
    <Description>cysr auto-update</Description>
    <URI>\cysr-probe\54e15ddeb8d020f56fae3b6e82b7c55d\recover-f6</URI>
  </RegistrationInfo>
  <Principals>
    <Principal id="Author">
      <UserId>S-1-5-21-1-2-3-1001</UserId>
      <LogonType>InteractiveToken</LogonType>
    </Principal>
  </Principals>
  <Settings>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <ExecutionTimeLimit>PT2H</ExecutionTimeLimit>
    <Hidden>true</Hidden>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <IdleSettings>
      <StopOnIdleEnd>true</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
  </Settings>
  <Triggers>
    <LogonTrigger>
      <UserId>DESKTOP-TEST\user</UserId>
    </LogonTrigger>
  </Triggers>
  <Actions Context="Author">
    <Exec>
      <Command>C:\WINDOWS\System32\whoami.exe</Command>
      <Arguments>self-update --recover</Arguments>
    </Exec>
  </Actions>
</Task>"#;
    const PROBE_XML_F16: &str = r#"<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <SecurityDescriptor>D:P(A;;FA;;;SY)(A;;FA;;;S-1-5-21-1-2-3-1001)</SecurityDescriptor>
    <Description>cysr auto-update</Description>
    <URI>\cysr-probe\54e15ddeb8d020f56fae3b6e82b7c55d\recover-f16</URI>
  </RegistrationInfo>
  <Principals>
    <Principal id="Author">
      <UserId>S-1-5-21-1-2-3-1001</UserId>
      <LogonType>InteractiveToken</LogonType>
    </Principal>
  </Principals>
  <Settings>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <ExecutionTimeLimit>PT2H</ExecutionTimeLimit>
    <Hidden>true</Hidden>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <IdleSettings>
      <StopOnIdleEnd>true</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
  </Settings>
  <Triggers>
    <LogonTrigger>
      <UserId>DESKTOP-TEST\user</UserId>
    </LogonTrigger>
  </Triggers>
  <Actions Context="Author">
    <Exec>
      <Command>C:\WINDOWS\System32\whoami.exe</Command>
      <Arguments>self-update --recover</Arguments>
    </Exec>
  </Actions>
</Task>"#;
    const PROBE_CMD: &str = r"C:\WINDOWS\System32\whoami.exe";
    const RECOVER_ARGS: [&str; 2] = ["self-update", "--recover"];

    #[test]
    fn probe_flag6_readback_is_refused_with_field_reasons() {
        let r = judge(PROBE_XML_F6, PROBE_TASK_SDDL_F6, PROBE_FOLDER_SDDL, Path::new(PROBE_CMD), &RECOVER_ARGS, PROBE_ME, true).unwrap_err();
        assert!(!r.read_error, "읽기 오류가 아니라 불일치");
        let has = |s: &str| r.reasons.iter().any(|w| w == s);
        assert!(has("작업 SDDL: 보호(P) 없음 — 상속 열림(DACL 표지 \"\")"), "{:?}", r.reasons);
        assert!(has(&format!("작업 SDDL: 권한 FA 아님 (A;;FR;;;{PROBE_ME})")), "{:?}", r.reasons);
        assert!(has(&format!("작업 SDDL: 추가 ACE — 같은 주체 {PROBE_ME} 가 2번")), "{:?}", r.reasons);
        assert!(r.reasons.iter().all(|w| w.starts_with("작업 SDDL:")), "정의·폴더는 맞다(K3·K4 아님): {:?}", r.reasons);
        assert_eq!(r.task_sddl.as_deref(), Some(PROBE_TASK_SDDL_F6), "증거 = 읽은 원문");
        let ev = r.evidence("recover", 1);
        assert_eq!(ev["task_sddl"], PROBE_TASK_SDDL_F6);
        assert_eq!(ev["xml"], PROBE_XML_F6);
        assert_eq!(ev["read_error"], false);
    }

    #[test]
    fn probe_flag16_readback_passes() {
        assert_eq!(judge(PROBE_XML_F16, PROBE_TASK_SDDL_F16, PROBE_FOLDER_SDDL, Path::new(PROBE_CMD), &RECOVER_ARGS, PROBE_ME, true), Ok(()));
        // 플래그 6 의 정규화 XML 도 정의 칸은 맞았다 — 거부는 오직 작업 SD 때문이었다.
        assert!(def_matches(&parse_task_xml(PROBE_XML_F6).unwrap(), Path::new(PROBE_CMD), &RECOVER_ARGS, PROBE_ME, true));
        assert!(!sddl_exactly(PROBE_TASK_SDDL_F6, PROBE_ME));
    }

    /// 뮤턴트 WT1(= 1.1.10 의 플래그 6) 이면 적.
    #[test]
    fn register_flags_pin_dont_add_principal_ace() {
        assert_eq!(TASK_CREATE_OR_UPDATE, 0x6);
        assert_eq!(TASK_DONT_ADD_PRINCIPAL_ACE, 0x10);
        assert_eq!(register_flags(), 0x16);
        assert_ne!(register_flags() & TASK_DONT_ADD_PRINCIPAL_ACE, 0, "0x10 없으면 스케줄러가 주체 ACE 를 붙여 재독 거부(윈 실측)");
    }

    #[test]
    fn read_error_is_not_a_mismatch_and_every_field_reason_is_reported() {
        let r = Refusal::read("GetTask hr=0x80070002".into());
        assert!(r.read_error);
        assert_eq!(r.summary(), "읽기 오류: GetTask hr=0x80070002");
        // 정의 칸이 여럿 어긋나면 전부 나온다(첫 칸에서 멈추지 않음).
        let me = "S-1-5-21-1-2-3-1001";
        let x = task_xml(Path::new(r"C:\y\cys.exe"), &["self-update", "--run"], "S-1-5-21-9", false);
        let w = def_check(&parse_task_xml(&x).unwrap(), Path::new(r"C:\x\cys.exe"), &RECOVER_ARGS, me, true).unwrap_err();
        assert_eq!(w.len(), 4, "{w:?}");
        assert!(w[0].starts_with("Command 다름") && w[1].starts_with("Arguments 다름") && w[2].starts_with("UserId 다름") && w[3].starts_with("로그온 트리거"));
        // 판정 = 1.1.10 과 같다: 같은 주체 FA 중복은 통과 · DACL 없음은 거부.
        assert!(sddl_exactly(&format!("D:P(A;;FA;;;SY)(A;;FA;;;{me})(A;;FA;;;{me})"), me));
        assert_eq!(sddl_check("O:SYG:SY", me), Err(vec!["DACL(D:) 없음".to_string()]));
        // codex R1-02: 읽기 도중 실패해도 앞서 읽은 원문이 증거로 남는다.
        let p = Refusal::read("Folder.GetSecurityDescriptor hr=0x80070005".into()).with_read(Some("<Task/>"), Some("D:P(A;;FA;;;SY)"), None);
        assert!(p.read_error);
        assert_eq!((p.xml.as_deref(), p.task_sddl.as_deref(), p.folder_sddl.as_deref()), (Some("<Task/>"), Some("D:P(A;;FA;;;SY)"), None));
        assert_eq!(p.evidence("recover", 1)["xml"], "<Task/>");
    }

    /// codex R1-04: 핀이 함수만 보지 않게 — 실제 RegisterTask 호출 인자가 `register_flags()` 이고, 등록 전에 옛 작업을 지운다
    /// (소스 핀 · 윈 전용 com 모듈은 맥에서 실행되지 않으므로 글자로 묶는다).
    #[test]
    fn com_register_call_uses_register_flags_and_deletes_first() {
        let src = include_str!("win_task.rs");
        let com = &src[src.find("mod com {").unwrap()..src.find("mod tests {").unwrap()];
        let reg = com.find("TASK_CREATE_OR_UPDATE, empty()").map(|_| ()).is_none();
        assert!(reg, "RegisterTask 에 상수 6 직접 전달 금지");
        let call = com.find("hr(f(folder.0, bn.0, bx.0, register_flags(), empty(), empty(), TASK_LOGON_INTERACTIVE_TOKEN").expect("RegisterTask 인자 = register_flags()");
        let del = com.find("let _ = delete(dir, name);\n        let mut p: Raw").expect("등록 직전 옛 작업 지우기");
        assert!(del < call, "지우기가 등록보다 먼저");
    }
}
