// REQ-LDBEAT-019(c) — 타임라인 자식 줄("이 구간 L·R 따로"/"다시 합치기")
// 순수 함수 시험. SPEC-LDBEAT-001 M9 step 2, 카드 t560 후속(리드 결정
// 2026-10-11, 근본 원인 정정).
//
// 리드 결정: 이름 규칙("<BASE>-ALL" → "-L/-R")은 테스트 리그 한 곡의
// 그룹 이름 관례에 앱을 묶는 하드코딩이다(feedback-generalize-beyond
// -test-rig) — 폐기한다. 분리 가능 여부는 이제 실측 데이터(그 콘솔 그룹에
// 소속 확인된 장비가 무대 좌우 양쪽에 있는가)로만 판정한다. 아래 시험은
// 일반 이름("FOOBAR")으로 — 어떤 그룹 이름 리터럴도 구현에 박히지 않았음을
// 보인다(§마지막 describe).
import { describe, expect, it } from "vitest";

import {
  canDeclareLRSplit,
  clearLRSplit,
  computeLRSplitEligibility,
  declareLRSplit,
  lrChildRowsForTrack,
  type LRSplitDeclarations,
} from "./lrSplit";

describe("computeLRSplitEligibility", () => {
  it("fixtures 가 없으면(빈 배열) 분리 불가다", () => {
    expect(computeLRSplitEligibility({ group_name: "FOOBAR" }, [])).toEqual({
      splittable: false,
      leftCount: 0,
      rightCount: 0,
    });
  });

  it("소속 확인된 장비가 한쪽에만 있으면 분리 불가다", () => {
    // 무대 중심은 (0+10)/2=5. 셋 다 왼쪽(x<5)뿐이다.
    const fixtures = [
      { x: 0, confirmedGroupName: "FOOBAR" },
      { x: 1, confirmedGroupName: "FOOBAR" },
      { x: 10, confirmedGroupName: "OTHER" }, // 경계를 만들 뿐, FOOBAR 소속 아님
    ];
    expect(computeLRSplitEligibility({ group_name: "FOOBAR" }, fixtures)).toEqual({
      splittable: false,
      leftCount: 2,
      rightCount: 0,
    });
  });

  it("소속 확인된 장비가 좌우 양쪽에 있으면 분리 가능하고 대수가 맞다", () => {
    const fixtures = [
      { x: 0, confirmedGroupName: "FOOBAR" },
      { x: 2, confirmedGroupName: "FOOBAR" },
      { x: 8, confirmedGroupName: "FOOBAR" },
      { x: 10, confirmedGroupName: "OTHER" },
    ];
    // 중심 = (0+10)/2 = 5. x=0,2 는 왼쪽(2대), x=8 은 오른쪽(1대).
    expect(computeLRSplitEligibility({ group_name: "FOOBAR" }, fixtures)).toEqual({
      splittable: true,
      leftCount: 2,
      rightCount: 1,
    });
  });

  it("다른 그룹 소속 장비는 세지 않는다(이름 추정 없음)", () => {
    const fixtures = [
      { x: 0, confirmedGroupName: "OTHER" },
      { x: 10, confirmedGroupName: "OTHER" },
    ];
    expect(computeLRSplitEligibility({ group_name: "FOOBAR" }, fixtures)).toEqual({
      splittable: false,
      leftCount: 0,
      rightCount: 0,
    });
  });

  it("무대 중심에 정확히 있는 장비는 어느 쪽도 아니다", () => {
    const fixtures = [
      { x: 0, confirmedGroupName: "FOOBAR" },
      { x: 10, confirmedGroupName: "FOOBAR" },
      { x: 5, confirmedGroupName: "FOOBAR" }, // 중심(5) 정확히 — 양쪽 다 아님
    ];
    expect(computeLRSplitEligibility({ group_name: "FOOBAR" }, fixtures)).toEqual({
      splittable: true,
      leftCount: 1,
      rightCount: 1,
    });
  });

  it("confirmedGroupName 이 없는(null) 장비도 무대 경계(중심) 계산엔 들어가지만 소속 집계엔 안 들어간다", () => {
    // 중심 = (0+10)/2 = 5. x=0 장비는 소속 미확인(null)이라 집계에서
    // 빠지지만 경계(min=0)에는 기여한다 — 그 결과 FOOBAR(x=10)는
    // 오른쪽(1대)뿐이라 한쪽뿐 → 분리 불가.
    const fixtures = [
      { x: 0, confirmedGroupName: null },
      { x: 10, confirmedGroupName: "FOOBAR" },
    ];
    expect(computeLRSplitEligibility({ group_name: "FOOBAR" }, fixtures)).toEqual({
      splittable: false,
      leftCount: 0,
      rightCount: 1,
    });
  });
});

describe("canDeclareLRSplit", () => {
  const bothSides = [
    { x: 0, confirmedGroupName: "FOOBAR" },
    { x: 10, confirmedGroupName: "FOOBAR" },
  ];

  it("옆빛(side) 역할 + 좌우 양쪽 실측이면 선언 가능", () => {
    expect(canDeclareLRSplit({ layer_role: "side", group_name: "FOOBAR" }, bothSides)).toBe(true);
  });

  it("역할이 옆빛이 아니면 불가(일반화 범위 — REQ-LDBEAT-021(b) 옆빛 L·R 전용)", () => {
    expect(canDeclareLRSplit({ layer_role: "mover", group_name: "FOOBAR" }, bothSides)).toBe(false);
  });

  it("역할이 옆빛이어도 fixtures 가 없으면(분리 가능 데이터 없음) 불가", () => {
    expect(canDeclareLRSplit({ layer_role: "side", group_name: "FOOBAR" }, [])).toBe(false);
  });

  it("역할이 옆빛이어도 한쪽에만 있으면 불가", () => {
    const oneSideOnly = [
      { x: 0, confirmedGroupName: "FOOBAR" },
      { x: 10, confirmedGroupName: "OTHER" },
    ];
    expect(canDeclareLRSplit({ layer_role: "side", group_name: "FOOBAR" }, oneSideOnly)).toBe(false);
  });

  it("역할이 없으면(null) 불가", () => {
    expect(canDeclareLRSplit({ layer_role: null, group_name: "FOOBAR" }, bothSides)).toBe(false);
  });
});

describe("declareLRSplit / clearLRSplit", () => {
  it("선언하면 그 그룹 키로 구간이 들어간다", () => {
    const empty: LRSplitDeclarations = new Map();
    const next = declareLRSplit(empty, "FOOBAR", { startBar: 11, endBar: 14 });
    expect(next.get("FOOBAR")).toEqual({ startBar: 11, endBar: 14 });
  });

  it("다시 선언하면 이전 구간을 덮어쓴다(한 트랙에 하나)", () => {
    const first = declareLRSplit(new Map(), "FOOBAR", { startBar: 11, endBar: 14 });
    const second = declareLRSplit(first, "FOOBAR", { startBar: 18, endBar: 22 });
    expect(second.get("FOOBAR")).toEqual({ startBar: 18, endBar: 22 });
  });

  it("합치면 그 그룹 키가 사라진다", () => {
    const declared = declareLRSplit(new Map(), "FOOBAR", { startBar: 11, endBar: 14 });
    const cleared = clearLRSplit(declared, "FOOBAR");
    expect(cleared.has("FOOBAR")).toBe(false);
  });

  it("선언 없는 키를 합쳐도 에러 없이 그대로다", () => {
    const empty: LRSplitDeclarations = new Map();
    expect(clearLRSplit(empty, "FOOBAR")).toBe(empty);
  });

  it("원본 Map을 변형하지 않는다(불변)", () => {
    const empty: LRSplitDeclarations = new Map();
    declareLRSplit(empty, "FOOBAR", { startBar: 11, endBar: 14 });
    expect(empty.size).toBe(0);
  });
});

describe("lrChildRowsForTrack", () => {
  const track = { layer_role: "side", group_name: "FOOBAR" };
  const bothSides = [
    { x: 0, confirmedGroupName: "FOOBAR" },
    { x: 2, confirmedGroupName: "FOOBAR" },
    { x: 8, confirmedGroupName: "FOOBAR" },
  ];

  it("선언 전에는 자식 줄이 0개다(AC-LDBEAT-019(c))", () => {
    const declarations: LRSplitDeclarations = new Map();
    expect(lrChildRowsForTrack(track, declarations, bothSides)).toEqual([]);
  });

  it("선언 후에는 L·R 두 줄이 생기고, 그룹 이름을 그대로 쓴 라벨(L·R 접미사뿐 — 특정 리터럴 없음)과 실측 대수를 담는다", () => {
    const declarations = declareLRSplit(new Map(), "FOOBAR", { startBar: 11, endBar: 14 });
    const rows = lrChildRowsForTrack(track, declarations, bothSides);
    expect(rows).toHaveLength(2);
    // 중심 = (0+8)/2 = 4. x=0,2 왼쪽(2대) · x=8 오른쪽(1대).
    expect(rows[0]).toEqual({ side: "L", label: "FOOBAR L", memberCount: 2, startBar: 11, endBar: 14 });
    expect(rows[1]).toEqual({ side: "R", label: "FOOBAR R", memberCount: 1, startBar: 11, endBar: 14 });
  });

  it("합친 뒤에는 다시 0개다", () => {
    const declared = declareLRSplit(new Map(), "FOOBAR", { startBar: 11, endBar: 14 });
    const cleared = clearLRSplit(declared, "FOOBAR");
    expect(lrChildRowsForTrack(track, cleared, bothSides)).toEqual([]);
  });

  it("선언이 있어도 그 트랙이 분리 불가(canDeclareLRSplit=false)면 0개다", () => {
    const nonSide = { layer_role: "mover", group_name: "MOVER" };
    const declarations = declareLRSplit(new Map(), "MOVER", { startBar: 0, endBar: 4 });
    expect(lrChildRowsForTrack(nonSide, declarations, bothSides)).toEqual([]);
  });

  it("선언이 있어도 좌우 실측이 없으면(fixtures 변화) 0개다", () => {
    const declarations = declareLRSplit(new Map(), "FOOBAR", { startBar: 11, endBar: 14 });
    expect(lrChildRowsForTrack(track, declarations, [])).toEqual([]);
  });

  it("다른 트랙의 선언은 섞이지 않는다", () => {
    const other = { layer_role: "side", group_name: "OTHER" };
    const declarations = declareLRSplit(new Map(), "FOOBAR", { startBar: 11, endBar: 14 });
    expect(lrChildRowsForTrack(other, declarations, bothSides)).toEqual([]);
  });
});

describe("그룹 이름 리터럴 없음(일반화 — feedback-generalize-beyond-test-rig)", () => {
  it("실제 제품 그룹 이름(SIDE-ALL 등)을 쓰지 않아도 완전히 같은 방식으로 동작한다", () => {
    const track = { layer_role: "side", group_name: "ZZZ-NOT-A-REAL-SONG-GROUP" };
    const fixtures = [
      { x: 0, confirmedGroupName: "ZZZ-NOT-A-REAL-SONG-GROUP" },
      { x: 10, confirmedGroupName: "ZZZ-NOT-A-REAL-SONG-GROUP" },
    ];
    expect(canDeclareLRSplit(track, fixtures)).toBe(true);
    const declarations = declareLRSplit(new Map(), track.group_name, { startBar: 0, endBar: 4 });
    const rows = lrChildRowsForTrack(track, declarations, fixtures);
    expect(rows.map((r) => r.label)).toEqual([
      "ZZZ-NOT-A-REAL-SONG-GROUP L",
      "ZZZ-NOT-A-REAL-SONG-GROUP R",
    ]);
  });
});
