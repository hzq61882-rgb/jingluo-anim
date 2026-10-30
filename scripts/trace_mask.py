#!/usr/bin/env python3
"""把粗折线吸到色带中线上，输出原图像素坐标。

rough.json：
{
  "taiyang": {"rgb": [225, 60, 40], "pts": [[400, 298], [190, 68]], "thr": 30}
}

  python scripts/trace_mask.py --image scan.jpg --rough rough.json --out paths.json
  python scripts/trace_mask.py --image scan.jpg --rough rough.json --out paths.json --overlay overlay.svg
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import dump_json, load_json  # noqa: E402
from geo import colmask, load_lab, pts_round, snap_mask  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description='色带中线吸附')
    parser.add_argument('--image', required=True)
    parser.add_argument('--rough', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--step', type=float, default=3.0)
    parser.add_argument('--passes', type=int, default=2)
    parser.add_argument('--overlay', help='可选，写出同像素坐标的 SVG')
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    lab = load_lab(args.image)
    rough = load_json(args.rough)
    out = {}
    for key, spec in rough.items():
        rgb = tuple(spec['rgb'])
        thr = spec.get('thr', 28)
        mask = colmask(lab, rgb, thr)
        pts = spec['pts']
        width = None
        for _ in range(args.passes):
            pts, width = snap_mask(mask, pts, rad=spec.get('rad', 24), maxshift=spec.get('maxshift', 24),
                                   step=args.step, keep_ends=spec.get('keep_ends', False))
        rounded = pts_round(pts, spec.get('round_step', 3))
        out[key] = {'pts': rounded, 'w': round(float(width), 2), 'rgb': list(rgb)}
        print(f'{key}  width {width:.1f}  points {len(rounded)}')
    dump_json(args.out, out)
    if args.overlay:
        from overlay import write_svg
        write_svg(args.overlay, paths=out, image=args.image)
        print('overlay', args.overlay)


if __name__ == '__main__':
    main()
