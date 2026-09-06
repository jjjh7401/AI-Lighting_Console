"""Maroon 5 — Sugar 의 LX-SEQ 조명 설계를 앱 타임라인 페이로드로 옮긴 것.

정본은 감독이 만든 단일 HTML 산출물 ``LXSEQ_SAMPLE_01_Sugar_r3.timeline.html``
(LX-SEQ v2.1 · r3) 이고, 이 모듈은 그 문서의 큐시트 18행(Q010~Q180)과 헤더 메타를
t279 가 넓힌 ``SongTimelineSection`` / ``SongTimelineView`` 필드에 그대로 싣는다.
서버가 만들어 내는 값이 아니라 **옮겨 적은 값**이다 — 문서에 없는 큐·색·수치는
만들지 않고, 문서에서 빈 칸(``—``)인 자리는 키 자체를 내지 않는다.

## 곡 사실 (문서 헤더 + 공개 자료 대조)

03:56.0 · 120 BPM · 4/4 · D♭ major · 118마디 · 1마디 2.000s. songbpm / Tunebat /
Musicstax / Wikipedia 로 확인한 값이 문서 헤더와 정확히 일치한다.

## 타임코드의 출처 — DERIVED

``tc_method`` 는 ``"DERIVED"`` 다. 이 타임코드는 마디 연산(1마디 2.000s)으로 도출한
값이고 음원 청취로 검증하지 않았다. 앱은 이 값을 실측처럼 보여선 안 되며,
``tc_method_warning`` 이 화면 배너 문구로 그대로 나간다.

## 옮기면서 계산한 것 (문서에 문장으로 없는 것)

문서는 마디 번호를 열로 갖고 있지 않고, 구간 밴드에만 마디 수를 적는다. 아래 세
필드는 문서가 적어 둔 TC 와 「1마디 2.000s」에서 나온 산술이지 새 정보가 아니다.

* ``bar_start`` = ``start_ms / 2000 + 1``
* ``bar_count`` = ``duration_ms / 2000``
* ``d_level`` = ``ceil(intensity / 20)`` (1~5 로 자름) — 기존 모델의 필수 5단계
  축이라 비울 수 없어, 문서의 Intensity 값에서 환산했다.

``position`` / ``texture`` 는 t279 이전부터 있던 필수 필드다. 문서에 대응 열이 없어
같은 정보의 다른 표현(Movement / Mood)을 넣는다 — t280 시각 확인용 픽스처
``ui/src/components/cueSheetExample.ts`` 와 같은 규약이다.

Intensity 칸이 그룹으로 나뉘지 않은 행(예: Q010 의 ``55``)은 리그 전체를 뜻하므로
그룹 이름 ``ALL`` 로 싣는다. 그룹별로 적힌 행(``KEY 70 / BACK 35``)은 적힌 그대로다.
"""

from __future__ import annotations

import math

__all__ = [
    "SUGAR_ENTRY_ID",
    "SUGAR_TIMELINE_NAME",
    "build_sugar_timeline",
    "sugar_library_entry",
]

SUGAR_ENTRY_ID = "seed-sugar-r3"
SUGAR_TIMELINE_NAME = "Maroon 5 — Sugar"

#: 문서 헤더의 「1마디 2.000s」.
_SECONDS_PER_BAR = 2.0

_PALETTE_LEGEND: tuple[dict[str, str], ...] = (
    {"id": "P1", "name": "골드 앰버", "color": "#FFB43C"},
    {"id": "P2", "name": "웜 화이트", "color": "#FFE0B0"},
    {"id": "P4", "name": "핫 핑크", "color": "#FF3C9E"},
    {"id": "P5", "name": "딥 퍼플", "color": "#5A2BC8"},
    {"id": "P6", "name": "터쿼이즈", "color": "#2ED8D8"},
    {"id": "P7", "name": "선셋 오렌지", "color": "#FF6A28"},
    {"id": "P8", "name": "블랙아웃", "color": "#101418"},
)

_DERIVED_WARNING = (
    "이 타임라인의 모든 타임코드는 마디 연산(1마디 = 2.000s)으로 도출한 값입니다. "
    "음원 청취로 검증하지 않았습니다. 픽업·하프바 삽입이 있으면 전 구간이 어긋납니다. "
    "리허설에서 LTC 대조 필수."
)

# 큐시트 18행. 열 순서는 정본 표와 같다:
#   (Q#, Section, TC In ms, TC Out ms|None, Mood, Color 주, Color 보조|None,
#    Intensity[(group, level)], Fixture Group, Movement, Effect, Trans,
#    Fade, Note, [MANUAL])
_ROWS: tuple[dict[str, object], ...] = (
    {
        "cue": 10,
        "label": "INTRO",
        "start": 0,
        "end": 8_000,
        "mood": "화사, 등장",
        "primary": "P1 골드앰버",
        "secondary": "P2 웜화이트",
        "intensity": (("ALL", 55),),
        "groups": ("BACK", "WASH-U", "HAZE"),
        "movement": "STATIC",
        "effect": "NONE",
        "trans": "SNAP",
        "fade": 0.0,
        "note": "[MANUAL] 헤이즈 곡 시작 30초 전 선투입 · 첫 박에 스냅 인",
        "manual": True,
    },
    {
        "cue": 20,
        "label": "VERSE1",
        "start": 8_000,
        "end": 24_000,
        "mood": "경쾌, 근접",
        "primary": "P2 웜화이트",
        "secondary": "P1 골드앰버",
        "intensity": (("KEY", 70), ("BACK", 35)),
        "groups": ("KEY", "BACK"),
        "movement": "STATIC",
        "effect": "NONE",
        "trans": "XFADE",
        "fade": 1.5,
        "note": "보컬 인 · 페이스 확보 우선, 백라이트 낮게",
    },
    {
        "cue": 30,
        "label": "VERSE1",
        "start": 24_000,
        "end": 40_000,
        "mood": "확장, 그루브",
        "primary": "P2 웜화이트",
        "secondary": "P6 터쿼이즈",
        "intensity": (("KEY", 70), ("SIDE", 40)),
        "groups": ("KEY", "BACK", "SIDE-L", "SIDE-R"),
        "movement": "STATIC",
        "effect": "PULSE @2bar",
        "trans": "XFADE",
        "fade": 2.0,
        "note": "사이드 합류로 폭 확보 · 펄스는 2마디 주기 얕게",
    },
    {
        "cue": 40,
        "label": "PRE1",
        "start": 40_000,
        "end": 56_000,
        "mood": "축적, 상승",
        "primary": "P6 터쿼이즈",
        "secondary": "P5 딥퍼플",
        "intensity": (("ALL", 60),),
        "groups": ("SIDE-L", "SIDE-R", "MOVER-U"),
        "movement": "TILT-UP @slow",
        "effect": "BREATHE @1bar",
        "trans": "FADE",
        "fade": 8.0,
        "note": "8초에 걸쳐 서서히 · 후렴 직전 60 도달",
    },
    {
        "cue": 50,
        "label": "CHORUS1",
        "start": 56_000,
        "end": 72_000,
        "mood": "개방, 축제",
        "primary": "P4 핫핑크",
        "secondary": "P1 골드앰버",
        "intensity": (("ALL", 90),),
        "groups": ("MOVER-U", "MOVER-D", "BACK", "WASH-D"),
        "movement": "FAN-OUT @mid",
        "effect": "CHASE @1/8",
        "trans": "SNAP",
        "fade": 0.0,
        "note": "후렴 첫 박 정확히 · 1차 웨이브 정점",
    },
    {
        "cue": 60,
        "label": "CHORUS1",
        "start": 72_000,
        "end": 88_000,
        "mood": "유지, 회전",
        "primary": "P4 핫핑크",
        "secondary": "P6 터쿼이즈",
        "intensity": (("ALL", 90),),
        "groups": ("MOVER-U", "MOVER-D", "BACK"),
        "movement": "CIRCLE @mid",
        "effect": "CHASE @1/8",
        "trans": "XFADE",
        "fade": 1.0,
        "note": "강도 유지, 색만 교체 · 후렴 후반 지루함 방지",
    },
    {
        "cue": 70,
        "label": "VERSE2",
        "start": 88_000,
        "end": 104_000,
        "mood": "하강, 근접",
        "primary": "P2 웜화이트",
        "secondary": "P5 딥퍼플",
        "intensity": (("KEY", 65), ("BACK", 30)),
        "groups": ("KEY", "BACK"),
        "movement": "STATIC",
        "effect": "NONE",
        "trans": "XFADE",
        "fade": 2.0,
        "note": "2차 웨이브 시작 · V1보다 5 낮게 잡아 후속 상승폭 확보",
    },
    {
        "cue": 80,
        "label": "PRE2",
        "start": 104_000,
        "end": 120_000,
        "mood": "축적, 압박",
        "primary": "P6 터쿼이즈",
        "secondary": "P4 핫핑크",
        "intensity": (("ALL", 70),),
        "groups": ("SIDE-L", "SIDE-R", "MOVER-U", "LED-W"),
        "movement": "TILT-UP @mid",
        "effect": "PULSE @1beat",
        "trans": "FADE",
        "fade": 8.0,
        "note": "PRE1보다 10 높게 · LED월 합류 · 펄스 1박 주기로 조임",
    },
    {
        "cue": 90,
        "label": "CHORUS2",
        "start": 120_000,
        "end": 136_000,
        "mood": "개방, 확산",
        "primary": "P4 핫핑크",
        "secondary": "P7 선셋오렌지",
        "intensity": (("ALL", 95),),
        "groups": ("MOVER-U", "MOVER-D", "BACK", "WASH-D", "LED-W"),
        "movement": "FAN-OUT @fast",
        "effect": "CHASE @1/8",
        "trans": "SNAP",
        "fade": 0.0,
        "note": "2차 웨이브 정점 · 1차보다 5 높게",
    },
    {
        "cue": 100,
        "label": "CHORUS2",
        "start": 136_000,
        "end": 152_000,
        "mood": "유지, 확장",
        "primary": "P1 골드앰버",
        "secondary": "P4 핫핑크",
        "intensity": (("ALL", 95),),
        "groups": ("MOVER-U", "MOVER-D", "BACK", "WASH-D", "LED-W", "BLIND"),
        "movement": "SWEEP-H @fast",
        "effect": "CHASE @1/8",
        "trans": "XFADE",
        "fade": 1.0,
        "note": "블라인더 합류 · 객석 직사 각도 리허설에서 확정",
    },
    {
        "cue": 110,
        "label": "BRIDGE",
        "start": 152_000,
        "end": 160_000,
        "mood": "절제, 집중",
        "primary": "P5 딥퍼플",
        "secondary": None,
        "intensity": (("ALL", 35),),
        "groups": ("KEY", "BACK"),
        "movement": "STATIC",
        "effect": "NONE",
        "trans": "XFADE",
        "fade": 2.5,
        "note": "급강하 · 3차 웨이브 lull 구간, 낙차 확보가 목적",
    },
    {
        "cue": 120,
        "label": "BRIDGE",
        "start": 160_000,
        "end": 168_000,
        "mood": "재점화, 축적",
        "primary": "P5 딥퍼플",
        "secondary": "P4 핫핑크",
        "intensity": (("ALL", 75),),
        "groups": ("KEY", "BACK", "SIDE-L", "SIDE-R"),
        "movement": "TILT-UP @fast",
        "effect": "BREATHE @1bar",
        "trans": "FADE",
        "fade": 7.0,
        "note": "마지막 후렴 직전까지 7초 상승 · 35→75",
    },
    {
        "cue": 130,
        "label": "CHORUS3",
        "start": 168_000,
        "end": 184_000,
        "mood": "폭발, 최대",
        "primary": "P4 핫핑크",
        "secondary": "P1 골드앰버",
        "intensity": (("ALL", 100),),
        "groups": (
            "MOVER-U",
            "MOVER-D",
            "BACK",
            "WASH-D",
            "WASH-U",
            "SIDE-L",
            "SIDE-R",
            "LED-W",
        ),
        "movement": "FAN-OUT @fast",
        "effect": "CHASE @1/8",
        "trans": "SNAP",
        "fade": 0.0,
        "note": "곡 전체 최고점 · 가용 그룹 전개 (FOH 제외)",
    },
    {
        "cue": 140,
        "label": "CHORUS3",
        "start": 184_000,
        "end": 200_000,
        "mood": "유지, 회전",
        "primary": "P7 선셋오렌지",
        "secondary": "P6 터쿼이즈",
        "intensity": (("ALL", 100),),
        "groups": (
            "MOVER-U",
            "MOVER-D",
            "BACK",
            "WASH-D",
            "WASH-U",
            "SIDE-L",
            "SIDE-R",
            "LED-W",
        ),
        "movement": "CIRCLE @fast",
        "effect": "RAINBOW",
        "trans": "XFADE",
        "fade": 1.0,
        "note": "더블 후렴 전반부 종료 · 색상만 순환시켜 체감 변화 유지",
    },
    {
        "cue": 150,
        "label": "CHORUS3",
        "start": 200_000,
        "end": 216_000,
        "mood": "최고조, 난반사",
        "primary": "P4 핫핑크",
        "secondary": "P6 터쿼이즈",
        "intensity": (("ALL", 100),),
        "groups": (
            "MOVER-U",
            "MOVER-D",
            "BACK",
            "WASH-D",
            "SIDE-L",
            "SIDE-R",
            "LED-W",
            "BLIND",
            "STROBE",
        ),
        "movement": "SWEEP-H @fast",
        "effect": "STROBE @2bar",
        "trans": "SNAP",
        "fade": 0.0,
        "note": "스트로브 구간 · 광과민성 사전 고지 필수 · 2마디 주기로 제한",
    },
    {
        "cue": 160,
        "label": "CHORUS3",
        "start": 216_000,
        "end": 232_000,
        "mood": "해소 준비",
        "primary": "P1 골드앰버",
        "secondary": "P2 웜화이트",
        "intensity": (("ALL", 85),),
        "groups": ("MOVER-U", "MOVER-D", "BACK", "WASH-D"),
        "movement": "CIRCLE @mid",
        "effect": "TWINKLE",
        "trans": "XFADE",
        "fade": 2.0,
        "note": "스트로브 해제 · 색온도 회복하며 종료 준비",
    },
    {
        "cue": 170,
        "label": "OUTRO",
        "start": 232_000,
        "end": 236_000,
        "mood": "잔향, 종료",
        "primary": "P1 골드앰버",
        "secondary": None,
        "intensity": (("ALL", 20),),
        "groups": ("BACK", "WASH-U"),
        "movement": "STATIC",
        "effect": "NONE",
        "trans": "FADE",
        "fade": 3.5,
        "note": "마지막 음 위에서 하강 · 85→20",
    },
    {
        # 정본 표에서 TC Out 과 Dur 이 둘 다 `—` 인 유일한 행이다. 없는 칸은
        # 만들어 넣지 않는다 — end_ms / duration_ms / bar_count 키 자체가 없다.
        "cue": 180,
        "label": "OUTRO",
        "start": 236_000,
        "end": None,
        "mood": "암전",
        "primary": "P8 블랙아웃",
        "secondary": None,
        "intensity": (("ALL", 0),),
        "groups": ("ALL",),
        "movement": "STATIC",
        "effect": "NONE",
        "trans": "FADE",
        "fade": 1.5,
        "note": "[MANUAL] 곡 종료 확인 후 · 다음 곡 인계 시 BACK 15% 잔광 유지",
        "manual": True,
    },
)


def _d_level(intensity: tuple[tuple[str, int], ...]) -> int:
    """문서의 Intensity 값에서 환산한 1~5 축. 문서가 적어 둔 값이 아니다."""
    peak = max(level for _, level in intensity)
    return min(5, max(1, math.ceil(peak / 20)))


def _bar_number(start_ms: int) -> int:
    return int(start_ms / 1000 / _SECONDS_PER_BAR) + 1


def _section(index: int, row: dict[str, object]) -> dict[str, object]:
    start = int(row["start"])  # type: ignore[arg-type]
    end = row["end"]
    intensity: tuple[tuple[str, int], ...] = row["intensity"]  # type: ignore[assignment]
    primary = str(row["primary"])
    secondary = row["secondary"]
    movement = str(row["movement"])
    mood = str(row["mood"])

    section: dict[str, object] = {
        # -- t279 이전부터 있던 필수 필드 --
        "index": index,
        "label": row["label"],
        "start_ms": start,
        "cue_number": row["cue"],
        "d_level": _d_level(intensity),
        "palette": [primary] if secondary is None else [primary, str(secondary)],
        "position": movement,
        "texture": mood,
        "fx": [] if row["effect"] == "NONE" else [str(row["effect"])],
        "accents": [],
        "mib": False,
        "trig_time_seconds": start / 1000,
        # -- LX-SEQ 큐시트 확장 (t279) --
        "bar_start": _bar_number(start),
        "mood": mood,
        "palette_primary": primary,
        "intensity": [{"group": group, "level": level} for group, level in intensity],
        "fixture_groups": list(row["groups"]),  # type: ignore[arg-type]
        "movement": movement,
        "effect": row["effect"],
        "trans": row["trans"],
        "fade_seconds": row["fade"],
        "note": row["note"],
        "manual": bool(row.get("manual", False)),
    }
    if secondary is not None:
        section["palette_secondary"] = str(secondary)
    if end is not None:
        end_ms = int(end)  # type: ignore[arg-type]
        section["end_ms"] = end_ms
        section["duration_ms"] = end_ms - start
        section["bar_count"] = int((end_ms - start) / 1000 / _SECONDS_PER_BAR)
    return section


def build_sugar_timeline() -> dict[str, object]:
    """정본 문서를 옮긴 감독 타임라인 페이로드 (읽기 전용 리뷰 투영)."""
    return {
        "song_title": SUGAR_TIMELINE_NAME,
        "sequence_name": None,
        "sequence_number": 0,
        "timing_mode": "timecode",
        "timecode_number": None,
        "lifecycle": "pending_approval",
        "approval": "pending_review",
        "director_decisions": [],
        "sections": [_section(i + 1, row) for i, row in enumerate(_ROWS)],
        "lint": [],
        "unresolved": [],
        "disabled": [],
        "readback": {"verified": None, "message": None},
        # -- 헤더 메타 (문서 헤더 그대로) --
        "bpm": 120,
        "time_signature": "4/4",
        "musical_key": "D♭ major",
        "total_duration_ms": 236_000,
        "bar_count": 118,
        "seconds_per_bar": _SECONDS_PER_BAR,
        "tc_source": "LTC",
        "tc_origin": "00:00.0 = 곡 첫 음 (카운트인 없음)",
        "tc_method": "DERIVED",
        "tc_method_warning": _DERIVED_WARNING,
        "palette_legend": [dict(entry) for entry in _PALETTE_LEGEND],
    }


def sugar_library_entry() -> dict[str, object]:
    """``SongTimelineLibrary`` 항목 한 칸 — {id, name, saved_at, timeline}."""
    return {
        "id": SUGAR_ENTRY_ID,
        "name": SUGAR_TIMELINE_NAME,
        # 정본 산출물의 생성일(r3). 시드는 매번 새로 저장되는 값이 아니라
        # 고정된 문서 한 판이라, 실행 시각이 아니라 문서 날짜를 적는다.
        "saved_at": "2026-08-21T00:00:00+00:00",
        "timeline": build_sugar_timeline(),
    }
