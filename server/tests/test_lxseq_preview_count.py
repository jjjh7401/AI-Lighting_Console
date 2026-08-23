"""The preview must not promise fixtures the write path will refuse (card t28).

A run whose width came from the CSV rather than the console is passed WITHOUT
`channels_per_fixture`, `patch_fixtures` refuses it as `footprint_unknown`, and
the whole file stops at that run. The refusal is the intended safety device and
is left alone — what was wrong is that the preview counted those fixtures into
one total, promising N and creating 0.
"""

from __future__ import annotations

from server.lxseq.mapper import TypeModeRead

from .test_lxseq_mapper import _plan, _records


def _mixed_plan():
    """One type unreadable on the console, the rest measured — a MIXED plan.

    Building it from the shared helper keeps it honest: if the fixture data
    ever stops carrying two types, `test_the_input_is_actually_mixed` fails
    instead of the split silently going untested.
    """
    records = _records()
    modes = {}
    unread_type = records[0].fixture_type
    widths = {}
    for record in records:
        widths.setdefault(record.fixture_type, record.channels)
    for name, width in widths.items():
        if name == unread_type:
            modes[name] = TypeModeRead(attempted=True, type_found=False)
        else:
            from server.prechk.mode_read import ModeChoice

            modes[name] = TypeModeRead(
                attempted=True,
                type_found=True,
                modes=(ModeChoice(name=f"{name} std", width=width, slot=1),),
            )
    return _plan(records, mode_reads=modes)


def test_the_input_is_actually_mixed():
    """Vacuity guard: with no unconfirmed run the split proves nothing."""
    plan = _mixed_plan()
    confirmed = [run for run in plan.runs if run.width_confirmed]
    unconfirmed = [run for run in plan.runs if not run.width_confirmed]
    assert confirmed, "no console-measured run — the split is untested"
    assert unconfirmed, "no width-unconfirmed run — the split is untested"


def test_the_two_counts_are_reported_separately():
    plan = _mixed_plan()
    assert plan.write_count_applicable > 0
    assert plan.write_count_width_unconfirmed > 0
    assert plan.write_count_applicable != plan.write_count_planned


def test_the_split_adds_up_to_the_total():
    """Splitting a number that no longer sums is a new defect, not a fix."""
    plan = _mixed_plan()
    assert (
        plan.write_count_applicable + plan.write_count_width_unconfirmed == plan.write_count_planned
    )


def test_every_run_falls_on_exactly_one_side():
    plan = _mixed_plan()
    counted = sum(1 for run in plan.runs if run.width_confirmed) + sum(
        1 for run in plan.runs if not run.width_confirmed
    )
    assert counted == len(plan.runs)


def test_the_count_uses_the_same_predicate_the_write_path_uses():
    """If the counter and `as_tool_arguments` disagree, the preview lies again."""
    plan = _mixed_plan()
    for run in plan.runs:
        passes_width = "channels_per_fixture" in run.as_tool_arguments()
        assert passes_width is run.width_confirmed, run.console_type


def test_a_fully_measured_plan_reports_nothing_unconfirmed():
    """Positive control — the notice must not fire when nothing is at risk."""
    plan = _plan()
    assert plan.write_count_width_unconfirmed == 0
    assert plan.write_count_applicable == plan.write_count_planned


# ---------------------------------------------------------------------------
# 안내 문구 — 조작자가 실제로 읽는 것은 payload 가 아니라 summary_ko 다.
# 필드만 갈라 두고 문장은 총계로 두면, 정직해진 것은 기계뿐이다.
# ---------------------------------------------------------------------------


def _preview_with_one_type_unread(monkeypatch):
    """타입 **하나만** 모드 트리 판독에 실패시켜 실제 도구로 섞인 미리보기를 낸다.

    `type_found=False` 는 폭을 `caller_unverified` 로 떨어뜨린다 — 실기에서 이름은
    맞는데 모드 트리가 답하지 않을 때 나는 바로 그 상태다. 전부 실패시키면 섞이지
    않아 이 갈래가 시험되지 않으므로, 한 타입만 골라 막는다.
    """
    from server.orchestrator import tools as tools_module
    from server.prechk.mode_read import TypeModeRead
    from server.tests.test_lxseq_tool import FakeConsole, _run, _type_widths

    blocked = sorted(_type_widths())[0]
    real = tools_module.read_type_mode_widths

    def fake(state_port, property_port, *, root, type_name):
        if type_name == blocked:
            return TypeModeRead(attempted=True, type_found=False, detail="tree silent")
        return real(state_port, property_port, root=root, type_name=type_name)

    monkeypatch.setattr(tools_module, "read_type_mode_widths", fake)
    payload, _execution, _console, _deploy, _runner = _run(FakeConsole(), action="preview")
    return payload, blocked


def test_the_input_really_has_both_kinds(monkeypatch):
    """공허 방지 — 한쪽만 있는 계획에서는 이 갈래가 시험되지 않는다."""
    payload, _blocked = _preview_with_one_type_unread(monkeypatch)
    assert payload["plan"]["write_count_width_unconfirmed"] > 0
    assert payload["plan"]["write_count_applicable"] > 0


def test_the_summary_announces_the_unconfirmed_count(monkeypatch):
    """사람이 읽는 문장이 위험한 대수를 직접 말해야 한다."""
    payload, _blocked = _preview_with_one_type_unread(monkeypatch)
    summary = payload["summary_ko"]
    assert f"{payload['plan']['write_count_width_unconfirmed']}대" in summary
    assert "폭 미확정" in summary


def test_the_summary_stays_quiet_when_nothing_is_at_risk():
    """대조군 — 전량 확정이면 경고 문장이 붙지 않는다."""
    from server.tests.test_lxseq_tool import _run

    payload, _execution, _console, _deploy, _runner = _run(action="preview")
    assert payload["plan"]["write_count_width_unconfirmed"] == 0
    assert "폭 미확정" not in payload["summary_ko"]
