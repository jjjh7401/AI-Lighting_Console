from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from server.looks.busking import VALUE_LINE_COLLISION
from server.looks.report import COMPLETE, NONE, PARTIAL
from server.looks.schema import AttributeValue, Look
from server.looks.songcue import (
    EXPLICIT_DYNAMICS_REQUIRED,
    ROLE_UNMAPPED,
    UNMAPPED_LOOK,
    SongCueLookSelection,
    build_songcue_bundle,
    parse_sections,
)
from server.looks.songcue_report import (
    DYNAMICS_LOOK_MISSING,
    PROPERTY_UNOBSERVED_NOTE,
    ROLE_UNADDRESSED,
    UNKNOWN_VOCABULARY,
    VALUE_SKIPPED,
    VERDICTS,
    build_songcue_report,
)
from server.tests.busking_fixtures import FULL_RIG
from server.tests.test_looks_instantiate import _groups

_REPORT_MODULE = Path("server/looks/songcue_report.py")
_FORBIDDEN_PROPERTY_CLAIMS = frozenset(
    {
        "cue_fade_verified",
        "cuefade_verified",
        "trig_type_verified",
        "trigtype_verified",
    }
)


def test_report_sections_cover_every_song_section_once_with_closed_verdicts():
    bundle = _mixed_bundle()
    report = build_songcue_report(bundle)
    payload = report.to_dict()
    section_rows = payload["sections"]

    assert len(section_rows) == len(bundle.sections)
    assert sorted(row["index"] for row in section_rows) == [
        section.section.index for section in bundle.sections
    ]
    assert [row["name"] for row in section_rows] == [
        section.section.name for section in bundle.sections
    ]
    assert {row["verdict"] for row in section_rows} <= VERDICTS
    assert frozenset({COMPLETE, PARTIAL, NONE}) == VERDICTS


def test_report_summary_is_section_arithmetic_and_keeps_runtime_remainder_separate():
    bundle = _mixed_bundle()
    statuses = [SimpleNamespace(status="executed_ok") for _command in bundle.commands]
    statuses[-1] = SimpleNamespace(status="not_executed")
    report = build_songcue_report(bundle, outcomes=statuses)
    payload = report.to_dict()
    sections = payload["sections"]
    summary = payload["summary"]

    assert summary["section_count"] == len(sections)
    assert summary["generated_count"] == sum(
        1 for row in sections if row["verdict"] in {COMPLETE, PARTIAL}
    )
    assert summary["unmapped_count"] == sum(
        1
        for row in sections
        if row["reason_kind"] in {UNKNOWN_VOCABULARY, DYNAMICS_LOOK_MISSING, ROLE_UNADDRESSED}
    )
    assert summary["skipped_save_count"] == sum(
        1 for row in sections if row["reason_kind"] == VALUE_SKIPPED
    )
    assert summary["not_executed"] == sum(row["not_executed"] for row in sections)
    assert summary["failed"] == sum(row["failed"] for row in sections)
    assert summary["skipped_save_count"] == 1
    assert summary["not_executed"] == 1
    assert summary["skipped_save_count"] + summary["not_executed"] == 2


def test_unmapped_reason_categories_stay_separate():
    report = build_songcue_report(_mixed_bundle())
    payload = report.to_dict()
    kinds = [section["reason_kind"] for section in payload["unmapped_sections"]]

    assert kinds.count(UNKNOWN_VOCABULARY) == 1
    assert kinds.count(DYNAMICS_LOOK_MISSING) == 1
    assert kinds.count(ROLE_UNADDRESSED) == 1
    assert len(set(kinds)) == 3


def test_skipped_saves_are_section_units_not_unmapped_sections():
    report = build_songcue_report(_mixed_bundle())
    payload = report.to_dict()

    assert len(payload["skipped_saves"]) == 1
    assert payload["skipped_saves"][0]["reason"] == VALUE_LINE_COLLISION
    assert all(section["reason_kind"] != VALUE_SKIPPED for section in payload["unmapped_sections"])


def test_korean_summary_contains_every_section_name_and_uses_public_label_accessors():
    bundle = _mixed_bundle()
    summary = build_songcue_report(bundle).to_korean()
    identifiers = _imported_identifiers(_REPORT_MODULE)

    assert all(section.section.name in summary for section in bundle.sections)
    assert "reason_label" in identifiers
    assert "verdict_label" in identifiers
    assert "_REASON_LABELS" not in identifiers
    assert "_VERDICT_LABELS" not in identifiers


def test_property_unobserved_payload_matches_constant_and_constant_is_not_empty():
    payload = build_songcue_report(_mixed_bundle()).to_dict()

    assert payload["property_unobserved"] == PROPERTY_UNOBSERVED_NOTE
    assert PROPERTY_UNOBSERVED_NOTE.strip()
    assert "CueFade" in PROPERTY_UNOBSERVED_NOTE
    assert "TrigType" in PROPERTY_UNOBSERVED_NOTE
    assert "state snapshots" in PROPERTY_UNOBSERVED_NOTE
    assert "prop command" in PROPERTY_UNOBSERVED_NOTE


def test_requery_confirms_cue_count_and_names_without_property_verification_claims():
    bundle = _mixed_bundle()
    requery_payload = _requery_payload(bundle)
    payload = build_songcue_report(bundle, requery_payload=requery_payload).to_dict()

    assert payload["requery"]["matched"] is True
    assert payload["requery"]["expected"] == payload["requery"]["observed"]
    assert len(payload["requery"]["observed"]) == len(bundle.stored_sections)
    assert _forbidden_property_claims(payload) == []


def test_system_cues_are_excluded_and_offcue_position_is_never_guessed_as_a_number():
    """M7이 라이브에서만 잡은 결함의 회귀 고정.

    `OffCue`는 `cueNo`가 없다. 예전 구현은 나열 위치 `i`로 대체 추정했고, 그 값이
    사용자 큐 1번과 충돌해 `observed != expected`가 되어 `matched`가 **구조적으로**
    거짓이었다. 유닛 픽스처가 시스템 큐를 빠뜨려 그것을 놓쳤다.
    """
    bundle = _mixed_bundle()
    payload = build_songcue_report(bundle, requery_payload=_requery_payload(bundle)).to_dict()
    observed = payload["requery"]["observed"]

    names = [row["name"] for row in observed]
    assert "OffCue" not in names, "cueNo 없는 시스템 큐가 관측 목록에 새어 들어왔다"
    assert "CueZero" not in names, "cueNo=0 시스템 큐가 관측 목록에 새어 들어왔다"
    assert observed, "비공허성 — 필터가 사용자 큐까지 전부 지워 버리면 위 두 assert는 공허하다"
    assert all(row["cue_number"] >= 1 for row in observed)
    assert len({row["cue_number"] for row in observed}) == len(observed), (
        "큐 번호가 중복이면 i 폴백이 되살아난 것이다"
    )
    assert payload["requery"]["matched"] is True


def _mixed_bundle():
    complete, collision, unknown, no_look, no_role = parse_sections(
        (
            ("후렴", "0:00"),
            ("후렴", "0:20"),
            ("Breakdown", "0:40"),
            ("Verse", "1:00"),
            ("Bridge", "1:20"),
        )
    )
    selections = (
        SongCueLookSelection(
            section=complete,
            requested_dynamics=(4,),
            look=_look("chorus", dynamics=4, value=80),
        ),
        SongCueLookSelection(
            section=collision,
            requested_dynamics=(4,),
            look=_look("chorus-copy", dynamics=4, value=80),
        ),
        SongCueLookSelection(
            section=unknown,
            requested_dynamics=(),
            look=None,
            reason=EXPLICIT_DYNAMICS_REQUIRED,
        ),
        SongCueLookSelection(
            section=no_look,
            requested_dynamics=(2,),
            look=None,
            reason=UNMAPPED_LOOK,
        ),
        SongCueLookSelection(
            section=no_role,
            requested_dynamics=(3,),
            look=_look("bridge", dynamics=3, roles=("없는역할",), value=35),
        ),
    )
    bundle = build_songcue_bundle(
        "사랑 노래",
        selections,
        sequences_section=_sequences(1, 2, 4),
        groups_section=_groups(*FULL_RIG),
    )

    assert {skipped.reason for skipped in bundle.skipped} == {
        EXPLICIT_DYNAMICS_REQUIRED,
        UNMAPPED_LOOK,
        ROLE_UNMAPPED,
        VALUE_LINE_COLLISION,
    }
    return bundle


def _look(
    look_id: str,
    *,
    dynamics: int,
    value: float,
    roles: tuple[str, ...] = ("백라이트",),
) -> Look:
    return Look(
        look_id=look_id,
        display_name=look_id,
        genre="rock",
        dynamics=dynamics,
        roles=roles,
        attributes=(AttributeValue("Dimmer", value),),
    )


def _sequences(*numbers: int) -> dict[str, object]:
    return {
        "objects": [{"no": number, "name": f"Sequence {number}"} for number in numbers],
        "truncated": False,
        "total": len(numbers),
    }


def _requery_payload(bundle) -> dict[str, object]:
    """Requery payload shaped like the LIVE console, not an idealised one.

    M0 실측(F-2): 모든 시퀀스는 암묵 시스템 큐 둘을 갖는다 — `OffCue`는 응답기가
    실제 큐 번호를 확신하지 못해 `cueNo`를 **생략**하고, `CueZero`는 `cueNo: 0`이다.
    이 픽스처가 그 둘을 빠뜨렸던 탓에 유닛은 통과하고 M7 라이브에서만
    `requery.matched=false`가 났다. 픽스처는 콘솔이 실제로 주는 모양이어야 한다.
    """
    return {
        "children": [
            {"class": "Cue", "i": 1, "name": "OffCue"},
            {"class": "Cue", "cueNo": 0, "i": 2, "name": "CueZero"},
            *(
                {
                    "class": "Cue",
                    "cueNo": section.cue_number,
                    "i": index,
                    "name": section.cue_name,
                }
                for index, section in enumerate(bundle.stored_sections, start=3)
            ),
        ]
    }


def _imported_identifiers(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    identifiers: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "server.looks.report":
            identifiers.update(alias.name for alias in node.names)
    return identifiers


def _forbidden_property_claims(value: Any) -> list[str]:
    if isinstance(value, dict):
        hits = [key for key in value if key in _FORBIDDEN_PROPERTY_CLAIMS]
        for item in value.values():
            hits.extend(_forbidden_property_claims(item))
        return hits
    if isinstance(value, list):
        hits: list[str] = []
        for item in value:
            hits.extend(_forbidden_property_claims(item))
        return hits
    return []
