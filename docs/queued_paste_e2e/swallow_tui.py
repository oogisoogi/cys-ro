#!/usr/bin/env python3
"""가짜 에이전트 TUI — **붙여넣기 처리 지연 중 도착한 Return 을 먹는** Claude Code 거동의 최소 모형
(TICKET=cysr-queued-paste-submit).

모형의 근거(벤더 이슈 anthropics/claude-code#28137 원문): 붙여넣기 처리에 지연이 있고 그 사이 Enter 가 오면 메시지가
붙여넣기 없이 전송되며, 붙여넣은 글은 **그 뒤에** 입력줄에 나타난다. 빈 입력줄의 Enter 는 아무것도 하지 않는다(Claude Code 와 같음).
현장(윈 dept-1 11-09 · cysr 1.1.14 · Claude Code 2.1.311)에서 입력줄에 `[Pasted text #9 +69 lines]` 가 미제출로 남은 모양이 이것이다.

  · raw 모드 · ESC[?2004h(괄호 붙여넣기 on).
  · 괄호 붙여넣기(ESC[200~ … ESC[201~)를 받으면 SWALLOW_LAG_MS 동안 '처리 중'이다. 그 사이의 CR 은 빈 줄 Enter(무동작 ·
    로그 CR_EATEN). 처리가 끝나면 입력줄에 `[Pasted text #k +n lines]` 를 그린다(n = 줄바꿈 수).
  · 처리가 끝난 뒤의 CR = 제출 — 본문 영역에 [SUBMIT] 줄 · 제출 로그(jsonl · Claude Code 세션 기록과 같은 user 레코드 꼴).
  · SWALLOW_FIRST_ONLY=1 이면 첫 붙여넣기만 지연한다(두 번째 배달부터는 정상 — 막힘 해소 뒤 후속 배달 검증용).

env: SWALLOW_LAG_MS(기본 900) · SWALLOW_FIRST_ONLY · SWALLOW_EAT_ALL · FAKE_RXLOG(받은 바이트 hex) · FAKE_SUBMITS(제출 jsonl)
"""
import json
import os
import sys
import termios
import threading
import time
import tty

LAG = int(os.environ.get("SWALLOW_LAG_MS", "900")) / 1000.0
FIRST_ONLY = os.environ.get("SWALLOW_FIRST_ONLY", "") == "1"
EAT_ALL = os.environ.get("SWALLOW_EAT_ALL", "") == "1"  # 모든 Return 을 먹는다(재시도 상한·경보 1회 검증용)
RXLOG = os.environ.get("FAKE_RXLOG", "")
SUBMITS = os.environ.get("FAKE_SUBMITS", "")
RULE = "─" * 60
lock = threading.Lock()
line = ""            # 입력줄에 보이는 글(자리표시 포함)
pending_paste = None  # 입력줄의 자리표시가 가리키는 실제 본문
processing_until = 0.0
paste_no = 0
body = []


def out(s):
    sys.stdout.write(s)
    sys.stdout.flush()


def log(path, rec):
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def paint():
    with lock:
        s = "\x1b[2J\x1b[H\r\n  fake-agent body\r\n"
        for b in body[-6:]:
            s += "  " + b + "\r\n"
        s += RULE + "\r\n" + "❯ " + line + "\r\n" + RULE + "\r\n" + "  ? for shortcuts"
        s += "\x1b[%d;%dH" % (4 + min(len(body), 6), 3 + len(line))
    out(s)


def finish_paste(text, k):
    global line, pending_paste
    time.sleep(LAG if (not FIRST_ONLY or k == 1) else 0.0)
    with lock:
        n = text.count("\n")
        line = "[Pasted text #%d +%d lines] " % (k, n) if n > 2 or len(text) > 800 else text
        pending_paste = text
    paint()


def submit():
    global line, pending_paste
    with lock:
        text = pending_paste if pending_paste is not None else line
        if not text.strip():
            return False
        body.append("[SUBMIT] " + text.splitlines()[0][:50])
        log(SUBMITS, {"type": "user", "message": {"content": text}, "t": time.time()})
        line, pending_paste = "", None
    paint()
    return True


def main():
    global processing_until, paste_no, line
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    tty.setraw(fd)
    out("\x1b[?2004h")
    paint()
    buf = b""
    try:
        while True:
            chunk = os.read(fd, 65536)
            if not chunk:
                break
            log(RXLOG, {"t": time.time(), "hex": chunk.hex()[:200], "n": len(chunk)})
            buf += chunk
            while buf:
                if buf.startswith(b"\x1b[200~"):
                    end = buf.find(b"\x1b[201~")
                    if end < 0:
                        break  # 붙여넣기 덜 왔다
                    text = buf[6:end].decode("utf-8", "replace")
                    buf = buf[end + 6:]
                    paste_no += 1
                    processing_until = time.time() + (LAG if (not FIRST_ONLY or paste_no == 1) else 0.0)
                    threading.Thread(target=finish_paste, args=(text, paste_no), daemon=True).start()
                    continue
                b = buf[:1]
                buf = buf[1:]
                if b in (b"\r", b"\n"):
                    if EAT_ALL or time.time() < processing_until:
                        log(RXLOG, {"t": time.time(), "event": "CR_EATEN"})  # 처리 중의 Enter = 빈 줄 Enter
                    else:
                        log(RXLOG, {"t": time.time(), "event": "CR_SUBMIT" if submit() else "CR_EMPTY"})
                elif b in (b"\x15", b"\x03"):
                    with lock:
                        line = ""
                    paint()
                elif b == b"\x1b":
                    pass
                else:
                    with lock:
                        line += b.decode("utf-8", "replace")
                    paint()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


if __name__ == "__main__":
    main()
