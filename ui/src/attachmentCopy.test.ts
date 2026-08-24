// SPEC-COPILOT-SHEETPIPE-001 M1 — 첨부 경로의 문구가 종류를 단정하지 않는다.
//
// `AC-SHEETPIPE-005` ⑤⑥이 grep으로 적어 둔 두 단언을 테스트로 옮긴 것이다.
// 이 저장소에는 테스트 CI가 없으므로, 손으로 치는 grep보다 스위트가 잡는 쪽이
// 낫다.
//
// 이 파일 자신은 검사 대상이 아니다 — 검사는 `App.tsx`와
// `useCopilotSocket.ts` 두 파일만 읽는다. (문서가 검사의 토큰을 인용하는 순간
// 그 검사가 죽는 형태를 피하려고 대상을 명시적으로 고정했다.)

import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

// 종류를 단정하는 문구는 따옴표나 백틱 바로 뒤에 온다. 식별자
// (`sendVectorworksExportUpload` 같은 것)는 문구가 아니므로 대상이 아니다 —
// 그 이름들까지 세면 오늘 값이 19가 되어 이 검사는 판별력을 잃는다.
const KIND_ASSERTING_LITERAL = /["'`]Vectorworks/g;

const SOURCES = [
  "src/App.tsx",
  "src/useCopilotSocket.ts",
];

function read(path: string): string {
  return readFileSync(new URL(path, import.meta.url).pathname, "utf8");
}

function countMatches(text: string, pattern: RegExp): number {
  return (text.match(new RegExp(pattern.source, "g")) ?? []).length;
}

describe("첨부 경로의 문구는 판정 전에 나가므로 종류를 단정하지 않는다", () => {
  it("정규식 자체가 판별력이 있다 (날조 대조군)", () => {
    // 검사가 공허하지 않은지 먼저 잰다: 이 패턴이 아무것도 못 잡는 정규식이면
    // 아래 두 단언은 늘 초록이고 아무것도 지키지 않는다.
    const control = 'setError("Vectorworks export는 ...");';
    expect(countMatches(control, KIND_ASSERTING_LITERAL)).toBe(1);
    // 식별자는 잡지 않는다 — 그것이 문구와 이름을 가르는 경계다.
    expect(countMatches("sendVectorworksExportUpload(x)", KIND_ASSERTING_LITERAL)).toBe(0);
  });

  it.each(SOURCES)("%s에 종류를 단정하는 문구가 없다", (source) => {
    expect(countMatches(read(`../${source}`), KIND_ASSERTING_LITERAL)).toBe(0);
  });

  it("라우터 옆에 유산 프레임 앵커 주석이 있다", () => {
    // 이 검사가 단언하는 것: 주석이 있다. 단언하지 못하는 것: 주석의 뜻.
    // 그래도 아무것도 걸지 않는 것보다는 낫다 — 확장자 라우팅을 "복원"하려는
    // 사람이 이 주석을 지우면 여기가 빨개진다.
    expect(read("../src/App.tsx")).toContain("SPEC-COPILOT-SHEETPIPE-001");
  });
});
