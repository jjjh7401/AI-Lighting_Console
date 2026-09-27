"""카드 t460 — PLAN CUE 수정요청 생성기와 파서의 어휘 일치 고정 시험
(SPEC-LDDESIGN-001 AC-LDDESIGN-039).

`ui/src/components/__fixtures__/cueRequestSentences.json` 은 생성기 TS
빌더(`cueRequestSentence.ts`)와 이 시험이 함께 읽는 fixture다 — TS 쪽
(`cueRequestSentence.test.ts`)은 빌더가 그 문장을 정확히 만드는지 재고,
여기서는 그 문장을 실제 파서(`parse_cue_sheet_edit_request`)에 통과시켜
기대한 `changes` 가 나오는지 잰다. 둘이 같은 파일을 읽으므로 한쪽만 고치고
다른 쪽을 안 고치면 이 시험이 잡는다.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from server.design.cue_sheet_edit import parse_cue_sheet_edit_request

_FIXTURE_PATH = (
    Path(__file__).resolve().parents[2]
    / "ui"
    / "src"
    / "components"
    / "__fixtures__"
    / "cueRequestSentences.json"
)


def _load_fixture() -> list[dict[str, object]]:
    return json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))


FIXTURE = _load_fixture()


def test_fixture_has_the_nine_representative_operations() -> None:
    # t470 — t466 이 넓힌 파서 어휘(트래킹·MIB·페이저·포지션) 네 건이 기존
    # 대표 5종에 더해졌다.
    names = {item["name"] for item in FIXTURE}
    assert names == {
        "group-multi-intensity",
        "colour-single-group",
        "effect-preset-name",
        "fade",
        "trans",
        "tracking",
        "mib",
        "phaser",
        "position",
    }


@pytest.mark.parametrize("item", FIXTURE, ids=lambda item: item["name"])
def test_generator_sentence_resolves_to_the_expected_changes(item: dict[str, object]) -> None:
    request = parse_cue_sheet_edit_request(item["sentence"])
    assert request is not None, item["sentence"]
    assert request["cue"] == item["cue"]
    assert request["changes"] == item["expected_changes"]
