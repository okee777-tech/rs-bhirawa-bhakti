// RS Bhirawa Bhakti — Prototype JS
// Mobile navigation toggle + simple language-switch placeholder.

(function () {
  var toggle = document.getElementById('navToggle');
  var nav = document.getElementById('mainNav');

  if (toggle && nav) {
    toggle.addEventListener('click', function () {
      nav.classList.toggle('open');
      toggle.textContent = nav.classList.contains('open') ? '✕' : '☰';
    });
  }

  // Language switch (placeholder — konten EN menyusul)
  var langs = document.querySelectorAll('.lang-switch .lang');
  langs.forEach(function (lang) {
    lang.addEventListener('click', function () {
      langs.forEach(function (l) { l.classList.remove('active'); });
      lang.classList.add('active');
    });
  });
})();
