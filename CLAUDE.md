# MODIS_NeonTail — "Neon Tail & The Thermal Tracker"
*Project-specific reference — save as `CLAUDE.md` in this project's own folder (`C:\Users\saiqu\Projects\MODIS_NeonTail\CLAUDE.md`) so any Claude Code session opened here reads it automatically. As of 2026-09-19.*

## What this project is

A polished 2D game, built as the user's **first real coding product**, teaching them Python/pygame-ce game development from scratch through the terminal. Chor Police (tag) game, non-violent, built for both young kids (the user's sons Sahid and Sahil) and hardcore game players — easy to learn, hard to master.

**Chor** = Agent S.Q.U.I.R.E.L. — a nimble squirrel stealing glowing neon acorns.
**Police** = V.I.P.E.R. — a hovering snake-drone security robot with heat vision.
A caught player gets beamed into a comical "stasis bubble" timeout — never anything violent.

Modes: Player vs AI (default), local 2-player (shared keyboard), timed rounds with role swap.

## How this project runs — originally STRICT teaching mode, changed by explicit user request during Phase 3

The user's ORIGINAL rules for this project (their own words, condensed) — still apply to explanation style and pacing, but see the "changed" note below for execution:
- **Before each phase**: confirm project name, exact file(s) to edit, and the exact next step. Then **wait for their "go"**.
- **ONE step per message.** Never bundle multiple steps.
- Explain new concepts in 2-3 simple sentences, no jargon dumps.
- If something errors: **ask for the full error text and fix only that** — don't guess ahead.
- Free/self-generated assets only (simple shapes first, real art later). Never copyrighted characters or music.
- 100% non-violent, age-appropriate at every level.

**CHANGED, 2026-09-19, explicit user request** ("CAN ETIRE THINGS" → clarified as "DO IT FOR ME WITHOUT ASKEING TO PASTE" / "DO FOR ME"): Claude now writes files and runs terminal commands (git add/commit/log, syntax checks) directly, using its own tools, instead of asking the user to paste content into Notepad or copy-paste command results back. This followed real, repeated friction: Notepad was silently corrupting pasted code (see Phase 2 in the status log below), and the user was often pasting command TEXT back instead of command RESULTS, needing several rounds of clarification each time.

**What's still the user's job**: actually running `python main.py` and describing what they see/how it plays — Claude has no way to view their screen or press keys in the game window, so all gameplay/visual verification still comes from the user's own testing and description. Everything else (writing code, git operations, syntax checks) is now Claude's job, reported back rather than delegated.

**Tooling note carried over from earlier friction**: on this machine, Python processes spawned via the Bash tool have an unreliable view of the filesystem (a file just written can appear via `ls` but fail to open when a Bash-spawned `python` tries to read it). Use the PowerShell tool for verification/syntax-checks and for git commands in this project, not Bash.

## Project facts

- **Folder**: `C:\Users\saiqu\Projects\MODIS_NeonTail`
- **Engine**: Python 3.12 (via `py -3.12`) + pygame-ce 2.5.8, pinned exactly in `requirements.txt`
- **Venv**: `venv/` (gitignored)
- **Git**: initialized, `master` branch. Commits: `01f3913` (Phase 1), `c474607` (Phase 2), `fdf8ad9` (Phase 3), `6856a0e` (CLAUDE.md added), `3935fc9` (Phase 4 Step 1), `53b0460` (Phase 4 Step 2), `b93a797` (gitignore `__pycache__/`), `619c3b1` (CLAUDE.md status update), `bc69e7e` (Phase 5 Step 1), `a3418ac` (Phase 5 Step 2)

## Build phases (12 total, one step at a time, do not skip ahead)

1. **Setup** — venv, requirements.txt, git init, window opens with a colored background — **DONE, committed (`01f3913`)**
2. Squirrel moves with keyboard, animated placeholder sprite — **DONE, committed (`c474607`)**
3. V.I.P.E.R. drone with basic chase AI — **DONE, committed (`fdf8ad9`)**
4. Tag mechanic, stasis bubble timeout, score, timer — **DONE, committed (`3935fc9`, `53b0460`)**
5. Dirt Kick particle effects, drone blinding — **DONE, committed (`bc69e7e`, `a3418ac`)**
6. Tile-map level loader from JSON, levels 1-10
7. Menus, level select, pause, save system
8. Sound, music, taunt bubbles, whoopee-cushion landmines
9. Levels 11-50: jump-pads, Tail Flagging, Tracker Tags, shields
10. Levels 51-100: gravity flips, time bubbles, tripwires, teleport dodge, predictive AI
11. Local 2-player mode and gamepad
12. Polish, playtest balance, pytest tests, PyInstaller .exe, README, GitHub release

## Planned folder structure (not all built yet)

```
neontail/
  main.py, settings.py
  assets/ (images, sounds, fonts)
  levels/ (level_001.json ...)
  src/ (game.py, scenes/, entities/, ai/, systems/, ui/)
  tests/
  requirements.txt, README.md
```

## Techniques to be introduced across phases (explain briefly, in-context, when first used)

OOP entity classes (Squirrel, ViperDrone, Acorn, Decoy, TrackerTag, Landmine, Level, Game); fixed-timestep 60 FPS game loop; scene state machine (Menu, LevelSelect, Playing, Paused, LevelComplete, GameOver); rebindable input + gamepad; rect/circle/mask collision + tile maps; particle system; AI (vision cones, heat detection, patrol/chase/search, A* predictive tracking, difficulty curve); JSON-driven levels; pygame.mixer sound/music; screen shake, tweening, sprite sheets; JSON save system; kid-friendly assist mode; pytest for AI/level loading; git commit after each verified phase; PyInstaller .exe packaging. (3D upgrade via Ursina/Godot is explicitly a "later, not now" idea.)

## Status log

- 2026-09-19: **Phase 1 complete and committed.** Folder created, `py -3.12 -m venv venv`, pygame-ce 2.5.8 installed and pinned in `requirements.txt`, `git init` + `.gitignore` (excludes `venv/`), `main.py` written (minimal pygame window, dark space-blue background `(20, 20, 40)`, clean quit on Escape/X, 60 FPS `clock.tick`). Verified live by the user running `python main.py` themselves — window opened with the correct color, closed cleanly with no traceback. First commit `01f3913` — "Phase 1: project setup, window opens with colored background", 3 files (`.gitignore`, `main.py`, `requirements.txt`).
  - Two real friction points hit and resolved during this phase, not hypothetical: (1) user typed `Activate.ps` instead of `Activate.ps1` — simple typo, caught from the exact PowerShell error text as instructed. (2) User pressed Ctrl+C in the terminal to try to close the running game instead of closing the actual game window (Escape/X) — produced a `KeyboardInterrupt` traceback that looked alarming but was not a code bug; the window itself had opened correctly with the right color the whole time. (3) A `git commit -m "..."` message got split across two separate pastes, landing the closing `"` on a different line than the opening one, producing a stuck PowerShell `>>` continuation prompt — resolved with Ctrl+C then a clean single-paste retry. (4) `git add` was typed once directly into the Claude Code chat (not the user's own terminal) and mistaken for having been run — caught when the following `git commit` reported "nothing added to commit"; re-run for real in PowerShell fixed it.
- 2026-09-19: **Phase 2 complete and committed.** `main.py` updated in two steps: Step 1 added keyboard movement (arrow keys/WASD, delta-time-based speed, clamped to window bounds) with a static orange placeholder rectangle for the squirrel; Step 2 added a simple `math.sin`-based hop animation while moving, settling flat when idle. Verified live twice by the user (moves correctly after Step 1; moves AND hops after Step 2). Second commit `c474607` — "Phase 2: squirrel moves with keyboard, simple hop animation".
  - **Real, significant friction point this phase — worth expecting again**: pasting multi-line code into Notepad silently corrupted it in dozens of places (lines truncated mid-word, e.g. `WINDOW_WIDTH = 1` instead of `1024`, `SQUIRREL_SPEED =` with the value entirely missing, `for even` instead of `for event in pygame.event.get():`). Not a user mistake — confirmed by reading the actual saved file content via `Get-Content main.py`, which matched the corrupted text exactly. Root cause not diagnosed (possibly a Notepad/clipboard sync issue on this machine with large pastes). **Fix that worked**: abandoned the Notepad-paste approach for this file and had Claude write the file directly instead (the user explicitly asked for this: "CAN WE DO WITH MY INTERVINE" / "WITHOUT MY INTERVINE") — the user still runs and verifies every result themselves, only the mechanical act of getting the text into the file changed. **If Notepad-paste corruption happens again on a future phase, don't retry Notepad repeatedly — switch straight to Claude writing the file directly and having the user verify via `Get-Content`/running it,** rather than burning multiple rounds on a re-paste that's likely to corrupt the same way.
  - Also hit again this phase: the user pasting a command's TEXT back as if it were the result of running it (no actual output shown), several times in a row — resolved each time by asking for the literal terminal output after the command runs, not the command itself. Worth staying patient and explicit about this distinction throughout the project, it's a recurring pattern for this user, not a one-off.
- 2026-09-19: **Phase 3 complete and committed.** `main.py` updated in two steps: Step 1 added V.I.P.E.R. as a second entity with a fixed left-right patrol (bounces between two x-bounds at a fixed height, simplest possible "AI" — no decisions, just a repeating pattern); Step 2 added real chase behavior — every frame, straight-line distance to the squirrel (`math.hypot`) is checked against `VIPER_DETECTION_RANGE` (250px); within range it moves toward the squirrel using a normalized direction vector at `VIPER_CHASE_SPEED` (220, deliberately slower than the squirrel's own 300 so a reacting player can always outrun it); outside range it resumes patrolling at a fixed height (a stated simplification — it doesn't remember/resume its exact previous patrol position, snaps back to `VIPER_PATROL_Y` instead). Verified live by the user both after Step 1 (patrol moving on its own) and Step 2 (chases when close, correctly disengages and the user could escape). Third commit `fdf8ad9` — "Phase 3: V.I.P.E.R. drone with patrol and chase AI".
  - **Operating mode changed here, explicit user request** (see "How this project runs" above for the full note) — from this point on, Claude runs git commands and writes files directly using its own tools rather than asking the user to paste content/results. This commit itself was the first one run via Claude's own PowerShell tool rather than the user's terminal. The user still does all actual gameplay testing and reports what they see, since Claude can't view the game window or press keys in it.
- 2026-09-19: **Phase 4 complete and committed.** `main.py` updated in two steps: Step 1 added the tag mechanic — when V.I.P.E.R.'s rect collides with the squirrel's rect while `squirrel_state == "free"`, the squirrel enters a `"stasis"` state (frozen, no input accepted, drawn as a pale icy-blue circle instead of the usual rectangle) for `STASIS_DURATION` (3 seconds), then returns to `"free"` and re-centers; V.I.P.E.R. keeps patrolling/chasing normally throughout, it just has nothing to chase while the squirrel is in stasis. Step 2 added an on-screen score ("Caught: N", incremented on every tag) and a running game timer ("Time: MM:SS", counting up every frame) using `pygame.font.SysFont` + `render()`/`blit()`. Verified live by the user: caught → bubble → released confirmed Step 1; both the counter and timer updating correctly confirmed Step 2. Two commits — `3935fc9` ("Phase 4 Step 1: tag mechanic with stasis bubble timeout") and `53b0460` ("Phase 4 Step 2: on-screen score and running timer") — plus `b93a797` adding `__pycache__/` to `.gitignore`.
  - **Process note**: Claude initially wrote the Step 2 (score/timer) code directly on top of the not-yet-committed Step 1 code in the same file, before committing Step 1 as the user had just asked. Caught before committing — fixed by reconstructing a Step-1-only version from the last commit's `main.py` (via `git show HEAD:main.py`), committing that alone first, then re-applying the Step 2 changes on top as a separate, later commit. Worth deliberately committing each step right after it's verified, rather than writing ahead into the next step, to avoid needing this kind of untangling again.
- 2026-09-19: **Phase 5 complete and committed.** `main.py` updated in two steps: Step 1 added a particle system — pressing Space spawns `PARTICLE_COUNT` (10) small dirt-brown dots from the squirrel's position, fired in a `PARTICLE_SPREAD_DEGREES`-wide (40°) cone around whichever direction the squirrel last moved (tracked as `facing_x`/`facing_y`, updated on every WASD/arrow press), each with a random speed and a fixed `PARTICLE_LIFETIME` (0.4s); every frame each particle's position updates and its lifetime ticks down, and a list comprehension drops any particle whose lifetime has expired. Step 2 gave V.I.P.E.R. its own `viper_state` ("active"/"blinded") alongside the squirrel's existing state: if any particle's position lands inside V.I.P.E.R.'s rect (`viper_rect.collidepoint(...)`) while it's active, it goes blinded for `VIPER_BLIND_DURATION` (3s) — drawn dim gray (`VIPER_BLINDED_COLOR`) — during which it ignores the squirrel entirely and just patrols, then reverts to normal chase/patrol behavior. This required separating the squirrel's stasis-timer countdown from V.I.P.E.R.'s movement branch (previously combined in one `if squirrel_state == "free": ... else: ...` block) so the chase condition could check both `squirrel_state == "free"` and `viper_state == "active"` together. Verified live by the user: Step 1 confirmed dirt bursts fire in the facing direction and fade cleanly; Step 2 confirmed V.I.P.E.R. turns gray and stops chasing when hit, then resumes chasing normally once the blind wears off. Two commits — `bc69e7e` ("Phase 5 Step 1: dirt kick particle system") and `a3418ac` ("Phase 5 Step 2: dirt particles blind V.I.P.E.R. on hit").
