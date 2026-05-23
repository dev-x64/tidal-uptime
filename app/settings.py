from __future__ import annotations

from functools import lru_cache
from math import ceil

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict, TomlConfigSettingsSource


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            TomlConfigSettingsSource(settings_cls, ".smtp.toml"),
            file_secret_settings,
        )

    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    check_interval_seconds: int = Field(default=300, alias="CHECK_INTERVAL_SECONDS")
    request_timeout_seconds: float = Field(default=10.0, alias="REQUEST_TIMEOUT_SECONDS")
    database_path: str = Field(default="data/uptime.db", alias="DATABASE_PATH")
    reference_api_version_source_url: str = Field(
        default="https://raw.githubusercontent.com/binimum/hifi-api/refs/heads/main/main.py",
        alias="REFERENCE_API_VERSION_SOURCE_URL",
    )
    reference_api_version_cache_path: str = Field(
        default="data/reference_api_version.json",
        alias="REFERENCE_API_VERSION_CACHE_PATH",
    )
    reference_api_version_refresh_seconds: int = Field(
        default=86400,
        alias="REFERENCE_API_VERSION_REFRESH_SECONDS",
    )
    history_retention_runs: int = Field(default=4320, alias="HISTORY_RETENTION_RUNS")
    status_page_window_hours: int = Field(default=168, alias="STATUS_PAGE_WINDOW_HOURS")
    max_track_retries: int = Field(default=2, alias="MAX_TRACK_RETRIES")
    admin_password: str = Field(default="change-me", alias="ADMIN_PASSWORD")
    auth_cookie_name: str = Field(default="tidal_uptime_auth", alias="AUTH_COOKIE_NAME")
    auth_cookie_secret: str = Field(default="change-this-cookie-secret", alias="AUTH_COOKIE_SECRET")
    auth_cookie_max_age_seconds: int = Field(default=604800, alias="AUTH_COOKIE_MAX_AGE_SECONDS")
    user_agent: str = Field(
        default=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/134.0.0.0 Safari/537.36"
        ),
        alias="USER_AGENT",
    )
    search_query: str = Field(default="the weeknd", alias="SEARCH_QUERY")
    alert_failure_streak: int = Field(default=2, alias="ALERT_FAILURE_STREAK")
    alert_recovery_enabled: bool = Field(default=True, alias="ALERT_RECOVERY_ENABLED")
    alert_recovery_streak: int = Field(default=1, alias="ALERT_RECOVERY_STREAK")
    alert_trigger_states_raw: str = Field(
        default="outage,degraded",
        alias="ALERT_TRIGGER_STATES",
    )
    alert_trigger_probes_raw: str = Field(
        default="api,search,track",
        alias="ALERT_TRIGGER_PROBES",
    )
    email_alerts_enabled: bool = Field(default=True, alias="EMAIL_ALERTS_ENABLED")
    smtp_host: str | None = Field(default=None, alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_username: str | None = Field(default=None, alias="SMTP_USERNAME")
    smtp_password: str | None = Field(default=None, alias="SMTP_PASSWORD")
    smtp_from_email: str | None = Field(default=None, alias="SMTP_FROM_EMAIL")
    smtp_from_name: str | None = Field(default=None, alias="SMTP_FROM_NAME")
    smtp_reply_to: str | None = Field(default=None, alias="SMTP_REPLY_TO")
    smtp_message_stream_header: str | None = Field(
        default=None,
        alias="SMTP_MESSAGE_STREAM_HEADER",
    )
    smtp_use_starttls: bool = Field(default=True, alias="SMTP_USE_STARTTLS")
    smtp_use_ssl: bool = Field(default=False, alias="SMTP_USE_SSL")
    smtp_timeout_seconds: float = Field(default=10.0, alias="SMTP_TIMEOUT_SECONDS")
    metrics_max_payload_bytes: int = Field(default=200_000, alias="METRICS_MAX_PAYLOAD_BYTES")

    default_endpoints: tuple[str, ...] = (
        "https://wolf.qqdl.site",
        "https://maus.qqdl.site",
        "https://katze.qqdl.site",
        "https://hund.qqdl.site",
        "https://hifi-spo.spotisaver.net",
        "https://hifi-api2.spotisaver.net",
        "https://hifi-api3.spotisaver.net",
    )

    default_group_name: str = "Tidal"

    probe_track_ids: tuple[int, ...] = (134858527, 125155092, 204567804)

    @property
    def email_alerting_enabled(self) -> bool:
        return self.email_alerts_enabled and bool(self.smtp_host) and bool(self.smtp_from_email)

    @property
    def alert_trigger_states(self) -> tuple[str, ...]:
        return self._split_csv(self.alert_trigger_states_raw)

    @property
    def alert_trigger_probes(self) -> tuple[str, ...]:
        return self._split_csv(self.alert_trigger_probes_raw)

    @property
    def status_page_history_points(self) -> int:
        interval = max(int(self.check_interval_seconds), 1)
        window_seconds = max(int(self.status_page_window_hours), 1) * 3600
        return max(1, ceil(window_seconds / interval))

    def _split_csv(self, value: str) -> tuple[str, ...]:
        return tuple(item.strip().lower() for item in value.split(",") if item.strip())


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
