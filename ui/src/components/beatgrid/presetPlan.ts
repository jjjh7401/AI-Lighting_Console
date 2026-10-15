// 「필요한 프리셋 만들기」 — 서버가 승인 카드보다 먼저 보내는 계획표 읽기.
//
// 서버(`session.beat_grid_preset_plan`)는 새 메시지 타입 없이 기존 `chat_response`
// (summary = PRESET_PLAN_SUMMARY, text = `plan_table_markdown`)로 계획표를 보낸다.
// 여기서는 그 마크다운 표를 행으로 읽을 뿐, 값을 지어내지 않는다.

export const PRESET_PLAN_SUMMARY = "연출 프리셋 계획";

export type PresetPlanKind = "dimmer" | "color" | "position";

export interface PresetPlanRow {
  kind: PresetPlanKind;
  name: string;
  value: string;
  /** 후보 번호 `pool.slot` — 풀을 못 읽었으면 「없음」. */
  slot: string;
  cellCount: number;
  /** 「저장(이 카드)」 · 「이 카드 밖」 · 「미정」. */
  status: string;
  /** 「감독이 고칠 값」 목록에 이 줄이 걸려 있다. */
  needsSupervisor: boolean;
}

export interface PresetPlan {
  rows: PresetPlanRow[];
  /** 「이 카드 밖」·「미정」 — 사유 문장 그대로. */
  excluded: { title: string; items: string[] }[];
  supervisorFixes: string[];
}

export const PRESET_PLAN_KIND_LABEL: Record<PresetPlanKind, string> = {
  dimmer: "디머",
  color: "색",
  position: "위치",
};

function kindOf(value: string): PresetPlanKind {
  if (/%\s*$/.test(value)) return "dimmer";
  if (/^RGB\b/i.test(value)) return "color";
  return "position";
}

function cellsOf(line: string): string[] {
  return line
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((c) => c.trim());
}

/** 계획표 마크다운 → 구조. 표가 없으면 `null`(다른 답을 계획표로 착각하지 않는다). */
export function parsePresetPlan(text: string): PresetPlan | null {
  const lines = text.split("\n");
  const head = lines.findIndex((l) => l.startsWith("| 만들 프리셋"));
  if (head < 0) return null;
  const rowsRaw: string[][] = [];
  let i = head + 2;
  for (; i < lines.length && lines[i].startsWith("|"); i += 1) rowsRaw.push(cellsOf(lines[i]));
  const sections: { title: string; items: string[] }[] = [];
  for (; i < lines.length; i += 1) {
    const m = /^\*\*(.+)\*\*$/.exec(lines[i].trim());
    if (m) sections.push({ title: m[1], items: [] });
    else if (lines[i].startsWith("- ") && sections.length > 0) {
      sections[sections.length - 1].items.push(lines[i].slice(2));
    }
  }
  const supervisorFixes = sections.find((s) => s.title === "감독이 고칠 값")?.items ?? [];
  const rows: PresetPlanRow[] = rowsRaw
    .filter((c) => c.length >= 5)
    .map(([name, value, slot, cells, status]) => {
      const label = value.split(" (대략")[0];
      return {
        kind: kindOf(value),
        name,
        value,
        slot,
        cellCount: Number.parseInt(cells, 10) || 0,
        status,
        needsSupervisor: supervisorFixes.some(
          (fix) => fix.startsWith(`${name} `) || fix.startsWith(`${label} `),
        ),
      };
    });
  return {
    rows,
    excluded: sections.filter((s) => s.title !== "감독이 고칠 값"),
    supervisorFixes,
  };
}
