// 상단 바 「장비 다시 읽기」 버튼 (리드 재측정 뒤, 2026-10-19). 콜백을 넘길 때만 그리고,
// 누르면 콘솔에 쓰지 않는 읽기 메시지(`beat_grid_rig_refresh`, 페이로드 없음)가 나간다.
// 마크업은 `renderToStaticMarkup`으로 단언한다(BeatGridTopBar.test.tsx 와 같은 방식).
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { buildBeatGridRigRefresh } from "../protocol";
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
      {...overrides}
    />,
  );
}

describe("상단 바 — 장비 다시 읽기 버튼", () => {
  it("콜백을 넘기면 버튼을 그리고, 넘기지 않으면 그리지 않는다", () => {
    expect(renderTopBar({ onRigRefresh: noop })).toContain("장비 다시 읽기");
    expect(renderTopBar()).not.toContain("장비 다시 읽기");
  });

  it("버튼 설명은 콘솔에 쓰지 않는다고 말한다", () => {
    expect(renderTopBar({ onRigRefresh: noop })).toContain("콘솔에는 쓰지 않습니다");
  });
});

describe("프로토콜 — 장비 다시 읽기 메시지", () => {
  it("페이로드 없이 beat_grid_rig_refresh 를 만든다", () => {
    expect(JSON.parse(buildBeatGridRigRefresh())).toEqual({
      v: expect.any(Number),
      type: "beat_grid_rig_refresh",
    });
  });
});
