"""main(argv), driven exactly the way a shell would drive it.

main takes an argv list precisely so a test can call it. Everything here runs
offline: the commands exercised are the ones that never reach the network, and
the error paths are the ones that used to print tracebacks instead of reasons.
"""

from __future__ import annotations

import json

import pytest

from meturgaman.cli import main


def test_a_bad_scheme_name_refuses_instead_of_crashing(capsys):
    code = main(["romanize", "שָׁלוֹם", "--scheme", "no-such-scheme"])
    captured = capsys.readouterr()
    assert code == 1
    assert "refused:" in captured.err
    assert "Traceback" not in captured.err


def test_romanize_prints_the_result(capsys):
    code = main(["romanize", "שָׁלוֹם"])
    captured = capsys.readouterr()
    assert code == 0
    assert captured.out.strip() == "shalom"


def test_romanize_json_is_valid_json_with_flags_inside(capsys):
    # This Aramaic word raises qamats and sheva flags, and in JSON mode the
    # flags must live in the document, not on stderr.
    code = main(["romanize", "קָנְיָא", "--json"])
    captured = capsys.readouterr()
    assert code == 0
    payload = json.loads(captured.out)
    assert payload["scheme"] == "sbl-general"
    assert any("qamats" in flag for flag in payload["flags"])
    assert captured.err.strip() == ""


def test_the_register_guard_refuses_with_exit_2(capsys):
    code = main(["romanize", "Shabbos and halachah"])
    captured = capsys.readouterr()
    assert code == 2
    assert "Ashkenazi" in captured.err


def test_the_register_guard_yields_to_force(capsys):
    code = main(["romanize", "Shabbos and halachah", "--force"])
    assert code == 0


def test_detect_reports_evidence_and_admits_a_tie(capsys):
    code = main(["detect", "ḥokhmah"])
    captured = capsys.readouterr()
    assert code == 0
    assert "evidence" in captured.out.lower()
    # This particular string ties across several schemes, and the honest
    # output says so instead of picking one.
    assert "not a determination" in captured.out


def test_detect_json_lists_guesses(capsys):
    code = main(["detect", "Shabbos and halachah", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["guesses"]
    assert {"scheme", "score", "matched"} <= set(payload["guesses"][0])


def test_schemes_lists_all_eight(capsys):
    code = main(["schemes"])
    captured = capsys.readouterr()
    assert code == 0
    assert "sbl-general (default)" in captured.out
    assert captured.out.count("script hebrew") >= 6


def test_schemes_json_round_trips(capsys):
    code = main(["schemes", "--json"])
    payload = json.loads(capsys.readouterr().out)
    names = {entry["name"] for entry in payload["schemes"]}
    assert "yivo" in names and "sbl-academic" in names
    assert sum(entry["is_default"] for entry in payload["schemes"]) == 1


def test_reverse_offers_candidates(capsys):
    code = main(["reverse", "shalom"])
    captured = capsys.readouterr()
    assert code == 0
    assert captured.out.strip()


def test_register_reads_ashkenazi_evidence(capsys):
    code = main(["register", "Shabbos and mitzvos"])
    captured = capsys.readouterr()
    assert code == 0
    assert "ashkenazi" in captured.out.lower()


def test_an_out_of_range_limit_is_an_argument_error(capsys):
    # Unbounded limits went straight into the service's query and came back
    # as an HTTP 500 that read like the service's fault. argparse exits 2.
    with pytest.raises(SystemExit) as caught:
        main(["search", "ribbit", "--limit", "-5"])
    assert caught.value.code == 2
    assert "between 1 and 100" in capsys.readouterr().err

    with pytest.raises(SystemExit) as caught:
        main(["search", "ribbit", "--limit", "100000"])
    assert caught.value.code == 2


def test_a_non_numeric_limit_is_an_argument_error(capsys):
    with pytest.raises(SystemExit) as caught:
        main(["topics", "charity", "--limit", "many"])
    assert caught.value.code == 2
    assert "not a whole number" in capsys.readouterr().err


def test_clear_cache_reports_what_it_removed(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("METURGAMAN_CACHE", str(tmp_path))
    (tmp_path / "aa.json").write_text("{}", encoding="utf-8")
    code = main(["clear-cache"])
    captured = capsys.readouterr()
    assert code == 0
    assert "removed 1" in captured.out


def test_no_cache_flag_disables_the_cache(monkeypatch):
    from meturgaman import net

    monkeypatch.setattr(net, "CACHE_DISABLED", False)
    # romanize is offline, so this proves the flag plumbing without a socket.
    main(["romanize", "שָׁלוֹם", "--no-cache"])
    assert net.CACHE_DISABLED
    monkeypatch.setattr(net, "CACHE_DISABLED", False)
