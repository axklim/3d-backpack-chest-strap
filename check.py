"""Sanity checks: every solid is valid and neighbours keep a printable gap."""
import strap

MIN_GAP = 0.4
p = strap.build()
solids = [p["chain_clip"], *p["links"]]
ok = True
for i, s in enumerate([*solids, p["hook_clip"]]):
    n = len(s.solids())
    if n != 1 or s.volume <= 0:
        ok = False
        print(f"solid {i}: {n} bodies, volume {s.volume:.1f}")
for i in range(len(solids) - 1):
    for j in (i + 1, i + 2):
        if j >= len(solids):
            continue
        d = solids[i].distance_to(solids[j])
        if d < MIN_GAP:
            ok = False
            print(f"gap {i}-{j}: {d:.2f} mm")
gaps = [solids[i].distance_to(solids[i + 1]) for i in range(3)]
print("first gaps:", [round(g, 2) for g in gaps])
bb = p["links"][1].bounding_box()
print("flat link bbox:", [round(v, 2) for v in (bb.size.X, bb.size.Y, bb.size.Z)])
free_l = strap.LINK_IN_L - 2 * strap.WIRE
for name, short in (("flat", strap.LINK_IN_W), ("upright", strap.UP_IN_H)):
    play = (short - strap.HOOK_T) / 2
    print(f"hook in a middle {name} link: opening {free_l:.1f} x {short:.1f}, play {play:.1f} mm per side")
    if play < 0.7 or free_l < 4 + 2 * strap.WIRE:
        ok = False
if strap.HOOK_THROAT < 3 * strap.WIRE + 1:
    ok = False
    print("hook throat too shallow for two link bars")
if strap.HOOK_T + strap.HOOK_THROAT > strap.CLIP_H:
    ok = False
    print("hook tip is higher than the clip")
levels = {
    "FLAT_T": strap.FLAT_T, "UP_RAIL": strap.UP_RAIL, "Z_BAR": strap.Z_BAR,
    "bar top": strap.Z_BAR + strap.BAR_T, "upright opening top": strap.UP_RAIL + strap.UP_IN_H,
    "UP_H": strap.UP_H,
}
for name, z in levels.items():
    n = (z - strap.FIRST_LAYER) / strap.LAYER
    if abs(n - round(n)) > 1e-6:
        ok = False
        print(f"{name} ({z:.3f}) is not on a layer boundary")
if strap.GAP_Z < 0.6 - 1e-9:
    ok = False
    print("GAP_Z below 0.6")
print(f"layer {strap.LAYER}: gap {strap.GAP_Z:.2f} = {strap.GAP_Z / strap.LAYER:.0f} layers, upright link {strap.UP_H:.2f} high")
print("OK" if ok else "FAILED")
