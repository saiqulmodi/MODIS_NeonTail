"""Balance and audio checks for Stratos_squirrel_vs_viper (the current main.py)."""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

import main as g


@pytest.fixture(scope="module", autouse=True)
def mixer():
    pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.init()
    pygame.mixer.init()
    yield
    pygame.quit()


STAT_KEYS = ("max_hp", "max_defense", "attack_power", "shot_cd", "special_cd", "hp", "defense")


@pytest.mark.parametrize("level", [1, 5, 10, 33, 60, 100])
def test_squirrel_and_viper_share_level_stats(level):
    squirrel = g.SquirrelPlayer(0, 0, level=level)
    for player_controlled in (False, True):
        viper = g.ViperEnemy(level=level, is_player_controlled=player_controlled)
        assert all(getattr(squirrel, k) == getattr(viper, k) for k in STAT_KEYS)


def test_pvp_viper_moves_like_the_squirrel():
    for level in (1, 20, 80):
        assert g.ViperEnemy(level=level, is_player_controlled=True).base_speed == g.SquirrelPlayer(0, 0, level=level).speed


@pytest.mark.parametrize("squirrels", [1, 2])
def test_squirrel_power_matches_viper_pack(squirrels):
    for level in range(1, 121):
        pack = g.pack_size(level, squirrels)
        assert 1 <= pack * squirrels <= g.MAX_VIPERS_ON_SCREEN
        squirrel = g.SquirrelPlayer(0, 0, level=level)
        squirrel.apply_level_up(level, power_mult=pack)
        viper = g.ViperEnemy(level=level)
        for k in ("max_hp", "max_defense", "attack_power"):
            assert getattr(squirrel, k) == getattr(viper, k) * pack


def test_pack_grows_every_five_levels():
    assert [g.pack_size(level) for level in (1, 5, 6, 10, 11, 16)] == [1, 1, 2, 2, 3, 4]
    assert g.pack_size(100) == 10 and g.pack_size(100, squirrels=2) == 5


def test_shard_power_up_is_identical_and_wears_off():
    squirrel, viper = g.SquirrelPlayer(0, 0, level=12), g.ViperEnemy(level=12)
    base = squirrel.power()
    squirrel.collect_shard()
    viper.collect_shard()
    assert squirrel.power() == viper.power() == int(base * g.SHARD_BOOST)
    for _ in range(g.SHARD_BOOST_FRAMES):
        squirrel.tick_timers()
        viper.tick_timers()
    assert squirrel.power() == viper.power() == base


def test_every_attack_has_its_own_short_sound():
    for mode in (1, 2, 3):
        raws = []
        for tool in g.ATTACK_TUNES:
            snd = g.get_attack_sfx(tool, mode, 1)
            assert snd is not None
            assert snd.get_length() <= 0.36
            raws.append(snd.get_raw()[:4000])
        assert len(set(raws)) == len(raws)


def test_sound_length_is_correct_for_the_mixer_format():
    snd = g.render_sound(0.30, lambda t: g.voice("bell", 440, t))
    assert abs(snd.get_length() - 0.30) < 0.01
