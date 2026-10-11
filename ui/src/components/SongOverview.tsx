// 곡 전체 지도 (SPEC-LDBEAT-001 M9 step 1, 카드 t559, REQ-LDBEAT-018).
//
// 시안 `ldbeat-runbook-ui-proposal-20261008.html`의 `.ov`/`drawOv()` 모양을
// 옮긴다: 구간 띠 · 에너지선 · 강조 ★ · 채운 범위(점선) · 지금 보는 범위
// 창(흰 테두리) · 재생 위치(노란 선) · 클릭하면 그 마디로 점프 · 확대 3단계.
// 그리는 값은 전부 `songOverviewModel.ts`가 곡 데이터에서 만든 모델이다.
import { useEffect, useRef, useState } from "react";

import { OVERVIEW_ZOOM_LEVELS, overviewBarAtFraction, type OverviewZoom, type SongOverviewModel } from "./songOverviewModel";

export interface SongOverviewProps {
  model: SongOverviewModel;
  /** 격자에 실제 칸 데이터가 있는 범위(시안 "채운 범위"). */
  filledRange: { start: number; end: number };
  /** 지금 타임라인에 보이는 범위(배타적 끝). 모르면 null. */
  visibleWindow: { startBar: number; endBar: number } | null;
  playheadBar: number | null;
  currentBar: number;
  /** SCENE 메모가 걸린 마디(t537 ② — 기존 지도의 「⚠ 미정」 표식 유지). */
  sceneMemos: readonly { bar: number; text: string }[];
  zoom: OverviewZoom;
  onZoomChange: (zoom: OverviewZoom) => void;
  onJump: (bar: number) => void;
}

const SVG_HEIGHT = 64;
/** 측정 전(첫 렌더·정적 렌더) 기본 폭 — 시안 viewBox 와 같은 값. */
const DEFAULT_WIDTH = 830;
const NEUTRAL_SECTION_FILL = "#5b6b8a";

export function SongOverview({
  model,
  filledRange,
  visibleWindow,
  playheadBar,
  currentBar,
  sceneMemos,
  zoom,
  onZoomChange,
  onJump,
}: SongOverviewProps) {
  const svgRef = useRef<SVGSVGElement | null>(null);
  const [width, setWidth] = useState(DEFAULT_WIDTH);

  useEffect(() => {
    const el = svgRef.current;
    if (!el) return;
    const measure = () => setWidth(Math.max(300, Math.round(el.clientWidth || DEFAULT_WIDTH)));
    measure();
    if (typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(measure);
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const total = Math.max(1, model.totalBars);
  const ub = width / total;
  const x = (bar: number) => bar * ub;

  // 에너지선 — 에너지를 아는 구간이 이어진 동안만 한 선으로 잇는다(모르는
  // 구간에서는 끊는다, 지어내지 않음).
  const energyRuns: string[] = [];
  let run: string[] = [];
  for (const section of model.sections) {
    if (section.energy === null) {
      if (run.length > 0) energyRuns.push(run.join(" "));
      run = [];
      continue;
    }
    for (let b = section.startBar; b < section.endBar; b++) {
      run.push(`${(x(b + 0.5)).toFixed(1)},${(20 - section.energy * 16).toFixed(1)}`);
    }
  }
  if (run.length > 0) energyRuns.push(run.join(" "));

  const filledEnd = Math.min(total, filledRange.end + 1);

  return (
    <div className="song-overview">
      <div className="song-overview-label">
        <span>곡 전체 — 구간 · 에너지선(구간 D 레벨) · 강조(★) · 흰 테두리 = 아래에 보이는 범위</span>
        <span className="song-overview-zoom" role="group" aria-label="확대">
          {OVERVIEW_ZOOM_LEVELS.map((level) => (
            <button
              key={level.id}
              type="button"
              className={zoom === level.id ? "on" : undefined}
              aria-pressed={zoom === level.id}
              onClick={() => onZoomChange(level.id)}
            >
              {level.label}
            </button>
          ))}
        </span>
      </div>
      <svg
        ref={svgRef}
        className="song-overview-map"
        viewBox={`0 0 ${width} ${SVG_HEIGHT}`}
        role="img"
        aria-label={`곡 전체 지도 — ${total}마디, 지금 ${currentBar}마디`}
        onClick={(event) => {
          const rect = event.currentTarget.getBoundingClientRect();
          if (rect.width <= 0) return;
          onJump(overviewBarAtFraction((event.clientX - rect.left) / rect.width, total));
        }}
      >
        {model.sections.map((section) => {
          const w = x(section.endBar) - x(section.startBar);
          return (
            <g key={`${section.label}-${section.startBar}`} className="song-overview-section">
              <rect
                x={x(section.startBar)}
                y={22}
                width={Math.max(0, w - 0.5)}
                height={26}
                fill={section.hex ?? NEUTRAL_SECTION_FILL}
                opacity={0.85}
              >
                <title>{`${section.label} · ${section.startBar}~${section.endBar - 1}마디`}</title>
              </rect>
              {w > 34 && (
                <text x={x(section.startBar) + 3} y={39} fontSize={10} fill="#fff">
                  {section.label}
                </text>
              )}
            </g>
          );
        })}
        {model.sections.length === 0 && (
          <text x={6} y={39} fontSize={10} fill="#9a98a6">
            구간 데이터 없음
          </text>
        )}
        {energyRuns.map((points, i) => (
          <polyline key={i} className="song-overview-energy" points={points} fill="none" stroke="#ffd84d" strokeWidth={1.5} />
        ))}
        {model.accentBars.map((bar) => (
          <text
            key={bar}
            className="song-overview-accent"
            data-bar={bar}
            x={x(bar + 0.5)}
            y={62}
            fontSize={11}
            fill="#ffd84d"
            textAnchor="middle"
          >
            ★
          </text>
        ))}
        {sceneMemos.map((memo) => (
          <text
            key={`memo-${memo.bar}`}
            className="song-overview-memo"
            x={x(memo.bar + 0.5)}
            y={12}
            fontSize={9}
            fill="#e0a040"
            textAnchor="middle"
          >
            ⚠<title>{`${memo.bar}마디 미정 — ${memo.text}`}</title>
          </text>
        ))}
        {filledEnd > filledRange.start && filledEnd < total && (
          <g className="song-overview-filled">
            <rect
              x={x(filledRange.start)}
              y={22}
              width={x(filledEnd) - x(filledRange.start)}
              height={26}
              fill="none"
              stroke="#7fc45a"
              strokeDasharray="3 2"
            />
            <text x={x(filledEnd) + 3} y={58} fontSize={9} fill="#7fc45a">
              {`← 채운 범위(${filledRange.start}~${filledRange.end})`}
            </text>
          </g>
        )}
        {visibleWindow && visibleWindow.endBar > visibleWindow.startBar && (
          <rect
            className="song-overview-window"
            x={x(visibleWindow.startBar)}
            y={20}
            width={x(visibleWindow.endBar) - x(visibleWindow.startBar)}
            height={30}
            fill="#ffffff10"
            stroke="#fff"
            strokeWidth={1.5}
          />
        )}
        {playheadBar !== null && (
          <line
            className="song-overview-playhead"
            x1={x(playheadBar + 0.5)}
            x2={x(playheadBar + 0.5)}
            y1={16}
            y2={52}
            stroke="#ffd84d"
            strokeWidth={2}
          />
        )}
      </svg>
    </div>
  );
}
