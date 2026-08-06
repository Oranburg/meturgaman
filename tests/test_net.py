"""The network layer, exercised entirely offline.

Nothing here opens a socket. The cache, the limiter, and the URL guard are the
pieces of net.py that can corrupt or mislead silently, and each test pins the
exact failure that motivated it.
"""

from __future__ import annotations

import json
import time

import pytest

from meturgaman import net


@pytest.fixture()
def cache(tmp_path, monkeypatch):
    monkeypatch.setenv("METURGAMAN_CACHE", str(tmp_path))
    monkeypatch.setattr(net, "CACHE_DISABLED", False)
    return tmp_path


def test_cache_round_trip(cache):
    net._write_cache("key", {"a": ["b", 1]})
    assert net._read_cache("key") == {"a": ["b", 1]}


def test_a_corrupt_entry_reads_as_a_miss(cache):
    net._write_cache("key", {"a": 1})
    path = net._cache_path("key")
    path.write_text("{ half of a json docu", encoding="utf-8")
    assert net._read_cache("key") is None


def test_an_expired_entry_reads_as_a_miss(cache):
    net._write_cache("key", {"a": 1})
    path = net._cache_path("key")
    old = time.time() - net.CACHE_SECONDS - 10
    import os
    os.utime(path, (old, old))
    assert net._read_cache("key") is None


def test_a_vanished_entry_reads_as_a_miss_not_a_crash(cache):
    # Another process can delete the entry between the stat and the read;
    # the old code did path.exists() then stat() and raised.
    assert net._read_cache("never written") is None


def test_writes_leave_no_partial_files_behind(cache):
    net._write_cache("key", {"a": 1})
    leftovers = [p for p in cache.iterdir() if p.suffix == ".tmp"]
    assert leftovers == []


def test_cache_disabled_reads_and_writes_nothing(cache, monkeypatch):
    net._write_cache("key", {"a": 1})
    monkeypatch.setattr(net, "CACHE_DISABLED", True)
    assert net._read_cache("key") is None
    net._write_cache("other", {"b": 2})
    monkeypatch.setattr(net, "CACHE_DISABLED", False)
    assert net._read_cache("other") is None


def test_clear_cache_counts_and_deletes(cache):
    net._write_cache("one", 1)
    net._write_cache("two", 2)
    assert net.clear_cache() == 2
    assert list(cache.glob("*.json")) == []


def test_cache_directory_refuses_a_file(tmp_path, monkeypatch):
    target = tmp_path / "actually-a-file"
    target.write_text("occupied", encoding="utf-8")
    monkeypatch.setenv("METURGAMAN_CACHE", str(target))
    with pytest.raises(net.NetworkError):
        net.cache_directory()


def test_error_payloads_are_not_cached(cache):
    assert net._is_error_payload({"error": "We are down"})
    assert not net._is_error_payload({"error": ""})
    assert not net._is_error_payload({"is_ref": False})
    assert not net._is_error_payload(["error"])


def test_rate_limit_refuses_a_zero_window():
    with pytest.raises(ValueError):
        net.RateLimit(requests=0, seconds=1.0)


def test_rate_limit_delays_the_burst_past_the_window():
    limiter = net.RateLimit(requests=2, seconds=0.2, name="test")
    started = time.monotonic()
    for _ in range(4):
        limiter.wait()
    elapsed = time.monotonic() - started
    # Four requests through a two-per-0.2s window cannot finish instantly.
    assert elapsed >= 0.2


def test_non_http_urls_are_refused(tmp_path):
    secret = tmp_path / "secret.txt"
    secret.write_text("do not read me", encoding="utf-8")
    with pytest.raises(net.NetworkError):
        net._request(f"file://{secret}")
    with pytest.raises(net.NetworkError):
        net.get_bytes("ftp://example.org/x")


def test_get_json_serves_from_cache_without_a_socket(cache):
    url = "https://api.example.org/thing"
    net._write_cache(url, {"served": "from cache"})
    found = net.get_json(url)
    assert found.from_cache
    assert found.payload == {"served": "from cache"}
