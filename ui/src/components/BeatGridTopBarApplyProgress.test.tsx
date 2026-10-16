// 상단 바 「⇪ 콘솔에 반영」 진행 문구 시험 (SPEC-LDRHYTHM-001, 카드 apply-latency).
// 마크업은 `renderToStaticMarkup`으로 문자열을 단언한다(BeatGridTopBar.test.tsx 와 같은 방식).
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { BeatGridTopBar } from "./BeatGridTopBar";

const noop = () => {};

function renderTopBar(overrides: Partial<Parameters<typeof BeatGridTopBar>[0]> = {}) {
  return renderToStaticMarkup(
    <BeatGridTopBar
      songTitle="가짜 곡"
      versionLabel="초안"
      bpm={98.5}
      currentBar={3}
      barRange={{ start: 0, end: 9 }}
      onBarChange={noop}
      onDrawerToggle={noop}
      onApply={noop}
      {...overrides}
    />,
  );
}

describe("상단 바 — 「⇪ 콘솔에 반영」 진행 문구", () => {
  it("진행 문구가 없으면 진행 표시를 그리지 않는다", () => {
    expect(renderTopBar()).not.toContain("beat-grid-apply-progress");
  });

  it("진행 문구가 있으면 반영 버튼 곁에 상태 알림으로 보인다", () => {
    const markup = renderTopBar({ applyProgress: "콘솔을 읽는 중 · 12초" });
    expect(markup).toContain('class="beat-grid-apply-progress"');
    expect(markup).toContain('role="status"');
    expect(markup).toContain("콘솔을 읽는 중 · 12초");
  });
});
