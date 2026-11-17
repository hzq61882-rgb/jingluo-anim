#!/usr/bin/env python3
"""B/31 逐环旋转文字版。只写新的 HTML，不覆盖原成片、清晰重绘版和文字校正版。"""
from __future__ import annotations

import base64
import io
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_b31_corrected import (  # noqa: E402
    DIR,
    OLD_HTML,
    READS,
    SRC_HTML,
    STYLE,
    USER_JSON,
    WHEEL_GAPS,
    panel_html,
    sha256,
)
from build_clear import FLOW, FONT, TPL, add_generic, cover_glyphs, image_from  # noqa: E402
from common import data_url, subset_woff2  # noqa: E402

OUT_HTML = DIR / '寸关尺四季表里图_逐环旋转文字版.html'
CORR_HTML = DIR / '寸关尺四季表里图_流动动画_文字校正版.html'
CX, CY = 404.0, 296.0
# 九层色环的中线半径。带宽约 8，彼此相接。外缘停在辐条之前。
RING_RADII = [24.45, 32.0, 38.95, 45.95, 53.45, 60.45, 68.0, 74.95, 81.45]
RING_TURNS = [1, -2, 3, -1, 2, -3, 4, -4, 5]
# 10:30 用户确认的夏火区原位。框是墨迹，不是名单顺序。
# 经名拆成单字，是因为原印竖排；合起来仍是用户给的「手太阳 小肠经」「手少阴 心经」。
EXTRA = [
    ('少府', 740, 422, 759, 436, 'lw-lo'),
    ('阳谷', 662, 478, 682, 492, 'lw-lo'),
    ('阳', 649, 516, 666, 528, 'lw-lo'),
    ('阴', 756, 512, 774, 526, 'lw-lo'),
    ('面血', 628, 414, 654, 428, 'lw-lo'),
    ('语言', 628, 430, 654, 444, 'lw-lo'),
    ('手', 604, 446, 618, 458, 'side'),
    ('太阳', 624, 448, 646, 462, 'side'),
    ('小', 632, 470, 646, 486, 'side'),
    ('肠', 632, 486, 646, 502, 'side'),
    ('经', 632, 502, 646, 516, 'side'),
    ('手', 751, 453, 765, 465, 'side'),
    ('少', 751, 465, 765, 477, 'side'),
    ('阴', 751, 477, 765, 489, 'side'),
    ('心', 764, 450, 778, 470, 'side'),
    ('经', 764, 474, 778, 496, 'side'),
    ('后溪', 686, 444, 706, 456, 'lw-lo'),
    ('腕骨', 688, 462, 706, 474, 'lw-lo'),
    ('小海', 692, 498, 712, 511, 'lw-lo'),
    ('神', 704, 446, 732, 454, 'lw-lo'),
    ('门', 704, 464, 738, 474, 'lw-lo'),
    # 10:41 画面右上冬水。穴名用核对后的写法。拆开的字是原印分栏或竖排。
    ('足通谷', 660, 108, 684, 120, 'lw-hi'),
    ('太', 712, 134, 732, 148, 'part'),
    ('溪', 712, 150, 732, 166, 'part'),
    ('阴谷', 736, 182, 760, 198, 'lw-hi'),
    ('发', 636, 170, 656, 182, 'note'),
    ('骨', 636, 180, 656, 192, 'note'),
    ('听觉', 634, 190, 660, 201, 'note'),
    ('申脉', 606, 204, 642, 222, 'lw-hi'),
    ('后溪', 616, 222, 644, 236, 'note'),
    ('足', 634, 126, 650, 142, 'part'),
    ('太阳', 630, 144, 656, 156, 'part'),
    ('足', 758, 138, 774, 152, 'part'),
    ('少', 758, 152, 774, 166, 'part'),
    ('阴', 758, 166, 774, 182, 'part'),
    ('肾', 716, 184, 730, 198, 'part'),
    ('经', 716, 200, 730, 214, 'part'),
    ('厥', 604, 154, 618, 166, 'part'),
    ('阴', 604, 166, 618, 176, 'part'),
    ('经', 604, 176, 618, 188, 'part'),
    ('肝', 582, 168, 598, 182, 'link'),
    ('小肠', 578, 204, 598, 216, 'link'),
    ('忍', 570, 80, 594, 95, 'note'),
    ('人', 600, 102, 614, 114, 'note'),
    # 10:50 底部路径图例。三行在序号 5 的左下方，样条线留在字的左边。
    ('路径：', 506, 506, 530, 516, 'legend'),
    ('可行', 506, 516, 524, 525, 'legend'),
    ('破滞', 506, 526, 524, 535, 'legend'),
]
# (字, 左缘 x) 落在色圆里。盖字时回填圆色，不回填白纸。
DISK_KEYS = {
    ('少府', 740), ('阳谷', 662), ('阳', 649), ('阴', 756),
    ('足通谷', 660), ('阴谷', 736), ('肝', 582), ('小肠', 578),
}
LIGHT_KEYS = {
    ('发', 636), ('骨', 636), ('听觉', 634), ('申脉', 606), ('后溪', 616), ('门', 704),
    ('路径：', 506), ('可行', 506), ('破滞', 506),
}
# 放大裁图里，n0 到 n11 依次是奇数链。与图例「1→3→…→23→1」一致。
NODE_NUMS = [str(1 + 2 * i) for i in range(12)]
MANUAL_CIRCLES = [
    {'id': 'shaofu', 'cx': 749.1, 'cy': 428.1, 'r': 14, 'name': '少府', 'where': '画面右下右列大红圈'},
    {'id': 'yanggu', 'cx': 672.0, 'cy': 485.0, 'r': 14, 'name': '阳谷', 'where': '画面右下左列大红圈'},
    {'id': 'yang', 'cx': 657.0, 'cy': 527.0, 'r': 14, 'name': '阳', 'where': '画面右下底部红白圈'},
    {'id': 'yin', 'cx': 765.0, 'cy': 524.0, 'r': 15, 'name': '阴', 'where': '画面右下底部绿白圈'},
    {'id': 'mianxue', 'cx': 641.0, 'cy': 429.0, 'r': 16, 'name': '面血语言', 'where': '画面右下黑线圈，两行'},
    {'id': 'zutong', 'cx': 672.0, 'cy': 118.0, 'r': 14, 'name': '足通谷', 'where': '画面右上左列红圈'},
    {'id': 'yingu', 'cx': 748.0, 'cy': 191.0, 'r': 14, 'name': '阴谷', 'where': '画面右上右列红圈'},
    {'id': 'fa', 'cx': 648.0, 'cy': 185.0, 'r': 18, 'name': '发骨听觉', 'where': '画面右上空白注释圆'},
    {'id': 'gan-link', 'cx': 590.0, 'cy': 175.0, 'r': 12, 'name': '肝', 'where': '冬水区旁绿色连接圆，不是春木大区的肝'},
    {'id': 'xiao-link', 'cx': 588.0, 'cy': 210.0, 'r': 11, 'name': '小肠', 'where': '绿色连接圆下方的大红圈，不是夏火大区的小肠'},
]


def png_uri(im: Image.Image) -> str:
    buf = io.BytesIO()
    im.save(buf, format='PNG', optimize=True)
    return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode('ascii')


def jpeg_uri(arr: np.ndarray) -> str:
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format='JPEG', quality=92)
    return 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode('ascii')


def decode_uri(uri: str) -> np.ndarray:
    raw = base64.b64decode(uri.split(',', 1)[1])
    return np.array(Image.open(io.BytesIO(raw)).convert('RGB'))


def soft_cover(arr: np.ndarray, boxes: list, kind: str = 'paper') -> None:
    """纸色格涂掉灰笔画；色圆只涂比圆色更暗的字，并避开横竖长线。"""
    gray = arr.mean(axis=2)
    H, W = gray.shape
    for x0, y0, x1, y1 in boxes:
        x0, y0 = max(0, int(x0)), max(0, int(y0))
        x1, y1 = min(W, int(x1)), min(H, int(y1))
        if x1 - x0 < 2 or y1 - y0 < 2:
            continue
        sl = gray[y0:y1, x0:x1]
        if kind == 'disk':
            level = float(np.median(sl))
            mask = sl < (level - 16)
        else:
            rules = np.zeros(sl.shape, bool)
            dark = sl < 110
            row = dark.mean(axis=1)
            col = dark.mean(axis=0)
            rules[row > 0.45, :] = True
            rules[:, col > 0.45] = True
            if kind == 'glyph':
                import cv2
                ink = ((sl < 200).astype(np.uint8)) * 255
                hk = cv2.getStructuringElement(cv2.MORPH_RECT, (max(10, sl.shape[1] * 2 // 3), 1))
                vk = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(8, sl.shape[0] // 2)))
                lines = cv2.bitwise_or(
                    cv2.morphologyEx(ink, cv2.MORPH_OPEN, hk),
                    cv2.morphologyEx(ink, cv2.MORPH_OPEN, vk),
                )
                mask = (ink > 0) & (lines == 0)
            else:
                mask = (sl < (205 if kind == 'light' else 175)) & ~rules
        if kind == 'glyph':
            by0, by1 = max(0, y0 - 3), min(H, y1 + 3)
            bx0, bx1 = max(0, x0 - 3), min(W, x1 + 3)
            border = arr[by0:by1, bx0:bx1].reshape(-1, 3)
            border = border[border.mean(axis=1) > 188]
            fill = np.median(border, axis=0) if len(border) > 8 else np.array([246, 242, 230])
            arr[y0:y1, x0:x1][mask] = fill
            continue
        if int(mask.sum()) < 4 or float(mask.mean()) > 0.82:
            continue
        paper = arr[y0:y1, x0:x1][~mask]
        if len(paper) < 4:
            continue
        arr[y0:y1, x0:x1][mask] = np.median(paper, axis=0)


def ring_and_taiji(arr: np.ndarray):
    """抽出九层环和中央太极，底图相应位置改成该环自身的浅色，避免原印留在原地当残影。"""
    h, w = arr.shape[:2]
    yy, xx = np.ogrid[:h, :w]
    dist = np.sqrt((xx - CX) ** 2 + (yy - CY) ** 2)
    nearest = np.full(dist.shape, -1, np.int16)
    best = np.full(dist.shape, 99.0)
    for i, rad in enumerate(RING_RADII):
        delta = np.abs(dist - rad)
        take = (delta < best) & (delta <= 4.05) & (dist >= 20.3) & (dist <= 85.1)
        nearest[take] = i
        best = np.where(take, delta, best)
    gray = arr.mean(axis=2)
    sprites = []
    for i, rad in enumerate(RING_RADII):
        mask = nearest == i
        ys, xs = np.where(mask)
        if len(xs) == 0:
            raise SystemExit(f'环 {i} 没有像素')
        x0, x1 = int(xs.min()), int(xs.max()) + 1
        y0, y1 = int(ys.min()), int(ys.max()) + 1
        sub = arr[y0:y1, x0:x1]
        local = mask[y0:y1, x0:x1]
        light = sub[local & (gray[y0:y1, x0:x1] > 110)]
        fill = np.median(light, axis=0) if len(light) > 20 else np.median(sub[local], axis=0)
        rgba = np.zeros((y1 - y0, x1 - x0, 4), np.uint8)
        rgba[local, :3] = sub[local]
        rgba[local, 3] = 255
        arr[mask] = fill
        sprites.append({
            'id': f'ring{i}',
            'kind': 'ring',
            'turns': RING_TURNS[i],
            'cx': CX,
            'cy': CY,
            'x': x0,
            'y': y0,
            'w': x1 - x0,
            'h': y1 - y0,
            'png': png_uri(Image.fromarray(rgba)),
            'radius': rad,
            'motion': '整环原印绕共同圆心旋转，圈数是整数，24 秒回到原位',
        })
    taiji = dist <= 19.6
    ys, xs = np.where(taiji)
    x0, x1 = int(xs.min()), int(xs.max()) + 1
    y0, y1 = int(ys.min()), int(ys.max()) + 1
    sub = arr[y0:y1, x0:x1]
    local = taiji[y0:y1, x0:x1]
    rgba = np.zeros((y1 - y0, x1 - x0, 4), np.uint8)
    rgba[local, :3] = sub[local]
    rgba[local, 3] = 255
    light = sub[local & (gray[y0:y1, x0:x1] > 140)]
    arr[taiji] = np.median(light, axis=0) if len(light) else 245
    taiji_sprite = {
        'id': 'taiji',
        'kind': 'taiji',
        'turns': 1,
        'cx': CX,
        'cy': CY,
        'x': x0,
        'y': y0,
        'w': x1 - x0,
        'h': y1 - y0,
        'png': png_uri(Image.fromarray(rgba)),
        'radius': 19.6,
        'motion': '中央太极原印绕自身圆心转 1 圈/24 秒',
    }
    return sprites, taiji_sprite


def colored_circles(arr: np.ndarray, skip: list) -> list:
    """轮外有颜色的圆点。轮内九层不在这里重复计算。"""
    r, g, b = arr[:, :, 0].astype(int), arr[:, :, 1].astype(int), arr[:, :, 2].astype(int)
    mx = np.maximum(np.maximum(r, g), b)
    mn = np.minimum(np.minimum(r, g), b)
    mask = ((mx - mn) > 45) & (mx > 80) & (mn < 230)
    h, w = mask.shape
    yy, xx = np.ogrid[:h, :w]
    dist = np.sqrt((xx - CX) ** 2 + (yy - CY) ** 2)
    mask[dist < 92] = False
    vis = np.zeros(mask.shape, bool)
    found = []
    from collections import deque
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
            if not 25 <= len(pts) <= 800:
                continue
            ys = np.array([p[0] for p in pts])
            xs = np.array([p[1] for p in pts])
            bh, bw = int(ys.max() - ys.min() + 1), int(xs.max() - xs.min() + 1)
            if not (0.65 <= bw / max(bh, 1) <= 1.55 and 8 <= bw <= 40):
                continue
            rad = max(bw, bh) / 2
            if len(pts) / (np.pi * rad * rad) < 0.42:
                continue
            ccx, ccy = float(xs.mean()), float(ys.mean())
            if ccx < 8 or ccy < 8 or ccx > w - 8 or ccy > h - 8:
                continue
            if any((ccx - s[0]) ** 2 + (ccy - s[1]) ** 2 < s[2] ** 2 for s in skip):
                continue
            found.append([ccx, ccy, rad, len(pts)])
    found.sort(key=lambda t: (t[1], t[0]))
    merged = []
    for item in found:
        if any((item[0] - m[0]) ** 2 + (item[1] - m[1]) ** 2 < 64 for m in merged):
            continue
        merged.append(item)
    return merged


def label_row(t, x0, y0, x1, y1, zone):
    w, h = x1 - x0, y1 - y0
    fs = max(8, min(14, round(h * 0.78)))
    if zone in ('disk', 'link', 'note') or t in ('足通谷', '阴谷'):
        fs = min(fs, 8)
    if zone == 'legend':
        fs = 7
    if zone == 'strip':
        fs = 6 if h <= 8 else 7
    row = {
        't': t,
        'x': round((x0 + x1) / 2, 1),
        'y': round((y0 + y1) / 2, 1),
        'fs': fs,
        'fw': 700,
        'halo': 0.25 if zone in ('legend', 'strip') else (0.45 if h < 16 else 0.6),
        'zone': zone,
    }
    if zone != 'legend' and zone != 'strip' and len(t) > 1 and 7 * len(t) <= w <= 20 * len(t):
        row['tl'] = w
    return row


def spin_svg(sprites: list) -> str:
    parts = ['<g id="spin">']
    for sp in sprites:
        parts.append(
            f'<g id="{sp["id"]}" data-spin="1" data-kind="{sp["kind"]}" data-turns="{sp["turns"]}" '
            f'data-cx="{sp["cx"]}" data-cy="{sp["cy"]}">'
        )
        if sp.get('png'):
            parts.append(
                f'<image href="{sp["png"]}" x="{sp["x"]}" y="{sp["y"]}" width="{sp["w"]}" height="{sp["h"]}"/>'
            )
        else:
            parts.append(
                f'<circle cx="{sp["cx"]}" cy="{sp["cy"]}" r="{sp["arc"]}" fill="none" '
                f'stroke="{sp["stroke"]}" stroke-width="{sp["sw"]}" stroke-linecap="round" '
                f'stroke-dasharray="{sp["dash"]}"/>'
            )
        parts.append('</g>')
    parts.append('</g>')
    return ''.join(parts)


SPIN_JS = r'''
let spinHeld=null;
function applySpin(){
  const scan=$('tgScan').checked;
  const textOn=$('tgText').checked;
  const flowOn=$('tgFlow').checked;
  $('spin').style.display=scan?'none':'';
  $('flows').style.display=(scan||!flowOn)?'none':'';
  $('nodes').style.display=scan?'none':'';
  $('nodesBack').style.display=scan?'none':'';
  $('pipes').style.display=scan?'none':'';
  $('ink').style.display=scan?'none':'';
  if($('taiji')) $('taiji').style.display=scan?'none':'';
  $('labels').style.display=(scan||!textOn)?'none':'';
  if(scan) return;
  let u=+$('scrub').value;
  if(document.body.classList.contains('quiet')){
    if(spinHeld==null) spinHeld=u;
    u=spinHeld;
  } else spinHeld=null;
  document.querySelectorAll('[data-spin]').forEach(el=>{
    const deg=u*(+el.getAttribute('data-turns'))*360;
    el.setAttribute('transform','rotate('+deg.toFixed(3)+' '+el.getAttribute('data-cx')+' '+el.getAttribute('data-cy')+')');
  });
}
const _seekSpin=window.seek;
window.seek=function(sec){_seekSpin(sec); if(document.body.classList.contains('quiet')) spinHeld=+$('scrub').value; applySpin();};
$('tgScan').addEventListener('change',()=>{spinHeld=null; applySpin();});
$('tgFlow').addEventListener('change',applySpin);
$('tgText').addEventListener('change',applySpin);
$('tgQuiet').addEventListener('change',()=>{spinHeld=null; applySpin();});
window.spinState=function(){return [...document.querySelectorAll('[data-spin]')].map(el=>({id:el.id,kind:el.getAttribute('data-kind'),turns:+el.getAttribute('data-turns'),transform:el.getAttribute('transform')||''}));};
(function spinLoop(){applySpin(); requestAnimationFrame(spinLoop);})();
'''


def main(extra_labels=None, out_html=None, coverage_path=None, inner=False):
    if not FONT.is_file():
        raise SystemExit('缺少 Noto 字体文件')
    before = {
        'source': sha256(SRC_HTML),
        'clear': sha256(OLD_HTML),
        'corrected': sha256(CORR_HTML),
    }
    user = json.loads(USER_JSON.read_text(encoding='utf-8'))
    cfg = json.loads((DIR / 'config.json').read_text(encoding='utf-8'))
    raw_uri = image_from(SRC_HTML)
    more = list(EXTRA) + list(extra_labels or [])
    out_path = Path(out_html) if out_html else OUT_HTML
    cov_path = Path(coverage_path) if coverage_path else (DIR / 'coverage-逐环旋转.json')
    reads = list(READS) + more
    placed_names = [{'t': t, 'zone': zone} for t, x0, y0, x1, y1, zone in reads]
    # 神门在原印里是上下两字，图上分成「神」「门」，待核名单里仍算这一个穴名。
    placed_names.append({'t': '神门', 'zone': 'lw-lo'})
    # 太、溪分在色条上下，合起来是核对后的太溪。
    placed_names.append({'t': '太溪', 'zone': 'lw-hi'})
    doc = {
        'id': 'b31',
        'draft': True,
        'title': '寸关尺 / 四季表里图（B/31）—— 逐环旋转文字版',
        'sub': '采用用户口述版。九层环各自整数圈旋转，24 秒回到原位，标为示意独立旋转。画面左是人体右腕，画面右是人体左腕。',
        'note': (
            '采用用户确认的轮周十二组原文，已写在主图对应彩点旁。未改的原印仍留在默认主图。动画为示意。'
            if inner else
            '采用用户口述版。按原图及用户转写复刻，未作经穴归属改编；动画为示意。默认主图保留未替换的原印。圈内字没有全部换成字体。心疏、中腕、腹瘤、步廊、经门待用户重录确认，没有写上主图。'
        ),
        'assumption': '能量仍沿原有路径。环的转向没有箭头，标示意独立旋转，不是六经传变。没有新的医理连线。',
        'credit': '原图 J. Martin-Hartz / Fondation Cornelius Celsus · 动画示意 · 用户补充署名：J.Martin-Herz（不覆盖原图手签，也不改写原署名）',
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
    nodes = [n for n in doc['nodes']]
    if len(nodes) != 12:
        raise SystemExit(f'序号圆不是 12 个，而是 {len(nodes)}')
    nodes.sort(key=lambda n: int(n['id'][1:]))
    digit_boxes = []
    for n, num in zip(nodes, NODE_NUMS):
        n['fill'] = 'none'
        n['t'] = num
        n['fs'] = 9 if len(num) == 1 else 7
        n['halo'] = 0.35
        if len(num) == 2:
            n['tl'] = 9
        half = 4 if len(num) == 1 else 5
        digit_boxes.append((n['x'] - half, n['y'] - 4, n['x'] + half, n['y'] + 4))
    for t, x0, y0, x1, y1, zone in reads:
        doc['labels'].append(label_row(t, x0, y0, x1, y1, zone))
    covered = cover_glyphs(raw_uri, [[x0, y0, x1, y1] for t, x0, y0, x1, y1, zone in READS])
    arr = decode_uri(covered)
    light_keys = set(LIGHT_KEYS)
    glyph_keys = {(t, x0) for t, x0, y0, x1, y1, zone in (extra_labels or [])}
    paper = [e for e in more if (e[0], e[1]) not in DISK_KEYS and (e[0], e[1]) not in light_keys and (e[0], e[1]) not in glyph_keys]
    lights = [e for e in more if (e[0], e[1]) in light_keys]
    disks = [e for e in more if (e[0], e[1]) in DISK_KEYS]
    glyphs = [e for e in more if (e[0], e[1]) in glyph_keys]
    soft_cover(arr, [[x0, y0, x1, y1] for t, x0, y0, x1, y1, zone in paper], 'paper')
    soft_cover(arr, [[x0, y0, x1, y1] for t, x0, y0, x1, y1, zone in lights], 'light')
    soft_cover(arr, [[x0, y0, x1, y1] for t, x0, y0, x1, y1, zone in disks], 'disk')
    soft_cover(arr, [[x0, y0, x1, y1] for t, x0, y0, x1, y1, zone in glyphs], 'glyph')
    soft_cover(arr, digit_boxes)
    sprites, taiji = ring_and_taiji(arr)
    skip = [(CX, CY, 92)]
    skip += [(n['x'], n['y'], n['r'] + 2) for n in nodes]
    skip += [(c['cx'], c['cy'], c['r']) for c in MANUAL_CIRCLES]
    blobs = colored_circles(arr, skip)
    circles = []
    for i, (ccx, ccy, rad, area) in enumerate(blobs):
        turns = (1 if i % 2 == 0 else -1) * (2 if i % 5 == 0 else 1)
        circles.append({
            'id': f'dot{i}',
            'kind': 'dot',
            'turns': turns,
            'cx': round(ccx, 1),
            'cy': round(ccy, 1),
            'r': round(rad, 1),
            'area': area,
            'motion': '绕自身圆心的亮弧，圆心不移动',
        })
    for i, c in enumerate(MANUAL_CIRCLES):
        turns = -1 if i % 2 else 1
        circles.append({
            **c,
            'kind': 'named',
            'turns': turns * 2,
            'motion': '圈内已换嵌入字体并保持正向；圆本身以亮弧自转，圆心不移动',
        })
    arc_sprites = list(sprites) + [taiji]
    for c in circles:
        lum_x, lum_y = int(c['cx']), int(c['cy'])
        sample = arr[max(0, lum_y - 2):lum_y + 3, max(0, lum_x - 2):lum_x + 3]
        lum = float(sample.mean()) if sample.size else 200
        dark = lum < 165
        arc_sprites.append({
            'id': c['id'],
            'kind': c['kind'],
            'turns': c['turns'],
            'cx': c['cx'],
            'cy': c['cy'],
            'arc': round(max(2.4, c['r'] * 0.78), 2),
            'stroke': '#fff6d8' if dark else '#6b5424',
            'sw': 1.5 if c['r'] >= 10 else 1.15,
            'dash': '7 16' if c['r'] >= 10 else '3 8',
        })
    # 十二个序号圆的虚线环已经跟着主时钟走，这里只登记，不再叠第二条弧。
    for n, num in zip(nodes, NODE_NUMS):
        circles.append({
            'id': n['id'],
            'kind': 'node',
            'turns': None,
            'cx': n['x'],
            'cy': n['y'],
            'r': n['r'],
            'name': num,
            'motion': '原有序号圆虚线环随主时钟转动；圈内数字改成嵌入字体并保持正向',
        })

    panel, placed_n, pending_n = panel_html(user, placed_names)
    mapping = (
        '<div class="extra"><p><b>2026-11-17 10:30 夏火区，用户逐字确认，已写入本页。</b> '
        '画面右下是人体左腕。右列大红圈是少府，左列大红圈是阳谷，左下红白圈是阳，右下绿白圈是阴。'
        '这四个圈内已换成嵌入字体，不再放在本区待核名单。后溪按统一标准显示后溪，原字后谿留在异体记录，不是另一个穴。'
        '面血、语言两行按用户原文，不改成面色或舌。手、太阳、小、肠、经是左列旁的「手太阳 小肠经」；'
        '手、少、阴、心、经是右列旁的「手少阴 心经」。神、门上下两字是神门。'
        '用户补充署名：J.Martin-Herz。原图手签留在原图对照里，不覆盖，也不把 Herz 写成对 Hartz 的改写。</p>'
        '<p><b>2026-11-17 10:41 冬水区，用户逐字确认，已写入本页。</b> '
        '画面右上。足太阳膀胱经显示至阴、足通谷、束骨、京骨、昆仑、委中；足少阴肾经显示涌泉、然谷、太溪、复溜、阴谷。'
        '足通谷是核对后的写法，原文通谷留在异体记录，用来区别手通谷。太溪、申脉、后溪用简体，原文太谿、申脈、後谿保留。'
        '太在色条上、溪在色条下，合起来是太溪。左列红圈是足通谷，右列红圈是阴谷。'
        '空白圆里是发、骨、听觉。圈下是申脉、后溪。'
        '旁边绿色连接圆里是肝，圈外竖排是厥阴经；这不是春木大区括号里的肝。'
        '绿圆下方大红圈是小肠；这不是夏火大区括号里的小肠。紧挨着的另一枚小红圈，圈内字认不清，用户没有给第二个名字，仍留原印。'
        '左列旁竖排是足太阳，右列旁竖排是足少阴，阴谷左侧竖排是肾经。忍、人写在右上引线旁的原位。'
        '筋骨感觉按用户原文收录，这一带没有对上明确原位，位置待核，不改成别的词。</p>'
        '<p>九层环各自按 1、−2、3、−1、2、−3、4、−4、5 圈每 24 秒绕共同圆心转，方向是示意独立旋转，不是六经传变。'
        '环上未替换的序号留在该环的原印里，随环转动。轮周横条、圆内未替换的字、黑线旁注留在默认主图的原位，不随环转，也不被环层遮住。'
        '序号圆 1、13、17、5 以及其余奇数序号，仍写在各自原来的圆里，没有按名单重排。'
        '底部路径图例按口述写成路径：、可行、破滞。上面这些圆各自有亮弧自转，圈内新字保持正向。'
        '勾选原图对照时，旋转层、能量和新字一起藏起，底图换成未改的原图。</p></div>'
    )
    oral_confirmed = (
        '<h2>轮周十二组，按用户确认文字写在主图</h2>'
        '<p>2026-11-17 11:08 与 11:09 的十二组优先于先前口述。心俞、丝竹空、中脘、复溜、京门、步廊、五枢按这次文字。'
        '丝竹空只写在中央三焦这一串，外围夏火区的阳谷不动。'
        '中下这一串是厉兑、至阴、冲阳、束骨、承扬、睛明、中极、膀胱俞，不覆盖另一串冲阳、解溪、厉兑、头维、丰隆、中脘、胃俞，也不另起经名。'
        '没有逐字对上彩点的词不会被猜放；这一轮十二组的穴名都按彩点顺序写在原串上。</p>'
    )
    oral_archive = (
        '<h2>采用用户口述版</h2>'
        '<p>文字消息里已经写明、并且字框对得上的，留在主图。组号只是口述顺序，不是扇区坐标。'
        '位置对不上的不往扇区里猜放，主图仍是原印。这一页不是国家标准核对，圈内字也没有全部换成字体。</p>'
        '<p><b>待用户重录确认，没有写上主图。</b>心疏、中腕、腹瘤、步廊、经门。'
        '这五个是通话里没听清的词，只留在这里供下一段校对。不把它们当成确定字体，也不换成别的穴名。</p>'
        '<p><b>10:50 文字消息里的中央轮周。</b>右上：太冲、曲泉、行间、大敦、期门、蠡沟、肝俞。'
        '右中：腕骨、后溪、小海、支正、少泽、颧髎、关元、小肠俞。'
        '右下：太渊、尺泽、中府、列缺、肺俞。'
        '中下：厉兑、至阴、冲阳、束骨、承扬、睛明、中极、膀胱俞。承扬按消息原字。'
        '左下：合谷、曲池、二间、三间、偏历、天枢、大肠俞、迎香。'
        '左上：丘墟、侠溪、阳辅、童子髎、足临泣、光明、中渎、悬钟、日月、胆俞。童子髎按消息原字。'
        '外围六区已经有字框的同名穴维持该处新字。轮周横条没有逐条新字框，默认主图保留原印，上列是口述待定位。'
        '底部路径图例已按消息写成路径：、可行、破滞。</p>'
        '<p><b>10:53 口述四组，未落新坐标。</b>'
        '第一组听到：神门、少冲、通里、极泉、巨阙；心疏见上，待重录。'
        '第二组：阳谷、阳池、中渚、天井、关冲、外关、石门、三焦俞。阳谷不改作支沟。'
        '第三组：太白、大都、商丘、隐白、大包、公孙、章门、脾俞。'
        '第四组：大陵、中冲、天池、劳宫、内关、厥阴俞。'
        '其中神门、少冲、阳谷、阳池、中渚、天井、关冲、大都、商丘、中冲已在外围原位。其余没有新字框。</p>'
        '<p><b>10:54 口述两组，未落新坐标。</b>丰隆、胃俞，以及太溪、涌泉、然谷、大钟、肾俞、照海。'
        '中腕、腹瘤、步廊、经门见上，待重录，不写上主图。'
        '太溪、涌泉、然谷已在冬水区原位。丰隆、胃俞、大钟、肾俞、照海没有新字框，主图留原印。</p>'
    )
    oral = oral_confirmed if inner else oral_archive
    gap_html = '<h2>轮内还没有写入的字</h2><ul>' + ''.join('<li>' + line + '</li>' for line in WHEEL_GAPS) + '</ul>'
    if inner:
        kept_html = (
            '<h2>默认主图里的原印</h2>'
            '<p>底图是完整原图。轮周十二组已换成嵌入字体，只遮这十二串和先前已经换过的字。'
            '环上序号、还没换的圆内字、黑线旁注仍留在默认主图。环层不盖环外扇区。'
            '底部路径三字是路径：、可行、破滞。</p>'
            + oral
        )
    else:
        kept_html = (
            '<h2>默认主图里的原印</h2>'
            '<p>底图是完整原图。只遮已经换成嵌入字体、并且字框落在原笔画上的那些字。'
            '左右轮周约 25 条图例横条、环上序号、尚未替换的圆内字、黑线旁注，都留在默认主图。'
            '环层只取九层色环自身的像素，不盖环外扇区。底部路径三字已换成路径：、可行、破滞，样条线仍在。</p>'
            + oral
        )
    if gap_html not in panel:
        raise SystemExit('找不到轮内缺口段落')
    panel = panel.replace(gap_html, kept_html)
    tpl = TPL.read_text(encoding='utf-8')
    tpl = tpl.replace('__FLOW__', FLOW.read_text(encoding='utf-8'))
    page_doc = json.loads(json.dumps(doc))
    for lab in page_doc['labels']:
        lab.pop('zone', None)
    page = tpl.replace('__TITLE__', page_doc['title'])
    page = page.replace('__CFG__', json.dumps(page_doc, ensure_ascii=False).replace('<', '\\u003c'))
    page = page.replace('__IMG__', jpeg_uri(arr)).replace('__RAW__', raw_uri)
    chars = ''.join(sorted({c for c in page + panel + mapping if ord(c) >= 32}))
    subset = Path('/tmp') / '_clear_b31spin.woff2'
    subset_woff2(chars, FONT, subset, None)
    url = data_url(subset, 'font/woff2')
    subset.unlink(missing_ok=True)
    page = page.replace('__FONTR__', f"url({url}) format('woff2')").replace('__FONTB__', f"url({url}) format('woff2')")
    page = page.replace('</style>', STYLE + '</style>', 1)
    page = page.replace('<g id="ink"></g>', spin_svg(arc_sprites) + '<g id="ink"></g>', 1)
    page = page.replace('<div class="note" id="note"></div>', '<div class="note" id="note"></div>\n' + panel + mapping, 1)
    page = page.replace('</script>\n</body>', SPIN_JS + '</script>\n</body>', 1)
    external = page.replace('http://www.w3.org/2000/svg', '')
    for cite in (user.get('reading') or {}).get('citations') or []:
        external = external.replace(cite, '')
    if 'http://' in external or 'https://' in external:
        raise SystemExit('逐环旋转版出现了外链')
    out_path.write_text(page, encoding='utf-8')
    after = {
        'source': sha256(SRC_HTML),
        'clear': sha256(OLD_HTML),
        'corrected': sha256(CORR_HTML),
    }
    if after != before:
        raise SystemExit('原件、清晰版或文字校正版被写到了')
    font_labels = len(doc['labels']) + len(nodes)
    report = {
        'id': 'b31-spin',
        'html': out_path.name,
        'bytes': out_path.stat().st_size,
        'draft': True,
        'not_full_transcription': True,
        'circle_interiors_not_all_replaced': True,
        'awaiting_rerecord': ['心疏', '中腕', '腹瘤', '步廊', '经门'],
        'source': '采用用户口述版。10:30 夏火、10:41 冬水、10:50 轮周、10:53 与 10:54 口述组，并入同一逐环旋转文字版。不是 OCR，也不是国家标准核对。',
        'legend_path_replaced': ['路径：', '可行', '破滞'],
        'oral_unplaced': {
            '1050_wheel_strips': '左右轮周穴名按用户分区原文收录，没有逐条新字框，主图保留原印。外围已有字框的同名穴不另搬。',
            '1053_no_new_box': ['通里', '极泉', '巨阙', '外关', '石门', '三焦俞', '太白', '隐白', '大包', '公孙', '章门', '脾俞', '大陵', '天池', '劳宫', '内关', '厥阴俞'],
            '1053_already_on_outer_figure': ['神门', '少冲', '阳谷', '阳池', '中渚', '天井', '关冲', '大都', '商丘', '中冲'],
            '1054_word_set_position_not_boxed': ['丰隆', '胃俞', '大钟', '肾俞', '照海'],
            'awaiting_rerecord': ['心疏', '中腕', '腹瘤', '步廊', '经门'],
            'glyph_notes': {
                '心疏': '待用户重录确认。未写入主图，也未改成别的字。',
                '中腕': '待用户重录确认。未写入主图，也未改成别的字。',
                '腹瘤': '待用户重录确认。未写入主图，也未改成别的字。',
                '步廊': '待用户重录确认。未写入主图，也未改成别的字。',
                '经门': '待用户重录确认。未写入主图，也未改成别的字。',
                '承扬': '10:50 文字消息原字。轮周横条未逐条落字框，主图留原印。',
                '童子髎': '10:50 文字消息原字。轮周横条未逐条落字框，主图留原印。',
                '破滞': '底部图例按 10:50 文字消息写入。',
            },
        },
        'winter_1041': {
            'placed': ['足通谷', '太溪', '阴谷', '申脉', '后溪', '发', '骨', '听觉', '肝（连接圆）', '厥阴经', '小肠（连接圆）', '足太阳', '足少阴', '肾经', '忍', '人'],
            'display': {'通谷': '足通谷', '太谿': '太溪', '申脈': '申脉', '後谿': '后溪'},
            'position_pending': ['筋骨感觉'],
            'unread_neighbor_circle': '绿色肝圆下方、小肠红圈旁边的小红圈，圈内未辨认，未改字',
        },
        'signature_note': '用户补充署名：J.Martin-Herz。原图手签与页脚 J. Martin-Hartz 都保留，没有互相改写。',
        'labels_font': font_labels,
        'labels_from_correction': len(READS),
        'labels_added_1030': len(EXTRA),
        'labels_inner': len(extra_labels or []),
        'node_digits_font': NODE_NUMS,
        'names_accounted': placed_n,
        'names_pending_position': pending_n,
        'ring_turns_per_24s': RING_TURNS,
        'ring_motion': '示意独立旋转，整数圈，t=24 与 t=0 重合。环上序号保留原印并随环转动。',
        'legend_strips_kept_as_ink': 25,
        'taiji': {'cx': CX, 'cy': CY, 'r': 19.6, 'turns': 1},
        'circles': [
            {k: v for k, v in c.items() if k != 'png'}
            for c in ([{**s, 'kind': 'ring'} for s in sprites] + [taiji] + circles)
        ],
        'circle_count': 9 + 1 + len(circles),
        'unchanged_sha': {k: v[:16] for k, v in before.items()},
    }
    cov_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('labels', len(doc['labels']), 'nodes', len(nodes), 'dots', len(blobs), 'named', len(MANUAL_CIRCLES))
    print('accounted', placed_n, 'pending', pending_n, 'MB', round(out_path.stat().st_size / 1e6, 2))
    print('unchanged', report['unchanged_sha'])


if __name__ == '__main__':
    main()
