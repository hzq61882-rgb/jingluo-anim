#!/usr/bin/env python3
"""把描好的圆、弧、折线叠回扫描图，坐标就是原图像素，不缩放。

  python scripts/overlay.py --image scan.jpg --paths paths.json --circles circles.json --labels labels.json --out overlay.svg

paths.json 可以是 {名字: {pts: [[x,y], ...]}}，或 {名字: [[x,y], ...]}，或 [折线, 折线]。
circles.json 可以是 [{x,y,r,t}] 或 [[x,y,r], ...]。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import load_json  # noqa: E402


def _polylines(data):
    if data is None:
        return []
    if isinstance(data, list):
        if not data:
            return []
        if isinstance(data[0], dict) and 'pts' in data[0]:
            return [(item.get('n') or item.get('name') or '', item['pts']) for item in data]
        if isinstance(data[0], (list, tuple)) and data[0] and isinstance(data[0][0], (list, tuple)):
            return [(str(i), line) for i, line in enumerate(data)]
        return []
    lines = []
    for key, value in data.items():
        if isinstance(value, dict) and 'pts' in value:
            lines.append((key, value['pts']))
        elif isinstance(value, list) and value and isinstance(value[0], (list, tuple)):
            lines.append((key, value))
    return lines


def _circles(data):
    if not data:
        return []
    out = []
    for item in data:
        if isinstance(item, dict):
            out.append((float(item.get('x', item.get('cx'))), float(item.get('y', item.get('cy'))),
                        float(item.get('r', 8)), str(item.get('t') or item.get('text') or '')))
        else:
            x, y, r = item[:3]
            text = str(item[3]) if len(item) > 3 and isinstance(item[3], str) else ''
            out.append((float(x), float(y), float(r), text))
    return out


def _labels(data):
    if not data:
        return []
    if isinstance(data, dict) and 'labels' in data:
        data = data['labels']
    out = []
    for item in data:
        if isinstance(item, dict):
            out.append((float(item['x']), float(item['y']), str(item.get('text', item.get('t', '')))))
        elif isinstance(item, (list, tuple)) and len(item) >= 6:
            out.append((float(item[0]), float(item[1]), str(item[5])))
    return out


def write_svg(out, paths=None, circles=None, labels=None, image=None, width=None, height=None):
    if image and (width is None or height is None):
        try:
            from PIL import Image
        except ImportError as exc:
            raise SystemExit('读取图片尺寸需要 pillow') from exc
        with Image.open(image) as im:
            width, height = im.size
    width = width or 595
    height = height or 808
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
    ]
    if image:
        name = Path(image).name
        parts.append(f'<image href="{name}" x="0" y="0" width="{width}" height="{height}"/>')
    for name, pts in _polylines(paths):
        if len(pts) < 2:
            continue
        numbers = ' '.join(f'{float(x):.1f},{float(y):.1f}' for x, y in pts)
        title = f'<title>{name}</title>' if name else ''
        parts.append(f'<polyline points="{numbers}" fill="none" stroke="#00bcd4" stroke-width="1.4">{title}</polyline>')
        x, y = pts[0]
        parts.append(f'<circle cx="{float(x):.1f}" cy="{float(y):.1f}" r="2.2" fill="#1a7f37"/>')
    for x, y, r, text in _circles(circles):
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="none" stroke="#c0392b" stroke-width="1"/>')
        if text:
            safe = text.replace('&', '&amp;').replace('<', '&lt;')
            parts.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{max(8, r * 0.7):.1f}" text-anchor="middle" dominant-baseline="central">{safe}</text>')
    for x, y, text in _labels(labels):
        safe = text.replace('&', '&amp;').replace('<', '&lt;')
        parts.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="11" fill="#6B3A8C" text-anchor="middle">{safe}</text>')
    parts.append('</svg>')
    path = Path(out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('\n'.join(parts) + '\n', encoding='utf-8')


def main(argv=None):
    parser = argparse.ArgumentParser(description='SVG 叠图，坐标为原图像素')
    parser.add_argument('--out', required=True)
    parser.add_argument('--image')
    parser.add_argument('--paths')
    parser.add_argument('--circles')
    parser.add_argument('--labels')
    parser.add_argument('--width', type=int)
    parser.add_argument('--height', type=int)
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    write_svg(
        args.out,
        paths=load_json(args.paths) if args.paths else None,
        circles=load_json(args.circles) if args.circles else None,
        labels=load_json(args.labels) if args.labels else None,
        image=args.image,
        width=args.width,
        height=args.height,
    )
    print('wrote', args.out)


if __name__ == '__main__':
    main()
