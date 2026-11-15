"""Parametric model of the chest strap: two webbing clips and a print-in-place chain.

All sizes in mm. Print orientation is the model orientation: Z up, as exported.
Worn orientation: X runs across the chest, Z runs up along the shoulder strap.
"""

import json
import math
from pathlib import Path

from build123d import (
    Box, Compound, Plane, Polygon, Pos, Rectangle, RectangleRounded,
    SlotOverall, chamfer, export_step, export_stl, extrude, fillet, mirror,
)

from bambu3mf import ObjectSpec, PartSpec, write_project

# --- measurements of the backpack -------------------------------------------
WEBBING_W = 20.0      # measured
WEBBING_T = 2.0       # ASSUMED, not measured yet

# --- printing ----------------------------------------------------------------
LAYER = 0.08          # print layer height (0.08 = finest preset for the 0.4 mm nozzle)
FIRST_LAYER = 0.20    # first layer height of the Bambu presets

# The slicer cuts at FIRST_LAYER + k * LAYER. Every Z level of the chain sits on that grid,
# so no gap between links gets rounded smaller.


def _level(v):
    """Snap an absolute height above the bed to a layer boundary."""
    return FIRST_LAYER + round((v - FIRST_LAYER) / LAYER) * LAYER


def _layers(v, up=False):
    """Snap a thickness to a whole number of layers."""
    n = v / LAYER
    return (math.ceil(n - 1e-6) if up else round(n)) * LAYER


# Bambu Studio project files: settings as Bambu Studio saved them, plus the overrides below
BAMBU_SETTINGS = Path(__file__).parent / "bambu" / "project_settings.config"
BAMBU_PRINT_OVERRIDES = {"brim_type": "no_brim"}  # the brim leaves sharp remains on the links
FILAMENT = 4          # AMS slot of the black PLA
BED_XY = 256.0
PART_GAP = 12.0       # distance between parts on the plate
RESULT_3MF = Path(__file__).parent / "backpack-chest-strap.3mf"  # the file to print; tracked in git

# --- chain -------------------------------------------------------------------
N_LINKS = 15          # taut length = N_LINKS * LINK_IN_L
TEST_LINKS = 4        # short chain for the first test print
WIRE = 2.4            # link bar width
LINK_IN_L = 15.0      # inner length = taut pitch = one adjustment step
LINK_IN_W = 5.0       # inner width of a flat link
FLAT_T = _level(2.4)   # flat link thickness where it lies on the bed
BAR_T = _layers(2.2)   # thickness of the raised end bar of a flat link
UP_RAIL = _level(2.0)  # bottom rail of an upright link
UP_TOP = _layers(2.0)  # top rail of an upright link
UP_T = 2.4            # upright link thickness (Y)
UP_IN_H = _layers(4.4) # opening height of an upright link
GAP_Z = _layers(0.6, up=True)  # vertical print gap between links, never below 0.6
CHAMFER = 0.4         # edge chamfer on the links, the hook and the clips

# --- clips -------------------------------------------------------------------
CLIP_H = 16.0         # height along the webbing; higher than the hook, so the tip is shielded
CLIP_WALL = 2.4       # front and back bar
CLIP_SIDE = 3.0       # side walls
SLOT_W = WEBBING_W + 1.0
SLOT_T = WEBBING_T + 0.6
SPLIT = 6.0           # gap in the back bar; the folded webbing goes in here
HOOK_T = 2.8          # hook bar section; must pass through a link that already holds its neighbours
HOOK_THROAT = 9.0     # deep enough for two link bars: the hooked link and the next spare link
HOOK_MOUTH = 5.0      # gap between the hook tip and the clip
HOOK_RAMP = 3.0       # 45 deg wedge where the hook bar meets the clip, instead of a sharp corner

LINK_OUT_L = LINK_IN_L + 2 * WIRE
LINK_OUT_W = LINK_IN_W + 2 * WIRE
PITCH = (LINK_IN_L + LINK_OUT_L) / 3       # spacing as printed; equal gaps on both sides of each bar
Z_BAR = UP_RAIL + GAP_Z                    # underside of a raised end bar
UP_H = UP_RAIL + UP_IN_H + UP_TOP
SLOPE_Y = 1.73                             # pocket side walls, 30 deg from vertical
POCKET_X0 = LINK_IN_L / 2 - 4.0            # where the 45 deg ramp starts
POCKET_YB = UP_T / 2 + GAP_Z + Z_BAR / SLOPE_Y
FAR = 30.0


def _tent(x0, z_top, yb, lip_x=None):
    """Convex wedge at the +X end: 45 deg ramp in X, sloped walls in Y, flat top.

    With lip_x the top rises again at 45 deg beyond lip_x.
    """
    top = [(FAR, z_top)] if lip_x is None else [(lip_x, z_top), (FAR, z_top + FAR - lip_x)]
    side = Polygon((x0, 0), (x0 + z_top, z_top), *top, (FAR, 0), align=None)
    across = Polygon((-yb, 0), (0, yb * SLOPE_Y), (yb, 0), align=None)
    return extrude(Plane.XZ * side, FAR, both=True) & extrude(Plane.YZ * across, FAR, both=True)


def _ring(height):
    plan = SlotOverall(LINK_OUT_L, LINK_OUT_W) - SlotOverall(LINK_IN_L, LINK_IN_W)
    ring = extrude(plan, height)
    return chamfer(ring.edges(), CHAMFER)


def flat_link():
    """Link lying on the bed. Both end bars are raised so an upright link passes under.

    The chamfer comes from the two chamfered rings; chamfering the finished link fails in OCC.
    """
    bar_top = Z_BAR + BAR_T
    raised = _ring(bar_top) & _tent(POCKET_X0 - 3.0, bar_top, LINK_OUT_W / 2 + 1.5)
    pocket = _tent(POCKET_X0, Z_BAR, POCKET_YB, lip_x=LINK_OUT_L / 2 - CHAMFER)
    half = raised - pocket
    body = _ring(FLAT_T) - pocket - mirror(pocket, Plane.YZ)
    return body + half + mirror(half, Plane.YZ)


def upright_link(inner_l=LINK_IN_L):
    """Link standing on its long side."""
    c = 1.5
    hl, h = inner_l / 2 + WIRE, UP_H
    outer = Polygon(
        (-hl + c, 0), (hl - c, 0), (hl, c), (hl, h - c),
        (hl - c, h), (-hl + c, h), (-hl, h - c), (-hl, c), align=None,
    )
    inner = Pos(0, UP_RAIL + UP_IN_H / 2) * RectangleRounded(inner_l, UP_IN_H, 1.2)
    link = extrude(Plane.XZ * (outer - inner), UP_T / 2, both=True)
    return chamfer(link.edges(), CHAMFER)


def clip_body():
    """Sleeve around the webbing. Inner wall face at X=0, body towards -X."""
    depth = SLOT_T + 2 * CLIP_WALL
    width = SLOT_W + 2 * CLIP_SIDE
    cx = -width / 2
    profile = Pos(cx, 0) * RectangleRounded(width, depth, 1.5)
    profile -= Pos(cx, 0) * Rectangle(SLOT_W, SLOT_T)
    profile -= Pos(cx, -(SLOT_T + CLIP_WALL) / 2) * Rectangle(SPLIT, CLIP_WALL + 0.2)
    body = extrude(profile, CLIP_H)
    return chamfer(body.edges(), CHAMFER)


EYE_IN_L = LINK_IN_L / 2      # the eye is half an upright link: it only holds one link bar
EYE_END = EYE_IN_L - 0.2      # far inner face of the eye; its near post sits inside the clip wall


def chain_clip():
    """Left clip. The eye is a short upright link fused into the clip wall, in line with the hook."""
    return clip_body() + Pos(EYE_END - EYE_IN_L / 2, 0, 0) * upright_link(EYE_IN_L)


def _round(sketch, x, y, radius):
    """2D fillet of the sketch corner at (x, y)."""
    corner = [v for v in sketch.vertices() if abs(v.X - x) < 1e-6 and abs(v.Y - y) < 1e-6]
    assert len(corner) == 1, f"no corner at ({x}, {y})"
    return fillet(corner, radius)


def hook_clip():
    """Right clip. The hook lies flat against the chest and its tip points up."""
    t, rise = HOOK_T, HOOK_THROAT
    r = rise + 4 + HOOK_MOUTH
    hook = Polygon(
        (0.5, 0), (-r, 0), (-r, t), (-r + rise, t + rise),
        (-r + rise + 4, t + rise), (-r + 4, t), (-HOOK_RAMP, t), (0.5, t + HOOK_RAMP + 0.5), align=None,
    )
    # no sharp points: the tip is a 45 deg corner before rounding
    hook = _round(hook, -r + rise + 4, t + rise, 1.2)
    hook = _round(hook, -r + rise, t + rise, 1.2)
    hook = _round(hook, -r, t, 1.5)
    hook = _round(hook, -r + 4, t, 0.6)
    bar = extrude(Plane.XZ * hook, t / 2, both=True)
    # The bar is thin only where links pass over it: the barb and the throat, which holds two link
    # bars. From there to the clip it widens, so a side knock does not snap it off at the wall.
    wide = SLOT_T + 2 * CLIP_WALL - 1.0
    taper_end = -r + 4 + 2 * WIRE + 0.2
    plan = Polygon((1.5, -wide / 2), (1.5, wide / 2), (taper_end, t / 2), (taper_end, -t / 2), align=None)
    root = extrude(plan, t)
    return mirror(clip_body(), Plane.YZ) + chamfer(bar.edges(), CHAMFER) + chamfer(root.edges(), CHAMFER)


def chain_links(n=N_LINKS):
    links = []
    for i in range(n):
        link = flat_link() if i % 2 == 0 else upright_link()
        links.append(Pos(EYE_END - LINK_IN_L / 2 + (i + 1) * PITCH, 0, 0) * link)
    return links


def build():
    return {"chain_clip": chain_clip(), "links": chain_links(), "hook_clip": hook_clip()}


def export(out=Path("out")):
    out.mkdir(exist_ok=True)
    parts = build()
    left = Compound(children=[parts["chain_clip"], *parts["links"]])
    # fresh shapes: a shape can have only one parent compound
    test = Compound(children=[chain_clip(), *chain_links(TEST_LINKS)])
    test_links = Compound(children=chain_links(TEST_LINKS))
    shapes = (
        ("left-clip-with-chain", left), ("right-clip-with-hook", parts["hook_clip"]),
        ("test-chain", test), ("test-chain-only", test_links),
        ("test-2-links", Compound(children=chain_links(2))),
    )
    for name, shape in shapes:
        export_stl(shape, str(out / f"{name}.stl"), tolerance=0.01, angular_tolerance=0.1)
        export_step(shape, str(out / f"{name}.step"))
    return parts


def _plate(shapes):
    """One object per (name, shape), stacked front to back around the bed centre."""
    boxes = [shape.bounding_box() for _, shape in shapes]
    depth = sum(b.size.Y for b in boxes) + PART_GAP * (len(boxes) - 1)
    y = (BED_XY - depth) / 2
    objects = []
    for (name, shape), b in zip(shapes, boxes):
        at = (BED_XY / 2 - (b.min.X + b.max.X) / 2, y - b.min.Y)
        objects.append(ObjectSpec(name, [PartSpec(name, shape, FILAMENT)], at))
        y += b.size.Y + PART_GAP
    return objects


def export_3mf(out=Path("out")):
    """Bambu Studio projects: the full strap on one plate (RESULT_3MF), and the test prints in out/."""
    settings = json.loads(BAMBU_SETTINGS.read_text())
    plates = {
        RESULT_3MF.stem: [
            ("left clip with chain", Compound(children=[chain_clip(), *chain_links()])),
            ("right clip with hook", hook_clip()),
        ],
        "test-2-links": [("two links", Compound(children=chain_links(2)))],
        "test-right-clip": [("right clip with hook", hook_clip())],
        "test-left-clip": [("left clip with short chain", Compound(children=[chain_clip(), *chain_links(TEST_LINKS)]))],
    }
    for name, shapes in plates.items():
        path = RESULT_3MF if name == RESULT_3MF.stem else out / f"{name}.3mf"
        write_project(path, settings, _plate(shapes), title=name, print_overrides=BAMBU_PRINT_OVERRIDES)


if __name__ == "__main__":
    export()
    export_3mf()
    print(f"taut chain length: {N_LINKS * LINK_IN_L:.0f} mm, step {LINK_IN_L:.0f} mm")
    print(f"printed length of left part: {EYE_END - LINK_IN_L / 2 + N_LINKS * PITCH + LINK_OUT_L / 2 + SLOT_W + 2 * CLIP_SIDE:.0f} mm")
