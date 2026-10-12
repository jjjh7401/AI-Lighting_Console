// t492 — 컨셉 패널 탭 1 「그래서 보이는 것」 사유·4칸 「바꾸려면」·탭 2·3 본문을 헤드리스
// Chrome(1600×1000)으로 확인한다. 화면 글자를 서버 페이로드(payload_roles.json)와 대조한다.
// 실행: vite dev(:5492) 뒤 `NODE_PATH=<playwright> node panel_probe.js <출력 폴더>`
const { chromium } = require('playwright');
const fs = require('fs');

const out = process.argv[2];
const ROLES = JSON.parse(fs.readFileSync(`${__dirname}/payload_roles.json`, 'utf-8'));

async function open(page, query) {
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  page.on('console', (m) => { if (m.type() === 'error') errors.push(`console: ${m.text().slice(0, 300)}`); });
  await page.goto(`http://localhost:5492/acui-harness.html${query}`);
  await page.waitForTimeout(1200);
  await page.click('details.concept-panel > summary');
  await page.waitForTimeout(200);
  return errors;
}

const dl = () =>
  [...document.querySelectorAll('.concept-tab-body .concept-materials > div')].map((d) => ({
    title: d.querySelector('dt')?.textContent,
    text: d.querySelector('dd')?.textContent,
    nodata: d.querySelector('dd')?.classList.contains('concept-nodata') ?? false,
  }));

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
  const r = {};
  const errors = await open(page, '');
  // 탭 1 — 「그래서 보이는 것」 칸과 표 아래 사유
  r.outcome_cells = await page.evaluate(() =>
    [...document.querySelectorAll('.concept-grammar tbody tr:not(.concept-explain-row)')].map((tr) => tr.lastElementChild.textContent),
  );
  r.outcome_note = await page.evaluate(() => document.querySelector('.concept-grammar-note')?.textContent ?? null);
  // 4칸 — 첫 행(Intro, draft)을 연다
  await page.click('.concept-row-toggle');
  await page.waitForTimeout(150);
  r.explain = await page.evaluate(() =>
    [...document.querySelectorAll('.concept-explain > div')].map((d) => [d.querySelector('dt').textContent, d.querySelector('dd').textContent]),
  );
  await page.screenshot({ path: `${out}/panel_tab1.png`, fullPage: false });
  // 4칸이 가리킨 Q 번호의 PLAN CUE 카드에 실제로 수정요청 생성기가 있나
  r.generator_cards = await page.evaluate(() =>
    document.querySelectorAll('.song-timeline-section.has-generator').length,
  );
  // 탭 2
  await page.click('.concept-tab:nth-child(2)');
  await page.waitForTimeout(150);
  r.tab2 = await page.evaluate(dl);
  await page.screenshot({ path: `${out}/panel_tab2.png` });
  // 탭 3
  await page.click('.concept-tab:nth-child(3)');
  await page.waitForTimeout(150);
  r.tab3 = await page.evaluate(dl);
  r.tab3_reserve = await page.evaluate(() => [...document.querySelectorAll('.concept-reserve li')].map((li) => li.textContent));
  await page.screenshot({ path: `${out}/panel_tab3.png` });
  r.page_errors = errors;

  // 서버 값 대조 — 페이로드에서 직접 센다
  const secs = ROLES.sections;
  const reserve = ROLES.concept_report.reserve;
  r.server = {
    section_count: secs.length,
    positions: secs.map((s) => s.position),
    textures: secs.map((s) => s.texture),
    movement_equals_position: secs.every((s) => !s.movement || s.movement === s.position),
    reserve,
    released_section: reserve.map((it) =>
      it.screen_position === null ? null : `Q${String(secs[it.screen_position].cue_number).padStart(3, '0')} ${secs[it.screen_position].label}`,
    ),
    first_status: secs[0].plan_status,
    first_cue: secs[0].cue_number,
  };

  // 기본 실제 세션(인터뷰 경로, 컨셉 리포트 없음) — 탭 3 사유가 서버 사유와 같은가
  const page2 = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
  const errors2 = await open(page2, '?causal');
  await page2.click('.concept-tab:nth-child(3)');
  await page2.waitForTimeout(150);
  r.causal_tab3 = await page2.evaluate(dl);
  r.causal_page_errors = errors2;

  fs.writeFileSync(`${out}/panel_probe.json`, JSON.stringify(r, null, 1));
  console.log(JSON.stringify(r, null, 1));
  await browser.close();
})();
