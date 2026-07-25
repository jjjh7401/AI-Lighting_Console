from __future__ import annotations

import re
from collections.abc import Sequence

_TARGET_RE = re.compile(
    r"\b(?P<kind>Group|Preset|Cue|Sequence|Executor|Macro|Plugin|Fixture|ShowFile)"
    r"\s+(?P<target>\"[^\"]+\"|'[^']+'|[\w.:-]+)",
    re.IGNORECASE,
)
_MA_OBJECTS = {
    "group": "Group",
    "preset": "Preset",
    "cue": "Cue",
    "sequence": "Sequence",
    "executor": "Executor",
    "macro": "Macro",
    "plugin": "Plugin",
    "fixture": "Fixture",
    "showfile": "ShowFile",
    "unknown": "대상 미확인",
}
_ACTIONS = {
    "store_overwrite": "덮어쓰기",
    "store": "저장",
    "delete": "삭제",
    "blackout": "블랙아웃",
    "off": "오프",
    "run": "실행",
    "modify": "수정",
    "unknown": "명령",
}
_RISK_ORDER = {"info": 0, "caution": 1, "danger": 2}


def build_execution_preview(*, preview_id: str, commands: Sequence[str]) -> dict:
    command_views = [_command_view(command) for command in commands]
    warnings = [
        warning
        for command in commands
        for warning in _warnings_for_command(command)
    ]
    risk_level = _risk_level(warnings)
    return {
        "preview_id": preview_id,
        "summary": f"실행 전 미리보기 — {len(command_views)}개 명령",
        "risk_level": risk_level,
        "commands": command_views,
        "warnings": warnings,
    }


def _command_view(command: str) -> dict:
    target_kind, target = _target(command)
    action = _action(command)
    return {
        "command": command,
        "action": action,
        "target_kind": target_kind,
        "target": target,
        "label": _label(action=action, target_kind=target_kind, target=target),
    }


def _target(command: str) -> tuple[str, str | None]:
    match = _TARGET_RE.search(command)
    if match is None:
        return "unknown", None
    return match.group("kind").lower(), match.group("target").strip("\"'")


def _action(command: str) -> str:
    lower = command.lower()
    if re.search(r"(^|\s)delete(\s|$)", lower):
        return "delete"
    if "blackout" in lower:
        return "blackout"
    if re.search(r"(^|\s)off(\s|$)", lower):
        return "off"
    if re.search(r"(^|\s)store(\s|$)", lower) and "overwrite" in lower:
        return "store_overwrite"
    if re.search(r"(^|\s)store(\s|$)", lower):
        return "store"
    if re.search(r"(^|\s)go\+?(\s|$)", lower) or re.search(r"(^|\s)macro\s+\S+", lower):
        return "run"
    if re.search(r"(^|\s)(at|fade|delay|attribute)(\s|$)", lower) or _has_movement(lower):
        return "modify"
    return "unknown"


def _label(*, action: str, target_kind: str, target: str | None) -> str:
    target_label = _MA_OBJECTS.get(target_kind, target_kind)
    if target is not None:
        target_label = f"{target_label} {target}"
    action_label = _ACTIONS.get(action, action)
    return f"{target_label} {action_label}"


def _warnings_for_command(command: str) -> list[dict]:
    lower = command.lower()
    warnings: list[dict] = []
    action = _action(command)

    if action == "delete":
        warnings.append(
            _warning(
                severity="danger",
                label="삭제 명령",
                detail="대상 객체를 제거할 수 있습니다. 쇼파일 영향 범위를 확인해야 합니다.",
                command=command,
            )
        )
    if action == "store_overwrite":
        warnings.append(
            _warning(
                severity="caution",
                label="덮어쓰기",
                detail="기존 cue, preset, sequence 내용을 바꿀 수 있습니다.",
                command=command,
            )
        )
    if action in ("blackout", "off"):
        warnings.append(
            _warning(
                severity="danger",
                label="블랙아웃/오프",
                detail="현재 출력 또는 재생 중인 executor/sequence가 꺼질 수 있습니다.",
                command=command,
            )
        )
    if re.search(r"\b(strobe|shutter|hz)\b", lower):
        warnings.append(
            _warning(
                severity="danger",
                label="스트로브/셔터 변화",
                detail="스트로브 Hz 또는 셔터 상태가 관객과 카메라에 직접 영향을 줄 수 있습니다.",
                command=command,
            )
        )
    if re.search(r"\b(blinder|audience)\b|객석", lower):
        warnings.append(
            _warning(
                severity="danger",
                label="객석 블라인더",
                detail="관객 방향 고광량 출력 가능성이 있습니다.",
                command=command,
            )
        )
    if _has_movement(lower):
        warnings.append(
            _warning(
                severity="caution",
                label="Pan/Tilt 이동",
                detail="무빙 위치가 급변하거나 객석 방향으로 움직일 수 있습니다.",
                command=command,
            )
        )
    if not _has_movement(lower) and re.search(
        r"(^|\s)(full)(\s|$)|\bat\s+100\b|\bdimmer\s+100\b|\bintensity\s+100\b",
        lower,
    ):
        warnings.append(
            _warning(
                severity="caution",
                label="풀 인텐시티",
                detail="디머 또는 fixture intensity가 100%로 올라갈 수 있습니다.",
                command=command,
            )
        )
    return _dedupe_warnings(warnings)


def _has_movement(lower_command: str) -> bool:
    return re.search(r"\b(pan|tilt)\b", lower_command) is not None


def _warning(*, severity: str, label: str, detail: str, command: str) -> dict:
    return {
        "severity": severity,
        "label": label,
        "detail": detail,
        "command": command,
    }


def _dedupe_warnings(warnings: Sequence[dict]) -> list[dict]:
    deduped: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    for warning in warnings:
        key = (warning["severity"], warning["label"], warning["command"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(warning)
    return deduped


def _risk_level(warnings: Sequence[dict]) -> str:
    level = "info"
    for warning in warnings:
        severity = str(warning.get("severity", "info"))
        if _RISK_ORDER.get(severity, 0) > _RISK_ORDER[level]:
            level = severity
    return level
