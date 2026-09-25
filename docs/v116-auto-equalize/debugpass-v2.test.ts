// 디버깅 정밀 패스(TICKET=v116-equalize-v2) — 열기·닫기·세로 분할·사람 끌기 연쇄를 무작위로 굴리며 매 걸음 불변식 검사.
import { it, expect } from "bun:test";
import { autoArrange, formationLayout, LEFT_SHARE_DEFAULT, type LayoutNode } from "./formation";
const leftColumnShare = (_n: number) => LEFT_SHARE_DEFAULT;
type N = LayoutNode;
const sids = (n: N | null, o: number[] = []): number[] => { if (!n) return o; if (n.type === "pane") o.push(n.sid); else { sids(n.a, o); sids(n.b, o); } return o; };
const units = (n: N | null, o: N[] = []): N[] => { if (!n) return o; if (n.type === "split" && n.dir === "row") { units(n.a, o); units(n.b, o); } else o.push(n); return o; };
const widths = (n: N | null, w = 1, o: number[] = []): number[] => { if (!n) return o; if (n.type === "split" && n.dir === "row") { const r = n.ratio ?? 0.5; widths(n.a, w * r, o); widths(n.b, w * (1 - r), o); } else o.push(w); return o; };
const has = (n: N | null, t: N): boolean => !!n && (n === t || (n.type === "split" && (has(n.a, t) || has(n.b, t))));
const ratiosOk = (n: N): boolean => n.type === "pane" || ((n.ratio === undefined || (Number.isFinite(n.ratio) && n.ratio > 0 && n.ratio < 1)) && ratiosOk(n.a) && ratiosOk(n.b));
function rng(seed: number) { return () => { seed |= 0; seed = (seed + 0x6d2b79f5) | 0; let t = Math.imul(seed ^ (seed >>> 15), 1 | seed); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
// 사람 끌기 흉내: 임의 split 하나의 비율을 0.15~0.85 로
function drag(n: N, r: () => number, depth = 0): N { if (n.type === "pane") return n; const k = r(); if (k < 0.3) { const m: any = { ...n, ratio: 0.15 + r() * 0.7 }; delete m.leftAuto; return m; } return k < 0.65 ? { ...n, a: drag(n.a, r, depth + 1) } : { ...n, b: drag(n.b, r, depth + 1) }; }
it("연쇄 20,000걸음 × 시드 40 — 좌석 보존 · 비율 (0,1) · 맞춘 모양이면 워커 기둥 균등 · 손 안 댄 사람 기둥 같은 객체 · 좌열 서브트리 보존 · 멱등", () => {
  let resizes = 0, humanKept = 0, defaultKept = 0; let steps = 0, fitted = 0, unfit = 0, colOps = 0, drags = 0, closesInPillar = 0, maxSeats = 0; const seatHist = new Map<number, number>();
  for (let seed = 1; seed <= 40; seed++) {
    const r = rng(seed * 7919);
    const hq = r() < 0.75;
    const roles = new Map<number, string | null>();
    let next = 10;
    let t: N | null = null;
    if (hq) { roles.set(1, "master"); roles.set(2, "cso"); t = autoArrange(null, roles, { add: [{ sid: 1 }, { sid: 2 }] }); }
    for (let k = 0; k < 500; k++) {
      const cur = sids(t);
      const op = r();
      const before = t;
      const D = [0.25, 0.3, 0.41, 0.5][Math.floor(r() * 4)]; // 창 크기(기본 폭)
      if (op > 0.9 && t && t.type === "split" && (t as any).leftAuto) { const o2 = autoArrange(t, roles, {}, "auto", D)!; expect(new Set(sids(o2))).toEqual(new Set(sids(t))); if (units(o2)[0] && sids(units(o2)[0]).every((x) => /^(master|cso)/.test(roles.get(x) ?? ""))) expect(widths(o2)[0]).toBeCloseTo(D, 12); t = o2; resizes++; continue; }
      let change: any = {};
      if (op < 0.35 || cur.length === 0) { const sid = next++; roles.set(sid, r() < 0.9 ? "worker" : null); const after = cur.length && r() < 0.6 ? cur[Math.floor(r() * cur.length)] : undefined; const dir = r() < 0.4 ? "col" : undefined; if (dir) colOps++; change = { add: [{ sid, after, dir }] }; }
      else if (op < 0.65) { const w = cur.filter((s) => !(roles.get(s) ?? "").match(/^(master|cso)/)); if (!w.length) continue; const sid = w[Math.floor(r() * w.length)]; change = { remove: [sid] }; if (t && units(t).some((u) => u.type === "split" && sids(u).includes(sid))) closesInPillar++; }
      else if (op < 0.8 && t) { t = drag(t, r); drags++; continue; }
      else if (op < 0.85 && hq && t && !cur.includes(1)) { roles.set(1, "master"); change = { add: [{ sid: 1 }] }; }
      else if (op < 0.88 && hq && cur.includes(2)) { change = { remove: [2] }; }
      else if (op < 0.9 && hq && t && !cur.includes(2)) { change = { add: [{ sid: 2 }] }; }
      else continue;
      const out = autoArrange(before, roles, change, "auto", D);
      steps++;
      const want = new Set([...(before ? sids(before) : []).filter((s) => !(change.remove ?? []).includes(s)), ...(change.add ?? []).map((a: any) => a.sid)]);
      expect(new Set(sids(out))).toEqual(want);
      expect(sids(out).length).toBe(want.size);
      maxSeats = Math.max(maxSeats, want.size); seatHist.set(want.size, (seatHist.get(want.size) ?? 0) + 1);
      if (out) {
        expect(ratiosOk(out)).toBe(true);
        expect(widths(out).reduce((a, b) => a + b, 0)).toBeCloseTo(1, 9);
        expect(autoArrange(out, roles, {}, "auto", D)).toEqual(out); // 멱등(같은 창 크기)
        const L = [sids(out).find((s) => /^master/.test(roles.get(s) ?? "")), sids(out).find((s) => /^cso/.test(roles.get(s) ?? ""))].filter((x) => x !== undefined) as number[];
        const ou = units(out);
        const fit = ou.every((u) => { const us = sids(u); return !us.some((x) => L.includes(x)) || us.every((x) => L.includes(x)); });
        // 좌열 폭: 사람 값(표지 없음 · 루트 왼쪽 직계 · 끌기 범위 · 옛 기본값 아님)은 그대로 · 표지 있으면 이번 기본 폭 D
        const isL = (x: number) => L.includes(x);
        const lu = (n: N | null) => n && n.type === "split" && n.dir === "row" && sids(n.a).length > 0 && sids(n.a).every(isL) ? n : null;
        const bl = lu(before), ol = lu(out);
        if (fit && bl && ol && sids(before!).some((x) => !isL(x)) && sids(out).some((x) => !isL(x))) {
          const bs = (bl as any).ratio ?? 0.5;
          const bothSameLeft = JSON.stringify(sids((bl as any).a).sort()) === JSON.stringify(sids((ol as any).a).sort());
          if ((bl as any).leftAuto) { expect((ol as any).ratio).toBeCloseTo(D, 12); defaultKept++; }
          else if (bothSameLeft && bs >= 0.15 && bs <= 0.85) { expect((ol as any).ratio).toBe(bs); humanKept++; } // (Fable 2R ②) 옛 기본 이동은 복원 때 한 번 — 이 판의 1/2·1/3 도 사람 값
        }
        if (fit) { fitted++; const w = widths(out).filter((_, i) => !sids(ou[i]).some((x) => L.includes(x))); for (const x of w) expect(x).toBeCloseTo(w[0], 9); } else unfit++;
        // 손 안 댄 입력 워커 기둥(닫힘·after 없음)은 같은 객체
        if (before) for (const u of units(before)) { const us = sids(u); if (us.some((x) => L.includes(x) || (change.remove ?? []).includes(x) || (change.add ?? []).some((a: any) => a.after === x))) continue; expect(has(out, u)).toBe(true); }
        // 좌열 구성이 그대로면 좌열 서브트리 같은 객체(4:1 포함)
        if (before && L.length === 2) { const lu = units(before).find((u) => { const us = sids(u); return us.length === 2 && L.every((x) => us.includes(x)); }); if (lu) expect(has(out, lu)).toBe(true); }
      }
      t = out;
    }
  }
  console.log(JSON.stringify({ resizes, humanKept, defaultKept, steps, fitted, unfit, colOps, drags, closesInPillar, maxSeats, seats: [...seatHist.entries()].sort((a, b) => a[0] - b[0]).slice(0, 8) }));
});
it("좌석 0·1·2·5 경계 · 사람 끌기 뒤 열기 · formation 직후", () => {
  const R = new Map<number, string | null>([[1, "master"], [2, "cso"], [3, "worker"], [4, "worker"], [5, "worker"], [6, "worker"], [7, "worker"]]);
  expect(autoArrange(null, R, {})).toBeNull();
  expect(autoArrange({ type: "pane", sid: 3 }, R, { remove: [3] })).toBeNull();
  expect(autoArrange(null, R, { add: [{ sid: 3 }] })).toEqual({ type: "pane", sid: 3 });
  expect(autoArrange({ type: "pane", sid: 3 }, R, { add: [{ sid: 4, after: 3, dir: "col" }] })).toEqual({ type: "split", dir: "col", ratio: 0.5, a: { type: "pane", sid: 3 }, b: { type: "pane", sid: 4 } });
  const f = formationLayout([1, 2, 3, 4, 5].map((sid) => ({ sid, role: R.get(sid) })))!;
  expect(autoArrange(f, R, {})).toEqual(f); // formation 직후 = 무변경
  // 사람이 워커 기둥 경계를 끈 뒤 열기 → 워커 폭만 다시 균등 · 좌열 1/3 유지
  const dragged: N = { ...(f as any), b: { ...(f as any).b, ratio: 0.7 } };
  const o = autoArrange(dragged, R, { add: [{ sid: 6 }] })!;
  const w = widths(o); expect(w[0]).toBeCloseTo(LEFT_SHARE_DEFAULT, 9); for (const x of w.slice(1)) expect(x).toBeCloseTo(w[1], 9);
  // 사람이 좌열 폭을 0.45 로 끈 뒤 열기 → 0.45 유지
  const d2: any = { ...(f as any), ratio: 0.45 }; delete d2.leftAuto; // 실제 끌기(main.ts attachDividerDrag)도 표지를 지운다
  expect(widths(autoArrange(d2, R, { add: [{ sid: 7 }] })!)[0]).toBeCloseTo(0.45, 9);
});
