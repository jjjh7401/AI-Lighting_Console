"""모델이 **사용자에게 되묻는** 통로 — 추측 대신 질문.

없는 픽스처 타입, 좁혀지지 않는 후보, 비어 있는 필수 값. 이런 자리에서 모델이
혼자 판단하면 실물 사고가 난다. 실측 사례: 라이브러리에 없는 타입을 요청받자
모델이 ``Import`` 문법과 GDTF 파일명을 **다섯 번 추측**하고 플러그인까지
배포·실행했으나 장비는 하나도 생기지 않았다(59.6초, ``retries_exhausted``).

이 모듈은 그 자리에 **질문 카드**를 세운다. 흐름은 M7 배포 검토와 같다 —
:class:`~server.web.approval_bridge.ApprovalChannel`\\ 은 payload를 들여다보지
않으므로 세 번째 인스턴스로 그대로 재사용한다(``id_prefix="question"``).

**승인과 다른 점 하나.** 승인은 실패하면 **거부**가 안전하다(되돌릴 수 없는 쓰기를
막는다). 질문은 실패해도 **거부가 아니다** — 답을 못 받았을 뿐이다. 그래서
:data:`UNANSWERED`\\ 를 내고, 모델은 "사용자가 아직 답하지 않았다"를 사실 그대로
받는다. 없는 답을 지어내지 않게 하는 것이 이 통로의 전부다.
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: 답을 받지 못했을 때의 값 — 거부가 아니라 **미응답**이다.
UNANSWERED = "__unanswered__"

#: 답 대신 사용자가 대화로 잇겠다고 고른 경우.
ANSWER_FREEFORM = "__freeform__"


@dataclass(frozen=True)
class QuestionOption:
    """고를 수 있는 답 하나."""

    label: str
    #: 이 갈래를 고르면 무슨 일이 일어나는지 — 사용자가 고르기 전에 읽는다.
    description: str = ""


@dataclass(frozen=True)
class QuestionRequest:
    """모델이 사용자에게 던지는 물음 하나.

    ``options``\\ 가 비면 자유 입력 질문이다. 차 있으면 선택지 + 자유 입력이다 —
    선택지가 사용자의 실제 사정을 다 담지 못하는 경우가 실물에서 흔하다.
    """

    #: 무엇을 묻는가. 한국어 한 문장.
    prompt: str
    #: 왜 필요한가. 이유 없는 질문은 사용자를 막는 벽이다.
    why: str = ""
    #: 사용자가 따라 할 수 있는 절차(콘솔 조작 등). 없으면 빈 튜플.
    steps: tuple[str, ...] = ()
    options: tuple[QuestionOption, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, object]:
        return {
            "prompt": self.prompt,
            "why": self.why,
            "steps": list(self.steps),
            "options": [
                {"label": option.label, "description": option.description}
                for option in self.options
            ],
        }
