#!/usr/bin/env python3
import argparse
import curses
import os
import random
import time
from dataclasses import dataclass


BOARD_WIDTH = 10
BOARD_VISIBLE_HEIGHT = 20
BOARD_HIDDEN_ROWS = 2
BOARD_HEIGHT = BOARD_VISIBLE_HEIGHT + BOARD_HIDDEN_ROWS
BLOCK_TEXT = "[]"
GHOST_TEXT = ".."
PREVIEW_COUNT = 5
TICK_SECONDS = 0.02
LOCK_DELAY = 0.5
MIN_WIDTH = 74
MIN_HEIGHT = 28
SCORE_FILE_NAME = ".tetris_console"
LINE_CLEAR_SCORES = {1: 40, 2: 100, 3: 300, 4: 1200}
PIECE_ORDER = ["I", "O", "T", "S", "Z", "J", "L"]


PIECE_STATES = {
    "I": [
        [(0, 1), (1, 1), (2, 1), (3, 1)],
        [(2, 0), (2, 1), (2, 2), (2, 3)],
        [(0, 2), (1, 2), (2, 2), (3, 2)],
        [(1, 0), (1, 1), (1, 2), (1, 3)],
    ],
    "O": [
        [(1, 0), (2, 0), (1, 1), (2, 1)],
        [(1, 0), (2, 0), (1, 1), (2, 1)],
        [(1, 0), (2, 0), (1, 1), (2, 1)],
        [(1, 0), (2, 0), (1, 1), (2, 1)],
    ],
    "T": [
        [(1, 0), (0, 1), (1, 1), (2, 1)],
        [(1, 0), (1, 1), (2, 1), (1, 2)],
        [(0, 1), (1, 1), (2, 1), (1, 2)],
        [(1, 0), (0, 1), (1, 1), (1, 2)],
    ],
    "S": [
        [(1, 0), (2, 0), (0, 1), (1, 1)],
        [(1, 0), (1, 1), (2, 1), (2, 2)],
        [(1, 1), (2, 1), (0, 2), (1, 2)],
        [(0, 0), (0, 1), (1, 1), (1, 2)],
    ],
    "Z": [
        [(0, 0), (1, 0), (1, 1), (2, 1)],
        [(2, 0), (1, 1), (2, 1), (1, 2)],
        [(0, 1), (1, 1), (1, 2), (2, 2)],
        [(1, 0), (0, 1), (1, 1), (0, 2)],
    ],
    "J": [
        [(0, 0), (0, 1), (1, 1), (2, 1)],
        [(1, 0), (2, 0), (1, 1), (1, 2)],
        [(0, 1), (1, 1), (2, 1), (2, 2)],
        [(1, 0), (1, 1), (0, 2), (1, 2)],
    ],
    "L": [
        [(2, 0), (0, 1), (1, 1), (2, 1)],
        [(1, 0), (1, 1), (1, 2), (2, 2)],
        [(0, 1), (1, 1), (2, 1), (0, 2)],
        [(0, 0), (1, 0), (1, 1), (1, 2)],
    ],
}


JLSTZ_KICKS = [
    (0, 0),
    (-1, 0),
    (1, 0),
    (0, -1),
    (-1, -1),
    (1, -1),
    (-2, 0),
    (2, 0),
]

I_KICKS = [
    (0, 0),
    (-2, 0),
    (1, 0),
    (-1, 0),
    (2, 0),
    (0, -1),
    (0, 1),
]


@dataclass
class Piece:
    kind: str
    x: int
    y: int
    rotation: int = 0


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
        self.lines = 0
        self.level = 1
        self.board = [[None for _ in range(BOARD_WIDTH)] for _ in range(BOARD_HEIGHT)]
        self.queue = []
        self.bag = []
        self.hold_kind = None
        self.hold_used = False
        self.current = None
        self.last_fall_at = 0.0
        self.lock_started_at = None
        self.line_flash_frames = 0
        self.cleared_rows = []

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
            curses.init_pair(1, curses.COLOR_CYAN, -1)
            curses.init_pair(2, curses.COLOR_YELLOW, -1)
            curses.init_pair(3, curses.COLOR_MAGENTA, -1)
            curses.init_pair(4, curses.COLOR_GREEN, -1)
            curses.init_pair(5, curses.COLOR_RED, -1)
            curses.init_pair(6, curses.COLOR_BLUE, -1)
            curses.init_pair(7, curses.COLOR_WHITE, -1)
            curses.init_pair(8, curses.COLOR_WHITE, -1)
            self.use_colors = True

        self.load_score_file()
        self.refill_queue()
        self.spawn_piece()
        self.last_fall_at = time.monotonic()

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
        self.stdscr.keypad(True)

        while True:
            self.stdscr.erase()
            title = "NEW TOP 10 SCORE"
            prompt = "Enter name (max 8 chars):"
            hint = "ENTER confirm | BACKSPACE edit"
            current = "".join(buf)[:8]
            self.safe_addstr(self.h // 2 - 2, max(1, self.w // 2 - len(title) // 2), title, self.color_attr(5) | curses.A_BOLD)
            self.safe_addstr(self.h // 2, max(1, self.w // 2 - len(prompt) // 2), prompt, self.color_attr(8))
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

        name = "".join(buf).strip() or default
        self.stdscr.nodelay(True)
        return self.sanitize_name(name)

    def show_top10_intro(self, seconds=3.0):
        end_time = time.monotonic() + seconds
        self.stdscr.nodelay(True)

        while time.monotonic() < end_time:
            self.stdscr.erase()
            self.safe_addstr(1, max(1, self.w // 2 - 6), "TOP 10 SCORES", self.color_attr(5) | curses.A_BOLD)
            self.safe_addstr(2, max(1, self.w // 2 - 8), "NAME     SCORE", self.color_attr(8) | curses.A_BOLD)

            if self.top_scores:
                for idx, entry in enumerate(self.top_scores[:10], start=1):
                    y = 2 + idx
                    if y >= self.h - 2:
                        break
                    line = f"{idx:>2}. {entry['name']:<8} {entry['score']:>6}"
                    self.safe_addstr(y, max(1, self.w // 2 - 10), line, self.color_attr(8))
            else:
                self.safe_addstr(5, max(1, self.w // 2 - 6), "NO SCORES YET", self.color_attr(1))

            self.stdscr.refresh()
            time.sleep(0.05)

    def finalize_score_submission(self):
        if self.score_qualifies_top10():
            name = self.prompt_for_name()
            self.add_top_score(name, self.score)

        self.high_score = max(self.high_score, self.score)
        self.games_played += 1
        self.save_score_file()

    def refill_queue(self):
        while len(self.queue) < PREVIEW_COUNT + 1:
            if not self.bag:
                self.bag = PIECE_ORDER[:]
                random.shuffle(self.bag)
            self.queue.append(self.bag.pop())

    def spawn_piece(self):
        self.refill_queue()
        kind = self.queue.pop(0)
        self.current = Piece(kind=kind, x=3, y=0, rotation=0)
        self.hold_used = False
        self.lock_started_at = None
        self.last_fall_at = time.monotonic()
        if not self.can_place(self.current):
            self.game_over = True
            self.running = False

    def current_cells(self, piece=None):
        piece = piece or self.current
        return [
            (piece.x + dx, piece.y + dy)
            for dx, dy in PIECE_STATES[piece.kind][piece.rotation]
        ]

    def can_place(self, piece):
        for x, y in self.current_cells(piece):
            if x < 0 or x >= BOARD_WIDTH or y >= BOARD_HEIGHT:
                return False
            if y >= 0 and self.board[y][x] is not None:
                return False
        return True

    def move(self, dx, dy):
        candidate = Piece(self.current.kind, self.current.x + dx, self.current.y + dy, self.current.rotation)
        if not self.can_place(candidate):
            return False
        self.current = candidate
        if dy != 0 or dx != 0:
            self.reset_lock_delay()
        return True

    def rotation_kicks(self):
        return I_KICKS if self.current.kind == "I" else JLSTZ_KICKS

    def rotate(self, direction):
        if self.current.kind == "O":
            return True
        target_rotation = (self.current.rotation + direction) % 4
        for dx, dy in self.rotation_kicks():
            candidate = Piece(self.current.kind, self.current.x + dx, self.current.y + dy, target_rotation)
            if self.can_place(candidate):
                self.current = candidate
                self.reset_lock_delay()
                return True
        return False

    def hold(self):
        if self.hold_used:
            return
        current_kind = self.current.kind
        if self.hold_kind is None:
            self.hold_kind = current_kind
            self.spawn_piece()
        else:
            self.current = Piece(kind=self.hold_kind, x=3, y=0, rotation=0)
            self.hold_kind = current_kind
            if not self.can_place(self.current):
                self.game_over = True
                self.running = False
        self.hold_used = True
        self.lock_started_at = None

    def ghost_piece(self):
        ghost = Piece(self.current.kind, self.current.x, self.current.y, self.current.rotation)
        while self.can_place(Piece(ghost.kind, ghost.x, ghost.y + 1, ghost.rotation)):
            ghost.y += 1
        return ghost

    def hard_drop(self):
        distance = 0
        while self.move(0, 1):
            distance += 1
        self.score += distance * 2
        self.lock_piece()

    def soft_drop(self):
        if self.move(0, 1):
            self.score += 1
            self.last_fall_at = time.monotonic()
            return True
        return False

    def gravity_delay(self):
        return max(0.05, 0.8 * (0.82 ** (self.level - 1)))

    def reset_lock_delay(self):
        grounded = not self.can_place(Piece(self.current.kind, self.current.x, self.current.y + 1, self.current.rotation))
        self.lock_started_at = time.monotonic() if grounded else None

    def lock_piece(self):
        for x, y in self.current_cells():
            if 0 <= y < BOARD_HEIGHT:
                self.board[y][x] = self.current.kind
        self.clear_lines()
        self.spawn_piece()

    def clear_lines(self):
        full_rows = [
            idx for idx, row in enumerate(self.board)
            if all(cell is not None for cell in row)
        ]
        if not full_rows:
            return
        self.cleared_rows = full_rows[:]
        self.line_flash_frames = 3
        cleared = len(full_rows)
        remaining_rows = [
            row for idx, row in enumerate(self.board)
            if idx not in full_rows
        ]
        self.board = (
            [[None for _ in range(BOARD_WIDTH)] for _ in range(cleared)]
            + remaining_rows
        )
        self.lines += cleared
        self.level = 1 + (self.lines // 10)
        self.score += LINE_CLEAR_SCORES[cleared] * self.level
        self.high_score = max(self.high_score, self.score)

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

            if key == curses.KEY_LEFT:
                self.move(-1, 0)
            elif key == curses.KEY_RIGHT:
                self.move(1, 0)
            elif key == curses.KEY_DOWN:
                self.soft_drop()
            elif key in (curses.KEY_UP, ord("x"), ord("X")):
                self.rotate(1)
            elif key in (ord("z"), ord("Z"), ord("c"), ord("C")):
                self.rotate(-1)
            elif key == ord(" "):
                self.hard_drop()
            elif key in (ord("h"), ord("H"), curses.KEY_BTAB):
                self.hold()
            elif key in (ord("v"), ord("V")):
                self.hold()
            key = self.stdscr.getch()

    def update(self):
        if self.paused or self.game_over:
            return

        now = time.monotonic()
        if self.line_flash_frames > 0:
            self.line_flash_frames -= 1

        if now - self.last_fall_at >= self.gravity_delay():
            if self.move(0, 1):
                self.last_fall_at = now
            else:
                if self.lock_started_at is None:
                    self.lock_started_at = now
                elif now - self.lock_started_at >= LOCK_DELAY:
                    self.lock_piece()
                self.last_fall_at = now
        else:
            grounded = not self.can_place(Piece(self.current.kind, self.current.x, self.current.y + 1, self.current.rotation))
            if not grounded:
                self.lock_started_at = None
            elif self.lock_started_at is None:
                self.lock_started_at = now

    def block_color(self, kind):
        mapping = {
            "I": 1,
            "O": 2,
            "T": 3,
            "S": 4,
            "Z": 5,
            "J": 6,
            "L": 7,
        }
        return self.color_attr(mapping[kind]) | curses.A_BOLD

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

    def draw_block(self, top, left, cell_x, cell_y, kind, ghost=False):
        draw_y = top + (cell_y - BOARD_HIDDEN_ROWS)
        if cell_y < BOARD_HIDDEN_ROWS or draw_y < top:
            return
        draw_x = left + (cell_x * 2)
        text = GHOST_TEXT if ghost else BLOCK_TEXT
        attr = self.color_attr(8) if ghost else self.block_color(kind)
        if ghost:
            attr |= curses.A_DIM
        self.safe_addstr(draw_y, draw_x, text, attr)

    def draw_piece_preview(self, piece_kind, top, left, label):
        self.safe_addstr(top, left, label, self.color_attr(8) | curses.A_BOLD)
        for row in range(4):
            self.safe_addstr(top + 1 + row, left, "        ", self.color_attr(8))
        preview_piece = Piece(piece_kind, 0, 0, 0)
        cells = PIECE_STATES[piece_kind][0]
        min_x = min(x for x, _ in cells)
        max_x = max(x for x, _ in cells)
        min_y = min(y for _, y in cells)
        width = max_x - min_x + 1
        start_x = left + max(0, 4 - width)
        for x, y in cells:
            px = start_x + ((x - min_x) * 2)
            py = top + 1 + (y - min_y)
            self.safe_addstr(py, px, BLOCK_TEXT, self.block_color(piece_kind))

    def draw_board(self):
        self.stdscr.erase()
        board_top = 4
        board_left = max(18, self.w // 2 - 10)
        # Each board column renders as two characters, so the right border
        # should sit immediately after the visible playfield.
        board_right = board_left + (BOARD_WIDTH * 2)

        self.safe_addstr(0, 2, f"SCORE {self.score:07d}", self.color_attr(8) | curses.A_BOLD)
        self.safe_addstr(1, 2, f"HIGH  {max(self.high_score, self.score):07d}", self.color_attr(8))
        self.safe_addstr(0, board_left, "TETRIS CONSOLE", self.color_attr(1) | curses.A_BOLD)
        status = f"LEVEL {self.level}  LINES {self.lines}"
        self.safe_addstr(1, board_left, status, self.color_attr(8))

        if self.paused:
            self.safe_addstr(2, board_left, "PAUSED", self.color_attr(2) | curses.A_BOLD)
        elif self.game_over:
            self.safe_addstr(2, board_left, "TOP OUT", self.color_attr(5) | curses.A_BOLD)

        self.draw_piece_preview(self.hold_kind, 4, 2, "HOLD") if self.hold_kind else self.safe_addstr(4, 2, "HOLD", self.color_attr(8) | curses.A_BOLD)
        for idx, kind in enumerate(self.queue[:PREVIEW_COUNT]):
            self.draw_piece_preview(kind, 4 + idx * 5, board_right + 4, "NEXT" if idx == 0 else "")

        # Board frame.
        self.safe_addstr(board_top - 1, board_left - 1, "+" + ("-" * (BOARD_WIDTH * 2)) + "+", self.color_attr(8))
        for row in range(BOARD_VISIBLE_HEIGHT):
            self.safe_addstr(board_top + row, board_left - 1, "|", self.color_attr(8))
            self.safe_addstr(board_top + row, board_right, "|", self.color_attr(8))
        self.safe_addstr(board_top + BOARD_VISIBLE_HEIGHT, board_left - 1, "+" + ("-" * (BOARD_WIDTH * 2)) + "+", self.color_attr(8))

        for y in range(BOARD_HIDDEN_ROWS, BOARD_HEIGHT):
            for x in range(BOARD_WIDTH):
                kind = self.board[y][x]
                if kind is None:
                    self.safe_addstr(board_top + (y - BOARD_HIDDEN_ROWS), board_left + (x * 2), "  ")
                else:
                    self.draw_block(board_top, board_left, x, y, kind)

        ghost = self.ghost_piece()
        for x, y in self.current_cells(ghost):
            if (x, y) not in self.current_cells():
                self.draw_block(board_top, board_left, x, y, self.current.kind, ghost=True)

        for x, y in self.current_cells():
            self.draw_block(board_top, board_left, x, y, self.current.kind)

        controls = [
            "Left/Right: move",
            "Down: soft drop",
            "Up/X: rotate CW",
            "Z/C: rotate CCW",
            "Space: hard drop",
            "H/V: hold",
            "Esc: pause",
            "Q: quit",
        ]
        control_top = board_top + BOARD_VISIBLE_HEIGHT + 2
        for idx, line in enumerate(controls):
            self.safe_addstr(control_top + idx, 2, line, self.color_attr(8))

        self.stdscr.refresh()

    def intro_screen(self):
        self.stdscr.nodelay(False)
        self.stdscr.erase()
        lines = [
            "TETRIS CONSOLE",
            "",
            "Modern endless mode with ghost, hold, next queue,",
            "seven-bag randomizer, wall kicks, soft drop, and hard drop.",
            "",
            "Press any key to start",
        ]
        top = max(2, self.h // 2 - len(lines) // 2)
        for idx, line in enumerate(lines):
            attr = self.color_attr(1) | curses.A_BOLD if idx == 0 else self.color_attr(8)
            self.safe_addstr(top + idx, max(2, self.w // 2 - len(line) // 2), line, attr)
        self.stdscr.refresh()
        self.stdscr.getch()
        self.stdscr.nodelay(True)

    def game_over_screen(self):
        self.finalize_score_submission()
        self.stdscr.nodelay(False)
        self.stdscr.erase()
        title = "GAME OVER"
        score_line = f"Score {self.score}   High {max(self.high_score, self.score)}"
        hint = "Press any key to exit"
        self.safe_addstr(self.h // 2 - 1, max(1, self.w // 2 - len(title) // 2), title, self.color_attr(5) | curses.A_BOLD)
        self.safe_addstr(self.h // 2, max(1, self.w // 2 - len(score_line) // 2), score_line, self.color_attr(8))
        if self.top_scores:
            leader = self.top_scores[0]
            leader_line = f"Top: {leader['name']} {leader['score']}"
            self.safe_addstr(self.h // 2 + 1, max(1, self.w // 2 - len(leader_line) // 2), leader_line, self.color_attr(2))
        self.safe_addstr(self.h // 2 + 2, max(1, self.w // 2 - len(hint) // 2), hint, self.color_attr(2))
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
    game.show_top10_intro(3.0)
    game.intro_screen()
    game.draw_board()
    game.loop()
    game.game_over_screen()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Terminal Tetris clone")
    parser.parse_args()
    try:
        curses.wrapper(run)
    except KeyboardInterrupt:
        pass
