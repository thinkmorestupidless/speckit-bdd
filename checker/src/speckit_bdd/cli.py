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
    check.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"speckit-bdd: {root} is not a directory", file=sys.stderr)
        return 2
    terms = glossary.load(root / args.glossary)
    scenarios, errors = features.load(root / args.features, root)
    found = checks.run(terms, scenarios, errors, specs.load(root / args.specs, root))

    if args.format == "json":
        print(json.dumps({"findings": [asdict(f) for f in found], "scenarios": len(scenarios)}, indent=2))
    else:
        for f in found:
            print(f"{f.file}:{f.line}: [{f.check}] {f.message}")
        print(f"{len(found)} finding{'s' if len(found) != 1 else ''} in {len(scenarios)} scenarios", file=sys.stderr)
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
