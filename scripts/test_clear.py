#!/usr/bin/env python3
"""七张清晰重绘：原哈希、每条已登记线有动画、接缝、离线、宽度、截图。"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from record import chrome_path  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ART = Path('/opt/cursor/artifacts/clear')
CHARTS = [
    ('b31', 'examples/b31-cunguan-siji/寸关尺四季表里图_流动动画.html'),
    ('b45', 'examples/b45-yulong-bafa/玉龍八法_流动动画.html'),
    ('b1', 'examples/b1-yulong/玉龍_流动动画.html'),
    ('b39', 'examples/b39-qi-qijing/氣的循環奇經八脈圖_流动动画.html'),
    ('b36', 'examples/b36-shenying/神應經穴法圖_流动动画.html'),
    ('b28', 'examples/b28-wuxing-liujing/五行六经图动画.html'),
    ('b24', 'examples/b24-bamai-yuanli/把脈的原理動畫.html'),
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
    rows = []
    overlaps = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=chrome_path(), args=['--no-sandbox', '--disable-dev-shm-usage'])
        for key, rel in CHARTS:
            src = ROOT / rel
            enh = src.with_name(src.stem + '_清晰重绘版.html')
            backup = src.parent / 'backup' / '2026-11-17-清晰重绘前' / 'HASH.txt'
            digest = sha256(src)
            if digest not in backup.read_text(encoding='utf-8'):
                problems.append(key + ' hash')
            errs, reqs = [], []
            page = browser.new_page(viewport={'width': 1100, 'height': 1400})
            page.on('pageerror', lambda e: errs.append(str(e)))
            page.on('console', lambda m: errs.append(m.text) if m.type == 'error' else None)
            page.on('request', lambda r: reqs.append(r.url))
            page.goto(enh.resolve().as_uri() + '?video=1')
            page.wait_for_timeout(400)
            info = page.evaluate('''() => {
              const cov = coverage();
              const ids = [...document.querySelectorAll('[data-flow]')].map(el => el.getAttribute('data-flow'));
              const moved = {};
              renderAt(0.2);
              ids.forEach(id => {
                const g = document.querySelector('[data-flow="'+id+'"]');
                const c = g.querySelector('.fx-crowd, .fx-lead') || g;
                moved[id] = (c.getAttribute('cx')||'') + '|' + (c.getAttribute('stroke-dashoffset')||'');
              });
              renderAt(1.4);
              let still = [];
              ids.forEach(id => {
                const g = document.querySelector('[data-flow="'+id+'"]');
                const c = g.querySelector('.fx-crowd, .fx-lead') || g;
                const now = (c.getAttribute('cx')||'') + '|' + (c.getAttribute('stroke-dashoffset')||'');
                if (now === moved[id]) still.push(id);
              });
              const sig = () => [...document.querySelectorAll('.fx-crowd,.fx-lead')].map(c => c.getAttribute('cx')+','+c.getAttribute('cy')).join('|');
              renderAt(0); const a = sig(); renderAt(CYC); const b = sig();
              const scan = getComputedStyle(document.getElementById('bg')).display;
              const boxes = [...document.querySelectorAll('[data-label]')].map(t => {
                const r = t.getBBox(); return {t:t.textContent, x:r.x, y:r.y, w:r.width, h:r.height};
              });
              const hits = [];
              for (let i=0;i<boxes.length;i++) for (let j=i+1;j<boxes.length;j++) {
                const A=boxes[i], B=boxes[j];
                const x=Math.max(0, Math.min(A.x+A.w,B.x+B.w)-Math.max(A.x,B.x));
                const y=Math.max(0, Math.min(A.y+A.h,B.y+B.h)-Math.max(A.y,B.y));
                const inter=x*y, small=Math.min(A.w*A.h, B.w*B.h);
                if (small>0 && inter/small>0.45) hits.push(A.t+'/'+B.t);
              }
              let taiji=null;
              if (typeof CFG!=='undefined' && CFG.taiji) {
                taiji={wood:[taijiAngle('木',0),taijiAngle('木',6)], earth:[taijiAngle('土',11),taijiAngle('土',12),taijiAngle('土',14)], sw:CFG.taiji.switchAt};
              }
              return {cov, still, same:a===b, scan, hits:hits.slice(0,12), hitN:hits.length, cyc:CYC, taiji};
            }''')
            page.locator('#stage').screenshot(path=str(ART / f'{key}_full.png'))
            im = Image.open(ART / f'{key}_full.png')
            # dense center crop
            w, h = im.size
            im.crop((int(w*0.28), int(h*0.22), int(w*0.72), int(h*0.62))).save(ART / f'{key}_dense.png')
            page.close()
            live = browser.new_page(viewport={'width': 390, 'height': 800})
            live.goto(enh.resolve().as_uri())
            live.wait_for_timeout(200)
            live.evaluate("document.getElementById('btnPlay').click()")
            t1 = live.evaluate('Tm')
            live.wait_for_timeout(250)
            t2 = live.evaluate('Tm')
            live.evaluate('seek(CYC/5)')
            seek = live.evaluate('JingluoFlow.wrap(Tm, CYC)')
            small = live.evaluate('''() => {
              const s=document.getElementById('stage');
              return {min: parseFloat(getComputedStyle(s).minWidth), scroll: document.getElementById('view').scrollWidth > document.getElementById('view').clientWidth};
            }''')
            live.set_viewport_size({'width': 1280, 'height': 900})
            wide = live.evaluate('''() => document.getElementById('btnPlay').getBoundingClientRect().height''')
            live.close()
            net = [u for u in reqs if not (u.startswith('file:') or u.startswith('data:'))]
            row = {'id': key, 'cyc': info['cyc'], 'still': info['still'], 'same': info['same'], 'scan': info['scan'], 'cov': info['cov'], 'hitN': info['hitN'], 'hits': info['hits'], 'seek': seek, 'pause': t2-t1, 'small': small, 'taiji': info['taiji']}
            rows.append(row)
            overlaps[key] = info['hits']
            if errs: problems.append(key+' err '+errs[0][:180])
            if net: problems.append(key+' net')
            if info['scan'] != 'none': problems.append(key+' scan visible')
            if not info['same']: problems.append(key+' seam')
            if info['still']: problems.append(key+' still '+','.join(info['still'][:8]))
            if info['cov']['flowsN'] != info['cov']['expected']: problems.append(key+' count')
            if info['cov']['outside']: problems.append(key+' outside')
            if abs(t2-t1) > 1e-4: problems.append(key+' pause')
            if abs(seek - info['cyc']/5) > 0.08: problems.append(key+f' seek {seek}')
            if not small['scroll']: problems.append(key+' narrow did not keep a scrollable stage')
            if wide < 20: problems.append(key+' wide')
            if info.get('taiji'):
                if not (info['taiji']['wood'][1] > info['taiji']['wood'][0]): problems.append(key+' wood')
                e11,e12,e14=info['taiji']['earth']
                if e14 >= e12: problems.append(key+' earth turn')
            print(key, 'flows', info['cov']['flowsN'], 'still', len(info['still']), 'hits', info['hitN'])
        browser.close()
    (ART/'summary.json').write_text(json.dumps({'problems':problems,'rows':rows}, ensure_ascii=False, indent=2), encoding='utf-8')
    if problems:
        print('\n'.join(problems))
        raise SystemExit(1)
    print('clear ok')


if __name__ == '__main__':
    main()
