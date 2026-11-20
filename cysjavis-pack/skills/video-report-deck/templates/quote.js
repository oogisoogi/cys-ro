// 인용 — 큰 따옴표(강조) · 인용문 큰 글씨(뒷줄은 단계마다 켜짐) · 위에 출처 꼬리표
// data: { tag, tag_acc, lines: [..] }
TYPES.quote = (d, step) => `
<div style="display:flex;flex-direction:column;justify-content:center;height:100%;border:1.5px solid var(--line-2);border-radius:10px;padding:56px 64px">
  <div style="font-size:32px;color:var(--ink-2);margin-bottom:28px">${md(d.tag)} <span class="acc" style="margin-left:40px;font-weight:700">${md(d.tag_acc)}</span></div>
  <div style="display:flex;gap:28px"><div class="acc" style="font-size:150px;font-weight:900;line-height:.8">“</div>
  <div>${(d.lines || []).map((l, i) => `<div class="${st(i, step)}" style="font-size:66px;font-weight:800;line-height:1.3">${md(l)}</div>`).join("")}</div></div>
</div>`;
