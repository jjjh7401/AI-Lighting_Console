// 카드 t603 — 「＋ 새 프리셋 만들기」 창의 효과 종류 입력칸: 효과 틀 + 주기(박/마디).
//
// 서버(t593)는 반영 때 `preset_fx_recipes{"p.s": {fx_id, period_unit, period_value}}`로
// 효과 프리셋을 만든다. 이 칸이 그 레시피를 채운다. 효과 틀 목록은 서버가 격자에 실어
// 내려 준 `fx_templates`(출하 fx 라이브러리)만 쓰고, 그 칸의 효과 종류(`effect_kind`)를
// 쓸 수 있는 틀만 보인다 — 반영 때 서버가 받아 주는 판정(`kinds`)과 같다.
// 문구는 시안의 「한 바퀴 N박」을 따른다. 순수 부품(jsdom 없음 — `renderToStaticMarkup`).
import type { BeatGridFxRecipe, BeatGridFxTemplate } from "../../protocol";

export type FxPeriodUnit = "beat" | "bar";

/** 그 칸의 효과 종류에 쓸 수 있는 틀만. 종류를 모르면(`null`) 빈 목록. */
export function fxTemplatesForKind(
  templates: readonly BeatGridFxTemplate[] | null | undefined,
  kind: string | null | undefined,
): BeatGridFxTemplate[] {
  if (!templates || !kind) return [];
  return templates.filter((template) => template.kinds.includes(kind));
}

/** 주기 칸 — 양의 정수(박·마디 수)만. 초·소수·0·빈 칸은 거절(서버와 같은 뜻). */
export function isValidFxPeriod(value: string): boolean {
  if (!/^\d+$/.test(value.trim())) return false;
  return Number(value) > 0;
}

/** 칸 값 셋 → 서버로 보낼 레시피. 하나라도 모자라면 `null`(만들기 비활성). */
export function fxRecipeFromDraft(draft: {
  fxId: string;
  period: string;
  unit: FxPeriodUnit;
}): BeatGridFxRecipe | null {
  if (!draft.fxId || !isValidFxPeriod(draft.period)) return null;
  return { fx_id: draft.fxId, period_unit: draft.unit, period_value: Number(draft.period) };
}

export interface NewPresetFxFieldsProps {
  templates: readonly BeatGridFxTemplate[] | null | undefined;
  /** 그 칸의 `effect_kind` — 번호대와 고를 수 있는 틀을 정한다. */
  kind: string | null | undefined;
  fxId: string;
  period: string;
  unit: FxPeriodUnit;
  onFxIdChange: (value: string) => void;
  onPeriodChange: (value: string) => void;
  onUnitChange: (value: FxPeriodUnit) => void;
}

export function NewPresetFxFields({
  templates,
  kind,
  fxId,
  period,
  unit,
  onFxIdChange,
  onPeriodChange,
  onUnitChange,
}: NewPresetFxFieldsProps) {
  if (!kind) {
    return (
      <p className="beat-grid-cue-field-note u">
        이 칸의 효과 종류(위치·색·혼합)를 먼저 정해야 효과 틀을 고를 수 있어요.
      </p>
    );
  }
  const choices = fxTemplatesForKind(templates, kind);
  if (choices.length === 0) {
    return (
      <p className="beat-grid-cue-field-note u">
        이 효과 종류에 쓸 수 있는 효과 틀 목록을 서버에서 받지 못했어요.
      </p>
    );
  }
  return (
    <>
      <label className="beat-grid-new-preset-field">
        효과 틀
        <select value={fxId} aria-label="효과 틀" onChange={(event) => onFxIdChange(event.target.value)}>
          <option value="">— 고르기 —</option>
          {choices.map((template) => (
            <option key={template.fx_id} value={template.fx_id}>
              {template.display_name} ({template.attributes.join("·")})
            </option>
          ))}
        </select>
      </label>
      <label className="beat-grid-new-preset-field">
        한 바퀴
        <input
          type="number"
          min="1"
          step="1"
          value={period}
          aria-label="한 바퀴 길이"
          onChange={(event) => onPeriodChange(event.target.value)}
        />
      </label>
      <select
        value={unit}
        aria-label="한 바퀴 단위"
        onChange={(event) => onUnitChange(event.target.value === "bar" ? "bar" : "beat")}
      >
        <option value="beat">박</option>
        <option value="bar">마디</option>
      </select>
      {period && !isValidFxPeriod(period) && (
        <p className="beat-grid-cue-field-note u">한 바퀴 길이는 1 이상의 정수(박·마디 수)예요.</p>
      )}
    </>
  );
}
