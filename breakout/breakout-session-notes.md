# Breakout Session Notes

This document tracks the working conversation for the TAME Breakout cabinet: user feedback, implementation decisions, and changes made during the session. It is intended to be updated as the work continues.

## Session Summary

Goal: create a Breakout cabinet for TAME in the same spirit and structure as the other terminal arcade games.

Current status:
- Breakout has been added as a new TAME cabinet.
- The game follows the existing per-cabinet pattern with its own console directory, launch scripts, install script, and README.
- The launcher and project documentation were updated to include Breakout.
- Gameplay tuning has already been adjusted based on user feedback.

## Conversation Log

### 1. Initial request

User feedback:
- Create a Breakout game for the cabinet.
- Refer to the `breakout` folder and match the style of the other games.

Actions taken:
- Reviewed `breakout/breakout.md` for gameplay notes and constraints.
- Reviewed the existing TAME launcher and cabinet implementations to match project structure and behavior.
- Implemented a new Breakout cabinet under `breakout/breakoutconsole/`.
- Added:
  - `breakout/breakoutconsole/breakout_terminal.py`
  - `breakout/breakoutconsole/run.sh`
  - `breakout/breakoutconsole/install.sh`
  - `breakout/breakoutconsole/README.md`
- Registered Breakout in the launcher.
- Updated top-level docs and cabinet slide content to include Breakout.

Implementation summary:
- Built a curses-based Breakout game.
- Added persistent top-10 score handling in `~/.breakout_console`.
- Used a centered playfield with side HUD.
- Kept the brick wall edge-to-edge within the playfield.
- Left two empty rows above the brick wall.
- Added paddle shrink behavior after breaking through the red row and touching the ceiling.
- Added wave reset behavior when the wall is cleared.

### 2. Gameplay tuning request

User feedback:
- Paddle needs to move faster.
- Reduce return speed of the ball by 25%.
- Increase game field width and height by 25%.

Actions taken:
- Increased paddle speed.
- Reduced base ball speed, max ball speed, and speed ramp increments by 25%.
- Increased playfield size by 25% in both width and height.

Implementation details:
- `PLAYFIELD_WIDTH`: `32` -> `40`
- `PLAYFIELD_HEIGHT`: `24` -> `30`
- `PADDLE_SPEED`: `44.0` -> `56.0`
- `BALL_START_SPEED`: `13.5` -> `10.125`
- `BALL_MAX_SPEED`: `19.0` -> `14.25`
- Level speed growth and bounce-triggered speed increases were reduced proportionally.

### 3. Brick wall width correction

User feedback:
- The playing field was expanded.
- The blocks should go edge to edge.

Actions taken:
- Expanded the brick rack to match the widened playfield instead of keeping the original narrower wall.

Implementation details:
- `BRICK_COLS`: `16` -> `20`
- With two-character bricks, the wall now spans the full `40`-column playfield width.

### 4. High score logic requirement

User feedback:
- We should include the standard TAME high score logic.
- Persistent score handling is expected across all cabinet games.

Actions taken:
- Reviewed the Breakout cabinet score flow against the existing cabinet standard.
- Confirmed the standard logic is already present in the Breakout implementation.
- Recorded the requirement here so it remains part of the ongoing session baseline.

Implementation summary:
- Breakout loads persistent score data from `~/.breakout_console`.
- Breakout tracks `high_score`, `games_played`, and a persistent top-10 table.
- Qualifying scores prompt for a player name before saving.
- The score file is written back at game over, matching the existing cabinet pattern.

### 5. Paddle collision reliability

User feedback:
- There are times when the ball seems to go through the paddle.

Actions taken:
- Tightened the downward paddle collision check to use the ball's crossing point at the paddle row instead of relying only on the next-step position.
- Added a wider paddle contact tolerance and resolved the bounce from the exact crossing location before continuing movement.

Implementation summary:
- The paddle collision now checks whether the ball segment crosses the paddle row during the frame.
- The bounce uses the interpolated `crossing_x` contact point, which reduces tunneling on faster downward motion.
- Missed-ball handling now happens only after the paddle-crossing test fails.

### 6. Small paddle movement speed

User feedback:
- When the paddle is small, it still needs to move fast.

Actions taken:
- Added a separate movement speed for the shrunk paddle state so post-shrink control stays aggressive.

Implementation summary:
- Normal paddle movement still uses the base speed.
- Shrunk paddle movement now uses a higher speed value to offset the reduced paddle width.
- This keeps the late-wave control feel aligned with the cabinet standard of responsive movement.

## Files Touched So Far

- [breakout_terminal.py](/home/beed2112/gitspace/TAME/breakout/breakoutconsole/breakout_terminal.py:1)
- [run.sh](/home/beed2112/gitspace/TAME/breakout/breakoutconsole/run.sh:1)
- [install.sh](/home/beed2112/gitspace/TAME/breakout/breakoutconsole/install.sh:1)
- [README.md](/home/beed2112/gitspace/TAME/breakout/breakoutconsole/README.md:1)
- [arcade_launcher.py](/home/beed2112/gitspace/TAME/arcade/arcade_launcher.py:46)
- [README.md](/home/beed2112/gitspace/TAME/README.md:13)
- [tame-game-cabinet.retro.html](/home/beed2112/gitspace/TAME/tame-game-cabinet.retro.html:67)

## Verification So Far

- `python3 -m py_compile breakout/breakoutconsole/breakout_terminal.py`
- `python3 -m py_compile breakout/breakoutconsole/breakout_terminal.py arcade/arcade_launcher.py`

## Update Rule

As new feedback arrives, append:
- the user request or gameplay note
- the code or design changes made in response
- any verification performed
