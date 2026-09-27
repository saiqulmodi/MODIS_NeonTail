import sys
import math
import random
import struct
import asyncio
import pygame

# ---------------------------------------------------------
# 1. VIEWPORT & FULLSCREEN CONFIGURATION
# ---------------------------------------------------------
if sys.platform == "emscripten":
    import platform
    try:
        # Stretch canvas edge-to-edge across the entire browser viewport
        platform.window.canvas.style.position = "fixed"
        platform.window.canvas.style.top = "0"
        platform.window.canvas.style.left = "0"
        platform.window.canvas.style.width = "100vw"
        platform.window.canvas.style.height = "100vh"
        platform.window.canvas.style.display = "block"
        platform.window.canvas.style.margin = "0"
        platform.window.canvas.style.padding = "0"
        platform.window.canvas.style.border = "none"
        platform.window.document.body.style.margin = "0"
        platform.window.document.body.style.padding = "0"
        platform.window.document.body.style.backgroundColor = "#05060d"
        platform.window.document.body.style.overflow = "hidden"
    except Exception:
        pass

WIDTH = 1280
HEIGHT = 720

# ---------------------------------------------------------
# 2. LOCALSTORAGE HIGH SCORE
# ---------------------------------------------------------
def get_stored_high_score():
    if sys.platform == "emscripten":
        try:
            import platform
            val = platform.window.localStorage.getItem("neontail_hiscore")
            return int(val) if val else 0
        except Exception:
            return 0
    return 0

def save_stored_high_score(score):
    if sys.platform == "emscripten":
        try:
            import platform
            platform.window.localStorage.setItem("neontail_hiscore", str(score))
        except Exception:
            pass

# ---------------------------------------------------------
# 3. WASM-COMPATIBLE SYNTHETIC AUDIO WITH RIFF WAV HEADERS
# ---------------------------------------------------------
audio_muted = False

def build_wav_sound(duration, func, sample_rate=22050):
    """Encodes synthetic PCM audio inside a proper RIFF WAV container for WASM compatibility."""
    n_samples = int(sample_rate * duration)
    raw_pcm = bytearray(n_samples)
    for i in range(n_samples):
        t = i / sample_rate
        val, decay = func(t, duration)
        raw_pcm[i] = max(0, min(255, int(128 + 115 * val * decay)))

    byte_rate = sample_rate
    block_align = 1
    data_size = n_samples
    file_size = 36 + data_size

    header = bytearray()
    header.extend(b'RIFF')
    header.extend(struct.pack('<I', file_size))
    header.extend(b'WAVEfmt ')
    header.extend(struct.pack('<I', 16))         # PCM chunk size
    header.extend(struct.pack('<H', 1))          # Format 1 = PCM
    header.extend(struct.pack('<H', 1))          # 1 Channel (Mono)
    header.extend(struct.pack('<I', sample_rate))
    header.extend(struct.pack('<I', byte_rate))
    header.extend(struct.pack('<H', block_align))
    header.extend(struct.pack('<H', 8))          # 8-bit unsigned
    header.extend(b'data')
    header.extend(struct.pack('<I', data_size))

    try:
        return pygame.mixer.Sound(buffer=bytes(header + raw_pcm))
    except Exception:
        return None

# Each game mode gives every attack its own waveform "voice"
MODE_WAVES = {1: "sine", 2: "square", 3: "saw"}

# Attack tool recipes: (duration, start Hz, end Hz, noise mix, extra harmonic)
ATTACK_RECIPES = {
    "p1_laser": (0.11, 980, 360, 0.00, 0.0),   # Squirrel P1 zap (falls)
    "p1_nova":  (0.30, 450, 100, 0.20, 0.0),   # Squirrel P1 shockwave (deep drop)
    "p2_laser": (0.12, 1250, 700, 0.00, 0.3),  # Squirrel P2 blaster (bright, harmonic)
    "p2_nova":  (0.30, 260, 620, 0.15, 0.3),   # Squirrel P2 shockwave (rises)
    "ai_spit":  (0.16, 720, 180, 0.40, 0.0),   # AI viper venom sizzle
    "pvp_spit": (0.18, 480, 900, 0.30, 0.2),   # Player viper venom (rising hiss)
    "ai_bite":  (0.14, 160, 60, 0.80, 0.0),    # AI viper bite thud
    "pvp_bite": (0.14, 260, 90, 0.60, 0.3),    # Player viper bite snap
}

def sound_tier(level):
    """Sounds and music evolve every 10 levels (tier 0-9)."""
    return max(0, min(9, level // 10))

def wave_sample(shape, phase):
    frac = phase % 1.0
    if shape == "square":
        return 0.55 if frac < 0.5 else -0.55
    if shape == "saw":
        return 0.7 * (2.0 * frac - 1.0)
    return math.sin(2 * math.pi * phase)

_attack_sfx_cache = {}

def get_attack_sfx(tool, mode, level):
    """Unique sound per (attack tool, game mode, level tier), built once and cached."""
    tier = sound_tier(level)
    key = (tool, mode, tier)
    if key not in _attack_sfx_cache:
        dur, f0, f1, noise, harm = ATTACK_RECIPES[tool]
        shape = MODE_WAVES.get(mode, "sine")
        pitch = 2 ** (tier * 2 / 12.0)  # +2 semitones per tier
        f0 *= pitch
        f1 *= pitch
        harm_mix = min(0.45, harm + tier * 0.03)
        harm_ratio = 1.5 + (tier % 3) * 0.5

        def fn(t, d):
            phase = f0 * t + (f1 - f0) * t * t / (2 * d)
            tone = wave_sample(shape, phase) * (1.0 - harm_mix) + math.sin(2 * math.pi * phase * harm_ratio) * harm_mix
            val = tone * (1.0 - noise) + (random.random() * 2.0 - 1.0) * noise
            return val, max(0.0, 1.0 - (t / d))

        try:
            _attack_sfx_cache[key] = build_wav_sound(dur, fn)
        except Exception:
            _attack_sfx_cache[key] = None
    return _attack_sfx_cache[key]

# Background music scales per mode: solo = minor pentatonic, co-op = major pentatonic, PvP = tense
MODE_SCALES = {1: [0, 3, 5, 7, 10], 2: [0, 2, 4, 7, 9], 3: [0, 1, 5, 6, 10]}
MUSIC_PATTERN = [0, 2, 4, 2, 1, 3, 4, 3, 0, 2, 4, 7, 5, 4, 2, 1]

def build_music_loop(mode, tier):
    """16-step arpeggio loop; key rises and tempo quickens as the level tier grows."""
    scale = MODE_SCALES.get(mode, MODE_SCALES[1])
    shape = MODE_WAVES.get(mode, "sine")
    root = 110.0 * (2 ** (tier / 12.0))
    step = max(0.12, 0.24 - tier * 0.012)
    notes = [root * 2 ** ((scale[i % 5] + 12 * (i // 5) + 12) / 12.0) for i in MUSIC_PATTERN]

    def fn(t, d):
        idx = min(len(notes) - 1, int(t / step))
        local = t - idx * step
        env = max(0.0, 1.0 - local / step) ** 1.5
        lead = wave_sample(shape, notes[idx] * t) * env * 0.45
        bass = math.sin(2 * math.pi * (root / 2) * t) * (0.30 if (idx % 4) < 2 else 0.15)
        return lead + bass, 1.0

    return build_wav_sound(step * len(MUSIC_PATTERN), fn, sample_rate=11025)

def sfx_boom_audio():
    # Enemy defeat detonation
    return build_wav_sound(0.22, lambda t, d: ((random.random() * 2.0 - 1.0), max(0.0, 1.0 - (t / d))))

def sfx_pickup_audio():
    # Energy shard absorption chime
    return build_wav_sound(0.13, lambda t, d: (math.sin(2 * math.pi * (520 + (t / d) * 880) * t), max(0.0, 1.0 - (t / d))))

def play_sfx(sfx):
    global audio_muted
    if sfx and not audio_muted:
        try:
            sfx.play()
        except Exception:
            pass

# ---------------------------------------------------------
# 4. PROJECTILES, PARTICLES & ENERGY SHARDS
# ---------------------------------------------------------
class Projectile:
    def __init__(self, x, y, tx, ty, damage=40, color=(0, 255, 230), is_hostile=False, speed=15.0):
        self.x = float(x)
        self.y = float(y)
        angle = math.atan2(ty - y, tx - x)
        self.speed = speed
        self.vx = math.cos(angle) * self.speed
        self.vy = math.sin(angle) * self.speed
        self.damage = damage
        self.color = color
        self.is_hostile = is_hostile
        self.alive = True

    def update(self):
        self.x += self.vx
        self.y += self.vy
        if self.x < -30 or self.x > WIDTH + 30 or self.y < -30 or self.y > HEIGHT + 30:
            self.alive = False

    def draw(self, surface):
        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), 6)
        pygame.draw.circle(surface, (255, 255, 255), (int(self.x), int(self.y)), 3)

class Particle:
    def __init__(self, x, y, color):
        self.x = float(x)
        self.y = float(y)
        angle = random.uniform(0, math.pi * 2)
        speed = random.uniform(2.0, 6.0)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life = random.randint(14, 24)
        self.color = color

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1

    def draw(self, surface):
        if self.life > 0:
            pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), max(1, self.life // 5))

class Shard:
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.life = 360
        self.pulse = random.uniform(0, math.pi * 2)

    def update(self):
        self.life -= 1
        self.pulse += 0.12

    def draw(self, surface):
        r = int(5 + math.sin(self.pulse) * 2)
        pygame.draw.circle(surface, (0, 255, 180), (int(self.x), int(self.y)), r)
        pygame.draw.circle(surface, (255, 255, 255), (int(self.x), int(self.y)), 2)

# ---------------------------------------------------------
# 5. SHARED LEVEL STATS (squirrel and viper always identical)
# ---------------------------------------------------------
def level_stats(level):
    level = max(1, level)
    return {
        "max_hp": 300 + (level - 1) * 35,
        "max_defense": 100 + (level - 1) * 20,
        "attack_power": 35 + (level - 1) * 4,
    }

def apply_level_stats(unit, level):
    """Single source of truth: HP, defense and attack refill to the same values for both sides."""
    stats = level_stats(level)
    unit.max_hp = stats["max_hp"]
    unit.hp = unit.max_hp
    unit.max_defense = stats["max_defense"]
    unit.defense = unit.max_defense
    unit.attack_power = stats["attack_power"]

# ---------------------------------------------------------
# 5b. SQUIRREL / HERO (SYMMETRICAL SCALING)
# ---------------------------------------------------------
class SquirrelPlayer:
    def __init__(self, x, y, player_id=1, level=1):
        self.player_id = player_id
        self.x = float(x)
        self.y = float(y)
        self.score = 0
        self.kills = 0
        self.facing_right = True
        self.anim_t = 0.0
        self.nova_cd = 0
        self.apply_level_up(level)

    def apply_level_up(self, level):
        self.level = level
        self.speed = 6.8 + min(3.0, (self.level - 1) * 0.06)
        apply_level_stats(self, level)
        self.nova_max_cd = max(70, 180 - (self.level * 3))

    def move(self, dx, dy):
        if dx > 0:
            self.facing_right = True
        elif dx < 0:
            self.facing_right = False
        self.x = max(50, min(WIDTH - 50, self.x + dx * self.speed))
        self.y = max(50, min(HEIGHT - 50, self.y + dy * self.speed))

    def take_damage(self, amount):
        if self.defense > 0:
            absorbed = min(self.defense, amount)
            self.defense -= absorbed
            amount -= absorbed
        self.hp = max(0, self.hp - amount)

    def update(self):
        self.anim_t += 0.15
        if self.nova_cd > 0:
            self.nova_cd -= 1

    def draw(self, surface):
        tail_dir = -1 if self.facing_right else 1
        tail_wave = math.sin(self.anim_t * 1.5) * 6
        tint = (215, 145, 80) if self.player_id == 1 else (100, 200, 255)
        base_fur = (190, 115, 50) if self.player_id == 1 else (60, 130, 200)

        for seg in range(6):
            tx = self.x + tail_dir * (22 + seg * 7)
            ty = self.y + 6 + math.sin(self.anim_t + seg * 0.4) * 8 + tail_wave
            rad = max(4, 11 - seg)
            pygame.draw.circle(surface, base_fur, (int(tx), int(ty)), rad)
            pygame.draw.circle(surface, tint, (int(tx), int(ty)), rad - 2)

        pygame.draw.ellipse(surface, base_fur, (self.x - 22, self.y - 12, 44, 24))
        pygame.draw.ellipse(surface, tint, (self.x - 16, self.y - 8, 32, 16))

        hx = self.x + (16 if self.facing_right else -16)
        hy = self.y - 6
        pygame.draw.circle(surface, tint, (int(hx), int(hy)), 12)

        ear_x = hx - (4 if self.facing_right else -4)
        ear_y = hy - 11
        pygame.draw.circle(surface, (150, 80, 30), (int(ear_x), int(ear_y)), 5)
        pygame.draw.circle(surface, (240, 180, 140), (int(ear_x), int(ear_y)), 2)

        eye_x = hx + (4 if self.facing_right else -4)
        pygame.draw.circle(surface, (25, 25, 25), (int(eye_x), int(hy - 2)), 3)
        pygame.draw.circle(surface, (255, 255, 255), (int(eye_x + 1), int(hy - 3)), 1)

# ---------------------------------------------------------
# 6. VIPER (SYMMETRICAL SCALING & ARSENAL)
# ---------------------------------------------------------
class ViperEnemy:
    def __init__(self, tail_scale=1.0, level=1, is_player_controlled=False):
        self.tail_scale = max(0.40, tail_scale)
        self.level = level
        self.is_player_controlled = is_player_controlled

        side = random.choice(["L", "R", "T", "B"])
        if side == "L":
            self.x, self.y = -60.0, random.uniform(80, HEIGHT - 80)
        elif side == "R":
            self.x, self.y = float(WIDTH + 60), random.uniform(80, HEIGHT - 80)
        elif side == "T":
            self.x, self.y = random.uniform(80, WIDTH - 80), -60.0
        else:
            self.x, self.y = random.uniform(80, WIDTH - 80), float(HEIGHT + 60)

        self.num_segments = max(8, int(24 * self.tail_scale))
        self.history = [(self.x, self.y) for _ in range(self.num_segments * 3 + 12)]

        self.base_speed = 3.0 + min(3.5, (level - 1) * 0.05)
        self.slither_t = random.uniform(0, 10)

        # Identical balance curves (shared with SquirrelPlayer)
        apply_level_stats(self, level)

        self.spit_cd = random.randint(40, 100)

    def apply_level_up(self, level):
        self.level = level
        self.base_speed = 3.0 + min(3.5, (level - 1) * 0.05)
        apply_level_stats(self, level)

    def take_damage(self, amount):
        if self.defense > 0:
            absorbed = min(self.defense, amount)
            self.defense -= absorbed
            amount -= absorbed
        self.hp = max(0, self.hp - amount)

    def update_ai(self, targets, projectiles_list, new_proj_fn):
        self.slither_t += 0.14
        active_targets = [t for t in targets if t.hp > 0]
        if not active_targets:
            return

        closest_target = min(active_targets, key=lambda t: math.hypot(t.x - self.x, t.y - self.y))
        tx, ty = closest_target.x, closest_target.y
        dist = math.hypot(tx - self.x, ty - self.y)

        # Evade player lasers
        evade_x, evade_y = 0.0, 0.0
        for p in projectiles_list:
            if not p.is_hostile:
                d_p = math.hypot(p.x - self.x, p.y - self.y)
                if d_p < 140:
                    evade_x += -p.vy / (d_p + 1) * 35.0
                    evade_y += p.vx / (d_p + 1) * 35.0
                    break

        lunge = 1.35 if dist < 170 else 1.0
        angle = math.atan2(ty - self.y, tx - self.x)
        wiggle = math.sin(self.slither_t) * 0.70

        self.x += (math.cos(angle + wiggle) * self.base_speed * lunge) + evade_x
        self.y += (math.sin(angle + wiggle) * self.base_speed * lunge) + evade_y

        self.history.insert(0, (self.x, self.y))
        max_h = self.num_segments * 3 + 12
        if len(self.history) > max_h:
            self.history = self.history[:max_h]

        # Venom spit mechanic
        self.spit_cd -= 1
        if self.spit_cd <= 0 and dist < 450:
            self.spit_cd = max(50, 160 - self.level * 2)
            new_proj_fn(self.x, self.y, tx, ty, damage=self.attack_power, color=(255, 60, 100), is_hostile=True)

    def update_manual(self, dx, dy):
        self.slither_t += 0.14
        self.x = max(50, min(WIDTH - 50, self.x + dx * self.base_speed))
        self.y = max(50, min(HEIGHT - 50, self.y + dy * self.base_speed))

        self.history.insert(0, (self.x, self.y))
        max_h = self.num_segments * 3 + 12
        if len(self.history) > max_h:
            self.history = self.history[:max_h]

    def draw(self, surface):
        step = 3
        for i in range(self.num_segments - 1, 0, -1):
            idx = min(len(self.history) - 1, i * step)
            sx, sy = self.history[idx]
            ratio = 1.0 - (i / self.num_segments)
            radius = int(max(3, (7 + ratio * 8) * self.tail_scale))

            col_dark = (25, 90, 45) if (i % 2 == 0) else (45, 140, 65)
            if self.is_player_controlled:
                col_dark = (160, 25, 55) if (i % 2 == 0) else (220, 50, 85)

            pygame.draw.circle(surface, col_dark, (int(sx), int(sy)), radius)
            pygame.draw.circle(surface, (140, 220, 100) if not self.is_player_controlled else (255, 130, 160), (int(sx), int(sy)), max(1, radius - 3))

        head_r = 16
        head_col = (130, 20, 30) if self.is_player_controlled else (20, 85, 40)
        pygame.draw.circle(surface, head_col, (int(self.x), int(self.y)), head_r)
        pygame.draw.circle(surface, (60, 170, 75) if not self.is_player_controlled else (220, 60, 80), (int(self.x), int(self.y)), head_r - 3)

        head_ang = math.atan2(self.y - self.history[4][1], self.x - self.history[4][0]) if len(self.history) > 4 else 0
        eye_off = 8
        e1 = (int(self.x + math.cos(head_ang + 0.8) * eye_off), int(self.y + math.sin(head_ang + 0.8) * eye_off))
        e2 = (int(self.x + math.cos(head_ang - 0.8) * eye_off), int(self.y + math.sin(head_ang - 0.8) * eye_off))
        pygame.draw.circle(surface, (255, 30, 30), e1, 3)
        pygame.draw.circle(surface, (255, 30, 30), e2, 3)

# ---------------------------------------------------------
# 7. MAIN ENGINE LOOP
# ---------------------------------------------------------
async def main():
    global audio_muted
    pygame.init()
    try:
        pygame.mixer.init()
    except Exception:
        pass

    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("MODIS NeonTail - Squirrel vs Viper")
    canvas = pygame.Surface((WIDTH, HEIGHT))
    clock = pygame.time.Clock()

    font_hud = pygame.font.SysFont("consolas", 14, bold=True)
    font_hud_sm = pygame.font.SysFont("consolas", 11, bold=True)
    font_big = pygame.font.SysFont("arial", 48, bold=True)

    # Audio with fail-safe initialization
    try:
        snd_boom = sfx_boom_audio()
        snd_pickup = sfx_pickup_audio()
    except Exception:
        snd_boom = snd_pickup = None

    # Background music (rebuilt when the mode or level tier changes)
    music_key = None
    music_sound = None
    music_cache = {}

    levelup_timer = 0
    levelup_text = ""

    game_mode = 1  # 1: Solo vs AI, 2: Dual Squirrel vs AI, 3: Squirrel vs Viper
    players = [SquirrelPlayer(WIDTH // 2 - 40, HEIGHT // 2, player_id=1, level=1)]
    high_score = get_stored_high_score()

    projectiles = []
    particles = []
    shards = []
    vipers = []

    shake_intensity = 0
    game_over = False

    def attack_sound(tool):
        play_sfx(get_attack_sfx(tool, game_mode, players[0].level))

    def spawn_venom(x, y, tx, ty, damage, color=(255, 50, 100), is_hostile=True, tool="ai_spit"):
        projectiles.append(Projectile(x, y, tx, ty, damage=damage, color=color, is_hostile=is_hostile, speed=10.0))
        attack_sound(tool)

    def sync_tier_level(target_level):
        nonlocal levelup_timer, levelup_text
        target_level = max(1, target_level)
        for p in players:
            p.apply_level_up(target_level)
        # Vipers get the exact same refreshed stats; they respawn at the new level
        vipers.clear()
        projectiles.clear()
        s = level_stats(target_level)
        levelup_text = f"LEVEL {target_level}  |  SQUIRREL = VIPER  HP {s['max_hp']}  DEF {s['max_defense']}  ATK {s['attack_power']}"
        levelup_timer = 150

    def get_tier_info(level):
        tier = (level - 1) // 5
        count = 1 + tier if game_mode != 3 else 1
        tail_scale = max(0.40, 1.0 - (tier * 0.05))
        return count, tail_scale

    def trigger_nova(p):
        if p.nova_cd <= 0:
            color = (0, 255, 230) if p.player_id == 1 else (100, 220, 255)
            for angle in range(0, 360, 24):
                rad = math.radians(angle)
                tx = p.x + math.cos(rad) * 200
                ty = p.y + math.sin(rad) * 200
                projectiles.append(Projectile(p.x, p.y, tx, ty, damage=p.attack_power, color=color, is_hostile=False))
            p.nova_cd = p.nova_max_cd
            attack_sound("p1_nova" if p.player_id == 1 else "p2_nova")

    running = True
    while running:
        current_level = players[0].level

        # Switch background music when mode or level tier changes
        wanted_key = (game_mode, sound_tier(current_level))
        if wanted_key != music_key:
            music_key = wanted_key
            if music_sound:
                music_sound.stop()
            if wanted_key not in music_cache:
                try:
                    music_cache[wanted_key] = build_music_loop(*wanted_key)
                except Exception:
                    music_cache[wanted_key] = None
            music_sound = music_cache[wanted_key]
            if music_sound:
                music_sound.set_volume(0.30)
                if not audio_muted:
                    music_sound.play(loops=-1)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_m:
                    audio_muted = not audio_muted
                    if music_sound:
                        if audio_muted:
                            music_sound.stop()
                        else:
                            music_sound.play(loops=-1)

                elif event.key == pygame.K_t:
                    game_mode = (game_mode % 3) + 1
                    players = [SquirrelPlayer(WIDTH // 2 - 40, HEIGHT // 2, player_id=1, level=current_level)]
                    if game_mode == 2:
                        players.append(SquirrelPlayer(WIDTH // 2 + 40, HEIGHT // 2, player_id=2, level=current_level))
                    sync_tier_level(current_level)
                    game_over = False

                elif event.key == pygame.K_r:
                    players = [SquirrelPlayer(WIDTH // 2 - 40, HEIGHT // 2, player_id=1, level=current_level)]
                    if game_mode == 2:
                        players.append(SquirrelPlayer(WIDTH // 2 + 40, HEIGHT // 2, player_id=2, level=current_level))
                    sync_tier_level(current_level)
                    game_over = False

                elif pygame.K_1 <= event.key <= pygame.K_9:
                    sync_tier_level((event.key - pygame.K_0) * 10)
                    game_over = False

                elif event.key == pygame.K_RIGHTBRACKET or event.key == pygame.K_PAGEUP:
                    sync_tier_level(((current_level // 10) + 1) * 10)
                    game_over = False

                elif event.key == pygame.K_LEFTBRACKET or event.key == pygame.K_PAGEDOWN:
                    target_lvl = max(1, ((current_level - 1) // 10) * 10)
                    sync_tier_level(target_lvl if target_lvl > 0 else 1)
                    game_over = False

                # Co-op Player 2 Blaster
                elif game_mode == 2 and not game_over and (event.key == pygame.K_RETURN or event.key == pygame.K_RCTRL):
                    p2 = players[1]
                    mx = p2.x + (150 if p2.facing_right else -150)
                    projectiles.append(Projectile(p2.x, p2.y, mx, p2.y, damage=p2.attack_power, color=(100, 220, 255), is_hostile=False))
                    attack_sound("p2_laser")

                # Co-op Player 2 Nova
                elif game_mode == 2 and not game_over and event.key == pygame.K_RSHIFT:
                    if players[1].hp > 0:
                        trigger_nova(players[1])

                # PvP Viper Spit (Player 2)
                elif game_mode == 3 and not game_over and (event.key in (pygame.K_RCTRL, pygame.K_KP0, pygame.K_RETURN)):
                    if len(vipers) > 0:
                        v = vipers[0]
                        spawn_venom(v.x, v.y, players[0].x, players[0].y, damage=v.attack_power, color=(255, 60, 100), is_hostile=True, tool="pvp_spit")

                elif not game_over:
                    if event.key == pygame.K_SPACE:
                        mx, my = pygame.mouse.get_pos()
                        projectiles.append(Projectile(players[0].x, players[0].y, mx, my, damage=players[0].attack_power, color=(0, 255, 230), is_hostile=False))
                        attack_sound("p1_laser")
                    elif event.key == pygame.K_e:
                        trigger_nova(players[0])

            elif event.type == pygame.MOUSEBUTTONDOWN and not game_over:
                if event.button == 1:
                    mx, my = pygame.mouse.get_pos()
                    projectiles.append(Projectile(players[0].x, players[0].y, mx, my, damage=players[0].attack_power, color=(0, 255, 230), is_hostile=False))
                    attack_sound("p1_laser")
                elif event.button == 3:
                    trigger_nova(players[0])

        if not game_over:
            keys = pygame.key.get_pressed()

            # P1 Controls (WASD)
            if players[0].hp > 0:
                dx1 = (keys[pygame.K_d]) - (keys[pygame.K_a])
                dy1 = (keys[pygame.K_s]) - (keys[pygame.K_w])
                players[0].move(dx1, dy1)
                players[0].update()

            # P2 Controls (Arrows)
            if game_mode == 2 and len(players) > 1 and players[1].hp > 0:
                dx2 = (keys[pygame.K_RIGHT]) - (keys[pygame.K_LEFT])
                dy2 = (keys[pygame.K_DOWN]) - (keys[pygame.K_UP])
                players[1].move(dx2, dy2)
                players[1].update()

            target_viper_count, current_tail_scale = get_tier_info(current_level)

            # Spawn Vipers
            while len(vipers) < target_viper_count:
                vipers.append(ViperEnemy(
                    tail_scale=current_tail_scale,
                    level=current_level,
                    is_player_controlled=(game_mode == 3)
                ))

            # Update Projectiles
            for p in projectiles[:]:
                p.update()
                if not p.alive:
                    projectiles.remove(p)

            # Update Energy Shards
            for s in shards[:]:
                s.update()
                if s.life <= 0:
                    shards.remove(s)
                else:
                    for p in players:
                        if p.hp > 0 and math.hypot(s.x - p.x, s.y - p.y) < 26:
                            p.defense = min(p.max_defense, p.defense + 30)
                            p.hp = min(p.max_hp, p.hp + 20)
                            p.score += 100
                            if p.score > high_score:
                                high_score = p.score
                                save_stored_high_score(high_score)
                            shards.remove(s)
                            play_sfx(snd_pickup)
                            break

            # Update Particles
            for part in particles[:]:
                part.update()
                if part.life <= 0:
                    particles.remove(part)

            # Update Vipers
            for viper in vipers[:]:
                if game_mode == 3:
                    sdx = (keys[pygame.K_RIGHT]) - (keys[pygame.K_LEFT])
                    sdy = (keys[pygame.K_DOWN]) - (keys[pygame.K_UP])
                    viper.update_manual(sdx, sdy)
                else:
                    viper.update_ai(players, projectiles, spawn_venom)

                # Projectile vs Viper
                for p in projectiles[:]:
                    if not p.is_hostile:
                        hit = False
                        if math.hypot(p.x - viper.x, p.y - viper.y) < 18:
                            hit = True
                            viper.take_damage(p.damage)
                        else:
                            for seg_idx in range(3, min(len(viper.history), 18), 3):
                                sx, sy = viper.history[seg_idx]
                                if math.hypot(p.x - sx, p.y - sy) < max(8.0, 14 * viper.tail_scale):
                                    hit = True
                                    viper.take_damage(p.damage // 2)
                                    break

                        if hit:
                            if p in projectiles:
                                projectiles.remove(p)
                            for _ in range(5):
                                particles.append(Particle(p.x, p.y, (80, 255, 120)))
                            shake_intensity = max(shake_intensity, 3)

                            if viper.hp <= 0:
                                if viper in vipers:
                                    vipers.remove(viper)
                                for _ in range(16):
                                    particles.append(Particle(viper.x, viper.y, (60, 220, 90)))
                                if random.random() < 0.40:
                                    shards.append(Shard(viper.x, viper.y))

                                players[0].score += int(250 * (2.0 - viper.tail_scale))
                                players[0].kills += 1
                                if players[0].score > high_score:
                                    high_score = players[0].score
                                    save_stored_high_score(high_score)
                                play_sfx(snd_boom)

                                if players[0].kills > 0 and players[0].kills % 5 == 0:
                                    sync_tier_level(players[0].level + 1)
                                break

                # Viper Melee Strike vs Players
                for p in players:
                    if p.hp > 0 and math.hypot(viper.x - p.x, viper.y - p.y) < 28:
                        p.take_damage(viper.attack_power)
                        attack_sound("pvp_bite" if viper.is_player_controlled else "ai_bite")
                        shake_intensity = max(shake_intensity, 9)
                        for _ in range(8):
                            particles.append(Particle(p.x, p.y, (255, 60, 80)))
                        viper.x += (-50 if viper.x < p.x else 50)
                        viper.y += (-50 if viper.y < p.y else 50)

            # Hostile Venom vs Players
            for p in projectiles[:]:
                if p.is_hostile:
                    for ply in players:
                        if ply.hp > 0 and math.hypot(p.x - ply.x, p.y - ply.y) < 22:
                            ply.take_damage(p.damage)
                            attack_sound("pvp_bite" if game_mode == 3 else "ai_bite")
                            shake_intensity = max(shake_intensity, 6)
                            if p in projectiles:
                                projectiles.remove(p)
                            for _ in range(6):
                                particles.append(Particle(ply.x, ply.y, (255, 80, 120)))
                            break

            # Defeat Check
            if all(p.hp <= 0 for p in players):
                game_over = True
                if players[0].score > high_score:
                    high_score = players[0].score
                    save_stored_high_score(high_score)

        # ---------------- RENDER ----------------
        canvas.fill((9, 12, 22))

        # Ambient Grid
        for gx in range(0, WIDTH, 80):
            pygame.draw.line(canvas, (18, 25, 42), (gx, 0), (gx, HEIGHT), 1)
        for gy in range(0, HEIGHT, 80):
            pygame.draw.line(canvas, (18, 25, 42), (0, gy), (WIDTH, gy), 1)

        for s in shards:
            s.draw(canvas)
        for p in projectiles:
            p.draw(canvas)
        for part in particles:
            part.draw(canvas)
        for viper in vipers:
            viper.draw(canvas)
        for p in players:
            if p.hp > 0:
                p.draw(canvas)

        if not game_over:
            mx, my = pygame.mouse.get_pos()
            pygame.draw.circle(canvas, (0, 255, 230), (mx, my), 7, 1)
            pygame.draw.line(canvas, (0, 255, 230), (mx - 10, my), (mx + 10, my), 1)
            pygame.draw.line(canvas, (0, 255, 230), (mx, my - 10), (mx, my + 10), 1)

        # --- HUD METERS ---
        p1 = players[0]
        # P1 Health
        hp_ratio = max(0.0, p1.hp / p1.max_hp)
        pygame.draw.rect(canvas, (35, 15, 20), (25, 20, 190, 12))
        pygame.draw.rect(canvas, (255, 55, 75), (25, 20, int(190 * hp_ratio), 12))
        pygame.draw.rect(canvas, (255, 160, 175), (25, 20, 190, 12), 1)
        canvas.blit(font_hud_sm.render(f"P1 HP {p1.hp}/{p1.max_hp}", True, (255, 220, 230)), (30, 20))

        # P1 Defense
        def_ratio = max(0.0, p1.defense / p1.max_defense)
        pygame.draw.rect(canvas, (15, 25, 40), (25, 38, 190, 10))
        pygame.draw.rect(canvas, (0, 215, 255), (25, 38, int(190 * def_ratio), 10))
        pygame.draw.rect(canvas, (180, 240, 255), (25, 38, 190, 10), 1)
        canvas.blit(font_hud_sm.render(f"P1 DEFENSE {p1.defense}/{p1.max_defense}", True, (210, 255, 255)), (30, 37))

        # Nova Cooldown
        nova_ratio = 1.0 - (p1.nova_cd / p1.nova_max_cd)
        pygame.draw.rect(canvas, (25, 30, 20), (25, 54, 190, 8))
        pygame.draw.rect(canvas, (0, 255, 170) if p1.nova_cd == 0 else (120, 160, 90), (25, 54, int(190 * nova_ratio), 8))
        pygame.draw.rect(canvas, (160, 255, 200), (25, 54, 190, 8), 1)

        # Mode Indicator
        mode_names = {1: "SOLO vs AI", 2: "DUAL SQUIRREL vs AI", 3: "SQUIRREL vs VIPER (PVP)"}
        canvas.blit(font_hud.render(f"MODE: {mode_names[game_mode]} [T: SWITCH]", True, (255, 200, 80)), (25, 70))

        target_count, current_tail_scale = get_tier_info(current_level)
        canvas.blit(font_hud.render(f"VIPERS: {len(vipers)} (SCALE: {int(current_tail_scale * 100)}%)", True, (80, 255, 120)), (25, 90))
        canvas.blit(font_hud.render(f"LEVEL: {current_level} | ATK: {p1.attack_power}", True, (255, 205, 50)), (WIDTH // 2 - 80, 20))
        canvas.blit(font_hud.render(f"SCORE: {p1.score}", True, (220, 220, 220)), (WIDTH - 220, 20))
        canvas.blit(font_hud.render(f"HI-SCORE: {high_score}", True, (255, 215, 0)), (WIDTH - 220, 40))

        # Viper HP / Defense (same scale as the squirrel at every level)
        if vipers:
            v0 = vipers[0]
            vx0 = WIDTH - 220
            v_hp_ratio = max(0.0, v0.hp / v0.max_hp)
            pygame.draw.rect(canvas, (35, 15, 20), (vx0, 62, 190, 12))
            pygame.draw.rect(canvas, (80, 220, 110), (vx0, 62, int(190 * v_hp_ratio), 12))
            pygame.draw.rect(canvas, (160, 255, 180), (vx0, 62, 190, 12), 1)
            canvas.blit(font_hud_sm.render(f"VIPER HP {v0.hp}/{v0.max_hp}", True, (230, 255, 230)), (vx0 + 5, 62))
            v_def_ratio = max(0.0, v0.defense / v0.max_defense)
            pygame.draw.rect(canvas, (15, 25, 40), (vx0, 80, 190, 10))
            pygame.draw.rect(canvas, (0, 215, 255), (vx0, 80, int(190 * v_def_ratio), 10))
            pygame.draw.rect(canvas, (180, 240, 255), (vx0, 80, 190, 10), 1)
            canvas.blit(font_hud_sm.render(f"VIPER DEFENSE {v0.defense}/{v0.max_defense}", True, (210, 255, 255)), (vx0 + 5, 79))
            canvas.blit(font_hud_sm.render(f"VIPER ATK {v0.attack_power}", True, (255, 205, 50)), (vx0 + 5, 94))

        if levelup_timer > 0:
            levelup_timer -= 1
            banner = font_hud.render(levelup_text, True, (255, 230, 90))
            canvas.blit(banner, banner.get_rect(center=(WIDTH // 2, 60)))

        controls_str = "[P1: WASD+SPACE+E] [P2: ARROWS+ENTER+RSHIFT] [PVP VIPER: ARROWS+RCTRL/ENTER] [T: MODE] [R: RESET] [M: MUTE]"
        canvas.blit(font_hud.render(controls_str, True, (0, 215, 255)), (25, HEIGHT - 35))

        if game_over:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((8, 10, 22, 215))
            canvas.blit(overlay, (0, 0))

            txt_over = font_big.render("MISSION FAILED", True, (255, 60, 80))
            txt_stats = font_hud.render(f"LEVEL {current_level} | SCORE: {p1.score} | BEST: {high_score}", True, (220, 220, 220))
            txt_restart = font_hud.render("PRESS [R] TO RESTART  |  PRESS [1-9] TO WARP", True, (0, 255, 220))

            canvas.blit(txt_over, txt_over.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 35)))
            canvas.blit(txt_stats, txt_stats.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 15)))
            canvas.blit(txt_restart, txt_restart.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 55)))

        ox, oy = 0, 0
        if shake_intensity > 0:
            ox = random.randint(-shake_intensity, shake_intensity)
            oy = random.randint(-shake_intensity, shake_intensity)
            shake_intensity = max(0, shake_intensity - 1)

        screen.fill((5, 6, 13))
        screen.blit(canvas, (ox, oy))

        pygame.display.flip()
        clock.tick(60)
        await asyncio.sleep(0)

if __name__ == "__main__":
    asyncio.run(main())