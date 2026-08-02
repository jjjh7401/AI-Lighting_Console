"""Frozen-aware paperwork output directory + deterministic HTML write (T-J).

Mirrors ``test_deploy_runtime_data_path.py``'s frozen/dev split for
``resolve_runtime_audit_dir`` — same idiom, different runtime-output kind.
"""

from __future__ import annotations

from pathlib import Path

from server.paperwork.output import (
    DEFAULT_PAPERWORK_DIR,
    resolve_paperwork_dir,
    write_paperwork_html,
)


class TestResolvePaperworkDir:
    def test_dev_checkout_uses_the_repo_relative_default(self):
        assert resolve_paperwork_dir(frozen=False) == DEFAULT_PAPERWORK_DIR

    def test_default_sits_beside_the_paperwork_package(self):
        assert DEFAULT_PAPERWORK_DIR.name == "paperwork_output"
        assert DEFAULT_PAPERWORK_DIR.parent.name == "server"

    def test_frozen_routes_under_the_user_data_dir_not_the_repo(self):
        got = resolve_paperwork_dir(frozen=True)
        assert got != DEFAULT_PAPERWORK_DIR
        assert got.name == "paperwork"

    def test_frozen_none_falls_back_to_sys_frozen(self, monkeypatch):
        import sys

        monkeypatch.delattr(sys, "frozen", raising=False)
        assert resolve_paperwork_dir() == DEFAULT_PAPERWORK_DIR


class TestWritePaperworkHtml:
    def test_writes_the_exact_content_to_the_named_file(self, tmp_path):
        path = write_paperwork_html("patch_sheet.html", "<html>x</html>", directory=tmp_path)
        assert path == tmp_path / "patch_sheet.html"
        assert path.read_text(encoding="utf-8") == "<html>x</html>"

    def test_a_second_write_overwrites_rather_than_accumulating(self, tmp_path):
        write_paperwork_html("cue_sheet.html", "first", directory=tmp_path)
        write_paperwork_html("cue_sheet.html", "second", directory=tmp_path)
        files = list(tmp_path.glob("cue_sheet*"))
        assert len(files) == 1
        assert files[0].read_text(encoding="utf-8") == "second"

    def test_creates_the_directory_when_missing(self, tmp_path):
        nested: Path = tmp_path / "nested" / "deeper"
        assert not nested.exists()
        write_paperwork_html("preset_list.html", "x", directory=nested)
        assert nested.is_dir()

    def test_defaults_to_resolve_paperwork_dir_when_no_directory_given(self, tmp_path, monkeypatch):
        monkeypatch.setattr("server.paperwork.output.resolve_paperwork_dir", lambda: tmp_path)
        path = write_paperwork_html("patch_sheet.html", "x")
        assert path == tmp_path / "patch_sheet.html"
