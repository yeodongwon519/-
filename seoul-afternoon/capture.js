// Renders scene.html deterministically: a still (PNG) or a frame sequence.
// usage: node capture.js still <t> <out.png> [scale]
//        node capture.js frames <fps> <seconds> <outdir>
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

(async () => {
  const [mode, ...args] = process.argv.slice(2);
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
  const scale = mode === 'still' && args[2] ? parseFloat(args[2]) : 1;
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: scale });
  await page.goto('file://' + path.join(__dirname, 'scene.html') + '?capture=1');
  await page.waitForFunction(() => typeof window.renderFrame === 'function');

  if (mode === 'still') {
    const t = parseFloat(args[0]);
    await page.evaluate(t => window.renderFrame(t), t);
    await page.locator('#c').screenshot({ path: args[1] });
    console.log('wrote', args[1]);
  } else {
    const fps = parseInt(args[0]), secs = parseFloat(args[1]), out = args[2];
    const shard = parseInt(args[3] || 0), nshard = parseInt(args[4] || 1);
    fs.mkdirSync(out, { recursive: true });
    const n = Math.round(fps * secs);
    for (let i = shard; i < n; i += nshard) {
      const t = i / fps;
      const data = await page.evaluate(t => { window.renderFrame(t); return document.getElementById('c').toDataURL('image/png').slice(22); }, t);
      fs.writeFileSync(path.join(out, `f_${String(i).padStart(4, '0')}.png`), Buffer.from(data, 'base64'));
      if (i % 30 === 0) console.log('frame', i, '/', n);
    }
    console.log('done', n, 'frames');
  }
  await browser.close();
})();
