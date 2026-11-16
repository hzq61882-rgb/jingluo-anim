/* B/4 ring-chart pipes. Uses JingluoFlow and the page's existing paths.
 * Particles stay on those paths (stroke mask or annulus). No new shortcuts.
 */
(function () {
  const WXPOS = { 木: [502, 422], 火: [502, 602], 土: [92, 426], 金: [92, 602], 水: [502, 242] };
  const WXCOL = { 木: '#3fdc5a', 火: '#ff3b30', 土: '#ffd60a', 金: '#ffffff', 水: '#2f80ff' };
  const swarms = [];
  const rings = [];
  let installed = false;
  let boxCache = null;
  let boxW = -1;
  const grads = {};

  function defs() { return document.querySelector('#stage defs'); }

  function wxAt(x, y) {
    let best = null;
    let bd = 30;
    for (const k in WXPOS) {
      const p = WXPOS[k];
      const d = Math.hypot(x - p[0], y - p[1]);
      if (d < bd) { bd = d; best = k; }
    }
    return best ? WXCOL[best] : null;
  }

  function grad(color) {
    const key = String(color).replace('#', '');
    if (grads[key]) return 'url(#' + grads[key] + ')';
    const id = 'pgx_' + key;
    grads[key] = id;
    const rg = el('radialGradient', { id: id }, defs());
    el('stop', { offset: '0', 'stop-color': '#ffffff' }, rg);
    el('stop', { offset: '0.38', 'stop-color': color }, rg);
    el('stop', { offset: '1', 'stop-color': color, 'stop-opacity': '0' }, rg);
    return 'url(#' + id + ')';
  }

  function paint(node, color, ink) {
    const white = !color || String(color).toLowerCase() === '#ffffff';
    if (ink || white) {
      node.setAttribute('fill', '#ffffff');
      node.setAttribute('stroke', '#140a1c');
      node.setAttribute('stroke-width', '0.45');
    } else {
      node.setAttribute('fill', grad(color));
    }
  }

  function addSwarm(parent, spec) {
    const maskId = 'msk_' + spec.id;
    const mask = el('mask', { id: maskId, maskUnits: 'userSpaceOnUse' }, defs());
    el('path', {
      d: spec.d, fill: 'none', stroke: '#fff', 'stroke-width': spec.width,
      'stroke-linecap': 'round', 'stroke-linejoin': 'round',
    }, mask);
    const g = el('g', {
      mask: 'url(#' + maskId + ')', class: 'pipe-swarm', 'data-pipe': spec.id, 'pointer-events': 'none',
    }, parent);
    const path = el('path', { d: spec.d, fill: 'none', stroke: 'none' }, g);
    const len = path.getTotalLength() || 1;
    const n = spec.n || Math.max(4, Math.min(8, Math.round(len / 70)));
    const dots = [];
    for (let i = 0; i < n; i++) {
      const c = el('circle', { r: spec.r, class: 'fx-crowd' }, g);
      paint(c, spec.color, spec.ink);
      dots.push(c);
    }
    let lead = null;
    if (spec.lead) {
      const lg = el('g', { class: 'fx-lead' }, g);
      const tail = [];
      for (let j = 0; j < 7; j++) {
        const e = el('circle', { r: (2.4 * (1 - j / 8)).toFixed(2) }, lg);
        paint(e, spec.color, spec.ink);
        tail.push(e);
      }
      const head = el('circle', { r: spec.ink ? 3.3 : 4.0 }, lg);
      paint(head, spec.color, spec.ink);
      const core = el('circle', { r: 1.45, fill: '#ffffff', stroke: spec.ink ? '#140a1c' : spec.color, 'stroke-width': 0.6 }, lg);
      lead = { tail: tail, head: head, core: core };
    }
    const half = spec.width * 0.5;
    const amp = Math.min(spec.amp, Math.max(0, half - spec.r - 0.35));
    swarms.push({
      id: spec.id, path: path, len: len, dots: dots, lead: lead, g: g,
      amp: amp, laps: Math.max(1, Math.round(spec.laps || 2)),
      leadLaps: Math.max(1, Math.round(spec.leadLaps || spec.laps || 1)),
      mode: spec.mode, clock: spec.clock || 'main', r: spec.r,
    });
  }

  function addRing(c, i) {
    const col = wxAt(c.x, c.y) || c.c || '#f7f8fb';
    const ink = !c.c && !wxAt(c.x, c.y);
    const R0 = c.r;
    const maskId = 'ann_' + i;
    const mask = el('mask', { id: maskId, maskUnits: 'userSpaceOnUse' }, defs());
    el('circle', { cx: c.x, cy: c.y, r: (R0 + 2.2).toFixed(2), fill: '#fff' }, mask);
    el('circle', { cx: c.x, cy: c.y, r: Math.max(0.4, R0 - 2.2).toFixed(2), fill: '#000' }, mask);
    const g = el('g', {
      mask: 'url(#' + maskId + ')', class: 'pipe-swarm', 'data-ring': i, 'pointer-events': 'none',
    }, $('L_rim'));
    const n = R0 > 30 ? 28 : R0 > 16 ? 18 : 10;
    const dots = [];
    for (let k = 0; k < n; k++) {
      const node = el('circle', { r: R0 > 30 ? 1.5 : 1.2, class: 'fx-crowd' }, g);
      paint(node, col, ink || col === '#ffffff');
      dots.push(node);
    }
    rings.push({ c: c, dots: dots, g: g, ink: ink });
  }

  function boxes() {
    const svg = $('stage');
    const w = svg.clientWidth || 0;
    if (boxCache && boxW === w && w > 0) return boxCache;
    boxW = w;
    boxCache = [];
    if (!w) return boxCache;
    const s = svg.getBoundingClientRect();
    const vb = svg.viewBox.baseVal;
    const sx = s.width ? vb.width / s.width : 1;
    const sy = s.height ? vb.height / s.height : 1;
    document.querySelectorAll('#L_txt text, #legend text').forEach(function (t) {
      const a = t.getBoundingClientRect();
      if (a.width < 1 || a.height < 1) return;
      boxCache.push({
        x: (a.left - s.left) * sx - 1.5,
        y: (a.top - s.top) * sy - 1.5,
        x2: (a.right - s.left) * sx + 1.5,
        y2: (a.bottom - s.top) * sy + 1.5,
      });
    });
    return boxCache;
  }

  function hit(x, y, bb) {
    for (let i = 0; i < bb.length; i++) {
      const b = bb[i];
      if (x >= b.x && x <= b.x2 && y >= b.y && y <= b.y2) return true;
    }
    return false;
  }

  function put(node, x, y, op) {
    node.setAttribute('cx', x.toFixed(2));
    node.setAttribute('cy', y.toFixed(2));
    node.setAttribute('opacity', Math.max(0, Math.min(1, op)).toFixed(3));
  }

  function placeSwarm(s, t, bb) {
    const F = JingluoFlow;
    s.dots.forEach(function (dot, i) {
      const u = F.uOf(t, CYCLE, s.laps, i / s.dots.length);
      const tr = F.travel(u, s.mode);
      const spin = 2 * Math.PI * (3 * tr.s + i * 0.17);
      const q = F.sample(s.path, s.len, tr.s, s.amp, spin);
      const dist = Math.hypot(q.x - q.cx, q.y - q.cy);
      dot.setAttribute('data-dist', dist.toFixed(3));
      let op = tr.fade * (0.62 + 0.38 * (0.5 + 0.5 * Math.sin(spin)));
      if (hit(q.x, q.y, bb)) op = 0;
      put(dot, q.x, q.y, op);
    });
    if (!s.lead) return;
    const u = F.uOf(t, CYCLE, s.leadLaps, 0.08);
    const tr = F.travel(u, s.mode);
    const q = F.sample(s.path, s.len, tr.s, 0, 0);
    let hop = tr.fade;
    if (hit(q.x, q.y, bb)) hop = 0;
    put(s.lead.head, q.x, q.y, hop * 0.95);
    put(s.lead.core, q.x, q.y, hop);
    s.lead.head.setAttribute('data-dist', '0');
    s.lead.core.setAttribute('data-dist', '0');
    s.lead.tail.forEach(function (e, j) {
      const s2 = F.behind(tr.s, tr.dir, (j + 1) * 6.5, s.len, s.mode);
      const q2 = F.sample(s.path, s.len, s2, 0, 0);
      let op = hop * (0.72 * (1 - (j + 1) / (s.lead.tail.length + 2)));
      if (hit(q2.x, q2.y, bb)) op = 0;
      e.setAttribute('data-dist', '0');
      put(e, q2.x, q2.y, op);
    });
  }

  function placeRing(r, t, bb) {
    const c = r.c;
    const n = r.dots.length;
    const F = JingluoFlow;
    r.dots.forEach(function (dot, i) {
      const u = F.uOf(t, CYCLE, c.rev, i / n + ((c.a0 || 0) / 360));
      const ang = (c.dir || 1) * u * Math.PI * 2;
      const x = c.x + c.r * Math.cos(ang);
      const y = c.y + c.r * Math.sin(ang);
      const dist = Math.abs(Math.hypot(x - c.x, y - c.y) - c.r);
      dot.setAttribute('data-dist', dist.toFixed(3));
      const tw = 0.7 + 0.3 * F.twinkle(t, CYCLE, c.rev, i / n);
      let op = tw;
      if (hit(x, y, bb)) op = 0;
      put(dot, x, y, op);
    });
  }

  function draw(t, tb) {
    arcObjs.forEach(function (a) {
      a.dash.setAttribute('stroke-dashoffset', (-15 * 30 * t / CYCLE).toFixed(2));
    });
    wxSegs.forEach(function (s) {
      s.dash.setAttribute('stroke-dashoffset', (-13 * 9 * t / CYCLE).toFixed(2));
    });
    qjObjs.forEach(function (q) {
      const k = q.main ? 26 : 14;
      const per = q.main ? 13 : 10;
      q.dash.setAttribute('stroke-dashoffset', (-k * per * t / CYCLE).toFixed(2));
    });
    const bb = boxes();
    swarms.forEach(function (s) { placeSwarm(s, s.clock === 'black' ? tb : t, bb); });
    rings.forEach(function (r) { placeRing(r, t, bb); });
    ORDER.forEach(function (k, i) {
      const base = JingluoFlow.glowAmp(t, i, SLOT, ORDER.length);
      const tw = JingluoFlow.twinkle(t, CYCLE, 12, i * 0.13);
      const want = base * (0.42 + 0.58 * tw);
      const o = nodeObjs[k];
      const cur = parseFloat(o.ring.getAttribute('opacity')) || 0;
      if (want > cur + 0.02) {
        o.ring.setAttribute('opacity', want.toFixed(3));
        if (cur < 0.05) o.ring.setAttribute('r', (R + 2).toFixed(2));
      }
    });
  }

  function audit() {
    let n = 0;
    let outside = 0;
    let maxDist = 0;
    let labelHits = 0;
    let visible = 0;
    const bb = boxes();
    function check(node, limit) {
      n++;
      const x = +node.getAttribute('cx');
      const y = +node.getAttribute('cy');
      const dist = +node.getAttribute('data-dist') || 0;
      const op = +node.getAttribute('opacity') || 0;
      if (dist > limit) outside++;
      if (dist > maxDist) maxDist = dist;
      if (op > 0.2 && hit(x, y, bb)) labelHits++;
      if (op > 0.3) visible++;
    }
    swarms.forEach(function (s) {
      const limit = s.amp + 0.2;
      s.dots.forEach(function (d) { check(d, limit); });
      if (s.lead) {
        check(s.lead.head, 0.2);
        check(s.lead.core, 0.2);
        s.lead.tail.forEach(function (e) { check(e, 0.2); });
      }
    });
    rings.forEach(function (r) {
      r.dots.forEach(function (d) { check(d, 0.35); });
    });
    return {
      n: n, outside: outside, maxDist: maxDist, labelHits: labelHits, visible: visible,
      rings: rings.length, swarms: swarms.length, circles: (typeof CIR !== 'undefined' ? CIR.length : 0),
    };
  }

  function install() {
    if (installed) return;
    installed = true;
    arcObjs.forEach(function (a, i) {
      addSwarm($('L_arc'), {
        id: 'arc' + i, d: a.path.getAttribute('d'), color: '#f0a04a', width: 8,
        n: 28, amp: 1.7, r: 1.4, laps: 2, leadLaps: 1, mode: 'fade', lead: true,
      });
    });
    segObjs.forEach(function (s, i) {
      addSwarm($('L_mer'), {
        id: 'mer' + i, d: s.path.getAttribute('d'), color: '#ffd34d', width: 6,
        amp: 1.15, r: 1.2, laps: 2, leadLaps: 1, mode: 'fade', lead: false,
      });
    });
    BL.solid.forEach(function (b, i) {
      const isU = b.n === 'U_L' || b.n === 'U_R';
      addSwarm(gS, {
        id: 'bs' + i, d: b.d, color: '#ffffff', width: 4.4,
        n: isU ? 16 : undefined, amp: 0.55, r: 1.05, laps: 2, leadLaps: 1,
        mode: isU ? 'ping' : 'fade', lead: isU, ink: true, clock: 'black',
      });
    });
    BL.dashed.forEach(function (b, i) {
      addSwarm(gD, {
        id: 'bd' + i, d: b.d, color: '#d8ecff', width: 4.4,
        n: 5, amp: 0.5, r: 1.1, laps: 2, mode: 'fade', lead: false, clock: 'black',
      });
    });
    CIR.forEach(function (c, i) { addRing(c, i); });

    const lg = $('legend');
    const rect = lg.querySelector('rect');
    if (rect) rect.setAttribute('height', '86');
    const y = 52 + 4 * 15;
    el('line', { x1: 460, y1: y, x2: 486, y2: y, stroke: '#ffb15a', 'stroke-width': 2.2, 'stroke-linecap': 'round' }, lg);
    el('circle', { cx: 468, cy: y, r: 1.7, fill: '#fff7ea', stroke: '#f0a04a', 'stroke-width': 0.6 }, lg);
    const tx = el('text', { x: 492, y: y + 3.5, 'font-size': 9.5, fill: '#2a1338' }, lg);
    tx.textContent = '管内同色粒子';

    const note = document.querySelector('.note');
    if (note && note.textContent.indexOf('管内同色') < 0) {
      note.insertAdjacentHTML('beforeend',
        '<br>增强：同色光点只在原有色带、弧线、黑线和圆周转，遮罩卡在笔划里，不另开穿越空白的线。下方两条 U 形细线原图没有箭头，领头亮点（白芯加尾迹）沿已经描好的线往返，这是示意假定。圆周流动和中心放射是图示，不表示疗效。脏腑小圆在气血流过之后继续闪，次数整除 24 秒。');
    }
  }

  function bindControls() {
    install();
    const orig = window.renderAt;
    window.renderAt = function (t, tb) {
      if (tb === undefined) tb = t;
      orig(t, tb);
      const tt = JingluoFlow.wrap(t, CYCLE);
      const ttb = JingluoFlow.wrap(tb, CYCLE);
      draw(tt, ttb);
    };
    const clock = new JingluoFlow.FlowClock(CYCLE);
    JingluoRing.clock = clock;
    const video = /[?&]video=1/.test(location.search);
    if (video) document.body.classList.add('video');

    function blkVis() {
      const on = $('tg_blk').checked;
      BLK.style.display = on ? '' : 'none';
      gS.style.display = $('tg_bs').checked ? '' : 'none';
      gD.style.display = $('tg_bd').checked ? '' : 'none';
      $('tg_bs').disabled = !on;
      $('tg_bd').disabled = !on;
    }
    function ringVis() {
      const on = $('tg_ring').checked;
      RING.style.display = on ? '' : 'none';
      RIM.style.display = $('tg_rim').checked ? '' : 'none';
      RAD.style.display = $('tg_rad').checked ? '' : 'none';
      $('tg_rim').disabled = !on;
      $('tg_rad').disabled = !on;
    }
    $('btnPlay').onclick = function () {
      clock.playing = !clock.playing;
      $('btnPlay').textContent = clock.playing ? '⏸ 暂停' : '▶ 播放';
    };
    $('selSpeed').onchange = function (e) { clock.speed = parseFloat(e.target.value) || 1; };
    $('scrub').oninput = function (e) { window.seek(parseFloat(e.target.value)); };
    $('bspeed').oninput = function (e) {
      clock.bspeed = parseFloat(e.target.value) || 0;
      $('bspeedV').textContent = clock.bspeed.toFixed(1) + '×';
    };
    ['tg_blk', 'tg_bs', 'tg_bd'].forEach(function (id) { $(id).onchange = blkVis; });
    ['tg_ring', 'tg_rim', 'tg_rad'].forEach(function (id) { $(id).onchange = ringVis; });
    ['mer', 'arc', 'wx', 'qj', 'yy'].forEach(function (k) {
      $('tg_' + k).onchange = function (e) {
        L[k].style.display = e.target.checked ? '' : 'none';
        if (k === 'mer') L.nodes.style.display = e.target.checked ? '' : 'none';
      };
    });
    $('tg_pipe').onchange = function (e) {
      document.querySelectorAll('.pipe-swarm').forEach(function (g) {
        g.style.display = e.target.checked ? '' : 'none';
      });
    };
    $('tg_quiet').onchange = function (e) { document.body.classList.toggle('quiet', e.target.checked); };
    $('tg_contrast').onchange = function (e) {
      document.body.classList.toggle('hc', e.target.checked);
      const rect = $('legend').querySelector('rect');
      if (rect) rect.setAttribute('fill-opacity', e.target.checked ? '0.96' : '0.82');
    };
    window.seek = function (sec) {
      clock.seek(sec);
      window.renderAt(clock.t, clock.tb);
      if ($('scrub')) $('scrub').value = JingluoFlow.wrap(clock.t, CYCLE).toFixed(2);
    };
    const mq = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)');
    if (mq && mq.matches) {
      document.body.classList.add('quiet');
      $('tg_quiet').checked = true;
    }
    function frame(ts) {
      clock.tick(ts);
      window.renderAt(clock.t, clock.tb);
      if (!video && $('scrub')) $('scrub').value = JingluoFlow.wrap(clock.t, CYCLE).toFixed(2);
      requestAnimationFrame(frame);
    }
    if (!video) requestAnimationFrame(frame);
    else window.renderAt(0, 0);
  }

  window.JingluoRing = { install: install, draw: draw, audit: audit, bindControls: bindControls, boxes: boxes };
})();
