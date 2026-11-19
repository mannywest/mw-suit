import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { MeshoptDecoder } from 'three/examples/jsm/libs/meshopt_decoder.module.js';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';
import { contact, packages, families } from './data.js';

const MODELS = 'configurator/models/';
const CLOTHS = [
  { id: 'midnight', name: 'Midnight', hex: '#10131f' },
  { id: 'navy', name: 'Navy', hex: '#1d2f5a' },
  { id: 'charcoal', name: 'Charcoal', hex: '#3b3e44' },
  { id: 'burgundy', name: 'Burgundy', hex: '#5b1a27' },
  { id: 'green', name: 'Bottle green', hex: '#17402f' },
  { id: 'stone', name: 'Stone', hex: '#b7aa92' },
  { id: 'ivory', name: 'Ivory', hex: '#e6dfcd' },
];
const KEYS = {
  hero:    { az: 0,   ty: 0.95, d: 4.0, sx: -0.2 },
  cloth:   { az: -36, ty: 1.12, d: 3.1, sx: 0.27 },
  lapel:   { az: 26,  ty: 1.3,  d: 2.15, sx: -0.2 },
  process: { az: 152, ty: 1.05, d: 3.7, sx: 0.2 },
  builder: { az: 152, ty: 1.05, d: 3.7, sx: 0.2 },
};
const state = { cloth: CLOTHS[0], lapel: 'shawl', satin: true };
const $ = (s) => document.querySelector(s);
const ease = (t) => t * t * (3 - 2 * t);
const lerp = (a, b, t) => a + (b - a) * t;

/* ---------- renderer ---------- */
const stage = $('#stage');
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;
stage.appendChild(renderer.domElement);
const scene = new THREE.Scene();
const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
scene.environmentIntensity = 0.55;
const camera = new THREE.PerspectiveCamera(28, 1, 0.1, 50);
const key = new THREE.SpotLight(0xffe2b8, 90, 0, 0.5, 0.7, 1.6); key.position.set(2.2, 3.4, 3.2); scene.add(key, key.target);
const rim = new THREE.DirectionalLight(0x8fb4ff, 1.6); rim.position.set(-3, 2.2, -3); scene.add(rim);
const fill = new THREE.DirectionalLight(0xffffff, 0.25); fill.position.set(-2, 1, 3); scene.add(fill);
const root = new THREE.Group(); scene.add(root);

/* ---------- models ---------- */
const loader = new GLTFLoader().setMeshoptDecoder(MeshoptDecoder);
const loaded = {}; // lapel -> gltf scene
const loadModel = (l) => loaded[l] ? Promise.resolve(loaded[l]) : new Promise((res, rej) => {
  loader.load(MODELS + l + '.' + (import.meta.env.VITE_MODEL_EXT ?? 'glb'), (g) => {
    g.scene.traverse((o) => { if (o.isMesh) { o.frustumCulled = false; o.material = o.material.clone(); o.material.userData.map0 = o.material.map; o.material.userData.orig = { t: o.material.transparent, o: o.material.opacity }; } });
    g.scene.visible = false; root.add(g.scene); loaded[l] = g.scene; applyLook(g.scene); res(g.scene);
  }, undefined, rej);
});
const CLOTH_RE = /^(Jacket_Wool|Trousers_Wool|Waistcoat_Wool)/;
function applyLook(sc) {
  const c = new THREE.Color(state.cloth.hex);
  sc.traverse((o) => {
    if (!o.isMesh) return; const m = o.material, n = m.name || '';
    if (CLOTH_RE.test(n)) { m.color.copy(c); }
    else if (/^Jacket_Lapel/.test(n)) {
      if (state.satin) { // same recipe as the configurator's matte satin (config.ts FINISHES / main.ts)
        m.map = null; m.metalnessMap = null; m.roughnessMap = null; m.metalness = 0; m.color.set('#0d0d11'); m.roughness = 0.66;
        m.sheen = 1; m.sheenRoughness = 0.5; m.sheenColor.set(0x4a4a58); m.envMapIntensity = 0.4; m.specularIntensity = 0.45; m.clearcoat = 0;
      } else { m.map = m.userData.map0 ?? null; m.color.copy(c); m.roughness = 0.85; m.envMapIntensity = 1; m.sheen = 0; }
      m.needsUpdate = true;
    }
  });
}
const applyAll = () => Object.values(loaded).forEach(applyLook);

/* ---------- particle reveal built from the suit's own vertices ---------- */
let pts = null; const U = { uT: { value: 0 }, uA: { value: 1 }, uTime: { value: 0 }, uPR: { value: renderer.getPixelRatio() } };
function buildParticles(sc) {
  const out = []; sc.updateMatrixWorld(true); const v = new THREE.Vector3();
  sc.traverse((o) => { if (o.isMesh && /^(Jacket|Trousers|Waistcoat|Shirt|Tie)$/.test(o.name)) {
    const p = o.geometry.attributes.position, n = p.count, step = Math.max(1, Math.floor(n / 9000));
    for (let i = 0; i < n; i += step) { v.fromBufferAttribute(p, i).applyMatrix4(o.matrixWorld); out.push(v.x, v.y, v.z); } } });
  const N = out.length / 3, pos = new Float32Array(out), seed = new Float32Array(N); for (let i = 0; i < N; i++) seed[i] = Math.random();
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.BufferAttribute(pos, 3)); g.setAttribute('aSeed', new THREE.BufferAttribute(seed, 1));
  const m = new THREE.ShaderMaterial({ uniforms: U, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    vertexShader: `uniform float uT,uTime,uPR;attribute float aSeed;varying float vS;
      void main(){vec3 t=position;float a=aSeed*6.2831+aSeed*40.;vec3 s=t+vec3(cos(a),sin(a*1.7)*.6,sin(a))*(1.2+aSeed*3.2);
      float k=clamp(uT*1.35-aSeed*.35,0.,1.);k=k*k*(3.-2.*k);vec3 p=mix(s,t,k);
      p+=vec3(sin(uTime*.6+aSeed*30.),cos(uTime*.5+aSeed*17.),sin(uTime*.4+aSeed*9.))*.006*(1.-k*.6);
      vec4 mv=modelViewMatrix*vec4(p,1.);gl_Position=projectionMatrix*mv;vS=aSeed;gl_PointSize=(1.6+aSeed*1.8)*uPR*(2.6/-mv.z);}`,
    fragmentShader: `uniform float uA;varying float vS;void main(){float d=length(gl_PointCoord-.5);if(d>.5)discard;float f=smoothstep(.5,.0,d);
      gl_FragColor=vec4(mix(vec3(.95,.86,.66),vec3(.8,.9,1.),vS),f*uA);}` });
  pts = new THREE.Points(g, m); pts.frustumCulled = false; scene.add(pts);
}
const setOpacity = (sc, a) => sc.traverse((o) => { if (o.isMesh) { const m = o.material; m.transparent = a < 0.999 ? true : m.userData.orig.t; m.opacity = a < 0.999 ? a : m.userData.orig.o; m.depthWrite = a > 0.6; } });

/* ---------- scroll choreography ---------- */
const chaps = [...document.querySelectorAll('[data-k]')].filter((e) => KEYS[e.dataset.k]);
let cur = { ...KEYS.hero }, mx = 0.5, paused = false;
const mobile = () => innerWidth < 900;
function target() {
  const y = scrollY + innerHeight * 0.5, cs = chaps.map((e) => e.offsetTop + e.offsetHeight / 2);
  let i = 0; while (i < cs.length - 1 && y > cs[i + 1]) i++;
  const a = KEYS[chaps[i].dataset.k], b = KEYS[chaps[Math.min(i + 1, chaps.length - 1)].dataset.k];
  const t = i >= cs.length - 1 ? 0 : ease(Math.min(1, Math.max(0, (y - cs[i]) / (cs[i + 1] - cs[i]))));
  return { az: lerp(a.az, b.az, t), ty: lerp(a.ty, b.ty, t), d: lerp(a.d, b.d, t), sx: lerp(a.sx, b.sx, t) };
}
function resize() { const w = stage.clientWidth, h = stage.clientHeight; renderer.setSize(w, h); camera.aspect = w / h; camera.updateProjectionMatrix(); }
addEventListener('resize', resize); resize();
addEventListener('pointermove', (e) => { mx = e.clientX / innerWidth; }, { passive: true });

let t0 = performance.now(), revealAt = null, ready = false;
function frame(now) {
  requestAnimationFrame(frame); if (paused) return;
  const t = (now - t0) / 1000; U.uTime.value = t;
  const T = target(), k = 1 - Math.pow(0.001, 1 / 60 * 1.6);
  for (const p of ['az', 'ty', 'd', 'sx']) cur[p] = lerp(cur[p], T[p], k);
  const az = THREE.MathUtils.degToRad(cur.az + (mx - 0.5) * 10 + Math.sin(t * 0.3) * 2.5);
  const h = cur.ty + (cur.d > 3 ? 0.18 : 0.05) * (1 - Math.min(1, scrollY / 600));
  const D = cur.d * (mobile() ? 1.3 : 1); camera.position.set(Math.sin(az) * D, h, Math.cos(az) * D); camera.lookAt(0, cur.ty, 0);
  const W = stage.clientWidth, H = stage.clientHeight; camera.setViewOffset(W, H, (mobile() ? 0 : cur.sx) * W, mobile() ? H * 0.2 : 0, W, H);
  if (ready) {
    if (revealAt == null) revealAt = t;
    const r = t - revealAt; U.uT.value = Math.min(1, r / 3.2);
    const m = ease(Math.min(1, Math.max(0, (r - 1.8) / 2.2))), sc = loaded[state.lapel];
    if (sc) { sc.visible = m > 0.001; setOpacity(sc, m); }
    U.uA.value = lerp(1, 0.07, ease(Math.min(1, Math.max(0, (r - 2.6) / 2))));
    $('#hint').style.opacity = scrollY > 80 ? 0 : (r > 3 ? 1 : 0);
  }
  renderer.render(scene, camera);
}

/* ---------- UI ---------- */
function look() { return `${state.lapel} lapel, ${state.cloth.name.toLowerCase()}${state.satin ? ', satin lapel' : ''}`; }
const wa = (txt) => `https://wa.me/${contact.whatsapp}?text=${encodeURIComponent(txt)}`;
function syncLook() { $('#sendLook').href = wa(`Hello MW Tailleur, I'd like to talk about a jacket: ${look()}. Could we arrange a consultation?`); }
const cl = $('#cloths');
CLOTHS.forEach((c) => { const b = document.createElement('button'); b.className = 'sw' + (c.id === state.cloth.id ? ' on' : ''); b.style.background = c.hex; b.title = c.name; b.innerHTML = `<span>${c.name}</span>`;
  b.onclick = () => { state.cloth = c; cl.querySelectorAll('.sw').forEach((x) => x.classList.toggle('on', x === b)); applyAll(); syncLook(); }; cl.appendChild(b); });
$('#satinChip').onclick = (e) => { state.satin = !state.satin; e.currentTarget.classList.toggle('on', state.satin); applyAll(); syncLook(); };
$('#lapels').onclick = async (e) => { const b = e.target.closest('button'); if (!b) return; const l = b.dataset.l; if (l === state.lapel) return;
  document.querySelectorAll('#lapels button').forEach((x) => x.classList.toggle('on', x === b));
  const sc = await loadModel(l); Object.entries(loaded).forEach(([k, s]) => { s.visible = k === l; }); setOpacity(sc, 1); state.lapel = l; syncLook(); };
syncLook();

// packages
const sel = new Set(); let fam = 'all';
const tabs = $('#tabs'), grid = $('#grid'), bar = $('#bar');
const money = (p) => `${p.from ? 'From ' : ''}£${p.amount.toLocaleString('en-GB')}${p.perPerson ? '<small>per person</small>' : ''}`;
function drawPk() {
  tabs.innerHTML = ''; [{ id: 'all', name: 'All' }, ...families].forEach((f) => { const b = document.createElement('button'); b.textContent = f.name; b.className = f.id === fam ? 'on' : ''; b.onclick = () => { fam = f.id; drawPk(); }; tabs.appendChild(b); });
  grid.innerHTML = ''; packages.filter((p) => fam === 'all' || p.family === fam).forEach((p) => { const c = document.createElement('button'); c.className = 'card' + (sel.has(p.id) ? ' on' : '');
    c.innerHTML = `<span class="tag">${p.tag}</span><span class="nm">${p.name}</span><span class="pr">${money(p)}</span><span class="pick">${sel.has(p.id) ? 'Selected' : 'Tap to select'}</span>`;
    c.onclick = () => { sel.has(p.id) ? sel.delete(p.id) : sel.add(p.id); drawPk(); drawBar(); }; grid.appendChild(c); });
}
function drawBar() { bar.classList.toggle('show', sel.size > 0); if (!sel.size) return; const list = packages.filter((p) => sel.has(p.id));
  $('#barTxt').textContent = `${sel.size} package${sel.size > 1 ? 's' : ''} selected`;
  $('#barSend').href = wa(`Hello MW Tailleur, I'm interested in:\n${list.map((p) => `- ${p.name} (${p.from ? 'from ' : ''}£${p.amount}${p.perPerson ? ' pp' : ''})`).join('\n')}\nCould we arrange a consultation?`); }
drawPk();
$('#waLink').href = `https://wa.me/${contact.whatsapp}`; $('#mailLink').href = `mailto:${contact.email}`; $('#mailLink').textContent = contact.email;

// builder iframe + pause 3D when it is on screen
const frameEl = $('#cfg');
new IntersectionObserver((es) => { if (es[0].isIntersecting && !frameEl.src) frameEl.src = frameEl.dataset.src; }, { rootMargin: '700px' }).observe(frameEl);
new IntersectionObserver((es) => { paused = es[0].intersectionRatio > 0.55; stage.style.opacity = paused ? 0 : 1; }, { threshold: [0, 0.55, 1] }).observe($('#builder'));

/* ---------- boot ---------- */
requestAnimationFrame(frame);
loadModel('shawl').then((sc) => { sc.visible = false; buildParticles(sc); ready = true; $('#status').style.opacity = 0; })
  .catch((e) => { $('#status').textContent = 'Could not load the 3D model'; console.error(e); });
window.__mw = { state, applyAll, loaded, camera, cur };
