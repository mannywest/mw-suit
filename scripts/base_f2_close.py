#!/usr/bin/env python3
"""Close see-through gaps left at the torso/sleeve junction (|x| 0.17-0.225, y 0.72-1.02) after the side panels. python3 scripts/base_f2_close.py IN.glb OUT.glb"""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np, base_e_sides as be
be.WHERE = lambda p: 0.17 < abs(p[0]) < 0.225 and 0.72 < p[1] < 1.02
src, dst = sys.argv[1], sys.argv[2]; cur = src
for ps in range(1):
    fl = be.fills_for(cur, ['sleeve', 'hem']); nxt = dst if ps == 0 else '/tmp/stepF2_pass1.glb'
    n = be.write(cur, nxt, fl); print('pass', ps + 1, 'added', n, 'tris'); cur = nxt
    if not n:
        import shutil; shutil.copy(cur, dst); break
