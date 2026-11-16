#!/usr/bin/env python3
"""打开 B/4 圆环增强版：38 圆、图层开关、暂停、调速、seek、video=1、接缝、粒子不出管道。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from record import chrome_path  # noqa: E402

HTML = ROOT / 'examples' / 'b4-maizhen' / '经络流注动画_圆环版_增强版.html'
OLD = ROOT / 'examples' / 'b4-maizhen' / 'backup' / '2026-11-16-圆环版' / '经络流注动画_圆环版.html'
ART = Path('/opt/cursor/artifacts')

EVAL_AUDIT = r'''
(t) => {
  renderAt(t);
  const a = JingluoRing.audit();
  a.t = t;
  return a;
}
'''


def main():
    from PIL import Image
    from playwright.sync_api import sync_playwright

    assert HTML.is_file(), HTML
    text = HTML.read_text(encoding='utf-8')
    assert 'data:image/jpeg;base64,' in text
    assert '君宝学中医' not in text
    assert '增强版' in text
    assert HTML.stat().st_size < 10_000_000
    assert '往返' in text and '疗效' in text

    chrome = chrome_path()
    errors = []
    requests = []
    ART.mkdir(parents=True, exist_ok=True)

    def shoot(page, path):
        page.locator('#stage').screenshot(path=str(path))

    def crop_chi(src, dest):
        im = Image.open(src)
        w, h = im.size
        sx, sy = w / 595, h / 900
        cx, cy, rad = 275, 243, 78
        box = (
            max(0, int((cx - rad) * sx)),
            max(0, int((cy - rad) * sy)),
            min(w, int((cx + rad) * sx)),
            min(h, int((cy + rad) * sy)),
        )
        im.crop(box).save(dest)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=chrome,
            args=['--no-sandbox', '--disable-dev-shm-usage', '--force-color-profile=srgb'],
        )
        page = browser.new_page(viewport={'width': 980, 'height': 1400})
        page.on('pageerror', lambda err: errors.append('page:' + str(err)))
        page.on('console', lambda msg: errors.append('console:' + msg.text) if msg.type == 'error' else None)
        page.on('request', lambda req: requests.append(req.url))
        page.goto(HTML.as_uri() + '?video=1')
        page.wait_for_timeout(400)
        video = page.evaluate('''() => ({
          video: document.body.classList.contains('video'),
          h1: getComputedStyle(document.querySelector('h1')).display,
          credit: document.getElementById('capCredit').textContent,
          cyc: CYC,
          nRing: document.querySelectorAll('[data-ring]').length,
          nObj: ringObjs.length,
          nCir: CIR.length
        })''')
        seams = page.evaluate('''() => {
          const sig = () => [...document.querySelectorAll('.pipe-swarm circle')]
            .map(c => [c.getAttribute('cx'), c.getAttribute('cy'), c.getAttribute('opacity')].join(',')).join('|');
          renderAt(0);
          const a = sig();
          renderAt(CYC);
          const b = sig();
          renderAt(23.95);
          const ring = document.querySelector('[data-ring="0"] circle');
          const c = ringObjs[0].c;
          const p1 = {x:+ring.getAttribute('cx'), y:+ring.getAttribute('cy')};
          renderAt(0.05);
          const p2 = {x:+ring.getAttribute('cx'), y:+ring.getAttribute('cy')};
          const ang = (p) => Math.atan2(p.y - c.y, p.x - c.x);
          let d = ang(p2) - ang(p1);
          while (d > Math.PI) d -= Math.PI * 2;
          while (d < -Math.PI) d += Math.PI * 2;
          return {same: a === b && a.length > 100, dang: d, n: a.split('|').length};
        }''')
        audits = [page.evaluate(EVAL_AUDIT, t) for t in (0, 6, 12, 18, 23.5)]
        page.evaluate('''() => { document.body.classList.remove('quiet'); renderAt(6); }''')
        after = ART / 'b4_after_t6.png'
        shoot(page, after)
        crop_chi(after, ART / 'b4_after_closeup_chi.png')

        old = browser.new_page(viewport={'width': 980, 'height': 1400})
        old.goto(OLD.as_uri() + '?video=1')
        old.wait_for_timeout(400)
        old.evaluate('renderAt(6)')
        before = ART / 'b4_before_t6.png'
        old.locator('#stage').screenshot(path=str(before))
        crop_chi(before, ART / 'b4_before_closeup_chi.png')
        old.close()

        live = browser.new_page(viewport={'width': 1100, 'height': 1500})
        live_err = []
        live.on('pageerror', lambda err: live_err.append(str(err)))
        live.on('console', lambda msg: live_err.append(msg.text) if msg.type == 'error' else None)
        live.goto(HTML.as_uri())
        live.wait_for_timeout(300)
        toggles = live.evaluate('''() => {
          const map = {
            tg_mer: 'L_mer', tg_arc: 'L_arc', tg_wx: 'L_wx', tg_qj: 'L_qj', tg_yy: 'L_yy',
            tg_ring: 'L_ring', tg_rim: 'L_rim', tg_rad: 'L_rad', tg_blk: 'L_blk'
          };
          const out = {};
          for (const id in map) {
            const box = document.getElementById(id);
            box.click();
            out[id] = document.getElementById(map[id]).style.display;
            box.click();
          }
          document.getElementById('tg_bs').click();
          out.tg_bs = document.querySelector('#L_blk > g').style.display;
          document.getElementById('tg_bs').click();
          document.getElementById('tg_bd').click();
          out.tg_bd = document.querySelector('#L_blk > g:nth-child(2)').style.display;
          document.getElementById('tg_bd').click();
          document.getElementById('tg_pipe').click();
          out.tg_pipe = document.querySelector('.pipe-swarm').style.display;
          document.getElementById('tg_pipe').click();
          document.getElementById('tg_quiet').click();
          out.quiet = document.body.classList.contains('quiet');
          document.getElementById('tg_quiet').click();
          document.getElementById('tg_contrast').click();
          out.hc = document.body.classList.contains('hc');
          document.getElementById('tg_contrast').click();
          document.getElementById('btnPlay').click();
          const t1 = JingluoRing.clock.t;
          return {out, t1, paused: !JingluoRing.clock.playing};
        }''')
        live.wait_for_timeout(350)
        paused = live.evaluate('JingluoRing.clock.t')
        speed = live.evaluate('''() => {
          document.getElementById('btnPlay').click();
          document.getElementById('selSpeed').value = '2';
          document.getElementById('selSpeed').dispatchEvent(new Event('change'));
          const t0 = JingluoRing.clock.t;
          return t0;
        }''')
        live.wait_for_timeout(400)
        speed_after = live.evaluate('''() => {
          const t1 = JingluoRing.clock.t;
          document.getElementById('btnPlay').click();
          JingluoRing.clock.speed = 1;
          return t1;
        }''')
        seek = live.evaluate('''() => {
          const c = JingluoRing.clock;
          c.t = 1.2; c.tb = 1.2;
          window.seek(8);
          const together = {
            t: JingluoFlow.wrap(c.t, CYC),
            tb: JingluoFlow.wrap(c.tb, CYC),
            scrub: +document.getElementById('scrub').value
          };
          c.t = 2; c.tb = 1.6;
          window.seek(8);
          const kept = {
            t: JingluoFlow.wrap(c.t, CYC),
            tb: JingluoFlow.wrap(c.tb, CYC)
          };
          return {together, kept};
        }''')
        live.set_viewport_size({'width': 390, 'height': 800})
        live.wait_for_timeout(150)
        small = live.evaluate('''() => {
          const b = document.getElementById('btnPlay').getBoundingClientRect();
          return {h: b.height, top: b.top, scroll: document.documentElement.scrollWidth - document.documentElement.clientWidth};
        }''')
        live.set_viewport_size({'width': 1280, 'height': 900})
        wide = live.evaluate('''() => {
          const b = document.getElementById('btnPlay').getBoundingClientRect();
          return {w: b.width, h: b.height};
        }''')
        browser.close()

    bad_net = [u for u in requests if not (u.startswith('file:') or u.startswith('data:'))]
    problems = []
    if errors:
        problems.append('video console: ' + ' | '.join(errors[:8]))
    if live_err:
        problems.append('live console: ' + ' | '.join(live_err[:8]))
    if bad_net:
        problems.append('network: ' + ' '.join(bad_net[:5]))
    if not video['video'] or video['h1'] != 'none':
        problems.append(f'video mode {video}')
    if video['nRing'] != 38 or video['nObj'] != 38 or video['nCir'] != 38:
        problems.append(f'circle count {video}')
    if '往返' not in video['credit'] or '疗效' not in video['credit']:
        problems.append('caption ' + video['credit'])
    if not seams['same']:
        problems.append('seam mismatch')
    if abs(seams['dang']) > 0.6:
        problems.append(f"seam angle jump {seams['dang']}")
    for a in audits:
        if a['outside'] or a['labelHits'] or a['rings'] != 38 or a['visible'] < 150:
            problems.append('audit ' + json.dumps(a, ensure_ascii=False))
    for key, val in toggles['out'].items():
        if key in ('quiet', 'hc'):
            if not val:
                problems.append(f'toggle {key} did not apply')
        elif val != 'none':
            problems.append(f'toggle {key} display={val}')
    if not toggles['paused']:
        problems.append('pause flag')
    if abs(paused - toggles['t1']) > 1e-6:
        problems.append(f'pause drifted {toggles["t1"]} -> {paused}')
    delta = speed_after - speed
    if not (0.45 <= delta <= 1.4):
        problems.append(f'speed 2x delta {delta} over ~0.4s (expect ~0.8)')
    if abs(seek['together']['t'] - 8) > 0.05 or abs(seek['together']['tb'] - 8) > 0.05:
        problems.append(f'seek together {seek}')
    if abs(seek['together']['scrub'] - 8) > 0.05:
        problems.append(f'seek scrub {seek}')
    if abs(seek['kept']['t'] - 8) > 0.05 or abs((seek['kept']['t'] - seek['kept']['tb']) - 0.4) > 0.05:
        problems.append(f'seek offset {seek}')
    if small['h'] < 36 or small['top'] < 0:
        problems.append(f'small control {small}')
    if small['scroll'] > 8:
        problems.append(f'small overflow {small}')
    if wide['h'] < 20:
        problems.append(f'wide control {wide}')

    summary = {
        'html_mb': round(HTML.stat().st_size / 1_000_000, 3),
        'circles': video['nCir'],
        'particles_sampled': seams['n'],
        'seam_same': seams['same'],
        'seam_angle': seams['dang'],
        'audits': audits,
        'pause_held': abs(paused - toggles['t1']) <= 1e-6,
        'speed_delta_s': delta,
        'seek': seek,
        'small': small,
        'problems': problems,
    }
    (ART / 'b4_test_summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    if problems:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        raise SystemExit('B/4 增强版检查没有通过')
    print('b4 enhanced ok', summary['html_mb'], 'MB', 'visible', audits[1]['visible'])
    return 0


if __name__ == '__main__':
    sys.exit(main())
