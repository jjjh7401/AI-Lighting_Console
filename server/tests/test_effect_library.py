"""외부 효과 라이브러리 읽기 전용 들여오기와 앱 대응표 검사.

라이브러리는 122종 전량을 센다. 대응표는 가리키는 앱 자산(fx·페이저·칸 종류·움직임 모양)이
실제로 있는지 전부 확인한다 — 이름이 바뀐 자산을 가리키는 줄이 조용히 남지 않게 한다.
콘솔을 건드리지 않는다.
"""

from __future__ import annotations

import json

import pytest
import yaml

from server.design.cell_direction import EFFECT_KINDS
from server.design.phaser_catalog import (
    COLOR_PHASER_SEQUENCE,
    COMBO_PHASER_SEQUENCE,
    DIMMER_PHASER_SEQUENCE,
)
from server.fx.effect_library import (
    DEFAULT_LIBRARY_PATH,
    DEFAULT_MAPPING_PATH,
    MAPPING_REF_KINDS,
    MUSIC_USE_STATUS,
    EffectLibraryError,
    load_app_mapping,
    load_effect_library,
)
from server.fx.loader import load_library_from_dir
from server.spatial.position_fx import POSITION_FX_EFFECTS

_EXPECTED_COUNTS = {
    "POS": 18,
    "DIM": 14,
    "SHU": 4,
    "COL": 8,
    "BEM": 9,
    "PIX": 7,
    "LOOK": 13,
    "MOD": 10,
    "TIM": 8,
    "CUE": 8,
    "SPC": 5,
    "OPS": 18,
}


@pytest.fixture(scope="module")
def library():
    return load_effect_library()


def _app_assets() -> dict[str, set[str]]:
    return {
        "fx": {fx.fx_id for fx in load_library_from_dir().fx},
        "dimmer_phaser": {row[0] for row in DIMMER_PHASER_SEQUENCE},
        "color_phaser": {row[0] for row in COLOR_PHASER_SEQUENCE},
        "combo_phaser": {row[0] for row in COMBO_PHASER_SEQUENCE},
        "cell_kind": set(EFFECT_KINDS),
        "position_fx": set(POSITION_FX_EFFECTS),
    }


def test_library_has_all_122_effects_in_12_categories(library):
    assert library.version == "v1.1"
    assert len(library.effects) == 122
    assert [code for code, _ in library.categories] == list(_EXPECTED_COUNTS)
    for code, count in _EXPECTED_COUNTS.items():
        assert len(library.in_category(code)) == count, code


def test_every_music_use_is_marked_hypothesis(library):
    assert {e.music_use_status for e in library.effects} == {MUSIC_USE_STATUS}
    assert MUSIC_USE_STATUS == "hypothesis"


def test_by_id_and_optional_fields(library):
    circle = library.by_id("POS-01")
    assert circle.category == "POS"
    assert circle.name_en == "Circle"
    assert library.by_id("DIM-02").mbl_impl  # v1.1 이 근거를 붙인 항목
    assert library.by_id("OPS-01").src
    with pytest.raises(KeyError):
        library.by_id("POS-99")


def test_library_note_says_music_use_is_a_hypothesis():
    """자료의 note 가 music_use 를 가설로 적는다 — 로더가 붙이는 상태값의 근거."""
    raw = json.loads(DEFAULT_LIBRARY_PATH.read_text(encoding="utf-8"))
    assert raw["version"] == "v1.1"
    assert "가설" in raw["note"]


def test_mapping_ids_exist_in_library_and_refs_exist_in_app(library):
    mapping = load_app_mapping(library=library)
    assert mapping
    assets = _app_assets()
    missing = [
        (entry.library_id, ref.kind, ref.ref_id)
        for entry in mapping
        for ref in entry.refs
        if ref.ref_id not in assets[ref.kind]
    ]
    assert missing == []
    assert set(assets) == set(MAPPING_REF_KINDS)


def test_mapping_keeps_name_only_and_unverified_marks():
    raw = yaml.safe_load(DEFAULT_MAPPING_PATH.read_text(encoding="utf-8"))
    assert raw["match_basis"] == "name_only"
    assert raw["console_verified"] is False


@pytest.mark.parametrize(
    ("patch", "message"),
    [
        ({"console_verified": True}, "console_verified"),
        ({"match_basis": "measured"}, "match_basis"),
    ],
)
def test_mapping_refuses_verified_claim_without_measurement(tmp_path, patch, message):
    raw = yaml.safe_load(DEFAULT_MAPPING_PATH.read_text(encoding="utf-8"))
    raw.update(patch)
    path = tmp_path / "mapping.yaml"
    path.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")
    with pytest.raises(EffectLibraryError, match=message):
        load_app_mapping(path)


def test_mapping_refuses_unknown_library_id(tmp_path, library):
    raw = yaml.safe_load(DEFAULT_MAPPING_PATH.read_text(encoding="utf-8"))
    raw["entries"].append(
        {"library_id": "POS-99", "refs": [{"kind": "fx", "id": "x", "similarity": "same"}]}
    )
    path = tmp_path / "mapping.yaml"
    path.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")
    with pytest.raises(EffectLibraryError, match="POS-99"):
        load_app_mapping(path, library=library)


def test_mapping_refuses_unknown_ref_kind(tmp_path):
    raw = yaml.safe_load(DEFAULT_MAPPING_PATH.read_text(encoding="utf-8"))
    raw["entries"][0]["refs"][0]["kind"] = "laser"
    path = tmp_path / "mapping.yaml"
    path.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")
    with pytest.raises(EffectLibraryError, match="laser"):
        load_app_mapping(path)


def test_library_refuses_category_mismatch(tmp_path):
    raw = json.loads(DEFAULT_LIBRARY_PATH.read_text(encoding="utf-8"))
    raw["items"][0]["cat"] = "DIM"  # POS-01 을 DIM 으로
    path = tmp_path / "lib.json"
    path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(EffectLibraryError, match="POS-01"):
        load_effect_library(path)
