Most real questions are not citations. "What does Jewish law say about
lending at interest" wants a taught answer: the question as the tradition
frames it, the sources in their order, the disagreement if there is one, and
what turns on it. This page is the workflow the agent follows, and it works
just as well for a person at the command line.

## 1. Find where the tradition works the question

Sefaria's curated topic ontology beats full-text search for anything anyone
has thought about before:

```
meturgaman topics charity            # find the slug: tzedakah, not charity
meturgaman sources tzedakah --text   # the curated passages, with their text
meturgaman search "ribbit" --filter Halakhah   # only when no topic fits
```

## 2. Fetch what you will teach from

```
meturgaman text "Bava Metzia 75a:3-75b:12" --full
```

Every edition arrives with its language, its stated source, and its licence.
Editions marked locked or non-commercial get short quotation and paraphrase.

## 3. Walk the transmission

```
meturgaman chain "Mishnah Bava Metzia 5:11"    # the whole shelf, in order
meturgaman links "Bava Metzia 75b:2" --category Commentary
meturgaman related "Bava Metzia 75b"           # counts, topics, sheets
```

See [[The Corpus and Its Chains]] for what these return and how to read them.

## 4. Name the disagreement

The interesting answer to most real questions is that the tradition
disagrees. Say who holds what, on what grounds, and what turns on it. Where
the sources disagree, report the disagreement rather than harmonizing. Where
you found nothing, say you found nothing.

## The four disciplines

Each of these exists because an answer without it failed a hostile
verification pass (the evidence is in the repository under
`notes/agent-evaluation.md`):

1. **No census without an enumeration.** Do not say a work does something "in
   nine places" unless you fetched the work and counted. The one baseline
   answer that failed verification failed exactly here: every quotation was
   genuine and the overview was written from memory.
2. **No dressing your reading in the tool's authority.** Report what a
   command returned; argue your interpretation as your interpretation.
3. **Copy references exactly as fetched.** Sefaria's segmentation is what the
   reader will look up. Do not renumber from a remembered printed edition,
   and do not inherit a traditional citation number without checking it
   against the edition you actually fetched.
4. **A search snippet is a lead, not a source.** Sefaria's search index
   sometimes holds text a revised edition no longer contains. Fetch before
   quoting.
