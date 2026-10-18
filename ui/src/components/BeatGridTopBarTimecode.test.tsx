// 상단 바 타임코드 번호 입력칸 시험 (반영 준비).
//
// jsdom 시험대가 없으므로(BeatGridTopBar.test.tsx 와 같은 방식) 순수 함수는 직접
// 부르고, 입력칸의 모양은 `renderToStaticMarkup`으로 문자열을 단언한다. 입력값을
// 서버로 보내는 동작은 부모 화면(BeatGrid.tsx)이 콜백을 넘길 때만 생긴다.
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import {
  BeatGridTopBar,
  TIMECODE_UNWIRED_TITLE,
  type BeatGridTopBarProps,
  parseTimecodeInput,
} from "./BeatGridTopBar";

const noop = () => {};

function render(overrides: Partial<BeatGridTopBarProps> = {}) {
  return renderToStaticMarkup(
    <BeatGridTopBar
      songTitle="LOVE ATTACK"
      versionLabel={null}
      bpm={112}
      currentBar={1}
      barRange={{ start: 0, end: 82 }}
      onBarChange={noop}
      {...overrides}
    />,
  );
}

describe("parseTimecodeInput", () => {
  it("reads only a positive whole number and never invents one", () => {
    expect(parseTimecodeInput("20")).toBe(20);
    expect(parseTimecodeInput(" 7 ")).toBe(7);
    for (const bad of ["", "0", "-3", "2.5", "abc", "1e3", "3번"]) {
      expect(parseTimecodeInput(bad)).toBeNull();
    }
  });
});

describe("타임코드 번호 입력칸", () => {
  it("is disabled, with the reason in its title, when no submit callback is wired", () => {
    const markup = render({ timecodeNumber: 20 });

    expect(markup).toContain('value="20"');
    expect(markup).toMatch(/<input[^>]*disabled/);
    expect(markup).toContain(TIMECODE_UNWIRED_TITLE);
    expect(markup).not.toContain("타임코드 번호를 넣어 주세요");
  });

  it("asks for a timecode number when the draft has none — the guidance lives in the input's title", () => {
    const markup = render({ timecodeNumber: null, onTimecodeSubmit: noop });

    expect(markup).toContain('title="타임코드 번호를 넣어 주세요 — Enter 로 적기"');
  });

  it("is only a small input among the top bar buttons — no label text, no 적기 button, no visible hint", () => {
    const markup = render({ timecodeNumber: 20, onTimecodeSubmit: noop });

    expect(markup).toContain('class="beat-grid-timecode-input"');
    expect(markup).not.toContain('<span class="beat-grid-timecode"');
    expect(markup).not.toContain(">적기<");
    expect(markup).not.toMatch(/>타임코드/);
  });

  it("is enabled when a submit callback is wired", () => {
    const markup = render({ timecodeNumber: null, onTimecodeSubmit: noop });

    expect(markup).not.toContain(TIMECODE_UNWIRED_TITLE);
    expect(markup).not.toMatch(/<input[^>]*disabled/);
  });
});
