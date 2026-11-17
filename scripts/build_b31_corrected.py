#!/usr/bin/env python3
"""B/31 文字校正版。只写新的 HTML，不覆盖原成片，也不覆盖已交清晰重绘版。"""
from __future__ import annotations

import base64
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_clear import FLOW, FONT, ROOT, TPL, add_generic, cover_glyphs, image_from  # noqa: E402
from common import data_url, subset_woff2  # noqa: E402

DIR = ROOT / 'examples' / 'b31-cunguan-siji'
SRC_HTML = DIR / '寸关尺四季表里图_流动动画.html'
OLD_HTML = DIR / '寸关尺四季表里图_流动动画_清晰重绘版.html'
OUT_HTML = DIR / '寸关尺四季表里图_流动动画_文字校正版.html'
USER_JSON = DIR / '用户校正.json'

# 已对上原印墨迹框的字。字用用户校正文的字形。框是墨迹，不是名单顺序推出来的圆。
# (字, x0, y0, x1, y1, 分区)
READS = [
    ('表层', 630, 52, 679, 67, 'lw-hi'),
    ('冬', 698, 46, 722, 61, 'lw-hi'),
    ('里层', 746, 50, 780, 70, 'lw-hi'),
    ('志', 688, 63, 700, 79, 'lw-hi'),
    ('水', 710, 65, 726, 80, 'lw-hi'),
    ('肾', 744, 74, 755, 83, 'lw-hi'),
    ('膀胱', 648, 74, 674, 86, 'lw-hi'),
    ('至阴', 681, 93, 701, 102, 'lw-hi'),
    ('涌泉', 709, 92, 731, 102, 'lw-hi'),
    ('然谷', 709, 113, 732, 123, 'lw-hi'),
    ('束骨', 682, 133, 702, 143, 'lw-hi'),
    ('京骨', 680, 150, 702, 163, 'lw-hi'),
    ('昆仑', 682, 171, 702, 182, 'lw-hi'),
    ('复溜', 712, 169, 734, 179, 'lw-hi'),
    ('委中', 683, 189, 701, 200, 'lw-hi'),
    ('春', 699, 202, 713, 215, 'lw-mid'),
    ('木', 711, 214, 728, 228, 'lw-mid'),
    ('胆', 656, 229, 668, 238, 'lw-mid'),
    ('魂', 688, 224, 700, 234, 'lw-mid'),
    ('肝', 741, 228, 750, 236, 'lw-mid'),
    ('足厥阴', 673, 248, 704, 258, 'lw-mid'),
    ('侠溪', 683, 267, 706, 277, 'lw-mid'),
    ('行间', 711, 267, 733, 277, 'lw-mid'),
    ('丘墟', 687, 304, 705, 314, 'lw-mid'),
    ('阳陵泉', 676, 342, 709, 356, 'lw-mid'),
    ('曲泉', 714, 342, 736, 353, 'lw-mid'),
    ('夏', 705, 362, 720, 374, 'lw-lo'),
    ('神', 694, 381, 705, 393, 'lw-lo'),
    ('火', 717, 380, 728, 392, 'lw-lo'),
    ('少泽', 687, 409, 706, 419, 'lw-lo'),
    ('少冲', 716, 408, 737, 419, 'lw-lo'),
    ('前谷', 686, 427, 708, 437, 'lw-lo'),
    ('灵道', 717, 481, 739, 492, 'lw-lo'),
    ('少海', 717, 501, 739, 511, 'lw-lo'),
    ('左腕', 697, 520, 729, 535, 'lw-lo'),
    ('小肠', 656, 390, 684, 399, 'lw-lo'),
    ('心', 746, 388, 764, 396, 'lw-lo'),
    ('表层', 44, 50, 97, 65, 'rw-hi'),
    ('里层', 157, 50, 185, 63, 'rw-hi'),
    ('神', 96, 68, 112, 86, 'rw-hi'),
    ('火', 120, 68, 136, 86, 'rw-hi'),
    ('三焦', 58, 76, 84, 87, 'rw-hi'),
    ('心包', 148, 76, 172, 88, 'rw-hi'),
    ('关冲', 89, 97, 112, 108, 'rw-hi'),
    ('中冲', 120, 97, 140, 112, 'rw-hi'),
    ('液门', 89, 115, 111, 125, 'rw-hi'),
    ('中渚', 92, 135, 111, 146, 'rw-hi'),
    ('阳池', 89, 154, 111, 165, 'rw-hi'),
    ('厥阴', 164, 162, 188, 173, 'rw-hi'),
    ('间使', 118, 173, 139, 184, 'rw-hi'),
    ('天井', 90, 192, 111, 202, 'rw-hi'),
    ('曲泽', 118, 192, 139, 202, 'rw-hi'),
    ('足临泣', 46, 215, 75, 224, 'rw-mid'),
    ('长夏', 100, 205, 140, 218, 'rw-mid'),
    ('意', 97, 223, 111, 237, 'rw-mid'),
    ('土', 120, 223, 134, 237, 'rw-mid'),
    ('胃', 64, 230, 80, 241, 'rw-mid'),
    ('脾', 150, 230, 168, 242, 'rw-mid'),
    ('内庭', 91, 272, 111, 282, 'rw-mid'),
    ('大都', 118, 272, 139, 282, 'rw-mid'),
    ('陷谷', 91, 291, 112, 300, 'rw-mid'),
    ('解溪', 91, 310, 111, 320, 'rw-mid'),
    ('解溪', 88, 329, 114, 340, 'rw-mid'),
    ('商丘', 120, 328, 141, 338, 'rw-mid'),
    ('阴陵泉', 113, 347, 145, 360, 'rw-mid'),
    ('秋', 107, 366, 123, 380, 'rw-lo'),
    ('魄', 95, 388, 108, 401, 'rw-lo'),
    ('大肠', 62, 390, 84, 401, 'rw-lo'),
    ('肺', 152, 394, 170, 404, 'rw-lo'),
    ('金', 120, 387, 133, 401, 'rw-lo'),
    ('少商', 120, 412, 140, 424, 'rw-lo'),
    ('太阴', 161, 432, 184, 443, 'rw-lo'),
    ('商阳', 117, 433, 132, 445, 'rw-lo'),
    ('合谷', 90, 469, 111, 479, 'rw-lo'),
    ('列缺', 198, 470, 217, 480, 'rw-lo'),
    ('阳明', 42, 481, 65, 493, 'rw-lo'),
    ('阳溪', 90, 489, 112, 499, 'rw-lo'),
    ('曲池', 90, 508, 111, 518, 'rw-lo'),
    ('尺泽', 120, 508, 141, 517, 'rw-lo'),
    ('右腕', 97, 528, 129, 543, 'rw-lo'),
]

# 足临泣印在图左侧（右腕侧）原格。用户把它列在左腕中部，这里不另造一个左腕坐标。
CROSS = {
    'lw-mid': {
        '足临泣': '已写在画面左中的原印格（人体右腕侧），不另造画面右中的坐标。',
    },
}

WHEEL_GAPS = [
    '轮内左侧图例 12 条横条（约 14 像素高，单字约 6 到 8 像素）。用户校正文没有这些字，没有写入，原印留在轮内。',
    '轮内右侧图例 13 条横条，同样没有写入，原印留在轮内。',
    '九层色环上的序号没有另写矢量数字。清晰层仍是原印，色环轨道不铺色盖住环和太极。',
    '红圆压住的字没有按五输或分区名单填进去。画面右侧约 (666,118)、(744,194)、(743,253)、(669,293)、(748,428)、(672,484)。画面左侧约 (153,114)、(74,173)、(150,295)、(76,352)、(75,420)、(153,493)。',
    '肺扇区示例太渊、列缺、中府、肺俞，胃扇区示例冲阳、丰隆、中脘、胃俞：扇区横条放大后仍是断开的墨点，没有确认到格子，没有写入。列缺只留在画面左下已经对上的原格。',
    '其余十经的原穴、络穴、募穴、背俞，用户没有给出组合，没有用常见穴名填进扇区。',
    '中央仍是原图九层色环。没有按六经说明改成六层，也没有给每一层另起经名，没有新增流向。',
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _mark(name, zone_id, placed_names):
    hits = [p for p in placed_names if p['t'] == name and p['zone'] == zone_id]
    cross = CROSS.get(zone_id, {}).get(name)
    if hits:
        n = len(hits)
        return 'on', name + (f'（原印{n}格）' if n > 1 else '')
    if cross:
        return 'on', name + '（' + cross + '）'
    return 'wait', name


def panel_html(user, placed_names):
    parts = [
        '<section class="corr" id="corr">',
        '<h2>穴名采用用户提供校正文；原图可切换</h2>',
        '<p>' + user.get('screenNote', '') + ' 图上的穴名来自用户提供的校正文，不是从原图逐字认出，也不是另行核对过的国家标准。'
        '井、荥、输、经、合是类别，不用这个顺序去推断被挡住的圆在图上的位置。'
        '表层括号里的脏腑按阳腑，里层括号里的脏腑按阴脏，写在已经看得见的括号上。'
        '标「原位待核」的名字只出现在本区名单里，没有画到某个圆或某条新线上。</p>',
        '<div class="zones">',
    ]
    pending_total = 0
    placed_total = 0
    for zone in user['zones']:
        seen = set()
        parts.append('<article class="zone">')
        parts.append(f'<h3>{zone["screen"]} · {zone["element"]}</h3>')
        parts.append(f'<p>{zone["wrist"]}</p>')
        if zone.get('sense'):
            parts.append(f'<p>{zone["sense"]}</p>')
        for side in (zone['biao'], zone['li']):
            on_fig, pending = [], []
            organ_state, organ_label = _mark(side['organ'], zone['id'], placed_names)
            if organ_state == 'on':
                on_fig.append(side['organ'])
                placed_total += 1
            else:
                pending.append(side['organ'])
                pending_total += 1
            seen.add(side['organ'])
            for item in side['points']:
                name = item['t']
                if name in seen:
                    continue
                seen.add(name)
                state, label = _mark(name, zone['id'], placed_names)
                shown = label + '·' + item['role']
                if state == 'on':
                    on_fig.append(shown)
                    placed_total += 1
                else:
                    pending.append(shown)
                    pending_total += 1
            parts.append(f'<p><b>{side["side"]} {side["channel"]}</b></p>')
            parts.append('<p class="ok">已在图上：' + ('、'.join(on_fig) if on_fig else '无') + '</p>')
            parts.append('<p class="wait">原位待核：' + ('、'.join(pending) if pending else '无') + '</p>')
        extra_on = []
        for p in placed_names:
            if p['zone'] == zone['id'] and p['t'] not in seen:
                extra_on.append(p['t'])
                seen.add(p['t'])
        if extra_on:
            parts.append('<p class="ok">同区原印上另有：' + '、'.join(extra_on) + '</p>')
        parts.append('</article>')
    parts.append('</div>')
    parts.append('<h2>十二经五输（类别顺序，不是图上位置）</h2>')
    parts.append('<table class="shu"><thead><tr><th>经脉</th><th>井、荥、输、经、合</th><th>原穴</th><th>八脉交会穴</th></tr></thead><tbody>')
    for row in user['meridians']:
        extra = row['extra'] or '—'
        parts.append(
            '<tr><td>' + row['name'] + '</td><td>' + '、'.join(row['shu']) + '</td><td>'
            + row['yuan'] + '</td><td>' + extra + '</td></tr>'
        )
    parts.append('</tbody></table>')
    parts.append('<h2>轮内还没有写入的字</h2>')
    parts.append('<ul>')
    for line in WHEEL_GAPS:
        parts.append('<li>' + line + '</li>')
    parts.append('</ul>')
    reading = user.get('reading') or {}
    if reading:
        parts.append('<details class="extra"><summary>' + reading.get('title', '') + '</summary>')
        for para in reading.get('body') or []:
            parts.append('<p>' + para + '</p>')
        for url in reading.get('citations') or []:
            parts.append('<p class="cite">' + url + '</p>')
        parts.append('</details>')
    parts.append('<p>原图作者与来源仍在图下：J. Martin-Hartz / Fondation Cornelius Celsus。勾选「原图对照」回到未改的原图，矢量字会暂时藏起。</p>')
    parts.append('</section>')
    return ''.join(parts), placed_total, pending_total


STYLE = '''
.corr{margin-top:14px;background:#3a2150;border:1px solid rgba(212,175,55,.45);border-radius:6px;padding:12px 14px;color:#f6efe2}
.corr h2{font-size:16px;color:#D4AF37;margin:14px 0 6px}
.corr p,.corr li{font-size:14px;line-height:1.65;margin:6px 0}
.zones{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:10px}
.zone{background:#2a1338;border:1px solid rgba(212,175,55,.35);border-radius:4px;padding:8px 10px}
.zone h3{margin:0 0 4px;font-size:15px;color:#ffd9a0}
.ok{color:#d8ffd0}
.wait{color:#ffe0a8}
table.shu{width:100%;border-collapse:collapse;font-size:13px;margin-top:6px}
table.shu td,table.shu th{border:1px solid rgba(212,175,55,.3);padding:4px 6px;text-align:left;vertical-align:top}
#stage{min-width:0}
details.extra{margin-top:12px;background:#2a1338;border:1px solid rgba(212,175,55,.35);border-radius:4px;padding:8px 10px}
details.extra summary{cursor:pointer;color:#ffd9a0;font-size:15px}
.cite{font-size:12px;word-break:break-all;color:#cbb6dc}
'''


def main():
    if not FONT.is_file():
        raise SystemExit('缺少 Noto 字体文件')
    before_old = sha256(OLD_HTML)
    before_src = sha256(SRC_HTML)
    user = json.loads(USER_JSON.read_text(encoding='utf-8'))
    cfg = json.loads((DIR / 'config.json').read_text(encoding='utf-8'))
    image = image_from(SRC_HTML)

    # 校正文里的每一个穴名、脏腑名，必须在图上或待核栏出现。
    required = []
    for zone in user['zones']:
        required.extend(zone['points'])
        required.extend(zone['organs'])
        required.extend(zone['also'])
    for row in user['meridians']:
        required.extend(row['shu'])
        required.append(row['yuan'])
        if row['extra']:
            required.append(row['extra'])
    placed_names = [{'t': t, 'zone': zone} for t, x0, y0, x1, y1, zone in READS]
    zone_names = set()
    for zone in user['zones']:
        zone_names.update(zone['points'])
        zone_names.update(zone['organs'])
        zone_names.update(zone['also'])
    stranded = sorted({name for name in required if name not in zone_names})
    if stranded:
        raise SystemExit('校正文里的名字没有分区: ' + '、'.join(stranded))

    doc = {
        'id': 'b31',
        'draft': True,
        'title': '寸关尺 / 四季表里图（B/31）—— 流动动画 · 文字校正',
        'sub': '穴名采用用户提供校正文；原图可切换。画面左是人体右腕，画面右是人体左腕。原图：J. Martin-Hartz / Fondation Cornelius Celsus（B/31）。动画按图中圆环、序号与线条示意，非原作者制作。',
        'note': '这一页是文字校正工作稿。对得上原印格子的字已替换，并只盖住这些旧笔画。对不上格子的名字在图下分区栏，标原位待核。中央仍是九层色环。轮内图例和环上序号仍是原印。用户补充解读在页下，尚未逐项核对原图。',
        'assumption': '穴名采用用户提供校正文；原图可切换。画面左是人体右腕，画面右是人体左腕。能量沿原有路径走，没有新的医理连线。',
        'credit': '原图 J. Martin-Hartz / Fondation Cornelius Celsus · 动画示意 · 穴名校正文由用户提供',
        'cycle': cfg['cycle'],
        'W': cfg['W'],
        'H': cfg['H'],
        'steps': [{'dur': s.get('dur'), 'main': s.get('main') or '', 'sub': s.get('sub') or ''} for s in (cfg.get('steps') or [])],
        'flows': [],
        'nodes': [],
        'labels': [],
        'scanPair': True,
        'uncertain': WHEEL_GAPS,
    }
    add_generic(doc, cfg)
    for row in doc['flows']:
        if row.get('width', 0) >= 6:
            row['strokeOpacity'] = 0
    boxes = []
    for t, x0, y0, x1, y1, zone in READS:
        w, h = x1 - x0, y1 - y0
        fs = max(8, min(14, round(h * 0.78)))
        row = {
            't': t,
            'x': round((x0 + x1) / 2, 1),
            'y': round((y0 + y1) / 2, 1),
            'fs': fs, 'fw': 700, 'halo': 0.6,
            'zone': zone,
        }
        if len(t) > 1 and 7 * len(t) <= w <= 20 * len(t):
            row['tl'] = w
        doc['labels'].append(row)
        boxes.append([x0, y0, x1, y1])
    raw = image
    image = cover_glyphs(image, boxes)

    panel, placed_n, pending_n = panel_html(user, placed_names)
    tpl = TPL.read_text(encoding='utf-8')
    tpl = tpl.replace('__FLOW__', FLOW.read_text(encoding='utf-8'))
    # 标签上的 zone 不进页面脚本，避免无关字段。
    page_doc = json.loads(json.dumps(doc))
    for lab in page_doc['labels']:
        lab.pop('zone', None)
    page = tpl.replace('__TITLE__', page_doc['title'])
    page = page.replace('__CFG__', json.dumps(page_doc, ensure_ascii=False).replace('<', '\\u003c'))
    page = page.replace('__IMG__', image).replace('__RAW__', raw)
    chars = ''.join(sorted({c for c in page + panel if ord(c) >= 32}))
    subset = Path('/tmp') / '_clear_b31corr.woff2'
    subset_woff2(chars, FONT, subset, None)
    url = data_url(subset, 'font/woff2')
    subset.unlink(missing_ok=True)
    page = page.replace('__FONTR__', f"url({url}) format('woff2')").replace('__FONTB__', f"url({url}) format('woff2')")
    page = page.replace('</style>', STYLE + '</style>', 1)
    page = page.replace('<div class="note" id="note"></div>', '<div class="note" id="note"></div>\n' + panel, 1)
    external = page.replace('http://www.w3.org/2000/svg', '')
    for url in (user.get('reading') or {}).get('citations') or []:
        external = external.replace(url, '')
    if 'http://' in external or 'https://' in external:
        raise SystemExit('校正版出现了外链')
    OUT_HTML.write_text(page, encoding='utf-8')
    if sha256(OLD_HTML) != before_old or sha256(SRC_HTML) != before_src:
        raise SystemExit('原件或已交清晰版被写到了')

    report = {
        'id': 'b31-corrected',
        'html': OUT_HTML.name,
        'bytes': OUT_HTML.stat().st_size,
        'labels_on_figure': len(doc['labels']),
        'names_accounted_on_figure_or_cross': placed_n,
        'names_pending_position': pending_n,
        'wheel_gap_lines': WHEEL_GAPS,
        'not_ocr': True,
        'not_national_standard_claim': True,
        'source_sha': before_src,
        'previous_clear_sha': before_old,
        'user_text': 'docs/b31-用户文字校正.md',
    }
    (DIR / 'coverage-文字校正.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('labels', len(doc['labels']), 'accounted', placed_n, 'pending', pending_n, 'MB', round(OUT_HTML.stat().st_size / 1e6, 2))
    print('unchanged clear', before_old[:12], 'source', before_src[:12])


if __name__ == '__main__':
    main()
