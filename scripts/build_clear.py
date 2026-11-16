#!/usr/bin/env python3
"""从已核对的 config 生成清晰重绘 HTML。不改原成片。

默认不显示扫描图。文字和线只来自该图 config / 模板里已经写明的字段。
没有坐标的手写字不猜，写进 coverage 的 uncertain。
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

# 看过扫描图、但没有逐字坐标表，不能当成已经誊清。
UNCERTAIN = {
    'b31': [
        '轮心九层色环以外的穴名、表里框、四季和左右腕旁注没有逐字坐标，未誊写。',
        '轮辐之间更密的细线多于 config 里的 14 条黑实线和 4 条虚线，多出来的墨迹未重绘。',
    ],
    'b45': [
        '椭圆内的多层细线和交会穴下方的穴名没有标签表，未逐字誊写。',
        'config 只含已描的色带、外环、横线和少数脉动点，不是全图墨迹。',
    ],
    'b1': [
        '花形、柱内网格和斜轴旁的小字没有坐标级标签，未猜写。',
        '只重绘 config.items 里已有的中轴、彩线、弧和黑线。',
    ],
    'b39': [
        '外圈 1–24 的序号字和圆内其余穴名不在 config 的文字字段里，未逐字誊写。',
        '同心细弧、四角奇经表没有单独的路径表，未冒充已经重绘。',
    ],
    'b36': [
        '方格里的穴名、经名和左右密排小字没有 labels 表，未从扫描图猜写。',
        '只重绘 config 里的上部 8 列、下部 6 列和左侧编号竖线，格子横线未描。',
    ],
    'b28': [
        '色带上更细的分支墨迹如果不在 items、chain 或 staticLines 里，就没有重绘。',
        '圆内穴名只用 circles / plates 里已有的字。',
    ],
    'b24': [
        '清晰层用 config 的 bands、rings、circles、labels、discs、lines、yuan。',
        '扫描图上若还有未进入这些字段的小字，没有另猜。',
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
    return {
        'id': key,
        'title': cfg.get('title') or key,
        'sub': cfg.get('sub') or '',
        'note': (cfg.get('note') or '') + '<br>清晰重绘默认不叠扫描图。原图对照可打开。' + ''.join('<br>待核：' + u for u in UNCERTAIN[key]),
        'assumption': '已重绘的线沿原描线点序流动。没有新箭头的地方不另作往返。未进入矢量表的墨迹和小字见待核，不猜。',
        'credit': cfg.get('credit') or '',
        'cycle': cfg.get('cycle'),
        'W': cfg['W'],
        'H': cfg['H'],
        'steps': [{'dur': s.get('dur'), 'main': s.get('main') or '', 'sub': s.get('sub') or ''} for s in (cfg.get('steps') or [])],
        'flows': [],
        'nodes': [],
        'labels': [],
        'uncertain': UNCERTAIN[key],
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


def add_b28(doc, cfg):
    add_generic(doc, cfg)
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
    for c in cfg['circles']:
        doc['nodes'].append({'id': 'ac-' + c['n'], 'x': c['x'], 'y': c['y'], 'r': c['r'], 't': c['n'], 'fill': '#fff', 'flow': c.get('bc') or '#c0201c', 'fs': max(9, c['r'] * 0.55)})
    placed = [(p['x'], p['y'], p.get('t')) for p in cfg.get('labels') or [] if p.get('t')]
    def duplicated(x, y, text):
        return any(text == t and abs(x - px) < 42 and abs(y - py) < 42 for px, py, t in placed)
    for d in cfg.get('discs') or []:
        style = wx.get(d.get('el')) or {}
        text = d.get('t') or d.get('el')
        if text and duplicated(d['x'], d['y'], text):
            text = None
        doc['nodes'].append({
            'id': d.get('id') or 'disc',
            'x': d['x'], 'y': d['y'], 'r': d['r'],
            't': text,
            'fill': style.get('dark', '#ddd'),
            'flow': style.get('glow', '#ffd34d'),
            'fs': d.get('fs') or max(12, d['r'] * 0.4),
        })
    for i, line in enumerate(cfg.get('lines') or []):
        doc['flows'].append({'id': 'ln%d' % i, 'pts': xy(line), 'closed': False, 'ring': False, 'track': '#1a1a1a', 'flow': '#d6e6ff', 'width': 1.8, 'group': 'black', 'v': 20})
    for i, path in enumerate(cfg['yuan']['paths']):
        doc['flows'].append({'id': 'yuan%d' % i, 'pts': [[float(p[0]), float(p[1])] for p in path], 'closed': False, 'ring': False, 'track': '#8a3030', 'flow': '#ffb15a', 'width': 3, 'group': 'main', 'v': 16})
    sp = cfg['yuan']['spiral']
    doc['flows'].append({'id': 'spiral', 'pts': xy(sp['pts']), 'closed': False, 'ring': False, 'track': '#8a6a12', 'flow': '#ffd34d', 'width': 2.2, 'group': 'main', 'v': 16})
    for p in cfg.get('labels') or []:
        if p.get('t'):
            doc['labels'].append({'t': p['t'], 'x': p['x'], 'y': p['y'], 'fs': p.get('fs') or 14, 'rot': p.get('rot') or 0, 'fw': p.get('fw') or 500, 'color': p.get('color') or '#111'})
    if cfg.get('brand'):
        doc['labels'].append({'t': cfg['brand']['text'], 'x': cfg['W'] / 2, 'y': cfg['H'] - 28, 'fs': 18, 'fw': 700, 'color': '#6b3a12'})


CHARTS = [
    ('b31', 'examples/b31-cunguan-siji', '寸关尺四季表里图_流动动画.html', 'config.json', add_generic),
    ('b45', 'examples/b45-yulong-bafa', '玉龍八法_流动动画.html', 'config.json', add_generic),
    ('b1', 'examples/b1-yulong', '玉龍_流动动画.html', 'config.json', add_generic),
    ('b39', 'examples/b39-qi-qijing', '氣的循環奇經八脈圖_流动动画.html', 'config.json', add_generic),
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
    for key, folder, html_name, cfg_name, adder in CHARTS:
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
