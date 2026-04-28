from __future__ import annotations

import logging
import re
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import Cookie, FastAPI, HTTPException, Response, status
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.auth import AuthManager
from app.dashboard import render_dashboard, render_login
from app.monitor import EndpointMonitor
from app.settings import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

settings = get_settings()
monitor = EndpointMonitor(settings)
auth_manager = AuthManager(settings)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await monitor.start()
    try:
        yield
    finally:
        await monitor.stop()


app = FastAPI(title="Tidal Uptime", lifespan=lifespan)


class SubcheckPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    label: str = ""
    url: AnyHttpUrl
    request_method: str = Field(default="GET", alias="requestMethod")
    expected_status: int | None = Field(default=None, alias="expectedStatus")
    match_type: str | None = Field(default=None, alias="matchType")
    match_path: str | None = Field(default=None, alias="matchPath")
    match_value: str | None = Field(default=None, alias="matchValue")
    sort_order: int = Field(default=0, alias="sortOrder")


class EndpointPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    url: AnyHttpUrl
    name: str | None = None
    kind: str = "tidal"
    group_id: int | None = Field(default=None, alias="groupId")
    request_method: str = Field(default="GET", alias="requestMethod")
    expected_status: int | None = Field(default=None, alias="expectedStatus")
    match_type: str | None = Field(default=None, alias="matchType")
    match_path: str | None = Field(default=None, alias="matchPath")
    match_value: str | None = Field(default=None, alias="matchValue")
    metrics_url: str | None = Field(default=None, alias="metricsUrl")
    metrics_keys: str | None = Field(default=None, alias="metricsKeys")
    email_alerts_enabled: bool = Field(default=True, alias="emailAlertsEnabled")
    alert_on_outage: bool = Field(default=True, alias="alertOnOutage")
    alert_on_search: bool = Field(default=True, alias="alertOnSearch")
    alert_on_track: bool = Field(default=True, alias="alertOnTrack")
    alert_on_recovery: bool = Field(default=True, alias="alertOnRecovery")
    subchecks: list[SubcheckPayload] = Field(default_factory=list)


class LoginPayload(BaseModel):
    password: str


class BulkEndpointAlertsPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    email_alerts_enabled: bool = Field(default=True, alias="emailAlertsEnabled")
    alert_on_outage: bool = Field(default=True, alias="alertOnOutage")
    alert_on_search: bool = Field(default=True, alias="alertOnSearch")
    alert_on_track: bool = Field(default=True, alias="alertOnTrack")
    alert_on_recovery: bool = Field(default=True, alias="alertOnRecovery")


class GroupPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    sort_order: int = Field(default=0, alias="sortOrder")


class EmailSubscriptionPayload(BaseModel):
    email: str


def _endpoint_payload_to_dict(payload: EndpointPayload) -> tuple[dict, list[dict]]:
    fields = {
        "url": str(payload.url).rstrip("/"),
        "name": (payload.name or None),
        "kind": payload.kind,
        "group_id": payload.group_id,
        "request_method": payload.request_method,
        "expected_status": payload.expected_status,
        "match_type": payload.match_type,
        "match_path": payload.match_path,
        "match_value": payload.match_value,
        "metrics_url": payload.metrics_url,
        "metrics_keys": payload.metrics_keys,
        "email_alerts_enabled": payload.email_alerts_enabled,
        "alert_on_outage": payload.alert_on_outage,
        "alert_on_search": payload.alert_on_search,
        "alert_on_track": payload.alert_on_track,
        "alert_on_recovery": payload.alert_on_recovery,
    }
    subchecks = [
        {
            "label": sub.label,
            "url": str(sub.url).rstrip("/"),
            "request_method": sub.request_method,
            "expected_status": sub.expected_status,
            "match_type": sub.match_type,
            "match_path": sub.match_path,
            "match_value": sub.match_value,
            "sort_order": sub.sort_order,
        }
        for sub in payload.subchecks
    ]
    return fields, subchecks


EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_email(value: str) -> str:
    email = value.strip().lower()
    if not EMAIL_PATTERN.fullmatch(email):
        raise HTTPException(status_code=422, detail="Invalid email address")
    return email


def require_authenticated(auth_cookie: str | None) -> None:
    if not auth_manager.is_cookie_valid(auth_cookie):
        raise HTTPException(status_code=401, detail="Authentication required")


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def root(
    auth_cookie: str | None = Cookie(default=None, alias=settings.auth_cookie_name),
) -> HTMLResponse:
    if not auth_manager.is_cookie_valid(auth_cookie):
        return HTMLResponse(render_login())
    return HTMLResponse(render_dashboard())


@app.get("/robots.txt", response_class=PlainTextResponse, include_in_schema=False)
async def robots_txt() -> PlainTextResponse:
    return PlainTextResponse("User-agent: *\nDisallow: /\n")


@app.get("/favicon.ico", response_class=PlainTextResponse, include_in_schema=False)
async def favicon() -> PlainTextResponse:
    return PlainTextResponse("", status_code=204)


@app.get("/status.json")
async def status_json() -> dict:
    return await monitor.get_snapshot()


@app.get("/api/status-page", include_in_schema=False)
async def status_page_data(
    auth_cookie: str | None = Cookie(default=None, alias=settings.auth_cookie_name),
) -> dict:
    require_authenticated(auth_cookie)
    return await monitor.get_status_page_data()


@app.get("/api/auth/status", include_in_schema=False)
async def auth_status(
    auth_cookie: str | None = Cookie(default=None, alias=settings.auth_cookie_name),
) -> dict[str, bool]:
    return {"authenticated": auth_manager.is_cookie_valid(auth_cookie)}


@app.post("/api/auth/login", include_in_schema=False)
async def auth_login(payload: LoginPayload) -> Response:
    if not auth_manager.verify_password(payload.password):
        raise HTTPException(status_code=401, detail="Invalid password")

    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    auth_manager.apply_login_cookie(response)
    return response


@app.post("/api/auth/logout", include_in_schema=False)
async def auth_logout() -> Response:
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    auth_manager.clear_login_cookie(response)
    return response


@app.get("/api/instances", include_in_schema=False)
async def list_instances(
    auth_cookie: str | None = Cookie(default=None, alias=settings.auth_cookie_name),
) -> dict[str, list[dict]]:
    require_authenticated(auth_cookie)
    return {"items": await monitor.list_endpoints()}


@app.post("/api/instances", status_code=status.HTTP_201_CREATED, include_in_schema=False)
async def create_instance(
    payload: EndpointPayload,
    auth_cookie: str | None = Cookie(default=None, alias=settings.auth_cookie_name),
) -> dict:
    require_authenticated(auth_cookie)
    fields, subchecks = _endpoint_payload_to_dict(payload)
    try:
        endpoint = await monitor.create_endpoint(fields, subchecks)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return endpoint


@app.put("/api/instances/{endpoint_id}", include_in_schema=False)
async def update_instance(
    endpoint_id: int,
    payload: EndpointPayload,
    auth_cookie: str | None = Cookie(default=None, alias=settings.auth_cookie_name),
) -> dict:
    require_authenticated(auth_cookie)
    fields, subchecks = _endpoint_payload_to_dict(payload)
    try:
        endpoint = await monitor.update_endpoint(endpoint_id, fields, subchecks)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return endpoint


@app.get("/api/instances/{endpoint_id}/metrics", include_in_schema=False)
async def get_instance_metrics(
    endpoint_id: int,
    auth_cookie: str | None = Cookie(default=None, alias=settings.auth_cookie_name),
) -> dict:
    require_authenticated(auth_cookie)
    metrics = await monitor.store.get_endpoint_metrics(endpoint_id)
    if metrics is None:
        return {"endpointId": endpoint_id, "fetchedAt": None, "ok": None, "payloadJson": None}
    return metrics


@app.get("/api/groups", include_in_schema=False)
async def list_groups_route(
    auth_cookie: str | None = Cookie(default=None, alias=settings.auth_cookie_name),
) -> dict[str, list[dict]]:
    require_authenticated(auth_cookie)
    return {"items": await monitor.list_groups()}


@app.post("/api/groups", status_code=status.HTTP_201_CREATED, include_in_schema=False)
async def create_group_route(
    payload: GroupPayload,
    auth_cookie: str | None = Cookie(default=None, alias=settings.auth_cookie_name),
) -> dict:
    require_authenticated(auth_cookie)
    try:
        return await monitor.create_group(payload.name, payload.sort_order)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.put("/api/groups/{group_id}", include_in_schema=False)
async def update_group_route(
    group_id: int,
    payload: GroupPayload,
    auth_cookie: str | None = Cookie(default=None, alias=settings.auth_cookie_name),
) -> dict:
    require_authenticated(auth_cookie)
    try:
        return await monitor.update_group(group_id, payload.name, payload.sort_order)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.delete(
    "/api/groups/{group_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    include_in_schema=False,
)
async def delete_group_route(
    group_id: int,
    auth_cookie: str | None = Cookie(default=None, alias=settings.auth_cookie_name),
) -> Response:
    require_authenticated(auth_cookie)
    try:
        await monitor.delete_group(group_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.patch("/api/instances/settings", include_in_schema=False)
async def bulk_update_instance_settings(
    payload: BulkEndpointAlertsPayload,
    auth_cookie: str | None = Cookie(default=None, alias=settings.auth_cookie_name),
) -> dict[str, int]:
    require_authenticated(auth_cookie)
    updated = await monitor.update_all_endpoint_settings(
        payload.email_alerts_enabled,
        payload.alert_on_outage,
        payload.alert_on_search,
        payload.alert_on_track,
        payload.alert_on_recovery,
    )
    return {"updated": updated}


@app.post(
    "/api/instances/{endpoint_id}/subscriptions",
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def create_instance_subscription(
    endpoint_id: int,
    payload: EmailSubscriptionPayload,
) -> dict:
    if not settings.email_alerting_enabled:
        raise HTTPException(status_code=503, detail="Email alerts are not configured")

    try:
        subscription = await monitor.create_email_subscription(
            endpoint_id,
            normalize_email(payload.email),
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return subscription


@app.get("/api/subscriptions", include_in_schema=False)
async def list_subscriptions(
    auth_cookie: str | None = Cookie(default=None, alias=settings.auth_cookie_name),
) -> dict[str, list[dict]]:
    require_authenticated(auth_cookie)
    return {"items": await monitor.list_email_subscriptions()}


@app.delete(
    "/api/subscriptions/{subscription_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    include_in_schema=False,
)
async def delete_subscription(
    subscription_id: int,
    auth_cookie: str | None = Cookie(default=None, alias=settings.auth_cookie_name),
) -> Response:
    require_authenticated(auth_cookie)
    try:
        await monitor.delete_email_subscription(subscription_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.delete("/api/instances/{endpoint_id}", status_code=status.HTTP_204_NO_CONTENT, include_in_schema=False)
async def delete_instance(
    endpoint_id: int,
    auth_cookie: str | None = Cookie(default=None, alias=settings.auth_cookie_name),
) -> Response:
    require_authenticated(auth_cookie)
    try:
        await monitor.delete_endpoint(endpoint_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/api/refresh", include_in_schema=False)
async def trigger_refresh() -> dict:
    snapshot = await monitor.get_snapshot()
    started = await monitor.trigger_refresh()
    return {
        "status": "started" if started else "already_running",
        "lastUpdated": snapshot["lastUpdated"],
        "refreshInProgress": monitor.is_refresh_in_progress(),
    }


@app.get("/health")
async def health() -> dict[str, str]:
    snapshot = await monitor.get_snapshot()
    return {"status": "ok", "lastUpdated": snapshot["lastUpdated"]}


if __name__ == "__main__":
    uvicorn.run(app, host=settings.app_host, port=settings.app_port)
