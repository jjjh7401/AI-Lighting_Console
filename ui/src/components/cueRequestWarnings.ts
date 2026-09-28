// PLAN CUE 수정요청 생성기 — 파생 경고 4종 (t460, SPEC-LDDESIGN-001 REQ-093,
// D3 감독 결정 2026-09-27: 데이터가 있는 4개만 — (1) 후렴 밝기 역전,
// (3) 리저브 위반, (4) 헤드룸<4, (5) MIB live). (2) 팬 폭·(6) 페이저=BPM은
// UI로 오는 데이터가 없어(t460 plan.md F8) 구현하지 않는다 — 서버 필드
// 노출 카드(t467)로 넘긴다.
//
// AC-LDDESIGN-040: 리저브 위반·헤드룸·MIB live 3종은 REQ-027·REQ-090·
// REQ-050·REQ-066이 이미 계산한 필드 값을 **그대로 소비**한다 — 이 파일은
// 그 세 값에 대해 별도 재계산 로직을 갖지 않는다(코드 검사 대상). 후렴
// 역전(1)만 이 파일이 직접 계산한다(REQ-093 (1)이 "신규"라고 명시).
import type { SongTimelineConceptRow, SongTimelineReserveItem, SongTimelineSection } from "../protocol";
import { sectionIntensityPercent } from "./CueSheetTimeline";
import { sectionPosition } from "./runbookM7";
import type { GeneratorChange } from "./cueRequestSentence";

/** REQ-093 (1) — 이 큐가 후렴(role === "chorus")이고, 제안된 밝기가 뒤에
 * 오는 어느 후렴보다도 밝으면 상승 곡선이 무너진다. `role` 은 서버가
 * 판독했을 때만 존재한다(protocol.ts) — 없으면 판단하지 않는다(n/a). */
export function chorusReversalWarning(
  section: SongTimelineSection,
  allSections: SongTimelineSection[],
  proposedIntensityPercent: number,
): string | null {
  if (section.role !== "chorus") return null;
  const laterChoruses = allSections.filter(
    (candidate) => candidate.index > section.index && candidate.role === "chorus",
  );
  if (laterChoruses.length === 0) return null;
  const maxLaterPercent = Math.max(...laterChoruses.map(sectionIntensityPercent));
  if (proposedIntensityPercent > maxLaterPercent) {
    return `⚠ 뒤 후렴(${maxLaterPercent}%)보다 밝아져 후렴 상승 곡선이 무너진다`;
  }
  return null;
}

/** REQ-090·REQ-093 (3) 리저브 판정 한 곳 — BLIND 잠금과 리저브 경고가 함께
 * 쓴다. `reserve` 는 `concept_report.reserve` 를 그대로 읽는다(재계산 금지,
 * REQ-027·REQ-090의 서버 원천). 이름 대조는 대소문자 무시(서버 그룹명은
 * 대문자, 색 이름은 표기가 다를 수 있어 정확 일치만 본다 — 지어낸 근사
 * 매칭은 하지 않는다).
 *
 * t481 — 해제 시점은 `screen_position`(구간 0부터 위치)으로 비교한다.
 * `released_q` 는 컨셉 **행** 번호라 구간 큐 번호와 단위가 다르다(행 49개 곡에서
 * 45 = 구간 33). `position` 은 `sectionPosition()` 이 낸 값이어야 한다.
 * 잠겨 있으면 이름과 해제 큐 라벨을, 아니면 null 을 낸다. 해제 행이 화면
 * 구간과 짝이 안 됐으면(`screen_position` null) 위치를 지어내지 않고 잠그지
 * 않는다. */
export function reserveLock(
  name: string,
  reserve: SongTimelineReserveItem[] | undefined,
  position: number,
  sections: ReadonlyArray<Pick<SongTimelineSection, "cue_number">>,
): { name: string; release: string } | null {
  const item = reserve?.find((entry) => entry.name.toUpperCase() === name.toUpperCase());
  if (!item) return null;
  if (item.released_q === null) return { name: item.name, release: "미해제" };
  if (item.screen_position === null || position >= item.screen_position) return null;
  const cue = sections[item.screen_position]?.cue_number;
  return { name: item.name, release: cue === undefined ? "위치 불명" : `Q${cue}` };
}

/** REQ-093 (3) — 리저브(BLIND·STROBE·유보색) 대상을 해제 큐 이전에 쓰면 위반. */
export function reserveViolationWarning(
  position: number,
  reserve: SongTimelineReserveItem[] | undefined,
  proposedName: string,
  sections: ReadonlyArray<Pick<SongTimelineSection, "cue_number">>,
): string | null {
  const lock = reserveLock(proposedName, reserve, position, sections);
  return lock === null ? null : `⚠ ${lock.name}은(는) 리저브 대상이다 — 해제 큐(${lock.release}) 이전`;
}

/** REQ-093 (4) — 잔여 그룹 < 4. `row.unused_groups` 는 REQ-050의 헤드룸
 * 필드를 그대로 읽는다(재계산 금지, AC-040). */
export function headroomWarning(row: SongTimelineConceptRow | undefined): string | null {
  if (row?.unused_groups === undefined) return null;
  return row.unused_groups < 4 ? `⚠ 잔여 그룹 ${row.unused_groups}개 — 헤드룸 부족` : null;
}

/** REQ-093 (5) — MIB `live` 는 GATE WARN 예고. `row.mib` 는 포지션 변화가
 * 있을 때만 값을 갖는다(protocol.ts 주석) — 그래서 이 경고는 무브먼트
 * 변경에만 병기한다(아래 deriveWarningsForChange). */
export function mibLiveWarning(row: SongTimelineConceptRow | undefined): string | null {
  return row?.mib === "live" ? "⚠ MIB live — GATE 경고 예고" : null;
}

export interface WarningContext {
  section: SongTimelineSection;
  allSections: SongTimelineSection[];
  conceptRow: SongTimelineConceptRow | undefined;
  reserve: SongTimelineReserveItem[] | undefined;
}

/** 변경 하나에 병기할 경고 전부(REQ-091 — diff 줄에 그대로 붙인다, 스택
 * 하단에 모아 쓰지 않는다). 필드별 대응:
 *  - intensity/palette_primary → 그 변경이 다루는 그룹·색이 리저브 대상인지
 *  - intensity → 후렴 역전(제안값 기준) + 헤드룸(그 큐의 값을 그대로 읽음)
 *  - movement/position → MIB(포지션 변화가 있을 때만 의미 있는 필드이므로 여기 붙인다.
 *    t470 — 포지션 행이 `movement` 대신 `position` 문장을 내므로 둘 다 받는다)
 */
export function deriveWarningsForChange(context: WarningContext, change: GeneratorChange): string[] {
  const warnings: string[] = [];
  const position = sectionPosition(context.section, context.allSections);

  if (change.field === "intensity") {
    const reversal = chorusReversalWarning(context.section, context.allSections, change.value);
    if (reversal) warnings.push(reversal);
    for (const group of change.groups ?? []) {
      const reserveHit = reserveViolationWarning(position, context.reserve, group, context.allSections);
      if (reserveHit) warnings.push(reserveHit);
    }
    const headroom = headroomWarning(context.conceptRow);
    if (headroom) warnings.push(headroom);
  }

  if (change.field === "palette_primary") {
    for (const group of change.groups) {
      const reserveHit = reserveViolationWarning(position, context.reserve, group, context.allSections);
      if (reserveHit) warnings.push(reserveHit);
    }
    const colorReserveHit = reserveViolationWarning(position, context.reserve, change.value, context.allSections);
    if (colorReserveHit) warnings.push(colorReserveHit);
  }

  if (change.field === "movement" || change.field === "position") {
    const mibHit = mibLiveWarning(context.conceptRow);
    if (mibHit) warnings.push(mibHit);
  }

  return warnings;
}
