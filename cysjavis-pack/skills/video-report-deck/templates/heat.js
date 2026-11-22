// 요일×시간 히트맵 — 진할수록 연두. 행 이름 · 3시간 눈금
// data: { title, grid: [7][24], rows: "월화수목금토일" }
TYPES.heat = (d, step) => {
  const max = Math.max(...d.grid.flat());
  const rows = d.rows || "월화수목금토일";
  let h = `${d.title ? `<div class="title" style="margin-bottom:24px">${md(d.title)}</div>` : ""}
<div style="flex:1;display:grid;grid-template-columns:70px repeat(24,1fr);grid-template-rows:40px repeat(${d.grid.length},1fr);gap:6px">
<div></div>${[...Array(24).keys()].map(i => `<div class="mono" style="font-size:26px;color:var(--ink-2);text-align:center">${i % 3 === 0 ? i : ""}</div>`).join("")}`;
  d.grid.forEach((row, w) => {
    h += `<div style="font-size:34px;font-weight:700;align-self:center;color:var(--ink-2)">${rows[w]}</div>`;
    row.forEach(v => { const a = v / max; h += `<div style="border-radius:4px;background:${a > .02 ? `rgba(209,244,38,${(0.08 + a * 0.92).toFixed(2)})` : "var(--ghost)"}"></div>`; });
  });
  return h + `</div>`;
};
