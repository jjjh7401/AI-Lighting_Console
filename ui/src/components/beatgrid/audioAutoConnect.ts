// 음원 자동 연결 상태 전이 (SPEC-LDBEAT-001 M9 step 7, 카드 t570,
// REQ-LDBEAT-024(c)).
//
// 이 세션에서 이미 첨부된 곡 음원(기존 업로드 경로 — `App.tsx`
// `uploadSongAudio`가 읽는 File)이 있으면 런북 전체화면 뷰를 열 때
// 자동으로 연결한다. 이 모듈은 `File`/`HTMLAudioElement`를 직접 다루지
// 않는다(jsdom 시험대 없음, BeatGrid.test.tsx 와 같은 경계) — 연결 상태
// 전이·버튼 문구·재생 큐잉 판정만 순수 함수로 둔다. DOM 쪽(objectURL
// 생성·`<audio>` 이벤트 리스너)은 `BeatGrid.tsx`가 그대로 건다.

// 카드 t571(REQ-LDBEAT-024(c) 후속) — `"missing"`을 추가한다: 세션 첨부도
// 없고, 서버에 물어본 결과("song_audio_link_request") 이 곡엔 저장된 링크도
// 없다고 확인된 상태다. `"idle"`(아직 아무것도 시도하지 않음)과는 다르다 —
// 이미 "확인해 봤다"는 사실을 운영자에게 솔직하게 보여준다(♪ 버튼 "음원 없음").
export type AudioConnectStatus = "idle" | "loading" | "connected" | "failed" | "missing";

export interface AudioConnectState {
  status: AudioConnectStatus;
  /** 지금 연결(또는 연결 시도) 중인 음원의 안정적 식별자. 같은 음원으로
   * 다시 자동 연결을 반복하지 않으려고 쓴다(`audioSourceId`). */
  connectedSourceId: string | null;
}

/** 파일 하나를 구분하는 안정적 식별자(이름+크기) — `File` 객체 참조
 * 동일성에 기대지 않는다(React 리렌더마다 같은 File이 새 참조로 올 수도
 * 있는 호출부를 가정하지 않기 위해서다). 파일이 없으면 `null`. */
export function audioSourceId(file: { name: string; size: number } | null): string | null {
  if (!file) return null;
  return `${file.name}:${file.size}`;
}

/** 런북 전체화면 뷰를 열 때(또는 첨부된 음원이 바뀌었을 때) 자동으로
 * 연결해야 하는가(REQ-LDBEAT-024(c)). 첨부된 음원이 없으면(`null`)
 * 연결하지 않는다 — 이미 그 음원에 연결·연결 시도 중이면 반복하지
 * 않는다(무한 재연결 루프 방지). */
export function shouldAutoConnectAudio(
  state: AudioConnectState,
  attachedSourceId: string | null,
): boolean {
  if (!attachedSourceId) return false;
  if (state.status === "loading") return false;
  if (state.status === "connected" && state.connectedSourceId === attachedSourceId) return false;
  return true;
}

/** ♪ 버튼 문구(mockup `audLbl`) — 연결되면 체크(✓)+파일명, 불러오는
 * 중이면 그 사실, 서버에 저장된 링크가 없다고 확인됐으면(카드 t571)
 * "음원 없음", 그 밖(idle·failed)은 기본 안내. 지어낸 파일명을 보이지
 * 않는다 — `audioName`이 없으면 기본 안내로 떨어진다. */
export function audioButtonLabel(status: AudioConnectStatus, audioName: string | null): string {
  if (status === "connected" && audioName) return `✓ ${audioName}`;
  if (status === "loading") return "불러오는 중…";
  if (status === "missing") return "음원 없음";
  return "음원";
}

/** ♪ 버튼 짧은 문구 — 1450px 이상에서만 보인다(상단 바가 한 줄을 지키려고). 연결되면 체크(✓)만
 * 보이고 파일명은 버튼 title 로 본다. 그 밖의 상태는 원래 문구가 이미 짧아 그대로 쓴다. */
export function audioButtonShortLabel(status: AudioConnectStatus, audioName: string | null): string {
  if (status === "connected" && audioName) return "✓";
  return audioButtonLabel(status, audioName);
}

/** 카드 t571 — 서버가 "이 곡엔 저장된 링크가 없다"고 답했을 때
 * (`songAudioLinkMissing`) `"missing"` 상태로 넘어가야 하는가. `"idle"`일
 * 때만 — 이미 다른 전이(연결 시도/연결/실패) 중이면 덮어쓰지 않는다. 이
 * 상태에서 나가는 길은 `shouldAutoConnectAudio`가 쥔다(첨부든 링크든 실제
 * 파일이 나타나면 그 쪽이 이긴다). */
export function shouldMarkAudioLinkMissing(status: AudioConnectStatus): boolean {
  return status === "idle";
}

/** 연결 실패 이유(AC-LDBEAT-024(c)) — 화면에 그대로 보일 문자열. */
export function formatAudioConnectFailureReason(fileName: string): string {
  return `${fileName} 을 읽지 못했어요 — 「♪ 음원」을 눌러 파일을 직접 골라 주세요`;
}

/** ▶ 를 눌렀을 때 지금 바로 처리하지 않고 뒤로 미뤄야 하는가 —
 * 불러오는 중(`loading`)일 때만(AC-LDBEAT-024(b)). idle·failed 는 BPM
 * 시계만으로도(음원 없이) 바로 재생을 시작할 수 있으므로 미루지
 * 않는다. */
export function shouldDeferPlayPress(status: AudioConnectStatus): boolean {
  return status === "loading";
}

export interface PlayIntentResolution {
  /** 지금 재생을 시작해야 하는가. */
  shouldStart: boolean;
  /** 큐잉 상태를 유지해야 하는가(아직 loading 이면 유지). */
  nextPending: boolean;
}

/** 큐잉된 재생 의도(`pendingPlayIntent`)가 연결 상태 전이 뒤 어떻게
 * 되는가(AC-LDBEAT-024(b) "로딩 완료 즉시 재생이 시작된다 — 대기 없이
 * 큐잉"). 큐잉이 없으면 아무것도 하지 않는다. 큐잉 중 `loading`이
 * 계속되면 큐잉을 유지한다. `connected`가 되면 즉시 시작하고 큐잉을
 * 지운다. `failed`가 되면(음원을 못 읽음) 시작하지 않고 큐잉만 지운다 —
 * 실패를 재생 시작으로 지어내지 않는다. */
export function resolvePlayIntentOnReady(
  pendingPlayIntent: boolean,
  status: AudioConnectStatus,
): PlayIntentResolution {
  if (!pendingPlayIntent) return { shouldStart: false, nextPending: false };
  if (status === "loading") return { shouldStart: false, nextPending: true };
  return { shouldStart: status === "connected", nextPending: false };
}
