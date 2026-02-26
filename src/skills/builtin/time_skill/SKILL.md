---
name: time_skill
description: 返回时间和时区信息。
---

## When to use
Use when the user asks for the current time or date-related scheduling details.

## Scripts
- `scripts/now.py`: returns current time with timezone metadata.
- Usage: `python scripts/now.py --timezone Asia/Seoul`

## Limits
This skill only exposes `time.now`. Do not invent other endpoints or return historical dates unless explicitly requested.
