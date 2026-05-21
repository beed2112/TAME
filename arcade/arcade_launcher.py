#!/usr/bin/env python3
import curses
import math
import random
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path


FRAME_SECONDS = 0.05
MIN_WIDTH = 84
MIN_HEIGHT = 28
STAR_COUNT = 152
SPLASH_SECONDS = 5
TAME_ART = (
    " _____   _   __  __  _____ ",
    "|_   _| / \\ |  \\/  || ____|",
    "  | |  / _ \\| |\\/| ||  _|  ",
    "  |_| /_/ \\_\\_|  |_||_____|",
)


@dataclass(frozen=True)
class Cabinet:
    key: str
    title: str
    subtitle: str
    path: Path
    min_size: str
    accent_pair: int
    art: tuple[str, ...]
    controls: tuple[str, ...]


@dataclass
class Star:
    x: float
    y: int
    speed: float
    glyph: str
    color_pair: int


ROOT = Path(__file__).resolve().parents[1]
GAMES = (
    Cabinet(
        key="1",
        title="GALGA",
        subtitle="FORMATION ASSAULT",
        path=ROOT / "galaga" / "galgaconsole" / "run.sh",
        min_size="55x22",
        accent_pair=3,
        art=(
            "   \\/  \\/  \\/   ",
            "  <V> <V> <V>   ",
            "    \\\\ || //     ",
            "      _/\\_       ",
            "     /_==_\\\\      ",
        ),
        controls=("MOVE: LEFT RIGHT", "FIRE: SPACE", "PAUSE: ESC", "QUIT: Q"),
    ),
    Cabinet(
        key="2",
        title="DEFENDER",
        subtitle="SAVE THE LAST HUMANS",
        path=ROOT / "defender" / "defenderconsole" / "run.sh",
        min_size="80x26",
        accent_pair=5,
        art=(
            "     .       .    ",
            "  .       .       ",
            "    <A==>         ",
            " _/|_     o   _/|_",
            "/____\\___/ \\_/____",
        ),
        controls=("THRUST: A D", "ALTITUDE: W S", "FIRE: SPACE", "BOMB/HYPER: B H"),
    ),
    Cabinet(
        key="3",
        title="TETRIS",
        subtitle="STACK UNDER PRESSURE",
        path=ROOT / "tetris" / "tetrisconsole" / "run.sh",
        min_size="74x28",
        accent_pair=4,
        art=(
            " [][]    [][][]   ",
            " [][]      [][]   ",
            "[][][]   [][][][] ",
            "  [][]   [][]     ",
            "[][][]   [][][]   ",
        ),
        controls=("MOVE: ARROWS", "ROTATE: UP X Z C", "DROP: SPACE DOWN", "HOLD: H V"),
    ),
    Cabinet(
        key="4",
        title="CENTIPEDE",
        subtitle="MUSHROOM FIELD LOCKDOWN",
        path=ROOT / "centipede" / "centipedeconsole" / "run.sh",
        min_size="78x30",
        accent_pair=6,
        art=(
            "  M   M   M   M   ",
            " Qooooooooooo     ",
            "      |           ",
            "   M      W    S  ",
            "        A         ",
        ),
        controls=("MOVE: ARROWS WASD", "FIRE: SPACE", "PAUSE: ESC", "QUIT: Q"),
    ),
    Cabinet(
        key="5",
        title="BREAKOUT",
        subtitle="SHATTER THE WALL",
        path=ROOT / "breakout" / "breakoutconsole" / "run.sh",
        min_size="84x30",
        accent_pair=2,
        art=(
            "[][][][][][][][][]",
            "[][][][][][][][][]",
            "     o            ",
            "                  ",
            "      =======     ",
        ),
        controls=("MOVE: LEFT RIGHT", "MOVE: A D", "SERVE: SPACE ENTER", "PAUSE: ESC"),
    ),
    Cabinet(
        key="6",
        title="ASTEROIDS",
        subtitle="VECTOR FIELD SURVIVAL",
        path=ROOT / "asteroids" / "asteroidsconsole" / "run.sh",
        min_size="80x26",
        accent_pair=1,
        art=(
            "    ##      ##    ",
            "  ### ##  ## ###  ",
            "      >>>>>>      ",
            "        >>>       ",
            "      *           ",
        ),
        controls=("TURN: LEFT RIGHT", "THRUST: UP W", "FIRE: SPACE", "HYPER: H"),
    ),
)


class Launcher:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.h = 0
        self.w = 0
        self.selected = 0
        self.running = True
        self.use_colors = False
        self.stars: list[Star] = []
        self.status_text = "SELECT A CABINET"
        self.status_until = 0.0
        self.splash_active = True
        self.splash_started = time.monotonic()

    def setup(self):
        try:
            curses.curs_set(0)
        except curses.error:
            pass
        self.stdscr.nodelay(True)
        self.stdscr.keypad(True)
        self.stdscr.timeout(0)
        if curses.has_colors():
            curses.start_color()
            curses.use_default_colors()
            curses.init_pair(1, curses.COLOR_WHITE, -1)
            curses.init_pair(2, curses.COLOR_MAGENTA, -1)
            curses.init_pair(3, curses.COLOR_CYAN, -1)
            curses.init_pair(4, curses.COLOR_YELLOW, -1)
            curses.init_pair(5, curses.COLOR_GREEN, -1)
            curses.init_pair(6, curses.COLOR_RED, -1)
            curses.init_pair(7, curses.COLOR_BLUE, -1)
            self.use_colors = True
        self.refresh_size()
        self.reset_stars()

    def refresh_size(self):
        self.h, self.w = self.stdscr.getmaxyx()

    def color(self, pair_id):
        return curses.color_pair(pair_id) if self.use_colors else 0

    def reset_stars(self):
        self.stars = []
        spawn_bottom = max(8, self.h - 8)
        for _ in range(STAR_COUNT):
            self.stars.append(
                Star(
                    x=random.uniform(0, max(1, self.w - 2)),
                    y=random.randint(1, spawn_bottom),
                    speed=random.uniform(0.08, 0.35),
                    glyph=random.choice([".", ".", "+", "*"]),
                    color_pair=random.choice([1, 3, 4, 5]),
                )
            )

    def put(self, y, x, text, attr=0):
        if y < 0 or y >= self.h or x >= self.w:
            return
        try:
            self.stdscr.addnstr(y, max(0, x), text, max(0, self.w - max(0, x)), attr)
        except curses.error:
            pass

    def center(self, y, text, attr=0):
        x = max(0, (self.w - len(text)) // 2)
        self.put(y, x, text, attr)

    def flash_status(self, text, duration=2.2):
        self.status_text = text
        self.status_until = time.monotonic() + duration

    def current_status(self):
        if self.status_until and time.monotonic() <= self.status_until:
            return self.status_text
        return "SELECT A CABINET"

    def run(self):
        while self.running:
            started = time.monotonic()
            self.handle_input()
            self.update()
            self.draw()
            elapsed = time.monotonic() - started
            if elapsed < FRAME_SECONDS:
                time.sleep(FRAME_SECONDS - elapsed)

    def handle_input(self):
        while True:
            key = self.stdscr.getch()
            if key == -1:
                return
            if key in (ord("q"), ord("Q")):
                self.running = False
                return
            if self.splash_active:
                self.splash_active = False
                self.flash_status("SELECT A CABINET", duration=1.4)
                if key == curses.KEY_RESIZE:
                    self.refresh_size()
                    self.reset_stars()
                return
            if key in (curses.KEY_LEFT, curses.KEY_UP):
                self.selected = (self.selected - 1) % len(GAMES)
            elif key in (curses.KEY_RIGHT, curses.KEY_DOWN, ord("\t")):
                self.selected = (self.selected + 1) % len(GAMES)
            elif key in (10, 13, curses.KEY_ENTER):
                self.launch_game(GAMES[self.selected])
            elif key in tuple(ord(str(index)) for index in range(1, len(GAMES) + 1)):
                self.selected = int(chr(key)) - 1
            elif key in (ord(" "),):
                self.launch_game(GAMES[self.selected])
            elif key == curses.KEY_RESIZE:
                self.refresh_size()
                self.reset_stars()

    def update(self):
        self.refresh_size()
        if self.splash_active and time.monotonic() - self.splash_started >= SPLASH_SECONDS:
            self.splash_active = False
        spawn_bottom = max(6, self.h - 8)
        for star in self.stars:
            star.x -= star.speed
            if star.x < 1:
                star.x = max(2, self.w - 3)
                star.y = random.randint(1, spawn_bottom)
                star.speed = random.uniform(0.08, 0.35)
                star.glyph = random.choice([".", ".", "+", "*"])
                star.color_pair = random.choice([1, 3, 4, 5])

    def draw(self):
        self.stdscr.erase()
        if self.h < MIN_HEIGHT or self.w < MIN_WIDTH:
            self.draw_size_warning()
            self.stdscr.refresh()
            return
        self.draw_border()
        self.draw_stars()
        self.draw_floor()
        if self.splash_active:
            self.draw_splash()
        else:
            self.draw_marquee()
            self.draw_selector_strip()
            self.draw_cabinet()
            self.draw_tame_banner()
            self.draw_footer()
        self.stdscr.refresh()

    def draw_size_warning(self):
        self.center(max(1, self.h // 2 - 1), "TERMINAL TOO SMALL", self.color(6) | curses.A_BOLD)
        self.center(self.h // 2 + 1, f"Need at least {MIN_WIDTH}x{MIN_HEIGHT} for the launcher", self.color(1))
        self.center(self.h // 2 + 3, "Resize the terminal, then press any launcher key.", self.color(1))

    def draw_border(self):
        self.stdscr.border()
        tick = int(time.monotonic() * 8)
        bulbs = [2, 3, 4, 5, 6]
        for x in range(2, self.w - 2, 4):
            pair = bulbs[(x // 4 + tick) % len(bulbs)]
            self.put(0, x, "o", self.color(pair) | curses.A_BOLD)
            self.put(self.h - 1, x, "o", self.color(pair) | curses.A_BOLD)
        for y in range(2, self.h - 2, 3):
            pair = bulbs[(y + tick) % len(bulbs)]
            self.put(y, 0, "o", self.color(pair) | curses.A_BOLD)
            self.put(y, self.w - 1, "o", self.color(pair) | curses.A_BOLD)

    def draw_stars(self):
        top_limit = max(4, self.h - 8)
        for star in self.stars:
            if 1 <= star.y < top_limit:
                self.put(star.y, int(star.x), star.glyph, self.color(star.color_pair))

    def draw_marquee(self):
        box_width = min(self.w - 10, 52)
        left = max(3, (self.w - box_width) // 2)
        right = left + box_width - 1
        top = 2
        self.put(top, left, "+" + "-" * (box_width - 2) + "+", self.color(4))
        self.put(top + 1, left, "|" + " " * (box_width - 2) + "|", self.color(4))
        self.put(top + 2, left, "|" + " " * (box_width - 2) + "|", self.color(4))
        self.put(top + 3, left, "+" + "-" * (box_width - 2) + "+", self.color(4))
        self.center(top + 1, "TAME", self.color(4) | curses.A_BOLD)
        self.center(top + 2, "Arrow keys move   Enter launches   Q exits", self.color(1))
        self.put(top + 1, left + 2, "[=]", self.color(6) | curses.A_BOLD)
        self.put(top + 1, right - 4, "[=]", self.color(6) | curses.A_BOLD)

    def draw_splash(self):
        elapsed = time.monotonic() - self.splash_started
        art_width = len(TAME_ART[0])
        final_left = max(2, (self.w - art_width) // 2)
        intro_progress = min(1.0, elapsed / 1.25)
        eased = 1.0 - ((1.0 - intro_progress) ** 3)
        start_left = -art_width
        art_left = int(start_left + ((final_left - start_left) * eased))
        wobble = int(round(math.sin(elapsed * 9.5) * (1.0 - intro_progress) * 2.5))
        art_top = max(4, self.h // 2 - 8 + wobble)
        spinner_frames = ("|", "/", "-", "\\")
        spinner = spinner_frames[int(elapsed * 14) % len(spinner_frames)]
        colors = [4, 6, 3, 5]
        for idx, line in enumerate(TAME_ART):
            self.put(art_top + idx, art_left, line, self.color(colors[idx]) | curses.A_BOLD)

        orbit_y = art_top + 1
        self.put(orbit_y, max(2, art_left - 4), f"<{spinner}>", self.color(3) | curses.A_BOLD)
        self.put(orbit_y, min(self.w - 5, art_left + art_width + 1), f"<{spinner}>", self.color(6) | curses.A_BOLD)

        pulse_attr = self.color(1) | (curses.A_BOLD if int(elapsed * 4) % 2 == 0 else 0)
        self.center(art_top + len(TAME_ART) + 2, "Terminal Arcade Multiple Emulator", pulse_attr)
        self.center(art_top + len(TAME_ART) + 4, "Galga   Defender   Tetris   Centipede   Breakout   Asteroids", self.color(4))
        self.center(art_top + len(TAME_ART) + 6, "Press any key to enter the cabinet selector", self.color(6) | curses.A_BOLD)
        self.center(art_top + len(TAME_ART) + 7, "Q exits", self.color(1))

    def draw_selector_strip(self):
        y = 7
        labels = [f" {cabinet.key}. {cabinet.title} " for cabinet in GAMES]
        total_width = sum(len(label) for label in labels) + (2 * (len(labels) - 1))
        x = max(2, (self.w - total_width) // 2)
        cursor = x
        for index, cabinet in enumerate(GAMES):
            selected = index == self.selected
            label = labels[index]
            attr = self.color(cabinet.accent_pair)
            if selected:
                attr |= curses.A_BOLD | curses.A_REVERSE
            self.put(y, cursor, label, attr)
            cursor += len(label) + 2

    def draw_cabinet(self):
        cabinet = GAMES[self.selected]
        box_width = min(self.w - 12, 62)
        box_height = 13
        left = (self.w - box_width) // 2
        top = 9
        accent = self.color(cabinet.accent_pair) | curses.A_BOLD

        self.put(top, left, "." + "-" * (box_width - 2) + ".", accent)
        for row in range(1, box_height - 1):
            self.put(top + row, left, "|", accent)
            self.put(top + row, left + box_width - 1, "|", accent)
            self.put(top + row, left + 1, " " * (box_width - 2))
        self.put(top + box_height - 1, left, "'" + "-" * (box_width - 2) + "'", accent)

        self.center(top + 1, cabinet.title, accent)
        self.center(top + 2, cabinet.subtitle, self.color(1) | curses.A_BOLD)

        art_left = left + 4
        for offset, line in enumerate(cabinet.art):
            self.put(top + 4 + offset, art_left, line, accent)

        detail_left = left + box_width // 2 + 1
        self.put(top + 4, detail_left, "READY LIGHTS", self.color(1) | curses.A_BOLD)
        self.put(top + 5, detail_left, f"MIN SIZE  {cabinet.min_size}", self.color(1))
        self.put(top + 6, detail_left, "CONTROLS", self.color(1) | curses.A_BOLD)
        for idx, line in enumerate(cabinet.controls[:4]):
            self.put(top + 7 + idx, detail_left, line, self.color(1))

        self.draw_side_titles(top + 5)

    def draw_side_titles(self, y):
        left_game = GAMES[(self.selected - 1) % len(GAMES)]
        right_game = GAMES[(self.selected + 1) % len(GAMES)]
        self.put(y, 4, f"< {left_game.title}", self.color(left_game.accent_pair))
        right_label = f"{right_game.title} >"
        self.put(y, self.w - len(right_label) - 4, right_label, self.color(right_game.accent_pair))

    def draw_floor(self):
        start = self.h - 9
        if start <= 0:
            return
        horizon_left = self.w // 2
        floor_bottom = self.h - 6
        for row in range(start, floor_bottom):
            depth = row - start + 1
            spread = depth * 4
            left = max(2, horizon_left - spread)
            right = min(self.w - 3, horizon_left + spread)
            line = [" "] * max(0, right - left + 1)
            for idx in range(len(line)):
                absolute_x = left + idx
                if idx == 0 or idx == len(line) - 1:
                    line[idx] = "/"
                elif (absolute_x - horizon_left) % max(4, depth + 2) == 0:
                    line[idx] = "|"
                elif row == floor_bottom - 1 or idx % 6 == 0:
                    line[idx] = "_"
            self.put(row, left, "".join(line), self.color(7))

    def draw_tame_banner(self):
        art_width = len(TAME_ART[0])
        travel = max(1, self.w - art_width - 4)
        phase = int(time.monotonic() * 8)
        loop = travel * 2
        position = phase % loop
        if position >= travel:
            position = loop - position
        left = 2 + position
        top = self.h - len(TAME_ART) - 1
        colors = [4, 6, 3, 5]
        for idx, line in enumerate(TAME_ART):
            self.put(top + idx, left, line, self.color(colors[idx]) | curses.A_BOLD)

    def draw_footer(self):
        status = self.current_status()
        self.center(self.h - 8, status, self.color(6) | curses.A_BOLD)
        self.center(self.h - 7, "1-6 jump directly   Space also launches   After a game exits, you return here", self.color(1))

    def launch_game(self, cabinet):
        if not cabinet.path.exists():
            self.flash_status(f"MISSING: {cabinet.path}", duration=3.5)
            return

        self.flash_status(f"BOOTING {cabinet.title}...", duration=1.5)
        self.draw()
        curses.doupdate()

        result = None
        error_text = None
        try:
            curses.def_prog_mode()
            curses.endwin()
            result = subprocess.run(["bash", str(cabinet.path)], cwd=str(cabinet.path.parent), check=False)
        except Exception as exc:  # pragma: no cover - interactive fallback
            error_text = str(exc)
        finally:
            curses.reset_prog_mode()
            self.stdscr.refresh()
            self.stdscr.nodelay(True)
            self.stdscr.keypad(True)
            self.stdscr.timeout(0)
            try:
                curses.curs_set(0)
            except curses.error:
                pass
            curses.flushinp()
            self.refresh_size()
            self.reset_stars()

        if error_text:
            self.flash_status(f"LAUNCH FAILED: {error_text[:42]}", duration=4.0)
        elif result and result.returncode != 0:
            self.flash_status(f"{cabinet.title} exited with code {result.returncode}", duration=3.0)
        else:
            self.flash_status(f"{cabinet.title} complete. Pick the next cabinet.", duration=2.5)


def main(stdscr):
    launcher = Launcher(stdscr)
    launcher.setup()
    launcher.run()


if __name__ == "__main__":
    curses.wrapper(main)
