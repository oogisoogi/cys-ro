//! TICKET=cysr-seatkeep-t3 · 손잡이 우회 grep 게이트 — cysd **운영 구역**에서 좌석 PTY·자식에 직접 닿는 코드는 `seat_proc.rs` 에만
//! 있어야 한다(브리프 §5 방법 ③ · 「남으면 붉어지는 시험」). 시험 구역(`#[cfg(test)]` 이 붙은 mod/fn/impl · `*_tests.rs`)은 세지 않는다 —
//! 그곳은 손잡이 얼굴(`Box<dyn Child>`·`Box<dyn MasterPty>`)을 통해 부르므로 노브 켬에서 seatkeep 구현으로 간다.
//!
//! ⚠알려진 한계(codex 1R #3 · master 처분 = 싼 것만 고침 · 필드 비공개화 86곳은 안 함): 이 게이트는 **문자열 판독**이다(Rust 구문 트리 아님).
//! 잡는 것 = `.child`/`.master` 필드 참조(별칭 포함) · `Surface { child, .. }` 구조 분해 · 손잡이 머리의 식별자 경계(`evil_probe_child(` 거부) ·
//! 손잡이 함수의 **직접 인자**가 아닌 넘김(중첩 호출 `seat_proc::f(g(&s.child))` 거부). 못 잡는 것(남는 우회) = 매크로가 만든 접근 ·
//! 다른 이름으로 다시 내보낸 타입(`type S = Surface;` 뒤 `S { child, .. }`) · 필드를 통째로 옮기는 함수 인자(`fn f(Surface { child, .. }: Surface)`
//! 의 타입 경로가 `Surface` 가 아닌 경우) · 손잡이 함수 안에서 받은 참조를 밖으로 돌려주는 것. 정본(타입으로 막기)은 `Surface` 필드를
//! 손잡이 모듈 비공개 타입으로 바꾸는 것이며 T4 이후 몫이다.

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

/// 좌석 필드(`Surface::child`·`Surface::master`)를 가리키는 자리 — 손잡이로 **넘기는** 자리(`seat_proc::<함수>(… &x.child …)`)만 허용한다
/// (독립 검증 D4 · 별칭 `let ch = &s.child; ch.lock()` 도 여기서 잡힌다). 타입으로 막는 길은 시험 구역 86곳이 바뀌어 차선을 골랐다.
const FIELDS: &[&str] = &[".child", ".master"];

/// 같은 이름의 다른 구조체 필드(좌석 아님) — (파일, 받는 쪽+필드) 짝으로만 허용한다. 늘리면 까닭을 적는다.
const UNRELATED_FIELDS: &[(&str, &str)] = &[
    ("declaration.rs", "v.master"),       // 선언 어휘(Vocab) 의 master 칸
    ("declaration.rs", "vocab().master"), // 같은 것
    ("governance.rs", "d.child"),         // 후손 기록(부모·자식 pid 짝)의 child 칸
    ("state.rs", "spawned.child"),        // 손잡이가 돌려준 결과(seat_proc::Spawned)를 Surface 로 옮기는 자리 · 뿌리 관측(얼굴 = Child 트레이트)
    ("state.rs", "spawned.master"),       // 같은 것(Surface.master 로 옮김)
];

/// 손잡이로 넘기는 호출의 머리 — `seat_proc::` 또는 그 모듈에서 가져다 쓰는 손잡이 함수 이름. 앞 글자는 식별자 경계여야 한다
/// (codex 1R #3: `evil_probe_child(` · `notseat_proc::` 는 머리가 아니다).
const HANDOFF_HEADS: &[&str] = &["seat_proc::", "probe_child("];

/// `Surface` 구조체 식(구조 분해 패턴이든 만들기든)에서 좌석 필드를 집는 자리 — 만들기는 이 (파일, 바로 앞 글자열) 짝만 허용한다.
const SURFACE_LITERAL_OK: &[(&str, &str)] = &[
    ("state.rs", "Arc::new("), // 좌석 생성 — 손잡이 결과(spawned.child·master)를 Surface 로 옮기는 유일한 자리
];

fn is_ident(c: u8) -> bool {
    c.is_ascii_alphanumeric() || c == b'_'
}

/// 손잡이 머리 `h` 가 `sq[..at]` 안에서 식별자 경계로 나오는 마지막 위치.
fn last_head(sq: &str, at: usize, h: &str) -> Option<usize> {
    let b = sq.as_bytes();
    let mut end = at;
    while let Some(p) = sq[..end].rfind(h) {
        if p == 0 || !is_ident(b[p - 1]) {
            return Some(p);
        }
        end = p;
    }
    None
}

/// 손잡이 머리 `sp` 의 호출 괄호 **바로 안**(깊이 1)의 인자로 `&x.field` 가 넘겨지는가 — 받는 쪽 식(`x`)은 식별자와 `.` 만(codex 1R #3:
/// 중첩 호출 `seat_proc::f(g(&s.child))`·식 섞기 `seat_proc::f(&(a+s).child)` 는 직접 인자가 아니다).
fn direct_arg(sq: &str, sp: usize, at: usize) -> bool {
    let between = &sq[sp..at];
    if between.contains(';') || between.contains('{') || between.contains('}') {
        return false;
    }
    let Some(open) = between.find('(') else { return false };
    let args = &between[open + 1..];
    let mut depth = 0i32;
    let mut last = 0usize;
    for (i, c) in args.char_indices() {
        match c {
            '(' | '[' => depth += 1,
            ')' | ']' => {
                depth -= 1;
                if depth < 0 {
                    return false; // 머리 호출이 이미 닫혔다
                }
            }
            ',' if depth == 0 => last = i + 1,
            _ => {}
        }
    }
    if depth != 0 {
        return false;
    }
    let arg = &args[last..];
    let body = arg.strip_prefix("&mut").or_else(|| arg.strip_prefix('&')).unwrap_or(arg);
    !body.is_empty() && body.bytes().all(|c| is_ident(c) || c == b'.')
}

/// `Surface { … }` 구조체 식 안에서 좌석 필드(`child`·`master`)를 집는 자리 — (바이트 위치, 표시). 다른 타입의 `X::Surface {`·
/// `VerifiedSurface {` 는 보지 않는다(앞이 식별자이거나 `state::` 가 아닌 `::`).
fn surface_pattern_violations(name: &str, sq: &str) -> Vec<(usize, String)> {
    let b = sq.as_bytes();
    let mut out = Vec::new();
    let mut from = 0;
    while let Some(k) = sq[from..].find("Surface{") {
        let at = from + k;
        from = at + "Surface{".len();
        // 앞 식별자 = 다른 이름의 일부(`VerifiedSurface`)면 건너뛴다 — 공백을 지운 글이라 `let Surface` 는 `letSurface` 로 붙는다(키워드는 본다).
        let word_start = sq[..at].bytes().rev().take_while(|c| is_ident(*c)).count();
        let word = &sq[at - word_start..at];
        if !word.is_empty() && !matches!(word, "let" | "iflet" | "whilelet" | "elseiflet" | "mut" | "ref" | "in") {
            continue;
        }
        if sq[..at].ends_with("::") && !sq[..at].ends_with("state::") {
            continue;
        }
        if SURFACE_LITERAL_OK.iter().any(|(n, pre)| *n == name && sq[..at].ends_with(pre)) {
            continue;
        }
        // 짝 맞는 닫는 중괄호까지의 깊이 1 필드 이름들
        let mut depth = 0i32;
        let mut field_start = at + "Surface{".len();
        let mut k2 = at + "Surface".len();
        while k2 < b.len() {
            match b[k2] {
                b'{' | b'(' | b'[' => depth += 1,
                b'}' | b')' | b']' => {
                    depth -= 1;
                    if depth == 0 {
                        break;
                    }
                }
                _ => {}
            }
            if depth == 1 && (b[k2] == b'{' || b[k2] == b',') {
                field_start = k2 + 1;
                let name_end = sq[field_start..].bytes().take_while(|c| is_ident(*c)).count() + field_start;
                let field = &sq[field_start..name_end];
                let after = b.get(name_end).copied();
                if (field == "child" || field == "master") && matches!(after, Some(b':') | Some(b',') | Some(b'}')) {
                    out.push((field_start, format!("Surface{{{field}}}")));
                }
            }
            k2 += 1;
        }
        let _ = field_start;
    }
    out
}

/// 압축된(공백 없는) 운영 구역에서 좌석 필드 참조 위반을 찾는다 — (바이트 위치, 「받는 쪽+필드」).
fn field_violations(name: &str, sq: &str) -> Vec<(usize, String)> {
    let b = sq.as_bytes();
    let ident = |c: u8| c.is_ascii_alphanumeric() || c == b'_';
    let mut out = Vec::new();
    for f in FIELDS {
        let mut from = 0;
        while let Some(k) = sq[from..].find(f) {
            let at = from + k;
            from = at + f.len();
            if b.get(at + f.len()).map(|c| ident(*c)).unwrap_or(false) {
                continue; // `.children` · `.master_fd` 같은 다른 이름
            }
            // 받는 쪽 = 바로 앞 식별자(또는 `()` 로 끝나는 호출)
            let mut st = at;
            while st > 0 && (ident(b[st - 1]) || b[st - 1] == b'(' || b[st - 1] == b')') {
                st -= 1;
            }
            let recv = &sq[st..at + f.len()];
            if UNRELATED_FIELDS.iter().any(|(n, r)| *n == name && recv.ends_with(r) && (recv.len() == r.len() || !ident(recv.as_bytes()[recv.len() - r.len() - 1]))) {
                continue;
            }
            // 손잡이로 넘기는 자리: 앞쪽 가장 가까운 (식별자 경계의) 손잡이 호출 머리의 **직접 인자**다(codex 1R #3).
            let handoff = HANDOFF_HEADS.iter().filter_map(|h| last_head(sq, at, h)).max().map(|sp| direct_arg(sq, sp, at));
            if handoff == Some(true) {
                continue;
            }
            out.push((at, recv.to_string()));
        }
    }
    out
}

/// 판정 대상 = `src/bin/cysd/` 아래 모든 `.rs`(하위 폴더 포함) + 라이브러리 `src/*.rs` — 시험 파일·`seat_proc.rs`·시험 지원 파일 밖.
fn target_files() -> Vec<std::path::PathBuf> {
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR"));
    let mut files = Vec::new();
    let mut stack = vec![root.join("src/bin/cysd")];
    while let Some(d) = stack.pop() {
        for e in std::fs::read_dir(&d).expect("소스 폴더").flatten() {
            let p = e.path();
            if p.is_dir() {
                stack.push(p);
            } else {
                files.push(p);
            }
        }
    }
    files.extend(std::fs::read_dir(root.join("src")).expect("src").flatten().map(|e| e.path()).filter(|p| p.is_file()));
    files.retain(|p| {
        let name = p.file_name().and_then(|n| n.to_str()).unwrap_or("");
        name.ends_with(".rs") && !name.ends_with("_tests.rs") && name != "seat_proc.rs" && name != "pty_test_support.rs" && name != "c8_test_inputs.rs"
    });
    files.sort();
    files
}

/// 운영 구역 위반 목록(파일:줄 · 바늘).
fn violations() -> Vec<String> {
    let mut out = Vec::new();
    for p in target_files() {
        let name = p.file_name().and_then(|n| n.to_str()).unwrap_or("").to_string();
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
        for (at, recv) in field_violations(&name, &squeezed) {
            out.push(format!("{name}:{} 필드 참조 {recv}", line_of.get(at).copied().unwrap_or(0)));
        }
        for (at, what) in surface_pattern_violations(&name, &squeezed) {
            out.push(format!("{name}:{} 구조 분해 {what}", line_of.get(at).copied().unwrap_or(0)));
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
    // D4: 필드 참조 자체 — 별칭은 잡고, 손잡이로 넘기는 자리·다른 이름·허용 목록은 안 잡는다.
    let fields = |name: &str, src: &str| {
        let prod = drop_test_blocks(&strip_code(src));
        let sq: String = prod.chars().filter(|c| !c.is_whitespace()).collect();
        field_violations(name, &sq).len()
    };
    assert_eq!(fields("governance.rs", "fn f(surface: &S) { let ch = &surface.child; let _ = ch.lock().map(|mut c| c.try_wait()); }"), 1, "별칭 우회(검증 ME)를 못 잡음");
    assert_eq!(fields("x.rs", "fn f(s: &S) { let m = &s.master; m.lock(); }"), 1, "master 별칭을 못 잡음");
    assert_eq!(fields("governance.rs", "fn f(surface: &S) { crate::seat_proc::kill_and_reap(&surface.child); }"), 0, "손잡이로 넘기는 자리를 셌다");
    assert_eq!(fields("close_auth.rs", "fn f(s: &S) -> P { crate::seat_proc::probe_child(&s.exited, &s.child) }"), 0, "둘째 인자로 넘기는 자리를 셌다");
    assert_eq!(fields("close_auth.rs", "fn f(s: &S) -> P { probe_child(&s.exited, &s.child) }"), 0, "가져다 쓴 손잡이 함수로 넘기는 자리를 셌다");
    assert_eq!(fields("state.rs", "fn f(spawned: Spawned) { let m = Mutex::new(spawned.master); }"), 0, "손잡이 결과를 옮기는 자리를 셌다");
    assert_eq!(fields("handlers.rs", "fn f(spawned: Spawned) { let m = spawned.master; }"), 1, "Spawned 허용이 다른 파일로 샜다");
    assert_eq!(fields("x.rs", "fn f(s: &S) { let _ = s.children(); let _ = s.master_fd; }"), 0, "다른 이름을 셌다");
    assert_eq!(fields("governance.rs", "fn f(d: &D) { let _ = d.child; }"), 0, "허용 목록(후손 기록)을 셌다");
    assert_eq!(fields("x.rs", "fn f(d: &D) { let _ = d.child; }"), 1, "허용 목록이 다른 파일로 샜다");
    assert_eq!(fields("x.rs", "fn f(s: &S) { crate::seat_proc::resize(&s.master, 1, 1); let c = &s.child; }"), 1, "넘기는 자리 뒤의 별칭을 놓침");
    // codex 1R #3: 식별자 경계 · 중첩 호출 · 구조 분해.
    assert_eq!(fields("x.rs", "fn f(s: &S) { evil_probe_child(&s.child); }"), 1, "식별자 경계 없는 머리(evil_probe_child)를 허용함");
    assert_eq!(fields("x.rs", "fn f(s: &S) { notseat_proc::kill_and_reap(&s.child); }"), 1, "식별자 경계 없는 seat_proc:: 를 허용함");
    assert_eq!(fields("x.rs", "fn f(s: &S) { crate::seat_proc::resize(pass_through(&s.master), 1, 1); }"), 1, "중첩 호출을 허용함");
    assert_eq!(fields("x.rs", "fn f(s: &S) { crate::seat_proc::kill_and_reap(&wrap(s).child); }"), 1, "식 섞인 받는 쪽을 허용함");
    assert_eq!(fields("x.rs", "fn f(s: &S) { crate::seat_proc::kill_and_reap(&self.surfaces.child); }"), 0, "점 경로 받는 쪽을 셌다");
    assert_eq!(fields("x.rs", "fn f(s: &S) { crate::seat_proc::resize(&s.master, s.rows(), s.cols()); }"), 0, "뒤 인자의 호출 때문에 셌다");
    let pats = |name: &str, src: &str| {
        let prod = drop_test_blocks(&strip_code(src));
        let sq: String = prod.chars().filter(|c| !c.is_whitespace()).collect();
        surface_pattern_violations(name, &sq).len()
    };
    assert_eq!(pats("x.rs", "fn f(surface: Surface) { let Surface { child: ch, .. } = surface; ch.lock(); }"), 1, "구조 분해(child: 이름)를 놓침");
    assert_eq!(pats("x.rs", "fn f(surface: Surface) { let crate::state::Surface { id, master, .. } = surface; }"), 1, "경로 붙은 구조 분해(줄임)를 놓침");
    assert_eq!(pats("x.rs", "fn f(s: Surface) { if let Surface { child, .. } = s {} }"), 1, "if let 구조 분해를 놓침");
    assert_eq!(pats("x.rs", "fn f(s: Surface) { let Surface { id, name, .. } = s; }"), 0, "좌석 필드 없는 구조 분해를 셌다");
    assert_eq!(pats("x.rs", "fn f() { let a = CallerRecord::Surface { id: 1 }; let b = VerifiedSurface { child: 1 }; }"), 0, "다른 타입을 셌다");
    assert_eq!(pats("state.rs", "fn f() { let s = Arc::new(Surface { id, child: Mutex::new(spawned.child), master: m }); }"), 0, "허용된 좌석 생성을 셌다");
    assert_eq!(pats("handlers.rs", "fn f() { let s = Arc::new(Surface { id, child: c }); }"), 1, "좌석 생성 허용이 다른 파일로 샜다");
    assert_eq!(pats("x.rs", "fn f(s: Surface) { let Surface { inner: Inner { child }, .. } = s; }"), 0, "깊이 2 의 다른 필드를 셌다");
}
