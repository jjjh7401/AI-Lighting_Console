// 마디 지도 진입 컨트롤 `BarMapEntry` 의 정적 HTML 시험 (SPEC-LDBARMAP-003, 카드 t648).
//
// 이 프로젝트에는 DOM 시험대(jsdom, testing-library)가 없다(spec.md §4 「시험 방식」,
// `BeatGrid.test.tsx` 와 같은 바운드). 그래서 `renderToStaticMarkup` 이 내놓는 문자열만
// 본다. 클릭, 실제 소켓, 실제 넘침은 자동으로 재지 않는다 — 수동 확인이다(plan.md §4).
//
// 기대 문구는 spec.md §4 「문구 고정표」의 글자 그대로다.
import { readFileSync } from "node:fs";

import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { BarMapEntry, type BarMapEntryProps } from "./BarMapEntry";

const NOTICE_CANCELLED = "취소했습니다. 서버의 분석은 계속될 수 있으며, 끝나면 이 자리에 결과가 표시됩니다.";
const NOTICE_SAVED = "곡 «sample-track.wav» 마디 지도를 초안에 저장했습니다.";
const NOTICE_METER = "이 분석기는 4/4 곡만 다룬다.";

const BASE: BarMapEntryProps = {
  offset: null,
  waiting: false,
  responding: false,
  timelineMeter: null,
  notice: null,
  onOffsetChange: () => {},
  onAnalyse: () => {},
  onCancel: () => {},
};

function render(over: Partial<BarMapEntryProps> = {}): string {
  return renderToStaticMarkup(<BarMapEntry {...BASE} {...over} />);
}

// --- 정적 HTML 을 읽는 작은 도구들 (DOM 이 없어서 정규식으로 읽는다) -----------

const stripTags = (fragment: string): string => fragment.replace(/<[^>]*>/g, "").trim();
const isDisabled = (attrs: string): boolean => /(^|\s)disabled(=|\s|$)/.test(attrs);

interface Button {
  attrs: string;
  text: string;
}

function buttons(html: string): Button[] {
  return [...html.matchAll(/<button\b([^>]*)>([\s\S]*?)<\/button>/g)].map((m) => ({
    attrs: m[1],
    text: stripTags(m[2]),
  }));
}

function buttonByText(html: string, text: string): Button | undefined {
  return buttons(html).find((b) => b.text === text);
}

function selectAttrs(html: string): string | null {
  const m = /<select\b([^>]*)>/.exec(html);
  return m === null ? null : m[1];
}

interface Option {
  attrs: string;
  value: string | null;
  text: string;
  selected: boolean;
}

function options(html: string): Option[] {
  return [...html.matchAll(/<option\b([^>]*)>([\s\S]*?)<\/option>/g)].map((m) => {
    const value = /\bvalue="([^"]*)"/.exec(m[1]);
    return {
      attrs: m[1],
      value: value === null ? null : value[1],
      text: stripTags(m[2]),
      selected: /(^|\s)selected(=|\s|$)/.test(m[1]),
    };
  });
}

/** class 토큰으로 요소 하나를 찾아, 같은 태그 이름의 깊이를 세어 닫는 태그까지 잘라 낸다. */
function elementByClass(html: string, className: string): string | null {
  const open = new RegExp(`<(\\w+)\\b[^>]*\\bclass="(?:[^"]*\\s)?${className}(?:\\s[^"]*)?"[^>]*>`);
  const first = open.exec(html);
  if (first === null) return null;
  const tag = first[1];
  const tagRe = new RegExp(`<(/?)${tag}\\b[^>]*>`, "g");
  tagRe.lastIndex = first.index;
  let depth = 0;
  for (let m = tagRe.exec(html); m !== null; m = tagRe.exec(html)) {
    depth += m[1] === "/" ? -1 : 1;
    if (depth === 0) return html.slice(first.index, tagRe.lastIndex);
  }
  return null;
}

describe("AC-LDBARUI-001: analyse button is blocked while a chat reply is in progress", () => {
  it("AC-LDBARUI-001: responding disables the 마디 지도 분석 button even with an offset chosen", () => {
    const button = buttonByText(render({ offset: 2, responding: true }), "마디 지도 분석");
    expect(button).toBeDefined();
    expect(isDisabled(button!.attrs)).toBe(true);
  });

  it("AC-LDBARUI-001: control — with an offset chosen and nothing in progress the button is enabled", () => {
    const button = buttonByText(render({ offset: 2 }), "마디 지도 분석");
    expect(button).toBeDefined();
    expect(isDisabled(button!.attrs)).toBe(false);
  });
});

describe("AC-LDBARUI-002: the dropdown starts on the empty 선택 option", () => {
  it("AC-LDBARUI-002: with a null offset the selected option has the empty value and the text 선택", () => {
    const html = render({ offset: null });
    const selected = options(html).filter((o) => o.selected);
    expect(selected).toHaveLength(1);
    expect(selected[0].value).toBe("");
    expect(selected[0].text).toBe("선택");
  });

  it("AC-LDBARUI-002: with a null offset the 마디 지도 분석 button is disabled", () => {
    const button = buttonByText(render({ offset: null }), "마디 지도 분석");
    expect(button).toBeDefined();
    expect(isDisabled(button!.attrs)).toBe(true);
  });

  it("AC-LDBARUI-002: the dropdown carries its name 첫 박 오프셋", () => {
    expect(render()).toContain("첫 박 오프셋");
  });

  it("AC-LDBARUI-002: control — a chosen offset is the selected option, not the empty one", () => {
    const selected = options(render({ offset: 2 })).filter((o) => o.selected);
    expect(selected).toHaveLength(1);
    expect(selected[0].value).toBe("2");
  });
});

describe("AC-LDBARUI-003: four choices, and the meter notice never changes the range", () => {
  it("AC-LDBARUI-003: the non-empty option values are exactly 0, 1, 2, 3", () => {
    const values = options(render())
      .map((o) => o.value)
      .filter((v) => v !== "");
    expect(values).toEqual(["0", "1", "2", "3"]);
  });

  it("AC-LDBARUI-003: an off-meter timeline shows the 4/4-only notice and the range stays 0..3", () => {
    const html = render({ timelineMeter: "3/4" });
    expect(html).toContain(NOTICE_METER);
    const values = options(html)
      .map((o) => o.value)
      .filter((v) => v !== "");
    expect(values).toEqual(["0", "1", "2", "3"]);
  });

  it("AC-LDBARUI-003: no notice for 4/4 (whitespace ignored), a missing meter, or an empty one", () => {
    for (const timelineMeter of ["4/4", " 4 / 4 ", null, ""]) {
      expect(render({ timelineMeter }), String(timelineMeter)).not.toContain("이 분석기는");
    }
  });
});

describe("AC-LDBARUI-004: waiting state", () => {
  const waitingHtml = render({ offset: 2, waiting: true });

  it("AC-LDBARUI-004: the analyse button and the dropdown are disabled", () => {
    const button = buttonByText(waitingHtml, "마디 지도 분석");
    expect(button).toBeDefined();
    expect(isDisabled(button!.attrs)).toBe(true);
    const select = selectAttrs(waitingHtml);
    expect(select).not.toBeNull();
    expect(isDisabled(select!)).toBe(true);
  });

  it("AC-LDBARUI-004: 분석 중 and a 취소 button are shown, and the cancel button is usable", () => {
    expect(waitingHtml).toContain("분석 중");
    const cancel = buttonByText(waitingHtml, "취소");
    expect(cancel).toBeDefined();
    expect(isDisabled(cancel!.attrs)).toBe(false);
  });

  it("AC-LDBARUI-004: control — when idle there is no 분석 중 text and no 취소 button, and the dropdown is enabled", () => {
    const idleHtml = render({ offset: 2 });
    expect(idleHtml).not.toContain("분석 중");
    expect(buttonByText(idleHtml, "취소")).toBeUndefined();
    const select = selectAttrs(idleHtml);
    expect(select).not.toBeNull();
    expect(isDisabled(select!)).toBe(false);
  });
});

describe("AC-LDBARUI-012: the two analyse buttons are kept apart", () => {
  it("AC-LDBARUI-012: the button text is exactly 마디 지도 분석", () => {
    const html = render({ offset: 2 });
    expect(buttonByText(html, "마디 지도 분석")).toBeDefined();
  });

  it("AC-LDBARUI-012: no button here is labelled only 분석 (that is the existing song_audio_analyse button)", () => {
    for (const html of [render(), render({ offset: 2 }), render({ offset: 2, waiting: true })]) {
      expect(buttons(html).some((b) => b.text === "분석")).toBe(false);
    }
  });
});

describe("AC-LDBARUI-013: status and notice lines are separate elements; the control group may wrap", () => {
  const html = render({ offset: 2, waiting: true, notice: NOTICE_CANCELLED });
  const group = elementByClass(html, "composer-bar-map");

  it("AC-LDBARUI-013: the control group (class composer-bar-map) holds the dropdown and the analyse button", () => {
    expect(group).not.toBeNull();
    expect(group).toContain("<select");
    expect(group).toContain("마디 지도 분석");
  });

  it("AC-LDBARUI-013: 분석 중 and the notice are in elements outside the control group", () => {
    expect(group).not.toBeNull();
    expect(html).toContain("분석 중");
    expect(html).toContain(NOTICE_CANCELLED);
    expect(group).not.toContain("분석 중");
    expect(group).not.toContain(NOTICE_CANCELLED);
  });

  it("AC-LDBARUI-013: a result notice (with a file name) is also outside the control group", () => {
    const savedHtml = render({ offset: 2, notice: NOTICE_SAVED });
    const savedGroup = elementByClass(savedHtml, "composer-bar-map");
    expect(savedGroup).not.toBeNull();
    expect(savedHtml).toContain(NOTICE_SAVED);
    expect(savedGroup).not.toContain(NOTICE_SAVED);
  });

  it("AC-LDBARUI-013: styles.css gives .composer-bar-map both flex-wrap: wrap and max-width: 100%", () => {
    const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
    const block = /\.composer-bar-map\s*\{([^}]*)\}/.exec(css);
    expect(block, ".composer-bar-map rule block not found in styles.css").not.toBeNull();
    expect(block![1]).toMatch(/flex-wrap:\s*wrap/);
    expect(block![1]).toMatch(/max-width:\s*100%/);
  });
});
