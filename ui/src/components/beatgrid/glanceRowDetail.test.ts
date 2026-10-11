// REQ-LDBEAT-023(b) — 「이 마디 한눈에」 줄 이름 ▸ 펼침의 상세 한 줄
// (장비 번호·Seq/Cue·마디 범위·길이·타임코드 시각·콘솔 명령) 순수 함수
// 시험. SPEC-LDBEAT-001 M9 step 6, 카드 t560.
//
// 데이터 경계(§Gaps, 카드 t560 보고): Seq/Cue 번호와 콘솔 명령 문자열은
// 클라이언트 모델(BeatGridCue/BeatGridTrack)에 없다(서버 emit.py 소관) —
// 그 둘은 항상 GLANCE_DETAIL_UNKNOWN("미확인")으로 떨어진다(지어내지
// 않는다). 장비 번호는 `fixtures[].confirmedGroupName`이 그 트랙 이름과
// 정확히 일치하는 것만 센다(이름 추정 금지, BeatGrid.tsx 기존 원칙과 동일).
import { describe, expect, it } from "vitest";

import { GLANCE_DETAIL_UNKNOWN, buildGlanceRowDetail } from "./glanceRowDetail";

const TRACK = { group_no: 7, group_no_confirmed: true, group_name: "FOOBAR-ALL", layer_role: "side", cues: [] };

describe("buildGlanceRowDetail", () => {
  it("확인된 소속 장비만 번호로 센다", () => {
    const detail = buildGlanceRowDetail({
      track: TRACK,
      startBar: 11,
      endBar: 14,
      secondsPerBar: 2,
      fixtures: [
        { fid: 301, confirmedGroupName: "FOOBAR-ALL" },
        { fid: 302, confirmedGroupName: "FOOBAR-ALL" },
        { fid: 401, confirmedGroupName: "OTHER-ALL" },
        { fid: 501, confirmedGroupName: null },
      ],
    });
    expect(detail.fixtureNumbers).toEqual([301, 302]);
  });

  it("소속 확인된 장비가 하나도 없으면 미확인이다(추정 금지)", () => {
    const detail = buildGlanceRowDetail({
      track: TRACK,
      startBar: 11,
      endBar: 14,
      secondsPerBar: 2,
      fixtures: [{ fid: 301, confirmedGroupName: null }],
    });
    expect(detail.fixtureNumbers).toBe(GLANCE_DETAIL_UNKNOWN);
  });

  it("Seq/Cue 번호는 클라이언트에 없는 데이터라 항상 미확인이다", () => {
    const detail = buildGlanceRowDetail({ track: TRACK, startBar: 0, endBar: 4, secondsPerBar: 2, fixtures: [] });
    expect(detail.seqCue).toBe(GLANCE_DETAIL_UNKNOWN);
  });

  it("콘솔 명령은 서버(emit.py) 소관이라 항상 미확인이다", () => {
    const detail = buildGlanceRowDetail({ track: TRACK, startBar: 0, endBar: 4, secondsPerBar: 2, fixtures: [] });
    expect(detail.consoleCommand).toBe(GLANCE_DETAIL_UNKNOWN);
  });

  it("마디 범위는 배타적 endBar를 포함 표기로 바꾼다", () => {
    const detail = buildGlanceRowDetail({ track: TRACK, startBar: 11, endBar: 14, secondsPerBar: 2, fixtures: [] });
    expect(detail.barRangeLabel).toBe("11~13마디");
    expect(detail.lengthBars).toBe(3);
  });

  it("secondsPerBar가 있으면 타임코드를 환산한다", () => {
    const detail = buildGlanceRowDetail({ track: TRACK, startBar: 11, endBar: 14, secondsPerBar: 2, fixtures: [] });
    // 11마디 * 2초/마디 = 22초 = "00:22.0"
    expect(detail.timecodeLabel).toBe("00:22.0");
  });

  it("secondsPerBar가 없으면(BPM 미확정) 타임코드도 미확인이다 — 환산을 지어내지 않는다", () => {
    const detail = buildGlanceRowDetail({ track: TRACK, startBar: 11, endBar: 14, secondsPerBar: null, fixtures: [] });
    expect(detail.timecodeLabel).toBe(GLANCE_DETAIL_UNKNOWN);
  });
});
