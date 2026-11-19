#!/bin/bash
# Full rebuild: body + lapel/collar. Usage: scripts/rebuild_suit.sh IN.glb OUT.glb LAPEL_MATERIAL  (Jacket_Lapel | Jacket_Lapel_Peak | Jacket_Lapel_Shawl)
set -e; cd "$(dirname "$0")/.."
scripts/rebuild_body.sh "$1" /tmp/rs_body.glb
scripts/rebuild_lapel.sh /tmp/rs_body.glb "$2" "$3"
