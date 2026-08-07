"""The MCP server, spoken to over real stdio.

These tests run only when the optional SDK is installed; without it, the
entry point's contract is the refusal message, exercised separately. The
handshake here is the real protocol: initialize, list the tools, call one
that needs no network, and read the structured result back.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

mcp = pytest.importorskip("mcp", reason="the mcp extra is not installed")

SERVER = Path(sys.executable).parent / "meturgaman-mcp"


@pytest.fixture()
def handshake():
    proc = subprocess.Popen(
        [str(SERVER)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True,
    )

    def send(message):
        proc.stdin.write(json.dumps(message) + "\n")
        proc.stdin.flush()

    send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "test", "version": "0"},
    }})
    initialized = json.loads(proc.stdout.readline())
    send({"jsonrpc": "2.0", "method": "notifications/initialized"})
    try:
        yield send, proc, initialized
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def test_the_server_identifies_itself(handshake):
    _, _, initialized = handshake
    assert initialized["result"]["serverInfo"]["name"] == "meturgaman"


def test_the_toolset_is_complete(handshake):
    send, proc, _ = handshake
    send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    tools = json.loads(proc.stdout.readline())
    names = {tool["name"] for tool in tools["result"]["tools"]}
    assert {
        "text", "chain", "links", "romanize", "detect", "verify_draft",
        "anchors", "topics", "topic_sources", "search", "word", "sugya",
        "calendars",
    } <= names


def test_romanize_answers_offline_with_flags_inside(handshake):
    send, proc, _ = handshake
    send({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {
        "name": "romanize", "arguments": {"text": "קָנְיָא"},
    }})
    reply = json.loads(proc.stdout.readline())
    content = reply["result"]["content"][0]["text"]
    payload = json.loads(content)
    assert payload["text"] == "qaneya"
    assert payload["scheme"] == "sbl-general"
    # Uncertainty travels in the result, never on a stderr nobody reads.
    assert any("sheva" in flag for flag in payload["flags"])


def test_romanize_scheme_carries_an_enum_a_cold_client_can_read(handshake):
    """A client that has never read the source should not have to guess a
    scheme name and eat an error to learn the real vocabulary."""
    send, proc, _ = handshake
    send({"jsonrpc": "2.0", "id": 4, "method": "tools/list"})
    tools = json.loads(proc.stdout.readline())["result"]["tools"]
    romanize_tool = next(t for t in tools if t["name"] == "romanize")
    enum = romanize_tool["inputSchema"]["properties"]["scheme"].get("enum")
    assert enum is not None
    assert "sbl-general" in enum
    assert "yivo" in enum
    # Blank stays valid: it is the sentinel for "use the default scheme".
    assert "" in enum


def test_every_tool_is_marked_read_only(handshake):
    send, proc, _ = handshake
    send({"jsonrpc": "2.0", "id": 5, "method": "tools/list"})
    tools = json.loads(proc.stdout.readline())["result"]["tools"]
    for tool in tools:
        annotations = tool.get("annotations") or {}
        assert annotations.get("readOnlyHint") is True, tool["name"]


def test_calendars_refuses_a_malformed_date_cleanly(handshake):
    """A raw unpack error, or worse, silent garbage sent to the service, is
    what a cold client used to get from a date shaped like "not-a-date"."""
    send, proc, _ = handshake
    send({"jsonrpc": "2.0", "id": 6, "method": "tools/call", "params": {
        "name": "calendars", "arguments": {"date": "not-a-date"},
    }})
    reply = json.loads(proc.stdout.readline())["result"]
    assert reply.get("isError") is True
    message = reply["content"][0]["text"]
    assert "not-a-date" in message
    assert "unpack" not in message
