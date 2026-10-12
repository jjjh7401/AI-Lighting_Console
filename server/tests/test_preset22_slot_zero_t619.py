"""카드 t619(SPEC-LDBEAT-001, REQ-LDBEAT-015(h) 계속) — 혼합 효과 풀 22
번호대(``mixed_all``)가 슬롯 0("22.0")을 새 프리셋 번호로 내주던 결함.

실측(실기 콘솔, 이 카드): 풀 22에는 슬롯 1 "Piano Solo" 하나만 있었다.
`Store Preset 22.0`을 보내자 슬롯 0은 그대로 비어 있고, 다음 빈 자리인
슬롯 2에 "Preset 2"가 새로 생겼다 — 콘솔에는 슬롯 0이 없다. 앱이 기록한
번호("22.0")와 콘솔이 실제로 저장한 번호("22.2")가 어긋난 것이다.

원인: `preset_pools.yaml`의 ``mixed_all`` 시작이 ``"22.0"``이고,
`first_free_preset_number`가 정책의 시작 슬롯부터 그대로 돌았다. 고침은
두 겹이다 — 출하 정책을 ``"22.1"``로 바꾸고, 정책이 낡아 슬롯 0을 선언해도
함수가 슬롯 0을 절대 내주지 않는다. 콘솔 접촉: 0건 — 순수 함수만 부른다."""

from __future__ import annotations

from server.design.beat_grid_edit import load_preset_pool_policy
from server.design.beat_grid_presets import first_free_preset_number


def test_shipped_policy_skips_slot_zero_when_piano_solo_is_the_only_preset() -> None:
    # 실측 그대로: 풀 22에는 슬롯 1 "Piano Solo"만 있다. 슬롯 0은 콘솔에
    # 없는 자리라 후보가 아니다 — 다음 빈 자리는 슬롯 2다.
    policy = load_preset_pool_policy()
    result = first_free_preset_number(
        "mixed",
        policy=policy,
        grid={"tracks": []},
        console_children={22: {1: "Piano Solo"}},
    )
    assert result == ("22.2", None, None)


def test_shipped_policy_offers_slot_one_on_empty_pool() -> None:
    # 빈 풀이라도 첫 후보는 슬롯 1이다 — "22.0"을 내주지 않는다.
    policy = load_preset_pool_policy()
    result = first_free_preset_number(
        "mixed",
        policy=policy,
        grid={"tracks": []},
        console_children={22: {}},
    )
    assert result == ("22.1", None, None)


def test_stale_policy_declaring_slot_zero_never_offers_it() -> None:
    # 정책이 낡아 시작을 "22.0"으로 선언해도 함수가 슬롯 0을 건너뛴다 —
    # 데이터 파일 하나가 되돌아가도 같은 결함이 다시 나지 않게 하는 잠금.
    policy = {"confirmed": False, "pools": {"mixed_all": {"start": "22.0", "end": "22.99"}}}
    result = first_free_preset_number(
        "mixed",
        policy=policy,
        grid={"tracks": []},
        console_children={22: {1: "Piano Solo"}},
    )
    assert result == ("22.2", None, None)


def test_shipped_mixed_band_starts_at_slot_one() -> None:
    # 출하 데이터 자체도 슬롯 1부터 시작한다.
    assert load_preset_pool_policy()["pools"]["mixed_all"]["start"] == "22.1"
