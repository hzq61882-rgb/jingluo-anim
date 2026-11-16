#!/usr/bin/env python3
"""七张增强版：原文件哈希、离线、接缝、粒子不出线、开关、两种宽度、截图。"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from record import chrome_path  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ART = Path('/opt/cursor/artifacts/seven')

CHARTS = [
    ('b31', 'examples/b31-cunguan-siji/寸关尺四季表里图_流动动画.html', True),
    ('b45', 'examples/b45-yulong-bafa/玉龍八法_流动动画.html', True),
    ('b1', 'examples/b1-yulong/玉龍_流动动画.html', True),
    ('b39', 'examples/b39-qi-qijing/氣的循環奇經八脈圖_流动动画.html', True),
    ('b36', 'examples/b36-shenying/神應經穴法圖_流动动画.html', True),
    ('b28', 'examples/b28-wuxing-liujing/五行六经图动画.html', True),
    ('b24', 'examples/b24-bamai-yuanli/把脈的原理動畫.html', False),
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def main():
    from PIL import Image
    from playwright.sync_api import sync_playwright

    ART.mkdir(parents=True, exist_ok=True)
    problems = []
    summary = []
    chrome = chrome_path()
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=chrome,
            args=['--no-sandbox', '--disable-dev-shm-usage', '--force-color-profile=srgb'],
        )
        for key, rel, pipes in CHARTS:
            src = ROOT / rel
            enh = src.with_name(src.stem + '_增强版' + src.suffix)
            backup = src.parent / 'backup' / '2026-11-17-增强前' / src.name
            digest = sha256(src)
            recorded = (backup.parent / 'HASH.txt').read_text(encoding='utf-8').split()[0]
            if digest != recorded or sha256(backup) != digest:
                problems.append(key + ' hash changed')
            errs = []
            reqs = []
            page = browser.new_page(viewport={'width': 1100, 'height': 1400})
            page.on('pageerror', lambda e: errs.append(str(e)))
            page.on('console', lambda m: errs.append(m.text) if m.type == 'error' else None)
            page.on('request', lambda r: reqs.append(r.url))
            page.goto(enh.resolve().as_uri() + '?video=1')
            page.wait_for_timeout(350)
            info = page.evaluate('''() => {
              const vb = document.getElementById('stage').viewBox.baseVal;
              const hdr = (typeof CFG!=='undefined' && CFG.HDR) ? CFG.HDR : 0;
              let x = vb.width/2, y = vb.height/2;
              if (typeof items!=='undefined') {
                const o = items.find(i => i.it && i.it.pts && i.it.pts.length>1 && i.it.type!=='pulse');
                if (o) { const p=o.it.pts[Math.floor(o.it.pts.length/2)]; x=p[0]; y=p[1]+hdr; }
              } else if (CFG.bands && CFG.bands[0] && CFG.bands[0].pts) {
                const p=CFG.bands[0].pts[Math.floor(CFG.bands[0].pts.length/2)];
                x=p[0]; y=p[1]+hdr;
              }
              const times = [0, CYC/3, CYC/2, CYC];
              const audits = [];
              times.forEach(t => { renderAt(t); if (window.JingluoBake) audits.push(JingluoBake.audit()); });
              const sig = () => [...document.querySelectorAll('#stage circle')].slice(0,120)
                .map(c => (c.getAttribute('cx')||'')+','+(c.getAttribute('cy')||'')+','+(c.getAttribute('opacity')||'')).join('|');
              renderAt(0); const a = sig(); renderAt(CYC); const b = sig();
              const taiji = window.taijiAngle ? {
                wood: [taijiAngle('木',0), taijiAngle('木',6)],
                earth: [taijiAngle('土',11), taijiAngle('土',12), taijiAngle('土',14)],
                dir: CFG.TAIJI_DIR, sw: CFG.TU_SWITCH
              } : null;
              const clip = document.getElementById('L_front') ? document.querySelectorAll('#L_front [clip-path], #L_front circle').length : 0;
              return {cyc: CYC, x, y, vw: vb.width, vh: vb.height, audits, same: a===b, taiji, clip, pipes: document.querySelectorAll('[data-pipe]').length};
            }''')
            page.locator('#stage').screenshot(path=str(ART / f'{key}_after.png'))
            im = Image.open(ART / f'{key}_after.png')
            sx, sy = im.width / info['vw'], im.height / info['vh']
            rad = 90
            box = (
                max(0, int((info['x'] - rad) * sx)),
                max(0, int((info['y'] - rad) * sy)),
                min(im.width, int((info['x'] + rad) * sx)),
                min(im.height, int((info['y'] + rad) * sy)),
            )
            if box[2] > box[0] + 8 and box[3] > box[1] + 8:
                im.crop(box).save(ART / f'{key}_closeup.png')
            old = browser.new_page(viewport={'width': 1100, 'height': 1400})
            old.goto(src.resolve().as_uri() + '?video=1')
            old.wait_for_timeout(250)
            old.evaluate('renderAt(CYC/3)')
            old.locator('#stage').screenshot(path=str(ART / f'{key}_before.png'))
            old.close()
            live = browser.new_page(viewport={'width': 1100, 'height': 1200})
            live.goto(enh.resolve().as_uri())
            live.wait_for_timeout(250)
            toggles = live.evaluate('''() => {
              const out = {};
              document.querySelectorAll('#toggles input').forEach((box, i) => {
                const g = document.querySelector('#layers > g, #L_flow');
                box.click();
                out['layer'+i] = box.checked;
                box.click();
              });
              const q = document.getElementById('tgQuiet');
              q.click(); out.quiet = document.body.classList.contains('quiet'); q.click();
              const c = document.getElementById('tgContrast');
              c.click(); out.hc = document.body.classList.contains('hc'); c.click();
              document.getElementById('btnPlay').click();
              const t1 = Tm;
              return {out, t1};
            }''')
            live.wait_for_timeout(300)
            t2 = live.evaluate('Tm')
            live.evaluate('window.seek(CYC/4)')
            seek = live.evaluate('JingluoFlow.wrap(Tm, CYC)')
            live.set_viewport_size({'width': 390, 'height': 800})
            small = live.evaluate('''() => {
              const b = document.getElementById('btnPlay').getBoundingClientRect();
              return {h:b.height, scroll: document.documentElement.scrollWidth - document.documentElement.clientWidth};
            }''')
            live.set_viewport_size({'width': 1280, 'height': 900})
            wide = live.evaluate('''() => document.getElementById('btnPlay').getBoundingClientRect().height''')
            live.close()
            page.close()
            net = [u for u in reqs if not (u.startswith('file:') or u.startswith('data:'))]
            row = {
                'id': key, 'cyc': info['cyc'], 'same': info['same'], 'pipes': info['pipes'],
                'audits': info['audits'], 'taiji': info['taiji'], 'clip': info['clip'],
                'pause_delta': t2 - toggles['t1'], 'seek': seek, 'small': small, 'wide': wide,
                'bytes': enh.stat().st_size, 'sha': digest,
            }
            summary.append(row)
            if errs:
                problems.append(key + ' console ' + ' | '.join(errs[:3]))
            if net:
                problems.append(key + ' net ' + ' '.join(net[:3]))
            if not info['same']:
                problems.append(key + ' seam')
            if pipes:
                if not info['audits'] or any(a['outside'] for a in info['audits']):
                    problems.append(key + ' outside ' + json.dumps(info['audits']))
                if info['pipes'] < 1:
                    problems.append(key + ' no pipes')
            else:
                if info['cyc'] != 60 or info['clip'] < 1:
                    problems.append(key + f" b24 cyc/clip {info['cyc']} {info['clip']}")
            if info.get('taiji'):
                w0, w6 = info['taiji']['wood']
                if not (w6 > w0):
                    problems.append(key + ' wood direction ' + str(info['taiji']['wood']))
                e11, e12, e14 = info['taiji']['earth']
                # 土在 12 秒换向：12→14 的增量应小于 11→12 的同向延续，或符号反过来
                if abs((e14 - e12) - (e12 - e11) * 2) < 1:
                    problems.append(key + ' earth did not turn ' + str(info['taiji']['earth']))
            if abs((t2 - toggles['t1'])) > 1e-6:
                problems.append(key + ' pause moved')
            if abs(seek - info['cyc'] / 4) > 0.05:
                problems.append(key + f' seek {seek}')
            if small['h'] < 30 or small['scroll'] > 8:
                problems.append(key + f' small {small}')
            if wide < 20:
                problems.append(key + ' wide')
            if not toggles['out'].get('quiet') or not toggles['out'].get('hc'):
                problems.append(key + ' toggles ' + str(toggles['out']))
            print(key, 'ok' if key not in ''.join(problems) else 'CHECK', 'cyc', info['cyc'], 'pipes', info['pipes'])
        browser.close()
    (ART / 'summary.json').write_text(json.dumps({'problems': problems, 'rows': summary}, ensure_ascii=False, indent=2), encoding='utf-8')
    if problems:
        print('\n'.join(problems))
        raise SystemExit(1)
    print('seven ok')


if __name__ == '__main__':
    main()
