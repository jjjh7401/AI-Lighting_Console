// WebSocket protocol v1 — TypeScript mirror of server/web/PROTOCOL.md.
// Pure functions only (parse / build / reduce) so the module is unit-testable
// without a DOM; the socket hook and components consume it.

export const PROTOCOL_VERSION = 1;

export interface CommandView {
  command: string;
  status: string;
  label: string;
  detail: string;
}

export interface ApprovalItem {
  command: string;
  risk_reasons: string[];
  warnings: string[];
}

// -- M7 deploy review (REQ-MVP-019/027) ---------------------------------------

export interface ScanFinding {
  line: number;
  command: string;
  kind: string; // "blacklisted" | "invoking" | "unparseable"
  matched_entry: string | null;
  reasons: string[];
}

export interface DynamicCallView {
  line: number;
  snippet: string;
}

export interface ScanReportView {
  destructive: boolean;
  findings: ScanFinding[];
  dynamic_calls: DynamicCallView[];
  caveat: string;
}

export interface ReviewRequestView {
  request_id: string;
  plugin_name: string;
  source_preview: string;
  source_length: number;
  source_truncated: boolean;
  compile_ok: boolean;
  scan: ScanReportView;
}

/**
 * The console-OSC-input reachability verdict carried on `status`.
 *
 * Three values, not two: "undetermined" (a remote console whose port cannot be
 * bound from here, or a server that did not probe) must stay distinguishable
 * from "silent". Collapsing them would show a confident wrong cause again —
 * the exact defect the verdict exists to remove.
 */
export type ConsoleInput = "listening" | "silent" | "undetermined";

export type PreviewRiskLevel = "info" | "caution" | "danger";
export type PreviewWarningSeverity = "caution" | "danger";
export type PreviewAction =
  | "store_overwrite"
  | "store"
  | "delete"
  | "blackout"
  | "off"
  | "run"
  | "modify"
  | "unknown";
export type PreviewTargetKind =
  | "group"
  | "preset"
  | "cue"
  | "sequence"
  | "executor"
  | "macro"
  | "plugin"
  | "fixture"
  | "showfile"
  | "unknown";

export interface ExecutionPreviewCommand {
  command: string;
  action: PreviewAction;
  target_kind: PreviewTargetKind;
  target: string | null;
  label: string;
}

export interface ExecutionPreviewWarning {
  severity: PreviewWarningSeverity;
  label: string;
  detail: string;
  command: string;
}

export interface ExecutionPreview {
  preview_id: string;
  summary: string;
  risk_level: PreviewRiskLevel;
  commands: ExecutionPreviewCommand[];
  warnings: ExecutionPreviewWarning[];
}

// -- show-control panel (SPEC-COPILOT-SHOWUI-001 M1) --------------------------
//
// An ADDITIVE v1 extension, same call as the M7 `review_decision` one: the
// protocol version stays 1 and every type below is registered on BOTH
// allowlists — here and in `server/web/messages.py`. A type present on only one
// side goes silently missing on this side and loudly wrong on the server
// (REQ-SHOWUI-014); the two unknown-type contracts are deliberately asymmetric
// and neither may be "harmonised" into the other.

/**
 * The tile's type badge — LOOK / FX / SEQ (design.md §4), plus the additive
 * MACRO badge (SPEC-COPILOT-DASHUI-001 REQ-DASHUI-012): both closed sets widen
 * together so a macro tile is never stamped with the "sequence" badge.
 */
export type PanelItemKind = "look" | "effect" | "sequence" | "macro";

/**
 * The console object classes a tile may address.
 *
 * `fixture` is absent on purpose (REQ-SHOWUI-003): a fixture's `no` is its
 * patch slot, not its fixture id, so it is not an address the console fires.
 * `macro` is the SPEC-COPILOT-DASHUI-001 additive entry (REQ-DASHUI-012) —
 * the rulebook-verified run form is `Macro <no>`, one-shot (no Off form).
 */
export type PanelTargetKind = "executor" | "sequence" | "macro";

/** Chat-pinned (REQ-SHOWUI-004) vs rig-enumerated (REQ-SHOWUI-001). */
export type PanelItemSource = "pin" | "auto";

/**
 * Why a catalog section is (in)complete. The two failure causes stay distinct
 * (REQ-SHOWUI-002) — "the path does not exist in this showfile" and "the
 * console did not answer" ask the operator for different actions.
 */
export type PanelSectionStatus = "ok" | "path_not_resolved" | "console_unreachable";

export interface PanelItem {
  /** `"<target_kind>:<no>"` — derived from the REAL object number. */
  id: string;
  kind: PanelItemKind;
  target_kind: PanelTargetKind;
  /** The console's real object number (pool numbers are non-contiguous). */
  target: number;
  name: string;
  /** Appearance colour chip, or null when the object has none. */
  appearance: string | null;
  source: PanelItemSource;
}

export interface PanelSection {
  name: string;
  status: PanelSectionStatus;
  /** The responder said its own listing was cut short. */
  truncated?: boolean;
  /** The query budget ran out before every container was opened. */
  drilldown_capped?: boolean;
  /** At least one container could not be opened — NOT the same as empty. */
  contents_unavailable?: boolean;
}

// -- console-info dashboard (SPEC-COPILOT-DASHUI-001 M1) ----------------------
//
// INFO-ONLY shape (REQ-DASHUI-007): a dashboard entry is a read-only console
// fact. The address triple a panel tile carries — a derived id, an object
// class discriminator (`target_kind`), a fireable number — simply does not
// exist on this shape, so nothing built from it can become a command. The
// non-fireability is structural (a missing field), not a runtime check.

/** One read-only pool entry: the console's REAL object number + name. */
export interface DashItem {
  /** The console's real object number (pools are non-contiguous). */
  no: number;
  name: string;
  /** Appearance colour chip; null or absent when the object has none. */
  appearance?: string | null;
  /** Optional extra facts (e.g. the fixture-count summary, REQ-DASHUI-009). */
  meta?: Record<string, unknown>;
}

/**
 * One dashboard section: its own completeness plus its info-only entries.
 *
 * Status and flags reuse the panel-section vocabulary verbatim
 * (REQ-DASHUI-004) — the two failure causes stay distinct, the three
 * completeness flags carry through. Unlike `panel_catalog`'s flat tile list,
 * `items` ride INSIDE their section: a self-contained pool view.
 */
export interface DashSection {
  name: string;
  status: PanelSectionStatus;
  truncated?: boolean;
  drilldown_capped?: boolean;
  contents_unavailable?: boolean;
  items: DashItem[];
}

// -- live cue-progress monitor (T-C, wave 2 — ad-hoc contract, no SPEC) -------
//
// Two independent read paths (server/web/cue_monitor.py): a per-executor cue-
// progress row, and a console-independent recent-execution history read off
// the audit log. Deliberately NO progress percentage and NO timer field — no
// channel confirms a fade's remaining time (contract explicitly excludes
// them); the UI must explain an "unavailable" current cue, never estimate one.

export type CueExecutorStatus = "ok" | "unassigned" | "unavailable";

/** One cue in a sequence's cue list: its pool slot + name, plus the
 * responder's additive real cue number (`cue_no`) when it could read one. */
export interface CueItem {
  no: number;
  name: string;
  cue_no?: number;
}

/** The current-cue read outcome — independently Optional (see module note). */
export interface CueCurrentCue {
  status: "ok" | "unavailable";
  value?: string;
  property?: string;
  tried?: string[];
}

/**
 * The app's own last confirmed/failed action on one executor (T-H). This is
 * NOT a claim about whether the console is currently playing that command —
 * only that the app sent it and the console did (or did not) ok it. `null`
 * when the app has never sent this executor anything (a console operated by
 * hand is invisible to the app either way).
 */
export interface CueLastAppAction {
  command: string;
  ts: string;
  ok: boolean;
}

/** One executor's live cue-progress row. */
export interface CueExecutorEntry {
  executor_no: number;
  status: CueExecutorStatus;
  sequence_no?: number | null;
  sequence_name?: string | null;
  cues: CueItem[];
  current_cue: CueCurrentCue | null;
  last_app_action?: CueLastAppAction | null;
  /** 1-based slot in the operator's PLANNED show order (진행 순서 보드) —
   *  the server orders rows by the director timeline's sequence and stamps
   *  the planned ones; absent/null for rows the plan does not name. */
  planned_position?: number | null;
}

/** One recent-execution row (audit-log derived, oldest-first). Attribution
 * (`target_kind`/`target_no`) is best-effort — both `null` when the command
 * did not parse as a known playback form; the row is still kept. */
export interface CueHistoryEntry {
  ts: string;
  command: string;
  ok: boolean;
  target_kind?: PanelTargetKind | null;
  target_no?: number | null;
}

// -- director song timeline ---------------------------------------------------
//
// This is a review artifact, never a command surface. It mirrors the
// server-owned UnifiedSongLightingPlan after every material lifecycle change:
// draft/requery → explicit approval → readback verdict.
export type SongTimelineLifecycle =
  | "draft"
  | "requires_requery"
  | "pending_approval"
  | "approved"
  | "verified"
  | "readback_failed";

// Per-section design/console state. `draft`/`requires_requery`/`approved`
// are PLAN-only (nothing stored on the console yet); `stored`/`verified`
// mean the cue exists on the console. Optional on the wire so older server
// payloads still parse — consumers derive a fallback from `lifecycle`.
export type SongTimelinePlanStatus =
  | "draft"
  | "requires_requery"
  | "approved"
  | "stored"
  | "verified";

export interface SongTimelineDecision {
  step: string;
  axis: string;
  value: unknown;
  confirmed: boolean;
  source: string;
}

export interface SongTimelineSection {
  index: number;
  label: string;
  start_ms: number;
  cue_number: number;
  d_level: number;
  palette: string[];
  position: string;
  texture: string;
  fx: string[];
  accents: string[];
  mib: boolean;
  trig_time_seconds: number | null;
  plan_status?: SongTimelinePlanStatus;
}

export interface SongTimelineView {
  song_title: string;
  sequence_name: string | null;
  sequence_number: number;
  timing_mode: "manual_go" | "trig_time" | "timecode";
  timecode_number: number | null;
  lifecycle: SongTimelineLifecycle;
  approval: string;
  director_decisions: SongTimelineDecision[];
  sections: SongTimelineSection[];
  lint: { rule_id: string; cue_number: number; description: string }[];
  unresolved: { axis: string; section_index: number | null; reason: string }[];
  disabled: { axis: string; section_index: number | null; reason: string }[];
  readback: { verified: boolean | null; message: string | null };
  /** True only when the console actually holds cues for this plan
   * (lifecycle readback_failed/verified). Optional for older payloads. */
  console_stored?: boolean;
  warnings?: string[];
  /** 결함 6: role → console group-number mapping recorded by the director
   * (group membership is unreadable, so this never claims member fixtures). */
  layer_mapping?: { role: string; group_no: number; group_name: string }[];
  /** Basic-position preset base the plan was built on (edit support). */
  preset_start?: number | null;
}

export type DirectorTimelineView = SongTimelineView;

export interface SongTimelineEvent {
  v: 1;
  type: "song_timeline";
  timeline: SongTimelineView;
}

export type ServerEvent =
  | {
      v: 1;
      type: "chat_response";
      status: string;
      summary: string;
      text: string;
      commands: CommandView[];
    }
  | {
      v: 1;
      type: "approval_request";
      request_id: string;
      items: ApprovalItem[];
      actions: string[];
    }
  | ({
      v: 1;
      type: "execution_preview";
    } & ExecutionPreview)
  | { v: 1; type: "approval_resolved"; request_id: string; approved: boolean }
  | ({
      v: 1;
      type: "review_request";
      actions: string[];
    } & ReviewRequestView)
  | { v: 1; type: "review_resolved"; request_id: string; approved: boolean }
  // [round24] 모델이 되묻는 질문 카드. 추측 대신 물으라는 통로 — 답이 없으면
  // 모델은 "아직 답하지 않았다"를 사실 그대로 받는다(거부가 아니다).
  | {
      v: 1;
      type: "question_request";
      request_id: string;
      prompt: string;
      why: string;
      steps: string[];
      // 사용자가 콘솔 명령줄에 복사해 실행할 명령들 — 서버가 대신 실행하면
      // 안 되는 인계 명령(AddFixtures 패치 등). 구버전 서버에는 없다(additive).
      commands?: string[];
      options: { label: string; description: string }[];
    }
  | { v: 1; type: "question_resolved"; request_id: string; answer: string }
  | {
      v: 1;
      type: "status";
      health: string;
      live_lock: boolean;
      executions_blocked: boolean;
      // Additive (protocol stays v1) — the console-OSC-input bind verdict.
      // Absent from a server that does not probe; treated as "undetermined".
      console_input?: ConsoleInput;
      // Additive — the reply-port MISMATCH pair, present together or not at all:
      // a console reply was observed on `reply_port` while the app listens on
      // `receive_port`. Reported, never applied (REQ-DEPLOY-026).
      reply_port?: number | null;
      receive_port?: number | null;
    }
  | { v: 1; type: "proposal"; commands: string[]; reasons: string[] }
  | { v: 1; type: "error"; message: string; kind: string }
  | { v: 1; type: "busy"; message: string }
  | { v: 1; type: "notice"; message: string }
  // 진행 스트리밍 (additive — 이 이벤트를 모르는 구버전 서버는 그냥 보내지
  // 않고, 그 경우 UI는 종전처럼 turn 종료 프레임만 받는다). 소멸성 상태:
  // 대화록에 쌓지 않고 마지막 한 줄만 들고 있다가 턴 종료에서 지운다.
  | { v: 1; type: "progress"; phase: string; detail: string; seq: number }
  | { v: 1; type: "panel_catalog"; items: PanelItem[]; sections: PanelSection[] }
  | {
      v: 1;
      type: "panel_item_state";
      id: string;
      target_kind: PanelTargetKind;
      target: number;
      running: boolean;
      /** Current cue of a running sequence — a string ("1.5" is a cue). */
      cue: string | null;
    }
  | {
      v: 1;
      type: "panel_busy";
      id: string;
      target_kind: PanelTargetKind;
      target: number;
      message: string;
    }
  | { v: 1; type: "dash_catalog"; sections: DashSection[]; cached?: boolean }
  | {
      v: 1;
      type: "cue_monitor";
      executors: CueExecutorEntry[];
      history: CueHistoryEntry[];
      cached?: boolean;
    }
  | SongTimelineEvent;

const SERVER_EVENT_TYPES = new Set([
  "chat_response",
  "approval_request",
  "execution_preview",
  "approval_resolved",
  "review_request",
  "review_resolved",
  "question_request",
  "question_resolved",
  "status",
  "proposal",
  "error",
  "busy",
  "notice",
  // 진행 스트리밍 — server/web/messages.py `progress_event`와 짝.
  "progress",
  // Panel (REQ-SHOWUI-014) — mirrored by PANEL_* in server/web/messages.py.
  "panel_catalog",
  "panel_item_state",
  "panel_busy",
  // Dashboard (REQ-DASHUI-006) — mirrored by DASH_* in server/web/messages.py.
  "dash_catalog",
  // Cue monitor (T-C, wave 2) — mirrored by CUE_* in server/web/messages.py.
  "cue_monitor",
  "song_timeline",
]);

/** Parse one server frame; unknown/foreign frames return null (ignored). */
export function parseServerEvent(raw: string): ServerEvent | null {
  let data: unknown;
  try {
    data = JSON.parse(raw);
  } catch {
    return null;
  }
  if (typeof data !== "object" || data === null) return null;
  const event = data as { v?: unknown; type?: unknown };
  if (event.v !== PROTOCOL_VERSION) return null;
  if (typeof event.type !== "string" || !SERVER_EVENT_TYPES.has(event.type)) return null;
  return data as ServerEvent;
}

// -- client -> server builders -------------------------------------------------

export function buildChat(text: string): string {
  return JSON.stringify({ v: PROTOCOL_VERSION, type: "chat", text });
}

export function buildVectorworksExportUpload(fileName: string, contentBase64: string): string {
  return JSON.stringify({
    v: PROTOCOL_VERSION,
    type: "vectorworks_export_upload",
    file_name: fileName,
    content_base64: contentBase64,
  });
}

/**
 * SPEC-COPILOT-IMGLAYOUT-001 M1 — attach a design/reference image (contract
 * §1). `mimeType` must be one of the server's allowed MIME types
 * (`image/png` / `image/jpeg` / `image/webp`) — this builder does not
 * validate; the server rejects an unlisted type with `error(kind:
 * "layout_image_rejected")`.
 */
export function buildLayoutImageUpload(
  fileName: string,
  mimeType: string,
  contentBase64: string,
): string {
  return JSON.stringify({
    v: PROTOCOL_VERSION,
    type: "layout_image_upload",
    file_name: fileName,
    mime_type: mimeType,
    content_base64: contentBase64,
  });
}

export function buildApprovalDecision(requestId: string, approved: boolean): string {
  return JSON.stringify({
    v: PROTOCOL_VERSION,
    type: "approval_decision",
    request_id: requestId,
    approved,
  });
}

export function buildReviewDecision(requestId: string, approved: boolean): string {
  return JSON.stringify({
    v: PROTOCOL_VERSION,
    type: "review_decision",
    request_id: requestId,
    approved,
  });
}

export function buildQuestionAnswer(requestId: string, answer: string): string {
  return JSON.stringify({
    v: PROTOCOL_VERSION,
    type: "question_answer",
    request_id: requestId,
    answer,
  });
}

export function buildLock(active: boolean): string {
  return JSON.stringify({ v: PROTOCOL_VERSION, type: "lock", active });
}

export function buildStatusRequest(): string {
  return JSON.stringify({ v: PROTOCOL_VERSION, type: "status_request" });
}

/**
 * The stable tile key: `"<target_kind>:<no>"`.
 *
 * Keyed on the console's REAL object number, never a list position
 * (REQ-SHOWUI-003) — pool numbers are non-contiguous, so "the 3rd tile" and
 * "object 3" are different objects. The `kind:no` shape also keeps Executor 41
 * and Sequence 41 apart, which a bare number cannot.
 */
export function panelItemId(targetKind: PanelTargetKind, target: number): string {
  return `${targetKind}:${target}`;
}

export function buildPanelExecute(targetKind: PanelTargetKind, target: number): string {
  return JSON.stringify({
    v: PROTOCOL_VERSION,
    type: "panel_execute",
    target_kind: targetKind,
    target,
  });
}

export function buildPanelStop(targetKind: PanelTargetKind, target: number): string {
  return JSON.stringify({
    v: PROTOCOL_VERSION,
    type: "panel_stop",
    target_kind: targetKind,
    target,
  });
}

/** T-H5 — step to the PREVIOUS cue (console verb `Go-`). Same shape as
 * `buildPanelExecute`/`buildPanelStop`. */
export function buildPanelBack(targetKind: PanelTargetKind, target: number): string {
  return JSON.stringify({
    v: PROTOCOL_VERSION,
    type: "panel_back",
    target_kind: targetKind,
    target,
  });
}

/**
 * T-H5 — jump to a specific cue (console form `Goto Cue <c> Sequence <s>`).
 * `target`/`targetKind` still name the EXECUTOR the press originated on (the
 * server resolves executor -> sequence and validates cue membership before
 * building any command — see server/web/panel.py's own module notes); this
 * builder does not, and must not, attempt that resolution itself.
 */
export function buildPanelGoto(targetKind: PanelTargetKind, target: number, cue: number): string {
  return JSON.stringify({
    v: PROTOCOL_VERSION,
    type: "panel_goto",
    target_kind: targetKind,
    target,
    cue,
  });
}

/**
 * Pin whatever the chat just created. Payload-free by design: the seed is the
 * server's own `_last_created` cross-turn memory (REQ-SHOWUI-004), so there is
 * no client-supplied target to get wrong.
 */
export function buildPanelPin(): string {
  return JSON.stringify({ v: PROTOCOL_VERSION, type: "panel_pin" });
}

export function buildPanelUnpin(targetKind: PanelTargetKind, target: number): string {
  return JSON.stringify({
    v: PROTOCOL_VERSION,
    type: "panel_unpin",
    target_kind: targetKind,
    target,
  });
}

export function buildPanelCatalogRequest(): string {
  return JSON.stringify({ v: PROTOCOL_VERSION, type: "panel_catalog_request" });
}

/**
 * Ask for a `dash_catalog` event (REQ-DASHUI-006). Payload-free, and sent only
 * on connect and on manual refresh — never on a timer (REQ-DASHUI-021).
 */
export function buildDashCatalogRequest(): string {
  return JSON.stringify({ v: PROTOCOL_VERSION, type: "dash_catalog_request" });
}

/**
 * Ask for a `cue_monitor` event (T-C, wave 2). Payload-free — the client
 * polls for a fresh snapshot; there is nothing client-supplied to validate.
 */
export function buildCueMonitorRequest(): string {
  return JSON.stringify({ v: PROTOCOL_VERSION, type: "cue_monitor_request" });
}

// -- UI state reducer ------------------------------------------------------------

export type ChatEntry =
  | { kind: "user"; text: string }
  | {
      kind: "assistant";
      status: string;
      summary: string;
      text: string;
      commands: CommandView[];
    }
  | { kind: "proposal"; commands: string[]; reasons: string[] }
  | { kind: "preview"; preview: ExecutionPreview }
  | { kind: "error"; message: string; errorKind: string }
  | { kind: "notice"; message: string }
  | { kind: "busy"; message: string };

export interface StatusState {
  health: string;
  live_lock: boolean;
  executions_blocked: boolean;
  console_input?: ConsoleInput;
  reply_port?: number | null;
  receive_port?: number | null;
}

export interface PendingApproval {
  request_id: string;
  items: ApprovalItem[];
}

/** One tile's playback state. Volatile — see `clearOnDisconnect`. */
export interface PanelItemState {
  running: boolean;
  cue: string | null;
}

export interface PanelState {
  /**
   * The tile list in WIRE order, which IS grid order (REQ-SHOWUI-017): nothing
   * sorts it and new items append, so a tile never moves under the operator's
   * finger mid-show.
   */
  items: PanelItem[];
  sections: PanelSection[];
  /** Per-tile playback state, keyed by `panelItemId`. */
  running: Record<string, PanelItemState>;
  /**
   * The most recent busy refusal (REQ-SHOWUI-011). Held as state rather than
   * shown as a toast — design.md §7 forbids toasts; the tile carries its own
   * status persistently.
   */
  busy: { id: string; message: string } | null;
}

/**
 * The console-info dashboard's slice of the UI state (REQ-DASHUI-006/015/018).
 *
 * `sections` is server state (a `dash_catalog` REPLACES it, never merges) and
 * survives a disconnect so the dashboard still renders, inert, while offline.
 * `lastSyncAt` + `stale` are the freshness claim — the volatile half: once the
 * socket closes the app can no longer say the catalog matches the console, so
 * `clearOnDisconnect` withdraws the claim by marking it stale rather than
 * rendering yesterday's rig as current.
 */
export interface DashState {
  /** Section list in wire order (REQ-DASHUI-003 — nothing sorts it). */
  sections: DashSection[];
  /** Wall-clock ms of the last `dash_catalog` receipt, or null before one. */
  lastSyncAt: number | null;
  /** Set on disconnect: the catalog on screen may no longer match the console. */
  stale: boolean;
}

/**
 * The live cue-progress monitor's slice of the UI state (T-C, wave 2).
 *
 * Same freshness-claim shape as `DashState`: `executors`/`history` are server
 * state (a `cue_monitor` REPLACES both, never merges) and survive a
 * disconnect so the panel still renders, inert, while offline; `stale` marks
 * that the last snapshot may no longer match the console.
 */
export interface CueMonitorState {
  executors: CueExecutorEntry[];
  history: CueHistoryEntry[];
  lastSyncAt: number | null;
  stale: boolean;
}

/** Last server-authored director plan. It is review-only and becomes stale
 * after disconnect because a new server session has no plan to execute. */
export interface SongTimelineState {
  timeline: SongTimelineView | null;
  stale: boolean;
}

export interface PendingQuestion {
  request_id: string;
  prompt: string;
  why: string;
  steps: string[];
  commands: string[];
  options: { label: string; description: string }[];
}

/**
 * 지금 돌고 있는 턴의 진행 한 줄 (`progress` 이벤트).
 *
 * 소멸성 상태다 — 대화록(`entries`)에 쌓지 않는다. 한 턴이 모델 호출 24회 +
 * 도구당 수백 콘솔 왕복을 도는 동안 수십 줄이 흘러나오는데, 그것이 전부
 * 기록으로 남으면 정작 읽어야 할 답이 묻힌다. 마지막 한 줄만 들고 있다가
 * 턴 종료 프레임(`chat_response` / `error`)에서 `null`로 되돌린다.
 *
 * `seq`를 들고 있는 이유: 턴 안에서 단조증가하므로, 늦게 도착한 프레임이
 * 앞선 상태를 되돌리는 일을 여기서 막는다(턴이 바뀌면 1로 되돌아가지만,
 * 그때는 종료 프레임이 이미 `null`로 지워 놓은 뒤다).
 */
export interface ProgressState {
  phase: string;
  detail: string;
  seq: number;
}

export interface UiState {
  entries: ChatEntry[];
  status: StatusState | null;
  pendingApprovals: PendingApproval[];
  pendingReviews: ReviewRequestView[];
  pendingQuestions: PendingQuestion[];
  panel: PanelState;
  dash: DashState;
  cueMonitor: CueMonitorState;
  songTimeline: SongTimelineState;
  /** 진행 중인 턴의 마지막 진행 한 줄. 턴이 끝나면 `null`이 된다. */
  progress: ProgressState | null;
}

export const initialState: UiState = {
  entries: [],
  status: null,
  songTimeline: { timeline: null, stale: false },
  pendingApprovals: [],
  pendingReviews: [],
  pendingQuestions: [],
  panel: { items: [], sections: [], running: {}, busy: null },
  dash: { sections: [], lastSyncAt: null, stale: false },
  progress: null,
  cueMonitor: { executors: [], history: [], lastSyncAt: null, stale: false },
};

/**
 * Fold one server event into the UI state.
 *
 * `nowMs` exists so the `dash_catalog` freshness stamp stays a pure input —
 * tests pass an explicit clock; production callers take the default.
 */
export function reduceServerEvent(
  state: UiState,
  event: ServerEvent,
  nowMs: number = Date.now(),
): UiState {
  switch (event.type) {
    case "chat_response":
      return {
        ...state,
        // 턴 종료 = 진행 표시 소멸. 답이 도착한 뒤에도 "…중"이 남아 있으면
        // 그것은 정보가 아니라 거짓말이다.
        progress: null,
        entries: [
          ...state.entries,
          {
            kind: "assistant",
            status: event.status,
            summary: event.summary,
            text: event.text,
            commands: event.commands,
          },
        ],
      };
    case "approval_request":
      return {
        ...state,
        pendingApprovals: [
          ...state.pendingApprovals,
          { request_id: event.request_id, items: event.items },
        ],
      };
    case "execution_preview":
      return {
        ...state,
        entries: [...state.entries, { kind: "preview", preview: event }],
      };
    case "approval_resolved":
      return {
        ...state,
        pendingApprovals: state.pendingApprovals.filter(
          (pending) => pending.request_id !== event.request_id,
        ),
      };
    case "question_request":
      return {
        ...state,
        pendingQuestions: [
          ...state.pendingQuestions,
          {
            request_id: event.request_id,
            prompt: event.prompt,
            why: event.why,
            steps: event.steps ?? [],
            commands: event.commands ?? [],
            options: event.options ?? [],
          },
        ],
      };
    case "question_resolved":
      return {
        ...state,
        pendingQuestions: state.pendingQuestions.filter(
          (pending) => pending.request_id !== event.request_id,
        ),
      };
    case "review_request":
      return {
        ...state,
        pendingReviews: [
          ...state.pendingReviews,
          {
            request_id: event.request_id,
            plugin_name: event.plugin_name,
            source_preview: event.source_preview,
            source_length: event.source_length,
            source_truncated: event.source_truncated,
            compile_ok: event.compile_ok,
            scan: event.scan,
          },
        ],
      };
    case "review_resolved":
      return {
        ...state,
        pendingReviews: state.pendingReviews.filter(
          (pending) => pending.request_id !== event.request_id,
        ),
      };
    case "status":
      return {
        ...state,
        status: {
          health: event.health,
          live_lock: event.live_lock,
          executions_blocked: event.executions_blocked,
          console_input: event.console_input,
          reply_port: event.reply_port,
          receive_port: event.receive_port,
        },
      };
    case "proposal":
      return {
        ...state,
        entries: [
          ...state.entries,
          { kind: "proposal", commands: event.commands, reasons: event.reasons },
        ],
      };
    case "error":
      return {
        ...state,
        // `chat_response`와 나란한 또 하나의 턴 종결 프레임 — 세션의
        // run_instruction은 예외를 error 이벤트로 바꿔 내보내고 그대로 끝난다.
        progress: null,
        entries: [...state.entries, { kind: "error", message: event.message, errorKind: event.kind }],
      };
    case "progress":
      // 마지막 한 줄만 들고 있는다(대화록에 쌓지 않는다). `seq`가 뒤로 가는
      // 프레임은 버린다 — 늦게 도착한 옛 줄이 최신 상태를 되돌리면 안 된다.
      if (state.progress !== null && event.seq <= state.progress.seq) return state;
      return {
        ...state,
        progress: { phase: event.phase, detail: event.detail, seq: event.seq },
      };
    case "busy":
      return { ...state, entries: [...state.entries, { kind: "busy", message: event.message }] };
    case "notice":
      return { ...state, entries: [...state.entries, { kind: "notice", message: event.message }] };
    case "panel_catalog":
      // A refresh REPLACES the tile list; it does not merge. The server owns
      // the catalog (single source of truth, REQ-SHOWUI-005) and merging here
      // would keep tiles alive that the rig no longer has.
      return {
        ...state,
        panel: { ...state.panel, items: event.items, sections: event.sections },
      };
    case "panel_item_state":
      return {
        ...state,
        panel: {
          ...state.panel,
          running: {
            ...state.panel.running,
            [event.id]: { running: event.running, cue: event.cue },
          },
        },
      };
    case "panel_busy":
      return {
        ...state,
        panel: { ...state.panel, busy: { id: event.id, message: event.message } },
      };
    case "dash_catalog":
      // A refresh REPLACES the section list (REQ-DASHUI-006) — merging would
      // keep pools the showfile no longer has. A FRESH catalog renews the
      // freshness claim; a CACHED one (the server's stale-while-revalidate
      // first paint) renders immediately but keeps the stale badge and the
      // previous sync stamp — the console never answered for it.
      return {
        ...state,
        dash: {
          sections: event.sections,
          lastSyncAt: event.cached === true ? state.dash.lastSyncAt : nowMs,
          stale: event.cached === true,
        },
      };
    case "cue_monitor":
      // A refresh REPLACES both lists — same replace semantics as
      // `dash_catalog`; merging would keep an executor's stale cue list
      // alive after the showfile changed underneath it.
      return {
        ...state,
        cueMonitor: {
          executors: event.executors,
          history: event.history,
          lastSyncAt: event.cached === true ? state.cueMonitor.lastSyncAt : nowMs,
          stale: event.cached === true,
        },
      };
    case "song_timeline":
      return {
        ...state,
        songTimeline: { timeline: event.timeline, stale: false },
      };
  }
}

/** Append the user's own chat line (echoed locally on send). */
export function addUserMessage(state: UiState, text: string): UiState {
  return { ...state, entries: [...state.entries, { kind: "user", text }] };
}

// -- chat transcript persistence (refresh survival) ----------------------------
//
// The transcript is persisted to localStorage so a page refresh keeps the
// conversation visible. NOTE this restores the VISIBLE transcript only — the
// server builds a fresh session per WebSocket connection, so the model's own
// cross-turn memory starts anew after a refresh.

export const CHAT_STORAGE_KEY = "ma3-copilot.chat-entries.v1";
// Bound the stored transcript so localStorage never grows unbounded; the tail
// is what carries context, so the OLDEST entries are dropped first.
export const CHAT_STORAGE_MAX_ENTRIES = 200;

/** Serialize entries for storage. `busy` lines are transient progress markers
 *  — restoring a stale "처리 중" would claim work that is not running. */
export function serializeEntriesForStorage(entries: ChatEntry[]): string {
  const kept = entries.filter((entry) => entry.kind !== "busy");
  return JSON.stringify(kept.slice(-CHAT_STORAGE_MAX_ENTRIES));
}

function isStoredEntry(item: unknown): item is ChatEntry {
  if (typeof item !== "object" || item === null) return false;
  const entry = item as Record<string, unknown>;
  switch (entry.kind) {
    case "user":
      return typeof entry.text === "string";
    case "assistant":
      return (
        typeof entry.status === "string" &&
        typeof entry.summary === "string" &&
        typeof entry.text === "string" &&
        Array.isArray(entry.commands)
      );
    case "proposal":
      return Array.isArray(entry.commands) && Array.isArray(entry.reasons);
    case "preview": {
      const preview = entry.preview as Record<string, unknown> | null | undefined;
      return (
        typeof preview === "object" &&
        preview !== null &&
        Array.isArray(preview.commands) &&
        Array.isArray(preview.warnings)
      );
    }
    case "error":
      return typeof entry.message === "string" && typeof entry.errorKind === "string";
    case "notice":
      return typeof entry.message === "string";
    default:
      return false;
  }
}

/** Parse a stored transcript; malformed input or items degrade to fewer/zero
 *  entries rather than crashing the boot render (boundary discipline). */
export function parseStoredEntries(raw: string | null): ChatEntry[] {
  if (!raw) return [];
  let data: unknown;
  try {
    data = JSON.parse(raw);
  } catch {
    return [];
  }
  if (!Array.isArray(data)) return [];
  return data.filter(isStoredEntry);
}

// On (re)connect the restored transcript is reinjected into the fresh server
// session so the MODEL's cross-turn memory also survives a refresh (the
// server keeps history per WebSocket connection). Mirror of the server's
// HISTORY_RESTORE_MAX_MESSAGES — only the newest window carries context.
export const HISTORY_RESTORE_MAX_MESSAGES = 16;

/** Build the history_restore frame from a transcript, or null when there is
 *  no user/assistant exchange worth reinjecting. */
export function buildHistoryRestore(entries: ChatEntry[]): string | null {
  const messages = entries
    .flatMap((entry) => {
      if (entry.kind === "user") return [{ role: "user", text: entry.text }];
      if (entry.kind === "assistant") {
        const text = entry.text.trim() || entry.summary.trim();
        return text ? [{ role: "assistant", text }] : [];
      }
      return [];
    })
    .filter((message) => message.text.trim().length > 0)
    .slice(-HISTORY_RESTORE_MAX_MESSAGES);
  if (messages.length === 0) return null;
  return JSON.stringify({ v: PROTOCOL_VERSION, type: "history_restore", messages });
}

/**
 * Drop every pending approval/review card. The server fail-safe-denies all
 * of a session's own outstanding requests on that session's disconnect —
 * without this, a stale card sits in the UI forever after a reconnect,
 * misleading the operator into thinking a decision is still awaited when
 * the server already resolved it.
 */
export function clearPendingRequests(state: UiState): UiState {
  if (state.pendingApprovals.length === 0 && state.pendingReviews.length === 0) return state;
  return { ...state, pendingApprovals: [], pendingReviews: [] };
}

/**
 * The single disconnect action: drop every pending card, erase the panel's
 * running state, AND withdraw the dashboard's freshness claim.
 *
 * Running state is volatile derived state — the console keeps playing, but the
 * app can no longer observe it, and "probably still running" is exactly the
 * render that gets an operator to press Off on a tile that already stopped, or
 * to leave one running that did not (REQ-SHOWUI-015/016). Fail closed: show
 * nothing rather than a guess, and rebuild from a catalog + status resync on
 * reconnect.
 *
 * The tile LIST survives — it is server state, not an observation of the
 * console — so the panel still renders (inert) while offline. The dashboard's
 * sections survive on the same terms, but their freshness claim does not: a
 * synced catalog is marked STALE (REQ-DASHUI-015), because an offline app
 * cannot claim the pools on screen still match the console. The mark clears
 * when the reconnect resync delivers a fresh `dash_catalog`.
 *
 * One function rather than two so a disconnect handler cannot clear half the
 * volatile state and keep the other half on screen.
 */
export function clearOnDisconnect(state: UiState): UiState {
  let next = clearPendingRequests(state);
  const { running, busy } = next.panel;
  if (Object.keys(running).length > 0 || busy !== null) {
    next = { ...next, panel: { ...next.panel, running: {}, busy: null } };
  }
  // Only a catalog that was actually synced carries a freshness claim to
  // withdraw; before the first `dash_catalog` there is nothing to mark.
  if (next.dash.lastSyncAt !== null && !next.dash.stale) {
    next = { ...next, dash: { ...next.dash, stale: true } };
  }
  // Same withdrawal for the cue monitor's own freshness claim.
  if (next.cueMonitor.lastSyncAt !== null && !next.cueMonitor.stale) {
    next = { ...next, cueMonitor: { ...next.cueMonitor, stale: true } };
  }
  if (next.songTimeline.timeline !== null && !next.songTimeline.stale) {
    next = { ...next, songTimeline: { ...next.songTimeline, stale: true } };
  }
  // 진행 표시는 "지금 서버가 이걸 하고 있다"는 주장이다. 소켓이 끊긴 뒤에는
  // 그 주장을 할 수 없다 — 남겨 두면 영원히 도는 "…중" 한 줄이 된다.
  if (next.progress !== null) {
    next = { ...next, progress: null };
  }
  return next;
}

// -- Korean display labels ---------------------------------------------------------

export const HEALTH_LABELS: Record<string, string> = {
  online: "콘솔 온라인",
  console_offline: "콘솔 오프라인 — 신규 실행 차단",
  responder_degraded: "응답기 저하 — 결과 확인 불가",
};

export function healthLabel(health: string): string {
  return HEALTH_LABELS[health] ?? health;
}

// Cause + action guidance for each degraded health state (REQ-DEPLOY-018/019).
// Human-friendly Korean only — NEVER a stack trace or raw SDK original. The
// healthy state (and any unknown state) yields null so no guidance line shows.
export const HEALTH_GUIDANCE: Record<string, string> = {
  console_offline: "onPC가 실행 중인지, OSC 입력이 켜져 있는지 확인해 주세요.",
  responder_degraded:
    "CopilotResponder를 onPC에서 로드하고, onPC OSC 출력을 앱의 피드백 수신 포트로 설정해 주세요.",
};

// console_offline is reached by TWO different situations: onPC is genuinely
// down, and onPC is up with its OSC input live but the responder plugin — the
// only thing that ever sends — has stopped. The backend's bind probe tells them
// apart; without this refinement the second one is sent to inspect the two
// subsystems that are already healthy while the real cause goes unnamed.
// Claim discipline: the port sentence states what was actually observed (the
// port is held), and the cause stays hedged — a held port proves something is
// listening, not that it is onPC.
export const CONSOLE_OFFLINE_RESPONDER_GUIDANCE =
  "콘솔 OSC 입력 포트는 열려 있습니다 — CopilotResponder 플러그인이 실행 중이 아닐 수 있습니다. " +
  "onPC의 Plugins 풀에서 CopilotResponder를 실행해 주세요.";

// The third console_offline cause. A grandMA3 OSC entry has ONE port used for
// BOTH directions, so the port the console replies THROUGH lives in the
// console's OSC table while the port the app listens ON lives in the app's
// settings — two numbers, two places, kept in sync by hand. When they drift the
// link goes quiet with every subsystem healthy, and the responder message above
// would be wrong in a NEW way: the plugin is running, it is just answering
// somewhere nobody is listening.
//
// Both numbers are named and both fixes are offered, because the app must not
// change its own effective port (REQ-DEPLOY-026) — the operator decides whether
// the console moves or the app does.
export function consoleOfflineReplyPortGuidance(replyPort: number, receivePort: number): string {
  return (
    `콘솔이 응답을 다른 포트로 보내고 있습니다 — 콘솔은 ${replyPort}번 포트로 회신하는데 ` +
    `앱은 ${receivePort}번 포트에서 수신 대기 중입니다. ` +
    `onPC의 OSC 설정에서 해당 항목 Port를 ${receivePort}(으)로 맞추거나, ` +
    `앱 설정(Settings)의 수신 포트를 ${replyPort}(으)로 바꾼 뒤 다시 시작해 주세요.`
  );
}

/**
 * Cause+action guidance for a health state, refined by the backend's diagnosis.
 *
 * Ordered most-specific first. A reply-port mismatch implies the console's input
 * IS listening, so both refinements apply at once — but only the mismatch names
 * the real cause, and the responder message would misattribute it.
 *
 * Every argument is optional: absent / "undetermined" / "silent" / no observed
 * reply port all keep the message that is correct in that case, so a server that
 * does not diagnose behaves exactly as before.
 */
export function healthGuidance(
  health: string,
  consoleInput?: ConsoleInput,
  replyPort?: number | null,
  receivePort?: number | null,
): string | null {
  if (health === "console_offline") {
    if (
      typeof replyPort === "number" &&
      typeof receivePort === "number" &&
      replyPort !== receivePort
    ) {
      return consoleOfflineReplyPortGuidance(replyPort, receivePort);
    }
    if (consoleInput === "listening") {
      return CONSOLE_OFFLINE_RESPONDER_GUIDANCE;
    }
  }
  return HEALTH_GUIDANCE[health] ?? null;
}
