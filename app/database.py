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

    async def save_snapshot(self, snapshot: dict[str, Any], endpoint_results: list[dict[str, Any]]) -> None:
        await asyncio.to_thread(self._save_snapshot_sync, snapshot, endpoint_results)

    async def list_endpoints(self) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._list_endpoints_sync)

    async def list_endpoint_urls(self) -> list[str]:
        return await asyncio.to_thread(self._list_endpoint_urls_sync)

    async def create_endpoint(
        self,
        url: str,
        alerts_enabled: bool = True,
        alert_on_outage: bool = True,
        alert_on_search: bool = True,
        alert_on_track: bool = True,
        alert_on_recovery: bool = True,
    ) -> dict[str, Any]:
        return await asyncio.to_thread(
            self._create_endpoint_sync,
            url,
            alerts_enabled,
            alert_on_outage,
            alert_on_search,
            alert_on_track,
            alert_on_recovery,
        )

    async def update_endpoint(
        self,
        endpoint_id: int,
        url: str,
        alerts_enabled: bool = True,
        alert_on_outage: bool = True,
        alert_on_search: bool = True,
        alert_on_track: bool = True,
        alert_on_recovery: bool = True,
    ) -> dict[str, Any]:
        return await asyncio.to_thread(
            self._update_endpoint_sync,
            endpoint_id,
            url,
            alerts_enabled,
            alert_on_outage,
            alert_on_search,
            alert_on_track,
            alert_on_recovery,
        )

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

    async def update_endpoint_alerts_enabled(
        self,
        endpoint_id: int,
        alerts_enabled: bool,
    ) -> dict[str, Any]:
        return await asyncio.to_thread(
            self._update_endpoint_alerts_enabled_sync,
            endpoint_id,
            alerts_enabled,
        )

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
                    alert_on_outage INTEGER NOT NULL DEFAULT 1,
                    alert_on_degraded INTEGER NOT NULL DEFAULT 1,
                    alert_on_search INTEGER NOT NULL DEFAULT 1,
                    alert_on_track INTEGER NOT NULL DEFAULT 1,
                    alert_on_recovery INTEGER NOT NULL DEFAULT 1,
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
            if endpoint_count == 0:
                now = self._utc_now()
                connection.executemany(
                    """
                    INSERT INTO monitored_endpoints (
                        url,
                        alerts_enabled,
                        alert_on_outage,
                        alert_on_degraded,
                        alert_on_search,
                        alert_on_track,
                        alert_on_recovery,
                        created_at,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [(url, 1, 1, 1, 1, 1, 1, now, now) for url in self.settings.default_endpoints],
                )
            latest_status_columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info(latest_endpoint_status)").fetchall()
            }
            if "search_ok" not in latest_status_columns:
                connection.execute(
                    "ALTER TABLE latest_endpoint_status ADD COLUMN search_ok INTEGER NOT NULL DEFAULT 0"
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

    def _save_snapshot_sync(self, snapshot: dict[str, Any], endpoint_results: list[dict[str, Any]]) -> None:
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
                    down_error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
                    down_error
                ) VALUES (?, ?, ?, ?)
                """,
                [
                    (
                        endpoint_id_by_url[result["url"]],
                        poll_run_id,
                        result["down_status"],
                        result["down_error"],
                    )
                    for result in endpoint_results
                    if result["down_status"] is not None
                ],
            )
            self._prune_old_runs(connection)
            connection.commit()

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
                       latest_endpoint_status.down_status, latest_endpoint_status.down_error
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
                SELECT id, url, alerts_enabled, alert_on_outage, alert_on_search,
                       alert_on_track,
                       alert_on_recovery, created_at, updated_at
                FROM monitored_endpoints
                ORDER BY id ASC
                """
            ).fetchall()
        return [self._normalize_endpoint_row(row) for row in rows]

    def _list_endpoint_urls_sync(self) -> list[str]:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT url FROM monitored_endpoints ORDER BY id ASC"
            ).fetchall()
        return [row[0] for row in rows]

    def _create_endpoint_sync(
        self,
        url: str,
        alerts_enabled: bool = True,
        alert_on_outage: bool = True,
        alert_on_search: bool = True,
        alert_on_track: bool = True,
        alert_on_recovery: bool = True,
    ) -> dict[str, Any]:
        timestamp = self._utc_now()
        with self._connect() as connection:
            try:
                cursor = connection.execute(
                    """
                    INSERT INTO monitored_endpoints (
                        url,
                        alerts_enabled,
                        alert_on_outage,
                        alert_on_degraded,
                        alert_on_search,
                        alert_on_track,
                        alert_on_recovery,
                        created_at,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        url,
                        1 if alerts_enabled else 0,
                        1 if alert_on_outage else 0,
                        1 if (alert_on_search or alert_on_track) else 0,
                        1 if alert_on_search else 0,
                        1 if alert_on_track else 0,
                        1 if alert_on_recovery else 0,
                        timestamp,
                        timestamp,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ValueError("Endpoint already exists") from exc

            row = connection.execute(
                """
                SELECT id, url, alerts_enabled, alert_on_outage, alert_on_search,
                       alert_on_track,
                       alert_on_recovery, created_at, updated_at
                FROM monitored_endpoints
                WHERE id = ?
                """,
                (cursor.lastrowid,),
            ).fetchone()
            connection.commit()
        return self._normalize_endpoint_row(row)

    def _update_endpoint_sync(
        self,
        endpoint_id: int,
        url: str,
        alerts_enabled: bool = True,
        alert_on_outage: bool = True,
        alert_on_search: bool = True,
        alert_on_track: bool = True,
        alert_on_recovery: bool = True,
    ) -> dict[str, Any]:
        timestamp = self._utc_now()
        with self._connect() as connection:
            try:
                cursor = connection.execute(
                    """
                    UPDATE monitored_endpoints
                    SET url = ?, alerts_enabled = ?, alert_on_outage = ?, alert_on_degraded = ?,
                        alert_on_search = ?, alert_on_track = ?, alert_on_recovery = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        url,
                        1 if alerts_enabled else 0,
                        1 if alert_on_outage else 0,
                        1 if (alert_on_search or alert_on_track) else 0,
                        1 if alert_on_search else 0,
                        1 if alert_on_track else 0,
                        1 if alert_on_recovery else 0,
                        timestamp,
                        endpoint_id,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ValueError("Endpoint already exists") from exc

            if cursor.rowcount == 0:
                raise LookupError("Endpoint not found")

            row = connection.execute(
                """
                SELECT id, url, alerts_enabled, alert_on_outage, alert_on_search,
                       alert_on_track,
                       alert_on_recovery, created_at, updated_at
                FROM monitored_endpoints
                WHERE id = ?
                """,
                (endpoint_id,),
            ).fetchone()
            connection.commit()
        return self._normalize_endpoint_row(row)

    def _update_endpoint_alerts_enabled_sync(
        self,
        endpoint_id: int,
        alerts_enabled: bool,
    ) -> dict[str, Any]:
        timestamp = self._utc_now()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE monitored_endpoints
                SET alerts_enabled = ?, updated_at = ?
                WHERE id = ?
                """,
                (1 if alerts_enabled else 0, timestamp, endpoint_id),
            )

            if cursor.rowcount == 0:
                raise LookupError("Endpoint not found")

            row = connection.execute(
                """
                SELECT id, url, alerts_enabled, alert_on_outage, alert_on_search,
                       alert_on_track,
                       alert_on_recovery, created_at, updated_at
                FROM monitored_endpoints
                WHERE id = ?
                """,
                (endpoint_id,),
            ).fetchone()
            connection.commit()
        return self._normalize_endpoint_row(row)

    def _create_email_subscription_sync(self, endpoint_id: int, email: str) -> dict[str, Any]:
        timestamp = self._utc_now()
        normalized_email = email.strip().lower()
        with self._connect() as connection:
            endpoint = connection.execute(
                """
                SELECT id, url
                FROM monitored_endpoints
                WHERE id = ?
                """,
                (endpoint_id,),
            ).fetchone()
            if endpoint is None:
                raise LookupError("Endpoint not found")

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
                SELECT id, url, created_at, updated_at
                FROM monitored_endpoints
                ORDER BY id ASC
                """
            ).fetchall()
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
                    SELECT endpoint_id, poll_run_id, down_status, down_error
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
                       latest_endpoint_status.down_status, latest_endpoint_status.down_error
                FROM latest_endpoint_status
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
                    }
                )
                if state != -1:
                    known_runs += 1
                if state == STATE_OPERATIONAL:
                    operational_runs += 1

            uptime_percentage = round((operational_runs / known_runs) * 100, 3) if known_runs else None
            instances.append(
                {
                    "id": endpoint["id"],
                    "url": endpoint["url"],
                    "createdAt": endpoint["created_at"],
                    "updatedAt": endpoint["updated_at"],
                    "version": current_row["version"] if current_row and current_row["version"] else None,
                    "state": self._state_label(current_state),
                    "error": current_row["down_error"] if current_row else None,
                    "statusCode": current_row["down_status"] if current_row else None,
                    "apiOk": bool(current_row["api_ok"]) if current_row else False,
                    "searchOk": bool(current_row["search_ok"]) if current_row else False,
                    "trackOk": bool(current_row["track_ok"]) if current_row else False,
                    "uptimePercentage": uptime_percentage,
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
        payload["alert_on_outage"] = bool(payload.get("alert_on_outage", 1))
        payload["alert_on_search"] = bool(
            payload.get("alert_on_search", payload.get("alert_on_degraded", 1))
        )
        payload["alert_on_track"] = bool(
            payload.get("alert_on_track", payload.get("alert_on_degraded", 1))
        )
        payload["alert_on_recovery"] = bool(payload.get("alert_on_recovery", 1))
        return payload

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
        retention = max(int(self.settings.history_retention_runs), 1)
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
