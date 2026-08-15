import type {
  CueExecutorEntry,
  CueMonitorState,
  SongTimelinePlanStatus,
  SongTimelineSection,
  SongTimelineView,
} from "../protocol";

const LIFECYCLE_LABEL: Record<SongTimelineView["lifecycle"], string> = {
  draft: "초안",
  requires_requery: "재질의 필요",
  pending_approval: "감독 검토 대기",
  approved: "승인됨 · 적용 중",
  verified: "적용 및 검증 완료",
  readback_failed: "Readback 불일치",
};

const TIMING_LABEL: Record<SongTimelineView["timing_mode"], string> = {
  manual_go: "수동 Go",
  trig_time: "큐 타임 (자동 진행)",
  timecode: "타임코드",
};

function formatTimestamp(startMs: number): string {
  const seconds = Math.floor(startMs / 1000);
  const minutes = Math.floor(seconds / 60);
  return `${String(minutes).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
}

function sectionWidth(section: SongTimelineSection, next: SongTimelineSection | undefined): number {
  return Math.max(1, (next?.start_ms ?? section.start_ms + 15_000) - section.start_ms);
}

function Palette({ colors }: { colors: string[] }) {
  return (
    <span className="song-timeline-palette" aria-label={`팔레트: ${colors.join(", ")}`}>
      {colors.map((color) => (
        <span className="song-timeline-color" key={color} title={color}>
          {color}
        </span>
      ))}
    </span>
  );
}

/** Match only the console's explicit sequence number. Name matching would
 * incorrectly imply that an unrelated executor belongs to this song plan. */
export function linkedTimelineExecutor(
  timeline: SongTimelineView,
  cueMonitor: CueMonitorState,
): CueExecutorEntry | null {
  return cueMonitor.executors.find(
    (entry) => entry.status === "ok" && entry.sequence_no === timeline.sequence_number,
  ) ?? null;
}

/** The console reports the current cue as a bare number OR as
 * "<number> — <name>" (live-verified against onPC 2.4). Match on the leading
 * numeric token only — never on the name half. */
export function isTimelineCurrentCue(entry: CueExecutorEntry | null, cueNumber: number): boolean {
  if (entry?.current_cue?.status !== "ok") return false;
  const leading = /^\s*(\d+(?:\.\d+)?)/.exec(entry.current_cue.value ?? "");
  return leading !== null && Number(leading[1]) === cueNumber;
}

/** Older server payloads carry no per-section `plan_status`; derive the
 * closest equivalent from the plan lifecycle so PLAN cues never masquerade
 * as console-stored ones. */
export function sectionPlanStatus(
  section: SongTimelineSection,
  lifecycle: SongTimelineView["lifecycle"],
): SongTimelinePlanStatus {
  if (section.plan_status) return section.plan_status;
  switch (lifecycle) {
    case "verified":
      return "verified";
    case "readback_failed":
      return "stored";
    case "approved":
      return "approved";
    default:
      return "draft";
  }
}

/** Missing `console_stored` (older payloads) derives from lifecycle: only
 * readback_failed/verified mean the console holds cues. */
export function timelineConsoleStored(timeline: SongTimelineView): boolean {
  return (
    timeline.console_stored ??
    (timeline.lifecycle === "readback_failed" || timeline.lifecycle === "verified")
  );
}

const PLAN_STATUS_LINE: Record<SongTimelinePlanStatus, string> = {
  draft: "설계 초안 · 콘솔 미저장",
  requires_requery: "재질의 필요 · 콘솔 미저장",
  approved: "승인됨 · 저장 대기",
  stored: "콘솔 저장 · 검증 실패/대기",
  verified: "콘솔 저장 확인",
};

export function sectionCardTitle(section: SongTimelineSection, status: SongTimelinePlanStatus): string {
  if (status === "verified") return `CUE ${section.cue_number}`;
  if (status === "stored") return `CUE ${section.cue_number} · ${section.label}`;
  return `PLAN CUE ${section.cue_number} · ${section.label}`;
}

/** PLAN cues (draft/requires_requery/approved) exist only in the design;
 * linking them to a live executor would claim console state that is not
 * there. Live rendering stays sequence-number-gated on top of this. */
export function liveExecutorForSection(
  status: SongTimelinePlanStatus,
  executor: CueExecutorEntry | null,
): CueExecutorEntry | null {
  return status === "stored" || status === "verified" ? executor : null;
}

function TimelineSectionCard({
  section,
  next,
  executor,
  lifecycle,
}: {
  section: SongTimelineSection;
  next?: SongTimelineSection;
  executor: CueExecutorEntry | null;
  lifecycle: SongTimelineView["lifecycle"];
}) {
  const width = sectionWidth(section, next);
  const status = sectionPlanStatus(section, lifecycle);
  const onConsole = status === "stored" || status === "verified";
  const liveExecutor = liveExecutorForSection(status, executor);
  const current = isTimelineCurrentCue(liveExecutor, section.cue_number);
  return (
    <article
      className={`song-timeline-section d-level-${section.d_level}${onConsole ? "" : " is-plan-cue"}${current ? " is-current" : ""}`}
      style={{ flexGrow: width, flexBasis: 0 }}
      aria-label={`${formatTimestamp(section.start_ms)} ${section.label}, D${section.d_level}`}
    >
      <div className="song-timeline-section-head">
        <span>{formatTimestamp(section.start_ms)}</span>
      </div>
      <h3>{sectionCardTitle(section, status)}</h3>
      <p className={`song-timeline-plan-state is-${status}`}>{PLAN_STATUS_LINE[status]}</p>
      <div className="song-timeline-energy" aria-label={`에너지 D${section.d_level}`}>
        <span>D{section.d_level}</span>
        <i style={{ width: `${section.d_level * 20}%` }} />
      </div>
      <dl>
        <div><dt>POSITION</dt><dd>{section.position}</dd></div>
        <div><dt>TEXTURE</dt><dd>{section.texture}</dd></div>
        <div><dt>FX</dt><dd>{section.fx.length ? section.fx.join(" · ") : "정적"}</dd></div>
      </dl>
      <Palette colors={section.palette} />
      <footer>
        {section.mib && <span>MIB</span>}
        {section.accents.length > 0 && <span>ACCENT</span>}
        {section.trig_time_seconds !== null && <span>큐 타임 +{section.trig_time_seconds}s</span>}
      </footer>
      {liveExecutor && (
        <p className={`song-timeline-live-cue${current ? " is-current" : ""}`}>
          {current ? `LIVE · EXEC ${liveExecutor.executor_no}` : `PLANNED · EXEC ${liveExecutor.executor_no}`}
        </p>
      )}
    </article>
  );
}

function DecisionRail({ timeline }: { timeline: SongTimelineView }) {
  return (
    <ol className="song-timeline-decisions" aria-label="감독 결정">
      {timeline.director_decisions.map((decision) => (
        <li className={decision.confirmed ? "is-confirmed" : "is-draft"} key={decision.step}>
          <span>{decision.step.replace("_", " ")}</span>
          <strong>{decision.confirmed ? "확정" : "초안"}</strong>
        </li>
      ))}
    </ol>
  );
}

export interface SongTimelineProps {
  timeline: SongTimelineView | null;
  cueMonitor: CueMonitorState;
  stale?: boolean;
  isExample?: boolean;
}

export function SongTimeline({
  timeline,
  cueMonitor,
  stale = false,
  isExample = false,
}: SongTimelineProps) {
  if (timeline === null) {
    return (
      <section className="song-timeline song-timeline-empty">
        <p className="song-timeline-eyebrow">DIRECTOR TIMELINE</p>
        <h2>아직 검토할 곡이 없습니다.</h2>
        <p>디자인 인터뷰를 완료하면 구간별 연출과 Cue 설계가 이곳에 표시됩니다.</p>
      </section>
    );
  }

  const executor = linkedTimelineExecutor(timeline, cueMonitor);
  const consoleStored = timelineConsoleStored(timeline);
  const readbackText = timeline.readback.verified === null
    ? "아직 콘솔에 적용하지 않았습니다."
    : timeline.readback.message ?? (timeline.readback.verified ? "검증 완료" : "검증 실패");

  return (
    <section className="song-timeline" aria-label={`${timeline.song_title} 감독 타임라인`}>
      <header className="song-timeline-header">
        <div>
          <p className="song-timeline-eyebrow">
            {isExample ? "DEMO · CONSOLE WRITE DISABLED" : `DIRECTOR TIMELINE / SEQUENCE ${timeline.sequence_number}`}
          </p>
          <h2>{timeline.song_title}</h2>
          <p className="song-timeline-subtitle">
            {TIMING_LABEL[timeline.timing_mode]}
            {timeline.timecode_number !== null && ` · TIMECODE ${timeline.timecode_number}`}
          </p>
        </div>
        <div className={`song-timeline-status is-${timeline.lifecycle}`}>
          <span>{LIFECYCLE_LABEL[timeline.lifecycle]}</span>
          <small>{isExample ? "예제 데이터입니다. 콘솔에 적용하거나 검증하지 않습니다." : stale ? "연결이 끊겨 마지막 계획을 표시 중" : readbackText}</small>
        </div>
      </header>

      {(timeline.warnings ?? []).length > 0 && (
        <ul className="song-timeline-warnings" aria-label="설계 경고">
          {(timeline.warnings ?? []).map((warning) => (
            <li key={warning}>{warning}</li>
          ))}
        </ul>
      )}

      <div className={`song-timeline-execution-link${consoleStored && executor ? " is-linked" : ""}`}>
        <b>LIVE EXECUTION</b>
        {!consoleStored ? (
          <span>계획 단계 — 콘솔에 저장된 큐가 없습니다.</span>
        ) : executor ? (
          <>
            <span>EXEC {executor.executor_no} · {executor.sequence_name ?? `SEQUENCE ${timeline.sequence_number}`}</span>
            <strong>{executor.current_cue?.status === "ok" ? `현재 Cue ${executor.current_cue.value}` : "현재 Cue 확인 불가"}</strong>
          </>
        ) : (
          <span>SEQUENCE {timeline.sequence_number}에 연결된 실행기가 없습니다.</span>
        )}
      </div>

      <DecisionRail timeline={timeline} />

      <div className="song-timeline-track" role="list">
        {timeline.sections.map((section, index) => (
          <TimelineSectionCard
            key={`${section.index}-${section.cue_number}`}
            section={section}
            next={timeline.sections[index + 1]}
            executor={executor}
            lifecycle={timeline.lifecycle}
          />
        ))}
      </div>

      <div className="song-timeline-notes">
        <p><b>LINT</b> {timeline.lint.length === 0 ? "위반 없음" : `${timeline.lint.length}건 검토 필요`}</p>
        <p><b>RULES</b> {timeline.disabled.length === 0 ? "비활성 규칙 없음" : `${timeline.disabled.length}개 비활성`}</p>
        <p><b>REQUERY</b> {timeline.unresolved.length === 0 ? "미해결 입력 없음" : `${timeline.unresolved.length}개 재질의 필요`}</p>
      </div>
    </section>
  );
}
