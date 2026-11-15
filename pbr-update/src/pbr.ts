import * as THREE from 'three';

// Runtime PBR derivation from a flat swatch photo (no new assets needed).
// A photo only holds colour. This builds a normal map from its high-frequency luminance (yarn/weave relief)
// and a procedural fibre noise used as a bump map, so light has something to react to.

export const TUNING = { relief: 1.0, fuzz: 0.6, rough: 0.9, fibre: 0.25 };
export const FIBRE_CM = 8; // physical size of the fibre noise tile

function boxBlurWrap(src: Float32Array, w: number, h: number, r: number): Float32Array {
  const tmp = new Float32Array(w * h), out = new Float32Array(w * h), n = 2 * r + 1;
  for (let y = 0; y < h; y++) {
    let s = 0; const row = y * w;
    for (let k = -r; k <= r; k++) s += src[row + ((k + w) % w)];
    for (let x = 0; x < w; x++) { tmp[row + x] = s / n; s += src[row + ((x + r + 1) % w)] - src[row + ((x - r + w) % w)]; }
  }
  for (let x = 0; x < w; x++) {
    let s = 0;
    for (let k = -r; k <= r; k++) s += tmp[((k + h) % h) * w + x];
    for (let y = 0; y < h; y++) { out[y * w + x] = s / n; s += tmp[((y + r + 1) % h) * w + x] - tmp[((y - r + h) % h) * w + x]; }
  }
  return out;
}

/** Returns a stable CanvasTexture (flat normal until the swatch has loaded, then filled in). */
export function makeNormalTexture(size = 1024): { tex: THREE.CanvasTexture; fill: (img: HTMLImageElement) => void } {
  const c = document.createElement('canvas'); c.width = c.height = size;
  const g = c.getContext('2d')!; g.fillStyle = 'rgb(128,128,255)'; g.fillRect(0, 0, size, size);
  const tex = new THREE.CanvasTexture(c);
  const fill = (img: HTMLImageElement) => {
    const w = size, h = size;
    const tc = document.createElement('canvas'); tc.width = w; tc.height = h;
    const tg = tc.getContext('2d', { willReadFrequently: true })!; tg.drawImage(img, 0, 0, w, h);
    const px = tg.getImageData(0, 0, w, h).data, L = new Float32Array(w * h);
    for (let i = 0; i < w * h; i++) L[i] = (0.299 * px[i * 4] + 0.587 * px[i * 4 + 1] + 0.114 * px[i * 4 + 2]) / 255;
    // High-pass: remove the large-scale pattern (stripes, jacquard motifs, baked lighting), keep yarn-scale relief.
    const base = boxBlurWrap(L, w, h, 7), hp = new Float32Array(w * h);
    for (let i = 0; i < hp.length; i++) hp[i] = L[i] - base[i];
    const sm = boxBlurWrap(hp, w, h, 1); // soften JPEG noise
    let sd = 0; for (let i = 0; i < sm.length; i++) sd += sm[i] * sm[i]; sd = Math.sqrt(sd / sm.length) || 1e-3;
    const gain = Math.min(6, 0.05 / sd); // normalise so dark and light fabrics get comparable relief; cap to avoid amplifying noise
    const out = tg.createImageData(w, h), K = 3.0;
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      const xl = (x - 1 + w) % w, xr = (x + 1) % w, yu = (y - 1 + h) % h, yd = (y + 1) % h;
      const dx = (sm[y * w + xr] - sm[y * w + xl]) * gain * K, dy = (sm[yd * w + x] - sm[yu * w + x]) * gain * K;
      // OpenGL-style normal (green up). Texture v runs opposite to canvas rows, so n.y = +dh/drow.
      let nx = -dx, ny = dy, nz = 1; const l = Math.hypot(nx, ny, nz); nx /= l; ny /= l; nz /= l;
      const o = (y * w + x) * 4; out.data[o] = (nx * 0.5 + 0.5) * 255; out.data[o + 1] = (ny * 0.5 + 0.5) * 255; out.data[o + 2] = (nz * 0.5 + 0.5) * 255; out.data[o + 3] = 255;
    }
    g.putImageData(out, 0, 0); tex.needsUpdate = true;
  };
  return { tex, fill };
}

let fibre: THREE.Texture | null = null;
/** Seamless fine fibre noise for the bump slot (breaks up the "smooth plastic" look when close up). */
export function fibreTexture(): THREE.Texture {
  if (fibre) return fibre;
  const n = 256, c = document.createElement('canvas'); c.width = c.height = n; const g = c.getContext('2d')!;
  const f = new Float32Array(n * n); let s = 12345; const rnd = () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
  for (let i = 0; i < f.length; i++) f[i] = rnd();
  const b = boxBlurWrap(f, n, n, 1), d = g.createImageData(n, n);
  for (let i = 0; i < b.length; i++) { const v = Math.max(0, Math.min(255, 128 + (b[i] - 0.5) * 900)); d.data[i * 4] = d.data[i * 4 + 1] = d.data[i * 4 + 2] = v; d.data[i * 4 + 3] = 255; }
  g.putImageData(d, 0, 0);
  fibre = new THREE.CanvasTexture(c); fibre.wrapS = fibre.wrapT = THREE.RepeatWrapping; fibre.channel = 1;
  return fibre;
}
