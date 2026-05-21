# Asteroids Session Notes

This document tracks the working conversation for the TAME Asteroids cabinet: user feedback, implementation decisions, and changes made during the session. It is intended to be updated as the work continues.

## Session Summary

Goal: add an Asteroids cabinet to TAME with a readable ship, rotation, thrust-driven movement, and the standard cabinet score flow.

Current status:
- Asteroids cabinet implementation started.
- Dedicated cabinet files and session tracking are being added under `asteroids/`.

## Conversation Log

### 1. Initial request

User feedback:
- Move to Asteroids next and add it to the cabinet.
- Make sure the ship is a decent size.
- The ship rotates and moves with propulsion.
- Keep session notes for this also in the `asteroids` folder.

Actions taken:
- Reviewed the Asteroids reference notes in the `asteroids` folder.
- Confirmed the cabinet implementation pattern used across TAME.
- Started a dedicated Asteroids session notes file.
- Began implementing a new Asteroids cabinet with rotation, thrust, wraparound, asteroid splitting, and persistent high score logic.

Implementation summary:
- Added a new cabinet under `asteroids/asteroidsconsole/`.
- Built a curses-based Asteroids game with:
  - rotating ship controls
  - thrust-driven inertia
  - wraparound movement
  - bullets with lifetime limits
  - large, medium, and small asteroid splitting
  - hyperspace
  - extra lives at score thresholds
  - persistent top-10 score handling in `~/.asteroids_console`
- Registered Asteroids in the TAME launcher.
- Updated top-level docs and cabinet slide content to include Asteroids.

Files added:
- `asteroids/asteroidsconsole/asteroids_terminal.py`
- `asteroids/asteroidsconsole/run.sh`
- `asteroids/asteroidsconsole/install.sh`
- `asteroids/asteroidsconsole/README.md`
- `asteroids/asteroids-session-notes.md`

Files updated:
- `arcade/arcade_launcher.py`
- `README.md`
- `tame-game-cabinet.retro.html`

Verification so far:
- `python3 -m py_compile asteroids/asteroidsconsole/asteroids_terminal.py arcade/arcade_launcher.py`

### 2. Playfield size adjustment

User feedback:
- The Asteroids playfield should be closer to a Galaga/Defender-sized cabinet field.
- A reference graphic was added to show the broader open-space composition.

Actions taken:
- Reviewed the added Asteroids reference image.
- Increased the Asteroids playfield dimensions to make the cabinet feel wider and more open.
- Updated cabinet metadata and documentation to match the larger runtime size.

Implementation summary:
- `FIELD_WIDTH`: `64` -> `78`
- `FIELD_HEIGHT`: `26` -> `28`
- `MIN_WIDTH`: `92` -> `106`
- `MIN_HEIGHT`: `32` -> `34`

### 3. Defender-sized field and classic ship/rock styling

User feedback:
- Model the playfield after Defender as far as overall field size.
- The classic player ship shape is `>`, but bigger.
- The asteroid targets should feel like rocks of various sizes.

Actions taken:
- Resized the Asteroids cabinet down to the Defender baseline footprint.
- Reworked the ship silhouette into a larger wedge-like `>` form across its rotation states.
- Replaced the simple round asteroid markers with irregular multi-cell rock shapes for large and medium targets.

Implementation summary:
- `MIN_WIDTH`: `106` -> `80`
- `MIN_HEIGHT`: `34` -> `26`
- `FIELD_WIDTH`: `78` -> `52`
- `FIELD_HEIGHT`: `28` -> `20`
- Ship rendering now uses a larger wedge-style model.
- Rock rendering now uses irregular size-based cell clusters instead of single round glyphs.

### 4. Saucer pressure pass

User feedback:
- Asteroids should feel more like a full game cabinet, not just a rock-clearing prototype.

Actions taken:
- Added timed saucer spawns that enter from the screen edge during active waves.
- Added saucer bullets so the player gets counterfire instead of passive target practice.
- Added saucer score values, HUD status, and intro/sidebar copy updates.

Implementation summary:
- Added large and small saucer variants with different point values and accuracy.
- Ship bullets now distinguish between player and saucer ownership.
- Saucer collisions, scoring, and respawn timing are handled in the main update loop.

Files updated:
- `asteroids/asteroidsconsole/asteroids_terminal.py`
- `asteroids/asteroidsconsole/README.md`

Verification:
- `python3 -m py_compile asteroids/asteroidsconsole/asteroids_terminal.py`

### 5. Defender-sized field pass

User feedback:
- Model the playing field and ship after Defender.
- The current Asteroids field is too small and the ship is too big.

Actions taken:
- Expanded the Asteroids playfield to consume more of the `80x26` cabinet width.
- Compressed the right-side info panel so it stops stealing horizontal play space.
- Replaced the oversized wedge ship with a tighter Defender-scaled sprite set.

Implementation summary:
- `FIELD_WIDTH`: `52` -> `62`
- `FIELD_HEIGHT`: `20` -> `21`
- `field_left()` now anchors the field near the left edge instead of centering a narrow box.
- Ship nose/flame offsets and collision spacing were reduced to match the smaller craft.

Files updated:
- `asteroids/asteroidsconsole/asteroids_terminal.py`

Verification:
- `python3 -m py_compile asteroids/asteroidsconsole/asteroids_terminal.py`

## Update Rule

As new feedback arrives, append:
- the user request or gameplay note
- the code or design changes made in response
- any verification performed
