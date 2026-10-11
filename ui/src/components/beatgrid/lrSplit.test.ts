// REQ-LDBEAT-019(c) — 타임라인 자식 줄("이 구간 L·R 따로"/"다시 합치기")
// 순수 함수 시험. SPEC-LDBEAT-001 M9 step 2, 카드 t560 후속(리드 결정
// 2026-10-11, 근본 원인 정정) → 카드 t568(같은 REQ, 근본 원인 재정정 —
// 부모 그룹은 `confirmedGroupName` 정확 일치로 영원히 못 맞았다).
//
// 이 시험은 이제 `beat_grid_stage` 응답 모양(그룹별 `member_fids`+
// `complete`)을 직접 조립해서 넘긴다(`LRSplitStage`) — 장비 하나당
// "확인된 소속 이름" 필드는 더 이상 쓰지 않는다. 아래는 일반 이름
// ("FOOBAR")으로 — 어떤 그룹 이름 리터럴도 구현에 박히지 않았음을 보인다
// (§마지막 describe).
import { describe, expect, it } from "vitest";

import {
  canDeclareLRSplit,
  clearLRSplit,
  computeLRSplitEligibility,
  declareLRSplit,
  lrChildRowsForTrack,
  type LRSplitDeclarations,
  type LRSplitStage,
} from "./lrSplit";

describe("computeLRSplitEligibility", () => {
  it("fixtures 가 없으면(빈 배열) 분리 불가다", () => {
    const stage: LRSplitStage = {
      fixtures: [],
      groups: [{ group_name: "FOOBAR", member_fids: [1, 2], complete: true }],
    };
    expect(computeLRSplitEligibility({ group_name: "FOOBAR" }, stage)).toEqual({
      splittable: false,
      leftCount: 0,
      rightCount: 0,
    });
  });

  it("트랙 이름과 같은 그룹이 groups 에 없으면 분리 불가다(이름 추정 없음)", () => {
    const stage: LRSplitStage = {
      fixtures: [
        { fid: 1, x: 0 },
        { fid: 2, x: 10 },
      ],
      groups: [{ group_name: "OTHER", member_fids: [1, 2], complete: true }],
    };
    expect(computeLRSplitEligibility({ group_name: "FOOBAR" }, stage)).toEqual({
      splittable: false,
      leftCount: 0,
      rightCount: 0,
    });
  });

  it("그룹 소속 장비가 한쪽에만 있으면 분리 불가다", () => {
    // 무대 중심은 (0+10)/2=5. 그룹 소속(fid 1,2)이 둘 다 왼쪽(x<5)뿐이다.
    const stage: LRSplitStage = {
      fixtures: [
        { fid: 1, x: 0 },
        { fid: 2, x: 1 },
        { fid: 3, x: 10 }, // 경계를 만들 뿐, 이 그룹 소속(member_fids) 아님
      ],
      groups: [{ group_name: "FOOBAR", member_fids: [1, 2], complete: true }],
    };
    expect(computeLRSplitEligibility({ group_name: "FOOBAR" }, stage)).toEqual({
      splittable: false,
      leftCount: 2,
      rightCount: 0,
    });
  });

  it("그룹 소속 장비가 좌우 양쪽에 있으면 분리 가능하고 대수가 맞다", () => {
    const stage: LRSplitStage = {
      fixtures: [
        { fid: 1, x: 0 },
        { fid: 2, x: 2 },
        { fid: 3, x: 8 },
        { fid: 4, x: 10 },
      ],
      groups: [{ group_name: "FOOBAR", member_fids: [1, 2, 3], complete: true }],
    };
    // 중심 = (0+10)/2 = 5(fixtures 전체 경계, fid 4 포함). x=0,2 는
    // 왼쪽(2대), x=8 은 오른쪽(1대). fid 4(소속 아님)는 안 센다.
    expect(computeLRSplitEligibility({ group_name: "FOOBAR" }, stage)).toEqual({
      splittable: true,
      leftCount: 2,
      rightCount: 1,
    });
  });

  it("부모 그룹(member_fids 가 자식 그룹들의 합집합)도 그 자체 소속만으로 분리된다 — 카드 t568 핵심", () => {
    // 콘솔엔 SIDE-ALL(부모) ⊇ SIDE-L ∪ SIDE-R 같은 구조가 있을 수 있지만,
    // `groups` 응답은 트랙 이름과 정확히 같은 그룹만 담는다(t565) — 여기
    // 트랙은 "SIDE-ALL"이므로 그 그룹의 member_fids 를 직접 쓴다. 장비의
    // confirmedGroupName(자식 그룹 이름)은 이 판정에 전혀 등장하지 않는다.
    const stage: LRSplitStage = {
      fixtures: [
        { fid: 11, x: 0 }, // SIDE-L 소속(과거엔 confirmedGroupName="SIDE-L")
        { fid: 12, x: 1 },
        { fid: 21, x: 9 }, // SIDE-R 소속(과거엔 confirmedGroupName="SIDE-R")
        { fid: 22, x: 10 },
      ],
      groups: [{ group_name: "SIDE-ALL", member_fids: [11, 12, 21, 22], complete: true }],
    };
    expect(computeLRSplitEligibility({ group_name: "SIDE-ALL" }, stage)).toEqual({
      splittable: true,
      leftCount: 2,
      rightCount: 2,
    });
  });

  it("그 그룹이 complete=false 면(일부만 읽힘) 분리 불가다 — 부분 데이터를 지어내지 않는다", () => {
    const stage: LRSplitStage = {
      fixtures: [
        { fid: 1, x: 0 },
        { fid: 2, x: 10 },
      ],
      groups: [{ group_name: "FOOBAR", member_fids: [1, 2], complete: false }],
    };
    expect(computeLRSplitEligibility({ group_name: "FOOBAR" }, stage)).toEqual({
      splittable: false,
      leftCount: 0,
      rightCount: 0,
    });
  });

  it("무대 중심에 정확히 있는 장비는 어느 쪽도 아니다", () => {
    const stage: LRSplitStage = {
      fixtures: [
        { fid: 1, x: 0 },
        { fid: 2, x: 10 },
        { fid: 3, x: 5 }, // 중심(5) 정확히 — 양쪽 다 아님
      ],
      groups: [{ group_name: "FOOBAR", member_fids: [1, 2, 3], complete: true }],
    };
    expect(computeLRSplitEligibility({ group_name: "FOOBAR" }, stage)).toEqual({
      splittable: true,
      leftCount: 1,
      rightCount: 1,
    });
  });

  it("member_fids 에 있는 fid 가 fixtures 목록에 없으면 세지 않는다(지어내지 않음)", () => {
    const stage: LRSplitStage = {
      fixtures: [{ fid: 1, x: 10 }],
      groups: [{ group_name: "FOOBAR", member_fids: [1, 999], complete: true }],
    };
    // 중심 = (10+10)/2 = 10(fixtures 가 한 대뿐). fid 1 은 x===중심이라
    // 어느 쪽도 아니고, fid 999 는 fixtures 에 없어 무시된다 → 분리 불가.
    expect(computeLRSplitEligibility({ group_name: "FOOBAR" }, stage)).toEqual({
      splittable: false,
      leftCount: 0,
      rightCount: 0,
    });
  });
});

describe("canDeclareLRSplit", () => {
  const bothSidesStage: LRSplitStage = {
    fixtures: [
      { fid: 1, x: 0 },
      { fid: 2, x: 10 },
    ],
    groups: [{ group_name: "FOOBAR", member_fids: [1, 2], complete: true }],
  };

  it("옆빛(side) 역할 + 좌우 양쪽 실측이면 선언 가능", () => {
    expect(canDeclareLRSplit({ layer_role: "side", group_name: "FOOBAR" }, bothSidesStage)).toBe(true);
  });

  it("역할이 옆빛이 아니면 불가(일반화 범위 — REQ-LDBEAT-021(b) 옆빛 L·R 전용)", () => {
    expect(canDeclareLRSplit({ layer_role: "mover", group_name: "FOOBAR" }, bothSidesStage)).toBe(false);
  });

  it("역할이 옆빛이어도 fixtures 가 없으면(분리 가능 데이터 없음) 불가", () => {
    const empty: LRSplitStage = { fixtures: [], groups: bothSidesStage.groups };
    expect(canDeclareLRSplit({ layer_role: "side", group_name: "FOOBAR" }, empty)).toBe(false);
  });

  it("역할이 옆빛이어도 그 그룹이 없으면 불가", () => {
    const noGroup: LRSplitStage = { fixtures: bothSidesStage.fixtures, groups: [] };
    expect(canDeclareLRSplit({ layer_role: "side", group_name: "FOOBAR" }, noGroup)).toBe(false);
  });

  it("역할이 옆빛이어도 complete=false 면 불가", () => {
    const incomplete: LRSplitStage = {
      fixtures: bothSidesStage.fixtures,
      groups: [{ group_name: "FOOBAR", member_fids: [1, 2], complete: false }],
    };
    expect(canDeclareLRSplit({ layer_role: "side", group_name: "FOOBAR" }, incomplete)).toBe(false);
  });

  it("역할이 옆빛이어도 한쪽에만 있으면 불가", () => {
    const oneSideOnly: LRSplitStage = {
      fixtures: [
        { fid: 1, x: 0 },
        { fid: 2, x: 10 },
      ],
      groups: [{ group_name: "FOOBAR", member_fids: [1], complete: true }],
    };
    expect(canDeclareLRSplit({ layer_role: "side", group_name: "FOOBAR" }, oneSideOnly)).toBe(false);
  });

  it("역할이 없으면(null) 불가", () => {
    expect(canDeclareLRSplit({ layer_role: null, group_name: "FOOBAR" }, bothSidesStage)).toBe(false);
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
  const bothSidesStage: LRSplitStage = {
    fixtures: [
      { fid: 1, x: 0 },
      { fid: 2, x: 2 },
      { fid: 3, x: 8 },
    ],
    groups: [{ group_name: "FOOBAR", member_fids: [1, 2, 3], complete: true }],
  };

  it("선언 전에는 자식 줄이 0개다(AC-LDBEAT-019(c))", () => {
    const declarations: LRSplitDeclarations = new Map();
    expect(lrChildRowsForTrack(track, declarations, bothSidesStage)).toEqual([]);
  });

  it("선언 후에는 L·R 두 줄이 생기고, 그룹 이름을 그대로 쓴 라벨(L·R 접미사뿐 — 특정 리터럴 없음)과 실측 대수를 담는다", () => {
    const declarations = declareLRSplit(new Map(), "FOOBAR", { startBar: 11, endBar: 14 });
    const rows = lrChildRowsForTrack(track, declarations, bothSidesStage);
    expect(rows).toHaveLength(2);
    // 중심 = (0+8)/2 = 4. x=0,2 왼쪽(2대) · x=8 오른쪽(1대).
    expect(rows[0]).toEqual({ side: "L", label: "FOOBAR L", memberCount: 2, startBar: 11, endBar: 14 });
    expect(rows[1]).toEqual({ side: "R", label: "FOOBAR R", memberCount: 1, startBar: 11, endBar: 14 });
  });

  it("합친 뒤에는 다시 0개다", () => {
    const declared = declareLRSplit(new Map(), "FOOBAR", { startBar: 11, endBar: 14 });
    const cleared = clearLRSplit(declared, "FOOBAR");
    expect(lrChildRowsForTrack(track, cleared, bothSidesStage)).toEqual([]);
  });

  it("선언이 있어도 그 트랙이 분리 불가(canDeclareLRSplit=false)면 0개다", () => {
    const nonSide = { layer_role: "mover", group_name: "MOVER" };
    const declarations = declareLRSplit(new Map(), "MOVER", { startBar: 0, endBar: 4 });
    expect(lrChildRowsForTrack(nonSide, declarations, bothSidesStage)).toEqual([]);
  });

  it("선언이 있어도 좌우 실측이 없으면(fixtures 변화) 0개다", () => {
    const declarations = declareLRSplit(new Map(), "FOOBAR", { startBar: 11, endBar: 14 });
    const empty: LRSplitStage = { fixtures: [], groups: bothSidesStage.groups };
    expect(lrChildRowsForTrack(track, declarations, empty)).toEqual([]);
  });

  it("선언이 있어도 그 그룹이 complete=false 면 0개다", () => {
    const declarations = declareLRSplit(new Map(), "FOOBAR", { startBar: 11, endBar: 14 });
    const incomplete: LRSplitStage = {
      fixtures: bothSidesStage.fixtures,
      groups: [{ group_name: "FOOBAR", member_fids: [1, 2, 3], complete: false }],
    };
    expect(lrChildRowsForTrack(track, declarations, incomplete)).toEqual([]);
  });

  it("다른 트랙의 선언은 섞이지 않는다", () => {
    const other = { layer_role: "side", group_name: "OTHER" };
    const declarations = declareLRSplit(new Map(), "FOOBAR", { startBar: 11, endBar: 14 });
    expect(lrChildRowsForTrack(other, declarations, bothSidesStage)).toEqual([]);
  });
});

// L·R 방향 — 카드 t568, 두 출처 인용(둘 다 "작은 x = 왼쪽(house, 한국어
// '왼쪽')"로 일치하므로 더 이상 미확인 가정이 아니다):
//
// 출처 1 — MA3 공식 좌표 규약(`.moai/specs/SPEC-COPILOT-SPATIAL-001/
// design.md:67-71`, `spec.md:164-165,170`): "+x = stage left"(배우
// 기준, *"Stage right will be negative numbers"*)이고 stage left/right
// (배우 기준)와 house left/right(객석 기준)는 정반대다 — 그러므로 house
// left(= 한국어 "왼쪽", 이 규약 자체가 "한국어 '왼쪽/오른쪽'도 house
// 기준"이라고 명시)는 음의 x, 즉 더 작은 x다.
//
// 출처 2 — 이 앱 자신의 2D 무대 투영(`BeatGrid.tsx` `projectFixture`):
// `cx = STAGE_MARGIN + ((point.x - bounds.minX) / bounds.spanX) * usableW`
// — x가 커질수록 화면 좌표 cx도 커진다(SVG 관례, cx 작을수록 화면
// 왼쪽). 그러므로 작은 x는 이미 화면 왼쪽에 그려진다.
//
// 두 출처가 똑같이 "작은 x = 왼쪽"을 가리키므로 `computeLRSplitEligibility`
// 의 `fixture.x < centre` → leftCount 규칙은 검증된 규칙이다.
describe("L·R 방향(실측 확정 — 두 출처 인용, 카드 t568)", () => {
  it("더 작은 x 쪽이 L(출처1 MA3 house 좌표 규약 + 출처2 BeatGrid.tsx projectFixture 둘 다 일치)", () => {
    const stage: LRSplitStage = {
      fixtures: [
        { fid: 1, x: -5 }, // 더 작은 x → house left(한국어 "왼쪽") → L
        { fid: 2, x: 5 }, // 더 큰 x → house right(한국어 "오른쪽") → R
      ],
      groups: [{ group_name: "FOOBAR", member_fids: [1, 2], complete: true }],
    };
    const result = computeLRSplitEligibility({ group_name: "FOOBAR" }, stage);
    expect(result).toEqual({ splittable: true, leftCount: 1, rightCount: 1 });
  });
});

describe("그룹 이름 리터럴 없음(일반화 — feedback-generalize-beyond-test-rig)", () => {
  it("실제 제품 그룹 이름(SIDE-ALL 등)을 쓰지 않아도 완전히 같은 방식으로 동작한다", () => {
    const track = { layer_role: "side", group_name: "ZZZ-NOT-A-REAL-SONG-GROUP" };
    const stage: LRSplitStage = {
      fixtures: [
        { fid: 1, x: 0 },
        { fid: 2, x: 10 },
      ],
      groups: [{ group_name: "ZZZ-NOT-A-REAL-SONG-GROUP", member_fids: [1, 2], complete: true }],
    };
    expect(canDeclareLRSplit(track, stage)).toBe(true);
    const declarations = declareLRSplit(new Map(), track.group_name, { startBar: 0, endBar: 4 });
    const rows = lrChildRowsForTrack(track, declarations, stage);
    expect(rows.map((r) => r.label)).toEqual([
      "ZZZ-NOT-A-REAL-SONG-GROUP L",
      "ZZZ-NOT-A-REAL-SONG-GROUP R",
    ]);
  });
});
