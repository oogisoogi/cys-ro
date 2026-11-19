#!/usr/bin/env python3
"""Isolated probe: does real Claude Code emit OSC 7501 reports?
mode=noreply : never answer the 7501 query (today's cysd behaviour)
mode=reply   : answer the query with the spec reply (echo ESC ] 7501 ; ? + same terminator)
Writes <out>.raw (all pty bytes) and <out>.events.jsonl (timestamped 7501/OSC0 events + our actions).
"""
import os, pty, sys, time, json, select, re, signal, tempfile

mode, out = sys.argv[1], sys.argv[2]
cwd = tempfile.mkdtemp(prefix="p7501-", dir=os.environ.get("TMPDIR", "/tmp"))
env = {k: v for k, v in os.environ.items()
       if not k.startswith(("CYS_", "CMUX_", "CLAUDE_CODE_", "CLAUDECODE"))}
env["TERM"] = "xterm-256color"
argv = ["claude", "--model", "haiku", "--setting-sources", "project"] + os.environ.get("PROBE_EXTRA", "").split()

pid, fd = pty.fork()
if pid == 0:
    os.chdir(cwd)
    os.execvpe(argv[0], argv, env)

import fcntl, termios, struct
fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", 40, 120, 0, 0))
t0 = time.monotonic()
raw = bytearray()
ev = open(out + ".events.jsonl", "w")
def log(**k):
    k["t"] = round(time.monotonic() - t0, 3)
    ev.write(json.dumps(k, ensure_ascii=False) + "\n"); ev.flush()

OSC = re.compile(rb"\x1b\](7501|0|2);([^\x07\x1b]*)(\x07|\x1b\\)")
seen = 0
def pump(secs):
    global seen
    end = time.monotonic() + secs
    while time.monotonic() < end:
        r, _, _ = select.select([fd], [], [], 0.05)
        if not r:
            continue
        try:
            b = os.read(fd, 65536)
        except OSError:
            log(act="eof"); finish()
        if not b:
            log(act="eof"); finish()
        raw.extend(b)
        for m in OSC.finditer(bytes(raw), max(0, seen - 8192)):
            if m.end() <= seen:
                continue
            num, body, term = m.group(1).decode(), m.group(2).decode("utf-8", "replace"), m.group(3)
            log(osc=num, body=body, term="BEL" if term == b"\x07" else "ST")
            if num == "7501" and body.strip() == "?" and mode == "reply":
                os.write(fd, b"\x1b]7501;?" + term)
                log(act="answered-query")
        seen = len(raw)
    return True

def send(s, label):
    try:
        os.write(fd, s.encode()); log(act="send", what=label)
    except OSError:
        finish()

def finish():
    open(out + ".raw", "wb").write(bytes(raw))
    try:
        _, st = os.waitpid(pid, os.WNOHANG); log(act="wait", status=st)
    except Exception as e:
        log(act="wait-err", err=str(e))
    log(act="done", cwd=cwd, bytes=len(raw)); sys.exit(0)

pump(8)
send("\x1b[B", "down"); pump(1); send("\r", "enter(trust-yes)")
pump(6)
send("Reply with exactly the word: hi", "prompt1")
pump(1)
send("\r", "enter")
pump(25)
send("Use the Write tool to create a file named probe.txt containing hello", "prompt2-permission")
pump(1)
send("\r", "enter")
pump(25)
send("\x1b", "esc")
pump(6)
send("/exit", "exit")
pump(1)
send("\r", "enter")
alive = pump(8)
if alive:
    os.kill(pid, signal.SIGTERM); pump(2)
finish()
