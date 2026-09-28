// t485 — 컨셉 패널 탭 1 인과 불릿(REQ-013·032·080).
//
// 원천은 서버 `concept_bullet`(server/concept/session_bridge.py, 인터뷰 Q1 기록) 하나다.
// 원문 원칙(REQ-032 "요약·재작성 없이"): 줄바꿈으로 불릿을 나누고 빈 줄만 버린다.
// 각 줄의 글자(앞뒤 공백 포함)는 바꾸지 않는다. 원문이 없으면 서버 사유를 그대로 보인다.
import type { SongTimelineConceptBullet } from "../protocol";

/** REQ-080 "원문 그대로" 배지 문자열. */
export const VERBATIM_BADGE = "원문 그대로";

export type ConceptBulletView =
  | { status: "none"; reason: string }
  | { status: "ok"; lines: string[]; badge: string; origin: string };

export function conceptBulletView(bullet: SongTimelineConceptBullet | undefined): ConceptBulletView {
  if (!bullet) {
    return { status: "none", reason: "서버가 인과 불릿 원문을 보내지 않았다(예전 페이로드)" };
  }
  if (!bullet.available) {
    return { status: "none", reason: bullet.reason ?? "서버가 사유를 보내지 않았다" };
  }
  const lines = (bullet.text ?? "").split("\n").filter((line) => line.trim() !== "");
  if (lines.length === 0) {
    return { status: "none", reason: "Q1 컨셉 답이 비어 있다" };
  }
  return { status: "ok", lines, badge: VERBATIM_BADGE, origin: bullet.origin_label ?? "" };
}
