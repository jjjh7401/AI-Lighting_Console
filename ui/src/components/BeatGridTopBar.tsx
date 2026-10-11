// 박자 격자 상단 바 (SPEC-LDBEAT-001 M9 step 8, 카드 t559, REQ-LDBEAT-017).
//
// 시안 `ldbeat-runbook-ui-proposal-20261008.html`의 `.top` 모양: 곡·버전·BPM ·
// ◀ 마디 ▶(←→ 키) · ▶ 이 마디 콘솔에서 보기 · ■ 끄기 · ⇪ 콘솔에 반영(대기 수) ·
// 프리셋 서랍. 화면 폭 1450px 이상에서는 한 줄을 지키려고 「▶ 콘솔」·「⇪ 반영」·
// 「▤」로 줄이고 풀네임은 title 로 보여 준다(REQ-LDBEAT-017(b), CSS 가 가른다).
//
// 콘솔 쓰기 경로(이 마디 미리보기·끄기·반영)는 이 카드 범위 밖이라 콜백이
// 없으면 버튼이 비활성으로 남고, 그 사실을 title 로 말한다(지어낸 동작 0).
import { useEffect } from "react";

export interface TopBarAction {
  id: "preview" | "apply" | "drawer";
  full: string;
  short: string;
}

/** 1450px 이상에서 줄여 보이는 세 버튼(시안 `:122`). */
export const TOP_BAR_SHORTENED_ACTIONS: readonly TopBarAction[] = [
  { id: "preview", full: "▶ 이 마디 콘솔에서 보기", short: "▶ 콘솔" },
  { id: "apply", full: "⇪ 콘솔에 반영", short: "⇪ 반영" },
  { id: "drawer", full: "▤ 프리셋 서랍", short: "▤" },
];

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

export function formatTopBarBpm(bpm: number | null | undefined): string {
  if (typeof bpm !== "number" || !Number.isFinite(bpm) || bpm <= 0) return "BPM —";
  return `BPM ${Number(bpm.toFixed(2))}`;
}

export interface BeatGridTopBarProps {
  songTitle: string;
  /** 격자 출처 안내(`BeatGridView.note`) — 기존 머리줄에 있던 값을 그대로 옮긴다. */
  note?: string | null;
  versionLabel: string | null;
  bpm: number | null | undefined;
  currentBar: number;
  barRange: { start: number; end: number };
  onBarChange: (bar: number) => void;
  onPreviewBar?: (bar: number) => void;
  onPreviewOff?: () => void;
  onApply?: () => void;
  /** 콘솔에 아직 안 보낸 편집 수. 출처가 없으면 생략 — 숫자를 지어내지 않는다. */
  pendingApplyCount?: number | null;
  onDrawerToggle?: () => void;
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
  barRange,
  onBarChange,
  onPreviewBar,
  onPreviewOff,
  onApply,
  pendingApplyCount,
  onDrawerToggle,
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

  const [preview, apply, drawer] = TOP_BAR_SHORTENED_ACTIONS;
  const titleFor = (full: string, wired: boolean) => (wired ? full : full + UNWIRED_NOTE);

  return (
    <header className="beat-grid-topbar">
      <b className="beat-grid-topbar-mode">런북 모드</b>
      <span className="beat-grid-pill beat-grid-song">{songTitle || "(곡 미지정)"}</span>
      {versionLabel && <span className="beat-grid-pill">{versionLabel}</span>}
      <span className="beat-grid-pill" title="스피드 마스터 BPM 은 콘솔에서 직접 설정">
        {formatTopBarBpm(bpm)}
      </span>
      {note && <span className="beat-grid-note">{note}</span>}
      <span className="beat-grid-topbar-spacer" />
      <button
        type="button"
        className="tbtn"
        title="이전 마디 (←)"
        disabled={currentBar <= barRange.start}
        onClick={() => onBarChange(stepBar(currentBar, -1, barRange))}
      >
        ◀
      </button>
      <span className="beat-grid-topbar-bar">{currentBar}마디</span>
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
      <button
        type="button"
        className="tbtn"
        title={titleFor(apply.full, !!onApply)}
        disabled={!onApply}
        onClick={() => onApply?.()}
      >
        <ShortenedLabel action={apply} />
        {typeof pendingApplyCount === "number" && <span className="badge">{pendingApplyCount}</span>}
      </button>
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
