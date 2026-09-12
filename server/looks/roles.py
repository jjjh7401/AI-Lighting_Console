"""역할 어휘 — 위치 축 6개 + 기구 종류 축 5개, 그리고 이름 매칭 규율.

원래 이 어휘는 **위치 역할 6개로 닫힌 집합**이었다(spec.md §A, 사용자 확정 ⑨ /
plan.md §A.4a 결정 J). 각 역할은 한국어 대표 이름 하나, 영어 별칭 최소 하나,
매핑 힌트 최소 하나를 갖는다 — 힌트가 리그 그룹명과 맞춰지는 물건이다.

## 왜 닫힌 집합을 열었는가 (카드 t356, 2026-09-12, 감독 승인)

닫힌 6개로는 실기 리그의 절반을 부를 수 없다. `.moai/specs/SPEC-COPILOT-LXSEQ-001/
research.md:28` 이 기록한 12그룹 86대에 대고 재면 **5그룹 38대(44.2%)만 이름이
붙는다** — `BLIND`·`STROBE`·`HAZE`·`MOVER-U`·`MOVER-D`·`WASH-U`·`WASH-D` 일곱
그룹 48대가 전부 no_match 다. 그래서 이 어휘로는
`docs/proposals/song-structure-lighting-standard.md` 가 요구하는 두 가지를
못 한다: §6.2 의 세 층(앰비언트 워시 / 텍스처 / 에너지)으로 기구에 역할을
나누는 것과, §7.1 아껴두기 사다리의 마지막 두 칸(chorus 3 의 **블라인더**,
앙코르의 **스트로브**)을 부르는 것. 같은 진단이 §12 항목 6 이다.

**위 6개의 이름은 하나도 바꾸지 않았다.** `server/looks/library/*.yaml` 의 룩들이
그 이름을 문자열로 든다 — 이름을 고치면 자산이 깨지고, 그것은 이행이 아니라 회귀다.
변경은 전부 **덧붙이기**다.

## 두 축으로 나눈 이유

역할을 하나의 평평한 집합으로 두되 각 역할에 :data:`POSITION` / :data:`FIXTURE_TYPE`
축을 붙였다. 축을 **별도의 필드 두 개**(위치 역할 목록 + 종류 역할 목록)로 가르지
않은 것은 룩 스키마 때문이다 — `roles: ["프론트", "스페셜"]` 는 닫힌 스키마의
문자열 리스트이고(`loader.py`), 축을 가르면 4개 yaml 자산과 로더와 리졸버가 전부
바뀐다. 표준이 요구하는 것은 「기구마다 역할을 부여하라」이지 「룩이 두 종류의
역할을 따로 선언하라」가 아니다.

축은 장식이 아니라 **충돌 규칙의 근거**다. 아래 참조.

## 위치가 종류를 이긴다 (충돌 규칙)

`WASH-U` 는 워시이면서 위쪽이고, `Back_Wash` 는 백라이트이면서 워시다. 한 이름을
두 역할이 주장할 때:

* 위치 역할 하나가 주장하면 **그 위치 역할이 이긴다**. 진 종류 역할은 버려지지
  않고 :attr:`RoleNameMatch.deferred` 로 보고된다.
* 위치 역할 **둘 이상**이 주장하면 예전처럼 ``ambiguous`` — 위치 축이 스스로
  못 정하는 것을 종류 답으로 메우는 것은 추측이다.
* 위치가 하나도 없고 종류가 둘 이상이면 그것도 ``ambiguous``.

근거는 둘이다. 하나는 측정이다 — `Back_Wash → 백라이트`, `SR Wash → 사이드`,
`foh wash → 프론트` 는 이미 고정된 기대값이고(`test_looks_schema.py`), 규칙이
없으면 셋 다 ambiguous 로 뒤집혀 회귀가 된다. 다른 하나는 이 파일이 원래 적어 둔
이유 그대로다: **워시 한 대는 이 리그에서 백라이트이고 저 리그에서 프론트다.**
종류는 기구가 무엇인지를 말하고 위치는 빛이 어디에 떨어지는지를 말하므로,
조준에 관해서는 위치가 더 구체적인 주장이다. 더 구체적인 쪽이 이긴다.

그래서 **위치 역할의 힌트에는 여전히 종류 어휘가 들어가지 않는다**(AC-LOOKLIB-015 ④
의 원래 금지는 위치 축에 대해 글자 그대로 살아 있다). 종류 어휘는 종류 역할의
힌트에만 산다.

## 리그마다 다른 그룹명

힌트 목록은 유일한 수단이 **아니다**. 다음 리그는 그룹명이 다르고, 그때마다 이
파일을 고치는 것은 어휘를 리그에 고정하는 일이다. :func:`resolve_role_token` 과
`resolver.resolve_roles(..., aliases=...)` 가 쇼 단위 별칭 표를 받는다 —
그룹명 → 역할 이름/별칭. 오타는 조용히 흡수되지 않고 `alias_unknown_role` 로
보고된다.

이 어휘는 NEW 다. ``20_korean_terms.md`` 를 확장하지 않는다: 그 파일의 쇼파일 행은
기구 TYPE 클래스(워시 / 스팟 / 빔)이고 PRESERVE 대상이다. 이름 짓는 **양식**만
물려받는다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

AMBIGUOUS = "ambiguous"
NO_MATCH = "no_match"

#: 역할의 축. 위치 역할은 빛이 **어디에** 떨어지는지를, 종류 역할은 기구가
#: **무엇인지**를 말한다. 충돌 시 위치가 이긴다 — 모듈 독스트링 참조.
POSITION = "position"
FIXTURE_TYPE = "type"
ROLE_KINDS = (POSITION, FIXTURE_TYPE)

# Characters that count as "inside a word" for boundary purposes. Hangul is a
# word character here on purpose: Python's ``\b`` would happily match `백`
# inside `백색`, because both sides are ``\w``.
_WORD = r"[0-9A-Za-zㄱ-ㆎ가-힣]"


@dataclass(frozen=True)
class Role:
    """역할 하나: 한국어 대표 이름 + 축 + 별칭 + 그룹명 힌트."""

    name: str
    kind: str
    aliases: tuple[str, ...]
    hints: tuple[str, ...]
    abbreviations: tuple[str, ...]


# 위치 축 힌트는 spec.md §A 원문 그대로다. M0 이 실기 쇼파일에 대고 쟀고
# (progress.md §E.2 측정 3) 2/6 역할 매칭 · ambiguous 0 · 오탐 0 이라 M1 에 무수정
# 진입했다. **이 여섯의 이름·별칭·힌트는 t356 에서 한 글자도 바뀌지 않았다.**
_POSITION_ROLES: tuple[Role, ...] = (
    Role(
        name="백라이트",
        kind=POSITION,
        aliases=("back", "backlight"),
        hints=("Back", "Backlight", "BackLight", "Rear", "BL", "백", "백라이트", "뒤"),
        abbreviations=("BL",),
    ),
    Role(
        name="프론트",
        kind=POSITION,
        aliases=("front", "FOH"),
        hints=("Front", "FOH", "F.O.H", "FR", "프론트", "전면", "앞"),
        abbreviations=("FR",),
    ),
    Role(
        name="사이드",
        kind=POSITION,
        aliases=("side",),
        hints=("Side", "SL", "SR", "Wing", "사이드", "측면"),
        abbreviations=("SL", "SR"),
    ),
    Role(
        name="탑",
        kind=POSITION,
        aliases=("top", "downlight"),
        hints=("Top", "Down", "Downlight", "TP", "탑", "다운", "상부"),
        abbreviations=("TP",),
    ),
    Role(
        name="배경",
        kind=POSITION,
        aliases=("cyc", "backdrop"),
        hints=("Cyc", "Cyclorama", "Backdrop", "BD", "배경", "샤막", "호리"),
        abbreviations=("BD",),
    ),
    Role(
        name="스페셜",
        kind=POSITION,
        aliases=("special", "key"),
        hints=("Special", "Spc", "Key", "KeyLight", "스페셜", "키라이트"),
        abbreviations=("Spc",),
    ),
)

# 기구 종류 축 — t356 이 더한 다섯. 고른 기준은 취향이 아니라 **두 문서**다.
#
#   1. 실기 리그(research.md:28)에서 위치 어휘가 못 부른 일곱 그룹:
#      BLIND · STROBE · HAZE · MOVER-U · MOVER-D · WASH-U · WASH-D.
#      다섯 역할이 그 일곱을 정확히 덮는다.
#   2. 표준 §6.2 의 세 층 — 앰비언트 워시(워시) · 텍스처(무버) · 에너지
#      (스트로브·블라인더) — 과 §7.1 사다리의 마지막 두 칸(블라인더·스트로브).
#      헤이즈는 세 층 어디에도 안 들어간다: §6.2 자신이 그것을 「빔을 보이게 하는
#      필수 요소」로 층이 아니라 **조력자**로 적는다. 그래서 층 태그를 필드로 만들지
#      않았다 — 층이 셋이 아니라 「셋 + 조력자 하나」인데 소비자가 아직 없다.
#
# 여기 없는 것(스팟·빔·ACL)은 누락이 아니라 **안 더한 것**이다. 실기 리그에 그런
# 그룹이 없고, 힌트 `Spot` 은 `Spotlight` 를 no_match 로 고정한 기존 측정
# (`test_looks_schema.py`)을 뒤집는다. 리그가 그런 그룹을 들고 오면 그때 잰다.
_TYPE_ROLES: tuple[Role, ...] = (
    Role(
        name="워시",
        kind=FIXTURE_TYPE,
        aliases=("wash", "washlight"),
        hints=("Wash", "Washlight", "WashLight", "워시", "워시라이트"),
        abbreviations=(),
    ),
    Role(
        name="무버",
        kind=FIXTURE_TYPE,
        aliases=("mover", "movinghead"),
        hints=("Mover", "Moving", "MovingHead", "무버", "무빙", "무빙헤드"),
        abbreviations=(),
    ),
    Role(
        name="블라인더",
        kind=FIXTURE_TYPE,
        aliases=("blinder",),
        hints=("Blind", "Blinder", "블라인더", "블라인드"),
        abbreviations=(),
    ),
    Role(
        name="스트로브",
        kind=FIXTURE_TYPE,
        aliases=("strobe",),
        hints=("Strobe", "Strob", "스트로브", "스트롭"),
        abbreviations=(),
    ),
    Role(
        name="헤이즈",
        kind=FIXTURE_TYPE,
        aliases=("haze", "hazer"),
        hints=("Haze", "Hazer", "Fog", "Fogger", "Smoke", "헤이즈", "헤이저", "포그"),
        abbreviations=(),
    ),
)

#: 축 순서로 이어 붙인 전체 집합. 위치가 앞이라 기존 소비자가 보는 순서는 그대로다.
ROLES: tuple[Role, ...] = _POSITION_ROLES + _TYPE_ROLES

POSITION_ROLES: tuple[Role, ...] = _POSITION_ROLES
TYPE_ROLES: tuple[Role, ...] = _TYPE_ROLES
POSITION_ROLE_NAMES = frozenset(role.name for role in _POSITION_ROLES)
TYPE_ROLE_NAMES = frozenset(role.name for role in _TYPE_ROLES)

ROLE_NAMES = frozenset(role.name for role in ROLES)

_BY_NAME = {role.name: role for role in ROLES}


@dataclass(frozen=True)
class RoleNameMatch:
    """한 그룹명을 역할 힌트에 맞춘 결과.

    ``role`` 은 모호하지 않은 단일 결정일 때만 채워진다. 아니면 ``reason`` 이
    ``ambiguous``(같은 축의 역할 둘 이상이 주장) 또는 ``no_match`` 이고,
    ``candidates`` 가 **결정에 참여한** 역할들을 담아 caller 가 보고할 수 있게 한다.

    ``deferred`` 는 위치 역할에 밀린 종류 역할이다 — 버려지지 않고 여기 남는다.
    「이 그룹은 백라이트로 잡혔고 워시이기도 하다」를 말할 수 있어야 조준을
    의심할 수 있기 때문이다. 결정에는 참여하지 않으므로 ``candidates`` 와 따로 둔다.
    """

    role: str | None
    reason: str | None
    candidates: tuple[str, ...]
    deferred: tuple[str, ...] = ()


#: 별칭 표가 받아들이는 토큰 → 대표 이름. 대표 이름 자신과 선언된 별칭만 넣는다.
#: 힌트는 **넣지 않는다** — 힌트는 부분 일치용 패턴이지 식별자가 아니고, `BL` 같은
#: 약어를 식별자로 받으면 별칭 표가 힌트 매칭을 둘째 경로로 복제하게 된다.
_BY_TOKEN: dict[str, str] = {}
for _role in ROLES:
    for _token in (_role.name, *_role.aliases):
        _BY_TOKEN.setdefault(_token.casefold(), _role.name)
del _role, _token


def role_by_name(name: str) -> Role:
    """Return the role with this Korean primary name, or raise ``KeyError``."""
    return _BY_NAME[name]


def resolve_role_token(token: str) -> str | None:
    """별칭 표의 값 하나를 대표 이름으로 푼다. 모르는 토큰이면 ``None``.

    ``None`` 은 호출자가 **보고**할 것이지 조용히 흡수할 것이 아니다 — 오타 난
    역할 이름을 힌트 매칭으로 되돌리면, 운영자가 지정한 것과 다른 조명이 켜진다.
    """
    if not isinstance(token, str):
        return None
    return _BY_TOKEN.get(token.strip().casefold())


def _strict_pattern(hint: str) -> re.Pattern[str]:
    """Hint must occupy a whole token (case-insensitive)."""
    return re.compile(f"(?<!{_WORD}){re.escape(hint)}(?!{_WORD})", re.IGNORECASE)


def _camel_pattern(hint: str) -> re.Pattern[str] | None:
    """Hint may also open or close a CamelCase hump (case-SENSITIVE).

    This is what makes ``FrontBack Truss`` report as ambiguous instead of
    matching nothing: a reader sees both words in it, so the matcher must too.
    The case sensitivity is the whole point — it is the capital letter that
    marks the hump — so this pass cannot be folded into the strict one.
    """
    left = f"(?<!{_WORD})"
    right = f"(?!{_WORD})"
    relaxed = False
    if hint[0].isascii() and hint[0].isupper():
        left = f"(?:(?<!{_WORD})|(?<=[a-z]))"
        relaxed = True
    if hint[-1].isascii() and hint[-1].islower():
        right = f"(?:(?!{_WORD})|(?=[A-Z]))"
        relaxed = True
    if not relaxed:
        return None
    return re.compile(left + re.escape(hint) + right)


# Abbreviations are matched by the strict pass only. `SP` was rejected as a
# hint for exactly this reason (it would prefix Spot-family names); `Spc`
# survives because nothing but the token itself can produce it.
_STRICT: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (role.name, _strict_pattern(hint)) for role in ROLES for hint in role.hints
)
_CAMEL: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (role.name, pattern)
    for role in ROLES
    for hint in role.hints
    if hint not in role.abbreviations
    for pattern in (_camel_pattern(hint),)
    if pattern is not None
)


_KIND_OF = {role.name: role.kind for role in ROLES}


# @MX:WARN: [AUTO] 이름 규약 휴리스틱 — 규약이 없는 리그는 0개를 매핑하고,
#   그것은 덮을 실패가 아니라 옳은 동작이다
# @MX:REASON: REQ-LOOKLIB-009 가 명시적인 미매핑 보고를 요구한다. 힌트를 넓힐 때의
#   위험은 리그가 올린 적 없는 그룹을 발명하는 것이다
#   (31_choreography_patterns.md:184-191). 실측한 그룹명에 대고서만 넓히고,
#   모호함은 추측으로 풀지 말고 보고한 채로 둬라. t356 이 종류 축을 더하면서
#   **위치 우선** 규칙이 새 위험을 하나 만들었다: 위치 힌트를 넓히면 그것이
#   종류 판정을 조용히 덮는다. 위치 힌트는 특히 좁게 유지하라.
def match_role_by_name(group_name: str) -> RoleNameMatch:
    """리그 그룹명 하나를 역할 어휘에 맞춘다.

    같은 축의 역할 둘 이상이 주장한 이름은 ``ambiguous`` 로 보고하고 미매핑으로
    둔다 — 먼저 검사된 쪽에 배정하지 않는다. 축이 갈리면 위치가 이기고, 진 종류
    역할은 ``deferred`` 로 남는다(모듈 독스트링 「위치가 종류를 이긴다」).
    """
    hit: list[str] = []
    for role_name, pattern in _STRICT:
        if role_name not in hit and pattern.search(group_name):
            hit.append(role_name)
    for role_name, pattern in _CAMEL:
        if role_name not in hit and pattern.search(group_name):
            hit.append(role_name)

    ordered = tuple(role.name for role in ROLES if role.name in hit)
    if not ordered:
        return RoleNameMatch(role=None, reason=NO_MATCH, candidates=())

    positions = tuple(name for name in ordered if _KIND_OF[name] == POSITION)
    types = tuple(name for name in ordered if _KIND_OF[name] == FIXTURE_TYPE)

    # 위치 축이 하나라도 답하면 결정은 위치 축 안에서만 이뤄진다. 종류 답은
    # 버리지 않고 deferred 로 넘긴다.
    contenders, deferred = (positions, types) if positions else (types, ())

    if len(contenders) == 1:
        return RoleNameMatch(
            role=contenders[0], reason=None, candidates=contenders, deferred=deferred
        )
    return RoleNameMatch(role=None, reason=AMBIGUOUS, candidates=contenders, deferred=deferred)
