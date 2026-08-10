"""MVR(My Virtual Rig) 판독 — 도면 측 입력의 두 번째 경로.

MVR은 GDTF의 짝이 되는 ZIP 컨테이너로, ``GeneralSceneDescription.xml``에 픽스처
전량과 그 픽스처가 참조하는 ``.gdtf`` 파일을 **함께** 담는다. grandMA3는 이 형식을
Patch 메뉴에서 직접 임포트한다(``patch_mvr.html``).

**왜 별도 모듈인가.** Vectorworks 워크시트 경로(:mod:`server.vwx.reader`)는 도면의
타입 *이름*을 콘솔 라이브러리 이름과 맞춰야 한다 — 이 SPEC이 반복해 결함을 낸 지대다.
MVR은 ``GDTFSpec``이 가리키는 **파일 자체를 동봉**하므로 그 추측이 필요 없다.

**출력은 워크시트 경로와 같은 어휘다.** 이 모듈은 :class:`~server.vwx.reader.ReadResult`
와 같은 모양으로, ``columns.ALIAS_TABLE``이 해석하는 헤더 이름의 dict 목록을 낸다.
따라서 하류(``resolve_columns`` -> ``resolve_all`` -> ``build_designed_rig``)가 그대로
쓰인다 — 파이프라인을 두 벌 만들지 않는다.

이 모듈은 예외를 던지지 않는다. 모든 실패는 :class:`~server.vwx.reader.ReadFailure`
목록으로 나간다(``reader.py``와 같은 HARD 제약).
"""

from __future__ import annotations

import io
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass

from server.vwx.reader import ReadFailure, ReadResult

#: MVR 컨테이너의 필수 진입 파일.
SCENE_ENTRY = "GeneralSceneDescription.xml"

#: ``reader.PATH_A``/``PATH_B``와 구별되는 세 번째 입력 경로.
PATH_MVR = "MVR"

READ_FAILURE_NOT_A_CONTAINER = "mvr_not_a_zip_container"
READ_FAILURE_SCENE_MISSING = "mvr_scene_entry_missing"
READ_FAILURE_SCENE_MALFORMED = "mvr_scene_xml_malformed"
READ_FAILURE_GDTF_MISSING = "mvr_gdtf_spec_not_in_container"
READ_FAILURE_ADDRESS_UNREADABLE = "mvr_address_unreadable"

#: DMX 유니버스 하나의 폭. 절대주소를 ``universe`` / ``address``로 가르는 데 쓴다.
UNIVERSE_WIDTH = 512

#: 이 모듈이 내보내는 헤더 — 전부 ``columns.ALIAS_TABLE``이 해석한다.
#: **사용자가 MVR 없이 제출하는 엑셀도 이 이름을 쓴다**(같은 하류를 타기 위해서).
MVR_HEADERS: tuple[str, ...] = (
    "Device Type",
    "Fixture Name",
    "Instrument Type",
    "GDTF Fixture",
    "GDTF Fixture Mode",
    "Fixture ID",
    "Channel",
    "Universe",
    "U Address",
    "Absolute Address",
    "DMX Footprint",
    "Unit Number",
    "Position",
    "Layer",
    "Color",
    "UID",
)


@dataclass(frozen=True)
class FixtureTypeEntry:
    """컨테이너에 동봉된 GDTF 하나에서 읽어낸 타입 정의.

    ``spec``은 ``GeneralSceneDescription.xml``의 ``GDTFSpec`` 원문
    (``제조사@이름``)이고, ``modes``는 모드 이름 -> DMX 채널 수다.
    """

    spec: str
    manufacturer: str
    name: str
    modes: dict[str, int]


def _strip_trailing_nul(data: bytes) -> bytes:
    """MA3가 내보낸 MVR/GDTF의 XML은 끝에 NUL 바이트가 붙어 있다.

    실물 근거: ``Demoshow_grandMA3.mvr``의 ``GeneralSceneDescription.xml``이
    ``b'...</GeneralSceneDescription>\\n\\x00'``으로 끝나고, 동봉된 GDTF 5종의
    ``description.xml``도 전부 같다. 표준 XML 파서는 이것을 ``not well-formed``로
    **거부**한다 — 벗기지 않으면 파일을 아예 열 수 없다.

    앞뒤 공백은 건드리지 않는다. 벗기는 것은 후행 NUL뿐이다.
    """
    return data.rstrip(b"\x00")


def _mode_footprint(mode_element: ET.Element) -> int:
    """DMX 모드가 차지하는 채널 수 — 채널 오프셋의 최댓값.

    ``Offset``이 하나도 없는(가상) 모드는 채널 요소 수로 대신한다. 둘 다 없으면 0을
    내고, 호출부가 그 값을 빈칸으로 내보낸다 — 추측한 숫자를 싣지 않는다.
    """
    offsets: list[int] = []
    channels = list(mode_element.iter("DMXChannel"))
    for channel in channels:
        raw = channel.get("Offset") or ""
        for piece in raw.split(","):
            piece = piece.strip()
            if piece.lstrip("-").isdigit():
                offsets.append(int(piece))
    if offsets:
        return max(offsets)
    return len(channels)


def read_fixture_types(archive: zipfile.ZipFile) -> dict[str, FixtureTypeEntry]:
    """컨테이너에 동봉된 ``.gdtf`` 전량을 ``GDTFSpec`` 키로 읽는다.

    파일 이름이 곧 ``GDTFSpec + '.gdtf'``다(MVR 규약). 열리지 않는 GDTF는 조용히
    건너뛰지 않고 **목록에서 빠진다** — 그 결과 참조가 미해결로 남고 호출부가
    ``mvr_gdtf_spec_not_in_container``로 보고한다.
    """
    entries: dict[str, FixtureTypeEntry] = {}
    for name in archive.namelist():
        if not name.lower().endswith(".gdtf"):
            continue
        try:
            with archive.open(name) as handle:
                nested = zipfile.ZipFile(io.BytesIO(handle.read()))
            description = _strip_trailing_nul(nested.read("description.xml"))
            root = ET.fromstring(description.decode("utf-8", "replace"))
        except (zipfile.BadZipFile, KeyError, ET.ParseError):
            continue
        fixture_type = root.find(".//FixtureType")
        if fixture_type is None:
            continue
        modes = {(mode.get("Name") or ""): _mode_footprint(mode) for mode in root.iter("DMXMode")}
        spec = name[: -len(".gdtf")]
        entries[spec] = FixtureTypeEntry(
            spec=spec,
            manufacturer=fixture_type.get("Manufacturer") or "",
            name=fixture_type.get("Name") or "",
            modes=modes,
        )
    return entries


def bundled_fixture_type_bytes(data: bytes, spec: str) -> bytes | None:
    """MVR이 동봉한 ``spec``의 GDTF 원본 바이트 — 없으면 ``None``.

    **이것이 「라이브러리에 없는 타입」의 첫 번째 답이다.** MVR은 참조만 담는 것이
    아니라 GDTF 파일 자체를 싣는다(실물 확인: ``Demoshow_grandMA3.mvr``에 5종).
    도면이 쓴 **바로 그 버전**이므로 이름으로 검색해 받는 것보다 정확하다.

    바이트를 그대로 돌려준다 — 여기서 디스크에 쓰지 않는다. 어디에 놓을지는
    호출부가 정하고, 콘솔 라이브러리에 놓는 것은 **세션 밖에서** 해야 한다
    (round20 세션 GO 조건 ①: 세션 중 GDTF 임포트 금지).
    """
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        return None
    name = spec if spec.lower().endswith(".gdtf") else f"{spec}.gdtf"
    if name not in archive.namelist():
        return None
    return archive.read(name)


def _child_text(element: ET.Element, tag: str) -> str:
    child = element.find(tag)
    return (child.text or "").strip() if child is not None else ""


def split_absolute(absolute: int) -> tuple[int, int]:
    """절대 DMX 주소를 ``(universe, address)``로 가른다.

    MVR의 ``Address``는 break 기준 **절대** 주소다(실물 확인: 1~1834). MA3의 Patch
    표기는 ``universe.address``이므로(``patch_add_fixtures.html`` — *"Type the DMX
    universe and address separated by a dot (for example, 2.1)"*) 여기서 가른다.

    **이 산술은 저장소에 한 자리뿐이다.** 절대주소를 다루는 모듈이 각자 나누기·
    나머지를 쓰면 그것이 곧 형제 표면이고, 이 SPEC이 열네 라운드 맞은 형태다.
    """
    zero_based = absolute - 1
    return zero_based // UNIVERSE_WIDTH + 1, zero_based % UNIVERSE_WIDTH + 1


def join_absolute(universe: int, address: int) -> int:
    """``universe.address``를 절대 DMX 주소로 되돌린다 — :func:`split_absolute`의 역."""
    return (universe - 1) * UNIVERSE_WIDTH + address


def fits_in_one_universe(absolute: int, width: int) -> bool:
    """``width`` 채널이 유니버스를 **걸치지 않는가**.

    MA3 Patch는 유니버스 안의 주소다 — 걸친 픽스처는 설 자리가 없다.
    """
    first, _ = split_absolute(absolute)
    last, _ = split_absolute(absolute + max(width, 1) - 1)
    return first == last


def next_universe_start(absolute: int) -> int:
    """``absolute``가 속한 유니버스의 **다음** 유니버스 첫 채널."""
    universe, _ = split_absolute(absolute)
    return join_absolute(universe + 1, 1)


def _instrument_type_of(spec: str, entry: FixtureTypeEntry | None) -> str:
    """콘솔 라이브러리에서 찾을 타입 이름.

    GDTF에 실린 ``Name``이 정본이다. GDTF를 못 읽었으면 ``제조사@이름`` 표기에서
    ``@`` 뒤를 쓴다 — 추측이 아니라 MVR 규약이 정한 분해다.
    """
    if entry is not None and entry.name:
        return entry.name
    _, _, tail = spec.partition("@")
    return tail or spec


def read(data: bytes) -> ReadResult:
    """MVR 바이트를 워크시트 경로와 같은 어휘의 레코드로 판독한다."""
    failures: list[ReadFailure] = []
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        return ReadResult(
            records=(),
            encoding="binary",
            path_kind=PATH_MVR,
            header=(),
            read_failures=(
                ReadFailure(
                    row=None,
                    kind=READ_FAILURE_NOT_A_CONTAINER,
                    detail="ZIP 컨테이너가 아니다 — MVR은 ZIP이다",
                ),
            ),
        )

    if SCENE_ENTRY not in archive.namelist():
        return ReadResult(
            records=(),
            encoding="utf-8",
            path_kind=PATH_MVR,
            header=(),
            read_failures=(
                ReadFailure(
                    row=None,
                    kind=READ_FAILURE_SCENE_MISSING,
                    detail=f"{SCENE_ENTRY}가 없다 — MVR 필수 진입 파일",
                ),
            ),
        )

    try:
        scene = ET.fromstring(
            _strip_trailing_nul(archive.read(SCENE_ENTRY)).decode("utf-8", "replace")
        )
    except ET.ParseError as error:
        return ReadResult(
            records=(),
            encoding="utf-8",
            path_kind=PATH_MVR,
            header=(),
            read_failures=(
                ReadFailure(
                    row=None,
                    kind=READ_FAILURE_SCENE_MALFORMED,
                    detail=f"{SCENE_ENTRY} 파싱 실패: {error}",
                ),
            ),
        )

    types = read_fixture_types(archive)
    records: list[dict[str, str]] = []
    unresolved_specs: set[str] = set()

    for layer in scene.iter("Layer"):
        layer_name = layer.get("name") or ""
        for fixture in layer.iter("Fixture"):
            row_index = len(records)
            spec = _child_text(fixture, "GDTFSpec")
            entry = types.get(spec)
            if entry is None and spec:
                unresolved_specs.add(spec)
            mode = _child_text(fixture, "GDTFMode")

            address_element = fixture.find(".//Address")
            raw_address = (
                (address_element.text or "").strip() if address_element is not None else ""
            )
            universe_text = ""
            address_text = ""
            absolute_text = ""
            if raw_address.isdigit():
                absolute = int(raw_address)
                universe, address = split_absolute(absolute)
                universe_text = str(universe)
                address_text = str(address)
                absolute_text = str(absolute)
            else:
                failures.append(
                    ReadFailure(
                        row=row_index,
                        kind=READ_FAILURE_ADDRESS_UNREADABLE,
                        detail=(
                            f"Address가 정수가 아니다: {raw_address!r} — 주소를 추측하지 않는다"
                        ),
                    )
                )

            footprint = ""
            if entry is not None and mode in entry.modes and entry.modes[mode] > 0:
                footprint = str(entry.modes[mode])

            records.append(
                {
                    "Device Type": "Light",
                    "Fixture Name": fixture.get("name") or "",
                    "Instrument Type": _instrument_type_of(spec, entry),
                    "GDTF Fixture": spec,
                    "GDTF Fixture Mode": mode,
                    "Fixture ID": _child_text(fixture, "FixtureID"),
                    "Channel": _child_text(fixture, "FixtureID"),
                    "Universe": universe_text,
                    "U Address": address_text,
                    "Absolute Address": absolute_text,
                    "DMX Footprint": footprint,
                    "Unit Number": _child_text(fixture, "UnitNumber"),
                    "Position": layer_name,
                    "Layer": layer_name,
                    "Color": _child_text(fixture, "Color"),
                    "UID": fixture.get("uuid") or "",
                }
            )

    for spec in sorted(unresolved_specs):
        failures.append(
            ReadFailure(
                row=None,
                kind=READ_FAILURE_GDTF_MISSING,
                detail=(
                    f"GDTFSpec {spec!r}이 컨테이너에 없다 — 타입 이름을 표기에서 "
                    "분해했고 채널 수는 비웠다"
                ),
            )
        )

    return ReadResult(
        records=tuple(records),
        encoding="utf-8",
        path_kind=PATH_MVR,
        header=MVR_HEADERS,
        read_failures=tuple(failures),
    )
