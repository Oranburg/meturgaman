"""The MCP server, spoken to over real stdio.

These tests run only when the optional SDK is installed; without it, the
entry point's contract is the refusal message, exercised separately. The
handshake here is the real protocol: initialize, list the tools, call one
that needs no network, and read the structured result back.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

mcp = pytest.importorskip("mcp", reason="the mcp extra is not installed")

SERVER = Path(sys.executable).parent / "meturgaman-mcp"
ALEPH = "א"


@pytest.fixture()
def handshake():
    proc = subprocess.Popen(
        [str(SERVER)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True,
        # Named rather than left to the locale: on Windows `text=True` alone
        # decodes the child by the active code page, and cp1252 cannot read
        # the Hebrew the server correctly writes. The wire is UTF-8 in both
        # directions, whatever the machine's code page says.
        encoding="utf-8",
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


def test_the_wire_is_utf8_whatever_the_machines_code_page_says():
    """The one property a Windows host cannot be trusted to supply.

    A client such as LM Studio spawns the server itself and sets no encoding,
    so on a cp1252 machine the question is whether Hebrew survives the trip.
    It does, and not by luck: the SDK's stdio transport re-wraps the raw
    binary buffers as UTF-8 rather than using the interpreter's text streams,
    whose platform encodings it calls unreliable. This test reads bytes, not
    text, under a parent that has asked for the worst case, so a future SDK
    that quietly went back to the code page would fail here rather than in
    someone's transcript.
    """
    hostile = dict(os.environ)
    hostile["PYTHONIOENCODING"] = "cp1252"
    hostile["PYTHONLEGACYWINDOWSSTDIO"] = "1"
    hostile.pop("PYTHONUTF8", None)
    proc = subprocess.Popen(
        [str(SERVER)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env=hostile,
    )

    def send(message):
        proc.stdin.write(json.dumps(message).encode("utf-8") + b"\n")
        proc.stdin.flush()

    try:
        send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "0"},
        }})
        proc.stdout.readline()
        send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        # Hebrew has to travel in as well as out: the flag quotes back the
        # very letter the request carried.
        send({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {
            "name": "romanize", "arguments": {"text": "קָנְיָא"},
        }})
        raw = proc.stdout.readline()
    finally:
        proc.terminate()
        proc.wait(timeout=10)

    # Aleph, as UTF-8 encodes it. Under the code page it would not be here.
    assert ALEPH.encode("utf-8") in raw
    reply = json.loads(raw.decode("utf-8"))
    payload = json.loads(reply["result"]["content"][0]["text"])
    assert payload["text"] == "qaneya"
    assert ALEPH in " ".join(payload["flags"])


@pytest.mark.network
def test_a_crowded_passage_does_not_arrive_as_a_wall(handshake):
    """The tools a model calls have to fit in the context it has.

    `links Genesis 1:1` is 1,817 records. Returned whole, with the service's
    own `_id`, `commentaryNum` and `compDate` on each, that was 1.3 MB --
    roughly 324,000 tokens for one call, delivered as a wall rather than as an
    error, so nothing in the transcript would say what went wrong. `chain` on
    the same verse was 109 KB.

    The caps exist to make the answer readable, so the counts have to be the
    true ones: a reader shown eight works and told there are sixty-five can
    ask for the rest, and a reader shown eight and told nothing will count
    them.
    """
    send, proc, _ = handshake
    send({"jsonrpc": "2.0", "id": 20, "method": "tools/call", "params": {
        "name": "links", "arguments": {"citation": "Genesis 1:1", "limit": 25},
    }})
    payload = json.loads(
        json.loads(proc.stdout.readline())["result"]["content"][0]["text"]
    )
    assert payload["returned"] == 25
    assert payload["total"] > 1000, "the true total, not the number shown"
    assert len(payload["links"]) == 25
    # Trimmed to what a reader uses; the service's internals stay behind.
    assert set(payload["links"][0]) == {
        "ref", "work", "category", "type", "anchor"
    }

    send({"jsonrpc": "2.0", "id": 21, "method": "tools/call", "params": {
        "name": "chain",
        "arguments": {
            "citation": "Genesis 1:1", "works_per_category": 3, "refs_per_work": 2
        },
    }})
    chain = json.loads(
        json.loads(proc.stdout.readline())["result"]["content"][0]["text"]
    )
    commentary = next(
        group for group in chain["chain"] if group["category"] == "Commentary"
    )
    assert commentary["works_shown"] == 3
    assert commentary["works_total"] > 3
    assert commentary["count"] > 100, "the category's real ref count"
    for work in commentary["works"].values():
        assert len(work["refs"]) <= 2
        assert work["more"] == work["count"] - len(work["refs"])
