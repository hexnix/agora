"""v28 test: the Notes deck.

    python3 tools/app-test/test_notes.py . --out shots/notes/

Imports the test library, then checks the Notes tile on the home screen, writing a note (title, bold, a heading, a checklist
with a ticked line, a numbered list, a quote, a picture), that an empty note is never kept, the list (last edited first, a line
of what follows the title, a small picture), that notes survive a reload, hold to select and delete (and the picture goes too),
Back, the backup (notes and pictures in the zip, a fresh phone gets them back, re-importing changes nothing), that an imported
note can't carry a script, and JavaScript errors. The picture is made up (drawn here); never put real photos in the repo.
"""
import argparse, asyncio, json, os, sys, tempfile, zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import Phone

KIT = os.path.dirname(os.path.abspath(__file__))
LIB_ZIP = os.path.join(KIT, 'fixtures', 'test-library.zip')


def make_photo(path):
    from PIL import Image, ImageDraw
    im = Image.new('RGB', (1200, 800)); d = ImageDraw.Draw(im)
    for y in range(800): d.line([(0, y), (1200, y)], fill=(30 + y // 8, 50 + y // 12, 110 - y // 20))
    d.ellipse([800, 200, 950, 350], fill=(240, 200, 140))
    d.polygon([(0, 600), (300, 450), (600, 580), (900, 420), (1200, 560), (1200, 800), (0, 800)], fill=(20, 28, 36))
    im.save(path, quality=85)


async def main(app, out):
    os.makedirs(out, exist_ok=True)
    fails = []
    def check(ok, what):
        print(('PASS ' if ok else 'FAIL ') + what)
        if not ok: fails.append(what)
    tmp = tempfile.mkdtemp(); photo = os.path.join(tmp, 'photo.jpg'); make_photo(photo)
    top = '.page:last-child'
    async with Phone(app) as ph:
        pg = ph.pg
        print('import:', await ph.imp([LIB_ZIP]))
        meta = await pg.inner_text('[data-notes] .tile-meta')
        check(await pg.locator('[data-notes]').count() == 1 and meta.strip() == '0 notes', f'the Notes tile is on the home screen ({meta.strip()})')
        await ph.shot(f'{out}/1-home.png')
        await pg.click('[data-notes]'); await pg.wait_for_timeout(500)
        check('Tap + to write' in await pg.inner_text(top), 'an empty Notes page says how to start')

        async def fmt(k): await pg.click(f'{top} [data-fmt="{k}"]'); await pg.wait_for_timeout(80)
        # a new note left empty is never kept
        await pg.click('[data-p="nnew"]'); await pg.wait_for_timeout(400)
        await ph.back()
        check(await pg.evaluate("T.NT.notes.size") == 0, 'a note left empty is not kept')

        # write one with every kind of formatting
        await pg.click('[data-p="nnew"]'); await pg.wait_for_timeout(400)
        check(await pg.evaluate("document.activeElement.classList.contains('ntitle')"), 'a new note starts in the title')
        await pg.keyboard.type('Weekend in the hills'); await pg.keyboard.press('Enter')
        await pg.keyboard.type('Leave early. '); await fmt('b'); await pg.keyboard.type('Book the cabin.'); await fmt('b')
        await pg.keyboard.press('Enter'); await fmt('h'); await pg.keyboard.type('Pack'); await pg.keyboard.press('Enter')
        await fmt('check'); await pg.keyboard.type('Rain jacket'); await pg.keyboard.press('Enter'); await pg.keyboard.type('Charger')
        await pg.keyboard.press('Enter'); await pg.keyboard.press('Enter')
        await fmt('ol'); await pg.keyboard.type('First stop'); await pg.keyboard.press('Enter'); await pg.keyboard.type('Second stop')
        await pg.keyboard.press('Enter'); await pg.keyboard.press('Enter')
        await fmt('quote'); await pg.keyboard.type('Go slow.'); await pg.keyboard.press('Enter'); await fmt('quote')
        await pg.set_input_files(f'{top} .npick', photo); await pg.wait_for_timeout(900)
        await fmt('i'); await pg.keyboard.type('The ridge.'); await fmt('i')
        on = await pg.evaluate("[...document.querySelectorAll('.page:last-child [data-fmt].on')].map(b=>b.dataset.fmt)")
        bb = await pg.locator(f'{top} ul.checks > li').first.bounding_box()
        await pg.mouse.click(bb['x'] + 8, bb['y'] + 10); await pg.wait_for_timeout(700)
        html = await pg.evaluate("document.querySelector('.page:last-child .nbody').innerHTML")
        print('note:', html[:400])
        check('<b>Book the cabin.</b>' in html and '<h2>Pack</h2>' in html, 'bold and a heading')
        check('<ul class="checks"><li class="done">Rain jacket</li><li>Charger</li></ul>' in html, 'a checklist with the first line ticked')
        check('<ol><li>First stop</li><li>Second stop</li></ol>' in html and '<blockquote>Go slow.</blockquote>' in html, 'a numbered list and a quote')
        check('<p><ul' not in html and '<p><ol' not in html, 'lists are never inside a paragraph')
        check(await pg.locator(f'{top} .nbody img.in').count() == 1, 'the picture shows in the note')
        await pg.evaluate("document.activeElement.blur()"); await pg.evaluate("document.querySelector('.page:last-child').scrollTop=0"); await pg.wait_for_timeout(200)
        await ph.shot(f'{out}/2-note.png')
        await ph.back()
        n = await pg.evaluate("[...T.NT.notes.values()][0]")
        stored = await pg.evaluate("(async()=>{const n=[...T.NT.notes.values()][0];const r=await T.nstore.get('notes',n.id);return r&&r.html})()")
        check(n['title'] == 'Weekend in the hills' and len(n['imgs']) == 1 and 'src=' not in n['html'] and stored == n['html'], 'the note is saved, with its picture and no picture address in the text')

        # a second note without a title, named by its first line
        await pg.click('[data-p="nnew"]'); await pg.wait_for_timeout(400)
        await pg.keyboard.press('Enter'); await pg.keyboard.type('Ideas'); await pg.keyboard.press('Enter'); await pg.keyboard.type('A notes deck')
        await ph.back()
        rows = await pg.evaluate("[...document.querySelectorAll('.page:last-child .nrow')].map(r=>[r.querySelector('.nt').textContent,(r.querySelector('.np')||{}).textContent||'',!!r.querySelector('img')])")
        print('rows:', rows)
        check(rows[0][:2] == ['Ideas', 'A notes deck'] and rows[1][0] == 'Weekend in the hills' and rows[1][2], 'the list: last edited first, the first line names an untitled note, a small picture')
        check((await pg.inner_text(f'{top} .summary')).strip() == '2 notes · last edited first', 'the count under the title')
        await ph.shot(f'{out}/3-list.png')
        # editing an older note moves it to the top
        await pg.locator(f'{top} .nrow').nth(1).click(); await pg.wait_for_timeout(400)
        await pg.click(f'{top} .nbody i'); await pg.keyboard.press('End'); await pg.keyboard.type(' Done.')
        await ph.back()
        check(await pg.evaluate("document.querySelector('.page:last-child .nrow .nt').textContent") == 'Weekend in the hills', 'an edited note moves to the top')
        await ph.back()
        check((await pg.inner_text('[data-notes] .tile-meta')).strip() == '2 notes', 'the tile counts the notes')

        # notes survive a reload
        await pg.reload(); await pg.wait_for_function("window.T && T.NT && T.NT.loaded"); await pg.wait_for_timeout(500)
        check(await pg.evaluate("T.NT.notes.size") == 2, 'notes are still there after the app reopens')

        # backup
        await pg.click('#appMenu'); await pg.wait_for_timeout(500)
        async with pg.expect_download() as dl:
            await pg.click('#sheet [data-act="export"]')
        d = await dl.value; bpath = os.path.join(tmp, 'backup.zip'); await d.save_as(bpath)
        z = zipfile.ZipFile(bpath); man = json.loads(z.read('manifest.json'))
        items = man.get('notes', {}).get('items', [])
        check(len(items) == 2 and sum(len(x['images']) for x in items) == 1 and all(f in z.namelist() for x in items for f in x['images']), 'the backup carries the notes and the picture')
        await pg.wait_for_timeout(2500)
        t = await ph.imp([bpath]); print('re-import backup:', t)
        check('note' not in t and 'already up to date' in t, 're-importing the backup changes no notes')

        # hold to select, then delete: the picture goes too
        await pg.click('[data-notes]'); await pg.wait_for_timeout(500)
        await ph.hold(f'{top} .nrow >> nth=0'); await pg.wait_for_timeout(200)
        check('1 selected' in await pg.inner_text(f'{top} .pbar'), 'holding a note selects it')
        await ph.shot(f'{out}/4-select.png')
        await pg.locator(f'{top} .nrow').nth(1).click(); await pg.wait_for_timeout(150)
        await pg.click(f'{top} [data-p="ndel"]'); await pg.wait_for_timeout(500)
        await pg.click('#sheet [data-act="yes"]'); await pg.wait_for_timeout(900)
        imgs = await pg.evaluate("T.nstore.all('images').then(a=>a.length)")
        check(await pg.evaluate("T.NT.notes.size") == 0 and imgs == 0, f'deleting notes removes them and their pictures ({imgs} pictures left)')
        await ph.back(); await pg.wait_for_timeout(300)
        check(await pg.evaluate("T.pages.length") == 0, 'Back steps out to the home screen')
        print('JS errors:', ph.errors or 'none')
        check(not ph.errors, 'no JavaScript errors')

    # a fresh phone: the backup brings the notes back; a note can't carry a script
    bad = os.path.join(tmp, 'bad.zip')
    with zipfile.ZipFile(bad, 'w') as zz:
        zz.writestr('manifest.json', json.dumps({'app': 'agora', 'version': 1, 'decks': [], 'notes': {'items': [
            {'id': 'n-evil', 'title': 'Odd', 'html': '<p onclick="x()">Hi <img src=x onerror="window.pwned=1"><script>window.pwned=2</script><a href="javascript:1">link</a></p>', 'createdAt': 1, 'updatedAt': 2}]}}))
    async with Phone(app) as ph:
        pg = ph.pg
        t = await ph.imp([bpath]); print('fresh import:', t)
        check('2 notes' in t, 'a backup brings the notes back on a fresh phone')
        t = await ph.imp([bad]); print('odd import:', t)
        h = await pg.evaluate("T.NT.notes.get('n-evil').html")
        await pg.evaluate("T.openNote('n-evil')"); await pg.wait_for_timeout(600)
        check(h == '<p>Hi link</p>' and not await pg.evaluate("window.pwned"), f'an imported note keeps only plain formatting ({h})')
        await ph.back(); await pg.evaluate("T.openNotes()"); await pg.wait_for_timeout(400)
        await pg.locator('.page:last-child .nrow', has_text='Weekend').click(); await pg.wait_for_timeout(800)
        check(await pg.locator('.page:last-child .nbody img.in').count() == 1, 'the restored note shows its picture')
        print('JS errors:', ph.errors or 'none')
        check(not ph.errors, 'no JavaScript errors on the fresh phone')

    print('\n' + ('ALL PASS' if not fails else f'{len(fails)} FAILED: ' + '; '.join(fails)))
    return 1 if fails else 0


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('app'); ap.add_argument('--out', default='shots/notes')
    a = ap.parse_args(); sys.exit(asyncio.run(main(a.app, a.out)))
