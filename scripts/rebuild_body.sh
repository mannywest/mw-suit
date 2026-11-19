#!/bin/bash
# One-shot rebuild of the jacket body (settings of try 3). Usage: scripts/rebuild_body.sh OLD.glb OUT.glb
set -e; cd "$(dirname "$0")/.."
LOCAL="0.183,0.835,-0.02,80,28;0.242,1.30,-0.01,80,28;0.176,0.945,0.02,60,16;0.175,1.07,0.024,50,14;0.178,1.209,-0.087,50,14" python3 scripts/rebuild_body.py "$1" /tmp/rb_shell.npz 6 2 3.7
python3 scripts/rebuild_decimate.py /tmp/rb_shell.npz /tmp/rb_dec.npz 90000
python3 scripts/rebuild_finish.py "$1" /tmp/rb_dec.npz "$2"
