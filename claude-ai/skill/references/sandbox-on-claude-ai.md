# The container this skill runs in

Read this when the probe reported a blocked host, or when a file has to change
hands in either direction.

## What the container is

Linux on x86_64, **Python 3.11**, one CPU, 5 GiB of memory, 5 GiB of workspace.
Nothing can be installed while it runs, which is why the `meturgaman` package is
vendored whole inside this skill and written against the standard library alone.
It needs Python 3.11 or newer and gets exactly that, with nothing to spare: the
probe checks the version first and stops if it is older.

Files in the workspace survive between turns of the same conversation. The
container is checkpointed after a few minutes of inactivity and restored on the
next message, and expires thirty days after it was made.

## Network egress is a setting, and the default is not enough

Whether this container can reach the internet at all is decided by an account
setting, not by the skill.

**Free, Pro and Max:** Settings → Capabilities.
**Team and Enterprise:** Organization settings → Capabilities, and only an
administrator can change it.

Four states, and only the last two are any use here:

| Setting | What this skill can do |
|---|---|
| Network egress off | Romanization, the schemes, `law tiers`, `law statutes`, `law sources`, `law parse`, `law align`, `law reconcile`. No text can be fetched at all. |
| Package managers only *(the Team and Enterprise default)* | The same. The allowlist is github.com, npm, PyPI, crates.io, Ubuntu, yarn and api.anthropic.com — every host this skill needs is absent. |
| Package managers **and specific domains** | Everything, once the three hosts below are added. This is the setting to ask for. |
| All domains | Everything, and rather more than this skill needs. |

The middle setting is the trap worth naming out loud. It sounds like network
access, it *is* network access, and it makes no difference whatever to this
skill, because the package index was never what was wanted.

### The three hosts to add

```
www.sefaria.org
www.hebcal.com
he.wikisource.org
```

- **www.sefaria.org** — texts and their editions, references, links, topics,
  sugya boundaries, dictionaries, search, and the learning calendar. Everything
  in the classical library goes through it. Recorded cantillation is served from
  a media URL that Sefaria's own payload names, which may be a fourth host; if
  the fetch fails after the other three are added, that is why.
- **www.hebcal.com** — the calendar family: `day`, `leyning`, `zmanim`,
  `yahrzeit`.
- **he.wikisource.org** — the consolidated Hebrew of Israeli statutes, with the
  revision id, behind `law hebrew` and `law amendments`.

Partial egress is a real state, which is why `scripts/probe.py` tests all three
separately rather than testing one and inferring the others.

### What egress buys that the fallback cannot

Two commands need to POST, and a web fetch can only GET, so these exist only
when the container itself can reach Sefaria:

- **`search`** — full-text search across the library. Without it, subject
  questions have to go through `topics`, which is better anyway for anything the
  tradition has a topic for, and simply unavailable for anything else. Say so
  rather than substituting a web search result.
- **`verify`** — the citation and quotation check over a draft, which needs
  `POST /api/find-refs` and then polls an async task. The degraded offer is
  citation validation alone; call it that and do not call it `verify`.

## Files, in and out

Nothing in this container touches the user's own disk.

**In.** The user attaches a file to the conversation and it arrives in the
workspace. Look for it rather than assuming a path, and name the file you
actually read in the answer. Every file has a 30 MB ceiling. This is how
`law parse`, `law align`, `law reconcile` and `verify` get their input: the user
attaches the delivered translation or the draft chapter, they do not name a path
on their laptop.

**Out.** A file is returned to the user only if it is sitting at the top level
of `$OUTPUT_DIR` when the command finishes. Files written anywhere else stay in
the container and are never seen. So write there, or copy there in the same
command, and list the directory in that command so the capture is visible:

```
python3 scripts/mtg.py study "Genesis 1" --tier file --output "$OUTPUT_DIR" && ls "$OUTPUT_DIR"
```

The `ls` is not decoration. The listing is the only evidence in reach that the
file was captured, so never tell the user a download is ready without having
seen it there.

## What this container cannot do at any setting

**Play audio.** `audio` can name the recording, its licence and its URL and hand
the user the link. PocketTorah's cantillation is real, CC-BY-SA and timestamped
to the verse, and giving someone the link is a good answer. Saying a passage was
played is not.

**Add vowel points with Dicta.** `vocalize` and `study --vocalize` want PyTorch,
Transformers and several hundred megabytes of model weights, none of which are in
this bundle and none of which can be downloaded. Offer the better answer instead,
which is an edition that already carries points: *Tanach with Nikkud* for Tanakh,
the vocalized William Davidson Aramaic for Bavli.

`references/capability-map.md` has the full three-way split of what works
offline, what needs the network, and what cannot be done here at all.
