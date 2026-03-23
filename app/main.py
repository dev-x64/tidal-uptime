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
from app.dashboard import render_dashboard
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


class EndpointPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    url: AnyHttpUrl
    alerts_enabled: bool = Field(default=True, alias="alertsEnabled")
    alert_on_outage: bool = Field(default=True, alias="alertOnOutage")
    alert_on_search: bool = Field(default=True, alias="alertOnSearch")
    alert_on_track: bool = Field(default=True, alias="alertOnTrack")
    alert_on_recovery: bool = Field(default=True, alias="alertOnRecovery")


class LoginPayload(BaseModel):
    password: str


class EndpointAlertsPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    alerts_enabled: bool = Field(alias="alertsEnabled")


class EmailSubscriptionPayload(BaseModel):
    email: str


EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_email(value: str) -> str:
    email = value.strip().lower()
    if not EMAIL_PATTERN.fullmatch(email):
        raise HTTPException(status_code=422, detail="Invalid email address")
    return email


def require_authenticated(auth_cookie: str | None) -> None:
    if not auth_manager.is_cookie_valid(auth_cookie):
        raise HTTPException(status_code=401, detail="Authentication required")


@app.get("/", response_class=HTMLResponse)
async def root() -> HTMLResponse:
    return HTMLResponse(render_dashboard())


@app.get("/robots.txt", response_class=PlainTextResponse)
async def robots_txt() -> PlainTextResponse:
    return PlainTextResponse("User-agent: *\nDisallow: /\n")


@app.get("/favicon.ico", response_class=PlainTextResponse)
async def favicon() -> PlainTextResponse:
    return PlainTextResponse("", status_code=204)


@app.get("/status.json")
async def status_json() -> dict:
    return await monitor.get_snapshot()


@app.get("/api/status-page")
async def status_page_data() -> dict:
    return await monitor.get_status_page_data()


@app.get("/api/auth/status")
async def auth_status(
    auth_cookie: str | None = Cookie(default=None, alias=settings.auth_cookie_name),
) -> dict[str, bool]:
    return {"authenticated": auth_manager.is_cookie_valid(auth_cookie)}


@app.post("/api/auth/login")
async def auth_login(payload: LoginPayload) -> Response:
    if not auth_manager.verify_password(payload.password):
        raise HTTPException(status_code=401, detail="Invalid password")

    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    auth_manager.apply_login_cookie(response)
    return response


@app.post("/api/auth/logout")
async def auth_logout() -> Response:
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    auth_manager.clear_login_cookie(response)
    return response


@app.get("/api/instances")
async def list_instances(
    auth_cookie: str | None = Cookie(default=None, alias=settings.auth_cookie_name),
) -> dict[str, list[dict]]:
    require_authenticated(auth_cookie)
    return {"items": await monitor.list_endpoints()}


@app.post("/api/instances", status_code=status.HTTP_201_CREATED)
async def create_instance(
    payload: EndpointPayload,
    auth_cookie: str | None = Cookie(default=None, alias=settings.auth_cookie_name),
) -> dict:
    require_authenticated(auth_cookie)
    try:
        endpoint = await monitor.create_endpoint(
            str(payload.url).rstrip("/"),
            payload.alerts_enabled,
            payload.alert_on_outage,
            payload.alert_on_search,
            payload.alert_on_track,
            payload.alert_on_recovery,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return endpoint


@app.put("/api/instances/{endpoint_id}")
async def update_instance(
    endpoint_id: int,
    payload: EndpointPayload,
    auth_cookie: str | None = Cookie(default=None, alias=settings.auth_cookie_name),
) -> dict:
    require_authenticated(auth_cookie)
    try:
        endpoint = await monitor.update_endpoint(
            endpoint_id,
            str(payload.url).rstrip("/"),
            payload.alerts_enabled,
            payload.alert_on_outage,
            payload.alert_on_search,
            payload.alert_on_track,
            payload.alert_on_recovery,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return endpoint


@app.patch("/api/instances/{endpoint_id}/alerts")
async def update_instance_alerts(
    endpoint_id: int,
    payload: EndpointAlertsPayload,
    auth_cookie: str | None = Cookie(default=None, alias=settings.auth_cookie_name),
) -> dict:
    require_authenticated(auth_cookie)
    try:
        endpoint = await monitor.set_endpoint_alerts_enabled(
            endpoint_id,
            payload.alerts_enabled,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return endpoint


@app.post("/api/instances/{endpoint_id}/subscriptions", status_code=status.HTTP_201_CREATED)
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


@app.get("/api/subscriptions")
async def list_subscriptions(
    auth_cookie: str | None = Cookie(default=None, alias=settings.auth_cookie_name),
) -> dict[str, list[dict]]:
    require_authenticated(auth_cookie)
    return {"items": await monitor.list_email_subscriptions()}


@app.delete("/api/subscriptions/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
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


@app.delete("/api/instances/{endpoint_id}", status_code=status.HTTP_204_NO_CONTENT)
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


@app.post("/api/refresh")
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
