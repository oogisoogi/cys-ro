#!/usr/bin/env python3
"""portrait_cutout.py — 인물·사물 사진 → 배경을 지운 투명 그림(웹 히어로·발표 자료용) · 배경 걷기 + 입체 보정.

사용(사진 · 맥 전용 · macOS 14 이상 · Apple Vision):
  python3 portrait_cutout.py <원본> <출력.webp|출력.png> [--crop x0,y0,x1,y1(비율 0~1)] [--height 994] [--top-pad 40]
      [--fringe-box x0,y0,x1,y1(비율 · 밝은 테 채울 구역 · 여러 번 가능)]
사용(AI 생성 그림의 초록 #00FF00 바탕 · Vision 불필요 · Pillow 만):
  python3 portrait_cutout.py <원본> <출력.png|출력.webp> --green [--crop ...]

사진 단계(순서가 곧 품질):
 ① 맥 Vision 전경 가림(vision_mask.swift · foreground) — person 가림은 저해상이라 테두리가 번진다
 ② 가림 = 원해상도에서 단단하게(128 문턱) → 3px 깎기(MinFilter 7) = 배경 테(흰 벽·책장 등) 잘라 냄
 ③ 가장자리 색 정리(안쪽 7px 색을 바깥 띠로 번지게 · 원색과 반반) = 옅은 후광 제거
 ④ 미세 선명(UnsharpMask)
 ⑤ 축소 → 머리 위 여백(--top-pad) → 좌우 = 실 화소 경계(26 문턱 bbox)
 ⑥ 밝은 테 채우기(--fringe-box 구역 · 경계 근처 밝은 화소를 같은 줄 안쪽 옷 결로 덮음)
 ⑦ 입체감 = 국부 대비(r40 24%) + 대비 1.04 · 채도 1.05 + 밝은 곳 눌림(200 위 0.6배) + 윤곽 안쪽 음영(가장자리 0.8 → 안 1.0)
 ⑧ 저장 = WebP q92 알파 또는 PNG 32비트(256색 PNG 금지 — 피부에 계단 무늬)
초록 바탕 단계: 알파 = 초록 우세도(255 − (g − max(r,b))×255/180 을 0~255 로 자름) + 넘침 억제 g ← min(g, max(r,b)).

끝나면 한 줄 JSON(출력 경로·크기·바이트·알파 비율)을 찍는다.
종료 코드: 0 성공 · 1 처리 실패 · 2 사용법·입력 오류 · 3 맥이 아님 · 4 macOS 버전·swift 없음 · 5 Pillow 없음.
"""
import argparse, json, os, platform, shutil, subprocess, sys, tempfile
from pathlib import Path

MIN_MACOS = 14  # VNGenerateForegroundInstanceMaskRequest 도입 = macOS 14.0 (Apple 개발자 문서)
HERE = Path(__file__).resolve().parent
SWIFT_SCRIPT = HERE / 'vision_mask.swift'


def die(code, *lines):
    for ln in lines:
        print(ln, file=sys.stderr)
    sys.exit(code)


ap = argparse.ArgumentParser(description='사진·그림의 배경을 지워 투명 그림으로 오린다.')
ap.add_argument('src'); ap.add_argument('out')
ap.add_argument('--crop', default='0,0,1,1'); ap.add_argument('--height', type=int, default=994)
ap.add_argument('--top-pad', type=int, default=40); ap.add_argument('--fringe-box', action='append', default=[])
ap.add_argument('--green', action='store_true', help='AI 생성 그림의 초록(#00FF00) 바탕을 뺀다(Vision 불필요)')
a = ap.parse_args()

# ── 의존 점검(조용한 실패·자동 설치 금지) ──
try:
    from PIL import Image, ImageFilter, ImageEnhance, ImageChops, UnidentifiedImageError
except ImportError:
    die(5, 'Pillow(그림 처리 라이브러리)가 없습니다.',
        '설치: python3 -m pip install Pillow  — 설치 뒤 같은 명령을 다시 실행하세요.')

swift = None
if not a.green:
    if sys.platform != 'darwin':
        die(3, '맥 전용 기능입니다 — 사진 배경 지우기는 macOS 의 Apple Vision 으로만 동작합니다(윈도우·리눅스 불가).',
            '초록(#00FF00) 바탕 그림이라면 --green 을 붙이면 어느 기기에서나 됩니다.')
    ver = ''
    try:
        ver = subprocess.run(['/usr/bin/sw_vers', '-productVersion'], capture_output=True, text=True, timeout=10).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        ver = platform.mac_ver()[0]
    try:
        major = int(ver.split('.')[0])
    except ValueError:
        major = None
    if major is None:
        die(4, f'macOS 버전을 읽지 못했습니다(sw_vers 결과 「{ver}」).', f'이 기능은 macOS {MIN_MACOS} 이상이 필요합니다.')
    if major < MIN_MACOS:
        die(4, f'macOS {ver} 입니다 — 배경 지우기(Apple Vision 앞 물체 가림)는 macOS {MIN_MACOS} 이상에서만 됩니다.',
            '시스템 설정 → 일반 → 소프트웨어 업데이트에서 macOS 를 올린 뒤 다시 실행하세요.')
    swift = shutil.which('swift')
    devtools_ok = False
    if swift:
        try:
            devtools_ok = subprocess.run(['/usr/bin/xcode-select', '-p'], capture_output=True, timeout=10).returncode == 0
        except (OSError, subprocess.SubprocessError):
            devtools_ok = False
    if not swift or not devtools_ok:
        die(4, 'swift(애플 개발 도구)를 찾을 수 없습니다 — 배경 지우기는 swift 로 Apple Vision 을 부릅니다.',
            '설치: 터미널에서 xcode-select --install 실행 → 뜨는 창에서 「설치」(Command Line Tools · 무료).',
            '설치가 끝나면 같은 명령을 다시 실행하세요.')
    if not SWIFT_SCRIPT.is_file():
        die(1, f'동봉 파일 {SWIFT_SCRIPT.name} 이 스크립트 옆에 없습니다 — 스킬 폴더가 온전한지 확인하세요.')

# ── 입력 점검 ──
ext = Path(a.out).suffix.lower()
if ext not in ('.webp', '.png'):
    die(2, f'출력 파일은 .webp 또는 .png 여야 합니다(받은 것: {a.out}).')
try:
    cx = [float(v) for v in a.crop.split(',')]
    assert len(cx) == 4 and 0 <= cx[0] < cx[2] <= 1 and 0 <= cx[1] < cx[3] <= 1
except (ValueError, AssertionError):
    die(2, f'--crop 은 비율 4개 x0,y0,x1,y1(0~1 · x0<x1 · y0<y1)이어야 합니다(받은 것: {a.crop}).')
if not os.path.isfile(a.src):
    die(2, f'원본 파일이 없습니다: {a.src}')
if os.path.getsize(a.src) == 0:
    die(2, f'원본 파일이 비어 있습니다(0바이트): {a.src}')
try:
    im = Image.open(a.src); im.load(); im = im.convert('RGB')
except (UnidentifiedImageError, OSError) as e:
    die(2, f'그림 파일로 읽을 수 없습니다: {a.src}', f'(JPG·PNG·WebP 등 그림 파일인지, 내려받다 깨지지 않았는지 확인하세요 · {type(e).__name__})')
W0, H0 = im.size
src = im.crop((int(W0*cx[0]), int(H0*cx[1]), int(W0*cx[2]), int(H0*cx[3])))


def save_and_report(img):
    if ext == '.webp':
        img.save(a.out, 'WEBP', quality=92, method=6, alpha_quality=100)
    else:
        img.save(a.out, 'PNG', optimize=True)  # RGBA 32비트(팔레트 변환 안 함)
    A = img.split()[3]; h = A.histogram(); n = img.width * img.height
    print(json.dumps({'out': a.out, 'mode': 'green' if a.green else 'vision', 'size': list(img.size),
                      'bytes': os.path.getsize(a.out), 'opaque_pct': round(100*h[255]/n, 2),
                      'transparent_pct': round(100*h[0]/n, 2), 'partial_pct': round(100*(n-h[0]-h[255])/n, 2)},
                     ensure_ascii=False))


# ── 초록 바탕(AI 생성 그림) ──
if a.green:
    r, g, b = src.split()
    m = ImageChops.lighter(r, b)                                                  # max(r,b)
    A = ImageChops.subtract(g, m).point(lambda d: max(0, min(255, int(255 - d*255/180))))   # 초록 우세도 → 알파
    g2 = ImageChops.darker(g, m)                                                  # 넘침 억제 g ← min(g, max(r,b))
    out = Image.merge('RGBA', (r, g2, b, A))
    if A.getbbox() is None or A.point(lambda v: 255 if v >= 26 else 0).getbbox() is None:
        die(1, '남는 부분이 없습니다 — 그림 전체가 초록으로 판정됐습니다. 초록 바탕 그림이 맞는지 확인하세요.')
    save_and_report(out)
    sys.exit(0)

# ── 사진(맥 Vision) ──
# 임시 폴더(사용자 사진 사본 src.png · 가림 mask.png)는 가림을 메모리로 읽는 즉시 지운다 — 성공·실패·예외 모든 길에서.
tmp = tempfile.mkdtemp(prefix='portrait-cutout-')
try:
    sp = os.path.join(tmp, 'src.png'); mp = os.path.join(tmp, 'mask.png'); src.save(sp)
    res = subprocess.run([swift, str(SWIFT_SCRIPT), sp, mp, 'foreground'], capture_output=True, text=True,
                         env={**os.environ, 'TMPDIR': tmp})   # swift 자체 임시 폴더도 같은 곳에 → 함께 지워진다
    if res.returncode != 0 or not os.path.isfile(mp):
        msg = (res.stdout + res.stderr).strip().splitlines()
        die(1, 'Apple Vision 가림 뽑기에 실패했습니다' + (f': {msg[-1]}' if msg else '') + '.',
            '「앞 물체 0」이면 앞에 선 물체를 찾지 못한 것입니다 — 인물·사물이 또렷한 사진인지, --crop 범위가 맞는지 확인하세요.')
    M = Image.open(mp).convert('L').resize(src.size)   # convert 가 화소를 메모리로 읽는다 → 아래부터 임시 파일 불필요
finally:
    shutil.rmtree(tmp, ignore_errors=True)
hard = M.point(lambda v: 255 if v >= 128 else 0); er = hard.filter(ImageFilter.MinFilter(7)); inner = hard.filter(ImageFilter.MinFilter(15))
num = Image.composite(src, Image.new('RGB', src.size, (0, 0, 0)), inner)
nb = num.filter(ImageFilter.BoxBlur(12)).load(); wb = inner.filter(ImageFilter.BoxBlur(12)).load()
out = src.copy(); op = out.load(); sp_ = src.load(); ep = er.load(); ip = inner.load()
for y in range(src.height):
    for x in range(src.width):
        if ep[x, y] and not ip[x, y] and wb[x, y] > 8:
            k = 255.0 / wb[x, y]; r, g, b = nb[x, y]; s = sp_[x, y]
            op[x, y] = ((s[0] + min(255, int(r*k))) // 2, (s[1] + min(255, int(g*k))) // 2, (s[2] + min(255, int(b*k))) // 2)
out = out.filter(ImageFilter.UnsharpMask(radius=2.2, percent=70, threshold=2))
alpha = er.filter(ImageFilter.GaussianBlur(0.6)); rgba = out.copy(); rgba.putalpha(alpha)
bb = alpha.point(lambda v: 255 if v >= 26 else 0).getbbox()
if bb is None:
    die(1, '가림이 비었습니다 — 3px 깎기 뒤 남는 앞 물체가 없습니다(물체가 너무 작거나 가늘 수 있음). --crop 으로 물체 둘레를 좁혀 다시 해 보세요.')
c = rgba.crop((bb[0], bb[1], bb[2], src.height))
Hh = a.height; Ww = round(c.width * Hh / c.height); c = c.resize((Ww, Hh), Image.LANCZOS)
n = Image.new('RGBA', (Ww, Hh + a.top_pad), (0, 0, 0, 0)); n.paste(c, (0, a.top_pad)); c = n; W, H = c.size
p = c.load(); lum = lambda q: 0.3*q[0] + 0.59*q[1] + 0.11*q[2]
for fb in a.fringe_box:   # ⑥ 밝은 테 → 같은 줄 안쪽 옷 결
    f = [float(v) for v in fb.split(',')]; xs = range(int(W*f[0]), int(W*f[2])); ys = range(int(H*f[1]), int(H*f[3]))
    ref = sorted(lum(p[x, y]) for y in ys for x in xs if p[x, y][3] == 255) or [80]; base = ref[len(ref)//4]
    rightward = (f[0] + f[2]) / 2 < 0.5
    for y in ys:
        for x in xs:
            q = p[x, y]
            if q[3] == 0 or lum(q) <= base + 20: continue
            for d in range(1, 80):
                xx = x + d if rightward else x - d
                if not 0 <= xx < W: break
                r = p[xx, y]
                if r[3] == 255 and lum(r) <= base + 15:
                    s = p[min(W-1, max(0, xx + (6 if rightward else -6))), y]; p[x, y] = (s[0], s[1], s[2], q[3]); break
A = c.split()[3]; rgb = c.convert('RGB')
rgb = rgb.filter(ImageFilter.UnsharpMask(radius=40, percent=24, threshold=0)).filter(ImageFilter.UnsharpMask(radius=1.4, percent=50, threshold=2))
rgb = ImageEnhance.Color(ImageEnhance.Contrast(rgb).enhance(1.04)).enhance(1.05)
rgb = rgb.point([v if v <= 200 else int(200 + (v - 200) * 0.6) for v in range(256)] * 3)
S = A.filter(ImageFilter.GaussianBlur(28)); f = S.point(lambda v: int(255 * (0.80 + 0.20 * (min(1.0, (v/255.0 - 0.5)/0.5) if v > 127 else 0.0))))
rgb = ImageChops.multiply(rgb, Image.merge('RGB', (f, f, f))); rgb.putalpha(A)
save_and_report(rgb)
