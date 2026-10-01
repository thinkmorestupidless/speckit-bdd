#!/usr/bin/env bash
# Installs the extension and the preset into a fresh spec-kit project with the real `specify` CLI,
# and checks spec-kit wired them in: the commands exist, the hooks run them, the config is in place,
# and the spec template resolves to the preset's.
#
#   scripts/integration.sh            # the `specify` on PATH, the extension and preset from this tree
#   SPECIFY=/path/to/specify scripts/integration.sh
#   EXTENSION=<url> PRESET=<url> scripts/integration.sh   # from release archives, as users install
#
# Nothing short of spec-kit itself can show these: a manifest that parses can still name a hook
# spec-kit does not run, or a template spec-kit does not resolve.
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
specify="${SPECIFY:-specify}"
project="$(mktemp -d)"
logs="$(mktemp -d)"   # outside the project: `specify init --here` refuses a directory that is not empty
trap 'rm -rf "$project" "$logs"' EXIT

fail() { echo "integration: $*" >&2; exit 1; }

cd "$project"
# `--non-interactive` arrived after 0.14.0, the oldest spec-kit the manifests support; before it,
# `init` asks nothing in an empty directory without a terminal.
# (The help is read whole: `grep -q` on a pipe would stop reading at its match, and under
# `pipefail` the CLI dying on the closed pipe would read as the flag being absent.)
quiet=()
case "$("$specify" init --help 2>&1 || true)" in *--non-interactive*) quiet=(--non-interactive) ;; esac
# ${quiet[@]+…}: bash 3.2, macOS's, calls an empty array unbound under `set -u`.
"$specify" init --here --integration claude --script sh --ignore-agent-tools ${quiet[@]+"${quiet[@]}"} > "$logs/init" 2>&1 < /dev/null \
  || fail "specify init failed: $(tail -20 "$logs/init")"
# A directory installs as a development copy; a URL as a user installs a release, answering yes to
# spec-kit's question about trusting the source.
install() {
  local kind="$1" source="$2"
  case "$source" in
    http://* | https://*) echo y | "$specify" "$kind" add bdd --from "$source" ;;
    *) "$specify" "$kind" add --dev "$source" ;;
  esac
}
install extension "${EXTENSION:-$root/extension}" > "$logs/extension" 2>&1 \
  || fail "the extension did not install: $(tail -20 "$logs/extension")"
install preset "${PRESET:-$root/preset}" > "$logs/preset" 2>&1 \
  || fail "the preset did not install: $(tail -20 "$logs/preset")"
echo "installed  ${EXTENSION:-$root/extension}, ${PRESET:-$root/preset}"

for skill in speckit-bdd-features speckit-bdd-check; do
  [ -f ".claude/skills/$skill/SKILL.md" ] || fail "no /$skill command was generated"
done
echo "commands   /speckit-bdd-features, /speckit-bdd-check"

hooks=.specify/extensions.yml
[ -f "$hooks" ] || fail "no $hooks: spec-kit registered no hooks"
for pair in "after_specify speckit.bdd.features" "before_clarify speckit.bdd.check"; do
  set -- $pair
  grep -A3 "^  $1:" "$hooks" | grep -q "command: $2" || fail "$1 does not run $2:
$(cat "$hooks")"
done
echo "hooks      after_specify, before_clarify"

# Newer spec-kit renders the config from its template at install; 0.14 copies the template and
# leaves the config to the user, and the commands read the defaults when it is absent.
if [ -f .specify/extensions/bdd/bdd-config.yml ]; then
  echo "config     .specify/extensions/bdd/bdd-config.yml"
elif [ -f .specify/extensions/bdd/config-template.yml ]; then
  echo "config     not rendered by this spec-kit; the commands use the defaults"
else
  fail "neither the extension's config nor its template is in the project"
fi

resolved="$("$specify" preset resolve spec-template 2>&1 | tr -d '\n ')"
case "$resolved" in
  *presets/bdd/templates/spec-template.md*) ;;
  *) fail "spec-template resolves elsewhere: $resolved" ;;
esac
grep -q '\*\*Given\*\*' .specify/presets/bdd/templates/spec-template.md \
  && fail "the resolved spec template still writes Given/When/Then prose"
echo "template   spec-template resolves to the bdd preset"
