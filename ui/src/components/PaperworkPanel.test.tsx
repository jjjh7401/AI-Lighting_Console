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

import { describe, expect, it, vi, afterEach } from "vitest";
import {
  PAPERWORK_KINDS,
  PaperworkCard,
  PaperworkPanelView,
  contentUrl,
  downloadUrl,
  fetchPaperworkList,
  generatePaperworkDocument,
  paperworkBadges,
  paperworkStatLine,
  parsePaperworkGenerateResponse,
  parsePaperworkListResponse,
  type PaperworkKind,
  type PaperworkSummary,
} from "./PaperworkPanel";

function childArray(element: ReactElement): unknown[] {
  const children = element.props.children;
  if (children === undefined) return [];
  const list = Array.isArray(children) ? children : [children];
  return list.filter((child) => child !== null && child !== undefined && child !== false);
}

/** Renders a function-component ReactElement one level deeper — same
 * technique CueMonitor.test.tsx uses for nested hook-free components. */
function render(element: ReactElement): ReactElement {
  return (element.type as (props: unknown) => ReactElement)(element.props);
}

function isElementWithClassName(value: unknown, className: string): value is ReactElement {
  if (value === null || value === undefined || typeof value !== "object") return false;
  const element = value as ReactElement;
  if (typeof element.type === "string") return element.props.className === className;
  return false;
}

const PATCH_SHEET_COMPLETE: PaperworkSummary = {
  path: "/tmp/paperwork_output/patch_sheet.html",
  fixture_count: 18,
  child_count: 18,
  completeness: "complete",
};

const PATCH_SHEET_INCOMPLETE: PaperworkSummary = {
  path: "/tmp/paperwork_output/patch_sheet.html",
  fixture_count: 18,
  child_count: 19,
  completeness: "incomplete",
};

const CUE_SHEET_TRUNCATED: PaperworkSummary = {
  path: "/tmp/paperwork_output/cue_sheet.html",
  sequence_count: 5,
  cue_count: 42,
  truncated: true,
  drilldown_capped: true,
};

const PRESET_LIST_CLEAN: PaperworkSummary = {
  path: "/tmp/paperwork_output/preset_list.html",
  pool_count: 3,
  preset_count: 12,
  truncated: false,
  drilldown_capped: false,
};

describe("paperworkBadges — ③ 불완전성 배지가 응답 플래그에 따라 나타난다/사라진다", () => {
  it("patch_sheet — count mismatch + incomplete", () => {
    const badges = paperworkBadges("patch_sheet", PATCH_SHEET_INCOMPLETE);
    expect(badges).toContain("관측 18 / 선언 19");
    expect(badges).toContain("불완전");
  });

  it("patch_sheet — matching counts and complete → no badges", () => {
    expect(paperworkBadges("patch_sheet", PATCH_SHEET_COMPLETE)).toEqual([]);
  });

  it("cue_sheet — truncated + drilldown_capped", () => {
    const badges = paperworkBadges("cue_sheet", CUE_SHEET_TRUNCATED);
    expect(badges).toContain("절단됨");
    expect(badges).toContain("드릴다운 상한");
  });

  it("preset_list — clean → no badges", () => {
    expect(paperworkBadges("preset_list", PRESET_LIST_CLEAN)).toEqual([]);
  });
});

describe("paperworkStatLine", () => {
  it("patch_sheet shows fixture count", () => {
    expect(paperworkStatLine("patch_sheet", PATCH_SHEET_COMPLETE)).toBe("픽스처 18대");
  });
  it("cue_sheet shows sequence + cue count", () => {
    expect(paperworkStatLine("cue_sheet", CUE_SHEET_TRUNCATED)).toBe("시퀀스 5개 · 큐 42개");
  });
  it("preset_list shows pool + preset count", () => {
    expect(paperworkStatLine("preset_list", PRESET_LIST_CLEAN)).toBe("풀 3개 · 프리셋 12개");
  });
});

describe("contentUrl / downloadUrl", () => {
  it("contentUrl builds the content endpoint path", () => {
    expect(contentUrl("patch_sheet")).toBe("/api/paperwork/patch_sheet/content");
  });
  it("downloadUrl builds the download endpoint path", () => {
    expect(downloadUrl("cue_sheet")).toBe("/api/paperwork/cue_sheet/download");
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
  const cardProps = (overrides: Partial<Parameters<typeof PaperworkCard>[0]> = {}) => ({
    meta: PAPERWORK_KINDS[0],
    result: null as PaperworkSummary | null,
    busy: false,
    previewing: false,
    onGenerate: vi.fn(),
    onPreview: vi.fn(),
    onDownload: vi.fn(),
    ...overrides,
  });

  it("renders the kind label and a [생성] button when no result yet", () => {
    const element = PaperworkCard(cardProps());
    const children = childArray(element);
    const head = children.find((child) => isElementWithClassName(child, "paperwork-card-head"));
    expect(head).toBeDefined();
    const headChildren = childArray(head as ReactElement);
    const label = headChildren.find((child) => isElementWithClassName(child, "paperwork-card-label"));
    expect(childArray(label as ReactElement)).toEqual(["패치시트"]);
    // No result yet -> no actions section.
    const actions = children.find((child) => isElementWithClassName(child, "paperwork-card-actions"));
    expect(actions).toBeUndefined();
  });

  it("② 생성 클릭 시 onGenerate(kind)가 호출된다", () => {
    const onGenerate = vi.fn();
    const element = PaperworkCard(cardProps({ meta: PAPERWORK_KINDS[1], onGenerate }));
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
    const element = PaperworkCard(cardProps({ busy: true }));
    const head = childArray(element).find((child) =>
      isElementWithClassName(child, "paperwork-card-head"),
    ) as ReactElement;
    const button = childArray(head).find(
      (child) => (child as ReactElement).props.className === "paperwork-card-generate",
    ) as ReactElement;
    expect(button.props.disabled).toBe(true);
    expect(childArray(button)).toEqual(["생성 중…"]);
  });

  it("shows '새로고침' when a result exists", () => {
    const element = PaperworkCard(cardProps({ result: PATCH_SHEET_COMPLETE }));
    const head = childArray(element).find((child) =>
      isElementWithClassName(child, "paperwork-card-head"),
    ) as ReactElement;
    const button = childArray(head).find(
      (child) => (child as ReactElement).props.className === "paperwork-card-generate",
    ) as ReactElement;
    expect(childArray(button)).toEqual(["새로고침"]);
  });

  it("③ 배지가 나타난다 — an incomplete result shows badges", () => {
    const element = PaperworkCard(cardProps({ result: PATCH_SHEET_INCOMPLETE }));
    const actions = childArray(element).find((child) =>
      isElementWithClassName(child, "paperwork-card-actions"),
    ) as ReactElement;
    expect(actions).toBeDefined();
    const badgesBox = childArray(actions).find((child) =>
      isElementWithClassName(child, "paperwork-card-badges"),
    ) as ReactElement;
    const badgeTexts = childArray(badgesBox).map((badge) => childArray(badge as ReactElement)[0]);
    expect(badgeTexts).toEqual(expect.arrayContaining(["관측 18 / 선언 19", "불완전"]));
  });

  it("③ 배지가 사라진다 — a complete result shows no badges box at all", () => {
    const element = PaperworkCard(cardProps({ result: PATCH_SHEET_COMPLETE }));
    const actions = childArray(element).find((child) =>
      isElementWithClassName(child, "paperwork-card-actions"),
    ) as ReactElement;
    const badgesBox = childArray(actions).find((child) =>
      isElementWithClassName(child, "paperwork-card-badges"),
    );
    expect(badgesBox).toBeUndefined();
  });

  it("미리보기 button fires onPreview(kind)", () => {
    const onPreview = vi.fn();
    const element = PaperworkCard(cardProps({ result: PATCH_SHEET_COMPLETE, onPreview }));
    const actions = childArray(element).find((child) =>
      isElementWithClassName(child, "paperwork-card-actions"),
    ) as ReactElement;
    const buttonsBox = childArray(actions).find((child) =>
      isElementWithClassName(child, "paperwork-card-buttons"),
    ) as ReactElement;
    const previewBtn = childArray(buttonsBox).find(
      (child) => (child as ReactElement).props.className?.includes("paperwork-card-preview"),
    ) as ReactElement;
    previewBtn.props.onClick();
    expect(onPreview).toHaveBeenCalledWith("patch_sheet");
  });

  it("다운로드 button fires onDownload(kind)", () => {
    const onDownload = vi.fn();
    const element = PaperworkCard(cardProps({ result: PATCH_SHEET_COMPLETE, onDownload }));
    const actions = childArray(element).find((child) =>
      isElementWithClassName(child, "paperwork-card-actions"),
    ) as ReactElement;
    const buttonsBox = childArray(actions).find((child) =>
      isElementWithClassName(child, "paperwork-card-buttons"),
    ) as ReactElement;
    const downloadBtn = childArray(buttonsBox).find(
      (child) => (child as ReactElement).props.className === "paperwork-card-download",
    ) as ReactElement;
    downloadBtn.props.onClick();
    expect(onDownload).toHaveBeenCalledWith("patch_sheet");
  });

  it("stat line shows kind-specific summary", () => {
    const element = PaperworkCard(cardProps({ result: PATCH_SHEET_COMPLETE }));
    const head = childArray(element).find((child) =>
      isElementWithClassName(child, "paperwork-card-head"),
    ) as ReactElement;
    const stat = childArray(head).find((child) =>
      isElementWithClassName(child, "paperwork-card-stat"),
    ) as ReactElement;
    expect(childArray(stat)).toEqual(["픽스처 18대"]);
  });
});

describe("PaperworkPanelView — ① 4종 렌더", () => {
  const viewProps = (overrides: Partial<Parameters<typeof PaperworkPanelView>[0]> = {}) => ({
    results: {} as Record<string, PaperworkSummary | null>,
    busyKind: null as PaperworkKind | null,
    previewKind: null as PaperworkKind | null,
    onGenerate: vi.fn(),
    onPreview: vi.fn(),
    onDownload: vi.fn(),
    ...overrides,
  });
  it("renders exactly one card per PAPERWORK_KINDS entry, in order", () => {
    const element = PaperworkPanelView(viewProps());
    const children = childArray(element);
    const cardsBox = children.find((child) =>
      isElementWithClassName(child, "paperwork-cards"),
    ) as ReactElement;
    const cards = childArray(cardsBox) as ReactElement[];
    expect(cards).toHaveLength(4);
    expect(cards.map((card) => card.props.meta.kind)).toEqual([
      "patch_sheet",
      "cue_sheet",
      "preset_list",
      "magic_sheet",
    ]);
  });

  it("passes each kind's own result (or null) down to its card, keyed by kind", () => {
    const element = PaperworkPanelView(viewProps({ results: { cue_sheet: CUE_SHEET_TRUNCATED } }));
    const cardsBox = childArray(element).find((child) =>
      isElementWithClassName(child, "paperwork-cards"),
    ) as ReactElement;
    const cards = childArray(cardsBox) as ReactElement[];
    expect(cards[0].props.result).toBeNull(); // patch_sheet: no last_result
    expect(cards[1].props.result).toBe(CUE_SHEET_TRUNCATED); // cue_sheet
    expect(cards[2].props.result).toBeNull(); // preset_list
    expect(cards[3].props.result).toBeNull(); // magic_sheet
  });

  it("marks only the busy kind's card as busy", () => {
    const element = PaperworkPanelView(viewProps({ busyKind: "preset_list" }));
    const cardsBox = childArray(element).find((child) =>
      isElementWithClassName(child, "paperwork-cards"),
    ) as ReactElement;
    const cards = childArray(cardsBox) as ReactElement[];
    expect(cards.map((card) => card.props.busy)).toEqual([false, false, true, false]);
  });

  it("renders a notice line only when one is present", () => {
    const withoutNotice = PaperworkPanelView(viewProps());
    expect(
      childArray(withoutNotice).some((child) => isElementWithClassName(child, "paperwork-notice")),
    ).toBe(false);

    const withNotice = PaperworkPanelView(viewProps({ notice: "문서 생성 중 오류가 발생했습니다." }));
    const notice = childArray(withNotice).find((child) =>
      isElementWithClassName(child, "paperwork-notice"),
    ) as ReactElement;
    expect(childArray(notice)).toEqual(["문서 생성 중 오류가 발생했습니다."]);
  });

  it("renders iframe preview when previewKind is set", () => {
    const element = PaperworkPanelView(viewProps({ previewKind: "cue_sheet" }));
    const preview = childArray(element).find((child) =>
      isElementWithClassName(child, "paperwork-preview"),
    ) as ReactElement;
    expect(preview).toBeDefined();
    const iframe = childArray(preview).find(
      (child) => (child as ReactElement).type === "iframe",
    ) as ReactElement;
    expect(iframe.props.src).toBe("/api/paperwork/cue_sheet/content");
  });

  it("no iframe when previewKind is null", () => {
    const element = PaperworkPanelView(viewProps());
    const preview = childArray(element).find((child) =>
      isElementWithClassName(child, "paperwork-preview"),
    );
    expect(preview).toBeUndefined();
  });

  it("the close button fires onClose", () => {
    const onClose = vi.fn();
    const element = PaperworkPanelView(viewProps({ onClose }));
    const header = childArray(element).find((child) =>
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
    const element = PaperworkPanelView({
      results: {},
      busyKind: null,
      notice: null,
      previewKind: null,
      onGenerate: vi.fn(),
      onPreview: vi.fn(),
      onDownload: vi.fn(),
      onClose: vi.fn(),
    });
    const cardsBox = childArray(element).find((child) =>
      isElementWithClassName(child, "paperwork-cards"),
    ) as ReactElement;
    const firstCard = (childArray(cardsBox) as ReactElement[])[0];
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
