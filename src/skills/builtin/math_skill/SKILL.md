---
name: math_skill
description: 利用安全算术解析处理用户的表达式。
---

## When to use
When the user gives a calculation request or embeds math expressions.

## Scripts
- `scripts/calc.py`: evaluates arithmetic expressions safely with an AST whitelist.
- Usage: `python scripts/calc.py --expression "1 + 2 * (3 - 1)"`

## Limits
Do not evaluate arbitrary strings: use AST whitelisting and report clear errors if parsing fails.
