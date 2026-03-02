#!/usr/bin/env bash
# Make trade-skills commands available globally from any Claude Code project.
# Run once per machine after cloning.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GLOBAL_COMMANDS_DIR="$HOME/.claude/commands"

mkdir -p "$GLOBAL_COMMANDS_DIR"

for cmd_file in "$REPO_DIR/.claude/commands/"*.md; do
    cmd_name="$(basename "$cmd_file")"
    target="$GLOBAL_COMMANDS_DIR/$cmd_name"
    ln -sf "$cmd_file" "$target"
    echo "linked: $target -> $cmd_file"
done

echo ""
echo "Done. Skills available globally in any Claude Code project:"
for cmd_file in "$REPO_DIR/.claude/commands/"*.md; do
    cmd_name="$(basename "$cmd_file" .md)"
    echo "  /$cmd_name"
done
