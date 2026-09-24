// v116-ui 헤드리스 흉내층 — Tauri invoke/listen 을 결정론 가짜로 대체(라이브 0).
// 원형 = master/reports/cysr-115-debug-2026-09-23/D4-evidence/shim.js(D4 · 996). 이 판의 추가:
//   · 호출 인자 기록(__shimCalls = [{cmd,args}]) · 좌석 종료 흉내(__shimExit) · 목록 조회 실패 주입(__shimFailList)
//   · 파일 흉내(__shimFiles: 경로 → 본문 · read_text_head 가 읽는다)
//   · (v116-restart-toast) 재시작 흉내(restart_after_update · __shimRestartLive = 살아 있는 세션 거부 · __shimRestartFail = 실패)
//     · 앱 판번 흉내(app_version ← __shimAppVersion · 지연 __shimAppVersionDelayMs · 실패 __shimFailAppVersion) · build_id(app_build_id ← __shimBuildId · 기본 build-A)
//     · 확인 응답 지연(__shimCheckDelayMs) · 새로고침(⌘R)을 넘어 남는 흉내 값 = sessionStorage "__shimUpdate"·"__shimAppVersion"
//   · (R1c) 좌석 추가(__shimAddSeat) · sc=late = master 없이 시작 · (D4 #12) 이름 바꾸기(rename_surface → 좌석 제목) · (D4 #18) control_dashboard(__shimDash) · (D4 #14) check_update 실패 주입(__shimFailUpdate) · 새 판 흉내(__shimUpdate)
(() => {
  const q = new URLSearchParams(location.search);
  const SC = q.get("sc") || "two";
  const calls = [];
  window.__shimCalls = calls;
  const handlers = {};
  const emit = (name, payload) => (handlers[name] || []).forEach((h) => { try { h({ event: name, payload }); } catch (e) { console.error("handler", name, e); } });
  window.__shimEmit = emit;
  const b64 = (s) => btoa(String.fromCharCode(...new TextEncoder().encode(s)));
  const now = Date.now() / 1000;
  const mk = (id, role, cwd) => ({ surface_id: id, role, title: `${id} · ${role}`, live_cwd: cwd, exited: false, agent: "claude", usage: { ctx_pct: 10 } });
  const SEATS = {
    two: [mk(1, "master", "/Users/user/jarvis"), mk(2, "worker", "/Users/user/jarvis/w1")],
    three: [mk(1, "master", "/Users/user/jarvis"), mk(2, "cso", "/Users/user/jarvis/cso"), mk(3, "worker", "/Users/user/jarvis/w1")],
    late: [mk(2, "worker", "/Users/user/jarvis/w1")], // (R1c) master 자리가 늦게 선다 — __shimAddSeat 로 나중에 세운다
  };
  const seats = SEATS[SC] || SEATS.two;
  window.__shimSeats = seats;
  window.__shimAddSeat = (id, role, cwd) => { seats.push(mk(id, role, cwd)); };
  window.__shimFiles = {};
  window.__shimFailList = 0;
  try {
    const u = sessionStorage.getItem("__shimUpdate");
    if (u) window.__shimUpdate = JSON.parse(u);
    const v = sessionStorage.getItem("__shimAppVersion");
    if (v) window.__shimAppVersion = v;
    window.__shimAppVersionDelayMs = Number(sessionStorage.getItem("__shimAppVersionDelayMs") || 0);
    window.__shimFailAppVersion = sessionStorage.getItem("__shimFailAppVersion") === "1";
    const b = sessionStorage.getItem("__shimBuildId");
    if (b) window.__shimBuildId = b;
  } catch {}
  // 좌석 종료 흉내 — 데몬 기록을 exited 로 바꾸고 pane 스트림 종료를 보낸다.
  //   withEvent=true 면 데몬 surface.exited 이벤트도 보낸다(평시 경로) · false 면 이벤트 유실(D4 #17 잔재 경로).
  window.__shimExit = (sid, withEvent) => {
    const s = seats.find((x) => x.surface_id === sid);
    if (!s) return;
    s.exited = true;
    emit(`exit-${sid}`, null);
    if (withEvent) emit("daemon-event", { name: "surface.exited", category: "surface", surface_id: sid, payload: {} });
  };
  const screen = (s) =>
    `\x1b[2J\x1b[H\x1b[1m✻ Welcome to Claude Code\x1b[0m  (${s.role})\r\n\r\n  작업 폴더: ${s.live_cwd}\r\n\r\n❯ \r\n`;
  const R = {
    daemon_status: () => ({ daemon_pid: 4242, version: "1.1.6", socket_path: "/Users/user/.local/state/cys/cys.sock", surface_count: seats.length, started_at: now - 60 }),
    list_surfaces: () => {
      if (window.__shimFailList > 0) { window.__shimFailList--; throw new Error("rpc timeout (shim)"); }
      if (Date.now() < (window.__shimFailUntil || 0)) throw new Error("rpc timeout (shim · window)");
      return { surfaces: seats.map((s) => ({ ...s })) };
    },
    org_status: () => ({ surfaces: seats.map((s) => ({ ...s, state: "working" })), feed: { pending: 0 } }),
    attach_surface: (a) => ({ output_event: `out-${a.surfaceId}`, exited_event: `exit-${a.surfaceId}` }),
    start_surface_stream: (a) => {
      const s = seats.find((x) => x.surface_id === a.surfaceId);
      setTimeout(() => { if (s) emit(`out-${a.surfaceId}`, b64(screen(s))); if (s && s.exited) emit(`exit-${a.surfaceId}`, null); }, 50);
      return null;
    },
    create_surface: () => { const id = 100 + seats.length; const s = mk(id, null, "/Users/user"); s.title = ""; seats.push(s); return { surface_id: id }; },
    rename_surface: (a) => { const s = seats.find((x) => x.surface_id === a.surfaceId); if (s) s.title = a.title; return null; },
    close_surface: (a) => { const i = seats.findIndex((x) => x.surface_id === a.surfaceId); if (i >= 0) seats.splice(i, 1); return null; },
    check_update: () => { if (window.__shimFailUpdate) throw "error sending request for url (https://example.invalid/latest.json): dns error"; return window.__shimUpdate || null; },
    control_dashboard: () => window.__shimDash || { fleet: [], uptime_secs: 60, version: "1.1.6" },
    usage_accounts_all: () => ({ accounts: window.__shimAccounts || [] }),
    usage_named_reporters: () => ({ reporters: [] }),
    list_depts: () => ({ depts: {} }),
    dept_tombstones: () => ({ tombstones: [] }),
    app_version: () => window.__shimAppVersion || "1.1.6",
    app_build_id: () => window.__shimBuildId || "build-A",
    restart_after_update: (a) => {
      if (window.__shimRestartFail) throw "restart failed (shim)";
      if (window.__shimRestartLive && !a.force) throw "live_sessions:2";
      return null;
    },
    home_dir_path: () => "/Users/user",
    read_text_head: (a) => { const t = window.__shimFiles[a.path]; if (t == null) throw new Error("not found"); return t; },
    list_dir: () => [],
    feed_list: () => ({ items: [] }),
    ceo_pending: () => null,
    bundle_integrity: () => ({ ok: true }),
    win_wheel_guard_disabled: () => false,
    alt_scroll_cursor_mode: () => false,
    ime_debug_enabled: () => false,
    claude_missing_hint: () => null,
    resource_gate_check: () => ({ ok: true }),
    control_skills: () => [], control_weekly: () => ({}), control_sessions: () => [],
    learn_status: () => ({}), skill_runs: () => [], org_fleet: () => ({}),
    read_dept_catalog: () => ({ entries: [] }), read_board_catalog: () => ({ entries: [] }),
    ensure_dept_forwarders: () => null,
  };
  const invoke = (cmd, args) => {
    calls.push({ cmd, args: args || {} });
    if (cmd === "check_update" && window.__shimCheckDelayMs) // 확인 응답 지연(진행 중 확인과 교체 완료 경합)
      return new Promise((res) => setTimeout(() => res(R.check_update()), window.__shimCheckDelayMs));
    if (cmd === "app_version" && (window.__shimAppVersionDelayMs || window.__shimFailAppVersion))
      return new Promise((res, rej) => setTimeout(() => (window.__shimFailAppVersion ? rej("app_version failed (shim)") : res(R.app_version())), window.__shimAppVersionDelayMs || 0));
    const f = R[cmd];
    return new Promise((res, rej) => { try { res(f ? f(args || {}) : null); } catch (e) { rej(e); } });
  };
  const listen = (name, h) => { (handlers[name] ||= []).push(h); return Promise.resolve(() => {}); };
  window.__TAURI__ = { core: { invoke }, event: { listen } };
  window.__TAURI_INTERNALS__ = { invoke: (c, a) => invoke(c, a), transformCallback: () => 0, metadata: { currentWindow: { label: "main" } } };
  setTimeout(() => emit("daemon-ready", null), 30);
})();
