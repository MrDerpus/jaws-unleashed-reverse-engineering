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
# Build this level from custom_fish.blend and put it in the game as TEST.GDW.
#
#   ./build.sh                  export from Blender, build, install
#   ./build.sh --show-exits     same, with pink columns marking exit zones
#   ./build.sh --no-deploy      build only (custom_fish.GDW here), don't install
#
# Save the .blend in Blender first: this reads the saved file.
# In the game: enter Fisherman's Isle from Open Ocean South, or press F10 if
# you're already in the level.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SCRIPTS="$HERE/../../scripts"
DEPLOY=(--deploy TEST)
EXTRA=()
for arg in "$@"; do
    case "$arg" in
        --show-exits) EXTRA+=(--show-exits) ;;
        --no-deploy)  DEPLOY=() ;;
        *) echo "unknown option: $arg" >&2; exit 1 ;;
    esac
done

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
if ! python3 build_scene.py "$HERE/FISH_minimal_base.GDW" "$HERE/custom_fish.GDW" \
        "$HERE/blender_export" "${DEPLOY[@]}" "${EXTRA[@]}" >> "$LOG" 2>&1; then
    echo "Build failed. Last lines of build.log:" >&2; tail -15 "$LOG" >&2; exit 1
fi
grep -E "^(node|exit zone|texture |material |wrote|deployed)|large mesh|warning" "$LOG" || true
[ ${#DEPLOY[@]} -eq 0 ] && echo "built $HERE/custom_fish.GDW (not installed)"
exit 0
