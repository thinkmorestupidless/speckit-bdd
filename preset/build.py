"""Builds the preset's spec template from spec-kit's own, changing only what the preset is for.

    python preset/build.py                       # from the pinned copy in preset/upstream/
    python preset/build.py --upstream <file|url>  # from another copy, e.g. spec-kit's latest
    python preset/build.py --check                # fail if the committed template differs

The preset replaces spec-kit's spec template whole, because a template cannot be partly removed:
`prepend`, `append` and `wrap` all keep the core's Given/When/Then prose. Building the replacement
from the core, with each change stated below, keeps the two in step: when spec-kit changes its
template, a change that no longer applies fails here, naming itself, instead of silently shipping a
stale copy.
"""

from __future__ import annotations

import argparse
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).parent
PINNED = HERE / "upstream" / "spec-template.md"
OUTPUT = HERE / "templates" / "spec-template.md"
LATEST = "https://raw.githubusercontent.com/github/spec-kit/main/templates/spec-template.md"

REFERENCES = """**Acceptance Scenarios** *(each names a scenario in a living feature; none is written here)*:

<!--
  The scenarios themselves live in the project's features (default: features/<area>/*.feature),
  written by /speckit-bdd-features in the glossary's words. Name each one by its rule, marking
  whether this spec adds it, changes it or removes it:
-->

- added `features/[area]/[capability].feature`: [the scenario's name, its rule in one sentence]"""

# (what the core says, what the preset says instead, how many times the core says it)
CHANGES: list[tuple[str, str, int]] = [
    (
        "**Acceptance Scenarios**:\n\n"
        "1. **Given** [initial state], **When** [action], **Then** [expected outcome]\n"
        "2. **Given** [initial state], **When** [action], **Then** [expected outcome]",
        REFERENCES + "\n- changed `features/[area]/[capability].feature`: [the scenario's name]",
        1,
    ),
    (
        "**Acceptance Scenarios**:\n\n"
        "1. **Given** [initial state], **When** [action], **Then** [expected outcome]",
        REFERENCES,
        2,
    ),
    (
        "- What happens when [boundary condition]?\n- How does system handle [error scenario]?",
        "- What happens when [boundary condition]? *(once answered, a scenario, or a row of a\n"
        "  `Scenario Outline`'s `Examples`, referenced above)*\n"
        "- How does system handle [error scenario]?",
        1,
    ),
    (
        "### Key Entities *(include if feature involves data)*",
        "### Key Entities *(include if feature involves data; each a term in the project glossary)*",
        1,
    ),
]


def build(core: str) -> str:
    text = core
    for old, new, times in CHANGES:
        found = text.count(old)
        if found != times:
            raise SystemExit(
                f"spec-kit's template says this {found} time(s), not {times}; the preset needs updating:\n\n{old}"
            )
        text = text.replace(old, new)
    if "**Given**" in text:
        raise SystemExit("the built template still holds a Given/When/Then; a change above no longer covers it")
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--upstream", help="the core template to build from: a file or a URL")
    parser.add_argument("--latest", action="store_true", help=f"build from spec-kit's main branch ({LATEST})")
    parser.add_argument("--check", action="store_true", help="fail if the committed template is not what this builds")
    args = parser.parse_args()
    source = LATEST if args.latest else args.upstream
    if source is None:
        core = PINNED.read_text(encoding="utf-8")
    elif source.startswith(("http://", "https://")):
        core = urllib.request.urlopen(source, timeout=30).read().decode("utf-8")
    else:
        core = Path(source).read_text(encoding="utf-8")
    built = build(core)
    if args.check:
        if OUTPUT.read_text(encoding="utf-8") != built:
            print(f"{OUTPUT} is not what spec-kit's template builds; run preset/build.py", file=sys.stderr)
            return 1
        print(f"{OUTPUT.name} is current")
        return 0
    OUTPUT.write_text(built, encoding="utf-8")
    print(f"wrote {OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
