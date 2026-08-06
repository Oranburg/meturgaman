# Sacred names

Words the engine writes as a fixed form rather than romanizing letter by letter.

This is the one place the tool overrides its own tables by default, and the
reason is that the alternative is not a worse romanization but a thing that
should not be written at all. Spelling the Tetragrammaton out in Latin letters,
under any scheme, produces something many readers will not write and some will
not read aloud. The engine therefore does not produce it.

Everything else in this repository reports rather than decides. This file
decides, and says so.

## The forms

| Hebrew | Written as | Note |
|---|---|---|
| יהוה | HaShem | The Tetragrammaton, unpointed. |
| יְהֹוָה | HaShem | Pointed with the vowels of Adonai. |
| יְהוָה | HaShem | The commoner pointing in printed editions. |
| אֲדֹנָי | Adonai | The actual word, where the text has it. |
| אדני | Adonai | Unpointed. |

Matching is on the consonantal skeleton, so any pointing of the four letters
resolves to the same entry.

## What is deliberately absent

**Elohim, El, Eloheinu, Shaddai, Tzevaot** are not here. They are ordinary words
of the language and the schemes romanize them correctly: `אֱלֹהִים` gives
*elohim*. They are not substitutions for a name and do not need one.

**Ha-Shem written in Hebrew** (`הַשֵּׁם`) is likewise not here. It is a word,
and it romanizes as *ha-Shem* by the ordinary rules.

## The one judgement in the file

`אֲדֹנָי` is the actual word in some texts and a substitution for the
Tetragrammaton in others, and the difference is invisible to a machine. This file
writes *Adonai* in both cases, which is right in the first and defensible in the
second. A reader who needs the distinction is reading a pointed critical edition
and will see it.

## Turning this off

`meturgaman romanize --literal` writes what the scheme's table says, for anyone
whose work needs the letters as letters: a study of the divine names, a textual
apparatus, a Semitics paper. The flag exists because a tool that cannot be made
to do the thing has stopped being a tool.
