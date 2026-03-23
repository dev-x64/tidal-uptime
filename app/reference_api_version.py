from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx

from app.settings import Settings

logger = logging.getLogger(__name__)

API_VERSION_PATTERN = re.compile(r"^\s*API_VERSION\s*=\s*[\"']([^\"']+)[\"']", re.MULTILINE)


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


class ReferenceApiVersionTracker:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._lock = asyncio.Lock()
        self._version: str | None = None
        self._checked_at: str | None = None

    async def start(self) -> None:
        await self._load_cache()

    async def get_payload(self) -> dict[str, Any]:
        async with self._lock:
            return {
                "version": self._version,
                "checkedAt": self._checked_at,
                "sourceUrl": self.settings.reference_api_version_source_url,
            }

    async def ensure_fresh(self, client: httpx.AsyncClient | None = None) -> None:
        async with self._lock:
            if self._is_fresh():
                return

            try:
                if client is None:
                    timeout = httpx.Timeout(self.settings.request_timeout_seconds)
                    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as transient_client:
                        version = await self._fetch_version(transient_client)
                else:
                    version = await self._fetch_version(client)
            except Exception:
                logger.exception(
                    "Failed to refresh reference API version from %s",
                    self.settings.reference_api_version_source_url,
                )
                return

            self._version = version
            self._checked_at = utc_timestamp()
            await asyncio.to_thread(self._write_cache)

    async def _load_cache(self) -> None:
        payload = await asyncio.to_thread(self._read_cache)
        async with self._lock:
            self._version = self._normalize_version(payload.get("version"))
            checked_at = payload.get("checkedAt")
            self._checked_at = checked_at if isinstance(checked_at, str) and checked_at.strip() else None

    async def _fetch_version(self, client: httpx.AsyncClient) -> str:
        response = await client.get(self.settings.reference_api_version_source_url)
        response.raise_for_status()
        match = API_VERSION_PATTERN.search(response.text)
        if match is None:
            raise ValueError("API_VERSION was not found in upstream main.py")

        version = self._normalize_version(match.group(1))
        if version is None:
            raise ValueError("API_VERSION in upstream main.py is empty")
        return version

    def _read_cache(self) -> dict[str, Any]:
        path = Path(self.settings.reference_api_version_cache_path)
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            logger.exception("Failed to read cached reference API version from %s", path)
            return {}

    def _write_cache(self) -> None:
        path = Path(self.settings.reference_api_version_cache_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": self._version,
            "checkedAt": self._checked_at,
            "sourceUrl": self.settings.reference_api_version_source_url,
        }
        path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")

    def _is_fresh(self) -> bool:
        checked_at = parse_timestamp(self._checked_at)
        if checked_at is None:
            return False
        max_age = timedelta(seconds=max(int(self.settings.reference_api_version_refresh_seconds), 1))
        return datetime.now(timezone.utc) - checked_at < max_age

    def _normalize_version(self, value: Any) -> str | None:
        if value is None:
            return None
        version = str(value).strip()
        return version or None
