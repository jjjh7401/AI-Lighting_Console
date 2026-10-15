// 편집 창 「이 구간 왼쪽·오른쪽 따로」 토글 — 펼침 줄과 같은 상태·같은 갱신 규칙
// (`lrSplitToggleControl`). SPEC-LDBEAT-001 M9, 편집 창 버튼 연결.
//
// 여기서는 React 를 띄우지 않는다. 갱신 함수(updater)를 붙잡아 빈 선언에 직접
// 적용해 보는 방식으로 「누르면 무엇이 선언·해제되는가」만 고정한다.
import { describe, expect, it } from "vitest";

import {
  lrSplitToggleControl,
  type LRSplitDeclarations,
  type LRSplitStage,
  type LRSplitToggleControl,
} from "./lrSplit";

// 좌(x 음수)·우(x 양수) 장비가 모두 있는 그룹 — 분리 가능.
const SPLITTABLE: LRSplitStage = {
  fixtures: [
    { fid: 1, x: -10 },
    { fid: 2, x: 10 },
  ],
  groups: [{ group_name: "FOOBAR", member_fids: [1, 2], complete: true }],
};
const SIDE_TRACK = { layer_role: "side", group_name: "FOOBAR" };
const SEGMENT = { startBar: 4, endBar: 9 };

function must(control: LRSplitToggleControl | null): LRSplitToggleControl {
  if (control === null) throw new Error("토글이 null 이면 안 되는 자리다");
  return control;
}

/** 갱신 함수를 붙잡아 두었다가, 주어진 선언에 마지막 갱신을 적용해 본다. */
function captureUpdate() {
  const updaters: Array<(prev: LRSplitDeclarations) => LRSplitDeclarations> = [];
  return {
    update: (updater: (prev: LRSplitDeclarations) => LRSplitDeclarations) => {
      updaters.push(updater);
    },
    apply: (declarations: LRSplitDeclarations): LRSplitDeclarations => {
      const last = updaters[updaters.length - 1];
      if (last === undefined) throw new Error("갱신 함수가 없다");
      return last(declarations);
    },
  };
}

describe("lrSplitToggleControl — 편집 창 L·R 토글", () => {
  it("구간이 없으면 null 이다(버튼 비활성)", () => {
    const control = lrSplitToggleControl({
      track: SIDE_TRACK,
      stage: SPLITTABLE,
      segment: undefined,
      declarations: new Map(),
      update: () => undefined,
    });
    expect(control).toBeNull();
  });

  it("옆빛이 아니면 null 이다", () => {
    const control = lrSplitToggleControl({
      track: { layer_role: "mover", group_name: "FOOBAR" },
      stage: SPLITTABLE,
      segment: SEGMENT,
      declarations: new Map(),
      update: () => undefined,
    });
    expect(control).toBeNull();
  });

  it("좌우 한쪽에만 장비가 있으면 분리 불가라 null 이다(지어내지 않는다)", () => {
    const oneSided: LRSplitStage = {
      fixtures: [
        { fid: 1, x: -10 },
        { fid: 2, x: -10 },
        // 그룹 밖 장비 — 무대 중심(전체 장비 가운데)을 0 으로 밀어, 그룹은 왼쪽에만 있게 한다.
        { fid: 3, x: 10 },
      ],
      groups: [{ group_name: "FOOBAR", member_fids: [1, 2], complete: true }],
    };
    const control = lrSplitToggleControl({
      track: SIDE_TRACK,
      stage: oneSided,
      segment: SEGMENT,
      declarations: new Map(),
      update: () => undefined,
    });
    expect(control).toBeNull();
  });

  it("아직 안 갈랐으면 isSplit=false 이고, 누르면 이 구간을 선언한다", () => {
    const { update, apply } = captureUpdate();
    const control = must(
      lrSplitToggleControl({
        track: SIDE_TRACK,
        stage: SPLITTABLE,
        segment: SEGMENT,
        declarations: new Map(),
        update,
      }),
    );
    expect(control.isSplit).toBe(false);
    control.onToggle();
    expect(apply(new Map()).get("FOOBAR")).toEqual({ startBar: 4, endBar: 9 });
  });

  it("이미 갈라졌으면 isSplit=true 이고, 누르면 선언을 지운다(다시 합치기)", () => {
    const declared: LRSplitDeclarations = new Map([["FOOBAR", SEGMENT]]);
    const { update, apply } = captureUpdate();
    const control = must(
      lrSplitToggleControl({
        track: SIDE_TRACK,
        stage: SPLITTABLE,
        segment: SEGMENT,
        declarations: declared,
        update,
      }),
    );
    expect(control.isSplit).toBe(true);
    control.onToggle();
    expect(apply(declared).has("FOOBAR")).toBe(false);
  });

  it("선언에는 구간의 시작·끝 마디만 담는다(구간 객체의 다른 필드는 새지 않는다)", () => {
    const { update, apply } = captureUpdate();
    const segmentWithCue = { startBar: 4, endBar: 9, cue: null };
    const control = must(
      lrSplitToggleControl({
        track: SIDE_TRACK,
        stage: SPLITTABLE,
        segment: segmentWithCue,
        declarations: new Map(),
        update,
      }),
    );
    control.onToggle();
    expect(apply(new Map()).get("FOOBAR")).toEqual({ startBar: 4, endBar: 9 });
  });

  it("갱신은 렌더 시점의 선언을 바꾸지 않고 새 Map 을 돌려준다", () => {
    const declared: LRSplitDeclarations = new Map([["FOOBAR", SEGMENT]]);
    const { update, apply } = captureUpdate();
    const control = must(
      lrSplitToggleControl({
        track: SIDE_TRACK,
        stage: SPLITTABLE,
        segment: SEGMENT,
        declarations: declared,
        update,
      }),
    );
    control.onToggle();
    const next = apply(declared);
    expect(next).not.toBe(declared);
    expect(declared.has("FOOBAR")).toBe(true);
  });
});
