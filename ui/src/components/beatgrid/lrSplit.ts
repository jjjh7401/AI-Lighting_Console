// 타임라인 자식 줄 — "이 구간 L·R 따로" 선언 / "다시 합치기"
// (REQ-LDBEAT-019(c), AC-LDBEAT-019(c)). SPEC-LDBEAT-001 M9, 카드 t560
// 후속(리드 결정 2026-10-11, 근본 원인 정정).
//
// 리드 결정 — 이름 규칙("<BASE>-ALL" 꼴이면 "-L/-R" 자식 유도)은 테스트
// 리그 한 곡의 그룹 이름 관례를 앱 코드에 박아 넣은 것이었다(다른 장비·
// 다른 디자인에서는 그룹 이름이 그 꼴이 아닐 수 있다, feedback-generalize
// -beyond-test-rig) — 폐기한다. 분리 가능 여부는 이제 **실측 데이터**로만
// 판정한다: 그 콘솔 그룹에 소속 확인된(SELECTIONDATA) 장비가 무대 좌우
// 양쪽에 각각 1대 이상 있을 때만 분리 가능하다. 장비 패치가 없으면
// (fixtures 전체가 비거나 한쪽에만 있으면) 분리 불가 — 지어내지 않는다.
//
// §Gaps(카드 t560 보고, 이어서 유효) — 이 콘솔 그룹의 실제 L/R 자식 장비
// 패치(소속 fid 목록·그룹 번호)는 콘솔 SELECTIONDATA를 더 읽어야 아는
// 값이고, 이 카드 범위에서는 그 읽기 경로가 없다. 그래서 여기서 유도하는
// 것은 "표시용 자식 그룹 **이름**"("<group_name> L"/"<group_name> R",
// 접두사·접미사 치환 없이 그대로 이어붙인다)과 "선언된 마디 구간"·
// "좌우 실측 대수"뿐이다 — 장비 번호·그룹 번호는 만들어내지 않는다
// (지어내지 않는다, REQ-LDBEAT-015(f)와 같은 원칙). 선언 자체도 로컬 UI
// 상태일 뿐 서버에 저장하지 않는다(mockup 자신의 `SPLIT` 전역도 세션
// state — 이 카드는 그 동작을 그대로 옮긴다).
//
// 주의(미확인) — "x 값이 작을수록 왼쪽(L)"은 방향 가정이다(`BeatGrid.tsx`
// `projectFixture`의 Y축 주석과 같은 성격 — "위에서 본 그림" 관례이지만
// 좌우 방향 자체는 콘솔 실측으로 아직 확인하지 않았다).
export interface LRSplitFixture {
  x: number;
  confirmedGroupName?: string | null;
}

export interface LRSplitEligibleTrack {
  layer_role: string | null;
  group_name: string;
}

/** 무대 가로 중심 — fixtures 전체의 x 최소·최대 중간점. `BeatGrid.tsx`
 * `computeStageBounds`의 minX/maxX와 같은 정의다 — 모듈 순환 참조를
 * 피하려고 이 두 줄만 이 파일에 복제한다(로직 1줄, 분기 없음 — 두 자리가
 * 어긋날 위험이 실질적으로 없다). fixtures가 없으면 `null`(지어내지
 * 않음). */
function stageCentreX(fixtures: readonly LRSplitFixture[]): number | null {
  if (fixtures.length === 0) return null;
  const xs = fixtures.map((f) => f.x);
  return (Math.min(...xs) + Math.max(...xs)) / 2;
}

export interface LRSplitEligibility {
  splittable: boolean;
  leftCount: number;
  rightCount: number;
}

/** 이 콘솔 그룹의 분리 가능 여부 + 좌우 실측 대수. `fixture.confirmedGroupName`
 * 이 `track.group_name`과 **정확히** 일치하는 것만 센다 — 이름이 비슷해
 * 보인다는 추론(접두 매칭)은 쓰지 않는다(`BeatGrid.tsx` `fixtureDisplayColor`
 * 와 같은 원칙). 중앙(x === 중심)에 정확히 있는 장비는 어느 쪽도 아니다. */
export function computeLRSplitEligibility(
  track: { group_name: string },
  fixtures: readonly LRSplitFixture[],
): LRSplitEligibility {
  const centre = stageCentreX(fixtures);
  if (centre === null) return { splittable: false, leftCount: 0, rightCount: 0 };
  let leftCount = 0;
  let rightCount = 0;
  for (const fixture of fixtures) {
    if (fixture.confirmedGroupName !== track.group_name) continue;
    if (fixture.x < centre) leftCount++;
    else if (fixture.x > centre) rightCount++;
    // x === centre 는 어느 쪽도 아니다(명세 그대로, 지어내지 않음).
  }
  return { splittable: leftCount > 0 && rightCount > 0, leftCount, rightCount };
}

/** 이 트랙이 "이 구간 L·R 따로"를 선언할 수 있는가 — 층 역할이
 * 옆빛(side)이고(REQ-LDBEAT-021(b) "옆빛 L·R" 전용 필드와 같은 범위)
 * 실측 장비가 무대 좌우 양쪽에 있을 때만(`computeLRSplitEligibility`). */
export function canDeclareLRSplit(
  track: LRSplitEligibleTrack,
  fixtures: readonly LRSplitFixture[],
): boolean {
  if (track.layer_role !== "side") return false;
  return computeLRSplitEligibility(track, fixtures).splittable;
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
  /** 그 쪽(좌/우)에 소속 확인된 장비 대수 — 실측값, 지어내지 않음. */
  memberCount: number;
  startBar: number;
  endBar: number;
}

/** 이 트랙의 자식 줄 — 선언이 없으면(AC-LDBEAT-019(c) "분리 선언 전에는
 * 0개") 빈 배열. 분리 불가 트랙(옆빛이 아니거나 좌우 실측이 없음)이면
 * 선언이 남아 있어도 0개로 떨어진다(지어낸 자식 줄 0건). 라벨은
 * `"<group_name> L"`/`"<group_name> R"` — 접두·접미 치환 없이 그룹 이름을
 * 그대로 이어붙인다(특정 그룹 이름 리터럴을 구현에 두지 않는다). */
export function lrChildRowsForTrack(
  track: LRSplitEligibleTrack,
  declarations: LRSplitDeclarations,
  fixtures: readonly LRSplitFixture[],
): LRChildRow[] {
  if (!canDeclareLRSplit(track, fixtures)) return [];
  const range = declarations.get(track.group_name);
  if (!range) return [];
  const { leftCount, rightCount } = computeLRSplitEligibility(track, fixtures);
  return [
    { side: "L", label: `${track.group_name} L`, memberCount: leftCount, startBar: range.startBar, endBar: range.endBar },
    { side: "R", label: `${track.group_name} R`, memberCount: rightCount, startBar: range.startBar, endBar: range.endBar },
  ];
}
