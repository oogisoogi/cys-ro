// tests/update_drainhold_e2e.rs 의 좌석 대역: 이름이 claude 인 실행 파일(OS env 관측 · 자손 argv 일치를 받기 위해 스크립트가 아니다).
// --resume/--continue 를 따르고 · SessionStart 등록(cys usage-register)을 --resume 일 때 FAKE_BOOT 초 뒤에 · set-status waiting · [DRAIN-VERIFY] 체크포인트 저장.
// FAKE_NEW_SID = 재개해도 새 세션 id 로 등록(세션이 채워졌는데 다른 경우).
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <termios.h>
static void slug(const char *c, char *o) { for (; *c; c++, o++) *o = ((*c >= 'a' && *c <= 'z') || (*c >= 'A' && *c <= 'Z') || (*c >= '0' && *c <= '9')) ? *c : '-'; *o = 0; }
int main(int ac, char **av) {
  char sid[128] = "", cwd[900], sl[900], pd[2000], cmd[4000], tp[2200];
  int cont = 0;
  for (int i = 1; i < ac; i++) { if (!strcmp(av[i], "--resume") && i + 1 < ac) snprintf(sid, sizeof sid, "%s", av[i + 1]); if (!strcmp(av[i], "--continue")) cont = 1; }
  getcwd(cwd, sizeof cwd); slug(cwd, sl);
  const char *cd = getenv("CLAUDE_CONFIG_DIR");
  if (cd && *cd) snprintf(pd, sizeof pd, "%s/projects/%s", cd, sl); else snprintf(pd, sizeof pd, "%s/.claude/projects/%s", getenv("HOME"), sl);
  snprintf(cmd, sizeof cmd, "mkdir -p '%s'", pd); system(cmd);
  if (!sid[0] && cont) { snprintf(cmd, sizeof cmd, "ls -t '%s' 2>/dev/null | grep jsonl | head -1 | sed 's/.jsonl//'", pd); FILE *f = popen(cmd, "r"); if (f) { if (fgets(sid, sizeof sid, f)) sid[strcspn(sid, "\n")] = 0; pclose(f); } }
  if (!sid[0]) { FILE *f = popen("/usr/bin/uuidgen | tr A-Z a-z", "r"); fgets(sid, sizeof sid, f); sid[strcspn(sid, "\n")] = 0; pclose(f); }
  snprintf(tp, sizeof tp, "%s/%s.jsonl", pd, sid);
  FILE *t = fopen(tp, "a"); if (t) { fprintf(t, "{\"type\":\"user\",\"sessionId\":\"%s\",\"cwd\":\"%s\"}\n", sid, cwd); fclose(t); }
  char lg[1200]; snprintf(lg, sizeof lg, "%s/fake.log", getenv("HOME")); FILE *l = fopen(lg, "a"); if (l) { fprintf(l, "sid=%s surface=%s role=%s argv:", sid, getenv("CYS_SURFACE_ID") ?: "", getenv("CYS_ROLE") ?: ""); for (int i = 1; i < ac; i++) fprintf(l, " %s", av[i]); fprintf(l, "\n"); fclose(l); }
  for (int i = 1; i < ac; i++) if (getenv("FAKE_NEW_SID") && !strcmp(av[i], "--resume")) { FILE *f = popen("/usr/bin/uuidgen | tr A-Z a-z", "r"); fgets(sid, sizeof sid, f); sid[strcspn(sid, "\n")] = 0; pclose(f); snprintf(tp, sizeof tp, "%s/%s.jsonl", pd, sid); FILE *n = fopen(tp, "a"); if (n) fclose(n); }
  const char *bt = getenv("FAKE_BOOT"); for (int i = 1; i < ac; i++) if (bt && !strcmp(av[i], "--resume")) usleep((useconds_t)(atof(bt) * 1000000));
  snprintf(cmd, sizeof cmd, "cys usage-register --transcript '%s' >/dev/null 2>&1; cys set-status --state waiting >/dev/null 2>&1", tp); system(cmd);
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
