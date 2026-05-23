# Tidal uptime

This service checks a list of Tidal API endpoints and exposes the current snapshot as JSON.
Each poll run is stored in SQLite.
It can send email alerts to subscribers.

Checks performed for each URL:

1. `GET /` - the endpoint must return JSON with `version`
2. `GET /search/?s=the weeknd` - the endpoint must return a non-empty `data.items`
3. `GET /track/` - the endpoint must return non-empty `data.manifestHash` and `data.manifest`

Track validation uses the following `track id` list: `134858527`, `125155092`, `204567804`, with up to 2 retries on a different `id`.

If step 1 succeeds, the URL is included in `api`.

If both search and track checks succeed, the URL is treated as `operational`.

If the base API is reachable but `search` or `track` fails, the endpoint is treated as `degraded`.

If the base API itself fails, the endpoint is treated as `outage`.

If `/track/` returns `assetPresentation: "PREVIEW"`, it is treated as an invalid track response and reported as `Preview only (premium expired)`.

## Run with Docker

```bash
docker compose up --build -d
```

After startup:

- `http://localhost:8000/` - HTML dashboard
- `http://localhost:8000/status.json`

From the dashboard you can:

- add new API instances
- edit existing URLs
- monitor Apple Music wrapper account endpoints (`http://host:30020/`) by checking `dev_token` and `music_token`
- delete instances
- subscribe to email alerts for a specific API even without authentication
- review and delete all email subscriptions from the admin UI

## Environment variables

- `APP_HOST=0.0.0.0`
- `APP_PORT=8000`
- `CHECK_INTERVAL_SECONDS=300`
- `REQUEST_TIMEOUT_SECONDS=10`
- `DATABASE_PATH=data/uptime.db`
- `HISTORY_RETENTION_RUNS=4320`
- `STATUS_PAGE_WINDOW_HOURS=168`
- `MAX_TRACK_RETRIES=2`
- `USER_AGENT=...`
- `SEARCH_QUERY=the weeknd`
- `REFERENCE_API_VERSION_SOURCE_URL=...`
- `REFERENCE_API_VERSION_CACHE_PATH=data/reference_api_version.json`
- `REFERENCE_API_VERSION_REFRESH_SECONDS=86400`
- `ADMIN_PASSWORD=change-me`
- `AUTH_COOKIE_NAME=tidal_uptime_auth`
- `AUTH_COOKIE_SECRET=change-this-cookie-secret`
- `AUTH_COOKIE_MAX_AGE_SECONDS=604800`
- `EMAIL_ALERTS_ENABLED=true`
- `ALERT_FAILURE_STREAK=2`
- `ALERT_RECOVERY_ENABLED=true`
- `ALERT_RECOVERY_STREAK=1`
- `ALERT_TRIGGER_STATES=outage,degraded`
- `ALERT_TRIGGER_PROBES=api,search,track`
- `METRICS_MAX_PAYLOAD_BYTES=200000`

SMTP settings are stored in a separate `.smtp.toml` file.

The current probe track list is hardcoded in `app/settings.py`: `134858527`, `125155092`, `204567804`.

## Alerting

Global alert behavior is controlled by:

- `ALERT_FAILURE_STREAK` - failed polls in a row before first incident alert
- `ALERT_RECOVERY_ENABLED` - whether to send recovery notifications
- `ALERT_RECOVERY_STREAK` - successful polls in a row before recovery alert
- `ALERT_TRIGGER_STATES` - incident states to alert on: `outage`, `degraded`
- `ALERT_TRIGGER_PROBES` - probes to consider: `api`, `search`, `track`

Per monitor, alert types can be enabled/disabled in the Manager UI:

- primary outage (`alert_on_outage`)
- search/sub-check degradation (`alert_on_search`)
- track degradation (`alert_on_track`)
- recovery (`alert_on_recovery`)

Each endpoint sends only one incident alert per condition; a new alert for the same condition is sent only after recovery.

## Email subscriptions

Each endpoint card includes a bell button. Any user can use it to subscribe an email address to alerts for that specific API.

Subscriptions receive the same event types that are enabled for the endpoint itself:

- `outage`
- `search`
- `track`
- `recovery`

If a specific alert type is disabled for an endpoint, subscribers for that endpoint will not receive that event by email either.

To enable email alerts:

- keep `EMAIL_ALERTS_ENABLED=true` in `.env`
- configure SMTP settings in `.smtp.toml`
- `SMTP_USE_STARTTLS=true` for standard SMTP with STARTTLS
- `SMTP_USE_SSL=true` for SMTPS over implicit TLS

Supported SMTP fields:

- `smtp_host`
- `smtp_port`
- `smtp_username`
- `smtp_password`
- `smtp_from_name`
- `smtp_from_email`
- `smtp_reply_to`
- `smtp_message_stream_header`
- `smtp_use_starttls`
- `smtp_use_ssl`
- `smtp_timeout_seconds`

Example `.smtp.toml` for Postmark:

```toml
smtp_host = "smtp-broadcasts.postmarkapp.com"
smtp_port = 587
smtp_username = "..."
smtp_password = "..."
smtp_from_name = "Spotisaver"
smtp_from_email = "hi@spotisaver.online"
smtp_reply_to = "hi@spotisaver.online"
smtp_message_stream_header = "X-PM-Message-Stream: broadcast"
smtp_use_starttls = true
smtp_use_ssl = false
smtp_timeout_seconds = 10
```

All subscriptions can be reviewed and deleted from the authenticated `Subscriptions` popup in the dashboard.

## Status page

The dashboard timeline shows the last `168` hours (7 days) by default.
The number of columns is calculated automatically from `STATUS_PAGE_WINDOW_HOURS` and `CHECK_INTERVAL_SECONDS`.
The dashboard summary also shows the effective poll interval, for example: `2016 checks over ~168h · every 5m`.

To change the history window or how often the monitor checks endpoints, edit `.env`:

```env
STATUS_PAGE_WINDOW_HOURS=168
CHECK_INTERVAL_SECONDS=300
```

Examples:

- `STATUS_PAGE_WINDOW_HOURS=168` with `CHECK_INTERVAL_SECONDS=300` -> `2016` checks
- `STATUS_PAGE_WINDOW_HOURS=168` with `CHECK_INTERVAL_SECONDS=60` -> `10080` checks

Legend:

- `Operational` - both search and track checks work
- `Degraded` - the base API works, but search or track fails
- `Outage` - the base API is unreachable

The dashboard also includes an **Incidents** view with:

- incident log (`startedAt`, `resolvedAt`, `duration`, `reason`)
- per-monitor reliability metrics:
  `MTTR` (mean time to recovery) and `MTBF` (mean time between failures)

All incident calculations are based on the currently visible history window (`STATUS_PAGE_WINDOW_HOURS`).

## Storage

SQLite defaults to `data/uptime.db`.
In `docker-compose.yml`, the folder is mounted as `./data:/app/data`, so data survives container restarts.

Storage details:

- SQLite runs in `WAL` mode
- only the latest detailed endpoint status is stored as the current snapshot
- uptime history is stored compactly using `endpoint_id + poll_run_id + state`
- old runs are pruned automatically according to `HISTORY_RETENTION_RUNS`, but never below the visible status window
- alert state is stored separately so container restarts do not resend duplicate alerts
- email subscriptions are stored in SQLite and are deleted automatically when the related endpoint is deleted
