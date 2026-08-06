Sefaria organizes the library into categories that mirror the tradition's own
shelf order: Tanakh, Targum, Mishnah, Tosefta, Talmud, Midrash, Commentary,
Halakhah, Kabbalah, Liturgy, Jewish Thought, Chasidut, Musar, Responsa. A
halakhic question travels a known road through those shelves: Torah verse,
Mishnah, Gemara, the Rishonim, Mishneh Torah and the Shulchan Arukh with
their commentators, then responsa. An aggadic or conceptual question travels
a different one, through midrash and Jewish thought. Knowing which road a
question belongs to is most of knowing where to look.

## chain: the shelf order for one passage

```
$ meturgaman chain "Mishnah Bava Metzia 5:11"
Mishnah Bava Metzia 5:11: what the tradition built on this passage

Tanakh  (5)
    Exodus       Exodus 22:24
    ...
Talmud  (3)
    Bava Metzia  Bava Metzia 75a:11-75b:4
Commentary  (43)
Quoting Commentary  (6)
Halakhah  (1)
```

Every entry is a link Sefaria records and every ref can be fetched with
`meturgaman text`; the command only adds the ordering. Reading down from a
Gemara shows where its law lands in the codes. Reading up from a code shows
where its ruling began. `--full` prints every ref in every work; `--json`
gives the same structure to a program.

## links: the graph, filtered and flat

```
meturgaman links "Bava Metzia 75b:2" --category Commentary
meturgaman links "Bava Metzia 75b:2" --category Halakhah
meturgaman links "Bava Metzia 75b:2" --refs-only    # bare refs, for piping
```

Category names are Sefaria's own. Commentary on a Talmud passage includes
Rashi, Tosafot, the Rishonim's running commentaries, and the Steinsaltz
explanations; Halakhah links carry the passage into Mishneh Torah, the Tur,
and the Shulchan Arukh.

## related: everything at once

```
meturgaman related "Bava Metzia 75b"
```

One call summarizes the link counts by category, the topics Sefaria attaches
to the passage, and how many source sheets, manuscripts, and recordings
exist. Use it to decide where to dig before fetching anything.

## sugya: the argument's boundary

```
$ meturgaman sugya "Bava Metzia 75b:2"
Bava Metzia 75a:11-75b:4
```

A page of Talmud is a physical unit, not an argument, and the mapped passage
regularly crosses the page in both directions. Fetch the whole boundary
before walking an argument, and expect one page to hold several passages.

## word: the terms

```
meturgaman word אסמכתא
```

Dictionary entries with Jastrow's citations back into the corpus, which makes
the dictionary a second index: look up a term of art, then fetch the passages
its entry cites.
