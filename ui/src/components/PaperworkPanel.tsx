// Paperwork panel (W3 — P0 UI exposure,
// docs/reports/2026-08-06-workflow-coverage-review.html §5).
//
// Surfaces the read-only printable documents (patch sheet / cue sheet /
// preset list / reduced magic sheet) that were previously reachable ONLY via
// an LLM tool call —
// server/orchestrator/tools.py's own build_patch_sheet/build_cue_sheet/
// build_preset_list handlers, now also reachable from server/web/
// paperwork_api.py's GET/POST /api/paperwork(/:kind). Query-only: this panel
// never sends an OSC command and never touches the approval/review path.
//
// Split for the "no DOM/jsdom test harness" bound (see protocol.ts's own
// header): PaperworkPanelView/PaperworkCard are hook-free and are called
// directly as plain functions in tests, the same technique
// RunbookMode.tsx/CueMonitor.tsx use. The named PaperworkPanel owns fetch()
// + React state and renders the view, mirroring SettingsPanel/
// ResponderGuide's split (their pure companions are settings.ts/
// provision.ts; the pure pieces here live in this same file since this
// panel owns nothing else).
//
// The incompleteness badge is the reason this panel exists at all (brief):
// "일부만 본 목록을 전량으로 오해" is the single biggest handover risk, so a
// generated result is never shown as a bare success — every incompleteness
// signal the server reports rides along as a badge.
import { useCallback, useEffect, useState } from "react";

import { apiUrl } from "../launchContext";

export type PaperworkKind = "patch_sheet" | "cue_sheet" | "preset_list" | "magic_sheet";

export interface PaperworkKindMeta {
  kind: PaperworkKind;
  label: string;
}

export const PAPERWORK_KINDS: readonly PaperworkKindMeta[] = [
  { kind: "patch_sheet", label: "패치시트" },
  { kind: "cue_sheet", label: "큐시트" },
  { kind: "preset_list", label: "프리셋 목록" },
  { kind: "magic_sheet", label: "매직시트(축약형)" },
];

// Mirrors the per-kind summary fields server/web/paperwork_api.py's
// _patch_sheet/_cue_sheet/_preset_list/_magic_sheet return — a superset
// across all kinds, each kind populating only the fields that apply to it.
export interface PaperworkSummary {
  path: string;
  fixture_count?: number;
  child_count?: number;
  completeness?: string;
  sequence_count?: number;
  cue_count?: number;
  pool_count?: number;
  preset_count?: number;
  truncated?: boolean;
  drilldown_capped?: boolean;
  group_count?: number;
  preset_pool_count?: number;
  placement_count?: number;
  placements_complete?: boolean;
  group_membership_readable?: boolean;
}

// -- pure logic (response parsing / badge derivation) ------------------------
//
// No fetch(), no React — unit-testable without a DOM, matching protocol.ts.

/**
 * The incompleteness badges for one kind's summary — the SAME vocabulary
 * server/paperwork/render.py's HTML badges use ("incomplete"/"truncated"/
 * "drilldown capped"), translated for the operator-facing panel. Never
 * fabricated: every badge traces to a field the server actually reported.
 */
export function paperworkBadges(kind: PaperworkKind, summary: PaperworkSummary): string[] {
  const badges: string[] = [];
  if (kind === "patch_sheet") {
    const observed = summary.fixture_count;
    const declared = summary.child_count;
    if (typeof observed === "number" && typeof declared === "number" && observed !== declared) {
      badges.push(`관측 ${observed} / 선언 ${declared}`);
    }
    if (summary.completeness !== undefined && summary.completeness !== "complete") {
      badges.push("불완전");
    }
  } else if (kind === "magic_sheet") {
    if (summary.placements_complete === false) {
      badges.push("배치 좌표 일부");
    }
    // ALWAYS shown, never conditional on a field being false: group
    // membership is unreadable on grandMA3 as a matter of platform, so an
    // operator glancing at the card must not have to notice an absent badge
    // to learn it. A conditional badge would go quiet the day the field is
    // dropped from the response.
    badges.push("그룹 멤버십 판독 불가");
  } else {
    if (summary.truncated) badges.push("절단됨");
    if (summary.drilldown_capped) badges.push("드릴다운 상한");
  }
  return badges;
}

export interface PaperworkListResponse {
  kinds: string[];
  lastResults: Record<string, PaperworkSummary | null>;
}

/** Parses GET /api/paperwork's body. `null` on any shape mismatch — the
 * caller degrades to "could not load", never a fabricated empty list. */
export function parsePaperworkListResponse(text: string): PaperworkListResponse | null {
  let data: unknown;
  try {
    data = JSON.parse(text);
  } catch {
    return null;
  }
  if (typeof data !== "object" || data === null) return null;
  const body = data as { kinds?: unknown; last_results?: unknown };
  if (!Array.isArray(body.kinds) || !body.kinds.every((kind) => typeof kind === "string")) {
    return null;
  }
  const lastResults = (
    typeof body.last_results === "object" && body.last_results !== null ? body.last_results : {}
  ) as Record<string, PaperworkSummary | null>;
  return { kinds: body.kinds as string[], lastResults };
}

export type PaperworkGenerateOutcome =
  | { ok: true; kind: PaperworkKind; summary: PaperworkSummary; badges: string[] }
  | { ok: false; message: string };

/** Parses POST /api/paperwork/{kind}'s body — success shape
 * (`{ok: true, path, ...summary}`) or the HTTPException `{detail: {message}}`
 * shape server/web/paperwork_api.py's error paths raise (unknown_kind /
 * capability_unavailable / query_failed / write_failed all share this
 * `{error, message}` detail shape — this parser reads the `message` field
 * common to all four, never branching on the specific `error` code). */
export function parsePaperworkGenerateResponse(
  kind: PaperworkKind,
  status: number,
  text: string,
): PaperworkGenerateOutcome {
  let data: unknown;
  try {
    data = JSON.parse(text);
  } catch {
    return { ok: false, message: "응답을 해석하지 못했습니다." };
  }
  if (typeof data !== "object" || data === null) {
    return { ok: false, message: "응답을 해석하지 못했습니다." };
  }
  const body = data as Record<string, unknown>;
  if (status >= 200 && status < 300 && body.ok === true && typeof body.path === "string") {
    const summary = body as unknown as PaperworkSummary;
    return { ok: true, kind, summary, badges: paperworkBadges(kind, summary) };
  }
  const detail =
    typeof body.detail === "object" && body.detail !== null
      ? (body.detail as Record<string, unknown>)
      : body;
  const message = typeof detail.message === "string" ? detail.message : "생성에 실패했습니다.";
  return { ok: false, message };
}

/** URL for the in-app iframe preview (GET /api/paperwork/:kind/content). */
export function contentUrl(kind: PaperworkKind): string {
  return apiUrl(`/api/paperwork/${kind}/content`);
}

/** URL for the file download (GET /api/paperwork/:kind/download). */
export function downloadUrl(kind: PaperworkKind): string {
  return apiUrl(`/api/paperwork/${kind}/download`);
}

/** Kind-specific stat line shown below the label after generation. */
export function paperworkStatLine(kind: PaperworkKind, summary: PaperworkSummary): string {
  if (kind === "patch_sheet") {
    const n = summary.fixture_count ?? 0;
    return `픽스처 ${n}대`;
  }
  if (kind === "cue_sheet") {
    const seq = summary.sequence_count ?? 0;
    const cue = summary.cue_count ?? 0;
    return `시퀀스 ${seq}개 · 큐 ${cue}개`;
  }
  const pool = summary.pool_count ?? 0;
  const preset = summary.preset_count ?? 0;
  return `풀 ${pool}개 · 프리셋 ${preset}개`;
}

// -- fetch wrappers (thin — call + parse, no React) ---------------------------

export async function fetchPaperworkList(): Promise<PaperworkListResponse | null> {
  const response = await fetch(apiUrl("/api/paperwork"));
  return parsePaperworkListResponse(await response.text());
}

export async function generatePaperworkDocument(
  kind: PaperworkKind,
): Promise<PaperworkGenerateOutcome> {
  const response = await fetch(apiUrl(`/api/paperwork/${kind}`), { method: "POST" });
  return parsePaperworkGenerateResponse(kind, response.status, await response.text());
}

// -- hook-free presentational view (directly testable) ------------------------

export interface PaperworkCardProps {
  meta: PaperworkKindMeta;
  result: PaperworkSummary | null;
  busy: boolean;
  previewing: boolean;
  onGenerate: (kind: PaperworkKind) => void;
  onPreview: (kind: PaperworkKind) => void;
  onDownload: (kind: PaperworkKind) => void;
}

export function PaperworkCard({
  meta,
  result,
  busy,
  previewing,
  onGenerate,
  onPreview,
  onDownload,
}: PaperworkCardProps) {
  const badges = result !== null ? paperworkBadges(meta.kind, result) : [];
  const stat = result !== null ? paperworkStatLine(meta.kind, result) : null;
  return (
    <div className={`paperwork-card${previewing ? " paperwork-card-active" : ""}`} data-kind={meta.kind}>
      <div className="paperwork-card-head">
        <span className="paperwork-card-label">{meta.label}</span>
        {stat !== null && <span className="paperwork-card-stat">{stat}</span>}
        <button
          className="paperwork-card-generate"
          disabled={busy}
          onClick={() => onGenerate(meta.kind)}
        >
          {busy ? "생성 중…" : result !== null ? "새로고침" : "생성"}
        </button>
      </div>
      {result !== null && (
        <div className="paperwork-card-actions">
          {badges.length > 0 && (
            <div className="paperwork-card-badges">
              {badges.map((badge) => (
                <span key={badge} className="paperwork-badge">
                  {badge}
                </span>
              ))}
            </div>
          )}
          <div className="paperwork-card-buttons">
            <button
              className={`paperwork-card-preview${previewing ? " paperwork-card-preview-active" : ""}`}
              onClick={() => onPreview(meta.kind)}
            >
              {previewing ? "닫기" : "미리보기"}
            </button>
            <button className="paperwork-card-download" onClick={() => onDownload(meta.kind)}>
              ↓ 다운로드
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export interface PaperworkPanelViewProps {
  results: Record<string, PaperworkSummary | null>;
  busyKind: PaperworkKind | null;
  notice: string | null;
  previewKind: PaperworkKind | null;
  onGenerate: (kind: PaperworkKind) => void;
  onPreview: (kind: PaperworkKind) => void;
  onDownload: (kind: PaperworkKind) => void;
  onClose: () => void;
}

export function PaperworkPanelView({
  results,
  busyKind,
  notice,
  previewKind,
  onGenerate,
  onPreview,
  onDownload,
  onClose,
}: PaperworkPanelViewProps) {
  return (
    <section className="paperwork-panel" aria-label="페이퍼워크">
      <div className="paperwork-sidebar">
        <header className="paperwork-header">
          <span className="paperwork-title">페이퍼워크</span>
          <button className="paperwork-close" onClick={onClose} aria-label="닫기">
            ✕
          </button>
        </header>
        {notice !== null && <div className="paperwork-notice">{notice}</div>}
        <div className="paperwork-cards">
          {PAPERWORK_KINDS.map((meta) => (
            <PaperworkCard
              key={meta.kind}
              meta={meta}
              result={results[meta.kind] ?? null}
              busy={busyKind === meta.kind}
              previewing={previewKind === meta.kind}
              onGenerate={onGenerate}
              onPreview={onPreview}
              onDownload={onDownload}
            />
          ))}
        </div>
      </div>
      <div className="paperwork-preview-area">
        {previewKind !== null ? (
          <iframe
            className="paperwork-preview-frame"
            src={contentUrl(previewKind)}
            title={PAPERWORK_KINDS.find((m) => m.kind === previewKind)?.label ?? "미리보기"}
          />
        ) : (
          <div className="paperwork-preview-empty">
            <span className="paperwork-preview-empty-icon">📄</span>
            <span>문서를 생성하면 여기에 미리보기가 표시됩니다</span>
          </div>
        )}
      </div>
    </section>
  );
}

// -- stateful component (fetch() + React state; App.tsx mounts this one) -----

export function PaperworkPanel({ onClose }: { onClose: () => void }) {
  const [results, setResults] = useState<Record<string, PaperworkSummary | null>>({});
  const [busyKind, setBusyKind] = useState<PaperworkKind | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [previewKind, setPreviewKind] = useState<PaperworkKind | null>(null);

  const load = useCallback(async () => {
    try {
      const parsed = await fetchPaperworkList();
      if (parsed !== null) setResults(parsed.lastResults);
    } catch {
      setNotice("문서 목록을 불러오지 못했습니다 — 서버 연결을 확인해 주세요.");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const generate = async (kind: PaperworkKind) => {
    setBusyKind(kind);
    setNotice(null);
    try {
      const outcome = await generatePaperworkDocument(kind);
      if (outcome.ok) {
        setResults((current) => ({ ...current, [kind]: outcome.summary }));
        // Auto-open preview after successful generation
        setPreviewKind(kind);
      } else {
        setNotice(outcome.message);
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "";
      setNotice(`문서 생성 중 오류가 발생했습니다.${msg ? ` (${msg})` : ""}`);
    } finally {
      setBusyKind(null);
    }
  };

  const togglePreview = (kind: PaperworkKind) => {
    setPreviewKind((current) => (current === kind ? null : kind));
  };

  const triggerDownload = (kind: PaperworkKind) => {
    const link = document.createElement("a");
    link.href = downloadUrl(kind);
    link.download = `${kind}.html`;
    link.click();
  };

  return (
    <PaperworkPanelView
      results={results}
      busyKind={busyKind}
      notice={notice}
      previewKind={previewKind}
      onGenerate={(kind) => void generate(kind)}
      onPreview={togglePreview}
      onDownload={triggerDownload}
      onClose={onClose}
    />
  );
}
