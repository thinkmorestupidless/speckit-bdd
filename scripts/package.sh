#!/usr/bin/env bash
# Builds the release archives for one version: `scripts/package.sh 0.1.0` writes
#
#   dist/speckit-bdd-extension-0.1.0.zip   for `specify extension add bdd --from …`
#   dist/speckit-bdd-preset-0.1.0.zip      for `specify preset add bdd --from …`
#
# each with its manifest at the archive's root, and every `0.0.0` placeholder replaced by the
# version: the manifests, and the checker the commands run, pinned to this release's tag. (The
# checker takes its own version from that tag.) The tree is never written: the placeholders are
# stamped in a copy under dist/, so a release cannot dirty the checkout it was cut from.
set -euo pipefail

version="${1:?usage: scripts/package.sh <version, e.g. 0.1.0>}"
[[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+([.-][0-9A-Za-z.-]+)?$ ]] || { echo "package: '$version' is not a version" >&2; exit 2; }

root="$(cd "$(dirname "$0")/.." && pwd)"
dist="$root/dist"
stage="$dist/stage"
rm -rf "$stage" && mkdir -p "$stage"

fail() { echo "package: $*" >&2; exit 1; }

# The files each placeholder lives in, and how many each must hold. A placeholder that moves or
# multiplies fails the build rather than shipping a release that names version 0.0.0.
stamp() {
  local file="$1" pattern="$2" expected="$3" found
  found="$(grep -c -- "$pattern" "$file" || true)"
  [ "$found" = "$expected" ] || fail "$file holds '$pattern' $found time(s), not $expected"
  sed -i.bak "s/$pattern/${pattern//0.0.0/$version}/g" "$file" && rm "$file.bak"
}

cp -R "$root/extension" "$stage/extension"
cp -R "$root/preset" "$stage/preset"
rm -rf "$stage/preset/upstream" "$stage/preset/build.py"   # how the template is made, not part of it

stamp "$stage/extension/extension.yml" 'version: "0.0.0"' 1
stamp "$stage/extension/config-template.yml" 'speckit-bdd@v0.0.0#' 1
stamp "$stage/extension/commands/speckit.bdd.features.md" 'speckit-bdd@v0.0.0#' 1
stamp "$stage/extension/commands/speckit.bdd.check.md" 'speckit-bdd@v0.0.0#' 1
stamp "$stage/preset/preset.yml" 'version: "0.0.0"' 1

if grep -rn "0\.0\.0" "$stage" > /dev/null; then
  fail "a placeholder survived stamping:
$(grep -rn "0\.0\.0" "$stage")"
fi

for part in extension preset; do
  archive="$dist/speckit-bdd-$part-$version.zip"
  rm -f "$archive"
  (cd "$stage/$part" && find . -type f -not -name '.DS_Store' | LC_ALL=C sort | zip -q -X "$archive" -@)
  echo "built $archive"
done
