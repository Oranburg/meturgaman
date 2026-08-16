Hebrew orthography is genuinely ambiguous in a few places, and each of them
has one mark doing two jobs: a dagesh is lene or forte, a sheva is vocal or
silent, a qamats is long or short, a vav is a consonant or half a vowel. The
engine decides these in the open, and where the rules cannot settle a
question it raises a flag rather than picking a default and staying quiet.

Output goes to stdout, flags to stderr. Under `--json` the flags travel
inside the document, so a pipeline consumer cannot lose them. A flag is the
tool saying "I made a decision the spelling alone does not justify"; the
right response is to check the word when the reading matters, and to carry
the uncertainty into whatever you write.

| Flag | What it means | What to do |
|---|---|---|
| `qamats-may-be-short` | Read long, which is the commoner reading of the shape, and a few words take short here | Check the word against a dictionary if the vowel matters; genuinely short words belong in `rules/qamats-qatan.md`, which the engine reads silently |
| `established-form` | English already spells this word a settled way (Torah, Hanukkah) | Decide whether the context wants the scheme's spelling or the established one; the tool names the convention rather than substituting it |
| `sheva-undecided` / `sheva-after-qamats` | The spelling does not say whether this sheva is pronounced | Check the received reading; Aramaic in particular often runs against the default |
| `unpointed` | No vowels are written and none can be recovered | Fetch a pointed edition, or run `meturgaman vocalize` and mark the result as a model's reading |
| `shin-undotted` | Shin and sin cannot be told apart here | Check the word; the tool will not guess |
| `script-mismatch` | A Yiddish scheme was used on Hebrew, or the reverse | Pick a scheme whose script matches the text |
| `source-gap` | The scheme's source document prints no row for this character | Read the scheme file's disclosure section; the gap is the standard's, and the tool refuses to invent a value |
| `distinction-not-in-scheme` | The text makes a distinction the scheme cannot express | Choose a richer scheme, or accept the merger knowingly |
| `scheme-unused` | A romanization scheme was passed to a rendering tier that carries no romanization line | Nothing; it says the option had no effect rather than leaving that to be inferred |

An example of a flag doing real work:

```
$ meturgaman romanize "קָנְיָא"
qaneya
  [qamats-may-be-short] (קָנְיָא) read long (a), which is the commoner reading
  of this shape. ...
  [sheva-after-qamats] (קָנְיָא) read as vocal, which is the commoner reading
  after a long qamats. ...
```

In this Aramaic word the received reading is *kanya*, with the sheva silent.
The flags are what let a reader catch that; silent output would not have.
