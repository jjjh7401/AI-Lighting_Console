"""t432 선행 측정 — GDTF 파일에서 원색 CIE x·y 가 읽히는지 본다(콘솔 없음, 읽기 전용).

GDTF(DIN SPEC 15800) 는 ``description.xml`` 의 ``PhysicalDescriptions`` 아래에
``Emitters/Emitter@Color`` ("x,y,Y"), ``Filters/Filter@Color``, ``ColorSpace``
(``Mode`` 또는 ``Red/Green/Blue/WhitePoint``) 를 둔다. 이 스크립트는 저장소 안
GDTF 전부에서 그 태그와 속성을 원문 그대로 뽑는다 — 해석하지 않는다.

    uv run python .moai/reports/t432/gdtf_emitters.py <gdtf 또는 mvr> ...
"""

import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

TAGS = ("Emitter", "Filter", "ColorSpace", "AdditionalColorSpaces", "Gamut", "Measurement")


def gdtf_blobs(path: Path):
    with zipfile.ZipFile(path) as archive:
        if path.suffix.lower() == ".gdtf":
            yield path.name, archive.read("description.xml")
            return
        for name in archive.namelist():
            if name.lower().endswith(".gdtf"):
                with zipfile.ZipFile(archive.open(name)) as inner:
                    yield name, inner.read("description.xml")


def report(label: str, blob: bytes) -> None:
    try:
        root = ET.fromstring(blob)
    except ET.ParseError as error:
        # 파서가 거부한 파일은 태그 원문을 정규식으로만 센다(해석 없음).
        import re

        text = blob.decode("utf-8", "replace")
        print(f"== {label}\n   XML ParseError: {error} — regex fallback")
        for tag in TAGS:
            found = re.findall(rf"<{tag}\b[^>]*>", text)
            print(f"   {tag}: {len(found)}")
            for item in found[:8]:
                print(f"     {item}")
        return
    fixture = root.find("FixtureType")
    head = fixture.attrib if fixture is not None else {}
    print(f"== {label}")
    print(f"   FixtureType Name={head.get('Name')!r} Manufacturer={head.get('Manufacturer')!r}")
    counts = {}
    for element in root.iter():
        tag = element.tag.split("}")[-1]
        if tag not in TAGS:
            continue
        counts[tag] = counts.get(tag, 0) + 1
        if counts[tag] <= 8:
            attrs = {
                k: v
                for k, v in element.attrib.items()
                if k
                in (
                    "Name",
                    "Color",
                    "Mode",
                    "Red",
                    "Green",
                    "Blue",
                    "WhitePoint",
                    "DominantWaveLength",
                    "DiodePart",
                )
            }
            print(f"   <{tag}> {attrs}")
    print(f"   counts: {counts or 'none'}")


for arg in sys.argv[1:]:
    for label, blob in gdtf_blobs(Path(arg)):
        report(label, blob)
