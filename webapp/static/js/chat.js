(function () {
  'use strict';
  var C = window.CDS, el = C.el;
  var box = document.getElementById('messages'), input = document.getElementById('chat-text'), sendBtn = document.getElementById('chat-send');
  var errorBox = document.getElementById('chat-error'), suggestions = document.getElementById('suggestions');
  var history = [], pending = false;

  function inline(parent, text) {
    text.split(/(\*\*[^*]+\*\*|`[^`]+`)/).forEach(function (part) {
      if (!part) return;
      if (part.slice(0, 2) === '**' && part.slice(-2) === '**' && part.length > 4) parent.appendChild(el('strong', '', part.slice(2, -2)));
      else if (part[0] === '`' && part.slice(-1) === '`' && part.length > 2) parent.appendChild(el('code', '', part.slice(1, -1)));
      else parent.appendChild(document.createTextNode(part));
    });
  }
  function markdown(text) {
    var wrap = el('div'), list = null, kind = null;
    text.split(/\r?\n/).forEach(function (raw) {
      var line = raw.trim(), m;
      if (!line) { list = null; return; }
      if ((m = line.match(/^[-*\u2022]\s+(.*)$/))) {
        if (kind !== 'ul' || !list) { list = el('ul'); kind = 'ul'; wrap.appendChild(list); }
        inline(list.appendChild(el('li')), m[1]);
      } else if ((m = line.match(/^\d+[.)]\s+(.*)$/))) {
        if (kind !== 'ol' || !list) { list = el('ol'); kind = 'ol'; wrap.appendChild(list); }
        inline(list.appendChild(el('li')), m[1]);
      } else {
        list = null;
        var p = el('p');
        if ((m = line.match(/^#{1,6}\s+(.*)$/))) { p.appendChild(el('strong', '', m[1])); } else { inline(p, line); }
        wrap.appendChild(p);
      }
    });
    return wrap;
  }

  function scrollDown() { box.scrollTop = box.scrollHeight; }
  function addUser(text) {
    var m = el('div', 'msg user'); m.appendChild(el('div', 'bubble', text)); box.appendChild(m); scrollDown();
  }
  function card(c) {
    var d = el('div', 'mini-card');
    if (c.type === 'url') {
      d.appendChild(C.pill(c.verdict)); d.appendChild(el('span', 'u mono', c.url)); d.appendChild(el('span', '', C.pct(c.probability) + '% phishing'));
    } else {
      d.appendChild(C.pill(c.verdict)); d.appendChild(el('span', 'u', 'Message check'));
      d.appendChild(el('span', '', C.pct(c.probability) + '% phishing'));
    }
    return d;
  }
  function addBot(data) {
    var m = el('div', 'msg bot');
    (data.cards || []).forEach(function (c) { m.appendChild(card(c)); });
    var bubble = el('div', 'bubble'); bubble.appendChild(markdown(data.reply)); m.appendChild(bubble);
    if (data.notice) m.appendChild(el('div', 'msg-notice', data.notice));
    if (data.sources && data.sources.length) {
      m.appendChild(el('div', 'sources', 'Related articles: ' + data.sources.map(function (s) { return '[' + s.n + '] ' + s.title + ' - ' + s.heading; }).join('; ')));
    }
    if (data.mode === 'gemini' || data.mode === 'offline') m.appendChild(C.feedbackRow('chat', null));
    box.appendChild(m); scrollDown();
    return m;
  }
  function typing() { var m = el('div', 'msg bot'); m.appendChild(el('div', 'bubble typing', 'Thinking...')); box.appendChild(m); scrollDown(); return m; }

  function setPending(on) { pending = on; sendBtn.disabled = on; sendBtn.textContent = on ? 'Sending...' : 'Send'; }

  async function send(text) {
    text = (text || '').trim();
    if (!text || pending) return;
    errorBox.textContent = '';
    suggestions.hidden = true;
    var prior = history.slice(-8);
    addUser(text); history.push({ role: 'user', content: text });
    input.value = ''; input.style.height = 'auto';
    setPending(true);
    var wait = typing();
    try {
      var data = await C.postJSON('/api/v1/chat', { message: text, history: prior });
      wait.remove(); addBot(data); history.push({ role: 'assistant', content: data.reply });
    } catch (e) {
      wait.remove(); history.pop(); errorBox.textContent = e.message;
    } finally { setPending(false); input.focus(); }
  }

  sendBtn.addEventListener('click', function () { send(input.value); });
  input.addEventListener('keydown', function (e) { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(input.value); } });
  input.addEventListener('input', function () { input.style.height = 'auto'; input.style.height = Math.min(input.scrollHeight, 140) + 'px'; });
  suggestions.querySelectorAll('.chip').forEach(function (b) { b.addEventListener('click', function () { send(b.textContent); }); });
  document.getElementById('chat-clear').addEventListener('click', function () {
    history = []; box.replaceChildren(); suggestions.hidden = false; errorBox.textContent = ''; greet();
  });

  function greet() {
    addBot({ reply: "Hi! I'm CyberGuide. Ask me anything about cybersecurity and online safety, or paste a link and I will check it with the URL engine.", mode: 'greeting', cards: [], sources: [] });
  }
  greet();

  C.request('/api/v1/health').then(function (h) {
    var s = document.getElementById('ai-status');
    if (h.gemini_configured) { s.textContent = 'Gemini connected (' + h.gemini_model + ')'; s.className = 'badge-status on'; }
    else { s.textContent = 'Offline mode: add GEMINI_API_KEY to enable the AI model'; }
  }, function () { document.getElementById('ai-status').textContent = 'Status unavailable'; });
})();
