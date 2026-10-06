import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle

from .geometry import Layout


def draw_layout(L: Layout, length: float | None = None, ax=None):
    length = length or 4 * L.pitch + L.diameter
    ax = ax or plt.subplots(figsize=(9, 9 * L.coil_width / length if length else 3))[1]
    ax.add_patch(Rectangle((0, 0), length, L.coil_width, fc="#d9dde1", ec="#5b6670"))
    off = (L.coil_width - L.width_used) / 2
    ax.axhspan(off, off + L.edge, color="#f4c7a1", alpha=.6, lw=0)
    ax.axhspan(L.coil_width - off - L.edge, L.coil_width - off, color="#f4c7a1", alpha=.6, lw=0)
    for x, y in L.centres(length):
        ax.add_patch(Circle((x, y), L.diameter / 2, fc="#2f6f8f", ec="white", lw=.8))
    ax.set_xlim(0, length); ax.set_ylim(0, L.coil_width); ax.set_aspect("equal")
    ax.set_xlabel("along coil (mm)"); ax.set_ylabel("across coil (mm)")
    ax.set_title(f"{L.lanes} lane(s) at {L.angle_deg:g}°, pitch {L.pitch:.1f} mm, "
                 f"recovery {L.recovery:.1%}")
    return ax
