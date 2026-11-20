// 체크리스트(행동 목록) — 네모 칸 · 단계까지 체크(연두) · 안 온 줄 흐림
// data: { title, items: [..] }
TYPES.checklist = (d, step) => `
${d.title ? `<div class="title">${md(d.title)}</div>` : ""}
<div style="display:flex;flex-direction:column;gap:${d.items.length > 5 ? 20 : 30}px;flex:1;justify-content:center">
${d.items.map((t, i) => `<div class="${st(i, step)}" style="display:flex;align-items:center;gap:30px">
  <div style="width:52px;height:52px;flex:none;border-radius:8px;border:3px solid ${i <= step ? "var(--accent)" : "var(--mute)"};background:${i <= step ? "var(--accent)" : "transparent"};display:flex;align-items:center;justify-content:center;color:var(--card);font-size:40px;font-weight:900">${i <= step ? "✓" : ""}</div>
  <div class="mono" style="font-size:40px;color:var(--ink-2);width:44px">${i + 1}</div>
  <div style="font-size:var(--fs-item);font-weight:var(--fw-item)">${md(t)}</div>
</div>`).join("")}
</div>`;
