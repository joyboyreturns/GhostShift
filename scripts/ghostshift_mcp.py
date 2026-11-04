#!/usr/bin/env python3
"""GhostShift MCP server (stdio, standard library only).

Lets an MCP client such as Kiro rehearse a playbook through the running GhostShift API.
Every tool is a thin wrapper over an existing /api route; nothing here interprets policy or
fabricates results. Errors from the API are returned verbatim as tool errors.

Authored by Claude Code (not Kiro). Environment: GHOSTSHIFT_API_URL (default http://127.0.0.1:8000).
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from typing import Any

PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "ghostshift", "version": "0.1.0"}
TIMEOUT_SECONDS = 15

ApiCall = Callable[[str, str, "dict[str, Any] | None"], Any]


def _schema(properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {"type": "object", "properties": properties, "required": required, "additionalProperties": False}


_ID = {"type": "string", "minLength": 1, "maxLength": 100}

TOOLS: list[dict[str, Any]] = [
    {
        "name": "ghostshift_health",
        "description": "Check that the GhostShift API is reachable.",
        "inputSchema": _schema({}, []),
    },
    {
        "name": "ghostshift_list_demos",
        "description": "List the prepared fictional demo playbooks and their scenario IDs.",
        "inputSchema": _schema({}, []),
    },
    {
        "name": "ghostshift_start_rehearsal",
        "description": (
            "Start a rehearsal session for a scenario. Returns the session including its current node, "
            "available choices and status. Seeded rules are drafts, so draft rehearsal must be allowed explicitly."
        ),
        "inputSchema": _schema(
            {"scenario_id": _ID, "allow_draft_rehearsal": {"type": "boolean", "default": False}},
            ["scenario_id"],
        ),
    },
    {
        "name": "ghostshift_choose",
        "description": (
            "Record one choice in a session. The engine stops at an uncovered path (zero matching rules) "
            "or an overlap (several), and records a deviation if the choice does not match the model."
        ),
        "inputSchema": _schema(
            {"session_id": _ID, "choice_id": _ID, "expected_revision": {"type": "integer", "minimum": 0}},
            ["session_id", "choice_id", "expected_revision"],
        ),
    },
    {
        "name": "ghostshift_get_session",
        "description": "Read a session's current state and event ledger.",
        "inputSchema": _schema({"session_id": _ID}, ["session_id"]),
    },
    {
        "name": "ghostshift_verify_replay",
        "description": "Replay a session's append-only events and return the verified state hash.",
        "inputSchema": _schema({"session_id": _ID}, ["session_id"]),
    },
    {
        "name": "ghostshift_session_report",
        "description": "Return the after-action report with quoted sources and replay inputs.",
        "inputSchema": _schema({"session_id": _ID}, ["session_id"]),
    },
]

# tool name -> (method, path template, body keys). Path templates use argument names.
ROUTES: dict[str, tuple[str, str, tuple[str, ...]]] = {
    "ghostshift_health": ("GET", "/api/health", ()),
    "ghostshift_list_demos": ("GET", "/api/demo", ()),
    "ghostshift_start_rehearsal": ("POST", "/api/sessions", ("scenario_id", "allow_draft_rehearsal")),
    "ghostshift_choose": ("POST", "/api/sessions/{session_id}/choose", ("choice_id", "expected_revision")),
    "ghostshift_get_session": ("GET", "/api/sessions/{session_id}", ()),
    "ghostshift_verify_replay": ("GET", "/api/sessions/{session_id}/replay", ()),
    "ghostshift_session_report": ("GET", "/api/sessions/{session_id}/report", ()),
}


class ToolError(Exception):
    """A tool failed; the message is returned to the client as tool output."""


def http_call(method: str, path: str, body: dict[str, Any] | None) -> Any:
    base = os.environ.get("GHOSTSHIFT_API_URL", "http://127.0.0.1:8000").rstrip("/")
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(  # noqa: S310 - scheme fixed by operator-set base URL
        base + path, data=data, method=method, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:  # noqa: S310
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as error:
        detail = error.read().decode(errors="replace")[:2000]
        raise ToolError(f"GhostShift API returned HTTP {error.code}: {detail}") from error
    except (urllib.error.URLError, TimeoutError, ConnectionError) as error:
        raise ToolError(f"Cannot reach the GhostShift API at {base}: {error}") from error


def call_tool(name: str, arguments: dict[str, Any], api: ApiCall) -> Any:
    route = ROUTES.get(name)
    if route is None:
        raise ToolError(f"Unknown tool: {name}")
    method, template, body_keys = route
    declared = next(tool for tool in TOOLS if tool["name"] == name)["inputSchema"]
    unknown = set(arguments) - set(declared["properties"])
    missing = [key for key in declared["required"] if key not in arguments]
    if unknown or missing:
        raise ToolError(f"Invalid arguments: unknown={sorted(unknown)} missing={missing}")
    path = template.format(**{k: urllib.parse.quote(str(v), safe="") for k, v in arguments.items()})
    body = {key: arguments[key] for key in body_keys if key in arguments} if method == "POST" else None
    return api(method, path, body)


def handle(message: dict[str, Any], api: ApiCall) -> dict[str, Any] | None:
    """Handle one JSON-RPC message; return a response or None for notifications."""
    method = message.get("method")
    request_id = message.get("id")
    if request_id is None:
        return None  # notifications such as notifications/initialized
    if method == "initialize":
        result: dict[str, Any] = {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": SERVER_INFO,
        }
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": TOOLS}
    elif method == "tools/call":
        params = message.get("params") or {}
        try:
            payload = call_tool(str(params.get("name")), params.get("arguments") or {}, api)
            result = {"content": [{"type": "text", "text": json.dumps(payload, indent=2)}], "isError": False}
        except ToolError as error:
            result = {"content": [{"type": "text", "text": str(error)}], "isError": True}
    else:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": f"Method not found: {method}"}}
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def main() -> None:
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            reply: dict[str, Any] | None = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": "Parse error"},
            }
        else:
            reply = handle(message, http_call) if isinstance(message, dict) else None
        if reply is not None:
            sys.stdout.write(json.dumps(reply) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
