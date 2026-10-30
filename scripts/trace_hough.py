#!/usr/bin/env python3
"""霍夫变换抽出长直线，合并近乎共线的段。

  python scripts/trace_hough.py --image scan.jpg --out lines.json --margin 52,40,50,73
margin 是左、上、右、下要忽略的页边，避免外框被当成经络。
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

from common import dump_json  # noqa: E402


def angle(seg):
    return math.degrees(math.atan2(seg[3] - seg[1], seg[2] - seg[0])) % 180


def main(argv=None):
    parser = argparse.ArgumentParser(description='霍夫直线')
    parser.add_argument('--image', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--min-length', type=int, default=45)
    parser.add_argument('--max-gap', type=int, default=4)
    parser.add_argument('--threshold', type=int, default=30)
    parser.add_argument('--margin', default='', help='left,top,right,bottom 页边，像素')
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    image = cv2.imread(args.image)
    if image is None:
        raise SystemExit(f'打不开图片：{args.image}')
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).astype(int)
    sat = np.max(image, 2).astype(int) - np.min(image, 2)
    mask = ((gray < 150) & (sat < 60)).astype(np.uint8) * 255
    if args.margin:
        left, top, right, bottom = [int(v) for v in args.margin.split(',')]
        height, width = mask.shape
        if left:
            mask[:, :left] = 0
        if right:
            mask[:, width - right:] = 0
        if top:
            mask[:top, :] = 0
        if bottom:
            mask[height - bottom:, :] = 0
    raw = cv2.HoughLinesP(mask, 1, np.pi / 360, threshold=args.threshold,
                          minLineLength=args.min_length, maxLineGap=args.max_gap)
    if raw is None:
        dump_json(args.out, [])
        print('0 lines')
        return
    segments = [list(map(int, seg)) for seg in np.array(raw).reshape(-1, 4)]
    merged = []
    for seg in sorted(segments, key=lambda s: -math.hypot(s[2] - s[0], s[3] - s[1])):
        ang = angle(seg)
        placed = False
        for item in merged:
            if min(abs(ang - item['a']), 180 - abs(ang - item['a'])) >= 3:
                continue
            x1, y1, x2, y2 = item['p']
            length = math.hypot(x2 - x1, y2 - y1) or 1
            def dist(x, y):
                return abs((x2 - x1) * (y1 - y) - (x1 - x) * (y2 - y1)) / length
            if dist(seg[0], seg[1]) >= 3 or dist(seg[2], seg[3]) >= 3:
                continue
            ux, uy = (x2 - x1) / length, (y2 - y1) / length
            projections = [0, length,
                           (seg[0] - x1) * ux + (seg[1] - y1) * uy,
                           (seg[2] - x1) * ux + (seg[3] - y1) * uy]
            gap = max(0, min(projections[2], projections[3]) - length, -max(projections[2], projections[3]))
            if gap < 6:
                t0, t1 = min(projections), max(projections)
                item['p'] = [x1 + ux * t0, y1 + uy * t0, x1 + ux * t1, y1 + uy * t1]
                placed = True
                break
        if not placed:
            merged.append({'a': ang, 'p': [float(v) for v in seg]})
    out = [[round(v, 1) for v in item['p']] for item in merged]
    dump_json(args.out, out)
    print(f'{len(out)} lines')


if __name__ == '__main__':
    main()
