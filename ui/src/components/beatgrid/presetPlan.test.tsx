import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { buildBeatGridApply } from "../../protocol";
import { BeatGridTopBar } from "../BeatGridTopBar";
import { PresetPlanButton, PresetPlanPanel } from "./PresetPlanPanel";
import { PRESET_PLAN_SUMMARY, parsePresetPlan } from "./presetPlan";

const TABLE = [
  "| 만들 프리셋 | 값 | 후보 번호 | 칸 수 | 상태 |",
  "|---|---|---|---|---|",
  "| DIM 40 | 40% | 5.1 | 3 | 저장(이 카드) |",
  "| COL Red | RGB 100 0 0 | 6.2 | 2 | 이 카드 밖 |",
  "| POS Floor | 바닥 쪽 (대략: 틸트 -20) | 7.1 | 1 | 이 카드 밖 |",
  "",
  "**이 카드 밖**",
  "- COL Red RGB 100 0 0(칸 2개, 후보 6.2): 색 저장은 기존 경로로 만든다",
  "",
  "**미정(이번 계획에서 제외)**",
  "- SCENE 메모 3마디: 계획 밖",
  "",
  "**감독이 고칠 값**",
  "- DIM 40 의 그룹 'A' 디머 속성을 얻지 못해 기본값을 쓴다. 감독이 고칠 값: 확인",
].join("\n");

describe("필요한 프리셋 만들기", () => {
  it("버튼은 정확히 mode: preset_plan 을 보내고, 기존 반영 메시지는 그대로다", () => {
    expect(JSON.parse(buildBeatGridApply("preset_plan"))).toEqual({
      v: 1,
      type: "beat_grid_apply",
      mode: "preset_plan",
    });
    expect(JSON.parse(buildBeatGridApply())).toEqual({
      v: 1,
      type: "beat_grid_apply",
    });
  });

  it("상단 바에는 프리셋 계획 버튼이 없다 — 한 줄을 지킨다", () => {
    const html = renderToStaticMarkup(
      <BeatGridTopBar
        songTitle="곡"
        versionLabel={null}
        bpm={100}
        currentBar={0}
        barRange={{ start: 0, end: 4 }}
        onBarChange={() => {}}
        onDrawerToggle={() => {}}
        onApply={() => {}}
      />,
    );
    expect(html).not.toContain("프리셋 계획");
  });

  it("서랍 머리의 버튼이 눌리면 콜백을 부른다", () => {
    let clicked = 0;
    const el = PresetPlanButton({ onClick: () => (clicked += 1) });
    expect(renderToStaticMarkup(el)).toContain("프리셋 계획 만들기");
    el.props.onClick();
    expect(clicked).toBe(1);
  });

  it("계획표 행·종류·표식·제외 항목을 읽고 그린다", () => {
    expect(PRESET_PLAN_SUMMARY).toBe("연출 프리셋 계획");
    const plan = parsePresetPlan(TABLE);
    expect(plan).not.toBeNull();
    expect(
      plan?.rows.map((r) => [r.kind, r.slot, r.name, r.cellCount]),
    ).toEqual([
      ["dimmer", "5.1", "DIM 40", 3],
      ["color", "6.2", "COL Red", 2],
      ["position", "7.1", "POS Floor", 1],
    ]);
    expect(plan?.rows.map((r) => r.needsSupervisor)).toEqual([
      true,
      false,
      false,
    ]);
    const html = renderToStaticMarkup(<PresetPlanPanel plan={plan!} />);
    expect(html).toContain("DIM 40");
    expect(html).toContain("디머");
    expect(html).toContain("preset-plan-mark");
    expect(html).toContain("제외 · 이 카드 밖");
    expect(html).toContain("SCENE 메모 3마디");
  });

  it("표가 없는 답은 계획표가 아니다", () => {
    expect(parsePresetPlan("그냥 답")).toBeNull();
  });
});
