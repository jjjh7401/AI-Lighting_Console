"""실기 미확인 어휘 판정 — 「⚠ 실기 미확인」 배지의 유일한 출처 (카드 t579,
REQ-LDBEAT-010 · plan.md M5).

이 모듈은 콘솔에 아무것도 쓰지 않는다. 칸의 ``app_movement``가 §6의 미확인
어휘(circle·발리후·위상 펼침)를 쓰는지 보고, 그 어휘가 **아직 확인되지
않았는지**를 두 데이터 출처로만 가른다:

1. **M1 상태표** — ``grid["probe_results"]``(서버가 progress.md 를 서빙할
   때마다 그 자리에서 읽은 값, 카드 t537). §6 어휘를 다루는 행은 ⑨
   (「circle·발리후·wave」)이다. 그 판정 칸이 「통과」로 시작해야 확인이다.
2. **실측 무빙 기록** — ``beat_grid_measured.is_movement_measured_open``
   (``measured_movements.yaml``). 그 칸의 (그룹·모양·축)이 실기 프로브로
   이미 열렸으면(예: t548 D1 — MOVER-D Tilt 웨이브 + 위상 펼침) 미확인이
   아니다. 송신 게이트(`beat_grid_emit.blocked_m1_items_for_cue`)가 같은
   기록으로 같은 칸을 여는 것과 맞춘 것이다 — 배지와 송신이 서로 다른 말을
   하지 않게.

「확인됨」 목록을 코드 상수로 들고 있지 않는다(카드 t579 배차 규칙). 코드에
있는 것은 「어떤 어휘가 §6 미확인 어휘인가」(SPEC §6 의 정의)와 「그 어휘를
다루는 M1 행 번호」뿐이고, 확인 여부는 늘 위 두 출처에서 읽는다.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from server.design.beat_grid_measured import is_movement_measured_open

__all__ = [
    "PHASE_SPREAD_TERM",
    "UNVERIFIED_VOCABULARY_M1_ITEM",
    "UNVERIFIED_VOCABULARY_SHAPES",
    "unverified_beat_grid_cells",
    "unverified_movement_terms",
]

#: SPEC §6 의 미확인 모양 어휘(REQ-LDBEAT-010 본문 「circle·발리후」). 확인
#: 여부가 아니라 「무엇이 §6 어휘인가」의 정의다 — 확인은 M1 표에서 읽는다.
UNVERIFIED_VOCABULARY_SHAPES: tuple[str, ...] = ("circle", "ballyhoo")

#: REQ-LDBEAT-010 본문 「위상 펼침」 — ``app_movement.phase_spread``가 참인 칸.
PHASE_SPREAD_TERM = "위상 펼침"

#: progress.md M1 표에서 §6 어휘를 다루는 행(「⑨ circle·발리후·wave」).
UNVERIFIED_VOCABULARY_M1_ITEM = 9

#: M1 판정 칸 중 PASS 로 보는 접두사 — ``beat_grid_emit._M1_PASS_PREFIX``와
#: 같은 값이다(그 모듈은 ``beat_grid``를 import 해 여기서 끌어오면 순환이 된다).
_M1_PASS_PREFIX = "통과"


def unverified_movement_terms(
    movement: object,
    probe_results: Mapping[int, str] | Mapping[str, str],
    *,
    group_no: int | None = None,
) -> tuple[str, ...]:
    """``movement``(칸의 ``app_movement``)가 쓰는 §6 미확인 어휘 중 아직 확인되지
    않은 것들을 돌려준다 — 빈 튜플이면 배지를 달지 않는다.

    ``group_no``는 그 칸이 속한 트랙의 **확인된** 그룹 번호다(모르면 ``None`` —
    그러면 실측 기록으로는 열리지 않는다, 지어내지 않음)."""
    if not isinstance(movement, Mapping):
        return ()
    shape = movement.get("shape")
    terms: list[str] = []
    if shape in UNVERIFIED_VOCABULARY_SHAPES:
        terms.append(str(shape))
    if movement.get("phase_spread") is True:
        terms.append(PHASE_SPREAD_TERM)
    if not terms:
        return ()
    status = probe_results.get(UNVERIFIED_VOCABULARY_M1_ITEM)  # type: ignore[call-overload]
    if status is None:
        # JSON 을 거친 격자는 키가 문자열이다.
        status = probe_results.get(str(UNVERIFIED_VOCABULARY_M1_ITEM))  # type: ignore[call-overload]
    if isinstance(status, str) and status.startswith(_M1_PASS_PREFIX):
        return ()
    axes: Sequence[str] = movement.get("axes") or ()
    if is_movement_measured_open(group_no, shape, axes):
        return ()
    return tuple(terms)


def unverified_beat_grid_cells(grid: Mapping[str, object]) -> list[dict[str, object]]:
    """격자 전체에서 「⚠ 실기 미확인」을 달 칸 목록 —
    ``[{"group_name", "bar", "terms"}]``(트랙 순서·마디 순서 그대로).

    M1 판정은 ``grid["probe_results"]``에서만 읽는다(없으면 빈 표 = 전부
    미확인 — 지어낸 PASS 0건)."""
    probe_results = grid.get("probe_results")
    if not isinstance(probe_results, Mapping):
        probe_results = {}
    cells: list[dict[str, object]] = []
    for track in grid.get("tracks") or []:  # type: ignore[union-attr]
        if not isinstance(track, Mapping):
            continue
        group_no = track.get("group_no") if track.get("group_no_confirmed") else None
        if not isinstance(group_no, int) or isinstance(group_no, bool):
            group_no = None
        for cue in track.get("cues") or []:
            if not isinstance(cue, Mapping):
                continue
            terms = unverified_movement_terms(
                cue.get("app_movement"), probe_results, group_no=group_no
            )
            if terms:
                cells.append(
                    {
                        "group_name": track.get("group_name"),
                        "bar": cue.get("bar"),
                        "terms": list(terms),
                    }
                )
    return cells
