// REQ-LDBEAT-019(c) — 타임라인 자식 줄("이 구간 L·R 따로"/"다시 합치기")
// 순수 함수 시험. SPEC-LDBEAT-001 M9 step 2, 카드 t560.
//
// 데이터 경계(§Gaps, 카드 t560 보고): 이 콘솔 그룹의 실제 L/R 자식 장비
// 패치(소속 fid 목록)는 클라이언트에 없다(콘솔 SELECTIONDATA 읽기 범위
// 밖) — 그래서 여기서 유도하는 것은 "표시용 자식 그룹 이름"과 "선언된
// 마디 구간"뿐이고, 장비 번호·그룹 번호는 만들어내지 않는다.
import { describe, expect, it } from "vitest";

import {
  canDeclareLRSplit,
  clearLRSplit,
  declareLRSplit,
  deriveLRChildNames,
  lrChildRowsForTrack,
  type LRSplitDeclarations,
} from "./lrSplit";

describe("deriveLRChildNames", () => {
  it("<BASE>-ALL 꼴이면 <BASE>-L / <BASE>-R 을 유도한다 (일반화 — 특정 그룹 이름 하드코딩 없음)", () => {
    expect(deriveLRChildNames("FOOBAR-ALL")).toEqual({ left: "FOOBAR-L", right: "FOOBAR-R" });
  });

  it("대소문자를 가리지 않고 접미사를 인식한다", () => {
    expect(deriveLRChildNames("wash-all")).toEqual({ left: "wash-L", right: "wash-R" });
  });

  it("-ALL 접미사가 없으면 null(지어내지 않음)", () => {
    expect(deriveLRChildNames("MOVER-U")).toBeNull();
    expect(deriveLRChildNames("BACK")).toBeNull();
  });
});

describe("canDeclareLRSplit", () => {
  it("옆빛(side) 역할 + -ALL 그룹이면 선언 가능", () => {
    expect(canDeclareLRSplit({ layer_role: "side", group_name: "FOOBAR-ALL" })).toBe(true);
  });

  it("역할이 옆빛이 아니면 불가(일반화 범위 — REQ-LDBEAT-021(b) 옆빛 L·R 전용)", () => {
    expect(canDeclareLRSplit({ layer_role: "mover", group_name: "MOVER-ALL" })).toBe(false);
  });

  it("-ALL 꼴이 아니면 역할이 옆빛이어도 불가", () => {
    expect(canDeclareLRSplit({ layer_role: "side", group_name: "SIDE-SOLO" })).toBe(false);
  });

  it("역할이 없으면(null) 불가", () => {
    expect(canDeclareLRSplit({ layer_role: null, group_name: "FOOBAR-ALL" })).toBe(false);
  });
});

describe("declareLRSplit / clearLRSplit", () => {
  it("선언하면 그 그룹 키로 구간이 들어간다", () => {
    const empty: LRSplitDeclarations = new Map();
    const next = declareLRSplit(empty, "FOOBAR-ALL", { startBar: 11, endBar: 14 });
    expect(next.get("FOOBAR-ALL")).toEqual({ startBar: 11, endBar: 14 });
  });

  it("다시 선언하면 이전 구간을 덮어쓴다(한 트랙에 하나)", () => {
    const first = declareLRSplit(new Map(), "FOOBAR-ALL", { startBar: 11, endBar: 14 });
    const second = declareLRSplit(first, "FOOBAR-ALL", { startBar: 18, endBar: 22 });
    expect(second.get("FOOBAR-ALL")).toEqual({ startBar: 18, endBar: 22 });
  });

  it("합치면 그 그룹 키가 사라진다", () => {
    const declared = declareLRSplit(new Map(), "FOOBAR-ALL", { startBar: 11, endBar: 14 });
    const cleared = clearLRSplit(declared, "FOOBAR-ALL");
    expect(cleared.has("FOOBAR-ALL")).toBe(false);
  });

  it("선언 없는 키를 합쳐도 에러 없이 그대로다", () => {
    const empty: LRSplitDeclarations = new Map();
    expect(clearLRSplit(empty, "FOOBAR-ALL")).toBe(empty);
  });

  it("원본 Map을 변형하지 않는다(불변)", () => {
    const empty: LRSplitDeclarations = new Map();
    declareLRSplit(empty, "FOOBAR-ALL", { startBar: 11, endBar: 14 });
    expect(empty.size).toBe(0);
  });
});

describe("lrChildRowsForTrack", () => {
  const track = { layer_role: "side", group_name: "FOOBAR-ALL" };

  it("선언 전에는 자식 줄이 0개다(AC-LDBEAT-019(c))", () => {
    const declarations: LRSplitDeclarations = new Map();
    expect(lrChildRowsForTrack(track, declarations)).toEqual([]);
  });

  it("선언 후에는 L·R 두 줄이 생긴다", () => {
    const declarations = declareLRSplit(new Map(), "FOOBAR-ALL", { startBar: 11, endBar: 14 });
    const rows = lrChildRowsForTrack(track, declarations);
    expect(rows).toHaveLength(2);
    expect(rows[0]).toEqual({ side: "L", label: "FOOBAR-L", startBar: 11, endBar: 14 });
    expect(rows[1]).toEqual({ side: "R", label: "FOOBAR-R", startBar: 11, endBar: 14 });
  });

  it("합친 뒤에는 다시 0개다", () => {
    const declared = declareLRSplit(new Map(), "FOOBAR-ALL", { startBar: 11, endBar: 14 });
    const cleared = clearLRSplit(declared, "FOOBAR-ALL");
    expect(lrChildRowsForTrack(track, cleared)).toEqual([]);
  });

  it("선언이 있어도 그 트랙이 분리 불가(canDeclareLRSplit=false)면 0개다", () => {
    const nonSide = { layer_role: "mover", group_name: "MOVER-ALL" };
    const declarations = declareLRSplit(new Map(), "MOVER-ALL", { startBar: 0, endBar: 4 });
    expect(lrChildRowsForTrack(nonSide, declarations)).toEqual([]);
  });

  it("다른 트랙의 선언은 섞이지 않는다", () => {
    const other = { layer_role: "side", group_name: "OTHER-ALL" };
    const declarations = declareLRSplit(new Map(), "FOOBAR-ALL", { startBar: 11, endBar: 14 });
    expect(lrChildRowsForTrack(other, declarations)).toEqual([]);
  });
});
