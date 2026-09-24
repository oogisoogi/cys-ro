import { autoArrange, formationLayout, leftColumnShare, type LayoutNode } from "/Users/oogisoogi/axdev/.wt/v116-auto-equalize/ui/src/formation";
const P = (sid: number): LayoutNode => ({ type: "pane", sid });
const S = (a: LayoutNode, b: LayoutNode, dir: "row"|"col"="row", ratio?: number): LayoutNode => ({ type: "split", dir, ratio, a, b } as any);
function shares(n: LayoutNode, w = 1, out = new Map<number, number>()) { if (n.type==="pane"){out.set(n.sid,w);return out;} const r=n.ratio??0.5; if(n.dir==="row"){shares(n.a,w*r,out);shares(n.b,w*(1-r),out);} else {shares(n.a,w,out);shares(n.b,w,out);} return out; }
const sids = (n: LayoutNode|null, o: number[] = []): number[] => { if(!n) return o; if(n.type==="pane") o.push(n.sid); else {sids(n.a,o);sids(n.b,o);} return o; };
const roles = new Map<number,string|null>([[1,"master"],[2,"cso"],[3,"worker"],[4,"worker"],[5,"worker"],[6,"worker"],[7,"worker"]]);
// (a) transferCrossDept: dest wraps 0.5 around arranged tree
let t = formationLayout([{sid:1,role:"master"},{sid:2,role:"cso"},{sid:3,role:"worker"},{sid:4,role:"worker"}])!;
console.log("a0 left", shares(t).get(1));
t = S(t, P(5), "row"); // transferCrossDept dest wrap (ratio undefined => 0.5)
console.log("a1 after transfer left", shares(t).get(1));
t = autoArrange(t, roles, { add: [{ sid: 6 }] })!;
console.log("a2 after next open left", shares(t).get(1), "rule", leftColumnShare(4));
t = autoArrange(t, roles, { remove: [6] })!;
console.log("a3 after close left", shares(t).get(1));
// (b) R1 old buggy tree: formation n=1 then old 0.5 adopt wrap
let b = formationLayout([{sid:1,role:"master"},{sid:2,role:"cso"},{sid:3,role:"worker"}])!;
b = S(b, P(4), "row");
console.log("b0 legacy left", shares(b).get(1));
b = autoArrange(b, roles, { add: [{ sid: 5 }] })!;
console.log("b1 after upgrade + open left", shares(b).get(1), "workers", [3,4,5].map(s=>shares(b).get(s)));
// (c) remove absent id triggers relayout of human layout
const h = S(S(P(1),P(2),"col",0.8), S(P(3),P(4),"col",0.5), "row", 1/3);
const hh = autoArrange(h, roles, { remove: [999] });
console.log("c no-op remove flattens human col:", JSON.stringify(hh));
// (d) degenerate/NaN ratios & duplicates fuzz
let bad = 0;
function chk(out: LayoutNode|null, tag: string) {
  const walk = (n: LayoutNode|null) => { if(!n||n.type==="pane") return; const r = n.ratio; if (r!==undefined && !(r>0 && r<1)) { bad++; if (bad<6) console.log("bad ratio", tag, r, JSON.stringify(out)); } walk(n.a); walk(n.b); };
  walk(out);
  const s = sids(out); if (new Set(s).size !== s.length) { bad++; if (bad<6) console.log("dup", tag, s); }
}
chk(autoArrange(S(S(P(1),P(2),"col",NaN),P(3),"row",0.4), roles, {add:[{sid:4}]}), "NaN col");
chk(autoArrange(S(S(P(1),P(2),"col",1),P(3),"row",0.4), roles, {add:[{sid:4}]}), "col=1");
chk(autoArrange(S(S(P(1),P(3),"row",0.5),S(P(1),P(2),"col",0.5),"row",0.4), roles, {add:[{sid:4}]}), "dup master");
chk(autoArrange(S(P(3),P(3)), roles, {}), "dup worker");
chk(autoArrange(S(S(P(1),P(2),"col",0.8),P(3),"row",0), roles, {add:[{sid:4}]}), "share0");
console.log("bad", bad);
// (e) master removed when master-2 exists in row: col ratio preserved?
const r2 = new Map<number,string|null>([[1,"master"],[2,"cso"],[3,"worker"],[8,"master-2"]]);
const e0 = S(S(P(1),P(2),"col",0.6), S(P(3),P(8)), "row", 0.4);
const e1 = autoArrange(e0, r2, { remove: [1] })!;
console.log("e master removed, master-2 promoted:", JSON.stringify(e1));
// (f) left column on the right side (human moved) -> share semantics
const f0 = S(S(P(3),P(4)), S(P(1),P(2),"col",0.8), "row", 0.7);
const f1 = autoArrange(f0, roles, { add: [{sid:5}] })!;
console.log("f left moved right: new left share", shares(f1).get(1), JSON.stringify(sids(f1)));
