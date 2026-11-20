// 핵심 N개 — 01·02… 고정폭 번호 + 두 줄 큰 글씨(main · sub). 지금 켜지는 줄은 왼쪽 연두 세로줄.
// 지난 줄 밝음 · 안 온 줄 흐림. 다섯 줄 이상이면 글자를 한 단계 줄인다.
// data: { kicker, title, items: [{ main, sub }] }
TYPES.numbered = (d, step) => {
  const dense = d.items.length > 4;
  const cur = Math.min(step, d.items.length - 1);
  return `
${d.kicker ? `<div class="kicker">${md(d.kicker)}</div>` : ""}
${d.title ? `<div class="title" style="margin-bottom:${dense ? 22 : 36}px">${md(d.title)}</div>` : ""}
<div style="display:flex;flex-direction:column;flex:1;justify-content:center">
${d.items.map((it, i) => `<div class="${st(i, step)}" style="display:grid;grid-template-columns:${dense ? 104 : 124}px 1fr;align-items:center;border-bottom:1.5px solid var(--line);padding:${dense ? 10 : 16}px 0 ${dense ? 10 : 16}px 22px;border-left:8px solid ${i === cur ? "var(--accent)" : "transparent"}">
  <div class="mono acc" style="font-size:${dense ? 60 : 72}px;font-weight:800;line-height:1">${String(i + 1).padStart(2, "0")}</div>
  <div style="line-height:1.22"><div style="font-size:${dense ? 46 : 52}px;font-weight:800">${md(it.main ?? it)}</div>
  ${it.sub ? `<div style="font-size:${dense ? 40 : 46}px;font-weight:700;color:var(--ink-2)">${md(it.sub)}</div>` : ""}</div>
</div>`).join("")}
</div>`;
};
