from pathlib import Path
import pygame

pygame.init()

sprite_dir = Path("assets/sprites")
sprite_dir.mkdir(parents=True, exist_ok=True)


def create_squirrel_sprite(tail_flag: bool = False) -> pygame.Surface:
    """Agent S.Q.U.I.R.E.L. with a 3x massive bushy neon tail."""
    surf = pygame.Surface((72, 60), pygame.SRCALPHA)

    tail_neon = (255, 140, 0)
    tail_core = (255, 215, 60)
    tail_highlight = (255, 240, 150)
    body_fur = (195, 85, 20)
    chest_cream = (245, 205, 150)

    # 1. 3x Massive Bushy Neon Tail
    if tail_flag:
        pygame.draw.circle(surf, tail_neon, (18, 20), 20)
        pygame.draw.circle(surf, tail_neon, (28, 14), 16)
        pygame.draw.circle(surf, tail_core, (20, 18), 12)
        pygame.draw.circle(surf, tail_highlight, (22, 16), 6)
    else:
        pygame.draw.ellipse(surf, tail_neon, (2, 8, 30, 46))
        pygame.draw.ellipse(surf, tail_neon, (10, 4, 26, 32))
        pygame.draw.ellipse(surf, tail_core, (8, 12, 18, 36))
        pygame.draw.ellipse(surf, tail_highlight, (12, 16, 10, 24))

    # 2. Body & Chest
    pygame.draw.ellipse(surf, body_fur, (28, 24, 26, 28))
    pygame.draw.ellipse(surf, chest_cream, (36, 28, 14, 18))

    # 3. Head & Pointed Ears
    pygame.draw.circle(surf, body_fur, (46, 24), 11)
    pygame.draw.polygon(surf, body_fur, [(42, 14), (46, 6), (50, 14)])
    pygame.draw.polygon(surf, (255, 180, 180), [(43, 13), (46, 8), (48, 13)])

    # 4. Cyber Visor
    pygame.draw.ellipse(surf, (0, 240, 255), (46, 21, 12, 6))
    pygame.draw.circle(surf, (255, 255, 255), (51, 23), 2)

    # 5. Snout & Paws
    pygame.draw.circle(surf, (40, 20, 20), (56, 26), 2)
    pygame.draw.ellipse(surf, body_fur, (30, 48, 10, 6))
    pygame.draw.ellipse(surf, body_fur, (44, 48, 10, 6))

    return surf


def create_viper_sprite() -> pygame.Surface:
    """V.I.P.E.R. with an extended 3x triple-segment serpentine thruster tail."""
    surf = pygame.Surface((84, 54), pygame.SRCALPHA)

    dark_metal = (45, 55, 75)
    light_metal = (65, 80, 105)
    neon_cyan = (0, 210, 255)
    lens_glow = (200, 255, 255)

    # 1. 3x Long Triple-Segment Serpentine Tail
    pygame.draw.circle(surf, dark_metal, (8, 27), 7)
    pygame.draw.circle(surf, neon_cyan, (4, 27), 4)

    pygame.draw.ellipse(surf, dark_metal, (14, 18, 18, 18))
    pygame.draw.ellipse(surf, neon_cyan, (18, 21, 10, 12), width=2)

    pygame.draw.ellipse(surf, dark_metal, (28, 16, 22, 22))
    pygame.draw.ellipse(surf, neon_cyan, (32, 19, 14, 16), width=2)

    # 2. Main Armored Torso
    pygame.draw.ellipse(surf, dark_metal, (44, 14, 26, 26))
    pygame.draw.ellipse(surf, neon_cyan, (48, 17, 18, 20), width=2)

    # 3. Angular Viper Drone Head
    head_points = [(56, 10), (82, 27), (56, 44), (64, 27)]
    pygame.draw.polygon(surf, light_metal, head_points)
    pygame.draw.polygon(surf, neon_cyan, head_points, width=2)

    # 4. Slit Sensor Lens
    pygame.draw.polygon(surf, lens_glow, [(68, 24), (79, 27), (68, 30)])

    return surf


if __name__ == "__main__":
    pygame.image.save(create_squirrel_sprite(tail_flag=False), sprite_dir / "squirrel.png")
    pygame.image.save(create_squirrel_sprite(tail_flag=True), sprite_dir / "squirrel_tail_flag.png")
    pygame.image.save(create_viper_sprite(), sprite_dir / "viper.png")
    print("Updated 3x enlarged sprites created successfully in assets/sprites/")