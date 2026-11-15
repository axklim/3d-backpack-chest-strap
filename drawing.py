"""Dimensioned drawings of both clips in docs/drawings/. Outlines come from the model."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from shapely.geometry import Polygon
from shapely.ops import unary_union

import strap as s

INK, DIM = "#1c2733", "#b3261e"


def silhouette(shape, axes):
    verts, tris = shape.tessellate(0.01, 0.1)
    pts = np.array([[v.X, v.Y, v.Z] for v in verts])[:, axes]
    polys = [Polygon(pts[list(t)]) for t in tris]
    return unary_union([p.buffer(1e-4) for p in polys if p.area > 1e-9])


def outline(ax, geom):
    for g in getattr(geom, "geoms", [geom]):
        ax.fill(*g.exterior.xy, facecolor="#dfe6ee", edgecolor=INK, linewidth=1.2)
        for hole in g.interiors:
            ax.fill(*hole.xy, facecolor="white", edgecolor=INK, linewidth=1.2)


def dim(ax, a, b, at, text, vertical=False, text_right=False):
    """Dimension between coordinates a and b, drawn on the line `at`."""
    p, q = ((at, a), (at, b)) if vertical else ((a, at), (b, at))
    ax.annotate("", p, q, arrowprops=dict(arrowstyle="<->", color=DIM, lw=0.9, shrinkA=0, shrinkB=0))
    mid = ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)
    off = ((0.5 if text_right else -0.5), 0) if vertical else (0, 0.45)
    ha = ("left" if text_right else "right") if vertical else "center"
    ax.text(mid[0] + off[0], mid[1] + off[1], text, color=DIM, fontsize=9, ha=ha, va="center" if vertical else "bottom")


def frame(ax, title, xlim, ylim):
    ax.set_title(title, loc="left", fontsize=11, color=INK)
    ax.set_aspect("equal")
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.axis("off")


def webbing_note(ax, x, y):
    ax.text(x, y,
            f"Walls: front and back bar {s.CLIP_WALL:g}, side walls {s.CLIP_SIDE:g}. Edge chamfer {s.CHAMFER:g}.\n"
            f"Webbing: {s.WEBBING_W:g} wide (measured), {s.WEBBING_T:g} thick (assumed). "
            f"The slot is {s.SLOT_W - s.WEBBING_W:g} wider and {s.SLOT_T - s.WEBBING_T:g} thicker than that.",
            color=INK, fontsize=9, va="top")


def left_clip(out):
    clip = s.chain_clip()
    width = s.SLOT_W + 2 * s.CLIP_SIDE
    depth = s.SLOT_T + 2 * s.CLIP_WALL
    eye = s.EYE_END + s.WIRE

    fig, (side, top) = plt.subplots(2, 1, figsize=(11, 10.5), dpi=140, gridspec_kw=dict(height_ratios=[1.25, 1]))
    fig.suptitle("Left clip with eye: sizes in mm", x=0.06, ha="left", fontsize=14, color=INK)

    outline(side, silhouette(clip, [0, 2]))
    frame(side, "Side view, as it sits on the strap (up is up)", (-37, 27), (-7.5, 20))
    dim(side, -width, 0, -2.0, f"clip {width:g}")
    dim(side, 0, eye, -2.0, f"eye {eye:g}")
    dim(side, -width, eye, -5.2, f"total {width + eye:g}")
    dim(side, 0, s.CLIP_H, -width - 2.5, f"clip height {s.CLIP_H:g}", vertical=True)
    dim(side, 0, s.UP_H, eye + 2.0, f"eye height {s.UP_H:.2f}", vertical=True, text_right=True)
    dim(side, 0, s.EYE_END, s.UP_H + 1.3, f"opening {s.EYE_END:g}")
    dim(side, s.UP_RAIL, s.UP_RAIL + s.UP_IN_H, s.EYE_END / 2 + 1.6, f"{s.UP_IN_H:g}", vertical=True)

    outline(top, silhouette(clip, [0, 1]))
    frame(top, "Top view, looking down along the strap", (-37, 27), (-10, 9.5))
    dim(top, -width + s.CLIP_SIDE, -s.CLIP_SIDE, depth / 2 + 1.2, f"slot {s.SLOT_W:g}")
    dim(top, -width, -width + s.CLIP_SIDE, depth / 2 + 1.2, f"{s.CLIP_SIDE:g}")
    dim(top, -s.CLIP_SIDE, 0, depth / 2 + 1.2, f"{s.CLIP_SIDE:g}")
    dim(top, -width / 2 - s.SPLIT / 2, -width / 2 + s.SPLIT / 2, -depth / 2 - 1.2, f"split {s.SPLIT:g}")
    dim(top, -depth / 2, depth / 2, -width - 2.5, f"clip depth {depth:g}", vertical=True)
    dim(top, -s.SLOT_T / 2, s.SLOT_T / 2, -width / 2 + 6, f"{s.SLOT_T:g}", vertical=True, text_right=True)
    dim(top, -s.UP_T / 2, s.UP_T / 2, eye + 2.0, f"eye {s.UP_T:g}", vertical=True, text_right=True)
    top.text(-width / 2, depth / 2 + 4.2, "front (faces out)", color=INK, fontsize=9, ha="center")
    top.text(-width / 2 - 9, -depth / 2 - 2.2, "back (on the strap pad)", color=INK, fontsize=9, ha="center")
    webbing_note(top, -36, -8.6)
    top.text(-36, -6.9, "The first chain link (a flat link) runs through the eye. It is not shown.", color=INK, fontsize=9, va="top")

    fig.savefig(out / "left-clip.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def right_clip(out):
    clip = s.hook_clip()
    t, rise = s.HOOK_T, s.HOOK_THROAT
    reach = rise + 4 + s.HOOK_MOUTH
    width = s.SLOT_W + 2 * s.CLIP_SIDE
    depth = s.SLOT_T + 2 * s.CLIP_WALL
    tip_x, vertex_x = -s.HOOK_MOUTH, -reach + 4

    fig, (side, top) = plt.subplots(2, 1, figsize=(11, 10.5), dpi=140, gridspec_kw=dict(height_ratios=[1.25, 1]))
    fig.suptitle("Right clip with hook: sizes in mm", x=0.06, ha="left", fontsize=14, color=INK)

    outline(side, silhouette(clip, [0, 2]))
    frame(side, "Side view, as it sits on the strap (up is up)", (-27, 37), (-7.5, 20))
    dim(side, -reach, 0, -2.0, f"hook {reach:g}")
    dim(side, 0, width, -2.0, f"clip {width:g}")
    dim(side, -reach, width, -5.2, f"total {reach + width:g}")
    dim(side, 0, s.CLIP_H, width + 2.5, f"{s.CLIP_H:g}", vertical=True)
    side.text(width + 3.2, s.CLIP_H / 2, "clip height", color=DIM, fontsize=9, va="center")
    dim(side, 0, t + rise, -reach - 4.5, f"tip {t + rise:g}", vertical=True)
    dim(side, 0, t, -reach - 1.5, f"{t:g}", vertical=True)
    dim(side, vertex_x, tip_x, t + rise + 1.3, f"throat {rise:g}")
    dim(side, tip_x, 0, t + rise + 1.3, f"mouth {s.HOOK_MOUTH:g}")
    dim(side, -s.HOOK_RAMP, 0, t + s.HOOK_RAMP + 1.5, f"ramp {s.HOOK_RAMP:g}")

    outline(top, silhouette(clip, [0, 1]))
    frame(top, "Top view, looking down along the strap", (-27, 37), (-10, 9.5))
    dim(top, s.CLIP_SIDE, s.CLIP_SIDE + s.SLOT_W, depth / 2 + 1.2, f"slot {s.SLOT_W:g}")
    dim(top, 0, s.CLIP_SIDE, depth / 2 + 1.2, f"{s.CLIP_SIDE:g}")
    dim(top, width - s.CLIP_SIDE, width, depth / 2 + 1.2, f"{s.CLIP_SIDE:g}")
    dim(top, width / 2 - s.SPLIT / 2, width / 2 + s.SPLIT / 2, -depth / 2 - 1.2, f"split {s.SPLIT:g}")
    dim(top, -depth / 2, depth / 2, width + 2.5, f"{depth:g}", vertical=True)
    top.text(width + 3.2, 0, "clip depth", color=DIM, fontsize=9, va="center")
    dim(top, -s.SLOT_T / 2, s.SLOT_T / 2, width / 2 - 6, f"{s.SLOT_T:g}", vertical=True)
    dim(top, -t / 2, t / 2, -reach - 1.5, f"{t:g}", vertical=True)
    top.text(width / 2, depth / 2 + 4.2, "front (faces out)", color=INK, fontsize=9, ha="center")
    top.text(width / 2 + 9, -depth / 2 - 2.2, "back (on the strap pad)", color=INK, fontsize=9, ha="center")
    webbing_note(top, -26, -8.6)

    fig.savefig(out / "right-clip.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main(out=Path("docs/drawings")):
    out.mkdir(parents=True, exist_ok=True)
    left_clip(out)
    right_clip(out)


if __name__ == "__main__":
    main()
