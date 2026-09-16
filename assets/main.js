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
