// 「이 마디 한눈에」 머리 문구(마디 이름·접힌 폴더 요약) 시험 — checklist 「이 마디 한눈에」.
import { describe, expect, it } from "vitest";

import { collapsedFolderSummary, glanceBarLabel } from "./glanceCells";

describe("glanceBarLabel", () => {
  it("0번 마디는 「앞박」, 그 밖은 「N마디」다", () => {
    expect(glanceBarLabel(0)).toBe("앞박");
    expect(glanceBarLabel(18)).toBe("18마디");
  });
});

describe("collapsedFolderSummary", () => {
  it("접힌 폴더는 줄 수를 보이고, 이 마디에 바뀐 줄이 있으면 그 수도 잇는다", () => {
    expect(collapsedFolderSummary(2, 2)).toBe(" — 2줄 접힘 · 이 마디 2줄 바뀜");
  });

  it("이 마디에 바뀐 줄이 없으면 접힘 수만 보인다", () => {
    expect(collapsedFolderSummary(3, 0)).toBe(" — 3줄 접힘");
  });
});
