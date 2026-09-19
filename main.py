"""
main.py -- MODIS_NeonTail

Phase 6, Step 1: tile-map level loader. Reads levels/level_001.json --
a grid of characters describing walls and start positions -- and builds
the level from it instead of hardcoding everything. Walls are drawn but
don't block movement yet.
"""

import json
import math
import random
from pathlib import Path

import pygame

LEVEL_DIR = Path(__file__).parent / "levels"
LEVEL_PATH = LEVEL_DIR / "level_001.json"
TILE_WALL_COLOR = (60, 60, 90)  # dark slate -- reads as "structure", not floor


def load_level(path):
    """Read a level JSON file and turn its character grid into wall rects
    and start positions. '#' = wall, 'S' = squirrel start, 'V' = V.I.P.E.R. start."""
    with open(path, "r", encoding="utf-8") as level_file:
        data = json.load(level_file)

    tile_size = data["tile_size"]
    grid = data["grid"]

    walls = []
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

    return walls, squirrel_start, viper_start


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


def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("MODIS_NeonTail")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 36)  # None = pygame's default built-in font

    walls, squirrel_start, viper_start = load_level(LEVEL_PATH)

    squirrel_x, squirrel_y = squirrel_start
    animation_timer = 0.0

    # squirrel_state is "free" (normal play) or "stasis" (caught, frozen
    # in the bubble for STASIS_DURATION seconds before being released).
    squirrel_state = "free"
    stasis_timer = 0.0

    viper_x, viper_y = viper_start
    viper_patrol_y = viper_y  # patrol height now comes from the level file
    viper_direction = 1  # 1 = moving right, -1 = moving left

    # viper_state is "active" (can see/chase normally) or "blinded"
    # (dirt hit it -- just patrols obliviously until blind_timer runs out).
    viper_state = "active"
    blind_timer = 0.0

    score = 0            # how many times you've been caught
    game_time = 0.0       # total seconds played, counts up

    facing_x, facing_y = 1, 0  # direction the squirrel last moved/faced
    particles = []              # each particle is a dict: x, y, vx, vy, lifetime

    running = True
    while running:
        delta_time = clock.tick(FPS) / 1000
        game_time += delta_time

        # 1. Handle input/events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                if squirrel_state == "free":
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

        # 2. Update game state
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

        if squirrel_state == "free" and viper_state == "active":
            # Distance from V.I.P.E.R. to the squirrel, using each one's
            # center point -- the classic way an AI "notices" a target.
            dx = (squirrel_x + SQUIRREL_SIZE / 2) - (viper_x + VIPER_SIZE / 2)
            dy = (squirrel_y + SQUIRREL_SIZE / 2) - (viper_y + VIPER_SIZE / 2)
            distance_to_squirrel = math.hypot(dx, dy)

            if distance_to_squirrel <= VIPER_DETECTION_RANGE and distance_to_squirrel > 0:
                chase_dx = (dx / distance_to_squirrel) * VIPER_CHASE_SPEED * delta_time
                chase_dy = (dy / distance_to_squirrel) * VIPER_CHASE_SPEED * delta_time
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

        # Advance every particle and drop the ones whose lifetime ran out.
        for particle in particles:
            particle["x"] += particle["vx"] * delta_time
            particle["y"] += particle["vy"] * delta_time
            particle["lifetime"] -= delta_time
        particles = [p for p in particles if p["lifetime"] > 0]

        # A dirt particle touching V.I.P.E.R. blinds it -- only while it
        # can currently see, so an already-blinded hit doesn't reset the timer.
        if viper_state == "active":
            for particle in particles:
                if viper_rect.collidepoint(particle["x"], particle["y"]):
                    viper_state = "blinded"
                    blind_timer = VIPER_BLIND_DURATION
                    break

        # Tag check -- only while free, so an already-caught squirrel
        # can't be "caught again" mid-bubble.
        if squirrel_state == "free" and squirrel_rect.colliderect(viper_rect):
            squirrel_state = "stasis"
            stasis_timer = STASIS_DURATION
            score += 1

        # 3. Draw everything
        screen.fill(BACKGROUND_COLOR)

        for wall in walls:
            pygame.draw.rect(screen, TILE_WALL_COLOR, wall)

        if squirrel_state == "stasis":
            bubble_center = (int(squirrel_x + SQUIRREL_SIZE / 2), int(squirrel_y + SQUIRREL_SIZE / 2))
            pygame.draw.circle(screen, STASIS_BUBBLE_COLOR, bubble_center, SQUIRREL_SIZE)
        else:
            pygame.draw.rect(screen, SQUIRREL_COLOR, squirrel_rect)

        viper_color = VIPER_BLINDED_COLOR if viper_state == "blinded" else VIPER_COLOR
        pygame.draw.rect(screen, viper_color, viper_rect)

        for particle in particles:
            pygame.draw.circle(screen, PARTICLE_COLOR, (int(particle["x"]), int(particle["y"])), PARTICLE_SIZE)

        # Score and timer, top-left corner. render() turns text into an
        # image; blit() draws that image onto the screen.
        score_surface = font.render(f"Caught: {score}", True, TEXT_COLOR)
        screen.blit(score_surface, (20, 20))

        minutes = int(game_time // 60)
        seconds = int(game_time % 60)
        timer_surface = font.render(f"Time: {minutes:02d}:{seconds:02d}", True, TEXT_COLOR)
        screen.blit(timer_surface, (20, 60))

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
