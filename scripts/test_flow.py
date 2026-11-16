#!/usr/bin/env python3
"""JingluoFlow 的时间公式。和 template/flow.js 对一下，不打开浏览器。"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    raw = subprocess.check_output(
        ['node', '-e', r'''
const F = require("./template/flow.js");
const glow = [];
for (let i = 0; i < 12; i++) glow.push([F.glowAmp(24 - 1e-4, i, 2, 12), F.glowAmp(0, i, 2, 12)]);
console.log(JSON.stringify({
  wrapNeg: F.wrap(-1, 24),
  wrapCyc: F.wrap(24, 24),
  u0: F.uOf(0, 24, 2, 0.25),
  uC: F.uOf(24, 24, 2, 0.25),
  uNear: F.uOf(23.99, 24, 2, 0),
  laps: F.laps(18, 24, 30),
  ping0: F.travel(0, "ping").s,
  pingHalf: F.travel(0.5, "ping").s,
  pingEnd: F.travel(0.999, "ping").s,
  fade0: F.travel(0, "fade").fade,
  fadeMid: F.travel(0.5, "fade").fade,
  loopFade: F.travel(0, "loop").fade,
  tw0: F.twinkle(0, 24, 12, 0),
  twC: F.twinkle(24, 24, 12, 0),
  glow
}));
'''],
        cwd=ROOT, text=True,
    )
    d = json.loads(raw)
    assert abs(d['wrapNeg'] - 23) < 1e-9, d['wrapNeg']
    assert d['wrapCyc'] == 0
    assert abs(d['u0'] - d['uC']) < 1e-9
    assert d['uNear'] > 0.99
    assert d['laps'] == 14  # 18*24/30 = 14.4，四舍五入到 14
    assert abs(d['ping0']) < 1e-9
    assert abs(d['pingHalf'] - 1) < 1e-6
    assert d['pingEnd'] < 0.01
    assert d['fade0'] == 0
    assert d['fadeMid'] == 1
    assert d['loopFade'] == 1
    assert abs(d['tw0'] - d['twC']) < 1e-9
    for i, (before, after) in enumerate(d['glow']):
        if i == 0:
            assert before < 0.02 and abs(after - 1) < 1e-9, (before, after)
        else:
            assert abs(before - after) < 0.02, (i, before, after)
    print('flow ok')
    return 0


if __name__ == '__main__':
    sys.exit(main())
