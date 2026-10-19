"""외부 효과 라이브러리(122종) 읽기 전용 로더와 앱 자산 대응표.

``effect_library_data/lighting_effect_library_v1_1.json`` 은 바깥에서 받은 자료를 바이트 그대로
옮긴 것이다. 파라미터는 숫자 칸 없이 ``ma3`` 글로만 있고, ``music_use`` 는 자료 스스로
"가설"이라고 적는다. 그래서 여기서는 읽기만 하고 항목마다 ``music_use_status="hypothesis"``
를 붙인다. 콘솔 명령을 만들거나 칸 규칙을 바꾸지 않는다.

``app_mapping.yaml`` 은 라이브러리 ID 를 앱이 이미 가진 fx·페이저·칸 종류에 맞춘 표다.
이름 기준이고 실콘솔 미확인이다 — 로더는 그 두 표시가 빠지면 거절한다.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

__all__ = [
    "DEFAULT_LIBRARY_PATH",
    "DEFAULT_MAPPING_PATH",
    "MAPPING_REF_KINDS",
    "MUSIC_USE_STATUS",
    "EffectEntry",
    "EffectLibrary",
    "EffectLibraryError",
    "MappingEntry",
    "MappingRef",
    "load_app_mapping",
    "load_effect_library",
]

_DATA_DIR = Path(__file__).parent / "effect_library_data"
DEFAULT_LIBRARY_PATH = _DATA_DIR / "lighting_effect_library_v1_1.json"
DEFAULT_MAPPING_PATH = _DATA_DIR / "app_mapping.yaml"

#: 자료의 ``note`` 가 music_use 를 가설로 적는다. 영상 검증 전에는 이 값만 쓴다.
MUSIC_USE_STATUS = "hypothesis"

#: 대응표 ref.kind 어휘 — 각 값이 가리키는 앱 자산은 app_mapping.yaml 머리말에 있다.
MAPPING_REF_KINDS: tuple[str, ...] = (
    "fx",
    "dimmer_phaser",
    "color_phaser",
    "combo_phaser",
    "cell_kind",
    "position_fx",
)
_SIMILARITY = ("same", "similar")
_REQUIRED_FIELDS = ("id", "ko", "en", "aka", "desc", "visual_cue", "ma3", "music_use", "cat")


class EffectLibraryError(ValueError):
    """라이브러리나 대응표가 약속한 모양이 아닐 때."""


@dataclass(frozen=True)
class EffectEntry:
    effect_id: str
    category: str
    name_ko: str
    name_en: str
    desc: str
    ma3: str
    music_use: str
    music_use_status: str
    mbl_impl: str | None
    src: str | None


@dataclass(frozen=True)
class EffectLibrary:
    version: str
    categories: tuple[tuple[str, str], ...]  # (코드, 한국어 이름)
    effects: tuple[EffectEntry, ...]

    def by_id(self, effect_id: str) -> EffectEntry:
        for entry in self.effects:
            if entry.effect_id == effect_id:
                return entry
        raise KeyError(effect_id)

    def in_category(self, code: str) -> tuple[EffectEntry, ...]:
        return tuple(e for e in self.effects if e.category == code)


@dataclass(frozen=True)
class MappingRef:
    kind: str
    ref_id: str
    similarity: str


@dataclass(frozen=True)
class MappingEntry:
    library_id: str
    refs: tuple[MappingRef, ...]
    note: str | None


def load_effect_library(path: Path | str = DEFAULT_LIBRARY_PATH) -> EffectLibrary:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    categories = tuple((c["code"], c["ko"]) for c in data["categories"])
    codes = {code for code, _ in categories}
    effects: list[EffectEntry] = []
    seen: set[str] = set()
    for item in data["items"]:
        missing = [k for k in _REQUIRED_FIELDS if k not in item]
        if missing:
            raise EffectLibraryError(f"{item.get('id', '?')}: 필드 없음 {missing}")
        effect_id, cat = item["id"], item["cat"]
        if effect_id in seen:
            raise EffectLibraryError(f"{effect_id}: ID 중복")
        if cat not in codes or not effect_id.startswith(f"{cat}-"):
            raise EffectLibraryError(f"{effect_id}: 카테고리 {cat!r} 가 맞지 않음")
        seen.add(effect_id)
        effects.append(
            EffectEntry(
                effect_id=effect_id,
                category=cat,
                name_ko=item["ko"],
                name_en=item["en"],
                desc=item["desc"],
                ma3=item["ma3"],
                music_use=item["music_use"],
                music_use_status=MUSIC_USE_STATUS,
                mbl_impl=item.get("mbl_impl"),
                src=item.get("src"),
            )
        )
    return EffectLibrary(version=data["version"], categories=categories, effects=tuple(effects))


def _parse_ref(library_id: str, raw: Any) -> MappingRef:
    kind, ref_id, similarity = raw.get("kind"), raw.get("id"), raw.get("similarity")
    if kind not in MAPPING_REF_KINDS:
        raise EffectLibraryError(f"{library_id}: 모르는 ref.kind {kind!r}")
    if not isinstance(ref_id, str) or not ref_id:
        raise EffectLibraryError(f"{library_id}: ref.id 가 비었음")
    if similarity not in _SIMILARITY:
        raise EffectLibraryError(f"{library_id}: similarity {similarity!r}")
    return MappingRef(kind=kind, ref_id=ref_id, similarity=similarity)


def load_app_mapping(
    path: Path | str = DEFAULT_MAPPING_PATH,
    *,
    library: EffectLibrary | None = None,
) -> tuple[MappingEntry, ...]:
    """대응표를 읽는다. ``library`` 를 주면 라이브러리에 없는 ID 를 거절한다."""
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    # 이 두 표시가 대응표의 신뢰 수준이다. 실측 없이 바뀌면 안 된다.
    if data.get("match_basis") != "name_only" or data.get("console_verified") is not False:
        raise EffectLibraryError("대응표는 match_basis: name_only, console_verified: false 여야 함")
    known = {e.effect_id for e in library.effects} if library is not None else None
    entries: list[MappingEntry] = []
    seen: set[str] = set()
    for raw in data["entries"]:
        library_id = raw["library_id"]
        if library_id in seen:
            raise EffectLibraryError(f"{library_id}: 대응표에 두 번 나옴")
        if known is not None and library_id not in known:
            raise EffectLibraryError(f"{library_id}: 라이브러리에 없는 ID")
        refs = tuple(_parse_ref(library_id, r) for r in raw.get("refs") or ())
        if not refs:
            raise EffectLibraryError(f"{library_id}: refs 가 비었음")
        seen.add(library_id)
        entries.append(MappingEntry(library_id=library_id, refs=refs, note=raw.get("note")))
    return tuple(entries)
