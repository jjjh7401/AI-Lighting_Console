// In-app settings + secure-key API client (M3 — REQ-DEPLOY-005/007, AC-DEPLOY-003).
//
// Pure functions only (parse / build / validate / onboarding) so the module is
// unit-testable without a DOM, matching protocol.ts. The SettingsPanel component
// consumes these and owns the fetch() calls + React state.
//
// SECURITY: a key value NEVER rides the settings payload and is NEVER returned by
// GET /api/settings — the server exposes only a per-provider "key set" boolean.

export const PROVIDERS = ["anthropic", "gemini"] as const;
export type ProviderId = (typeof PROVIDERS)[number];

export const PROVIDER_LABELS: Record<string, string> = {
  anthropic: "Anthropic",
  gemini: "Gemini",
};

export function providerLabel(provider: string): string {
  return PROVIDER_LABELS[provider] ?? provider;
}

export const MIN_PORT = 1;
export const MAX_PORT = 65535;

// -- server response shapes (mirror server/web/settings_api.py) ---------------

export interface EffectiveSettings {
  active_provider: string;
  console_host: string;
  console_port: number;
  receive_port: number;
  web_host: string;
  web_port: number;
  plugin_import_dir: string;
}

export interface SettingsResponse {
  settings: EffectiveSettings;
  providers: string[];
  keys: Record<string, boolean>;
  keystore_available: boolean;
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
  };
  if (typeof record.settings !== "object" || record.settings === null) return null;
  if (!Array.isArray(record.providers)) return null;
  if (typeof record.keys !== "object" || record.keys === null) return null;
  return data as SettingsResponse;
}

// -- editable non-sensitive form ----------------------------------------------

// The subset the UI edits. Web host/port are shown read-only (REQ-DEPLOY-005),
// so they are not part of the editable form.
export interface SettingsForm {
  active_provider: string;
  console_port: number;
  receive_port: number;
  plugin_import_dir: string;
}

export function formFromSettings(settings: EffectiveSettings): SettingsForm {
  return {
    active_provider: settings.active_provider,
    console_port: settings.console_port,
    receive_port: settings.receive_port,
    plugin_import_dir: settings.plugin_import_dir,
  };
}

function portError(label: string, value: number): string | null {
  if (!Number.isInteger(value) || value < MIN_PORT || value > MAX_PORT) {
    return `${label} 포트는 ${MIN_PORT}–${MAX_PORT} 범위의 정수여야 합니다.`;
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
  if (form.plugin_import_dir.trim() === "") {
    errors.push("플러그인 임포트 디렉터리를 입력해 주세요.");
  }
  if (!(PROVIDERS as readonly string[]).includes(form.active_provider)) {
    errors.push(`활성 프로바이더는 ${PROVIDERS.join(" / ")} 중 하나여야 합니다.`);
  }
  return errors;
}

// -- request builders ----------------------------------------------------------

/** Build the POST /api/settings body — the non-sensitive settings ONLY (a key
 *  never rides this payload). */
export function buildSettingsPayload(form: SettingsForm): string {
  return JSON.stringify({
    active_provider: form.active_provider,
    console_port: form.console_port,
    receive_port: form.receive_port,
    plugin_import_dir: form.plugin_import_dir,
  });
}

/** Build the POST /api/keys body. ``session_only`` is included only when the
 *  session fallback is explicitly chosen (keystore unavailable path). */
export function buildKeyPayload(provider: string, key: string, sessionOnly = false): string {
  const body: { provider: string; key: string; session_only?: boolean } = { provider, key };
  if (sessionOnly) body.session_only = true;
  return JSON.stringify(body);
}

// -- onboarding (non-intrusive banner) ----------------------------------------

/** Providers whose key is unset. */
export function missingKeyProviders(keys: Record<string, boolean>): string[] {
  return Object.keys(keys).filter((provider) => !keys[provider]);
}

/** Non-intrusive onboarding (REQ-DEPLOY-005, first-run banner not a wizard):
 *  a Korean prompt when the ACTIVE provider's key is unset, else null. */
export function onboardingMessage(response: SettingsResponse): string | null {
  const active = response.settings.active_provider;
  if (response.keys[active]) return null;
  return `${providerLabel(active)} API 키가 설정되지 않았습니다 — 설정에서 키를 입력해 주세요.`;
}
