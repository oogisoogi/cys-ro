// 표지 — 왼쪽: 작은 머리말 · 큰 제목 2줄(둘째 줄 강조) · 날짜 · 부제 / 오른쪽: 고정폭 라벨 + 뼈대 막대(내용 예고)
// data: { kicker, line1, line2, date, sub, label, slots }
TYPES.cover = (d, step) => `
<div style="display:flex;height:100%;gap:80px">
  <div style="flex:1.3;border-left:8px solid var(--accent);padding-left:48px;display:flex;flex-direction:column;justify-content:center">
    <div class="kicker">${md(d.kicker)}</div>
    <div style="font-size:96px;font-weight:800;line-height:1.12;letter-spacing:-2px">${md(d.line1)}</div>
    <div class="acc" style="font-size:112px;font-weight:800;line-height:1.12;letter-spacing:-2px">${md(d.line2)}</div>
    <div class="mono" style="font-size:44px;color:var(--ink-2);margin-top:40px">${esc(d.date)}</div>
    <div style="font-size:40px;color:var(--mute);margin-top:14px">${md(d.sub)}</div>
  </div>
  <div style="flex:1;display:flex;flex-direction:column;justify-content:center;gap:26px">
    <div class="mono" style="font-size:34px;font-weight:700;letter-spacing:3px;color:var(--ink-2)">${esc(d.label || "REPORT")}</div>
    ${(d.slots || ["", "", "", ""]).map((s, i) => `<div class="${st(i, step)}" style="height:64px;border-left:5px solid var(--accent);background:var(--ghost);border-radius:4px;display:flex;align-items:center;padding-left:24px;font-size:34px;font-weight:700">${md(s)}</div>`).join("")}
  </div>
</div>`;
