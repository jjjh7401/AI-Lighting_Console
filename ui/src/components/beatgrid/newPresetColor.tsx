// 카드 t594 — 「＋ 새 프리셋 만들기」 창의 "색" 필드 입력칸: R·G·B(0~100%) +
// 미리보기 조각.
//
// 서버(t594)는 반영 때 그룹 선택 한 줄(`Group <g> ; Attribute 'ColorRGB_R' At
// <r> ; ... 'ColorRGB_G' ... ; ... 'ColorRGB_B' ...`)로 색 프리셋을 만든다 —
// UI는 번호도 명령도 짓지 않는다(기존 aim/fx 칸과 같은 원칙). 순수 부품
// (jsdom 없음 — `renderToStaticMarkup`).

/** 채널 칸 — 0~100 범위의 수만. 빈 칸·범위 밖·수가 아님은 거절(서버의
 * `_validate_new_preset_rgb`와 같은 뜻의 화면 쪽 즉시 확인). */
export function isValidColorChannel(value: string): boolean {
  if (value.trim() === "") return false;
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed >= 0 && parsed <= 100;
}

/** 칸 값 셋 → 미리보기 조각에 쓸 `rgb(...)` 문자열. 셋 중 하나라도 모자라면
 * `null`(스와치를 그리지 않는다) — 0~100% 를 0~255로 환산한다. */
export function colorSwatchValue(draft: { r: string; g: string; b: string }): string | null {
  if (!isValidColorChannel(draft.r) || !isValidColorChannel(draft.g) || !isValidColorChannel(draft.b)) {
    return null;
  }
  const toByte = (percent: string) => Math.round((Number(percent) * 255) / 100);
  return `rgb(${toByte(draft.r)}, ${toByte(draft.g)}, ${toByte(draft.b)})`;
}

export interface NewPresetColorFieldsProps {
  r: string;
  g: string;
  b: string;
  onRChange: (value: string) => void;
  onGChange: (value: string) => void;
  onBChange: (value: string) => void;
}

export function NewPresetColorFields({
  r,
  g,
  b,
  onRChange,
  onGChange,
  onBChange,
}: NewPresetColorFieldsProps) {
  const swatch = colorSwatchValue({ r, g, b });
  return (
    <>
      <label className="beat-grid-new-preset-field">
        R (%)
        <input
          type="number"
          min="0"
          max="100"
          step="1"
          value={r}
          aria-label="R (%)"
          onChange={(event) => onRChange(event.target.value)}
        />
      </label>
      <label className="beat-grid-new-preset-field">
        G (%)
        <input
          type="number"
          min="0"
          max="100"
          step="1"
          value={g}
          aria-label="G (%)"
          onChange={(event) => onGChange(event.target.value)}
        />
      </label>
      <label className="beat-grid-new-preset-field">
        B (%)
        <input
          type="number"
          min="0"
          max="100"
          step="1"
          value={b}
          aria-label="B (%)"
          onChange={(event) => onBChange(event.target.value)}
        />
      </label>
      {swatch && (
        <span
          className="beat-grid-new-preset-color-swatch"
          role="img"
          aria-label="색 미리보기"
          style={{ backgroundColor: swatch }}
        />
      )}
      {(r || g || b) && !swatch && (
        <p className="beat-grid-cue-field-note u">R·G·B는 0~100 범위의 수예요.</p>
      )}
    </>
  );
}
