"""카드 t496 — 런북 UI 사본(`ui/src/components/runbookServerPayload.json`)이 서버 실출력과
다시 어긋나는 걸 막는 대조 시험.

배경(.moai/reports/t493/verdict.md): 사본이 t458 이후 한 번도 다시 뜨지 않아 구조 80항목이
실출력과 달랐다. UI 쪽 행 수 잠금(`runbookM7Third.test.tsx`)은 새 키 추가를 못 잡는다.

대조 기준은 **구조**다 — 키 집합(목록 원소는 하나로 합쳐 본다)과 목록 길이. 값은 비교하지
않는다. 다르면 오류 문구에 재생성 명령이 실린다.
"""

from __future__ import annotations

import json

from server.tests.runbook_payload_fixture import FIXTURE_PATH, REGEN_COMMAND, build_payload


def key_paths(value: object, path: str = "$") -> set[str]:
    """키 경로 집합. 목록 원소의 키는 `[]` 한 경로로 합친다(원소마다 있는 선택 키도 잡힌다)."""
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            keys.add(f"{path}.{key}")
            keys |= key_paths(child, f"{path}.{key}")
    elif isinstance(value, list):
        for child in value:
            keys |= key_paths(child, f"{path}[]")
    return keys


def list_lengths(value: object, path: str = "$") -> dict[str, int]:
    """목록 길이(행 수). 목록 안의 목록은 원소 번호로 갈라 센다 — 구간마다 길이가 다르다."""
    lengths: dict[str, int] = {}
    if isinstance(value, dict):
        for key, child in value.items():
            lengths |= list_lengths(child, f"{path}.{key}")
    elif isinstance(value, list):
        lengths[path] = len(value)
        for i, child in enumerate(value):
            lengths |= list_lengths(child, f"{path}[{i}]")
    return lengths


def structure_diff(expected: object, actual: object) -> list[str]:
    """`expected`(서버 실출력) 대비 `actual`(사본)의 구조 차이 목록. 같으면 빈 목록."""
    exp_keys, exp_lengths = key_paths(expected), list_lengths(expected)
    act_keys, act_lengths = key_paths(actual), list_lengths(actual)
    lines = [f"사본에 없는 키: {key}" for key in sorted(exp_keys - act_keys)]
    lines += [f"서버에 없는 키(사본에만): {key}" for key in sorted(act_keys - exp_keys)]
    for path in sorted(set(exp_lengths) | set(act_lengths)):
        if exp_lengths.get(path) != act_lengths.get(path):
            lines.append(
                f"목록 길이 {path}: 서버 {exp_lengths.get(path)} · 사본 {act_lengths.get(path)}"
            )
    return lines


def mismatch_message(diff: list[str]) -> str:
    shown = "\n".join(f"  - {line}" for line in diff[:20])
    more = f"\n  … 외 {len(diff) - 20}건" if len(diff) > 20 else ""
    return (
        f"{FIXTURE_PATH.name} 가 서버 실출력과 구조가 다르다({len(diff)}건).\n"
        f"{shown}{more}\n"
        f"다시 뜨기: {REGEN_COMMAND}"
    )


def test_fixture_structure_matches_server_output() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    diff = structure_diff(build_payload(), fixture)
    assert not diff, mismatch_message(diff)


class TestStructureDiffCatches:
    """대조기가 각 어긋남을 실제로 잡는가 — 결함을 넣은 사본으로 쏜다."""

    SERVER = {"a": 1, "rows": [{"q": 1}, {"q": 2}], "nested": {"x": [1, 2, 3]}}

    def test_same_structure_different_values_passes(self) -> None:
        copy = {"a": 99, "rows": [{"q": 7}, {"q": 8}], "nested": {"x": [9, 9, 9]}}
        assert structure_diff(self.SERVER, copy) == []

    def test_new_server_key_missing_from_copy(self) -> None:
        copy = {"rows": [{"q": 1}, {"q": 2}], "nested": {"x": [1, 2, 3]}}
        assert structure_diff(self.SERVER, copy) == ["사본에 없는 키: $.a"]

    def test_key_only_in_copy(self) -> None:
        copy = {**self.SERVER, "old": 1}
        assert structure_diff(self.SERVER, copy) == ["서버에 없는 키(사본에만): $.old"]

    def test_row_count_change(self) -> None:
        copy = {**self.SERVER, "rows": [{"q": 1}]}
        assert structure_diff(self.SERVER, copy) == ["목록 길이 $.rows: 서버 2 · 사본 1"]

    def test_new_key_inside_list_rows(self) -> None:
        server = {"rows": [{"q": 1, "evidence": None}, {"q": 2, "evidence": "x"}]}
        copy = {"rows": [{"q": 1}, {"q": 2}]}
        assert structure_diff(server, copy) == ["사본에 없는 키: $.rows[].evidence"]

    def test_nested_list_length_change(self) -> None:
        copy = {**self.SERVER, "nested": {"x": [1, 2]}}
        diff = structure_diff(self.SERVER, copy)
        assert len(diff) == 1 and diff[0].startswith("목록 길이 $.nested.x")

    def test_message_carries_regen_command(self) -> None:
        message = mismatch_message(["사본에 없는 키: $.beat_grid"])
        assert REGEN_COMMAND in message
        assert "$.beat_grid" in message
