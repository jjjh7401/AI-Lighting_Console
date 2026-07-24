// Left dashboard pane (SPEC-COPILOT-DASHUI-001, plan.md §B M3/M4, design.md
// §2 IA / §6 layout). M3 built the structural skeleton (header + collapse +
// an empty body region); M4 wires `dash.sections` into real onPC-style pool
// rendering via PoolSection/PoolTile, plus the header-strip fixture count +
// last-sync time + manual refresh affordance (design.md §2 헤더 스트립).
//
// No internal hooks by design: this project has no DOM/jsdom test harness
// (see protocol.ts's own header — "Pure functions only... unit-testable
// without a DOM"). A hook-free component can be called directly as a plain
// function in tests, returning an inspectable React element tree with no
// renderer — see DashBoard.test.tsx and the sibling AppShell in App.tsx.
import { type DashItem, type DashSection, type DashState } from "../protocol";
import { PoolSection } from "./PoolSection";

/**
 * Site preference (user direction, 2026-07-24): the preset pool list is too
 * long to be useful on the dashboard — show ONLY pool 21 ("All 1"). Every
 * other section renders unfiltered. Widen this set when more pools become
 * operationally relevant.
 */
export const VISIBLE_PRESET_POOL_NOS: ReadonlySet<number> = new Set([21]);

/** The section as the dashboard actually renders it (preset filter applied). */
export function visibleSection(section: DashSection): DashSection {
  if (section.name !== "preset_pools") return section;
  return {
    ...section,
    items: section.items.filter((item) => VISIBLE_PRESET_POOL_NOS.has(item.no)),
  };
}

export interface DashBoardProps {
  dash: DashState;
  /**
   * Optional collapse affordance. The M6 console-primary inversion makes the
   * info pane permanent — App no longer supplies this, so the ◂ 접기 button
   * disappears from the live UI; the prop stays for callers/tests that still
   * want a collapsible variant.
   */
  onToggleCollapse?: () => void;
  /**
   * Dispatches a manual `dash_catalog_request` (REQ-DASHUI-021 — refresh is
   * on-demand only, never timer-driven). Optional by design decision: M5
   * owns the actual socket wiring, so DashBoard exposes the callback slot
   * without forcing a stub on every M4-era caller. When omitted, the click
   * still fires (no dead button, design.md §7 rule 7) but only logs —
   * App.tsx starts supplying the real callback in M5.
   */
  onRefresh?: () => void;
  /** Per-item running lookup (M5) — see `pressVerbForSection`/`runningVerbForSection`. */
  isItemRunning?: (sectionName: string, item: DashItem) => boolean;
  /** Fires panel_execute or panel_stop depending on current running state (M5). */
  onItemPress?: (sectionName: string, item: DashItem) => void;
  /** Per-section tile width in px (M6-UX). Defaults when omitted. */
  sectionTileWidth?: (sectionName: string) => number | undefined;
  /** When provided, each section header offers a drag-resize handle. */
  onSectionResizeStart?: (sectionName: string, event: { clientX: number }) => void;
}

const SECTION_LABEL: Record<string, string> = {
  groups: "그룹",
  preset_pools: "프리셋",
  macros: "매크로",
  plugins: "플러그인",
  executors: "익스큐터",
};

function sectionLabel(name: string): string {
  return SECTION_LABEL[name] ?? name;
}

/** The console verb shown on a press-able tile in this section, if any. */
function pressVerbForSection(name: string): string | undefined {
  if (name === "macros") return "Macro";
  if (name === "executors") return "Go+";
  return undefined;
}

/**
 * The verb shown while a tile is running (M5, design.md §4). Executors get
 * an "Off" affordance; macros stay one-shot with no Off — pressing Run again
 * simply re-fires the macro rather than toggling anything (§4 "Off 어포던스
 * 없음").
 */
function runningVerbForSection(name: string): string | undefined {
  if (name === "executors") return "Off";
  return undefined;
}

/**
 * Per-item pressability (REQ-DASHUI-011): an executor tile is press-able
 * ONLY when the server's resolution report marks it `meta.resolved === true`
 * — an unresolved/unverified executor NEVER gets fireable affordance
 * (EXECBODY AC-016 inheritance). Macros are press-able unconditionally at
 * this layer — a blacklisted/unparseable macro body is held gate-side on
 * actual press (design.md §4), the tile still offers Run. Every other
 * section (groups/preset_pools/plugins) stays read-only — info tiles are
 * structurally non-fireable (DashItem carries no target_kind at all).
 */
export function dashItemIsPressable(sectionName: string, item: DashItem): boolean {
  if (sectionName === "macros") return true;
  if (sectionName === "executors") return item.meta?.resolved === true;
  return false;
}

/** `HH:MM:SS`, or a not-yet-synced placeholder before the first dash_catalog. */
export function formatSyncTime(lastSyncAt: number | null): string {
  if (lastSyncAt === null) return "동기화 전";
  const date = new Date(lastSyncAt);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
}

/**
 * REQ-DASHUI-009/022: fixtures render as a count summary ONLY — never a
 * per-fixture list or a slot-number-as-FID tile. `build_dash_catalog`
 * (server/web/dash.py `_count_only_items`) already encodes the count into a
 * single synthetic item's `meta.count`; this just reads it back out.
 * Returns null when the section is absent (not yet synced) or the expected
 * shape is missing — never a guessed number.
 */
export function fixtureCount(section: DashSection | undefined): number | null {
  const count = section?.items[0]?.meta?.count;
  return typeof count === "number" ? count : null;
}

/** The fixture-count phrase for the header strip — an honest "확인 불가" when
 * the section hasn't synced, failed, or (unexpectedly) lacks a count. */
export function fixtureSummaryLabel(section: DashSection | undefined): string {
  if (section === undefined || section.status !== "ok") return "확인 불가";
  const count = fixtureCount(section);
  return count !== null ? `${count}대` : "확인 불가";
}

/** The full header-strip line (design.md §2 "리그 요약: 픽스처 N대 · 동기화
 * HH:MM:SS"), including the stale suffix withdrawn by `clearOnDisconnect`. */
export function dashboardSummaryText(dash: DashState, fixturesSection: DashSection | undefined): string {
  const staleSuffix = dash.stale ? " (오래됨)" : "";
  return `픽스처 ${fixtureSummaryLabel(fixturesSection)} · 동기화 ${formatSyncTime(dash.lastSyncAt)}${staleSuffix}`;
}

export function DashBoard({
  dash,
  onToggleCollapse,
  onRefresh,
  isItemRunning,
  onItemPress,
  sectionTileWidth,
  onSectionResizeStart,
}: DashBoardProps) {
  const hasSections = dash.sections.length > 0;
  const fixturesSection = dash.sections.find((section) => section.name === "fixtures");
  // Fixtures fold into the header-strip summary line (design.md §2 헤더
  // 스트립), never their own pool grid — REQ-DASHUI-009 avoids the slot!=FID
  // trap structurally by never listing a single fixture.
  const poolSections = dash.sections.filter((section) => section.name !== "fixtures");

  const handleRefresh = () => {
    if (onRefresh) {
      onRefresh();
    } else {
      // eslint-disable-next-line no-console -- M5 wires the real dispatch.
      console.debug("dash: manual refresh requested (M5 wires dash_catalog_request)");
    }
  };

  return (
    <aside className="dashboard" aria-label="리그 대시보드">
      <header className="dashboard-header">
        <span className="dashboard-title">리그 요약</span>
        {onToggleCollapse && (
          <button
            className="dashboard-collapse"
            onClick={onToggleCollapse}
            aria-label="대시보드 접기"
          >
            ◂ 접기
          </button>
        )}
      </header>
      <div className="dashboard-syncline">
        <span className="dashboard-summary">{dashboardSummaryText(dash, fixturesSection)}</span>
        <button className="dashboard-refresh" onClick={handleRefresh} aria-label="새로고침">
          ⟳ 새로고침
        </button>
      </div>
      <div className="dashboard-body">
        {hasSections ? (
          <div className="dashboard-sections">
            {poolSections.map(visibleSection).map((section) => (
              <PoolSection
                key={section.name}
                section={section}
                label={sectionLabel(section.name)}
                isPressable={(item) => dashItemIsPressable(section.name, item)}
                verb={pressVerbForSection(section.name)}
                runningVerb={runningVerbForSection(section.name)}
                isRunning={
                  isItemRunning ? (item) => isItemRunning(section.name, item) : undefined
                }
                onPress={onItemPress ? (item) => onItemPress(section.name, item) : undefined}
                tileWidth={sectionTileWidth?.(section.name)}
                onResizeStart={
                  onSectionResizeStart
                    ? (event) => onSectionResizeStart(section.name, event)
                    : undefined
                }
              />
            ))}
          </div>
        ) : (
          <div className="dashboard-empty">로딩 중…</div>
        )}
      </div>
    </aside>
  );
}
