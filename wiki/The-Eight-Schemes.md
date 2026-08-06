Eight published standards, one markdown file each in `schemes/`, every table
read off its source document and checked by a test that re-extracts the
source. No romanization table exists in Python anywhere in the repository.

| Scheme | Source | Use it when |
|---|---|---|
| `sbl-general` | SBL Handbook 2nd ed. §5.1.2 | general scholarly writing. The default. |
| `sbl-academic` | SBL Handbook 2nd ed. §5.1.1 | the romanization is itself the object of study and must be reversible |
| `ala-lc` | ALA-LC Romanization Table, Library of Congress | the result has to match a library catalogue record |
| `bgn-pcgn` | BGN/PCGN 2018 Agreement | Israeli place names, or anything official |
| `encyclopaedia-judaica-general` | EJ 2nd ed. vol. 1 p. 197 | matching how a Jewish Studies reader expects to see a word |
| `encyclopaedia-judaica-scientific` | EJ 2nd ed. vol. 1 p. 197 | comparative Semitics; several of its cells are alternatives, so check its output |
| `yivo` | YIVO Institute | Yiddish, and the closest published thing to Ashkenazi Hebrew |
| `ala-lc-yiddish` | ALA-LC, Yiddish column | Yiddish for a catalogue record |

```
meturgaman schemes                  # the list with sources
meturgaman schemes --name yivo      # one file in full, table and reasoning
meturgaman romanize "חָכְמָה" --scheme sbl-academic
meturgaman detect "Shabbos and halachah"    # which standard a text already uses
```

## Choosing in practice

- Writing for a journal or general scholarly prose: `sbl-general`. It is
  phonetic, unmarked for vowel length, and what most style sheets expect.
- Arguing about the Hebrew itself, where a reader must be able to reconstruct
  the spelling: `sbl-academic`.
- Citing a book the way a library catalogue cites it: `ala-lc`.
- Place names on a map or in anything official: `bgn-pcgn`.
- Matching the look of Jewish Studies reference works: the EJ general column.
- Yiddish, or Hebrew as Ashkenazim pronounce it: `yivo`. There is no
  published romanization table for Ashkenazi Hebrew as such; YIVO's treatment
  of the loshn-koydesh layer is the closest published thing, and it is what
  gives Shabbos rather than Shabbat.

## The register guard

`meturgaman romanize` refuses to rewrite Ashkenazi spelling as Sephardi and
prints its evidence, because that edit once happened silently across a whole
folder of notes. `--force` overrides it; do not reach for `--force` unless
the change of voice is actually wanted. `meturgaman register` reports which
community's romanization a text uses and why it thinks so.
