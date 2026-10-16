// 큐 패널이 열렸을 때 프리셋 서랍(풀 목록)을 자동으로 받을지 정하고, 드롭다운 옆 안내 문구를 만든다.
// 서랍 요청은 기존 `beat_grid_drawer_request` 를 그대로 쓴다(새 WS 타입 없음). 이 모듈은 판정과 문구만 가진다.
//
// 상태 타입은 `BeatGrid.tsx` 의 `DrawerLoadState` 와 같은 네 값이다. 컴포넌트 파일을 가져오면 순환 참조가
// 생기므로 여기서 다시 적는다(`glanceCells.ts` 의 「미정」 문구와 같은 판단).

/** 서랍 읽기 상태 — 받음 · 받는 중 · 거절(busy) · 시간 초과. */
export type DrawerLoadState = "loaded" | "loading" | "busy" | "timeout";

export interface CuePanelDrawerInput {
  /** 큐 패널이 열려 있는가(칸을 골라 둔 상태). */
  panelOpen: boolean;
  /** 받은 서랍 목록. 아직 못 받았으면 `null`. */
  drawerSections: readonly unknown[] | null;
  /** 서랍을 이미 물은 기록(답 대기·거절·시간 초과 포함). 한 번도 안 물었으면 `null`. */
  drawerAsk: { busyAt: number } | null;
  /** 서랍 요청 수단이 연결된 화면인가(`onDrawerRequest` 가 있는가). */
  canRequest: boolean;
}

/** 패널이 열렸고, 서랍이 아직 없고, 아직 묻지 않았을 때만 한 번 묻는다.
 * 거절·시간 초과 뒤에는 자동으로 다시 묻지 않는다 — 콘솔을 되풀이해 두드리지 않으려고.
 * 다시 받으려면 서랍의 「다시 시도」를 누른다. */
export function shouldAutoRequestDrawer(input: CuePanelDrawerInput): boolean {
  return input.panelOpen && input.canRequest && input.drawerSections === null && input.drawerAsk === null;
}

/** 드롭다운 옆 안내. 「먼저 열어야」로 잠그지 않고, 지금 받는 상태를 그대로 말한다. */
export function drawerPoolStatusText(state: DrawerLoadState): string {
  switch (state) {
    case "loading":
      return "프리셋 목록을 콘솔에서 받는 중입니다. 잠시만 기다려 주세요.";
    case "busy":
      return "서버가 다른 일을 처리하는 중이라 목록을 못 받았어요. 프리셋 서랍에서 「다시 시도」를 눌러 주세요.";
    case "timeout":
      return "콘솔 답이 늦어요. 프리셋 서랍에서 「다시 시도」를 눌러 주세요.";
    case "loaded":
      return "콘솔 서랍에 이 풀이 없어요.";
  }
}
