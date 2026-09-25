import asyncio
import math
from pathlib import Path
import random
import pygame

pygame.init()

sprite_dir = Path("assets/sprites")
sprite_dir.mkdir(parents=True, exist_ok=True)


def create_squirrel_sprite(tail_flag: bool = False, aura_color=None, alpha: int = 255) -> pygame.Surface:
    """Agent S.Q.U.I.R.E.L. with a massive bushy neon tail and power aura."""
    surf = pygame.Surface((72, 60), pygame.SRCALPHA)

    tail_neon = aura_color if aura_color else (255, 140, 0)
    tail_core = (255, 215, 60)
    tail_highlight = (255, 240, 150)
    body_fur = (195, 85, 20)
    chest_cream = (245, 205, 150)

    # Bushy Neon Tail
    if tail_flag:
        pygame.draw.circle(surf, (*tail_neon, alpha), (18, 20), 20)
        pygame.draw.circle(surf, (*tail_neon, alpha), (28, 14), 16)
        pygame.draw.circle(surf, (*tail_core, alpha), (20, 18), 12)
        pygame.draw.circle(surf, (*tail_highlight, alpha), (22, 16), 6)
    else:
        pygame.draw.ellipse(surf, (*tail_neon, alpha), (2, 8, 30, 46))
        pygame.draw.ellipse(surf, (*tail_neon, alpha), (10, 4, 26, 32))
        pygame.draw.ellipse(surf, (*tail_core, alpha), (8, 12, 18, 36))
        pygame.draw.ellipse(surf, (*tail_highlight, alpha), (12, 16, 10, 24))

    # Body & Head
    pygame.draw.ellipse(surf, (*body_fur, alpha), (28, 24, 26, 28))
    pygame.draw.ellipse(surf, (*chest_cream, alpha), (36, 28, 14, 18))
    pygame.draw.circle(surf, (*body_fur, alpha), (46, 24), 11)
    pygame.draw.polygon(surf, (*body_fur, alpha), [(42, 14), (46, 6), (50, 14)])
    pygame.draw.polygon(surf, (255, 180, 180, alpha), [(43, 13), (46, 8), (48, 13)])

    # Cyber Visor & Eye
    pygame.draw.ellipse(surf, (0, 240, 255, alpha), (46, 21, 12, 6))
    pygame.draw.circle(surf, (255, 255, 255, alpha), (51, 23), 2)

    # Paws
    pygame.draw.circle(surf, (40, 20, 20, alpha), (56, 26), 2)
    pygame.draw.ellipse(surf, (*body_fur, alpha), (30, 48, 10, 6))
    pygame.draw.ellipse(surf, (*body_fur, alpha), (44, 48, 10, 6))

    return surf


def create_viper_sprite(is_boss: bool = False, flash_white: bool = False) -> pygame.Surface:
    """V.I.P.E.R. drone sprite with hit-flash support."""
    surf = pygame.Surface((84, 54), pygame.SRCALPHA)

    if flash_white:
        dark_metal = (240, 240, 255)
        light_metal = (255, 255, 255)
        neon_accent = (255, 255, 255)
        lens_glow = (255, 255, 255)
    else:
        dark_metal = (35, 40, 55) if not is_boss else (60, 20, 25)
        light_metal = (65, 80, 105) if not is_boss else (110, 40, 50)
        neon_accent = (0, 210, 255) if not is_boss else (255, 40, 80)
        lens_glow = (200, 255, 255) if not is_boss else (255, 220, 100)

    # Thrusters
    pygame.draw.circle(surf, dark_metal, (8, 27), 7)
    pygame.draw.circle(surf, neon_accent, (4, 27), 4)
    pygame.draw.ellipse(surf, dark_metal, (14, 18, 18, 18))
    pygame.draw.ellipse(surf, neon_accent, (18, 21, 10, 12), width=2)
    pygame.draw.ellipse(surf, dark_metal, (28, 16, 22, 22))
    pygame.draw.ellipse(surf, neon_accent, (32, 19, 14, 16), width=2)

    # Torso & Head
    pygame.draw.ellipse(surf, dark_metal, (44, 14, 26, 26))
    pygame.draw.ellipse(surf, neon_accent, (48, 17, 18, 20), width=2)

    head_points = [(56, 10), (82, 27), (56, 44), (64, 27)]
    pygame.draw.polygon(surf, light_metal, head_points)
    pygame.draw.polygon(surf, neon_accent, head_points, width=2)
    pygame.draw.polygon(surf, lens_glow, [(68, 24), (79, 27), (68, 30)])

    return pygame.transform.flip(surf, True, False)


class ViperEnemy:
    PATTERNS = ["SINE_WAVE", "ZIG_ZAG", "HUNT_TRACK", "LURK_SWOOP"]

    def __init__(self, level: int, is_boss: bool = False, offset_x: int = 0):
        self.is_boss = is_boss
        self.scale = 2.8 if is_boss else 2.0
        self.width = int(84 * self.scale)
        self.height = int(54 * self.scale)

        self.normal_sprite = pygame.transform.scale(
            create_viper_sprite(is_boss=is_boss, flash_white=False), (self.width, self.height)
        )
        self.flash_sprite = pygame.transform.scale(
            create_viper_sprite(is_boss=is_boss, flash_white=True), (self.width, self.height)
        )

        self.base_anchor_x = 590.0 + offset_x
        self.x = self.base_anchor_x
        self.y = random.randint(80, 420)

        base_hp = 250 if is_boss else 60
        self.max_hp = base_hp + (level * 18 if is_boss else level * 6)
        self.hp = self.max_hp

        self.level = level
        self.speed_stat = 2.4 + min(4.0, level * 0.05)
        self.speed_y = self.speed_stat * random.choice([1, -1])

        self.current_pattern = random.choice(self.PATTERNS)
        self.pattern_timer = random.randint(120, 240)
        self.sine_angle = random.uniform(0, math.pi * 2)

        self.cooldown_max = max(18, (36 if is_boss else 52) - int(level * 0.35))
        self.shoot_timer = random.randint(0, self.cooldown_max)
        self.flash_timer = 0

    def update(self, screen_height: int, screen_width: int, player_y: float):
        self.pattern_timer -= 1
        if self.pattern_timer <= 0:
            self.current_pattern = random.choice(self.PATTERNS)
            self.pattern_timer = random.randint(120, 220)
            self.speed_y = self.speed_stat * random.choice([1, -1])

        if self.current_pattern == "SINE_WAVE":
            self.sine_angle += 0.05
            self.y += math.sin(self.sine_angle) * (self.speed_stat * 1.6)
            self.x = self.base_anchor_x + math.cos(self.sine_angle * 0.5) * 50

        elif self.current_pattern == "ZIG_ZAG":
            self.y += self.speed_y * 1.3
            if self.y <= 60 or self.y >= screen_height - self.height - 30:
                self.speed_y *= -1
            self.x += (self.base_anchor_x - self.x) * 0.05

        elif self.current_pattern == "HUNT_TRACK":
            target_diff = (player_y + 10) - self.y
            if abs(target_diff) > 8:
                self.y += math.copysign(min(abs(target_diff), self.speed_stat * 1.1), target_diff)
            forward_x = self.base_anchor_x - 110
            self.x += (forward_x - self.x) * 0.04

        elif self.current_pattern == "LURK_SWOOP":
            self.sine_angle += 0.07
            self.y += math.cos(self.sine_angle) * (self.speed_stat * 1.2)
            self.x = (self.base_anchor_x - 70) + math.sin(self.sine_angle) * 120

        self.y = max(55, min(screen_height - self.height - 20, self.y))
        self.x = max(380, min(screen_width - self.width - 15, self.x))

        if self.flash_timer > 0:
            self.flash_timer -= 1

        self.shoot_timer += 1
        should_shoot = False
        if self.shoot_timer >= self.cooldown_max:
            self.shoot_timer = 0
            should_shoot = True

        return should_shoot

    @property
    def rect(self):
        return pygame.Rect(self.x + 10, self.y + 10, self.width - 20, self.height - 20)

    @property
    def sprite(self):
        return self.flash_sprite if self.flash_timer > 0 else self.normal_sprite


def draw_bar(surface, x, y, width, height, current, maximum, bar_color):
    fill = int((max(0, current) / maximum) * width)
    pygame.draw.rect(surface, (30, 32, 45), (x, y, width, height), border_radius=4)
    if fill > 0:
        pygame.draw.rect(surface, bar_color, (x, y, fill, height), border_radius=4)
    pygame.draw.rect(surface, (180, 185, 205), (x, y, width, height), 2, border_radius=4)


WEAPON_TIERS = {
    1: {"speed": 14, "color_outer": (255, 140, 0), "color_core": (255, 230, 80), "dmg": 20, "name": "AMBER SPARK"},
    2: {"speed": 19, "color_outer": (0, 220, 255), "color_core": (200, 255, 255), "dmg": 30, "name": "CYAN PULSE"},
    3: {"speed": 25, "color_outer": (220, 50, 255), "color_core": (255, 180, 255), "dmg": 45, "name": "MAGENTA NOVA"},
    4: {"speed": 29, "color_outer": (40, 255, 120), "color_core": (210, 255, 220), "dmg": 60, "name": "EMERALD FURY"},
    5: {"speed": 35, "color_outer": (255, 50, 120), "color_core": (255, 255, 255), "dmg": 85, "name": "HYPER OVERDRIVE"},
}


async def main():
    SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("MODIS NeonTail - 100 Levels")
    clock = pygame.time.Clock()

    font = pygame.font.SysFont("consolas", 16, bold=True)
    big_font = pygame.font.SysFont("consolas", 34, bold=True)
    title_font = pygame.font.SysFont("consolas", 40, bold=True)

    scale = 2
    v_preview = pygame.transform.scale(create_viper_sprite(False), (84 * 1.4, 54 * 1.4))

    # Game States: 'HOW_TO_PLAY', 'PLAYING', 'WIN_CELEBRATION'
    game_state = "HOW_TO_PLAY"
    current_level = 1
    max_levels = 100

    # Physics & stats
    player_x, player_y = 70.0, 360.0
    vel_x, vel_y = 0.0, 0.0
    gravity = 0.55
    floor_y = 440.0
    is_grounded = True
    player_max_hp = 100
    player_hp = player_max_hp

    # Special Squirrel Moves
    vanish_timer = 0
    vanish_cooldown = 0
    dash_timer = 0
    dash_cooldown = 0
    dash_dir = 1
    ghost_trails = []

    # Weapon & Progress
    power_tier = 1
    power_charge = 0.0
    max_power_charge = 100.0

    shoot_cooldown = 0
    tail_anim_timer = 0
    total_score = 0
    combo_hits = 0
    combo_timer = 0
    level_banner_timer = 90

    # 5-Second Celebration System (300 frames @ 60 FPS)
    celebration_frames = 300
    celebration_timer = celebration_frames
    fireworks = []

    def spawn_wave(lvl):
        enemies = []
        is_boss_wave = (lvl % 10 == 0)
        if is_boss_wave:
            enemies.append(ViperEnemy(lvl, is_boss=True, offset_x=0))
        else:
            num_drones = min(3, 1 + (lvl // 15))
            for i in range(num_drones):
                enemies.append(ViperEnemy(lvl, is_boss=False, offset_x=i * 55))
        return enemies

    enemies = spawn_wave(current_level)
    player_bullets = []
    enemy_bullets = []
    energy_pickups = []

    hit_sparks = []
    floating_texts = []

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if game_state == "HOW_TO_PLAY" and event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    game_state = "PLAYING"
                # Quick restart from celebration
                if game_state == "WIN_CELEBRATION" and event.key in (pygame.K_RETURN, pygame.K_r):
                    game_state = "HOW_TO_PLAY"
                    current_level = 1

        screen.fill((10, 12, 22))

        # Background grid
        for gx in range(0, SCREEN_WIDTH, 50):
            pygame.draw.line(screen, (20, 24, 40), (gx, 0), (gx, SCREEN_HEIGHT))
        for gy in range(0, SCREEN_HEIGHT, 50):
            pygame.draw.line(screen, (20, 24, 40), (0, gy), (SCREEN_WIDTH, gy))

        current_weapon = WEAPON_TIERS[power_tier]

        s_normal = pygame.transform.scale(
            create_squirrel_sprite(False, current_weapon["color_outer"], alpha=255), (72 * scale, 60 * scale)
        )
        s_alert = pygame.transform.scale(
            create_squirrel_sprite(True, current_weapon["color_outer"], alpha=255), (72 * scale, 60 * scale)
        )
        s_ghost = pygame.transform.scale(
            create_squirrel_sprite(True, (0, 240, 255), alpha=70), (72 * scale, 60 * scale)
        )

        # ==================== STATE 1: HOW TO PLAY & POWER SURVIVAL BRIEFING ====================
        if game_state == "HOW_TO_PLAY":
            t_surf = title_font.render("MODIS NEON TAIL", True, (255, 140, 0))
            sub_surf = font.render("MISSION BRIEFING: SURVIVAL & CONTROL SYSTEMS", True, (0, 220, 255))
            screen.blit(t_surf, (SCREEN_WIDTH // 2 - t_surf.get_width() // 2, 20))
            screen.blit(sub_surf, (SCREEN_WIDTH // 2 - sub_surf.get_width() // 2, 65))

            # Controls Box
            box_left = pygame.Rect(40, 95, 350, 395)
            pygame.draw.rect(screen, (18, 22, 38), box_left, border_radius=10)
            pygame.draw.rect(screen, (0, 180, 220), box_left, 2, border_radius=10)

            title_ctrl = font.render("=== ALL CONTROL KEYS ===", True, (255, 215, 60))
            screen.blit(title_ctrl, (60, 108))

            controls_list = [
                ("[ A / D or L/R ]", "Sprint Left / Right"),
                ("[ W / UP / C ]", "Jet Jump & High Leap"),
                ("[ S / DOWN ]", "Tail Helicopter Glide (in air)"),
                ("[ SHIFT / X ]", "CYBER CLOAK (Vanish/Invulnerable)"),
                ("[ V Key ]", "WARP SWOOP (Instant forward dash)"),
                ("[ SPACEBAR ]", "Fire Evolving Neon Acorns"),
                ("[ 'N' Key ]", "Skip level (Testing shortcut)"),
                ("[ 'R' Key ]", "Instant Mission Retry"),
            ]
            y_pos = 138
            for k, d in controls_list:
                screen.blit(font.render(k, True, (255, 230, 100)), (55, y_pos))
                screen.blit(font.render(d, True, (215, 220, 235)), (55, y_pos + 17))
                y_pos += 36

            # How Power Helps You Survive Box
            box_right = pygame.Rect(410, 95, 350, 395)
            pygame.draw.rect(screen, (18, 22, 38), box_right, border_radius=10)
            pygame.draw.rect(screen, (255, 140, 0), box_right, 2, border_radius=10)

            title_pwr = font.render("=== HOW POWER SAVES YOU ===", True, (255, 140, 0))
            screen.blit(title_pwr, (430, 108))

            power_perks = [
                ("[ 2X TRAVEL SPEED ]", "Bullets cross screen instantly so"),
                ("", "drones have zero reaction time."),
                ("[ EXPANDED HITBOX ]", "Larger neon shells ensure direct hits"),
                ("", "even against erratic zig-zagging foes."),
                ("[ RAPID COOLDOWN ]", "Power cuts firing delays in half,"),
                ("", "allowing lethal continuous salvos."),
                ("[ BOSS HEALTH SHRED ]", "Tiers 4-5 deal 4x base damage to"),
                ("", "destroy crimson Overlords quickly."),
                ("[ STAGE REPAIR ]", "Clearing each level restores +30 HP."),
            ]
            y_pos_r = 138
            for label, desc in power_perks:
                if label:
                    screen.blit(font.render(label, True, (0, 255, 180)), (425, y_pos_r))
                if desc:
                    screen.blit(font.render(desc, True, (215, 220, 235)), (425, y_pos_r + (17 if label else 0)))
                y_pos_r += 32 if label else 18

            # Blinking Start Bar
            tail_anim_timer += 1
            if (tail_anim_timer // 25) % 2 == 0:
                p_surf = big_font.render(">> PRESS ENTER OR SPACE TO COMMENCE <<", True, (100, 255, 150))
                screen.blit(p_surf, (SCREEN_WIDTH // 2 - p_surf.get_width() // 2, 520))

            pygame.display.flip()
            clock.tick(60)
            await asyncio.sleep(0)
            continue

        # ==================== STATE 3: 5-SECOND GRAND WIN CELEBRATION ====================
        if game_state == "WIN_CELEBRATION":
            celebration_timer -= 1
            remaining_seconds = max(0, int(math.ceil(celebration_timer / 60.0)))

            # Spawn colorful fireworks
            if celebration_timer % 6 == 0:
                fw_x = random.randint(100, SCREEN_WIDTH - 100)
                fw_y = random.randint(80, 340)
                base_color = random.choice([
                    (255, 215, 0), (0, 240, 255), (255, 50, 120), (50, 255, 120), (255, 140, 0)
                ])
                for _ in range(25):
                    speed = random.uniform(2.5, 7.5)
                    angle = random.uniform(0, math.pi * 2)
                    fireworks.append({
                        "x": fw_x,
                        "y": fw_y,
                        "vx": math.cos(angle) * speed,
                        "vy": math.sin(angle) * speed,
                        "color": base_color,
                        "radius": random.randint(2, 5),
                        "life": random.randint(25, 45),
                    })

            # Update & draw fireworks
            for fw in fireworks[:]:
                fw["x"] += fw["vx"]
                fw["y"] += fw["vy"]
                fw["life"] -= 1
                if fw["life"] <= 0:
                    fireworks.remove(fw)
                else:
                    pygame.draw.circle(screen, fw["color"], (int(fw["x"]), int(fw["y"])), fw["radius"])

            # Victory Banners
            w_surf = title_font.render("CONGRATULATIONS, AGENT!", True, (255, 215, 60))
            sub_w = big_font.render("ALL 100 LEVELS CONQUERED", True, (0, 255, 200))
            score_w = font.render(f"FINAL CYBER SCORE: {total_score}", True, (255, 255, 255))
            time_w = big_font.render(f"Returning to Base in: {remaining_seconds}s", True, (255, 90, 140))

            screen.blit(w_surf, (SCREEN_WIDTH // 2 - w_surf.get_width() // 2, 130))
            screen.blit(sub_w, (SCREEN_WIDTH // 2 - sub_w.get_width() // 2, 190))
            screen.blit(score_w, (SCREEN_WIDTH // 2 - score_w.get_width() // 2, 260))
            screen.blit(time_w, (SCREEN_WIDTH // 2 - time_w.get_width() // 2, 320))

            # Celebratory Squirrel Doing Air Flips
            tail_anim_timer += 1
            flip_s = s_alert if (tail_anim_timer // 10) % 2 == 0 else s_normal
            screen.blit(flip_s, (SCREEN_WIDTH // 2 - 72, 410))

            if celebration_timer <= 0:
                game_state = "HOW_TO_PLAY"
                current_level = 1
                player_hp = player_max_hp
                celebration_timer = celebration_frames
                fireworks.clear()

            pygame.display.flip()
            clock.tick(60)
            await asyncio.sleep(0)
            continue

        # ==================== STATE 2: ACTIVE GAMEPLAY ====================
        keys = pygame.key.get_pressed()
        is_moving = False

        if player_hp > 0:
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                vel_x = -5.8
                dash_dir = -1
                is_moving = True
            elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                vel_x = 5.8
                dash_dir = 1
                is_moving = True
            else:
                vel_x *= 0.7

            # Jet Jump (W / UP / C)
            if (keys[pygame.K_UP] or keys[pygame.K_w] or keys[pygame.K_c]) and is_grounded:
                vel_y = -13.5
                is_grounded = False
                is_moving = True
                for _ in range(6):
                    hit_sparks.append([
                        player_x + 50,
                        player_y + 110,
                        random.uniform(-3.0, 3.0),
                        random.uniform(1.0, 4.0),
                        random.randint(2, 4),
                        (255, 140, 0),
                        15,
                    ])

            # Tail Helicopter Glide
            if (keys[pygame.K_DOWN] or keys[pygame.K_s]) and not is_grounded:
                if vel_y > 1.8:
                    vel_y = 1.8

            # Cyber Cloak
            if vanish_cooldown > 0:
                vanish_cooldown -= 1
            if (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT] or keys[pygame.K_x]) and vanish_cooldown == 0 and vanish_timer == 0:
                vanish_timer = 120
                vanish_cooldown = 300
                floating_texts.append(["CLOAK ACTIVATED!", player_x + 10, player_y - 20, (0, 240, 255), 40])
                for _ in range(12):
                    hit_sparks.append([
                        player_x + 60,
                        player_y + 50,
                        random.uniform(-4, 4),
                        random.uniform(-4, 4),
                        3,
                        (0, 240, 255),
                        20,
                    ])

            # Warp Dash
            if dash_cooldown > 0:
                dash_cooldown -= 1
            if keys[pygame.K_v] and dash_cooldown == 0 and dash_timer == 0:
                dash_timer = 14
                dash_cooldown = 110
                floating_texts.append(["WARP SWOOP!", player_x + 20, player_y - 15, (255, 230, 80), 30])

            if dash_timer > 0:
                dash_timer -= 1
                vel_x = dash_dir * 18.0
                vel_y = 0.0
                ghost_trails.append({"x": player_x, "y": player_y, "alpha": 180})

            if dash_timer == 0:
                vel_y += gravity
                player_y += vel_y

            player_x += vel_x

            if player_y >= floor_y:
                player_y = floor_y
                vel_y = 0.0
                is_grounded = True
            if player_y <= 50:
                player_y = 50
                vel_y = 0.0

            player_x = max(10, min(SCREEN_WIDTH - 250, player_x))

            # Fire weapon
            if shoot_cooldown > 0:
                shoot_cooldown -= 1
            if keys[pygame.K_SPACE] and shoot_cooldown == 0:
                b_width = 16 + (power_tier * 3)
                b_height = 8 + power_tier
                bullet_info = {
                    "rect": pygame.Rect(player_x + 115, player_y + 48, b_width, b_height),
                    "speed": current_weapon["speed"],
                    "color_outer": current_weapon["color_outer"],
                    "color_core": current_weapon["color_core"],
                    "dmg": current_weapon["dmg"],
                }
                player_bullets.append(bullet_info)
                shoot_cooldown = max(7, 13 - power_tier)

        if vanish_timer > 0:
            vanish_timer -= 1

        # Restart
        if player_hp <= 0 and keys[pygame.K_r]:
            player_hp = player_max_hp
            power_tier = 1
            power_charge = 0.0
            player_x, player_y = 70.0, 360.0
            vel_x, vel_y = 0.0, 0.0
            enemies = spawn_wave(current_level)
            player_bullets.clear()
            enemy_bullets.clear()
            energy_pickups.clear()
            hit_sparks.clear()
            floating_texts.clear()
            ghost_trails.clear()
            combo_hits = 0

        # Skip level testing
        if keys[pygame.K_n] and level_banner_timer == 0:
            enemies.clear()

        for gt in ghost_trails[:]:
            gt["alpha"] -= 16
            if gt["alpha"] <= 0:
                ghost_trails.remove(gt)

        if combo_timer > 0:
            combo_timer -= 1
        else:
            combo_hits = 0

        # Dynamic Enemy AI Updates
        for e in enemies:
            can_fire = e.update(SCREEN_HEIGHT, SCREEN_WIDTH, player_y)
            if can_fire and player_hp > 0:
                bullet_y = e.y + (e.height // 2)
                bullet_color = (255, 60, 90) if e.is_boss else (0, 220, 255)
                enemy_bullets.append({
                    "rect": pygame.Rect(e.x - 10, bullet_y, 16, 6),
                    "color": bullet_color,
                    "dmg": 18 if e.is_boss else 10,
                })

        # Update Projectiles
        for b in player_bullets[:]:
            b["rect"].x += b["speed"]
            if b["rect"].x > SCREEN_WIDTH:
                player_bullets.remove(b)

        for b in enemy_bullets[:]:
            b["rect"].x -= 9
            if b["rect"].x < 0:
                enemy_bullets.remove(b)

        p_hitbox = pygame.Rect(player_x + 30, player_y + 20, 80, 80)
        for ep in energy_pickups[:]:
            ep[0] += ep[2]
            ep[1] += ep[3]
            ep[4] -= 1
            pickup_rect = pygame.Rect(ep[0] - 8, ep[1] - 8, 16, 16)
            if p_hitbox.colliderect(pickup_rect):
                power_charge += 30.0
                energy_pickups.remove(ep)
                floating_texts.append(["+POWER!", player_x + 50, player_y - 10, (100, 255, 180), 30])
            elif ep[4] <= 0:
                energy_pickups.remove(ep)

        for b in enemy_bullets[:]:
            if p_hitbox.colliderect(b["rect"]):
                if vanish_timer > 0:
                    enemy_bullets.remove(b)
                    floating_texts.append(["DODGED!", player_x + 30, player_y - 15, (0, 240, 255), 25])
                else:
                    player_hp -= b["dmg"]
                    enemy_bullets.remove(b)
                    combo_hits = 0

        # Target hits
        for b in player_bullets[:]:
            for e in enemies[:]:
                if e.rect.colliderect(b["rect"]):
                    if b in player_bullets:
                        player_bullets.remove(b)

                    dmg = b["dmg"]
                    e.hp -= dmg
                    e.flash_timer = 3

                    combo_hits += 1
                    combo_timer = 70
                    hit_points = dmg + (combo_hits * 5)
                    total_score += hit_points

                    power_charge += 12.0
                    if power_charge >= max_power_charge and power_tier < 5:
                        power_charge = 0.0
                        power_tier += 1
                        floating_texts.append([
                            f"WEAPON UPGRADED: {WEAPON_TIERS[power_tier]['name']}!",
                            SCREEN_WIDTH // 2 - 140,
                            SCREEN_HEIGHT // 2 - 80,
                            WEAPON_TIERS[power_tier]['color_outer'],
                            50,
                        ])

                    impact_x = b["rect"].x + 8
                    impact_y = b["rect"].y + 4
                    for _ in range(8):
                        hit_sparks.append([
                            impact_x,
                            impact_y,
                            random.uniform(-4.0, 4.0),
                            random.uniform(-3.5, 3.5),
                            random.randint(2, 5),
                            random.choice([b["color_outer"], b["color_core"], (255, 255, 255)]),
                            random.randint(10, 20),
                        ])

                    floating_texts.append([
                        f"+{hit_points}",
                        impact_x - 10,
                        impact_y - 15,
                        b["color_core"],
                        30,
                    ])

                    if e.hp <= 0:
                        enemies.remove(e)
                        total_score += 200 if e.is_boss else 75
                        energy_pickups.append([
                            e.x + e.width // 2,
                            e.y + e.height // 2,
                            random.uniform(-1.5, -0.5),
                            random.uniform(-1.0, 1.0),
                            180,
                        ])
                        for _ in range(22):
                            hit_sparks.append([
                                e.x + e.width // 2,
                                e.y + e.height // 2,
                                random.uniform(-6.0, 6.0),
                                random.uniform(-6.0, 6.0),
                                random.randint(3, 7),
                                (255, 70, 90) if e.is_boss else (0, 220, 255),
                                25,
                            ])
                    break

        # Level Progression & Win Condition
        if len(enemies) == 0:
            if current_level < max_levels:
                current_level += 1
                level_banner_timer = 80
                player_hp = min(player_max_hp, player_hp + 30)
                enemies = spawn_wave(current_level)
                player_bullets.clear()
                enemy_bullets.clear()
            else:
                # 100 Levels beaten -> Start 5-second victory celebration!
                game_state = "WIN_CELEBRATION"
                celebration_timer = celebration_frames
                fireworks.clear()

        # Update hit particles & floating texts
        for spark in hit_sparks[:]:
            spark[0] += spark[2]
            spark[1] += spark[3]
            spark[6] -= 1
            if spark[6] <= 0:
                hit_sparks.remove(spark)

        for ft in floating_texts[:]:
            ft[2] -= 1.2
            ft[4] -= 1
            if ft[4] <= 0:
                floating_texts.remove(ft)

        # Draw Ghost Trails
        for gt in ghost_trails:
            g_surf = s_ghost.copy()
            g_surf.set_alpha(gt["alpha"])
            screen.blit(g_surf, (gt["x"], gt["y"]))

        # Draw Bullets
        for b in player_bullets:
            pygame.draw.ellipse(screen, b["color_core"], b["rect"])
            pygame.draw.ellipse(screen, b["color_outer"], b["rect"], 3)

        for b in enemy_bullets:
            pygame.draw.ellipse(screen, b["color"], b["rect"])

        for ep in energy_pickups:
            pygame.draw.circle(screen, (0, 255, 180), (int(ep[0]), int(ep[1])), 7)
            pygame.draw.circle(screen, (255, 255, 255), (int(ep[0]), int(ep[1])), 4)

        for spark in hit_sparks:
            pygame.draw.circle(screen, spark[5], (int(spark[0]), int(spark[1])), spark[4])

        for ft in floating_texts:
            f_surf = font.render(ft[0], True, ft[3])
            screen.blit(f_surf, (int(ft[1]), int(ft[2])))

        # Ground Floor Indicator
        pygame.draw.line(screen, (35, 45, 75), (0, int(floor_y + 115)), (SCREEN_WIDTH, int(floor_y + 115)), 2)

        # Draw Player
        tail_anim_timer += 1
        use_alert = (tail_anim_timer // 15) % 2 == 1 or is_moving or not is_grounded
        current_squirrel = s_alert if use_alert else s_normal

        if player_hp > 0:
            if vanish_timer > 0:
                if (vanish_timer // 4) % 2 == 0:
                    screen.blit(s_ghost, (player_x, player_y))
            else:
                screen.blit(current_squirrel, (player_x, player_y))

        # Draw Enemies
        for e in enemies:
            screen.blit(e.sprite, (e.x, e.y))
            bar_color = (255, 50, 70) if e.is_boss else (0, 210, 255)
            draw_bar(screen, int(e.x), int(e.y) - 12, e.width, 8, e.hp, e.max_hp, bar_color)

        # HUD
        screen.blit(font.render("AGENT S.Q.U.I.R.E.L.", True, (255, 180, 80)), (20, 10))
        draw_bar(screen, 20, 30, 140, 10, player_hp, player_max_hp, (255, 140, 0))

        p_label = f"PWR TIER {power_tier}: {current_weapon['name']}"
        screen.blit(font.render(p_label, True, current_weapon["color_outer"]), (20, 46))
        draw_bar(screen, 20, 66, 140, 8, power_charge, max_power_charge, current_weapon["color_outer"])

        cloak_status = "CLOAK: READY" if vanish_cooldown == 0 else f"CLOAK: {vanish_cooldown // 60}s"
        dash_status = "DASH: READY" if dash_cooldown == 0 else "DASH: ..."
        screen.blit(font.render(cloak_status, True, (0, 220, 255) if vanish_cooldown == 0 else (120, 140, 160)), (20, 82))
        screen.blit(font.render(dash_status, True, (255, 230, 100) if dash_cooldown == 0 else (120, 140, 160)), (140, 82))

        level_str = f"LEVEL {current_level} / {max_levels}"
        if current_level % 10 == 0:
            level_str += " [BOSS ALERT]"
        screen.blit(font.render(level_str, True, (255, 230, 100)), (SCREEN_WIDTH // 2 - 80, 12))
        screen.blit(font.render(f"SCORE: {total_score}", True, (200, 210, 240)), (SCREEN_WIDTH - 150, 12))

        if combo_hits > 1:
            c_surf = font.render(f"COMBO x{combo_hits}!", True, (255, 100, 220))
            screen.blit(c_surf, (SCREEN_WIDTH - 150, 34))

        if level_banner_timer > 0:
            level_banner_timer -= 1
            b_text = f"LEVEL {current_level}" if current_level % 10 != 0 else f"LEVEL {current_level}: VIPER OVERLORD"
            color = (255, 70, 90) if current_level % 10 == 0 else (0, 230, 255)
            b_surf = big_font.render(b_text, True, color)
            screen.blit(b_surf, (SCREEN_WIDTH // 2 - b_surf.get_width() // 2, SCREEN_HEIGHT // 2 - 50))

        if player_hp <= 0:
            over_surf = big_font.render("MISSION FAILED", True, (255, 70, 70))
            sub_surf = font.render(f"Fell at Level {current_level} - Press 'R' to Retry", True, (240, 240, 240))
            screen.blit(over_surf, (SCREEN_WIDTH // 2 - over_surf.get_width() // 2, SCREEN_HEIGHT // 2 - 30))
            screen.blit(sub_surf, (SCREEN_WIDTH // 2 - sub_surf.get_width() // 2, SCREEN_HEIGHT // 2 + 15))

        pygame.display.flip()
        clock.tick(60)
        await asyncio.sleep(0)

    pygame.quit()


if __name__ == "__main__":
    asyncio.run(main())