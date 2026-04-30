#!/usr/bin/env python3
import curses
import random
import time
from dataclasses import dataclass


TICK_SECONDS = 0.04
PLAYER_COOLDOWN = 0.16
ENEMY_FIRE_CHANCE = 0.015
ENEMY_STEP_TIME = 0.5
ENEMY_DROP_ROWS = 1


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
    alive: bool = True


class Game:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.h = 0
        self.w = 0
        self.player_x = 0
        self.player_y = 0
        self.player_lives = 3
        self.score = 0
        self.level = 1
        self.last_shot = 0.0
        self.last_enemy_step = 0.0
        self.enemy_dir = 1
        self.enemies = []
        self.bullets = []
        self.running = True
        self.win = False

    def setup(self):
        curses.curs_set(0)
        self.stdscr.nodelay(True)
        self.stdscr.keypad(True)
        self.stdscr.timeout(0)
        self.h, self.w = self.stdscr.getmaxyx()
        if self.h < 18 or self.w < 45:
            raise RuntimeError("Terminal too small. Need at least 45x18.")
        self.player_x = self.w // 2
        self.player_y = self.h - 2
        self.spawn_enemies()

    def spawn_enemies(self):
        self.enemies = []
        rows = min(6, 2 + self.level)
        cols = 10
        x_start = max(3, (self.w - (cols * 4)) // 2)
        y_start = 2
        for r in range(rows):
            for c in range(cols):
                self.enemies.append(Enemy(x=x_start + c * 4, y=y_start + r * 2))
        self.enemy_dir = 1

    def draw(self):
        self.stdscr.erase()
        hud = f" SCORE: {self.score}   LIVES: {self.player_lives}   LEVEL: {self.level}   Q:QUIT "
        self.stdscr.addstr(0, 0, hud[: self.w - 1])
        self.stdscr.hline(1, 0, ord("="), self.w - 1)

        for e in self.enemies:
            if e.alive and 0 < e.y < self.h - 1 and 0 < e.x < self.w - 1:
                self.stdscr.addch(e.y, e.x, "W")

        for b in self.bullets:
            if 0 < b.y < self.h - 1 and 0 < b.x < self.w - 1:
                self.stdscr.addch(b.y, b.x, "|" if b.dy < 0 else "!")

        if 0 < self.player_y < self.h and 0 < self.player_x < self.w - 1:
            self.stdscr.addch(self.player_y, self.player_x, "A")

        self.stdscr.refresh()

    def handle_input(self):
        key = self.stdscr.getch()
        while key != -1:
            if key in (ord("q"), ord("Q")):
                self.running = False
                return
            if key == curses.KEY_LEFT:
                self.player_x = max(1, self.player_x - 1)
            elif key == curses.KEY_RIGHT:
                self.player_x = min(self.w - 2, self.player_x + 1)
            elif key == ord(" "):
                now = time.monotonic()
                if now - self.last_shot >= PLAYER_COOLDOWN:
                    self.bullets.append(Bullet(self.player_x, self.player_y - 1, -1, False))
                    self.last_shot = now
            key = self.stdscr.getch()

    def move_enemies(self):
        now = time.monotonic()
        if now - self.last_enemy_step < max(0.10, ENEMY_STEP_TIME - (self.level * 0.03)):
            return
        self.last_enemy_step = now

        living = [e for e in self.enemies if e.alive]
        if not living:
            self.level += 1
            self.spawn_enemies()
            return

        min_x = min(e.x for e in living)
        max_x = max(e.x for e in living)
        hit_side = (self.enemy_dir == 1 and max_x >= self.w - 2) or (
            self.enemy_dir == -1 and min_x <= 1
        )

        if hit_side:
            self.enemy_dir *= -1
            for e in living:
                e.y += ENEMY_DROP_ROWS
                if e.y >= self.player_y:
                    self.player_lives = 0
        else:
            for e in living:
                e.x += self.enemy_dir

        for e in living:
            if random.random() < ENEMY_FIRE_CHANCE + (self.level * 0.002):
                self.bullets.append(Bullet(e.x, e.y + 1, 1, True))

    def move_bullets(self):
        for b in self.bullets:
            b.y += b.dy
        self.bullets = [b for b in self.bullets if 1 < b.y < self.h - 1]

    def collisions(self):
        enemy_map = {(e.x, e.y): e for e in self.enemies if e.alive}
        remaining = []
        for b in self.bullets:
            if not b.from_enemy:
                hit = enemy_map.get((b.x, b.y))
                if hit:
                    hit.alive = False
                    self.score += 10
                    continue
            remaining.append(b)
        self.bullets = remaining

        remaining = []
        for b in self.bullets:
            if b.from_enemy and b.y == self.player_y and b.x == self.player_x:
                self.player_lives -= 1
                continue
            remaining.append(b)
        self.bullets = remaining

        if self.player_lives <= 0:
            self.running = False
            self.win = False

    def loop(self):
        self.last_enemy_step = time.monotonic()
        while self.running:
            self.handle_input()
            self.move_enemies()
            self.move_bullets()
            self.collisions()
            living = [e for e in self.enemies if e.alive]
            if not living and self.level >= 5:
                self.running = False
                self.win = True
            self.draw()
            time.sleep(TICK_SECONDS)

    def game_over_screen(self):
        self.stdscr.nodelay(False)
        self.stdscr.erase()
        msg = "YOU WIN!" if self.win else "GAME OVER"
        self.stdscr.addstr(self.h // 2 - 1, max(1, self.w // 2 - len(msg) // 2), msg)
        score_line = f"Final score: {self.score}"
        self.stdscr.addstr(self.h // 2, max(1, self.w // 2 - len(score_line) // 2), score_line)
        hint = "Press any key to exit"
        self.stdscr.addstr(self.h // 2 + 2, max(1, self.w // 2 - len(hint) // 2), hint)
        self.stdscr.refresh()
        self.stdscr.getch()


def run(stdscr):
    game = Game(stdscr)
    try:
        game.setup()
    except RuntimeError as e:
        stdscr.nodelay(False)
        stdscr.erase()
        stdscr.addstr(0, 0, str(e))
        stdscr.addstr(2, 0, "Resize the terminal and try again.")
        stdscr.refresh()
        stdscr.getch()
        return
    game.draw()
    game.loop()
    game.game_over_screen()


if __name__ == "__main__":
    curses.wrapper(run)
