# speckit-bdd

Behaviour-driven specs for [spec-kit](https://github.com/github/spec-kit): a project glossary and
living Gherkin features beside spec-kit's specs, checked for undefined terms, refused synonyms,
contradictions and untraced requirements before anyone writes code.

spec-kit already asks for Given/When/Then, as prose in each `spec.md`. Prose cannot be checked: two
scenarios can give one situation different outcomes, the same thing can go by three names, and the
specs record changes rather than what the system does now. This moves the scenarios into Gherkin
features that describe the current system, holds every word they use to one glossary, and leaves
each spec naming the scenarios it adds, changes or removes.

It is two installables and the checker they run:

| Directory | What it is | Installs as |
| --- | --- | --- |
| `extension/` | the `bdd` extension: two commands and the hooks that run them | `specify extension add bdd --from <release>` |
| `preset/` | the `bdd` preset: spec-kit's spec template, with acceptance scenarios as references | `specify preset add bdd --from <release>` |
| `checker/` | `speckit-bdd check`, the mechanical checks, in Python | run by the commands, through `uvx` |

## Install

Both, in a spec-kit project (spec-kit 0.14.0 or later):

```bash
specify extension add bdd --from https://github.com/thinkmorestupidless/speckit-bdd/releases/download/vX.Y.Z/speckit-bdd-extension-X.Y.Z.zip
specify preset add bdd --from https://github.com/thinkmorestupidless/speckit-bdd/releases/download/vX.Y.Z/speckit-bdd-preset-X.Y.Z.zip
```

The commands run the checker with `uvx`, so `uv` must be on `PATH`, as it is wherever spec-kit was
installed with it.

## What a project gains

| File | Holds | Written by |
| --- | --- | --- |
| `GLOSSARY.md` | every word the features use, each in one sense | `/speckit-bdd-features` proposes terms; `/speckit-clarify` settles them |
| `features/<area>/*.feature` | what the system does now, in Gherkin | `/speckit-bdd-features`, from each spec |
| `specs/NNN-*/spec.md` | spec-kit's spec, whose acceptance scenarios name scenarios in the features | `/speckit-specify`, from the preset's template |

### The glossary

```markdown
# Glossary

### cart
The items a customer has chosen and not yet ordered.

Avoid: basket, trolley

### unpaid order
*Proposed.* An order that has been placed and not yet paid for.

## Everyday words

pay, pays, send, holds, empty, minutes
```

Each `###` is a term, as steps write it; a term may be several words. `Avoid:` lists the synonyms a
step must not use for it. `*Proposed.*` marks a term `/speckit-clarify` has still to settle.
`## Everyday words` lists the ordinary words steps use without a definition. Every other word in a
step is reported until it is one or the other, so the vocabulary is always written down in one place.

### A spec's acceptance scenarios

```markdown
**Acceptance Scenarios** *(each names a scenario in a living feature; none is written here)*:

- added `features/checkout/cancel.feature`: an unpaid order is cancelled after thirty minutes
- changed `features/checkout/pay.feature`: a declined card leaves the order unpaid
- removed `features/checkout/pay.feature`: a cheque is accepted
```

## Commands

| Command | Runs | Does |
| --- | --- | --- |
| `/speckit-bdd-features` | after `/speckit-specify` | writes the spec's scenarios into the features, proposes glossary terms, and rewrites the spec's acceptance scenarios as references |
| `/speckit-bdd-check` | before `/speckit-clarify` | runs the checks over every feature, fixes what needs no decision, and turns the rest into clarification questions |

## The checks

`speckit-bdd check` exits 0 with nothing found, 1 with findings, and 2 when misused, so CI can gate
on it. Each finding names a file and a line.

| Check | Finds |
| --- | --- |
| `undefined-term` | a word in a step that is neither a glossary term nor an everyday word |
| `refused-synonym` | a word the glossary lists under a term's `Avoid:` |
| `contradiction` | two scenarios with the same preconditions (in any order) and actions (in order), and different outcomes |
| `repeated-scenario` | two scenarios that say the same thing |
| `unknown-scenario` | a spec reference to a scenario no feature has |
| `removed-scenario-present` | a scenario a spec says it removed, still in a feature |
| `untraced-requirement` | an acceptance criterion in a spec that names no scenario |
| `duplicated-scenario` | Given/When/Then written in a spec, where it belongs in a feature |
| `parse` | a feature that is not valid Gherkin |

Scenarios are compared as Cucumber compiles them: a `Background` is part of every scenario after it,
each `Examples` row of a `Scenario Outline` is its own scenario, and `And`/`But` take the kind of the
step before them.

```bash
uvx --from "git+https://github.com/thinkmorestupidless/speckit-bdd@vX.Y.Z#subdirectory=checker" speckit-bdd check --root .
```

## Development

```bash
python3 -m venv .venv && .venv/bin/pip install -e "checker[test]"
.venv/bin/pytest -q checker                 # the checks, against small projects built per test
python3 preset/build.py --check             # the preset's template is what spec-kit's builds
python3 preset/build.py --latest --check    # ...and still is, against spec-kit's main branch
scripts/integration.sh                      # both installed by the real `specify`; SPECIFY=… for another
```

### Releasing

```bash
git tag v0.1.0 && git push --tags
```

The `release` workflow runs the tests on the tagged tree, builds both archives with
`scripts/package.sh` (every `0.0.0` placeholder stamped in a copy under `dist/`, never in the tree),
installs them by URL into fresh projects on the oldest and the latest supported spec-kit, and only
then publishes a GitHub release with them attached. The checker is not published anywhere: the
commands run it from the tag with `uvx`, and it takes its version from the tag (hatch-vcs).

`scripts/package.sh 0.1.0` builds the same archives locally.

The preset's template is built, never edited: `preset/build.py` applies a stated list of changes to
spec-kit's own template (`preset/upstream/`), so a change spec-kit makes to a replaced part fails the
build by name.

spec-kit 0.14 installs the extension's config template without rendering
`.specify/extensions/bdd/bdd-config.yml`; the commands read the defaults when the file is absent.
