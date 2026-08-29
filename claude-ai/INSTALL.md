# Meturgaman on claude.ai

The same instrument as the command line tool, packaged for the places Claude
runs without a terminal. There are two halves and they are installed separately:
a **skill**, which is a zip you upload once, and an **agent**, which is the
standing instruction that makes Claude reach for the skill and hold the line on
what an answer has to carry.

The skill is the same on every surface. The agent is not, because "agent" means
three different things depending on where you are, so there are three of them.

## The skill

### 1. Build the zip

```
python tools/build_skill.py --surface claude-ai
```

Or `python tools/build_skill.py` with no argument to build the Claude Desktop
package alongside it; they share almost everything and both get proven.

`python`, not `python3`. This command runs on your own machine, and Windows has
no `python3` on the path: it ships a `python3.exe` App Execution Alias that opens
the Microsoft Store instead of an interpreter, so `python3` there fails with
advice about the Store and nothing to do with this repository. On macOS and Linux
either name works. The `python3` inside the skill's own pages is a different
matter and correct as written, because that runs in a Linux container.

It writes `dist/meturgaman-claude-ai-skill.zip`, about 366 KB. The script stages
the tree, resolves the three symlinks under `meturgaman/data/` into real
directories, validates the frontmatter against what claude.ai actually rejects,
packs the archive, then extracts it somewhere new with a cold `HOME` and an empty
`PYTHONPATH` and runs ten commands inside it. Read the last block of its output:
`crashes: 0` is the whole point of the exercise, and the two live cases at the
bottom also tell you whether your own machine can reach Sefaria.

The vendored package is standard library only and needs no install step, which is
what lets it run where nothing can be downloaded. It wants Python 3.11 or newer;
the container runs exactly 3.11.

### 2. Upload it

**Settings → Capabilities → Skills → upload.** Pro, Max, Team and Enterprise,
with code execution turned on. Custom skills on claude.ai are per-user: they are
not shared across a team and cannot be pushed by an administrator, so everyone who
wants this uploads it themselves.

Skills do not sync across surfaces. A skill uploaded to claude.ai is not available
through the API, and neither is available to Claude Code, which reads
`~/.claude/skills/` and `.claude/skills/` off the filesystem instead.

### 3. Let the sandbox reach three hosts

**This is the step that decides whether the skill can fetch anything at all**, and
the default setting is not enough.

Go to **Settings → Capabilities** (on Team and Enterprise, Organization settings →
Capabilities, and an administrator has to do it). Set network egress to **package
managers and specific domains**, and add:

```
www.sefaria.org
www.hebcal.com
he.wikisource.org
```

The setting immediately below the one you want is *package managers only*, and it
is the trap worth naming: it is real network access, it is the Team and Enterprise
default, and it makes no difference whatever here, because its allowlist is PyPI,
npm, crates.io, GitHub and Ubuntu and this skill wanted none of them.

Sefaria serves the texts, their editions, the link graph, topics, sugya
boundaries, dictionaries, search and the learning calendar. Hebcal serves the
calendar, readings, zmanim and yahrzeits. he.wikisource.org serves the
consolidated Hebrew of Israeli statutes with its revision id. Partial egress is a
real state, so the skill's probe tests all three separately.

With egress off, the skill still romanizes under all eight schemes, detects which
standard a text uses, reads the register, prints the statute authority ladder and
the registry, and parses, aligns and reconciles statute files. It fetches nothing.

### 4. Check it

Ask, in a new conversation:

> Run the meturgaman probe and tell me what it found.

You want three `reachable` lines and `VERDICT FULL`. Then:

> What does Bava Metzia 75b say about interest, and which edition did you read it
> from?

A good answer names the edition and its licence. An answer that does not is the
one thing this package exists to prevent, and is worth reporting as a bug.

## The agents

| Where you work | File | Where it goes |
|---|---|---|
| claude.ai, in chat | `agents/project-instructions.md` | a Project's Instructions box |
| Claude Cowork | `agents/cowork-instructions.md` | folder instructions for the working folder |
| claude.ai/code | `.claude/agents/meturgaman.md` | already in this repository; nothing to do |

**The Project** is the closest thing to an agent in ordinary claude.ai chat.
Make a Project, paste the instructions in, and every conversation started inside
it works under them. The file is deliberately short: a Project's instructions are
in context from the first word, while a skill's load only once it triggers, so the
Project carries the rules that must never be missed and leaves the procedure to
the skill.

**Cowork** reaches a real folder on a real machine, so it installs the tool
properly instead of running the vendored copy, and its instructions carry the part
that only matters when a session runs long: fetch before drafting and keep the
fetch, run `verify` before calling a draft done, hold one romanization scheme
across the whole deliverable.

**claude.ai/code** discovers `.claude/agents/meturgaman.md` on its own once this
repository is open. It installs the package from the checkout with
`pip install -e .` and reads `skills/meturgaman/SKILL.md`. The older
`agents/meturgaman.md` is the same agent written for a workstation where the tool
is already on the path; leave it alone.

## What is in here

```
claude-ai/
  INSTALL.md                     this file
  skill/
    SKILL.md                     the claude.ai skill
    references/
      sandbox-on-claude-ai.md    the container, the egress setting, $OUTPUT_DIR
  agents/
    project-instructions.md
    cowork-instructions.md

tools/build_skill.py             stage, validate, pack, prove, for both surfaces
```

That is the whole of it, because almost nothing about this skill is specific to
claude.ai. `desktop-skill/` is the complete package — SKILL.md, eleven reference
files, the launcher, the probe, the API reader — and the build lays
`claude-ai/skill/` over the top of it, so a file present in both wins from here.
The build prints which side every file came from. Forking the shared prose would
mean a correction to one copy silently missing the other.

`desktop-skill/scripts/meturgaman/` is a committed copy of the library, because
LawOS builds its online skill set by copying that directory whole and a zip
cannot hold a symlink. Committed means it can fall behind, so every build
compares it against `meturgaman/` and says so; `--sync` refreshes it. The
superseded macOS build scripts are still in `desktop-skill/_build/`, with one
developer's home directory written into them; `tools/build_skill.py` replaces
both and the packaging excludes `_build/` anyway.

## The API contracts

Three documents ship inside the zip, at `scripts/meturgaman/data/api/`: Sefaria's
own OpenAPI 3.0.2 document with all sixty of its paths, Sefaria's index of its
documentation, and Hebcal's OpenAPI document. Provenance, hashes and the refetch
commands are in [docs/api/README.md](../docs/api/README.md).

They are there so the skill can answer a question about a parameter from the
service's own contract rather than from recollection, and
`desktop-skill/scripts/api.py` is there so that answering one costs a few hundred
tokens instead of the thirty thousand it would cost to open a 1.2 MB file. It
ships in both packages, since nothing about reading a committed spec is specific
to one surface:

```
python3 scripts/api.py                        # every endpoint, one line each
python3 scripts/api.py texts                  # every parameter of everything matching
python3 scripts/api.py --responses api/ref/   # what comes back
python3 scripts/api.py --docs passages        # where the prose about it lives
```

A spec records signatures, not behaviour, and this one is confidently wrong in at
least one place: it says `version=all` returns all the texts, and what the service
returns is an empty `versions` array with the metadata moved to
`available_versions`. Every divergence anyone here has met is recorded in
`desktop-skill/references/sefaria-api-traps.md`, which also reaches the zip.
Believe that file where the two disagree.
