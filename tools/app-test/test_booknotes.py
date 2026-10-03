"""Notes and highlights in books (v45): the made-up book in a made-up My Files, on a phone held upright (412×915).

    python3 tools/app-test/test_booknotes.py . --out shots/booknotes/

Checks picking words (the phone's own selection) showing the bar under them (A1), Vocabulary saving them with where they sit,
Undo, + Question then Concept, a pick across two paragraphs, a picked word never turning the chapter, the white underline (B1), a
tap on it showing the strip with Remove, a card made from the words (fromNote) turning them blue, a card of this book found on its
page by its scene's paragraph, a tap showing its card (C1), Open card above the book and Back to it, the For cards tile and rows
for the book, Read from here, the zip for the card chat, the backup on a fresh phone, re-imports, and JavaScript errors.
Everything is invented: never put real books or cards in the repo.
"""
import argparse, asyncio, base64, io, json, os, sys, tempfile, zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import Phone
from test_books import FILL_JS, BOOK, SWIPE, locked_copy
from PIL import Image

# pick characters a to b of the chapter's paragraph p, the way a finger does (a selection over its text)
PICK = """([p, a, b, p2]) => { const pg = T.BK.page, bs = pg.blocks, at = (blk, o) => { const tw = document.createTreeWalker(blk, NodeFilter.SHOW_TEXT); let n, s = 0;
    while ((n = tw.nextNode())) { if (s + n.nodeValue.length >= o) return [n, o - s]; s += n.nodeValue.length; } return [n, 0]; };
  const x = at(bs[p], a), y = at(bs[p2 == null ? p : p2], b); getSelection().setBaseAndExtent(x[0], x[1], y[0], y[1]); return getSelection().toString(); }"""
TAP = """(sel) => { const m = document.querySelector(sel); m.scrollIntoView({block: 'center'}); const r = m.getClientRects()[0], x = r.left + r.width / 2, y = r.top + r.height / 2;
  const t = document.elementFromPoint(x, y), o = {pointerId: 5, pointerType: 'touch', isPrimary: true, bubbles: true, clientX: x, clientY: y};
  t.dispatchEvent(new PointerEvent('pointerdown', o)); t.dispatchEvent(new PointerEvent('pointerup', o)); t.dispatchEvent(new MouseEvent('click', {bubbles: true, clientX: x, clientY: y})); return t.outerHTML.slice(0, 80); }"""


def jpg(color, w=640, h=360):
    b = io.BytesIO(); Image.new('RGB', (w, h), color).save(b, 'JPEG'); return b.getvalue()


def card_zip(path, cards):
    """An import zip with made-up cards of the made-up book."""
    with zipfile.ZipFile(path, 'w') as z:
        for c in cards: z.writestr(c['scene'], jpg((40, 50, 80)))
        z.writestr('manifest.json', json.dumps({'app': 'agora', 'version': 1, 'decks': [{'name': 'Vocabulary', 'cards': cards}]}))


def text_def(word):
    return {'source': 'made-up', 'kind': 'dictionary', 'blocks': [{'type': 'headword', 'text': word}, {'type': 'def', 'n': 1, 'text': 'a made-up meaning for this test'}]}


async def main(app, out):
    os.makedirs(out, exist_ok=True)
    fails = []
    def check(ok, what):
        print(('ok   ' if ok else 'FAIL ') + what)
        if not ok: fails.append(what)

    async with Phone(app) as ph:
        pg = ph.pg
        await pg.evaluate(FILL_JS, [base64.b64encode(open(BOOK, 'rb').read()).decode(), base64.b64encode(locked_copy()).decode()])
        await pg.evaluate("T.connectFiles(true)"); await pg.wait_for_function("T.FX.scanned && !T.FX.scanning", timeout=20000)
        await pg.evaluate("T.openFolder('Books')"); await pg.wait_for_timeout(500)

        async def open_book():
            await pg.locator('.page:last-child [data-fp="Books/The Salt Ledger.epub"]').first.click()
            await pg.wait_for_function("T.BK && T.BK.page && !document.querySelector('.bk-wait')", timeout=15000)
            await pg.wait_for_timeout(500); await pg.evaluate("document.querySelectorAll('.toast,.bk-toast').forEach(t => t.classList.remove('show'))")
        await open_book()
        await pg.evaluate("document.querySelector('[data-b=toc]').click()"); await pg.wait_for_timeout(400)
        await pg.locator('.bk-trow2', has_text='The Harbour Office').click(); await pg.wait_for_timeout(1200)
        info = await pg.evaluate("""(() => { const bs = T.BK.page.blocks; const i = bs.findIndex(b => b.querySelector('i') && /Marigold/.test(b.textContent));
          const t = bs[i].textContent, a = t.indexOf('the Marigold'); return [T.BK.ch, bs.length, i, a, bs.map(b => b.textContent)]; })()""")
        ch, nblocks, mp, ma, texts = info
        phrase = 'the Marigold, outbound, no cargo declared'
        check(ch == 3 and mp > 0 and ma > 0, f'the chapter with the pencilled line is open ({info[:4]})')
        await pg.evaluate(f"T.BK.page.scrollTop = T.BK.page.blocks[{mp}].offsetTop - 120"); await pg.wait_for_timeout(300)

        # A1: picking words shows the bar under them
        got = await pg.evaluate(PICK, [mp, ma, ma + len(phrase), None]); await pg.wait_for_timeout(500)
        bar = await pg.evaluate("""(() => { const b = document.querySelector('.bk-selbar'), r = b.getBoundingClientRect(), s = getSelection().getRangeAt(0).getBoundingClientRect();
          return [b.hidden, b.textContent.replace(/\\s+/g, ' ').trim(), Math.round(r.top - s.bottom), getComputedStyle(b.querySelector('button')).fontFamily]; })()""")
        check(got == phrase and not bar[0] and 'Vocabulary' in bar[1] and 'Concept' in bar[1] and '+ Question' in bar[1], f'picking words shows Vocabulary, Concept and + Question ({bar[:2]})')
        check(bar[2] > 20 and 'Merriweather' in bar[3], f'the bar sits under the words, clear of the phone\'s handles, in Merriweather ({bar[2]} px)')
        await ph.shot(f'{out}/01-picked-bar.png')

        # a sideways drag while words are picked doesn't turn the chapter
        await pg.evaluate(SWIPE, [-260]); await pg.wait_for_timeout(700)
        check(await pg.evaluate("T.BK.ch") == 3, 'a drag while words are picked never turns the chapter')
        await pg.evaluate(PICK, [mp, ma, ma + len(phrase), None]); await pg.wait_for_timeout(500)

        # Vocabulary: saved with where it sits, a white underline, Undo
        await pg.locator('.bk-selbar [data-sb=vocabulary]').click(); await pg.wait_for_timeout(700)
        n = await pg.evaluate("""(() => { const n = [...T.CN.recs.values()].find(x => x.book); const m = [...document.querySelectorAll('mark.hl')];
          return [n && n.kind, n && n.text, n && n.src.type, n && n.src.title, n && n.book.chapter, n && n.book.p0, n && n.book.o0, n && n.book.o1, n && n.book.prefix.length, n && n.book.paras.length,
            m.map(x => x.className).join(','), m.map(x => x.textContent).join(''), getSelection().isCollapsed, document.querySelector('.bk-selbar').hidden,
            document.querySelector('.bk-toast') && document.querySelector('.bk-toast').textContent, getComputedStyle(m[0]).textDecorationLine]; })()""")
        print('  saved:', n)
        check(n[:5] == ['vocabulary', phrase, 'book', 'The Salt Ledger', 'The Harbour Office'] and n[5] == mp and n[6] == ma and n[7] == ma + len(phrase), 'Vocabulary saves the words with the book, chapter, paragraph and characters')
        check(n[8] == 32 and n[9] >= 3, 'the words before and after, and the paragraphs around, are kept')
        check('hl s' in n[10] and n[11] == phrase and n[15] == 'underline', 'the saved words get a white underline (B1)')
        check(n[12] and n[13] and n[14] and 'Undo' in n[14], 'the selection and bar go, and a toast offers Undo')
        await ph.shot(f'{out}/02-saved-underline.png')
        await pg.locator('.bk-toast button').click(); await pg.wait_for_timeout(500)
        u = await pg.evaluate("[[...T.CN.recs.values()].filter(x => x.book).length, document.querySelectorAll('mark.hl').length]")
        check(u == [0, 0], f'Undo takes them back off ({u})')

        # + Question, then Concept
        await pg.evaluate(PICK, [mp, ma, ma + len(phrase), None]); await pg.wait_for_timeout(500)
        await pg.locator('.bk-selbar [data-sb=q]').click(); await pg.wait_for_timeout(600)
        q = await pg.evaluate("[!!document.querySelector('#sheet.open, .sheet.open, #askIn'), document.querySelectorAll('mark.hl.pend').length]")
        await ph.shot(f'{out}/03-question.png')
        await pg.fill('#askIn', 'Why is there no date?'); await pg.press('#askIn', 'Enter'); await pg.wait_for_timeout(600)
        qb = await pg.evaluate("[document.querySelector('.bk-selbar').hidden, document.querySelector('.bk-selbar [data-sb=q]').textContent, document.querySelectorAll('mark.hl.pend').length]")
        check(q[0] and q[1] > 0 and qb == [False, 'Question ✓', q[1]], f'+ Question asks, the words stay marked and the bar comes back ({q}, {qb})')
        await ph.shot(f'{out}/04-question-added.png')
        await pg.locator('.bk-selbar [data-sb=concept]').click(); await pg.wait_for_timeout(900)
        c = await pg.evaluate("""(() => { const n = [...T.CN.recs.values()].find(x => x.book); return [n && n.kind, n && n.question, document.querySelectorAll('mark.hl.pend').length,
          document.querySelectorAll('mark.hl.s').length, history.state && history.state.agora, T.pages.length]; })()""")
        note_id = await pg.evaluate("[...T.CN.recs.values()].find(x => x.book).id")
        check(c[:4] == ['concept', 'Why is there no date?', 0, c[3]] and c[3] > 0, f'Concept saves them with the question ({c})')

        # a pick across two paragraphs
        lo = next(i for i in range(nblocks - 1) if abs(i - mp) > 1 and len(texts[i]) > 100 and len(texts[i + 1]) > 100); hi = lo + 1
        a0 = texts[lo].rfind(' ', 0, len(texts[lo]) - 30) + 1; b0 = texts[hi].find(' ', 20)
        await pg.evaluate(f"T.BK.page.scrollTop = T.BK.page.blocks[{lo}].offsetTop - 160"); await pg.wait_for_timeout(300)
        await pg.evaluate(PICK, [lo, a0, b0, hi]); await pg.wait_for_timeout(500)
        await pg.locator('.bk-selbar [data-sb=vocabulary]').click(); await pg.wait_for_timeout(800)
        x2 = await pg.evaluate(f"""(() => {{ const n = [...T.CN.recs.values()].filter(x => x.book).sort((a, b) => b.createdAt - a.createdAt)[0];
          const ms = [...document.querySelectorAll('mark.hl.s')].filter(m => m.dataset.hl === n.id); return [n.book.p0, n.book.p1, new Set(ms.map(m => T.BK.page.blocks.findIndex(b => b.contains(m)))).size, n.text]; }})()""")
        check(x2[0] == lo and x2[1] == hi and x2[2] == 2, f'words picked across two paragraphs are saved and underlined in both ({x2[:3]})')
        await ph.shot(f'{out}/05-two-paragraphs.png')

        # a tap on the underline: the strip, with Remove; Back closes it
        await pg.evaluate("document.querySelectorAll('.bk-toast').forEach(t => t.remove())")
        await pg.evaluate(TAP, [f'mark.hl.s[data-hl="{note_id}"]']); await pg.wait_for_timeout(400)
        s = await pg.evaluate("document.querySelector('.bk-strip') && document.querySelector('.bk-strip').textContent.replace(/\\s+/g, ' ')")
        check(s and 'Saved for a Concept card' in s and 'Remove' in s and 'no date' in s, f'a tap on saved words shows them with Remove ({s})')
        await ph.shot(f'{out}/06-strip-saved.png')
        await ph.back()
        check(await pg.evaluate("!document.querySelector('.bk-strip') && !!T.BK"), 'Back closes the strip and stays in the book')
        check(await pg.evaluate("T.BK.ui") is False, 'a tap on a highlight doesn\'t bring up the controls')

        # close, import a card made from the words (fromNote) and a card of this book found by its paragraph
        cp = next(i for i, t in enumerate(texts) if i not in (mp, lo, hi) and len(t) > 200 and ' ledger ' in t.lower())
        para = texts[cp]; wi = para.lower().index(' ledger ') + 1
        scene = para[:wi] + '==' + para[wi:wi + 6] + '==' + para[wi + 6:]
        await ph.back(); await pg.wait_for_timeout(400)
        tmp = tempfile.mkdtemp(); zp = os.path.join(tmp, 'book-cards.zip')
        card_zip(zp, [
            {'id': 'test-book-marigold', 'word': 'Marigold', 'shotAt': 1790000000000, 'scene': 'images/marigold.jpg', 'definitions': [None], 'definitionText': [text_def('Marigold')],
             'sceneText': {'paras': [f'The line in pencil read *==the Marigold==, outbound, no cargo declared*.']}, 'tags': ['Book', 'The Salt Ledger'], 'fromNote': note_id},
            {'id': 'test-book-ledger', 'word': 'ledger', 'shotAt': 1790000001000, 'scene': 'images/ledger.jpg', 'definitions': [None], 'definitionText': [text_def('ledger')],
             'sceneText': {'paras': [scene]}, 'tags': ['Book', 'The Salt Ledger']}])
        t = await ph.imp([zp]); print('  import:', t)
        await open_book()
        blue = await pg.evaluate(f"""(() => {{ const a = [...document.querySelectorAll('mark.hl.c[data-hl="{note_id}"]')], b = [...document.querySelectorAll('mark.hl.c[data-card="test-book-ledger"]')];
          return [T.BK.ch, a.map(m => m.textContent).join(''), b.map(m => m.textContent).join(''), b[0] ? T.BK.page.blocks.findIndex(x => x.contains(b[0])) : -1,
            a[0] ? getComputedStyle(a[0]).backgroundColor : '']; }})()""")
        print('  blue:', blue)
        check(blue[0] == 3 and blue[1] == phrase, 'words a card was made from turn blue (B1)')
        check(blue[2].lower() == 'ledger' and blue[3] == cp, 'a card of this book shows on its page, found by its scene\'s paragraph')
        check('0, 134, 255' in blue[4], 'the blue is the soft blue fill')
        await pg.evaluate(f"T.BK.page.scrollTop = T.BK.page.blocks[{cp}].offsetTop - 200"); await pg.wait_for_timeout(300)
        await ph.shot(f'{out}/07-blue-highlights.png')

        # C1: a tap on the blue one shows its card; Open card above the book; Back to the page
        await pg.evaluate(TAP, ['mark.hl.c[data-card="test-book-ledger"]']); await pg.wait_for_timeout(600)
        s = await pg.evaluate("document.querySelector('.bk-strip') && [document.querySelector('.bk-strip b').textContent, document.querySelector('.bk-strip small').textContent, document.querySelector('.bk-strip button').textContent, !!document.querySelector('.bk-strip img').src]")
        check(s and s[0] == 'ledger' and 'card made' in s[1] and s[2] == 'Open card' and s[3], f'a tap shows the card in a strip at the bottom (C1) ({s})')
        await ph.shot(f'{out}/08-card-strip.png')
        top = await pg.evaluate("T.BK.page.scrollTop")
        await pg.locator('.bk-strip [data-k=open]').click(); await pg.wait_for_timeout(1100)
        o = await pg.evaluate("[!!T.S, T.S && T.S.order.map(c => c.id), document.querySelector('.study:last-of-type') && getComputedStyle(document.querySelector('.study')).zIndex, document.querySelector('.study .wordbtn').textContent]")
        check(o[0] and o[1] == ['test-book-marigold', 'test-book-ledger'] and o[2] == '55' and o[3] == 'ledger', f'Open card shows it above the book, among the book\'s cards in reading order ({o})')
        await ph.shot(f'{out}/09-card-open.png')
        await ph.back(); await pg.wait_for_timeout(300)
        r = await pg.evaluate("[!document.querySelector('.study'), !!T.BK, T.BK && T.BK.ch, T.BK && Math.round(T.BK.page.scrollTop), !document.querySelector('.bk-strip')]")
        check(r[:3] == [True, True, 3] and abs(r[3] - top) < 4 and r[4], f'Back comes back to the same place in the book ({r})')

        # a plain tap still shows the controls, and a swipe still turns the chapter
        await pg.evaluate(SWIPE, [-260]); await pg.wait_for_timeout(900)
        check(await pg.evaluate("T.BK.ch") == 4, 'with nothing picked, a swipe still turns the chapter')

        # For cards: the book's tile and its rows
        await ph.back(); await pg.wait_for_timeout(400)
        await pg.evaluate("T.openCardNotes()"); await pg.wait_for_timeout(800)
        tile = await pg.evaluate("""[...document.querySelectorAll('.page:last-child .src')].map(s => [s.querySelector('.tile-name').textContent, s.querySelector('.tile-meta').textContent, !!s.querySelector('img').src])""")
        check(tile == [['The Salt Ledger', '2 lines', True]], f'For cards has a tile for the book with its cover ({tile})')
        await ph.shot(f'{out}/10-for-cards.png')
        await pg.locator('.page:last-child [data-cng]').first.click(); await pg.wait_for_timeout(700)
        rows = await pg.evaluate("[...document.querySelectorAll('.page:last-child .cnrow')].map(r => [r.querySelector('.ln b') && r.querySelector('.ln b').textContent, r.querySelector('.mt').textContent, r.querySelector('.qq') && r.querySelector('.qq').textContent])")
        print('  rows:', rows)
        check(len(rows) == 2 and rows[1][0] == phrase and 'The Harbour Office · Concept · card made' in rows[1][1] and 'no date' in rows[1][2], 'each row shows the words in blue, the chapter, Concept or Vocabulary, "card made" and the question')
        await ph.shot(f'{out}/11-book-lines.png')

        # Read from here
        await pg.locator('.page:last-child .cnrow').nth(1).click(); await pg.wait_for_timeout(500)
        sh = await pg.evaluate("document.querySelector('#sheet') ? document.querySelector('#sheet').textContent : ''")
        check('Read from here' in sh and 'Play from here' not in sh, 'a row\'s menu offers Read from here')
        await pg.locator('#sheet [data-act=play]').click()
        await pg.wait_for_function("T.BK && T.BK.page && !document.querySelector('.bk-wait')", timeout=15000); await pg.wait_for_timeout(500)
        rd = await pg.evaluate(f"""(() => {{ const b = T.BK.page.blocks[{mp}].getBoundingClientRect(); return [T.BK.ch, b.top > 0 && b.bottom < innerHeight, !!document.querySelector('mark.hl.c')]; }})()""")
        check(rd == [3, True, True], f'Read from here opens the book at those words ({rd})')
        await ph.shot(f'{out}/12-read-from-here.png')
        await ph.back()

        # the zip for the card chat
        z = await pg.evaluate("""(async () => { await T.loadZip(); const b = await T.cnZip([...T.CN.recs.values()]); const zip = await JSZip.loadAsync(b);
          const j = JSON.parse(await zip.file('notes.json').async('string')); return [j, Object.keys(zip.files)]; })()""")
        bn = next(x for x in z[0]['notes'] if x['id'] == note_id); b = bn['book']
        check(bn['kind'] == 'concept' and bn['question'] == 'Why is there no date?' and bn['selection']['text'] == phrase and 'video' not in bn, 'the zip has the words, the kind and the question')
        check(b['title'] == 'The Salt Ledger' and b['author'] == 'M. A. Invented' and b['tags'] == ['Book', 'The Salt Ledger'] and b['chapter'] == {'title': 'The Harbour Office', 'index': 3}, f'the zip has the book, its tags and the chapter ({b["chapter"]})')
        check(f'=={phrase}==' in b['para']['text'] and b['para']['index'] == mp and len(b['before']) == 2 and len(b['after']) == 2, 'the paragraph is marked ==like this==, with two paragraphs either side')
        check(b['position']['exact'] == phrase and len(b['position']['prefix']) == 32 and b['cover'] in z[1] and bn.get('cards') == ['test-book-marigold'], 'where they sit, the cover and the card made from them are in the zip')

        # backups: a fresh phone gets them back; a re-import changes nothing
        bk = await pg.evaluate("""(async () => { await T.loadZip(); const zip = new JSZip(); const m = await T.exportCardNotes(zip);
          const again = await T.importCardNotes(m.notes, async x => null);
          const ids = [...T.CN.recs.keys()]; ids.forEach(k => T.CN.recs.delete(k)); T.CN.gone.clear(); await T.cstore.del('frames', ids.flatMap(i => [i, i + '-t']));
          const back = await T.importCardNotes(m.notes, async x => x.frame ? zip.file(x.frame).async('arraybuffer') : null);
          const n = [...T.CN.recs.values()].find(x => x.book && x.question);
          return [again, back, !!(await T.cstore.get('frames', n.id + '-t')), n.book.exact, n.book.paras.length, n.src.author]; })()""")
        check(bk[0] == 0 and bk[1] == 2 and bk[2] and bk[3] == phrase and bk[4] >= 3 and bk[5] == 'M. A. Invented', f'a backup brings the book\'s lines back on a fresh phone; a re-import changes nothing ({bk})')
        t = await ph.imp([zp]); check('up to date' in t, f'importing the book\'s cards again changes nothing ({t})')

        print('errors:', ph.errors)
        check(not ph.errors, 'no JavaScript errors')

    print('\nALL OK' if not fails else f'\n{len(fails)} FAILED')
    return 1 if fails else 0


if __name__ == '__main__':
    a = argparse.ArgumentParser(); a.add_argument('app'); a.add_argument('--out', default='shots/booknotes')
    a = a.parse_args()
    sys.exit(asyncio.run(main(a.app, a.out)))
