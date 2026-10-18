// @vitest-environment jsdom
// 칸 단위 반영·여러 칸 편집을 실제로 소켓에 싣는 길 시험(카드 WT-cell-apply). 가짜 WebSocket 으로 훅이 내보내는
// 프레임을 그대로 본다. 특히 빈 칸 목록이 곡 전체 반영으로 새지 않는지 못박는다 — 프레임에서 빈 `cells` 는 빠지므로
// 가드가 없으면 「칸 단위 반영」을 눌렀는데 곡 전체가 콘솔에 나간다.
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { buildBeatGridApply, buildBeatGridEditCells } from "./protocol";
import { useCopilotSocket, type CopilotSocket } from "./useCopilotSocket";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

/** 보낸 프레임만 모으는 가짜 소켓. 만들자마자 열린 것으로 친다. */
class FakeSocket {
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSING = 2;
  static readonly CLOSED = 3;
  static instances: FakeSocket[] = [];
  readyState = FakeSocket.OPEN;
  sent: string[] = [];
  onopen: (() => void) | null = null;
  onmessage: ((message: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  constructor(
    public url: string,
    public protocols?: string | string[],
  ) {
    FakeSocket.instances.push(this);
  }
  send(frame: string) {
    this.sent.push(frame);
  }
  close() {
    this.readyState = FakeSocket.CLOSED;
  }
}

let container: HTMLElement;
let root: Root;
let socket: CopilotSocket;

function Harness() {
  socket = useCopilotSocket("ws://test.invalid/ws");
  return null;
}

beforeEach(() => {
  FakeSocket.instances = [];
  vi.stubGlobal("WebSocket", FakeSocket);
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
  act(() => root.render(<Harness />));
});

afterEach(() => {
  act(() => root.unmount());
  container.remove();
  vi.unstubAllGlobals();
});

/** 지금까지 이 소켓이 내보낸 프레임 가운데 `beat_grid_*` 만. */
const beatGridFrames = () => FakeSocket.instances[0].sent.filter((frame) => frame.includes('"type":"beat_grid_'));

describe("sendBeatGridApplyCells", () => {
  it("칸이 있으면 cells 를 실은 beat_grid_apply 하나를 보낸다", () => {
    const cells: [string, number][] = [
      ["BACK", 1],
      ["FOH", 3],
    ];
    act(() => socket.sendBeatGridApplyCells(cells));
    expect(beatGridFrames()).toEqual(['{"v":1,"type":"beat_grid_apply","cells":[["BACK",1],["FOH",3]]}']);
  });

  it("빈 목록은 아무것도 보내지 않는다 — 곡 전체 반영 프레임으로 새지 않는다", () => {
    act(() => socket.sendBeatGridApplyCells([]));
    expect(beatGridFrames()).toEqual([]);
    // 대조군: 같은 빈 목록을 빌더에 그대로 넘기면 전체 반영 프레임이 된다 — 그래서 위 가드가 필요하다.
    expect(buildBeatGridApply(undefined, [])).toBe('{"v":1,"type":"beat_grid_apply"}');
  });

  it("예전 전체 반영 sendBeatGridApply 는 그대로 cells 없는 프레임이다", () => {
    act(() => socket.sendBeatGridApply());
    expect(beatGridFrames()).toEqual(['{"v":1,"type":"beat_grid_apply"}']);
  });
});

describe("sendBeatGridEditCells", () => {
  const changes = { brightness: { mode: "value", value_percent: 60, preset_no: null } };

  it("고른 칸 전부를 한 메시지로 보낸다 — 칸마다 보내지 않는다", () => {
    const cells: [string, number][] = [
      ["BACK", 1],
      ["BACK", 2],
      ["FOH", 3],
    ];
    act(() => socket.sendBeatGridEditCells(cells, changes));
    expect(beatGridFrames()).toEqual([buildBeatGridEditCells(cells, changes)]);
  });

  it("빈 목록은 보내지 않는다", () => {
    act(() => socket.sendBeatGridEditCells([], changes));
    expect(beatGridFrames()).toEqual([]);
  });

  it("한 칸 편집 sendBeatGridEdit 는 그대로 bar+target 이다", () => {
    act(() => socket.sendBeatGridEdit(7, "BACK", changes));
    expect(beatGridFrames()).toEqual([
      '{"v":1,"type":"beat_grid_edit","bar":7,"target":"BACK","changes":{"brightness":{"mode":"value","value_percent":60,"preset_no":null}}}',
    ]);
  });
});
