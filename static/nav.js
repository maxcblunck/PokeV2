(function () {
  var links = [
    { href: '/',           label: '🏠 Home' },
    { href: '/search',     label: '🔍 Card Search' },
    { href: '/compare',    label: '🆚 Compare' },
    { href: '/collection', label: '📦 Collection' },
    { href: '/popularity', label: '🌟 Rankings' },
    { href: '/game',       label: '⚡ PokéCross' },
  ];

  var path = window.location.pathname;

  /* ── Fixed header bar ────────────────────────────────────────────── */
  var header = document.createElement('header');
  header.className = 'site-header';
  header.innerHTML =
    '<button class="hamburger" id="hamburger" aria-label="Open menu">' +
      '<span></span><span></span><span></span>' +
    '</button>' +
    '<a class="site-logo" href="/">PokéValue</a>';

  /* ── Sidebar ─────────────────────────────────────────────────────── */
  var sidebar = document.createElement('nav');
  sidebar.className = 'sidebar';
  sidebar.id = 'sidebar';
  sidebar.innerHTML =
    '<div class="sidebar-header">' +
      '<span class="sidebar-title">PokéValue</span>' +
      '<button class="sidebar-close" id="sidebar-close">✕</button>' +
    '</div>' +
    links.map(function (l) {
      return '<a href="' + l.href + '" class="sidebar-link' + (path === l.href ? ' active' : '') + '">' + l.label + '</a>';
    }).join('');

  /* ── Overlay ─────────────────────────────────────────────────────── */
  var overlay = document.createElement('div');
  overlay.className = 'sidebar-overlay';
  overlay.id = 'sidebar-overlay';

  document.body.prepend(overlay);
  document.body.prepend(sidebar);
  document.body.prepend(header);

  function openSidebar() {
    document.getElementById('sidebar').classList.add('open');
    document.getElementById('sidebar-overlay').classList.add('open');
    document.body.style.overflow = 'hidden';
  }
  function closeSidebar() {
    document.getElementById('sidebar').classList.remove('open');
    document.getElementById('sidebar-overlay').classList.remove('open');
    document.body.style.overflow = '';
  }

  document.getElementById('hamburger').addEventListener('click', openSidebar);
  document.getElementById('sidebar-close').addEventListener('click', closeSidebar);
  document.getElementById('sidebar-overlay').addEventListener('click', closeSidebar);
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') closeSidebar(); });
})();
