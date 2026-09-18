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

// Modal info layanan — kartu layanan bisa diklik, menampilkan foto/jadwal/telepon.
(function () {
  var data = window.LAYANAN_DATA || [];
  if (!data.length) return;

  var overlay = document.getElementById('layananModal');
  var closeBtn = document.getElementById('layananModalClose');
  var mFoto = document.getElementById('mFoto');
  var mIkon = document.getElementById('mIkon');
  var mNama = document.getElementById('mNama');
  var mDeskripsi = document.getElementById('mDeskripsi');
  var mJadwal = document.getElementById('mJadwal');
  var mJadwalVal = document.getElementById('mJadwalVal');
  var mTelepon = document.getElementById('mTelepon');
  var mTeleponVal = document.getElementById('mTeleponVal');
  if (!overlay) return;

  function open(idx) {
    var d = data[idx];
    if (!d) return;

    mNama.textContent = d.nama || '';
    mDeskripsi.textContent = d.deskripsi || '';

    // foto (kalau ada) atau ikon
    if (d.foto) {
      var img = document.createElement('img');
      img.src = d.foto;
      img.alt = d.nama || '';
      img.loading = 'lazy';
      mFoto.innerHTML = '';
      mFoto.appendChild(img);
      mFoto.hidden = false;
      mIkon.hidden = true;
    } else if (d.ikon) {
      mIkon.textContent = d.ikon;
      mIkon.hidden = false;
      mFoto.hidden = true;
    } else {
      mFoto.hidden = true;
      mIkon.hidden = true;
    }

    // jadwal
    if (d.jadwal) {
      mJadwalVal.textContent = d.jadwal;
      mJadwal.hidden = false;
    } else {
      mJadwal.hidden = true;
    }

    // telepon
    if (d.telepon) {
      var digits = d.telepon.replace(/[^0-9+]/g, '');
      mTelepon.href = 'tel:' + digits;
      mTeleponVal.textContent = d.telepon;
      mTelepon.hidden = false;
    } else {
      mTelepon.hidden = true;
    }

    overlay.hidden = false;
    document.body.style.overflow = 'hidden';
  }

  function close() {
    overlay.hidden = true;
    document.body.style.overflow = '';
  }

  document.querySelectorAll('.service-card[data-layanan]').forEach(function (card) {
    card.addEventListener('click', function () {
      open(parseInt(card.getAttribute('data-layanan'), 10));
    });
    card.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        open(parseInt(card.getAttribute('data-layanan'), 10));
      }
    });
  });

  if (closeBtn) closeBtn.addEventListener('click', close);
  overlay.addEventListener('click', function (e) {
    if (e.target === overlay) close();
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && !overlay.hidden) close();
  });
})();

// Lightbox galeri + modal berita.
(function () {
  // --- Galeri (lightbox) ---
  var gData = window.GALERI_DATA || [];
  var gOverlay = document.getElementById('galeriModal');
  if (gOverlay && gData.length) {
    var gClose = document.getElementById('galeriModalClose');
    var gFoto = document.getElementById('gFoto');
    var gNama = document.getElementById('gNama');
    var gDesk = document.getElementById('gDeskripsi');
    var gMeta = document.getElementById('gMeta');
    var gMetaVal = document.getElementById('gMetaVal');

    function gOpen(i) {
      var d = gData[i];
      if (!d) return;
      gNama.textContent = d.judul || '';
      gDesk.textContent = d.deskripsi || '';
      if (d.foto) {
        var img = document.createElement('img');
        img.src = d.foto;
        img.alt = d.judul || '';
        img.loading = 'lazy';
        gFoto.innerHTML = '';
        gFoto.appendChild(img);
        gFoto.hidden = false;
      } else {
        gFoto.hidden = true;
      }
      var meta = [];
      if (d.kategori) meta.push(d.kategori);
      if (d.tanggal) meta.push(d.tanggal);
      if (meta.length) {
        gMetaVal.textContent = meta.join(' · ');
        gMeta.hidden = false;
      } else {
        gMeta.hidden = true;
      }
      gOverlay.hidden = false;
      document.body.style.overflow = 'hidden';
    }
    function gCloseFn() {
      gOverlay.hidden = true;
      document.body.style.overflow = '';
    }
    document.querySelectorAll('.gallery-item[data-galeri]').forEach(function (el) {
      el.addEventListener('click', function () { gOpen(parseInt(el.getAttribute('data-galeri'), 10)); });
      el.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          gOpen(parseInt(el.getAttribute('data-galeri'), 10));
        }
      });
    });
    if (gClose) gClose.addEventListener('click', gCloseFn);
    gOverlay.addEventListener('click', function (e) { if (e.target === gOverlay) gCloseFn(); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !gOverlay.hidden) gCloseFn(); });
  }

  // --- Berita (modal artikel) ---
  var bData = window.BERITA_DATA || [];
  var bOverlay = document.getElementById('beritaModal');
  if (bOverlay && bData.length) {
    var bClose = document.getElementById('beritaModalClose');
    var bFoto = document.getElementById('bFoto');
    var bMeta = document.getElementById('bMeta');
    var bMetaVal = document.getElementById('bMetaVal');
    var bJudul = document.getElementById('bJudul');
    var bIsi = document.getElementById('bIsi');

    function setMultiline(el, text) {
      el.innerHTML = '';
      var lines = (text || '').split('\n');
      lines.forEach(function (line, i) {
        if (i > 0) el.appendChild(document.createElement('br'));
        el.appendChild(document.createTextNode(line));
      });
    }

    function bOpen(i) {
      var d = bData[i];
      if (!d) return;
      bJudul.textContent = d.judul || '';
      setMultiline(bIsi, d.isi || d.ringkasan || '');
      if (d.foto) {
        var img = document.createElement('img');
        img.src = d.foto;
        img.alt = d.judul || '';
        img.loading = 'lazy';
        bFoto.innerHTML = '';
        bFoto.appendChild(img);
        bFoto.hidden = false;
      } else {
        bFoto.hidden = true;
      }
      var meta = [];
      if (d.kategori) meta.push(d.kategori);
      if (d.tanggal) meta.push(d.tanggal);
      if (meta.length) {
        bMetaVal.textContent = meta.join(' · ');
        bMeta.hidden = false;
      } else {
        bMeta.hidden = true;
      }
      bOverlay.hidden = false;
      document.body.style.overflow = 'hidden';
    }
    function bCloseFn() {
      bOverlay.hidden = true;
      document.body.style.overflow = '';
    }
    document.querySelectorAll('.news-card[data-berita]').forEach(function (el) {
      el.addEventListener('click', function () { bOpen(parseInt(el.getAttribute('data-berita'), 10)); });
      el.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          bOpen(parseInt(el.getAttribute('data-berita'), 10));
        }
      });
    });
    if (bClose) bClose.addEventListener('click', bCloseFn);
    bOverlay.addEventListener('click', function (e) { if (e.target === bOverlay) bCloseFn(); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !bOverlay.hidden) bCloseFn(); });
  }
})();

// Tombol geser (carousel) untuk baris dokter, layanan, dan berita.
(function () {
  document.querySelectorAll('.scroll-wrap').forEach(function (wrap) {
    var scroller = wrap.querySelector('.doctor-scroll, .service-scroll, .news-scroll');
    if (!scroller) return;
    var left = wrap.querySelector('.scroll-btn-left');
    var right = wrap.querySelector('.scroll-btn-right');

    function update() {
      if (left) left.disabled = scroller.scrollLeft <= 4;
      if (right) right.disabled = scroller.scrollLeft + scroller.clientWidth >= scroller.scrollWidth - 4;
    }
    function step() { return Math.round(scroller.clientWidth * 0.8); }

    if (left) left.addEventListener('click', function () {
      scroller.scrollBy({ left: -step(), behavior: 'smooth' });
    });
    if (right) right.addEventListener('click', function () {
      scroller.scrollBy({ left: step(), behavior: 'smooth' });
    });
    scroller.addEventListener('scroll', update, { passive: true });
    window.addEventListener('resize', update);
    update();
  });
})();

// Slider hero: otomatis geser halus + tombol panah & titik + pause saat disentuh.
(function () {
  var slider = document.getElementById('heroSlider');
  if (!slider) return;
  var track = document.getElementById('slidesTrack');
  var prevBtn = document.getElementById('sliderPrev');
  var nextBtn = document.getElementById('sliderNext');
  var dotsWrap = document.getElementById('sliderDots');
  if (!track || !dotsWrap) return;

  var slides = track.children;
  if (!slides.length) return;

  var INTERVAL = 4500; // ms antar slide
  var index = 0;
  var timer = null;

  // buat titik navigasi sesuai jumlah slide
  for (var i = 0; i < slides.length; i++) {
    (function (i) {
      var b = document.createElement('button');
      b.type = 'button';
      b.setAttribute('aria-label', 'Ke slide ' + (i + 1));
      b.addEventListener('click', function () { go(i); restart(); });
      dotsWrap.appendChild(b);
    })(i);
  }
  var dots = dotsWrap.children;

  function go(i) {
    index = ((i % slides.length) + slides.length) % slides.length;
    track.style.transform = 'translateX(' + (-index * 100) + '%)';
    for (var d = 0; d < dots.length; d++) {
      dots[d].classList.toggle('active', d === index);
    }
  }

  function next() { go(index + 1); }
  function prev() { go(index - 1); }
  function stop() { if (timer) { clearInterval(timer); timer = null; } }
  function start() { stop(); timer = setInterval(next, INTERVAL); }
  function restart() { start(); }

  if (nextBtn) nextBtn.addEventListener('click', function () { next(); restart(); });
  if (prevBtn) prevBtn.addEventListener('click', function () { prev(); restart(); });

  // pause otomatis saat kursor di atas slider / sentuh, lanjut saat keluar
  slider.addEventListener('mouseenter', stop);
  slider.addEventListener('mouseleave', start);
  slider.addEventListener('touchstart', stop, { passive: true });

  go(0);
  start();
})();
