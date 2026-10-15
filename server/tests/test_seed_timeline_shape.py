"""저장소의 모든 시드 타임라인은 화면이 실제로 읽는 키를 갖는다.

화면은 구간 항목과 최상위 키가 있다고 전제한다. 키가 빠지면 Array.map 안에서 죽는다.
그래서 시드는 값이 없어도 키를 두고 빈 값을 넣는다. 필수 키는 Sugar 시드 전체가 아니라
화면이 읽는 키만이다(리드 결정, 2026-10-15).
"""

from __future__ import annotations

import importlib
import pkgutil
from collections.abc import Callable

import server.design as design
from server.design.sugar_timeline import sugar_library_entry

#: 구간 항목에서 화면이 읽는 키.
REQUIRED_SECTION_KEYS = frozenset(
    {
        "palette",
        "fx",
        "accents",
        "intensity",
        "fixture_groups",
        "cue_number",
        "d_level",
        "position",
        "movement",
        "mood",
        "texture",
        "trig_time_seconds",
        "mib",
    }
)
#: 최상위에서 화면이 읽는 키.
REQUIRED_TOP_KEYS = frozenset({"bar_count", "seconds_per_bar"})


def _seed_entry_builders() -> list[Callable[[], dict[str, object]]]:
    """server/design 의 *_timeline 모듈에서 *_library_entry 시드 함수를 모은다."""
    builders: list[Callable[[], dict[str, object]]] = []
    for info in pkgutil.iter_modules(design.__path__):
        if not info.name.endswith("_timeline"):
            continue
        module = importlib.import_module(f"{design.__name__}.{info.name}")
        for name in dir(module):
            if name.endswith("_library_entry"):
                builders.append(getattr(module, name))
    return builders


SEED_BUILDERS = _seed_entry_builders()


def test_discovery_finds_both_known_seeds() -> None:
    names = {builder.__name__ for builder in SEED_BUILDERS}
    assert {"sugar_library_entry", "love_attack_library_entry"} <= names


def test_sugar_reference_seed_carries_every_required_key() -> None:
    timeline = sugar_library_entry()["timeline"]
    assert set(timeline) >= REQUIRED_TOP_KEYS
    for section in timeline["sections"]:
        assert set(section) >= REQUIRED_SECTION_KEYS, section.get("label")


def test_every_seed_timeline_carries_the_keys_the_screen_reads() -> None:
    for builder in SEED_BUILDERS:
        timeline = builder()["timeline"]
        missing_top = sorted(REQUIRED_TOP_KEYS - set(timeline))
        assert not missing_top, f"{builder.__name__} 최상위에 키가 없다: {missing_top}"
        for section in timeline["sections"]:
            missing = sorted(REQUIRED_SECTION_KEYS - set(section))
            assert not missing, f"{builder.__name__} · {section.get('label')}: {missing}"
