import * as THREE from 'three';
// Runtime lapel/collar split for the v2 jacket (no GLB change). Rule is geometric, in model space (metres, +z = front):
// front-facing triangles above the lapel tip, between the front opening edge e(y) and e(y)+WIDTH.
// Tune here; run with ?debug=lapel to see the selection in red.
// e(y): front opening edge. o(y): outer lapel edge, tapering from the tip (~y 1.13) up to the notch; capped at maxX.
export const LAPEL = { yMin: 1.12, yMax: 1.42, zMin: 0.04, e0: 0.017, e0y: 1.12, slope: 0.14, inner: -0.006, o0: 0.0075, o0y: 1.13, oSlope: 0.515, maxX: 0.125 };

export function splitLapel(mesh: THREE.Mesh, bodyMat: THREE.Material, lapelMat: THREE.Material): number {
  const g = mesh.geometry as THREE.BufferGeometry, pos = g.getAttribute('position'), idx = g.getIndex()!;
  const a = idx.array, n = a.length / 3, lap: number[] = [], rest: number[] = [];
  for (let t = 0; t < n; t++) {
    const i0 = a[3 * t], i1 = a[3 * t + 1], i2 = a[3 * t + 2];
    const x = Math.abs(pos.getX(i0) + pos.getX(i1) + pos.getX(i2)) / 3, y = (pos.getY(i0) + pos.getY(i1) + pos.getY(i2)) / 3, z = (pos.getZ(i0) + pos.getZ(i1) + pos.getZ(i2)) / 3;
    const e = LAPEL.e0 + (y - LAPEL.e0y) * LAPEL.slope, o = Math.min(LAPEL.maxX, LAPEL.o0 + (y - LAPEL.o0y) * LAPEL.oSlope);
    (y > LAPEL.yMin && y < LAPEL.yMax && z > LAPEL.zMin && x > e + LAPEL.inner && x < o ? lap : rest).push(i0, i1, i2);
  }
  g.setIndex([...rest, ...lap]); g.clearGroups();
  g.addGroup(0, rest.length, 0); g.addGroup(rest.length, lap.length, 1);
  mesh.material = [bodyMat, lapelMat];
  return lap.length / 3;
}
