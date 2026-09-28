// t454 — REQ-LDDESIGN-079/080/097/098 컨셉 패널(런북 모드 블록 1과 2 사이).
//
// 원천 판정(.moai/reports/t454/verdict.md 원천 매핑 표, t482 갱신):
// - 탭 1 여섯 칸 표의 앞 다섯 칸 — 구간 값(label·palette·intensity·
//   fixture_groups·movement·effect)이 있다 → 채운다.
// - "한눈에" 5단계 카드(t482) — 서버 `concept_report.glance` 가 단계 배정만 주고,
//   카드 수치는 CUE SHEET 와 같은 구간 데이터에서 계산한다(`conceptGlance.ts`).
//   배정 규칙은 감독 확인 전 제안 규칙이라 규칙 표식을 그대로 보인다.
// - 항목 클릭 4칸 설명(t482) — 표의 구간 행을 누르면 편다. 「무대에서」만 원천이
//   있다(서버 큐 설명 `rows[].description`). 나머지 셋은 사유와 함께 데이터 없음.
// - 「그래서 보이는 것」·인과 불릿(워크시트 `concept` 원문)·탭 2·3 본문 — 서버가
//   내지 않는다 → 데이터 없음. 문장을 지어 넣지 않는다.
import { useState } from "react";

import type { SongTimelineSection, SongTimelineView } from "../protocol";
import { explanationCells, glanceView } from "./conceptGlance";
import { NO_DATA, grammarRows } from "./runbookM7";

/** REQ-098 고정 라벨. 영어는 보조 표기로만 쓴다. */
const TABS = [
  { id: "master", label: "이 곡의 연출", sub: "Master Concept" },
  { id: "micro", label: "이 곡의 재료", sub: "Micro Concept" },
  { id: "grammar", label: "지키는 것·하지 않는 것·아껴 두는 것", sub: "Visual Grammar" },
] as const;

type TabId = (typeof TABS)[number]["id"];

/** REQ-080 고정 헤더. */
const GRAMMAR_HEADERS = ["구간", "색", "기구·밝기", "움직임", "효과", "그래서 보이는 것"];

export interface ConceptPanelProps {
  sections: SongTimelineSection[];
  /** t482 — 있으면 "한눈에" 카드와 4칸 설명을 이 타임라인(`concept_report`)에서 채운다. */
  timeline?: SongTimelineView | null;
}

export function ConceptPanel({ sections, timeline }: ConceptPanelProps) {
  const [tab, setTab] = useState<TabId>("master");
  const [openRow, setOpenRow] = useState<number | null>(null);
  const rows = grammarRows(sections);
  const glance = timeline
    ? glanceView(timeline)
    : ({ status: "none", reason: "단계 배정 원천이 서버에 없다" } as const);
  const report = timeline?.concept_report;

  return (
    <details className="concept-panel">
      <summary className="concept-panel-head">이 곡의 컨셉</summary>
      <div className="concept-panel-body">
        <section className="concept-glance" aria-label="한눈에">
          <h4>한눈에 — 이 곡을 이렇게 끌고 간다</h4>
          {glance.status === "none" ? (
            <p className="concept-nodata">
              {NO_DATA} — {glance.reason}
            </p>
          ) : (
            <>
              <p className="concept-glance-analysis">{glance.analysis}</p>
              <ol className="concept-glance-cards">
                {glance.cards.map((card) => (
                  <li key={card.stage} className={`concept-glance-card${card.empty ? " is-empty" : ""}`}>
                    <span
                      className="concept-glance-bar"
                      style={card.colorBar ? { background: card.colorBar } : undefined}
                      aria-hidden="true"
                    />
                    <strong>{card.stage}</strong>
                    {card.empty ? (
                      <p className="concept-nodata">{card.empty}</p>
                    ) : (
                      <dl>
                        <dt>Q</dt>
                        <dd>{card.qRange}</dd>
                        <dt>구간</dt>
                        <dd>{card.sections.join(" · ")}</dd>
                        <dt>시간</dt>
                        <dd>{card.time}</dd>
                        <dt>색</dt>
                        <dd>{card.hexes.length > 0 ? card.hexes.join(" ") : `${NO_DATA} — 색값 원천 없음`}</dd>
                        <dt>밝기</dt>
                        <dd>{card.brightness}</dd>
                        <dt>한 줄</dt>
                        <dd>{card.line}</dd>
                      </dl>
                    )}
                  </li>
                ))}
              </ol>
            </>
          )}
        </section>

        <div className="concept-tabs" role="tablist">
          {TABS.map((entry) => (
            <button
              type="button"
              role="tab"
              key={entry.id}
              aria-selected={tab === entry.id}
              className={`concept-tab${tab === entry.id ? " is-active" : ""}`}
              onClick={() => setTab(entry.id)}
            >
              {entry.label}
              <small>{entry.sub}</small>
            </button>
          ))}
        </div>

        {tab === "master" ? (
          <div className="concept-tab-body" role="tabpanel">
            <p className="concept-nodata">인과 불릿 · {NO_DATA} — 워크시트 concept 원문이 서버에서 오지 않는다</p>
            <div className="concept-grammar-scroll">
              <table className="concept-grammar">
                <thead>
                  <tr>
                    {GRAMMAR_HEADERS.map((head) => (
                      <th key={head}>{head}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.flatMap((row, position) => {
                    const open = openRow === position;
                    const main = (
                      <tr key={row.key}>
                        <td>
                          <button
                            type="button"
                            className="concept-row-toggle"
                            aria-expanded={open}
                            onClick={() => setOpenRow(open ? null : position)}
                          >
                            {row.section}
                          </button>
                        </td>
                        <td>{row.color}</td>
                        <td className="m">{row.fixture}</td>
                        <td>{row.motion}</td>
                        <td>{row.effect}</td>
                        <td className="concept-nodata">{NO_DATA}</td>
                      </tr>
                    );
                    if (!open) return [main];
                    return [
                      main,
                      <tr key={`${row.key}-explain`} className="concept-explain-row">
                        <td colSpan={GRAMMAR_HEADERS.length}>
                          <dl className="concept-explain">
                            {explanationCells(report, position).map((cell) => (
                              <div key={cell.title}>
                                <dt>{cell.title}</dt>
                                <dd>
                                  {cell.text}
                                  {cell.source && <small className="concept-explain-source">{cell.source}</small>}
                                </dd>
                              </div>
                            ))}
                          </dl>
                        </td>
                      </tr>,
                    ];
                  })}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <div className="concept-tab-body" role="tabpanel">
            <p className="concept-nodata">{NO_DATA}</p>
          </div>
        )}
      </div>
    </details>
  );
}
