"""Director 교환·저장 층 — 판단하지 않는다 (SPEC-LDSTORE-001).

이 패키지가 하는 일은 셋이다: 외부 `lighting-director` 플러그인이 보낸 교환 객체를
**계약대로 엄격히 파싱**하고, **불변으로 보관**하고, 무엇을 근거로 만들었는지
되짚을 **context 를 발급**한다. 그게 전부다.

이 패키지가 하지 않는 일:

- **예술 판단을 하지 않는다.** 어떤 색이 어울리는지, 후렴이 더 세야 하는지는
  외부 Director 의 몫이다. `server/looks/songcue.py` 와 `server/web/session.py` 의
  `_ARC_*` 표는 기존 앱 경로의 것이며 이 패키지는 그것들을 호출하지 않는다.
- **콘솔을 만지지 않는다.** `server/bridge/osc.py` 가 서버 전체의 유일한 송신
  표면이고, 이 패키지는 그 이름조차 부르지 않는다.
- **검증 판정을 내리지 않는다.** 계약 §3 의 `SubmitResult` 가 `ValidationReport` 를
  포함하지만, 그것을 만드는 것은 `SPEC-LDCOMPILE-001` 이다. 이 패키지는 검증기를
  **주입받는 seam** 으로만 두고, 기본 구현은 "검증 미구현"을 blocked 로 답한다 —
  검증 없이 `ready_for_review` 를 내는 것은 계약 §10 이 막으려는 상태다.

두 경계는 취향이 아니라 기계로 고정돼 있다: `server/tests/test_director_boundary.py`
가 형제 경계 시험들(`test_paperwork_boundary.py`, `test_audio_boundary.py`)과 같은
형태로 임포트를 훑는다.

규범의 위치: `.moai/specs/SPEC-LDPLUGIN-001/contract.md` (wire shape·state·hash 의
단일 원본) + 같은 곳의 `schemas/exchange.schema.json`. 이 패키지의
`schemas/exchange.schema.json` 은 **런타임 자원 사본**이며 바이트가 같아야 한다 —
그 동일성도 시험이 지킨다.
"""

from __future__ import annotations
