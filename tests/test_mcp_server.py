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
