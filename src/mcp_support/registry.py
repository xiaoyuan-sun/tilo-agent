from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Mapping

if TYPE_CHECKING:
    from agentscope.tool import Toolkit

try:
    from agentscope.mcp import HttpStatefulClient, HttpStatelessClient, StdIOStatefulClient
except ModuleNotFoundError:  # pragma: no cover - exercised via runtime import failures
    HttpStatefulClient = None  # type: ignore[assignment]
    HttpStatelessClient = None  # type: ignore[assignment]
    StdIOStatefulClient = None  # type: ignore[assignment]

_ENV_NAME = "AGENTSCOPE_MCP_SERVERS"
_ALLOWED_NAMESAKE_STRATEGIES = {"override", "skip", "raise", "rename"}


@dataclass(frozen=True)
class MCPConfig:
    name: str
    client_type: str
    transport: str | None = None
    url: str | None = None
    headers: dict[str, str] | None = None
    timeout: float = 30
    sse_read_timeout: float = 300
    command: str | None = None
    args: list[str] | None = None
    env: dict[str, str] | None = None
    cwd: str | None = None
    group_name: str = "basic"
    enable_funcs: list[str] | None = None
    disable_funcs: list[str] | None = None
    preset_kwargs_mapping: dict[str, dict[str, Any]] | None = None
    namesake_strategy: str = "raise"


@dataclass
class MCPRegistrationManager:
    client_names: list[str]
    _stateful_clients: list[Any]

    async def close(self) -> None:
        for client in reversed(self._stateful_clients):
            await client.close()
        self._stateful_clients.clear()


def _as_str_list(value: Any, *, key: str) -> list[str] | None:
    if value is None:
        return None
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"`{key}` must be a list of strings.")
    return value


def _as_optional_mapping_str_str(value: Any, *, key: str) -> dict[str, str] | None:
    if value is None:
        return None
    if not isinstance(value, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in value.items()
    ):
        raise ValueError(f"`{key}` must be a string-to-string mapping.")
    return value


def _as_optional_preset_kwargs(value: Any) -> dict[str, dict[str, Any]] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("`preset_kwargs_mapping` must be a dict.")
    for k, v in value.items():
        if not isinstance(k, str) or not isinstance(v, dict):
            raise ValueError(
                "`preset_kwargs_mapping` must be a dict[str, dict[str, Any]]."
            )
    return value


def _parse_one_config(raw: Any) -> MCPConfig:
    if not isinstance(raw, dict):
        raise ValueError("Each MCP server config must be an object.")
    if not isinstance(raw.get("name"), str) or not raw["name"].strip():
        raise ValueError("MCP server config requires non-empty `name`.")
    if not isinstance(raw.get("type"), str):
        raise ValueError("MCP server config requires string `type`.")

    namesake_strategy = raw.get("namesake_strategy", "raise")
    if namesake_strategy not in _ALLOWED_NAMESAKE_STRATEGIES:
        raise ValueError(
            "`namesake_strategy` must be one of: "
            + ", ".join(sorted(_ALLOWED_NAMESAKE_STRATEGIES))
        )

    cfg = MCPConfig(
        name=raw["name"],
        client_type=raw["type"],
        transport=raw.get("transport"),
        url=raw.get("url"),
        headers=_as_optional_mapping_str_str(raw.get("headers"), key="headers"),
        timeout=float(raw.get("timeout", 30)),
        sse_read_timeout=float(raw.get("sse_read_timeout", 300)),
        command=raw.get("command"),
        args=_as_str_list(raw.get("args"), key="args"),
        env=_as_optional_mapping_str_str(raw.get("env"), key="env"),
        cwd=raw.get("cwd"),
        group_name=str(raw.get("group_name", "basic")),
        enable_funcs=_as_str_list(raw.get("enable_funcs"), key="enable_funcs"),
        disable_funcs=_as_str_list(raw.get("disable_funcs"), key="disable_funcs"),
        preset_kwargs_mapping=_as_optional_preset_kwargs(raw.get("preset_kwargs_mapping")),
        namesake_strategy=namesake_strategy,
    )
    return cfg


def load_mcp_configs_from_env(env: Mapping[str, str] | None = None) -> list[MCPConfig]:
    env = os.environ if env is None else env
    raw = env.get(_ENV_NAME, "").strip()
    if not raw:
        return []
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid JSON in environment variable `{_ENV_NAME}`: {exc}"
        ) from exc
    if not isinstance(decoded, list):
        raise ValueError(f"`{_ENV_NAME}` must be a JSON array.")
    return [_parse_one_config(item) for item in decoded]


def _build_client(cfg: MCPConfig) -> tuple[Any, bool]:
    if cfg.client_type == "http_stateful":
        if HttpStatefulClient is None:
            raise RuntimeError(
                "MCP dependencies are missing. Install project dependencies first: pip install -e ."
            )
        if not cfg.transport or not cfg.url:
            raise ValueError("`http_stateful` requires `transport` and `url`.")
        return (
            HttpStatefulClient(
                name=cfg.name,
                transport=cfg.transport,
                url=cfg.url,
                headers=cfg.headers,
                timeout=cfg.timeout,
                sse_read_timeout=cfg.sse_read_timeout,
            ),
            True,
        )
    if cfg.client_type == "http_stateless":
        if HttpStatelessClient is None:
            raise RuntimeError(
                "MCP dependencies are missing. Install project dependencies first: pip install -e ."
            )
        if not cfg.transport or not cfg.url:
            raise ValueError("`http_stateless` requires `transport` and `url`.")
        return (
            HttpStatelessClient(
                name=cfg.name,
                transport=cfg.transport,
                url=cfg.url,
                headers=cfg.headers,
                timeout=cfg.timeout,
                sse_read_timeout=cfg.sse_read_timeout,
            ),
            False,
        )
    if cfg.client_type == "stdio_stateful":
        if StdIOStatefulClient is None:
            raise RuntimeError(
                "MCP dependencies are missing. Install project dependencies first: pip install -e ."
            )
        if not cfg.command:
            raise ValueError("`stdio_stateful` requires `command`.")
        return (
            StdIOStatefulClient(
                name=cfg.name,
                command=cfg.command,
                args=cfg.args,
                env=cfg.env,
                cwd=cfg.cwd,
            ),
            True,
        )
    raise ValueError(f"Unsupported MCP client type: {cfg.client_type}")


async def auto_register_mcp_clients(
    toolkit: Toolkit, env: Mapping[str, str] | None = None
) -> MCPRegistrationManager:
    configs = load_mcp_configs_from_env(env)
    client_names: list[str] = []
    stateful_clients: list[Any] = []
    try:
        for cfg in configs:
            client, is_stateful = _build_client(cfg)
            if is_stateful:
                await client.connect()
                stateful_clients.append(client)
            await toolkit.register_mcp_client(
                mcp_client=client,
                group_name=cfg.group_name,
                enable_funcs=cfg.enable_funcs,
                disable_funcs=cfg.disable_funcs,
                preset_kwargs_mapping=cfg.preset_kwargs_mapping,
                namesake_strategy=cfg.namesake_strategy,  # type: ignore[arg-type]
            )
            client_names.append(cfg.name)
    except Exception:
        for client in reversed(stateful_clients):
            await client.close()
        raise
    return MCPRegistrationManager(client_names=client_names, _stateful_clients=stateful_clients)
