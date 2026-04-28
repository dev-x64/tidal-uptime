from __future__ import annotations

import asyncio
import logging
import smtplib
import ssl
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import formataddr
from typing import Any

import httpx

from app.database import SQLiteStore
from app.reference_api_version import ReferenceApiVersionTracker
from app.settings import Settings

logger = logging.getLogger(__name__)

ALERT_PHASE_CLEAR = "clear"
ALERT_PHASE_FAILING = "failing"
ALERT_PHASE_RECOVERING = "recovering"


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def build_url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


@dataclass(slots=True)
class ProbeFailure(Exception):
    status: int
    error: str


@dataclass(slots=True)
class ProbeIssue:
    probe: str
    status: int
    error: str


@dataclass(slots=True)
class SubcheckResult:
    subcheck_id: int
    label: str
    url: str
    ok: bool
    status: int | None = None
    error: str | None = None
    response_time_ms: int | None = None


@dataclass(slots=True)
class EndpointResult:
    url: str
    kind: str = "tidal"
    version: str | None = None
    api_ok: bool = False
    track_ok: bool = False
    api_issue: ProbeIssue | None = None
    search_issue: ProbeIssue | None = None
    track_issue: ProbeIssue | None = None
    response_time_ms: int | None = None
    subcheck_results: list[SubcheckResult] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.subcheck_results is None:
            self.subcheck_results = []

    @property
    def issues(self) -> tuple[ProbeIssue, ...]:
        issues: list[ProbeIssue] = []
        if self.api_issue is not None:
            issues.append(self.api_issue)
        if self.search_issue is not None:
            issues.append(self.search_issue)
        if self.track_issue is not None:
            issues.append(self.track_issue)
        return tuple(issues)

    @property
    def primary_issue(self) -> ProbeIssue | None:
        for issue in self.issues:
            return issue
        return None


@dataclass(slots=True)
class AlertCondition:
    state: str
    key: str
    summary: str
    issues: tuple[ProbeIssue, ...]


@dataclass(slots=True)
class AlertState:
    phase: str = ALERT_PHASE_CLEAR
    condition_key: str | None = None
    condition_state: str | None = None
    condition_summary: str | None = None
    failure_streak: int = 0
    recovery_streak: int = 0
    last_failure_alert_streak: int = 0
    updated_at: str = ""

    @classmethod
    def from_record(cls, record: dict[str, Any] | None) -> AlertState:
        if record is None:
            return cls(updated_at=utc_timestamp())
        return cls(
            phase=str(record["phase"]),
            condition_key=record["condition_key"],
            condition_state=record["condition_state"],
            condition_summary=record["condition_summary"],
            failure_streak=int(record["failure_streak"]),
            recovery_streak=int(record["recovery_streak"]),
            last_failure_alert_streak=int(record["last_failure_alert_streak"]),
            updated_at=str(record["updated_at"]),
        )

    def to_record(self, endpoint_id: int) -> dict[str, Any]:
        return {
            "endpoint_id": endpoint_id,
            "phase": self.phase,
            "condition_key": self.condition_key,
            "condition_state": self.condition_state,
            "condition_summary": self.condition_summary,
            "failure_streak": self.failure_streak,
            "recovery_streak": self.recovery_streak,
            "last_failure_alert_streak": self.last_failure_alert_streak,
            "updated_at": self.updated_at or utc_timestamp(),
        }


class EndpointMonitor:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.store = SQLiteStore(settings)
        self.reference_api_version = ReferenceApiVersionTracker(settings)
        self._snapshot: dict[str, Any] = {
            "lastUpdated": utc_timestamp(),
            "api": [],
            "streaming": [],
            "down": [],
        }
        self._lock = asyncio.Lock()
        self._refresh_lock = asyncio.Lock()
        self._refresh_task_lock = asyncio.Lock()
        self._task: asyncio.Task[None] | None = None
        self._manual_refresh_task: asyncio.Task[None] | None = None
        self._background_tasks: set[asyncio.Task[None]] = set()
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        await self.store.initialize()
        await self.reference_api_version.start()
        stored_snapshot = await self.store.load_latest_snapshot()
        if stored_snapshot is not None:
            async with self._lock:
                self._snapshot = stored_snapshot
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run_forever())
        initial_task = asyncio.create_task(self.refresh())
        self._background_tasks.add(initial_task)
        initial_task.add_done_callback(self._finalize_background_task)

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task is not None:
            await self._task
        if self._manual_refresh_task is not None:
            await self._manual_refresh_task
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)

    async def get_snapshot(self) -> dict[str, Any]:
        async with self._lock:
            return {
                "lastUpdated": self._snapshot["lastUpdated"],
                "api": list(self._snapshot["api"]),
                "streaming": list(self._snapshot["streaming"]),
                "down": list(self._snapshot["down"]),
            }

    async def list_endpoints(self) -> list[dict[str, Any]]:
        return await self.store.list_endpoints()

    async def list_groups(self) -> list[dict[str, Any]]:
        return await self.store.list_groups()

    async def create_group(self, name: str, sort_order: int = 0) -> dict[str, Any]:
        return await self.store.create_group(name, sort_order)

    async def update_group(self, group_id: int, name: str, sort_order: int) -> dict[str, Any]:
        return await self.store.update_group(group_id, name, sort_order)

    async def delete_group(self, group_id: int) -> None:
        await self.store.delete_group(group_id)

    async def replace_subchecks_for_endpoint(
        self,
        endpoint_id: int,
        subchecks: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        result = await self.store.replace_subchecks_for_endpoint(endpoint_id, subchecks)
        await self.store.clear_alert_state(endpoint_id)
        return result

    async def create_email_subscription(self, endpoint_id: int, email: str) -> dict[str, Any]:
        return await self.store.create_email_subscription(endpoint_id, email)

    async def list_email_subscriptions(self) -> list[dict[str, Any]]:
        return await self.store.list_email_subscriptions()

    async def delete_email_subscription(self, subscription_id: int) -> None:
        await self.store.delete_email_subscription(subscription_id)

    async def get_status_page_data(self, history_limit: int | None = None) -> dict[str, Any]:
        effective_history_limit = history_limit or self.settings.status_page_history_points
        payload = await self.store.get_status_page_data(effective_history_limit)
        payload["referenceApiVersion"] = await self.reference_api_version.get_payload()
        payload["refreshInProgress"] = self.is_refresh_in_progress()
        payload["historyWindowPoints"] = effective_history_limit
        payload["historyWindowHours"] = self.settings.status_page_window_hours
        payload["checkIntervalSeconds"] = self.settings.check_interval_seconds
        payload["emailAlertingEnabled"] = self.settings.email_alerting_enabled
        return payload

    def is_refresh_in_progress(self) -> bool:
        return self._refresh_lock.locked() or (
            self._manual_refresh_task is not None and not self._manual_refresh_task.done()
        )

    async def trigger_refresh(self) -> bool:
        async with self._refresh_task_lock:
            if self.is_refresh_in_progress():
                return False
            self._manual_refresh_task = asyncio.create_task(self.refresh())
            self._manual_refresh_task.add_done_callback(self._finalize_manual_refresh_task)
            return True

    async def create_endpoint(
        self,
        payload: dict[str, Any],
        subchecks: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        endpoint = await self.store.create_endpoint(payload)
        if subchecks is not None:
            await self.store.replace_subchecks_for_endpoint(int(endpoint["id"]), subchecks)
            endpoint["subchecks"] = await self._fetch_subchecks(int(endpoint["id"]))
        self._spawn_background_refresh([endpoint])
        return endpoint

    async def update_endpoint(
        self,
        endpoint_id: int,
        payload: dict[str, Any],
        subchecks: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        endpoint = await self.store.update_endpoint(endpoint_id, payload)
        if subchecks is not None:
            await self.store.replace_subchecks_for_endpoint(endpoint_id, subchecks)
            endpoint["subchecks"] = await self._fetch_subchecks(endpoint_id)
        await self.store.clear_alert_state(endpoint_id)
        self._spawn_background_refresh([endpoint])
        return endpoint

    def _spawn_background_refresh(self, endpoints: list[dict[str, Any]]) -> None:
        if not endpoints:
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        task = loop.create_task(self._refresh_selected_endpoints(endpoints))
        self._background_tasks.add(task)
        task.add_done_callback(self._finalize_background_task)

    def _finalize_background_task(self, task: asyncio.Task[None]) -> None:
        self._background_tasks.discard(task)
        try:
            task.result()
        except Exception:
            logger.exception("Background endpoint refresh failed")

    async def _fetch_subchecks(self, endpoint_id: int) -> list[dict[str, Any]]:
        all_endpoints = await self.store.list_endpoints()
        for endpoint in all_endpoints:
            if int(endpoint["id"]) == endpoint_id:
                return endpoint.get("subchecks") or []
        return []

    async def update_all_endpoint_settings(
        self,
        email_alerts_enabled: bool,
        alert_on_outage: bool,
        alert_on_search: bool,
        alert_on_track: bool,
        alert_on_recovery: bool,
    ) -> int:
        updated = await self.store.update_all_endpoint_alert_settings(
            email_alerts_enabled,
            alert_on_outage,
            alert_on_search,
            alert_on_track,
            alert_on_recovery,
        )
        await self.store.clear_all_alert_states()
        return updated

    async def delete_endpoint(self, endpoint_id: int) -> None:
        await self.store.delete_endpoint(endpoint_id)
        await self._reload_snapshot_from_store()

    def _finalize_manual_refresh_task(self, task: asyncio.Task[None]) -> None:
        if self._manual_refresh_task is task:
            self._manual_refresh_task = None
        try:
            task.result()
        except Exception:
            logger.exception("Background refresh failed")

    async def _run_forever(self) -> None:
        while not self._stop_event.is_set():
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self.settings.check_interval_seconds,
                )
            except asyncio.TimeoutError:
                await self.refresh()

    async def refresh(self) -> None:
        async with self._refresh_lock:
            endpoints = await self.store.list_endpoints()
            logger.info("Refreshing monitor snapshot for %s endpoints", len(endpoints))

            timeout = httpx.Timeout(self.settings.request_timeout_seconds)
            limits = httpx.Limits(max_connections=25, max_keepalive_connections=10)
            headers = {"User-Agent": self.settings.user_agent, "Accept": "application/json"}

            async with httpx.AsyncClient(
                timeout=timeout,
                headers=headers,
                limits=limits,
                follow_redirects=True,
            ) as client:
                await self.reference_api_version.ensure_fresh(client)
                results = await asyncio.gather(
                    *(self._check_endpoint(client, endpoint) for endpoint in endpoints)
                )

                last_updated = utc_timestamp()
                persisted_results = [
                    self._result_to_persisted_payload(result)
                    for result in results
                ]
                snapshot = self._build_snapshot_for_status_json(
                    last_updated, endpoints, results
                )

                alert_states = await self.store.load_alert_states()
                email_subscriptions = await self.store.load_email_subscriptions_by_endpoint()
                persisted_alert_states = await self._process_alerts(
                    client=client,
                    endpoints=endpoints,
                    results=results,
                    alert_states=alert_states,
                    email_subscriptions=email_subscriptions,
                )
                await self.store.save_alert_states(persisted_alert_states)

            poll_run_id = await self.store.save_snapshot(snapshot, persisted_results)
            if poll_run_id is not None:
                subcheck_payload = self._collect_subcheck_results(results)
                if subcheck_payload:
                    await self.store.save_subcheck_results(poll_run_id, subcheck_payload)

            async with self._lock:
                self._snapshot = snapshot

    def _collect_subcheck_results(
        self, results: list[EndpointResult]
    ) -> list[dict[str, Any]]:
        payload: list[dict[str, Any]] = []
        for result in results:
            for sub in result.subcheck_results:
                payload.append(
                    {
                        "subcheck_id": sub.subcheck_id,
                        "ok": sub.ok,
                        "status_code": sub.status,
                        "error": sub.error,
                        "response_time_ms": sub.response_time_ms,
                    }
                )
        return payload

    def _build_snapshot_for_status_json(
        self,
        last_updated: str,
        endpoints: list[dict[str, Any]],
        results: list[EndpointResult],
    ) -> dict[str, Any]:
        snapshot: dict[str, Any] = {
            "lastUpdated": last_updated,
            "api": [],
            "streaming": [],
            "down": [],
        }
        endpoints_by_url = {str(endpoint["url"]): endpoint for endpoint in endpoints}
        for result in results:
            endpoint = endpoints_by_url.get(result.url)
            if endpoint is None or str(endpoint.get("kind") or "tidal") != "tidal":
                continue
            if result.api_ok and result.version:
                snapshot["api"].append({"url": result.url, "version": result.version})
            if result.track_ok and result.version:
                snapshot["streaming"].append({"url": result.url, "version": result.version})
            if result.primary_issue is not None:
                snapshot["down"].append(
                    {
                        "url": result.url,
                        "status": result.primary_issue.status,
                        "error": result.primary_issue.error,
                    }
                )
        return snapshot

    async def _refresh_selected_endpoints(self, selected_endpoints: list[dict[str, Any]]) -> None:
        async with self._refresh_lock:
            all_endpoints = await self.store.list_endpoints()
            endpoints_by_id = {int(endpoint["id"]): endpoint for endpoint in all_endpoints}
            selected_endpoint_ids = {int(endpoint["id"]) for endpoint in selected_endpoints}
            latest_results_by_id = await self.store.load_latest_endpoint_results()

            timeout = httpx.Timeout(self.settings.request_timeout_seconds)
            limits = httpx.Limits(max_connections=25, max_keepalive_connections=10)
            headers = {"User-Agent": self.settings.user_agent, "Accept": "application/json"}

            async with httpx.AsyncClient(
                timeout=timeout,
                headers=headers,
                limits=limits,
                follow_redirects=True,
            ) as client:
                await self.reference_api_version.ensure_fresh(client)
                full_endpoints = [
                    endpoints_by_id[int(endpoint["id"])]
                    for endpoint in selected_endpoints
                    if int(endpoint["id"]) in endpoints_by_id
                ]
                selected_results = await asyncio.gather(
                    *(self._check_endpoint(client, endpoint) for endpoint in full_endpoints)
                )

                for endpoint, result in zip(full_endpoints, selected_results):
                    latest_results_by_id[int(endpoint["id"])] = self._result_to_persisted_payload(result)

                last_updated = utc_timestamp()
                persisted_results = [
                    {
                        **result,
                        "url": str(endpoint["url"]),
                    }
                    for endpoint in all_endpoints
                    if (result := latest_results_by_id.get(int(endpoint["id"]))) is not None
                ]
                snapshot = self._build_snapshot_from_persisted_results(
                    last_updated, all_endpoints, persisted_results
                )

                alert_states = await self.store.load_alert_states()
                email_subscriptions = await self.store.load_email_subscriptions_by_endpoint()
                persisted_alert_states = await self._process_alerts(
                    client=client,
                    endpoints=full_endpoints,
                    results=selected_results,
                    alert_states=alert_states,
                    email_subscriptions=email_subscriptions,
                )
                await self.store.save_alert_states(persisted_alert_states)

            poll_run_id = await self.store.save_snapshot(snapshot, persisted_results)
            if poll_run_id is not None:
                subcheck_payload = self._collect_subcheck_results(selected_results)
                if subcheck_payload:
                    await self.store.save_subcheck_results(poll_run_id, subcheck_payload)

            async with self._lock:
                self._snapshot = snapshot

    async def _reload_snapshot_from_store(self) -> None:
        stored_snapshot = await self.store.load_latest_snapshot()
        snapshot = stored_snapshot or {
            "lastUpdated": utc_timestamp(),
            "api": [],
            "streaming": [],
            "down": [],
        }
        async with self._lock:
            self._snapshot = snapshot

    def _build_snapshot_from_persisted_results(
        self,
        last_updated: str,
        endpoints: list[dict[str, Any]],
        persisted_results: list[dict[str, Any]],
    ) -> dict[str, Any]:
        snapshot = {
            "lastUpdated": last_updated,
            "api": [],
            "streaming": [],
            "down": [],
        }
        kind_by_url = {
            str(endpoint["url"]): str(endpoint.get("kind") or "tidal")
            for endpoint in endpoints
        }
        for result in persisted_results:
            if kind_by_url.get(result["url"]) != "tidal":
                continue
            if result["api_ok"] and result["version"]:
                snapshot["api"].append({"url": result["url"], "version": result["version"]})
            if result["track_ok"] and result["version"]:
                snapshot["streaming"].append({"url": result["url"], "version": result["version"]})
            if result["down_status"] is not None:
                snapshot["down"].append(
                    {
                        "url": result["url"],
                        "status": result["down_status"],
                        "error": result["down_error"],
                    }
                )

        return snapshot

    def _result_to_persisted_payload(self, result: EndpointResult) -> dict[str, Any]:
        primary_issue = result.primary_issue
        return {
            "url": result.url,
            "version": result.version,
            "api_ok": result.api_ok,
            "search_ok": result.api_ok and result.search_issue is None,
            "track_ok": result.track_ok,
            "down_status": primary_issue.status if primary_issue else None,
            "down_error": primary_issue.error if primary_issue else None,
            "response_time_ms": result.response_time_ms,
        }

    async def _check_endpoint(
        self, client: httpx.AsyncClient, endpoint: dict[str, Any]
    ) -> EndpointResult:
        kind = str(endpoint.get("kind") or "tidal")
        if kind == "http":
            return await self._check_endpoint_http(client, endpoint)
        return await self._check_endpoint_tidal(client, endpoint)

    PROBE_GAP_SECONDS = 1.0

    async def _check_endpoint_tidal(
        self, client: httpx.AsyncClient, endpoint: dict[str, Any]
    ) -> EndpointResult:
        base_url = str(endpoint["url"])

        start = time.perf_counter()
        try:
            version = await self._check_root(client, base_url)
        except ProbeFailure as failure:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            await asyncio.sleep(self.PROBE_GAP_SECONDS)
            subcheck_results = await self._run_subchecks_sequential(client, endpoint)
            return EndpointResult(
                url=base_url,
                kind="tidal",
                api_issue=ProbeIssue(probe="api", status=failure.status, error=failure.error),
                response_time_ms=elapsed_ms,
                subcheck_results=subcheck_results,
            )
        elapsed_ms = int((time.perf_counter() - start) * 1000)

        await asyncio.sleep(self.PROBE_GAP_SECONDS)
        try:
            await self._check_search(client, base_url)
            search_issue: ProbeIssue | None = None
        except ProbeFailure as failure:
            search_issue = ProbeIssue(probe="search", status=failure.status, error=failure.error)

        await asyncio.sleep(self.PROBE_GAP_SECONDS)
        try:
            await self._check_track(client, base_url)
            track_issue: ProbeIssue | None = None
            track_ok = True
        except ProbeFailure as failure:
            track_issue = ProbeIssue(probe="track", status=failure.status, error=failure.error)
            track_ok = False

        subcheck_results = await self._run_subchecks_sequential(
            client, endpoint, gap_before=True
        )

        return EndpointResult(
            url=base_url,
            kind="tidal",
            version=version,
            api_ok=True,
            track_ok=track_ok,
            search_issue=search_issue,
            track_issue=track_issue,
            response_time_ms=elapsed_ms,
            subcheck_results=subcheck_results,
        )

    async def _check_endpoint_http(
        self, client: httpx.AsyncClient, endpoint: dict[str, Any]
    ) -> EndpointResult:
        url = str(endpoint["url"])
        method = str(endpoint.get("request_method") or "GET")
        expected_status = endpoint.get("expected_status")
        match_type = endpoint.get("match_type")
        match_path = endpoint.get("match_path")
        match_value = endpoint.get("match_value")

        primary_failure, primary_elapsed_ms = await self._run_match_check(
            client=client,
            url=url,
            method=method,
            expected_status=expected_status,
            match_type=match_type,
            match_path=match_path,
            match_value=match_value,
            error_label="Check failed",
        )
        subcheck_results = await self._run_subchecks_sequential(
            client, endpoint, gap_before=True
        )
        await self._fetch_and_store_metrics(client, endpoint)

        any_subcheck_failure = any(not item.ok for item in subcheck_results)

        if primary_failure is not None:
            return EndpointResult(
                url=url,
                kind="http",
                api_issue=ProbeIssue(
                    probe="api", status=primary_failure.status, error=primary_failure.error
                ),
                response_time_ms=primary_elapsed_ms,
                subcheck_results=subcheck_results,
            )

        return EndpointResult(
            url=url,
            kind="http",
            version=None,
            api_ok=True,
            track_ok=not any_subcheck_failure,
            search_issue=(
                ProbeIssue(probe="search", status=502, error="Sub-check failed")
                if any_subcheck_failure
                else None
            ),
            response_time_ms=primary_elapsed_ms,
            subcheck_results=subcheck_results,
        )

    async def _fetch_and_store_metrics(
        self, client: httpx.AsyncClient, endpoint: dict[str, Any]
    ) -> None:
        metrics_url = (endpoint.get("metrics_url") or "").strip()
        if not metrics_url:
            return
        await asyncio.sleep(self.PROBE_GAP_SECONDS)
        start = time.perf_counter()
        record: dict[str, Any] = {
            "fetched_at": utc_timestamp(),
            "ok": False,
            "status_code": None,
            "error": None,
            "payload_json": None,
            "response_time_ms": None,
        }
        try:
            response = await client.get(metrics_url)
        except httpx.TimeoutException:
            record["response_time_ms"] = int((time.perf_counter() - start) * 1000)
            record["error"] = "timeout"
        except httpx.RequestError as exc:
            record["response_time_ms"] = int((time.perf_counter() - start) * 1000)
            record["error"] = exc.__class__.__name__
        else:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            record["response_time_ms"] = elapsed_ms
            record["status_code"] = int(response.status_code)
            text = response.text
            if response.status_code >= 400:
                record["error"] = f"HTTP {response.status_code}"
            else:
                record["ok"] = True
            record["payload_json"] = text[: self.settings.metrics_max_payload_bytes]
        try:
            await self.store.save_endpoint_metrics(int(endpoint["id"]), record)
        except Exception:
            logger.exception("Failed to persist metrics for endpoint %s", endpoint.get("id"))

    async def _run_subchecks_sequential(
        self,
        client: httpx.AsyncClient,
        endpoint: dict[str, Any],
        gap_before: bool = False,
    ) -> list[SubcheckResult]:
        subchecks = endpoint.get("subchecks") or []
        if not subchecks:
            return []
        results: list[SubcheckResult] = []
        for index, sub in enumerate(subchecks):
            if gap_before or index > 0:
                await asyncio.sleep(self.PROBE_GAP_SECONDS)
            results.append(await self._run_single_subcheck(client, sub))
        return results

    async def _run_subchecks(
        self, client: httpx.AsyncClient, endpoint: dict[str, Any]
    ) -> list[SubcheckResult]:
        subchecks = endpoint.get("subchecks") or []
        if not subchecks:
            return []
        results = await asyncio.gather(
            *(self._run_single_subcheck(client, sub) for sub in subchecks)
        )
        return list(results)

    async def _run_single_subcheck(
        self, client: httpx.AsyncClient, sub: dict[str, Any]
    ) -> SubcheckResult:
        url = str(sub.get("url") or "")
        label = str(sub.get("label") or url)
        if not url:
            return SubcheckResult(
                subcheck_id=int(sub["id"]),
                label=label,
                url=url,
                ok=False,
                status=400,
                error="missing url",
            )
        failure, elapsed_ms = await self._run_match_check(
            client=client,
            url=url,
            method=str(sub.get("request_method") or "GET"),
            expected_status=sub.get("expected_status"),
            match_type=sub.get("match_type"),
            match_path=sub.get("match_path"),
            match_value=sub.get("match_value"),
            error_label=f"{label} failed",
        )
        if failure is None:
            return SubcheckResult(
                subcheck_id=int(sub["id"]),
                label=label,
                url=url,
                ok=True,
                response_time_ms=elapsed_ms,
            )
        return SubcheckResult(
            subcheck_id=int(sub["id"]),
            label=label,
            url=url,
            ok=False,
            status=failure.status,
            error=failure.error,
            response_time_ms=elapsed_ms,
        )

    async def _run_match_check(
        self,
        *,
        client: httpx.AsyncClient,
        url: str,
        method: str,
        expected_status: int | None,
        match_type: str | None,
        match_path: str | None,
        match_value: str | None,
        error_label: str,
    ) -> tuple[ProbeFailure | None, int | None]:
        start = time.perf_counter()
        try:
            response = await client.request(method.upper(), url)
        except httpx.TimeoutException:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            return ProbeFailure(status=504, error=f"{error_label}: timeout"), elapsed_ms
        except httpx.RequestError as exc:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            return (
                ProbeFailure(status=503, error=f"{error_label}: {exc.__class__.__name__}"),
                elapsed_ms,
            )
        elapsed_ms = int((time.perf_counter() - start) * 1000)

        if expected_status is not None:
            if int(response.status_code) != int(expected_status):
                return (
                    ProbeFailure(
                        status=response.status_code,
                        error=f"expected status {expected_status}, got {response.status_code}",
                    ),
                    elapsed_ms,
                )
        else:
            if response.status_code >= 400:
                detail = self._extract_error_message(response, fallback=error_label)
                return ProbeFailure(status=response.status_code, error=detail), elapsed_ms

        normalized_match = (match_type or "").strip().lower() or None
        if normalized_match in (None, "status"):
            return None, elapsed_ms

        body_text = response.text
        if normalized_match == "contains":
            needle = (match_value or "")
            if not needle:
                return None, elapsed_ms
            if needle not in body_text:
                return (
                    ProbeFailure(status=422, error=f"body missing '{needle[:40]}'"),
                    elapsed_ms,
                )
            return None, elapsed_ms

        try:
            payload = response.json()
        except ValueError:
            return ProbeFailure(status=502, error="invalid JSON"), elapsed_ms

        path = (match_path or "").strip()
        value = self._json_path_lookup(payload, path) if path else payload
        if normalized_match == "json_key":
            if value is None:
                return (
                    ProbeFailure(status=422, error=f"missing key '{path or '<root>'}'"),
                    elapsed_ms,
                )
            if isinstance(value, (list, dict)) and not value:
                return (
                    ProbeFailure(status=422, error=f"empty value at '{path or '<root>'}'"),
                    elapsed_ms,
                )
            return None, elapsed_ms
        if normalized_match == "json_equals":
            expected_raw = match_value or ""
            actual_str = str(value) if value is not None else ""
            if actual_str != expected_raw:
                return (
                    ProbeFailure(
                        status=422,
                        error=f"{path or '<root>'}={actual_str[:40]} (expected {expected_raw[:40]})",
                    ),
                    elapsed_ms,
                )
            return None, elapsed_ms
        return None, elapsed_ms

    def _json_path_lookup(self, payload: Any, path: str) -> Any:
        tokens = self._tokenize_json_path(path)
        if tokens is None:
            return None
        current: Any = payload
        for token in tokens:
            if isinstance(token, int):
                if not isinstance(current, list):
                    return None
                if token < 0 or token >= len(current):
                    return None
                current = current[token]
                continue
            if isinstance(current, dict):
                if token not in current:
                    return None
                current = current[token]
            elif isinstance(current, list):
                try:
                    index = int(token)
                except ValueError:
                    return None
                if index < 0 or index >= len(current):
                    return None
                current = current[index]
            else:
                return None
        return current

    @staticmethod
    def _tokenize_json_path(path: str) -> list[str | int] | None:
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
                    return None
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

    async def _check_root(self, client: httpx.AsyncClient, base_url: str) -> str:
        payload = await self._request_json(
            client=client,
            url=build_url(base_url, "/"),
            error_label="API unreachable",
        )
        version = str(payload.get("version", "")).strip()
        if not version:
            raise ProbeFailure(status=502, error="API unreachable")
        return version

    async def _check_search(self, client: httpx.AsyncClient, base_url: str) -> list[dict[str, Any]]:
        payload = await self._request_json(
            client=client,
            url=build_url(base_url, "/search/"),
            params={"s": self.settings.search_query},
            error_label="Search unreachable",
        )
        data = payload.get("data")
        items = data.get("items") if isinstance(data, dict) else None
        if not isinstance(items, list) or not items:
            raise ProbeFailure(status=502, error="Search unreachable")
        return [item for item in items if isinstance(item, dict)]

    async def _check_track(
        self,
        client: httpx.AsyncClient,
        base_url: str,
    ) -> None:
        max_attempts = min(len(self.settings.probe_track_ids), self.settings.max_track_retries + 1)
        last_failure: ProbeFailure | None = None

        for track_id in self.settings.probe_track_ids[:max_attempts]:
            try:
                await self._check_single_track(client, base_url, str(track_id))
                return
            except ProbeFailure as failure:
                last_failure = failure

        if last_failure is not None:
            raise last_failure

        raise ProbeFailure(status=502, error="Track unreachable")

    async def _check_single_track(
        self,
        client: httpx.AsyncClient,
        base_url: str,
        track_id: str,
    ) -> None:
        last_failure: ProbeFailure | None = None

        for params in ({"id": track_id, "quality": "HIGH"}, {"id": track_id}):
            try:
                payload = await self._request_json(
                    client=client,
                    url=build_url(base_url, "/track/"),
                    params=params,
                    error_label="Track unreachable",
                )
            except ProbeFailure as failure:
                last_failure = failure
                continue

            data = payload.get("data")
            manifest_hash = data.get("manifestHash") if isinstance(data, dict) else None
            manifest = data.get("manifest") if isinstance(data, dict) else None
            asset_presentation = data.get("assetPresentation") if isinstance(data, dict) else None
            if str(asset_presentation).upper() == "PREVIEW":
                last_failure = ProbeFailure(status=402, error="Preview only (premium expired)")
                continue
            if manifest_hash and manifest:
                return

            last_failure = ProbeFailure(status=502, error="Track unreachable")

        raise last_failure or ProbeFailure(status=502, error="Track unreachable")

    async def _request_json(
        self,
        client: httpx.AsyncClient,
        url: str,
        error_label: str,
        params: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        try:
            response = await client.get(url, params=params)
        except httpx.TimeoutException as exc:
            raise ProbeFailure(status=504, error=error_label) from exc
        except httpx.RequestError as exc:
            raise ProbeFailure(status=503, error=error_label) from exc

        if response.status_code >= 400:
            raise ProbeFailure(
                status=response.status_code,
                error=self._extract_error_message(response, fallback=error_label),
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise ProbeFailure(status=502, error=error_label) from exc

        if not isinstance(payload, dict):
            raise ProbeFailure(status=502, error=error_label)

        return payload

    def _extract_error_message(self, response: httpx.Response, fallback: str) -> str:
        try:
            payload = response.json()
        except ValueError:
            return fallback

        if not isinstance(payload, dict):
            return fallback

        detail = payload.get("detail")
        if not isinstance(detail, str) or not detail.strip():
            return fallback

        if "Token refresh failed" in detail:
            return "Token refresh failed"

        return detail.strip()

    async def _process_alerts(
        self,
        client: httpx.AsyncClient,
        endpoints: list[dict[str, Any]],
        results: list[EndpointResult],
        alert_states: dict[int, dict[str, Any]],
        email_subscriptions: dict[int, list[str]],
    ) -> list[dict[str, Any]]:
        results_by_url = {result.url: result for result in results}
        persisted_states: list[dict[str, Any]] = []

        for endpoint in endpoints:
            endpoint_id = int(endpoint["id"])
            url = str(endpoint["url"])
            current_state = AlertState.from_record(alert_states.get(endpoint_id))
            endpoint_email_recipients = email_subscriptions.get(endpoint_id, [])
            email_channel_active = (
                bool(endpoint_email_recipients)
                and self.settings.email_alerting_enabled
                and bool(endpoint.get("email_alerts_enabled", True))
            )
            result = results_by_url.get(url)
            if not email_channel_active:
                persisted_states.append(self._clear_alert_state(utc_timestamp()).to_record(endpoint_id))
                continue
            condition = (
                self._build_alert_condition(endpoint, result)
                if result is not None
                else None
            )
            updated_state = await self._advance_alert_state(
                url=url,
                state=current_state,
                condition=condition,
                email_recipients=endpoint_email_recipients,
                send_failure_alert=(
                    condition is not None
                    and self._endpoint_allows_failure_alert(endpoint, condition)
                ),
                send_recovery_alert=self._endpoint_allows_recovery_alert(endpoint),
            )
            persisted_states.append(updated_state.to_record(endpoint_id))

        return persisted_states

    async def _advance_alert_state(
        self,
        url: str,
        state: AlertState,
        condition: AlertCondition | None,
        email_recipients: list[str],
        send_failure_alert: bool,
        send_recovery_alert: bool,
    ) -> AlertState:
        now = utc_timestamp()
        failure_threshold = max(int(self.settings.alert_failure_streak), 1)
        recovery_threshold = max(int(self.settings.alert_recovery_streak), 1)

        if condition is not None:
            if state.phase == ALERT_PHASE_FAILING:
                state.failure_streak += 1
            elif state.phase == ALERT_PHASE_RECOVERING:
                state.phase = ALERT_PHASE_FAILING
                state.recovery_streak = 0
                state.failure_streak = 1
            else:
                state.phase = ALERT_PHASE_FAILING
                state.failure_streak = 1
                state.recovery_streak = 0

            state.condition_key = condition.key
            state.condition_state = condition.state
            state.condition_summary = condition.summary

            if (
                send_failure_alert
                and state.last_failure_alert_streak == 0
                and state.failure_streak >= failure_threshold
            ):
                email_subject, email_body, email_html_body = self._build_failure_alert_email(
                    url=url,
                    condition=condition,
                    failure_streak=state.failure_streak,
                    timestamp=now,
                )
                if await self._send_email_alert(
                    email_recipients,
                    email_subject,
                    email_body,
                    email_html_body,
                ):
                    state.last_failure_alert_streak = state.failure_streak

            state.updated_at = now
            return state

        if state.phase == ALERT_PHASE_FAILING:
            if state.last_failure_alert_streak > 0 and send_recovery_alert:
                state.phase = ALERT_PHASE_RECOVERING
                state.failure_streak = 0
                state.recovery_streak = 1
                state.updated_at = now
                if state.recovery_streak >= recovery_threshold:
                    email_subject, email_body, email_html_body = self._build_recovery_alert_email(
                        url=url,
                        state=state,
                        recovery_streak=state.recovery_streak,
                        timestamp=now,
                    )
                    if await self._send_email_alert(
                        email_recipients,
                        email_subject,
                        email_body,
                        email_html_body,
                    ):
                        return self._clear_alert_state(now)
                return state
            return self._clear_alert_state(now)

        if state.phase == ALERT_PHASE_RECOVERING:
            state.recovery_streak += 1
            state.updated_at = now
            if state.recovery_streak >= recovery_threshold:
                email_subject, email_body, email_html_body = self._build_recovery_alert_email(
                    url=url,
                    state=state,
                    recovery_streak=state.recovery_streak,
                    timestamp=now,
                )
                if await self._send_email_alert(
                    email_recipients,
                    email_subject,
                    email_body,
                    email_html_body,
                ):
                    return self._clear_alert_state(now)
            return state

        return self._clear_alert_state(now)

    def _build_alert_condition(
        self,
        endpoint: dict[str, Any],
        result: EndpointResult | None,
    ) -> AlertCondition | None:
        if result is None:
            return None

        allowed_probes = set(self.settings.alert_trigger_probes)
        allowed_states = set(self.settings.alert_trigger_states)
        filtered_issues = tuple(
            issue
            for issue in result.issues
            if issue.probe in allowed_probes and self._endpoint_allows_probe_alert(endpoint, issue.probe)
        )

        if not filtered_issues:
            return None

        state = "outage" if any(issue.probe == "api" for issue in filtered_issues) else "degraded"
        if state not in allowed_states:
            return None

        key = f"{state}|{','.join(f'{issue.probe}:{issue.status}' for issue in filtered_issues)}"
        summary = ", ".join(self._format_issue(issue) for issue in filtered_issues)
        return AlertCondition(state=state, key=key, summary=summary, issues=filtered_issues)

    def _build_failure_alert_email(
        self,
        url: str,
        condition: AlertCondition,
        failure_streak: int,
        timestamp: str,
    ) -> tuple[str, str, str]:
        endpoint_label = self._format_endpoint_display(url)
        state_label = self._format_state_label(condition.state)
        subject = f"[Tidal Uptime] {state_label}: {endpoint_label}"
        text_body = (
            f"{state_label} detected\n\n"
            f"Endpoint: {endpoint_label}\n"
            f"State: {state_label}\n"
            f"Checks:\n{self._format_issues_text(condition.issues)}\n"
            f"Failed polls: {failure_streak} in a row\n"
            f"Time: {timestamp}"
        )
        html_body = self._build_alert_email_html(
            title=f"{state_label} detected",
            accent_color="#ff6b6b" if condition.state == "outage" else "#e3b341",
            badge_label=state_label,
            endpoint_label=endpoint_label,
            rows=(
                ("State", state_label),
                ("Checks", self._format_issues_html(condition.issues)),
                ("Failed polls", f"{failure_streak} in a row"),
                ("Time", timestamp),
            ),
        )
        return subject, text_body, html_body

    def _build_recovery_alert_email(
        self,
        url: str,
        state: AlertState,
        recovery_streak: int,
        timestamp: str,
    ) -> tuple[str, str, str]:
        endpoint_label = self._format_endpoint_display(url)
        previous_state = self._format_state_label(state.condition_state or "degraded")
        subject = f"[Tidal Uptime] Recovery: {endpoint_label}"
        text_body = (
            f"API recovered\n\n"
            f"Endpoint: {endpoint_label}\n"
            f"Recovered from: {previous_state}\n"
            f"Previous checks:\n{self._format_previous_summary_text(state.condition_summary)}\n"
            f"Successful polls: {recovery_streak} in a row\n"
            f"Time: {timestamp}"
        )
        html_body = self._build_alert_email_html(
            title="API recovered",
            accent_color="#36c26d",
            badge_label="Recovery",
            endpoint_label=endpoint_label,
            rows=(
                ("Recovered from", previous_state),
                ("Previous checks", self._format_previous_summary_html(state.condition_summary)),
                ("Successful polls", f"{recovery_streak} in a row"),
                ("Time", timestamp),
            ),
        )
        return subject, text_body, html_body

    async def _send_email_alert(
        self,
        recipients: list[str],
        subject: str,
        body: str,
        html_body: str,
    ) -> bool:
        if not recipients or not self.settings.email_alerting_enabled:
            return False

        try:
            await asyncio.to_thread(
                self._send_email_alert_sync,
                recipients,
                subject,
                body,
                html_body,
            )
        except Exception:
            logger.exception("Failed to send email alert")
            return False
        return True

    def _send_email_alert_sync(
        self,
        recipients: list[str],
        subject: str,
        body: str,
        html_body: str,
    ) -> None:
        from_address = self.settings.smtp_from_email
        host = self.settings.smtp_host
        if not from_address or not host:
            raise RuntimeError("Email alerting is not configured")

        smtp_class = smtplib.SMTP_SSL if self.settings.smtp_use_ssl else smtplib.SMTP
        context = ssl.create_default_context()
        with smtp_class(host, self.settings.smtp_port, timeout=self.settings.smtp_timeout_seconds) as server:
            if not self.settings.smtp_use_ssl and self.settings.smtp_use_starttls:
                server.starttls(context=context)
            if self.settings.smtp_username:
                server.login(self.settings.smtp_username, self.settings.smtp_password or "")

            for recipient in recipients:
                message = EmailMessage()
                message["Subject"] = subject
                message["From"] = (
                    formataddr((self.settings.smtp_from_name, from_address))
                    if self.settings.smtp_from_name
                    else from_address
                )
                message["To"] = recipient
                if self.settings.smtp_reply_to:
                    message["Reply-To"] = self.settings.smtp_reply_to
                if self.settings.smtp_message_stream_header:
                    header_name, header_value = self._parse_smtp_header(
                        self.settings.smtp_message_stream_header
                    )
                    if header_name and header_value:
                        message[header_name] = header_value
                message.set_content(body)
                message.add_alternative(html_body, subtype="html")
                server.send_message(message)

    def _parse_smtp_header(self, raw_header: str) -> tuple[str | None, str | None]:
        header = raw_header.strip()
        if not header or ":" not in header:
            return None, None
        name, value = header.split(":", 1)
        name = name.strip()
        value = value.strip()
        if not name or not value:
            return None, None
        return name, value

    def _format_issue(self, issue: ProbeIssue) -> str:
        probe_label = {
            "api": "API",
            "search": "Search",
            "track": "Track",
        }.get(issue.probe, issue.probe)
        return f"{probe_label} {issue.status} ({issue.error})"

    def _format_issues_text(self, issues: tuple[ProbeIssue, ...]) -> str:
        return "\n".join(f"- {self._format_issue(issue)}" for issue in issues)

    def _format_issues_html(self, issues: tuple[ProbeIssue, ...]) -> str:
        items = "".join(
            f"<li style=\"margin:0 0 6px; color:#344642;\">{self._escape_html(self._format_issue(issue))}</li>"
            for issue in issues
        )
        return f"<ul style=\"margin:0; padding-left:18px; color:#344642;\">{items}</ul>"

    def _format_previous_summary_text(self, summary: str | None) -> str:
        if not summary:
            return "- Unknown failure"
        return "\n".join(f"- {item.strip()}" for item in summary.split(",") if item.strip())

    def _format_previous_summary_html(self, summary: str | None) -> str:
        items = [item.strip() for item in (summary or "").split(",") if item.strip()]
        if not items:
            items = ["Unknown failure"]
        html_items = "".join(
            f"<li style=\"margin:0 0 6px; color:#344642;\">{self._escape_html(item)}</li>"
            for item in items
        )
        return f"<ul style=\"margin:0; padding-left:18px; color:#344642;\">{html_items}</ul>"

    def _format_endpoint_display(self, url: str) -> str:
        return url.removeprefix("https://").removeprefix("http://").rstrip("/")

    def _build_alert_email_html(
        self,
        title: str,
        accent_color: str,
        badge_label: str,
        endpoint_label: str,
        rows: tuple[tuple[str, str], ...],
    ) -> str:
        rows_html = "".join(
            (
                "<tr>"
                f"<td style=\"padding:0 0 12px; width:132px; vertical-align:top; color:#8ea19b; "
                "font-size:13px; font-weight:600;\">"
                f"{self._escape_html(label)}"
                "</td>"
                f"<td style=\"padding:0 0 12px; color:#344642; font-size:14px; line-height:1.55;\">{value}</td>"
                "</tr>"
            )
            for label, value in rows
        )
        return (
            "<!doctype html>"
            "<html><body style=\"margin:0; padding:24px; background:#f3f5f4;\">"
            "<div style=\"max-width:680px; margin:0 auto; font-family:Trebuchet MS, Segoe UI, sans-serif;\">"
            "<div style=\"border-radius:18px; overflow:hidden; border:1px solid #d9e2de; background:#ffffff;\">"
            f"<div style=\"padding:18px 22px; background:linear-gradient(135deg, {accent_color}, #1f2a2d);\">"
            "<div style=\"font-size:12px; letter-spacing:0.12em; text-transform:uppercase; color:rgba(255,255,255,0.72); "
            "font-weight:700; margin-bottom:10px;\">Tidal Uptime</div>"
            f"<div style=\"font-size:28px; line-height:1.2; color:#ffffff; font-weight:700; margin-bottom:14px;\">{self._escape_html(title)}</div>"
            f"<span style=\"display:inline-block; padding:6px 10px; border-radius:999px; background:rgba(255,255,255,0.14); "
            "color:#ffffff; font-size:12px; font-weight:700; letter-spacing:0.06em; text-transform:uppercase;\">"
            f"{self._escape_html(badge_label)}</span>"
            "</div>"
            "<div style=\"padding:22px;\">"
            "<div style=\"margin-bottom:18px;\">"
            "<div style=\"font-size:12px; color:#71857f; text-transform:uppercase; letter-spacing:0.08em; font-weight:700; "
            "margin-bottom:8px;\">Endpoint</div>"
            f"<div style=\"font-size:24px; line-height:1.3; color:#1a2325; font-weight:700; word-break:break-word; text-decoration:none;\">{self._escape_html(endpoint_label)}</div>"
            "</div>"
            "<table role=\"presentation\" cellspacing=\"0\" cellpadding=\"0\" border=\"0\" style=\"width:100%; border-collapse:collapse;\">"
            f"{rows_html}"
            "</table>"
            "</div>"
            "</div>"
            "</div>"
            "</body></html>"
        )

    def _escape_html(self, value: str) -> str:
        return (
            value.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;")
        )

    def _format_state_label(self, state: str) -> str:
        return {
            "outage": "Outage",
            "degraded": "Degraded",
            "operational": "Operational",
        }.get(state, state.capitalize())

    def _clear_alert_state(self, timestamp: str) -> AlertState:
        return AlertState(updated_at=timestamp)

    def _endpoint_allows_failure_alert(
        self,
        endpoint: dict[str, Any],
        condition: AlertCondition,
    ) -> bool:
        if condition.state == "outage":
            return bool(endpoint.get("alert_on_outage", True))
        if condition.state == "degraded":
            return any(self._endpoint_allows_probe_alert(endpoint, issue.probe) for issue in condition.issues)
        return False

    def _endpoint_allows_probe_alert(self, endpoint: dict[str, Any], probe: str) -> bool:
        if probe == "api":
            return bool(endpoint.get("alert_on_outage", True))
        if probe == "search":
            return bool(endpoint.get("alert_on_search", True))
        if probe == "track":
            return bool(endpoint.get("alert_on_track", True))
        return False

    def _endpoint_allows_recovery_alert(self, endpoint: dict[str, Any]) -> bool:
        return (
            self.settings.alert_recovery_enabled
            and bool(endpoint.get("alert_on_recovery", True))
        )
