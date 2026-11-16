/* Attach pipe particles to an existing chart's flow items.
 * Uses JingluoFlow. Does not invent paths or change point order.
 * Closed strokes loop. Open strokes fade at the ends. ping is not applied here.
 */
(function () {
  const WX = { 木: '#3fdc5a', 火: '#ff3b30', 土: '#ffd60a', 金: '#ffffff', 水: '#2f80ff' };
  const STYLE = { gold: '#ffd34d', band: '#fff4cc', solid: '#e8fdff', dashed: '#ffd0ea', faint: '#e2ccff' };
  let swarms = [];
  let pulses = [];
  let meta = null;
  const grads = {};

  function defs() {
    return document.querySelector('#stage defs') || document.querySelector('svg defs');
  }
  function colorOf(it) {
    if (it.color && WX[it.color]) return WX[it.color];
    if (it.color) return it.color;
    return STYLE[it.style] || '#ffd34d';
  }
  function grad(color) {
    const key = String(color).replace('#', '');
    if (grads[key]) return 'url(#' + grads[key] + ')';
    const id = 'bkp_' + key;
    grads[key] = id;
    const rg = el('radialGradient', { id: id }, defs());
    el('stop', { offset: '0', 'stop-color': '#ffffff' }, rg);
    el('stop', { offset: '0.4', 'stop-color': color }, rg);
    el('stop', { offset: '1', 'stop-color': color, 'stop-opacity': '0' }, rg);
    return 'url(#' + id + ')';
  }
  function paint(node, color) {
    const light = !color || String(color).toLowerCase() === '#ffffff' || String(color).toLowerCase() === '#e8fdff';
    if (light) {
      node.setAttribute('fill', '#ffffff');
      node.setAttribute('stroke', '#140a1c');
      node.setAttribute('stroke-width', '0.4');
    } else node.setAttribute('fill', grad(color));
  }
  function hold(t, id) {
    const F = JingluoFlow;
    const tt = F.wrap(t, meta.cycle);
    const steps = meta.steps || [];
    const starts = meta.starts || [];
    let on = false;
    let until = meta.cycle;
    steps.forEach(function (s, i) {
      if (!s.on || s.on.indexOf(id) < 0) return;
      const a = starts[i];
      const b = a + s.dur;
      if (tt >= a && tt < b) on = true;
      let dt = a - tt;
      if (dt < 0) dt += meta.cycle;
      if (dt < until) until = dt;
    });
    if (on) return { on: true, amp: 1 };
    const fade = 1.2;
    const amp = until < fade ? 0.7 * (until / fade) : 0.7;
    return { on: false, amp: amp };
  }

  function install(items, opts) {
    meta = opts;
    swarms = [];
    pulses = [];
    items.forEach(function (o, idx) {
      const it = o.it;
      if (!it) return;
      if (it.type === 'pulse') {
        if (o.ring) pulses.push(o);
        return;
      }
      if (!o.dash) return;
      const d = o.dash.getAttribute('d');
      if (!d) return;
      const len0 = o.len || o.dash.getTotalLength() || 0;
      if (len0 < 8) return;
      const color = colorOf(it);
      const width = Math.max(5.2, (+it.width || 3) + 2.2);
      const pr = 1.15;
      const amp = Math.min(1.05, Math.max(0, width * 0.5 - pr - 0.4));
      const maskId = 'bmsk_' + (it.id || idx);
      const mask = el('mask', { id: maskId, maskUnits: 'userSpaceOnUse' }, defs());
      el('path', {
        d: d, fill: 'none', stroke: '#fff', 'stroke-width': width,
        'stroke-linecap': 'round', 'stroke-linejoin': 'round'
      }, mask);
      const parent = o.g || o.dash.parentNode;
      const g = el('g', { mask: 'url(#' + maskId + ')', class: 'pipe-swarm', 'data-pipe': it.id || ('p' + idx), 'pointer-events': 'none' }, parent);
      const path = el('path', { d: d, fill: 'none', stroke: 'none' }, g);
      const len = path.getTotalLength() || 1;
      const n = Math.max(6, Math.min(28, Math.round(len / 22)));
      const dots = [];
      for (let i = 0; i < n; i++) {
        const c = el('circle', { r: pr, class: 'fx-crowd' }, g);
        paint(c, color);
        dots.push(c);
      }
      let lead = null;
      if (len >= 48) {
        const tail = [];
        for (let j = 0; j < 6; j++) {
          const e = el('circle', { r: (2.1 * (1 - j / 8)).toFixed(2), class: 'fx-lead' }, g);
          paint(e, color);
          tail.push(e);
        }
        const head = el('circle', { r: 3.4, class: 'fx-lead' }, g);
        paint(head, color);
        const core = el('circle', { r: 1.3, fill: '#ffffff', stroke: color, 'stroke-width': 0.55, class: 'fx-lead' }, g);
        lead = { tail: tail, head: head, core: core };
      }
      const laps = Math.max(1, Math.round(it.laps || JingluoFlow.laps(it.v || 26, meta.cycle, len)));
      swarms.push({
        it: it, path: path, len: len, dots: dots, lead: lead, g: g,
        amp: amp, laps: laps, leadLaps: laps,
        mode: it.closed ? 'loop' : 'fade',
        clock: it.group === 'black' ? 'black' : 'main'
      });
    });
    const note = document.getElementById('note');
    if (note && note.textContent.indexOf('不是疗效') < 0) {
      note.insertAdjacentHTML('beforeend', '<br>增强：同色粒子和白芯领头只沿原来的折线走。闭合的环循环，开口的线在两端淡出，不另画穿越空白的线，也不把无箭头的线改成往返。有箭头的仍按原来的点序。这是图示，不是疗效。');
    }
  }

  function put(node, x, y, op) {
    node.setAttribute('cx', x.toFixed(2));
    node.setAttribute('cy', y.toFixed(2));
    node.setAttribute('opacity', Math.max(0, Math.min(1, op)).toFixed(3));
  }

  function draw(t, tb) {
    if (!meta) return;
    const F = JingluoFlow;
    swarms.forEach(function (s) {
      const tt = s.clock === 'black' ? tb : t;
      s.dots.forEach(function (dot, i) {
        const u = F.uOf(tt, meta.cycle, s.laps, i / s.dots.length);
        const tr = F.travel(u, s.mode);
        const spin = 2 * Math.PI * (3 * tr.s + i * 0.17);
        const q = F.sample(s.path, s.len, tr.s, s.amp, spin);
        dot.setAttribute('data-dist', Math.hypot(q.x - q.cx, q.y - q.cy).toFixed(3));
        let op = tr.fade * (0.62 + 0.38 * (0.5 + 0.5 * Math.sin(spin)));
        put(dot, q.x, q.y, op);
      });
      if (!s.lead) return;
      const u = F.uOf(tt, meta.cycle, s.leadLaps, 0.05);
      const tr = F.travel(u, s.mode);
      const q = F.sample(s.path, s.len, tr.s, 0, 0);
      put(s.lead.head, q.x, q.y, tr.fade * 0.95);
      put(s.lead.core, q.x, q.y, tr.fade);
      s.lead.head.setAttribute('data-dist', '0');
      s.lead.core.setAttribute('data-dist', '0');
      s.lead.tail.forEach(function (e, j) {
        const s2 = F.behind(tr.s, tr.dir, (j + 1) * 6.5, s.len, s.mode);
        const q2 = F.sample(s.path, s.len, s2, 0, 0);
        e.setAttribute('data-dist', '0');
        put(e, q2.x, q2.y, tr.fade * 0.7 * (1 - (j + 1) / 8));
      });
    });
    pulses.forEach(function (o) {
      const g = hold(t, o.it.id);
      if (g.on) return;
      const cur = parseFloat(o.ring.getAttribute('opacity')) || 0;
      if (g.amp > cur + 0.02) o.ring.setAttribute('opacity', g.amp.toFixed(3));
    });
  }

  function audit() {
    let n = 0, outside = 0, maxDist = 0, visible = 0;
    swarms.forEach(function (s) {
      const lim = s.amp + 0.25;
      s.dots.forEach(function (d) {
        n++;
        const dist = +d.getAttribute('data-dist') || 0;
        const op = +d.getAttribute('opacity') || 0;
        if (dist > lim) outside++;
        if (dist > maxDist) maxDist = dist;
        if (op > 0.3) visible++;
      });
      if (s.lead) {
        [s.lead.head, s.lead.core].concat(s.lead.tail).forEach(function (d) {
          n++;
          const dist = +d.getAttribute('data-dist') || 0;
          if (dist > 0.25) outside++;
          if ((+d.getAttribute('opacity') || 0) > 0.3) visible++;
        });
      }
    });
    return { n: n, outside: outside, maxDist: maxDist, visible: visible, swarms: swarms.length, pulses: pulses.length };
  }

  window.JingluoBake = { install: install, draw: draw, audit: audit };
})();
