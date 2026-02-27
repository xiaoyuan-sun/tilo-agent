from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mcp_support.registry import auto_register_mcp_clients, load_mcp_configs_from_env


class _FakeToolkit:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def register_mcp_client(self, mcp_client: Any, **kwargs: Any) -> None:
        self.calls.append({"client": mcp_client, **kwargs})


class _StatefulClient:
    def __init__(self, name: str, **kwargs: Any) -> None:
        self.name = name
        self.kwargs = kwargs
        self.connected = False
        self.closed = False

    async def connect(self) -> None:
        self.connected = True

    async def close(self) -> None:
        self.closed = True


class _StatelessClient:
    def __init__(self, name: str, **kwargs: Any) -> None:
        self.name = name
        self.kwargs = kwargs


class _BrokenStatefulClient(_StatefulClient):
    async def connect(self) -> None:
        raise RuntimeError("connect failed")


def test_load_mcp_configs_from_env_parses_json() -> None:
    cfgs = load_mcp_configs_from_env(
        {
            "AGENTSCOPE_MCP_SERVERS": (
                '[{"name":"map","type":"http_stateless","transport":"streamable_http",'
                '"url":"https://example.com/mcp","group_name":"maps"}]'
            )
        }
    )
    assert len(cfgs) == 1
    assert cfgs[0].name == "map"
    assert cfgs[0].client_type == "http_stateless"
    assert cfgs[0].group_name == "maps"


def test_load_mcp_configs_from_env_rejects_invalid_json() -> None:
    with pytest.raises(ValueError, match="AGENTSCOPE_MCP_SERVERS"):
        load_mcp_configs_from_env({"AGENTSCOPE_MCP_SERVERS": "{"})


def test_load_mcp_configs_from_env_reads_os_environ_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "AGENTSCOPE_MCP_SERVERS",
        '[{"name":"map","type":"http_stateless","transport":"streamable_http","url":"https://example.com/mcp"}]',
    )
    cfgs = load_mcp_configs_from_env()
    assert len(cfgs) == 1
    assert cfgs[0].name == "map"


@pytest.mark.asyncio
async def test_auto_register_mcp_clients_registers_and_closes_stateful(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("mcp_support.registry.HttpStatefulClient", _StatefulClient)
    monkeypatch.setattr("mcp_support.registry.HttpStatelessClient", _StatelessClient)
    monkeypatch.setattr("mcp_support.registry.StdIOStatefulClient", _StatefulClient)

    toolkit = _FakeToolkit()
    manager = await auto_register_mcp_clients(
        toolkit,
        {
            "AGENTSCOPE_MCP_SERVERS": (
                "["
                '{"name":"fs","type":"stdio_stateful","command":"uvx","args":["mcp-server-filesystem","."]},'
                '{"name":"map","type":"http_stateless","transport":"streamable_http","url":"https://example.com/mcp"}'
                "]"
            )
        },
    )

    assert len(toolkit.calls) == 2
    assert toolkit.calls[0]["client"].name == "fs"
    assert toolkit.calls[1]["client"].name == "map"
    assert getattr(toolkit.calls[0]["client"], "connected", False) is True

    await manager.close()
    assert getattr(toolkit.calls[0]["client"], "closed", False) is True
    assert manager.client_names == ["fs", "map"]


@pytest.mark.asyncio
async def test_auto_register_mcp_clients_cleans_up_when_registration_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("mcp_support.registry.HttpStatefulClient", _StatefulClient)
    monkeypatch.setattr("mcp_support.registry.HttpStatelessClient", _StatelessClient)
    monkeypatch.setattr("mcp_support.registry.StdIOStatefulClient", _BrokenStatefulClient)

    toolkit = _FakeToolkit()

    with pytest.raises(RuntimeError, match="connect failed"):
        await auto_register_mcp_clients(
            toolkit,
            {
                "AGENTSCOPE_MCP_SERVERS": (
                    '[{"name":"fs","type":"stdio_stateful","command":"uvx","args":["mcp-server-filesystem","."]}]'
                )
            },
        )
