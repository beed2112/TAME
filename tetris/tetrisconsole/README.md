# Tetris Console

Terminal Tetris built with Python `curses`.

## Controls
- Left / Right: move
- Down: soft drop
- Up or `X`: rotate clockwise
- `Z` or `C`: rotate counter-clockwise
- `Space`: hard drop
- `H` or `V`: hold piece
- `Esc`: pause / unpause
- `Q`: quit

## Features
- Endless mode
- Seven-bag randomizer
- Ghost piece
- Hold piece
- Five-piece next queue
- Soft and hard drop scoring
- Level increases every 10 cleared lines
- Wall-kick rotation behavior

## Install
```bash
cd <CLONELOC>/TAME/tetris/tetrisconsole
./install.sh
```

## Run
```bash
cd <CLONELOC>/TAME/tetris/tetrisconsole
./run.sh
```

## Notes
- Requires terminal size at least `74x28`.
- Uses Python standard library only.
- High score is stored in `~/.tetris_console`.
