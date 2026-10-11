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
