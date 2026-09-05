"""오디오 분석 층 — 콘솔을 모른다 (REQ-MUSICSYNC-010).

이 패키지는 **바이트를 받아 숫자를 돌려주는 것**이 전부다. 콘솔 포트도, 실행
경로도, 안전 게이트도 여기서는 이름조차 부르지 않는다. 그 사실은 취향이 아니라
SPEC-COPILOT-MUSICSYNC-001 §A.4 의 예산이다 — M2 의 콘솔 접촉은 **쓰기 0건,
조회 0건**이며, 형제 경계 시험 넷과 같은 형태의
``server/tests/test_audio_boundary.py`` 가 그것을 기계로 고정한다.

측정은 DSP 가, 제안은 LLM 이, 확정은 사람이 한다(REQ-MUSICSYNC-009). 이 패키지는
그중 **측정**만 맡는다. 여기서 나온 숫자가 콘솔에 닿으려면 반드시 확인 카드를
지나야 하고, 그 카드는 이 패키지 밖(``server/web/question.py``)이 세운다.
"""

from __future__ import annotations
