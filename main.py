"""
main.py -- MODIS_NeonTail

Phase 3, Step 2: V.I.P.E.R. now chases the squirrel when it gets close,
and returns to patrolling when the squirrel escapes its detection range.
"""

import math
import pygame

WINDOW_WIDTH = 1024
WINDOW_HEIGHT = 768
FPS = 60
BACKGROUND_COLOR = (20, 20, 40)  # dark space-blue

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
VIPER_PATROL_Y = 100


def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("MODIS_NeonTail")
    clock = pygame.time.Clock()

    squirrel_x = WINDOW_WIDTH / 2
    squirrel_y = WINDOW_HEIGHT / 2
    animation_timer = 0.0

    viper_x = VIPER_PATROL_LEFT
    viper_y = VIPER_PATROL_Y
    viper_direction = 1  # 1 = moving right, -1 = moving left

    running = True
    while running:
        delta_time = clock.tick(FPS) / 1000

        # 1. Handle input/events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

        keys = pygame.key.get_pressed()
        is_moving = False
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            squirrel_x -= SQUIRREL_SPEED * delta_time
            is_moving = True
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            squirrel_x += SQUIRREL_SPEED * delta_time
            is_moving = True
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            squirrel_y -= SQUIRREL_SPEED * delta_time
            is_moving = True
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            squirrel_y += SQUIRREL_SPEED * delta_time
            is_moving = True

        # 2. Update game state
        squirrel_x = max(0, min(WINDOW_WIDTH - SQUIRREL_SIZE, squirrel_x))
        squirrel_y = max(0, min(WINDOW_HEIGHT - SQUIRREL_SIZE, squirrel_y))

        if is_moving:
            animation_timer += delta_time
        else:
            animation_timer = 0.0
        bounce = abs(math.sin(animation_timer * ANIMATION_SPEED)) * BOUNCE_HEIGHT

        # Distance from V.I.P.E.R. to the squirrel, using each one's
        # center point -- the classic way an AI "notices" a target.
        dx = (squirrel_x + SQUIRREL_SIZE / 2) - (viper_x + VIPER_SIZE / 2)
        dy = (squirrel_y + SQUIRREL_SIZE / 2) - (viper_y + VIPER_SIZE / 2)
        distance_to_squirrel = math.hypot(dx, dy)

        if distance_to_squirrel <= VIPER_DETECTION_RANGE and distance_to_squirrel > 0:
            # CHASE: move toward the squirrel at a steady speed, however
            # far away it is (see the direction-vector explanation above).
            viper_x += (dx / distance_to_squirrel) * VIPER_CHASE_SPEED * delta_time
            viper_y += (dy / distance_to_squirrel) * VIPER_CHASE_SPEED * delta_time
        else:
            # PATROL: same back-and-forth as before, always at a fixed
            # height -- a simplification for this placeholder AI; a
            # smarter "return to patrol" (remembering exactly where it
            # left off) can come in a later phase if it's worth it.
            viper_y = VIPER_PATROL_Y
            viper_x += VIPER_PATROL_SPEED * viper_direction * delta_time
            if viper_x <= VIPER_PATROL_LEFT:
                viper_x = VIPER_PATROL_LEFT
                viper_direction = 1
            elif viper_x >= VIPER_PATROL_RIGHT:
                viper_x = VIPER_PATROL_RIGHT
                viper_direction = -1

        # Safety clamp -- chasing could otherwise push it off-screen.
        viper_x = max(0, min(WINDOW_WIDTH - VIPER_SIZE, viper_x))
        viper_y = max(0, min(WINDOW_HEIGHT - VIPER_SIZE, viper_y))

        # 3. Draw everything
        screen.fill(BACKGROUND_COLOR)
        squirrel_rect = pygame.Rect(squirrel_x, squirrel_y - bounce, SQUIRREL_SIZE, SQUIRREL_SIZE)
        pygame.draw.rect(screen, SQUIRREL_COLOR, squirrel_rect)
        viper_rect = pygame.Rect(viper_x, viper_y, VIPER_SIZE, VIPER_SIZE)
        pygame.draw.rect(screen, VIPER_COLOR, viper_rect)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
