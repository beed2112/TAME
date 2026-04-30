---
title: "Tetris/Rotation systems"
source: "https://strategywiki.org/wiki/Tetris/Rotation_systems"
author:
  - "[[StrategyWiki]]"
published: 2023-01-20
created: 2026-03-17
description: "Like many aspects of Tetris, something like the rotation of pieces may at first appear very simple and straightforward, but in practice it is very nuanced. Although..."
tags:
  - "clippings"
---
< [Tetris](https://strategywiki.org/wiki/Tetris "Tetris")

Like many aspects of Tetris, something like the rotation of pieces may at first appear very simple and straightforward, but in practice it is very nuanced. Although all versions of Tetris allow you to rotate pieces 90 degrees, and most versions allow you to rotate them clockwise or counter-clockwise, not every version of Tetris rotates pieces quite the same way. Read more below for a better understanding.

## Rotation systems

### Nintendo rotation system

![](https://cdn.wikimg.net/en/strategywiki/images/thumb/5/53/Tetris_rotation_Nintendo.png/240px-Tetris_rotation_Nintendo.png)

The rotation system employed by the [NES](https://strategywiki.org/wiki/NES "NES") version of [Tetris](https://strategywiki.org/wiki/Tetris_\(NES\) "Tetris (NES)"), as well as the [SNES](https://strategywiki.org/wiki/SNES "SNES") compilation of [Tetris & Dr. Mario](https://strategywiki.org/w/index.php?title=Tetris_%26_Dr._Mario&action=edit&redlink=1 "Tetris & Dr. Mario (page does not exist)"), is fairly simple. It is also known as the "right handed rotation system" for the purposes of comparison to the Game Boy version of Tetris (see below).

- O pieces have no rotations.
- I pieces have two rotations, favoring the lower half when horizontal, and the right half when vertical.
- J, L, and T pieces have four rotations centered around the middle square of the three square edge.
- While S and Z pieces have four rotations, they always favor the bottom and right sides of their rotation space (hence the "right handed" aspect of this rotation system.)

These games don't contain more advanced movement features like wall kicks (see below) and lock delays (see [Features](https://strategywiki.org/wiki/Tetris/Features "Tetris/Features")).

### Game Boy rotation system

![](https://cdn.wikimg.net/en/strategywiki/images/thumb/4/4d/Tetris_rotation_Gameboy.png/240px-Tetris_rotation_Gameboy.png)

The rotation system employed by the [Game Boy](https://strategywiki.org/wiki/Game_Boy "Game Boy") version of [Tetris](https://strategywiki.org/wiki/Tetris_\(Game_Boy\) "Tetris (Game Boy)") is nearly identical to the one found in the NES version (described above) with one exception: The S and Z pieces favor the *left* side of their rotation space. For this reason, this rotation system is referred to as the left-handed rotation system.

### Original rotation system

The original rotation system found in a majority of the early console and computer releases of the game is identical to the Nintendo (right handed) rotation system described above, with one single exception: the I piece, when rotated horizontally, is one row of squares higher.

### Sega rotation system

![](https://cdn.wikimg.net/en/strategywiki/images/thumb/7/70/Tetris_rotation_Sega.png/240px-Tetris_rotation_Sega.png)

Sega rotation is a rotation system that has been used by [Sega](https://strategywiki.org/wiki/Sega "Sega") 's [arcade](https://strategywiki.org/wiki/Arcade "Arcade") version of [Tetris](https://strategywiki.org/wiki/Tetris_\(Sega\) "Tetris (Sega)") and its successors. Each tetromino is ordinarily spawned flat side up. The ceiling prevents rotation.

Apart from I and O, all tetrominoes rotate such that the bottom of the tetromino is at the bottom of the piece's bounding box. S and Z rotate between two states so that the center column stays constant. O does not rotate; I rotates between two states as depicted in the illustration.

The differences between Sega rotation and Nintendo Rotation System are that the flat-side-down states of J, L, and T are pushed down by one space, that S and Z round in different directions, that I rounds differently from the other pieces, and that I requires more space under it to rotate to a vertical orientation.

### Arika/TGM rotation system

Sega rotation originally used no wall kicks. Arika took Sega rotation, added mild wall kicks and initial rotation, and ended up with TGM ([Tetris: The Grand Master](https://strategywiki.org/wiki/Tetris:_The_Grand_Master "Tetris: The Grand Master")) Rotation, or Arika Rotation System. This rotation system is a game play mechanic used in Tetris: The Grand Master and other Arika tetromino games, derived from Sega rotation. It is often refered to as ARS (Arika Rotation System), even though some people believe that this name is misleading. Games using TGM rotation generally use IRS, fast DAS, lock delay, and firm drop, and tetrominoes start out with the topmost block on the top row (generally row 20). The "ARS" and "ARS2" modes of Tetris The Grand Master Ace use a hybrid of TGM rules and Guideline rules. In addition to the TGM series, most arcade games developed in Japan before the guideline followed the Sega rotation rules with varying degrees of wall kicks, such as [Flash Point](https://strategywiki.org/w/index.php?title=Flash_Point&action=edit&redlink=1 "Flash Point (page does not exist)"), [Bloxeed](https://strategywiki.org/w/index.php?title=Bloxeed&action=edit&redlink=1 "Bloxeed (page does not exist)"), [Sega Tetris](https://strategywiki.org/w/index.php?title=Sega_Tetris&action=edit&redlink=1 "Sega Tetris (page does not exist)"), and the [Tetris Plus](https://strategywiki.org/wiki/Tetris_Plus "Tetris Plus") series.

### Super rotation system

![](https://cdn.wikimg.net/en/strategywiki/images/thumb/7/7f/Tetris_rotation_super.png/240px-Tetris_rotation_super.png)

Super Rotation System, or SRS, is the current Tetris Guideline standard for how tetrominoes behave, defining where and how the tetrominoes spawn, how they rotate, and what wall kicks they may perform. Henk Rogers developed this system in order to unify all new Tetris games under the Tetris Guideline.

The basic rotation states are shown in the diagram on the right. Some points to note:

- When unobstructed, the tetrominoes all appear to rotate purely about a single point. These apparent rotation centers are shown as circles in the diagram.
- It is a pure rotation in a mathematical sense, as opposed to the combination of rotation and translation found in other systems such as Sega Rotation (described above) and Atari Rotation.
- As a direct consequence, the *J*, *L*, *S*, *T* and *Z* tetrominoes have 1 of their 4 states (the spawn state) in a "floating" position where they are not in contact with the bottom of their bounding box.
- This allows the bounding box to descend below the surface of the stack (or the floor of the playing field) making it impossible for the tetrominoes to be rotated without the aid of floor kicks.
- The *S*, *Z* and *I* tetrominoes have two horizontally oriented states and two vertically oriented states. It can be argued that having two vertical states leads to faster finesse.
- For the *I* and *O* tetrominoes, the apparent rotation center is at the intersection of gridlines, whereas for the *J*, *L*, *S*, *T* and *Z* tetrominoes, the rotation center coincides with the center of one of the four constituent minos.

## Wall kicks

Wall kicks are not available in most early versions of Tetris. Wall kicks were introduced in the 1998 arcade game [Tetris: The Grand Master](https://strategywiki.org/wiki/Tetris:_The_Grand_Master "Tetris: The Grand Master") (or TGM). They were formally adopted into the SRS in the 2001 game [Tetris Worlds](https://strategywiki.org/w/index.php?title=Tetris_Worlds&action=edit&redlink=1 "Tetris Worlds (page does not exist)"). They were introduced to address the issue of being unable to rotate a piece that was backed up against the wall until the piece was moved away.

A wall kick happens when a player rotates a piece when no space exists in the squares where that tetromino would normally be after the rotation. To compensate, the game sets a certain number of alternative spaces for the tetromino to look.

The simplest wall kick algorithm, used (with variations) by TGM rotation and several fan games in the same tradition, is to try moving the tetromino one space to the right, and then one space to the left, and fail if neither can be done. Wall kicks increase the number of possible twists, ways to rotate a piece into seemingly blocked positions.