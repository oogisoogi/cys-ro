//! 갱신 URL 허용 목록 · redirect 홉 규칙(설계 AUTO-UPDATE-118 §4-4 · 1R BLOCK 9 · MI3).
//!
//! 정규화 뒤 대조: 스킴 `https` 만 · 호스트 소문자·끝 점 제거 · 비 ASCII 호스트 거부(허용 호스트가 전부 ASCII 라 IDNA 결과가
//! 목록과 같을 수 없다 — 정규화 대신 거부가 같은 결과를 더 단순하게 낸다) · 포트 지정·userinfo·IP 리터럴·인코딩된 구분자
//! (`%2F`·`%5C`·`%2E` 등)·역슬래시·제어문자 거부 · 경로 `.`/`..` 정규화 뒤 정규식 대조. 쿼리는 자산 redirect 홉
//! (서명 토큰)에서만 허용하고 대조 밖이다.
//!
//! 홉 관계: 피드 → 피드 · 자산 1홉 → (자산 1홉 | 자산 redirect) · 자산 redirect → 자산 redirect · 최대 5홉.
//! 바꾸는 것은 새 판 또는 R 폐기문의 `url_rules` 추가로만(이 판에서는 상수).

use super::errors::{ErrCode, UpdateErr};

/// 피드·폐기문·본문 보관소·아고라 zip 호스트.
pub const FEED_HOST: &str = "jarvis.godmeyou.kr";
/// 자산 1홉 호스트.
pub const ASSET_HOST: &str = "github.com";
/// 자산 redirect 호스트(실측 2026-10-05 23:2x · `HTTP/2 302 location: https://release-assets.githubusercontent.com/…`).
pub const ASSET_REDIRECT_HOST: &str = "release-assets.githubusercontent.com";
/// redirect 를 따라가는 최대 홉 수.
pub const MAX_HOPS: usize = 5;

/// 홉 종류.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Hop {
    Feed,
    AssetFirst,
    AssetRedirect,
}

const FEED_PATHS: [&str; 4] = [
    r"^/update/(cysr|agora-client)/(stable|next)\.json(\.minisig)?$",
    r"^/update/revocations\.json(\.minisig)?$",
    r"^/update/(cysr|agora-client)/releases/[0-9]+\.json(\.minisig)?$",
    r"^/install/agora-client-[0-9.]+\.zip$",
];
const ASSET_FIRST_PATH: &str = r"^/oogisoogi/cys-ro/releases/download/v[0-9][0-9A-Za-z.+-]*/[A-Za-z0-9._+-]+$";
const ASSET_REDIRECT_PATH: &str = r"^/github-production-release-asset/[0-9]+/[0-9a-f-]+$";

/// 정규화된 URL(대조 통과본).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CheckedUrl {
    pub hop: Hop,
    pub host: String,
    pub path: String,
    pub query: Option<String>,
}

impl CheckedUrl {
    /// 내려받기에 쓸 정규화 문자열.
    pub fn to_url(&self) -> String {
        match &self.query {
            Some(q) => format!("https://{}{}?{}", self.host, self.path, q),
            None => format!("https://{}{}", self.host, self.path),
        }
    }
}

fn refused(detail: impl Into<String>) -> UpdateErr {
    UpdateErr::new(ErrCode::UrlRefused, "url", detail)
}

/// 구문 분해 + 정규화(규칙 대조 전). 성공 = (호스트, 경로, 쿼리).
fn normalize(url: &str) -> Result<(String, String, Option<String>), UpdateErr> {
    if url.chars().any(|c| c.is_control() || c == '\\' || c.is_whitespace()) {
        return Err(refused("제어문자·역슬래시·공백"));
    }
    let rest = url
        .strip_prefix("https://")
        .or_else(|| {
            // 스킴은 대소문자 무관(RFC 3986) — 소문자로 비교하되 https 외는 거부.
            let (s, r) = url.split_once("://")?;
            if s.eq_ignore_ascii_case("https") {
                Some(r)
            } else {
                None
            }
        })
        .ok_or_else(|| refused("https 아님"))?;
    if rest.contains('#') {
        return Err(refused("조각(#) 거부"));
    }
    let (authority, path_query) = match rest.find('/') {
        Some(i) => (&rest[..i], &rest[i..]),
        None => (rest, "/"),
    };
    if authority.contains('@') {
        return Err(refused("userinfo 거부"));
    }
    if authority.contains(':') || authority.contains('[') {
        return Err(refused("포트·IP 리터럴 거부"));
    }
    if !authority.is_ascii() {
        return Err(refused("비 ASCII 호스트"));
    }
    let mut host = authority.to_ascii_lowercase();
    while host.ends_with('.') {
        host.pop();
    }
    if host.is_empty() {
        return Err(refused("호스트 없음"));
    }
    if host.split('.').all(|l| !l.is_empty() && l.chars().all(|c| c.is_ascii_digit())) {
        return Err(refused("IP 리터럴 거부"));
    }
    let (raw_path, query) = match path_query.split_once('?') {
        Some((p, q)) => (p, Some(q.to_string())),
        None => (path_query, None),
    };
    let lower = raw_path.to_ascii_lowercase();
    for enc in ["%2f", "%5c", "%2e", "%00", "%3f", "%23"] {
        if lower.contains(enc) {
            return Err(refused(format!("인코딩된 구분자 {enc}")));
        }
    }
    // `.`/`..` 정규화(루트 위로 못 올라간다 — 올라가려 하면 거부).
    let mut segs: Vec<&str> = Vec::new();
    for s in raw_path.split('/').skip(1) {
        match s {
            "." => {}
            ".." => {
                if segs.pop().is_none() {
                    return Err(refused("루트 위 .."));
                }
            }
            other => segs.push(other),
        }
    }
    let path = format!("/{}", segs.join("/"));
    Ok((host, path, query))
}

fn re(p: &str) -> regex::Regex {
    regex::Regex::new(p).expect("상수 정규식")
}

/// URL 하나를 `allowed` 홉 종류 중 하나로 대조한다(첫 일치 종류로 분류).
pub fn check_url(url: &str, allowed: &[Hop]) -> Result<CheckedUrl, UpdateErr> {
    let (host, path, query) = normalize(url)?;
    for &hop in allowed {
        let ok = match hop {
            Hop::Feed => host == FEED_HOST && query.is_none() && FEED_PATHS.iter().any(|p| re(p).is_match(&path)),
            Hop::AssetFirst => host == ASSET_HOST && query.is_none() && re(ASSET_FIRST_PATH).is_match(&path),
            // redirect 홉의 쿼리(서명 토큰)는 대조 밖 — 있어도 되고 없어도 된다.
            Hop::AssetRedirect => host == ASSET_REDIRECT_HOST && re(ASSET_REDIRECT_PATH).is_match(&path),
        };
        if ok {
            return Ok(CheckedUrl { hop, host, path, query });
        }
    }
    Err(refused(format!("허용 목록 밖 {host}{path}")))
}

/// 이 홉에서 다음 홉으로 갈 수 있는 종류.
pub fn next_hops(from: Hop) -> &'static [Hop] {
    match from {
        Hop::Feed => &[Hop::Feed],
        Hop::AssetFirst => &[Hop::AssetFirst, Hop::AssetRedirect],
        Hop::AssetRedirect => &[Hop::AssetRedirect],
    }
}

/// redirect `Location` 재대조 — 상대 경로는 거부(fail-closed · 우리가 아는 호스트는 전부 절대 경로를 준다).
/// `hops_so_far` = 지금까지 따라간 홉 수(첫 요청 = 0).
pub fn check_redirect(from: Hop, location: &str, hops_so_far: usize) -> Result<CheckedUrl, UpdateErr> {
    if hops_so_far >= MAX_HOPS {
        return Err(refused(format!("redirect {MAX_HOPS}홉 초과")));
    }
    check_url(location.trim(), next_hops(from))
}

#[cfg(test)]
mod tests {
    use super::*;

    const FEED: &[Hop] = &[Hop::Feed];
    const ASSET: &[Hop] = &[Hop::AssetFirst];

    #[test]
    fn allowed_examples_pass() {
        for u in [
            "https://jarvis.godmeyou.kr/update/cysr/stable.json",
            "https://jarvis.godmeyou.kr/update/cysr/next.json.minisig",
            "https://jarvis.godmeyou.kr/update/agora-client/stable.json",
            "https://jarvis.godmeyou.kr/update/revocations.json.minisig",
            "https://jarvis.godmeyou.kr/update/cysr/releases/12.json",
            "https://jarvis.godmeyou.kr/install/agora-client-0.1.11.zip",
            "HTTPS://Jarvis.GodMeYou.KR./update/cysr/stable.json", // 스킴·호스트 대소문자·끝 점 정규화
            "https://jarvis.godmeyou.kr/update/./cysr/x/../stable.json", // . / .. 정규화
        ] {
            assert!(check_url(u, FEED).is_ok(), "{u}");
        }
        let a = check_url("https://github.com/oogisoogi/cys-ro/releases/download/v1.1.8/cysr_1.1.8_x64-setup.exe", ASSET).unwrap();
        assert_eq!(a.hop, Hop::AssetFirst);
        let r = check_redirect(
            Hop::AssetFirst,
            "https://release-assets.githubusercontent.com/github-production-release-asset/1289215339/925981fc-0a1b-4c2d-9e8f-0123456789ab?sp=r&sig=abc%2Fdef",
            1,
        )
        .unwrap();
        assert_eq!(r.hop, Hop::AssetRedirect);
        assert!(r.query.is_some());
    }

    /// §4-4 거부 사례 전부(1R BLOCK 9 · D4 단위 시험).
    #[test]
    fn refused_examples() {
        let cases: &[(&str, &[Hop])] = &[
            ("http://jarvis.godmeyou.kr/update/cysr/stable.json", FEED),          // 스킴
            ("ftp://jarvis.godmeyou.kr/update/cysr/stable.json", FEED),
            ("https://jarvis.godmeyou.kr:443/update/cysr/stable.json", FEED),     // 포트
            ("https://u:p@jarvis.godmeyou.kr/update/cysr/stable.json", FEED),     // userinfo
            ("https://93.184.216.34/update/cysr/stable.json", FEED),              // IP 리터럴
            ("https://[::1]/update/cysr/stable.json", FEED),
            ("https://jarvis.godmeyou.kr/update%2Fcysr/stable.json", FEED),       // 인코딩 구분자
            ("https://jarvis.godmeyou.kr/update/cysr%2fstable.json", FEED),
            ("https://jarvis.godmeyou.kr/update/%2e%2e/stable.json", FEED),
            ("https://jarvis.godmeyou.kr/update\\cysr/stable.json", FEED),        // 역슬래시
            ("https://jarvis.godmeyou.kr/update/cysr/stable.json?x=1", FEED),     // 쿼리(피드)
            ("https://jarvis.godmeyou.kr/update/cysr/stable.json#f", FEED),
            ("https://jarvis.godmeyou.kr/update/cysr/beta.json", FEED),           // 미지 채널
            ("https://jarvis.godmeyou.kr/update/evil/stable.json", FEED),         // 미지 부품
            ("https://jarvis.godmeyou.kr/../../etc/passwd", FEED),                // 루트 위
            ("https://jarvis.godmeyou.kr.evil.com/update/cysr/stable.json", FEED),// 접미 호스트
            ("https://evil.com/update/cysr/stable.json", FEED),
            ("https://jarvís.godmeyou.kr/update/cysr/stable.json", FEED),         // 비 ASCII(동형 문자)
            ("https://jarvis.godmeyou.kr/update/cysr/stable.json\n", FEED),       // 제어문자
            ("https://github.com/idoforgod/cys-terminal/releases/download/v0.14.43/x.zip", ASSET), // 원작자 저장소
            ("https://github.com/oogisoogi/cys-ro/releases/latest/download/latest.json", ASSET),  // latest 경로
            ("https://github.com/oogisoogi/cys-ro/releases/download/v1.1.8/a/b.zip", ASSET),       // 하위 폴더
            ("https://objects.githubusercontent.com/github-production-release-asset/1/ab", &[Hop::AssetRedirect]), // 옛 redirect 호스트
        ];
        for (u, hops) in cases {
            let e = check_url(u, hops).expect_err(u);
            assert_eq!(e.code, ErrCode::UrlRefused, "{u}");
        }
    }

    #[test]
    fn redirect_chain_rules() {
        // 피드 호스트에서 자산 호스트로 빠지는 redirect = 거부(피드는 피드로만)
        assert!(check_redirect(Hop::Feed, "https://github.com/oogisoogi/cys-ro/releases/download/v1.1.8/x.zip", 1).is_err());
        // 자산 redirect 에서 다시 1홉으로 = 거부
        assert!(check_redirect(Hop::AssetRedirect, "https://github.com/oogisoogi/cys-ro/releases/download/v1.1.8/x.zip", 2).is_err());
        // 상대 Location = 거부
        assert!(check_redirect(Hop::AssetFirst, "/github-production-release-asset/1/ab", 1).is_err());
        // 5홉 초과 = 거부
        let ok = "https://release-assets.githubusercontent.com/github-production-release-asset/1/ab";
        assert!(check_redirect(Hop::AssetRedirect, ok, 4).is_ok());
        assert!(check_redirect(Hop::AssetRedirect, ok, 5).is_err());
    }
}
