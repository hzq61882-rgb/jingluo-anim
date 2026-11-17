#!/usr/bin/env python3
"""本版全图重绘点亮版的验收。只读这一页，结果写到 /tmp/b31redraw-pass。"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from record import chrome_path  # noqa: E402

HTML = Path('examples/b31-cunguan-siji/寸关尺四季表里图_全图重绘点亮版.html').resolve()
OUT = Path('/tmp/b31redraw-pass')
OUT.mkdir(exist_ok=True)


def angle_of(transform: str) -> float:
    if not transform or 'rotate(' not in transform:
        return 0.0
    return float(transform.split('rotate(')[1].split()[0])


def main():
    raw = HTML.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    errors = []
    requests = []
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=chrome_path(), args=['--no-sandbox'])
        page = browser.new_page(viewport={'width': 1280, 'height': 900})
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
        page.on('request', lambda r: requests.append(r.url))
        page.goto(HTML.as_uri())
        page.wait_for_timeout(400)
        page.evaluate('''() => {
          document.getElementById("btnPlay").click();
          window.seek(0);
        }''')

        def spins():
            return page.evaluate('''() => [...document.querySelectorAll("[data-spin]")].map(el => ({
              id: el.id, kind: el.getAttribute("data-kind"), transform: el.getAttribute("transform") || ""
            }))''')

        counts = page.evaluate('''() => ({
          bars: document.querySelectorAll('#bars rect').length,
          spec: document.querySelectorAll('[data-kind="spec"]').length,
          rings: document.querySelectorAll('[data-kind="ring"]').length,
          images: document.querySelectorAll('image').length,
          labels: document.querySelectorAll('#labels text').length
        })''')
        texts = page.evaluate('''() => [...document.querySelectorAll('#labels text, #geom text')].map(el => el.textContent)''')
        need = ['支沟', '劳宫', '三里', '经渠', '大敦', '二间', '三间', '厉兑', '隐白', '商阳', '足通谷', '阴谷', '阳谷', '少府', '丰隆']
        present = {t: texts.count(t) for t in need}
        present['足'] = texts.count('足')
        present['阳'] = texts.count('阳')
        present['阴'] = texts.count('阴')
        present['太'] = texts.count('太')
        present['白'] = texts.count('白')

        s0 = spins()
        page.evaluate('() => window.seek(5)')
        s5 = spins()
        by0 = {r['id']: r for r in s0}
        by5 = {r['id']: r for r in s5}
        rings0 = {i: angle_of(by0[i]['transform']) for i in by0 if by0[i]['kind'] == 'ring'}
        rings5 = {i: angle_of(by5[i]['transform']) for i in rings0}
        spec_ids = [i for i in by0 if by0[i]['kind'] == 'spec']
        spec_moved = []
        spec_still = []
        for i in spec_ids:
            a0, a5 = angle_of(by0[i]['transform']), angle_of(by5[i]['transform'])
            (spec_moved if abs(a5 - a0) > 1 else spec_still).append(i)

        page.evaluate('() => window.seek(5)')
        scrub_before = page.evaluate('() => document.getElementById("scrub").value')
        page.wait_for_timeout(400)
        scrub_held = page.evaluate('() => document.getElementById("scrub").value')
        held0 = spins()
        page.wait_for_timeout(400)
        held1 = spins()
        pause_same = [(a['id'], a['transform']) for a in held0] == [(a['id'], a['transform']) for a in held1]

        page.evaluate('''() => {
          const el = document.getElementById("spMain");
          el.value = "2.4";
          el.dispatchEvent(new Event("input"));
        }''')
        scrub_after_speed = page.evaluate('() => document.getElementById("scrub").value')
        width0 = page.evaluate('() => document.getElementById("stage").style.width')
        page.evaluate('() => document.getElementById("zoomIn").click()')
        width1 = page.evaluate('() => document.getElementById("stage").style.width')
        page.evaluate('() => document.getElementById("zoomReset").click()')

        page.evaluate('() => window.seek(0)')
        at0 = [(a['id'], a['transform']) for a in spins()]
        page.evaluate('''() => {
          const svg = document.getElementById("stage");
          svg.style.width = "809px";
          svg.style.height = "674px";
        }''')
        box = page.locator('#stage').bounding_box()
        clip = {'x': box['x'], 'y': box['y'], 'width': 809, 'height': 596}
        page.screenshot(path=str(OUT / 't0.png'), clip=clip)
        page.evaluate('() => window.seek(24)')
        at24 = [(a['id'], a['transform']) for a in spins()]
        page.screenshot(path=str(OUT / 't24.png'), clip=clip)
        a = np.array(Image.open(OUT / 't0.png').convert('RGB')).astype(int)
        b = np.array(Image.open(OUT / 't24.png').convert('RGB')).astype(int)
        t0_t24_mean = float(np.abs(a - b).mean()) if a.shape == b.shape else -1

        page.evaluate('() => window.seek(0)')
        page.evaluate('''() => {
          const el = document.getElementById("tgScan");
          el.checked = true;
          el.dispatchEvent(new Event("change"));
        }''')
        scan = page.evaluate('''() => ({
          geom: document.getElementById("geom") && document.getElementById("geom").style.display,
          kept: document.getElementById("kept") && document.getElementById("kept").style.display,
          spin: document.getElementById("spin").style.display,
          labels: document.getElementById("labels").style.display,
          flows: document.getElementById("flows").style.display,
          raw: document.getElementById("raw").style.display,
          bg: document.getElementById("bg").style.display
        })''')
        page.evaluate('''() => {
          const el = document.getElementById("tgScan");
          el.checked = false;
          el.dispatchEvent(new Event("change"));
        }''')

        overflows = {}
        for width in (390, 1280):
            page.set_viewport_size({'width': width, 'height': 800})
            page.wait_for_timeout(150)
            overflows[str(width)] = page.evaluate('''() => ({
              scroll: document.documentElement.scrollWidth,
              inner: window.innerWidth,
              stage: document.getElementById("stage").getBoundingClientRect().width
            })''')
        browser.close()

    http_reqs = [u for u in requests if u.startswith('http://') or u.startswith('https://')]
    report = {
        'commit': commit,
        'html': HTML.name,
        'html_sha256': sha,
        'html_bytes': len(raw),
        'counts': counts,
        'restored_text_counts': present,
        'ring_count': len(rings0),
        'ring_angles_unique_at_t5': len({round(v, 2) for v in rings5.values()}) == len(rings5) and len(rings5) == 9,
        'every_ring_moved': all(abs(rings5[k] - rings0[k]) > 1 for k in rings0),
        'spec_circle_count': len(spec_ids),
        'spec_circles_moved': len(spec_moved),
        'spec_circles_not_moved': spec_still,
        'pause_scrub': [scrub_before, scrub_held],
        'pause_angles_held': pause_same and scrub_before == scrub_held,
        'speed_scrub_before_after': [scrub_before, scrub_after_speed],
        'speed_did_not_jump': scrub_before == scrub_after_speed,
        'zoom_width_before_after': [width0, width1],
        'zoom_changed': width0 != width1,
        't0_t24_transforms_match': at0 == at24,
        't0_t24_pixel_mean_abs': round(t0_t24_mean, 4),
        'scan': scan,
        'overflows': overflows,
        'overflow_ok': all(v['scroll'] <= v['inner'] + 1 for v in overflows.values()),
        'http_requests': http_reqs,
        'offline_no_http': len(http_reqs) == 0,
        'console_errors': errors,
        'bars_are_72': counts['bars'] == 72,
    }
    (OUT / 'test.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: report[k] for k in (
        'commit', 'html_sha256', 'counts', 'ring_angles_unique_at_t5', 'every_ring_moved',
        'spec_circle_count', 'spec_circles_moved', 'spec_circles_not_moved',
        'pause_angles_held', 'speed_did_not_jump', 'zoom_changed',
        't0_t24_transforms_match', 't0_t24_pixel_mean_abs', 'overflow_ok',
        'offline_no_http', 'console_errors', 'bars_are_72', 'scan',
    )}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
