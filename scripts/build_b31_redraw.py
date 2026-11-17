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

    # 六区彩条：按已确认字框取样，画完整横条，不描碎线。
    bars = []
    for name, x0, y0, x1, y1, zone in READS:
        if name in SKIP_BAR or (x1 - x0) > 40:
            continue
        if zone not in ('rw-hi', 'rw-mid', 'rw-lo', 'lw-hi', 'lw-mid', 'lw-lo'):
            continue
        rgb, sat = sample_box(scan, x0 - 2, y0, x1 + 2, y1)
        if sat < 12:
            continue
        col = boost(rgb, 1.7, 1.05)
        parts.append(
            f'<rect x="{x0 - 1}" y="{y0}" width="{x1 - x0 + 2}" height="{max(6, y1 - y0)}" '
            f'rx="0.6" fill="{hex_of(col)}" stroke="#222" stroke-width="0.4"/>'
        )
        bars.append({'name': name, 'zone': zone, 'x': x0, 'y': y0, 'hex': hex_of(col)})

    # 六区外框和中缝。范围按各区字框，线是一整段。
    frames = [
        (42, 44, 196, 198),
        (42, 202, 196, 358),
        (42, 362, 208, 546),
        (632, 40, 784, 196),
        (646, 200, 784, 356),
        (632, 360, 784, 546),
    ]
    seams = [115, 115, 116, 706, 705, 704]
    parts.append('<g id="tables" fill="none" stroke="#1a1a1a" stroke-width="1.15">')
    for (x, y, x2, y2), seam in zip(frames, seams):
        parts.append(f'<rect x="{x}" y="{y}" width="{x2 - x}" height="{y2 - y}" rx="3"/>')
        parts.append(f'<line x1="{seam}" y1="{y + 28}" x2="{seam}" y2="{y2 - 8}"/>')
        # 表头括号：上沿一条，两端向下。
        parts.append(f'<path d="M{x + 6} {y + 26} v-8 h{x2 - x - 12} v8"/>')
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

    dots = []
    missed = []
    parts.append('<g id="dots">')
    seen = set()
    for gi, (title, where, rows) in enumerate(GROUPS):
        for name, x0, y0, x1, y1, zone in rows:
            found = dot_for(scan, x0, y0, x1, y1)
            key = (name, x0, y0)
            if key in seen:
                continue
            seen.add(key)
            if found is None:
                missed.append({'name': name, 'group': title, 'x0': x0, 'y0': y0})
                continue
            px, py, rgb, sat = found
            dots.append({
                'name': name, 'group': title, 'where': where,
                'x': px, 'y': py, 'hex': hex_of(rgb), 'sat': sat,
            })
            parts.append(
                f'<circle cx="{px}" cy="{py}" r="3.15" fill="{hex_of(rgb)}" stroke="#222" stroke-width="0.55"/>'
            )
            parts.append(
                f'<circle data-glow="1" data-ph="{(len(dots) * 0.17):.2f}" cx="{px}" cy="{py}" r="3.15" '
                f'fill="none" stroke="{hex_of(rgb)}" stroke-width="1.15" opacity="0.8"/>'
            )
    parts.append('</g>')
    parts.append(f'<image id="kept-sign" href="{sig_uri}" x="688" y="546" width="98" height="30"/>')
    parts.append('</g>')
    geom = ''.join(parts)

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
            f'stroke-width="6.6"/>' + ticks(rad, ring_colors[n])
        )
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
        "$('spin').style.display=scan?'none':'';\n  if($('geom')) $('geom').style.display=scan?'none':'';",
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
            '环上原印序号没有逐个认成字体，这一版用整齐短刻度表示自转，不把扫描碎点铺回环上。',
            '表外手写旁注里还没有单独字框的，没有整页铺回；只有签名做了紧框裁片。',
        ],
        'geometry': {
            'frame': 1,
            'table_frames': len(frames),
            'seams': len(seams),
            'color_bars': len(bars),
            'organ_circles': len(kept_organs),
            'named_dots': len(dots),
            'dots_without_saturated_sample': missed,
            'rings': [{'r': r, 'hex': hex_of(c)} for r, c in zip(RING_RADII, ring_colors)],
            'config_paths_kept': {'spokes': 12, 'gold': 12, 'dashed': 4, 'black': 2, 'nodes': 12},
        },
        'dots': dots,
        'bars': bars,
        'organs': kept_organs,
        'labels_from_previous': len(all_labels()),
    }
    COV.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('bars', len(bars), 'organs', len(kept_organs), 'dots', len(dots), 'missed', len(missed))
    print('rings', [hex_of(c) for c in ring_colors])


if __name__ == '__main__':
    main_redraw()
