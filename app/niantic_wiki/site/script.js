
(function () {
  document.documentElement.className = document.documentElement.className.replace(/\bno-js\b/, 'js');

  function initHiddenBlocks() {
    document.querySelectorAll('div.hiddenActive > div.hiddenHead').forEach(function (head) {
      head.addEventListener('click', function () {
        var root = head.parentElement;
        root.classList.toggle('hiddenHidden');
      });
    });
  }

  function initTocToggle() {
    var tocToggle = document.querySelector('#dw__toc h3.toggle');
    var tocBody = document.querySelector('#dw__toc > div');
    if (!tocToggle || !tocBody) return;
    tocToggle.style.cursor = 'pointer';
    tocToggle.classList.toggle('closed', getComputedStyle(tocBody).display === 'none');
    tocToggle.addEventListener('click', function () {
      var hidden = getComputedStyle(tocBody).display === 'none';
      tocBody.style.display = hidden ? 'block' : 'none';
      tocToggle.classList.toggle('closed', !hidden);
      tocToggle.classList.toggle('open', hidden);
    });
  }

  function initIndexTree() {
    document.querySelectorAll('#index__tree .index-tree-toggle').forEach(function (toggle) {
      toggle.addEventListener('click', function () {
        var item = toggle.closest('li.node');
        if (!item) return;
        var childTree = item.querySelector(':scope > ul.index-tree');
        if (!childTree) return;
        var expanded = toggle.getAttribute('aria-expanded') === 'true';
        toggle.setAttribute('aria-expanded', expanded ? 'false' : 'true');
        childTree.hidden = expanded;
      });
    });
  }

  function escapeHtml(value) {
    return value.replace(/[&<>"]/g, function (ch) {
      return ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'})[ch];
    });
  }

  function buildSnippet(text, terms) {
    var lower = text.toLowerCase();
    var index = -1;
    terms.forEach(function (term) {
      if (index !== -1) return;
      index = lower.indexOf(term);
    });
    if (index === -1) index = 0;
    var start = Math.max(0, index - 70);
    var end = Math.min(text.length, index + 130);
    var snippet = text.slice(start, end).trim();
    if (start > 0) snippet = '...' + snippet;
    if (end < text.length) snippet = snippet + '...';
    return snippet;
  }

  function initSearchPage() {
    var results = document.getElementById('search-results');
    var status = document.getElementById('search-status');
    var input = document.getElementById('search-page-input');
    if (!results || !status || !input) return;

    var params = new URLSearchParams(window.location.search);
    var query = (params.get('q') || '').trim();
    input.value = query;
    if (!query) return;

    status.textContent = 'Searching...';
    fetch('/niantic_wiki/search-index.json')
      .then(function (response) { return response.json(); })
      .then(function (entries) {
        var terms = query.toLowerCase().split(/\s+/).filter(Boolean);
        var matches = entries.map(function (entry) {
          var haystack = (entry.title + ' ' + entry.slug.replace(/\//g, ' ') + ' ' + entry.text).toLowerCase();
          var score = 0;
          terms.forEach(function (term) {
            if (entry.title.toLowerCase().indexOf(term) !== -1) score += 10;
            if (entry.slug.toLowerCase().indexOf(term) !== -1) score += 4;
            if (haystack.indexOf(term) !== -1) score += 1;
          });
          return { entry: entry, score: score };
        }).filter(function (item) {
          return item.score > 0;
        }).sort(function (a, b) {
          if (b.score !== a.score) return b.score - a.score;
          return a.entry.slug.localeCompare(b.entry.slug);
        }).slice(0, 50);

        status.textContent = matches.length + ' result' + (matches.length === 1 ? '' : 's') + ' for "' + query + '"';
        if (!matches.length) {
          results.innerHTML = '<p>No matching pages found.</p>';
          return;
        }
        results.innerHTML = matches.map(function (item) {
          var entry = item.entry;
          var snippet = buildSnippet(entry.text, terms);
          return '<article class="search-result">'
            + '<h2><a href="/niantic_wiki/page/' + encodeURI(entry.slug) + '.html">' + escapeHtml(entry.title) + '</a></h2>'
            + '<p class="search-result-path">' + escapeHtml(entry.slug) + '</p>'
            + '<p class="search-result-snippet">' + escapeHtml(snippet) + '</p>'
            + '</article>';
        }).join('');
      })
      .catch(function () {
        status.textContent = 'Search index could not be loaded.';
      });
  }

  initHiddenBlocks();
  initTocToggle();
  initIndexTree();
  initSearchPage();
})();
