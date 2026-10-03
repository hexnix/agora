"""Saving lines for cards (v40): a made-up film in a made-up My Files, in a phone held sideways (915×412), then the
For cards pages upright (412×915).

    python3 tools/app-test/test_cardnotes.py . --out shots/cardnotes/

Checks that tapping a subtitle pauses the film and opens the panel (every line the same size, nothing picked), picking
words by tap and by drag (across two lines), the question, Vocabulary saving the line with its frame and the film playing on,
Undo, Back closing the panel, the For cards icon on Vocabulary's page, the tiles and the list, a line's menu, the zip for the
card chat (notes.json and frames), Send, a backup's lines coming back on a fresh phone, re-imports changing nothing, a card's
fromNote showing "card made", and JavaScript errors. Everything is invented: never put real films or subtitles in the repo.
"""
import argparse, asyncio, base64, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import Phone
from test_player import FILL_JS, FILM, SRT

KIT = os.path.dirname(os.path.abspath(__file__))
ZIP = os.path.join(KIT, 'fixtures', 'test-library.zip')


async def main(app, out):
    os.makedirs(out, exist_ok=True)
    fails = []
    def check(ok, what):
        print(('ok   ' if ok else 'FAIL ') + what)
        if not ok: fails.append(what)

    async with Phone(app, width=915, height=412) as ph:
        pg = ph.pg
        await ph.imp([ZIP])
        await pg.evaluate("T.decks[0].name = 'Vocabulary'")
        film = base64.b64encode(open(FILM, 'rb').read()).decode()
        await pg.evaluate(FILL_JS, [film, SRT])
        await pg.evaluate("T.connectFiles(true)")
        await pg.wait_for_function("T.FX.scanned && !T.FX.scanning", timeout=20000)
        await pg.evaluate("T.openFolder('Films')"); await pg.wait_for_timeout(500)
        await pg.locator('[data-fp="Films/Made Up Film.mkv"]').first.click()
        await pg.wait_for_function("T.PL && T.PL.cues.length >= 5", timeout=20000)
        await pg.evaluate("T.PL.v.currentTime = 6.5"); await pg.wait_for_timeout(500)
        await pg.evaluate("document.querySelector('.player').classList.remove('ui')"); await pg.wait_for_timeout(400)

        # a tap on the subtitle: the film pauses and the panel opens
        await pg.locator('.pl-sub span').click(); await pg.wait_for_timeout(500)
        st = await pg.evaluate("[T.PL.noting, T.PL.v.paused, document.querySelectorAll('.pl-note .nl').length, document.querySelectorAll('.pl-note .nl.now').length, document.querySelectorAll('.pl-note .nw.on').length]")
        check(st[0] and st[1], f'tapping a subtitle pauses the film and opens the panel ({st[:2]})')
        check(st[2] == 4 and st[3] == 1 and st[4] == 0, f'it shows the lines around it, the tapped one marked, nothing picked ({st[2:]})')
        fs = await pg.evaluate("[...new Set([...document.querySelectorAll('.pl-note .nl')].map(x => getComputedStyle(x).fontSize))]")
        check(len(fs) == 1, f'every line is the same size ({fs})')
        await ph.shot(f'{out}/01-panel.png')

        # pick a word by tapping, then more by dragging across two lines
        cur = pg.locator('.pl-note .nl.now .nw')
        n = await cur.count()
        await cur.nth(n - 1).click(); await pg.wait_for_timeout(200)
        one = await pg.evaluate("[T.PL.note.sel, document.querySelector('.pl-note .nhint').textContent]")
        check(one[0] and one[0][0] == one[0][1] and '1 word picked' in one[1], f'a tap picks one word ({one})')
        await cur.nth(n - 1).click(); await pg.wait_for_timeout(200)
        check(await pg.evaluate("T.PL.note.sel === null"), 'tapping it again drops it')
        a = await cur.nth(n - 2).bounding_box(); b = await pg.locator('.pl-note .nl').nth(2).locator('.nw').nth(1).bounding_box()
        await pg.mouse.move(a['x'] + 4, a['y'] + a['height'] / 2); await pg.mouse.down()
        await pg.mouse.move(b['x'] + 4, b['y'] + b['height'] / 2, steps=6); await pg.mouse.up(); await pg.wait_for_timeout(200)
        sel = await pg.evaluate("[T.PL.note.sel, document.querySelectorAll('.pl-note .nw.on').length]")
        check(sel[0] and sel[1] >= 4, f'dragging picks words across two lines ({sel})')
        await pg.locator('.pl-note .nq').fill('Is this a made-up question?')
        await ph.shot(f'{out}/02-picked.png')
        await pg.locator('.pl-note [data-kind="vocabulary"]').click(); await pg.wait_for_timeout(1200)
        rec = await pg.evaluate("(() => { const n = [...T.CN.recs.values()][0]; return n && [n.kind, n.text, n.question, n.time, n.src.name, !T.PL.noting, !T.PL.v.paused]; })()")
        print('  saved:', rec)
        check(rec and rec[0] == 'vocabulary' and rec[2] == 'Is this a made-up question?' and rec[4] == 'Made Up Film.mkv', 'Vocabulary saves the picked words, the question and the film')
        check(rec and rec[5] and rec[6], 'the panel closes and the film plays on')
        fr = await pg.evaluate("(async () => { const n = [...T.CN.recs.values()][0]; const f = await T.cstore.get('frames', n.id); const t = await T.cstore.get('frames', n.id + '-t'); return [!!f && f.blob.size, !!t]; })()")
        check(fr[0] and fr[1], f'the frame is kept, with a small copy for the list ({fr})')
        check(await pg.evaluate("!!document.querySelector('.pl-toast')"), 'a note says it was saved, with Undo')
        await ph.shot(f'{out}/03-saved.png')

        # a Concept with nothing picked keeps the whole line; Undo takes it away
        await pg.evaluate("T.PL.v.currentTime = 15.5"); await pg.wait_for_timeout(500)
        await pg.evaluate("document.querySelector('.player').classList.remove('ui')"); await pg.wait_for_timeout(400)
        await pg.locator('.pl-sub span').click(); await pg.wait_for_timeout(500)
        line = await pg.evaluate("T.PL.note.lines[T.PL.note.cur].x.replace(/\\n/g, ' ')")
        await pg.locator('.pl-note [data-kind="concept"]').click(); await pg.wait_for_timeout(1200)
        c2 = await pg.evaluate("[...T.CN.recs.values()].find(n => n.kind === 'concept')")
        check(c2 and c2['text'] == line and c2['sel'] is None, f'with nothing picked the whole line is saved ({c2 and c2["text"]})')
        await pg.locator('.pl-toast button').click(); await pg.wait_for_timeout(500)
        check(await pg.evaluate("T.CN.recs.size === 1 && T.CN.gone.size === 1"), 'Undo takes it away again')

        # Back closes the panel without saving, then the player
        await pg.evaluate("document.querySelector('.player').classList.remove('ui')"); await pg.wait_for_timeout(400)
        await pg.evaluate("T.PL.v.currentTime = 24.5"); await pg.wait_for_timeout(500)
        await pg.locator('.pl-sub span').click(); await pg.wait_for_timeout(400)
        await ph.back()
        check(await pg.evaluate("T.PL && !T.PL.noting && T.CN.recs.size === 1"), 'Back closes the panel without saving')
        await ph.back(); await pg.wait_for_timeout(400)
        check(await pg.evaluate("!T.PL"), 'and then the player')

        # the For cards pages, upright
        await pg.set_viewport_size({'width': 412, 'height': 915})
        await pg.evaluate("T.back()"); await pg.wait_for_timeout(400)  # out of the folder
        await pg.evaluate("T.openDeck(T.studyDeck())"); await pg.wait_for_timeout(800)
        check(await pg.locator('[data-p="cnotes"]').count() == 1, 'Vocabulary\'s page has the For cards icon')
        await pg.locator('[data-p="cnotes"]').click(); await pg.wait_for_timeout(700)
        top = await pg.evaluate("[document.querySelectorAll('[data-cng]').length, document.querySelector('.deckpage:last-of-type .summary').textContent]")
        check(top[0] == 1 and '1 line' in top[1], f'For cards shows a tile for the film ({top})')
        await ph.shot(f'{out}/04-for-cards.png')
        await pg.locator('[data-cng]').first.click(); await pg.wait_for_timeout(700)
        row = await pg.evaluate("[document.querySelectorAll('.cnrow').length, document.querySelector('.cnrow .ln b') && document.querySelector('.cnrow .ln b').textContent, document.querySelector('.cnrow .qq').textContent]")
        check(row[0] == 1 and row[1] and 'made-up question' in row[2], f'its lines show the picked words and the question ({row})')
        await ph.shot(f'{out}/05-list.png')
        await pg.locator('.cnrow').first.click(); await pg.wait_for_timeout(500)
        await pg.locator('#sheet [data-act="kind"]').click(); await pg.wait_for_timeout(500)
        check(await pg.evaluate("[...T.CN.recs.values()][0].kind === 'concept'"), 'a line\'s menu changes it to a Concept')

        # the zip for the card chat
        z = await pg.evaluate("""(async () => { await T.loadZip(); const b = await T.cnZip([...T.CN.recs.values()]); const zip = await JSZip.loadAsync(b);
          const j = JSON.parse(await zip.file('notes.json').async('string')); return [j, Object.keys(zip.files)]; })()""")
        j, names = z
        n0 = j['notes'][0]
        print('  notes.json:', json.dumps(n0)[:400])
        check(j['kind'] == 'card-notes' and j['version'] == 1 and n0['question'] and n0['video']['cue']['text'] and '==' in n0['selection']['marked'], 'notes.json carries the line, the words marked, the question')
        check(n0['video']['frame'] in names and n0['video']['before'] is not None and n0['video']['after'], 'and the frame and the lines around it')
        await pg.evaluate("window.__shared = null; navigator.canShare = () => true; navigator.share = async d => { window.__shared = d.files[0].name; }; 1")
        await pg.locator('[data-p="cnsend"]').last.click(); await pg.wait_for_timeout(1500)
        sh = await pg.evaluate("[window.__shared, [...T.CN.recs.values()][0].sentAt > 0, document.querySelector('.cnrow .mt').textContent]")
        check(sh[0] and sh[0].endswith('.zip') and sh[1] and 'sent' in sh[2], f'Send shares the zip and marks the lines sent ({sh})')

        # a card made from the line shows it
        await pg.evaluate("T.cards[0].fromNote = [...T.CN.recs.values()][0].id; T.back()"); await pg.wait_for_timeout(300)
        await pg.locator('[data-cng]').first.click(); await pg.wait_for_timeout(500)
        check('card made' in await pg.inner_text('.cnrow .mt'), 'a card made from it (fromNote) shows "card made"')

        # backups: the lines and frames come back on a fresh phone, and a re-import changes nothing
        bk = await pg.evaluate("""(async () => { await T.loadZip(); const zip = new JSZip(); const m = await T.exportCardNotes(zip);
          const id = m.notes.find(n => !n.gone).id, f = await zip.file(m.notes.find(n => !n.gone).frame).async('arraybuffer');
          const again = await T.importCardNotes(m.notes, async x => null);
          [...T.CN.recs.keys()].forEach(k => T.CN.recs.delete(k)); T.CN.gone.clear(); await T.cstore.del('frames', [id, id + '-t']);
          const back = await T.importCardNotes(m.notes, async x => x.frame ? zip.file(x.frame).async('arraybuffer') : null);
          const fr = await T.cstore.get('frames', id);
          return [again, back, !!fr, T.CN.recs.size, T.CN.gone.size, f.byteLength]; })()""")
        check(bk[0] == 0, f're-importing the same lines changes nothing ({bk[0]})')
        check(bk[1] == 1 and bk[2] and bk[3] == 1 and bk[4] == 1, f'a fresh phone gets the lines, their frames and the deleted one ({bk})')

        print('errors:', ph.errors)
        check(not [e for e in ph.errors if 'play()' not in e], 'no JavaScript errors')

    print('\nALL OK' if not fails else f'\n{len(fails)} FAILED')
    return 1 if fails else 0


if __name__ == '__main__':
    a = argparse.ArgumentParser(); a.add_argument('app'); a.add_argument('--out', default='shots/cardnotes')
    a = a.parse_args()
    sys.exit(asyncio.run(main(a.app, a.out)))
