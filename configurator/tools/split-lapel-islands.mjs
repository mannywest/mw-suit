// node tools/split-lapel-islands.mjs in.glb out.glb  (island-based lapel+collar, tris from tools/lapcol_tris.json; no subdivision)
// (legacy header) node tools/split-lapel.mjs in.glb out.glb  — refine the jacket mesh around the lapel boundary (red-green midpoint subdivision,
// edges keyed by position so UV/normal seams stay crack-free) and split the lapel into its own primitive + material "Jacket_Lapel".
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';
import { readFileSync } from 'fs';
const PEAK = process.env.PEAK ? JSON.parse(readFileSync(new URL('./peak_edit.json', import.meta.url))) : null;
const STYLES = !!process.env.STYLES; // STYLES=1 PEAK=1: keep notch AND add a peak lapel primitive (cloned vertices) so the app can switch
const DROP = new Set(PEAK ? PEAK.drop : []); const lapIds = [];
const SELTRIS = new Set(JSON.parse(readFileSync(new URL('./lapcol_tris.json', import.meta.url))));
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
let tris = []; for (let t = 0; t < idx.length; t += 3) tris.push(Object.assign([idx[t], idx[t + 1], idx[t + 2]], { id: t / 3 }));
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
  const sel = ts.filter(t => SELTRIS.has(t.id)).length > ts.length / 2;
  for (const t of ts) { if (!STYLES && DROP.has(t.id)) continue; (sel ? lap : rest).push(...t); if (sel) lapIds.push(t.id); }
});

const lapPeak = [];
const RB = process.env.REBUILD ? JSON.parse(readFileSync(new URL('./peak_rebuild.json', import.meta.url))) : null;
if (RB) { // rebuilt peak lapel: new grid lapel (rolled surface + edge rim) with fresh vertices + original collar triangles
  const nv0 = P.length / 3, map = { POSITION: RB.P, NORMAL: RB.N, TEXCOORD_0: RB.U0, TEXCOORD_1: RB.U1 };
  for (const n of names) { const { a, size } = arr[n]; const src = map[n]; if (!src) { for (let i = 0; i < RB.P.length; i++) for (let q = 0; q < size; q++) a.push(0); continue; } for (const v of src) for (let q = 0; q < size; q++) a.push(v[q]); }
  for (const id of RB.collar) lapPeak.push(idx[3 * id], idx[3 * id + 1], idx[3 * id + 2]);
  for (const t of RB.T) lapPeak.push(nv0 + t[0], nv0 + t[1], nv0 + t[2]);
}
else
if (PEAK && STYLES) {
  const clone = new Map(); const nv0 = P.length / 3;
  for (const k of Object.keys(PEAK.moved)) { const ni = nv0 + clone.size; clone.set(+k, ni); for (const n of names) { const { a, size } = arr[n]; for (let q = 0; q < size; q++) a.push(a[+k * size + q]); } arr.POSITION.a.splice(3 * ni, 3, ...PEAK.moved[k]); if (arr.NORMAL) arr.NORMAL.a.splice(3 * ni, 3, ...PEAK.normals[k]); }
  for (let q = 0; q < lapIds.length; q++) { if (DROP.has(lapIds[q])) continue; for (let c = 0; c < 3; c++) { const v = lap[3 * q + c]; lapPeak.push(clone.get(v) ?? v); } }
} else if (PEAK) for (const [k, p] of Object.entries(PEAK.moved)) { arr.POSITION.a.splice(3 * +k, 3, ...p); if (arr.NORMAL) arr.NORMAL.a.splice(3 * +k, 3, ...PEAK.normals[k]); }
const buf = doc.getRoot().listBuffers()[0];
for (const n of names) { const acc = attrs[n]; acc.setArray(Float32Array.from(arr[n].a)); }
const mkIdx = (a, ref) => ref.setArray(a.length > 65535 || P.length / 3 > 65535 ? Uint32Array.from(a) : Uint16Array.from(a));
const idxBody = prim.getIndices(); mkIdx(rest, idxBody);
const idxLap = doc.createAccessor().setType('SCALAR').setBuffer(buf); mkIdx(lap, idxLap);
const mat = prim.getMaterial(); const matL = mat.clone().setName('Jacket_Lapel');
const p2 = doc.createPrimitive(); for (const n of names) p2.setAttribute(n, attrs[n]); p2.setIndices(idxLap).setMaterial(matL).setMode(prim.getMode());
mesh.addPrimitive(p2);
if (lapPeak.length) { const idxP = doc.createAccessor().setType('SCALAR').setBuffer(buf); mkIdx(lapPeak, idxP); const matP = mat.clone().setName('Jacket_Lapel_Peak'); const p4 = doc.createPrimitive(); for (const n of names) p4.setAttribute(n, attrs[n]); p4.setIndices(idxP).setMaterial(matP).setMode(prim.getMode()); mesh.addPrimitive(p4); }
if (wb.length) { const idxW = doc.createAccessor().setType('SCALAR').setBuffer(buf); mkIdx(wb, idxW); const p3 = doc.createPrimitive(); for (const n of names) p3.setAttribute(n, attrs[n]); p3.setIndices(idxW).setMaterial(doc.getRoot().listMaterials().find(m => m.getName() === 'Trousers_Wool')).setMode(prim.getMode()); mesh.addPrimitive(p3); }
await io.write(outp, doc);
console.log(JSON.stringify({ verts: P.length / 3, trisBody: rest.length / 3, trisLapel: lap.length / 3, trisPeak: lapPeak.length / 3, trisWaistband: wb.length / 3, trisBefore: idx.length / 3 }));
