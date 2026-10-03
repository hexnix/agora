"""The book reader (v44): a made-up book in a made-up My Files, on a phone held upright (412×915).

    python3 tools/app-test/test_books.py . --out shots/books/

Checks that a tap on the .epub opens the reader on its first page (the cover), Merriweather for every word, the chapter's name and
how far you are, the book's own styles and scripts left out, a sideways swipe to the next and the previous chapter (and none past
either end), a chapter scrolling to its end and stopping there, a tap showing and hiding the controls, the bar moving through the
book, the contents page (C1: chapters, a section, "You're here", going to one), a note link and its way back, text size, lines and
margins kept, the place kept when the book opens again, Back one step at a time, a locked (DRM) book saying so, and JavaScript errors.
Everything is invented: never put real books in the repo.
"""
import argparse, asyncio, base64, io, os, sys, zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import Phone

KIT = os.path.dirname(os.path.abspath(__file__))
BOOK = os.path.join(KIT, 'fixtures', 'made-up-book.epub')

FILL_JS = r"""
async ([book, locked]) => {
  const root = await navigator.storage.getDirectory();
  for await (const [n] of root.entries()) await root.removeEntry(n, { recursive: true });
  const put = async (path, b64) => {
    const parts = path.split('/'); let d = root;
    for (const p of parts.slice(0, -1)) d = await d.getDirectoryHandle(p, { create: true });
    const w = await (await d.getFileHandle(parts[parts.length - 1], { create: true })).createWritable();
    await w.write(new Blob([Uint8Array.from(atob(b64), c => c.charCodeAt(0))])); await w.close();
  };
  await put('Books/The Salt Ledger.epub', book);
  await put('Books/Locked.epub', locked);
  window.showDirectoryPicker = async () => root;
}
"""


SWIPE = """([dx]) => { const el = document.querySelector('.bk-page'); const o = {pointerId: 7, pointerType: 'touch', isPrimary: true, bubbles: true}; const x = 206, y = 450, n = 10;
  el.dispatchEvent(new PointerEvent('pointerdown', {...o, clientX: x, clientY: y}));
  return new Promise(r => { let i = 0; const f = () => { i++; el.dispatchEvent(new PointerEvent('pointermove', {...o, clientX: x + dx * i / n, clientY: y}));
    if (i < n) setTimeout(f, 16); else { el.dispatchEvent(new PointerEvent('pointerup', {...o, clientX: x + dx, clientY: y})); r(); } }; setTimeout(f, 16); }); }"""


def locked_copy():
    """The same book with its pages marked as encrypted, the way a shop's DRM does."""
    src, out = zipfile.ZipFile(BOOK), io.BytesIO()
    with zipfile.ZipFile(out, 'w') as z:
        for n in src.namelist(): z.writestr(n, src.read(n))
        z.writestr('META-INF/encryption.xml', '<?xml version="1.0"?><encryption xmlns="urn:oasis:names:tc:opendocument:xmlns:container" xmlns:enc="http://www.w3.org/2001/04/xmlenc#">'
                   '<enc:EncryptedData><enc:CipherData><enc:CipherReference URI="OEBPS/text/ch1.xhtml"/></enc:CipherData></enc:EncryptedData></encryption>')
    return out.getvalue()


async def main(app, out):
    os.makedirs(out, exist_ok=True)
    fails = []
    def check(ok, what):
        print(('ok   ' if ok else 'FAIL ') + what)
        if not ok: fails.append(what)

    async with Phone(app) as ph:
        pg = ph.pg
        b64 = base64.b64encode(open(BOOK, 'rb').read()).decode(); lk = base64.b64encode(locked_copy()).decode()
        await pg.evaluate(FILL_JS, [b64, lk])
        await pg.evaluate("T.connectFiles(true)")
        await pg.wait_for_function("T.FX.scanned && !T.FX.scanning", timeout=20000)
        await pg.evaluate("T.openFolder('Books')"); await pg.wait_for_timeout(500)
        await pg.locator('.page:last-child [data-fp="Books/The Salt Ledger.epub"]').first.click()
        await pg.wait_for_function("T.BK && T.BK.page && !document.querySelector('.bk-wait')", timeout=15000)
        await pg.wait_for_timeout(400)
        st = await pg.evaluate("[T.BK.title, T.BK.author, T.BK.pages.length, T.BK.ch, !!document.querySelector('.bk-page img'), document.querySelector('.bk-title').textContent]")
        check(st[:4] == ['The Salt Ledger', 'M. A. Invented', 7, 0] and st[4], f'the book opens on its cover, with its title and author ({st})')
        await ph.shot(f'{out}/01-cover.png')

        # the next chapter by a swipe
        await pg.evaluate(SWIPE, [-260]); await pg.wait_for_timeout(900)
        c1 = await pg.evaluate("""[T.BK.ch, document.querySelector('.bk-ch').textContent, document.querySelector('.bk-prog').textContent,
          getComputedStyle(document.querySelector('.bk-text p')).fontFamily, getComputedStyle(document.querySelector('.bk-text p')).color,
          getComputedStyle(document.querySelector('.bk-ch')).fontFamily, !!document.querySelector('.bk-text [style],.bk-text [onclick],.bk-text script,.bk-text style,.bk-text [class]'), !!window.pwned]""")
        print('  ch1:', c1)
        check(c1[0] == 1 and c1[1] == 'The Last Ferry' and 'min left in chapter' in c1[2], 'a swipe opens the next chapter, its name on top and how far below')
        check('Merriweather' in c1[3] and 'Merriweather' in c1[5] and c1[4] == 'rgb(228, 228, 228)', 'the text and the lines around it are Merriweather')
        check(not c1[6] and not c1[7], "the book's own styles and scripts are left out")
        await ph.shot(f'{out}/02-chapter.png')

        # the chapter scrolls to its end and stops there
        await pg.evaluate("T.BK.page.scrollTop = 1e6"); await pg.wait_for_timeout(500)
        end = await pg.evaluate("[T.BK.ch, Math.round(T.BK.page.scrollTop + T.BK.page.clientHeight - T.BK.page.scrollHeight), document.querySelector('.bk-end').textContent, document.querySelector('.bk-prog').textContent]")
        check(end[0] == 1 and abs(end[1]) <= 2 and 'A Box of Letters' in end[2] and 'End of chapter' in end[3], f'scrolling stops at the end of the chapter, which names the next ({end})')
        await ph.shot(f'{out}/03-chapter-end.png')
        await pg.evaluate(SWIPE, [-260]); await pg.wait_for_timeout(900)
        await pg.evaluate(SWIPE, [260]); await pg.wait_for_timeout(900)
        back1 = await pg.evaluate("[T.BK.ch, T.BK.page.scrollTop > 100]")
        check(back1 == [1, True], f'swiping back returns to the chapter where it was left ({back1})')
        await pg.evaluate("T.BK.page.scrollTop = 0"); await pg.evaluate(SWIPE, [260]); await pg.wait_for_timeout(900)
        await pg.evaluate(SWIPE, [260]); await pg.wait_for_timeout(900)
        check(await pg.evaluate("T.BK.ch") == 0, 'there is nothing before the first page')

        # a tap shows the controls, another hides them
        await pg.mouse.click(206, 500); await pg.wait_for_timeout(400)
        ui = await pg.evaluate("[document.querySelector('.book').classList.contains('ui'), getComputedStyle(document.querySelector('.bk-title')).fontFamily]")
        check(ui[0] and 'Merriweather' in ui[1], 'a tap shows the controls, in Merriweather')
        # the bar: a tap near the middle goes there
        bx = await pg.locator('.bk-track').bounding_box()
        await pg.mouse.click(bx['x'] + bx['width'] * 0.55, bx['y'] + 1); await pg.wait_for_timeout(1000)
        mid = await pg.evaluate("[T.BK.ch, T.BK.pct]")
        check(mid[0] >= 3 and 40 <= mid[1] <= 70, f'the bar moves through the book ({mid})')
        await ph.shot(f'{out}/04-controls.png')

        # the contents
        await pg.click('.bk-top [data-b="toc"]'); await pg.wait_for_timeout(500)
        toc = await pg.evaluate("[[...document.querySelectorAll('.bk-trow2')].map(r => r.querySelector('.nm').textContent), document.querySelector('.bk-trow2.on .pg').textContent, document.querySelector('.bk-toc .summary:nth-of-type(2)') && document.querySelectorAll('.bk-toc .summary')[1].textContent]")
        print('  contents:', toc)
        check(toc[0][:4] == ['The Last Ferry', 'A Box of Letters', 'The Harbour Office', 'The clerk'] and 'Notes' in toc[0] and toc[1] == 'You’re here', 'the contents list the chapters and a section, marking where you are')
        check('6 chapters' in (toc[2] or '') and '% read' in toc[2], f'and say how much is read ({toc[2]})')
        await ph.shot(f'{out}/05-contents.png')
        await ph.back(); await pg.wait_for_timeout(400)
        check(await pg.evaluate("!document.querySelector('.bk-toc') && !!T.BK"), 'Back closes the contents, the book stays')
        await pg.click('.bk-top [data-b="toc"]'); await pg.wait_for_timeout(500)
        await pg.locator('.bk-trow2', has_text='The clerk').click(); await pg.wait_for_timeout(1200)
        sec = await pg.evaluate("(() => { const t = document.querySelector('.bk-page [data-id=\"c3b\"]'); return [T.BK.ch, !!t && Math.abs(t.getBoundingClientRect().top - T.BK.page.getBoundingClientRect().top) < 60, !document.querySelector('.bk-toc')]; })()")
        check(sec == [3, True, True], f'a section in the contents opens its chapter at that heading ({sec})')

        # a note link and its way back
        await pg.evaluate("document.querySelector('.bk-page a[data-id=\"r1\"]').scrollIntoView({block: 'center'})"); await pg.wait_for_timeout(300)
        await pg.click('.bk-page a[data-id="r1"]'); await pg.wait_for_timeout(1100)
        note = await pg.evaluate("[T.BK.ch, document.querySelector('.bk-page').textContent.includes('Pencil fades')]")
        check(note == [6, True], f'a note link opens the notes ({note})')
        await pg.click('.bk-page a[data-to]'); await pg.wait_for_timeout(1100)
        check(await pg.evaluate("T.BK.ch") == 3, 'and its Back link returns to the chapter')

        # text size, lines and margins
        await pg.mouse.click(206, 500); await pg.wait_for_timeout(400)
        if not await pg.evaluate("document.querySelector('.book').classList.contains('ui')"):
            await pg.mouse.click(206, 500); await pg.wait_for_timeout(400)
        await pg.click('.bk-top [data-b="text"]'); await pg.wait_for_timeout(500)
        await pg.click('#sheet [data-act="bigger"]'); await pg.click('#sheet [data-act="bigger"]'); await pg.click('#sheet [data-act="l-open"]'); await pg.click('#sheet [data-act="m-wide"]')
        await pg.wait_for_timeout(300)
        await ph.shot(f'{out}/06-text-size.png')
        ts = await pg.evaluate("[getComputedStyle(document.querySelector('.bk-text')).fontSize, getComputedStyle(document.querySelector('.bk-page')).paddingLeft, document.querySelector('#sheet .bk-n').textContent, getComputedStyle(document.querySelector('#sheet h2')).fontFamily]")
        check(ts[:3] == ['19px', '34px', '19'] and 'Merriweather' in ts[3], f'Aa makes the text bigger, the lines open and the margins wide ({ts})')
        await ph.back(); await pg.wait_for_timeout(400)
        await pg.evaluate("T.BK.page.scrollTop = T.BK.page.scrollHeight * 0.3"); await pg.wait_for_timeout(1200)
        place = await pg.evaluate("[T.BK.ch, T.BK.rec.y]")

        # Back leaves the book; it opens again where it was, in the same size
        await pg.mouse.click(206, 500); await pg.wait_for_timeout(400)
        if await pg.evaluate("document.querySelector('.book').classList.contains('ui')"):
            await pg.mouse.click(206, 500); await pg.wait_for_timeout(400)
        await ph.back(); await pg.wait_for_timeout(500)
        check(await pg.evaluate("!T.BK && !document.querySelector('.book') && T.pages.length > 0"), 'Back leaves the book for the folder')
        await pg.locator('.page:last-child [data-fp="Books/The Salt Ledger.epub"]').first.click()
        await pg.wait_for_function("T.BK && T.BK.page && !document.querySelector('.bk-wait')", timeout=15000); await pg.wait_for_timeout(600)
        again = await pg.evaluate("[T.BK.ch, Math.abs(T.BK.page.scrollTop / (T.BK.page.scrollHeight - T.BK.page.clientHeight) - %f) < 0.05, getComputedStyle(document.querySelector('.bk-text')).fontSize, document.querySelector('.toast') && document.querySelector('.toast').textContent]" % place[1])
        check(again[:3] == [place[0], True, '19px'] and 'Carrying on' in (again[3] or ''), f'opened again, it carries on where it was, in the same size ({again})')
        await ph.shot(f'{out}/07-again.png')
        await ph.back(); await pg.wait_for_timeout(500)

        # a locked book says so
        await pg.locator('.page:last-child [data-fp="Books/Locked.epub"]').first.click(); await pg.wait_for_timeout(2500)
        lk = await pg.evaluate("(document.querySelector('.bk-wait') || {}).textContent || ''")
        check('DRM' in lk and 'Share' in lk, f'a locked book says it can’t be opened ({lk.strip()[:60]})')
        await ph.shot(f'{out}/08-locked.png')
        await ph.back(); await pg.wait_for_timeout(500)
        check(await pg.evaluate("!T.BK"), 'and Back leaves it')
        print('errors:', ph.errors)
        check(not ph.errors, 'no JavaScript errors')

    print('\nALL OK' if not fails else f'\n{len(fails)} FAILED')
    return 1 if fails else 0


if __name__ == '__main__':
    a = argparse.ArgumentParser(); a.add_argument('app'); a.add_argument('--out', default='shots/books')
    a = a.parse_args()
    sys.exit(asyncio.run(main(a.app, a.out)))
