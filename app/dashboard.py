from __future__ import annotations


def render_dashboard() -> str:
    return """<!doctype html>
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

    .shell {
      width: min(980px, calc(100vw - 24px));
      margin: 0 auto;
      padding: 18px 0 34px;
    }

    .card, .banner, .modal-panel {
      border: 1px solid var(--border);
      border-radius: 14px;
      background: var(--panel);
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.18);
    }

    .banner {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 16px 18px;
      margin-bottom: 14px;
    }

    .banner-main {
      display: flex;
      align-items: center;
      gap: 12px;
      min-width: 0;
    }

    .dot {
      width: 12px;
      height: 12px;
      border-radius: 999px;
      flex: none;
      box-shadow: 0 0 0 4px rgba(255,255,255,0.03);
    }

    .dot.operational { background: var(--ok); }
    .dot.degraded { background: var(--warn); }
    .dot.outage { background: var(--bad); }
    .dot.unknown { background: var(--unknown); }

    .banner-title {
      font-size: 20px;
      font-weight: 700;
      letter-spacing: -0.02em;
    }

    .banner-subtitle, .small, .meta, .instance-note, .timeline-labels {
      color: var(--muted);
      font-size: 13px;
    }

    .banner-actions {
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
      justify-content: flex-end;
    }

    .button, .ghost-button {
      min-height: 38px;
      border-radius: 999px;
      padding: 0 14px;
      border: 1px solid var(--border);
      color: var(--text);
      background: var(--panel-soft);
      cursor: pointer;
      transition: transform 150ms ease, border-color 150ms ease, background 150ms ease;
      font-size: 14px;
    }

    .button:hover, .ghost-button:hover { transform: translateY(-1px); }

    .button.primary {
      border-color: rgba(240, 138, 93, 0.3);
      background: linear-gradient(135deg, rgba(240, 138, 93, 0.22), rgba(240, 138, 93, 0.08));
    }

    .ghost-button.danger {
      border-color: rgba(255,107,107,0.28);
      color: #ffd7d7;
      background: linear-gradient(135deg, rgba(255,107,107,0.18), rgba(255,107,107,0.05));
    }

    .ghost-button.danger:hover {
      border-color: rgba(255,107,107,0.42);
      background: linear-gradient(135deg, rgba(255,107,107,0.24), rgba(255,107,107,0.08));
    }

    .stack {
      display: grid;
      gap: 12px;
    }

    .group {
      padding: 6px 0 0;
    }

    .group-title {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 0 14px 10px;
      color: #d9e5df;
      font-size: 15px;
      font-weight: 700;
    }

    .group-summary {
      color: var(--muted);
      font-size: 12px;
      font-weight: 500;
    }

    .instance {
      padding: 14px;
      border-top: 1px solid rgba(255,255,255,0.04);
    }

    .instance-head {
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 18px;
      margin-bottom: 10px;
    }

    .instance-main {
      display: flex;
      align-items: center;
      gap: 10px;
      min-width: 0;
    }

    .instance-name {
      color: var(--text);
      text-decoration: none;
      font-size: 14px;
      font-weight: 600;
      word-break: break-word;
    }

    .instance-name:hover { color: white; }

    .instance-meta {
      display: flex;
      gap: 12px;
      flex-wrap: nowrap;
      align-items: center;
      justify-content: flex-end;
      text-align: right;
      min-width: 0;
    }

    .uptime {
      font-size: 13px;
      color: #d7e6dd;
    }

    .status-chip {
      padding: 4px 9px;
      border-radius: 999px;
      font-size: 11px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      border: 1px solid transparent;
    }

    .status-chip.operational { color: #d7ffe4; background: rgba(54,194,109,0.12); border-color: rgba(54,194,109,0.22); }
    .status-chip.degraded { color: #fff0c0; background: rgba(227,179,65,0.12); border-color: rgba(227,179,65,0.22); }
    .status-chip.outage { color: #ffd4d4; background: rgba(255,107,107,0.12); border-color: rgba(255,107,107,0.22); }
    .status-chip.unknown { color: #cad6d9; background: rgba(58,71,75,0.22); border-color: rgba(58,71,75,0.35); }

    .instance-note {
      margin-bottom: 10px;
      line-height: 1.4;
      min-height: 18px;
    }

    .probe-statuses {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin-bottom: 10px;
    }

    .probe-pill {
      display: inline-flex;
      align-items: center;
      gap: 7px;
      padding: 4px 9px;
      border-radius: 999px;
      border: 1px solid rgba(255,255,255,0.06);
      background: rgba(255,255,255,0.03);
      color: #d7e4de;
      font-size: 12px;
      line-height: 1;
    }

    .probe-pill-dot {
      width: 8px;
      height: 8px;
      border-radius: 999px;
      background: var(--unknown);
      flex: none;
    }

    .probe-pill.ok .probe-pill-dot { background: var(--ok); }
    .probe-pill.bad .probe-pill-dot { background: var(--bad); }

    .timeline {
      display: grid;
      grid-template-columns: repeat(var(--timeline-columns, 96), minmax(0, 1fr));
      gap: 2px;
      margin-bottom: 6px;
    }

    .bar {
      height: 25px;
      border-radius: 6px;
      background: var(--unknown);
    }

    .bar.operational { background: var(--ok); }
    .bar.degraded { background: var(--warn); }
    .bar.outage { background: var(--bad); }
    .bar.unknown { background: var(--unknown); }

    .timeline-labels {
      display: flex;
      justify-content: space-between;
    }

    .footer {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      margin-top: 12px;
      color: var(--muted);
      font-size: 12px;
      padding: 0 2px;
      flex-wrap: wrap;
    }

    .legend {
      display: flex;
      flex-wrap: wrap;
      gap: 14px;
      align-items: center;
    }

    .legend-item {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.4;
    }

    .legend-item .dot {
      width: 10px;
      height: 10px;
      box-shadow: none;
    }

    .link {
      color: #f6b08f;
      text-decoration: none;
    }

    .link:hover { color: #ffd7c5; }

    .empty {
      padding: 16px;
      text-align: center;
      color: var(--muted);
    }

    .modal {
      position: fixed;
      inset: 0;
      display: none;
      align-items: center;
      justify-content: center;
      padding: 20px;
      background: rgba(8, 11, 12, 0.72);
      backdrop-filter: blur(6px);
      z-index: 20;
    }

    .modal.open { display: flex; }

    .modal-panel {
      width: min(1180px, 100%);
      max-height: min(92vh, 920px);
      overflow: auto;
      padding: 18px;
    }

    .modal-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 14px;
    }

    .modal-title {
      font-size: 20px;
      font-weight: 700;
    }

    .manager-grid {
      display: grid;
      grid-template-columns: minmax(320px, 420px) minmax(0, 1fr);
      gap: 18px;
    }

    .auth-panel {
      width: min(420px, 100%);
    }

    .manager-card {
      border: 1px solid rgba(255,255,255,0.05);
      border-radius: 12px;
      background: var(--panel-soft);
      padding: 14px;
    }

    .field {
      display: grid;
      gap: 8px;
      margin-bottom: 12px;
    }

    .field label {
      font-size: 13px;
      color: #d7e4de;
    }

    input[type="url"], input[type="password"], input[type="email"] {
      width: 100%;
      min-height: 44px;
      border-radius: 10px;
      border: 1px solid var(--border);
      background: #111718;
      color: var(--text);
      padding: 0 12px;
      outline: none;
    }

    input[type="url"]:focus, input[type="password"]:focus, input[type="email"]:focus {
      border-color: rgba(240, 138, 93, 0.35);
      box-shadow: 0 0 0 4px rgba(240, 138, 93, 0.12);
    }

    .manager-actions, .manager-toolbar, .instance-actions {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }

    .manager-status {
      min-height: 18px;
      margin-top: 10px;
      font-size: 13px;
      color: #d7e6dd;
    }

    .manager-status.error { color: #ffd4d4; }
    .manager-status.success { color: #d4ffe1; }

    .toast-stack {
      position: fixed;
      right: 18px;
      bottom: 18px;
      display: grid;
      gap: 10px;
      z-index: 40;
      pointer-events: none;
      width: min(360px, calc(100vw - 24px));
    }

    .toast {
      border-radius: 12px;
      border: 1px solid rgba(255,255,255,0.08);
      background: rgba(19, 26, 27, 0.96);
      box-shadow: 0 14px 32px rgba(0, 0, 0, 0.28);
      padding: 12px 14px;
      color: var(--text);
      transform: translateY(8px);
      opacity: 0;
      animation: toast-in 180ms ease forwards;
    }

    .toast.success {
      border-color: rgba(54,194,109,0.28);
      background: linear-gradient(135deg, rgba(54,194,109,0.18), rgba(19, 26, 27, 0.96));
    }

    .toast.error {
      border-color: rgba(255,107,107,0.28);
      background: linear-gradient(135deg, rgba(255,107,107,0.16), rgba(19, 26, 27, 0.96));
    }

    .toast.info {
      border-color: rgba(240,138,93,0.28);
      background: linear-gradient(135deg, rgba(240,138,93,0.16), rgba(19, 26, 27, 0.96));
    }

    .toast-title {
      font-size: 13px;
      font-weight: 700;
      margin-bottom: 4px;
      color: #f3f8f4;
    }

    .toast-message {
      font-size: 13px;
      line-height: 1.4;
      color: #d9e6e0;
    }

    @keyframes toast-in {
      from {
        opacity: 0;
        transform: translateY(8px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }

    .checkbox-row {
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 14px;
      color: #d7e4de;
      font-size: 13px;
    }

    .checkbox-row input[type="checkbox"] {
      width: 16px;
      height: 16px;
      accent-color: var(--accent);
    }

    .managed-list {
      display: grid;
      gap: 10px;
    }

    .managed-item {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 12px;
      padding: 12px;
      border-radius: 10px;
      background: rgba(255,255,255,0.03);
      border: 1px solid rgba(255,255,255,0.04);
    }

    .managed-copy {
      min-width: 0;
      display: grid;
      gap: 6px;
    }

    .managed-meta {
      color: var(--muted);
      font-size: 12px;
    }

    .icon-button {
      min-width: 36px;
      width: 36px;
      height: 36px;
      min-height: 36px;
      padding: 0;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      font-size: 14px;
      line-height: 1;
      border-radius: 999px;
      color: #aab7b2;
      background: rgba(255,255,255,0.03);
      border-color: rgba(255,255,255,0.06);
      box-shadow: none;
      flex: none;
      margin-left: auto;
    }

    .icon-button:hover {
      color: #d7e4de;
      background: rgba(255,255,255,0.06);
      border-color: rgba(255,255,255,0.12);
    }

    .subscribe-endpoint {
      color: #dfeae4;
      font-size: 14px;
      line-height: 1.5;
      word-break: break-word;
      margin-bottom: 12px;
    }

    .subscriptions-list {
      display: grid;
      gap: 10px;
    }

    .subscription-item {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 14px;
      padding: 12px;
      border-radius: 10px;
      background: rgba(255,255,255,0.03);
      border: 1px solid rgba(255,255,255,0.04);
    }

    .subscription-copy {
      min-width: 0;
      display: grid;
      gap: 6px;
    }

    .subscription-email {
      color: #f3f8f4;
      font-size: 14px;
      font-weight: 700;
      word-break: break-word;
    }

    @media (max-width: 860px) {
      .banner, .instance-head, .managed-item, .subscription-item, .modal-head {
        flex-direction: column;
        align-items: flex-start;
      }

      .banner-actions, .instance-meta {
        justify-content: flex-start;
        text-align: left;
      }

      .manager-grid {
        grid-template-columns: 1fr;
      }

      .timeline {
        height: auto;
      }
    }
  </style>
</head>
<body>
  <main class="shell">
    <section class="banner">
      <div class="banner-main">
        <span class="dot operational" id="summary-dot"></span>
        <div>
          <div class="banner-title" id="summary-title">Loading status...</div>
          <div class="banner-subtitle" id="summary-subtitle">Pulling the latest monitor history.</div>
        </div>
      </div>
      <div class="banner-actions">
        <div class="small">Last updated: <strong id="last-updated">n/a</strong> · updates every <strong id="refresh-interval">5m</strong></div>
        <button class="button" id="subscriptions-button" type="button" hidden>Subscriptions</button>
        <button class="button primary" id="manage-button" type="button">Manage instances</button>
        <a class="ghost-button link" href="/status.json" target="_blank" rel="noreferrer" style="display:inline-flex;align-items:center;">status.json</a>
      </div>
    </section>

    <section class="card group">
      <div class="group-title">
        <span>Tidal Instances</span>
        <span class="group-summary" id="group-summary">Recent checks</span>
      </div>
      <div class="stack" id="status-list"></div>
    </section>

    <div class="footer">
      <span id="footer-stats">0 instances</span>
      <div class="legend">
        <span class="legend-item"><span class="dot operational"></span>Operational: track check works</span>
        <span class="legend-item"><span class="dot degraded"></span>Degraded: API works, but search or track fails</span>
        <span class="legend-item"><span class="dot outage"></span>Outage: base API is unreachable</span>
      </div>
    </div>
  </main>

    <div class="modal" id="manager-modal" aria-hidden="true">
      <div class="modal-panel">
        <div class="modal-head">
          <div>
            <div class="modal-title">Instance Manager</div>
            <div class="small">Add, edit or delete monitored endpoints. Changes are saved and the affected API is rechecked.</div>
          </div>
          <div class="instance-actions">
            <button class="ghost-button danger" id="logout-button" style="margin-right: 20px;" type="button">Logout</button>
            <button class="ghost-button" id="close-modal" type="button">Close</button>
          </div>
        </div>

      <div class="manager-grid">
        <section class="manager-card">
          <div style="font-weight:700; margin-bottom:12px;" id="form-title">Add instance</div>
          <form id="instance-form">
            <div class="field">
              <label for="instance-url">Endpoint URL</label>
              <input id="instance-url" name="url" type="url" placeholder="https://example.com" required>
            </div>
            <label class="checkbox-row" for="alerts-enabled">
              <input id="alerts-enabled" name="alertsEnabled" type="checkbox" checked>
              <span>Enable Discord alerts for this instance (send alerts to the configured Discord webhook)</span>
            </label>
            <label class="checkbox-row" for="alert-on-outage">
              <input id="alert-on-outage" name="alertOnOutage" type="checkbox" checked>
              <span>Send Outage alerts (base API does not work)</span>
            </label>
            <label class="checkbox-row" for="alert-on-search">
              <input id="alert-on-search" name="alertOnSearch" type="checkbox" checked>
              <span>Send Search alerts (search check fails)</span>
            </label>
            <label class="checkbox-row" for="alert-on-track">
              <input id="alert-on-track" name="alertOnTrack" type="checkbox" checked>
              <span>Send Track alerts (track check fails)</span>
            </label>
            <label class="checkbox-row" for="alert-on-recovery">
              <input id="alert-on-recovery" name="alertOnRecovery" type="checkbox" checked>
              <span>Send Recovery notifications</span>
            </label>
            <div class="manager-actions">
              <button class="button primary" id="submit-button" type="submit">Add instance</button>
              <button class="ghost-button" id="cancel-button" type="button" hidden>Cancel</button>
            </div>
          </form>
          <div class="manager-status" id="manager-status"></div>
        </section>

        <section class="manager-card">
          <div style="display:flex; align-items:center; justify-content:space-between; gap:10px; margin-bottom:12px;">
            <div style="font-weight:700;">Managed instances</div>
            <span class="small" id="instance-count-label">0 items</span>
          </div>
          <div class="managed-list" id="instance-list"></div>
        </section>
      </div>
      </div>
    </div>

    <div class="modal" id="auth-modal" aria-hidden="true">
      <div class="modal-panel auth-panel">
        <div class="modal-head">
          <div>
            <div class="modal-title">Manage instances</div>
            <div class="small">Enter the admin password to access the instance manager.</div>
          </div>
          <button class="ghost-button" id="close-auth-modal" type="button">Close</button>
        </div>
        <form id="auth-form">
          <div class="field">
            <label for="auth-password">Password</label>
            <input id="auth-password" name="password" type="password" autocomplete="current-password" required>
          </div>
          <div class="manager-actions">
            <button class="button primary" id="auth-submit" type="submit">Unlock</button>
          </div>
        </form>
        <div class="manager-status" id="auth-status"></div>
      </div>
    </div>

    <div class="modal" id="subscribe-modal" aria-hidden="true">
      <div class="modal-panel auth-panel">
        <div class="modal-head">
          <div>
            <div class="modal-title">Email alerts</div>
            <div class="small">Subscribe to alerts for a specific API endpoint.</div>
          </div>
          <button class="ghost-button" id="close-subscribe-modal" type="button">Close</button>
        </div>
        <div class="subscribe-endpoint" id="subscribe-endpoint-label"></div>
        <form id="subscribe-form">
          <div class="field">
            <label for="subscribe-email">Email</label>
            <input id="subscribe-email" name="email" type="email" placeholder="name@example.com" autocomplete="email" required>
          </div>
          <div class="manager-actions">
            <button class="button primary" id="subscribe-submit" type="submit">Subscribe</button>
          </div>
        </form>
        <div class="manager-status" id="subscribe-status"></div>
      </div>
    </div>

    <div class="modal" id="subscriptions-modal" aria-hidden="true">
      <div class="modal-panel" style="width:min(860px, 100%);">
        <div class="modal-head">
          <div>
            <div class="modal-title">Email subscriptions</div>
            <div class="small">All alert subscriptions currently stored in the monitor.</div>
          </div>
          <button class="ghost-button" id="close-subscriptions-modal" type="button">Close</button>
        </div>
        <div class="subscriptions-list" id="subscriptions-list"></div>
        <div class="manager-status" id="subscriptions-status"></div>
      </div>
    </div>

    <div class="toast-stack" id="toast-stack" aria-live="polite" aria-atomic="true"></div>

  <script>
    const pageEndpoint = "/api/status-page";
    const instancesEndpoint = "/api/instances";
    const subscriptionsEndpoint = "/api/subscriptions";
    const authStatusEndpoint = "/api/auth/status";
    const authLoginEndpoint = "/api/auth/login";
    const authLogoutEndpoint = "/api/auth/logout";
    const state = {
      editingId: null,
      authenticated: false,
      subscribeEndpointId: null,
      subscribeEndpointUrl: "",
      historyWindowPoints: 96,
      historyWindowHours: 8,
      checkIntervalSeconds: 300
    };

    const refreshMs = 30000;

    const refs = {
      summaryDot: document.getElementById("summary-dot"),
      summaryTitle: document.getElementById("summary-title"),
      summarySubtitle: document.getElementById("summary-subtitle"),
      lastUpdated: document.getElementById("last-updated"),
      refreshInterval: document.getElementById("refresh-interval"),
      groupSummary: document.getElementById("group-summary"),
      statusList: document.getElementById("status-list"),
      footerStats: document.getElementById("footer-stats"),
      subscriptionsButton: document.getElementById("subscriptions-button"),
      manageButton: document.getElementById("manage-button"),
      modal: document.getElementById("manager-modal"),
      closeModal: document.getElementById("close-modal"),
      logoutButton: document.getElementById("logout-button"),
      form: document.getElementById("instance-form"),
      formTitle: document.getElementById("form-title"),
      urlInput: document.getElementById("instance-url"),
      alertsEnabledInput: document.getElementById("alerts-enabled"),
      alertOnOutageInput: document.getElementById("alert-on-outage"),
      alertOnSearchInput: document.getElementById("alert-on-search"),
      alertOnTrackInput: document.getElementById("alert-on-track"),
      alertOnRecoveryInput: document.getElementById("alert-on-recovery"),
      submitButton: document.getElementById("submit-button"),
      cancelButton: document.getElementById("cancel-button"),
      managerStatus: document.getElementById("manager-status"),
      instanceList: document.getElementById("instance-list"),
      instanceCountLabel: document.getElementById("instance-count-label"),
      authModal: document.getElementById("auth-modal"),
      closeAuthModal: document.getElementById("close-auth-modal"),
      authForm: document.getElementById("auth-form"),
      authPassword: document.getElementById("auth-password"),
      authSubmit: document.getElementById("auth-submit"),
      authStatus: document.getElementById("auth-status"),
      subscribeModal: document.getElementById("subscribe-modal"),
      closeSubscribeModal: document.getElementById("close-subscribe-modal"),
      subscribeForm: document.getElementById("subscribe-form"),
      subscribeEndpointLabel: document.getElementById("subscribe-endpoint-label"),
      subscribeEmail: document.getElementById("subscribe-email"),
      subscribeSubmit: document.getElementById("subscribe-submit"),
      subscribeStatus: document.getElementById("subscribe-status"),
      subscriptionsModal: document.getElementById("subscriptions-modal"),
      closeSubscriptionsModal: document.getElementById("close-subscriptions-modal"),
      subscriptionsList: document.getElementById("subscriptions-list"),
      subscriptionsStatus: document.getElementById("subscriptions-status"),
      toastStack: document.getElementById("toast-stack")
    };

    function escapeHtml(value) {
      return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
    }

    function formatTime(value) {
      if (!value) return "n/a";
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) return escapeHtml(value);
      return date.toLocaleString(undefined, {
        year: "numeric",
        month: "short",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        timeZoneName: "short"
      });
    }

    function stateLabel(stateValue) {
      return {
        operational: "Operational",
        degraded: "Degraded",
        outage: "Outage",
        unknown: "Unknown"
      }[stateValue] || "Unknown";
    }

    function formatIntervalLabel(seconds) {
      const value = Number(seconds) || 0;
      if (value <= 0) return "n/a";
      if (value % 3600 === 0) return `${value / 3600}h`;
      if (value % 60 === 0) return `${value / 60}m`;
      return `${value}s`;
    }

    function normalizeHistoryEntry(entry) {
      if (entry && typeof entry === "object") {
        return {
          state: entry.state || "unknown",
          lastUpdated: entry.lastUpdated || null,
          statusCode: entry.statusCode ?? null,
          error: entry.error || null
        };
      }

      return {
        state: typeof entry === "string" ? entry : "unknown",
        lastUpdated: null,
        statusCode: null,
        error: null
      };
    }

    function historyBarTitle(entry) {
      const lines = [stateLabel(entry.state)];

      if (entry.lastUpdated) {
        lines.push(`Time: ${formatTime(entry.lastUpdated)}`);
      }

      if (entry.state === "degraded" || entry.state === "outage") {
        lines.push(`Reason: ${historyReasonLabel(entry)}`);
      }

      return lines.join("\\n");
    }

    function historyReasonLabel(entry) {
      if (entry.error) {
        const statusSuffix = entry.statusCode ? ` (${entry.statusCode})` : "";
        return `${entry.error}${statusSuffix}`;
      }

      if (entry.state === "outage") {
        return "Endpoint was unreachable during this check";
      }

      if (entry.state === "degraded") {
        return "Base API responded, but one of the feature checks failed";
      }

      return "No additional details";
    }

    function setManagerStatus(message, kind = "") {
      refs.managerStatus.textContent = message;
      refs.managerStatus.className = `manager-status ${kind}`.trim();
    }

    function setAuthStatus(message, kind = "") {
      refs.authStatus.textContent = message;
      refs.authStatus.className = `manager-status ${kind}`.trim();
    }

    function setSubscribeStatus(message, kind = "") {
      refs.subscribeStatus.textContent = message;
      refs.subscribeStatus.className = `manager-status ${kind}`.trim();
    }

    function setSubscriptionsStatus(message, kind = "") {
      refs.subscriptionsStatus.textContent = message;
      refs.subscriptionsStatus.className = `manager-status ${kind}`.trim();
    }

    function showToast(message, kind = "info", title = "") {
      if (!message) return;

      const toast = document.createElement("div");
      toast.className = `toast ${kind}`.trim();
      const resolvedTitle =
        title || (kind === "success" ? "Success" : kind === "error" ? "Error" : "Notice");

      toast.innerHTML = `
        <div class="toast-title">${escapeHtml(resolvedTitle)}</div>
        <div class="toast-message">${escapeHtml(message)}</div>
      `;
      refs.toastStack.appendChild(toast);

      window.setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transform = "translateY(8px)";
        toast.style.transition = "opacity 180ms ease, transform 180ms ease";
        window.setTimeout(() => toast.remove(), 220);
      }, 2600);
    }

    function updateManageButton() {
      refs.manageButton.textContent = state.authenticated ? "Manage instances" : "Login";
      refs.subscriptionsButton.hidden = !state.authenticated;
    }

    function resetForm() {
      state.editingId = null;
      refs.form.reset();
      refs.formTitle.textContent = "Add instance";
      refs.submitButton.textContent = "Add instance";
      refs.alertsEnabledInput.checked = true;
      refs.alertOnOutageInput.checked = true;
      refs.alertOnSearchInput.checked = true;
      refs.alertOnTrackInput.checked = true;
      refs.alertOnRecoveryInput.checked = true;
      refs.cancelButton.hidden = true;
    }

    function openModal() {
      refs.modal.classList.add("open");
      refs.modal.setAttribute("aria-hidden", "false");
    }

    function closeModal() {
      refs.modal.classList.remove("open");
      refs.modal.setAttribute("aria-hidden", "true");
      resetForm();
      setManagerStatus("");
    }

    function openAuthModal() {
      refs.authModal.classList.add("open");
      refs.authModal.setAttribute("aria-hidden", "false");
      refs.authPassword.focus();
    }

    function closeAuthModal() {
      refs.authModal.classList.remove("open");
      refs.authModal.setAttribute("aria-hidden", "true");
      refs.authForm.reset();
      setAuthStatus("");
    }

    function openSubscribeModal(endpointId, endpointUrl) {
      state.subscribeEndpointId = endpointId;
      state.subscribeEndpointUrl = endpointUrl;
      refs.subscribeEndpointLabel.textContent = endpointUrl;
      refs.subscribeModal.classList.add("open");
      refs.subscribeModal.setAttribute("aria-hidden", "false");
      refs.subscribeEmail.focus();
    }

    function closeSubscribeModal() {
      refs.subscribeModal.classList.remove("open");
      refs.subscribeModal.setAttribute("aria-hidden", "true");
      refs.subscribeForm.reset();
      state.subscribeEndpointId = null;
      state.subscribeEndpointUrl = "";
      setSubscribeStatus("");
    }

    function openSubscriptionsModal() {
      refs.subscriptionsModal.classList.add("open");
      refs.subscriptionsModal.setAttribute("aria-hidden", "false");
    }

    function closeSubscriptionsModal() {
      refs.subscriptionsModal.classList.remove("open");
      refs.subscriptionsModal.setAttribute("aria-hidden", "true");
      setSubscriptionsStatus("");
    }

    function buildHistoryBars(history) {
      const values = Array.isArray(history) ? history.map(normalizeHistoryEntry) : [];
      const historyPoints = Math.max(Number(state.historyWindowPoints) || 1, 1);
      const normalized = values.length >= historyPoints
        ? values.slice(values.length - historyPoints)
        : [...Array(historyPoints - values.length).fill(null).map(() => normalizeHistoryEntry(null)), ...values];
      return normalized.map((item) => (
        `<span class="bar ${escapeHtml(item.state)}" title="${escapeHtml(historyBarTitle(item))}"></span>`
      )).join("");
    }

    function renderInstance(item) {
      const version = item.version ? `v${item.version}` : "no version";
      const uptimeText = item.uptimePercentage === null || item.uptimePercentage === undefined
        ? "n/a"
        : `${item.uptimePercentage.toFixed(3)}%`;
      const baseNote = item.error
        ? `${item.error}${item.statusCode ? ` (${item.statusCode})` : ""}`
        : item.trackOk
          ? "Track delivery healthy."
          : item.apiOk
            ? "Base API reachable."
            : "No successful data yet.";
      let note = baseNote;
      if (item.state === "degraded") {
        const degradedParts = [baseNote];
        if (!item.trackOk) {
          degradedParts.push("Track: problem.");
        }
        degradedParts.push(`Search: ${item.searchOk ? "responding." : "not responding."}`);
        note = degradedParts.join(" ");
      }
      const searchPill = `
        <span class="probe-pill ${item.searchOk ? "ok" : "bad"}">
          <span class="probe-pill-dot"></span>
          <span>Search</span>
        </span>
      `;
      const trackPill = `
        <span class="probe-pill ${item.trackOk ? "ok" : "bad"}">
          <span class="probe-pill-dot"></span>
          <span>Track</span>
        </span>
      `;
      return `
        <article class="instance">
          <div class="instance-head">
            <div class="instance-main">
              <span class="dot ${escapeHtml(item.state)}"></span>
              <a class="instance-name" href="${escapeHtml(item.url)}" target="_blank" rel="noreferrer">${escapeHtml(item.url)}</a>
              <span class="status-chip ${escapeHtml(item.state)}">${escapeHtml(stateLabel(item.state))}</span>
            </div>
            <div class="instance-meta">
              <span class="meta">${escapeHtml(version)}</span>
              <span class="uptime">Uptime: ${escapeHtml(uptimeText)}</span>
              <button class="ghost-button icon-button" type="button" data-action="subscribe" data-id="${item.id}" data-url="${escapeHtml(item.url)}" title="Subscribe by email">&#128276;</button>
            </div>
          </div>
          <div class="probe-statuses">${searchPill}${trackPill}</div>
          <div class="instance-note">${escapeHtml(note)}</div>
          <div class="timeline" style="--timeline-columns:${Number(state.historyWindowPoints) || 96}">${buildHistoryBars(item.history)}</div>
          <div class="timeline-labels">
            <span>Older</span>
            <span>Newest</span>
          </div>
        </article>
      `;
    }

    function updateStatusPage(payload) {
      const summary = payload.summary || {};
      const instances = Array.isArray(payload.instances) ? payload.instances : [];
      const historyPoints = payload.historyPoints || 0;
      state.historyWindowPoints = payload.historyWindowPoints || state.historyWindowPoints;
      state.historyWindowHours = payload.historyWindowHours || state.historyWindowHours;
      state.checkIntervalSeconds = payload.checkIntervalSeconds || state.checkIntervalSeconds;

      refs.summaryDot.className = `dot ${summary.state || "unknown"}`;
      refs.summaryTitle.textContent =
        summary.state === "operational" ? "All systems operational" :
        summary.state === "outage" ? "Major outage detected" :
        "Some systems are degraded";
      refs.summarySubtitle.textContent =
        `${summary.streamingCount || 0}/${summary.totalInstances || 0} instances currently serving tracks, ${summary.downCount || 0} degraded.`;
      refs.lastUpdated.textContent = formatTime(payload.lastUpdated);
      refs.refreshInterval.textContent = formatIntervalLabel(state.checkIntervalSeconds);
      refs.groupSummary.textContent =
        `${historyPoints} checks over ~${state.historyWindowHours}h · every ${formatIntervalLabel(state.checkIntervalSeconds)}`;
      refs.footerStats.textContent = `${summary.totalInstances || 0} instances · ${summary.apiCount || 0} API alive · ${summary.streamingCount || 0} streaming`;

      if (instances.length === 0) {
        refs.statusList.innerHTML = '<div class="empty">No instances configured.</div>';
        return;
      }

      refs.statusList.innerHTML = instances.map(renderInstance).join("");
    }

    function renderManagedInstances(items) {
      refs.instanceCountLabel.textContent = `${items.length} items`;
      if (!Array.isArray(items) || items.length === 0) {
        refs.instanceList.innerHTML = '<div class="empty">No instances configured.</div>';
        return;
      }

      function alertLevelsText(item) {
        const parts = [];
        if (item.alert_on_outage) parts.push("outage");
        if (item.alert_on_search) parts.push("search");
        if (item.alert_on_track) parts.push("track");
        if (item.alert_on_recovery) parts.push("recovery");
        return parts.length ? parts.join(", ") : "none";
      }

      refs.instanceList.innerHTML = items.map((item) => `
        <article class="managed-item">
          <div class="managed-copy">
            <a class="instance-name" href="${escapeHtml(item.url)}" target="_blank" rel="noreferrer">${escapeHtml(item.url)}</a>
            <div class="managed-meta">Updated ${escapeHtml(formatTime(item.updated_at))}</div>
            <div class="managed-meta">Alerts: ${item.alerts_enabled ? "enabled" : "disabled"}</div>
            <div class="managed-meta">Levels: ${escapeHtml(alertLevelsText(item))}</div>
          </div>
          <div class="instance-actions">
            <button class="ghost-button" type="button" data-action="toggle-alerts" data-id="${item.id}" data-url="${escapeHtml(item.url)}" data-alerts-enabled="${item.alerts_enabled ? "true" : "false"}">${item.alerts_enabled ? "Disable alerts" : "Enable alerts"}</button>
            <button class="ghost-button" type="button" data-action="edit" data-id="${item.id}" data-url="${escapeHtml(item.url)}" data-alerts-enabled="${item.alerts_enabled ? "true" : "false"}" data-alert-on-outage="${item.alert_on_outage ? "true" : "false"}" data-alert-on-search="${item.alert_on_search ? "true" : "false"}" data-alert-on-track="${item.alert_on_track ? "true" : "false"}" data-alert-on-recovery="${item.alert_on_recovery ? "true" : "false"}">Edit</button>
            <button class="ghost-button" type="button" data-action="delete" data-id="${item.id}" data-url="${escapeHtml(item.url)}">Delete</button>
          </div>
        </article>
      `).join("");
    }

    function renderSubscriptions(items) {
      if (!Array.isArray(items) || items.length === 0) {
        refs.subscriptionsList.innerHTML = '<div class="empty">No subscriptions yet.</div>';
        return;
      }

      refs.subscriptionsList.innerHTML = items.map((item) => `
        <article class="subscription-item">
          <div class="subscription-copy">
            <div class="subscription-email">${escapeHtml(item.email)}</div>
            <a class="instance-name" href="${escapeHtml(item.endpoint_url)}" target="_blank" rel="noreferrer">${escapeHtml(item.endpoint_url)}</a>
            <div class="managed-meta">Added ${escapeHtml(formatTime(item.created_at))}</div>
          </div>
          <div class="instance-actions">
            <button class="ghost-button" type="button" data-action="delete-subscription" data-id="${item.id}" data-email="${escapeHtml(item.email)}" data-url="${escapeHtml(item.endpoint_url)}">Delete</button>
          </div>
        </article>
      `).join("");
    }

    async function fetchJson(url, options = {}) {
      const response = await fetch(url, {
        headers: { "Content-Type": "application/json", ...(options.headers || {}) },
        ...options
      });

      if (response.status === 204) return null;

      const contentType = response.headers.get("content-type") || "";
      const payload = contentType.includes("application/json") ? await response.json() : null;

      if (!response.ok) {
        const detail = payload && typeof payload.detail === "string" ? payload.detail : `HTTP ${response.status}`;
        throw new Error(detail);
      }

      return payload;
    }

    async function loadStatusPage() {
      const payload = await fetchJson(pageEndpoint, { cache: "no-store" });
      updateStatusPage(payload);
      return payload;
    }

    async function loadInstances() {
      const payload = await fetchJson(instancesEndpoint, { cache: "no-store" });
      renderManagedInstances(payload.items || []);
    }

    async function loadSubscriptions() {
      const payload = await fetchJson(subscriptionsEndpoint, { cache: "no-store" });
      renderSubscriptions(payload.items || []);
    }

    async function reloadAll() {
      try {
        return await loadStatusPage();
      } catch (error) {
        refs.summaryDot.className = "dot outage";
        refs.summaryTitle.textContent = "Dashboard unavailable";
        refs.summarySubtitle.textContent = error.message;
        return null;
      }
    }

    async function refreshAuthStatus() {
      try {
        const payload = await fetchJson(authStatusEndpoint, { cache: "no-store" });
        state.authenticated = Boolean(payload.authenticated);
      } catch {
        state.authenticated = false;
      }
      if (!state.authenticated && refs.subscriptionsModal.classList.contains("open")) {
        closeSubscriptionsModal();
      }
      updateManageButton();
    }

    async function openManagerIfAuthenticated() {
      await refreshAuthStatus();
      if (!state.authenticated) {
        openAuthModal();
        return;
      }

      openModal();
      try {
        await loadInstances();
      } catch (error) {
        if (error.message === "Authentication required") {
          state.authenticated = false;
          updateManageButton();
          closeModal();
          openAuthModal();
          return;
        }
        setManagerStatus(error.message, "error");
      }
    }

    async function openSubscriptionsIfAuthenticated() {
      await refreshAuthStatus();
      if (!state.authenticated) {
        openAuthModal();
        return;
      }

      openSubscriptionsModal();
      try {
        await loadSubscriptions();
      } catch (error) {
        if (error.message === "Authentication required") {
          state.authenticated = false;
          updateManageButton();
          closeSubscriptionsModal();
          openAuthModal();
          return;
        }
        setSubscriptionsStatus(error.message, "error");
      }
    }

    refs.manageButton.addEventListener("click", async () => {
      await openManagerIfAuthenticated();
    });

    refs.subscriptionsButton.addEventListener("click", async () => {
      await openSubscriptionsIfAuthenticated();
    });

    refs.closeModal.addEventListener("click", closeModal);
    refs.modal.addEventListener("click", (event) => {
      if (event.target === refs.modal) {
        closeModal();
      }
    });
    refs.closeAuthModal.addEventListener("click", closeAuthModal);
    refs.authModal.addEventListener("click", (event) => {
      if (event.target === refs.authModal) {
        closeAuthModal();
      }
    });
    refs.closeSubscribeModal.addEventListener("click", closeSubscribeModal);
    refs.subscribeModal.addEventListener("click", (event) => {
      if (event.target === refs.subscribeModal) {
        closeSubscribeModal();
      }
    });
    refs.closeSubscriptionsModal.addEventListener("click", closeSubscriptionsModal);
    refs.subscriptionsModal.addEventListener("click", (event) => {
      if (event.target === refs.subscriptionsModal) {
        closeSubscriptionsModal();
      }
    });

    window.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && refs.modal.classList.contains("open")) {
        closeModal();
      }
      if (event.key === "Escape" && refs.authModal.classList.contains("open")) {
        closeAuthModal();
      }
      if (event.key === "Escape" && refs.subscribeModal.classList.contains("open")) {
        closeSubscribeModal();
      }
      if (event.key === "Escape" && refs.subscriptionsModal.classList.contains("open")) {
        closeSubscriptionsModal();
      }
    });

    refs.authForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const password = refs.authPassword.value;
      if (!password) return;

      refs.authSubmit.disabled = true;
      setAuthStatus("Checking password...");
      try {
        await fetchJson(authLoginEndpoint, {
          method: "POST",
          body: JSON.stringify({ password })
        });
        state.authenticated = true;
        updateManageButton();
        closeAuthModal();
        showToast("You are now signed in.", "success", "Login");
        await openManagerIfAuthenticated();
      } catch (error) {
        setAuthStatus(error.message, "error");
        showToast(error.message, "error", "Login failed");
      } finally {
        refs.authSubmit.disabled = false;
      }
    });

    refs.subscribeForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const email = refs.subscribeEmail.value.trim();
      if (!email || !state.subscribeEndpointId) return;

      refs.subscribeSubmit.disabled = true;
      setSubscribeStatus("Saving subscription...");
      try {
        await fetchJson(`${instancesEndpoint}/${state.subscribeEndpointId}/subscriptions`, {
          method: "POST",
          body: JSON.stringify({ email })
        });
        setSubscribeStatus("Subscription created.", "success");
        showToast("Email subscription created.", "success", "Subscribed");
        closeSubscribeModal();
        if (state.authenticated && refs.subscriptionsModal.classList.contains("open")) {
          await loadSubscriptions();
        }
      } catch (error) {
        setSubscribeStatus(error.message, "error");
        showToast(error.message, "error", "Subscription failed");
      } finally {
        refs.subscribeSubmit.disabled = false;
      }
    });

    refs.logoutButton.addEventListener("click", async () => {
      refs.logoutButton.disabled = true;
      try {
        await fetchJson(authLogoutEndpoint, { method: "POST" });
        state.authenticated = false;
        updateManageButton();
        closeModal();
        closeSubscriptionsModal();
        showToast("You have been signed out.", "success", "Logout");
      } finally {
        refs.logoutButton.disabled = false;
      }
    });

    refs.form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const url = refs.urlInput.value.trim();
      const alertsEnabled = refs.alertsEnabledInput.checked;
      const alertOnOutage = refs.alertOnOutageInput.checked;
      const alertOnSearch = refs.alertOnSearchInput.checked;
      const alertOnTrack = refs.alertOnTrackInput.checked;
      const alertOnRecovery = refs.alertOnRecoveryInput.checked;
      if (!url) return;
      const isEditing = state.editingId !== null;

      refs.submitButton.disabled = true;
      refs.cancelButton.disabled = true;
      setManagerStatus(isEditing ? "Saving changes..." : "Adding instance...");

      try {
        await fetchJson(isEditing ? `${instancesEndpoint}/${state.editingId}` : instancesEndpoint, {
          method: isEditing ? "PUT" : "POST",
          body: JSON.stringify({
            url,
            alertsEnabled,
            alertOnOutage,
            alertOnSearch,
            alertOnTrack,
            alertOnRecovery
          })
        });
        resetForm();
        setManagerStatus(isEditing ? "Instance updated." : "Instance added.", "success");
        showToast(
          isEditing ? "Instance updated." : "Instance added.",
          "success",
          isEditing ? "Saved" : "Created"
        );
        await reloadAll();
        await loadInstances();
      } catch (error) {
        if (error.message === "Authentication required") {
          state.authenticated = false;
          updateManageButton();
          closeModal();
          openAuthModal();
          return;
        }
        setManagerStatus(error.message, "error");
        showToast(error.message, "error", "Save failed");
      } finally {
        refs.submitButton.disabled = false;
        refs.cancelButton.disabled = false;
      }
    });

    refs.cancelButton.addEventListener("click", () => {
      resetForm();
      setManagerStatus("");
    });

    refs.statusList.addEventListener("click", (event) => {
      const button = event.target.closest("button[data-action='subscribe']");
      if (!button) return;
      openSubscribeModal(Number(button.dataset.id), button.dataset.url || "");
    });

    refs.instanceList.addEventListener("click", async (event) => {
      const button = event.target.closest("button[data-action]");
      if (!button) return;

      const action = button.dataset.action;
      const id = Number(button.dataset.id);
      const url = button.dataset.url || "";
      const alertsEnabled = button.dataset.alertsEnabled === "true";
      const alertOnOutage = button.dataset.alertOnOutage === "true";
      const alertOnSearch = button.dataset.alertOnSearch === "true";
      const alertOnTrack = button.dataset.alertOnTrack === "true";
      const alertOnRecovery = button.dataset.alertOnRecovery === "true";

      if (action === "edit") {
        state.editingId = id;
        refs.urlInput.value = url;
        refs.alertsEnabledInput.checked = alertsEnabled;
        refs.alertOnOutageInput.checked = alertOnOutage;
        refs.alertOnSearchInput.checked = alertOnSearch;
        refs.alertOnTrackInput.checked = alertOnTrack;
        refs.alertOnRecoveryInput.checked = alertOnRecovery;
        refs.formTitle.textContent = "Edit instance";
        refs.submitButton.textContent = "Save changes";
        refs.cancelButton.hidden = false;
        refs.urlInput.focus();
        setManagerStatus(`Editing ${url}`);
        return;
      }

      if (action === "toggle-alerts") {
        const nextAlertsEnabled = !alertsEnabled;
        setManagerStatus(`${nextAlertsEnabled ? "Enabling" : "Disabling"} alerts for ${url}...`);
        try {
          await fetchJson(`${instancesEndpoint}/${id}/alerts`, {
            method: "PATCH",
            body: JSON.stringify({ alertsEnabled: nextAlertsEnabled })
          });
          if (state.editingId === id) {
            refs.alertsEnabledInput.checked = nextAlertsEnabled;
          }
          setManagerStatus(
            nextAlertsEnabled ? "Alerts enabled." : "Alerts disabled.",
            "success"
          );
          showToast(
            nextAlertsEnabled ? "Alerts enabled." : "Alerts disabled.",
            "success",
            "Instance alerts"
          );
          await loadInstances();
        } catch (error) {
          if (error.message === "Authentication required") {
            state.authenticated = false;
            updateManageButton();
            closeModal();
            openAuthModal();
            return;
          }
          setManagerStatus(error.message, "error");
          showToast(error.message, "error", "Alerts update failed");
        }
        return;
      }

      if (action === "delete") {
        if (!window.confirm(`Delete monitored instance?\\n\\n${url}`)) return;
        setManagerStatus(`Deleting ${url}...`);
        try {
          await fetchJson(`${instancesEndpoint}/${id}`, { method: "DELETE" });
          if (state.editingId === id) resetForm();
          setManagerStatus("Instance deleted.", "success");
          showToast("Instance deleted.", "success", "Deleted");
          await reloadAll();
          await loadInstances();
        } catch (error) {
          if (error.message === "Authentication required") {
            state.authenticated = false;
            updateManageButton();
            closeModal();
            openAuthModal();
            return;
          }
          setManagerStatus(error.message, "error");
          showToast(error.message, "error", "Delete failed");
        }
      }
    });

    refs.subscriptionsList.addEventListener("click", async (event) => {
      const button = event.target.closest("button[data-action='delete-subscription']");
      if (!button) return;

      const id = Number(button.dataset.id);
      const email = button.dataset.email || "";
      const url = button.dataset.url || "";
      if (!window.confirm(`Delete email subscription?\\n\\n${email}\\n${url}`)) return;

      setSubscriptionsStatus(`Deleting subscription for ${email}...`);
      try {
        await fetchJson(`${subscriptionsEndpoint}/${id}`, { method: "DELETE" });
        setSubscriptionsStatus("Subscription deleted.", "success");
        showToast("Subscription deleted.", "success", "Deleted");
        await loadSubscriptions();
      } catch (error) {
        if (error.message === "Authentication required") {
          state.authenticated = false;
          updateManageButton();
          closeSubscriptionsModal();
          openAuthModal();
          return;
        }
        setSubscriptionsStatus(error.message, "error");
        showToast(error.message, "error", "Delete failed");
      }
    });

    resetForm();
    updateManageButton();
    refreshAuthStatus();
    reloadAll().finally(() => {
      refs.refreshInterval.textContent = formatIntervalLabel(state.checkIntervalSeconds);
    });
    setInterval(loadStatusPage, refreshMs);
  </script>
</body>
</html>
"""
