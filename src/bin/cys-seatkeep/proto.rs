//! seatkeep ↔ 조종자(cysd) 프레임 — T2 시제품(TICKET=cysr-seatkeep-t2 · 설계 = DESIGN.md §3-2 ②).
//!
//! 한 프레임 = `[kind u8][seat u32 LE][len u32 LE][payload]`. 프레임 모양은 허더 `holder_proto.rs` 를
//! 참고했고 코드는 새로 썼다(복사 없음 → NOTICE.md 항목 불요).
//!
//! **고정 핵심**(영구 고정 · `CORE_VERSION`): HELLO · WELCOME · REJECT · EXITED · RELEASE · SIGNAL.
//! 나머지는 확장이다.
//!
//! SIGNAL 본문(JSON) = `{"sig": <번호>}`(T2 · 그룹 = killpg) · **T3 확장**(master#fe07cc6a · D7 결정 B) 선택 칸
//! `"target"`: `"group"`(= 칸 없음과 같음 · killpg) · `"leader"`(좌석 리더 pid 에만 kill) · 그 밖의 값 = **거절**(신호 0 ·
//! 조용히 그룹으로 내려가지 않음). 회수 표시가 선 좌석에는 어느 쪽이든 보내지 않는다. `target` 칸이 있는 요청에만 결과 프레임
//! SIGNAL_RESULT `{"sig","target","result": "sent"|"reaped"|"bad_target"|"no_pid"}` 를 좌석마다 돌려준다(칸 없는 T2 요청은
//! 답 없음 = T2 동작 그대로). ★발행 전 확장 · 핵심 판 번호(CORE_VERSION) 그대로 — seatkeep 은 아직 한 번도 발행되지 않아
//! 이 칸을 모르는 옛 seatkeep 이 현장에 없다(어긋날 상대 없음 · master#fe07cc6a). 핵심 판이 다르면 seatkeep 은 REJECT(`core_mismatch`)로 끊는다 — 허더처럼
//! 판 번호를 받기만 하고 비교하지 않는 일(holder.rs:207)은 하지 않는다.

use std::io::{self, Read, Write};

pub const CORE_VERSION: u32 = 1;
/// 한 프레임 본문 상한. 넘으면 연결을 끊는다(메모리 폭주 방지).
pub const MAX_PAYLOAD: usize = 16 << 20;

// 조종자 → seatkeep
pub const HELLO: u8 = 1;
pub const INPUT: u8 = 3;
pub const RESIZE: u8 = 4;
pub const SIGNAL: u8 = 5;
pub const RELEASE: u8 = 6;
pub const FOREGROUND: u8 = 8;
pub const EXIT_ACK: u8 = 10;

// seatkeep → 조종자
pub const WELCOME: u8 = 101;
pub const OUTPUT: u8 = 103;
pub const EXITED: u8 = 106;
pub const FOREGROUND_IS: u8 = 108;
pub const REJECT: u8 = 109;
pub const INPUT_ACK: u8 = 110;
/// SIGNAL 결과(T3 확장 · `target` 칸이 있는 SIGNAL 에만).
pub const SIGNAL_RESULT: u8 = 111;

pub fn frame(kind: u8, seat: u32, payload: &[u8]) -> Vec<u8> {
    debug_assert!(payload.len() <= MAX_PAYLOAD, "보내는 프레임도 상한 안이어야 한다(재생은 나눠 보낸다)");
    let mut v = Vec::with_capacity(9 + payload.len());
    v.push(kind);
    v.extend_from_slice(&seat.to_le_bytes());
    v.extend_from_slice(&(payload.len() as u32).to_le_bytes());
    v.extend_from_slice(payload);
    v
}

pub fn json_frame(kind: u8, seat: u32, value: &serde_json::Value) -> Vec<u8> {
    frame(kind, seat, value.to_string().as_bytes())
}

/// 프레임 1개를 읽는다. 깨끗한 EOF(머리 0바이트) = `Ok(None)`.
pub fn read_frame(r: &mut impl Read) -> io::Result<Option<(u8, u32, Vec<u8>)>> {
    read_frame_max(r, MAX_PAYLOAD)
}

/// 본문 상한을 따로 주는 읽기(HELLO 같은 작은 프레임용 — 큰 길이를 선언해 버퍼를 잡게 하지 못하게).
pub fn read_frame_max(r: &mut impl Read, max: usize) -> io::Result<Option<(u8, u32, Vec<u8>)>> {
    let mut head = [0u8; 9];
    let mut got = 0;
    while got < head.len() {
        let n = r.read(&mut head[got..])?;
        if n == 0 {
            return if got == 0 { Ok(None) } else { Err(io::ErrorKind::UnexpectedEof.into()) };
        }
        got += n;
    }
    let kind = head[0];
    let seat = u32::from_le_bytes([head[1], head[2], head[3], head[4]]);
    let len = u32::from_le_bytes([head[5], head[6], head[7], head[8]]) as usize;
    if len > max {
        return Err(io::Error::new(io::ErrorKind::InvalidData, "payload too large"));
    }
    let mut payload = vec![0u8; len];
    r.read_exact(&mut payload)?;
    Ok(Some((kind, seat, payload)))
}

pub fn write_all(w: &mut impl Write, bytes: &[u8]) -> io::Result<()> {
    w.write_all(bytes)?;
    w.flush()
}

/// OUTPUT 본문 = `[offset u64 LE][bytes]` — offset = 이 바이트들의 좌석 누적 출력 시작 위치.
pub fn output_payload(offset: u64, bytes: &[u8]) -> Vec<u8> {
    let mut v = Vec::with_capacity(8 + bytes.len());
    v.extend_from_slice(&offset.to_le_bytes());
    v.extend_from_slice(bytes);
    v
}

/// INPUT 본문 = `[input_id u64 LE][bytes]`. id 0 은 「중복 제거 안 함」.
pub fn split_input(payload: &[u8]) -> Option<(u64, &[u8])> {
    if payload.len() < 8 {
        return None;
    }
    let id = u64::from_le_bytes(payload[..8].try_into().ok()?);
    Some((id, &payload[8..]))
}

/// INPUT_ACK 본문 = `[input_id u64 LE][dup u8]` — dup=1 이면 이미 쓴 id 라 이번엔 쓰지 않았다.
pub fn input_ack_payload(id: u64, dup: bool) -> Vec<u8> {
    let mut v = id.to_le_bytes().to_vec();
    v.push(dup as u8);
    v
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn frame_roundtrip() {
        let f = frame(INPUT, 7, b"abc");
        let mut r = &f[..];
        let (k, s, p) = read_frame(&mut r).unwrap().unwrap();
        assert_eq!((k, s, p.as_slice()), (INPUT, 7, &b"abc"[..]));
        assert!(read_frame(&mut r).unwrap().is_none());
    }

    #[test]
    fn oversize_rejected() {
        let mut f = frame(INPUT, 0, b"");
        f[5..9].copy_from_slice(&((MAX_PAYLOAD as u32) + 1).to_le_bytes());
        assert!(read_frame(&mut &f[..]).is_err());
    }

    #[test]
    fn small_cap_rejects_big_hello() {
        let f = frame(HELLO, 0, &vec![b'x'; 5000]);
        assert!(read_frame_max(&mut &f[..], 4096).is_err());
        assert!(read_frame_max(&mut &f[..], 8192).unwrap().is_some());
    }

    #[test]
    fn truncated_head_is_error_not_eof() {
        let f = frame(INPUT, 0, b"x");
        assert!(read_frame(&mut &f[..4]).is_err());
    }

    #[test]
    fn input_split() {
        let mut p = 42u64.to_le_bytes().to_vec();
        p.extend_from_slice(b"hi");
        assert_eq!(split_input(&p), Some((42, &b"hi"[..])));
        assert_eq!(split_input(b"short"), None);
    }
}
