"""Render shaded preview PNGs of the exported STLs into out/ (not tracked)."""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import trimesh
from mpl_toolkits.mplot3d.art3d import Poly3DCollection


def render(stl, png, elev, azim, xlim=None):
    m = trimesh.load(stl)
    tris = m.triangles
    if xlim:
        cx = tris[:, :, 0].mean(axis=1)
        keep = (cx > xlim[0]) & (cx < xlim[1])
        tris, normals = tris[keep], m.face_normals[keep]
    else:
        normals = m.face_normals
    light = np.array([0.3, -0.5, 0.8])
    light /= np.linalg.norm(light)
    shade = 0.35 + 0.65 * np.clip(normals @ light, 0, 1)
    colors = np.stack([shade * 0.55, shade * 0.6, shade * 0.7, np.ones_like(shade)], axis=1)
    fig = plt.figure(figsize=(14, 7), dpi=110)
    ax = fig.add_subplot(projection="3d")
    ax.add_collection3d(Poly3DCollection(tris, facecolors=colors, edgecolors="none"))
    lo, hi = tris.reshape(-1, 3).min(axis=0), tris.reshape(-1, 3).max(axis=0)
    ax.set_xlim(lo[0], hi[0]); ax.set_ylim(lo[1], hi[1]); ax.set_zlim(lo[2], hi[2])
    ax.set_box_aspect(hi - lo)
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()
    fig.savefig(png, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    out = Path("out")
    out.mkdir(exist_ok=True)
    left, right = Path("output/left-clip-with-chain.stl"), Path("output/right-clip-with-hook.stl")
    render(left, out / "preview-left-full.png", 35, -70)
    render(left, out / "preview-left-detail.png", 30, -60, xlim=(-30, 45))
    render(left, out / "preview-chain-side.png", 4, -90, xlim=(-5, 45))
    render(right, out / "preview-right.png", 25, -110)
    render(right, out / "preview-right-side.png", 0, -90)
    render(Path("test-prints/test-left-clip.stl"), out / "preview-test-left-clip.png", 35, -65)
    render(Path("test-prints/test-chain-only.stl"), out / "preview-test-chain-only.png", 35, -65)
