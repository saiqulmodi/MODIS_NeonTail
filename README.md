# Stratos_squirrel_vs_viper

A neon arcade duel built with Python and [pygame-ce](https://pyga.me/), by Stratos Games.
Blast laser fans and Nova rings as the Squirrel, or lead the Viper pack. Every level brings more
vipers, and the squirrel's power grows to match, so both sides always have the same total strength.

**Play it free in your browser:** https://saiqulmodi.github.io/Stratos_squirrel_vs_viper/

## Game modes

Press **T** to switch mode (on the start screen or in game).

| Mode | Who plays |
|---|---|
| Solo vs AI | Squirrel P1 vs an AI viper pack |
| Dual Squirrel vs AI | Squirrel P1 + Squirrel P2 (co-op), each with their own viper pack |
| Squirrel vs Viper | Squirrel P1 vs Player 2 steering the lead viper (the rest of the pack is AI) |

## Controls

The game opens on a screen listing every key and rule. Press **H** (or START on a controller) to see it again.

| Player | Move | Shoot (hold to keep firing) | Special |
|---|---|---|---|
| Squirrel P1 | W A S D | Space / left click (aim with mouse) | E / right click: Nova ring |
| Squirrel P2 (Dual) | Arrow keys | Enter / Right Ctrl | Right Shift: Nova ring |
| Viper (Squirrel vs Viper) | Arrow keys | Enter / Right Ctrl: venom spit | Right Shift: venom burst |

| Key | Action |
|---|---|
| T / R / M / H | Change mode / restart / mute / help screen |
| 1 - 9, 0 | Jump to level 10 - 90, 100 |
| ] or Page Up / [ or Page Down | Next / previous level ending in 0 |
| Click LV 1 ... LV 100 | Level-jump buttons at the bottom of the screen |

**Game controllers:** pad 1 = Squirrel P1, pad 2 = Squirrel P2 (Dual) or the Viper (Squirrel vs Viper).
Left stick / D-pad move, A / X shoot (right stick aims, hold to keep firing), B / Y / LB / RB special,
START shows the help screen. In a browser, press any button on the controller once so the page detects it.

## How the balance works

- Squirrel and viper share one stats formula per level: HP `300 + 35*(L-1)`, defense `100 + 20*(L-1)`,
  attack `35 + 4*(L-1)`, plus the same fire rate and special cooldown.
- Each squirrel faces a pack of `1 + (L-1)//5` vipers (max 10 on screen; max 5 per squirrel in Dual).
- A squirrel facing N vipers has N x HP, N x defense, fires N laser beams per shot and an N x denser Nova ring,
  so the squirrel side's total strength equals the pack's.
- Kill 5 vipers to reach the next level. Beating a whole pack refills everyone before the next pack.
- Body contact hurts both sides. Green gems appear every 7 s: +25% attack for 10 s plus HP/DEF, for whoever grabs them.
- Squirrel vs Viper is played in rounds: beat the whole pack (squirrel) or the squirrel (viper) to win a round.
- Sound plays only on attacks. Every attack has its own tune, different per mode and every 3 levels.

## Running from source

```bash
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
python main.py
```

Requires Python 3.12 and pygame-ce 2.5.8 (pinned in `requirements.txt`).

## Building the web version (GitHub Pages)

```bash
pip install pygbag
# build from a clean folder named stratos_squirrel_vs_viper containing only main.py
pygbag --title "Stratos_squirrel_vs_viper" --build path\to\stratos_squirrel_vs_viper
```

Copy the contents of that folder's `build/web/` into `docs/` and push. GitHub Pages serves `docs/` on the
`main` branch. `docs/cover.png` is the screenshot used on stratos.games.

## Building the .exe

```bash
pip install pyinstaller
pyinstaller Stratos_squirrel_vs_viper.spec
```

The executable appears in `dist/`.

## Tests

```bash
pip install pytest
pytest tests/test_balance.py -v
```

`tests/test_balance.py` checks the equal-power rules, viper packs, shard power-ups and attack sounds.
The older files in `tests/` (`test_collision.py`, `test_level_loading.py`, `test_save_system.py`) were written
for the earlier chase-game version of this project and do not match the current `main.py`.

## Website

`website/stratos_games_section.html` is the ready-made section for https://stratos.games
(paste it into an Elementor HTML widget).

## License

No license has been chosen yet for this project.
