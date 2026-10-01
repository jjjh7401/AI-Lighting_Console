"""카드 t501 M3 후속 — climax_return 역할 줄 복원 뒤 세 측정 스크립트
(measure_ac001_8songs.py / measure_dimmer_only_8songs.py /
measure_ac004_8songs.py)를 그대로 재사용해 돌리되, 출력 파일만 `_climaxfix`
접미사로 새로 쓴다 — M4 가 이미 저장해 둔 `ac001_8songs.json`/`.txt`·
`dimmer_only_8songs.json`·`ac004_8songs.json`(climax_return 수정 전 값)을
덮어쓰지 않는다(배차서 지시 — "overwriting the M4 outputs" 금지).

세 모듈 자체는 한 글자도 바꾸지 않는다 — `pathlib.Path.write_text` 를 이
스크립트 실행 동안만 가로채 파일명에 `_climaxfix` 를 끼워 넣는다. 모듈
내부의 `HERE / "<이름>.json"` 경로 조립·측정 로직·출력 포맷은 전부
그대로다(이 스크립트는 "어디에 쓰는가"만 바꾼다, "무엇을 재는가"는 그대로).

실행: uv run python .moai/reports/t501/run_climaxfix_measurements.py
"""

from __future__ import annotations

import pathlib
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

_ORIGINAL_WRITE_TEXT = pathlib.Path.write_text


def _climaxfix_write_text(self: pathlib.Path, data, encoding=None, errors=None, newline=None):
    renamed = self.with_name(f"{self.stem}_climaxfix{self.suffix}")
    return _ORIGINAL_WRITE_TEXT(renamed, data, encoding=encoding, errors=errors, newline=newline)


def main() -> None:
    import measure_ac001_8songs
    import measure_ac004_8songs
    import measure_dimmer_only_8songs

    pathlib.Path.write_text = _climaxfix_write_text
    try:
        print("=== measure_ac001_8songs (climaxfix) ===")
        measure_ac001_8songs.main()
        print("\n=== measure_dimmer_only_8songs (climaxfix) ===")
        measure_dimmer_only_8songs.main()
        print("\n=== measure_ac004_8songs (climaxfix) ===")
        measure_ac004_8songs.main()
    finally:
        pathlib.Path.write_text = _ORIGINAL_WRITE_TEXT


if __name__ == "__main__":
    main()
