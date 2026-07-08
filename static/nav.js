(function () {
  var SPRITE = 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/';
  var links = [
    { href: '/',           pokemon: 1,   label: 'Home' },
    { href: '/search',     pokemon: 52,  label: 'Card Search' },
    { href: '/compare',    pokemon: 106, label: 'Compare' },
    { href: '/collection', pokemon: 133, label: 'Collection' },
    { href: '/game',       pokemon: 25,  label: 'PokéCross' },
  ];

  var path = window.location.pathname;

  /* ── Fixed header bar ────────────────────────────────────────────── */
  var header = document.createElement('header');
  header.className = 'site-header';
  header.innerHTML =
    '<button class="hamburger" id="hamburger" aria-label="Open menu">' +
      '<span></span><span></span><span></span>' +
    '</button>' +
    '<a class="site-logo" href="/">Pok&eacute;Value</a>';

  /* ── Sidebar ─────────────────────────────────────────────────────── */
  var sidebar = document.createElement('nav');
  sidebar.className = 'sidebar';
  sidebar.id = 'sidebar';
  sidebar.innerHTML =
    '<div class="sidebar-header">' +
      '<span class="sidebar-title">Pok&eacute;Value</span>' +
      '<button class="sidebar-close" id="sidebar-close">&#x2715;</button>' +
    '</div>' +
    links.map(function (l) {
      var active = path === l.href ? ' active' : '';
      var img = '<img src="' + SPRITE + l.pokemon + '.png" alt="" ' +
                'style="width:30px;height:30px;image-rendering:pixelated;flex-shrink:0;">';
      return '<a href="' + l.href + '" class="sidebar-link' + active + '">' + img + l.label + '</a>';
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
