"""v30 test: Bookmarks, links shared into Agora.

    python3 tools/app-test/test_bookmarks.py . --out shots/bookmarks/

Uses made-up bookmarks only. Checks the home tile, the Bookmarks page (list and grid, search inside it), sharing a link
(Android opens Agora at ./?title=…&text=… : the save sheet, suggested tags already added, one tap Save), sharing the same
link again (edits it, no copy), Add a link by hand, hold to select (Edit, Add tags, Delete), the main search finding
bookmarks, Back, the backup carrying bookmarks, re-imports reporting "already up to date", and JavaScript errors.
"""
import argparse, asyncio, json, os, sys, tempfile, time, zipfile
from urllib.parse import urlencode

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import Phone

KIT = os.path.dirname(os.path.abspath(__file__))
LIB_ZIP = os.path.join(KIT, 'fixtures', 'test-library.zip')
fails = []


def check(ok, what):
    print(('ok   ' if ok else 'FAIL ') + what)
    if not ok: fails.append(what)


def marks_zip(path):
    now = int(time.time() * 1000); day = 86400000
    rows = [('https://www.youtube.com/watch?v=aaaaaaaaaa1', 'How to make perfect espresso at home', ['YouTube', 'Cooking'], 0.1),
            ('https://www.example.com/wellness/the-quiet-science-of-better-sleep', 'The quiet science of better sleep', ['Article', 'Health'], 1),
            ('https://medium.com/@writer/notes-on-minimal-note-apps', 'Notes on minimal note apps', [], 2),
            ('https://en.wikipedia.org/wiki/Palimpsest', 'Palimpsest', ['Wikipedia', 'Words'], 3)]
    man = {'app': 'agora', 'version': 1, 'decks': [], 'bookmarks': [
        {'id': f'bm-test{i}', 'url': u, 'title': t, 'tags': tg, 'addedAt': int(now - d * day), 'at': int(now - d * day)} for i, (u, t, tg, d) in enumerate(rows)]}
    with zipfile.ZipFile(path, 'w') as z: z.writestr('manifest.json', json.dumps(man))


async def main(app, out):
    tmp = tempfile.mkdtemp(); mz = os.path.join(tmp, 'marks.zip'); marks_zip(mz)
    async with Phone(app) as ph:
        pg = ph.pg
        await pg.route('**/www.youtube.com/oembed**', lambda r: r.abort())
        t = await ph.imp([LIB_ZIP, mz]); print('import:', t)
        check('4 bookmarks' in t, 'importing a zip with bookmarks adds them')
        tile = pg.locator('[data-marks]')
        check(await tile.count() == 1 and '4 bookmarks' in await tile.inner_text(), 'home tile "Bookmarks · 4 bookmarks"')
        await ph.shot(f'{out}/1-home.png')

        await tile.click(); await pg.wait_for_timeout(500)
        check(await pg.locator('.bmrow').count() == 4, 'the page lists 4 bookmarks, newest first')
        check((await pg.inner_text('.page .summary')).startswith('4 bookmarks'), 'count line under the title')
        await ph.shot(f'{out}/2-list.png')
        await pg.click('[data-p="view"]'); await pg.wait_for_timeout(300)
        check(await pg.locator('.bmcard').count() == 4, 'grid view')
        await ph.shot(f'{out}/3-grid.png')
        await pg.click('[data-p="view"]'); await pg.wait_for_timeout(300)

        # search inside Bookmarks
        await pg.click('[data-p="bsearch"]'); await pg.wait_for_timeout(300)
        await pg.fill('#bq', 'sleep'); await pg.wait_for_timeout(200)
        check(await pg.locator('.bmrow').count() == 1, 'search inside Bookmarks finds by title')
        await pg.fill('#bq', 'words'); await pg.wait_for_timeout(200)
        check(await pg.locator('.bmrow').count() == 1, 'and by tag')
        await ph.shot(f'{out}/4-search.png')
        await ph.back()
        check(await pg.locator('#bq').count() == 0 and await pg.locator('.bmrow').count() == 4, 'Back closes the search, the list is whole again')

        # tapping opens the link
        await pg.evaluate("() => { window.__opened = []; window.open = u => { window.__opened.push(u); }; }")
        await pg.locator('.bmrow').nth(1).click(); await pg.wait_for_timeout(200)
        check(await pg.evaluate("window.__opened[0]") == 'https://www.example.com/wellness/the-quiet-science-of-better-sleep', 'tapping a bookmark opens its link')

        # hold to select, Edit
        await ph.hold('.bmrow >> nth=2')
        check(await pg.locator('.page .selcount').count() == 1, 'holding a bookmark selects it')
        await pg.click('.page [data-p="all"]'); await pg.wait_for_timeout(200)
        check(await pg.locator('.bmrow.on').count() == 4, 'the select-all icon selects every bookmark')
        await pg.click('.page [data-p="all"]'); await pg.wait_for_timeout(200)
        check(await pg.locator('.bmrow.on').count() == 0, 'and a second tap clears the selection')
        await pg.locator('.bmrow').nth(2).click(); await pg.wait_for_timeout(200)
        await pg.click('[data-p="selmenu"]'); await pg.wait_for_timeout(400)
        await pg.click('#sheet [data-act="edit"]'); await pg.wait_for_timeout(600)
        check(await pg.locator('#bmUrl').count() == 1 and 'Edit bookmark' in await pg.inner_text('#sheet h2'), 'Edit opens the sheet with link and title')
        await pg.fill('#bmTag', 'Reading list'); await pg.press('#bmTag', 'Enter'); await pg.wait_for_timeout(200)
        check('Reading list' in await pg.locator('#sheet .bon .chip').all_inner_texts(), 'Enter in the tag field adds the tag')
        await ph.shot(f'{out}/5-edit.png')
        await pg.click('#sheet [data-act="save"]'); await pg.wait_for_timeout(600)
        tags = await pg.evaluate("T.BM.recs.get('bm-test2').tags")
        check(tags == ['Reading list'], f'a tag added later is saved ({tags})')
        check(await pg.locator('.page .selcount').count() == 0 and not await pg.evaluate("document.querySelector('#sheet').classList.contains('open')"), 'after Save the selection has ended')

        # Add tags to several, then Delete one
        await ph.hold('.bmrow >> nth=0'); await pg.locator('.bmrow').nth(1).click(); await pg.wait_for_timeout(200)
        await pg.click('[data-p="selmenu"]'); await pg.wait_for_timeout(400)
        await pg.click('#sheet [data-act="tag"]'); await pg.wait_for_timeout(400)
        await pg.fill('#bmTag', 'Later'); await pg.press('#bmTag', 'Enter'); await pg.wait_for_timeout(300)
        n = await pg.evaluate("[...T.BM.recs.values()].filter(r=>r.tags.includes('Later')).length")
        check(n == 2, 'Add tags tags both selected bookmarks')
        await ph.back(); await ph.back()
        await ph.hold('.bmrow >> nth=3')
        await pg.click('[data-p="selmenu"]'); await pg.wait_for_timeout(400)
        await pg.click('#sheet [data-act="del"]'); await pg.wait_for_timeout(400)
        await pg.click('#sheet [data-act="yes"]'); await pg.wait_for_timeout(800)
        check(await pg.evaluate("T.BM.recs.size") == 3 and await pg.locator('.bmrow').count() == 3, 'Delete removes the bookmark')
        await ph.back()
        check(await pg.locator('.page').count() == 0, 'Back steps out to the home screen')

        # sharing a link into Agora (what Android's share menu does)
        q = urlencode({'title': 'Example Show season 2 review', 'text': 'Worth a read https://www.example.com/tv/example-show-season-2-review'})
        await pg.goto(ph.base + '?' + q); await pg.wait_for_timeout(1500)
        check(await pg.evaluate("location.search") == '', 'the shared link is taken out of the address (a reload won\'t share it again)')
        check('Save bookmark' in await pg.inner_text('#sheet h2'), 'sharing opens the Save sheet over Bookmarks')
        check(await pg.input_value('#bmTitle') == 'Example Show season 2 review', 'the title is filled in')
        on = await pg.locator('#sheet .bon .chip').all_inner_texts()
        check('Example Show' in on and 'Article' in on, f'suggested tags already added: {on}')
        await ph.shot(f'{out}/6-share.png')
        await pg.click('#sheet [data-act="save"]'); await pg.wait_for_timeout(600)
        check(await pg.evaluate("T.BM.recs.size") == 4, 'one tap saves it')
        await ph.shot(f'{out}/7-saved.png')
        # the same link again: edits, never a copy
        await pg.goto(ph.base + '?' + urlencode({'url': 'https://www.example.com/tv/example-show-season-2-review'})); await pg.wait_for_timeout(1500)
        check('Edit bookmark' in await pg.inner_text('#sheet h2') and 'saved on' in await pg.inner_text('#sheet .sub'), 'sharing a saved link again says when it was saved')
        await pg.click('#sheet [data-act="save"]'); await pg.wait_for_timeout(500)
        check(await pg.evaluate("T.BM.recs.size") == 4, 'and saves no copy')
        await ph.back()

        # Add a link by hand from the tile's ⋯
        await pg.click('[data-mmenu]'); await pg.wait_for_timeout(400)
        await pg.click('#sheet [data-act="add"]'); await pg.wait_for_timeout(600)
        await pg.fill('#bmUrl', 'youtu.be/aaaaaaaaaa9'); await pg.fill('#bmTitle', 'A video'); await pg.wait_for_timeout(100)
        await pg.dispatch_event('#bmUrl', 'change'); await pg.wait_for_timeout(200)
        await pg.click('#sheet [data-act="save"]'); await pg.wait_for_timeout(500)
        r = await pg.evaluate("[...T.BM.recs.values()].find(r=>r.title==='A video')")
        check(r and r['url'] == 'https://youtu.be/aaaaaaaaaa9' and r['site'] == 'youtu.be', 'Add a link: a link without https:// is completed')
        check(r and 'YouTube' in r['tags'], f'a YouTube link gets the YouTube tag ({r and r["tags"]})')

        # the main search finds bookmarks under the cards
        await pg.evaluate("T.openSearch()"); await pg.wait_for_timeout(300)
        await pg.fill('#q', 'espresso'); await pg.wait_for_timeout(300)
        check(await pg.locator('#results [data-bm]').count() == 1, 'the main search finds a bookmark by its title')
        await ph.shot(f'{out}/8-search.png')
        await ph.back()
        await pg.evaluate("T.openSearch(['Cooking'])"); await pg.wait_for_timeout(300)
        check(await pg.locator('#results [data-bm]').count() == 1, 'a pinned tag shows the bookmarks with it')
        await ph.back()

        # backup carries the bookmarks; re-importing it changes nothing
        await pg.click('#appMenu'); await pg.wait_for_timeout(500)
        async with pg.expect_download() as dl:
            await pg.click('#sheet [data-act="export"]')
        d = await dl.value; bpath = os.path.join(tmp, 'backup.zip'); await d.save_as(bpath)
        man = json.loads(zipfile.ZipFile(bpath).read('manifest.json'))
        check(len(man.get('bookmarks', [])) == 5, f'the backup carries {len(man.get("bookmarks", []))} bookmarks')
        await pg.wait_for_timeout(2500)
        t = await ph.imp([bpath]); print('re-import backup:', t)
        check('bookmark' not in t, 're-importing the backup adds no bookmarks')
        t = await ph.imp([mz]); print('re-import marks zip:', t)
        check(t == 'Nothing to import', 're-importing the older bookmarks zip changes nothing (edits stay, a deleted bookmark stays deleted)')
        print('JS errors:', ph.errors or 'none')
        check(not ph.errors, 'no JavaScript errors')

    async with Phone(app) as ph:
        t = await ph.imp([bpath]); print('fresh import:', t)
        check('5 bookmarks' in t, 'a backup restores the bookmarks on a fresh phone')
    print('\n' + ('ALL PASSED' if not fails else f'{len(fails)} FAILED: ' + '; '.join(fails)))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    a = argparse.ArgumentParser(); a.add_argument('app'); a.add_argument('--out', default='shots/bookmarks')
    o = a.parse_args(); asyncio.run(main(o.app, o.out))
