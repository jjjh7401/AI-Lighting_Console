// 카드 t490 — 재질의 대기(lifecycle requires_requery) 타임라인이 구간마다
// `fade_seconds: null` 을 싣는데, CUE SHEET 가 `undefined` 만 막아
// `null.toFixed` 로 터지고 런북 화면 전체(#root)가 빈다(t485 lane-2 실측,
// .moai/reports/t485/bullet_probe.json raw_payload_without_workaround).
//
// 서버가 null 을 싣는 것은 의도다 — 재질의 대기에서는 조립기 결과가 없고
// (`song_cue_composer.py` "a successful bundle cannot also request re-query
// cards"), 그래서 페이드는 아직 정해지지 않은 값이다. 고칠 곳은 UI 다.
//
// 픽스처는 t485 가 실제 세션을 인터뷰부터 돌려 받은 타임라인 그대로다
// (`requeryTimeline.t490.json` = t485 `payload_causal.json`, sha256 a61b651f…).
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { SongTimelineSection, SongTimelineView } from "../protocol";
import { CueSheetTimeline, EMPTY_CELL } from "./CueSheetTimeline";
import { fadeBeforeLabel } from "./PlanCueRequestGenerator";
import { RunbookMode } from "./RunbookMode";
import { fadeTrackLine } from "./SongTimeline";
import REQUERY from "./__fixtures__/requeryTimeline.t490.json";

const TIMELINE = REQUERY as unknown as SongTimelineView;

describe("재질의 대기 타임라인 — 픽스처 전제", () => {
  it("실제 페이로드가 재질의 대기이고 구간마다 fade_seconds 가 null 이다", () => {
    expect(TIMELINE.lifecycle).toBe("requires_requery");
    expect(TIMELINE.sections.length).toBeGreaterThan(0);
    expect(TIMELINE.sections.every((section) => section.fade_seconds === null)).toBe(true);
  });
});

describe("CUE SHEET 는 null 페이드로 터지지 않는다", () => {
  it("실제 재질의 대기 페이로드를 그린다", () => {
    const html = renderToStaticMarkup(<CueSheetTimeline timeline={TIMELINE} />);
    expect(html.length).toBeGreaterThan(0);
    expect(html).not.toContain("null");
  });

  it("값이 있는 페이드는 그대로 소수 둘째 자리로 보인다(대조군)", () => {
    const sections = TIMELINE.sections.map((section) => ({ ...section, fade_seconds: 1.5 }));
    const html = renderToStaticMarkup(<CueSheetTimeline timeline={{ ...TIMELINE, sections }} />);
    expect(html).toContain("1.50");
  });

  it("null 페이드 칸은 빈 칸 표식이다", () => {
    const one = { ...TIMELINE, sections: TIMELINE.sections.slice(0, 1) };
    const html = renderToStaticMarkup(<CueSheetTimeline timeline={one} />);
    expect(html).toContain(EMPTY_CELL);
  });
});

describe("런북 화면 전체 — 브라우저에서 #root 가 비던 그 트리", () => {
  it("RunbookMode 가 실제 재질의 대기 페이로드로 그려지고 CUE SHEET 를 담는다", () => {
    const html = renderToStaticMarkup(
      <RunbookMode
        cueMonitor={{ executors: [], history: [], lastSyncAt: null, stale: false }}
        timeline={TIMELINE}
      />,
    );
    expect(html).toContain(TIMELINE.sections[0].label);
    expect(html).not.toContain("nulls");
    expect(html).not.toContain("null초");
  });
});

describe("다른 두 소비처도 null 을 글자로 찍지 않는다", () => {
  const section = TIMELINE.sections[0] as SongTimelineSection;

  it("Fade/Track 줄", () => {
    expect(fadeTrackLine(section, undefined)).toBe("Fade — · Track —");
    expect(fadeTrackLine({ ...section, fade_seconds: 2 }, undefined)).toBe("Fade 2s · Track —");
  });

  it("수정 요청 생성기의 이전 값", () => {
    expect(fadeBeforeLabel(section)).toBe("—");
    expect(fadeBeforeLabel({ ...section, fade_seconds: 2 })).toBe("2초");
  });
});
