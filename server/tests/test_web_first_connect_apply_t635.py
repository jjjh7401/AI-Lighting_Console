"""카드 t635 — 새 WebSocket 연결(새로고침·두 번째 탭)이 **「반영 기록」을 잃고**
반영 대기 배지를 틀리게 그리는 결함의 재현 시험 (RED 단계).

상단 바 「⇪ 반영」 배지의 값은 서버가 보내는 ``beat_grid.unsent_cells`` 하나다
(SPEC-LDBEAT-001 REQ-LDBEAT-011~013/017, 카드 t563·t568 계약 — ``test_beat_grid_send_t563.py``
의 ``TestBeatGridUnsentCells``). UI(``ui/src/components/beatgrid/pendingApplyCount.ts``)는
세 모양을 가른다: 키가 **없으면** 필드 없는 옛 서버로 읽어 배지를 숨기고, ``null`` 이면
「반영 기록 없음」이라 「—」로 보이고, 배열이면 그 길이를 그린다.

같은 뿌리에서 두 갈래가 나온다:

1. **재생(replay)이 파생 필드를 빼먹는다.** ``server/web/app.py`` 는 새 연결에
   ``deps.song_timeline_store.latest`` 를 **원본 그대로** 다시 보낸다.
   ``unsent_cells`` 는 ``ChatSession._beat_grid_refresh_unsent_cells`` 가 **보낼 때마다**
   붙이는 파생 필드라 저장소에는 없다 — 그래서 재생 프레임에는 키 자체가 없고,
   배지는 「—」가 아니라 **숨겨진다**.
2. **반영 기록이 연결 안에 갇혀 있다.** 「콘솔에 반영」이 성공하면 곡별 칸 스냅샷을
   ``ChatSession._beat_grid_snapshots`` 에 적는데, 이 사전은 연결(=세션)마다 새로
   만들어지고 저장소에서 복원되지 않는다. 방금 반영한 곡인데도 새 연결은 「반영 기록
   없음」(``None``)으로 시작한다 — 아무것도 안 바뀌었으면 ``[]`` 여야 한다.

탭 두 개 시험(``TestTwoTabsSharedRecord``)은 위 둘을 웹소켓 층에서 함께 잰다 — 탭이
동시에 여럿 열려 있어도 반영 기록은 **같은 곡에서만** 보여야 한다.

콘솔 접촉: 0건. ``FakeConsole``(승인=송신 각본)만 쓰고 실기 포트로는 한 바이트도
나가지 않는다. 이 파일의 시험 모두 기록 위치(스냅샷 사전)를 직접 쓰지 않는다 —
반영 기록은 실제 「콘솔에 반영」 성공 경로로만 만들어진다.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from server.web.app import create_app
from server.web.session import SongTimelineStore

from .conftest import drain_until
from .test_beat_grid_send_t563 import _new_session, _timeline
from .test_web_beat_grid_send_t563 import _approve_until, _send
from .test_web_beat_grid_send_t563 import _deps as _web_deps


class TestNewConnectionReplay:
    """WebSocket 층 — 새 연결이 받는 ``song_timeline`` 재생 프레임."""

    def test_new_connection_replays_timeline_with_unsent_cells_key(self, tmp_path):
        deps = _web_deps(tmp_path)
        stored = deps.song_timeline_store.latest
        # 전제(대조군): 저장소가 쥔 원본에는 파생 필드가 **없다**(보낼 때마다 붙는다).
        # 이 두 줄이 빠지면 아래 단언이 「키가 처음부터 저장돼 있었다」로 공허하게
        # 통과할 수 있다.
        assert isinstance(stored["beat_grid"], dict)
        assert "unsent_cells" not in stored["beat_grid"]

        with TestClient(create_app(deps)) as client, client.websocket_connect("/ws") as ws:
            event = drain_until(ws, "song_timeline")

        beat_grid = event["timeline"]["beat_grid"]
        # 이 프로세스에서는 누구도 「콘솔에 반영」을 한 적이 없으므로 값은 ``null``
        # (UI 가 「—」로 그리는 「반영 기록 없음」)이어야 하고, 키가 **있어야** 한다.
        assert "unsent_cells" in beat_grid, (
            f"재생된 beat_grid 에 unsent_cells 키가 없다(배지가 숨겨진다) — 키: {sorted(beat_grid)}"
        )
        assert beat_grid["unsent_cells"] is None


class TestApplyRecordAcrossConnections:
    """세션 층 — 새 연결 = 새 ``ChatSession``(``app.py`` 가 연결마다 새로 만든다)."""

    def test_apply_record_survives_a_new_connection(self, tmp_path):
        store = SongTimelineStore()
        store.latest = _timeline()

        # 연결 A — 실제 「콘솔에 반영」(승인=송신) 성공 경로. 스냅샷은 직접 쓰지 않는다.
        session_a, _console_a, _approval_a, _audit_a = _new_session(tmp_path, store=store)
        applied = session_a.beat_grid_apply()
        # 대조군: 반영이 승인=송신까지 정말 성공했고, A 자신은 「반영 기록과 같음」을
        # 본다. 이 줄들이 빠지면 아래 B 의 ``None`` 이 「반영이 안 됐다」와 구별되지 않는다.
        assert applied["ok"] is True
        assert applied["approval_vs_sent"]["match"] is True
        assert session_a._beat_grid_current_unsent_cells() == []

        # 연결 B — 같은 저장소, 새 ChatSession, 그 사이 편집 0건. 곡도 격자도 그대로이니
        # 반영 기록과 지금의 차이는 없다 — ``None``(기록 없음)이 아니라 ``[]`` 여야 한다.
        session_b, _console_b, _approval_b, _audit_b = _new_session(tmp_path, store=store)
        assert session_b is not session_a
        assert session_b._beat_grid_current_unsent_cells() == []


class TestTwoTabsSharedRecord:
    """WebSocket 층 — 탭 두 개가 **동시에** 열려 있어도 반영 기록은 같은 곡에서만 보인다.

    한 탭이 「콘솔에 반영」을 마친 뒤에 열리는 탭은 새 연결이라 새 ``ChatSession`` 을
    받는다. 기록이 연결마다 따로 있으면 그 탭의 배지는 「—」(``null``)로 거짓이 된다.
    같은 곡이면 어느 탭이든 「반영 기록과 같음」(``[]``)이어야 하고, 반영한 적 없는
    곡으로는 기록이 새지 않아야 한다."""

    def test_two_tabs_share_the_apply_record_for_the_same_song_only(self, tmp_path):
        deps = _web_deps(tmp_path)
        store = deps.song_timeline_store

        with (
            TestClient(create_app(deps)) as client,
            client.websocket_connect("/ws") as applying_tab,
        ):
            # (a) 실제 「콘솔에 반영」(승인=송신) 성공 경로를 웹소켓으로 보낸다 — 스냅샷
            # 사전은 직접 쓰지 않는다. 반영한 탭은 끝까지 닫지 않는다: 「탭을 닫을 때 기록을
            # 넘겨주는」 구현이 아니라, 열려 있는 연결과도 기록이 나뉘지 않는지를 재려는 것이다.
            _send(applying_tab, type="beat_grid_apply")
            status = _approve_until(applying_tab, "beat_grid_send_status")
            assert status["last_action"] == "apply"
            assert status["ok"] is True
            assert status["approval_vs_sent"]["match"] is True
            # 대조군: 반영한 연결 자신은 「반영 기록과 같음」을 본다. 이 줄이 빠지면 아래
            # 탭의 ``null`` 이 「반영이 안 됐다」와 구별되지 않는다.
            assert status["pending_apply_count"] == 0

            # (b) 반영이 끝난 뒤 탭 둘을 동시에 연다. 서버는 연결마다 마지막 타임라인을
            # 재생하므로, 이 프레임이 두 탭의 배지가 처음 읽는 값이다.
            with client.websocket_connect("/ws") as tab_1, client.websocket_connect("/ws") as tab_2:
                replay_1 = drain_until(tab_1, "song_timeline")
                replay_2 = drain_until(tab_2, "song_timeline")

                # (c) 같은 곡 — 두 탭 모두 「반영 기록과 같음」이어야 한다. 지금은 기록이
                # 반영한 연결 안에 갇혀 있어 새 탭은 ``None``(「—」)으로 시작한다.
                assert replay_1["timeline"]["beat_grid"]["unsent_cells"] == []
                assert replay_2["timeline"]["beat_grid"]["unsent_cells"] == []

                # (d) 다른 곡 대조 — 격자 내용은 그대로 두고 곡 열쇠(제목·번호)만 바꾼
                # 사본으로 갈아 끼운 뒤 새 탭을 연다. 이 곡은 반영한 적이 없으니 ``None``
                # 이어야 한다. 기록을 공유하는 구현(위 갈래 2)이 없는 지금도 통과하는 게
                # 정상이다 — 나중에 기록이 곡 열쇠 없이 공유되면 격자가 같아서 이 곡도 ``[]``
                # 로 읽히므로 여기서 잡힌다(「같은 곡에서만」 보인다는 조건을 지키는 단언).
                store.latest = {**store.latest, "song_title": "OTHER SONG", "sequence_number": 211}
                with client.websocket_connect("/ws") as tab_3:
                    replay_3 = drain_until(tab_3, "song_timeline")
                # 대조군: 재생된 것이 정말 다른 곡이다.
                assert replay_3["timeline"]["song_title"] == "OTHER SONG"
                assert replay_3["timeline"]["beat_grid"]["unsent_cells"] is None
