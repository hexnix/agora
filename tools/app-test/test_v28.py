"""v28 test: the home title spaced like every page title, Select all as an icon in every selection bar, search inside a deck,
and (v31) the same search inside My Files and Notes.

    python3 tools/app-test/test_v28.py . --out shots/v28/
"""
import argparse, asyncio, os, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import Phone
from test_study import vocab_zip
from test_files import FILL_JS, tree_for_js


async def main(app, out):
    os.makedirs(out, exist_ok=True)
    fails = []
    def check(ok, what):
        print(('PASS ' if ok else 'FAIL ') + what)
        if not ok: fails.append(what)
    vz = os.path.join(tempfile.mkdtemp(), 'vocab.zip'); vocab_zip(vz)
    async with Phone(app) as ph:
        pg = ph.pg; top = '.page:last-child'
        async def tap(sel): await pg.locator(sel).first.click(); await pg.wait_for_timeout(400)
        rect = lambda sel: pg.evaluate("s => { const b = document.querySelector(s).getBoundingClientRect(); return {y: b.y, h: b.height}; }", sel)
        print('import:', await ph.imp([vz]))
        await pg.wait_for_function("T.SD.loaded")

        # the home title sits where a page title does, its count right under it
        h, s = await rect('#home .bar h1'), await rect('#home .summary')
        await pg.evaluate("T.openDeck(T.studyDeck())"); await pg.wait_for_timeout(500)
        ph1, ps = await rect(f'{top} .pbar .pt'), await rect(f'{top} .pbar + .summary')
        gh, gp = s['y'] - (h['y'] + h['h']), ps['y'] - (ph1['y'] + ph1['h'])
        check(abs(gh - gp) < 3, f'home count gap matches the page gap ({gh:.1f} vs {gp:.1f})')
        check(abs((h['y'] + h['h'] / 2) - (ph1['y'] + ph1['h'] / 2)) < 3, 'home title sits at the page title height')

        # search inside the deck
        await tap(f'{top} [data-p="dsearch"]')
        check(await pg.get_attribute('#q', 'placeholder') == 'Search Vocabulary', 'deck search says "Search Vocabulary"')
        await pg.keyboard.type('candor'); await pg.wait_for_timeout(400)
        ids = await pg.evaluate("[...document.querySelectorAll('#results .res')].map(b => b.dataset.card)")
        mine = await pg.evaluate("T.cards.filter(c => c.deckId === T.studyDeck().id).map(c => c.id)")
        check(ids and all(i in mine for i in ids), f'deck search finds only that deck\'s cards ({len(ids)})')
        check('in Vocabulary' in await pg.inner_text('#results .rhead'), 'the count says which deck')
        await ph.shot(f'{out}/01-deck-search.png')
        await ph.back()
        check(await pg.locator('.page.search').count() == 0 and await pg.evaluate("T.pages.length") == 1, 'Back closes the search, the deck page stays')

        # Select all as an icon on a deck's cards
        await pg.locator(f'{top} .src-open', has_text='Example Show').first.click(); await pg.wait_for_timeout(450)
        check(await pg.locator(f'{top} .pbar [data-p="dsearch"]').count() == 0, 'no search icon on a deck\'s second page')
        await ph.hold(f'{top} .gcard')
        check(await pg.locator(f'{top} .pbar [data-p="all"]').count() == 1, 'the select-all icon is in the bar')
        await tap(f'{top} .pbar [data-p="all"]')
        n = await pg.locator(f'{top} .gcard').count()
        check(await pg.inner_text(f'{top} .selcount') == f'{n} selected', 'the icon selects every card')
        await ph.shot(f'{out}/02-all-selected.png')
        await tap(f'{top} .pbar [data-p="all"]')
        check(await pg.inner_text(f'{top} .selcount') == '0 selected', 'tapping it again clears the selection')
        await tap(f'{top} .pbar [data-p="all"]'); await tap(f'{top} [data-p="selmenu"]')
        check(await pg.locator('#sheet [data-act="all"]').count() == 0, 'Select all is gone from the ⋯ menu')
        await ph.back(); await ph.back(); await ph.back(); await ph.back()
        check(await pg.evaluate("T.pages.length") == 0, 'Back steps out one step at a time')

        # a deck of one source opens on its cards, with the search icon there
        check(not ph.errors, 'no JavaScript errors')
    # a deck of one source opens straight on its cards, so the search icon is there
    async with Phone(app) as ph:
        pg = ph.pg
        await ph.imp([os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures', 'test-library.zip')])
        await pg.evaluate("T.openDeck(T.decks.find(d => d.name === 'Example Show'))"); await pg.wait_for_timeout(500)
        kind = await pg.evaluate("T.pages.map(p => p.kind).join()")
        has = await pg.locator('.page:last-child .pbar [data-p="dsearch"]').count()
        check(kind != 'cards' or has == 1, f'the first page a deck opens on has the search icon ({kind})')
        check(not ph.errors, 'no JavaScript errors')
    # v31: search inside My Files and inside Notes
    async with Phone(app) as ph:
        pg = ph.pg; top = '.page:last-child'
        async def tap(sel): await pg.locator(sel).first.click(); await pg.wait_for_timeout(450)
        await pg.evaluate(FILL_JS, tree_for_js()); await pg.evaluate("T.connectFiles(true)")
        await pg.wait_for_function("T.FX.scanned && !T.FX.scanning", timeout=30000)
        await pg.evaluate("T.openFolder('')"); await pg.wait_for_timeout(500)
        check(await pg.locator(f'{top} .pbar [data-p="fsearch"]').count() == 1, 'My Files has the search icon')
        await ph.shot(f'{out}/03-files-bar.png')
        await tap(f'{top} [data-p="fsearch"]')
        check(await pg.get_attribute('#q', 'placeholder') == 'Search My Files', 'it says "Search My Files"')
        await pg.keyboard.type('resume'); await pg.wait_for_timeout(400)
        check(await pg.locator('#results [data-fopen="resume-2026.pdf"]').count() == 1 and await pg.locator('#results [data-card], #results [data-bm]').count() == 0,
              'it finds the file and nothing but files')
        await ph.shot(f'{out}/04-files-search.png')
        await ph.back()
        check(await pg.locator('.page.search').count() == 0, 'Back closes it')
        await ph.back()
        await pg.wait_for_function("T.NT.loaded")
        await pg.evaluate("""async () => { const now = Date.now();
          for (const [i, [t, h]] of [['Groceries', '<p>Milk, eggs</p><p>Olive oil</p>'], ['', '<p>Call the plumber</p><p>about the kitchen tap</p>'], ['Trip', '<p>Book the cabin</p>']].entries()) {
            const n = { id: 'n-test' + i, title: t, html: h, imgs: [], createdAt: now - i * 1000, updatedAt: now - i * 1000 };
            T.NT.notes.set(n.id, n); await T.nstore.put('notes', [n]); } }""")
        await pg.evaluate("T.openNotes()"); await pg.wait_for_timeout(500)
        check(await pg.locator(f'{top} .pbar [data-p="nsearch"]').count() == 1, 'Notes has the search icon')
        await tap(f'{top} [data-p="nsearch"]')
        check(await pg.get_attribute('#q', 'placeholder') == 'Search Notes', 'it says "Search Notes"')
        await pg.keyboard.type('tap'); await pg.wait_for_timeout(400)
        ids = await pg.evaluate("[...document.querySelectorAll('#results [data-note]')].map(b => b.dataset.note)")
        check(ids == ['n-test1'], f'it finds the note by a line inside it ({ids})')
        await ph.shot(f'{out}/05-notes-search.png')
        await tap('#results [data-note]')
        check(await pg.locator(f'{top} .nbody').count() == 1, 'tapping it opens the note')
        await ph.back(); await ph.back()
        check(await pg.locator('.page.search').count() == 0 and await pg.evaluate("T.pages.length") == 1, 'Back steps out: note, search, then the Notes page')
        check(not ph.errors, f'no JavaScript errors {ph.errors}')
    print('\nALL PASSED' if not fails else f'\n{len(fails)} FAILED')
    return not fails


if __name__ == '__main__':
    a = argparse.ArgumentParser(); a.add_argument('app'); a.add_argument('--out', default='shots/v28')
    x = a.parse_args(); sys.exit(0 if asyncio.run(main(x.app, x.out)) else 1)
