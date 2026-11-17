#!/usr/bin/env python3
"""B/31 全图重绘点亮版。不覆盖补字版和文字版。"""
from __future__ import annotations

import base64
import io
import json
import subprocess
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
CFG = ROOT / 'examples/b31-cunguan-siji/config.json'
OUT = ROOT / 'examples/b31-cunguan-siji/寸关尺四季表里图_全图重绘点亮版.html'
COV = ROOT / 'examples/b31-cunguan-siji/coverage-全图重绘点亮.json'
WORK = Path('/tmp/b31redraw')
CX, CY = 404.0, 296.0
RING_RADII = [24.45, 32.0, 38.95, 45.95, 53.45, 60.45, 68.0, 74.95, 81.45]


def uri_png(im):
    buf = io.BytesIO()
    im.save(buf, format='PNG', optimize=True)
    return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode('ascii')


def uri_jpg(arr, q=90):
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format='JPEG', quality=q)
    return 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode('ascii')


def boost(rgb, sat=1.55, val=1.12):
    bgr = np.uint8([[rgb[::-1]]])
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[0, 0, 1] = min(255, hsv[0, 0, 1] * sat)
    hsv[0, 0, 2] = min(255, hsv[0, 0, 2] * val)
    out = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)[0, 0]
    return [int(out[2]), int(out[1]), int(out[0])]


def hex_of(rgb):
    return '#{:02x}{:02x}{:02x}'.format(*rgb)


def boxes():
    rows = list(READS) + list(EXTRA)
    for _t, _w, group in GROUPS:
        rows.extend(group)
    return rows


def text_mask(arr):
    gray = arr.mean(2)
    sat = arr.max(2).astype(int) - arr.min(2).astype(int)
    ink = ((gray < 145) & (sat < 58)).astype(np.uint8) * 255
    hk = cv2.getStructuringElement(cv2.MORPH_RECT, (16, 1))
    vk = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 14))
    lines = cv2.bitwise_or(cv2.morphologyEx(ink, cv2.MORPH_OPEN, hk), cv2.morphologyEx(ink, cv2.MORPH_OPEN, vk))
    return (ink > 0) & (lines == 0)


def main_redraw():
    WORK.mkdir(exist_ok=True)
    subprocess.check_call([
        sys.executable, str(ROOT / 'scripts/trace_hough.py'),
        '--image', str(SCAN), '--out', str(WORK / 'hough12.json'),
        '--min-length', '12', '--margin', '2,2,2,2',
    ])
    strips = [row for _t, _w, rows in GROUPS for row in rows]
    main(extra_labels=strips, out_html=OUT, coverage_path=COV, inner=True)
    scan = np.array(Image.open(SCAN).convert('RGB'))
    h, w = scan.shape[:2]
    yy, xx = np.mgrid[:h, :w]
    dist = np.sqrt((xx - CX) ** 2 + (yy - CY) ** 2)
    gray = scan.mean(2)

    # 纸色底，不再把整张扫描当默认几何。
    paper = np.full_like(scan, (248, 244, 232))
    # 九层色环：按原色提亮，刻度另抽成随环转动的墨点。
    ring_colors = []
    ring_pngs = []
    for i, rad in enumerate(RING_RADII):
        band = np.abs(dist - rad) <= 3.2
        cols = scan[band & (gray > 140)]
        med = np.median(cols, axis=0) if len(cols) else np.array([230, 220, 200])
        rgb = [int(v) for v in med]
        if float(np.mean(rgb)) > 225 and (max(rgb) - min(rgb)) < 28:
            rgb = [236, 228, 206]
        else:
            rgb = boost(rgb, 1.7, 1.08)
        ring_colors.append(rgb)
        marks = band & (gray < 165)
        ys, xs = np.where(marks)
        if len(xs) == 0:
            ring_pngs.append(None)
            continue
        x0, x1 = int(xs.min()), int(xs.max()) + 1
        y0, y1 = int(ys.min()), int(ys.max()) + 1
        rgba = np.zeros((y1 - y0, x1 - x0, 4), np.uint8)
        local = marks[y0:y1, x0:x1]
        rgba[local, :3] = 25
        rgba[local, 3] = 230
        ring_pngs.append((uri_png(Image.fromarray(rgba)), x0, y0, x1 - x0, y1 - y0))

    # 太极：保黑白结构，只提高彩色部分的饱和。
    taiji = dist <= 19.6
    ys, xs = np.where(taiji)
    x0, x1 = int(xs.min()), int(xs.max()) + 1
    y0, y1 = int(ys.min()), int(ys.max()) + 1
    sub = scan[y0:y1, x0:x1].copy()
    hsv = cv2.cvtColor(sub, cv2.COLOR_RGB2HSV).astype(np.float32)
    colorful = hsv[:, :, 1] > 30
    hsv[:, :, 1] = np.where(colorful, np.minimum(255, hsv[:, :, 1] * 1.45), hsv[:, :, 1])
    hsv[:, :, 2] = np.where(colorful, np.minimum(255, hsv[:, :, 2] * 1.06), hsv[:, :, 2])
    sub = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB)
    taiji_png = uri_png(Image.fromarray(sub))

    # 未换字体的原印：只留深色文字像素，长线和色块不带回来。
    keep = text_mask(scan)
    keep &= dist > 88
    keep &= ~taiji
    for t, x0b, y0b, x1b, y1b, zone in boxes():
        keep[max(0, y0b - 1):y1b + 1, max(0, x0b - 1):x1b + 1] = False
    ink_rgba = np.zeros((h, w, 4), np.uint8)
    ink_rgba[keep, :3] = 20
    ink_rgba[keep, 3] = 220
    ink_uri = uri_png(Image.fromarray(ink_rgba))

    # 十二组穴名旁的彩点：在字框左侧取原色，再提亮。
    dots = []
    sat = scan.max(2).astype(int) - scan.min(2).astype(int)
    for title, where, rows in GROUPS:
        for name, x0b, y0b, x1b, y1b, zone in rows:
            wx0, wx1 = max(0, x0b - 8), min(w, x0b + 16)
            wy0, wy1 = max(0, y0b - 2), min(h, y1b + 2)
            window = sat[wy0:wy1, wx0:wx1]
            weak = False
            if window.size and int(window.max()) > 22:
                sel = window >= max(22, int(window.max()) * 0.65)
                ys, xs = np.where(sel)
                px = int(wx0 + np.median(xs))
                py = int(wy0 + np.median(ys))
                rgb = boost([int(v) for v in np.median(scan[wy0:wy1, wx0:wx1][sel], axis=0)], 1.8, 1.12)
            else:
                sl = gray[wy0:wy1, wx0:wx1]
                if sl.size and sl.min() < 170:
                    iy, ix = np.unravel_index(int(sl.argmin()), sl.shape)
                    px, py = wx0 + int(ix), wy0 + int(iy)
                    rgb = [232, 230, 226]
                else:
                    px, py = max(0, x0b - 8), min(h - 1, (y0b + y1b) // 2)
                    rgb = [232, 230, 226]
                    weak = True
            if px >= x0b - 1:
                px, py = max(0, x0b - 8), min(h - 1, (y0b + y1b) // 2)
            dots.append({
                'name': name, 'group': title, 'where': where,
                'x': px, 'y': py, 'rgb': rgb, 'hex': hex_of(rgb), 'weak_sample': weak,
            })

    # 轮外较大色圆：按原色提亮后画实心圆。
    color = (sat > 42) & (scan.max(2) > 80) & (dist > 92)
    vis = np.zeros(color.shape, bool)
    disks = []
    from collections import deque
    for y in range(0, h, 2):
        xs = np.where(color[y])[0]
        for x in xs[::2]:
            if vis[y, x]:
                continue
            q = deque([(y, x)])
            vis[y, x] = True
            pts = []
            while q:
                cy, cx = q.pop()
                pts.append((cy, cx))
                for dy in (-2, 0, 2):
                    for dx in (-2, 0, 2):
                        ny, nx = cy + dy, cx + dx
                        if 0 <= ny < h and 0 <= nx < w and color[ny, nx] and not vis[ny, nx]:
                            vis[ny, nx] = True
                            q.append((ny, nx))
            if not 40 <= len(pts) <= 900:
                continue
            ys = np.array([p[0] for p in pts])
            xs = np.array([p[1] for p in pts])
            bw, bh = int(xs.max() - xs.min()), int(ys.max() - ys.min())
            if bw < 8 or bh < 8 or not 0.55 <= bw / max(bh, 1) <= 1.8:
                continue
            ccx, ccy = float(xs.mean()), float(ys.mean())
            rad = max(bw, bh) / 2
            sample = scan[int(ccy), int(ccx)]
            disks.append({
                'x': round(ccx, 1), 'y': round(ccy, 1), 'r': round(float(rad), 1),
                'hex': hex_of(boost([int(v) for v in sample], 1.5, 1.12)),
            })

    hough = json.loads((WORK / 'hough12.json').read_text())
    grid = []
    for x1, y1, x2, y2 in hough:
        dx, dy = x2 - x1, y2 - y1
        length = (dx * dx + dy * dy) ** 0.5
        if length < 16:
            continue
        ang = abs(np.degrees(np.arctan2(dy, dx))) % 180
        if min(ang, 180 - ang) > 12 and abs(ang - 90) > 12:
            continue
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        if ((mx - CX) ** 2 + (my - CY) ** 2) ** 0.5 < 150:
            continue
        grid.append([round(x1, 1), round(y1, 1), round(x2, 1), round(y2, 1)])

    cfg = json.loads(CFG.read_text())
    flows = [it for it in cfg['items'] if it.get('type') == 'flow']
    geom = ['<g id="geom">', '<g id="disks">']
    for i, d in enumerate(disks):
        geom.append(
            f'<circle cx="{d["x"]}" cy="{d["y"]}" r="{d["r"]}" fill="{d["hex"]}" '
            f'stroke="#222" stroke-width="1.1"/>'
        )
        geom.append(
            f'<circle data-glow="1" data-ph="{i * 0.17:.2f}" cx="{d["x"]}" cy="{d["y"]}" '
            f'r="{max(2, d["r"] * 0.45):.1f}" fill="none" stroke="#fff" stroke-width="1.2" opacity="0.7"/>'
        )
    geom.append('</g>')
    geom.append(f'<image id="inktext" href="{ink_uri}" x="0" y="0" width="{w}" height="{h}"/>')
    geom.append('<g id="grid" fill="none" stroke="#1c1c1c" stroke-width="1.05" stroke-linecap="square">')
    for x1, y1, x2, y2 in grid:
        geom.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"/>')
    geom.append('</g><g id="dots">')
    for i, d in enumerate(dots):
        geom.append(
            f'<circle cx="{d["x"]}" cy="{d["y"]}" r="3.1" fill="{d["hex"]}" stroke="#222" stroke-width="0.6"/>'
        )
        geom.append(
            f'<circle data-glow="1" data-ph="{i * 0.13:.2f}" cx="{d["x"]}" cy="{d["y"]}" r="4.4" '
            f'fill="none" stroke="{d["hex"]}" stroke-width="1.1" opacity="0.8"/>'
        )
    geom.append('</g></g>')
    geom_svg = ''.join(geom)

    html = OUT.read_text(encoding='utf-8')
    key = '<image id="bg" href="'
    i = html.find(key)
    j = html.find('"', i + len(key))
    html = html[:i + len(key)] + uri_jpg(paper) + html[j:]
    # 几何层插在底图之后、旋转层之前。
    anchor = '<g id="spin">'
    html = html.replace(anchor, geom_svg + anchor, 1)
    for n, rad in enumerate(RING_RADII):
        token = f'<g id="ring{n}"'
        k = html.find(token)
        img = html.find('<image ', k)
        end = html.find('/>', img) + 2
        color = hex_of(ring_colors[n])
        piece = (
            f'<circle cx="{CX}" cy="{CY}" r="{rad}" fill="none" stroke="{color}" stroke-width="6.4"/>'
        )
        if ring_pngs[n]:
            href, x, y, ww, hh = ring_pngs[n]
            piece += f'<image href="{href}" x="{x}" y="{y}" width="{ww}" height="{hh}"/>'
        html = html[:img] + piece + html[end:]
    tk = html.find('<g id="taiji"')
    img = html.find('<image ', tk)
    q1 = html.find('"', img + len('<image href="'))
    # href is the next quoted value
    href_at = html.find('href="', img) + 6
    href_end = html.find('"', href_at)
    html = html[:href_at] + taiji_png + html[href_end:]
    html = html.replace(
        "$('spin').style.display=scan?'none':'';",
        "$('spin').style.display=scan?'none':'';\n  if($('geom')) $('geom').style.display=scan?'none':'';",
        1,
    )
    html = html.replace(
        "el.setAttribute('transform','rotate('+deg.toFixed(3)+' '+el.getAttribute('data-cx')+' '+el.getAttribute('data-cy')+')');\n  });",
        "el.setAttribute('transform','rotate('+deg.toFixed(3)+' '+el.getAttribute('data-cx')+' '+el.getAttribute('data-cy')+')');\n  });\n"
        "  document.querySelectorAll('[data-glow]').forEach(el=>{\n"
        "    const a=0.45+0.55*Math.abs(Math.sin((u*8+(+el.getAttribute('data-ph')))*Math.PI));\n"
        "    el.setAttribute('opacity', a.toFixed(3));\n"
        "  });",
        1,
    )
    html = html.replace(
        '采用用户确认的轮周十二组原文，已写在主图对应彩点旁。未改的原印仍留在默认主图。动画为示意。',
        '全图重绘点亮版。默认是矢量几何、已确认字体，和尚未换字的原印文字。扫描整图只在原图对照里。动画为示意。',
        1,
    )
    OUT.write_text(html, encoding='utf-8')
    report = json.loads(COV.read_text(encoding='utf-8'))
    report['redraw'] = {
        'html': OUT.name,
        'default': '纸色底 + 矢量线圆 + 已确认字体 + 未换字的原印文字层。整张扫描不在默认层。',
        'tools': {
            'trace_hough_min45': 246,
            'trace_hough_min12': len(hough),
            'trace_dashes_chains': 0,
            'config_flows': {
                'rings': 9, 'spokes': 12, 'gold': 12, 'dashed': 4, 'black': 2, 'nodes': 12,
            },
        },
        'geometry': {
            'frame_and_grid_lines': len(grid),
            'rings': 9,
            'ring_colors': [hex_of(c) for c in ring_colors],
            'colored_disks': len(disks),
            'named_dots': len(dots),
            'inktext_pixels': int(keep.sum()),
            'confirmed_boxes_erased': len(boxes()),
        },
        'dots': dots,
        'disks': disks,
        'flows_kept_from_config': len(flows),
        'dash_tracer': 'trace_dashes 串成 0 条。虚线用 config 里已经描好的 4 条 dashed。',
    }
    COV.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('grid', len(grid), 'dots', len(dots), 'disks', len(disks), 'ink', int(keep.sum()), 'MB', round(OUT.stat().st_size / 1e6, 2))


if __name__ == '__main__':
    main_redraw()
