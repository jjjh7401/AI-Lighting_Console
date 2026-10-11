// 타임라인 자식 줄 — "이 구간 L·R 따로" 선언 / "다시 합치기"
// (REQ-LDBEAT-019(c), AC-LDBEAT-019(c)). SPEC-LDBEAT-001 M9, 카드 t560
// 후속(리드 결정 2026-10-11, 근본 원인 정정) → 카드 t568(같은 REQ) 후속.
//
// 리드 결정(2026-10-11, t560) — 이름 규칙("<BASE>-ALL" 꼴이면 "-L/-R" 자식
// 유도)은 테스트 리그 한 곡의 그룹 이름 관례를 앱 코드에 박아 넣은
// 것이었다(다른 장비·다른 디자인에서는 그룹 이름이 그 꼴이 아닐 수 있다,
// feedback-generalize-beyond-test-rig) — 폐기한다. 분리 가능 여부는 실측
// 데이터로만 판정한다.
//
// 카드 t568(같은 REQ 후속, 근본 원인 재정정) — t560 이 쓴
// `fixture.confirmedGroupName === track.group_name`(장비 한 대당 소속
// 이름 **한 개**짜리 필드의 정확 일치)은 그 콘솔 그룹이 부모 그룹(예:
// "SIDE-ALL")이면 영원히 못 맞는다: `beat_grid_stage` 판독(카드 t565)이
// 장비별로 채우는 소속은 **자식** 그룹 이름뿐이라서 부모 그룹 이름과는
// 글자 자체가 다르다 — 그래서 L·R 토글이 한 번도 뜨지 않았다(t560 보고
// "지금 데이터로는 버튼이 사실상 안 보인다"). 이 카드는 t565 가 이미 쥔
// `beat_grid_stage` 응답(그룹별 `member_fids` + `complete`, 아래
// `LRSplitStage`)을 직접 쓴다: 트랙 이름과 정확히 같은 그룹을 그 응답의
// `groups`에서 찾고, 그 그룹의 `member_fids`를 무대 x로 좌우로 나눈다 —
// 장비의 "확인된 소속 이름"을 다시 거치지 않으므로 부모·자식 이름이
// 달라도 상관없다(그룹 자체가 멤버 목록을 이미 들고 있다). 그 그룹을 못
// 찾거나(이 트랙 이름의 그룹이 없음) `complete`가 거짓이면(일부만 읽힘)
// 분리 불가로 둔다 — 부분 데이터로 "그럴듯한" 좌우 대수를 지어내지
// 않는다.
//
// L·R 방향(실측 확정, 카드 t568) — "x 작을수록 왼쪽(L)"은 house(객석)
// 기준으로 **두 출처가 일치**한다. (1) MA3 공식 좌표 규약: `+x = stage
// left`(배우 기준, *"Stage right will be negative numbers"*)이고 무대
// 관례상 stage left/right(배우 기준)와 house left/right(객석 기준)는
// 정반대다 — 그러므로 house left(한국어 "왼쪽", 이 규약 자체도 house
// 기준이라고 명시됨)는 **음의 x**, 즉 더 **작은 x** 다
// (`.moai/specs/SPEC-COPILOT-SPATIAL-001/design.md:67-71` + `spec.md:
// 164-165,170`, "한국어 '왼쪽/오른쪽'도 house 기준이다"). (2) 이 앱
// 자신의 2D 무대 투영(`BeatGrid.tsx` `projectFixture`: `cx = STAGE_MARGIN
// + ((point.x - bounds.minX) / bounds.spanX) * usableW`)도 x 가 커질수록
// 화면 좌표 cx 가 커진다 — 작은 x 가 이미 화면 왼쪽에 그려진다. 두
// 출처가 서로 다른 결론을 내리지 않으므로(둘 다 "작은 x = 왼쪽") 이
// 규칙은 더 이상 t560 이 적었던 "미확인 가정"이 아니다 — 아래
// `lrSplit.test.ts`의 "L·R 방향(실측 확정)" describe 가 그 두 출처를
// 인용해 고정한다.

/** `beat_grid_stage` 응답(카드 t565)의 장비 한 대 — 이 모듈이 쓰는 최소
 * 모양(fid·x)만 구조적으로 요구한다(실제로는 `BeatGridStageFixture`나
 * `BeatGridFixturePoint`가 들어오며, 둘 다 이 모양의 상위집합이다). */
export interface LRSplitStageFixture {
  fid: number;
  x: number;
}

/** `beat_grid_stage` 응답의 콘솔 그룹 하나 — `BeatGridStageGroup`(실제
 * 콘솔 판독 결과 타입)과 구조적으로 호환된다(초과 필드 `group_no`는
 * 허용). 그 응답은 박자 격자 트랙 이름과 **정확히** 같은 그룹만 담는다
 * (이름 앞부분 추정 없음, t565). `complete=false`면 그 그룹 소속 장비
 * 일부만 읽혔다는 뜻이다 — 이 모듈은 그 경우를 분리 불가로 다룬다. */
export interface LRSplitStageGroup {
  group_name: string;
  member_fids: readonly number[];
  complete: boolean;
}

/** `canDeclareLRSplit`/`computeLRSplitEligibility`/`lrChildRowsForTrack`가
 * 받는 무대 판독 묶음 — `beat_grid_stage` 응답(`BeatGridStageView`)과
 * 구조적으로 호환된다(초과 필드는 허용되므로 그 응답을 그대로 넘겨도
 * 된다). */
export interface LRSplitStage {
  fixtures: readonly LRSplitStageFixture[];
  groups: readonly LRSplitStageGroup[];
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
function stageCentreX(fixtures: readonly LRSplitStageFixture[]): number | null {
  if (fixtures.length === 0) return null;
  const xs = fixtures.map((f) => f.x);
  return (Math.min(...xs) + Math.max(...xs)) / 2;
}

export interface LRSplitEligibility {
  splittable: boolean;
  leftCount: number;
  rightCount: number;
}

/** 이 콘솔 그룹의 분리 가능 여부 + 좌우 실측 대수. 트랙 이름과 정확히
 * 같은 그룹을 `stage.groups`에서 찾아(이름 앞부분 추정 없음) 그 그룹의
 * `member_fids`를 무대 x로 좌우로 나눈다. 그룹이 없거나 `complete`가
 * 거짓(일부만 읽힘)이면 분리 불가 — 부분 데이터를 지어내지 않는다.
 * 중앙(x === 중심)에 정확히 있는 장비는 어느 쪽도 아니다. */
export function computeLRSplitEligibility(
  track: { group_name: string },
  stage: LRSplitStage,
): LRSplitEligibility {
  const group = stage.groups.find((candidate) => candidate.group_name === track.group_name);
  if (!group || !group.complete) return { splittable: false, leftCount: 0, rightCount: 0 };
  const centre = stageCentreX(stage.fixtures);
  if (centre === null) return { splittable: false, leftCount: 0, rightCount: 0 };
  const fixturesByFid = new Map(stage.fixtures.map((fixture) => [fixture.fid, fixture]));
  let leftCount = 0;
  let rightCount = 0;
  for (const fid of group.member_fids) {
    const fixture = fixturesByFid.get(fid);
    if (!fixture) continue; // 그룹이 든 fid가 fixtures 목록에 없음 — 지어내지 않는다.
    if (fixture.x < centre) leftCount++;
    else if (fixture.x > centre) rightCount++;
    // x === centre 는 어느 쪽도 아니다(명세 그대로, 지어내지 않음).
  }
  return { splittable: leftCount > 0 && rightCount > 0, leftCount, rightCount };
}

/** 이 트랙이 "이 구간 L·R 따로"를 선언할 수 있는가 — 층 역할이
 * 옆빛(side)이고(REQ-LDBEAT-021(b) "옆빛 L·R" 전용 필드와 같은 범위)
 * 실측 장비가 무대 좌우 양쪽에 있을 때만(`computeLRSplitEligibility`). */
export function canDeclareLRSplit(track: LRSplitEligibleTrack, stage: LRSplitStage): boolean {
  if (track.layer_role !== "side") return false;
  return computeLRSplitEligibility(track, stage).splittable;
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
  stage: LRSplitStage,
): LRChildRow[] {
  if (!canDeclareLRSplit(track, stage)) return [];
  const range = declarations.get(track.group_name);
  if (!range) return [];
  const { leftCount, rightCount } = computeLRSplitEligibility(track, stage);
  return [
    { side: "L", label: `${track.group_name} L`, memberCount: leftCount, startBar: range.startBar, endBar: range.endBar },
    { side: "R", label: `${track.group_name} R`, memberCount: rightCount, startBar: range.startBar, endBar: range.endBar },
  ];
}

/** 지금 편집 칸이 보고 있는 L·R 자식 줄(REQ-LDBEAT-021(b) "옆빛 L·R"과
 * 같은 범위) — `null`이면 부모 그룹 줄을 보고 있다는 뜻이다. */
export interface LRSplitViewedChild {
  groupName: string;
  side: "L" | "R";
}

/** REQ-LDBEAT-024(e)/AC-LDBEAT-024(e) — 보고 있는 줄이 L·R 자식 줄인데
 * 마디(재생 위치·클릭한 마디)가 그 구간을 벗어나면 편집 칸이 부모
 * 그룹 줄로 넘어간다(`null`). 이미 부모를 보고 있으면(`viewed`가
 * `null`) 그대로 `null`. 선언이 없거나(다시 합치기로 지워짐) 범위
 * 밖이면(끝은 배타적, `lrChildRowsForTrack`의 `endBar`와 같은 관례)
 * `null`로 떨어진다 — 지어낸 자식 유지 없음. 범위 안이면 입력을 그대로
 * 돌려준다(side 유지). */
export function resolveLRSplitViewAfterBarChange(
  viewed: LRSplitViewedChild | null,
  declarations: LRSplitDeclarations,
  bar: number,
): LRSplitViewedChild | null {
  if (!viewed) return null;
  const range = declarations.get(viewed.groupName);
  if (!range) return null;
  if (bar < range.startBar || bar >= range.endBar) return null;
  return viewed;
}
