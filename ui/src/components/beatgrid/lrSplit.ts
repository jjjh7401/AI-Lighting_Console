// 타임라인 자식 줄 — "이 구간 L·R 따로" 선언 / "다시 합치기"
// (REQ-LDBEAT-019(c), AC-LDBEAT-019(c)). SPEC-LDBEAT-001 M9 step 2, 카드
// t560.
//
// §Gaps(카드 t560 보고) — 이 콘솔 그룹의 실제 L/R 자식 장비 패치(소속
// fid 목록·그룹 번호)는 콘솔 SELECTIONDATA를 더 읽어야 아는 값이고,
// 이 카드 범위에서는 그 읽기 경로가 없다. 그래서 여기서 유도하는 것은
// "표시용 자식 그룹 **이름**"과 "선언된 마디 구간"뿐이다 — 장비 번호·
// 그룹 번호는 만들어내지 않는다(지어내지 않는다, REQ-LDBEAT-015(f)와
// 같은 원칙). 선언 자체도 로컬 UI 상태일 뿐 서버에 저장하지 않는다
// (mockup 자신의 `SPLIT` 전역도 세션 state — 이 카드는 그 동작을 그대로
// 옮긴다).
export interface LRChildNames {
  left: string;
  right: string;
}

const PARENT_SUFFIX = /-ALL$/i;

/** `groupName`이 "<BASE>-ALL" 꼴일 때만 L/R 자식 이름을 유도한다 — 특정
 * 곡·특정 그룹 이름(예: "SIDE")을 하드코딩하지 않는다(일반화 원칙,
 * feedback-generalize-beyond-test-rig). `rig.py`의 부모·자식 그룹 접미사
 * 관례(SIDE-ALL/L/R 패밀리)와 같은 모양이다. 그 꼴이 아니면 `null`
 * (분리 불가로 본다 — 지어내지 않는다). */
export function deriveLRChildNames(groupName: string): LRChildNames | null {
  if (!PARENT_SUFFIX.test(groupName)) return null;
  const base = groupName.replace(PARENT_SUFFIX, "");
  return { left: `${base}-L`, right: `${base}-R` };
}

export interface LRSplitEligibleTrack {
  layer_role: string | null;
  group_name: string;
}

/** 이 트랙이 "이 구간 L·R 따로"를 선언할 수 있는가 — 층 역할이
 * 옆빛(side)이고(REQ-LDBEAT-021(b) "옆빛 L·R" 전용 필드와 같은 범위)
 * 그룹 이름이 L/R 자식을 유도할 수 있는 꼴일 때만. */
export function canDeclareLRSplit(track: LRSplitEligibleTrack): boolean {
  return track.layer_role === "side" && deriveLRChildNames(track.group_name) !== null;
}

export interface LRSplitRange {
  startBar: number;
  /** 배타적 — `trackCueSegments`의 `endBar`와 같은 관례. */
  endBar: number;
}

/** 트랙별(콘솔 그룹 이름 키) 선언. 한 트랙에 동시에 둘 이상의 구간을
 * 선언하지 않는다(mockup `SPLIT` 전역 하나와 같은 단순함 — "한 번에
 * 하나"). */
export type LRSplitDeclarations = ReadonlyMap<string, LRSplitRange>;

/** 선언 — 이미 선언이 있으면 덮어쓴다(새 구간으로 교체, 둘을 합치거나
 * 쌓지 않는다). 원본을 변형하지 않는다. */
export function declareLRSplit(
  declarations: LRSplitDeclarations,
  groupName: string,
  range: LRSplitRange,
): LRSplitDeclarations {
  const next = new Map(declarations);
  next.set(groupName, range);
  return next;
}

/** 합치기 — 그 그룹의 선언을 제거한다. 선언이 없으면 원본을 그대로
 * 돌려준다(불필요한 새 Map을 만들지 않는다). */
export function clearLRSplit(declarations: LRSplitDeclarations, groupName: string): LRSplitDeclarations {
  if (!declarations.has(groupName)) return declarations;
  const next = new Map(declarations);
  next.delete(groupName);
  return next;
}

export interface LRChildRow {
  side: "L" | "R";
  label: string;
  startBar: number;
  endBar: number;
}

/** 이 트랙의 자식 줄 — 선언이 없으면(AC-LDBEAT-019(c) "분리 선언 전에는
 * 0개") 빈 배열. 분리 불가 트랙(옆빛이 아니거나 -ALL 꼴이 아님)이면
 * 선언이 남아 있어도 0개로 떨어진다(지어낸 자식 줄 0건). */
export function lrChildRowsForTrack(
  track: LRSplitEligibleTrack,
  declarations: LRSplitDeclarations,
): LRChildRow[] {
  if (!canDeclareLRSplit(track)) return [];
  const range = declarations.get(track.group_name);
  if (!range) return [];
  const names = deriveLRChildNames(track.group_name);
  if (!names) return [];
  return [
    { side: "L", label: names.left, startBar: range.startBar, endBar: range.endBar },
    { side: "R", label: names.right, startBar: range.startBar, endBar: range.endBar },
  ];
}
