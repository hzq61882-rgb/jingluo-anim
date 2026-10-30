#!/usr/bin/env python3
"""擦掉扫描图上的手写字，留下线条，供矢量文字重绘。

两种范围：

  labels  每个标签一块旋转矩形。细线（霍夫线段、细长连通域）默认保护。
          python scripts/inpaint.py labels --image src.jpg --labels labels.json --out clean.jpg

  boxes   命名矩形。mode 为 dark（浅底深字）、in（深底浅字）、cap / white（说明框刷白，留下长下划线）。
          python scripts/inpaint.py boxes --image src.jpg --boxes boxes.json --out clean.png

labels.json 接受对象或七元数组 [x, y, size, rotate, weight, text, kind]。
坐标是原图像素。
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import load_json, normalize_label  # noqa: E402

try:
    import cv2
    import numpy as np
except ImportError as exc:
    raise SystemExit('需要 opencv-python-headless 和 numpy：pip install -r scripts/requirements.txt') from exc


def label_polygon(label, pad):
    text = label['text']
    size = label['size']
    kind = label['kind']
    width = (size * len(text) * (1.02 if kind == 'cjk' else 0.58)) + pad * 2
    height = size * 1.08 + pad * 2
    angle = math.radians(label['rotate'])
    cos_a, sin_a = math.cos(angle), math.sin(angle)
    pts = []
    for dx, dy in ((-width / 2, -height / 2), (width / 2, -height / 2),
                   (width / 2, height / 2), (-width / 2, height / 2)):
        pts.append((label['x'] + dx * cos_a - dy * sin_a,
                    label['y'] + 0.05 * size + dx * sin_a + dy * cos_a))
    return np.array(pts, np.int32)


def _as_circles(data):
    circles = []
    for item in data:
        if isinstance(item, (list, tuple)):
            circles.append((int(item[0]), int(item[1]), int(item[2])))
        else:
            circles.append((int(item['cx'] if 'cx' in item else item['x']),
                            int(item['cy'] if 'cy' in item else item['y']),
                            int(item['r'])))
    return circles


def inpaint_labels(image_path, labels_path, out_path, rings_path=None, lines_path=None,
                   restore_saturated=False, discs_path=None):
    img = cv2.imread(str(image_path))
    if img is None:
        raise SystemExit(f'打不开图片：{image_path}')
    height, width = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    dark = ((gray < 135) & (hsv[..., 2] < 150)).astype(np.uint8)
    count, lab, _stats, _cent = cv2.connectedComponentsWithStats(dark, 8)

    protect = np.zeros_like(dark)
    for kernel in (cv2.getStructuringElement(cv2.MORPH_RECT, (31, 1)),
                   cv2.getStructuringElement(cv2.MORPH_RECT, (1, 31))):
        protect |= cv2.morphologyEx(dark, cv2.MORPH_OPEN, kernel)
    if lines_path:
        segs = load_json(lines_path)
        if isinstance(segs, dict):
            segs = segs.get('segs', [])
        for seg in segs:
            x1, y1, x2, y2 = [int(v) for v in seg[:4]]
            if math.hypot(x2 - x1, y2 - y1) > 45:
                cv2.line(protect, (x1, y1), (x2, y2), 1, 3)
    protect &= dark

    labels = [normalize_label(item) for item in load_json(labels_path)]
    mask = np.zeros_like(dark)
    for label in labels:
        box = np.zeros_like(dark)
        cv2.fillPoly(box, [label_polygon(label, 2)], 1)
        big = np.zeros_like(dark)
        cv2.fillPoly(big, [label_polygon(label, 6)], 1)
        ids = np.unique(lab[(box > 0) & (dark > 0)])
        ids = ids[ids > 0]
        for index in ids:
            comp = (lab == index)
            inside = (comp & (big > 0)).sum() / max(1, comp.sum())
            if inside > 0.9:
                mask |= (comp & (big > 0)).astype(np.uint8)
            elif label['size'] >= 24:
                mask |= (comp & (box > 0)).astype(np.uint8)
            else:
                mask |= (comp & (box > 0) & (protect == 0)).astype(np.uint8)
    core = mask.copy()
    allbox = np.zeros_like(dark)
    for label in labels:
        cv2.fillPoly(allbox, [label_polygon(label, 3)], 1)
    halo = ((gray < 205) & (allbox > 0) & (protect == 0)).astype(np.uint8)
    for _ in range(3):
        mask |= cv2.dilate(mask, np.ones((3, 3), np.uint8)) & halo
    mask = cv2.dilate(mask, np.ones((3, 3), np.uint8), iterations=2)

    if rings_path:
        ring = np.zeros_like(dark)
        for cx, cy, radius in _as_circles(load_json(rings_path)):
            cv2.circle(ring, (cx, cy), radius, 1, 5)
        ring &= (gray < 150).astype(np.uint8)
        mask[ring > 0] = 0

    out = cv2.inpaint(img, mask, 5, cv2.INPAINT_TELEA)
    core_dilate = cv2.dilate(core, np.ones((3, 3), np.uint8), iterations=1)

    if discs_path:
        for cx, cy, radius in _as_circles(load_json(discs_path)):
            disk = np.zeros_like(dark)
            cv2.circle(disk, (cx, cy), max(1, radius - 3), 1, -1)
            good = (disk > 0) & (mask == 0) & (hsv[..., 1] > 70)
            if not good.any():
                continue
            median = np.median(img[good], axis=0)
            fill = (disk > 0) & (mask > 0)
            out[fill] = median.astype(np.uint8)
            blurred = cv2.GaussianBlur(out, (5, 5), 0)
            out = np.where(disk[..., None] > 0, blurred, out)

    if restore_saturated:
        saturated = ((hsv[..., 0] >= 3) & (hsv[..., 0] <= 25) & (hsv[..., 1] > 110) & (hsv[..., 2] > 90)).astype(np.uint8)
        restore = ((cv2.dilate(protect, np.ones((3, 3), np.uint8)) | saturated) > 0) & (core_dilate == 0)
        out[restore] = img[restore]

    _write(out, out_path, mask)
    print(f'inpaint labels {width}×{height}  mask {int(mask.sum())} px  -> {out_path}')


def inpaint_boxes(image_path, boxes_path, out_path):
    try:
        from scipy import ndimage as ndi
    except ImportError as exc:
        raise SystemExit('boxes 模式需要 scipy：pip install -r scripts/requirements.txt') from exc
    img = cv2.imread(str(image_path))
    if img is None:
        raise SystemExit(f'打不开图片：{image_path}')
    gray = img.mean(-1)
    boxes = load_json(boxes_path)
    mask = np.zeros(gray.shape, np.uint8)
    for _name, box in boxes.items():
        x0, y0, x1, y1, mode = box
        if mode == 'in':
            sub = img[y0:y1, x0:x1].max(-1) < 120
        else:
            sub = gray[y0:y1, x0:x1] < 165
        if mode == 'cap':
            lab, count = ndi.label(sub, structure=np.ones((3, 3)))
            for index in range(1, count + 1):
                ys, xs = np.nonzero(lab == index)
                if xs.max() - xs.min() > 60:
                    sub[lab == index] = False
        mask[y0:y1, x0:x1] |= sub.astype(np.uint8)
    mask = cv2.dilate(mask, np.ones((3, 3), np.uint8), iterations=2)
    out = cv2.inpaint(img, mask * 255, 4, cv2.INPAINT_TELEA)
    for _name, box in boxes.items():
        x0, y0, x1, y1, mode = box
        if mode not in ('cap', 'white'):
            continue
        patch = gray[y0:y1, x0:x1]
        dark = patch < 200
        lab, count = ndi.label(dark, structure=np.ones((3, 3)))
        keep = np.zeros_like(dark)
        for index in range(1, count + 1):
            ys, xs = np.nonzero(lab == index)
            if mode == 'cap' and xs.max() - xs.min() > 40 and ys.max() - ys.min() > 10:
                keep |= lab == index
        keep = ndi.binary_dilation(keep, iterations=1)
        sub = out[y0:y1, x0:x1]
        sub[~keep] = 255
        if mode == 'cap':
            sub[keep] = img[y0:y1, x0:x1][keep]
    _write(out, out_path, mask)
    print(f'inpaint boxes -> {out_path}')


def _write(image, out_path, mask):
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    ext = out_path.suffix.lower()
    if ext in ('.jpg', '.jpeg'):
        cv2.imwrite(str(out_path), image, [cv2.IMWRITE_JPEG_QUALITY, 92])
    else:
        cv2.imwrite(str(out_path), image)
    mask_path = out_path.with_name(out_path.stem + '_mask.png')
    cv2.imwrite(str(mask_path), mask * 255)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(description='擦除扫描图手写')
    sub = parser.add_subparsers(dest='mode', required=True)

    labels = sub.add_parser('labels', help='按标签框擦字，保护细线')
    labels.add_argument('--image', required=True)
    labels.add_argument('--labels', required=True)
    labels.add_argument('--out', required=True)
    labels.add_argument('--rings', help='要保住的圆环 [cx, cy, r]，擦字时不涂掉环线')
    labels.add_argument('--lines', help='霍夫线段 JSON，长线段并进保护区')
    labels.add_argument('--restore-saturated', action='store_true', help='把橙色弧线像素从原图拷回')
    labels.add_argument('--discs', help='实心小圆 [cx, cy, r]，圆内用周围色填平')

    boxes = sub.add_parser('boxes', help='按命名矩形擦字')
    boxes.add_argument('--image', required=True)
    boxes.add_argument('--boxes', required=True)
    boxes.add_argument('--out', required=True)

    args = parser.parse_args(argv)
    if args.mode == 'labels':
        inpaint_labels(args.image, args.labels, args.out, args.rings, args.lines,
                       args.restore_saturated, args.discs)
    else:
        inpaint_boxes(args.image, args.boxes, args.out)


if __name__ == '__main__':
    main()
