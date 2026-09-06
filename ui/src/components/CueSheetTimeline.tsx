// 두 축이 하나의 상태를 본다 — 위는 가로로 스크롤하는 타임라인 창,
// 아래는 그 창에 맞춰 세로로 움직이는 큐시트. 선택된 큐는 양쪽에 함께 표시된다.
//
// 정본 산출물은 LXSEQ_SAMPLE_01_Sugar_r3.timeline.html 이고, 이 컴포넌트는
// 그 시각 언어(틱 레일 · 구간 밴드 · 큐 칩 · 인텐시티 폴리라인 · 팔레트 범례 ·
// 14열 큐시트)를 앱 안에서 재현한다. 읽기 전용 — 편집·콘솔 쓰기는 없다.
//
// t279 가 넓힌 큐시트 필드는 전부 선택 필드다. 서버가 아직 대부분을 채우지
// 않으므로 모든 칸은 값이 없으면 EMPTY_CELL 로 떨어진다 (undefined 를 그리지
// 않는다).
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import type {
  SongTimelinePaletteEntry,
  SongTimelineSection,
  SongTimelineView,
} from "../protocol";

/** 큐시트에 한 번에 보이는 행 수. 타임라인 창과 같은 범위를 쓴다. */
export const VISIBLE_CUE_ROWS = 5;

/** 값이 없는 칸의 표기. undefined 를 그리지 않기 위한 단일 출구. */
export const EMPTY_CELL = "—";

/** 초당 픽셀. 곡 전체 길이를 가로 스크롤 폭으로 환산하는 유일한 축척.
 * 창이 곡 전체를 담으면 「창」이 아니게 된다 — 16초짜리 구간 기준으로 화면에
 * VISIBLE_CUE_ROWS 안팎이 보이도록 잡았다(1400px ≈ 58초 ≈ 큐 4~5개). */
export const PX_PER_SECOND = 24;

/** 팔레트 범례에서 색을 못 찾았을 때 쓰는 중립색. */
const FALLBACK_CUE_COLOR = "#4A5568";

/** 값이 없으면 em-dash. 빈 문자열·빈 배열도 없는 것으로 본다. */
export function cell(value: string | number | string[] | null | undefined): string {
  if (value === null || value === undefined) return EMPTY_CELL;
  if (Array.isArray(value)) return value.length > 0 ? value.join("+") : EMPTY_CELL;
  if (typeof value === "number") return Number.isFinite(value) ? String(value) : EMPTY_CELL;
  return value.trim() === "" ? EMPTY_CELL : value;
}

/** "MM:SS.d" — 정본 산출물의 TC 표기. */
export function formatTc(ms: number | null | undefined): string {
  if (ms === null || ms === undefined || !Number.isFinite(ms)) return EMPTY_CELL;
  const total = Math.max(0, ms) / 1000;
  const minutes = Math.floor(total / 60);
  const seconds = total - minutes * 60;
  return `${String(minutes).padStart(2, "0")}:${seconds.toFixed(1).padStart(4, "0")}`;
}

/** 초 단위 지속시간 — 정본 산출물의 Dur 열. */
export function formatDuration(ms: number | null | undefined): string {
  if (ms === null || ms === undefined || !Number.isFinite(ms)) return EMPTY_CELL;
  return (Math.max(0, ms) / 1000).toFixed(1);
}

/** Q# 라벨. 정본은 Q010 처럼 세 자리로 적는다. */
export function cueLabel(section: SongTimelineSection): string {
  return `Q${String(section.cue_number).padStart(3, "0")}`;
}

/** 곡 전체 길이. 헤더 메타가 없으면 마지막 구간 끝에서 역산한다. */
export function songTotalMs(timeline: SongTimelineView): number {
  if (timeline.total_duration_ms && timeline.total_duration_ms > 0) {
    return timeline.total_duration_ms;
  }
  const last = timeline.sections[timeline.sections.length - 1];
  if (!last) return 1;
  return Math.max(1, last.end_ms ?? last.start_ms + (last.duration_ms ?? 15_000));
}

/** TC Out. 서버가 안 주면 다음 구간 시작 → 곡 끝 순으로 내려간다. */
export function sectionEndMs(
  section: SongTimelineSection,
  next: SongTimelineSection | undefined,
  totalMs: number,
): number | null {
  if (section.end_ms !== undefined) return section.end_ms;
  if (section.duration_ms !== undefined) return section.start_ms + section.duration_ms;
  if (next) return next.start_ms;
  return totalMs > section.start_ms ? totalMs : null;
}

/** Dur. end 를 못 구하면 없는 것으로 둔다 — 추정치를 표에 싣지 않는다. */
export function sectionDurationMs(
  section: SongTimelineSection,
  next: SongTimelineSection | undefined,
  totalMs: number,
): number | null {
  if (section.duration_ms !== undefined) return section.duration_ms;
  const end = sectionEndMs(section, next, totalMs);
  return end === null ? null : Math.max(0, end - section.start_ms);
}

/** Intensity 열. 그룹별 값이 있으면 그대로, 없으면 전체 d_level 을 % 로 적는다. */
export function sectionIntensityText(section: SongTimelineSection): string {
  if (section.intensity && section.intensity.length > 0) {
    return section.intensity.map((entry) => `${entry.group} ${entry.level}`).join(" / ");
  }
  return String(sectionIntensityPercent(section));
}

/** 폴리라인 높이용 0..100. 그룹별 값이 있으면 최댓값, 없으면 d_level(1..5)×20. */
export function sectionIntensityPercent(section: SongTimelineSection): number {
  if (section.intensity && section.intensity.length > 0) {
    return Math.max(...section.intensity.map((entry) => entry.level));
  }
  return Math.min(100, Math.max(0, section.d_level * 20));
}

/** SNAP 전환 — 큐 칩의 흰 좌측선이 이 값을 표시한다. */
export function isSnapCue(section: SongTimelineSection): boolean {
  return section.trans === "SNAP";
}

/** DERIVED 배너는 장식이 아니다: 타임코드가 계산값임을 감독에게 알린다. */
export function showDerivedBanner(timeline: SongTimelineView): boolean {
  return timeline.tc_method === "DERIVED";
}

export function derivedBannerText(timeline: SongTimelineView): string {
  return (
    timeline.tc_method_warning ??
    "이 타임라인의 모든 타임코드는 마디 연산으로 도출한 값입니다. 음원 청취로 검증하지 않았습니다. 리허설에서 LTC 대조 필수."
  );
}

/** 큐시트에 그릴 행 범위. 선택된 큐를 가운데 두고 목록 양끝에서 잘린다. */
export function cueWindow(
  total: number,
  selectedIndex: number,
  rows: number = VISIBLE_CUE_ROWS,
): { start: number; end: number } {
  if (total <= 0) return { start: 0, end: 0 };
  const span = Math.min(rows, total);
  const centred = selectedIndex - Math.floor(span / 2);
  const start = Math.min(Math.max(0, centred), total - span);
  return { start, end: start + span };
}

/** 큐를 고른 뒤 레일이 스스로 움직이는 동안 스크롤을 무시할 시간(ms).
 * 부드러운 스크롤과 브라우저의 자동 스크롤은 이벤트를 여러 번 낸다 — 한 번만
 * 막으면 나머지가 방금 고른 큐를 다시 0번으로 되돌린다(실측). */
export const SCROLL_SETTLE_MS = 700;

/** 이 스크롤 이벤트를 선택 변경으로 받아들일지. 선택 직후 창은 무시한다. */
export function shouldAdoptScroll(now: number, suppressUntil: number): boolean {
  return now >= suppressUntil;
}

/** 가로 스크롤 위치(ms)에 해당하는 큐 인덱스 — 레일 스크롤이 큐시트를 움직인다. */
export function cueIndexAtMs(sections: SongTimelineSection[], ms: number): number {
  let index = 0;
  for (let i = 0; i < sections.length; i += 1) {
    if (sections[i].start_ms <= ms) index = i;
    else break;
  }
  return index;
}

/** 팔레트 범례에서 색을 찾는다. `palette_primary` 는 "P4 핫핑크" 형태라
 * 앞 토큰(P4)이 범례 id 다. 못 찾으면 중립색으로 떨어진다. */
export function paletteColorFor(
  section: SongTimelineSection,
  legend: SongTimelinePaletteEntry[] | undefined,
): string {
  if (!legend || legend.length === 0) return FALLBACK_CUE_COLOR;
  const token = (section.palette_primary ?? section.palette[0] ?? "").trim().split(/\s+/)[0];
  if (!token) return FALLBACK_CUE_COLOR;
  const hit = legend.find((entry) => entry.id === token || entry.name === token);
  return hit?.color ?? FALLBACK_CUE_COLOR;
}

/** 틱 레일 눈금 — 16초 간격, 정본 산출물과 같은 간격이다. */
const TICK_STEP_MS = 16_000;

function ticksFor(totalMs: number): number[] {
  const ticks: number[] = [];
  for (let ms = 0; ms <= totalMs; ms += TICK_STEP_MS) ticks.push(ms);
  return ticks;
}

function intensityPolyline(
  sections: SongTimelineSection[],
  totalMs: number,
  width: number,
  height: number,
): string {
  if (sections.length === 0) return "";
  const points: string[] = [];
  sections.forEach((section, index) => {
    const next = sections[index + 1];
    const end = sectionEndMs(section, next, totalMs) ?? totalMs;
    const y = height - (sectionIntensityPercent(section) / 100) * height;
    points.push(`${((section.start_ms / totalMs) * width).toFixed(2)},${y.toFixed(2)}`);
    points.push(`${((end / totalMs) * width).toFixed(2)},${y.toFixed(2)}`);
  });
  return points.join(" ");
}

const SHEET_COLUMNS = [
  "Q#",
  "Section",
  "TC In",
  "TC Out",
  "Dur",
  "Mood",
  "Color(주/보조)",
  "Intensity",
  "Fixture Group",
  "Movement",
  "Effect",
  "Trans",
  "Fade",
  "Note",
];

export interface CueSheetTimelineProps {
  timeline: SongTimelineView | null;
}

export function CueSheetTimeline({ timeline }: CueSheetTimelineProps) {
  const [selectedIndex, setSelectedIndex] = useState(0);
  const railRef = useRef<HTMLDivElement | null>(null);
  // 프로그램이 만든 스크롤이 방금 고른 큐를 되돌리지 않게 잠시 막는다.
  const suppressUntilRef = useRef(0);

  const sections = timeline?.sections ?? [];
  const totalMs = useMemo(() => (timeline ? songTotalMs(timeline) : 1), [timeline]);
  const trackWidth = Math.max(640, Math.round((totalMs / 1000) * PX_PER_SECOND));

  const selectCue = useCallback((index: number) => {
    suppressUntilRef.current = Date.now() + SCROLL_SETTLE_MS;
    setSelectedIndex(index);
    const rail = railRef.current;
    if (!rail) return;
    const chip = rail.querySelector<HTMLElement>(`[data-cue-index="${index}"]`);
    if (!chip) return;
    rail.scrollTo({ left: Math.max(0, chip.offsetLeft - rail.clientWidth / 3), behavior: "smooth" });
  }, []);

  const onRailScroll = useCallback(() => {
    if (!shouldAdoptScroll(Date.now(), suppressUntilRef.current)) return;
    const rail = railRef.current;
    if (!rail || sections.length === 0) return;
    const ms = (rail.scrollLeft / trackWidth) * totalMs;
    setSelectedIndex(cueIndexAtMs(sections, ms));
  }, [sections, totalMs, trackWidth]);

  useEffect(() => {
    setSelectedIndex(0);
  }, [timeline?.song_title, timeline?.sequence_number]);

  if (timeline === null) {
    return (
      <section className="cue-sheet-timeline is-empty" aria-label="큐시트 타임라인">
        <p>아직 볼 곡이 없습니다. 설계가 끝나면 구간과 큐시트가 여기에 표시됩니다.</p>
      </section>
    );
  }

  const visible = cueWindow(sections.length, selectedIndex);
  const rows = sections.slice(visible.start, visible.end);
  const legend = timeline.palette_legend ?? [];

  return (
    <section className="cue-sheet-timeline" aria-label={`${timeline.song_title} 큐시트 타임라인`}>
      <header className="cst-header">
        <h2>
          {timeline.song_title}
          <small>LX-SEQ · 조명연출 시퀀스</small>
        </h2>
        <div className="cst-meta">
          <code>{formatTc(timeline.total_duration_ms ?? totalMs)}</code>
          <code>{cell(timeline.bpm)} BPM</code>
          <code>{cell(timeline.time_signature)}</code>
          <code>{cell(timeline.musical_key)}</code>
          <code>
            {timeline.bar_count === undefined ? EMPTY_CELL : `${timeline.bar_count}마디`}
            {timeline.seconds_per_bar === undefined
              ? ""
              : ` · 1마디 ${timeline.seconds_per_bar.toFixed(3)}s`}
          </code>
          <code>TC_SOURCE: {cell(timeline.tc_source)}</code>
          <code>{sections.length} cues</code>
          {timeline.tc_origin !== undefined && <span>TC_ORIGIN: {timeline.tc_origin}</span>}
        </div>
      </header>

      {showDerivedBanner(timeline) && (
        <div className="cst-derived" role="alert">
          <b>TC_METHOD: DERIVED</b> — {derivedBannerText(timeline)}
        </div>
      )}

      <div className="cst-panel">
        <h3>TIMELINE</h3>
        <div className="cst-rail" ref={railRef} onScroll={onRailScroll}>
          <div className="cst-track" style={{ width: trackWidth }}>
            <div className="cst-ticks">
              {ticksFor(totalMs).map((ms) => (
                <div className="cst-tick" key={ms} style={{ left: `${(ms / totalMs) * 100}%` }}>
                  <span>{formatTc(ms)}</span>
                </div>
              ))}
            </div>

            <div className="cst-sections">
              {sections.map((section, index) => {
                const next = sections[index + 1];
                const end = sectionEndMs(section, next, totalMs) ?? totalMs;
                const duration = sectionDurationMs(section, next, totalMs);
                return (
                  <div
                    className="cst-section"
                    key={`sec-${section.index}-${section.cue_number}`}
                    style={{
                      left: `${(section.start_ms / totalMs) * 100}%`,
                      width: `${((end - section.start_ms) / totalMs) * 100}%`,
                      background: paletteColorFor(section, legend),
                    }}
                  >
                    <b>{section.label}</b>
                    <i>
                      {section.bar_count === undefined ? EMPTY_CELL : `${section.bar_count}마디`}
                      {duration === null ? "" : ` · ${formatDuration(duration)}s`}
                    </i>
                  </div>
                );
              })}
            </div>

            <div className="cst-cues">
              {sections.map((section, index) => {
                const next = sections[index + 1];
                const end = sectionEndMs(section, next, totalMs) ?? totalMs;
                const selected = index === selectedIndex;
                return (
                  <button
                    type="button"
                    className={`cst-cue${isSnapCue(section) ? " is-snap" : ""}${selected ? " is-selected" : ""}`}
                    key={`cue-${section.index}-${section.cue_number}`}
                    data-cue-index={index}
                    aria-pressed={selected}
                    title={`${cueLabel(section)} ${section.label} · ${sectionIntensityText(section)} · ${cell(section.trans)}`}
                    style={{
                      left: `${(section.start_ms / totalMs) * 100}%`,
                      width: `${((end - section.start_ms) / totalMs) * 100}%`,
                      background: paletteColorFor(section, legend),
                    }}
                    onClick={() => selectCue(index)}
                  >
                    {cueLabel(section)}
                  </button>
                );
              })}
            </div>

            <svg
              className="cst-chart"
              viewBox={`0 0 ${trackWidth} 100`}
              preserveAspectRatio="none"
              aria-label="구간별 인텐시티"
            >
              <line x1="0" y1="0" x2={trackWidth} y2="0" stroke="#2f394b" strokeDasharray="3 4" />
              <line x1="0" y1="50" x2={trackWidth} y2="50" stroke="#2a3243" strokeDasharray="3 4" />
              <polyline
                points={intensityPolyline(sections, totalMs, trackWidth, 100)}
                fill="none"
                stroke="#ff3c9e"
                strokeWidth="2"
                vectorEffect="non-scaling-stroke"
              />
            </svg>
          </div>
        </div>

        <div className="cst-legend">
          {legend.map((entry) => (
            <span className="cst-legend-item" key={entry.id}>
              <i style={{ background: entry.color }} />
              {entry.id} {entry.name}
            </span>
          ))}
          <span className="cst-legend-item">
            <i className="cst-legend-snap" />
            흰 좌측선 = SNAP 전환
          </span>
        </div>
      </div>

      <div className="cst-panel">
        <h3>
          CUE SHEET
          <small>
            {sections.length === 0
              ? "큐 없음"
              : `${visible.start + 1}–${visible.end} / ${sections.length}`}
          </small>
        </h3>
        <div className="cst-sheet-scroll">
        <table className="cst-sheet">
          <thead>
            <tr>
              {SHEET_COLUMNS.map((column) => (
                <th key={column}>{column}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((section) => {
              const index = sections.indexOf(section);
              const next = sections[index + 1];
              const selected = index === selectedIndex;
              return (
                <tr
                  key={`row-${section.index}-${section.cue_number}`}
                  className={selected ? "is-selected" : undefined}
                  aria-selected={selected}
                  onClick={() => selectCue(index)}
                >
                  <td className="m">{cueLabel(section)}</td>
                  <td className="m">{cell(section.label)}</td>
                  <td className="m">{formatTc(section.start_ms)}</td>
                  <td className="m">{formatTc(sectionEndMs(section, next, totalMs))}</td>
                  <td className="m">{formatDuration(sectionDurationMs(section, next, totalMs))}</td>
                  <td>{cell(section.mood)}</td>
                  <td>
                    {cell(section.palette_primary)} / {cell(section.palette_secondary)}
                  </td>
                  <td className="m">{sectionIntensityText(section)}</td>
                  <td className="fx">{cell(section.fixture_groups)}</td>
                  <td>{cell(section.movement)}</td>
                  <td>{cell(section.effect ?? (section.fx.length ? section.fx.join(" · ") : null))}</td>
                  <td className={`m${isSnapCue(section) ? " snap" : ""}`}>{cell(section.trans)}</td>
                  <td className="m">
                    {section.fade_seconds === undefined
                      ? EMPTY_CELL
                      : section.fade_seconds.toFixed(1)}
                  </td>
                  <td className="nt">{cell(section.note)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
        </div>
      </div>
    </section>
  );
}
