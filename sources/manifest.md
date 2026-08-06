# Sources

The published standards this project implements. **The PDFs are not committed.**
Two of them are copyrighted commercial publications and are not ours to
redistribute, so `sources/pdf/` is gitignored and only provenance lives here.

What *is* committed is the extracted table data in `schemes/`, because a table
of romanization correspondences is a set of facts rather than protectable
expression. Anyone can re-fetch a PDF from the URL below, check it against the
recorded hash, and re-verify the tables against it.

Retrieved 2026-08-05.

## ALA-LC Romanization Table: Hebrew and Yiddish

- **File** `sources/pdf/ala-lc.pdf` (131,364 bytes)
- **URL** https://www.loc.gov/catdir/cpso/romanization/hebrew.pdf
- **SHA-256** `0c0e8f41b24980281aab86cd96b2b97ae3ea3385e41d2c7e4452dda74951cc6d`
- **Rights** US Government (Library of Congress). Public domain.
- **Redistribution** redistributable

## BGN/PCGN 2018 Agreement, Romanization of Hebrew

- **File** `sources/pdf/bgn-pcgn.pdf` (357,352 bytes)
- **URL** https://assets.publishing.service.gov.uk/media/5e4d10d886650c10ee32f51f/ROMANIZATION_OF_HEBREW.pdf
- **SHA-256** `88445650e7285eb091e3a1a67d63f7addea27877273cb6e96527e8087d08c56f`
- **Rights** US/UK government publication.
- **Redistribution** redistributable

## SBL Handbook of Style, 2nd ed., §5

- **File** `sources/pdf/sbl-handbook.pdf` (180,476 bytes)
- **URL** https://www.uu.se/download/18.5bbc4a9418f774ee94a32a04/1716369935454/c_821854-l_3-k_transliterations-hebrew-and-greek-ur-sbl-handbook-of-style-of-style.pdf
- **SHA-256** `b317456babd752e88ede9da1038e6032ecbf63e9f337d81aea46290e4561343d`
- **Rights** Copyright SBL Press.
- **Redistribution** NOT redistributable

## Encyclopaedia Judaica, 2nd ed., vol. 1, p. 197

- **File** `sources/pdf/encyclopaedia-judaica.pdf` (39,736 bytes)
- **URL** https://jart.biu.ac.il/sites/jart/files/shared/transliteration_rules_heb_0.pdf
- **SHA-256** `27a3ca5b8a9c9c5597f210c780426f89d39cf975b6b2057d8f33a10d0006929c`
- **Rights** Copyright Keter/Gale.
- **Redistribution** NOT redistributable

## Hebraica Cataloging Manual (RDA rev. 2025)

- **File** `sources/pdf/hebraica-cataloging.pdf` (1,796,024 bytes)
- **URL** http://rascat.pbworks.com/w/file/fetch/160973124/HCM%20RDA%20rev25.pdf
- **SHA-256** `75a7ccc95446ba34fd41f0384a2a7d5f3d4b2c61e6114ef0718e72ecced796d2`
- **Rights** Library of Congress / cataloging community.
- **Redistribution** unclear; treated as NOT redistributable

## YIVO Institute for Jewish Research, Yiddish Alef-beys

- **File** `sources/html/yivo-alphabet.html` (70,049 bytes)
- **URL** https://www.yivo.org/Yiddish-Alphabet
- **SHA-256** `80bb269f94adb46d4bb7486e897fc09edce11cc3fa55217d256f48252883c27b`
- **Rights** Copyright YIVO Institute for Jewish Research.
- **Redistribution** NOT redistributable
- **Retrieved** 2026-08-06

The one source here that is a web page rather than a document, so its hash is of
the page as served on the date above. A page changes more readily than a PDF, and
a mismatch here is more likely to mean the site was redesigned than that the
standard moved. Check the tables before assuming either.

## Re-fetching

```bash
python -m tools.fetch_sources     # downloads and verifies every hash
```

A hash mismatch means the publisher changed the document. That is a fact worth
knowing before the tables are trusted, so the fetcher refuses rather than
overwriting.
