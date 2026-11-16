#!/usr/bin/env python3
"""从原图核对过的文字和已有路径生成清晰重绘 HTML。不改原成片。

核对完的页默认只显示矢量。还在逐区誊写的页是工作稿，原图对照默认打开。
单个认不出的字才标待核；没有核对完的整页不把文字清成空白。
"""
from __future__ import annotations

import hashlib
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
        {'id': 'wheel', 'status': 'lines', 'note': '九层色环、轮辐和序号链沿已描路径重绘。轮内小字本轮没有另猜。'},
        {'id': 'right-table', 'status': 'done', 'note': '右侧表里、四季和腕下左腕、陰、小海少海按原格中心写入。红圆压住的三处没有补字。'},
        {'id': 'left-table', 'status': 'reading', 'note': '左侧表的小字还没有逐格钉上，原图对照开着。'},
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


def add_b31(doc, cfg):
    add_generic(doc, cfg)
    # 坐标是原图墨迹的中心。红圆盖住、看不全的字不写。
    labels = [
        ('表層', 655, 64, 15), ('冬', 722, 58, 16), ('裡層', 770, 64, 15),
        ('膀胱', 650, 86, 13), ('志', 692, 106, 16), ('水', 740, 106, 16), ('腎', 772, 96, 14),
        ('至陰', 675, 116, 12), ('湧泉', 724, 104, 12),
        ('束骨', 679, 146, 12), ('然谷', 723, 138, 12),
        ('京骨', 688, 174, 12), ('太谿', 725, 174, 12),
        ('崑崙', 690, 192, 12), ('復溜', 734, 192, 12),
        ('委中', 692, 210, 12),
        ('足太陽', 652, 146, 12), ('足少陰', 788, 166, 11),
        ('春', 710, 222, 16),
        ('膽', 648, 236, 14), ('魂', 683, 244, 16), ('木', 730, 244, 16), ('肝', 772, 240, 14),
        ('足厥陰', 622, 258, 12),
        ('俠谿', 687, 270, 12), ('行間', 734, 272, 12),
        ('足少陽', 600, 310, 12),
        ('丘墟', 686, 318, 12), ('太衝', 726, 320, 12),
        ('陽輔', 687, 344, 12), ('中封', 725, 346, 12),
        ('陽陵泉', 682, 374, 11), ('曲泉', 723, 370, 12),
        ('小腸', 662, 396, 13), ('神', 693, 390, 16), ('夏', 712, 372, 15),
        ('火', 733, 394, 16), ('心', 768, 396, 14),
        ('少澤', 690, 428, 12), ('少衝', 733, 430, 12),
        ('神門', 724, 476, 12), ('靈道', 762, 476, 12),
        ('小海', 718, 508, 12), ('少海', 756, 512, 12),
        ('左腕', 424, 494, 16), ('陰', 778, 530, 16),
        ('J. Martin-Hartz', 700.0, 575.0, 11),
    ]
    for t, x, y, fs in labels:
        doc['labels'].append({'t': t, 'x': x, 'y': y, 'fs': fs, 'fw': 700, 'halo': 3})
    doc['uncertain'] = [
        '右表红圆压住的字没有补：束骨左侧约 (648,125)、復溜右侧约 (755,200)、小海上方约 (680,470)。',
        '左侧表和轮内细字本轮没有写入。',
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
        out_cfg = directory / 'clear-data.json'
        out_cfg.write_text(json.dumps(doc, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
        page = tpl.replace('__TITLE__', doc['title']).replace('__CFG__', json.dumps(doc, ensure_ascii=False).replace('<', '\\u003c')).replace('__IMG__', image)
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
