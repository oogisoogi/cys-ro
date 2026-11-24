// (TICKET=cysr-1119-s6 · V1) 마스터 답 마크다운 → 블록 나무(순수 · DESIGN §6 V1 · VISUAL 카드 V1).
//
// 받는 글 = 믿지 못할 글(마스터 답). 나무는 「글 조각(문자열)」만 담는다 — 태그·속성·주소를 실행할 칸이 없다.
// 그리기(chat/md.ts)는 이 글을 textContent 로만 넣는다(HTML 해석 0 · href·src·title 0).
//
// 지원(설계 목록 그대로): 제목 h1~h3 · 문단 · 굵게/기울임 · 인라인 코드 · 울타리 · 목록(순서/점 · 들여쓴 항목 1단까지) ·
// GFM 표(구분 줄 있을 때만) · 링크 = 「글 (주소)」(주소는 보이는 글일 뿐 · 누를 것 0).
// 그 밖(인용 `>` · 가로줄 · h4+ · 그림 `![]()` · HTML 꼴 · 자동 링크 `<…>` · 실체 `&amp;`) = 글 그대로.
// (C-19) 답이 64KB(MD_MAX · UTF-16 글자 수)를 넘으면 앞쪽을 줄 경계에서 잘라 서식 · 나머지는 원문 그대로(raw).
// 시간: 블록·인라인 모두 선형(닫는 짝을 못 찾은 표지는 다시 찾지 않음 · 병적 입력 시험 = md.test.ts).
// (fix-1119-s6-adv) 원칙 = 「명령줄·경로·주소는 복사했을 때 원문과 글자가 같다」 가 표준(CommonMark) 충실도보다 위:
//   줄 = 모든 줄 끝 글자(\r\n · \r · \n · U+2028 · U+2029)로 먼저 가름(줄 안에 `.` 이 못 집는 글자 0 → 줄 정규식 되짚기 0) ·
//   역빗금 = 벗김 글자 아님(글자 그대로 · 표 칸 가르기에서만 `\|` = `|`) · 강조 = 낱말·경로·식 안이 아닌 경계에서만 ·
//   목록 안 울타리 = 울타리(여는 줄 들여쓰기만큼 걷음 · 코드 들여쓰기 보존).

// 「m」·「n」·「f」·「info」·「mark」 = 파서가 서식 표지로 쓴 원문 글자(그리기는 안 씀 · 시험의 글자 손실 대조가 이것만 뺌).
export type Inline =
  | { k: "text"; v: string }
  | { k: "strong"; m: string; c: Inline[] }
  | { k: "em"; m: string; c: Inline[] }
  | { k: "code"; n: number; v: string }
  | { k: "link"; c: Inline[]; url: string };

/** 항목 안 덧붙은 블록(항목 안 울타리 · 울타리 뒤 이어진 글). */
export type ItemBlock = { k: "pre"; v: string; f: string; info: string; end: string } | { k: "p"; c: Inline[] };

/** 목록 항목 — depth 0 = 맨 앞 · 1 = 들여쓴 항목(더 깊어도 1) · num = 적힌 번호 표지 그대로(「3.」·「10)」) · 점 목록 = null. */
export interface Item {
  depth: 0 | 1;
  num: string | null;
  mark: string;
  c: Inline[];
  more: ItemBlock[];
}

export type Block =
  | { k: "h"; level: 1 | 2 | 3; c: Inline[]; end: string }
  | { k: "p"; c: Inline[] }
  | { k: "pre"; v: string; f: string; info: string; end: string }
  | { k: "list"; ordered: boolean; items: Item[] }
  | { k: "table"; head: Inline[][]; rows: Inline[][][] }
  | { k: "raw"; v: string };

export const MD_MAX = 65536;

// (fix B1) 줄 정규식 = 머리만 맞추고 끝까지 훑는 꼬리(`(.*)$`) 0 — 나머지는 slice(줄 끝 글자가 줄 안에 있어도 되짚기 0).
const LINE_END = /\r\n|\r|\n|\u2028|\u2029/;
const FENCE = /^(`{3,}|~{3,})/;
const HEAD = /^ {0,3}(#{1,3})(?=[ \t]|$)/;
const ITEM = /^([ \t]*)([-*+]|\d{1,9}[.)])(?=[ \t]|$)/;
const DELIM = /^ {0,3}\|?[ \t]*:?-+:?(?:[ \t]*\|[ \t]*:?-+:?)*[ \t]*\|?$/; // 끝 빈칸을 걷은 줄에만(trimEnd · 되짚기 상한)
const SPACE = /\s/;
const WORD = /[\p{L}\p{N}]/u;

const OPEN_P = "([{\"'「『“‘<《〈【";
const CLOSE_BR = ")]}」』”’>》〉】";
const CLOSE_P = `${CLOSE_BR}"'.,;:!?…`;
const HANGUL = /[\uAC00-\uD7A3\u3131-\u318E]/;
const IDENT = /^[A-Za-z0-9_]+$/;

function lead(s: string): number {
  let n = 0;
  while (s[n] === " ") n++;
  return n;
}

/** 줄 머리 빈칸 n 개까지 걷음(코드 몸 · 들여쓰기 보존). */
function dedent(s: string, n: number): string {
  return s.slice(Math.min(n, lead(s)));
}

function indentOf(s: string): number {
  let n = 0;
  for (const ch of s) n += ch === "\t" ? 4 : 1;
  return n;
}

/** 표 한 줄 → 칸 글(앞뒤 파이프 걷음 · 탈출 `\|` 는 칸을 가르지 않음 · 글은 인라인 해석에서 `|` 로). */
function cells(line: string): string[] {
  let s = line.trim();
  if (s.startsWith("|")) s = s.slice(1);
  if (s.endsWith("|") && !s.endsWith("\\|")) s = s.slice(0, -1);
  const out: string[] = [];
  let cur = "";
  for (let i = 0; i < s.length; i++) {
    if (s[i] === "\\" && s[i + 1] === "|") {
      cur += "|"; // (fix H4) 표 칸 가르기에서만 `\|` = 한 글자 `|`(코드 칸 안도 · 복사하면 명령 그대로)
      i++;
    } else if (s[i] === "|") {
      out.push(cur.trim());
      cur = "";
    } else cur += s[i];
  }
  out.push(cur.trim());
  return out;
}

interface Fence {
  ch: string;
  n: number;
  ind: number;
  info: string;
}

/** 여는 울타리 — maxInd = 앞 빈칸 상한(맨 앞 = 3 · 항목 안 = 상한 없음). */
function fenceOpen(line: string, maxInd = 3): Fence | null {
  const ind = lead(line);
  if (ind > maxInd) return null;
  const t = line.slice(ind);
  const r = FENCE.exec(t);
  if (!r) return null;
  const info = t.slice(r[1].length).trim();
  // (fix2 N-B) 정보 글이 무엇이든 울타리 = 울타리(`bash title=run.sh` · `ts:src/a.ts` · `shell script`) — 단 정보 글에 울타리 글자가 들면 울타리 아님
  // (백틱 = CommonMark · 물결은 덧붙임 = `~~~ 물결 장식 ~~~` 장식 줄이 글로 남게 · L2)
  if (info.includes(r[1][0])) return null;
  return { ch: r[1][0], n: r[1].length, ind, info };
}

function fenceClose(line: string, f: Fence): boolean {
  const ind = lead(line);
  if (ind - f.ind > 3) return false;
  const t = line.slice(ind).trimEnd();
  if (t.length < f.n) return false;
  for (let x = 0; x < t.length; x++) if (t[x] !== f.ch) return false;
  return true;
}

/** 울타리 몸 읽기 — from = 여는 줄 다음 · inList = 항목 안(들여쓰기가 모자란 항목·맨 앞 줄에서 끝남) → [다음 줄, 블록]. */
function readFence(lines: string[], from: number, f: Fence, inList: boolean): [number, { k: "pre"; v: string; f: string; info: string; end: string }] {
  const body: string[] = [];
  let i = from;
  let end = ""; // 닫는 줄 원문(없으면 "" · 끝까지 = CommonMark)
  while (i < lines.length) {
    const l = lines[i];
    if (fenceClose(l, f)) {
      end = l.trim();
      i++;
      break;
    }
    // (fix2 N-G) 항목 안 울타리 = 몸이 덜 들여쓰여도 닫는 울타리까지 코드 · 닫히지 않으면 더 얕은 항목 줄·빈 줄 뒤 맨 앞 줄에서 끝(뒤 답을 삼키지 않음)
    if (inList && l.trim() !== "" && lead(l) < f.ind && (itemAt(l) !== null || (lead(l) === 0 && i > from && lines[i - 1].trim() === ""))) break;
    body.push(dedent(l, f.ind));
    i++;
  }
  return [i, { k: "pre", v: body.join("\n"), f: f.ch.repeat(f.n), info: f.info, end }];
}

/** 가로줄 꼴(`* * *` · `- - -`) = 목록 아님(글 그대로 · L1). */
function isRule(line: string): boolean {
  const t = line.replace(/[ \t]/g, "");
  return t.length >= 3 && (t[0] === "*" || t[0] === "-" || t[0] === "_") && t.split(t[0]).join("") === "";
}

/** 목록 항목 줄 — 내용 없는 항목·가로줄 꼴 = 항목 아님(글 그대로). col = 내용 첫 글자 자리. */
function itemAt(line: string): { ind: string; mk: string; content: string; col: number } | null {
  const m = ITEM.exec(line);
  if (!m) return null;
  let col = m[0].length;
  while (line[col] === " " || line[col] === "\t") col++;
  const content = line.slice(col);
  if (content.trim() === "" || isRule(line)) return null;
  return { ind: m[1], mk: m[2], content, col };
}

function isTableStart(lines: string[], i: number): boolean {
  const a = lines[i];
  const b = lines[i + 1];
  if (b === undefined || !a.trim().startsWith("|") || !b.includes("|") || !DELIM.test(b.trimEnd())) return false; // (L28) 머리 줄이 「|」 로 시작 · 구분 줄에 「|」 있을 때만 표(`ls -la | grep foo` 다음 `--- | ---` · `|x` 다음 `-` = 글)
  return cells(a).length === cells(b).length; // GFM: 머리 칸 수 = 구분 칸 수일 때만 표
}

function startsBlock(lines: string[], i: number): boolean {
  const l = lines[i];
  return fenceOpen(l) !== null || HEAD.test(l) || itemAt(l) !== null || isTableStart(lines, i);
}

/** 인라인 — 글 → 조각. depth = 겹침 깊이(3 을 넘으면 안쪽은 글 그대로 · 재귀 상한). */
export function parseInline(s: string, depth = 0): Inline[] {
  const out: Inline[] = [];
  let buf = "";
  const miss = new Set<string>(); // 닫는 짝을 못 찾은 표지 = 뒤에서도 못 찾음(닫는 조건이 여는 자리와 무관) → 다시 찾지 않음
  let closeBracket = -1; // 다음 「]」 자리(지나치면 다시 찾음 · 「[」 6만 개 병적 입력 선형)
  const flush = () => {
    if (buf) out.push({ k: "text", v: buf });
    buf = "";
  };
  const runLen = (at: number, ch: string): number => {
    let n = 0;
    while (s[at + n] === ch) n++;
    return n;
  };
  // (fix H3 · L4) 인라인 코드 칸을 먼저 한 번에 짝짓는다(CommonMark: 코드 칸이 강조보다 먼저) — 백틱 묶음마다 「같은 길이 다음 묶음」 을
  // 뒤에서부터 한 번 훑어 셈(선형) · codeAt[여는 자리] = 닫는 묶음 자리 + 1 · skip[칸 안 자리] = 칸 끝(강조 짝 찾기가 칸 안 별표를 안 봄).
  const codeAt = new Int32Array(s.length + 1);
  const skip = new Int32Array(s.length + 1);
  {
    const runs: number[] = [];
    for (let x = 0; x < s.length; ) {
      if (s[x] === "`") {
        runs.push(x);
        x += runLen(x, "`");
      } else x++;
    }
    const nextSame = new Int32Array(runs.length).fill(-1);
    const lastOf = new Map<number, number>();
    for (let r = runs.length - 1; r >= 0; r--) {
      const n = runLen(runs[r], "`");
      nextSame[r] = lastOf.get(n) ?? -1;
      lastOf.set(n, r);
    }
    for (let r = 0; r < runs.length; ) {
      const q = nextSame[r];
      if (q < 0) {
        r++;
        continue;
      }
      const a = runs[r];
      const end = runs[q] + runLen(runs[q], "`");
      codeAt[a] = runs[q] + 1;
      for (let x = a; x < end; x++) skip[x] = end;
      r = q + 1;
    }
  }
  /** 여는 강조 — 앞 = 줄 처음·빈칸·여는 문장 부호 · 뒤 = 빈칸·닫는 괄호 아님(낱말·경로·식 안 = 글 · H2·H3·M4). */
  const canOpen = (i: number, L: number): boolean => {
    const b = s[i - 1];
    const a = s[i + L];
    return (b === undefined || SPACE.test(b) || OPEN_P.includes(b)) && a !== undefined && !SPACE.test(a) && !CLOSE_BR.includes(a);
  };
  /** 닫는 강조 — 앞 = 빈칸·여는 문장 부호 아님 · 뒤 = (닫는 문장 부호 몇 개 다음) 줄 끝·빈칸 · 별표만 바로 뒤 한글(조사 「**굵게**는」) 허용. */
  const canClose = (j: number, L: number, ch: string): boolean => {
    const b = s[j - 1];
    if (b === undefined || SPACE.test(b) || OPEN_P.includes(b)) return false;
    let k = j + L;
    if (ch === "*" && k < s.length && HANGUL.test(s[k])) return true;
    while (k < s.length && CLOSE_P.includes(s[k])) k++;
    return k >= s.length || SPACE.test(s[k]);
  };
  // (fix2 N-A) 두 별표(`**…**`)만 너그럽게 — 마스터 답 굵게는 거의 늘 이 꼴(`**굵게**(설명)` · `**"확정"**` · `**가**·**나**` · `**요약**:내용`).
  // 여는 표지 = 뒤 빈칸 아님 ∧ 앞 ASCII 영숫자·별표·빗금 아님 / 닫는 표지 = 앞 빈칸 아님 ∧ 뒤 ASCII 영숫자·별표·빗금 아님 · 같은 줄 안 가장 가까운 짝 ·
  // 덧붙임(master 판정 밖 · 글롭 보호) = 여는 표지 바로 뒤·닫는 표지 바로 앞이 빗금(`/`·`\`)이면 표지 아님 — `src/**/*.ts`(L14) 는 글 · `**예**/**아니오**` 는 굵게.
  // 한 별표·밑줄은 위 엄한 규칙 그대로.
  const NEAR2 = /[A-Za-z0-9*]/;
  const SLASH = /[/\\]/;
  const canOpen2 = (i: number): boolean => {
    const b = s[i - 1];
    const a = s[i + 2];
    return a !== undefined && !SPACE.test(a) && !SLASH.test(a) && !(b !== undefined && NEAR2.test(b));
  };
  const canClose2 = (j: number, L: number): boolean => {
    const b = s[j - 1];
    const a = s[j + L];
    return b !== undefined && !SPACE.test(b) && !SLASH.test(b) && !(a !== undefined && NEAR2.test(a));
  };
  let miss2 = -1; // 두 별표 닫는 짝을 못 찾은 줄의 끝 자리(그 줄 안 뒤 여는 표지는 다시 찾지 않음 · 줄마다 한 번 = 선형)
  /** 닫는 강조 짝 — 정확히 len(1) 또는 len 이상(2·3) 인 같은 글자 묶음 · 코드 칸 안은 건너뜀 · upTo = 찾는 끝(두 별표 = 그 줄 끝). */
  const findEmph = (ch: string, len: 1 | 2 | 3, from: number, dbl = false, upTo = s.length): number => {
    let j = s.indexOf(ch, from);
    while (j >= 0 && j < upTo) {
      if (skip[j]) {
        j = s.indexOf(ch, skip[j]);
        continue;
      }
      const L = runLen(j, ch);
      const okLen = len === 1 ? L === 1 : L >= len;
      if (okLen && (dbl ? canClose2(j, L) : canClose(j, L, ch))) return j;
      j = s.indexOf(ch, j + L);
    }
    return -1;
  };
  let match: Int32Array | null = null; // 「(」 자리 → 짝 「)」 자리(-1 = 없음) · 처음 쓸 때 한 번 선형으로 셈
  const parenMatch = (q: number): number => {
    if (!match) {
      match = new Int32Array(s.length).fill(-1);
      const st: number[] = [];
      for (let x = 0; x < s.length; x++) {
        if (s[x] === "(") st.push(x);
        else if (s[x] === ")" && st.length) match[st.pop() as number] = x;
      }
    }
    return match[q];
  };
  let ws = -1; // from 이후 첫 빈칸 자리(캐시 · 묻는 자리는 앞으로만 감)
  let wsFrom = -1;
  const spaceAt = (from: number): number => {
    if (wsFrom < 0 || from < wsFrom || (ws >= 0 && ws < from)) {
      const re = /\s/g;
      re.lastIndex = from;
      const m = re.exec(s);
      ws = m ? m.index : s.length;
      wsFrom = from;
    }
    return ws;
  };
  let i = 0;
  while (i < s.length) {
    const ch = s[i];
    // (fix H1) 역빗금 = 벗김 글자 아님 — 글자 그대로(`C:\Users\user\.cys` · `\\server` · `\d+\.\d+` · `\*.log` 보존 · 뒤 글자도 보통 글자로 이어 읽음)
    if (ch === "`") {
      const n = runLen(i, "`");
      if (codeAt[i]) {
        const j = codeAt[i] - 1;
        flush();
        let v = s.slice(i + n, j);
        if (v.length >= 2 && v[0] === " " && v[v.length - 1] === " " && v.trim() !== "") v = v.slice(1, -1);
        out.push({ k: "code", n, v });
        i = j + n;
        continue;
      }
      buf += s.slice(i, i + n);
      i += n;
      continue;
    }
    if (ch === "!" && s[i + 1] === "[") {
      buf += "!["; // 그림 = 원문 글 그대로(그림 요소·불러오기 0)
      i += 2;
      continue;
    }
    if (ch === "[" && !miss.has("]") && !WORD.test(s[i - 1] ?? "")) { // (fix M4) 낱말 바로 뒤 「[」 = 코드 꼴(`handlers[name](event)`) → 글
      if (closeBracket <= i) closeBracket = s.indexOf("]", i + 1);
      const j = closeBracket;
      if (j < 0) miss.add("]");
      else if (s[j + 1] === "(" && !(s.indexOf("[", i + 1) > i && s.indexOf("[", i + 1) < j)) {
        const k = parenMatch(j + 1); // 주소 = 「(」 의 짝 「)」 까지(겹친 괄호 허용 · 짝 표 = 선형 · 「[a](」 반복 병적 입력) · 사이에 빈칸 없음
        if (k > j + 2 && spaceAt(j + 2) > k) {
          flush();
          const label = s.slice(i + 1, j);
          out.push({ k: "link", c: depth < 3 ? parseInline(label, depth + 1) : [{ k: "text", v: label }], url: s.slice(j + 2, k) });
          i = k + 1;
          continue;
        }
      }
      buf += "[";
      i += 1;
      continue;
    }
    if (ch === "*" || ch === "_") {
      const L = runLen(i, ch);
      const len: 1 | 2 | 3 = L >= 3 ? 3 : L >= 2 ? 2 : 1; // (L3) `***굵은 기울임***` = 굵게 안 기울임
      const key = ch + len;
      const dbl = ch === "*" && L === 2;
      const eol = dbl ? (s.indexOf("\n", i) < 0 ? s.length : s.indexOf("\n", i)) : s.length;
      if (depth < 3 && (dbl ? canOpen2(i) && i >= miss2 : canOpen(i, L) && !miss.has(key))) {
        const j = findEmph(ch, len, i + L, dbl, eol);
        const inner = j >= 0 ? s.slice(i + len, j) : "";
        const dunder = ch === "_" && IDENT.test(inner); // (fix H2) `__init__` · `__name__` · `_private_` = 이름 그대로(글)
        if (j >= 0 && j > i + len && !dunder) {
          flush();
          const m = ch.repeat(len);
          const c = parseInline(inner, depth + 1);
          out.push(len === 3 ? { k: "strong", m: ch.repeat(2), c: [{ k: "em", m: ch, c }] } : { k: len === 2 ? "strong" : "em", m, c });
          i = j + len;
          continue;
        }
        if (j < 0 && dbl) miss2 = eol;
        else if (j < 0) miss.add(key);
      }
      buf += s.slice(i, i + L);
      i += L;
      continue;
    }
    buf += ch;
    i += 1;
  }
  flush();
  return out;
}

/** 블록 — 글 → 나무(64KB 넘으면 앞쪽만 · 나머지 raw). */
export function parseMd(src: string): Block[] {
  let head = src;
  let tail = "";
  if (src.length > MD_MAX) {
    const cut = src.lastIndexOf("\n", MD_MAX - 1);
    head = cut >= 0 ? src.slice(0, cut + 1) : "";
    tail = src.slice(head.length);
  }
  const lines = head.split(LINE_END); // (fix B1) 모든 줄 끝 글자로 먼저 가름(맨 CR · U+2028 · U+2029 가 줄 안에 남지 않음)
  if (head.endsWith("\n")) lines.pop(); // 끝 줄바꿈 = 빈 줄 하나 덜 셈
  const out: Block[] = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (line.trim() === "") {
      i++;
      continue;
    }
    const f = fenceOpen(line);
    if (f) {
      const [next, pre] = readFence(lines, i + 1, f, false); // 닫는 줄 없으면 끝까지 = CommonMark · 몸 = 여는 줄 들여쓰기만큼 걷음(M2)
      out.push(pre);
      i = next;
      continue;
    }
    const h = HEAD.exec(line);
    if (h) {
      let t = line.slice(h[0].length).trim();
      let e = t.length;
      let end = "";
      while (e > 0 && t[e - 1] === "#") e--;
      if (e < t.length && (e === 0 || t[e - 1] === " " || t[e - 1] === "\t")) {
        end = t.slice(e);
        t = t.slice(0, e).trimEnd(); // 닫는 「###」 = 표지
      }
      out.push({ k: "h", level: h[1].length as 1 | 2 | 3, c: parseInline(t), end });
      i++;
      continue;
    }
    if (isTableStart(lines, i)) {
      const headCells = cells(line).map((c) => parseInline(c));
      const rows: Inline[][][] = [];
      i += 2;
      // (L27) 몸 줄 = 「|」 로 시작하거나 칸 수가 머리 이하일 때만(표 뒤에 붙은 `cmd1 || cmd2` = 글)
      while (i < lines.length && lines[i].trim() !== "" && lines[i].includes("|") && fenceOpen(lines[i]) === null && !HEAD.test(lines[i]) && (lines[i].trim().startsWith("|") || cells(lines[i]).length <= headCells.length)) rows.push(cells(lines[i++]).map((c) => parseInline(c)));
      out.push({ k: "table", head: headCells, rows });
      continue;
    }
    const m = itemAt(line);
    if (m) {
      const ordered = /\d/.test(m.mk);
      type Raw = { depth: 0 | 1; num: string | null; mark: string; t: string; more: Array<{ k: "pre"; v: string; f: string; info: string; end: string } | { k: "p"; t: string }> };
      const items: Raw[] = [];
      while (i < lines.length) {
        const im = itemAt(lines[i]);
        if (im) {
          const isNum = /\d/.test(im.mk);
          const depth: 0 | 1 = indentOf(im.ind) >= 2 ? 1 : 0;
          if (depth === 0 && isNum !== ordered) break; // 맨 앞 항목의 종류가 바뀌면 새 목록
          const it: Raw = { depth, num: isNum ? im.mk : null, mark: im.mk, t: "", more: [] };
          items.push(it);
          const ff = fenceOpen(im.content); // (fix M1) 항목 첫 줄이 울타리(`1. ```bash`) = 그 항목 안 울타리(들여쓰기 = 내용 자리)
          if (ff) {
            const [next, pre] = readFence(lines, i + 1, { ...ff, ind: im.col }, true);
            it.more.push(pre);
            i = next;
            continue;
          }
          it.t = im.content;
          i++;
          continue;
        }
        if (lines[i].trim() === "") {
          let j = i;
          while (j < lines.length && lines[j].trim() === "") j++;
          const nm = j < lines.length ? itemAt(lines[j]) : null;
          if (nm && (indentOf(nm.ind) >= 2 || /\d/.test(nm.mk) === ordered)) {
            i = j;
            continue;
          }
          if (j < lines.length && lead(lines[j]) >= 2 && fenceOpen(lines[j], Infinity)) { // 빈 줄 뒤 들여쓴 울타리 = 같은 항목
            i = j;
            continue;
          }
          break;
        }
        const cur = items[items.length - 1];
        const lf = lead(lines[i]) >= 1 ? fenceOpen(lines[i], Infinity) : null; // (fix H5 · M2) 들여쓴 울타리 = 항목 안 울타리(코드 들여쓰기 보존)
        if (lf) {
          const [next, pre] = readFence(lines, i + 1, lf, true);
          cur.more.push(pre);
          i = next;
          continue;
        }
        if (startsBlock(lines, i)) break;
        const lastMore = cur.more[cur.more.length - 1];
        if (lastMore && lastMore.k === "p") lastMore.t += `\n${lines[i].trim()}`;
        else if (lastMore) cur.more.push({ k: "p", t: lines[i].trim() }); // 울타리 뒤 이어진 글 = 그 항목 안 문단
        else items[items.length - 1].t += `\n${lines[i].trim()}`; // 이어진 줄 = 그 항목
        i++;
      }
      out.push({
        k: "list",
        ordered,
        items: items.map((it) => ({ depth: it.depth, num: it.num, mark: it.mark, c: parseInline(it.t), more: it.more.map((b) => (b.k === "p" ? { k: "p" as const, c: parseInline(b.t) } : b)) })),
      });
      continue;
    }
    const para: string[] = [line];
    i++;
    while (i < lines.length && lines[i].trim() !== "" && !startsBlock(lines, i)) para.push(lines[i++]);
    out.push({ k: "p", c: parseInline(para.join("\n")) });
  }
  if (tail) out.push({ k: "raw", v: tail });
  return out;
}
