#!/bin/bash
# usage: holes6.sh file k
f=$1; k=$2; tot=0; out=""
for d in "0,0,-1" "0.8,0,-1" "-0.8,0,-1" "0,0.6,-1" "0.8,0,1" "-0.8,0,1"; do
  r=$(/home/claude/venv/py311/bin/python -I /home/claude/work/scripts/check/gapview.py /home/claude/work/scripts/check "$f" $k "$d" 2>&1 | grep -E "hole pixels" | tail -1)
  out="$out | $d: $r"
done
echo "$out"
