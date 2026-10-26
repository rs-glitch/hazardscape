"""python test_raster.py -- scanline fill gives exact areas (square with a hole, and a triangle)."""
import numpy as np

from build_fire import fill_rings

sq = np.array([[10, 10], [90, 10], [90, 90], [10, 90], [10, 10]], float)
hole = np.array([[30, 30], [50, 30], [50, 50], [30, 50], [30, 30]], float)
assert fill_rings([sq, hole], 100, 100).sum() == 80 * 80 - 20 * 20
tri = np.array([[0, 0], [200, 0], [0, 200], [0, 0]], float)
a = fill_rings([tri], 200, 200).sum()
assert abs(a / (200 * 200 / 2) - 1) < 0.01, a
wiggle = np.array([[50 + 30 * np.cos(t) * (1 + 0.2 * np.sin(40 * t)), 50 + 30 * np.sin(t) * (1 + 0.2 * np.sin(40 * t))]
                   for t in np.linspace(0, 2 * np.pi, 4001)])
true = 0.5 * abs(np.dot(wiggle[:-1, 0], wiggle[1:, 1]) - np.dot(wiggle[1:, 0], wiggle[:-1, 1]))   # shoelace
got = fill_rings([wiggle], 100, 100).sum()
assert abs(got / true - 1) < 0.01, (got, true)
print("raster ok", got, round(true, 1))
