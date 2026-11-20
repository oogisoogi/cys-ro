// 가로 막대 — 왼쪽 이름 · 막대(강조=연두 · 나머지=회색) · 오른쪽 고정폭 값. 단계마다 한 줄씩
// 이름 왼쪽 정렬 · 값은 강조 막대에만(참고 문법) — d.values: "all" 이거나 강조 막대가 하나도 없으면 모든 막대에 값
// data: { title, unit, items: [{ l, v, hl }], note, values }
TYPES.bars = (d, step) => {
  const max = Math.max(...d.items.map(x => x.v));
  const all = d.reveal === false;
  const showAll = d.values === "all" || !d.items.some(x => x.hl);  // 강조 막대가 없으면 값을 모두 보인다
  return `${d.title ? `<div class="title">${md(d.title)}</div>` : ""}
<div style="display:flex;flex-direction:column;gap:${d.items.length > 7 ? 10 : 22}px;flex:1;justify-content:center">
${d.items.map((x, i) => `<div class="${all ? "" : st(i, step)}" style="display:grid;grid-template-columns:420px 1fr 270px;gap:28px;align-items:center">
  <div style="font-size:40px;font-weight:700;text-align:left;color:${x.hl ? "var(--ink)" : "var(--ink-2)"};white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${md(x.l)}</div>
  <div style="height:${d.items.length > 7 ? 34 : 50}px;background:var(--ghost);border-radius:4px;overflow:hidden"><div style="height:100%;width:${(x.v / max * 100).toFixed(1)}%;background:${x.hl ? "var(--accent)" : "var(--mute)"};border-radius:4px"></div></div>
  <div class="mono" style="font-size:44px;font-weight:800;${x.hl ? "color:var(--accent)" : ""}">${x.hl || showAll ? `${fmt(x.v)}<span style="font-size:.66em">${esc(d.unit || "")}</span>` : ""}</div>
</div>`).join("")}
</div>${d.note ? `<div class="mono" style="font-size:26px;color:var(--mute);margin-top:18px">${md(d.note)}</div>` : ""}`;
};
