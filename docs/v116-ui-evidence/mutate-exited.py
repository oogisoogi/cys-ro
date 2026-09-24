# v116-exited-banner 뮤턴트 — 수리 줄을 하나씩 망가뜨려 시험이 빨개지는지(KILLED) 잰다.
# usage: python3 mutate-exited.py [--headless]   (--headless = 헤드리스 c17 로도 잰다 · CHS 환경변수 필요)
# (기록) `ESC[?6l` 을 영역 해제 뒤에 더하는 판은 등가(헤드리스 c17 16/16 같음) — 그래서 수리본에서 뺐다.
# 판정: 단위(bun test src/exitbanner.test.ts) 또는 헤드리스(c17) 중 하나라도 rc≠0 → KILLED. 적용 앵커가 정확히 1곳이 아니면 INVALID.
import subprocess, sys, os
H = os.path.dirname(os.path.abspath(__file__))
UI = os.path.abspath(os.path.join(H, '..', '..', 'ui'))
env = dict(os.environ, PATH=os.path.expanduser('~/.bun/bin') + ':' + os.environ['PATH'])
HEADLESS = '--headless' in sys.argv
M = [
 # (id, 파일, 원문, 뮤턴트, 헤드리스로도 잴지)
 ('E1 이동 제거(커서 자리 배너로 회귀)', 'src/exitbanner.ts',
  'return `${RESET_MARGINS}\\x1b[${bannerRow(v) + 1};1H${EXITED_BANNER}`;', 'return EXITED_BANNER;', True),
 ('E2 판독을 콜백 전(동기)으로', 'src/exitbanner.ts',
  '  term.write(filter.reset(), () => {\n    let seq = EXITED_BANNER;\n    try {\n      const buf = term.buffer.active;\n      seq = exitedBannerSeq({ rows: term.rows, cursorY: buf.cursorY, line: (y) => buf.getLine(buf.baseY + y)?.translateToString(true) ?? "" });\n    } catch {\n      /* 판독 실패 — 종전 자리(커서 다음 줄)로 강등 */\n    }\n    term.write(seq, done);\n  });',
  '  let seq = EXITED_BANNER;\n  try {\n    const buf = term.buffer.active;\n    seq = exitedBannerSeq({ rows: term.rows, cursorY: buf.cursorY, line: (y) => buf.getLine(buf.baseY + y)?.translateToString(true) ?? "" });\n  } catch {}\n  term.write(filter.reset(), () => {\n    term.write(seq, done);\n  });', False),
 ('E3 첫 내용 줄에서 멈춤(마지막 아님)', 'src/exitbanner.ts',
  '  for (let y = v.rows - 1; y > v.cursorY; y--) {\n    if (v.line(y).trim() !== "") return y;\n  }',
  '  for (let y = v.cursorY + 1; y < v.rows; y++) {\n    if (v.line(y).trim() !== "") return y;\n  }', False),
 ('E4 스크롤 영역 해제 제거', 'src/exitbanner.ts',
  'const RESET_MARGINS = "\\x1b[r";', 'const RESET_MARGINS = "";', True),
 ('E5 영역 해제 대신 원점 모드만 끔', 'src/exitbanner.ts',
  'const RESET_MARGINS = "\\x1b[r";', 'const RESET_MARGINS = "\\x1b[?6l";', True),
 ('E6 baseY 무시', 'src/exitbanner.ts',
  'buf.getLine(buf.baseY + y)', 'buf.getLine(y)', True),
 ('E7 판독 실패 강등 제거', 'src/exitbanner.ts',
  '    } catch {\n      /* 판독 실패 — 종전 자리(커서 다음 줄)로 강등 */\n    }\n    term.write(seq, done);',
  '    } finally {}\n    term.write(seq, done);', False),
 ('E8 done(snapToBottom) 미전달', 'src/exitbanner.ts',
  '    term.write(seq, done);', '    term.write(seq);', False),
 ('E9 순서 뒤집기(배너 뒤에 정합기 reset)', 'src/exitbanner.ts',
  '  term.write(filter.reset(), () => {', '  const r = filter.reset();\n  term.write("", () => {\n    term.write(r);', False),
 ('E10 배선 되돌리기(main.ts 종전 직접 쓰기)', 'src/main.ts',
  '    writeExitedBanner(term, trackFilter, snapToBottom);',
  '    const rest = trackFilter.flush();\n    if (rest.length > 0) term.write(rest);\n    term.write(trackFilter.reset());\n    term.write("\\r\\n\\x1b[31m[surface exited]\\x1b[0m\\r\\n", snapToBottom);', True),
 ('E11 잔여 방류 제거', 'src/exitbanner.ts',
  '  if (rest.length > 0) term.write(rest);\n', '', False),
]

def run(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)

res = []
for mid, f, a, b, hl in M:
    p = os.path.join(UI, f)
    src = open(p, encoding='utf8').read()
    if src.count(a) != 1:
        res.append((mid, 'INVALID', f'anchor x{src.count(a)}')); continue
    open(p, 'w', encoding='utf8').write(src.replace(a, b))
    try:
        u = run(['bun', 'test', 'src/exitbanner.test.ts'], UI)
        how = []
        if u.returncode != 0: how.append('unit')
        if HEADLESS and hl:
            bld = run(['sh', 'build.sh'], UI)
            if bld.returncode != 0: how.append('build')
            else:
                h = subprocess.run(['bun', os.path.join(H, 'v116-headless.ts')], cwd=H, env=dict(env, DIST=os.path.join(UI, 'dist'), ONLY='c17'), capture_output=True, text=True)
                if h.returncode != 0:
                    red = [l.split(' ')[1] for l in h.stdout.splitlines() if l.startswith('FAIL c17')]
                    how.append('headless[' + ','.join(red) + ']')
        res.append((mid, 'KILLED' if how else 'SURVIVED', ' + '.join(how)))
    finally:
        open(p, 'w', encoding='utf8').write(src)
if HEADLESS: run(['sh', 'build.sh'], UI)  # 원본으로 재빌드
for r in res: print(f'{r[1]:8} {r[0]} — {r[2]}')
k = sum(1 for r in res if r[1] == 'KILLED')
print(f'KILLED {k}/{len(res)}')
sys.exit(0 if k == len(res) else 1)
