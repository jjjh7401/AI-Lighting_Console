// @vitest-environment jsdom
// 곡 음원 링크 요청의 발동 조건 — 불러오기로 최상위 `song_title` 이 바뀌면 다시 요청한다.
//
// 불러오기(`POST /api/timelines/{id}/load`)는 `timeline.song_title` 을 라이브러리 이름으로
// 바꾼다. 요청 효과가 `beat_grid.song_title` 만 보면 두 값이 어긋난 채로 요청이 다시 가지 않는다.
// App() 전체는 무거워 그릴 수 없으므로(파일 App.test.tsx 머리말), 효과를 담은
// `useSongAudioLinkRequest` 를 작은 하네스로 그려 `send` 호출 횟수를 잰다(소켓은 목).
import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useSongAudioLinkRequest } from "./App";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

type HarnessProps = {
  active: boolean;
  hasSessionFile: boolean;
  songTitle: string | null;
  beatGridSongTitle: string | null;
  send: () => void;
};

function Harness(props: HarnessProps) {
  useSongAudioLinkRequest(props);
  return null;
}

let container: HTMLElement;
let root: Root;

beforeEach(() => {
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(() => {
  act(() => root.unmount());
  container.remove();
});

function render(props: HarnessProps) {
  act(() => root.render(createElement(Harness, props)));
}

describe("changing the top-level song_title re-requests the song audio link", () => {
  it("최상위 song_title 만 바뀌어도(beat_grid.song_title 은 그대로) 다시 요청한다", () => {
    const send = vi.fn();
    const base = { active: true, hasSessionFile: false, beatGridSongTitle: "OLD", send };
    render({ ...base, songTitle: "OLD" });
    // 대조군: 처음 열 때 한 번 요청한다.
    expect(send).toHaveBeenCalledTimes(1);

    render({ ...base, songTitle: "NEW" });
    expect(send).toHaveBeenCalledTimes(2);
  });

  it("제목이 그대로면 다시 요청하지 않는다", () => {
    const send = vi.fn();
    const props = {
      active: true,
      hasSessionFile: false,
      songTitle: "SAME",
      beatGridSongTitle: "SAME",
      send,
    };
    render(props);
    render({ ...props });
    expect(send).toHaveBeenCalledTimes(1);
  });

  it("세션 첨부가 있으면 제목이 바뀌어도 요청하지 않는다", () => {
    const send = vi.fn();
    const base = { active: true, hasSessionFile: true, beatGridSongTitle: "OLD", send };
    render({ ...base, songTitle: "OLD" });
    render({ ...base, songTitle: "NEW" });
    expect(send).not.toHaveBeenCalled();
  });

  it("전체화면이 닫혀 있으면 요청하지 않는다", () => {
    const send = vi.fn();
    render({
      active: false,
      hasSessionFile: false,
      songTitle: "A",
      beatGridSongTitle: "A",
      send,
    });
    expect(send).not.toHaveBeenCalled();
  });
});
