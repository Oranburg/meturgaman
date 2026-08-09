"""main(argv), driven exactly the way a shell would drive it.

main takes an argv list precisely so a test can call it. Everything here runs
offline: the commands exercised are the ones that never reach the network, and
the error paths are the ones that used to print tracebacks instead of reasons.
"""

from __future__ import annotations

import json

import pytest

from meturgaman.cli import main


def test_verify_on_a_missing_file_refuses_in_its_own_voice(capsys):
    code = main(["verify", "/nonexistent/path/does-not-exist.md"])
    captured = capsys.readouterr()
    assert code == 1
    assert "refused:" in captured.err
    # A bare OSError repr ("[Errno 2] No such file or directory: ...") is
    # Python's voice, not this tool's; the message must not leak it verbatim.
    assert "Errno" not in captured.err
    assert "does-not-exist.md" in captured.err


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


# ---------------------------------------------------------------------------
# `meturgaman law`, the Israeli legislation group
# ---------------------------------------------------------------------------

LAW_FIXTURE = "tests/fixtures/remedies-1970.web-copy.txt"


@pytest.mark.parametrize(
    "action",
    ["tiers", "statutes"],
)
def test_the_law_group_takes_json_after_the_action_name(capsys, action):
    """`--json` has to work where a hand puts it, which is last.

    Attached only to the `law` group and not to its actions, argparse rejected
    it after the action name with "unrecognized arguments: --json", which is
    exactly where anyone types it.
    """
    assert main(["law", action, "--json"]) == 0
    json.loads(capsys.readouterr().out)


def test_law_tiers_marks_only_the_two_printable_as_law(capsys):
    main(["law", "tiers", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["printable_as_law"] == ["authorized", "enacted"]
    assert payload["ladder"][0] == "enacted"


def test_law_sources_omits_lsi_for_a_statute_the_series_never_reached(capsys):
    main(["law", "sources", "int-sale-1999", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert "lsi" not in [row["key"] for row in payload["sources"]]


def test_an_unknown_statute_slug_refuses_and_lists_the_known_ones(capsys):
    code = main(["law", "sources", "sale-law"])
    captured = capsys.readouterr()
    assert code == 1
    assert "refused:" in captured.err
    assert "sale-1968" in captured.err


def test_law_parse_reports_the_sections_it_found(capsys):
    assert main(["law", "parse", LAW_FIXTURE, "--json"]) == 0
    rows = json.loads(capsys.readouterr().out)
    assert [row["number"] for row in rows] == [str(n) for n in range(1, 26)]


def test_law_parse_refuses_a_file_with_no_sections_rather_than_returning_nothing(
    capsys, tmp_path
):
    """An empty result that looks like an answer is the failure this tool is built against."""
    path = tmp_path / "prose.txt"
    path.write_text("A paragraph with no section numbering at all.\n", encoding="utf-8")
    code = main(["law", "parse", str(path)])
    captured = capsys.readouterr()
    assert code == 1
    assert "refused:" in captured.err


def test_law_align_exits_non_zero_on_a_section_with_no_counterpart(capsys, tmp_path):
    numbers = tmp_path / "numbers.txt"
    numbers.write_text("\n".join(str(n) for n in range(1, 27)), encoding="utf-8")
    code = main(["law", "align", "--hebrew", str(numbers), "--english", LAW_FIXTURE])
    assert code == 1
    assert "HEBREW WITH NO ENGLISH" in capsys.readouterr().out


def test_law_align_exits_zero_when_every_section_pairs(capsys, tmp_path):
    numbers = tmp_path / "numbers.txt"
    numbers.write_text("\n".join(str(n) for n in range(1, 26)), encoding="utf-8")
    code = main(["law", "align", "--hebrew", str(numbers), "--english", LAW_FIXTURE])
    assert code == 0


def test_law_reconcile_refuses_a_witness_spelled_wrong(capsys):
    code = main(["law", "reconcile", "--witness", f"web:{LAW_FIXTURE}"])
    captured = capsys.readouterr()
    assert code == 1
    assert "key=tier:path" in captured.err


def test_law_reconcile_refuses_an_unknown_tier(capsys):
    code = main(["law", "reconcile", "--witness", f"web=offical:{LAW_FIXTURE}"])
    captured = capsys.readouterr()
    assert code == 1
    assert "not a tier" in captured.err
