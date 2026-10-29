(function () {
  'use strict';
  var LABELS = { legitimate: 'Looks safe', suspicious: 'Be careful', phishing: 'Likely phishing' };
  var ADVICE = {
    legitimate: 'No strong phishing signs in what was checked. Only enter passwords on sites you meant to visit.',
    suspicious: 'Parts of this look risky. Do not sign in or download anything unless you can confirm it another way.',
    phishing: 'This matches common phishing patterns. Do not open it or enter any details.'
  };
  var SEV = { high: 'Strong sign', medium: 'Warning', low: 'Minor' };
  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined) n.textContent = text;
    return n;
  }
  function pct(p) { return Math.round(p * 100); }
  function pill(verdict) { return el('span', 'pill ' + verdict, LABELS[verdict] || verdict); }

  async function request(path, options) {
    var res;
    try { res = await fetch(path, options); }
    catch (e) { throw new Error('Could not reach the server. Make sure it is running.'); }
    var data = {};
    try { data = await res.json(); } catch (e) { data = {}; }
    if (!res.ok) throw new Error(data.error || 'Something went wrong. Try again.');
    return data;
  }
  function postJSON(path, body) {
    return request(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  }

  function gauge(p, verdict) {
    var NS = 'http://www.w3.org/2000/svg', len = Math.PI * 80, d = 'M10 95 A80 80 0 0 1 170 95';
    var svg = document.createElementNS(NS, 'svg');
    svg.setAttribute('viewBox', '0 0 180 110');
    svg.setAttribute('class', 'gauge ' + verdict);
    svg.setAttribute('role', 'img');
    svg.setAttribute('aria-label', pct(p) + ' percent chance of phishing');
    var track = document.createElementNS(NS, 'path'); track.setAttribute('d', d); track.setAttribute('class', 'track');
    var fill = document.createElementNS(NS, 'path'); fill.setAttribute('d', d); fill.setAttribute('class', 'fill');
    fill.style.strokeDasharray = String(len);
    fill.style.strokeDashoffset = String(len);
    var text = document.createElementNS(NS, 'text'); text.setAttribute('x', '90'); text.setAttribute('y', '86'); text.textContent = '0%';
    svg.appendChild(track); svg.appendChild(fill); svg.appendChild(text);
    var target = pct(p);
    requestAnimationFrame(function () { requestAnimationFrame(function () { fill.style.strokeDashoffset = String(len * (1 - p)); }); });
    if (reduceMotion) { text.textContent = target + '%'; }
    else {
      var t0 = performance.now();
      (function step(t) {
        var k = Math.min((t - t0) / 800, 1);
        text.textContent = Math.round(target * (1 - Math.pow(1 - k, 3))) + '%';
        if (k < 1) requestAnimationFrame(step);
      })(t0);
    }
    return svg;
  }

  function verdictCard(p, verdict, subline) {
    var card = el('div', 'card verdict ' + verdict);
    var left = el('div');
    left.appendChild(gauge(p, verdict));
    left.appendChild(el('div', 'gauge-cap', 'chance of phishing'));
    var right = el('div');
    right.appendChild(el('h2', '', LABELS[verdict]));
    right.appendChild(el('p', '', ADVICE[verdict]));
    if (subline) right.appendChild(el('p', 'subscore', subline));
    card.appendChild(left);
    card.appendChild(right);
    return { card: card, right: right };
  }

  function reasonsList(reasons) {
    if (!reasons.length) return el('div', 'clear-note', 'No common phishing signs found.');
    var ul = el('ul', 'reasons');
    reasons.forEach(function (r) {
      var li = el('li');
      li.appendChild(el('span', 'badge ' + r.severity, SEV[r.severity] || r.severity));
      li.appendChild(el('span', '', r.text));
      ul.appendChild(li);
    });
    return ul;
  }

  function feedbackRow(kind, refId) {
    var row = el('div', 'feedback');
    row.appendChild(el('span', '', 'Was this helpful?'));
    function send(rating) {
      postJSON('/api/v1/feedback', { kind: kind, rating: rating, ref_id: refId || null }).then(
        function () { row.replaceChildren(el('span', '', 'Thanks for the feedback.')); },
        function () { row.replaceChildren(el('span', '', 'Could not send feedback.')); });
    }
    [['Yes', 1], ['No', -1]].forEach(function (o) {
      var b = el('button', 'btn small', o[0]); b.type = 'button';
      b.addEventListener('click', function () { send(o[1]); });
      row.appendChild(b);
    });
    return row;
  }

  function initTabs(onSelect) {
    var tabs = Array.prototype.slice.call(document.querySelectorAll('.tab'));
    if (!tabs.length) return;
    function select(tab) {
      tabs.forEach(function (t) {
        var on = t === tab;
        t.setAttribute('aria-selected', on ? 'true' : 'false');
        t.tabIndex = on ? 0 : -1;
        document.getElementById(t.getAttribute('aria-controls')).hidden = !on;
      });
      if (onSelect) onSelect(tab);
    }
    tabs.forEach(function (t, i) {
      t.addEventListener('click', function () { select(t); });
      t.addEventListener('keydown', function (e) {
        var j = e.key === 'ArrowRight' ? (i + 1) % tabs.length : e.key === 'ArrowLeft' ? (i + tabs.length - 1) % tabs.length : -1;
        if (j >= 0) { e.preventDefault(); tabs[j].focus(); select(tabs[j]); }
      });
    });
  }

  function initTheme() {
    var btn = document.getElementById('theme');
    if (!btn) return;
    function label() { btn.textContent = document.documentElement.getAttribute('data-theme') === 'dark' ? 'Light mode' : 'Dark mode'; }
    btn.addEventListener('click', function () {
      var next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      try { localStorage.setItem('theme', next); } catch (e) {}
      label();
    });
    label();
  }

  window.CDS = { LABELS: LABELS, ADVICE: ADVICE, SEV: SEV, el: el, pct: pct, pill: pill, request: request, postJSON: postJSON,
    gauge: gauge, verdictCard: verdictCard, reasonsList: reasonsList, feedbackRow: feedbackRow, initTabs: initTabs };
  initTheme();
})();
