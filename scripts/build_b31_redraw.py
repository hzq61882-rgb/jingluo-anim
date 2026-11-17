#!/usr/bin/env python3
"""B/31 全图重绘点亮版。默认只有矢量几何和字体，不铺整页墨线。"""
from __future__ import annotations

import base64
import io
import json
import re
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_b31_corrected import READS  # noqa: E402
from build_b31_inner import GROUPS  # noqa: E402
from build_b31_spin import EXTRA, main  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SCAN = Path('/tmp/scans/b31.jpg')
OUT = ROOT / 'examples/b31-cunguan-siji/寸关尺四季表里图_全图重绘点亮版.html'
COV = ROOT / 'examples/b31-cunguan-siji/coverage-全图重绘点亮.json'
CX, CY = 404.0, 296.0
RING_RADII = [24.45, 32.0, 38.95, 45.95, 53.45, 60.45, 68.0, 74.95, 81.45]
# 这些是表头、分区名，旁边没有穴位彩条。
SKIP_BAR = {'表层', '里层', '冬', '春', '夏', '秋', '长夏', '左腕', '右腕', '足临泣'}


def uri_png(im):
    buf = io.BytesIO()
    im.save(buf, format='PNG', optimize=True)
    return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode('ascii')


def uri_jpg(arr):
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format='JPEG', quality=90)
    return 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode('ascii')


def hex_of(rgb):
    return '#{:02x}{:02x}{:02x}'.format(*[int(max(0, min(255, v))) for v in rgb])


def boost(rgb, sat=1.65, val=1.08):
    bgr = np.uint8([[list(map(int, rgb))[::-1]]])
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[0, 0, 1] = min(255, hsv[0, 0, 1] * sat)
    hsv[0, 0, 2] = min(255, max(40, hsv[0, 0, 2] * val))
    out = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)[0, 0]
    return [int(out[2]), int(out[1]), int(out[0])]


def sample_box(scan, x0, y0, x1, y1):
    h, w = scan.shape[:2]
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(w, x1), min(h, y1)
    sl = scan[y0:y1, x0:x1]
    if sl.size == 0:
        return [230, 220, 200], 0
    sat = sl.max(2).astype(int) - sl.min(2).astype(int)
    if int(sat.max()) < 18:
        return [int(v) for v in np.median(sl.reshape(-1, 3), 0)], int(sat.max())
    sel = sat >= max(18, int(sat.max()) * 0.55)
    med = np.median(sl.reshape(-1, 3)[sel.reshape(-1)], 0)
    return [int(v) for v in med], int(sat.max())


def all_labels():
    rows = list(READS) + list(EXTRA)
    for _t, _w, group in GROUPS:
        rows.extend(group)
    return rows


def row_dot(scan, x0, y0, x1, y1):
    """这一行里饱和度最高的小色块。深色高饱和也算，纯黑字不算。"""
    h, w = scan.shape[:2]
    wy0, wy1 = max(0, y0 - 1), min(h, y1 + 2)
    wx0, wx1 = max(0, x0 - 22), min(w, x1 + 6)
    sl = scan[wy0:wy1, wx0:wx1]
    if sl.size == 0:
        return None
    sat = sl.max(2).astype(int) - sl.min(2).astype(int)
    if int(sat.max()) < 28:
        return None
    iy, ix = np.unravel_index(int(sat.argmax()), sat.shape)
    py, px = wy0 + int(iy), wx0 + int(ix)
    patch = scan[max(0, py - 1):py + 2, max(0, px - 1):px + 2]
    med = np.median(patch.reshape(-1, 3), 0)
    psat = int(patch.max() - patch.min())
    if psat < 24 or float(patch.mean()) < 18:
        return None
    return px, py, boost(med, 1.4, 1.02), int(sat.max())


def dot_for(scan, x0, y0, x1, y1):
    """在字行左侧的彩点里取高饱和像素，不拿文字黑边当填色。"""
    h, w = scan.shape[:2]
    wx0, wx1 = max(0, x0 - 26), min(w, x0 + 4)
    wy0, wy1 = max(0, y0 - 1), min(h, y1 + 1)
    sl = scan[wy0:wy1, wx0:wx1]
    sat = sl.max(2).astype(int) - sl.min(2).astype(int)
    if sl.size == 0 or int(sat.max()) < 20:
        return None
    sel = sat >= max(20, int(sat.max()) * 0.62)
    ys, xs = np.where(sel)
    keep = (xs + wx0) < (x0 + 3)
    if int(keep.sum()) < 2:
        return None
    ys, xs = ys[keep], xs[keep]
    px = int(wx0 + np.median(xs))
    py = int(wy0 + np.median(ys))
    med = np.median(sl[ys, xs].reshape(-1, 3), 0)
    if float(np.mean(med)) < 45:
        return None
    return px, py, boost(med, 1.55, 1.05), int(sat.max())


def column_bars(scan, x0, x1, y0, y1):
    """原图上连贯的彩色横条，按列宽取，不按字框。"""
    sat = scan.max(2).astype(int) - scan.min(2).astype(int)
    sl = sat[y0:y1, x0:x1]
    row = (sl > 26).mean(1)
    ys = np.where(row > 0.32)[0]
    bands = []
    if len(ys):
        s = p = int(ys[0])
        for y in map(int, ys[1:]):
            if y <= p + 1:
                p = y
            else:
                if p - s >= 2:
                    bands.append((y0 + s, y0 + p))
                s = p = y
        if p - s >= 2:
            bands.append((y0 + s, y0 + p))
    out = []
    for a, b in bands:
        rgb, satv = sample_box(scan, x0, a, x1, b + 1)
        hgt = b - a + 1
        if satv < 20 or hgt > 8:
            continue
        out.append({'x': x0, 'y': a, 'w': x1 - x0, 'h': hgt, 'hex': hex_of(boost(rgb, 1.35, 1.04))})
    return out


def column_rules(scan, x0, x1, y0, y1):
    g = scan.mean(2)
    dark = g[y0:y1, x0:x1] < 105
    frac = dark.mean(1)
    ys = np.where(frac > 0.42)[0]
    rules = []
    if len(ys):
        s = p = int(ys[0])
        for y in map(int, ys[1:]):
            if y <= p + 1:
                p = y
            else:
                rules.append(y0 + (s + p) // 2)
                s = p = y
        rules.append(y0 + (s + p) // 2)
    return rules


def detect_dots(scan):
    """只收原图上小而圆的高饱和点。颜色取点内部，丢掉最暗的边缘。"""
    h, w = scan.shape[:2]
    sat = scan.max(2).astype(int) - scan.min(2).astype(int)
    gray = scan.mean(2)
    mask = (sat > 16) & (gray > 35) & (gray < 245)
    yy, xx = np.mgrid[:h, :w]
    dist = np.sqrt((xx - CX) ** 2 + (yy - CY) ** 2)
    mask &= (dist > 96) | (dist < 88)
    vis = np.zeros(mask.shape, bool)
    from collections import deque
    found = []
    for y in range(h):
        for x in np.where(mask[y])[0]:
            if vis[y, x]:
                continue
            q = deque([(y, x)])
            vis[y, x] = True
            pts = []
            while q:
                cy, cx = q.pop()
                pts.append((cy, cx))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        ny, nx = cy + dy, cx + dx
                        if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not vis[ny, nx]:
                            vis[ny, nx] = True
                            q.append((ny, nx))
            if not 8 <= len(pts) <= 80:
                continue
            ys = np.array([p[0] for p in pts])
            xs = np.array([p[1] for p in pts])
            bw, bh = int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1)
            if not (3 <= bw <= 12 and 3 <= bh <= 12 and 0.55 <= bw / max(bh, 1) <= 1.8):
                continue
            colors = scan[ys, xs]
            order = np.argsort(colors.mean(1))
            core = colors[order[len(order) // 3:]]
            med = np.median(core, 0)
            core_sat = int(core.max(1).astype(int).mean() - core.min(1).astype(int).mean()) if False else int(
                (core.max() - core.min()))
            if int(np.max(core, 1).mean() - np.min(core, 1).mean()) < 18:
                continue
            found.append({
                'x': round(float(xs.mean()), 1),
                'y': round(float(ys.mean()), 1),
                'hex': hex_of(boost(med, 1.45, 1.04)),
            })
    return found


def glyph_sprites(scan, keep, max_n=240):
    """紧框裁深色文字，不含长线。"""
    n, lab, stats, _ = cv2.connectedComponentsWithStats(keep.astype(np.uint8), 8)
    sprites = []
    for i in range(1, n):
        x, y, w, h, area = [int(v) for v in stats[i]]
        if not 10 <= area <= 160 or w > 22 or h > 16 or w < 2 or h < 3:
            continue
        if max(w, h) / max(1, min(w, h)) > 4.5:
            continue
        sprites.append((x, y, w, h, area))
    sprites.sort(key=lambda t: (t[1], t[0]))
    return sprites[:max_n]


def sprite_png(scan, x, y, w, h, mask):
    sl = scan[y:y + h, x:x + w]
    local = mask[y:y + h, x:x + w]
    rgba = np.zeros((h, w, 4), np.uint8)
    rgba[local, :3] = 25
    rgba[local, 3] = 230
    if int(local.sum()) < 8:
        return None
    return uri_png(Image.fromarray(rgba))


def main_redraw():
    # 只改这一次进程里的读数，不改校正版源文件。L2 第一格源图是冲阳，L3 右列那格源图是鱼际。
    for i, row in enumerate(READS):
        if row[:5] == ('解溪', 91, 310, 111, 320):
            READS[i] = ('冲阳', 91, 310, 111, 320, row[5])
        elif row[:5] == ('商阳', 117, 433, 132, 445):
            READS[i] = ('鱼际', 117, 433, 132, 445, row[5])
    strips = [row for _t, _w, rows in GROUPS for row in rows]
    strips.append(('商阳', 66, 406, 82, 422, 'disk'))
    # 报告点名的空白圆和空格。只补这些字，不改已经在位的商阳、足通谷、阴谷、阳谷、少府。
    fixes = [
        ('支沟', 66, 171, 86, 181, 'cellfix'),
        ('劳宫', 142, 116, 164, 126, 'cellfix'),
        ('三里', 64, 348, 86, 358, 'cellfix'),
        ('足', 50, 345, 60, 356, 'cellfix'),
        ('太', 145, 290, 157, 300, 'cellfix'),
        ('经渠', 141, 489, 163, 499, 'cellfix'),
        ('大敦', 733, 244, 755, 254, 'cellfix'),
        ('大', 121, 133, 135, 143, 'cellfix'),
        ('陵', 121, 152, 135, 162, 'cellfix'),
        ('厉兑', 90, 252, 112, 262, 'cellfix'),
        ('隐白', 116, 252, 140, 262, 'cellfix'),
        ('白', 122, 310, 136, 320, 'cellfix'),
        ('二间', 90, 432, 112, 442, 'cellfix'),
        ('三间', 90, 450, 112, 460, 'cellfix'),
        ('太', 121, 450, 135, 460, 'cellfix'),
        ('渊', 121, 469, 135, 479, 'cellfix'),
    ]
    strips.extend(fixes)
    main(extra_labels=strips, out_html=OUT, coverage_path=COV, inner=True)
    scan = np.array(Image.open(SCAN).convert('RGB'))
    h, w = scan.shape[:2]
    paper = np.full_like(scan, (248, 244, 232))

    yy, xx = np.mgrid[:h, :w]
    dist = np.sqrt((xx - CX) ** 2 + (yy - CY) ** 2)
    gray = scan.mean(2)
    from b31_qc_geom import RING_HEX, build_spec_svg, NAMED_DOTS
    ring_colors = []
    for hex_color in RING_HEX:
        ring_colors.append([int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)])

    from b31_qc_geom import (
        PAL, WHEEL_TEXT, PLUS_BOXES, SIDE_BOXES, CHAIN, NODE_IDS, PERIPH,
    )
    confirmed = [(x0 - 1, y0 - 1, x1 + 1, y1 + 1) for _t, x0, y0, x1, y1, _z in list(READS) + list(EXTRA) + strips]
    geom, inv, circles, named_dots, bar_n = build_spec_svg()

    def bind_label(name, x0, y0, x1, y1):
        cy = (y0 + y1) / 2
        if name not in NAMED_DOTS:
            return None
        if name == '照海':
            return []
        hits = []
        for (px, py), klass, r in NAMED_DOTS[name]:
            if abs(py - cy) <= 8 and (x0 - 10) <= px <= (x1 + 28):
                hits.append((px, py, klass, r))
        return hits

    name_status = []
    for title, _where, rows in GROUPS:
        for name, x0, y0, x1, y1, _zone in rows:
            hits = bind_label(name, x0, y0, x1, y1)
            if hits is None:
                name_status.append({
                    'name': name, 'group': title, 'status': '待核', 'y': y0,
                    'why': '规格没有逐字绑这一组，不按附近饱和色块配，也不把未取到写成无点',
                })
            elif hits == [] and name == '照海':
                name_status.append({
                    'name': name, 'group': title, 'status': '待核', 'y': y0,
                    'why': '规格写明这一行未见明确独立小彩点。(401,458) 是引线端，不造点',
                })
            elif not hits:
                name_status.append({
                    'name': name, 'group': title, 'status': '待核', 'y': y0,
                    'why': '同名点的源坐标和这一处字框对不上，不把别处的点绑过来',
                })
            else:
                for px, py, klass, _r in hits:
                    name_status.append({
                        'name': name, 'group': title, 'status': '有点',
                        'x': px, 'y': py, 'klass': klass, 'hex': PAL[klass],
                    })

    # 脾经规格未逐字给点。只在每个字框自己的行高、x258–274 里取色块，不借用邻行。
    spleen_bits = []
    spleen_used = []
    for title, _where, rows in GROUPS:
        if title != '足太阴脾经':
            continue
        for name, x0, y0, x1, y1, _zone in rows:
            def drop_prior(name=name, y0=y0, title=title):
                name_status[:] = [s for s in name_status if not (
                    s['name'] == name and s['group'] == title and s.get('y') == y0)]
            wy0 = max(0, y0)
            sl = scan[wy0:min(h, y1 + 1), 258:275]
            if sl.size == 0:
                continue
            sat = sl.max(2).astype(int) - sl.min(2).astype(int)
            if int(sat.max()) < 28:
                drop_prior()
                name_status.append({'name': name, 'group': title, 'status': '待核', 'y': y0,
                                    'why': '这一行 x258–274 没有饱和色块。待核不是无点'})
                continue
            iy, ix = np.unravel_index(int(sat.argmax()), sat.shape)
            py, px = wy0 + int(iy), 258 + int(ix)
            if any(abs(px - a) <= 3 and abs(py - b) <= 3 for a, b in spleen_used):
                drop_prior()
                name_status.append({'name': name, 'group': title, 'status': '待核', 'y': y0,
                                    'why': '这一行色块和上一行是同一颗，不重复绑定'})
                continue
            spleen_used.append((px, py))
            patch = scan[max(0, py - 1):py + 2, max(0, px - 1):px + 2]
            med = np.median(patch.reshape(-1, 3), 0)
            rgb = boost(med, 1.25, 1.02)
            spleen_bits.append((name, px, py, hex_of(rgb)))
            drop_prior()
            name_status.append({'name': name, 'group': title, 'status': '有点', 'x': px, 'y': py,
                                'hex': hex_of(rgb), 'why': '规格未逐字给脾经。只取该字框同一行 x258–274 的色块'})
    if spleen_bits:
        extra = ['<g id="spleen-dots">']
        for i, (name, px, py, hx) in enumerate(spleen_bits):
            extra.append(
                f'<g id="spleen-{i}" data-spin="1" data-kind="spec" data-turns="1" data-cx="{px}" data-cy="{py}">'
                f'<circle cx="{px}" cy="{py}" r="2.2" fill="{hx}" stroke="#202020" stroke-width="0.45"/>'
                f'</g>'
            )
            inv.append({'id': f'spleen-{i}', 'type': 'acupoint-dot', 'redrawn': True, 'new_id': f'spleen-{i}',
                        'name': name, 'cx': px, 'cy': py, 'why': '同一行实测，不是邻行饱和度抢配'})
        extra.append('</g>')
        geom = geom[:-4] + ''.join(extra) + '</g>'

    def crop_components(box):
        x0, y0, x1, y1 = [int(v) for v in box]
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(w, x1), min(h, y1)
        if x1 - x0 < 3 or y1 - y0 < 3:
            return []
        sl = scan[y0:y1, x0:x1]
        g = sl.mean(2)
        sat = sl.max(2).astype(int) - sl.min(2).astype(int)
        ink = (g < 140) & (sat < 50)
        # 小框里的竖笔会被当成表格线删掉，B/31 和表内细字不再做开运算。
        if (y1 - y0) >= 28 and (x1 - x0) >= 24:
            u8 = ink.astype(np.uint8) * 255
            hk = cv2.getStructuringElement(cv2.MORPH_RECT, (max(12, (x1 - x0) * 2 // 3), 1))
            vk = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(12, (y1 - y0) * 2 // 3)))
            lines = cv2.bitwise_or(cv2.morphologyEx(u8, cv2.MORPH_OPEN, hk), cv2.morphologyEx(u8, cv2.MORPH_OPEN, vk))
            ink = ink & (lines == 0)
        yy, xx = np.mgrid[y0:y1, x0:x1]
        edge = np.zeros(ink.shape, bool)
        for cx, cy, rad in circles:
            if rad > 40:
                continue
            if cx + rad < x0 - 2 or cx - rad > x1 + 2 or cy + rad < y0 - 2 or cy - rad > y1 + 2:
                continue
            d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
            if rad <= 6.2:
                edge |= d <= rad + 1.1
            else:
                edge |= np.abs(d - rad) <= 1.5
        ink = ink & ~edge
        for bx0, by0, bx1, by1 in confirmed:
            ix0, iy0 = max(0, int(bx0) - x0), max(0, int(by0) - y0)
            ix1, iy1 = min(ink.shape[1], int(bx1) - x0), min(ink.shape[0], int(by1) - y0)
            if ix1 > ix0 and iy1 > iy0:
                ink[iy0:iy1, ix0:ix1] = False
        count, labels, stats, _cent = cv2.connectedComponentsWithStats(ink.astype(np.uint8), 8)
        found = []
        for i in range(1, count):
            x, y, ww, hh, area = stats[i]
            if area < 8 or ww < 2 or hh < 2:
                continue
            if ww > hh * 4 and ww > 14:
                continue
            if (y1 - y0) >= 28 and 0.75 <= ww / max(hh, 1) <= 1.3 and area > 18 and area / float(ww * hh) > 0.55 and max(ww, hh) < 16:
                continue
            mask = labels[y:y + hh, x:x + ww] == i
            found.append((x0 + int(x), y0 + int(y), int(ww), int(hh), mask))
        return found

    legend_boxes = []
    legend_y = [451, 466, 479, 493, 506, 519, 533]
    for i in range(6):
        if i == 3:
            legend_boxes.append((556, legend_y[i] + 1, 588, legend_y[i + 1] - 1))
        else:
            legend_boxes.append((556, legend_y[i] + 1, 568, legend_y[i + 1] - 1))
            legend_boxes.append((576, legend_y[i] + 1, 588, legend_y[i + 1] - 1))
    # 这三个感官圈改成一整块圈内墨字，不再拆成偏旁。右上发/骨/听觉已是新字，不贴回旧圈。
    whole_interiors = [(153, 359, 178, 389), (187, 495, 213, 529), (636, 332, 659, 358)]
    pending_boxes = [
        b for b in list(WHEEL_TEXT) + list(PLUS_BOXES) + list(SIDE_BOXES) + legend_boxes
        if b not in whole_interiors
    ]
    kept = ['<g id="kept">']
    side = []
    empty_pending = []
    for box in pending_boxes:
        bits = crop_components(box)
        if not bits:
            empty_pending.append(list(box))
            inv.append({'id': f'pending-{box[0]}-{box[1]}', 'type': 'text-pending', 'redrawn': False,
                        'box': list(box), 'why': '框内没有分离出不含圆边的字，待核，不把圆边或色条当成字'})
            continue
        for x, y, ww, hh, mask in bits:
            rgba = np.zeros((hh, ww, 4), np.uint8)
            rgba[mask, :3] = 25
            rgba[mask, 3] = 230
            png = uri_png(Image.fromarray(rgba))
            kept.append(f'<image data-scan-ink="1" href="{png}" x="{x}" y="{y}" width="{ww}" height="{hh}"/>')
            side.append((x, y, ww, hh))

    def emit_ink(mask, x0, y0, why):
        if int(mask.sum()) < 8:
            return False
        ys, xs = np.where(mask)
        xa, xb = int(xs.min()), int(xs.max()) + 1
        ya, yb = int(ys.min()), int(ys.max()) + 1
        sub = mask[ya:yb, xa:xb]
        rgba = np.zeros((yb - ya, xb - xa, 4), np.uint8)
        rgba[sub, :3] = 25
        rgba[sub, 3] = 230
        kept.append(
            f'<image data-scan-ink="1" href="{uri_png(Image.fromarray(rgba))}" '
            f'x="{x0 + xa}" y="{y0 + ya}" width="{xb - xa}" height="{yb - ya}"/>'
        )
        side.append((x0 + xa, y0 + ya, xb - xa, yb - ya))
        inv.append({'id': f'ink-{x0 + xa}-{y0 + ya}', 'type': 'text-pending', 'redrawn': False,
                    'box': [x0 + xa, y0 + ya, x0 + xb, y0 + yb], 'why': why})
        return True

    def interior_ink(x0, y0, x1, y1):
        x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
        sl = scan[y0:y1, x0:x1]
        g = sl.mean(2)
        sat = sl.max(2).astype(int) - sl.min(2).astype(int)
        ink = (g < 145) & (sat < 48)
        yy, xx = np.mgrid[y0:y1, x0:x1]
        edge = np.zeros(ink.shape, bool)
        for cx, cy, rad in circles:
            if rad > 40 or cx + rad < x0 - 2 or cx - rad > x1 + 2 or cy + rad < y0 - 2 or cy - rad > y1 + 2:
                continue
            d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
            edge |= np.abs(d - rad) <= 1.6
        ink = ink & ~edge
        for bx0, by0, bx1, by1 in confirmed:
            ix0, iy0 = max(0, int(bx0) - x0), max(0, int(by0) - y0)
            ix1, iy1 = min(ink.shape[1], int(bx1) - x0), min(ink.shape[0], int(by1) - y0)
            if ix1 > ix0 and iy1 > iy0:
                ink[iy0:iy1, ix0:ix1] = False
        return ink, x0, y0

    # C9 红底上的黑字饱和度不低，不能用低饱和阈值。只取圈内比红底更暗的像素。
    c9 = scan[285:301, 658:687]
    c9g = c9.mean(2)
    yy, xx = np.mgrid[285:301, 658:687]
    c9m = (c9g < 80) & (((xx - 672) ** 2 + (yy - 290) ** 2) < (16 - 2.8) ** 2)
    emit_ink(c9m, 658, 285, 'C9 圈内原字不能确认，紧框待核，不按胆经顺序起名')
    for box in whole_interiors:
        ink, x0, y0 = interior_ink(*box)
        if not emit_ink(ink, x0, y0, '圈内原字未辨清，整块紧框保留，不拆成偏旁，也不猜名'):
            empty_pending.append(list(box))
    for cx, cy, rad, _klass in PERIPH:
        if abs(cx - 585) < 1 and abs(cy - 175) < 1:
            inv.append({'id': 'periph-gan', 'type': 'text', 'redrawn': True, 'cx': cx, 'cy': cy,
                        'why': '右上绿圈已有确认字肝，不叠旧墨'})
            continue
        ink, x0, y0 = interior_ink(cx - rad + 1.5, cy - rad + 1.5, cx + rad - 1.5, cy + rad - 1.5)
        yy, xx = np.mgrid[0:ink.shape[0], 0:ink.shape[1]]
        inside = (xx + x0 - cx) ** 2 + (yy + y0 - cy) ** 2 <= (rad - 2.0) ** 2
        emit_ink(ink & inside, x0, y0, '外围彩圆内原字未辨清，紧框待核，不编号')
    kept.append('</g>')
    ring_glyphs = [[] for _ in RING_RADII]
    for i, rad in enumerate(RING_RADII):
        inv.append({'id': f'ring{i}-numerals', 'type': 'text-pending', 'redrawn': False, 'r': rad,
                    'why': '环上原字和刻度分不开，不把含线裁片当字体，也不新写数字'})
    geom = geom + ''.join(kept)
    bars = [s for s in inv if s['type'] == 'color-bar']
    kept_organs = [s for s in inv if s['type'] == 'circle']
    dots_unique = list(named_dots) + [
        {'name': n, 'x': x, 'y': y, 'hex': hx} for n, x, y, hx in spleen_bits
    ]

    html = OUT.read_text(encoding='utf-8')
    key = '<image id="bg" href="'
    i = html.find(key)
    j = html.find('"', i + len(key))
    html = html[:i + len(key)] + uri_jpg(paper) + html[j:]
    html = html.replace('<g id="spin">', geom + '<g id="spin">', 1)
    for n, rad in enumerate(RING_RADII):
        token = f'<g id="ring{n}"'
        k = html.find(token)
        img = html.find('<image ', k)
        end = html.find('/>', img) + 2
        piece = (
            f'<circle cx="{CX}" cy="{CY}" r="{rad}" fill="none" stroke="{hex_of(ring_colors[n])}" '
            f'stroke-width="7"/>'
        )
        html = html[:img] + piece + html[end:]
    taiji = dist <= 19.4
    ys, xs = np.where(taiji)
    x0, x1 = int(xs.min()), int(xs.max()) + 1
    y0, y1 = int(ys.min()), int(ys.max()) + 1
    sub = scan[y0:y1, x0:x1].copy()
    hsv = cv2.cvtColor(sub, cv2.COLOR_RGB2HSV).astype(np.float32)
    colorful = hsv[:, :, 1] > 28
    hsv[:, :, 1] = np.where(colorful, np.minimum(255, hsv[:, :, 1] * 1.4), hsv[:, :, 1])
    hsv[:, :, 2] = np.where(colorful, np.minimum(255, hsv[:, :, 2] * 1.05), hsv[:, :, 2])
    sub = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB)
    taiji_png = uri_png(Image.fromarray(sub))
    tk = html.find('<g id="taiji"')
    href_at = html.find('href="', tk) + 6
    href_end = html.find('"', href_at)
    html = html[:href_at] + taiji_png + html[href_end:]
    html = re.sub(r'<g id="dot\d+"[^>]*>.*?</g>', '', html)
    for cid in ('shaofu', 'yanggu', 'yang', 'yin', 'mianxue', 'zutong', 'yingu', 'fa', 'gan-link', 'xiao-link'):
        html = re.sub(rf'<g id="{cid}" data-spin="1".*?</g>', '', html, count=1)
    marker = 'const CFG='
    ci = html.find(marker)
    cj = html.find(';\n', ci)
    cfg = json.loads(html[ci + len(marker):cj])
    for node in cfg.get('nodes') or []:
        if node.get('id') in NODE_IDS:
            x, y = CHAIN[NODE_IDS.index(node['id'])]
            node['x'], node['y'] = x, y
            node['r'] = 7
            node['fs'] = 6
            node['fill'] = '#fff'
            node['halo'] = 0.35
            if 'tl' in node and len(str(node.get('t') or '')) == 2:
                node['tl'] = 8
    html = html[:ci + len(marker)] + json.dumps(cfg, ensure_ascii=False).replace('<', '\\u003c') + html[cj:]
    html = html.replace('</style>', '#ink path,#flows path,#pipes path{stroke:none !important}\n</style>', 1)
    html = html.replace(
        "$('spin').style.display=scan?'none':'';",
        "$('spin').style.display=scan?'none':'';\n  if($('geom')) $('geom').style.display=scan?'none':'';\n  if($('kept')) $('kept').style.display=scan?'none':'';",
        1,
    )
    html = html.replace(
        '全图重绘点亮版。默认是矢量几何、已确认字体，和尚未换字的原印文字。扫描整图只在原图对照里。动画为示意。',
        '全图重绘点亮版。几何按 809×596 源坐标规格。已确认字体留在原位。未辨字只留紧框。动画为示意。',
    )
    html = html.replace(
        '采用用户确认的轮周十二组原文，已写在主图对应彩点旁。未改的原印仍留在默认主图。动画为示意。',
        '全图重绘点亮版。几何按 809×596 源坐标规格。已确认字体留在原位。未辨字只留紧框。动画为示意。',
    )
    OUT.write_text(html, encoding='utf-8')
    for i, (rad, col) in enumerate(zip(RING_RADII, ring_colors)):
        inv.append({'id': f'ring{i}', 'type': 'circle-band', 'redrawn': True, 'r': rad, 'hex': hex_of(col),
                    'why': '色类按规格，不沿用先前采成米色的第3、第4、第9层'})
    report = {
        'html': OUT.name,
        'default_layer': '纸色底。六表 72 条短格、穹顶、五行轮、右下六行表、三道外围圆、双线辐条，都按源坐标。',
        'pure_geometry': '藏起待核字裁片后，矢量层仍在。中心花形内部曲线未描。',
        'stage': '混合阶段稿。几何和九环色序沿用 2887065，本轮只补确定被盖掉的字。默认仍有待核原字裁片，不是全矢量。',
        'restored_font': [t for t, *_rest in fixes] + ['阳', '阴'],
        'not_done': [
            '九环原微字和刻度没有转成字体。ring0-numerals 到 ring8-numerals 仍是待核，没有新写数字。',
            '五行轮外 5 个手写框待核，没有贴五行名。',
            '右下表细字待核。(576,507)-(588,518) 这一格没有可靠字，仍是缺字框。',
            '中心 (384,276)-(424,316) 仍是原曲线裁片，只另有 r20 圆边，不是矢量重绘。',
            'C9 (658,285)-(687,301) 原字不能确认，只留紧框，没有写成临泣或绝骨。',
            '规格没有逐字绑点的组保持待核。隐白、章门与邻行同一色块，没有重复绑定。脾俞这一行没有饱和色块。',
        ],
        'geometry': {
            'color_bars': len(bars),
            'circles': len(kept_organs),
            'named_dots': len(named_dots),
            'spleen_row_dots': len(spleen_bits),
            'pending_crops': len(side),
            'pending_boxes_without_ink': len(empty_pending),
            'name_dot_status': {
                '有点': sum(1 for s in name_status if s['status'] == '有点'),
                '待核': sum(1 for s in name_status if s['status'] == '待核'),
            },
            'rings': [{'r': r, 'hex': hex_of(c)} for r, c in zip(RING_RADII, ring_colors)],
        },
        'name_status': name_status,
        'empty_pending': empty_pending,
        'labels_from_previous': len(all_labels()),
    }
    COV.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    (ROOT / 'examples/b31-cunguan-siji/source_vs_vector_inventory.json').write_text(
        json.dumps({'coord': '809x596 source jpg', 'shapes': inv, 'names': name_status}, ensure_ascii=False, indent=2),
        encoding='utf-8')
    print('bars', len(bars), 'circles', len(kept_organs), 'named', len(named_dots), 'spleen', len(spleen_bits),
          '有点', report['geometry']['name_dot_status']['有点'],
          '待核', report['geometry']['name_dot_status']['待核'],
          'crops', len(side), 'empty', len(empty_pending))
    print('rings', [hex_of(c) for c in ring_colors])



if __name__ == '__main__':
    main_redraw()
