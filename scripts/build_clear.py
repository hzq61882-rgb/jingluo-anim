#!/usr/bin/env python3
"""从原图核对过的文字和已有路径生成清晰重绘 HTML。不改原成片。

核对完的页默认只显示矢量。还在逐区誊写的页是工作稿，原图对照默认打开。
单个认不出的字才标待核；没有核对完的整页不把文字清成空白。
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import data_url, subset_woff2  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FONT = Path('/tmp/NotoSansCJKtc-Regular.otf')
TPL = ROOT / 'template' / 'clear.html'
FLOW = ROOT / 'template' / 'flow.js'

GLOW = {'木': '#3fdc5a', '火': '#ff3b30', '土': '#ffd60a', '金': '#ffffff', '水': '#2f80ff'}
DARK = {'木': '#2f8a3c', '火': '#c0201c', '土': '#caa005', '金': '#5c6370', '水': '#1e5bb8'}

# 已经逐区看过原图、可以当成成品的页。其余是工作稿。
FINISHED = {'b24', 'b28'}

# 工作稿里尚未钉死坐标的区块。不是「整页没有字」。
ZONES = {
    'b31': [
        {'id': 'wheel', 'status': 'lines', 'note': '九层色环、轮辐和序号链沿已描路径重绘。轮内图例按约 14 像素高的横条逐条裁过，单字只有 6 到 8 像素，对不成一个词，没有写入。序号圆里的数字同样没有写入。'},
        {'id': 'right-table', 'status': 'partial', 'note': '右侧能单独看清的字按该字墨迹框对齐，并只盖住这些旧笔画。红圆压住和裁开后不成字的格子没有补。'},
        {'id': 'left-table', 'status': 'partial', 'note': '左侧逐格裁过。能读成一个词的按墨迹框写入并盖住旧笔画。红圆里的字和裁不开的格子没有补。'},
    ],
    'b45': [
        {'id': 'bands', 'status': 'lines', 'note': '左侧六经色带、右椭圆、交会穴横线、玉龍色条和六条奇经横线沿已描路径流动。'},
        {'id': 'titles', 'status': 'done', 'note': '五行、六经名、交會穴、母、子、神應經、玉龍按原图大字位置写入。'},
        {'id': 'grid', 'status': 'reading', 'note': '交会穴下方的络穴小字和椭圆内细字还在逐区钉坐标，原图对照开着。'},
    ],
    'b1': [
        {'id': 'axis', 'status': 'lines', 'note': '中轴、彩线和弧沿已描路径重绘。'},
        {'id': 'labels', 'status': 'reading', 'note': '花形、柱内和斜轴旁的小字还在逐区誊写，原图对照开着。'},
    ],
    'b39': [
        {'id': 'title', 'status': 'done', 'note': '标题和三行题记按题头位置写入。题记作 Neboget、德·莫朗，与放大后的印刷字一致。'},
        {'id': 'ring-numbers', 'status': 'done', 'note': '外圈 1–24 写在原序号圆心里。'},
        {'id': 'organs', 'status': 'done', 'note': '十二脏腑写在对应偶数序号内侧：24 膽、2 肝、4 肺、6 大腸、8 胃、10 脾、12 心、14 小腸、16 膀胱、18 腎、20 心包、22 三焦。大腸对准序号 6 已对照放大图。'},
        {'id': 'interior', 'status': 'partial', 'note': '圆内和四角里，从原图单字块读清的穴名、脉名已按该字块的坐标写入。读不清的没有用常见穴名补。弯曲的穴间细线和没有形成整圈的弧还没有全部重描。原图对照因此仍然开着。这一页还不能算誊完。'},
    ],
    'b36': [
        {'id': 'columns', 'status': 'lines', 'note': '上部 8 列、下部 6 列和左侧编号竖线沿已描路径重绘。'},
        {'id': 'cells', 'status': 'reading', 'note': '方格里的穴名和格子横线还在逐格誊写，原图对照开着。'},
    ],
    'b28': [
        {'id': 'labels', 'status': 'done', 'note': '28 个穴圈、六经名、魂志神魄意和 1–6 号与原图能读清的字一致。没有另补看不清的小字。'},
        {'id': 'paths', 'status': 'done', 'note': '六条色带、相生相克链和四条黑线沿已核对的路径。这张图的结构是六经环和太极，不是另一组同心圆，没有另加圆。'},
    ],
    'b24': [
        {'id': 'body', 'status': 'done', 'note': '穴圈、色带、圆环、圆盘和原有标签都在矢量层。'},
        {'id': 'quotes', 'status': 'done', 'note': '右侧五段说明保持原来的坐标和行宽。五行大圆按原图只画出外侧半圆，内侧穴圈和穴名画在圆上面。'},
    ],
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def image_from(html_path: Path) -> str:
    text = html_path.read_text(encoding='utf-8')
    m = re.search(r'data:image/jpeg;base64,[A-Za-z0-9+/=]+', text)
    if not m:
        raise SystemExit(f'没有底图 {html_path}')
    return m.group(0)


def colors(style, color):
    if color in GLOW:
        return DARK[color], GLOW[color]
    if isinstance(color, str) and color.lower() in ('#ffffff', '#fff', '#fff7c0', '#fff0d8'):
        return '#8d8678', '#ffd34d'
    if isinstance(color, str) and color.startswith('#'):
        return color, color
    if style == 'solid':
        return '#1a1a1a', '#d6e6ff'
    if style == 'dashed':
        return '#1a1a1a', '#7cc0ff'
    if style == 'faint':
        return '#5c3d7a', '#c08cff'
    if style == 'gold':
        return '#8a6a12', '#ffd34d'
    return '#333333', '#ffd34d'


def flow_item(it, idx):
    pts = it.get('pts')
    if not pts or it.get('type') == 'pulse':
        return None
    track, flow = colors(it.get('style'), it.get('color'))
    return {
        'id': it.get('id') or f'p{idx}',
        'pts': [[float(p[0]), float(p[1])] for p in pts],
        'closed': bool(it.get('closed')),
        'ring': bool(it.get('closed')),
        'track': track,
        'flow': flow,
        'width': float(it.get('width') or (8 if it.get('style') == 'band' else 2.4)),
        'group': it.get('group') or ('black' if it.get('style') in ('solid', 'dashed') else 'main'),
        'v': it.get('v') or 24,
    }


def base_doc(cfg, image, key):
    draft = key not in FINISHED
    zones = ZONES[key]
    open_zones = [z for z in zones if z['status'] != 'done']
    if draft:
        lead = '这一页是工作稿。原图对照默认打开。已经核对的字写在矢量层上，还在誊写的区块仍看原图。'
    else:
        lead = '这一页默认只显示矢量。原图对照可以再打开。'
    zone_note = ''.join('<br>' + z['id'] + '：' + z['note'] for z in zones)
    return {
        'id': key,
        'draft': draft,
        'title': cfg.get('title') or key,
        'sub': cfg.get('sub') or '',
        'note': lead + '<br>' + (cfg.get('note') or '') + zone_note,
        'assumption': '已重绘的线沿原描线点序流动。没有新箭头的地方不另作往返。单个认不出的字才标待核。',
        'credit': cfg.get('credit') or '',
        'cycle': cfg.get('cycle'),
        'W': cfg['W'],
        'H': cfg['H'],
        'steps': [{'dur': s.get('dur'), 'main': s.get('main') or '', 'sub': s.get('sub') or ''} for s in (cfg.get('steps') or [])],
        'flows': [],
        'nodes': [],
        'labels': [],
        'zones': zones,
        'uncertain': [z['note'] for z in open_zones],
        'image': image,
    }


def add_generic(doc, cfg):
    for i, it in enumerate(cfg.get('items') or []):
        if it.get('type') == 'pulse':
            c = it.get('c') or [0, 0]
            doc['nodes'].append({
                'id': it.get('id') or f'pulse{i}',
                'x': c[0], 'y': c[1], 'r': it.get('r') or 8,
                't': None, 'fill': '#fff', 'flow': it.get('color') or '#c0201c',
            })
            continue
        row = flow_item(it, i)
        if row:
            doc['flows'].append(row)


def cover_glyphs(data_uri: str, boxes: list) -> str:
    """只把已誊字的深色笔画涂成周围纸色或圆色。长线和色条不涂。"""
    import numpy as np
    from PIL import Image

    head, b64 = data_uri.split(',', 1)
    im = Image.open(io.BytesIO(base64.b64decode(b64))).convert('RGB')
    arr = np.array(im)
    bch, gch, rch = arr[:, :, 2], arr[:, :, 1], arr[:, :, 0]
    gray = arr.mean(axis=2)
    mx = np.maximum(np.maximum(rch, gch), bch).astype(np.int16)
    mn = np.minimum(np.minimum(rch, gch), bch).astype(np.int16)
    ink = ((gray < 145) & ((mx - mn) < 58)).astype(np.uint8) * 255
    import cv2
    hker = cv2.getStructuringElement(cv2.MORPH_RECT, (16, 1))
    vker = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 14))
    lines = cv2.bitwise_or(cv2.morphologyEx(ink, cv2.MORPH_OPEN, hker), cv2.morphologyEx(ink, cv2.MORPH_OPEN, vker))
    text = (cv2.subtract(ink, lines) > 0)
    # 扩 1 像素，把笔画边缘的灰边也盖住，但不扩到长线上
    text = cv2.dilate(text.astype(np.uint8), np.ones((3, 3), np.uint8), iterations=1) > 0
    text = text & (lines == 0)
    H, W = gray.shape
    for x0, y0, x1, y1 in boxes:
        x0, y0 = max(0, int(x0) - 1), max(0, int(y0) - 1)
        x1, y1 = min(W, int(x1) + 1), min(H, int(y1) + 1)
        if x1 <= x0 or y1 <= y0:
            continue
        region = arr[y0:y1, x0:x1]
        local = gray[y0:y1, x0:x1]
        # 比本格纸色或圆色更暗的像素才是字。色条和圆本身接近本格中位色，不涂。
        level = float(np.percentile(local, 68))
        dark = local < (level - 22)
        mask = dark & (lines[y0:y1, x0:x1] == 0)
        mask = cv2.dilate(mask.astype(np.uint8), np.ones((2, 2), np.uint8), iterations=1) > 0
        mask = mask & (lines[y0:y1, x0:x1] == 0)
        if int(mask.sum()) < 6:
            continue
        paper_px = region[~mask]
        if len(paper_px) < 4:
            continue
        paper = np.median(paper_px, axis=0)
        region[mask] = paper
    out = Image.fromarray(arr)
    buf = io.BytesIO()
    out.save(buf, format='JPEG', quality=92)
    return 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode('ascii')


def add_b31(doc, cfg):
    add_generic(doc, cfg)
    # 色环轨道宽 8 像素的淡色描边会整圈盖住印刷色环、环上序号和太极。
    # 能量点仍沿原路径走，轨道本身不铺色。
    for row in doc['flows']:
        if row.get('width', 0) >= 6:
            row['strokeOpacity'] = 0
    # 每个框是单独裁图后能读成一个词的墨迹范围，不是整列猜测。
    # (字, x0, y0, x1, y1)
    reads = [
        ('表層', 630, 52, 679, 67), ('冬', 698, 46, 722, 61), ('裡層', 746, 50, 780, 70),
        ('志', 688, 63, 700, 79), ('水', 710, 65, 726, 80), ('腎', 744, 74, 755, 83),
        ('至陰', 681, 93, 701, 102), ('湧泉', 709, 92, 731, 102),
        ('然谷', 709, 113, 732, 123), ('束骨', 682, 133, 702, 143),
        ('京骨', 680, 150, 702, 163),
        ('崑崙', 682, 171, 702, 182), ('復溜', 712, 169, 734, 179),
        ('委中', 683, 189, 701, 200),
        ('木', 711, 214, 728, 228),
        ('膽', 656, 229, 668, 238), ('魂', 688, 224, 700, 234), ('肝', 741, 228, 750, 236),
        ('足厥陰', 673, 248, 704, 258),
        ('俠谿', 683, 267, 706, 277), ('行間', 711, 267, 733, 277),
        ('丘墟', 687, 304, 705, 314),
        ('陽陵泉', 676, 342, 709, 356), ('曲泉', 714, 342, 736, 353),
        ('少澤', 687, 409, 706, 419), ('少衝', 716, 408, 737, 419),
        ('前谷', 686, 427, 708, 437),
        ('靈道', 717, 481, 739, 492),
        ('少海', 717, 501, 739, 511),
        ('左腕', 697, 520, 729, 535),
        ('表層', 44, 50, 97, 65), ('裡層', 157, 50, 185, 63),
        ('神', 96, 68, 112, 86), ('火', 120, 68, 136, 86),
        ('關衝', 89, 97, 112, 108), ('中衝', 120, 97, 140, 112),
        ('液門', 89, 115, 111, 125),
        ('中渚', 92, 135, 111, 146),
        ('陽池', 89, 154, 111, 165),
        ('厥陰', 164, 162, 188, 173),
        ('間使', 118, 173, 139, 184),
        ('天井', 90, 192, 111, 202), ('曲澤', 118, 192, 139, 202),
        ('足臨泣', 46, 215, 75, 224),
        ('長夏', 100, 205, 140, 218),
        ('意', 97, 223, 111, 237), ('土', 120, 223, 134, 237),
        ('金', 120, 387, 133, 401),
        ('內庭', 91, 272, 111, 282), ('大都', 118, 272, 139, 282),
        ('陷谷', 91, 291, 112, 300),
        ('解谿', 91, 310, 111, 320),
        ('解谿', 88, 329, 114, 340),
        ('商丘', 120, 328, 141, 338),
        ('陰陵泉', 113, 347, 145, 360),
        ('秋', 107, 366, 123, 380),
        ('少商', 120, 412, 140, 424),
        ('太陰', 161, 432, 184, 443), ('商陽', 117, 433, 132, 445),
        ('合谷', 90, 469, 111, 479), ('列缺', 198, 470, 217, 480),
        ('陽明', 42, 481, 65, 493), ('陽谿', 90, 489, 112, 499),
        ('曲池', 90, 508, 111, 518), ('尺澤', 120, 508, 141, 517),
        ('右脇', 97, 528, 129, 543),
    ]
    boxes = []
    for t, x0, y0, x1, y1 in reads:
        w, h = x1 - x0, y1 - y0
        # 字号略小于墨迹框，避免笔画加白边后压到邻格或圈线。
        fs = max(8, min(14, round(h * 0.78)))
        row = {
            't': t,
            'x': round((x0 + x1) / 2, 1),
            'y': round((y0 + y1) / 2, 1),
            'fs': fs, 'fw': 700, 'halo': 0.6,
        }
        if len(t) > 1 and 7 * len(t) <= w <= 20 * len(t):
            row['tl'] = w
        doc['labels'].append(row)
        boxes.append([x0, y0, x1, y1])
    doc['cover'] = boxes
    doc['scanPair'] = True
    doc['uncertain'] = [
        '右表京骨右侧同一格单独裁开后不是完整的太谿，没有写。',
        '右表红圆盖住的字没有写：约 (666,118)、(744,194)、(743,253)、(669,293)、(748,428)、(672,484)。',
        '右表陽輔、中封、神門、膀胱、三焦、春，以及跨过竖线的腕骨框，没有写。',
        '左表外關和右下另一处合谷的裁图没有落在格子里，没有写。',
        '左表心包这一格（约 148,80–167,87）10 倍裁开后第二字不是完整的包，没有写。',
        '左表红圆盖住的字没有写：约 (153,114)、(74,173)、(150,295)、(76,352)、(75,420)、(153,493)。',
        '轮内图例按约 14 像素高的横条逐条裁过，单字 6 到 8 像素，对不成一个词，没有写。环上序号同样没有写，清晰层里仍是原印。',
        '左表魄、胃、脾、大腸、肺和三焦，右表春、膀胱，单独放大后不是一个完整的字，没有写。原印留在原位。',
    ]


def add_b45(doc, cfg):
    add_generic(doc, cfg)
    # 放大后能读清的大字。坐标按原图像素。
    for lab in (
        {'t': '五行', 'x': 74, 'y': 90, 'fs': 18},
        {'t': '氣穴', 'x': 46, 'y': 128, 'fs': 13},
        {'t': '傷寒論', 'x': 72, 'y': 146, 'fs': 13},
        {'t': '66個五輸穴', 'x': 112, 'y': 124, 'fs': 11},
        {'t': '太陽', 'x': 78, 'y': 186, 'fs': 13},
        {'t': '陽明', 'x': 78, 'y': 220, 'fs': 13},
        {'t': '少陽', 'x': 78, 'y': 254, 'fs': 13},
        {'t': '太陰', 'x': 78, 'y': 288, 'fs': 13},
        {'t': '少陰', 'x': 78, 'y': 322, 'fs': 13},
        {'t': '厥陰', 'x': 78, 'y': 354, 'fs': 13},
        {'t': '交會穴', 'x': 52, 'y': 408, 'fs': 14},
        {'t': '母', 'x': 155, 'y': 392, 'fs': 14},
        {'t': '子', 'x': 200, 'y': 392, 'fs': 14},
        {'t': '神應經', 'x': 520, 'y': 378, 'fs': 15},
        {'t': '玉龍', 'x': 298, 'y': 706, 'fs': 22},
        {'t': 'J. Martin-Hartz', 'x': 500, 'y': 786, 'fs': 11},
    ):
        doc['labels'].append({**lab, 'fw': 700, 'halo': 3})


def add_b28(doc, cfg):
    add_generic(doc, cfg)
    # 五行脉动白底留在太极后面，只让带穴名的小圆盖在阴阳图案上。
    for n in doc['nodes']:
        if not n.get('t') and n['r'] >= 40:
            n['behind'] = True
            n['fill'] = 'none'
    for L in cfg.get('staticLines') or []:
        doc['flows'].append({
            'id': 'static%d' % len(doc['flows']),
            'pts': [[float(p[0]), float(p[1])] for p in L],
            'closed': False, 'ring': False, 'track': '#1a1a1a', 'flow': '#d6e6ff',
            'width': 1.6, 'group': 'black', 'v': 22,
        })
    for i, link in enumerate(cfg['chain']['links']):
        doc['flows'].append({
            'id': 'chain%d' % i,
            'pts': [[float(p[0]), float(p[1])] for p in link['pts']],
            'closed': False, 'ring': False, 'track': '#8a6a12', 'flow': '#ffd34d',
            'width': 2.6, 'group': 'main', 'v': 18,
        })
    for p in cfg.get('plates') or []:
        if p.get('t'):
            doc['labels'].append({'t': p['t'], 'x': p['x'], 'y': p['y'], 'fs': p.get('fs') or 14, 'rot': p.get('rot') or 0, 'fw': 700, 'color': p.get('color') or '#111'})
    for c in cfg.get('circles') or []:
        doc['nodes'].append({'id': 'c-' + c['t'], 'x': c['x'], 'y': c['y'], 'r': c['r'], 't': c['t'], 'fill': '#fff', 'flow': '#c0201c', 'fs': max(10, c['r'] * 0.62)})
    items = {}
    for k, t in cfg['taiji'].items():
        items[k] = {
            'c': t['c'], 'r': t['r'], 'mirror': t.get('mirror', 1), 'rot': t.get('rot', 0),
            'light': t['light'], 'dark': t['dark'], 'glow': t['glow'],
            'label': t.get('label') or k, 'sublabel': t.get('sublabel'),
            'fs': t.get('fs'), 'lx': t.get('lx') or 0, 'ly': t.get('ly') or 0,
        }
    doc['taiji'] = {
        'dir': cfg['TAIJI_DIR'], 'mode': cfg['TU_MODE'], 'switchAt': cfg['TU_SWITCH'],
        'rev': cfg.get('TAIJI_REV') or 1, 'order': cfg['taijiDrawOrder'], 'items': items,
    }


def xy(pts):
    return [[float(p[0]), float(p[1])] for p in pts]


# 外圈偶数序号上的脏腑名。位置是该序号向圆心收 40 像素，字保持水平。
# 序号 6 旁的「大腸」对照过放大图。
B39_ORGANS = {
    24: '膽', 2: '肝', 4: '肺', 6: '大腸', 8: '胃', 10: '脾',
    12: '心', 14: '小腸', 16: '膀胱', 18: '腎', 20: '心包', 22: '三焦',
}
B39_CX, B39_CY, B39_R = 598.0, 808.0, 488.0


def _add_b39_reads(doc):
    """把从原图单字块里读清的字放到该字块中心。读成两可的不写。"""
    box_path = ROOT / 'examples/b39-qi-qijing/word-boxes.json'
    text_path = ROOT / 'examples/b39-qi-qijing/read-words.json'
    if not box_path.is_file() or not text_path.is_file():
        return
    boxes = {str(b['i']): b for b in json.loads(box_path.read_text(encoding='utf-8'))}
    reads = json.loads(text_path.read_text(encoding='utf-8'))
    placed = [(p['x'], p['y'], p['t']) for p in doc['labels']]
    fresh = []
    for key, text in reads.items():
        box = boxes.get(str(key))
        if not box or not text:
            continue
        x, y = float(box['cx']), float(box['cy'])
        if any(abs(x - px) < 28 and abs(y - py) < 22 for px, py, t in placed):
            continue
        fs = max(9, min(16, float(box['h']) * 0.92))
        fresh.append({'t': text, 'x': round(x, 1), 'y': round(y, 1), 'fs': round(fs, 1), 'fw': 700, 'halo': 2, 'w': box['w'], 'h': box['h']})
    kept = []
    for lab in fresh:
        hit = False
        for prev in kept:
            dx = abs(lab['x'] - prev['x'])
            dy = abs(lab['y'] - prev['y'])
            if dx < (lab['w'] + prev['w']) * 0.35 and dy < (lab['h'] + prev['h']) * 0.55:
                hit = True
                break
        if not hit:
            kept.append(lab)
    for lab in kept:
        lab.pop('w', None)
        lab.pop('h', None)
        doc['labels'].append(lab)


def _add_b39_lines(doc, cfg):
    path = ROOT / 'examples/b39-qi-qijing/extra-lines.json'
    if not path.is_file():
        return
    data = json.loads(path.read_text(encoding='utf-8'))
    x0, y0, x1, y1 = data['frame']
    doc.setdefault('ink', []).append({
        'pts': [[x0, y0], [x1, y0], [x1, y1], [x0, y1]],
        'closed': True, 'track': '#1a1a1a', 'width': 1.4,
    })
    cx, cy = B39_CX, B39_CY
    for i, seg in enumerate(data['segs']):
        (ax, ay), (bx, by) = seg
        mx, my = (ax + bx) / 2, (ay + by) / 2
        horizontal = abs(ay - by) < 8
        in_table = (my > 1280 and mx < 420) or (mx > 900 and my < 230)
        if horizontal and in_table:
            doc['ink'].append({'pts': [[ax, ay], [bx, by]], 'closed': False, 'track': '#1a1a1a', 'width': 1.1})
            continue
        # 已有的六条轮辐不再叠一条。
        if any(_near_flow(doc, ax, ay) and _near_flow(doc, bx, by) for _ in (0,)):
            continue
        doc['flows'].append({
            'id': 'ink%d' % i,
            'pts': [[ax, ay], [bx, by]],
            'closed': False, 'ring': False,
            'track': '#243044', 'flow': '#7cc0ff',
            'width': 1.6, 'group': 'black', 'v': 22,
        })


def _near_flow(doc, x, y):
    for flow in doc['flows']:
        for px, py in flow['pts'][:: max(1, len(flow['pts']) // 8)]:
            if abs(px - x) < 10 and abs(py - y) < 10:
                return True
    return False


def add_b39(doc, cfg):
    add_generic(doc, cfg)
    for n in doc['nodes']:
        ident = str(n.get('id') or '')
        if ident.startswith('n') and ident[1:].isdigit():
            num = int(ident[1:])
            n['t'] = str(num)
            n['fs'] = 15
            if num not in B39_ORGANS:
                continue
            vx, vy = n['x'] - B39_CX, n['y'] - B39_CY
            dist = (vx * vx + vy * vy) ** 0.5 or 1
            inward = (B39_R - 22) / dist
            doc['labels'].append({
                't': B39_ORGANS[num],
                'x': round(B39_CX + vx * inward, 1),
                'y': round(B39_CY + vy * inward, 1),
                'fs': 14, 'fw': 700, 'color': '#1a1a1a', 'halo': 2,
            })
    # 题头墨迹范围：标题 y 196–214、x 268–560；三行题记从 x 269 起。
    doc['labels'].extend([
        {'t': '氣的循環對應奇經八脈圖', 'x': 268, 'y': 205, 'fs': 17, 'fw': 700, 'anchor': 'start', 'tl': 292, 'halo': 3},
        {'t': '編自 J.E.H. Neboget 博士的著作「針灸的實踐論述」', 'x': 269, 'y': 227, 'fs': 13, 'anchor': 'start', 'tl': 321, 'halo': 2},
        {'t': '採用德·莫朗的拼音法', 'x': 269, 'y': 247, 'fs': 13, 'anchor': 'start', 'tl': 158, 'halo': 2},
        {'t': '於古波瓦 1954年5月6日', 'x': 268, 'y': 265, 'fs': 13, 'anchor': 'start', 'tl': 151, 'halo': 2},
        {'t': 'Jacques Hartz', 'x': 250, 'y': 284, 'fs': 14, 'anchor': 'start', 'tl': 150, 'halo': 2},
    ])
    _add_b39_reads(doc)
    _add_b39_lines(doc, cfg)


def add_b24(doc, cfg):
    wx = cfg.get('wxStyle') or {}
    for b in cfg['bands']:
        doc['flows'].append({
            'id': 'band-' + b['key'],
            'pts': xy(b['pts']),
            'closed': False, 'ring': False,
            'track': b['color'], 'flow': b.get('glow') or b['color'],
            'width': 14, 'group': 'main', 'v': 22,
            'clip': xy(b['clip']) if b.get('clip') else None,
        })
    for r in cfg['rings']:
        colors = r.get('colors') or ['#e0392b', '#5aaee0']
        split = r.get('fSplit') or 0.5
        pts = xy(r['pts'])
        i = max(1, min(len(pts) - 2, int(split * (len(pts) - 1))))
        clip = xy(r['clip']) if r.get('clip') else None
        doc['flows'].append({'id': r['id'] + '-a', 'pts': pts[:i + 1], 'closed': False, 'ring': True, 'track': colors[0], 'flow': colors[0], 'width': 12, 'group': 'main', 'v': 18, 'clip': clip})
        doc['flows'].append({'id': r['id'] + '-b', 'pts': pts[i:], 'closed': False, 'ring': True, 'track': colors[1], 'flow': colors[1], 'width': 12, 'group': 'main', 'v': 18, 'clip': clip})
    placed = [(p['x'], p['y'], p.get('t')) for p in cfg.get('labels') or [] if p.get('t')]
    def duplicated(x, y, text):
        return any(text == t and abs(x - px) < 42 and abs(y - py) < 42 for px, py, t in placed)
    # 大圆先画，并按原图的半圆裁切，避免整圆盖住内侧穴圈。穴圈后画，字留在圆上面。
    for d in cfg.get('discs') or []:
        style = wx.get(d.get('el')) or {}
        text = d.get('t') or d.get('el')
        if text and duplicated(d['x'], d['y'], text):
            text = None
        node = {
            'id': d.get('id') or 'disc',
            'x': d['x'], 'y': d['y'], 'r': d['r'],
            't': text,
            'tx': d.get('lx') if d.get('lx') is not None else d['x'],
            'ty': d.get('ly') if d.get('ly') is not None else d['y'],
            'fill': style.get('dark', '#ddd'),
            'flow': style.get('glow', '#ffd34d'),
            'fs': d.get('fs') or max(12, d['r'] * 0.4),
            'halo': 2,
        }
        if d.get('clip'):
            node['clip'] = d['clip']
        doc['nodes'].append(node)
    for c in cfg['circles']:
        nch = len(c['n'])
        fs = 10.6 if nch == 2 else 8.4
        doc['nodes'].append({
            'id': 'ac-' + c['n'], 'x': c['x'], 'y': c['y'], 'r': c['r'], 't': c['n'],
            'fill': '#fff', 'flow': c.get('bc') or '#c0201c', 'fs': fs,
            'tl': round(fs * nch * 0.98, 2), 'halo': 2,
        })
    for i, line in enumerate(cfg.get('lines') or []):
        doc['flows'].append({'id': 'ln%d' % i, 'pts': xy(line), 'closed': False, 'ring': False, 'track': '#1a1a1a', 'flow': '#d6e6ff', 'width': 1.8, 'group': 'black', 'v': 20})
    for i, path in enumerate(cfg['yuan']['paths']):
        doc['flows'].append({'id': 'yuan%d' % i, 'pts': [[float(p[0]), float(p[1])] for p in path], 'closed': False, 'ring': False, 'track': '#8a3030', 'flow': '#ffb15a', 'width': 3, 'group': 'main', 'v': 16})
    sp = cfg['yuan']['spiral']
    doc['flows'].append({'id': 'spiral', 'pts': xy(sp['pts']), 'closed': False, 'ring': False, 'track': '#8a6a12', 'flow': '#ffd34d', 'width': 2.2, 'group': 'main', 'v': 16})
    for p in cfg.get('labels') or []:
        if p.get('t'):
            doc['labels'].append({
                't': p['t'], 'x': p['x'], 'y': p['y'], 'fs': p.get('fs') or 14, 'rot': p.get('rot') or 0,
                'fw': p.get('fw') or 500, 'color': p.get('color') or '#111',
                'anchor': p.get('anchor') or 'middle', 'halo': 3,
                'tl': p.get('tl'),
            })
    if cfg.get('brand'):
        doc['labels'].append({'t': cfg['brand']['text'], 'x': cfg['W'] / 2, 'y': cfg['H'] - 28, 'fs': 18, 'fw': 700, 'color': '#6b3a12'})


CHARTS = [
    ('b31', 'examples/b31-cunguan-siji', '寸关尺四季表里图_流动动画.html', 'config.json', add_b31),
    ('b45', 'examples/b45-yulong-bafa', '玉龍八法_流动动画.html', 'config.json', add_b45),
    ('b1', 'examples/b1-yulong', '玉龍_流动动画.html', 'config.json', add_generic),
    ('b39', 'examples/b39-qi-qijing', '氣的循環奇經八脈圖_流动动画.html', 'config.json', add_b39),
    ('b36', 'examples/b36-shenying', '神應經穴法圖_流动动画.html', 'config.json', add_generic),
    ('b28', 'examples/b28-wuxing-liujing', '五行六经图动画.html', 'config.json', add_b28),
    ('b24', 'examples/b24-bamai-yuanli', '把脈的原理動畫.html', 'config.json', add_b24),
]


def main():
    if not FONT.is_file():
        raise SystemExit('缺少 Noto 字体文件')
    tpl = TPL.read_text(encoding='utf-8')
    flow = FLOW.read_text(encoding='utf-8')
    tpl = tpl.replace('__FLOW__', flow)
    reports = []
    only = set(sys.argv[1:])
    for key, folder, html_name, cfg_name, adder in CHARTS:
        if only and key not in only:
            continue
        directory = ROOT / folder
        html_path = directory / html_name
        cfg_path = directory / cfg_name
        digest = sha256(html_path)
        cfg_digest = sha256(cfg_path)
        backup = directory / 'backup' / '2026-11-17-清晰重绘前'
        backup.mkdir(parents=True, exist_ok=True)
        if not (backup / html_name).exists():
            (backup / html_name).write_bytes(html_path.read_bytes())
        (backup / 'HASH.txt').write_text(
            f'{digest}  {html_name}\n{cfg_digest}  {cfg_name}\n日期 2026-11-17。原成片与 config 保持这些哈希。\n',
            encoding='utf-8',
        )
        if sha256(html_path) != digest:
            raise SystemExit('原 HTML 被写到了')
        cfg = json.loads(cfg_path.read_text(encoding='utf-8'))
        doc = base_doc(cfg, image_from(html_path), key)
        adder(doc, cfg)
        image = doc.pop('image')
        cover = doc.pop('cover', None)
        raw_token = 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7'
        if cover:
            raw_token = image
            image = cover_glyphs(image, cover)
            if key == 'b31':
                Path('/tmp/b31_clean.jpg').write_bytes(base64.b64decode(image.split(',', 1)[1]))
        out_cfg = directory / 'clear-data.json'
        out_cfg.write_text(json.dumps(doc, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
        page = tpl.replace('__TITLE__', doc['title']).replace('__CFG__', json.dumps(doc, ensure_ascii=False).replace('<', '\\u003c')).replace('__IMG__', image).replace('__RAW__', raw_token)
        chars = ''.join(sorted({c for c in page if ord(c) >= 32}))
        subset = Path('/tmp') / f'_clear_{key}.woff2'
        subset_woff2(chars, FONT, subset, None)
        url = data_url(subset, 'font/woff2')
        subset.unlink(missing_ok=True)
        page = page.replace('__FONTR__', f"url({url}) format('woff2')").replace('__FONTB__', f"url({url}) format('woff2')")
        if image not in page:
            raise SystemExit(key + ' 底图丢失')
        if sha256(html_path) != digest:
            raise SystemExit(key + ' 原文件变化')
        out = directory / (Path(html_name).stem + '_清晰重绘版.html')
        out.write_text(page, encoding='utf-8')
        rings = sum(1 for f in doc['flows'] if f.get('ring')) + len(doc['nodes']) + (len(doc['taiji']['order']) if doc.get('taiji') else 0)
        report = {
            'id': key, 'cycle': doc['cycle'],
            'texts': len(doc['labels']) + sum(1 for n in doc['nodes'] if n.get('t')) + (len(doc['taiji']['order']) if doc.get('taiji') else 0),
            'paths': len(doc['flows']),
            'rings': rings,
            'draft': doc['draft'],
            'zones': doc['zones'],
            'uncertain': doc['uncertain'],
            'html': out.name,
            'bytes': out.stat().st_size,
            'source_sha': digest,
        }
        (directory / 'coverage-清晰重绘.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        reports.append(report)
        print(key, 'texts', report['texts'], 'paths', report['paths'], 'rings', report['rings'], 'MB', round(report['bytes'] / 1e6, 2))
    print('reports', len(reports))


if __name__ == '__main__':
    main()
