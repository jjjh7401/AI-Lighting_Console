"""t225 패치 적용기 -- 편집 도구가 이 워크트리에서 path traversal 로 막혀
Bash 경로로 넣는다(규약 §2). 중괄호 리터럴을 쓰지 않는 이유도 같은 절이다.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]

CUE_MAPPER = ROOT / "server/lxseq/cue_mapper.py"
TOOLS = ROOT / "server/orchestrator/tools.py"


def insert_after(lines, predicate, block, once=True):
    out = []
    done = False
    for line in lines:
        out.append(line)
        if (not done or not once) and predicate(line):
            out.extend(block)
            done = True
    if not done:
        raise SystemExit("anchor not found for block starting: " + block[0][:60])
    return out


def insert_before(lines, predicate, block):
    out = []
    done = False
    for line in lines:
        if not done and predicate(line):
            out.extend(block)
            done = True
        out.append(line)
    if not done:
        raise SystemExit("anchor not found for block starting: " + block[0][:60])
    return out


ALL_ENTRIES = [
    '    "UNRESOLVED_CONSOLE_LACKS_NAME",\n',
    '    "UNRESOLVED_POOL_UNREADABLE",\n',
    '    "UNRESOLVED_SHEET_LACKS_ID",\n',
    '    "UNRESOLVED_SHEET_NOT_SUPPLIED",\n',
]

CAUSE_BLOCK = [
    "\n",
    "#: `unresolved_preset` 을 **원인별로** 가르는 닫힌 클래스.\n",
    "#:\n",
    "#: 이 분류를 붙이는 것은 이 층이 아니라 **툴 층**이다 -- 바로 위\n",
    "#: `_HOLD_BLOCK_CLASS` 가 적어 둔 「이 층에서는 안 갈린다」가 그 이유이고,\n",
    "#: 시트(정의)와 콘솔 되읽기(조인)를 **둘 다** 쥔 자리는\n",
    "#: `import_lxseq_cues` 뿐이다. 그런데 어휘는 여기 둔다: `UNRESOLVED_PRESET`\n",
    "#: 을 **세는** 코드와 그것을 **가르는** 어휘가 다른 파일에서 자라면, 한쪽만\n",
    "#: 늘어난 날 두 산출물이 같은 것을 다른 이름으로 부른다.\n",
    "#:\n",
    "#: 셋을 가르는 이유는 처방이 다르기 때문이다 -- 시트를 안 실은 것은 호출\n",
    "#: 인자를 고치면 되고, 시트에 ID 가 없는 것은 시트를 고쳐야 하고, 콘솔에\n",
    "#: 그 이름이 없는 것은 **프리셋을 먼저 만들어야** 한다. 한 덩어리로 세면\n",
    "#: 「어느 하나를 풀면 몇 건이 열리는지」를 아무도 모른다\n",
    "#: (`preset_parser` 의 HOLD_* 닫힌 클래스가 같은 이유로 있다).\n",
    'UNRESOLVED_SHEET_NOT_SUPPLIED = "sheet_not_supplied"\n',
    'UNRESOLVED_SHEET_LACKS_ID = "sheet_lacks_id"\n',
    'UNRESOLVED_CONSOLE_LACKS_NAME = "console_lacks_name"\n',
    'UNRESOLVED_POOL_UNREADABLE = "pool_unreadable"\n',
]

IMPORT_LINE = [
    "        from server.lxseq.cue_mapper import (\n",
    "            PRESET_REF_PATTERN,\n",
    "            UNRESOLVED_CONSOLE_LACKS_NAME,\n",
    "            UNRESOLVED_POOL_UNREADABLE,\n",
    "            UNRESOLVED_SHEET_LACKS_ID,\n",
    "            UNRESOLVED_SHEET_NOT_SUPPLIED,\n",
    "        )\n",
]

SHEET_NAMES_INIT = [
    "        # 시트가 실제로 실어 온 ID -> Name. `preset_slots` 는 **조인에\n",
    "        # 성공한** 것만 담아서, 빠진 참조가 왜 빠졌는지는 그 표만으로 안\n",
    "        # 갈린다. 이 표가 나머지 반쪽이다 -- 아래 unresolved_preset_refs 가\n",
    "        # 둘을 맞대어 원인을 붙인다(t225).\n",
    "        sheet_names_by_kind: dict[str, dict[str, str]] = dict()\n",
]

SHEET_NAMES_DIM_COL_BM = [
    '            sheet_names_by_kind[kind.removeprefix("preset-").upper()] = dict(\n',
    "                id_to_name\n",
    "            )\n",
]

SHEET_NAMES_FX = [
    '                sheet_names_by_kind["FX"] = dict(fx_id_to_name)\n',
]

UNRESOLVED_BLOCK = [
    "        # -- 미해결 프리셋 참조를 **원인별로** 편다 (t225) ------------------\n",
    "        #\n",
    "        # 이 표가 없으면 산출물은 「unresolved_preset 이 Q040/MOVER-U 에\n",
    "        # 있다」까지만 말하고 **어느 참조인지도 왜인지도** 말하지 않는다.\n",
    "        # 그래서 t225 는 콘솔 풀 다섯 개를 손으로 떠서 원인을 갈라야 했다.\n",
    "        # 여기서 갈라 두면 다음 사람은 그 왕복을 안 한다.\n",
    "        #\n",
    "        # 계획에 영향을 주지 않는다 -- 순수하게 산출물 한 칸이다.\n",
    "        unresolved_refs: list[dict[str, object]] = []\n",
    "        seen_refs: set[str] = set()\n",
    "        for record in parsed.records:\n",
    "            if record.is_video_call:\n",
    "                continue\n",
    "            raws = (record.col_raw, record.pos_raw, record.bm_raw, record.fx_raw)\n",
    "            for raw in raws:\n",
    "                text = raw.strip()\n",
    "                # 문법이 아닌 것(빈칸·OFF)은 미해결이 아니다 -- 각각 트래킹과\n",
    "                # 정지 명령이고, 판별은 참조 문법 하나가 한다.\n",
    "                found = PRESET_REF_PATTERN.match(text)\n",
    "                if found is None or text in preset_slots or text in seen_refs:\n",
    "                    continue\n",
    "                seen_refs.add(text)\n",
    "                ref_kind = found.group(1)\n",
    "                names = sheet_names_by_kind.get(ref_kind)\n",
    "                expected = None if names is None else names.get(text)\n",
    '                if ref_kind == "POS":\n',
    "                    # POS 는 시트에 Name 열이 없어 조인이 콘솔 라벨에서만 온다\n",
    "                    # (§10). 그래서 시트 갈래 둘이 정의역 밖이다.\n",
    "                    cause = (\n",
    "                        UNRESOLVED_POOL_UNREADABLE\n",
    '                        if "position_pool" in preset_sheet_errors\n',
    "                        else UNRESOLVED_CONSOLE_LACKS_NAME\n",
    "                    )\n",
    "                elif names is None:\n",
    "                    cause = UNRESOLVED_SHEET_NOT_SUPPLIED\n",
    "                elif expected is None:\n",
    "                    cause = UNRESOLVED_SHEET_LACKS_ID\n",
    "                else:\n",
    "                    cause = UNRESOLVED_CONSOLE_LACKS_NAME\n",
    "                unresolved_refs.append(\n",
    "                    dict(\n",
    "                        ref=text,\n",
    "                        kind=ref_kind,\n",
    "                        cause=cause,\n",
    "                        expected_console_name=expected,\n",
    "                    )\n",
    "                )\n",
    '        unresolved_refs.sort(key=lambda item: str(item["ref"]))\n',
    "\n",
]

PAYLOAD_LINE = [
    '            "unresolved_preset_refs": unresolved_refs,\n',
]


def patch_cue_mapper() -> None:
    lines = CUE_MAPPER.read_text(encoding="utf-8").splitlines(keepends=True)
    lines = insert_after(lines, lambda ln: ln == '    "UNRESOLVED_PRESET",\n', ALL_ENTRIES)
    lines = insert_after(
        lines,
        lambda ln: ln.startswith("UNRESOLVED_PRESET = "),
        CAUSE_BLOCK,
    )
    CUE_MAPPER.write_text("".join(lines), encoding="utf-8")


def patch_tools() -> None:
    lines = TOOLS.read_text(encoding="utf-8").splitlines(keepends=True)
    lines = insert_after(
        lines,
        lambda ln: ln == "        from server.lxseq.cue_mapper import block_report, map_cues\n",
        IMPORT_LINE,
    )
    lines = insert_after(
        lines,
        lambda ln: ln.startswith("        preset_sheet_errors: dict[str, str] = "),
        SHEET_NAMES_INIT,
    )
    lines = insert_after(
        lines,
        lambda ln: ln.strip().startswith("id_to_name = ") and "preset_parsed" in ln,
        SHEET_NAMES_DIM_COL_BM,
    )
    lines = insert_before(
        lines,
        lambda ln: ln == "                fx_pool_path = None\n",
        SHEET_NAMES_FX,
    )
    lines = insert_before(
        lines,
        lambda ln: ln == "        placement = result.placement or result.already_present\n",
        UNRESOLVED_BLOCK,
    )
    lines = insert_after(
        lines,
        lambda ln: ln == '            "preset_slots_resolved": len(preset_slots),\n',
        PAYLOAD_LINE,
    )
    TOOLS.write_text("".join(lines), encoding="utf-8")


def main() -> int:
    patch_cue_mapper()
    patch_tools()
    print("patched")
    return 0


if __name__ == "__main__":
    sys.exit(main())
