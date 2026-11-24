// (TICKET=cysr-1119-s11 · DESIGN TC3) 대화 입력칸 끌어 놓기의 순수 판정 — 칩 목록 · 보낼 때 펼친 글.
//
// 파일은 올리지 않는다(업로드 0) — 보내는 글 끝에 경로를 붙일 뿐이다. 경로 꼴 = 작업 화면 끌어 놓기와 같은 함수(ftdrop.insertionText)의
// 에이전트 갈래(`@경로` · 공백 있는 경로 = 셸 인용)이고, 마스터 좌석 cwd 를 이 화면이 들고 있지 않으므로 상대화하지 않는다(절대 경로).

import { baseName, insertionText } from "../../ftdrop";

/** 칩 목록에 새로 놓은 경로를 더한다 — 같은 경로는 한 번만(처음 놓은 순서) · 빈 경로 버림 · 새 배열. */
export function addDropped(files: readonly string[], paths: readonly string[]): string[] {
  const out = [...files];
  for (const p of paths) if (p && !out.includes(p)) out.push(p);
  return out;
}

/** 칩에 보이는 이름 = 파일 이름(맥 / · 윈 \). */
export function chipName(path: string): string {
  return baseName(path);
}

/** 보내는 글 = 입력칸 글(칩이 있으면 끝 공백을 걷고) + 공백 1 + 칩 경로들. 칩이 없으면 입력칸 글 그대로(바이트 같음). */
export function withDroppedFiles(text: string, files: readonly string[], isWin: boolean): string {
  if (files.length === 0) return text;
  const mentions = insertionText([...files], { agent: true, isWin, cwd: null }).trimEnd();
  const base = text.replace(/\s+$/, "");
  return base.trim() === "" ? mentions : `${base} ${mentions}`;
}
