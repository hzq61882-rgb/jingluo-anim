#!/usr/bin/env python3
"""从干净底图生成黑线流光相位图，供模板里的 __LF__ 使用。

暗色、低饱和的墨线被骨架化。相位从每条线偏下的端点沿骨架往外量，
周期默认 44 像素，写进 PNG 的 R 通道；A 通道是略膨胀后的线掩膜。
页面用 feColorMatrix 取出 R，再映射成金色短流光。

B/24 的 clean.jpg 已经是 1190×1616（config 的 2 倍），--scale 用 1。
从一半尺寸的扫描放大时再传 --scale 2。仓库里的
examples/b24-bamai-yuanli/lineflow.png 是从成片抽出的相位图；
用 JPEG 底图重算会因压缩有少量差别，重建动画时优先用那一份。

  python scripts/lineflow.py \\
    --image examples/b24-bamai-yuanli/clean.jpg \\
    --out examples/b24-bamai-yuanli/lineflow.png
"""
from __future__ import annotations

import argparse
import sys
from collections import deque
from pathlib import Path

try:
    import cv2
    import numpy as np
    from PIL import Image
    from scipy import ndimage as ndi
    from skimage.morphology import skeletonize
except ImportError as exc:
    raise SystemExit(
        '需要 opencv、numpy、scipy、scikit-image、pillow：pip install -r scripts/requirements.txt'
    ) from exc


def parse_args(argv):
    p = argparse.ArgumentParser(description='生成黑线流光相位图 PNG')
    p.add_argument('--image', required=True, help='去手写后的底图')
    p.add_argument('--out', required=True, help='输出 PNG（R=相位，A=线掩膜）')
    p.add_argument('--scale', type=float, default=1.0,
                   help='先把底图放大再取线。已是目标分辨率时用 1，半尺寸扫描用 2')
    p.add_argument('--period', type=float, default=44.0, help='相位重复的像素周期')
    p.add_argument('--dark-max', type=int, default=110, help='墨线最大通道值')
    p.add_argument('--chroma-max', type=int, default=70, help='墨线最大通道差，用来丢掉彩色带')
    p.add_argument('--min-area', type=int, default=30, help='丢掉小于这么多像素的碎块（按放大后的图）')
    p.add_argument('--dilate', type=int, default=1, help='线掩膜膨胀次数')
    p.add_argument('--vis', default=None, help='可选：另存一张伪彩色预览')
    return p.parse_args(argv)


def phase_image(rgb, period, dark_max, chroma_max, min_area, dilate):
    mx = rgb.max(-1)
    mn = rgb.min(-1)
    mask = (mx < dark_max) & ((mx - mn) < chroma_max)
    structure = np.ones((3, 3), dtype=int)
    labels, count = ndi.label(mask, structure=structure)
    if count:
        sizes = ndi.sum(mask, labels, range(1, count + 1))
        keep = 1 + np.nonzero(sizes >= min_area)[0]
        mask = np.isin(labels, keep)
    else:
        mask = np.zeros(mask.shape, dtype=bool)
    skel = skeletonize(mask)
    dist = distance_from_bottom(skel)
    _, (iy, ix) = ndi.distance_transform_edt(~skel, return_indices=True)
    full = dist[iy, ix]
    phase = ((full % period) / period * 255).astype(np.uint8)
    if dilate > 0:
        alpha_mask = ndi.binary_dilation(mask, iterations=dilate)
    else:
        alpha_mask = mask
    rgba = np.zeros((*mask.shape, 4), np.uint8)
    rgba[..., 0] = phase
    rgba[..., 3] = alpha_mask.astype(np.uint8) * 255
    return rgba, int(mask.sum()), int(skel.sum())


def distance_from_bottom(skel):
    """每条骨架从画面上更靠下的端点起算路程。断开的线各自起算。"""
    height, width = skel.shape
    dist = np.full(skel.shape, -1.0)
    ys, xs = np.nonzero(skel)
    if len(ys) == 0:
        return dist
    order = np.lexsort((xs, -ys))
    neighbors = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
    for index in order:
        y, x = int(ys[index]), int(xs[index])
        if dist[y, x] >= 0:
            continue
        dist[y, x] = 0.0
        queue = deque([(y, x)])
        while queue:
            cy, cx = queue.popleft()
            base = dist[cy, cx]
            for dy, dx in neighbors:
                yy, xx = cy + dy, cx + dx
                if 0 <= yy < height and 0 <= xx < width and skel[yy, xx] and dist[yy, xx] < 0:
                    dist[yy, xx] = base + (1.41421356237 if dy and dx else 1.0)
                    queue.append((yy, xx))
    return dist


def main(argv=None):
    args = parse_args(argv if argv is not None else sys.argv[1:])
    if args.scale <= 0:
        raise SystemExit('--scale 要大于 0')
    if args.period <= 0:
        raise SystemExit('--period 要大于 0')
    bgr = cv2.imread(str(args.image), cv2.IMREAD_COLOR)
    if bgr is None:
        raise SystemExit(f'打不开图片：{args.image}')
    if abs(args.scale - 1) > 1e-6:
        bgr = cv2.resize(bgr, None, fx=args.scale, fy=args.scale, interpolation=cv2.INTER_CUBIC)
    rgb = bgr[:, :, ::-1].astype(int)
    rgba, ink, skel = phase_image(
        rgb, args.period, args.dark_max, args.chroma_max, args.min_area, args.dilate,
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgba).save(out, optimize=True)
    print(f'wrote {out}  {rgba.shape[1]}×{rgba.shape[0]}  ink {ink}  skeleton {skel}', flush=True)
    if args.vis:
        phase = rgba[..., 0]
        vis = np.zeros((*phase.shape, 3), np.uint8)
        on = rgba[..., 3] > 0
        vis[on, 0] = phase[on]
        vis[on, 1] = 255 - phase[on]
        vis[on, 2] = 128
        Image.fromarray(vis).save(args.vis)
        print(f'wrote {args.vis}', flush=True)


if __name__ == '__main__':
    main()
