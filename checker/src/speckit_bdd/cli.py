"""`speckit-bdd check`: run every mechanical check over a project and report what it finds.

Exits 0 when nothing is found, 1 when something is, and 2 when it was misused, so a CI step can
gate on it. Paths are relative to `--root`, the project, and default to the extension's layout.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from . import __version__, checks, features, glossary, specs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="speckit-bdd", description=__doc__.splitlines()[0])
    parser.add_argument("--version", action="version", version=f"speckit-bdd {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check", help="check the glossary, the features and the specs")
    check.add_argument("--root", default=".", help="the project (default: the current directory)")
    check.add_argument("--glossary", default="GLOSSARY.md", help="the glossary, relative to the root")
    check.add_argument("--features", default="features", help="the living features, relative to the root")
    check.add_argument("--specs", default="specs", help="spec-kit's specs, relative to the root")
    check.add_argument(
        "--specs-from",
        metavar="SPEC",
        help="the first spec to check, by its directory's name or leading number (019); older specs are not read",
    )
    check.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"speckit-bdd: {root} is not a directory", file=sys.stderr)
        return 2
    terms = glossary.load(root / args.glossary)
    scenarios, errors = features.load(root / args.features, root)
    if args.specs_from is not None and not args.specs_from.strip():
        print("speckit-bdd: --specs-from needs a spec's directory name or number", file=sys.stderr)
        return 2
    read, older = specs.load(root / args.specs, root, args.specs_from)
    found = checks.run(terms, scenarios, errors, read)

    # How many specs were read and how many were not is always said: a `--specs-from` that names a
    # spec later than every one there is reads nothing, and that must not look like a clean project.
    if args.format == "json":
        report = {
            "findings": [asdict(f) for f in found],
            "scenarios": len(scenarios),
            "specs": {"checked": len(read), "skipped": older},
        }
        print(json.dumps(report, indent=2))
    else:
        for f in found:
            print(f"{f.file}:{f.line}: [{f.check}] {f.message}")
        summary = f"{len(found)} finding{'s' if len(found) != 1 else ''} in {len(scenarios)} scenarios and {_specs(len(read))}"
        if args.specs_from is not None:
            summary += f"; {_specs(older)} before {args.specs_from} not read"
        print(summary, file=sys.stderr)
    return 1 if found else 0


def _specs(count: int) -> str:
    return f"{count} spec{'s' if count != 1 else ''}"


if __name__ == "__main__":
    sys.exit(main())
