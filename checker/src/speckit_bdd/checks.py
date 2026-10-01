"""The mechanical checks: each reads the parsed glossary, features and specs and reports findings.

None needs a model, so each gives the same answer on every run and can gate a pull request. A
finding names the file and line to go to and says what is wrong in the project's own words.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .features import ParseError, Scenario
from .glossary import Glossary
from .specs import Spec


@dataclass(frozen=True, order=True)
class Finding:
    file: str
    line: int
    check: str
    message: str


# Words any step may use: they carry grammar, not the domain.
FUNCTION_WORDS = frozenset(
    """a an the and or but nor not no yes is are was were be been being am has have had do does did
    of to in on at by for with from into onto out off over under up down about after before than then
    that this these those it its they them their there here he she him his her i me my we us our you
    your as if when while until so because since though although whether can cannot could will
    would shall should must may might more less
    most least all any each every some none both either neither other another same such only also
    again still just very too one two three four five six seven eight nine ten first second third
    last next""".split()
)


def _forms(word: str) -> set[str]:
    """A word and the bases it may be an inflection of: carts → cart, holds → hold, paying → pay."""
    w = word.lower().strip("'")
    if w.endswith("'s"):
        w = w[:-2]
    forms = {w}
    if w.endswith("ies") and len(w) > 4:
        forms.add(w[:-3] + "y")
    if w.endswith("es") and len(w) > 3:
        forms.add(w[:-2])
    if w.endswith("s") and len(w) > 2:
        forms.add(w[:-1])
    if w.endswith("ed") and len(w) > 3:
        forms |= {w[:-2], w[:-1]}
        # A doubled consonant before the ending: cancelled → cancel, shopped → shop.
        if len(w) > 4 and w[-3] == w[-4]:
            forms.add(w[:-3])
    if w.endswith("ing") and len(w) > 4:
        forms |= {w[:-3], w[:-3] + "e"}
        if len(w) > 5 and w[-4] == w[-5]:
            forms.add(w[:-4])
    return forms


def _step_words(text: str) -> list[str]:
    # A quoted value is data the step carries, not vocabulary.
    text = re.sub(r'"[^"]*"', " ", text)
    return re.findall(r"[A-Za-z][A-Za-z'-]*", text)


def _normal(step: str) -> str:
    return re.sub(r"\s+", " ", step.strip().lower()).rstrip(".")


def parse_errors(errors: list[ParseError]) -> list[Finding]:
    return [Finding(str(e.file), e.line, "parse", e.message) for e in errors]


def undefined_terms(scenarios: list[Scenario], glossary: Glossary) -> list[Finding]:
    """A word in a step that is neither part of a glossary term nor an everyday word."""
    known = {f for w in glossary.words() | glossary.everyday | FUNCTION_WORDS for f in _forms(w)}
    refused = {f for r in glossary.refused() for w in re.findall(r"[a-z][a-z'-]*", r) for f in _forms(w)}
    findings: dict[tuple[str, int, str], Finding] = {}
    for scenario in scenarios:
        for step in scenario.steps:
            for word in _step_words(step.text):
                forms = _forms(word)
                # A refused synonym has a finding of its own; reporting it twice says nothing more.
                if forms & known or forms & refused:
                    continue
                # A hyphenated word is known when its parts are: "checked-out" for the term
                # "checked out".
                parts = [p for p in word.split("-") if p]
                if len(parts) > 1 and all(_forms(p) & known for p in parts):
                    continue
                key = (str(scenario.file), step.line, word.lower())
                findings.setdefault(
                    key,
                    Finding(
                        str(scenario.file),
                        step.line,
                        "undefined-term",
                        f"'{word}' is not a glossary term or an everyday word: define it under "
                        f"`### {word.lower()}` in {glossary.path.name}, or list it under `## Everyday words`",
                    ),
                )
    return list(findings.values())


def refused_synonyms(scenarios: list[Scenario], glossary: Glossary) -> list[Finding]:
    """A word the glossary says must not stand for one of its terms."""
    findings = []
    for synonym, term in glossary.refused().items():
        pattern = re.compile(r"\b" + re.escape(synonym) + r"(?:s|es)?\b", re.IGNORECASE)
        for scenario in scenarios:
            for step in scenario.steps:
                if pattern.search(step.text):
                    findings.append(
                        Finding(
                            str(scenario.file),
                            step.line,
                            "refused-synonym",
                            f"'{synonym}' stands for '{term.name}' ({glossary.path.name}:{term.line}); write '{term.name}'",
                        )
                    )
    return sorted(set(findings))


def contradictions(scenarios: list[Scenario]) -> list[Finding]:
    """Two scenarios in the same situation, doing the same thing, with different outcomes.

    The situation is the set of preconditions, in any order; the actions are compared in order,
    since doing two things in another order is another scenario. Scenarios that also agree on the
    outcome are the same scenario written twice.
    """
    seen: dict[tuple, Scenario] = {}
    findings = []
    for scenario in scenarios:
        whens = tuple(_normal(s) for s in scenario.of("when"))
        if not whens:
            continue
        key = (frozenset(_normal(s) for s in scenario.of("given")), whens)
        earlier = seen.get(key)
        if earlier is None:
            seen[key] = scenario
            continue
        where = f"{earlier.file}:{earlier.line} ('{earlier.name}')"
        if {_normal(s) for s in earlier.of("then")} != {_normal(s) for s in scenario.of("then")}:
            findings.append(
                Finding(
                    str(scenario.file),
                    scenario.line,
                    "contradiction",
                    f"'{scenario.name}' has the same preconditions and actions as {where} "
                    f"but a different outcome: which one is right?",
                )
            )
        else:
            findings.append(
                Finding(
                    str(scenario.file),
                    scenario.line,
                    "repeated-scenario",
                    f"'{scenario.name}' says what {where} says; keep one",
                )
            )
    return findings


def spec_references(specs: list[Spec], scenarios: list[Scenario]) -> list[Finding]:
    """Every scenario a spec names exists, or no longer does if it says it removed it."""
    index = {(str(s.file), s.name.strip().lower()) for s in scenarios}
    findings = []
    for spec in specs:
        for ref in spec.references:
            present = (ref.feature, ref.scenario.lower()) in index
            if ref.marker == "removed" and present:
                findings.append(
                    Finding(
                        str(spec.path),
                        ref.line,
                        "removed-scenario-present",
                        f"the spec removes '{ref.scenario}' but {ref.feature} still has it",
                    )
                )
            elif ref.marker != "removed" and not present:
                findings.append(
                    Finding(
                        str(spec.path),
                        ref.line,
                        "unknown-scenario",
                        f"no scenario '{ref.scenario}' in {ref.feature}",
                    )
                )
    return findings


def untraced_requirements(specs: list[Spec]) -> list[Finding]:
    """An acceptance criterion in a spec that names no scenario."""
    return [
        Finding(
            str(u.spec),
            u.line,
            "untraced-requirement",
            f"'{u.text}' names no scenario: write it as a scenario in a feature and reference it here",
        )
        for spec in specs
        for u in spec.untraced
    ]


def duplicated_scenarios(specs: list[Spec]) -> list[Finding]:
    """Given/When/Then written out in a spec, where it would be a second copy of a scenario."""
    return [
        Finding(
            str(p.spec),
            p.line,
            "duplicated-scenario",
            "a scenario written in the spec: move it to a feature and reference it, so it is written once",
        )
        for spec in specs
        for p in spec.prose
    ]


def run(
    glossary: Glossary,
    scenarios: list[Scenario],
    errors: list[ParseError],
    specs: list[Spec],
) -> list[Finding]:
    return sorted(
        parse_errors(errors)
        + undefined_terms(scenarios, glossary)
        + refused_synonyms(scenarios, glossary)
        + contradictions(scenarios)
        + spec_references(specs, scenarios)
        + untraced_requirements(specs)
        + duplicated_scenarios(specs)
    )
