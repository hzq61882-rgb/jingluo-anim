#!/usr/bin/env python3
"""在一批色点上拟合圆弧。guesses.json 给出初值，结果仍是原图像素。

[
  {"name": "outer", "c": [270, 400], "r": 236, "tol": 12}
]

可选 --exclude，圆心列表，拟合前丢掉这些圆附近的点（脏腑小圆、五行大圆）。

  python scripts/trace_arcs.py --image scan.jpg --guesses guesses.json --out arcs.json
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    import cv2
    import numpy as np
except ImportError as exc:
    raise SystemExit('需要 opencv-python-headless 和 numpy：pip install -r scripts/requirements.txt') from exc

from common import dump_json, load_json  # noqa: E402


def fit(points, centre, radius, tol, rounds=5):
    centre = np.array(centre, float)
    selected = None
    for _ in range(rounds):
        dist = np.hypot(points[:, 0] - centre[0], points[:, 1] - centre[1])
        selected = np.abs(dist - radius) < tol
        chosen = points[selected]
        if len(chosen) < 6:
            break
        design = np.c_[2 * chosen[:, 0], 2 * chosen[:, 1], np.ones(len(chosen))]
        target = (chosen ** 2).sum(1)
        solution = np.linalg.lstsq(design, target, rcond=None)[0]
        centre = solution[:2]
        radius = math.sqrt(max(0.0, solution[2] + centre @ centre))
    chosen = points[selected] if selected is not None else points[:0]
    if len(chosen) == 0:
        return centre, radius, []
    ang = np.degrees(np.arctan2(chosen[:, 1] - centre[1], chosen[:, 0] - centre[0]))
    return centre, radius, [round(float(v), 1) for v in np.percentile(ang, [0, 1, 50, 99, 100])]


def main(argv=None):
    parser = argparse.ArgumentParser(description='拟合圆弧')
    parser.add_argument('--image', required=True)
    parser.add_argument('--guesses', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--exclude', help='[[x, y, r], ...] 拟合前排除的圆')
    parser.add_argument('--exclude-pad', type=float, default=0)
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    image = cv2.imread(args.image)
    if image is None:
        raise SystemExit(f'打不开图片：{args.image}')
    image = image.astype(int)
    blue, green, red = image[..., 0], image[..., 1], image[..., 2]
    mask = (red - blue > 50) & (red > 100) & (red < 235) & (green < 170) & (green - blue > 10)
    ys, xs = np.nonzero(mask)
    points = np.c_[xs, ys].astype(float)
    if args.exclude:
        for item in load_json(args.exclude):
            x, y, radius = item[:3]
            points = points[np.hypot(points[:, 0] - x, points[:, 1] - y) > radius + args.exclude_pad]
    results = []
    for guess in load_json(args.guesses):
        centre, radius, ang = fit(points, guess['c'], guess['r'], guess.get('tol', 12))
        item = {
            'name': guess.get('name', ''),
            'c': [round(float(centre[0]), 1), round(float(centre[1]), 1)],
            'r': round(float(radius), 1),
            'angles': ang,
        }
        results.append(item)
        print(item)
    dump_json(args.out, results)


if __name__ == '__main__':
    main()
