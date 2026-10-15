// 박자 격자 상단 바 (SPEC-LDBEAT-001 M9 step 8, 카드 t559, REQ-LDBEAT-017).
//
// 시안 `ldbeat-runbook-ui-proposal-20261008.html`의 `.top` 모양: 곡·버전·BPM ·
// ◀ 마디 ▶(←→ 키) · ▶ 이 마디 콘솔에서 보기 · ■ 끄기 · ⇪ 콘솔에 반영(대기 수) ·
// 프리셋 서랍. 화면 폭 1450px 이상에서는 한 줄을 지키려고 「▶ 콘솔」·「⇪ 반영」·
// 「▤」로 줄이고 풀네임은 title 로 보여 준다(REQ-LDBEAT-017(b), CSS 가 가른다).
//
// 콘솔 쓰기 경로(이 마디 미리보기·끄기·반영)는 이 카드 범위 밖이라 콜백이
// 없으면 버튼이 비활성으로 남고, 그 사실을 title 로 말한다(지어낸 동작 0).
import { useEffect, useState } from "react";

import { formatPlaybackClock, isPlaybackSpaceToggleKey } from "./beatgrid/playbackClock";

export interface TopBarAction {
  id: "preview" | "apply" | "drawer" | "preset-plan";
  full: string;
  short: string;
}

/** 1450px 이상에서 줄여 보이는 세 버튼(시안 `:122`). */
export const TOP_BAR_SHORTENED_ACTIONS: readonly TopBarAction[] = [
  { id: "preview", full: "▶ 이 마디 콘솔에서 보기", short: "▶ 콘솔" },
  { id: "apply", full: "⇪ 콘솔에 반영", short: "⇪ 반영" },
  { id: "drawer", full: "▤ 프리셋 서랍", short: "▤" },
];

/** 「프리셋 계획」 — 한 줄을 지키려고 1450px 이상에서는 아이콘 크기(▦)로 줄인다. */
export const TOP_BAR_PRESET_PLAN_ACTION: TopBarAction = {
  id: "preset-plan",
  full: "▦ 프리셋 계획",
  short: "▦",
};

const UNWIRED_NOTE = " — 아직 배선 안 됨(콘솔 송신 경로 없음)";

export function stepBar(current: number, delta: number, range: { start: number; end: number }): number {
  return Math.max(range.start, Math.min(range.end, current + delta));
}

/** ←/→ 만 마디 이동. 입력칸·선택칸 안의 화살표와 수정키 조합은 그대로 둔다. */
export function barNavKeyDelta(event: {
  key: string;
  targetTag?: string;
  isContentEditable?: boolean;
  altKey?: boolean;
  ctrlKey?: boolean;
  metaKey?: boolean;
  shiftKey?: boolean;
}): -1 | 0 | 1 {
  if (event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return 0;
  const tag = (event.targetTag ?? "").toUpperCase();
  if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || event.isContentEditable) return 0;
  if (event.key === "ArrowLeft") return -1;
  if (event.key === "ArrowRight") return 1;
  return 0;
}

/** REQ-LDBEAT-014(plan.md M6) — 곡 재생 중 스피드 마스터 BPM 을 자동으로 싣는
 * 방법(G9)이 미확인인 동안, BPM 알약이 자동 설정처럼 읽히지 않게 「사람이 콘솔
 * 에서 직접 설정」을 **눈에 보이게** 붙인다(hover 전용 title 만으로는 알약이
 * 앱이 맞춘 값처럼 보인다). 글자는 시안 `ldbeat-runbook-mockup-20261008.html`
 * 상단 바의 「스피드 마스터 15 — 콘솔에서 직접 설정」에서 리그 전용 번호(15)만
 * 뺐다(어느 스피드 마스터를 쓰는지는 리그마다 다르다). */
export const SPEED_MASTER_MANUAL_NOTE = "스피드 마스터 — 콘솔에서 직접 설정";
/** 카드 t587 — 1450px 이상 한 줄용 짧은 꼬리(리드 판단, REQ-LDBEAT-014). */
export const SPEED_MASTER_MANUAL_SHORT_NOTE = "콘솔에서 설정";
export const SPEED_MASTER_MANUAL_TITLE =
  "스피드 마스터 BPM 은 앱이 자동으로 싣지 않습니다 — 사람이 콘솔에서 직접 설정합니다(자동 설정 방법 미확인).";

/** 반영 준비 — 타임코드 번호 입력칸의 글자를 번호로 읽는다. 양의 정수 글자만 번호가 되고,
 * 빈칸·소수·음수·글자는 `null`이다(번호를 지어내지 않는다). */
export function parseTimecodeInput(text: string): number | null {
  const trimmed = text.trim();
  if (!/^\d+$/.test(trimmed)) return null;
  const value = Number(trimmed);
  return Number.isSafeInteger(value) && value >= 1 ? value : null;
}

/** 콜백이 넘어오지 않은 입력칸(배선 전)이 그 사실을 말하는 title. */
export const TIMECODE_UNWIRED_TITLE =
  "타임코드 번호 입력은 아직 화면에 연결되지 않았습니다 — 연결 전에는 비활성입니다";
/** 입력칸의 안내 — 시안에 없는 작은 칸이라 글 대신 title 로 말하고, 적기는 Enter 로 한다. */
export const TIMECODE_HINT_TITLE = "타임코드 번호를 넣어 주세요 — Enter 로 적기";

export function formatTopBarBpm(bpm: number | null | undefined): string {
  if (typeof bpm !== "number" || !Number.isFinite(bpm) || bpm <= 0) return "BPM —";
  return `BPM ${Number(bpm.toFixed(2))}`;
}

/** 카드 t570(REQ-LDBEAT-024(a)) — 플레이 묶음(상단 바 가운데). 로직은
 * `beatgrid/playbackClock.ts`·`beatgrid/audioAutoConnect.ts`에 있고, 이
 * 컴포넌트는 그 결과를 받아 마운트만 한다. `playback`을 안 넘기면(즉
 * 생략) 기존(카드 t559)과 바이트 동일하게 렌더된다(additive). */
export interface BeatGridTopBarPlaybackProps {
  playing: boolean;
  positionSeconds: number;
  onTogglePlay: () => void;
  onRewindToStart: () => void;
  /** ⏪10초/10초⏩(REQ-LDBEAT-024(d)) — 초 단위 이동(음수 = 뒤로). */
  onSeek: (deltaSeconds: number) => void;
  /** `audioAutoConnect.audioButtonLabel`의 결과 그대로("✓ <파일명>" 등). */
  audioButtonLabel: string;
  onSelectAudioFile: (file: File | null) => void;
  /** AC-LDBEAT-024(c) — 연결 실패 이유. 없으면 칸 자체가 없다. */
  audioFailureReason?: string | null;
  /** 「콘솔 같이」 토글이 늘 비활성인 이유(송신 경로 t563 준비 전) —
   * `consoleSyncAudio.CONSOLE_FOLLOW_DISABLED_REASON`. */
  consoleFollowDisabledReason: string;
  /** 카드 t578(REQ-LDBEAT-024(a)) — 「콘솔 같이」 켬/끔. `onToggleConsoleFollow`가
   * 없으면(송신 경로를 안 넘겼으면) 토글은 기존처럼 비활성이다. */
  consoleFollowOn?: boolean;
  onToggleConsoleFollow?: () => void;
  /** 콘솔 재생이 거절된 이유(반영 기록 없음 등). 없으면 칸 자체가 없다. */
  consoleFollowError?: string | null;
}

export interface BeatGridTopBarProps {
  songTitle: string;
  /** 격자 출처 안내(`BeatGridView.note`) — 기존 머리줄에 있던 값을 그대로 옮긴다. */
  note?: string | null;
  versionLabel: string | null;
  bpm: number | null | undefined;
  currentBar: number;
  /** 지금 마디가 속한 구간 이름 — 「N마디 한눈에」 제목에 붙는 값과 같다. 화면 폭
   * 1490px 이상에서만 마디 번호 옆에 보이고(CSS), 그보다 좁으면 마디 번호만 보이며
   * 전체 이름(「N마디 · 이름」)은 마디 칸의 title 로 본다. 없거나 `null`이면 마디
   * 번호만 보이고 title 도 없다. */
  barSectionLabel?: string | null;
  barRange: { start: number; end: number };
  onBarChange: (bar: number) => void;
  onPreviewBar?: (bar: number) => void;
  onPreviewOff?: () => void;
  onApply?: () => void;
  /** 「필요한 프리셋 만들기」 — 계획표를 먼저 받고 이어서 승인 카드가 뜬다. 없으면 버튼을 그리지 않는다. */
  onPresetPlanRequest?: () => void;
  /** 콘솔에 아직 안 보낸 편집 수. `undefined`는 배선 전이라 배지를 생략하고,
   * `null`은 아직 반영 기록이 없다는 뜻이라 「—」를 보이며(0으로 지어내지
   * 않는다), 숫자는 그 개수다. */
  pendingApplyCount?: number | null;
  onDrawerToggle?: () => void;
  /** 「자동 배치 제안」 — 서버에 초안을 한 번 요청한다(보류만 만든다). 없으면 버튼을 그리지 않는다. */
  onDraftPropose?: () => void;
  /** 카드 t570 — 플레이 묶음(REQ-LDBEAT-024(a)). 생략하면 기존과 바이트
   * 동일. */
  playback?: BeatGridTopBarPlaybackProps | null;
  /** 반영 준비 — 타임코드 번호. `timecodeNumber`는 지금 초안에 적힌 번호(없으면 `null`).
   * `onTimecodeSubmit`이 없으면 입력칸은 비활성이고 title 로 그 이유를 말한다. */
  timecodeNumber?: number | null;
  onTimecodeSubmit?: (timecodeNumber: number) => void;
}

function TimecodeField({
  value,
  onSubmit,
}: {
  value: number | null;
  onSubmit?: (timecodeNumber: number) => void;
}) {
  const [draft, setDraft] = useState(value === null ? "" : String(value));
  useEffect(() => {
    setDraft(value === null ? "" : String(value));
  }, [value]);
  const wired = onSubmit !== undefined;
  const submit = () => {
    const parsed = parseTimecodeInput(draft);
    if (parsed !== null) onSubmit?.(parsed);
  };
  return (
    <input
      type="text"
      inputMode="numeric"
      className="beat-grid-timecode-input"
      aria-label="타임코드 번호"
      title={wired ? TIMECODE_HINT_TITLE : TIMECODE_UNWIRED_TITLE}
      value={draft}
      placeholder="번호"
      disabled={!wired}
      onChange={(event) => setDraft(event.target.value)}
      onKeyDown={(event) => {
        if (event.key === "Enter") submit();
      }}
    />
  );
}

/** 배지·버튼 툴팁 — 자기 말 뒤에 격자 출처 안내(감독 상태)를 잇는다. 둘 다 없으면 title 을 두지 않는다. */
function badgeTitle(own: string | null, note: string | null): string | undefined {
  return [own, note].filter(Boolean).join(" · ") || undefined;
}

function ShortenedLabel({ action }: { action: TopBarAction }) {
  return (
    <>
      <span className="lbl-full">{action.full}</span>
      <span className="lbl-short">{action.short}</span>
    </>
  );
}

export function BeatGridTopBar({
  songTitle,
  note = null,
  versionLabel,
  bpm,
  currentBar,
  barSectionLabel,
  barRange,
  onBarChange,
  onPreviewBar,
  onPreviewOff,
  onApply,
  onPresetPlanRequest,
  timecodeNumber = null,
  onTimecodeSubmit,
  pendingApplyCount,
  onDrawerToggle,
  onDraftPropose,
  playback = null,
}: BeatGridTopBarProps) {
  useEffect(() => {
    if (typeof window === "undefined") return;
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      const delta = barNavKeyDelta({
        key: event.key,
        targetTag: target?.tagName,
        isContentEditable: target?.isContentEditable,
        altKey: event.altKey,
        ctrlKey: event.ctrlKey,
        metaKey: event.metaKey,
        shiftKey: event.shiftKey,
      });
      if (delta === 0) return;
      event.preventDefault();
      onBarChange(stepBar(currentBar, delta, barRange));
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [currentBar, barRange, onBarChange]);

  // 카드 t570(REQ-LDBEAT-024(a)) — 스페이스바로 재생/일시정지(mockup
  // `document.addEventListener("keydown", ...Space...)`). `playback`을
  // 안 넘기면(즉 플레이 묶음 자체가 없음) 리스너를 걸지 않는다.
  useEffect(() => {
    if (!playback || typeof window === "undefined") return;
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (
        !isPlaybackSpaceToggleKey({
          code: event.code,
          key: event.key,
          targetTag: target?.tagName,
          isContentEditable: target?.isContentEditable,
        })
      ) {
        return;
      }
      event.preventDefault();
      playback.onTogglePlay();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [playback]);

  const [preview, apply, drawer] = TOP_BAR_SHORTENED_ACTIONS;
  const titleFor = (full: string, wired: boolean) => (wired ? full : full + UNWIRED_NOTE);
  // 카드 t630 — 구간 이름은 1490px 이상에서만 보이고(CSS) 그보다 좁으면 마디 번호만
  // 보인다(상단 바가 두 줄로 꺾이지 않게). 전체 이름은 title 로 본다. 구분점 앞
  // 공백은 JSX 가 지우지 못하게 문자열 안에 둔다.
  const barTitle = barSectionLabel ? `${currentBar}마디 · ${barSectionLabel}` : undefined;
  const barSectionSuffix = barSectionLabel ? (
    <span className="beat-grid-topbar-bar-section">{` · ${barSectionLabel}`}</span>
  ) : null;

  return (
    <header className="beat-grid-topbar">
      <b className="beat-grid-topbar-mode">런북 모드</b>
      <span className="beat-grid-pill beat-grid-song">{songTitle || "(곡 미지정)"}</span>
      {versionLabel && <span className="beat-grid-pill">{versionLabel}</span>}
      <span className="beat-grid-pill" title={SPEED_MASTER_MANUAL_TITLE}>
        {/* 카드 t587 — 1450px 이상에서는 긴 안내 대신 짧은 안내를 보인다(한 줄
            유지). 어느 폭에서도 「콘솔에서 설정」이 눈에 보여야 자동 설정처럼
            읽히지 않는다(REQ-LDBEAT-014) — 긴 문장은 알약 title. */}
        {formatTopBarBpm(bpm)}
        <span className="beat-grid-pill-note"> · {SPEED_MASTER_MANUAL_NOTE}</span>
        <span className="beat-grid-pill-note-short"> · {SPEED_MASTER_MANUAL_SHORT_NOTE}</span>
      </span>
      <span className="beat-grid-topbar-spacer" />
      {/* 카드 t570(REQ-LDBEAT-024(a)) — 플레이 묶음(상단 바 가운데).
          두 번째 스페이서(아래)로 가운데 고정 — `playback`이 없으면(즉
          생략) 이 블록 전체가 안 나오고 위 스페이서 하나만 남아 기존
          (카드 t559)과 바이트 동일하다. */}
      {playback && (
        <>
          {/* 시안 순서 그대로(proposal.html `.play`): 플레이 · ⏮ · ⏪ 10초 ·
              ▶ 재생 · 10초 ⏩ · 시계 · ♪ 음원 · 콘솔 같이. */}
          <span className="beat-grid-play-cluster">
            <span className="beat-grid-play-label">플레이</span>
            <button type="button" className="tbtn" title="처음으로" onClick={playback.onRewindToStart}>
              ⏮
            </button>
            <button type="button" className="tbtn" title="10초 뒤로" onClick={() => playback.onSeek(-10)}>
              ⏪ 10초
            </button>
            <button
              type="button"
              className="tbtn pri"
              title="재생 / 일시정지 (스페이스)"
              onClick={playback.onTogglePlay}
            >
              {playback.playing ? "❚❚ 일시정지" : "▶ 재생"}
            </button>
            <button type="button" className="tbtn" title="10초 앞으로" onClick={() => playback.onSeek(10)}>
              10초 ⏩
            </button>
            <span className="beat-grid-clock">{formatPlaybackClock(playback.positionSeconds)}</span>
            <label
              className="tbtn beat-grid-audio-label"
              title={`${playback.audioButtonLabel} — 음원 파일을 불러오면 음악에 맞춰 재생`}
            >
              ♪ {playback.audioButtonLabel}
              <input
                type="file"
                accept="audio/*"
                hidden
                onChange={(event) => playback.onSelectAudioFile(event.target.files?.[0] ?? null)}
              />
            </label>
            {playback.onToggleConsoleFollow ? (
              <button
                type="button"
                className={`tbtn${playback.consoleFollowOn ? " pri" : ""}`}
                title="켜면 ▶ 가 콘솔 타임코드를 처음부터 재생하고, 음원은 실측 지연 뒤 시작합니다"
                aria-pressed={!!playback.consoleFollowOn}
                onClick={playback.onToggleConsoleFollow}
              >
                {playback.consoleFollowOn ? "콘솔 같이 켬" : "콘솔 같이 끔"}
              </button>
            ) : (
              <button type="button" className="tbtn" title={playback.consoleFollowDisabledReason} disabled>
                콘솔 같이 끔
              </button>
            )}
            {playback.consoleFollowError && (
              <span className="beat-grid-audio-error">{playback.consoleFollowError}</span>
            )}
            {playback.audioFailureReason && (
              <span className="beat-grid-audio-error">{playback.audioFailureReason}</span>
            )}
          </span>
          <span className="beat-grid-topbar-spacer" />
        </>
      )}
      <button
        type="button"
        className="tbtn"
        title="이전 마디 (←)"
        disabled={currentBar <= barRange.start}
        onClick={() => onBarChange(stepBar(currentBar, -1, barRange))}
      >
        ◀
      </button>
      <span className="beat-grid-topbar-bar" title={barTitle}>{currentBar}마디{barSectionSuffix}</span>
      <button
        type="button"
        className="tbtn"
        title="다음 마디 (→)"
        disabled={currentBar >= barRange.end}
        onClick={() => onBarChange(stepBar(currentBar, 1, barRange))}
      >
        ▶
      </button>
      <button
        type="button"
        className="tbtn pri"
        title={titleFor(preview.full, !!onPreviewBar)}
        disabled={!onPreviewBar}
        onClick={() => onPreviewBar?.(currentBar)}
      >
        <ShortenedLabel action={preview} />
      </button>
      <button
        type="button"
        className="tbtn"
        title={titleFor("■ 끄기", !!onPreviewOff)}
        disabled={!onPreviewOff}
        onClick={() => onPreviewOff?.()}
      >
        ■ 끄기
      </button>
      <TimecodeField value={timecodeNumber} onSubmit={onTimecodeSubmit} />
      {/* 격자 출처 안내(감독 상태)는 반영 배지 툴팁으로 옮겼다. 배지가 없는 배선 전 상태에서만 버튼 title 에 싣는다. */}
      <button
        type="button"
        className="tbtn"
        title={
          pendingApplyCount === undefined
            ? badgeTitle(titleFor(apply.full, !!onApply), note)
            : titleFor(apply.full, !!onApply)
        }
        disabled={!onApply}
        onClick={() => onApply?.()}
      >
        <ShortenedLabel action={apply} />
        {typeof pendingApplyCount === "number" && (
          <span className="badge" title={badgeTitle(null, note)}>
            {pendingApplyCount}
          </span>
        )}
        {pendingApplyCount === null && (
          <span
            className="badge badge-dash"
            title={badgeTitle("반영 기록 없음 — 첫 반영 뒤에 숫자가 보인다", note)}
          >
            —
          </span>
        )}
      </button>
      {onDraftPropose && (
        <button
          type="button"
          className="tbtn"
          title="자동 배치 제안 — 초안을 보류로 만든다. 「적용」 전까지 격자는 그대로다"
          onClick={() => onDraftPropose()}
        >
          자동 배치
        </button>
      )}
      {onPresetPlanRequest && (
        <button
          type="button"
          className="tbtn"
          title="프리셋 계획 — 필요한 프리셋 만들기: 격자 칸이 쓰는 값으로 만들 프리셋 계획표를 보이고, 승인 카드를 띄운다"
          aria-label="프리셋 계획"
          onClick={() => onPresetPlanRequest()}
        >
          <ShortenedLabel action={TOP_BAR_PRESET_PLAN_ACTION} />
        </button>
      )}
      <button
        type="button"
        className="tbtn"
        title={onDrawerToggle ? drawer.full : drawer.full + " — M3에서 배선"}
        disabled={!onDrawerToggle}
        onClick={() => onDrawerToggle?.()}
      >
        <ShortenedLabel action={drawer} />
      </button>
    </header>
  );
}
