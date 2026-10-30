#!/usr/bin/env python3
"""检查循环接缝。

HTML：用 renderAt(0) 和 renderAt(CYC) 各截一张图。周期整除时两张应当几乎相同
（虚线位移、闪烁、品牌条的周期都要能整除 CYC）。

MP4：抽出第 0 帧和最后一帧，报告平均绝对差。最后一帧是回绕前的一帧，
差一个运动步长是正常的；差得很大说明接缝处会跳。

  python scripts/verify_loop.py --html animation.html
  python scripts/verify_loop.py --mp4 out.mp4 --cycle 24
"""
from __future__ import annotations

import argparse
import asyncio
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from record import chrome_path  # noqa: E402


def mae(a_path, b_path):
    try:
        import numpy as np
        from PIL import Image
    except ImportError:
        proc = subprocess.run(
            ['ffmpeg', '-i', str(a_path), '-i', str(b_path), '-lavfi', 'psnr', '-f', 'null', '-'],
            capture_output=True, text=True,
        )
        text = proc.stderr
        print(text.strip().splitlines()[-1] if text.strip() else 'psnr 无输出')
        return None
    a = np.asarray(Image.open(a_path).convert('RGB'), dtype=np.float32)
    b = np.asarray(Image.open(b_path).convert('RGB'), dtype=np.float32)
    if a.shape != b.shape:
        raise SystemExit(f'两帧尺寸不同：{a.shape} vs {b.shape}')
    return float(np.mean(np.abs(a - b)))


async def shoot_pair(html, out_dir, width, chrome):
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise SystemExit('检查 HTML 需要 playwright：pip install playwright') from exc
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
        await page.wait_for_timeout(600)
        box = await page.evaluate("(()=>{const r=document.getElementById('stage').getBoundingClientRect();return [r.width,r.height]})()")
        height = int(round(box[1]))
        height += height % 2
        await page.set_viewport_size({'width': width, 'height': height})
        cycle = float(await page.evaluate('CYC'))
        await page.evaluate('renderAt(0)')
        start = out_dir / 'seam_0.png'
        await page.screenshot(path=str(start))
        await page.evaluate(f'renderAt({cycle})')
        end = out_dir / 'seam_cycle.png'
        await page.screenshot(path=str(end))
        await browser.close()
    return cycle, start, end, errors


def check_mp4(path, cycle, tmp):
    proc = subprocess.run(
        ['ffprobe', '-v', 'error', '-select_streams', 'v:0',
         '-show_entries', 'stream=width,height,nb_frames,r_frame_rate,duration',
         '-of', 'default=nw=1', str(path)],
        check=True, capture_output=True, text=True,
    )
    info = {}
    for line in proc.stdout.splitlines():
        if '=' in line:
            k, v = line.split('=', 1)
            info[k] = v
    print('mp4', info)
    height = int(info.get('height') or 0)
    if height % 2:
        print(f'警告：高度 {height} 是奇数，yuv420p 会补行')
    if cycle and info.get('duration'):
        duration = float(info['duration'])
        if abs(duration - cycle) > 0.08:
            print(f'警告：片长 {duration:.3f}s 与 cycle {cycle:.3f}s 不一致')
        else:
            print(f'片长 {duration:.3f}s 对齐 cycle {cycle:.3f}s')
    first = tmp / 'f0.png'
    last = tmp / 'flast.png'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(path), '-frames:v', '1', str(first)], check=True)
    nframes = info.get('nb_frames')
    if nframes and nframes.isdigit() and int(nframes) > 1:
        subprocess.run([
            'ffmpeg', '-y', '-loglevel', 'error', '-i', str(path),
            '-vf', f'select=eq(n\\,{int(nframes) - 1})', '-vsync', 'vfr',
            '-frames:v', '1', str(last),
        ], check=True)
    else:
        subprocess.run([
            'ffmpeg', '-y', '-loglevel', 'error', '-sseof', '-0.04',
            '-i', str(path), '-frames:v', '1', str(last),
        ], check=True)
    if not last.is_file():
        raise SystemExit('抽不出末帧')
    score = mae(first, last)
    if score is None:
        return 0
    print(f'首帧与末帧平均绝对差 {score:.2f}（末帧是回绕前一帧，小步差正常，突然很大就是接缝跳变）')
    if score > 40:
        print('警告：首尾差偏大，打开两帧看是运动一步还是图案跳变')
        return 1
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description='检查动画循环接缝')
    parser.add_argument('--html')
    parser.add_argument('--mp4')
    parser.add_argument('--cycle', type=float, default=None, help='期望片长（秒），与 MP4 对照')
    parser.add_argument('--width', type=int, default=900)
    parser.add_argument('--chrome', default=None)
    parser.add_argument('--out-dir', default=None, help='留下 seam_0.png 与 seam_cycle.png 的目录')
    parser.add_argument('--mae-max', type=float, default=2.0, help='renderAt(0) 与 renderAt(CYC) 允许的平均绝对差')
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    if not args.html and not args.mp4:
        parser.error('至少给 --html 或 --mp4')
    code = 0
    if args.html:
        if args.out_dir:
            out = Path(args.out_dir)
            out.mkdir(parents=True, exist_ok=True)
            cycle, start, end, errors = asyncio.run(shoot_pair(args.html, out, args.width, args.chrome or chrome_path()))
            score = mae(start, end)
        else:
            with tempfile.TemporaryDirectory() as tmp:
                out = Path(tmp)
                cycle, start, end, errors = asyncio.run(shoot_pair(args.html, out, args.width, args.chrome or chrome_path()))
                score = mae(start, end)
        if errors:
            print('页面错误', errors)
            code = 1
        print(f'HTML cycle {cycle:.3f}s  renderAt(0) 与 renderAt(cycle) 平均绝对差 {score}')
        if score is None:
            code = 1
        elif score > args.mae_max:
            print(f'接缝未对齐（>{args.mae_max}）。检查虚线周期、闪烁周期是否整除 cycle。')
            code = 1
        else:
            print('HTML 接缝对齐')
    if args.mp4:
        with tempfile.TemporaryDirectory() as tmp:
            code = max(code, check_mp4(args.mp4, args.cycle, Path(tmp)))
    return code


if __name__ == '__main__':
    sys.exit(main())
