// 도넛 — 전체 중 일부(가운데 고정폭 숫자 · 오른쪽 문장)
// data: { value, total, center_sub, lines: [..] }
TYPES.ring = (d, step) => {
  const r = 210, c = 2 * Math.PI * r, p = d.value / d.total;
  return `<div style="display:flex;align-items:center;gap:110px;height:100%">
<svg width="560" height="560" viewBox="0 0 560 560"><circle cx="280" cy="280" r="${r}" fill="none" stroke="var(--ghost)" stroke-width="56"/>
<circle cx="280" cy="280" r="${r}" fill="none" stroke="var(--accent)" stroke-width="56" stroke-dasharray="${(c * p).toFixed(1)} ${c.toFixed(1)}" transform="rotate(-90 280 280)"/>
<text x="280" y="285" text-anchor="middle" font-family="JetBrains Mono" font-weight="800" font-size="120" fill="var(--ink)">${esc(d.center ?? d.value)}</text>
<text x="280" y="365" text-anchor="middle" font-family="JetBrains Mono" font-size="44" fill="var(--ink-2)">${esc(d.center_sub ?? "/ " + d.total)}</text></svg>
<div style="flex:1">${(d.lines || []).map((l, i) => `<div class="${st(i, step)}" style="font-size:${i ? 72 : 52}px;font-weight:800;line-height:1.25;margin-bottom:18px">${md(l)}</div>`).join("")}</div></div>`;
};
