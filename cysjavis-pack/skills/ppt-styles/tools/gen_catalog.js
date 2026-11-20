// 유지보수용(저장소에서만): styles/*.js → references/CATALOG.md + styles.json(pick.py 가 읽는다). 손으로 고치지 않는다.
// 머리말 = references/catalog.head.md · 사용: node tools/gen_catalog.js
const fs = require("fs"), path = require("path");
const deps = require("../lib/deps");
deps.setup();
const dir = path.join(deps.SKILL, "styles");
const files = fs.readdirSync(dir).filter(f => /^\d\d-.*\.js$/.test(f)).sort();
const styles = files.map(f => ({ f, ...require(path.join(dir, f)) }));
const head = fs.readFileSync(path.join(deps.SKILL, "references", "catalog.head.md"), "utf8");
let out = head + "\n## 한눈에 보기\n\n| 번호 | 스타일 | id | 분위기 묘사어 | 어울리는 용도 |\n|---|---|---|---|---|\n";
for (const s of styles) out += `| ${s.meta.no} | ${s.meta.name} | \`${s.meta.id}\` | ${s.meta.mood.join(" · ")} | ${s.meta.good[0]} |\n`;
for (const s of styles) { const m = s.meta;
  const input = { style: m.id, title: "(파일 속성 제목)" };
  for (const k of Object.keys(m.sample)) if (!["title", "cards", "question"].includes(k)) input[k] = m.sample[k];
  input.slides = [{ kind: "title", ...m.sample.title }, { kind: "cards", ...m.sample.cards }, { kind: "question", ...m.sample.question }];
  out += `\n---\n\n## ${m.no}. ${m.name}\n\n- id: \`${m.id}\` · 코드: \`styles/${s.f}\` · 테마 이름: \`${s.THEME.name}\`\n- 미리보기: \`bash run.sh samples ${m.id}\`(견본 3장 = 제목 · 카드 · 질문)\n\n`;
  out += `**분위기 묘사어** — ${m.mood.join(" · ")}\n\n**팔레트**\n\n| 이름 | hex |\n|---|---|\n` + m.palette.map(([n, h]) => `| ${n} | \`${h}\` |`).join("\n") + "\n\n";
  out += `**글꼴** — 제목: ${m.fonts.head} / 본문: ${m.fonts.body} / 라이선스: ${m.fonts.license}\n\n`;
  out += `**레이아웃 모티프**\n\n` + m.motifs.map(x => `- ${x}`).join("\n") + "\n\n";
  out += `**어울리는 용도** — ${m.good.join(" / ")}\n\n**피할 용도** — ${m.avoid.join(" / ")}\n\n**색·구성의 출처** — ${m.origin}\n\n`;
  out += `**입력 칸(make_deck.js 내용 JSON 예 = 견본 글)**\n\n\`\`\`json\n${JSON.stringify(input, null, 1)}\n\`\`\`\n`; }
fs.writeFileSync(path.join(deps.SKILL, "references", "CATALOG.md"), out);
fs.writeFileSync(path.join(deps.SKILL, "styles.json"), JSON.stringify(styles.map(s => ({ ...s.meta, sample: undefined, file: "styles/" + s.f, theme: s.THEME })), null, 1) + "\n");
console.log("CATALOG.md", out.length, "chars ·", styles.length, "styles");
