#!/bin/bash
# Rebuild a lapel/collar prim as a smooth closed shell.  Usage: scripts/rebuild_lapel.sh IN.glb OUT.glb MATERIAL_NAME   (IN should already have the rebuilt body)
set -e; cd "$(dirname "$0")/.."
MAT="$3" python3 scripts/rebuild_body.py "$1" /tmp/rl_shell.npz ${RL_R:-3} ${RL_V:-1.5} ${RL_T:-3.4}
python3 scripts/rebuild_decimate.py /tmp/rl_shell.npz /tmp/rl_dec.npz ${RL_TRIS:-14000}
MAT="$3" INNER=wool python3 scripts/rebuild_finish.py "$1" /tmp/rl_dec.npz "$2"
