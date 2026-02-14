from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from tools.base import Tool


def _now(timezone: str | None = None) -> dict[str, str]:
    tz = ZoneInfo(timezone or "Asia/Seoul")
    now = datetime.now(tz)
    return {"iso": now.isoformat(), "timezone": tz.key}


time_tool = Tool(
    name="time.now",
    description="Returns the current time in the requested timezone (defaults to Asia/Seoul).",
    args_schema={"timezone": "string (optional)"},
    func=_now,
)

TOOLS = [time_tool]
