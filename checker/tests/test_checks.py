"""Each test builds a small project and checks one rule, against a clean project that passes them all."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from speckit_bdd import cli

GLOSSARY = """# Glossary

### cart
The items a customer has chosen and not yet ordered.

Avoid: basket, trolley

### customer
A person who buys from the shop.

### unpaid order
An order placed and not yet paid for.

### order
Items a customer has committed to buy.

### item
One thing a customer can buy.

## Everyday words

add, adds, hold, place, pay, paid, cancel, minutes, thirty, pass, wait, remove, empty, accept, refuse, with
"""

CHECKOUT = """Feature: Checkout

  Scenario: a customer places an order from a cart
    Given a customer
    And a cart holding 2 items
    When the customer places an order
    Then the order holds 2 items
    And the cart is empty

  Scenario: an unpaid order is cancelled after thirty minutes
    Given an unpaid order
    When thirty minutes pass
    Then the order is cancelled
"""

SPEC = """# Feature Specification: checkout

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Place an order (Priority: P1)

**Acceptance Scenarios**:

- added `features/checkout.feature`: a customer places an order from a cart
- added `features/checkout.feature`: an unpaid order is cancelled after thirty minutes

<!--
  The template's own instructions may show the old form, **Given** [state], and are not the spec.
-->
"""


def project(tmp_path: Path, *, glossary: str = GLOSSARY, features: dict[str, str] | None = None, spec: str | None = SPEC) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "GLOSSARY.md").write_text(glossary)
    for name, text in (features if features is not None else {"checkout.feature": CHECKOUT}).items():
        path = tmp_path / "features" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    if spec is not None:
        (tmp_path / "specs" / "001-checkout").mkdir(parents=True)
        (tmp_path / "specs" / "001-checkout" / "spec.md").write_text(spec)
    return tmp_path


def check(root: Path, capsys) -> tuple[int, list[dict], int]:
    code = cli.main(["check", "--root", str(root), "--format", "json"])
    out = json.loads(capsys.readouterr().out)
    return code, out["findings"], out["scenarios"]


def checks_of(findings: list[dict]) -> list[str]:
    return [f["check"] for f in findings]


def test_a_clean_project_has_no_findings(tmp_path, capsys):
    code, findings, scenarios = check(project(tmp_path), capsys)
    assert findings == []
    assert code == 0
    assert scenarios == 2  # and the checks ran over something


# ── the glossary ────────────────────────────────────────────────────────────


def test_a_word_that_is_neither_a_term_nor_everyday_is_undefined(tmp_path, capsys):
    root = project(tmp_path, features={"checkout.feature": CHECKOUT.replace("Then the order is cancelled", "Then the order is voided")})
    code, findings, _ = check(root, capsys)
    assert checks_of(findings) == ["undefined-term"]
    assert "'voided'" in findings[0]["message"]
    assert findings[0]["line"] == 13
    assert code == 1


def test_plurals_and_inflections_of_known_words_are_known(tmp_path, capsys):
    text = CHECKOUT.replace("When the customer places an order", "When the customers placed the carts' orders")
    _, findings, _ = check(project(tmp_path, features={"checkout.feature": text}), capsys)
    assert findings == []


def test_a_hyphenated_word_is_known_when_its_parts_are(tmp_path, capsys):
    known = CHECKOUT.replace("Given an unpaid order", "Given an unpaid-order")
    assert check(project(tmp_path / "known", features={"checkout.feature": known}), capsys)[1] == []
    unknown = CHECKOUT.replace("Given an unpaid order", "Given an unpaid-voucher")
    _, findings, _ = check(project(tmp_path / "unknown", features={"checkout.feature": unknown}), capsys)
    assert checks_of(findings) == ["undefined-term"]
    assert "'unpaid-voucher'" in findings[0]["message"]


def test_grammar_is_not_vocabulary(tmp_path, capsys):
    text = CHECKOUT.replace("Then the order is cancelled", "Then the order is cancelled because thirty minutes pass")
    _, findings, _ = check(project(tmp_path, features={"checkout.feature": text}), capsys)
    assert findings == []


def test_quoted_values_are_data_not_vocabulary(tmp_path, capsys):
    text = CHECKOUT.replace("Then the order is cancelled", 'Then the order is "zzqx"\n    And the order is cancelled')
    _, findings, _ = check(project(tmp_path, features={"checkout.feature": text}), capsys)
    assert findings == []


def test_a_refused_synonym_is_reported_once_and_names_the_term(tmp_path, capsys):
    text = CHECKOUT.replace("And the cart is empty", "And the basket is empty")
    _, findings, _ = check(project(tmp_path, features={"checkout.feature": text}), capsys)
    assert checks_of(findings) == ["refused-synonym"]
    assert "'basket' stands for 'cart'" in findings[0]["message"]


# ── contradictions ──────────────────────────────────────────────────────────

SAME_SITUATION = """Feature: Payment

  Scenario: a declined card leaves the order unpaid
    Given a customer
    And an unpaid order
    When the customer pays
    Then the order is unpaid

  Scenario: paying always works
    Given an unpaid order
    And a customer
    When the customer pays
    Then the order is paid
"""


def test_the_same_situation_and_action_with_another_outcome_is_a_contradiction(tmp_path, capsys):
    _, findings, _ = check(project(tmp_path, features={"pay.feature": SAME_SITUATION}, spec=None), capsys)
    assert checks_of(findings) == ["contradiction"]
    assert "features/pay.feature:3" in findings[0]["message"]
    assert findings[0]["line"] == 9


def test_preconditions_in_any_order_are_one_situation_and_the_same_outcome_is_a_repeat(tmp_path, capsys):
    text = SAME_SITUATION.replace("Then the order is paid", "Then the order is unpaid")
    _, findings, _ = check(project(tmp_path, features={"pay.feature": text}, spec=None), capsys)
    assert checks_of(findings) == ["repeated-scenario"]


def test_contradictions_are_found_across_features_and_through_a_background(tmp_path, capsys):
    one = "Feature: one\n  Background:\n    Given a customer\n  Scenario: first\n    When the customer pays\n    Then the order is paid\n"
    two = "Feature: two\n  Scenario: second\n    Given a customer\n    When the customer pays\n    Then the order is unpaid\n"
    _, findings, _ = check(project(tmp_path, features={"a/one.feature": one, "b/two.feature": two}, spec=None), capsys)
    assert checks_of(findings) == ["contradiction"]


def test_actions_in_another_order_are_another_scenario(tmp_path, capsys):
    text = """Feature: Cart
  Scenario: add then remove
    Given a cart
    When the customer adds an item
    And the customer removes an item
    Then the cart is empty

  Scenario: remove then add
    Given a cart
    When the customer removes an item
    And the customer adds an item
    Then the cart holds 1 item
"""
    _, findings, _ = check(project(tmp_path, features={"cart.feature": text}, spec=None), capsys)
    assert findings == []


def test_each_examples_row_is_its_own_scenario(tmp_path, capsys):
    text = """Feature: Payment
  Scenario Outline: paying
    Given an unpaid order
    When the customer pays with <card>
    Then the order is <status>

    Examples:
      | card     | status |
      | "valid"  | paid   |
      | "valid"  | unpaid |
"""
    _, findings, _ = check(project(tmp_path, features={"pay.feature": text}, spec=None), capsys)
    assert checks_of(findings) == ["contradiction"]
    assert findings[0]["line"] == 10  # the row, which is where a reader goes


# ── specs ───────────────────────────────────────────────────────────────────


def test_a_spec_that_names_a_scenario_no_feature_has_is_refused(tmp_path, capsys):
    spec = SPEC.replace("an unpaid order is cancelled after thirty minutes", "an unpaid order is cancelled after an hour")
    _, findings, _ = check(project(tmp_path, spec=spec), capsys)
    assert checks_of(findings) == ["unknown-scenario"]


def test_a_removed_scenario_must_be_gone(tmp_path, capsys):
    spec = SPEC.replace("- added `features/checkout.feature`: an unpaid", "- removed `features/checkout.feature`: an unpaid")
    _, findings, _ = check(project(tmp_path, spec=spec), capsys)
    assert checks_of(findings) == ["removed-scenario-present"]


def test_an_acceptance_criterion_that_names_no_scenario_is_untraced(tmp_path, capsys):
    spec = SPEC.replace("<!--", "- the customer is told the order went through\n\n<!--")
    _, findings, _ = check(project(tmp_path, spec=spec), capsys)
    assert checks_of(findings) == ["untraced-requirement"]


def test_given_when_then_written_in_a_spec_is_a_duplicate(tmp_path, capsys):
    spec = SPEC.replace("<!--", "1. **Given** a cart, **When** the customer places an order, **Then** an order exists\n\n<!--")
    _, findings, _ = check(project(tmp_path, spec=spec), capsys)
    assert checks_of(findings) == ["duplicated-scenario"]


def test_the_presets_own_template_is_read_as_references_and_nothing_else():
    # The checker and the preset's template describe one format; if they drift, a spec written from
    # the template would have its scenarios read as untraced requirements, or not read at all.
    from speckit_bdd import specs

    template = Path(__file__).parents[2] / "preset" / "templates" / "spec-template.md"
    parsed = specs.parse(template, template.parent)
    assert [r.marker for r in parsed.references] == ["added", "changed", "added", "added"]
    assert all(r.feature == "features/[area]/[capability].feature" for r in parsed.references)
    assert parsed.untraced == []
    assert parsed.prose == []


# ── the command ─────────────────────────────────────────────────────────────


# ── a project that had specs before it had features ─────────────────────────

OLDER = """# Feature Specification: an earlier change

**Acceptance Scenarios**:

1. **Given** a cart, **When** the customer pays, **Then** the order is paid.
- the customer is told when the order ships
"""


def older(root: Path, *names: str) -> Path:
    for name in names:
        (root / "specs" / name).mkdir(parents=True)
        (root / "specs" / name / "spec.md").write_text(OLDER)
    return root


def report(root: Path, capsys, *args: str) -> tuple[int, dict]:
    code = cli.main(["check", "--root", str(root), "--format", "json", *args])
    return code, json.loads(capsys.readouterr().out)


def test_every_spec_is_read_unless_told_otherwise(tmp_path, capsys):
    code, out = report(older(project(tmp_path), "000-before"), capsys)
    assert code == 1
    assert sorted(checks_of(out["findings"])) == ["duplicated-scenario", "untraced-requirement"]
    assert {f["file"] for f in out["findings"]} == {"specs/000-before/spec.md"}
    assert out["specs"] == {"checked": 2, "skipped": 0}


def test_specs_before_the_first_one_named_are_not_read(tmp_path, capsys):
    code, out = report(older(project(tmp_path), "000-before"), capsys, "--specs-from", "001")
    assert (code, out["findings"]) == (0, [])
    # ...and the one named is still held to the features: this is not the checks being off.
    assert out["specs"] == {"checked": 1, "skipped": 1}


def test_the_spec_named_and_every_later_one_are_read(tmp_path, capsys):
    root = older(project(tmp_path), "000-before", "002-after")
    code, out = report(root, capsys, "--specs-from", "001-checkout")
    assert code == 1
    assert {f["file"] for f in out["findings"]} == {"specs/002-after/spec.md"}
    assert out["specs"] == {"checked": 2, "skipped": 1}


@pytest.mark.parametrize(
    ("first", "skipped"),
    [
        ("100", ["001-checkout", "099-a"]),  # numbers compare as numbers: 99 is before 100
        ("1000", ["001-checkout", "099-a", "100-b"]),  # ...and 100 before 1000
        ("999", ["001-checkout", "099-a", "100-b"]),  # the thousandth spec is after the 999th, not before
        ("20260319-143022", ["001-checkout", "099-a", "100-b", "1000-c", "20260319-143021-d"]),  # timestamps
        ("1", []),  # a number needs no padding: 1 is 001
    ],
)
def test_specs_are_ordered_as_spec_kit_numbers_them(tmp_path, capsys, first, skipped):
    names = ["099-a", "100-b", "1000-c", "20260319-143021-d", "20260319-143022-e"]
    code, out = report(older(project(tmp_path), *names), capsys, "--specs-from", first)
    read = {f["file"].split("/")[1] for f in out["findings"]}
    assert read == set(names) - set(skipped)
    assert out["specs"]["skipped"] == len(skipped)


def test_a_first_spec_later_than_every_spec_reads_none_and_says_so(tmp_path, capsys):
    root = older(project(tmp_path), "000-before")
    code, out = report(root, capsys, "--specs-from", "190")
    # Nothing is found because nothing was read, and the report is what tells the two apart.
    assert (code, out["findings"]) == (0, [])
    assert out["specs"] == {"checked": 0, "skipped": 2}
    cli.main(["check", "--root", str(root), "--specs-from", "190"])
    assert "0 specs; 2 specs before 190 not read" in capsys.readouterr().err


def test_the_summary_counts_specs_and_names_older_ones_only_when_asked(tmp_path, capsys):
    root = older(project(tmp_path), "000-before")
    cli.main(["check", "--root", str(root)])
    assert capsys.readouterr().err.strip() == "2 findings in 2 scenarios and 2 specs"
    cli.main(["check", "--root", str(root), "--specs-from", "001"])
    assert capsys.readouterr().err.strip() == "0 findings in 2 scenarios and 1 spec; 1 spec before 001 not read"


def test_a_first_spec_that_names_nothing_is_a_usage_error(tmp_path, capsys):
    assert cli.main(["check", "--root", str(project(tmp_path)), "--specs-from", " "]) == 2
    assert "--specs-from" in capsys.readouterr().err


def test_a_feature_that_does_not_parse_is_a_finding_with_its_line(tmp_path, capsys):
    broken = "Feature: broken\n  Scenario: one\n    Given a cart\n    Whatever this is\n"
    _, findings, _ = check(project(tmp_path, features={"broken.feature": broken}, spec=None), capsys)
    assert checks_of(findings) == ["parse"]
    assert findings[0]["line"] == 4


def test_text_output_names_file_line_and_check(tmp_path, capsys):
    root = project(tmp_path, features={"checkout.feature": CHECKOUT.replace("cart is empty", "basket is empty")})
    code = cli.main(["check", "--root", str(root)])
    out = capsys.readouterr().out
    assert code == 1
    assert out.startswith("features/checkout.feature:8: [refused-synonym] ")


def test_a_root_that_is_not_a_directory_is_a_usage_error(tmp_path):
    assert cli.main(["check", "--root", str(tmp_path / "nowhere")]) == 2


@pytest.mark.parametrize("missing", ["GLOSSARY.md", "features"])
def test_an_empty_project_runs_and_reports_what_it_could_not_find(tmp_path, capsys, missing):
    root = project(tmp_path, spec=None)
    target = root / missing
    if target.is_dir():
        for f in target.rglob("*"):
            if f.is_file():
                f.unlink()
    else:
        target.unlink()
    code, findings, scenarios = check(root, capsys)
    # No glossary: every domain word is undefined. No features: nothing to check, and nothing found.
    assert (code, scenarios) == ((1, 2) if missing == "GLOSSARY.md" else (0, 0))
