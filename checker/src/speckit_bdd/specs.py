"""What a spec says about scenarios: the references under its Acceptance Scenarios headings.

The `bdd` preset's spec template writes each acceptance scenario as a reference to a scenario in a
living feature, never as the scenario itself:

    **Acceptance Scenarios**:

    - added `features/checkout/cancel.feature`: an unpaid order is cancelled after thirty minutes
    - changed `features/checkout/pay.feature`: a declined card leaves the order unpaid
    - removed `features/checkout/pay.feature`: a cheque is accepted

`added` and `changed` name a scenario that must exist; `removed`, one that must not. A reference
with no marker is read as `added`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

# The heading, bold or as a heading, with anything after it on the line: the preset's template
# notes there that the scenarios live in the features.
_SECTION = re.compile(r"^\s*\*\*Acceptance Scenarios\*\*|^#+\s*Acceptance Scenarios\b", re.IGNORECASE)
_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(.*\S)\s*$")
_REFERENCE = re.compile(
    r"^(?:(?P<marker>added|changed|removed)\s+)?`(?P<file>[^`]+\.feature)`\s*[:—–-]\s*(?P<name>.+?)\s*$",
    re.IGNORECASE,
)
# Given/When/Then written out in a spec: bold keywords, or one line that runs through all three.
_PROSE = re.compile(r"\*\*Given\*\*|^\s*(?:[-*+]|\d+[.)])?\s*Given\b.*\bWhen\b.*\bThen\b")


@dataclass(frozen=True)
class Reference:
    spec: Path
    line: int
    marker: str  # "added", "changed" or "removed"
    feature: str
    scenario: str


@dataclass(frozen=True)
class Untraced:
    spec: Path
    line: int
    text: str


@dataclass(frozen=True)
class Prose:
    spec: Path
    line: int
    text: str


@dataclass
class Spec:
    path: Path
    references: list[Reference]
    untraced: list[Untraced]
    prose: list[Prose]


def parse(path: Path, root: Path) -> Spec:
    relative = path.relative_to(root) if path.is_relative_to(root) else path
    spec = Spec(relative, [], [], [])
    in_section = False
    in_comment = False
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        # An HTML comment holds the template's instructions, not the spec.
        if in_comment:
            in_comment = "-->" not in line
            continue
        if "<!--" in line and "-->" not in line.split("<!--", 1)[1]:
            in_comment = True
            continue
        if _PROSE.search(line):
            spec.prose.append(Prose(relative, number, line.strip()))
        if _SECTION.match(line):
            in_section = True
            continue
        if in_section and (line.startswith("#") or line.strip() == "---" or line.strip().startswith("**")):
            in_section = False
        if not in_section:
            continue
        item = _ITEM.match(line)
        if not item:
            continue
        reference = _REFERENCE.match(item.group(1))
        if reference:
            spec.references.append(
                Reference(
                    relative,
                    number,
                    (reference.group("marker") or "added").lower(),
                    reference.group("file"),
                    reference.group("name").strip(),
                )
            )
        elif not _PROSE.search(line):
            spec.untraced.append(Untraced(relative, number, item.group(1)))
    return spec


def load(directory: Path, root: Path) -> list[Spec]:
    if not directory.exists():
        return []
    return [parse(p, root) for p in sorted(directory.glob("*/spec.md"))]
