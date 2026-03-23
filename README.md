# Tidal uptime

This service checks a list of Tidal API endpoints every 5 minutes and exposes the current snapshot as JSON.
Each poll run is stored in SQLite.
It can also send alerts to a Discord webhook and email subscribers.

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
- delete instances
- subscribe to email alerts for a specific API even without authentication
- review and delete all email subscriptions from the admin UI

## Environment variables

- `CHECK_INTERVAL_SECONDS=300`
- `REQUEST_TIMEOUT_SECONDS=6`
- `DATABASE_PATH=data/uptime.db`
- `STATUS_PAGE_WINDOW_HOURS=8`
- `MAX_TRACK_RETRIES=2`
- `ADMIN_PASSWORD=change-me`
- `AUTH_COOKIE_SECRET=change-this-cookie-secret`
- `AUTH_COOKIE_MAX_AGE_SECONDS=604800`
- `APP_HOST=0.0.0.0`
- `APP_PORT=8000`
- `USER_AGENT=...`
- `SEARCH_QUERY=the weeknd`
- `DISCORD_WEBHOOK_URL=...`
- `DISCORD_ALERTS_ENABLED=true`
- `DISCORD_ALERT_USERNAME=Tidal Uptime`
- `DISCORD_ALERT_FAILURE_STREAK=2`
- `DISCORD_ALERT_RECOVERY_ENABLED=true`
- `DISCORD_ALERT_RECOVERY_STREAK=1`
- `DISCORD_ALERT_TRIGGER_STATES=outage,degraded`
- `DISCORD_ALERT_TRIGGER_PROBES=api,search,track`
- `EMAIL_ALERTS_ENABLED=true`

SMTP settings are stored in a separate `.smtp.toml` file.

The current probe track list is hardcoded in [app/settings.py](c:\Users\dmitry\Desktop\tidal uptime\app\settings.py): `134858527`, `125155092`, `204567804`.

## Discord alerts

An alert is sent only if `DISCORD_WEBHOOK_URL` is configured and `DISCORD_ALERTS_ENABLED=true`.
Each endpoint sends only one alert per incident. A new alert for the same endpoint can be sent only after recovery.

Flexible settings:

- `DISCORD_ALERT_FAILURE_STREAK` - how many failed polls in a row are required before the first alert is sent
- `DISCORD_ALERT_RECOVERY_ENABLED` - whether to send a recovery notification
- `DISCORD_ALERT_RECOVERY_STREAK` - how many successful polls in a row are required before recovery is sent
- `DISCORD_ALERT_TRIGGER_STATES` - alert states: `outage`, `degraded`
- `DISCORD_ALERT_TRIGGER_PROBES` - which checks are considered: `api`, `search`, `track`

Examples:

- Alert only when the base API is fully down after 3 failed polls in a row:
  `DISCORD_ALERT_TRIGGER_STATES=outage`
  `DISCORD_ALERT_TRIGGER_PROBES=api`
  `DISCORD_ALERT_FAILURE_STREAK=3`

- Alert on any degradation, but without recovery notifications:
  `DISCORD_ALERT_TRIGGER_STATES=outage,degraded`
  `DISCORD_ALERT_TRIGGER_PROBES=api,search,track`
  `DISCORD_ALERT_RECOVERY_ENABLED=false`

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

The dashboard timeline shows the last `8` hours by default.
The number of columns is calculated automatically from `STATUS_PAGE_WINDOW_HOURS` and `CHECK_INTERVAL_SECONDS`.

Legend:

- `Operational` - both search and track checks work
- `Degraded` - the base API works, but search or track fails
- `Outage` - the base API is unreachable

## Storage

SQLite defaults to `data/uptime.db`.
In `docker-compose.yml`, the folder is mounted as `./data:/app/data`, so data survives container restarts.

Storage details:

- SQLite runs in `WAL` mode
- only the latest detailed endpoint status is stored as the current snapshot
- uptime history is stored compactly using `endpoint_id + poll_run_id + state`
- old runs are pruned automatically according to `HISTORY_RETENTION_RUNS`
- alert state is stored separately so container restarts do not resend duplicate alerts
- email subscriptions are stored in SQLite and are deleted automatically when the related endpoint is deleted
