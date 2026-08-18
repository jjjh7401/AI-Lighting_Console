// PresetPoolPopup — one preset pool's contents, fetched ON DEMAND when the
// operator opens a pool category card from the dashboard's 프리셋 section.
//
// Why a popup + on-demand fetch instead of listing every preset on the dash
// (user direction, 2026-08-15): a showfile carries many pools × many presets,
// and the dash snapshot's bounded drilldown budget can never (and should
// never) pre-walk them all. Opening ONE pool costs exactly two gate-audited
// queries (`GET /api/presets/{no}` — pool listing + pool contents), rides no
// shared budget, and is always CURRENT: a preset stored seconds ago is
// visible on the next open.
//
// Read-only by structure: tiles are info cells (PoolTile pressable=false
// shape); nothing in this component can reach a console-firing path.
//
// The view is hook-free (this project has no DOM/jsdom harness — see
// protocol.ts's own header); the container hook lives in App.tsx. Parsers and
// fetch wrappers below are plain functions, unit-testable without a DOM.
import { apiUrl } from "../launchContext";

/** One preset slot as the wire carries it: the console's REAL number + name.
 * `color` (optional `#rrggbb`) is the app's OWN palette colour for presets it
 * stored itself — the console exposes no preset colour (Appearance/Color
 * props answered "not readable", live-probed 2026-08-16), so a manual
 * preset's colour is unknown and the API honestly omits the field rather
 * than inventing one. `colors` (optional, 2+ hexes) is the same rule for the
 * app's own multi-colour PHASER presets: the step colours it stored from its
 * palette, drawn as the split circle the console shows on a ⋯ preset. */
export interface PresetEntry {
  no: number;
  name: string;
  color?: string;
  colors?: string[];
}

export interface PresetPoolContents {
  pool: PresetEntry;
  presets: PresetEntry[];
  /** The responder said the pool listing was cut short. */
  truncated: boolean;
  /** The responder's own childCount, when it gave one. */
  total: number | null;
}

/** The popup's whole lifecycle as data — the container owns transitions. */
export type PresetPopupState =
  | { phase: "loading"; pool: PresetEntry }
  | { phase: "error"; pool: PresetEntry; message: string }
  | { phase: "ready"; contents: PresetPoolContents };

// -- parsing (pure — unit-testable without a DOM) ------------------------------

function entryOf(raw: unknown): PresetEntry | null {
  if (typeof raw !== "object" || raw === null) return null;
  const no = (raw as Record<string, unknown>).no;
  const name = (raw as Record<string, unknown>).name;
  const color = (raw as Record<string, unknown>).color;
  const colors = (raw as Record<string, unknown>).colors;
  // A name-only entry (the responder could not number the slot) is dropped:
  // a tile without a REAL console number would invite addressing by position,
  // the exact trap the real-`no` rule exists to prevent.
  if (typeof no !== "number") return null;
  const entry: PresetEntry = { no, name: typeof name === "string" ? name : "" };
  // Only a well-formed hex colour rides through — anything else is treated
  // as absent (never a CSS injection channel).
  if (typeof color === "string" && /^#[0-9a-fA-F]{6}$/.test(color)) entry.color = color;
  // A phaser's step colours ride only when EVERY entry is a well-formed hex
  // and there are at least 2 (a 1-step list is not a phaser; a bad entry
  // drops the whole field — never a partial or injected gradient).
  if (
    Array.isArray(colors) &&
    colors.length >= 2 &&
    colors.every((c) => typeof c === "string" && /^#[0-9a-fA-F]{6}$/.test(c))
  ) {
    entry.colors = colors as string[];
  }
  return entry;
}

/** Parse GET /api/presets/{no}'s body; null = malformed (treated as error). */
export function parsePresetPoolResponse(text: string): PresetPoolContents | null {
  let data: unknown;
  try {
    data = JSON.parse(text);
  } catch {
    return null;
  }
  if (typeof data !== "object" || data === null) return null;
  const record = data as Record<string, unknown>;
  const pool = entryOf(record.pool);
  if (pool === null || !Array.isArray(record.presets)) return null;
  const presets = record.presets
    .map(entryOf)
    .filter((entry): entry is PresetEntry => entry !== null);
  return {
    pool,
    presets,
    truncated: record.truncated === true,
    total: typeof record.total === "number" ? record.total : null,
  };
}

/** The error message shown for a non-OK response, from the API's detail. */
export function presetPoolErrorMessage(status: number, text: string): string {
  try {
    const detail = (JSON.parse(text) as Record<string, unknown>).detail;
    if (typeof detail === "string" && detail.length > 0) return detail;
  } catch {
    // fall through to the status line
  }
  return `프리셋 풀을 읽지 못했습니다 (HTTP ${status})`;
}

// -- fetch wrapper (thin — call + parse, no React) ------------------------------

export async function fetchPresetPool(poolNo: number): Promise<PresetPopupState> {
  const pool = { no: poolNo, name: "" };
  try {
    const response = await fetch(apiUrl(`/api/presets/${poolNo}`));
    const text = await response.text();
    if (!response.ok) {
      return { phase: "error", pool, message: presetPoolErrorMessage(response.status, text) };
    }
    const contents = parsePresetPoolResponse(text);
    if (contents === null) {
      return { phase: "error", pool, message: "서버 응답을 해석하지 못했습니다" };
    }
    return { phase: "ready", contents };
  } catch (error) {
    return { phase: "error", pool, message: `서버에 연결하지 못했습니다: ${String(error)}` };
  }
}

// -- hook-free view (directly testable) ----------------------------------------

/** The header line: pool number/name plus an honest count when known.
 * A truncated read with no responder total claim must NOT state the partial
 * window length as THE count — `N개 이상` keeps the header consistent with
 * the "일부만 표시됨" badge (2026-08-17 review). */
export function presetPopupTitle(state: PresetPopupState): string {
  if (state.phase === "ready") {
    const { pool, presets, total, truncated } = state.contents;
    const count = total ?? presets.length;
    const suffix = truncated && total === null ? `${count}개 이상` : `${count}개`;
    return `프리셋 풀 ${pool.no} · ${pool.name || "—"} — ${suffix}`;
  }
  const name = state.pool.name ? ` · ${state.pool.name}` : "";
  return `프리셋 풀 ${state.pool.no}${name}`;
}

export interface PresetPoolPopupProps {
  state: PresetPopupState;
  onClose: () => void;
  onRefresh: () => void;
}

/** The console's ⋯ split circle: N step colours as N equal conic segments.
 * `from 270deg` puts a 2-step split on the horizontal (top/bottom halves,
 * matching the onPC pool tile); 3 steps become thirds (the Rainbow pie).
 * Inputs are already hex-validated by `entryOf` — never a CSS channel. */
export function phaserGradient(colors: string[]): string {
  const n = colors.length;
  const stops = colors.map((c, i) => `${c} ${(i * 100) / n}% ${((i + 1) * 100) / n}%`);
  return `conic-gradient(from 270deg, ${stops.join(", ")})`;
}

export function PresetPoolPopup({ state, onClose, onRefresh }: PresetPoolPopupProps) {
  return (
    <div className="preset-popup-overlay" onClick={onClose} role="presentation">
      <div
        className="preset-popup"
        role="dialog"
        aria-label={presetPopupTitle(state)}
        onClick={(event) => event.stopPropagation()}
      >
        <header className="preset-popup-header">
          <span className="preset-popup-title">{presetPopupTitle(state)}</span>
          <div className="preset-popup-actions">
            <button className="preset-popup-refresh" onClick={onRefresh} aria-label="새로고침">
              ⟳
            </button>
            <button className="preset-popup-close" onClick={onClose} aria-label="닫기">
              ✕
            </button>
          </div>
        </header>
        {state.phase === "ready" && state.contents.truncated && (
          <div className="preset-popup-badge">일부만 표시됨 — 콘솔이 목록을 잘랐습니다</div>
        )}
        <div className="preset-popup-body">
          {state.phase === "loading" && <div className="preset-popup-empty">콘솔에서 읽는 중…</div>}
          {state.phase === "error" && <div className="preset-popup-error">{state.message}</div>}
          {state.phase === "ready" &&
            (state.contents.presets.length === 0 ? (
              <div className="preset-popup-empty">이 풀은 비어 있습니다</div>
            ) : (
              <div className="preset-popup-grid">
                {state.contents.presets.map((preset) => (
                  <div key={preset.no} className="pool-tile pool-tile-info preset-popup-tile">
                    <span className="pool-tile-no">{preset.no}</span>
                    {preset.colors ? (
                      <span
                        className="preset-popup-swatch"
                        role="img"
                        style={{ background: phaserGradient(preset.colors) }}
                        aria-label={`색 ${preset.colors.join("/")}`}
                      />
                    ) : preset.color ? (
                      <span
                        className="preset-popup-swatch"
                        role="img"
                        style={{ background: preset.color }}
                        aria-label={`색 ${preset.color}`}
                      />
                    ) : null}
                    <span className="pool-tile-name">{preset.name || "—"}</span>
                  </div>
                ))}
              </div>
            ))}
        </div>
      </div>
    </div>
  );
}
