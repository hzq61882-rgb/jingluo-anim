#!/usr/bin/env python3
"""把 B/4 圆环版 HTML 收成增强版，不改输入文件。

嵌入的扫描图原样保留。字体按整页用到的字从 Noto Sans CJK 传统汉字重切，
这样新增的说明不会缺字。页面不引用网络。

  python scripts/ring_enhance.py \
    --src examples/b4-maizhen/backup/2026-11-16-圆环版/经络流注动画_圆环版.html \
    --out examples/b4-maizhen/经络流注动画_圆环版_增强版.html
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import data_url, find_cjk_font, subset_woff2  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]

CSS = """
  @media (max-width:720px){
    .wrap{padding:8px}
    h1{font-size:17px;letter-spacing:0}
    .ctl{gap:8px 12px;font-size:15px}
    input[type=range]{width:min(100%,220px);max-width:100%}
    button,select{min-height:40px;padding:8px 14px}
  }
  .ctl{max-width:100%}
  .pipe-swarm{pointer-events:none}
  body.quiet .fx-crowd{display:none}
  body.hc{background:#120814;color:#fff}
  body.hc .note,body.hc .sub{color:#f6efe2}
  body.hc .ctl{background:#1a0b22;border:1px solid #D4AF37;border-radius:6px;padding:8px}
"""

CTL = """<div class="ctl" id="ctlEnhance">
  <label><input type="checkbox" id="tg_pipe" checked> 管内粒子</label>
  <label><input type="checkbox" id="tg_quiet"> 减弱动效</label>
  <label><input type="checkbox" id="tg_contrast"> 高对比</label>
</div>
"""

OLD_CREDIT = '十二经子午流注 · 原图 J. Martin-Hartz / Fondation Cornelius Celsus · 动画示意'
NEW_CREDIT = '十二经子午流注 · 示意 · U形无箭头沿描线往返 · 圆环放射非疗效 · J. Martin-Hartz / Celsus'
MARKER = 'let T=0,TB=0,playing=true,speed=1,bspeed=1,last=null;'


def parse_args(argv):
    p = argparse.ArgumentParser(description='由圆环版生成 B/4 增强版 HTML')
    p.add_argument('--src', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--font', default=None, help='Noto Sans CJK 传统汉字，默认在系统里找')
    return p.parse_args(argv)


def splice(html, flow, ring):
    if MARKER not in html:
        raise SystemExit('源页面没有预期的播放时钟，不能在这份 HTML 上增强。')
    if html.count(MARKER) != 1:
        raise SystemExit('播放时钟出现了不止一次。')
    if '</style>' not in html or '<div class="note">' not in html:
        raise SystemExit('源页面结构对不上。')
    html = html.replace('</style>', CSS + '</style>', 1)
    html = html.replace('经络流注动画（圆环版）', '经络流注动画（圆环版·增强版）')
    if OLD_CREDIT not in html:
        raise SystemExit('找不到页脚署名，没有改页脚。')
    html = html.replace(
        f'<text x="102" y="891" font-size="9.5" fill="#cbb6dc">{OLD_CREDIT}</text>',
        f'<text id="capCredit" x="102" y="891" font-size="8.2" fill="#ffd9a0">{NEW_CREDIT}</text>',
        1,
    )
    html = html.replace('<div class="note">', CTL + '<div class="note">', 1)
    i = html.find(MARKER)
    j = html.find('</script>', i)
    if j < 0:
        raise SystemExit('脚本没有收尾。')
    injection = flow.rstrip() + '\n' + ring.rstrip() + '\nJingluoRing.bindControls();\n'
    html = html[:i] + injection + html[j:]
    banner = (
        '<!-- 增强版 2026-11-16。底图沿用圆环版。'
        '旧文件 examples/b4-maizhen/backup/2026-11-16-圆环版/ 未改。'
        '时间轴与管内粒子见 template/flow.js、template/ring-pipes.js。 -->\n'
    )
    if banner.strip() not in html:
        html = html.replace('<!DOCTYPE html>\n', '<!DOCTYPE html>\n' + banner, 1)
    return html


def embed_font(html, font_path):
    chars = ''.join(sorted({c for c in html if ord(c) >= 32}))
    out = Path(font_path).parent  # unused
    del out
    subset = Path('/tmp') / '_jingluo_ring_subset.woff2'
    subset_woff2(chars, Path(font_path), subset, font_index=3 if str(font_path).lower().endswith(('.ttc', '.otc')) else None)
    url = data_url(subset, 'font/woff2')
    subset.unlink(missing_ok=True)
    html2, n = re.subn(
        r'src:url\(data:font/woff2;base64,[A-Za-z0-9+/=]+\)',
        'src:url(' + url + ')',
        html,
        count=1,
    )
    if n != 1:
        raise SystemExit('没有替换到内嵌字体。')
    return html2


def main(argv=None):
    args = parse_args(argv or sys.argv[1:])
    src = Path(args.src)
    html = src.read_text(encoding='utf-8')
    if 'data:image/jpeg;base64,' not in html:
        raise SystemExit('源页面没有内嵌底图，拒绝做成空壳。')
    flow = (ROOT / 'template' / 'flow.js').read_text(encoding='utf-8')
    ring = (ROOT / 'template' / 'ring-pipes.js').read_text(encoding='utf-8')
    html = splice(html, flow, ring)
    font = Path(args.font) if args.font else find_cjk_font(400)
    html = embed_font(html, font)
    if '君宝学中医' in html:
        raise SystemExit('增强版里出现了不该加的「君宝学中医」。')
    if '__FLOW__' in html or '__IMG__' in html:
        raise SystemExit('占位符没有清掉。')
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding='utf-8')
    print(f'wrote {out}  {out.stat().st_size / 1_000_000:.2f} MB', flush=True)


if __name__ == '__main__':
    main()
