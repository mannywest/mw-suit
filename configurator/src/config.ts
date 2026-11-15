// Stage 1 contracts. Region IDs follow the handoff; only mesh-level regions exist in the v2 GLB.
export const MODEL_FILE = 'models/MW_Tailleur_suit_v3.glb'; // v3 = v2 + refined jacket with native Jacket_Lapel primitive (tools/split-lapel.mjs)
export const UV_CM_PER_UNIT = 3.2; // measured on TEXCOORD_1 of the v2 GLB (approx, +-~10%)

export interface Region { id: string; mesh: string; label: string; fabric: boolean; toggle?: boolean }
export const REGIONS: Region[] = [
  { id: 'jacket_body',    mesh: 'Jacket',    label: 'Jacket',    fabric: true },
  { id: 'jacket_lapel',   mesh: 'Jacket',    label: 'Lapel & collar', fabric: true },
  { id: 'waistcoat_body', mesh: 'Waistcoat', label: 'Waistcoat', fabric: true, toggle: true },
  { id: 'trousers_body',  mesh: 'Trousers',  label: 'Trousers',  fabric: true },
  { id: 'tie',            mesh: 'Tie',       label: 'Tie',       fabric: false, toggle: true },
];

export interface Fabric {
  id: string; code: string | null; name: string; supplier: string; book: string; page: number; weightGsm: number | null;
  pattern: 'plain' | 'patterned'; family: string; tone: string; file: string; thumb: string; tileCm: number; scaleVerified: boolean;
  review: string[]; source: string;
}
export interface Config {
  lapel_style?: string; // 'notch' | 'peak' (optional; added Stage 8)
  schema: 'mwt.config'; version: 1; model: string; created: string;
  fabrics: Record<string, string>; visible: Record<string, boolean>; trims?: Record<string, string>;
}

// Finishes for the lapel slot besides 'match' (= same as jacket) and library fabrics.
export interface Finish { id: string; name: string; color: number; roughness: number; sheen: number; weave: boolean }
export const FINISHES: Finish[] = [
  { id: 'satin-black', name: 'Black satin', color: 0x15151a, roughness: 0.55, sheen: 1, weave: true },
  { id: 'satin-navy',  name: 'Navy satin',  color: 0x1a2145, roughness: 0.55, sheen: 1, weave: true },
];

export interface TicketLine { region: string; label: string; fabricId: string; fabricName: string; code: string | null; supplier: string; weightGsm: number | null; source: string; finish: boolean; needsReview: boolean }
export interface Ticket { trims?: unknown[]; schema: 'mwt.ticket'; version: 1; ticketId: string; created: string; model: string; lines: TicketLine[]; omitted: string[]; notes: string }
