// t481 — 런북 PLAN CUE 카드 레이아웃·BLIND 잠금 실측(헤드리스 Chrome 1600×1000).
// 하니스: ui/src/acuiHarness.tsx(임시, 커밋 안 함 — 사본 acuiHarness.tsx.txt),
// 데이터: 서버 `_song_timeline_payload` 실출력 36구간(payload_36.json). 콘솔 0.
// 실행: vite dev(:5398) 뒤 `NODE_PATH=<playwright> node layout_probe.js <출력 폴더> <라벨>`
const { chromium } = require('playwright');
const fs = require('fs');

const out = process.argv[2];
const label = process.argv[3];
const BASE = 'http://localhost:5398/acui-harness.html';
const CARDS = [0, 3, 8, 20, 35];

(async () => {
  const b = await chromium.launch();
  const page = await b.newPage({ viewport: { width: 1600, height: 1000 } });
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto(BASE);
  await page.waitForTimeout(1200);
  const result = { label, viewport: '1600x1000' };

  // 1) 타임라인 컨테이너가 사람이 가로로 굴릴 수 있는가, 카드가 처음부터 보이는가.
  result.container = await page.evaluate((cards) => {
    const box = (() => { const t = document.querySelector('.song-timeline-track'); const o = getComputedStyle(t).overflowX; return o === 'auto' || o === 'scroll' ? t : document.querySelector('.song-timeline'); })();
    const cs = getComputedStyle(box);
    const br = box.getBoundingClientRect();
    const all = [...document.querySelectorAll('.song-timeline-section')];
    return {
      overflowX: cs.overflowX,
      scrollWidth: box.scrollWidth,
      clientWidth: box.clientWidth,
      userScrollable: (cs.overflowX === 'auto' || cs.overflowX === 'scroll') && box.scrollWidth > box.clientWidth,
      cardsTotal: all.length,
      cardsFullyVisibleWithoutScroll: all.filter((a) => {
        const r = a.getBoundingClientRect();
        return r.left >= br.left - 1 && r.right <= br.right + 1;
      }).length,
      cardWidths: cards.map((i) => Math.round(all[i].getBoundingClientRect().width)),
    };
  }, CARDS);

  // 2) 카드별 생성기 버튼·입력 히트 테스트. 가로는 사람이 할 수 있는 방식으로만
  //    옮긴다: 컨테이너가 굴러가면 scrollLeft 를 준다(휠·스크롤바와 같은 효과),
  //    overflow: hidden 이면 옮기지 않는다 — 사람이 옮길 수 없으니까.
  result.cards = [];
  for (const i of CARDS) {
    const r = await page.evaluate((idx) => {
      const box = (() => { const t = document.querySelector('.song-timeline-track'); const o = getComputedStyle(t).overflowX; return o === 'auto' || o === 'scroll' ? t : document.querySelector('.song-timeline'); })();
      const art = document.querySelectorAll('.song-timeline-section')[idx];
      const cs = getComputedStyle(box);
      const scrollable = cs.overflowX === 'auto' || cs.overflowX === 'scroll';
      if (scrollable) {
        box.scrollLeft = 0;
        const target = art.getBoundingClientRect().left - box.getBoundingClientRect().left - 20;
        box.scrollLeft = Math.max(0, target);
      }
      window.scrollTo(0, window.scrollY + art.querySelector('.plan-cue-generator').getBoundingClientRect().top - 60);
      const g = art.querySelector('.plan-cue-generator');
      const controls = [...g.querySelectorAll('button, input')];
      let ok = 0;
      const blocked = [];
      for (const el of controls) {
        const cr = el.getBoundingClientRect();
        const x = cr.left + cr.width / 2;
        const y = cr.top + cr.height / 2;
        const inViewport = x >= 0 && x <= innerWidth && y >= 0 && y <= innerHeight;
        const top = inViewport ? document.elementFromPoint(x, y) : null;
        if (top && (top === el || el.contains(top))) ok++;
        else blocked.push({ el: (el.textContent || el.placeholder || el.type).trim().slice(0, 12), why: !inViewport ? 'offscreen' : (top?.closest('article')?.getAttribute('aria-label') ?? top?.className ?? 'none') });
      }
      return {
        card: idx,
        label: art.getAttribute('aria-label'),
        article_width: Math.round(art.getBoundingClientRect().width),
        generator_scrollWidth: g.scrollWidth,
        generator_clientWidth: g.clientWidth,
        controls: controls.length,
        clickable: ok,
        blocked: blocked.slice(0, 8),
      };
    }, i);
    result.cards.push(r);
  }

  // 3) 실제 마우스 클릭: 카드 3 「적용」(밝기)을 좌표로 누른다(5초 제한).
  const g3 = page.locator('.plan-cue-generator').nth(3);
  await page.evaluate(() => { const box = (() => { const t = document.querySelector('.song-timeline-track'); const o = getComputedStyle(t).overflowX; return o === 'auto' || o === 'scroll' ? t : document.querySelector('.song-timeline'); })(); box.scrollLeft = 0; });
  await g3.scrollIntoViewIfNeeded();
  await g3.locator('input[type=number]').nth(0).fill('90');
  try {
    await g3.locator('.plan-cue-generator-field').nth(0).locator('button', { hasText: '적용' }).click({ timeout: 5000 });
    result.card3_real_mouse_click_apply = { clicked: true, stack: await g3.locator('.plan-cue-generator-diff').count() };
  } catch (e) {
    result.card3_real_mouse_click_apply = { clicked: false, error: e.message.split('\n')[0] };
  }
  await page.screenshot({ path: `${out}/${label}_card3.png`, clip: await g3.evaluate((g) => { const a = g.closest('article').getBoundingClientRect(); return { x: Math.max(0, a.left - 20), y: Math.max(0, a.top - 10), width: Math.min(760, 1600 - Math.max(0, a.left - 20)), height: Math.min(990, a.height + 20) }; }) });

  // 4) BLIND 잠금(?blind — 각 구간에 BLIND 칩만 덧붙임, reserve 는 서버 값 그대로).
  const p2 = await b.newPage({ viewport: { width: 1600, height: 1000 } });
  await p2.goto(`${BASE}?blind`);
  await p2.waitForTimeout(1200);
  result.blind = await p2.evaluate(() =>
    [...document.querySelectorAll('.plan-cue-generator')].map((g) => {
      const chip = [...g.querySelectorAll('.plan-cue-chip')].find((c) => c.textContent.includes('BLIND'));
      return chip ? (chip.disabled ? 'L' : 'u') : '?';
    }).join(''),
  );
  result.blind_legend = 'L=잠김 u=풀림, 카드 0..35 순서. 서버 reserve BLIND released_q=45 screen_position=33';

  result.page_errors = errors;
  fs.writeFileSync(`${out}/layout_${label}.json`, JSON.stringify(result, null, 1));
  console.log(JSON.stringify(result, null, 1));
  await b.close();
})().catch((e) => { console.error('FAILED', e); process.exit(1); });
