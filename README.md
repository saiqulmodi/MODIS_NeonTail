# MODIS_NeonTail — Neon Tail & The Thermal Tracker

A non-violent, chase-and-evade "chor police" (cops and robbers) game built with Python and [pygame-ce](https://pyga.me/), built from scratch as a first coding project and playable by kids and experienced players alike — easy to learn, hard to master.

**Chor (evader):** Agent S.Q.U.I.R.E.L. — a nimble squirrel darting between neon obstacles.
**Police (chaser):** V.I.P.E.R. — a hovering snake-drone security robot with heat vision.

Getting caught doesn't hurt anyone — you're beamed into a comical "stasis bubble" for a few seconds and released. 100 hand-and-code-generated levels, three game modes, sound and music, and a full local 2-player mode with gamepad support.

## Features

- **Player vs AI** — outrun, outsmart, and distract V.I.P.E.R.'s chase AI, which predicts your movement and locks onto you once it gets close
- **Local 2-player** — a full match with a round timer; both players swap between squirrel and V.I.P.E.R. halfway through, and whoever catches more as V.I.P.E.R. wins
- **Gamepad support** — a connected controller works alongside the keyboard for whichever character you're controlling
- **100 levels** with wall mazes, jump-pads, shields, whoopee-cushion landmines, time bubbles, gravity-flip zones, and tripwires
- **Tools:** kick dirt to blind V.I.P.E.R., drop a decoy to distract it, or teleport-dodge out of danger
- Sound effects and music, all synthesized from scratch — no external audio files
- Menus, pause, level select, and a save file that remembers your last level and lifetime catch count

## Controls

| Key | Action |
|---|---|
| Arrow keys / WASD | Move (vs-AI mode: either works; 2-player: one set per player) |
| Space | Kick dirt (blinds V.I.P.E.R. briefly if it hits) |
| F | Drop a decoy |
| T | Teleport dodge (long cooldown) |
| N / P | Switch to the next / previous level |
| Enter | Confirm / start / play |
| Escape | Pause, go back, or quit (from the main menu) |
| L | Level select (from the main menu) |
| 2 | Start a 2-player match (from the main menu) |
| Q | Quit (from the pause screen) |

A connected gamepad's left stick or D-pad works as an alternative to arrow keys.

## Running from source

```bash
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
python main.py
```

Requires Python 3.12 and pygame-ce 2.5.8 (pinned in `requirements.txt`).

## Running the standalone build

No Python installation needed — grab `MODIS_NeonTail.exe` from a release and double-click it.

## Building the .exe yourself

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name MODIS_NeonTail --add-data "levels;levels" --add-data "assets;assets" main.py
```

The built executable appears in `dist/`. (`MODIS_NeonTail.spec` in this repo already captures these settings — running `pyinstaller MODIS_NeonTail.spec` works too.)

## Running the tests

```bash
pip install pytest
pytest -v
```

Covers level loading (including every shipped level file), wall collision physics, and the save system.

## Project structure

```
main.py              -- the entire game
levels/               -- level_001.json ... level_100.json
assets/
  sounds/             -- synthesized sound effects (.wav)
  music/              -- synthesized background music (.wav)
tests/                -- pytest suite
requirements.txt
MODIS_NeonTail.spec   -- PyInstaller build recipe
```

## License

No license has been chosen yet for this project.
