# TAME

```text
 _____   _   __  __  _____
|_   _| / \ |  \/  || ____|
  | |  / _ \| |\/| ||  _|
  |_| /_/ \_\_|  |_||_____|
```

Terminal Arcade Multiple Emulator.

TAME is a terminal-first arcade launcher for the local cabinet set:
- Galga
- Defender
- Tetris
- Centipede

## Run
```bash
git clone https://github.com/beed2112/TAME.git
cd TAME
cd arcade
./run.sh
```

## Controls
- Arrow keys: move between cabinets
- `1`, `2`, `3`, `4`: jump directly to a game
- `Enter` or `Space`: launch the selected game
- `Q`: quit the launcher

## Behavior
- The launcher returns to the menu after a game exits.
- The lower window includes a moving ASCII `TAME` marquee.
- Cabinet cards show the game art, minimum terminal size, and core controls.

## Requirements
- Use a terminal at least `84x28` for TAME.
- Individual cabinets may require more space.
- Defender still needs the largest game window at `80x26`.
