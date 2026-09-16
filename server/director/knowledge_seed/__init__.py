"""design §3 의 검토된 지식 seed 5주제 — 순수 데이터 (SPEC-LDSTORE-001 M3).

design.md §3 의 표는 6개 행을 담지만 6번째 "feedback seed" 행은 이 SPEC 의 범위 밖이다 —
plan.md §2 M3 는 "지식 seed" 단일 마일스톤으로만 명시하고, feedback 워크플로(proposal·
scope binding·review) 는 `SPEC-LDPLUGIN-001` 이 소유하는 `director-feedback` 패키지가
맡는다. 그래서 여기 담기는 것은 **5주제**뿐이다:

1. 음악 근거 규칙 (:mod:`music_evidence`)
2. tracking 규칙 (:mod:`tracking`)
3. 연출 case (:mod:`staging_cases`)
4. rig·preset 규칙 (:mod:`rig_preset`)
5. 적용·안전 규칙 (:mod:`safety`)

이 패키지는 ``server.director.knowledge`` 를 임포트하지 않는다 — 검증·레코드 조립은
그쪽의 일이고, 여기서 뒤섞으면 순환 임포트가 된다.
"""

from __future__ import annotations

from typing import Any

from server.director.knowledge_seed import (
    music_evidence,
    rig_preset,
    safety,
    staging_cases,
    tracking,
)

#: design §3 의 검토된 5주제. 순서는 design.md 표의 순서와 같다.
RAW_TOPICS: tuple[dict[str, Any], ...] = (
    music_evidence.TOPIC,
    tracking.TOPIC,
    staging_cases.TOPIC,
    rig_preset.TOPIC,
    safety.TOPIC,
)

__all__ = ["RAW_TOPICS"]
