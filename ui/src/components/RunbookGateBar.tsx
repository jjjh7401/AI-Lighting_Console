// t454 — REQ-LDDESIGN-084 상태줄 GATE. 런북 모드 전용이다: 앱 셸의
// StatusBanner(App.tsx)는 메인 화면과 같이 쓰는 컴포넌트라 건드리지 않는다.
//
// 원천은 `concept_report.gates` 하나다(server/concept/session_bridge.py).
// 판정은 통과·실패·해당없음 세 가지뿐이라, 설계(src/DESIGN.md §2)의 4상태 중
// 「경고」는 데이터 없음으로 둔다 — 0 으로 적으면 「경고 없음」으로 읽힌다.
//
// 훅 없는 컴포넌트다(RunbookMode 와 같은 관례). 상세 펼침은 <details> 가 한다.
import type { SongTimelineConceptReport } from "../protocol";
import { NO_DATA, type GateVerdict, gateRows, gateTally } from "./runbookM7";

const VERDICT_LABEL: Record<GateVerdict, { mark: string; text: string }> = {
  pass: { mark: "✓", text: "통과" },
  fail: { mark: "✕", text: "실패" },
  na: { mark: "–", text: "해당없음" },
};

export interface RunbookGateBarProps {
  report: SongTimelineConceptReport | undefined;
}

export function RunbookGateBar({ report }: RunbookGateBarProps) {
  const tally = gateTally(report);
  const rows = gateRows(report);

  return (
    <section className="runbook-gate" aria-label="상태줄 GATE">
      <div className="runbook-gate-line">
        <span className="runbook-gate-title">GATE</span>
        {tally === null ? (
          <span className="runbook-gate-missing">
            {report && !report.available && report.reason ? report.reason : NO_DATA}
          </span>
        ) : (
          <>
            {(["pass", "fail", "na"] as const).map((verdict) => (
              <span className={`runbook-gate-badge is-${verdict}`} key={verdict}>
                {VERDICT_LABEL[verdict].mark} {VERDICT_LABEL[verdict].text} {tally[verdict]}
              </span>
            ))}
            <span className="runbook-gate-badge is-nodata">! 경고 · {NO_DATA}</span>
          </>
        )}
      </div>
      {rows.length > 0 && (
        <details className="runbook-gate-detail">
          <summary>GATE 상세 보기 ▼</summary>
          <table>
            <thead>
              <tr>
                <th>판정</th>
                <th>게이트</th>
                <th>근거 — 실제 값</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.name}>
                  <td className={`runbook-gate-verdict is-${row.verdict}`}>
                    {VERDICT_LABEL[row.verdict].mark} {VERDICT_LABEL[row.verdict].text}
                  </td>
                  <td>{row.name}</td>
                  <td>{row.detail}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </details>
      )}
    </section>
  );
}
