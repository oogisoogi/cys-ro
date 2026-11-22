// 의존 패키지(pptxgenjs · react · react-dom · react-icons · sharp)를 찾는다.
// 팩 폴더 안에는 node_modules 를 두지 않는다 — 사용자 기기의 의존 폴더(PPT_STYLES_DEPS, 기본 ~/.cys/deps/ppt-styles)에 한 번 설치한다.
const path = require("path"), os = require("os"), Module = require("module");
const SKILL = path.resolve(__dirname, "..");
const NEED = ["pptxgenjs", "jszip", "react", "react-dom", "react-icons", "sharp"];
function depsDir() { return process.env.PPT_STYLES_DEPS || path.join(os.homedir(), ".cys", "deps", "ppt-styles"); }
function setup() {
  const nm = path.join(depsDir(), "node_modules");
  const cur = (process.env.NODE_PATH || "").split(path.delimiter).filter(Boolean);
  if (!cur.includes(nm)) { process.env.NODE_PATH = [nm, ...cur].join(path.delimiter); Module._initPaths(); }
  const missing = NEED.filter(n => { try { require.resolve(n); return false; } catch { return true; } });
  if (missing.length) {
    console.error(`[ppt-styles] node 패키지가 없습니다: ${missing.join(", ")} (찾은 곳: ${nm})`);
    console.error(`  설치(한 번만): bash "${path.join(SKILL, "run.sh")}" setup 을 실행하고 안내대로 npm ci 를 돌리세요.`);
    console.error(`  bash 가 없으면(윈도): "${depsDir()}" 폴더를 만들고 "${SKILL}" 의 package.json · package-lock.json 을 복사한 뒤 그 폴더에서 npm ci`);
    process.exit(3);
  }
}
module.exports = { SKILL, depsDir, setup };
