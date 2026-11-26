// 넘겨받은 CYSR_BUILD_ID 검사(1.1.20 #57 R1 · TICKET=cysr-1120-integ2 · master#c5a0c510).
//
// build.rs 가 `#[path]` 로 이 파일을 읽어 빌드 때 부르고, lib 시험(src/update/buildinfo.rs tests)도 같은 파일을 읽어 잰다
// (빌드 스크립트는 시험 하네스가 없다 — 한 파일 두 소비자 · 운영 lib 에는 시험 때만 실린다).
//
// 왜: 빌드 표지 `cysr-buildmark:…;build_id=<id>;`(buildinfo.rs) 와 x64 정적 수집기(scripts/update/collect_x64_static.py)는
// build_id 앞 12자를 「이 바이너리를 컴파일한 커밋」 으로 믿는다. 종전 build.rs 는 넘겨받은 값을 trim 만 해 그대로 구웠다 —
// 다른 커밋에서 같은 값을 export 해 만든 바이너리도 같은 표지를 가졌고(검증 R1 · F07), 공백 값은 trim 뒤 빈 값으로 떨어져
// 타깃마다 자기 시각으로 찍혔다. 그래서 받은 값이 「지금 HEAD 12자 + 지금 -dirty 여부 + UTC 분」 꼴이 아니면 빌드를 멈춘다.

/// 받은 값이 쓸 수 있으면 None, 아니면 멈출 이유. `head12` = `git rev-parse --short=12 HEAD`(못 읽으면 "unknown") · `dirty` = 추적 파일 변경 있음.
pub fn given_build_id_problem(given: &str, head12: &str, dirty: bool) -> Option<String> {
    let b = given.as_bytes();
    let hex12 = |s: &[u8]| s.len() == 12 && s.iter().all(|c| c.is_ascii_digit() || (b'a'..=b'f').contains(c));
    let (sha, rest) = if b.len() >= 12 { b.split_at(12) } else { return Some(format!("CYSR_BUILD_ID 형식(<커밋 12자>[-dirty].<UTC yyyymmddTHHMMZ>) 아님: {given:?}")) };
    let (has_dirty, stamp) = match rest.strip_prefix(b"-dirty") {
        Some(s) => (true, s),
        None => (false, rest),
    };
    let stamp_ok = stamp.len() == 15
        && stamp[0] == b'.'
        && stamp[1..9].iter().all(u8::is_ascii_digit)
        && stamp[9] == b'T'
        && stamp[10..14].iter().all(u8::is_ascii_digit)
        && stamp[14] == b'Z';
    if !hex12(sha) || !stamp_ok {
        return Some(format!("CYSR_BUILD_ID 형식(<커밋 12자>[-dirty].<UTC yyyymmddTHHMMZ>) 아님: {given:?}"));
    }
    if !hex12(head12.as_bytes()) {
        return Some(format!("CYSR_BUILD_ID 를 받았는데 지금 HEAD 를 읽지 못했다({head12:?}) — 어느 커밋인지 대조할 수 없다"));
    }
    if sha != head12.as_bytes() {
        return Some(format!(
            "CYSR_BUILD_ID 커밋 {} ≠ 지금 HEAD {head12} — 다른 커밋의 값을 재사용하면 표지가 이 코드를 가리키지 않는다",
            String::from_utf8_lossy(sha)
        ));
    }
    if has_dirty != dirty {
        return Some(format!(
            "CYSR_BUILD_ID 의 -dirty 표기({}) ≠ 지금 작업트리({})",
            if has_dirty { "있음" } else { "없음" },
            if dirty { "추적 파일 변경 있음" } else { "깨끗" }
        ));
    }
    None
}
