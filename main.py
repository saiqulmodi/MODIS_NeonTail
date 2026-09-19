"""
main.py -- MODIS_NeonTail

Phase 2, Step 2: the placeholder squirrel now bounces while moving --
a simple time-based animation before we have real sprite artwork.
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


def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("MODIS_NeonTail")
    clock = pygame.time.Clock()

    squirrel_x = WINDOW_WIDTH / 2
    squirrel_y = WINDOW_HEIGHT / 2
    animation_timer = 0.0

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

        # Animation: a simple "hop" while moving, using a sine wave over
        # elapsed time -- this is the core idea behind all animation.
        # Real sprite-sheet artwork (actual running frames) comes later.
        if is_moving:
            animation_timer += delta_time
        else:
            animation_timer = 0.0
        bounce = abs(math.sin(animation_timer * ANIMATION_SPEED)) * BOUNCE_HEIGHT

        # 3. Draw everything
        screen.fill(BACKGROUND_COLOR)
        squirrel_rect = pygame.Rect(squirrel_x, squirrel_y - bounce, SQUIRREL_SIZE, SQUIRREL_SIZE)
        pygame.draw.rect(screen, SQUIRREL_COLOR, squirrel_rect)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
