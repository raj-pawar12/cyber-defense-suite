(function () {
  'use strict';
  var C = window.CDS, el = C.el;

  function stat(value, label) {
    var s = el('div', 'stat'); s.appendChild(el('b', '', value)); s.appendChild(el('span', '', label)); return s;
  }

  function renderModule(box, module, title, m) {
    box.replaceChildren();
    box.appendChild(el('h2', '', title));
    box.appendChild(el('p', 'hint', 'Best model: ' + m.best_model + '. Trained on ' + m.n_train + ' examples, tested on ' + m.n_test +
      ' unseen ones, ' + m.n_features + ' features. Data file: ' + m.data_file + '.'));
    var stats = el('div', 'stats mt-12');
    [['accuracy', 'Accuracy'], ['precision', 'Precision'], ['recall', 'Recall'], ['f1', 'F1 score'], ['roc_auc', 'ROC AUC']].forEach(function (k) {
      stats.appendChild(stat((m[k[0]] * 100).toFixed(1) + '%', k[1]));
    });
    box.appendChild(stats);
    if (/^(urls|messages)\.csv$/.test(m.data_file)) {
      box.appendChild(el('div', 'notice', 'These scores come from the synthetic demo dataset. Results on real-world data will be lower.'));
    }
    box.appendChild(el('h3', '', 'Model comparison (5-fold cross-validation, F1)'));
    var wrap = el('div', 'card table-wrap'), table = el('table'), head = el('tr');
    ['Model', 'Mean F1', 'Spread', 'Used in the app'].forEach(function (h) { head.appendChild(el('th', '', h)); });
    var thead = el('thead'); thead.appendChild(head); table.appendChild(thead);
    var tbody = el('tbody');
    Object.keys(m.model_comparison).forEach(function (name) {
      var c = m.model_comparison[name], tr = el('tr', c.deployed ? 'best' : '');
      tr.appendChild(el('td', '', name));
      tr.appendChild(el('td', '', c.cv_f1_mean.toFixed(4)));
      tr.appendChild(el('td', '', '+/- ' + c.cv_f1_std.toFixed(4)));
      tr.appendChild(el('td', '', c.deployed ? 'Yes' : 'Comparison only'));
      tbody.appendChild(tr);
    });
    table.appendChild(tbody); wrap.appendChild(table); box.appendChild(wrap);
    box.appendChild(el('h3', '', 'Charts'));
    var figs = el('div', 'figs');
    [['confusion_matrix.png', 'Confusion matrix of the test results', 'Confusion matrix'], ['roc_curve.png', 'ROC curve of the selected model', 'ROC curve'],
     ['feature_importance.png', 'Bar chart of the most influential features', module === 'url' ? 'Top features' : 'Top words']].forEach(function (f) {
      var fig = el('figure'), img = document.createElement('img');
      img.src = '/api/v1/reports/' + module + '/' + f[0]; img.alt = f[1]; img.loading = 'lazy';
      fig.appendChild(img); fig.appendChild(el('figcaption', '', f[2])); figs.appendChild(fig);
    });
    box.appendChild(figs);
  }

  function loadModule(module, title) {
    var box = document.getElementById('module-' + module);
    C.request('/api/v1/metrics?module=' + module).then(function (m) { renderModule(box, module, title, m); },
      function (e) { box.replaceChildren(el('p', 'hint', title + ': ' + e.message)); });
  }

  C.request('/api/v1/stats').then(function (s) {
    var u = document.getElementById('usage');
    u.appendChild(stat(String(s.total_checks), 'Checks run'));
    u.appendChild(stat(String(s.checks_last_24h), 'Last 24 hours'));
    u.appendChild(stat(String((s.by_verdict.phishing || 0)), 'Flagged as phishing'));
    u.appendChild(stat(String(s.feedback.helpful), 'Helpful votes'));
    u.appendChild(stat(String(s.feedback.not_helpful), 'Not helpful votes'));
  }, function () {});

  loadModule('url', 'Module 1: URL engine');
  loadModule('message', 'Module 2: Message engine');
})();
