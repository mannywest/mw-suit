# Base jacket + swappable lapels — plan (Manny, 15 Nov 2026)

Idea: stop repairing a whole jacket for each lapel. Build ONE clean base jacket with a standard neckline,
and build each lapel style as a separate part that plugs into it (like a picture frame: same wall and hook, swap the picture).

## What the base jacket needs
- One fixed, clean neck opening: smooth edge round the neck and down the front, no collar or lapel material left on it.
- Fixed seam points that every lapel uses: back of neck, both shoulder points, both gorge points (where collar meets lapel).
- Everything else locked: sleeves, body, pockets, buttons, weave direction (TEXCOORD_1) never change when a lapel changes.
- A clean chest and shoulder surface: no tears, flaps, shards, duplicate-vertex seams in the neck/shoulder area.

## What each lapel part is
- Self-contained mesh (one per style), built from a few numbers: width, gorge height, peak angle/length, button point.
- Lies on the chest without poking through or floating; weave pattern runs on across the seam.
- Checked alone with the same tests as now: holes (gaps.py / gapview.py), shirt poke-through, symmetry, validator 0 errors.

## Which lapels fit the ONE standard single-breasted base
- Notch (also tuxedo/satin), Peak (also tuxedo/satin).
- Width/height changes: slim or wide, high or low gorge, bigger or smaller peak (number changes only).
- One, two or three buttons (moves button point and roll line only).
- Step and cutaway lapels (close cousins of notch).
- Shawl: PROBABLY, with a small tweak. No gorge seam; collar + lapel are one piece; the roll line must run unbroken from the button to the back of the neck. Needs a reference photo first.

## Which need their OWN base
- Double-breasted (any lapel): wider front panel, overlap, extra buttons, different front edge.
- Mandarin / Nehru / band collar and collarless jackets: different neckline.
- Other special cuts (Norfolk, safari, military): change front, shoulders or closure.
Rule of thumb: collar/lapel shape only = reuse the base. Front panel, closure or neckline changes = new base.

## Order of work (one step per session, Manny checks each)
1. Step 3: notch lapel, mirror the better side above the top button, fix wing points.
2. Step 4: collar/shoulder clean-up (jagged side and top edges, shoulder-corner shards and flaps) + close the small tear under the back collar edge
   (white shirt patch, x 42-56 mm, y 1445-1452 mm, z -63..-81 mm; body stops a few mm short of the collar's lower edge).
3. Build the clean base jacket (no lapels, no collar, standard neck opening, defined seam points).
4. Turn the peak lapel into the first plug-in part; then notch; then the shawl as the first NEW style (needs reference photo).
5. Later, if wanted: double-breasted as a second base model.
Alternative for truly new designs: Marvelous Designer / CLO3D (sew flat pattern pieces on a 3D body, export GLB), by Manny or a freelancer.

## State of the base today (15 Nov 2026, checked on peak_step2d_shoulders.glb)
NOT ready as a base. Lapels and collar are separate pieces but overlap and share vertices with the body; the body still has
open edges (366 segments, about 2.7 m, in the neck/shoulder zone above y 1.38 m), the small tear under the back collar edge,
old flaps/shards at the shoulder corners, and a black line across the neck opening in the top view.
