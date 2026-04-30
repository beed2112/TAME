---
title: "Centipede Disassembly"
source: "https://6502disassembly.com/va-centipede/"
author:
published:
created: 2026-03-24
description: "Disassembly of Atari Centipede (arcade version)"
tags:
  - "clippings"
---
[(back to project list)](https://6502disassembly.com/index.html)

## Centipede (1981) Disassembly

[Centipede](https://en.wikipedia.org/wiki/Centipede_\(video_game\)) is a "fixed shooter" game, developed for video arcades in the 1980s. It was one of the top-selling games of the era, and one of the first to have a significant female player base.

Four revisions of the official Centipede ROMs were released. The final revision caused some controversy among game emulator enthusiasts, because it replaced support for two-player games with a countdown timer. Most of the code was untouched, so the disassembly here is for revision 4.

Centipede is copyright 1980 Atari, Inc.

- [Disassembly listing](https://6502disassembly.com/va-centipede/Centipede_rev4.html) of the Centipede rev 4 ROMs.
- **[Explanation of graphics](https://6502disassembly.com/va-centipede/graphics.html)**, including the playfield tiles, motion objects, and color scheme.
- **[List of messages](https://6502disassembly.com/va-centipede/messages.html)** displayed.
- **[Project set](https://6502disassembly.com/va-centipede/va-centipede.zip)** - project files and binaries (requires SourceGen v1.8.2 or later).
- Instructions for **[creating the binary](https://6502disassembly.com/va-centipede/bingen.html)** used for the disassembly listing.

Related resources:

- **[Original sources](https://github.com/historicalsource/centipede)**. The original source code for all ROM revisions of Centipede is now available.
- **[MAME](https://www.mamedev.org/)**. The best way to play classic arcade games if you can't afford the real thing.
- **[Atari service manuals](https://arcarc.xmission.com/PDF_Arcade_Atari_Kee/)** at arcarc.xmission.com. Includes manuals for various versions of Centipede.

---

## Game Play

![scores](https://6502disassembly.com/va-centipede/images/scores.png) ![play](https://6502disassembly.com/va-centipede/images/play.png)

The controls are simple. The game is designed to work with either a trackball or a digital joystick. The player positions a gun in the lower part of the play area, and fires one shot at a time with the fire button.

#### Using MAME

The easiest way to play is via emulation on a computer. Once you have the Centipede ROM file, save it in the MAME "roms" folder". When you start the MAME UI front-end, it will find the game automatically. Select it from the list and hit Enter. When the system summary displays, hit Enter again. (If this doesn't work for you, please visit one of the many MAME help sites.)

While the game is running, you can get a list of keys by hitting Tab, selecting "Input (this Machine)" with the arrow keys, and hitting Enter. The most important are:

- 5 - deposit a coin
- 1 - start game (1 player)
- LeftArrow / UpArrow / RightArrow / DownArrow - move gun
- Ctrl - fire (hold for continuous shots)
- P - pause/unpause
- ESC - exit

Hit Tab to open a menu with a "DIP Switches" sub-menu that will let you set the machine for free play so you can stop inserting virtual quarters.

If you don't want to move the crosshairs with the arrow keys, you'll want to configure MAME to use a mouse or game controller. From the main MAME menu, select Configure Options, then Device Mapping, then adjust the Trackball Device Assignment. If you select "mouse", you can use the mouse to move the pointer and the button to fire. Note that selecting the mouse as the controller will cause MAME to grab the mouse cursor, which is fine while playing full-screen but inconvenient while trying to use the debugger.

I used MAME v0.236 for my testing.

### Playing

The basic idea is to shoot everything that moves without running into anything, as colliding with any moving object will kill the player. The player starts with 2-5 lives (determined by the DIP switch configuration), and will be awarded bonus lives as their score increases. The player can have at most 6 lives.

Points are awarded for shooting enemies:

| Target | Points |
| --- | --- |
| Mushroom | 1 (4th hit) |
| Centipede head | 100 |
| Centipede body | 10 |
| Spider | 300 / 600 / 900 |
| Flea | 200 (2nd hit) |
| Scorpion | 1000 |

Additionally, partially-destroyed mushrooms count for 5 points when the screen is resetting after the player dies.

#### Mushrooms

A field of mushrooms is randomly planted at the start of the game. Mushrooms are destroyed when shot multiple times by the player or touched by the spider, are created by fleas, and appear when a centipede segment is destroyed.

The initial field has up to 46 mushrooms. The code walks through rows 27 to 2, where row 31 holds the scores at the top and row 0 is below the player, and adds a new mushroom in a random column. When it reaches the bottom, it returns to the top. This means that most rows after the bottom five will have two mushrooms, though if both mushrooms in a row happened to land in the same column it will only have one. (See $28e4.)

#### Centipedes

There are 12 centipede segments. Initially the centipede is created as a single entity, but with each new wave the main centipede becomes shorter. The unaffiliated segments are created as single-segment heads with random position and direction.

At the start of a wave, the main centipede moves at 1 pixel/frame, until 40K points when the initial speed increases to 2 pixels/frame. Independent heads always start at 2 pixels/frame.

When the centipede reaches the bottom of the screen, new heads will start to replace any destroyed segments. The pace at which they appear increases every 10K points. Initially the delay is 192 frames (~3.2 sec), but reduces by 8 every time a head is created, to a minimum of 96 (~1.6 sec). It's further reduced by 2 frames every 10K points.

#### Spiders

The first spider appears 96 frames (~1.6sec) after a wave starts. After being killed, the cooldown is set to 128 frames (~2.1 sec). Spiders move at 1 pixel/frame until the score reaches 5,000 points, when the speed increases to 2 pixels/frame. In hard mode, the score threshold is lowered to 1,000 points.

Spiders move in a random direction for 48 frames (~3/4 sec), then have a 50% chance of changing direction. In hard mode, the chance of changing direction is 75%, making the movement more erratic. The only exception is if a spider reaches the limits of vertical movement, in which case it reverses direction immediately. The upper bound for a spider starts at 96 (12 rows up), but steadily contracts as the player's score increases from 60K to 180K points, eventually being reduced to 56 (7 rows).

Killing a spider earns the player 300, 600, or 900 points. The value is determined by the vertical distance between the player's gun and the spider at the time of the collision.

If a spider collides with a mushroom, the mushroom is destroyed.

#### Fleas

Fleas are the main source of new mushrooms. They don't spawn in waves where the centipede is 12 segments long, such as the first, and don't appear if there are enough mushrooms in the lower part of the screen (rows 1-11).

If the player's score is under 20K, a flea appears when there are five or fewer mushrooms near the bottom. At 120K points, the threshold increases to 9 or fewer. After that, it's 6 + (score / 20000), i.e. 12 or fewer at 120K points.

The flea moves at 2 pixels/frame, until the player reaches 60K points, when it speeds up to 3 pixels/frame. The first time the player shoots the flea, the speed increases to 4 pixels/frame. A second hit will destroy the flea.

As the flea moves down the screen, it has a 25% chance of creating a mushroom under it. This is tested every 4 frames, so when moving at 2 pixels/frame this is a 25% chance per tile. At faster speeds, fewer mushrooms will be created on average.

The flea has 4 animation frames defined for it, but only uses two. This appears to be a coding mistake.

#### Scorpions

Scorpions move horizontally across the upper part of the screen. Any mushroom they touch becomes poisoned, changing appearance. If a centipede touches a poisoned mushroom, it goes crazy and charges straight down the screen. When it reaches the bottom, the madness ends.

Scorpions use the same object slot as fleas, so the two will never be on screen at the same time. They move at 1 pixel/frame, until the player reaches 20K points, when it gains a 75% chance of moving at 2 pixels/frame instead. The movement direction is chosen at random.

## Under the Hood

In the original sources, fleas are called "ants", and spiders are called "bugs".

The game uses a 30x32 grid of 8x8 tiles. Moving objects are 16x8, two tiles wide. If the game is being played on a cocktail cabinet, the display needs to be rotated 180 degrees when player 2 is active. This is done entirely in software, by flipping the various graphics and rearranging their positions. For more details, see the [graphics page](https://6502disassembly.com/va-centipede/graphics.html).

The POKEY provides four sound channels. Assignments:

1. explosions
2. bonus life chime, centipede, scorpion sounds
3. shot sound
4. spider sound

The hardware provides a 64-byte Electrically Alterable Read Only Memory (EAROM). This type of storage is slow to write and requires that the software obey various timing requirements. For Centipede, it's used to hold the top 3 high scores, the total time spent playing games, and the total number of games played. This allows an average game time value to be shown in the self-test screen.

The revision 4 ROM replaced support for two-player games with a hard timer. The three DIP switches that configured the coin slot multiplier settings were repurposed to specify a timer value, 0-7 minutes (where zero means no time limit). The timer is displayed where player 2's score would go (and is actually stored in player 2's score variables), and support for player 2 was removed in a few places. Most of the code was unchanged, however, so you can still see most of the screen-flipping code in rev4.

The self-test feature has color bars and an alignment grid that aren't mentioned in the service manual.

The word "centipede" doesn't appear in the ROM, and there is no graphic image for it. There is no title screen; the game just puts up the high score list and lets "attract" mode run. Without the cabinet artwork, you wouldn't know what the game was called.

The copyright date displayed by the game is 1980, but the internal documentation is dated May 1981, and the game wasn't shipped until late 1981. The copyright notice is "booby trapped", with various strange things happening if the notice or the code that copies it to the screen is altered, so it's possible the programmers just didn't think it was worth the trouble to update the notice from "1980" to "1981" (it makes no difference legally).

MAME v0.236 oddities:

- The MAME driver seems to think there's RAM from $0200-03ff, but the game doesn't use it.
- In the default input configuration, the self-test screen shows that the keyboard arrow keys are generating both trackball and joystick input. The joystick handler speeds up movement over a few frames, allowing fine positioning, but the default control configuration prevents that from working.

---

Copyright 2022 by [Andy McFadden](https://fadden.com/)