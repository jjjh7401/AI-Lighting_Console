// PaperworkPanel structural + logic tests (W3 — P0 UI exposure).
//
// Same mocked-fidelity bound as RunbookMode.test.tsx/CueMonitor.test.tsx
// (this project has no DOM/jsdom test harness): PaperworkPanelView/
// PaperworkCard have no internal hooks, so they are called directly as
// plain functions and the returned React element tree is inspected without
// a renderer. The stateful PaperworkPanel (fetch() + React hooks) is
// exercised only through its pure companions below — the same bound
// SettingsPanel/ResponderGuide already accept for their own fetch-owning
// components.
import type { ReactElement } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  PAPERWORK_KINDS,
  PaperworkCard,
  PaperworkPanelView,
  contentUrl,
  downloadUrl,
  fetchPaperworkList,
  generatePaperworkDocument,
  paperworkBadges,
  parsePaperworkGenerateResponse,
  parsePaperworkListResponse,
  type PaperworkSummary,
} from "./PaperworkPanel";

function childArray(element: ReactElement): unknown[] {
  const children = element.props.children;
  if (children === undefined) return [];
  const list = Array.isArray(children) ? children : [children];
  return list
    .flat(Infinity)
    .filter((child) => child !== null && child !== undefined && child !== false);
}

/** Renders a function-component ReactElement one level deeper — same
 * technique CueMonitor.test.tsx uses for nested hook-free components. */
function render(element: ReactElement): ReactElement {
  return (element.type as (props: unknown) => ReactElement)(element.props);
}

function isElementWithClassName(value: unknown, className: string): value is ReactElement {
  return (
    typeof value === "object" &&
    value !== null &&
    "props" in value &&
    (value as ReactElement).props !== null &&
    typeof (value as ReactElement).props === "object" &&
    (value as ReactElement).props.className === className
  );
}

const PATCH_SHEET_COMPLETE: PaperworkSummary = {
  path: "/tmp/paperwork_output/patch_sheet.html",
  fixture_count: 19,
  child_count: 19,
  completeness: "complete",
};

const PATCH_SHEET_INCOMPLETE: PaperworkSummary = {
  path: "/tmp/paperwork_output/patch_sheet.html",
  fixture_count: 18,
  child_count: 19,
  completeness: "partial",
};

const CUE_SHEET_TRUNCATED: PaperworkSummary = {
  path: "/tmp/paperwork_output/cue_sheet.html",
  sequence_count: 3,
  cue_count: 40,
  truncated: true,
  drilldown_capped: false,
};

const PRESET_LIST_CLEAN: PaperworkSummary = {
  path: "/tmp/paperwork_output/preset_list.html",
  pool_count: 2,
  preset_count: 12,
  truncated: false,
  drilldown_capped: false,
};

describe("paperworkBadges — ③ 불완전성 배지가 응답 플래그에 따라 나타난다/사라진다", () => {
  it("patch_sheet: no badge when observed matches declared and completeness is complete", () => {
    expect(paperworkBadges("patch_sheet", PATCH_SHEET_COMPLETE)).toEqual([]);
  });

  it("patch_sheet: names the observed/declared gap and flags incompleteness", () => {
    const badges = paperworkBadges("patch_sheet", PATCH_SHEET_INCOMPLETE);
    expect(badges).toContain("관측 18 / 선언 19");
    expect(badges).toContain("불완전");
  });

  it("cue_sheet: truncated flag surfaces as a badge", () => {
    expect(paperworkBadges("cue_sheet", CUE_SHEET_TRUNCATED)).toEqual(["절단됨"]);
  });

  it("cue_sheet/preset_list: no badge when neither flag is set", () => {
    expect(paperworkBadges("preset_list", PRESET_LIST_CLEAN)).toEqual([]);
  });

  it("preset_list: drilldown_capped surfaces independently of truncated", () => {
    const badges = paperworkBadges("preset_list", {
      path: "x",
      truncated: false,
      drilldown_capped: true,
    });
    expect(badges).toEqual(["드릴다운 상한"]);
  });

  it("magic_sheet: the membership badge is unconditional — a complete read still carries it", () => {
    // Group membership is unreadable as a matter of platform, not as an
    // outcome of this call, so an operator must not have to notice an ABSENT
    // badge to learn it (server/paperwork/data.py GROUP_MEMBERSHIP_UNAVAILABLE).
    const badges = paperworkBadges("magic_sheet", {
      path: "x",
      group_count: 4,
      preset_pool_count: 6,
      placement_count: 19,
      placements_complete: true,
    });
    expect(badges).toEqual(["그룹 멤버십 판독 불가"]);
  });

  it("magic_sheet: a partial placement read adds its own badge beside it", () => {
    const badges = paperworkBadges("magic_sheet", {
      path: "x",
      placement_count: 18,
      placements_complete: false,
    });
    expect(badges).toEqual(["배치 좌표 일부", "그룹 멤버십 판독 불가"]);
  });

  it("magic_sheet: truncated/drilldown_capped do not leak in from the pool kinds", () => {
    const badges = paperworkBadges("magic_sheet", {
      path: "x",
      truncated: true,
      drilldown_capped: true,
      placements_complete: true,
    });
    expect(badges).toEqual(["그룹 멤버십 판독 불가"]);
  });
});

describe("PaperworkCard — hook-free structural render", () => {
  it("renders the kind label and a [생성] button when no result yet", () => {
    const element = PaperworkCard({
      meta: PAPERWORK_KINDS[0],
      result: null,
      busy: false,
      previewing: false,
      onGenerate: vi.fn(),
      onPreview: vi.fn(),
      onDownload: vi.fn(),
    });
    const children = childArray(element);
    const head = children.find((child) => isElementWithClassName(child, "paperwork-card-head"));
    expect(head).toBeDefined();
    const headChildren = childArray(head as ReactElement);
    const label = headChildren.find((child) => isElementWithClassName(child, "paperwork-card-label"));
    expect(childArray(label as ReactElement)).toEqual(["패치시트"]);
    // No result yet -> no .paperwork-card-actions section at all.
    const actions = children.find((child) => isElementWithClassName(child, "paperwork-card-actions"));
    expect(actions).toBeUndefined();
  });

  it("② 생성 클릭 시 onGenerate(kind)가 호출된다 (App/PaperworkPanel이 fetch로 연결)", () => {
    const onGenerate = vi.fn();
    const element = PaperworkCard({
      meta: PAPERWORK_KINDS[1],
      result: null,
      busy: false,
      previewing: false,
      onGenerate,
      onPreview: vi.fn(),
      onDownload: vi.fn(),
    });
    const head = childArray(element).find((child) =>
      isElementWithClassName(child, "paperwork-card-head"),
    ) as ReactElement;
    const button = childArray(head).find(
      (child) => (child as ReactElement).props.className === "paperwork-card-generate",
    ) as ReactElement;
    expect(button.props.disabled).toBe(false);
    button.props.onClick();
    expect(onGenerate).toHaveBeenCalledWith("cue_sheet");
  });

  it("shows '생성 중…' and disables the button while busy", () => {
    const element = PaperworkCard({
      meta: PAPERWORK_KINDS[0],
      result: null,
      busy: true,
      previewing: false,
      onGenerate: vi.fn(),
      onPreview: vi.fn(),
      onDownload: vi.fn(),
    });
    const head = childArray(element).find((child) =>
      isElementWithClassName(child, "paperwork-card-head"),
    ) as ReactElement;
    const button = childArray(head).find(
      (child) => (child as ReactElement).props.className === "paperwork-card-generate",
    ) as ReactElement;
    expect(button.props.disabled).toBe(true);
    expect(childArray(button)).toEqual(["생성 중…"]);
  });

  it("③ 배지가 나타난다 — an incomplete result shows badges + preview/download buttons", () => {
    const element = PaperworkCard({
      meta: PAPERWORK_KINDS[0],
      result: PATCH_SHEET_INCOMPLETE,
      busy: false,
      previewing: false,
      onGenerate: vi.fn(),
      onPreview: vi.fn(),
      onDownload: vi.fn(),
    });
    const actions = childArray(element).find((child) =>
      isElementWithClassName(child, "paperwork-card-actions"),
    ) as ReactElement;
    expect(actions).toBeDefined();
    const badgesBox = childArray(actions).find((child) =>
      isElementWithClassName(child, "paperwork-card-badges"),
    ) as ReactElement;
    const badgeTexts = childArray(badgesBox).map((badge) => childArray(badge as ReactElement)[0]);
    expect(badgeTexts).toEqual(expect.arrayContaining(["관측 18 / 선언 19", "불완전"]));
    const buttons = childArray(actions).find((child) =>
      isElementWithClassName(child, "paperwork-card-buttons"),
    );
    expect(buttons).toBeDefined();
  });

  it("③ 배지가 사라진다 — a complete result shows no badges box at all", () => {
    const element = PaperworkCard({
      meta: PAPERWORK_KINDS[0],
      result: PATCH_SHEET_COMPLETE,
      busy: false,
      previewing: false,
      onGenerate: vi.fn(),
      onPreview: vi.fn(),
      onDownload: vi.fn(),
    });
    const actions = childArray(element).find((child) =>
      isElementWithClassName(child, "paperwork-card-actions"),
    ) as ReactElement;
    const badgesBox = childArray(actions).find((child) =>
      isElementWithClassName(child, "paperwork-card-badges"),
    );
    expect(badgesBox).toBeUndefined();
  });

  it("the [미리보기]/[다운로드] buttons fire onPreview/onDownload with the kind", () => {
    const onPreview = vi.fn();
    const onDownload = vi.fn();
    const element = PaperworkCard({
      meta: PAPERWORK_KINDS[0],
      result: PATCH_SHEET_COMPLETE,
      busy: false,
      previewing: false,
      onGenerate: vi.fn(),
      onPreview,
      onDownload,
    });
    const actions = childArray(element).find((child) =>
      isElementWithClassName(child, "paperwork-card-actions"),
    ) as ReactElement;
    const buttons = childArray(actions).find((child) =>
      isElementWithClassName(child, "paperwork-card-buttons"),
    ) as ReactElement;
    const [previewButton, downloadButton] = childArray(buttons) as ReactElement[];
    previewButton.props.onClick();
    expect(onPreview).toHaveBeenCalledWith("patch_sheet");
    downloadButton.props.onClick();
    expect(onDownload).toHaveBeenCalledWith("patch_sheet");
  });
});

function panelView(overrides: Partial<Parameters<typeof PaperworkPanelView>[0]> = {}) {
  return PaperworkPanelView({
    results: {},
    busyKind: null,
    notice: null,
    previewKind: null,
    onGenerate: vi.fn(),
    onPreview: vi.fn(),
    onDownload: vi.fn(),
    onClose: vi.fn(),
    ...overrides,
  });
}

/** The view now splits into `.paperwork-sidebar` + `.paperwork-preview-area`;
 * the cards live inside the sidebar. */
function sidebarOf(element: ReactElement): ReactElement {
  return childArray(element).find((child) =>
    isElementWithClassName(child, "paperwork-sidebar"),
  ) as ReactElement;
}

function cardsBoxOf(element: ReactElement): ReactElement {
  return childArray(sidebarOf(element)).find((child) =>
    isElementWithClassName(child, "paperwork-cards"),
  ) as ReactElement;
}

describe("PaperworkPanelView — ① 4종 렌더", () => {
  it("renders exactly one card per PAPERWORK_KINDS entry, in order", () => {
    const cards = childArray(cardsBoxOf(panelView())) as ReactElement[];
    expect(cards).toHaveLength(4);
    expect(cards.map((card) => card.props.meta.kind)).toEqual([
      "patch_sheet",
      "cue_sheet",
      "preset_list",
      "magic_sheet",
    ]);
  });

  it("passes each kind's own result (or null) down to its card, keyed by kind", () => {
    const element = panelView({ results: { cue_sheet: CUE_SHEET_TRUNCATED } });
    const cards = childArray(cardsBoxOf(element)) as ReactElement[];
    expect(cards[0].props.result).toBeNull(); // patch_sheet: no last_result
    expect(cards[1].props.result).toBe(CUE_SHEET_TRUNCATED); // cue_sheet
    expect(cards[2].props.result).toBeNull(); // preset_list
    expect(cards[3].props.result).toBeNull(); // magic_sheet
  });

  it("marks only the busy kind's card as busy", () => {
    const cards = childArray(cardsBoxOf(panelView({ busyKind: "preset_list" }))) as ReactElement[];
    expect(cards.map((card) => card.props.busy)).toEqual([false, false, true, false]);
  });

  it("marks only the previewed kind's card as previewing", () => {
    const cards = childArray(cardsBoxOf(panelView({ previewKind: "cue_sheet" }))) as ReactElement[];
    expect(cards.map((card) => card.props.previewing)).toEqual([false, true, false, false]);
  });

  it("renders a notice line only when one is present", () => {
    expect(
      childArray(sidebarOf(panelView())).some((child) =>
        isElementWithClassName(child, "paperwork-notice"),
      ),
    ).toBe(false);

    const withNotice = panelView({ notice: "문서 생성 중 오류가 발생했습니다." });
    const notice = childArray(sidebarOf(withNotice)).find((child) =>
      isElementWithClassName(child, "paperwork-notice"),
    ) as ReactElement;
    expect(childArray(notice)).toEqual(["문서 생성 중 오류가 발생했습니다."]);
  });

  it("shows the empty preview placeholder until a preview kind is chosen", () => {
    const area = childArray(panelView()).find((child) =>
      isElementWithClassName(child, "paperwork-preview-area"),
    ) as ReactElement;
    expect(
      childArray(area).some((child) => isElementWithClassName(child, "paperwork-preview-empty")),
    ).toBe(true);
  });

  it("renders the preview iframe for the chosen kind", () => {
    const area = childArray(panelView({ previewKind: "patch_sheet" })).find((child) =>
      isElementWithClassName(child, "paperwork-preview-area"),
    ) as ReactElement;
    const frame = childArray(area).find((child) =>
      isElementWithClassName(child, "paperwork-preview-frame"),
    ) as ReactElement;
    expect(frame.props.src).toBe("/api/paperwork/patch_sheet/content");
  });

  it("the close button fires onClose", () => {
    const onClose = vi.fn();
    const element = panelView({ onClose });
    const header = childArray(sidebarOf(element)).find((child) =>
      isElementWithClassName(child, "paperwork-header"),
    ) as ReactElement;
    const closeButton = childArray(header).find(
      (child) => (child as ReactElement).props.className === "paperwork-close",
    ) as ReactElement;
    closeButton.props.onClick();
    expect(onClose).toHaveBeenCalled();
  });
});

describe("parsePaperworkListResponse", () => {
  it("parses kinds + per-kind last_results", () => {
    const parsed = parsePaperworkListResponse(
      JSON.stringify({
        kinds: ["patch_sheet", "cue_sheet", "preset_list"],
        last_results: { patch_sheet: null, cue_sheet: CUE_SHEET_TRUNCATED, preset_list: null },
      }),
    );
    expect(parsed?.kinds).toEqual(["patch_sheet", "cue_sheet", "preset_list"]);
    expect(parsed?.lastResults.cue_sheet).toEqual(CUE_SHEET_TRUNCATED);
  });

  it("returns null on malformed JSON", () => {
    expect(parsePaperworkListResponse("not json")).toBeNull();
  });

  it("returns null when kinds is not an array of strings", () => {
    expect(parsePaperworkListResponse(JSON.stringify({ kinds: [1, 2, 3] }))).toBeNull();
  });
});

describe("parsePaperworkGenerateResponse", () => {
  it("parses a 200 success body into ok:true with derived badges", () => {
    const outcome = parsePaperworkGenerateResponse(
      "patch_sheet",
      200,
      JSON.stringify({ ok: true, kind: "patch_sheet", ...PATCH_SHEET_INCOMPLETE }),
    );
    expect(outcome.ok).toBe(true);
    if (outcome.ok) {
      expect(outcome.summary.path).toBe(PATCH_SHEET_INCOMPLETE.path);
      expect(outcome.badges).toContain("불완전");
    }
  });

  it("④ capability_unavailable(503)와 query_failed(502)는 서로 다른 message로 도착한다", () => {
    const capability = parsePaperworkGenerateResponse(
      "patch_sheet",
      503,
      JSON.stringify({
        detail: { error: "capability_unavailable", message: "property reads are not wired" },
      }),
    );
    const queryFailed = parsePaperworkGenerateResponse(
      "patch_sheet",
      502,
      JSON.stringify({
        detail: { error: "query_failed", message: "fixture inventory unreadable: boom" },
      }),
    );
    expect(capability.ok).toBe(false);
    expect(queryFailed.ok).toBe(false);
    if (!capability.ok && !queryFailed.ok) {
      expect(capability.message).not.toBe(queryFailed.message);
    }
  });

  it("falls back to a generic message when the body has no message field", () => {
    const outcome = parsePaperworkGenerateResponse("cue_sheet", 500, JSON.stringify({}));
    expect(outcome).toEqual({ ok: false, message: "생성에 실패했습니다." });
  });

  it("returns ok:false on malformed JSON rather than throwing", () => {
    const outcome = parsePaperworkGenerateResponse("cue_sheet", 200, "not json");
    expect(outcome.ok).toBe(false);
  });
});

describe("contentUrl / downloadUrl", () => {
  it("builds the same-origin API urls for preview and download", () => {
    expect(contentUrl("patch_sheet")).toBe("/api/paperwork/patch_sheet/content");
    expect(downloadUrl("magic_sheet")).toBe("/api/paperwork/magic_sheet/download");
  });
});

describe("fetch wrappers — ② 생성 클릭 시 fetch 호출 (실제 네트워크 계층)", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("fetchPaperworkList calls GET /api/paperwork", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      text: () =>
        Promise.resolve(
          JSON.stringify({
            kinds: ["patch_sheet", "cue_sheet", "preset_list"],
            last_results: { patch_sheet: null, cue_sheet: null, preset_list: null },
          }),
        ),
    });
    vi.stubGlobal("fetch", fetchMock);

    const parsed = await fetchPaperworkList();

    expect(fetchMock).toHaveBeenCalledWith("/api/paperwork");
    expect(parsed?.kinds).toEqual(["patch_sheet", "cue_sheet", "preset_list"]);
  });

  it("generatePaperworkDocument POSTs /api/paperwork/{kind}", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      status: 200,
      text: () => Promise.resolve(JSON.stringify({ ok: true, kind: "cue_sheet", ...CUE_SHEET_TRUNCATED })),
    });
    vi.stubGlobal("fetch", fetchMock);

    const outcome = await generatePaperworkDocument("cue_sheet");

    expect(fetchMock).toHaveBeenCalledWith("/api/paperwork/cue_sheet", { method: "POST" });
    expect(outcome.ok).toBe(true);
  });

  it("a 502 query_failed response surfaces as ok:false with the server message", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      status: 502,
      text: () =>
        Promise.resolve(
          JSON.stringify({
            detail: { error: "query_failed", message: "the sequences pool did not arrive: console_unreachable" },
          }),
        ),
    });
    vi.stubGlobal("fetch", fetchMock);

    const outcome = await generatePaperworkDocument("cue_sheet");

    expect(outcome).toEqual({
      ok: false,
      message: "the sequences pool did not arrive: console_unreachable",
    });
  });
});

describe("render() smoke — PaperworkPanelView descends into real PaperworkCard elements", () => {
  it("a card pulled from the rendered tree, re-rendered one level deeper, shows its label", () => {
    const firstCard = (childArray(cardsBoxOf(panelView())) as ReactElement[])[0];
    const rendered = render(firstCard);
    const head = childArray(rendered).find((child) =>
      isElementWithClassName(child, "paperwork-card-head"),
    ) as ReactElement;
    const label = childArray(head).find(
      (child) => (child as ReactElement).props.className === "paperwork-card-label",
    ) as ReactElement;
    expect(childArray(label)).toEqual(["패치시트"]);
  });
});
