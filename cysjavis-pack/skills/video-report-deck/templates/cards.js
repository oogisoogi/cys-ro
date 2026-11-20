// 카드 N장 — 고정폭 번호(강조) · 카드 제목 · 본문 · 아래 고정폭 꼬리값. 단계마다 한 장씩 아래에서 올라온다
// data: { title, items: [{ title, body, foot }] }
TYPES.cards = (d, step) => `
${d.title ? `<div class="title">${md(d.title)}</div>` : ""}
<div style="display:grid;grid-template-columns:repeat(${d.items.length},1fr);gap:36px;flex:1">
${d.items.map((x, i) => `<div class="${st(i, step)}" style="border:1.5px solid var(--line-2);border-radius:12px;padding:40px 40px 34px;background:rgba(255,255,255,.025);display:flex;flex-direction:column">
  <div class="mono acc" style="font-size:40px;font-weight:800">${String(i + 1).padStart(2, "0")}</div>
  <div style="font-size:48px;font-weight:800;margin:14px 0 18px;line-height:1.2">${md(x.title)}</div>
  <div style="font-size:36px;color:var(--ink-2);line-height:1.4;flex:1">${md(x.body)}</div>
  ${x.foot ? `<div class="mono" style="font-size:40px;font-weight:700;color:var(--ink-2);margin-top:18px">${md(x.foot)}</div>` : ""}
</div>`).join("")}
</div>`;
