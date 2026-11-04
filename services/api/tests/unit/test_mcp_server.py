"""Tests for the stdio MCP wrapper in scripts/ghostshift_mcp.py (no network)."""

import importlib.util
import json
from pathlib import Path
from typing import Any

SCRIPT = Path(__file__).resolve().parents[4] / "scripts" / "ghostshift_mcp.py"
spec = importlib.util.spec_from_file_location("ghostshift_mcp", SCRIPT)
assert spec is not None and spec.loader is not None
mcp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mcp)


class Recorder:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict[str, Any] | None]] = []

    def __call__(self, method: str, path: str, body: dict[str, Any] | None) -> Any:
        self.calls.append((method, path, body))
        return {"ok": True}


def call(name: str, arguments: dict[str, Any], api: Recorder) -> dict[str, Any]:
    reply = mcp.handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        },
        api,
    )
    assert reply is not None
    result: dict[str, Any] = reply["result"]
    return result


def test_initialize_and_list_tools() -> None:
    api = Recorder()
    init = mcp.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}, api)
    assert init is not None and init["result"]["serverInfo"]["name"] == "ghostshift"
    listed = mcp.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, api)
    assert listed is not None
    assert {tool["name"] for tool in listed["result"]["tools"]} == set(mcp.ROUTES)
    assert mcp.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}, api) is None


def test_choose_maps_to_existing_route_and_body() -> None:
    api = Recorder()
    result = call(
        "ghostshift_choose", {"session_id": "s1", "choice_id": "c1", "expected_revision": 2}, api
    )
    assert result["isError"] is False
    assert api.calls == [
        ("POST", "/api/sessions/s1/choose", {"choice_id": "c1", "expected_revision": 2})
    ]
    assert json.loads(result["content"][0]["text"]) == {"ok": True}


def test_path_arguments_are_url_encoded() -> None:
    api = Recorder()
    call("ghostshift_verify_replay", {"session_id": "../x?y"}, api)
    assert api.calls == [("GET", "/api/sessions/..%2Fx%3Fy/replay", None)]


def test_invalid_arguments_and_unknown_tools_are_tool_errors() -> None:
    api = Recorder()
    assert call("ghostshift_choose", {"session_id": "s1"}, api)["isError"] is True
    assert call("ghostshift_get_session", {"session_id": "s1", "extra": 1}, api)["isError"] is True
    assert call("nope", {}, api)["isError"] is True
    assert api.calls == []


def test_api_failure_is_reported_not_swallowed() -> None:
    def failing(method: str, path: str, body: dict[str, Any] | None) -> Any:
        raise mcp.ToolError("GhostShift API returned HTTP 409: stale revision")

    result = call("ghostshift_get_session", {"session_id": "s1"}, failing)  # type: ignore[arg-type]
    assert result["isError"] is True and "409" in result["content"][0]["text"]
