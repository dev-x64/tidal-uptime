from __future__ import annotations


def render_login() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Tidal Status — Sign in</title>
  <style>
    :root {
      --bg: #111617;
      --panel: #171d1f;
      --border: #242d30;
      --text: #edf4ef;
      --muted: #93a5a0;
      --accent: #f08a5d;
      --bad: #ff6b6b;
    }
    * { box-sizing: border-box; }
    html { color-scheme: dark; }
    body {
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      font-family: "Trebuchet MS", "Segoe UI", sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at top left, rgba(240, 138, 93, 0.08), transparent 28%),
        linear-gradient(180deg, #101516 0%, #0d1213 100%);
    }
    .login-card {
      width: min(360px, calc(100vw - 32px));
      padding: 28px 26px;
      border: 1px solid var(--border);
      border-radius: 14px;
      background: var(--panel);
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.18);
    }
    h1 { margin: 0 0 6px; font-size: 20px; letter-spacing: 0.02em; }
    p { margin: 0 0 18px; color: var(--muted); font-size: 13px; }
    label { display: block; font-size: 12px; color: var(--muted); margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.08em; }
    input[type="password"] {
      width: 100%; padding: 10px 12px; border-radius: 8px;
      border: 1px solid var(--border); background: #0f1416; color: var(--text);
      font: inherit; outline: none;
    }
    input[type="password"]:focus { border-color: var(--accent); }
    button {
      width: 100%; margin-top: 14px; padding: 10px 14px; border-radius: 8px;
      border: 0; background: var(--accent); color: #1a1a1a; font: inherit;
      font-weight: 700; cursor: pointer;
    }
    button:disabled { opacity: 0.6; cursor: progress; }
    .error { margin-top: 12px; color: var(--bad); font-size: 13px; min-height: 18px; }
  </style>
</head>
<body>
  <main class="login-card">
    <h1>Tidal Status</h1>
    <p>Enter the admin password to continue.</p>
    <form id="login-form" autocomplete="on">
      <label for="password">Password</label>
      <input id="password" name="password" type="password" autocomplete="current-password" required autofocus>
      <button type="submit" id="submit">Sign in</button>
      <div class="error" id="error"></div>
    </form>
  </main>
  <script>
    const form = document.getElementById("login-form");
    const passwordInput = document.getElementById("password");
    const submit = document.getElementById("submit");
    const errorEl = document.getElementById("error");
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const password = passwordInput.value;
      if (!password) return;
      submit.disabled = true;
      errorEl.textContent = "";
      try {
        const response = await fetch("/api/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ password }),
        });
        if (response.ok) { window.location.replace("/"); return; }
        let detail = "Invalid password";
        try {
          const payload = await response.json();
          if (payload && typeof payload.detail === "string") detail = payload.detail;
        } catch (_) {}
        errorEl.textContent = detail;
      } catch (err) {
        errorEl.textContent = "Sign-in failed. Try again.";
      } finally {
        submit.disabled = false;
        passwordInput.select();
      }
    });
  </script>
</body>
</html>"""


def render_dashboard() -> str:
    return r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Tidal Status</title>
  <style>
    :root {
      --bg: #111617;
      --panel: #171d1f;
      --panel-soft: #1b2325;
      --border: #242d30;
      --text: #edf4ef;
      --muted: #93a5a0;
      --ok: #36c26d;
      --warn: #e3b341;
      --bad: #ff6b6b;
      --unknown: #3a474b;
      --accent: #f08a5d;
    }
    * { box-sizing: border-box; }
    html { color-scheme: dark; }
    body {
      margin: 0;
      font-family: "Trebuchet MS", "Segoe UI", sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at top left, rgba(240, 138, 93, 0.08), transparent 28%),
        linear-gradient(180deg, #101516 0%, #0d1213 100%);
    }
    a { color: inherit; }
    .shell {
      width: min(1100px, calc(100vw - 24px));
      margin: 0 auto;
      padding: 18px 0 40px;
    }
    .topbar {
      display: flex; align-items: center; justify-content: space-between;
      gap: 12px; margin-bottom: 18px; flex-wrap: wrap;
    }
    .brand { display:flex; align-items:center; gap:10px; }
    .brand .logo {
      width: 36px; height: 36px; border-radius: 10px;
      background: linear-gradient(135deg, var(--accent), #efb88a);
    }
    .brand h1 { margin: 0; font-size: 18px; letter-spacing: 0.02em; }
    .brand .small { color: var(--muted); font-size: 12px; }
    .topbar-actions { display:flex; gap:8px; flex-wrap: wrap; }
    .button, .ghost-button {
      display: inline-flex; align-items: center; gap:6px;
      padding: 9px 14px; border-radius: 9px; border: 1px solid var(--border);
      background: var(--panel); color: var(--text); font: inherit; cursor: pointer;
      font-weight: 600; font-size: 13px;
    }
    .button.primary { background: var(--accent); border-color: var(--accent); color: #1a1a1a; }
    .button.primary:hover { filter: brightness(1.08); }
    .ghost-button:hover { border-color: #3a474b; }
    .button:disabled, .ghost-button:disabled { opacity: 0.5; cursor: not-allowed; }
    .danger { border-color: rgba(255, 107, 107, 0.4); color: #ff9494; }
    .card, .modal-panel {
      border: 1px solid var(--border);
      border-radius: 14px;
      background: var(--panel);
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.18);
    }
    .summary {
      padding: 18px 22px;
      display: grid; grid-template-columns: auto 1fr auto; align-items: center;
      gap: 16px; margin-bottom: 18px;
    }
    .summary-dot {
      width: 14px; height: 14px; border-radius: 50%;
      background: var(--unknown); box-shadow: 0 0 0 5px rgba(58,71,75,0.18);
    }
    .summary-dot.operational { background: var(--ok); box-shadow: 0 0 0 5px rgba(54,194,109,0.16); }
    .summary-dot.degraded { background: var(--warn); box-shadow: 0 0 0 5px rgba(227,179,65,0.16); }
    .summary-dot.outage { background: var(--bad); box-shadow: 0 0 0 5px rgba(255,107,107,0.16); }
    .summary-title { font-size: 18px; font-weight: 700; margin-bottom: 2px; }
    .summary-sub { color: var(--muted); font-size: 13px; }
    .summary-stats { display: flex; gap: 16px; }
    .summary-stats div { text-align: right; }
    .summary-stats b { font-size: 18px; }
    .summary-stats span { color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; }
    .group { margin-bottom: 22px; }
    .group-head {
      display:flex; align-items:center; justify-content: space-between;
      margin: 0 4px 10px; gap: 12px;
    }
    .group-title { font-weight: 700; font-size: 14px; letter-spacing: 0.04em; text-transform: uppercase; color: var(--muted); }
    .group-count { color: var(--muted); font-size: 12px; }
    .instances {
      display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px;
    }
    .instance {
      padding: 14px 16px; border: 1px solid var(--border); border-radius: 12px;
      background: var(--panel); display: flex; flex-direction: column; gap: 8px;
    }
    .instance-head { display:flex; align-items:center; gap: 10px; }
    .dot { width: 10px; height: 10px; border-radius: 50%; flex: 0 0 auto; background: var(--unknown); }
    .dot.operational { background: var(--ok); }
    .dot.degraded { background: var(--warn); }
    .dot.outage { background: var(--bad); }
    .instance-name {
      font-weight: 700; font-size: 14px; flex: 1; min-width: 0;
      overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
      text-decoration: none;
    }
    .badge {
      font-size: 11px; padding: 3px 8px; border-radius: 999px;
      border: 1px solid var(--border); background: var(--panel-soft); color: var(--muted);
    }
    .badge.ok { color: var(--ok); border-color: rgba(54,194,109,0.3); }
    .badge.bad { color: var(--bad); border-color: rgba(255,107,107,0.3); }
    .instance-meta { display: flex; gap: 12px; flex-wrap: wrap; color: var(--muted); font-size: 12px; }
    .subchecks { display: flex; flex-wrap: wrap; gap: 6px; }
    .subcheck-pill {
      font-size: 11px; padding: 3px 8px; border-radius: 999px;
      border: 1px solid var(--border); background: var(--panel-soft);
      display: inline-flex; align-items: center; gap: 5px;
    }
    .subcheck-pill .dot { width: 7px; height: 7px; }
    .history { display: flex; gap: 2px; align-items: center; }
    .history-bar {
      flex: 1; height: 18px; min-width: 3px; max-width: 5px; border-radius: 2px;
      background: var(--unknown);
    }
    .history-bar.operational { background: var(--ok); }
    .history-bar.degraded { background: var(--warn); }
    .history-bar.outage { background: var(--bad); }
    .latency-chart {
      position: relative; height: 64px; margin-top: 4px;
      border-radius: 8px; background: linear-gradient(180deg, rgba(240,138,93,0.04), rgba(240,138,93,0));
      border: 1px solid var(--border); overflow: hidden;
    }
    .latency-chart svg { display: block; width: 100%; height: 100%; }
    .latency-chart .axis-label {
      position: absolute; top: 4px; left: 8px;
      font-size: 10px; color: var(--muted); letter-spacing: 0.04em; text-transform: uppercase;
      pointer-events: none;
    }
    .latency-chart .axis-value {
      position: absolute; top: 4px; right: 8px;
      font-size: 11px; color: var(--text); font-weight: 600;
      pointer-events: none;
    }
    .latency-chart .axis-min {
      position: absolute; bottom: 4px; left: 8px;
      font-size: 10px; color: var(--muted);
      pointer-events: none;
    }
    .latency-chart .axis-max {
      position: absolute; bottom: 4px; right: 8px;
      font-size: 10px; color: var(--muted);
      pointer-events: none;
    }
    .latency-chart .empty-msg {
      position: absolute; inset: 0; display: grid; place-items: center;
      color: var(--muted); font-size: 12px;
    }
    .latency-chart .hover-line {
      position: absolute; top: 0; bottom: 0; width: 1px;
      background: rgba(237, 244, 239, 0.4); pointer-events: none; display: none;
    }
    .latency-chart .hover-tip {
      position: absolute; pointer-events: none; display: none;
      padding: 4px 7px; border-radius: 6px; border: 1px solid var(--border);
      background: #0d1213; color: var(--text); font-size: 11px; white-space: nowrap;
      transform: translate(-50%, -120%);
      box-shadow: 0 4px 12px rgba(0,0,0,0.35);
    }
    .latency-chart.hide { display: none; }
    .icon-toggle {
      display: inline-flex; align-items: center; justify-content: center;
      width: 26px; height: 26px; padding: 0; border-radius: 7px;
      border: 1px solid var(--border); background: var(--panel-soft);
      color: var(--muted); cursor: pointer; transition: color 0.15s, border-color 0.15s;
    }
    .icon-toggle:hover { color: var(--text); border-color: #3a474b; }
    .icon-toggle.active { color: var(--accent); border-color: rgba(240,138,93,0.5); background: rgba(240,138,93,0.08); }
    .icon-toggle svg { width: 14px; height: 14px; display: block; }
    .instance-head-actions { display: inline-flex; gap: 6px; align-items: center; }
    .badge.link { cursor: pointer; text-decoration: none; transition: filter 0.15s; }
    .badge.link:hover { filter: brightness(1.2); }
    .badge.link::after { content: " ↗"; opacity: 0.7; }
    .metrics-block {
      width: 100%; text-align: left; padding: 10px 12px;
      border: 1px solid var(--border); border-radius: 10px;
      background: var(--panel-soft); color: inherit; font: inherit; cursor: pointer;
      display: flex; flex-direction: column; gap: 6px;
      transition: border-color 0.15s, background 0.15s;
    }
    .metrics-block:hover { border-color: rgba(240,138,93,0.45); background: rgba(240,138,93,0.05); }
    .metrics-head {
      display: flex; align-items: center; justify-content: space-between;
      font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.06em;
    }
    .metrics-link { color: var(--accent); font-weight: 700; }
    .metrics-rows { display: grid; gap: 4px; }
    .metrics-row {
      display: flex; align-items: baseline; justify-content: space-between; gap: 10px;
      font-size: 12.5px; line-height: 1.3;
    }
    .metrics-label { color: var(--muted); flex: 0 0 auto; max-width: 55%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .metrics-val {
      color: var(--text); font-weight: 600; text-align: right;
      overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0;
    }
    .metrics-val.muted { color: var(--muted); font-weight: 400; }
    .metrics-error { color: var(--bad); font-size: 12px; }
    .metrics-meta { color: var(--muted); font-size: 12px; margin-bottom: 8px; }
    .metrics-json {
      margin: 0; padding: 14px; border-radius: 10px; border: 1px solid var(--border);
      background: #0d1213; color: var(--text); font-family: "Consolas", "Menlo", monospace;
      font-size: 12.5px; line-height: 1.5; max-height: 60vh; overflow: auto;
      white-space: pre; word-break: normal;
    }
    .subcheck-pill.link { cursor: pointer; transition: border-color 0.15s, color 0.15s; text-decoration: none; color: inherit; }
    .subcheck-pill.link:hover { border-color: #3a474b; color: var(--text); }
    .subcheck-pill.fail { border-color: rgba(255,107,107,0.35); }
    .instance-actions { display: flex; gap: 6px; flex-wrap: wrap; }
    .instance-actions .ghost-button { padding: 5px 10px; font-size: 12px; }
    footer.foot {
      margin-top: 22px; color: var(--muted); font-size: 12px;
      display: flex; justify-content: space-between; gap: 12px; flex-wrap: wrap;
    }
    .modal {
      position: fixed; inset: 0; background: rgba(8, 12, 13, 0.62);
      display: none; align-items: flex-start; justify-content: center;
      padding: 32px 16px; z-index: 50; overflow-y: auto;
    }
    .modal.open { display: flex; }
    .modal-panel {
      width: min(820px, 100%); padding: 20px 22px; max-height: calc(100vh - 64px);
      overflow-y: auto;
    }
    .modal-head { display:flex; align-items:flex-start; justify-content: space-between; gap: 12px; margin-bottom: 16px; }
    .modal-title { font-weight: 700; font-size: 18px; }
    .modal-sub { color: var(--muted); font-size: 13px; }
    .tabs { display: flex; gap: 6px; border-bottom: 1px solid var(--border); margin-bottom: 16px; }
    .tab {
      padding: 8px 14px; border: 0; background: transparent; color: var(--muted);
      cursor: pointer; font: inherit; font-weight: 600; font-size: 13px;
      border-bottom: 2px solid transparent; margin-bottom: -1px;
    }
    .tab.active { color: var(--text); border-color: var(--accent); }
    .field { margin-bottom: 12px; }
    .field label { display: block; font-size: 11px; color: var(--muted); margin-bottom: 5px; text-transform: uppercase; letter-spacing: 0.08em; }
    .row { display: grid; gap: 10px; }
    .row.cols-2 { grid-template-columns: 1fr 1fr; }
    .row.cols-3 { grid-template-columns: 1fr 1fr 1fr; }
    .row.cols-3-1 { grid-template-columns: 1fr 1fr 0.7fr; }
    input[type="url"], input[type="text"], input[type="number"], input[type="email"], input[type="password"], select, textarea {
      width: 100%; padding: 9px 11px; border-radius: 8px;
      border: 1px solid var(--border); background: #0f1416; color: var(--text);
      font: inherit; outline: none;
    }
    input:focus, select:focus, textarea:focus { border-color: var(--accent); }
    .checkbox-row {
      display: flex; align-items: center; gap: 8px; padding: 6px 0;
      color: var(--text); font-size: 13px;
    }
    .checkbox-row input[type="checkbox"] { width: 16px; height: 16px; accent-color: var(--accent); }
    .kind-toggle { display: flex; gap: 6px; }
    .kind-toggle label {
      flex: 1; text-align: center; padding: 10px; border-radius: 9px;
      border: 1px solid var(--border); cursor: pointer; font-weight: 600; font-size: 13px;
      color: var(--muted); text-transform: none; letter-spacing: 0;
    }
    .kind-toggle input { display: none; }
    .kind-toggle input:checked + span {
      color: var(--text);
    }
    .kind-toggle label:has(input:checked) { border-color: var(--accent); background: rgba(240,138,93,0.08); color: var(--text); }
    .actions-row { display: flex; gap: 8px; margin-top: 8px; }
    .status { font-size: 13px; padding: 8px 0; min-height: 18px; }
    .status.success { color: var(--ok); }
    .status.error { color: var(--bad); }
    .toast {
      position: fixed; right: 22px; bottom: 22px; max-width: 360px;
      padding: 12px 14px; border-radius: 10px; border: 1px solid var(--border);
      background: var(--panel); box-shadow: 0 10px 30px rgba(0,0,0,0.4); z-index: 60;
      display: none;
    }
    .toast.open { display: block; }
    .toast.success { border-color: rgba(54,194,109,0.45); }
    .toast.error { border-color: rgba(255,107,107,0.45); }
    .toast-title { font-weight: 700; margin-bottom: 4px; font-size: 13px; }
    .toast-body { font-size: 12px; color: var(--muted); }
    .subcheck-card {
      border: 1px solid var(--border); border-radius: 10px; padding: 12px;
      margin-bottom: 10px; background: var(--panel-soft);
    }
    .subcheck-card .row { margin-bottom: 8px; }
    .subcheck-card-head { display:flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
    .empty { color: var(--muted); font-size: 13px; padding: 12px 0; }
    .group-row {
      display: flex; align-items: center; justify-content: space-between;
      padding: 10px 12px; border: 1px solid var(--border); border-radius: 10px;
      margin-bottom: 8px; background: var(--panel-soft);
    }
    .group-row-actions { display: flex; gap: 6px; }
    .help { color: var(--muted); font-size: 12px; margin-top: -4px; margin-bottom: 12px; }
  </style>
</head>
<body>
  <div class="shell">
    <div class="topbar">
      <div class="brand">
        <div class="logo"></div>
        <div>
          <h1>Tidal Status</h1>
          <div class="small">Last updated <span id="last-updated">—</span> · refreshes every <span id="refresh-interval">—</span></div>
        </div>
      </div>
      <div class="topbar-actions">
        <button class="ghost-button" id="refresh-button" type="button">Refresh now</button>
        <button class="ghost-button" id="manage-button" type="button">Manage</button>
        <button class="ghost-button" id="logout-button" type="button">Logout</button>
      </div>
    </div>

    <section class="card summary">
      <div class="summary-dot" id="summary-dot"></div>
      <div>
        <div class="summary-title" id="summary-title">Loading…</div>
        <div class="summary-sub" id="summary-sub"></div>
      </div>
      <div class="summary-stats">
        <div><b id="stat-api">0</b><br><span>API alive</span></div>
        <div><b id="stat-stream">0</b><br><span>Streaming</span></div>
        <div><b id="stat-down">0</b><br><span>Down</span></div>
      </div>
    </section>

    <main id="groups-container"></main>

    <footer class="foot">
      <div id="footer-stats">—</div>
      <div>Status data <a href="/status.json" target="_blank" rel="noreferrer">/status.json</a></div>
    </footer>
  </div>

  <!-- Manager modal -->
  <div class="modal" id="manage-modal" aria-hidden="true">
    <div class="modal-panel">
      <div class="modal-head">
        <div>
          <div class="modal-title">Manager</div>
          <div class="modal-sub">Configure monitors, groups, and email subscriptions.</div>
        </div>
        <button class="ghost-button" id="close-manage" type="button">Close</button>
      </div>
      <div class="tabs">
        <button class="tab active" data-tab="instances" type="button">Monitors</button>
        <button class="tab" data-tab="groups" type="button">Groups</button>
        <button class="tab" data-tab="subscriptions" type="button">Subscriptions</button>
      </div>

      <section data-pane="instances">
        <div class="actions-row" style="margin-bottom: 10px;">
          <button class="button primary" id="add-instance" type="button">+ Add monitor</button>
          <button class="ghost-button" id="disable-all-alerts" type="button">Disable alerts on all monitors</button>
        </div>
        <div id="instance-list"></div>
      </section>

      <section data-pane="groups" hidden>
        <form id="group-form" class="card" style="padding:14px 16px; margin-bottom: 12px;">
          <div class="row cols-2">
            <div class="field">
              <label for="group-name">Group name</label>
              <input id="group-name" type="text" required>
            </div>
            <div class="field">
              <label for="group-sort">Sort order</label>
              <input id="group-sort" type="number" value="0">
            </div>
          </div>
          <div class="actions-row">
            <button class="button primary" id="group-submit" type="submit">Add group</button>
            <button class="ghost-button" id="group-cancel" type="button" hidden>Cancel</button>
          </div>
          <div class="status" id="group-status"></div>
        </form>
        <div id="group-list"></div>
      </section>

      <section data-pane="subscriptions" hidden>
        <p class="help">Email subscriptions are managed per-monitor. Click the bell icon on the status page to add an email for a specific monitor.</p>
        <div id="subscriptions-list"></div>
      </section>
    </div>
  </div>

  <!-- Instance form modal -->
  <div class="modal" id="instance-modal" aria-hidden="true">
    <div class="modal-panel">
      <div class="modal-head">
        <div>
          <div class="modal-title" id="instance-form-title">Add monitor</div>
          <div class="modal-sub">Define what to check, response matching, optional sub-checks, and alerting.</div>
        </div>
        <button class="ghost-button" id="close-instance" type="button">Close</button>
      </div>
      <form id="instance-form">
        <div class="row cols-2">
          <div class="field">
            <label for="inst-url">URL</label>
            <input id="inst-url" type="url" placeholder="https://example.com" required>
          </div>
          <div class="field">
            <label for="inst-name">Display name (optional)</label>
            <input id="inst-name" type="text" placeholder="Auto from URL">
          </div>
        </div>

        <div class="row cols-2">
          <div class="field">
            <label>Type</label>
            <div class="kind-toggle">
              <label><input type="radio" name="kind" value="tidal" checked><span>Tidal (api/search/track)</span></label>
              <label><input type="radio" name="kind" value="http"><span>Generic HTTP</span></label>
            </div>
          </div>
          <div class="field">
            <label for="inst-group">Group</label>
            <select id="inst-group"></select>
          </div>
        </div>

        <div id="http-fields" hidden>
          <div class="row cols-3-1">
            <div class="field">
              <label for="inst-method">Method</label>
              <select id="inst-method">
                <option>GET</option><option>POST</option><option>HEAD</option><option>PUT</option><option>PATCH</option><option>DELETE</option>
              </select>
            </div>
            <div class="field">
              <label for="inst-expected-status">Expected status (optional)</label>
              <input id="inst-expected-status" type="number" placeholder="default: any 2xx/3xx">
            </div>
            <div class="field">
              <label for="inst-match-type">Response match</label>
              <select id="inst-match-type">
                <option value="">None</option>
                <option value="status">Status only</option>
                <option value="json_key">JSON key exists</option>
                <option value="json_equals">JSON key equals</option>
                <option value="contains">Body contains</option>
              </select>
            </div>
          </div>
          <div class="row cols-2" id="match-detail-row">
            <div class="field">
              <label for="inst-match-path">JSON path (e.g. data.items.0.id)</label>
              <input id="inst-match-path" type="text" placeholder="leave empty for root">
            </div>
            <div class="field">
              <label for="inst-match-value">Expected value / substring</label>
              <input id="inst-match-value" type="text">
            </div>
          </div>
          <p class="help">JSON path uses dotted notation; arrays accept either <code>key[0]</code> or <code>key.0</code>.</p>

          <div class="field">
            <label for="inst-metrics-url">Info URL (optional)</label>
            <input id="inst-metrics-url" type="url" placeholder="https://example.com/info.json">
          </div>
          <div class="field">
            <label for="inst-metrics-keys">Info keys to display (one per line)</label>
            <textarea id="inst-metrics-keys" rows="4" placeholder="status as Status&#10;nodes[0].name as Primary node&#10;queue.depth"></textarea>
            <p class="help">One JSON path per line. Optional label after <code>as</code>. The raw JSON stays available via the card.</p>
          </div>
        </div>

        <div class="field" style="margin-top: 6px;">
          <label>Sub-checks (extra requests for this monitor)</label>
          <div id="subchecks-list"></div>
          <button class="ghost-button" id="add-subcheck" type="button">+ Add sub-check</button>
        </div>

        <div class="row cols-2" style="margin-top: 12px;">
          <div>
            <label class="checkbox-row"><input type="checkbox" id="email-alerts-enabled"><span>Email alerts enabled (only sent if someone is subscribed to this monitor)</span></label>
            <label class="checkbox-row"><input type="checkbox" id="alert-recovery"><span>Send recovery notifications</span></label>
          </div>
          <div>
            <label class="checkbox-row"><input type="checkbox" id="alert-outage"><span>Alert on primary failure (outage)</span></label>
            <label class="checkbox-row"><input type="checkbox" id="alert-search"><span>Alert on search/sub-check failure</span></label>
            <label class="checkbox-row"><input type="checkbox" id="alert-track"><span>Alert on track failure (Tidal)</span></label>
          </div>
        </div>

        <div class="actions-row">
          <button class="button primary" id="instance-submit" type="submit">Save monitor</button>
          <button class="ghost-button" id="instance-delete" type="button" hidden>Delete</button>
        </div>
        <div class="status" id="instance-status"></div>
      </form>
    </div>
  </div>

  <!-- Metrics modal -->
  <div class="modal" id="metrics-modal" aria-hidden="true">
    <div class="modal-panel" style="width: min(720px, 100%);">
      <div class="modal-head">
        <div>
          <div class="modal-title">Info</div>
          <div class="modal-sub" id="metrics-target">—</div>
        </div>
        <button class="ghost-button" id="close-metrics" type="button">Close</button>
      </div>
      <div id="metrics-meta" class="metrics-meta"></div>
      <pre class="metrics-json" id="metrics-json">Loading…</pre>
    </div>
  </div>

  <!-- Subscribe modal -->
  <div class="modal" id="subscribe-modal" aria-hidden="true">
    <div class="modal-panel" style="max-width: 460px;">
      <div class="modal-head">
        <div>
          <div class="modal-title">Email alerts</div>
          <div class="modal-sub" id="subscribe-target">—</div>
        </div>
        <button class="ghost-button" id="close-subscribe" type="button">Close</button>
      </div>
      <form id="subscribe-form">
        <div class="field">
          <label for="subscribe-email">Email</label>
          <input id="subscribe-email" type="email" required>
        </div>
        <div class="actions-row">
          <button class="button primary" type="submit">Subscribe</button>
        </div>
        <div class="status" id="subscribe-status"></div>
      </form>
    </div>
  </div>

  <!-- Auth modal (re-login on cookie expiry) -->
  <div class="modal" id="auth-modal" aria-hidden="true">
    <div class="modal-panel" style="max-width: 380px;">
      <div class="modal-head">
        <div>
          <div class="modal-title">Session expired</div>
          <div class="modal-sub">Re-enter the admin password to continue.</div>
        </div>
      </div>
      <form id="auth-form">
        <div class="field">
          <label for="auth-password">Password</label>
          <input id="auth-password" type="password" autocomplete="current-password" required>
        </div>
        <div class="actions-row">
          <button class="button primary" type="submit">Unlock</button>
        </div>
        <div class="status" id="auth-status"></div>
      </form>
    </div>
  </div>

  <div class="toast" id="toast">
    <div class="toast-title" id="toast-title"></div>
    <div class="toast-body" id="toast-body"></div>
  </div>

  <script>
    const escapeHtml = (s) => String(s ?? "")
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");

    const state = {
      groups: [],
      instances: [],
      checkIntervalSeconds: 60,
      editingId: null,
      subscribeFor: null,
      subchecks: [],
      groupEditingId: null,
    };

    const refs = {
      lastUpdated: document.getElementById("last-updated"),
      refreshInterval: document.getElementById("refresh-interval"),
      summaryDot: document.getElementById("summary-dot"),
      summaryTitle: document.getElementById("summary-title"),
      summarySub: document.getElementById("summary-sub"),
      statApi: document.getElementById("stat-api"),
      statStream: document.getElementById("stat-stream"),
      statDown: document.getElementById("stat-down"),
      groupsContainer: document.getElementById("groups-container"),
      footerStats: document.getElementById("footer-stats"),
      manageBtn: document.getElementById("manage-button"),
      refreshBtn: document.getElementById("refresh-button"),
      logoutBtn: document.getElementById("logout-button"),
      manageModal: document.getElementById("manage-modal"),
      closeManage: document.getElementById("close-manage"),
      instanceModal: document.getElementById("instance-modal"),
      closeInstance: document.getElementById("close-instance"),
      subscribeModal: document.getElementById("subscribe-modal"),
      closeSubscribe: document.getElementById("close-subscribe"),
      authModal: document.getElementById("auth-modal"),
      metricsModal: document.getElementById("metrics-modal"),
      closeMetrics: document.getElementById("close-metrics"),
      metricsTarget: document.getElementById("metrics-target"),
      metricsMeta: document.getElementById("metrics-meta"),
      metricsJson: document.getElementById("metrics-json"),
      addInstanceBtn: document.getElementById("add-instance"),
      instanceList: document.getElementById("instance-list"),
      groupList: document.getElementById("group-list"),
      subscriptionsList: document.getElementById("subscriptions-list"),
      groupForm: document.getElementById("group-form"),
      groupName: document.getElementById("group-name"),
      groupSort: document.getElementById("group-sort"),
      groupSubmit: document.getElementById("group-submit"),
      groupCancel: document.getElementById("group-cancel"),
      groupStatus: document.getElementById("group-status"),
      instanceForm: document.getElementById("instance-form"),
      instanceFormTitle: document.getElementById("instance-form-title"),
      instUrl: document.getElementById("inst-url"),
      instName: document.getElementById("inst-name"),
      instGroup: document.getElementById("inst-group"),
      instMethod: document.getElementById("inst-method"),
      instExpectedStatus: document.getElementById("inst-expected-status"),
      instMatchType: document.getElementById("inst-match-type"),
      instMatchPath: document.getElementById("inst-match-path"),
      instMatchValue: document.getElementById("inst-match-value"),
      instMetricsUrl: document.getElementById("inst-metrics-url"),
      instMetricsKeys: document.getElementById("inst-metrics-keys"),
      httpFields: document.getElementById("http-fields"),
      kindRadios: document.querySelectorAll("input[name='kind']"),
      subchecksList: document.getElementById("subchecks-list"),
      addSubcheck: document.getElementById("add-subcheck"),
      emailAlerts: document.getElementById("email-alerts-enabled"),
      alertRecovery: document.getElementById("alert-recovery"),
      alertOutage: document.getElementById("alert-outage"),
      alertSearch: document.getElementById("alert-search"),
      alertTrack: document.getElementById("alert-track"),
      instanceSubmit: document.getElementById("instance-submit"),
      instanceDelete: document.getElementById("instance-delete"),
      instanceStatus: document.getElementById("instance-status"),
      subscribeForm: document.getElementById("subscribe-form"),
      subscribeEmail: document.getElementById("subscribe-email"),
      subscribeTarget: document.getElementById("subscribe-target"),
      subscribeStatus: document.getElementById("subscribe-status"),
      authForm: document.getElementById("auth-form"),
      authPassword: document.getElementById("auth-password"),
      authStatus: document.getElementById("auth-status"),
      toast: document.getElementById("toast"),
      toastTitle: document.getElementById("toast-title"),
      toastBody: document.getElementById("toast-body"),
    };

    let toastTimer = null;
    function showToast(title, body, kind = "") {
      refs.toast.className = "toast open " + kind;
      refs.toastTitle.textContent = title;
      refs.toastBody.textContent = body || "";
      clearTimeout(toastTimer);
      toastTimer = setTimeout(() => { refs.toast.classList.remove("open"); }, 3500);
    }

    function setStatus(el, msg, kind = "") {
      el.textContent = msg || "";
      el.className = "status " + kind;
    }

    async function fetchJson(url, options = {}) {
      const init = {
        headers: { "Content-Type": "application/json", ...(options.headers || {}) },
        ...options,
      };
      const response = await fetch(url, init);
      if (response.status === 401) {
        openAuthModal();
        throw new Error("Authentication required");
      }
      if (response.status === 204) return null;
      const contentType = response.headers.get("content-type") || "";
      const payload = contentType.includes("application/json") ? await response.json() : null;
      if (!response.ok) {
        const detail = (payload && typeof payload.detail === "string") ? payload.detail : `HTTP ${response.status}`;
        throw new Error(detail);
      }
      return payload;
    }

    function formatTime(value) {
      if (!value) return "—";
      try {
        const date = new Date(value);
        return date.toLocaleString();
      } catch (_) { return value; }
    }
    function formatIntervalLabel(seconds) {
      if (!seconds) return "—";
      if (seconds % 60 === 0) return `${seconds / 60} min`;
      return `${seconds} s`;
    }
    function formatLatencyText(ms) {
      if (ms === null || ms === undefined) return "";
      if (ms >= 1000) return `${(ms / 1000).toFixed(2)} s`;
      return `${ms} ms`;
    }
    function formatLatencyBadge(ms) {
      const text = formatLatencyText(ms);
      if (!text) return "";
      const cls = ms >= 2000 ? "badge bad" : (ms >= 800 ? "badge" : "badge ok");
      return `<span class="${cls}" title="Response time">${escapeHtml(text)}</span>`;
    }

    function hostnameOf(url) {
      try { return new URL(url).hostname; } catch (_) { return url; }
    }

    function loadStatusPage() {
      return fetchJson("/api/status-page", { cache: "no-store" })
        .then((payload) => {
          if (!payload) return;
          state.checkIntervalSeconds = payload.checkIntervalSeconds || 60;
          state.groups = payload.groups || [];
          state.instances = payload.instances || [];
          renderSummary(payload);
          renderGroups(payload);
        })
        .catch((err) => {
          if (err.message === "Authentication required") return;
          refs.summaryDot.className = "summary-dot outage";
          refs.summaryTitle.textContent = "Dashboard unavailable";
          refs.summarySub.textContent = err.message;
        });
    }

    function renderSummary(payload) {
      const summary = payload.summary || {};
      const dotClass = summary.state || "operational";
      refs.summaryDot.className = `summary-dot ${dotClass}`;
      const titles = {
        operational: "All systems operational",
        degraded: "Some systems degraded",
        outage: "Major outage detected",
      };
      refs.summaryTitle.textContent = titles[summary.state] || "Status";
      refs.summarySub.textContent = `${summary.totalInstances || 0} monitors · ${(payload.referenceApiVersion || {}).version ? "Reference: " + payload.referenceApiVersion.version : "Reference: —"}`;
      refs.statApi.textContent = summary.apiCount || 0;
      refs.statStream.textContent = summary.streamingCount || 0;
      refs.statDown.textContent = summary.downCount || 0;
      refs.lastUpdated.textContent = formatTime(payload.lastUpdated);
      refs.refreshInterval.textContent = formatIntervalLabel(state.checkIntervalSeconds);
      refs.footerStats.textContent = `${summary.totalInstances || 0} monitors · ${summary.apiCount || 0} api · ${summary.streamingCount || 0} streaming · ${summary.downCount || 0} down`;
    }

    function renderGroups(payload) {
      const groupsById = new Map(state.groups.map((g) => [g.id, g]));
      const buckets = new Map();
      const orphan = [];
      for (const inst of state.instances) {
        if (inst.groupId && groupsById.has(inst.groupId)) {
          if (!buckets.has(inst.groupId)) buckets.set(inst.groupId, []);
          buckets.get(inst.groupId).push(inst);
        } else {
          orphan.push(inst);
        }
      }
      const sections = [];
      for (const group of state.groups) {
        const items = buckets.get(group.id) || [];
        if (items.length === 0) continue;
        sections.push(renderGroupSection(group.name, items));
      }
      if (orphan.length) sections.push(renderGroupSection("Other", orphan));
      refs.groupsContainer.innerHTML = sections.join("") || '<div class="empty">No monitors configured. Click <b>Manage</b> to add one.</div>';
      paintAllCharts();
    }

    function renderGroupSection(name, instances) {
      const cards = instances.map(renderInstanceCard).join("");
      return `
        <section class="group">
          <div class="group-head">
            <div class="group-title">${escapeHtml(name)}</div>
            <div class="group-count">${instances.length}</div>
          </div>
          <div class="instances">${cards}</div>
        </section>
      `;
    }

    const chartPrefKey = "tu.chart.";
    function isChartEnabled(id) {
      try { return localStorage.getItem(chartPrefKey + id) !== "0"; } catch (_) { return true; }
    }
    function setChartEnabled(id, on) {
      try { localStorage.setItem(chartPrefKey + id, on ? "1" : "0"); } catch (_) {}
    }

    function renderLatencyChart(item) {
      const points = (item.history || []).map((h) => h.responseTimeMs).filter((v) => v !== null && v !== undefined);
      if (!points.length) {
        return `<div class="latency-chart" data-chart-for="${item.id}">
          <div class="axis-label">Response time</div>
          <div class="empty-msg">No latency data yet</div>
        </div>`;
      }
      const avg = Math.round(points.reduce((a, b) => a + b, 0) / points.length);
      return `<div class="latency-chart" data-chart-for="${item.id}">
        <div class="axis-label">Response time · avg</div>
        <div class="axis-value">${escapeHtml(formatLatencyText(avg))}</div>
        <svg viewBox="0 0 100 100" preserveAspectRatio="none" data-chart-svg="${item.id}"></svg>
        <div class="axis-min" data-chart-min></div>
        <div class="axis-max" data-chart-max></div>
        <div class="hover-line" data-chart-line></div>
        <div class="hover-tip" data-chart-tip></div>
      </div>`;
    }

    function paintLatencyChart(container, item) {
      const svg = container.querySelector("[data-chart-svg]");
      if (!svg) return;
      const history = item.history || [];
      const series = history.map((h) => ({
        ms: (h.responseTimeMs === null || h.responseTimeMs === undefined) ? null : Number(h.responseTimeMs),
        state: h.state || "unknown",
        when: h.lastUpdated || "",
        error: h.error || null,
      }));
      const numericValues = series.filter((p) => p.ms !== null).map((p) => p.ms);
      if (!numericValues.length) return;
      const min = Math.min(...numericValues);
      const max = Math.max(...numericValues);
      const span = Math.max(1, max - min);
      const W = 100, H = 100, padTop = 14, padBot = 12, padLR = 2;
      const usableH = H - padTop - padBot;
      const xFor = (i) => series.length === 1 ? W / 2 : padLR + (i / (series.length - 1)) * (W - padLR * 2);
      const yFor = (v) => padTop + (1 - (v - min) / span) * usableH;

      const lastPoint = series[series.length - 1];
      const lineColor = lastPoint && lastPoint.ms !== null && lastPoint.ms >= 2000
        ? "#ff6b6b" : (lastPoint && lastPoint.ms !== null && lastPoint.ms >= 800 ? "#e3b341" : "#36c26d");

      const linePoints = [];
      const areaPoints = [];
      let started = false;
      let firstX = 0;
      let lastX = 0;
      series.forEach((p, i) => {
        if (p.ms === null) return;
        const x = xFor(i);
        const y = yFor(p.ms);
        if (!started) { firstX = x; started = true; }
        lastX = x;
        linePoints.push(`${x.toFixed(2)},${y.toFixed(2)}`);
        areaPoints.push(`${x.toFixed(2)},${y.toFixed(2)}`);
      });
      if (!linePoints.length) return;
      const areaPath = `M ${firstX.toFixed(2)},${(H - padBot).toFixed(2)} L ${areaPoints.join(" L ")} L ${lastX.toFixed(2)},${(H - padBot).toFixed(2)} Z`;

      const gradId = `lc-${item.id}`;
      const dots = series.map((p, i) => {
        if (p.ms === null) return "";
        const x = xFor(i).toFixed(2);
        const y = yFor(p.ms).toFixed(2);
        const fill = p.state === "outage" ? "#ff6b6b" : (p.state === "degraded" ? "#e3b341" : lineColor);
        const isLast = i === series.length - 1;
        const r = isLast ? 1.6 : 0;
        return `<circle cx="${x}" cy="${y}" r="${r}" fill="${fill}" />`;
      }).join("");

      svg.innerHTML = `
        <defs>
          <linearGradient id="${gradId}" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="${lineColor}" stop-opacity="0.35"/>
            <stop offset="100%" stop-color="${lineColor}" stop-opacity="0"/>
          </linearGradient>
        </defs>
        <path d="${areaPath}" fill="url(#${gradId})" />
        <polyline points="${linePoints.join(" ")}" fill="none" stroke="${lineColor}" stroke-width="1.4" stroke-linejoin="round" stroke-linecap="round" vector-effect="non-scaling-stroke"/>
        ${dots}
      `;

      const minLabel = container.querySelector("[data-chart-min]");
      const maxLabel = container.querySelector("[data-chart-max]");
      if (minLabel) minLabel.textContent = `min ${formatLatencyText(min)}`;
      if (maxLabel) maxLabel.textContent = `max ${formatLatencyText(max)}`;

      const hoverLine = container.querySelector("[data-chart-line]");
      const hoverTip = container.querySelector("[data-chart-tip]");
      const indices = series.map((p, i) => p.ms !== null ? i : -1).filter((i) => i >= 0);
      const onMove = (event) => {
        const rect = svg.getBoundingClientRect();
        if (!rect.width) return;
        const ratio = (event.clientX - rect.left) / rect.width;
        if (ratio < 0 || ratio > 1) return;
        let nearestIdx = indices[0];
        let nearestDist = Infinity;
        for (const i of indices) {
          const x = xFor(i) / 100;
          const d = Math.abs(x - ratio);
          if (d < nearestDist) { nearestDist = d; nearestIdx = i; }
        }
        const p = series[nearestIdx];
        const xPct = xFor(nearestIdx);
        hoverLine.style.left = `${xPct}%`;
        hoverLine.style.display = "block";
        hoverTip.style.left = `${xPct}%`;
        hoverTip.style.top = `${yFor(p.ms)}%`;
        hoverTip.style.display = "block";
        const dt = p.when ? new Date(p.when).toLocaleTimeString() : "";
        hoverTip.textContent = `${formatLatencyText(p.ms)}${dt ? " · " + dt : ""}`;
      };
      const onLeave = () => {
        hoverLine.style.display = "none";
        hoverTip.style.display = "none";
      };
      svg.addEventListener("mousemove", onMove);
      svg.addEventListener("mouseleave", onLeave);
    }

    const chartIcon = '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12L5.5 7.5L8.5 10L13.5 4"/><circle cx="13.5" cy="4" r="1.1" fill="currentColor" stroke="none"/></svg>';

    function renderInstanceCard(item) {
      const stateClass = item.state || "unknown";
      const labelName = item.name || hostnameOf(item.url);
      const versionTag = item.version ? `<span class="badge ok">v${escapeHtml(item.version)}</span>` : "";
      const uptimeTag = item.uptimePercentage !== null && item.uptimePercentage !== undefined
        ? `<span class="badge">${item.uptimePercentage.toFixed(2)}%</span>` : "";
      const latencyTag = formatLatencyBadge(item.responseTimeMs);
      const subchecks = (item.subchecks || []).map((s) => {
        const sCls = s.ok === true ? "operational" : (s.ok === false ? "outage" : "");
        const latencyText = formatLatencyText(s.responseTimeMs);
        const tip = [s.label, latencyText, s.error, s.url].filter(Boolean).join(" · ");
        const trailing = latencyText ? ` <span style="color:var(--muted);">${escapeHtml(latencyText)}</span>` : "";
        const failCls = s.ok === false ? " fail" : "";
        if (s.url) {
          return `<a class="subcheck-pill link${failCls}" href="${escapeHtml(s.url)}" target="_blank" rel="noreferrer" title="${escapeHtml(tip)}"><span class="dot ${sCls}"></span>${escapeHtml(s.label)}${trailing}</a>`;
        }
        return `<span class="subcheck-pill${failCls}" title="${escapeHtml(tip)}"><span class="dot ${sCls}"></span>${escapeHtml(s.label)}${trailing}</span>`;
      }).join("");
      let issueLine = "";
      if ((item.state === "outage" || item.state === "degraded") && item.error) {
        const failedSub = (item.subchecks || []).find((s) => s.ok === false);
        if (failedSub && failedSub.url) {
          const tip = [failedSub.label, failedSub.error, failedSub.url].filter(Boolean).join(" · ");
          issueLine = `<div class="instance-meta"><a class="badge bad link" href="${escapeHtml(failedSub.url)}" target="_blank" rel="noreferrer" title="Open sub-check: ${escapeHtml(tip)}">${escapeHtml(item.error)}</a></div>`;
        } else {
          issueLine = `<div class="instance-meta"><span class="badge bad">${escapeHtml(item.error)}</span></div>`;
        }
      }
      const history = (item.history || []).slice(-60).map((h) => {
        const c = h.state && h.state !== "unknown" ? h.state : "";
        const latencyText = formatLatencyText(h.responseTimeMs);
        const tip = [h.lastUpdated || "", latencyText, h.error].filter(Boolean).join(" · ");
        return `<span class="history-bar ${c}" title="${escapeHtml(tip)}"></span>`;
      }).join("");
      const chartOn = isChartEnabled(item.id);
      const metricsBlock = renderMetricsBlock(item);
      return `
        <article class="instance">
          <div class="instance-head">
            <span class="dot ${stateClass}"></span>
            <a class="instance-name" href="${escapeHtml(item.url)}" target="_blank" rel="noreferrer">${escapeHtml(labelName)}</a>
            ${versionTag}
            <span class="instance-head-actions">
              <button class="icon-toggle ${chartOn ? "active" : ""}" type="button" data-action="toggle-chart" data-id="${item.id}" title="${chartOn ? "Hide response time graph" : "Show response time graph"}" aria-label="Toggle response time graph">${chartIcon}</button>
            </span>
          </div>
          ${subchecks ? `<div class="subchecks">${subchecks}</div>` : ""}
          ${issueLine}
          <div class="history">${history}</div>
          ${chartOn ? renderLatencyChart(item) : ""}
          ${metricsBlock}
          <div class="instance-meta">
            ${uptimeTag}
            ${latencyTag}
            <span class="badge">${escapeHtml(item.kind || "tidal")}</span>
          </div>
          <div class="instance-actions">
            <button class="ghost-button" type="button" data-action="edit" data-id="${item.id}">Edit</button>
            <button class="ghost-button" type="button" data-action="subscribe" data-id="${item.id}" data-url="${escapeHtml(item.url)}">Email alerts</button>
          </div>
        </article>
      `;
    }

    function renderMetricsBlock(item) {
      const m = item.metrics;
      if (!m || !m.url) return "";
      const headerText = m.fetchedAt ? `Info · updated ${formatTime(m.fetchedAt)}` : "Info";
      let body = "";
      if (m.error) {
        body = `<div class="metrics-error">${escapeHtml(m.error)}</div>`;
      } else if (m.parseError) {
        body = `<div class="metrics-error">${escapeHtml(m.parseError)}</div>`;
      } else if (m.values && m.values.length) {
        body = `<div class="metrics-rows">${m.values.map((v) => {
          const valueText = v.found ? v.value : "—";
          const cls = v.found ? "metrics-val" : "metrics-val muted";
          return `<div class="metrics-row"><span class="metrics-label" title="${escapeHtml(v.path)}">${escapeHtml(v.label)}</span><span class="${cls}" title="${escapeHtml(v.value || "")}">${escapeHtml(valueText)}</span></div>`;
        }).join("")}</div>`;
      } else if (m.hasPayload) {
        body = `<div class="metrics-row" style="color:var(--muted); font-size:12px;">No keys configured. Click to view JSON.</div>`;
      } else {
        body = `<div class="metrics-row" style="color:var(--muted); font-size:12px;">Awaiting first fetch…</div>`;
      }
      return `<button class="metrics-block" type="button" data-action="metrics" data-id="${item.id}" title="View raw JSON">
        <div class="metrics-head"><span>${escapeHtml(headerText)}</span><span class="metrics-link">view JSON ↗</span></div>
        ${body}
      </button>`;
    }

    function paintAllCharts() {
      const instancesById = new Map(state.instances.map((i) => [i.id, i]));
      document.querySelectorAll(".latency-chart[data-chart-for]").forEach((node) => {
        const id = Number(node.dataset.chartFor);
        const item = instancesById.get(id);
        if (item) paintLatencyChart(node, item);
      });
    }

    refs.groupsContainer.addEventListener("click", (event) => {
      const btn = event.target.closest("button[data-action]");
      if (!btn) return;
      const id = Number(btn.dataset.id);
      const action = btn.dataset.action;
      if (action === "edit") {
        openInstanceForm(id);
      } else if (action === "subscribe") {
        openSubscribe(id, btn.dataset.url);
      } else if (action === "metrics") {
        openMetricsModal(id);
      } else if (action === "toggle-chart") {
        const wasOn = isChartEnabled(id);
        setChartEnabled(id, !wasOn);
        const card = btn.closest(".instance");
        const item = state.instances.find((x) => x.id === id);
        if (!card || !item) { renderGroups({}); return; }
        const existing = card.querySelector(".latency-chart");
        if (wasOn) {
          if (existing) existing.remove();
          btn.classList.remove("active");
          btn.title = "Show response time graph";
        } else {
          const historyEl = card.querySelector(".history");
          const tmp = document.createElement("div");
          tmp.innerHTML = renderLatencyChart(item);
          const node = tmp.firstElementChild;
          if (historyEl && node) {
            historyEl.insertAdjacentElement("afterend", node);
            paintLatencyChart(node, item);
          }
          btn.classList.add("active");
          btn.title = "Hide response time graph";
        }
      }
    });

    // ---------- Manager modal ----------
    function openManage() {
      refs.manageModal.classList.add("open");
      switchTab("instances");
      loadInstances();
      loadGroups();
    }
    function closeManage() { refs.manageModal.classList.remove("open"); }
    refs.manageBtn.addEventListener("click", openManage);
    refs.closeManage.addEventListener("click", closeManage);
    refs.manageModal.addEventListener("click", (e) => { if (e.target === refs.manageModal) closeManage(); });

    function switchTab(name) {
      document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === name));
      document.querySelectorAll("section[data-pane]").forEach((p) => { p.hidden = p.dataset.pane !== name; });
      if (name === "subscriptions") loadSubscriptions();
    }
    document.querySelectorAll(".tab").forEach((t) => t.addEventListener("click", () => switchTab(t.dataset.tab)));

    refs.refreshBtn.addEventListener("click", async () => {
      refs.refreshBtn.disabled = true;
      try {
        await fetchJson("/api/refresh", { method: "POST" });
        showToast("Refresh started", "Snapshot will update shortly.", "success");
        setTimeout(loadStatusPage, 1500);
      } catch (err) {
        if (err.message !== "Authentication required") showToast("Refresh failed", err.message, "error");
      } finally { refs.refreshBtn.disabled = false; }
    });

    refs.logoutBtn.addEventListener("click", async () => {
      try {
        await fetchJson("/api/auth/logout", { method: "POST" });
      } catch (_) {}
      window.location.replace("/");
    });

    // ---------- Instances ----------
    async function loadInstances() {
      try {
        const payload = await fetchJson("/api/instances", { cache: "no-store" });
        renderInstanceList(payload.items || []);
      } catch (err) {
        if (err.message !== "Authentication required") refs.instanceList.innerHTML = `<div class="empty">${escapeHtml(err.message)}</div>`;
      }
    }
    function renderInstanceList(items) {
      if (!items.length) { refs.instanceList.innerHTML = '<div class="empty">No monitors yet.</div>'; return; }
      refs.instanceList.innerHTML = items.map((item) => {
        const groupName = (state.groups.find((g) => g.id === item.group_id) || {}).name || "—";
        const subCount = (item.subchecks || []).length;
        return `
          <div class="group-row">
            <div>
              <div style="font-weight:700;">${escapeHtml(item.name || hostnameOf(item.url))}</div>
              <div style="color:var(--muted); font-size:12px;">${escapeHtml(item.url)} · ${escapeHtml(item.kind)} · ${escapeHtml(groupName)} · ${subCount} sub-check${subCount === 1 ? "" : "s"}</div>
            </div>
            <div class="group-row-actions">
              <button class="ghost-button" type="button" data-edit="${item.id}">Edit</button>
              <button class="ghost-button danger" type="button" data-delete="${item.id}">Delete</button>
            </div>
          </div>
        `;
      }).join("");
    }
    refs.instanceList.addEventListener("click", async (event) => {
      const editId = event.target.dataset?.edit;
      const deleteId = event.target.dataset?.delete;
      if (editId) openInstanceForm(Number(editId));
      else if (deleteId) {
        if (!confirm("Delete this monitor?")) return;
        try {
          await fetchJson(`/api/instances/${deleteId}`, { method: "DELETE" });
          showToast("Deleted", "Monitor removed.", "success");
          await loadInstances();
          await loadStatusPage();
        } catch (err) {
          if (err.message !== "Authentication required") showToast("Delete failed", err.message, "error");
        }
      }
    });

    refs.addInstanceBtn.addEventListener("click", () => openInstanceForm(null));

    document.getElementById("disable-all-alerts").addEventListener("click", async () => {
      if (!confirm("Disable email alerts and all alert levels on every monitor?")) return;
      try {
        await fetchJson("/api/instances/settings", {
          method: "PATCH",
          body: JSON.stringify({
            emailAlertsEnabled: false,
            alertOnOutage: false,
            alertOnSearch: false,
            alertOnTrack: false,
            alertOnRecovery: false,
          }),
        });
        showToast("Disabled", "Alerts turned off for all monitors.", "success");
        await loadInstances();
      } catch (err) {
        if (err.message !== "Authentication required") showToast("Failed", err.message, "error");
      }
    });

    async function openInstanceForm(id) {
      state.editingId = id;
      state.subchecks = [];
      refs.instanceFormTitle.textContent = id ? "Edit monitor" : "Add monitor";
      refs.instanceDelete.hidden = !id;
      setStatus(refs.instanceStatus, "");
      refs.instanceForm.reset();
      refs.emailAlerts.checked = false;
      refs.alertRecovery.checked = false;
      refs.alertOutage.checked = false;
      refs.alertSearch.checked = false;
      refs.alertTrack.checked = false;
      refs.instMethod.value = "GET";
      refs.instMatchType.value = "";
      refs.kindRadios.forEach((r) => { r.checked = r.value === "tidal"; });
      await refreshGroupsDropdown();

      if (id) {
        try {
          const payload = await fetchJson("/api/instances", { cache: "no-store" });
          const item = (payload.items || []).find((x) => x.id === id);
          if (item) populateInstanceForm(item);
        } catch (err) {
          if (err.message !== "Authentication required") setStatus(refs.instanceStatus, err.message, "error");
        }
      }
      updateKindVisibility();
      renderSubchecks();
      refs.instanceModal.classList.add("open");
    }

    function populateInstanceForm(item) {
      refs.instUrl.value = item.url || "";
      refs.instName.value = item.name || "";
      refs.kindRadios.forEach((r) => { r.checked = r.value === item.kind; });
      refs.instGroup.value = item.group_id || "";
      refs.instMethod.value = item.request_method || "GET";
      refs.instExpectedStatus.value = item.expected_status ?? "";
      refs.instMatchType.value = item.match_type || "";
      refs.instMatchPath.value = item.match_path || "";
      refs.instMatchValue.value = item.match_value || "";
      refs.instMetricsUrl.value = item.metrics_url || "";
      refs.instMetricsKeys.value = item.metrics_keys || "";
      refs.emailAlerts.checked = !!item.email_alerts_enabled;
      refs.alertOutage.checked = !!item.alert_on_outage;
      refs.alertSearch.checked = !!item.alert_on_search;
      refs.alertTrack.checked = !!item.alert_on_track;
      refs.alertRecovery.checked = !!item.alert_on_recovery;
      state.subchecks = (item.subchecks || []).map((s) => ({ ...s }));
    }

    refs.kindRadios.forEach((r) => r.addEventListener("change", updateKindVisibility));
    function updateKindVisibility() {
      const kind = Array.from(refs.kindRadios).find((r) => r.checked)?.value || "tidal";
      refs.httpFields.hidden = kind !== "http";
    }

    function renderSubchecks() {
      if (!state.subchecks.length) {
        refs.subchecksList.innerHTML = '<div class="empty" style="padding:6px 0;">No sub-checks defined.</div>';
        return;
      }
      refs.subchecksList.innerHTML = state.subchecks.map((s, idx) => `
        <div class="subcheck-card" data-idx="${idx}">
          <div class="subcheck-card-head">
            <strong>Sub-check #${idx + 1}</strong>
            <button class="ghost-button danger" type="button" data-remove="${idx}">Remove</button>
          </div>
          <div class="row cols-2">
            <div class="field">
              <label>Label</label>
              <input type="text" data-field="label" value="${escapeHtml(s.label || "")}" placeholder="e.g. health">
            </div>
            <div class="field">
              <label>URL</label>
              <input type="url" data-field="url" value="${escapeHtml(s.url || "")}" placeholder="https://...">
            </div>
          </div>
          <div class="row cols-3-1">
            <div class="field">
              <label>Method</label>
              <select data-field="request_method">
                ${["GET","POST","HEAD","PUT","PATCH","DELETE"].map((m) => `<option ${(s.request_method||"GET")===m?"selected":""}>${m}</option>`).join("")}
              </select>
            </div>
            <div class="field">
              <label>Expected status</label>
              <input type="number" data-field="expected_status" value="${s.expected_status ?? ""}" placeholder="any 2xx/3xx">
            </div>
            <div class="field">
              <label>Response match</label>
              <select data-field="match_type">
                ${[["","None"],["status","Status only"],["json_key","JSON key exists"],["json_equals","JSON key equals"],["contains","Body contains"]].map(([v,l]) => `<option value="${v}" ${((s.match_type||"")===v)?"selected":""}>${l}</option>`).join("")}
              </select>
            </div>
          </div>
          <div class="row cols-2">
            <div class="field">
              <label>JSON path</label>
              <input type="text" data-field="match_path" value="${escapeHtml(s.match_path || "")}">
            </div>
            <div class="field">
              <label>Expected value / substring</label>
              <input type="text" data-field="match_value" value="${escapeHtml(s.match_value || "")}">
            </div>
          </div>
        </div>
      `).join("");
    }

    refs.subchecksList.addEventListener("click", (event) => {
      const removeIdx = event.target.dataset?.remove;
      if (removeIdx !== undefined) {
        state.subchecks.splice(Number(removeIdx), 1);
        renderSubchecks();
      }
    });

    refs.subchecksList.addEventListener("input", (event) => {
      const card = event.target.closest("[data-idx]");
      if (!card) return;
      const idx = Number(card.dataset.idx);
      const field = event.target.dataset.field;
      if (!field) return;
      const value = event.target.value;
      state.subchecks[idx] = { ...(state.subchecks[idx] || {}), [field]: value };
    });

    refs.addSubcheck.addEventListener("click", () => {
      state.subchecks.push({ label: "", url: "", request_method: "GET", expected_status: "", match_type: "", match_path: "", match_value: "" });
      renderSubchecks();
    });

    refs.closeInstance.addEventListener("click", () => refs.instanceModal.classList.remove("open"));
    refs.instanceModal.addEventListener("click", (e) => { if (e.target === refs.instanceModal) refs.instanceModal.classList.remove("open"); });

    refs.instanceForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const kind = Array.from(refs.kindRadios).find((r) => r.checked)?.value || "tidal";
      const groupVal = refs.instGroup.value;
      const payload = {
        url: refs.instUrl.value.trim(),
        name: refs.instName.value.trim() || null,
        kind,
        groupId: groupVal ? Number(groupVal) : null,
        requestMethod: refs.instMethod.value,
        expectedStatus: refs.instExpectedStatus.value !== "" ? Number(refs.instExpectedStatus.value) : null,
        matchType: refs.instMatchType.value || null,
        matchPath: refs.instMatchPath.value || null,
        matchValue: refs.instMatchValue.value || null,
        metricsUrl: (refs.instMetricsUrl.value || "").trim() || null,
        metricsKeys: (refs.instMetricsKeys.value || "").trim() || null,
        emailAlertsEnabled: refs.emailAlerts.checked,
        alertOnOutage: refs.alertOutage.checked,
        alertOnSearch: refs.alertSearch.checked,
        alertOnTrack: refs.alertTrack.checked,
        alertOnRecovery: refs.alertRecovery.checked,
        subchecks: state.subchecks
          .filter((s) => (s.url || "").trim())
          .map((s, idx) => ({
            label: s.label || "",
            url: (s.url || "").trim(),
            requestMethod: s.request_method || "GET",
            expectedStatus: s.expected_status !== "" && s.expected_status !== null && s.expected_status !== undefined ? Number(s.expected_status) : null,
            matchType: s.match_type || null,
            matchPath: s.match_path || null,
            matchValue: s.match_value || null,
            sortOrder: idx,
          })),
      };
      refs.instanceSubmit.disabled = true;
      setStatus(refs.instanceStatus, state.editingId ? "Saving…" : "Adding…");
      try {
        const url = state.editingId ? `/api/instances/${state.editingId}` : "/api/instances";
        const method = state.editingId ? "PUT" : "POST";
        await fetchJson(url, { method, body: JSON.stringify(payload) });
        showToast(state.editingId ? "Saved" : "Created", "Monitor updated.", "success");
        refs.instanceModal.classList.remove("open");
        await loadInstances();
        await loadStatusPage();
      } catch (err) {
        if (err.message !== "Authentication required") setStatus(refs.instanceStatus, err.message, "error");
      } finally { refs.instanceSubmit.disabled = false; }
    });

    refs.instanceDelete.addEventListener("click", async () => {
      if (!state.editingId) return;
      if (!confirm("Delete this monitor?")) return;
      try {
        await fetchJson(`/api/instances/${state.editingId}`, { method: "DELETE" });
        showToast("Deleted", "Monitor removed.", "success");
        refs.instanceModal.classList.remove("open");
        await loadInstances();
        await loadStatusPage();
      } catch (err) {
        if (err.message !== "Authentication required") setStatus(refs.instanceStatus, err.message, "error");
      }
    });

    // ---------- Groups ----------
    async function loadGroups() {
      try {
        const payload = await fetchJson("/api/groups", { cache: "no-store" });
        state.groups = payload.items || [];
        renderGroupList();
        await refreshGroupsDropdown();
      } catch (err) {
        if (err.message !== "Authentication required") refs.groupList.innerHTML = `<div class="empty">${escapeHtml(err.message)}</div>`;
      }
    }
    function renderGroupList() {
      if (!state.groups.length) { refs.groupList.innerHTML = '<div class="empty">No groups.</div>'; return; }
      refs.groupList.innerHTML = state.groups.map((g) => `
        <div class="group-row">
          <div>
            <div style="font-weight:700;">${escapeHtml(g.name)}</div>
            <div style="color:var(--muted); font-size:12px;">sort ${g.sort_order}</div>
          </div>
          <div class="group-row-actions">
            <button class="ghost-button" type="button" data-edit-group="${g.id}">Edit</button>
            <button class="ghost-button danger" type="button" data-delete-group="${g.id}">Delete</button>
          </div>
        </div>
      `).join("");
    }
    refs.groupList.addEventListener("click", async (event) => {
      const editId = event.target.dataset?.editGroup;
      const deleteId = event.target.dataset?.deleteGroup;
      if (editId) {
        const g = state.groups.find((x) => x.id === Number(editId));
        if (!g) return;
        state.groupEditingId = g.id;
        refs.groupName.value = g.name;
        refs.groupSort.value = g.sort_order;
        refs.groupSubmit.textContent = "Save group";
        refs.groupCancel.hidden = false;
      } else if (deleteId) {
        if (!confirm("Delete this group? Monitors will be moved to 'Other'.")) return;
        try {
          await fetchJson(`/api/groups/${deleteId}`, { method: "DELETE" });
          showToast("Deleted", "Group removed.", "success");
          await loadGroups();
          await loadStatusPage();
        } catch (err) {
          if (err.message !== "Authentication required") showToast("Delete failed", err.message, "error");
        }
      }
    });
    refs.groupCancel.addEventListener("click", () => {
      state.groupEditingId = null;
      refs.groupForm.reset();
      refs.groupSort.value = 0;
      refs.groupSubmit.textContent = "Add group";
      refs.groupCancel.hidden = true;
      setStatus(refs.groupStatus, "");
    });
    refs.groupForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const name = refs.groupName.value.trim();
      const sort = Number(refs.groupSort.value || 0);
      if (!name) return;
      refs.groupSubmit.disabled = true;
      try {
        if (state.groupEditingId) {
          await fetchJson(`/api/groups/${state.groupEditingId}`, { method: "PUT", body: JSON.stringify({ name, sortOrder: sort }) });
          showToast("Saved", "Group updated.", "success");
        } else {
          await fetchJson("/api/groups", { method: "POST", body: JSON.stringify({ name, sortOrder: sort }) });
          showToast("Created", "Group added.", "success");
        }
        state.groupEditingId = null;
        refs.groupForm.reset();
        refs.groupSort.value = 0;
        refs.groupSubmit.textContent = "Add group";
        refs.groupCancel.hidden = true;
        setStatus(refs.groupStatus, "");
        await loadGroups();
        await loadStatusPage();
      } catch (err) {
        if (err.message !== "Authentication required") setStatus(refs.groupStatus, err.message, "error");
      } finally { refs.groupSubmit.disabled = false; }
    });

    async function refreshGroupsDropdown() {
      if (!state.groups.length) {
        try {
          const payload = await fetchJson("/api/groups", { cache: "no-store" });
          state.groups = payload.items || [];
        } catch (_) {}
      }
      const options = ['<option value="">— None —</option>']
        .concat(state.groups.map((g) => `<option value="${g.id}">${escapeHtml(g.name)}</option>`));
      refs.instGroup.innerHTML = options.join("");
    }

    // ---------- Subscriptions ----------
    async function loadSubscriptions() {
      try {
        const payload = await fetchJson("/api/subscriptions", { cache: "no-store" });
        renderSubscriptions(payload.items || []);
      } catch (err) {
        if (err.message !== "Authentication required") refs.subscriptionsList.innerHTML = `<div class="empty">${escapeHtml(err.message)}</div>`;
      }
    }
    function renderSubscriptions(items) {
      if (!items.length) { refs.subscriptionsList.innerHTML = '<div class="empty">No subscriptions.</div>'; return; }
      refs.subscriptionsList.innerHTML = items.map((s) => `
        <div class="group-row">
          <div>
            <div style="font-weight:700;">${escapeHtml(s.email)}</div>
            <div style="color:var(--muted); font-size:12px;">${escapeHtml(s.endpoint_url)}</div>
          </div>
          <div class="group-row-actions">
            <button class="ghost-button danger" type="button" data-delete-sub="${s.id}">Delete</button>
          </div>
        </div>
      `).join("");
    }
    refs.subscriptionsList.addEventListener("click", async (event) => {
      const id = event.target.dataset?.deleteSub;
      if (!id) return;
      if (!confirm("Delete this subscription?")) return;
      try {
        await fetchJson(`/api/subscriptions/${id}`, { method: "DELETE" });
        await loadSubscriptions();
      } catch (err) {
        if (err.message !== "Authentication required") showToast("Delete failed", err.message, "error");
      }
    });

    function openSubscribe(endpointId, url) {
      state.subscribeFor = endpointId;
      refs.subscribeTarget.textContent = url;
      refs.subscribeEmail.value = "";
      setStatus(refs.subscribeStatus, "");
      refs.subscribeModal.classList.add("open");
    }
    refs.closeSubscribe.addEventListener("click", () => refs.subscribeModal.classList.remove("open"));
    refs.subscribeModal.addEventListener("click", (e) => { if (e.target === refs.subscribeModal) refs.subscribeModal.classList.remove("open"); });
    refs.subscribeForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const email = refs.subscribeEmail.value.trim();
      if (!email || !state.subscribeFor) return;
      try {
        await fetchJson(`/api/instances/${state.subscribeFor}/subscriptions`, {
          method: "POST", body: JSON.stringify({ email }),
        });
        showToast("Subscribed", "Email added.", "success");
        refs.subscribeModal.classList.remove("open");
      } catch (err) {
        if (err.message !== "Authentication required") setStatus(refs.subscribeStatus, err.message, "error");
      }
    });

    // ---------- Metrics modal ----------
    async function openMetricsModal(endpointId) {
      const item = state.instances.find((x) => x.id === endpointId);
      const labelName = item ? (item.name || hostnameOf(item.url)) : `monitor #${endpointId}`;
      const metricsUrl = item && item.metrics ? item.metrics.url : "";
      refs.metricsTarget.textContent = metricsUrl ? `${labelName} · ${metricsUrl}` : labelName;
      refs.metricsMeta.textContent = "";
      refs.metricsJson.textContent = "Loading…";
      refs.metricsModal.classList.add("open");
      try {
        const data = await fetchJson(`/api/instances/${endpointId}/metrics`, { cache: "no-store" });
        const meta = [];
        if (data.fetchedAt) meta.push(`fetched ${formatTime(data.fetchedAt)}`);
        if (data.statusCode !== null && data.statusCode !== undefined) meta.push(`HTTP ${data.statusCode}`);
        if (data.responseTimeMs !== null && data.responseTimeMs !== undefined) meta.push(formatLatencyText(data.responseTimeMs));
        if (data.ok === false && data.error) meta.push(`error: ${data.error}`);
        refs.metricsMeta.textContent = meta.join(" · ");
        if (!data.payloadJson) {
          refs.metricsJson.textContent = data.error || "No info fetched yet.";
          return;
        }
        let pretty = data.payloadJson;
        try { pretty = JSON.stringify(JSON.parse(data.payloadJson), null, 2); } catch (_) {}
        refs.metricsJson.textContent = pretty;
      } catch (err) {
        if (err.message !== "Authentication required") {
          refs.metricsJson.textContent = `Failed to load: ${err.message}`;
        }
      }
    }
    refs.closeMetrics.addEventListener("click", () => refs.metricsModal.classList.remove("open"));
    refs.metricsModal.addEventListener("click", (e) => { if (e.target === refs.metricsModal) refs.metricsModal.classList.remove("open"); });

    // ---------- Auth modal (re-login) ----------
    function openAuthModal() { refs.authModal.classList.add("open"); refs.authPassword.focus(); }
    refs.authForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const password = refs.authPassword.value;
      if (!password) return;
      setStatus(refs.authStatus, "Checking…");
      try {
        const response = await fetch("/api/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ password }),
        });
        if (!response.ok) {
          const payload = await response.json().catch(() => ({}));
          setStatus(refs.authStatus, payload.detail || "Invalid password", "error");
          return;
        }
        refs.authModal.classList.remove("open");
        refs.authPassword.value = "";
        setStatus(refs.authStatus, "");
        await loadStatusPage();
      } catch (err) {
        setStatus(refs.authStatus, err.message, "error");
      }
    });

    // ---------- Boot ----------
    loadStatusPage();
    let refreshTimer = null;
    function scheduleRefresh() {
      const ms = Math.max(15, state.checkIntervalSeconds || 60) * 1000;
      clearInterval(refreshTimer);
      refreshTimer = setInterval(loadStatusPage, ms);
    }
    setTimeout(scheduleRefresh, 2000);
  </script>
</body>
</html>
"""
