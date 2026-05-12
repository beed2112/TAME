#!/usr/bin/env python3
import argparse
import curses
import math
import os
import random
import time
from dataclasses import dataclass


TICK_SECONDS = 0.04
MIN_WIDTH = 80
MIN_HEIGHT = 26
WORLD_WIDTH = 320
HUD_ROWS = 4
PLAYER_SPEED = 1.8
PLAYER_VERTICAL_SPEED = 1.0
PLAYER_COOLDOWN = 0.06
PLAYER_INVULN_FRAMES = 45
PLAYER_RESPAWN_FRAMES = 12
SMART_BOMBS_PER_GAME = 3
HIGH_SCORE_FILE = ".defender_console"
BONUS_FRAMES = 60
HYPERSPACE_COOLDOWN = 1.4
PLAYER_SPRITE_RIGHT = "<A==>"
PLAYER_SPRITE_LEFT = "<==A>"
ENEMY_FIRE_COOLDOWN_SCALE = 4 / 3


@dataclass
class Bullet:
    x: float
    y: float
    dx: float
    dy: float
    from_enemy: bool
    ttl: int = 90


@dataclass
class Enemy:
    enemy_id: int
    kind: str
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    alive: bool = True
    cooldown: float = 0.0
    phase: float = 0.0
    target_human: int | None = None
    carrying_human: int | None = None


@dataclass
class Human:
    human_id: int
    x: float
    y: float
    state: str = "grounded"
    vy: float = 0.0
    carrier_id: int | None = None


@dataclass
class Star:
    x: float
    y: int
    speed: float
    glyph: str
    color: int


@dataclass
class Explosion:
    x: float
    y: float
    frames: int


@dataclass
class Mine:
    x: float
    y: float
    phase: float = 0.0


class Game:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.h = 0
        self.w = 0
        self.play_top = HUD_ROWS
        self.play_bottom = 0
        self.player_x = WORLD_WIDTH / 2
        self.player_y = 12.0
        self.player_dir = 1
        self.player_lives = 3
        self.smart_bombs = SMART_BOMBS_PER_GAME
        self.score = 0
        self.high_score = 0
        self.last_score = 0
        self.games_played = 0
        self.top_scores = []
        self.wave = 0
        self.running = True
        self.paused = False
        self.use_colors = False
        self.last_shot = 0.0
        self.last_hyperspace = -99.0
        self.invuln_frames = 0
        self.respawn_frames = 0
        self.bonus_frames = 0
        self.bonus_text = ""
        self.player_carry_human: int | None = None
        self.terrain = []
        self.humans: list[Human] = []
        self.enemies: list[Enemy] = []
        self.bullets: list[Bullet] = []
        self.stars: list[Star] = []
        self.explosions: list[Explosion] = []
        self.mines: list[Mine] = []
        self.enemy_id_seq = 1
        self.human_id_seq = 1

    def setup(self):
        try:
            curses.curs_set(0)
        except curses.error:
            pass
        self.stdscr.nodelay(True)
        self.stdscr.keypad(True)
        self.stdscr.timeout(0)
        self.h, self.w = self.stdscr.getmaxyx()
        if self.h < MIN_HEIGHT or self.w < MIN_WIDTH:
            raise RuntimeError(f"Terminal too small. Need at least {MIN_WIDTH}x{MIN_HEIGHT}.")
        self.play_bottom = self.h - 2

        if curses.has_colors():
            curses.start_color()
            curses.use_default_colors()
            curses.init_pair(1, curses.COLOR_WHITE, -1)
            curses.init_pair(2, curses.COLOR_RED, -1)
            curses.init_pair(3, curses.COLOR_CYAN, -1)
            curses.init_pair(4, curses.COLOR_YELLOW, -1)
            curses.init_pair(5, curses.COLOR_GREEN, -1)
            curses.init_pair(6, curses.COLOR_MAGENTA, -1)
            curses.init_pair(7, curses.COLOR_BLUE, -1)
            self.use_colors = True

        self.load_score_file()
        self.generate_terrain()
        self.spawn_stars()
        self.start_wave()

    def color_attr(self, pair_id):
        return curses.color_pair(pair_id) if self.use_colors else 0

    def score_file_path(self):
        return os.path.join(os.path.expanduser("~"), HIGH_SCORE_FILE)

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

        if parsed.get("high_score", "").isdigit():
            self.high_score = int(parsed["high_score"])
        if parsed.get("last_score", "").isdigit():
            self.last_score = int(parsed["last_score"])
        if parsed.get("games_played", "").isdigit():
            self.games_played = int(parsed["games_played"])

        self.top_scores = sorted(entries, key=lambda item: item["score"], reverse=True)[:10]
        if self.top_scores:
            self.high_score = max(self.high_score, self.top_scores[0]["score"])

    def save_score_file(self):
        self.high_score = max(self.high_score, self.score)
        lines = [
            f"high_score={self.high_score}",
            f"last_score={self.score}",
            f"games_played={self.games_played}",
        ]
        for entry in self.top_scores[:10]:
            lines.append(f"entry={entry['name']}|{entry['score']}")
        payload = "\n".join(lines) + "\n"
        try:
            with open(self.score_file_path(), "w", encoding="utf-8") as handle:
                handle.write(payload)
        except OSError:
            pass

    def default_player_name(self):
        uname = os.environ.get("USER") or os.environ.get("LOGNAME")
        if uname:
            return self.sanitize_name(uname)
        return "PLAYER"

    def sanitize_name(self, name):
        cleaned = "".join(ch for ch in str(name).upper() if ch.isalnum() or ch in "_- ")
        cleaned = cleaned.strip()
        return cleaned[:8] or "PLAYER"

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
        self.stdscr.keypad(True)

        while True:
            self.stdscr.erase()
            title = "NEW TOP 10 SCORE"
            prompt = "Enter name (max 8 chars):"
            hint = "ENTER confirm | BACKSPACE edit"
            current = "".join(buf)[:8]
            self.safe_addstr(self.h // 2 - 2, max(1, self.w // 2 - len(title) // 2), title, self.color_attr(2) | curses.A_BOLD)
            self.safe_addstr(self.h // 2, max(1, self.w // 2 - len(prompt) // 2), prompt, self.color_attr(1))
            self.safe_addstr(self.h // 2 + 1, max(1, self.w // 2 - 5), f"[{current:<8}]", self.color_attr(4) | curses.A_BOLD)
            self.safe_addstr(self.h // 2 + 3, max(1, self.w // 2 - len(hint) // 2), hint, self.color_attr(3))
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

        name = "".join(buf).strip() or default
        self.stdscr.nodelay(True)
        return self.sanitize_name(name)

    def show_top10_intro(self, seconds=3.0):
        end_time = time.monotonic() + seconds
        self.stdscr.nodelay(True)

        while time.monotonic() < end_time:
            self.stdscr.erase()
            self.safe_addstr(1, max(1, self.w // 2 - 6), "TOP 10 SCORES", self.color_attr(2) | curses.A_BOLD)
            self.safe_addstr(2, max(1, self.w // 2 - 8), "NAME     SCORE", self.color_attr(1) | curses.A_BOLD)

            if self.top_scores:
                for idx, entry in enumerate(self.top_scores[:10], start=1):
                    y = 2 + idx
                    if y >= self.h - 2:
                        break
                    line = f"{idx:>2}. {entry['name']:<8} {entry['score']:>6}"
                    self.safe_addstr(y, max(1, self.w // 2 - 10), line, self.color_attr(1))
            else:
                self.safe_addstr(5, max(1, self.w // 2 - 6), "NO SCORES YET", self.color_attr(3))

            self.stdscr.refresh()
            time.sleep(0.05)

    def finalize_score_submission(self):
        if self.score_qualifies_top10():
            name = self.prompt_for_name()
            self.add_top_score(name, self.score)

        self.high_score = max(self.high_score, self.score)
        self.games_played += 1
        self.save_score_file()

    def generate_terrain(self):
        base = self.play_bottom - 2
        amp_a = max(2, (self.play_bottom - self.play_top) // 6)
        amp_b = max(1, amp_a // 2)
        self.terrain = []
        for x in range(WORLD_WIDTH):
            value = (
                base
                - math.sin(x / 12.0) * amp_a
                - math.sin((x + 35) / 27.0) * amp_b
                - math.sin((x + 5) / 7.0) * 0.8
            )
            jitter = random.choice([0.0, 0.0, 0.0, 0.4, -0.4])
            surface = int(round(value + jitter))
            surface = max(self.play_top + 8, min(self.play_bottom, surface))
            self.terrain.append(surface)

    def spawn_stars(self):
        self.stars = []
        count = max(35, self.w // 2)
        glyphs = [".", ".", ".", "+", "*"]
        for _ in range(count):
            self.stars.append(
                Star(
                    x=random.uniform(0, WORLD_WIDTH),
                    y=random.randint(self.play_top + 1, self.play_bottom - 4),
                    speed=random.uniform(0.05, 0.24),
                    glyph=random.choice(glyphs),
                    color=random.choice([1, 3, 4, 7]),
                )
            )

    def start_wave(self):
        if self.wave > 0:
            survivors = sum(1 for human in self.humans if human.state == "grounded")
            if self.player_carry_human is not None:
                survivors += 1
            if survivors:
                bonus = survivors * 100
                self.score += bonus
                self.high_score = max(self.high_score, self.score)
                self.bonus_text = f"WAVE CLEAR +{bonus}"
                self.bonus_frames = BONUS_FRAMES

        self.wave += 1
        self.player_carry_human = None
        self.bullets = []
        self.explosions = []
        self.mines = []
        self.humans = []
        self.enemies = []

        self.player_x = WORLD_WIDTH / 2
        self.player_y = self.play_top + 9

        self.spawn_humans()
        self.spawn_wave_enemies()

    def spawn_humans(self):
        slots = 8
        step = WORLD_WIDTH // slots
        for idx in range(slots):
            base_x = idx * step + step // 2 + random.randint(-5, 5)
            x = float(base_x % WORLD_WIDTH)
            y = float(self.surface_y(x) - 1)
            self.humans.append(Human(self.next_human_id(), x, y))

    def spawn_wave_enemies(self):
        landers = min(5 + self.wave * 2, 14)
        mutants = min(max(0, self.wave - 2), 6)
        bombers = min(1 + (self.wave // 2), 4)
        wave_phase = ((self.wave - 1) % 4) + 1
        motherships = {1: 0, 2: 1, 3: 3, 4: 4}[wave_phase]

        for _ in range(landers):
            self.enemies.append(
                Enemy(
                    self.next_enemy_id(),
                    "lander",
                    random.uniform(0, WORLD_WIDTH),
                    random.uniform(self.play_top + 2, self.play_top + 10),
                    cooldown=random.uniform(0.3, 1.0) * ENEMY_FIRE_COOLDOWN_SCALE,
                    phase=random.uniform(0.0, math.tau),
                )
            )
        for _ in range(mutants):
            self.enemies.append(
                Enemy(
                    self.next_enemy_id(),
                    "mutant",
                    random.uniform(0, WORLD_WIDTH),
                    random.uniform(self.play_top + 1, self.play_top + 8),
                    cooldown=random.uniform(0.2, 0.8) * ENEMY_FIRE_COOLDOWN_SCALE,
                    phase=random.uniform(0.0, math.tau),
                )
            )
        for _ in range(bombers):
            self.enemies.append(
                Enemy(
                    self.next_enemy_id(),
                    "bomber",
                    random.uniform(0, WORLD_WIDTH),
                    random.uniform(self.play_top + 3, self.play_top + 12),
                    vx=random.choice([-0.45, 0.45]),
                    vy=random.choice([-0.15, 0.15]),
                    phase=random.uniform(0.0, math.tau),
                )
            )
        for _ in range(motherships):
            self.enemies.append(
                Enemy(
                    self.next_enemy_id(),
                    "mothership",
                    random.uniform(0, WORLD_WIDTH),
                    random.uniform(self.play_top + 2, self.play_top + 9),
                    vx=random.choice([-0.35, 0.35]),
                    cooldown=random.uniform(0.8, 1.4) * ENEMY_FIRE_COOLDOWN_SCALE,
                    phase=random.uniform(0.0, math.tau),
                )
            )

    def next_enemy_id(self):
        current = self.enemy_id_seq
        self.enemy_id_seq += 1
        return current

    def next_human_id(self):
        current = self.human_id_seq
        self.human_id_seq += 1
        return current

    def wrap_x(self, value):
        return value % WORLD_WIDTH

    def shortest_wrap_delta(self, source, target):
        delta = (target - source + WORLD_WIDTH / 2) % WORLD_WIDTH - WORLD_WIDTH / 2
        return delta

    def surface_y(self, world_x):
        return self.terrain[int(world_x) % WORLD_WIDTH]

    def camera_left(self):
        return self.wrap_x(self.player_x - (self.w // 2))

    def visible_dx(self, world_x):
        return (world_x - self.camera_left()) % WORLD_WIDTH

    def world_to_screen(self, world_x):
        dx = self.visible_dx(world_x)
        if 0 <= dx < self.w:
            return int(dx)
        return None

    def is_visible(self, world_x):
        return 0 <= self.visible_dx(world_x) < self.w

    def clamp_player_altitude(self):
        floor_y = self.surface_y(self.player_x) - 2
        self.player_y = max(self.play_top + 1, min(floor_y, self.player_y))

    def safe_addstr(self, y, x, text, attr=0):
        if y < 0 or y >= self.h:
            return
        if x >= self.w:
            return
        if x < 0:
            text = text[-x:]
            x = 0
        if not text:
            return
        text = text[: max(0, self.w - x)]
        if not text:
            return
        try:
            self.stdscr.addstr(y, x, text, attr)
        except curses.error:
            pass

    def safe_addch(self, y, x, ch, attr=0):
        if 0 <= y < self.h and 0 <= x < self.w:
            try:
                self.stdscr.addch(y, x, ch, attr)
            except curses.error:
                pass

    def enemy_glyph(self, enemy):
        if enemy.kind == "lander":
            return "V"
        if enemy.kind == "mutant":
            return "M"
        if enemy.kind == "bomber":
            return "B"
        if enemy.kind == "baiter":
            return "X"
        if enemy.kind == "mothership":
            return "W"
        return "s"

    def enemy_color(self, enemy):
        if enemy.kind == "lander":
            return self.color_attr(2)
        if enemy.kind == "mutant":
            return self.color_attr(6)
        if enemy.kind == "bomber":
            return self.color_attr(5)
        if enemy.kind == "baiter":
            return self.color_attr(3)
        if enemy.kind == "mothership":
            return self.color_attr(7)
        return self.color_attr(4)

    def player_sprite(self):
        return PLAYER_SPRITE_LEFT if self.player_dir < 0 else PLAYER_SPRITE_RIGHT

    def update_background(self):
        drift = -0.28 * self.player_dir
        for star in self.stars:
            star.x = self.wrap_x(star.x + drift * star.speed)

    def handle_input(self):
        key = self.stdscr.getch()
        while key != -1:
            if key in (ord("q"), ord("Q")):
                self.running = False
                return
            if key == 27:
                self.paused = not self.paused
                key = self.stdscr.getch()
                continue

            if self.paused or self.respawn_frames > 0:
                key = self.stdscr.getch()
                continue

            if key in (curses.KEY_UP, ord("w"), ord("W")):
                self.player_y -= PLAYER_VERTICAL_SPEED
            elif key in (curses.KEY_DOWN, ord("s"), ord("S")):
                self.player_y += PLAYER_VERTICAL_SPEED
            elif key in (curses.KEY_RIGHT, ord("d"), ord("D")):
                self.player_x = self.wrap_x(self.player_x + (PLAYER_SPEED * self.player_dir))
            elif key in (curses.KEY_LEFT, ord("a"), ord("A")):
                self.player_dir *= -1
                self.player_x = self.wrap_x(self.player_x + (PLAYER_SPEED * self.player_dir))
            elif key == ord(" "):
                self.fire_player_bullet()
            elif key in (ord("b"), ord("B")):
                self.use_smart_bomb()
            elif key in (ord("h"), ord("H")):
                self.use_hyperspace()
            key = self.stdscr.getch()

        self.clamp_player_altitude()

    def fire_player_bullet(self):
        now = time.monotonic()
        if now - self.last_shot < PLAYER_COOLDOWN:
            return
        self.last_shot = now
        muzzle_x = self.wrap_x(self.player_x + (1.6 * self.player_dir))
        self.bullets.append(
            Bullet(
                x=muzzle_x,
                y=self.player_y,
                dx=2.4 * self.player_dir,
                dy=0.0,
                from_enemy=False,
                ttl=50,
            )
        )

    def use_smart_bomb(self):
        if self.smart_bombs <= 0:
            return
        self.smart_bombs -= 1
        destroyed = 0
        for enemy in self.enemies:
            if not enemy.alive:
                continue
            if self.world_to_screen(enemy.x) is not None:
                self.destroy_enemy(enemy, smart_bomb=True)
                destroyed += 1
        self.bullets = [bullet for bullet in self.bullets if not bullet.from_enemy]
        if destroyed:
            self.bonus_text = f"SMART BOMB x{destroyed}"
            self.bonus_frames = BONUS_FRAMES // 2

    def use_hyperspace(self):
        now = time.monotonic()
        if now - self.last_hyperspace < HYPERSPACE_COOLDOWN:
            return
        self.last_hyperspace = now
        self.player_x = random.uniform(0, WORLD_WIDTH)
        self.player_y = random.uniform(self.play_top + 2, self.play_bottom - 8)
        self.clamp_player_altitude()
        if random.random() < 0.18:
            self.hit_player()

    def enemy_map(self):
        return {enemy.enemy_id: enemy for enemy in self.enemies if enemy.alive}

    def human_map(self):
        return {human.human_id: human for human in self.humans if human.state != "dead"}

    def available_humans(self):
        targeted = {
            enemy.target_human
            for enemy in self.enemies
            if enemy.alive and enemy.kind == "lander" and enemy.target_human is not None
        }
        return [
            human for human in self.humans
            if human.state == "grounded" and human.human_id not in targeted
        ]

    def update_enemies(self):
        self.maybe_spawn_baiter()
        enemy_by_id = self.enemy_map()
        for enemy in self.enemies:
            if not enemy.alive:
                continue

            enemy.phase += 0.14
            enemy.cooldown = max(0.0, enemy.cooldown - TICK_SECONDS)

            if enemy.kind == "lander":
                self.update_lander(enemy, enemy_by_id)
            elif enemy.kind == "mutant":
                self.update_mutant(enemy)
            elif enemy.kind == "bomber":
                self.update_bomber(enemy)
            elif enemy.kind == "baiter":
                self.update_baiter(enemy)
            elif enemy.kind == "mothership":
                self.update_mothership(enemy)
            else:
                self.update_swarmer(enemy)

            enemy.x = self.wrap_x(enemy.x)
            enemy.y = max(self.play_top + 1, min(self.play_bottom - 1, enemy.y))

    def update_lander(self, enemy, enemy_by_id):
        human_by_id = self.human_map()
        if enemy.carrying_human is not None:
            carried = human_by_id.get(enemy.carrying_human)
            enemy.x = self.wrap_x(enemy.x + math.sin(enemy.phase * 0.7) * 0.25)
            enemy.y -= 0.38
            if carried:
                carried.x = enemy.x
                carried.y = enemy.y + 1.0
                carried.state = "abducted"
                carried.carrier_id = enemy.enemy_id
            if enemy.y <= self.play_top + 1:
                if carried:
                    carried.state = "dead"
                enemy.carrying_human = None
                enemy.kind = "mutant"
                enemy.cooldown = 0.35 * ENEMY_FIRE_COOLDOWN_SCALE
            return

        target = human_by_id.get(enemy.target_human) if enemy.target_human is not None else None
        if target is None or target.state != "grounded":
            enemy.target_human = None

        if enemy.target_human is None:
            candidates = self.available_humans()
            if candidates and random.random() < 0.8:
                enemy.target_human = random.choice(candidates).human_id

        target = human_by_id.get(enemy.target_human) if enemy.target_human is not None else None
        if target:
            dx = self.shortest_wrap_delta(enemy.x, target.x)
            if abs(dx) > 1.4:
                enemy.x = self.wrap_x(enemy.x + max(-0.75, min(0.75, dx * 0.18)))
                enemy.y += math.sin(enemy.phase) * 0.08
            else:
                desired_y = target.y - 1.0
                if enemy.y < desired_y:
                    enemy.y += 0.48
                else:
                    enemy.y = desired_y
                if enemy.y >= target.y - 1.0:
                    target.state = "abducted"
                    target.carrier_id = enemy.enemy_id
                    enemy.carrying_human = target.human_id
                    enemy.target_human = None
            return

        dx_player = self.shortest_wrap_delta(enemy.x, self.player_x)
        enemy.x = self.wrap_x(enemy.x + max(-0.45, min(0.45, dx_player * 0.06)))
        enemy.y += math.sin(enemy.phase) * 0.16
        if (
            abs(dx_player) < 24
            and abs(enemy.y - self.player_y) < 6
            and enemy.cooldown <= 0.0
            and self.is_visible(enemy.x)
        ):
            self.fire_enemy_bullet(enemy, speed=1.0)

    def update_mutant(self, enemy):
        dx = self.shortest_wrap_delta(enemy.x, self.player_x)
        dy = self.player_y - enemy.y
        enemy.x = self.wrap_x(enemy.x + max(-1.0, min(1.0, dx * 0.11)))
        enemy.y += max(-0.55, min(0.55, dy * 0.12)) + math.sin(enemy.phase) * 0.08
        if abs(dx) < 30 and abs(dy) < 7 and enemy.cooldown <= 0.0 and self.is_visible(enemy.x):
            self.fire_enemy_bullet(enemy, speed=1.2)

    def update_swarmer(self, enemy):
        dx = self.shortest_wrap_delta(enemy.x, self.player_x)
        enemy.x = self.wrap_x(enemy.x + enemy.vx + max(-0.35, min(0.35, dx * 0.02)))
        enemy.y += math.sin(enemy.phase * 1.9) * 0.35 + enemy.vy
        if enemy.y <= self.play_top + 1 or enemy.y >= self.play_bottom - 1:
            enemy.vy *= -1
        if random.random() < 0.04:
            enemy.vx *= -1

    def update_bomber(self, enemy):
        enemy.x = self.wrap_x(enemy.x + enemy.vx)
        enemy.y += math.sin(enemy.phase * 0.8) * 0.12 + enemy.vy
        if enemy.y <= self.play_top + 2 or enemy.y >= self.play_bottom - 6:
            enemy.vy *= -1
        if enemy.cooldown <= 0.0 and self.is_visible(enemy.x):
            self.mines.append(Mine(enemy.x, enemy.y + 1.0, random.uniform(0.0, math.tau)))
            enemy.cooldown = random.uniform(1.2, 2.4)

    def update_baiter(self, enemy):
        dx = self.shortest_wrap_delta(enemy.x, self.player_x)
        dy = self.player_y - enemy.y
        enemy.x = self.wrap_x(enemy.x + max(-1.6, min(1.6, dx * 0.14)))
        enemy.y += max(-0.8, min(0.8, dy * 0.16))
        if enemy.cooldown <= 0.0 and abs(dx) < 34 and self.is_visible(enemy.x):
            self.fire_enemy_bullet(enemy, speed=1.45)

    def update_mothership(self, enemy):
        enemy.x = self.wrap_x(enemy.x + enemy.vx)
        enemy.y += math.sin(enemy.phase * 0.55) * 0.1
        if random.random() < 0.02:
            enemy.vx *= -1
        dx = self.shortest_wrap_delta(enemy.x, self.player_x)
        if enemy.cooldown <= 0.0 and abs(dx) < 26 and abs(enemy.y - self.player_y) < 8 and self.is_visible(enemy.x):
            self.fire_enemy_bullet(enemy, speed=1.0)

    def maybe_spawn_baiter(self):
        living = [enemy for enemy in self.enemies if enemy.alive]
        if not living:
            return
        if any(enemy.kind == "baiter" for enemy in living):
            return
        remaining_non_baiters = [enemy for enemy in living if enemy.kind != "baiter"]
        if len(remaining_non_baiters) > 3:
            return
        self.enemies.append(
            Enemy(
                self.next_enemy_id(),
                "baiter",
                self.wrap_x(self.player_x + random.choice([-34, 34])),
                max(self.play_top + 2, min(self.play_bottom - 6, self.player_y + random.choice([-5, 5]))),
                cooldown=0.4 * ENEMY_FIRE_COOLDOWN_SCALE,
                phase=random.uniform(0.0, math.tau),
            )
        )

    def fire_enemy_bullet(self, enemy, speed):
        dx = self.shortest_wrap_delta(enemy.x, self.player_x)
        dy = self.player_y - enemy.y
        distance = max(1.0, math.hypot(dx, dy))
        self.bullets.append(
            Bullet(
                x=enemy.x,
                y=enemy.y,
                dx=(dx / distance) * speed,
                dy=(dy / distance) * speed,
                from_enemy=True,
                ttl=70,
            )
        )
        enemy.cooldown = random.uniform(0.75, 1.35) * ENEMY_FIRE_COOLDOWN_SCALE

    def update_bullets(self):
        survivors = []
        for bullet in self.bullets:
            bullet.x = self.wrap_x(bullet.x + bullet.dx)
            bullet.y += bullet.dy
            bullet.ttl -= 1
            if bullet.ttl <= 0:
                continue
            if bullet.y < self.play_top + 1 or bullet.y >= self.play_bottom:
                continue
            if bullet.y >= self.surface_y(bullet.x):
                continue
            survivors.append(bullet)
        self.bullets = survivors

    def update_humans(self):
        enemy_by_id = self.enemy_map()
        for human in self.humans:
            if human.state == "dead":
                continue

            if human.state == "grounded":
                human.y = float(self.surface_y(human.x) - 1)
            elif human.state == "abducted":
                carrier = enemy_by_id.get(human.carrier_id)
                if carrier is None or not carrier.alive:
                    human.state = "falling"
                    human.carrier_id = None
                    human.vy = 0.0
                else:
                    human.x = carrier.x
                    human.y = carrier.y + 1.0
            elif human.state == "carried":
                human.x = self.player_x
                human.y = self.player_y + 1.0
            elif human.state == "falling":
                human.y += human.vy
                human.vy += 0.12
                if human.y >= self.surface_y(human.x) - 1:
                    human.state = "dead"

    def update_mines(self):
        next_mines = []
        for mine in self.mines:
            mine.phase += 0.2
            mine.y += 0.08
            if mine.y < self.surface_y(mine.x) - 0.2:
                next_mines.append(mine)
        self.mines = next_mines

    def update_explosions(self):
        next_explosions = []
        for explosion in self.explosions:
            explosion.frames -= 1
            if explosion.frames > 0:
                next_explosions.append(explosion)
        self.explosions = next_explosions

    def update_player_state(self):
        if self.respawn_frames > 0:
            self.respawn_frames -= 1
            if self.respawn_frames == 0 and self.player_lives > 0:
                self.invuln_frames = PLAYER_INVULN_FRAMES
                self.player_x = WORLD_WIDTH / 2
                self.player_y = self.play_top + 9
        elif self.invuln_frames > 0:
            self.invuln_frames -= 1

        if self.bonus_frames > 0:
            self.bonus_frames -= 1

        if self.player_carry_human is not None:
            human = next((h for h in self.humans if h.human_id == self.player_carry_human), None)
            if human is None or human.state == "dead":
                self.player_carry_human = None
            elif self.player_y >= self.surface_y(self.player_x) - 3:
                human.state = "grounded"
                human.x = self.player_x
                human.y = float(self.surface_y(self.player_x) - 1)
                self.player_carry_human = None
                self.score += 500
                self.high_score = max(self.high_score, self.score)
                self.bonus_text = "HUMAN RETURNED +500"
                self.bonus_frames = BONUS_FRAMES

    def destroy_enemy(self, enemy, smart_bomb=False):
        if not enemy.alive:
            return
        enemy.alive = False
        if enemy.carrying_human is not None:
            human = next((h for h in self.humans if h.human_id == enemy.carrying_human), None)
            if human is not None and human.state != "dead":
                human.state = "falling"
                human.carrier_id = None
                human.vy = -0.15 if smart_bomb else 0.0
                human.x = enemy.x
                human.y = enemy.y + 1.0
        if enemy.kind == "mothership":
            for _ in range(random.randint(5, 7)):
                self.enemies.append(
                    Enemy(
                        self.next_enemy_id(),
                        "swarmer",
                        enemy.x,
                        enemy.y + random.uniform(-1.0, 1.0),
                        vx=random.choice([-1.35, -1.1, 1.1, 1.35]),
                        vy=random.choice([-0.35, -0.2, 0.2, 0.35]),
                        phase=random.uniform(0.0, math.tau),
                    )
                )
        points = {
            "lander": 150,
            "mutant": 150,
            "bomber": 250,
            "baiter": 200,
            "mothership": 1000,
            "swarmer": 150,
        }[enemy.kind]
        self.score += points
        self.high_score = max(self.high_score, self.score)
        self.explosions.append(Explosion(enemy.x, enemy.y, 8))

    def hit_player(self):
        if self.invuln_frames > 0 or self.respawn_frames > 0:
            return
        self.player_lives -= 1
        self.respawn_frames = PLAYER_RESPAWN_FRAMES
        self.explosions.append(Explosion(self.player_x, self.player_y, 10))
        self.bullets = [bullet for bullet in self.bullets if not bullet.from_enemy]
        if self.player_carry_human is not None:
            human = next((h for h in self.humans if h.human_id == self.player_carry_human), None)
            if human is not None and human.state != "dead":
                human.state = "falling"
                human.vy = 0.0
                human.carrier_id = None
            self.player_carry_human = None
        if self.player_lives <= 0:
            self.running = False

    def collisions(self):
        enemy_hits = []
        remaining_bullets = []

        for bullet in self.bullets:
            if bullet.from_enemy:
                remaining_bullets.append(bullet)
                continue

            hit = None
            for enemy in self.enemies:
                if not enemy.alive:
                    continue
                if abs(self.shortest_wrap_delta(bullet.x, enemy.x)) <= 1.4 and abs(bullet.y - enemy.y) <= 0.8:
                    hit = enemy
                    break
            if hit is not None:
                enemy_hits.append(hit)
            else:
                remaining_bullets.append(bullet)

        self.bullets = remaining_bullets
        for enemy in enemy_hits:
            self.destroy_enemy(enemy)

        if self.invuln_frames > 0 or self.respawn_frames > 0:
            return

        next_bullets = []
        for bullet in self.bullets:
            if bullet.from_enemy and abs(self.shortest_wrap_delta(bullet.x, self.player_x)) <= 1.4 and abs(bullet.y - self.player_y) <= 0.9:
                self.hit_player()
                continue
            next_bullets.append(bullet)
        self.bullets = next_bullets

        for enemy in self.enemies:
            if enemy.alive and abs(self.shortest_wrap_delta(enemy.x, self.player_x)) <= 1.6 and abs(enemy.y - self.player_y) <= 0.9:
                self.destroy_enemy(enemy)
                self.hit_player()
                break

        for mine in self.mines:
            if abs(self.shortest_wrap_delta(mine.x, self.player_x)) <= 1.0 and abs(mine.y - self.player_y) <= 0.9:
                self.hit_player()
                break

        for human in self.humans:
            if human.state not in {"grounded", "falling"}:
                continue
            if self.player_carry_human is not None:
                break
            if abs(self.shortest_wrap_delta(human.x, self.player_x)) <= 1.7 and abs(human.y - (self.player_y + 1.0)) <= 1.2:
                human.state = "carried"
                human.carrier_id = None
                human.vy = 0.0
                self.player_carry_human = human.human_id
                if human.y < self.surface_y(human.x) - 1.5:
                    self.score += 500
                    self.high_score = max(self.high_score, self.score)
                    self.bonus_text = "HUMAN CAUGHT +500"
                    self.bonus_frames = BONUS_FRAMES
                break

    def living_humans(self):
        return sum(1 for human in self.humans if human.state != "dead")

    def living_enemies(self):
        return [enemy for enemy in self.enemies if enemy.alive]

    def draw_radar(self):
        radar_y = 1
        left = 1
        width = self.w - 2
        if width <= 10:
            return

        self.safe_addstr(radar_y, 1, "RADAR", self.color_attr(3) | curses.A_BOLD)
        for offset in range(width):
            self.safe_addch(radar_y + 1, left + offset, "-", self.color_attr(7))

        def plot(world_x, ch, attr):
            rx = left + int((world_x / WORLD_WIDTH) * max(1, width - 1))
            self.safe_addch(radar_y + 1, rx, ch, attr)

        for human in self.humans:
            if human.state != "dead":
                plot(human.x, "h", self.color_attr(4))

        for enemy in self.enemies:
            if enemy.alive:
                glyph = "!" if enemy.kind in {"mutant", "baiter", "swarmer"} else "v"
                plot(enemy.x, glyph, self.enemy_color(enemy))

        plot(self.player_x, "A", self.color_attr(1) | curses.A_BOLD)

    def draw(self):
        self.stdscr.erase()

        self.safe_addstr(0, 1, f"SCORE {self.score:06d}", self.color_attr(1) | curses.A_BOLD)
        center = max(1, self.w // 2 - 8)
        self.safe_addstr(0, center, f"HIGH {self.high_score:06d}", self.color_attr(3) | curses.A_BOLD)
        right_text = f"WAVE {self.wave}  LIVES {self.player_lives}  BOMBS {self.smart_bombs}"
        self.safe_addstr(0, self.w - len(right_text) - 2, right_text, self.color_attr(4) | curses.A_BOLD)

        self.draw_radar()
        separator = "." * max(1, self.w - 2)
        self.safe_addstr(self.play_top - 1, 1, separator, self.color_attr(7))

        if self.paused:
            self.safe_addstr(2, max(1, self.w // 2 - 3), "PAUSED", self.color_attr(4) | curses.A_BOLD)

        if self.bonus_frames > 0 and self.bonus_text:
            self.safe_addstr(2, max(1, self.w // 2 - len(self.bonus_text) // 2), self.bonus_text, self.color_attr(2) | curses.A_BOLD)
        else:
            humans_text = f"HUMANS {self.living_humans()}"
            self.safe_addstr(2, 1, humans_text, self.color_attr(4))

        for star in self.stars:
            sx = self.world_to_screen(star.x)
            if sx is not None:
                self.safe_addch(star.y, sx, star.glyph, self.color_attr(star.color))

        for screen_x in range(self.w):
            world_x = (self.camera_left() + screen_x) % WORLD_WIDTH
            surface = self.surface_y(world_x)
            self.safe_addch(surface, screen_x, "_", self.color_attr(5))
            for fill_y in range(surface + 1, self.h):
                self.safe_addch(fill_y, screen_x, "^", self.color_attr(5))

        for human in self.humans:
            if human.state == "dead":
                continue
            sx = self.world_to_screen(human.x)
            if sx is None:
                continue
            glyph = "Y" if human.state == "carried" else "i"
            self.safe_addch(int(human.y), sx, glyph, self.color_attr(4) | curses.A_BOLD)

        for enemy in self.enemies:
            if not enemy.alive:
                continue
            sx = self.world_to_screen(enemy.x)
            if sx is None:
                continue
            self.safe_addch(int(enemy.y), sx, self.enemy_glyph(enemy), self.enemy_color(enemy) | curses.A_BOLD)

        for mine in self.mines:
            sx = self.world_to_screen(mine.x)
            if sx is None:
                continue
            glyph = "o" if math.sin(mine.phase) >= 0 else "O"
            self.safe_addch(int(mine.y), sx, glyph, self.color_attr(6) | curses.A_BOLD)

        for bullet in self.bullets:
            sx = self.world_to_screen(bullet.x)
            if sx is None:
                continue
            glyph = "!" if bullet.from_enemy else "-"
            color = self.color_attr(2 if bullet.from_enemy else 3) | curses.A_BOLD
            self.safe_addch(int(bullet.y), sx, glyph, color)

        for explosion in self.explosions:
            sx = self.world_to_screen(explosion.x)
            if sx is None:
                continue
            glyph = "*" if explosion.frames % 2 else "+"
            self.safe_addch(int(explosion.y), sx, glyph, self.color_attr(2) | curses.A_BOLD)

        if self.respawn_frames == 0 and (self.invuln_frames == 0 or self.invuln_frames % 4 < 2):
            sx = self.world_to_screen(self.player_x)
            if sx is not None:
                ship = self.player_sprite()
                self.safe_addstr(int(self.player_y), sx - (len(ship) // 2), ship, self.color_attr(1) | curses.A_BOLD)

        self.stdscr.refresh()

    def loop(self):
        while self.running:
            self.handle_input()
            if not self.running:
                break
            if not self.paused:
                self.update_background()
                self.update_enemies()
                self.update_bullets()
                self.update_humans()
                self.update_mines()
                self.collisions()
                self.update_explosions()
                self.update_player_state()
                if not self.living_enemies():
                    self.start_wave()
            self.draw()
            time.sleep(TICK_SECONDS)

    def intro_screen(self):
        self.stdscr.nodelay(False)
        self.stdscr.erase()
        lines = [
            "DEFENDER CONSOLE",
            "",
            "Arrow keys or WASD: move",
            "Right/D: thrust, Left/A: reverse thrust",
            "Up/Down or W/S: vertical",
            "Space: fire",
            "B: smart bomb (visible area only)",
            "H: hyperspace",
            "Esc: pause",
            "Q: quit",
            "",
            "Protect humans, shoot abductors, catch falling colonists.",
            "",
            "Press any key to launch",
        ]
        top = max(1, self.h // 2 - len(lines) // 2)
        for idx, line in enumerate(lines):
            attr = self.color_attr(3) | curses.A_BOLD if idx == 0 else self.color_attr(1)
            self.safe_addstr(top + idx, max(1, self.w // 2 - len(line) // 2), line, attr)
        self.stdscr.refresh()
        self.stdscr.getch()
        self.stdscr.nodelay(True)

    def game_over_screen(self):
        self.finalize_score_submission()
        self.stdscr.nodelay(False)
        self.stdscr.erase()
        title = "GAME OVER"
        score_line = f"Score {self.score}   High {self.high_score}"
        hint = "Press any key to exit"
        self.safe_addstr(self.h // 2 - 1, max(1, self.w // 2 - len(title) // 2), title, self.color_attr(2) | curses.A_BOLD)
        self.safe_addstr(self.h // 2, max(1, self.w // 2 - len(score_line) // 2), score_line, self.color_attr(1))
        if self.top_scores:
            leader = self.top_scores[0]
            leader_line = f"Top: {leader['name']} {leader['score']}"
            self.safe_addstr(self.h // 2 + 1, max(1, self.w // 2 - len(leader_line) // 2), leader_line, self.color_attr(3))
        self.safe_addstr(self.h // 2 + 2, max(1, self.w // 2 - len(hint) // 2), hint, self.color_attr(4))
        self.stdscr.refresh()
        self.stdscr.getch()


def run(stdscr):
    game = Game(stdscr)
    try:
        game.setup()
    except RuntimeError as err:
        stdscr.nodelay(False)
        stdscr.erase()
        stdscr.addstr(0, 0, str(err))
        stdscr.addstr(2, 0, "Resize the terminal and try again.")
        stdscr.refresh()
        stdscr.getch()
        return
    game.show_top10_intro(3.0)
    game.intro_screen()
    game.draw()
    game.loop()
    game.game_over_screen()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Terminal Defender-style game")
    parser.parse_args()
    try:
        curses.wrapper(run)
    except KeyboardInterrupt:
        pass
