"""server/vwx — Vectorworks Instrument Data 연계 1단계 (SPEC-COPILOT-VWX-001).

문서 근거 · 실물 미검증. 이 패키지 전체는 실물 Vectorworks export 샘플이
아니라 Vectorworks 공식 문서 조사(``research.md`` §1-§6)에 근거해 작성됐다 —
M0(실물 샘플 확보)가 BLOCKED 상태이므로 컬럼 계약은 아직 정본이 아니라
강력한 초안이다.

이 패키지는 파일 바이트를 받아 판정 결과를 산출하는 순수 판정 계층이다.
``server.bridge``/``pythonosc``를 직접 import하지 않는다(``server/tests/
test_architecture.py``의 ``_FORBIDDEN_MODULE_PREFIXES``가 강제한다). 콘솔
실측은 이미 라이브 검증된 ``server.prechk``/``server.paperwork``의 공개
함수(``read_inventory``/``build_patch_sheet``/``normalize_address``/
``_range_overlaps``)를 소비만 한다 — 재구현하지 않는다.

흐름: ``reader`` (판독) -> ``columns`` (별칭 해석) -> ``address`` (주소 정규화)
-> ``rig`` (설계상 리그 모델) -> ``diff`` (precheck_patch 대조) -> ``report``
(구조화 페이로드 + 한국어 표현).
"""

from __future__ import annotations

__all__: list[str] = []
