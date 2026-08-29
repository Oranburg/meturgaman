#!/usr/bin/env python3
"""Read the committed API contracts without loading them into the context.

Sefaria's OpenAPI document is 1.2 MB and Hebcal's is 55 KB. Both are bundled at
`scripts/meturgaman/data/api/`, and both are far too large to read. That is the
whole problem this script solves: a script's output enters the context window
and its input does not, so a question about a parameter costs a few hundred
tokens here and thirty thousand if the file is opened instead.

It answers four questions.

    python3 scripts/api.py                       what endpoints exist
    python3 scripts/api.py texts                 what to send to the ones matching "texts"
    python3 scripts/api.py --responses /api/ref/{tref}    what comes back
    python3 scripts/api.py --docs passages       where the prose about it is

The first is a one-line-per-endpoint index of both services. The second prints
every query, path and body parameter of every matching endpoint, with its type,
whether it is required, its default and its allowed values, straight out of the
document rather than out of anyone's recollection. The third prints the response
shape, one line per field, to the depth asked for. The fourth searches Sefaria's
own documentation index and prints the URLs, because the schema says what the
parameters are and the prose says what the service actually does with them.

**A spec is not a description of behaviour.** It does not record that
`version=all` returns an empty `versions` array, or that `/api/ref/` answers
HTTP 200 with `is_ref: false` for a string that is no reference at all. Those
are in `references/sefaria-api-traps.md`, each one having been met. Read the
spec for what to send and that file for what comes back.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any

HERE = pathlib.Path(__file__).resolve().parent

def _search_path() -> tuple[pathlib.Path, ...]:
    """Where the contracts might be, packaged copy first.

    A built skill carries them inside the vendored package, which is the only
    case that matters in a sandbox. A developer running this file out of a
    checkout has them at `docs/api/` some way up the tree instead, so the
    parents are walked as far as the repository root, the same way
    `meturgaman/sources/hebcal.py` finds the Hebcal document.
    """
    found = [HERE / "meturgaman" / "data" / "api"]
    for parent in HERE.parents:
        found.append(parent / "docs" / "api")
        if (parent / ".git").exists():
            break
    return tuple(found)


SEARCH = _search_path()

SPECS = {
    "sefaria": "sefaria-openapi.json",
    "hebcal": "hebcal-openapi.json",
}
INDEX = "sefaria-llms.txt"


def _locate(filename: str) -> pathlib.Path | None:
    for directory in SEARCH:
        candidate = directory / filename
        if candidate.is_file():
            return candidate
    return None


def _load(service: str) -> tuple[dict[str, Any], pathlib.Path] | None:
    path = _locate(SPECS[service])
    if path is None:
        return None
    return json.loads(path.read_text(encoding="utf-8")), path


def _deref(spec: dict[str, Any], node: Any) -> Any:
    """Follow a local `$ref` one hop. Both documents only use local refs."""
    if isinstance(node, dict) and "$ref" in node:
        target: Any = spec
        for part in node["$ref"].lstrip("#/").split("/"):
            if not isinstance(target, dict) or part not in target:
                return node
            target = target[part]
        return target
    return node


def _base(spec: dict[str, Any]) -> str:
    servers = spec.get("servers") or []
    return servers[0].get("url", "") if servers else ""


def _operations(spec: dict[str, Any]):
    """Yield (path, method, operation, shared parameters) for every endpoint."""
    for path, item in sorted(spec.get("paths", {}).items()):
        shared = item.get("parameters", [])
        for method, operation in item.items():
            if method in {"get", "post", "put", "patch", "delete"}:
                yield path, method, operation, shared


def _summary(path: str, item_or_op: dict[str, Any], spec: dict[str, Any]) -> str:
    for source in (item_or_op, spec.get("paths", {}).get(path, {})):
        text = (source.get("summary") or "").strip()
        if text:
            return text
    return ""


# --------------------------------------------------------------------------
# the index


def index(match: str | None) -> int:
    """One line per endpoint, across both services."""
    printed = 0
    for service in SPECS:
        loaded = _load(service)
        if loaded is None:
            print(f"{service}: spec not found", file=sys.stderr)
            continue
        spec, path_on_disk = loaded
        print(f"\n{service}  {_base(spec)}   ({path_on_disk.name})")
        for endpoint, method, operation, _ in _operations(spec):
            if match and match.lower() not in endpoint.lower():
                continue
            label = _summary(endpoint, operation, spec)
            print(f"  {method.upper():4} {endpoint:44} {label}")
            printed += 1
    if match and not printed:
        print(f"\nno endpoint matches {match!r}", file=sys.stderr)
        return 1
    return 0


# --------------------------------------------------------------------------
# parameters


def _describe_parameter(spec: dict[str, Any], raw: Any) -> list[str]:
    parameter = _deref(spec, raw)
    schema = _deref(spec, parameter.get("schema", {}))
    bits = [f"in={parameter.get('in')}", f"type={schema.get('type', '?')}"]
    if parameter.get("required"):
        bits.append("REQUIRED")
    if "default" in schema:
        bits.append(f"default={schema['default']!r}")
    if schema.get("enum"):
        bits.append("one of " + ", ".join(repr(v) for v in schema["enum"]))
    lines = [f"    {parameter.get('name')}  ({'  '.join(bits)})"]
    prose = " ".join((parameter.get("description") or "").split())
    if prose:
        lines.extend(_wrap(prose, indent=6))
    return lines


def _wrap(text: str, indent: int, width: int = 78) -> list[str]:
    out: list[str] = []
    line = " " * indent
    for word in text.split():
        if len(line) + 1 + len(word) > width and line.strip():
            out.append(line)
            line = " " * indent
        line += ("" if line.strip() == "" else " ") + word
    if line.strip():
        out.append(line)
    return out


def parameters(match: str) -> int:
    """Every parameter of every endpoint whose path matches."""
    found = 0
    for service in SPECS:
        loaded = _load(service)
        if loaded is None:
            continue
        spec, _ = loaded
        for endpoint, method, operation, shared in _operations(spec):
            if match.lower() not in endpoint.lower():
                continue
            found += 1
            print(f"\n{method.upper()} {_base(spec)}{endpoint}   [{service}]")
            label = _summary(endpoint, operation, spec)
            if label:
                print(f"  {label}")
            prose = " ".join((operation.get("description") or "").split())
            if prose:
                print("\n".join(_wrap(prose, indent=2)))

            declared = list(shared) + list(operation.get("parameters", []))
            if declared:
                print("  parameters:")
                seen: set[str] = set()
                for raw in declared:
                    name = _deref(spec, raw).get("name")
                    if name in seen:
                        continue
                    seen.add(name)
                    print("\n".join(_describe_parameter(spec, raw)))

            body = operation.get("requestBody")
            if body:
                body = _deref(spec, body)
                for content_type, media in (body.get("content") or {}).items():
                    schema = _deref(spec, media.get("schema", {}))
                    required = sorted(schema.get("required", []))
                    print(f"  body {content_type}  required: {required or 'none'}")
                    for name, prop in (schema.get("properties") or {}).items():
                        prop = _deref(spec, prop)
                        mark = "*" if name in required else " "
                        print(f"    {mark}{name}  (type={prop.get('type', '?')})")
                        text = " ".join((prop.get("description") or "").split())
                        if text:
                            print("\n".join(_wrap(text, indent=6)))
    if not found:
        print(f"no endpoint matches {match!r}", file=sys.stderr)
        return 1
    return 0


# --------------------------------------------------------------------------
# responses


def _fields(spec: dict[str, Any], schema: Any, depth: int, indent: int = 4) -> list[str]:
    schema = _deref(spec, schema)
    if not isinstance(schema, dict) or depth < 0:
        return []
    out: list[str] = []
    if schema.get("type") == "array" or "items" in schema:
        items = _deref(spec, schema.get("items", {}))
        out.append(" " * indent + "[ array of ]")
        out.extend(_fields(spec, items, depth - 1, indent + 2))
        return out
    for name, prop in (schema.get("properties") or {}).items():
        prop = _deref(spec, prop)
        kind = prop.get("type", "?")
        note = " ".join((prop.get("description") or "").split())
        line = f"{' ' * indent}{name}: {kind}"
        if note:
            line += f"  -- {note[:90]}"
        out.append(line)
        if kind in {"object", "array"} or "properties" in prop or "items" in prop:
            out.extend(_fields(spec, prop, depth - 1, indent + 2))
    return out


def responses(match: str, depth: int) -> int:
    found = 0
    for service in SPECS:
        loaded = _load(service)
        if loaded is None:
            continue
        spec, _ = loaded
        for endpoint, method, operation, _shared in _operations(spec):
            if match.lower() not in endpoint.lower():
                continue
            found += 1
            print(f"\n{method.upper()} {endpoint}   [{service}]")
            for status, response in (operation.get("responses") or {}).items():
                response = _deref(spec, response)
                print(f"  {status}  {(response.get('description') or '').strip()}")
                for content_type, media in (response.get("content") or {}).items():
                    print(f"    {content_type}")
                    lines = _fields(spec, media.get("schema", {}), depth)
                    print("\n".join(lines) if lines else "      (no schema recorded)")
    if not found:
        print(f"no endpoint matches {match!r}", file=sys.stderr)
        return 1
    return 0


# --------------------------------------------------------------------------
# the prose


def docs(term: str) -> int:
    """Search Sefaria's own documentation index and print the page URLs.

    Every URL it prints takes a `.md` suffix and returns markdown, which is what
    makes these readable by a web fetch. The index is a map to prose, and the
    prose is where behaviour the schema cannot express is written down.
    """
    path = _locate(INDEX)
    if path is None:
        print(f"{INDEX} not found", file=sys.stderr)
        return 1
    hits = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("- [") and term.lower() in line.lower():
            print(line)
            hits += 1
    if not hits:
        print(f"nothing in {INDEX} mentions {term!r}", file=sys.stderr)
        return 1
    print("\nAppend .md to any URL above to fetch the page as markdown.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="api.py",
        description="Query the bundled Sefaria and Hebcal API contracts.",
    )
    parser.add_argument(
        "match",
        nargs="?",
        help="part of an endpoint path, e.g. texts, ref, topics, /api/links/",
    )
    parser.add_argument(
        "--responses",
        action="store_true",
        help="print the response shape rather than the parameters",
    )
    parser.add_argument(
        "--depth", type=int, default=2, help="how far to descend into a response schema"
    )
    parser.add_argument(
        "--docs",
        metavar="TERM",
        help="search Sefaria's documentation index for pages about TERM",
    )
    parser.add_argument(
        "--index",
        action="store_true",
        help="one line per endpoint, even when MATCH is given",
    )
    args = parser.parse_args()

    if args.docs:
        return docs(args.docs)
    if args.match is None or args.index:
        return index(args.match)
    if args.responses:
        return responses(args.match, args.depth)
    return parameters(args.match)


if __name__ == "__main__":
    sys.exit(main())
