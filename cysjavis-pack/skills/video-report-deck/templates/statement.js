// 한 문장 장면 — 큰 글씨 2~3줄(강조는 *…*) + 작은 머리말 + 아래 보조 줄
// data: { kicker, lines: [..], note }
TYPES.statement = (d, step) => `
<div style="display:flex;flex-direction:column;justify-content:center;height:100%">
  <div class="kicker">${md(d.kicker)}</div>
  ${(d.lines || []).map((l, i) => `<div class="${st(i, step)}" style="font-size:${d.size || 104}px;font-weight:800;line-height:1.18;letter-spacing:-2px">${md(l)}</div>`).join("")}
  ${d.note ? `<div style="font-size:40px;color:var(--ink-2);margin-top:44px">${md(d.note)}</div>` : ""}
</div>`;
