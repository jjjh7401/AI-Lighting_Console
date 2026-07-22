// Responder provisioning client tests (M4 — REQ-DEPLOY-010/011, AC-DEPLOY-006/007).
//
// Mirrors settings.test.ts: this project has no DOM/jsdom harness, so the
// ResponderGuide component's logic lives in the pure functions of provision.ts
// (parse / status / install-summary), and these exercise them directly.
import { describe, expect, it } from "vitest";

import {
  RESPONDER_ASSETS,
  allInstalled,
  installSummary,
  parseInstalledList,
  oscSlotWarning,
  parseResponderStatus,
  type ResponderStatusResponse,
} from "./provision";

const STATUS: ResponderStatusResponse = {
  import_dir: "/home/op/plugins",
  assets: ["copilot_responder.xml", "copilot_responder.lua"],
  installed: { "copilot_responder.xml": false, "copilot_responder.lua": false },
  installed_all: false,
  guide: {
    receive_port: 9000,
    steps: [
      "설치된 플러그인 파일이 onPC 플러그인 라이브러리 폴더에 있는지 확인합니다.",
      "onPC의 OSC 출력(Output)을 이 앱의 피드백 수신 포트(9000)로 설정합니다.",
    ],
  },
};

describe("RESPONDER_ASSETS", () => {
  it("is the native import XML + the Lua component", () => {
    expect([...RESPONDER_ASSETS]).toEqual(["copilot_responder.xml", "copilot_responder.lua"]);
  });
});

describe("parseResponderStatus", () => {
  it("parses a well-formed status response", () => {
    const parsed = parseResponderStatus(JSON.stringify(STATUS));
    expect(parsed).not.toBeNull();
    expect(parsed?.import_dir).toBe("/home/op/plugins");
    expect(parsed?.guide.receive_port).toBe(9000);
    expect(parsed?.guide.steps.length).toBe(2);
  });

  it("returns null on invalid JSON", () => {
    expect(parseResponderStatus("{not json")).toBeNull();
  });

  it("returns null when the guide is missing (boundary discipline)", () => {
    const bad = { ...STATUS } as Record<string, unknown>;
    delete bad.guide;
    expect(parseResponderStatus(JSON.stringify(bad))).toBeNull();
  });

  it("returns null when installed is not an object", () => {
    const bad = { ...STATUS, installed: 42 };
    expect(parseResponderStatus(JSON.stringify(bad))).toBeNull();
  });
});

describe("allInstalled", () => {
  it("is false when any asset is missing", () => {
    expect(allInstalled(STATUS)).toBe(false);
  });

  it("is true when the server reports installed_all", () => {
    const done: ResponderStatusResponse = {
      ...STATUS,
      installed: { "copilot_responder.xml": true, "copilot_responder.lua": true },
      installed_all: true,
    };
    expect(allInstalled(done)).toBe(true);
  });
});

describe("parseInstalledList", () => {
  it("extracts the installed filenames from a POST body", () => {
    const body = JSON.stringify({
      ok: true,
      installed: ["copilot_responder.xml", "copilot_responder.lua"],
    });
    expect(parseInstalledList(body)).toEqual([
      "copilot_responder.xml",
      "copilot_responder.lua",
    ]);
  });

  it("returns an empty list on invalid JSON or a missing field", () => {
    expect(parseInstalledList("{oops")).toEqual([]);
    expect(parseInstalledList(JSON.stringify({ ok: true }))).toEqual([]);
  });

  it("filters out non-string entries", () => {
    const body = JSON.stringify({ installed: ["a.lua", 42, null] });
    expect(parseInstalledList(body)).toEqual(["a.lua"]);
  });
});

describe("installSummary", () => {
  it("names the installed files in a Korean confirmation", () => {
    const message = installSummary(["copilot_responder.xml", "copilot_responder.lua"]);
    expect(message).toContain("copilot_responder.xml");
    expect(message).toContain("copilot_responder.lua");
  });

  it("handles an empty install list without crashing", () => {
    expect(typeof installSummary([])).toBe("string");
  });
});

// The rendered OSC reply row only helps if the setting is the right one. The
// shipped default is row 1 while the live rig replies on row 2, so installing
// before setting the row silently re-breaks the console link — the failure the
// rendering was added to prevent. The guard has to be legible in the UI, not
// only enforced by a 409 the operator sees as "설치 실패".
describe("oscSlotWarning", () => {
  it("is silent when the values agree", () => {
    expect(
      oscSlotWarning({ ...STATUS, configured_osc_slot: 2, installed_osc_slot: 2, osc_slot_mismatch: false }),
    ).toBeNull();
  });

  it("is silent on a first install", () => {
    expect(
      oscSlotWarning({ ...STATUS, configured_osc_slot: 2, installed_osc_slot: null, osc_slot_mismatch: false }),
    ).toBeNull();
  });

  it("names BOTH numbers so the operator can tell which way to resolve it", () => {
    const warning = oscSlotWarning({
      ...STATUS,
      configured_osc_slot: 1,
      installed_osc_slot: 2,
      osc_slot_mismatch: true,
    });
    expect(warning).not.toBeNull();
    expect(warning).toContain("1");
    expect(warning).toContain("2");
  });

  it("says the value is unknown rather than inventing one", () => {
    const warning = oscSlotWarning({
      ...STATUS,
      configured_osc_slot: 2,
      installed_osc_slot: null,
      osc_slot_mismatch: true,
    });
    expect(warning).not.toBeNull();
    expect(warning).toContain("확인할 수 없");
  });

  it("is silent when the server did not report the fields at all", () => {
    // An older backend must not make the UI shout about a mismatch it cannot
    // know about.
    expect(oscSlotWarning(STATUS)).toBeNull();
  });
});
