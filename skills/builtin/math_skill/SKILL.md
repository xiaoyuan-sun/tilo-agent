name: math_skill
description: 利用安全算术解析处理用户的表达式。

## When to use
When the user gives a calculation request or embeds math expressions.

## Tool guidance
Only parse arithmetic with +, -, *, / and parenthesis. Reject code and text outside the math expression.

## Limits
Do not evaluate arbitrary strings: use AST whitelisting and report clear errors if parsing fails.
