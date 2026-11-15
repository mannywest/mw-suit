# MW Tailleur Configurator – Stage 1
Vite + TypeScript + Three.js. Loads the v2 GLB, per-garment fabric picker (jacket / waistcoat / trousers), waistcoat + tie toggles, config JSON export.

    npm install
    npm run dev        # http://localhost:5173
    npm run build      # static site in dist/

- `public/fabrics/manifest.json` – fabric library (swatches cropped from Den Vi Stylish100 5822, lighting flattened, baked as 2x2 mirrored tiles).
- `src/config.ts` – region registry (mesh -> region id) and UV scale (3.2 cm per TEXCOORD_1 unit).
- Add a fabric: drop a 1024px seamless/mirrored jpg in `public/fabrics/`, add an entry with `tileCm`.
Known limits: swatch colour is approximate (dark photos); mirrored tiles show symmetry on patterned weaves; no lapel/collar split yet (Stage 3); buttons mesh is 44% of tris (LOD later); v2 GLB untouched.

## Stage 2 – lapel & collar slot
`src/lapel.ts` splits the jacket at load time (no GLB change) into body + lapel/collar groups using a geometric rule on triangle centroids (tune the `LAPEL` constants). Lapel options: match jacket, any library fabric, black/navy satin (`FINISHES` in config.ts). Open `?debug=lapel` to see the selection in red. Config export now includes `jacket_lapel`.
Limit: edge is jagged (~1 cm, follows triangle size) and there is no true roll line; a clean seam needs a Blender face selection + GLB re-export.

## Order spec
- **Export config JSON** (`mwt.config` v1) / **Load config…** restores fabrics, lapel slot and toggles; invalid files show an error.
- **Cutting ticket** (`mwt.ticket` v1): one line per visible fabric region with fabric name and book page, plus omitted parts. No measurements and no label codes yet (add `code` to manifest entries when read from the book labels).

## Fabric catalog (replaces the 5 hand-made swatches)
- `python3 tools/ingest.py book.pdf --supplier "Den Vi" --book "Stylish100 5822"` crops every page, flattens lighting, writes mirrored 1024px tiles + 96px thumbs + `public/fabrics/manifest.json` (v2). Needs poppler, tesseract, pillow, numpy, opencv-python. Re-run per book (use a different --out or merge manifests).
- Label codes are read by OCR (47 of 63 pages for Den Vi 5838 book; rest flagged `no-label-code`). Duplicates flagged `duplicate-code`. Flagged tiles have a red border in the catalog.
- In the app: click a garment's fabric button to open the catalog (search code/name, filter pattern/colour/tone).
- **Admin mode:** open `?admin=1`. The catalog gains editable code and name fields per fabric and an "Export manifest" button; replace `public/fabrics/manifest.json` with the export to save corrections.
- Cutting ticket now carries code, supplier, weight and a `needsReview` flag.

## Lapel seam (v3 model)
`node tools/split-lapel.mjs MW_Tailleur_suit_repaired_v2.glb out.glb` refines the jacket triangles along the lapel boundary (4 levels, crack-free) and writes the lapel as its own primitive with material `Jacket_Lapel`. Shipped as `public/models/MW_Tailleur_suit_v3.glb` (jacket 37k -> 69k tris; the original v2 file is not included and was not modified). The app uses the native primitive when present and falls back to the runtime split for v2. The boundary is still the geometric rule in the script (not a hand-drawn seam), now smooth; edit `L` constants to adjust. Needs `npm i` (devDependency @gltf-transform).

## Model size
`node tools/optimize.mjs in.glb out.glb` meshopt-compresses the model (18 MB -> 7.5 MB; positions/normals quantized, UVs untouched). `public/models/MW_Tailleur_suit_v3.glb` is the optimized file. For hosts that refuse .glb: generate `src/model-embed.ts` (`export const B64 = "<base64>"`) and build with `VITE_EMBED=1`.

## Stage 6 (14 Nov 2026) – state at handoff
Post-Stage-5 fixes: button/shirt toggles, matte satin, island-based lapel+collar (tools/split-lapel.mjs: excludes front-edge strips, welt bars, shoulder slivers; adds back collar via COLLAR_Y/X/Z), waistband on trouser material, shirt tails hidden. Rebuild: node tools/split-lapel.mjs <v2.glb> /tmp/t.glb; node tools/optimize.mjs /tmp/t.glb public/models/MW_Tailleur_suit_v3.glb; npx vite build. Open issues are listed in the Google Drive handoff doc.

---
# Handoff for a website builder (15 Nov 2026)

## Run / build
    npm install
    npm run dev      # local
    npm run build    # static site in dist/ (upload anywhere, or embed in an iframe)
Models load from `public/models/{shawl,notch,peak}.glb`. Choose with `?model=notch|peak|shawl` (default shawl). Do NOT use `VITE_EMBED=1` (that is only a preview-host workaround that needs generated `src/model-*.ts`).

## What the app does
- Three jacket models (notch, peak, shawl lapel), waistcoat/tie toggles, fabric catalogue, lapel fabric/satin, trims (button colour and finish, buttonhole thread), customer fabric upload (photo -> texture), export/load config JSON, cutting ticket JSON (`mwt.ticket`).
- Hook for the website: `exportTicket()` / `currentConfig()` in `src/main.ts` produce the order JSON. Suggested integration: iframe the built app and `postMessage` the ticket to the page on a "Request this suit" button.

## Missing from this repo (must be supplied)
- **Fabric images**: `public/fabrics/manifest.json` is only an empty stub. The 126 fabric tiles (Den Vi Stylish100 book) are not in git. Rebuild with `tools/ingest.py book.pdf ...` from the supplier PDF, or ask Manny for the files.
- Trim thumbnails/catalogue are in `public/trims/`.

## Known flaws (be honest with Manny)
- Suit mesh: neck rim bits, shards near the closure, rough shoulder corners, jagged back collar edge (see repo root notes and `HANDOFF_2026-11-15.md`).
- Shawl lapel uses a wool material until black satin is chosen. Button colours are approximate. Velvet not included.
- Customer fabric upload: photos of bent/draped cloth can show diagonal fold stripes (fix in progress in `makeTile` in `src/main.ts`, plain-fabric mode).
- No price, checkout, or order submission yet.
Never edit the original GLBs in the repo root; the app models in `public/models/` are compressed (meshopt + quantize) copies.
