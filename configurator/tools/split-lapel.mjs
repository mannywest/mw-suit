// node tools/split-lapel.mjs in.glb out.glb  — refine the jacket mesh around the lapel boundary (red-green midpoint subdivision,
// edges keyed by position so UV/normal seams stay crack-free) and split the lapel into its own primitive + material "Jacket_Lapel".
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';
const [, , inp, outp] = process.argv;
const L = { yMin: 1.12, yMax: 1.42, zMin: 0.04, e0: 0.017, e0y: 1.12, slope: 0.14, inner: -0.006, o0: 0.0075, o0y: 1.13, oSlope: 0.515, maxX: 0.125 };
const SEL = { minRank: 12, yMin: 1.05, zMin: 0.0, maxCx: 0.16, maxX: 0.17 };
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS);
const doc = await io.read(inp);
const mesh = doc.getRoot().listMeshes().find(m => m.getName() === 'Jacket');
const prim = mesh.listPrimitives()[0];
const names = prim.listSemantics();
let attrs = Object.fromEntries(names.map(n => [n, prim.getAttribute(n)]));
const arr = {}; for (const n of names) arr[n] = { a: Array.from(attrs[n].getArray()), size: attrs[n].getElementSize() };
let idx = Array.from(prim.getIndices().getArray());
const P = arr.POSITION.a;
const pk = i => `${Math.round(P[3 * i] * 1e5)},${Math.round(P[3 * i + 1] * 1e5)},${Math.round(P[3 * i + 2] * 1e5)}`;
const inLapel = (x, y, z) => { x = Math.abs(x); const e = L.e0 + (y - L.e0y) * L.slope, o = Math.min(L.maxX, L.o0 + (y - L.o0y) * L.oSlope); return y > L.yMin && y < L.yMax && z > L.zMin && x > e + L.inner && x < o; };
const tri = t => { const [a, b, c] = t; return inLapel((P[3*a]+P[3*b]+P[3*c])/3, (P[3*a+1]+P[3*b+1]+P[3*c+1])/3, (P[3*a+2]+P[3*b+2]+P[3*c+2])/3); };
const vcls = i => inLapel(P[3 * i], P[3 * i + 1], P[3 * i + 2]);
// Island-based: the model's own pattern pieces (index-connected components) include the lapel/collar as small separate islands.
let tris = []; for (let t = 0; t < idx.length; t += 3) tris.push([idx[t], idx[t + 1], idx[t + 2]]);
const par = Int32Array.from({ length: P.length / 3 }, (_, i) => i); const find = x => { while (par[x] !== x) { par[x] = par[par[x]]; x = par[x]; } return x; };
for (const t of tris) for (const [a, b] of [[0, 1], [1, 2]]) { const x = find(t[a]), y = find(t[b]); if (x !== y) par[x] = y; }
const isl = new Map(); for (const t of tris) { const r = find(t[0]); (isl.get(r) ?? isl.set(r, []).get(r)).push(t); }
const ranked = [...isl.values()].sort((a, b) => b.length - a.length);
const lap = [], rest = [], wb = []; const picked = [];
ranked.forEach((ts, rank) => {
  let n = 0, cx = 0, cy = 0, cz = 0, ymax = -9, xmax = 0;
  for (const t of ts) for (const v of t) { n++; cx += Math.abs(P[3 * v]); cy += P[3 * v + 1]; cz += P[3 * v + 2]; ymax = Math.max(ymax, P[3 * v + 1]); xmax = Math.max(xmax, Math.abs(P[3 * v])); }
  cx /= n; cy /= n; cz /= n;
  // trouser waistband (+ hook button area) is modelled inside the jacket mesh: move it to the trousers material
  const isWb = rank >= SEL.minRank && cy > 0.9 && cy < 1.01 && cz > 0.1 && cz < 0.14 && cx < 0.1 && ts.length < 300;
  if (isWb) { for (const t of ts) wb.push(...t); return; }
  let ymin = 9, xmin = 9; for (const t of ts) for (const v of t) { ymin = Math.min(ymin, P[3 * v + 1]); xmin = Math.min(xmin, Math.abs(P[3 * v])); }
  // exclude front-edge facing strips (reach below the lapel), breast-pocket welt bars (flat, wide, mid-chest) and shoulder-seam slivers
  const welt = (ymax - ymin) < 0.06 && cy < 1.31 && cy > 1.2 && cz > 0.07 && cz < 0.14 && cx > 0.06;
  const sel = rank >= SEL.minRank && cy > SEL.yMin && cz > SEL.zMin && cx < SEL.maxCx && xmax < SEL.maxX && ymin > (+(process.env.LAPEL_YMIN ?? 1.08)) && cx < 0.125 && !welt && !(ts.length <= 20 && cx > 0.1 && cy > 1.39 && cz < 0.07 && !process.env.KEEP_CORNER); // last: loose slivers at the collar corners stick out as spikes
  if (sel) picked.push([rank, ts.length, +cx.toFixed(3), +cy.toFixed(3), +cz.toFixed(3)]); if (process.env.BB && sel && ts.length >= 15) { let b=[9,-9,9,-9,9,-9]; for (const t of ts) for (const v of t) { b[0]=Math.min(b[0],P[3*v]);b[1]=Math.max(b[1],P[3*v]);b[2]=Math.min(b[2],P[3*v+1]);b[3]=Math.max(b[3],P[3*v+1]);b[4]=Math.min(b[4],P[3*v+2]);b[5]=Math.max(b[5],P[3*v+2]); } console.log(rank, ts.length, b.map(x=>+x.toFixed(2)).join(' ')); }
  for (const t of ts) (sel ? lap : rest).push(...t);
});
const CY = +(process.env.COLLAR_Y ?? 1.42), CX = +(process.env.COLLAR_X ?? 0.11), ZC = +(process.env.COLLAR_Z ?? -0.02);
// Back collar: body triangles inside a smooth region (y > CY, radius CX around (0, ZC)) go to the lapel group. To get a smooth edge instead of a
// triangle-staircase, triangles that straddle the region boundary are split (conforming red-green midpoint refinement, edges keyed by position,
// so no cracks) COLLAR_LEVELS times before classifying.
const inColl = (x, y, z) => y > CY && Math.hypot(x, z - ZC) < CX;
const vin = i => inColl(P[3 * i], P[3 * i + 1], P[3 * i + 2]);
{
  const tv = [], tg = [];
  for (const [ar, g] of [[rest, 0], [lap, 1], [wb, 2]]) for (let t = 0; t < ar.length; t += 3) { tv.push(ar[t], ar[t + 1], ar[t + 2]); tg.push(g); }
  const ek = (a, b) => { const x = pk(a), y = pk(b); return x < y ? x + '|' + y : y + '|' + x; };
  let cur = tv, curg = tg;
  for (let lv = 0; lv < +(process.env.COLLAR_LEVELS ?? 4); lv++) {
    const split = new Set();
    for (let t = 0; t < curg.length; t++) {
      if (curg[t] !== 0) continue;
      const a = cur[3 * t], b = cur[3 * t + 1], c = cur[3 * t + 2], ia = vin(a);
      if (ia === vin(b) && ia === vin(c)) continue;
      split.add(ek(a, b)); split.add(ek(b, c)); split.add(ek(c, a));
    }
    if (!split.size) break;
    const mid = new Map();
    const mv = (u, v) => {
      const k = u < v ? u + ',' + v : v + ',' + u; let m = mid.get(k); if (m !== undefined) return m;
      m = P.length / 3;
      for (const n of names) { const { a, size } = arr[n]; const o = a.length; for (let s = 0; s < size; s++) a.push((a[u * size + s] + a[v * size + s]) / 2); if (n === 'NORMAL') { const l = Math.hypot(a[o], a[o + 1], a[o + 2]) || 1; a[o] /= l; a[o + 1] /= l; a[o + 2] /= l; } }
      mid.set(k, m); return m;
    };
    const nv = [], ng = [];
    for (let t = 0; t < curg.length; t++) {
      let a = cur[3 * t], b = cur[3 * t + 1], c = cur[3 * t + 2]; const g = curg[t];
      const sa = split.has(ek(a, b)), sb = split.has(ek(b, c)), sc = split.has(ek(c, a)), n = +sa + +sb + +sc;
      const out = [];
      if (n === 0) out.push(a, b, c);
      else if (n === 3) { const ab = mv(a, b), bc = mv(b, c), ca = mv(c, a); out.push(a, ab, ca, ab, b, bc, ca, bc, c, ab, bc, ca); }
      else if (n === 1) { if (sb) [a, b, c] = [b, c, a]; else if (sc) [a, b, c] = [c, a, b]; const m = mv(a, b); out.push(a, m, c, m, b, c); }
      else { if (!sa) [a, b, c] = [b, c, a]; else if (!sb) [a, b, c] = [c, a, b]; const m1 = mv(a, b), m2 = mv(b, c); out.push(m1, b, m2, a, m1, m2, a, m2, c); }
      for (let i = 0; i < out.length; i += 3) { nv.push(out[i], out[i + 1], out[i + 2]); ng.push(g); }
    }
    cur = nv; curg = ng;
  }
  rest.length = lap.length = wb.length = 0;
  for (let t = 0; t < curg.length; t++) {
    const a = cur[3 * t], b = cur[3 * t + 1], c = cur[3 * t + 2]; let g = curg[t];
    if (g === 0 && inColl((P[3*a]+P[3*b]+P[3*c])/3, (P[3*a+1]+P[3*b+1]+P[3*c+1])/3, (P[3*a+2]+P[3*b+2]+P[3*c+2])/3)) g = 1;
    (g === 0 ? rest : g === 1 ? lap : wb).push(a, b, c);
  }
}
console.log('lapel islands', picked.length); if (process.env.LIST) console.log(JSON.stringify(picked));
const buf = doc.getRoot().listBuffers()[0];
for (const n of names) { const acc = attrs[n]; acc.setArray(Float32Array.from(arr[n].a)); }
const mkIdx = (a, ref) => ref.setArray(a.length > 65535 || P.length / 3 > 65535 ? Uint32Array.from(a) : Uint16Array.from(a));
const idxBody = prim.getIndices(); mkIdx(rest, idxBody);
const idxLap = doc.createAccessor().setType('SCALAR').setBuffer(buf); mkIdx(lap, idxLap);
const mat = prim.getMaterial(); const matL = mat.clone().setName('Jacket_Lapel');
const p2 = doc.createPrimitive(); for (const n of names) p2.setAttribute(n, attrs[n]); p2.setIndices(idxLap).setMaterial(matL).setMode(prim.getMode());
mesh.addPrimitive(p2);
if (wb.length) { const idxW = doc.createAccessor().setType('SCALAR').setBuffer(buf); mkIdx(wb, idxW); const p3 = doc.createPrimitive(); for (const n of names) p3.setAttribute(n, attrs[n]); p3.setIndices(idxW).setMaterial(doc.getRoot().listMaterials().find(m => m.getName() === 'Trousers_Wool')).setMode(prim.getMode()); mesh.addPrimitive(p3); }
await io.write(outp, doc);
console.log(JSON.stringify({ verts: P.length / 3, trisBody: rest.length / 3, trisLapel: lap.length / 3, trisWaistband: wb.length / 3, trisBefore: idx.length / 3 }));
