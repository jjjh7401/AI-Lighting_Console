// PoolSection — one onPC-style pool window (SPEC-COPILOT-DASHUI-001 M4,
// design.md §2/§3, REQ-DASHUI-004/008/010/018). Renders a section header
// (label + an honest health/flag badge) and a numbered-tile grid, IN WIRE
// ORDER — `section.items` is never sorted or reflowed (AC-DASHUI-010,
// protocol.ts's own DashState doc: "nothing sorts it").
//
// Per-item pressability is a CALLER predicate (`isPressable`), never decided
// here — see PoolTile.tsx's header for why the structural non-fireability
// boundary lives one layer up, at DashBoard's section-name routing.
//
// No internal hooks by design — this project has no DOM/jsdom test harness
// (see protocol.ts's own header); PoolSection is called directly as a plain
// function in PoolSection.test.tsx.
import { type DashItem, type DashSection } from "../protocol";
import { PoolTile } from "./PoolTile";

const HEALTH_LABEL: Record<string, string> = {
  path_not_resolved: "경로 미해결 — 이 쇼파일에 없는 경로",
  console_unreachable: "콘솔 무응답",
};

/**
 * The section's health/flag badge text, or null when the section is fully
 * healthy with nothing to disclose.
 *
 * `path_not_resolved` and `console_unreachable` stay textually distinct
 * (design.md §3 "신선도" row, REQ-DASHUI-008) — never collapsed into one
 * generic "error" string. When the section itself resolved OK, the three
 * completeness flags (`truncated`/`drilldown_capped`/`contents_unavailable`)
 * are surfaced honestly instead of silently capped away.
 */
export function sectionHealthLabel(section: DashSection): string | null {
  if (section.status !== "ok") {
    return HEALTH_LABEL[section.status] ?? section.status;
  }
  const flags: string[] = [];
  if (section.truncated) flags.push("일부만 표시됨");
  if (section.drilldown_capped) flags.push("드릴다운 예산 소진");
  if (section.contents_unavailable) flags.push("내용물 확인 불가");
  return flags.length > 0 ? flags.join(" · ") : null;
}

/** onPC-style SQUARE cell size bounds (px), stepped by the −/+ controls. */
export const POOL_TILE_MIN_SIZE = 64;
export const POOL_TILE_MAX_SIZE = 200;
export const POOL_TILE_DEFAULT_SIZE = 104;
export const POOL_TILE_SIZE_STEP = 16;

/** Clamp one cell size into the legal range. */
export function clampPoolTileSize(size: number): number {
  return Math.min(POOL_TILE_MAX_SIZE, Math.max(POOL_TILE_MIN_SIZE, Math.round(size)));
}

/** onPC-style pool-WINDOW area bounds (px) for the corner drag-resize. */
export const POOL_AREA_MIN_WIDTH = 240;
export const POOL_AREA_MAX_WIDTH = 1800;
export const POOL_AREA_MIN_HEIGHT = 150;
export const POOL_AREA_MAX_HEIGHT = 1000;
export const POOL_AREA_DEFAULT: PoolArea = { width: 520, height: 260 };

export interface PoolArea {
  width: number;
  height: number;
}

/** Clamp one dragged window area into the legal range. */
export function clampPoolArea(area: PoolArea): PoolArea {
  return {
    width: Math.min(POOL_AREA_MAX_WIDTH, Math.max(POOL_AREA_MIN_WIDTH, Math.round(area.width))),
    height: Math.min(
      POOL_AREA_MAX_HEIGHT,
      Math.max(POOL_AREA_MIN_HEIGHT, Math.round(area.height)),
    ),
  };
}

export interface PoolSectionProps {
  section: DashSection;
  label: string;
  /** Per-item pressability, decided by the caller — never inferred here. */
  isPressable: (item: DashItem) => boolean;
  /** The console verb for press-able tiles in this section (e.g. "Go+", "Macro"). */
  verb?: string;
  /**
   * The verb shown while a tile is running (e.g. "Off" for executors).
   * Omitted for one-shot sections (macros — no Off affordance, design.md §4).
   */
  runningVerb?: string;
  /** Per-item running lookup (M5). Defaults to not-running when omitted. */
  isRunning?: (item: DashItem) => boolean;
  onPress?: (item: DashItem) => void;
  /** SQUARE cell edge in px (M6-UX v3). Session-volatile, owned by App. */
  tileSize?: number;
  /** When provided, the header renders −/+ controls stepping the cell size. */
  onTileSizeChange?: (next: number) => void;
  /** This pool WINDOW's on-screen area (M6-UX v3). Owned by App. */
  area?: PoolArea;
  /**
   * When provided, an onPC-style bottom-right corner handle starts a 2D
   * area drag (the drag session itself — document-level move/up listeners —
   * lives in App; this hook-free component only surfaces the start event).
   */
  onAreaResizeStart?: (event: { clientX: number; clientY: number }) => void;
}

export function PoolSection({
  section,
  label,
  isPressable,
  verb,
  runningVerb,
  isRunning,
  onPress,
  tileSize = POOL_TILE_DEFAULT_SIZE,
  onTileSizeChange,
  area = POOL_AREA_DEFAULT,
  onAreaResizeStart,
}: PoolSectionProps) {
  const health = sectionHealthLabel(section);
  const size = clampPoolTileSize(tileSize);
  const { width, height } = clampPoolArea(area);
  return (
    <section
      className={`pool-section pool-section-${section.name}`}
      aria-label={label}
      style={{ width: `${width}px`, height: `${height}px` }}
    >
      <header className="pool-section-header">
        <span className="pool-section-label">{label}</span>
        {health ? <span className="pool-section-health">{health}</span> : null}
        {onTileSizeChange ? (
          <span className="pool-size-control">
            <button
              type="button"
              className="pool-size-step"
              aria-label="셀 작게"
              onClick={() => onTileSizeChange(clampPoolTileSize(size - POOL_TILE_SIZE_STEP))}
            >
              −
            </button>
            <button
              type="button"
              className="pool-size-step"
              aria-label="셀 크게"
              onClick={() => onTileSizeChange(clampPoolTileSize(size + POOL_TILE_SIZE_STEP))}
            >
              +
            </button>
          </span>
        ) : null}
      </header>
      {section.items.length === 0 ? (
        <div className="pool-section-empty">비어 있음</div>
      ) : (
        <div
          className="pool-section-grid"
          style={{ gridTemplateColumns: `repeat(auto-fill, ${size}px)` }}
        >
          {section.items.map((item) => {
            const pressable = isPressable(item);
            const running = pressable && (isRunning?.(item) ?? false);
            return (
              <PoolTile
                key={item.no}
                item={item}
                pressable={pressable}
                verb={running && runningVerb ? runningVerb : verb}
                running={running}
                onPress={onPress}
              />
            );
          })}
        </div>
      )}
      {onAreaResizeStart ? (
        <span
          className="pool-area-resize"
          aria-label="영역 크기 조절 — 모서리를 드래그"
          onMouseDown={(event: {
            clientX: number;
            clientY: number;
            preventDefault?: () => void;
          }) => {
            event.preventDefault?.();
            onAreaResizeStart(event);
          }}
        >
          ◢
        </span>
      ) : null}
    </section>
  );
}
