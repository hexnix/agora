"""Cards on the film's timeline (v43, picks A1, B1, C1): a made-up film in a made-up My Files, in a phone held sideways (915×412).

    python3 tools/app-test/test_timeline.py . --out shots/timeline/

Imports three made-up cards from "Made Up Film" (two with a line from the film's subtitles, one with only its scene time)
and one from another film, then checks that the player finds which film it is by its subtitles and says so once (A1), a blue
dot for each card at its moment and a white one for a line saved for a card (B1), the card notice when the film plays into a
card (C1), Open card showing the card above the film and Back coming back to it, the choice kept when the film opens again,
"Cards from" in ⋯ (another film, None of these), a tap on a dot going to just before it, a card made from the saved line
turning its dot blue, and JavaScript errors. Everything is invented: never put real films, subtitles or cards in the repo.
"""
import argparse, asyncio, base64, json, os, sys, tempfile, zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import Phone
from make_test_library import frame
from test_player import FILL_JS, FILM, SRT

KIT = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(KIT, 'fixtures', 'test-library.zip')
T0 = 1790000000000


def film_zip(path):
    def card(i, id, word, cap, t, show='Made Up Film', **kw):
        c = {'id': id, 'seq': i, 'word': word, 'addedAt': T0 + i, 'shotAt': T0 + i, 'sceneTime': t, 'scene': f'images/{id}.jpg',
             'definitions': [None], 'definitionText': [{'src': 'made up', 'kind': 'dictionary', 'blocks': [
                 {'t': 'headword', 'text': word}, {'t': 'def', 'text': 'A made-up meaning for a test.'}]}],
             'tags': ['Movie', show]}
        if cap: c['sceneCaption'] = cap
        c.update(kw); return c
    cs = [card(1, 'tl-report', 'shorter report', 'Then we write a\n==shorter report==.', 106.0),
          card(2, 'tl-numbers', 'numbers', None, 115.2),
          card(3, 'tl-candor', 'candor', 'Bring the ==candor==,\nleave the timing.', 124.5),
          card(4, 'tl-other', 'elsewhere', 'A line from ==another== film entirely.', 50.0, show='Another Made Up Film')]
    man = {'app': 'agora', 'version': 1, 'decks': [{'name': 'Vocabulary', 'cards': cs}]}
    with zipfile.ZipFile(path, 'w') as z:
        z.writestr('manifest.json', json.dumps(man))
        for i, c in enumerate(cs): z.writestr(c['scene'], frame(i + 2, 960, 540))


async def main(app, out):
    os.makedirs(out, exist_ok=True); tmp = tempfile.mkdtemp()
    fails = []
    def check(ok, what):
        print(('ok   ' if ok else 'FAIL ') + what)
        if not ok: fails.append(what)
    zp = os.path.join(tmp, 'film-cards.zip'); film_zip(zp)

    async with Phone(app, width=915, height=412) as ph:
        pg = ph.pg
        await ph.imp([LIB]); print('import:', await ph.imp([zp]))
        film = base64.b64encode(open(FILM, 'rb').read()).decode()
        await pg.evaluate(FILL_JS, [film, SRT])
        await pg.evaluate("T.connectFiles(true)")
        await pg.wait_for_function("T.FX.scanned && !T.FX.scanning", timeout=20000)

        async def open_film():
            await pg.evaluate("T.openFolder('Films')"); await pg.wait_for_timeout(500)
            await pg.locator('.page:last-child [data-fp="Films/Made Up Film.mkv"]').first.click()
            await pg.wait_for_function("T.PL && T.PL.cues.length >= 5 && T.PL.v.duration > 0", timeout=20000)
        await open_film()
        await pg.evaluate("T.PL.v.pause(); T.PL.v.currentTime = 1"); await pg.wait_for_timeout(2200)

        # A1: found by its subtitles, said once
        m = await pg.evaluate("T.PL.match && [T.PL.match.name, T.PL.match.cards.map(c => c.id), T.PL.rec.match]")
        print('  match:', m)
        check(m and m[0] == 'Made Up Film' and m[1] == ['tl-report', 'tl-numbers', 'tl-candor'] and m[2]['by'] == 'subtitles', 'the film is found by its subtitles, its cards in order')
        line = await pg.evaluate("(document.querySelector('.pl-match') || {}).textContent || ''")
        check('This is Made Up Film' in line and '3 cards' in line and 'Change' in line, f'a line says which film it is, with Change ({line})')
        await ph.shot(f'{out}/01-match-line.png')

        # B1: blue dots where the cards are
        dots = await pg.evaluate("[...document.querySelectorAll('.pl-marks i')].map(i => [i.className, parseFloat(i.style.left)])")
        print('  dots:', dots)
        want = [6 / 40 * 100, 15.2 / 40 * 100, 24 / 40 * 100]
        check([d[0] for d in dots] == ['c', 'c', 'c'] and all(abs(d[1] - w) < 0.5 for d, w in zip(dots, want)),
              'a blue dot for each card: two at their lines, one moved by the same offset')
        col = await pg.evaluate("getComputedStyle(document.querySelector('.pl-marks i.c')).backgroundColor")
        check(col == 'rgb(0, 134, 255)', f'card dots are blue ({col})')

        # a line saved for a card: a white dot
        await pg.evaluate("T.PL.v.currentTime = 33.5"); await pg.wait_for_timeout(500)
        await pg.evaluate("document.querySelector('.player').classList.remove('ui')"); await pg.wait_for_timeout(400)
        await pg.locator('.pl-sub span').click(); await pg.wait_for_timeout(500)
        await pg.locator('.pl-note [data-kind="vocabulary"]').click(); await pg.wait_for_timeout(1200)
        await pg.evaluate("T.PL.v.pause()")
        n = await pg.evaluate("[...document.querySelectorAll('.pl-marks i.n')].map(i => parseFloat(i.style.left))")
        check(len(n) == 1 and abs(n[0] - 33 / 40 * 100) < 2.5, f'a white dot for the saved line ({n})')
        col = await pg.evaluate("getComputedStyle(document.querySelector('.pl-marks i.n')).backgroundColor")
        check(col == 'rgb(255, 255, 255)', f'saved lines are white ({col})')
        await pg.evaluate("document.querySelectorAll('.pl-toast').forEach(t => t.remove()); T.PL.v.currentTime = 20; document.querySelector('.player').classList.add('ui')")
        await pg.wait_for_timeout(500)
        await ph.shot(f'{out}/02-dots.png')

        # a tap on a dot goes to a second before it
        bx = await pg.locator('.pl-track').bounding_box()
        await pg.mouse.click(bx['x'] + bx['width'] * 0.6 + 6, bx['y'] + bx['height'] / 2); await pg.wait_for_timeout(400)
        t = await pg.evaluate("T.PL.v.currentTime")
        check(abs(t - 23) < 0.3, f'a tap near a dot goes to a second before it ({t:.2f})')

        # C1: playing into a card's moment
        await pg.evaluate("T.PL.v.currentTime = 22.8; T.PL.v.play()")
        await pg.wait_for_function("!!document.querySelector('.pl-card')", timeout=5000)
        cn = await pg.evaluate("[document.querySelector('.pl-card').dataset.id, document.querySelector('.pl-card').textContent]")
        check(cn[0] == 'tl-candor' and 'candor' in cn[1] and 'Open card' in cn[1], f'reaching a card shows it at the top right ({cn})')
        await pg.wait_for_timeout(400)
        await ph.shot(f'{out}/03-card-notice.png')
        await pg.locator('.pl-card').click(); await pg.wait_for_timeout(900)
        st = await pg.evaluate("(() => { const s = [...document.querySelectorAll('.study')].pop(); return s && [getComputedStyle(s).zIndex, T.PL.v.paused, s.querySelector('.wordbtn').textContent]; })()")
        check(st and st[0] == '55' and st[1] and 'candor' in st[2], f'Open card pauses the film and shows the card above it ({st})')
        await ph.shot(f'{out}/04-card-open.png')
        await ph.swipe(-300); await pg.wait_for_timeout(700)
        await ph.shot(f'{out}/05-card-meaning.png')
        await ph.back(); await pg.wait_for_timeout(300); await ph.back(); await pg.wait_for_timeout(600)
        back = await pg.evaluate("[document.querySelectorAll('.study').length, !!T.PL, T.PL && Math.round(T.PL.v.currentTime)]")
        check(back[0] == 0 and back[1] and 23 <= back[2] <= 26, f'Back returns to the film at the same moment ({back})')
        await pg.evaluate("T.PL.v.pause()")
        ce = await pg.evaluate("[...document.querySelectorAll('.pl-card')].length")

        # it is remembered: no line the second time
        await ph.back(); await pg.wait_for_timeout(600)
        check(await pg.evaluate("!T.PL"), 'Back leaves the player')
        await open_film(); await pg.evaluate("T.PL.v.pause()"); await pg.wait_for_timeout(2200)
        again = await pg.evaluate("[T.PL.match && T.PL.match.name, !!document.querySelector('.pl-match'), document.querySelectorAll('.pl-marks i.c').length]")
        check(again == ['Made Up Film', False, 3], f'opened again, it remembers the film and says nothing ({again})')

        # ⋯ › Cards from: None of these, then another film, then back
        await pg.click('.player [data-p="more"]'); await pg.wait_for_timeout(500)
        menu = await pg.inner_text('#sheet')
        check('Cards from' in menu and 'Made Up Film' in menu, 'the ⋯ menu says where the cards come from')
        await pg.click('#sheet [data-act="match"]'); await pg.wait_for_timeout(600)
        sh = await pg.inner_text('#sheet'); print('  sheet:', sh.replace('\n', ' | '))
        check('✓ Made Up Film' in sh and 'Another Made Up Film' in sh and 'None of these' in sh, 'the sheet lists the films, this one ticked')
        await ph.shot(f'{out}/06-cards-from.png')
        await pg.click('#sheet [data-act="none"]'); await pg.wait_for_timeout(600)
        no = await pg.evaluate("[T.PL.match, document.querySelectorAll('.pl-marks i.c').length, document.querySelectorAll('.pl-marks i.n').length, T.PL.rec.match]")
        check(no[0] is None and no[1] == 0 and no[2] == 1 and no[3].get('none'), f'None of these takes the card dots away, the saved line stays ({no[:3]})')
        await pg.click('.player [data-p="more"]'); await pg.wait_for_timeout(400)
        await pg.click('#sheet [data-act="match"]'); await pg.wait_for_timeout(500)
        await pg.locator('#sheet .item', has_text='Another Made Up Film').click(); await pg.wait_for_timeout(600)
        ot = await pg.evaluate("[T.PL.match && T.PL.match.name, T.PL.rec.match.by, document.querySelectorAll('.pl-marks i.c').length]")
        check(ot == ['Another Made Up Film', 'you', 1], f'picking another film shows its cards ({ot})')
        await pg.click('.player [data-p="more"]'); await pg.wait_for_timeout(400)
        await pg.click('#sheet [data-act="match"]'); await pg.wait_for_timeout(500)
        await pg.evaluate("[...document.querySelectorAll('#sheet [data-act]')].find(b => b.textContent.trim().startsWith('Made Up Film')).click()"); await pg.wait_for_timeout(600)
        check(await pg.evaluate("T.PL.match && T.PL.match.name") == 'Made Up Film', 'and back to this one')

        # a card made from the saved line: its dot turns blue
        nid = await pg.evaluate("[...T.CN.recs.values()][0].id")
        mz = os.path.join(tmp, 'made.zip')
        with zipfile.ZipFile(zp) as z0, zipfile.ZipFile(mz, 'w') as z:
            man = json.loads(z0.read('manifest.json'))
            c = dict(man['decks'][0]['cards'][2]); c.update(id='tl-last', seq=5, word='last line', sceneTime=133.0, scene='images/tl-last.jpg',
                                                         sceneCaption="That's the ==last line== of the film.", fromNote=nid)
            man['decks'][0]['cards'] = [c]; z.writestr('manifest.json', json.dumps(man)); z.writestr('images/tl-last.jpg', frame(7, 960, 540))
        await ph.back(); await pg.wait_for_timeout(500)
        print('made:', await ph.imp([mz]))
        await open_film(); await pg.evaluate("T.PL.v.pause()"); await pg.wait_for_timeout(2200)
        fin = await pg.evaluate("[document.querySelectorAll('.pl-marks i.c').length, document.querySelectorAll('.pl-marks i.n').length]")
        check(fin == [4, 0], f'a card made from the saved line turns its dot blue ({fin})')
        print('errors:', ph.errors)
        check(not ph.errors, 'no JavaScript errors')

    print('\nALL OK' if not fails else f'\n{len(fails)} FAILED')
    return 1 if fails else 0


if __name__ == '__main__':
    a = argparse.ArgumentParser(); a.add_argument('app'); a.add_argument('--out', default='shots/timeline')
    a = a.parse_args()
    sys.exit(asyncio.run(main(a.app, a.out)))
