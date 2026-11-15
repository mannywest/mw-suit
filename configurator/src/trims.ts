// Trims catalogue (buttons, button thread, buttonholes, felt, satin) read from public/trims/trims.json.
// Source: Buttons_Felt_Satin_Thread_Milanese_Velvet_2023.pdf. Colours on screen are sampled from the PDF photos (approximate).
import * as THREE from 'three';
import { FINISHES } from './config';

export interface TrimItem { id: string; kind: 'button' | 'thread' | 'felt' | 'satin'; code: string; name: string; color: string; thumb: string; finish?: string }
export interface TrimSlot { id: string; label: string; kind: TrimItem['kind'] | 'hole'; onModel: boolean; note: string }
export const SLOTS: TrimSlot[] = [
  { id: 'button', label: 'Buttons', kind: 'button', onModel: true, note: 'Shown on the suit (colour approximate)' },
  { id: 'thread', label: 'Buttonhole thread', kind: 'thread', onModel: true, note: 'Shown on the suit (also used on the order spec)' },
  { id: 'hole', label: 'Milanese buttonhole style', kind: 'hole', onModel: false, note: 'Order spec only (not drawn on the model)' },
  { id: 'felt', label: 'Under-collar felt', kind: 'felt', onModel: false, note: 'Order spec only (hidden under the collar)' },
];
let items: TrimItem[] = []; let holes: string[] = [];
export const trimState: Record<string, string> = {};
const BASE = import.meta.env.BASE_URL;
export async function loadTrims() {
  try { const j = await (await fetch(BASE + 'trims/trims.json')).json(); items = j.items; holes = j.buttonholes;
    for (const s of items.filter(x => x.kind === 'satin')) if (!FINISHES.some(f => f.id === s.id)) FINISHES.push({ id: s.id, name: s.name, color: parseInt(s.color, 16), roughness: 0.5, sheen: 1, weave: true });
  } catch (e) { console.warn('trims not loaded', e); }
}
export const trimById = (id: string) => items.find(x => x.id === id);
const HOLE = (n: string) => 'hole_' + n;

export function applyTrims(scene: THREE.Object3D) {
  const b = trimById(trimState['button']), t = trimById(trimState['thread']);
  scene.traverse(o => {
    const m = (o as THREE.Mesh).isMesh ? ((o as THREE.Mesh).material as THREE.MeshPhysicalMaterial) : null; if (!m) return;
    if (m.name === 'Trim' && b) {
      m.map = null; m.color.set(parseInt(b.color, 16)); const f = b.finish ?? 'horn';
      m.metalness = f === 'metal' ? 0.9 : 0; m.roughness = f === 'metal' ? 0.3 : f === 'gloss' ? 0.2 : f === 'shell' ? 0.25 : 0.4; m.needsUpdate = true;
    }
    if (m.name === 'Buttons' && t) { m.map = null; m.color.set(parseInt(t.color, 16)); m.needsUpdate = true; }
  });
}
export function trimLabel(slot: TrimSlot): string {
  const id = trimState[slot.id]; if (!id) return 'Not chosen';
  if (slot.kind === 'hole') return 'Style ' + id.replace('hole_', '');
  const i = trimById(id); return i ? i.code : id;
}
export function trimTicket() {
  return SLOTS.filter(s => trimState[s.id]).map(s => { const id = trimState[s.id]; const i = trimById(id);
    return { slot: s.id, label: s.label, code: s.kind === 'hole' ? id.replace('hole_', '') : i?.code ?? id, name: s.kind === 'hole' ? 'Milanese buttonhole style ' + id.replace('hole_', '') : i?.name ?? id, shownOnModel: s.onModel, source: 'Buttons_Felt_Satin_Thread_Milanese_Velvet_2023.pdf' }; });
}
export function setTrim(slot: string, id: string, scene: THREE.Object3D) { trimState[slot] = id; applyTrims(scene); }

export function openTrimPicker(slot: TrimSlot, scene: THREE.Object3D, done: () => void, render: () => void) {
  const ov = document.createElement('div'); ov.style.cssText = 'position:fixed;inset:0;background:#000c;z-index:9;display:flex;justify-content:center;align-items:center';
  const box = document.createElement('div'); box.style.cssText = 'background:#1d1f25;width:min(900px,96vw);height:min(80vh,700px);border-radius:10px;display:flex;flex-direction:column;padding:12px;gap:8px';
  const bar = document.createElement('div'); bar.style.cssText = 'display:flex;gap:8px;align-items:center;color:#ddd'; bar.textContent = slot.label + ' — ' + slot.note;
  const close = document.createElement('button'); close.textContent = '✕'; close.className = 'act'; close.style.cssText = 'margin:0 0 0 auto'; close.onclick = () => ov.remove(); bar.append(close);
  const grid = document.createElement('div'); grid.style.cssText = 'overflow:auto;display:grid;grid-template-columns:repeat(auto-fill,minmax(84px,1fr));gap:8px;align-content:start;flex:1';
  const pick = (id: string) => { setTrim(slot.id, id, scene); render(); ov.remove(); done(); };
  if (slot.kind === 'hole') {
    const img = document.createElement('img'); img.src = BASE + 'trims/buttonholes.jpg'; img.style.cssText = 'grid-column:1/-1;max-height:260px;object-fit:contain'; grid.appendChild(img);
    for (const n of holes) { const b = document.createElement('button'); b.className = 'act'; b.style.margin = '0'; b.textContent = 'Style ' + n; b.onclick = () => pick(HOLE(n)); grid.appendChild(b); }
  } else {
    const list = items.filter(x => x.kind === slot.kind);
    const g = (label: string, f: (i: TrimItem) => boolean) => { const sub = list.filter(f); if (!sub.length) return; const h = document.createElement('div'); h.style.cssText = 'grid-column:1/-1;color:#9a9aa3;font-size:11px;margin-top:6px'; h.textContent = label; grid.appendChild(h); for (const i of sub) grid.appendChild(cell(i)); };
    const cell = (i: TrimItem) => { const c = document.createElement('div'); c.style.cssText = 'font-size:10px;color:#aaa;text-align:center';
      const b = document.createElement('button'); b.title = i.name; b.style.cssText = `width:100%;height:70px;border:2px solid ${trimState[slot.id] === i.id ? '#c9a45c' : 'transparent'};border-radius:6px;background:url(${BASE}${i.thumb}) center/cover;cursor:pointer`; b.onclick = () => pick(i.id);
      c.append(b, i.code); return c; };
    if (slot.kind === 'button') { g('Horn-look (U7, U28)', i => i.code.startsWith('U')); g('Enamel colours (SYG)', i => i.code.startsWith('SYG')); g('Other (horn, shell, metal)', i => !i.code.startsWith('U') && !i.code.startsWith('SYG')); }
    else g('', () => true);
  }
  box.append(bar, grid); ov.append(box); ov.onclick = e => { if (e.target === ov) ov.remove(); }; document.body.appendChild(ov);
}
export function trimPanel(panel: HTMLElement, scene: THREE.Object3D, rebuild: () => void, render: () => void) {
  if (!items.length) return;
  panel.insertAdjacentHTML('beforeend', '<h2>Trims (from your 2023 trims book)</h2>');
  for (const s of SLOTS) {
    const b = document.createElement('button'); b.style.cssText = 'display:flex;align-items:center;gap:8px;width:100%;padding:6px;background:#111;color:#eee;border:1px solid #444;border-radius:6px;cursor:pointer;text-align:left;margin-bottom:6px';
    const i = trimById(trimState[s.id]); const sw = document.createElement('span'); sw.style.cssText = 'width:30px;height:30px;border-radius:4px;flex:none;background:' + (i ? `url(${BASE}${i.thumb}) center/cover` : '#334');
    const tx = document.createElement('span'); tx.style.fontSize = '12px'; tx.innerHTML = s.label + '<br><small style="color:#8a8a93">' + trimLabel(s) + (s.onModel ? '' : ' · spec only') + '</small>';
    b.append(sw, tx); b.onclick = () => openTrimPicker(s, scene, rebuild, render); panel.appendChild(b);
  }
}
