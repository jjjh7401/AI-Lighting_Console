"""SPATIAL position moods — 연출 의도(자연어)를 기본 포지션 추천으로 사상한다.

``server/fx/matching.py``의 mood-keyword 스코어링과 같은 결정론적 패턴: 문장에서
무드 키워드를 세고, 가장 많이 맞은 포지션 하나 + 대안 목록을 돌려준다. 여기서
멈춘다 — 이 모듈은 아무것도 실행하지 않고, 추천은 반드시 카드(사용자 선택)를
거쳐 적용된다. 키워드 하나로 단정해 바로 실행하는 반사적 처리(과거 제거된 캔드
클래리파이어의 결함 형태)를 재도입하지 않기 위한 경계다.

추천 대상은 :data:`server.spatial.pointing.BASIC_POSITION_SEQUENCE`의 열 개
이름뿐이다. 매핑은 업계 관례(보컬 스페셜 = DSC 포커스, 수렴 = 시선 고정,
교차/부채 = 에너지, 평행 커튼 = 장엄 — docs/proposals/
pan-tilt-position-preset-strategy.md의 리서치 절)에서 왔고, 취향의 대체가
아니라 출발점이다.
"""

from __future__ import annotations

from dataclasses import dataclass

from server.spatial.pointing import BASIC_POSITION_SEQUENCE

__all__ = [
    "POSITION_MOOD_TABLE",
    "PositionMoodEntry",
    "PositionMoodSuggestion",
    "match_position_mood",
]


@dataclass(frozen=True)
class PositionMoodEntry:
    """한 포지션이 어울리는 연출 의도의 어휘와 그 이유."""

    label: str  # BASIC_POSITION_SEQUENCE의 이름 그대로
    korean: str
    keywords: tuple[str, ...]
    reason: str
    alternatives: tuple[str, ...]  # 같은 결에서 고를 수 있는 다른 포지션


#: 무드 어휘 → 포지션. 키워드는 표 전체에서 서로 겹치지 않게 유지한다 —
#: 겹침은 동점을 만들고, 동점은 표 순서라는 임의성으로 풀리기 때문이다.
#: (겹침 금지는 테스트가 고정한다.)
POSITION_MOOD_TABLE: tuple[PositionMoodEntry, ...] = (
    PositionMoodEntry(
        label="Vocal DSC",
        korean="보컬 포커스",
        keywords=("발라드", "잔잔", "조용", "서정", "어쿠스틱", "보컬", "솔로", "감성", "슬픈"),
        reason="조용한 곡은 시선을 사람에게 모은다 — 다운스테이지 보컬 지점 포커스가 표준.",
        alternatives=("Center", "Wall"),
    ),
    PositionMoodEntry(
        label="Center",
        korean="센터 수렴",
        keywords=("오프닝", "등장", "인트로", "드라마틱", "스포트라이트", "주인공"),
        reason="등장·오프닝은 한 점 수렴이 시선을 고정한다.",
        alternatives=("Ring In", "Vocal DSC"),
    ),
    PositionMoodEntry(
        label="Ring In",
        korean="수렴 콘",
        keywords=("웅장", "장엄", "클라이맥스", "피날레", "대미", "수렴"),
        reason="공중 한 점으로 모이는 콘은 규모감·장엄함의 관례적 표현.",
        alternatives=("Center", "Wall"),
    ),
    PositionMoodEntry(
        label="Cross",
        korean="교차빔",
        keywords=("신나는", "클럽", "후렴", "파티", "댄스", "강렬", "터지", "폭발", "edm"),
        reason="교차하는 빔은 에너지가 큰 구간(후렴·드롭)의 표준 룩.",
        alternatives=("Fan Out", "Ring Out"),
    ),
    PositionMoodEntry(
        label="Fan Out",
        korean="부채살",
        keywords=("화려", "펼쳐", "개방", "시원", "넓게", "스케일"),
        reason="바깥으로 벌어지는 부채살은 개방감과 규모를 만든다.",
        alternatives=("Cross", "Audience"),
    ),
    PositionMoodEntry(
        label="Audience",
        korean="객석 방향",
        keywords=("관객", "객석", "호응", "싱어롱", "떼창", "블라인더"),
        reason="객석으로 빔을 넘기는 순간이 호응 유도의 관례.",
        alternatives=("Fan Out", "Wall"),
    ),
    PositionMoodEntry(
        label="Wall",
        korean="평행 빔 커튼",
        keywords=("커튼", "장벽", "배경", "합창", "성가", "백월"),
        reason="같은 각도의 평행 빔은 배경 커튼 — 장면 뒤를 세우는 룩.",
        alternatives=("Ring In", "Audience"),
    ),
    PositionMoodEntry(
        label="Home",
        korean="홈(수직 아래)",
        keywords=("정리", "리셋", "파킹", "대기", "암전"),
        reason="전환·대기는 수직 아래 파킹이 안전한 기본.",
        alternatives=("Wall",),
    ),
)


@dataclass(frozen=True)
class PositionMoodSuggestion:
    """한 문장에 대한 추천 하나 — 근거와 대안을 함께 담는다."""

    entry: PositionMoodEntry
    matched: tuple[str, ...]  # 실제로 문장에서 발견된 키워드
    score: int


def match_position_mood(text: str) -> PositionMoodSuggestion | None:
    """문장에서 무드 키워드를 세어 최고 득점 포지션을 추천한다.

    아무 키워드도 없으면 ``None`` — 추천이 없는 문장에 추천을 지어내지 않는다.
    동점은 표 순서로 풀리지만, 키워드 무겹침 규칙(테스트 고정) 덕에 동점은
    같은 문장이 두 결의 어휘를 동시에 담은 경우로 한정된다.
    """
    folded = text.casefold()
    best: PositionMoodSuggestion | None = None
    for entry in POSITION_MOOD_TABLE:
        matched = tuple(keyword for keyword in entry.keywords if keyword in folded)
        if not matched:
            continue
        if best is None or len(matched) > best.score:
            best = PositionMoodSuggestion(entry=entry, matched=matched, score=len(matched))
    return best


def _labels_are_canonical() -> bool:
    """모든 label/alternative가 기본 시퀀스의 실명인지 — import 시 1회 검증."""
    names = set(BASIC_POSITION_SEQUENCE)
    return all(
        entry.label in names and all(alt in names for alt in entry.alternatives)
        for entry in POSITION_MOOD_TABLE
    )


assert _labels_are_canonical(), "position mood table names a look outside BASIC_POSITION_SEQUENCE"
