"""Shared helpers: CJK font subsetting and small IO utilities.

Noto Sans CJK's TTC keeps several languages in one file. These charts use
traditional characters, which are face index 3 in NotoSansCJK-Regular.ttc
(0 Japanese, 1 Korean, 2 Simplified Chinese, 3 Traditional Chinese).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


def load_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def dump_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')


def which(cmd):
    found = shutil.which(cmd)
    if found:
        return found
    home = Path.home() / '.local' / 'bin' / cmd
    if home.is_file():
        return str(home)
    return None


FONT_DIRS = [
    '/usr/share/fonts/opentype/noto',
    '/usr/share/fonts/truetype/noto',
    '/usr/share/fonts/noto-cjk',
    '/usr/share/fonts/opentype/noto-cjk',
]

FONT_NAMES = {
    400: [
        'NotoSansCJK-Regular.ttc',
        'NotoSansCJKtc-Regular.otf',
        'NotoSansCJKsc-Regular.otf',
        'NotoSansCJKtc-Regular.ttf',
    ],
    700: [
        'NotoSansCJK-Bold.ttc',
        'NotoSansCJKtc-Bold.otf',
        'NotoSansCJKsc-Bold.otf',
        'NotoSansCJKtc-Bold.ttf',
    ],
}


def find_cjk_font(weight=400, explicit=None):
    if explicit:
        path = Path(explicit)
        if not path.is_file():
            raise SystemExit(f'找不到字体文件：{explicit}')
        return path
    for folder in FONT_DIRS:
        for name in FONT_NAMES[weight]:
            candidate = Path(folder) / name
            if candidate.is_file():
                return candidate
    raise SystemExit(
        '找不到 Noto Sans CJK。安装 fonts-noto-cjk，或用 --font-regular / --font-bold 指定文件。\n'
        '子集工具：pip install "fonttools[woff]"'
    )


def subset_woff2(text, font_path, out_path, font_index=3):
    """Write a woff2 subset containing the characters in ``text``."""
    tool = which('pyftsubset')
    if not tool:
        raise SystemExit('找不到 pyftsubset。安装：pip install "fonttools[woff]"')
    chars = ''.join(sorted({c for c in text if ord(c) >= 32}))
    if not chars:
        chars = ' '
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', delete=False) as tmp:
        tmp.write(chars)
        text_file = tmp.name
    cmd = [
        tool, str(font_path),
        f'--text-file={text_file}',
        '--flavor=woff2',
        f'--output-file={out_path}',
        '--layout-features=*',
    ]
    if str(font_path).lower().endswith(('.ttc', '.otc')) and font_index is not None:
        cmd.append(f'--font-number={font_index}')
    try:
        subprocess.run(cmd, check=True)
    finally:
        os.unlink(text_file)
    return out_path


def normalize_label(item):
    """标签：对象，或 [x, y, size, rotate, weight, text, kind]。"""
    if isinstance(item, (list, tuple)):
        x, y, size, rotate, weight, text, kind = item[:7]
        return dict(x=float(x), y=float(y), size=float(size), rotate=float(rotate),
                    weight=int(weight), text=str(text), kind=str(kind))
    return dict(
        x=float(item['x']),
        y=float(item['y']),
        size=float(item.get('size', item.get('fs', 14))),
        rotate=float(item.get('rotate', item.get('rot', 0))),
        weight=int(item.get('weight', item.get('fw', 400))),
        text=str(item.get('text', item.get('t', ''))),
        kind=str(item.get('kind', item.get('k', 'cjk'))),
    )


def data_url(path, mime):
    import base64
    raw = Path(path).read_bytes()
    return f'data:{mime};base64,' + base64.b64encode(raw).decode('ascii')
