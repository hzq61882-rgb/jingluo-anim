#!/usr/bin/env python3
"""把直线或二次曲线的草图端点吸到深色墨线上。

strokes.json：
[
  {"name": "V170", "type": "L", "pts": [[170, 177], [170, 569]]},
  {"name": "C_心包三焦", "type": "Q", "pts": [[183, 223], [207, 222], [215, 247]]}
]

  python scripts/trace_strokes.py --image scan.jpg --strokes strokes.json --out lines.json
"""
from __future__ import annotations

import argparse
import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    import cv2
    import numpy as np
except ImportError as exc:
    raise SystemExit('需要 opencv-python-headless 和 numpy：pip install -r scripts/requirements.txt') from exc

from common import dump_json, load_json  # noqa: E402


def quad(p0, control, p1, n=60):
    t = np.linspace(0, 1, n)[:, None]
    p0, control, p1 = map(np.array, (p0, control, p1))
    return (1 - t) ** 2 * p0 + 2 * (1 - t) * t * control + t * t * p1


def line(a, b, n=None):
    n = n or int(np.hypot(b[0] - a[0], b[1] - a[1])) + 1
    t = np.linspace(0, 1, max(2, n))[:, None]
    return (1 - t) * np.array(a) + t * np.array(b)


def main(argv=None):
    parser = argparse.ArgumentParser(description='直线 / 二次曲线吸附到墨线')
    parser.add_argument('--image', required=True)
    parser.add_argument('--strokes', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--line-radius', type=int, default=3)
    parser.add_argument('--quad-radius', type=int, default=4)
    parser.add_argument('--control-radius', type=int, default=10)
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    img = cv2.imread(args.image)
    if img is None:
        raise SystemExit(f'打不开图片：{args.image}')
    height, width = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(float)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    ink = np.clip((200 - gray) / 120, 0, 1) * (hsv[..., 1] < 100)
    ink_blur = cv2.GaussianBlur(ink, (3, 3), 0.8)
    ink_dilate = cv2.dilate(ink, np.ones((3, 3)))

    def sample(points, field=ink_blur):
        x = np.clip(points[:, 0], 0, width - 1).round().astype(int)
        y = np.clip(points[:, 1], 0, height - 1).round().astype(int)
        return field[y, x]

    def cover(points):
        return float((sample(points, ink_dilate) > 0.4).mean())

    def snap_line(a, b, radius):
        best = None
        for dx1, dy1, dx2, dy2 in itertools.product(range(-radius, radius + 1), repeat=4):
            start = (a[0] + dx1, a[1] + dy1)
            end = (b[0] + dx2, b[1] + dy2)
            score = sample(line(start, end)).mean()
            if best is None or score > best[0]:
                best = (score, start, end)
        return best

    def snap_quad(a, control, b):
        best = None
        for dx1, dy1, dx2, dy2 in itertools.product(range(-args.quad_radius, args.quad_radius + 1, 2), repeat=4):
            start = (a[0] + dx1, a[1] + dy1)
            end = (b[0] + dx2, b[1] + dy2)
            for cx, cy in itertools.product(range(-args.control_radius, args.control_radius + 1, 2), repeat=2):
                ctrl = (control[0] + cx, control[1] + cy)
                score = sample(quad(start, ctrl, end)).mean()
                if best is None or score > best[0]:
                    best = (score, start, ctrl, end)
        return best

    results = []
    for stroke in load_json(args.strokes):
        kind = stroke.get('type', 'L')
        name = stroke.get('name', '')
        pts = stroke['pts']
        if kind == 'L':
            score, start, end = snap_line(pts[0], pts[1], stroke.get('radius', args.line_radius))
            item = dict(n=name, t='L', p=[list(map(float, start)), list(map(float, end))],
                        score=round(float(score), 3), cov=round(cover(line(start, end)), 2))
        elif kind == 'Q':
            score, start, ctrl, end = snap_quad(pts[0], pts[1], pts[2])
            item = dict(n=name, t='Q', p=[list(map(float, start)), list(map(float, ctrl)), list(map(float, end))],
                        score=round(float(score), 3), cov=round(cover(quad(start, ctrl, end)), 2))
        else:
            raise SystemExit(f'未知 type {kind}（用 L 或 Q）')
        results.append(item)
        print(item['n'], item['t'], 'score', item['score'], 'cov', item['cov'])
    dump_json(args.out, results)


if __name__ == '__main__':
    main()
