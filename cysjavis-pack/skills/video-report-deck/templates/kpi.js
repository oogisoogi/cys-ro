// 숫자 카드 — 큰 고정폭 숫자(강조) + 설명. 1~4장. 단계마다 한 장씩
// data: { title, items: [{ v, unit, l }] }
TYPES.kpi = (d, step) => `
${d.title ? `<div class="title">${md(d.title)}</div>` : ""}
<div style="display:grid;grid-template-columns:repeat(${d.items.length},1fr);gap:40px;flex:1;align-items:center">
${d.items.map((x, i) => `<div class="${st(i, step)}" style="border:1.5px solid var(--line-2);border-radius:10px;padding:48px 44px;background:rgba(255,255,255,.02)">
  <div class="mono acc" style="font-size:${d.items.length > 2 ? 104 : 132}px;font-weight:800;line-height:1;letter-spacing:-3px">${fmt(x.v)}<span style="font-size:.42em;margin-left:8px">${esc(x.unit || "")}</span></div>
  <div style="font-size:38px;color:var(--ink-2);margin-top:30px;line-height:1.35">${md(x.l)}</div>
</div>`).join("")}
</div>`;
