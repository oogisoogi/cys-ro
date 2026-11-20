// 세로 막대(시간대 등) — 한두 계열 · 강조 구간(hl 인덱스) · 범례 · 아래 눈금
// data: { title, s1, s2, legend:[a,b], hl:[i..], xlabel(i)=>"" 대신 xstep(눈금 간격), xunit }
TYPES.columns = (d, step) => {
  const tot = d.s1.map((v, i) => v + (d.s2 ? d.s2[i] : 0));
  const max = Math.max(...tot);
  const hl = new Set(d.hl || []);
  const xs = d.xstep || 3;
  return `${d.title ? `<div class="title" style="margin-bottom:20px">${md(d.title)}</div>` : ""}
${d.legend ? `<div style="display:flex;gap:44px;font-size:32px;color:var(--ink-2);margin-bottom:22px">${d.legend.map((l, i) => `<span><i style="display:inline-block;width:28px;height:28px;border-radius:5px;margin-right:12px;vertical-align:-3px;background:${i ? "var(--mute)" : "var(--accent)"}"></i>${md(l)}</span>`).join("")}</div>` : ""}
<div style="flex:1;display:flex;align-items:flex-end;gap:10px;border-bottom:2px solid var(--line-2)">
${d.s1.map((v, i) => `<div style="flex:1;height:100%;display:flex;flex-direction:column-reverse;gap:3px">
  <div style="height:${(v / max * 100).toFixed(1)}%;background:var(--accent);opacity:${hl.size && !hl.has(i) ? .45 : 1};border-radius:3px 3px 0 0"></div>
  ${d.s2 ? `<div style="height:${(d.s2[i] / max * 100).toFixed(1)}%;background:var(--mute);border-radius:3px 3px 0 0"></div>` : ""}
</div>`).join("")}
</div>
<div class="mono" style="display:flex;gap:10px;font-size:28px;color:var(--ink-2);margin-top:12px">${d.s1.map((_, i) => `<div style="flex:1;text-align:center">${i % xs === 0 ? i + (d.xunit || "") : ""}</div>`).join("")}</div>`;
};
