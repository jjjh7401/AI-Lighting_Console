// 콘솔 장비가 마디 배치에서 빠졌다는 알림 — 카드 WT-all-fixtures(감독 2026-10-18).
// 「조명장비가 있는데 마디 배치에 넣지 않는게 말이 돼?」 — 서버가 콘솔 그룹·소속 장비와 배치 줄을 대조한 결과
// (`console_coverage`)를 그대로 보인다. 이유는 서버가 붙인 문장 그대로다(화면이 짐작하지 않는다).
// 일부러 뺀 장비(연기 장비 — 감독 「이건 조명연출이 아니라 … 연기를 만드는 장비야」)는 경고가 아니라 안내다.
import type { BeatGridConsoleCoverage, BeatGridUncoveredFixture } from "../../protocol";

/** 같은 그룹·같은 이유로 빠진 장비를 한 줄로 묶는다. */
function groupUncovered(uncovered: BeatGridUncoveredFixture[]) {
  const rows = new Map<string, { label: string; reason: string; fids: number[] }>();
  for (const entry of uncovered) {
    const label = entry.group_names.length > 0 ? entry.group_names.join("·") : "그룹 없음";
    const key = `${label}\u0000${entry.reason}`;
    const row = rows.get(key) ?? { label, reason: entry.reason, fids: [] };
    row.fids.push(entry.fid);
    rows.set(key, row);
  }
  return [...rows.values()];
}

export function ConsoleCoverageNotice({ coverage }: { coverage: BeatGridConsoleCoverage | null | undefined }) {
  if (!coverage) return null;
  const { added, uncovered, unread } = coverage;
  const missing = uncovered.filter((entry) => !entry.intentional);
  const intentional = uncovered.filter((entry) => entry.intentional);
  if (added.length === 0 && uncovered.length === 0 && unread.length === 0) return null;
  const alert = missing.length > 0 || unread.length > 0;
  return (
    <div className="beat-grid-console-coverage" role={alert ? "alert" : "status"}>
      {missing.length > 0 && <strong>⚠ 콘솔 장비 {missing.length}대가 마디 배치에 없어요</strong>}
      {(missing.length > 0 || unread.length > 0) && (
        <ul>
          {groupUncovered(missing).map((row) => (
            <li key={`${row.label}-${row.reason}`}>
              {row.label} · {row.fids.join(", ")} — {row.reason}
            </li>
          ))}
          {unread.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      )}
      {intentional.length > 0 && (
        <ul>
          {groupUncovered(intentional).map((row) => (
            <li key={`${row.label}-${row.reason}`}>
              일부러 뺀 장비 · {row.label} · {row.fids.join(", ")} — {row.reason}
            </li>
          ))}
        </ul>
      )}
      {added.length > 0 && <p>콘솔 그룹으로 줄을 붙였어요: {added.join(", ")}</p>}
    </div>
  );
}
