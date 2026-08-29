"""The contracts README is parsed as prose, so the parse is worth a test.

`docs/api/README.md` is written for a person and read by a script, which is the
arrangement this repository prefers over a machine format that can drift out of
step with its documentation. The cost of that choice is that an edit to the prose
can silently stop the script finding an entry, and a fetcher that quietly checks
two of three files is worse than one that fails.
"""

from __future__ import annotations

import pytest

from tools.fetch_contracts import Contract, read_readme


def test_reads_every_committed_contract():
    contracts = read_readme()
    names = {contract.name for contract in contracts}
    assert names == {
        "sefaria-openapi.json",
        "sefaria-llms.txt",
        "hebcal-openapi.json",
    }


def test_every_entry_carries_a_full_length_hash():
    for contract in read_readme():
        assert len(contract.sha256) == 64
        assert contract.sha256 == contract.sha256.lower()


def test_the_recorded_hashes_match_the_files_on_disk():
    """The whole point of recording a hash is that someone checks it.

    This is the test that would have caught the line-ending problem: the first
    hashes committed here were of Windows working copies rather than of the
    bytes the services serve, so they matched nothing on any other machine.
    """
    for contract in read_readme():
        assert contract.path.exists(), f"{contract.name} is recorded but not present"
        assert contract.on_disk_digest() == contract.sha256, (
            f"{contract.name} on disk does not match its recorded SHA-256"
        )


def test_an_entry_without_a_url_still_parses(tmp_path):
    """hebcal-openapi.json predates anyone writing down where it came from.

    Dropping such an entry would silently shrink the set of files anyone
    verifies, so it is kept with `url` as None and reported as unfetchable.
    """
    readme = tmp_path / "README.md"
    readme.write_text(
        "# Contracts\n\n"
        "**`with-url.json`**\n\n"
        "- URL `https://example.org/spec.json`\n"
        f"- SHA-256 `{'a' * 64}`\n\n"
        "**`no-url.json`**\n\n"
        "- URL not recorded when it was committed.\n"
        f"- SHA-256 `{'b' * 64}`\n",
        encoding="utf-8",
    )
    by_name = {c.name: c for c in read_readme(readme)}
    assert by_name["with-url.json"].url == "https://example.org/spec.json"
    assert by_name["no-url.json"].url is None


def test_an_entry_with_no_hash_is_an_error_rather_than_a_silent_skip(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text(
        "**`half-recorded.json`**\n\n- URL `https://example.org/spec.json`\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="half-recorded.json"):
        read_readme(readme)


def test_a_readme_naming_nothing_is_an_error(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text("# Contracts\n\nProse and no entries.\n", encoding="utf-8")
    with pytest.raises(ValueError, match="named no contracts"):
        read_readme(readme)


def test_a_missing_readme_says_so(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_readme(tmp_path / "absent.md")


def test_path_resolves_into_the_contracts_directory():
    contract = Contract(name="x.json", url=None, sha256="c" * 64)
    assert contract.path.parent.name == "api"
    assert contract.path.name == "x.json"
