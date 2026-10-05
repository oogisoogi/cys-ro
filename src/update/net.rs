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

/// 피드 본문 상한(봉투·폐기문·본문 — 작은 JSON).
pub const FEED_MAX_BYTES: u64 = 1 << 20;
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

/// `<뿌리>/<rel>` 를 가져온다. `file://` 뿌리는 디버그 덮어쓰기에서만 온다.
pub fn fetch_feed_file(base: &str, rel: &str) -> Result<Fetched, NetErr> {
    let url = format!("{base}/{rel}");
    if let Some(path) = url.strip_prefix("file://") {
        if !cfg!(debug_assertions) {
            return Err(NetErr::Refused(UpdateErr::new(super::ErrCode::UrlRefused, "net", "출시 빌드 file 스킴")));
        }
        return std::fs::read(path)
            .map(|bytes| Fetched { bytes, http_date: None, hops: vec![url.clone()] })
            .map_err(|e| NetErr::Unreachable(format!("{path}: {e}")));
    }
    fetch(&url, Hop::Feed, FEED_MAX_BYTES)
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
}
