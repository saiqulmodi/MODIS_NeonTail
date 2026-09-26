import array
import asyncio
import json
import math
from pathlib import Path
import random
from collections import deque
import pygame

pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
pygame.joystick.init()
joysticks = [pygame.joystick.Joystick(i) for i in range(pygame.joystick.get_count())]

sprite_dir = Path("assets/sprites")
sprite_dir.mkdir(parents=True, exist_ok=True)
SAVE_FILE = Path("save.json")

# ==============================================================================
# PERSISTENT SAVE SYSTEM
# ==============================================================================
def load_save_data() -> dict:
    if SAVE_FILE.exists():
        try:
            with open(SAVE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"high_score": 0, "max_level_reached": 1, "total_drones_destroyed": 0, "unlocked_tier": 1}

def update_save_data(score: int, level: int, kills_added: int = 0, tier: int = 1):
    data = load_save_data()
    updated = False
    if score > data.get("high_score", 0):
        data["high_score"] = score
        updated = True
    if level > data.get("max_level_reached", 1):
        data["max_level_reached"] = min(10, level)
        updated = True
    if tier > data.get("unlocked_tier", 1):
        data["unlocked_tier"] = tier
        updated = True
    if kills_added > 0:
        data["total_drones_destroyed"] = data.get("total_drones_destroyed", 0) + kills_added
        updated = True
    if updated:
        try:
            with open(SAVE_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

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
        self.snd_laser = self.create_tone(950, 1200, 0.05, "sine", volume=0.15)
        self.snd_hit = self.create_tone(1100, 350, 0.06, "sine", volume=0.3)
        self.snd_explode = self.create_tone(160, 40, 0.35, "noise", volume=0.45)
        self.snd_shield = self.create_tone(400, 800, 0.15, "sine", volume=0.35)
        self.snd_heal = self.create_tone(523, 1046, 0.22, "sine", volume=0.35)
        self.snd_decoy = self.create_tone(600, 1200, 0.2, "sine", volume=0.35)
        self.snd_burrow = self.create_tone(280, 90, 0.28, "square", volume=0.3)
        self.snd_win = self.create_tone(440, 880, 0.35, "sine", volume=0.4)
        self.snd_split = self.create_tone(350, 1050, 0.3, "sine", volume=0.4)
        self.snd_bomb = self.create_tone(120, 30, 0.45, "noise", volume=0.55)
        self.snd_cluster = self.create_tone(600, 150, 0.18, "noise", volume=0.35)
        self.snd_armor = self.create_tone(700, 400, 0.12, "square", volume=0.35)
        self.snd_surge = self.create_tone(300, 900, 0.14, "sine", volume=0.3)

SFX = RetroSoundEngine()

DANCE_STYLES = ["HELICOPTER", "DISCO", "JELLY", "MOONWALK", "SOMERSAULT"]

# ==============================================================================
# DEFENSIVE BUNKERS & FORTIFIED WALLS
# ==============================================================================
class BarricadeWall:
    def __init__(self, rect: pygame.Rect, max_hp: int = 240):
        self.rect = rect
        self.max_hp = max_hp
        self.hp = max_hp

    @property
    def is_destroyed(self) -> bool:
        return self.hp <= 0

    def draw(self, surface):
        if self.is_destroyed:
            return
        ratio = max(0.0, self.hp / self.max_hp)
        color = (int(40 + 160 * (1 - ratio)), int(180 * ratio), int(220 * ratio))
        pygame.draw.rect(surface, (20, 26, 42), self.rect, border_radius=4)
        pygame.draw.rect(surface, color, self.rect, width=2, border_radius=4)

class BunkerRoom:
    def __init__(self, rect: pygame.Rect):
        self.rect = rect
        door_w = 48
        mid_x = rect.x + rect.width // 2
        self.walls = [
            pygame.Rect(rect.x, rect.y, (rect.width - door_w) // 2, 6),
            pygame.Rect(mid_x + door_w // 2, rect.y, (rect.width - door_w) // 2, 6),
            pygame.Rect(rect.x, rect.bottom - 6, (rect.width - door_w) // 2, 6),
            pygame.Rect(mid_x + door_w // 2, rect.bottom - 6, (rect.width - door_w) // 2, 6),
            pygame.Rect(rect.x, rect.y, 6, rect.height),
            pygame.Rect(rect.right - 6, rect.y, 6, rect.height),
        ]

    def contains(self, px: float, py: float) -> bool:
        return self.rect.collidepoint(px, py)

    def draw(self, surface, is_boss_level: bool = False):
        safe_surf = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        glow_col = (255, 50, 100, 30) if is_boss_level else (0, 200, 255, 20)
        safe_surf.fill(glow_col)
        surface.blit(safe_surf, self.rect.topleft)

        accent = (255, 60, 90) if is_boss_level else (0, 210, 255)
        for w in self.walls:
            pygame.draw.rect(surface, (40, 50, 75), w, border_radius=2)
            pygame.draw.rect(surface, accent, w, width=2, border_radius=2)

# ==============================================================================
# SPRITE GENERATION (HALF SIZE BODY, GROWING NEON TAIL)
# ==============================================================================
def create_squirrel_sprite(tail_scale: float = 0.0, tail_flag: bool = False, aura_color=None, alpha: int = 255) -> pygame.Surface:
    surf = pygame.Surface((120, 70), pygame.SRCALPHA)
    t_col = aura_color if aura_color else (255, 140, 0)
    
    # Squirrel Tail: Peak at level 10 is double the body size (~56x44 px)
    if tail_scale > 0.02:
        tw = int(56 * tail_scale)
        th = int(44 * tail_scale)
        tx = int(60 - tw)
        ty = int(35 - th // 2)
        pygame.draw.ellipse(surf, (*t_col, min(255, alpha)), (tx, ty, tw, th))
        if tw > 12 and th > 12:
            pygame.draw.ellipse(surf, (255, 215, 60, min(255, alpha)), (tx + 4, ty + 4, max(4, tw - 8), max(4, th - 8)))
            pygame.draw.ellipse(surf, (255, 255, 200, min(255, alpha)), (tx + 8, ty + 8, max(2, tw - 16), max(2, th - 16)))
        if tail_flag:
            pygame.draw.ellipse(surf, (0, 240, 255, 200), (tx - 2, ty - 2, tw + 4, th + 4), width=2)

    # Squirrel Body: Half size (~28x22 px) centered at x=60, y=24
    body_fur = (195, 85, 20)
    pygame.draw.ellipse(surf, (*body_fur, alpha), (60, 24, 28, 22))
    pygame.draw.ellipse(surf, (245, 205, 150, alpha), (68, 27, 14, 15))
    pygame.draw.circle(surf, (*body_fur, alpha), (85, 29), 9)
    pygame.draw.polygon(surf, (*body_fur, alpha), [(81, 21), (85, 14), (89, 21)])
    pygame.draw.ellipse(surf, (0, 240, 255, alpha), (85, 27, 6, 4))
    pygame.draw.circle(surf, (255, 255, 255, alpha), (87, 28), 1)

    return surf

def create_viper_head(is_boss: bool = False, flash_white: bool = False, alpha: int = 255) -> pygame.Surface:
    """Clear, high-visibility cyber snake head oriented pointing RIGHT (0 degrees)."""
    surf = pygame.Surface((58, 42), pygame.SRCALPHA)
    accent = (255, 255, 255) if flash_white else ((255, 45, 85) if is_boss else (0, 230, 255))
    core_dark = (240, 240, 255) if flash_white else ((80, 25, 40) if is_boss else (30, 48, 75))
    core_light = (255, 255, 255) if flash_white else ((120, 35, 55) if is_boss else (55, 85, 125))

    # Flared Cobra Hood / Crest
    pygame.draw.polygon(surf, (*core_dark, alpha), [(4, 21), (20, 4), (36, 12), (54, 21), (36, 30), (20, 38)])
    pygame.draw.polygon(surf, (*core_light, alpha), [(14, 21), (24, 10), (38, 16), (50, 21), (38, 26), (24, 32)])
    pygame.draw.polygon(surf, (*accent, alpha), [(4, 21), (20, 4), (36, 12), (54, 21), (36, 30), (20, 38)], width=2)

    # Dual Glowing Sensor Eyes
    eye_col = (255, 255, 255) if flash_white else ((255, 230, 80) if is_boss else (0, 255, 200))
    pygame.draw.circle(surf, (*eye_col, alpha), (36, 14), 4)
    pygame.draw.circle(surf, (*eye_col, alpha), (36, 28), 4)
    pygame.draw.circle(surf, (255, 255, 255, alpha), (38, 14), 2)
    pygame.draw.circle(surf, (255, 255, 255, alpha), (38, 28), 2)

    # Snout Cannon / Fang Emitter
    pygame.draw.polygon(surf, (*accent, alpha), [(46, 19), (56, 21), (46, 23)])

    return surf

# ==============================================================================
# ORDNANCE / BOMB SYSTEM
# ==============================================================================
class Ordnance:
    def __init__(self, x: float, y: float, kind: str = "BOMB", vx: float = 0.0, vy: float = 0.0):
        self.x = x
        self.y = y
        self.kind = kind
        self.vx = vx
        self.vy = vy
        if kind == "BOMB":
            self.timer = 45
            self.radius = 6
            self.color = (255, 80, 0)
        elif kind == "CLUSTER":
            self.timer = 35
            self.radius = 8
            self.color = (255, 210, 0)
        elif kind == "SUBMUNITION":
            self.timer = random.randint(20, 32)
            self.radius = 4
            self.color = (255, 140, 50)
        else:
            self.timer = 50
            self.armed = False
            self.radius = 6
            self.color = (0, 240, 255)

    def update(self) -> bool:
        self.x += self.vx
        self.y += self.vy
        self.vx *= 0.93
        self.vy *= 0.93

        if self.kind == "AMBUSH_MINE":
            if self.timer > 0:
                self.timer -= 1
                if self.timer == 0:
                    self.armed = True
            return False

        self.timer -= 1
        return self.timer <= 0

    def draw(self, surface):
        ix, iy = int(self.x), int(self.y)
        if self.kind == "AMBUSH_MINE":
            alpha_col = (0, 240, 255) if self.armed else (120, 120, 140)
            pygame.draw.circle(surface, alpha_col, (ix, iy), self.radius, 2)
        else:
            pygame.draw.circle(surface, self.color, (ix, iy), self.radius)
            pygame.draw.circle(surface, (255, 255, 255), (ix, iy), max(2, self.radius - 3))

# ==============================================================================
# AI ENEMY CLASS (SNAKE LENGTH: 10X AT L1 TO 20X AT L10, THEN FIXED)
# ==============================================================================
class ViperEnemy:
    def __init__(self, level: int, is_boss: bool = False, is_minion: bool = False, speed: float = 5.0):
        self.level = level
        self.is_boss = is_boss
        self.is_minion = is_minion
        
        # Viper length: 10x squirrel body (18 segs) at L1 -> doubles to 20x (36 segs) at L10
        prog = min(1.0, (level - 1) / 9.0)
        self.max_segments = int(18 + (18 * prog))

        self.head_normal = create_viper_head(is_boss=is_boss, flash_white=False)
        self.head_flash = create_viper_head(is_boss=is_boss, flash_white=True)

        self.x = random.uniform(480, 720)
        self.y = random.uniform(90, 500)
        
        base_hp = 380 if is_boss else (45 if is_minion else 80)
        hp_growth = 40 if is_boss else 16
        self.max_hp = base_hp + (level * hp_growth)
        self.hp = self.max_hp
        self.speed_stat = speed * (1.15 if is_minion else 0.95)
        self.angle = 180.0
        self.wave_phase = random.uniform(0, 6.28)
        self.is_burrowed = False
        self.burrow_timer = 0
        self.burrow_cooldown = random.randint(180, 360)
        self.cooldown_max = max(12, (32 if is_boss else 44) - int(level * 1.5))
        self.shoot_timer = random.randint(0, self.cooldown_max)
        self.flash_timer = 0

        self.history = deque(maxlen=self.max_segments * 3 + 8)
        for _ in range(self.history.maxlen):
            self.history.append((self.x, self.y, self.angle))

        self.has_camo = (level >= 2)
        self.has_acid = (level >= 4)
        self.has_split = (level >= 7 and not is_minion and not is_boss)
        self.has_homing = (level >= 9 or is_boss)
        self.camo_alpha = 255
        self.acid_drop_timer = 0

    @property
    def core_rect(self):
        return pygame.Rect(self.x - 18, self.y - 18, 36, 36)

    def get_tail_segments(self):
        points = []
        if self.is_burrowed:
            return points
        step = 3
        for i in range(2, self.max_segments + 2):
            idx = i * step
            if idx < len(self.history):
                points.append(self.history[idx])
        return points

    def update(self, holes, target_x, target_y, screen_w, screen_h, acid_pools):
        if self.flash_timer > 0:
            self.flash_timer -= 1

        self.wave_phase += 0.16

        if self.has_camo:
            dist = math.hypot(target_x - self.x, target_y - self.y)
            if dist > 170:
                self.camo_alpha = max(70, self.camo_alpha - 5)
            else:
                self.camo_alpha = min(255, self.camo_alpha + 15)
        else:
            self.camo_alpha = 255

        if self.has_acid and not self.is_burrowed:
            self.acid_drop_timer += 1
            if self.acid_drop_timer >= 45:
                self.acid_drop_timer = 0
                acid_pools.append({"x": self.x, "y": self.y, "life": 160, "radius": 14})

        if self.is_burrowed:
            self.burrow_timer -= 1
            if self.burrow_timer <= 0:
                dest = random.choice(holes)
                self.x = dest[0]
                self.y = dest[1]
                self.is_burrowed = False
                self.burrow_cooldown = random.randint(200, 380)
                self.history.clear()
                for _ in range(self.history.maxlen):
                    self.history.append((self.x, self.y, self.angle))
                SFX.snd_burrow.play()
            return None

        if self.burrow_cooldown > 0:
            self.burrow_cooldown -= 1
        elif len(holes) > 0 and (self.hp < self.max_hp * 0.5 or random.random() < 0.007):
            nearest = min(holes, key=lambda h: math.hypot(h[0] - self.x, h[1] - self.y))
            dist = math.hypot(nearest[0] - self.x, nearest[1] - self.y)
            if dist < 24:
                self.is_burrowed = True
                self.burrow_timer = 90
                SFX.snd_burrow.play()
                return None
            else:
                angle = math.atan2(nearest[1] - self.y, nearest[0] - self.x)
                self.x += math.cos(angle) * self.speed_stat
                self.y += math.sin(angle) * self.speed_stat
                self.angle = math.degrees(angle)

        if not self.is_burrowed:
            dx, dy = target_x - self.x, target_y - self.y
            dist = math.hypot(dx, dy)
            target_angle = math.atan2(dy, dx)

            perp_angle = target_angle + math.pi / 2
            wave_amp = 2.4 * math.sin(self.wave_phase)

            if dist > 190:
                vx = math.cos(target_angle) * (self.speed_stat * 0.95) + math.cos(perp_angle) * wave_amp
                vy = math.sin(target_angle) * (self.speed_stat * 0.95) + math.sin(perp_angle) * wave_amp
            elif dist < 110:
                vx = -math.cos(target_angle) * (self.speed_stat * 0.85) + math.cos(perp_angle) * wave_amp
                vy = -math.sin(target_angle) * (self.speed_stat * 0.85) + math.sin(perp_angle) * wave_amp
            else:
                vx = -math.sin(target_angle) * (self.speed_stat * 0.9) + math.cos(perp_angle) * wave_amp
                vy = math.cos(target_angle) * (self.speed_stat * 0.9) + math.sin(perp_angle) * wave_amp

            self.x += vx
            self.y += vy
            self.angle = math.degrees(math.atan2(vy, vx))
            self.x = max(25, min(screen_w - 70, self.x))
            self.y = max(55, min(screen_h - 60, self.y))

        self.history.appendleft((self.x, self.y, self.angle))

        self.shoot_timer += 1
        if self.shoot_timer >= self.cooldown_max and not self.is_burrowed:
            self.shoot_timer = 0
            b_angle = math.atan2(target_y - self.y, target_x - self.x)
            shots = []
            bullet_col = (255, 60, 90) if self.is_boss else ((140, 255, 50) if self.has_acid else (0, 220, 255))
            shots.append({
                "x": self.x,
                "y": self.y,
                "vx": math.cos(b_angle) * 7.5,
                "vy": math.sin(b_angle) * 7.5,
                "color": bullet_col,
                "dmg": 24 if self.is_boss else 14,
                "homing": self.has_homing,
            })
            return shots
        return None

    def draw(self, surface):
        if self.is_burrowed:
            return
        
        # 1. Articulated trailing segments
        tail_points = self.get_tail_segments()
        accent = (255, 45, 85) if self.is_boss else (0, 220, 255)
        for i, (seg_x, seg_y, _) in enumerate(tail_points):
            seg_ratio = 1.0 - (i / max(1, len(tail_points)))
            seg_r = max(3, int(11 * seg_ratio))
            alpha_val = int(self.camo_alpha * seg_ratio)
            s_surf = pygame.Surface((seg_r * 2 + 4, seg_r * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(s_surf, (25, 38, 60, alpha_val), (seg_r + 2, seg_r + 2), seg_r)
            pygame.draw.circle(s_surf, (*accent, alpha_val), (seg_r + 2, seg_r + 2), seg_r, 1)
            surface.blit(s_surf, (seg_x - seg_r - 2, seg_y - seg_r - 2))

        # 2. Glowing Head on top
        base_surf = self.head_flash if self.flash_timer > 0 else self.head_normal
        rotated = pygame.transform.rotate(base_surf, -self.angle)
        if self.camo_alpha < 255:
            rotated.set_alpha(self.camo_alpha)
        rot_rect = rotated.get_rect(center=(self.x, self.y))
        surface.blit(rotated, rot_rect.topleft)

        # 3. Reticle / Targeting Bracket
        bracket_col = (255, 70, 70) if self.is_boss else (0, 255, 230)
        bracket_r = 20
        pygame.draw.circle(surface, bracket_col, (int(self.x), int(self.y)), bracket_r, 1)
        for deg in (0, 90, 180, 270):
            rad = math.radians(deg)
            tx1 = self.x + math.cos(rad) * (bracket_r - 4)
            ty1 = self.y + math.sin(rad) * (bracket_r - 4)
            tx2 = self.x + math.cos(rad) * (bracket_r + 4)
            ty2 = self.y + math.sin(rad) * (bracket_r + 4)
            pygame.draw.line(surface, bracket_col, (tx1, ty1), (tx2, ty2), 1)

# ==============================================================================
# WEAPONS EVOLUTION MATRIX
# ==============================================================================
WEAPON_TIERS = {
    1: {"type": "bullet", "speed": 14, "color_outer": (255, 140, 0), "color_core": (255, 230, 80), "dmg": 22, "pierce": 1},
    2: {"type": "bullet", "speed": 18, "color_outer": (0, 220, 255), "color_core": (200, 255, 255), "dmg": 34, "pierce": 2},
    3: {"type": "laser",  "beam_w": 5,  "color_outer": (220, 50, 255), "color_core": (255, 200, 255), "dmg": 2.4},
    4: {"type": "laser",  "beam_w": 8,  "color_outer": (40, 255, 120), "color_core": (210, 255, 220), "dmg": 3.6},
    5: {"type": "laser",  "beam_w": 12, "color_outer": (255, 50, 120), "color_core": (255, 255, 255), "dmg": 5.2},
}

# ==============================================================================
# MAIN ASYNC LOOP
# ==============================================================================
async def main():
    global joysticks
    SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    dark_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    pygame.display.set_caption("MODIS NeonTail - Cyber Combat")
    clock = pygame.time.Clock()

    font = pygame.font.SysFont("consolas", 13, bold=True)
    num_font = pygame.font.SysFont("consolas", 20, bold=True)
    big_font = pygame.font.SysFont("consolas", 26, bold=True)
    title_font = pygame.font.SysFont("consolas", 32, bold=True)

    saved_state = load_save_data()
    game_state = "MODE_SELECT"
    prev_mode = "CAMPAIGN"
    burrow_holes = [(160, 130), (640, 130), (160, 490), (640, 490), (400, 520)]
    active_decoys = []
    current_level = 1
    total_score = 0
    drones_killed_session = 0

    bunker = BunkerRoom(pygame.Rect(340, 250, 120, 90))
    barricades = [
        BarricadeWall(pygame.Rect(250, 260, 8, 70)),
        BarricadeWall(pygame.Rect(540, 260, 8, 70)),
    ]

    break_timer = 0
    break_winner = "P1"
    active_dance = "HELICOPTER"
    fireworks = []

    BASE_SPEED = 5.2
    SPEED_INC_PER_LEVEL = 0.30

    def get_current_speed(lvl: int) -> float:
        return round(BASE_SPEED + (lvl * SPEED_INC_PER_LEVEL), 2)

    def get_max_armor(lvl: int) -> int:
        return 70 + (lvl * 12)

    def get_max_hp(lvl: int) -> int:
        return 280 + (lvl * 20)

    def get_squirrel_tail_scale(lvl: int) -> float:
        return min(1.0, max(0.0, round((lvl - 1) / 9.0, 2)))

    def get_viper_length_factor(lvl: int) -> float:
        return min(2.0, 1.0 + (min(10, lvl) - 1) / 9.0)

    p1_x, p1_y = 120.0, 280.0
    p1_speed = get_current_speed(current_level)
    p1_max_hp = get_max_hp(current_level)
    p1_hp = p1_max_hp
    p1_max_armor = get_max_armor(current_level)
    p1_armor = float(p1_max_armor)
    p1_last_hit_timer = 0
    p1_surge_timer = 0

    p1_guard = False
    p1_guard_energy = 100.0
    p1_med_kits = 6
    p1_decoys = 6
    p1_shoot_cd = 0
    p1_power_tier = saved_state.get("unlocked_tier", 1)
    p1_power_charge = 0.0

    p1_bombs = 4
    p1_clusters = 3
    p1_mines = 3

    p1_split_timer = 0
    p1_split_charges = 3

    p1_wins = 0
    p2_wins = 0

    # Player 2 Serpent Configuration
    p2_x, p2_y = 620.0, 280.0
    p2_speed = get_current_speed(current_level)
    p2_max_hp = 120 + (current_level * 10)
    p2_hp = p2_max_hp
    p2_max_armor = get_max_armor(current_level) // 2
    p2_armor = float(p2_max_armor)
    p2_last_hit_timer = 0
    p2_angle = 180.0
    p2_shoot_cd = 0
    p2_flash_timer = 0
    p2_is_burrowed = False
    p2_burrow_timer = 0
    p2_burrow_cd = 0
    p2_decoys = 3
    p2_power_tier = 1
    p2_power_charge = 0.0
    p2_head_normal = create_viper_head(is_boss=False, flash_white=False)
    p2_head_flash = create_viper_head(is_boss=False, flash_white=True)
    p2_max_segments = int(18 + (18 * min(1.0, (current_level - 1) / 9.0)))
    p2_history = deque(maxlen=p2_max_segments * 3 + 8)
    for _ in range(p2_history.maxlen):
        p2_history.append((p2_x, p2_y, p2_angle))

    def spawn_campaign_wave(lvl):
        enemies = []
        is_boss = (lvl >= 10)
        spd = get_current_speed(lvl)
        if is_boss:
            enemies.append(ViperEnemy(lvl, is_boss=True, speed=spd))
        else:
            num = min(4, 1 + (lvl // 3))
            for _ in range(num):
                enemies.append(ViperEnemy(lvl, is_boss=False, speed=spd))
        return enemies

    campaign_enemies = spawn_campaign_wave(current_level)
    p1_bullets = []
    p2_bullets = []
    enemy_bullets = []
    hit_sparks = []
    floating_texts = []
    active_ordnance = []
    shockwaves = []
    acid_pools = []
    player_trails = []

    def trigger_explosion(x: float, y: float, max_r: float, dmg: int, col=(255, 120, 0)):
        SFX.snd_bomb.play()
        shockwaves.append({"x": x, "y": y, "r": 8.0, "max_r": max_r, "col": col, "dmg": dmg})
        for _ in range(18):
            ang = random.uniform(0, 6.28)
            sp = random.uniform(2.5, 5.5)
            hit_sparks.append([x, y, math.cos(ang) * sp, math.sin(ang) * sp, 3, col, 18])

    def reset_positions():
        nonlocal p1_x, p1_y, p2_x, p2_y, p1_bullets, p2_bullets, enemy_bullets, active_decoys, p1_split_timer, p1_speed, p2_speed, active_ordnance, shockwaves, acid_pools, player_trails, p1_surge_timer, barricades, p2_max_segments, p2_history
        p1_x, p1_y = 120.0, 280.0
        p2_x, p2_y = 620.0, 280.0
        p1_speed = get_current_speed(current_level)
        p2_speed = get_current_speed(current_level)
        p1_bullets.clear()
        p2_bullets.clear()
        enemy_bullets.clear()
        active_decoys.clear()
        active_ordnance.clear()
        shockwaves.clear()
        acid_pools.clear()
        player_trails.clear()
        p1_split_timer = 0
        p1_surge_timer = 0

        p2_max_segments = int(18 + (18 * min(1.0, (current_level - 1) / 9.0)))
        p2_history = deque(maxlen=p2_max_segments * 3 + 8)
        for _ in range(p2_history.maxlen):
            p2_history.append((p2_x, p2_y, p2_angle))

        if current_level >= 10:
            barricades = [
                BarricadeWall(pygame.Rect(180, 180, 8, 80), max_hp=350),
                BarricadeWall(pygame.Rect(600, 330, 8, 80), max_hp=350),
                BarricadeWall(pygame.Rect(360, 480, 80, 8), max_hp=350),
            ]
        else:
            barricades = [
                BarricadeWall(pygame.Rect(250, 260, 8, 70)),
                BarricadeWall(pygame.Rect(540, 260, 8, 70)),
            ]

    def handle_round_conclusion(winner: str, origin_mode: str):
        nonlocal game_state, break_timer, break_winner, active_dance, prev_mode, p1_split_timer, current_level, p1_speed, p2_speed, p1_bombs, p1_clusters, p1_mines, p1_max_armor, p1_armor, p1_max_hp, p1_hp, p2_max_armor, p2_armor
        prev_mode = origin_mode
        break_winner = winner
        fireworks.clear()
        p1_split_timer = 0
        update_save_data(total_score, current_level, kills_added=drones_killed_session, tier=p1_power_tier)

        cleared_level = current_level
        current_level = min(10, current_level + 1)

        p1_speed = get_current_speed(current_level)
        p2_speed = get_current_speed(current_level)
        p1_max_armor = get_max_armor(current_level)
        p1_armor = float(p1_max_armor)
        p1_max_hp = get_max_hp(current_level)
        p1_hp = p1_max_hp

        p2_max_armor = get_max_armor(current_level) // 2
        p2_armor = float(p2_max_armor)

        p1_bombs = min(8, p1_bombs + 1)
        p1_clusters = min(5, p1_clusters + 1)
        p1_mines = min(5, p1_mines + 1)

        if cleared_level > 0 and cleared_level % 2 == 0:
            game_state = "MILESTONE_CELEBRATION"
            break_timer = 190
            active_dance = random.choice(DANCE_STYLES)
            SFX.snd_win.play()
        else:
            game_state = "NORMAL_ROUND_BREAK"
            break_timer = 25

    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()
        ps_pad_p1 = joysticks[0] if len(joysticks) > 0 else None
        ps_pad_p2 = joysticks[1] if len(joysticks) > 1 else None

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.JOYDEVICEADDED:
                joysticks = [pygame.joystick.Joystick(i) for i in range(pygame.joystick.get_count())]

            if game_state == "MODE_SELECT":
                if (event.type == pygame.KEYDOWN and event.key in (pygame.K_1, pygame.K_KP1)) or \
                   (event.type == pygame.JOYBUTTONDOWN and event.button == 0):
                    game_state = "CAMPAIGN"
                    current_level = 1
                    p1_max_hp = get_max_hp(current_level)
                    p1_hp = p1_max_hp
                    p1_max_armor = get_max_armor(current_level)
                    p1_armor = float(p1_max_armor)
                    p1_med_kits = 6
                    p1_decoys = 6
                    p1_bombs = 4
                    p1_clusters = 3
                    p1_mines = 3
                    p1_split_charges = 3
                    p1_power_charge = 0.0
                    reset_positions()
                    campaign_enemies = spawn_campaign_wave(current_level)
                    SFX.snd_win.play()
                elif (event.type == pygame.KEYDOWN and event.key in (pygame.K_2, pygame.K_KP2)) or \
                     (event.type == pygame.JOYBUTTONDOWN and event.button == 1):
                    game_state = "DUEL"
                    current_level = 1
                    p1_max_hp = 120
                    p1_hp = p1_max_hp
                    p1_max_armor = get_max_armor(current_level)
                    p1_armor = float(p1_max_armor)
                    p1_med_kits = 2
                    p1_decoys = 3
                    p1_bombs = 2
                    p1_clusters = 1
                    p1_mines = 2
                    p1_split_charges = 2
                    p1_power_charge = 0.0
                    p2_max_hp = 120
                    p2_hp = p2_max_hp
                    p2_max_armor = get_max_armor(current_level) // 2
                    p2_armor = float(p2_max_armor)
                    p2_decoys = 3
                    p2_power_tier = 1
                    p2_power_charge = 0.0
                    reset_positions()
                    SFX.snd_win.play()

            # P1 Heal
            if game_state in ("CAMPAIGN", "DUEL") and p1_med_kits > 0 and p1_hp < p1_max_hp:
                if (event.type == pygame.KEYDOWN and event.key in (pygame.K_q, pygame.K_m)) or \
                   (event.type == pygame.JOYBUTTONDOWN and ps_pad_p1 and event.joy == 0 and event.button in (1, 2, 3)):
                    heal_amt = 55 if game_state == "CAMPAIGN" else 35
                    p1_hp = min(p1_max_hp, p1_hp + heal_amt)
                    p1_med_kits -= 1
                    SFX.snd_heal.play()
                    floating_texts.append([f"+{heal_amt} HP", p1_x + 40, p1_y - 10, (100, 255, 120), 30])

            # P1 Decoys
            if game_state in ("CAMPAIGN", "DUEL") and p1_decoys > 0:
                if (event.type == pygame.KEYDOWN and event.key == pygame.K_f) or \
                   (event.type == pygame.JOYBUTTONDOWN and ps_pad_p1 and event.joy == 0 and event.button == 3):
                    p1_decoys -= 1
                    clone_count = 5
                    radius = 50
                    for i in range(clone_count):
                        angle = (2.0 * math.pi / clone_count) * i
                        cx = p1_x + math.cos(angle) * radius
                        cy = p1_y + math.sin(angle) * radius
                        active_decoys.append({"x": cx, "y": cy, "life": 220, "type": "p1"})

                    if current_level >= 3:
                        for _ in range(3):
                            c_ang = random.uniform(0, 6.28)
                            active_ordnance.append(Ordnance(p1_x + 75, p1_y + 35, kind="SUBMUNITION", vx=math.cos(c_ang) * 4.5, vy=math.sin(c_ang) * 4.5))
                    SFX.snd_decoy.play()

            # Ordnance Launchers
            if game_state in ("CAMPAIGN", "DUEL") and p1_bombs > 0:
                if (event.type == pygame.KEYDOWN and event.key == pygame.K_g) or \
                   (event.type == pygame.JOYBUTTONDOWN and ps_pad_p1 and event.joy == 0 and event.button == 2):
                    p1_bombs -= 1
                    aim = p1_aim_angle if 'p1_aim_angle' in locals() else 0.0
                    active_ordnance.append(Ordnance(p1_x + 75, p1_y + 35, kind="BOMB", vx=math.cos(aim) * 9.0, vy=math.sin(aim) * 9.0))
                    SFX.snd_shoot.play()

            if game_state in ("CAMPAIGN", "DUEL") and p1_clusters > 0:
                if (event.type == pygame.KEYDOWN and event.key == pygame.K_b) or \
                   (event.type == pygame.JOYBUTTONDOWN and ps_pad_p1 and event.joy == 0 and event.button == 9):
                    p1_clusters -= 1
                    aim = p1_aim_angle if 'p1_aim_angle' in locals() else 0.0
                    active_ordnance.append(Ordnance(p1_x + 75, p1_y + 35, kind="CLUSTER", vx=math.cos(aim) * 8.0, vy=math.sin(aim) * 8.0))
                    SFX.snd_shoot.play()

            if game_state in ("CAMPAIGN", "DUEL") and p1_mines > 0:
                if (event.type == pygame.KEYDOWN and event.key == pygame.K_v) or \
                   (event.type == pygame.JOYBUTTONDOWN and ps_pad_p1 and event.joy == 0 and event.button == 10):
                    p1_mines -= 1
                    active_ordnance.append(Ordnance(p1_x + 75, p1_y + 35, kind="AMBUSH_MINE"))
                    SFX.snd_shield.play()

            # Mitosis Split
            if game_state in ("CAMPAIGN", "DUEL") and p1_split_charges > 0 and p1_split_timer == 0:
                if (event.type == pygame.KEYDOWN and event.key == pygame.K_t) or \
                   (event.type == pygame.JOYBUTTONDOWN and ps_pad_p1 and event.joy == 0 and event.button in (8, 11)):
                    p1_split_charges -= 1
                    p1_split_timer = 400
                    SFX.snd_split.play()

            # P2 Decoys
            if game_state == "DUEL" and p2_decoys > 0:
                if (event.type == pygame.KEYDOWN and event.key in (pygame.K_KP7, pygame.K_LEFTBRACKET)) or \
                   (event.type == pygame.JOYBUTTONDOWN and ps_pad_p2 and event.joy == 1 and event.button == 4):
                    p2_decoys -= 1
                    clone_count = 4
                    radius = 50
                    for i in range(clone_count):
                        angle = (2.0 * math.pi / clone_count) * i
                        cx = p2_x + math.cos(angle) * radius
                        cy = p2_y + math.sin(angle) * radius
                        active_decoys.append({"x": cx, "y": cy, "life": 200, "type": "p2"})
                    SFX.snd_decoy.play()

            # P2 Burrow
            if game_state == "DUEL" and not p2_is_burrowed and p2_burrow_cd == 0:
                if (event.type == pygame.KEYDOWN and event.key in (pygame.K_KP_ENTER, pygame.K_SLASH)) or \
                   (event.type == pygame.JOYBUTTONDOWN and ps_pad_p2 and event.joy == 1 and event.button == 5):
                    nearest = min(burrow_holes, key=lambda h: math.hypot(h[0] - p2_x, h[1] - p2_y))
                    if math.hypot(nearest[0] - p2_x, nearest[1] - p2_y) < 70:
                        p2_is_burrowed = True
                        p2_burrow_timer = 80
                        p2_burrow_cd = 200
                        SFX.snd_burrow.play()

            if event.type == pygame.KEYDOWN and event.key == pygame.K_l and game_state in ("CAMPAIGN", "DUEL"):
                p1_power_tier = 3 if p1_power_tier < 3 else (4 if p1_power_tier == 3 else (5 if p1_power_tier == 4 else 1))
                if game_state == "DUEL":
                    p2_power_tier = p1_power_tier
                SFX.snd_win.play()

            if event.type == pygame.KEYDOWN and event.key == pygame.K_n and game_state == "CAMPAIGN":
                campaign_enemies.clear()

            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                game_state = "MODE_SELECT"

        screen.fill((10, 12, 22))
        for gx in range(0, SCREEN_WIDTH, 50):
            pygame.draw.line(screen, (20, 24, 40), (gx, 0), (gx, SCREEN_HEIGHT))
        for gy in range(0, SCREEN_HEIGHT, 50):
            pygame.draw.line(screen, (20, 24, 40), (0, gy), (SCREEN_WIDTH, gy))

        # MODE SELECT SCREEN
        if game_state == "MODE_SELECT":
            t_surf = title_font.render("MODIS NEON TAIL", True, (255, 140, 0))
            sub_surf = font.render("CHOOSE GAMEPLAY MODE", True, (0, 220, 255))
            screen.blit(t_surf, (SCREEN_WIDTH // 2 - t_surf.get_width() // 2, 45))
            screen.blit(sub_surf, (SCREEN_WIDTH // 2 - sub_surf.get_width() // 2, 88))

            card1 = pygame.Rect(55, 145, 335, 350)
            pygame.draw.rect(screen, (18, 22, 38), card1, border_radius=12)
            pygame.draw.rect(screen, (255, 140, 0), card1, 2, border_radius=12)
            screen.blit(big_font.render("1P CAMPAIGN", True, (255, 180, 80)), (75, 160))
            lines1 = [
                "Enhanced Visual Targeting:",
                "- Glowing Cyber Serpent Heads",
                "- High-Visibility Reticle Lock",
                "- Undulating Snake Body Trail",
                "- Dynamic Tail Scaling (1-10)",
                f"- High Score: {saved_state.get('high_score', 0)}",
                f"- Best Level: {saved_state.get('max_level_reached', 1)} / 10",
                "",
                ">> PRESS '1' OR CROSS (X) <<",
            ]
            y_c1 = 198
            for ln in lines1:
                col = (100, 255, 150) if ">>" in ln else ((0, 240, 255) if "Heads" in ln or "Reticle" in ln else (210, 220, 235))
                screen.blit(font.render(ln, True, col), (70, y_c1))
                y_c1 += 23

            card2 = pygame.Rect(410, 145, 335, 350)
            pygame.draw.rect(screen, (18, 22, 38), card2, border_radius=12)
            pygame.draw.rect(screen, (0, 210, 255), card2, 2, border_radius=12)
            screen.blit(big_font.render("2P DUEL (PVP)", True, (0, 220, 255)), (435, 160))
            lines2 = [
                "P1 (Squirrel) vs P2 (Cyber Snake)",
                "- P2 Now Uses Full Slithering Snake",
                "- Visible Targeting Bracket on Head",
                "- Armor & Speed scale each round",
                "- Full ordnance & decoy loadout",
                "- Milestone dance every 2 rounds",
                "",
                ">> PRESS '2' OR CIRCLE (O) <<",
            ]
            y_c2 = 198
            for ln in lines2:
                col = (100, 255, 150) if ">>" in ln else ((0, 240, 255) if "P2 Now" in ln or "Bracket" in ln else (210, 220, 235))
                screen.blit(font.render(ln, True, col), (425, y_c2))
                y_c2 += 23

            pygame.display.flip()
            clock.tick(60)
            await asyncio.sleep(0)
            continue

        # QUICK TRANSITION
        if game_state == "NORMAL_ROUND_BREAK":
            break_timer -= 1
            if break_timer <= 0:
                if prev_mode == "CAMPAIGN":
                    game_state = "CAMPAIGN"
                    if break_winner == "P1":
                        p1_hp = min(p1_max_hp, p1_hp + 40)
                    campaign_enemies = spawn_campaign_wave(current_level)
                    if current_level % 5 == 0:
                        p1_split_timer = 400
                        SFX.snd_split.play()
                else:
                    game_state = "DUEL"
                    p1_hp = p1_max_hp
                    p2_hp = p2_max_hp
                reset_positions()

            pygame.display.flip()
            clock.tick(60)
            await asyncio.sleep(0)
            continue

        # CELEBRATION (EVERY 2 LEVELS)
        if game_state == "MILESTONE_CELEBRATION":
            break_timer -= 1
            t_progress = 190 - break_timer

            if break_timer % 3 == 0:
                fx = random.randint(80, SCREEN_WIDTH - 80)
                fy = random.randint(50, 240)
                col = random.choice([(255, 215, 0), (0, 240, 255), (255, 50, 120), (50, 255, 120), (255, 140, 0)])
                for _ in range(16):
                    ang = random.uniform(0, math.pi * 2)
                    sp = random.uniform(2.5, 6.5)
                    fireworks.append({"x": fx, "y": fy, "vx": math.cos(ang) * sp, "vy": math.sin(ang) * sp, "col": col, "life": 30})

            for fw in fireworks[:]:
                fw["x"] += fw["vx"]
                fw["y"] += fw["vy"]
                fw["life"] -= 1
                if fw["life"] <= 0:
                    fireworks.remove(fw)
                else:
                    pygame.draw.circle(screen, fw["col"], (int(fw["x"]), int(fw["y"])), 3)

            center_x, center_y = 280 if break_winner == "P1" else 520, 320
            loser_x, loser_y = 520 if break_winner == "P1" else 280, 320

            sq_scale = get_squirrel_tail_scale(current_level)
            win_sprite_raw = create_squirrel_sprite(sq_scale, True, (255, 140, 0)) if break_winner == "P1" else create_viper_head(is_boss=False, flash_white=False)

            if active_dance == "HELICOPTER":
                hover_y = center_y + math.sin(t_progress * 0.15) * 18
                rot_ang = (t_progress * 24) % 360
                w_rot = pygame.transform.rotate(win_sprite_raw, rot_ang)
                screen.blit(w_rot, w_rot.get_rect(center=(center_x, hover_y)))
            elif active_dance == "DISCO":
                step_x = center_x + math.sin(t_progress * 0.25) * 30
                tilt = math.sin(t_progress * 0.25) * 16
                w_rot = pygame.transform.rotate(win_sprite_raw, tilt)
                screen.blit(w_rot, w_rot.get_rect(center=(step_x, center_y)))
            elif active_dance == "JELLY":
                squish = 1.0 + math.sin(t_progress * 0.28) * 0.25
                w = max(10, int(win_sprite_raw.get_width() * squish))
                h = max(10, int(win_sprite_raw.get_height() * (2.0 - squish)))
                w_surf = pygame.transform.scale(win_sprite_raw, (w, h))
                screen.blit(w_surf, w_surf.get_rect(center=(center_x, center_y)))
            elif active_dance == "MOONWALK":
                slide_x = center_x + ((t_progress * 2) % 120) - 60
                bob_y = center_y + abs(math.sin(t_progress * 0.2)) * -12
                w_flip = pygame.transform.flip(win_sprite_raw, True, False)
                screen.blit(w_flip, w_flip.get_rect(center=(slide_x, bob_y)))
            else:
                rot_ang = (t_progress * 14) % 360
                jump_y = center_y - abs(math.sin(t_progress * 0.12)) * 36
                w_rot = pygame.transform.rotate(win_sprite_raw, rot_ang)
                screen.blit(w_rot, w_rot.get_rect(center=(center_x, jump_y)))

            if break_winner == "P1":
                v_loser = create_viper_head(is_boss=False, flash_white=(break_timer % 10 < 5))
                screen.blit(v_loser, v_loser.get_rect(center=(loser_x, loser_y)))
            else:
                s_loser = create_squirrel_sprite(sq_scale, False, (255, 80, 80))
                screen.blit(s_loser, (loser_x - 30, loser_y - 20))

            if break_timer <= 0:
                if prev_mode == "CAMPAIGN":
                    game_state = "CAMPAIGN"
                    p1_hp = min(p1_max_hp, p1_hp + 50)
                    campaign_enemies = spawn_campaign_wave(current_level)
                    if current_level % 5 == 0:
                        p1_split_timer = 400
                        SFX.snd_split.play()
                else:
                    game_state = "DUEL"
                    p1_hp = p1_max_hp
                    p2_hp = p2_max_hp
                reset_positions()

            pygame.display.flip()
            clock.tick(60)
            await asyncio.sleep(0)
            continue

        for hole in burrow_holes:
            pygame.draw.circle(screen, (35, 10, 50), hole, 20)
            pygame.draw.circle(screen, (160, 40, 255), hole, 20, 2)
            pygame.draw.circle(screen, (10, 5, 20), hole, 12)

        bunker.draw(screen, is_boss_level=(current_level >= 10))
        for b_wall in barricades:
            b_wall.draw(screen)

        for pool in acid_pools[:]:
            pool["life"] -= 1
            if pool["life"] <= 0:
                acid_pools.remove(pool)
            else:
                p_surf = pygame.Surface((pool["radius"] * 2, pool["radius"] * 2), pygame.SRCALPHA)
                alpha = min(180, pool["life"] * 2)
                pygame.draw.circle(p_surf, (140, 255, 40, alpha), (pool["radius"], pool["radius"]), pool["radius"])
                screen.blit(p_surf, (pool["x"] - pool["radius"], pool["y"] - pool["radius"]))

        for pt in player_trails[:]:
            pt["life"] -= 1
            if pt["life"] <= 0:
                player_trails.remove(pt)
            else:
                for b in enemy_bullets[:]:
                    if math.hypot(b["x"] - pt["x"], b["y"] - pt["y"]) < 12:
                        enemy_bullets.remove(b)
                        SFX.snd_hit.play()
                pygame.draw.circle(screen, (0, 240, 255), (int(pt["x"]), int(pt["y"])), 3)

        keys = pygame.key.get_pressed()
        mouse_buttons = pygame.mouse.get_pressed()

        p1_sq_tail_scale = get_squirrel_tail_scale(current_level)

        center_p1_x = p1_x + 74
        center_p1_y = p1_y + 35
        p1_laser_active = False
        p2_laser_active = False

        p1_micro_rect = pygame.Rect(p1_x + 60, p1_y + 24, 28, 22)
        if p1_sq_tail_scale > 0.03:
            tw = int(58 * p1_sq_tail_scale)
            th = int(46 * p1_sq_tail_scale)
            p1_tail_rect = pygame.Rect(p1_x + (62 - tw), p1_y + (37 - th // 2), tw, th)
        else:
            p1_tail_rect = pygame.Rect(0, 0, 0, 0)

        if p1_surge_timer > 0:
            p1_surge_timer -= 1

        in_bunker_p1 = bunker.contains(center_p1_x, center_p1_y)
        if in_bunker_p1:
            p1_guard_energy = min(100.0, p1_guard_energy + 0.4)
            p1_hp = min(p1_max_hp, p1_hp + 0.06)

        p1_last_hit_timer += 1
        regen_rate = 0.28 if in_bunker_p1 else 0.14
        if p1_last_hit_timer > 180 and p1_armor < p1_max_armor:
            p1_armor = min(p1_max_armor, p1_armor + regen_rate)

        for pool in acid_pools:
            if math.hypot(center_p1_x - pool["x"], center_p1_y - pool["y"]) < pool["radius"] + 10:
                if p1_armor > 0:
                    p1_armor = max(0.0, p1_armor - 0.35)
                else:
                    p1_hp = max(0.0, p1_hp - 0.35)

        if game_state == "DUEL":
            center_p2_x = p2_x
            center_p2_y = p2_y
            p2_micro_rect = pygame.Rect(p2_x - 18, p2_y - 18, 36, 36)

            in_bunker_p2 = bunker.contains(center_p2_x, center_p2_y)
            p2_last_hit_timer += 1
            if in_bunker_p2:
                p2_hp = min(p2_max_hp, p2_hp + 0.06)
            regen_rate_p2 = 0.28 if in_bunker_p2 else 0.14
            if p2_last_hit_timer > 180 and p2_armor < p2_max_armor:
                p2_armor = min(p2_max_armor, p2_armor + regen_rate_p2)

        if p1_split_timer > 0:
            p1_split_timer -= 1

        for dec in active_decoys[:]:
            dec["life"] -= 1
            if dec["life"] <= 0:
                active_decoys.remove(dec)

        # PLAYER 1 CONTROLS
        if p1_hp > 0:
            speed_mult = 1.35 if p1_surge_timer > 0 else 1.0
            actual_p1_speed = p1_speed * speed_mult

            pad_x = ps_pad_p1.get_axis(0) if ps_pad_p1 and abs(ps_pad_p1.get_axis(0)) > 0.15 else 0.0
            pad_y = ps_pad_p1.get_axis(1) if ps_pad_p1 and abs(ps_pad_p1.get_axis(1)) > 0.15 else 0.0

            dx, dy = 0.0, 0.0
            if keys[pygame.K_a] or pad_x < -0.3:
                dx -= actual_p1_speed
            if keys[pygame.K_d] or pad_x > 0.3:
                dx += actual_p1_speed
            if keys[pygame.K_w] or pad_y < -0.3:
                dy -= actual_p1_speed
            if keys[pygame.K_s] or pad_y > 0.3:
                dy += actual_p1_speed

            if (dx != 0 or dy != 0) and current_level >= 2:
                player_trails.append({"x": center_p1_x, "y": center_p1_y, "life": 20})

            test_rect_x = pygame.Rect(p1_micro_rect.x + dx, p1_micro_rect.y, p1_micro_rect.width, p1_micro_rect.height)
            blocked_x = False
            for w in bunker.walls + [bw.rect for bw in barricades if not bw.is_destroyed]:
                if test_rect_x.colliderect(w):
                    blocked_x = True
                    break
            if not blocked_x:
                p1_x += dx

            test_rect_y = pygame.Rect(p1_micro_rect.x, p1_micro_rect.y + dy, p1_micro_rect.width, p1_micro_rect.height)
            blocked_y = False
            for w in bunker.walls + [bw.rect for bw in barricades if not bw.is_destroyed]:
                if test_rect_y.colliderect(w):
                    blocked_y = True
                    break
            if not blocked_y:
                p1_y += dy

            p1_x = max(10, min(SCREEN_WIDTH - 120, p1_x))
            p1_y = max(40, min(SCREEN_HEIGHT - 80, p1_y))

            pad_guard = ps_pad_p1 and (ps_pad_p1.get_button(4) or ps_pad_p1.get_button(9) or ps_pad_p1.get_axis(4) > 0.3)
            if (keys[pygame.K_e] or pad_guard) and p1_guard_energy > 5.0:
                p1_guard = True
                p1_guard_energy -= 0.6
            else:
                p1_guard = False
                if p1_guard_energy < 100.0:
                    p1_guard_energy += 0.35

            pad_aim_x = ps_pad_p1.get_axis(2) if ps_pad_p1 and abs(ps_pad_p1.get_axis(2)) > 0.2 else 0.0
            pad_aim_y = ps_pad_p1.get_axis(3) if ps_pad_p1 and abs(ps_pad_p1.get_axis(3)) > 0.2 else 0.0
            if math.hypot(pad_aim_x, pad_aim_y) > 0.3:
                p1_aim_angle = math.atan2(pad_aim_y, pad_aim_x)
            else:
                p1_aim_angle = math.atan2(mouse_pos[1] - center_p1_y, mouse_pos[0] - center_p1_x)

            pad_shoot = ps_pad_p1 and (ps_pad_p1.get_button(0) or ps_pad_p1.get_button(5) or (ps_pad_p1.get_numaxes() > 5 and ps_pad_p1.get_axis(5) > 0.3))
            current_wpn = WEAPON_TIERS[p1_power_tier]
            is_firing = (mouse_buttons[0] or keys[pygame.K_SPACE] or pad_shoot) and not p1_guard

            squirrel_squad_origins = [(center_p1_x, center_p1_y)]
            if p1_split_timer > 0:
                squirrel_squad_origins.append((center_p1_x - 30, center_p1_y - 25))
                squirrel_squad_origins.append((center_p1_x - 30, center_p1_y + 25))

            if current_wpn["type"] == "laser" and is_firing:
                p1_laser_active = True
                p1_laser_end_x = center_p1_x + math.cos(p1_aim_angle) * 900
                p1_laser_end_y = center_p1_y + math.sin(p1_aim_angle) * 900
                if random.random() < 0.2:
                    SFX.snd_laser.play()

                mult = 2 if game_state == "CAMPAIGN" else 1
                if p1_split_timer > 0:
                    mult *= 1.8
                laser_dmg = current_wpn["dmg"] * mult

                p1_dmg_box = pygame.Rect(
                    min(center_p1_x, p1_laser_end_x) - 15,
                    min(center_p1_y, p1_laser_end_y) - 15,
                    abs(p1_laser_end_x - center_p1_x) + 30,
                    abs(p1_laser_end_y - center_p1_y) + 30
                )

                for bw in barricades:
                    if not bw.is_destroyed and bw.rect.colliderect(p1_dmg_box):
                        bw.hp -= laser_dmg * 0.8

                if game_state == "CAMPAIGN":
                    for e in campaign_enemies[:]:
                        if not e.is_burrowed and e.core_rect.colliderect(p1_dmg_box):
                            e.hp -= laser_dmg
                            e.flash_timer = 2
                            total_score += int(laser_dmg)
                            p1_power_charge += 1.0 + (current_level * 0.1)
                            if random.random() < 0.3:
                                hit_sparks.append([e.x, e.y, random.uniform(-4, 4), random.uniform(-4, 4), 3, current_wpn["color_outer"], 12])
                            if e.hp <= 0:
                                drones_killed_session += 1
                                if e.has_split:
                                    for _ in range(2):
                                        campaign_enemies.append(ViperEnemy(current_level, is_boss=False, is_minion=True, speed=p1_speed * 1.1))
                                campaign_enemies.remove(e)
                                SFX.snd_explode.play()
                elif game_state == "DUEL" and p2_hp > 0 and not p2_is_burrowed:
                    if p2_micro_rect.colliderect(p1_dmg_box):
                        if p2_armor > 0:
                            p2_armor = max(0.0, p2_armor - laser_dmg)
                            SFX.snd_armor.play()
                        else:
                            p2_hp = max(0.0, p2_hp - laser_dmg)
                        p2_last_hit_timer = 0
                        p2_flash_timer = 2
                        p1_power_charge += 1.0

                if p1_power_charge >= 100.0 and p1_power_tier < 5:
                    p1_power_charge = 0.0
                    p1_power_tier += 1
                    update_save_data(total_score, current_level, tier=p1_power_tier)
                    SFX.snd_win.play()

            elif current_wpn["type"] == "bullet":
                p1_dmg = current_wpn["dmg"] * (2.5 if game_state == "CAMPAIGN" else 1)
                if p1_shoot_cd > 0:
                    p1_shoot_cd -= 1
                if is_firing and p1_shoot_cd == 0:
                    for ox, oy in squirrel_squad_origins:
                        p1_bullets.append({
                            "x": ox,
                            "y": oy,
                            "vx": math.cos(p1_aim_angle) * current_wpn["speed"],
                            "vy": math.sin(p1_aim_angle) * current_wpn["speed"],
                            "radius": 4 + p1_power_tier,
                            "dmg": p1_dmg,
                            "pierce": current_wpn.get("pierce", 1) + (1 if current_level >= 5 else 0),
                            "color_outer": current_wpn["color_outer"],
                            "color_core": current_wpn["color_core"],
                        })
                    SFX.snd_shoot.play()
                    p1_shoot_cd = 11

        # ORDNANCE UPDATE & EXPLOSIONS
        for ord_item in active_ordnance[:]:
            should_explode = ord_item.update()

            if ord_item.kind == "AMBUSH_MINE" and ord_item.armed:
                targets = campaign_enemies if game_state == "CAMPAIGN" else ([ViperEnemy(1)] if p2_hp > 0 and not p2_is_burrowed else [])
                for e in targets:
                    if math.hypot(e.x - ord_item.x, e.y - ord_item.y) < 40:
                        should_explode = True
                        break

            if should_explode:
                if ord_item.kind == "CLUSTER":
                    SFX.snd_cluster.play()
                    for _ in range(5):
                        c_ang = random.uniform(0, 6.28)
                        c_spd = random.uniform(3.0, 6.0)
                        active_ordnance.append(Ordnance(ord_item.x, ord_item.y, kind="SUBMUNITION", vx=math.cos(c_ang) * c_spd, vy=math.sin(c_ang) * c_spd))
                elif ord_item.kind == "SUBMUNITION":
                    trigger_explosion(ord_item.x, ord_item.y, max_r=40, dmg=35, col=(255, 180, 0))
                elif ord_item.kind == "AMBUSH_MINE":
                    trigger_explosion(ord_item.x, ord_item.y, max_r=75, dmg=90, col=(0, 240, 255))
                else:
                    trigger_explosion(ord_item.x, ord_item.y, max_r=85, dmg=80, col=(255, 100, 0))
                active_ordnance.remove(ord_item)

        # SHOCKWAVES
        for sw in shockwaves[:]:
            sw["r"] += 4.5
            for b in enemy_bullets[:] if game_state == "CAMPAIGN" else p2_bullets[:]:
                if math.hypot(b["x"] - sw["x"], b["y"] - sw["y"]) < sw["r"]:
                    if b in enemy_bullets:
                        enemy_bullets.remove(b)
                    if b in p2_bullets:
                        p2_bullets.remove(b)

            for bw in barricades:
                if not bw.is_destroyed and math.hypot(bw.rect.centerx - sw["x"], bw.rect.centery - sw["y"]) < sw["r"]:
                    bw.hp -= sw["dmg"] * 0.2

            if game_state == "CAMPAIGN":
                for e in campaign_enemies[:]:
                    if not e.is_burrowed and math.hypot(e.x - sw["x"], e.y - sw["y"]) < sw["r"] + 18:
                        e.hp -= sw["dmg"] * 0.15
                        e.flash_timer = 2
                        total_score += 4
                        if e.hp <= 0:
                            drones_killed_session += 1
                            if e.has_split:
                                for _ in range(2):
                                    campaign_enemies.append(ViperEnemy(current_level, is_boss=False, is_minion=True, speed=p1_speed * 1.1))
                            campaign_enemies.remove(e)
                            SFX.snd_explode.play()
            elif game_state == "DUEL" and p2_hp > 0 and not p2_is_burrowed:
                if math.hypot(p2_x - sw["x"], p2_y - sw["y"]) < sw["r"] + 18:
                    dmg_chunk = sw["dmg"] * 0.15
                    if p2_armor > 0:
                        p2_armor = max(0.0, p2_armor - dmg_chunk)
                    else:
                        p2_hp = max(0.0, p2_hp - dmg_chunk)
                    p2_last_hit_timer = 0
                    p2_flash_timer = 2

            if sw["r"] >= sw["max_r"]:
                shockwaves.remove(sw)

        # 1-PLAYER CAMPAIGN LOGIC
        if game_state == "CAMPAIGN":
            p1_target_x = center_p1_x
            p1_target_y = center_p1_y
            p1_decoys_active = [d for d in active_decoys if d["type"] == "p1"]
            if len(p1_decoys_active) > 0:
                p1_target_x = p1_decoys_active[0]["x"] + 74
                p1_target_y = p1_decoys_active[0]["y"] + 35

            for e in campaign_enemies:
                shots = e.update(burrow_holes, p1_target_x, p1_target_y, SCREEN_WIDTH, SCREEN_HEIGHT, acid_pools)
                if shots and p1_hp > 0:
                    enemy_bullets.extend(shots)

            for b in enemy_bullets[:]:
                if b.get("homing", False):
                    h_angle = math.atan2(p1_target_y - b["y"], p1_target_x - b["x"])
                    b["vx"] = b["vx"] * 0.95 + math.cos(h_angle) * 0.4
                    b["vy"] = b["vy"] * 0.95 + math.sin(h_angle) * 0.4

                if current_level >= 8 and p1_surge_timer == 0:
                    dist_to_p1 = math.hypot(b["x"] - center_p1_x, b["y"] - center_p1_y)
                    if 20 < dist_to_p1 < 50:
                        p1_surge_timer = 90
                        SFX.snd_surge.play()
                        floating_texts.append(["HYPER REFLEX!", center_p1_x - 25, center_p1_y - 25, (0, 240, 255), 30])

                b["x"] += b["vx"]
                b["y"] += b["vy"]
                b_rect = pygame.Rect(b["x"] - 5, b["y"] - 5, 10, 10)
                hit_wall = False
                for w in bunker.walls:
                    if w.colliderect(b_rect):
                        hit_wall = True
                        break
                for bw in barricades:
                    if not bw.is_destroyed and bw.rect.colliderect(b_rect):
                        bw.hp -= b["dmg"]
                        hit_wall = True
                        break
                if hit_wall or b["x"] < 0 or b["x"] > SCREEN_WIDTH or b["y"] < 0 or b["y"] > SCREEN_HEIGHT:
                    enemy_bullets.remove(b)

            # Defensive Squirrel Tail Deflection Check
            for b in enemy_bullets[:]:
                b_rect = pygame.Rect(b["x"] - 5, b["y"] - 5, 10, 10)
                if p1_guard and math.hypot(b["x"] - center_p1_x, b["y"] - center_p1_y) < 38:
                    enemy_bullets.remove(b)
                    SFX.snd_shield.play()
                elif p1_sq_tail_scale > 0.03 and p1_tail_rect.colliderect(b_rect):
                    enemy_bullets.remove(b)
                    SFX.snd_shield.play()
                    hit_sparks.append([b["x"], b["y"], random.uniform(-3, 3), random.uniform(-3, 3), 2, (255, 140, 0), 10])
                elif p1_micro_rect.colliderect(b_rect):
                    p1_last_hit_timer = 0
                    incoming_dmg = b["dmg"]
                    if p1_armor > 0:
                        absorbed = min(p1_armor, incoming_dmg)
                        p1_armor -= absorbed
                        incoming_dmg -= absorbed
                        SFX.snd_armor.play()
                        if p1_armor <= 0 and current_level >= 6:
                            trigger_explosion(center_p1_x, center_p1_y, max_r=70, dmg=45, col=(0, 240, 255))
                            floating_texts.append(["ARMOR OVERLOAD!", center_p1_x - 30, center_p1_y - 20, (0, 240, 255), 35])
                    if incoming_dmg > 0:
                        p1_hp = max(0, p1_hp - incoming_dmg)
                        SFX.snd_hit.play()
                    enemy_bullets.remove(b)

            # Bullets hitting Viper (Core Head vs Body segments)
            for b in p1_bullets[:]:
                b_rect = pygame.Rect(b["x"] - b["radius"], b["y"] - b["radius"], b["radius"] * 2, b["radius"] * 2)
                hit_wall = False
                for w in bunker.walls:
                    if w.colliderect(b_rect):
                        hit_wall = True
                        break
                for bw in barricades:
                    if not bw.is_destroyed and bw.rect.colliderect(b_rect):
                        bw.hp -= b["dmg"] * 0.5
                        hit_wall = True
                        break
                if hit_wall:
                    p1_bullets.remove(b)
                    continue

                for e in campaign_enemies[:]:
                    if not e.is_burrowed:
                        # Core head hit
                        if e.core_rect.colliderect(b_rect):
                            e.hp -= b["dmg"]
                            e.flash_timer = 3
                            SFX.snd_hit.play()
                            total_score += b["dmg"]
                            p1_power_charge += 24.0

                            b["pierce"] = b.get("pierce", 1) - 1
                            if b["pierce"] <= 0:
                                if b in p1_bullets:
                                    p1_bullets.remove(b)

                            if p1_power_charge >= 100.0 and p1_power_tier < 5:
                                p1_power_charge = 0.0
                                p1_power_tier += 1
                                update_save_data(total_score, current_level, tier=p1_power_tier)
                                SFX.snd_win.play()
                            if e.hp <= 0:
                                drones_killed_session += 1
                                if e.has_split:
                                    for _ in range(2):
                                        campaign_enemies.append(ViperEnemy(current_level, is_boss=False, is_minion=True, speed=p1_speed * 1.1))
                                campaign_enemies.remove(e)
                                SFX.snd_explode.play()
                            break

                        # Trailing Body segment deflection
                        deflected = False
                        for seg_x, seg_y, _ in e.get_tail_segments():
                            if math.hypot(b["x"] - seg_x, b["y"] - seg_y) < 13:
                                if b in p1_bullets:
                                    p1_bullets.remove(b)
                                SFX.snd_shield.play()
                                deflected = True
                                break
                        if deflected:
                            break

            if len(campaign_enemies) == 0:
                handle_round_conclusion("P1", "CAMPAIGN")
            if p1_hp <= 0:
                handle_round_conclusion("P2", "CAMPAIGN")

        # ======================================================================
        # 2-PLAYER DUEL LOGIC (UPGRADED WITH FULL ARTICULATED CYBER SNAKE)
        # ======================================================================
        elif game_state == "DUEL":
            p2_micro_rect = pygame.Rect(p2_x - 18, p2_y - 18, 36, 36)

            if p2_hp > 0:
                if p2_burrow_cd > 0:
                    p2_burrow_cd -= 1
                if p2_is_burrowed:
                    p2_burrow_timer -= 1
                    if p2_burrow_timer <= 0:
                        dest = random.choice(burrow_holes)
                        p2_x = dest[0]
                        p2_y = dest[1]
                        p2_is_burrowed = False
                        p2_history.clear()
                        for _ in range(p2_history.maxlen):
                            p2_history.append((p2_x, p2_y, p2_angle))
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

                    p2_test = pygame.Rect(p2_micro_rect.x + p2_vx, p2_micro_rect.y + p2_vy, p2_micro_rect.width, p2_micro_rect.height)
                    blocked_p2 = False
                    for w in bunker.walls + [bw.rect for bw in barricades if not bw.is_destroyed]:
                        if p2_test.colliderect(w):
                            blocked_p2 = True
                            break
                    if not blocked_p2:
                        p2_x += p2_vx
                        p2_y += p2_vy

                    p2_x = max(20, min(SCREEN_WIDTH - 60, p2_x))
                    p2_y = max(55, min(SCREEN_HEIGHT - 60, p2_y))

                    aim_target_x = center_p1_x
                    aim_target_y = center_p1_y
                    p1_decoys_active = [d for d in active_decoys if d["type"] == "p1"]
                    if len(p1_decoys_active) > 0:
                        aim_target_x = p1_decoys_active[0]["x"] + 74
                        aim_target_y = p1_decoys_active[0]["y"] + 35

                    p2_dx = aim_target_x - p2_x
                    p2_dy = aim_target_y - p2_y
                    p2_angle = math.degrees(math.atan2(p2_dy, p2_dx))

                    p2_history.appendleft((p2_x, p2_y, p2_angle))

                    p2_current_wpn = WEAPON_TIERS[p2_power_tier]
                    p2_pad_shoot = ps_pad_p2 and (ps_pad_p2.get_button(0) or ps_pad_p2.get_button(7))
                    p2_is_firing = (keys[pygame.K_KP0] or keys[pygame.K_RSHIFT] or p2_pad_shoot)

                    if p2_current_wpn["type"] == "bullet":
                        if p2_shoot_cd > 0:
                            p2_shoot_cd -= 1
                        if p2_is_firing and p2_shoot_cd == 0:
                            rad = math.radians(p2_angle)
                            p2_bullets.append({
                                "x": p2_x,
                                "y": p2_y,
                                "vx": math.cos(rad) * p2_current_wpn["speed"],
                                "vy": math.sin(rad) * p2_current_wpn["speed"],
                                "radius": 4 + p2_power_tier,
                                "dmg": p2_current_wpn["dmg"],
                            })
                            SFX.snd_v_shoot.play()
                            p2_shoot_cd = 11

            if p2_flash_timer > 0:
                p2_flash_timer -= 1

            for b in p2_bullets[:]:
                b["x"] += b["vx"]
                b["y"] += b["vy"]
                b_rect = pygame.Rect(b["x"] - 5, b["y"] - 5, 10, 10)
                hit_wall = False
                for w in bunker.walls:
                    if w.colliderect(b_rect):
                        hit_wall = True
                        break
                for bw in barricades:
                    if not bw.is_destroyed and bw.rect.colliderect(b_rect):
                        bw.hp -= b["dmg"]
                        hit_wall = True
                        break
                if hit_wall or b["x"] < 0 or b["x"] > SCREEN_WIDTH or b["y"] < 0 or b["y"] > SCREEN_HEIGHT:
                    p2_bullets.remove(b)

            for b in p2_bullets[:]:
                b_rect = pygame.Rect(b["x"] - 5, b["y"] - 5, 10, 10)
                if p1_guard and math.hypot(b["x"] - center_p1_x, b["y"] - center_p1_y) < 38:
                    p2_bullets.remove(b)
                    SFX.snd_shield.play()
                elif p1_sq_tail_scale > 0.03 and p1_tail_rect.colliderect(b_rect):
                    p2_bullets.remove(b)
                    SFX.snd_shield.play()
                elif p1_micro_rect.colliderect(b_rect) and p1_hp > 0:
                    p1_last_hit_timer = 0
                    incoming = b["dmg"]
                    if p1_armor > 0:
                        absorbed = min(p1_armor, incoming)
                        p1_armor -= absorbed
                        incoming -= absorbed
                        SFX.snd_armor.play()
                    if incoming > 0:
                        p1_hp = max(0, p1_hp - incoming)
                        SFX.snd_hit.play()
                    p2_bullets.remove(b)
                    p2_power_charge += 24.0

            # P1 hits P2
            for b in p1_bullets[:]:
                b_rect = pygame.Rect(b["x"] - 5, b["y"] - 5, 10, 10)
                if not p2_is_burrowed and p2_hp > 0:
                    if p2_micro_rect.colliderect(b_rect):
                        p2_last_hit_timer = 0
                        incoming = b["dmg"]
                        if p2_armor > 0:
                            absorbed = min(p2_armor, incoming)
                            p2_armor -= absorbed
                            incoming -= absorbed
                            SFX.snd_armor.play()
                        if incoming > 0:
                            p2_hp = max(0, p2_hp - incoming)
                            SFX.snd_hit.play()
                        p2_flash_timer = 3
                        p1_bullets.remove(b)
                        p1_power_charge += 24.0
                    else:
                        deflected = False
                        step = 3
                        for i in range(2, p2_max_segments + 2):
                            idx = i * step
                            if idx < len(p2_history):
                                sx, sy, _ = p2_history[idx]
                                if math.hypot(b["x"] - sx, b["y"] - sy) < 13:
                                    p1_bullets.remove(b)
                                    SFX.snd_shield.play()
                                    deflected = True
                                    break
                        if deflected:
                            continue

            if p1_hp <= 0:
                p2_wins += 1
                handle_round_conclusion("P2", "DUEL")
            elif p2_hp <= 0:
                p1_wins += 1
                handle_round_conclusion("P1", "DUEL")

        # Projectiles
        for b in p1_bullets[:]:
            b["x"] += b["vx"]
            b["y"] += b["vy"]
            if b["x"] < 0 or b["x"] > SCREEN_WIDTH or b["y"] < 0 or b["y"] > SCREEN_HEIGHT:
                p1_bullets.remove(b)

        for b in p1_bullets:
            pygame.draw.circle(screen, b["color_outer"], (int(b["x"]), int(b["y"])), b["radius"])
            pygame.draw.circle(screen, b["color_core"], (int(b["x"]), int(b["y"])), max(1, b["radius"] - 2))

        for b in (enemy_bullets if game_state == "CAMPAIGN" else p2_bullets):
            color = b.get("color", (0, 210, 255))
            r = b.get("radius", 5)
            pygame.draw.circle(screen, color, (int(b["x"]), int(b["y"])), r)
            pygame.draw.circle(screen, (255, 255, 255), (int(b["x"]), int(b["y"])), max(1, r - 2))

        for ord_item in active_ordnance:
            ord_item.draw(screen)

        for sw in shockwaves:
            alpha = max(30, int(255 * (1.0 - sw["r"] / sw["max_r"])))
            sw_surf = pygame.Surface((int(sw["r"] * 2 + 8), int(sw["r"] * 2 + 8)), pygame.SRCALPHA)
            pygame.draw.circle(sw_surf, (*sw["col"], alpha), (int(sw["r"] + 4), int(sw["r"] + 4)), int(sw["r"]), 3)
            screen.blit(sw_surf, (int(sw["x"] - sw["r"] - 4), int(sw["y"] - sw["r"] - 4)))

        wpn = WEAPON_TIERS[p1_power_tier]
        if p1_laser_active:
            pygame.draw.line(screen, wpn["color_outer"], (center_p1_x, center_p1_y), (p1_laser_end_x, p1_laser_end_y), wpn["beam_w"] + 4)
            pygame.draw.line(screen, wpn["color_core"], (center_p1_x, center_p1_y), (p1_laser_end_x, p1_laser_end_y), wpn["beam_w"])

        for dec in active_decoys:
            alpha = 130 + int(math.sin(dec["life"] * 0.2) * 50)
            if dec["type"] == "p1":
                h_surf = create_squirrel_sprite(p1_sq_tail_scale, True, (0, 240, 255), alpha=alpha)
                screen.blit(h_surf, (dec["x"], dec["y"]))
            else:
                v_h_raw = create_viper_head(is_boss=False, flash_white=False, alpha=alpha)
                screen.blit(v_h_raw, (dec["x"] - 29, dec["y"] - 21))

        for spark in hit_sparks[:]:
            spark[0] += spark[2]
            spark[1] += spark[3]
            spark[6] -= 1
            if spark[6] <= 0:
                hit_sparks.remove(spark)
            else:
                pygame.draw.circle(screen, spark[5], (int(spark[0]), int(spark[1])), spark[4])

        for ft in floating_texts[:]:
            ft[2] -= 1.0
            ft[4] -= 1
            if ft[4] <= 0:
                floating_texts.remove(ft)
            else:
                screen.blit(font.render(ft[0], True, ft[3]), (int(ft[1]), int(ft[2])))

        # Draw P1
        aura_color = (0, 240, 255) if p1_surge_timer > 0 else WEAPON_TIERS[p1_power_tier]["color_outer"]
        s_surf = create_squirrel_sprite(p1_sq_tail_scale, p1_guard, aura_color)
        if p1_hp > 0:
            screen.blit(s_surf, (p1_x, p1_y))

        if p1_armor > 0 and p1_hp > 0:
            pygame.draw.circle(screen, (0, 180, 255), (int(center_p1_x), int(center_p1_y)), 22, 1)

        if p1_guard:
            pygame.draw.circle(screen, (0, 220, 255), (int(center_p1_x), int(center_p1_y)), 34, 2)

        # Draw Enemies (Campaign Mode)
        if game_state == "CAMPAIGN":
            for e in campaign_enemies:
                e.draw(screen)

        # Draw Player 2 (Duel Mode)
        elif game_state == "DUEL" and p2_hp > 0:
            if not p2_is_burrowed:
                # 1. Trailing Snake Segments
                step = 3
                for i in range(2, p2_max_segments + 2):
                    idx = i * step
                    if idx < len(p2_history):
                        seg_x, seg_y, _ = p2_history[idx]
                        seg_ratio = 1.0 - (i / max(1, p2_max_segments + 2))
                        seg_r = max(3, int(11 * seg_ratio))
                        s_surf = pygame.Surface((seg_r * 2 + 4, seg_r * 2 + 4), pygame.SRCALPHA)
                        pygame.draw.circle(s_surf, (25, 38, 60), (seg_r + 2, seg_r + 2), seg_r)
                        pygame.draw.circle(s_surf, (0, 220, 255), (seg_r + 2, seg_r + 2), seg_r, 1)
                        screen.blit(s_surf, (seg_x - seg_r - 2, seg_y - seg_r - 2))

                # 2. Glowing P2 Head on Top
                v_head = p2_head_flash if p2_flash_timer > 0 else p2_head_normal
                v_rot = pygame.transform.rotate(v_head, -p2_angle)
                screen.blit(v_rot, v_rot.get_rect(center=(p2_x, p2_y)))

                # 3. P2 Targeting Reticle
                bracket_col = (0, 255, 230)
                bracket_r = 20
                pygame.draw.circle(screen, bracket_col, (int(p2_x), int(p2_y)), bracket_r, 1)
                for deg in (0, 90, 180, 270):
                    rad = math.radians(deg)
                    tx1 = p2_x + math.cos(rad) * (bracket_r - 4)
                    ty1 = p2_y + math.sin(rad) * (bracket_r - 4)
                    tx2 = p2_x + math.cos(rad) * (bracket_r + 4)
                    ty2 = p2_y + math.sin(rad) * (bracket_r + 4)
                    pygame.draw.line(screen, bracket_col, (tx1, ty1), (tx2, ty2), 1)

                if p2_armor > 0:
                    pygame.draw.circle(screen, (0, 180, 255), (int(p2_x), int(p2_y)), 22, 1)
            else:
                screen.blit(font.render("[UNDERGROUND]", True, (200, 100, 255)), (p2_x - 30, p2_y - 20))

        if not ps_pad_p1:
            pygame.draw.circle(screen, WEAPON_TIERS[p1_power_tier]["color_outer"], mouse_pos, 5, 1)
            pygame.draw.circle(screen, (255, 255, 255), mouse_pos, 2)

        # HUD
        p1_col = (255, 140, 0) if p1_hp > 50 else (255, 60, 60)
        screen.blit(font.render("P1: S.Q.U.I.R.E.L.", True, (255, 180, 80)), (20, 10))
        screen.blit(num_font.render(f"HP: {int(p1_hp)}/{p1_max_hp}", True, p1_col), (20, 25))
        screen.blit(font.render(f"ARMOR: {int(p1_armor)}/{p1_max_armor}", True, (0, 210, 255)), (20, 48))
        spd_col = (0, 240, 255) if p1_surge_timer > 0 else (0, 255, 200)
        screen.blit(font.render(f"SPEED: {actual_p1_speed if 'actual_p1_speed' in locals() else p1_speed:.2f}", True, spd_col), (20, 64))
        tail_disp = f"SQ TAIL DEF: {int(p1_sq_tail_scale * 100)}% | VIPER LENGTH: {int(get_viper_length_factor(current_level) * 10)}x"
        screen.blit(font.render(tail_disp, True, (255, 215, 60)), (20, 80))

        if game_state == "CAMPAIGN":
            lvl_col = (255, 60, 90) if current_level >= 10 else (255, 230, 100)
            lvl_txt = "FINAL LEVEL 10 (BOSS)" if current_level >= 10 else f"LEVEL {current_level} / 10"
            screen.blit(font.render(lvl_txt, True, lvl_col), (SCREEN_WIDTH // 2 - 50, 10))
            screen.blit(font.render(f"SCORE: {total_score}", True, (200, 210, 240)), (SCREEN_WIDTH - 140, 10))

            augments_active = []
            if current_level >= 2: augments_active.append("PLASMA TRAIL")
            if current_level >= 3: augments_active.append("BURROW SCATTER")
            if current_level >= 5: augments_active.append("PIERCING ROUNDS")
            if current_level >= 6: augments_active.append("AEGIS OVERLOAD")
            if current_level >= 8: augments_active.append("HYPER REFLEX")
            if augments_active:
                aug_str = "AUGMENTS: " + " + ".join(augments_active)
                screen.blit(font.render(aug_str, True, (0, 240, 255)), (20, SCREEN_HEIGHT - 22))

        elif game_state == "DUEL":
            p2_col = (0, 210, 255) if p2_hp > 35 else (255, 60, 60)
            p2_head = font.render("P2: CYBER VIPER", True, (0, 210, 255))
            p2_num = num_font.render(f"HP: {int(p2_hp)}/{p2_max_hp}", True, p2_col)
            p2_arm = font.render(f"ARMOR: {int(p2_armor)}/{p2_max_armor}", True, (0, 210, 255))
            p2_sub = font.render(f"SPEED: {p2_speed:.2f} | WINS: {p2_wins}", True, (200, 210, 230))
            screen.blit(p2_head, (SCREEN_WIDTH - p2_head.get_width() - 20, 10))
            screen.blit(p2_num, (SCREEN_WIDTH - p2_num.get_width() - 20, 25))
            screen.blit(p2_arm, (SCREEN_WIDTH - p2_arm.get_width() - 20, 48))
            screen.blit(p2_sub, (SCREEN_WIDTH - p2_sub.get_width() - 20, 64))

        pygame.display.flip()
        clock.tick(60)
        await asyncio.sleep(0)

    pygame.quit()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass