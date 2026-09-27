// t472 — 런북 MIB 칸에 조립기의 「켜진 채 이동」 경고(t471 live_move)를 띄운다.
// 서버가 사전이동 구간에 dark_window_seconds·live_move 를 싣는다(session.py).
// 경고가 없으면 두 경로(bool 표기·컨셉 3상태 기호) 모두 지금과 글자 그대로다.
import { describe, expect, it } from "vitest";

import type { SongTimelineConceptReport, SongTimelineSection, SongTimelineView } from "../protocol";
import serverPayload from "./runbookServerPayload.json";
import { conceptBySection, conceptCells, liveMoveWarning, mibCellText } from "./runbookM7";

const TIMELINE = serverPayload as unknown as SongTimelineView;
const REPORT = TIMELINE.concept_report as SongTimelineConceptReport;
const SECTIONS = TIMELINE.sections;
const BASE = SECTIONS[0];

const liveMove = (seconds: number): SongTimelineSection => ({
  ...BASE,
  mib: true,
  dark_window_seconds: seconds,
  live_move: true,
});

describe("live_move 경고 문구", () => {
  it("어둠 길이를 초로 적는다", () => {
    expect(liveMoveWarning(liveMove(2.07))).toBe("⚠ 어둠 2.07초 — 켜진 채 이동");
    expect(liveMoveWarning(liveMove(2))).toBe("⚠ 어둠 2초 — 켜진 채 이동");
  });

  it("경고가 아니면 null 이다", () => {
    expect(liveMoveWarning({ ...BASE, mib: true, dark_window_seconds: 10, live_move: false })).toBe(
      null,
    );
    expect(liveMoveWarning({ ...BASE, mib: true })).toBe(null);
  });
});

describe("bool 표기 경로(컨셉 짝 없음)", () => {
  it("켜진 채 이동이면 경고를 띄운다", () => {
    expect(mibCellText(liveMove(2.07))).toBe("⚠ 어둠 2.07초 — 켜진 채 이동");
  });

  it("어둠이 충분하면 지금과 같다", () => {
    expect(
      mibCellText({ ...BASE, mib: true, dark_window_seconds: 10, live_move: false }),
    ).toBe("사전이동 있음");
  });
});

describe("컨셉 3상태 경로(짝 있음)", () => {
  it("기호 뒤에 경고를 덧붙인다", () => {
    const concept = conceptBySection(REPORT, SECTIONS.length);
    const cells = conceptCells(concept![0], liveMove(2.07));
    expect(cells.mib).toBe("◐ dark ⚠ 어둠 2.07초 — 켜진 채 이동");
  });

  it("경고가 없으면 기호만 — 지금과 같다", () => {
    const concept = conceptBySection(REPORT, SECTIONS.length);
    expect(conceptCells(concept![0], SECTIONS[0]).mib).toBe("◐ dark");
  });
});
