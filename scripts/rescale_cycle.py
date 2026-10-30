#!/usr/bin/env python3
"""把一份动画 config 的循环长度改成新的秒数，并保持接缝闭合。

步长、圈数按 new/old 缩放。圈数（lineLaps、dashLaps、twN、leadLaps、粒子 k、
turns、TAIJI_REV）必须是整数，这样 t = cycle 时相位回到 t = 0。
算出来不是整数就取最近的整数（至少 1 圈），并警告速度变了。
leadLaps 为 1、循环减半时按比例是 0.5，会保持 1，速度变为两倍。

brand.period 是真实秒数，不跟着缩短；它必须整除新的 cycle。整除不了就改成最近的可整除周期。
TU_SWITCH 这类「循环内的时刻」按比例挪。

items 里的 v 是速度（像素/秒）。页面自己用 round(v * cycle / 间距) 取整圈，
这里不改 v，循环仍然闭合。

  python scripts/rescale_cycle.py \\
    --config examples/b24-bamai-yuanli/config.json \\
    --cycle 30 \\
    --out out/b24-30s.json

再用原来的模板和底图跑 scripts/build.py。改完可以用 scripts/verify_loop.py 看接缝。
"""
from __future__ import annotations

import argparse
import math
import re
import sys
from collections import Counter
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import dump_json, load_json  # noqa: E402


# 一圈循环里走完的整数圈数。缩放后仍须为整数，速度才接得上。
LAP_KEYS = {'lineLaps', 'dashLaps', 'twN', 'leadLaps', 'k', 'turns', 'TAIJI_REV'}
# 以秒计、落在循环内部的时刻，按同样比例挪。
TIME_KEYS = {'TU_SWITCH'}

_SECOND = re.compile(r'(\d+(?:\.\d+)?)(\s*)(秒)')


def parse_args(argv):
    p = argparse.ArgumentParser(description='按比例改动画循环秒数，并保持周期能整除')
    p.add_argument('--config', required=True)
    p.add_argument('--cycle', required=True, type=float, help='新的循环秒数')
    p.add_argument('--out', required=True)
    return p.parse_args(argv)


def warn(msg):
    print(msg, file=sys.stderr, flush=True)


def as_fraction(value):
    return Fraction(str(value))


def json_number(value):
    if isinstance(value, Fraction):
        if value.denominator == 1:
            return int(value)
        return float(value)
    if isinstance(value, float) and abs(value - round(value)) < 1e-9:
        return int(round(value))
    return value


def divides(cycle, period):
    if period == 0:
        return False
    quot = float(cycle) / float(period)
    return abs(quot - round(quot)) <= 1e-6


def round_half_away(value):
    if value >= 0:
        return int(math.floor(value + 0.5))
    return -int(math.floor(-value + 0.5))


def scale_laps(old, ratio):
    """返回 (新圈数, 按比例的精确值, 速度是否因此改变)。0 保持 0。"""
    target = float(as_fraction(old) * ratio)
    if old == 0:
        return 0, target, False
    rounded = round_half_away(target)
    if rounded == 0:
        rounded = 1 if target > 0 else -1
    changed = abs(rounded - target) > 1e-6
    return rounded, target, changed


def fmt(value):
    if isinstance(value, float):
        text = f'{value:.6f}'.rstrip('0').rstrip('.')
        return text or '0'
    return str(value)


def laps_per_sec(laps, cycle):
    return float(laps) / float(cycle)


class Rescaler:
    def __init__(self, old_cycle, new_cycle):
        self.old_cycle = as_fraction(old_cycle)
        self.new_cycle = as_fraction(new_cycle)
        self.ratio = self.new_cycle / self.old_cycle
        self.notes = []
        self.adjustments = []
        # (where, old, new, target, changed)。粒子圈数在收尾时按旧值/新值汇总。
        self.laps = []

    def note(self, msg):
        self.notes.append(msg)

    def apply_laps(self, old, where):
        new, target, changed = scale_laps(old, self.ratio)
        self.laps.append((where, old, new, target, changed))
        return new

    def scale_steps(self, steps):
        if not isinstance(steps, list) or not steps:
            return
        scaled = []
        for step in steps:
            dur = step.get('dur', 0)
            scaled.append(as_fraction(dur) * self.ratio)
        drift = self.new_cycle - sum(scaled, Fraction(0))
        if scaled and drift != 0:
            scaled[-1] += drift
            if abs(float(drift)) > 1e-6:
                self.adjustments.append(
                    f'警告：步长按比例相加与新 cycle 差 {float(drift):.6f} 秒，已补进最后一步。'
                )
        if scaled and scaled[-1] <= 0:
            raise SystemExit('缩放后有步长小于等于 0，请换一个能被各段比例容纳的 cycle。')
        for step, dur in zip(steps, scaled):
            step['dur'] = json_number(dur)
        shown = ', '.join(fmt(json_number(d)) for d in scaled)
        self.note(f'steps 时长 × {fmt(float(self.ratio))} → {shown}（合计 {fmt(json_number(self.new_cycle))}）')

    def fit_period(self, period, where):
        if divides(self.new_cycle, period):
            self.note(f'{where} {fmt(period)} 秒仍整除 cycle {fmt(json_number(self.new_cycle))}')
            return json_number(as_fraction(period)) if not isinstance(period, float) else period
        count = max(1, round_half_away(float(self.new_cycle) / float(period)))
        new_period = self.new_cycle / count
        old_rate = 1 / float(period)
        new_rate = 1 / float(new_period)
        self.adjustments.append(
            f'警告：{where} {fmt(period)} 秒不能整除新 cycle {fmt(json_number(self.new_cycle))}，'
            f'改为 {fmt(json_number(new_period))} 秒（{count} 次）。'
            f'闪烁由 {old_rate:.4f} 次/秒变为 {new_rate:.4f} 次/秒。'
        )
        return json_number(new_period)

    def rewrite_text(self, text):
        old = float(self.old_cycle)
        new = json_number(self.new_cycle)

        def repl(match):
            try:
                value = float(match.group(1))
            except ValueError:
                return match.group(0)
            if abs(value - old) > 1e-6:
                return match.group(0)
            return f'{fmt(new)}{match.group(2)}{match.group(3)}'

        return _SECOND.sub(repl, text)

    def scale_particles(self, rows, where):
        for row in rows:
            if not isinstance(row, list) or not row:
                continue
            old = row[0]
            if isinstance(old, bool) or not isinstance(old, (int, float)):
                continue
            row[0] = self.apply_laps(old, f'{where} k')

    def walk(self, node, path):
        if isinstance(node, dict):
            for key, value in list(node.items()):
                here = f'{path}.{key}' if path else key
                if key == 'steps' and isinstance(value, list):
                    self.scale_steps(value)
                    for index, step in enumerate(value):
                        self.walk(step, f'{here}[{index}]')
                elif key == 'P' and _particle_table(value):
                    self.scale_particles(value, here)
                elif key in LAP_KEYS and _number(value):
                    node[key] = self.apply_laps(value, here)
                elif key == 'period' and _number(value):
                    node[key] = self.fit_period(value, here)
                elif key in TIME_KEYS and _number(value):
                    target = as_fraction(value) * self.ratio
                    node[key] = json_number(target)
                    self.note(f'{here} {fmt(value)} → {fmt(node[key])}（循环内时刻）')
                elif isinstance(value, str):
                    rewritten = self.rewrite_text(value)
                    if rewritten != value:
                        node[key] = rewritten
                        self.note(f'{here} 里的「{fmt(float(self.old_cycle))} 秒」已改成 {fmt(json_number(self.new_cycle))} 秒')
                else:
                    self.walk(value, here)
        elif isinstance(node, list):
            for index, item in enumerate(node):
                if isinstance(item, str):
                    node[index] = self.rewrite_text(item)
                else:
                    self.walk(item, f'{path}[{index}]')


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _particle_table(rows):
    if not isinstance(rows, list) or not rows:
        return False
    for row in rows:
        if not isinstance(row, list) or len(row) < 4:
            return False
        if not all(_number(item) for item in row[:5] if item is not None):
            return False
        if not _number(row[0]) or abs(float(row[0])) > 100:
            return False
    return True


def rescale(cfg, new_cycle):
    if 'cycle' not in cfg:
        raise SystemExit('config 里没有 cycle')
    old_cycle = cfg['cycle']
    if float(old_cycle) <= 0 or float(new_cycle) <= 0:
        raise SystemExit('cycle 要大于 0')
    tool = Rescaler(old_cycle, new_cycle)
    cfg['cycle'] = json_number(tool.new_cycle)
    tool.note(f'cycle {fmt(old_cycle)} → {fmt(cfg["cycle"])}')
    # cycle 已经写好，避免 walk 再把它当普通字段。其余字段从根往下走。
    saved = cfg.pop('cycle')
    tool.walk(cfg, '')
    cfg['cycle'] = saved
    # 把 cycle 放回原来的相对位置：walk 不移动键，pop 会把 cycle 挪到末尾。
    # 重新插入到原位。
    return cfg, tool


def restore_key_order(original, updated):
    """保持原来的键顺序，避免 cycle 被挪到 JSON 末尾。"""
    if isinstance(original, dict) and isinstance(updated, dict):
        out = {}
        for key in original:
            if key in updated:
                out[key] = restore_key_order(original[key], updated[key])
        for key in updated:
            if key not in out:
                out[key] = updated[key]
        return out
    if isinstance(original, list) and isinstance(updated, list) and len(original) == len(updated):
        return [restore_key_order(a, b) for a, b in zip(original, updated)]
    return updated


def _is_particle(where):
    return where.endswith(' k') or '.P' in where


def summarize(tool):
    """stdout 放缩放结果；速度变了的写到 stderr。粒子按旧圈数/新圈数合成一行。"""
    lines = list(tool.notes)
    particles = Counter()
    for where, old, new, target, changed in tool.laps:
        if _is_particle(where):
            particles[(old, new, fmt(target), changed)] += 1
            continue
        old_rate = laps_per_sec(old, tool.old_cycle)
        new_rate = laps_per_sec(new, tool.new_cycle)
        if changed:
            tool.adjustments.append(
                f'警告：{where} {fmt(old)} → {fmt(new)}（按比例应为 {fmt(target)}）。'
                f'速度由 {old_rate:.4f} 圈/秒变为 {new_rate:.4f} 圈/秒。'
            )
        else:
            lines.append(f'{where} {fmt(old)} → {fmt(new)}（速度不变，{old_rate:.4f} 圈/秒）')
    for (old, new, target, changed), count in sorted(particles.items(), key=lambda item: (item[0][0], item[0][1])):
        old_rate = laps_per_sec(old, tool.old_cycle)
        new_rate = laps_per_sec(new, tool.new_cycle)
        if changed:
            tool.adjustments.append(
                f'警告：粒子圈数 k {fmt(old)} → {fmt(new)}（按比例应为 {target}），共 {count} 处。'
                f'速度由 {old_rate:.4f} 圈/秒变为 {new_rate:.4f} 圈/秒。'
            )
        else:
            lines.append(
                f'粒子圈数 k {fmt(old)} → {fmt(new)}，{count} 处（速度不变，{old_rate:.4f} 圈/秒）'
            )
    return lines


def main(argv=None):
    args = parse_args(argv if argv is not None else sys.argv[1:])
    original = load_json(args.config)
    # rescale 就地修改，先留一份键顺序。
    import copy
    snapshot = copy.deepcopy(original)
    updated, tool = rescale(original, args.cycle)
    updated = restore_key_order(snapshot, updated)
    for line in summarize(tool):
        print(line, flush=True)
    for msg in tool.adjustments:
        print(msg, file=sys.stderr, flush=True)
    durations = [float(step.get('dur', 0)) for step in updated.get('steps') or []]
    if durations and abs(sum(durations) - float(updated['cycle'])) > 1e-4:
        raise SystemExit(f'steps 之和 {sum(durations)} 与 cycle {updated["cycle"]} 不一致')
    dump_json(args.out, updated)
    print(f'wrote {args.out}', flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
