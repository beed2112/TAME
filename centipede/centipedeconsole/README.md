# Centipede Console

Terminal Centipede-style fixed shooter built with Python `curses`.

## Controls
- Arrow keys or `WASD`: move inside the lower player zone
- `Space`: fire
- `Esc`: pause / unpause
- `Q`: quit

## Features
- Splitting centipedes with independent heads
- Mushroom damage and poisoned mushrooms
- Spider, flea, and scorpion hazards
- Wave progression and score persistence

## Install
```bash
cd /home/beed2112/chatgptspace/centipede/centipedeconsole
./install.sh
```

## Run
```bash
cd /home/beed2112/chatgptspace/centipede/centipedeconsole
./run.sh
```

## Notes
- Requires terminal size at least `78x30`.
- Playfield expands to use most of the available terminal window.
- Uses Python standard library only.
- High score is stored in `~/.centipede_console`.
