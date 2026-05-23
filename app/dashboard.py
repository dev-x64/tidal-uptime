from __future__ import annotations

from pathlib import Path

STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_URL_PREFIX = "/static"


def _versioned(path: Path) -> str:
    try:
        version = int(path.stat().st_mtime)
    except OSError:
        version = 0
    return f"{STATIC_URL_PREFIX}/{path.name}?v={version}"


def _discover(prefix: str, suffix: str) -> list[Path]:
    """Return base file plus any sibling files matching `{prefix}.*.{suffix}` in alphabetical order.

    This lets future contributors drop e.g. `dashboard.theme.css` or
    `dashboard.extras.js` next to the base file and have them loaded
    automatically without editing this module.
    """
    if not STATIC_DIR.exists():
        return []
    base = STATIC_DIR / f"{prefix}.{suffix}"
    extras = sorted(p for p in STATIC_DIR.glob(f"{prefix}.*.{suffix}") if p.is_file())
    return ([base] if base.exists() else []) + extras


def _link_tags() -> str:
    return "\n  ".join(
        f'<link rel="stylesheet" href="{_versioned(p)}">' for p in _discover("dashboard", "css")
    )


def _script_tags() -> str:
    return "\n  ".join(
        f'<script defer src="{_versioned(p)}"></script>' for p in _discover("dashboard", "js")
    )


def _login_link_tags() -> str:
    return "\n  ".join(
        f'<link rel="stylesheet" href="{_versioned(p)}">' for p in _discover("login", "css")
    )


def _login_script_tags() -> str:
    return "\n  ".join(
        f'<script defer src="{_versioned(p)}"></script>' for p in _discover("login", "js")
    )


def render_login() -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Tidal Status — Sign in</title>
  {_login_link_tags()}
  {_login_script_tags()}
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
</body>
</html>"""


def render_dashboard() -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Tidal Status</title>
  {_link_tags()}
  {_script_tags()}
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

    <div class="view-tabs">
      <button class="view-tab active" id="view-overview" data-view="overview" type="button">Overview</button>
      <button class="view-tab" id="view-incidents" data-view="incidents" type="button">Incidents</button>
    </div>

    <section id="overview-view">
      <main id="groups-container"></main>
    </section>

    <section id="incidents-view" hidden>
      <section class="card incidents-summary">
        <div class="summary-stats">
          <div><b id="incidents-total">0</b><br><span>Total incidents</span></div>
          <div><b id="incidents-open">0</b><br><span>Open now</span></div>
          <div><b id="incidents-resolved">0</b><br><span>Resolved</span></div>
          <div><b id="incidents-mttr">—</b><br><span>Avg MTTR</span></div>
          <div><b id="incidents-mtbf">—</b><br><span>Avg MTBF</span></div>
        </div>
      </section>
      <section class="card incidents-list-card">
        <div class="group-head">
          <div class="group-title">By monitor</div>
        </div>
        <div id="incidents-instance-metrics"></div>
      </section>
      <section class="card incidents-list-card">
        <div class="group-head">
          <div class="group-title">Incident log</div>
        </div>
        <div id="incidents-list"></div>
      </section>
    </section>

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
              <label><input type="radio" name="kind" value="applemusic_wrapper"><span>Apple Music Wrapper</span></label>
            </div>
          </div>
          <div class="field">
            <label for="inst-group">Group</label>
            <select id="inst-group"></select>
          </div>
        </div>

        <div class="row cols-2">
          <div class="field">
            <label for="inst-check-interval">Check interval (seconds)</label>
            <input id="inst-check-interval" type="number" min="1" step="1" placeholder="default: global interval">
            <p class="help">Leave empty to use the global interval. Set to 1, 2, 3, … to check this monitor more often.</p>
          </div>
          <div></div>
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

  <!-- Info modal -->
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
</body>
</html>"""
