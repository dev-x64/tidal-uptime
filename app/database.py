from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path
from typing import Any

from app.settings import Settings

STATE_OUTAGE = 0
STATE_DEGRADED = 1
STATE_OPERATIONAL = 2


class SQLiteStore:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.db_path = Path(settings.database_path)

    async def initialize(self) -> None:
        await asyncio.to_thread(self._initialize_sync)

    async def load_latest_snapshot(self) -> dict[str, Any] | None:
        return await asyncio.to_thread(self._load_latest_snapshot_sync)

    async def save_snapshot(
        self, snapshot: dict[str, Any], endpoint_results: list[dict[str, Any]]
    ) -> int | None:
        return await asyncio.to_thread(self._save_snapshot_sync, snapshot, endpoint_results)

    async def list_endpoints(self) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._list_endpoints_sync)

    async def list_endpoint_urls(self) -> list[str]:
        return await asyncio.to_thread(self._list_endpoint_urls_sync)

    async def create_endpoint(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await asyncio.to_thread(self._create_endpoint_sync, payload)

    async def update_endpoint(self, endpoint_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        return await asyncio.to_thread(self._update_endpoint_sync, endpoint_id, payload)

    async def list_groups(self) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._list_groups_sync)

    async def create_group(self, name: str, sort_order: int = 0) -> dict[str, Any]:
        return await asyncio.to_thread(self._create_group_sync, name, sort_order)

    async def update_group(self, group_id: int, name: str, sort_order: int) -> dict[str, Any]:
        return await asyncio.to_thread(self._update_group_sync, group_id, name, sort_order)

    async def delete_group(self, group_id: int) -> None:
        await asyncio.to_thread(self._delete_group_sync, group_id)

    async def replace_subchecks_for_endpoint(
        self,
        endpoint_id: int,
        subchecks: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return await asyncio.to_thread(
            self._replace_subchecks_sync, endpoint_id, subchecks
        )

    async def save_subcheck_results(
        self,
        poll_run_id: int,
        results: list[dict[str, Any]],
    ) -> None:
        await asyncio.to_thread(self._save_subcheck_results_sync, poll_run_id, results)

    async def latest_subcheck_status_by_endpoint(self) -> dict[int, list[dict[str, Any]]]:
        return await asyncio.to_thread(self._latest_subcheck_status_by_endpoint_sync)

    async def save_endpoint_metrics(self, endpoint_id: int, metrics: dict[str, Any]) -> None:
        await asyncio.to_thread(self._save_endpoint_metrics_sync, endpoint_id, metrics)

    async def get_endpoint_metrics(self, endpoint_id: int) -> dict[str, Any] | None:
        return await asyncio.to_thread(self._get_endpoint_metrics_sync, endpoint_id)

    async def delete_endpoint(self, endpoint_id: int) -> None:
        await asyncio.to_thread(self._delete_endpoint_sync, endpoint_id)

    async def get_status_page_data(self, history_limit: int = 60) -> dict[str, Any]:
        return await asyncio.to_thread(self._get_status_page_data_sync, history_limit)

    async def load_alert_states(self) -> dict[int, dict[str, Any]]:
        return await asyncio.to_thread(self._load_alert_states_sync)

    async def save_alert_states(self, alert_states: list[dict[str, Any]]) -> None:
        await asyncio.to_thread(self._save_alert_states_sync, alert_states)

    async def clear_alert_state(self, endpoint_id: int) -> None:
        await asyncio.to_thread(self._clear_alert_state_sync, endpoint_id)

    async def load_latest_endpoint_results(self) -> dict[int, dict[str, Any]]:
        return await asyncio.to_thread(self._load_latest_endpoint_results_sync)

    async def update_all_endpoint_alert_settings(
        self,
        email_alerts_enabled: bool,
        alert_on_outage: bool,
        alert_on_search: bool,
        alert_on_track: bool,
        alert_on_recovery: bool,
    ) -> int:
        return await asyncio.to_thread(
            self._update_all_endpoint_alert_settings_sync,
            email_alerts_enabled,
            alert_on_outage,
            alert_on_search,
            alert_on_track,
            alert_on_recovery,
        )

    async def clear_all_alert_states(self) -> None:
        await asyncio.to_thread(self._clear_all_alert_states_sync)

    async def create_email_subscription(self, endpoint_id: int, email: str) -> dict[str, Any]:
        return await asyncio.to_thread(
            self._create_email_subscription_sync,
            endpoint_id,
            email,
        )

    async def list_email_subscriptions(self) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._list_email_subscriptions_sync)

    async def load_email_subscriptions_by_endpoint(self) -> dict[int, list[str]]:
        return await asyncio.to_thread(self._load_email_subscriptions_by_endpoint_sync)

    async def delete_email_subscription(self, subscription_id: int) -> None:
        await asyncio.to_thread(self._delete_email_subscription_sync, subscription_id)

    def _initialize_sync(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            migration_performed = False
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS monitored_endpoints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL UNIQUE,
                    alerts_enabled INTEGER NOT NULL DEFAULT 1,
                    email_alerts_enabled INTEGER NOT NULL DEFAULT 1,
                    alert_on_outage INTEGER NOT NULL DEFAULT 1,
                    alert_on_degraded INTEGER NOT NULL DEFAULT 1,
                    alert_on_search INTEGER NOT NULL DEFAULT 1,
                    alert_on_track INTEGER NOT NULL DEFAULT 1,
                    alert_on_recovery INTEGER NOT NULL DEFAULT 1,
                    check_interval_seconds INTEGER,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS poll_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    last_updated TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS latest_endpoint_status (
                    endpoint_id INTEGER PRIMARY KEY,
                    poll_run_id INTEGER NOT NULL,
                    version TEXT,
                    api_ok INTEGER NOT NULL,
                    search_ok INTEGER NOT NULL DEFAULT 0,
                    track_ok INTEGER NOT NULL,
                    down_status INTEGER,
                    down_error TEXT,
                    response_time_ms INTEGER,
                    FOREIGN KEY (endpoint_id) REFERENCES monitored_endpoints(id) ON DELETE CASCADE,
                    FOREIGN KEY (poll_run_id) REFERENCES poll_runs(id) ON DELETE CASCADE
                ) WITHOUT ROWID
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS endpoint_history (
                    endpoint_id INTEGER NOT NULL,
                    poll_run_id INTEGER NOT NULL,
                    state INTEGER NOT NULL,
                    PRIMARY KEY (endpoint_id, poll_run_id),
                    FOREIGN KEY (endpoint_id) REFERENCES monitored_endpoints(id) ON DELETE CASCADE,
                    FOREIGN KEY (poll_run_id) REFERENCES poll_runs(id) ON DELETE CASCADE
                ) WITHOUT ROWID
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_endpoint_history_poll_run_id
                ON endpoint_history (poll_run_id)
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS endpoint_history_detail (
                    endpoint_id INTEGER NOT NULL,
                    poll_run_id INTEGER NOT NULL,
                    down_status INTEGER,
                    down_error TEXT,
                    response_time_ms INTEGER,
                    PRIMARY KEY (endpoint_id, poll_run_id),
                    FOREIGN KEY (endpoint_id) REFERENCES monitored_endpoints(id) ON DELETE CASCADE,
                    FOREIGN KEY (poll_run_id) REFERENCES poll_runs(id) ON DELETE CASCADE
                ) WITHOUT ROWID
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_endpoint_history_detail_poll_run_id
                ON endpoint_history_detail (poll_run_id)
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS endpoint_alert_state (
                    endpoint_id INTEGER PRIMARY KEY,
                    phase TEXT NOT NULL,
                    condition_key TEXT,
                    condition_state TEXT,
                    condition_summary TEXT,
                    failure_streak INTEGER NOT NULL DEFAULT 0,
                    recovery_streak INTEGER NOT NULL DEFAULT 0,
                    last_failure_alert_streak INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (endpoint_id) REFERENCES monitored_endpoints(id) ON DELETE CASCADE
                ) WITHOUT ROWID
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS endpoint_email_subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    endpoint_id INTEGER NOT NULL,
                    email TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE (endpoint_id, email),
                    FOREIGN KEY (endpoint_id) REFERENCES monitored_endpoints(id) ON DELETE CASCADE
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_endpoint_email_subscriptions_endpoint_id
                ON endpoint_email_subscriptions (endpoint_id)
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS monitor_groups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS monitor_subchecks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    endpoint_id INTEGER NOT NULL,
                    label TEXT NOT NULL,
                    url TEXT NOT NULL,
                    request_method TEXT NOT NULL DEFAULT 'GET',
                    expected_status INTEGER,
                    match_type TEXT,
                    match_path TEXT,
                    match_value TEXT,
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (endpoint_id) REFERENCES monitored_endpoints(id) ON DELETE CASCADE
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_monitor_subchecks_endpoint_id
                ON monitor_subchecks (endpoint_id)
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS latest_subcheck_status (
                    subcheck_id INTEGER PRIMARY KEY,
                    poll_run_id INTEGER NOT NULL,
                    ok INTEGER NOT NULL,
                    status_code INTEGER,
                    error TEXT,
                    response_time_ms INTEGER,
                    FOREIGN KEY (subcheck_id) REFERENCES monitor_subchecks(id) ON DELETE CASCADE,
                    FOREIGN KEY (poll_run_id) REFERENCES poll_runs(id) ON DELETE CASCADE
                ) WITHOUT ROWID
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS latest_endpoint_metrics (
                    endpoint_id INTEGER PRIMARY KEY,
                    fetched_at TEXT NOT NULL,
                    ok INTEGER NOT NULL,
                    status_code INTEGER,
                    error TEXT,
                    payload_json TEXT,
                    response_time_ms INTEGER,
                    FOREIGN KEY (endpoint_id) REFERENCES monitored_endpoints(id) ON DELETE CASCADE
                ) WITHOUT ROWID
                """
            )
            endpoint_count = connection.execute(
                """
                SELECT COUNT(*)
                FROM monitored_endpoints
                """
            ).fetchone()[0]
            endpoint_columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info(monitored_endpoints)").fetchall()
            }
            if "alerts_enabled" not in endpoint_columns:
                connection.execute(
                    "ALTER TABLE monitored_endpoints ADD COLUMN alerts_enabled INTEGER NOT NULL DEFAULT 1"
                )
            if "email_alerts_enabled" not in endpoint_columns:
                connection.execute(
                    "ALTER TABLE monitored_endpoints ADD COLUMN email_alerts_enabled INTEGER NOT NULL DEFAULT 1"
                )
            if "alert_on_outage" not in endpoint_columns:
                connection.execute(
                    "ALTER TABLE monitored_endpoints ADD COLUMN alert_on_outage INTEGER NOT NULL DEFAULT 1"
                )
            if "alert_on_degraded" not in endpoint_columns:
                connection.execute(
                    "ALTER TABLE monitored_endpoints ADD COLUMN alert_on_degraded INTEGER NOT NULL DEFAULT 1"
                )
            if "alert_on_search" not in endpoint_columns:
                connection.execute(
                    "ALTER TABLE monitored_endpoints ADD COLUMN alert_on_search INTEGER NOT NULL DEFAULT 1"
                )
                connection.execute(
                    """
                    UPDATE monitored_endpoints
                    SET alert_on_search = COALESCE(alert_on_degraded, 1)
                    """
                )
            if "alert_on_track" not in endpoint_columns:
                connection.execute(
                    "ALTER TABLE monitored_endpoints ADD COLUMN alert_on_track INTEGER NOT NULL DEFAULT 1"
                )
                connection.execute(
                    """
                    UPDATE monitored_endpoints
                    SET alert_on_track = COALESCE(alert_on_degraded, 1)
                    """
                )
            if "alert_on_recovery" not in endpoint_columns:
                connection.execute(
                    "ALTER TABLE monitored_endpoints ADD COLUMN alert_on_recovery INTEGER NOT NULL DEFAULT 1"
                )
            if "name" not in endpoint_columns:
                connection.execute("ALTER TABLE monitored_endpoints ADD COLUMN name TEXT")
            if "kind" not in endpoint_columns:
                connection.execute(
                    "ALTER TABLE monitored_endpoints ADD COLUMN kind TEXT NOT NULL DEFAULT 'tidal'"
                )
            if "group_id" not in endpoint_columns:
                connection.execute(
                    "ALTER TABLE monitored_endpoints ADD COLUMN group_id INTEGER"
                )
            if "request_method" not in endpoint_columns:
                connection.execute(
                    "ALTER TABLE monitored_endpoints ADD COLUMN request_method TEXT NOT NULL DEFAULT 'GET'"
                )
            if "expected_status" not in endpoint_columns:
                connection.execute("ALTER TABLE monitored_endpoints ADD COLUMN expected_status INTEGER")
            if "match_type" not in endpoint_columns:
                connection.execute("ALTER TABLE monitored_endpoints ADD COLUMN match_type TEXT")
            if "match_path" not in endpoint_columns:
                connection.execute("ALTER TABLE monitored_endpoints ADD COLUMN match_path TEXT")
            if "match_value" not in endpoint_columns:
                connection.execute("ALTER TABLE monitored_endpoints ADD COLUMN match_value TEXT")
            if "metrics_url" not in endpoint_columns:
                connection.execute("ALTER TABLE monitored_endpoints ADD COLUMN metrics_url TEXT")
            if "metrics_keys" not in endpoint_columns:
                connection.execute("ALTER TABLE monitored_endpoints ADD COLUMN metrics_keys TEXT")
            if "check_interval_seconds" not in endpoint_columns:
                connection.execute(
                    "ALTER TABLE monitored_endpoints ADD COLUMN check_interval_seconds INTEGER"
                )

            now = self._utc_now()
            tidal_group_row = connection.execute(
                "SELECT id FROM monitor_groups WHERE name = ?",
                (self.settings.default_group_name,),
            ).fetchone()
            if tidal_group_row is None:
                cursor = connection.execute(
                    """
                    INSERT INTO monitor_groups (name, sort_order, created_at, updated_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (self.settings.default_group_name, 0, now, now),
                )
                tidal_group_id = cursor.lastrowid
            else:
                tidal_group_id = int(tidal_group_row["id"])

            connection.execute(
                """
                UPDATE monitored_endpoints
                SET group_id = ?
                WHERE group_id IS NULL AND kind = 'tidal'
                """,
                (tidal_group_id,),
            )

            if endpoint_count == 0:
                connection.executemany(
                    """
                    INSERT INTO monitored_endpoints (
                        url,
                        alerts_enabled,
                        email_alerts_enabled,
                        alert_on_outage,
                        alert_on_degraded,
                        alert_on_search,
                        alert_on_track,
                        alert_on_recovery,
                        kind,
                        group_id,
                        request_method,
                        created_at,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (url, 1, 1, 1, 1, 1, 1, 1, "tidal", tidal_group_id, "GET", now, now)
                        for url in self.settings.default_endpoints
                    ],
                )
            latest_status_columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info(latest_endpoint_status)").fetchall()
            }
            if "search_ok" not in latest_status_columns:
                connection.execute(
                    "ALTER TABLE latest_endpoint_status ADD COLUMN search_ok INTEGER NOT NULL DEFAULT 0"
                )
            if "response_time_ms" not in latest_status_columns:
                connection.execute(
                    "ALTER TABLE latest_endpoint_status ADD COLUMN response_time_ms INTEGER"
                )
            latest_subcheck_columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info(latest_subcheck_status)").fetchall()
            }
            if "response_time_ms" not in latest_subcheck_columns:
                connection.execute(
                    "ALTER TABLE latest_subcheck_status ADD COLUMN response_time_ms INTEGER"
                )
            history_detail_columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info(endpoint_history_detail)").fetchall()
            }
            if "response_time_ms" not in history_detail_columns:
                connection.execute(
                    "ALTER TABLE endpoint_history_detail ADD COLUMN response_time_ms INTEGER"
                )

            legacy_exists = connection.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='endpoint_checks'"
            ).fetchone()[0]
            if legacy_exists:
                columns = {
                    row[1]
                    for row in connection.execute("PRAGMA table_info(endpoint_checks)").fetchall()
                }
                if "streaming_ok" in columns and "track_ok" not in columns:
                    connection.execute("ALTER TABLE endpoint_checks RENAME COLUMN streaming_ok TO track_ok")

            if self._legacy_data_needs_migration(connection):
                self._migrate_legacy_endpoint_checks(connection)
                migration_performed = True

            self._prune_old_runs(connection)
            connection.commit()
            if migration_performed:
                connection.execute("VACUUM")

    def _load_latest_snapshot_sync(self) -> dict[str, Any] | None:
        if not self.db_path.exists():
            return None

        with self._connect() as connection:
            endpoint_urls = [
                row["url"]
                for row in connection.execute(
                    "SELECT url FROM monitored_endpoints ORDER BY id ASC"
                ).fetchall()
            ]
            latest_run = connection.execute(
                "SELECT id, last_updated FROM poll_runs ORDER BY id DESC LIMIT 1"
            ).fetchone()

            if latest_run is None:
                return None

            rows = connection.execute(
                """
                SELECT monitored_endpoints.url, latest_endpoint_status.version,
                       latest_endpoint_status.api_ok, latest_endpoint_status.search_ok,
                       latest_endpoint_status.track_ok,
                       latest_endpoint_status.down_status, latest_endpoint_status.down_error
                FROM latest_endpoint_status
                JOIN monitored_endpoints ON monitored_endpoints.id = latest_endpoint_status.endpoint_id
                WHERE latest_endpoint_status.poll_run_id = ?
                ORDER BY monitored_endpoints.id ASC
                """,
                (latest_run["id"],),
            ).fetchall()

        return self._build_snapshot(latest_run["last_updated"], rows, endpoint_urls)

    def _save_snapshot_sync(
        self, snapshot: dict[str, Any], endpoint_results: list[dict[str, Any]]
    ) -> int | None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            endpoint_id_by_url = {
                row["url"]: row["id"]
                for row in connection.execute(
                    "SELECT id, url FROM monitored_endpoints"
                ).fetchall()
            }
            cursor = connection.execute(
                "INSERT INTO poll_runs (last_updated) VALUES (?)",
                (snapshot["lastUpdated"],),
            )
            poll_run_id = cursor.lastrowid

            connection.execute("DELETE FROM latest_endpoint_status")
            connection.executemany(
                """
                INSERT INTO latest_endpoint_status (
                    endpoint_id,
                    poll_run_id,
                    version,
                    api_ok,
                    search_ok,
                    track_ok,
                    down_status,
                    down_error,
                    response_time_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        endpoint_id_by_url[result["url"]],
                        poll_run_id,
                        result["version"],
                        1 if result["api_ok"] else 0,
                        1 if result["search_ok"] else 0,
                        1 if result["track_ok"] else 0,
                        result["down_status"],
                        result["down_error"],
                        result.get("response_time_ms"),
                    )
                    for result in endpoint_results
                ],
            )
            connection.executemany(
                """
                INSERT INTO endpoint_history (
                    endpoint_id,
                    poll_run_id,
                    state
                ) VALUES (?, ?, ?)
                """,
                [
                    (
                        endpoint_id_by_url[result["url"]],
                        poll_run_id,
                        self._state_from_result(result),
                    )
                    for result in endpoint_results
                ],
            )
            connection.executemany(
                """
                INSERT INTO endpoint_history_detail (
                    endpoint_id,
                    poll_run_id,
                    down_status,
                    down_error,
                    response_time_ms
                ) VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (
                        endpoint_id_by_url[result["url"]],
                        poll_run_id,
                        result["down_status"],
                        result["down_error"],
                        result.get("response_time_ms"),
                    )
                    for result in endpoint_results
                    if (
                        result["down_status"] is not None
                        or result.get("response_time_ms") is not None
                    )
                ],
            )
            self._prune_old_runs(connection)
            connection.commit()
        return int(poll_run_id) if poll_run_id is not None else None

    def _load_alert_states_sync(self) -> dict[int, dict[str, Any]]:
        if not self.db_path.exists():
            return {}

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT endpoint_id, phase, condition_key, condition_state, condition_summary,
                       failure_streak, recovery_streak, last_failure_alert_streak, updated_at
                FROM endpoint_alert_state
                """
            ).fetchall()
        return {row["endpoint_id"]: dict(row) for row in rows}

    def _save_alert_states_sync(self, alert_states: list[dict[str, Any]]) -> None:
        if not alert_states:
            return

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executemany(
                """
                INSERT INTO endpoint_alert_state (
                    endpoint_id,
                    phase,
                    condition_key,
                    condition_state,
                    condition_summary,
                    failure_streak,
                    recovery_streak,
                    last_failure_alert_streak,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(endpoint_id) DO UPDATE SET
                    phase = excluded.phase,
                    condition_key = excluded.condition_key,
                    condition_state = excluded.condition_state,
                    condition_summary = excluded.condition_summary,
                    failure_streak = excluded.failure_streak,
                    recovery_streak = excluded.recovery_streak,
                    last_failure_alert_streak = excluded.last_failure_alert_streak,
                    updated_at = excluded.updated_at
                """,
                [
                    (
                        state["endpoint_id"],
                        state["phase"],
                        state["condition_key"],
                        state["condition_state"],
                        state["condition_summary"],
                        state["failure_streak"],
                        state["recovery_streak"],
                        state["last_failure_alert_streak"],
                        state["updated_at"],
                    )
                    for state in alert_states
                ],
            )
            connection.commit()

    def _clear_alert_state_sync(self, endpoint_id: int) -> None:
        if not self.db_path.exists():
            return

        with self._connect() as connection:
            connection.execute(
                "DELETE FROM endpoint_alert_state WHERE endpoint_id = ?",
                (endpoint_id,),
            )
            connection.commit()

    def _load_latest_endpoint_results_sync(self) -> dict[int, dict[str, Any]]:
        if not self.db_path.exists():
            return {}

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT monitored_endpoints.id, monitored_endpoints.url, latest_endpoint_status.version,
                       latest_endpoint_status.api_ok, latest_endpoint_status.search_ok,
                       latest_endpoint_status.track_ok,
                       latest_endpoint_status.down_status, latest_endpoint_status.down_error,
                       latest_endpoint_status.response_time_ms
                FROM latest_endpoint_status
                JOIN monitored_endpoints ON monitored_endpoints.id = latest_endpoint_status.endpoint_id
                """
            ).fetchall()

        return {
            int(row["id"]): {
                "url": row["url"],
                "version": row["version"],
                "api_ok": bool(row["api_ok"]),
                "search_ok": bool(row["search_ok"]),
                "track_ok": bool(row["track_ok"]),
                "down_status": row["down_status"],
                "down_error": row["down_error"],
                "response_time_ms": row["response_time_ms"],
            }
            for row in rows
        }

    def _build_snapshot(
        self,
        last_updated: str,
        rows: list[sqlite3.Row],
        endpoint_urls: list[str],
    ) -> dict[str, Any]:
        rows_by_url = {row["url"]: row for row in rows}
        snapshot = {
            "lastUpdated": last_updated,
            "api": [],
            "streaming": [],
            "down": [],
        }

        for url in endpoint_urls:
            row = rows_by_url.get(url)
            if row is None:
                continue

            version = row["version"]
            if row["api_ok"] and version:
                snapshot["api"].append({"url": url, "version": version})
            if row["track_ok"] and version:
                snapshot["streaming"].append({"url": url, "version": version})
            if row["down_status"] is not None:
                snapshot["down"].append(
                    {
                        "url": url,
                        "status": row["down_status"],
                        "error": row["down_error"],
                    }
                )

        return snapshot

    def _list_endpoints_sync(self) -> list[dict[str, Any]]:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, url, name, kind, group_id, request_method,
                       expected_status, match_type, match_path, match_value,
                       metrics_url, metrics_keys, check_interval_seconds,
                       alerts_enabled, email_alerts_enabled,
                       alert_on_outage, alert_on_search, alert_on_track, alert_on_recovery,
                       created_at, updated_at
                FROM monitored_endpoints
                ORDER BY id ASC
                """
            ).fetchall()
            subchecks_by_endpoint = self._load_subchecks_by_endpoint(connection)
        normalized = [self._normalize_endpoint_row(row) for row in rows]
        for endpoint in normalized:
            endpoint["subchecks"] = subchecks_by_endpoint.get(int(endpoint["id"]), [])
        return normalized

    def _load_subchecks_by_endpoint(
        self, connection: sqlite3.Connection
    ) -> dict[int, list[dict[str, Any]]]:
        rows = connection.execute(
            """
            SELECT id, endpoint_id, label, url, request_method,
                   expected_status, match_type, match_path, match_value,
                   sort_order
            FROM monitor_subchecks
            ORDER BY endpoint_id ASC, sort_order ASC, id ASC
            """
        ).fetchall()
        result: dict[int, list[dict[str, Any]]] = {}
        for row in rows:
            result.setdefault(int(row["endpoint_id"]), []).append(self._normalize_subcheck_row(row))
        return result

    def _normalize_subcheck_row(self, row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
        payload = dict(row)
        return {
            "id": int(payload["id"]),
            "endpoint_id": int(payload["endpoint_id"]) if payload.get("endpoint_id") is not None else None,
            "label": str(payload.get("label") or ""),
            "url": str(payload.get("url") or ""),
            "request_method": str(payload.get("request_method") or "GET"),
            "expected_status": int(payload["expected_status"]) if payload.get("expected_status") is not None else None,
            "match_type": payload.get("match_type"),
            "match_path": payload.get("match_path"),
            "match_value": payload.get("match_value"),
            "sort_order": int(payload.get("sort_order") or 0),
        }

    def _list_endpoint_urls_sync(self) -> list[str]:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT url FROM monitored_endpoints ORDER BY id ASC"
            ).fetchall()
        return [row[0] for row in rows]

    ENDPOINT_INSERT_FIELDS = (
        "url",
        "name",
        "kind",
        "group_id",
        "request_method",
        "expected_status",
        "match_type",
        "match_path",
        "match_value",
        "alerts_enabled",
        "email_alerts_enabled",
        "alert_on_outage",
        "alert_on_degraded",
        "alert_on_search",
        "alert_on_track",
        "alert_on_recovery",
    )

    def _coerce_endpoint_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        kind = (payload.get("kind") or "tidal").strip().lower()
        if kind not in {"tidal", "http", "applemusic_wrapper"}:
            raise ValueError(f"Unsupported monitor kind: {kind}")
        url = str(payload["url"]).rstrip("/")
        if not url:
            raise ValueError("URL is required")
        name = (payload.get("name") or "").strip() or None
        group_id = payload.get("group_id")
        if group_id is not None:
            group_id = int(group_id)
        method = (payload.get("request_method") or "GET").strip().upper()
        if method not in {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"}:
            method = "GET"
        expected_status = payload.get("expected_status")
        if expected_status is not None and expected_status != "":
            expected_status = int(expected_status)
        else:
            expected_status = None
        match_type = (payload.get("match_type") or None) or None
        if match_type:
            match_type = str(match_type).strip().lower()
            if match_type not in {"status", "json_key", "json_equals", "contains"}:
                raise ValueError(f"Unsupported match_type: {match_type}")
        match_path = payload.get("match_path") or None
        match_value = payload.get("match_value") or None
        metrics_url = (payload.get("metrics_url") or "").strip() or None
        metrics_keys_raw = payload.get("metrics_keys")
        if isinstance(metrics_keys_raw, list):
            metrics_keys = "\n".join(str(line).strip() for line in metrics_keys_raw if str(line).strip())
        else:
            metrics_keys = (str(metrics_keys_raw or "")).strip() or None
            if metrics_keys:
                metrics_keys = "\n".join(
                    line.strip() for line in metrics_keys.splitlines() if line.strip()
                )
        if not metrics_keys:
            metrics_keys = None

        check_interval_raw = payload.get("check_interval_seconds")
        if check_interval_raw is None or check_interval_raw == "":
            check_interval_seconds: int | None = None
        else:
            check_interval_seconds = int(check_interval_raw)
            if check_interval_seconds < 1:
                raise ValueError("check_interval_seconds must be >= 1")

        alerts_enabled = bool(payload.get("alerts_enabled", True))
        email_alerts_enabled = bool(payload.get("email_alerts_enabled", True))
        alert_on_outage = bool(payload.get("alert_on_outage", True))
        alert_on_search = bool(payload.get("alert_on_search", True))
        alert_on_track = bool(payload.get("alert_on_track", True))
        alert_on_recovery = bool(payload.get("alert_on_recovery", True))

        return {
            "url": url,
            "name": name,
            "kind": kind,
            "group_id": group_id,
            "request_method": method,
            "expected_status": expected_status,
            "match_type": match_type,
            "match_path": match_path,
            "match_value": match_value,
            "metrics_url": metrics_url,
            "metrics_keys": metrics_keys,
            "check_interval_seconds": check_interval_seconds,
            "alerts_enabled": 1 if alerts_enabled else 0,
            "email_alerts_enabled": 1 if email_alerts_enabled else 0,
            "alert_on_outage": 1 if alert_on_outage else 0,
            "alert_on_degraded": 1 if (alert_on_search or alert_on_track) else 0,
            "alert_on_search": 1 if alert_on_search else 0,
            "alert_on_track": 1 if alert_on_track else 0,
            "alert_on_recovery": 1 if alert_on_recovery else 0,
        }

    def _create_endpoint_sync(self, payload: dict[str, Any]) -> dict[str, Any]:
        coerced = self._coerce_endpoint_payload(payload)
        timestamp = self._utc_now()
        with self._connect() as connection:
            try:
                cursor = connection.execute(
                    """
                    INSERT INTO monitored_endpoints (
                        url, name, kind, group_id, request_method,
                        expected_status, match_type, match_path, match_value,
                        metrics_url, metrics_keys, check_interval_seconds,
                        alerts_enabled, email_alerts_enabled,
                        alert_on_outage, alert_on_degraded,
                        alert_on_search, alert_on_track, alert_on_recovery,
                        created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        coerced["url"],
                        coerced["name"],
                        coerced["kind"],
                        coerced["group_id"],
                        coerced["request_method"],
                        coerced["expected_status"],
                        coerced["match_type"],
                        coerced["match_path"],
                        coerced["match_value"],
                        coerced["metrics_url"],
                        coerced["metrics_keys"],
                        coerced["check_interval_seconds"],
                        coerced["alerts_enabled"],
                        coerced["email_alerts_enabled"],
                        coerced["alert_on_outage"],
                        coerced["alert_on_degraded"],
                        coerced["alert_on_search"],
                        coerced["alert_on_track"],
                        coerced["alert_on_recovery"],
                        timestamp,
                        timestamp,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ValueError("Endpoint already exists") from exc

            new_id = cursor.lastrowid
            connection.commit()
        return self._fetch_endpoint(new_id)

    def _update_endpoint_sync(self, endpoint_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        coerced = self._coerce_endpoint_payload(payload)
        timestamp = self._utc_now()
        with self._connect() as connection:
            try:
                cursor = connection.execute(
                    """
                    UPDATE monitored_endpoints
                    SET url = ?, name = ?, kind = ?, group_id = ?, request_method = ?,
                        expected_status = ?, match_type = ?, match_path = ?, match_value = ?,
                        metrics_url = ?, metrics_keys = ?, check_interval_seconds = ?,
                        alerts_enabled = ?, email_alerts_enabled = ?,
                        alert_on_outage = ?, alert_on_degraded = ?,
                        alert_on_search = ?, alert_on_track = ?, alert_on_recovery = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        coerced["url"],
                        coerced["name"],
                        coerced["kind"],
                        coerced["group_id"],
                        coerced["request_method"],
                        coerced["expected_status"],
                        coerced["match_type"],
                        coerced["match_path"],
                        coerced["match_value"],
                        coerced["metrics_url"],
                        coerced["metrics_keys"],
                        coerced["check_interval_seconds"],
                        coerced["alerts_enabled"],
                        coerced["email_alerts_enabled"],
                        coerced["alert_on_outage"],
                        coerced["alert_on_degraded"],
                        coerced["alert_on_search"],
                        coerced["alert_on_track"],
                        coerced["alert_on_recovery"],
                        timestamp,
                        endpoint_id,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ValueError("Endpoint already exists") from exc

            if cursor.rowcount == 0:
                raise LookupError("Endpoint not found")
            connection.commit()
        return self._fetch_endpoint(endpoint_id)

    def _fetch_endpoint(self, endpoint_id: int | None) -> dict[str, Any]:
        if endpoint_id is None:
            raise LookupError("Endpoint not found")
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, url, name, kind, group_id, request_method,
                       expected_status, match_type, match_path, match_value,
                       metrics_url, metrics_keys, check_interval_seconds,
                       alerts_enabled, email_alerts_enabled,
                       alert_on_outage, alert_on_search, alert_on_track, alert_on_recovery,
                       created_at, updated_at
                FROM monitored_endpoints
                WHERE id = ?
                """,
                (endpoint_id,),
            ).fetchone()
            if row is None:
                raise LookupError("Endpoint not found")
            subchecks_by_endpoint = self._load_subchecks_by_endpoint(connection)
        normalized = self._normalize_endpoint_row(row)
        normalized["subchecks"] = subchecks_by_endpoint.get(int(normalized["id"]), [])
        return normalized

    def _update_all_endpoint_alert_settings_sync(
        self,
        email_alerts_enabled: bool,
        alert_on_outage: bool,
        alert_on_search: bool,
        alert_on_track: bool,
        alert_on_recovery: bool,
    ) -> int:
        timestamp = self._utc_now()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE monitored_endpoints
                SET email_alerts_enabled = ?,
                    alert_on_outage = ?,
                    alert_on_degraded = ?,
                    alert_on_search = ?,
                    alert_on_track = ?,
                    alert_on_recovery = ?,
                    updated_at = ?
                """,
                (
                    1 if email_alerts_enabled else 0,
                    1 if alert_on_outage else 0,
                    1 if (alert_on_search or alert_on_track) else 0,
                    1 if alert_on_search else 0,
                    1 if alert_on_track else 0,
                    1 if alert_on_recovery else 0,
                    timestamp,
                ),
            )
            connection.commit()
        return int(cursor.rowcount or 0)

    def _list_groups_sync(self) -> list[dict[str, Any]]:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, name, sort_order, created_at, updated_at
                FROM monitor_groups
                ORDER BY sort_order ASC, name ASC, id ASC
                """
            ).fetchall()
        return [
            {
                "id": int(row["id"]),
                "name": str(row["name"]),
                "sort_order": int(row["sort_order"]),
                "created_at": str(row["created_at"]),
                "updated_at": str(row["updated_at"]),
            }
            for row in rows
        ]

    def _create_group_sync(self, name: str, sort_order: int = 0) -> dict[str, Any]:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Group name is required")
        timestamp = self._utc_now()
        with self._connect() as connection:
            try:
                cursor = connection.execute(
                    """
                    INSERT INTO monitor_groups (name, sort_order, created_at, updated_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (clean_name, int(sort_order), timestamp, timestamp),
                )
            except sqlite3.IntegrityError as exc:
                raise ValueError("Group already exists") from exc
            row = connection.execute(
                "SELECT id, name, sort_order, created_at, updated_at FROM monitor_groups WHERE id = ?",
                (cursor.lastrowid,),
            ).fetchone()
            connection.commit()
        return {
            "id": int(row["id"]),
            "name": str(row["name"]),
            "sort_order": int(row["sort_order"]),
            "created_at": str(row["created_at"]),
            "updated_at": str(row["updated_at"]),
        }

    def _update_group_sync(self, group_id: int, name: str, sort_order: int) -> dict[str, Any]:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Group name is required")
        timestamp = self._utc_now()
        with self._connect() as connection:
            try:
                cursor = connection.execute(
                    """
                    UPDATE monitor_groups
                    SET name = ?, sort_order = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (clean_name, int(sort_order), timestamp, group_id),
                )
            except sqlite3.IntegrityError as exc:
                raise ValueError("Group already exists") from exc
            if cursor.rowcount == 0:
                raise LookupError("Group not found")
            row = connection.execute(
                "SELECT id, name, sort_order, created_at, updated_at FROM monitor_groups WHERE id = ?",
                (group_id,),
            ).fetchone()
            connection.commit()
        return {
            "id": int(row["id"]),
            "name": str(row["name"]),
            "sort_order": int(row["sort_order"]),
            "created_at": str(row["created_at"]),
            "updated_at": str(row["updated_at"]),
        }

    def _delete_group_sync(self, group_id: int) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE monitored_endpoints SET group_id = NULL WHERE group_id = ?",
                (group_id,),
            )
            cursor = connection.execute(
                "DELETE FROM monitor_groups WHERE id = ?",
                (group_id,),
            )
            if cursor.rowcount == 0:
                raise LookupError("Group not found")
            connection.commit()

    def _replace_subchecks_sync(
        self,
        endpoint_id: int,
        subchecks: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        timestamp = self._utc_now()
        with self._connect() as connection:
            endpoint_row = connection.execute(
                "SELECT id FROM monitored_endpoints WHERE id = ?",
                (endpoint_id,),
            ).fetchone()
            if endpoint_row is None:
                raise LookupError("Endpoint not found")
            connection.execute(
                "DELETE FROM monitor_subchecks WHERE endpoint_id = ?",
                (endpoint_id,),
            )
            normalized: list[tuple[Any, ...]] = []
            for index, sub in enumerate(subchecks):
                label = (sub.get("label") or "").strip()
                url = (sub.get("url") or "").strip().rstrip("/")
                if not url:
                    continue
                if not label:
                    label = url
                method = (sub.get("request_method") or "GET").strip().upper()
                if method not in {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"}:
                    method = "GET"
                expected_status = sub.get("expected_status")
                if expected_status not in (None, ""):
                    expected_status = int(expected_status)
                else:
                    expected_status = None
                match_type = (sub.get("match_type") or None) or None
                if match_type:
                    match_type = str(match_type).strip().lower()
                    if match_type not in {"status", "json_key", "json_equals", "contains"}:
                        raise ValueError(f"Unsupported match_type: {match_type}")
                match_path = sub.get("match_path") or None
                match_value = sub.get("match_value") or None
                sort_order = int(sub.get("sort_order") or index)
                normalized.append(
                    (
                        endpoint_id,
                        label,
                        url,
                        method,
                        expected_status,
                        match_type,
                        match_path,
                        match_value,
                        sort_order,
                        timestamp,
                    )
                )
            if normalized:
                connection.executemany(
                    """
                    INSERT INTO monitor_subchecks (
                        endpoint_id, label, url, request_method,
                        expected_status, match_type, match_path, match_value,
                        sort_order, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    normalized,
                )
            rows = connection.execute(
                """
                SELECT id, endpoint_id, label, url, request_method,
                       expected_status, match_type, match_path, match_value,
                       sort_order
                FROM monitor_subchecks
                WHERE endpoint_id = ?
                ORDER BY sort_order ASC, id ASC
                """,
                (endpoint_id,),
            ).fetchall()
            connection.commit()
        return [self._normalize_subcheck_row(row) for row in rows]

    def _save_subcheck_results_sync(
        self,
        poll_run_id: int,
        results: list[dict[str, Any]],
    ) -> None:
        if not results:
            return
        with self._connect() as connection:
            connection.executemany(
                """
                INSERT INTO latest_subcheck_status (
                    subcheck_id, poll_run_id, ok, status_code, error, response_time_ms
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(subcheck_id) DO UPDATE SET
                    poll_run_id = excluded.poll_run_id,
                    ok = excluded.ok,
                    status_code = excluded.status_code,
                    error = excluded.error,
                    response_time_ms = excluded.response_time_ms
                """,
                [
                    (
                        int(item["subcheck_id"]),
                        poll_run_id,
                        1 if item["ok"] else 0,
                        item.get("status_code"),
                        item.get("error"),
                        item.get("response_time_ms"),
                    )
                    for item in results
                ],
            )
            connection.commit()

    def _latest_subcheck_status_by_endpoint_sync(self) -> dict[int, list[dict[str, Any]]]:
        if not self.db_path.exists():
            return {}
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT s.endpoint_id, s.id AS subcheck_id, s.label, s.url, s.sort_order,
                       latest.ok, latest.status_code, latest.error
                FROM monitor_subchecks s
                LEFT JOIN latest_subcheck_status latest ON latest.subcheck_id = s.id
                ORDER BY s.endpoint_id ASC, s.sort_order ASC, s.id ASC
                """
            ).fetchall()
        result: dict[int, list[dict[str, Any]]] = {}
        for row in rows:
            result.setdefault(int(row["endpoint_id"]), []).append(
                {
                    "subcheck_id": int(row["subcheck_id"]),
                    "label": str(row["label"]),
                    "url": str(row["url"]),
                    "sort_order": int(row["sort_order"]),
                    "ok": bool(row["ok"]) if row["ok"] is not None else None,
                    "status_code": row["status_code"],
                    "error": row["error"],
                }
            )
        return result

    def _save_endpoint_metrics_sync(self, endpoint_id: int, metrics: dict[str, Any]) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO latest_endpoint_metrics (
                    endpoint_id, fetched_at, ok, status_code, error,
                    payload_json, response_time_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(endpoint_id) DO UPDATE SET
                    fetched_at = excluded.fetched_at,
                    ok = excluded.ok,
                    status_code = excluded.status_code,
                    error = excluded.error,
                    payload_json = excluded.payload_json,
                    response_time_ms = excluded.response_time_ms
                """,
                (
                    endpoint_id,
                    metrics.get("fetched_at"),
                    1 if metrics.get("ok") else 0,
                    metrics.get("status_code"),
                    metrics.get("error"),
                    metrics.get("payload_json"),
                    metrics.get("response_time_ms"),
                ),
            )
            connection.commit()

    def _get_endpoint_metrics_sync(self, endpoint_id: int) -> dict[str, Any] | None:
        if not self.db_path.exists():
            return None
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT endpoint_id, fetched_at, ok, status_code, error,
                       payload_json, response_time_ms
                FROM latest_endpoint_metrics
                WHERE endpoint_id = ?
                """,
                (endpoint_id,),
            ).fetchone()
        if row is None:
            return None
        return {
            "endpointId": int(row["endpoint_id"]),
            "fetchedAt": row["fetched_at"],
            "ok": bool(row["ok"]),
            "statusCode": row["status_code"],
            "error": row["error"],
            "payloadJson": row["payload_json"],
            "responseTimeMs": row["response_time_ms"],
        }

    def _create_email_subscription_sync(self, endpoint_id: int, email: str) -> dict[str, Any]:
        timestamp = self._utc_now()
        normalized_email = email.strip().lower()
        with self._connect() as connection:
            endpoint = connection.execute(
                """
                SELECT id, url, email_alerts_enabled
                FROM monitored_endpoints
                WHERE id = ?
                """,
                (endpoint_id,),
            ).fetchone()
            if endpoint is None:
                raise LookupError("Endpoint not found")
            if not bool(endpoint["email_alerts_enabled"]):
                raise ValueError("Email alerts are disabled for this instance")

            try:
                cursor = connection.execute(
                    """
                    INSERT INTO endpoint_email_subscriptions (
                        endpoint_id,
                        email,
                        created_at
                    )
                    VALUES (?, ?, ?)
                    """,
                    (endpoint_id, normalized_email, timestamp),
                )
            except sqlite3.IntegrityError as exc:
                raise ValueError("Subscription already exists") from exc

            row = connection.execute(
                """
                SELECT endpoint_email_subscriptions.id,
                       endpoint_email_subscriptions.endpoint_id,
                       monitored_endpoints.url AS endpoint_url,
                       endpoint_email_subscriptions.email,
                       endpoint_email_subscriptions.created_at
                FROM endpoint_email_subscriptions
                JOIN monitored_endpoints ON monitored_endpoints.id = endpoint_email_subscriptions.endpoint_id
                WHERE endpoint_email_subscriptions.id = ?
                """,
                (cursor.lastrowid,),
            ).fetchone()
            connection.commit()
        return dict(row)

    def _list_email_subscriptions_sync(self) -> list[dict[str, Any]]:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT endpoint_email_subscriptions.id,
                       endpoint_email_subscriptions.endpoint_id,
                       monitored_endpoints.url AS endpoint_url,
                       endpoint_email_subscriptions.email,
                       endpoint_email_subscriptions.created_at
                FROM endpoint_email_subscriptions
                JOIN monitored_endpoints ON monitored_endpoints.id = endpoint_email_subscriptions.endpoint_id
                ORDER BY endpoint_email_subscriptions.created_at DESC, endpoint_email_subscriptions.id DESC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def _load_email_subscriptions_by_endpoint_sync(self) -> dict[int, list[str]]:
        if not self.db_path.exists():
            return {}

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT endpoint_id, email
                FROM endpoint_email_subscriptions
                ORDER BY endpoint_id ASC, email ASC
                """
            ).fetchall()

        subscriptions: dict[int, list[str]] = {}
        for row in rows:
            subscriptions.setdefault(int(row["endpoint_id"]), []).append(str(row["email"]))
        return subscriptions

    def _delete_email_subscription_sync(self, subscription_id: int) -> None:
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM endpoint_email_subscriptions WHERE id = ?",
                (subscription_id,),
            )
            if cursor.rowcount == 0:
                raise LookupError("Subscription not found")
            connection.commit()

    def _delete_endpoint_sync(self, endpoint_id: int) -> None:
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM monitored_endpoints WHERE id = ?",
                (endpoint_id,),
            )
            if cursor.rowcount == 0:
                raise LookupError("Endpoint not found")
            connection.commit()

    def _utc_now(self) -> str:
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

    def _get_status_page_data_sync(self, history_limit: int) -> dict[str, Any]:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            endpoints = connection.execute(
                """
                SELECT id, url, name, kind, group_id, created_at, updated_at,
                       email_alerts_enabled,
                       expected_status, match_type, match_path, match_value,
                       metrics_url, metrics_keys,
                       request_method
                FROM monitored_endpoints
                ORDER BY id ASC
                """
            ).fetchall()
            groups = connection.execute(
                """
                SELECT id, name, sort_order
                FROM monitor_groups
                ORDER BY sort_order ASC, name ASC, id ASC
                """
            ).fetchall()
            subcheck_rows = connection.execute(
                """
                SELECT s.endpoint_id, s.id AS subcheck_id, s.label, s.url, s.sort_order,
                       latest.ok, latest.status_code, latest.error, latest.response_time_ms
                FROM monitor_subchecks s
                LEFT JOIN latest_subcheck_status latest ON latest.subcheck_id = s.id
                ORDER BY s.endpoint_id ASC, s.sort_order ASC, s.id ASC
                """
            ).fetchall()
            subcheck_status: dict[int, list[dict[str, Any]]] = {}
            for row in subcheck_rows:
                subcheck_status.setdefault(int(row["endpoint_id"]), []).append(
                    {
                        "subcheckId": int(row["subcheck_id"]),
                        "label": str(row["label"]),
                        "url": str(row["url"]),
                        "ok": bool(row["ok"]) if row["ok"] is not None else None,
                        "statusCode": row["status_code"],
                        "error": row["error"],
                        "responseTimeMs": row["response_time_ms"],
                    }
                )
            poll_runs = list(
                reversed(
                    connection.execute(
                        """
                        SELECT id, last_updated
                        FROM poll_runs
                        ORDER BY id DESC
                        LIMIT ?
                        """,
                        (history_limit,),
                    ).fetchall()
                )
            )

            run_ids = [row["id"] for row in poll_runs]
            history_rows: list[sqlite3.Row] = []
            if run_ids:
                placeholders = ", ".join("?" for _ in run_ids)
                history_rows = connection.execute(
                    f"""
                    SELECT endpoint_id, poll_run_id, state
                    FROM endpoint_history
                    WHERE poll_run_id IN ({placeholders})
                    """,
                    run_ids,
                ).fetchall()
            history_detail_rows: list[sqlite3.Row] = []
            if run_ids:
                placeholders = ", ".join("?" for _ in run_ids)
                history_detail_rows = connection.execute(
                    f"""
                    SELECT endpoint_id, poll_run_id, down_status, down_error, response_time_ms
                    FROM endpoint_history_detail
                    WHERE poll_run_id IN ({placeholders})
                    """,
                    run_ids,
                ).fetchall()
            latest_rows = connection.execute(
                """
                SELECT latest_endpoint_status.endpoint_id, latest_endpoint_status.version,
                       latest_endpoint_status.api_ok, latest_endpoint_status.search_ok,
                       latest_endpoint_status.track_ok,
                       latest_endpoint_status.down_status, latest_endpoint_status.down_error,
                       latest_endpoint_status.response_time_ms
                FROM latest_endpoint_status
                """
            ).fetchall()
            metrics_rows = connection.execute(
                """
                SELECT endpoint_id, fetched_at, ok, status_code, error,
                       payload_json, response_time_ms
                FROM latest_endpoint_metrics
                """
            ).fetchall()

        history_by_key = {
            (row["endpoint_id"], row["poll_run_id"]): row["state"]
            for row in history_rows
        }
        history_detail_by_key = {
            (row["endpoint_id"], row["poll_run_id"]): row
            for row in history_detail_rows
        }
        latest_by_endpoint_id = {row["endpoint_id"]: row for row in latest_rows}
        metrics_by_endpoint_id = {row["endpoint_id"]: row for row in metrics_rows}
        latest_run = poll_runs[-1] if poll_runs else None
        instances: list[dict[str, Any]] = []
        api_count = 0
        streaming_count = 0
        down_count = 0

        for endpoint in endpoints:
            current_row = latest_by_endpoint_id.get(endpoint["id"])
            current_state = self._classify_row(current_row)
            if current_row and current_row["api_ok"] and current_row["version"]:
                api_count += 1
            if current_row and current_row["track_ok"] and current_row["version"]:
                streaming_count += 1
            if current_row and current_row["down_status"] is not None:
                down_count += 1

            history = []
            operational_runs = 0
            known_runs = 0
            for poll_run in poll_runs:
                state = history_by_key.get((endpoint["id"], poll_run["id"]), -1)
                detail = history_detail_by_key.get((endpoint["id"], poll_run["id"]))
                history.append(
                    {
                        "state": self._state_label(state),
                        "lastUpdated": poll_run["last_updated"],
                        "statusCode": detail["down_status"] if detail else None,
                        "error": detail["down_error"] if detail else None,
                        "responseTimeMs": detail["response_time_ms"] if detail else None,
                    }
                )
                if state != -1:
                    known_runs += 1
                if state == STATE_OPERATIONAL:
                    operational_runs += 1

            uptime_percentage = round((operational_runs / known_runs) * 100, 3) if known_runs else None
            kind = str(endpoint["kind"]) if endpoint["kind"] else "tidal"
            endpoint_subchecks = subcheck_status.get(int(endpoint["id"]), [])
            if kind != "tidal" and endpoint_subchecks:
                if any(item["ok"] is False for item in endpoint_subchecks):
                    if current_state == STATE_OPERATIONAL:
                        current_state = STATE_DEGRADED
            metrics_row = metrics_by_endpoint_id.get(endpoint["id"])
            metrics_summary = self._build_metrics_summary(
                endpoint_columns=endpoint,
                metrics_row=metrics_row,
            )
            instances.append(
                {
                    "id": endpoint["id"],
                    "url": endpoint["url"],
                    "name": endpoint["name"] if endpoint["name"] else None,
                    "kind": kind,
                    "metrics": metrics_summary,
                    "groupId": int(endpoint["group_id"]) if endpoint["group_id"] is not None else None,
                    "createdAt": endpoint["created_at"],
                    "updatedAt": endpoint["updated_at"],
                    "version": current_row["version"] if current_row and current_row["version"] else None,
                    "state": self._state_label(current_state),
                    "error": current_row["down_error"] if current_row else None,
                    "statusCode": current_row["down_status"] if current_row else None,
                    "apiOk": bool(current_row["api_ok"]) if current_row else False,
                    "searchOk": bool(current_row["search_ok"]) if current_row else False,
                    "trackOk": bool(current_row["track_ok"]) if current_row else False,
                    "responseTimeMs": current_row["response_time_ms"] if current_row else None,
                    "emailAlertsEnabled": bool(endpoint["email_alerts_enabled"]),
                    "uptimePercentage": uptime_percentage,
                    "subchecks": endpoint_subchecks,
                    "history": history,
                }
            )

        total_instances = len(endpoints)
        overall_state = "operational" if down_count == 0 else "degraded"
        if total_instances > 0 and down_count == total_instances:
            overall_state = "outage"

        instances.sort(
            key=lambda item: (
                0 if item["apiOk"] else 1,
                -(item["uptimePercentage"] if item["uptimePercentage"] is not None else -1.0),
                self._state_sort_weight(item["state"]),
                item["url"],
            )
        )

        return {
            "lastUpdated": latest_run["last_updated"] if latest_run else None,
            "historyPoints": len(poll_runs),
            "summary": {
                "totalInstances": total_instances,
                "apiCount": api_count,
                "streamingCount": streaming_count,
                "downCount": down_count,
                "state": overall_state,
            },
            "instances": instances,
            "groups": [
                {
                    "id": int(row["id"]),
                    "name": str(row["name"]),
                    "sortOrder": int(row["sort_order"]),
                }
                for row in groups
            ],
        }

    def _classify_row(self, row: sqlite3.Row | None) -> int:
        if row is None:
            return -1
        if row["search_ok"] and row["track_ok"]:
            return STATE_OPERATIONAL
        if row["api_ok"]:
            return STATE_DEGRADED
        return STATE_OUTAGE

    def _state_label(self, state: int) -> str:
        if state == STATE_OPERATIONAL:
            return "operational"
        if state == STATE_DEGRADED:
            return "degraded"
        if state == STATE_OUTAGE:
            return "outage"
        return "unknown"

    def _state_from_result(self, result: dict[str, Any]) -> int:
        if result["search_ok"] and result["track_ok"]:
            return STATE_OPERATIONAL
        if result["api_ok"]:
            return STATE_DEGRADED
        return STATE_OUTAGE

    def _state_sort_weight(self, state: str) -> int:
        if state == "operational":
            return 0
        if state == "degraded":
            return 1
        if state == "outage":
            return 2
        return 3

    def _normalize_endpoint_row(self, row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
        payload = dict(row)
        payload["alerts_enabled"] = bool(payload.get("alerts_enabled", 1))
        payload["email_alerts_enabled"] = bool(payload.get("email_alerts_enabled", 1))
        payload["alert_on_outage"] = bool(payload.get("alert_on_outage", 1))
        payload["alert_on_search"] = bool(
            payload.get("alert_on_search", payload.get("alert_on_degraded", 1))
        )
        payload["alert_on_track"] = bool(
            payload.get("alert_on_track", payload.get("alert_on_degraded", 1))
        )
        payload["alert_on_recovery"] = bool(payload.get("alert_on_recovery", 1))
        payload["kind"] = str(payload.get("kind") or "tidal")
        payload["name"] = payload.get("name") or None
        payload["group_id"] = (
            int(payload["group_id"]) if payload.get("group_id") is not None else None
        )
        payload["request_method"] = str(payload.get("request_method") or "GET")
        payload["expected_status"] = (
            int(payload["expected_status"]) if payload.get("expected_status") is not None else None
        )
        payload["match_type"] = payload.get("match_type") or None
        payload["match_path"] = payload.get("match_path") or None
        payload["match_value"] = payload.get("match_value") or None
        payload["metrics_url"] = payload.get("metrics_url") or None
        payload["metrics_keys"] = payload.get("metrics_keys") or None
        payload["check_interval_seconds"] = (
            int(payload["check_interval_seconds"])
            if payload.get("check_interval_seconds") is not None
            else None
        )
        payload["subchecks"] = payload.get("subchecks") or []
        return payload

    def _clear_all_alert_states_sync(self) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM endpoint_alert_state")
            connection.commit()

    def _build_metrics_summary(
        self,
        endpoint_columns: sqlite3.Row,
        metrics_row: sqlite3.Row | None,
    ) -> dict[str, Any] | None:
        url = endpoint_columns["metrics_url"] if "metrics_url" in endpoint_columns.keys() else None
        keys_raw = endpoint_columns["metrics_keys"] if "metrics_keys" in endpoint_columns.keys() else None
        if not url and metrics_row is None:
            return None
        keys = self._parse_metrics_keys(keys_raw)
        payload: Any = None
        parse_error: str | None = None
        if metrics_row is not None and metrics_row["payload_json"]:
            import json as _json
            try:
                payload = _json.loads(metrics_row["payload_json"])
            except ValueError:
                parse_error = "invalid JSON"
        values: list[dict[str, Any]] = []
        if payload is not None:
            for entry in keys:
                resolved = self._lookup_metrics_path(payload, entry["path"])
                values.append({
                    "label": entry["label"],
                    "path": entry["path"],
                    "value": self._stringify_metric_value(resolved),
                    "found": resolved is not None,
                })
        return {
            "url": url,
            "configuredKeys": keys,
            "values": values,
            "ok": bool(metrics_row["ok"]) if metrics_row is not None else None,
            "statusCode": metrics_row["status_code"] if metrics_row is not None else None,
            "error": metrics_row["error"] if metrics_row is not None else None,
            "fetchedAt": metrics_row["fetched_at"] if metrics_row is not None else None,
            "responseTimeMs": metrics_row["response_time_ms"] if metrics_row is not None else None,
            "hasPayload": payload is not None,
            "parseError": parse_error,
        }

    @staticmethod
    def _parse_metrics_keys(raw: str | None) -> list[dict[str, str]]:
        if not raw:
            return []
        entries: list[dict[str, str]] = []
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            label = ""
            path = line
            lower = line.lower()
            sep_idx = lower.rfind(" as ")
            if sep_idx > 0:
                path = line[:sep_idx].strip()
                label = line[sep_idx + 4 :].strip()
            if not path:
                continue
            if not label:
                tokens = SQLiteStore._tokenize_metrics_path(path)
                last = next((t for t in reversed(tokens) if isinstance(t, str)), None)
                label = last if last else path
            entries.append({"label": label, "path": path})
        return entries

    @staticmethod
    def _tokenize_metrics_path(path: str) -> list[str | int]:
        tokens: list[str | int] = []
        i = 0
        n = len(path)
        buf: list[str] = []

        def flush_key() -> None:
            if buf:
                tokens.append("".join(buf))
                buf.clear()

        while i < n:
            ch = path[i]
            if ch == ".":
                flush_key()
                i += 1
                continue
            if ch == "[":
                flush_key()
                end = path.find("]", i + 1)
                if end == -1:
                    break
                inner = path[i + 1 : end].strip()
                if inner.startswith(("'", '"')) and inner.endswith(("'", '"')) and len(inner) >= 2:
                    tokens.append(inner[1:-1])
                else:
                    try:
                        tokens.append(int(inner))
                    except ValueError:
                        tokens.append(inner)
                i = end + 1
                continue
            buf.append(ch)
            i += 1
        flush_key()
        return tokens

    @staticmethod
    def _lookup_metrics_path(payload: Any, path: str) -> Any:
        tokens = SQLiteStore._tokenize_metrics_path(path)
        current: Any = payload
        for token in tokens:
            if isinstance(token, int):
                if not isinstance(current, list) or token < 0 or token >= len(current):
                    return None
                current = current[token]
                continue
            if isinstance(current, dict):
                if token not in current:
                    return None
                current = current[token]
            elif isinstance(current, list):
                try:
                    idx = int(token)
                except ValueError:
                    return None
                if idx < 0 or idx >= len(current):
                    return None
                current = current[idx]
            else:
                return None
        return current

    @staticmethod
    def _stringify_metric_value(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, str):
            return value
        import json as _json
        try:
            return _json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        except (TypeError, ValueError):
            return str(value)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL;")
        connection.execute("PRAGMA synchronous=NORMAL;")
        connection.execute("PRAGMA foreign_keys=ON;")
        connection.execute("PRAGMA wal_autocheckpoint=1000;")
        return connection

    def _legacy_data_needs_migration(self, connection: sqlite3.Connection) -> bool:
        latest_status_count = connection.execute(
            "SELECT COUNT(*) FROM latest_endpoint_status"
        ).fetchone()[0]
        if latest_status_count > 0:
            return False

        has_legacy_table = connection.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='endpoint_checks'"
        ).fetchone()[0]
        if not has_legacy_table:
            return False

        legacy_count = connection.execute(
            "SELECT COUNT(*) FROM endpoint_checks"
        ).fetchone()[0]
        return legacy_count > 0

    def _migrate_legacy_endpoint_checks(self, connection: sqlite3.Connection) -> None:
        endpoint_id_by_url = {
            row["url"]: row["id"]
            for row in connection.execute(
                "SELECT id, url FROM monitored_endpoints"
            ).fetchall()
        }
        latest_run = connection.execute(
            "SELECT id FROM poll_runs ORDER BY id DESC LIMIT 1"
        ).fetchone()
        legacy_rows = connection.execute(
            """
            SELECT poll_run_id, url, version, api_ok, track_ok, down_status, down_error
            FROM endpoint_checks
            ORDER BY poll_run_id ASC, id ASC
            """
        ).fetchall()

        latest_status_rows = []
        history_rows = []
        history_detail_rows = []
        for row in legacy_rows:
            endpoint_id = endpoint_id_by_url.get(row["url"])
            if endpoint_id is None:
                continue
            history_rows.append(
                (
                    endpoint_id,
                    row["poll_run_id"],
                    self._state_from_result(
                        {
                            "api_ok": bool(row["api_ok"]),
                            "track_ok": bool(row["track_ok"]),
                        }
                    ),
                )
            )
            if row["down_status"] is not None:
                history_detail_rows.append(
                    (
                        endpoint_id,
                        row["poll_run_id"],
                        row["down_status"],
                        row["down_error"],
                    )
                )
            if latest_run and row["poll_run_id"] == latest_run["id"]:
                latest_status_rows.append(
                    (
                        endpoint_id,
                        row["poll_run_id"],
                        row["version"],
                        row["api_ok"],
                        row["track_ok"],
                        row["down_status"],
                        row["down_error"],
                    )
                )

        if history_rows:
            connection.executemany(
                """
                INSERT OR IGNORE INTO endpoint_history (
                    endpoint_id,
                    poll_run_id,
                    state
                ) VALUES (?, ?, ?)
                """,
                history_rows,
            )
        if history_detail_rows:
            connection.executemany(
                """
                INSERT OR REPLACE INTO endpoint_history_detail (
                    endpoint_id,
                    poll_run_id,
                    down_status,
                    down_error
                ) VALUES (?, ?, ?, ?)
                """,
                history_detail_rows,
            )
        if latest_status_rows:
            connection.executemany(
                """
                INSERT OR REPLACE INTO latest_endpoint_status (
                    endpoint_id,
                    poll_run_id,
                    version,
                    api_ok,
                    track_ok,
                    down_status,
                    down_error
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                latest_status_rows,
            )

        connection.execute("DROP TABLE IF EXISTS endpoint_checks")
        connection.execute("DROP INDEX IF EXISTS idx_endpoint_checks_poll_run_id")
        connection.execute("DROP INDEX IF EXISTS idx_endpoint_checks_url")

    def _prune_old_runs(self, connection: sqlite3.Connection) -> None:
        retention = max(
            int(self.settings.history_retention_runs),
            int(self.settings.status_page_history_points),
            1,
        )
        run_ids_to_delete = connection.execute(
            """
            SELECT id
            FROM poll_runs
            WHERE id NOT IN (
                SELECT id
                FROM poll_runs
                ORDER BY id DESC
                LIMIT ?
            )
            """,
            (retention,),
        ).fetchall()
        if run_ids_to_delete:
            connection.executemany(
                "DELETE FROM poll_runs WHERE id = ?",
                [(row["id"],) for row in run_ids_to_delete],
            )
