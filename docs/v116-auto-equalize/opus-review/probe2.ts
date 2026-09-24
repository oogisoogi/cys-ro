import { autoArrange, formationLayout, type LayoutNode } from "../../../ui/src/formation";
const P = (sid: number): LayoutNode => ({ type: "pane", sid });
const S = (a: LayoutNode, b: LayoutNode, dir: "row"|"col"="row", ratio?: number): LayoutNode => ({ type: "split", dir, ratio, a, b } as any);
function rng(seed: number) { return () => { seed |= 0; seed = (seed + 0x6d2b79f5) | 0; let t = Math.imul(seed ^ (seed >>> 15), 1 | seed); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
const POOL = ["master","cso","worker",null,"master-2","cso-2"];
const r = rng(7); let diff = 0, n = 0, bad = 0;
function walk(t: LayoutNode|null){ if(!t||t.type==="pane") return; if(t.ratio!==undefined && !(t.ratio>0&&t.ratio<1)) bad++; walk(t.a); walk(t.b); }
for (let it = 0; it < 20000; it++) {
  const base = Array.from({length: Math.floor(r()*5)}, (_,i)=>100+i);
  const roles = new Map<number,string|null>();
  for (const s of [...base, 200,201,202,203]) roles.set(s, POOL[Math.floor(r()*POOL.length)]);
  // start tree = arranged formation (or null)
  let t0: LayoutNode|null = base.length ? autoArrange(null, roles, { add: base.map(sid=>({sid})) }) : null;
  if (t0 && t0.type==="split" && t0.dir==="row" && r()<0.5) t0 = { ...t0, ratio: (()=>{let v; do { v = 0.15 + r()*0.7 } while (Math.abs(v-1/3)<0.011||Math.abs(v-0.5)<0.011); return v;})() };
  const adds = [200,201,202,203].filter(()=>r()<0.6).map(sid=>({sid}));
  const batch = autoArrange(t0, roles, { add: adds });
  let seq = t0; for (const a of adds) seq = autoArrange(seq, roles, { add: [a] });
  n++; walk(batch); walk(seq);
  if (JSON.stringify(batch) !== JSON.stringify(seq)) { diff++; if (diff<4) console.log("DIFF", JSON.stringify([...roles]), JSON.stringify(t0), JSON.stringify(adds), "\n batch", JSON.stringify(batch), "\n seq  ", JSON.stringify(seq)); }
}
console.log("per-add vs batch diffs", diff, "/", n, "bad ratios", bad);
// F4 carry when removed master's role unknown (ghost eviction after fresh list)
const rolesNoOld = new Map<number,string|null>([[2,"cso"],[3,"worker"],[8,"master-2"]]);
const e0 = S(S(P(1),P(2),"col",0.6), S(P(3),P(8)), "row", 0.4);
console.log("F4 old master role gone:", JSON.stringify(autoArrange(e0, rolesNoOld, { remove: [1] })));
// drag on direct root at edge
const roles = new Map<number,string|null>([[1,"master"],[2,"cso"],[3,"worker"],[4,"worker"],[5,"worker"]]);
console.log("drag 0.85 kept:", (autoArrange(S(S(P(1),P(2),"col",0.8),S(P(3),P(4)),"row",0.85), roles, {add:[{sid:5}]}) as any).ratio);
