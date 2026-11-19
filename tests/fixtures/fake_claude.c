// tests/update_drainhold_e2e.rs 의 좌석 대역: 이름이 claude 인 실행 파일(OS env 관측 · 자손 argv 일치를 받기 위해 스크립트가 아니다).
// --resume/--continue 를 따르고 · SessionStart 등록(cys usage-register · 훅 이름 session-start.sh 셸 아래)을 --resume 일 때 FAKE_BOOT 초 뒤에 · set-status waiting · [DRAIN-VERIFY] 체크포인트 저장.
// FAKE_NEW_SID = 재개해도 새 세션 id 로 등록(세션이 채워졌는데 다른 경우).
// FAKE_NO_REG = 등록·대화 파일 0(훅 부재 좌석 · seatkeep-t1 r5 codex r4 #1 재현).
// FAKE_HELPER_GATE = 그 파일이 생기면 자식이 이 실행 파일을 `claude -p` 헬퍼로 다시 띄운다(FAKE_HELPER=1 · 새 대화 id 로 훅 이름 셸에서 등록하고 끝남 ·
//   좌석 안 헬퍼 등록 · skt1 독립 검증 V1 = 계통 거름의 행동 시험).
// FAKE_REG_GATE = 화면은 띄우고 등록만 그 파일이 생길 때까지(최대 120초) 자식 셸(이름 session-start.sh)에서 미룬다(정상 기동 직후 SessionStart 등록 전 창 · seatkeep-t1 r5b).
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <termios.h>
static void slug(const char *c, char *o) { for (; *c; c++, o++) *o = ((*c >= 'a' && *c <= 'z') || (*c >= 'A' && *c <= 'Z') || (*c >= '0' && *c <= '9')) ? *c : '-'; *o = 0; }
int main(int ac, char **av) {
  char sid[128] = "", cwd[900], sl[900], pd[2000], cmd[4000], tp[2200];
  int cont = 0;
  int helper = getenv("FAKE_HELPER") != NULL;
  for (int i = 1; i < ac; i++) { if (!strcmp(av[i], "--resume") && i + 1 < ac) snprintf(sid, sizeof sid, "%s", av[i + 1]); if (!strcmp(av[i], "--continue")) cont = 1; }
  getcwd(cwd, sizeof cwd); slug(cwd, sl);
  const char *cd = getenv("CLAUDE_CONFIG_DIR");
  if (cd && *cd) snprintf(pd, sizeof pd, "%s/projects/%s", cd, sl); else snprintf(pd, sizeof pd, "%s/.claude/projects/%s", getenv("HOME"), sl);
  snprintf(cmd, sizeof cmd, "mkdir -p '%s'", pd); system(cmd);
  if (!sid[0] && cont) { snprintf(cmd, sizeof cmd, "ls -t '%s' 2>/dev/null | grep jsonl | head -1 | sed 's/.jsonl//'", pd); FILE *f = popen(cmd, "r"); if (f) { if (fgets(sid, sizeof sid, f)) sid[strcspn(sid, "\n")] = 0; pclose(f); } }
  if (!sid[0]) { FILE *f = popen("/usr/bin/uuidgen | tr A-Z a-z", "r"); fgets(sid, sizeof sid, f); sid[strcspn(sid, "\n")] = 0; pclose(f); }
  snprintf(tp, sizeof tp, "%s/%s.jsonl", pd, sid);
  int noreg = getenv("FAKE_NO_REG") != NULL;
  FILE *t = noreg ? NULL : fopen(tp, "a"); if (t) { fprintf(t, "{\"type\":\"user\",\"sessionId\":\"%s\",\"cwd\":\"%s\"}\n", sid, cwd); fclose(t); }
  char lg[1200]; snprintf(lg, sizeof lg, "%s/fake.log", getenv("HOME")); FILE *l = fopen(lg, "a"); if (l) { fprintf(l, "sid=%s surface=%s role=%s argv:", sid, getenv("CYS_SURFACE_ID") ?: "", getenv("CYS_ROLE") ?: ""); for (int i = 1; i < ac; i++) fprintf(l, " %s", av[i]); fprintf(l, "\n"); fclose(l); }
  for (int i = 1; i < ac; i++) if (getenv("FAKE_NEW_SID") && !strcmp(av[i], "--resume")) { FILE *f = popen("/usr/bin/uuidgen | tr A-Z a-z", "r"); fgets(sid, sizeof sid, f); sid[strcspn(sid, "\n")] = 0; pclose(f); snprintf(tp, sizeof tp, "%s/%s.jsonl", pd, sid); FILE *n = fopen(tp, "a"); if (n) fclose(n); }
  const char *bt = getenv("FAKE_BOOT"); for (int i = 1; i < ac; i++) if (bt && !strcmp(av[i], "--resume")) usleep((useconds_t)(atof(bt) * 1000000));
  // FAKE_CYS = 시험이 지은 cys 절대 경로(좌석 로그인 셸의 PATH 재정렬이 맨 `cys` 를 설치본으로 풀지 않게 · skt1) · 없으면 종전 `cys`.
  const char *cy = getenv("FAKE_CYS"); if (!cy || !*cy) cy = "cys";
  if (noreg) snprintf(cmd, sizeof cmd, "'%s' set-status --state waiting >/dev/null 2>&1", cy); else
  // 진짜 claude 처럼 SessionStart 훅 스크립트(이름 session-start.sh) 아래에서 등록한다 — cys follow 의 계통 판정(skt1 · 헬퍼·도구 셸 거름)이 보는 모양.
  snprintf(cmd, sizeof cmd, "exec /bin/sh -c '\"$2\" usage-register --transcript \"$1\" >/dev/null 2>&1; \"$2\" set-status --state waiting >/dev/null 2>&1' session-start.sh '%s' '%s'", tp, cy);
  if (helper) { system(cmd); return 0; } // 헬퍼 = 등록하고 끝(화면·tty 0)
  const char *hg = getenv("FAKE_HELPER_GATE");
  if (hg && *hg) { if (fork() == 0) { for (int i = 0; i < 1200 && access(hg, F_OK) != 0; i++) usleep(100000); setenv("FAKE_HELPER", "1", 1); unsetenv("FAKE_REG_GATE"); execlp(av[0], "claude", "-p", "hi", (char *)0); _exit(0); } }
  const char *gate = getenv("FAKE_REG_GATE");
  // 미룬 등록도 훅 이름 셸에서(자식 = sh · claude 실행 파일 아님 — 같은 실행 파일 자식이면 계통이 「에이전트 2 = 헬퍼」로 보인다 · skt1).
  if (gate && *gate && !noreg) { if (fork() == 0) { execl("/bin/sh", "sh", "-c", "i=0; while [ ! -e \"$3\" ] && [ $i -lt 1200 ]; do sleep 0.1; i=$((i+1)); done; \"$2\" usage-register --transcript \"$1\" >/dev/null 2>&1; \"$2\" set-status --state waiting >/dev/null 2>&1", "session-start.sh", tp, cy, gate, (char *)0); _exit(0); } } else system(cmd);
  printf("Claude Code fake\n\xe2\x9d\xaf \n"); fflush(stdout);
  struct termios ti; if (!tcgetattr(0, &ti)) { cfmakeraw(&ti); tcsetattr(0, TCSANOW, &ti); }
  static char buf[1 << 16]; size_t n = 0; ssize_t r; 
  while ((r = read(0, buf + n, sizeof buf - 1 - n)) > 0) {
    n += r; buf[n] = 0;
    { char gp[1200]; snprintf(gp, sizeof gp, "%s/got.log", getenv("HOME")); FILE *g = fopen(gp, "a"); if (g) { fwrite(buf + n - r, 1, r, g); fclose(g); } }
    char *c = strstr(buf, "checkpoint-"); char *e = c ? strstr(c, ".md") : NULL;
    if (c && e) {
      char *s = c; while (s > buf && s[-1] != ' ' && s[-1] != '`') s--;
      char path[2000]; snprintf(path, sizeof path, "%.*s", (int)(e + 3 - s), s);
      char *m = strstr(e, "<!--"); char mark[300] = ""; if (m) { char *z = strstr(m, "-->"); if (z) snprintf(mark, sizeof mark, "%.*s", (int)(z + 3 - m), m); }
      if (mark[0]) { char dir[2000]; snprintf(dir, sizeof dir, "%s", path); char *sl2 = strrchr(dir, '/'); if (sl2) *sl2 = 0; snprintf(cmd, sizeof cmd, "mkdir -p '%s'", dir); system(cmd); FILE *o = fopen(path, "w"); if (o) { fprintf(o, "%s\n", mark); fclose(o); } n = 0; }
    }
    if (n > sizeof buf - 4096) n = 0;
  }
  return 0;
}
