"""v27 test: History, card names from the dictionary headword, tiles that match their scene, page headings, search, New cards.

    python3 tools/app-test/test_history.py . --out shots/history/

Uses the 30-card "Vocabulary" deck from test_study.py, with one card whose stored word ("be candid about") differs from its
dictionary headword ("candor"). Checks the smaller home title, the count line sitting right under every page title (2A),
the empty search (no "words saved" line, "Search anything"), the card's name everywhere (study header, tiles, the queue,
search) while search still finds the stored word, the History icon and page (grouped by day, studied cards in blue, select
and remove, clear the last hour, clear all, Back), New cards not moving when a card is held, tiles of article and magazine
cards redrawn from what they show, re-imports reporting "already up to date", and JavaScript errors.
"""
import argparse, asyncio, json, os, sys, tempfile, zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import Phone
from test_study import vocab_zip


def named_zip(src, path):
    """The Vocabulary zip with test-candor's stored word changed, so it differs from its headword."""
    z = zipfile.ZipFile(src); man = json.loads(z.read('manifest.json'))
    for c in man['decks'][0]['cards']:
        if c['id'] == 'test-candor': c['word'] = 'be candid about'
    with zipfile.ZipFile(path, 'w') as out:
        for n in z.namelist():
            if n != 'manifest.json': out.writestr(n, z.read(n))
        out.writestr('manifest.json', json.dumps(man))


async def main(app, out):
    os.makedirs(out, exist_ok=True)
    fails = []
    def check(ok, what):
        print(('PASS ' if ok else 'FAIL ') + what)
        if not ok: fails.append(what)
    tmp = tempfile.mkdtemp(); vz = os.path.join(tmp, 'vocab.zip'); nz = os.path.join(tmp, 'named.zip')
    vocab_zip(vz); named_zip(vz, nz)
    async with Phone(app) as ph:
        pg = ph.pg
        top = '.page:last-child'
        async def tap(sel): await pg.locator(sel).first.click(); await pg.wait_for_timeout(450)
        box = lambda sel: pg.locator(sel).first.bounding_box()
        async def textx(sel):  # where the text itself starts (padding moves the text, not the box)
            return await pg.evaluate("s => { const e = document.querySelector(s), w = document.createTreeWalker(e, NodeFilter.SHOW_TEXT); let n; while ((n = w.nextNode()) && !n.textContent.trim()); const r = document.createRange(); r.selectNodeContents(n); const b = r.getBoundingClientRect(); return {x: b.x, y: b.y, h: b.height}; }", sel)
        async def lined(sel):
            t, c = await textx(f'{top} .pbar .pt'), await textx(sel)
            return abs(t['x'] - c['x']) < 1.5, c['y'] - (t['y'] + t['h'])
        print('import:', await ph.imp([nz]))
        await pg.wait_for_function("T.SD.loaded && T.HI.loaded")

        # 1C: the home title
        fs = await pg.evaluate("getComputedStyle(document.querySelector('#home .bar h1')).fontSize")
        check(fs == '24px', f'"Your decks" is 24px ({fs})')
        await ph.shot(f'{out}/01-home.png')

        # the tiles of the article and magazine cards are redrawn from what they show
        await pg.wait_for_function("['test-ephemeral','test-palimpsest'].every(id => { const c = T.cards.find(x => x.id === id); return c.thumbKey && c.thumbKey === T.thumbKeyOf(c); })", timeout=30000)
        check(True, 'article and magazine tiles redrawn from their scene')
        check(await pg.evaluate("T.cards.filter(c => c.thumbKey).length") == await pg.evaluate("T.cards.filter(c => T.thumbKeyOf(c)).length"), 'only text and magazine cards get a new tile')

        # 2A + 4A: Vocabulary's page, the History icon, the count right under the title
        await pg.evaluate("T.openDeck(T.studyDeck())"); await pg.wait_for_timeout(500)
        check(await pg.locator(f'{top} [data-p="history"]').count() == 1, 'Vocabulary shows the History icon')
        ok, gap = await lined(f'{top} .pbar + .summary')
        check(ok and 0 <= gap < 14, f'the count sits right under the title, lined up (gap {gap:.0f}px)')
        await ph.shot(f'{out}/02-vocabulary.png')
        await pg.locator(f'{top} .src-open', has_text='Example Show').first.click(); await pg.wait_for_timeout(450)
        check((await lined(f'{top} .pbar + .summary'))[0], 'a deck\'s cards: count lined up with the title')
        await ph.shot(f'{out}/03-deck-cards.png')
        names = await pg.evaluate(f"[...document.querySelectorAll('{top} .gcard .w')].map(e => e.textContent)")
        check('candor' in names and 'be candid about' not in names, 'a tile shows the headword')
        await pg.evaluate("T.back()"); await pg.wait_for_timeout(400)

        # the Study page and New cards: 2A, and holding a card moves nothing
        await tap(f'{top} .sban')
        check((await lined(f'{top} .pbar + .summary'))[0], 'Study: count lined up with the title')
        await ph.shot(f'{out}/04-study.png')
        await tap(f'{top} [data-p="queue"]')
        check((await lined(f'{top} .cline span'))[0], 'New cards: count lined up with the title')
        qnames = await pg.evaluate(f"[...document.querySelectorAll('{top} .qrow .w')].map(e => e.textContent)")
        check('candor' in qnames, 'the queue shows the headword')
        await ph.shot(f'{out}/05-queue.png')
        ys = lambda: pg.evaluate(f"[...document.querySelectorAll('{top} .qrow')].slice(0, 6).map(e => Math.round(e.getBoundingClientRect().top))")
        y0 = await ys()
        await ph.hold(f'{top} .qrow:nth-child(2)')
        y1 = await ys()
        check(await pg.locator(f'{top} .selcount').count() == 1, 'holding a card selects it')
        check(y0 == y1, f'the rows stay where they were ({y0[:3]} → {y1[:3]})')
        await ph.shot(f'{out}/06-queue-selecting.png')
        await tap(f'{top} .qrow:nth-child(4)')
        check(await pg.inner_text(f'{top} .selcount') == '2 selected' and await ys() == y0, 'tapping another adds it, nothing moves')
        await tap(f'{top} [data-p="all"]')
        check(await pg.inner_text(f'{top} .selcount') == '30 selected' and await pg.locator(f'{top} [data-p="all"]').count() == 0, 'Select all')
        await ph.back()
        check(await pg.locator(f'{top} .selcount').count() == 0 and await ys() == y0, 'Back stops selecting, nothing moves')
        # look at three cards from the queue, then study two
        await tap(f'{top} .qrow:nth-child(1)'); await ph.swipe(0, -300); await ph.swipe(0, -300)
        await ph.back(); await ph.back()  # the study view, the queue
        await tap(f'{top} [data-p="start"]')
        await tap('.answer [data-a="continue"]'); await tap('.answer [data-a="continue"]')
        await ph.back()

        # search: the empty page, the placeholder, the name, the stored word
        await ph.back(); await ph.back()  # Study page, Vocabulary page
        await pg.evaluate("T.openSearch()"); await pg.wait_for_timeout(400)
        check(await pg.get_attribute('#q', 'placeholder') == 'Search anything', 'the search box says "Search anything"')
        check((await pg.inner_text('#results')).strip() == '', 'no "words saved" line')
        await ph.shot(f'{out}/07-search.png')
        await pg.fill('#q', 'candid'); await pg.wait_for_timeout(300)
        rw = await pg.evaluate("[...document.querySelectorAll('#results .res .rw')].map(e => e.textContent)")
        check('candor' in rw, f'searching the stored word finds the card, shown by its name ({rw})')
        await pg.fill('#q', 'cand'); await pg.wait_for_timeout(300)
        await ph.shot(f'{out}/08-search-name.png')
        await tap('#results .res[data-card="test-candor"]')
        check(await pg.inner_text('.study .wordbtn') == 'candor', 'the study view title is the headword')
        await ph.shot(f'{out}/09-card-title.png')
        await ph.back(); await ph.back()

        # History
        await pg.evaluate("T.openDeck(T.studyDeck())"); await pg.wait_for_timeout(400)
        await tap(f'{top} [data-p="history"]')
        n, want = await pg.locator(f'{top} .hrow').count(), await pg.evaluate("T.HI.recs.size")
        check(n == want and n >= 4, f'History lists every card opened, once each ({n})')
        first = await pg.inner_text(f'{top} .hrow .w')
        check(first == 'candor', f'newest first ({first})')
        check(await pg.inner_text(f'{top} .hday') == 'Today', 'grouped by day: Today')
        studied = await pg.locator(f'{top} .hrow .d b').all_inner_texts()
        check(studied == ['Studied · New', 'Studied · New'], f'studied cards say so in blue ({studied})')
        check((await lined(f'{top} .cline span'))[0], 'History: count lined up with the title')
        await ph.shot(f'{out}/10-history.png')
        ys = lambda: pg.evaluate(f"[...document.querySelectorAll('{top} .hrow')].map(e => Math.round(e.getBoundingClientRect().top))")
        y0 = await ys()
        await ph.hold(f'{top} .hrow:nth-child(2)')
        check(await ys() == y0, 'holding a card in History moves nothing')
        await tap(f'{top} .hrow:nth-child(3)')
        await ph.shot(f'{out}/11-history-selecting.png')
        await tap(f'{top} [data-p="hremove"]'); await pg.wait_for_timeout(300)
        check(await pg.locator(f'{top} .hrow').count() == n - 2 and await pg.evaluate("T.HI.recs.size") == n - 2, 'Remove takes 2 cards out of History')
        check(await pg.evaluate("T.cards.length") == 30, 'the cards themselves stay')
        await tap(f'{top} [data-p="hmenu"]')
        await ph.shot(f'{out}/12-history-menu.png')
        # an older visit stays when the last hour is cleared
        await pg.evaluate("(() => { const r = [...T.HI.recs.values()].at(-1); r.at = Date.now() - 2 * 864e5; })()")
        await tap('#sheet [data-act="hour"]')
        check(await pg.locator(f'{top} .hrow').count() == 1, 'Clear the last hour keeps the older card')
        check(await pg.locator(f'{top} .hday').first.inner_text() not in ('Today', 'Yesterday'), 'an older day shows its date')
        await ph.shot(f'{out}/13-history-older.png')
        await tap(f'{top} .hrow'); check(await pg.evaluate("!!T.S && !T.S.drill"), 'tapping a card opens it to look at')
        await ph.back()
        check(await pg.inner_text(f'{top} .hday') == 'Today', 'opening it again moves it to Today')
        await tap(f'{top} [data-p="hmenu"]'); await tap('#sheet [data-act="all"]')
        check(await pg.locator(f'{top} .hrow').count() == 0 and 'Nothing yet' in await pg.inner_text(f'{top} .cline'), 'Clear all history empties it')
        check(await pg.evaluate("T.SD.recs.size") == 2, 'Study progress stays')
        await ph.shot(f'{out}/14-history-empty.png')
        await ph.back(); await ph.back()
        check(await pg.locator('.page').count() == 0, 'Back leads out to the home screen')

        # history survives a reload (its own database)
        await pg.evaluate("T.openStudy(T.studyDeck(), 'test-brusque')"); await pg.wait_for_timeout(500); await ph.back()
        await pg.reload(); await pg.wait_for_function("window.T && T.HI && T.HI.loaded")
        check(await pg.evaluate("T.HI.recs.has('test-brusque')"), 'History is kept when the app is reopened')
        check(await pg.evaluate("T.cards.find(c => c.id === 'test-ephemeral').thumbKey") is not None, 'redrawn tiles are kept')

        print('re-import:', t := await ph.imp([nz]))
        check('already up to date' in t, 're-importing: already up to date')
        print('JS errors:', ph.errors or 'none')
        check(not ph.errors, 'no JavaScript errors')
    print('\nALL PASSED' if not fails else f'\n{len(fails)} FAILED')
    return not fails


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('app'); ap.add_argument('--out', default='shots/history')
    a = ap.parse_args()
    sys.exit(0 if asyncio.run(main(a.app, a.out)) else 1)
