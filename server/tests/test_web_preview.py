from server.web.preview import build_execution_preview


def _preview(*commands: str) -> dict:
    return build_execution_preview(preview_id="preview-test", commands=list(commands))


def test_store_overwrite_cue_gets_caution_preview():
    preview = _preview("Store /Overwrite Cue 4")

    assert preview["preview_id"] == "preview-test"
    assert preview["risk_level"] == "caution"
    (command,) = preview["commands"]
    assert command["action"] == "store_overwrite"
    assert command["target_kind"] == "cue"
    assert command["target"] == "4"
    assert "Cue 4" in command["label"]
    assert preview["warnings"][0]["label"] == "덮어쓰기"


def test_delete_sequence_gets_danger_preview():
    preview = _preview("Delete Sequence 5")

    assert preview["risk_level"] == "danger"
    assert preview["commands"][0]["action"] == "delete"
    assert preview["warnings"][0]["severity"] == "danger"
    assert preview["warnings"][0]["label"] == "삭제 명령"


def test_blinder_full_intensity_gets_danger_and_intensity_context():
    preview = _preview("Group Blinder At Full")

    assert preview["risk_level"] == "danger"
    labels = {warning["label"] for warning in preview["warnings"]}
    assert "객석 블라인더" in labels
    assert "풀 인텐시티" in labels


def test_strobe_hz_gets_danger_preview():
    preview = _preview("Fixture 12 Attribute Strobe At 12 Hz")

    assert preview["risk_level"] == "danger"
    assert preview["warnings"][0]["label"] == "스트로브/셔터 변화"


def test_pan_tilt_gets_movement_caution_without_false_intensity_warning():
    preview = _preview('Fixture 3 Attribute "Pan" At 100')

    assert preview["risk_level"] == "caution"
    labels = {warning["label"] for warning in preview["warnings"]}
    assert "Pan/Tilt 이동" in labels
    assert "풀 인텐시티" not in labels
