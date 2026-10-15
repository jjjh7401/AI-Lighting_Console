// 「이 마디 한눈에」 표 칸 하나를 그린다(REQ-LDBEAT-023(a)(c)) —
// `glanceCells.ts`가 계산한 값을 그대로 그린다(로직 0, 표시만). 칩이면
// 프리셋 번호+이름을 작은 태그로, 텍스트면 그대로. SPEC-LDBEAT-001 M9
// step 2·4(나)·6, 카드 t560 후속.
import type { GlanceCellValue } from "./glanceCells";

export function GlanceCell({ value }: { value: GlanceCellValue }) {
  if (value.kind === "chip") {
    return (
      <span className="beat-grid-glance-chip" title={value.tooltip}>
        <b>{value.presetNo}</b>
        {value.name !== null && ` ${value.name}`}
      </span>
    );
  }
  if (value.dim) return <span className="beat-grid-glance-dim">{value.text}</span>;
  return <>{value.text}</>;
}
