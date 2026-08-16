"""The only module that touches the network.

Everything that leaves this machine goes through here, which makes three things
possible that are awkward otherwise: a single place to be polite about rate
limits, a single cache so repeated work does not repeatedly ask, and a single
honest answer about what was fetched and when.

Politeness is not optional here. Sefaria and Hebcal both give away a great deal
of work for nothing, and Hebcal states a limit of ninety requests in any ten
seconds. This respects that without being asked twice.

Standard library only. Both services are keyless JSON over HTTPS and `urllib`
does that.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any

__all__ = [
    "Fetched",
    "NetworkError",
    "RateLimit",
    "get_json",
    "post_json",
    "get_bytes",
    "cache_directory",
    "clear_cache",
    "USER_AGENT",
]

USER_AGENT = "meturgaman/0.1 (+https://github.com/Oranburg/meturgaman)"

#: How long a cached response stays good. Texts and calendars change rarely, and
#: a day is short enough that a correction reaches the user quickly.
CACHE_SECONDS = 24 * 60 * 60

#: Set by the CLI's --no-cache flag. When true, nothing is read from or written
#: to the cache, so a suspect answer can be refetched without hunting down and
#: deleting the entry that produced it.
CACHE_DISABLED = False


class NetworkError(Exception):
    """A request failed, with the service and the reason named."""


@dataclass
class Fetched:
    """A response, and where it came from."""

    payload: Any
    url: str
    from_cache: bool
    #: Attribution the service requires, ready to print. Empty when none is.
    attribution: str = ""


class RateLimit:
    """A sliding window, so a burst of calls does not trip a service's limit."""

    def __init__(self, requests: int, seconds: float, name: str = "") -> None:
        if requests < 1:
            # A window that admits nothing would make wait() index an empty
            # deque and never return. Refuse it at construction, loudly.
            raise ValueError("a rate limit must admit at least one request")
        self.requests = requests
        self.seconds = seconds
        self.name = name
        self._times: deque[float] = deque()
        # The two limiters below are module singletons, so any code that ever
        # fetches from two threads shares them. The lock keeps the deque sane.
        self._lock = threading.Lock()

    def wait(self) -> None:
        # A loop rather than recursion: a long queue of waiters must not grow
        # the call stack, and each pass re-reads the clock after sleeping.
        while True:
            with self._lock:
                now = time.monotonic()
                while self._times and now - self._times[0] > self.seconds:
                    self._times.popleft()
                if len(self._times) < self.requests:
                    self._times.append(now)
                    return
                sleep_for = self.seconds - (now - self._times[0]) + 0.05
            if sleep_for > 0:
                time.sleep(sleep_for)


def cache_directory() -> Path:
    """Where responses are kept. Override with METURGAMAN_CACHE."""
    override = os.environ.get("METURGAMAN_CACHE")
    if override:
        path = Path(override).expanduser()
    else:
        path = Path.home() / ".cache" / "meturgaman"
    try:
        path.mkdir(parents=True, exist_ok=True)
    except FileExistsError:
        # METURGAMAN_CACHE named an existing file. Say what is wrong instead
        # of letting mkdir's traceback stand in for an explanation.
        raise NetworkError(
            f"METURGAMAN_CACHE points at a file, not a directory: {path}"
        ) from None
    return path


def clear_cache() -> int:
    """Delete every cached response. Returns how many files went."""
    removed = 0
    for entry in cache_directory().glob("*.json"):
        # missing_ok because two processes may clear at once, and losing the
        # race to delete a file is the outcome we wanted anyway.
        entry.unlink(missing_ok=True)
        removed += 1
    return removed


def _cache_path(key: str) -> Path:
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]
    return cache_directory() / f"{digest}.json"


def _read_cache(key: str) -> Any | None:
    if CACHE_DISABLED:
        return None
    path = _cache_path(key)
    try:
        # stat and read both live inside the try: another process can delete
        # the entry between any two of these calls, and a vanished cache file
        # means refetch, never a traceback.
        if time.time() - path.stat().st_mtime > CACHE_SECONDS:
            return None
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        # A missing or damaged cache entry is not worth an error. Refetch.
        return None


def _write_cache(key: str, payload: Any) -> None:
    if CACHE_DISABLED:
        return
    try:
        path = _cache_path(key)
        # Write to a private temporary file and rename it into place. A plain
        # write_text let two concurrent processes interleave their bytes, and
        # a reader saw a half-written entry. os.replace is atomic on POSIX,
        # so a reader sees the old entry or the new one, never a mixture.
        handle, tmp_name = tempfile.mkstemp(
            dir=path.parent, prefix=path.stem, suffix=".tmp"
        )
        try:
            with os.fdopen(handle, "w", encoding="utf-8") as tmp:
                tmp.write(json.dumps(payload, ensure_ascii=False))
            os.replace(tmp_name, path)
        except BaseException:
            os.unlink(tmp_name)
            raise
    except (OSError, TypeError):
        # Caching is an optimization. Failing to cache is not failing.
        pass


def _is_error_payload(payload: Any) -> bool:
    """True when a 200 response is really the service reporting a failure.

    Sefaria and Hebcal both answer some failures with HTTP 200 and an `error`
    key in the body. Caching one of those kept a transient failure alive for a
    day: the service recovered in seconds and this tool kept repeating its
    outage. Answers that are legitimately negative, such as `is_ref: false`
    for a non-reference, carry no `error` key and are still cached.
    """
    return isinstance(payload, dict) and bool(payload.get("error"))


def _request(
    url: str,
    *,
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 30.0,
    service: str = "",
) -> bytes:
    scheme = urllib.parse.urlsplit(url).scheme.lower()
    if scheme not in ("http", "https"):
        # urllib happily opens file:// and ftp:// URLs, and audio download
        # URLs arrive from an API response rather than from this codebase.
        # A poisoned response must not be able to read local files.
        raise NetworkError(f"refusing a non-HTTP URL: {url}")
    combined = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if headers:
        combined.update(headers)
    request = urllib.request.Request(url, data=data, headers=combined)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()
    except urllib.error.HTTPError as error:
        detail = ""
        try:
            body = error.read().decode("utf-8", "replace")[:300]
            detail = f"\n  {body}" if body.strip() else ""
        except Exception:  # pragma: no cover
            pass
        raise NetworkError(
            f"{service or 'request'} returned HTTP {error.code} for {url}{detail}"
        ) from error
    except urllib.error.URLError as error:
        raise NetworkError(
            f"could not reach {service or url}: {error.reason}"
        ) from error
    except TimeoutError as error:
        raise NetworkError(f"{service or url} timed out after {timeout}s") from error


def get_json(
    url: str,
    params: dict[str, Any] | None = None,
    *,
    limiter: RateLimit | None = None,
    service: str = "",
    attribution: str = "",
    use_cache: bool = True,
    timeout: float = 30.0,
) -> Fetched:
    """GET a URL and parse it as JSON.

    A parameter whose value is a list becomes repeated parameters, which is how
    Sefaria's v3 texts endpoint asks for several editions at once:
    `?version=hebrew&version=english`.
    """
    query = ""
    if params:
        pairs: list[tuple[str, str]] = []
        for key, value in params.items():
            if value is None:
                continue
            if isinstance(value, (list, tuple)):
                pairs.extend((key, str(item)) for item in value)
            elif isinstance(value, bool):
                pairs.append((key, "1" if value else "0"))
            else:
                pairs.append((key, str(value)))
        query = urllib.parse.urlencode(pairs)
    full = f"{url}?{query}" if query else url

    if use_cache:
        cached = _read_cache(full)
        if cached is not None:
            return Fetched(
                payload=cached, url=full, from_cache=True, attribution=attribution
            )

    if limiter is not None:
        limiter.wait()

    raw = _request(full, timeout=timeout, service=service)
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as error:
        raise NetworkError(
            f"{service or full} returned something that is not JSON: "
            f"{raw[:200]!r}"
        ) from error

    if use_cache and not _is_error_payload(payload):
        _write_cache(full, payload)
    return Fetched(payload=payload, url=full, from_cache=False, attribution=attribution)


def post_json(
    url: str,
    body: Any,
    *,
    limiter: RateLimit | None = None,
    service: str = "",
    attribution: str = "",
    use_cache: bool = True,
    timeout: float = 30.0,
) -> Fetched:
    """POST a JSON body and parse the reply. Used for search and for find-refs."""
    encoded = json.dumps(body, ensure_ascii=False).encode("utf-8")
    key = f"{url}::{encoded.decode('utf-8')}"

    if use_cache:
        cached = _read_cache(key)
        if cached is not None:
            return Fetched(
                payload=cached, url=url, from_cache=True, attribution=attribution
            )

    if limiter is not None:
        limiter.wait()

    raw = _request(
        url,
        data=encoded,
        headers={"Content-Type": "application/json"},
        timeout=timeout,
        service=service,
    )
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as error:
        raise NetworkError(
            f"{service or url} returned something that is not JSON"
        ) from error

    if use_cache and not _is_error_payload(payload):
        _write_cache(key, payload)
    return Fetched(payload=payload, url=url, from_cache=False, attribution=attribution)


def get_bytes(
    url: str,
    *,
    limiter: RateLimit | None = None,
    service: str = "",
    timeout: float = 60.0,
) -> bytes:
    """Fetch raw bytes. Used for audio, which is not JSON and is not cached here."""
    if limiter is not None:
        limiter.wait()
    return _request(url, timeout=timeout, service=service)
