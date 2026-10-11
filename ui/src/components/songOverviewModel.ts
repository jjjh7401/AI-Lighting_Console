// 곡 전체 지도의 데이터 모양 (SPEC-LDBEAT-001 M9 step 1, 카드 t559,
// REQ-LDBEAT-018 / AC-LDBEAT-018).
//
// plan.md M9 step 1 이 "데이터 모양을 먼저 고정"하라고 한 자리다 — 화면
// (`SongOverview.tsx`)은 이 모듈이 낸 값만 그린다. 모든 값은 곡 데이터
// (`SongTimelineView.bar_count` · `sections[].bar_start/start_ms/d_level/
// accents/palette_primary_hex`)에서 읽는다. 특정 곡의 마디 번호를 코드에
// 두지 않는다(REQ-LDBEAT-018(a), REQ-LDBEAT-006(v-1)과 같은 일반화 원칙).

/** 서버가 `timeline.sections[]`로 이미 보내는 필드 중 지도가 쓰는 것만. */
export interface SongOverviewSectionInput {
  label: string;
  start_ms: number;
  palette_primary_hex?: string | null;
  /** 큐시트 확장(t279) — 있으면 `start_ms` 환산보다 우선한다. */
  bar_start?: number;
  /** 1~5(서버 `song_plan.py`가 검증). 없으면 에너지 미정. */
  d_level?: number;
  /** 구간 단위 강조 문구(예: `"climax accent"`). 비어 있지 않으면 ★. */
  accents?: readonly string[];
}

export interface SongOverviewSection {
  label: string;
  startBar: number;
  /** 배타적 — 다음 구간 시작(또는 곡 끝). */
  endBar: number;
  hex: string | null;
  /** d_level 을 0~1 로 옮긴 값. 모르면 null(선을 지어내지 않는다). */
  energy: number | null;
}

export interface SongOverviewModel {
  totalBars: number;
  sections: SongOverviewSection[];
  /** 강조(★) 마디 — accents 가 있는 구간의 시작 마디. */
  accentBars: number[];
}

/** 서버 `song_plan.py`의 d_level 상한(1~5). */
const D_LEVEL_MAX = 5;

export function buildSongOverview({
  sections,
  barCount,
  secondsPerBar,
  fallbackRange,
}: {
  sections: readonly SongOverviewSectionInput[] | undefined;
  barCount: number | null | undefined;
  secondsPerBar: number | null | undefined;
  fallbackRange: { start: number; end: number };
}): SongOverviewModel {
  const totalBars =
    typeof barCount === "number" && Number.isFinite(barCount) && barCount > 0
      ? Math.round(barCount)
      : fallbackRange.end + 1;
  const validSpb = typeof secondsPerBar === "number" && Number.isFinite(secondsPerBar) && secondsPerBar > 0;

  const located = (sections ?? [])
    .map((section) => {
      let startBar: number | null = null;
      if (typeof section.bar_start === "number" && Number.isFinite(section.bar_start)) {
        startBar = Math.max(0, Math.round(section.bar_start));
      } else if (validSpb) {
        startBar = Math.max(0, Math.round(section.start_ms / 1000 / (secondsPerBar as number)));
      }
      return { section, startBar };
    })
    .filter((item): item is { section: SongOverviewSectionInput; startBar: number } => item.startBar !== null)
    .filter((item) => item.startBar < totalBars)
    .sort((a, b) => a.startBar - b.startBar);

  const out: SongOverviewSection[] = [];
  const accentBars: number[] = [];
  located.forEach(({ section, startBar }, i) => {
    const endBar = located[i + 1]?.startBar ?? totalBars;
    if (endBar <= startBar) return;
    const level = section.d_level;
    out.push({
      label: section.label,
      startBar,
      endBar,
      hex: section.palette_primary_hex ?? null,
      energy:
        typeof level === "number" && Number.isFinite(level)
          ? Math.max(0, Math.min(1, level / D_LEVEL_MAX))
          : null,
    });
    if ((section.accents ?? []).length > 0) accentBars.push(startBar);
  });

  return { totalBars, sections: out, accentBars };
}

export type OverviewZoom = "song" | "bars16" | "bars8";

/** 시안 `#zoom` 버튼 순서 그대로: 곡 전체 / 16마디 / 8마디. */
export const OVERVIEW_ZOOM_LEVELS: readonly { id: OverviewZoom; label: string; bars: number | null }[] = [
  { id: "song", label: "곡 전체", bars: null },
  { id: "bars16", label: "16마디", bars: 16 },
  { id: "bars8", label: "8마디", bars: 8 },
];

/** 곡 전체 단계에서 막대가 읽히지 않을 만큼 좁아지지 않게 하는 하한. */
const MIN_PX_PER_BAR = 6;

/** 확대 단계 → 타임라인 마디 한 칸의 가로 폭(px). 보이는 폭(`visibleWidth`,
 * 타임라인 칸에서 줄 이름 열을 뺀 폭)을 아직 모르면(첫 렌더) 기존 고정값으로
 * 떨어진다. */
export function pxPerBarForZoom(
  zoom: OverviewZoom,
  visibleWidth: number,
  totalBars: number,
  fallbackPxPerBar = 42,
): number {
  if (!(visibleWidth > 0)) return fallbackPxPerBar;
  const level = OVERVIEW_ZOOM_LEVELS.find((z) => z.id === zoom);
  const bars = level?.bars ?? Math.max(1, totalBars);
  const px = visibleWidth / bars;
  return level?.bars ? px : Math.max(MIN_PX_PER_BAR, px);
}

/** 지금 타임라인에 보이는 마디 범위(시안의 흰 테두리 창). `endBar` 배타적. */
export function overviewVisibleWindow({
  scrollLeft,
  visibleWidth,
  pxPerBar,
  rangeStart,
  totalBars,
}: {
  scrollLeft: number;
  visibleWidth: number;
  pxPerBar: number;
  rangeStart: number;
  totalBars: number;
}): { startBar: number; endBar: number } {
  if (!(pxPerBar > 0)) return { startBar: rangeStart, endBar: rangeStart };
  const startBar = Math.max(0, Math.min(totalBars, rangeStart + scrollLeft / pxPerBar));
  const endBar = Math.max(startBar, Math.min(totalBars, startBar + visibleWidth / pxPerBar));
  return { startBar, endBar };
}

/** 지도 위 클릭 가로 비율(0~1) → 마디. */
export function overviewBarAtFraction(fraction: number, totalBars: number): number {
  const bar = Math.floor(fraction * totalBars);
  return Math.max(0, Math.min(totalBars - 1, bar));
}
