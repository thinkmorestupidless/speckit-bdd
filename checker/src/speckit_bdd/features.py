"""The living features, parsed and compiled into scenarios.

Compiling is Cucumber's own: a `Background` is folded into every scenario after it, a
`Scenario Outline` becomes one scenario per `Examples` row with the row's values in place, and each
step is typed as a precondition, an action or an outcome, so an `And` or `But` takes the type of the
step before it. Two scenarios are therefore compared as what they say, not as how they were written.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from gherkin.errors import CompositeParserException
from gherkin.parser import Parser
from gherkin.pickles.compiler import Compiler


@dataclass(frozen=True)
class Step:
    kind: str  # "given", "when" or "then"
    text: str
    line: int


@dataclass(frozen=True)
class Scenario:
    file: Path
    line: int
    name: str
    steps: tuple[Step, ...]

    def of(self, kind: str) -> tuple[str, ...]:
        return tuple(s.text for s in self.steps if s.kind == kind)


@dataclass(frozen=True)
class ParseError:
    file: Path
    line: int
    message: str


_KINDS = {"Context": "given", "Action": "when", "Outcome": "then"}


def _locations(node, found: dict[str, int]) -> None:
    """Every AST node id mapped to its line, so a compiled scenario can be traced to its source."""
    if isinstance(node, dict):
        if "id" in node and isinstance(node.get("location"), dict):
            found[node["id"]] = node["location"]["line"]
        for value in node.values():
            _locations(value, found)
    elif isinstance(node, list):
        for value in node:
            _locations(value, found)


def parse(path: Path, root: Path) -> tuple[list[Scenario], list[ParseError]]:
    relative = path.relative_to(root) if path.is_relative_to(root) else path
    try:
        document = Parser().parse(path.read_text(encoding="utf-8"))
    except CompositeParserException as failure:
        return [], [ParseError(relative, e.location["line"], str(e)) for e in failure.errors]
    except Exception as failure:  # a single parse error
        line = getattr(failure, "location", {}).get("line", 1) if hasattr(failure, "location") else 1
        return [], [ParseError(relative, line, str(failure))]
    document["uri"] = str(relative)
    lines: dict[str, int] = {}
    _locations(document, lines)
    scenarios = []
    for pickle in Compiler().compile(document):
        # The last id is the example row for an outline, the scenario otherwise: the line a reader
        # goes to. Steps carry their own ids likewise.
        line = lines.get(pickle["astNodeIds"][-1], lines.get(pickle["astNodeIds"][0], 1))
        steps = tuple(
            Step(_KINDS.get(s.get("type"), "given"), s["text"], lines.get(s["astNodeIds"][0], line))
            for s in pickle["steps"]
        )
        scenarios.append(Scenario(relative, line, pickle["name"], steps))
    return scenarios, []


def load(directory: Path, root: Path) -> tuple[list[Scenario], list[ParseError]]:
    scenarios: list[Scenario] = []
    errors: list[ParseError] = []
    if not directory.exists():
        return scenarios, errors
    for path in sorted(directory.rglob("*.feature")):
        found, failed = parse(path, root)
        scenarios += found
        errors += failed
    return scenarios, errors
