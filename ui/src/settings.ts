// In-app settings + secure-key API client (M3 — REQ-DEPLOY-005/007, AC-DEPLOY-003).
//
// Pure functions only (parse / build / validate / onboarding) so the module is
// unit-testable without a DOM, matching protocol.ts. The SettingsPanel component
// consumes these and owns the fetch() calls + React state.
//
// SECURITY: a key value NEVER rides the settings payload and is NEVER returned by
// GET /api/settings — the server exposes only a per-provider "key set" boolean.

export const PROVIDERS = ["anthropic", "claude_code", "gemini", "ollama"] as const;
export type ProviderId = (typeof PROVIDERS)[number];

export const PROVIDER_LABELS: Record<string, string> = {
  anthropic: "Anthropic API",
  claude_code: "Claude 구독",
  gemini: "Gemini",
  ollama: "로컬 (오프라인)",
};

/** API 키가 필요 없는 프로바이더 — 키 입력칸을 아예 만들지 않는다.
 *
 *  `claude_code`는 구독 OAuth 세션을 Keychain이 들고 있고, `ollama`는 이
 *  기계에서 돈다. 서버의 `_PROVIDER_ENV_VARS`에 항목이 없는 것과 같은 집합이다
 *  — 한쪽만 늘리면 있지도 않은 키를 입력하라는 칸이 생긴다. */
export const KEYLESS_PROVIDERS: readonly string[] = ["claude_code", "ollama"];

export function providerLabel(provider: string): string {
  return PROVIDER_LABELS[provider] ?? provider;
}

export const MIN_PORT = 1;
export const MAX_PORT = 65535;
// An OSC settings ROW index on the console, not a port. The bound's job is to
// reject a port pasted into this field — every neighbouring input is a port,
// and a wrong row's only symptom is a console that silently stops replying.
// Mirrors _MIN_OSC_SLOT / _MAX_OSC_SLOT in server/deploy/settings.py.
export const MIN_OSC_SLOT = 1;
export const MAX_OSC_SLOT = 32;

// -- server response shapes (mirror server/web/settings_api.py) ---------------

export interface EffectiveSettings {
  active_provider: string;
  claude_code_model: string;
  console_host: string;
  console_port: number;
  receive_port: number;
  web_host: string;
  web_port: number;
  plugin_import_dir: string;
  osc_slot: number;
}

export interface ClaudeCodeStatus {
  available: boolean;
  logged_in: boolean;
  email?: string | null;
  subscription_type?: string | null;
  model_options: string[];
}
export interface SettingsResponse {
  settings: EffectiveSettings;
  providers: string[];
  keys: Record<string, boolean>;
  keystore_available: boolean;
  claude_code: ClaudeCodeStatus;
  active_model: string | null;
}

/** Parse a GET /api/settings response; a shape mismatch returns null so the
 *  caller keeps its prior state rather than crashing (boundary discipline). */
export function parseSettingsResponse(raw: string): SettingsResponse | null {
  let data: unknown;
  try {
    data = JSON.parse(raw);
  } catch {
    return null;
  }
  if (typeof data !== "object" || data === null) return null;
  const record = data as {
    settings?: unknown;
    providers?: unknown;
    keys?: unknown;
    keystore_available?: unknown;
    claude_code?: unknown;
    active_model?: unknown;
  };
  if (typeof record.settings !== "object" || record.settings === null) return null;
  if (!Array.isArray(record.providers)) return null;
  if (typeof record.keys !== "object" || record.keys === null) return null;
  if (typeof record.claude_code !== "object" || record.claude_code === null) return null;
  if (typeof record.active_model !== "string" && record.active_model !== null) return null;
  return data as SettingsResponse;
}

// -- editable non-sensitive form ----------------------------------------------

// The subset the UI edits. Web host/port are shown read-only (REQ-DEPLOY-005),
// so they are not part of the editable form.
export interface SettingsForm {
  active_provider: string;
  claude_code_model: string;
  console_port: number;
  receive_port: number;
  plugin_import_dir: string;
  osc_slot: number;
}

export function formFromSettings(settings: EffectiveSettings): SettingsForm {
  return {
    active_provider: settings.active_provider,
    claude_code_model: settings.claude_code_model,
    console_port: settings.console_port,
    receive_port: settings.receive_port,
    plugin_import_dir: settings.plugin_import_dir,
    osc_slot: settings.osc_slot,
  };
}

function portError(label: string, value: number): string | null {
  if (!Number.isInteger(value) || value < MIN_PORT || value > MAX_PORT) {
    return `${label} 포트는 ${MIN_PORT}–${MAX_PORT} 범위의 정수여야 합니다.`;
  }
  return null;
}

function oscSlotError(value: number): string | null {
  if (!Number.isInteger(value) || value < MIN_OSC_SLOT || value > MAX_OSC_SLOT) {
    return `OSC 응답 행은 ${MIN_OSC_SLOT}–${MAX_OSC_SLOT} 범위의 정수여야 합니다 (포트 번호가 아닙니다).`;
  }
  return null;
}

/** Client-side validation mirroring the backend (M1) — a fast local check before
 *  the POST; the server remains the authority and re-validates. */
export function validateSettingsForm(form: SettingsForm): string[] {
  const errors: string[] = [];
  const consolePortError = portError("콘솔 송신", form.console_port);
  if (consolePortError) errors.push(consolePortError);
  const receivePortError = portError("피드백 수신", form.receive_port);
  if (receivePortError) errors.push(receivePortError);
  const slotError = oscSlotError(form.osc_slot);
  if (slotError) errors.push(slotError);
  if (form.plugin_import_dir.trim() === "") {
    errors.push("플러그인 임포트 디렉터리를 입력해 주세요.");
  }
  if (!(PROVIDERS as readonly string[]).includes(form.active_provider)) {
    errors.push(`활성 프로바이더는 ${PROVIDERS.join(" / ")} 중 하나여야 합니다.`);
  }
  if (!["opus", "sonnet", "fable"].includes(form.claude_code_model)) {
    errors.push("Claude 모델은 Opus / Sonnet / Fable 중 하나여야 합니다.");
  }
  return errors;
}

// -- request builders ----------------------------------------------------------

/** Build the POST /api/settings body — the non-sensitive settings ONLY (a key
 *  never rides this payload). */
export function buildSettingsPayload(form: SettingsForm): string {
  return JSON.stringify({
    active_provider: form.active_provider,
    claude_code_model: form.claude_code_model,
    console_port: form.console_port,
    receive_port: form.receive_port,
    plugin_import_dir: form.plugin_import_dir,
    osc_slot: form.osc_slot,
  });
}

/** Build the POST /api/keys body. ``session_only`` is included only when the
 *  session fallback is explicitly chosen (keystore unavailable path). */
export function buildKeyPayload(provider: string, key: string, sessionOnly = false): string {
  const body: { provider: string; key: string; session_only?: boolean } = { provider, key };
  if (sessionOnly) body.session_only = true;
  return JSON.stringify(body);
}

/** Providers whose key is unset. */
export function missingKeyProviders(keys: Record<string, boolean>): string[] {
  return Object.keys(keys).filter((provider) => !keys[provider] && provider !== "claude_code");
}

/** Non-intrusive onboarding (REQ-DEPLOY-005, first-run banner not a wizard). */
export function onboardingMessage(response: SettingsResponse): string | null {
  const active = response.settings.active_provider;
  if (active === "claude_code") {
    return response.claude_code.logged_in
      ? null
      : "Claude 구독 로그인이 필요합니다 — 설정에서 Claude로 로그인해 주세요.";
  }
  if (response.keys[active]) return null;
  return `${providerLabel(active)} API 키가 설정되지 않았습니다 — 설정에서 키를 입력해 주세요.`;
}
