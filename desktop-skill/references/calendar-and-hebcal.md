# The calendar family, and which host serves what

Short, because the only thing here that surprises people is the host split.

## Three hosts, not one

The CLI does not talk to a single service, and partial egress is a real state in
a sandbox. `scripts/probe.py` tests all three for this reason.

| Host | Commands it serves |
|---|---|
| `www.sefaria.org` | `text`, `editions`, `compare`, `links`, `related`, `chain`, `sugya`, `word`, `topics`, `sources`, `candidates`, `anchors`, `study`, and also `calendars` and `daf` |
| `www.hebcal.com` | `day`, `leyning`, `zmanim`, `yahrzeit` |
| `he.wikisource.org` | `law hebrew`, `law amendments` |

`calendars` and `daf` sit with Sefaria rather than with the rest of the calendar
family, so a sandbox that reaches Sefaria and not hebcal.com can still tell you
today's daf while failing to give you candle-lighting times.

## The commands

    python3 scripts/mtg.py day --date 2026-08-08 --register a
    python3 scripts/mtg.py calendars
    python3 scripts/mtg.py daf
    python3 scripts/mtg.py leyning --date 2026-08-08 --triennial
    python3 scripts/mtg.py yahrzeit 2020-03-15
    python3 scripts/mtg.py zmanim --zip 20902 --elevation 150

`day` also takes `--israel` for the Israeli holiday schedule and
`--after-sunset` when the civil date has already turned.

## Register

`--register` takes a Hebcal locale: `s` for Sephardi transliteration, `a` for
Ashkenazi, `ashkenazi_litvish` and the other Hebcal variants. Passing `a` gives
Ashkenazi forms of the holiday names, so a writer working in Ashkenazi register
keeps the calendar in register too rather than having *Shavuos* become *Shavuot*
halfway down a page.

This is the same discipline as the romanization rule about never flattening
someone's spelling. Match the register the surrounding writing already uses.

## Fetching the readings

Every reference the learning calendar names can be fetched as text. Get the
reference from `calendars` or `daf`, then pass it to `text`, and the passage
arrives with its edition and licence like any other.
