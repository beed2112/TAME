# Breakout Console

Terminal Breakout built with Python `curses`.

## Controls
- Left / Right: move paddle
- `A` / `D`: move paddle
- `Space` or `Enter`: launch ball / continue
- `Esc` or `P`: pause / unpause
- `Q`: quit

## Features
- Eight-row brick wall with original color scoring bands
- Three lives and progressive wave resets
- Paddle-controlled bounce angles
- Deliberate ball-speed ramp that stays readable in the terminal
- Persistent top-10 score table in `~/.breakout_console`

## Install
```bash
cd <CLONELOC>/TAME/breakout/breakoutconsole
./install.sh
```

## Run
```bash
cd <CLONELOC>/TAME/breakout/breakoutconsole
./run.sh
```

## Notes
- Requires terminal size at least `84x30`.
- Uses Python standard library only.
