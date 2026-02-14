name: time_skill
description: 返回时间和时区信息。

## When to use
Use when the user asks for the current time or date-related scheduling details.

## Tool guidance
Provide a timezone when needed; default is Asia/Seoul. Output must be ISO8601 string and timezone metadata.

## Limits
This skill only exposes `time.now`. Do not invent other endpoints or return historical dates unless explicitly requested.
