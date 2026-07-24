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

/** onPC-style tile scale for one section (M6-UX, user direction). */
export type PoolTileSize = "s" | "m" | "l";

const SIZE_ORDER: PoolTileSize[] = ["s", "m", "l"];

/** One step smaller/larger, clamped at both ends. */
export function stepPoolSize(size: PoolTileSize, direction: -1 | 1): PoolTileSize {
  const index = SIZE_ORDER.indexOf(size) + direction;
  return SIZE_ORDER[Math.min(SIZE_ORDER.length - 1, Math.max(0, index))];
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
  /** This section's tile scale (M6-UX). Session-volatile, owned by App. */
  size?: PoolTileSize;
  /** When provided, the header renders −/+ controls that step the size. */
  onSizeChange?: (next: PoolTileSize) => void;
}

export function PoolSection({
  section,
  label,
  isPressable,
  verb,
  runningVerb,
  isRunning,
  onPress,
  size = "m",
  onSizeChange,
}: PoolSectionProps) {
  const health = sectionHealthLabel(section);
  return (
    <section className={`pool-section pool-section-${section.name}`} aria-label={label}>
      <header className="pool-section-header">
        <span className="pool-section-label">{label}</span>
        {health ? <span className="pool-section-health">{health}</span> : null}
        {onSizeChange ? (
          <span className="pool-size-control">
            <button
              type="button"
              className="pool-size-step"
              aria-label="타일 작게"
              onClick={() => onSizeChange(stepPoolSize(size, -1))}
            >
              −
            </button>
            <button
              type="button"
              className="pool-size-step"
              aria-label="타일 크게"
              onClick={() => onSizeChange(stepPoolSize(size, 1))}
            >
              +
            </button>
          </span>
        ) : null}
      </header>
      {section.items.length === 0 ? (
        <div className="pool-section-empty">비어 있음</div>
      ) : (
        <div className={`pool-section-grid pool-size-${size}`}>
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
    </section>
  );
}
