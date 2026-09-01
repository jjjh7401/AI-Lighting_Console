// Settings API client tests (M3 — REQ-DEPLOY-005/007, AC-DEPLOY-003).
//
// Mirrors protocol.test.ts: this project has no DOM/jsdom harness, so the
// SettingsPanel component's logic lives in the pure functions of settings.ts
// (parse / build / validate / onboarding), and these exercise them directly.
import { describe, expect, it } from "vitest";

import {
  buildKeyPayload,
  buildSettingsPayload,
  formFromSettings,
  missingKeyProviders,
  onboardingMessage,
  parseSettingsResponse,
  validateSettingsForm,
  type EffectiveSettings,
  type SettingsForm,
  type SettingsResponse,
} from "./settings";

const EFFECTIVE: EffectiveSettings = {
  active_provider: "gemini",
  claude_code_model: "sonnet",
  console_host: "127.0.0.1",
  console_port: 8000,
  receive_port: 9000,
  web_host: "127.0.0.1",
  web_port: 8765,
  plugin_import_dir: "/home/op/plugins",
  osc_slot: 1,
};

const RESPONSE: SettingsResponse = {
  settings: EFFECTIVE,
  providers: ["anthropic", "claude_code", "gemini"],
  keys: { anthropic: false, claude_code: false, gemini: false },
  keystore_available: true,
  claude_code: {
    available: true,
    logged_in: false,
    model_options: ["opus", "sonnet", "fable"],
  },
  active_model: "gemini-3.5-flash",
};

function validForm(): SettingsForm {
  return {
    active_provider: "gemini",
    claude_code_model: "sonnet",
    console_port: 8000,
    receive_port: 9000,
    plugin_import_dir: "/home/op/plugins",
    osc_slot: 1,
  };
}

describe("parseSettingsResponse", () => {
  it("parses a well-formed response", () => {
    const parsed = parseSettingsResponse(JSON.stringify(RESPONSE));
    expect(parsed).not.toBeNull();
    expect(parsed!.settings.console_port).toBe(8000);
    expect(parsed!.keys.gemini).toBe(false);
    expect(parsed!.keystore_available).toBe(true);
  });

  it("returns null on invalid JSON", () => {
    expect(parseSettingsResponse("{not json")).toBeNull();
  });

  it("returns null when the settings block is missing", () => {
    expect(parseSettingsResponse(JSON.stringify({ providers: [], keys: {} }))).toBeNull();
  });
});

describe("formFromSettings", () => {
  it("extracts the editable non-sensitive subset", () => {
    const form = formFromSettings(EFFECTIVE);
    expect(form).toEqual({
      active_provider: "gemini",
      claude_code_model: "sonnet",
      console_port: 8000,
      receive_port: 9000,
      plugin_import_dir: "/home/op/plugins",
      osc_slot: 1,
    });
  });
});

describe("validateSettingsForm", () => {
  it("accepts a valid form", () => {
    expect(validateSettingsForm(validForm())).toEqual([]);
  });

  it("rejects an out-of-range console port", () => {
    const errors = validateSettingsForm({ ...validForm(), console_port: 70000 });
    expect(errors.length).toBeGreaterThan(0);
    expect(errors.join(" ")).toContain("콘솔");
  });

  it("rejects a zero / negative receive port", () => {
    expect(validateSettingsForm({ ...validForm(), receive_port: 0 }).length).toBeGreaterThan(0);
  });

  it("rejects a non-integer port", () => {
    expect(validateSettingsForm({ ...validForm(), console_port: 80.5 }).length).toBeGreaterThan(0);
  });

  it("rejects an empty plugin import directory", () => {
    expect(validateSettingsForm({ ...validForm(), plugin_import_dir: "  " }).length).toBeGreaterThan(
      0,
    );
  });

  it("rejects an unsupported provider", () => {
    expect(
      validateSettingsForm({ ...validForm(), active_provider: "openai" }).length,
    ).toBeGreaterThan(0);
  });
});

describe("buildSettingsPayload", () => {
  it("serialises exactly the non-sensitive form fields", () => {
    const body = JSON.parse(buildSettingsPayload(validForm()));
    expect(body).toEqual({
      active_provider: "gemini",
      claude_code_model: "sonnet",
      console_port: 8000,
      receive_port: 9000,
      plugin_import_dir: "/home/op/plugins",
      osc_slot: 1,
    });
    // A key value must never ride the settings payload.
    expect("key" in body).toBe(false);
    expect("api_key" in body).toBe(false);
  });
});

// 키 픽스처는 실제 키 접두사(sk- / ghp_ / AKIA / AIza+35자)를 흉내 내지 않는다.
// 흉내 내면 astgrep 규칙 sec-hardcoded-credential-typescript 가 매 커밋마다 error 를
// 내고, 매 커밋 울리는 경고는 읽히지 않는 경고가 된다.
// buildKeyPayload 는 값을 그대로 실어 보내는 패스스루라 값의 "모양"은 아무것도 검증하지 않는다.
describe("buildKeyPayload", () => {
  it("carries provider + key, no session flag by default", () => {
    const body = JSON.parse(buildKeyPayload("gemini", "gemini-test-key"));
    expect(body.provider).toBe("gemini");
    expect(body.key).toBe("gemini-test-key");
    expect("session_only" in body).toBe(false);
  });

  it("includes session_only when the session fallback is chosen", () => {
    const body = JSON.parse(buildKeyPayload("anthropic", "anthropic-test-key", true));
    expect(body.session_only).toBe(true);
  });
});

describe("missingKeyProviders", () => {
  it("lists only the providers whose key is unset", () => {
    expect(missingKeyProviders({ anthropic: false, gemini: true })).toEqual(["anthropic"]);
  });
});

describe("onboardingMessage", () => {
  it("prompts when the active provider's key is unset", () => {
    const message = onboardingMessage(RESPONSE);
    expect(message).not.toBeNull();
    expect(message!).toContain("Gemini");
  });

  it("is silent once the active provider has a key", () => {
    const ready: SettingsResponse = {
      ...RESPONSE,
      keys: { anthropic: false, gemini: true },
    };
    expect(onboardingMessage(ready)).toBeNull();
  });
});

// The console's OSC reply row is per-site: on this rig row 1 targets the
// broadcast address 192.168.0.255 and never reaches the app, so replies must
// go out on row 2. It used to be a hand-edit of the installed Lua that every
// re-provision silently reverted; surfacing it here is what lets the operator
// set it once.
describe("osc_slot", () => {
  it("rides the settings payload so the backend can render it into the Lua", () => {
    const body = JSON.parse(buildSettingsPayload({ ...validForm(), osc_slot: 2 }));
    expect(body.osc_slot).toBe(2);
  });

  it("is carried from the effective settings into the editable form", () => {
    expect(formFromSettings({ ...EFFECTIVE, osc_slot: 3 }).osc_slot).toBe(3);
  });

  it("rejects a value outside the OSC row range", () => {
    expect(validateSettingsForm({ ...validForm(), osc_slot: 0 })).not.toEqual([]);
    expect(validateSettingsForm({ ...validForm(), osc_slot: 99 })).not.toEqual([]);
  });

  it("rejects a port number pasted into the row field", () => {
    // The neighbouring inputs are all ports, so this is the likely slip — and
    // the only symptom would be a console that silently stops replying.
    expect(validateSettingsForm({ ...validForm(), osc_slot: 9000 })).not.toEqual([]);
  });

  it("accepts the rows an operator actually uses", () => {
    expect(validateSettingsForm({ ...validForm(), osc_slot: 1 })).toEqual([]);
    expect(validateSettingsForm({ ...validForm(), osc_slot: 2 })).toEqual([]);
  });
});
