# Asteroids Console

Terminal Asteroids built with Python `curses`.

## Controls
- Left / Right: rotate ship
- Up or `W`: thrust
- Space: fire
- `H`: hyperspace
- `Esc` or `P`: pause / unpause
- `Q`: quit

## Features
- Rotating ship with inertia-based propulsion
- Wraparound playfield
- Large, medium, and small asteroid splitting
- Enemy saucer fly-bys with return fire
- Persistent top-10 score table in `~/.asteroids_console`

## Install
```bash
cd <CLONELOC>/TAME/asteroids/asteroidsconsole
./install.sh
```

## Run
```bash
cd <CLONELOC>/TAME/asteroids/asteroidsconsole
./run.sh
```

## Notes
- Requires terminal size at least `80x26`.
- Uses Python standard library only.
