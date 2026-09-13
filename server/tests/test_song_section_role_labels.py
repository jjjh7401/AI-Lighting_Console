"""카드 t391 — 확정 구간의 표시 이름이 중립 ASCII S<n> 이라 곡 하나에 라벨이
중복됐다.

재현(실측, 감독의 실제 곡 17개 라벨): ``S1 S2 S3 S4 S5 S6 S7 S8 S8 S9 S10
S11 S12 S13 S14 S15 S16`` — 8번째·9번째가 둘 다 ``S8`` 이다. 원인은 마디
분할(``_split_sections_for_density``, 카드 t305)이 한 구간을 여러 큐로
쪼갤 때 부모 이름을 그대로 물려주기 때문이다. 콘솔의 큐 목록은 같은
화면에서 ``Intro / Verse 1 / Verse 2 / Chorus 1 ...`` 처럼 역할+회차로
감독이 하나를 짚을 수 있게 이름 붙인다.

고침: ``_confirmed_section_names`` 가 확정 구간의 기본 이름을 역할+회차로
만들고, ``_disambiguate_split_names`` 가 마디 분할로 갈린 큐에만 회차
접미사를 붙인다.
"""

from __future__ import annotations

from server.design.profile import MusicProfile
from server.spatial.position_cuesheet import PositionSheetSection
from server.web.session import (
    _confirmed_section_names,
    _disambiguate_split_names,
    _infer_confirmed_role,
    _split_sections_for_density,
)


class TestConfirmedSectionNames:
    """역할 + 회차 이름 붙이기 — 콘솔 큐 목록과 같은 어휘."""

    def test_first_and_last_are_intro_and_finale_without_a_number(self):
        roles = ["intro", "verse", "chorus", "bridge", "chorus", "finale"]
        names = _confirmed_section_names(roles)
        assert names[0] == "Intro"
        assert names[-1] == "Finale"

    def test_repeated_roles_get_ascending_occurrence_numbers(self):
        roles = ["intro", "verse", "chorus", "verse", "chorus", "finale"]
        names = _confirmed_section_names(roles)
        assert names == ["Intro", "Verse 1", "Chorus 1", "Verse 2", "Chorus 2", "Finale"]

    def test_names_are_all_distinct_on_the_directors_real_song_shape(self):
        """감독의 실제 곡 D 레벨 배열(카드 t393 이 실측한 16개)로 재현."""
        measured_d_levels = (2, 4, 4, 5, 5, 2, 2, 5, 4, 5, 4, 5, 1, 4, 2, 5)
        roles = [
            _infer_confirmed_role(i, list(measured_d_levels)) for i in range(len(measured_d_levels))
        ]
        names = _confirmed_section_names(roles)
        assert len(names) == len(set(names)), f"중복 라벨: {names}"


class TestDisambiguateSplitNames:
    """마디 분할로 갈린 큐만 회차 접미사를 받는다 — 부모 이름은 그대로."""

    def test_unsplit_sections_keep_their_name_byte_identical(self):
        names = ["Intro", "Verse 1", "Chorus 1"]
        origins = [0, 1, 2]
        assert _disambiguate_split_names(names, origins) == names

    def test_a_section_split_into_two_cues_gets_distinct_labels(self):
        """재현 대상: 고침 전에는 이 둘이 바이트 동일 'Chorus 3' 이었다."""
        names = ["Intro", "Verse 1", "Chorus 3", "Chorus 3", "Finale"]
        origins = [0, 1, 2, 2, 3]
        result = _disambiguate_split_names(names, origins)
        assert result == ["Intro", "Verse 1", "Chorus 3 (1/2)", "Chorus 3 (2/2)", "Finale"]
        assert len(result) == len(set(result)), f"여전히 중복: {result}"


class TestSplitSectionsForDensityProducesUniqueLabels:
    """통합 재현 — 실제 마디 분할 경로(`_split_sections_for_density`)를 태워
    긴 구간이 둘 이상의 큐로 갈릴 때 라벨이 갈리는지 확인한다."""

    def test_a_16_bar_section_split_in_two_gets_two_distinct_labels(self):
        # 120 BPM · 4/4 → 마디 하나 2000ms, 8마디 단위 16000ms.
        # 구간 하나(Chorus 3)가 32마디(64000ms) 길이면 4개 큐로 갈린다.
        profile = MusicProfile(bpm=120.0, genre=None)
        sections = [
            PositionSheetSection(name="Intro", start_ms=0, mood="", role="intro"),
            PositionSheetSection(name="Chorus 3", start_ms=10_000, mood="", role="chorus"),
            PositionSheetSection(name="Finale", start_ms=74_000, mood="", role="finale"),
        ]
        # 팔레트가 다양해야(변주 ≥ 유닛 수) 회전으로 안 잘린다 — 여기서는
        # `_section_palette_sizes` 가 자동으로 재므로 role 만 채워 두면 된다.
        expanded, origins, _notes = _split_sections_for_density(sections, profile=profile)
        chorus_labels = [
            section.name for section, origin in zip(expanded, origins, strict=True) if origin == 1
        ]
        assert len(chorus_labels) > 1, "이 구간이 애초에 안 쪼개졌다 — 전제가 깨졌다"
        assert len(chorus_labels) == len(set(chorus_labels)), f"중복 라벨: {chorus_labels}"
        # 쪼개지지 않은 구간(Intro·Finale)의 이름은 바이트 그대로다.
        assert expanded[0].name == "Intro"
        assert expanded[-1].name == "Finale"
