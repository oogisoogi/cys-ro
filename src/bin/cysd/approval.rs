//! HMAC signed-prefix 승인 primitive (규약→기술 강제 ①).
//!
//! 자율주행 denylist 위험명령의 "1회 승인"을 `command_prefix + cwd + environment`에 대한
//! HMAC-SHA256 서명 레코드로 영속하고, 이후 동일 prefix 명령은 서명 검증으로만 자동 통과시킨다.
//! 시크릿 없이는 레코드를 위조할 수 없으므로(서명 불일치 hard-reject) 승인은 암호학적으로
//! 위조 불가능하다. base64·HMAC-SHA256은 외부 crate 0(sha2 0.10만)으로 수동 구현한다 —
//! recall.rs:hash_step의 Sha256 패턴을 ipad/opad로 확장. RFC 4231 KAT로 정확성을 박제한다.

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::path::PathBuf;

// ── 자료구조 ────────────────────────────────────────────────────────────────

/// 서명된 명령 접두 승인 레코드(한 기계 안에서 쓰는 형식).
/// environment 는 정렬된 Vec<(String,String)> — JSON 맵의 키 순서에 기대지 않아야 같은 레코드가
/// 언제나 같은 서명 원문을 만든다(결정론 서명의 핵심).
#[derive(Clone, Serialize, Deserialize)]
pub struct ApprovalRecord {
    pub version: u32,
    pub id: String,
    pub command_prefix: Vec<String>, // 빈 벡터 금지(폴백 차단)
    pub cwd: Option<String>,         // normalized
    pub environment: Vec<(String, String)>, // 정렬·민감키 drop 후
    pub created_at: f64,
    pub updated_at: f64,
    pub signature: String, // base64(HMAC-SHA256(payload))
}

// ── 수동 base64 (표준 알파벳, 의존 0) ─────────────────────────────────────────

const B64_ALPHABET: &[u8; 64] =
    b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

/// 표준 base64 인코딩(패딩 `=` 포함). 서명 직렬화·HMAC 출력 인코딩 전용.
pub fn b64_encode(input: &[u8]) -> String {
    let mut out = String::with_capacity(input.len().div_ceil(3) * 4);
    for chunk in input.chunks(3) {
        let b0 = chunk[0] as u32;
        let b1 = *chunk.get(1).unwrap_or(&0) as u32;
        let b2 = *chunk.get(2).unwrap_or(&0) as u32;
        let n = (b0 << 16) | (b1 << 8) | b2;
        out.push(B64_ALPHABET[((n >> 18) & 0x3f) as usize] as char);
        out.push(B64_ALPHABET[((n >> 12) & 0x3f) as usize] as char);
        if chunk.len() > 1 {
            out.push(B64_ALPHABET[((n >> 6) & 0x3f) as usize] as char);
        } else {
            out.push('=');
        }
        if chunk.len() > 2 {
            out.push(B64_ALPHABET[(n & 0x3f) as usize] as char);
        } else {
            out.push('=');
        }
    }
    out
}

/// 표준 base64 디코딩(패딩 허용·내부 공백 무시). 잘못된 문자가 있으면 None.
pub fn b64_decode(input: &str) -> Option<Vec<u8>> {
    fn val(c: u8) -> Option<u32> {
        match c {
            b'A'..=b'Z' => Some((c - b'A') as u32),
            b'a'..=b'z' => Some((c - b'a' + 26) as u32),
            b'0'..=b'9' => Some((c - b'0' + 52) as u32),
            b'+' => Some(62),
            b'/' => Some(63),
            _ => None,
        }
    }
    let mut symbols: Vec<u32> = Vec::with_capacity(input.len());
    let mut pad = 0usize;
    let mut seen_pad = false;
    for &c in input.as_bytes() {
        match c {
            b'\n' | b'\r' | b' ' | b'\t' => continue,
            b'=' => {
                pad += 1;
                seen_pad = true;
            }
            _ => {
                if seen_pad {
                    return None; // 패딩 뒤 데이터 = 손상
                }
                symbols.push(val(c)?);
            }
        }
    }
    if (symbols.len() + pad) % 4 != 0 {
        return None;
    }
    let mut out = Vec::with_capacity(symbols.len() / 4 * 3);
    for chunk in symbols.chunks(4) {
        let n = (chunk[0] << 18)
            | (chunk.get(1).copied().unwrap_or(0) << 12)
            | (chunk.get(2).copied().unwrap_or(0) << 6)
            | chunk.get(3).copied().unwrap_or(0);
        out.push(((n >> 16) & 0xff) as u8);
        if chunk.len() > 2 {
            out.push(((n >> 8) & 0xff) as u8);
        }
        if chunk.len() > 3 {
            out.push((n & 0xff) as u8);
        }
    }
    Some(out)
}

// ── 수동 HMAC-SHA256 (recall.rs:hash_step 확장 — ipad/opad, 의존 0) ────────────

/// HMAC-SHA256(RFC 2104). 키>64B면 sha256(key)로 축약, 키<64B면 0패딩.
/// RFC 4231 KAT(hmac_kat 테스트)가 정확성을 증명한다 — KAT 실패=구현 버그.
pub fn hmac_sha256(secret: &[u8], msg: &[u8]) -> [u8; 32] {
    const BLOCK: usize = 64;
    let mut key = [0u8; BLOCK];
    if secret.len() > BLOCK {
        let h: [u8; 32] = {
            let mut s = Sha256::new();
            s.update(secret);
            s.finalize().into()
        };
        key[..32].copy_from_slice(&h);
    } else {
        key[..secret.len()].copy_from_slice(secret);
    }
    let mut ipad = [0x36u8; BLOCK];
    let mut opad = [0x5cu8; BLOCK];
    for i in 0..BLOCK {
        ipad[i] ^= key[i];
        opad[i] ^= key[i];
    }
    let inner: [u8; 32] = {
        let mut s = Sha256::new();
        s.update(ipad);
        s.update(msg);
        s.finalize().into()
    };
    let outer: [u8; 32] = {
        let mut s = Sha256::new();
        s.update(opad);
        s.update(inner);
        s.finalize().into()
    };
    outer
}

/// 상수시간 바이트 비교 — 서명 검증의 조기반환 타이밍 사이드채널 차단.
/// 길이 다르면 즉시 false(길이는 비밀이 아님), 같으면 전 바이트 XOR 누적 후 0 판정.
fn constant_time_eq(a: &[u8], b: &[u8]) -> bool {
    if a.len() != b.len() {
        return false;
    }
    let mut diff = 0u8;
    for i in 0..a.len() {
        diff |= a[i] ^ b[i];
    }
    diff == 0
}

// ── 결정론 직렬화 + 서명/검증 ─────────────────────────────────────────────────

impl ApprovalRecord {
    /// 서명 원문 — 7줄 `이름=값`, 줄 사이는 `\n`(끝 줄바꿈 없음). 문자열 값은 전부 base64 로 싸서
    /// 따옴표·등호·쉼표·줄바꿈으로 칸 경계를 흉내 내는 위조를 막는다.
    ///
    /// ★이 형식(칸 이름·순서·구분자·숫자 표기)은 **디스크에 있는 모든 승인 레코드의 계약**이다. 한 글자만
    /// 바뀌어도 기존 승인 서명이 전부 거부된다 — 바꾸지 마라(시험 `golden_signing_payload_and_signature_bytes_are_frozen`).
    /// (TICKET=cysr-117-impl-lead ⑲: 우리 방식으로 재작성 · 원문 바이트 불변.)
    pub fn signing_payload(&self) -> Vec<u8> {
        fn b64_joined<'a>(parts: impl Iterator<Item = &'a str>) -> String {
            parts.map(|p| b64_encode(p.as_bytes())).collect::<Vec<_>>().join(",")
        }
        let env = self
            .environment
            .iter() // sort_norm_env 가 정렬을 보장한다
            .map(|(k, v)| format!("{}={}", b64_encode(k.as_bytes()), b64_encode(v.as_bytes())))
            .collect::<Vec<_>>()
            .join(",");
        let lines: [(&str, String); 7] = [
            ("version", self.version.to_string()),
            ("id", self.id.clone()),
            ("commandPrefix", b64_joined(self.command_prefix.iter().map(String::as_str))),
            ("cwd", b64_joined(self.cwd.as_deref().into_iter())),
            ("environment", env),
            ("createdAt", self.created_at.to_string()),
            ("updatedAt", self.updated_at.to_string()),
        ];
        let mut out = String::new();
        for (i, (name, value)) in lines.iter().enumerate() {
            if i > 0 {
                out.push('\n');
            }
            out.push_str(name);
            out.push('=');
            out.push_str(value);
        }
        out.into_bytes()
    }

    pub fn sign(&mut self, secret: &[u8]) {
        self.signature = b64_encode(&hmac_sha256(secret, &self.signing_payload()));
    }

    /// 상수시간 비교로 서명 검증 — 재서명 후 동치 비교(타이밍릭 차단).
    pub fn has_valid_signature(&self, secret: &[u8]) -> bool {
        let expect = b64_encode(&hmac_sha256(secret, &self.signing_payload()));
        constant_time_eq(self.signature.as_bytes(), expect.as_bytes())
    }

    /// 명령이 이 레코드 prefix에 매칭하는가: prefix가 명령 토큰의 정확한 접두 + cwd 완전일치
    /// + environment 부분집합(레코드 env가 호출 env에 모두 포함). 빈 prefix·미닫힌 따옴표 거부.
    pub fn matches(&self, command: &str, cwd: Option<&str>, env: &[(String, String)]) -> bool {
        if self.command_prefix.is_empty() {
            return false; // 폴백 차단
        }
        let Some(toks) = tokenize(command) else {
            return false; // 미닫힌 따옴표 = prefix injection 차단
        };
        if toks.len() < self.command_prefix.len() {
            return false;
        }
        if toks[..self.command_prefix.len()] != self.command_prefix[..] {
            return false;
        }
        if let Some(rc) = &self.cwd {
            if normalize_cwd(cwd).as_deref() != Some(rc.as_str()) {
                return false;
            }
        }
        // environment 부분집합: 레코드의 (민감키 drop·정렬된) env 항목이 모두 호출 env에 존재.
        // 호출 측이 추가 env를 더 가져도 매칭(미세 변동 내성) — 단 레코드가 요구한 키-값은 강제.
        let call_env = sort_norm_env(env);
        self.environment
            .iter()
            .all(|kv| call_env.binary_search(kv).is_ok())
    }
}

/// 서명 유효 + 매칭 레코드 중 최장 prefix(동률은 updated_at 최신) 선택.
pub fn best_match<'a>(
    records: &'a [ApprovalRecord],
    secret: &[u8],
    command: &str,
    cwd: Option<&str>,
    env: &[(String, String)],
) -> Option<&'a ApprovalRecord> {
    records
        .iter()
        .filter(|r| r.has_valid_signature(secret)) // 서명 유효만
        .filter(|r| r.matches(command, cwd, env))
        .max_by(|a, b| {
            a.command_prefix
                .len()
                .cmp(&b.command_prefix.len())
                .then(
                    a.updated_at
                        .partial_cmp(&b.updated_at)
                        .unwrap_or(std::cmp::Ordering::Equal),
                )
        })
}

/// approval.check 의 매칭 갱신 — `best_match` 가 **현재 키로 검증한 바로 그 기록(위치)** 만 updated_at 갱신·재서명한다.
/// A1(1.1.7 fix-blockers · codex 2R Q3-8): id 로 다시 찾으면 같은 id 의 앞선 옛(다른 키) 기록을 새 키로 재서명할 수 있다
/// (옛 승인 자동 재서명 금지). 반환 = (id, prefix) · 매칭 없음 = None(무변경).
pub fn touch_best_match(
    records: &mut [ApprovalRecord],
    secret: &[u8],
    command: &str,
    cwd: Option<&str>,
    env: &[(String, String)],
) -> Option<(String, Vec<String>)> {
    let m = best_match(records, secret, command, cwd, env)?;
    let idx = records.iter().position(|r| std::ptr::eq(r, m))?;
    let r = &mut records[idx];
    r.updated_at = crate::state::now_epoch();
    r.sign(secret);
    Some((r.id.clone(), r.command_prefix.clone()))
}

// ── 토큰화 / 정규화 / 민감 env ─────────────────────────────────────────────────

/// 명령 문자열을 셸처럼 낱말로 나눈다 — 승인 접두 비교의 재료.
///
/// 규칙(POSIX 셸의 근사 · TICKET=cysr-117-impl-lead ⑲ 재작성 · 진리표 = 시험 `golden_tokenize_table_is_frozen`):
/// - 따옴표 밖: 공백·탭·`\n`·`\r` 이 낱말을 끊는다. `\` 는 다음 한 글자를 그대로 싣는다(맨 끝 `\` 는 버린다).
///   따옴표를 여는 순간 낱말이 생긴다 — `''` 도 빈 낱말 하나다.
/// - 작은따옴표 안: 닫는 `'` 말고는 전부 글자 그대로(`\` 포함).
/// - 큰따옴표 안: `\` 뒤가 `"` `\` `$` `` ` `` 이면 그 글자만, 아니면 `\` 를 그대로 둔다.
/// - 따옴표가 안 닫히면 None — 접두 끼워 넣기를 막으려고 비교 자체를 거부한다.
///
/// 셸 문법 전체(파이프·`;`·`$()`)를 해석하지는 않는다 — 접두 일치로 허용 범위를 좁힐 뿐이다.
pub fn tokenize(command: &str) -> Option<Vec<String>> {
    #[derive(Clone, Copy, PartialEq)]
    enum Mode {
        Bare,
        Single,
        Double,
    }
    let mut words: Vec<String> = Vec::new();
    let mut word = String::new();
    let mut in_word = false;
    let mut mode = Mode::Bare;
    let mut it = command.chars().peekable();
    while let Some(c) = it.next() {
        match (mode, c) {
            (Mode::Single, '\'') | (Mode::Double, '"') => mode = Mode::Bare,
            (Mode::Single, _) => word.push(c),
            (Mode::Double, '\\') => match it.peek() {
                Some(&n @ ('"' | '\\' | '$' | '`')) => {
                    word.push(n);
                    it.next();
                }
                _ => word.push('\\'),
            },
            (Mode::Double, _) => word.push(c),
            (Mode::Bare, '\'') => {
                mode = Mode::Single;
                in_word = true;
            }
            (Mode::Bare, '"') => {
                mode = Mode::Double;
                in_word = true;
            }
            (Mode::Bare, '\\') => {
                if let Some(n) = it.next() {
                    word.push(n);
                    in_word = true;
                }
            }
            (Mode::Bare, ' ' | '\t' | '\n' | '\r') => {
                if in_word {
                    words.push(std::mem::take(&mut word));
                    in_word = false;
                }
            }
            (Mode::Bare, _) => {
                word.push(c);
                in_word = true;
            }
        }
    }
    if mode != Mode::Bare {
        return None;
    }
    if in_word {
        words.push(word);
    }
    Some(words)
}

/// cwd 정규화 — tilde 확장 + 후행 슬래시 제거. 단일머신 전제(symlink 정규화는 비용·미사용).
pub fn normalize_cwd(cwd: Option<&str>) -> Option<String> {
    let raw = cwd?;
    let expanded = if let Some(rest) = raw.strip_prefix("~/") {
        if let Some(home) = dirs::home_dir() {
            home.join(rest).to_string_lossy().to_string()
        } else {
            raw.to_string()
        }
    } else if raw == "~" {
        dirs::home_dir()
            .map(|h| h.to_string_lossy().to_string())
            .unwrap_or_else(|| raw.to_string())
    } else {
        raw.to_string()
    };
    let trimmed = expanded.trim_end_matches('/');
    Some(if trimmed.is_empty() {
        "/".to_string()
    } else {
        trimmed.to_string()
    })
}

/// 민감한 환경변수를 빼고(서명 원문에 비밀값을 싣지 않는다) 키 순으로 정렬한다(결정론 ·
/// `matches` 의 binary_search 전제). 키를 대문자로 바꿔 아래 낱말이 **들어 있기만** 해도 뺀다.
pub fn sort_norm_env(env: &[(String, String)]) -> Vec<(String, String)> {
    const SENSITIVE: &[&str] = &[
        "API_KEY",
        "ACCESS_KEY",
        "AUTH_TOKEN",
        "BEARER_TOKEN",
        "PRIVATE_KEY",
        "PASSWORD",
        "PASSWD",
        "SECRET",
        "TOKEN",
        "CREDENTIAL",
        "COOKIE",
    ];
    let mut out: Vec<(String, String)> = env
        .iter()
        .filter(|(k, _)| {
            let up = k.to_uppercase();
            !SENSITIVE.iter().any(|s| up.contains(s))
        })
        .cloned()
        .collect();
    out.sort();
    out
}

// ── 서명 키 저장 (운영체제 키체인 대신 0600 파일 — 외부 crate 없이) ─────────────

const ENV_SECRET_B64: &str = "CYS_APPROVAL_SECRET_B64";

/// 시크릿 파일 경로: ~/.cys/.approval-secret — pack(~/.cys/pack) 밖, ~/.cys/ 직하.
/// pack은 배포·git 추적 대상일 수 있으므로 시크릿이 새지 않게 분리한다.
fn secret_path() -> PathBuf {
    dirs::home_dir()
        .unwrap_or_else(|| PathBuf::from("."))
        .join(".cys")
        .join(".approval-secret")
}

/// 승인 레코드 영속 경로: ~/.cys/approvals.json (0600).
fn records_path() -> PathBuf {
    dirs::home_dir()
        .unwrap_or_else(|| PathBuf::from("."))
        .join(".cys")
        .join("approvals.json")
}

/// 우선순위: ① env override(B64, 로깅 금지) → ② 0600 파일 → ③ **파일이 없을 때만** 생성·0600 저장.
///
/// ⑨(TICKET=cysr-117-impl-lead · MUST-DO-117 ⑨ · 원작자 8be494d1 의 우리 판 재구현) 키 파일이
/// **있는데** 못 읽거나(권한·백신 잠금) 비어 있으면 새 키로 덮지 않고 None(= 호출부 fail-closed:
/// 미승인 취급)을 돌린다. 종전엔 새 키를 같은 경로에 써서 기존 승인 서명이 전부 무효가 됐다
/// (가드 훅이 `approval check` 를 자동으로 부르므로 사람 조작 없이도 났다).
pub fn signing_secret() -> Option<Vec<u8>> {
    // ① env override(B64) — 로깅·이벤트 payload에 절대 미포함.
    if let Ok(b64) = std::env::var(ENV_SECRET_B64) {
        if let Some(d) = b64_decode(&b64) {
            if !d.is_empty() {
                return Some(d);
            }
        }
    }
    signing_secret_at(&secret_path())
}

/// ②③ 파일 경로 판(시험 주입용).
///
/// A1-F1(1.1.7 fix-blockers · codex 1R·2R 차단 수리): **정확히 0바이트** 키 파일은 지킬 키가 없는 파일이라
/// 부재와 같이 새 키를 게시한다(v1.1.6 자가 치유 복원 · 영구 미승인 회귀 금지). 비어 있지 않은 바이트 = 키(기존 계약),
/// 읽기 오류 = None·무변경(⑨ 그대로). 생성·복구는 전부 한 규약: **키 전용 프로세스 간 잠금**(`<p>.cys-lock` ·
/// std `File::lock` = 유닉스 flock / 윈 LockFileEx) → 잠금 안 재판독 → 완성 임시 키(0600·sync) → 게시 → 재판독 확인.
/// 잠금을 못 잡으면 만들지 않는다(무잠금 폴백 = 신판끼리 「반환 키 ≠ 경로 키」 경합 · codex 2R ①).
/// 게시·확인 실패 = None(「세션 한정 키」 반환 없음 — 호출마다 다른 키라 서명이 영영 안 맞는다 · codex 2R (b)).
/// ⚠구판(1.1.6 이하) 데몬은 이 잠금을 모르고 `fs::write` 로 직접 쓴다 — 갱신 뒤 구판 데몬 종료가 전제다.
fn signing_secret_at(path: &std::path::Path) -> Option<Vec<u8>> {
    match std::fs::read(path) {
        Ok(d) if !d.is_empty() => return Some(d),
        Ok(_) => {} // 0바이트 = 아래 잠금 안에서 다시 판정
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => {}
        Err(e) => {
            eprintln!("[cysd] approval: 서명 키 파일 읽기 실패({e}) — 새 키로 덮지 않는다(미승인 취급)");
            return None;
        }
    }
    let dir = path.parent().unwrap_or(std::path::Path::new("."));
    if let Err(e) = std::fs::create_dir_all(dir) {
        eprintln!("[cysd] approval: 서명 키 폴더 준비 실패({e}) — 키를 만들지 않는다(미승인 취급)");
        return None;
    }
    #[cfg(test)]
    tests::run_hook(path, "prelock");
    let Some(_key_lock) = lock_key_exclusive(path) else {
        eprintln!("[cysd] approval: 서명 키 잠금 실패 — 키를 만들지 않는다(미승인 취급)");
        return None;
    };
    // 잠금 안 재판독 — 그 사이 다른 데몬이 게시했으면 그 키.
    let was_empty = match std::fs::read(path) {
        Ok(d) if !d.is_empty() => return Some(d),
        Ok(_) => true,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => false,
        Err(e) => {
            eprintln!("[cysd] approval: 서명 키 파일 읽기 실패({e}) — 새 키로 덮지 않는다(미승인 취급)");
            return None;
        }
    };
    #[cfg(test)]
    tests::run_hook(path, "publish");
    let secret = random_32()?;
    // tmp 이름 = pid + 프로세스 안 순번(같은 데몬의 두 스레드가 같은 tmp 를 덮지 않게).
    static TMP_SEQ: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(0);
    let tmp = dir.join(format!(
        ".approval-secret.tmp-{}-{}",
        std::process::id(),
        TMP_SEQ.fetch_add(1, std::sync::atomic::Ordering::Relaxed)
    ));
    #[cfg(test)]
    tests::run_tmp_hook(path, &tmp);
    // 임시 키 실패는 게시 충돌과 섞지 않는다 — 만들지 못했으면(남의 잔재 등) 건드리지 않고, 만든 뒤 실패면 내 것만 지운다.
    if let Err(e) = write_key_tmp(&tmp, &secret, path) {
        eprintln!("[cysd] approval: 서명 임시 키 작성 실패({e}) — 미승인 취급");
        return None;
    }
    // 게시: Ok(true) = 부재 게시가 선점에 막힘(hard_link AlreadyExists — 덮지 않고 ⑥ 에서 경로의 키).
    let publish: std::io::Result<bool> = match fail_point(path, "publish") {
        Some(e) => Err(e),
        None if was_empty => std::fs::rename(&tmp, path).map(|()| false), // 0바이트 → 원자 교체
        None => match std::fs::hard_link(&tmp, path) {
            Ok(()) => Ok(false),
            Err(e) if e.kind() == std::io::ErrorKind::AlreadyExists => Ok(true),
            // 하드링크를 못 쓰는 FS 등: 잠금 안 원자 교체(참여자끼리는 닫힘 · 비참여 writer 보존은 보장 밖).
            Err(_) => std::fs::rename(&tmp, path).map(|()| false),
        },
    };
    match std::fs::remove_file(&tmp) {
        Err(e) if e.kind() != std::io::ErrorKind::NotFound => {
            eprintln!("[cysd] approval: 서명 임시 키 정리 실패({e}) — {}", tmp.display());
        }
        _ => {}
    }
    if let Err(e) = publish {
        eprintln!("[cysd] approval: 서명 키 게시 실패({e}) — 미승인 취급");
        return None;
    }
    // 게시 뒤 경로를 다시 읽어 확인한다 — 경로의 키만 돌려준다(반환 키 == 경로 키). 잠금은 여기까지 쥐지만,
    // 게시 뒤 참여자는 잠금 없는 첫 판독에서 키를 읽으므로 ⑥ 구간 보유는 참여자끼리의 정확성 조건이 아니다.
    let reread = match fail_point(path, "verify") {
        Some(e) => Err(e),
        None => std::fs::read(path),
    };
    match reread {
        Ok(d) if d == secret => Some(secret),
        Ok(d) if !d.is_empty() => Some(d), // 비참여 writer 가 먼저 게시(선점) — 경로의 키로 수렴
        _ => {
            eprintln!("[cysd] approval: 서명 키 게시 확인 실패 — 미승인 취급");
            None
        }
    }
}

/// 시험 전용 실패 주입점(경로·단계별) — 운영 빌드에서는 언제나 None.
fn fail_point(path: &std::path::Path, stage: &str) -> Option<std::io::Error> {
    #[cfg(test)]
    {
        tests::injected_failure(path, stage)
    }
    #[cfg(not(test))]
    {
        let _ = (path, stage);
        None
    }
}

/// 키 전용 프로세스 간 배타 잠금(`<p>.cys-lock`). 유닉스 = flock 이라 같은 이름을 쓰는 `pack::acquire_settings_lock`
/// 과도 서로 배제된다. 실패(파일 못 엶·잠금 오류) = None — 호출부는 쓰지 않는다.
fn lock_key_exclusive(path: &std::path::Path) -> Option<std::fs::File> {
    let lp = std::path::PathBuf::from(format!("{}.cys-lock", path.display()));
    let f = std::fs::OpenOptions::new().create(true).write(true).open(&lp).ok()?;
    if let Some(e) = fail_point(path, "lock") {
        let _ = e;
        return None;
    }
    f.lock().ok()?;
    Some(f)
}

/// 완성 임시 키: 새 파일(create_new · 이미 있으면 Err = 남의 것 · 건드리지 않음) · 0600(유닉스 · 실패 = Err) ·
/// 전량 쓰기 · sync_all. 연 뒤의 실패는 **이 호출이 만든 임시 파일만** 지우고 Err.
fn write_key_tmp(tmp: &std::path::Path, secret: &[u8], key: &std::path::Path) -> std::io::Result<()> {
    use std::io::Write;
    let mut o = std::fs::OpenOptions::new();
    o.write(true).create_new(true);
    #[cfg(unix)]
    {
        use std::os::unix::fs::OpenOptionsExt;
        o.mode(0o600);
    }
    let mut f = o.open(tmp)?;
    let r = (|| {
        if let Some(e) = fail_point(key, "tmp_perm") {
            return Err(e);
        }
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            f.set_permissions(std::fs::Permissions::from_mode(0o600))?;
        }
        if let Some(e) = fail_point(key, "tmp_write") {
            return Err(e);
        }
        f.write_all(secret)?;
        if let Some(e) = fail_point(key, "tmp_sync") {
            return Err(e);
        }
        f.sync_all()
    })();
    if r.is_err() {
        drop(f);
        let _ = std::fs::remove_file(tmp);
    }
    r
}

/// ⑨(Fable R1 #1) approvals.json 읽기→변경→저장 직렬화 락 — 본부·부서 데몬이 같은 파일을 쓴다.
/// 돌려받은 핸들을 **이름 있는 바인딩**으로 RMW 끝까지 쥐어라(drop = 해제 · 윈도 = 기존 헬퍼대로 None).
pub fn lock_records() -> Option<std::fs::File> {
    cys::pack::acquire_settings_lock(&records_path())
}

/// 0600 권한 부여(Unix). Windows는 ACL 미설정(단일 사용자 데스크톱 전제).
fn set_owner_only(path: &PathBuf) {
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        let _ = std::fs::set_permissions(path, std::fs::Permissions::from_mode(0o600));
    }
    #[cfg(not(unix))]
    {
        let _ = path; // no-op
    }
}

/// 32바이트 난수. Unix=/dev/urandom 직접 read(getrandom/OsRng crate 부재).
/// 비-Unix는 시간 기반 PRNG 폴백(단일 데스크톱 전제 — 위협모델상 허용, 명문화).
fn random_32() -> Option<Vec<u8>> {
    #[cfg(unix)]
    {
        // ★/dev/urandom은 무한 스트림 — std::fs::read(전체 읽기)는 EOF가 없어 영영 반환하지
        //   않는다(hang+무한메모리). 반드시 read_exact로 32바이트만 채운다.
        use std::io::Read;
        if let Ok(mut f) = std::fs::File::open("/dev/urandom") {
            let mut buf = [0u8; 32];
            if f.read_exact(&mut buf).is_ok() {
                return Some(buf.to_vec());
            }
        }
        // /dev/urandom 읽기 실패(컨테이너 등) — 아래 폴백으로.
    }
    // 폴백: 시간+pid 기반 SHA256(약한 엔트로피 — Unix urandom 실패 시 한정).
    let seed = format!(
        "{}-{}-{:?}",
        std::process::id(),
        crate::state::now_epoch(),
        std::time::SystemTime::now()
    );
    let mut s = Sha256::new();
    s.update(seed.as_bytes());
    let h: [u8; 32] = s.finalize().into();
    Some(h.to_vec())
}

// ── 레코드 영속 (JSON 0600, atomic tmp+rename) ────────────────────────────────

/// 저장 형식: `{"records":[...]}`(현행 쓰기 형식) 또는 최상위 배열(옛 형식) 둘 다 읽는다.
///
/// ⑨(TICKET=cysr-117-impl-lead) 파일 부재만 빈 목록 · 읽기·해석 실패는 Err — 호출부는 저장하지
/// 않는다. 종전엔 실패를 빈 목록으로 접어 `approval.sign` 이 새 1건만 남기고 기존 승인을 덮었다.
pub fn load_records() -> Result<Vec<ApprovalRecord>, String> {
    load_records_at(&records_path())
}

fn load_records_at(path: &std::path::Path) -> Result<Vec<ApprovalRecord>, String> {
    let content = match std::fs::read_to_string(path) {
        Ok(c) => c,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(Vec::new()),
        Err(e) => return Err(format!("{} 읽기 실패({e})", path.display())),
    };
    // A1-F2(1.1.7 fix-blockers · codex 1R): **정확히 0바이트**만 빈 목록 — 지킬 기록이 없는 파일이라 v1.1.6 처럼
    // 이후 저장이 가능해야 한다(영구 records_unreadable 회귀 금지). 공백·BOM 만·손상은 아래 해석 실패 = Err 그대로.
    if content.is_empty() {
        return Ok(Vec::new());
    }
    // 선두 BOM 하나만 벗기고 해석한다(부서 목록 판독과 같은 규칙) — BOM 파일 전체를 빈 목록으로 접지 않는다.
    let content = content.strip_prefix('\u{feff}').unwrap_or(&content);
    // ① {"records":[...]} 형태
    if let Ok(v) = serde_json::from_str::<serde_json::Value>(&content) {
        if let Some(arr) = v.get("records") {
            if let Ok(recs) = serde_json::from_value::<Vec<ApprovalRecord>>(arr.clone()) {
                return Ok(recs);
            }
        }
    }
    // ② bare 배열
    serde_json::from_str::<Vec<ApprovalRecord>>(&content)
        .map_err(|e| format!("{} 해석 실패({e})", path.display()))
}

/// atomic write: tmp 작성·0600 부여 후 rename. 디렉토리 자동 생성.
pub fn save_records(records: &[ApprovalRecord]) -> Result<(), String> {
    save_records_at(&records_path(), records)
}

fn save_records_at(path: &std::path::Path, records: &[ApprovalRecord]) -> Result<(), String> {
    let path = path.to_path_buf();
    if let Some(dir) = path.parent() {
        std::fs::create_dir_all(dir).map_err(|e| e.to_string())?;
    }
    let body = serde_json::to_string_pretty(&serde_json::json!({"records": records}))
        .map_err(|e| e.to_string())?;
    // ⑨(Fable R1 #1) tmp 이름 = pid+순번 — 고정 이름은 두 데몬이 같은 tmp 를 서로 잘라 먹는다.
    static SAVE_SEQ: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(0);
    let tmp = path.with_extension(format!(
        "json.tmp-{}-{}",
        std::process::id(),
        SAVE_SEQ.fetch_add(1, std::sync::atomic::Ordering::Relaxed)
    ));
    std::fs::write(&tmp, body.as_bytes()).map_err(|e| e.to_string())?;
    set_owner_only(&tmp);
    if let Err(e) = std::fs::rename(&tmp, &path) {
        let _ = std::fs::remove_file(&tmp);
        return Err(e.to_string());
    }
    set_owner_only(&path);
    Ok(())
}

/// 신규 레코드 id 생성: epoch초 + 프로세스 카운터(동일 초 충돌 차단).
pub fn new_record_id() -> String {
    use std::sync::atomic::{AtomicU64, Ordering};
    static COUNTER: AtomicU64 = AtomicU64::new(0);
    format!(
        "ap-{}-{}-{}",
        std::process::id(),
        crate::state::now_epoch() as u64,
        COUNTER.fetch_add(1, Ordering::Relaxed),
    )
}

/// JSON 객체 {"K":"V",...}를 정렬·민감키 drop된 Vec<(String,String)>로 — RPC env 파라미터 정규화.
pub fn env_from_json(v: &serde_json::Value) -> Vec<(String, String)> {
    let raw: Vec<(String, String)> = v
        .as_object()
        .map(|m| {
            m.iter()
                .filter_map(|(k, val)| val.as_str().map(|s| (k.clone(), s.to_string())))
                .collect()
        })
        .unwrap_or_default();
    sort_norm_env(&raw)
}

// ── 테스트 (E-n: 10종, hmac_kat = RFC 4231) ──────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    const SECRET: &[u8] = b"test-approval-secret-32-bytes!!!";

    fn rec(prefix: &[&str], cwd: Option<&str>, env: &[(&str, &str)]) -> ApprovalRecord {
        ApprovalRecord {
            version: 1,
            id: "ap-test-1".to_string(),
            command_prefix: prefix.iter().map(|s| s.to_string()).collect(),
            cwd: cwd.map(|c| c.to_string()),
            environment: sort_norm_env(
                &env.iter()
                    .map(|(k, v)| (k.to_string(), v.to_string()))
                    .collect::<Vec<_>>(),
            ),
            created_at: 1000.0,
            updated_at: 1000.0,
            signature: String::new(),
        }
    }

    /// ⑲(TICKET=cysr-117-impl-lead) 재작성 전 골든 핀 — 서명 원문 바이트·서명값은 **디스크에 있는 모든
    /// 승인 레코드의 계약**이다. 기대값은 코드가 아니라 파이썬 hmac/base64 로 독립 계산했다. 한 바이트라도
    /// 바뀌면 참가자 기기의 기존 승인이 전부 거부된다 — 이 시험이 적색이면 재작성이 틀린 것이다.
    #[test]
    fn golden_signing_payload_and_signature_bytes_are_frozen() {
        let mut r = ApprovalRecord {
            version: 1,
            id: "rec-골든-1".into(),
            command_prefix: vec!["git".into(), "push".into(), "--force, \"x\"=1".into()],
            cwd: Some("/tmp/작업 폴더".into()),
            environment: vec![
                ("HOME".into(), "/Users/한글".into()),
                ("LANG".into(), "ko_KR.UTF-8".into()),
            ],
            created_at: 1700000000.25,
            updated_at: 1700000100.0,
            signature: String::new(),
        };
        assert_eq!(
            String::from_utf8(r.signing_payload()).unwrap(),
            "version=1\nid=rec-골든-1\ncommandPrefix=Z2l0,cHVzaA==,LS1mb3JjZSwgIngiPTE=\n\
             cwd=L3RtcC/snpHsl4Ug7Y+0642U\n\
             environment=SE9NRQ===L1VzZXJzL+2VnOq4gA==,TEFORw===a29fS1IuVVRGLTg=\n\
             createdAt=1700000000.25\nupdatedAt=1700000100"
        );
        r.sign(b"golden-secret-0123456789");
        assert_eq!(r.signature, "/eGEZxkMdIGwwAGWm/5Yh9ZfzhZee1SLfDmIKhwFggk=");
        assert!(r.has_valid_signature(b"golden-secret-0123456789"));
        let mut r2 = ApprovalRecord {
            version: 1,
            id: "r2".into(),
            command_prefix: vec!["ls".into()],
            cwd: None,
            environment: vec![],
            created_at: 0.0,
            updated_at: 0.0,
            signature: String::new(),
        };
        assert_eq!(
            String::from_utf8(r2.signing_payload()).unwrap(),
            "version=1\nid=r2\ncommandPrefix=bHM=\ncwd=\nenvironment=\ncreatedAt=0\nupdatedAt=0"
        );
        r2.sign(b"k");
        assert_eq!(r2.signature, "j3aLIBJE3b3l6T2OPdOzrBwWaASiybyBDz/+igRD+jI=");
        // 디스크 형식(두 형) 왕복: 객체형 · 최상위 배열형 모두 같은 레코드로 읽히고 서명이 산다.
        let d = tdir("golden");
        let p = d.join("approvals.json");
        let one = serde_json::to_value(&r).unwrap();
        for text in [
            serde_json::json!({"records": [one.clone()]}).to_string(),
            serde_json::json!([one.clone()]).to_string(),
        ] {
            std::fs::write(&p, text).unwrap();
            let got = load_records_at(&p).unwrap();
            assert_eq!(got.len(), 1);
            assert!(got[0].has_valid_signature(b"golden-secret-0123456789"));
            assert_eq!(got[0].signing_payload(), r.signing_payload());
        }
        let _ = std::fs::remove_dir_all(&d);
    }

    /// ⑲ 재작성 전 토큰화 진리표 핀(따옴표·백슬래시·공백·미닫힘).
    #[test]
    fn golden_tokenize_table_is_frozen() {
        let v = |xs: &[&str]| Some(xs.iter().map(|x| x.to_string()).collect::<Vec<_>>());
        let table: &[(&str, Option<Vec<String>>)] = &[
            ("git push origin main", v(&["git", "push", "origin", "main"])),
            ("  a\t b\n", v(&["a", "b"])),
            ("echo 'a b' \"c d\"", v(&["echo", "a b", "c d"])),
            ("echo ''", v(&["echo", ""])),
            ("a\\ b", v(&["a b"])),
            ("a\\", v(&["a"])),
            (r#""a\"b\\c\$d\x""#, v(&[r#"a"b\c$d\x"#])),
            (r"'a\b'", v(&[r"a\b"])),
            ("a\"b c\"d", v(&["ab cd"])),
            ("", v(&[])),
            ("\"unterminated", None),
            ("'x", None),
            ("\"a\\", None),
            ("x\r\ny", v(&["x", "y"])),
        ];
        for (input, want) in table {
            assert_eq!(&tokenize(input), want, "입력 {input:?}");
        }
    }

    /// ⑲ 재작성 전 env 정규화 핀(민감 키 부분일치 제거 · 바이트 정렬).
    #[test]
    fn golden_sort_norm_env_is_frozen() {
        let e = |k: &str, v: &str| (k.to_string(), v.to_string());
        let got = sort_norm_env(&[
            e("b", "1"),
            e("MY_TOKEN_X", "s"),
            e("a", "2"),
            e("api_key", "k"),
            e("PATH", "/bin"),
            e("cookie_jar", "c"),
            e("Passwd", "p"),
            e("aws_secret", "z"),
        ]);
        assert_eq!(got, vec![e("PATH", "/bin"), e("a", "2"), e("b", "1")]);
    }

    fn tdir(tag: &str) -> std::path::PathBuf {
        let d = std::env::temp_dir().join(format!(
            "cys-appr-{tag}-{}-{}",
            std::process::id(),
            crate::state::now_epoch().to_bits()
        ));
        let _ = std::fs::remove_dir_all(&d);
        std::fs::create_dir_all(&d).unwrap();
        d
    }

    /// ⑨(TICKET=cysr-117-impl-lead) 서명 키는 **없을 때만** 만든다 — 있는데 못 읽거나 비어 있으면
    /// None(fail-closed) · 디스크 무변경. 종전(읽기 실패 → 새 키 덮기)으로 되돌리면 적색.
    #[test]
    fn signing_secret_never_overwrites_existing_unreadable_key_but_recovers_zero_bytes() {
        let d = tdir("key");
        let p = d.join(".approval-secret");
        let k1 = signing_secret_at(&p).expect("부재 = 생성");
        assert_eq!(k1.len(), 32);
        assert_eq!(std::fs::read(&p).unwrap(), k1, "게시된 키 = 반환 키");
        assert_eq!(signing_secret_at(&p).unwrap(), k1, "재호출 = 같은 키");
        // A1-F1(1.1.7 fix-blockers): 0바이트만은 지킬 키가 없다 — 새 키를 게시한다(v1.1.6 자가 치유 복원).
        std::fs::write(&p, b"").unwrap();
        let k0 = signing_secret_at(&p).expect("0바이트 키 파일이 영구 미승인으로 남았다");
        assert_eq!(k0.len(), 32);
        assert_ne!(k0, k1);
        assert_eq!(std::fs::read(&p).unwrap(), k0, "게시된 키 = 반환 키");
        assert_eq!(signing_secret_at(&p).unwrap(), k0, "재호출 = 같은 키");
        // 비어 있지 않은 바이트 = 키(기존 계약) — 공백이어도 덮지 않는다.
        std::fs::write(&p, b" \n").unwrap();
        assert_eq!(signing_secret_at(&p).unwrap(), b" \n");
        assert_eq!(std::fs::read(&p).unwrap(), b" \n", "비어 있지 않은 키 파일이 덮였다");
        std::fs::remove_file(&p).unwrap();
        std::fs::create_dir_all(&p).unwrap(); // 읽기 오류
        assert!(signing_secret_at(&p).is_none());
        assert!(p.is_dir(), "읽기 오류 자리가 바뀌었다");
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            std::fs::remove_dir_all(&p).unwrap();
            std::fs::write(&p, &k1).unwrap();
            std::fs::set_permissions(&p, std::fs::Permissions::from_mode(0o000)).unwrap();
            if std::fs::read(&p).is_err() {
                assert!(signing_secret_at(&p).is_none(), "권한 거부 = 미승인 취급");
                std::fs::set_permissions(&p, std::fs::Permissions::from_mode(0o600)).unwrap();
                assert_eq!(std::fs::read(&p).unwrap(), k1, "권한 거부 키가 덮였다");
            }
        }
        let _ = std::fs::remove_dir_all(&d);
    }

    /// ⑨ 여러 데몬이 동시에 처음 만들어도 게시된 키 하나로 수렴한다(덮어쓰지 않는 게시).
    #[test]
    fn signing_secret_concurrent_first_creation_converges_to_one_key() {
        let d = tdir("race");
        let p = d.join(".approval-secret");
        let hs: Vec<_> = (0..8)
            .map(|_| {
                let p = p.clone();
                std::thread::spawn(move || signing_secret_at(&p).unwrap())
            })
            .collect();
        let keys: Vec<Vec<u8>> = hs.into_iter().map(|h| h.join().unwrap()).collect();
        let disk = std::fs::read(&p).unwrap();
        assert!(keys.iter().all(|k| *k == disk), "스레드마다 다른 키 = 기존 승인 무효화 경합");
        let _ = std::fs::remove_dir_all(&d);
    }

    // ── A1-F1 시험 전용 중단점·실패 주입(경로·단계별 · 병렬 시험 무간섭) ──
    type Hook = std::sync::Arc<dyn Fn() + Send + Sync>;
    static HOOKS: std::sync::Mutex<Vec<(std::path::PathBuf, &'static str, Hook)>> = std::sync::Mutex::new(Vec::new());
    static FAILS: std::sync::Mutex<Vec<(std::path::PathBuf, &'static str)>> = std::sync::Mutex::new(Vec::new());

    pub(super) fn run_hook(path: &std::path::Path, stage: &str) {
        let h = HOOKS.lock().unwrap().iter().find(|(p, s, _)| p == path && *s == stage).map(|(_, _, f)| f.clone());
        if let Some(f) = h {
            f()
        }
    }

    pub(super) fn injected_failure(path: &std::path::Path, stage: &str) -> Option<std::io::Error> {
        FAILS.lock().unwrap().iter().any(|(p, s)| p == path && *s == stage)
            .then(|| std::io::Error::other(format!("injected {stage}")))
    }

    type TmpHook = std::sync::Arc<dyn Fn(&std::path::Path) + Send + Sync>;
    static TMP_HOOKS: std::sync::Mutex<Vec<(std::path::PathBuf, TmpHook)>> = std::sync::Mutex::new(Vec::new());

    pub(super) fn run_tmp_hook(path: &std::path::Path, tmp: &std::path::Path) {
        let h = TMP_HOOKS.lock().unwrap().iter().find(|(p, _)| p == path).map(|(_, f)| f.clone());
        if let Some(f) = h {
            f(tmp)
        }
    }

    /// 임시 키 이름 자리에 이미 남의 파일(비정상 종료 잔재·pid 재사용)이 있으면: 만들지 못한 것이므로 None 이고,
    /// 그 파일은 건드리지 않는다(게시 충돌로 섞어 재판독하거나 남의 임시 파일을 지우지 않는다 · codex 3R ②).
    #[test]
    fn signing_secret_foreign_tmp_is_left_alone() {
        let d = tdir("foreigntmp");
        let p = d.join(".approval-secret");
        std::fs::write(&p, b"").unwrap();
        let seen = std::sync::Arc::new(std::sync::Mutex::new(None::<std::path::PathBuf>));
        let seen2 = seen.clone();
        TMP_HOOKS.lock().unwrap().push((p.clone(), std::sync::Arc::new(move |t: &std::path::Path| {
            std::fs::write(t, b"other").unwrap();
            *seen2.lock().unwrap() = Some(t.to_path_buf());
        })));
        let got = signing_secret_at(&p);
        TMP_HOOKS.lock().unwrap().retain(|(q, _)| *q != p);
        assert!(got.is_none(), "임시 키를 만들지 못했는데 키를 돌려줬다");
        let t = seen.lock().unwrap().clone().expect("임시 경로 훅 미발화");
        assert_eq!(std::fs::read(&t).unwrap(), b"other", "남의 임시 파일을 지우거나 덮었다");
        assert_eq!(std::fs::read(&p).unwrap(), b"", "임시 키 실패인데 경로가 바뀌었다");
        let _ = std::fs::remove_dir_all(&d);
    }

    fn set_hook(p: &std::path::Path, stage: &'static str, f: Hook) {
        HOOKS.lock().unwrap().push((p.to_path_buf(), stage, f));
    }

    fn clear_hooks(p: &std::path::Path) {
        HOOKS.lock().unwrap().retain(|(q, _, _)| q != p);
        FAILS.lock().unwrap().retain(|(q, _)| q != p);
    }

    /// 첫 호출자만 세우는 중단점: (도착 신호 수신기, 풀어 주기 송신기).
    fn pause_first(p: &std::path::Path, stage: &'static str)
        -> (std::sync::mpsc::Receiver<()>, std::sync::mpsc::Sender<()>) {
        let (at_tx, at_rx) = std::sync::mpsc::channel::<()>();
        let (go_tx, go_rx) = std::sync::mpsc::channel::<()>();
        let at_tx = std::sync::Mutex::new(at_tx);
        let go_rx = std::sync::Mutex::new(go_rx);
        let fired = std::sync::atomic::AtomicBool::new(false);
        set_hook(p, stage, std::sync::Arc::new(move || {
            if fired.swap(true, std::sync::atomic::Ordering::SeqCst) {
                return; // 첫 호출자(A)만 — B 가 잠금 없이 여기 오면 그대로 지나간다(무잠금 변이를 드러냄)
            }
            let _ = at_tx.lock().unwrap().send(());
            let _ = go_rx.lock().unwrap().recv_timeout(std::time::Duration::from_secs(20));
        }));
        (at_rx, go_tx)
    }

    /// 결정적 경합: A 가 잠금 안에서 부재/0바이트를 판정하고 게시 직전에 멈춘 동안 B 가 들어오면 B 는 잠금에서
    /// 기다렸다가 A 가 게시한 키를 받는다(두 키 = 경로 키 하나). 잠금·잠금 안 재판독을 빼면 B 가 자기 키를 게시한다.
    fn locked_recovery_serializes(start_empty: bool, stage: &'static str) {
        let d = tdir(&format!("lock{}{stage}", if start_empty { "0" } else { "abs" }));
        let p = d.join(".approval-secret");
        if start_empty {
            std::fs::write(&p, b"").unwrap();
        }
        let (at_rx, go_tx) = pause_first(&p, stage);
        let pa = p.clone();
        let a = std::thread::spawn(move || signing_secret_at(&pa));
        at_rx.recv_timeout(std::time::Duration::from_secs(20)).expect("A 가 중단점에 오지 않았다");
        // B 가 잠금 진입점까지 온 것을 신호로 확인한 뒤에 「기다리는 중」 을 단언한다(스케줄 지연 거짓 초록 차단).
        let (b_rx, b_go) = pause_first(&p, "prelock");
        drop(b_go); // B 는 prelock 에서 멈추지 않는다(신호만 · recv 즉시 끊김)
        let pb = p.clone();
        let b = std::thread::spawn(move || signing_secret_at(&pb));
        b_rx.recv_timeout(std::time::Duration::from_secs(20)).expect("B 가 잠금 진입점에 오지 않았다");
        std::thread::sleep(std::time::Duration::from_millis(300));
        assert!(!b.is_finished(), "B 가 A 의 잠금({stage})을 기다리지 않고 끝났다");
        go_tx.send(()).unwrap();
        let ka = a.join().unwrap().expect("A");
        let kb = b.join().unwrap().expect("B");
        clear_hooks(&p);
        let disk = std::fs::read(&p).unwrap();
        assert_eq!(ka, disk, "A 반환 키 ≠ 경로 키");
        assert_eq!(kb, disk, "B 반환 키 ≠ 경로 키");
        let _ = std::fs::remove_dir_all(&d);
    }

    #[test]
    fn signing_secret_zero_byte_recovery_is_serialized_by_lock() {
        locked_recovery_serializes(true, "publish");
    }


    #[test]
    fn signing_secret_absent_creation_is_serialized_by_lock() {
        locked_recovery_serializes(false, "publish");
    }

    /// 비참여 writer(잠금을 모르는 구판 등)가 재판독 뒤·게시 전에 먼저 키를 쓰면, 부재 게시(hard_link)는 그 키를
    /// 덮지 않고 게시 뒤 확인이 경로의 키를 돌려준다(반환 키 == 경로 키).
    #[test]
    fn signing_secret_absent_publish_yields_to_non_participant_key() {
        let d = tdir("nonpart");
        let p = d.join(".approval-secret");
        let pw = p.clone();
        set_hook(&p, "publish", std::sync::Arc::new(move || {
            std::fs::write(&pw, [5u8; 32]).unwrap();
        }));
        let got = signing_secret_at(&p);
        clear_hooks(&p);
        assert_eq!(got.as_deref(), Some(&[5u8; 32][..]), "경로의 키가 아닌 자기 키를 돌려줬다");
        assert_eq!(std::fs::read(&p).unwrap(), vec![5u8; 32], "비참여 writer 의 키를 덮었다");
        let _ = std::fs::remove_dir_all(&d);
    }

    /// 잠금을 못 잡으면 만들지 않는다(무잠금 폴백 없음) — 부재는 그대로 부재 · 0바이트는 그대로 0바이트.
    #[test]
    fn signing_secret_lock_failure_creates_nothing() {
        let d = tdir("lockfail");
        let p = d.join(".approval-secret");
        std::fs::create_dir_all(d.join(".approval-secret.cys-lock")).unwrap(); // 잠금 파일 자리가 폴더 = 열기 실패
        assert!(signing_secret_at(&p).is_none(), "잠금 없이 키를 만들었다");
        assert!(!p.exists(), "잠금 실패인데 키 파일이 생겼다");
        std::fs::write(&p, b"").unwrap();
        assert!(signing_secret_at(&p).is_none(), "잠금 없이 0바이트를 복구했다");
        assert_eq!(std::fs::read(&p).unwrap(), b"");
        let _ = std::fs::remove_dir_all(&d);
    }

    /// 게시 실패 = None(세션 한정 키를 돌려주지 않는다) · 0바이트 그대로 · 임시 파일 잔재 없음.
    #[cfg(unix)]
    #[test]
    fn signing_secret_publish_failure_returns_none() {
        use std::os::unix::fs::PermissionsExt;
        let d = tdir("pubfail");
        let p = d.join(".approval-secret");
        std::fs::write(&p, b"").unwrap();
        std::fs::write(d.join(".approval-secret.cys-lock"), b"").unwrap(); // 잠금은 열리게
        std::fs::set_permissions(&d, std::fs::Permissions::from_mode(0o555)).unwrap();
        let probe = std::fs::write(d.join("probe"), b"x").is_ok(); // 루트면 권한 무시 — 판정 불가
        let got = if probe { None } else { Some(signing_secret_at(&p)) };
        std::fs::set_permissions(&d, std::fs::Permissions::from_mode(0o755)).unwrap();
        if let Some(got) = got {
            assert!(got.is_none(), "게시 실패인데 키를 돌려줬다");
            assert_eq!(std::fs::read(&p).unwrap(), b"");
            let left: Vec<_> = std::fs::read_dir(&d).unwrap().flatten()
                .filter(|e| e.file_name().to_string_lossy().contains(".tmp-")).collect();
            assert!(left.is_empty(), "임시 키 잔재");
        }
        let _ = std::fs::remove_dir_all(&d);
    }

    /// 다중 프로세스: 0바이트 키를 여러 데몬(프로세스)이 동시에 복구해도 한 키로 수렴 · 반환 키 == 경로 키.
    #[test]
    fn signing_secret_zero_byte_multi_process_converges() {
        if std::env::var_os("CYS_APPROVAL_SECRET_HELPER").is_some() {
            return;
        }
        let d = tdir("mproc");
        let p = d.join(".approval-secret");
        std::fs::write(&p, b"").unwrap();
        let exe = std::env::current_exe().unwrap();
        let kids: Vec<_> = (0..6)
            .map(|_| {
                std::process::Command::new(&exe)
                    .args(["--exact", "approval::tests::secret_proc_helper", "--nocapture", "--test-threads", "1"])
                    .env("CYS_APPROVAL_SECRET_HELPER", &p)
                    .stdout(std::process::Stdio::piped())
                    .stderr(std::process::Stdio::null())
                    .spawn()
                    .unwrap()
            })
            .collect();
        let outs: Vec<String> = kids
            .into_iter()
            .map(|k| String::from_utf8_lossy(&k.wait_with_output().unwrap().stdout).to_string())
            .collect();
        let disk = std::fs::read(&p).unwrap();
        assert_eq!(disk.len(), 32);
        let want = format!("KEY={}", disk.iter().map(|b| format!("{b:02x}")).collect::<String>());
        for o in &outs {
            assert!(o.contains(&want), "프로세스 반환 키 ≠ 경로 키: {o}");
        }
        let _ = std::fs::remove_dir_all(&d);
    }

    #[test]
    fn secret_proc_helper() {
        let Some(p) = std::env::var_os("CYS_APPROVAL_SECRET_HELPER") else { return };
        let k = signing_secret_at(std::path::Path::new(&p)).expect("helper");
        println!("KEY={}", k.iter().map(|b| format!("{b:02x}")).collect::<String>());
    }

    /// 복구된 새 키로 옛 키 기록은 매칭·재서명되지 않는다 · 갱신 대상은 검증된 바로 그 기록(위치) — 중복 id 반례 차단.
    #[test]
    fn recovered_key_never_approves_or_resigns_old_records() {
        let d = tdir("oldrec");
        let p = d.join(".approval-secret");
        let k_old = signing_secret_at(&p).unwrap();
        let mut old = rec(&["git", "push"], None, &[]);
        old.sign(&k_old);
        std::fs::write(&p, b"").unwrap();
        let k_new = signing_secret_at(&p).unwrap();
        assert_ne!(k_old, k_new);
        assert!(best_match(std::slice::from_ref(&old), &k_new, "git push origin", None, &[]).is_none(),
                "옛 키 기록이 새 키로 승인됐다");
        // 실제 중복 id: 앞 = 옛 키 기록 · 뒤 = 새 키 기록(같은 id). 갱신·재서명은 뒤(검증된 것)만.
        let mut old2 = old.clone();
        let mut cur = rec(&["git", "push"], None, &[]);
        cur.id = old2.id.clone();
        cur.updated_at = 1.0;
        cur.sign(&k_new);
        old2.updated_at = 1.0;
        old2.sign(&k_old);
        let old_sig = old2.signature.clone();
        let mut recs = vec![old2, cur];
        let hit = touch_best_match(&mut recs, &k_new, "git push origin", None, &[]);
        assert!(hit.is_some());
        assert_eq!(recs[0].signature, old_sig, "같은 id 의 옛 기록이 새 키로 재서명됐다");
        assert!(!recs[0].has_valid_signature(&k_new));
        assert!(recs[1].updated_at > 1.0 && recs[1].has_valid_signature(&k_new), "검증된 기록이 갱신되지 않았다");
        let h = include_str!("handlers.rs");
        assert!(h.contains("crate::approval::touch_best_match(&mut records"), "approval.check 가 touch_best_match 를 안 쓴다");
        let _ = std::fs::remove_dir_all(&d);
    }

    /// ⑨(Fable R1 #1) 저장 tmp 이름이 호출마다 다르다(고정 `json.tmp` 로 되돌리면 두 데몬이 서로 잘라 먹는다).
    #[test]
    fn save_records_tmp_name_is_unique_per_call() {
        let src = include_str!("approval.rs");
        let prod = &src[..src.find("\n#[cfg(test)]\nmod tests {").unwrap()];
        let f = &prod[prod.find("fn save_records_at(").unwrap()..]; // 본문 = save_records_at(A1 에서 경로 판 분리)
        let f = &f[..f.find("\n}\n").unwrap()];
        assert!(!f.contains("with_extension(\"json.tmp\")"), "고정 tmp 이름 잔존");
        assert!(f.contains("SAVE_SEQ.fetch_add"), "호출마다 다른 tmp 이름이 아니다");
        let h = include_str!("handlers.rs");
        assert_eq!(h.matches("let _records_lock = crate::approval::lock_records();").count(), 2,
                   "approval.check·sign 의 RMW 락");
    }

    /// ⑨ 승인 목록: 부재만 빈 목록 · BOM·잘림·형식 불일치 = Err(호출부 무저장).
    #[test]
    fn load_records_unreadable_is_error_not_empty() {
        let d = tdir("recs");
        let p = d.join("approvals.json");
        assert!(load_records_at(&p).unwrap().is_empty(), "부재 = 빈 목록");
        std::fs::write(&p, r#"{"records":[]}"#).unwrap();
        assert!(load_records_at(&p).unwrap().is_empty());
        std::fs::write(&p, "[]").unwrap();
        assert!(load_records_at(&p).unwrap().is_empty(), "bare 배열 하위호환");
        // A1-F2(1.1.7 fix-blockers): 0바이트만 빈 목록 · BOM 은 벗기고 해석 — 그 밖 손상은 계속 Err·무변경.
        for bytes in [&b"\xEF\xBB\xBF{\"records\":["[..], &b"{\"records\":["[..], &b"{\"x\":1}"[..],
                      &b" \n"[..], &b"\xEF\xBB\xBF"[..]] {
            std::fs::write(&p, bytes).unwrap();
            assert!(load_records_at(&p).is_err(), "판독 불가가 빈 목록으로 접혔다");
            assert_eq!(std::fs::read(&p).unwrap(), bytes);
        }
        let _ = std::fs::remove_dir_all(&d);
    }

    /// A1-F2(1.1.7 fix-blockers · codex 1R 차단): 0바이트 승인 목록 = 지킬 기록이 없는 파일 → 빈 목록(v1.1.6 처럼
    /// 이후 저장 가능) · 선두 BOM 뒤 유효 JSON = BOM 만 벗기고 그 기록을 읽는다(파일 전체를 빈 목록으로 접지 않는다).
    #[test]
    fn load_records_zero_bytes_is_empty_and_bom_is_stripped() {
        let d = tdir("recs0");
        let p = d.join("approvals.json");
        std::fs::write(&p, b"").unwrap();
        assert!(load_records_at(&p).expect("0바이트가 영구 판독 실패로 남았다").is_empty());
        let mut r = rec(&["git", "push"], None, &[]);
        r.sign(SECRET);
        let body = serde_json::json!({"records": [serde_json::to_value(&r).unwrap()]}).to_string();
        let mut bom = b"\xEF\xBB\xBF".to_vec();
        bom.extend_from_slice(body.as_bytes());
        std::fs::write(&p, &bom).unwrap();
        let got = load_records_at(&p).expect("BOM + 유효 JSON 을 못 읽음");
        assert_eq!(got.len(), 1, "BOM 파일의 기록이 사라졌다");
        assert!(got[0].has_valid_signature(SECRET));
        std::fs::write(&p, format!("\u{feff}{}", serde_json::json!([serde_json::to_value(&r).unwrap()]))).unwrap();
        assert_eq!(load_records_at(&p).expect("BOM + bare 배열").len(), 1);
        let _ = std::fs::remove_dir_all(&d);
    }

    /// A1-F2: 0바이트 목록 위 저장이 된다(v1.1.6 처럼 재승인 가능) · BOM 파일의 기존 기록은 새 기록과 함께 보존된다.
    #[test]
    fn records_zero_bytes_then_save_and_bom_records_survive_append() {
        let d = tdir("recsave");
        let p = d.join("approvals.json");
        std::fs::write(&p, b"").unwrap();
        let mut recs = load_records_at(&p).unwrap();
        let mut r1 = rec(&["git", "push"], None, &[]);
        r1.sign(SECRET);
        recs.push(r1.clone());
        save_records_at(&p, &recs).unwrap();
        let back = load_records_at(&p).unwrap();
        assert_eq!(back.len(), 1);
        assert!(back[0].has_valid_signature(SECRET));
        let mut bom = b"\xEF\xBB\xBF".to_vec();
        bom.extend_from_slice(serde_json::json!({"records": [serde_json::to_value(&r1).unwrap()]}).to_string().as_bytes());
        std::fs::write(&p, &bom).unwrap();
        let mut recs = load_records_at(&p).unwrap();
        let mut r2 = rec(&["npm", "publish"], None, &[]);
        r2.id = "ap-test-2".into();
        r2.sign(SECRET);
        recs.push(r2);
        save_records_at(&p, &recs).unwrap();
        let back = load_records_at(&p).unwrap();
        assert_eq!(back.len(), 2, "BOM 파일의 기존 기록이 저장에서 사라졌다");
        assert!(back.iter().all(|r| r.has_valid_signature(SECRET)));
        let _ = std::fs::remove_dir_all(&d);
    }

    /// A1-F1: 단계별 실패 주입 — 잠금·임시 키(권한·쓰기·sync)·게시·게시 뒤 확인 어느 단계가 실패해도 None ·
    /// 반환하지 않은 키가 경로에 새로 서지 않음(확인 단계 제외) · 임시 파일 잔재 0.
    #[test]
    fn signing_secret_each_stage_failure_returns_none_without_residue() {
        for stage in ["lock", "tmp_perm", "tmp_write", "tmp_sync", "publish", "verify"] {
            for start_empty in [true, false] {
                let d = tdir(&format!("fail-{stage}-{start_empty}"));
                let p = d.join(".approval-secret");
                if start_empty {
                    std::fs::write(&p, b"").unwrap();
                }
                FAILS.lock().unwrap().push((p.clone(), stage));
                let got = signing_secret_at(&p);
                clear_hooks(&p);
                assert!(got.is_none(), "{stage}/{start_empty}: 실패인데 키를 돌려줬다");
                let now = std::fs::read(&p).ok();
                if stage != "verify" {
                    let want = if start_empty { Some(Vec::new()) } else { None };
                    assert_eq!(now, want, "{stage}/{start_empty}: 실패인데 경로가 바뀌었다");
                }
                let left: Vec<_> = std::fs::read_dir(&d).unwrap().flatten()
                    .filter(|e| e.file_name().to_string_lossy().contains(".tmp-")).collect();
                assert!(left.is_empty(), "{stage}/{start_empty}: 임시 키 잔재");
                let _ = std::fs::remove_dir_all(&d);
            }
        }
    }

    #[test]
    fn sign_verify_roundtrip() {
        let mut r = rec(&["git", "push"], None, &[]);
        r.sign(SECRET);
        assert!(!r.signature.is_empty());
        assert!(r.has_valid_signature(SECRET));
    }

    #[test]
    fn tampered_rejected() {
        // 변종 1: command_prefix 변조
        let mut r = rec(&["git", "push"], None, &[]);
        r.sign(SECRET);
        let mut t1 = r.clone();
        t1.command_prefix = vec!["git".into(), "pull".into()];
        assert!(!t1.has_valid_signature(SECRET), "command_prefix 변조 통과");

        // 변종 2: cwd 변조
        let mut r2 = rec(&["git", "push"], Some("/a"), &[]);
        r2.sign(SECRET);
        let mut t2 = r2.clone();
        t2.cwd = Some("/b".into());
        assert!(!t2.has_valid_signature(SECRET), "cwd 변조 통과");

        // 변종 3: env 변조
        let mut r3 = rec(&["git", "push"], None, &[("CI", "1")]);
        r3.sign(SECRET);
        let mut t3 = r3.clone();
        t3.environment = vec![("CI".into(), "2".into())];
        assert!(!t3.has_valid_signature(SECRET), "env 변조 통과");

        // 변종 4: signature 한 글자 변조
        let mut t4 = r.clone();
        let mut sig: Vec<char> = t4.signature.chars().collect();
        // 첫 글자를 다른 base64 문자로 치환
        sig[0] = if sig[0] == 'A' { 'B' } else { 'A' };
        t4.signature = sig.into_iter().collect();
        assert!(!t4.has_valid_signature(SECRET), "signature 변조 통과");
    }

    #[test]
    fn wrong_secret_rejected() {
        let mut r = rec(&["git", "push"], None, &[]);
        r.sign(SECRET);
        assert!(!r.has_valid_signature(b"a-completely-different-secret-key"));
    }

    #[test]
    fn prefix_match() {
        let r = rec(&["git", "push"], None, &[]);
        assert!(r.matches("git push origin main", None, &[]));
        assert!(!r.matches("git status", None, &[]), "git status 오매칭");
        assert!(!r.matches("git", None, &[]), "토큰 부족인데 매칭");
    }

    #[test]
    fn empty_prefix_no_fallback() {
        let r = rec(&[], None, &[]);
        assert!(!r.matches("anything goes here", None, &[]));
    }

    #[test]
    fn unclosed_quote_rejected() {
        assert!(tokenize("git push 'x").is_none(), "미닫힌 따옴표 토큰화 통과");
        let r = rec(&["git", "push"], None, &[]);
        assert!(
            !r.matches("git push 'unterminated", None, &[]),
            "미닫힌 따옴표 명령 매칭 통과(prefix injection)"
        );
    }

    #[test]
    fn longest_prefix_wins() {
        let mut short = rec(&["git"], None, &[]);
        short.id = "ap-short".into();
        short.sign(SECRET);
        let mut long = rec(&["git", "push"], None, &[]);
        long.id = "ap-long".into();
        long.sign(SECRET);
        let recs = vec![short, long];
        let best = best_match(&recs, SECRET, "git push origin main", None, &[]).unwrap();
        assert_eq!(best.id, "ap-long", "최장 prefix 미선택");
    }

    #[test]
    fn sensitive_env_dropped() {
        let r = rec(&["deploy"], None, &[("API_KEY", "leak"), ("CI", "1")]);
        // 레코드 environment에서 API_KEY가 제거되고 CI만 남는다.
        assert!(
            r.environment.iter().all(|(k, _)| k != "API_KEY"),
            "API_KEY가 레코드에 잔존"
        );
        assert!(r.environment.iter().any(|(k, _)| k == "CI"));
        // 서명 페이로드에도 시크릿값이 없어야 한다.
        let payload = String::from_utf8(r.signing_payload()).unwrap();
        let leaked = b64_encode(b"leak");
        assert!(!payload.contains(&leaked), "시크릿값이 서명 페이로드에 유출");
    }

    #[test]
    fn determinism() {
        let mut r1 = rec(&["git", "push"], Some("/x"), &[("CI", "1"), ("AAA", "2")]);
        let mut r2 = rec(&["git", "push"], Some("/x"), &[("AAA", "2"), ("CI", "1")]);
        r1.sign(SECRET);
        r2.sign(SECRET);
        assert_eq!(r1.signature, r2.signature, "동일 입력 2회 서명 불일치(비결정)");
    }

    /// RFC 4231 Test Case 2 — 수동 HMAC-SHA256 정확성 박제.
    /// Key = "Jefe", Data = "what do ya want for nothing?"
    /// HMAC-SHA256 = 5bdcc146bf60754e6a042426089575c75a003f089d2739839dec58b964ec3843
    #[test]
    fn hmac_kat() {
        let key = b"Jefe";
        let data = b"what do ya want for nothing?";
        let expected: [u8; 32] = [
            0x5b, 0xdc, 0xc1, 0x46, 0xbf, 0x60, 0x75, 0x4e, 0x6a, 0x04, 0x24, 0x26, 0x08, 0x95,
            0x75, 0xc7, 0x5a, 0x00, 0x3f, 0x08, 0x9d, 0x27, 0x39, 0x83, 0x9d, 0xec, 0x58, 0xb9,
            0x64, 0xec, 0x38, 0x43,
        ];
        assert_eq!(hmac_sha256(key, data), expected, "RFC 4231 TC2 KAT 실패");

        // RFC 4231 Test Case 1 — Key = 0x0b*20, Data = "Hi There"
        // HMAC-SHA256 = b0344c61d8db38535ca8afceaf0bf12b881dc200c9833da726e9376c2e32cff7
        let key1 = [0x0bu8; 20];
        let data1 = b"Hi There";
        let expected1: [u8; 32] = [
            0xb0, 0x34, 0x4c, 0x61, 0xd8, 0xdb, 0x38, 0x53, 0x5c, 0xa8, 0xaf, 0xce, 0xaf, 0x0b,
            0xf1, 0x2b, 0x88, 0x1d, 0xc2, 0x00, 0xc9, 0x83, 0x3d, 0xa7, 0x26, 0xe9, 0x37, 0x6c,
            0x2e, 0x32, 0xcf, 0xf7,
        ];
        assert_eq!(hmac_sha256(&key1, data1), expected1, "RFC 4231 TC1 KAT 실패");

        // RFC 4231 Test Case 3 — long key path (key>64B 축약 검증):
        // Key = 0xaa*131, Data = "Test Using Larger Than Block-Size Key - Hash Key First"
        // HMAC-SHA256 = 60e431591ee0b67f0d8a26aacbf5b77f8e0bc6213728c5140546040f0ee37f54
        let key3 = [0xaau8; 131];
        let data3 = b"Test Using Larger Than Block-Size Key - Hash Key First";
        let expected3: [u8; 32] = [
            0x60, 0xe4, 0x31, 0x59, 0x1e, 0xe0, 0xb6, 0x7f, 0x0d, 0x8a, 0x26, 0xaa, 0xcb, 0xf5,
            0xb7, 0x7f, 0x8e, 0x0b, 0xc6, 0x21, 0x37, 0x28, 0xc5, 0x14, 0x05, 0x46, 0x04, 0x0f,
            0x0e, 0xe3, 0x7f, 0x54,
        ];
        assert_eq!(
            hmac_sha256(&key3, data3),
            expected3,
            "RFC 4231 TC3 KAT 실패(키 축약)"
        );
    }

    #[test]
    fn b64_roundtrip() {
        for s in [
            &b""[..],
            b"f",
            b"fo",
            b"foo",
            b"foob",
            b"fooba",
            b"foobar",
            b"\x00\xff\x10",
        ] {
            let enc = b64_encode(s);
            assert_eq!(b64_decode(&enc).as_deref(), Some(s), "base64 라운드트립 실패");
        }
        // 알려진 벡터(RFC 4648)
        assert_eq!(b64_encode(b"foobar"), "Zm9vYmFy");
        assert_eq!(b64_decode("Zm9vYmFy").unwrap(), b"foobar");
    }
}
