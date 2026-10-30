#!/usr/bin/env python3
"""把断开的短虚线墨迹串成折线。

  python scripts/trace_dashes.py --image scan.jpg --out dashes.json
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    import cv2
    import numpy as np
except ImportError as exc:
    raise SystemExit('需要 opencv-python-headless 和 numpy：pip install -r scripts/requirements.txt') from exc

from common import dump_json  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description='串连虚线墨迹')
    parser.add_argument('--image', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--min-area', type=int, default=12)
    parser.add_argument('--max-area', type=int, default=220)
    parser.add_argument('--gap', type=float, default=17, help='两段端点最远距离')
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    image = cv2.imread(args.image)
    if image is None:
        raise SystemExit(f'打不开图片：{args.image}')
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).astype(int)
    sat = np.max(image, 2).astype(int) - np.min(image, 2)
    mask = ((gray < 130) & (sat < 60)).astype(np.uint8)
    count, lab, stats, _cent = cv2.connectedComponentsWithStats(mask, 8)
    dashes = []
    for index in range(1, count):
        _x, _y, w, h, area = stats[index]
        length = max(w, h)
        if not (args.min_area <= area <= args.max_area and 7 <= length <= 32):
            continue
        ys, xs = np.nonzero(lab == index)
        points = np.c_[xs, ys].astype(float)
        centre = points.mean(0)
        values, vectors = np.linalg.eigh(np.cov(points.T))
        if values[1] <= 5 * max(values[0], 0.3):
            continue
        direction = vectors[:, 1]
        proj = (points - centre) @ direction
        dashes.append(dict(c=centre, u=direction, e0=centre + direction * proj.min(), e1=centre + direction * proj.max()))

    def best_link(index, end):
        dash = dashes[index]
        origin = dash['e1'] if end == 1 else dash['e0']
        forward = dash['u'] if end == 1 else -dash['u']
        best = None
        for other_index, other in enumerate(dashes):
            if other_index == index:
                continue
            for other_end, point in ((0, other['e0']), (1, other['e1'])):
                delta = point - origin
                dist = np.linalg.norm(delta)
                if dist < 3 or dist > args.gap:
                    continue
                if delta @ forward / dist < 0.88:
                    continue
                other_dir = other['u'] if other_end == 0 else -other['u']
                if other_dir @ forward < 0.85:
                    continue
                score = dist * (2 - delta @ forward / dist)
                if best is None or score < best[0]:
                    best = (score, other_index, other_end)
        return best

    nxt = {}
    for index in range(len(dashes)):
        for end in (0, 1):
            link = best_link(index, end)
            if link:
                nxt[(index, end)] = (link[1], link[2])

    used = set()
    chains = []
    for index in range(len(dashes)):
        if index in used:
            continue
        chain = [(index, 1)]
        used.add(index)
        for direction in (1, 0):
            current = (index, direction)
            seq = []
            while True:
                if current not in nxt:
                    break
                other, other_end = nxt[current]
                if other in used:
                    break
                back = nxt.get((other, other_end))
                if not back or back[0] != current[0]:
                    break
                used.add(other)
                seq.append((other, 1 - other_end))
                current = (other, 1 - other_end)
            if direction == 1:
                chain = chain + seq
            else:
                chain = [(j, 1 - e) for j, e in seq[::-1]] + chain
        if len(chain) >= 3:
            chains.append(chain)

    out = []
    for chain in chains:
        pts = []
        for index, end in chain:
            dash = dashes[index]
            start, finish = (dash['e0'], dash['e1']) if end == 1 else (dash['e1'], dash['e0'])
            pts += [start.tolist(), finish.tolist()]
        out.append([[round(x, 1), round(y, 1)] for x, y in pts])
    dump_json(args.out, out)
    print(f'{len(dashes)} dash pieces -> {len(out)} chains')


if __name__ == '__main__':
    main()
