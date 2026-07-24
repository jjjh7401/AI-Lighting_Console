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

export interface PoolSectionProps {
  section: DashSection;
  label: string;
  /** Per-item pressability, decided by the caller — never inferred here. */
  isPressable: (item: DashItem) => boolean;
  /** The console verb for press-able tiles in this section (e.g. "Go+", "Macro"). */
  verb?: string;
  onPress?: (item: DashItem) => void;
}

export function PoolSection({ section, label, isPressable, verb, onPress }: PoolSectionProps) {
  const health = sectionHealthLabel(section);
  return (
    <section className={`pool-section pool-section-${section.name}`} aria-label={label}>
      <header className="pool-section-header">
        <span className="pool-section-label">{label}</span>
        {health ? <span className="pool-section-health">{health}</span> : null}
      </header>
      {section.items.length === 0 ? (
        <div className="pool-section-empty">비어 있음</div>
      ) : (
        <div className="pool-section-grid">
          {section.items.map((item) => (
            <PoolTile
              key={item.no}
              item={item}
              pressable={isPressable(item)}
              verb={verb}
              onPress={onPress}
            />
          ))}
        </div>
      )}
    </section>
  );
}
