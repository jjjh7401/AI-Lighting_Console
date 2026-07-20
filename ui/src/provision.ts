// Responder provisioning API client (M4 — REQ-DEPLOY-010/011, AC-DEPLOY-006/007).
//
// Pure functions only (parse / status / install-summary) so the module is
// unit-testable without a DOM, matching settings.ts. The ResponderGuide component
// consumes these and owns the fetch() calls + React state.
//
// This layer NEVER sends an OSC command: provisioning is a filesystem copy plus a
// human-facing guide. Only the file copy is off-gate; the ``Import Plugin`` console
// send (deploy path) transits the single safety gate on the backend (REQ-DEPLOY-011a).

export const RESPONDER_ASSETS = ["copilot_responder.xml", "copilot_responder.lua"] as const;

// -- server response shapes (mirror server/web/provision_api.py) --------------

export interface ResponderGuide {
  receive_port: number;
  steps: string[];
}

export interface ResponderStatusResponse {
  import_dir: string;
  assets: string[];
  installed: Record<string, boolean>;
  installed_all: boolean;
  guide: ResponderGuide;
}

function isGuide(value: unknown): value is ResponderGuide {
  if (typeof value !== "object" || value === null) return false;
  const guide = value as { receive_port?: unknown; steps?: unknown };
  return typeof guide.receive_port === "number" && Array.isArray(guide.steps);
}

/** Parse a GET/POST /api/provision/responder status response; a shape mismatch
 *  returns null so the caller keeps its prior state rather than crashing
 *  (boundary discipline, matching settings.ts). */
export function parseResponderStatus(raw: string): ResponderStatusResponse | null {
  let data: unknown;
  try {
    data = JSON.parse(raw);
  } catch {
    return null;
  }
  if (typeof data !== "object" || data === null) return null;
  const record = data as {
    import_dir?: unknown;
    installed?: unknown;
    guide?: unknown;
  };
  if (typeof record.import_dir !== "string") return null;
  if (typeof record.installed !== "object" || record.installed === null) return null;
  if (!isGuide(record.guide)) return null;
  return data as ResponderStatusResponse;
}

/** Whether every bundled asset is installed in the import directory. */
export function allInstalled(status: ResponderStatusResponse): boolean {
  if (status.installed_all) return true;
  const values = Object.values(status.installed);
  return values.length > 0 && values.every(Boolean);
}

/** Extract the ``installed`` filename list from a POST /api/provision/responder
 *  body. The POST response shape (a string array of copied files) differs from
 *  the GET status shape (a per-asset boolean map), so it has its own parser. A
 *  shape mismatch yields an empty list rather than throwing. */
export function parseInstalledList(raw: string): string[] {
  let data: unknown;
  try {
    data = JSON.parse(raw);
  } catch {
    return [];
  }
  if (typeof data !== "object" || data === null) return [];
  const installed = (data as { installed?: unknown }).installed;
  if (!Array.isArray(installed)) return [];
  return installed.filter((entry): entry is string => typeof entry === "string");
}

/** Korean confirmation naming the files just installed (REQ-DEPLOY-010). */
export function installSummary(installed: string[]): string {
  if (installed.length === 0) {
    return "설치된 파일이 없습니다.";
  }
  return `responder 플러그인을 설치했습니다: ${installed.join(", ")}`;
}
