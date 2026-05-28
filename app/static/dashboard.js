const escapeHtml = (s) => String(s ?? "")
  .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
  .replace(/"/g, "&quot;").replace(/'/g, "&#39;");

const state = {
  groups: [],
  instances: [],
  incidentAnalytics: {
    rows: [],
    byInstance: new Map(),
    total: 0,
    open: 0,
    resolved: 0,
    mttrSeconds: null,
    mtbfSeconds: null,
  },
  activeView: "overview",
  checkIntervalSeconds: 60,
  historyWindowHours: 168,
  editingId: null,
  instanceFormMode: "create",
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
  viewOverview: document.getElementById("view-overview"),
  viewIncidents: document.getElementById("view-incidents"),
  overviewView: document.getElementById("overview-view"),
  incidentsView: document.getElementById("incidents-view"),
  incidentsTotal: document.getElementById("incidents-total"),
  incidentsOpen: document.getElementById("incidents-open"),
  incidentsResolved: document.getElementById("incidents-resolved"),
  incidentsMttr: document.getElementById("incidents-mttr"),
  incidentsMtbf: document.getElementById("incidents-mtbf"),
  incidentsInstanceMetrics: document.getElementById("incidents-instance-metrics"),
  incidentsList: document.getElementById("incidents-list"),
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
  instCheckInterval: document.getElementById("inst-check-interval"),
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
function formatHistoryWindowLabel(hours) {
  const value = Number(hours || 0);
  if (!value) return "uptime";
  if (value % 24 === 0) return `${value / 24}d uptime`;
  return `${value}h uptime`;
}
function findCurrentApiDownSince(history) {
  if (!Array.isArray(history) || history.length === 0) return null;
  let since = null;
  for (let i = history.length - 1; i >= 0; i -= 1) {
    const point = history[i] || {};
    if (point.state !== "outage") break;
    if (point.lastUpdated) since = point.lastUpdated;
  }
  return since;
}
function parseDate(value) {
  if (!value) return null;
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}
function durationSeconds(start, end) {
  if (!start || !end) return null;
  return Math.max(0, Math.round((end.getTime() - start.getTime()) / 1000));
}
function formatDuration(seconds) {
  if (seconds === null || seconds === undefined) return "—";
  const total = Math.max(0, Math.round(seconds));
  const days = Math.floor(total / 86400);
  const hours = Math.floor((total % 86400) / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const secs = total % 60;
  if (days > 0) return `${days}d ${hours}h`;
  if (hours > 0) return `${hours}h ${minutes}m`;
  if (minutes > 0) return `${minutes}m ${secs}s`;
  return `${secs}s`;
}
function average(nums) {
  if (!nums.length) return null;
  return nums.reduce((sum, value) => sum + value, 0) / nums.length;
}
function isIncidentState(stateValue) {
  return stateValue === "outage" || stateValue === "degraded";
}
function buildInstanceIncidentAnalytics(item) {
  const history = Array.isArray(item.history) ? item.history : [];
  const incidents = [];
  let active = null;
  let lastKnownAt = null;

  for (const point of history) {
    const stateValue = point && point.state ? point.state : "unknown";
    if (!["operational", "degraded", "outage"].includes(stateValue)) continue;
    const pointAt = parseDate(point.lastUpdated);
    if (!pointAt) continue;
    lastKnownAt = pointAt;

    if (isIncidentState(stateValue)) {
      if (!active) {
        active = {
          level: stateValue,
          startedAt: point.lastUpdated,
          _startedAtDate: pointAt,
          reason: point.error || null,
        };
      } else {
        if (stateValue === "outage") active.level = "outage";
        if (!active.reason && point.error) active.reason = point.error;
      }
      continue;
    }

    if (active) {
      incidents.push({
        level: active.level,
        startedAt: active.startedAt,
        resolvedAt: point.lastUpdated,
        durationSeconds: durationSeconds(active._startedAtDate, pointAt),
        reason: active.reason || "No reason captured",
        ongoing: false,
      });
      active = null;
    }
  }

  if (active) {
    const nowAt = lastKnownAt || active._startedAtDate;
    incidents.push({
      level: active.level,
      startedAt: active.startedAt,
      resolvedAt: null,
      durationSeconds: durationSeconds(active._startedAtDate, nowAt),
      reason: active.reason || item.error || "No reason captured",
      ongoing: true,
    });
  }

  const mttrSamples = incidents
    .filter((incident) => !incident.ongoing && incident.durationSeconds !== null)
    .map((incident) => incident.durationSeconds);
  const mtbfSamples = [];
  for (let i = 1; i < incidents.length; i += 1) {
    const prev = incidents[i - 1];
    const current = incidents[i];
    if (!prev.resolvedAt) continue;
    const prevResolvedAt = parseDate(prev.resolvedAt);
    const currentStartedAt = parseDate(current.startedAt);
    const gap = durationSeconds(prevResolvedAt, currentStartedAt);
    if (gap !== null) mtbfSamples.push(gap);
  }

  return {
    incidents,
    total: incidents.length,
    open: incidents.filter((incident) => incident.ongoing).length,
    resolved: incidents.filter((incident) => !incident.ongoing).length,
    mttrSeconds: average(mttrSamples),
    mtbfSeconds: average(mtbfSamples),
    mttrSamples,
    mtbfSamples,
  };
}
function buildIncidentAnalytics(instances) {
  const byInstance = new Map();
  const rows = [];
  let open = 0;
  let resolved = 0;
  const allMttrSamples = [];
  const allMtbfSamples = [];

  for (const item of instances) {
    const analytics = buildInstanceIncidentAnalytics(item);
    byInstance.set(item.id, analytics);
    open += analytics.open;
    resolved += analytics.resolved;
    allMttrSamples.push(...analytics.mttrSamples);
    allMtbfSamples.push(...analytics.mtbfSamples);

    for (const incident of analytics.incidents) {
      rows.push({
        instanceId: item.id,
        instanceUrl: item.url,
        instanceName: item.name || hostnameOf(item.url),
        ...incident,
      });
    }
  }

  rows.sort((a, b) => {
    const aTime = parseDate(a.startedAt);
    const bTime = parseDate(b.startedAt);
    if (!aTime && !bTime) return 0;
    if (!aTime) return 1;
    if (!bTime) return -1;
    return bTime.getTime() - aTime.getTime();
  });

  return {
    byInstance,
    rows,
    total: rows.length,
    open,
    resolved,
    mttrSeconds: average(allMttrSamples),
    mtbfSeconds: average(allMtbfSamples),
  };
}

function hostnameOf(url) {
  try { return new URL(url).hostname; } catch (_) { return url; }
}

function loadStatusPage() {
  return fetchJson("/api/status-page", { cache: "no-store" })
    .then((payload) => {
      if (!payload) return;
      state.checkIntervalSeconds = payload.checkIntervalSeconds || 60;
      state.historyWindowHours = payload.historyWindowHours || 168;
      state.groups = payload.groups || [];
      state.instances = payload.instances || [];
      state.incidentAnalytics = buildIncidentAnalytics(state.instances);
      renderSummary(payload);
      renderGroups(payload);
      renderIncidents();
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
function switchView(viewName) {
  state.activeView = viewName === "incidents" ? "incidents" : "overview";
  refs.overviewView.hidden = state.activeView !== "overview";
  refs.incidentsView.hidden = state.activeView !== "incidents";
  refs.viewOverview.classList.toggle("active", state.activeView === "overview");
  refs.viewIncidents.classList.toggle("active", state.activeView === "incidents");
}
refs.viewOverview.addEventListener("click", () => switchView("overview"));
refs.viewIncidents.addEventListener("click", () => switchView("incidents"));

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
function renderIncidents() {
  const analytics = state.incidentAnalytics || {
    rows: [],
    byInstance: new Map(),
    total: 0,
    open: 0,
    resolved: 0,
    mttrSeconds: null,
    mtbfSeconds: null,
  };

  refs.incidentsTotal.textContent = analytics.total;
  refs.incidentsOpen.textContent = analytics.open;
  refs.incidentsResolved.textContent = analytics.resolved;
  refs.incidentsMttr.textContent = analytics.mttrSeconds === null
    ? "—"
    : formatDuration(analytics.mttrSeconds);
  refs.incidentsMtbf.textContent = analytics.mtbfSeconds === null
    ? "—"
    : formatDuration(analytics.mtbfSeconds);

  const instanceRows = state.instances
    .map((item) => {
      const row = analytics.byInstance.get(item.id) || {
        total: 0,
        open: 0,
        mttrSeconds: null,
        mtbfSeconds: null,
      };
      return { item, row };
    })
    .sort((a, b) => {
      if (a.row.open !== b.row.open) return b.row.open - a.row.open;
      if (a.row.total !== b.row.total) return b.row.total - a.row.total;
      return String(a.item.name || a.item.url).localeCompare(String(b.item.name || b.item.url));
    });

  refs.incidentsInstanceMetrics.innerHTML = instanceRows.length
    ? instanceRows.map(({ item, row }) => `
      <div class="incident-instance-row">
        <div>
          <div class="incident-instance-title">${escapeHtml(item.name || hostnameOf(item.url))}</div>
          <div class="incident-instance-sub">${escapeHtml(item.url)}</div>
        </div>
        <div class="incident-instance-badges">
          <span class="badge ${row.open > 0 ? "bad" : ""}">${row.open} open</span>
          <span class="badge">${row.total} total</span>
          <span class="badge">MTTR ${escapeHtml(row.mttrSeconds === null ? "—" : formatDuration(row.mttrSeconds))}</span>
          <span class="badge">MTBF ${escapeHtml(row.mtbfSeconds === null ? "—" : formatDuration(row.mtbfSeconds))}</span>
        </div>
      </div>
    `).join("")
    : '<div class="empty">No monitors configured yet.</div>';

  refs.incidentsList.innerHTML = analytics.rows.length
    ? `
      <div class="incident-table">
        ${analytics.rows.map((row) => `
          <div class="incident-row">
            <div class="incident-cell incident-monitor">
              <div class="incident-instance-title">${escapeHtml(row.instanceName)}</div>
              <div class="incident-instance-sub">${escapeHtml(row.instanceUrl)}</div>
            </div>
            <div class="incident-cell"><span class="badge ${row.level === "outage" ? "bad" : "warn"}">${escapeHtml(row.level)}</span></div>
            <div class="incident-cell">${escapeHtml(formatTime(row.startedAt))}</div>
            <div class="incident-cell">${escapeHtml(row.resolvedAt ? formatTime(row.resolvedAt) : "Ongoing")}</div>
            <div class="incident-cell">${escapeHtml(formatDuration(row.durationSeconds))}</div>
            <div class="incident-cell incident-reason">${escapeHtml(row.reason || "No reason captured")}</div>
          </div>
        `).join("")}
      </div>
    `
    : '<div class="empty">No incidents within the selected history window.</div>';
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
  const uptimeWindowLabel = formatHistoryWindowLabel(state.historyWindowHours);
  const uptimeTag = item.uptimePercentage !== null && item.uptimePercentage !== undefined
    ? `<span class="badge" title="${escapeHtml(uptimeWindowLabel)}">${item.uptimePercentage.toFixed(2)}% · ${escapeHtml(uptimeWindowLabel)}</span>` : "";
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
  const issueBadges = [];
  if ((item.state === "outage" || item.state === "degraded") && item.error) {
    const failedSub = (item.subchecks || []).find((s) => s.ok === false);
    if (failedSub && failedSub.url) {
      const tip = [failedSub.label, failedSub.error, failedSub.url].filter(Boolean).join(" · ");
      issueBadges.push(`<a class="badge bad link" href="${escapeHtml(failedSub.url)}" target="_blank" rel="noreferrer" title="Open sub-check: ${escapeHtml(tip)}">${escapeHtml(item.error)}</a>`);
    } else {
      issueBadges.push(`<span class="badge bad">${escapeHtml(item.error)}</span>`);
    }
  }
  if (!item.apiOk) {
    const outageSince = findCurrentApiDownSince(item.history || []);
    const label = outageSince
      ? `API down since ${formatTime(outageSince)}`
      : "API is down";
    issueBadges.push(`<span class="badge bad">${escapeHtml(label)}</span>`);
  }
  const issueLine = issueBadges.length
    ? `<div class="instance-meta">${issueBadges.join("")}</div>`
    : "";
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
          <button class="ghost-button" type="button" data-clone="${item.id}">Clone</button>
          <button class="ghost-button" type="button" data-edit="${item.id}">Edit</button>
          <button class="ghost-button danger" type="button" data-delete="${item.id}">Delete</button>
        </div>
      </div>
    `;
  }).join("");
}
refs.instanceList.addEventListener("click", async (event) => {
  const cloneId = event.target.dataset?.clone;
  const editId = event.target.dataset?.edit;
  const deleteId = event.target.dataset?.delete;
  if (cloneId) openInstanceForm(Number(cloneId), { clone: true });
  else if (editId) openInstanceForm(Number(editId));
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

async function openInstanceForm(id, options = {}) {
  const cloneMode = options.clone === true;
  state.editingId = cloneMode ? null : id;
  state.instanceFormMode = cloneMode ? "clone" : (id ? "edit" : "create");
  state.subchecks = [];
  refs.instanceFormTitle.textContent = cloneMode ? "Clone monitor" : (id ? "Edit monitor" : "Add monitor");
  refs.instanceDelete.hidden = !id || cloneMode;
  refs.instanceSubmit.textContent = cloneMode ? "Create clone" : (id ? "Save monitor" : "Add monitor");
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
      if (item) {
        populateInstanceForm(item);
        if (cloneMode) {
          refs.instUrl.value = "";
          if (item.name) refs.instName.value = `${item.name} (copy)`;
          setStatus(refs.instanceStatus, "Cloned settings loaded. Set URL and save.");
        }
      }
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
  refs.instCheckInterval.value = item.check_interval_seconds ?? "";
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
    checkIntervalSeconds: refs.instCheckInterval.value !== "" ? Number(refs.instCheckInterval.value) : null,
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
    const isEdit = state.instanceFormMode === "edit";
    const title = isEdit ? "Saved" : "Created";
    const message = isEdit ? "Monitor updated." : "Monitor created.";
    showToast(title, message, "success");
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
switchView("overview");
loadStatusPage();
let refreshTimer = null;
function scheduleRefresh() {
  const ms = Math.max(15, state.checkIntervalSeconds || 60) * 1000;
  clearInterval(refreshTimer);
  refreshTimer = setInterval(loadStatusPage, ms);
}
setTimeout(scheduleRefresh, 2000);
