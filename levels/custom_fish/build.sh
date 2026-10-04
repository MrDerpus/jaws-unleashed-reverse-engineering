#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Jaws Unleashed reverse engineering tools
# Copyright (C) 2026 MrDerpus and contributors
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# Build this level from custom_fish.blend and install it in the game's
# custom_levels/ folder (next to Jaws.exe) as LEVEL_NAME.GDW.
#
#   ./build.sh                  export from Blender, build, install
#   ./build.sh --show-exits     same, with pink columns marking exit zones
#   ./build.sh --no-deploy      build only (custom_fish.GDW here), don't install
#
# Save the .blend in Blender first: this reads the saved file.
# In the game: press F9 and pick the level (needs the mod), or press F10 if
# you're already in it.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SCRIPTS="$HERE/../../scripts"
LEVEL_NAME=CUSTOM_FISH   # letters, digits and _ only; not a stock level's name
# Level music: keep (Fisherman's Isle's), none (silent, ~41 MB smaller), or
# custom (the files in music/: calm_above, calm_under, suspense, action; any
# audio format; missing ones fall back to calm_above).
MUSIC=keep
DEPLOY=(--deploy "$LEVEL_NAME")
EXTRA=()
for arg in "$@"; do
    case "$arg" in
        --show-exits) EXTRA+=(--show-exits) ;;
        --no-deploy)  DEPLOY=() ;;
        *) echo "unknown option: $arg" >&2; exit 1 ;;
    esac
done

case "$MUSIC" in
    keep|none) MUSIC_ARG="$MUSIC" ;;
    custom)    MUSIC_ARG="$HERE/music" ;;
    *) echo "MUSIC must be keep, none or custom" >&2; exit 1 ;;
esac

LOG="$HERE/build.log"
echo "== Exporting from custom_fish.blend"
rm -rf "$HERE/blender_export"
blender -b "$HERE/custom_fish.blend" --python "$SCRIPTS/blender_export_scene.py" > "$LOG" 2>&1 || true
if [ ! -f "$HERE/blender_export/manifest.json" ]; then
    echo "Export failed. Last lines of build.log:" >&2; tail -15 "$LOG" >&2; exit 1
fi
grep -E "^exported" "$LOG"

echo "== Building the level"
cd "$SCRIPTS"
if ! python3 build_scene.py "$HERE/FISH_blank_base.GDW" "$HERE/custom_fish.GDW" \
        "$HERE/blender_export" --prune --music "$MUSIC_ARG" "${DEPLOY[@]}" "${EXTRA[@]}" >> "$LOG" 2>&1; then
    echo "Build failed. Last lines of build.log:" >&2; tail -15 "$LOG" >&2; exit 1
fi
grep -E "^(node|exit zone|spawn|music|pruned|texture |material |wrote|deployed)|large mesh|warning" "$LOG" || true
[ ${#DEPLOY[@]} -eq 0 ] && echo "built $HERE/custom_fish.GDW (not installed)"
exit 0
