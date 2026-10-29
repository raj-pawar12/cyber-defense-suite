(function () {
  'use strict';
  var C = window.CDS, el = C.el, pct = C.pct;
  var input = document.getElementById('msg-input'), btn = document.getElementById('msg-check');
  var errorBox = document.getElementById('msg-error'), out = document.getElementById('msg-result');

  function linkRows(items) {
    var wrap = el('div', 'plain-list');
    items.forEach(function (l) {
      var a = l.analysis, row = el('div', 'link-row');
      row.appendChild(a ? C.pill(a.verdict) : el('span', 'pill invalid', 'Unchecked'));
      row.appendChild(el('span', 'u mono', l.link));
      row.appendChild(el('span', '', a ? pct(a.phishing_probability) + '%' : '-'));
      wrap.appendChild(row);
    });
    return wrap;
  }

  function wordChips(words) {
    var wrap = el('div', 'words');
    words.forEach(function (w) {
      var pts = Math.round(w.effect * 100);
      wrap.appendChild(el('span', 'word ' + (w.effect > 0 ? 'up' : 'down'), w.word + ' (' + (pts > 0 ? '+' : '') + pts + ')'));
    });
    return wrap;
  }

  function renderMessage(d) {
    out.replaceChildren();
    var sub = 'Wording score ' + pct(d.text_probability) + '%' + (d.links.length ? ' - riskiest link ' + pct(d.worst_link_probability) + '%' : '');
    var v = C.verdictCard(d.phishing_probability, d.verdict, sub);
    out.appendChild(v.card);
    if (d.links.length) {
      out.appendChild(el('h3', '', 'Links found in the message'));
      out.appendChild(linkRows(d.links));
    }
    out.appendChild(el('h3', '', 'What we noticed'));
    out.appendChild(C.reasonsList(d.reasons));
    if (d.influential_words.length) {
      out.appendChild(el('h3', '', 'Words that moved the score'));
      out.appendChild(wordChips(d.influential_words));
      out.appendChild(el('p', 'hint', 'Red words push the wording score up, green words push it down. Numbers are percentage points.'));
    }
    out.appendChild(C.feedbackRow('message', d.check_id));
  }

  function renderQr(d) {
    out.replaceChildren();
    var v = C.verdictCard(d.phishing_probability, d.verdict, 'From a scanned QR code');
    out.appendChild(v.card);
    out.appendChild(el('h3', '', 'The QR code contains'));
    var box = el('div', 'card mono', d.decoded); out.appendChild(box);
    if (d.links.length) {
      out.appendChild(el('h3', '', 'Links found'));
      out.appendChild(linkRows(d.links.map(function (a) { return { link: a.url, analysis: a }; })));
      d.links.forEach(function (a) {
        if (a.reasons.length) {
          out.appendChild(el('h3', '', 'Why ' + a.url.slice(0, 50) + ' was flagged'));
          out.appendChild(C.reasonsList(a.reasons));
        }
      });
    } else if (d.message) {
      out.appendChild(el('h3', '', 'What we noticed'));
      out.appendChild(C.reasonsList(d.message.reasons));
    }
    out.appendChild(C.feedbackRow('qr', d.check_id));
  }

  async function check() {
    errorBox.textContent = '';
    var text = input.value.trim();
    if (text.length < 3) { errorBox.textContent = 'Paste the email or SMS text you want to check.'; input.focus(); return; }
    btn.disabled = true; btn.textContent = 'Checking...';
    try { renderMessage(await C.postJSON('/api/v1/check-message', { text: text })); }
    catch (e) { out.replaceChildren(); errorBox.textContent = e.message; }
    finally { btn.disabled = false; btn.textContent = 'Check message'; }
  }
  btn.addEventListener('click', check);
  document.querySelectorAll('.chip').forEach(function (b) { b.addEventListener('click', function () { input.value = b.dataset.text; check(); }); });

  var file = document.getElementById('qr-file');
  file.addEventListener('change', async function () {
    errorBox.textContent = '';
    if (!file.files.length) return;
    var form = new FormData(); form.append('image', file.files[0]);
    try { renderQr(await C.request('/api/v1/check-qr', { method: 'POST', body: form })); }
    catch (e) { out.replaceChildren(); errorBox.textContent = e.message; }
    finally { file.value = ''; }
  });
})();
