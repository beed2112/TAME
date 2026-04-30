# Defender Console

Terminal Defender-style game built with Python `curses`.

## Controls
- Right / `D`: thrust in the current facing direction
- Left / `A`: reverse thrust and flip direction
- Up / `W`: move up
- Down / `S`: move down
- `Space`: fire
- `B`: smart bomb for the current visible area
- `H`: hyperspace jump
- `Esc`: pause / unpause
- `Q`: quit

## Install
```bash
cd /home/beed2112/chatgptspace/defender/defenderconsole
./install.sh
```

## Run
```bash
cd /home/beed2112/chatgptspace/defender/defenderconsole
./run.sh
```

## Notes
- Requires terminal size at least `80x26`.
- Uses Python standard library only.
- Score data is stored in `~/.defender_console`.
- Includes landers, mutants, bombers, baiters, motherships, swarmers, falling-human catches, and return-to-ground bonuses.
