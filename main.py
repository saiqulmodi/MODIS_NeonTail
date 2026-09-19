"""
main.py -- MODIS_NeonTail

Phase 10, Step 1: predictive AI. V.I.P.E.R. now aims PREDICTION_TIME
seconds ahead of the squirrel's current velocity instead of its exact
position -- a simple, believable stand-in for real pathfinding, which
wouldn't fit this game's continuous pixel movement (no grid to run A* on).
"""

import json
import math
import random
from pathlib import Path

import pygame

LEVEL_DIR = Path(__file__).parent / "levels"
LEVEL_COUNT = 50  # level_001.json through level_050.json
SAVE_PATH = Path(__file__).parent / "save.json"
SOUND_DIR = Path(__file__).parent / "assets" / "sounds"
MUSIC_PATH = Path(__file__).parent / "assets" / "music" / "theme.wav"
TILE_WALL_COLOR = (60, 60, 90)  # dark slate -- reads as "structure", not floor


def load_save():
    """Read save.json if it exists; fall back to defaults on a first run
    or if the file is missing/corrupt."""
    if SAVE_PATH.exists():
        try:
            with open(SAVE_PATH, "r", encoding="utf-8") as save_file:
                data = json.load(save_file)
            return {
                "last_level": data.get("last_level", 1),
                "lifetime_catches": data.get("lifetime_catches", 0),
            }
        except (json.JSONDecodeError, OSError):
            pass
    return {"last_level": 1, "lifetime_catches": 0}


def write_save(last_level, lifetime_catches):
    data = {"last_level": last_level, "lifetime_catches": lifetime_catches}
    with open(SAVE_PATH, "w", encoding="utf-8") as save_file:
        json.dump(data, save_file, indent=2)


def level_path(level_number):
    return LEVEL_DIR / f"level_{level_number:03d}.json"


def reset_level(level_number):
    """Load a level's walls, landmines, jump-pads, shields, and start
    positions. Shared by the initial setup, N-key switching, and the
    level-select screen, so the loading logic only lives in one place."""
    walls, landmines, jump_pads, shields, squirrel_start, viper_start = load_level(level_path(level_number))
    squirrel_x, squirrel_y = squirrel_start
    viper_x, viper_y = viper_start
    viper_patrol_y = viper_y
    return walls, landmines, jump_pads, shields, squirrel_x, squirrel_y, viper_x, viper_y, viper_patrol_y


def load_level(path):
    """Read a level JSON file and turn its character grid into wall rects,
    landmine rects, jump-pad rects, shield rects, and start positions.
    '#' = wall, 'S' = squirrel start, 'V' = V.I.P.E.R. start,
    'W' = whoopee-cushion landmine, 'J' = jump-pad, 'H' = shield pickup."""
    with open(path, "r", encoding="utf-8") as level_file:
        data = json.load(level_file)

    tile_size = data["tile_size"]
    grid = data["grid"]

    walls = []
    landmines = []
    jump_pads = []
    shields = []
    squirrel_start = (0, 0)
    viper_start = (0, 0)

    for row_index, row in enumerate(grid):
        for col_index, tile_char in enumerate(row):
            x = col_index * tile_size
            y = row_index * tile_size
            if tile_char == "#":
                walls.append(pygame.Rect(x, y, tile_size, tile_size))
            elif tile_char == "S":
                squirrel_start = (x, y)
            elif tile_char == "V":
                viper_start = (x, y)
            elif tile_char == "W":
                landmines.append(pygame.Rect(x, y, tile_size, tile_size))
            elif tile_char == "J":
                jump_pads.append(pygame.Rect(x, y, tile_size, tile_size))
            elif tile_char == "H":
                shields.append(pygame.Rect(x, y, tile_size, tile_size))

    return walls, landmines, jump_pads, shields, squirrel_start, viper_start


def move_with_collision(x, y, dx, dy, size, walls):
    """Move by (dx, dy) one axis at a time, undoing whichever axis would
    land inside a wall -- this is what lets you slide along a wall instead
    of getting stuck the moment you bump into it diagonally."""
    new_x = x + dx
    if pygame.Rect(new_x, y, size, size).collidelist(walls) != -1:
        new_x = x
    new_y = y + dy
    if pygame.Rect(new_x, new_y, size, size).collidelist(walls) != -1:
        new_y = y
    return new_x, new_y


WINDOW_WIDTH = 1024
WINDOW_HEIGHT = 768
FPS = 60
BACKGROUND_COLOR = (20, 20, 40)  # dark space-blue
TEXT_COLOR = (255, 255, 255)

SQUIRREL_COLOR = (255, 140, 0)  # orange -- heat-signature color, matches the theme
SQUIRREL_SIZE = 40
SQUIRREL_SPEED = 300  # pixels per second

ANIMATION_SPEED = 10  # how fast the bounce cycles
BOUNCE_HEIGHT = 8      # how many pixels it hops up

VIPER_COLOR = (0, 200, 255)  # cool cyan -- heat-vision-camera color
VIPER_SIZE = 50
VIPER_PATROL_SPEED = 150   # pixels per second while patrolling
VIPER_CHASE_SPEED = 220    # faster while chasing, but still slower than the
                            # squirrel's own top speed -- you can outrun it
                            # if you react in time
VIPER_DETECTION_RANGE = 250  # pixels -- how close before it notices you
VIPER_PATROL_LEFT = 100
VIPER_PATROL_RIGHT = WINDOW_WIDTH - 100 - VIPER_SIZE

VIPER_BLIND_DURATION = 3.0  # seconds V.I.P.E.R. can't see after a dirt hit
VIPER_BLINDED_COLOR = (80, 80, 90)  # dim gray -- visually shows it can't see

STASIS_DURATION = 3.0  # seconds spent in the stasis bubble after being caught
STASIS_BUBBLE_COLOR = (200, 230, 255)  # pale icy-blue bubble

PARTICLE_COLOR = (139, 90, 43)  # dirt brown
PARTICLE_SIZE = 4
PARTICLE_COUNT = 10        # particles spawned per kick
PARTICLE_LIFETIME = 0.4    # seconds each particle lives
PARTICLE_SPEED_MIN = 150
PARTICLE_SPEED_MAX = 300
PARTICLE_SPREAD_DEGREES = 40  # cone width the burst fans out into

TAUNT_COLOR = (255, 230, 80)  # bright yellow -- reads as playful, not urgent
TAUNT_DURATION = 1.5  # seconds a taunt bubble is shown before it's gone
TAUNT_RISE_SPEED = 30  # pixels per second it drifts upward
TAUNT_PHRASES = ["Nyah nyah!", "Too slow!", "Can't catch me!", "Nice try!"]

WHOOPEE_COLOR = (230, 120, 180)  # comic pink -- distinct from every other game element
VIPER_STUN_DURATION = 2.0  # seconds V.I.P.E.R. is fully frozen after a landmine

JUMP_PAD_COLOR = (255, 215, 0)  # gold -- reads as "special", distinct from everything else
JUMP_DISTANCE = 150  # pixels the squirrel is launched, more than one tile wide
JUMP_COOLDOWN = 0.4  # seconds after a launch before the pad can fire again

DECOY_DURATION = 5.0  # seconds a decoy lasts before it vanishes unused

TAG_DURATION = 4.0  # seconds V.I.P.E.R. stays locked on after losing direct range

SHIELD_COLOR = (80, 220, 120)  # protective green -- reads as "power-up"
INVULNERABLE_DURATION = 1.5  # seconds of safety right after a shield absorbs a catch

PREDICTION_TIME = 0.3  # seconds V.I.P.E.R. aims ahead of the squirrel's current heading


def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("MODIS_NeonTail")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 36)  # None = pygame's default built-in font
    title_font = pygame.font.SysFont(None, 72)

    caught_sound = pygame.mixer.Sound(SOUND_DIR / "caught.wav")
    kick_sound = pygame.mixer.Sound(SOUND_DIR / "kick.wav")
    blind_sound = pygame.mixer.Sound(SOUND_DIR / "blind.wav")
    landmine_sound = pygame.mixer.Sound(SOUND_DIR / "landmine.wav")

    pygame.mixer.music.load(MUSIC_PATH)
    pygame.mixer.music.set_volume(0.4)  # quieter than the sound effects

    # game_state is "menu" (title screen) or "playing" (gameplay running).
    game_state = "menu"

    save_data = load_save()
    lifetime_catches = save_data["lifetime_catches"]

    level_number = save_data["last_level"]
    level_select_choice = level_number  # which level is highlighted on the select screen
    walls, landmines, jump_pads, shields, squirrel_x, squirrel_y, viper_x, viper_y, viper_patrol_y = reset_level(level_number)
    jump_cooldown_timer = 0.0
    has_shield = False
    invulnerable_timer = 0.0
    animation_timer = 0.0

    # squirrel_state is "free" (normal play) or "stasis" (caught, frozen
    # in the bubble for STASIS_DURATION seconds before being released).
    squirrel_state = "free"
    stasis_timer = 0.0

    viper_direction = 1  # 1 = moving right, -1 = moving left

    # viper_state is "active" (can see/chase normally) or "blinded"
    # (dirt hit it -- just patrols obliviously until blind_timer runs out).
    viper_state = "active"
    blind_timer = 0.0
    stun_timer = 0.0
    tag_timer = 0.0

    score = 0            # how many times you've been caught
    game_time = 0.0       # total seconds played, counts up

    facing_x, facing_y = 1, 0  # direction the squirrel last moved/faced
    particles = []              # each particle is a dict: x, y, vx, vy, lifetime
    taunts = []                  # each taunt is a dict: text, x, y, age
    decoy = None                 # None, or a dict: x, y, timer

    running = True
    while running:
        delta_time = clock.tick(FPS) / 1000

        # 1. Handle input/events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if game_state == "menu":
                    running = False
                elif game_state == "playing":
                    game_state = "paused"
                    pygame.mixer.music.pause()
                elif game_state == "paused":
                    game_state = "playing"
                    pygame.mixer.music.unpause()
                elif game_state == "level_select":
                    game_state = "menu"
            if game_state == "menu":
                if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    game_state = "playing"
                    pygame.mixer.music.play(loops=-1)
                if event.type == pygame.KEYDOWN and event.key == pygame.K_l:
                    level_select_choice = level_number
                    game_state = "level_select"
            elif game_state == "level_select":
                if event.type == pygame.KEYDOWN and event.key in (pygame.K_LEFT, pygame.K_a):
                    level_select_choice = (level_select_choice - 2) % LEVEL_COUNT + 1
                if event.type == pygame.KEYDOWN and event.key in (pygame.K_RIGHT, pygame.K_d):
                    level_select_choice = level_select_choice % LEVEL_COUNT + 1
                if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    level_number = level_select_choice
                    walls, landmines, jump_pads, shields, squirrel_x, squirrel_y, viper_x, viper_y, viper_patrol_y = reset_level(level_number)
                    viper_direction = 1
                    squirrel_state = "free"
                    stasis_timer = 0.0
                    viper_state = "active"
                    blind_timer = 0.0
                    stun_timer = 0.0
                    tag_timer = 0.0
                    jump_cooldown_timer = 0.0
                    has_shield = False
                    invulnerable_timer = 0.0
                    facing_x, facing_y = 1, 0
                    particles = []
                    taunts = []
                    decoy = None
                    game_state = "playing"
                    write_save(level_number, lifetime_catches)
                    pygame.mixer.music.play(loops=-1)
            elif game_state == "paused":
                if event.type == pygame.KEYDOWN and event.key == pygame.K_q:
                    running = False
            elif game_state == "playing":
                if event.type == pygame.KEYDOWN and event.key == pygame.K_n:
                    level_number = level_number % LEVEL_COUNT + 1  # wraps 10 -> 1
                    walls, landmines, jump_pads, shields, squirrel_x, squirrel_y, viper_x, viper_y, viper_patrol_y = reset_level(level_number)
                    viper_direction = 1
                    squirrel_state = "free"
                    stasis_timer = 0.0
                    viper_state = "active"
                    blind_timer = 0.0
                    stun_timer = 0.0
                    tag_timer = 0.0
                    jump_cooldown_timer = 0.0
                    has_shield = False
                    invulnerable_timer = 0.0
                    facing_x, facing_y = 1, 0
                    particles = []
                    taunts = []
                    decoy = None
                    write_save(level_number, lifetime_catches)
                if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                    if squirrel_state == "free":
                        kick_sound.play()
                        base_angle = math.atan2(facing_y, facing_x)
                        spread = math.radians(PARTICLE_SPREAD_DEGREES)
                        kick_x = squirrel_x + SQUIRREL_SIZE / 2
                        kick_y = squirrel_y + SQUIRREL_SIZE / 2
                        for _ in range(PARTICLE_COUNT):
                            angle = base_angle + random.uniform(-spread / 2, spread / 2)
                            speed = random.uniform(PARTICLE_SPEED_MIN, PARTICLE_SPEED_MAX)
                            particles.append({
                                "x": kick_x,
                                "y": kick_y,
                                "vx": math.cos(angle) * speed,
                                "vy": math.sin(angle) * speed,
                                "lifetime": PARTICLE_LIFETIME,
                            })
                if event.type == pygame.KEYDOWN and event.key == pygame.K_f:
                    if squirrel_state == "free" and decoy is None:
                        decoy = {
                            "x": squirrel_x + SQUIRREL_SIZE / 2,
                            "y": squirrel_y + SQUIRREL_SIZE / 2,
                            "timer": DECOY_DURATION,
                        }

        # 2. Update game state -- gameplay only advances while playing, so
        # the menu screen doesn't move or count down behind the scenes.
        if game_state == "playing":
            game_time += delta_time
            keys = pygame.key.get_pressed()
            is_moving = False
            move_dx = 0
            move_dy = 0

            # No player input while caught -- the squirrel is frozen in the bubble.
            if squirrel_state == "free":
                if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                    move_dx -= SQUIRREL_SPEED * delta_time
                    is_moving = True
                    facing_x, facing_y = -1, 0
                if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                    move_dx += SQUIRREL_SPEED * delta_time
                    is_moving = True
                    facing_x, facing_y = 1, 0
                if keys[pygame.K_UP] or keys[pygame.K_w]:
                    move_dy -= SQUIRREL_SPEED * delta_time
                    is_moving = True
                    facing_x, facing_y = 0, -1
                if keys[pygame.K_DOWN] or keys[pygame.K_s]:
                    move_dy += SQUIRREL_SPEED * delta_time
                    is_moving = True
                    facing_x, facing_y = 0, 1

            # Recover actual pixels-per-second velocity from this frame's
            # already-delta_time-scaled movement -- V.I.P.E.R. uses this to
            # predict where the squirrel is heading, not just where it is.
            squirrel_velocity_x = move_dx / delta_time if delta_time > 0 else 0
            squirrel_velocity_y = move_dy / delta_time if delta_time > 0 else 0

            squirrel_x, squirrel_y = move_with_collision(
                squirrel_x, squirrel_y, move_dx, move_dy, SQUIRREL_SIZE, walls
            )
            squirrel_x = max(0, min(WINDOW_WIDTH - SQUIRREL_SIZE, squirrel_x))
            squirrel_y = max(0, min(WINDOW_HEIGHT - SQUIRREL_SIZE, squirrel_y))

            if is_moving:
                animation_timer += delta_time
            else:
                animation_timer = 0.0
            bounce = abs(math.sin(animation_timer * ANIMATION_SPEED)) * BOUNCE_HEIGHT
            squirrel_rect = pygame.Rect(squirrel_x, squirrel_y - bounce, SQUIRREL_SIZE, SQUIRREL_SIZE)

            # Jump-pads launch the squirrel in its current facing direction.
            # Reusable (unlike landmines), so a short cooldown -- not removal
            # from the list -- is what stops one firing every single frame
            # while the squirrel is still standing on it.
            jump_cooldown_timer -= delta_time
            if (
                squirrel_state == "free"
                and jump_cooldown_timer <= 0
                and squirrel_rect.collidelist(jump_pads) != -1
            ):
                launch_dx = facing_x * JUMP_DISTANCE
                launch_dy = facing_y * JUMP_DISTANCE
                squirrel_x, squirrel_y = move_with_collision(
                    squirrel_x, squirrel_y, launch_dx, launch_dy, SQUIRREL_SIZE, walls
                )
                squirrel_x = max(0, min(WINDOW_WIDTH - SQUIRREL_SIZE, squirrel_x))
                squirrel_y = max(0, min(WINDOW_HEIGHT - SQUIRREL_SIZE, squirrel_y))
                squirrel_rect = pygame.Rect(squirrel_x, squirrel_y - bounce, SQUIRREL_SIZE, SQUIRREL_SIZE)
                jump_cooldown_timer = JUMP_COOLDOWN

            # Picking up a shield grants one-catch protection -- a one-time
            # pickup, removed from the level once collected.
            if squirrel_state == "free" and not has_shield:
                hit_shield = squirrel_rect.collidelist(shields)
                if hit_shield != -1:
                    del shields[hit_shield]
                    has_shield = True

            # Brief invulnerability right after a shield absorbs a catch,
            # so the same overlap can't immediately catch you again.
            if invulnerable_timer > 0:
                invulnerable_timer -= delta_time

            # Squirrel stasis countdown -- independent of what V.I.P.E.R. is doing.
            if squirrel_state == "stasis":
                stasis_timer -= delta_time
                if stasis_timer <= 0:
                    squirrel_state = "free"
                    squirrel_x = WINDOW_WIDTH / 2
                    squirrel_y = WINDOW_HEIGHT / 2

            # V.I.P.E.R. blinded countdown -- independent of the squirrel.
            if viper_state == "blinded":
                blind_timer -= delta_time
                if blind_timer <= 0:
                    viper_state = "active"

            # V.I.P.E.R. stunned countdown -- a landmine freezes it completely,
            # so unlike blinded it doesn't even patrol until this runs out.
            if viper_state == "stunned":
                stun_timer -= delta_time
                if stun_timer <= 0:
                    viper_state = "active"

            # The decoy expires on its own if V.I.P.E.R. never reaches it.
            if decoy is not None:
                decoy["timer"] -= delta_time
                if decoy["timer"] <= 0:
                    decoy = None

            if viper_state == "stunned":
                pass  # frozen in place -- no movement at all
            elif squirrel_state == "free" and viper_state == "active":
                # Distance to the REAL squirrel drives tag_timer, regardless
                # of whether a decoy is what's actually being chased right
                # now -- this is what makes the lock-on "sticky": tag_timer
                # keeps getting refreshed while in range, and only starts
                # counting down once the squirrel steps back out of it.
                squirrel_dx = (squirrel_x + SQUIRREL_SIZE / 2) - (viper_x + VIPER_SIZE / 2)
                squirrel_dy = (squirrel_y + SQUIRREL_SIZE / 2) - (viper_y + VIPER_SIZE / 2)
                distance_to_squirrel = math.hypot(squirrel_dx, squirrel_dy)

                if distance_to_squirrel <= VIPER_DETECTION_RANGE:
                    tag_timer = TAG_DURATION
                else:
                    tag_timer -= delta_time

                if distance_to_squirrel <= VIPER_DETECTION_RANGE or tag_timer > 0:
                    # What V.I.P.E.R. is trying to reach: a decoy takes
                    # priority over the real squirrel if V.I.P.E.R. is close
                    # enough to it to notice -- otherwise it aims a little
                    # ahead of the squirrel's current heading, not straight
                    # at it, which is what makes the chase feel smarter.
                    target_x = squirrel_x + SQUIRREL_SIZE / 2 + squirrel_velocity_x * PREDICTION_TIME
                    target_y = squirrel_y + SQUIRREL_SIZE / 2 + squirrel_velocity_y * PREDICTION_TIME
                    if decoy is not None:
                        decoy_distance = math.hypot(decoy["x"] - (viper_x + VIPER_SIZE / 2), decoy["y"] - (viper_y + VIPER_SIZE / 2))
                        if decoy_distance <= VIPER_DETECTION_RANGE:
                            target_x, target_y = decoy["x"], decoy["y"]

                    dx = target_x - (viper_x + VIPER_SIZE / 2)
                    dy = target_y - (viper_y + VIPER_SIZE / 2)
                    target_distance = math.hypot(dx, dy)

                    if target_distance > 0:
                        chase_dx = (dx / target_distance) * VIPER_CHASE_SPEED * delta_time
                        chase_dy = (dy / target_distance) * VIPER_CHASE_SPEED * delta_time
                        viper_x, viper_y = move_with_collision(viper_x, viper_y, chase_dx, chase_dy, VIPER_SIZE, walls)
                else:
                    viper_y = viper_patrol_y
                    patrol_dx = VIPER_PATROL_SPEED * viper_direction * delta_time
                    viper_x, viper_y = move_with_collision(viper_x, viper_y, patrol_dx, 0, VIPER_SIZE, walls)
                    if viper_x <= VIPER_PATROL_LEFT:
                        viper_x = VIPER_PATROL_LEFT
                        viper_direction = 1
                    elif viper_x >= VIPER_PATROL_RIGHT:
                        viper_x = VIPER_PATROL_RIGHT
                        viper_direction = -1
            else:
                # Squirrel in stasis, or V.I.P.E.R. blinded -- either way there's
                # nothing to chase right now, so just patrol.
                viper_y = viper_patrol_y
                patrol_dx = VIPER_PATROL_SPEED * viper_direction * delta_time
                viper_x, viper_y = move_with_collision(viper_x, viper_y, patrol_dx, 0, VIPER_SIZE, walls)
                if viper_x <= VIPER_PATROL_LEFT:
                    viper_x = VIPER_PATROL_LEFT
                    viper_direction = 1
                elif viper_x >= VIPER_PATROL_RIGHT:
                    viper_x = VIPER_PATROL_RIGHT
                    viper_direction = -1

            viper_x = max(0, min(WINDOW_WIDTH - VIPER_SIZE, viper_x))
            viper_y = max(0, min(WINDOW_HEIGHT - VIPER_SIZE, viper_y))
            viper_rect = pygame.Rect(viper_x, viper_y, VIPER_SIZE, VIPER_SIZE)

            # V.I.P.E.R. reaching the decoy "investigates" it -- consumed,
            # freeing up another drop, with no other gameplay effect.
            if decoy is not None and viper_rect.collidepoint(decoy["x"], decoy["y"]):
                decoy = None

            # Stepping on a landmine stuns V.I.P.E.R. and uses the landmine
            # up -- only while active, so it can't be re-triggered or
            # stacked with blinded/stunned.
            if viper_state == "active":
                hit_landmine = viper_rect.collidelist(landmines)
                if hit_landmine != -1:
                    del landmines[hit_landmine]
                    viper_state = "stunned"
                    stun_timer = VIPER_STUN_DURATION
                    landmine_sound.play()

            # Advance every particle and drop the ones whose lifetime ran out.
            for particle in particles:
                particle["x"] += particle["vx"] * delta_time
                particle["y"] += particle["vy"] * delta_time
                particle["lifetime"] -= delta_time
            particles = [p for p in particles if p["lifetime"] > 0]

            # Drift every taunt bubble upward and age it out once its
            # display time is up.
            for taunt in taunts:
                taunt["y"] -= TAUNT_RISE_SPEED * delta_time
                taunt["age"] += delta_time
            taunts = [t for t in taunts if t["age"] < TAUNT_DURATION]

            # A dirt particle touching V.I.P.E.R. blinds it -- only while it
            # can currently see, so an already-blinded hit doesn't reset the timer.
            if viper_state == "active":
                for particle in particles:
                    if viper_rect.collidepoint(particle["x"], particle["y"]):
                        viper_state = "blinded"
                        blind_timer = VIPER_BLIND_DURATION
                        blind_sound.play()
                        taunts.append({
                            "text": random.choice(TAUNT_PHRASES),
                            "x": squirrel_x + SQUIRREL_SIZE / 2,
                            "y": squirrel_y - 20,
                            "age": 0.0,
                        })
                        break

            # Tag check -- only while free and not still invulnerable from a
            # just-consumed shield, so an already-caught squirrel can't be
            # "caught again" mid-bubble or immediately re-caught same frame.
            if squirrel_state == "free" and invulnerable_timer <= 0 and squirrel_rect.colliderect(viper_rect):
                if has_shield:
                    has_shield = False
                    invulnerable_timer = INVULNERABLE_DURATION
                else:
                    squirrel_state = "stasis"
                    stasis_timer = STASIS_DURATION
                    score += 1
                    lifetime_catches += 1
                    write_save(level_number, lifetime_catches)
                    caught_sound.play()

        # 3. Draw everything
        screen.fill(BACKGROUND_COLOR)

        if game_state == "menu":
            title_surface = title_font.render("MODIS_NeonTail", True, TEXT_COLOR)
            title_rect = title_surface.get_rect(center=(WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2 - 40))
            screen.blit(title_surface, title_rect)

            prompt_surface = font.render("Press ENTER to Play  --  L for Level Select", True, TEXT_COLOR)
            prompt_rect = prompt_surface.get_rect(center=(WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2 + 40))
            screen.blit(prompt_surface, prompt_rect)

            info_text = f"Last played: Level {level_number}   Lifetime catches: {lifetime_catches}"
            info_surface = font.render(info_text, True, TEXT_COLOR)
            info_rect = info_surface.get_rect(center=(WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2 + 100))
            screen.blit(info_surface, info_rect)

        elif game_state == "level_select":
            title_surface = title_font.render("Select Level", True, TEXT_COLOR)
            title_rect = title_surface.get_rect(center=(WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2 - 80))
            screen.blit(title_surface, title_rect)

            choice_surface = title_font.render(f"< {level_select_choice} >", True, TEXT_COLOR)
            choice_rect = choice_surface.get_rect(center=(WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2))
            screen.blit(choice_surface, choice_rect)

            hint_surface = font.render("Left/Right to choose, Enter to start, Esc to go back", True, TEXT_COLOR)
            hint_rect = hint_surface.get_rect(center=(WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2 + 80))
            screen.blit(hint_surface, hint_rect)

        else:  # game_state == "playing" or "paused"
            for wall in walls:
                pygame.draw.rect(screen, TILE_WALL_COLOR, wall)

            for landmine in landmines:
                pygame.draw.circle(screen, WHOOPEE_COLOR, landmine.center, landmine.width // 3)

            for pad in jump_pads:
                cx, cy = pad.center
                half = pad.width // 2 - 6
                diamond_points = [(cx, cy - half), (cx + half, cy), (cx, cy + half), (cx - half, cy)]
                pygame.draw.polygon(screen, JUMP_PAD_COLOR, diamond_points)

            for shield in shields:
                pygame.draw.circle(screen, SHIELD_COLOR, shield.center, shield.width // 3, width=4)

            if decoy is not None:
                decoy_rect = pygame.Rect(0, 0, SQUIRREL_SIZE, SQUIRREL_SIZE)
                decoy_rect.center = (decoy["x"], decoy["y"])
                pygame.draw.rect(screen, SQUIRREL_COLOR, decoy_rect, width=3)

            if squirrel_state == "stasis":
                bubble_center = (int(squirrel_x + SQUIRREL_SIZE / 2), int(squirrel_y + SQUIRREL_SIZE / 2))
                pygame.draw.circle(screen, STASIS_BUBBLE_COLOR, bubble_center, SQUIRREL_SIZE)
            else:
                pygame.draw.rect(screen, SQUIRREL_COLOR, squirrel_rect)
                if has_shield:
                    pygame.draw.rect(screen, SHIELD_COLOR, squirrel_rect.inflate(8, 8), width=3)
                elif invulnerable_timer > 0:
                    pygame.draw.rect(screen, TEXT_COLOR, squirrel_rect.inflate(8, 8), width=3)

            if viper_state == "blinded":
                viper_color = VIPER_BLINDED_COLOR
            elif viper_state == "stunned":
                viper_color = WHOOPEE_COLOR
            else:
                viper_color = VIPER_COLOR
            pygame.draw.rect(screen, viper_color, viper_rect)

            for particle in particles:
                pygame.draw.circle(screen, PARTICLE_COLOR, (int(particle["x"]), int(particle["y"])), PARTICLE_SIZE)

            for taunt in taunts:
                taunt_surface = font.render(taunt["text"], True, TAUNT_COLOR)
                fade = max(0.0, 1.0 - taunt["age"] / TAUNT_DURATION)
                taunt_surface.set_alpha(int(255 * fade))
                taunt_rect = taunt_surface.get_rect(center=(taunt["x"], taunt["y"]))
                screen.blit(taunt_surface, taunt_rect)

            # Score and timer, top-left corner. render() turns text into an
            # image; blit() draws that image onto the screen.
            score_surface = font.render(f"Caught: {score}", True, TEXT_COLOR)
            screen.blit(score_surface, (20, 20))

            minutes = int(game_time // 60)
            seconds = int(game_time % 60)
            timer_surface = font.render(f"Time: {minutes:02d}:{seconds:02d}", True, TEXT_COLOR)
            screen.blit(timer_surface, (20, 60))

            level_surface = font.render(f"Level: {level_number}/{LEVEL_COUNT} (N to switch)", True, TEXT_COLOR)
            screen.blit(level_surface, (20, 100))

            if game_state == "paused":
                # A semi-transparent black rectangle drawn over everything
                # else -- set_alpha() controls how see-through it is (0 =
                # invisible, 255 = solid), so the frozen game shows through.
                overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
                overlay.set_alpha(150)
                overlay.fill((0, 0, 0))
                screen.blit(overlay, (0, 0))

                paused_surface = title_font.render("PAUSED", True, TEXT_COLOR)
                paused_rect = paused_surface.get_rect(center=(WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2 - 40))
                screen.blit(paused_surface, paused_rect)

                hint_surface = font.render("Esc to resume, Q to quit", True, TEXT_COLOR)
                hint_rect = hint_surface.get_rect(center=(WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2 + 40))
                screen.blit(hint_surface, hint_rect)

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
