import sys
import math
import random
import asyncio
import pygame

# ---------------------------------------------------------
# 1. VIEWPORT & LETTERBOX CONFIGURATION
# ---------------------------------------------------------
if sys.platform == "emscripten":
    import platform
    try:
        platform.window.canvas.style.width = "auto"
        platform.window.canvas.style.height = "100vh"
        platform.window.canvas.style.aspectRatio = "16 / 9"
        platform.window.canvas.style.display = "block"
        platform.window.canvas.style.margin = "0 auto"
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
# 3. SYNTHETIC AUDIO GENERATION
# ---------------------------------------------------------
audio_muted = False

def generate_laser_audio():
    sample_rate = 22050
    duration = 0.12
    n_samples = int(sample_rate * duration)
    buf = bytearray(n_samples)
    for i in range(n_samples):
        t = i / sample_rate
        freq = 950 - (t / duration) * 650
        val = math.sin(2 * math.pi * freq * t)
        decay = max(0.0, 1.0 - (t / duration))
        buf[i] = max(0, min(255, int(128 + 110 * val * decay)))
    try:
        return pygame.mixer.Sound(buffer=bytes(buf))
    except Exception:
        return None

def generate_boom_audio():
    sample_rate = 22050
    duration = 0.22
    n_samples = int(sample_rate * duration)
    buf = bytearray(n_samples)
    for i in range(n_samples):
        t = i / sample_rate
        val = (random.random() * 2.0 - 1.0)
        decay = max(0.0, 1.0 - (t / duration))
        buf[i] = max(0, min(255, int(128 + 110 * val * decay)))
    try:
        return pygame.mixer.Sound(buffer=bytes(buf))
    except Exception:
        return None

def generate_pickup_audio():
    sample_rate = 22050
    duration = 0.14
    n_samples = int(sample_rate * duration)
    buf = bytearray(n_samples)
    for i in range(n_samples):
        t = i / sample_rate
        freq = 550 + (t / duration) * 900
        val = math.sin(2 * math.pi * freq * t)
        decay = max(0.0, 1.0 - (t / duration))
        buf[i] = max(0, min(255, int(128 + 100 * val * decay)))
    try:
        return pygame.mixer.Sound(buffer=bytes(buf))
    except Exception:
        return None

def play_sfx(sfx):
    global audio_muted
    if sfx and not audio_muted:
        try:
            sfx.play()
        except Exception:
            pass

# ---------------------------------------------------------
# 4. PROJECTILES, PARTICLES & PICKUPS
# ---------------------------------------------------------
class Projectile:
    def __init__(self, x, y, tx, ty, color=(0, 255, 230)):
        self.x = float(x)
        self.y = float(y)
        angle = math.atan2(ty - y, tx - x)
        self.speed = 15.0
        self.vx = math.cos(angle) * self.speed
        self.vy = math.sin(angle) * self.speed
        self.color = color
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
# 5. AUTHENTIC MONGOOSE HERO (P1 & P2 SKINS)
# ---------------------------------------------------------
class MongoosePlayer:
    def __init__(self, x, y, player_id=1):
        self.player_id = player_id
        self.x = float(x)
        self.y = float(y)
        self.speed = 6.8
        self.hp = 500
        self.max_hp = 500
        self.armor = 200
        self.max_armor = 200
        self.facing_right = True
        self.anim_t = 0.0
        self.nova_cd = 0
        self.nova_max_cd = 180
        self.shield_timer = 90  # 1.5 seconds invulnerability at spawn
        self.alive = True

        if player_id == 1:
            self.col_primary = (195, 120, 52)
            self.col_highlight = (235, 165, 98)
            self.col_dark = (145, 78, 28)
            self.col_proj = (0, 255, 230)
        else:
            self.col_primary = (65, 135, 185)
            self.col_highlight = (145, 210, 245)
            self.col_dark = (32, 70, 110)
            self.col_proj = (255, 215, 0)

    def move(self, dx, dy):
        if not self.alive:
            return
        if dx > 0:
            self.facing_right = True
        elif dx < 0:
            self.facing_right = False
        self.x = max(50, min(WIDTH - 50, self.x + dx * self.speed))
        self.y = max(50, min(HEIGHT - 50, self.y + dy * self.speed))

    def take_damage(self, amount):
        if not self.alive or self.shield_timer > 0:
            return
        if self.armor > 0:
            absorbed = min(self.armor, amount)
            self.armor -= absorbed
            amount -= absorbed
        self.hp = max(0, self.hp - amount)
        if self.hp <= 0:
            self.alive = False

    def update(self):
        self.anim_t += 0.15
        if self.nova_cd > 0:
            self.nova_cd -= 1
        if self.shield_timer > 0:
            self.shield_timer -= 1

    def draw(self, surface):
        if not self.alive:
            return
        facing = 1 if self.facing_right else -1

        # 0. Invulnerability Shield Ring
        if self.shield_timer > 0:
            pulse_r = int(28 + math.sin(self.anim_t * 3) * 4)
            pygame.draw.circle(surface, (0, 220, 255), (int(self.x), int(self.y)), pulse_r, 2)

        # 1. Furry Tapered Tail
        tail_wave = math.sin(self.anim_t * 1.6) * 5
        for s in range(7):
            tx = self.x - facing * (18 + s * 6)
            ty = self.y + 4 + math.sin(self.anim_t + s * 0.45) * 6 + tail_wave
            rad = max(3, 10 - s)
            pygame.draw.circle(surface, self.col_dark, (int(tx), int(ty)), rad)
            pygame.draw.circle(surface, self.col_highlight, (int(tx), int(ty)), max(1, rad - 2))

        # 2. Running Paws
        paw_t = math.sin(self.anim_t * 2.2) * 5
        pygame.draw.ellipse(surface, self.col_dark, (self.x - 14 + paw_t, self.y + 8, 9, 6))
        pygame.draw.ellipse(surface, self.col_dark, (self.x + 8 - paw_t, self.y + 8, 9, 6))

        # 3. Arched Mongoose Torso
        pygame.draw.ellipse(surface, self.col_primary, (self.x - 22, self.y - 11, 42, 22))
        pygame.draw.ellipse(surface, self.col_highlight, (self.x - 16, self.y - 7, 30, 14))

        # 4. Tapered Snout Head
        hx = self.x + (16 * facing)
        hy = self.y - 5
        head_pts = [
            (hx - (6 * facing), hy - 9),
            (hx + (14 * facing), hy - 1),
            (hx - (4 * facing), hy + 7),
            (hx - (10 * facing), hy - 2),
        ]
        pygame.draw.polygon(surface, self.col_primary, head_pts)
        pygame.draw.polygon(surface, self.col_highlight, [
            (hx - (4 * facing), hy - 6),
            (hx + (10 * facing), hy - 1),
            (hx - (2 * facing), hy + 4)
        ])

        # 5. Round Predator Ears
        ear_x = hx - (4 * facing)
        ear_y = hy - 10
        pygame.draw.circle(surface, self.col_dark, (int(ear_x), int(ear_y)), 5)
        pygame.draw.circle(surface, (245, 195, 170), (int(ear_x), int(ear_y)), 2)

        # 6. Sharp Eyes & Nose
        pygame.draw.circle(surface, (20, 20, 25), (int(hx + 3 * facing), int(hy - 3)), 3)
        pygame.draw.circle(surface, (255, 255, 255), (int(hx + 4 * facing), int(hy - 4)), 1)
        pygame.draw.circle(surface, (30, 15, 15), (int(hx + 14 * facing), int(hy - 1)), 2)

# ---------------------------------------------------------
# 6. ANATOMICAL SLITHERING SERPENT WITH BUFFERED SPAWN
# ---------------------------------------------------------
class SnakeEnemy:
    def __init__(self, size_scale=1.0, level=1, avoid_targets=None):
        self.size_scale = max(0.40, size_scale)

        # Buffer: Ensure spawn point is at least 380px away from any player
        valid_pos = False
        attempts = 0
        while not valid_pos and attempts < 15:
            attempts += 1
            side = random.choice(["L", "R", "T", "B"])
            if side == "L":
                sx, sy = -70.0, random.uniform(80, HEIGHT - 80)
            elif side == "R":
                sx, sy = float(WIDTH + 70), random.uniform(80, HEIGHT - 80)
            elif side == "T":
                sx, sy = random.uniform(80, WIDTH - 80), -70.0
            else:
                sx, sy = random.uniform(80, WIDTH - 80), float(HEIGHT + 70)

            if avoid_targets:
                close = any(math.hypot(sx - t.x, sy - t.y) < 380 for t in avoid_targets if t.alive)
                if not close:
                    valid_pos = True
            else:
                valid_pos = True

        self.x = sx
        self.y = sy
        self.num_segments = 24
        self.history = [(self.x, self.y) for _ in range(self.num_segments * 3 + 12)]

        self.base_speed = (2.3 + min(3.0, (level - 1) * 0.04)) / (self.size_scale ** 0.25)
        self.slither_t = random.uniform(0, 10)
        self.hp = int((120 + level * 10) * self.size_scale)
        self.alive = True

    def update(self, targets):
        active = [t for t in targets if t.alive]
        if not active:
            return
        target = min(active, key=lambda p: math.hypot(p.x - self.x, p.y - self.y))

        self.slither_t += 0.14
        angle = math.atan2(target.y - self.y, target.x - self.x)
        wiggle = math.sin(self.slither_t) * 0.75

        self.x += math.cos(angle + wiggle) * self.base_speed
        self.y += math.sin(angle + wiggle) * self.base_speed

        self.history.insert(0, (self.x, self.y))
        max_h = self.num_segments * 3 + 12
        if len(self.history) > max_h:
            self.history = self.history[:max_h]

    def draw(self, surface):
        step = 3
        # 1. Sinuous Scaled Tail
        for i in range(self.num_segments - 1, 0, -1):
            idx = min(len(self.history) - 1, i * step)
            sx, sy = self.history[idx]
            ratio = 1.0 - (i / self.num_segments)
            radius = int(max(3, (6 + ratio * 8) * self.size_scale))

            scale_dark = (20, 75, 35) if (i % 2 == 0) else (35, 115, 50)
            pygame.draw.circle(surface, scale_dark, (int(sx), int(sy)), radius)
            pygame.draw.circle(surface, (130, 210, 85), (int(sx), int(sy + radius * 0.2)), max(1, radius - 3))

        # 2. Angle orientation
        if len(self.history) > 4:
            prev_x, prev_y = self.history[4]
            head_ang = math.atan2(self.y - prev_y, self.x - prev_x)
        else:
            head_ang = 0

        cos_a = math.cos(head_ang)
        sin_a = math.sin(head_ang)

        # 3. Flared Diamond Cobra Hood
        hood_w = 14 * self.size_scale
        hood_len = 16 * self.size_scale
        p_nose = (self.x + cos_a * hood_len, self.y + sin_a * hood_len)
        p_left = (self.x - cos_a * 4 - sin_a * hood_w, self.y - sin_a * 4 + cos_a * hood_w)
        p_right = (self.x - cos_a * 4 + sin_a * hood_w, self.y - sin_a * 4 - cos_a * hood_w)
        p_back = (self.x - cos_a * 8, self.y - sin_a * 8)

        pygame.draw.polygon(surface, (18, 70, 32), [p_nose, p_left, p_back, p_right])
        pygame.draw.polygon(surface, (45, 140, 65), [
            (self.x + cos_a * 10 * self.size_scale, self.y + sin_a * 10 * self.size_scale),
            (self.x - sin_a * (hood_w - 3), self.y + cos_a * (hood_w - 3)),
            (self.x - cos_a * 4, self.y - sin_a * 4),
            (self.x + sin_a * (hood_w - 3), self.y - cos_a * (hood_w - 3))
        ])

        # 4. Slit Crimson Viper Eyes
        eye_dist = 7 * self.size_scale
        e1 = (int(self.x + cos_a * 4 - sin_a * eye_dist), int(self.y + sin_a * 4 + cos_a * eye_dist))
        e2 = (int(self.x + cos_a * 4 + sin_a * eye_dist), int(self.y + sin_a * 4 - cos_a * eye_dist))
        pygame.draw.circle(surface, (255, 30, 30), e1, max(2, int(3 * self.size_scale)))
        pygame.draw.circle(surface, (255, 30, 30), e2, max(2, int(3 * self.size_scale)))

        # 5. Forked Red Tongue
        if int(self.slither_t * 3.5) % 2 == 0:
            tongue_base = p_nose
            t_tip = (tongue_base[0] + cos_a * (10 * self.size_scale), tongue_base[1] + sin_a * (10 * self.size_scale))
            fork_l = (t_tip[0] + (cos_a * 4 - sin_a * 4) * self.size_scale, t_tip[1] + (sin_a * 4 + cos_a * 4) * self.size_scale)
            fork_r = (t_tip[0] + (cos_a * 4 + sin_a * 4) * self.size_scale, t_tip[1] + (sin_a * 4 - cos_a * 4) * self.size_scale)
            pygame.draw.line(surface, (255, 35, 45), tongue_base, t_tip, max(1, int(2 * self.size_scale)))
            pygame.draw.line(surface, (255, 35, 45), t_tip, fork_l, 1)
            pygame.draw.line(surface, (255, 35, 45), t_tip, fork_r, 1)

# ---------------------------------------------------------
# 7. MAIN ENGINE & GAME STATE CONTROLLER
# ---------------------------------------------------------
async def main():
    global audio_muted
    pygame.init()
    try:
        pygame.mixer.init()
    except Exception:
        pass

    pygame.joystick.init()
    joysticks = [pygame.joystick.Joystick(i) for i in range(pygame.joystick.get_count())]
    for joy in joysticks:
        joy.init()

    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("MODIS NeonTail - Mongoose vs Snake")

    canvas = pygame.Surface((WIDTH, HEIGHT))

    clock = pygame.time.Clock()
    font_hud = pygame.font.SysFont("consolas", 14, bold=True)
    font_hud_sm = pygame.font.SysFont("consolas", 11, bold=True)
    font_big = pygame.font.SysFont("arial", 44, bold=True)
    font_sub = pygame.font.SysFont("consolas", 17, bold=True)
    font_desc = pygame.font.SysFont("consolas", 14)

    sfx_laser = generate_laser_audio()
    sfx_boom = generate_boom_audio()
    sfx_pickup = generate_pickup_audio()

    high_score = get_stored_high_score()

    state = 'MENU'
    num_players = 1
    level = 1
    score = 0
    kills = 0

    players = []
    projectiles = []
    particles = []
    shards = []
    snakes = []
    shake_intensity = 0

    def start_game(mode=1):
        nonlocal state, num_players, level, score, kills, players, projectiles, particles, shards, snakes, shake_intensity
        num_players = mode
        level = 1
        score = 0
        kills = 0
        projectiles.clear()
        particles.clear()
        shards.clear()
        snakes.clear()
        shake_intensity = 0

        if num_players == 1:
            players = [MongoosePlayer(WIDTH // 2, HEIGHT // 2, player_id=1)]
        else:
            players = [
                MongoosePlayer(WIDTH // 2 - 100, HEIGHT // 2, player_id=1),
                MongoosePlayer(WIDTH // 2 + 100, HEIGHT // 2, player_id=2)
            ]
        state = 'PLAYING'

    def get_tier_info(lvl):
        tier = (lvl - 1) // 5
        count = (1 if num_players == 1 else 2) + tier
        size_scale = max(0.40, 1.0 - (tier * 0.05))
        return count, size_scale

    def trigger_nova(p):
        if p.alive and p.nova_cd <= 0:
            for angle in range(0, 360, 24):
                rad = math.radians(angle)
                tx = p.x + math.cos(rad) * 200
                ty = p.y + math.sin(rad) * 200
                projectiles.append(Projectile(p.x, p.y, tx, ty, color=p.col_proj))
            p.nova_cd = p.nova_max_cd
            play_sfx(sfx_laser)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.JOYDEVICEADDED:
                joy = pygame.joystick.Joystick(event.device_index)
                joy.init()
                joysticks.append(joy)
            elif event.type == pygame.JOYDEVICEREMOVED:
                joysticks = [j for j in joysticks if j.get_instance_id() != event.instance_id]

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_m:
                    audio_muted = not audio_muted

                if state == 'MENU':
                    if event.key in (pygame.K_1, pygame.K_KP1):
                        start_game(mode=1)
                    elif event.key in (pygame.K_2, pygame.K_KP2):
                        start_game(mode=2)
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        start_game(mode=1)

                elif state == 'GAMEOVER':
                    if event.key == pygame.K_r:
                        start_game(num_players)
                    elif event.key == pygame.K_ESCAPE:
                        state = 'MENU'

                elif state == 'PLAYING':
                    # Player 1 Attacks
                    if event.key == pygame.K_SPACE and len(players) >= 1 and players[0].alive:
                        mx, my = pygame.mouse.get_pos()
                        projectiles.append(Projectile(players[0].x, players[0].y, mx, my, color=players[0].col_proj))
                        play_sfx(sfx_laser)
                    elif event.key == pygame.K_e and len(players) >= 1:
                        trigger_nova(players[0])

                    # Player 2 Attacks
                    if len(players) >= 2 and players[1].alive:
                        if event.key in (pygame.K_KP0, pygame.K_l):
                            if snakes:
                                nearest = min(snakes, key=lambda s: math.hypot(s.x - players[1].x, s.y - players[1].y))
                                projectiles.append(Projectile(players[1].x, players[1].y, nearest.x, nearest.y, color=players[1].col_proj))
                            else:
                                aim_dir = 1 if players[1].facing_right else -1
                                projectiles.append(Projectile(players[1].x, players[1].y, players[1].x + aim_dir * 100, players[1].y, color=players[1].col_proj))
                            play_sfx(sfx_laser)
                        elif event.key in (pygame.K_KP_PERIOD, pygame.K_k):
                            trigger_nova(players[1])

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if state == 'MENU':
                    mx, my = pygame.mouse.get_pos()
                    if 350 < my < 530 and mx > WIDTH // 2:
                        start_game(2)
                    else:
                        start_game(1)
                elif state == 'GAMEOVER':
                    start_game(num_players)
                elif state == 'PLAYING':
                    if len(players) >= 1 and players[0].alive:
                        if event.button == 1:
                            mx, my = pygame.mouse.get_pos()
                            projectiles.append(Projectile(players[0].x, players[0].y, mx, my, color=players[0].col_proj))
                            play_sfx(sfx_laser)
                        elif event.button == 3:
                            trigger_nova(players[0])

            elif event.type == pygame.JOYBUTTONDOWN:
                if state in ('MENU', 'GAMEOVER'):
                    start_game(1)
                elif state == 'PLAYING' and len(players) >= 1:
                    if event.button == 0:
                        mx, my = pygame.mouse.get_pos()
                        projectiles.append(Projectile(players[0].x, players[0].y, mx, my, color=players[0].col_proj))
                        play_sfx(sfx_laser)
                    elif event.button in (1, 5):
                        trigger_nova(players[0])

        # ---------------- STATE UPDATES ----------------
        if state == 'PLAYING':
            keys = pygame.key.get_pressed()

            # P1 Movement
            if len(players) >= 1 and players[0].alive:
                dx1 = (keys[pygame.K_d]) - (keys[pygame.K_a])
                dy1 = (keys[pygame.K_s]) - (keys[pygame.K_w])
                if joysticks:
                    try:
                        ax = joysticks[0].get_axis(0)
                        ay = joysticks[0].get_axis(1)
                        if abs(ax) > 0.25:
                            dx1 = 1 if ax > 0 else -1
                        if abs(ay) > 0.25:
                            dy1 = 1 if ay > 0 else -1
                    except Exception:
                        pass
                players[0].move(dx1, dy1)
                players[0].update()

            # P2 Movement
            if len(players) >= 2 and players[1].alive:
                dx2 = (keys[pygame.K_RIGHT]) - (keys[pygame.K_LEFT])
                dy2 = (keys[pygame.K_DOWN]) - (keys[pygame.K_UP])
                players[1].move(dx2, dy2)
                players[1].update()

            # Multi-Snake Tier Population (with distance avoidance)
            target_snakes, current_size_scale = get_tier_info(level)
            while len(snakes) < target_snakes:
                snakes.append(SnakeEnemy(size_scale=current_size_scale, level=level, avoid_targets=players))

            # Update Projectiles
            for p in projectiles[:]:
                p.update()
                if not p.alive:
                    projectiles.remove(p)

            # Update Pickups
            for s in shards[:]:
                s.update()
                if s.life <= 0:
                    shards.remove(s)
                else:
                    for pl in players:
                        if pl.alive and math.hypot(s.x - pl.x, s.y - pl.y) < 26:
                            pl.armor = min(pl.max_armor, pl.armor + 30)
                            pl.hp = min(pl.max_hp, pl.hp + 20)
                            score += 100
                            if score > high_score:
                                high_score = score
                                save_stored_high_score(high_score)
                            if s in shards:
                                shards.remove(s)
                            play_sfx(sfx_pickup)
                            break

            # Update Particles
            for part in particles[:]:
                part.update()
                if part.life <= 0:
                    particles.remove(part)

            # Snake Updates & Combat
            for snake in snakes[:]:
                snake.update(players)

                # Headshot Detection
                for p in projectiles[:]:
                    if math.hypot(p.x - snake.x, p.y - snake.y) < (18 * snake.size_scale + 4):
                        if p in projectiles:
                            projectiles.remove(p)
                        for _ in range(6):
                            particles.append(Particle(p.x, p.y, (255, 230, 80)))
                        shake_intensity = max(shake_intensity, 3)
                        snake.hp -= 50

                        if snake.hp <= 0:
                            if snake in snakes:
                                snakes.remove(snake)
                            for _ in range(18):
                                particles.append(Particle(snake.x, snake.y, (80, 255, 120)))
                            if random.random() < 0.45:
                                shards.append(Shard(snake.x, snake.y))
                            score += int(300 * (2.0 - snake.size_scale))
                            kills += 1
                            if score > high_score:
                                high_score = score
                                save_stored_high_score(high_score)
                            play_sfx(sfx_boom)

                            if kills > 0 and kills % 5 == 0:
                                level += 1
                            break

                # Mongoose Body Damage
                for pl in players:
                    if pl.alive and math.hypot(snake.x - pl.x, snake.y - pl.y) < (24 * snake.size_scale + 12):
                        pl.take_damage(int(22 * snake.size_scale))
                        shake_intensity = max(shake_intensity, 9)
                        for _ in range(8):
                            particles.append(Particle(pl.x, pl.y, (255, 60, 80)))
                        snake.x += (-60 if snake.x < pl.x else 60)
                        snake.y += (-60 if snake.y < pl.y else 60)

            if not any(pl.alive for pl in players):
                state = 'GAMEOVER'

        # ---------------- RENDER ----------------
        canvas.fill((9, 12, 22))

        # Ambient Grid
        for gx in range(0, WIDTH, 80):
            pygame.draw.line(canvas, (18, 25, 42), (gx, 0), (gx, HEIGHT), 1)
        for gy in range(0, HEIGHT, 80):
            pygame.draw.line(canvas, (18, 25, 42), (0, gy), (WIDTH, gy), 1)

        # ---------------- RENDER STATES ----------------
        if state == 'MENU':
            panel = pygame.Surface((920, 560), pygame.SRCALPHA)
            panel.fill((12, 16, 32, 235))
            canvas.blit(panel, (180, 80))
            pygame.draw.rect(canvas, (0, 215, 255), (180, 80, 920, 560), 2)

            t1 = font_big.render("MODIS NEONTAIL: MONGOOSE VS SNAKE", True, (0, 255, 220))
            t2 = font_sub.render("TACTICAL DEFENSE BRIEFING & CONTROLS", True, (255, 210, 60))
            canvas.blit(t1, t1.get_rect(center=(WIDTH // 2, 125)))
            canvas.blit(t2, t2.get_rect(center=(WIDTH // 2, 165)))

            briefing = [
                "• MISSION OBJECTIVE: Defend the cyber-arena against evolving serpent tiers.",
                "• HEADSHOT ONLY: Only direct laser strikes on the snake HEAD deal damage.",
                "• ARMOR ABSORPTION: Cyber armor absorbs hits first before health is depleted.",
                "• ENERGY SHARDS: Collect glowing green drops to restore +30 Armor and +20 HP.",
                "• LEVEL PROGRESSION: Swarms grow by +1 snake every 5 levels (100+ tiers)."
            ]
            for i, line in enumerate(briefing):
                canvas.blit(font_desc.render(line, True, (220, 230, 245)), (210, 205 + i * 26))

            # P1 Card
            c1_rect = pygame.Rect(210, 355, 420, 160)
            pygame.draw.rect(canvas, (20, 30, 55), c1_rect)
            pygame.draw.rect(canvas, (0, 215, 255), c1_rect, 1)
            canvas.blit(font_sub.render("PLAYER 1 (GOLDEN MONGOOSE)", True, (255, 180, 60)), (225, 365))
            canvas.blit(font_desc.render("MOVE:   [W, A, S, D] or Gamepad Stick", True, (200, 215, 235)), (225, 395))
            canvas.blit(font_desc.render("SHOOT:  [Left-Click / Space / Pad-A]", True, (200, 215, 235)), (225, 420))
            canvas.blit(font_desc.render("NOVA:   [Right-Click / E / Pad-B]", True, (200, 215, 235)), (225, 445))
            canvas.blit(font_desc.render("START:  Press [1] or Click Left Box", True, (0, 255, 220)), (225, 475))

            # P2 Card
            c2_rect = pygame.Rect(650, 355, 420, 160)
            pygame.draw.rect(canvas, (20, 30, 55), c2_rect)
            pygame.draw.rect(canvas, (0, 215, 255), c2_rect, 1)
            canvas.blit(font_sub.render("PLAYER 2 (CYBER CO-OP)", True, (100, 200, 255)), (665, 365))
            canvas.blit(font_desc.render("MOVE:   [Arrow Keys]", True, (200, 215, 235)), (665, 395))
            canvas.blit(font_desc.render("SHOOT:  [NUMPAD 0 / L Key]", True, (200, 215, 235)), (665, 420))
            canvas.blit(font_desc.render("NOVA:   [NUMPAD . / K Key]", True, (200, 215, 235)), (665, 445))
            canvas.blit(font_desc.render("START:  Press [2] or Click Right Box", True, (0, 255, 220)), (665, 475))

            prompt = font_sub.render("PRESS [1] FOR SOLO  |  PRESS [2] FOR 2-PLAYER CO-OP", True, (255, 225, 80))
            canvas.blit(prompt, prompt.get_rect(center=(WIDTH // 2, 595)))

        elif state in ('PLAYING', 'GAMEOVER'):
            for s in shards:
                s.draw(canvas)
            for p in projectiles:
                p.draw(canvas)
            for part in particles:
                part.draw(canvas)
            for snake in snakes:
                snake.draw(canvas)
            for pl in players:
                pl.draw(canvas)

            if state == 'PLAYING' and len(players) >= 1 and players[0].alive:
                mx, my = pygame.mouse.get_pos()
                pygame.draw.circle(canvas, (0, 255, 230), (mx, my), 7, 1)
                pygame.draw.line(canvas, (0, 255, 230), (mx - 10, my), (mx + 10, my), 1)
                pygame.draw.line(canvas, (0, 255, 230), (mx, my - 10), (mx, my + 10), 1)

            # P1 HUD
            if len(players) >= 1:
                p1 = players[0]
                pygame.draw.rect(canvas, (35, 15, 20), (25, 20, 180, 12))
                pygame.draw.rect(canvas, (255, 55, 75), (25, 20, int(180 * max(0.0, p1.hp / p1.max_hp)), 12))
                pygame.draw.rect(canvas, (255, 160, 175), (25, 20, 180, 12), 1)
                canvas.blit(font_hud_sm.render(f"P1 HP {p1.hp}/{p1.max_hp}", True, (255, 220, 230)), (30, 20))

                pygame.draw.rect(canvas, (15, 25, 40), (25, 38, 180, 10))
                pygame.draw.rect(canvas, (0, 215, 255), (25, 38, int(180 * max(0.0, p1.armor / p1.max_armor)), 10))
                pygame.draw.rect(canvas, (180, 240, 255), (25, 38, 180, 10), 1)
                canvas.blit(font_hud_sm.render(f"P1 ARMOR {p1.armor}/{p1.max_armor}", True, (210, 255, 255)), (30, 37))

                nova_ratio1 = 1.0 - (p1.nova_cd / p1.nova_max_cd)
                pygame.draw.rect(canvas, (25, 30, 20), (25, 54, 180, 8))
                col_n1 = (0, 255, 170) if p1.nova_cd == 0 else (120, 160, 90)
                pygame.draw.rect(canvas, col_n1, (25, 54, int(180 * nova_ratio1), 8))
                pygame.draw.rect(canvas, (160, 255, 200), (25, 54, 180, 8), 1)

            # P2 HUD
            if len(players) >= 2:
                p2 = players[1]
                pygame.draw.rect(canvas, (35, 15, 20), (220, 20, 180, 12))
                pygame.draw.rect(canvas, (255, 160, 50), (220, 20, int(180 * max(0.0, p2.hp / p2.max_hp)), 12))
                pygame.draw.rect(canvas, (255, 210, 175), (220, 20, 180, 12), 1)
                canvas.blit(font_hud_sm.render(f"P2 HP {p2.hp}/{p2.max_hp}", True, (255, 240, 220)), (225, 20))

                pygame.draw.rect(canvas, (15, 25, 40), (220, 38, 180, 10))
                pygame.draw.rect(canvas, (255, 215, 0), (220, 38, int(180 * max(0.0, p2.armor / p2.max_armor)), 10))
                pygame.draw.rect(canvas, (255, 245, 180), (220, 38, 180, 10), 1)
                canvas.blit(font_hud_sm.render(f"P2 ARMOR {p2.armor}/{p2.max_armor}", True, (255, 245, 210)), (225, 37))

                nova_ratio2 = 1.0 - (p2.nova_cd / p2.nova_max_cd)
                pygame.draw.rect(canvas, (25, 30, 20), (220, 54, 180, 8))
                col_n2 = (255, 215, 0) if p2.nova_cd == 0 else (160, 140, 70)
                pygame.draw.rect(canvas, col_n2, (220, 54, int(180 * nova_ratio2), 8))
                pygame.draw.rect(canvas, (255, 240, 170), (220, 54, 180, 8), 1)

            target_snakes, current_size_scale = get_tier_info(level)
            scale_pct = int(current_size_scale * 100)
            canvas.blit(font_hud.render(f"SNAKES: {len(snakes)} (SCALE: {scale_pct}%)", True, (80, 255, 120)), (25, 70))
            canvas.blit(font_hud.render(f"LEVEL: {level}", True, (255, 205, 50)), (WIDTH // 2 - 35, 20))
            canvas.blit(font_hud.render(f"SCORE: {score}", True, (220, 220, 220)), (WIDTH - 220, 20))
            canvas.blit(font_hud.render(f"HI-SCORE: {high_score}", True, (255, 215, 0)), (WIDTH - 220, 40))

            audio_str = "MUTED" if audio_muted else "ON"
            pad_str = " | PAD: CONNECTED" if joysticks else ""
            mode_str = "CO-OP" if num_players == 2 else "SOLO"
            controls_hud = f"MODE: {mode_str} | [WASD / ARROWS: MOVE] [CLICK/NUM0: HEADSHOT] [E/NUM.: NOVA] [M: {audio_str}]{pad_str}"
            canvas.blit(font_hud.render(controls_hud, True, (0, 215, 255)), (25, HEIGHT - 35))

            if state == 'GAMEOVER':
                overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                overlay.fill((8, 10, 22, 220))
                canvas.blit(overlay, (0, 0))

                txt_over = font_big.render("MISSION FAILED", True, (255, 60, 80))
                txt_stats = font_hud.render(f"REACHED LEVEL {level}  |  FINAL SCORE: {score}  |  BEST: {high_score}", True, (220, 220, 220))
                txt_restart = font_hud.render("CLICK SCREEN OR PRESS [R] TO RESTART  |  [ESC] FOR BRIEFING MENU", True, (0, 255, 220))

                canvas.blit(txt_over, txt_over.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 35)))
                canvas.blit(txt_stats, txt_stats.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 15)))
                canvas.blit(txt_restart, txt_restart.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 55)))

        # Screen Shake
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