"""불러오기로 곡 제목이 바뀌어도 음원 링크가 따라온다(RED → GREEN).

``POST /api/timelines/{id}/load`` 는 라이브러리 이름을 ``song_title`` 로 덮어쓴다. 음원 링크의
열쇠는 ``(song_title, sequence_number)`` 라서, 이름이 다른 항목을 불러오면 새 열쇠로는 링크가
없어 곡을 다시 올려야 했다. 불러오기는 옛 열쇠의 링크를 새 열쇠로 **복제**해야 한다(옛 열쇠는
그대로 둔다).

콘솔 접촉: 0건. 링크는 저장소의 쓰기 경로(``SongAudioLinkStore.link``)로만 만든다.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from server.web.app import create_app

from .test_web_beat_grid_send_t563 import _deps as _web_deps

_AUDIO = b"RIFF-fake-audio-bytes"


def test_link_is_found_after_loading_a_library_entry_with_a_new_name(tmp_path):
    deps = _web_deps(tmp_path)
    current = deps.song_timeline_store.latest
    title = current["song_title"]
    sequence_number = current.get("sequence_number")
    renamed = "AUDIO LINK RENAMED"
    # 대조군: 이름이 정말 다르다. 같으면 이 시험은 아무것도 재지 못한다.
    assert renamed != title
    old_key = (title, sequence_number)
    new_key = (renamed, sequence_number)
    deps.song_audio_link_store.link(
        old_key, file_name="song.wav", mime_type="audio/wav", data=_AUDIO
    )
    # 대조군: 옛 열쇠에는 링크가 있고, 새 열쇠에는 아직 없다.
    assert deps.song_audio_link_store.resolve(old_key).status == "found"
    assert deps.song_audio_link_store.resolve(new_key).status == "none"

    with TestClient(create_app(deps)) as client:
        saved = client.post("/api/timelines", json={"name": renamed})
        assert saved.status_code == 200, saved.text
        loaded = client.post(f"/api/timelines/{saved.json()['item']['id']}/load")
        assert loaded.status_code == 200, loaded.text

    assert deps.song_timeline_store.latest["song_title"] == renamed
    result = deps.song_audio_link_store.resolve(new_key)
    assert result.status == "found", f"새 열쇠 {new_key} 의 링크 상태: {result.status}"
    assert result.data == _AUDIO
    # 옛 열쇠는 지우지 않는다.
    assert deps.song_audio_link_store.resolve(old_key).status == "found"
