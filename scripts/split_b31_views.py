#!/usr/bin/env python3
"""把可播放的 B31 页拆成左、中、右三份独立 HTML。坐标仍是原图 809×596。"""
from __future__ import annotations

import base64
import io
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import data_url, subset_woff2  # noqa: E402

NS = '{http://www.w3.org/2000/svg}'
ET.register_namespace('', 'http://www.w3.org/2000/svg')
SRC = Path('examples/b31-cunguan-siji/b31-animation.html')
FONT = Path('/tmp/NotoSansCJKtc-Regular.otf')
SCAN = Path('/tmp/scans/b31.jpg')
OUT_DIR = Path('examples/b31-cunguan-siji')

# (x0, y0, x1, y1) 含一点交界，避免切到界上的圈和字。
PARTS = [
    {
        'file': 'part1-left.html',
        'key': 'left',
        'title': '寸关尺分区视图 1/3 左侧',
        'box': (0, 0, 318, 596),
        'note': '分区视图 1/3 左侧。这是全图左侧三表，不是完整图。表仍在原坐标。中央九环和右侧三表在另外两份里。',
    },
    {
        'file': 'part2-center.html',
        'key': 'center',
        'title': '寸关尺分区视图 2/3 中央',
        'box': (145, 0, 675, 596),
        'note': '分区视图 2/3 中央。这是九环、轮周十二组和外围连接，不是完整图。左右六表在另外两份里。',
    },
    {
        'file': 'part3-right.html',
        'key': 'right',
        'title': '寸关尺分区视图 3/3 右侧',
        'box': (540, 0, 809, 596),
        'note': '分区视图 3/3 右侧。这是全图右侧三表，不是完整图。表仍在原坐标。中央九环和左侧三表在另外两份里。',
    },
]
STRUCTURAL = {
    'stage', 'main', 'geom', 'spin', 'kept', 'ink', 'pipes', 'flows',
    'nodesBack', 'taiji', 'nodes', 'labels', 'caption', 'glowS',
    'bars', 'cell-frames', 'rules', 'organs', 'big-red', 'header-wings',
    'outer-brackets', 'sensory', 'periph', 'table-dots', 'named-dots',
    'spokes', 'crosses', 'legend-table', 'dot-brackets',
}


def nums(text: str) -> list[float]:
    return [float(n) for n in re.findall(r'-?\d+(?:\.\d+)?', text or '')]


def own_box(el) -> tuple[float, float, float, float] | None:
    tag = el.tag.split('}')[-1]
    if tag == 'circle' and el.get('cx') is not None:
        cx, cy, r = float(el.get('cx')), float(el.get('cy')), float(el.get('r') or 0)
        return (cx - r, cy - r, cx + r, cy + r)
    if tag in ('rect', 'image'):
        if el.get('id') in ('bg', 'raw'):
            return (0, 0, 809, 596)
        if el.get('width') and el.get('height'):
            x, y = float(el.get('x') or 0), float(el.get('y') or 0)
            return (x, y, x + float(el.get('width')), y + float(el.get('height')))
    if tag == 'line':
        xs = [float(el.get('x1')), float(el.get('x2'))]
        ys = [float(el.get('y1')), float(el.get('y2'))]
        return (min(xs), min(ys), max(xs), max(ys))
    if tag == 'path' and el.get('d'):
        vals = nums(el.get('d'))
        if len(vals) >= 2:
            return (min(vals), min(vals), max(vals), max(vals))
    if tag == 'text' and el.get('x') is not None:
        x, y = float(el.get('x')), float(el.get('y') or 0)
        return (x - 18, y - 12, x + 18, y + 12)
    if el.get('data-cx'):
        cx, cy = float(el.get('data-cx')), float(el.get('data-cy'))
        return (cx - 8, cy - 8, cx + 8, cy + 8)
    return None


def union(a, b):
    if a is None:
        return b
    if b is None:
        return a
    return (min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]))


def tree_box(el):
    box = own_box(el)
    for child in list(el):
        box = union(box, tree_box(child))
    return box


def hit(box, region, pad=0) -> bool:
    if box is None:
        return False
    x0, y0, x1, y1 = box
    a0, b0, a1, b1 = region
    return not (x1 < a0 - pad or x0 > a1 + pad or y1 < b0 - pad or y0 > b1 + pad)


def role_of(id_: str | None) -> str | None:
    if not id_:
        return None
    if id_ == 'frame':
        return 'all'
    if re.fullmatch(r'ring\d+', id_):
        return 'center'
    if id_.startswith((
        'spoke', 'node-ring', 'sector', 'node-chain', 'wuxing', 'w-',
        'legend', 'path-', 'periph', 'ndot', 'lead', 'spleen', 'dot-bracket', 'taiji',
    )) or id_ in ('spokes', 'crosses', 'named-dots', 'wuxing-wheel', 'taiji-edge'):
        return 'center'
    if id_.startswith('X') and id_[1:].isdigit():
        return 'center'
    if id_.startswith(('bar-L', 'cell-L', 'dash-L', 'wing-L', 'arc-L', 'head-L', 'tdot-L')):
        return 'left'
    if id_.startswith(('bar-R', 'cell-R', 'dash-R', 'wing-R', 'arc-R', 'head-R', 'tdot-R')):
        return 'right'
    if id_.startswith('seam-'):
        return 'left' if int(id_.split('-')[1]) < 3 else 'right'
    if re.fullmatch(r'C\d+', id_):
        return 'left' if int(id_[1:]) <= 6 else 'right'
    if id_.startswith(('sensory-', 'half-')):
        return 'left' if int(id_.split('-')[1]) < 2 else 'right'
    return None


def wants(key: str, role: str | None, box, region, eid: str | None) -> bool:
    if role == 'all':
        return True
    if role == key:
        return True
    # 左右页只多留伸进来的外圈弧、辐条端和跨区连线，不带走九环和五行轮。
    if (
        key != 'center' and eid and box and hit(box, region, 0)
        and (eid.startswith(('node-ring', 'sector', 'spoke', 'X')) or eid.startswith('sa') or eid.startswith('da'))
    ):
        return True
    if role is None and hit(box, region, 8):
        return True
    return False


def prune(el, key, region):
    for child in list(el):
        prune(child, key, region)
    tag = el.tag.split('}')[-1]
    if tag in ('svg', 'defs', 'filter', 'feGaussianBlur', 'feMerge', 'feMergeNode'):
        return
    eid = el.get('id')
    if eid in STRUCTURAL or eid in ('bg', 'raw'):
        return
    role = role_of(eid)
    box = tree_box(el)
    if wants(key, role, box, region):
        return
    parent = el.getparent() if hasattr(el, 'getparent') else None
    # ElementTree has no getparent. Caller passes parent.
    

def prune_children(parent, key, region):
    for child in list(parent):
        prune_children(child, key, region)
        tag = child.tag.split('}')[-1]
        if tag in ('defs', 'filter', 'feGaussianBlur', 'feMerge', 'feMergeNode'):
            continue
        eid = child.get('id')
        if eid in STRUCTURAL or eid in ('bg', 'raw'):
            continue
        role = role_of(eid)
        box = tree_box(child)
        if wants(key, role, box, region, eid):
            continue
        parent.remove(child)


def flow_box(flow):
    pts = flow.get('pts') or []
    if not pts:
        return None
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return (min(xs), min(ys), max(xs), max(ys))


def crop_scan(box):
    im = Image.open(SCAN).convert('RGB')
    x0, y0, x1, y1 = [int(v) for v in box]
    x1, y1 = min(im.width, x1), min(im.height, y1)
    part = im.crop((x0, y0, x1, y1))
    buf = io.BytesIO()
    part.save(buf, format='JPEG', quality=80)
    uri = 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode('ascii')
    return uri, x0, y0, x1 - x0, y1 - y0


def replace_font(html: str) -> str:
    chars = ''.join(sorted({c for c in html if ord(c) >= 32}))
    out = Path('/tmp/b31-part-subset.woff2')
    subset_woff2(chars, FONT, out, None)
    uri = data_url(out, 'font/woff2')
    html = re.sub(r'data:font/woff2;base64,[A-Za-z0-9+/=]+', uri, html, count=1)
    html = re.sub(
        r"@font-face\{font-family:'NotoTC';font-weight:700;src:url\(data:font/woff2;base64,[A-Za-z0-9+/=]+\) format\('woff2'\);\}",
        '',
        html,
        count=1,
    )
    html = html.replace('font-weight:400;src:url(' + uri, 'font-weight:400 700;src:url(' + uri, 1)
    return html


def build_one(text: str, part: dict) -> str:
    key = part['key']
    region = part['box']
    i = text.find('const CFG=')
    j = text.find('const NS=', i)
    cfg = json.loads(text[i + 10:j - 2])
    cfg['title'] = part['title']
    cfg['draft'] = False
    cfg['sub'] = part['note']
    cfg['note'] = part['note']
    cfg['uncertain'] = []
    cfg['labels'] = [lab for lab in cfg['labels'] if hit((lab['x'], lab['y'], lab['x'], lab['y']), region, 14)]
    cfg['nodes'] = [n for n in cfg['nodes'] if hit((n['x'] - 12, n['y'] - 12, n['x'] + 12, n['y'] + 12), region, 0)]
    kept_flows = []
    for flow in cfg['flows']:
        fid = flow.get('id') or ''
        box = flow_box(flow)
        if fid.startswith('ring'):
            if key == 'center':
                kept_flows.append(flow)
            continue
        if key == 'center' or (box and hit(box, region, 0) and max(box[2] - box[0], box[3] - box[1]) > 60):
            # 中央保留环、辐条和连线。左右只保留伸进本区的长线端，不带走九环。
            if key != 'center' and fid.startswith(('c', 'sp', 'sa', 'da', 'ring')):
                if box and hit(box, region, 0):
                    kept_flows.append(flow)
                continue
            kept_flows.append(flow)
    cfg['flows'] = kept_flows
    new_cfg = json.dumps(cfg, ensure_ascii=False).replace('<', '\\u003c')
    text = text[:i + 10] + new_cfg + text[j - 2:]

    a = text.find('<svg')
    b = text.find('</svg>') + 6
    root = ET.fromstring(text[a:b])
    prune_children(root, key, region)
    raw_uri, x, y, w, h = crop_scan(region)
    for el in root.iter(f'{NS}image'):
        if el.get('id') == 'raw':
            el.set('href', raw_uri)
            el.set('x', str(x))
            el.set('y', str(y))
            el.set('width', str(w))
            el.set('height', str(h))
    xml = ET.tostring(root, encoding='unicode')
    text = text[:a] + xml + text[b:]
    x0, y0, x1, y1 = region
    text = text.replace(
        "$('stage').setAttribute('viewBox',`0 0 ${W} ${H+78}`);",
        f"$('stage').setAttribute('viewBox','{x0} {y0} {x1 - x0} {y1 - y0}');",
        1,
    )
    text = re.sub(r'<title>.*?</title>', f'<title>{part["title"]}</title>', text, count=1)
    text = re.sub(
        r'<section class="corr" id="corr">.*?</section>',
        f'<section class="corr" id="corr"><h2>{part["title"]}</h2><p>{part["note"]}</p></section>',
        text,
        count=1,
        flags=re.S,
    )
    text = re.sub(r'<div class="extra">.*?</div>\s*', '', text, count=1, flags=re.S)
    return replace_font(text)


def main():
    text = SRC.read_text(encoding='utf-8')
    for part in PARTS:
        html = build_one(text, part)
        path = OUT_DIR / part['file']
        path.write_text(html, encoding='utf-8')
        print(part['file'], path.stat().st_size)


if __name__ == '__main__':
    main()
