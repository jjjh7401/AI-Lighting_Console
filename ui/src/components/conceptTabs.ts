// t492 — SPEC-LDDESIGN-001 AC-018 후속: 컨셉 패널 탭 2·3 본문과 4칸 「바꾸려면」,
// 「그래서 보이는 것」 칸 사유(REQ-079·080·097·098). 원천 판정은
// .moai/reports/t492/run-verdict.md, 리드 결정(2026-10-12)을 따른다.
//
// 원칙 두 가지:
// - 다른 칸에 이미 나온 값을 되풀이하지 않는다(REQ-097). 탭 2 는 구간 행 값을
//   늘어놓지 않고 곡 단위로 센다(몇 구간에 무엇이 몇 번).
// - 원천이 없는 내용은 지어내지 않는다. 비우고 사유를 보인다.
import type {
  SongTimelineConceptReport,
  SongTimelinePlanStatus,
  SongTimelineSection,
} from "../protocol";
import { cueLabel } from "./CueSheetTimeline";
import { NO_DATA } from "./runbookM7";

/** 「그래서 보이는 것」 칸 사유 — 인터뷰 Q1~Q5 가 모두 곡 단위라 구간별 결과
 * 문장 원천이 없다(판정서 §1). 표 아래 한 번만 쓴다(행마다 반복하지 않는다). */
export const OUTCOME_NO_SOURCE = "구간별 원천 없음 — 인터뷰가 곡 단위";

/** 4칸 「바꾸려면」. 런북의 수정요청 생성기는 콘솔에 저장 전 큐(PLAN CUE)
 * 카드에만 열린다(SongTimeline `onConsole` — stored·verified 면 닫힘). */
export function changeGuideText(section: SongTimelineSection, status: SongTimelinePlanStatus): string {
  if (status === "stored" || status === "verified") {
    return `${NO_DATA} — 콘솔에 저장된 큐라 런북 수정요청 생성기가 열리지 않는다(PLAN CUE 에만 열림)`;
  }
  return `타임라인 ${cueLabel(section)} PLAN CUE 카드 → 수정요청 생성기(그룹·밝기·페이드·전환·트래킹·MIB·콘솔 반영 값)`;
}

export interface Tally {
  value: string;
  count: number;
}

/** 값별 구간 수. 많은 순, 같으면 처음 나온 순. 빈 값은 세지 않는다. */
function tally(values: readonly (string | undefined | null)[]): Tally[] {
  const counts = new Map<string, number>();
  for (const raw of values) {
    const value = raw?.trim();
    if (!value) continue;
    counts.set(value, (counts.get(value) ?? 0) + 1);
  }
  return [...counts.entries()]
    .map(([value, count]) => ({ value, count }))
    .sort((a, b) => b.count - a.count);
}

/** 이웃 구간 사이에서 값이 바뀐 횟수(둘 다 값이 있을 때만 센다). */
function changes(values: readonly (string | undefined | null)[]): { changed: number; compared: number } {
  let changed = 0;
  let compared = 0;
  for (let i = 1; i < values.length; i += 1) {
    const before = values[i - 1]?.trim();
    const now = values[i]?.trim();
    if (!before || !now) continue;
    compared += 1;
    if (before !== now) changed += 1;
  }
  return { changed, compared };
}

export interface MaterialItem {
  title: string;
  /** 원천이 있으면 집계 문장, 없으면 NO_DATA + 사유. */
  text: string;
  nodata: boolean;
}

function tallyItem(title: string, values: readonly (string | undefined | null)[], total: number): MaterialItem {
  const counts = tally(values);
  if (counts.length === 0) {
    return { title, text: `${NO_DATA} — 이 곡 구간에 ${title} 값이 없다`, nodata: true };
  }
  const filled = counts.reduce((sum, entry) => sum + entry.count, 0);
  const body = counts.map((entry) => `${entry.value} ${entry.count}구간`).join(" · ");
  const blank = total - filled;
  return { title, text: blank > 0 ? `${body} · 값 없음 ${blank}구간` : body, nodata: false };
}

/** 서버 `movement` 는 큐의 포지션 프리셋이다(server/web/session.py
 * `cue.position.stored or cue.position.requested`) — 「공간」(`position`)과 같은 축.
 * 모든 구간에서 둘이 같으면 따로 세면 같은 집계가 두 번 나온다(REQ-097) → 비운다.
 * 다른 구간이 하나라도 있을 때만 움직임 값을 센다. */
function movementItem(sections: readonly SongTimelineSection[], total: number): MaterialItem {
  const differs = sections.some((section) => {
    const movement = section.movement?.trim();
    return Boolean(movement) && movement !== section.position?.trim();
  });
  if (!differs && sections.some((section) => section.movement?.trim())) {
    return {
      title: "움직임",
      text: `${NO_DATA} — 움직임 값이 포지션 프리셋과 같다(공간에서 셌다)`,
      nodata: true,
    };
  }
  return tallyItem("움직임", sections.map((section) => section.movement), total);
}

/** 탭 2 「이 곡의 재료」 — 감정·공간·움직임·질감·시작–끝(src/DESIGN.md §4.2). */
export function materialSummary(sections: readonly SongTimelineSection[]): MaterialItem[] {
  const total = sections.length;
  const positions = sections.map((section) => section.position);
  const textures = sections.map((section) => section.texture);
  const space = changes(positions);
  const texture = changes(textures);
  const startEnd: MaterialItem =
    space.compared + texture.compared === 0
      ? { title: "시작–끝", text: `${NO_DATA} — 비교할 이웃 구간 값이 없다`, nodata: true }
      : {
          title: "시작–끝",
          text: `구간 경계 ${Math.max(total - 1, 0)}곳 중 공간 바뀜 ${space.changed}번 · 질감 바뀜 ${texture.changed}번`,
          nodata: false,
        };
  return [
    {
      title: "감정",
      // server/web/session.py `_song_cue_sheet_section_fields` — "못 채우는 것: mood".
      text: `${NO_DATA} — 서버가 구간 무드를 계획으로 넘기지 못한다`,
      nodata: true,
    },
    tallyItem("공간", positions, total),
    movementItem(sections, total),
    tallyItem("질감", textures, total),
    startEnd,
  ];
}

export interface ReserveLine {
  name: string;
  kind: "그룹" | "색";
  release: string;
}

export type GrammarView =
  | { status: "none"; reason: string }
  | { status: "ok"; reserve: ReserveLine[] };

/** 탭 3 「지키는 것·하지 않는 것」 칸 사유 — 게이트를 지킴/금지로 나누는 분류
 * 원천이 없고, 규칙 판정은 이미 게이트 바가 보인다(리드 결정: 분류표 안 만듦). */
export const KEEP_FORBID_NO_SOURCE = "규칙별 지킴/금지 분류 원천이 없다 — 규칙 판정은 게이트 바";

/** 탭 3 「아껴 두는 것」 — `concept_report.reserve` 를 그대로 읽는다(재계산 금지).
 * 해제 위치는 `screen_position`(구간 0부터) → 그 구간 큐 번호. `released_q` 는
 * 컨셉 행 번호라 화면 큐 번호와 단위가 다르다(cueRequestWarnings `reserveLock`). */
export function grammarView(
  report: SongTimelineConceptReport | undefined,
  sections: readonly SongTimelineSection[],
): GrammarView {
  if (!report) return { status: "none", reason: "컨셉 리포트가 없다" };
  if (!report.available) return { status: "none", reason: report.reason ?? "컨셉 리포트를 못 만들었다" };
  if (!report.reserve || report.reserve.length === 0) {
    return { status: "none", reason: "아껴 둘 그룹·색이 서버 리포트에 없다" };
  }
  return {
    status: "ok",
    reserve: report.reserve.map((item) => {
      let release: string;
      if (item.released_q === null) {
        // 서버는 "한 번도 안 켜짐"과 "입력 색이 없어 판정 안 함"을 둘 다 null 로
        // 낸다(session_bridge `_concept_reserve`) — 이유를 지어내지 않는다.
        release = "미해제 — 해제 큐를 찾지 못했다";
      } else if (item.screen_position === null || sections[item.screen_position] === undefined) {
        release = "해제됨 — 화면 구간 위치 불명";
      } else {
        const section = sections[item.screen_position];
        release = `${cueLabel(section)} ${section.label} 에서 처음 푼다`;
      }
      return { name: item.name, kind: item.kind === "color" ? "색" : "그룹", release };
    }),
  };
}
