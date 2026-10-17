// 「이 마디 한눈에」 줄 이름 ▸ 펼침의 상세 한 줄(REQ-LDBEAT-023(b)) —
// 장비 번호·Seq/Cue·마디 범위·길이·타임코드 시각·콘솔 명령. SPEC-LDBEAT-001
// M9 step 6, 카드 t560.
//
// §Gaps(카드 t560 보고) — 아래 두 자리는 클라이언트 모델에 아예 없는
// 데이터라 **항상** `GLANCE_DETAIL_UNKNOWN`으로 떨어진다(지어내지 않는다):
//   - Seq/Cue 번호: `BeatGridTrack`/`BeatGridCue`에 시퀀스·큐 번호 필드가
//     없다(그룹 **번호**(`group_no`)와는 다른 축).
//   - 콘솔 명령 문자열: 명령 합성은 서버(`server/director/emit.py`)
//     소관이고 클라이언트에 노출되지 않는다.
// 장비 번호는 `fixtures[].confirmedGroupName`이 그 트랙의 `group_name`과
// **정확히** 일치하는 것만 센다 — 이름이 비슷해 보인다는 추론(접두 매칭)은
// 쓰지 않는다(BeatGrid.tsx `fixtureDisplayColor`와 같은 원칙).
import { formatTc } from "../CueSheetTimeline";

export const GLANCE_DETAIL_UNKNOWN = "미확인";

export interface GlanceDetailTrack {
  group_name: string;
}

export interface GlanceDetailFixture {
  fid: number;
  confirmedGroupName?: string | null;
}

export interface GlanceRowDetail {
  fixtureNumbers: number[] | typeof GLANCE_DETAIL_UNKNOWN;
  seqCue: typeof GLANCE_DETAIL_UNKNOWN;
  barRangeLabel: string;
  lengthBars: number;
  timecodeLabel: string;
  consoleCommand: typeof GLANCE_DETAIL_UNKNOWN;
}

export function buildGlanceRowDetail(params: {
  track: GlanceDetailTrack;
  /** 이 칸이 시작하는 마디. */
  startBar: number;
  /** 배타적 — `trackCueSegments`의 관례와 같다. */
  endBar: number;
  secondsPerBar: number | null | undefined;
  /** 0마디가 시작하는 곡 시각(초) — 타임코드 표시 기준(콘솔 큐와 같다). 없으면 0초. */
  barZeroStartSeconds?: number | null;
  fixtures: readonly GlanceDetailFixture[];
}): GlanceRowDetail {
  const { track, startBar, endBar, secondsPerBar, fixtures } = params;
  const zeroStart = params.barZeroStartSeconds ?? 0;
  const confirmedFids = fixtures
    .filter((fixture) => fixture.confirmedGroupName === track.group_name)
    .map((fixture) => fixture.fid)
    .sort((a, b) => a - b);
  const lengthBars = Math.max(0, endBar - startBar);
  const hasSecondsPerBar = !!secondsPerBar && Number.isFinite(secondsPerBar) && secondsPerBar > 0;
  const timecodeLabel = hasSecondsPerBar
    ? formatTc(Math.max(0, zeroStart + startBar * (secondsPerBar as number)) * 1000)
    : GLANCE_DETAIL_UNKNOWN;
  return {
    fixtureNumbers: confirmedFids.length > 0 ? confirmedFids : GLANCE_DETAIL_UNKNOWN,
    seqCue: GLANCE_DETAIL_UNKNOWN,
    barRangeLabel: `${startBar}~${endBar - 1}마디`,
    lengthBars,
    timecodeLabel,
    consoleCommand: GLANCE_DETAIL_UNKNOWN,
  };
}
