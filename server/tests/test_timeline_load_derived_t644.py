"""카드 t644 — 라이브러리에서 곡을 **불러오면** 응답의 ``beat_grid`` 에 파생 필드가 없는
결함의 재현 시험 (RED 단계).

상단 바 「⇪ 반영」 배지와 박자 격자 표식은 서버가 **보낼 때마다** ``beat_grid`` 에 붙이는
파생 필드 다섯(``unsent_cells`` · ``unverified_cells`` · ``movement_vocabulary`` ·
``fx_templates`` · ``empty_preset_cells``)을 읽는다. 붙이는 자리는
``ChatSession._beat_grid_refresh_unsent_cells`` 하나이고, 새 연결의 재생
(``ChatSession.song_timeline_replay`` — 카드 t635)도 거기를 지난다.

그런데 ``POST /api/timelines/{id}/load`` (``server/web/timeline_api.py``)는 저장된 항목을
얕게 복사해 ``song_title`` 만 라이브러리 이름으로 바꾼 뒤 **원본 모양 그대로** 저장소에 놓고
그대로 응답한다. UI 는 이 응답을 곧장 ``applySongTimeline`` 에 넘기고
(``ui/src/timelineLibrary.ts`` → ``TimelineLibrary.tsx`` → ``App.tsx``) 웹소켓으로 다시
묻지 않는다. 그래서 파생 필드는 다음 편집·반영이 올 때까지 **없는 채로** 남는다 — 키가
없으면 UI 는 필드 없는 옛 서버로 읽어 배지를 숨긴다(``pendingApplyCount.ts``). 같은 곡을
새로고침하면(재생 경로) 맞게 나오니, 같은 곡이 **들어온 길에 따라** 달리 보이는 셈이다.

세 시험은 같은 불변식을 세 방향에서 잰다:

A. 응답에 파생 필드 다섯이 **키로** 들어 있다(반영 기록이 없으면 ``unsent_cells`` 는 ``null``).
B. 응답은 같은 저장소 내용을 새 연결이 재생한 것과 **같다**.
C. 이 프로세스에서 「콘솔에 반영」을 마친 곡을 불러오면 응답이 **참인 대기 수**(``[]``)를 싣는다.

콘솔 접촉: 0건. ``FakeConsole``(승인=송신 각본)만 쓰고 실기 포트로는 한 바이트도 나가지
않는다. 시험 C 의 반영 기록은 실제 「콘솔에 반영」 성공 경로로만 만들어진다 — 스냅샷 사전을
직접 쓰지 않는다.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from server.web.app import create_app

from .conftest import drain_until
from .test_web_beat_grid_send_t563 import _approve_until, _send
from .test_web_beat_grid_send_t563 import _deps as _web_deps

#: 보낼 때마다 ``ChatSession._beat_grid_refresh_unsent_cells`` 가 ``beat_grid`` 에 붙이는
#: 파생 필드 다섯. 저장소가 쥔 원본에는 하나도 없다.
_DERIVED_KEYS = (
    "unsent_cells",
    "unverified_cells",
    "movement_vocabulary",
    "fx_templates",
    "empty_preset_cells",
)

#: 키가 **없는** 것과 값이 ``None`` 인 것을 가르는 표지 — ``dict.get`` 은 둘을 같은
#: ``None`` 으로 답하는데, ``unsent_cells`` 가 정확히 그 두 갈래(숨김 / 「—」)다.
_ABSENT = object()


def _save_and_load(client: TestClient, name: str) -> dict:
    """저장소의 현재 타임라인을 라이브러리에 ``name`` 으로 저장하고, 곧바로 그 항목을
    불러온 응답 본문을 돌려준다(UI 의 「저장」 → 「불러오기」와 같은 두 REST 호출)."""
    saved = client.post("/api/timelines", json={"name": name})
    assert saved.status_code == 200, saved.text
    entry_id = saved.json()["item"]["id"]
    loaded = client.post(f"/api/timelines/{entry_id}/load")
    assert loaded.status_code == 200, loaded.text
    body = loaded.json()
    assert body["ok"] is True
    return body


def _differing_keys(left: dict, right: dict) -> list[str]:
    """값이 다르거나 한쪽에만 있는 키. 안쪽 사전은 ``beat_grid.unsent_cells`` 처럼 점으로 잇는다."""
    differing: list[str] = []
    for key in sorted(left.keys() | right.keys()):
        a, b = left.get(key, _ABSENT), right.get(key, _ABSENT)
        if a == b:
            continue
        if isinstance(a, dict) and isinstance(b, dict):
            differing.extend(f"{key}.{inner}" for inner in _differing_keys(a, b))
        else:
            differing.append(key)
    return differing


class TestLoadResponseDerivedFields:
    """REST 층 — ``POST /api/timelines/{id}/load`` 의 응답이 곧 UI 가 그리는 타임라인이다."""

    def test_load_response_carries_the_derived_beat_grid_fields(self, tmp_path):
        deps = _web_deps(tmp_path)
        stored_grid = deps.song_timeline_store.latest["beat_grid"]
        # 전제(대조군): 저장소가 쥔 원본에는 파생 필드가 **하나도** 없다(보낼 때마다 붙는다).
        # 이 줄이 빠지면 아래 단언이 「키가 처음부터 저장돼 있었다」로 공허하게 통과할 수 있다.
        assert [key for key in _DERIVED_KEYS if key in stored_grid] == []

        with TestClient(create_app(deps)) as client:
            loaded = _save_and_load(client, "T644 LOAD")

        beat_grid = loaded["timeline"]["beat_grid"]
        missing = [key for key in _DERIVED_KEYS if key not in beat_grid]
        # 키가 없으면 UI 는 「필드 없는 옛 서버」로 읽어 배지를 숨긴다 — 값이 무엇이든
        # 키 자체가 와야 한다. 하나씩 가르되, 빠진 키 전부를 메시지에 같이 적는다.
        for key in _DERIVED_KEYS:
            assert key in beat_grid, (
                f"불러오기 응답의 beat_grid 에 {key} 키가 없다 — 빠진 키: {missing}, "
                f"있는 키: {sorted(beat_grid)}"
            )
        # 이 프로세스에서는 누구도 「콘솔에 반영」을 한 적이 없으므로 값은 ``null``(UI 가
        # 「—」로 그리는 「반영 기록 없음」)이다 — 키가 없어 배지가 숨겨지는 것과 다른 사실이다.
        assert beat_grid["unsent_cells"] is None, (
            f"반영한 적 없는 곡인데 unsent_cells 가 null 이 아니다: {beat_grid['unsent_cells']!r}"
        )

    def test_load_response_matches_a_fresh_connection_replay(self, tmp_path):
        deps = _web_deps(tmp_path)

        with TestClient(create_app(deps)) as client:
            loaded = _save_and_load(client, "T644 LOAD")
            # 불러오기가 저장소에 놓은 그 곡을 새 연결이 그대로 재생한다(``app.py`` 가 연결마다
            # ``song_timeline_replay`` 를 보낸다) — 같은 곡의 「다른 길」이다.
            with client.websocket_connect("/ws") as ws:
                replay = drain_until(ws, "song_timeline")

        loaded_timeline = loaded["timeline"]
        replayed_timeline = replay["timeline"]
        # 대조군 1: 재생된 것이 정말 방금 불러온 곡이다.
        assert replayed_timeline["song_title"] == "T644 LOAD"
        # 대조군 2: 재생 쪽에는 파생 필드가 **있다**(카드 t635). 이 줄이 빠지면 응답과 재생이
        # 둘 다 비어 「같다」로 공허하게 통과할 수 있다.
        replay_missing = [key for key in _DERIVED_KEYS if key not in replayed_timeline["beat_grid"]]
        assert replay_missing == []

        differing = _differing_keys(loaded_timeline, replayed_timeline)
        assert loaded_timeline == replayed_timeline, (
            f"불러오기 응답이 같은 곡의 새 연결 재생과 다르다 — 다른 키: {differing}"
        )


class TestLoadAfterAnApplyInThisProcess:
    """WebSocket + REST 층 — 반영 기록은 프로세스 단위로 공유된다(카드 t635). 한 탭이 「콘솔에
    반영」을 마친 **뒤에** 같은 곡을 라이브러리에서 불러오면, 불러오기 응답도 그 기록을 본다."""

    def test_load_after_an_apply_in_this_process_shows_the_true_pending_count(self, tmp_path):
        deps = _web_deps(tmp_path)
        applied_title = deps.song_timeline_store.latest["song_title"]

        with (
            TestClient(create_app(deps)) as client,
            client.websocket_connect("/ws") as applying_tab,
        ):
            # (a) 실제 「콘솔에 반영」(승인=송신) 성공 경로를 웹소켓으로 보낸다 — 스냅샷 사전은
            # 직접 쓰지 않는다. 반영한 탭은 끝까지 닫지 않는다(t635 와 같은 이유).
            _send(applying_tab, type="beat_grid_apply")
            status = _approve_until(applying_tab, "beat_grid_send_status")
            # 대조군: 반영이 승인=송신까지 정말 성공했고, 반영한 연결 자신은 「반영 기록과
            # 같음」을 본다. 이 줄들이 빠지면 아래 불러오기 응답의 값이 「반영이 안 됐다」와
            # 구별되지 않는다.
            assert status["last_action"] == "apply"
            assert status["ok"] is True
            assert status["approval_vs_sent"]["match"] is True
            assert status["pending_apply_count"] == 0

            # (b) 반영한 곡을 **반영한 곡의 제목**으로 저장하고 불러온다. 불러오기는 라이브러리
            # 이름을 ``song_title`` 로 쓰고(``timeline_api.py``) 곡 열쇠는
            # ``(song_title, sequence_number)`` 라서, 다른 이름으로 저장하면 다른 곡이 된다.
            loaded = _save_and_load(client, applied_title)

            # 대조군: 같은 곡을 새 연결이 재생하면 「반영 기록과 같음」(``[]``)이다. 이 줄이
            # 빠지면 아래 응답의 기대값 ``[]`` 가 곡 열쇠가 어긋난 채 세운 것인지 가려지지
            # 않는다(어긋났다면 ``null`` 이 참이다).
            with client.websocket_connect("/ws") as fresh_tab:
                replay = drain_until(fresh_tab, "song_timeline")
            assert replay["timeline"]["song_title"] == applied_title
            assert replay["timeline"]["beat_grid"]["unsent_cells"] == []

        # (c) 불러오기 응답 자신이 참인 대기 수를 싣는지 — 키부터, 그다음 값.
        beat_grid = loaded["timeline"]["beat_grid"]
        assert "unsent_cells" in beat_grid, (
            f"불러오기 응답의 beat_grid 에 unsent_cells 키가 없다(배지가 숨겨진다) — "
            f"키: {sorted(beat_grid)}"
        )
        assert beat_grid["unsent_cells"] == [], (
            f"방금 반영한 곡인데 불러오기 응답의 unsent_cells 가 [] 가 아니다: "
            f"{beat_grid['unsent_cells']!r}"
        )
