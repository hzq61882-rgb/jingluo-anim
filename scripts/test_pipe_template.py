#!/usr/bin/env python3
"""通用模板的 pipe：合成一份小页面，检查粒子留在直线上，且 t=0 与 t=cycle 相同。"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from record import chrome_path  # noqa: E402


CFG = {
    'title': 'pipe-test',
    'sub': '测试',
    'hdrTitle': 'pipe',
    'hdrSub': '',
    'hdrSub2': '',
    'credit': 'test',
    'assumption': '测试直线，无医学含义。',
    'note': '测试',
    'cycle': 24,
    'W': 200,
    'H': 80,
    'HDR': 24,
    'CAP': 28,
    'layers': [{'id': 'main', 'label': '主流'}],
    'legend': [{'kind': 'pipe', 'label': '管内', 'color': '#ff3b30'}],
    'steps': [{'dur': 24, 'main': '循环', 'sub': '', 'on': ['line']}],
    'items': [
        {
            'id': 'line', 'type': 'pipe', 'layer': 'main', 'color': '火',
            'width': 10, 'pts': [[10, 40], [190, 40]], 'laps': 2, 'amp': 2,
            'count': 16, 'lead': True,
        },
        {
            'id': 'box', 'type': 'pipe', 'layer': 'main', 'color': '水',
            'width': 8, 'closed': True, 'mode': 'loop',
            'pts': [[30, 20], [80, 20], [80, 60], [30, 60]],
            'laps': 1, 'amp': 1.2, 'count': 12, 'lead': True,
        },
    ],
    'labels': [{'x': 100, 'y': 12, 'fs': 12, 't': '標', 'fw': 700}],
}


def main():
    from PIL import Image
    tmp = Path(tempfile.mkdtemp(prefix='jingluo-pipe-'))
    image = tmp / 'blank.jpg'
    Image.new('RGB', (200, 80), (255, 255, 255)).save(image, quality=80)
    cfg = tmp / 'config.json'
    cfg.write_text(json.dumps(CFG, ensure_ascii=False), encoding='utf-8')
    html = tmp / 'pipe.html'
    subprocess.check_call([
        sys.executable, str(ROOT / 'scripts' / 'build.py'),
        '--config', str(cfg), '--image', str(image), '--out', str(html),
        '--skip-fonts',
    ])
    text = html.read_text(encoding='utf-8')
    assert '__FLOW__' not in text
    assert 'JingluoFlow' in text
    assert 'data-pipe' in text
    assert '减弱动效' in text

    from playwright.sync_api import sync_playwright
    chrome = chrome_path()
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=chrome,
            args=['--no-sandbox', '--disable-dev-shm-usage'],
        )
        page = browser.new_page(viewport={'width': 900, 'height': 700})
        page.on('pageerror', lambda err: errors.append(str(err)))
        page.on('console', lambda msg: errors.append(msg.text) if msg.type == 'error' else None)
        page.goto(html.as_uri())
        page.wait_for_timeout(300)
        report = page.evaluate('''() => {
          const sig = () => [...document.querySelectorAll('[data-pipe] circle')]
            .map(c => c.getAttribute('cx')+','+c.getAttribute('cy')+','+c.getAttribute('opacity')).join('|');
          renderAt(0);
          const a = sig();
          const line = [...document.querySelectorAll('[data-pipe="line"] circle.fx-crowd')].map(c => ({
            y: +c.getAttribute('cy'), d: +c.getAttribute('data-dist'), op: +c.getAttribute('opacity')
          }));
          renderAt(CYC);
          const b = sig();
          window.seek(6);
          const scrub = document.getElementById('scrub').value;
          return {same: a === b, n: line.length, line, scrub, hasSeek: typeof window.seek === 'function'};
        }''')
        page.set_viewport_size({'width': 390, 'height': 700})
        page.wait_for_timeout(100)
        box = page.locator('#btnPlay').bounding_box()
        browser.close()
    assert not errors, errors
    assert report['same'], 't=0 与 t=cycle 不一致'
    assert report['n'] >= 12
    assert report['hasSeek']
    assert abs(float(report['scrub']) - 6 / 24) < 0.02, report['scrub']
    for dot in report['line']:
        assert abs(dot['y'] - 40) <= 2.3, dot
        assert dot['d'] <= 2.3, dot
    assert box and box['height'] >= 20 and box['y'] >= 0
    print('pipe template ok', report['n'], 'dots')
    return 0


if __name__ == '__main__':
    sys.exit(main())
