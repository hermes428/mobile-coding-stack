#!/usr/bin/env bash
# Mobile Coding Stack installer / upgrader.
# Usage: bash install.sh [target-repo-dir]   (default: current directory)
# Safe to re-run: managed files are replaced, your contract/state/lessons are kept,
# and existing .claude/settings.json hooks are merged, not overwritten.
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/template/.claude"
TARGET="$(cd "${1:-.}" && pwd)"
DEST="$TARGET/.claude"
WORK="$TARGET/.mcs"
VERSION="$(cat "$(dirname "$SRC")/../VERSION")"

mkdir -p "$DEST/stack/hooks" "$DEST/agents" "$DEST/skills" "$WORK/archive"

# Managed files: always replaced with this version.
cp "$SRC/stack/hooks/stack.py"            "$DEST/stack/hooks/stack.py"
cp "$SRC/stack/governance.md"             "$DEST/stack/governance.md"
cp "$SRC/stack/contract.template.md"      "$DEST/stack/contract.template.md"
cp "$SRC/agents/architect.md"             "$DEST/agents/architect.md"
cp "$SRC/agents/verifier.md"              "$DEST/agents/verifier.md"
for s in build verify status scientific-rigor capability-provisioning; do
  mkdir -p "$DEST/skills/$s"
  cp "$SRC/skills/$s/SKILL.md" "$DEST/skills/$s/SKILL.md"
done
chmod +x "$DEST/stack/hooks/stack.py"
echo "$VERSION" > "$DEST/stack/VERSION"
touch "$WORK/archive/.gitkeep"

# Project-owned files: created once, never overwritten.
[ -f "$WORK/lessons.md" ] || cp "$SRC/../.mcs/lessons.md" "$WORK/lessons.md"

# Merge hooks into settings.json.
python3 - "$SRC/settings.json" "$DEST/settings.json" <<'PY'
import json, os, sys
src, dest = sys.argv[1], sys.argv[2]
new = json.load(open(src))
cur = json.load(open(dest)) if os.path.exists(dest) else {}
hooks = cur.setdefault("hooks", {})
def cmds(groups):
    return {h.get("command") for g in groups for h in g.get("hooks", [])}
for event, groups in new["hooks"].items():
    have = hooks.setdefault(event, [])
    existing = cmds(have)
    for g in groups:
        if not cmds([g]) <= existing:
            have.append(g)
allow = cur.setdefault("permissions", {}).setdefault("allow", [])
for rule in new.get("permissions", {}).get("allow", []):
    if rule not in allow:
        allow.append(rule)
with open(dest, "w") as f:
    json.dump(cur, f, indent=2)
    f.write("\n")
PY

python3 "$DEST/stack/hooks/stack.py" status >/dev/null
echo "Mobile Coding Stack v$VERSION installed in $DEST"
echo "Next: commit .claude/ and .mcs/, then start with /build <task>."
