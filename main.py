import sys
import math
import random
import struct
import asyncio
from array import array
import pygame

GAME_VERSION = "v4 NO BG MUSIC"

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

SHOT_SPEED = 12.0      # Squirrel laser and viper venom travel at the same speed
HIT_RADIUS = 20        # Same hit size for squirrel body and viper head
CONTACT_RADIUS = 30    # Squirrel and viper touching = both take a hit
SHARD_BOOST = 1.25         # Picking up a shard: +25% attack...
SHARD_BOOST_FRAMES = 600   # ...for 10 seconds (60 FPS), for whoever grabs it
SHARD_SPAWN_FRAMES = 420   # A new shard appears every 7 seconds (max 2 on screen)

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
# 3. CLEAN MUSICAL AUDIO (16-bit PCM, no white noise)
# ---------------------------------------------------------
audio_muted = False
SFX_RATE = 22050

def pcm16_sound(samples, rate):
    """Wraps 16-bit mono PCM samples in a RIFF WAV container (works in the browser build too)."""
    data = array("h", samples).tobytes()
    header = bytearray()
    header.extend(b"RIFF")
    header.extend(struct.pack("<I", 36 + len(data)))
    header.extend(b"WAVEfmt ")
    header.extend(struct.pack("<I", 16))
    header.extend(struct.pack("<H", 1))            # PCM
    header.extend(struct.pack("<H", 1))            # mono
    header.extend(struct.pack("<I", rate))
    header.extend(struct.pack("<I", rate * 2))     # byte rate
    header.extend(struct.pack("<H", 2))            # block align
    header.extend(struct.pack("<H", 16))           # 16-bit
    header.extend(b"data")
    header.extend(struct.pack("<I", len(data)))
    try:
        return pygame.mixer.Sound(buffer=bytes(header + data))
    except Exception:
        return None

def render_sound(duration, fn, rate=SFX_RATE, peak=0.6):
    """Renders fn(t) into a normalised, click-free sound (short fade in/out, never clips)."""
    n = max(1, int(rate * duration))
    buf = [fn(i / rate) for i in range(n)]
    top = max(1e-6, max(abs(v) for v in buf))
    scale = peak * 32767 / top
    fade_in = max(1, int(rate * 0.004))
    fade_out = max(1, int(rate * 0.015))
    out = []
    for i, v in enumerate(buf):
        g = 1.0
        if i < fade_in:
            g = i / fade_in
        elif i > n - fade_out:
            g = (n - i) / fade_out
        out.append(int(v * scale * g))
    return pcm16_sound(out, rate)

TWO_PI = 2 * math.pi

def voice(name, f, t):
    """One musical note of the given instrument, t seconds after it starts."""
    w = TWO_PI * t
    if name == "bell":
        return (math.sin(w * f) + 0.35 * math.sin(w * f * 2.76) * math.exp(-t * 10)
                + 0.12 * math.sin(w * f * 5.4) * math.exp(-t * 22)) * math.exp(-t * 6)
    if name == "pluck":
        return (math.sin(w * f) + 0.3 * math.sin(w * f * 2) + 0.12 * math.sin(w * f * 3)) * math.exp(-t * 13)
    if name == "pad":
        return (math.sin(w * f) + 0.6 * math.sin(w * f * 1.004) + 0.2 * math.sin(w * f * 2)) * min(1.0, t * 40) * math.exp(-t * 4)
    if name == "marimba":
        return (math.sin(w * f) + 0.5 * math.sin(w * f * 4) * math.exp(-t * 40)) * math.exp(-t * 10)
    if name == "reed":
        vib = 0.25 * math.sin(w * 6)
        return (math.sin(w * f + vib) + 0.3 * math.sin(3 * (w * f + vib)) + 0.12 * math.sin(5 * (w * f + vib))) * min(1.0, t * 60) * math.exp(-t * 7)
    if name == "fm":
        return math.sin(w * f + 2.0 * math.exp(-t * 8) * math.sin(w * f * 2)) * math.exp(-t * 7)
    if name == "drum":
        phase = TWO_PI * (f * t + f * 2.0 * (1.0 - math.exp(-t * 30)) / 30.0)
        return math.sin(phase) * math.exp(-t * 16)
    return math.sin(w * f) * math.exp(-t * 8)

# Each game mode has its own musical scale (semitones)
MODE_SCALES = {
    1: [0, 2, 4, 7, 9],           # Solo vs AI: bright pentatonic
    2: [0, 2, 4, 5, 7, 9, 11],    # Dual squirrels vs AI: major
    3: [0, 2, 3, 5, 7, 8, 10],    # Squirrel vs Viper: minor (tense)
}

# ...and its own key, so the same tool never sounds the same in two modes
MODE_KEYS = {1: 0, 2: 5, 3: -3}

# Every attacking tool plays its own little tune: (instrument, base Hz, [(scale step, seconds), ...])
ATTACK_TUNES = {
    "sq1_shot":  ("bell",    523.25, [(0, 0.05), (4, 0.09)]),                          # P1 squirrel laser
    "sq1_nova":  ("pad",     392.00, [(0, 0.05), (2, 0.05), (4, 0.05), (7, 0.20)]),    # P1 squirrel nova
    "sq2_shot":  ("pluck",   587.33, [(2, 0.05), (5, 0.09)]),                          # P2 squirrel blaster
    "sq2_nova":  ("marimba", 440.00, [(7, 0.05), (5, 0.05), (3, 0.05), (0, 0.20)]),    # P2 squirrel nova
    "vp_spit":   ("reed",    196.00, [(1, 0.07), (0, 0.11)]),                          # viper venom spit
    "vp_burst":  ("fm",      146.83, [(0, 0.07), (2, 0.07), (4, 0.18)]),               # viper venom burst
    "vp_bite":   ("drum",    150.00, [(0, 0.14)]),                                     # squirrel/viper clash
}
# In Squirrel vs Viper the human-controlled viper gets its own instruments
PVP_INSTRUMENTS = {"vp_spit": "marimba", "vp_burst": "bell", "vp_bite": "drum"}

def sound_tier(level):
    """Attack tunes move up a step every 3 levels (0-11)."""
    return max(0, min(11, (max(1, level) - 1) // 3))

def render_tune(instrument, base, notes, scale, transpose, tempo):
    starts = []
    t0 = 0.0
    for step, dur in notes:
        semi = scale[step % len(scale)] + 12 * (step // len(scale)) + transpose
        starts.append((t0, base * 2 ** (semi / 12.0)))
        t0 += dur * tempo
    ring = 0.18
    total = t0 + ring

    def fn(t):
        v = 0.0
        for st, fr in starts:
            lt = t - st
            if 0.0 <= lt < ring + 0.25:
                v += voice(instrument, fr, lt)
        return v

    return render_sound(total, fn)

_attack_sfx_cache = {}

def get_attack_sfx(tool, mode, level):
    """Unique tune per (attack tool, game mode, level tier), built once and cached."""
    tier = sound_tier(level)
    key = (tool, mode, tier)
    if key not in _attack_sfx_cache:
        instrument, base, notes = ATTACK_TUNES[tool]
        if mode == 3 and tool in PVP_INSTRUMENTS:
            instrument = PVP_INSTRUMENTS[tool]
        try:
            _attack_sfx_cache[key] = render_tune(instrument, base, notes, MODE_SCALES.get(mode, MODE_SCALES[1]),
                                                 transpose=tier + MODE_KEYS.get(mode, 0), tempo=max(0.7, 1.0 - tier * 0.025))
        except Exception:
            _attack_sfx_cache[key] = None
    return _attack_sfx_cache[key]

def sfx_boom_audio():
    # Enemy defeat: soft descending chime
    return render_sound(0.35, lambda t: voice("bell", 330 - t * 300, t) + 0.5 * voice("drum", 90, t))

def sfx_pickup_audio():
    # Energy shard absorption: rising sparkle
    return render_sound(0.25, lambda t: voice("bell", 880 * (1 + t * 2), t))

def sfx_round_audio():
    # Round / level win fanfare
    notes = [(523.25, 0.0), (659.25, 0.1), (783.99, 0.2), (1046.5, 0.3)]
    return render_sound(0.75, lambda t: sum(voice("bell", f, t - s) for f, s in notes if t >= s))

def play_sfx(sfx):
    if sfx and not audio_muted:
        try:
            sfx.play()
        except Exception:
            pass

# ---------------------------------------------------------
# 4. PROJECTILES, PARTICLES & ENERGY SHARDS
# ---------------------------------------------------------
class Projectile:
    def __init__(self, x, y, tx, ty, damage=40, color=(0, 255, 230), is_hostile=False, speed=SHOT_SPEED, owner=None):
        self.x = float(x)
        self.y = float(y)
        angle = math.atan2(ty - y, tx - x)
        self.speed = speed
        self.vx = math.cos(angle) * self.speed
        self.vy = math.sin(angle) * self.speed
        self.damage = damage
        self.color = color
        self.is_hostile = is_hostile
        self.owner = owner
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
        self.x = float(max(40, min(WIDTH - 40, x)))
        self.y = float(max(40, min(HEIGHT - 40, y)))
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
# 5. SHARED FIGHTER STATS (squirrel and viper always identical)
# ---------------------------------------------------------
def level_stats(level):
    level = max(1, level)
    return {
        "max_hp": 300 + (level - 1) * 35,
        "max_defense": 100 + (level - 1) * 20,
        "attack_power": 35 + (level - 1) * 4,
        "shot_cd": max(6, 14 - level // 5),             # frames between normal shots
        "special_cd": max(70, 180 - level * 3),         # frames between nova / venom burst
    }

def fighter_speed(level):
    return 6.8 + min(3.0, (max(1, level) - 1) * 0.06)

class Fighter:
    """Everything combat-related lives here, so squirrel and viper can never drift apart."""

    def apply_level_up(self, level):
        self.level = max(1, level)
        s = level_stats(self.level)
        self.max_hp = s["max_hp"]
        self.max_defense = s["max_defense"]
        self.attack_power = s["attack_power"]
        self.shot_cd = s["shot_cd"]
        self.special_cd = s["special_cd"]
        self.shot_timer = 0
        self.special_timer = 0
        self.contact_timer = 0
        self.boost_timer = 0
        self.refill()

    def power(self):
        """Attack damage right now: +25% while a shard power-up is active (same rule for both sides)."""
        return int(self.attack_power * SHARD_BOOST) if self.boost_timer > 0 else self.attack_power

    def collect_shard(self):
        self.boost_timer = SHARD_BOOST_FRAMES
        self.defense = min(self.max_defense, self.defense + 30)
        self.hp = min(self.max_hp, self.hp + 20)

    def refill(self):
        self.hp = self.max_hp
        self.defense = self.max_defense

    def take_damage(self, amount):
        if self.defense > 0:
            absorbed = min(self.defense, amount)
            self.defense -= absorbed
            amount -= absorbed
        self.hp = max(0, self.hp - amount)

    def tick_timers(self):
        if self.shot_timer > 0:
            self.shot_timer -= 1
        if self.special_timer > 0:
            self.special_timer -= 1
        if self.contact_timer > 0:
            self.contact_timer -= 1
        if self.boost_timer > 0:
            self.boost_timer -= 1

    def try_shot(self):
        if self.hp <= 0 or self.shot_timer > 0:
            return False
        self.shot_timer = self.shot_cd
        return True

    def try_special(self):
        if self.hp <= 0 or self.special_timer > 0:
            return False
        self.special_timer = self.special_cd
        return True

# ---------------------------------------------------------
# 6. SQUIRREL
# ---------------------------------------------------------
class SquirrelPlayer(Fighter):
    def __init__(self, x, y, player_id=1, level=1):
        self.player_id = player_id
        self.x = float(x)
        self.y = float(y)
        self.score = 0
        self.kills = 0
        self.facing_right = True
        self.anim_t = 0.0
        self.apply_level_up(level)

    def apply_level_up(self, level):
        super().apply_level_up(level)
        self.speed = fighter_speed(self.level)

    def move(self, dx, dy):
        if dx > 0:
            self.facing_right = True
        elif dx < 0:
            self.facing_right = False
        self.x = max(50, min(WIDTH - 50, self.x + dx * self.speed))
        self.y = max(50, min(HEIGHT - 50, self.y + dy * self.speed))

    def update(self):
        self.anim_t += 0.15
        self.tick_timers()

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
# 7. VIPER
# ---------------------------------------------------------
class ViperEnemy(Fighter):
    def __init__(self, level=1, is_player_controlled=False, spawn=None):
        self.is_player_controlled = is_player_controlled
        self.tail_scale = 1.0   # tail never shrinks, so the viper never gets harder to hit

        if spawn is not None:
            self.x, self.y = float(spawn[0]), float(spawn[1])
        else:
            side = random.choice(["L", "R", "T", "B"])
            if side == "L":
                self.x, self.y = -60.0, random.uniform(80, HEIGHT - 80)
            elif side == "R":
                self.x, self.y = float(WIDTH + 60), random.uniform(80, HEIGHT - 80)
            elif side == "T":
                self.x, self.y = random.uniform(80, WIDTH - 80), -60.0
            else:
                self.x, self.y = random.uniform(80, WIDTH - 80), float(HEIGHT + 60)

        self.num_segments = 24
        self.history = [(self.x, self.y) for _ in range(self.num_segments * 3 + 12)]
        self.heading = math.pi if self.x > WIDTH / 2 else 0.0
        self.slither_t = random.uniform(0, 10)
        self.ai_fire_wait = random.randint(40, 90)
        self.last_hit_by = None
        self.apply_level_up(level)

    def apply_level_up(self, level):
        super().apply_level_up(level)
        if self.is_player_controlled:
            self.base_speed = fighter_speed(self.level)   # human viper moves exactly like the squirrel
        else:
            self.base_speed = 3.0 + min(3.5, (self.level - 1) * 0.05)

    def _push_history(self):
        self.history.insert(0, (self.x, self.y))
        max_h = self.num_segments * 3 + 12
        if len(self.history) > max_h:
            self.history = self.history[:max_h]

    def update_ai(self, targets, projectiles_list, spit_fn, burst_fn, shards=()):
        self.slither_t += 0.14
        self.tick_timers()
        active_targets = [t for t in targets if t.hp > 0]
        if not active_targets:
            return

        closest_target = min(active_targets, key=lambda t: math.hypot(t.x - self.x, t.y - self.y))
        tx, ty = closest_target.x, closest_target.y
        dist = math.hypot(tx - self.x, ty - self.y)

        # Race the squirrel for power-up shards, just like a player would
        move_x, move_y = tx, ty
        if shards and self.boost_timer <= 0:
            near = min(shards, key=lambda s: math.hypot(s.x - self.x, s.y - self.y))
            d_s = math.hypot(near.x - self.x, near.y - self.y)
            if d_s < 320 and d_s < dist:
                move_x, move_y = near.x, near.y

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
        angle = math.atan2(move_y - self.y, move_x - self.x)
        wiggle = math.sin(self.slither_t) * 0.70
        self.heading = angle

        self.x += (math.cos(angle + wiggle) * self.base_speed * lunge) + evade_x
        self.y += (math.sin(angle + wiggle) * self.base_speed * lunge) + evade_y
        self._push_history()

        # Same weapons and cooldowns as the squirrel; the AI just chooses to fire less often
        self.ai_fire_wait -= 1
        if dist < 220 and self.special_timer <= 0:
            burst_fn(self)
        elif self.ai_fire_wait <= 0 and dist < 450:
            self.ai_fire_wait = self.shot_cd * 4 + random.randint(0, 30)
            spit_fn(self, tx, ty)

    def update_manual(self, dx, dy):
        self.slither_t += 0.14
        self.tick_timers()
        if dx or dy:
            self.heading = math.atan2(dy, dx)
        self.x = max(50, min(WIDTH - 50, self.x + dx * self.base_speed))
        self.y = max(50, min(HEIGHT - 50, self.y + dy * self.base_speed))
        self._push_history()

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

        head_ang = self.heading
        eye_off = 8
        e1 = (int(self.x + math.cos(head_ang + 0.8) * eye_off), int(self.y + math.sin(head_ang + 0.8) * eye_off))
        e2 = (int(self.x + math.cos(head_ang - 0.8) * eye_off), int(self.y + math.sin(head_ang - 0.8) * eye_off))
        pygame.draw.circle(surface, (255, 30, 30), e1, 3)
        pygame.draw.circle(surface, (255, 30, 30), e2, 3)

# ---------------------------------------------------------
# 8. MAIN ENGINE LOOP
# ---------------------------------------------------------
async def main():
    global audio_muted
    try:
        pygame.mixer.pre_init(44100, -16, 2, 512)
    except Exception:
        pass
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

    try:
        snd_boom = sfx_boom_audio()
        snd_pickup = sfx_pickup_audio()
        snd_round = sfx_round_audio()
    except Exception:
        snd_boom = snd_pickup = snd_round = None

    tune_key = None

    game_mode = 1  # 1: Solo vs AI, 2: Dual Squirrel vs AI, 3: Squirrel vs Viper
    level_state = {"level": 1, "kills": 0}
    players = []
    vipers = []
    projectiles = []
    particles = []
    shards = []
    high_score = get_stored_high_score()
    pvp_wins = {"squirrel": 0, "viper": 0}
    banner = {"text": "", "timer": 0}
    shard_clock = {"t": 0}

    shake_intensity = 0
    game_over = False

    def show_banner(text):
        banner["text"] = text
        banner["timer"] = 170

    def attack_sound(tool):
        play_sfx(get_attack_sfx(tool, game_mode, level_state["level"]))

    def build_players(level):
        if game_mode == 3:
            new = [SquirrelPlayer(220, HEIGHT // 2, player_id=1, level=level)]
        else:
            new = [SquirrelPlayer(WIDTH // 2 - 40, HEIGHT // 2, player_id=1, level=level)]
            if game_mode == 2:
                new.append(SquirrelPlayer(WIDTH // 2 + 40, HEIGHT // 2, player_id=2, level=level))
        players[:] = new

    def start_level(level, message=None):
        """Everyone (squirrels and vipers) starts the level with the same full stats."""
        level = max(1, level)
        level_state["level"] = level
        for p in players:
            p.apply_level_up(level)
            if game_mode == 3:
                p.x, p.y = 220.0, float(HEIGHT // 2)
        vipers.clear()
        projectiles.clear()
        shards.clear()
        s = level_stats(level)
        show_banner(message or f"LEVEL {level}  |  SQUIRREL = VIPER   HP {s['max_hp']}   DEF {s['max_defense']}   ATK {s['attack_power']}")

    def reset_game(level):
        nonlocal game_over
        build_players(level)
        level_state["kills"] = 0
        start_level(level)
        game_over = False

    def viper_target_count():
        # One viper per living squirrel: never outnumbered
        return 1 if game_mode == 3 else max(1, sum(1 for p in players if p.hp > 0))

    def squirrel_shot(p, tx, ty):
        if p.try_shot():
            color = (0, 255, 230) if p.player_id == 1 else (100, 220, 255)
            projectiles.append(Projectile(p.x, p.y, tx, ty, damage=p.power(), color=color, is_hostile=False, owner=p))
            attack_sound("sq1_shot" if p.player_id == 1 else "sq2_shot")

    def squirrel_nova(p):
        if p.try_special():
            color = (0, 255, 230) if p.player_id == 1 else (100, 220, 255)
            for angle in range(0, 360, 24):
                rad = math.radians(angle)
                projectiles.append(Projectile(p.x, p.y, p.x + math.cos(rad) * 200, p.y + math.sin(rad) * 200,
                                              damage=p.power(), color=color, is_hostile=False, owner=p))
            attack_sound("sq1_nova" if p.player_id == 1 else "sq2_nova")

    def viper_spit(v, tx, ty):
        if v.try_shot():
            projectiles.append(Projectile(v.x, v.y, tx, ty, damage=v.power(), color=(255, 60, 100), is_hostile=True, owner=v))
            attack_sound("vp_spit")

    def viper_burst(v):
        if v.try_special():
            for angle in range(0, 360, 24):
                rad = math.radians(angle)
                projectiles.append(Projectile(v.x, v.y, v.x + math.cos(rad) * 200, v.y + math.sin(rad) * 200,
                                              damage=v.power(), color=(255, 120, 60), is_hostile=True, owner=v))
            attack_sound("vp_burst")

    def update_high_score(score):
        nonlocal high_score
        if score > high_score:
            high_score = score
            save_stored_high_score(high_score)

    def pvp_round_over(winner):
        pvp_wins[winner] += 1
        play_sfx(snd_round)
        start_level(level_state["level"] + 1,
                    f"{winner.upper()} WINS THE ROUND!  NEXT: LEVEL {level_state['level'] + 1}  (both refilled, equal stats)")

    def viper_defeated(viper):
        if viper in vipers:
            vipers.remove(viper)
        for _ in range(16):
            particles.append(Particle(viper.x, viper.y, (60, 220, 90)))
        play_sfx(snd_boom)
        if game_mode == 3:
            pvp_round_over("squirrel")
            return
        if random.random() < 0.40:
            shards.append(Shard(viper.x, viper.y))
        killer = viper.last_hit_by if viper.last_hit_by in players else players[0]
        killer.score += 250
        killer.kills += 1
        update_high_score(killer.score)
        level_state["kills"] += 1
        if level_state["kills"] % 5 == 0:
            play_sfx(snd_round)
            start_level(level_state["level"] + 1)
        else:
            # Fair fights: the next duel starts with everyone back at full strength
            for f in players + vipers:
                if f.hp > 0:
                    f.refill()

    reset_game(1)

    running = True
    while running:
        current_level = level_state["level"]

        # Mode or level tier changed: pre-build attack tunes so the first shot doesn't stutter
        wanted_key = (game_mode, sound_tier(current_level))
        if wanted_key != tune_key:
            tune_key = wanted_key
            for tool in ATTACK_TUNES:
                get_attack_sfx(tool, game_mode, current_level)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_m:
                    audio_muted = not audio_muted

                elif event.key == pygame.K_t:
                    game_mode = (game_mode % 3) + 1
                    pvp_wins["squirrel"] = pvp_wins["viper"] = 0
                    reset_game(current_level)

                elif event.key == pygame.K_r:
                    reset_game(current_level)

                elif pygame.K_1 <= event.key <= pygame.K_9:
                    start_level((event.key - pygame.K_0) * 10)
                    game_over = False

                elif event.key == pygame.K_RIGHTBRACKET or event.key == pygame.K_PAGEUP:
                    start_level(((current_level // 10) + 1) * 10)
                    game_over = False

                elif event.key == pygame.K_LEFTBRACKET or event.key == pygame.K_PAGEDOWN:
                    start_level(max(1, ((current_level - 1) // 10) * 10))
                    game_over = False

                elif game_over:
                    pass

                # Co-op Player 2 (arrows + ENTER blaster + RSHIFT nova)
                elif game_mode == 2 and event.key in (pygame.K_RETURN, pygame.K_RCTRL):
                    p2 = players[1]
                    squirrel_shot(p2, p2.x + (150 if p2.facing_right else -150), p2.y)
                elif game_mode == 2 and event.key == pygame.K_RSHIFT:
                    squirrel_nova(players[1])

                # PvP viper (arrows + RCTRL/ENTER spit in its heading + RSHIFT burst)
                elif game_mode == 3 and event.key in (pygame.K_RCTRL, pygame.K_KP0, pygame.K_RETURN):
                    if vipers:
                        v = vipers[0]
                        viper_spit(v, v.x + math.cos(v.heading) * 150, v.y + math.sin(v.heading) * 150)
                elif game_mode == 3 and event.key == pygame.K_RSHIFT:
                    if vipers:
                        viper_burst(vipers[0])

                elif event.key == pygame.K_SPACE:
                    mx, my = pygame.mouse.get_pos()
                    squirrel_shot(players[0], mx, my)
                elif event.key == pygame.K_e:
                    squirrel_nova(players[0])

            elif event.type == pygame.MOUSEBUTTONDOWN and not game_over:
                if event.button == 1:
                    mx, my = pygame.mouse.get_pos()
                    squirrel_shot(players[0], mx, my)
                elif event.button == 3:
                    squirrel_nova(players[0])

        if not game_over:
            keys = pygame.key.get_pressed()

            # P1 Controls (WASD)
            if players[0].hp > 0:
                players[0].move(keys[pygame.K_d] - keys[pygame.K_a], keys[pygame.K_s] - keys[pygame.K_w])
                players[0].update()

            # P2 Controls (Arrows)
            if game_mode == 2 and len(players) > 1 and players[1].hp > 0:
                players[1].move(keys[pygame.K_RIGHT] - keys[pygame.K_LEFT], keys[pygame.K_DOWN] - keys[pygame.K_UP])
                players[1].update()

            # Spawn vipers at exactly the same level/stats as the squirrels
            while len(vipers) < viper_target_count():
                if game_mode == 3:
                    vipers.append(ViperEnemy(level=level_state["level"], is_player_controlled=True, spawn=(WIDTH - 220, HEIGHT // 2)))
                else:
                    vipers.append(ViperEnemy(level=level_state["level"]))

            for p in projectiles[:]:
                p.update()
                if not p.alive:
                    projectiles.remove(p)

            for part in particles[:]:
                part.update()
                if part.life <= 0:
                    particles.remove(part)

            # Energy shards: whoever grabs one (squirrel OR viper) gets the same boost
            for s in shards[:]:
                s.update()
                if s.life <= 0:
                    shards.remove(s)
                    continue
                for f in [p for p in players if p.hp > 0] + vipers:
                    if math.hypot(s.x - f.x, s.y - f.y) < 26:
                        f.collect_shard()
                        if isinstance(f, SquirrelPlayer):
                            f.score += 100
                            update_high_score(f.score)
                            who = f"SQUIRREL P{f.player_id}"
                        else:
                            who = "VIPER"
                        show_banner(f"{who} POWER UP!  ATK {f.attack_power} -> {f.power()} for 10s")
                        for _ in range(12):
                            particles.append(Particle(f.x, f.y, (255, 230, 90)))
                        shards.remove(s)
                        play_sfx(snd_pickup)
                        break

            # New shards appear regularly in every mode, anywhere in the middle of the arena
            shard_clock["t"] += 1
            if shard_clock["t"] >= SHARD_SPAWN_FRAMES and len(shards) < 2:
                shard_clock["t"] = 0
                shards.append(Shard(random.uniform(200, WIDTH - 200), random.uniform(150, HEIGHT - 150)))

            # Move vipers
            for viper in vipers:
                if game_mode == 3:
                    viper.update_manual(keys[pygame.K_RIGHT] - keys[pygame.K_LEFT], keys[pygame.K_DOWN] - keys[pygame.K_UP])
                else:
                    viper.update_ai(players, projectiles, viper_spit, viper_burst, shards)

            # Squirrel shots vs vipers (head = full damage, tail = half)
            for p in projectiles[:]:
                if p.is_hostile:
                    continue
                for viper in vipers:
                    hit = False
                    if math.hypot(p.x - viper.x, p.y - viper.y) < HIT_RADIUS:
                        hit = True
                        viper.take_damage(p.damage)
                    else:
                        for seg_idx in range(3, min(len(viper.history), 18), 3):
                            sx, sy = viper.history[seg_idx]
                            if math.hypot(p.x - sx, p.y - sy) < 14:
                                hit = True
                                viper.take_damage(p.damage // 2)
                                break
                    if hit:
                        viper.last_hit_by = p.owner
                        if p in projectiles:
                            projectiles.remove(p)
                        for _ in range(5):
                            particles.append(Particle(p.x, p.y, (80, 255, 120)))
                        shake_intensity = max(shake_intensity, 3)
                        break

            # Viper venom vs squirrels (same hit size, same damage)
            for p in projectiles[:]:
                if not p.is_hostile:
                    continue
                for ply in players:
                    if ply.hp > 0 and math.hypot(p.x - ply.x, p.y - ply.y) < HIT_RADIUS:
                        ply.take_damage(p.damage)
                        shake_intensity = max(shake_intensity, 6)
                        if p in projectiles:
                            projectiles.remove(p)
                        for _ in range(6):
                            particles.append(Particle(ply.x, ply.y, (255, 80, 120)))
                        break

            # Body contact: BOTH sides take a hit (fair clash)
            for viper in vipers:
                for ply in players:
                    if ply.hp > 0 and viper.contact_timer <= 0 and math.hypot(viper.x - ply.x, viper.y - ply.y) < CONTACT_RADIUS:
                        ply.take_damage(viper.power())
                        viper.take_damage(ply.power())
                        viper.last_hit_by = ply
                        viper.contact_timer = 40
                        attack_sound("vp_bite")
                        shake_intensity = max(shake_intensity, 9)
                        for _ in range(8):
                            particles.append(Particle((ply.x + viper.x) / 2, (ply.y + viper.y) / 2, (255, 200, 80)))
                        ang = math.atan2(viper.y - ply.y, viper.x - ply.x)
                        viper.x = max(50, min(WIDTH - 50, viper.x + math.cos(ang) * 60))
                        viper.y = max(50, min(HEIGHT - 50, viper.y + math.sin(ang) * 60))
                        ply.x = max(50, min(WIDTH - 50, ply.x - math.cos(ang) * 30))
                        ply.y = max(50, min(HEIGHT - 50, ply.y - math.sin(ang) * 30))

            # Defeats
            if game_mode == 3 and players[0].hp <= 0:
                play_sfx(snd_boom)
                pvp_round_over("viper")
            else:
                for viper in vipers[:]:
                    if viper.hp <= 0 and viper in vipers:
                        viper_defeated(viper)

            if game_mode != 3 and all(p.hp <= 0 for p in players):
                game_over = True
                update_high_score(players[0].score)

        # ---------------- RENDER ----------------
        current_level = level_state["level"]
        canvas.fill((9, 12, 22))

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

        # --- HUD: identical stat panels for squirrel(s) and viper(s) ---
        def draw_panel(x, y, label, unit, hp_color):
            pygame.draw.rect(canvas, (35, 15, 20), (x, y, 200, 12))
            pygame.draw.rect(canvas, hp_color, (x, y, int(200 * max(0.0, unit.hp / unit.max_hp)), 12))
            pygame.draw.rect(canvas, (220, 220, 220), (x, y, 200, 12), 1)
            canvas.blit(font_hud_sm.render(f"{label} HP {unit.hp}/{unit.max_hp}", True, (255, 240, 240)), (x + 5, y))
            pygame.draw.rect(canvas, (15, 25, 40), (x, y + 16, 200, 10))
            pygame.draw.rect(canvas, (0, 215, 255), (x, y + 16, int(200 * max(0.0, unit.defense / unit.max_defense)), 10))
            pygame.draw.rect(canvas, (180, 240, 255), (x, y + 16, 200, 10), 1)
            canvas.blit(font_hud_sm.render(f"DEF {unit.defense}/{unit.max_defense}", True, (210, 255, 255)), (x + 5, y + 15))
            ready = 1.0 - (unit.special_timer / unit.special_cd)
            pygame.draw.rect(canvas, (25, 30, 20), (x, y + 30, 200, 8))
            pygame.draw.rect(canvas, (0, 255, 170) if unit.special_timer == 0 else (120, 160, 90), (x, y + 30, int(200 * ready), 8))
            atk_txt = f"ATK {unit.power()}  POWER UP {unit.boost_timer // 60 + 1}s" if unit.boost_timer > 0 else f"ATK {unit.attack_power}"
            canvas.blit(font_hud_sm.render(atk_txt, True, (255, 240, 120) if unit.boost_timer > 0 else (255, 205, 50)), (x + 5, y + 40))

        for i, p in enumerate(players):
            draw_panel(25, 20 + i * 60, f"SQUIRREL P{p.player_id}", p, (255, 110, 60) if p.player_id == 1 else (90, 170, 255))
        for i, v in enumerate(vipers[:2]):
            draw_panel(WIDTH - 225, 20 + i * 60, "VIPER" + (" (P2)" if v.is_player_controlled else " AI"), v, (80, 220, 110))

        mode_names = {1: "SOLO vs AI", 2: "DUAL SQUIRREL vs AI", 3: "SQUIRREL vs VIPER (PVP)"}
        top = font_hud.render(f"LEVEL {current_level}  |  {mode_names[game_mode]}  [T: SWITCH]", True, (255, 205, 50))
        canvas.blit(top, top.get_rect(center=(WIDTH // 2, 22)))
        if game_mode == 3:
            sc = font_hud.render(f"ROUNDS  SQUIRREL {pvp_wins['squirrel']} - {pvp_wins['viper']} VIPER", True, (230, 230, 230))
        else:
            sc = font_hud.render(f"SCORE {players[0].score}   HI {high_score}   KILLS TO NEXT LEVEL {5 - level_state['kills'] % 5}", True, (230, 230, 230))
        canvas.blit(sc, sc.get_rect(center=(WIDTH // 2, 42)))

        if banner["timer"] > 0:
            banner["timer"] -= 1
            b = font_hud.render(banner["text"], True, (255, 230, 90))
            canvas.blit(b, b.get_rect(center=(WIDTH // 2, 70)))

        controls = {
            1: "[P1: WASD move, SPACE/L-CLICK shoot, E/R-CLICK nova] [M: MUTE] [R: RESET] [T: MODE]",
            2: "[P1: WASD+SPACE+E] [P2: ARROWS move, ENTER shoot, R-SHIFT nova] [M: MUTE] [T: MODE]",
            3: "[SQUIRREL: WASD+SPACE+E] [VIPER: ARROWS move, ENTER/R-CTRL spit, R-SHIFT burst] [M: MUTE] [T: MODE]",
        }[game_mode]
        canvas.blit(font_hud.render(controls, True, (0, 215, 255)), (25, HEIGHT - 35))
        canvas.blit(font_hud_sm.render(GAME_VERSION, True, (120, 130, 160)), (WIDTH - 110, HEIGHT - 20))

        if game_over:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((8, 10, 22, 215))
            canvas.blit(overlay, (0, 0))
            txt_over = font_big.render("MISSION FAILED", True, (255, 60, 80))
            txt_stats = font_hud.render(f"LEVEL {current_level} | SCORE: {players[0].score} | BEST: {high_score}", True, (220, 220, 220))
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
