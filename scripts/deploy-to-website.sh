#!/usr/bin/env bash
# Sync this project's gallery into the personal website and deploy it.
# Run from anywhere in the narrow-corridor-llm repo. Assumes the website repo
# is checked out as a sibling directory:
#   repos/narrow-corridor-llm/  <- this repo (docs/ is the built gallery)
#   repos/website/              <- esonghori.com (served by GitHub Pages)
#
# If the runs changed, rebuild the gallery first:
#   uv run python scripts/build_site.py --runs paper/experiments/results --out docs
set -euo pipefail

cd "$(dirname "$0")/.."                          # narrow-corridor-llm repo root
SRC="docs"
SITE="../website"
DEST="$SITE/narrow-corridor-llm/gallery"

[ -d "$SRC" ]  || { echo "gallery not built: $SRC/ missing — run build_site.py first" >&2; exit 1; }
[ -d "$SITE" ] || { echo "website repo not found at $SITE — check it out next to this repo" >&2; exit 1; }

rsync -a --delete "$SRC/" "$DEST/"               # mirror; --delete drops files removed at the source

if [ -z "$(git -C "$SITE" status --porcelain narrow-corridor-llm/gallery)" ]; then
  echo "gallery already up to date; nothing to deploy."
  exit 0
fi

git -C "$SITE" add narrow-corridor-llm/gallery
git -C "$SITE" commit -m "Sync Narrow Corridor gallery from source repo"
git -C "$SITE" push
echo "deployed: https://esonghori.com/narrow-corridor-llm/gallery/"
