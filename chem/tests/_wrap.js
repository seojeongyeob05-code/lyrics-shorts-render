// Wraps chem-daily.html in the same skeleton the Artifact host adds at publish time,
// so the page can be opened from file:// for testing. Returns the file URL.
const fs = require('fs'), os = require('os'), path = require('path');
const HEAD = '<!doctype html><html><head><meta charset=utf8><meta name=viewport content="width=device-width,initial-scale=1,viewport-fit=cover"><style>:root{color-scheme:light;box-sizing:border-box;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}html{scroll-padding-top:env(safe-area-inset-top,0px)}body{margin:0;padding:0;font:14px -apple-system,BlinkMacSystemFont,sans-serif;background:#fff;color:#000}img{max-width:100%}[hidden]:not([hidden=until-found i]){display:none!important}</style></head><body>\n';
module.exports = function wrap() {
  const src = path.join(__dirname, '..', 'chem-daily.html');
  const out = path.join(os.tmpdir(), 'chem-daily-wrapped.html');
  fs.writeFileSync(out, HEAD + fs.readFileSync(src, 'utf8') + '\n</body></html>');
  return 'file://' + out;
};
module.exports.CHROMIUM = '/opt/pw-browsers/chromium';
