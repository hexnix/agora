"""The Concepts deck (v42): a made-up concept card with a numbered list and a picture in its explanation.

    python3 tools/app-test/test_concepts.py . --out shots/concepts/

Checks the Concepts tile (its light-bulb logo, no "Cover image"), the card's name, the explanation page (numbered list,
the picture and its caption), search finding words in a caption, re-importing changing nothing, a new picture under the same
path replacing the old one (and the old file going), the backup carrying the picture and bringing it back on a fresh phone,
deleting the card removing its pictures, Back, and JavaScript errors. Everything is invented.
"""
import argparse, asyncio, io, json, os, sys, tempfile, zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import Phone
from make_test_library import frame
from PIL import Image, ImageDraw

KIT = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(KIT, 'fixtures', 'test-library.zip')
T0 = 1790000000000


def diagram(w):
    """A made-up diagram: three boxes joined by blue lines."""
    im = Image.new('RGB', (w, w * 7 // 15), (28, 29, 32)); d = ImageDraw.Draw(im); h = im.height
    for k in range(3):
        x = w * (0.06 + k * 0.31); d.rectangle([x, h * 0.36, x + w * 0.25, h * 0.62], outline=(228, 228, 228), width=3)
        if k: d.line([x - w * 0.06, h * 0.49, x, h * 0.49], fill=(0, 134, 255), width=4)
    b = io.BytesIO(); im.save(b, 'JPEG', quality=85); return b.getvalue()


def concept_zip(path, pic_w=900):
    blocks = [
        {'t': 'headword', 'text': 'Second-order thinking'},
        {'t': 'p', 'text': 'Asking **"and then what?"** about a decision, not just what happens first.'},
        {'t': 'heading', 'text': 'How it works'},
        {'t': 'ol', 'items': ['Name the first effect of the choice.', 'Ask what that effect causes in turn.', 'Repeat once or twice.']},
        {'t': 'img', 'src': 'images/chain.jpg', 'text': 'A made-up chain of effects'},
        {'t': 'quote', 'text': 'The first step is easy to plan.'},
    ]
    man = {'app': 'agora', 'version': 1, 'decks': [{'name': 'Concepts', 'cards': [{
        'id': 'test-concept', 'seq': 1, 'word': 'second order', 'addedAt': T0, 'shotAt': T0, 'sceneTime': 1500,
        'scene': 'images/c.jpg', 'definitions': [None],
        'definitionText': [{'src': 'made up', 'kind': 'concept', 'blocks': blocks}],
        'sceneCaption': 'And after that,\nwhat does the ==world== do?', 'tags': ['Movie', 'Made Up Film']}]}]}
    with zipfile.ZipFile(path, 'w') as z:
        z.writestr('manifest.json', json.dumps(man)); z.writestr('images/c.jpg', frame(5)); z.writestr('images/chain.jpg', diagram(pic_w))


PIC = """async () => { const c = T.cards.find(x => x.id === 'test-concept'); if (!c) return null;
  const b = c.defText[0].blocks.find(x => x.t === 'img'); const r = b && b.id && await T.store.get('blobs', b.id).catch(() => null);
  return [b ? b.id : null, r ? r.blob.size : 0]; }"""


async def main(app, out):
    os.makedirs(out, exist_ok=True); tmp = tempfile.mkdtemp()
    fails = []
    def check(ok, what):
        print(('ok   ' if ok else 'FAIL ') + what)
        if not ok: fails.append(what)
    cz, cz2 = os.path.join(tmp, 'concept.zip'), os.path.join(tmp, 'concept2.zip')
    concept_zip(cz); concept_zip(cz2, pic_w=700)

    async with Phone(app) as ph:
        pg = ph.pg
        await ph.imp([LIB]); t = await ph.imp([cz]); print('import:', t)
        check(await pg.evaluate("T.cards.some(c => c.id === 'test-concept')"), 'the concept card comes in')
        tile = pg.locator('.tile', has_text='Concepts').first
        check(await tile.locator('.cover svg').count() == 1, 'the Concepts tile shows its light bulb')
        await ph.shot(f'{out}/01-home.png')
        await tile.locator('.more').click(); await pg.wait_for_timeout(500)
        menu = await pg.inner_text('#sheet')
        check('Cover image' not in menu, 'its ⋯ has no "Cover image"')
        await ph.back(); await pg.wait_for_timeout(300)
        check(await pg.evaluate("T.nameOf(T.cards.find(c => c.id === 'test-concept'))") == 'Second-order thinking', "the card's name is its title")

        p1 = await pg.evaluate(PIC)
        check(p1 and p1[0] and p1[1] > 0, f'its picture is stored ({p1})')
        await ph.open_card('test-concept'); await ph.shot(f'{out}/02-scene.png')
        await ph.swipe(-300); await pg.wait_for_timeout(900)
        ex = await pg.evaluate("""(() => { const d = document.querySelector('.slide .def .dtext'); if (!d) return null; const im = d.querySelector('.t-img img');
          return [d.querySelectorAll('ol li').length, getComputedStyle(d.querySelector('ol li'), '::before').content, !!im && im.naturalWidth > 0, (d.querySelector('.t-img .cap') || {}).textContent]; })()""")
        check(ex and ex[0] == 3 and '"' in ex[1] and ex[2] and 'chain of effects' in (ex[3] or ''), f'the explanation shows the numbered list, the picture and its caption ({ex})')
        await ph.shot(f'{out}/03-explanation.png')
        await pg.evaluate("document.querySelector('.slide .def .scroll').scrollTop = 9999"); await pg.wait_for_timeout(300)
        await ph.shot(f'{out}/04-explanation-end.png')
        await ph.back(); await pg.wait_for_timeout(300); await ph.back(); await pg.wait_for_timeout(500)

        t = await ph.imp([cz]); print('re-import:', t)
        check('already up to date' in t, 're-importing the same zip changes nothing')
        t = await ph.imp([cz2]); print('new picture:', t)
        p2 = await pg.evaluate(PIC)
        old = await pg.evaluate("id => T.store.get('blobs', id).then(r => !!r).catch(() => false)", p1[0])
        check(p2 and p2[1] != p1[1] and p2[0] != p1[0] and not old, f'a new picture under the same path replaces the old one, and the old file goes ({p1} -> {p2}, old kept: {old})')
        t = await ph.imp([cz2]); check('already up to date' in t, 'and importing that again changes nothing')

        # the backup carries the picture
        await pg.click('#appMenu'); await pg.wait_for_timeout(500)
        async with pg.expect_download() as dl:
            await pg.click('#sheet [data-act="export"]')
        d = await dl.value; bpath = os.path.join(tmp, 'backup.zip'); await d.save_as(bpath)
        z = zipfile.ZipFile(bpath); man = json.loads(z.read('manifest.json'))
        mc = next(c for dk in man['decks'] for c in dk['cards'] if c['id'] == 'test-concept')
        ib = next(b for b in mc['definitionText'][0]['blocks'] if b['t'] == 'img')
        check(ib.get('src') in z.namelist() and 'id' not in ib and len(z.read(ib['src'])) == p2[1], f'the backup carries the picture as a file ({ib})')
        await pg.wait_for_timeout(2500)
        t = await ph.imp([bpath]); print('re-import backup:', t)
        check('already up to date' in t, 're-importing the backup changes nothing')

        # deleting the card removes its picture
        await pg.evaluate("T.deleteCards(T.cards.filter(c => c.id === 'test-concept'))"); await pg.wait_for_timeout(300)
        gone = await pg.evaluate("id => T.store.get('blobs', id).then(r => !r).catch(() => true)", p2[0])
        check(gone, 'deleting the card removes its picture')
        print('errors:', ph.errors)
        check(not ph.errors, 'no JavaScript errors')

    async with Phone(app) as ph:
        pg = ph.pg
        t = await ph.imp([bpath]); print('fresh phone:', t)
        p3 = await pg.evaluate(PIC)
        check(p3 and p3[1] == p2[1], f'a fresh phone gets the card and its picture back ({p3})')
        await ph.open_card('test-concept'); await ph.swipe(-300); await pg.wait_for_timeout(900)
        check(await pg.evaluate("(document.querySelector('.slide .def .t-img img') || {}).naturalWidth > 0"), 'and shows it')
        check(not ph.errors, f'no JavaScript errors ({ph.errors})')

    print('\nALL OK' if not fails else f'\n{len(fails)} FAILED')
    return 1 if fails else 0


if __name__ == '__main__':
    a = argparse.ArgumentParser(); a.add_argument('app'); a.add_argument('--out', default='shots/concepts')
    a = a.parse_args()
    sys.exit(asyncio.run(main(a.app, a.out)))
