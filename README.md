# Tilo Agent (AgentScope Minimal Framework)

A minimal ReAct-style framework built directly on AgentScope primitives (`ReActAgent`, `Toolkit`, `Msg`, `Memory`).

## Overview
- No CLI or package entry point; this project exposes modules you can import to build or test an agent.
- Tools are registered via `skills` and `tools` modules, then run through AgentScope's toolkit and memory stack.
- A mock LLM is included so the framework runs fully offline without requiring API keys.

## Example
```python
import asyncio
from runtime.session import SessionContext
from agent.core import run_once

ctx = SessionContext(
    session_id="demo",
    enabled_skills=["time_skill", "math_skill"],
)
print(asyncio.run(run_once("现在几点？", ctx)))
```

## Running
1. Install dependencies: `pip install .`
2. Run the example above from any Python script; no environment variables are required because the mock model always loads when no provider config is found.

## Structure
- `agent/` holds the protocol, prompt builder, and orchestrator.
- `tools/` defines the Tool abstraction and AgentScope registry.
- `skills/` exposes builtin skills (`time_skill`, `math_skill`) with their metadata and tool exports.
- `llm/` contains the mock model and the env-driven adapter hooks.
- `memory/` persists interactions via JSONL.
- `runtime/` hosts session configuration helpers.

## Environment
Fill `.env.example` to configure real models later. The mock model works without any keys, so you can safely run `run_once` immediately.
