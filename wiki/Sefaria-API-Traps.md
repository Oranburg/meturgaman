Behaviors of the live services that cost real debugging time in this
project. Each one is handled inside `meturgaman`, and they are recorded here
because anyone building directly on Sefaria or Hebcal will meet them too.

## Sefaria

- **`version=all` returns an empty `versions` list** and puts the metadata in
  `available_versions`. Asking for everything gets you nothing; the reader
  does a two-step fetch instead.
- **The `version` parameter wants the full language name.** `hebrew|Title`
  works; `he|Title` returns nothing, with no error. Use `languageFamilyName`.
- **Naming many editions in one query string returns HTTP 502.** Batch at
  six.
- **`/api/ref/` answers HTTP 200 with `is_ref: false`** and no error key for
  a string that is not a reference. Without checking that field, every
  fabricated citation validates. This is the single most important check in
  the package.
- **`/api/find-refs` is asynchronous.** It returns `{"task_id": ...}`; poll
  `GET /api/async/{task_id}` until `state == "SUCCESS"`.
- **Search needs `source_proj: true`** or every `_source` comes back empty.
- **`/api/name/` wants spaces, not underscores.**
- **Sefaria's name ranking is often wrong.** `Hilchot Deot` returns
  `Mishneh Torah, Repentance` first, which is a different book. Never
  auto-pick a suggestion; list candidates and let a person choose.
- **The search index can hold text a revised edition no longer contains.**
  A search hit is a lead; fetch the ref before quoting it. This was observed
  live with a frequently revised contemporary work.
- **Some services answer failures as HTTP 200 with an `error` key** in the
  body. Cache those and you keep a transient outage alive for a day.

## Hebcal

- **The yahrzeit endpoint's parameters are `y1`, `m1`, `d1`, `s1`, `t1`,
  `n1`.** The long spellings (`year1`, `month1`) are silently ignored and the
  reply is an empty item list that looks like "no yahrzeits exist."
- **The `lg` locale table is worth reading closely:** `sh` is Sephardic
  transliteration with Hebrew, despite the leading letters. The Ashkenazi
  locales are `a`, `ah`, and the four `ashkenazi_*` variants.
- **Hebcal states a limit of ninety requests per ten seconds.** Respect it.

## Unicode, while you are here

- `pdftotext` decomposes diacritics; NFC-normalize both sides before
  searching extracted text.
- U+034F COMBINING GRAPHEME JOINER appears in Sefaria's Masoretic text and
  sits outside the Hebrew block, so a naive "is this Hebrew" range check cuts
  words in half at it.
- U+05BA HOLAM HASER FOR VAV is used routinely by Sefaria and appears in no
  published romanization table.
