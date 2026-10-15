// 구간의 D 레벨(d_level)이 null 이면 「모름」이다. 0 으로 읽으면 에너지 막대가 0% 로
// 그려지고 「D」만 남아 「0」처럼 보인다(LOVE ATTACK 시드). null 은 「—」로 그리고,
// 밝기 증감·한눈에 밝기·후렴 경고 같은 계산에서도 0 으로 치지 않는다.
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { SongTimelineReserveItem, SongTimelineSection, SongTimelineView } from "../protocol";
import { CueSheetTimeline, cueLabel } from "./CueSheetTimeline";
import { glanceView } from "./conceptGlance";
import { RunbookMode } from "./RunbookMode";
import { SongTimeline, sectionCardTitle } from "./SongTimeline";
import { chorusReversalWarning, reserveLock } from "./cueRequestWarnings";
import { grammarRows, intensityTrend } from "./runbookM7";
import REQUERY from "./__fixtures__/requeryTimeline.t490.json";

const SOURCE = REQUERY as unknown as SongTimelineView;
const CUE_MONITOR = { executors: [], history: [], lastSyncAt: null, stale: false };

/** D 레벨만 모르는 구간 — 서버가 null 을 싣는 모양. */
function withNullLevel(section: SongTimelineSection): SongTimelineSection {
  return { ...section, d_level: null } as unknown as SongTimelineSection;
}

const NULL_LEVEL_SECTIONS = SOURCE.sections.map(withNullLevel);

describe("곡 타임라인 카드 — D 레벨 null", () => {
  const renderCard = () =>
    renderToStaticMarkup(
      <SongTimeline timeline={{ ...SOURCE, sections: NULL_LEVEL_SECTIONS }} cueMonitor={CUE_MONITOR} />,
    );

  it("에너지 칸은 「—」이고 0% 막대를 그리지 않는다", () => {
    const html = renderCard();
    expect(html).toContain("<span>—</span>");
    expect(html).not.toContain("width:0%");
  });

  it("글자로 null 이나 NaN 을 찍지 않는다", () => {
    const html = renderCard();
    expect(html).not.toContain("null");
    expect(html).not.toContain("NaN");
  });
});

describe("런북 화면 전체 — D 레벨 null", () => {
  it("모든 구간 D 레벨이 null 이어도 죽지 않고 null·NaN·Infinity 를 글자로 찍지 않는다", () => {
    const html = renderToStaticMarkup(
      <RunbookMode cueMonitor={CUE_MONITOR} timeline={{ ...SOURCE, sections: NULL_LEVEL_SECTIONS }} />,
    );
    expect(html).toContain(SOURCE.sections[0].label);
    expect(html).not.toContain("null");
    expect(html).not.toContain("NaN");
    expect(html).not.toContain("Infinity");
  });
});

describe("CUE SHEET — D 레벨 null", () => {
  it("인텐시티 막대를 그리지 않고 null 을 찍지 않는다", () => {
    const html = renderToStaticMarkup(
      <CueSheetTimeline timeline={{ ...SOURCE, sections: NULL_LEVEL_SECTIONS }} />,
    );
    expect(html).not.toContain("cst-level-bar");
    expect(html).not.toContain("null");
    expect(html).not.toContain("NaN");
  });
});

describe("연출 표 한 줄 — D 레벨 null", () => {
  it("밝기 칸은 「Dnull」이 아니라 「—」다", () => {
    expect(grammarRows(NULL_LEVEL_SECTIONS)[0].fixture).toBe("—");
  });
});

describe("밝기 증감 기호 — 모르는 구간은 0 이 아니다", () => {
  it("모르는 구간과 맞닿은 기호는 비운다", () => {
    const sections = [SOURCE.sections[0], withNullLevel(SOURCE.sections[1])];
    expect(intensityTrend(sections, 1)).toBe("");
  });
});

describe("한눈에 구획 — D 레벨 null", () => {
  it("단계 밝기는 0–0% 가 아니라 빈 값이다", () => {
    const withGlance = {
      ...SOURCE,
      sections: NULL_LEVEL_SECTIONS,
      concept_report: {
        ...SOURCE.concept_report,
        available: true,
        glance: {
          available: true,
          rule: "R",
          stages: [{ stage: "S", positions: [0], reason: null }],
        },
      },
    } as unknown as SongTimelineView;
    const view = glanceView(withGlance);
    expect(view.status).toBe("ok");
    if (view.status === "ok") {
      expect(view.cards[0].brightness).toBeNull();
      expect(view.cards[0].line).toContain("밝기 —");
    }
  });
});

describe("후렴 경고 — 뒤 후렴의 밝기를 모르면 경고하지 않는다", () => {
  it("뒤 후렴이 모두 모르는 값이면 0% 와 비교하지 않는다", () => {
    const chorus = { ...SOURCE.sections[0], role: "chorus", index: 1 } as SongTimelineSection;
    const later = withNullLevel({ ...SOURCE.sections[1], role: "chorus", index: 2 } as SongTimelineSection);
    expect(chorusReversalWarning(chorus, [chorus, later], 50)).toBeNull();
  });
});

/** 키 자체가 빠진 모양(undefined) — 옛 페이로드나 아직 채우지 않은 시드. */
function withoutKey(section: SongTimelineSection, key: "d_level" | "cue_number"): SongTimelineSection {
  const copy: Record<string, unknown> = { ...section };
  delete copy[key];
  return copy as unknown as SongTimelineSection;
}

/** 큐 번호만 모르는 구간 — null 로 싣는 모양. */
function withNullCue(section: SongTimelineSection): SongTimelineSection {
  return { ...section, cue_number: null } as unknown as SongTimelineSection;
}

describe("D 레벨 키가 아예 없어도 null 과 같다", () => {
  const noKey = SOURCE.sections.map((section) => withoutKey(section, "d_level"));

  it("곡 타임라인 카드는 「—」를 내고 undefined·NaN 을 찍지 않는다", () => {
    const html = renderToStaticMarkup(
      <SongTimeline timeline={{ ...SOURCE, sections: noKey }} cueMonitor={CUE_MONITOR} />,
    );
    expect(html).toContain("<span>—</span>");
    expect(html).not.toContain("width:0%");
    expect(html).not.toContain("undefined");
    expect(html).not.toContain("NaN");
  });

  it("런북 화면 전체가 죽지 않는다", () => {
    const html = renderToStaticMarkup(
      <RunbookMode cueMonitor={CUE_MONITOR} timeline={{ ...SOURCE, sections: noKey }} />,
    );
    expect(html).toContain(SOURCE.sections[0].label);
    expect(html).not.toContain("undefined");
    expect(html).not.toContain("NaN");
  });
});

describe("큐 번호가 없으면 「—」 — Qnull·Qundefined 로 찍지 않는다", () => {
  const noCue = SOURCE.sections.map(withNullCue);
  const noCueKey = SOURCE.sections.map((section) => withoutKey(section, "cue_number"));
  // 생성기 시험은 PLAN CUE 구간이어야 열린다(확정 큐에는 생성기가 없다).
  const draftSections = SOURCE.sections.map(
    (section) => ({ ...section, plan_status: "draft" }) as SongTimelineSection,
  );

  it("큐 라벨과 카드 제목은 「—」다", () => {
    expect(cueLabel(noCue[0])).toBe("—");
    expect(sectionCardTitle(noCue[0], "draft")).toBe(`PLAN CUE — · ${SOURCE.sections[0].label}`);
    expect(sectionCardTitle(noCueKey[0], "verified")).toBe("CUE —");
  });

  it("화면 전체에 Qnull·Qundefined 가 없다 — null 과 키 누락 둘 다", () => {
    for (const sections of [noCue, noCueKey]) {
      const html = renderToStaticMarkup(
        <RunbookMode cueMonitor={CUE_MONITOR} timeline={{ ...SOURCE, sections }} />,
      );
      expect(html).not.toContain("Qnull");
      expect(html).not.toContain("Qundefined");
      expect(html).not.toContain("undefined");
      expect(html).not.toContain("null");
    }
  });

  it("수정요청 생성기는 큐 번호가 있는 구간에만 열린다", () => {
    const render = (sections: SongTimelineSection[]) =>
      renderToStaticMarkup(
        <SongTimeline
          timeline={{ ...SOURCE, sections }}
          cueMonitor={CUE_MONITOR}
          onGeneratorSend={() => {}}
        />,
      );
    expect(render(draftSections)).toContain('aria-label="PLAN CUE 수정요청 생성기"');
    expect(render(draftSections.map(withNullCue))).not.toContain('aria-label="PLAN CUE 수정요청 생성기"');
  });

  it("해제 위치의 큐 번호를 모르면 「위치 불명」이다", () => {
    const reserve = [{ name: "BLIND", released_q: 3, screen_position: 1 }] as unknown as SongTimelineReserveItem[];
    expect(reserveLock("BLIND", reserve, 0, noCue)).toEqual({ name: "BLIND", release: "위치 불명" });
  });
});
