"""구간 팔레트 결정 — SPEC-LDDESIGN-001 REQ-003 (카드 t441).

``server/web/session.py``(경로 A, 채팅/웹 인터뷰) 의 `_section_palette_choice` 와
그것이 기대는 아크 회전 함수들을 여기로 옮긴다. 이 SPEC 의 새 소비자는 경로 B
(LLM 도구, `server/orchestrator/tools.py`) 다 — 두 경로가 같은 함수를 불러야
같은 곡이 같은 색을 낸다(카드 t439 실측: 오늘은 경로마다 다른 색이 나간다,
`server/tests/test_chorus_color_two_paths_t439.py` 참고).

**옮기는 것과 안 옮기는 것.** 여기 오는 것은 ``_section_palette_choice`` 가
색(주색·보조색·무게)을 고르는 데 실제로 쓰는 것뿐이다. 같은 역할 표를 쓰지만 색이
아닌 다른 축(D 레벨 `_ARC_D_LEVEL`, 질감 `_ARC_TEXTURE`, 이펙트 `_ARC_FX`/
`_ARC_FX_LADDER`)은 ``session.py`` 에 그대로 남는다 — 이 카드의 범위는 "구간별
주색 결정"뿐이다(카드 지시문).

``session.py`` 는 이 모듈에서 같은 이름을 다시 가져가 그대로 쓴다(재수출) — 동작은
바이트 그대로이고, 기존 테스트가 ``server.web.session`` 에서 이 이름들을 직접
import 하는 자리도 그대로 통과한다.
"""

from __future__ import annotations

import re

from server.design import color_names as _COLOR_NAMES
from server.design.color_names import _HUE_MODIFIER_STRIP, _KO_EN_COLOR_EQUIV
from server.design.cue_density import rotate_palette
from server.design.profile import MusicProfile
from server.looks.section_intent import intent_for_label
from server.looks.section_vocab import (
    ROW_BREAKDOWN,
    ROW_BUILD,
    ROW_CHORUS,
    ROW_INTRO,
    ROW_POST_CHORUS,
    ROW_VERSE,
)
from server.spatial.position_cuesheet import PositionSheetSection

__all__ = [
    "_ACCENT_WEIGHT_LADDER",
    "_ARC_PALETTE",
    "_CHORUS_IDENTITY_ROLES",
    "_COLOR_WORDS",
    "_arc_accent_weight",
    "_arc_palette",
    "_distinct_from_primary",
    "_extract_color_words",
    "_hue_key",
    "_palette_colors",
    "_per_chorus_palette",
    "_section_palette_choice",
    "role_for_songcue_label",
]


def _palette_colors(value: object) -> tuple[str, ...]:
    if isinstance(value, tuple) and all(isinstance(item, str) for item in value):
        return value or ("white",)
    text = str(value)
    colors = tuple(
        chunk.strip()
        for chunk in re.split(r"[/,+、=·\s]+", text)
        if chunk.strip() and chunk.strip() not in ("색", "조합")
    )
    return colors or ("white",)


# 카드 t409 감독 판정 — 표준 팔레트는 파랑이 한 종류(#8 Blue)뿐이라 인트로
# "deep blue"·벌스 "blue"·브리지 "cold blue" 세 아크가 전부 같은 RGB로
# 겹쳤다(t408 실측: 14구간이 동일 색). 감독은 "인접 색조로 갈라 다르게
# 보이게 하라"를 골랐다 — 인트로는 Cyan 계열로, 브리지는 Lavender 계열로
# 민다. 값은 전부 표준 팔레트 10색(spec.md §A.2)에서만 가져온다 — 새 RGB는
# 짓지 않는다.
_ARC_PALETTE: dict[str, tuple[str, ...]] = {
    "intro": ("cyan", "warm special"),
    "verse": ("blue", "cyan"),
    "chorus": ("warm white", "magenta"),
    "bridge": ("lavender",),
    "finale": ("warm white", "gold"),
}


_COLOR_WORDS = re.compile(
    r"레드|빨강|빨간|블루|파랑|파란|그린|초록|녹색|옐로우|엘로우|노랑|노란|골드|금색"
    r"|마젠타|시안|청록|화이트|흰색|하양|앰버|퍼플|보라|핑크|오렌지|주황"
    r"|red|blue|green|yellow|gold|magenta|cyan|white|amber|purple|pink|orange",
    re.IGNORECASE,
)


def _extract_color_words(text: object) -> tuple[str, ...]:
    return tuple(dict.fromkeys(_COLOR_WORDS.findall(str(text or ""))))


def _hue_key(color: str) -> str:
    stripped = _HUE_MODIFIER_STRIP.sub("", str(color or "").strip())
    return _KO_EN_COLOR_EQUIV.get(stripped, stripped.casefold())


def _distinct_from_primary(candidate: str, primary: str, fallback: str) -> str:
    """`candidate` 가 언어만 다를 뿐 `primary` 와 같은 색상이면(카드 t406 —
    "블루"/"blue") 팔레트에 이미 있는 다른 후보로 되돌아간다. 후보도
    같은 색상이면(단색 아크 등) 그대로 돌려준다 — 더 나은 대안이 없다."""
    if _hue_key(candidate) != _hue_key(primary):
        return candidate
    return fallback


#: 카드 t406 핫픽스 — 무게는 색 문자열과 분리된 필드로만 나른다. 예전에는
#: 이 사다리를 색 이름 앞에 접두어로 붙였는데, `cue_sheet_apply.py` 의
#: `_palette_rgb` 는 `value.strip().split()[0]` 을 범례 id 로 읽는다
#: (``"P4 핫핑크"`` → ``P4`` 관례) — 접두어가 그 첫 토큰이 되어 범례 조회가
#: 항상 실패하고 색이 아예 안 나간다(코디네이터 실측: `짙은 magenta` →
#: `None` → `CueSkip`). 색 문자열은 항상 범례에 그대로 걸리는 순정 토큰으로
#: 두고, 무게는 `PaletteDecision.weight` 로만 옮긴다.
#:
#: 회차마다 아크 색조를 두 상태(회전 주기 2)로만 돌리면 25회차짜리 코러스도
#: A-B-A-B 둘로만 보인다(실측: 같은 룩을 공유하는 구간이 13개). 색 목록
#: 자체를 늘리는 대신(순수 리스트 순환은 감독이 지시한 축이 아니다 — 카드
#: 지시문) 이 무게 축으로 상태 수를 늘린다. 색상 정체성(hue)은 그대로
#: 두므로 §7의 "곡 안 반복은 미덕"과 충돌하지 않는다 — 코러스 1의 색이
#: 이후에도 여전히 같은 색이고, 다만 진하기가 회차를 구분한다.
_ACCENT_WEIGHT_LADDER: tuple[str, ...] = ("", "짙은", "연한", "쿨톤", "웜톤")


def _arc_accent_weight(role: str, occurrence: int) -> str | None:
    """이 회차의 채도/무게 라벨. 아크가 없는 역할이거나 첫 회차(수식어
    없음)면 ``None`` — 색 문자열이 아니라 이 값만 봐서 "무게가 있는가"를
    판정할 수 있다."""
    if role not in _ARC_PALETTE or occurrence <= 1:
        return None
    label = _ACCENT_WEIGHT_LADDER[(occurrence - 1) % len(_ACCENT_WEIGHT_LADDER)]
    return label or None


#: 카드 t439 — REQ-LDDESIGN-004/030. 후렴(Chorus)·Final Chorus(finale) 역할은
#: 회차 축을 더 이상 색으로 표현하지 않는다 — §3.7(REQ-043)의 6개 에스컬레이션
#: 축(기구군 수·면적·밝기·모션·포지션·큐 밀도)이 색 대신 회차를 구분한다.
#: verse/intro/bridge 는 이 SPEC 의 범위 밖이라(REQ-030 이 "후렴" 한정) 회전을
#: 그대로 둔다 — 아래 `_arc_palette` 가 이 집합으로 occurrence 인자를 1로
#: 고정한다. 곡별 선택 `per_chorus`(`_per_chorus_palette`)는 감독 결정
#: (2026-09-23)으로 이 고정의 예외다.
_CHORUS_IDENTITY_ROLES: frozenset[str] = frozenset({"chorus", "finale"})


def _arc_palette(base: tuple[str, ...], role: str, occurrence: int = 1) -> tuple[str, ...]:
    """역할 아크 팔레트 — 회차마다 보조색을 돌린다 (카드 t402·t406), 단
    chorus/finale 은 회차와 무관하게 항등이다 (카드 t439, REQ-004/030).

    같은 역할이 반복되면(코러스 25회 등) 예전에는 매번 바이트 동일한
    팔레트가 나왔다 — 회차를 구분하지 않았기 때문이다. `occurrence` 가
    1보다 크면 `rotate_palette`(카드 t305, 마디분할 회전에서 이미 검증된
    함수)로 아크 색을 회전한다. 메인 컬러(``primary``, 감독이 지정한
    색)는 이 회전과 무관하게 아래 결합에 **항상** 남는다 — 감독 지시
    "메인 컬러 중심" 을 구조적으로 지킨다.

    카드 t439 — 위 회전 자체가 REQ-LDDESIGN-004/030 이 금지하는 성질이
    됐다: "후렴(Chorus) 구간 전체는 동일한 주색을 유지한다"(Final
    Chorus의 클라이맥스 색 전환만 예외). 회차 에스컬레이션은 색이 아니라
    §3.7(REQ-043)의 6개 축으로 표현하므로, `role`이
    :data:`_CHORUS_IDENTITY_ROLES`(chorus/finale)에 속하면 `occurrence`
    를 무시하고 항상 1회차 팔레트를 낸다 — verse/intro/bridge 는 이
    SPEC 의 범위 밖이라(REQ-030 은 "후렴" 한정) 기존 회전을 그대로 둔다.

    카드 t406 — `_distinct_from_primary` 로 회전이 아크 색을 primary 와
    같은 색상에(언어만 다른 표기 포함) 겹치게 돌리는 경우를 걸러낸다.
    반환값은 항상 범례 조회가 가능한 순정 색 문자열뿐이다 — 채도/무게
    수식어는 여기 없다(`_arc_accent_weight` 가 별도로 나른다).

    카드 t409 감독 판정 — "메인 색 깔고 포인트는 보조로": 어느 역할이든
    반환 튜플의 **첫 칸은 항상 primary**(감독이 지정한 색)다. 예전에는
    intro/bridge/chorus/finale 역할에서 아크 색이 첫 칸을 차지해
    (`_song_cue_sheet_section_fields` 의 `palette_primary=palette[0]`)
    콘솔 메인 픽스처에 감독 색 대신 아크 색이 나갔다(실측: 39구간 중
    7구간만 verse 역할이라 감독 색을 받았다). 둘째 칸(``accent``)은 변경
    없이 그대로 회전·역할별 계산을 유지한다 — `palette_secondary` 로
    나가 보조 픽스처(back 그룹)에 얹힌다.
    """
    arc = _ARC_PALETTE.get(role)
    if arc is None:
        return base or ("white",)
    rotated = arc
    if role not in _CHORUS_IDENTITY_ROLES and len(arc) > 1 and occurrence > 1:
        rotated = rotate_palette(arc, occurrence - 1)
    if not base:
        return rotated
    primary = base[0]
    if role == "verse":
        accent = _distinct_from_primary(rotated[-1], primary, fallback=rotated[0])
    else:
        accent = _distinct_from_primary(rotated[0], primary, fallback=rotated[-1])
    combined: tuple[str, ...] = (primary, accent)
    return tuple(dict.fromkeys(combined))


def _per_chorus_palette(base: tuple[str, ...], role: str, occurrence: int) -> tuple[str, ...]:
    """SPEC-COPILOT-COLORMODE-001 D5/REQ-014 — chorus/finale accent ladder.

    감독이 곡마다 고르는 ``color_usage="per_chorus"``(Q2B) 전용이다.
    occurrence 2+ 는 표준 10색 팔레트(spec.md §A.2)에서 액센트를 뽑아
    연속 회차가 겹치지 않는다. 주색(``primary``)은 늘 첫 칸이다.

    카드 t439 — 감독 결정(2026-09-23, 「음악 스타일마다 다르니 하나로
    고정은 무리」): REQ-LDDESIGN-004/030 의 후렴 회차 색 고정은 **기본값**
    (modulate)에만 적용되고, 이 함수가 대표하는 곡별 선택은 그 예외다.
    그래서 여기서는 `_CHORUS_IDENTITY_ROLES` 로 회차를 고정하지 않는다.

    Occurrence 1 은 :func:`_arc_palette` 에 그대로 위임한다 — 후렴이 한 번뿐인
    곡(AC-COLORMODE-013)이 modulate 와 바이트 동일한 이유다.
    """
    if occurrence <= 1:
        return _arc_palette(base, role, 1)
    if not base:
        base = ("white",)
    primary = base[0]
    first_arc = _arc_palette(base, role, 1)
    first_accent = first_arc[-1] if len(first_arc) > 1 else primary
    excluded_hues = {_hue_key(primary), _hue_key(first_accent)}
    ladder = tuple(
        name.casefold()
        for name, _rgb in _COLOR_NAMES.COLOR_PALETTE_SEQUENCE
        if _hue_key(name) not in excluded_hues
    )
    if not ladder:
        ladder = (first_accent,)
    accent = ladder[(occurrence - 2) % len(ladder)]
    return tuple(dict.fromkeys((primary, accent)))


def _section_palette_choice(
    section: PositionSheetSection,
    *,
    role: str,
    profile: MusicProfile,
    color_tendency: object,
    palette_mode: str,
    concept_colors: tuple[str, ...],
    occurrence: int = 1,
    color_usage: str = "modulate",
) -> tuple[tuple[str, ...], str, str | None]:
    """한 구간의 팔레트와 그 출처, 그리고 채도/무게 라벨. 구간의 색 단어 >
    팔레트 충돌 결정 > Q2 (+ Q2B 색 운용, SPEC-COPILOT-COLORMODE-001).

    ``occurrence`` — 카드 t402. 같은 역할의 몇 번째 회차인지(1부터).
    아크 색 회전(`_arc_palette`)에만 쓰이므로 구간이 직접 색을 적었거나
    (``section_text``) 컨셉 팔레트를 그대로 쓰는 경로는 영향받지 않는다.

    카드 t406 핫픽스 — 세 번째 반환값(무게)은 색 문자열과 분리된 채널이다
    (`_arc_accent_weight` 참조). 아크 경로가 아니면 항상 ``None``.

    ``color_usage`` (spec.md §2 D5) — Q2B 답이 이 `base` 확정 **다음**,
    `_arc_palette` 호출 **이전**에 개입한다(REQ-COLORMODE-013). `palette_mode`
    해소는 이미 끝난 뒤이므로 `single`/`per_chorus` 모두 그 결과(`base`)를
    우회하지 않는다:

    * ``"modulate"``(기본) — 분기 없이 그대로 `_arc_palette` 로 진행한다
      (REQ-012: 기존 fixture 와 바이트 동일).
    * ``"single"`` — `base` 를 회전 없이 그대로 반환한다.
    * ``"per_chorus"`` — chorus/finale 역할만 :func:`_per_chorus_palette`
      사다리를 쓰고, 그 외 역할은 modulate 와 동일하게 유지한다.
    """
    direct_colors = _extract_color_words(section.mood)
    if direct_colors:
        return direct_colors, "section_text", None
    if palette_mode == "concept" and concept_colors:
        base: tuple[str, ...] = concept_colors
    elif palette_mode == "mixed" and concept_colors and role in ("chorus", "finale"):
        base = concept_colors
    else:
        base = _palette_colors(profile.palette or color_tendency)
    if color_usage == "single":
        return base, "section_single", None
    if color_usage == "per_chorus" and role in ("chorus", "finale"):
        return (
            _per_chorus_palette(base, role, occurrence),
            "section_per_chorus",
            _arc_accent_weight(role, occurrence),
        )
    return (
        _arc_palette(base, role, occurrence),
        "section_arc",
        _arc_accent_weight(role, occurrence),
    )


# 카드 t441 — 경로 B(`server/looks/songcue.py`, `prepare_songcue`)의 라벨을
# 경로 A(`_section_role`, `session.py`)의 5역할 어휘로 접는 표. 새 판정기를
# 짓지 않는다 — `server.looks.section_intent.intent_for_label` 이 이미
# `section_vocab` 의 §6 6행(row) 최장 일치 판정으로 라벨을 접어 두므로, 그
# 결과(row)만 한 번 더 접는다.
#
# 접는 규칙(카드 지시문 — "역할 매핑을 쓰면 이 모듈에 두고 보고에 전부
# 적어라"):
#   * ROW_INTRO                    -> "intro"
#   * ROW_VERSE                    -> "verse"
#   * ROW_CHORUS  ("chorus · drop")     -> "chorus"
#   * ROW_BREAKDOWN ("breakdown · bridge") -> "bridge"
#   * ROW_BUILD   ("pre-chorus · build")   -> "other" (경로 A 에 대응 역할
#     없음 — `_ARC_PALETTE` 에 없는 역할은 `_arc_palette` 가 `base` 를 그대로
#     돌려준다, 아크 회전 없음)
#   * ROW_POST_CHORUS               -> "other" (위와 같음)
#   * 행이 없음(§6 미대응 라벨, `intent_for_label` 이 ``None``)  -> "other"
#
# **finale 을 따로 가르지 않는 이유.** 경로 A 의 "finale" 은 "곡의 마지막
# 구간이면서 절정류"라는 **자리** 판정이다(`_section_role` — `section_index
# == section_count` 조건). 경로 B 의 라벨 어휘(§2 팝/EDM 축)에는 대응하는
# 자리 개념이 없다 — 곡의 몇 번째 구간인지는 `intent_for_label` 의 입력이
# 아니다. 색 축(이 카드의 범위)에서는 갈라도 결과가 같다:
# `_CHORUS_IDENTITY_ROLES`·`_per_chorus_palette` 모두 chorus 와 finale 을
# `role in ("chorus", "finale")` 로 동일하게 다룬다(REQ-LDDESIGN-004/030,
# 카드 t439) — "chorus" 로만 접어도 이 카드가 옮기는 색 결정은 바이트
# 동일하다. finale 에서만 달라지는 축(D 레벨 `_ARC_D_LEVEL`, 질감
# `_ARC_TEXTURE`, 이펙트 `_ARC_FX`)은 경로 A 전용이고 이 카드 범위 밖이다
# — 경로 B 는 그 축에서 자기 자신의 밝기·이펙트 판정(§6 의도)을 그대로
# 쓴다.
_SONGCUE_ROW_ROLE: dict[str, str] = {
    ROW_INTRO: "intro",
    ROW_VERSE: "verse",
    ROW_CHORUS: "chorus",
    ROW_BREAKDOWN: "bridge",
    ROW_BUILD: "other",
    ROW_POST_CHORUS: "other",
}


def role_for_songcue_label(label: str) -> str:
    """경로 B(SongCue) 라벨 하나를 `_section_palette_choice` 의 ``role`` 로 접는다.

    표와 판단은 :data:`_SONGCUE_ROW_ROLE` 의 모듈 주석에 전부 적는다(카드
    지시문). 새 어휘·새 정규식을 짓지 않는다 — `section_intent.intent_for_label`
    (곧 `section_vocab.SECTION_TERMS` 최장 일치)이 이미 있는 유일한 판정기다.
    """
    intent = intent_for_label(label)
    row = intent.row if intent is not None else None
    return _SONGCUE_ROW_ROLE.get(row, "other")
