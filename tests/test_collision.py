"""Tests for move_with_collision() -- the per-axis wall collision helper
from Phase 6 that both the squirrel and V.I.P.E.R. move through.
"""

import pygame

import main


def test_move_with_collision_allows_open_movement():
    new_x, new_y = main.move_with_collision(100, 100, 50, 0, 40, walls=[])
    assert (new_x, new_y) == (150, 100)


def test_move_with_collision_blocked_by_wall():
    wall = pygame.Rect(140, 90, 64, 64)
    new_x, new_y = main.move_with_collision(100, 100, 50, 0, 40, walls=[wall])
    assert new_x == 100  # moving right would land inside the wall


def test_move_with_collision_slides_along_wall():
    # A wall blocks horizontal movement, but the same call's vertical
    # movement should still go through -- this per-axis resolution is
    # exactly what lets you slide along a wall instead of getting stuck.
    wall = pygame.Rect(140, 90, 64, 64)
    new_x, new_y = main.move_with_collision(100, 100, 50, 50, 40, walls=[wall])
    assert new_x == 100  # horizontal blocked
    assert new_y == 150  # vertical still allowed
