# Conventions for Hebrew in written work

How to use this tool's output in an article, a book chapter, or a set of notes.
The tool enforces none of this; it is the standard the tool was built to serve.

## Always name the edition

A Hebrew quotation without an edition is not a citation. `meturgaman text`
reports the edition, its source and its licence for every passage, and all three
belong in the footnote:

> בְּרֵאשִׁ֖ית בָּרָ֣א אֱלֹהִ֑ים
>
> Genesis 1:1, *Miqra according to the Masorah* (he.wikisource.org, CC-BY).

Editions disagree. Saying which one you read is what lets a reader check you.

## Three tiers, by what the quotation is doing

**Tier 1, the block quotation.** The text itself is the evidence. Hebrew and
translation, citation and edition underneath.

```
meturgaman study "Genesis 1:1" --tier block
```

**Tier 2, the teaching block.** The reader should be able to say the words.
Hebrew, romanization and translation stacked.

```
meturgaman study "Genesis 1:1" --tier teaching
```

**Tier 3, the inline gloss.** A phrase inside a sentence: the Hebrew, its
romanization in italics, a short translation in parentheses.

> The Mishnah's term is מוּעָד (*mu‘ad*, forewarned).

## Pick a scheme once, per piece, and say so

Mixing romanization standards inside one piece is the commonest fault and the
hardest to see. Decide at the start and put it in a note:

> Hebrew is romanized following the *SBL Handbook of Style*, 2nd ed., §5.1.2.

`sbl-general` is the default here and the right choice for most writing. Use
`sbl-academic` when the romanization is itself the object of study,
`encyclopaedia-judaica-general` when matching how a Jewish Studies reader expects
a word to look, and `bgn-pcgn` for Israeli place names.

To check a draft you have already written:

```
meturgaman detect "$(cat draft.md)"
```

## Words with an accepted English form stay in it

Torah, Talmud, Mishnah, Shabbat, Rosh Hashanah, mitzvah, halakhah. Romanize the
words a reader would not already know; leave alone the ones they would.

Encyclopaedia Judaica's note 3 says the same thing and goes further: biblical
names follow the Jewish Publication Society translation, and "names and some
words with an accepted English form are usually not transliterated."

## Register is the author's, not the tool's

A piece written in Ashkenazi register stays in it. Shabbos and Shabbat are not a
right answer and a wrong one; they are two communities.

`meturgaman romanize` refuses to convert one into the other and shows its
evidence. If a piece is genuinely mixed, that is worth fixing by choosing, not by
running a find and replace.

## Flags belong in the draft, not in the bin

When the tool flags a reading, the flag is telling you the orthography does not
settle the question. Two honest ways to handle it:

- Resolve it. Fetch an edition with meteg, or check a grammar, and move on.
- Say it. "*ḥokhmah*, though the vocalization here would also admit *ḥakhmah*"
  is a perfectly good sentence in a footnote.

What is not honest is deleting the flag and keeping the output.

## Aramaic uses the Hebrew system

SBL §5.2, in full: "The systems described above for Hebrew are to be followed,
even though tsere and holem are frequently not markers of long vowels in
Aramaic."

So a Talmudic passage is romanized under the same scheme as a biblical one. Where
a stretch of Aramaic behaves in a way the scheme did not anticipate, note it
rather than switching systems mid-page.

## Never invent

Not a verse, not a vocalization, not a citation. If it cannot be fetched, say it
cannot be fetched. This is the rule the whole tool exists to make easy to keep.
