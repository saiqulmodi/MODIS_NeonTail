import array
import asyncio
import math
from pathlib import Path
import random
import pygame

pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
pygame.joystick.init()

joysticks = [pygame.joystick.Joystick(i) for i in range(pygame.joystick.get_count())]
for joy in joysticks:
    joy.init()

sprite_dir = Path("assets/sprites")
sprite_dir.mkdir(parents=True, exist_ok=True)


# ==============================================================================
# PROCEDURAL AUDIO SYNTHESIZER
# ==============================================================================
class RetroSoundEngine:
    @staticmethod
    def create_tone(freq_start: float, freq_end: float, duration: float, wave_type: str = "square", volume: float = 0.5) -> pygame.mixer.Sound:
        sample_rate = 44100
        total_samples = int(sample_rate * duration)
        raw_samples = array.array("h")

        for i in range(total_samples):
            t = i / total_samples
            freq = freq_start + (freq_end - freq_start) * t
            phase = (2.0 * math.pi * freq * (i / sample_rate)) % (2.0 * math.pi)

            if wave_type == "sine":
                val = math.sin(phase)
            elif wave_type == "square":
                val = 1.0 if math.sin(phase) >= 0 else -1.0
            elif wave_type == "noise":
                val = random.uniform(-1.0, 1.0)
            else:
                val = 2.0 * (phase / (2.0 * math.pi)) - 1.0

            envelope = (1.0 - t) ** 1.3
            sample_val = int(val * envelope * 32767 * volume)
            raw_samples.append(sample_val)
            raw_samples.append(sample_val)

        return pygame.mixer.Sound(buffer=raw_samples)

    def __init__(self):
        self.snd_shoot = self.create_tone(880, 240, 0.08, "square", volume=0.25)
        self.snd_v_shoot = self.create_tone(320, 680, 0.09, "sine", volume=0.3)
        self.snd_laser = self.create_tone(950, 1200, 0.12, "sine", volume=0.25)
        self.snd_hit = self.create_tone(1100, 350, 0.06, "sine", volume=0.3)
        self.snd_explode = self.create_tone(160, 40, 0.35, "noise", volume=0.45)
        self.snd_shield = self.create_tone(400, 800, 0.15, "sine", volume=0.35)
        self.snd_heal = self.create_tone(523, 1046, 0.22, "sine", volume=0.35)
        self.snd_decoy = self.create_tone(600, 1200, 0.2, "sine", volume=0.35)
        self.snd_burrow = self.create_tone(280, 90, 0.28, "square", volume=0.3)
        self.snd_win = self.create_tone(440, 880, 0.35, "sine", volume=0.4)
        self.snd_bonus = self.create_tone(500, 1400, 0.25, "sine", volume=0.45)


SFX = RetroSoundEngine()


# ==============================================================================
# HILARIOUS TRASH TALK & CLOWN AWARDS
# ==============================================================================
SQUIRREL_VICTORY_QUOTES = [
    "404: Drone aim not found!",
    "That neon tail wasn't just glowing, it was 200 IQ!",
    "System reboot required: Drone dignity deleted.",
    "Out-calculated by a rodent with an acorn launcher!",
    "Next time, bring a firmware update, not plasma!"
]

VIPER_VICTORY_QUOTES = [
    "Thermal lock complete: Rodent grounded for recalibration!",
    "Your tail glowing at 10,000 Lumens gave you away, Agent.",
    "Acorns intercepted. Security protocol fully restored.",
    "Error 200: Squirrel captured. Rerouting acorns to trash.",
    "Target neutralized. Commencing aerial victory spin!"
]

CLOWN_AWARDS = [
    ("THE STORMTROOPER AWARD", "Fired 40 acorns, hit exactly 2."),
    ("THE UNDERGROUND CHAMELEON", "Spent half the match hiding inside holes!"),
    ("PANIC SHIELDER", "Held kinetic guard when no bullets were nearby."),
    ("THE SPEED DEMON", "Ran 500 meters without stopping to aim!"),
    ("HAIR TRIGGER SPECIALIST", "Trigger finger faster than calculation speed.")
]

DANCE_STYLES = [
    ("HELICOPTER PROPELLER HOVER", "Tail spinning like a rotor blade!"),
    ("RETRO DISCO SHUFFLE", "Grooving with electric side-steps!"),
    ("JELLY WIGGLE BOUNCE", "Rubber band squish & stretch!"),
    ("CYBER MOONWALK GLIDE", "Smooth backward zero-G slide!"),
    ("SOMERSAULT FLIP CARNIVAL", "Acrobatic backflips with fireworks!")
]


# ==============================================================================
# SPRITE GENERATION
# ==============================================================================
def create_squirrel_sprite(tail_flag: bool = False, aura_color=None, alpha: int = 255) -> pygame.Surface:
    surf = pygame.Surface((72, 60), pygame.SRCALPHA)

    tail_neon = aura_color if aura_color else (255, 140, 0)
    tail_core = (255, 215, 60)
    tail_highlight = (255, 240, 150)
    body_fur = (195, 85, 20)
    chest_cream = (245, 205, 150)

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

    pygame.draw.ellipse(surf, (*body_fur, alpha), (28, 24, 26, 28))
    pygame.draw.ellipse(surf, (*chest_cream, alpha), (36, 28, 14, 18))
    pygame.draw.circle(surf, (*body_fur, alpha), (46, 24), 11)
    pygame.draw.polygon(surf, (*body_fur, alpha), [(42, 14), (46, 6), (50, 14)])
    pygame.draw.polygon(surf, (255, 180, 180, alpha), [(43, 13), (46, 8), (48, 13)])
    pygame.draw.ellipse(surf, (0, 240, 255, alpha), (46, 21, 12, 6))
    pygame.draw.circle(surf, (255, 255, 255, alpha), (51, 23), 2)
    pygame.draw.circle(surf, (40, 20, 20, alpha), (56, 26), 2)
    pygame.draw.ellipse(surf, (*body_fur, alpha), (30, 48, 10, 6))
    pygame.draw.ellipse(surf, (*body_fur, alpha), (44, 48, 10, 6))

    return surf


def create_viper_sprite(is_boss: bool = False, flash_white: bool = False, alpha: int = 255) -> pygame.Surface:
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

    pygame.draw.circle(surf, (*dark_metal, alpha), (8, 27), 7)
    pygame.draw.circle(surf, (*neon_accent, alpha), (4, 27), 4)
    pygame.draw.ellipse(surf, (*dark_metal, alpha), (14, 18, 18, 18))
    pygame.draw.ellipse(surf, (*neon_accent, alpha), (18, 21, 10, 12), width=2)
    pygame.draw.ellipse(surf, (*dark_metal, alpha), (28, 16, 22, 22))
    pygame.draw.ellipse(surf, (*neon_accent, alpha), (32, 19, 14, 16), width=2)

    pygame.draw.ellipse(surf, (*dark_metal, alpha), (44, 14, 26, 26))
    pygame.draw.ellipse(surf, (*neon_accent, alpha), (48, 17, 18, 20), width=2)

    head_points = [(56, 10), (82, 27), (56, 44), (64, 27)]
    pygame.draw.polygon(surf, (*light_metal, alpha), head_points)
    pygame.draw.polygon(surf, (*neon_accent, alpha), head_points, width=2)
    pygame.draw.polygon(surf, (*lens_glow, alpha), [(68, 24), (79, 27), (68, 30)])

    return pygame.transform.flip(surf, True, False)


# ==============================================================================
# SINGLE-PLAYER AI ENEMY CLASS
# ==============================================================================
class ViperEnemy:
    def __init__(self, level: int, is_boss: bool = False):
        self.is_boss = is_boss
        self.scale = 2.8 if is_boss else 1.9
        self.width = int(84 * self.scale)
        self.height = int(54 * self.scale)

        self.normal_sprite = pygame.transform.scale(
            create_viper_sprite(is_boss=is_boss, flash_white=False), (self.width, self.height)
        )
        self.flash_sprite = pygame.transform.scale(
            create_viper_sprite(is_boss=is_boss, flash_white=True), (self.width, self.height)
        )

        self.x = random.uniform(420, 720)
        self.y = random.uniform(80, 500)

        base_hp = 250 if is_boss else 70
        self.max_hp = base_hp + (level * 18 if is_boss else level * 6)
        self.hp = self.max_hp

        self.speed_stat = 2.5 + min(0.6, level * 0.01)
        self.angle = 180.0
        self.is_burrowed = False
        self.burrow_timer = 0
        self.burrow_cooldown = random.randint(180, 360)

        self.cooldown_max = max(22, (42 if is_boss else 54) - int(level * 0.35))
        self.shoot_timer = random.randint(0, self.cooldown_max)
        self.flash_timer = 0

    def update(self, holes, target_x, target_y, screen_w, screen_h):
        if self.flash_timer > 0:
            self.flash_timer -= 1

        if self.is_burrowed:
            self.burrow_timer -= 1
            if self.burrow_timer <= 0:
                dest = random.choice(holes)
                self.x = dest[0] - self.width // 2
                self.y = dest[1] - self.height // 2
                self.is_burrowed = False
                self.burrow_cooldown = random.randint(240, 420)
                SFX.snd_burrow.play()
            return None

        if self.burrow_cooldown > 0:
            self.burrow_cooldown -= 1
        elif len(holes) > 0 and (self.hp < self.max_hp * 0.5 or random.random() < 0.005):
            nearest = min(holes, key=lambda h: math.hypot(h[0] - (self.x + self.width // 2), h[1] - (self.y + self.height // 2)))
            dist = math.hypot(nearest[0] - (self.x + self.width // 2), nearest[1] - (self.y + self.height // 2))
            if dist < 35:
                self.is_burrowed = True
                self.burrow_timer = 120
                SFX.snd_burrow.play()
                return None
            else:
                angle = math.atan2(nearest[1] - (self.y + self.height // 2), nearest[0] - (self.x + self.width // 2))
                self.x += math.cos(angle) * self.speed_stat
                self.y += math.sin(angle) * self.speed_stat
                self.angle = math.degrees(angle)

        if not self.is_burrowed:
            center_x = self.x + self.width // 2
            center_y = self.y + self.height // 2
            dx = target_x - center_x
            dy = target_y - center_y
            dist = math.hypot(dx, dy)
            target_angle = math.atan2(dy, dx)
            self.angle = math.degrees(target_angle)

            if dist > 250:
                self.x += math.cos(target_angle) * (self.speed_stat * 0.85)
                self.y += math.sin(target_angle) * (self.speed_stat * 0.85)
            elif dist < 160:
                self.x -= math.cos(target_angle) * (self.speed_stat * 0.75)
                self.y -= math.sin(target_angle) * (self.speed_stat * 0.75)
            else:
                self.x += -math.sin(target_angle) * (self.speed_stat * 0.8)
                self.y += math.cos(target_angle) * (self.speed_stat * 0.8)

            self.x = max(20, min(screen_w - self.width - 20, self.x))
            self.y = max(60, min(screen_h - self.height - 20, self.y))

        self.shoot_timer += 1
        if self.shoot_timer >= self.cooldown_max and not self.is_burrowed:
            self.shoot_timer = 0
            b_angle = math.atan2(target_y - (self.y + self.height // 2), target_x - (self.x + self.width // 2))
            return {
                "x": self.x + self.width // 2,
                "y": self.y + self.height // 2,
                "vx": math.cos(b_angle) * 7.0,
                "vy": math.sin(b_angle) * 7.0,
                "color": (255, 60, 90) if self.is_boss else (0, 220, 255),
                "dmg": 18 if self.is_boss else 10,
            }
        return None

    @property
    def rect(self):
        return pygame.Rect(self.x + 10, self.y + 10, self.width - 20, self.height - 20)

    def draw(self, surface):
        if self.is_burrowed:
            return
        base_surf = self.flash_sprite if self.flash_timer > 0 else self.normal_sprite
        rotated = pygame.transform.rotate(base_surf, -self.angle)
        rot_rect = rotated.get_rect(center=(self.x + self.width // 2, self.y + self.height // 2))
        surface.blit(rotated, rot_rect.topleft)


# ==============================================================================
# WEAPON TIERS & CYBER LASER RAY SYSTEM
# ==============================================================================
# Tiers 1-2: Fast Plasma Projectiles
# Tiers 3-5: Continuous High-Energy Laser Beams!
WEAPON_TIERS = {
    1: {"type": "bullet", "speed": 14, "color_outer": (255, 140, 0), "color_core": (255, 230, 80), "dmg": 20, "name": "AMBER SPARK"},
    2: {"type": "bullet", "speed": 19, "color_outer": (0, 220, 255), "color_core": (200, 255, 255), "dmg": 30, "name": "CYAN PULSE"},
    3: {"type": "laser",  "beam_w": 6,  "color_outer": (220, 50, 255), "color_core": (255, 200, 255), "dmg": 3,  "name": "MAGENTA LASER RAY"},
    4: {"type": "laser",  "beam_w": 10, "color_outer": (40, 255, 120), "color_core": (210, 255, 220), "dmg": 4,  "name": "EMERALD ION BEAM"},
    5: {"type": "laser",  "beam_w": 16, "color_outer": (255, 50, 120), "color_core": (255, 255, 255), "dmg": 6,  "name": "HYPER NOVA DEATH-RAY"},
}


# ==============================================================================
# MAIN ASYNC LOOP
# ==============================================================================
async def main():
    global joysticks
    SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("MODIS NeonTail - Cyber Combat")
    clock = pygame.time.Clock()

    font = pygame.font.SysFont("consolas", 14, bold=True)
    num_font = pygame.font.SysFont("consolas", 22, bold=True)
    big_font = pygame.font.SysFont("consolas", 28, bold=True)
    title_font = pygame.font.SysFont("consolas", 34, bold=True)

    scale = 2
    game_state = "MODE_SELECT"
    prev_mode = "CAMPAIGN"

    burrow_holes = [(200, 140), (620, 150), (220, 480), (600, 470), (410, 310)]
    active_decoys = []

    # Break & Celebration Timers
    break_timer = 0
    break_winner = "P1"
    break_quote = ""
    break_award = ("", "")
    active_dance = DANCE_STYLES[0]
    fireworks = []
    bonus_won_by = None
    milestone_count = 0

    # Player 1 State
    p1_x, p1_y = 120.0, 300.0
    p1_speed = 5.4
    p1_max_hp = 300
    p1_hp = p1_max_hp
    p1_guard = False
    p1_guard_energy = 100.0
    p1_med_kits = 6
    p1_decoys = 6
    p1_shoot_cd = 0
    p1_power_tier = 1
    p1_power_charge = 0.0

    # Campaign progression
    current_level = 1
    max_levels = 100
    total_score = 0

    # Player 2 Duel State
    p1_wins = 0
    p2_wins = 0
    p2_x, p2_y = 650.0, 300.0
    p2_speed = 4.4
    p2_max_hp = 120
    p2_hp = p2_max_hp
    p2_angle = 180.0
    p2_shoot_cd = 0
    p2_flash_timer = 0
    p2_is_burrowed = False
    p2_burrow_timer = 0
    p2_burrow_cd = 0
    p2_decoys = 3
    p2_power_tier = 1
    p2_power_charge = 0.0

    def spawn_campaign_wave(lvl):
        enemies = []
        if lvl % 10 == 0:
            enemies.append(ViperEnemy(lvl, is_boss=True))
        else:
            num = min(3, 1 + (lvl // 15))
            for _ in range(num):
                enemies.append(ViperEnemy(lvl, is_boss=False))
        return enemies

    campaign_enemies = spawn_campaign_wave(current_level)
    p1_bullets = []
    p2_bullets = []
    enemy_bullets = []
    hit_sparks = []
    floating_texts = []

    def handle_round_conclusion(winner: str, origin_mode: str):
        nonlocal game_state, break_timer, break_winner, break_quote, break_award, active_dance, bonus_won_by, prev_mode, milestone_count
        prev_mode = origin_mode
        break_winner = winner
        bonus_won_by = None
        fireworks.clear()

        wins = p1_wins if winner == "P1" else p2_wins
        is_5th_milestone = False

        if origin_mode == "DUEL" and wins > 0 and wins % 5 == 0:
            is_5th_milestone = True
            milestone_count = wins
        elif origin_mode == "CAMPAIGN" and current_level > 0 and current_level % 5 == 0 and winner == "P1":
            is_5th_milestone = True
            milestone_count = current_level

        if is_5th_milestone:
            game_state = "MILESTONE_CELEBRATION"
            break_timer = 300
            break_quote = random.choice(SQUIRREL_VICTORY_QUOTES if winner == "P1" else VIPER_VICTORY_QUOTES)
            break_award = random.choice(CLOWN_AWARDS)
            active_dance = random.choice(DANCE_STYLES)
            SFX.snd_win.play()
        else:
            game_state = "NORMAL_ROUND_BREAK"
            break_timer = 75
            SFX.snd_hit.play()

    def reset_positions():
        nonlocal p1_x, p1_y, p2_x, p2_y, p1_bullets, p2_bullets, enemy_bullets, active_decoys
        p1_x, p1_y = 120.0, 300.0
        p2_x, p2_y = 650.0, 300.0
        p1_bullets.clear()
        p2_bullets.clear()
        enemy_bullets.clear()
        active_decoys.clear()

    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()
        ps_pad_p1 = joysticks[0] if len(joysticks) > 0 else None
        ps_pad_p2 = joysticks[1] if len(joysticks) > 1 else None

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.JOYDEVICEADDED:
                joysticks.clear()
                for i in range(pygame.joystick.get_count()):
                    j = pygame.joystick.Joystick(i)
                    j.init()
                    joysticks.append(j)

            # Mode Selection
            if game_state == "MODE_SELECT":
                if (event.type == pygame.KEYDOWN and event.key in (pygame.K_1, pygame.K_KP1)) or \
                   (event.type == pygame.JOYBUTTONDOWN and event.button == 0):
                    game_state = "CAMPAIGN"
                    p1_max_hp = 300
                    p1_hp = p1_max_hp
                    p1_med_kits = 6
                    p1_decoys = 6
                    p1_power_tier = 1
                    p1_power_charge = 0.0
                    SFX.snd_win.play()

                elif (event.type == pygame.KEYDOWN and event.key in (pygame.K_2, pygame.K_KP2)) or \
                     (event.type == pygame.JOYBUTTONDOWN and event.button == 1):
                    game_state = "DUEL"
                    p1_max_hp = 120
                    p1_hp = p1_max_hp
                    p1_med_kits = 2
                    p1_decoys = 3
                    p1_power_tier = 1
                    p1_power_charge = 0.0
                    p2_max_hp = 120
                    p2_hp = p2_max_hp
                    p2_decoys = 3
                    p2_power_tier = 1
                    p2_power_charge = 0.0
                    SFX.snd_win.play()

            # Speed-Reflex Quiz during 5s Milestone
            if game_state == "MILESTONE_CELEBRATION" and bonus_won_by is None:
                if (event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE) or \
                   (event.type == pygame.JOYBUTTONDOWN and ps_pad_p1 and event.joy == 0 and event.button == 0):
                    bonus_won_by = "P1"
                    SFX.snd_bonus.play()
                elif (event.type == pygame.KEYDOWN and event.key in (pygame.K_KP0, pygame.K_RSHIFT)) or \
                     (event.type == pygame.JOYBUTTONDOWN and ps_pad_p2 and event.joy == 1 and event.button == 0):
                    bonus_won_by = "P2"
                    SFX.snd_bonus.play()

            # P1 Heal
            if game_state in ("CAMPAIGN", "DUEL") and p1_med_kits > 0 and p1_hp < p1_max_hp:
                if (event.type == pygame.KEYDOWN and event.key in (pygame.K_q, pygame.K_m)) or \
                   (event.type == pygame.JOYBUTTONDOWN and ps_pad_p1 and event.joy == 0 and event.button in (1, 2, 3)):
                    heal_amt = 60 if game_state == "CAMPAIGN" else 35
                    p1_hp = min(p1_max_hp, p1_hp + heal_amt)
                    p1_med_kits -= 1
                    SFX.snd_heal.play()
                    floating_texts.append([f"+{heal_amt} HP", p1_x + 10, p1_y - 20, (100, 255, 120), 35])

            # P1 Decoy
            if game_state in ("CAMPAIGN", "DUEL") and p1_decoys > 0:
                if (event.type == pygame.KEYDOWN and event.key == pygame.K_f) or \
                   (event.type == pygame.JOYBUTTONDOWN and ps_pad_p1 and event.joy == 0 and event.button == 3):
                    p1_decoys -= 1
                    active_decoys.append({"x": p1_x, "y": p1_y, "life": 240, "type": "p1"})
                    SFX.snd_decoy.play()
                    floating_texts.append(["HOLOGRAPHIC DECOY DEPLOYED!", p1_x, p1_y - 25, (0, 240, 255), 35])

            # P2 Decoy in Duel
            if game_state == "DUEL" and p2_decoys > 0:
                if (event.type == pygame.KEYDOWN and event.key in (pygame.K_KP7, pygame.K_LEFTBRACKET)) or \
                   (event.type == pygame.JOYBUTTONDOWN and ps_pad_p2 and event.joy == 1 and event.button == 4):
                    p2_decoys -= 1
                    active_decoys.append({"x": p2_x, "y": p2_y, "life": 240, "type": "p2"})
                    SFX.snd_decoy.play()
                    floating_texts.append(["VIPER HOLOGRAM DEPLOYED!", p2_x, p2_y - 25, (200, 100, 255), 35])

            # P2 Burrow in Duel
            if game_state == "DUEL" and not p2_is_burrowed and p2_burrow_cd == 0:
                if (event.type == pygame.KEYDOWN and event.key in (pygame.K_KP_ENTER, pygame.K_SLASH)) or \
                   (event.type == pygame.JOYBUTTONDOWN and ps_pad_p2 and event.joy == 1 and event.button == 5):
                    nearest = min(burrow_holes, key=lambda h: math.hypot(h[0] - (p2_x + 40), h[1] - (p2_y + 25)))
                    if math.hypot(nearest[0] - (p2_x + 40), nearest[1] - (p2_y + 25)) < 110:
                        p2_is_burrowed = True
                        p2_burrow_timer = 90
                        p2_burrow_cd = 240
                        SFX.snd_burrow.play()

            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                game_state = "MODE_SELECT"

        screen.fill((10, 12, 22))

        for gx in range(0, SCREEN_WIDTH, 50):
            pygame.draw.line(screen, (20, 24, 40), (gx, 0), (gx, SCREEN_HEIGHT))
        for gy in range(0, SCREEN_HEIGHT, 50):
            pygame.draw.line(screen, (20, 24, 40), (0, gy), (SCREEN_WIDTH, gy))

        # ======================================================================
        # STATE 1: MODE SELECT SCREEN
        # ======================================================================
        if game_state == "MODE_SELECT":
            t_surf = title_font.render("MODIS NEON TAIL", True, (255, 140, 0))
            sub_surf = font.render("CHOOSE GAMEPLAY MODE", True, (0, 220, 255))
            screen.blit(t_surf, (SCREEN_WIDTH // 2 - t_surf.get_width() // 2, 70))
            screen.blit(sub_surf, (SCREEN_WIDTH // 2 - sub_surf.get_width() // 2, 115))

            card1 = pygame.Rect(60, 160, 325, 300)
            pygame.draw.rect(screen, (18, 22, 38), card1, border_radius=12)
            pygame.draw.rect(screen, (255, 140, 0), card1, 2, border_radius=12)

            screen.blit(big_font.render("1P CAMPAIGN", True, (255, 180, 80)), (80, 180))
            lines1 = [
                "Agent S.Q.U.I.R.E.L. vs AI Swarm",
                "[PLAYER GETS 3X EVERYTHING]:",
                "- 3x Max HP (300 Health)",
                "- 3x Nanotech Med-Kits (6 Kits)",
                "- 3x Virtual Decoys (6 Holograms)",
                "- Tiers 3-5: HIGH-ENERGY LASER RAY",
                "",
                ">> PRESS '1' OR CROSS (X) <<",
            ]
            y_c1 = 220
            for ln in lines1:
                col = (100, 255, 150) if ">>" in ln else ((255, 220, 100) if "3X" in ln else (210, 220, 235))
                screen.blit(font.render(ln, True, col), (75, y_c1))
                y_c1 += 24

            card2 = pygame.Rect(415, 160, 325, 300)
            pygame.draw.rect(screen, (18, 22, 38), card2, border_radius=12)
            pygame.draw.rect(screen, (0, 210, 255), card2, 2, border_radius=12)

            screen.blit(big_font.render("2P DUEL (PVP)", True, (0, 220, 255)), (440, 180))
            lines2 = [
                "P1 (Squirrel) vs P2 (Viper)",
                "[EQUAL BALANCED POWER]:",
                "- Equal 120 HP for both players",
                "- 3 Virtual Image Decoys each",
                "- Tiers 3-5: LASER RAYS FOR BOTH",
                "- 5-Round Milestone Dance Breaks",
                "- P2 Burrow & Teleport Ambush",
                "",
                ">> PRESS '2' OR CIRCLE (O) <<",
            ]
            y_c2 = 220
            for ln in lines2:
                col = (100, 255, 150) if ">>" in ln else ((0, 240, 255) if "EQUAL" in ln else (210, 220, 235))
                screen.blit(font.render(ln, True, col), (430, y_c2))
                y_c2 += 24

            pad_msg = "PlayStation Gamepad Connected" if ps_pad_p1 else "Keyboard Connected"
            screen.blit(font.render(f"Controller: {pad_msg} | Esc to Switch Modes", True, (160, 170, 190)), (SCREEN_WIDTH // 2 - 190, 505))

            pygame.display.flip()
            clock.tick(60)
            await asyncio.sleep(0)
            continue

        # ======================================================================
        # STATE 2A: FAST 1-SECOND TACTICAL ROUND INTERLUDE (ROUNDS 1, 2, 3, 4...)
        # ======================================================================
        if game_state == "NORMAL_ROUND_BREAK":
            break_timer -= 1

            r_msg = "ROUND WON BY AGENT S.Q.U.I.R.E.L.!" if break_winner == "P1" else "ROUND WON BY V.I.P.E.R. DRONE!"
            r_col = (255, 180, 80) if break_winner == "P1" else (0, 220, 255)
            screen.blit(title_font.render(r_msg, True, r_col), (SCREEN_WIDTH // 2 - 270, 240))
            screen.blit(font.render("RESTORING POSITIONS...", True, (200, 210, 230)), (SCREEN_WIDTH // 2 - 90, 290))

            if break_timer <= 0:
                if prev_mode == "CAMPAIGN":
                    game_state = "CAMPAIGN"
                    if break_winner == "P1":
                        current_level = min(max_levels, current_level + 1)
                    p1_hp = min(p1_max_hp, p1_hp + 40)
                    campaign_enemies = spawn_campaign_wave(current_level)
                else:
                    game_state = "DUEL"
                    p1_hp = p1_max_hp
                    p2_hp = p2_max_hp

                reset_positions()

            pygame.display.flip()
            clock.tick(60)
            await asyncio.sleep(0)
            continue

        # ======================================================================
        # STATE 2B: 5-SECOND GRAND MILESTONE CELEBRATION (EVERY 5 ROUND WINS)
        # ======================================================================
        if game_state == "MILESTONE_CELEBRATION":
            break_timer -= 1
            rem_sec = max(0, int(math.ceil(break_timer / 60.0)))
            t_progress = 300 - break_timer

            # Fireworks burst
            if break_timer % 3 == 0:
                fx = random.randint(80, SCREEN_WIDTH - 80)
                fy = random.randint(50, 240)
                col = random.choice([(255, 215, 0), (0, 240, 255), (255, 50, 120), (50, 255, 120), (255, 140, 0)])
                for _ in range(22):
                    ang = random.uniform(0, math.pi * 2)
                    sp = random.uniform(2.5, 7.5)
                    fireworks.append({"x": fx, "y": fy, "vx": math.cos(ang) * sp, "vy": math.sin(ang) * sp, "col": col, "life": 32})

            for fw in fireworks[:]:
                fw["x"] += fw["vx"]
                fw["y"] += fw["vy"]
                fw["life"] -= 1
                if fw["life"] <= 0:
                    fireworks.remove(fw)
                else:
                    pygame.draw.circle(screen, fw["col"], (int(fw["x"]), int(fw["y"])), 3)

            # Golden Tournament Milestone Header
            m_title = f"*** TOURNAMENT MILESTONE: {milestone_count} ROUNDS CONQUERED! ***"
            m_surf = title_font.render(m_title, True, (255, 215, 60))
            screen.blit(m_surf, (SCREEN_WIDTH // 2 - m_surf.get_width() // 2, 20))

            # Speech Bubble
            speech_box = pygame.Rect(120, 68, 560, 46)
            pygame.draw.rect(screen, (25, 30, 50), speech_box, border_radius=10)
            pygame.draw.rect(screen, (255, 140, 0) if break_winner == "P1" else (0, 220, 255), speech_box, 2, border_radius=10)
            q_surf = font.render(f'"{break_quote}"', True, (255, 230, 100))
            screen.blit(q_surf, (SCREEN_WIDTH // 2 - q_surf.get_width() // 2, 82))

            # Clown Award Box
            award_box = pygame.Rect(160, 122, 480, 48)
            pygame.draw.rect(screen, (35, 20, 35), award_box, border_radius=8)
            pygame.draw.rect(screen, (255, 100, 200), award_box, 2, border_radius=8)
            screen.blit(font.render(f"[ {break_award[0]} ]", True, (255, 100, 200)), (180, 128))
            screen.blit(font.render(break_award[1], True, (220, 225, 240)), (180, 148))

            # Reflex Challenge Box
            quiz_box = pygame.Rect(100, 178, 600, 78)
            pygame.draw.rect(screen, (15, 35, 30) if bonus_won_by else (18, 24, 45), quiz_box, border_radius=12)
            pygame.draw.rect(screen, (0, 255, 180), quiz_box, 2, border_radius=12)

            ch_title = font.render(">> 5-ROUND COGNITIVE SPEED-REFLEX CHALLENGE <<", True, (0, 255, 180))
            screen.blit(ch_title, (SCREEN_WIDTH // 2 - ch_title.get_width() // 2, 186))

            if bonus_won_by is None:
                prompt_txt = "FIRST TO HIT [SPACE] (P1) OR [NUM 0] (P2) GETS +30 HP OVERCHARGE!"
                screen.blit(font.render(prompt_txt, True, (255, 255, 255)), (SCREEN_WIDTH // 2 - 250, 210))
                screen.blit(font.render("(OR CROSS BUTTON ON PS GAMEPAD)", True, (255, 215, 60)), (SCREEN_WIDTH // 2 - 130, 230))
            else:
                reward_winner = "PLAYER 1 (S.Q.U.I.R.E.L.)" if bonus_won_by == "P1" else "PLAYER 2 (V.I.P.E.R.)"
                rew_txt = f"LIGHTNING FAST! {reward_winner} CLAIMED +30 HP BONUS!"
                screen.blit(font.render(rew_txt, True, (100, 255, 140)), (SCREEN_WIDTH // 2 - 235, 218))

            dance_name = active_dance[0]
            center_x, center_y = 280 if break_winner == "P1" else 520, 385
            loser_x, loser_y = 520 if break_winner == "P1" else 280, 385

            screen.blit(big_font.render(f"DANCE ROUTINE: {dance_name}", True, (255, 220, 100)), (SCREEN_WIDTH // 2 - 200, 268))
            screen.blit(font.render(f"({active_dance[1]})", True, (200, 210, 230)), (SCREEN_WIDTH // 2 - 140, 302))

            if break_winner == "P1":
                win_sprite_raw = create_squirrel_sprite(True, (255, 140, 0))
            else:
                win_sprite_raw = create_viper_sprite(is_boss=False, flash_white=False)

            if "HELICOPTER" in dance_name:
                hover_y = center_y + math.sin(t_progress * 0.15) * 25
                rot_ang = (t_progress * 24) % 360
                w_surf = pygame.transform.scale(win_sprite_raw, (72 * scale, 60 * scale))
                w_rot = pygame.transform.rotate(w_surf, rot_ang)
                screen.blit(w_rot, w_rot.get_rect(center=(center_x, hover_y)))

                for _ in range(2):
                    pygame.draw.circle(screen, (255, 215, 60), (center_x + random.randint(-40, 40), int(hover_y + random.randint(20, 50))), random.randint(2, 4))

            elif "DISCO" in dance_name:
                step_x = center_x + math.sin(t_progress * 0.25) * 45
                tilt = math.sin(t_progress * 0.25) * 22
                w_surf = pygame.transform.scale(win_sprite_raw, (72 * scale, 60 * scale))
                w_rot = pygame.transform.rotate(w_surf, tilt)
                screen.blit(w_rot, w_rot.get_rect(center=(step_x, center_y)))

                floor_col = random.choice([(255, 50, 120), (0, 240, 255), (255, 215, 0), (50, 255, 120)])
                pygame.draw.ellipse(screen, floor_col, (step_x - 45, center_y + 40, 90, 16), 3)

            elif "JELLY" in dance_name:
                squish = 1.0 + math.sin(t_progress * 0.28) * 0.35
                w = int(72 * scale * squish)
                h = int(60 * scale * (2.0 - squish))
                w_surf = pygame.transform.scale(win_sprite_raw, (max(10, w), max(10, h)))
                screen.blit(w_surf, w_surf.get_rect(center=(center_x, center_y)))

            elif "MOONWALK" in dance_name:
                slide_x = center_x + ((t_progress * 2) % 140) - 70
                bob_y = center_y + abs(math.sin(t_progress * 0.2)) * -18
                w_surf = pygame.transform.scale(win_sprite_raw, (72 * scale, 60 * scale))
                w_flip = pygame.transform.flip(w_surf, True, False)
                screen.blit(w_flip, w_flip.get_rect(center=(slide_x, bob_y)))
                pygame.draw.line(screen, (0, 240, 255), (slide_x - 30, center_y + 35), (slide_x + 30, center_y + 35), 2)

            else:
                rot_ang = (t_progress * 14) % 360
                jump_y = center_y - abs(math.sin(t_progress * 0.12)) * 50
                w_surf = pygame.transform.scale(win_sprite_raw, (72 * scale, 60 * scale))
                w_rot = pygame.transform.rotate(w_surf, rot_ang)
                screen.blit(w_rot, w_rot.get_rect(center=(center_x, jump_y)))

            # Loser Animation
            if break_winner == "P1":
                v_loser = pygame.transform.scale(create_viper_sprite(is_boss=False, flash_white=(break_timer % 10 < 5)), (84 * 1.9, 54 * 1.9))
                screen.blit(v_loser, v_loser.get_rect(center=(loser_x, loser_y)))
                screen.blit(font.render("SMOKING ENGINE...", True, (255, 80, 80)), (loser_x - 60, loser_y + 45))
                pygame.draw.circle(screen, (100, 100, 120), (loser_x + random.randint(-15, 15), loser_y - 25 - (t_progress % 30)), random.randint(4, 9))
            else:
                s_loser = pygame.transform.scale(create_squirrel_sprite(False, (255, 80, 80)), (72 * scale, 60 * scale))
                screen.blit(s_loser, (loser_x - 72, loser_y - 30))
                screen.blit(font.render("DIZZY STUN...", True, (255, 80, 80)), (loser_x - 50, loser_y + 45))
                star_x = loser_x - 20 + math.cos(t_progress * 0.2) * 35
                star_y = loser_y - 45 + math.sin(t_progress * 0.2) * 15
                pygame.draw.circle(screen, (255, 230, 80), (int(star_x), int(star_y)), 4)

            next_label = f"ROUND {milestone_count + 1}"
            screen.blit(big_font.render(f"{next_label} IN: {rem_sec}s", True, (255, 230, 100)), (SCREEN_WIDTH // 2 - 110, 535))

            if break_timer <= 0:
                if prev_mode == "CAMPAIGN":
                    game_state = "CAMPAIGN"
                    current_level = min(max_levels, current_level + 1)
                    p1_hp = min(p1_max_hp, p1_hp + (80 if bonus_won_by == "P1" else 50))
                    p1_med_kits = min(6, p1_med_kits + 1)
                    p1_decoys = min(6, p1_decoys + 1)
                    campaign_enemies = spawn_campaign_wave(current_level)
                else:
                    game_state = "DUEL"
                    p1_hp = min(p1_max_hp, 120 + (30 if bonus_won_by == "P1" else 0))
                    p2_hp = min(p2_max_hp, 120 + (30 if bonus_won_by == "P2" else 0))
                    p1_med_kits = 2
                    p1_decoys = 3
                    p2_decoys = 3

                reset_positions()

            pygame.display.flip()
            clock.tick(60)
            await asyncio.sleep(0)
            continue

        # Draw Stealth Holes
        for hole in burrow_holes:
            pygame.draw.circle(screen, (35, 10, 50), hole, 22)
            pygame.draw.circle(screen, (160, 40, 255), hole, 22, 2)
            pygame.draw.circle(screen, (10, 5, 20), hole, 16)

        keys = pygame.key.get_pressed()
        mouse_buttons = pygame.mouse.get_pressed()

        center_p1_x = p1_x + 50
        center_p1_y = p1_y + 40
        p1_laser_active = False
        p2_laser_active = False

        for dec in active_decoys[:]:
            dec["life"] -= 1
            if dec["life"] <= 0:
                active_decoys.remove(dec)

        # ======================================================================
        # PLAYER 1 CONTROLS
        # ======================================================================
        if p1_hp > 0:
            pad_x = ps_pad_p1.get_axis(0) if ps_pad_p1 and abs(ps_pad_p1.get_axis(0)) > 0.15 else 0.0
            pad_y = ps_pad_p1.get_axis(1) if ps_pad_p1 and abs(ps_pad_p1.get_axis(1)) > 0.15 else 0.0

            if keys[pygame.K_a] or pad_x < -0.3:
                p1_x -= p1_speed
            if keys[pygame.K_d] or pad_x > 0.3:
                p1_x += p1_speed
            if keys[pygame.K_w] or pad_y < -0.3:
                p1_y -= p1_speed
            if keys[pygame.K_s] or pad_y > 0.3:
                p1_y += p1_speed

            p1_x = max(10, min(SCREEN_WIDTH - 110, p1_x))
            p1_y = max(55, min(SCREEN_HEIGHT - 90, p1_y))

            pad_guard = ps_pad_p1 and (ps_pad_p1.get_button(4) or ps_pad_p1.get_button(9) or ps_pad_p1.get_axis(4) > 0.3)
            if (keys[pygame.K_e] or pad_guard) and p1_guard_energy > 5.0:
                p1_guard = True
                p1_guard_energy -= 0.6
            else:
                p1_guard = False
                if p1_guard_energy < 100.0:
                    p1_guard_energy += 0.3

            pad_aim_x = ps_pad_p1.get_axis(2) if ps_pad_p1 and abs(ps_pad_p1.get_axis(2)) > 0.2 else 0.0
            pad_aim_y = ps_pad_p1.get_axis(3) if ps_pad_p1 and abs(ps_pad_p1.get_axis(3)) > 0.2 else 0.0

            if math.hypot(pad_aim_x, pad_aim_y) > 0.3:
                p1_aim_angle = math.atan2(pad_aim_y, pad_aim_x)
            else:
                p1_aim_angle = math.atan2(mouse_pos[1] - center_p1_y, mouse_pos[0] - center_p1_x)

            pad_shoot = ps_pad_p1 and (ps_pad_p1.get_button(0) or ps_pad_p1.get_button(5) or (ps_pad_p1.get_numaxes() > 5 and ps_pad_p1.get_axis(5) > 0.3))
            current_wpn = WEAPON_TIERS[p1_power_tier]
            is_firing = (mouse_buttons[0] or keys[pygame.K_SPACE] or pad_shoot) and not p1_guard

            # Tiers 3-5: CONTINUOUS LASER RAY BEAM
            if current_wpn["type"] == "laser" and is_firing:
                p1_laser_active = True
                p1_laser_end_x = center_p1_x + math.cos(p1_aim_angle) * 900
                p1_laser_end_y = center_p1_y + math.sin(p1_aim_angle) * 900

                # Laser damage ticks
                laser_dmg = current_wpn["dmg"] * (3 if game_state == "CAMPAIGN" else 1)
                p1_dmg_box = pygame.Rect(min(center_p1_x, p1_laser_end_x), min(center_p1_y, p1_laser_end_y),
                                         abs(p1_laser_end_x - center_p1_x) + 10, abs(p1_laser_end_y - center_p1_y) + 10)

                # Laser hitting AI enemies in Campaign
                if game_state == "CAMPAIGN":
                    for e in campaign_enemies:
                        if not e.is_burrowed and e.rect.colliderect(p1_dmg_box):
                            e.hp -= laser_dmg
                            e.flash_timer = 2
                            total_score += laser_dmg
                            p1_power_charge += 0.8
                            if random.random() < 0.3:
                                hit_sparks.append([e.x + e.width // 2, e.y + e.height // 2, random.uniform(-4, 4), random.uniform(-4, 4), 3, current_wpn["color_outer"], 12])
                            if e.hp <= 0:
                                campaign_enemies.remove(e)
                                SFX.snd_explode.play()

                # Laser hitting P2 in Duel
                elif game_state == "DUEL" and p2_hp > 0 and not p2_is_burrowed:
                    p2_hitbox = pygame.Rect(p2_x + 10, p2_y + 10, 70, 45)
                    if p2_hitbox.colliderect(p1_dmg_box):
                        p2_hp = max(0, p2_hp - laser_dmg)
                        p2_flash_timer = 2
                        p1_power_charge += 0.8
                        if random.random() < 0.3:
                            hit_sparks.append([p2_x + 40, p2_y + 25, random.uniform(-4, 4), random.uniform(-4, 4), 3, current_wpn["color_outer"], 12])

                # Upgrade power tier
                if p1_power_charge >= 100.0 and p1_power_tier < 5:
                    p1_power_charge = 0.0
                    p1_power_tier += 1
                    SFX.snd_win.play()
                    floating_texts.append([f"LASER UPGRADED: {WEAPON_TIERS[p1_power_tier]['name']}!", SCREEN_WIDTH // 2 - 140, 200, WEAPON_TIERS[p1_power_tier]["color_outer"], 45])

            # Tiers 1-2: FAST PLASMA BULLETS
            elif current_wpn["type"] == "bullet":
                p1_dmg = current_wpn["dmg"] * (3 if game_state == "CAMPAIGN" else 1)
                if p1_shoot_cd > 0:
                    p1_shoot_cd -= 1
                if is_firing and p1_shoot_cd == 0:
                    p1_bullets.append({
                        "x": center_p1_x, "y": center_p1_y,
                        "vx": math.cos(p1_aim_angle) * current_wpn["speed"],
                        "vy": math.sin(p1_aim_angle) * current_wpn["speed"],
                        "radius": 6 + p1_power_tier,
                        "dmg": p1_dmg,
                        "color_outer": current_wpn["color_outer"],
                        "color_core": current_wpn["color_core"],
                    })
                    SFX.snd_shoot.play()
                    p1_shoot_cd = 12

        # ======================================================================
        # 1-PLAYER CAMPAIGN LOGIC
        # ======================================================================
        if game_state == "CAMPAIGN":
            p1_target_x = center_p1_x
            p1_target_y = center_p1_y

            p1_decoys_active = [d for d in active_decoys if d["type"] == "p1"]
            if len(p1_decoys_active) > 0:
                p1_target_x = p1_decoys_active[0]["x"] + 36
                p1_target_y = p1_decoys_active[0]["y"] + 30

            for e in campaign_enemies:
                shot = e.update(burrow_holes, p1_target_x, p1_target_y, SCREEN_WIDTH, SCREEN_HEIGHT)
                if shot and p1_hp > 0:
                    enemy_bullets.append(shot)

            for b in enemy_bullets[:]:
                b["x"] += b["vx"]
                b["y"] += b["vy"]
                if b["x"] < 0 or b["x"] > SCREEN_WIDTH or b["y"] < 0 or b["y"] > SCREEN_HEIGHT:
                    enemy_bullets.remove(b)

            p1_hitbox = pygame.Rect(p1_x + 15, p1_y + 10, 70, 60)
            for b in enemy_bullets[:]:
                b_rect = pygame.Rect(b["x"] - 6, b["y"] - 6, 12, 12)
                if p1_guard and math.hypot(b["x"] - center_p1_x, b["y"] - center_p1_y) < 60:
                    enemy_bullets.remove(b)
                    SFX.snd_shield.play()
                    floating_texts.append(["BLOCKED!", center_p1_x - 20, center_p1_y - 40, (0, 255, 220), 20])
                elif p1_hitbox.colliderect(b_rect):
                    p1_hp = max(0, p1_hp - b["dmg"])
                    enemy_bullets.remove(b)
                    SFX.snd_hit.play()

            for b in p1_bullets[:]:
                b_rect = pygame.Rect(b["x"] - b["radius"], b["y"] - b["radius"], b["radius"] * 2, b["radius"] * 2)
                for e in campaign_enemies[:]:
                    if not e.is_burrowed and e.rect.colliderect(b_rect):
                        if b in p1_bullets:
                            p1_bullets.remove(b)
                        e.hp -= b["dmg"]
                        e.flash_timer = 3
                        SFX.snd_hit.play()

                        total_score += b["dmg"]
                        p1_power_charge += 12.0
                        if p1_power_charge >= 100.0 and p1_power_tier < 5:
                            p1_power_charge = 0.0
                            p1_power_tier += 1
                            SFX.snd_win.play()
                            floating_texts.append([f"POWER TIER {p1_power_tier}!", SCREEN_WIDTH // 2 - 90, 200, (255, 215, 60), 40])

                        floating_texts.append([f"+{b['dmg']} PTS", b["x"], b["y"] - 15, b["color_core"], 25])

                        if e.hp <= 0:
                            campaign_enemies.remove(e)
                            SFX.snd_explode.play()
                        break

            if len(campaign_enemies) == 0:
                handle_round_conclusion("P1", "CAMPAIGN")

            if p1_hp <= 0:
                handle_round_conclusion("P2", "CAMPAIGN")

        # ======================================================================
        # 2-PLAYER DUEL LOGIC
        # ======================================================================
        elif game_state == "DUEL":
            center_p2_x = p2_x + 40
            center_p2_y = p2_y + 25

            if p2_hp > 0:
                if p2_burrow_cd > 0:
                    p2_burrow_cd -= 1

                if p2_is_burrowed:
                    p2_burrow_timer -= 1
                    if p2_burrow_timer <= 0:
                        dest = random.choice(burrow_holes)
                        p2_x = dest[0] - 40
                        p2_y = dest[1] - 25
                        p2_is_burrowed = False
                        SFX.snd_burrow.play()
                else:
                    p2_pad_x = ps_pad_p2.get_axis(0) if ps_pad_p2 and abs(ps_pad_p2.get_axis(0)) > 0.15 else 0.0
                    p2_pad_y = ps_pad_p2.get_axis(1) if ps_pad_p2 and abs(ps_pad_p2.get_axis(1)) > 0.15 else 0.0

                    p2_vx, p2_vy = 0.0, 0.0
                    if keys[pygame.K_LEFT] or keys[pygame.K_KP4] or p2_pad_x < -0.3:
                        p2_vx -= p2_speed
                    if keys[pygame.K_RIGHT] or keys[pygame.K_KP6] or p2_pad_x > 0.3:
                        p2_vx += p2_speed
                    if keys[pygame.K_UP] or keys[pygame.K_KP8] or p2_pad_y < -0.3:
                        p2_vy -= p2_speed
                    if keys[pygame.K_DOWN] or keys[pygame.K_KP5] or keys[pygame.K_KP2] or p2_pad_y > 0.3:
                        p2_vy += p2_speed

                    if keys[pygame.K_RCTRL] or keys[pygame.K_KP_PERIOD] or (ps_pad_p2 and ps_pad_p2.get_button(5)):
                        p2_vx *= 1.6
                        p2_vy *= 1.6

                    p2_x += p2_vx
                    p2_y += p2_vy
                    p2_x = max(10, min(SCREEN_WIDTH - 90, p2_x))
                    p2_y = max(55, min(SCREEN_HEIGHT - 70, p2_y))

                    aim_target_x = center_p1_x
                    aim_target_y = center_p1_y
                    p1_decoys_active = [d for d in active_decoys if d["type"] == "p1"]
                    if len(p1_decoys_active) > 0:
                        aim_target_x = p1_decoys_active[0]["x"] + 36
                        aim_target_y = p1_decoys_active[0]["y"] + 30

                    p2_dx = aim_target_x - center_p2_x
                    p2_dy = aim_target_y - center_p2_y
                    p2_angle = math.degrees(math.atan2(p2_dy, p2_dx))

                    p2_current_wpn = WEAPON_TIERS[p2_power_tier]
                    p2_pad_shoot = ps_pad_p2 and (ps_pad_p2.get_button(0) or ps_pad_p2.get_button(7))
                    p2_is_firing = (keys[pygame.K_KP0] or keys[pygame.K_RSHIFT] or p2_pad_shoot)

                    # P2 Laser Ray (Tiers 3-5)
                    if p2_current_wpn["type"] == "laser" and p2_is_firing:
                        p2_laser_active = True
                        rad = math.radians(p2_angle)
                        p2_laser_end_x = center_p2_x + math.cos(rad) * 900
                        p2_laser_end_y = center_p2_y + math.sin(rad) * 900

                        p2_dmg_box = pygame.Rect(min(center_p2_x, p2_laser_end_x), min(center_p2_y, p2_laser_end_y),
                                                 abs(p2_laser_end_x - center_p2_x) + 10, abs(p2_laser_end_y - center_p2_y) + 10)

                        p1_hitbox = pygame.Rect(p1_x + 15, p1_y + 10, 70, 60)
                        if p1_guard and math.hypot(center_p2_x - center_p1_x, center_p2_y - center_p1_y) < 220:
                            SFX.snd_shield.play()
                        elif p1_hitbox.colliderect(p2_dmg_box) and p1_hp > 0:
                            p1_hp = max(0, p1_hp - p2_current_wpn["dmg"])
                            p2_power_charge += 0.8
                            if random.random() < 0.3:
                                hit_sparks.append([center_p1_x, center_p1_y, random.uniform(-4, 4), random.uniform(-4, 4), 3, (0, 210, 255), 12])

                        if p2_power_charge >= 100.0 and p2_power_tier < 5:
                            p2_power_charge = 0.0
                            p2_power_tier += 1
                            floating_texts.append([f"P2 LASER TIER {p2_power_tier}!", center_p2_x - 40, center_p2_y - 30, (0, 240, 255), 40])

                    # P2 Bullets (Tiers 1-2)
                    elif p2_current_wpn["type"] == "bullet":
                        if p2_shoot_cd > 0:
                            p2_shoot_cd -= 1
                        if p2_is_firing and p2_shoot_cd == 0:
                            rad = math.radians(p2_angle)
                            p2_bullets.append({
                                "x": center_p2_x, "y": center_p2_y,
                                "vx": math.cos(rad) * p2_current_wpn["speed"],
                                "vy": math.sin(rad) * p2_current_wpn["speed"],
                                "radius": 5 + p2_power_tier,
                                "dmg": p2_current_wpn["dmg"],
                            })
                            SFX.snd_v_shoot.play()
                            p2_shoot_cd = 12

            if p2_flash_timer > 0:
                p2_flash_timer -= 1

            for b in p2_bullets[:]:
                b["x"] += b["vx"]
                b["y"] += b["vy"]
                if b["x"] < 0 or b["x"] > SCREEN_WIDTH or b["y"] < 0 or b["y"] > SCREEN_HEIGHT:
                    p2_bullets.remove(b)

            p1_hitbox = pygame.Rect(p1_x + 15, p1_y + 10, 70, 60)
            p2_hitbox = pygame.Rect(p2_x + 10, p2_y + 10, 70, 45)

            for b in p2_bullets[:]:
                b_rect = pygame.Rect(b["x"] - 5, b["y"] - 5, 10, 10)
                if p1_guard and math.hypot(b["x"] - center_p1_x, b["y"] - center_p1_y) < 58:
                    p2_bullets.remove(b)
                    SFX.snd_shield.play()
                elif p1_hitbox.colliderect(b_rect) and p1_hp > 0:
                    p1_hp = max(0, p1_hp - b["dmg"])
                    p2_bullets.remove(b)
                    SFX.snd_hit.play()
                    p2_power_charge += 14.0
                    if p2_power_charge >= 100.0 and p2_power_tier < 5:
                        p2_power_charge = 0.0
                        p2_power_tier += 1

            for b in p1_bullets[:]:
                b_rect = pygame.Rect(b["x"] - 6, b["y"] - 6, 12, 12)
                if not p2_is_burrowed and p2_hitbox.colliderect(b_rect) and p2_hp > 0:
                    p2_hp = max(0, p2_hp - b["dmg"])
                    p2_flash_timer = 3
                    p1_bullets.remove(b)
                    SFX.snd_hit.play()
                    p1_power_charge += 14.0
                    if p1_power_charge >= 100.0 and p1_power_tier < 5:
                        p1_power_charge = 0.0
                        p1_power_tier += 1

            if p1_hp <= 0:
                p2_wins += 1
                handle_round_conclusion("P2", "DUEL")
            elif p2_hp <= 0:
                p1_wins += 1
                handle_round_conclusion("P1", "DUEL")

        # Update Projectiles
        for b in p1_bullets[:]:
            b["x"] += b["vx"]
            b["y"] += b["vy"]
            if b["x"] < 0 or b["x"] > SCREEN_WIDTH or b["y"] < 0 or b["y"] > SCREEN_HEIGHT:
                p1_bullets.remove(b)

        # Draw Projectiles
        for b in p1_bullets:
            pygame.draw.circle(screen, b["color_outer"], (int(b["x"]), int(b["y"])), b["radius"])
            pygame.draw.circle(screen, b["color_core"], (int(b["x"]), int(b["y"])), max(2, b["radius"] - 3))

        for b in (enemy_bullets if game_state == "CAMPAIGN" else p2_bullets):
            color = b["color"] if "color" in b else (0, 210, 255)
            r = b["radius"] if "radius" in b else 6
            pygame.draw.circle(screen, color, (int(b["x"]), int(b["y"])), r)
            pygame.draw.circle(screen, (255, 255, 255), (int(b["x"]), int(b["y"])), max(2, r - 3))

        # ==================== DRAW CYBER LASER BEAMS ====================
        if p1_laser_active:
            wpn = WEAPON_TIERS[p1_power_tier]
            # Outer aura beam
            pygame.draw.line(screen, wpn["color_outer"], (center_p1_x, center_p1_y), (p1_laser_end_x, p1_laser_end_y), wpn["beam_w"] + 6)
            # Core high-voltage beam
            pygame.draw.line(screen, wpn["color_core"], (center_p1_x, center_p1_y), (p1_laser_end_x, p1_laser_end_y), wpn["beam_w"])
            # Spark ring at weapon muzzle
            pygame.draw.circle(screen, wpn["color_core"], (int(center_p1_x), int(center_p1_y)), wpn["beam_w"] + 4)

        if p2_laser_active:
            wpn = WEAPON_TIERS[p2_power_tier]
            pygame.draw.line(screen, wpn["color_outer"], (center_p2_x, center_p2_y), (p2_laser_end_x, p2_laser_end_y), wpn["beam_w"] + 6)
            pygame.draw.line(screen, (255, 255, 255), (center_p2_x, center_p2_y), (p2_laser_end_x, p2_laser_end_y), wpn["beam_w"])
            pygame.draw.circle(screen, wpn["color_core"], (int(center_p2_x), int(center_p2_y)), wpn["beam_w"] + 4)

        for dec in active_decoys:
            alpha = 130 + int(math.sin(dec["life"] * 0.2) * 50)
            if dec["type"] == "p1":
                h_surf = pygame.transform.scale(create_squirrel_sprite(True, (0, 240, 255), alpha=alpha), (72 * scale, 60 * scale))
                screen.blit(h_surf, (dec["x"], dec["y"]))
                pygame.draw.circle(screen, (0, 240, 255), (int(dec["x"] + 36), int(dec["y"] + 30)), 45, 1)
            else:
                v_h_raw = pygame.transform.scale(create_viper_sprite(is_boss=False, flash_white=False, alpha=alpha), (84 * 1.9, 54 * 1.9))
                screen.blit(v_h_raw, (dec["x"], dec["y"]))
                pygame.draw.circle(screen, (200, 100, 255), (int(dec["x"] + 40), int(dec["y"] + 25)), 45, 1)

        for spark in hit_sparks[:]:
            spark[0] += spark[2]
            spark[1] += spark[3]
            spark[6] -= 1
            if spark[6] <= 0:
                hit_sparks.remove(spark)
            else:
                pygame.draw.circle(screen, spark[5], (int(spark[0]), int(spark[1])), spark[4])

        for ft in floating_texts[:]:
            ft[2] -= 1.2
            ft[4] -= 1
            if ft[4] <= 0:
                floating_texts.remove(ft)
            else:
                screen.blit(font.render(ft[0], True, ft[3]), (int(ft[1]), int(ft[2])))

        # Draw Player 1
        s_surf = pygame.transform.scale(create_squirrel_sprite(p1_guard, WEAPON_TIERS[p1_power_tier]["color_outer"]), (72 * scale, 60 * scale))
        if p1_hp > 0:
            screen.blit(s_surf, (p1_x, p1_y))
            if p1_guard:
                pygame.draw.circle(screen, (0, 220, 255), (int(center_p1_x), int(center_p1_y)), 52, 3)

            p1_aim = p1_aim_angle if 'p1_aim_angle' in locals() else 0.0
            pygame.draw.line(screen, WEAPON_TIERS[p1_power_tier]["color_outer"], (center_p1_x, center_p1_y),
                             (center_p1_x + math.cos(p1_aim) * 35, center_p1_y + math.sin(p1_aim) * 35), 3)

        # Draw Player 2 or Campaign Enemies
        if game_state == "CAMPAIGN":
            for e in campaign_enemies:
                e.draw(screen)
        elif game_state == "DUEL" and p2_hp > 0:
            if not p2_is_burrowed:
                v_raw = pygame.transform.scale(create_viper_sprite(flash_white=(p2_flash_timer > 0)), (84 * 1.9, 54 * 1.9))
                v_rot = pygame.transform.rotate(v_raw, -p2_angle)
                v_rect = v_rot.get_rect(center=(center_p2_x, center_p2_y))
                screen.blit(v_rot, v_rect.topleft)
            else:
                screen.blit(font.render("[UNDERGROUND]", True, (200, 100, 255)), (center_p2_x - 45, center_p2_y - 30))

        if not ps_pad_p1:
            pygame.draw.circle(screen, WEAPON_TIERS[p1_power_tier]["color_outer"], mouse_pos, 8, 2)
            pygame.draw.circle(screen, (255, 255, 255), mouse_pos, 2)

        # ======================================================================
        # DIGITAL NUMERIC HUD
        # ======================================================================
        p1_col = (255, 140, 0) if p1_hp > 50 else (255, 60, 60)
        p1_title = "P1: S.Q.U.I.R.E.L. (3X POWER)" if game_state == "CAMPAIGN" else "P1: S.Q.U.I.R.E.L."
        screen.blit(font.render(p1_title, True, (255, 180, 80)), (20, 12))
        screen.blit(num_font.render(f"HP: {int(p1_hp)} / {p1_max_hp}", True, p1_col), (20, 30))
        wpn_desc = f"PWR TIER {p1_power_tier}: {WEAPON_TIERS[p1_power_tier]['name']}"
        screen.blit(font.render(wpn_desc, True, WEAPON_TIERS[p1_power_tier]["color_outer"]), (20, 56))

        if game_state == "CAMPAIGN":
            lvl_txt = f"LEVEL {current_level} / {max_levels}"
            screen.blit(font.render(lvl_txt, True, (255, 230, 100)), (SCREEN_WIDTH // 2 - 60, 12))
            screen.blit(font.render(f"SCORE: {total_score}", True, (200, 210, 240)), (SCREEN_WIDTH - 150, 12))

        elif game_state == "DUEL":
            p2_col = (0, 210, 255) if p2_hp > 35 else (255, 60, 60)
            p2_head = font.render("P2: V.I.P.E.R. DRONE", True, (0, 210, 255))
            p2_num = num_font.render(f"HP: {int(p2_hp)} / {p2_max_hp}", True, p2_col)
            p2_wpn_desc = f"TIER {p2_power_tier}: {WEAPON_TIERS[p2_power_tier]['name']}"
            p2_sub = font.render(f"{p2_wpn_desc} | WINS: {p2_wins}", True, (200, 210, 230))
            screen.blit(p2_head, (SCREEN_WIDTH - p2_head.get_width() - 20, 12))
            screen.blit(p2_num, (SCREEN_WIDTH - p2_num.get_width() - 20, 30))
            screen.blit(p2_sub, (SCREEN_WIDTH - p2_sub.get_width() - 20, 56))

        pygame.display.flip()
        clock.tick(60)
        await asyncio.sleep(0)

    pygame.quit()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass