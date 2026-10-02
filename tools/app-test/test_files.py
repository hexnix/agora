"""My Files test: a made-up folder in the origin private file system stands in for the phone's My Files.

    python3 tools/app-test/test_files.py . --out shots/files/

Checks the folder index (hidden files skipped), the list and grid views, the path, hold-to-select and the tag sheet,
quick tagging, the tags copy in .agora/file-tags.json, search mixing cards and files, the file viewer (picture, PDF, text),
a moved file keeping its tags, Back stepping out one layer at a time, the backup carrying file tags, re-imports reporting
"already up to date", updating from older versions (even with one still open in another tab), and JavaScript errors. Screenshots go to --out.
Everything here is made up: never put real files in the repo.
"""
import argparse, asyncio, base64, json, os, shutil, subprocess, sys, tempfile, zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import Phone

KIT = os.path.dirname(os.path.abspath(__file__))
LIB_ZIP = os.path.join(KIT, 'fixtures', 'test-library.zip')


def tiny_pdf(title, lines, pages=2):
    """A small valid PDF with a title and some lines of text on each page."""
    objs, kids = [], []
    font = 3
    objs.append(None); objs.append(None)  # 1: catalog, 2: pages (filled below)
    objs.append(b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>')
    for p in range(pages):
        txt = [f'BT /F1 22 Tf 60 760 Td ({title}) Tj ET'] + [f'BT /F1 12 Tf 60 {720 - 20 * i} Td ({l} - page {p + 1}) Tj ET' for i, l in enumerate(lines)]
        stream = '\n'.join(txt).encode()
        objs.append(b'<< /Length %d >>\nstream\n' % len(stream) + stream + b'\nendstream')
        cid = len(objs)
        objs.append(f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 {font} 0 R >> >> /Contents {cid} 0 R >>'.encode())
        kids.append(len(objs))
    objs[0] = b'<< /Type /Catalog /Pages 2 0 R >>'
    objs[1] = f'<< /Type /Pages /Kids [{" ".join(f"{k} 0 R" for k in kids)}] /Count {len(kids)} >>'.encode()
    out = bytearray(b'%PDF-1.4\n'); offs = []
    for i, o in enumerate(objs):
        offs.append(len(out)); out += f'{i + 1} 0 obj\n'.encode() + o + b'\nendobj\n'
    x = len(out)
    out += f'xref\n0 {len(objs) + 1}\n0000000000 65535 f \n'.encode() + b''.join(f'{o:010d} 00000 n \n'.encode() for o in offs)
    out += f'trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{x}\n%%EOF\n'.encode()
    return bytes(out)


# the made-up My Files folder: path → ('img', seed, w, h) | ('pdf', bytes) | ('txt', text) | ('bin', size)
TREE = {
    'Documents/Bank/statement-aug.pdf': ('pdf', tiny_pdf('Statement August', ['Opening balance', 'Rent', 'Groceries', 'Closing balance'])),
    'Documents/Bank/cheque-book.jpg': ('img', 4, 1200, 800),
    'Documents/ID/passport-scan.jpg': ('img', 3, 900, 1200),
    'Photos/beach.jpg': ('img', 5, 1600, 1200),
    'Photos/hills.jpg': ('img', 2, 1600, 1067),
    'Photos/city.png': ('img', 1, 800, 600),
    'Receipts/rent-receipt.pdf': ('pdf', tiny_pdf('Rent receipt', ['Received with thanks', 'September'], 1)),
    'Travel/goa-tickets.pdf': ('pdf', tiny_pdf('Goa tickets', ['Seat 14A', 'Departure 06:10'], 1)),
    'Travel/hotel-booking.png': ('img', 0, 1000, 700),
    'rent-agreement.pdf': ('pdf', tiny_pdf('Rent agreement', ['Clause 1', 'Clause 2', 'Clause 3'], 3)),
    'resume-2026.pdf': ('pdf', tiny_pdf('Resume', ['Experience', 'Education'], 1)),
    'notes.txt': ('txt', 'Things to remember\n\n- renew the passport\n- call the bank about the cheque book\n'),
    'budget-2026.xlsx': ('bin', 5000),
    '.nomedia': ('txt', ''),
    '.hidden-folder/secret.txt': ('txt', 'should never be listed'),
}

FILL_JS = r"""
async (tree) => {
  const root = await navigator.storage.getDirectory();
  for await (const [n] of root.entries()) await root.removeEntry(n, { recursive: true });
  const photo = (seed, w, h, type) => new Promise(res => {
    const c = document.createElement('canvas'); c.width = w; c.height = h; const g = c.getContext('2d');
    const pal = [['#2b3a55', '#0d1117'], ['#4a2333', '#120a0e'], ['#2f4a3a', '#0b120e'], ['#4b3f2a', '#14110b'], ['#38304f', '#0e0c14'], ['#23474d', '#0a1213']][seed % 6];
    const gr = g.createLinearGradient(0, 0, 0, h); gr.addColorStop(0, pal[0]); gr.addColorStop(1, pal[1]); g.fillStyle = gr; g.fillRect(0, 0, w, h);
    let r = seed * 9301 + 49297; const rnd = () => (r = (r * 9301 + 49297) % 233280) / 233280;
    for (let i = 0; i < 6; i++) { g.fillStyle = `rgba(255,255,255,${0.06 + rnd() * 0.16})`; g.beginPath(); g.arc(rnd() * w, rnd() * h, w * (0.05 + rnd() * 0.2), 0, 7); g.fill(); }
    c.toBlob(res, type, 0.85);
  });
  for (const [path, spec] of Object.entries(tree)) {
    const parts = path.split('/'); let d = root;
    for (const p of parts.slice(0, -1)) d = await d.getDirectoryHandle(p, { create: true });
    let blob;
    if (spec[0] === 'img') blob = await photo(spec[1], spec[2], spec[3], path.endsWith('.png') ? 'image/png' : 'image/jpeg');
    else if (spec[0] === 'pdf') blob = new Blob([Uint8Array.from(atob(spec[1]), c => c.charCodeAt(0))]);
    else if (spec[0] === 'txt') blob = new Blob([spec[1]]);
    else blob = new Blob([new Uint8Array(spec[1])]);
    const w = await (await d.getFileHandle(parts[parts.length - 1], { create: true })).createWritable(); await w.write(blob); await w.close();
  }
  window.showDirectoryPicker = async () => root; // the folder picker can't be clicked in a test
}
"""


def tree_for_js():
    return {p: (('pdf', base64.b64encode(s[1]).decode()) if s[0] == 'pdf' else s) for p, s in TREE.items()}


async def tap(ph, sel, i=0):
    await ph.pg.locator(sel).nth(i).click(); await ph.pg.wait_for_timeout(450)


async def layers(ph):
    return await ph.pg.evaluate("history.state && history.state.agora || 0")


async def main(app, out):
    os.makedirs(out, exist_ok=True)
    fails = []
    def check(ok, what):
        print(('ok   ' if ok else 'FAIL ') + what)
        if not ok: fails.append(what)

    async with Phone(app) as ph:
        pg = ph.pg
        print('import:', await ph.imp([LIB_ZIP]))
        await ph.shot(f'{out}/01-home-before-connect.png')
        check('Tap to connect' in await pg.inner_text('#home'), 'home tile asks to connect before the folder is chosen')

        await pg.evaluate(FILL_JS, tree_for_js())
        await pg.evaluate("T.connectFiles(true)")
        await pg.wait_for_function("T.FX.scanned && !T.FX.scanning", timeout=20000)
        paths = await pg.evaluate("[...T.fidx.keys()].sort()")
        want = sorted({p for p in TREE if not p.startswith('.')} | {'Documents', 'Documents/Bank', 'Documents/ID', 'Photos', 'Receipts', 'Travel'})
        check(paths == want, f'index lists every file and folder, hidden ones skipped ({len(paths)} entries)')
        await pg.wait_for_function("[...T.fidx.values()].filter(r => r.kind === 'file' && /\\.(jpg|png|pdf)$/.test(r.name)).every(r => r.thumbId || r.noThumb)", timeout=30000)
        check(await pg.evaluate("[...T.fidx.values()].filter(r => /\\.(jpg|png|pdf)$/.test(r.name)).every(r => r.thumbId)"), 'small pictures made for images and PDFs')
        await pg.evaluate("T.back && 0"); await pg.wait_for_timeout(300)
        await pg.evaluate("document.querySelector('#home') && 0")
        await ph.shot(f'{out}/02-home-connected.png')

        # the browser: list, grid, a subfolder with its path
        await tap(ph, '[data-files]')
        await ph.shot(f'{out}/03-browser-list.png')
        await tap(ph, '[data-p="view"]')
        await ph.shot(f'{out}/04-browser-grid.png')
        await tap(ph, '[data-p="view"]')
        await tap(ph, '.page:last-child [data-fd="Documents"]')
        await tap(ph, '.page:last-child [data-fd="Documents/Bank"]')
        await ph.shot(f'{out}/05-browser-subfolder.png')
        check('My Files' in await pg.inner_text('.page:last-child .crumbs'), 'subfolder shows the path My Files › Documents › Bank')
        await tap(ph, '.page:last-child .crumbs button[data-crumb=""]')
        check(await pg.evaluate("T.pages.length") == 1, 'tapping My Files in the path steps back to the top folder')

        # hold to select, then tag three files at once
        await ph.hold('.page:last-child [data-fp="rent-agreement.pdf"]')
        await tap(ph, '.page:last-child [data-fp="resume-2026.pdf"]')
        await tap(ph, '.page:last-child [data-fp="notes.txt"]')
        await ph.shot(f'{out}/06-selecting.png')
        await tap(ph, '[data-p="selmenu"]')
        await tap(ph, '#sheet [data-act="tag"]')
        await pg.fill('#ftagIn', 'Home'); await pg.press('#ftagIn', 'Enter'); await pg.wait_for_timeout(300)
        await pg.fill('#ftagIn', 'Contract'); await pg.press('#ftagIn', 'Enter'); await pg.wait_for_timeout(300)
        await tap(ph, '#sheet .chip.on[data-tag="Contract"]')  # take it off all three again
        await pg.fill('#ftagIn', 'Example Show'); await pg.press('#ftagIn', 'Enter'); await pg.wait_for_timeout(300)  # a tag the cards use
        await pg.evaluate("document.activeElement.blur()"); await pg.wait_for_timeout(300)
        await ph.shot(f'{out}/07-tag-sheet.png')
        tags = await pg.evaluate("['rent-agreement.pdf','resume-2026.pdf','notes.txt'].map(p => T.fidx.get(p).tags)")
        check(all(t == ['Home', 'Example Show'] for t in tags), f'three files tagged at once: {tags}')
        await tap(ph, '#sheet [data-act="done"]')
        await ph.back()  # stop selecting
        check(await pg.evaluate("!document.querySelector('.page:last-child .home').classList.contains('selecting')"), 'Back stops selecting')

        # quick tagging: one tag, tap files to add or remove it
        await tap(ph, '[data-p="fmore"]')
        await tap(ph, '#sheet [data-act="quick"]')
        await pg.fill('#qtIn', 'Bank'); await pg.press('#qtIn', 'Enter'); await pg.wait_for_timeout(600)
        await tap(ph, '.page:last-child [data-fd="Documents"]')
        await tap(ph, '.page:last-child [data-fd="Documents/Bank"]')
        await tap(ph, '.page:last-child [data-fp="Documents/Bank/statement-aug.pdf"]')
        await tap(ph, '.page:last-child [data-fp="Documents/Bank/cheque-book.jpg"]')
        await tap(ph, '.page:last-child [data-fp="Documents/Bank/cheque-book.jpg"]')  # off again
        await tap(ph, '.page:last-child [data-fp="Documents/Bank/cheque-book.jpg"]')  # and on
        await ph.shot(f'{out}/08-quick-tagging.png')
        check(await pg.evaluate("T.fidx.get('Documents/Bank/cheque-book.jpg').tags.join()") == 'Bank', 'quick tagging adds and removes one tag per tap')
        await ph.back(); await ph.back()   # the two folders
        check(await pg.evaluate("!!T.FX.mode"), 'Back steps out of folders first, still tagging')
        await ph.back()
        check(await pg.evaluate("!T.FX.mode && T.pages.length === 1"), 'then Back ends quick tagging')

        # the second copy of the tags, inside the folder
        await pg.wait_for_timeout(1200); await pg.evaluate("T.saveTagsFile()")
        js = await pg.evaluate("""async () => { const r = await navigator.storage.getDirectory(); const d = await r.getDirectoryHandle('.agora');
          return await (await (await d.getFileHandle('file-tags.json')).getFile()).text(); }""")
        saved = {e['path']: e['tags'] for e in json.loads(js)['files']}
        check(saved.get('Documents/Bank/statement-aug.pdf') == ['Bank'] and saved.get('notes.txt') == ['Home', 'Example Show'], '.agora/file-tags.json holds the tags')
        check(await pg.evaluate("[...T.fidx.keys()].every(p => !p.startsWith('.agora'))"), 'the .agora folder never shows in My Files')

        # search: cards and files together, then a tag that both carry
        await pg.evaluate("T.back()"); await pg.wait_for_timeout(600)
        await tap(ph, '#searchBtn')
        await pg.fill('#q', 're'); await pg.wait_for_timeout(400)
        await ph.shot(f'{out}/09-search-re.png')
        txt = await pg.inner_text('#results')
        check('reticent' in txt and 'resume-2026.pdf' in txt and 'Receipts' in txt, 'search finds cards, files and folders')
        await pg.fill('#q', ''); await pg.wait_for_timeout(200)
        await pg.evaluate("T.openSearch(['Example Show'])"); await pg.wait_for_timeout(400)
        await ph.shot(f'{out}/10-search-tag.png')
        txt = await pg.inner_text('#results')
        check('candor' in txt and 'notes.txt' in txt, 'a tag shows the cards and the files that carry it')

        # the viewer: open a file from search, hold a tag, swipe, Back
        await tap(ph, '#results [data-fopen="rent-agreement.pdf"]')
        await pg.wait_for_function("T.FV && T.FV.slide && T.FV.slide.P", timeout=15000); await pg.wait_for_timeout(900)
        await ph.shot(f'{out}/11-viewer-pdf.png')
        check('page 1 of 3' in await pg.inner_text('.fview .vfoot'), 'a PDF opens inside Agora, page count shown')
        await ph.hold('.fview .tag')
        await ph.shot(f'{out}/12-viewer-tag-edit.png')
        check(await pg.evaluate("document.querySelector('.fview .tags').classList.contains('editing')"), 'holding a tag shows × and +')
        await pg.evaluate("T.back()"); await pg.wait_for_timeout(500)
        await pg.evaluate("T.openFolder('Photos')"); await pg.wait_for_timeout(500)
        await tap(ph, '.page:last-child [data-fp]')
        await pg.wait_for_function("T.FV && document.querySelector('.fview img.full[data-full]') && document.querySelector('.fview img.full').complete", timeout=10000); await pg.wait_for_timeout(500)
        await ph.shot(f'{out}/13-viewer-photo.png')
        first = await pg.evaluate("T.FV.i")
        await pg.evaluate("""() => { const el = document.querySelector('.vstage'); const o = { pointerId: 3, pointerType: 'touch', isPrimary: true, bubbles: true };
          el.dispatchEvent(new PointerEvent('pointerdown', { ...o, clientX: 320, clientY: 450 }));
          for (let i = 1; i <= 10; i++) el.dispatchEvent(new PointerEvent('pointermove', { ...o, clientX: 320 - i * 20, clientY: 452 }));
          el.dispatchEvent(new PointerEvent('pointerup', { ...o, clientX: 120, clientY: 452 })); }""")
        await pg.wait_for_timeout(700)
        check(await pg.evaluate("T.FV.i") == first + 1, 'swiping left shows the next file')
        await pg.evaluate("T.back()"); await pg.wait_for_timeout(500)
        check(await pg.evaluate("!T.FV && T.pages.length === 1"), 'Back closes the viewer, the folder stays')
        await pg.evaluate("T.back()"); await pg.wait_for_timeout(500)
        await pg.evaluate("T.openViewer([T.fidx.get('notes.txt')], 'notes.txt')"); await pg.wait_for_timeout(700)
        await ph.shot(f'{out}/14-viewer-text.png')
        check('renew the passport' in await pg.inner_text('.fview'), 'a text file shows its text')
        await pg.evaluate("T.back()"); await pg.wait_for_timeout(500)
        # a file Agora can't show: its name and Share / Open with… (sharing is stubbed: a test can't open Android's share sheet)
        await pg.evaluate("() => { navigator.canShare = () => true; navigator.share = async d => { window.shared = d.files.map(f => `${f.name}:${f.size}:${f.type}`); }; }")
        await pg.evaluate("T.openViewer([T.fidx.get('budget-2026.xlsx')], 'budget-2026.xlsx')"); await pg.wait_for_timeout(600)
        await ph.shot(f'{out}/16-viewer-other.png')
        await tap(ph, '.fview .vother [data-v="share"]'); await pg.wait_for_timeout(400)
        check(await pg.evaluate("(window.shared || []).join()") == 'budget-2026.xlsx:5000:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'Share hands the file itself to Android')
        await pg.evaluate("T.back()"); await pg.wait_for_timeout(500)
        await pg.evaluate("T.back()"); await pg.wait_for_timeout(500)  # search
        check(await layers(ph) == 0, 'Back leads all the way out to the home screen')

        # a moved file keeps its tags; a deleted one keeps them aside
        await pg.evaluate("T.setFileTags(['Photos/beach.jpg'], t => [...t, 'Goa'])")
        await pg.evaluate("""async () => { const r = await navigator.storage.getDirectory();
          const src = await (await r.getDirectoryHandle('Photos')).getFileHandle('beach.jpg');
          await src.move(await r.getDirectoryHandle('Travel')); }""")
        await pg.evaluate("T.FX.scanned = false; T.rescan()"); await pg.wait_for_function("T.FX.scanned && !T.FX.scanning")
        check(await pg.evaluate("(T.fidx.get('Travel/beach.jpg') || {}).tags?.join()") == 'Goa' and await pg.evaluate("!T.fidx.has('Photos/beach.jpg')"), 'a moved file keeps its tags')

        # not connected (as on the phone after a restart): browsing works from the index, one quiet line offers to connect
        await pg.evaluate("T.FX.ready = false"); await pg.evaluate("T.openFolder('')"); await pg.wait_for_timeout(500)
        await ph.shot(f'{out}/15-not-connected.png')
        await tap(ph, '.page:last-child [data-p="view"]'); await ph.shot(f'{out}/17-grid-tagged.png'); await tap(ph, '.page:last-child [data-p="view"]')
        check(await pg.locator('.page:last-child .connect').count() == 1, 'the Connect My Files line shows while not connected')
        await tap(ph, '.page:last-child .connect')
        await pg.wait_for_timeout(500)
        check(await pg.evaluate("T.FX.ready") and await pg.locator('.page:last-child .connect').count() == 0, 'one tap connects, the line goes away')
        await pg.evaluate("T.back()"); await pg.wait_for_timeout(500)
        await ph.shot(f'{out}/18-home-mosaic.png')
        check(await pg.locator('#home .mosaic img').count() == 4, 'the My Files tile shows the four newest pictures')

        # backup: includes file tags; re-importing it and the old library changes nothing
        await pg.click('#appMenu'); await pg.wait_for_timeout(500)
        async with pg.expect_download() as dl:
            await pg.click('#sheet [data-act="export"]')
        d = await dl.value; bpath = os.path.join(out, 'backup.zip'); await d.save_as(bpath)
        man = json.loads(zipfile.ZipFile(bpath).read('manifest.json'))
        ft = {e['path']: e['tags'] for e in man.get('files', {}).get('tags', [])}
        check(ft.get('Travel/beach.jpg') == ['Goa'] and len(man['decks']) == 2, 'the backup carries the file tags (not the files)')
        await pg.wait_for_timeout(2500)
        t = await ph.imp([bpath]); print('re-import backup:', t)
        check('already up to date' in t and 'Imported' not in t and 'Updated' not in t and 'Tags' not in t, 're-importing the backup: already up to date')
        t = await ph.imp([LIB_ZIP]); print('re-import library:', t)
        check(t == '6 already up to date', 're-importing the old test library: already up to date')
        print('JS errors:', ph.errors or 'none')
        check(not ph.errors, 'no JavaScript errors')
    os.remove(bpath)
    await upgrade_test(app, fails)
    print('\n' + ('ALL PASSED' if not fails else f'{len(fails)} FAILED: ' + '; '.join(fails)))
    return not fails


async def upgrade_test(app, fails):
    """Updating from an older version: the cards open even while the older version is still open in another tab
    (v23 opened to a black screen then), and a My Files index saved by v23 is carried over."""
    tmp = tempfile.mkdtemp()
    def ok(cond, what):
        print(('ok   ' if cond else 'FAIL ') + what)
        if not cond: fails.append(what)
    async def start(ph, html):
        open(os.path.join(tmp, 'index.html'), 'w').write(html)
        p = await ph.ctx.new_page(); errs = []
        p.on('pageerror', lambda e: errs.append(str(e)))
        await p.goto(ph.base); await p.wait_for_timeout(1500)
        return p, errs
    try:
        git = lambda rev: subprocess.run(['git', '-C', app, 'show', f'{rev}:index.html'], capture_output=True, text=True).stdout
        v22, v23, new = git('e6e50da'), git('ef39d35'), open(os.path.join(app, 'index.html')).read()
        if not v22 or not v23:
            print('skip upgrade test: older versions not in this checkout'); return
        # v22 (database version 1) stays open, like a forgotten Chrome tab, while the new version starts
        open(os.path.join(tmp, 'index.html'), 'w').write(v22)
        async with Phone(tmp) as ph:
            await ph.imp([LIB_ZIP])
            p, errs = await start(ph, new)
            n = await p.evaluate("T.cards.length")
            ok(n == 6 and 'Your decks' in await p.inner_text('#home'), f'with an older Agora still open in another tab, the new one opens its cards ({n})')
            ok(not errs, 'no JavaScript errors after the update')
            ok(await p.evaluate("""() => new Promise(r => { const q = indexedDB.open('subtext'); q.onsuccess = () => { r(q.result.version); q.result.close(); }; })""") == 1, 'the cards\' database is left at its version')
        # a phone where v23 upgraded the database (version 2) and saved a My Files index there
        open(os.path.join(tmp, 'index.html'), 'w').write(v23)
        async with Phone(tmp) as ph:
            await ph.imp([LIB_ZIP])
            await ph.pg.evaluate("""() => new Promise(r => { const q = indexedDB.open('subtext'); q.onsuccess = () => { const db = q.result; const t = db.transaction(['files', 'meta'], 'readwrite');
              t.objectStore('files').put({ path: 'a.pdf', kind: 'file', name: 'a.pdf', dir: '', size: 10, mtime: 1, ext: 'pdf', tags: ['Home'], tagsAt: 5 });
              t.objectStore('meta').put({ k: 'fileTagsPending', v: [{ path: 'gone.jpg', name: 'gone.jpg', size: 3, mtime: 2, tags: ['Goa'], at: 4 }] });
              t.oncomplete = () => { db.close(); r(); }; }; })""")
            await ph.pg.close()
            p, errs = await start(ph, new)
            n = await p.evaluate("T.cards.length")
            ok(n == 6 and await p.evaluate("(T.fidx.get('a.pdf') || {}).tags?.join()") == 'Home' and await p.evaluate("T.FX.pending.length") == 1,
               'a database upgraded by v23 still opens, and its My Files index and tags are carried over')
            ok(not errs, 'no JavaScript errors after the v23 update')
    finally:
        shutil.rmtree(tmp)


if __name__ == '__main__':
    a = argparse.ArgumentParser(); a.add_argument('app_dir'); a.add_argument('--out', default='shots/files')
    o = a.parse_args()
    sys.exit(0 if asyncio.run(main(os.path.abspath(o.app_dir), o.out)) else 1)
