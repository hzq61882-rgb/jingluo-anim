#!/usr/bin/env python3
"""把扫描图和 config.json 收成一份单文件 HTML。

用法：
  python scripts/build.py --config template/config.json --image scan.jpg --out out.html

页面含播放/暂停、主流与黑线两档速度、图层开关、右上图例。
地址栏加 ?video=1 时隐藏控件，只留画面，供 scripts/record.py 逐帧截图。
Noto Sans CJK 子集嵌进页面。繁体用字体集索引 3。
"""
from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import data_url, find_cjk_font, load_json, subset_woff2  # noqa: E402

try:
    from PIL import Image
except ImportError as exc:
    raise SystemExit('需要 pillow：pip install -r scripts/requirements.txt') from exc


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEMPLATE = ROOT / 'template' / 'template.html'


def parse_args(argv):
    p = argparse.ArgumentParser(description='合成单文件经络流动画 HTML')
    p.add_argument('--config', required=True, help='图表 config.json')
    p.add_argument('--image', required=True, help='去手写后的底图（jpg/png）')
    p.add_argument('--template', default=str(DEFAULT_TEMPLATE), help='HTML 模板')
    p.add_argument('--out', required=True, help='输出 HTML')
    p.add_argument('--quality', type=int, default=90, help='底图 JPEG 质量')
    p.add_argument('--maxw', type=int, default=None, help='页面最大宽度，默认用 config.maxw 或 820')
    p.add_argument('--skip-fonts', action='store_true', help='不嵌字体，改用系统里的 Noto')
    p.add_argument('--font-regular', default=None)
    p.add_argument('--font-bold', default=None)
    p.add_argument('--font-index', type=int, default=3, help='TTC 里的繁体字面，NotoSansCJK 为 3')
    p.add_argument('--keep-size', action='store_true', help='保留 config 里的 W/H，不改成图片尺寸')
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv or sys.argv[1:])
    cfg = load_json(args.config)
    image = Image.open(args.image).convert('RGB')
    if not args.keep_size:
        cfg['W'], cfg['H'] = image.size
    elif cfg.get('W') != image.size[0] or cfg.get('H') != image.size[1]:
        print(f'警告：config 尺寸 {cfg.get("W")}×{cfg.get("H")} 与图片 {image.size[0]}×{image.size[1]} 不同', file=sys.stderr)

    durations = [float(s.get('dur', 0)) for s in cfg.get('steps') or []]
    cycle = float(cfg.get('cycle') or 0)
    if durations and cycle and abs(sum(durations) - cycle) > 0.05:
        print(f'警告：steps.dur 之和 {sum(durations):.3f} 与 cycle {cycle:.3f} 不一致，循环接缝会错位', file=sys.stderr)

    import json
    cfg_text = json.dumps(cfg, ensure_ascii=False).replace('<', '\\u003c')
    template = Path(args.template).read_text(encoding='utf-8')
    chars = set(cfg_text) | set(template) | set('0123456789.×▶⏸暂停播放速度进度 ')

    if args.skip_fonts:
        font_regular = "local('Noto Sans CJK TC'),local('Noto Sans CJK SC')"
        font_bold = font_regular
    else:
        regular = find_cjk_font(400, args.font_regular)
        bold = find_cjk_font(700, args.font_bold)
        text = ''.join(sorted(c for c in chars if ord(c) >= 32))
        tmp = Path(args.out).resolve().parent
        reg_path = subset_woff2(text, regular, tmp / '_noto_400.woff2', args.font_index)
        bold_path = subset_woff2(text, bold, tmp / '_noto_700.woff2', args.font_index)
        font_regular = f"url({data_url(reg_path, 'font/woff2')}) format('woff2')"
        font_bold = f"url({data_url(bold_path, 'font/woff2')}) format('woff2')"
        reg_path.unlink(missing_ok=True)
        bold_path.unlink(missing_ok=True)

    buf = io.BytesIO()
    if Path(args.image).suffix.lower() == '.png':
        image.save(buf, 'PNG')
        mime = 'image/png'
    else:
        image.save(buf, 'JPEG', quality=args.quality)
        mime = 'image/jpeg'
    import base64
    img_url = f'data:{mime};base64,' + base64.b64encode(buf.getvalue()).decode('ascii')

    maxw = args.maxw or cfg.get('maxw') or 820
    html = (template
            .replace('__TITLE__', str(cfg.get('title') or '经络流动画'))
            .replace('__MAXW__', str(maxw))
            .replace('__FONTR__', font_regular)
            .replace('__FONTB__', font_bold)
            .replace('__IMG__', img_url)
            .replace('__CFG__', cfg_text))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding='utf-8')
    print(f'wrote {out}  {out.stat().st_size // 1024} KB  items {len(cfg.get("items") or [])}  {cfg["W"]}×{cfg["H"]}')


if __name__ == '__main__':
    main()
