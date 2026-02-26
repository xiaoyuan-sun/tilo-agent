from __future__ import annotations

import argparse
import json
from datetime import datetime
from zoneinfo import ZoneInfo


def now(timezone: str = "Asia/Seoul") -> dict[str, str]:
    tz = ZoneInfo(timezone)
    current = datetime.now(tz)
    return {"iso": current.isoformat(), "timezone": tz.key}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--timezone", default="Asia/Seoul", help="IANA timezone name")
    args = parser.parse_args()
    print(json.dumps(now(args.timezone), ensure_ascii=True))
