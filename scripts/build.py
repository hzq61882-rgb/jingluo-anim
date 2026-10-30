#!/usr/bin/env python3
"""把扫描图和 config.json 收成一份单文件 HTML。

用法：
  python scripts/build.py --config template/config.json --image scan.jpg --out out.html

页面含播放/暂停、主流与黑线两档速度、图层开关、右上图例。
地址栏加 ?video=1 时隐藏控件，只留画面，供 scripts/record.py 逐帧截图。
Noto Sans CJK 子集嵌进页面。繁体用字体集索引 3。

底图若是 config 宽高的整数倍（B/24 的 clean.jpg 是 595×808 的 2 倍，1190×1616），
自动保留 config 的 W/H，坐标不用改，也不必再传 --keep-size。
模板里的 __LF__ 是黑线流光相位图，用 --lineflow 指定，或放一份 lineflow.png 在 config / 底图旁边。
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
    p.add_argument('--lineflow', default=None,
                   help='黑线流光相位图 PNG，替换模板里的 __LF__。省略时用 config 或底图同目录的 lineflow.png')
    p.add_argument('--keep-size', action='store_true',
                   help='保留 config 的 W/H。整数倍大图（例如 2×）会自动这样做')
    p.add_argument('--use-image-size', action='store_true',
                   help='把 W/H 改成图片像素。坐标若是按 config 描的会错位')
    return p.parse_args(argv)


def warn(msg):
    print(msg, file=sys.stderr, flush=True)


def resolve_canvas(cfg, image, keep_size, use_image_size):
    """决定画面 W/H。整数倍大图保留 config 坐标，避免 2× 底图把坐标撑歪。"""
    iw, ih = image.size
    cw, ch = cfg.get('W'), cfg.get('H')
    if use_image_size and keep_size:
        raise SystemExit('--keep-size 与 --use-image-size 不能同时用')
    if use_image_size:
        if cw and ch and (int(cw), int(ch)) != (iw, ih):
            warn(f'警告：--use-image-size 把 W/H 从 {cw}×{ch} 改成图片 {iw}×{ih}。坐标若是按原来的 W/H 描的，会错位。')
        cfg['W'], cfg['H'] = iw, ih
        return
    if not cw or not ch:
        cfg['W'], cfg['H'] = iw, ih
        return
    if (iw, ih) == (int(cw), int(ch)):
        return
    sx, sy = iw / float(cw), ih / float(ch)

    def near_int(scale):
        rounded = round(scale)
        return rounded >= 2 and abs(scale - rounded) <= 1e-3

    if near_int(sx) and near_int(sy) and round(sx) == round(sy):
        multiple = int(round(sx))
        warn(
            f'底图 {iw}×{ih} 是 config {int(cw)}×{int(ch)} 的 {multiple} 倍，已保留 config 的 W/H。'
            f'坐标仍是扫描图像素，SVG 把大图缩进画面。不必再传 --keep-size。'
            f'若要把画面改成图片像素，用 --use-image-size。'
        )
        return
    if keep_size:
        warn(
            f'警告：--keep-size 保留 config {cw}×{ch}，图片是 {iw}×{ih}，不是整数倍。'
            f'坐标按 config，图片会被拉进这个画面，比例不对时会变形。'
        )
        return
    warn(
        f'警告：config {cw}×{ch} 与图片 {iw}×{ih} 不一致，且不是整数倍，已把 W/H 改成图片尺寸。'
        f'坐标若是按 config 描的会错位。整数倍大图（例如 2×）会自动保留 config 尺寸；'
        f'其它情况要对齐原来的坐标请加 --keep-size。'
    )
    cfg['W'], cfg['H'] = iw, ih


def resolve_lineflow(explicit, config_path, image_path):
    if explicit:
        path = Path(explicit)
        if not path.is_file():
            raise SystemExit(f'找不到流光图：{path}')
        return path
    seen = []
    for base in (Path(config_path).resolve().parent, Path(image_path).resolve().parent):
        cand = base / 'lineflow.png'
        if cand not in seen:
            seen.append(cand)
    for cand in seen:
        if cand.is_file():
            return cand
    return None


def main(argv=None):
    args = parse_args(argv or sys.argv[1:])
    cfg = load_json(args.config)
    image = Image.open(args.image).convert('RGB')
    resolve_canvas(cfg, image, args.keep_size, args.use_image_size)

    durations = [float(s.get('dur', 0)) for s in cfg.get('steps') or []]
    cycle = float(cfg.get('cycle') or 0)
    if durations and cycle and abs(sum(durations) - cycle) > 0.05:
        warn(f'警告：steps.dur 之和 {sum(durations):.3f} 与 cycle {cycle:.3f} 不一致，循环接缝会错位')

    import json
    cfg_text = json.dumps(cfg, ensure_ascii=False).replace('<', '\\u003c')
    template = Path(args.template).read_text(encoding='utf-8')
    needs_lineflow = '__LF__' in template
    lineflow = None
    if needs_lineflow:
        lineflow = resolve_lineflow(args.lineflow, args.config, args.image)
        if lineflow is None:
            raise SystemExit(
                '模板含 __LF__（黑线流光相位图），但没有可用的 PNG。\n'
                '把 lineflow.png 放在 config 或底图同目录，或用 --lineflow 指定。\n'
                '生成：python scripts/lineflow.py --image clean.jpg --out lineflow.png'
            )
        with Image.open(lineflow) as phase:
            if phase.size != image.size:
                warn(
                    f'警告：流光图 {phase.size[0]}×{phase.size[1]} 与底图 {image.size[0]}×{image.size[1]} 像素不同，'
                    f'SVG 会分别拉到 {cfg["W"]}×{cfg["H"]}。'
                )
    elif args.lineflow:
        warn('警告：给了 --lineflow，但模板里没有 __LF__，流光图没有嵌进去。')
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
    if lineflow is not None:
        template = template.replace('__LF__', data_url(lineflow, 'image/png'))
    html = (template
            .replace('__TITLE__', str(cfg.get('title') or '经络流动画'))
            .replace('__MAXW__', str(maxw))
            .replace('__FONTR__', font_regular)
            .replace('__FONTB__', font_bold)
            .replace('__IMG__', img_url)
            .replace('__CFG__', cfg_text))
    if '__LF__' in html:
        raise SystemExit('输出里仍有 __LF__，流光图没有替换干净。')
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding='utf-8')
    lf_note = f'  lineflow {lineflow.name}' if lineflow else ''
    print(
        f'wrote {out}  {out.stat().st_size // 1024} KB  items {len(cfg.get("items") or [])}  {cfg["W"]}×{cfg["H"]}{lf_note}',
        flush=True,
    )


if __name__ == '__main__':
    main()
