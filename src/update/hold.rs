//! 영속 보류 로그 — 정비 모드 동안 들어온 입력 배달을 갈무리한다(설계 AUTO-UPDATE-118 §3-3 · 2R 신규 BLOCK 6 · 3R 신규 BLOCK 1).
//!
//! - 자리 = `<상태 폴더>/hold-queue.jsonl`(스냅샷 밖 원장). 한 줄 = `{hold_seq(단조), target_surface_uuid, kind, body_sha256,
//!   body, received_at}`.
//! - **ACK 는 그 줄이 fsync 된 뒤에만**: [`HoldLog::append`] 가 `Ack{hold_seq, held:true}` 를 돌려주는 순간 그 입력은 정전이
//!   나도 남는다. 쓰다 끊긴 꼬리(개행 없는 마지막 줄)는 ACK 를 받은 적이 없으므로 다음 열기 때 잘라낸다(이어붙기 차단 —
//!   §6-11 교훈의 파일판).
//! - 재생 ①(로그 → 배송 큐 = **정확히 한 번**): 큐 항목 `id = "hold:<txn_id>:<hold_seq>"`([`queue_item_id`]) · 큐 쪽 원자 쓰기에
//!   `hold_ingested.upto_hold_seq` 를 함께 커밋 → [`plan_ingest`] 는 `upto` 보다 큰 줄만 · 이미 큐에 있는 id 는 빼고 고른다
//!   (둘 사이에서 죽어도 다시 돌리면 중복 0). 큐 파일 원자 쓰기 자체(`persist_queue_state`)와 `delivering` 표지(재생 ② ·
//!   최대 한 번)는 cysd 쪽 U2.
//! - ★폭주 방지 장치(치명 위험 4군 ①): 「정확히 한 번 · 중복 제거」 를 약화하지 않는다 — 같은 `hold_seq` 가 두 번 큐에 들어갈
//!   길을 시험이 막는다.

use serde::{Deserialize, Serialize};
use std::io::{Read, Seek, SeekFrom, Write};
use std::path::{Path, PathBuf};

pub const HOLD_FILE: &str = "hold-queue.jsonl";

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct HoldRecord {
    pub hold_seq: u64,
    pub target_surface_uuid: String,
    pub kind: String,
    pub body_sha256: String,
    pub body: String,
    pub received_at: i64,
}

/// 보낸 쪽에 돌려주는 접수(fsync 뒤).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
pub struct Ack {
    pub hold_seq: u64,
    pub held: bool,
}

/// 보류 로그 핸들(쓰는 쪽은 데몬 하나 — 단일 작성자 전제 · 정비 모드 RPC 가 직렬화한다).
pub struct HoldLog {
    path: PathBuf,
    last_seq: u64,
}

fn sha256_hex(s: &str) -> String {
    use sha2::{Digest, Sha256};
    format!("{:x}", Sha256::digest(s.as_bytes()))
}

impl HoldLog {
    /// 열기 — 개행 없는 꼬리(쓰다 끊김 = ACK 0)를 잘라내고 마지막 `hold_seq` 를 읽는다. 온전한 줄이 깨져 있으면 Err(fail-closed).
    pub fn open(dir: &Path) -> Result<HoldLog, String> {
        super::ensure_private_dir(dir)?;
        let path = dir.join(HOLD_FILE);
        let mut o = std::fs::OpenOptions::new();
        o.read(true).write(true).create(true).truncate(false);
        #[cfg(unix)]
        {
            use std::os::unix::fs::OpenOptionsExt;
            o.mode(0o600);
        }
        let mut f = o.open(&path).map_err(|e| format!("{}: {e}", path.display()))?;
        super::check_private_file(&path)?; // ★2R M3: 이미 있던 파일도 소유자 전용(아니면 Err = 판정 불가)
        let mut buf = Vec::new();
        f.read_to_end(&mut buf).map_err(|e| e.to_string())?;
        let keep = match buf.iter().rposition(|&b| b == b'\n') {
            Some(i) => i + 1,
            None => 0,
        };
        if keep < buf.len() {
            f.set_len(keep as u64).map_err(|e| format!("꼬리 자르기: {e}"))?;
            f.sync_all().map_err(|e| e.to_string())?;
            buf.truncate(keep);
        }
        let mut last_seq = 0;
        for (i, line) in buf.split(|&b| b == b'\n').filter(|l| !l.is_empty()).enumerate() {
            let r: HoldRecord = serde_json::from_slice(line).map_err(|e| format!("보류 로그 {}번째 줄 손상: {e}", i + 1))?;
            if r.hold_seq <= last_seq {
                return Err(format!("보류 로그 hold_seq 단조 위반 {} ≤ {last_seq}", r.hold_seq));
            }
            last_seq = r.hold_seq;
        }
        Ok(HoldLog { path, last_seq })
    }

    pub fn last_seq(&self) -> u64 {
        self.last_seq
    }

    /// 1건 기록 → fsync → ACK. fsync 가 실패하면 ACK 없음(Err) — 보낸 쪽은 「보류 안 됨」으로 안다.
    pub fn append(&mut self, target_surface_uuid: &str, kind: &str, body: &str, received_at: i64) -> Result<Ack, String> {
        let rec = HoldRecord {
            hold_seq: self.last_seq + 1,
            target_surface_uuid: target_surface_uuid.to_string(),
            kind: kind.to_string(),
            body_sha256: sha256_hex(body),
            body: body.to_string(),
            received_at,
        };
        let mut line = serde_json::to_vec(&rec).map_err(|e| e.to_string())?;
        line.push(b'\n');
        let mut f = std::fs::OpenOptions::new().append(true).open(&self.path).map_err(|e| e.to_string())?;
        f.seek(SeekFrom::End(0)).map_err(|e| e.to_string())?;
        f.write_all(&line).map_err(|e| e.to_string())?;
        f.sync_data().map_err(|e| format!("fsync: {e}"))?; // ★ACK 전에 디스크로
        self.last_seq = rec.hold_seq;
        Ok(Ack { hold_seq: rec.hold_seq, held: true })
    }

    /// `upto` 보다 큰 줄(순서대로). 본문 해시가 어긋난 줄 = Err(손상 · 배달하지 않는다).
    pub fn records_after(&self, upto: u64) -> Result<Vec<HoldRecord>, String> {
        let buf = std::fs::read(&self.path).map_err(|e| e.to_string())?;
        let mut out = Vec::new();
        for line in buf.split(|&b| b == b'\n').filter(|l| !l.is_empty()) {
            let r: HoldRecord = serde_json::from_slice(line).map_err(|e| e.to_string())?;
            if r.body_sha256 != sha256_hex(&r.body) {
                return Err(format!("hold_seq {} 본문 해시 불일치", r.hold_seq));
            }
            if r.hold_seq > upto {
                out.push(r);
            }
        }
        Ok(out)
    }

    /// 미배달 수(N3 · `delivered_hold_seq` 이후).
    pub fn undelivered(&self, delivered_hold_seq: u64) -> u64 {
        self.last_seq.saturating_sub(delivered_hold_seq)
    }
}

/// 읽기 전용 — 온전한 마지막 줄의 `hold_seq`(파일 없음 = 0 · 손상 = None). 꼬리 자르기 등 **쓰기 0**(`--check` 용).
pub fn last_seq_readonly(dir: &Path) -> Option<u64> {
    let buf = match std::fs::read(dir.join(HOLD_FILE)) {
        Ok(b) => b,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Some(0),
        Err(_) => return None,
    };
    super::check_private_file(&dir.join(HOLD_FILE)).ok()?; // ★2R M3: 소유자 전용 아님 = 모름(보류)
    let keep = buf.iter().rposition(|&b| b == b'\n').map(|i| i + 1).unwrap_or(0);
    let mut last = 0;
    for line in buf[..keep].split(|&b| b == b'\n').filter(|l| !l.is_empty()) {
        let r = serde_json::from_slice::<HoldRecord>(line).ok()?;
        // ★1R MAJOR(M7): 읽기 전용 경로도 본문 해시·엄격 단조를 본다 — 어긋나면 판정 불가(미배달 수 축소 차단).
        if !super::mutant("M7") && (r.body_sha256 != sha256_hex(&r.body) || r.hold_seq <= last) {
            return None;
        }
        last = r.hold_seq;
    }
    Some(last)
}

/// 배송 큐 항목 id(중복 제거 키).
pub fn queue_item_id(txn_id: &str, hold_seq: u64) -> String {
    format!("hold:{txn_id}:{hold_seq}")
}

/// 재생 ① 계획 — `hold_ingested_upto` 보다 크고 아직 큐에 없는 줄만(순서 유지). 결과와 「커밋할 새 upto」.
pub fn plan_ingest<'a>(
    txn_id: &str,
    records: &'a [HoldRecord],
    hold_ingested_upto: u64,
    existing_queue_ids: &std::collections::HashSet<String>,
) -> (Vec<&'a HoldRecord>, u64) {
    let mut out = Vec::new();
    let mut upto = hold_ingested_upto;
    for r in records.iter().filter(|r| r.hold_seq > hold_ingested_upto) {
        if !existing_queue_ids.contains(&queue_item_id(txn_id, r.hold_seq)) {
            out.push(r);
        }
        upto = upto.max(r.hold_seq);
    }
    (out, upto)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashSet;

    fn tmp(tag: &str) -> PathBuf {
        let d = std::env::temp_dir().join(format!("cys-u1-hold-{tag}-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&d);
        d
    }
    const T: &str = "0123456789abcdef0123456789abcdef";

    #[test]
    fn append_acks_after_durable_line_and_seq_is_monotonic_across_reopen() {
        let d = tmp("ack");
        let mut h = HoldLog::open(&d).unwrap();
        let a1 = h.append("uuid-1", "send", "안녕", 100).unwrap();
        let a2 = h.append("uuid-2", "queued", "둘", 101).unwrap();
        assert_eq!((a1, a2), (Ack { hold_seq: 1, held: true }, Ack { hold_seq: 2, held: true }));
        // ACK 받은 줄은 파일에 온전히 있다(다시 열어 읽힘 = 정전 뒤에도 남는다)
        drop(h);
        let mut h = HoldLog::open(&d).unwrap();
        assert_eq!(h.last_seq(), 2);
        assert_eq!(h.append("u", "send", "셋", 102).unwrap().hold_seq, 3);
        assert_eq!(h.records_after(1).unwrap().iter().map(|r| r.hold_seq).collect::<Vec<_>>(), vec![2, 3]);
        assert_eq!(h.undelivered(1), 2);
        assert_eq!(last_seq_readonly(&d), Some(3));
        assert_eq!(last_seq_readonly(&d.join("none")), Some(0));
        let _ = std::fs::remove_dir_all(&d);
    }

    /// fsync 전 ACK 0: 쓰다 끊긴 꼬리(개행 없음)는 ACK 를 받은 적 없는 기록 — 다음 열기가 잘라내고 다음 기록과 이어붙지 않는다.
    #[test]
    fn torn_tail_is_cut_and_never_glued_to_next_record() {
        let d = tmp("torn");
        let mut h = HoldLog::open(&d).unwrap();
        h.append("u", "send", "하나", 1).unwrap();
        drop(h);
        let p = d.join(HOLD_FILE);
        let mut f = std::fs::OpenOptions::new().append(true).open(&p).unwrap();
        f.write_all(br#"{"hold_seq":2,"target_surface_uuid":"u","ki"#).unwrap();
        drop(f);
        let mut h = HoldLog::open(&d).unwrap();
        assert_eq!(h.last_seq(), 1, "끊긴 꼬리는 없는 것");
        assert_eq!(h.append("u", "send", "둘", 2).unwrap().hold_seq, 2);
        let recs = h.records_after(0).unwrap();
        assert_eq!(recs.len(), 2);
        assert_eq!(recs[1].body, "둘");
        let _ = std::fs::remove_dir_all(&d);
    }

    #[test]
    fn corrupt_complete_line_or_body_tamper_fails_closed() {
        let d = tmp("bad");
        let mut h = HoldLog::open(&d).unwrap();
        h.append("u", "send", "본문", 1).unwrap();
        let p = d.join(HOLD_FILE);
        let s = std::fs::read_to_string(&p).unwrap().replace("본문", "변조");
        std::fs::write(&p, s).unwrap();
        assert!(h.records_after(0).unwrap_err().contains("해시 불일치"));
        std::fs::write(&p, b"not json\n").unwrap();
        assert!(HoldLog::open(&d).is_err());
        let _ = std::fs::remove_dir_all(&d);
    }

    /// ★1R MAJOR(M7) 뮤테이션: 읽기 전용 판독도 단조 위반·본문 변조면 None(미배달 수를 줄여 N3 을 통과시키는 길 차단).
    #[test]
    fn m7_readonly_last_seq_validates_monotonic_and_hash() {
        let d = tmp("m7");
        let mut h = HoldLog::open(&d).unwrap();
        for i in 0..3 {
            h.append("u", "send", &format!("m{i}"), i).unwrap();
        }
        assert_eq!(last_seq_readonly(&d), Some(3));
        // 마지막 줄 뒤에 낮은 seq 의 정상 JSON 을 덧붙임(축소 시도)
        let low = HoldRecord { hold_seq: 1, target_surface_uuid: "u".into(), kind: "send".into(), body_sha256: sha256_hex("x"), body: "x".into(), received_at: 9 };
        let mut f = std::fs::OpenOptions::new().append(true).open(d.join(HOLD_FILE)).unwrap();
        f.write_all(format!("{}\n", serde_json::to_string(&low).unwrap()).as_bytes()).unwrap();
        assert_eq!(last_seq_readonly(&d), None, "단조 위반 = 판정 불가");
        let s = std::fs::read_to_string(d.join(HOLD_FILE)).unwrap();
        let fixed: String = s.lines().take(3).map(|l| format!("{l}\n")).collect::<String>().replace("\"m2\"", "\"zz\"");
        std::fs::write(d.join(HOLD_FILE), fixed).unwrap();
        assert_eq!(last_seq_readonly(&d), None, "본문 변조 = 판정 불가");
        let _ = std::fs::remove_dir_all(&d);
    }

    /// 재생 ① 정확히 한 번: 「큐에 넣음」 커밋 직후·`upto` 커밋 전 죽음 → 다시 계획해도 중복 0 · 재부팅 뒤 중복 0.
    #[test]
    fn ingest_plan_is_exactly_once_under_crash_between_steps() {
        let d = tmp("ing");
        let mut h = HoldLog::open(&d).unwrap();
        for i in 0..5 {
            h.append("u", "send", &format!("m{i}"), i).unwrap();
        }
        let recs = h.records_after(0).unwrap();
        let mut queue: HashSet<String> = HashSet::new();
        // 1회차: 1~3 만 큐에 넣었고(원자 커밋에 upto=3) 그 뒤 4·5 를 넣다가 큐엔 들어갔지만 upto 는 못 올린 채 죽었다고 가정
        let (first, _) = plan_ingest(T, &recs[..3], 0, &queue);
        for r in first {
            queue.insert(queue_item_id(T, r.hold_seq));
        }
        queue.insert(queue_item_id(T, 4)); // 커밋된 큐에는 4 가 있음
        let upto = 3;
        // 재기동: upto 이후만 · 이미 있는 id 제외 → 5 하나만
        let (again, new_upto) = plan_ingest(T, &recs, upto, &queue);
        assert_eq!(again.iter().map(|r| r.hold_seq).collect::<Vec<_>>(), vec![5]);
        assert_eq!(new_upto, 5);
        for r in again {
            assert!(queue.insert(queue_item_id(T, r.hold_seq)), "중복 삽입 0");
        }
        // 한 번 더(멱등) = 0건
        let (third, _) = plan_ingest(T, &recs, new_upto, &queue);
        assert!(third.is_empty());
        assert_eq!(queue.len(), 5);
        let _ = std::fs::remove_dir_all(&d);
    }
}
