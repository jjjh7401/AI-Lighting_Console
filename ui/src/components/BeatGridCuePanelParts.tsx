// 박자 격자 — 큐 편집 칸의 새 부품들(SPEC-LDBEAT-001 M9 step 3·4, 카드
// t561, REQ-LDBEAT-020(c)·021(a)(b)). 정본: design/ldbeat-runbook-ui-
// proposal-20261008.html `drawClipEd` — 머리(줄·Cue·마디·초·타임코드) →
// 밝기 → 위치 → 색 → 움직임 → 옆빛 L·R → 콘솔 명령. `BeatGrid.tsx`는
// 이 부품들을 마운트만 한다.
import { useEffect, useRef, useState, type ReactNode } from "react";

import type { BeatGridCue, BeatGridTrack } from "../protocol";
import "./beatGridPanels.css";

/** 편집 칸이 초점을 둘 수 있는 항목(「이 마디 한눈에」 표 클릭 등에서 온다,
 * REQ-LDBEAT-021(a)). 값은 편집 칸 행의 `data-field` 와 짝지어진다. */
export type BeatGridFocusField = "밝기" | "위치" | "색" | "움직임" | "옆빛";

const FOCUS_FIELD_ROWS: Record<BeatGridFocusField, readonly string[]> = {
  밝기: ["밝기"],
  위치: ["위치 프리셋"],
  색: ["색 프리셋"],
  움직임: ["움직임", "효과 프리셋"],
  옆빛: ["옆빛 L·R"],
};

/** 초점 항목 → 편집 칸 행 이름(`data-field`) 후보. */
export function focusFieldRowNames(field: BeatGridFocusField): readonly string[] {
  return FOCUS_FIELD_ROWS[field];
}

/** 큐 편집 화면을 감싸 `focusField` 가 가리키는 행에 노란 테두리를 두고
 * 그 행으로 스크롤한다(시안 `FOCUS` — `el.focus(); outline 2px #ffd84d`).
 * 초점은 `focusField` 나 `focusKey`(지금 고른 칸)가 바뀔 때만 옮긴다 —
 * 다시 그릴 때마다 옮기면 입력 중인 칸에서 커서가 빠져나간다. */
export function BeatGridCueFocus({
  focusField,
  focusKey,
  children,
}: {
  focusField: BeatGridFocusField | null;
  focusKey?: string;
  children: ReactNode;
}) {
  const ref = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    const root = ref.current;
    if (!root) return;
    root.querySelectorAll(".is-focused").forEach((el) => el.classList.remove("is-focused"));
    if (!focusField) return;
    for (const name of focusFieldRowNames(focusField)) {
      const row = root.querySelector<HTMLElement>(`[data-field="${name}"]`);
      if (!row) continue;
      row.classList.add("is-focused");
      row.scrollIntoView?.({ block: "nearest" });
      row.querySelector<HTMLElement>("select, input, button, [tabindex]")?.focus();
      break;
    }
  }, [focusField, focusKey]);
  return (
    <div className="beat-grid-cue-view" ref={ref} data-focus-field={focusField ?? undefined}>
      {children}
    </div>
  );
}

/** 머리 둘째 줄 — Cue 번호·마디 범위·길이·초·곡 시각(시안 `drawClipEd`
 * 머리의 `fx` 줄). 초는 곡 BPM이 있을 때만 쓴다. */
export function BeatGridCueHeadMeta({
  track,
  cue,
  endBar,
  secondsPerBar,
  confirmedFixtureCount,
}: {
  track: BeatGridTrack;
  cue: BeatGridCue;
  endBar: number;
  secondsPerBar: number | null | undefined;
  confirmedFixtureCount: number;
}) {
  const cueNo = track.cues.indexOf(cue) + 1;
  const lengthBars = endBar - cue.bar;
  const hasTiming = secondsPerBar !== null && secondsPerBar !== undefined;
  return (
    <div className="beat-grid-cue-head-meta">
      {confirmedFixtureCount > 0 ? `장비 ${confirmedFixtureCount}대(소속 확인)` : "장비 소속 미확인"} ·{" "}
      {track.group_no_confirmed && track.group_no !== null ? `그룹 ${track.group_no}` : "그룹 번호 미확인"}
      <br />
      Cue {cueNo} · {cue.bar}~{endBar - 1}마디 · {lengthBars}마디
      {hasTiming ? ` ≈ ${(lengthBars * secondsPerBar).toFixed(1)}초 · 곡 ${(cue.bar * secondsPerBar).toFixed(2)}초` : ""}
    </div>
  );
}

/** REQ-LDBEAT-021(b) 「움직임」 전용 행 — 앱 2단계 무빙(REQ-LDBEAT-006(vi)).
 * 값 표시는 기존 `formatAppMovementField` 결과를 그대로 받는다. */
export function BeatGridMovementRow({ value, isUnset }: { value: string; isUnset: boolean }) {
  return (
    <div className="beat-grid-cue-field" data-field="움직임">
      <span className="beat-grid-cue-field-label">움직임</span>
      <span className={`beat-grid-cue-field-value${isUnset ? " is-unset" : ""}`}>{value}</span>
    </div>
  );
}

/** REQ-LDBEAT-021(b) 「옆빛 L·R」 행 — 옆빛(side) 줄에서만. L·R 갈라짐(자식
 * 줄, REQ-LDBEAT-019(c))은 타임라인 단계의 일이라 여기서는 지금 상태와
 * 그 버튼 자리만 보인다(지어낸 갈라짐 0건). */
export function BeatGridSideRow() {
  return (
    <div className="beat-grid-cue-field" data-field="옆빛 L·R">
      <span className="beat-grid-cue-field-label">옆빛 L·R</span>
      <span className="beat-grid-cue-field-value">
        같이(갈라지지 않음){" "}
        <button type="button" className="beat-grid-tg" disabled title="L·R 자식 줄은 타임라인 단계(REQ-LDBEAT-019(c))에서 배선">
          이 구간 왼쪽·오른쪽 따로
        </button>
      </span>
    </div>
  );
}

/** REQ-LDBEAT-020(c) — 편집 칸 맨 아래 「콘솔 명령」. 켜면 노란색, 지금 보는
 * 화면(큐 편집/전환)에 맞는 명령 미리보기를 보여 준다. 아무것도 보내지
 * 않는다. */
export function BeatGridConsoleCommand({ lines }: { lines: readonly string[] }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="beat-grid-cmd-section">
      <button
        type="button"
        className={`beat-grid-tg${open ? " is-on" : ""}`}
        aria-pressed={open}
        onClick={() => setOpen((v) => !v)}
      >
        콘솔 명령
      </button>
      {open && (
        <pre className="beat-grid-cmdbox" aria-label="콘솔 명령 미리보기">
          {lines.join("\n")}
          {"\n"}(미리보기 — 송신은 「⇪ 콘솔에 반영」)
        </pre>
      )}
    </div>
  );
}
