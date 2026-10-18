// 칸 단위 반영·여러 칸 편집의 와이어 모양(카드 WT-cell-apply, SPEC-LDRHYTHM-001) — 보내는 프레임과 받는 응답.
//
// 서버 계약: `beat_grid_apply` 는 선택 필드 `cells` 를 받고, 없으면 예전 곡 전체 반영이다. `beat_grid_edit` 는
// `bar`+`target` 대신 `cells` 로 주소를 줄 수 있다(둘 중 하나). 칸 단위 반영이 성공하면 `beat_grid_send_status` 에
// `subset`(+ 무엇을 기준으로 보냈는지 `baseline`)이 실린다. 타임라인 프레임의 `beat_grid.partial_baseline` 은 칸 단위
// 반영이 무엇을 기준으로 삼는지(`snapshot`·`record`·`null`)를 말한다. 리듀서는 상태 응답의 필드를 하나씩 옮기므로
// `subset` 이 조용히 버려지지 않는지 여기서 못박는다(타임라인은 통째로 보관된다).
import { describe, expect, it } from "vitest";

import {
  buildBeatGridApply,
  buildBeatGridEdit,
  buildBeatGridEditCells,
  initialState,
  parseServerEvent,
  reduceServerEvent,
  type ServerEvent,
} from "./protocol";

function event(fields: Record<string, unknown>): ServerEvent {
  const parsed = parseServerEvent(JSON.stringify({ v: 1, ...fields }));
  if (parsed === null) throw new Error("fixture did not parse");
  return parsed;
}

describe("buildBeatGridApply — cells", () => {
  it("cells 가 없으면 예전과 바이트가 같다", () => {
    expect(buildBeatGridApply()).toBe('{"v":1,"type":"beat_grid_apply"}');
    expect(buildBeatGridApply("preset_plan")).toBe('{"v":1,"type":"beat_grid_apply","mode":"preset_plan"}');
    expect(buildBeatGridApply(undefined, undefined)).toBe('{"v":1,"type":"beat_grid_apply"}');
  });

  it("cells 가 비어 있어도 키를 싣지 않는다 — 비면 예전 전체 반영과 같다", () => {
    expect(buildBeatGridApply(undefined, [])).toBe('{"v":1,"type":"beat_grid_apply"}');
    expect(buildBeatGridApply("preset_plan", [])).toBe('{"v":1,"type":"beat_grid_apply","mode":"preset_plan"}');
  });

  it("비지 않은 cells 는 [줄 이름, 마디] 쌍 그대로 싣는다", () => {
    const frame = buildBeatGridApply(undefined, [
      ["BACK", 1],
      ["FOH", 3],
    ]);
    expect(frame).toBe('{"v":1,"type":"beat_grid_apply","cells":[["BACK",1],["FOH",3]]}');
    expect(JSON.parse(frame)).toEqual({
      v: 1,
      type: "beat_grid_apply",
      cells: [
        ["BACK", 1],
        ["FOH", 3],
      ],
    });
  });

  it("cells 프레임에는 mode 키가 없다 — 서버는 mode 'apply' 에서만 cells 를 받는다", () => {
    expect("mode" in JSON.parse(buildBeatGridApply(undefined, [["BACK", 1]]))).toBe(false);
  });
});

describe("buildBeatGridEditCells", () => {
  const changes = { brightness: { mode: "value", value_percent: 60, preset_no: null } };

  it("cells 와 changes 만 싣는다 — bar·target 은 없다(주소는 한 가지만)", () => {
    const frame = buildBeatGridEditCells(
      [
        ["BACK", 1],
        ["BACK", 2],
      ],
      changes,
    );
    expect(frame).toBe(
      '{"v":1,"type":"beat_grid_edit","cells":[["BACK",1],["BACK",2]],"changes":{"brightness":{"mode":"value","value_percent":60,"preset_no":null}}}',
    );
    const parsed = JSON.parse(frame);
    expect("bar" in parsed).toBe(false);
    expect("target" in parsed).toBe(false);
  });

  it("한 칸 편집(bar+target)은 그대로다 — cells 키가 없다", () => {
    const single = JSON.parse(buildBeatGridEdit(11, "MOVER-U", changes));
    expect(single).toEqual({ v: 1, type: "beat_grid_edit", bar: 11, target: "MOVER-U", changes });
    expect("cells" in single).toBe(false);
  });
});

describe("beat_grid_send_status — subset", () => {
  const base = {
    type: "beat_grid_send_status",
    pending_apply_count: 2,
    last_action: "apply",
    ok: true,
    reason: null,
    blocked_cells: [],
    approval_vs_sent: null,
  };
  const subset = {
    requested: 3,
    applied: [
      ["BACK", 1],
      ["FOH", 3],
    ],
    not_applied: [{ group_name: "BACK", bar: 2, reason: "콘솔과 같음" }],
  };

  it("서버가 실은 subset 을 리듀서가 그대로 옮긴다 — 조용히 버리지 않는다", () => {
    const next = reduceServerEvent(initialState, event({ ...base, subset }));
    expect(next.beatGridSendStatus?.subset).toEqual(subset);
  });

  it("subset 이 없는 응답에는 키 자체가 없다 — 전체 반영과 구분되고 기존 상태 모양이 그대로다", () => {
    const next = reduceServerEvent(initialState, event(base));
    expect(next.beatGridSendStatus).not.toBeNull();
    expect("subset" in (next.beatGridSendStatus ?? {})).toBe(false);
  });

  it("다음 응답에 subset 이 없으면 앞 응답의 subset 이 남지 않는다(최신 응답으로 교체)", () => {
    const withSubset = reduceServerEvent(initialState, event({ ...base, subset }));
    const preview = reduceServerEvent(withSubset, event({ ...base, last_action: "preview" }));
    expect(preview.beatGridSendStatus?.last_action).toBe("preview");
    expect("subset" in (preview.beatGridSendStatus ?? {})).toBe(false);
  });

  it("subset.baseline(snapshot·record)도 그대로 옮긴다 — 지운 값 주의를 말하는 근거다", () => {
    for (const baseline of ["snapshot", "record"] as const) {
      const next = reduceServerEvent(initialState, event({ ...base, subset: { ...subset, baseline } }));
      expect(next.beatGridSendStatus?.subset?.baseline).toBe(baseline);
      expect(next.beatGridSendStatus?.subset).toEqual({ ...subset, baseline });
    }
  });

  it("baseline 을 안 실은 옛 응답에는 baseline 키가 없다 — 지어내지 않는다", () => {
    const next = reduceServerEvent(initialState, event({ ...base, subset }));
    expect("baseline" in (next.beatGridSendStatus?.subset ?? {})).toBe(false);
  });
});

describe("song_timeline — beat_grid.partial_baseline", () => {
  const timelineWith = (grid: Record<string, unknown>) => ({
    type: "song_timeline",
    timeline: {
      song_title: "LOVE ATTACK",
      beat_grid: { song_title: "LOVE ATTACK", bar_range: { start: 0, end: 25 }, tracks: [], ...grid },
    },
  });

  it("서버가 모든 타임라인 프레임에 싣는 partial_baseline 을 격자째 그대로 보존한다", () => {
    for (const [baseline, unsent] of [
      ["snapshot", []],
      ["record", null],
      [null, null],
    ] as const) {
      const next = reduceServerEvent(
        initialState,
        event(timelineWith({ unsent_cells: unsent, partial_baseline: baseline })),
      );
      const grid = next.songTimeline.timeline?.beat_grid;
      expect(grid?.partial_baseline).toBe(baseline);
      expect(grid?.unsent_cells).toEqual(unsent);
    }
  });

  it("옛 서버 응답(필드 없음)에서는 partial_baseline 이 없다 — 지어내지 않는다", () => {
    const next = reduceServerEvent(initialState, event(timelineWith({ unsent_cells: [] })));
    expect("partial_baseline" in (next.songTimeline.timeline?.beat_grid ?? {})).toBe(false);
  });

  it("부분 칸 기록일 때만 오는 known_cells 를 [줄 이름, 마디] 쌍 그대로 보존하고, 없으면 키를 만들지 않는다", () => {
    const known = [
      ["BACK", 1],
      ["FOH", 3],
    ];
    const partial = reduceServerEvent(
      initialState,
      event(timelineWith({ unsent_cells: [{ group_name: "BACK", bar: 1 }], known_cells: known, partial_baseline: "snapshot" })),
    );
    expect(partial.songTimeline.timeline?.beat_grid?.known_cells).toEqual(known);
    // 전체 기록이 되면 서버는 키를 싣지 않는다 — 앞 프레임의 목록이 남지 않는다(최신 프레임으로 교체).
    const full = reduceServerEvent(
      partial,
      event(timelineWith({ unsent_cells: [], partial_baseline: "snapshot" })),
    );
    expect("known_cells" in (full.songTimeline.timeline?.beat_grid ?? {})).toBe(false);
  });

  it("다음 타임라인 프레임이 기준을 바꾸면 최신 값으로 바뀐다", () => {
    const first = reduceServerEvent(initialState, event(timelineWith({ unsent_cells: null, partial_baseline: "record" })));
    const second = reduceServerEvent(first, event(timelineWith({ unsent_cells: [], partial_baseline: "snapshot" })));
    expect(second.songTimeline.timeline?.beat_grid?.partial_baseline).toBe("snapshot");
  });
});
