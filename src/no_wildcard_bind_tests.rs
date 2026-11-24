//! TICKET=fw-popup-1124 — 「시험·도구가 모든 인터페이스(0.0.0.0 · :: · 빈 주소)로 듣지 않는다」 원천 검사(테스트 전용 · 프로덕션 코드 0행).
//!
//! 왜 있는가: 맥 방화벽은 들어오는 흐름이 생기면 그 소켓의 **책임 앱**(좌석 안 자식이면 cysd) 이름으로
//! 「'cysd' 응용 프로그램이 들어오는 네트워크 연결을 허용하도록 하겠습니까?」를 묻는다(2026-11-24 14:52:00
//! 방화벽 기록 `Enqueuing new inbound flow for cysd` → `Prompting`). 루프백(127.0.0.1)에만 묶인 소켓은
//! 바깥 흐름을 받을 수 없어 묻지 않는다 — 같은 날 cysd 가지 아래 127.0.0.1 시험 서버 수백 회 중 흐름 기록 0.
//! 그래서 우리 저장소의 시험·도구·문서 처방은 **루프백에만 묶는다**. 이 핀은 그 규칙이 무너지는 자리
//! (바인드 미지정 `python -m http.server` · `--host 0.0.0.0` · `bind(("", …))` · Rust `bind("0.0.0.0:…")`)를
//! 소스에서 찾아 적색으로 만든다.
//!
//! 범위: 실행되는 코드와 사용자 대면 처방(README) — `docs/`·`review/`(기록·증거 보관)는 뺀다.
//! 대가 고지: 이 시험은 저장소 파일을 **런타임에 읽는다** — 일부러 모든 인터페이스로 들어야 하는 자리가
//! 생기면(예: VM 이 호스트에서 받아 가기) 그 줄에 `wildcard-bind-ok: <이유>` 를 적어 면제한다.
//! 면제 표식 없는 적색 = 「127.0.0.1(또는 `--bind 127.0.0.1`)로 묶어라」.
//! `[전제]`(읽기 실패·검사 대상 0) 적색은 판별력의 증명이 아니다 — 판별력의 증거는 아래 반증 변이 시험이다.
use regex::Regex;
use std::path::{Path, PathBuf};

/// 훑는 뿌리(파일 또는 폴더) — 저장소 상대.
const ROOTS: &[&str] = &[
    "src",
    "src-tauri/src",
    "scripts",
    "ui/src",
    "ui/e2e",
    "update-worker",
    "cysjavis-pack/bin",
    "cysjavis-pack/hooks",
    "cysjavis-pack/skills",
    "README.md",
    "README.en.md",
];
const SKIP_DIRS: &[&str] = &["node_modules", "target", "fixtures", "vendor", ".git"];
const CODE_EXT: &[&str] = &["rs", "py", "sh", "ts", "js", "mjs", "cjs"];
const EXEMPT: &str = "wildcard-bind-ok:";
/// 이 파일 자신(규칙·반증 표본에 나쁜 꼴이 들어 있다).
const SELF: &str = "src/no_wildcard_bind_tests.rs";

fn root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).to_path_buf()
}

struct Rules {
    py_tuple: Regex,
    http_server: Regex,
    http_bind: Regex,
    flag: Regex,
    rs_bind: Regex,
    host_kw: Regex,
}

fn rules() -> Rules {
    Rules {
        // bind(("", p)) · HTTPServer(("0.0.0.0", p)) · serve((“::”, p)) — 빈 주소 = 모든 인터페이스.
        py_tuple: Regex::new(r#"(bind|Server|serve|listen)\(\(\s*["'](0\.0\.0\.0|::)?["']\s*,"#).unwrap(),
        // `-m http.server` 는 --bind 없이는 모든 인터페이스로 듣는다.
        http_server: Regex::new(r"-m\s+http\.server\b").unwrap(),
        http_bind: Regex::new(r"(--bind|\s-b)\s").unwrap(),
        flag: Regex::new(r#"(--host|--ip|--bind|--listen|\s-b)[ =]["']?(0\.0\.0\.0|::|\[::\])(\b|:|["'\s]|$)"#).unwrap(),
        rs_bind: Regex::new(r#"bind\(\s*"(0\.0\.0\.0|\[::\]|::)[:"]|Ipv[46]Addr::UNSPECIFIED"#).unwrap(),
        host_kw: Regex::new(r#"\bhost\s*[:=]\s*["'](0\.0\.0\.0|::)["']"#).unwrap(),
    }
}

/// 한 줄 판정 — `ext` 는 확장자(README 는 "md"). 위반이면 규칙 이름.
fn judge(r: &Rules, ext: &str, line: &str) -> Option<&'static str> {
    if line.contains(EXEMPT) {
        return None;
    }
    let t = line.trim_start();
    let comment = t.starts_with('#') || t.starts_with("//") || t.starts_with("/*") || t.starts_with('*');
    if ext == "rs" {
        // Rust = 소켓을 실제로 여는 꼴만(시험 데이터의 명령줄 문자열은 남의 프로세스를 흉내 낸 것).
        return if !comment && r.rs_bind.is_match(line) { Some("rust-bind-wildcard") } else { None };
    }
    if comment && ext != "md" {
        return None;
    }
    if r.http_server.is_match(line) && !r.http_bind.is_match(line) {
        return Some("http.server-without-bind");
    }
    if r.flag.is_match(line) {
        return Some("flag-wildcard");
    }
    if ext != "md" && r.py_tuple.is_match(line) {
        return Some("bind-empty-or-wildcard-tuple");
    }
    if ext != "md" && r.host_kw.is_match(line) {
        return Some("host-wildcard");
    }
    None
}

fn walk(p: &Path, out: &mut Vec<PathBuf>) {
    if p.is_file() {
        out.push(p.to_path_buf());
        return;
    }
    let Ok(rd) = std::fs::read_dir(p) else { return };
    for e in rd.flatten() {
        let q = e.path();
        let name = e.file_name().to_string_lossy().to_string();
        if q.is_dir() {
            if !SKIP_DIRS.contains(&name.as_str()) {
                walk(&q, out);
            }
        } else {
            out.push(q);
        }
    }
}

fn ext_of(rel: &str) -> Option<&'static str> {
    let base = rel.rsplit('/').next().unwrap_or(rel);
    if base == "README.md" || base == "README.en.md" {
        return Some("md");
    }
    let e = base.rsplit_once('.')?.1;
    CODE_EXT.iter().copied().find(|x| *x == e)
}

#[test]
fn no_wildcard_listen_in_tests_tools_and_readme() {
    let r = rules();
    let base = root();
    let mut files = Vec::new();
    for rt in ROOTS {
        let p = base.join(rt);
        assert!(p.exists(), "[전제] 뿌리 {rt} 가 없다 — 목록을 저장소에 맞춰 고쳐라(사라진 뿌리를 조용히 건너뛰지 않는다)");
        walk(&p, &mut files);
    }
    let mut scanned = 0usize;
    let mut bad = Vec::new();
    for f in &files {
        let rel = f.strip_prefix(&base).unwrap().to_string_lossy().replace('\\', "/");
        if rel == SELF {
            continue;
        }
        let Some(ext) = ext_of(&rel) else { continue };
        let Ok(text) = std::fs::read_to_string(f) else { continue }; // 비 UTF-8(이진) = 대상 아님
        scanned += 1;
        for (i, line) in text.lines().enumerate() {
            if let Some(rule) = judge(&r, ext, line) {
                bad.push(format!("{rel}:{} [{rule}] {}", i + 1, line.trim()));
            }
        }
    }
    assert!(scanned > 500, "[전제] 훑은 파일 {scanned}개 — 너무 적다(뿌리·확장자 목록 고장 의심)");
    assert!(
        bad.is_empty(),
        "[판별] 모든 인터페이스로 듣는 자리 {}곳 — 127.0.0.1(또는 `--bind 127.0.0.1` · `--ip 127.0.0.1`)로 묶어라. \
         의도적이면 그 줄에 `{EXEMPT} <이유>` 를 적는다(맥 방화벽이 cysd 이름으로 묻는 원인 · TICKET=fw-popup-1124):\n{}",
        bad.len(),
        bad.join("\n")
    );
}

/// 반증 변이 — 나쁜 꼴은 잡고, 고친 꼴·면제·주석·남의 명령줄을 흉내 낸 Rust 시험 문자열은 놓아준다.
#[test]
fn judge_catches_wildcard_forms_and_spares_loopback() {
    let r = rules();
    let bad: &[(&str, &str)] = &[
        ("md", "cysr run -- python -m http.server              # 생명주기"),
        ("sh", "cys run -- python3 -m http.server 8000 --directory out"),
        ("py", "srv = http.server.ThreadingHTTPServer((\"\", 0), H)"),
        ("py", "s.bind(('0.0.0.0', 8080))"),
        ("py", "app.run(host=\"0.0.0.0\", port=5000)"),
        ("sh", "wrangler dev --ip 0.0.0.0 --port 8787"),
        ("sh", "npx vite --host 0.0.0.0"),
        ("sh", "uvicorn app:app --host 0.0.0.0"),
        ("rs", "let l = TcpListener::bind(\"0.0.0.0:0\")?;"),
        ("rs", "let a = SocketAddr::new(IpAddr::V4(Ipv4Addr::UNSPECIFIED), 0);"),
    ];
    for (ext, l) in bad {
        assert!(judge(&r, ext, l).is_some(), "[판별] 놓쳤다({ext}): {l}");
    }
    let good: &[(&str, &str)] = &[
        ("md", "cysr run -- python -m http.server --bind 127.0.0.1   # 생명주기"),
        ("sh", "cys run -- python3 -m http.server 8000 -b 127.0.0.1"),
        ("py", "srv = http.server.ThreadingHTTPServer((\"127.0.0.1\", 0), H)"),
        ("py", "for suffix, want in ((\"\", a), (\".minisig\", b)):"),
        ("sh", "wrangler dev --local --ip 127.0.0.1 --port 8787"),
        ("sh", "python3 -m http.server 8000  # wildcard-bind-ok: VM 이 192.168.64.1 로 받아 간다"),
        ("py", "#   \".../Python -m http.server\"로 표시"),
        ("rs", "cmdline: \"python3 -m http.server\".into(),"),
        ("rs", "assert_eq!(endpoint_key(\"uvicorn app:app --bind 0.0.0.0:8000\"), Some(\"port:8000\".into()));"),
        ("rs", "let l = TcpListener::bind(\"127.0.0.1:0\").unwrap();"),
    ];
    for (ext, l) in good {
        assert_eq!(judge(&r, ext, l), None, "[판별] 오탐({ext}): {l}");
    }
}
