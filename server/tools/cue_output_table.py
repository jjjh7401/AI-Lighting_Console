"""큐마다 그룹·장비가 무엇을 켜는가 — 읽기 전용 표(1차 전체 실행 G 단계 측정 수단).

쓰기 0건. 파일은 읽기만 한다(앱 저장본 ``song_timeline.json``·감사 기록 ``audit-*.jsonl``).
``--read-console`` 을 주면 응답기의 **읽기 문법만**(``state``·``props``) 쓴다 — 큐·프리셋이 실제로
있는가, 그룹 소속 장비, 장비 기종 속성. ``exec`` 은 한 번도 보내지 않는다.

🔴 이 표는 실제 출력(DMX)이 아니다 — :data:`server.design.cue_output_table.LIMIT_NOTE`.

예::

    uv run python -m server.tools.cue_output_table \\
        --store "~/Library/Application Support/GrandMA3 Copilot/song_timeline.json" \\
        --audit server/audit_logs/audit-20261017.jsonl --listen-port 9005 --out /tmp/cue-table.md

    # 콘솔까지 읽는다(앱 서버가 같은 회신 포트를 쥐고 있지 않을 때). ``--listen-port`` 는 도구
    # 규약상 늘 적는다(기본값 없음) — 파일만 읽을 때는 소켓을 열지 않는다:
    uv run python -m server.tools.cue_output_table --store … --audit … \\
        --read-console --listen-port 9005 --port 8000
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path

from server.design.cue_output_table import (
    fixture_findings,
    planned_cue_rows,
    render_markdown,
    stored_presets_from_audit,
)
from server.tools.probe_preflight import add_listen_port_argument
from server.tools.tree_identity import assert_same_tree

assert_same_tree(__file__)

DEFAULT_STORE = (
    Path.home() / "Library" / "Application Support" / "GrandMA3 Copilot" / "song_timeline.json"
)


def _read_audit(paths: Iterable[Path]) -> list[dict]:
    """감사 기록 여러 파일을 시각 순으로 — 깨진 줄은 건너뛴다."""
    entries: list[dict] = []
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if isinstance(entry, dict):
                    entries.append(entry)
    entries.sort(key=lambda entry: str(entry.get("ts") or ""))
    return entries


def _allocation_for(data: Mapping[str, object], timeline: Mapping[str, object]) -> dict | None:
    """반영 기록 열쇠는 ``(song_title, sequence_number)`` — 지금 제목으로 못 찾으면 격자가 기억하는
    원래 곡 제목으로 다시 찾는다(``session`` 의 원래 열쇠 규칙과 같다)."""
    allocations = data.get("beat_grid_allocations")
    if not isinstance(allocations, Mapping):
        return None
    grid = timeline.get("beat_grid")
    titles = [timeline.get("song_title")]
    if isinstance(grid, Mapping):
        titles.append(grid.get("song_title"))
    for title in titles:
        key = json.dumps([title, timeline.get("sequence_number")], ensure_ascii=False)
        found = allocations.get(key)
        if isinstance(found, dict):
            return found
    return None


def _children(port, path: str) -> list[dict]:
    """자식 목록을 끝까지 페이징한다 — 단발 조회는 잘린다(t230 §4.2)."""
    out: list[dict] = []
    offset = 0
    while True:
        payload = port.query_state(path, offset=offset)
        window = list(payload.get("children") or [])
        out.extend(window)
        if not payload.get("truncated") or not window:
            return out
        offset += len(window)


def _props(port, path: str, names: Sequence[str]) -> dict[str, str]:
    payload = port.query_properties(path, list(names))
    return {
        str(read.get("n")): str(read.get("v"))
        for read in payload.get("reads") or []
        if read.get("ok")
    }


def _cue_no(value: object) -> int | None:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return int(number) if number.is_integer() else None


def read_console_cues(port, sequences: Iterable[int], root: str) -> dict[tuple[int, int], str]:
    """시퀀스마다 큐 목록 → (시퀀스, 큐 번호) -> 「있음 · 데이터 있음/없음 · 크기」."""
    found: dict[tuple[int, int], str] = {}
    for sequence in sorted(set(sequences)):
        path = f"{root}/{sequence}"
        try:
            cues = _children(port, path)
        except Exception as error:  # noqa: BLE001 — 판독 실패는 표에 사유로 남긴다
            found[(sequence, -1)] = f"시퀀스 못 읽음({type(error).__name__})"
            continue
        for cue in cues:
            number = _cue_no(cue.get("cueNo"))
            slot = cue.get("i")
            if number is None or slot is None:
                continue
            cue_path = f"{path}/{slot}"
            try:
                parts = _children(port, cue_path)
                part = parts[0].get("i") if parts else None
                props = (
                    _props(port, f"{cue_path}/{part}", ("OWNDATAPRESENT", "MEMORYFOOTPRINT"))
                    if part is not None
                    else {}
                )
            except Exception as error:  # noqa: BLE001
                found[(sequence, number)] = f"있음 · 파트 못 읽음({type(error).__name__})"
                continue
            data = props.get("OWNDATAPRESENT")
            size = props.get("MEMORYFOOTPRINT")
            state = {"true": "데이터 있음", "false": "데이터 없음"}.get(str(data), "데이터 모름")
            found[(sequence, number)] = f"있음 · {state}" + (f" · {size}" if size else "")
    return found


def read_console_presets(port, slots: Iterable[str], root: str) -> dict[str, str]:
    """프리셋 칸(``pool.slot``) -> 「있음 '이름' · 데이터 …」 / 「콘솔에 없음」."""
    found: dict[str, str] = {}
    by_pool: dict[str, set[str]] = {}
    for slot in slots:
        pool, _, number = slot.partition(".")
        by_pool.setdefault(pool, set()).add(number)
    for pool, numbers in by_pool.items():
        try:
            listing = {str(child.get("i")): child for child in _children(port, f"{root}/{pool}")}
        except Exception as error:  # noqa: BLE001
            for number in numbers:
                found[f"{pool}.{number}"] = f"풀 못 읽음({type(error).__name__})"
            continue
        for number in numbers:
            child = listing.get(number)
            if child is None:
                found[f"{pool}.{number}"] = "콘솔에 없음"
                continue
            try:
                data = _props(port, f"{root}/{pool}/{number}", ("OWNDATAPRESENT",)).get(
                    "OWNDATAPRESENT"
                )
            except Exception:  # noqa: BLE001
                data = None
            state = {"true": "데이터 있음", "false": "데이터 없음"}.get(str(data), "데이터 모름")
            found[f"{pool}.{number}"] = f"있음 '{child.get('name')}' · {state}"
    return found


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--store", type=Path, default=DEFAULT_STORE, help="앱 저장본 JSON")
    parser.add_argument("--audit", type=Path, nargs="+", required=True, help="감사 기록 jsonl")
    parser.add_argument("--out", type=Path, help="표를 쓸 파일(없으면 표준 출력)")
    parser.add_argument("--read-console", action="store_true", help="응답기 읽기로 존재 확인")
    # 회신 포트는 공용 선언 하나로만 받는다(기본값 없음). 파일만 읽을 때는 쓰지 않는다.
    add_listen_port_argument(parser)
    parser.add_argument("--host", default="127.0.0.1", help="콘솔 OSC 입력 호스트")
    parser.add_argument("--port", type=int, default=8000, help="onPC OSC 입력 포트")
    args = parser.parse_args(argv)

    data = json.loads(args.store.expanduser().read_text(encoding="utf-8"))
    timeline = data.get("timeline") if isinstance(data, Mapping) else None
    if not isinstance(timeline, Mapping) or not isinstance(timeline.get("beat_grid"), Mapping):
        print("저장본에 타임라인·격자가 없습니다.", file=sys.stderr)
        return 1
    allocation = _allocation_for(data, timeline)
    rows = planned_cue_rows(timeline["beat_grid"], allocation)
    presets = stored_presets_from_audit(_read_audit(args.audit))
    notes = [
        f"곡 「{timeline.get('song_title')}」 · 큐 {len(rows)}개 · "
        f"감사 기록 {len(args.audit)}개 파일 · 저장 줄로 되살린 프리셋 {len(presets)}개",
    ]
    if allocation is None:
        notes.append("반영 기록이 없어 시퀀스·큐 번호를 비웠다(번호를 지어내지 않음).")

    console_cues = console_presets = None
    findings = []
    if args.read_console:
        # 콘솔 접촉 경로만 늦게 들여온다 — 파일만 읽는 쓰임새가 소켓을 열지 않게.
        from server.design.beat_grid_stage import read_beat_grid_stage
        from server.design.rig_capability_read import read_design_rig
        from server.orchestrator.tools import DEFAULT_RIG_CONTEXT_PATHS
        from server.safety.bootstrap import build_console_stack
        from server.safety.console import LinkTimeouts

        stack = build_console_stack(
            send_host=args.host,
            send_port=args.port,
            receive_host="127.0.0.1",
            receive_port=args.listen_port,
            audit_dir=None,
            timeouts=LinkTimeouts(state_query_seconds=6.0),
            attempt_session_backup=False,
        )
        port = stack.gate.state_port
        try:
            paths = DEFAULT_RIG_CONTEXT_PATHS
            console_cues = read_console_cues(
                port,
                (row.sequence_number for row in rows if row.sequence_number is not None),
                paths["sequences"],
            )
            console_presets = read_console_presets(
                port, {slot for row in rows for slot in row.presets}, paths["preset_pools"]
            )
            names = sorted({row.group_name for row in rows})
            stage = read_beat_grid_stage(
                port,
                fixtures_path=paths["fixtures"],
                groups_path=paths["groups"],
                track_names=names,
            )
            members = {
                str(group.get("group_name")): list(group.get("member_fids") or [])
                for group in stage.get("groups") or []
                if isinstance(group, Mapping) and group.get("complete") is True
            }
            notes.extend(f"무대 판독: {reason}" for reason in stage.get("unread") or [])
            rig = read_design_rig(port, fixture_types_root=paths["fixture_types"])
            capabilities = rig.capabilities.fixtures if rig.capabilities is not None else {}
            if rig.gap:
                notes.append(f"장비 판독이 전수가 아님: {rig.gap} {rig.detail}".strip())
            by_upper = {name.upper(): name for name in names}
            members = {by_upper.get(name.upper(), name): fids for name, fids in members.items()}
            findings = fixture_findings(rows, presets, members, capabilities)
        finally:
            stack.stop()

    text = render_markdown(
        rows,
        presets,
        findings=findings,
        console_cues=console_cues,
        console_presets=console_presets,
        notes=notes,
    )
    if args.out is not None:
        args.out.write_text(text, encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
