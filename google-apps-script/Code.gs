/**
 * RS Bhirawa Bhakti — pemicu otomatis deploy (event-driven).
 * Edit Google Sheet -> dalam <=5 menit GitHub Actions jalan -> website update sendiri.
 *
 * ===== CARA PASANG (sekali saja) =====
 *   1) Tempel token di baris TOKEN_GITHUB di bawah (lihat tanda "TEMPEL DI SINI").
 *   2) Di editor Apps Script, jalankan fungsi simpanToken() (sekali).
 *   3) Jalankan fungsi setup() (sekali).
 *   4) Tes: edit satu sel di sheet, tunggu <=5 menit, cek situs.
 */

const PROP_TOKEN = 'GITHUB_PAT';
const PROP_PENDING = 'PENDING_EDIT';
const REPO = 'okee777-tech/rs-bhirawa-bhakti';
const WORKFLOW = 'deploy-jadwal.yml';

// ===== TEMPEL DI SINI =====
// Ganti teks 'TEMPEL_TOKEN_ANDA' dengan token GitHub Anda (diawali github_pat_...).
// Contoh: const TOKEN_GITHUB = 'github_pat_11AAABBBCCCDDD...';
const TOKEN_GITHUB = 'TEMPEL_TOKEN_ANDA';

/** Simpan token dari TOKEN_GITHUB ke penyimpanan script (jalankan sekali). */
function simpanToken() {
  if (TOKEN_GITHUB === 'TEMPEL_TOKEN_ANDA' || TOKEN_GITHUB === '') {
    Logger.log('⚠️ Anda belum menempel token. Isi TOKEN_GITHUB di baris atas dulu.');
    return;
  }
  PropertiesService.getScriptProperties().setProperty(PROP_TOKEN, TOKEN_GITHUB);
  Logger.log('OK: token tersimpan (panjang ' + TOKEN_GITHUB.length + ').');
}

/** Pasang trigger onEdit + penjadwal 5 menit (jalankan sekali). */
function setup() {
  const ss = SpreadsheetApp.getActive();
  const handlers = ScriptApp.getProjectTriggers().map(function (t) {
    return t.getHandlerFunction();
  });
  if (handlers.indexOf('onSheetEdit') === -1) {
    ScriptApp.newTrigger('onSheetEdit').forSpreadsheet(ss).onEdit().create();
  }
  if (handlers.indexOf('checkAndDeploy') === -1) {
    ScriptApp.newTrigger('checkAndDeploy').timeBased().everyMinutes(5).create();
  }
  Logger.log('OK: trigger onEdit + penjadwal 5 menit terpasang.');
}

/** Dipanggil setiap ada edit -> tandai "ada perubahan". */
function onSheetEdit(e) {
  PropertiesService.getScriptProperties().setProperty(PROP_PENDING, '1');
}

/** Dicek tiap 5 menit -> kalau ada perubahan, picu GitHub Actions. */
function checkAndDeploy() {
  const p = PropertiesService.getScriptProperties();
  if (p.getProperty(PROP_PENDING) !== '1') return;
  p.setProperty(PROP_PENDING, '0');

  const token = p.getProperty(PROP_TOKEN);
  if (!token) {
    Logger.log('Token belum di-set. Jalankan simpanToken() dulu.');
    return;
  }

  const url = 'https://api.github.com/repos/' + REPO +
      '/actions/workflows/' + WORKFLOW + '/dispatches';
  const resp = UrlFetchApp.fetch(url, {
    method: 'post',
    headers: {
      'Authorization': 'Bearer ' + token,
      'Accept': 'application/vnd.github+json',
      'X-GitHub-Api-Version': '2022-11-28'
    },
    payload: JSON.stringify({ ref: 'main' }),
    muteHttpExceptions: true
  });
  Logger.log('GitHub API: ' + resp.getResponseCode() + ' ' + resp.getContentText());
}
