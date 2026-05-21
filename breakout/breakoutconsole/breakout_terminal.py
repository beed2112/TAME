#!/usr/bin/env python3
import curses
import math
import os
import random
import time
from dataclasses import dataclass


TICK_SECONDS = 0.02
MIN_WIDTH = 84
MIN_HEIGHT = 30
SCORE_FILE_NAME = ".breakout_console"
BRICK_COLS = 20
BRICK_ROWS = 8
EMPTY_ROWS_ABOVE = 2
PLAYFIELD_WIDTH = 40
PLAYFIELD_HEIGHT = 30
INITIAL_LIVES = 3
INITIAL_PADDLE_WIDTH = 7
SHRUNK_PADDLE_WIDTH = 4
PADDLE_SPEED = 56.0
SHRUNK_PADDLE_SPEED = 66.0
BALL_START_SPEED = 10.125
BALL_MAX_SPEED = 14.25
BALL_MIN_DY = 0.35
SIDE_PANEL_WIDTH = 28
BOTTOM_MARGIN = 2
BRICK_BANDS = (
    {"rows": (0, 1), "label": "RED", "score": 7, "color": 2},
    {"rows": (2, 3), "label": "ORANGE", "score": 5, "color": 3},
    {"rows": (4, 5), "label": "GREEN", "score": 3, "color": 4},
    {"rows": (6, 7), "label": "YELLOW", "score": 1, "color": 5},
)


@dataclass
class Ball:
    x: float = 0.0
    y: float = 0.0
    dx: float = 0.0
    dy: float = 0.0
    speed: float = BALL_START_SPEED
    attached: bool = True


class Game:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.h = 0
        self.w = 0
        self.use_colors = False
        self.running = True
        self.paused = False
        self.game_over = False
        self.cleared = False
        self.score = 0
        self.high_score = 0
        self.games_played = 0
        self.top_scores = []
        self.level = 1
        self.lives = INITIAL_LIVES
        self.paddle_x = 0.0
        self.paddle_width = INITIAL_PADDLE_WIDTH
        self.ball = Ball()
        self.last_frame_at = time.monotonic()
        self.last_bounce_at = 0.0
        self.wall_hit_count = 0
        self.red_touched = False
        self.orange_touched = False
        self.ceiling_break_armed = False
        self.paddle_shrunk = False
        self.bricks_remaining = 0
        self.bricks = []
        self.message = "PRESS SPACE TO SERVE"

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
            curses.init_pair(2, curses.COLOR_RED, -1)
            curses.init_pair(3, curses.COLOR_YELLOW, -1)
            curses.init_pair(4, curses.COLOR_GREEN, -1)
            curses.init_pair(5, curses.COLOR_CYAN, -1)
            curses.init_pair(6, curses.COLOR_MAGENTA, -1)
            curses.init_pair(7, curses.COLOR_BLUE, -1)
            self.use_colors = True

        self.load_score_file()
        self.reset_wave(full_reset=True)

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

        while True:
            self.stdscr.erase()
            title = "NEW TOP 10 SCORE"
            prompt = "Enter name (max 8 chars):"
            hint = "ENTER confirm | BACKSPACE edit"
            current = "".join(buf)[:8]
            self.safe_addstr(self.h // 2 - 2, max(1, self.w // 2 - len(title) // 2), title, self.color_attr(6) | curses.A_BOLD)
            self.safe_addstr(self.h // 2, max(1, self.w // 2 - len(prompt) // 2), prompt, self.color_attr(1))
            self.safe_addstr(self.h // 2 + 1, max(1, self.w // 2 - 5), f"[{current:<8}]", self.color_attr(5) | curses.A_BOLD)
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

        name = "".join(buf).strip() or default
        self.stdscr.nodelay(True)
        return self.sanitize_name(name)

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

    def playfield_top(self):
        return 3

    def playfield_left(self):
        total_width = PLAYFIELD_WIDTH + SIDE_PANEL_WIDTH + 6
        start = max(2, (self.w - total_width) // 2)
        return start + 2

    def playfield_bottom(self):
        return self.playfield_top() + PLAYFIELD_HEIGHT - 1

    def side_panel_left(self):
        return self.playfield_left() + PLAYFIELD_WIDTH + 5

    def brick_score(self, row):
        for band in BRICK_BANDS:
            if row in band["rows"]:
                return band["score"]
        return 1

    def brick_color(self, row):
        for band in BRICK_BANDS:
            if row in band["rows"]:
                return band["color"]
        return 1

    def reset_wave(self, full_reset=False):
        if full_reset:
            self.score = 0
            self.level = 1
            self.lives = INITIAL_LIVES
            self.game_over = False
            self.cleared = False
        self.paddle_width = INITIAL_PADDLE_WIDTH
        self.paddle_shrunk = False
        self.red_touched = False
        self.orange_touched = False
        self.ceiling_break_armed = False
        self.wall_hit_count = 0
        self.message = "PRESS SPACE TO SERVE"
        self.bricks = [[True for _ in range(BRICK_COLS)] for _ in range(BRICK_ROWS)]
        self.bricks_remaining = BRICK_ROWS * BRICK_COLS
        self.reset_serve(centered=True)

    def reset_serve(self, centered=False):
        if centered:
            self.paddle_x = (PLAYFIELD_WIDTH - self.paddle_width) / 2
        else:
            self.paddle_x = min(max(0.0, self.paddle_x), PLAYFIELD_WIDTH - self.paddle_width)
        self.ball = Ball()
        self.ball.attached = True
        self.ball.speed = min(BALL_MAX_SPEED, BALL_START_SPEED + ((self.level - 1) * 0.375))
        self.ball.dx = random.choice([-0.72, 0.72])
        self.ball.dy = -1.0
        self.sync_attached_ball()

    def sync_attached_ball(self):
        self.ball.x = self.paddle_x + (self.paddle_width / 2)
        self.ball.y = PLAYFIELD_HEIGHT - BOTTOM_MARGIN - 2

    def launch_ball(self):
        if not self.ball.attached or self.game_over:
            return
        self.ball.attached = False
        self.message = ""
        self.normalize_ball_velocity()

    def normalize_ball_velocity(self):
        length = math.hypot(self.ball.dx, self.ball.dy)
        if length == 0:
            self.ball.dx = 0.72
            self.ball.dy = -1.0
            length = math.hypot(self.ball.dx, self.ball.dy)
        self.ball.dx /= length
        self.ball.dy /= length

        if abs(self.ball.dy) < BALL_MIN_DY:
            self.ball.dy = math.copysign(BALL_MIN_DY, self.ball.dy or -1.0)
            horizontal = math.sqrt(max(0.01, 1.0 - (self.ball.dy * self.ball.dy)))
            self.ball.dx = math.copysign(horizontal, self.ball.dx or random.choice([-1.0, 1.0]))

    def increase_ball_speed(self, amount):
        self.ball.speed = min(BALL_MAX_SPEED, self.ball.speed + amount)

    def handle_input(self):
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
            if self.paused:
                continue
            if self.game_over:
                if key in (ord(" "), 10, 13, curses.KEY_ENTER):
                    self.running = False
                continue

            if key in (curses.KEY_LEFT, ord("a"), ord("A")):
                self.move_paddle(-1)
            elif key in (curses.KEY_RIGHT, ord("d"), ord("D")):
                self.move_paddle(1)
            elif key in (ord(" "), 10, 13, curses.KEY_ENTER):
                self.launch_ball()

    def move_paddle(self, direction):
        current_speed = SHRUNK_PADDLE_SPEED if self.paddle_shrunk else PADDLE_SPEED
        move_amount = current_speed * TICK_SECONDS
        self.paddle_x += direction * move_amount
        self.paddle_x = min(max(0.0, self.paddle_x), PLAYFIELD_WIDTH - self.paddle_width)
        if self.ball.attached:
            self.sync_attached_ball()

    def update(self):
        if self.paused or self.game_over:
            return

        now = time.monotonic()
        dt = min(0.04, now - self.last_frame_at)
        self.last_frame_at = now

        if self.ball.attached:
            self.sync_attached_ball()
            return

        steps = max(1, int(math.ceil((self.ball.speed * dt) / 0.35)))
        step_dt = dt / steps
        for _ in range(steps):
            if self.game_over or self.ball.attached:
                break
            self.advance_ball(step_dt)

    def advance_ball(self, dt):
        next_x = self.ball.x + (self.ball.dx * self.ball.speed * dt)
        next_y = self.ball.y + (self.ball.dy * self.ball.speed * dt)

        if next_x <= 0.5:
            next_x = 0.5
            self.ball.dx = abs(self.ball.dx)
        elif next_x >= PLAYFIELD_WIDTH - 0.5:
            next_x = PLAYFIELD_WIDTH - 0.5
            self.ball.dx = -abs(self.ball.dx)

        if next_y <= 0.5:
            next_y = 0.5
            self.ball.dy = abs(self.ball.dy)
            if self.ceiling_break_armed and not self.paddle_shrunk:
                self.paddle_shrunk = True
                self.paddle_width = SHRUNK_PADDLE_WIDTH
                self.paddle_x = min(self.paddle_x, PLAYFIELD_WIDTH - self.paddle_width)
                self.ceiling_break_armed = False
                self.message = "PADDLE SHRUNK"

        paddle_row = PLAYFIELD_HEIGHT - BOTTOM_MARGIN - 2
        if self.ball.dy > 0 and self.ball.y <= paddle_row <= next_y:
            crossing_ratio = 0.0 if next_y == self.ball.y else (paddle_row - self.ball.y) / (next_y - self.ball.y)
            crossing_ratio = min(1.0, max(0.0, crossing_ratio))
            crossing_x = self.ball.x + ((next_x - self.ball.x) * crossing_ratio)
            paddle_left = self.paddle_x
            paddle_right = self.paddle_x + self.paddle_width
            if paddle_left - 0.35 <= crossing_x <= paddle_right + 0.35:
                contact_x = min(max(crossing_x, paddle_left), paddle_right)
                relative = ((contact_x - paddle_left) / max(1.0, self.paddle_width)) - 0.5
                self.ball.dx = relative * 1.8
                self.ball.dy = -abs(1.0 - min(0.45, abs(relative) * 0.35))
                self.normalize_ball_velocity()
                next_x = contact_x + (self.ball.dx * self.ball.speed * dt * (1.0 - crossing_ratio))
                next_y = paddle_row - 0.35
                self.wall_hit_count += 1
                if self.wall_hit_count == 4:
                    self.increase_ball_speed(0.525)
                elif self.wall_hit_count == 12:
                    self.increase_ball_speed(0.675)
            elif next_y >= PLAYFIELD_HEIGHT - 0.3:
                self.lose_life()
                return
        elif next_y >= PLAYFIELD_HEIGHT - 0.3:
            self.lose_life()
            return

        brick_hit = self.hit_brick_at(next_x, next_y)
        if brick_hit is not None:
            if self.ball.attached:
                return
            row, col = brick_hit
            hit_x = col * 2 + 1
            hit_y = EMPTY_ROWS_ABOVE + row + 0.5
            overlap_x = abs(next_x - hit_x)
            overlap_y = abs(next_y - hit_y)
            if overlap_x > overlap_y:
                self.ball.dx *= -1
            else:
                self.ball.dy *= -1
            next_x = self.ball.x + (self.ball.dx * self.ball.speed * dt)
            next_y = self.ball.y + (self.ball.dy * self.ball.speed * dt)

        self.normalize_ball_velocity()
        self.ball.x = next_x
        self.ball.y = next_y

    def hit_brick_at(self, x, y):
        row = int(math.floor(y)) - EMPTY_ROWS_ABOVE
        col = int(math.floor(x / 2.0))
        if row < 0 or row >= BRICK_ROWS or col < 0 or col >= BRICK_COLS:
            return None
        if not self.bricks[row][col]:
            return None

        self.bricks[row][col] = False
        self.bricks_remaining -= 1
        self.score += self.brick_score(row)
        self.high_score = max(self.high_score, self.score)

        if row in BRICK_BANDS[0]["rows"]:
            self.red_touched = True
            self.ceiling_break_armed = True
            self.increase_ball_speed(0.375)
        elif row in BRICK_BANDS[1]["rows"] and not self.orange_touched:
            self.orange_touched = True
            self.increase_ball_speed(0.3)

        if self.bricks_remaining <= 0:
            self.level += 1
            self.reset_wave(full_reset=False)
            self.message = "RACK CLEARED"
        return row, col

    def lose_life(self):
        self.lives -= 1
        if self.lives <= 0:
            self.game_over = True
            self.running = False
            return
        self.message = "PRESS SPACE TO SERVE"
        self.reset_serve(centered=False)

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

    def draw(self):
        self.refresh_size()
        self.stdscr.erase()
        if self.h < MIN_HEIGHT or self.w < MIN_WIDTH:
            self.safe_addstr(self.h // 2, max(1, self.w // 2 - 9), "TERMINAL TOO SMALL", self.color_attr(2) | curses.A_BOLD)
            self.safe_addstr(self.h // 2 + 1, max(1, self.w // 2 - 17), f"Need at least {MIN_WIDTH}x{MIN_HEIGHT}", self.color_attr(1))
            self.stdscr.refresh()
            return
        self.draw_header()
        self.draw_playfield()
        self.draw_sidebar()
        self.stdscr.refresh()

    def draw_header(self):
        title = "BREAKOUT CONSOLE"
        self.safe_addstr(0, max(2, self.playfield_left()), title, self.color_attr(5) | curses.A_BOLD)
        self.safe_addstr(0, self.side_panel_left(), f"SCORE {self.score:05d}", self.color_attr(1) | curses.A_BOLD)
        self.safe_addstr(1, self.side_panel_left(), f"HIGH  {max(self.high_score, self.score):05d}", self.color_attr(1))

    def draw_playfield(self):
        top = self.playfield_top()
        left = self.playfield_left()
        inner_width = PLAYFIELD_WIDTH
        self.safe_addstr(top - 1, left - 1, "+" + ("-" * inner_width) + "+", self.color_attr(1))
        for row in range(PLAYFIELD_HEIGHT):
            self.safe_addstr(top + row, left - 1, "|", self.color_attr(1))
            self.safe_addstr(top + row, left + inner_width, "|", self.color_attr(1))
            self.safe_addstr(top + row, left, " " * inner_width)
        self.safe_addstr(top + PLAYFIELD_HEIGHT, left - 1, "+" + ("-" * inner_width) + "+", self.color_attr(1))

        for row in range(BRICK_ROWS):
            for col in range(BRICK_COLS):
                if not self.bricks[row][col]:
                    continue
                draw_y = top + EMPTY_ROWS_ABOVE + row
                draw_x = left + (col * 2)
                self.safe_addstr(draw_y, draw_x, "[]", self.color_attr(self.brick_color(row)) | curses.A_BOLD)

        paddle_y = top + PLAYFIELD_HEIGHT - BOTTOM_MARGIN - 1
        paddle_x = left + int(round(self.paddle_x))
        self.safe_addstr(paddle_y, paddle_x, "=" * self.paddle_width, self.color_attr(6) | curses.A_BOLD)

        ball_y = top + int(round(self.ball.y))
        ball_x = left + int(round(self.ball.x))
        self.safe_addstr(ball_y, ball_x, "o", self.color_attr(1) | curses.A_BOLD)

    def draw_sidebar(self):
        left = self.side_panel_left()
        top = self.playfield_top() + 3
        lines = [
            f"LEVEL   {self.level}",
            f"LIVES   {self.lives}",
            f"BRICKS  {self.bricks_remaining:03d}",
            "",
            "SCORING",
            "RED     7",
            "ORANGE  5",
            "GREEN   3",
            "YELLOW  1",
            "",
            "CONTROLS",
            "LEFT/RIGHT move",
            "A/D move",
            "SPACE launch",
            "ESC pause",
            "Q quit",
        ]
        for idx, line in enumerate(lines):
            attr = self.color_attr(1)
            if line in ("SCORING", "CONTROLS"):
                attr = self.color_attr(6) | curses.A_BOLD
            self.safe_addstr(top + idx, left, line, attr)

        status_y = self.playfield_top() + PLAYFIELD_HEIGHT - 3
        if self.paused:
            self.safe_addstr(status_y, left, "PAUSED", self.color_attr(3) | curses.A_BOLD)
        elif self.message:
            self.safe_addstr(status_y, left, self.message[:SIDE_PANEL_WIDTH - 2], self.color_attr(5) | curses.A_BOLD)

    def intro_screen(self):
        self.stdscr.nodelay(False)
        self.stdscr.erase()
        lines = [
            "BREAKOUT CONSOLE",
            "",
            "Clear the wall one brick at a time.",
            "Use the paddle to shape the ball angle.",
            "",
            "Controls",
            "Left/Right or A/D: move",
            "Space or Enter: serve",
            "Esc or P: pause",
            "Q: quit",
            "",
            "Press any key to start",
        ]
        for idx, line in enumerate(lines):
            attr = self.color_attr(5) | curses.A_BOLD if idx == 0 else self.color_attr(1)
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
        self.safe_addstr(self.h // 2 - 3, max(1, self.w // 2 - len(title) // 2), title, self.color_attr(2) | curses.A_BOLD)
        self.safe_addstr(self.h // 2 - 1, max(1, self.w // 2 - 10), f"Score {self.score:05d}", self.color_attr(1))
        self.safe_addstr(self.h // 2, max(1, self.w // 2 - 10), f"High  {self.high_score:05d}", self.color_attr(1))
        self.safe_addstr(self.h // 2 + 2, max(1, self.w // 2 - 18), "Press any key to return to cabinet", self.color_attr(5) | curses.A_BOLD)
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
