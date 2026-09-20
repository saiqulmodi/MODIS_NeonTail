"""Tests for load_level()/reset_level() -- the JSON-to-game-objects loader
introduced in Phase 6 and extended with more tile types in every phase
since. pytest finds any file named test_*.py, runs every function named
test_*, and reports which asserts passed or failed.
"""

import json

import pygame

import main


def write_level(tmp_path, grid, tile_size=64):
    path = tmp_path / "level_test.json"
    path.write_text(json.dumps({"tile_size": tile_size, "grid": grid}))
    return path


def test_load_level_parses_walls_and_spawns(tmp_path):
    grid = [
        "####",
        "#S.#",
        "#.V#",
        "####",
    ]
    level = main.load_level(write_level(tmp_path, grid))

    assert level["squirrel_start"] == (64, 64)
    assert level["viper_start"] == (128, 128)
    assert len(level["walls"]) == 12  # every '#' in the grid above


def test_load_level_parses_every_pickup_type(tmp_path):
    grid = [
        "########",
        "#S.....#",
        "#WJHBGX#",
        "#V.....#",
        "########",
    ]
    level = main.load_level(write_level(tmp_path, grid))

    assert level["landmines"] == [pygame.Rect(64, 128, 64, 64)]      # W
    assert level["jump_pads"] == [pygame.Rect(128, 128, 64, 64)]     # J
    assert level["shields"] == [pygame.Rect(192, 128, 64, 64)]       # H
    assert level["time_bubbles"] == [pygame.Rect(256, 128, 64, 64)]  # B
    assert level["gravity_zones"] == [pygame.Rect(320, 128, 64, 64)]  # G
    assert level["tripwires"] == [pygame.Rect(384, 128, 64, 64)]     # X


def test_reset_level_derives_patrol_y_from_viper_start():
    # Uses the real level_001.json rather than a synthetic one, since
    # reset_level() takes a level number, not a path.
    level = main.reset_level(1)
    assert level["viper_patrol_y"] == level["viper_start"][1]


def test_every_shipped_level_has_exactly_one_squirrel_and_viper_spawn():
    for level_number in range(1, main.LEVEL_COUNT + 1):
        level = main.load_level(main.level_path(level_number))
        assert level["squirrel_start"] != (0, 0), f"level {level_number} has no 'S' tile"
        assert level["viper_start"] != (0, 0), f"level {level_number} has no 'V' tile"
        assert level["squirrel_start"] != level["viper_start"], f"level {level_number} spawns overlap"
