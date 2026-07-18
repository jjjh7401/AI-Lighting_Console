"""Measurement corpus loader (M6a — acceptance "문법 오류율 측정 방법" §1).

The corpus YAML is the SSOT of the standard Korean instruction scenarios:
>=20 scenarios covering the 10 representative task types (AC-MVP-001) with
>=2 variants each, including >=3 field-terminology variants (AC-MVP-028 ③).

Each scenario carries a ``mock`` block consumed ONLY by the offline mock
provider (M6a): it scripts the deterministic tool action the mock model takes
for that instruction. Live runs (M6b) send the ``instruction`` text to the
real model and ignore the mock block entirely.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

# The 10 representative programming task types (AC-MVP-001, closed set).
TASK_TYPES = (
    "group_create",
    "preset_store",
    "cue_store",
    "sequence_assign",
    "page_setup",
    "macro_create",
    "effect_apply",
    "fader_control",
    "state_query",
    "plugin_deploy",
)

DEFAULT_CORPUS_PATH = Path(__file__).resolve().parent / "corpus.yaml"

_SCENARIO_KEYS = frozenset({"id", "task_type", "instruction", "field_terms", "mock"})
_MOCK_ACTION_KEYS = ("commands", "query_path", "plugin")


class CorpusError(ValueError):
    """Raised when the corpus file is missing, malformed, or inconsistent."""


@dataclass(frozen=True)
class MockScript:
    """The deterministic offline action for one scenario (mock mode only)."""

    kind: str  # "commands" | "query" | "plugin"
    commands: tuple[str, ...] = ()
    query_path: str = ""
    plugin_name: str = ""
    plugin_source: str = ""


@dataclass(frozen=True)
class Scenario:
    """One standard Korean instruction scenario of the measurement corpus."""

    id: str
    task_type: str
    instruction: str
    mock: MockScript
    field_terms: tuple[str, ...] = field(default=())


def _parse_mock(scenario_id: str, raw: object) -> MockScript:
    if not isinstance(raw, dict):
        raise CorpusError(f"{scenario_id}: 'mock' must be a mapping")
    present = [key for key in _MOCK_ACTION_KEYS if key in raw]
    if len(present) != 1:
        raise CorpusError(
            f"{scenario_id}: 'mock' must define exactly one of {_MOCK_ACTION_KEYS}, got {present}"
        )
    unknown = set(raw) - set(_MOCK_ACTION_KEYS)
    if unknown:
        raise CorpusError(f"{scenario_id}: unknown mock keys {sorted(unknown)}")
    action = present[0]
    if action == "commands":
        commands = raw["commands"]
        if (
            not isinstance(commands, list)
            or not commands
            or not all(isinstance(c, str) and c.strip() for c in commands)
        ):
            raise CorpusError(f"{scenario_id}: mock 'commands' must be non-empty command strings")
        return MockScript(kind="commands", commands=tuple(commands))
    if action == "query_path":
        path = raw["query_path"]
        if not isinstance(path, str) or not path.strip():
            raise CorpusError(f"{scenario_id}: mock 'query_path' must be a non-empty string")
        return MockScript(kind="query", query_path=path)
    plugin = raw["plugin"]
    if not isinstance(plugin, dict):
        raise CorpusError(f"{scenario_id}: mock 'plugin' must be a mapping")
    name = plugin.get("name")
    source = plugin.get("lua_source")
    if not isinstance(name, str) or not name.strip():
        raise CorpusError(f"{scenario_id}: mock plugin 'name' must be a non-empty string")
    if not isinstance(source, str) or not source.strip():
        raise CorpusError(f"{scenario_id}: mock plugin 'lua_source' must be non-empty Lua source")
    return MockScript(kind="plugin", plugin_name=name, plugin_source=source)


def _parse_scenario(raw: object) -> Scenario:
    if not isinstance(raw, dict):
        raise CorpusError("every corpus scenario must be a mapping")
    scenario_id = raw.get("id")
    if not isinstance(scenario_id, str) or not scenario_id.strip():
        raise CorpusError("scenario 'id' must be a non-empty string")
    unknown = set(raw) - _SCENARIO_KEYS
    if unknown:
        raise CorpusError(f"{scenario_id}: unknown scenario keys {sorted(unknown)}")
    task_type = raw.get("task_type")
    if task_type not in TASK_TYPES:
        raise CorpusError(f"{scenario_id}: unknown task_type {task_type!r}")
    instruction = raw.get("instruction")
    if not isinstance(instruction, str) or not instruction.strip():
        raise CorpusError(f"{scenario_id}: 'instruction' must be non-empty Korean text")
    field_terms_raw = raw.get("field_terms", [])
    if not isinstance(field_terms_raw, list) or not all(
        isinstance(t, str) and t.strip() for t in field_terms_raw
    ):
        raise CorpusError(f"{scenario_id}: 'field_terms' must be a list of non-empty strings")
    return Scenario(
        id=scenario_id,
        task_type=task_type,
        instruction=instruction,
        mock=_parse_mock(scenario_id, raw.get("mock")),
        field_terms=tuple(field_terms_raw),
    )


def load_corpus(path: Path | str = DEFAULT_CORPUS_PATH) -> tuple[Scenario, ...]:
    """Load and structurally validate the measurement corpus."""
    path = Path(path)
    if not path.is_file():
        raise CorpusError(f"corpus file not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("scenarios"), list):
        raise CorpusError("corpus must be a mapping with a 'scenarios' list")
    scenarios = tuple(_parse_scenario(raw) for raw in data["scenarios"])
    if not scenarios:
        raise CorpusError("corpus contains no scenarios")
    seen: set[str] = set()
    # instruction text -> the first scenario id that used it (exact-duplicate
    # check after whitespace normalization — NOT fuzzy similarity; a
    # copy-paste mistake that repeats one instruction under a different id
    # would silently double-count that instruction's contribution to the
    # measurement statistics).
    seen_instructions: dict[str, str] = {}
    for scenario in scenarios:
        if scenario.id in seen:
            raise CorpusError(f"duplicate scenario id: {scenario.id}")
        seen.add(scenario.id)
        normalized = " ".join(scenario.instruction.split())
        existing_id = seen_instructions.get(normalized)
        if existing_id is not None:
            raise CorpusError(
                f"duplicate instruction text across scenario ids {existing_id!r} and "
                f"{scenario.id!r}: {scenario.instruction!r}"
            )
        seen_instructions[normalized] = scenario.id
    return scenarios
