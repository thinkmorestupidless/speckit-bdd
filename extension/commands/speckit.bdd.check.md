---
description: "Check the features, the glossary and the specs; turn each finding into a question to resolve"
---

# Check the features, the glossary and the specs

Runs the mechanical checks over every feature, not only the current spec's, and turns what they
find into questions. Before `/speckit-clarify`, these are its first questions: a contradiction or an
undefined word is exactly the ambiguity clarification exists to remove.

## User input

```text
$ARGUMENTS
```

Consider the user input before proceeding, if it is not empty.

## Run the checker

Read `.specify/extensions/bdd/bdd-config.yml` (where it is missing: `glossary: GLOSSARY.md`,
`features: features`, `specs: specs`, and as the `checker`
`uvx --from "git+https://github.com/thinkmorestupidless/speckit-bdd@v0.0.0#subdirectory=checker" speckit-bdd`),
then from the project root:

```bash
<checker> check --root . --glossary <glossary> --features <features> --specs <specs> --format json
```

It exits 0 with no findings and 1 with some; each finding has `file`, `line`, `check` and
`message`. An exit of 2, or a command that cannot be run, is a problem with the setup: say so and
stop, rather than reporting the project clean.

## Turn findings into questions

| Finding | What to do |
| --- | --- |
| `contradiction` | Ask which outcome is right, quoting both scenarios. Never choose one yourself. |
| `undefined-term` | Ask what the word means here, and whether it is the domain's (a term) or ordinary (an everyday word). |
| `refused-synonym` | Reword the step with the glossary's term; no question. |
| `repeated-scenario` | Remove the later copy and update any spec that names it; no question. |
| `unknown-scenario`, `removed-scenario-present` | Correct the spec's reference, or ask whether the scenario should exist. |
| `untraced-requirement` | Ask for the scenario that shows the requirement holds, or whether it is a requirement at all. |
| `duplicated-scenario` | Move the Given/When/Then into a feature and reference it from the spec; no question. |
| `parse` | Fix the Gherkin. |

Then read the features yourself for two things the checker cannot decide, and report each as a
suspicion, not a finding:

- **Implementation in a step**: a screen, a button, a route, a status code or a component, where the
  domain's words belong.
- **The same situation in other words**: two scenarios that differ in wording but describe the same
  preconditions and action. If their outcomes differ, it is a contradiction.

Also settle every `*Proposed.*` glossary term: ask whether the word is right, what it does not mean,
and which synonyms to refuse.

## Report

The questions, most consequential first (contradictions, then undefined terms, then the rest), each
with its file and line, followed by what was fixed without asking.
