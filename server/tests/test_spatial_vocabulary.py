from server.spatial.vocabulary import LAYOUT_VOCABULARY, match_explicit_layout


def test_catalog_includes_extended_layout_and_height_terms():
    assert "반원" in LAYOUT_VOCABULARY["semicircle"]
    assert "마름모" in LAYOUT_VOCABULARY["diamond"]
    assert "짝지어" in LAYOUT_VOCABULARY["paired_types"]
    assert "좌-->우" in LAYOUT_VOCABULARY["left_to_right"]
    assert "앞-->뒤" in LAYOUT_VOCABULARY["front_to_back"]
    assert "무대 위" in LAYOUT_VOCABULARY["stage_height"]


def test_matches_whole_rig_grid_with_dimensions_and_spacing():
    match = match_explicit_layout("모든 장비를 4행×10열 그리드로 1.5m 간격 배치해줘")

    assert match is not None
    assert match.preset == "grid"
    assert match.rows == 4
    assert match.columns == 10
    assert match.spacing == 1.5


def test_matches_whole_rig_row_with_default_spacing():
    match = match_explicit_layout("전체 픽스처를 한 줄로 정렬해줘")

    assert match is not None
    assert match.preset == "row"
    assert match.spacing is None


def test_matches_whole_rig_circle_with_radius():
    match = match_explicit_layout("전부 원형 링으로 반지름 6m 배치해줘")

    assert match is not None
    assert match.preset == "circle"
    assert match.radius == 6.0


def test_does_not_match_implicit_target_or_grid_without_dimensions():
    assert match_explicit_layout("장비를 원형으로 배치해줘") is None
    assert match_explicit_layout("모든 장비를 그리드로 배치해줘") is None
