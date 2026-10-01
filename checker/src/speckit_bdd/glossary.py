"""The project's glossary: one `###` heading per term, its definition, an optional `Avoid:` line.

    ### cart
    The items a customer has chosen and not yet ordered.

    Avoid: basket, trolley

A term may be several words (`### unpaid order`). `Avoid:` names words that must not stand for
the term in a feature; a step using one is a refused synonym. A heading's words are the term as it
is written in steps, case aside, and its plural with `s` or `es` counts as the term.

A `## Everyday words` section lists, comma-separated, the ordinary words steps may use without a
definition: the verbs and the plain words that are not the domain's (pays, sent, holds). Every
other word in a step is reported until it is a term or an everyday word, so the vocabulary a
project's features use is always written down in one place.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

_HEADING = re.compile(r"^###\s+(.+?)\s*$")
_AVOID = re.compile(r"^\s*(?:\*\*|\*|_)?Avoid:?(?:\*\*|\*|_)?:?\s*(.+)$", re.IGNORECASE)


@dataclass(frozen=True)
class Term:
    name: str
    line: int
    definition: str
    avoid: tuple[str, ...] = ()


@dataclass
class Glossary:
    path: Path
    terms: list[Term] = field(default_factory=list)
    everyday: set[str] = field(default_factory=set)

    def words(self) -> set[str]:
        """Every word that appears in a term, lower-cased: the vocabulary a step may use."""
        return {w for t in self.terms for w in _words(t.name)}

    def phrases(self) -> list[str]:
        """Each term as a lower-cased phrase, longest first, so `unpaid order` wins over `order`."""
        return sorted({t.name.lower() for t in self.terms}, key=len, reverse=True)

    def refused(self) -> dict[str, Term]:
        """Each refused synonym, lower-cased, mapped to the term it must not stand for."""
        return {a.lower(): t for t in self.terms for a in t.avoid}


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z][a-z'-]*", text.lower())


def load(path: Path) -> Glossary:
    glossary = Glossary(path)
    if not path.exists():
        return glossary
    lines = path.read_text(encoding="utf-8").splitlines()
    current: dict | None = None

    def close():
        if current is not None:
            glossary.terms.append(
                Term(
                    current["name"],
                    current["line"],
                    " ".join(current["definition"]).strip(),
                    tuple(current["avoid"]),
                )
            )

    everyday = False
    for number, line in enumerate(lines, start=1):
        heading = _HEADING.match(line)
        if heading:
            close()
            everyday = False
            current = {"name": heading.group(1), "line": number, "definition": [], "avoid": []}
            continue
        if line.startswith("#"):
            close()
            current = None
            everyday = line.lstrip("#").strip().lower() == "everyday words"
            continue
        if everyday:
            glossary.everyday |= {w for item in line.split(",") for w in _words(item)}
            continue
        if current is None:
            continue
        avoid = _AVOID.match(line)
        if avoid:
            current["avoid"] += [w.strip(" .`*_") for w in avoid.group(1).split(",") if w.strip(" .`*_")]
        elif line.strip():
            current["definition"].append(line.strip())
    close()
    return glossary
