// 「이 마디 한눈에」 칸 표시 — 흐린 칸의 계획 색 네모(「유지」 칸은 기존 그대로).
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { GlanceCell } from "./GlanceCell";

describe("GlanceCell 흐린 칸", () => {
  it("계획 색이 있으면 흐린 칸 안에서 색 네모를 「—」 앞에 그린다", () => {
    const html = renderToStaticMarkup(
      <GlanceCell value={{ kind: "text", text: "—", dim: true, swatch: "rgb(102, 166, 242)" }} />,
    );
    expect(html).toContain('<span class="beat-grid-glance-dim">');
    expect(html).toContain('class="beat-grid-glance-sw"');
    expect(html).toContain("background:rgb(102, 166, 242)");
    expect(html).toContain("—");
  });

  it("색이 없는 흐린 칸(「유지」)은 네모 없이 글자만 그린다", () => {
    const html = renderToStaticMarkup(<GlanceCell value={{ kind: "text", text: "유지", dim: true }} />);
    expect(html).toBe('<span class="beat-grid-glance-dim">유지</span>');
  });
});
