// t482 — 컨셉 패널 "한눈에" 카드·4칸 설명을 헤드리스 Chrome(1600×1000)으로 확인한다.
// 데이터: payload_roles.json(서버 `_song_timeline_payload` 실출력, 역할은 실제 판정기).
// 카드 수치를 같은 화면의 CUE SHEET 에서 읽은 값과 대조한다(REQ-097 "시트와 같은 원천").
// 실행: vite dev(:5399) 뒤 `NODE_PATH=<playwright> node glance_probe.js <출력 폴더>`
const { chromium } = require('playwright');
const fs = require('fs');

const out = process.argv[2];
const PAYLOAD = JSON.parse(fs.readFileSync(`${__dirname}/payload_roles.json`, 'utf-8'));

(async () => {
  const b = await chromium.launch();
  const page = await b.newPage({ viewport: { width: 1600, height: 1000 } });
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto('http://localhost:5399/acui-harness.html');
  await page.waitForTimeout(1200);
  const result = { viewport: '1600x1000' };

  result.panel_open_by_default = await page.evaluate(() => document.querySelector('details.concept-panel').open);
  await page.click('details.concept-panel > summary');
  await page.waitForTimeout(200);

  // 1) 카드 읽기
  result.analysis = await page.locator('.concept-glance-analysis').textContent();
  result.cards = await page.evaluate(() =>
    [...document.querySelectorAll('.concept-glance-card')].map((c) => {
      const pairs = {};
      const dts = [...c.querySelectorAll('dt')];
      dts.forEach((dt) => { pairs[dt.textContent] = dt.nextElementSibling?.textContent ?? null; });
      return {
        stage: c.querySelector('strong')?.textContent,
        empty: c.classList.contains('is-empty') ? c.querySelector('.concept-nodata')?.textContent : null,
        bar: getComputedStyle(c.querySelector('.concept-glance-bar')).backgroundColor,
        ...pairs,
      };
    }),
  );

  // 2) 같은 화면의 CUE SHEET 에서 같은 구간을 읽어 대조한다.
  const sheet = await page.evaluate(() =>
    [...document.querySelectorAll('[data-row-index]')].map((r) => {
      const tds = [...r.querySelectorAll('td')];
      const heads = [...document.querySelectorAll('.cst-sheet thead th')].map((h) => h.textContent.trim());
      const at = (name) => tds[heads.indexOf(name)]?.textContent.trim();
      return { q: at('Q#'), section: at('구간'), time: at('시각'), bright: at('밝기'), rail: getComputedStyle(tds[0]).borderLeftColor };
    }),
  );
  result.sheet = sheet;
  const toHex = (rgb) => '#' + rgb.match(/\d+/g).slice(0, 3).map((x) => Number(x).toString(16).padStart(2, '0')).join('').toUpperCase();
  result.cross_check = PAYLOAD.concept_report.glance.stages.map((stage, i) => {
    const card = result.cards[i];
    if (stage.positions.length === 0) return { stage: stage.stage, empty: true, card_empty: card.empty };
    const rows = stage.positions.map((p) => sheet[p]);
    const first = rows[0];
    const last = rows[rows.length - 1];
    const expectQ = first.q === last.q ? first.q : `${first.q}–${last.q}`;
    const railHexes = [...new Set(rows.map((r) => toHex(r.rail)))];
    const levels = rows.flatMap((r) => (r.bright.match(/\d+/g) || []).map(Number));
    return {
      stage: stage.stage,
      q_card: card.Q, q_sheet: expectQ, q_match: card.Q === expectQ,
      sections_card: card['구간'], sections_sheet: rows.map((r) => r.section).join(' · '),
      time_start_card: card['시간']?.split('–')[0], time_start_sheet: first.time,
      time_match: card['시간']?.split('–')[0] === first.time,
      hex_card: card['색'], hex_sheet_rails: railHexes.join(' '), hex_match: card['색'] === railHexes.join(' '),
      bright_card: card['밝기'], bright_sheet_minmax: `${Math.min(...levels)}–${Math.max(...levels)}%`,
      bright_match: card['밝기'] === `${Math.min(...levels)}–${Math.max(...levels)}%`,
      line: card['한 줄'],
    };
  });

  // 3) 구간 행 클릭 → 4칸 설명
  const toggle = page.locator('.concept-row-toggle').nth(3);
  await toggle.click();
  await page.waitForTimeout(200);
  result.explain_row3 = await page.evaluate(() =>
    [...document.querySelectorAll('.concept-explain div')].map((d) => ({ title: d.querySelector('dt').textContent, text: d.querySelector('dd').textContent })),
  );
  result.explain_expected_description = PAYLOAD.concept_report.rows.find((r) => r.kind === 'section' && r.screen_position === 3)?.description;
  result.still_nodata = await page.evaluate(() => ({
    causal: [...document.querySelectorAll('.concept-nodata')].map((n) => n.textContent).filter((t) => t.includes('인과 불릿')),
    so_visible_cells: [...document.querySelectorAll('table.concept-grammar tbody tr:not(.concept-explain-row) td:last-child')].map((n) => n.textContent)
      .filter((v, i, a) => a.indexOf(v) === i),
  }));
  const panel = await page.locator('details.concept-panel').boundingBox();
  await page.screenshot({ path: `${out}/concept_panel_open.png`, clip: { x: 0, y: Math.max(0, panel.y - 10), width: 1600, height: Math.min(1400, panel.height + 20) }, fullPage: true });

  result.page_errors = errors;
  fs.writeFileSync(`${out}/glance_probe.json`, JSON.stringify(result, null, 1));
  console.log(JSON.stringify({ analysis: result.analysis, cross_check: result.cross_check, explain_row3: result.explain_row3, expected: result.explain_expected_description, still_nodata: result.still_nodata, open_default: result.panel_open_by_default, errors }, null, 1));
  await b.close();
})().catch((e) => { console.error('FAILED', e); process.exit(1); });
