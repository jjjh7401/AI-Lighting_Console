"""같은 종류 사건의 흔들림을 한 프레이즈(4마디) 단위로 모은다 — 사건 잡음 규칙(SPEC-LDRHYTHM-001).

실곡 Too Cool 에서 break 가 1~2마디 간격으로 몰려 나와 구간 경계를 망가뜨렸다. 같은 종류 사건이
프레이즈 안에서 다시 나오면 흔들림으로 보고 첫 마디만 남긴다. LOVE ATTACK 의 실측 사건(킥 진입
4·18·46, 브레이크 33·61·82)은 서로 4마디 이상 떨어져 있어 그대로 남는다.
"""

from server.audio.bar_map import BarEvent, BarFeatures, classify_bar_events

LOUD = 4.0  # 킥 진입 문턱(2.0배)을 넘는 저역
DIP = 0.1  # 브레이크 문턱(0.45배) 아래 저역


def _flat(count: int) -> list[BarFeatures]:
    return [BarFeatures(bar=i, volume_norm=1.0, low_band_norm=1.0) for i in range(1, count + 1)]


def _starts(events: list[BarEvent], kind: str) -> list[int]:
    return [event.start_bar for event in events if event.kind == kind]


def test_break_flicker_inside_one_phrase_keeps_only_the_first_bar() -> None:
    features = _flat(12)
    for bar in (4, 5, 6):
        features[bar - 1] = BarFeatures(bar=bar, volume_norm=1.0, low_band_norm=DIP)
    assert _starts(classify_bar_events(features), "break") == [4]


def test_breaks_a_full_phrase_apart_are_separate_events() -> None:
    features = _flat(12)
    for bar in (4, 8):
        features[bar - 1] = BarFeatures(bar=bar, volume_norm=1.0, low_band_norm=DIP)
    assert _starts(classify_bar_events(features), "break") == [4, 8]


def test_a_gap_shorter_than_a_phrase_is_flicker() -> None:
    features = _flat(12)
    for bar in (4, 7):
        features[bar - 1] = BarFeatures(bar=bar, volume_norm=1.0, low_band_norm=DIP)
    assert _starts(classify_bar_events(features), "break") == [4]


def test_dense_flicker_collapses_to_one_event_per_phrase() -> None:
    features = _flat(34)
    for bar in (6, 7, 8, 16, 22, 24, 31, 32):
        features[bar - 1] = BarFeatures(bar=bar, volume_norm=1.0, low_band_norm=DIP)
    assert _starts(classify_bar_events(features), "break") == [6, 16, 22, 31]


def test_kick_entry_flicker_keeps_only_the_first_bar_of_each_phrase() -> None:
    features = _flat(12)
    for bar in (5, 6, 10):
        features[bar - 1] = BarFeatures(bar=bar, volume_norm=1.0, low_band_norm=LOUD)
    assert _starts(classify_bar_events(features), "kick_entry") == [5, 10]


def test_build_anchors_only_to_kick_entries_that_survive_the_flicker_rule() -> None:
    features = _flat(8)
    for bar, volume in ((1, 1.0), (2, 1.1), (3, 1.2)):
        features[bar - 1] = BarFeatures(bar=bar, volume_norm=volume, low_band_norm=1.0)
    features[3] = BarFeatures(bar=4, volume_norm=1.5, low_band_norm=LOUD)
    features[4] = BarFeatures(bar=5, volume_norm=1.5, low_band_norm=LOUD)
    events = classify_bar_events(features)
    assert _starts(events, "kick_entry") == [4]
    assert [(e.start_bar, e.end_bar) for e in events if e.kind == "build"] == [(1, 3)]


def test_sparse_measured_style_events_all_survive() -> None:
    """LOVE ATTACK 의 실측 사건 간격(킥 진입 4·18·46, 브레이크 33·61·82)은 모두 남는다."""
    features = _flat(83)
    for bar in (4, 18, 46):
        features[bar - 1] = BarFeatures(bar=bar, volume_norm=1.0, low_band_norm=LOUD)
    for bar in (33, 61, 82):
        features[bar - 1] = BarFeatures(bar=bar, volume_norm=1.0, low_band_norm=DIP)
    events = classify_bar_events(features)
    assert _starts(events, "kick_entry") == [4, 18, 46]
    assert _starts(events, "break") == [33, 61, 82]
