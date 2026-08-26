"""t100 — 컬러+디머 복합 프리셋을 `/Universal` 로 저장할 수 있는가 (설계 §4.1).

이 카드가 재는 것은 **하나**다: `Store Preset <pool>.<n> /Universal` 이 **컬러+디머를
담은** 프리셋에서 거절되는가. `fx/instantiate.py:694` 의 live-verified 는 **페이저를
담은** 프리셋 얘기라 그대로 빌려올 수 없고, `session.py:1934` 는 같은 플래그를
「미검증 문법」이라 적어 뒀다. 둘 다 참일 수 있다 — 대상이 다르다.

**여기는 순수 검증이다. 콘솔·네트워크 접촉 0.**

`--approve` 가 도는지의 확인도 여기서 한다. 실기로 확인하지 않는다 — 안전장치가
없으면 그 확인이 곧 사고이기 때문이다(`test_lxseq_preset_safety.py` 모듈 docstring).
"""

from __future__ import annotations

import pytest

from server.presets.store import preset_store_commands
from server.spatial.pointing import SpatialPointingError
from server.tools import t100_universal_composite as harness

POOL = 10
PRESET_NO = 7
GROUP = 3
RGB = (100, 55, 5)
DIM_PCT = 85


def _bundle(**overrides):
    kwargs = dict(
        group=GROUP,
        dimmer_pct=DIM_PCT,
        rgb=RGB,
        pool_no=POOL,
        preset_no=PRESET_NO,
        label="복합 테스트",
    )
    kwargs.update(overrides)
    return harness.composite_bundle(**kwargs)


class TestTheStoreLineComesFromTheOneBuilder:
    """문형을 여기 다시 적으면 `presets/store.py` 와 갈라진다(§1.2 사본 증식 금지).

    프로브가 보태는 것은 **`/Universal` 토큰 하나**여야 한다 — 그게 이 카드가
    재는 대상이기 때문이다. 그 이상을 손으로 적으면 무엇을 쟀는지 흐려진다.
    """

    def test_the_store_line_is_the_builder_output_plus_one_token(self):
        base_store, base_label = preset_store_commands(POOL, PRESET_NO, "복합 테스트")
        bundle = _bundle()
        assert base_store + " /Universal" in bundle, bundle
        assert base_label in bundle, bundle

    def test_no_bare_store_line_survives_beside_it(self):
        """플래그 없는 Store 가 같이 나가면 두 건을 쏘는 것이다 — 「한 건만」이 깨진다."""
        base_store, _ = preset_store_commands(POOL, PRESET_NO, "복합 테스트")
        assert base_store not in _bundle()


class TestTheBundleIsActuallyComposite:
    """복합이 아니면 이 카드는 아무것도 못 잰다 — 디머만 담긴 프리셋을
    `/Universal` 로 쏘는 것은 이미 M4 가 다룬 축이다."""

    def test_the_dimmer_rides_the_selection_line(self):
        assert f"Group {GROUP} ; Attribute 'Dimmer' At {DIM_PCT:g}" in _bundle()

    def test_all_three_colour_channels_ride_one_line(self):
        chain = (
            "Attribute 'ColorRGB_R' At 100 ; Attribute 'ColorRGB_G' At 55 ; "
            "Attribute 'ColorRGB_B' At 5"
        )
        assert chain in _bundle()

    def test_the_bundle_clears_the_programmer_last(self):
        """지우지 않으면 다음 관측이 이번 선택을 물려받는다."""
        assert _bundle()[-1] == "ClearAll"

    def test_the_values_precede_the_store(self):
        bundle = _bundle()
        store_at = next(i for i, c in enumerate(bundle) if c.startswith("Store Preset "))
        colour_at = next(i for i, c in enumerate(bundle) if "ColorRGB_R" in c)
        dimmer_at = next(i for i, c in enumerate(bundle) if "'Dimmer'" in c)
        assert dimmer_at < store_at and colour_at < store_at, bundle


class TestNothingIsGuessed:
    """풀 번호·값은 **재서** 넣는다. 지어내면 엉뚱한 풀을 덮어쓰고, 프리셋 값은
    되읽을 수 없어 복구도 못 한다 — fail-closed 가 맞다."""

    @pytest.mark.parametrize("pool_no", [0, -1])
    def test_a_non_positive_pool_is_refused(self, pool_no):
        with pytest.raises(SpatialPointingError):
            _bundle(pool_no=pool_no)

    @pytest.mark.parametrize("pct", [-1, 101])
    def test_an_out_of_range_dimmer_is_refused(self, pct):
        with pytest.raises(SpatialPointingError):
            _bundle(dimmer_pct=pct)

    @pytest.mark.parametrize("rgb", [(-1, 0, 0), (0, 101, 0), (0, 0, 255)])
    def test_an_out_of_range_colour_is_refused(self, rgb):
        with pytest.raises(SpatialPointingError):
            _bundle(rgb=rgb)

    def test_an_in_range_boundary_is_accepted(self):
        """대조군 — 위 검사들이 「무조건 거절」과 구분되게 한다."""
        assert _bundle(dimmer_pct=100, rgb=(0, 0, 100))

    @pytest.mark.parametrize("group", [0, -2])
    def test_a_non_positive_group_is_refused(self, group):
        with pytest.raises(SpatialPointingError):
            _bundle(group=group)

    def test_a_quoted_label_is_refused_by_the_shared_predicate(self):
        """판정기는 `preset_label_refusal` 하나다 — 여기 사본을 두지 않는다(t97)."""
        with pytest.raises(SpatialPointingError):
            _bundle(label="따옴표'있음")


class TestHarnessRefusesWithoutApprove:
    def test_apply_without_approve_does_not_build_the_console_stack(self, monkeypatch):
        """`--approve` 는 **대답**이 아니라 **행위**를 막아야 한다 — 2026-08-25
        사고가 정확히 그 구분이었다. 콘솔 스택을 세우기 전에 거부한다."""

        def _boom(*_a, **_k):
            raise AssertionError("--approve 없이 콘솔 스택을 세웠다")

        monkeypatch.setattr(harness, "build_console_stack", _boom)
        with pytest.raises(SystemExit) as exit_info:
            harness.main(
                [
                    "--action",
                    "apply",
                    "--listen-port",
                    "9005",
                    "--pool",
                    str(POOL),
                    "--preset-no",
                    str(PRESET_NO),
                    "--group",
                    str(GROUP),
                    "--label",
                    "복합 테스트",
                ]
            )
        assert exit_info.value.code != 0

    def test_probe_only_never_needs_approve(self, monkeypatch):
        """대조군 — 읽기 전용 경로까지 막으면 위 검사가 「apply 를 막는다」가
        아니라 「아무것도 못 한다」와 구분되지 않는다."""

        built: list[bool] = []

        def _fake_stack(*_a, **_k):
            built.append(True)
            raise RuntimeError("stop here — 이 검사는 콘솔에 안 닿는다")

        monkeypatch.setattr(harness, "build_console_stack", _fake_stack)
        with pytest.raises(RuntimeError):
            harness.main(["--action", "probe", "--listen-port", "9005"])
        assert built, "읽기 전용 경로가 콘솔 스택 조립 앞에서 막혔다"
