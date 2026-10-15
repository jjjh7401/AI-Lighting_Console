// 런북: 불러온 곡이 없을 때의 안내와 타임라인 라이브러리 펼침 손잡이 (감독 화면 피드백).
// 이 프로젝트는 jsdom 이 없어 `renderToStaticMarkup` 으로 글자만 본다.
// 주의: 접힌 라벨의 화살표와 제목은 서로 다른 글자 조각이라 한 문자열로 잇지 않는다.
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { CueMonitorState } from "../protocol";
import { RunbookMode } from "./RunbookMode";
import { TimelineLibrary } from "./TimelineLibrary";

const EMPTY_STATE: CueMonitorState = {
  executors: [],
  history: [],
  lastSyncAt: null,
  stale: false,
};

describe("런북: 불러온 곡이 없을 때의 안내", () => {
  it("곡이 없으면 라이브러리 안내와 펼치기 버튼을 보인다", () => {
    const html = renderToStaticMarkup(
      RunbookMode({ cueMonitor: EMPTY_STATE, onOpenTimelineLibrary: () => {} }),
    );
    expect(html).toContain("불러온 곡이 없습니다");
    expect(html).toContain("타임라인 라이브러리 펼치기");
  });

  it("펼치기 손잡이를 주지 않으면 안내 문장만 보인다", () => {
    const html = renderToStaticMarkup(RunbookMode({ cueMonitor: EMPTY_STATE }));
    expect(html).toContain("불러온 곡이 없습니다");
    expect(html).not.toContain("타임라인 라이브러리 펼치기");
  });
});

describe("타임라인 라이브러리: 펼침 상태를 부모가 쥘 때", () => {
  it("open 을 넘기면 펼친 화살표(▾)로 그린다", () => {
    const html = renderToStaticMarkup(<TimelineLibrary hasTimeline={false} onLoaded={() => {}} open />);
    expect(html).toContain("▾");
    expect(html).toContain("타임라인 라이브러리");
  });

  it("open 을 넘기지 않으면 접힌 화살표(▸)로 그린다", () => {
    const html = renderToStaticMarkup(<TimelineLibrary hasTimeline={false} onLoaded={() => {}} />);
    expect(html).toContain("▸");
    expect(html).toContain("타임라인 라이브러리");
  });
});
