"""실제 곡 구간 표본 — 카드 t429 보고에 실린 ``pilot_baseline.json`` 원본 (이름, 시작 시각).

원래 ``test_songcue_t429_repeat_chorus_collision.py`` 에 있었다. 그 파일은 룩 라이브러리
조립기(``build_songcue_bundle``)의 회귀 시험이라 카드 t480 D3 에서 조립기와 함께
은퇴했고, 두 곡 표본은 업로드 길 전후 비교(``.moai/reports/t480/m3_upload_dump.py``)가
계속 쓰므로 값 그대로 여기로 옮겼다.

두 코러스뿐인 최소 재현(Ice cream)과, 코러스·버스가 섞여 반복되는 더 큰 재현(Rain,
코러스 6회)이다.
"""

from __future__ import annotations

ICE_CREAM_SECTIONS: tuple[tuple[str, str], ...] = (
    ("Intro", "0:00"),
    ("Verse 1", "0:17"),
    ("Bridge 1", "0:27"),
    ("Chorus 1", "0:37"),
    ("Bridge 2", "0:47"),
    ("Chorus 2", "0:58"),
    ("Finale", "1:08"),
)

RAIN_SECTIONS: tuple[tuple[str, str], ...] = (
    ("Intro", "0:00"),
    ("Verse 1", "0:20"),
    ("Verse 2", "0:33"),
    ("Chorus 1", "0:49"),
    ("Chorus 2", "1:06"),
    ("Verse 3", "1:19"),
    ("Chorus 3", "1:46"),
    ("Chorus 4", "2:03"),
    ("Chorus 5", "2:18"),
    ("Verse 4", "2:46"),
    ("Chorus 6", "2:59"),
    ("Finale", "3:29"),
)
