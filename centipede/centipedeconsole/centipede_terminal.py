#!/usr/bin/env python3
import argparse
import curses
import os
import random
import time
from dataclasses import dataclass


MIN_WIDTH = 78
MIN_HEIGHT = 30
TICK_SECONDS = 0.05
PLAYER_COOLDOWN = 0.10
SCORE_FILE_NAME = ".centipede_console"
EXTRA_LIFE_EVERY = 12000
MUSHROOM_CLEAR_ROWS = 4


@dataclass
class Mushroom:
    x: int
    y: int
    hp: int = 4
    poisoned: bool = False


@dataclass
class Bullet:
    x: int
    y: int


@dataclass
class Centipede:
    segments: list[tuple[int, int]]
    dx: int
    vertical_dir: int = 1
    charging: bool = False


@dataclass
class Spider:
    x: float
    y: float
    dx: float
    dy: float


@dataclass
class Flea:
    x: int
    y: float
    hits: int = 0
    drop_timer: int = 0


@dataclass
class Scorpion:
    x: float
    y: int
    dx: float


@dataclass
class Explosion:
    x: int
    y: int
    frames: int = 4
    glyph: str = "*"


class Game:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.h = 0
        self.w = 0
        self.use_colors = False
        self.running = True
        self.paused = False
        self.game_over = False
        self.board_width = 0
        self.board_height = 0
        self.player_zone_height = 0
        self.player_zone_top = 0
        self.score = 0
        self.high_score = 0
        self.wave = 0
        self.lives = 3
        self.next_extra_life = EXTRA_LIFE_EVERY
        self.player_x = 0
        self.player_y = 0
        self.player_flash = 0
        self.last_shot = 0.0
        self.last_centipede_move = 0.0
        self.last_spider_spawn = 0.0
        self.last_scorpion_spawn = 0.0
        self.mushrooms: list[Mushroom] = []
        self.centipedes: list[Centipede] = []
        self.bullet: Bullet | None = None
        self.spider: Spider | None = None
        self.flea: Flea | None = None
        self.scorpion: Scorpion | None = None
        self.explosions: list[Explosion] = []
        self.status_text = ""
        self.status_frames = 0

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

        if curses.has_colors():
            curses.start_color()
            curses.use_default_colors()
            curses.init_pair(1, curses.COLOR_WHITE, -1)
            curses.init_pair(2, curses.COLOR_GREEN, -1)
            curses.init_pair(3, curses.COLOR_RED, -1)
            curses.init_pair(4, curses.COLOR_YELLOW, -1)
            curses.init_pair(5, curses.COLOR_MAGENTA, -1)
            curses.init_pair(6, curses.COLOR_CYAN, -1)
            curses.init_pair(7, curses.COLOR_BLUE, -1)
            curses.init_pair(8, curses.COLOR_WHITE, -1)
            self.use_colors = True

        self.configure_playfield()
        self.load_score_file()
        self.start_new_game()

    def configure_playfield(self):
        self.board_width = self.w - 4
        self.board_height = self.h - 8
        self.player_zone_height = max(6, self.board_height // 4)
        self.player_zone_top = self.board_height - self.player_zone_height

    def start_new_game(self):
        self.score = 0
        self.wave = 0
        self.lives = 3
        self.next_extra_life = EXTRA_LIFE_EVERY
        self.player_x = self.board_width // 2
        self.player_y = self.board_height - 1
        self.player_flash = 0
        self.bullet = None
        self.spider = None
        self.flea = None
        self.scorpion = None
        self.explosions = []
        self.mushrooms = []
        self.seed_mushrooms(self.initial_mushroom_count())
        self.start_wave(initial=True)

    def initial_mushroom_count(self):
        area = self.board_width * self.board_height
        return max(42, area // 20)

    def max_mushroom_row(self):
        return max(1, self.board_height - MUSHROOM_CLEAR_ROWS - 1)

    def clear_bottom_mushrooms(self):
        max_row = self.max_mushroom_row()
        self.mushrooms = [mushroom for mushroom in self.mushrooms if mushroom.y <= max_row]

    def color_attr(self, pair_id):
        return curses.color_pair(pair_id) if self.use_colors else 0

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

    def center_text(self, y, text, attr=0):
        self.safe_addstr(y, max(1, self.w // 2 - len(text) // 2), text, attr)

    def score_file_path(self):
        return os.path.join(os.path.expanduser("~"), SCORE_FILE_NAME)

    def load_score_file(self):
        try:
            with open(self.score_file_path(), "r", encoding="utf-8") as handle:
                for line in handle:
                    if line.startswith("high_score="):
                        value = line.split("=", 1)[1].strip()
                        if value.isdigit():
                            self.high_score = int(value)
        except FileNotFoundError:
            return
        except OSError:
            return

    def save_score_file(self):
        self.high_score = max(self.high_score, self.score)
        try:
            with open(self.score_file_path(), "w", encoding="utf-8") as handle:
                handle.write(f"high_score={self.high_score}\n")
        except OSError:
            pass

    def set_status(self, text, frames=60):
        self.status_text = text
        self.status_frames = frames

    def seed_mushrooms(self, count):
        occupied = {(self.player_x, self.player_y)}
        occupied.update((mushroom.x, mushroom.y) for mushroom in self.mushrooms)
        max_row = self.max_mushroom_row()
        for _ in range(count):
            for _attempt in range(30):
                x = random.randint(0, self.board_width - 1)
                y = random.randint(1, max_row)
                if y == 0 or (x, y) in occupied:
                    continue
                occupied.add((x, y))
                self.mushrooms.append(Mushroom(x, y, hp=random.choice([3, 4, 4, 4])))
                break

    def mushroom_at(self, x, y):
        for mushroom in self.mushrooms:
            if mushroom.x == x and mushroom.y == y:
                return mushroom
        return None

    def add_mushroom(self, x, y, hp=4, poisoned=False):
        if not (0 <= x < self.board_width and 0 <= y <= self.max_mushroom_row()):
            return
        mushroom = self.mushroom_at(x, y)
        if mushroom is None:
            self.mushrooms.append(Mushroom(x, y, hp=hp, poisoned=poisoned))
        else:
            mushroom.hp = max(mushroom.hp, hp)
            mushroom.poisoned = poisoned

    def remove_mushroom(self, mushroom):
        self.mushrooms = [item for item in self.mushrooms if item is not mushroom]

    def start_wave(self, initial=False):
        self.wave += 1
        self.centipedes = []
        self.bullet = None
        self.spider = None
        self.flea = None
        self.scorpion = None
        self.explosions = []
        self.player_x = self.board_width // 2
        self.player_y = self.board_height - 1
        self.player_flash = 30
        self.last_centipede_move = time.monotonic()

        if not initial:
            self.set_status(f"WAVE {self.wave}", frames=70)
            self.seed_mushrooms(max(8, self.board_width // 7) + min(self.wave, 12))
            for mushroom in self.mushrooms:
                if mushroom.hp < 4 and random.random() < 0.5:
                    mushroom.hp += 1
                if random.random() < 0.3:
                    mushroom.poisoned = False
        self.clear_bottom_mushrooms()

        base_length = min(18, max(12, self.board_width // 4))
        main_length = max(6, base_length - min(self.wave - 1, 8))
        main_dx = -1 if self.wave % 2 else 1
        head_x = 0 if main_dx == -1 else main_length - 1
        segments = [(head_x - (idx * main_dx), 0) for idx in range(main_length)]
        self.centipedes.append(Centipede(segments=segments, dx=main_dx))

        for _ in range(min(self.wave - 1, 5)):
            x = random.randint(0, self.board_width - 1)
            y = random.randint(0, max(2, self.player_zone_top - 6))
            self.centipedes.append(
                Centipede(segments=[(x, y)], dx=random.choice([-1, 1]), vertical_dir=1)
            )

    def lower_mushroom_count(self):
        return sum(1 for mushroom in self.mushrooms if mushroom.y >= self.player_zone_top)

    def centipede_speed(self):
        return max(0.09, 0.24 - min(0.01 * self.wave, 0.08) - min(self.score / 90000.0, 0.04))

    def fire_player_bullet(self):
        now = time.monotonic()
        if self.bullet is not None or now - self.last_shot < PLAYER_COOLDOWN:
            return
        self.last_shot = now
        self.bullet = Bullet(self.player_x, self.player_y - 1)

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
            if self.paused or self.game_over:
                key = self.stdscr.getch()
                continue

            if key in (curses.KEY_LEFT, ord("a"), ord("A")):
                self.player_x = max(0, self.player_x - 1)
            elif key in (curses.KEY_RIGHT, ord("d"), ord("D")):
                self.player_x = min(self.board_width - 1, self.player_x + 1)
            elif key in (curses.KEY_UP, ord("w"), ord("W")):
                self.player_y = max(self.player_zone_top, self.player_y - 1)
            elif key in (curses.KEY_DOWN, ord("s"), ord("S")):
                self.player_y = min(self.board_height - 1, self.player_y + 1)
            elif key == ord(" "):
                self.fire_player_bullet()

            key = self.stdscr.getch()

    def update(self):
        if self.paused or self.game_over:
            return

        if self.status_frames > 0:
            self.status_frames -= 1
        if self.player_flash > 0:
            self.player_flash -= 1

        self.update_explosions()
        self.update_bullet()
        self.update_centipedes()
        self.update_spider()
        self.update_flea()
        self.update_scorpion()
        self.check_player_collisions()
        self.check_wave_clear()
        self.check_extra_life()

    def update_explosions(self):
        for explosion in self.explosions:
            explosion.frames -= 1
        self.explosions = [explosion for explosion in self.explosions if explosion.frames > 0]

    def update_bullet(self):
        if self.bullet is None:
            return
        self.bullet.y -= 1
        if self.bullet.y < 0:
            self.bullet = None
            return

        if self.hit_centipede(self.bullet.x, self.bullet.y):
            self.bullet = None
            return
        if self.hit_spider(self.bullet.x, self.bullet.y):
            self.bullet = None
            return
        if self.hit_flea(self.bullet.x, self.bullet.y):
            self.bullet = None
            return
        if self.hit_scorpion(self.bullet.x, self.bullet.y):
            self.bullet = None
            return

        mushroom = self.mushroom_at(self.bullet.x, self.bullet.y)
        if mushroom is not None:
            mushroom.hp -= 1
            if mushroom.hp <= 0:
                self.remove_mushroom(mushroom)
                self.score += 1
            self.bullet = None

    def hit_centipede(self, x, y):
        for centipede in list(self.centipedes):
            for index, segment in enumerate(centipede.segments):
                if segment != (x, y):
                    continue
                self.score += 100 if index == 0 else 10
                self.high_score = max(self.high_score, self.score)
                self.explosions.append(Explosion(x, y, frames=4, glyph="x"))
                self.add_mushroom(x, y, hp=4, poisoned=False)

                front = centipede.segments[:index]
                back = centipede.segments[index + 1:]
                replacement: list[Centipede] = []
                if front:
                    replacement.append(
                        Centipede(
                            segments=front,
                            dx=centipede.dx,
                            vertical_dir=centipede.vertical_dir,
                            charging=centipede.charging and index > 0,
                        )
                    )
                if back:
                    replacement.append(
                        Centipede(
                            segments=back,
                            dx=centipede.dx,
                            vertical_dir=centipede.vertical_dir,
                            charging=False,
                        )
                    )
                self.centipedes.remove(centipede)
                self.centipedes.extend(replacement)
                return True
        return False

    def hit_spider(self, x, y):
        if self.spider is None:
            return False
        if (round(self.spider.x), round(self.spider.y)) != (x, y):
            return False
        depth = max(0, y - self.player_zone_top)
        zone_band = max(1, self.player_zone_height // 3)
        self.score += [300, 600, 900][min(2, depth // zone_band)]
        self.high_score = max(self.high_score, self.score)
        self.explosions.append(Explosion(x, y, frames=5, glyph="*"))
        self.spider = None
        return True

    def hit_flea(self, x, y):
        if self.flea is None:
            return False
        if (self.flea.x, round(self.flea.y)) != (x, y):
            return False
        self.flea.hits += 1
        if self.flea.hits >= 2:
            self.score += 200
            self.high_score = max(self.high_score, self.score)
            self.explosions.append(Explosion(x, y, frames=5, glyph="+"))
            self.flea = None
        return True

    def hit_scorpion(self, x, y):
        if self.scorpion is None:
            return False
        if (round(self.scorpion.x), self.scorpion.y) != (x, y):
            return False
        self.score += 1000
        self.high_score = max(self.high_score, self.score)
        self.explosions.append(Explosion(x, y, frames=5, glyph="#"))
        self.scorpion = None
        return True

    def update_centipedes(self):
        now = time.monotonic()
        if now - self.last_centipede_move < self.centipede_speed():
            return
        self.last_centipede_move = now

        updated: list[Centipede] = []
        for centipede in self.centipedes:
            if not centipede.segments:
                continue

            head_x, head_y = centipede.segments[0]
            if centipede.charging:
                next_y = min(self.board_height - 1, head_y + 1)
                new_head = (head_x, next_y)
                if next_y >= self.board_height - 1:
                    centipede.charging = False
                    centipede.vertical_dir = -1
            else:
                next_x = head_x + centipede.dx
                blocked = next_x < 0 or next_x >= self.board_width
                poison_charge = False
                if not blocked:
                    mushroom = self.mushroom_at(next_x, head_y)
                    if mushroom is not None and mushroom.poisoned:
                        poison_charge = True
                    blocked = mushroom is not None

                if poison_charge:
                    centipede.charging = True
                    new_head = (head_x, min(self.board_height - 1, head_y + 1))
                elif blocked:
                    centipede.dx *= -1
                    next_y = head_y + centipede.vertical_dir
                    if next_y >= self.board_height:
                        next_y = self.board_height - 1
                        centipede.vertical_dir = -1
                    elif next_y < 0:
                        next_y = 0
                        centipede.vertical_dir = 1
                    new_head = (head_x, next_y)
                else:
                    new_head = (next_x, head_y)

                if new_head[1] <= 0:
                    centipede.vertical_dir = 1
                elif new_head[1] >= self.board_height - 1:
                    centipede.vertical_dir = -1

            centipede.segments = [new_head] + centipede.segments[:-1]
            updated.append(centipede)

        self.centipedes = updated

    def update_spider(self):
        now = time.monotonic()
        if self.spider is None:
            interval = max(3.2, 6.4 - min(self.wave * 0.18, 2.0))
            if now - self.last_spider_spawn >= interval:
                self.last_spider_spawn = now
                start_left = random.choice([True, False])
                self.spider = Spider(
                    x=-1.0 if start_left else self.board_width,
                    y=random.uniform(self.player_zone_top + 1, self.board_height - 1),
                    dx=0.45 if start_left else -0.45,
                    dy=random.choice([-0.35, 0.35]),
                )
            return

        self.spider.x += self.spider.dx
        self.spider.y += self.spider.dy
        if self.spider.y < self.player_zone_top:
            self.spider.y = float(self.player_zone_top)
            self.spider.dy *= -1
        if self.spider.y > self.board_height - 1:
            self.spider.y = float(self.board_height - 1)
            self.spider.dy *= -1
        if random.random() < 0.14:
            self.spider.dy = random.choice([-0.45, -0.25, 0.25, 0.45])
        if random.random() < 0.08:
            self.spider.dx *= -1
        mushroom = self.mushroom_at(round(self.spider.x), round(self.spider.y))
        if mushroom is not None:
            self.remove_mushroom(mushroom)
        if self.spider.x < -2 or self.spider.x > self.board_width + 1:
            self.spider = None

    def update_flea(self):
        if self.flea is None:
            threshold = max(6, self.board_width // 10)
            if self.lower_mushroom_count() <= threshold and random.random() < 0.025:
                self.flea = Flea(x=random.randint(0, self.board_width - 1), y=0.0)
            return

        self.flea.y += 0.40 + min(self.wave * 0.025, 0.25)
        self.flea.drop_timer += 1
        if self.flea.drop_timer >= 3:
            self.flea.drop_timer = 0
            if random.random() < 0.3:
                drop_y = round(self.flea.y) - 1
                if 0 <= drop_y <= self.max_mushroom_row() and self.mushroom_at(self.flea.x, drop_y) is None:
                    self.add_mushroom(self.flea.x, drop_y, hp=4, poisoned=False)
        if self.flea.y > self.board_height:
            self.flea = None

    def update_scorpion(self):
        now = time.monotonic()
        if self.scorpion is None:
            interval = max(5.0, 10.0 - min(self.wave * 0.4, 3.5))
            if now - self.last_scorpion_spawn >= interval and random.random() < 0.03:
                self.last_scorpion_spawn = now
                start_left = random.choice([True, False])
                self.scorpion = Scorpion(
                    x=-1.0 if start_left else self.board_width,
                    y=random.randint(2, self.player_zone_top - 2),
                    dx=0.38 if start_left else -0.38,
                )
            return

        self.scorpion.x += self.scorpion.dx
        mushroom = self.mushroom_at(round(self.scorpion.x), self.scorpion.y)
        if mushroom is not None:
            mushroom.poisoned = True
        if self.scorpion.x < -2 or self.scorpion.x > self.board_width + 1:
            self.scorpion = None

    def check_player_collisions(self):
        if self.player_flash > 0:
            return

        player_pos = (self.player_x, self.player_y)
        for centipede in self.centipedes:
            if player_pos in centipede.segments:
                self.lose_life("CENTIPEDE")
                return

        if self.spider is not None and (round(self.spider.x), round(self.spider.y)) == player_pos:
            self.lose_life("SPIDER")
            return
        if self.flea is not None and (self.flea.x, round(self.flea.y)) == player_pos:
            self.lose_life("FLEA")
            return
        if self.scorpion is not None and (round(self.scorpion.x), self.scorpion.y) == player_pos:
            self.lose_life("SCORPION")
            return

    def lose_life(self, reason):
        self.explosions.append(Explosion(self.player_x, self.player_y, frames=7, glyph="*"))
        self.lives -= 1
        self.bullet = None
        self.spider = None
        self.flea = None
        self.scorpion = None
        self.player_x = self.board_width // 2
        self.player_y = self.board_height - 1
        self.player_flash = 40
        self.set_status(f"{reason} HIT", frames=45)
        for mushroom in self.mushrooms:
            if mushroom.y >= self.player_zone_top and mushroom.hp < 4:
                mushroom.hp += 1
        if self.lives <= 0:
            self.game_over = True
            self.running = False

    def check_wave_clear(self):
        if self.centipedes:
            return
        self.start_wave()

    def check_extra_life(self):
        if self.score < self.next_extra_life:
            return
        self.lives = min(6, self.lives + 1)
        self.next_extra_life += EXTRA_LIFE_EVERY
        self.set_status("EXTRA LIFE", frames=55)

    def mushroom_glyph(self, mushroom):
        if mushroom.hp >= 4:
            return "M"
        if mushroom.hp == 3:
            return "m"
        if mushroom.hp == 2:
            return "n"
        return "."

    def draw_board(self):
        self.stdscr.erase()
        board_top = 3
        board_left = 2
        board_right = board_left + self.board_width

        self.safe_addstr(0, 2, "CENTIPEDE CONSOLE", self.color_attr(2) | curses.A_BOLD)
        self.safe_addstr(0, 22, f"SCORE {self.score:06d}", self.color_attr(8) | curses.A_BOLD)
        self.safe_addstr(0, 40, f"HIGH {max(self.high_score, self.score):06d}", self.color_attr(8))
        self.safe_addstr(0, 58, f"WAVE {self.wave:02d}", self.color_attr(4))
        self.safe_addstr(0, 69, f"FIELD {self.board_width}x{self.board_height}", self.color_attr(8))
        self.safe_addstr(1, 2, f"LIVES {'A' * max(0, self.lives)}", self.color_attr(6))

        status = "PAUSED" if self.paused else self.status_text
        if status and (self.paused or self.status_frames > 0):
            self.safe_addstr(1, 24, status[:30], self.color_attr(3) | curses.A_BOLD)

        self.safe_addstr(board_top - 1, board_left - 1, "+" + ("-" * self.board_width) + "+", self.color_attr(8))
        for row in range(self.board_height):
            self.safe_addstr(board_top + row, board_left - 1, "|", self.color_attr(8))
            self.safe_addstr(board_top + row, board_right, "|", self.color_attr(8))
            zone_attr = self.color_attr(7) if row >= self.player_zone_top else 0
            self.safe_addstr(board_top + row, board_left, " " * self.board_width, zone_attr)
        self.safe_addstr(board_top + self.board_height, board_left - 1, "+" + ("-" * self.board_width) + "+", self.color_attr(8))

        for mushroom in self.mushrooms:
            attr = self.color_attr(5 if mushroom.poisoned else 2) | curses.A_BOLD
            self.safe_addstr(board_top + mushroom.y, board_left + mushroom.x, self.mushroom_glyph(mushroom), attr)

        for centipede in self.centipedes:
            for index, (x, y) in enumerate(centipede.segments):
                pair = 3 if index == 0 else 4
                glyph = "Q" if index == 0 else "o"
                self.safe_addstr(board_top + y, board_left + x, glyph, self.color_attr(pair) | curses.A_BOLD)

        if self.spider is not None:
            self.safe_addstr(board_top + round(self.spider.y), board_left + round(self.spider.x), "W", self.color_attr(3) | curses.A_BOLD)
        if self.flea is not None:
            self.safe_addstr(board_top + round(self.flea.y), board_left + self.flea.x, "F", self.color_attr(4) | curses.A_BOLD)
        if self.scorpion is not None:
            self.safe_addstr(board_top + self.scorpion.y, board_left + round(self.scorpion.x), "S", self.color_attr(5) | curses.A_BOLD)
        if self.bullet is not None:
            self.safe_addstr(board_top + self.bullet.y, board_left + self.bullet.x, "|", self.color_attr(8) | curses.A_BOLD)

        for explosion in self.explosions:
            self.safe_addstr(board_top + explosion.y, board_left + explosion.x, explosion.glyph, self.color_attr(6) | curses.A_BOLD)

        if self.player_flash % 2 == 0:
            self.safe_addstr(board_top + self.player_y, board_left + self.player_x, "A", self.color_attr(6) | curses.A_BOLD)

        footer_y = board_top + self.board_height + 2
        self.safe_addstr(
            footer_y,
            2,
            "Move: Arrows/WASD   Fire: Space   Pause: Esc   Quit: Q",
            self.color_attr(8),
        )
        self.safe_addstr(
            footer_y + 1,
            2,
            "Legend: Q head 100  o body 10  W spider 300/600/900  F flea 200  S scorpion 1000",
            self.color_attr(8),
        )
        zone_text = f"Player zone: bottom {self.player_zone_height} rows"
        hazard_text = "Poisoned mushrooms force a vertical charge."
        self.safe_addstr(footer_y + 2, 2, zone_text, self.color_attr(6))
        self.safe_addstr(footer_y + 2, len(zone_text) + 8, hazard_text, self.color_attr(5))

        self.stdscr.refresh()

    def intro_screen(self):
        self.stdscr.nodelay(False)
        self.stdscr.erase()
        lines = [
            "CENTIPEDE CONSOLE",
            "",
            "Fixed-shooter cabinet with mushrooms, splitting centipedes,",
            "poison runs, spiders, fleas, and scorpions.",
            "",
            "The field now expands to fill most of the terminal.",
            "Move only inside the lower player zone.",
            "Shoot heads for 100, body segments for 10.",
            "",
            "Press any key to start",
        ]
        top = max(2, self.h // 2 - len(lines) // 2)
        for idx, line in enumerate(lines):
            attr = self.color_attr(2) | curses.A_BOLD if idx == 0 else self.color_attr(8)
            self.center_text(top + idx, line, attr)
        self.stdscr.refresh()
        self.stdscr.getch()
        self.stdscr.nodelay(True)

    def game_over_screen(self):
        self.save_score_file()
        self.stdscr.nodelay(False)
        self.stdscr.erase()
        title = "GAME OVER"
        score_line = f"Score {self.score}   High {max(self.high_score, self.score)}   Wave {self.wave}"
        hint = "Press any key to exit"
        self.center_text(self.h // 2 - 1, title, self.color_attr(3) | curses.A_BOLD)
        self.center_text(self.h // 2, score_line, self.color_attr(8))
        self.center_text(self.h // 2 + 2, hint, self.color_attr(4))
        self.stdscr.refresh()
        self.stdscr.getch()

    def loop(self):
        while self.running:
            self.handle_input()
            self.update()
            self.draw_board()
            time.sleep(TICK_SECONDS)


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
    game.intro_screen()
    game.draw_board()
    game.loop()
    game.game_over_screen()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Terminal Centipede clone")
    parser.parse_args()
    try:
        curses.wrapper(run)
    except KeyboardInterrupt:
        pass
