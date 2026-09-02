"""t255 — 정본 §11.1 「부분집합 금지 — 모든 큐에 최소 1행」을 CUE ↔ CUE-EX 로 대조한다."""

import glob

import openpyxl

PATH = glob.glob("src/Lighting_Designer/03_곡파일_Sugar/*.xlsx")[0]


def q_numbers(ws, header_hint: str = "Q#") -> list[str]:
    rows = list(ws.iter_rows(values_only=True))
    header_row = None
    for i, row in enumerate(rows):
        cells = [str(c).strip() if c is not None else "" for c in row]
        if header_hint in cells:
            header_row = i
            col = cells.index(header_hint)
            break
    if header_row is None:
        return []
    out = []
    for row in rows[header_row + 1 :]:
        value = row[col] if col < len(row) else None
        if value is None:
            continue
        text = str(value).strip()
        if text and text.upper().startswith("Q"):
            out.append(text)
    return out


def main() -> None:
    wb = openpyxl.load_workbook(PATH, read_only=True, data_only=True)
    cue = q_numbers(wb["CUE"])
    cue_ex = q_numbers(wb["CUE-EX"])
    cue_set, ex_set = sorted(set(cue)), sorted(set(cue_ex))
    print(f"CUE     행 {len(cue):3} · 고유 Q# {len(cue_set):3}")
    print(f"CUE-EX  행 {len(cue_ex):3} · 고유 Q# {len(ex_set):3}")
    print()
    print("CUE 에 있고 CUE-EX 에 없는 Q# :", [q for q in cue_set if q not in ex_set] or "없음")
    print("CUE-EX 에 있고 CUE 에 없는 Q# :", [q for q in ex_set if q not in cue_set] or "없음")
    print()
    print("CUE 고유 Q#   :", ", ".join(cue_set))
    print("CUE-EX 고유 Q#:", ", ".join(ex_set))


if __name__ == "__main__":
    main()
