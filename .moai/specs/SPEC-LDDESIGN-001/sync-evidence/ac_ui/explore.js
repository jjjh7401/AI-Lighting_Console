// AC-UI 마무리 — 하니스 화면 구조 훑기(1회용 탐색). 실행: NODE_PATH=<playwright 설치 경로> node explore.js <출력 폴더>
const { chromium } = require('playwright');
(async () => {
  const out = process.argv[2];
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1600, height: 1000 } });
  const errs = [];
  p.on('pageerror', (e) => errs.push(e.message));
  p.on('console', (m) => { if (m.type() === 'error') errs.push(m.text()); });
  await p.goto('http://localhost:5397/acui-harness.html');
  await p.waitForTimeout(1500);
  const info = await p.evaluate(() => ({
    details: [...document.querySelectorAll('details')].map((d) => ({ cls: d.className, open: d.open, summary: d.querySelector('summary')?.textContent })),
    topBlocks: [...document.querySelectorAll('#root > div > div > *, #root > div > * > *')].slice(0, 30).map((n) => n.tagName + '.' + n.className + ': ' + (n.textContent || '').slice(0, 60)),
    buttons: [...document.querySelectorAll('button')].map((x) => x.textContent.trim()).filter((v, i, a) => a.indexOf(v) === i).slice(0, 80),
    tables: [...document.querySelectorAll('table')].map((t) => t.className + ' :: ' + [...t.querySelectorAll('thead th')].map((h) => h.textContent.trim()).join(' | ')),
    rows: document.querySelectorAll('[data-row-index]').length,
    chips: document.querySelectorAll('[data-cue-index]').length,
  }));
  console.log(JSON.stringify(info, null, 1));
  console.log('ERRORS', errs);
  await p.screenshot({ path: out + '/01_initial.png', fullPage: true });
  await b.close();
})();
