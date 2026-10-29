(function () {
  'use strict';
  var C = window.CDS, el = C.el, pct = C.pct;
  var input = document.getElementById('url'), checkBtn = document.getElementById('check'), errorBox = document.getElementById('error');
  var out = document.getElementById('result');

  function anatomy(p) {
    var box = el('div', 'anatomy mono');
    box.setAttribute('aria-label', 'The link split into parts');
    box.appendChild(el('span', 'dim', p.scheme + '://'));
    if (p.userinfo) box.appendChild(el('span', 'dim trick', p.userinfo + '@'));
    if (p.subdomain) box.appendChild(el('span', 'dim', p.subdomain + '.'));
    box.appendChild(el('span', 'real', p.domain));
    if (p.port) box.appendChild(el('span', 'dim', ':' + p.port));
    box.appendChild(el('span', 'dim', p.rest));
    return box;
  }
  function legend() {
    var l = el('div', 'legend');
    [['l-real', 'Real destination'], ['l-dim', 'Everything else'], ['l-trick', 'Wavy line: text before @ is ignored by browsers']].forEach(function (x) {
      var s = el('span'); s.appendChild(el('i', x[0])); s.appendChild(document.createTextNode(x[1])); l.appendChild(s);
    });
    return l;
  }

  function renderResult(d) {
    out.replaceChildren();
    var v = C.verdictCard(d.phishing_probability, d.verdict);
    var copy = el('button', 'btn small', 'Copy summary'); copy.type = 'button';
    copy.addEventListener('click', function () {
      var lines = [C.LABELS[d.verdict] + ' (' + pct(d.phishing_probability) + '% phishing chance): ' + d.url];
      d.reasons.forEach(function (r) { lines.push('- ' + r.text); });
      if (!navigator.clipboard) { copy.textContent = 'Copy not supported'; return; }
      navigator.clipboard.writeText(lines.join('\n')).then(function () {
        copy.textContent = 'Copied'; setTimeout(function () { copy.textContent = 'Copy summary'; }, 1600);
      }, function () { copy.textContent = 'Could not copy'; });
    });
    v.right.appendChild(copy);
    out.appendChild(v.card);

    out.appendChild(el('h3', '', 'Where this link really goes'));
    var a = el('div', 'card');
    a.appendChild(anatomy(d.parts));
    a.appendChild(legend());
    if (d.parts.scheme_assumed) a.appendChild(el('p', 'hint', 'No http or https was given, so https was assumed.'));
    out.appendChild(a);

    out.appendChild(el('h3', '', 'What we noticed'));
    out.appendChild(C.reasonsList(d.reasons));

    if (d.contributions && d.contributions.length) {
      out.appendChild(el('h3', '', 'What moved the score'));
      var ul = el('ul', 'plain-list contrib');
      d.contributions.forEach(function (c) {
        var li = el('li');
        li.appendChild(el('span', '', c.label));
        var pts = Math.round(c.effect * 100);
        li.appendChild(el('span', 'badge ' + (c.effect > 0 ? 'up' : 'down'), (pts > 0 ? '+' : '') + pts + ' points'));
        ul.appendChild(li);
      });
      out.appendChild(ul);
      out.appendChild(el('p', 'hint', 'Each value shows how much the phishing chance changes compared with a typical link. Features can overlap, so treat this as a guide.'));
    }
    out.appendChild(C.feedbackRow('url', d.check_id));
  }

  /* history */
  var history = [];
  try { history = JSON.parse(localStorage.getItem('url-history') || '[]'); if (!Array.isArray(history)) history = []; } catch (e) { history = []; }
  function saveHistory() { try { localStorage.setItem('url-history', JSON.stringify(history)); } catch (e) {} }
  function renderHistory() {
    var box = document.getElementById('history'), list = document.getElementById('history-list');
    list.replaceChildren();
    box.hidden = history.length === 0;
    history.forEach(function (h) {
      var li = el('li'), b = el('button'); b.type = 'button';
      b.appendChild(C.pill(h.verdict));
      b.appendChild(el('span', 'u mono', h.url));
      b.appendChild(el('span', '', pct(h.p) + '%'));
      b.addEventListener('click', function () { input.value = h.url; check(); });
      li.appendChild(b); list.appendChild(li);
    });
  }
  document.getElementById('clear-history').addEventListener('click', function () { history = []; saveHistory(); renderHistory(); });

  async function check() {
    errorBox.textContent = '';
    var url = input.value.trim();
    if (!url) { errorBox.textContent = 'Enter a web address to check.'; input.focus(); return; }
    checkBtn.disabled = true; checkBtn.textContent = 'Checking...';
    try {
      var d = await C.postJSON('/api/v1/check-url', { url: url });
      renderResult(d);
      history = [{ url: d.url, verdict: d.verdict, p: d.phishing_probability }].concat(history.filter(function (h) { return h.url !== d.url; })).slice(0, 8);
      saveHistory(); renderHistory();
    } catch (e) {
      out.replaceChildren(); errorBox.textContent = e.message;
    } finally {
      checkBtn.disabled = false; checkBtn.textContent = 'Check link';
    }
  }
  checkBtn.addEventListener('click', check);
  input.addEventListener('keydown', function (e) { if (e.key === 'Enter') check(); });
  document.querySelectorAll('.chip').forEach(function (b) { b.addEventListener('click', function () { input.value = b.dataset.url; check(); }); });
  var pasteBtn = document.getElementById('paste');
  if (navigator.clipboard && navigator.clipboard.readText) {
    pasteBtn.hidden = false;
    pasteBtn.addEventListener('click', function () {
      navigator.clipboard.readText().then(function (t) { input.value = t.trim(); input.focus(); },
        function () { errorBox.textContent = 'Could not read the clipboard. Paste with Ctrl+V instead.'; });
    });
  }
  renderHistory();

  /* bulk */
  var bulkRows = [];
  function csvCell(v) { return '"' + String(v).replace(/"/g, '""') + '"'; }
  document.getElementById('bulk-run').addEventListener('click', async function () {
    var btn = document.getElementById('bulk-run'), err = document.getElementById('bulk-error'), body = document.getElementById('bulk-body');
    err.textContent = '';
    var seen = {}, urls = document.getElementById('bulk-input').value.split(/\r?\n/).map(function (s) { return s.trim(); }).filter(function (s) {
      if (!s || seen[s]) return false; seen[s] = true; return true;
    });
    if (!urls.length) { err.textContent = 'Paste at least one link, one per line.'; return; }
    if (urls.length > 25) { urls = urls.slice(0, 25); err.textContent = 'Only the first 25 links are checked.'; }
    btn.disabled = true; document.getElementById('bulk-csv').hidden = true; body.replaceChildren(); bulkRows = [];
    document.getElementById('bulk-table').hidden = false;
    var counts = { legitimate: 0, suspicious: 0, phishing: 0, invalid: 0 };
    for (var i = 0; i < urls.length; i++) {
      btn.textContent = 'Checking ' + (i + 1) + ' of ' + urls.length + '...';
      var row = el('tr'), v, p, u = urls[i];
      try { var d = await C.postJSON('/api/v1/check-url', { url: u }); v = d.verdict; p = pct(d.phishing_probability) + '%'; }
      catch (e) { v = 'invalid'; p = '-'; }
      counts[v]++;
      bulkRows.push([u, v, p]);
      var c1 = el('td'); c1.appendChild(C.pill(v === 'invalid' ? 'invalid' : v));
      row.appendChild(c1); row.appendChild(el('td', '', p)); row.appendChild(el('td', 'u mono', u));
      body.appendChild(row);
    }
    var sum = document.getElementById('bulk-summary'); sum.replaceChildren();
    [['legitimate', 'safe'], ['suspicious', 'careful'], ['phishing', 'likely phishing'], ['invalid', 'invalid']].forEach(function (k) {
      if (counts[k[0]]) sum.appendChild(el('span', 'pill ' + k[0], counts[k[0]] + ' ' + k[1]));
    });
    btn.disabled = false; btn.textContent = 'Check all'; document.getElementById('bulk-csv').hidden = false;
  });
  document.getElementById('bulk-csv').addEventListener('click', function () {
    var lines = ['url,verdict,phishing_chance'].concat(bulkRows.map(function (r) { return r.map(csvCell).join(','); }));
    var a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([lines.join('\n')], { type: 'text/csv' }));
    a.download = 'url-check-results.csv';
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(function () { URL.revokeObjectURL(a.href); }, 1000);
  });

  C.initTabs();
})();
