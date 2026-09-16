"""frozen artifact bytes 와 manifest 를 내는 한 자리 (C6).

이 층이 내는 것은 **bytes 와 manifest 뿐**이고 발화가 아니다 — OSC 를 만지지 않는다
(`spec.md §4.1`: *"frozen artifact 는 bytes 이고 발화가 아니다"*). 보내는 것은 형제
`SPEC-LDRECV-001` 의 일이다.

**무엇을 내지 않는가가 이 모듈의 핵심이다.**

이 저장소가 실측한 페이드는 큐 단위 스칼라 하나뿐이다 —
``Store … Cue <n> '<이름>' CueFade <초>`` (프로브 T11 §2/§4,
``server/design/cue_fade.py`` 독스트링). ``Property 'Fade'`` 는 **금지**이며
(``docs/handoff/2026-08-15-timeline-workflow-handoff.md:19``), 축별 delay/fade 통로는
**관측 0건**이다(``acceptance.md`` §3 착수 실측 ``cde2744``:
``PanFade``·``TiltFade``·``IndividualFade``·``AttributeFade``·``delay_ms`` 각 0건).

그래서 축별 timing 요청이 오면 이 모듈은 **거부한다.** 조용히 quantize·clamp·drop·
대체하지 않는다 — ``AC-LDPLUGIN-008`` 이 raw 문자열·silent clamp·drop·substitution 을
전부 거절 대상으로 못박았다. 관측 없이 축별 문법을 여기에 적는 것이 이 SPEC 전체가
막아 온 실패다. 여는 것은 실기 프로브의 일이고, 그 자리는
``validate/capability.py`` 의 ``AXIS_TIMING_OBSERVED`` 다.

**digest 는 받는다, 만들지 않는다.** ``plan_digest``·``context_digest``·
``compiler_build_digest`` 는 인자로 온다 — 저장·CAS·digest 계산은 형제
``SPEC-LDSTORE-001`` 의 범위다(``spec.md §4.1``). 예외는 ``artifact_sha256`` 하나로,
그 bytes 를 만드는 것이 이 모듈이므로 자기가 만든 것만 해시한다(계약 §209:
*"서버가 실제 보낼 frozen artifact bytes 를 해시"*).

``compiled_digest`` 는 **여기서 만들지 않는다.** manifest 객체 전체를 정규화해
해시해야 하고, JCS 정규화를 표준 라이브러리로 근사하면 깨진다 — 지어내는 대신
호출자에 남긴다.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

__all__ = [
    "CUE_FADE_KEYWORD",
    "PLAYBACK_MODES",
    "AxisTimingUnsupportedError",
    "emit_compiled",
    "store_with_measured_fade",
]

#: 실측된 유일한 페이드 키워드.
CUE_FADE_KEYWORD = "CueFade"

#: 계약이 허용하는 playback 둘. timecode mode 와 자동 GO 는 여기 없다.
PLAYBACK_MODES = ("manual_go", "trig_time")

_UNOBSERVED_AXIS_REASON = (
    "축별 delay/fade 를 보존하는 emitter 가 실측되지 않았습니다(관측 0건). 이 층은 "
    "요청 값을 조용히 quantize·clamp·drop·대체하지 않으므로, 관측 전에는 artifact 를 "
    "만들지 않고 거부합니다. 여는 것은 실기 프로브이며 그 자리는 "
    "validate/capability.py 의 AXIS_TIMING_OBSERVED 입니다."
)


class AxisTimingUnsupportedError(ValueError):
    """축별 timing 을 담은 action — 실측 전에는 artifact 를 만들 수 없다."""


def store_with_measured_fade(store: str, fade_seconds: float | None) -> str:
    """``Store …`` 줄에 실측된 형태의 페이드를 붙인다. ``None`` 이면 **받은 줄 그대로**.

    ``None`` 갈래가 항등인 것이 무회귀 성질이다 — 페이드 없는 입력이 내는 문면은
    이 파일이 생기기 전과 같다.

    ``:g`` 포맷은 실측 문면(``CueFade 2``)과 같은 모양을 내기 위한 것이다. ``2.0`` 이
    ``2`` 로, ``0.2`` 가 ``0.2`` 로 나간다.

    ``server/design/cue_fade.py`` 에 같은 문법을 조립하는 자리가 있고, 이 모듈은 그것을
    **import 하지 않는다**(``plan.md §3`` 이 그 경로를 읽기 전용 참고 자료로 정했다).
    두 벌이 조용히 갈라지는 것을 막는 것은 ``test_director_emit.py`` 의 문면 대조
    시험이다 — 한쪽만 바뀌면 그 시험이 깨진다.
    """
    if fade_seconds is None:
        return store
    if isinstance(fade_seconds, bool) or not isinstance(fade_seconds, int | float):
        raise ValueError(f"cue fade must be a number: {fade_seconds!r}")
    if fade_seconds < 0:
        raise ValueError(f"cue fade must be non-negative: {fade_seconds!r}")
    return f"{store} {CUE_FADE_KEYWORD} {fade_seconds:g}"


def _requested_axes(action: dict[str, Any]) -> list[str]:
    """action 이 실제로 축별 timing 을 든 축. 없으면 빈 목록이다."""
    timing = action.get("timing")
    return sorted(timing) if isinstance(timing, dict) and timing else []


def _artifact_bytes(destination: str, cue_number: int, cue: dict[str, Any]) -> bytes:
    """한 cue 의 frozen artifact. 실측된 문법만 들어간다.

    ``sort_keys`` 와 고정 구분자로 직렬화하는 것은 **재현성** 때문이다 — 같은 입력이
    같은 bytes 를 내지 않으면 ``artifact_sha256`` 이 뜻을 잃는다.
    """
    store = f"Store Sequence {destination} Cue {cue_number} '{cue['cue_id']}'"
    command = store_with_measured_fade(store, cue.get("fade_s"))
    payload = {
        "cue_id": cue["cue_id"],
        "cue_number": cue_number,
        "commands": [command],
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def emit_compiled(
    plan: dict[str, Any],
    *,
    target: dict[str, Any],
    compiler_id: str,
    compiler_version: str,
    compiler_build_digest: str,
    plan_digest: str,
    context_digest: str,
) -> tuple[dict[str, Any], dict[str, bytes]]:
    """계약 §145 형태의 ``compiled`` 와 bundle 별 frozen artifact bytes 를 낸다.

    cue 하나가 bundle 하나다. 준비 cue 도 예외가 아니다 — 계약이 *"준비 cue 도 최종
    순서와 delta 계산에 포함"* 이라 했으므로 번호와 delta 사슬에 함께 든다. 준비 cue 를
    빼면 그 뒤 모든 ``relative_ms`` 가 조용히 틀린다.

    ``compiled`` 에 ``compiled_digest`` 는 **없다**(모듈 독스트링 참조). 호출자가 채운다.

    Raises:
        AxisTimingUnsupportedError: action 이 축별 timing 을 들었을 때.
        ValueError: playback 이 계약의 둘이 아닐 때.
    """
    playback = plan.get("playback")
    if playback not in PLAYBACK_MODES:
        raise ValueError(
            f"playback mode {playback!r} 를 지원하지 않습니다. 계약은 "
            f"{' 와 '.join(PLAYBACK_MODES)} 둘만 허용하며 timecode mode·자동 GO 는 거부합니다."
        )

    destination = str(target["destination"])
    cues: list[dict[str, Any]] = list(plan.get("cues") or [])

    bundles: list[dict[str, Any]] = []
    artifacts: dict[str, bytes] = {}
    previous_at_ms: int | None = None

    for index, cue in enumerate(cues):
        cue_number = index + 1
        action_ids: list[str] = []
        for action in cue.get("actions") or []:
            axes = _requested_axes(action)
            if axes:
                raise AxisTimingUnsupportedError(
                    f"cue {cue['cue_id']} 의 action {action.get('action_id')} 이 축 "
                    f"{', '.join(axes)} 의 timing 을 요청했습니다 — {_UNOBSERVED_AXIS_REASON}"
                )
            action_ids.append(str(action.get("action_id")))

        at_ms = int(cue["at_ms"])
        if playback == "manual_go" or previous_at_ms is None:
            trigger = {"type": "manual_go", "relative_ms": 0}
        else:
            trigger = {"type": "time", "relative_ms": at_ms - previous_at_ms}
        previous_at_ms = at_ms

        payload = _artifact_bytes(destination, cue_number, cue)
        resource_id = f"artifact-{cue['cue_id']}"
        artifacts[resource_id] = payload

        bundles.append(
            {
                "bundle_id": f"bundle-{cue['cue_id']}",
                "cue_id": cue["cue_id"],
                "action_ids": action_ids,
                "at_ms": at_ms,
                "cue_number": cue_number,
                "trigger": trigger,
                "artifact_resource_id": resource_id,
                "artifact_sha256": hashlib.sha256(payload).hexdigest(),
            }
        )

    compiled = {
        "available": True,
        "manifest": {
            "compiler_id": compiler_id,
            "compiler_version": compiler_version,
            "compiler_build_digest": compiler_build_digest,
            "plan_digest": plan_digest,
            "context_digest": context_digest,
            "target": dict(target),
            "playback": playback,
            "bundles": bundles,
        },
    }
    return compiled, artifacts
