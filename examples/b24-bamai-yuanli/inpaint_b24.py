#!/usr/bin/env python3
"""B/24 专用：擦掉说明框里的手写，保住细弧和下划线。

通用 scripts/inpaint.py 在这张图上会留残字，也会把色带涂糊。
这里按 boxes.json 的矩形处理：dark / in 找深色字，cap 先丢掉又宽又长的笔画再修补，
最后把说明框刷白，只把长下划线从原图拷回。

原扫描和 boxes.json 不在仓库里。examples/b24-bamai-yuanli/clean.jpg
就是这支脚本放大 2 倍之后的结果（1190×1616），重建动画直接用它。

  python examples/b24-bamai-yuanli/inpaint_b24.py \
    --image b24.jpg --boxes boxes.json --out b24_clean.png --scale 2 --scaled-out clean.jpg
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import cv2
    import numpy as np
    from scipy import ndimage as ndi
except ImportError as exc:
    raise SystemExit('需要 opencv、numpy、scipy：pip install -r scripts/requirements.txt') from exc


def parse_args(argv):
    p = argparse.ArgumentParser(description='B/24：擦说明文字，保住细线')
    p.add_argument('--image', required=True, help='原始扫描')
    p.add_argument('--boxes', required=True, help='{"名字": [x0, y0, x1, y1, mode]}，mode 为 dark / in / cap / white')
    p.add_argument('--out', required=True, help='擦完的图，与扫描同尺寸')
    p.add_argument('--scale', type=float, default=0, help='再写出一张放大图。B/24 成片底图是 2')
    p.add_argument('--scaled-out', default=None, help='放大图路径。给了 --scale 就必填')
    return p.parse_args(argv)


def clean(image, boxes):
    gray = image.mean(-1)
    mask = np.zeros(gray.shape, np.uint8)
    for _name, (x0, y0, x1, y1, mode) in boxes.items():
        x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
        if mode != 'in':
            sub = gray[y0:y1, x0:x1] < 165
        else:
            sub = image[y0:y1, x0:x1].max(-1) < 120
        if mode == 'cap':
            labels, count = ndi.label(sub, structure=np.ones((3, 3)))
            for index in range(1, count + 1):
                ys, xs = np.nonzero(labels == index)
                if xs.max() - xs.min() > 60:
                    sub[labels == index] = False
        mask[y0:y1, x0:x1] |= sub.astype(np.uint8)
    mask = cv2.dilate(mask, np.ones((3, 3), np.uint8), iterations=2)
    out = cv2.inpaint(image, mask * 255, 4, cv2.INPAINT_TELEA)
    for _name, (x0, y0, x1, y1, mode) in boxes.items():
        if mode not in ('cap', 'white'):
            continue
        x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
        patch = gray[y0:y1, x0:x1]
        dark = patch < 200
        labels, count = ndi.label(dark, structure=np.ones((3, 3)))
        keep = np.zeros_like(dark)
        for index in range(1, count + 1):
            ys, xs = np.nonzero(labels == index)
            if mode == 'cap' and xs.max() - xs.min() > 40 and ys.max() - ys.min() > 10:
                keep |= labels == index
        keep = ndi.binary_dilation(keep, iterations=1)
        sub = out[y0:y1, x0:x1]
        sub[~keep] = 255
        if mode == 'cap':
            sub[keep] = image[y0:y1, x0:x1][keep]
    return out


def main(argv=None):
    args = parse_args(argv if argv is not None else sys.argv[1:])
    image = cv2.imread(str(args.image), cv2.IMREAD_COLOR)
    if image is None:
        raise SystemExit(f'打不开图片：{args.image}')
    boxes = json.loads(Path(args.boxes).read_text(encoding='utf-8'))
    out = clean(image, boxes)
    dest = Path(args.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(dest), out):
        raise SystemExit(f'写不出：{dest}')
    print(f'wrote {dest}  {out.shape[1]}×{out.shape[0]}', flush=True)
    if args.scale and args.scale != 1:
        if not args.scaled_out:
            raise SystemExit('给了 --scale 时要同时给 --scaled-out')
        scaled = cv2.resize(out, None, fx=args.scale, fy=args.scale, interpolation=cv2.INTER_LANCZOS4)
        scaled_path = Path(args.scaled_out)
        suffix = scaled_path.suffix.lower()
        if suffix in ('.jpg', '.jpeg'):
            ok = cv2.imwrite(str(scaled_path), scaled, [cv2.IMWRITE_JPEG_QUALITY, 90])
        else:
            ok = cv2.imwrite(str(scaled_path), scaled)
        if not ok:
            raise SystemExit(f'写不出：{scaled_path}')
        print(f'wrote {scaled_path}  {scaled.shape[1]}×{scaled.shape[0]}', flush=True)


if __name__ == '__main__':
    main()
