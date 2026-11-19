import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { MeshoptDecoder } from 'three/examples/jsm/libs/meshopt_decoder.module.js';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';
import { REGIONS, FINISHES, MODEL_FILE, UV_CM_PER_UNIT, type Fabric, type Config, type Ticket } from './config';
import { RGBELoader } from 'three/examples/jsm/loaders/RGBELoader.js';
import { splitLapel } from './lapel';
import { loadTrims, trimPanel, applyTrims, trimState, trimTicket, setTrim } from './trims';
import { TUNING, FIBRE_CM, makeNormalTexture, fibreTexture } from './pbr';

const view = document.getElementById('view')!, panel = document.getElementById('panel')!, status = document.getElementById('status')!;
const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.toneMapping = THREE.NeutralToneMapping;
renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
view.appendChild(renderer.domElement);
const scene = new THREE.Scene(); scene.background = new THREE.Color(0x15161a);
const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
scene.environmentIntensity = 0.55;
const key = new THREE.DirectionalLight(0xfff4e6, 2.2); key.position.set(2, 3, 3); key.castShadow = true;
key.shadow.mapSize.set(2048, 2048); key.shadow.bias = -0.0004; key.shadow.normalBias = 0.004; key.shadow.radius = 4; scene.add(key);
const fill = new THREE.DirectionalLight(0xdde6ff, 0.45); fill.position.set(-3, 1.2, 2); scene.add(fill);
const rim = new THREE.DirectionalLight(0xffffff, 0.9); rim.position.set(-1, 2.5, -3); scene.add(rim);
const ground = new THREE.Mesh(new THREE.PlaneGeometry(6, 6), new THREE.ShadowMaterial({ opacity: 0.35 })); ground.rotation.x = -Math.PI / 2; ground.receiveShadow = true; scene.add(ground);
// Optional HDRI: drop a studio .hdr at public/env/studio.hdr and it replaces the built-in room lighting.
fetch(import.meta.env.BASE_URL + 'env/studio.hdr', { method: 'HEAD' }).then(r => { if (!r.ok || (r.headers.get('content-type') ?? '').includes('html')) return;
  new RGBELoader().load(import.meta.env.BASE_URL + 'env/studio.hdr', t => { t.mapping = THREE.EquirectangularReflectionMapping; scene.environment = pmrem.fromEquirectangular(t).texture; scene.environmentIntensity = 1; render(); }); }).catch(() => {});
const camera = new THREE.PerspectiveCamera(30, 1, 0.05, 50);
const controls = new OrbitControls(camera, renderer.domElement); controls.enableDamping = true;

const state = { fabrics: {} as Record<string, string>, visible: {} as Record<string, boolean> };
const meshes: Record<string, THREE.Mesh> = {};
const baseMats: Record<string, THREE.MeshPhysicalMaterial> = {};
const texCache = new Map<string, THREE.Texture>();
const normCache = new Map<string, THREE.Texture>();
let library: Fabric[] = [];
let lapelMat: THREE.MeshPhysicalMaterial;
const LAPEL_STYLES: { id: string; name: string; mat: string }[] = [{ id: 'notch', name: 'Notch lapel', mat: 'Jacket_Lapel' }, { id: 'peak', name: 'Peak lapel', mat: 'Jacket_Lapel_Peak' }, { id: 'shawl', name: 'Shawl lapel', mat: 'Jacket_Lapel_Shawl' }];
const styleMeshes: Record<string, THREE.Mesh> = {}; let lapelStyle = 'notch';
function setLapelStyle(id: string) { if (!styleMeshes[id]) return; lapelStyle = id; for (const [k, m] of Object.entries(styleMeshes)) m.visible = k === id && state.visible['jacket_body'] !== false; placeLapelHole(); render(); }
// Lapel buttonhole: a stitched slot on the wearer's left lapel, laid on the lapel surface (found by a ray from the front). Thread colour follows the "Buttonhole thread" trim.
const HOLE_X = 0.085, HOLE_Y = 1.33, HOLE_TILT = 0.2; // metres / radians; tune per look
let holeMesh: THREE.Mesh | null = null;
// --- buttonhole designs (traced by eye from the trims-book photo; mm in a 2D plane, x = long axis). 01, 02 and 08 not drawn yet -> plain slot.
type Pt = [number, number];
const arcPts = (cx: number, cy: number, rx: number, ry: number, a0: number, a1: number, n = 24): Pt[] => Array.from({ length: n + 1 }, (_, i) => { const a = a0 + (a1 - a0) * i / n; return [cx + rx * Math.cos(a), cy + ry * Math.sin(a)] as Pt; });
const heartPts = (cx: number, cy: number, sc: number, n = 40): Pt[] => Array.from({ length: n }, (_, i) => { const t = i / n * 2 * Math.PI; return [cx + sc * 16 * Math.sin(t) ** 3 / 16, cy + sc * (13 * Math.cos(t) - 5 * Math.cos(2 * t) - 2 * Math.cos(3 * t) - Math.cos(4 * t)) / 16] as Pt; });
const line = (x0: number, x1: number, y = 0): Pt[] => [[x0, y], [x1, y]];
const slotOutline = (c: Pt[], h: (t: number) => number): Pt[] => { // closed outline round a centreline with half-width h(t)
  const L: Pt[] = [], R: Pt[] = [], n = c.length;
  for (let i = 0; i < n; i++) { const a = c[Math.max(0, i - 1)], b = c[Math.min(n - 1, i + 1)], dx = b[0] - a[0], dy = b[1] - a[1], d = Math.hypot(dx, dy) || 1, w = h(i / (n - 1)); L.push([c[i][0] - dy / d * w, c[i][1] + dx / d * w]); R.push([c[i][0] + dy / d * w, c[i][1] - dx / d * w]); }
  const cap = (e: Pt, from: Pt): Pt[] => { const cx = e[0], cy = e[1], a0 = Math.atan2(from[1] - cy, from[0] - cx), r = Math.hypot(from[0] - cx, from[1] - cy); return Array.from({ length: 7 }, (_, i) => { const a = a0 - Math.PI * (i / 6); return [cx + r * Math.cos(a), cy + r * Math.sin(a)] as Pt; }); };
  const endCap = cap(c[n - 1], L[n - 1]), startCap = cap(c[0], R[0]);
  return [...L, ...endCap, ...R.slice().reverse(), ...startCap];
};
const bendC = (x0: number, x1: number, f: (t: number) => number, n = 24): Pt[] => Array.from({ length: n + 1 }, (_, i) => { const t = i / n; return [x0 + (x1 - x0) * t, f(t)] as Pt; });
interface HoleDesign { strokes: { pts: Pt[]; closed: boolean; w: number }[] }
const HOLE_DESIGNS: Record<string, HoleDesign> = {
  '04': { strokes: [{ pts: line(-11, 3), closed: false, w: 0.8 }, { pts: slotOutline(line(1, 11), () => 1.3), closed: true, w: 0.8 }] },
  '05': { strokes: [{ pts: line(-11, 5.5), closed: false, w: 0.9 }, { pts: arcPts(8, 0, 2.4, 2.4, 0, 2 * Math.PI, 28).slice(0, -1), closed: true, w: 0.9 }] },
  '07': { strokes: [{ pts: slotOutline(line(-9.5, 9.5), () => 2.6), closed: true, w: 1.5 }] },
  '11': { strokes: [{ pts: slotOutline(line(-9.5, 9.5), () => 1.7), closed: true, w: 1.6 }] },
  '03': { strokes: [{ pts: line(-11, 4.5), closed: false, w: 0.9 }, { pts: heartPts(7.5, 0, 3.6).map(([x, y]) => [7.5 + y, x - 7.5] as Pt), closed: true, w: 0.8 }] },
  '06': { strokes: [{ pts: line(-11, 3.5, 0), closed: false, w: 1.1 }, { pts: heartPts(7, 0, 5).map(([x, y]) => [7 + y, x - 7] as Pt), closed: true, w: 1 }] },
  '09': { strokes: [{ pts: slotOutline(bendC(-11, 11, t => 3.2 * Math.sin(Math.PI * t) * (1 - 0.3 * t) - 1.6), t => 1.0 + 0.5 * t), closed: true, w: 0.8 }] },
  '10': { strokes: [{ pts: slotOutline(bendC(-11, 10, t => -5 + 8 * (1 - (1 - t) ** 2.2)), t => 0.4 + 1.3 * t), closed: true, w: 0.8 }] },
};
function ribbon(pts: Pt[], closed: boolean, w: number): THREE.BufferGeometry { // thin flat stroke along a polyline, in metres
  const n = pts.length, pos: number[] = [], idx: number[] = [], m = 0.001, segs = closed ? n : n - 1;
  for (let i = 0; i < n; i++) {
    const a = pts[closed ? (i + n - 1) % n : Math.max(0, i - 1)], b = pts[closed ? (i + 1) % n : Math.min(n - 1, i + 1)], dx = b[0] - a[0], dy = b[1] - a[1], d = Math.hypot(dx, dy) || 1, nx = -dy / d * w / 2, ny = dx / d * w / 2;
    pos.push((pts[i][0] + nx) * m, (pts[i][1] + ny) * m, 0, (pts[i][0] - nx) * m, (pts[i][1] - ny) * m, 0);
  }
  for (let i = 0; i < segs; i++) { const a = i * 2, b = ((i + 1) % n) * 2; idx.push(a, a + 1, b, a + 1, b + 1, b); }
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.setIndex(idx); g.computeVertexNormals(); return g;
}
function holeGeometry(style: string): THREE.BufferGeometry {
  const d = HOLE_DESIGNS[style] ?? HOLE_DESIGNS['11'], parts = d.strokes.map(st => ribbon(st.pts, st.closed, st.w));
  const pos: number[] = [], idx: number[] = []; let off = 0;
  for (const g of parts) { const p = g.getAttribute('position'); for (let i = 0; i < p.count; i++) pos.push(p.getX(i), p.getY(i), p.getZ(i)); for (const i of g.getIndex()!.array) idx.push(i + off); off += p.count; }
  const out = new THREE.BufferGeometry(); out.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); out.setIndex(idx); out.computeVertexNormals(); return out;
}
let holeStyle = '';
function syncHoleStyle() { if (!holeMesh) return; const st = (trimState['hole'] ?? 'hole_11').replace('hole_', ''); if (st === holeStyle) return; holeStyle = st; holeMesh.geometry.dispose(); holeMesh.geometry = holeGeometry(st); }
function makeHoleMesh(): THREE.Mesh {
  const mat = new THREE.MeshStandardMaterial({ color: 0x1a1a1a, roughness: 0.6, side: THREE.DoubleSide, polygonOffset: true, polygonOffsetFactor: -4, polygonOffsetUnits: -4 }); mat.name = 'LapelHole';
  const m = new THREE.Mesh(holeGeometry('11'), mat); m.renderOrder = 2; holeStyle = '11'; return m;
}
function placeLapelHole() {
  let lm: THREE.Mesh | undefined = styleMeshes[lapelStyle];
  if (!lm) scene.traverse(o => { const m = o as THREE.Mesh; if (m.isMesh && (m.material as THREE.Material)?.name === 'Jacket_Lapel_Peak') lm = m; }); // peak.glb: lapel not in styleMeshes
  if (!lm) return;
  if (!holeMesh) { holeMesh = makeHoleMesh(); scene.add(holeMesh); applyTrims(scene); }
  lm.updateWorldMatrix(true, false);
  const hit = new THREE.Raycaster(new THREE.Vector3(HOLE_X, HOLE_Y, 1), new THREE.Vector3(0, 0, -1)).intersectObject(lm, false)[0];
  if (!hit || !hit.face) { holeMesh.visible = false; return; }
  const n = hit.face.normal.clone().transformDirection(lm.matrixWorld); if (n.z < 0) n.negate();
  const q = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 0, 1), n);
  const tilt = new THREE.Quaternion().setFromAxisAngle(n, HOLE_TILT);
  holeMesh.quaternion.copy(tilt.multiply(q));
  holeMesh.position.copy(hit.point).addScaledVector(n, 0.0007); holeMesh.visible = state.visible['jacket_body'] !== false;
}

const fabSrc = (f: Fabric) => (f.file.startsWith('blob:') ? f.file : import.meta.env.BASE_URL + 'fabrics/' + f.file.replace('fabrics/', ''));
let customN = 0;
const customBmp = new Map<string, ImageBitmap>(); const customPlain = new Map<string, boolean>();
function boxBlur(src: Float32Array, w: number, h: number, r: number): Float32Array { // 3 channels interleaved, 2 passes
  const tmp = new Float32Array(src.length), out = new Float32Array(src.length);
  for (let y = 0; y < h; y++) for (let c = 0; c < 3; c++) { let acc = 0, cnt = 0; for (let x = -r; x <= r; x++) { const xx = Math.min(w - 1, Math.max(0, x)); acc += src[(y * w + xx) * 3 + c]; cnt++; }
    for (let x = 0; x < w; x++) { tmp[(y * w + x) * 3 + c] = acc / cnt; const add = Math.min(w - 1, x + r + 1), rem = Math.max(0, x - r); acc += src[(y * w + add) * 3 + c] - src[(y * w + rem) * 3 + c]; } }
  for (let x = 0; x < w; x++) for (let c = 0; c < 3; c++) { let acc = 0, cnt = 0; for (let y = -r; y <= r; y++) { const yy = Math.min(h - 1, Math.max(0, y)); acc += tmp[(yy * w + x) * 3 + c]; cnt++; }
    for (let y = 0; y < h; y++) { out[(y * w + x) * 3 + c] = acc / cnt; const add = Math.min(h - 1, y + r + 1), rem = Math.max(0, y - r); acc += tmp[(add * w + x) * 3 + c] - tmp[(rem * w + x) * 3 + c]; } }
  return out;
}
async function makeTile(bmp: ImageBitmap, plain: boolean): Promise<{ file: string; thumb: string }> {
  const full = Math.min(bmp.width, bmp.height), side = full * 0.55, sx = (bmp.width - side) / 2, sy = (bmp.height - side) / 2; // centre crop keeps the weave and drops most folds
  const N = 512, base = document.createElement('canvas'); base.width = base.height = N; const bg = base.getContext('2d', { willReadFrequently: true })!; bg.drawImage(bmp, sx, sy, side, side, 0, 0, N, N);
  const d = bg.getImageData(0, 0, N, N), px = d.data, f = new Float32Array(N * N * 3); let mr = 0, mg = 0, mb = 0;
  for (let i = 0, j = 0; i < px.length; i += 4, j += 3) { f[j] = px[i]; f[j + 1] = px[i + 1]; f[j + 2] = px[i + 2]; mr += px[i]; mg += px[i + 1]; mb += px[i + 2]; }
  const n = N * N; mr /= n; mg /= n; mb /= n;
  if (plain) { // plain fabric: keep only the fine weave, give the whole tile one even colour (removes folds, shadows and colour drift)
    const bl = boxBlur(boxBlur(f, N, N, 16), N, N, 16);
    let ss = 0, nn = 0; for (let j = 0; j < f.length; j += 3) { const d = (f[j] + f[j + 1] + f[j + 2] - bl[j] - bl[j + 1] - bl[j + 2]) / 3; ss += d * d; nn++; }
    const lim = 1.6 * Math.sqrt(ss / nn); // clip crease highlights/shadows: keep only weave-sized ripples
    const cl = (v: number) => Math.max(-lim, Math.min(lim, v));
    for (let i = 0, j = 0; i < px.length; i += 4, j += 3) { px[i] = Math.max(0, Math.min(255, mr + cl(f[j] - bl[j]) * 1.1)); px[i + 1] = Math.max(0, Math.min(255, mg + cl(f[j + 1] - bl[j + 1]) * 1.1)); px[i + 2] = Math.max(0, Math.min(255, mb + cl(f[j + 2] - bl[j + 2]) * 1.1)); }
  } else { // patterned fabric: only even out the lighting (divide by a very soft blur)
    const bl = boxBlur(boxBlur(f, N, N, 120), N, N, 120), ml = 0.3 * mr + 0.59 * mg + 0.11 * mb;
    for (let i = 0, j = 0; i < px.length; i += 4, j += 3) { const lum = 0.3 * bl[j] + 0.59 * bl[j + 1] + 0.11 * bl[j + 2], k = Math.pow(ml / Math.max(lum, 20), 0.95); px[i] = Math.min(255, f[j] * k); px[i + 1] = Math.min(255, f[j + 1] * k); px[i + 2] = Math.min(255, f[j + 2] * k); }
  }
  bg.putImageData(d, 0, 0);
  let c: HTMLCanvasElement;
  if (plain) { // seamless without blending: pick the crop size whose left/right and top/bottom edges match best (a whole number of weave repeats)
    const D = bg.getImageData(0, 0, N, N).data, L = (x: number, y: number) => D[(y * N + x) * 4] + D[(y * N + x) * 4 + 1] + D[(y * N + x) * 4 + 2], X0 = 24; let best = 400, bestE = Infinity;
    for (let S = 280; S <= N - X0 - X0 - 3; S++) { let e = 0; for (let k = 0; k < 3; k++) for (let t = 0; t < 280; t += 2) { const a1 = L(X0 + k, X0 + t) - L(X0 + S + k, X0 + t), a2 = L(X0 + t, X0 + k) - L(X0 + t, X0 + S + k); e += a1 * a1 + a2 * a2; } if (e < bestE) { bestE = e; best = S; } }
    c = document.createElement('canvas'); c.width = c.height = best; c.getContext('2d')!.putImageData(bg.getImageData(X0, X0, best, best), 0, 0);
  } else { // patterned: mirrored 2x2 tile like the book fabrics
    c = document.createElement('canvas'); c.width = c.height = 1024; const g = c.getContext('2d')!, q = 512;
    for (const [ox, oy, fx, fy] of [[0, 0, 1, 1], [q, 0, -1, 1], [0, q, 1, -1], [q, q, -1, -1]] as const) { g.save(); g.translate(ox + (fx < 0 ? q : 0), oy + (fy < 0 ? q : 0)); g.scale(fx, fy); g.drawImage(base, 24, 24, N - 48, N - 48, 0, 0, q, q); g.restore(); }
  }
  const t = document.createElement('canvas'); t.width = t.height = 96; t.getContext('2d')!.drawImage(base, 0, 0, N, N, 0, 0, 96, 96);
  const blob = (cv: HTMLCanvasElement) => new Promise<string>(res => cv.toBlob(bb => res(URL.createObjectURL(bb!)), 'image/jpeg', 0.9));
  return { file: await blob(c), thumb: await blob(t) };
}
async function addCustomFabric(file: File): Promise<Fabric> {
  const bmp = await createImageBitmap(file); const id = 'custom_' + (++customN); customBmp.set(id, bmp); customPlain.set(id, true);
  const t = await makeTile(bmp, true);
  const f: Fabric = { id, code: null, name: 'Customer fabric (photo ' + customN + ')', supplier: 'Customer', book: '', page: 0, weightGsm: null, pattern: 'plain', family: 'custom', tone: 'dark', file: t.file, thumb: t.thumb, tileCm: 20, scaleVerified: false, review: ['customer-supplied'], source: 'Customer-supplied photo (no book code; pattern size set by hand)' };
  library.push(f); return f;
}
async function retileCustom(f: Fabric, plain: boolean) {
  customPlain.set(f.id, plain); const t = await makeTile(customBmp.get(f.id)!, plain); f.file = t.file; f.thumb = t.thumb; texCache.delete(f.id); normCache.delete(f.id);
  for (const [r, id] of Object.entries(state.fabrics)) if (id === f.id || (r === 'jacket_lapel' && id === 'match' && state.fabrics.jacket_body === f.id)) applyFabric(r, id);
  buildPanel();
}
function fabricTexture(f: Fabric): THREE.Texture {
  let t = texCache.get(f.id); if (t) return t;
  t = new THREE.TextureLoader().load(fabSrc(f), () => render());
  t.colorSpace = THREE.SRGBColorSpace; t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.anisotropy = Math.min(8, renderer.capabilities.getMaxAnisotropy());
  t.channel = 1; // TEXCOORD_1: near-metric, warp-aligned (V vertical)
  // Texture is a 2x2 mirrored tile covering 2x the cropped swatch; tileCm is the physical size of that whole tile.
  const r = UV_CM_PER_UNIT / f.tileCm; t.repeat.set(r, r);
  texCache.set(f.id, t); return t;
}
function fabricNormal(f: Fabric): THREE.Texture {
  let n = normCache.get(f.id); if (n) return n;
  const { tex, fill } = makeNormalTexture(1024);
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping; tex.channel = 1; tex.anisotropy = Math.min(8, renderer.capabilities.getMaxAnisotropy());
  const r = UV_CM_PER_UNIT / f.tileCm; tex.repeat.set(r, r);
  const img = new Image(); img.onload = () => { fill(img); render(); }; img.src = fabSrc(f);
  normCache.set(f.id, tex); return tex;
}

function applyFabric(regionId: string, fabricId: string) {
  const requested = fabricId;
  const m = regionMat(regionId);
  if (regionId === 'jacket_lapel' && fabricId === 'match') fabricId = state.fabrics.jacket_body;
  const fin = FINISHES.find(x => x.id === fabricId);
  if (fin) {
    m.map = null; m.color.set(fin.color); m.metalness = 0; m.roughness = fin.roughness; m.metalnessMap = null; m.roughnessMap = null;
    m.sheen = fin.sheen; m.sheenRoughness = 0.5; m.sheenColor.set(0x666677); m.envMapIntensity = 0.6;
    m.normalMap = null; m.bumpMap = fin.weave ? satinWeave() : null; m.bumpScale = 0.35;
  } else {
    const f = library.find(x => x.id === fabricId)!, t = fabricTexture(f);
    // Wool: photo as colour, derived normal map for yarn relief, fine fibre bump, high roughness + sheen for the surface fuzz.
    const fb = fibreTexture(); fb.repeat.set(UV_CM_PER_UNIT / FIBRE_CM, UV_CM_PER_UNIT / FIBRE_CM);
    m.map = t; m.color.set(0xffffff); m.metalnessMap = null; m.roughnessMap = null; m.metalness = 0; m.envMapIntensity = 1;
    m.normalMap = fabricNormal(f); m.normalScale.set(TUNING.relief, TUNING.relief);
    m.bumpMap = fb; m.bumpScale = TUNING.fibre; m.roughness = TUNING.rough;
    m.sheen = TUNING.fuzz; m.sheenRoughness = 0.8; m.sheenColor.set(0xb8b8c0);
  }
  m.needsUpdate = true;
  state.fabrics[regionId] = requested;
  if (regionId === 'jacket_body' && state.fabrics.jacket_lapel === 'match') applyFabric('jacket_lapel', 'match');
  render();
}
let weaveTex: THREE.Texture | null = null;
function satinWeave(): THREE.Texture { // fine diagonal twill so satin is not a flat glossy sheet; ~4 mm period on TEXCOORD_1
  if (weaveTex) return weaveTex;
  const c = document.createElement('canvas'); c.width = c.height = 64; const g = c.getContext('2d')!;
  g.fillStyle = '#808080'; g.fillRect(0, 0, 64, 64);
  for (let i = -64; i < 128; i += 4) { g.strokeStyle = i % 8 ? '#a0a0a0' : '#606060'; g.lineWidth = 1.5; g.beginPath(); g.moveTo(i, 0); g.lineTo(i + 64, 64); g.stroke(); }
  weaveTex = new THREE.CanvasTexture(c); weaveTex.wrapS = weaveTex.wrapT = THREE.RepeatWrapping; weaveTex.channel = 1; weaveTex.repeat.set(8, 8);
  return weaveTex;
}
function regionMat(regionId: string): THREE.MeshPhysicalMaterial {
  return regionId === 'jacket_lapel' ? lapelMat : baseMats[REGIONS.find(r => r.id === regionId)!.mesh];
}
const waistParts: THREE.Mesh[] = [], tieParts: THREE.Mesh[] = []; let tieBox = new THREE.Box3();
function splitMesh(bm: THREE.Mesh, rule: (c: THREE.Vector3) => number, n: number): (THREE.Mesh | null)[] {
  const g = bm.geometry, pos = g.getAttribute('position'), ia = g.getIndex()!.array, buckets: number[][] = Array.from({ length: n }, () => []);
  bm.updateWorldMatrix(true, false); const v = new THREE.Vector3(), cen = new THREE.Vector3();
  for (let t = 0; t < ia.length; t += 3) { // classify by world-space centroid (positions may be quantized + node-scaled)
    cen.set(0, 0, 0); for (let k = 0; k < 3; k++) cen.add(v.fromBufferAttribute(pos, ia[t + k]).applyMatrix4(bm.matrixWorld)); cen.multiplyScalar(1 / 3);
    buckets[rule(cen)].push(ia[t], ia[t + 1], ia[t + 2]);
  }
  g.setIndex(buckets[0]);
  return buckets.map((b, i) => {
    if (i === 0 || !b.length) return null;
    const g2 = new THREE.BufferGeometry(); for (const k of Object.keys(g.attributes)) g2.setAttribute(k, g.getAttribute(k)); g2.setIndex(b);
    const m = new THREE.Mesh(g2, bm.material); m.position.copy(bm.position); m.quaternion.copy(bm.quaternion); m.scale.copy(bm.scale); bm.parent!.add(m); return m;
  });
}
function setVisible(regionId: string, v: boolean) {
  if (regionId === 'waistcoat_body') waistParts.forEach(m => (m.visible = v));
  if (regionId === 'tie') tieParts.forEach(m => (m.visible = !v));
  meshes[REGIONS.find(r => r.id === regionId)!.mesh].visible = v; state.visible[regionId] = v; render();
}
function download(name: string, obj: unknown) {
  const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([JSON.stringify(obj, null, 2)], { type: 'application/json' }));
  a.download = name; a.click();
}
function currentConfig(): Config {
  return { schema: 'mwt.config', version: 1, model: MODEL_FILE.split('/').pop()!, created: new Date().toISOString(), fabrics: { ...state.fabrics }, visible: { ...state.visible }, lapel_style: lapelStyle, trims: { ...trimState } } as Config;
}
function exportConfig() { download('mw-tailleur-config.json', currentConfig()); }
function exportTicket() {
  const c = currentConfig(), lines: Ticket['lines'] = [];
  for (const r of REGIONS.filter(x => x.fabric)) {
    if (c.visible[r.id] === false) continue;
    let id = c.fabrics[r.id]; if (id === 'match') id = c.fabrics.jacket_body;
    const f = library.find(x => x.id === id), fin = FINISHES.find(x => x.id === id);
    lines.push({ region: r.id, label: r.label, fabricId: id, fabricName: f?.name ?? fin?.name ?? id, code: f?.code ?? null, supplier: f?.supplier ?? '', weightGsm: f?.weightGsm ?? null, source: f?.source ?? (fin ? 'finish preset (no book swatch)' : ''), finish: !!fin, needsReview: !!f && (!f.code || f.review.length > 0) });
  }
  const t: Ticket = { trims: trimTicket(), schema: 'mwt.ticket', version: 1, ticketId: 'MWT-' + Date.now().toString(36).toUpperCase(), created: c.created, model: c.model, lines,
    omitted: REGIONS.filter(r => r.toggle && c.visible[r.id] === false).map(r => r.id),
    notes: 'Lapel style: ' + (LAPEL_STYLES.find(x => x.id === lapelStyle)?.name ?? lapelStyle) + '. Preview-derived spec: fabrics and garment parts only. No measurements. Lines with needsReview have an unconfirmed label code. Colour on screen is approximate.' };
  download(t.ticketId + '-ticket.json', t);
}
function loadConfig(c: Config) {
  if (c?.schema !== 'mwt.config' || c.version !== 1) throw new Error('Not an MW Tailleur config v1');
  for (const [r, f] of Object.entries(c.fabrics)) {
    const ok = r === 'jacket_lapel' ? (f === 'match' || FINISHES.some(x => x.id === f) || library.some(x => x.id === f)) : library.some(x => x.id === f);
    if (REGIONS.some(x => x.id === r && x.fabric) && ok) applyFabric(r, f);
  }
  for (const [r, v] of Object.entries(c.visible)) if (REGIONS.some(x => x.id === r && x.toggle)) setVisible(r, !!v);
  if ((c as any).lapel_style) setLapelStyle(String((c as any).lapel_style));
  if ((c as any).trims) { Object.assign(trimState, (c as any).trims); applyTrims(scene); }
  buildPanel();
}
function render() { syncHoleStyle(); renderer.render(scene, camera); publishSummary(); }
let lastSummary = '';
function publishSummary() { // sends a plain-text summary of the choices to the hosting page (landing page iframe)
  try {
    if (window.parent === window || !library.length) return;
    const c = currentConfig(), lines: string[] = [];
    const nm = (id: string) => { const f = library.find(x => x.id === id), fin = FINISHES.find(x => x.id === id); return f ? (f.code ? f.code + ' ' : '') + f.name : fin?.name ?? id; };
    lines.push('Lapel: ' + (LAPEL_STYLES.find(x => x.id === lapelStyle)?.name ?? lapelStyle));
    for (const r of REGIONS.filter(x => x.fabric)) {
      if (c.visible[r.id] === false) continue;
      let id = c.fabrics[r.id]; if (id === 'match') id = c.fabrics.jacket_body;
      lines.push(r.label + ': ' + nm(id));
    }
    if (c.visible['tie'] !== false) lines.push('Tie: yes');
    for (const t of trimTicket()) lines.push(t.label + ': ' + t.name);
    const key = JSON.stringify(lines); if (key === lastSummary) return; lastSummary = key;
    window.parent.postMessage({ type: 'mwt.summary', lines }, '*');
  } catch { /* never break rendering */ }
}
function resize() { const w = view.clientWidth, h = view.clientHeight; renderer.setSize(w, h); camera.aspect = w / h; camera.updateProjectionMatrix(); render(); }
addEventListener('resize', resize); controls.addEventListener('change', render);
(function loop() { requestAnimationFrame(loop); controls.update(); })();

const thumbUrl = (f: Fabric) => (f.thumb.startsWith('blob:') ? `url(${f.thumb})` : `url(${import.meta.env.BASE_URL}${f.thumb})`);
const ADMIN = new URLSearchParams(location.search).get('admin') === '1';
function label(r: string) { const id = state.fabrics[r]; if (r === 'jacket_lapel' && id === 'match') return 'Match jacket'; const f = library.find(x => x.id === id); return f ? (f.code ? f.code + ' · ' : '') + f.name : FINISHES.find(x => x.id === id)?.name ?? id; }
function openCatalog(regionId: string) {
  const ov = document.createElement('div'); ov.style.cssText = 'position:fixed;inset:0;background:#000c;z-index:9;display:flex;justify-content:center;align-items:center';
  const box = document.createElement('div'); box.style.cssText = 'background:#1d1f25;width:min(900px,96vw);height:min(80vh,700px);border-radius:10px;display:flex;flex-direction:column;padding:12px;gap:8px';
  const bar = document.createElement('div'); bar.style.cssText = 'display:flex;gap:8px;flex-wrap:wrap;align-items:center';
  const q = document.createElement('input'); q.placeholder = 'Search code or name'; q.style.cssText = 'flex:1;min-width:140px;padding:6px;background:#111;color:#eee;border:1px solid #444;border-radius:4px';
  const sel = (opts: string[]) => { const e = document.createElement('select'); e.style.cssText = 'padding:6px;background:#111;color:#eee;border:1px solid #444;border-radius:4px'; e.innerHTML = opts.map(o => `<option>${o}</option>`).join(''); return e; };
  const pat = sel(['all patterns', 'plain', 'patterned']), fam = sel(['all colours', ...new Set(library.map(f => f.family))]), tone = sel(['all tones', 'dark', 'light']);
  const close = document.createElement('button'); close.textContent = '✕'; close.className = 'act'; close.style.margin = '0'; close.onclick = () => ov.remove();
  bar.append(q, pat, fam, tone); if (ADMIN) { const ex = document.createElement('button'); ex.textContent = 'Export manifest'; ex.className = 'act'; ex.style.margin = '0'; ex.onclick = () => download('manifest.json', { version: 2, fabrics: library }); bar.append(ex); }
  { const up = document.createElement('button'); up.textContent = 'Upload my fabric'; up.className = 'act'; up.style.margin = '0'; const inp = document.createElement('input'); inp.type = 'file'; inp.accept = 'image/*'; inp.style.display = 'none';
    up.onclick = () => inp.click(); inp.onchange = async () => { const fl = inp.files?.[0]; if (!fl) return; try { const f = await addCustomFabric(fl); applyFabric(regionId, f.id); ov.remove(); buildPanel(); } catch (e) { alert('Could not read that image'); } };
    bar.append(up, inp); }
  bar.append(close);
  const grid = document.createElement('div'); grid.style.cssText = 'overflow:auto;display:grid;grid-template-columns:repeat(auto-fill,minmax(' + (ADMIN ? 180 : 92) + 'px,1fr));gap:8px;align-content:start;flex:1';
  const draw = () => {
    grid.innerHTML = '';
    const term = q.value.toLowerCase();
    const pick = (id: string) => { applyFabric(regionId, id); ov.remove(); buildPanel(); };
    if (regionId === 'jacket_lapel') for (const o of [{ id: 'match', name: 'Match jacket', css: 'linear-gradient(135deg,#334 50%,#556 50%)' }, ...FINISHES.map(x => ({ id: x.id, name: x.name, css: '#' + x.color.toString(16).padStart(6, '0') }))]) {
      if (term && !o.name.toLowerCase().includes(term)) continue;
      const b = document.createElement('button'); b.title = o.name; b.style.cssText = `height:60px;border:1px solid #444;border-radius:6px;background:${o.css};color:#fff;font-size:10px;cursor:pointer`; b.textContent = o.name; b.onclick = () => pick(o.id); grid.appendChild(b);
    }
    for (const f of library) {
      if (term && !(f.name + ' ' + (f.code ?? '')).toLowerCase().includes(term)) continue;
      if (pat.value !== 'all patterns' && f.pattern !== pat.value) continue; if (fam.value !== 'all colours' && f.family !== fam.value) continue; if (tone.value !== 'all tones' && f.tone !== tone.value) continue;
      const c = document.createElement('div'); c.style.cssText = 'font-size:10px;color:#aaa;text-align:center';
      const b = document.createElement('button'); b.style.cssText = `width:100%;height:70px;border:2px solid ${f.review.length ? '#a55' : 'transparent'};border-radius:6px;background:${thumbUrl(f)};background-size:cover;cursor:pointer`; b.title = f.source + (f.review.length ? ' · review: ' + f.review.join(', ') : ''); b.onclick = () => pick(f.id);
      c.append(b, f.code ?? 'p' + f.page + ' (no code)');
      if (ADMIN) {
        const ci = document.createElement('input'); ci.value = f.code ?? ''; ci.placeholder = 'code 5838-0850'; ci.style.cssText = 'width:100%;box-sizing:border-box;margin-top:3px;background:#111;color:#eee;border:1px solid #444;font-size:11px';
        ci.onchange = () => { f.code = ci.value.trim() || null; f.review = f.review.filter(x => x !== 'no-label-code' && x !== 'duplicate-code'); };
        const ni = document.createElement('input'); ni.value = f.name; ni.style.cssText = ci.style.cssText; ni.onchange = () => { f.name = ni.value; };
        c.append(ci, ni);
      }
      grid.appendChild(c);
    }
  };
  for (const e of [q, pat, fam, tone]) e.oninput = draw; draw();
  box.append(bar, grid); ov.append(box); ov.onclick = e => { if (e.target === ov) ov.remove(); }; document.body.appendChild(ov);
}
function buildPanel() {
  panel.innerHTML = '<h1>MW Tailleur</h1><small>Order spec · fabric preview, not photorealistic' + (ADMIN ? ' · ADMIN' : '') + `</small><br><small>${library.length} fabrics in catalog</small>`;
      { const cur = new URLSearchParams(location.search).get('model') ?? 'shawl'; panel.insertAdjacentHTML('beforeend', '<h2>Suit model (preview)</h2>'); const mr = document.createElement('div'); mr.style.cssText = 'display:flex;gap:6px;margin-bottom:10px'; for (const [id, nm] of [['notch', 'Notch'], ['peak', 'Peak'], ['shawl', 'Shawl']]) { const b = document.createElement('button'); b.style.cssText = 'flex:1;padding:8px;border-radius:6px;cursor:pointer;width:auto;height:auto;background:' + (id === cur ? '#c9a45c' : '#111') + ';color:' + (id === cur ? '#111' : '#eee') + ';border:1px solid #444;font-weight:600'; b.textContent = nm; b.onclick = () => { const u = new URL(location.href); u.searchParams.set('model', id); location.href = u.toString(); }; mr.appendChild(b); } panel.appendChild(mr); }
  for (const r of REGIONS.filter(x => x.fabric)) {
    panel.insertAdjacentHTML('beforeend', `<h2>${r.label}</h2>`);
    const f = library.find(x => x.id === state.fabrics[r.id]);
    const b = document.createElement('button'); b.style.cssText = 'display:flex;align-items:center;gap:8px;width:100%;padding:6px;background:#111;color:#eee;border:1px solid #444;border-radius:6px;cursor:pointer;text-align:left';
    const sw = document.createElement('span'); sw.style.cssText = 'width:36px;height:36px;border-radius:4px;flex:none;background-size:cover;background:' + (f ? thumbUrl(f) : '#334'); sw.style.backgroundSize = 'cover';
    const tx = document.createElement('span'); tx.style.fontSize = '12px'; tx.textContent = label(r.id);
    b.append(sw, tx); b.onclick = () => openCatalog(r.id); panel.appendChild(b);
    if (f && f.id.startsWith('custom_')) { const w = document.createElement('div'); w.style.cssText = 'font-size:11px;color:#9a9aa3;margin:4px 0'; w.innerHTML = 'Pattern size <span>' + f.tileCm + '</span> cm'; const rg = document.createElement('input'); rg.type = 'range'; rg.min = '5'; rg.max = '80'; rg.step = '1'; rg.value = String(f.tileCm); rg.style.width = '100%';
      rg.oninput = () => { f.tileCm = +rg.value; (w.firstElementChild as HTMLElement).textContent = rg.value; const rp = UV_CM_PER_UNIT / f.tileCm; texCache.get(f.id)?.repeat.set(rp, rp); normCache.get(f.id)?.repeat.set(rp, rp); render(); }; w.appendChild(rg); panel.appendChild(w);
      const lb = document.createElement('label'); lb.style.cssText = 'font-size:12px;display:block;margin:2px 0 8px'; const cb = document.createElement('input'); cb.type = 'checkbox'; cb.checked = customPlain.get(f.id) ?? true; cb.onchange = () => retileCustom(f, cb.checked); lb.append(cb, ' Plain fabric: remove folds and shading'); panel.appendChild(lb); }
  }
  trimPanel(panel, scene, buildPanel, render);
  if (Object.keys(styleMeshes).length > 1) {

    panel.insertAdjacentHTML('beforeend', '<h2>Lapel style</h2>');
    const row = document.createElement('div'); row.className = 'sw'; row.style.gap = '6px';
    for (const st of LAPEL_STYLES.filter(x => styleMeshes[x.id])) { const sb = document.createElement('button'); sb.style.cssText = 'flex:1;padding:8px;border-radius:6px;cursor:pointer;width:auto;height:auto;background:' + (st.id === lapelStyle ? '#c9a45c' : '#111') + ';color:' + (st.id === lapelStyle ? '#111' : '#eee') + ';border:1px solid #444;font-weight:600'; sb.textContent = st.name; sb.onclick = () => { setLapelStyle(st.id); buildPanel(); }; row.appendChild(sb); }
    panel.appendChild(row);
  }
  panel.insertAdjacentHTML('beforeend', '<h2>Show</h2>');
  for (const r of REGIONS.filter(x => x.toggle)) {
    const l = document.createElement('label'); const c = document.createElement('input'); c.type = 'checkbox'; c.checked = state.visible[r.id] !== false;
    c.onchange = () => setVisible(r.id, c.checked); l.append(c, ' ' + r.label); panel.appendChild(l);
  }
  panel.insertAdjacentHTML('beforeend', '<h2>Cloth tuning (preview)</h2>');
  for (const [k, lab, mx] of [['relief', 'Weave relief', 3], ['fuzz', 'Surface fuzz', 1.5], ['rough', 'Roughness', 1], ['fibre', 'Fibre grain', 1]] as const) {
    const l = document.createElement('label'); l.style.cssText = 'display:flex;align-items:center;gap:6px;font-size:12px'; const r = document.createElement('input'); r.type = 'range'; r.min = '0'; r.max = String(mx); r.step = '0.05'; r.value = String(TUNING[k]); r.style.flex = '1';
    r.oninput = () => { TUNING[k] = +r.value; for (const [reg, fid] of Object.entries(state.fabrics)) if (reg !== 'jacket_lapel') applyFabric(reg, fid); };
    l.append(lab, r); panel.appendChild(l);
  }
  const b = document.createElement('button'); b.className = 'act'; b.textContent = 'Export config JSON'; b.onclick = exportConfig; panel.appendChild(b);
  const t = document.createElement('button'); t.className = 'act'; t.style.marginLeft = '6px'; t.textContent = 'Cutting ticket'; t.onclick = exportTicket; panel.appendChild(t);
  const lb = document.createElement('button'); lb.className = 'act'; lb.textContent = 'Load config…'; panel.appendChild(lb);
  const inp = document.createElement('input'); inp.type = 'file'; inp.accept = '.json,application/json'; inp.hidden = true; panel.appendChild(inp);
  const msg = document.createElement('div'); msg.style.cssText = 'margin-top:8px;font-size:12px;color:#c98'; panel.appendChild(msg);
  lb.onclick = () => inp.click();
  inp.onchange = async () => { try { loadConfig(JSON.parse(await inp.files![0].text())); } catch (e) { msg.textContent = String(e instanceof Error ? e.message : e); } };
}

async function init() {
  const base = import.meta.env.BASE_URL;
  library = (await (await fetch(base + 'fabrics/manifest.json')).json()).fabrics; await loadTrims();
  const loader = new GLTFLoader().setMeshoptDecoder(MeshoptDecoder);
  let gltf;
  if (import.meta.env.VITE_EMBED) { // single-host build: model shipped as base64 in a .js module (host refuses .glb)
    const MID = new URLSearchParams(location.search).get('model') ?? 'shawl'; const { B64 } = MID === 'notch' ? await import('./model-notch') : MID === 'peak' ? await import('./model-peak') : await import('./model-shawl'); const bin = atob(B64), u = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i);
    gltf = await loader.parseAsync(u.buffer, '');
  } else gltf = await loader.loadAsync(base + 'models/' + (new URLSearchParams(location.search).get('model') ?? 'shawl') + '.' + (import.meta.env.VITE_MODEL_EXT ?? 'glb'));
  scene.add(gltf.scene);
  const allMeshes: THREE.Mesh[] = [];
  gltf.scene.traverse(o => { if ((o as THREE.Mesh).isMesh) { (o as THREE.Mesh).castShadow = true; (o as THREE.Mesh).receiveShadow = true; allMeshes.push(o as THREE.Mesh); const mn = ((o as THREE.Mesh).material as THREE.Material).name; meshes[mn === 'Jacket_Wool' ? 'Jacket' : o.name] = o as THREE.Mesh; } });
  for (const r of REGIONS) {
    const mesh = meshes[r.mesh]; if (!mesh) { console.warn('missing mesh', r.mesh); continue; }
    if (r.fabric) {
      if (r.id === 'jacket_lapel') continue;
      const origName = (mesh.material as THREE.Material).name, m = (mesh.material as THREE.MeshPhysicalMaterial).clone(); mesh.material = m; baseMats[r.mesh] = m;
      for (const x of allMeshes) if (x !== mesh && (x.material as THREE.Material).name === origName) x.material = m; // e.g. trouser waistband primitive lives in the jacket mesh
      if (r.id === 'jacket_body') {
        // v3 GLB ships a real Jacket_Lapel primitive; with the older v2 GLB fall back to the runtime split.
        const lm = allMeshes.find(x => (x.material as THREE.Material).name === 'Jacket_Lapel');
        const pm = allMeshes.find(x => (x.material as THREE.Material).name === 'Jacket_Lapel_Peak'), sm0 = allMeshes.find(x => (x.material as THREE.Material).name === 'Jacket_Lapel_Shawl');
        // Each native lapel primitive shares ONE lapel material, so the "Lapel & collar" picker reaches it. Runtime split only when the file has no native lapel at all.
        let native = false;
        if (lm) { lapelMat = (lm.material as THREE.MeshPhysicalMaterial).clone(); lm.material = lapelMat; styleMeshes['notch'] = lm; native = true; }
        if (pm) { if (!native) lapelMat = (pm.material as THREE.MeshPhysicalMaterial).clone(); pm.material = lapelMat; styleMeshes['peak'] = pm; native = true; }
        if (sm0) { if (!native) lapelMat = m.clone(); sm0.material = lapelMat; styleMeshes['shawl'] = sm0; native = true; }
        if (native) mesh.userData.lapelNative = true;
        else { lapelMat = m.clone(); console.log('lapel tris (runtime split)', splitLapel(mesh, m, lapelMat)); }
        if (new URLSearchParams(location.search).get('debug') === 'lapel') { lapelMat.onBeforeCompile = sh => { sh.fragmentShader = sh.fragmentShader.replace('#include <dithering_fragment>', 'gl_FragColor.rgb = mix(gl_FragColor.rgb, vec3(1.,0.,0.), 0.7);\n#include <dithering_fragment>'); }; } }
    }
    if (r.toggle) state.visible[r.id] = true;
  }
  // Buttons/threads live in two shared meshes (Buttons, Trim). Split by world-space centroid so waistcoat buttons follow the waistcoat
  // and shirt buttons that sit under the tie are hidden while the tie is shown.
  tieBox = new THREE.Box3().setFromObject(meshes['Tie']);
  // Button column centres (y, z) measured on the v2 model: waistcoat buttons vs shirt buttons share x~0 and nearly the same z, so use nearest centre.
  const WAIST: [number, number][] = [[1.223, 0.135], [1.151, 0.14], [1.081, 0.144], [1.011, 0.144], [0.944, 0.146]];
  const SHIRT: [number, number][] = [[1.422, 0.058], [1.353, 0.09], [1.261, 0.122], [1.164, 0.131], [1.067, 0.135], [0.983, 0.135], [0.967, 0.131], [0.876, 0.121]];
  const near = (a: [number, number][], c: THREE.Vector3) => Math.min(...a.map(([y, z]) => Math.hypot(c.y - y, c.z - z)));
  const inWaist = (c: THREE.Vector3) => Math.abs(c.x) < 0.07 && c.z > 0.1 && c.z < 0.17 && c.y > 0.9 && c.y < 1.3 && near(WAIST, c) < near(SHIRT, c);
  const underTie = (c: THREE.Vector3) => near(SHIRT, c) < near(WAIST, c) && Math.abs(c.x) < 0.04 && c.y > tieBox.min.y - 0.02 && c.y < tieBox.max.y + 0.02 && c.y > 0.9;
  for (const [name, rule] of [['Buttons', (c: THREE.Vector3) => (inWaist(c) ? 1 : 0)], ['Trim', (c: THREE.Vector3) => (inWaist(c) ? 1 : underTie(c) ? 2 : 0)]] as const) {
    const parts = splitMesh(meshes[name], rule, 3); if (parts[1]) waistParts.push(parts[1]); if (parts[2]) tieParts.push(parts[2]);
  }
  // Shirt tails run down inside the trousers and show through the open fly: hide the shirt below the waistband.
  const tails = splitMesh(meshes['Shirt'], c => (c.y < 0.985 ? 1 : 0), 2)[1]; if (tails) tails.visible = false;
  tieParts.forEach(m => (m.visible = false)); // tie shown by default -> shirt buttons under it stay hidden
  const box = new THREE.Box3().setFromObject(gltf.scene), size = box.getSize(new THREE.Vector3()), ctr = box.getCenter(new THREE.Vector3());
  const d = Math.max(size.y / 2 / Math.tan(THREE.MathUtils.degToRad(15)), 1) * 1.15;
  camera.position.set(ctr.x, ctr.y, ctr.z + d); controls.target.copy(ctr); controls.minDistance = d * 0.3; controls.maxDistance = d * 2.5;
  camera.near = d / 100; camera.far = d * 10; camera.updateProjectionMatrix();
  gltf.scene.traverse(o => { if ((o as THREE.Mesh).isMesh) { o.castShadow = true; o.receiveShadow = true; } }); // includes meshes created by splitMesh
  ground.position.y = box.min.y - 0.005; key.target.position.copy(ctr); scene.add(key.target);
  const sc = key.shadow.camera as THREE.OrthographicCamera, ext = Math.max(size.x, size.y) * 0.65; sc.left = -ext; sc.right = ext; sc.top = ext; sc.bottom = -ext; sc.near = 0.1; sc.far = 12; sc.updateProjectionMatrix();
  // defaults: jacket + waistcoat + trousers in the first fabric (navy plain)
  const dflt = (library.find(x => x.id === 'p45') ?? library[0]).id;
  state.fabrics = { jacket_body: dflt, jacket_lapel: 'match', waistcoat_body: dflt, trousers_body: dflt };
  setLapelStyle(Object.keys(styleMeshes)[0] ?? 'notch');
  placeLapelHole();
  buildPanel(); resize();
  for (const [r, f] of Object.entries(state.fabrics)) applyFabric(r, f);
  applyTrims(scene);
  const dbg = { size: size.toArray().map(v => +v.toFixed(3)), meshes: Object.keys(meshes) };
  status.textContent = 'ready ' + JSON.stringify(dbg); (window as any).__mwt = { scene, styleMeshes, setTrim: (s: string, i: string) => { setTrim(s, i, scene); render(); }, setLapelStyle, meshes, loadConfig, exportTicket, currentConfig, applyFabric, setVisible, state, camera, controls, render };
}
init().catch(e => { status.textContent = 'ERROR ' + e; console.error(e); });
