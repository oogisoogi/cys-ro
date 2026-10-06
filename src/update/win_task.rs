//! 윈 작업 스케줄러 — 러너 일회 작업 · 복구기 로그온 작업(설계 AUTO-UPDATE-118 §3-1 · 1R MAJOR 8 · 2R MAJOR 4 · §3-11 · N14 · P4).
//!
//! - `schtasks.exe`·`cmd /c` 0 — **작업 스케줄러 COM**(`ITaskService`)으로 등록한다. windows-sys 0.59 에는 작업 스케줄러 인터페이스가
//!   없어서 vtable 을 직접 선언한다(taskschd.h 순서 · IDispatch 7칸 뒤). 정의는 XML 한 장(`RegisterTask`)으로 넣는다.
//! - 폴더 `\cysr\<install_id>` · 폴더와 작업에 명시 SDDL `D:P(A;;FA;;;SY)(A;;FA;;;<현재 사용자 SID>)`(상속 끊음).
//! - 등록 뒤 **COM 으로 정의를 다시 읽어** ① `Command` 경로 ② `Arguments` 를 윈 명령줄 규칙으로 되파싱한 배열 = 우리가 쓴 배열
//!   ③ 주체 SID · 로그온 형 ④ 폴더·작업 SDDL 을 **구조적으로** 대조한다(문자열 비교 아님) — 다르면 삭제 · `update.win_task_refused`.
//! - 사용자 권한으로 작업 생성이 되는지 = 【미확인 → W1 ⑤】(안 되면 설치기 변경 = 비가역 · master).
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

/// SDDL 구조 대조(순수): DACL 보호(P) · 허용 ACE 주체 집합 = {SY, 나} · 거부·그 밖 ACE 0 · 권한 = FA(또는 같은 값의 16진).
pub fn sddl_exactly(sddl: &str, me: &str) -> bool {
    let Some(d) = sddl.find("D:") else { return false };
    let dacl = sddl[d + 2..].split("S:").next().unwrap_or("");
    let flags_end = dacl.find('(').unwrap_or(dacl.len());
    if !dacl[..flags_end].contains('P') {
        return false;
    }
    let mut who = std::collections::BTreeSet::new();
    for ace in dacl[flags_end..].split(['(', ')']).filter(|x| !x.is_empty()) {
        let f: Vec<&str> = ace.split(';').collect();
        if f.len() != 6 || f[0] != "A" || !(f[2] == "FA" || f[2].eq_ignore_ascii_case("0x1f01ff")) {
            return false;
        }
        who.insert(f[5].to_string());
    }
    who == [String::from("SY"), me.to_string()].into_iter().collect()
}

/// 대조(순수): 다시 읽은 정의·SDDL = 기대.
pub fn def_matches(got: &TaskDef, command: &Path, args: &[&str], me: &str, logon_trigger: bool) -> bool {
    got.command == command.to_string_lossy()
        && got.args == args.iter().map(|s| s.to_string()).collect::<Vec<_>>()
        && got.user_id.eq_ignore_ascii_case(me)
        && got.logon_type == "InteractiveToken"
        && got.logon_trigger == logon_trigger
}

/// 러너 일회 작업 등록 → 다시 읽어 대조 → 실행(즉시 반환).
pub fn run_once(runner: &Path, args: &[&str]) -> Result<(), String> {
    #[cfg(windows)]
    {
        com::register_and_verify(RUNNER_TASK, runner, args, false, true)
    }
    #[cfg(not(windows))]
    {
        let _ = (runner, args);
        Err("윈 전용".into())
    }
}

/// 러너가 끝날 때 자기 작업을 지운다(best-effort).
pub fn delete_runner_task() {
    #[cfg(windows)]
    {
        let _ = com::delete(RUNNER_TASK);
    }
}

pub fn register_recover_task(runner: &Path) -> Result<(), String> {
    #[cfg(windows)]
    {
        com::register_and_verify(RECOVER_TASK, runner, &["self-update", "--recover"], true, false)
    }
    #[cfg(not(windows))]
    {
        let _ = runner;
        Err("윈 전용".into())
    }
}

/// N14(윈): 복구기 로그온 작업 정의 재독 대조.
pub fn recover_task_ok(runner: &Path) -> Option<bool> {
    #[cfg(windows)]
    {
        com::verify(RECOVER_TASK, runner, &["self-update", "--recover"], true)
    }
    #[cfg(not(windows))]
    {
        let _ = runner;
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
    const TASK_CREATE_OR_UPDATE: i32 = 6;
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

    fn task_xml_sddl(task: &Com) -> Result<(String, String), String> {
        let mut x: BSTR = std::ptr::null_mut();
        // IRegisteredTask::get_Xml = 20 · GetSecurityDescriptor = 21
        let gx: extern "system" fn(Raw, *mut BSTR) -> HRESULT = unsafe { std::mem::transmute(slot(task.0, 20)) };
        hr(gx(task.0, &mut x), "get_Xml")?;
        let xml = take_bstr(x);
        let mut s: BSTR = std::ptr::null_mut();
        let gs: extern "system" fn(Raw, i32, *mut BSTR) -> HRESULT = unsafe { std::mem::transmute(slot(task.0, 21)) };
        hr(gs(task.0, SI_OWNER_DACL, &mut s), "Task.GetSecurityDescriptor")?;
        Ok((xml, take_bstr(s)))
    }

    fn our_folder(svc: &Com, create: bool, sddl: &str) -> Result<Com, String> {
        let dir = crate::update::buildinfo::state_dir()?;
        let id = crate::update::buildinfo::ensure_install_id(&dir)?;
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

    pub fn verify(name: &str, runner: &Path, args: &[&str], logon: bool) -> Option<bool> {
        let me = crate::update::current_user_sid_pub().ok()?;
        let svc = service().ok()?;
        let folder = our_folder(&svc, false, "").ok()?;
        let task = get_task(&folder, name).ok()?;
        let (xml, sddl) = task_xml_sddl(&task).ok()?;
        let def = parse_task_xml(&xml)?;
        Some(def_matches(&def, runner, args, &me, logon) && sddl_exactly(&sddl, &me) && folder_sddl(&folder).map(|s| sddl_exactly(&s, &me)).unwrap_or(false))
    }

    pub fn delete(name: &str) -> Result<(), String> {
        let svc = service()?;
        let folder = our_folder(&svc, false, "")?;
        let b = Bstr::new(name);
        // ITaskFolder::DeleteTask = 15
        let f: extern "system" fn(Raw, BSTR, i32) -> HRESULT = unsafe { std::mem::transmute(slot(folder.0, 15)) };
        hr(f(folder.0, b.0, 0), "DeleteTask")
    }

    pub fn register_and_verify(name: &str, runner: &Path, args: &[&str], logon: bool, run_now: bool) -> Result<(), String> {
        let me = crate::update::current_user_sid_pub()?;
        let sddl = sddl_for(&me);
        let svc = service()?;
        let folder = our_folder(&svc, true, &sddl)?;
        let xml = task_xml(runner, args, &me, logon);
        let (bn, bx, bs) = (Bstr::new(name), Bstr::new(&xml), Bstr::new(&sddl));
        let mut p: Raw = std::ptr::null_mut();
        // ITaskFolder::RegisterTask = 16
        let f: extern "system" fn(Raw, BSTR, BSTR, i32, VARIANT, VARIANT, i32, VARIANT, *mut Raw) -> HRESULT =
            unsafe { std::mem::transmute(slot(folder.0, 16)) };
        hr(f(folder.0, bn.0, bx.0, TASK_CREATE_OR_UPDATE, empty(), empty(), TASK_LOGON_INTERACTIVE_TOKEN, vbstr(&bs), &mut p), "RegisterTask")?;
        let task = Com(p);
        if verify(name, runner, args, logon) != Some(true) {
            let _ = delete(name);
            return Err("update.win_task_refused: 다시 읽은 정의·SDDL 불일치".into());
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
        let runner = Path::new(r"C:\Users\a b\AppData\Local\cys-update\runner\cys.exe");
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
}
