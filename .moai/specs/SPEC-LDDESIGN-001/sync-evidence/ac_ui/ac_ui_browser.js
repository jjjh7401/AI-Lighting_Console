// SPEC-LDDESIGN-001 AC-UI 마무리 — 런북 화면을 헤드리스 Chrome 으로 실제로 눌러 본다.
// 데이터: payload_36.json(서버 `_song_timeline_payload` 실출력, 36구간). 콘솔 접촉 0.
// 서버로 나가는 호출은 하니스(ui/src/acuiHarness.tsx 사본: acuiHarness.tsx.txt)가
// window.__calls 에 기록한다. 프리셋 풀 API(/api/presets/N)만 가짜 응답으로 가로챈다.
// 실행: vite dev(:5397) 뒤 `NODE_PATH=<playwright> node ac_ui_browser.js <출력 폴더>`
const { chromium } = require('playwright');
const fs = require('fs');

const BASE = 'http://localhost:5397';
const out = process.argv[2];
const results = {};
const PAYLOAD = JSON.parse(fs.readFileSync(__dirname + '/payload_36.json', 'utf-8'));
const log = (ac, key, value) => {
  results[ac] = results[ac] || {};
  results[ac][key] = value;
};

async function mockPools(page) {
  await page.route('**/api/presets/*', async (route) => {
    const no = Number(route.request().url().split('/').pop());
    const presets =
      no === 1
        ? [{ no: 18, name: '1.18 Dim 90' }, { no: 19, name: 'Dim 90 Warm' }]
        : no === 4
          ? [{ no: 3, name: 'Red' }, { no: 5, name: 'Deep Blue' }]
          : [{ no: 1, name: `Pool${no} A` }];
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ pool: { no, name: `pool-${no}` }, presets, truncated: false, total: presets.length }),
    });
  });
}

const gen = (page, i) => page.locator('.plan-cue-generator').nth(i);
const calls = (page) => page.evaluate(() => window.__calls.slice());
const btn = (scope, text) => scope.locator('button', { hasText: text });

(async () => {
  const b = await chromium.launch();
  const page = await b.newPage({ viewport: { width: 1600, height: 1000 } });
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await mockPools(page);
  await page.goto(`${BASE}/acui-harness.html`);
  await page.waitForTimeout(1200);

  // ---------- AC-018 레이아웃·컨셉 패널 ----------
  log('AC-018', 'block_order', await page.evaluate(() => {
    const want = ['runbook-header', 'concept-panel', 'cue-sheet-timeline', 'song-timeline', 'runbook-gate'];
    const nodes = [...document.querySelectorAll(want.map((c) => '.' + c).join(','))];
    return nodes.map((n) => want.find((c) => n.classList.contains(c)));
  }));
  log('AC-018', 'timeline_before_sheet_inside_cue_sheet_timeline', await page.evaluate(() => {
    const root = document.querySelector('.cue-sheet-timeline');
    const rail = root.querySelector('[data-cue-index]');
    const row = root.querySelector('[data-row-index]');
    return !!(rail && row && (rail.compareDocumentPosition(row) & Node.DOCUMENT_POSITION_FOLLOWING));
  }));
  log('AC-018', 'concept_panel_open_by_default', await page.evaluate(() => document.querySelector('details.concept-panel').open));
  await page.click('details.concept-panel > summary');
  await page.waitForTimeout(200);
  log('AC-018', 'concept_panel_after_click', await page.evaluate(() => {
    const p = document.querySelector('details.concept-panel');
    return {
      open: p.open,
      clickable_items_besides_tabs: [...p.querySelectorAll('button, [role=button], summary, a')].filter((n) => n.getAttribute('role') !== 'tab' && !n.closest('summary') && n.tagName !== 'SUMMARY').length,
      explanation_cells_4: [...p.querySelectorAll('*')].filter((n) => /무슨 뜻|무대에서|왜 이렇게 제안했나|바꾸려면/.test(n.textContent) && n.children.length === 0).length,
      nodata_lines: [...p.querySelectorAll('.concept-nodata')].map((n) => n.textContent.trim()).filter((v, i, a) => a.indexOf(v) === i),
      grammar_headers: [...p.querySelectorAll('table.concept-grammar thead th')].map((n) => n.textContent.trim()),
      grammar_first_row: [...p.querySelectorAll('table.concept-grammar tbody tr:first-child td')].map((n) => n.textContent.trim()),
    };
  }));
  await page.screenshot({ path: `${out}/02_concept_open.png`, clip: { x: 0, y: 0, width: 1600, height: 900 } });

  // ---------- AC-050 탭 라벨 ----------
  log('AC-050', 'tabs', await page.evaluate(() =>
    [...document.querySelectorAll('.concept-tab')].map((t) => {
      const small = t.querySelector('small');
      const label = [...t.childNodes].filter((n) => n.nodeType === 3).map((n) => n.textContent).join('').trim();
      return {
        label,
        sub: small?.textContent,
        label_font_px: parseFloat(getComputedStyle(t).fontSize),
        sub_font_px: small ? parseFloat(getComputedStyle(small).fontSize) : null,
      };
    }),
  ));
  await page.click('details.concept-panel > summary'); // 다시 접는다

  // ---------- AC-019 Q### 세 곳 + 14열 + 색 레일 ----------
  log('AC-019', 'q_label_three_places_idx3', await page.evaluate(() => {
    const chip = document.querySelector('[data-cue-index="3"]')?.textContent.trim();
    const row = document.querySelector('[data-row-index="3"] td')?.textContent.trim();
    const card = document.querySelectorAll('.song-timeline .plan-cue-generator')[3]?.closest('[class*="card"], article, li, div')?.parentElement;
    const cards = [...document.querySelectorAll('.song-timeline *')].filter((n) => n.children.length === 0 && /^Q1\d\d$/.test(n.textContent.trim()));
    return { chip, row, plan_cue_badges_in_order: cards.map((n) => n.textContent.trim()).slice(0, 6) };
  }));
  log('AC-019', 'all_36_consistent', await page.evaluate(() => {
    const chips = [...document.querySelectorAll('[data-cue-index]')].map((n) => n.textContent.trim());
    const rows = [...document.querySelectorAll('[data-row-index]')].map((n) => n.querySelector('td').textContent.trim());
    const badges = [...document.querySelectorAll('.song-timeline *')].filter((n) => n.children.length === 0 && /^Q1\d\d$/.test(n.textContent.trim())).map((n) => n.textContent.trim());
    return { n: chips.length, chips_eq_rows: JSON.stringify(chips) === JSON.stringify(rows), chips_eq_badges: JSON.stringify(chips) === JSON.stringify(badges), badges_n: badges.length };
  }));
  log('AC-019', 'sheet_headers', await page.evaluate(() => [...document.querySelectorAll('.cst-sheet thead th')].map((n) => n.textContent.trim())));
  log('AC-019', 'color_rail_vs_hex_first6', await page.evaluate(() =>
    [...document.querySelectorAll('[data-row-index]')].slice(0, 6).map((r) => {
      const td = r.querySelector('td');
      const cs = getComputedStyle(td);
      return { q: td.textContent.trim(), boxShadow: cs.boxShadow, borderLeft: `${cs.borderLeftWidth} ${cs.borderLeftColor}` };
    }),
  ));

  // ---------- AC-020 블록 색 = HEX, 스크롤 연동, GATE ----------
  log('AC-020', 'block_color_vs_hex', await page.evaluate(async (payload) => {
    const toHex = (rgb) => {
      const m = rgb.match(/\d+/g);
      return m ? '#' + m.slice(0, 3).map((x) => Number(x).toString(16).padStart(2, '0')).join('').toUpperCase() : rgb;
    };
    const chips = [...document.querySelectorAll('[data-cue-index]')];
    let match = 0;
    const mism = [];
    chips.forEach((c, i) => {
      const bg = toHex(getComputedStyle(c).backgroundColor);
      const want = payload.sections[i].palette_primary_hex;
      if (bg === want) match++;
      else mism.push({ i, bg, want });
    });
    return { total: chips.length, match, mismatches: mism.slice(0, 5) };
  }, PAYLOAD));
  const scrollProbe = async () => page.evaluate(() => {
    const sheet = document.querySelector('.cst-sheet-scroll') || document.querySelector('[data-row-index]').closest('div');
    const rail = document.querySelector('[data-cue-index]').parentElement.closest('div[class]');
    let railBox = document.querySelector('[data-cue-index]');
    while (railBox && railBox.scrollWidth <= railBox.clientWidth) railBox = railBox.parentElement;
    const sb = sheet.getBoundingClientRect();
    const mid = sb.top + sb.height / 2;
    const rows = [...document.querySelectorAll('[data-row-index]')];
    const center = rows.find((r) => { const b = r.getBoundingClientRect(); return b.top <= mid && b.bottom >= mid; });
    const idx = center ? Number(center.dataset.rowIndex) : null;
    const chip = idx !== null ? document.querySelector(`[data-cue-index="${idx}"]`) : null;
    const rb = railBox.getBoundingClientRect();
    const cb = chip?.getBoundingClientRect();
    return {
      sheetScrollTop: Math.round(sheet.scrollTop),
      railScrollLeft: Math.round(railBox.scrollLeft),
      centerRowIndex: idx,
      centerChipVisibleInRail: cb ? cb.left >= rb.left - 1 && cb.right <= rb.right + 1 : null,
      selected: document.querySelector('tr.is-selected td')?.textContent.trim() ?? null,
    };
  });
  const before = await scrollProbe();
  const sheetEl = page.locator('[data-row-index="0"]');
  await sheetEl.hover();
  for (let k = 0; k < 12; k++) { await page.mouse.wheel(0, 120); await page.waitForTimeout(60); }
  await page.waitForTimeout(1200);
  const after = await scrollProbe();
  log('AC-020', 'sheet_wheel_scroll', { before, after });
  await page.screenshot({ path: `${out}/03_after_sheet_scroll.png`, clip: { x: 0, y: 150, width: 1600, height: 800 } });
  log('AC-020', 'gate_bar', await page.evaluate(() => document.querySelector('.runbook-gate')?.textContent.replace(/\s+/g, ' ').slice(0, 120)));

  // ---------- AC-034 마운트 ----------
  log('AC-034', 'generators_mounted_with_onGeneratorSend', await page.locator('.plan-cue-generator').count());

  // ---------- 생성기 조작 가능성: 실제 마우스 히트 테스트 ----------
  // 사람이 누르는 좌표(버튼 중앙)에 무엇이 있는지 elementFromPoint 로 잰다.
  await gen(page, 3).scrollIntoViewIfNeeded();
  log('HIT', 'card3_controls_hit_test', await gen(page, 3).evaluate((g) =>
    [...g.querySelectorAll('button, input')].map((el) => {
      const r = el.getBoundingClientRect();
      const top = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
      const owner = top && top.closest('article');
      return { el: (el.textContent || el.placeholder || el.type).trim().slice(0, 14), hitsItself: top === el || el.contains(top), coveredBy: top && !(top === el || el.contains(top)) ? (owner ? owner.getAttribute('aria-label') : top.className) : null };
    }),
  ));
  log('HIT', 'card_vs_generator_width', await page.evaluate(() => {
    const g = document.querySelectorAll('.plan-cue-generator')[3];
    const art = g.closest('article');
    return { article_width: Math.round(art.getBoundingClientRect().width), generator_scroll_width: g.scrollWidth, generator_client_width: g.clientWidth };
  }));
  await page.screenshot({ path: `${out}/05_card3_overlap.png`, clip: await gen(page, 3).evaluate((g) => { const a = g.closest('article').getBoundingClientRect(); return { x: Math.max(0, a.left - 20), y: Math.max(0, a.top + window.scrollY - window.scrollY), width: Math.min(700, 1600 - a.left + 20), height: Math.min(1000, a.height) }; }) });

  // 이하 조작은 좌표 클릭 대신 클릭 이벤트를 요소에 직접 보낸다(겹침 우회 — 위 HIT 가 겹침 자체의 증거).
  // 생성기 조작은 3번 카드(Q104 · Chorus 1)에서 한다.
  const g = gen(page, 3);
  await g.scrollIntoViewIfNeeded();

  // ---------- AC-035 혼합 ----------
  const before035 = await g.locator('.plan-cue-generator-before').textContent();
  await btn(g, 'KEY').dispatchEvent('click');
  await btn(g, 'BACK').dispatchEvent('click');
  log('AC-035', 'intensity_before_label', { no_selection: before035, key_and_back: await g.locator('.plan-cue-generator-before').textContent() });
  log('AC-035', 'color_label_key_and_back', await g.locator('.plan-cue-generator-row').nth(1).textContent());

  // ---------- AC-052 / AC-042 / AC-043 ----------
  await g.locator('input[type=number]').nth(0).fill('90');
  await g.locator('.plan-cue-generator-field').nth(0).locator('button', { hasText: '적용' }).dispatchEvent('click');
  await g.locator('input[type=number]').nth(1).fill('3');
  await g.locator('.plan-cue-generator-field').nth(1).locator('button', { hasText: '적용' }).dispatchEvent('click');
  await btn(g.locator('[aria-label="전환"]'), 'SNAP').dispatchEvent('click');
  await btn(g.locator('[aria-label="트래킹"]'), 'Block').dispatchEvent('click');
  const lines = async () => g.locator('.plan-cue-generator-diff').evaluateAll((ns) => ns.map((n) => n.firstElementChild.textContent));
  const four = await lines();
  log('AC-052', 'stack_before', four);
  log('AC-043', 'buttons_containing_되돌리기_with_stack_filled', await page.evaluate(() =>
    [...document.querySelectorAll('button')].map((b) => b.textContent.trim()).filter((t) => t.includes('되돌리기')),
  ));
  log('AC-043', 'buttons_exact_선택취소_count', await page.evaluate(() => [...document.querySelectorAll('button')].filter((b) => b.textContent.trim() === '선택 취소').length));
  await g.locator('.plan-cue-generator-diff').nth(1).locator('.plan-cue-generator-remove').dispatchEvent('click');
  log('AC-052', 'stack_after_x_on_line2', await lines());
  const callsBeforeCancel = (await calls(page)).length;
  await btn(g.locator('.plan-cue-generator-actions'), '선택 취소').dispatchEvent('click');
  log('AC-052', 'stack_after_cancel_all', await lines());
  const afterCancel = await calls(page);
  log('AC-042', 'calls_emitted_by_cancel', afterCancel.slice(callsBeforeCancel));
  log('AC-042', 'timeline_draft_undo_count_total', afterCancel.filter((c) => c.kind === 'timeline_draft_undo').length);

  // ---------- AC-036 프리셋 이름 ----------
  await g.locator('.plan-cue-generator-row').nth(2).locator('button', { hasText: '바꾸기' }).dispatchEvent('click');
  await page.waitForTimeout(400);
  const popupText = await page.locator('body').evaluate(() => [...document.querySelectorAll('button, li')].map((n) => n.textContent.trim()).filter((t) => /Dim 90/.test(t)));
  log('AC-036', 'popup_entries', popupText);
  await page.locator('button, li', { hasText: '1.18 Dim 90' }).first().dispatchEvent('click');
  await page.waitForTimeout(200);
  log('AC-036', 'dimmer_row_label', await g.locator('.plan-cue-generator-row').nth(2).textContent());

  // ---------- AC-038 / AC-053 / AC-041 / AC-044 ----------
  await btn(g, 'BACK').dispatchEvent('click'); // KEY 만 남긴다
  await g.locator('input[type=number]').nth(0).fill('95');
  await g.locator('.plan-cue-generator-field').nth(0).locator('button', { hasText: '적용' }).dispatchEvent('click');
  await g.locator('.plan-cue-generator-row').nth(1).locator('button', { hasText: '바꾸기' }).dispatchEvent('click');
  await page.waitForTimeout(400);
  await page.locator('button, li', { hasText: 'Red' }).first().dispatchEvent('click');
  await page.waitForTimeout(200);
  await g.locator('.plan-cue-generator-free-text input').fill('그리고 이 구간 전체를 반 박자 당겨줘');
  const stackDom = async () => g.locator('.plan-cue-generator-diff').evaluateAll((ns) => ns.map((n) => ({
    cls: n.className,
    diff: n.firstElementChild.textContent,
    warnings: [...n.querySelectorAll('.plan-cue-generator-warning')].map((w) => w.textContent),
  })));
  log('AC-038', 'status_label_before_send', await g.locator('.plan-cue-generator-status').textContent());
  log('AC-038', 'stack_lines_with_their_warnings', await stackDom());
  log('AC-038', 'warnings_outside_diff_lines', await g.evaluate((n) => [...n.querySelectorAll('.plan-cue-generator-warning')].filter((w) => !w.closest('.plan-cue-generator-diff')).length));
  const badge = async () => page.evaluate(() => [...document.querySelectorAll('*')].filter((n) => n.children.length === 0 && /되돌리기 \d+단계/.test(n.textContent)).map((n) => n.textContent.trim())[0] ?? null);
  const badgeBefore = await badge();
  const n0 = (await calls(page)).length;
  await g.locator('.plan-cue-generator-submit').dispatchEvent('click');
  await page.waitForTimeout(200);
  log('AC-038', 'status_label_after_send', await g.locator('.plan-cue-generator-status').textContent());
  log('AC-038', 'line_states_after_send', (await stackDom()).map((l) => l.cls));
  await page.evaluate(() => window.__accept());
  await page.waitForTimeout(300);
  log('AC-038', 'line_states_after_first_accept', (await stackDom()).map((l) => l.cls));
  await page.evaluate(() => window.__accept());
  await page.waitForTimeout(300);
  const sent = (await calls(page)).slice(n0);
  log('AC-041', 'sentences_sent_via_chat', sent);
  log('AC-053', 'free_text_appended_verbatim', sent.map((c) => c.text?.endsWith('그리고 이 구간 전체를 반 박자 당겨줘')));
  log('AC-044', 'stack_after_all_accepted', await lines());
  log('AC-044', 'undo_badge', { before: badgeBefore, after: await badge(), items_sent: sent.length });
  await page.screenshot({ path: `${out}/04_generator_after_accept.png`, fullPage: false });

  // ---------- AC-037 BLIND 잠금 (?blind — BLIND 칩 주입, reserve 는 서버 값 그대로) ----------
  const p2 = await b.newPage({ viewport: { width: 1600, height: 1000 } });
  await p2.goto(`${BASE}/acui-harness.html?blind`);
  await p2.waitForTimeout(1200);
  log('AC-037', 'reserve_from_server', PAYLOAD.concept_report.reserve);
  log('AC-037', 'blind_chip_state_by_card', await p2.evaluate(() =>
    [...document.querySelectorAll('.plan-cue-generator')].map((gnode, i) => {
      const chip = [...gnode.querySelectorAll('.plan-cue-chip')].find((c) => c.textContent.includes('BLIND'));
      return { card: i, locked: chip ? chip.disabled : null };
    }).filter((x, i) => [0, 3, 31, 32, 33, 34, 35].includes(i)),
  ));
  const g2 = gen(p2, 3);
  await g2.scrollIntoViewIfNeeded();
  await g2.locator('.plan-cue-chip', { hasText: 'BLIND' }).dispatchEvent('click');
  log('AC-037', 'card3_blind_selected_after_click', await g2.locator('.plan-cue-chip', { hasText: 'BLIND' }).getAttribute('aria-pressed'));

  // ---------- AC-034 음성 대조: onGeneratorSend 없는 기존 미리보기 ----------
  const p3 = await b.newPage();
  await p3.goto(`${BASE}/runbook-preview.html`);
  await p3.waitForTimeout(1200);
  log('AC-034', 'generators_mounted_without_onGeneratorSend(runbook-preview.html)', await p3.locator('.plan-cue-generator').count());
  log('AC-034', 'plan_cue_cards_in_preview', await p3.evaluate(() => [...document.querySelectorAll('*')].filter((n) => n.children.length === 0 && /^PLAN CUE$/.test(n.textContent.trim())).length));

  results.page_errors = errors;
  fs.writeFileSync(`${out}/ac_ui_browser_result.json`, JSON.stringify(results, null, 1));
  console.log(JSON.stringify(results, null, 1));
  await b.close();
})().catch((e) => { console.error('FAILED', e); process.exit(1); });
