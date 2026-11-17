#!/usr/bin/env python3
"""B/31 按 2026-11-17 源坐标规格画出的矢量。坐标都是 809×596 源图。"""
from __future__ import annotations

import math

# 色类是源图视觉色，不是五行推断。
PAL = {
    'B': '#5898bb',
    'A': '#a8bcb1',
    'G': '#75a34f',
    'Y': '#efed5d',
    'R': '#c83a36',
    'D': '#29305e',
    'O': '#cf8746',
    'P': '#8d5a84',
    'K': '#8d8a84',
    'T': '#632b2a',
}

RING_HEX = ['#9ba8a2', '#edea62', '#c53b31', '#2e3464', '#d5803e', '#73a24e', '#9dafac', '#a087ac', '#4e2d28']

HEADERS = [
    {
        'id': 'L1', 'klass': 'R',
        'arc': 'M50 89 V80 C65 71 89 64 103 64 C109 64 113 69 115 73 C119 65 123 64 128 64 C146 65 162 71 176 79 V89 H145 M50 89 H88',
        'circles': [(103.5, 76.5, 12.5), (127.5, 76.5, 12.5)],
        'wings': [
            'M51 80 C68 70 88 65 103 64 L93 78 Q76 69 51 80 Z',
            'M128 64 C146 65 162 71 175 79 Q152 68 140 78 Z',
        ],
        'dash': 'M45 104 C37 132 38 179 49 216',
    },
    {
        'id': 'L2', 'klass': 'Y',
        'arc': 'M49 245 V234 C64 226 87 220 103 219 C110 219 114 224 116 230 C120 221 124 219 128 220 C145 221 163 227 176 235 V245 H145 M49 245 H86',
        'circles': [(103, 232.5, 12.5), (128, 233, 12.5)],
        'wings': [
            'M50 234 C68 225 88 220 103 219 L91 233 Q74 224 50 234 Z',
            'M128 220 C148 221 164 228 175 235 Q153 225 141 234 Z',
        ],
        'dash': 'M45 250 C35 286 39 350 50 389',
    },
    {
        'id': 'L3', 'klass': 'B',
        'arc': 'M49 406 V396 C66 387 87 383 102 382 C109 382 112 387 115 393 C119 384 123 383 127 383 C145 383 164 390 176 397 V405 H145 M49 406 H86',
        'circles': [(102, 395, 12.5), (127, 395, 12.5)],
        'wings': [
            'M50 396 C68 387 88 383 102 382 L90 396 Q74 386 50 396 Z',
            'M127 383 C147 384 165 391 175 397 Q151 387 140 397 Z',
        ],
        'dash': 'M46 418 C40 447 45 487 55 515',
    },
    {
        'id': 'R1', 'klass': 'A',
        'arc': 'M643 85 V76 C658 68 679 62 692 60 C699 60 704 65 705 71 C710 62 713 60 718 60 C735 61 756 67 773 76 V84 H734 M643 85 H680',
        'circles': [(692.5, 72.5, 12), (717, 72.5, 12)],
        'wings': [
            'M644 76 C659 68 679 62 692 60 L681 75 Q663 67 644 76 Z',
            'M718 60 C737 61 758 68 772 76 Q748 66 730 74 Z',
        ],
        'dash': 'M768 91 C781 124 785 176 769 218',
    },
    {
        'id': 'R2', 'klass': 'G',
        'arc': 'M643 240 V231 C658 223 680 216 694 214 C701 214 705 219 707 225 C711 216 716 214 720 214 C739 215 760 221 775 231 V239 H738 M643 240 H681',
        'circles': [(694.5, 226.5, 12.5), (719, 226, 12.5)],
        'wings': [
            'M644 231 C661 222 680 216 694 214 L682 230 Q666 222 644 231 Z',
            'M720 214 C741 215 760 222 774 231 Q750 221 732 230 Z',
        ],
        'dash': 'M770 248 C784 285 782 341 769 377',
    },
    {
        'id': 'R3', 'klass': 'R',
        'arc': 'M644 400 V391 C660 383 684 376 699 376 C705 376 709 382 711 387 C715 379 720 376 725 376 C742 377 761 383 775 392 V400 H741 M644 400 H682',
        'circles': [(699, 388.5, 12.5), (724, 388.5, 12.5)],
        'wings': [
            'M645 391 C662 382 685 376 699 376 L687 390 Q669 382 645 391 Z',
            'M725 376 C743 377 762 384 774 392 Q750 381 737 391 Z',
        ],
        'dash': 'M771 407 C784 438 780 478 770 507',
    },
]

BARS = {
    'L1-L': [[88, 89, 113, 94, 'B'], [89, 108, 113, 113, 'A'], [89, 127, 113, 132, 'G'], [90, 146, 113, 152, 'Y'], [61, 165, 89, 170, 'R'], [92, 184, 113, 189, 'Y']],
    'L1-R': [[117, 89, 138, 94, 'G'], [137, 108, 165, 113, 'R'], [116, 127, 139, 132, 'Y'], [116, 146, 139, 151, 'Y'], [115, 165, 141, 170, 'B'], [116, 184, 141, 189, 'A']],
    'L2-L': [[88, 246, 113, 250, 'B'], [90, 264, 113, 269, 'A'], [93, 283, 114, 288, 'G'], [94, 302, 114, 308, 'Y'], [90, 322, 115, 327, 'R'], [61, 341, 83, 346, 'Y']],
    'L2-R': [[116, 246, 140, 251, 'G'], [116, 263, 140, 269, 'R'], [140, 281, 161, 286, 'Y'], [117, 302, 141, 307, 'Y'], [116, 321, 141, 326, 'B'], [117, 340, 141, 345, 'A']],
    'L3-L': [[61, 406, 89, 411, 'B'], [89, 425, 115, 430, 'A'], [89, 443, 115, 448, 'G'], [89, 462, 116, 467, 'Y'], [89, 480, 116, 486, 'R'], [90, 500, 116, 505, 'Y']],
    'L3-R': [[116, 406, 141, 411, 'G'], [116, 425, 141, 431, 'R'], [116, 443, 141, 449, 'Y'], [116, 462, 141, 467, 'Y'], [139, 479, 163, 485, 'B'], [117, 500, 141, 505, 'A']],
    'R1-L': [[681, 85, 703, 90, 'B'], [657, 104, 681, 109, 'A'], [681, 124, 705, 130, 'G'], [681, 144, 704, 150, 'Y'], [681, 162, 704, 169, 'R'], [681, 182, 704, 188, 'Y']],
    'R1-R': [[708, 85, 731, 90, 'G'], [708, 105, 731, 111, 'R'], [708, 125, 731, 130, 'Y'], [708, 144, 732, 150, 'Y'], [708, 163, 731, 168, 'B'], [732, 181, 757, 186, 'B']],
    'R2-L': [[683, 240, 706, 246, 'B'], [683, 260, 706, 265, 'A'], [660, 280, 683, 285, 'G'], [682, 297, 708, 304, 'Y'], [683, 316, 708, 322, 'R'], [683, 335, 708, 341, 'Y']],
    'R2-R': [[733, 238, 756, 244, 'G'], [710, 258, 732, 264, 'R'], [711, 278, 733, 284, 'Y'], [711, 296, 733, 302, 'Y'], [711, 315, 734, 321, 'B'], [711, 334, 735, 339, 'A']],
    'R3-L': [[684, 400, 708, 406, 'B'], [684, 421, 709, 426, 'A'], [684, 438, 708, 444, 'G'], [684, 457, 708, 463, 'Y'], [660, 476, 684, 481, 'R'], [684, 494, 710, 500, 'Y']],
    'R3-R': [[712, 400, 737, 406, 'G'], [736, 418, 758, 424, 'R'], [712, 438, 738, 444, 'Y'], [712, 456, 739, 462, 'Y'], [712, 475, 739, 481, 'B'], [713, 493, 739, 499, 'A']],
}

CELLS = {
    'L1-L': [[89, 94, 113, 108], [89, 113, 113, 127], [90, 132, 113, 146], [90, 152, 113, 165], [90, 170, 113, 184], [92, 189, 113, 204]],
    'L1-R': [[117, 94, 141, 108], [117, 113, 141, 127], [117, 132, 139, 146], [116, 151, 139, 165], [116, 170, 141, 184], [116, 189, 141, 203]],
    'L2-L': [[90, 250, 113, 264], [91, 269, 114, 283], [94, 288, 114, 302], [94, 308, 114, 322], [91, 327, 114, 340], [91, 346, 114, 358]],
    'L2-R': [[116, 251, 140, 263], [116, 269, 140, 281], [117, 286, 141, 302], [117, 307, 141, 321], [117, 326, 141, 340], [117, 345, 141, 359]],
    'L3-L': [[89, 411, 115, 425], [89, 430, 115, 443], [89, 448, 115, 462], [89, 467, 116, 480], [90, 486, 116, 500], [90, 505, 116, 519]],
    'L3-R': [[116, 411, 141, 425], [116, 431, 141, 443], [116, 449, 141, 462], [116, 467, 141, 480], [117, 485, 141, 500], [117, 505, 141, 519]],
    'R1-L': [[681, 90, 703, 104], [681, 109, 704, 124], [681, 130, 704, 144], [681, 150, 704, 162], [681, 169, 704, 182], [681, 188, 704, 201]],
    'R1-R': [[708, 90, 731, 105], [708, 111, 731, 125], [708, 130, 732, 144], [708, 150, 732, 163], [708, 168, 732, 181], [708, 186, 732, 200]],
    'R2-L': [[683, 246, 706, 260], [683, 265, 706, 279], [683, 285, 707, 297], [683, 304, 708, 316], [683, 322, 708, 335], [683, 341, 708, 353]],
    'R2-R': [[710, 244, 733, 258], [711, 264, 733, 278], [711, 284, 733, 296], [711, 302, 734, 315], [711, 321, 735, 334], [711, 339, 735, 353]],
    'R3-L': [[684, 406, 708, 421], [684, 426, 708, 438], [684, 444, 708, 457], [684, 463, 708, 476], [684, 481, 710, 494], [684, 500, 710, 512]],
    'R3-R': [[712, 406, 737, 420], [712, 424, 738, 438], [712, 444, 738, 456], [712, 462, 739, 475], [713, 481, 739, 493], [713, 499, 739, 512]],
}

SEAMS = ['M114 94 V205', 'M115 250 V358', 'M116 411 V518', 'M706 90 V201', 'M708 245 V353', 'M710 406 V512']

BIG_RED = [
    ('C1', 76, 172, 14), ('C2', 153, 116, 16), ('C3', 75, 349, 15), ('C4', 151, 292, 16),
    ('C5', 74, 414, 16), ('C6', 152, 490, 16), ('C7', 669, 117, 16), ('C8', 746, 192, 14),
    ('C9', 672, 290, 16), ('C10', 744, 245, 15), ('C11', 671, 485, 14), ('C12', 749, 428, 15),
]

SENSORY = [(165, 374, 16), (201, 511, 18), (643, 183, 17), (648, 344, 17), (641, 425, 18)]

HALVES = [
    (61, 529, 12, 'R'), (168, 526, 12, 'G'), (659, 524, 12, 'R'), (762, 526, 12, 'G'),
]

PERIPH = [
    (206, 202, 11, 'Y'), (205, 185, 7, 'Y'),
    (247, 195, 11, 'R'), (232, 191, 7, 'R'),
    (388, 79, 11, 'R'), (401, 69, 6.5, 'R'),
    (435, 81, 11, 'G'), (418, 69, 6.5, 'G'), (410, 95, 7, 'G'),
    (585, 175, 11, 'G'), (602, 179, 7, 'G'),
    (571, 215, 11, 'R'), (584, 201, 7, 'R'),
    (558, 400, 10.5, 'A'), (576, 405, 7, 'A'),
    (603, 393, 11, 'B'), (603, 412, 7, 'B'),
    (393, 481, 11, 'A'), (399, 499, 7, 'A'),
    (420, 514, 11, 'B'), (407, 526, 7, 'B'),
    (239, 383, 11, 'R'), (226, 394, 7, 'R'),
    (224, 424, 11, 'Y'), (207, 418, 7, 'Y'),
]

TABLE_DOTS = {
    'L1': [(67.5, 98.5, 'O'), (67, 136, 'R'), (67, 155, 'Y'), (69, 193, 'D'), (47.5, 204, 'T'), (170, 98, 'R'), (130, 117, 'G'), (158, 136, 'D'), (167, 136, 'Y'), (158, 154, 'D'), (167, 154, 'Y'), (145, 209, 'T')],
    'L2': [(69, 257.5, 'D'), (58, 313.5, 'G'), (69, 314, 'Y'), (67, 333, 'R'), (94, 350, 'R'), (177, 352, 'T'), (157, 256, 'O'), (157, 273, 'R'), (128, 293, 'Y'), (157, 312, 'Y'), (158, 327, 'D')],
    'L3': [(69, 434, 'D'), (70, 454, 'D'), (58, 473, 'O'), (69, 473, 'Y'), (68, 511, 'R'), (163, 455, 'R'), (173, 455, 'Y'), (163, 473, 'R'), (173, 473, 'Y'), (165, 508, 'D'), (187, 486, 'T')],
    'R1': [(658, 95, 'G'), (667, 96, 'R'), (660, 134, 'D'), (660, 154, 'Y'), (648, 208, 'T'), (754, 93, 'D'), (759, 102, 'O'), (749, 114, 'D'), (750, 133, 'Y'), (751, 151, 'Y'), (749, 171, 'R'), (751, 211, 'T')],
    'R2': [(663, 270, 'R'), (692, 288, 'T'), (700, 288, 'G'), (664, 309, 'Y'), (664, 328, 'D'), (667, 364, 'T'), (722, 249, 'O'), (752, 268, 'D'), (752, 286, 'Y'), (753, 305, 'Y'), (755, 338, 'R')],
    'R3': [(664, 409, 'O'), (655, 445, 'T'), (664, 446, 'R'), (665, 464, 'Y'), (664, 503, 'D'), (645, 514, 'T'), (755, 406, 'R'), (765, 410, 'G'), (749, 446, 'D'), (758, 446, 'Y'), (750, 464, 'D'), (759, 464, 'Y')],
}

DOT_BRACKETS = [
    'M168 139 C180 141 180 149 168 152',
    'M174 456 C186 460 186 468 174 472',
    'M752 136 C764 139 764 145 752 149',
    'M754 289 C768 293 768 299 754 302',
    'M760 448 C772 451 772 459 760 462',
]

# 规格 §5.3 已核对的轮周点。空列表表示规格写明这一行没有独立小彩点。
NAMED_DOTS = {
    '神门': [((349.9, 157.9), 'D', 2.2), ((356.3, 157.9), 'Y', 2.2)],
    '少冲': [((349.9, 166.8), 'R', 2.2), ((356.3, 166.6), 'O', 2.2)],
    '通里': [((356.7, 175.5), 'K', 2.2)],
    '心俞': [((356.7, 193.3), 'K', 2.2)],
    '巨阙': [((356.5, 202.5), 'P', 2.2)],
    '天井': [((298.7, 192.0), 'B', 2.2)],
    '关冲': [((298.5, 201.7), 'O', 2.2)],
    '外关': [((298.5, 211.0), 'K', 2.2)],
    '石门': [((298.6, 220.6), 'P', 2.2)],
    '三焦俞': [((298.5, 230.0), 'K', 2.2)],
    '丰隆': [((307.7, 386.0), 'K', 2.2)],
    '中脘': [((307.8, 394.2), 'P', 2.2)],
    '胃俞': [((307.5, 402.5), 'K', 2.2)],
    '厉兑': [((307.5, 370.2), 'B', 2.2)],
    '头维': [((307.7, 378.1), 'O', 2.2)],
    '解溪': [((308.0, 363.0), 'R', 2.2)],
    '冲阳': [((302.0, 355.0), 'G', 2.2), ((308.0, 355.0), 'Y', 2.2)],
    '太溪': [((371.3, 383.0), 'Y', 2.2)],
    '复溜': [((371.1, 391.2), 'R', 2.2)],
    '涌泉': [((365.6, 398.9), 'B', 2.2), ((371.5, 399.1), 'O', 2.2)],
    '然谷': [((371.5, 407.4), 'B', 2.2)],
    '大钟': [((371.5, 416.0), 'K', 2.2)],
    '步廊': [((371.3, 424.8), 'G', 2.2)],
    '京门': [((371.2, 432.2), 'P', 2.2)],
    '肾俞': [((371.0, 440.5), 'K', 2.2)],
    '五枢': [((371.0, 448.5), 'K', 2.2)],
    '照海': [],
    '丘墟': [((407.1, 130.8), 'Y', 2.2)],
    '侠溪': [((407.3, 138.5), 'R', 2.2)],
    '阳辅': [((406.5, 147.8), 'B', 2.2)],
    '童子髎': [((406.7, 155.8), 'O', 2.2)],
    '足临泣': [((436.6, 164.4), 'G', 2.2)],
}

LEADS = [((328.6, 211.4), 5.0), ((401.0, 458.0), 5.0)]

CHAIN = [(517, 98), (633, 295), (518, 493), (287, 496), (174, 296), (287, 101),
         (511, 124), (607, 304), (498, 475), (294, 466), (200, 289), (308, 119)]

NODE_IDS = ['n0', 'n1', 'n2', 'n3', 'n4', 'n5', 'n6', 'n7', 'n8', 'n9', 'n10', 'n11']

CROSSES = [
    ('X1', 'M176 242 L635 80', False),
    ('X2', 'M176 403 L639 239', False),
    ('X3', 'M175 242 L637 239', False),
    ('X4', 'M176 403 L639 398', False),
    ('X5', 'M176 243 L641 395', True),
    ('X6', 'M176 400 L635 82', True),
]

WHEEL_TEXT = [(248, 481, 267, 490), (229, 500, 239, 519), (280, 501, 295, 516), (231, 528, 248, 544), (275, 526, 294, 540)]
PLUS_BOXES = [(366, 73, 380, 84), (439, 74, 450, 90), (239, 203, 252, 218), (190, 210, 202, 218),
              (561, 228, 577, 242), (576, 163, 585, 170), (233, 430, 245, 443), (214, 410, 224, 417),
              (541, 405, 552, 416), (581, 390, 591, 399), (400, 480, 410, 487), (430, 509, 440, 520)]
SIDE_BOXES = [
    (36, 96, 65, 202), (159, 142, 188, 209),
    (36, 249, 66, 358), (159, 300, 193, 359),
    (37, 430, 64, 519), (159, 430, 187, 513),
    (624, 99, 654, 213), (748, 101, 774, 216),
    (626, 249, 653, 375), (750, 264, 773, 375),
    (626, 431, 656, 515), (752, 430, 776, 509),
    (35, 12, 65, 25), (27, 526, 35, 572), (710, 550, 776, 566),
    (555, 437, 573, 451), (577, 438, 594, 451), (597, 455, 605, 533),
    (153, 359, 178, 389), (187, 495, 213, 529), (633, 170, 653, 197), (636, 332, 659, 358),
]


def _spin(parts, sid, cx, cy, r, fill, sw=0.9, stroke='#202020', turns=1):
    dash = max(2.2, r * 0.5)
    gap = max(3.2, r * 0.95)
    parts.append(
        f'<g id="{sid}" data-spin="1" data-kind="spec" data-turns="{turns}" data-cx="{cx}" data-cy="{cy}">'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#4a3b24" stroke-width="0.9" '
        f'stroke-dasharray="{dash:.1f} {gap:.1f}" opacity="0.8"/>'
        f'</g>'
    )


def build_spec_svg():
    """返回 (svg, inventory, circles, named_dots)。circles 是 (cx,cy,r) 供裁片剔除圆边。"""
    parts = ['<g id="geom">']
    inv = []
    circles = []
    nspin = 0

    def add_shape(item):
        inv.append(item)

    parts.append('<path id="frame" d="M35 26 H778 V572 H35 Z" fill="none" stroke="#161616" stroke-width="1"/>')
    add_shape({'id': 'frame', 'type': 'rect', 'redrawn': True, 'new_id': 'frame', 'box': [35, 26, 778, 572],
               'source': 'M35 26 H778 V572 H35 Z'})

    for rad, sid, sw in ((229, 'node-ring-outer', 1.05), (203, 'node-ring-inner', 0.9), (170, 'sector-ring', 0.85)):
        parts.append(f'<circle id="{sid}" cx="404" cy="296" r="{rad}" fill="none" stroke="#1a1a1a" stroke-width="{sw}"/>')
        add_shape({'id': sid, 'type': 'circle', 'redrawn': True, 'new_id': sid, 'cx': 404, 'cy': 296, 'r': rad})
        circles.append((404, 296, rad))

    parts.append('<g id="spokes" fill="none" stroke="#1a1a1a" stroke-width="0.7">')
    for k in range(12):
        th = math.radians(k * 30)
        u = (math.cos(th), math.sin(th))
        nrm = (-math.sin(th), math.cos(th))
        for s in (-1.1, 1.1):
            x0 = 404 + 84 * u[0] + s * nrm[0]
            y0 = 296 + 84 * u[1] + s * nrm[1]
            x1 = 404 + 170 * u[0] + s * nrm[0]
            y1 = 296 + 170 * u[1] + s * nrm[1]
            parts.append(f'<line id="spoke-{k}-{0 if s < 0 else 1}" x1="{x0:.2f}" y1="{y0:.2f}" x2="{x1:.2f}" y2="{y1:.2f}"/>')
        ex = 404 + 170 * u[0]
        ey = 296 + 170 * u[1]
        parts.append(f'<circle cx="{ex:.2f}" cy="{ey:.2f}" r="1.3" fill="#1a1a1a"/>')
        add_shape({'id': f'spoke-{k}', 'type': 'double-line', 'redrawn': True, 'new_id': f'spoke-{k}',
                   'theta': k * 30, 'r0': 84, 'r1': 170, 'offset': 1.1})
    parts.append('</g>')

    parts.append('<g id="crosses" fill="none" stroke="#1a1a1a">')
    for sid, d, dashed in CROSSES:
        dash = ' stroke-dasharray="4 2.6" stroke-width="0.7"' if dashed else ' stroke-width="0.85"'
        parts.append(f'<path id="{sid}" d="{d}"{dash}/>')
        add_shape({'id': sid, 'type': 'dashed' if dashed else 'line', 'redrawn': True, 'new_id': sid, 'd': d,
                   'grade': 'B', 'why': '可见共线段拟合，遮挡处不补分岔'})
    parts.append('</g>')

    chain = ' '.join(f'L{x} {y}' for x, y in CHAIN[1:])
    parts.append(f'<path id="node-chain" d="M{CHAIN[0][0]} {CHAIN[0][1]} {chain} Z" fill="none" stroke="#1a1a1a" stroke-width="0.95"/>')
    add_shape({'id': 'node-chain', 'type': 'polyline', 'redrawn': True, 'new_id': 'node-chain',
               'points': CHAIN, 'why': '1→3→5→7→9→11→13→15→17→19→21→23→1 直段'})

    parts.append('<g id="cell-frames" fill="none" stroke="#1a1a1a" stroke-width="0.75">')
    for key, rows in CELLS.items():
        for i, (x0, y0, x1, y1) in enumerate(rows):
            sid = f'cell-{key}-{i}'
            parts.append(f'<path id="{sid}" d="M{x0} {y0} V{y1} H{x1} V{y0}"/>')
            add_shape({'id': sid, 'type': 'cell', 'redrawn': True, 'new_id': sid, 'box': [x0, y0, x1, y1]})
    for i, d in enumerate(SEAMS):
        parts.append(f'<path id="seam-{i}" d="{d}"/>')
        add_shape({'id': f'seam-{i}', 'type': 'line', 'redrawn': True, 'new_id': f'seam-{i}', 'd': d})
    parts.append('</g>')

    parts.append('<g id="outer-brackets" fill="none" stroke="#1a1a1a" stroke-width="0.75" stroke-dasharray="3.5 2.5">')
    for h in HEADERS:
        parts.append(f'<path id="dash-{h["id"]}" d="{h["dash"]}"/>')
        add_shape({'id': f'dash-{h["id"]}', 'type': 'curve', 'redrawn': True, 'new_id': f'dash-{h["id"]}',
                   'd': h['dash'], 'grade': 'B'})
    parts.append('</g>')

    parts.append('<g id="big-red">')
    for sid, cx, cy, r in BIG_RED:
        _spin(parts, sid, cx, cy, r, '#ca4a59', 0.9, '#5c2428', 1 if nspin % 2 == 0 else -1)
        nspin += 1
        circles.append((cx, cy, r))
        add_shape({'id': sid, 'type': 'circle', 'redrawn': True, 'new_id': sid, 'cx': cx, 'cy': cy, 'r': r, 'fill': '#ca4a59'})
    parts.append('</g>')

    parts.append('<g id="bars">')
    bar_n = 0
    for key, rows in BARS.items():
        for i, (x0, y0, x1, y1, klass) in enumerate(rows):
            sid = f'bar-{key}-{i}'
            parts.append(
                f'<rect id="{sid}" x="{x0}" y="{y0}" width="{x1 - x0}" height="{y1 - y0}" '
                f'fill="{PAL[klass]}" stroke="#222" stroke-width="0.75"/>'
            )
            add_shape({'id': sid, 'type': 'color-bar', 'redrawn': True, 'new_id': sid,
                       'box': [x0, y0, x1, y1], 'klass': klass, 'hex': PAL[klass]})
            bar_n += 1
    parts.append('</g>')

    parts.append('<g id="header-wings">')
    for h in HEADERS:
        fill = PAL[h['klass']]
        for i, d in enumerate(h['wings']):
            sid = f'wing-{h["id"]}-{i}'
            parts.append(f'<path id="{sid}" d="{d}" fill="{fill}" stroke="#202020" stroke-width="0.7"/>')
            add_shape({'id': sid, 'type': 'wing', 'redrawn': True, 'new_id': sid, 'd': d, 'klass': h['klass'], 'grade': 'B'})
        parts.append(f'<path id="arc-{h["id"]}" d="{h["arc"]}" fill="none" stroke="#202020" stroke-width="1"/>')
        add_shape({'id': f'arc-{h["id"]}', 'type': 'header-arc', 'redrawn': True, 'new_id': f'arc-{h["id"]}',
                   'd': h['arc'], 'grade': 'B'})
        for i, (cx, cy, r) in enumerate(h['circles']):
            sid = f'head-{h["id"]}-{i}'
            _spin(parts, sid, cx, cy, r, fill, 1.1, '#202020', 1 if i == 0 else -1)
            nspin += 1
            circles.append((cx, cy, r))
            add_shape({'id': sid, 'type': 'circle', 'redrawn': True, 'new_id': sid, 'cx': cx, 'cy': cy, 'r': r, 'klass': h['klass']})
    parts.append('</g>')

    parts.append('<g id="sensory">')
    for i, (cx, cy, r) in enumerate(SENSORY):
        sid = f'sensory-{i}'
        _spin(parts, sid, cx, cy, r, '#f7f4ea', 1.0, '#202020', 1 if i % 2 == 0 else -1)
        circles.append((cx, cy, r))
        add_shape({'id': sid, 'type': 'circle', 'redrawn': True, 'new_id': sid, 'cx': cx, 'cy': cy, 'r': r,
                   'why': '感官圆。圈内未清字只留紧框，不新写'})
    for i, (cx, cy, r, klass) in enumerate(HALVES):
        sid = f'half-{i}'
        x0, x1 = cx - r, cx + r
        # y 向下：左点到右点、sweep 0 经过上方。
        half_text = ''
        if i == 0:
            half_text = (
                '<text x="61" y="523" text-anchor="middle" dominant-baseline="central" '
                'font-size="8.5" font-weight="700" fill="#111" stroke="#fff" stroke-width="0.45" paint-order="stroke">阳</text>'
            )
        elif i == 1:
            half_text = (
                '<text x="168" y="521" text-anchor="middle" dominant-baseline="central" '
                'font-size="8.5" font-weight="700" fill="#111" stroke="#fff" stroke-width="0.45" paint-order="stroke">阴</text>'
            )
        parts.append(
            f'<g id="{sid}" data-spin="1" data-kind="spec" data-turns="{1 if i % 2 == 0 else -1}" data-cx="{cx}" data-cy="{cy}">'
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#f7f4ea" stroke="#202020" stroke-width="1"/>'
            f'<path d="M{x0} {cy} A{r} {r} 0 0 1 {x1} {cy} Z" fill="{PAL[klass]}" stroke="#202020" stroke-width="0.6"/>'
            f'<path d="M{x0} {cy} H{x1}" fill="none" stroke="#202020" stroke-width="0.8"/>'
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#4a3b24" stroke-width="0.8" stroke-dasharray="3 5" opacity="0.75"/>'
            f'{half_text}'
            f'</g>'
        )
        circles.append((cx, cy, r))
        add_shape({'id': sid, 'type': 'half-circle', 'redrawn': True, 'new_id': sid, 'cx': cx, 'cy': cy, 'r': r, 'klass': klass})
    parts.append('</g>')

    parts.append('<g id="periph">')
    for i, (cx, cy, r, klass) in enumerate(PERIPH):
        sid = f'periph-{i}'
        _spin(parts, sid, cx, cy, r, PAL[klass], 0.8, '#202020', 1 if i % 2 == 0 else -1)
        circles.append((cx, cy, r))
        add_shape({'id': sid, 'type': 'circle', 'redrawn': True, 'new_id': sid, 'cx': cx, 'cy': cy, 'r': r, 'klass': klass,
                   'why': '外围彩圆。圈内字未全辨，不自填脏腑名'})
    parts.append('</g>')

    parts.append('<g id="dot-brackets" fill="none" stroke="#202020" stroke-width="0.8">')
    for i, d in enumerate(DOT_BRACKETS):
        parts.append(f'<path id="dot-bracket-{i}" d="{d}"/>')
        add_shape({'id': f'dot-bracket-{i}', 'type': 'curve', 'redrawn': True, 'new_id': f'dot-bracket-{i}', 'd': d, 'grade': 'B'})
    parts.append('</g>')

    parts.append('<g id="table-dots">')
    seen = []
    for key, rows in TABLE_DOTS.items():
        for i, (cx, cy, klass) in enumerate(rows):
            if any((cx - a) ** 2 + (cy - b) ** 2 < 9 for a, b, _r in seen):
                continue
            r = 5.0 if klass == 'T' else 4.4
            sid = f'tdot-{key}-{i}'
            _spin(parts, sid, cx, cy, r, PAL[klass], 0.7, '#202020', 1 if i % 2 == 0 else -1)
            circles.append((cx, cy, r))
            seen.append((cx, cy, r))
            add_shape({'id': sid, 'type': 'dot', 'redrawn': True, 'new_id': sid, 'cx': cx, 'cy': cy, 'r': r, 'klass': klass})
    parts.append('</g>')

    named = []
    parts.append('<g id="named-dots">')
    for name, dots in NAMED_DOTS.items():
        for i, ((cx, cy), klass, r) in enumerate(dots):
            sid = f'ndot-{name}-{i}'
            _spin(parts, sid, cx, cy, r, PAL[klass], 0.45, '#202020', 1)
            circles.append((cx, cy, r))
            named.append({'name': name, 'x': cx, 'y': cy, 'r': r, 'klass': klass, 'hex': PAL[klass], 'id': sid})
            add_shape({'id': sid, 'type': 'acupoint-dot', 'redrawn': True, 'new_id': sid,
                       'name': name, 'cx': cx, 'cy': cy, 'r': r, 'klass': klass})
    for i, ((cx, cy), r) in enumerate(LEADS):
        sid = f'lead-{i}'
        _spin(parts, sid, cx, cy, r, PAL['T'], 0.7, '#202020', -1)
        circles.append((cx, cy, r))
        add_shape({'id': sid, 'type': 'lead-node', 'redrawn': True, 'new_id': sid, 'cx': cx, 'cy': cy, 'r': r,
                   'why': '引线节点，不绑穴名。巨阙不使用 (328.6,211.4)，照海不使用 (401,458)'})
    parts.append('</g>')

    parts.append(
        '<g id="wuxing-wheel" data-spin="1" data-kind="spec" data-turns="1" data-cx="260" data-cy="512">'
        '<circle id="wuxing-outer" cx="260" cy="512" r="22" fill="#f7f4ea" stroke="#202020" stroke-width="1"/>'
        '<path id="w-top" fill="#4c8447" d="M255 493 C258 490 263 491 265 495 C268 499 268 502 265 505 L253 505 C250 501 252 496 255 493 Z"/>'
        '<path id="w-left" fill="#a3b9af" d="M240 505 C244 502 250 505 254 508 L253 517 C249 522 243 521 239 518 C238 513 238 509 240 505 Z"/>'
        '<path id="w-right" fill="#d52c29" d="M267 507 C272 503 279 505 281 509 C283 514 281 520 277 522 C273 524 269 521 266 518 Z"/>'
        '<path id="w-bottom" fill="#559cbe" d="M254 521 C258 518 261 519 264 521 C268 524 269 529 265 532 C261 534 255 533 252 530 C249 526 250 524 254 521 Z"/>'
        '<path id="w-inner-lines" fill="none" stroke="#202020" stroke-width="0.85" d="M240 504 L280 504 M239 506 L274 530 M245 530 L280 505 M260 491 L252 505 M260 491 L267 505 M252 520 L247 530 M267 520 L271 528"/>'
        '<path id="w-center" fill="#eee633" stroke="#202020" stroke-width="1" d="M256 505 Q260 503 264 506 L268 512 Q268 516 263 519 L259 521 L253 518 Q250 515 252 510 Z"/>'
        '</g>'
    )
    circles.append((260, 512, 22))
    add_shape({'id': 'wuxing-wheel', 'type': 'wheel', 'redrawn': True, 'new_id': 'wuxing-wheel',
               'cx': 260, 'cy': 512, 'r': 22, 'box': [226, 482, 298, 546],
               'why': '绿上、灰青左、红右、蓝下、黄心。不是五个等角外瓣。轮外字待核'})

    # 右下六行窄表。第 4 行合并，不画 569/575。
    ly = [451, 466, 479, 493, 506, 519, 533]
    left_k = ['B', 'A', 'G', None, 'R', 'Y']
    right_k = ['G', 'R', 'Y', 'Y', 'B', 'A']
    parts.append('<g id="legend-table">')
    parts.append('<rect id="legend-frame" x="555" y="451" width="39" height="82" fill="#f7f4ea" stroke="#202020" stroke-width="0.9"/>')
    for i in range(6):
        y0, y1 = ly[i], ly[i + 1]
        if i == 3:
            parts.append(f'<rect id="legend-merge" x="555" y="{y0}" width="34" height="{y1 - y0}" fill="none" stroke="#202020" stroke-width="0.6"/>')
        else:
            parts.append(f'<rect id="legend-tx-{i}a" x="555" y="{y0}" width="14" height="{y1 - y0}" fill="none" stroke="#202020" stroke-width="0.55"/>')
            parts.append(f'<rect id="legend-tx-{i}b" x="575" y="{y0}" width="14" height="{y1 - y0}" fill="none" stroke="#202020" stroke-width="0.55"/>')
            parts.append(f'<rect id="legend-bar-{i}a" x="569" y="{y0}" width="6" height="{y1 - y0}" fill="{PAL[left_k[i]]}" stroke="#202020" stroke-width="0.45"/>')
        parts.append(f'<rect id="legend-bar-{i}b" x="589" y="{y0}" width="5" height="{y1 - y0}" fill="{PAL[right_k[i]]}" stroke="#202020" stroke-width="0.45"/>')
    parts.append('</g>')
    add_shape({'id': 'legend-table', 'type': 'grid', 'redrawn': True, 'new_id': 'legend-table',
               'box': [555, 451, 594, 533], 'y': ly, 'x': [555, 569, 575, 589, 594],
               'why': '6 行窄彩条。格内小字未辨，只留紧框，不按六经填写'})

    parts.append(
        '<path id="path-dash" d="M450 525 H501" fill="none" stroke="#202020" stroke-width="1" stroke-dasharray="6 2"/>'
        '<path id="path-solid" d="M450 531 H501" fill="none" stroke="#202020" stroke-width="1"/>'
    )
    add_shape({'id': 'path-legend', 'type': 'line', 'redrawn': True, 'new_id': 'path-dash',
               'why': '路径图例样线。字用已确认的路径：、可行、破滞'})

    parts.append('<circle id="taiji-edge" cx="404" cy="296" r="20" fill="#f7f4ea" stroke="#202020" stroke-width="0.8"/>')
    add_shape({'id': 'taiji-interior', 'type': 'curves', 'redrawn': False, 'new_id': 'taiji-edge',
               'box': [384, 276, 424, 316],
               'why': 'C 级。中心约 r20 的边已画。内部 S 曲线在此分辨率下控制点不可靠，不编造太极符号，原盘仍叠在旋转层'})

    for i, (x0, y0, x1, y1) in enumerate(WHEEL_TEXT):
        add_shape({'id': f'wheel-text-{i}', 'type': 'text-pending', 'redrawn': False,
                   'box': [x0, y0, x1, y1], 'why': '轮外手写不够清晰，待核，不贴五行标签'})
    parts.append('</g>')
    return ''.join(parts), inv, circles, named, bar_n
