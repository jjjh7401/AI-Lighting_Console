// 2D 무대 판독(`beat_grid_stage`) → BeatGrid 장비 점 (카드 t565, SPEC-LDBEAT-001 REQ-022).
//
// 서버가 콘솔에서 읽은 값만 옮긴다 — 좌표는 패치 그대로, 소속은 트랙 이름과 같은
// 콘솔 그룹의 SELECTIONDATA 판독 결과다. 한 장비가 부모·자식 그룹(SIDE-ALL ⊇
// SIDE-L)에 함께 들 수 있으므로 소속은 이름 **목록**이다.
import type { BeatGridStageView } from "../protocol";
import type { BeatGridFixturePoint } from "./BeatGrid";

/** 장비가 콘솔에서 확인된 소속 그룹 이름들 — 새 목록 필드와 예전 한 개짜리
 * 필드를 합친다(중복 없이, 들어온 순서대로). */
export function fixtureConfirmedGroupNames(fixture: BeatGridFixturePoint): string[] {
  const names = [...(fixture.confirmedGroupNames ?? [])];
  if (fixture.confirmedGroupName) names.push(fixture.confirmedGroupName);
  const seen = new Set<string>();
  return names.filter((name) => {
    const key = name.toUpperCase();
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

/** 확인된 소속에 그 그룹 이름이 **정확히**(대소문자만 무시) 있는가. 이름 앞부분
 * 추정은 하지 않는다. */
export function fixtureBelongsTo(fixture: BeatGridFixturePoint, groupName: string): boolean {
  const key = groupName.toUpperCase();
  return fixtureConfirmedGroupNames(fixture).some((name) => name.toUpperCase() === key);
}

/** 판독 결과를 장비 점 목록으로. 회전은 이 판독이 읽지 않으므로 0이다(무대
 * 그림은 위에서 본 X·Y만 쓴다). */
export function stageFixturePoints(view: BeatGridStageView | null | undefined): BeatGridFixturePoint[] {
  if (!view) return [];
  return view.fixtures.map((fixture) => ({
    fid: fixture.fid,
    name: fixture.name,
    x: fixture.x,
    y: fixture.y,
    z: fixture.z,
    rotx: 0,
    roty: 0,
    rotz: 0,
    confirmedGroupNames: view.groups
      .filter((group) => group.member_fids.includes(fixture.fid))
      .map((group) => group.group_name),
  }));
}

/** 카드 t586 — 타임라인 줄 이름 아래 둘째 줄(시안 `.lhead small`, 예:
 * 「G3 · 111~118 · 8대」). 그룹 번호는 트랙 값, 장비 번호 범위와 대수는 무대
 * 판독이 그 그룹 소속으로 **확인한** 장비에서만 센다. 확인된 장비가 없으면
 * 범위·대수를 빼고(지어내지 않음), 그룹 번호도 없으면 `null`. */
/** 카드 t586 — 그 그룹 소속으로 확인된 장비 번호 범위(「201~202」, 한 대면
 * 「201」). 확인된 장비가 없으면 `null`. */
export function confirmedFixtureRange(
  groupName: string,
  fixtures: readonly BeatGridFixturePoint[],
): string | null {
  const fids = fixtures
    .filter((fixture) => fixtureBelongsTo(fixture, groupName))
    .map((fixture) => fixture.fid)
    .sort((a, b) => a - b);
  if (fids.length === 0) return null;
  const first = fids[0];
  const last = fids[fids.length - 1];
  return first === last ? `${first}` : `${first}~${last}`;
}

export function trackFixtureSummary(
  groupNo: number | null,
  groupName: string,
  fixtures: readonly BeatGridFixturePoint[],
): string | null {
  const count = fixtures.filter((fixture) => fixtureBelongsTo(fixture, groupName)).length;
  const range = confirmedFixtureRange(groupName, fixtures);
  const parts: string[] = [];
  if (groupNo !== null) parts.push(`G${groupNo}`);
  if (range !== null) {
    parts.push(range);
    parts.push(`${count}대`);
  }
  return parts.length > 0 ? parts.join(" · ") : null;
}
