(function () {
  var SPRITE = 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/';
  var links = [
    { href: '/',           pokemon: 1,   label: 'Home' },
    { href: '/search',     pokemon: 52,  label: 'Card Search' },
    { href: '/compare',    pokemon: 106, label: 'Compare' },
    { href: '/collection', pokemon: 133, label: 'Collection' },
    { href: '/portfolio',  pokemon: 6,   label: 'Portfolio' },
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

  /* ── Falling Pokémon background sprites ──────────────────────────── */
  (function () {
    var style = document.createElement('style');
    style.textContent =
      '@keyframes pv-fall {' +
        'from { transform: translateY(0); }' +
        'to   { transform: translateY(calc(100vh + 160px)); }' +
      '}';
    document.head.appendChild(style);

    var bg = document.createElement('div');
    bg.style.cssText = 'position:fixed;inset:0;z-index:0;pointer-events:none;overflow:hidden;';

    // Shuffle Gen-1 dex numbers so every load picks different Pokémon
    var pool = [];
    for (var n = 1; n <= 151; n++) pool.push(n);
    for (var i = pool.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var tmp = pool[i]; pool[i] = pool[j]; pool[j] = tmp;
    }

    var count = 22;
    for (var k = 0; k < count; k++) {
      var dex      = pool[k];
      var size     = 56 + Math.floor(Math.random() * 64);        // 56–120 px
      var op       = (0.15 + Math.random() * 0.15).toFixed(3);   // 0.15–0.30
      var x        = (Math.random() * 94).toFixed(1);             // % left
      var dur      = (7 + Math.random() * 8).toFixed(1);          // 7–15 s fall
      // Negative delay starts the sprite mid-fall so screen is full immediately
      var delay    = (-Math.random() * parseFloat(dur)).toFixed(2);

      var img = document.createElement('img');
      img.src = SPRITE + dex + '.png';
      img.alt = '';
      img.style.cssText =
        'position:absolute;' +
        'left:' + x + '%;' +
        'top:-140px;' +
        'width:' + size + 'px;' +
        'height:' + size + 'px;' +
        'opacity:' + op + ';' +
        'image-rendering:pixelated;' +
        'animation:pv-fall ' + dur + 's ' + delay + 's linear infinite;';
      bg.appendChild(img);
    }

    document.body.appendChild(bg);
  })();
})();
