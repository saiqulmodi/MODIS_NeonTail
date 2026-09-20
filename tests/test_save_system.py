"""Tests for load_save()/write_save() -- the Phase 7 save system.
monkeypatch temporarily replaces main.SAVE_PATH with a path inside
pytest's own tmp_path, so tests never touch the player's real save.json.
"""

import main


def test_load_save_defaults_when_file_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "SAVE_PATH", tmp_path / "save.json")
    assert main.load_save() == {"last_level": 1, "lifetime_catches": 0}


def test_write_then_load_save_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "SAVE_PATH", tmp_path / "save.json")
    main.write_save(7, 42)
    assert main.load_save() == {"last_level": 7, "lifetime_catches": 42}


def test_load_save_falls_back_on_corrupt_file(tmp_path, monkeypatch):
    save_path = tmp_path / "save.json"
    save_path.write_text("not valid json{{{")
    monkeypatch.setattr(main, "SAVE_PATH", save_path)
    assert main.load_save() == {"last_level": 1, "lifetime_catches": 0}
