#!/usr/bin/env python3
"""逐环旋转文字版的对照测试。只读页面，不改其他图。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from record import chrome_path  # noqa: E402

HTML = Path('examples/b31-cunguan-siji/寸关尺四季表里图_逐环旋转文字版.html').resolve()
OUT = Path('/tmp/b31spin')
OUT.mkdir(exist_ok=True)


def angle_of(transform: str) -> float:
    if 'rotate(' not in transform:
        return 0.0
    return float(transform.split('rotate(')[1].split()[0])


def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=chrome_path(), args=['--no-sandbox'])
        page = browser.new_page(viewport={'width': 1280, 'height': 900}, device_scale_factor=2)
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
        page.goto(HTML.as_uri())
        page.wait_for_timeout(400)
        page.evaluate('''() => {
          document.body.classList.remove('quiet');
          document.getElementById('tgQuiet').checked = false;
          document.getElementById('tgScan').checked = false;
          document.getElementById('tgText').checked = true;
          document.getElementById('tgFlow').checked = true;
          window.seek(0);
        }''')
        page.wait_for_timeout(200)

        def state():
            return page.evaluate('() => window.spinState()')

        box = page.locator('#stage').bounding_box()
        scale = box['width'] / 809

        def crop(name, sx, sy, rw=36, rh=36):
            page.screenshot(path=str(OUT / name), clip={
                'x': box['x'] + (sx - rw / 2) * scale,
                'y': box['y'] + (sy - rh / 2) * scale,
                'width': rw * scale,
                'height': rh * scale,
            })

        # 环 8 右侧、太极、少府、阳谷、阳、阴、一个序号圆
        spots = {
            'ring8': (485, 296),
            'ring2': (443, 296),
            'taiji': (404, 296),
            'shaofu': (749, 428),
            'yanggu': (672, 485),
            'yang': (657, 527),
            'yin': (765, 524),
            'node0': (518.5, 97.7),
            'summer': (700, 460),
        }
        s0 = state()
        for key, (x, y) in spots.items():
            rw = 150 if key == 'summer' else (70 if key == 'taiji' else 40)
            crop(f't0_{key}.png', x, y, rw, rw if key != 'summer' else 120)
        page.evaluate('() => window.seek(5)')
        s5 = state()
        for key, (x, y) in spots.items():
            rw = 150 if key == 'summer' else (70 if key == 'taiji' else 40)
            crop(f't5_{key}.png', x, y, rw, rw if key != 'summer' else 120)

        def diff(a, b):
            ia = np.array(Image.open(OUT / a).convert('RGB')).astype(int)
            ib = np.array(Image.open(OUT / b).convert('RGB')).astype(int)
            if ia.shape != ib.shape:
                return -1
            return int(np.abs(ia - ib).sum(axis=2).mean() > 8).sum() if False else int((np.abs(ia - ib).sum(axis=2) > 18).sum())

        pixel = {k: diff(f't0_{k}.png', f't5_{k}.png') for k in spots}
        page.locator('#stage').screenshot(path=str(OUT / 'stage_t5.png'))
        page.evaluate('() => window.seek(0)')
        page.locator('#stage').screenshot(path=str(OUT / 'stage_t0.png'))
        # 暂停时角度不动
        page.evaluate('() => { window.seek(5); document.getElementById("btnPlay").click(); }')
        frozen = state()
        scrub1 = page.evaluate('() => document.getElementById("scrub").value')
        page.wait_for_timeout(500)
        frozen2 = state()
        scrub2 = page.evaluate('() => document.getElementById("scrub").value')
        # 改速度不跳
        page.evaluate('() => document.getElementById("btnPlay").click()')
        before_speed = page.evaluate('() => document.getElementById("scrub").value')
        page.evaluate('''() => {
          const el = document.getElementById("spMain");
          el.value = "2.4";
          el.dispatchEvent(new Event("input"));
        }''')
        after_speed = page.evaluate('() => document.getElementById("scrub").value')
        page.evaluate('''() => {
          if (document.getElementById("btnPlay").textContent.indexOf("播放") < 0) document.getElementById("btnPlay").click();
          window.seek(0);
        }''')
        at0 = state()
        page.evaluate('() => window.seek(24)')
        at24 = state()
        cover = page.evaluate('() => window.coverage()')
        page.evaluate('() => window.seek(0)')
        # 原图对照藏起新字和旋转层
        page.evaluate('''() => {
          const el = document.getElementById("tgScan");
          el.checked = true;
          el.dispatchEvent(new Event("change"));
        }''')
        scan = page.evaluate('''() => ({
          spin: document.getElementById("spin").style.display,
          labels: document.getElementById("labels").style.display,
          flows: document.getElementById("flows").style.display,
          raw: document.getElementById("raw").style.display,
          bg: document.getElementById("bg").style.display
        })''')
        # 视口
        overflows = {}
        for width in (390, 1280):
            page.set_viewport_size({'width': width, 'height': 800})
            page.wait_for_timeout(200)
            overflows[str(width)] = page.evaluate('''() => ({
              scroll: document.documentElement.scrollWidth,
              inner: window.innerWidth,
              stage: document.getElementById("stage").getBoundingClientRect().width
            })''')
            page.screenshot(path=str(OUT / f'w{width}.png'), full_page=False)
        browser.close()

    rings0 = {r['id']: angle_of(r['transform']) for r in s0 if r['kind'] == 'ring'}
    rings5 = {r['id']: angle_of(r['transform']) for r in s5 if r['kind'] == 'ring'}
    dots0 = {r['id']: angle_of(r['transform']) for r in s0 if r['kind'] in ('dot', 'named', 'taiji')}
    dots5 = {r['id']: angle_of(r['transform']) for r in s5 if r['kind'] in ('dot', 'named', 'taiji')}
    report = {
        'console_errors': errors,
        'ring_angles_t0': rings0,
        'ring_angles_t5': rings5,
        'ring_angles_unique_at_t5': len(set(round(v, 2) for v in rings5.values())) == len(rings5),
        'every_ring_moved': all(abs(rings5[k] - rings0[k]) > 1 for k in rings0),
        'every_circle_arc_moved': all(abs(dots5[k] - dots0[k]) > 1 for k in dots0),
        'circle_arc_count': len(dots0),
        'pixel_changed': pixel,
        'pause_scrub': [scrub1, scrub2],
        'pause_angles_held': frozen == frozen2,
        'speed_scrub_before_after': [before_speed, after_speed],
        't0_t24_angles_match': at0 == at24,
        'coverage': cover,
        'scan': scan,
        'overflows': overflows,
    }
    Path(OUT / 'test.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: report[k] for k in report if k not in ('ring_angles_t0', 'ring_angles_t5')}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
