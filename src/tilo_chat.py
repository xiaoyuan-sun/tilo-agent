from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import TextIO

from runtime.session import SessionContext, new_session_id


def _parse_skills(raw: str) -> list[str]:
    return [part.strip() for part in raw.split(",") if part.strip()]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tilo-chat")
    parser.add_argument("-m", "--message", help="Single message mode. If omitted, run REPL.")
    parser.add_argument(
        "--skills",
        default="time_skill,math_skill",
        help="Comma-separated skill names to enable.",
    )
    parser.add_argument("--session-id", default="")
    parser.add_argument("--timezone", default="Asia/Seoul")
    parser.add_argument("--memory-dir", default="./data")
    parser.add_argument("--max-iters", type=int, default=6)
    return parser


def _build_context(args: argparse.Namespace) -> SessionContext:
    return SessionContext(
        session_id=args.session_id or new_session_id(),
        enabled_skills=_parse_skills(args.skills),
        timezone=args.timezone,
        memory_dir=Path(args.memory_dir),
        max_iters=args.max_iters,
    )


async def _run_once(user_text: str, ctx: SessionContext) -> str:
    try:
        from agent.core import run_once
    except ModuleNotFoundError as exc:
        if exc.name == "agentscope":
            raise RuntimeError(
                "Missing dependency 'agentscope'. Install project dependencies first: pip install -e ."
            ) from exc
        raise

    return await run_once(user_text, ctx)


def main(
    argv: list[str] | None = None,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    args = _build_parser().parse_args(argv)
    in_stream = stdin or sys.stdin
    out_stream = stdout or sys.stdout
    err_stream = stderr or sys.stderr
    ctx = _build_context(args)

    try:
        if args.message:
            reply = asyncio.run(_run_once(args.message, ctx))
            print(reply, file=out_stream)
            return 0

        for raw in in_stream:
            text = raw.strip()
            if not text:
                continue
            if text.lower() in {"exit", "quit", ":q"}:
                break
            reply = asyncio.run(_run_once(text, ctx))
            print(reply, file=out_stream)
        return 0
    except KeyboardInterrupt:
        return 0
    except RuntimeError as exc:
        print(str(exc), file=err_stream)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
