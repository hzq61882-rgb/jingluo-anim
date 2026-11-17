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
from build_b31_spin import EXTRA, MANUAL_CIRCLES, main  # noqa: E402

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
    strips = [row for _t, _w, rows in GROUPS for row in rows]
    main(extra_labels=strips, out_html=OUT, coverage_path=COV, inner=True)
    scan = np.array(Image.open(SCAN).convert('RGB'))
    h, w = scan.shape[:2]
    paper = np.full_like(scan, (248, 244, 232))

    yy, xx = np.mgrid[:h, :w]
    dist = np.sqrt((xx - CX) ** 2 + (yy - CY) ** 2)
    gray = scan.mean(2)
    ring_colors = []
    for rad in RING_RADII:
        band = (np.abs(dist - rad) <= 2.4) & (gray > 150)
        med = np.median(scan[band], 0) if band.any() else np.array([220, 210, 190])
        rgb = [int(v) for v in med]
        if max(rgb) - min(rgb) < 26 and np.mean(rgb) > 210:
            rgb = [232, 214, 150]
        else:
            rgb = boost(rgb, 1.85, 1.06)
        ring_colors.append(rgb)

    # 签名只留紧框里的深色字，不带表格线。
    sig = scan[546:576, 688:786].copy()
    sg = sig.mean(2)
    alpha = np.zeros(sig.shape[:2], np.uint8)
    alpha[(sg < 80)] = 230
    sig_rgba = np.zeros((*sig.shape[:2], 4), np.uint8)
    sig_rgba[..., :3] = 20
    sig_rgba[..., 3] = alpha
    sig_uri = uri_png(Image.fromarray(sig_rgba))

    parts = ['<g id="geom">']
    parts.append('<rect x="32" y="20" width="748" height="556" fill="none" stroke="#161616" stroke-width="1.6"/>')
    columns = [
        (72, 112, 88, 214), (116, 158, 88, 214),
        (72, 112, 248, 360), (116, 162, 248, 360),
        (70, 112, 395, 525), (116, 160, 395, 525),
        (662, 704, 82, 210), (708, 758, 82, 210),
        (662, 704, 225, 355), (708, 758, 225, 355),
        (648, 704, 385, 525), (708, 764, 385, 525),
    ]
    bars = []
    for x0, x1, y0, y1 in columns:
        bars.extend(column_bars(scan, x0, x1, y0, y1))
    parts.append('<g id="bars">')
    for b in bars:
        parts.append(f'<rect x="{b["x"]}" y="{b["y"]}" width="{b["w"]}" height="{b["h"]}" fill="{b["hex"]}"/>')
    parts.append('</g>')
    parts.append('<circle id="node-ring-outer" cx="404" cy="296" r="229" fill="none" stroke="#1a1a1a" stroke-width="1.15"/>')
    parts.append('<circle id="node-ring-inner" cx="404" cy="296" r="203" fill="none" stroke="#1a1a1a" stroke-width="1.05"/>')
    # 右下小图例：按测到的格线画，格子填原色。
    leg_x = [556, 570, 582, 594]
    leg_y = [506, 519, 532]
    parts.append('<g id="legend-table">')
    for i in range(len(leg_x) - 1):
        for j in range(len(leg_y) - 1):
            rgb, _s = sample_box(scan, leg_x[i] + 1, leg_y[j] + 1, leg_x[i + 1] - 1, leg_y[j + 1] - 1)
            parts.append(
                f'<rect id="leg-{j}-{i}" x="{leg_x[i]}" y="{leg_y[j]}" width="{leg_x[i+1]-leg_x[i]}" '
                f'height="{leg_y[j+1]-leg_y[j]}" fill="{hex_of(rgb)}" stroke="#222" stroke-width="0.7"/>'
            )
    parts.append('</g>')
    parts.append('<g id="rules" fill="none" stroke="#1a1a1a" stroke-width="1.05">')
    for x0, x1, y0, y1 in columns:
        for y in column_rules(scan, x0, x1, y0, y1):
            parts.append(f'<line x1="{x0}" y1="{y}" x2="{x1}" y2="{y}"/>')
    for x, y0, y1 in ((114, 96, 206), (114, 268, 352), (115, 408, 518),
                      (706, 90, 200), (706, 248, 348), (705, 400, 516)):
        parts.append(f'<line x1="{x}" y1="{y0}" x2="{x}" y2="{y1}"/>')
    parts.append('</g>')

    # 表头成对大圆，以及已经定位的穴圆。每圆只画一次。
    heads = [
        (104, 76, 12, '神'), (128, 76, 12, '火'),
        (104, 228, 13, '意'), (128, 228, 13, '土'),
        (104, 384, 13, '魄'), (128, 384, 13, '金'),
        (690, 70, 13, '志'), (722, 70, 13, '水'),
        (690, 222, 13, '魂'), (722, 222, 13, '木'),
        (694, 376, 13, '神'), (722, 376, 13, '火'),
    ]
    organs = []
    parts.append('<g id="organs">')
    for cx, cy, r, name in heads:
        rgb, _sat = sample_box(scan, int(cx - 6), int(cy - 6), int(cx + 6), int(cy + 6))
        organs.append({'name': name, 'x': cx, 'y': cy, 'r': r, 'hex': hex_of(boost(rgb))})
    for c in MANUAL_CIRCLES:
        rgb, _sat = sample_box(scan, int(c['cx'] - 5), int(c['cy'] - 5), int(c['cx'] + 5), int(c['cy'] + 5))
        organs.append({'name': c['name'], 'x': c['cx'], 'y': c['cy'], 'r': c['r'], 'hex': hex_of(boost(rgb))})
    # 去掉叠在一起的重复圆。
    kept_organs = []
    for item in organs:
        if any((item['x'] - o['x']) ** 2 + (item['y'] - o['y']) ** 2 < 12 ** 2 for o in kept_organs):
            continue
        kept_organs.append(item)
    for i, item in enumerate(kept_organs):
        parts.append(
            f'<circle cx="{item["x"]}" cy="{item["y"]}" r="{item["r"]}" fill="{item["hex"]}" '
            f'stroke="#222" stroke-width="1.2"/>'
        )
        parts.append(
            f'<circle data-glow="1" data-ph="{i * 0.2:.2f}" cx="{item["x"]}" cy="{item["y"]}" '
            f'r="{item["r"]}" fill="none" stroke="#fff" stroke-width="1.3" '
            f'stroke-dasharray="4 10" opacity="0.85"/>'
        )
    parts.append('</g>')

    # 底部图例的两条样线，字在已有标签上。
    parts.append(
        '<line x1="468" y1="520" x2="502" y2="520" stroke="#222" stroke-width="1.3" stroke-dasharray="3 2"/>'
        '<line x1="468" y1="532" x2="502" y2="532" stroke="#222" stroke-width="1.6"/>'
    )

    raw_dots = detect_dots(scan)
    # 同一位置只留一颗。
    dots_unique = []
    for d in raw_dots:
        if any((d['x'] - o['x']) ** 2 + (d['y'] - o['y']) ** 2 < 7 ** 2 for o in dots_unique):
            continue
        dots_unique.append(d)
    name_status = []
    used = set()
    for title, where, rows in GROUPS:
        for name, x0, y0, x1, y1, zone in rows:
            hit = row_dot(scan, x0, y0, x1, y1)
            if hit is None:
                name_status.append({'name': name, 'group': title, 'status': '待核', 'y': y0,
                                    'why': '这一行没有采到饱和度够高的色块，不能据此说原图没有点'})
            else:
                px, py, rgb, sat = hit
                if any((px - d['x']) ** 2 + (py - d['y']) ** 2 < 36 for d in dots_unique):
                    pass
                else:
                    dots_unique.append({'x': px, 'y': py, 'hex': hex_of(rgb)})
                name_status.append({
                    'name': name, 'group': title, 'status': '有点',
                    'x': px, 'y': py, 'hex': hex_of(rgb), 'sat': sat,
                })
    parts.append('<g id="dots">')
    for i, d in enumerate(dots_unique):
        parts.append(
            f'<circle cx="{d["x"]}" cy="{d["y"]}" r="3.1" fill="{d["hex"]}" stroke="#222" stroke-width="0.5"/>'
        )
        parts.append(
            f'<circle data-glow="1" data-ph="{i * 0.17:.2f}" cx="{d["x"]}" cy="{d["y"]}" r="3.1" '
            f'fill="none" stroke="{d["hex"]}" stroke-width="1.05" opacity="0.75"/>'
        )
    parts.append('</g></g>')
    # 未替换文字：去掉长线和已换字框后，按连通域做紧框。
    ink = ((gray < 120) & ((scan.max(2).astype(int) - scan.min(2).astype(int)) < 42))
    ink_u8 = ink.astype(np.uint8) * 255
    hk = cv2.getStructuringElement(cv2.MORPH_RECT, (14, 1))
    vk = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 12))
    lines = cv2.bitwise_or(cv2.morphologyEx(ink_u8, cv2.MORPH_OPEN, hk), cv2.morphologyEx(ink_u8, cv2.MORPH_OPEN, vk))
    keep = ink & (lines == 0) & (dist > 90)
    for _n, x0, y0, x1, y1, _z in all_labels():
        keep[max(0, y0 - 6):y1 + 7, max(0, x0 - 6):x1 + 7] = False
    side = [s for s in glyph_sprites(scan, keep, 400)
            if ((s[0] + s[2] / 2 - CX) ** 2 + (s[1] + s[3] / 2 - CY) ** 2) ** 0.5 > 210
            and s[4] >= 28 and s[2] >= 5 and s[3] >= 5]
    kept = ['<g id="kept">']
    for x, y, ww, hh, _a in side:
        png = sprite_png(scan, x, y, ww, hh, keep)
        if png:
            kept.append(f'<image href="{png}" x="{x}" y="{y}" width="{ww}" height="{hh}"/>')
    kept.append('</g>')
    ring_glyphs = [[] for _ in RING_RADII]
    for i, rad in enumerate(RING_RADII):
        band = (np.abs(dist - rad) <= 3.0) & (gray < 105) & ((scan.max(2).astype(int) - scan.min(2).astype(int)) < 40)
        for x, y, ww, hh, _a in glyph_sprites(scan, band, 80):
            png = sprite_png(scan, x, y, ww, hh, band)
            if png:
                ring_glyphs[i].append((png, x, y, ww, hh))
    geom = ''.join(parts) + ''.join(kept)

    # 环上短刻度，随环转，不用扫描碎点。
    def ticks(rad, color):
        bits = []
        dark = boost(color, 1.0, 0.55)
        for k in range(36):
            ang = np.radians(k * 10 - 90)
            r0, r1 = rad - 2.1, rad + 2.1
            x1 = CX + r0 * np.cos(ang)
            y1 = CY + r0 * np.sin(ang)
            x2 = CX + r1 * np.cos(ang)
            y2 = CY + r1 * np.sin(ang)
            bits.append(
                f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                f'stroke="{hex_of(dark)}" stroke-width="0.8"/>'
            )
        return ''.join(bits)

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
            f'stroke-width="6.6"/>'
        )
        for png, x, y, ww, hh in ring_glyphs[n]:
            piece += f'<image href="{png}" x="{x}" y="{y}" width="{ww}" height="{hh}"/>'
        html = html[:img] + piece + html[end:]
    # 太极只留提亮后的原图圆盘，外加一道矢量圆边。扫描碎点不进环。
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
    # 删掉自动散点的偏心虚线圈。大圆的光晕已经画在同一圆心上。
    html = re.sub(r'<g id="dot\d+"[^>]*>.*?</g>', '', html)
    html = html.replace(
        "$('spin').style.display=scan?'none':'';",
        "$('spin').style.display=scan?'none':'';\n  if($('geom')) $('geom').style.display=scan?'none':'';\n  if($('kept')) $('kept').style.display=scan?'none':'';",
        1,
    )
    html = html.replace(
        "el.setAttribute('transform','rotate('+deg.toFixed(3)+' '+el.getAttribute('data-cx')+' '+el.getAttribute('data-cy')+')');\n  });",
        "el.setAttribute('transform','rotate('+deg.toFixed(3)+' '+el.getAttribute('data-cx')+' '+el.getAttribute('data-cy')+')');\n  });\n"
        "  document.querySelectorAll('[data-glow]').forEach(el=>{\n"
        "    const a=0.35+0.65*Math.abs(Math.sin((u*8+(+el.getAttribute('data-ph')))*Math.PI));\n"
        "    el.setAttribute('stroke-opacity', a.toFixed(3));\n"
        "  });",
        1,
    )
    html = html.replace(
        '全图重绘点亮版。默认是矢量几何、已确认字体，和尚未换字的原印文字。扫描整图只在原图对照里。动画为示意。',
        '全图重绘点亮版。默认是矢量表格、色环、圆和已确认字体。原图整页只在对照里。签名是单独的字裁片。动画为示意。',
    )
    # 上一轮可能没这句话，补在 note 字段。
    html = html.replace(
        '采用用户确认的轮周十二组原文，已写在主图对应彩点旁。未改的原印仍留在默认主图。动画为示意。',
        '全图重绘点亮版。默认是矢量表格、色环、圆和已确认字体。原图整页只在对照里。签名是单独的字裁片。动画为示意。',
    )
    OUT.write_text(html, encoding='utf-8')
    report = {
        'html': OUT.name,
        'default_layer': '纸色底、参数化六区表格、九层色带、单圆心穴点、已确认字体、签名裁片。没有整页墨层，没有霍夫碎线。',
        'pure_geometry': '隐藏签名裁片和原图对照后，只剩矢量形状和字体。',
        'not_done': [
            '六区横条和横线按原图列宽重画，还不是每一格的弧形括号都逐段复刻。',
            '环上原印以紧框深色裁片随环转动，没有认成字体。',
            '没有彩点的穴名不新造点。',
        ],
        'geometry': {
            'frame': 1,
            'color_bars': len(bars),
            'organ_circles': len(kept_organs),
            'original_dots': len(dots_unique),
            'name_dot_status': {
                '有点': sum(1 for s in name_status if s['status'] == '有点'),
                '待核': sum(1 for s in name_status if s['status'] == '待核'),
            },
            'side_text_crops': len(side),
            'ring_glyph_crops': [len(g) for g in ring_glyphs],
            'rings': [{'r': r, 'hex': hex_of(c)} for r, c in zip(RING_RADII, ring_colors)],
            'config_paths_kept': {'spokes': 12, 'gold': 12, 'dashed': 4, 'black': 2, 'nodes': 12},
        },
        'dots': dots_unique,
        'name_status': name_status,
        'bars': bars,
        'organs': kept_organs,
        'labels_from_previous': len(all_labels()),
    }
    COV.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    inv = []
    inv.append({'id': 'frame', 'type': 'rect', 'redrawn': True, 'new_id': 'frame',
                'box': [32, 20, 780, 576]})
    inv.append({'id': 'node-ring-outer', 'type': 'circle', 'redrawn': True, 'cx': 404, 'cy': 296, 'r': 229,
                'why': '外圈序号圆所在的大圆，原图 r≈229 的深色圆弧'})
    inv.append({'id': 'node-ring-inner', 'type': 'circle', 'redrawn': True, 'cx': 404, 'cy': 296, 'r': 203,
                'why': '内圈序号圆所在的大圆'})
    for i, (r, c) in enumerate(zip(RING_RADII, ring_colors)):
        inv.append({'id': f'ring{i}', 'type': 'circle-band', 'redrawn': True, 'r': r, 'hex': hex_of(c)})
    inv.append({'id': 'legend-table', 'type': 'grid', 'redrawn': True,
                'x': leg_x, 'y': leg_y, 'why': '右下小图例按测到的格线重画，格内字仍是小裁片或未全转写'})
    inv.append({'id': 'wuxing-wheel', 'type': 'circle', 'redrawn': False,
                'why': '在 (110,500)-(260,575) 没有找到五色分瓣小轮，这一项未画，避免把别的圆错当成它'})
    for b in bars:
        inv.append({'id': f'bar-{b["x"]}-{b["y"]}', 'type': 'color-bar', 'redrawn': True, **b})
    (ROOT / 'examples/b31-cunguan-siji/source_vs_vector_inventory.json').write_text(
        json.dumps({'shapes': inv, 'dots': dots_unique, 'names': name_status}, ensure_ascii=False, indent=2),
        encoding='utf-8')
    print('bars', len(bars), 'organs', len(kept_organs), 'dots', len(dots_unique),
          '有点', sum(1 for s in name_status if s['status'] == '有点'),
          '待核', sum(1 for s in name_status if s['status'] == '待核'),
          'side', len(side), 'ringglyphs', [len(g) for g in ring_glyphs])
    print('rings', [hex_of(c) for c in ring_colors])


if __name__ == '__main__':
    main_redraw()
