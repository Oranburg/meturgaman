# Words that already have an English spelling

Hebrew words a reader of English already knows how to spell. Romanizing them
under a scheme produces a technically correct form that looks wrong on the page:
*tôrâ* is what SBL academic says and *Torah* is what the word is called.

## How this file is used

**It flags. It does not substitute.** The engine romanizes by the scheme and
adds a note naming the conventional spelling:

```
$ meturgaman romanize "תּוֹרָה"
torah
  [established-form] (תּוֹרָה) English usually spells this Torah
```

That is deliberate. Silent substitution would make the tool unpredictable in the
one place a user most needs it to be literal, and it would mean the same word
came out differently depending on whether someone had thought to add it here.
`--established` performs the substitution when you want it; the flag tells you it
is available either way.

Encyclopaedia Judaica's note 3 states the underlying convention: "Names and some
words with an accepted English form are usually not transliterated."

## The list

| Hebrew | English | |
|---|---|---|
| תורה | Torah | |
| תלמוד | Talmud | |
| משנה | Mishnah | |
| כשר | kosher | lowercase; it is a common adjective in English |
| קבלה | Kabbalah | |
| סנהדרין | Sanhedrin | |
| קידושין | Kiddushin | the tractate |
| שבת | Shabbat | Ashkenazi register writes Shabbos; see `romanize/register.py` |
| ירושלים | Jerusalem | |
| משה | Moses | |
| רמבם | Maimonides | the acronym Rambam is also standard |
| מצוה | mitzvah | |
| הלכה | halakhah | |
| מדרש | midrash | |
| סידור | siddur | |
| תנך | Tanakh | |
| גמרא | Gemara | |
| רבי | Rabbi | |
| כנסת | Knesset | |
| שופר | shofar | |
| מנורה | menorah | |
| סוכה | sukkah | |
| חנוכה | Hanukkah | three spellings are in use; see the note below |
| פסח | Passover | Pesach is also standard |
| מזוזה | mezuzah | |
| ציצית | tzitzit | |
| תפילין | tefillin | |
| ישיבה | yeshiva | |
| רבנות | rabbinate | |

Matching is on the consonantal skeleton, so a pointed and an unpointed spelling
both find the entry.

## Hanukkah, and why one word gets a note

`חנוכה` is spelled *Chanukah*, *Hanukkah* and *Ḥanukah* in current English, and
the three are not free variants. *Chanukah* is Ashkenazi and Orthodox publishing,
*Hanukkah* is general American usage, and *Ḥanukah* is academic. Choosing one is
choosing a readership.

This file gives *Hanukkah* because it is the commonest English spelling, and
`meturgaman register` will tell you when the surrounding text wants a different
one.

## Adding to it

Add a word when English has a settled spelling that no scheme would produce.
Do not add a word merely because you have a preferred spelling of it; that is
what choosing a scheme is for. Every entry here is a place the tool will tell a
user their scheme is being overruled by convention, so each one should be a
convention rather than a taste.
