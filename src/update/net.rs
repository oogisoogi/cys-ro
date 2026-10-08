//! 갱신 네트워크 sink — 시스템 `curl` 1홉씩(설계 AUTO-UPDATE-118 §4-4 · §3-1 「네트워크 없음」).
//!
//! - 자동 redirect **끔**(`--max-redirs 0`) · 홉마다 `Location` 을 [`super::url::check_redirect`] 로 재대조(≤5홉) ·
//!   `--proto =https` · 연결 10초 · 전체 60초 · 본문 상한. 기존 팩 갱신(`fetch_remote_pack`)과 같은 curl 셸아웃이지만
//!   그쪽의 `-L`(자동 redirect)은 쓰지 않는다.
//! - 응답 `Date` 헤더를 돌려준다(N13 「HTTPS 응답 Date 와 1시간 넘게 차이」).
//! - 피드 위치 덮어쓰기 `CYS_UPDATE_FEED_URL`(`file://<폴더>` 또는 `https://…`)는 **디버그 빌드에서만** 읽는다(§4-4 · 시험 1개).
//!   `file://` 은 덮어쓰기 경로에서만 허용된다(출시 빌드에서 file 스킴 0).
//! - 실패 = 조용히 끝(신호 없음) — 호출부가 「미도달」로 기록한다.

use super::errors::UpdateErr;
use super::url::{check_redirect, check_url, CheckedUrl, Hop, MAX_HOPS};

/// 피드 문서 상한 — **홉(상대 경로)별**([`feed_max_bytes`]). ★1.1.8 본체 실기(2026-10-08): 옛 단일 1 MiB 가 윈 행
/// `payload_manifest`(11,676 행) 를 실은 릴리스 본문 2,474,038 B 를 curl rc 63 으로 막아 `--preserve-installer` 가 rc 4 였다 —
/// 같은 본문을 base64 로 싣는 봉투(≈3.3 MB)도 같은 상한에 걸려 자동 갱신 첫 받기부터 끊긴다.
/// 발행 쪽(`scripts/update/update_common.py` `FEED_*_MAX_BYTES`)이 같은 값으로 초과 문서를 거부한다(대조 시험 = 양쪽 상수 일치).
/// 폐기문·서명(`.minisig`)·그 밖 = 작은 JSON·텍스트.
pub const FEED_MAX_BYTES: u64 = 1 << 20;
/// 릴리스 본문(`<c>/releases/<seq>.json`) — 1.1.8 실측 2,474,038 B 의 약 3.4배.
pub const FEED_BODY_MAX_BYTES: u64 = 8 << 20;
/// 봉투(`<c>/<channel>.json`) — 본문 원문·서명을 base64(4/3배)로 싣는다 + 칸 여유.
pub const FEED_ENVELOPE_MAX_BYTES: u64 = 12 << 20;
const _: () = assert!(FEED_ENVELOPE_MAX_BYTES >= FEED_BODY_MAX_BYTES.div_ceil(3) * 4 + (64 << 10), "봉투 상한 < 최대 본문의 base64 + 여유");

/// 상대 경로 → 그 홉의 상한(`.minisig` = 작은 상한 · `<c>/releases/<n>.json` = 본문 · `<c>/<x>.json` = 봉투 · 그 밖 = 작은 상한).
pub fn feed_max_bytes(rel: &str) -> u64 {
    if rel.ends_with(".minisig") {
        return FEED_MAX_BYTES;
    }
    match rel.split('/').collect::<Vec<_>>()[..] {
        [_, "releases", f] if f.ends_with(".json") => FEED_BODY_MAX_BYTES,
        [_, f] if f.ends_with(".json") => FEED_ENVELOPE_MAX_BYTES,
        _ => FEED_MAX_BYTES,
    }
}
pub const ENV_FEED_URL: &str = "CYS_UPDATE_FEED_URL";
/// 정식 피드 뿌리.
pub const FEED_BASE: &str = "https://jarvis.godmeyou.kr/update";

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum NetErr {
    /// 허용 목록·홉 규칙 위반(`update.url_refused`).
    Refused(UpdateErr),
    /// 연결·HTTP 실패(조용히 끝).
    Unreachable(String),
}

#[derive(Debug, Clone)]
pub struct Fetched {
    pub bytes: Vec<u8>,
    /// 응답 `Date`(epoch 초) · file:// = None.
    pub http_date: Option<i64>,
    /// 따라간 홉(정규화 URL).
    pub hops: Vec<String>,
}

/// 피드 뿌리 — 출시 빌드 = 정식 상수 · 디버그 빌드 = env 덮어쓰기 허용.
pub fn feed_base(debug: bool, get: impl Fn(&str) -> Option<String>) -> String {
    if debug {
        if let Some(v) = get(ENV_FEED_URL).filter(|v| !v.trim().is_empty()) {
            return v.trim().trim_end_matches('/').to_string();
        }
    }
    FEED_BASE.to_string()
}

/// `<뿌리>/<rel>` 를 가져온다(상한 = [`feed_max_bytes`]). `file://` 뿌리는 디버그 덮어쓰기에서만 온다(상한도 같게 잰다).
pub fn fetch_feed_file(base: &str, rel: &str) -> Result<Fetched, NetErr> {
    fetch_feed_file_with(base, rel, &fetch)
}

/// [`fetch_feed_file`] 본체 — https 갈래의 받기 함수를 주입받는다(시험이 그 갈래에 넘어가는 상한을 잰다).
fn fetch_feed_file_with(base: &str, rel: &str, https: &dyn Fn(&str, Hop, u64) -> Result<Fetched, NetErr>) -> Result<Fetched, NetErr> {
    let url = format!("{base}/{rel}");
    let max = feed_max_bytes(rel);
    if let Some(path) = url.strip_prefix("file://") {
        if !cfg!(debug_assertions) {
            return Err(NetErr::Refused(UpdateErr::new(super::ErrCode::UrlRefused, "net", "출시 빌드 file 스킴")));
        }
        let bytes = std::fs::read(path).map_err(|e| NetErr::Unreachable(format!("{path}: {e}")))?;
        if bytes.len() as u64 > max {
            return Err(NetErr::Unreachable("본문 상한 초과".into()));
        }
        return Ok(Fetched { bytes, http_date: None, hops: vec![url.clone()] });
    }
    https(&url, Hop::Feed, max)
}

/// 허용 목록 대조 + 수동 redirect 로 1개를 받는다.
pub fn fetch(url: &str, first: Hop, max_bytes: u64) -> Result<Fetched, NetErr> {
    let mut cur: CheckedUrl = check_url(url, &[first]).map_err(NetErr::Refused)?;
    let mut hops = Vec::new();
    for n in 0..=MAX_HOPS {
        hops.push(cur.to_url());
        let resp = curl_once(&cur.to_url(), max_bytes)?;
        match resp.status {
            200 => return Ok(Fetched { bytes: resp.body, http_date: resp.date, hops }),
            301 | 302 | 303 | 307 | 308 => {
                let loc = resp.location.ok_or_else(|| NetErr::Unreachable(format!("{} 에 Location 없음", resp.status)))?;
                cur = check_redirect(cur.hop, &loc, n + 1).map_err(NetErr::Refused)?;
            }
            s => return Err(NetErr::Unreachable(format!("HTTP {s}"))),
        }
    }
    Err(NetErr::Refused(UpdateErr::new(super::ErrCode::UrlRefused, "net", "redirect 홉 초과")))
}

struct Resp {
    status: u16,
    location: Option<String>,
    date: Option<i64>,
    body: Vec<u8>,
}

fn curl_once(url: &str, max_bytes: u64) -> Result<Resp, NetErr> {
    let dir = std::env::temp_dir().join(format!("cys-upd-net-{}-{}", std::process::id(), super::clock::mono_ms()));
    std::fs::create_dir_all(&dir).map_err(|e| NetErr::Unreachable(e.to_string()))?;
    let (hdr, body) = (dir.join("h"), dir.join("b"));
    let out = crate::hidden_command("curl")
        .args(["-sS", "--proto", "=https", "--max-redirs", "0", "--connect-timeout", "10", "--max-time", "60"])
        .arg("--max-filesize")
        .arg(max_bytes.to_string())
        .arg("-D")
        .arg(&hdr)
        .arg("-o")
        .arg(&body)
        .arg("--")
        .arg(url)
        .output();
    let res = (|| {
        let out = out.map_err(|e| NetErr::Unreachable(format!("curl 실행: {e}")))?;
        if !out.status.success() {
            return Err(NetErr::Unreachable(format!("curl rc {:?}", out.status.code())));
        }
        let headers = std::fs::read_to_string(&hdr).map_err(|e| NetErr::Unreachable(e.to_string()))?;
        let (status, location, date) = parse_headers(&headers).ok_or_else(|| NetErr::Unreachable("응답 머리 판독 불가".into()))?;
        let body = std::fs::read(&body).unwrap_or_default();
        if body.len() as u64 > max_bytes {
            return Err(NetErr::Unreachable("본문 상한 초과".into()));
        }
        Ok(Resp { status, location, date, body })
    })();
    let _ = std::fs::remove_dir_all(&dir);
    res
}

/// 응답 머리 판독 — (상태 코드, Location, Date). curl `-D` 는 홉 1개라 머리 블록 1개다(100 Continue 블록은 건너뜀).
pub fn parse_headers(raw: &str) -> Option<(u16, Option<String>, Option<i64>)> {
    let mut status = None;
    let mut location = None;
    let mut date = None;
    for line in raw.lines() {
        let line = line.trim_end_matches('\r');
        if line.starts_with("HTTP/") {
            let code: u16 = line.split_whitespace().nth(1)?.parse().ok()?;
            if code == 100 {
                continue;
            }
            status = Some(code);
            location = None;
            date = None;
        } else if let Some((k, v)) = line.split_once(':') {
            if k.eq_ignore_ascii_case("location") {
                location = Some(v.trim().to_string());
            } else if k.eq_ignore_ascii_case("date") {
                date = super::clock::parse_http_date(v.trim());
            }
        }
    }
    Some((status?, location, date))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn header_parse() {
        let raw = "HTTP/2 302 \r\nlocation: https://release-assets.githubusercontent.com/github-production-release-asset/1/ab?x=1\r\ndate: Tue, 06 Oct 2026 00:12:00 GMT\r\n\r\n";
        let (s, l, d) = parse_headers(raw).unwrap();
        assert_eq!(s, 302);
        assert!(l.unwrap().starts_with("https://release-assets"));
        assert_eq!(d, Some(1_791_245_520));
        let raw = "HTTP/1.1 100 Continue\r\n\r\nHTTP/1.1 200 OK\r\nDate: Tue, 06 Oct 2026 00:12:00 GMT\r\n\r\n";
        assert_eq!(parse_headers(raw).unwrap().0, 200);
        assert!(parse_headers("garbage").is_none());
    }

    /// §4-4·§7-1 「출시 빌드에서 CYS_UPDATE_FEED_URL 무시」.
    #[test]
    fn feed_url_override_only_in_debug() {
        let get = |_: &str| Some("file:///tmp/feed/".to_string());
        assert_eq!(feed_base(true, get), "file:///tmp/feed");
        assert_eq!(feed_base(false, get), FEED_BASE);
        assert_eq!(feed_base(true, |_: &str| None), FEED_BASE);
    }

    /// 허용 목록 밖 URL 은 curl 을 부르기 전에 거부(네트워크 sink 단위 시험 · MI3 ①).
    #[test]
    fn refused_before_any_network() {
        for u in ["https://evil.example/update/cysr/stable.json", "http://jarvis.godmeyou.kr/update/cysr/stable.json",
            "https://github.com/idoforgod/cys-terminal/releases/download/v1/x.zip"] {
            match fetch(u, Hop::Feed, 10) {
                Err(NetErr::Refused(e)) => assert_eq!(e.code, super::super::ErrCode::UrlRefused),
                o => panic!("{u}: {o:?}"),
            }
        }
    }

    #[test]
    fn file_override_reads_local_feed() {
        let d = std::env::temp_dir().join(format!("cys-u1-net-{}", std::process::id()));
        std::fs::create_dir_all(d.join("cysr")).unwrap();
        std::fs::write(d.join("cysr/stable.json"), b"{}").unwrap();
        let base = format!("file://{}", d.display());
        let f = fetch_feed_file(&base, "cysr/stable.json").unwrap();
        assert_eq!(f.bytes, b"{}");
        assert!(matches!(fetch_feed_file(&base, "cysr/none.json"), Err(NetErr::Unreachable(_))));
        let _ = std::fs::remove_dir_all(&d);
    }

    /// 홉별 상한 분류(본문·봉투·폐기문·서명) — 1.1.8 본체 실기 rc 63 회귀.
    #[test]
    fn feed_max_bytes_per_hop() {
        assert_eq!(feed_max_bytes("cysr/releases/1.json"), FEED_BODY_MAX_BYTES);
        assert_eq!(feed_max_bytes("agora-client/releases/12.json"), FEED_BODY_MAX_BYTES);
        assert_eq!(feed_max_bytes("cysr/stable.json"), FEED_ENVELOPE_MAX_BYTES);
        assert_eq!(feed_max_bytes("cysr/next.json"), FEED_ENVELOPE_MAX_BYTES);
        for small in ["revocations.json", "revocations.json.minisig", "cysr/releases/1.json.minisig", "cysr/stable.json.minisig"] {
            assert_eq!(feed_max_bytes(small), FEED_MAX_BYTES, "{small}");
        }
        assert!(FEED_BODY_MAX_BYTES > 2_474_038, "1.1.8 실측 본문이 상한 안");
        assert!(FEED_ENVELOPE_MAX_BYTES > 2_474_038_u64.div_ceil(3) * 4, "1.1.8 실측 본문을 실은 봉투가 상한 안");
    }

    /// https 갈래(기기 실경로)도 홉별 상한을 curl 에 넘긴다 — 받기 함수 주입으로 넘어간 값을 잰다.
    #[test]
    fn https_branch_passes_per_hop_cap() {
        let seen = std::cell::RefCell::new(Vec::new());
        let spy = |u: &str, h: Hop, m: u64| -> Result<Fetched, NetErr> {
            seen.borrow_mut().push((u.to_string(), h, m));
            Err(NetErr::Unreachable("spy".into()))
        };
        for rel in ["cysr/releases/1.json", "cysr/stable.json", "revocations.json", "cysr/releases/1.json.minisig"] {
            let _ = fetch_feed_file_with(FEED_BASE, rel, &spy);
        }
        let got: Vec<u64> = seen.borrow().iter().map(|(_, _, m)| *m).collect();
        assert_eq!(got, vec![FEED_BODY_MAX_BYTES, FEED_ENVELOPE_MAX_BYTES, FEED_MAX_BYTES, FEED_MAX_BYTES]);
        assert!(seen.borrow().iter().all(|(u, h, _)| u.starts_with(FEED_BASE) && *h == Hop::Feed));
    }

    /// 상한 경계 ±1(본문·봉투·폐기문) — 같은 바이트 수 = 받음 · +1 = 미도달(curl `--max-filesize` 와 같은 「초과만 거부」).
    #[test]
    fn feed_cap_boundary_plus_minus_one() {
        let d = std::env::temp_dir().join(format!("cys-u1-net-cap-{}", std::process::id()));
        std::fs::create_dir_all(d.join("cysr/releases")).unwrap();
        let base = format!("file://{}", d.display());
        for (rel, max) in [("cysr/releases/1.json", FEED_BODY_MAX_BYTES), ("cysr/stable.json", FEED_ENVELOPE_MAX_BYTES), ("revocations.json", FEED_MAX_BYTES)] {
            std::fs::write(d.join(rel), vec![b' '; max as usize]).unwrap();
            assert_eq!(fetch_feed_file(&base, rel).unwrap().bytes.len() as u64, max, "{rel} = 상한");
            std::fs::write(d.join(rel), vec![b' '; max as usize + 1]).unwrap();
            assert!(matches!(fetch_feed_file(&base, rel), Err(NetErr::Unreachable(m)) if m == "본문 상한 초과"), "{rel} = 상한+1");
        }
        let _ = std::fs::remove_dir_all(&d);
    }
}
