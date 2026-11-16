#!/usr/bin/env python3
"""给已有成片另存增强版。不改原 HTML 的字节。

五张通用旧模板、B/28、B/24 都走这一支脚本。粒子逻辑在 template/baked-pipes.js，
时间公式在 template/flow.js。B/24 已有 U 形裁剪和领头，只补时钟和开关，不改成往返。
"""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import data_url, subset_woff2  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FONT = Path('/tmp/NotoSansCJKtc-Regular.otf')
DAY = '2026-11-17'

CSS = """
@media (max-width:720px){
  .wrap{padding:8px}
  h1{font-size:17px;letter-spacing:0}
  .ctl{gap:8px 12px;font-size:15px}
  input[type=range]{width:min(100%,220px);max-width:100%}
  button,select{min-height:40px}
}
.ctl{max-width:100%}
.pipe-swarm{pointer-events:none}
body.quiet .fx-crowd{display:none}
body.quiet #L_flow{display:none}
body.hc{background:#120814;color:#fff}
body.hc .note,body.hc .sub{color:#f6efe2}
body.hc .ctl{background:#1a0b22;border:1px solid #D4AF37;border-radius:6px;padding:8px}
"""

CTL = """<div class="ctl" id="ctlEnhance">
  <label><input type="checkbox" id="tgQuiet"> 减弱动效</label>
  <label><input type="checkbox" id="tgContrast"> 高对比</label>
</div>
"""

HOOK_DUAL = r"""
window.renderAt=function(t,tb){if(tb===undefined)tb=t;render(t,tb);if(window.JingluoBake)JingluoBake.draw(JingluoFlow.wrap(t,CYC),JingluoFlow.wrap(tb,CYC));};
window.CYC=CYC;
JingluoBake.install(items,{cycle:CYC,steps:CFG.steps,starts:starts});
"""

HOOK_B28 = r"""
window.renderAt=function(t,tb){if(tb===undefined)tb=t;render(t,tb,t);if(window.JingluoBake)JingluoBake.draw(JingluoFlow.wrap(t,CYC),JingluoFlow.wrap(tb,CYC));};
window.CYC=CYC;window.taijiAngle=taijiAngle;
JingluoBake.install(items,{cycle:CYC,steps:CFG.steps,starts:starts});
"""

HOOK_B24 = r"""
window.renderAt=function(t){render(t);};
window.CYC=CYC;
"""

UI = r"""
window.seek=function(sec){
  const nt=JingluoFlow.wrap(+sec,CYC);
  const cur=JingluoFlow.wrap(Tm,CYC);
  const d=nt-cur;Tm+=d;
  if(typeof Tb!=='undefined')Tb+=d;
  window.renderAt(Tm,typeof Tb==='undefined'?Tm:Tb);
  if($('scrub'))$('scrub').value=(JingluoFlow.wrap(Tm,CYC)/CYC).toFixed(3);
};
if($('tgQuiet'))$('tgQuiet').onchange=e=>document.body.classList.toggle('quiet',e.target.checked);
if($('tgContrast'))$('tgContrast').onchange=e=>document.body.classList.toggle('hc',e.target.checked);
{const mq=window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)');
 if(mq&&mq.matches&&$('tgQuiet')){document.body.classList.add('quiet');$('tgQuiet').checked=true;}}
"""

CHARTS = [
    ('b31', 'examples/b31-cunguan-siji/寸关尺四季表里图_流动动画.html', 'dual'),
    ('b45', 'examples/b45-yulong-bafa/玉龍八法_流动动画.html', 'dual'),
    ('b1', 'examples/b1-yulong/玉龍_流动动画.html', 'dual'),
    ('b39', 'examples/b39-qi-qijing/氣的循環奇經八脈圖_流动动画.html', 'dual'),
    ('b36', 'examples/b36-shenying/神應經穴法圖_流动动画.html', 'dual'),
    ('b28', 'examples/b28-wuxing-liujing/五行六经图动画.html', 'b28'),
    ('b24', 'examples/b24-bamai-yuanli/把脈的原理動畫.html', 'b24'),
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def image_blob(html: str) -> str:
    m = re.search(r'data:image/jpeg;base64,[A-Za-z0-9+/=]+', html)
    return m.group(0) if m else ''


def embed_regular(html: str, font: Path) -> str:
    chars = ''.join(sorted({c for c in html if ord(c) >= 32}))
    subset = Path('/tmp') / '_seven_subset.woff2'
    subset_woff2(chars, font, subset, None)
    url = data_url(subset, 'font/woff2')
    subset.unlink(missing_ok=True)
    pat = r"(font-weight:400;src:url\()data:font/woff2;base64,[A-Za-z0-9+/=]+(\))"
    html2, n = re.subn(pat, r'\1' + url + r'\2', html, count=1)
    if n == 1:
        return html2
    face = "@font-face{font-family:'NotoTC';font-weight:400;src:url(" + url + ") format('woff2');}\n"
    html2, n = re.subn(r'<style>\n', '<style>\n' + face, html, count=1)
    if n != 1:
        raise SystemExit('没有放进字体')
    html2 = html2.replace(
        'font-family:"PingFang SC","Noto Sans CJK SC","Microsoft YaHei",sans-serif',
        'font-family:"NotoTC","PingFang SC","Noto Sans CJK SC","Microsoft YaHei",sans-serif',
        1,
    )
    return html2


def splice(html: str, kind: str, flow: str, bake: str) -> str:
    if '</style>' not in html:
        raise SystemExit('没有 style')
    html = html.replace('</style>', CSS + '</style>', 1)
    if '<div class="ctl" id="toggles"></div>' in html:
        html = html.replace('<div class="ctl" id="toggles"></div>', '<div class="ctl" id="toggles"></div>\n' + CTL, 1)
    elif 'id="toggles"' in html:
        html = html.replace('id="toggles"></div>', 'id="toggles"></div>\n' + CTL, 1)
    else:
        raise SystemExit('没有图层开关栏')
    block = flow.rstrip() + '\n' + (bake.rstrip() + '\n' if kind != 'b24' else '')
    if kind == 'dual':
        old = 'window.renderAt=t=>render(t,t);window.CYC=CYC;'
        new = block + HOOK_DUAL
        loop_old = 'render(Tm,Tb);$(\'scrub\')'
        loop_new = 'window.renderAt(Tm,Tb);$(\'scrub\')'
        scrub_old = "$('scrub').oninput=e=>{const nt=+e.target.value*CYC;const d=nt-((Tm%CYC+CYC)%CYC);Tm+=d;Tb+=d;render(Tm,Tb);};"
        scrub_new = "$('scrub').oninput=e=>{window.seek(+e.target.value*CYC);};"
    elif kind == 'b28':
        old = 'window.renderAt=t=>render(t,t);window.CYC=CYC;window.taijiAngle=taijiAngle;'
        new = block + HOOK_B28
        loop_old = 'render(Tm,Tb,ts/1000);$(\'scrub\')'
        loop_new = 'window.renderAt(Tm,Tb);$(\'scrub\')'
        scrub_old = "$('scrub').oninput=e=>{const nt=+e.target.value*CYC;const d=nt-((Tm%CYC+CYC)%CYC);Tm+=d;Tb+=d;render(Tm,Tb,performance.now()/1000);};"
        scrub_new = "$('scrub').oninput=e=>{window.seek(+e.target.value*CYC);};"
    elif kind == 'b24':
        old = 'window.renderAt=t=>render(t);window.CYC=CYC;'
        new = block + HOOK_B24
        loop_old = 'render(Tm);$(\'scrub\')'
        loop_new = 'window.renderAt(Tm);$(\'scrub\')'
        scrub_old = "$('scrub').oninput=e=>{Tm=+e.target.value*CYC;render(Tm);};"
        scrub_new = "$('scrub').oninput=e=>{window.seek(+e.target.value*CYC);};"
    else:
        raise SystemExit(kind)
    if html.count(old) != 1 or html.count(loop_old) != 1 or html.count(scrub_old) != 1:
        raise SystemExit(f'锚点数量不对: {kind} render {html.count(old)} loop {html.count(loop_old)} scrub {html.count(scrub_old)}')
    html = html.replace(old, new, 1).replace(loop_old, loop_new, 1).replace(scrub_old, scrub_new, 1)
    html = html.replace('</script>', UI + '</script>', 1)
    banner = '<!-- 增强版 2026-11-17。底图 data URL 与增强前备份相同。粒子沿原有路径。 -->\n'
    if banner.strip() not in html:
        html = html.replace('<!DOCTYPE html>\n', '<!DOCTYPE html>\n' + banner, 1)
    return html


def main():
    if not FONT.is_file():
        raise SystemExit(f'缺少字体 {FONT}')
    flow = (ROOT / 'template' / 'flow.js').read_text(encoding='utf-8')
    bake = (ROOT / 'template' / 'baked-pipes.js').read_text(encoding='utf-8')
    # templates keep the same hooks for the next rebuild
    for rel, kind in (
        ('examples/b28-wuxing-liujing/template.html', 'b28'),
        ('examples/b24-bamai-yuanli/template.html', 'b24'),
    ):
        path = ROOT / rel
        text = splice(path.read_text(encoding='utf-8'), kind, flow, bake)
        path.write_text(text, encoding='utf-8')
        print('template', rel)
    for key, rel, kind in CHARTS:
        src = ROOT / rel
        digest = sha256(src)
        backup = src.parent / 'backup' / f'{DAY}-增强前' / src.name
        backup.parent.mkdir(parents=True, exist_ok=True)
        if not backup.exists():
            backup.write_bytes(src.read_bytes())
        (backup.parent / 'HASH.txt').write_text(
            f'{digest}  {src.name}\n来源：增强前的成片，日期 {DAY}。原文件保持这个哈希。\n',
            encoding='utf-8',
        )
        raw = src.read_text(encoding='utf-8')
        img = image_blob(raw)
        if not img:
            raise SystemExit(f'{rel} 没有底图')
        html = splice(raw, kind, flow, bake)
        html = embed_regular(html, FONT)
        if image_blob(html) != img:
            raise SystemExit(f'{rel} 底图被改动')
        if sha256(src) != digest:
            raise SystemExit(f'{rel} 原文件被写到了')
        out = src.with_name(src.stem + '_增强版' + src.suffix)
        out.write_text(html, encoding='utf-8')
        print(f'{key} {out.name} {out.stat().st_size/1e6:.2f} MB sha {digest[:12]}')


if __name__ == '__main__':
    main()
