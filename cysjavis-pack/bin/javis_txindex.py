#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""javis_txindex — 원시 전사(JSONL) 인덱스 도구 (2층 기억 Layer 0).

설계 §3(`_round/DESIGN_quality_gates_2layer_memory.md`) 구현: 세션 JSONL을 증분
파싱해 SQLite FTS5로 인덱싱하고, 검색·인용·마이닝을 제공한다. 증류 기억의 사후
몰아쓰기 편향을 원시 전사 마이닝으로 보완하되 — **설계 불변식** 준수:
  · 컨텍스트 자동 주입 경로를 만들지 않는다 (주입은 기존 증류층 경로만).
  · 원본 JSONL을 수정·삭제하지 않는다 (txindex.db는 JSONL에서 전량 재생성 가능한
    파생 데이터 — 삭제 무손실).

명령:
  index  [--roots-file <p>] [--db <p>]        # 다중 프로필 증분 인덱스
  search "<질의>" [--limit N] [--db <p>]       # FTS5 검색 → ref + 1줄 발췌
  show   <ref> [--db <p>]                      # 원문 행 재조회(원본 JSONL read-only)
  mine   [--days N] [--ledger <p>] [--db <p>]  # 반복 패턴 후보 → RSI_LEDGER SHADOW append
  --self-test                                  # 결정론 자기검증

ref 형식: <프로필별칭>/<세션uuid>#<행번호>  (예: profileA/17cb1152-...#123)

DB 경로: --db > env CYS_TXINDEX_DB > 기본 ~/.cys/pack/state/txindex.db
        (테스트·개발은 반드시 _work 경로로 오버라이드).

종료 코드: 0 정상 · 2 인자/입력 오류 · 3 대상 없음(ref/db) · 4 쓰기 락 점유 · 1 self-test 실패
의존성: 파이썬 표준 라이브러리만 (sqlite3 포함). 네트워크·LLM 호출 없음.
주: 팩 기준선 Python 3.9 호환 — PEP604(`X | None`) 주석·match문 금지.
"""

import argparse
import fcntl
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
import time


# Windows: 콘솔 없는 부모(cysd·pythonw 브리지·GUI) 아래에서 출력을 캡처하는 콘솔 자식(cys.exe·powershell·cmd)을
# 숨김 없이 낳으면 자식마다 새 콘솔 창이 뜬다(TICKET=cysr-console-flicker-r2). 캡처하는 subprocess 호출에
# **NOWIN 을 전개한다(출력을 터미널로 흘리는 호출은 제외 — 창을 숨기면 그 출력이 사라진다). 타 OS 무동작.
NOWIN = {"creationflags": 0x08000000} if os.name == "nt" else {}

SCHEMA_VERSION = 2  # v1→v2: 발화 행 ts 열을 실제 timestamp 로 채움(mine --days 근거). v1 db 는 재구축 필요.

EXIT_OK = 0
EXIT_SELFTEST_FAIL = 1
EXIT_USAGE = 2
EXIT_NOT_FOUND = 3
EXIT_LOCK_BUSY = 4
EXIT_SCHEMA = 6


class _SchemaMismatch(Exception):
    """저장된 schema_version 이 현재와 불일치 — 파생 db 재구축 필요."""
    def __init__(self, stored, current):
        super().__init__("schema_version %s != %s" % (stored, current))
        self.stored = stored
        self.current = current

# 기본 인덱스 루트 유도용 glob 패턴 — 홈의 claude 프로필들의 projects 디렉토리 (설계 §3 다중 프로필).
# 개인 프로필명을 소스에 하드코딩하지 않는다(PUBLIC 발행 게이트) — 패턴 매칭으로 자동 탐색하고
# 심링크로 겹치는 base 프로필(예: ~/.claude → 실 프로필)은 root realpath dedup 으로 중복 스캔 회피.
DEFAULT_PROFILE_GLOB = os.path.join("~", ".claude*", "projects")

# 인덱스 대상이 되는 최상위 레코드 type — 나머지(attachment/system/file-history-snapshot/
# mode/permission-mode/bridge-session/ai-title/queue-operation/last-prompt)는 전량 제외.
_UTTERANCE_TYPES = ("user", "assistant")

_PROFILE_RE = re.compile(r"/\.claude-([^/]+)/")

# 시스템/하네스가 끼워넣은 user 줄(로컬 커맨드·caveat·reminder·디렉티브 stdin-push)은
# 사람 발화가 아니다. 검색·인용에는 남기되(injected=1 플래그) mine 반복신호 집계에서는 제외한다
# — javis_reflect.py SYSTEM_PREFIXES 와 동형(RECON 계약: reflect.py:171-182 형식 정합).
_SYSTEM_PREFIXES = ("<command-", "<local-command", "Caveat:", "<system-reminder",
                    "■ CYSJavis", "# MASTER ABSOLUTE DIRECTIVE", "# WORKER ABSOLUTE DIRECTIVE",
                    "# CSO ABSOLUTE DIRECTIVE", "# REVIEWER ABSOLUTE DIRECTIVE",
                    "# CEO (master of master)", "# RSI 학습 루프")


# ── 경로·루트 ───────────────────────────────────────────────────────────────

def default_db_path():
    env = os.environ.get("CYS_TXINDEX_DB")
    if env:
        return env
    return os.path.expanduser("~/.cys/pack/state/txindex.db")


def resolve_round_dir():
    """mine 기본 원장 위치가 될 _round 디렉토리 유도(임의 생성 금지).

    순서: ①env CYS_ROUND_DIR ②cwd 에서 위로 올라가며 존재하는 _round 디렉토리 탐색.
    발견 실패 시 None — 호출부가 명시 에러로 종료(엉뚱한 곳에 _round 를 만들지 않는다).
    """
    env = os.environ.get("CYS_ROUND_DIR")
    if env:
        return env
    cur = os.getcwd()
    while True:
        cand = os.path.join(cur, "_round")
        if os.path.isdir(cand):
            return cand
        parent = os.path.dirname(cur)
        if parent == cur:
            return None
        cur = parent


def _default_roots():
    """기본 인덱스 루트 유도(하드코딩 프로필명 없이).

    우선순위: ①env CYS_PROFILE_DIRS(콜론/쉼표 구분 경로 목록) ②홈의 `~/.claude*/projects` glob.
    """
    env = os.environ.get("CYS_PROFILE_DIRS")
    if env:
        return [p.strip() for p in re.split(r"[:,]", env) if p.strip()]
    return sorted(glob.glob(os.path.expanduser(DEFAULT_PROFILE_GLOB)))


def read_roots(roots_file):
    """루트 목록 확정. roots_file 주어지면 그 파일의 경로 목록, 아니면 기본 유도(_default_roots).

    반환: 존재하는 디렉토리 경로 리스트(순서 보존). realpath 로 중복 제거 —
    심링크 base 프로필이 실 프로필과 겹쳐도 한 번만 스캔한다(중복 스캔 회피).
    """
    raw = []
    if roots_file:
        with open(roots_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                raw.append(os.path.expanduser(line))
    else:
        raw = [os.path.expanduser(p) for p in _default_roots()]
    seen = set()
    out = []
    for p in raw:
        if not os.path.isdir(p):
            continue
        rp = os.path.realpath(p)
        if rp in seen:
            continue
        seen.add(rp)
        out.append(p)
    return out


def profile_alias(path):
    """실경로에서 프로필 별칭 추출(.claude-<alias>). 없으면 'unknown'."""
    m = _PROFILE_RE.search(path)
    return m.group(1) if m else "unknown"


def iter_jsonl_files(roots):
    """루트들 아래 모든 *.jsonl 을 realpath 로 dedup 하여 yield.

    yield: (realpath, profile_alias, session_uuid)
    홈의 claude 프로필 심링크(base → 실 프로필)로 같은 실체가 두 경로로 보여도 파일 realpath 로 1회만.
    """
    seen = set()
    for root in roots:
        # os.walk 사용 — glob '**' 는 숨김 디렉토리(.claude-*)를 건너뛴다.
        # followlinks=True 지만 파일 realpath dedup 이 심링크 중복을 최종 차단.
        for dirpath, _dirs, filenames in os.walk(root, followlinks=True):
            for fn in filenames:
                if not fn.endswith(".jsonl"):
                    continue
                path = os.path.join(dirpath, fn)
                if not os.path.isfile(path):
                    continue
                rp = os.path.realpath(path)
                if rp in seen:
                    continue
                seen.add(rp)
                alias = profile_alias(rp)
                session = os.path.splitext(os.path.basename(rp))[0]
                yield rp, alias, session


# ── 레코드 분류(필터 화이트리스트 · 설계 F4) ─────────────────────────────────

def _clean(s):
    """UTF-8 인코딩 불가 문자(짝 없는 surrogate 등)를 치환 — sqlite 저장·해시 인코딩 실패 방지.
    JSONL 의 `\\uXXXX` 이스케이프가 lone surrogate(예: \\ud95c)를 만들면 str.encode('utf-8')가
    'surrogates not allowed'로 터진다 → 인덱스 전체 중단 대신 해당 문자만 치환(fail-soft)."""
    if not s:
        return s
    return s.encode("utf-8", "replace").decode("utf-8")


def _block_text(block):
    """text/thinking 블록에서 본문 텍스트를 뽑는다(키 방어적·surrogate 안전)."""
    if not isinstance(block, dict):
        return ""
    return _clean((block.get("text") or block.get("thinking") or "").strip())


def _tool_first_line(payload):
    """도구 블록의 첫 유효 줄(표시·해시 보조용) 최대 200자."""
    s = _clean(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    for ln in s.splitlines():
        ln = ln.strip()
        if ln:
            return ln[:200]
    return ""


def classify_line(line):
    """JSONL 한 줄 → 인덱싱 항목 리스트.

    각 항목은 dict:
      {'utt': True, 'role', 'kind'('text'|'thinking'), 'body'}   FTS 본문 대상
      {'tool': True, 'role', 'name', 'hash', 'first_line'}       별도 열(본문 제외)
    반환: (items, status) where status ∈ {'ok','excluded','broken'}
      · broken: JSON 파싱 실패
      · excluded: 인덱스 대상 아닌 레코드(attachment/system/…, 또는 빈 발화)

    ★설계 F4 화이트리스트 해석 — thinking 블록 포함 결정(명문화):
      설계 §3 F4 는 'user/assistant 텍스트 발화'만 FTS 본문으로 규정한다. assistant `thinking`
      블록은 모델 내부사고라 '발화' 경계가 모호하나, 본 구현은 **포함하되 kind='thinking' 으로
      태깅**한다. 근거: (1) thinking 은 tool_use/tool_result 같은 '도구 덤프 잡음'(F4 가 배제하려는
      대상)이 아니라 자연어 사고 텍스트다 (2) RSI 마이닝의 '작업 한계=학습 신호' 포착에 유효한 recall
      소스다 (3) kind 태깅으로 text 발화와 분리 가능해 필요 시 mine/search 에서 배제할 수 있다.
      현행 mine 은 role='user' 만 집계하므로 thinking(assistant) 은 mine 후보에 **영향 없음** —
      검색면(search/show)만 확대한다. F4 negative(도구덤프 미검색)는 thinking 포함과 무관하게 유지.
    """
    line = line.strip()
    if not line:
        return [], "excluded"
    try:
        d = json.loads(line)
    except (ValueError, TypeError):
        return [], "broken"
    if not isinstance(d, dict):
        return [], "broken"
    t = d.get("type")
    if t not in _UTTERANCE_TYPES:
        return [], "excluded"  # attachment/system/mode/queue-operation/… 전량 제외
    msg = d.get("message")
    if not isinstance(msg, dict):
        return [], "excluded"
    role = msg.get("role") or t
    content = msg.get("content")
    # 최상위 레코드 timestamp(ISO 문자열) 추출 — mine --days cutoff 비교의 근거.
    # 부재 시 "" 유지(fail-soft). 일부 레코드는 message.timestamp 에 있을 수 있어 보강 조회.
    ts = d.get("timestamp") or (msg.get("timestamp") if isinstance(msg, dict) else "") or ""
    items = []

    if isinstance(content, str):
        body = _clean(content.strip())
        if body:
            inj = 1 if body.startswith(_SYSTEM_PREFIXES) else 0
            items.append({"utt": True, "role": role, "kind": "text", "body": body,
                          "injected": inj, "ts": ts})
        return (items, "ok") if items else ([], "excluded")

    if isinstance(content, list):
        for b in content:
            if not isinstance(b, dict):
                continue
            bt = b.get("type")
            if bt in ("text", "thinking"):
                body = _block_text(b)
                if body:
                    # 모델 출력(assistant text/thinking)은 주입 아님. user 리스트-텍스트만 프리픽스 검사.
                    inj = 1 if (role == "user" and body.startswith(_SYSTEM_PREFIXES)) else 0
                    items.append({"utt": True, "role": role, "kind": bt, "body": body,
                                  "injected": inj, "ts": ts})
            elif bt == "tool_use":
                name = b.get("name") or "?"
                payload = b.get("input") or {}
                h = hashlib.sha1(
                    _clean(json.dumps([name, payload], ensure_ascii=False, sort_keys=True)).encode("utf-8")
                ).hexdigest()
                items.append({"tool": True, "role": role, "name": name,
                              "hash": h, "first_line": _tool_first_line(payload)})
            elif bt == "tool_result":
                payload = b.get("content")
                h = hashlib.sha1(
                    _clean(json.dumps(payload, ensure_ascii=False, sort_keys=True)).encode("utf-8")
                ).hexdigest()
                items.append({"tool": True, "role": role, "name": "tool_result",
                              "hash": h, "first_line": _tool_first_line(payload)})
        return (items, "ok") if items else ([], "excluded")

    return [], "excluded"


# ── DB ───────────────────────────────────────────────────────────────────────

def _connect(db_path):
    import sqlite3
    os.makedirs(os.path.dirname(os.path.abspath(db_path)) or ".", exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=5.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def _ensure_schema(conn, allow_rebuild=False):
    # 먼저 meta 만 만들어 저장된 schema_version 을 읽는다.
    conn.execute("CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT)")
    row = conn.execute("SELECT v FROM meta WHERE k='schema_version'").fetchone()
    stored = int(row[0]) if row and str(row[0]).isdigit() else None
    if stored is not None and stored != SCHEMA_VERSION:
        if not allow_rebuild:
            raise _SchemaMismatch(stored, SCHEMA_VERSION)
        # 재구축: 파생 테이블만 드롭(원본 JSONL 무관·무손실). index 가 전량 재파싱한다.
        conn.executescript(
            "DROP TABLE IF EXISTS messages_fts;"
            "DROP TABLE IF EXISTS tool_records;"
            "DROP TABLE IF EXISTS files;"
        )
        conn.execute("DELETE FROM meta WHERE k='schema_version'")
        stored = None
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT);
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY,
            path TEXT UNIQUE,
            profile TEXT,
            session TEXT,
            mtime REAL,
            size INTEGER,
            indexed_at TEXT,
            msg_count INTEGER,
            tool_count INTEGER,
            excluded_count INTEGER,
            broken_count INTEGER
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
            body,
            profile UNINDEXED,
            session UNINDEXED,
            line_no UNINDEXED,
            role UNINDEXED,
            kind UNINDEXED,
            file_id UNINDEXED,
            ts UNINDEXED,
            injected UNINDEXED
        );
        CREATE TABLE IF NOT EXISTS tool_records (
            file_id INTEGER,
            line_no INTEGER,
            role TEXT,
            name TEXT,
            tool_hash TEXT,
            first_line TEXT,
            occurrences INTEGER DEFAULT 1,
            UNIQUE(file_id, tool_hash)
        );
        """
    )
    if stored is None:
        conn.execute("INSERT OR REPLACE INTO meta(k,v) VALUES('schema_version',?)",
                     (str(SCHEMA_VERSION),))
    conn.commit()


def _assert_version(conn):
    """읽기 명령 진입 가드 — 저장 schema_version 이 현재와 다르면 _SchemaMismatch.
    파생 db 는 재구축 가능하므로 침묵 대신 명시 거부(안내 후 재구축 요구)."""
    row = conn.execute("SELECT v FROM meta WHERE k='schema_version'").fetchone()
    stored = int(row[0]) if row and str(row[0]).isdigit() else None
    if stored is not None and stored != SCHEMA_VERSION:
        raise _SchemaMismatch(stored, SCHEMA_VERSION)


def _acquire_lock(db_path):
    """flock 단일 writer. 점유 중이면 None(대기 금지). 성공 시 열린 fd 반환."""
    lock_path = db_path + ".lock"
    os.makedirs(os.path.dirname(os.path.abspath(lock_path)) or ".", exist_ok=True)
    fd = open(lock_path, "w")
    try:
        fcntl.flock(fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (OSError, IOError):
        fd.close()
        return None
    return fd


# ── index ────────────────────────────────────────────────────────────────────

def index(db_path, roots, verbose=False, rebuild=False):
    """다중 프로필 루트를 증분(mtime+size) 인덱스. 반환: 통계 dict.

    락 실패 시 예외 대신 {'lock_busy': True} 반환(호출부가 exit 4).
    스키마 버전 불일치 시 {'schema_mismatch': (stored, current)} 반환(호출부가 exit 6)
    — rebuild=True 면 파생 테이블 재구축 후 전량 재인덱스.
    """
    lock = _acquire_lock(db_path)
    if lock is None:
        return {"lock_busy": True}
    conn = _connect(db_path)
    try:
        try:
            _ensure_schema(conn, allow_rebuild=rebuild)
        except _SchemaMismatch as e:
            return {"schema_mismatch": (e.stored, e.current)}
        stats = {"files_seen": 0, "files_parsed": 0, "files_skipped": 0,
                 "msg_indexed": 0, "tool_indexed": 0, "tool_deduped": 0,
                 "excluded": 0, "broken": 0}
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        for rp, alias, session in iter_jsonl_files(roots):
            stats["files_seen"] += 1
            try:
                st = os.stat(rp)
            except OSError:
                continue
            row = conn.execute(
                "SELECT id, mtime, size FROM files WHERE path=?", (rp,)
            ).fetchone()
            if row is not None and row[1] == st.st_mtime and row[2] == st.st_size:
                stats["files_skipped"] += 1
                continue

            # 변경/신규 → 재파싱. 기존 파생 행 제거 후 재삽입(멱등).
            if row is not None:
                fid = row[0]
                conn.execute("DELETE FROM messages_fts WHERE file_id=?", (fid,))
                conn.execute("DELETE FROM tool_records WHERE file_id=?", (fid,))
            else:
                fid = None

            msg_n = tool_n = exc_n = brk_n = dedup_n = 0
            seen_tool = set()
            fts_rows = []
            tool_rows = {}
            try:
                fh = open(rp, encoding="utf-8", errors="replace")
            except OSError:
                continue
            with fh:
                for line_no, line in enumerate(fh, start=1):
                    items, status = classify_line(line)
                    if status == "broken":
                        brk_n += 1
                        continue
                    if status == "excluded":
                        exc_n += 1
                        continue
                    for it in items:
                        if it.get("utt"):
                            fts_rows.append((it["body"], alias, session, line_no,
                                             it["role"], it["kind"], None,
                                             it.get("ts", ""), it.get("injected", 0)))
                            msg_n += 1
                        else:  # tool
                            key = it["hash"]
                            if key in seen_tool:
                                # 동일 도구덤프 반복 dedup(같은 파일 내) — 카운트만 증가
                                tool_rows[key][6] += 1
                                dedup_n += 1
                            else:
                                seen_tool.add(key)
                                tool_rows[key] = [None, line_no, it["role"], it["name"],
                                                  key, it["first_line"], 1]
                                tool_n += 1

            # files 행 확정(파일 id 필요 → upsert 먼저)
            if fid is None:
                cur = conn.execute(
                    "INSERT INTO files(path,profile,session,mtime,size,indexed_at,"
                    "msg_count,tool_count,excluded_count,broken_count) "
                    "VALUES(?,?,?,?,?,?,?,?,?,?)",
                    (rp, alias, session, st.st_mtime, st.st_size, now,
                     msg_n, tool_n, exc_n, brk_n),
                )
                fid = cur.lastrowid
            else:
                conn.execute(
                    "UPDATE files SET mtime=?,size=?,indexed_at=?,msg_count=?,"
                    "tool_count=?,excluded_count=?,broken_count=? WHERE id=?",
                    (st.st_mtime, st.st_size, now, msg_n, tool_n, exc_n, brk_n, fid),
                )
            conn.executemany(
                "INSERT INTO messages_fts(body,profile,session,line_no,role,kind,file_id,ts,injected) "
                "VALUES(?,?,?,?,?,?,?,?,?)",
                [(b, p, s, ln, ro, ki, fid, ts, inj)
                 for (b, p, s, ln, ro, ki, _f, ts, inj) in fts_rows],
            )
            conn.executemany(
                "INSERT INTO tool_records(file_id,line_no,role,name,tool_hash,first_line,occurrences) "
                "VALUES(?,?,?,?,?,?,?)",
                [(fid, ln, ro, nm, hh, fl, oc) for (_f, ln, ro, nm, hh, fl, oc) in tool_rows.values()],
            )
            conn.commit()

            stats["files_parsed"] += 1
            stats["msg_indexed"] += msg_n
            stats["tool_indexed"] += tool_n
            stats["tool_deduped"] += dedup_n
            stats["excluded"] += exc_n
            stats["broken"] += brk_n
            if verbose:
                sys.stderr.write("  indexed %s/%s msg=%d tool=%d\n" % (alias, session[:8], msg_n, tool_n))
        return stats
    finally:
        conn.close()
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
        lock.close()


# ── search / show ─────────────────────────────────────────────────────────────

def search(db_path, query, limit=10):
    """FTS5 검색. 반환: [{ref, profile, session, line_no, role, kind, excerpt}]."""
    if not os.path.isfile(db_path):
        return None
    conn = _connect(db_path)
    try:
        _assert_version(conn)  # 불일치 시 _SchemaMismatch 전파(아래 except 밖)
        try:
            rows = conn.execute(
                "SELECT profile, session, line_no, role, kind, "
                "snippet(messages_fts,0,'[',']','…',12) "
                "FROM messages_fts WHERE messages_fts MATCH ? "
                "ORDER BY rank LIMIT ?",
                (query, limit),
            ).fetchall()
        except _SchemaMismatch:
            raise
        except Exception as e:  # noqa: BLE001 — FTS 구문오류 등은 호출부에 전달
            raise ValueError("FTS 질의 오류: %s" % e)
    finally:
        conn.close()
    out = []
    for prof, sess, ln, role, kind, snip in rows:
        excerpt = re.sub(r"\s+", " ", snip or "").strip()
        out.append({
            "ref": "%s/%s#%d" % (prof, sess, ln),
            "profile": prof, "session": sess, "line_no": ln,
            "role": role, "kind": kind, "excerpt": excerpt,
        })
    return out


_REF_RE = re.compile(r"^([^/]+)/(.+)#(\d+)$")


def show(db_path, ref):
    """ref 원문 행을 원본 JSONL에서 read-only 재조회. 반환: (path, line_no, raw)|None."""
    m = _REF_RE.match(ref.strip())
    if not m:
        raise ValueError("ref 형식 오류(기대: 프로필/세션#행): %s" % ref)
    prof, sess, ln = m.group(1), m.group(2), int(m.group(3))
    if not os.path.isfile(db_path):
        return None
    conn = _connect(db_path)
    try:
        _assert_version(conn)
        row = conn.execute(
            "SELECT path FROM files WHERE profile=? AND session=?", (prof, sess)
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return None
    path = row[0]
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8", errors="replace") as f:
        for i, line in enumerate(f, start=1):
            if i == ln:
                return path, ln, line.rstrip("\n")
    return None


# ── mine ──────────────────────────────────────────────────────────────────────

# 반복 패턴 후보 신호군 — probe 택소노미와 정합(설계 M1 probe-gap 환류).
# behavior=True 인 신호군은 행동경계형이라 후보에 [probe-gap] 태그를 붙인다.
#
# ★신호 특이화(R1 적대검증 반영): 'return'·'context'·'clear'·'verdict' 같은 흔한 코드/작업 단어
#   단독 prefix 는 평범한 코드 대화를 전부 오탐한다(실측: verdict-mismatch 가 147세션 중 105세션 매칭).
#   따라서 각 신호를 **개념토큰 AND 실패마커** FTS5 불리언 식으로 좁힌다 — 개념어만으로는 매칭 안 되고
#   실패를 지시하는 마커가 같은 발화에 공존해야 후보가 된다. (인접 phrase 대신 동일-발화 AND —
#   한국어 어순 유연성에 견고). friction-rework 만은 reflect.py 식 '사람 교정 어휘'라 OR 유지.
MINE_SIGNALS = [
    {"label": "submit-return", "behavior": True,
     "expr": '("return"* OR "제출"* OR "submit"*) '
             'AND ("미제출" OR "재전송"* OR "안 눌"* OR "재발화"* OR "not_firing"* OR "blindspot"*)'},
    {"label": "kill-orphan", "behavior": True,
     "expr": '("kill"* OR "죽였" OR "죽임") '
             'AND ("고아" OR "orphan"* OR "부모 체인"* OR "오판"* OR "kill_judgment"*)'},
    {"label": "exit0-artifact", "behavior": True,
     "expr": '("산출물" OR "빌드"* OR "artifact"*) '
             'AND ("미확인" OR "성공했는데" OR "성공인데" OR "exit0_artifact"* OR "만 믿"*)'},
    {"label": "verdict-mismatch", "behavior": True,
     "expr": '("verdict"* OR "판정"*) '
             'AND ("대상 불일치" OR "target_mismatch"* OR "엉뚱"* OR "stale verdict"* OR "다른 태스크")'},
    {"label": "ctx-false-clear", "behavior": True,
     "expr": '("context"* OR "컨텍스트" OR "clear"*) '
             'AND ("오판" OR "false-clear"* OR "false_clear"* OR "threshold"* OR "자기보고 맹신")'},
    {"label": "friction-rework", "behavior": False,
     "expr": '"틀렸"* OR "다시 해"* OR "되돌려"* OR "그게 아니"* OR "wrong again"'},
]

# 자기참조 오염(R1 적대검증) — probe/게이트 시스템 자체를 '논의'한 세션이 반복 후보로 집계되는 오염을
# 결정론으로 완화한다. 아래 캠페인 메타 어휘가 (주입 아닌) 실발화에 등장한 세션은 후보 집계에서 제외하고
# 제외 수를 노출한다. 완전 차단은 불가능(실패를 실제로 겪으면서 도구도 언급한 세션은 함께 제외됨) —
# SHADOW 후보라 precision 우선의 보수적 선택. 한계는 docstring·STATUS 에 명시.
META_VOCAB = [
    "actprobe", "txindex", "probe-gap", "probe_runs", "kill-preflight",
    "verdict-match", "ctx-compare", "javis_actprobe", "javis_txindex",
    "2층 기억", "행동경계 게이트", "영수증 대조", "quality_gates_2layer",
]


def _meta_contaminated_sessions(conn):
    """캠페인 메타 어휘가 (주입 아닌) 실발화에 등장한 세션 집합 — 자기참조 오염 완화용.
    role 무관(사람·assistant 논의 모두)·injected=0(주입 디렉티브의 메타어휘는 오염 아님)."""
    expr = " OR ".join('"%s"*' % t.replace('"', '') for t in META_VOCAB)
    try:
        rows = conn.execute(
            "SELECT DISTINCT session FROM messages_fts WHERE messages_fts MATCH ? AND injected=0",
            (expr,),
        ).fetchall()
    except Exception:
        return set()
    return {r[0] for r in rows}


def _mine_candidates(conn, days, min_sessions):
    """인덱스에서 신호군별 재발(distinct 세션 수) 후보 추출.

    반환: (candidates, no_ts_skipped, meta_excluded)
      candidates = [{label, behavior, sessions(int), example(str), key(hash8)}]
      no_ts_skipped = cutoff 적용 상태에서 ts 부재로 집계에서 제외된 행 수(침묵 제거).
      meta_excluded = 자기참조 오염(캠페인 메타 어휘 등장)으로 후보 집계에서 제외된 세션 수.

    신호 특이화: 각 신호는 MINE_SIGNALS[].expr(개념토큰 AND 실패마커 FTS5 불리언)로 매칭 —
    흔한 코드 단어 단독 오탐을 차단(R1 반영). days>0 이면 ISO 사전순 cutoff.
    **cutoff 하 ts 부재 행**: 포함하면 '최근성'이 거짓이 되므로 제외하고 no_ts_skipped 로 노출.
    **자기참조 오염**: probe/게이트 시스템을 논의한 세션(_meta_contaminated_sessions)은
    후보 집계에서 제외하고 meta_excluded 로 노출(SHADOW precision 우선·완전차단 불가는 STATUS 명시).
    """
    cutoff = None
    if days and days > 0:
        cutoff = time.strftime("%Y-%m-%dT%H:%M:%SZ",
                               time.gmtime(time.time() - days * 86400))
    meta_sessions = _meta_contaminated_sessions(conn)
    out = []
    no_ts_skipped = 0
    meta_hit = set()
    for sig in MINE_SIGNALS:
        try:
            # injected=0: 시스템 주입 boilerplate 제외 — 진짜 사람 발화만 집계.
            rows = conn.execute(
                "SELECT session, ts, body FROM messages_fts "
                "WHERE messages_fts MATCH ? AND role='user' AND injected=0",
                (sig["expr"],),
            ).fetchall()
        except Exception:
            continue
        sessions = set()
        example = ""
        for sess, ts, body in rows:
            if cutoff:
                if not ts:
                    no_ts_skipped += 1  # ts 부재 → cutoff 하 집계 제외(침묵 금지)
                    continue
                if ts < cutoff:
                    continue            # cutoff 이전(오래됨) → 제외
            if sess in meta_sessions:
                meta_hit.add(sess)      # 자기참조 오염 세션 → 후보 집계 제외
                continue
            sessions.add(sess)
            if not example:
                example = re.sub(r"\s+", " ", body)[:80]
        if len(sessions) >= min_sessions:
            key = hashlib.sha1(("txindex:mine:" + sig["label"]).encode("utf-8")).hexdigest()[:8]
            out.append({"label": sig["label"], "behavior": sig["behavior"],
                        "sessions": len(sessions), "example": example, "key": key})
    return out, no_ts_skipped, len(meta_hit)


def _already_logged(ledger_path, key):
    if not os.path.isfile(ledger_path):
        return False
    try:
        text = open(ledger_path, encoding="utf-8", errors="replace").read()
    except OSError:
        return False
    return ("txindex:mine" in text) and (("key=%s" % key) in text)


def _transcript_effort(pack_bin, project_dir):
    """javis_transcript_stats.py --latest --oneline 읽기전용 호출. 실패 시 None(강등)."""
    script = os.path.join(pack_bin, "javis_transcript_stats.py")
    if not os.path.isfile(script):
        return None
    env = dict(os.environ)
    if project_dir:
        env["CYS_SESSION_PROJECT_DIR"] = project_dir
    try:
        p = subprocess.run(
            [sys.executable, script, "--latest", "--oneline"],
            capture_output=True, text=True, timeout=15, env=env, **NOWIN,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if p.returncode != 0:
        return None
    return p.stdout.strip() or None


def mine(db_path, days, ledger_path, min_sessions=3, pack_bin=None, project_dir=None):
    """반복 패턴 후보 추출 → RSI_LEDGER SHADOW 후보 append(멱등).

    반환: 결과 dict. 자동 저장·자동 주입 없음 — append 는 SHADOW 후보일 뿐.
    min_sessions 기본 3 — 2세션짜리 우연 공출현(R1 오탐)을 배제하는 보수적 기본값.
    """
    result = {"candidates": 0, "appended": 0, "effort": None, "skipped": 0,
              "no_ts_skipped": 0, "meta_excluded": 0, "reason": ""}
    if not os.path.isfile(db_path):
        result["reason"] = "db 없음"
        return result
    if pack_bin is None:
        # transcript_stats 는 라이브 팩에 있다(read-only 호출은 브리프상 허용). 부재 시 강등.
        pack_dir = os.environ.get("CYS_PACK_DIR") or os.path.expanduser("~/.cys/pack")
        pack_bin = os.path.join(pack_dir, "bin")
    result["effort"] = _transcript_effort(pack_bin, project_dir)  # 강등 안전(None 허용)

    conn = _connect(db_path)
    try:
        _assert_version(conn)
        cands, no_ts_skipped, meta_excluded = _mine_candidates(conn, days, min_sessions)
    finally:
        conn.close()
    result["candidates"] = len(cands)
    result["no_ts_skipped"] = no_ts_skipped
    result["meta_excluded"] = meta_excluded
    if not cands:
        result["reason"] = "후보 없음"
        return result

    date = time.strftime("%Y-%m-%d", time.gmtime())
    lines = []
    for c in cands:
        if _already_logged(ledger_path, c["key"]):
            result["skipped"] += 1
            continue
        tag = " [probe-gap]" if c["behavior"] else ""
        line = ("- [txindex:mine SHADOW] %s 반복신호 '%s' %d개 세션 재발(days=%s)"
                " — 반복 결함 후보(자동적용0·사람검토).%s 근거 예: \"%s\" key=%s\n"
                % (date, c["label"], c["sessions"], days, tag, c["example"], c["key"]))
        lines.append(line)

    if not lines:
        result["reason"] = "전 후보 이미 적재됨(멱등)"
        return result
    try:
        os.makedirs(os.path.dirname(ledger_path) or ".", exist_ok=True)
        prev = ""
        if os.path.isfile(ledger_path):
            prev = open(ledger_path, encoding="utf-8", errors="replace").read()
        with open(ledger_path, "a", encoding="utf-8") as f:
            if prev and not prev.endswith("\n"):
                f.write("\n")
            for line in lines:
                f.write(line)
        result["appended"] = len(lines)
        result["reason"] = "후보 적재"
    except OSError as e:
        result["reason"] = "ledger 쓰기 실패: %s" % e
    return result


# ── CLI ────────────────────────────────────────────────────────────────────────

def cmd_index(args):
    roots = read_roots(args.roots_file)
    if not roots:
        print("ERROR: 인덱스 루트 없음", file=sys.stderr)
        return EXIT_USAGE
    t0 = time.time()
    stats = index(args.db, roots, verbose=args.verbose, rebuild=args.rebuild)
    if stats.get("lock_busy"):
        print("ERROR: 다른 writer 가 락 점유 중 — 즉시 종료(대기 안 함)", file=sys.stderr)
        return EXIT_LOCK_BUSY
    if stats.get("schema_mismatch"):
        old, new = stats["schema_mismatch"]
        print("ERROR: schema_version 불일치(db=%s, 현재=%s) — 파생 db 재구축 필요. "
              "`index --rebuild` 로 재인덱스하거나 db 파일 삭제 후 재실행." % (old, new),
              file=sys.stderr)
        return EXIT_SCHEMA
    stats["elapsed_sec"] = round(time.time() - t0, 2)
    stats["roots"] = roots
    if args.json:
        print(json.dumps(stats, ensure_ascii=False, indent=2))
    else:
        print("index: 파일 %d(파싱 %d·skip %d) · 발화 %d · 도구 %d(dedup %d) · 제외 %d · 깨짐 %d · %.2fs"
              % (stats["files_seen"], stats["files_parsed"], stats["files_skipped"],
                 stats["msg_indexed"], stats["tool_indexed"], stats["tool_deduped"],
                 stats["excluded"], stats["broken"], stats["elapsed_sec"]))
    return EXIT_OK


def _print_schema_mismatch(e):
    print("ERROR: schema_version 불일치(db=%s, 현재=%s) — `index --rebuild` 로 재구축 후 재실행."
          % (e.stored, e.current), file=sys.stderr)


def cmd_search(args):
    try:
        res = search(args.db, args.query, args.limit)
    except _SchemaMismatch as e:
        _print_schema_mismatch(e)
        return EXIT_SCHEMA
    except ValueError as e:
        print("ERROR: %s" % e, file=sys.stderr)
        return EXIT_USAGE
    if res is None:
        print("ERROR: db 없음 (%s) — 먼저 index" % args.db, file=sys.stderr)
        return EXIT_NOT_FOUND
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        if not res:
            print("(검색 결과 없음)")
        for r in res:
            print("%s  [%s/%s]  %s" % (r["ref"], r["role"], r["kind"], r["excerpt"]))
    return EXIT_OK


def cmd_show(args):
    try:
        res = show(args.db, args.ref)
    except _SchemaMismatch as e:
        _print_schema_mismatch(e)
        return EXIT_SCHEMA
    except ValueError as e:
        print("ERROR: %s" % e, file=sys.stderr)
        return EXIT_USAGE
    if res is None:
        print("ERROR: ref 해당 원문 없음 (%s)" % args.ref, file=sys.stderr)
        return EXIT_NOT_FOUND
    path, ln, raw = res
    if args.json:
        print(json.dumps({"ref": args.ref, "path": path, "line_no": ln, "raw": raw},
                         ensure_ascii=False, indent=2))
    else:
        print("# %s (line %d)" % (path, ln))
        print(raw)
    return EXIT_OK


def cmd_mine(args):
    try:
        res = mine(args.db, args.days, args.ledger,
                   min_sessions=args.min_sessions, project_dir=args.project_dir)
    except _SchemaMismatch as e:
        _print_schema_mismatch(e)
        return EXIT_SCHEMA
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print("mine: 후보 %d · 적재 %d · skip(멱등) %d · no_ts_skipped %d · meta_excluded %d · effort=%s (%s)"
              % (res["candidates"], res["appended"], res["skipped"],
                 res["no_ts_skipped"], res["meta_excluded"], res["effort"] or "-", res["reason"]))
    return EXIT_OK


def _self_test():
    import tempfile
    failures = []

    def urow(content, sid="sess-a", ts="2026-07-18T10:00:00.000Z"):
        return json.dumps({"type": "user", "sessionId": sid, "timestamp": ts,
                           "message": {"role": "user", "content": content}}, ensure_ascii=False)

    def arow_text(text, sid="sess-a"):
        return json.dumps({"type": "assistant", "sessionId": sid,
                           "message": {"role": "assistant",
                                       "content": [{"type": "text", "text": text}]}}, ensure_ascii=False)

    def arow_tooluse(name, inp, sid="sess-a"):
        return json.dumps({"type": "assistant", "sessionId": sid,
                           "message": {"role": "assistant",
                                       "content": [{"type": "tool_use", "name": name, "input": inp}]}},
                          ensure_ascii=False)

    def urow_toolresult(payload, sid="sess-a"):
        return json.dumps({"type": "user", "sessionId": sid,
                           "message": {"role": "user",
                                       "content": [{"type": "tool_result", "content": payload}]}},
                          ensure_ascii=False)

    with tempfile.TemporaryDirectory(prefix="txindex-selftest-") as td:
        # 프로필 디렉토리 흉내(더미 프로필명): <td>/.claude-testalpha/projects/<proj>/*.jsonl
        proj = os.path.join(td, ".claude-testalpha", "projects", "-p")
        os.makedirs(proj)
        f1 = os.path.join(proj, "11111111-1111-1111-1111-111111111111.jsonl")
        NOISE = "ZZZTOOLNOISE_deadbeef"
        HUMAN = "QQQHUMANWORD_cafef00d"
        open(f1, "w", encoding="utf-8").write("\n".join([
            urow("사람 발화 " + HUMAN),                              # FTS 대상
            arow_text("assistant 텍스트 응답"),                      # FTS 대상
            arow_tooluse("Bash", {"command": "echo " + NOISE}),      # 도구 → FTS 제외
            urow_toolresult("tool 출력 " + NOISE),                   # 도구 → FTS 제외
            json.dumps({"type": "system", "content": "system " + NOISE}),      # 제외
            json.dumps({"type": "attachment", "content": "att " + NOISE}),     # 제외
            "{broken json line",                                     # 깨짐
            arow_tooluse("Bash", {"command": "echo " + NOISE}),      # 동일 덤프 → dedup
        ]) + "\n")

        roots_file = os.path.join(td, "roots.txt")
        open(roots_file, "w").write(proj + "\n")
        db = os.path.join(td, "t.db")

        # 1) index — 필터 화이트리스트 + dedup + broken fail-soft
        s1 = index(db, read_roots(roots_file))
        if s1.get("lock_busy"):
            failures.append("index 락 실패(예상 밖)")
        if s1["broken"] != 1:
            failures.append("broken 카운트 오류: %d (기대 1)" % s1["broken"])
        if s1["tool_deduped"] != 1:
            failures.append("dedup 카운트 오류: %d (기대 1)" % s1["tool_deduped"])
        # user str + assistant text = 2 발화
        if s1["msg_indexed"] != 2:
            failures.append("발화 인덱스 오류: %d (기대 2)" % s1["msg_indexed"])

        # 2) 필터 negative: 도구/시스템 잡음 토큰은 검색 안 됨, 사람 발화는 검색됨
        if search(db, NOISE, 10):
            failures.append("필터 위반: 도구/시스템 잡음(%s)이 FTS에서 검색됨" % NOISE)
        hits = search(db, HUMAN, 10)
        if not hits:
            failures.append("사람 발화(%s)가 검색 안 됨" % HUMAN)

        # 3) show 왕복
        if hits:
            got = show(db, hits[0]["ref"])
            if not got or HUMAN not in got[2]:
                failures.append("show 왕복 실패: %r" % (got,))

        # 4) 증분: 재실행 시 재파싱 0
        s2 = index(db, read_roots(roots_file))
        if s2["files_parsed"] != 0 or s2["files_skipped"] != 1:
            failures.append("증분 실패: parsed=%d skipped=%d (기대 0/1)"
                            % (s2["files_parsed"], s2["files_skipped"]))

        # 5) 심링크 dedup: 같은 실체 두 경로 → 1회 인덱스
        link = os.path.join(td, ".claude-testbeta", "projects")
        os.makedirs(os.path.dirname(link))
        os.symlink(os.path.join(td, ".claude-testalpha", "projects"), link)
        roots_file2 = os.path.join(td, "roots2.txt")
        open(roots_file2, "w").write(proj + "\n" + os.path.join(link, "-p") + "\n")
        db2 = os.path.join(td, "t2.db")
        s3 = index(db2, read_roots(roots_file2))
        if s3["files_parsed"] != 1:
            failures.append("심링크 dedup 실패: parsed=%d (기대 1)" % s3["files_parsed"])

        # 6) flock: 락 점유 중 index 즉시 실패
        lk = _acquire_lock(db)
        s4 = index(db, read_roots(roots_file))
        if lk is not None:
            fcntl.flock(lk.fileno(), fcntl.LOCK_UN)
            lk.close()
        if not s4.get("lock_busy"):
            failures.append("flock 실패: 락 점유 중인데 index 진행됨")

        # 7) mine 멱등: 재발 신호 2세션 → 후보, 재실행 시 중복 0
        proj_m = os.path.join(td, ".claude-testgamma", "projects", "-m")
        os.makedirs(proj_m)
        fm = os.path.join(proj_m, "22222222-2222-2222-2222-222222222222.jsonl")
        open(fm, "w", encoding="utf-8").write("\n".join([
            urow("이거 또 틀렸어 다시 해줘", sid="s1", ts="2026-07-18T10:00:00.000Z"),
            urow("kill 로 고아 프로세스 죽여", sid="s1", ts="2026-07-18T10:01:00.000Z"),
        ]) + "\n")
        fm2 = os.path.join(proj_m, "33333333-3333-3333-3333-333333333333.jsonl")
        open(fm2, "w", encoding="utf-8").write("\n".join([
            urow("그게 아니야 되돌려", sid="s2", ts="2026-07-18T11:00:00.000Z"),
            urow("orphan kill 판단 틀렸", sid="s2", ts="2026-07-18T11:01:00.000Z"),
        ]) + "\n")
        roots_m = os.path.join(td, "roots_m.txt")
        open(roots_m, "w").write(proj_m + "\n")
        dbm = os.path.join(td, "m.db")
        index(dbm, read_roots(roots_m))
        ledger = os.path.join(td, "RSI_LEDGER.md")
        m1 = mine(dbm, 0, ledger, min_sessions=2, project_dir=proj_m)
        if m1["appended"] < 1:
            failures.append("mine 후보 미적재: %s" % m1)
        body = open(ledger, encoding="utf-8").read() if os.path.isfile(ledger) else ""
        if "[probe-gap]" not in body:
            failures.append("mine probe-gap 태그 누락")
        if "[txindex:mine SHADOW]" not in body:
            failures.append("mine 계약 형식(- [txindex:mine SHADOW]) 누락")
        before = body
        m2 = mine(dbm, 0, ledger, min_sessions=2, project_dir=proj_m)
        after = open(ledger, encoding="utf-8").read()
        if m2["appended"] != 0 or before != after:
            failures.append("mine 멱등 위반: 재실행 시 중복 적재")

        # 8) days 필터 회귀 가드 (master 적발 결함) — 오래된 세션 제외 + ts 없는 행 no_ts_skipped.
        proj_d = os.path.join(td, ".claude-testgamma", "projects", "-days")
        os.makedirs(proj_d)
        recent_ts = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
        open(os.path.join(proj_d, "old0.jsonl"), "w", encoding="utf-8").write(
            urow("또 틀렸어 다시 해", sid="d-old", ts="2019-01-01T00:00:00.000Z") + "\n")
        open(os.path.join(proj_d, "rec1.jsonl"), "w", encoding="utf-8").write(
            urow("또 틀렸어", sid="d-rec1", ts=recent_ts) + "\n")
        open(os.path.join(proj_d, "rec2.jsonl"), "w", encoding="utf-8").write(
            urow("되돌려 그게 아니야", sid="d-rec2", ts=recent_ts) + "\n")
        open(os.path.join(proj_d, "nots.jsonl"), "w", encoding="utf-8").write(
            json.dumps({"type": "user", "sessionId": "d-nots",
                        "message": {"role": "user", "content": "다시 해 되돌려"}}) + "\n")
        roots_d = os.path.join(td, "roots_d.txt")
        open(roots_d, "w").write(proj_d + "\n")
        dbd = os.path.join(td, "d.db")
        index(dbd, read_roots(roots_d))
        cd = _connect(dbd)
        try:
            c7, skip7, _me7 = _mine_candidates(cd, 7, 2)
            c0, skip0, _me0 = _mine_candidates(cd, 0, 2)
        finally:
            cd.close()
        fr7 = [c for c in c7 if c["label"] == "friction-rework"]
        fr0 = [c for c in c0 if c["label"] == "friction-rework"]
        if not (len(fr7) == 1 and fr7[0]["sessions"] == 2):
            failures.append("days=7 필터 오작동(오래된 세션 미제외): fr7=%s" % fr7)
        if not (len(fr0) == 1 and fr0[0]["sessions"] == 4):
            failures.append("days=0 전기간 집계 오류: fr0=%s" % fr0)
        if skip7 < 1:
            failures.append("cutoff 하 ts 없는 행이 no_ts_skipped 로 집계 안 됨: skip7=%d" % skip7)
        if skip0 != 0:
            failures.append("cutoff 없는데 no_ts_skipped 발생: skip0=%d" % skip0)

    print(json.dumps({"self_test": "ok" if not failures else "fail",
                      "failures": failures}, ensure_ascii=False, indent=2))
    return EXIT_OK if not failures else EXIT_SELFTEST_FAIL


def main():
    ap = argparse.ArgumentParser(description="원시 전사 인덱스 (2층 기억 Layer 0)")
    ap.add_argument("--self-test", action="store_true", help="결정론 자기검증")
    sub = ap.add_subparsers(dest="cmd")

    pi = sub.add_parser("index", help="다중 프로필 증분 인덱스")
    pi.add_argument("--roots-file", help="루트 경로 목록 파일(생략 시 기본 3프로필)")
    pi.add_argument("--db", default=None)
    pi.add_argument("--json", action="store_true")
    pi.add_argument("--verbose", action="store_true")
    pi.add_argument("--rebuild", action="store_true",
                    help="schema_version 불일치 시 파생 테이블 재구축 후 전량 재인덱스")

    ps = sub.add_parser("search", help="FTS5 검색")
    ps.add_argument("query")
    ps.add_argument("--limit", type=int, default=10)
    ps.add_argument("--db", default=None)
    ps.add_argument("--json", action="store_true")

    ph = sub.add_parser("show", help="ref 원문 행 재조회(read-only)")
    ph.add_argument("ref")
    ph.add_argument("--db", default=None)
    ph.add_argument("--json", action="store_true")

    pm = sub.add_parser("mine", help="반복 패턴 후보 → RSI_LEDGER SHADOW append")
    pm.add_argument("--days", type=int, default=7)
    pm.add_argument("--ledger", default=None)
    pm.add_argument("--min-sessions", type=int, default=3, dest="min_sessions")
    pm.add_argument("--project-dir", default=None,
                    help="transcript_stats effort 산출용 세션 디렉토리")
    pm.add_argument("--db", default=None)
    pm.add_argument("--json", action="store_true")

    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    if not args.cmd:
        ap.print_help()
        return EXIT_USAGE

    if getattr(args, "db", None) is None:
        args.db = default_db_path()
    if args.cmd == "index":
        return cmd_index(args)
    if args.cmd == "search":
        return cmd_search(args)
    if args.cmd == "show":
        return cmd_show(args)
    if args.cmd == "mine":
        if args.ledger is None:
            round_dir = resolve_round_dir()
            if not round_dir:
                print("ERROR: _round 디렉토리를 찾지 못함 — --ledger 로 명시하거나 "
                      "env CYS_ROUND_DIR 설정(임의 생성 안 함)", file=sys.stderr)
                return EXIT_USAGE
            args.ledger = os.path.join(round_dir, "RSI_LEDGER.md")
        return cmd_mine(args)
    ap.print_help()
    return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())
