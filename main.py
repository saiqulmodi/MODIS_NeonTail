import sys
import math
import random
import struct
import io
import asyncio
from array import array
import pygame

GAME_NAME = "Stratos_squirrel_vs_viper"
GAME_VERSION = "v12"

# ---------------------------------------------------------
# 1. VIEWPORT & FULLSCREEN CONFIGURATION
# ---------------------------------------------------------
WIDTH = 1280
HEIGHT = 720

_last_fit = None

def fit_canvas_to_browser():
    """Browser only: scale the whole 1280x720 game to fit the window without cropping.

    Keeps the 16:9 shape (black bars fill any spare space) and works with any
    Windows display scaling (100%, 125%, 150%...). Called regularly because the
    pygbag loader resizes the canvas itself and would otherwise cut off the edges.
    """
    global _last_fit
    if sys.platform != "emscripten":
        return
    try:
        import platform
        win = platform.window
        vw = int(win.innerWidth)
        vh = int(win.innerHeight)
        scale = min(vw / WIDTH, vh / HEIGHT)
        w = int(WIDTH * scale)
        h = int(HEIGHT * scale)
        left = (vw - w) // 2
        top = (vh - h) // 2
        style = win.canvas.style
        # Re-apply if the window changed OR the loader overwrote our size
        if _last_fit == (vw, vh) and style.width == f"{w}px" and style.height == f"{h}px":
            return
        _last_fit = (vw, vh)
        body = win.document.body.style
        body.margin = "0"
        body.padding = "0"
        body.overflow = "hidden"
        body.backgroundColor = "#05060d"
        style.position = "fixed"
        style.inset = "auto"
        style.right = "auto"
        style.bottom = "auto"
        style.margin = "0"
        style.padding = "0"
        style.border = "none"
        style.display = "block"
        style.left = f"{left}px"
        style.top = f"{top}px"
        style.width = f"{w}px"
        style.height = f"{h}px"
    except Exception:
        pass

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

def mixer_sound(samples, rate):
    """Turns mono samples (-1.0..1.0) into a Sound in the mixer's OWN raw format.

    pygame's Sound(buffer=...) plays bytes as raw data in whatever format the mixer
    was opened with (rate, sample type, channels). Handing it a WAV file or a
    different format makes it play the header as noise, at the wrong speed/pitch,
    or (in the browser) as pure static. So we match the mixer exactly.
    """
    init = pygame.mixer.get_init()
    if not init:
        return None

    # Preferred: a real WAV file object. SDL decodes the header and converts to
    # whatever format the mixer uses (desktop or browser), so nothing is guessed.
    try:
        pcm = array("h", (int(32767 * max(-1.0, min(1.0, v))) for v in samples)).tobytes()
        wav = (b"RIFF" + struct.pack("<I", 36 + len(pcm)) + b"WAVEfmt "
               + struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * 2, 2, 16)
               + b"data" + struct.pack("<I", len(pcm)) + pcm)
        return pygame.mixer.Sound(file=io.BytesIO(wav))
    except Exception:
        pass

    # Fallback: raw bytes in the mixer's own format
    out_rate, fmt, channels = init

    # Resample (linear) from our render rate to the mixer's rate
    if out_rate != rate:
        n_out = max(1, int(len(samples) * out_rate / rate))
        step = rate / out_rate
        res = []
        last = len(samples) - 1
        for i in range(n_out):
            pos = i * step
            j = int(pos)
            if j >= last:
                res.append(samples[last])
            else:
                f = pos - j
                res.append(samples[j] * (1.0 - f) + samples[j + 1] * f)
        samples = res

    if fmt in (32, -32):     # 32-bit float (pygame reports it as -32)
        typecode, conv = "f", (lambda v: v)
    elif fmt == 16:          # 16-bit unsigned
        typecode, conv = "H", (lambda v: int(v * 32767) + 32768)
    elif fmt == 8:           # 8-bit unsigned
        typecode, conv = "B", (lambda v: int(v * 127) + 128)
    elif fmt == -8:          # 8-bit signed
        typecode, conv = "b", (lambda v: int(v * 127))
    else:                    # -16: 16-bit signed (the usual one)
        typecode, conv = "h", (lambda v: int(v * 32767))

    data = array(typecode)
    for v in samples:
        c = conv(v)
        for _ in range(channels):
            data.append(c)
    try:
        return pygame.mixer.Sound(buffer=data.tobytes())
    except Exception:
        return None

def render_sound(duration, fn, rate=SFX_RATE, peak=0.6):
    """Renders fn(t) into a normalised, click-free sound (short fade in/out, never clips)."""
    n = max(1, int(rate * duration))
    buf = [fn(i / rate) for i in range(n)]
    top = max(1e-6, max(abs(v) for v in buf))
    scale = peak / top
    fade_in = max(1, int(rate * 0.004))
    fade_out = max(1, int(rate * 0.015))
    out = []
    for i, v in enumerate(buf):
        g = 1.0
        if i < fade_in:
            g = i / fade_in
        elif i > n - fade_out:
            g = (n - i) / fade_out
        out.append(max(-1.0, min(1.0, v * scale * g)))
    return mixer_sound(out, rate)

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
    ring = 0.08   # short tail so rapid fire never blends into a continuous drone
    total = min(0.35, t0 + ring)

    def fn(t):
        v = 0.0
        for st, fr in starts:
            lt = t - st
            if 0.0 <= lt < total:
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

def play_sfx(sfx):
    """Only attack actions make sound. A repeat of the same attack restarts its sound instead of stacking copies."""
    if sfx and not audio_muted:
        try:
            sfx.stop()
            sfx.play()
        except Exception:
            pass

def stop_all_sound():
    try:
        pygame.mixer.stop()
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
        if not self.is_hostile:
            # Squirrel laser: a bright beam with a white-hot core
            tail = (int(self.x - self.vx * 1.6), int(self.y - self.vy * 1.6))
            head = (int(self.x), int(self.y))
            pygame.draw.line(surface, self.color, tail, head, 6)
            pygame.draw.line(surface, (255, 255, 255), tail, head, 2)
            pygame.draw.circle(surface, (255, 255, 255), head, 3)
            return
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

MAX_VIPERS_ON_SCREEN = 10

def pack_size(level, squirrels=1):
    """Vipers per squirrel: 1 at levels 1-5, 2 at 6-10, 3 at 11-15 ... (the original growth),
    capped so there are never more than 10 vipers on screen in total."""
    grow = 1 + (max(1, level) - 1) // 5
    return max(1, min(grow, MAX_VIPERS_ON_SCREEN // max(1, squirrels)))

class Fighter:
    """Everything combat-related lives here, so squirrel and viper can never drift apart."""

    def apply_level_up(self, level, power_mult=1):
        """power_mult: a squirrel facing a pack of N vipers gets N x HP, DEF and ATK,
        so both sides always have the same total strength."""
        self.level = max(1, level)
        self.power_mult = max(1, power_mult)
        s = level_stats(self.level)
        self.max_hp = s["max_hp"] * self.power_mult
        self.max_defense = s["max_defense"] * self.power_mult
        self.attack_power = s["attack_power"] * self.power_mult
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
        self.aim_angle = 0.0
        self.anim_t = 0.0
        self.apply_level_up(level)

    def apply_level_up(self, level, power_mult=1):
        super().apply_level_up(level, power_mult)
        self.speed = fighter_speed(self.level)

    def move(self, dx, dy):
        if dx > 0:
            self.facing_right = True
        elif dx < 0:
            self.facing_right = False
        if dx or dy:
            # Last direction moved: used to aim controller shots when the right stick is idle
            self.aim_angle = math.atan2(dy, dx)
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
    fit_canvas_to_browser()
    fit_clock = 0
    pygame.display.set_caption(GAME_NAME)
    canvas = pygame.Surface((WIDTH, HEIGHT))
    clock = pygame.time.Clock()

    font_hud = pygame.font.SysFont("consolas", 14, bold=True)
    font_hud_sm = pygame.font.SysFont("consolas", 11, bold=True)
    font_big = pygame.font.SysFont("arial", 48, bold=True)

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
    show_help = True   # the game opens on the "how to play / all keys" screen (H shows it again)
    game_over = False

    # ---- Game controllers: pad 1 = Squirrel P1, pad 2 = Squirrel P2 (Dual) or the Viper (PvP) ----
    try:
        pygame.joystick.init()
    except Exception:
        pass
    pads = {}   # instance_id -> Joystick, kept in the order they were plugged in
    PAD_DEAD = 0.3
    PAD_START = 9 if sys.platform == "emscripten" else 7   # browser vs desktop button numbering
    PAD_SHOOT = (0, 2)          # A, X
    PAD_SPECIAL = (1, 3, 4, 5)  # B, Y, LB, RB

    def pad_role(j):
        """Which character this controller drives in the current mode (None = unused)."""
        order = list(pads.values())
        idx = order.index(j) if j in order else -1
        if idx == 0:
            return "p1"
        if idx == 1:
            return {2: "p2", 3: "viper"}.get(game_mode)
        return None

    def pad_for(role):
        for j in pads.values():
            if pad_role(j) == role:
                return j
        return None

    def pad_move(role):
        """Left stick (analog) or D-pad for the given role; (0, 0) if no controller."""
        j = pad_for(role)
        if j is None:
            return 0.0, 0.0
        x = y = 0.0
        try:
            if j.get_numaxes() >= 2:
                x, y = j.get_axis(0), j.get_axis(1)
            if abs(x) < PAD_DEAD:
                x = 0.0
            if abs(y) < PAD_DEAD:
                y = 0.0
            if j.get_numhats() > 0:
                hx, hy = j.get_hat(0)
                if hx:
                    x = float(hx)
                if hy:
                    y = float(-hy)
        except Exception:
            return 0.0, 0.0
        m = math.hypot(x, y)
        if m > 1.0:
            x, y = x / m, y / m
        return x, y

    def pad_aim(j, unit, enemies, fallback_angle):
        """Right stick aims. With the stick idle: AI modes aim at the nearest enemy,
        Squirrel vs Viper shoots straight ahead (no auto-aim for either player)."""
        try:
            if j.get_numaxes() >= 4:
                rx, ry = j.get_axis(2), j.get_axis(3)
                if math.hypot(rx, ry) > 0.5:
                    return unit.x + rx * 200, unit.y + ry * 200
        except Exception:
            pass
        alive = [e for e in enemies if e.hp > 0]
        if game_mode != 3 and alive:
            e = min(alive, key=lambda e: math.hypot(e.x - unit.x, e.y - unit.y))
            return e.x, e.y
        return unit.x + math.cos(fallback_angle) * 200, unit.y + math.sin(fallback_angle) * 200

    def pad_held(role):
        """True while the shoot button (A / X) is held on that role's controller."""
        j = pad_for(role)
        if j is None:
            return False
        try:
            return any(j.get_button(b) for b in PAD_SHOOT if b < j.get_numbuttons())
        except Exception:
            return False

    def add_input(a, b):
        return max(-1.0, min(1.0, a + b))

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
        stop_all_sound()
        level = max(1, level)
        level_state["level"] = level
        pack = pack_size(level, len(players))
        for p in players:
            p.apply_level_up(level, power_mult=pack)
            if game_mode == 3:
                p.x, p.y = 220.0, float(HEIGHT // 2)
        vipers.clear()
        projectiles.clear()
        shards.clear()
        s = level_stats(level)
        show_banner(message or f"LEVEL {level}  |  {pack} VIPER{'S' if pack > 1 else ''} PER SQUIRREL  |  SQUIRREL POWER x{pack}  =  {pack} x VIPER (HP {s['max_hp']} DEF {s['max_defense']} ATK {s['attack_power']})")

    def reset_game(level):
        nonlocal game_over
        build_players(level)
        level_state["kills"] = 0
        start_level(level)
        game_over = False

    def spawn_wave():
        """A full pack for every living squirrel. The squirrel's power multiplier matches the pack size."""
        pack = pack_size(level_state["level"], len(players))
        alive = max(1, sum(1 for p in players if p.hp > 0))
        total = pack if game_mode == 3 else pack * alive
        for i in range(total):
            if game_mode == 3 and i == 0:
                # PvP: player 2 steers the pack leader; the rest of the pack is AI
                vipers.append(ViperEnemy(level=level_state["level"], is_player_controlled=True, spawn=(WIDTH - 220, HEIGHT // 2)))
            elif game_mode == 3:
                vipers.append(ViperEnemy(level=level_state["level"], spawn=(WIDTH + 60, random.uniform(80, HEIGHT - 80))))
            else:
                vipers.append(ViperEnemy(level=level_state["level"]))

    def pvp_viper():
        """The viper player 2 is steering right now (None if the pack is gone)."""
        for v in vipers:
            if v.is_player_controlled:
                return v
        return None

    def promote_pvp_leader():
        # PvP: if player 2's viper falls, control jumps to the next viper in the pack
        if game_mode == 3 and vipers and pvp_viper() is None:
            nxt = vipers[0]
            nxt.is_player_controlled = True
            nxt.base_speed = fighter_speed(nxt.level)
            show_banner("PLAYER 2 NOW CONTROLS THE NEXT VIPER IN THE PACK")

    def squirrel_shot(p, tx, ty):
        """A squirrel with xN power fires N laser beams in a fan - the same ammo as N vipers,
        each beam hitting as hard as one viper's spit (so total damage stays equal)."""
        if p.try_shot():
            color = (0, 255, 230) if p.player_id == 1 else (100, 220, 255)
            beams = max(1, p.power_mult)
            dmg = max(1, p.power() // beams)
            aim = math.atan2(ty - p.y, tx - p.x)
            spread = math.radians(min(48.0, 6.0 * (beams - 1)))
            for i in range(beams):
                a = aim if beams == 1 else aim - spread / 2 + spread * i / (beams - 1)
                projectiles.append(Projectile(p.x, p.y, p.x + math.cos(a) * 200, p.y + math.sin(a) * 200,
                                              damage=dmg, color=color, is_hostile=False, owner=p))
            attack_sound("sq1_shot" if p.player_id == 1 else "sq2_shot")

    def squirrel_nova(p):
        """Nova ring: 15 shots per power level (x3 squirrel = 45-shot ring), like N vipers bursting."""
        if p.try_special():
            color = (0, 255, 230) if p.player_id == 1 else (100, 220, 255)
            count = 15 * max(1, p.power_mult)
            dmg = max(1, p.power() // max(1, p.power_mult))
            for i in range(count):
                rad = math.radians(i * 360.0 / count)
                projectiles.append(Projectile(p.x, p.y, p.x + math.cos(rad) * 200, p.y + math.sin(rad) * 200,
                                              damage=dmg, color=color, is_hostile=False, owner=p))
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
        start_level(level_state["level"] + 1,
                    f"{winner.upper()} WINS THE ROUND!  NEXT: LEVEL {level_state['level'] + 1}  (both sides refilled, equal total power)")

    def viper_defeated(viper):
        if viper in vipers:
            vipers.remove(viper)
        for _ in range(16):
            particles.append(Particle(viper.x, viper.y, (60, 220, 90)))
        if game_mode == 3:
            if not vipers:
                pvp_round_over("squirrel")      # whole pack beaten
            else:
                promote_pvp_leader()
            return
        if random.random() < 0.40:
            shards.append(Shard(viper.x, viper.y))
        killer = viper.last_hit_by if viper.last_hit_by in players else players[0]
        killer.score += 250
        killer.kills += 1
        update_high_score(killer.score)
        level_state["kills"] += 1
        if level_state["kills"] % 5 == 0:
            start_level(level_state["level"] + 1)
        elif not vipers:
            # Wave cleared: everyone alive refills before the next full pack arrives
            for p in players:
                if p.hp > 0:
                    p.refill()

    reset_game(1)

    # Level-jump bar along the bottom: LV 1, 10, 20 ... 100
    level_jumps = [1] + list(range(10, 101, 10))
    btn_w, btn_gap = 58, 6
    strip_x = WIDTH // 2 - (len(level_jumps) * (btn_w + btn_gap) - btn_gap) // 2 + 60
    level_buttons = [(lvl, pygame.Rect(strip_x + i * (btn_w + btn_gap), HEIGHT - 66, btn_w, 22)) for i, lvl in enumerate(level_jumps)]

    def draw_level_bar(current_level):
        lbl = font_hud.render("JUMP TO LEVEL:", True, (255, 205, 50))
        canvas.blit(lbl, (level_buttons[0][1].x - lbl.get_width() - 10, HEIGHT - 63))
        for lvl, r in level_buttons:
            active = (current_level // 10 * 10 if current_level >= 10 else 1) == lvl
            pygame.draw.rect(canvas, (255, 205, 50) if active else (30, 40, 70), r, border_radius=4)
            pygame.draw.rect(canvas, (255, 230, 120), r, 1, border_radius=4)
            t = font_hud_sm.render(f"LV {lvl}", True, (20, 20, 30) if active else (230, 230, 230))
            canvas.blit(t, t.get_rect(center=r.center))
        hint = font_hud_sm.render("keys 1-9 = LV 10-90, 0 = LV 100, [ ] = -/+10", True, (160, 170, 200))
        canvas.blit(hint, hint.get_rect(center=((level_buttons[0][1].x + level_buttons[-1][1].right) // 2, HEIGHT - 76)))

    font_help_title = pygame.font.SysFont("arial", 34, bold=True)
    font_help_head = pygame.font.SysFont("consolas", 17, bold=True)
    font_help = pygame.font.SysFont("consolas", 14, bold=True)

    HELP_CONTROLS = [
        ("SQUIRREL  (Player 1, every mode)", None),
        ("W A S D", "move"),
        ("SPACE / LEFT CLICK", "laser (aim with mouse, HOLD to keep firing)"),
        ("E / RIGHT CLICK", "Nova ring attack (special)"),
        ("SQUIRREL 2 (Dual)  /  VIPER (Player 2, Sqrl vs Viper)", None),
        ("ARROW KEYS", "move (the viper player steers the lead viper)"),
        ("ENTER / RIGHT CTRL", "squirrel blaster  /  viper venom spit"),
        ("RIGHT SHIFT", "squirrel Nova  /  viper venom burst"),
        ("GAME CONTROLLER  (pad 1 = Squirrel, pad 2 = Squirrel 2 / Viper)", None),
        ("LEFT STICK / D-PAD", "move"),
        ("A / X", "shoot, hold to keep firing (right stick aims)"),
        ("B / Y / LB / RB", "special: Nova / venom burst"),
        ("START", "start the game / show this screen"),
        ("GAME", None),
        ("T  R  M  H", "mode / restart / mute / this screen"),
        ("LEVEL JUMP", None),
        ("1 - 9  /  0", "level 10, 20 ... 90  /  level 100"),
        ("] [  or  PAGE UP / DOWN", "next / previous level ending in 0"),
        ("CLICK  LV 1 ... LV 100", "buttons at the bottom of the screen"),
    ]
    HELP_RULES = [
        "EQUAL POWER",
        "- Squirrel and viper use the SAME level stats:",
        "  HP, defense, attack, fire rate and special.",
        "- More vipers come at higher levels: 1 per squirrel",
        "  at levels 1-5, +1 every 5 levels (max 10 on screen).",
        "- Each squirrel gets power x pack size:",
        "  3 vipers -> squirrel has 3x HP, 3x DEF and fires",
        "  3 lasers at once + a 3x bigger Nova ring.",
        "  So both sides always have the same total strength.",
        "",
        "PLAYING",
        "- Kill 5 vipers = next level (everyone refills).",
        "- Beat the whole pack = everyone refills, new pack.",
        "- Touching: squirrel AND viper both take damage.",
        "- Green gems every 7s: +25% attack for 10s plus",
        "  HP/DEF. Vipers can grab them too!",
        "- Squirrel vs Viper: beat the whole pack to win the",
        "  round; if P2's viper falls, P2 takes the next one.",
        "",
        "SOUND",
        "- Only attacks make sound. Every attack has its own",
        "  tune, different in each mode and every 3 levels.",
    ]

    def draw_help_screen(current_level):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((6, 8, 18, 238))
        canvas.blit(overlay, (0, 0))
        title = font_help_title.render(GAME_NAME, True, (255, 205, 50))
        canvas.blit(title, title.get_rect(center=(WIDTH // 2, 34)))
        mode_names = {1: "SOLO vs AI", 2: "DUAL SQUIRREL vs AI", 3: "SQUIRREL vs VIPER (2 players)"}
        m = font_help_head.render(f"MODE:  {mode_names[game_mode]}   (press T to change)      LEVEL: {current_level}", True, (0, 255, 220))
        canvas.blit(m, m.get_rect(center=(WIDTH // 2, 70)))

        # Left column: every key
        x, y = 50, 100
        canvas.blit(font_help_head.render("ALL KEYS", True, (255, 205, 50)), (x, y))
        y += 26
        for key, what in HELP_CONTROLS:
            if what is None:
                y += 4
                canvas.blit(font_help.render(key, True, (120, 200, 255)), (x, y))
            else:
                canvas.blit(font_help.render(key, True, (255, 255, 255)), (x + 12, y))
                canvas.blit(font_help.render(what, True, (190, 200, 220)), (x + 230, y))
            y += 21

        # Right column: how it works
        x, y = 690, 100
        canvas.blit(font_help_head.render("HOW IT WORKS", True, (255, 205, 50)), (x, y))
        y += 26
        for line in HELP_RULES:
            heading = line and not line.startswith(("-", " "))
            col = (120, 200, 255) if heading else (190, 200, 220)
            if line:
                canvas.blit(font_help.render(line, True, col), (x, y))
            y += 21

        go = font_help_head.render("PRESS ENTER / SPACE, CLICK, OR START ON A CONTROLLER TO PLAY", True, (80, 255, 120))
        canvas.blit(go, go.get_rect(center=(WIDTH // 2, HEIGHT - 28)))

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

            # Start / help screen: T changes mode, M mutes, anything else starts the game
            elif show_help and event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                if event.type == pygame.KEYDOWN and event.key == pygame.K_t:
                    game_mode = (game_mode % 3) + 1
                    pvp_wins["squirrel"] = pvp_wins["viper"] = 0
                    reset_game(current_level)
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_m:
                    audio_muted = not audio_muted
                    if audio_muted:
                        stop_all_sound()
                else:
                    show_help = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_m:
                    audio_muted = not audio_muted
                    if audio_muted:
                        stop_all_sound()

                elif event.key == pygame.K_h:
                    show_help = True

                elif event.key == pygame.K_t:
                    game_mode = (game_mode % 3) + 1
                    pvp_wins["squirrel"] = pvp_wins["viper"] = 0
                    reset_game(current_level)

                elif event.key == pygame.K_r:
                    reset_game(current_level)

                elif pygame.K_1 <= event.key <= pygame.K_9:
                    start_level((event.key - pygame.K_0) * 10)
                    game_over = False

                elif event.key == pygame.K_0:
                    start_level(100)
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
                    v = pvp_viper()
                    if v:
                        viper_spit(v, v.x + math.cos(v.heading) * 150, v.y + math.sin(v.heading) * 150)
                elif game_mode == 3 and event.key == pygame.K_RSHIFT:
                    v = pvp_viper()
                    if v:
                        viper_burst(v)

                elif event.key == pygame.K_SPACE:
                    mx, my = pygame.mouse.get_pos()
                    squirrel_shot(players[0], mx, my)
                elif event.key == pygame.K_e:
                    squirrel_nova(players[0])

            # Level-jump bar: click LV 1 / 10 / 20 ... 100 (works on the game-over screen too)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and any(r.collidepoint(event.pos) for _, r in level_buttons):
                for lvl, r in level_buttons:
                    if r.collidepoint(event.pos):
                        start_level(lvl)
                        game_over = False
                        break

            elif event.type == pygame.MOUSEBUTTONDOWN and not game_over:
                if event.button == 1:
                    mx, my = pygame.mouse.get_pos()
                    squirrel_shot(players[0], mx, my)
                elif event.button == 3:
                    squirrel_nova(players[0])

            # ---- Game controllers ----
            elif event.type == pygame.JOYDEVICEADDED:
                try:
                    j = pygame.joystick.Joystick(event.device_index)
                    j.init()
                    pads[j.get_instance_id()] = j
                    role = {"p1": "SQUIRREL P1", "p2": "SQUIRREL P2", "viper": "THE VIPER"}.get(pad_role(j), "nobody in this mode")
                    show_banner(f"GAME CONTROLLER {len(pads)} CONNECTED  ->  controls {role}")
                except Exception:
                    pass

            elif event.type == pygame.JOYDEVICEREMOVED:
                pads.pop(getattr(event, "instance_id", None), None)
                show_banner("GAME CONTROLLER DISCONNECTED")

            elif event.type == pygame.JOYBUTTONDOWN:
                j = pads.get(getattr(event, "instance_id", getattr(event, "joy", None)))
                if j is None:
                    continue
                btn = event.button
                if show_help:
                    if btn == PAD_START or btn in PAD_SHOOT:
                        show_help = False
                    continue
                if btn == PAD_START:
                    show_help = True
                    continue
                if game_over:
                    if btn in PAD_SHOOT:
                        reset_game(current_level)
                    continue
                role = pad_role(j)
                if role == "p1" or (role == "p2" and len(players) > 1):
                    p = players[0] if role == "p1" else players[1]
                    if btn in PAD_SHOOT:
                        tx, ty = pad_aim(j, p, vipers, p.aim_angle)
                        squirrel_shot(p, tx, ty)
                    elif btn in PAD_SPECIAL:
                        squirrel_nova(p)
                elif role == "viper":
                    v = pvp_viper()
                    if v:
                        if btn in PAD_SHOOT:
                            tx, ty = pad_aim(j, v, players, v.heading)
                            viper_spit(v, tx, ty)
                        elif btn in PAD_SPECIAL:
                            viper_burst(v)

        if not game_over and not show_help:
            keys = pygame.key.get_pressed()

            # P1 Controls (WASD + controller 1)
            if players[0].hp > 0:
                jx, jy = pad_move("p1")
                players[0].move(add_input(keys[pygame.K_d] - keys[pygame.K_a], jx), add_input(keys[pygame.K_s] - keys[pygame.K_w], jy))
                players[0].update()

            # P2 Controls (Arrows + controller 2)
            if game_mode == 2 and len(players) > 1 and players[1].hp > 0:
                jx, jy = pad_move("p2")
                players[1].move(add_input(keys[pygame.K_RIGHT] - keys[pygame.K_LEFT], jx), add_input(keys[pygame.K_DOWN] - keys[pygame.K_UP], jy))
                players[1].update()

            # Hold to keep firing (keyboard, mouse or controller A) - the fire rate limit still applies
            mouse_on_bar = any(r.collidepoint(pygame.mouse.get_pos()) for _, r in level_buttons)
            if players[0].hp > 0 and (keys[pygame.K_SPACE] or (pygame.mouse.get_pressed()[0] and not mouse_on_bar) or pad_held("p1")):
                j = pad_for("p1")
                if j is not None and pad_held("p1"):
                    tx, ty = pad_aim(j, players[0], vipers, players[0].aim_angle)
                else:
                    tx, ty = pygame.mouse.get_pos()
                squirrel_shot(players[0], tx, ty)
            if game_mode == 2 and len(players) > 1 and players[1].hp > 0 and (keys[pygame.K_RETURN] or keys[pygame.K_RCTRL] or pad_held("p2")):
                p2 = players[1]
                j = pad_for("p2")
                if j is not None and pad_held("p2"):
                    tx, ty = pad_aim(j, p2, vipers, p2.aim_angle)
                else:
                    tx, ty = p2.x + (150 if p2.facing_right else -150), p2.y
                squirrel_shot(p2, tx, ty)
            if game_mode == 3 and (keys[pygame.K_RETURN] or keys[pygame.K_RCTRL] or keys[pygame.K_KP0] or pad_held("viper")):
                v = pvp_viper()
                if v:
                    j = pad_for("viper")
                    if j is not None and pad_held("viper"):
                        tx, ty = pad_aim(j, v, players, v.heading)
                    else:
                        tx, ty = v.x + math.cos(v.heading) * 150, v.y + math.sin(v.heading) * 150
                    viper_spit(v, tx, ty)

            # Next wave: a full viper pack per squirrel (squirrel power already matches the pack)
            if not vipers:
                spawn_wave()

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
                        break

            # New shards appear regularly in every mode, anywhere in the middle of the arena
            shard_clock["t"] += 1
            if shard_clock["t"] >= SHARD_SPAWN_FRAMES and len(shards) < 2:
                shard_clock["t"] = 0
                shards.append(Shard(random.uniform(200, WIDTH - 200), random.uniform(150, HEIGHT - 150)))

            # Move vipers
            for viper in vipers:
                if game_mode == 3 and viper.is_player_controlled:
                    jx, jy = pad_move("viper")
                    viper.update_manual(add_input(keys[pygame.K_RIGHT] - keys[pygame.K_LEFT], jx), add_input(keys[pygame.K_DOWN] - keys[pygame.K_UP], jy))
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
            draw_panel(25, 20 + i * 60, f"SQUIRREL P{p.player_id} x{p.power_mult}", p, (255, 110, 60) if p.player_id == 1 else (90, 170, 255))
        shown = sorted(vipers, key=lambda v: not v.is_player_controlled)[:2]
        for i, v in enumerate(shown):
            draw_panel(WIDTH - 225, 20 + i * 60, "VIPER" + (" (P2)" if v.is_player_controlled else " AI"), v, (80, 220, 110))
        if len(vipers) > 2:
            more = font_hud_sm.render(f"+ {len(vipers) - 2} more vipers in the pack", True, (160, 230, 170))
            canvas.blit(more, (WIDTH - 225, 20 + 2 * 60))

        mode_names = {1: "SOLO vs AI", 2: "DUAL SQUIRREL vs AI", 3: "SQUIRREL vs VIPER (PVP)"}
        top = font_hud.render(f"LEVEL {current_level}  |  {mode_names[game_mode]}  [T: SWITCH]", True, (255, 205, 50))
        canvas.blit(top, top.get_rect(center=(WIDTH // 2, 22)))
        if game_mode == 3:
            sc = font_hud.render(f"ROUNDS  SQUIRREL {pvp_wins['squirrel']} - {pvp_wins['viper']} VIPER", True, (230, 230, 230))
        else:
            sc = font_hud.render(f"SCORE {players[0].score}   HI {high_score}   KILLS TO NEXT LEVEL {5 - level_state['kills'] % 5}", True, (230, 230, 230))
        canvas.blit(sc, sc.get_rect(center=(WIDTH // 2, 42)))

        # Power comparison: squirrel vs viper at this level (always equal base power)
        s_now = level_stats(current_level)
        pack_now = pack_size(current_level, len(players))
        pw = font_hud.render(f"VIPERS: {len(vipers)}   |   PACK: {pack_now} VIPER{'S' if pack_now > 1 else ''} PER SQUIRREL   |   SQUIRREL POWER x{pack_now}",
                             True, (80, 255, 120))
        canvas.blit(pw, pw.get_rect(center=(WIDTH // 2, 62)))
        pw2 = font_hud_sm.render(f"EACH VIPER: HP {s_now['max_hp']}  DEF {s_now['max_defense']}  ATK {s_now['attack_power']}      =      "
                                 f"SQUIRREL x{pack_now}: HP {s_now['max_hp'] * pack_now}  DEF {s_now['max_defense'] * pack_now}  ATK {s_now['attack_power'] * pack_now}",
                                 True, (170, 255, 190))
        canvas.blit(pw2, pw2.get_rect(center=(WIDTH // 2, 80)))

        if banner["timer"] > 0:
            banner["timer"] -= 1
            b = font_hud.render(banner["text"], True, (255, 230, 90))
            canvas.blit(b, b.get_rect(center=(WIDTH // 2, 102)))

        draw_level_bar(current_level)

        controls = {
            1: "[P1: WASD move, SPACE/L-CLICK shoot, E/R-CLICK nova] [M: MUTE] [R: RESET] [T: MODE] [H: HELP]",
            2: "[P1: WASD+SPACE+E] [P2: ARROWS move, ENTER shoot, R-SHIFT nova] [M: MUTE] [T: MODE] [H: HELP]",
            3: "[SQUIRREL: WASD+SPACE+E] [VIPER: ARROWS move, ENTER/R-CTRL spit, R-SHIFT burst] [M: MUTE] [T: MODE] [H: HELP]",
        }[game_mode]
        if pads:
            controls += f" [PAD: {len(pads)} CONNECTED]"
        canvas.blit(font_hud.render(controls, True, (0, 215, 255)), (25, HEIGHT - 35))
        canvas.blit(font_hud_sm.render(f"{GAME_NAME} {GAME_VERSION}", True, (120, 130, 160)), (WIDTH - 200, HEIGHT - 20))

        if game_over:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((8, 10, 22, 215))
            canvas.blit(overlay, (0, 0))
            txt_over = font_big.render("MISSION FAILED", True, (255, 60, 80))
            txt_stats = font_hud.render(f"LEVEL {current_level} | SCORE: {players[0].score} | BEST: {high_score}", True, (220, 220, 220))
            txt_restart = font_hud.render("PRESS [R] TO RESTART  |  PRESS [1-9]/[0] OR CLICK A LEVEL BELOW TO WARP", True, (0, 255, 220))
            canvas.blit(txt_over, txt_over.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 35)))
            canvas.blit(txt_stats, txt_stats.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 15)))
            canvas.blit(txt_restart, txt_restart.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 55)))
            draw_level_bar(current_level)

        if show_help:
            draw_help_screen(current_level)

        ox, oy = 0, 0
        if shake_intensity > 0:
            ox = random.randint(-shake_intensity, shake_intensity)
            oy = random.randint(-shake_intensity, shake_intensity)
            shake_intensity = max(0, shake_intensity - 1)

        screen.fill((5, 6, 13))
        screen.blit(canvas, (ox, oy))

        pygame.display.flip()
        clock.tick(60)
        # Keep the whole screen (including the power panels) inside the browser window
        fit_clock += 1
        if fit_clock >= 30:
            fit_clock = 0
            fit_canvas_to_browser()
        await asyncio.sleep(0)

if __name__ == "__main__":
    asyncio.run(main())
