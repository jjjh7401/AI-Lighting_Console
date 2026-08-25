"""M1 측정 하네스 — SPEC-COPILOT-UNREQ-001 (카드 t86).

「요청되지 않은 쓰기」 술어의 비용을 갈래 A·B 와 같은 단위로 잰다.
콘솔 발사 없음 — 코퍼스 텍스트와 명령 문자열만 본다.

이 파일이 server/tests/ 에 사는 이유(plan.md §5): 게이트 판정 근거를 CI 밖에
두면 CI 가 봉인을 덮은 척하게 된다.

[HARD] 이 모듈의 테스트는 C 가 통과하는지를 단언하지 않는다. 단언하는 것은
하네스 자신의 성질(대조군이 발사되는가, 세 부류가 갈리는가)뿐이다.
C 의 통과·불통과는 stop_conditions() 가 계산해 기록할 뿐이며 CI 를 빨갛게
만들지 않는다 — acceptance.md AC-UNREQ-005 가 「불통과가 정직하게 기록되면
합격」이라고 못박았다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from server.measurement.corpus import load_corpus
from server.safety.grammar import validate

WRITE_VERBS = ("Store", "Label", "Assign", "Copy")

OBJECT_WORDS = dict(
    그룹="Group",
    프리셋="Preset",
    큐="Cue",
    시퀀스="Sequence",
    페이지="Page",
    매크로="Macro",
    실행기="Executor",
    익스큐터="Executor",
)

_NUMBER = re.compile(r"\d+(\.\d+)?")

REQUESTED = "요청됨"
UNREQUESTED = "요청되지 않음"
UNDECIDABLE = "판정 불가"


@dataclass(frozen=True)
class Verdict:
    scenario_id: str
    task_type: str
    command: str
    object_type: str
    target: str
    label: str


def instruction_numbers(instruction: str) -> set[str]:
    """지시문에 나온 수 토큰. 4.1 은 4.1 로도 4 / 1 로도 센다."""
    found: set[str] = set()
    for match in _NUMBER.finditer(instruction):
        token = match.group(0)
        found.add(token)
        found.update(token.split("."))
    return found


def instruction_object_types(instruction: str) -> set[str]:
    """지시문이 언급한 개체 종류."""
    return set(kw for word, kw in OBJECT_WORDS.items() if word in instruction)


def write_target(command: str) -> tuple[str, str] | None:
    """쓰기 명령의 (개체 종류, 대상 번호). 쓰기가 아니면 None."""
    grammar = validate(command)
    if not grammar.ok:
        return None
    parsed = grammar.parsed
    if not any(parsed.verb.lower() == verb.lower() for verb in WRITE_VERBS):
        return None
    args = [a for a in parsed.args if not a.quoted]
    for i, arg in enumerate(args[:-1]):
        nxt = args[i + 1].text
        if _NUMBER.fullmatch(nxt):
            return arg.text, nxt
    return None


def classify(instruction: str, command: str, deictics: bool) -> Verdict | None:
    """한 명령을 세 부류 중 하나로 판정한다.

    deictics=False 는 「번호만」 범위 — 지시문에 대상 번호가 없으면 전부
    요청되지 않음으로 센다. deictics=True 는 「지시어 포함」 범위 — 번호는
    없지만 개체 종류를 언급했으면 사용자가 선택을 위임한 것으로 보고
    판정 불가로 가른다. 두 범위를 따로 보고하는 이유는 plan.md §5 에 있다.
    """
    target = write_target(command)
    if target is None:
        return None
    object_type, number = target
    if number in instruction_numbers(instruction):
        label = REQUESTED
    elif deictics and object_type in instruction_object_types(instruction):
        label = UNDECIDABLE
    else:
        label = UNREQUESTED
    return Verdict("", "", command, object_type, number, label)


SYNTHETIC = (
    ("synthetic-requested", "프리셋 9.3으로 저장해줘", "Store Preset 9.3", REQUESTED),
    (
        "synthetic-accident",
        "시트 읽어서 뭐가 들었는지 알려줘",
        "Store Preset 2.31",
        UNREQUESTED,
    ),
)


def measure(deictics: bool) -> list[Verdict]:
    """코퍼스 21 시나리오 전체를 한 범위로 판정한다."""
    out: list[Verdict] = []
    for scenario in load_corpus():
        for command in scenario.mock.commands:
            verdict = classify(scenario.instruction, command, deictics)
            if verdict is None:
                continue
            out.append(
                Verdict(
                    scenario.id,
                    scenario.task_type,
                    verdict.command,
                    verdict.object_type,
                    verdict.target,
                    verdict.label,
                )
            )
    return out


def summarize(verdicts: list[Verdict]) -> dict:
    """A·B 와 같은 단위 — 시나리오 수, 명령줄 수, 과업 유형."""
    scenarios = load_corpus()
    by_label: dict = dict()
    for label in (REQUESTED, UNREQUESTED, UNDECIDABLE):
        by_label[label] = [v for v in verdicts if v.label == label]
    summary: dict = dict()
    summary["corpus_scenarios"] = len(scenarios)
    summary["corpus_task_types"] = len(set(s.task_type for s in scenarios))
    summary["write_scenarios"] = len(set(v.scenario_id for v in verdicts))
    summary["write_lines"] = len(verdicts)
    for label, rows in by_label.items():
        summary[label + "_lines"] = len(rows)
        summary[label + "_scenarios"] = len(set(r.scenario_id for r in rows))
        summary[label + "_task_types"] = sorted(set(r.task_type for r in rows))
    return summary


def fully_covered_task_types(verdicts: list[Verdict], label: str) -> list[str]:
    """어떤 과업 유형의 쓰기 명령이 전부 그 라벨이면 그 유형은 통째로 덮인다."""
    by_type: dict = dict()
    for v in verdicts:
        by_type.setdefault(v.task_type, []).append(v)
    return sorted(t for t, rows in by_type.items() if all(r.label == label for r in rows))


def stop_conditions(verdicts: list[Verdict]) -> dict:
    """spec.md D.5 의 두 중단 조건. 측정 전에 확정된 값이다."""
    summary = summarize(verdicts)
    undecidable = int(summary[UNDECIDABLE + "_scenarios"])
    unrequested = int(summary[UNREQUESTED + "_scenarios"])
    covered = fully_covered_task_types(verdicts, UNDECIDABLE)
    one = undecidable >= unrequested
    two = len(covered) >= 1
    result: dict = dict()
    result["condition_1_triggered"] = one
    result["condition_1_detail"] = (
        "판정 불가 " + str(undecidable) + " >= 요청되지 않음 " + str(unrequested)
    )
    result["condition_2_triggered"] = two
    result["condition_2_detail"] = (
        "통째로 덮인 과업 유형 " + str(len(covered)) + "종: " + ", ".join(covered)
    )
    result["verdict"] = "불통과" if (one or two) else "통과"
    return result


class TestHarnessIsNotVacuous:
    """대조군 — 하네스가 판별력을 갖는지. 이것들은 진짜 단언이다."""

    def test_the_synthetic_controls_land_where_expected(self):
        for name, instruction, command, expected in SYNTHETIC:
            verdict = classify(instruction, command, True)
            assert verdict is not None, name
            assert verdict.label == expected, name + ": got " + verdict.label

    def test_the_harness_can_produce_the_requested_label(self):
        labels = set(v.label for v in measure(True))
        assert REQUESTED in labels, "요청됨 을 한 번도 못 내면 하네스가 눈이 먼 것이다"

    def test_a_non_write_command_is_not_classified(self):
        assert classify("아무거나", "Fixture 1 Thru 12", True) is None
        assert classify("아무거나", "At 100", True) is None

    def test_the_two_ranges_are_measured_separately(self):
        numbers_only = summarize(measure(False))
        with_deictics = summarize(measure(True))
        assert numbers_only[UNDECIDABLE + "_lines"] == 0
        assert with_deictics[UNREQUESTED + "_lines"] <= numbers_only[UNREQUESTED + "_lines"]


class TestMeasurementIsRecordedNotAsserted:
    """[HARD] C 의 통과 여부는 단언하지 않는다 — 기록만 한다."""

    def test_the_report_carries_denominators(self):
        summary = summarize(measure(True))
        assert summary["corpus_scenarios"] > 0
        assert summary["corpus_task_types"] > 0

    def test_the_stop_conditions_are_evaluated(self):
        result = stop_conditions(measure(True))
        assert result["verdict"] in ("통과", "불통과")


def render_report() -> str:
    """M1 산출 보고서. `python -m` 실행으로 사람이 읽는 표를 낸다."""
    lines = ["# M1 측정 결과 — SPEC-COPILOT-UNREQ-001 (카드 t86)", ""]
    for deictics in (False, True):
        name = "범위 B (번호 + 지시어)" if deictics else "범위 A (번호만)"
        verdicts = measure(deictics)
        summary = summarize(verdicts)
        lines.append("## " + name)
        lines.append("")
        for key in sorted(summary):
            lines.append("- " + key + ": " + str(summary[key]))
        result = stop_conditions(verdicts)
        lines.append("")
        for key in ("condition_1_detail", "condition_2_detail", "verdict"):
            lines.append("- " + key + ": " + str(result[key]))
        lines.append("")
        lines.append("| 시나리오 | 과업유형 | 명령 | 판정 |")
        lines.append("|---|---|---|---|")
        for v in verdicts:
            row = "| " + v.scenario_id + " | " + v.task_type
            row = row + " | `" + v.command + "` | " + v.label + " |"
            lines.append(row)
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    print(render_report())
