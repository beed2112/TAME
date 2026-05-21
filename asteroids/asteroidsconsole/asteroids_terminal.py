#!/usr/bin/env python3
import curses
import math
import os
import random
import time
from dataclasses import dataclass


TICK_SECONDS = 0.02
MIN_WIDTH = 80
MIN_HEIGHT = 26
FIELD_WIDTH = 62
FIELD_HEIGHT = 21
SCORE_FILE_NAME = ".asteroids_console"
INITIAL_LIVES = 3
ROTATION_STEP = 18
THRUST_ACCEL = 12.0
DRAG = 0.985
MAX_SPEED = 20.0
BULLET_SPEED = 28.0
BULLET_LIFE = 1.2
MAX_BULLETS = 4
SHIP_RESPAWN_INVULN = 2.2
HYPERSPACE_COOLDOWN = 1.0
EXTRA_LIFE_SCORE = 10000
ASTEROID_POINTS = {"L": 20, "M": 50, "S": 100}
SAUCER_POINTS = {"L": 200, "S": 1000}
ASTEROID_RADII = {"L": 2.4, "M": 1.7, "S": 1.1}
ASTEROID_SPEEDS = {"L": (2.0, 4.5), "M": (4.0, 6.8), "S": (6.0, 9.0)}
SAUCER_RADII = {"L": 1.8, "S": 1.4}
SAUCER_SPEEDS = {"L": 6.0, "S": 8.0}
SAUCER_BULLET_SPEED = 20.0
SAUCER_FIRE_DELAY = {"L": (1.1, 1.8), "S": (0.7, 1.2)}
SAUCER_SPAWN_DELAY = (9.0, 15.0)


SHIP_MODELS = {
    0: [(-2, -1), (-2, 1), (-1, 0), (0, 0), (1, 0)],
    1: [(-1, -2), (-2, 0), (-1, 1), (0, 0), (1, 1)],
    2: [(-1, -2), (1, -2), (0, -1), (0, 0), (0, 1)],
    3: [(1, -2), (0, -2), (-1, -1), (0, 0), (-1, 1)],
    4: [(2, -1), (2, 1), (1, 0), (0, 0), (-1, 0)],
    5: [(1, 2), (2, 0), (1, -1), (0, 0), (-1, -1)],
    6: [(-1, 2), (1, 2), (0, 1), (0, 0), (0, -1)],
    7: [(-1, 2), (0, 2), (1, 1), (0, 0), (1, -1)],
}

ROCK_MODELS = {
    "L": [
        [(-2, 0), (-1, -1), (0, -1), (1, 0), (0, 1), (-1, 1)],
        [(-2, 0), (-1, -1), (1, -1), (2, 0), (1, 1), (-1, 1)],
        [(-1, -1), (0, -1), (2, 0), (1, 1), (0, 1), (-2, 0)],
        [(-2, 0), (0, -1), (1, -1), (2, 0), (0, 1), (-1, 1)],
    ],
    "M": [
        [(-1, 0), (0, -1), (1, 0), (0, 1)],
        [(-1, -1), (1, -1), (1, 0), (-1, 1)],
        [(-1, 0), (0, -1), (1, -1), (0, 1)],
        [(-1, -1), (0, -1), (1, 0), (-1, 1)],
    ],
    "S": [
        [(0, 0), (1, 0)],
        [(0, -1), (0, 0)],
        [(0, 0), (1, -1)],
        [(-1, 0), (0, 0)],
    ],
}


@dataclass
class Ship:
    x: float
    y: float
    dx: float = 0.0
    dy: float = 0.0
    angle: int = 0
    thrusting: bool = False
    invuln_until: float = 0.0


@dataclass
class Bullet:
    x: float
    y: float
    dx: float
    dy: float
    expires_at: float
    owner: str = "ship"


@dataclass
class Asteroid:
    x: float
    y: float
    dx: float
    dy: float
    size: str
    spin: int
    phase: int = 0


@dataclass
class Saucer:
    x: float
    y: float
    dx: float
    dy: float
    size: str
    next_shot_at: float


class Game:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.h = 0
        self.w = 0
        self.use_colors = False
        self.running = True
        self.paused = False
        self.game_over = False
        self.score = 0
        self.high_score = 0
        self.games_played = 0
        self.top_scores = []
        self.level = 1
        self.lives = INITIAL_LIVES
        self.extra_life_threshold = EXTRA_LIFE_SCORE
        self.last_frame_at = time.monotonic()
        self.last_shot_at = 0.0
        self.last_hyperspace_at = -10.0
        self.ship = Ship(FIELD_WIDTH / 2, FIELD_HEIGHT / 2)
        self.bullets = []
        self.asteroids = []
        self.saucer = None
        self.next_saucer_at = time.monotonic() + random.uniform(*SAUCER_SPAWN_DELAY)
        self.message = "PRESS ANY KEY"

    def setup(self):
        try:
            curses.curs_set(0)
        except curses.error:
            pass
        self.stdscr.nodelay(True)
        self.stdscr.keypad(True)
        self.stdscr.timeout(0)
        self.refresh_size()
        if self.h < MIN_HEIGHT or self.w < MIN_WIDTH:
            raise RuntimeError(f"Terminal too small. Need at least {MIN_WIDTH}x{MIN_HEIGHT}.")
        if curses.has_colors():
            curses.start_color()
            curses.use_default_colors()
            curses.init_pair(1, curses.COLOR_WHITE, -1)
            curses.init_pair(2, curses.COLOR_CYAN, -1)
            curses.init_pair(3, curses.COLOR_YELLOW, -1)
            curses.init_pair(4, curses.COLOR_RED, -1)
            curses.init_pair(5, curses.COLOR_GREEN, -1)
            curses.init_pair(6, curses.COLOR_MAGENTA, -1)
            self.use_colors = True
        self.load_score_file()
        self.reset_wave(reset_score=True)

    def refresh_size(self):
        self.h, self.w = self.stdscr.getmaxyx()

    def color_attr(self, pair_id):
        return curses.color_pair(pair_id) if self.use_colors else 0

    def score_file_path(self):
        return os.path.join(os.path.expanduser("~"), SCORE_FILE_NAME)

    def load_score_file(self):
        path = self.score_file_path()
        try:
            with open(path, "r", encoding="utf-8") as handle:
                lines = [line.strip() for line in handle.readlines() if line.strip()]
        except FileNotFoundError:
            return
        except OSError:
            return
        if len(lines) == 1 and lines[0].isdigit():
            legacy_score = int(lines[0])
            self.high_score = max(self.high_score, legacy_score)
            self.top_scores = [{"name": self.default_player_name(), "score": legacy_score}]
            return
        parsed = {}
        entries = []
        for line in lines:
            if line.startswith("entry="):
                payload = line[len("entry="):]
                if "|" in payload:
                    raw_name, raw_score = payload.rsplit("|", 1)
                elif ":" in payload:
                    raw_name, raw_score = payload.rsplit(":", 1)
                else:
                    continue
                name = self.sanitize_name(raw_name)
                if raw_score.strip().isdigit():
                    entries.append({"name": name, "score": int(raw_score.strip())})
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            parsed[key.strip()] = value.strip()
        if parsed.get("games_played", "").isdigit():
            self.games_played = int(parsed["games_played"])
        high_from_file = int(parsed["high_score"]) if parsed.get("high_score", "").isdigit() else 0
        self.top_scores = sorted(entries, key=lambda item: item["score"], reverse=True)[:10]
        top_high = self.top_scores[0]["score"] if self.top_scores else 0
        self.high_score = max(self.high_score, high_from_file, top_high)

    def save_score_file(self):
        self.high_score = max(self.high_score, self.score)
        try:
            with open(self.score_file_path(), "w", encoding="utf-8") as handle:
                lines = [
                    f"high_score={self.high_score}",
                    f"last_score={self.score}",
                    f"games_played={self.games_played}",
                ]
                for entry in self.top_scores[:10]:
                    lines.append(f"entry={entry['name']}|{entry['score']}")
                handle.write("\n".join(lines) + "\n")
        except OSError:
            pass

    def default_player_name(self):
        uname = os.environ.get("USER") or os.environ.get("LOGNAME")
        if uname:
            return self.sanitize_name(uname)
        return "PLAYER"

    def sanitize_name(self, name):
        cleaned = "".join(ch for ch in str(name).upper() if ch.isalnum() or ch in "_- ")
        return (cleaned.strip()[:8] or "PLAYER")

    def score_qualifies_top10(self):
        if self.score <= 0:
            return False
        if len(self.top_scores) < 10:
            return True
        return self.score > self.top_scores[-1]["score"]

    def add_top_score(self, name, score):
        self.top_scores.append({"name": self.sanitize_name(name), "score": int(score)})
        self.top_scores = sorted(self.top_scores, key=lambda item: item["score"], reverse=True)[:10]
        if self.top_scores:
            self.high_score = max(self.high_score, self.top_scores[0]["score"])

    def prompt_for_name(self):
        default = self.default_player_name()
        buf = list(default)
        self.stdscr.nodelay(False)
        while True:
            self.stdscr.erase()
            title = "NEW TOP 10 SCORE"
            prompt = "Enter name (max 8 chars):"
            hint = "ENTER confirm | BACKSPACE edit"
            current = "".join(buf)[:8]
            self.safe_addstr(self.h // 2 - 2, max(1, self.w // 2 - len(title) // 2), title, self.color_attr(6) | curses.A_BOLD)
            self.safe_addstr(self.h // 2, max(1, self.w // 2 - len(prompt) // 2), prompt, self.color_attr(1))
            self.safe_addstr(self.h // 2 + 1, max(1, self.w // 2 - 5), f"[{current:<8}]", self.color_attr(2) | curses.A_BOLD)
            self.safe_addstr(self.h // 2 + 3, max(1, self.w // 2 - len(hint) // 2), hint, self.color_attr(1))
            self.stdscr.refresh()
            ch = self.stdscr.getch()
            if ch in (10, 13, curses.KEY_ENTER):
                break
            if ch in (curses.KEY_BACKSPACE, 127, 8):
                if buf:
                    buf.pop()
                continue
            if 32 <= ch <= 126 and len(buf) < 8:
                char = chr(ch).upper()
                if char.isalnum() or char in "_- ":
                    buf.append(char)
        self.stdscr.nodelay(True)
        return self.sanitize_name("".join(buf).strip() or default)

    def show_top10_intro(self, seconds=3.0):
        end_time = time.monotonic() + seconds
        self.stdscr.nodelay(True)
        while time.monotonic() < end_time:
            self.stdscr.erase()
            self.safe_addstr(1, max(1, self.w // 2 - 6), "TOP 10 SCORES", self.color_attr(6) | curses.A_BOLD)
            self.safe_addstr(2, max(1, self.w // 2 - 8), "NAME     SCORE", self.color_attr(1) | curses.A_BOLD)
            if self.top_scores:
                for idx, entry in enumerate(self.top_scores[:10], start=1):
                    y = 2 + idx
                    if y >= self.h - 2:
                        break
                    line = f"{idx:>2}. {entry['name']:<8} {entry['score']:>6}"
                    self.safe_addstr(y, max(1, self.w // 2 - 10), line, self.color_attr(1))
            else:
                self.safe_addstr(5, max(1, self.w // 2 - 6), "NO SCORES YET", self.color_attr(1))
            self.stdscr.refresh()
            time.sleep(0.05)

    def finalize_score_submission(self):
        if self.score_qualifies_top10():
            self.add_top_score(self.prompt_for_name(), self.score)
        self.high_score = max(self.high_score, self.score)
        self.games_played += 1
        self.save_score_file()

    def safe_addstr(self, y, x, text, attr=0):
        if y < 0 or y >= self.h or x >= self.w:
            return
        if x < 0:
            text = text[-x:]
            x = 0
        text = text[: max(0, self.w - x)]
        if not text:
            return
        try:
            self.stdscr.addstr(y, x, text, attr)
        except curses.error:
            pass

    def field_left(self):
        return 1

    def field_top(self):
        return 3

    def wrap_x(self, value):
        return value % FIELD_WIDTH

    def wrap_y(self, value):
        return value % FIELD_HEIGHT

    def reset_wave(self, reset_score=False):
        if reset_score:
            self.score = 0
            self.level = 1
            self.lives = INITIAL_LIVES
            self.extra_life_threshold = EXTRA_LIFE_SCORE
        self.bullets = []
        self.ship = Ship(FIELD_WIDTH / 2, FIELD_HEIGHT / 2, angle=0, invuln_until=time.monotonic() + SHIP_RESPAWN_INVULN)
        self.saucer = None
        self.next_saucer_at = time.monotonic() + random.uniform(*SAUCER_SPAWN_DELAY)
        self.spawn_asteroid_wave()
        self.message = "CLEAR THE FIELD"

    def spawn_asteroid_wave(self):
        self.asteroids = []
        for _ in range(min(8, 4 + self.level)):
            edge = random.choice(["top", "bottom", "left", "right"])
            if edge == "top":
                x, y = random.uniform(0, FIELD_WIDTH), 1.0
            elif edge == "bottom":
                x, y = random.uniform(0, FIELD_WIDTH), FIELD_HEIGHT - 1.0
            elif edge == "left":
                x, y = 1.0, random.uniform(0, FIELD_HEIGHT)
            else:
                x, y = FIELD_WIDTH - 1.0, random.uniform(0, FIELD_HEIGHT)
            if abs(x - self.ship.x) < 7 and abs(y - self.ship.y) < 5:
                x = self.wrap_x(x + 16)
                y = self.wrap_y(y + 8)
            self.asteroids.append(self.make_asteroid("L", x, y))

    def make_asteroid(self, size, x, y):
        speed_low, speed_high = ASTEROID_SPEEDS[size]
        angle = random.uniform(0, math.tau)
        speed = random.uniform(speed_low, speed_high)
        return Asteroid(
            x=x,
            y=y,
            dx=math.cos(angle) * speed,
            dy=math.sin(angle) * speed,
            size=size,
            spin=random.choice([-1, 1]),
            phase=random.randint(0, 3),
        )

    def ship_orientation(self):
        idx = int(((self.ship.angle % 360) + (ROTATION_STEP / 2)) // ROTATION_STEP) % 20
        mapping = {0: 0, 1: 0, 2: 1, 3: 1, 4: 2, 5: 2, 6: 3, 7: 3, 8: 4, 9: 4, 10: 4, 11: 5, 12: 5, 13: 6, 14: 6, 15: 7, 16: 7, 17: 0, 18: 0, 19: 0}
        return mapping[idx]

    def ship_cells(self):
        model = SHIP_MODELS[self.ship_orientation()]
        return [(self.wrap_x(self.ship.x + dx), self.wrap_y(self.ship.y + dy)) for dx, dy in model]

    def handle_input(self):
        self.ship.thrusting = False
        while True:
            key = self.stdscr.getch()
            if key == -1:
                return
            if key == curses.KEY_RESIZE:
                self.refresh_size()
                continue
            if key in (ord("q"), ord("Q")):
                self.running = False
                return
            if key in (27, ord("p"), ord("P")):
                self.paused = not self.paused
                continue
            if self.paused or self.game_over:
                continue
            if key == curses.KEY_LEFT:
                self.ship.angle = (self.ship.angle - ROTATION_STEP) % 360
            elif key == curses.KEY_RIGHT:
                self.ship.angle = (self.ship.angle + ROTATION_STEP) % 360
            elif key in (curses.KEY_UP, ord("w"), ord("W")):
                self.apply_thrust()
            elif key == ord(" "):
                self.fire_bullet()
            elif key in (ord("h"), ord("H")):
                self.hyperspace()

    def apply_thrust(self):
        radians = math.radians(self.ship.angle - 90)
        self.ship.dx += math.cos(radians) * THRUST_ACCEL * TICK_SECONDS
        self.ship.dy += math.sin(radians) * THRUST_ACCEL * TICK_SECONDS
        speed = math.hypot(self.ship.dx, self.ship.dy)
        if speed > MAX_SPEED:
            scale = MAX_SPEED / speed
            self.ship.dx *= scale
            self.ship.dy *= scale
        self.ship.thrusting = True

    def fire_bullet(self):
        now = time.monotonic()
        if len(self.bullets) >= MAX_BULLETS or now - self.last_shot_at < 0.13:
            return
        radians = math.radians(self.ship.angle - 90)
        nose_x = self.ship.x + math.cos(radians) * 1.5
        nose_y = self.ship.y + math.sin(radians) * 1.5
        bullet_dx = self.ship.dx + (math.cos(radians) * BULLET_SPEED)
        bullet_dy = self.ship.dy + (math.sin(radians) * BULLET_SPEED)
        self.bullets.append(Bullet(nose_x, nose_y, bullet_dx, bullet_dy, now + BULLET_LIFE, owner="ship"))
        self.last_shot_at = now

    def hyperspace(self):
        now = time.monotonic()
        if now - self.last_hyperspace_at < HYPERSPACE_COOLDOWN:
            return
        self.last_hyperspace_at = now
        self.ship.x = random.uniform(0, FIELD_WIDTH)
        self.ship.y = random.uniform(0, FIELD_HEIGHT)
        self.ship.dx *= 0.4
        self.ship.dy *= 0.4
        if random.random() < 0.1:
            self.destroy_ship("HYPERSPACE FAILURE")

    def update(self):
        if self.paused or self.game_over:
            return
        now = time.monotonic()
        dt = min(0.04, now - self.last_frame_at)
        self.last_frame_at = now
        self.ship.x = self.wrap_x(self.ship.x + (self.ship.dx * dt))
        self.ship.y = self.wrap_y(self.ship.y + (self.ship.dy * dt))
        self.ship.dx *= DRAG
        self.ship.dy *= DRAG

        next_bullets = []
        for bullet in self.bullets:
            if bullet.expires_at <= now:
                continue
            bullet.x = self.wrap_x(bullet.x + (bullet.dx * dt))
            bullet.y = self.wrap_y(bullet.y + (bullet.dy * dt))
            next_bullets.append(bullet)
        self.bullets = next_bullets

        for asteroid in self.asteroids:
            asteroid.x = self.wrap_x(asteroid.x + (asteroid.dx * dt))
            asteroid.y = self.wrap_y(asteroid.y + (asteroid.dy * dt))
            asteroid.phase = (asteroid.phase + asteroid.spin) % 4

        self.update_saucer(now, dt)

        self.resolve_bullet_hits()
        self.resolve_ship_hits(now)

        if not self.asteroids:
            self.level += 1
            self.spawn_asteroid_wave()
            self.ship.invuln_until = now + SHIP_RESPAWN_INVULN
            self.saucer = None
            self.next_saucer_at = now + random.uniform(*SAUCER_SPAWN_DELAY)
            self.message = f"WAVE {self.level}"

        while self.score >= self.extra_life_threshold:
            self.lives += 1
            self.extra_life_threshold += EXTRA_LIFE_SCORE
            self.message = "EXTRA SHIP"

    def schedule_next_saucer(self, now):
        self.next_saucer_at = now + random.uniform(*SAUCER_SPAWN_DELAY)

    def spawn_saucer(self, now):
        size = "S" if self.level >= 4 and random.random() < 0.55 else "L"
        direction = random.choice([-1, 1])
        x = 0.0 if direction > 0 else FIELD_WIDTH - 1.0
        y = random.uniform(2.0, FIELD_HEIGHT - 2.0)
        dy = random.uniform(-1.4, 1.4)
        self.saucer = Saucer(
            x=x,
            y=y,
            dx=SAUCER_SPEEDS[size] * direction,
            dy=dy,
            size=size,
            next_shot_at=now + random.uniform(*SAUCER_FIRE_DELAY[size]),
        )
        self.message = "SAUCER INBOUND"

    def update_saucer(self, now, dt):
        if self.saucer is None:
            if now >= self.next_saucer_at and self.asteroids:
                self.spawn_saucer(now)
            return
        self.saucer.x += self.saucer.dx * dt
        self.saucer.y = min(FIELD_HEIGHT - 2.0, max(1.0, self.saucer.y + (self.saucer.dy * dt)))
        if self.saucer.x < -3 or self.saucer.x > FIELD_WIDTH + 3:
            self.saucer = None
            self.schedule_next_saucer(now)
            return
        if now >= self.saucer.next_shot_at:
            self.fire_saucer_bullet(now)
            if self.saucer is not None:
                self.saucer.next_shot_at = now + random.uniform(*SAUCER_FIRE_DELAY[self.saucer.size])

    def fire_saucer_bullet(self, now):
        if self.saucer is None:
            return
        base_angle = math.atan2(self.ship.y - self.saucer.y, self.ship.x - self.saucer.x)
        spread = 0.45 if self.saucer.size == "L" else 0.14
        angle = base_angle + random.uniform(-spread, spread)
        self.bullets.append(
            Bullet(
                self.saucer.x,
                self.saucer.y,
                math.cos(angle) * SAUCER_BULLET_SPEED,
                math.sin(angle) * SAUCER_BULLET_SPEED,
                now + BULLET_LIFE,
                owner="saucer",
            )
        )

    def resolve_bullet_hits(self):
        remaining_asteroids = []
        spawned = []
        for asteroid in self.asteroids:
            hit_index = None
            for idx, bullet in enumerate(self.bullets):
                if bullet.owner != "ship":
                    continue
                if self.distance_wrap(bullet.x, bullet.y, asteroid.x, asteroid.y) <= ASTEROID_RADII[asteroid.size]:
                    hit_index = idx
                    break
            if hit_index is None:
                remaining_asteroids.append(asteroid)
                continue
            self.bullets.pop(hit_index)
            self.score += ASTEROID_POINTS[asteroid.size]
            self.high_score = max(self.high_score, self.score)
            if asteroid.size == "L":
                spawned.extend([self.make_child_asteroid("M", asteroid), self.make_child_asteroid("M", asteroid)])
            elif asteroid.size == "M":
                spawned.extend([self.make_child_asteroid("S", asteroid), self.make_child_asteroid("S", asteroid)])
        self.asteroids = remaining_asteroids + spawned
        self.resolve_saucer_hits()

    def make_child_asteroid(self, size, parent):
        child = self.make_asteroid(size, parent.x, parent.y)
        child.dx += parent.dx * 0.4
        child.dy += parent.dy * 0.4
        return child

    def resolve_ship_hits(self, now):
        if now < self.ship.invuln_until:
            return
        if self.saucer and self.distance_wrap(self.ship.x, self.ship.y, self.saucer.x, self.saucer.y) <= (SAUCER_RADII[self.saucer.size] + 0.6):
            self.destroy_ship("SAUCER COLLISION")
            return
        for bullet in self.bullets:
            if bullet.owner == "saucer" and self.distance_wrap(self.ship.x, self.ship.y, bullet.x, bullet.y) <= 1.0:
                bullet.expires_at = 0.0
                self.destroy_ship("SHOT DOWN")
                return
        for cell_x, cell_y in self.ship_cells():
            for asteroid in self.asteroids:
                if self.distance_wrap(cell_x, cell_y, asteroid.x, asteroid.y) <= ASTEROID_RADII[asteroid.size]:
                    self.destroy_ship("SHIP LOST")
                    return

    def resolve_saucer_hits(self):
        if self.saucer is None:
            return
        for bullet in self.bullets:
            if bullet.owner != "ship":
                continue
            if self.distance_wrap(bullet.x, bullet.y, self.saucer.x, self.saucer.y) <= SAUCER_RADII[self.saucer.size]:
                bullet.expires_at = 0.0
                self.score += SAUCER_POINTS[self.saucer.size]
                self.high_score = max(self.high_score, self.score)
                self.saucer = None
                self.schedule_next_saucer(time.monotonic())
                self.message = "SAUCER DESTROYED"
                return

    def destroy_ship(self, message):
        self.lives -= 1
        if self.lives <= 0:
            self.game_over = True
            self.running = False
            return
        self.ship = Ship(FIELD_WIDTH / 2, FIELD_HEIGHT / 2, angle=0, invuln_until=time.monotonic() + SHIP_RESPAWN_INVULN)
        self.message = message

    def distance_wrap(self, x1, y1, x2, y2):
        dx = abs(x1 - x2)
        dy = abs(y1 - y2)
        dx = min(dx, FIELD_WIDTH - dx)
        dy = min(dy, FIELD_HEIGHT - dy)
        return math.hypot(dx, dy)

    def draw(self):
        self.refresh_size()
        self.stdscr.erase()
        if self.h < MIN_HEIGHT or self.w < MIN_WIDTH:
            self.safe_addstr(self.h // 2, max(1, self.w // 2 - 9), "TERMINAL TOO SMALL", self.color_attr(4) | curses.A_BOLD)
            self.safe_addstr(self.h // 2 + 1, max(1, self.w // 2 - 17), f"Need at least {MIN_WIDTH}x{MIN_HEIGHT}", self.color_attr(1))
            self.stdscr.refresh()
            return
        self.draw_frame()
        self.draw_objects()
        self.draw_sidebar()
        self.stdscr.refresh()

    def draw_frame(self):
        top = self.field_top()
        left = self.field_left()
        self.safe_addstr(0, left, "ASTEROIDS CONSOLE", self.color_attr(2) | curses.A_BOLD)
        self.safe_addstr(1, left, f"SCORE {self.score:05d}", self.color_attr(1) | curses.A_BOLD)
        self.safe_addstr(1, left + 18, f"HIGH {max(self.high_score, self.score):05d}", self.color_attr(1))
        self.safe_addstr(top - 1, left - 1, "+" + ("-" * FIELD_WIDTH) + "+", self.color_attr(1))
        for row in range(FIELD_HEIGHT):
            self.safe_addstr(top + row, left - 1, "|", self.color_attr(1))
            self.safe_addstr(top + row, left + FIELD_WIDTH, "|", self.color_attr(1))
            self.safe_addstr(top + row, left, " " * FIELD_WIDTH)
        self.safe_addstr(top + FIELD_HEIGHT, left - 1, "+" + ("-" * FIELD_WIDTH) + "+", self.color_attr(1))

    def draw_objects(self):
        top = self.field_top()
        left = self.field_left()
        for asteroid in self.asteroids:
            rock_attr = self.color_attr(3) | curses.A_BOLD
            rock_cells = ROCK_MODELS[asteroid.size][asteroid.phase % len(ROCK_MODELS[asteroid.size])]
            for dx, dy in rock_cells:
                self.safe_addstr(
                    top + int(round(self.wrap_y(asteroid.y + dy))),
                    left + int(round(self.wrap_x(asteroid.x + dx))),
                    "#",
                    rock_attr,
                )
        for bullet in self.bullets:
            glyph = "." if bullet.owner == "ship" else "o"
            attr = self.color_attr(1) | curses.A_BOLD if bullet.owner == "ship" else self.color_attr(4) | curses.A_BOLD
            self.safe_addstr(top + int(round(bullet.y)), left + int(round(bullet.x)), glyph, attr)
        if self.saucer:
            saucer_cells = [(-2, 0), (-1, -1), (0, -1), (1, -1), (2, 0), (1, 1), (-1, 1)]
            saucer_attr = self.color_attr(6 if self.saucer.size == "S" else 2) | curses.A_BOLD
            for dx, dy in saucer_cells:
                self.safe_addstr(
                    top + int(round(self.saucer.y + dy)),
                    left + int(round(self.saucer.x + dx)),
                    "=",
                    saucer_attr,
                )
        ship_attr = self.color_attr(5) | curses.A_BOLD
        if time.monotonic() < self.ship.invuln_until and int(time.monotonic() * 10) % 2 == 0:
            ship_attr = self.color_attr(6) | curses.A_BOLD
        for cell_x, cell_y in self.ship_cells():
            self.safe_addstr(top + int(round(cell_y)), left + int(round(cell_x)), "#", ship_attr)
        if self.ship.thrusting:
            radians = math.radians(self.ship.angle + 90)
            flame_x = self.wrap_x(self.ship.x + math.cos(radians) * 1.5)
            flame_y = self.wrap_y(self.ship.y + math.sin(radians) * 1.5)
            self.safe_addstr(top + int(round(flame_y)), left + int(round(flame_x)), "*", self.color_attr(4) | curses.A_BOLD)

    def draw_sidebar(self):
        left = self.field_left() + FIELD_WIDTH + 3
        top = self.field_top() + 1
        lines = [
            f"W {self.level:02d}",
            f"L {self.lives}",
            f"R {len(self.asteroids):02d}",
            f"U {self.saucer.size if self.saucer else '--'}",
            "",
            "CTRL",
            "L/R turn",
            "UP/W go",
            "SP fire",
            "H hyper",
            "ESC p",
            "Q quit",
            "",
            "INFO",
            "Wrap",
            "Inertia",
            "Split",
            "UFO",
        ]
        for idx, line in enumerate(lines):
            attr = self.color_attr(1)
            if line in ("CTRL", "INFO"):
                attr = self.color_attr(6) | curses.A_BOLD
            self.safe_addstr(top + idx, left, line, attr)
        status_y = self.field_top() + FIELD_HEIGHT - 1
        if self.paused:
            self.safe_addstr(status_y, left, "PAUSE", self.color_attr(3) | curses.A_BOLD)
        elif self.message:
            self.safe_addstr(status_y, left, self.message[:12], self.color_attr(2) | curses.A_BOLD)

    def intro_screen(self):
        self.stdscr.nodelay(False)
        self.stdscr.erase()
        lines = [
            "ASTEROIDS CONSOLE",
            "",
            "Rotate, thrust, and clear the field.",
            "Ship movement uses inertia and wraparound.",
            "Enemy saucers sweep in and shoot back.",
            "",
            "Controls",
            "Left/Right: rotate",
            "Up or W: thrust",
            "Space: fire",
            "H: hyperspace",
            "Q: quit",
            "",
            "Press any key to start",
        ]
        for idx, line in enumerate(lines):
            attr = self.color_attr(2) | curses.A_BOLD if idx == 0 else self.color_attr(1)
            self.safe_addstr((self.h // 2 - 6) + idx, max(2, self.w // 2 - len(line) // 2), line, attr)
        self.stdscr.refresh()
        self.stdscr.getch()
        self.stdscr.nodelay(True)

    def game_over_screen(self):
        self.finalize_score_submission()
        self.show_top10_intro(seconds=2.5)
        self.stdscr.nodelay(False)
        self.stdscr.erase()
        title = "GAME OVER"
        self.safe_addstr(self.h // 2 - 3, max(1, self.w // 2 - len(title) // 2), title, self.color_attr(4) | curses.A_BOLD)
        self.safe_addstr(self.h // 2 - 1, max(1, self.w // 2 - 10), f"Score {self.score:05d}", self.color_attr(1))
        self.safe_addstr(self.h // 2, max(1, self.w // 2 - 10), f"High  {self.high_score:05d}", self.color_attr(1))
        self.safe_addstr(self.h // 2 + 2, max(1, self.w // 2 - 18), "Press any key to return to cabinet", self.color_attr(2) | curses.A_BOLD)
        self.stdscr.refresh()
        self.stdscr.getch()

    def run(self):
        self.intro_screen()
        self.last_frame_at = time.monotonic()
        while self.running:
            frame_started = time.monotonic()
            self.handle_input()
            self.update()
            self.draw()
            elapsed = time.monotonic() - frame_started
            if elapsed < TICK_SECONDS:
                time.sleep(TICK_SECONDS - elapsed)


def run(stdscr):
    game = Game(stdscr)
    game.setup()
    game.run()
    if game.game_over:
        game.game_over_screen()


if __name__ == "__main__":
    curses.wrapper(run)
