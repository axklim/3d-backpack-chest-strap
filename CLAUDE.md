# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

A 3D-printed chest strap for a backpack, made as a chain.

- **Problem:** the shoulder straps slide off the shoulders and have to be adjusted again and again while walking.
- **Idea:** print a chain on the 3D printer that links the two shoulder straps across the chest.
- **Why print it:** shop chest straps exist, but none match the backpack colour and the standard black webbing ones look ugly.
- **Look:** it should be a nice design, not just a functional part. Black is fine: printed plastic looks different enough from the fabric.
- **Origin:** the idea came up during a walk around Spandau.

## The backpack (from photos in `docs/reference/`)

- Tan backpack with padded shoulder straps, mesh on the inside.
- On the front of each pad a webbing strip is sewn at the top and runs down through a black plastic ladder-lock buckle at the lower end of the pad. Between the stitching and the buckle the webbing is free, not sewn to the pad (about 4 cm).
- Webbing is 20 mm wide (measured by the user). The buckle is about 30 mm long (estimate from a photo with a ruler: measure before modelling).
- No existing chest strap, rail or loops for one.
- `05-worn-metal-chain-mockup.jpg`: a metal chain hooked on both buckles. It only shows where the strap goes. It is not a reference for the look or the mechanism.

## Design (approved by the user)

- **Clips:** one sleeve on each strap, on the free webbing above the buckle. The back bar has a 6 mm split: fold the webbing and slide it in. The backpack is not changed.
- **Chain:** real chain, printed in place, already linked, and joined to the left clip.
- **Hook:** on the right clip. It takes any link, not only the last one, so one link (15 mm) is one adjustment step. The user wants to adjust it during a hike. It is also how the strap opens.
- **Material:** black PLA Basic (the user's choice). The AMS slots change between projects (black was slot 4 on 2026-11-14), so do not hard-code a slot.

## Printer and print settings

- Bambu Lab P1S, 0.4 mm nozzle (the default one: flow type Standard, not High Flow), AMS, textured PEI plate, Bambu Studio. Same setup as the user's other `3d-*` repos (github.com/axklim: `3d-door-handle`, `3d-box-for-plastic-bags`, `3d-skull-brush`); the box repo has `bambu3mf.py`, which writes a Bambu Studio project 3MF from build123d shapes.
- 0.08 mm Extra Fine profile (the user wants the finest layers), first layer 0.20 mm (preset default), 3 wall loops, 100% infill, supports off, no brim. `LAYER` and `FIRST_LAYER` in `strap.py` must match the slicer: every Z level of the chain is snapped to a layer boundary, so the slicer does not round a gap smaller. `check.py` tests this.
- Load each STL as one object. Do not split it into objects or parts: the links would lose their linked positions.

## Commands

```sh
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python build123d trimesh matplotlib shapely   # once
.venv/bin/python strap.py    # export STL + STEP + Bambu Studio 3MF projects to out/ (full left part, right clip, test-chain: left clip + 4 links, test-chain-only: 4 links, test-2-links: 2 links)
.venv/bin/python check.py    # every part is one solid, neighbour links keep >= 0.4 mm gap
.venv/bin/python render.py   # preview PNGs in out/ (look at them after every geometry change)
.venv/bin/python drawing.py  # dimensioned drawings of both clips in docs/drawings/ (tracked; rerun after a size change)
```

**`backpack-chest-strap.3mf` in the repo root is the result: the Bambu Studio project to print** (both parts on one plate, all settings inside). It is tracked on purpose, so a second copy can be printed without running anything. `strap.py` regenerates it; commit it together with every model change. The user counts this file and photos of the printed strap as the result of the project; their other `3d-*` repos keep such photos in `images/result/`. The `out/test-*.3mf` files (two links, right clip alone, left clip with 4 links) are generated test prints and are not tracked. `bambu3mf.py` writes them; it is a copy from the user's `3d-box-for-plastic-bags` repo, and that repo's `docs/bambu-3mf-format.md` lists the format rules. `bambu/project_settings.config` holds the print settings exactly as Bambu Studio saved them in `test-chain-only.3mf`; `BAMBU_PRINT_OVERRIDES` in `strap.py` goes on top (currently no brim). Bambu Studio is not installed on this Mac, so a generated 3MF can only be checked by reading the file, not by loading or slicing it.

`bambu/test-chain-only.3mf` is the Bambu Studio project the user saved for the first test print, kept as the source of `bambu/project_settings.config` (4 links, the settings below, black on slot 4). Its geometry is a copy: it does not update when `strap.py` changes.

`out/` and `.venv/` are not in git. The user works on another device: copy STL files to `~/Share` for them, never overwrite there, add `-1`, `-2` to the name instead.

## How the model works

`strap.py` is the whole model (build123d). All sizes are constants at the top. Model orientation is print orientation (Z up); when worn, X runs across the chest and Z runs up along the strap.

- **Two link types alternate.** Upright links stand on their long side. Flat links lie on the bed, but both of their end bars are raised (`_tent` builds the raised bar and the pocket under it), so the bottom rail of the next upright link passes under them. This is what lets a linked chain print without supports. Do not flatten the end bars.
- **Printed vs taut length.** `PITCH` (derived, 11.6) is the link spacing on the bed. Under tension the pitch is `LINK_IN_L` (15), so the worn chain is about 30% longer than the print.
- **Left part:** clip body + half an upright link fused into the clip wall as the eye (the user found a full link too long) + the chain (which starts with a flat link), exported as one STL with many separate solids (clip + one per link). A build123d shape can have only one parent `Compound`: reusing the same shapes in a second compound silently removes them from the first export. Build fresh shapes for each export.
- **Chamfer (0.4 mm, `CHAMFER`)** on all links, the hook bar and both clip bodies; the user asked for it. The clip body is chamfered before the eye or hook is joined. On the flat link it comes from two pre-chamfered rings (`_ring`), because chamfering the finished link fails in OCC. The sloped ramps and the underside of the raised bars have no chamfer.
- **The eye is an upright link, not a flat one.** A flat link is wider (9.8 mm) than the clip (7.4 mm) and stuck out; the user asked for the upright link, which also mirrors the hook on the right clip. Both clips share `clip_body()`, so they always have the same height.
- **Both clips are plain extrusions along Z**, so they need no supports. The hook is a 45 degree barb for the same reason, and its tip must point up when worn. Its tip and corners are rounded in the 2D profile (`_round`): the user found the first, pointed hook too sharp. The clips are 16 mm high so the hook tip (11.8 mm) sits below the clip top; the user asked for that. The hook bar is 2.8 mm thick only at the barb and the throat, where links pass; towards the clip it widens to almost the clip depth and ends in a 45 degree ramp, because the user found the thin joint weak.
- **The hook must work on a middle link.** A middle link's hole already holds the bars of both neighbours, so the free opening is `LINK_IN_L - 2 * WIRE` long, and the hook throat must hold two bars (the hooked link's end and the next spare link). The first version (12 x 4 links, 6 mm throat) only worked on the last link. `check.py` tests both; keep those tests when changing link or hook sizes.

## Open points

- `WEBBING_T` (2.0) is assumed. Measure the webbing thickness.
- `N_LINKS` (15, taut 225 mm) is a guess. It needs the distance between the two webbing strips when the pack is worn.
- **Test print 1 (2026-11-15):** `test-chain-only` at 0.08 mm with a 3 mm outer brim. The chain is good: the links are free and the 0.64 mm gap works. The brim came off the bed easily but left remains on the links, which makes them a bit sharp. The user wants to print without a brim.
- **Test print 2 (2026-11-15):** `test-2-links.3mf` without a brim. It held on the plate and the user finds the result better. Print without a brim from now on. The generated 3MF loaded in Bambu Studio with its settings.
- **Next tests, in the user's order:** `test-right-clip.3mf` first (slot fit on the webbing, hook), then `test-left-clip.3mf` (eye joint, hooking into a middle link).
- Still untested: the clip slot fit on the webbing, the eye joint, and the hook.
