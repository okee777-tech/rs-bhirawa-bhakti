/**
 * RS Bhirawa Bhakti — pemicu otomatis deploy (event-driven).
 * Edit Google Sheet -> dalam <=5 menit GitHub Actions jalan -> website update sendiri.
 *
 * ===== CARA PASANG (sekali saja) =====
 *   1) Buat GitHub PAT (token):
 *      - Buka https://github.com/settings/tokens?type=beta  (Fine-grained token)
 *      - Klik "Generate new token"
 *      - Token name: bebas (mis. "rsbb-trigger")
 *      - Expiration: mis. 90 hari
 *      - Repository access: "Only select repositories" -> pilih  okee777-tech/rs-bhirawa-bhakti
 *      - Permissions -> "Workflows": pilih "Read and write"
 *      - Klik "Generate token", lalu SALIN tokennya (diawali github_pat_...)
 *
 *   2) Buka Google Sheet "JADWAL DOKTER (Website)".
 *      Menu: Ekstensi -> Apps Script.
 *
 *   3) Hapus isi editor, tempel SELURUH isi file ini, lalu simpan
 *      (beri nama mis. "Trigger Deploy Jadwal").
 *
 *   4) Di editor, jalankan fungsi setToken dengan token tadi:
 *         setToken('github_pat_xxxxxxxx')
 *      lalu klik "Review permissions" / izinkan akses.
 *
 *   5) Jalankan fungsi setup() untuk memasang trigger.
 *
 *   6) Tes: edit satu sel di sheet, tunggu <=5 menit, cek situs.
 */

const PROP_TOKEN = 'GITHUB_PAT';
const PROP_PENDING = 'PENDING_EDIT';
const REPO = 'okee777-tech/rs-bhirawa-bhakti';
const WORKFLOW = 'deploy-jadwal.yml';

/** Simpan token GitHub (jalankan sekali). */
function setToken(token) {
  PropertiesService.getScriptProperties().setProperty(PROP_TOKEN, token);
  Logger.log('Token tersimpan (panjang ' + token.length + ').');
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
    Logger.log('Token belum di-set. Jalankan setToken(...) dulu.');
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
