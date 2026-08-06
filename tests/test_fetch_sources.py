"""The source fetcher, against a fabricated manifest and no network.

The fetcher is the integrity gate for every romanization table, so its failure
modes deserve tests: a hash mismatch must fail loudly, --check must never
touch the network, and --check --force must not report verified files missing,
which it once did.
"""

from __future__ import annotations

import hashlib

import pytest

from tools import fetch_sources


def _manifest(tmp_path, entries: list[tuple[str, bytes, str | None, int | None]]):
    """Build a manifest and its files.

    Each entry is (name, content, sha_override, size_override); None means
    record the truth.
    """
    lines = ["# Test manifest", ""]
    for name, content, sha, size in entries:
        recorded_sha = sha or hashlib.sha256(content).hexdigest()
        recorded_size = len(content) if size is None else size
        lines += [
            f"## {name}",
            "",
            f"- **File** `sources/pdf/{name}` ({recorded_size:,} bytes)",
            f"- **URL** https://example.org/{name}",
            f"- **SHA-256** `{recorded_sha}`",
            "",
        ]
    manifest = tmp_path / "manifest.md"
    manifest.write_text("\n".join(lines), encoding="utf-8")
    return manifest


@pytest.fixture()
def repo(tmp_path, monkeypatch):
    monkeypatch.setattr(fetch_sources, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(fetch_sources, "MANIFEST", tmp_path / "manifest.md")
    (tmp_path / "sources" / "pdf").mkdir(parents=True)
    return tmp_path


def _write(repo, name: str, content: bytes) -> None:
    (repo / "sources" / "pdf" / name).write_bytes(content)


def test_check_reports_verified_files_ok(repo, capsys):
    _manifest(repo, [("good.pdf", b"hello", None, None)])
    _write(repo, "good.pdf", b"hello")
    assert fetch_sources.main(["--check"]) == 0
    assert "ok" in capsys.readouterr().out


def test_check_with_force_still_reports_ok(repo, capsys):
    # The two flags together once reported every verified file as MISSING
    # and exited 1.
    _manifest(repo, [("good.pdf", b"hello", None, None)])
    _write(repo, "good.pdf", b"hello")
    assert fetch_sources.main(["--check", "--force"]) == 0
    out = capsys.readouterr().out
    assert "MISSING" not in out


def test_check_reports_a_missing_file_and_fails(repo, capsys):
    _manifest(repo, [("gone.pdf", b"hello", None, None)])
    assert fetch_sources.main(["--check"]) == 1
    assert "MISSING" in capsys.readouterr().out


def test_a_hash_mismatch_fails_and_leaves_the_file(repo, capsys):
    _manifest(repo, [("drift.pdf", b"original", None, None)])
    _write(repo, "drift.pdf", b"tampered")
    assert fetch_sources.main(["--check"]) == 1
    out = capsys.readouterr().out
    assert "MISMATCH" in out
    assert (repo / "sources" / "pdf" / "drift.pdf").read_bytes() == b"tampered"


def test_a_wrong_manifest_size_is_called_out(repo, capsys):
    # The byte count used to be printed as fact without ever being checked.
    _manifest(repo, [("sized.pdf", b"hello", None, 999)])
    _write(repo, "sized.pdf", b"hello")
    assert fetch_sources.main(["--check"]) == 0
    assert "fix the manifest" in capsys.readouterr().out


def test_a_missing_manifest_is_a_message_not_a_traceback(repo, capsys):
    assert fetch_sources.main(["--check"]) == 1
    assert "FAILED" in capsys.readouterr().err


def test_a_half_parsed_manifest_refuses(repo, capsys):
    manifest = repo / "manifest.md"
    manifest.write_text(
        "## Broken entry\n\n- **SHA-256** is mentioned but nothing parses\n",
        encoding="utf-8",
    )
    assert fetch_sources.main(["--check"]) == 1
    assert "FAILED" in capsys.readouterr().err


def test_read_manifest_parses_the_real_manifest():
    sources = fetch_sources.read_manifest()
    assert len(sources) == 6
    for source in sources:
        assert source.url.startswith("http")
        assert len(source.sha256) == 64
