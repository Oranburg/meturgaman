# Modern Israeli legislation

The classical library and the Israeli statute book are the same problem in
different clothes. In the library, the risk is a Hebrew text supplied from
memory. Here the Hebrew is usually the easy part and the English is the trap,
because an unattributed web copy of a statute reads exactly like an authorized
translation and nothing on its face separates them.

**Never translate a statute yourself and print it as the law.** Get the
authorized translation. The rule that governs Hebrew governs English:

> Never supply a translation from memory, and never produce one silently. A
> translation carries the authority of whoever made it, and that authority has
> to travel with the words.

## The registry works offline

Two commands read a local registry and need no network at all, which makes them
usable in a sandbox that has no egress:

    python3 scripts/mtg.py law statutes     # every statute the registry knows
    python3 scripts/mtg.py law tiers        # the authority ladder, in order

The rest of the `law` family fetches, so it needs either sandbox egress or the
web-fetch fallback:

    python3 scripts/mtg.py law sources remedies-1970     # where English can be had
    python3 scripts/mtg.py law hebrew remedies-1970      # consolidated Hebrew, with revision id
    python3 scripts/mtg.py law amendments remedies-1970  # which sections were amended, and by what

## The ladder, best first

| Tier | What it is |
|---|---|
| `enacted` | The English is law, or authentic treaty text. The CISG's English is authentic under its own Art. 101. |
| `authorized` | *Laws of the State of Israel* (L.S.I.), the Ministry of Justice's own English. Authorized and **not binding**; the Hebrew governs. |
| `government` | An Israeli government body's English with no translator named. |
| `commercial` | A named publisher. A.G. Publications (Arye Greenfield), Nevo, Halachot. |
| `scholarly` | A translation printed in a law review or treatise, translator named. |
| `unattributed` | A copy on the open web with no translator. A lead, not a source. |
| `assistant` | Produced by a model. Marked as such, and never printed as the law. |

Only `enacted` and `authorized` print as the law. `commercial` and `scholarly`
print with the translator named on the page. `unattributed` is good for
confirming a section number and for deciding whether a trip to the library is
worth making, and for nothing else. A hole that stays a hole is a good outcome.

## Where the authorized English actually is

L.S.I. covers volumes 1 to 45, roughly 1948 to 1989, so a statute enacted after
that has no authorized English at all, and the registry says so rather than
sending anyone to a volume that does not exist.

**HeinOnline does not hold the series**, checked inside it on an institutional
subscription 2026-08-09 by browsing rather than searching: its database picker
offers one Israeli database, Israel Law Reports, and the Foreign & International
Law Resources Database title index carries no L.S.I. among its 5,943 titles. A
print volume in a law library is the remaining route. Say that plainly instead
of fetching something weaker and letting it pass.

**What does work is the law reviews.** The *Israel Law Review* reprinted the
English of selected statutes in its Legislation section, sometimes as its own
item and sometimes appended to a commentary, and HeinOnline's Law Journal
Library holds all of it. That is how the Remedies Law (8 Isr. L. Rev. 135) and
the Contracts (General Part) Law (9 Isr. L. Rev. 282, behind Shalev's commentary
at 274) were obtained. **Browse the volume tables of contents; do not search.**
HeinOnline's full-text search silently drops the collection scope and returns
286,505 results for a phrase that has 4, while
`Page?handle=hein.journals/israel<VOL>&id=1` returns a reliable table of
contents every time.

**Check drift against the source, never against a guess.** `law amendments`
reads the amendment stamps the consolidated Hebrew already carries, so "the
interest amendment probably only touched damages" becomes a list. On the
Remedies Law it is § 11 alone; on the Contracts (General Part) Law it is § 25
alone, and § 25 is the interpretation section, amended three times since 1974,
so its old English and its current Hebrew are two different rules.

**Finding a law is a separate job from finding its English.** `law sources`
prints both registries. The Knesset's OData service at
`knesset.gov.il/Odata/ParliamentInfo.svc/` and the CKAN catalogue at
data.gov.il are keyless, live, and Hebrew only: fast for establishing which
instrument amended what, and no help at all with translation. Israel publishes
its legislation as structured open data and publishes no translation of it.

## The trap that costs the most

**L.S.I. prints the statute as enacted. A consolidated Hebrew text is current.**
Set a 1970 translation beside Hebrew amended in 2024 and the page prints two
different laws and calls one a translation of the other. Check every section
against the amending instruments before pairing it. Where a section has drifted,
print it with a dated note or leave it Hebrew only.

## When a machine translation is permitted, and what it costs

Almost never, and never quietly. `assistant` is the bottom of the ladder and it
does not print as the law under any circumstance. But refusing absolutely is not
the same as refusing well: where the authorized English genuinely cannot be had
and a lecturer would otherwise teach from a text he cannot read, a labelled
machine translation is better than a blank, **provided every one of these
holds**:

1. The authorized text was actually searched for, and the search is recorded:
   what was looked in, what was found, and what was not.
2. A named human authorizes it. Not an inference from convenience.
3. It is recorded at tier `assistant`, with `printableAsLaw: false`.
4. It carries a disclaimer naming it as a language model's work, with its date.
5. It carries a display label, and every page showing the text shows the label.
6. It states which Hebrew it translated, by revision id, because a translation
   of a consolidated current text and a translation of the enacted text are
   different documents.

**Translate as statute, not as prose.** Name every term of art you chose and the
alternatives you rejected; the reader has to be able to argue with your
vocabulary. Flag every ambiguity rather than resolving it silently. Do not
smooth knotty drafting into readable English, because a statute's awkwardness is
usually the drafter's precision. A confident translation with hidden guesses is
worse than an honest one with flagged holes.

## Pairing, and reconciling

    python3 scripts/mtg.py law parse delivery.txt --json
    python3 scripts/mtg.py law align --hebrew numbers.txt --english delivery.txt
    python3 scripts/mtg.py law reconcile --witness lsi=authorized:a.txt --witness web=unattributed:b.txt

`align` joins on the section number and exits non-zero on any section without a
counterpart. Pairing by position is how one short row shifts every later row
with nothing on the page to show it. `reconcile` classifies each section as
confirmed by two independent witnesses, held by one only, or disputed, and
prints both texts of a dispute rather than choosing. Two mirrors of one file are
one witness, not two.

Two shapes of Israeli statute defeat a naive read, and both are handled:

- A section's **marginal heading** is typeset in its own column, so flattening
  the columns drops it somewhere a naive read will misfile it. It is reported as
  a candidate and never merged into the text.
- A **spent provision** carries a heading and an editorial note where its body
  used to be, because a repealing or amending section's text is folded into the
  statute it changed and the consolidation then drops it. Remedies § 23 and Sale
  § 35 are both like this. The English will have text where the consolidated
  Hebrew has none, and that is correct rather than a gap.
