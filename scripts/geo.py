"""Polyline helpers used while tracing a scan.

Coordinates stay in the scan's pixel space. ``snap`` rides the dark ink of a
thin line; ``snap_mask`` rides a colour band (a six-channel ribbon, a ring).
"""
from __future__ import annotations

try:
    import numpy as np
except ImportError as exc:
    raise SystemExit('需要 numpy：pip install -r scripts/requirements.txt') from exc


def _pil():
    try:
        from PIL import Image
    except ImportError as exc:
        raise SystemExit('需要 pillow：pip install -r scripts/requirements.txt') from exc
    return Image


def load_lum(path):
    Image = _pil()
    a = np.array(Image.open(path).convert('RGB')).astype(float)
    return a.max(-1) * 0.7 + a.mean(-1) * 0.3


def resample(pts, step=3.0):
    pts = np.asarray(pts, float)
    if len(pts) < 2:
        return pts
    seg = np.hypot(*np.diff(pts, axis=0).T)
    cum = np.r_[0, np.cumsum(seg)]
    if cum[-1] == 0:
        return pts.copy()
    n = max(2, int(cum[-1] / step) + 1)
    s = np.linspace(0, cum[-1], n)
    return np.c_[np.interp(s, cum, pts[:, 0]), np.interp(s, cum, pts[:, 1])]


def smooth(p, w=7, it=2):
    p = p.copy()
    for _ in range(it):
        q = p.copy()
        k = w // 2
        for i in range(1, len(p) - 1):
            a, b = max(0, i - k), min(len(p), i + k + 1)
            q[i] = p[a:b].mean(0)
        p = q
    return p


def snap(lum, pts, maxw=16, dark=95, maxshift=7, step=3.0):
    """Move points to the midline between dark edges, along the normal."""
    p = resample(pts, step)
    height, width = lum.shape
    out = p.copy()
    widths = []
    for i in range(len(p)):
        a = p[max(0, i - 2)]
        b = p[min(len(p) - 1, i + 2)]
        tangent = b - a
        norm = np.hypot(*tangent)
        if norm == 0:
            continue
        nx, ny = -tangent[1] / norm, tangent[0] / norm

        def scan(sign):
            for s in np.arange(0, maxw, 0.5):
                x = int(round(p[i, 0] + sign * nx * s))
                y = int(round(p[i, 1] + sign * ny * s))
                if not (0 <= x < width and 0 <= y < height):
                    return None
                if lum[y, x] < dark:
                    return s
            return None

        x0, y0 = int(round(p[i, 0])), int(round(p[i, 1]))
        if not (0 <= x0 < width and 0 <= y0 < height) or lum[y0, x0] < dark:
            continue
        s1, s2 = scan(1), scan(-1)
        if s1 is None or s2 is None:
            continue
        shift = (s1 - s2) / 2
        if abs(shift) > maxshift:
            continue
        out[i] = p[i] + np.array([nx, ny]) * shift
        widths.append(s1 + s2)
    out[0] = p[0]
    out[-1] = p[-1]
    return smooth(out), (float(np.median(widths)) if widths else 10.0)


def pts_round(p, step=4):
    p = resample(p, step)
    return [[round(float(x), 1), round(float(y), 1)] for x, y in p]


def load_lab(path):
    try:
        from skimage.color import rgb2lab
    except ImportError as exc:
        raise SystemExit('需要 scikit-image：pip install -r scripts/requirements.txt') from exc
    Image = _pil()
    return rgb2lab(np.array(Image.open(path).convert('RGB')))


def colmask(lab, rgb, thr=28):
    from skimage.color import rgb2lab
    centre = rgb2lab(np.array([[rgb]], dtype=np.uint8))[0, 0]
    return np.linalg.norm(lab - centre, axis=-1) < thr


def snap_mask(mask, pts, rad=24, maxshift=24, step=3.0, sm=7, keep_ends=False):
    """Pull a rough polyline onto the midline of a boolean colour mask."""
    p = resample(pts, step)
    height, width = mask.shape
    out = p.copy()
    widths = []
    ok = np.zeros(len(p), bool)
    for i in range(len(p)):
        a = p[max(0, i - 2)]
        b = p[min(len(p) - 1, i + 2)]
        tangent = b - a
        norm = np.hypot(*tangent)
        if norm == 0:
            continue
        nx, ny = -tangent[1] / norm, tangent[0] / norm
        samples = np.arange(-rad, rad + 0.5, 0.5)
        xs = np.round(p[i, 0] + nx * samples).astype(int)
        ys = np.round(p[i, 1] + ny * samples).astype(int)
        valid = (xs >= 0) & (xs < width) & (ys >= 0) & (ys < height)
        hit = np.zeros(len(samples), bool)
        hit[valid] = mask[ys[valid], xs[valid]]
        runs = []
        j = 0
        while j < len(hit):
            if hit[j]:
                k = j
                while k < len(hit) and hit[k]:
                    k += 1
                runs.append((samples[j], samples[k - 1]))
                j = k
            else:
                j += 1
        runs = [r for r in runs if r[1] - r[0] >= 2]
        if not runs:
            continue
        best = min(runs, key=lambda r: 0 if r[0] <= 0 <= r[1] else min(abs(r[0]), abs(r[1])))
        shift = (best[0] + best[1]) / 2
        if abs(shift) > maxshift:
            continue
        out[i] = p[i] + np.array([nx, ny]) * shift
        widths.append(best[1] - best[0])
        ok[i] = True
    if ok.any():
        idx = np.arange(len(p))
        shift = out - p
        for channel in (0, 1):
            shift[:, channel] = np.interp(idx, idx[ok], shift[ok, channel])
        out = p + shift
    if keep_ends:
        out[0] = p[0]
        out[-1] = p[-1]
    return smooth(out, sm, 3), (float(np.median(widths)) if widths else 10.0)
