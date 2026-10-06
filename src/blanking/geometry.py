"""Geometry of a staggered circle-blanking layout.

Circles of diameter ``D`` are punched in ``k`` lanes running along the coil.
Neighbouring blanks must be at least ``s = D + bridge`` apart (centre to
centre), and every blank must stay ``edge`` mm inside the strip edge.

The *blanking angle* θ is the angle between the coil's rolling direction and
the line joining the centres of neighbouring blanks in adjacent lanes:

    lane spacing (across width) = s·sin θ
    pitch (along coil)          = max(s, 2·s·cos θ)
    lane j is shifted by        j·s·cos θ  (mod pitch)

θ = 60° is hexagonal packing (θ = 30° is the same packing rotated, with a
narrower strip and longer pitch); θ = 90° is a square grid. Below 30° blanks two
lanes apart would overlap, so θ is limited to [30°, 90°]. For θ ≥ 60° the
pitch is the minimum ``s``; smaller angles trade a longer pitch for a narrower
strip, which is what lets an extra lane fit onto a given coil width.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

AL_DENSITY_KG_MM3 = 2.70e-6  # aluminium, 2.70 g/cm^3


@dataclass(frozen=True)
class Layout:
    diameter: float
    bridge: float
    edge: float
    lanes: int
    angle_deg: float
    coil_width: float

    @property
    def spacing(self) -> float:
        return self.diameter + self.bridge

    @property
    def _theta(self):
        return math.radians(self.angle_deg)

    @property
    def lane_spacing(self) -> float:
        return self.spacing * math.sin(self._theta) if self.lanes > 1 else 0.0

    @property
    def pitch(self) -> float:
        if self.lanes == 1:
            return self.spacing
        return max(self.spacing, 2 * self.spacing * math.cos(self._theta))

    @property
    def width_used(self) -> float:
        """Strip width needed, including both edge allowances."""
        return 2 * self.edge + self.diameter + (self.lanes - 1) * self.lane_spacing

    @property
    def side_scrap(self) -> float:
        return self.coil_width - self.width_used

    @property
    def feasible(self) -> bool:
        ok_angle = self.lanes == 1 or 30.0 - 1e-9 <= self.angle_deg <= 90.0 + 1e-9
        return ok_angle and self.width_used <= self.coil_width + 1e-9

    @property
    def blank_area(self) -> float:
        return math.pi * self.diameter ** 2 / 4

    @property
    def recovery(self) -> float:
        """Steady-state material recovery: blank area / strip area consumed."""
        return self.lanes * self.blank_area / (self.coil_width * self.pitch)

    @property
    def blanks_per_metre(self) -> float:
        return self.lanes * 1000.0 / self.pitch

    def lane_offsets(self) -> np.ndarray:
        if self.lanes == 1:
            return np.zeros(1)
        shift = self.spacing * math.cos(self._theta)
        return np.mod(np.arange(self.lanes) * shift, self.pitch)

    def centres(self, length: float) -> np.ndarray:
        """All blank centres (x along coil, y across) on a strip of ``length`` mm."""
        r = self.diameter / 2
        y0 = (self.coil_width - self.width_used) / 2 + self.edge + r  # centre the pattern
        pts = []
        for j, off in enumerate(self.lane_offsets()):
            xs = np.arange(r + off, length - r + 1e-9, self.pitch)
            pts.append(np.column_stack([xs, np.full_like(xs, y0 + j * self.lane_spacing)]))
        return np.vstack(pts) if pts else np.zeros((0, 2))

    def blanks_from_length(self, length: float, head_tail: float = 0.0) -> int:
        usable = length - head_tail
        if usable < self.diameter:
            return 0
        n = np.floor((usable - self.diameter - self.lane_offsets()) / self.pitch) + 1
        return int(np.clip(n, 0, None).sum())

    def coil_length(self, coil_kg: float, thickness: float) -> float:
        """Length (mm) of a coil of given mass, width and thickness."""
        return coil_kg / (AL_DENSITY_KG_MM3 * self.coil_width * thickness)


def layout(diameter, bridge, edge, lanes, angle_deg, coil_width) -> Layout:
    return Layout(float(diameter), float(bridge), float(edge), int(lanes), float(angle_deg), float(coil_width))


def best_angle(diameter, bridge, edge, lanes, coil_width, min_angle=30.0, max_angle=90.0):
    """Closed-form optimum angle for fixed lanes and width (used to check the
    grid search): the smallest pitch whose layout still fits the width."""
    s = diameter + bridge
    if lanes == 1:
        return 90.0 if diameter + 2 * edge <= coil_width else None
    room = (coil_width - 2 * edge - diameter) / ((lanes - 1) * s)
    if room <= 0:
        return None
    theta_fit = 90.0 if room >= 1 else math.degrees(math.asin(room))
    hi = min(theta_fit, max_angle)
    if hi < max(30.0, min_angle):
        return None
    return min(max(60.0, min_angle), hi) if hi >= 60.0 else hi
