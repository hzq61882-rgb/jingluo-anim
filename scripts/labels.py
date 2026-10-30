#!/usr/bin/env python3
"""标签：原图像素坐标上的标准字体文字。

labels.json 每条是对象，或七元数组 [x, y, size, rotate, weight, text, kind]。
kind 为 cjk、latin、italic。weight 400 或 700。rotate 为度，顺时针在 SVG 里为正。

  python scripts/labels.py check --labels labels.json
  python scripts/labels.py preview --image src.jpg --labels labels.json --out preview.svg
  python scripts/labels.py subset --labels labels.json --template template/template.html --out-dir fonts/
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import dump_json, find_cjk_font, load_json, normalize_label, subset_woff2  # noqa: E402


def collect(path):
    data = load_json(path)
    if isinstance(data, dict) and 'labels' in data:
        data = data['labels']
    return [normalize_label(item) for item in data]


def cmd_check(args):
    labels = collect(args.labels)
    kinds = {}
    for label in labels:
        kinds[label['kind']] = kinds.get(label['kind'], 0) + 1
        if not label['text']:
            raise SystemExit('有空文本标签')
    chars = ''.join(sorted({c for label in labels for c in label['text']}))
    print(f'{len(labels)} labels  kinds {kinds}')
    print('chars', chars)


def cmd_preview(args):
    labels = collect(args.labels)
    if args.image:
        try:
            from PIL import Image
        except ImportError as exc:
            raise SystemExit('需要 pillow：pip install -r scripts/requirements.txt') from exc
        with Image.open(args.image) as im:
            width, height = im.size
    else:
        width = args.width
        height = args.height
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
    ]
    if args.image:
        name = Path(args.image).name
        lines.append(f'<image href="{name}" x="0" y="0" width="{width}" height="{height}"/>')
    for index, label in enumerate(labels):
        text = (label['text'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))
        weight = label['weight']
        style = 'italic' if label['kind'] == 'italic' else 'normal'
        lines.append(
            f'<g transform="translate({label["x"]:.1f},{label["y"]:.1f}) rotate({label["rotate"]:.1f})">'
            f'<text text-anchor="middle" dominant-baseline="central" font-size="{label["size"]}" '
            f'font-weight="{weight}" font-style="{style}" fill="#c0392b">{text}</text>'
            f'<circle r="1.4" fill="#1a7f37"/>'
            f'<title>{index} {text}</title></g>'
        )
    lines.append('</svg>')
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'wrote {out}  {len(labels)} labels  {width}×{height}')


def cmd_subset(args):
    parts = []
    if args.labels:
        parts.append(''.join(label['text'] for label in collect(args.labels)))
    if args.template:
        parts.append(Path(args.template).read_text(encoding='utf-8'))
    if args.text_file:
        parts.append(Path(args.text_file).read_text(encoding='utf-8'))
    text = ''.join(parts)
    out_dir = Path(args.out_dir)
    regular = find_cjk_font(400, args.font_regular)
    bold = find_cjk_font(700, args.font_bold)
    subset_woff2(text, regular, out_dir / 'noto_400.woff2', args.font_index)
    subset_woff2(text, bold, out_dir / 'noto_700.woff2', args.font_index)
    chars = ''.join(sorted({c for c in text if ord(c) >= 32}))
    (out_dir / 'subset_chars.txt').write_text(chars, encoding='utf-8')
    print(f'wrote {out_dir}/noto_400.woff2  {out_dir}/noto_700.woff2  {len(chars)} chars')


def cmd_normalize(args):
    labels = collect(args.labels)
    dump_json(args.out, labels)
    print(f'wrote {args.out}  {len(labels)}')


def main(argv=None):
    parser = argparse.ArgumentParser(description='标签检查、预览与字体子集')
    sub = parser.add_subparsers(dest='cmd', required=True)

    check = sub.add_parser('check')
    check.add_argument('--labels', required=True)
    check.set_defaults(func=cmd_check)

    preview = sub.add_parser('preview')
    preview.add_argument('--labels', required=True)
    preview.add_argument('--image', help='扫描图，SVG 按它的像素尺寸叠字')
    preview.add_argument('--width', type=int, default=595)
    preview.add_argument('--height', type=int, default=808)
    preview.add_argument('--out', required=True)
    preview.set_defaults(func=cmd_preview)

    subset = sub.add_parser('subset')
    subset.add_argument('--labels')
    subset.add_argument('--template')
    subset.add_argument('--text-file')
    subset.add_argument('--out-dir', required=True)
    subset.add_argument('--font-regular')
    subset.add_argument('--font-bold')
    subset.add_argument('--font-index', type=int, default=3)
    subset.set_defaults(func=cmd_subset)

    norm = sub.add_parser('normalize', help='把七元数组收成对象数组')
    norm.add_argument('--labels', required=True)
    norm.add_argument('--out', required=True)
    norm.set_defaults(func=cmd_normalize)

    args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    args.func(args)


if __name__ == '__main__':
    main()
