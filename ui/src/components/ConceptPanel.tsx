// t454 — REQ-LDDESIGN-079/080/097/098 컨셉 패널(런북 모드 블록 1과 2 사이).
//
// 원천 판정(.moai/reports/t454/verdict.md 원천 매핑 표):
// - 탭 1 여섯 칸 표의 앞 다섯 칸 — 구간 값(label·palette·intensity·
//   fixture_groups·movement·effect)이 있다 → 채운다.
// - 「그래서 보이는 것」·인과 불릿(워크시트 `concept` 원문)·"한눈에" 5단계
//   카드·탭 2·3 본문 — 서버가 내지 않는다 → 데이터 없음. 단계 이름이나 문장을
//   지어 넣지 않는다(REQ-097: 수치는 큐 데이터에서 파생, 하드코딩 금지).
// - 항목 클릭 4칸 설명 — 펼칠 항목(불릿·칩) 자체가 없어 그리지 않는다.
import { useState } from "react";

import type { SongTimelineSection } from "../protocol";
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
}

export function ConceptPanel({ sections }: ConceptPanelProps) {
  const [tab, setTab] = useState<TabId>("master");
  const rows = grammarRows(sections);

  return (
    <details className="concept-panel">
      <summary className="concept-panel-head">이 곡의 컨셉</summary>
      <div className="concept-panel-body">
        <section className="concept-glance" aria-label="한눈에">
          <h4>한눈에 — 이 곡을 이렇게 끌고 간다</h4>
          <p className="concept-nodata">{NO_DATA} — 단계 배정 원천이 서버에 없다</p>
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
                  {rows.map((row) => (
                    <tr key={row.key}>
                      <td>{row.section}</td>
                      <td>{row.color}</td>
                      <td className="m">{row.fixture}</td>
                      <td>{row.motion}</td>
                      <td>{row.effect}</td>
                      <td className="concept-nodata">{NO_DATA}</td>
                    </tr>
                  ))}
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
