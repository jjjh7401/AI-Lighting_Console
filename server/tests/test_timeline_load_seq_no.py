"""박자 격자 트랙의 콘솔 시퀀스 번호가 **불러오기** 응답에도 실린다(RED → GREEN).

``POST /api/timelines/{id}/load`` (``server/web/timeline_api.py``)는 화면용 값을 붙일 때
``track_sequence_numbers`` 를 넘기지 않아, 저장된 곡을 불러온 직후 응답의
``tracks[].sequence_number`` 가 빠진다. 새 연결의 재생(``ChatSession.song_timeline_replay``)은
같은 저장소의 반영 기록에서 번호를 읽어 싣는다. 그래서 같은 곡이 **들어온 길에 따라** 번호가
있거나 없게 보인다 — t644 가 잡은 불변식(불러오기 == 새 재생)이 시퀀스 번호에서도 깨진 것이다.

시험은 같은 불변식을 두 방향에서 잰다:

A. 반영 기록이 있는 트랙은 불러오기 응답에도 같은 ``sequence_number`` 를 싣고, 기록이 없는 트랙은
   키가 없다(``None`` 이 아니라 **키 없음**).
B. 불러오기 응답의 시퀀스 번호는 같은 저장소를 새 연결이 재생한 것과 같다.

콘솔 접촉: 0건. 반영 기록은 저장소의 쓰기 경로(``SongTimelineStore.set_beat_grid_allocation``,
카드 t572 — 「콘솔에 반영」이 실제로 남기는 모양)로만 만든다.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from server.web.app import create_app

from .conftest import drain_until
from .test_web_beat_grid_send_t563 import _deps as _web_deps

#: 키가 **없는** 것과 ``None`` 인 것을 가르는 표지 — ``dict.get`` 은 둘을 같은 ``None`` 으로 답한다.
_ABSENT = object()

_RECORDED_NUMBER = 282


def _track_numbers(beat_grid: dict) -> dict[str, object]:
    """그룹 이름 -> 응답 트랙의 ``sequence_number`` (키가 없으면 ``_ABSENT``)."""
    return {
        track["group_name"]: track.get("sequence_number", _ABSENT) for track in beat_grid["tracks"]
    }


def _shown(numbers: dict[str, object]) -> dict[str, object]:
    """실패 메시지용 — 키 없음 표지를 글로 바꾼다(센티넬 객체 주소가 메시지에 섞이지 않게)."""
    return {group: "키 없음" if number is _ABSENT else number for group, number in numbers.items()}


def _allocation_record(group: str) -> dict:
    """반영 기록의 모양(``updated_tracks_record``) — 그룹 하나만 번호가 있다."""
    return {
        "tracks": {
            group: {
                "sequence_number": _RECORDED_NUMBER,
                "sequence_name": "LDBEAT TEST",
                "cues": {},
            },
        }
    }


class TestLoadCarriesTheRecordedSequenceNumbers:
    def test_load_response_shows_the_recorded_console_sequence_number(self, tmp_path):
        deps = _web_deps(tmp_path)
        store = deps.song_timeline_store
        current = store.latest
        title = current["song_title"]
        recorded_group = current["beat_grid"]["tracks"][0]["group_name"]
        # 반영 기록을 저장소의 쓰기 경로로 남긴다. 곡 열쇠는 ``ChatSession._beat_grid_song_key`` 와
        # 같은 ``(song_title, sequence_number)`` 쌍이다.
        store.set_beat_grid_allocation(
            (title, current.get("sequence_number")), _allocation_record(recorded_group)
        )

        with TestClient(create_app(deps)) as client:
            saved = client.post("/api/timelines", json={"name": title})
            assert saved.status_code == 200, saved.text
            loaded = client.post(f"/api/timelines/{saved.json()['item']['id']}/load")
            assert loaded.status_code == 200, loaded.text
            with client.websocket_connect("/ws") as ws:
                replay = drain_until(ws, "song_timeline")

        loaded_numbers = _track_numbers(loaded.json()["timeline"]["beat_grid"])
        replay_numbers = _track_numbers(replay["timeline"]["beat_grid"])
        # 대조군: 재생된 것이 정말 같은 곡이고, 재생 쪽에는 기록된 번호가 **있다**. 이 줄이
        # 빠지면 아래 「같다」가 둘 다 빈 채로 공허하게 통과할 수 있다.
        assert replay["timeline"]["song_title"] == title
        assert replay_numbers[recorded_group] == _RECORDED_NUMBER
        # A-1. 불러오기 응답도 기록된 번호를 싣는다.
        assert loaded_numbers[recorded_group] == _RECORDED_NUMBER, (
            f"불러오기 응답에 {recorded_group} 번호가 없다 — 응답: {_shown(loaded_numbers)}"
        )
        # A-2. 기록이 없는 트랙에는 키 자체가 없다(지어내지 않는다).
        for group, number in loaded_numbers.items():
            if group != recorded_group:
                assert number is _ABSENT, f"기록 없는 {group} 에 번호가 붙었다: {number!r}"
        # B. 불러오기 응답 == 같은 저장소의 새 연결 재생.
        assert loaded_numbers == replay_numbers, (
            f"불러오기 응답이 새 연결 재생과 다르다 — 불러오기: {_shown(loaded_numbers)}, "
            f"재생: {_shown(replay_numbers)}"
        )

    def test_load_under_a_new_name_does_not_borrow_the_old_songs_number(self, tmp_path):
        """보조 가드: 다른 이름으로 저장해 불러오면 옛 곡의 번호를 빌려 오면 안 된다.

        곡 열쇠가 이름을 따라 바뀌므로 새 열쇠로는 기록이 없다. 번호를 이름을 바꾸기 **전**
        열쇠로 읽는 반쪽짜리 수정은 여기서 갈린다.
        """
        deps = _web_deps(tmp_path)
        store = deps.song_timeline_store
        current = store.latest
        title = current["song_title"]
        renamed = "LOAD SEQ RENAMED"
        # 대조군: 이름이 정말 다르다. 같으면 이 시험은 위 시험과 같은 시험이 된다.
        assert renamed != title
        recorded_group = current["beat_grid"]["tracks"][0]["group_name"]
        store.set_beat_grid_allocation(
            (title, current.get("sequence_number")), _allocation_record(recorded_group)
        )

        with TestClient(create_app(deps)) as client:
            saved = client.post("/api/timelines", json={"name": renamed})
            assert saved.status_code == 200, saved.text
            loaded = client.post(f"/api/timelines/{saved.json()['item']['id']}/load")
            assert loaded.status_code == 200, loaded.text
            with client.websocket_connect("/ws") as ws:
                replay = drain_until(ws, "song_timeline")

        assert replay["timeline"]["song_title"] == renamed
        loaded_numbers = _track_numbers(loaded.json()["timeline"]["beat_grid"])
        replay_numbers = _track_numbers(replay["timeline"]["beat_grid"])
        # 새 열쇠로는 기록이 없다 — 재생도 번호가 없어야 하고, 불러오기도 그래야 한다.
        assert all(n is _ABSENT for n in replay_numbers.values()), _shown(replay_numbers)
        assert loaded_numbers == replay_numbers, (
            f"이름 바꿔 불러온 응답이 재생과 다르다 — 불러오기: {_shown(loaded_numbers)}, "
            f"재생: {_shown(replay_numbers)}"
        )
