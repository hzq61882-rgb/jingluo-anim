#!/usr/bin/env python3
"""B/31 轮周十二组补字版。不覆盖逐环旋转文字版。"""
from __future__ import annotations

import json
from pathlib import Path

from build_b31_spin import DIR, main

# (字, x0, y0, x1, y1, zone) 彩点在字的左侧，框只盖字，不盖点和辐条。
def col(names, x, y, dy, h, w2=24, w3=34):
    out = []
    for i, name in enumerate(names):
        w = w3 if len(name) >= 3 else w2
        y0 = y + i * dy
        out.append((name, x, y0, x + w, y0 + h, 'strip'))
    return out


GROUPS = [
    ('手少阴心经', '左上靠中央', [
        ('神门', 348, 153, 372, 162, 'strip'),
        ('少冲', 348, 162, 376, 171, 'strip'),
        ('通里', 348, 171, 372, 180, 'strip'),
        ('极泉', 348, 181, 372, 190, 'strip'),
        ('心俞', 348, 190, 380, 199, 'strip'),
        ('巨阙', 348, 199, 374, 208, 'strip'),
    ]),
    ('手少阳三焦经', '左上', col(
        ['丝竹空', '阳池', '中渚', '天井', '关冲', '外关', '石门', '三焦俞'],
        300, 160, 10, 9)),
    ('足太阴脾经', '左中', col(
        ['太白', '大都', '商丘', '隐白', '大包', '公孙', '章门', '脾俞'],
        276, 238, 7, 6, w2=24, w3=28)),
    ('手厥阴心包经', '左下', col(
        ['大陵', '中冲', '天池', '劳宫', '内关', '厥阴俞'],
        270, 306, 9, 8)),
    ('足阳明胃经', '左下靠中央', col(
        ['冲阳', '解溪', '厉兑', '头维', '丰隆', '中脘', '胃俞'],
        316, 350, 9, 8)),
    ('足少阴肾经', '底部靠中央', col(
        ['太溪', '复溜', '涌泉', '然谷', '大钟', '步廊', '京门', '肾俞', '五枢', '照海'],
        378, 384, 8, 7, w2=28, w3=34)),
    ('足少阳胆经', '顶部靠中央', col(
        ['丘墟', '侠溪', '阳辅', '童子髎', '足临泣', '光明', '中渎', '悬钟', '日月', '胆俞'],
        412, 130, 8, 7, w2=28, w3=36)),
    ('足厥阴肝经', '右上', col(
        ['太冲', '曲泉', '行间', '大敦', '期门', '蠡沟', '肝俞'],
        482, 156, 10, 8, w2=28)),
    ('手太阳小肠经', '右中', col(
        ['腕骨', '后溪', '小海', '支正', '少泽', '颧髎', '关元', '小肠俞'],
        518, 226, 9, 8, w2=28, w3=36)),
    ('手太阴肺经', '右中下', col(
        ['太渊', '尺泽', '中府', '列缺', '肺俞'],
        500, 306, 10, 8)),
    ('手阳明大肠经', '底部', col(
        ['合谷', '曲池', '二间', '三间', '偏历', '天枢', '大肠俞', '迎香'],
        416, 402, 8, 7, w2=44, w3=48)),
    ('中下原图串', '右下，不另起经名', col(
        ['厉兑', '至阴', '冲阳', '束骨', '承扬', '睛明', '中极', '膀胱俞'],
        488, 362, 11, 9, w2=30, w3=38)),
]


def build():
    strips = [row for _title, _where, rows in GROUPS for row in rows]
    out = DIR / '寸关尺四季表里图_逐环旋转补字版.html'
    cov = DIR / 'coverage-逐环旋转补字.json'
    main(extra_labels=strips, out_html=out, coverage_path=cov, inner=True)
    report = json.loads(cov.read_text(encoding='utf-8'))
    groups = []
    for title, where, rows in GROUPS:
        groups.append({
            'title': title,
            'where': where,
            'given': len(rows),
            'placed': len(rows),
            'unmatched': [],
            'names': [r[0] for r in rows],
        })
    report['inner_groups'] = groups
    report['inner_names_given'] = sum(g['given'] for g in groups)
    report['inner_names_placed'] = sum(g['placed'] for g in groups)
    report['inner_unmatched'] = []
    report['source'] = '11:08 与 11:09 确认的轮周十二组，写在逐环旋转补字版。不是 OCR，也不是国家标准核对。'
    cov.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('groups', len(groups), 'names', report['inner_names_placed'])
    for g in groups:
        print(f"{g['given']:2d} {g['title']} {g['where']}")


if __name__ == '__main__':
    build()
