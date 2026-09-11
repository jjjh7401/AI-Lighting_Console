"""preset-bm 다섯 행의 ``classify_storability`` 출력 스냅샷.

`capabilities` 를 **주지 않고** 호출한다 — t229 의 「인자 없으면 바이트 동일」
주장을 변경 전후로 같은 명령으로 재기 위한 계측기다. 콘솔 접촉 0.
"""

from pathlib import Path

from server.lxseq.preset_parser import classify_storability, parse_preset_csv

CSV = Path("src/Lighting_Designer/02_RIG팩/LXSEQ_RIG_01_ShowBase_r3.preset-bm.csv")

result = parse_preset_csv(CSV.read_text(encoding="utf-8"))
for record in result.records:
    storable, reasons = classify_storability(record.kind, record.value_raw)
    print(record.preset_id + "\tstorable=" + str(storable))
    for reason in reasons:
        print("\t" + reason.hold_class + ": " + reason.detail)
