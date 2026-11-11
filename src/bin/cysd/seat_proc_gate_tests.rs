//! TICKET=cysr-seatkeep-t3 · 손잡이 우회 grep 게이트 — cysd **운영 구역**에서 좌석 PTY·자식에 직접 닿는 코드는 `seat_proc.rs` 에만
//! 있어야 한다(브리프 §5 방법 ③ · 「남으면 붉어지는 시험」). 시험 구역(`#[cfg(test)]` 이 붙은 mod/fn/impl · `*_tests.rs`)은 세지 않는다 —
//! 그곳은 손잡이 얼굴(`Box<dyn Child>`·`Box<dyn MasterPty>`)을 통해 부르므로 노브 켬에서 seatkeep 구현으로 간다.

/// 문자열·문자·주석을 공백으로 지운다(줄 수 보존).
fn strip_code(src: &str) -> String {
    let b = src.as_bytes();
    let mut out = Vec::with_capacity(b.len());
    let mut i = 0;
    let blank = |out: &mut Vec<u8>, s: &[u8]| out.extend(s.iter().map(|c| if *c == b'\n' { b'\n' } else { b' ' }));
    while i < b.len() {
        if b[i..].starts_with(b"//") {
            let j = b[i..].iter().position(|c| *c == b'\n').map(|p| i + p).unwrap_or(b.len());
            blank(&mut out, &b[i..j]);
            i = j;
        } else if b[i..].starts_with(b"/*") {
            let j = src[i + 2..].find("*/").map(|p| i + 2 + p + 2).unwrap_or(b.len());
            blank(&mut out, &b[i..j]);
            i = j;
        } else if (b[i] == b'r' || (b[i] == b'b' && b.get(i + 1) == Some(&b'r')))
            && (i == 0 || !(b[i - 1].is_ascii_alphanumeric() || b[i - 1] == b'_'))
            && {
                let k = if b[i] == b'b' { i + 2 } else { i + 1 };
                let h = b[k..].iter().take_while(|c| **c == b'#').count();
                b.get(k + h) == Some(&b'"')
            }
        {
            let k = if b[i] == b'b' { i + 2 } else { i + 1 };
            let h = b[k..].iter().take_while(|c| **c == b'#').count();
            let end_pat: Vec<u8> = std::iter::once(b'"').chain(std::iter::repeat(b'#').take(h)).collect();
            let start = k + h + 1;
            let j = b[start..].windows(end_pat.len()).position(|w| w == end_pat.as_slice()).map(|p| start + p + end_pat.len()).unwrap_or(b.len());
            blank(&mut out, &b[i..j]);
            i = j;
        } else if b[i] == b'"' {
            let mut j = i + 1;
            while j < b.len() && b[j] != b'"' {
                j += if b[j] == b'\\' { 2 } else { 1 };
            }
            let j = (j + 1).min(b.len());
            blank(&mut out, &b[i..j]);
            i = j;
        } else if b[i] == b'\'' {
            // 문자 리터럴('x' · '\n' · '\u{..}')만 지운다 — 수명 표기('a)는 닫는 따옴표가 가까이 없다.
            let close = b[i + 1..].iter().take(12).position(|c| *c == b'\'').map(|p| i + 1 + p);
            match close {
                Some(j) if j == i + 2 || b[i + 1] == b'\\' => {
                    blank(&mut out, &b[i..=j]);
                    i = j + 1;
                }
                _ => {
                    out.push(b[i]);
                    i += 1;
                }
            }
        } else {
            out.push(b[i]);
            i += 1;
        }
    }
    String::from_utf8(out).unwrap_or_default()
}

/// 시험 전용 cfg 속성(`#[cfg(test)]` · `#[cfg(all(test, ..))]`)이 달린 `mod`/`fn`/`impl` 블록을 지운다(중괄호 짝). 선언만 있는 `mod x;` 는 그대로.
fn drop_test_blocks(code: &str) -> String {
    let mut s = code.to_string();
    let mut from = 0;
    while let Some(k) = s[from..].find("#[cfg(") {
        let at = from + k;
        let Some(close) = s[at..].find(']') else { break };
        let inner: String = s[at + "#[cfg(".len()..at + close].chars().filter(|c| !c.is_whitespace()).collect();
        if !(inner == "test)" || inner.starts_with("all(test,")) {
            from = at + 1;
            continue;
        }
        let rest = &s[at..];
        let open = match (rest.find('{'), rest.find(';')) {
            (Some(b), Some(c)) if c < b => {
                from = at + 1; // `mod x;` 같은 선언
                continue;
            }
            (Some(b), _) => at + b,
            _ => break,
        };
        let bytes = s.as_bytes();
        let mut depth = 0i64;
        let mut k = open;
        while k < bytes.len() {
            match bytes[k] {
                b'{' => depth += 1,
                b'}' => {
                    depth -= 1;
                    if depth == 0 {
                        break;
                    }
                }
                _ => {}
            }
            k += 1;
        }
        let end = (k + 1).min(s.len());
        let blanked: String = s[at..end].chars().map(|c| if c == '\n' { '\n' } else { ' ' }).collect();
        s.replace_range(at..end, &blanked);
        from = at;
    }
    s
}

/// 공백을 다 지운 운영 구역에서 찾을 바늘 — 좌석 PTY·자식에 직접 닿는 호출.
const NEEDLES: &[&str] = &[
    "native_pty_system(",
    ".openpty(",
    ".spawn_command(",
    ".try_clone_reader(",
    ".take_writer(",
    "tcgetpgrp(",
    ".master.lock(",
    ".master.try_lock(",
    ".child.lock(",
    ".child.try_lock(",
    "pty_master_fd.load(",
    "master.as_raw_fd(",
];

/// 운영 구역 위반 목록(파일:줄 · 바늘). 판정 대상 = `src/bin/cysd/*.rs` 중 시험 파일·`seat_proc.rs` 밖.
fn violations() -> Vec<String> {
    let dir = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("src/bin/cysd");
    let mut out = Vec::new();
    let mut files: Vec<_> = std::fs::read_dir(&dir).expect("cysd 소스 폴더").filter_map(|e| e.ok()).map(|e| e.path()).collect();
    files.sort();
    for p in files {
        let name = p.file_name().and_then(|n| n.to_str()).unwrap_or("").to_string();
        if !name.ends_with(".rs") || name.ends_with("_tests.rs") || name == "seat_proc.rs" || name == "pty_test_support.rs" || name == "c8_test_inputs.rs" {
            continue;
        }
        let src = std::fs::read_to_string(&p).expect("소스 읽기");
        let prod = drop_test_blocks(&strip_code(&src));
        // 여러 줄로 이어진 호출(`.master\n    .lock()`)도 잡도록 공백을 지운 뒤 찾고, 줄 번호는 원래 위치로 되돌린다.
        let mut squeezed = String::with_capacity(prod.len());
        let mut line_of = Vec::with_capacity(prod.len());
        let mut line = 1usize;
        for c in prod.chars() {
            if c == '\n' {
                line += 1;
            }
            if !c.is_whitespace() {
                squeezed.push(c);
                for _ in 0..c.len_utf8() {
                    line_of.push(line);
                }
            }
        }
        for n in NEEDLES {
            let mut from = 0;
            while let Some(k) = squeezed[from..].find(n) {
                let at = from + k;
                out.push(format!("{name}:{} {n}", line_of.get(at).copied().unwrap_or(0)));
                from = at + n.len();
            }
        }
    }
    out
}

#[test]
fn seat_handle_gate_no_direct_pty_access_outside_seat_proc() {
    let v = violations();
    assert!(v.is_empty(), "좌석 프로세스 손잡이(seat_proc.rs)를 건너뛴 직접 접근 {}건:\n{}", v.len(), v.join("\n"));
}

/// 게이트가 실제로 잡는지(뮤턴트 대용) — 운영 구역 모양의 문장은 잡고, 시험 블록·주석·문자열 안은 안 잡는다.
#[test]
fn seat_handle_gate_detector_catches_and_skips_correctly() {
    let probe = |src: &str| {
        let prod = drop_test_blocks(&strip_code(src));
        let sq: String = prod.chars().filter(|c| !c.is_whitespace()).collect();
        NEEDLES.iter().filter(|n| sq.contains(*n)).count()
    };
    assert_eq!(probe("fn f(s: &S) { s.child.lock().unwrap().kill(); }"), 1, "운영 문장을 못 잡음");
    assert_eq!(probe("fn f(s: &S) { s.master\n        .lock()\n        .unwrap(); }"), 1, "여러 줄 호출을 못 잡음");
    assert_eq!(probe("#[cfg(test)]\nmod tests { fn f(s: &S) { s.child.lock(); } }"), 0, "시험 블록을 셌다");
    assert_eq!(probe("#[cfg(test)]\n#[allow(x)]\nfn f(s: &S) { s.child.lock(); }\nfn g(s:&S){ s.child.lock(); }"), 1, "시험 fn 뒤 운영 fn 을 놓침");
    assert_eq!(probe("// s.child.lock()\nfn f() { let x = \"s.child.lock()\"; let y = r#\"tcgetpgrp(\"#; }"), 0, "주석·문자열을 셌다");
    assert_eq!(probe("fn f<'a>(s: &'a S) { s.child.lock(); }"), 1, "수명 표기 뒤를 놓침");
    assert_eq!(probe("#[cfg(all(test, unix))]\nmod drills { fn f(s: &S) { s.child.lock(); } }"), 0, "cfg(all(test, ..)) 블록을 셌다");
    assert_eq!(probe("#[cfg(unix)]\nfn f(s: &S) { s.child.lock(); }"), 1, "운영 cfg(unix) 를 시험으로 봤다");
    assert_eq!(probe("#[cfg(not(test))]\nfn f(s: &S) { s.child.lock(); }"), 1, "cfg(not(test)) 를 시험으로 봤다");
}
