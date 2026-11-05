// 표 — 머리 줄(작은 회색) · 숫자 칸은 고정폭 오른쪽 정렬 · hl 줄 강조 · 단계마다 한 줄씩(reveal:false 면 한꺼번에)
// data: { title, head: [..], rows: [{ c: [..], hl }], num: [칸 번호..] }
TYPES.table = (d, step) => {
  const num = new Set(d.num || []);
  const all = d.reveal === false;
  return `${d.title ? `<div class="title">${md(d.title)}</div>` : ""}
<table style="width:100%;border-collapse:collapse;font-size:${d.rows.length > 6 ? 36 : 40}px">
<tr>${d.head.map((h, i) => `<th style="text-align:${num.has(i) ? "right" : "left"};font:600 28px var(--mono);color:var(--ink-2);padding:0 18px 16px;border-bottom:1.5px solid var(--line-2)">${esc(h)}</th>`).join("")}</tr>
${d.rows.map((r, j) => `<tr class="${all ? "" : st(j, step)}">${r.c.map((x, i) => `<td class="${num.has(i) ? "mono" : ""}" style="padding:${d.rows.length > 6 ? 13 : 18}px 18px;border-bottom:1.5px solid var(--line);text-align:${num.has(i) ? "right" : "left"};font-weight:${i === 0 || r.hl ? 700 : 500};${r.hl ? "color:var(--accent)" : ""}">${fmt(x)}</td>`).join("")}</tr>`).join("")}
</table>`;
};
