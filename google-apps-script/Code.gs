/**
 * RS Bhirawa Bhakti — pemicu otomatis deploy.
 * Edit Google Sheet -> dalam <=5 menit Netlify build -> website update sendiri.
 *
 * CARA PASANG (sekali saja):
 *   1) Buka Google Sheet "JADWAL DOKTER (Website)".
 *   2) Menu: Ekstensi -> Apps Script.
 *   3) Hapus isi editor, tempel SELURUH isi file ini, lalu simpan
 *      (beri nama mis. "Trigger Deploy Jadwal").
 *   4) Jalankan fungsi setHook dengan URL build hook Netlify:
 *         setHook('https://api.netlify.com/build_hooks/XXXXXXXX')
 *      lalu klik "Review permissions" / izinkan akses.
 *   5) Jalankan fungsi setup() untuk memasang trigger.
 *   6) Tes: edit satu sel di sheet, tunggu <=5 menit, cek situs.
 */

const PROP_HOOK = 'NETLIFY_BUILD_HOOK';
const PROP_PENDING = 'PENDING_EDIT';

/** Simpan URL build hook Netlify (jalankan sekali). */
function setHook(url) {
  PropertiesService.getScriptProperties().setProperty(PROP_HOOK, url);
  Logger.log('Hook tersimpan: ' + url);
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

/** Dicek tiap 5 menit -> kalau ada perubahan, panggil Netlify build hook. */
function checkAndDeploy() {
  const p = PropertiesService.getScriptProperties();
  if (p.getProperty(PROP_PENDING) !== '1') return;
  p.setProperty(PROP_PENDING, '0');
  const hook = p.getProperty(PROP_HOOK);
  if (!hook) {
    Logger.log('Hook belum di-set. Jalankan setHook(...) dulu.');
    return;
  }
  UrlFetchApp.fetch(hook, { method: 'post' });
  Logger.log('Trigger deploy terkirim ke Netlify.');
}
