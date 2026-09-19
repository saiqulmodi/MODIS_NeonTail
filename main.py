import pygame

# Basic window settings -- we'll move these into settings.py in a later step.
WINDOW_WIDTH = 1024
WINDOW_HEIGHT = 768
FPS = 60
BACKGROUND_COLOR = (20, 20, 40)  # dark space-blue


def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("MODIS_NeonTail")
    clock = pygame.time.Clock()

    running = True
    while running:
        # 1. Handle input/events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

        # 2. Update game state (nothing to update yet)

        # 3. Draw everything
        screen.fill(BACKGROUND_COLOR)
        pygame.display.flip()

        # 4. Wait so we run at a steady 60 frames per second
        clock.tick(FPS)

    pygame.quit()


if __name__ == "__main__":
    main()