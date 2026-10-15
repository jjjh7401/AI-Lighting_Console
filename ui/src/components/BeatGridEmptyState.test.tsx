// 박자 격자가 없을 때의 빈 화면 — 안내 문구와 「돌아가기」 버튼이 보이는지 잰다.
// 이 프로젝트는 jsdom 이 없어 `renderToStaticMarkup` 으로 글자만 본다
// (BeatGridEmptyPreset.test.tsx 와 같은 방식).
import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

import { BeatGrid } from "./BeatGrid";
import type { BeatGridView } from "../protocol";

const NO_DEFAULT_NOTE = "이 곡의 기본값 없음";

// 트랙이 비어 있는 격자 — 서버가 기본값 없는 곡에 빈 트랙과 안내를 붙여 보내는 모양.
function emptyTracksGrid(): BeatGridView {
  return {
    song_title: "시험 곡",
    bar_range: { start: 0, end: 25 },
    tracks: [],
    scene_memos: [],
    probe_results: [],
    source: "empty",
    note: NO_DEFAULT_NOTE,
    console_audio_offset_seconds: 0,
  } as unknown as BeatGridView;
}

describe("박자 격자 빈 화면", () => {
  it("격자가 없으면 안내 문구와 돌아가기 버튼을 보인다", () => {
    const html = renderToStaticMarkup(<BeatGrid grid={null} onExit={() => {}} />);
    expect(html).toContain("박자 격자가 아직 없습니다.");
    expect(html).toContain("곡 타임라인이 있어야 생깁니다");
    expect(html).toContain("런북 화면으로 돌아가기");
  });

  it("돌아갈 길(onExit)을 주지 않으면 버튼을 그리지 않는다", () => {
    const html = renderToStaticMarkup(<BeatGrid grid={null} />);
    expect(html).toContain("박자 격자가 아직 없습니다.");
    expect(html).not.toContain("런북 화면으로 돌아가기");
  });

  it("트랙이 없는 격자는 서버 안내 문구와 돌아가기 버튼을 보인다", () => {
    const html = renderToStaticMarkup(<BeatGrid grid={emptyTracksGrid()} onExit={() => {}} />);
    expect(html).toContain(NO_DEFAULT_NOTE);
    expect(html).toContain("런북 화면으로 돌아가기");
  });
});
