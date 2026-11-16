/* JingluoFlow — deterministic clock and path sampling.
 * Visuals are a pure function of time. No Math.random, no per-frame velocity.
 *
 * Ideas read from (not copied as libraries):
 * - bangtutorial/bang-motion SKILL.md law 2, commit c1aa65e (MIT)
 * - givemotion/givemotion src/runtime/runtime.js gm.seek, commit a2b02980 (MIT)
 * - heygen-com/hyperframes docs/packages/player.mdx seek + docs/concepts/compositions.mdx
 *   frame render, commit 6e0e03f5 (Apache-2.0). The player package is not bundled.
 * - greensock/gsap-skills skills/gsap-timeline/SKILL.md time/pause, commit aed9cfd (MIT).
 *   GSAP itself is not bundled.
 * - oil-oil/oil-motion SKILL.md scrub / references/runtime.md frame-scrub, commit 07e31f2 (MIT)
 * Pipe clipping follows this repo's B/24 template (mask or clip stays on the stroke).
 */
(function (root) {
  function wrap(t, cycle) {
    if (!cycle) return 0;
    const m = t % cycle;
    return m < 0 ? m + cycle : m;
  }

  function laps(speed, cycle, period) {
    if (!period) return 1;
    const k = Math.round((speed * cycle) / period);
    return Math.max(1, k);
  }

  function uOf(t, cycle, nLaps, offset) {
    const x = (nLaps || 1) * (wrap(t, cycle) / cycle) + (offset || 0);
    return wrap(x, 1);
  }

  /* mode: loop (closed), fade (open, one direction, invisible at the ends),
     ping (open, reverse at the ends — stays on the stroke). */
  function travel(u, mode) {
    const x = wrap(u, 1);
    if (mode === 'ping') {
      const tri = x < 0.5 ? x * 2 : 2 - 2 * x;
      return { s: tri, fade: 1, dir: x < 0.5 ? 1 : -1 };
    }
    let fade = 1;
    if (mode !== 'loop') {
      const e = 0.035;
      if (x < e) fade = x / e;
      else if (x > 1 - e) fade = (1 - x) / e;
    }
    return { s: x, fade: fade, dir: 1 };
  }

  function behind(s, dir, distPx, len, mode) {
    if (!len) return 0;
    let L = s * len - (dir || 1) * distPx;
    if (mode === 'loop') L = wrap(L, len);
    else L = Math.max(0, Math.min(len, L));
    return L / len;
  }

  function sample(pathEl, len, s, amp, spin) {
    if (!pathEl || !len) return { x: 0, y: 0, cx: 0, cy: 0, off: 0 };
    const u = Math.min(1, Math.max(0, s));
    const L = u * len;
    const dL = Math.max(0.8, Math.min(2.5, len * 0.004));
    const p = pathEl.getPointAtLength(Math.min(len, L));
    const p2 = pathEl.getPointAtLength(Math.min(len, L + dL));
    const p1 = pathEl.getPointAtLength(Math.max(0, L - dL));
    let tx = p2.x - p1.x;
    let ty = p2.y - p1.y;
    const mag = Math.hypot(tx, ty) || 1;
    const nx = -ty / mag;
    const ny = tx / mag;
    const off = (amp || 0) * Math.sin(spin || 0);
    return { x: p.x + nx * off, y: p.y + ny * off, cx: p.x, cy: p.y, off: off };
  }

  function twinkle(t, cycle, n, phi) {
    const ph = wrap(t, cycle) / cycle;
    return 0.5 + 0.5 * Math.sin(2 * Math.PI * ((n || 1) * ph + (phi || 0)));
  }

  /* After the flow passes index, the point keeps glowing, then fades in the
     slot before it is due again so t=0 matches t=cycle. Index 0 lights up at
     the wrap; that is the start of its slot, not a seam mismatch. */
  function glowAmp(t, index, slot, n) {
    slot = slot || 2;
    n = n || 12;
    const pos = wrap(t, slot * n) / slot;
    const since = wrap(pos - index, n);
    if (since < 1) return 1;
    if (since < 1.25) return 1 - 0.25 * ((since - 1) / 0.25);
    if (since < n - 1) return 0.75;
    return 0.75 * (1 - (since - (n - 1)));
  }

  function FlowClock(cycle) {
    this.cycle = cycle;
    this.t = 0;
    this.tb = 0;
    this.playing = true;
    this.speed = 1;
    this.bspeed = 1;
    this.last = null;
  }
  FlowClock.prototype.tick = function (ts) {
    if (this.last != null && this.playing) {
      const dt = (ts - this.last) / 1000;
      this.t += dt * this.speed;
      this.tb += dt * this.bspeed;
    }
    this.last = ts;
  };
  FlowClock.prototype.seek = function (sec) {
    const cur = wrap(this.t, this.cycle);
    const next = wrap(+sec, this.cycle);
    const d = next - cur;
    this.t += d;
    this.tb += d;
  };

  const api = {
    wrap: wrap,
    laps: laps,
    uOf: uOf,
    travel: travel,
    behind: behind,
    sample: sample,
    twinkle: twinkle,
    glowAmp: glowAmp,
    FlowClock: FlowClock,
  };
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.JingluoFlow = api;
})(typeof window !== 'undefined' ? window : globalThis);
