// t485 — 컨셉 패널 탭 1 인과 불릿을 헤드리스 Chrome(1600×1000)으로 확인한다.
// 데이터: payload_causal.json / payload_blank.json(실제 세션 인터뷰 → 타임라인 이벤트).
// 화면에 보인 글자를 서버 페이로드의 원문과 바이트 대조한다.
// 실행: vite dev(:5485) 뒤 `NODE_PATH=<playwright> node bullet_probe.js <출력 폴더>`
const { chromium } = require('playwright');
const fs = require('fs');

const out = process.argv[2];
const CAUSAL = JSON.parse(fs.readFileSync(`${__dirname}/payload_causal.json`, 'utf-8'));
const BLANK = JSON.parse(fs.readFileSync(`${__dirname}/payload_blank.json`, 'utf-8'));

async function read(page, query, shot) {
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  page.on('console', (m) => { if (m.type() === 'error') errors.push(`console: ${m.text().slice(0, 400)}`); });
  await page.goto(`http://localhost:5485/acui-harness.html${query}`);
  await page.waitForTimeout(1200);
  const r = {};
  if (!(await page.$('details.concept-panel'))) {
    r.panel_missing = true;
    r.root_html_length = (await page.innerHTML('#root')).length;
    r.page_errors = errors;
    return r;
  }
  r.panel_open_by_default = await page.evaluate(() => document.querySelector('details.concept-panel').open);
  r.runbook_blocks_before_open = await page.evaluate(() =>
    [...document.querySelectorAll('section, [class*="runbook"]')].length,
  );
  await page.click('details.concept-panel > summary');
  await page.waitForTimeout(200);
  r.active_tab = await page.evaluate(() => document.querySelector('.concept-tab.is-active')?.textContent);
  r.badge = await page.evaluate(() => document.querySelector('.concept-verbatim-badge')?.textContent ?? null);
  r.origin = await page.evaluate(() => document.querySelector('.concept-bullets-head small')?.textContent ?? null);
  r.lines = await page.evaluate(() => [...document.querySelectorAll('.concept-bullet')].map((li) => li.textContent));
  r.nodata = await page.evaluate(() =>
    [...document.querySelectorAll('.concept-tab-body > .concept-nodata')].map((p) => p.textContent),
  );
  r.grammar_last_header = await page.evaluate(() =>
    [...document.querySelectorAll('.concept-grammar th')].map((th) => th.textContent).pop(),
  );
  await page.locator('details.concept-panel').screenshot({ path: `${out}/${shot}` });
  r.page_errors = errors;
  return r;
}

(async () => {
  const b = await chromium.launch();
  const result = { viewport: '1600x1000' };

  const p1 = await b.newPage({ viewport: { width: 1600, height: 1000 } });
  result.causal = await read(p1, '', 'concept_bullet_causal.png');
  const expected = CAUSAL.concept_bullet.text.split('\n').filter((l) => l.trim() !== '');
  result.causal.expected_lines = expected;
  result.causal.lines_match = !result.causal.panel_missing && JSON.stringify(result.causal.lines) === JSON.stringify(expected);
  result.causal.origin_match = result.causal.origin === CAUSAL.concept_bullet.origin_label;

  const p2 = await b.newPage({ viewport: { width: 1600, height: 1000 } });
  result.blank = await read(p2, '?blank', 'concept_bullet_blank.png');

  // 기존 결함 재현(우회 없이 서버 페이로드 그대로) — 런북이 빈다.
  const p3 = await b.newPage({ viewport: { width: 1600, height: 1000 } });
  result.raw_payload_without_workaround = await read(p3, '?raw', 'raw_payload.png');
  result.blank.reason_shown = (result.blank.nodata ?? []).some((t) => t.includes(BLANK.concept_bullet.reason));

  await b.close();
  fs.writeFileSync(`${out}/bullet_probe.json`, JSON.stringify(result, null, 1));
  console.log(JSON.stringify(result, null, 1));
})();
