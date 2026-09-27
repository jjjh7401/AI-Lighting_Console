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

/** REQ-093 (3) — 리저브(BLIND·STROBE·유보색) 대상을 해제 큐 이전에 쓰면
 * 위반. `reserve` 는 `concept_report.reserve` 를 그대로 읽는다(재계산
 * 금지, REQ-027·REQ-090의 서버 원천). 이름 대조는 대소문자 무시(서버
 * 그룹명은 대문자, 색 이름은 표기가 다를 수 있어 정확 일치만 본다 —
 * 지어낸 근사 매칭은 하지 않는다). */
export function reserveViolationWarning(
  cueNumber: number,
  reserve: SongTimelineReserveItem[] | undefined,
  proposedName: string,
): string | null {
  const item = reserve?.find((entry) => entry.name.toUpperCase() === proposedName.toUpperCase());
  if (!item) return null;
  if (item.released_q === null || cueNumber < item.released_q) {
    const releaseLabel = item.released_q === null ? "미해제" : `Q${item.released_q}`;
    return `⚠ ${item.name}은(는) 리저브 대상이다 — 해제 큐(${releaseLabel}) 이전`;
  }
  return null;
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
 *  - movement → MIB(포지션 변화가 있을 때만 의미 있는 필드이므로 여기 붙인다)
 */
export function deriveWarningsForChange(context: WarningContext, change: GeneratorChange): string[] {
  const warnings: string[] = [];
  const cueNumber = context.section.cue_number;

  if (change.field === "intensity") {
    const reversal = chorusReversalWarning(context.section, context.allSections, change.value);
    if (reversal) warnings.push(reversal);
    for (const group of change.groups ?? []) {
      const reserveHit = reserveViolationWarning(cueNumber, context.reserve, group);
      if (reserveHit) warnings.push(reserveHit);
    }
    const headroom = headroomWarning(context.conceptRow);
    if (headroom) warnings.push(headroom);
  }

  if (change.field === "palette_primary") {
    for (const group of change.groups) {
      const reserveHit = reserveViolationWarning(cueNumber, context.reserve, group);
      if (reserveHit) warnings.push(reserveHit);
    }
    const colorReserveHit = reserveViolationWarning(cueNumber, context.reserve, change.value);
    if (colorReserveHit) warnings.push(colorReserveHit);
  }

  if (change.field === "movement") {
    const mibHit = mibLiveWarning(context.conceptRow);
    if (mibHit) warnings.push(mibHit);
  }

  return warnings;
}
