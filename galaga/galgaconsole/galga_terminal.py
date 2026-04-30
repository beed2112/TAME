#!/usr/bin/env python3
import argparse
import curses
import os
import random
import time
from dataclasses import dataclass


TICK_SECONDS = 0.04
PLAYER_COOLDOWN = 0.16
MACHINE_GUN_COOLDOWN = 0.02
ENEMY_FIRE_CHANCE = 0.015
ENEMY_FIRE_SCALE = 0.95
ENEMY_STEP_TIME = 0.5
ENEMY_DROP_ROWS = 1
ENEMY_DROP_EVERY = 2
MAX_PLAYER_BULLETS_ACTIVE = 2
PLAYER_HALF_WIDTH = 1
DIVE_CHANCE_BASE = 0.10
RESPAWN_EXPLOSION_FRAMES = 14
RESPAWN_INVULN_FRAMES = 20
CAPTURE_FRAMES = 22
SCORE_FILE_NAME = ".galaga"
CHALLENGE_GROUPS = 5
CHALLENGE_ENEMIES_PER_GROUP = 8
CHALLENGE_PERFECT_BONUS = 10000
CHALLENGE_MESSAGE_FRAMES = 80
STAGE_FIRE_RAMP_SECONDS = 6.0
MAX_ENEMY_BULLETS_BASE = 6


@dataclass
class Bullet:
    x: int
    y: int
    dy: int
    from_enemy: bool


@dataclass
class Enemy:
    x: int
    y: int
    glyph: str
    points: int
    alive: bool = True
    diving: bool = False
    dive_dx: int = 0
    dive_dy: int = 1
    crossed_center: bool = False


@dataclass
class Star:
    x: int
    y: int
    glyph: str
    color: int


class Game:
    def __init__(self, stdscr, endless=False, machine_gun=False):
        self.stdscr = stdscr
        self.h = 0
        self.w = 0
        self.player_x = 0
        self.player_y = 0
        self.player_lives = 4
        self.score = 0
        self.high_score = 0
        self.level = 1
        self.last_shot = 0.0
        self.cheat_endless = bool(endless)
        self.cheat_machine_gun = bool(machine_gun)
        self.player_cooldown = MACHINE_GUN_COOLDOWN if self.cheat_machine_gun else PLAYER_COOLDOWN
        self.max_player_bullets = 999 if self.cheat_machine_gun else MAX_PLAYER_BULLETS_ACTIVE
        self.last_enemy_step = 0.0
        self.enemy_dir = 1
        self.edge_hits = 0
        self.enemies = []
        self.bullets = []
        self.stars = []
        self.running = True
        self.win = False
        self.paused = False
        self.beam_frames = 0
        self.beam_length = 0
        self.beam_enemy = None
        self.use_colors = False
        self.respawn_frames = 0
        self.invuln_frames = 0
        self.explosion_x = 0
        self.explosion_y = 0
        self.capture_frames = 0
        self.capture_x = 0.0
        self.capture_y = 0.0
        self.capture_target_x = 0.0
        self.capture_target_y = 0.0
        self.captured_ship_active = False
        self.captured_ship_enemy = None
        self.pending_game_over = False
        self.dual_shot = False
        self.capture_revenge_target = None
        self.dive_side_toggle = False
        self.games_played = 0
        self.top_scores = []
        self.edge_hits = 0
        self.challenge_total = 0
        self.challenge_hits = 0
        self.challenge_bonus_awarded = False
        self.challenge_message_frames = 0
        self.stage_started_at = time.monotonic()

    def is_challenging_stage(self):
        return self.level == 3 or (self.level > 3 and (self.level - 3) % 4 == 0)

    def stage_label(self):
        return "CHALLENGE" if self.is_challenging_stage() else "FORMATION"

    def setup(self):
        curses.curs_set(0)
        self.stdscr.nodelay(True)
        self.stdscr.keypad(True)
        self.stdscr.timeout(0)
        self.h, self.w = self.stdscr.getmaxyx()
        if self.h < 22 or self.w < 55:
            raise RuntimeError("Terminal too small. Need at least 55x22.")

        if curses.has_colors():
            curses.start_color()
            curses.use_default_colors()
            curses.init_pair(1, curses.COLOR_WHITE, -1)
            curses.init_pair(2, curses.COLOR_RED, -1)
            curses.init_pair(3, curses.COLOR_CYAN, -1)
            curses.init_pair(4, curses.COLOR_YELLOW, -1)
            curses.init_pair(5, curses.COLOR_BLUE, -1)
            curses.init_pair(6, curses.COLOR_MAGENTA, -1)
            curses.init_pair(7, curses.COLOR_GREEN, -1)
            self.use_colors = True

        self.player_x = self.w // 2
        self.player_y = self.h - 3
        self.explosion_x = self.player_x
        self.explosion_y = self.player_y
        self.load_score_file()
        self.spawn_stars()
        self.spawn_enemies()

    def color_attr(self, color_pair):
        if self.use_colors:
            return curses.color_pair(color_pair)
        return 0

    def score_file_path(self):
        return os.path.join(os.path.expanduser("~"), SCORE_FILE_NAME)

    def load_score_file(self):
        path = self.score_file_path()
        try:
            with open(path, "r", encoding="utf-8") as handle:
                lines = [line.strip() for line in handle.readlines() if line.strip()]
        except FileNotFoundError:
            try:
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write("high_score=0\nlast_score=0\ngames_played=0\n")
            except OSError:
                pass
            return
        except OSError:
            return

        # Support legacy format where file contains only an integer high score.
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
        self.top_scores = sorted(entries, key=lambda x: x["score"], reverse=True)[:10]

        top_high = self.top_scores[0]["score"] if self.top_scores else 0
        self.high_score = max(self.high_score, high_from_file, top_high)

    def save_score_file(self):
        path = self.score_file_path()
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
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(payload)
        except OSError:
            pass

    def default_player_name(self):
        uname = os.environ.get("USER") or os.environ.get("LOGNAME")
        if uname:
            return self.sanitize_name(uname)
        return self.default_player_name_fallback()

    def sanitize_name(self, name):
        cleaned = "".join(ch for ch in str(name).upper() if ch.isalnum() or ch in "_- ")
        cleaned = cleaned.strip()
        if not cleaned:
            cleaned = self.default_player_name_fallback()
        return cleaned[:8]

    def default_player_name_fallback(self):
        return "PLAYER"

    def score_qualifies_top10(self):
        if self.score <= 0:
            return False
        if len(self.top_scores) < 10:
            return True
        return self.score > self.top_scores[-1]["score"]

    def add_top_score(self, name, score):
        self.top_scores.append({"name": self.sanitize_name(name), "score": int(score)})
        self.top_scores = sorted(self.top_scores, key=lambda x: x["score"], reverse=True)[:10]
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
            try:
                self.stdscr.addstr(self.h // 2 - 2, max(1, self.w // 2 - len(title) // 2), title, self.color_attr(2) | curses.A_BOLD)
                self.stdscr.addstr(self.h // 2, max(1, self.w // 2 - len(prompt) // 2), prompt, self.color_attr(1))
                self.stdscr.addstr(self.h // 2 + 1, max(1, self.w // 2 - 5), f"[{current:<8}]", self.color_attr(4) | curses.A_BOLD)
                self.stdscr.addstr(self.h // 2 + 3, max(1, self.w // 2 - len(hint) // 2), hint, self.color_attr(3))
            except curses.error:
                pass
            self.stdscr.refresh()

            ch = self.stdscr.getch()
            if ch in (10, 13, curses.KEY_ENTER):
                break
            if ch in (curses.KEY_BACKSPACE, 127, 8):
                if buf:
                    buf.pop()
                continue
            if 32 <= ch <= 126 and len(buf) < 8:
                c = chr(ch).upper()
                if c.isalnum() or c in "_- ":
                    buf.append(c)

        name = "".join(buf).strip() or default
        self.stdscr.nodelay(True)
        return self.sanitize_name(name)

    def show_top10_intro(self, seconds=3.0):
        end_time = time.monotonic() + seconds
        self.stdscr.nodelay(True)

        while time.monotonic() < end_time:
            self.stdscr.erase()
            title = "TOP 10 PILOTS"
            try:
                self.stdscr.addstr(1, max(1, self.w // 2 - len(title) // 2), title, self.color_attr(2) | curses.A_BOLD)
                self.stdscr.addstr(2, max(1, self.w // 2 - 8), "NAME     SCORE", self.color_attr(1) | curses.A_BOLD)
            except curses.error:
                pass

            if self.top_scores:
                for idx, entry in enumerate(self.top_scores[:10], start=1):
                    line = f"{idx:>2}. {entry['name']:<8} {entry['score']:>6}"
                    y = 2 + idx
                    if y >= self.h - 2:
                        break
                    try:
                        self.stdscr.addstr(y, max(1, self.w // 2 - 10), line, self.color_attr(1))
                    except curses.error:
                        pass
            else:
                try:
                    self.stdscr.addstr(5, max(1, self.w // 2 - 8), "NO SCORES YET", self.color_attr(3))
                except curses.error:
                    pass

            self.stdscr.refresh()
            time.sleep(0.05)

    def finalize_score_submission(self):
        if self.score_qualifies_top10():
            name = self.prompt_for_name()
            self.add_top_score(name, self.score)

        self.high_score = max(self.high_score, self.score)
        self.games_played += 1
        self.save_score_file()

    def spawn_stars(self):
        self.stars = []
        count = max(80, (self.w * self.h) // 30)
        for _ in range(count):
            self.stars.append(
                Star(
                    x=random.randint(1, self.w - 2),
                    y=random.randint(2, self.h - 2),
                    glyph=random.choice([".", ".", ".", "*", "+"]),
                    color=random.choice([1, 3, 5, 6]),
                )
            )

    def spawn_enemies(self):
        self.enemies = []
        self.stage_started_at = time.monotonic()
        self.beam_enemy = None
        self.beam_frames = 0
        self.beam_length = 0
        self.capture_revenge_target = None
        self.captured_ship_enemy = None
        self.captured_ship_active = False
        self.challenge_total = 0
        self.challenge_hits = 0
        self.challenge_bonus_awarded = False

        if self.is_challenging_stage():
            self.spawn_challenge_enemies()
            return

        spacing = 3
        cols = max(12, min(18, (self.w - 8) // spacing))
        rows = [
            ("M", 150),
            ("V", 80),
            ("V", 80),
            ("A", 50),
            ("A", 50),
        ]
        formation_width = (cols - 1) * spacing
        x_start = max(3, (self.w - formation_width) // 2)
        y_start = 4
        for r, (glyph, points) in enumerate(rows):
            for c in range(cols):
                self.enemies.append(
                    Enemy(x=x_start + c * spacing, y=y_start + r * 2, glyph=glyph, points=points)
                )
        self.enemy_dir = 1

    def spawn_challenge_enemies(self):
        margin = 4
        width = max(12, self.w - (margin * 2))
        stride = max(1, width // max(1, CHALLENGE_ENEMIES_PER_GROUP - 1))
        self.challenge_total = CHALLENGE_GROUPS * CHALLENGE_ENEMIES_PER_GROUP
        self.challenge_hits = 0

        for group in range(CHALLENGE_GROUPS):
            from_left = (group % 2) == 0
            for i in range(CHALLENGE_ENEMIES_PER_GROUP):
                idx = i if from_left else (CHALLENGE_ENEMIES_PER_GROUP - 1 - i)
                x = margin + (idx * stride)
                x = max(3, min(self.w - 4, x))
                y = -((group * 3) + i)
                self.enemies.append(
                    Enemy(
                        x=x,
                        y=y,
                        glyph="B",
                        points=100,
                        diving=True,
                        dive_dx=1 if from_left else -1,
                        dive_dy=1,
                    )
                )

    def enemy_color(self, enemy):
        if enemy.diving:
            return self.color_attr(4)
        if enemy.glyph == "M":
            return self.color_attr(7)
        if enemy.glyph == "V":
            return self.color_attr(2)
        return self.color_attr(3)

    def update_background(self):
        for star in self.stars:
            if random.random() < 0.02:
                star.glyph = random.choice([".", "*", "+"])
            if random.random() < 0.01:
                star.color = random.choice([1, 3, 5, 6])

    def draw_capture_beam(self):
        boss = self.beam_enemy
        if self.beam_frames <= 0 or boss is None:
            return
        if not boss.alive or not boss.diving:
            return

        base_y = boss.y + 1
        max_rows = min(12, self.beam_length)
        if max_rows <= 0:
            return

        for i in range(max_rows):
            y = base_y + i
            left = max(1, boss.x - i)
            right = min(self.w - 2, boss.x + i)
            if y <= 1 or y >= self.h - 1:
                continue
            try:
                if left <= right:
                    self.stdscr.addstr(y, left, "~" * (right - left + 1), self.color_attr(3))
            except curses.error:
                pass

    def draw_player_explosion(self):
        phase = self.respawn_frames % 4
        cx = self.explosion_x
        cy = self.explosion_y
        chars = ["*", "x", "+", "#"]
        ch = chars[phase]
        points = [
            (cx, cy),
            (cx - 1, cy),
            (cx + 1, cy),
            (cx, cy - 1),
            (cx, cy + 1),
            (cx - 1, cy - 1),
            (cx + 1, cy - 1),
            (cx - 1, cy + 1),
            (cx + 1, cy + 1),
        ]
        if phase in (1, 3):
            points.extend([(cx - 2, cy), (cx + 2, cy), (cx, cy - 2), (cx, cy + 2)])

        for x, y in points:
            if 1 < y < self.h - 1 and 1 < x < self.w - 1:
                try:
                    self.stdscr.addch(y, x, ch, self.color_attr(2) | curses.A_BOLD)
                except curses.error:
                    pass

    def draw(self):
        self.stdscr.erase()

        for s in self.stars:
            if 1 < s.y < self.h - 1 and 0 < s.x < self.w - 1:
                try:
                    self.stdscr.addch(s.y, s.x, s.glyph, self.color_attr(s.color))
                except curses.error:
                    pass

        top_label = "HIGH SCORE"
        top_x = max(1, (self.w // 2) - (len(top_label) // 2))
        try:
            self.stdscr.addstr(0, top_x, top_label, self.color_attr(2) | curses.A_BOLD)
            score_text = f"{self.high_score:05d}"
            score_x = max(1, (self.w // 2) - (len(score_text) // 2))
            self.stdscr.addstr(1, score_x, score_text, self.color_attr(1) | curses.A_BOLD)
            self.stdscr.addstr(1, 1, f"1UP {self.score:05d}", self.color_attr(1))
            lives_text = "LIVES INF" if self.cheat_endless else f"LIVES {self.player_lives}"
            self.stdscr.addstr(1, self.w - len(lives_text) - 2, lives_text, self.color_attr(1))
            stage_text = f"STAGE {self.level} {self.stage_label()}"
            stage_x = max(1, self.w - len(stage_text) - 2)
            self.stdscr.addstr(0, stage_x, stage_text, self.color_attr(4) | curses.A_BOLD)
        except curses.error:
            pass

        if self.paused:
            try:
                self.stdscr.addstr(2, self.w - 8, "PAUSED", self.color_attr(4))
            except curses.error:
                pass

        cheat_flags = []
        if self.cheat_endless:
            cheat_flags.append("ENDLESS")
        if self.cheat_machine_gun:
            cheat_flags.append("M-GUN")
        if cheat_flags:
            try:
                self.stdscr.addstr(2, 1, "CHEAT: " + ",".join(cheat_flags), self.color_attr(6) | curses.A_BOLD)
            except curses.error:
                pass

        if self.is_challenging_stage():
            challenge_text = f"HITS {self.challenge_hits}/{self.challenge_total}"
            try:
                self.stdscr.addstr(2, max(1, self.w // 2 - len(challenge_text) // 2), challenge_text, self.color_attr(3) | curses.A_BOLD)
            except curses.error:
                pass
            if self.challenge_message_frames > 0:
                msg = f"PERFECT +{CHALLENGE_PERFECT_BONUS}"
                try:
                    self.stdscr.addstr(3, max(1, self.w // 2 - len(msg) // 2), msg, self.color_attr(2) | curses.A_BOLD)
                except curses.error:
                    pass

        self.draw_capture_beam()

        for e in self.enemies:
            if e.alive and 1 < e.y < self.h - 1 and 1 < e.x < self.w - 2:
                try:
                    attrs = self.enemy_color(e) | curses.A_BOLD
                    if e.diving:
                        attrs |= curses.A_REVERSE
                    self.stdscr.addstr(e.y, e.x - 1, f"<{e.glyph}>", attrs)
                except curses.error:
                    pass

        for b in self.bullets:
            if 1 < b.y < self.h - 1 and 1 < b.x < self.w - 1:
                try:
                    if b.from_enemy:
                        self.stdscr.addch(b.y, b.x, "!", self.color_attr(4) | curses.A_BOLD)
                    else:
                        self.stdscr.addch(b.y, b.x, "|", self.color_attr(1) | curses.A_BOLD)
                except curses.error:
                    pass

        if self.respawn_frames > 0:
            self.draw_player_explosion()
        elif self.capture_frames > 0:
            try:
                self.stdscr.addstr(
                    int(self.capture_y),
                    int(self.capture_x) - PLAYER_HALF_WIDTH,
                    "/A\\",
                    self.color_attr(3) | curses.A_BOLD,
                )
            except curses.error:
                pass

        if self.captured_ship_active and self.captured_ship_enemy and self.captured_ship_enemy.alive:
            held_x = self.captured_ship_enemy.x
            held_y = min(self.h - 3, self.captured_ship_enemy.y + 1)
            if 1 < held_y < self.h and PLAYER_HALF_WIDTH <= held_x < self.w - 1 - PLAYER_HALF_WIDTH:
                try:
                    self.stdscr.addstr(
                        held_y,
                        held_x - PLAYER_HALF_WIDTH,
                        "/A\\",
                        self.color_attr(3) | curses.A_BOLD,
                    )
                except curses.error:
                    pass

        should_draw_player = self.respawn_frames == 0 and self.capture_frames == 0 and (
            self.invuln_frames == 0 or (self.invuln_frames % 4 < 2)
        )
        if should_draw_player and 1 < self.player_y < self.h and PLAYER_HALF_WIDTH <= self.player_x < self.w - 1 - PLAYER_HALF_WIDTH:
            try:
                self.stdscr.addstr(
                    self.player_y,
                    self.player_x - PLAYER_HALF_WIDTH,
                    "/A\\",
                    self.color_attr(1) | curses.A_BOLD,
                )
            except curses.error:
                pass

        lives_icons = "" if self.cheat_endless else " ".join(["/A\\"] * max(0, self.player_lives))
        if lives_icons:
            try:
                self.stdscr.addstr(self.h - 1, 1, lives_icons, self.color_attr(1))
            except curses.error:
                pass

        try:
            self.stdscr.hline(self.h - 2, 0, ord("-"), self.w - 1)
        except curses.error:
            pass

        self.stdscr.refresh()

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

            if self.paused or self.respawn_frames > 0 or self.capture_frames > 0:
                key = self.stdscr.getch()
                continue

            if key == curses.KEY_LEFT:
                self.player_x = max(PLAYER_HALF_WIDTH + 1, self.player_x - 1)
            elif key == curses.KEY_RIGHT:
                self.player_x = min(self.w - 2 - PLAYER_HALF_WIDTH, self.player_x + 1)
            elif key == ord(" "):
                now = time.monotonic()
                active_player_bullets = sum(
                    1 for b in self.bullets if not b.from_enemy and 1 < b.y < self.h - 1
                )
                bullets_per_shot = 2 if self.dual_shot else 1
                if now - self.last_shot >= self.player_cooldown and active_player_bullets + bullets_per_shot <= self.max_player_bullets:
                    if self.dual_shot:
                        left_x = max(1, self.player_x - 1)
                        right_x = min(self.w - 2, self.player_x + 1)
                        self.bullets.append(Bullet(left_x, self.player_y - 1, -1, False))
                        self.bullets.append(Bullet(right_x, self.player_y - 1, -1, False))
                    else:
                        self.bullets.append(Bullet(self.player_x, self.player_y - 1, -1, False))
                    self.last_shot = now
            key = self.stdscr.getch()

    def maybe_start_dive(self, living):
        if self.is_challenging_stage():
            return

        chance = min(0.45, DIVE_CHANCE_BASE + (self.level * 0.02))
        if random.random() >= chance:
            return

        candidates = [e for e in living if not e.diving]
        if not candidates:
            return

        diver = random.choice(candidates)
        diver.diving = True
        diver.dive_dy = 1
        offset = self.player_x - diver.x
        if offset == 0:
            diver.dive_dx = random.choice([-1, 1])
        elif abs(offset) < 6:
            diver.dive_dx = 1 if offset > 0 else -1
        else:
            diver.dive_dx = 2 if offset > 0 else -2

        if diver.glyph == "M" and random.random() < 0.75:
            self.beam_enemy = diver
            self.beam_frames = random.randint(24, 42)
            self.beam_length = 1

    def update_divers(self, living):
        self.dive_side_toggle = not self.dive_side_toggle
        for e in living:
            if not e.diving:
                continue

            # Beam capture dive: descend near the player row so the beam can reach.
            if self.beam_enemy is e and self.beam_frames > 0:
                target_x = self.player_x
                if e.x < target_x:
                    e.dive_dx = min(2, e.dive_dx + 1)
                elif e.x > target_x:
                    e.dive_dx = max(-2, e.dive_dx - 1)
                else:
                    e.dive_dx = 0

                e.x += e.dive_dx
                hold_y = min(self.h - 5, self.player_y - 4)
                if e.y < hold_y:
                    e.y += 1
                else:
                    e.y = hold_y
                e.x = max(2, min(self.w - 3, e.x))
                continue

            if random.random() < 0.35:
                if self.player_x > e.x:
                    e.dive_dx = min(2, e.dive_dx + 1)
                elif self.player_x < e.x:
                    e.dive_dx = max(-2, e.dive_dx - 1)

            if random.random() < 0.20:
                e.dive_dx = max(-2, min(2, e.dive_dx + random.choice([-1, 0, 1])))

            # Prioritize side-to-side movement over vertical movement.
            e.x += e.dive_dx
            if self.dive_side_toggle:
                e.y += e.dive_dy

            if e.y >= self.h - 2 or e.x <= 1 or e.x >= self.w - 2:
                if self.captured_ship_enemy is e and self.captured_ship_active:
                    e.x = max(3, min(self.w - 3, e.x))
                    e.y = min(7, max(4, e.y))
                    e.dive_dx *= -1
                    continue

                e.diving = False
                if self.beam_enemy is e:
                    self.beam_enemy = None
                    self.beam_frames = 0
                e.x = random.randint(5, self.w - 6)
                e.y = random.randint(4, 7)

    def update_challenge_divers(self, living):
        center_x = self.w // 2
        for e in living:
            if not e.diving:
                e.diving = True

            if not e.crossed_center:
                if abs(e.x - center_x) <= 1:
                    e.crossed_center = True
                    e.dive_dx = random.choice([-2, -1, 1, 2])
                else:
                    e.dive_dx = 1 if e.x < center_x else -1

            e.x += e.dive_dx
            e.y += e.dive_dy

            if e.x <= 2 or e.x >= self.w - 3:
                e.dive_dx *= -1
                e.x = max(3, min(self.w - 4, e.x))

            if e.y >= self.h - 2:
                e.y = random.randint(-8, -1)
                e.x = max(3, min(self.w - 4, e.x + random.choice([-4, -2, 0, 2, 4])))

    def update_beam_state(self):
        if self.beam_enemy is None:
            self.beam_frames = 0
            self.beam_length = 0
            return

        if (not self.beam_enemy.alive) or (not self.beam_enemy.diving):
            self.beam_enemy = None
            self.beam_frames = 0
            self.beam_length = 0
            return

        # Don't burn beam timer while boss is still too high to reach the player.
        # Beam max length is 12, so boss needs to be near the lower playfield first.
        min_boss_y_for_reach = self.player_y - 12
        if self.beam_enemy.y < min_boss_y_for_reach:
            self.beam_length = min(12, self.beam_length + 1)
            return

        if self.beam_frames > 0:
            self.beam_frames -= 1
            self.beam_length = min(12, self.beam_length + 1)
        else:
            self.beam_enemy = None
            self.beam_length = 0

    def maybe_capture_player(self):
        boss = self.beam_enemy
        if self.beam_frames <= 0 or boss is None:
            return
        if self.capture_frames > 0 or self.respawn_frames > 0 or self.invuln_frames > 0:
            return

        base_y = boss.y + 1
        if self.player_y < base_y:
            return

        # Capture only when the live beam actually reaches the player row.
        tip_y = base_y + self.beam_length - 1
        if tip_y < self.player_y:
            return

        contact_depth = self.player_y - base_y
        left = boss.x - contact_depth
        right = boss.x + contact_depth
        if left <= self.player_x <= right:
            self.trigger_player_capture(boss)

    def move_enemies(self):
        if self.paused:
            return

        now = time.monotonic()
        if self.is_challenging_stage():
            step_time = 0.07
        else:
            step_time = max(0.10, ENEMY_STEP_TIME - (self.level * 0.03))
        if now - self.last_enemy_step < step_time:
            return
        self.last_enemy_step = now

        living = [e for e in self.enemies if e.alive]
        if not living:
            return

        if self.is_challenging_stage():
            self.update_challenge_divers(living)
            if self.challenge_message_frames > 0:
                self.challenge_message_frames -= 1
            return

        formation = [e for e in living if not e.diving]
        if formation:
            min_x = min(e.x for e in formation)
            max_x = max(e.x for e in formation)
            hit_side = (self.enemy_dir == 1 and max_x >= self.w - 3) or (
                self.enemy_dir == -1 and min_x <= 2
            )

            if hit_side:
                self.enemy_dir *= -1
                self.edge_hits += 1
                if self.edge_hits % ENEMY_DROP_EVERY == 0:
                    for e in formation:
                        e.y += ENEMY_DROP_ROWS
                        if e.y >= self.player_y and not self.cheat_endless:
                            self.player_lives = 0
            else:
                for e in formation:
                    e.x += self.enemy_dir

        self.maybe_start_dive(living)
        self.update_divers(living)

        for e in living:
            active_enemy_bullets = sum(1 for b in self.bullets if b.from_enemy)
            max_enemy_bullets = MAX_ENEMY_BULLETS_BASE + min(8, self.level // 2)
            if active_enemy_bullets >= max_enemy_bullets:
                break

            elapsed = max(0.0, time.monotonic() - self.stage_started_at)
            # Ease in enemy fire at stage start to avoid overwhelming openings.
            start_ramp = min(1.0, 0.35 + (0.65 * (elapsed / STAGE_FIRE_RAMP_SECONDS)))
            fire_chance = (ENEMY_FIRE_CHANCE + (self.level * 0.002)) * ENEMY_FIRE_SCALE * start_ramp
            if e.diving:
                # Stop dive fire in the bottom 25% of the screen.
                if e.y >= int(self.h * 0.75):
                    continue
                fire_chance *= 2.2
            if random.random() < fire_chance:
                self.bullets.append(Bullet(e.x, e.y + 1, 1, True))

        self.update_beam_state()
        self.maybe_capture_player()

    def move_bullets(self):
        if self.paused:
            return
        for b in self.bullets:
            b.y += b.dy
        self.bullets = [b for b in self.bullets if 1 < b.y < self.h - 2]

    def trigger_player_hit(self):
        if self.respawn_frames > 0 or self.invuln_frames > 0 or self.capture_frames > 0:
            return

        self.dual_shot = False
        self.capture_revenge_target = None
        if not self.cheat_endless:
            self.player_lives -= 1
        self.explosion_x = self.player_x
        self.explosion_y = self.player_y
        self.respawn_frames = RESPAWN_EXPLOSION_FRAMES

        self.bullets = [
            b for b in self.bullets
            if not (b.from_enemy and b.y >= self.player_y - 2)
        ]

        if self.player_lives <= 0 and not self.cheat_endless:
            self.running = False
            self.win = False
            return

        self.player_x = self.w // 2

    def trigger_player_capture(self, captor):
        self.capture_frames = CAPTURE_FRAMES
        self.capture_x = float(self.player_x)
        self.capture_y = float(self.player_y)
        self.capture_target_x = float(captor.x)
        self.capture_target_y = float(max(3, captor.y + 1))

        self.capture_revenge_target = captor
        self.captured_ship_active = True
        self.captured_ship_enemy = captor

        # Keep captor in a hold zone so it can be hunted down.
        captor.diving = False
        captor.y = min(7, max(4, captor.y))

        if not self.cheat_endless:
            self.player_lives -= 1
            self.pending_game_over = self.player_lives <= 0
        else:
            self.pending_game_over = False

        self.bullets = [b for b in self.bullets if not b.from_enemy]

    def restore_captured_fighter(self):
        # Rejoin the rescued ship to the player as a dual-fighter state.
        self.dual_shot = True
        self.capture_revenge_target = None
        self.captured_ship_active = False
        self.captured_ship_enemy = None

    def update_player_state(self):
        if self.capture_frames > 0:
            self.capture_frames -= 1
            self.capture_x += (self.capture_target_x - self.capture_x) * 0.25
            self.capture_y += (self.capture_target_y - self.capture_y) * 0.25
            if self.capture_frames == 0:
                if self.pending_game_over:
                    self.running = False
                    self.win = False
                    return
                self.player_x = self.w // 2
                self.invuln_frames = RESPAWN_INVULN_FRAMES
        elif self.respawn_frames > 0:
            self.respawn_frames -= 1
            if self.respawn_frames == 0 and self.player_lives > 0:
                self.invuln_frames = RESPAWN_INVULN_FRAMES
        elif self.invuln_frames > 0:
            self.invuln_frames -= 1

    def collisions(self):
        if self.paused:
            return

        enemy_map = {}
        for e in self.enemies:
            if not e.alive:
                continue
            enemy_map[(e.x, e.y)] = e
            enemy_map[(e.x - 1, e.y)] = e
            enemy_map[(e.x + 1, e.y)] = e

        remaining = []
        for b in self.bullets:
            if not b.from_enemy:
                hit = enemy_map.get((b.x, b.y))
                if hit:
                    if self.captured_ship_active and self.captured_ship_enemy is hit:
                        self.restore_captured_fighter()
                    elif self.capture_revenge_target is hit:
                        self.restore_captured_fighter()
                    hit.alive = False
                    self.score += hit.points
                    self.high_score = max(self.high_score, self.score)
                    if self.beam_enemy is hit:
                        self.beam_enemy = None
                        self.beam_frames = 0
                        self.beam_length = 0
                    if self.is_challenging_stage():
                        self.challenge_hits += 1
                    continue
            remaining.append(b)
        self.bullets = remaining

        if self.is_challenging_stage():
            return

        vulnerable = (
            self.respawn_frames == 0
            and self.invuln_frames == 0
            and self.capture_frames == 0
        )

        remaining = []
        took_hit = False
        for b in self.bullets:
            if (
                not took_hit
                and vulnerable
                and b.from_enemy
                and b.y >= self.player_y - 1
                and abs(b.x - self.player_x) <= PLAYER_HALF_WIDTH
            ):
                self.trigger_player_hit()
                took_hit = True
                continue
            remaining.append(b)
        self.bullets = remaining

        if not took_hit and vulnerable:
            for e in self.enemies:
                if not e.alive or not e.diving:
                    continue
                if e.y >= self.player_y - 1 and abs(e.x - self.player_x) <= PLAYER_HALF_WIDTH + 1:
                    self.trigger_player_hit()
                    e.alive = False
                    if self.beam_enemy is e:
                        self.beam_enemy = None
                        self.beam_frames = 0
                        self.beam_length = 0
                    if self.captured_ship_enemy is e:
                        self.captured_ship_enemy = None
                        self.captured_ship_active = False
                        self.capture_revenge_target = None
                    break

        if self.player_lives <= 0 and self.capture_frames == 0 and not self.cheat_endless:
            self.running = False
            self.win = False

    def loop(self):
        self.last_enemy_step = time.monotonic()
        while self.running:
            self.handle_input()
            self.update_background()
            self.move_enemies()
            self.move_bullets()
            self.collisions()
            self.update_player_state()
            living = [e for e in self.enemies if e.alive]
            if not living:
                if self.is_challenging_stage() and not self.challenge_bonus_awarded:
                    if self.challenge_total > 0 and self.challenge_hits == self.challenge_total:
                        self.score += CHALLENGE_PERFECT_BONUS
                        self.high_score = max(self.high_score, self.score)
                        self.challenge_message_frames = CHALLENGE_MESSAGE_FRAMES
                    self.challenge_bonus_awarded = True
                self.level += 1
                self.spawn_enemies()
            self.draw()
            time.sleep(TICK_SECONDS)

    def game_over_screen(self):
        self.finalize_score_submission()
        self.stdscr.nodelay(False)
        self.stdscr.erase()
        msg = "YOU WIN!" if self.win else "GAME OVER"
        try:
            self.stdscr.addstr(
                self.h // 2 - 1,
                max(1, self.w // 2 - len(msg) // 2),
                msg,
                self.color_attr(2) | curses.A_BOLD,
            )
            score_line = f"Final score: {self.score}"
            self.stdscr.addstr(
                self.h // 2,
                max(1, self.w // 2 - len(score_line) // 2),
                score_line,
                self.color_attr(1),
            )
            hint = "Press any key to exit"
            self.stdscr.addstr(
                self.h // 2 + 2,
                max(1, self.w // 2 - len(hint) // 2),
                hint,
                self.color_attr(4),
            )
        except curses.error:
            pass
        self.stdscr.refresh()
        self.stdscr.getch()


def run(stdscr, endless=False, machine_gun=False):
    game = Game(stdscr, endless=endless, machine_gun=machine_gun)
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
    game.draw()
    game.loop()
    game.game_over_screen()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Terminal Galaga clone")
    parser.add_argument("--endless", action="store_true", help="Disable win condition; play until death or Ctrl+C")
    parser.add_argument("--machine-gun", action="store_true", help="Enable high-rate player fire")
    args = parser.parse_args()

    try:
        curses.wrapper(run, args.endless, args.machine_gun)
    except KeyboardInterrupt:
        pass
