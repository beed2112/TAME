# TAME Game Cabinet

## Overview

### What TAME Is

1. Terminal Arcade Multiple Emulator

- Terminal-first arcade launcher for a local cabinet set
- Built around lightweight Python `curses` games
- Current cabinets: Galga, Defender, Tetris, Centipede
- Designed to return to the launcher after each game exits

:::info
TAME is positioned as a self-contained terminal arcade experience, not a general emulator frontend.
:::

### Launch Sequence

1. Clone and enter the project

- `git clone https://github.com/beed2112/TAME.git`
- `cd TAME`
- `cd arcade`

2. Start the cabinet launcher

- Run `./run.sh`
- Use a terminal sized at least `84x28`
- Expect the launcher menu to remain available after a game closes

```bash
git clone https://github.com/beed2112/TAME.git
cd TAME/arcade
./run.sh
```

:::warning
The global launcher fits in `84x28`, but some cabinets need more room. Defender is the tightest at `80x26`.
:::

### Cabinet Navigation

1. Move around the launcher

- Arrow keys move between cabinets
- `1`, `2`, `3`, `4` jump directly to a cabinet
- `Enter` or `Space` launches the selected game
- `Q` exits the launcher

2. Read cabinet status at a glance

- Cabinet cards show title and subtitle
- Each card includes minimum terminal size
- Core controls are visible before launch
- A moving ASCII `TAME` marquee stays active in the lower window

## Cabinets

### Galga

1. Cabinet role

- Fast formation shooter
- Smallest runtime footprint in the set
- Python standard library only

2. Controls

- Move: Left Arrow, Right Arrow
- Fire: `Space`
- Pause: `Esc`
- Quit: `Q`

3. Runtime notes

- Launch path: `TAME/galaga/galgaconsole/run.sh`
- Minimum size: `55x22`

### Defender

1. Cabinet role

- Most complex control scheme in the set
- Horizontal survival and rescue gameplay
- Includes multiple enemy types and human rescue flow

2. Controls

- Thrust: Right or `D`
- Reverse thrust / flip: Left or `A`
- Altitude: Up or `W`, Down or `S`
- Fire: `Space`
- Smart bomb: `B`
- Hyperspace: `H`
- Pause/Quit: `Esc`, `Q`

3. Runtime notes

- Launch path: `TAME/defender/defenderconsole/run.sh`
- Minimum size: `80x26`
- Score data stored in `~/.defender_console`

:::danger
Defender has the highest screen and control overhead. It should be the baseline when validating cabinet host terminal size.
:::

### Tetris

1. Cabinet role

- Endless stack-management cabinet
- Most feature-rich ruleset in the set
- Good default demonstration cabinet for new users

2. Controls

- Move: Left, Right
- Soft drop: Down
- Rotate clockwise: Up or `X`
- Rotate counter-clockwise: `Z` or `C`
- Hard drop: `Space`
- Hold piece: `H` or `V`

3. Runtime notes

- Features: seven-bag randomizer, ghost piece, hold, five-piece queue
- Minimum size: `74x28`
- High score stored in `~/.tetris_console`

### Centipede

1. Cabinet role

- Fixed shooter with expanding playfield usage
- Strong arcade feel with mushroom and hazard interactions
- Supports wave progression and persistent scoring

2. Controls

- Move: Arrow keys or `WASD`
- Fire: `Space`
- Pause: `Esc`
- Quit: `Q`

3. Runtime notes

- Features: splitting centipedes, spider, flea, scorpion hazards
- Minimum size: `78x30`
- High score stored in `~/.centipede_console`

## Operations

### Install and Runtime Expectations

1. Environment assumptions

- Linux terminal environment
- Python `curses` available
- No pip dependencies required for the included cabinets

2. Operational behavior

- Cabinet launcher returns to menu after each game exits
- Individual games are started via their own `run.sh`
- Install steps are available per cabinet via local `install.sh`

```bash
cd TAME/<cabinet>/<console-dir>
./install.sh
./run.sh
```

### Workflow

1. Get game info

- Research the game we want to recreate in the terminal
- Capture controls, gameplay loop, scoring, and distinctive mechanics

2. Save game info with the Obsidian web extension

- Store source material and notes in reference folder
- Keep references organized for later implementation work

3. Tell Codex we want to create a terminal version of the game

- Use the collected notes as implementation context
- Define the target experience and scope for the terminal build

4. Test and improve in a loop

- Run the game
- Check feel, controls, and readability
- Iterate on gameplay until the cabinet is solid

:::success
This workflow keeps discovery, note capture, implementation, and iteration tightly connected.
:::
