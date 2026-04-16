from __future__ import annotations

import os
from datetime import UTC, datetime
from zoneinfo import ZoneInfo


APP_TIMEZONE_NAME = os.getenv("APP_TIMEZONE", "Europe/Madrid")


def app_timezone() -> ZoneInfo:
    try:
        return ZoneInfo(APP_TIMEZONE_NAME)
    except Exception:
        return ZoneInfo("Europe/Madrid")


def now_local() -> datetime:
    return datetime.now(app_timezone())


def now_utc() -> datetime:
    return datetime.now(UTC)


def format_clock_timestamp(value=None, with_timezone: bool = True) -> str:
    if value is None:
        value = now_local()
    elif not isinstance(value, datetime):
        try:
            raw = str(value).strip()
            value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except Exception:
            return str(value)
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    local_value = value.astimezone(app_timezone())
    if with_timezone:
        return local_value.strftime("%H:%M:%S %Z")
    return local_value.strftime("%H:%M:%S")


def format_timestamp(value, include_seconds: bool = True) -> str:
    if value is None:
        return "—"
    if not isinstance(value, datetime):
        try:
            raw = str(value).strip()
            value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except Exception:
            return str(value)
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    local_value = value.astimezone(app_timezone())
    time_fmt = "%Y-%m-%d %H:%M:%S" if include_seconds else "%Y-%m-%d %H:%M"
    offset = local_value.strftime("%z")
    offset = f"UTC{offset[:3]}:{offset[3:]}" if offset else "UTC"
    return f"{local_value.strftime(time_fmt)} {local_value.tzname()} ({offset})"
