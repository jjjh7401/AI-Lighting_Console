// 이음매(◆) 끌기 — 순수 계산(SPEC-LDBEAT-001 M9, 이음매 드래그). 시안
// `reports/ldbeat-runbook-ui-proposal-20261008.html` 표의 「큐 길이」 행: 이음매를
// 좌우로 끌면 다음 큐의 트리거 박이 옮겨진다 — 박 단위로 붙는다. 끌기는 마디 안의
// 트리거 박만 옮긴다(첫 박~마지막 박). 놓을 때만 기존 전환 편집 요청으로 보낸다.
// 포인터 이벤트는 호출하는 쪽(BeatGridJoint)이 받아 여기로 넘기고, 여기는 계산만 한다.

/** 이 거리(px) 미만으로 움직이면 끌기가 아니라 누르기다 — 떨림을 끌기로 치지 않는다. */
export const SEAM_DRAG_THRESHOLD_PX = 3;

/** 놓은 뒤 서버 응답이 오기 전까지 옮긴 자리를 보여 주는 시간(ms). 응답이 없으면 저장된 자리로 돌아간다. */
export const SEAM_DROP_HOLD_MS = 1500;

/** 끌어서 옮긴 거리(px)를 트리거 박(1부터)으로 바꾼다. 가장 가까운 박에 붙이고, 마디 밖으로는 나가지 않는다.
 * 박 수를 모르면(`beatsPerBar` 가 `null`) 박 단위로 붙일 수 없으니 `null` 이다. */
export function seamTriggerBeat(input: {
  startBeat: number;
  deltaPx: number;
  pxPerBar: number;
  beatsPerBar: number | null;
}): number | null {
  const { startBeat, deltaPx, pxPerBar, beatsPerBar } = input;
  if (beatsPerBar === null || beatsPerBar < 1 || pxPerBar <= 0) return null;
  const pxPerBeat = pxPerBar / beatsPerBar;
  const index = Math.round(startBeat - 1 + deltaPx / pxPerBeat);
  return Math.min(beatsPerBar, Math.max(1, index + 1));
}

/** 끌기 상태 — 누르기부터 놓기까지. `pressed` 는 아직 끌기가 아니다(임계값 전). */
export type SeamDragState =
  | { phase: "idle" }
  | { phase: "pressed"; pointerId: number; startX: number; startBeat: number }
  | { phase: "dragging"; pointerId: number; startX: number; startBeat: number; beat: number };

export type SeamDragEvent =
  | { type: "down"; pointerId: number; x: number; startBeat: number }
  | { type: "move"; pointerId: number; x: number; pxPerBar: number; beatsPerBar: number | null }
  | { type: "up"; pointerId: number; x: number; pxPerBar: number; beatsPerBar: number | null }
  | { type: "cancel"; pointerId: number };

export interface SeamDragOutcome {
  state: SeamDragState;
  /** 놓을 때 옮겨진 트리거 박 — 처음 박과 다를 때만. 그 밖에는 `null`. */
  commitBeat: number | null;
  /** 끌었으면 뒤따르는 클릭(편집 창 열기)을 무시한다 — 끌기 뒤 클릭이 편집을 열면 안 된다. */
  suppressClick: boolean;
}

/** 끌기 한 걸음 — 상태와 이벤트를 받아 새 상태, 놓을 때의 커밋, 클릭 무시 여부를 돌려준다. */
export function reduceSeamDrag(state: SeamDragState, event: SeamDragEvent): SeamDragOutcome {
  const keep = (next: SeamDragState): SeamDragOutcome => ({
    state: next,
    commitBeat: null,
    suppressClick: false,
  });
  switch (event.type) {
    case "down":
      return keep({
        phase: "pressed",
        pointerId: event.pointerId,
        startX: event.x,
        startBeat: event.startBeat,
      });
    case "move": {
      if (state.phase === "idle" || state.pointerId !== event.pointerId) return keep(state);
      const deltaPx = event.x - state.startX;
      if (state.phase === "pressed" && Math.abs(deltaPx) < SEAM_DRAG_THRESHOLD_PX) return keep(state);
      const beat = seamTriggerBeat({
        startBeat: state.startBeat,
        deltaPx,
        pxPerBar: event.pxPerBar,
        beatsPerBar: event.beatsPerBar,
      });
      if (beat === null) return keep(state);
      return keep({
        phase: "dragging",
        pointerId: state.pointerId,
        startX: state.startX,
        startBeat: state.startBeat,
        beat,
      });
    }
    case "up": {
      if (state.phase === "idle" || state.pointerId !== event.pointerId) return keep(state);
      if (state.phase === "pressed") return keep({ phase: "idle" });
      const finalBeat =
        seamTriggerBeat({
          startBeat: state.startBeat,
          deltaPx: event.x - state.startX,
          pxPerBar: event.pxPerBar,
          beatsPerBar: event.beatsPerBar,
        }) ?? state.beat;
      return {
        state: { phase: "idle" },
        commitBeat: finalBeat !== state.startBeat ? finalBeat : null,
        suppressClick: true,
      };
    }
    case "cancel": {
      if (state.phase === "idle" || state.pointerId !== event.pointerId) return keep(state);
      return {
        state: { phase: "idle" },
        commitBeat: null,
        suppressClick: state.phase === "dragging",
      };
    }
  }
}
