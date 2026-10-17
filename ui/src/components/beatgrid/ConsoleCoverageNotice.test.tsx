// 콘솔 장비가 배치에서 빠지면 이유와 함께 보인다(카드 WT-all-fixtures) — 정적 렌더로 단언한다.
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { BeatGridConsoleCoverage } from "../../protocol";
import { ConsoleCoverageNotice } from "./ConsoleCoverageNotice";

const SMOKE = "일부러 뺌: 연기 장비(연출 대상 아님)";
const NO_GROUP = "어느 콘솔 그룹에도 들어 있지 않아 줄을 만들 수 없습니다";

describe("ConsoleCoverageNotice", () => {
  it("빠진 장비를 그룹·장비 번호·이유와 함께 크게 보인다", () => {
    const coverage: BeatGridConsoleCoverage = {
      added: ["KEY"],
      uncovered: [{ fid: 999, group_names: [], reason: NO_GROUP, intentional: false }],
      unread: [],
    };
    const html = renderToStaticMarkup(<ConsoleCoverageNotice coverage={coverage} />);
    expect(html).toContain('role="alert"');
    expect(html).toContain("콘솔 장비 1대가 마디 배치에 없어요");
    expect(html).toContain(`그룹 없음 · 999 — ${NO_GROUP}`);
    expect(html).toContain("콘솔 그룹으로 줄을 붙였어요: KEY");
  });

  it("일부러 뺀 장비(연기 장비)는 경고가 아니라 안내로 따로 보인다", () => {
    const coverage: BeatGridConsoleCoverage = {
      added: [],
      uncovered: [
        { fid: 621, group_names: ["HAZE"], reason: SMOKE, intentional: true },
        { fid: 622, group_names: ["HAZE"], reason: SMOKE, intentional: true },
      ],
      unread: [],
    };
    const html = renderToStaticMarkup(<ConsoleCoverageNotice coverage={coverage} />);
    expect(html).toContain('role="status"');
    expect(html).not.toContain("마디 배치에 없어요");
    expect(html).toContain(`일부러 뺀 장비 · HAZE · 621, 622 — ${SMOKE}`);
  });

  it("못 읽은 것이 있으면 그것도 보인다(다 들어갔다고 말하지 않는다)", () => {
    const html = renderToStaticMarkup(
      <ConsoleCoverageNotice coverage={{ added: [], uncovered: [], unread: ["콘솔 그룹을 하나도 읽지 못했습니다"] }} />,
    );
    expect(html).toContain('role="alert"');
    expect(html).toContain("콘솔 그룹을 하나도 읽지 못했습니다");
  });

  it("다 들어갔고 붙인 줄도 없으면 아무것도 그리지 않는다", () => {
    expect(renderToStaticMarkup(<ConsoleCoverageNotice coverage={{ added: [], uncovered: [], unread: [] }} />)).toBe("");
    expect(renderToStaticMarkup(<ConsoleCoverageNotice coverage={undefined} />)).toBe("");
  });
});
