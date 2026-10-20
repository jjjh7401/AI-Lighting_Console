// 콘솔 타임코드가 돌고 있을 수 있다는 큰 알림(N11) — 정적 렌더로 보이는 글과 끄기 버튼을 단언한다.
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { BeatGridView } from "../../protocol";
import { BeatGrid } from "../BeatGrid";
import { ConsoleRunningBanner } from "./ConsoleRunningBanner";
import { createConsoleFollowRelay } from "./consoleFollowRelay";

describe("ConsoleRunningBanner", () => {
  it("콘솔이 돌 수 있으면 타임코드 번호와 끄기 버튼을 크게 보인다", () => {
    const html = renderToStaticMarkup(
      <ConsoleRunningBanner visible timecodeNumber={5} approvalPending={false} onStop={() => {}} />,
    );
    expect(html).toContain('role="alert"');
    expect(html).toContain("콘솔 Timecode 5 가 아직 돌고 있을 수 있어요");
    expect(html).toContain("■ 콘솔 끄기");
  });

  it("정지 카드를 기다리는 중이면 카드에서 승인하라고 말하고 버튼은 숨긴다(카드를 겹쳐 띄우지 않음)", () => {
    const html = renderToStaticMarkup(
      <ConsoleRunningBanner visible timecodeNumber={5} approvalPending onStop={() => {}} />,
    );
    expect(html).toContain("정지 승인 카드를 기다리고 있어요");
    expect(html).not.toContain("■ 콘솔 끄기");
  });

  it("안 보일 때는 아무것도 그리지 않는다", () => {
    expect(renderToStaticMarkup(<ConsoleRunningBanner visible={false} timecodeNumber={5} approvalPending={false} />)).toBe("");
  });
});

// 2026-10-20 실측 — 콘솔이 출발한 바로 그 순간(음원은 아직 지연을 기다린다) 격자 화면이 「앱은 멈췄지만 콘솔
// 정지가 확인되지 않았어요」를 그렸다. 어긋남이 막 생긴 첫 렌더에서는 알리지 않는다(오래 갈 때만).
describe("BeatGrid — 콘솔이 막 출발한 첫 렌더", () => {
  it("콘솔이 돌 수 있고 음원이 아직 안 돌아도 첫 렌더에는 「정지 미확인」 알림이 없다", () => {
    const relay = createConsoleFollowRelay();
    relay.consoleFollow = true;
    relay.consoleMayRun = true;
    relay.responseAtMs = Date.now();
    const grid = {
      song_title: "LOVE ATTACK",
      bar_range: { start: 0, end: 8 },
      source: "custom",
      note: null,
      scene_memos: [],
      probe_results: {},
      unsent_cells: null,
      tracks: [],
      console_audio_offset_seconds: 3.002,
    } as unknown as BeatGridView;
    const html = renderToStaticMarkup(<BeatGrid grid={grid} consoleFollowRelay={relay} timecodeNumber={5} />);
    expect(html).not.toContain("콘솔 정지가 확인되지 않았어요");
  });
});
