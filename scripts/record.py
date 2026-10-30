#!/usr/bin/env python3
"""把单文件 HTML 录成 HD MP4、GIF 和一张静帧 PNG。

页面必须提供 window.renderAt(秒) 和 window.CYC，并在 ?video=1 时只显示画面。
template/template.html 已经这样做。

  python scripts/record.py --html animation.html --out-dir out --name chart

MP4 用 libx264、yuv420p，高度取偶数。CRF 从 18 加到 36，直到文件不超过 --mp4-max-mb（默认 15）。
GIF 依次试更窄的宽度（最窄 160）和更少的调色板颜色，直到不超过 --gif-max-mb（默认 9.9）。
体积用十进制 MB（1 MB = 10^6 字节），打印出来的数和上限比较用的是同一把尺子。
帧数 = round(cycle * fps)，这样首尾相接时图案周期是整数圈。进度行会立刻刷出。
"""
from __future__ import annotations

import argparse
import asyncio
import os
import shutil
import subprocess
import sys
from pathlib import Path


# 与 --mp4-max-mb / --gif-max-mb 一致：十进制兆字节，不是 1024² 的 MiB。
BYTES_PER_MB = 1_000_000


def chrome_path():
    env = os.environ.get('CHROME') or os.environ.get('CHROME_PATH')
    candidates = [env, '/usr/bin/google-chrome', '/usr/bin/google-chrome-stable',
                  '/usr/bin/chromium', '/usr/bin/chromium-browser']
    for path in candidates:
        if path and Path(path).is_file():
            return path
    return None


def parse_args(argv):
    p = argparse.ArgumentParser(description='录制流动画为 MP4 / GIF / PNG')
    p.add_argument('--html', required=True)
    p.add_argument('--out-dir', required=True)
    p.add_argument('--name', required=True, help='输出文件名，不含扩展名')
    p.add_argument('--fps', type=int, default=30)
    p.add_argument('--width', type=int, default=1280, help='画面宽度。1280 为 HD 宽，画面按原比例变高')
    p.add_argument('--mp4-max-mb', type=float, default=15.0, help='MP4 上限，十进制 MB（10^6 字节）')
    p.add_argument('--gif-max-mb', type=float, default=9.9, help='GIF 上限，十进制 MB（10^6 字节）')
    p.add_argument('--gif-widths', default='540,480,420,360,320,280,240,200,160',
                   help='GIF 宽度候选，逗号分隔，从大到小试到不超限')
    p.add_argument('--gif-colors', default='160,128,96,64')
    p.add_argument('--gif-fps', type=int, default=10)
    p.add_argument('--still-time', type=float, default=None, help='静帧时间（秒）。默认不另出高清静帧，除非给了这个值')
    p.add_argument('--still-width', type=int, default=1920)
    p.add_argument('--limit-frames', type=int, default=None, help='只画前 N 帧，用来试编码体积')
    p.add_argument('--keep-frames', action='store_true')
    p.add_argument('--crf', default='18,20,22,24,26,28,30,32,34,36',
                   help='MP4 CRF 候选，逗号分隔，从小到大试到不超限')
    p.add_argument('--chrome', default=None)
    return p.parse_args(argv)


async def grab(html, frames_dir, width, fps, limit, still, chrome):
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise SystemExit('需要 playwright：pip install playwright。系统已有 Chrome 时不必再 playwright install。') from exc
    html = Path(html).resolve()
    launch = {'args': ['--force-color-profile=srgb', '--no-sandbox', '--disable-dev-shm-usage']}
    if chrome:
        launch['executable_path'] = chrome
    async with async_playwright() as p:
        browser = await p.chromium.launch(**launch)
        page = await browser.new_page(viewport={'width': width, 'height': 400})
        errors = []
        page.on('pageerror', lambda err: errors.append(str(err)))
        await page.goto(html.as_uri() + '?video=1')
        await page.wait_for_timeout(800)
        box = await page.evaluate("(()=>{const r=document.getElementById('stage').getBoundingClientRect();return [r.width,r.height]})()")
        height = int(round(box[1]))
        height += height % 2
        await page.set_viewport_size({'width': width, 'height': height})
        await page.wait_for_timeout(200)
        cycle = float(await page.evaluate('CYC'))
        if errors:
            print('页面错误', errors, file=sys.stderr, flush=True)
        count = int(round(cycle * fps))
        if limit:
            count = min(count, limit)
        frames_dir.mkdir(parents=True, exist_ok=True)
        stride = 1 if count <= 30 else max(1, fps)
        for index in range(count):
            await page.evaluate(f'renderAt({index / fps})')
            await page.screenshot(path=str(frames_dir / f'f{index:04d}.png'))
            if index % stride == 0 or index + 1 == count:
                print(f'frame {index + 1}/{count}', flush=True)
        still_path = None
        if still is not None:
            still_page = await browser.new_page(viewport={'width': still[0], 'height': 400}, device_scale_factor=1)
            await still_page.goto(html.as_uri() + '?video=1')
            await still_page.wait_for_timeout(600)
            box = await still_page.evaluate("(()=>{const r=document.getElementById('stage').getBoundingClientRect();return [r.width,r.height]})()")
            still_h = int(round(box[1]))
            still_h += still_h % 2
            await still_page.set_viewport_size({'width': still[0], 'height': still_h})
            await still_page.evaluate(f'renderAt({still[1]})')
            still_path = still[2]
            await still_page.screenshot(path=str(still_path))
        await browser.close()
    return cycle, width, height, count, still_path


def encode(frames_dir, mp4, gif, fps, count, cycle, args):
    expected = int(round(cycle * fps))
    crfs = [int(x) for x in args.crf.split(',') if x]
    chosen = None
    for crf in crfs:
        subprocess.run([
            'ffmpeg', '-y', '-loglevel', 'error',
            '-framerate', str(fps), '-i', str(frames_dir / 'f%04d.png'),
            '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', str(crf),
            '-preset', 'slow', '-tune', 'animation', '-movflags', '+faststart', str(mp4),
        ], check=True)
        size = mp4.stat().st_size
        estimate = size if count >= expected else size * (expected / max(1, count))
        print(
            f'mp4 crf {crf}  {size / BYTES_PER_MB:.2f} MB  全长估计 {estimate / BYTES_PER_MB:.2f} MB',
            flush=True,
        )
        chosen = crf
        if estimate <= args.mp4_max_mb * BYTES_PER_MB:
            break
    else:
        print(f'警告：MP4 仍超过 {args.mp4_max_mb} MB', file=sys.stderr, flush=True)

    widths = [int(x) for x in args.gif_widths.split(',') if x]
    colors = [int(x) for x in args.gif_colors.split(',') if x]
    gif_ok = False
    for gw in widths:
        for cols in colors:
            vf = (f'fps={args.gif_fps},scale={gw}:-1:flags=lanczos,split[a][b];'
                  f'[a]palettegen=max_colors={cols}:stats_mode=diff[p];'
                  f'[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle')
            subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(mp4), '-vf', vf, '-loop', '0', str(gif)], check=True)
            size = gif.stat().st_size
            print(f'gif {gw}px {cols} colors  {size / BYTES_PER_MB:.2f} MB', flush=True)
            if size <= args.gif_max_mb * BYTES_PER_MB:
                gif_ok = True
                break
        if gif_ok:
            break
    if not gif_ok:
        print(f'警告：GIF 仍超过 {args.gif_max_mb} MB', file=sys.stderr, flush=True)
    return chosen


def main(argv=None):
    args = parse_args(argv if argv is not None else sys.argv[1:])
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    frames = out_dir / '_frames'
    if frames.exists():
        shutil.rmtree(frames)
    chrome = args.chrome or chrome_path()
    still = None
    png = out_dir / f'{args.name}.png'
    if args.still_time is not None:
        still = (args.still_width, args.still_time, png)
    cycle, width, height, count, still_path = asyncio.run(
        grab(args.html, frames, args.width, args.fps, args.limit_frames, still, chrome)
    )
    print(f'frames {count}  {width}×{height}  cycle {cycle:.3f}s', flush=True)
    mp4 = out_dir / f'{args.name}.mp4'
    gif = out_dir / f'{args.name}.gif'
    encode(frames, mp4, gif, args.fps, count, cycle, args)
    if not args.keep_frames:
        shutil.rmtree(frames, ignore_errors=True)
    print('mp4', mp4, flush=True)
    print('gif', gif, flush=True)
    if still_path:
        print('png', still_path, flush=True)


if __name__ == '__main__':
    main()
