#!/usr/bin/env python3
"""사용자 제출용 패치 시트 템플릿 생성 — MVR 없이 같은 정보를 담기 위한 것.

**컬럼은 추측이 아니다.** 실물 MVR(``Demoshow_grandMA3.mvr``, 176대)이 실제로 담고
있던 필드와, grandMA3 매뉴얼이 픽스처 추가에 요구하는 값을 대조해 정했다.

* MA3 요구:      ``patch_add_fixtures.html`` — Insert New Fixtures 마법사
                 (FixtureType · Mode · FID · Patch ``universe.address``)
* MVR 실물 근거: ``GeneralSceneDescription.xml`` -> ``Fixture``
                 (GDTFSpec · GDTFMode · FixtureID · Address · UnitNumber · Color · Matrix)

헤더 이름은 :data:`server.vwx.mvr.MVR_HEADERS`와 **같다**. MVR 경로와 시트 경로가
같은 하류(``columns.resolve_columns`` -> ``address.resolve_all`` -> ``rig``)를 타야
파이프라인이 두 벌이 되지 않는다.

사용::

    uv run python tools/make_patch_template.py                # 템플릿만
    uv run python tools/make_patch_template.py --from-mvr F   # MVR을 시트로 변환
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from server.vwx import mvr  # noqa: E402

SPEC: tuple[tuple[str, str, str, str], ...] = (
    (
        "Channel",
        "필수",
        "제어 채널 번호. 도면과 콘솔을 잇는 **조인 키**이고 콘솔 FID의 기본값이 된다. "
        "이 칸이 비면 그 행은 대조 대상에서 빠진다(중복 패치를 막기 위한 설계).",
        "1",
    ),
    (
        "Fixture ID",
        "권장",
        "콘솔 Fixture ID(FID). Channel과 다르게 쓸 때만 채운다. 중복 금지.",
        "1",
    ),
    (
        "Instrument Type",
        "필수",
        "콘솔 라이브러리의 픽스처 타입 이름. GDTF의 Name과 같게 쓴다.",
        "MAC Encore Performance CLD",
    ),
    (
        "GDTF Fixture Mode",
        "필수",
        "DMX 모드 이름. 타입마다 모드가 여럿이고 채널 수가 다르다.",
        "Basic",
    ),
    (
        "Universe",
        "필수*",
        "DMX 유니버스. MA3 Patch 표기 `universe.address`의 앞자리.",
        "1",
    ),
    (
        "U Address",
        "필수*",
        "유니버스 안의 주소(1~512). Patch 표기의 뒷자리.",
        "1",
    ),
    (
        "Absolute Address",
        "대안",
        "절대 주소 하나로 대신할 수 있다(1부터 연속). Universe/U Address와 택일.",
        "",
    ),
    (
        "GDTF Fixture",
        "권장",
        "`제조사@타입이름` 표기. 있으면 라이브러리 대조가 이름 추측이 아니게 된다.",
        "Martin Professional@MAC Encore Performance CLD",
    ),
    (
        "DMX Footprint",
        "권장",
        "이 모드가 쓰는 채널 수. 주소 충돌을 착수 전에 검산한다.",
        "38",
    ),
    (
        "Fixture Name",
        "권장",
        "콘솔에 표시될 이름.",
        "Spot 1",
    ),
    (
        "Device Type",
        "권장",
        "`Light`만 패치 대상. 액세서리 등은 여기서 걸러진다.",
        "Light",
    ),
    (
        "Position",
        "권장",
        "행잉 포지션 라벨. 사람이 리포트를 읽을 때의 기준이 된다.",
        "Backtruss",
    ),
    ("Unit Number", "권장", "포지션 안의 순번. Channel이 비었을 때의 보조 조인 키.", "1"),
    ("Layer", "선택", "MA3 Layer.", "Backtruss"),
    ("Color", "선택", "젤/색. MA3 Gel Color로 간다.", ""),
    ("UID", "선택", "도면 측 고유 식별자. 재실행 대조에 쓰인다.", ""),
)

HEADERS: tuple[str, ...] = tuple(row[0] for row in SPEC)

#: 예시 3행 — 서로 다른 타입·모드·유니버스를 일부러 섞는다.
SAMPLE_ROWS: tuple[dict[str, str], ...] = (
    {
        "Channel": "1",
        "Fixture ID": "1",
        "Unit Number": "1",
        "Instrument Type": "MAC Encore Performance CLD",
        "GDTF Fixture Mode": "Basic",
        "Universe": "1",
        "U Address": "1",
        "GDTF Fixture": "Martin Professional@MAC Encore Performance CLD",
        "DMX Footprint": "38",
        "Fixture Name": "Spot 1",
        "Device Type": "Light",
        "Position": "Backtruss",
    },
    {
        "Channel": "2",
        "Fixture ID": "2",
        "Unit Number": "2",
        "Instrument Type": "MAC Encore Performance CLD",
        "GDTF Fixture Mode": "Basic",
        "Universe": "1",
        "U Address": "39",
        "GDTF Fixture": "Martin Professional@MAC Encore Performance CLD",
        "DMX Footprint": "38",
        "Fixture Name": "Spot 2",
        "Device Type": "Light",
        "Position": "Backtruss",
    },
    {
        "Channel": "35",
        "Fixture ID": "35",
        "Unit Number": "33",
        "Instrument Type": "Mac Aura XB",
        "GDTF Fixture Mode": "Standard (14 ch)",
        "Universe": "2",
        "U Address": "169",
        "GDTF Fixture": "Martin@Mac Aura XB",
        "DMX Footprint": "14",
        "Fixture Name": "Wash 33",
        "Device Type": "Light",
        "Position": "Backtruss",
    },
)


def rows_from_mvr(path: Path) -> list[dict[str, str]]:
    """MVR을 시트 행으로 변환 — 두 경로가 같은 어휘임을 실증한다."""
    result = mvr.read(path.read_bytes())
    return [{header: record.get(header, "") for header in HEADERS} for record in result.records]


def write_csv(target: Path, rows: list[dict[str, str]]) -> None:
    with target.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(HEADERS))
        writer.writeheader()
        writer.writerows(rows)


def write_xlsx(target: Path, rows: list[dict[str, str]]) -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill

    book = Workbook()
    sheet = book.active
    sheet.title = "Patch"

    grade_fill = {
        "필수": PatternFill("solid", fgColor="FFD9D9"),
        "필수*": PatternFill("solid", fgColor="FFE8D9"),
        "대안": PatternFill("solid", fgColor="FFF4D9"),
        "권장": PatternFill("solid", fgColor="E8F0FE"),
        "선택": PatternFill("solid", fgColor="F2F2F2"),
    }
    for column, (header, grade, _desc, _ex) in enumerate(SPEC, start=1):
        cell = sheet.cell(row=1, column=column, value=header)
        cell.font = Font(bold=True)
        cell.fill = grade_fill[grade]
        cell.alignment = Alignment(horizontal="center")
        sheet.column_dimensions[cell.column_letter].width = max(14, len(header) + 4)
    sheet.freeze_panes = "A2"

    for index, row in enumerate(rows, start=2):
        for column, header in enumerate(HEADERS, start=1):
            sheet.cell(row=index, column=column, value=row.get(header, ""))

    guide = book.create_sheet("읽어주세요")
    guide.column_dimensions["A"].width = 22
    guide.column_dimensions["B"].width = 8
    guide.column_dimensions["C"].width = 92
    guide.append(["컬럼", "등급", "설명"])
    guide["A1"].font = guide["B1"].font = guide["C1"].font = Font(bold=True)
    for header, grade, desc, _example in SPEC:
        guide.append([header, grade, desc])
    guide.append([])
    guide.append(
        [
            "필수*",
            "",
            "Universe + U Address 쌍, 또는 Absolute Address 하나. 둘 중 하나는 있어야 한다.",
        ]
    )
    guide.append(["행 규칙", "", "픽스처 한 대 = 한 행. 합계·소계·집계 행을 넣지 마라."])
    guide.append(
        ["헤더 규칙", "", "첫 행이 헤더다. 제목 행을 그 위에 두어도 되지만 헤더는 한 번만."]
    )
    guide.append(
        ["예시", "", "Patch 시트의 3행이 실물 MVR(Demoshow_grandMA3)에서 그대로 가져온 값이다."]
    )
    for row in guide.iter_rows():
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)

    book.save(target)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-mvr", type=Path, default=None, help="MVR을 시트로 변환")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "docs" / "templates")
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    rows = rows_from_mvr(args.from_mvr) if args.from_mvr else list(SAMPLE_ROWS)
    stem = "patch_from_mvr" if args.from_mvr else "patch_template"

    csv_path = args.out_dir / f"{stem}.csv"
    xlsx_path = args.out_dir / f"{stem}.xlsx"
    write_csv(csv_path, rows)
    write_xlsx(xlsx_path, rows)
    print(f"{csv_path}  ({len(rows)}행)")
    print(f"{xlsx_path}  ({len(rows)}행)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
