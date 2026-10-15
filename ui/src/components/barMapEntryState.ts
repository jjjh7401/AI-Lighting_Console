// 마디 지도 진입 컨트롤의 순수 상태 리듀서 (SPEC-LDBARMAP-003, 카드 t648).
//
// DOM 도 React 도 소켓도 없다. 이벤트를 받아 다음 상태를 돌려줄 뿐이다. 이 프로젝트에는
// DOM 시험대가 없어서(spec.md §4 「시험 방식」) 대기·결과·오류·취소·끊김의 전이를 전부
// 여기에 모았고, `barMapEntryState.test.ts` 가 이벤트를 차례로 먹여 결과 상태를 본다.
// 소켓 훅과 컴포넌트는 이 리듀서를 부르거나 그 상태를 props 로 받을 뿐이다.
//
// 규칙 요약
// - 대기(`waiting`)는 결과 라벨, 오류 종류, 소켓 끊김, 「취소」로만 끝난다(REQ-LDBARUI-005).
// - `busy` 에는 요청 번호가 없어 이 요청의 거절인지 다른 요청(채팅 등)의 거절인지 가를 수
//   없다(spec.md §4). 그래서 안내만 바꾸고 대기는 끝내지 않는다(REQ-LDBARUI-009).
// - 「취소」는 화면의 대기만 끈다. 서버의 분석은 계속될 수 있으므로, 취소 뒤에 온 결과도
//   무시하지 않고 같은 문구로 보인다(REQ-LDBARUI-006, 007).
// - 화면에 보이는 문구는 spec.md §4 「문구 고정표」의 글자 그대로다. 서버가 낸 거절 사유
//   (`text`)만 예외이고, 그때도 클라이언트가 사유를 지어내지 않고 그대로 보인다.
import { BAR_MAP_METER_LABEL } from "../protocol";

/** 서버 `chat_response.summary` 라벨 — 저장 성공(`session.py` 저장 관문). */
const SUMMARY_SAVED = "마디 지도 저장";

/** 서버 `chat_response.summary` 라벨 세 개 — 거절. 사유 문장은 `text` 에 있다. */
const SUMMARIES_REJECTED: ReadonlySet<string> = new Set([
  "마디 지도 분석 거절", // 범위 밖 오프셋, 분석 단계의 거절·실패, 분석 중 곡 교체
  "마디 지도 저장 거절", // 저장 검사(`validate_bar_map`) 실패
  "마디 지도 저장 불가", // 초안 타임라인이 없음
]);

/** 이 컨트롤이 문구로 끝내는 `error.kind` 두 개. 그 밖의 종류는 무시한다(REQ-LDBARUI-008). */
const ERROR_KIND_AUDIO_MISSING = "song_audio_missing";
const ERROR_KIND_PROTOCOL = "protocol";

const NOTICE_SAVED_NO_NAME = "마디 지도를 초안에 저장했습니다.";
const NOTICE_AUDIO_MISSING = "곡 오디오를 먼저 첨부해 주세요.";
const NOTICE_PROTOCOL = "분석 요청 형식이 맞지 않아 시작하지 못했습니다.";
const NOTICE_NOT_CONNECTED = "연결되어 있지 않아 분석을 시작하지 못했습니다.";
const NOTICE_SOCKET_CLOSED = "연결이 끊겨 분석 결과를 받지 못했을 수 있습니다.";
const NOTICE_CANCELLED = "취소했습니다. 서버의 분석은 계속될 수 있으며, 끝나면 이 자리에 결과가 표시됩니다.";

/** 곡 박자표가 분석기의 박자표와 다를 때 컨트롤 곁에 보이는 사실 문구(REQ-LDBARUI-003).
 * 박자표 숫자는 상수에서 만든다(REQ-LDBARUI-011) — 선택지 범위는 이 문구가 바꾸지 않는다. */
export const BAR_MAP_NOTICE_OFF_METER = `이 분석기는 ${BAR_MAP_METER_LABEL} 곡만 다룬다.`;

/** `idle`: 요청 전이거나 끝난 뒤. `waiting`: 요청을 보냈고 결과를 기다린다. */
export type BarMapEntryPhase = "idle" | "waiting";

export interface BarMapEntryState {
  phase: BarMapEntryPhase;
  /** 사람이 고른 첫 박 오프셋. 고르기 전에는 `null` — 기본값이 없다(REQ-LDBARUI-002). */
  offset: number | null;
  /** 요청을 보낸 시점의 곡 파일명(결과 문구에 쓴다). 없으면 `null`. 타임라인 곡과 같은지는
   * 확인하지 않는다(spec.md Gaps 6번). */
  songName: string | null;
  /** 컨트롤 안에 보이는 안내 줄. 없으면 `null`. */
  notice: string | null;
}

export const initialBarMapEntryState: BarMapEntryState = {
  phase: "idle",
  offset: null,
  songName: null,
  notice: null,
};

export type BarMapEntryEvent =
  /** 사람이 드롭다운에서 고름. 「선택」(빈 값)으로 되돌리면 `null`. */
  | { type: "offset-selected"; offset: number | null }
  /** 요청 프레임이 실제로 나갔다. `songName` 은 보낸 시점의 곡 파일명. */
  | { type: "sent"; songName: string | null }
  /** 연결이 열려 있지 않아 프레임을 보내지 못했다. */
  | { type: "not-connected" }
  /** 사용자가 「취소」를 눌렀다. 화면의 대기만 끈다. */
  | { type: "cancel" }
  /** 소켓이 끊겼다. */
  | { type: "socket-closed" }
  /** 서버가 `busy` 를 보냈다. `message` 는 프레임의 안내 문장. */
  | { type: "busy"; message: string }
  /** `chat_response` 프레임 — `summary` 라벨이 결과를 가른다. */
  | { type: "chat-response"; summary: string; text: string }
  /** `error` 프레임 — `kind` 가 이 컨트롤의 것인지 가른다. */
  | { type: "error"; kind: string };

/** 곡 박자표 문자열이 분석기의 박자표와 다른가. 공백을 뺀 값이 있고 `BAR_MAP_METER_LABEL`
 * 과 다를 때만 참이다. 없거나 비었거나 같으면 거짓 — 모르는 박자표를 "다르다"고 하지
 * 않는다(REQ-LDBARUI-003). */
export function isOffMeter(timelineMeter: string | null | undefined): boolean {
  if (timelineMeter === null || timelineMeter === undefined) return false;
  const compact = timelineMeter.replace(/\s+/g, "");
  return compact !== "" && compact !== BAR_MAP_METER_LABEL;
}

/** 저장 성공 한 줄. 파일명이 없으면 이름 없는 문구다(REQ-LDBARUI-006). */
function savedNotice(songName: string | null): string {
  return songName ? `곡 «${songName}» ${NOTICE_SAVED_NO_NAME}` : NOTICE_SAVED_NO_NAME;
}

/** 대기 중일 때만 대기를 끝내고 안내를 바꾼다. 대기 중이 아니면 아무것도 바꾸지 않는다. */
function endWaiting(state: BarMapEntryState, notice: string): BarMapEntryState {
  return state.phase === "waiting" ? { ...state, phase: "idle", notice } : state;
}

function reduceChatResponse(state: BarMapEntryState, summary: string, text: string): BarMapEntryState {
  // 결과는 대기 중이든 「취소」 뒤든 같은 문구로 보이고 늦은 결과를 무시하지 않는다.
  // 그래서 여기서는 phase 를 따지지 않고, 어느 쪽에서 왔든 `idle` 로 둔다.
  if (summary === SUMMARY_SAVED) return { ...state, phase: "idle", notice: savedNotice(state.songName) };
  // 거절 사유는 서버 문장 그대로다. 클라이언트가 지어내거나 다듬지 않는다(REQ-LDBARUI-007).
  if (SUMMARIES_REJECTED.has(summary)) return { ...state, phase: "idle", notice: text };
  return state;
}

function reduceError(state: BarMapEntryState, kind: string): BarMapEntryState {
  // 대기 중이 아닐 때의 `error` 는 다른 흐름의 것이라 이 컨트롤이 건드리지 않는다.
  if (kind === ERROR_KIND_AUDIO_MISSING) return endWaiting(state, NOTICE_AUDIO_MISSING);
  if (kind === ERROR_KIND_PROTOCOL) return endWaiting(state, NOTICE_PROTOCOL);
  return state;
}

export function barMapEntryReducer(state: BarMapEntryState, event: BarMapEntryEvent): BarMapEntryState {
  switch (event.type) {
    case "offset-selected":
      return { ...state, offset: event.offset };
    case "sent":
      // 새 요청이 시작되면 앞 요청의 안내 줄은 더 이상 이 요청의 것이 아니라서 지운다.
      // 대기 중에는 이미 요청이 나가 있으므로 두 번째 `sent` 는 받지 않는다.
      return state.phase === "idle"
        ? { ...state, phase: "waiting", songName: event.songName, notice: null }
        : state;
    case "not-connected":
      // 프레임이 나가지 않았으니 대기에 들어가지 않는다. 대기를 끝내는 사건도 아니다.
      return state.phase === "idle" ? { ...state, notice: NOTICE_NOT_CONNECTED } : state;
    case "cancel":
      return endWaiting(state, NOTICE_CANCELLED);
    case "socket-closed":
      return endWaiting(state, NOTICE_SOCKET_CLOSED);
    case "busy":
      // 안내만 바꾸고 대기는 끝내지 않는다. 대기 중이 아니면 이 컨트롤과 무관하다.
      return state.phase === "waiting" ? { ...state, notice: event.message } : state;
    case "chat-response":
      return reduceChatResponse(state, event.summary, event.text);
    case "error":
      return reduceError(state, event.kind);
    default:
      // 모르는 이벤트는 아무것도 바꾸지 않는다.
      return state;
  }
}
