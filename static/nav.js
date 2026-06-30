(function () {
  const links = [
    { href: '/popularity', label: '🌟 Popularity' },
    { href: '/search',     label: '🔍 Card Search' },
    { href: '/compare',    label: '🆚 Compare' },
    { href: '/collection', label: '📦 Collection' },
    { href: '/game',       label: '⚡ PokéCross' },
  ];

  const path = window.location.pathname;

  const nav = document.createElement('nav');
  nav.className = 'site-nav';
  nav.innerHTML =
    '<a class="nav-logo" href="/popularity">PokéValue</a>' +
    '<div class="nav-links">' +
    links.map(function (l) {
      const active = (path === l.href || (path === '/' && l.href === '/popularity'))
        ? ' active' : '';
      return '<a href="' + l.href + '" class="' + active.trim() + '">' + l.label + '</a>';
    }).join('') +
    '</div>';

  document.body.prepend(nav);
})();
