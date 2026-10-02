"""The Agora folder (v32): everything Agora holds is also kept as files in My Files › Agora, with previous versions.

    python3 tools/app-test/test_folder.py . --out shots/folder/

A made-up folder in the origin private file system stands in for the phone's My Files (as in test_files.py).
Checks: the home line before the folder is chosen; the first copy (cards, pictures, magazine PDF, a note and its picture,
a bookmark, study progress, history, Read me); Agora's folder staying out of the My Files list; a changed card keeping its
earlier copy in Previous versions; a deleted card restored; a renamed note; a bookmark's own previous versions; both views
of the Previous versions page and an item's own list; the "changes waiting" line when the folder isn't allowed; a fresh
phone bringing everything back from the folder alone; re-importing the test library reporting "already up to date"; Back;
and JavaScript errors. Everything here is made up.
"""
import argparse, asyncio, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import Phone

KIT = os.path.dirname(os.path.abspath(__file__))
LIB_ZIP = os.path.join(KIT, 'fixtures', 'test-library.zip')
fails = []


def check(ok, what):
    print(('ok   ' if ok else 'FAIL ') + what)
    if not ok: fails.append(what)


CONNECT = """async () => {
  const root = await navigator.storage.getDirectory();
  if (!(await root.getDirectoryHandle('Documents', {create: true}).then(() => true))) return;
  const d = await root.getDirectoryHandle('Documents', {create: true});
  const w = await (await d.getFileHandle('letter.txt', {create: true})).createWritable(); await w.write('Dear bank'); await w.close();
  window.showDirectoryPicker = async () => root; await T.connectFiles(true);
}"""
IDLE = """async () => { for (let i = 0; i < 600; i++) { await new Promise(r => setTimeout(r, 100));
  if (!T.AG.linking && !T.AG.run) { await T.agFlush(); if (!T.AG.run && !T.AG.dirty.size) return true; } } return false; }"""
LIST = """async () => { const out = {}; const root = await navigator.storage.getDirectory();
  const walk = async (d, p) => { for await (const [n, h] of d.entries()) { const q = p ? p + '/' + n : n;
    if (h.kind === 'directory') await walk(h, q); else { const f = await h.getFile(); out[q] = f.size; } } };
  await walk(root, ''); return out; }"""
DUMP = """async () => { const out = {}; const root = await navigator.storage.getDirectory();
  const walk = async (d, p) => { for await (const [n, h] of d.entries()) { const q = p ? p + '/' + n : n;
    if (h.kind === 'directory') await walk(h, q); else { const b = new Uint8Array(await (await h.getFile()).arrayBuffer());
      let s = ''; for (let i = 0; i < b.length; i += 0x8000) s += String.fromCharCode(...b.subarray(i, i + 0x8000)); out[q] = btoa(s); } } };
  await walk(root, ''); return out; }"""
LOAD = """async files => { const root = await navigator.storage.getDirectory();
  for (const [path, data] of Object.entries(files)) { const parts = path.split('/'); let d = root;
    for (const p of parts.slice(0, -1)) d = await d.getDirectoryHandle(p, {create: true});
    const w = await (await d.getFileHandle(parts.at(-1), {create: true})).createWritable();
    await w.write(Uint8Array.from(atob(data), c => c.charCodeAt(0))); await w.close(); } }"""
PIC = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAQAAAAECAYAAACp8Z5+AAAAFklEQVQImWNkYPj/n4GBgYGJAQoQAwA7LgQEcG9JmAAAAABJRU5ErkJggg=='


async def main(app, out):
    os.makedirs(out, exist_ok=True)
    async with Phone(app) as ph:
        pg = ph.pg
        print(await ph.imp([LIB_ZIP]))
        # a note with a picture, a bookmark, a study answer and a visit, all made up
        await pg.evaluate("""async pic => {
          const blob = await (await fetch(pic)).blob();
          await T.nstore.put('images', [{id: 'ni-test1', blob}, {id: 'ni-test1-t', blob}]);
          const n = {id: 'n-test1', title: 'Weekend plan', html: '<p>Buy <b>bread</b></p><p><img data-img="ni-test1" alt=""></p>', imgs: ['ni-test1'], createdAt: Date.now() - 5000, updatedAt: Date.now() - 5000};
          T.NT.notes.set(n.id, n); await T.nstore.put('notes', [n]);
          await T.saveRecs([{id: 'test-candor', step: 1, due: T.dayNo() + 3, first: T.dayNo(), last: T.dayNo(), at: Date.now()}]);
          await T.saveMarks([{id: 'bm-test1', url: 'https://example.com/a', title: 'An example page', site: 'example.com', tags: ['Reading'], addedAt: Date.now(), at: Date.now()}]);
        }""", PIC)
        await ph.open_card('test-candor'); await ph.back()
        await pg.wait_for_timeout(500)
        line = await pg.inner_text('#home .agslot')
        check('Keep everything in My Files' in line, f'home line before the folder is chosen: {line!r}')
        await ph.shot(f'{out}/1-home-before.png')

        # choose My Files: everything is copied into Agora/
        await pg.evaluate(CONNECT)
        check(await pg.evaluate(IDLE), 'first copy finished')
        files = await pg.evaluate(LIST)
        want = ['Agora/Read me.txt', 'Agora/Cards/Example Show/candor/card.json', 'Agora/Cards/Example Show/candor/scene.jpg',
                'Agora/Cards/Example Show/candor/tile.jpg', 'Agora/Cards/Example Show/brusque/definition 2.jpg', 'Agora/Cards/Example Show/deck.json',
                'Agora/Cards/Example Reading/heuristic/source.jpg', 'Agora/Notes/Weekend plan.html', 'Agora/Notes/pictures/ni-test1.jpg',
                'Agora/Bookmarks.json', 'Agora/Study progress.json', 'Agora/History.json']
        for w in want: check(w in files, f'folder has {w}')
        check(any(p.startswith('Agora/Magazines/') and p.endswith('.pdf') for p in files), 'folder has the magazine PDF')
        check(not any(k.startswith('Previous versions') for k in files), 'no previous versions after the first copy')
        await pg.wait_for_timeout(800)
        idx = await pg.evaluate("[...T.fidx.keys()]")
        check('Documents/letter.txt' in idx and not any(p.startswith('Agora') for p in idx), f'My Files lists the owner\'s files only: {idx}')
        line = await pg.inner_text('#home .agslot')
        check(line.strip() == '', f'home line gone once saved: {line!r}')
        await ph.shot(f'{out}/2-home-saved.png')
        note_html = await pg.evaluate("async () => (await (await (await (await (await (await navigator.storage.getDirectory()).getDirectoryHandle('Agora')).getDirectoryHandle('Notes')).getFileHandle('Weekend plan.html')).getFile()).text())")
        check('<b>bread</b>' in note_html and 'src="pictures/ni-test1.jpg"' in note_html, 'the note is a readable page with its picture')

        # nothing changed: flushing again writes nothing new
        await pg.evaluate("T.AG.dirty.clear(); ['card:test-candor','study','marks'].forEach(k => T.AG.dirty.set(k, Date.now()))")
        await pg.evaluate(IDLE)
        files2 = await pg.evaluate(LIST)
        check(not any(k.startswith('Agora/Previous versions') for k in files2), 'an unchanged item makes no previous version')

        # change a card's tags: the earlier card.json is kept
        await pg.evaluate("() => { const c = T.cards.find(x => x.id === 'test-candor'); c.tags = [...c.tags, 'Favourite']; return T.saveCards([c]); }")
        await pg.evaluate(IDLE)
        files = await pg.evaluate(LIST)
        vers = [k for k in files if k.startswith('Agora/Previous versions/') and k.endswith('candor/card.json')]
        check(len(vers) == 1, f'the earlier card.json is in Previous versions: {vers}')
        ch = await pg.evaluate("async () => (await T.agVersions()).map(x => [x.k, x.what])")
        check(['card:test-candor', 'tags changed'] in ch, f'changes.json says tags changed: {ch}')

        # delete a card, then restore it from Previous versions
        await pg.evaluate("T.deleteCards([T.cards.find(x => x.id === 'test-brusque')])")
        await pg.evaluate(IDLE)
        files = await pg.evaluate(LIST)
        check(not any('Example Show/brusque/' in k and not k.startswith('Agora/Previous') for k in files), 'a deleted card\'s folder goes')
        check(any(k.startswith('Agora/Previous versions/') and k.endswith('brusque/definition 2.jpg') for k in files), 'its files are kept in Previous versions')

        # rename the note, edit the bookmark
        await pg.evaluate("""() => { const n = T.NT.notes.get('n-test1'); n.title = 'Saturday plan'; n.updatedAt = Date.now(); return T.nstore.put('notes', [n]); }""")
        await pg.evaluate("() => T.saveMarks([{...T.BM.recs.get('bm-test1'), title: 'A renamed page', at: Date.now()}])")
        await pg.evaluate(IDLE)
        files = await pg.evaluate(LIST)
        check('Agora/Notes/Saturday plan.html' in files and 'Agora/Notes/Weekend plan.html' not in files, 'a renamed note gets its new file name')
        check(any(k.startswith('Agora/Previous versions/') and k.endswith('Notes/Weekend plan.html') for k in files), 'the old note page is kept')

        # the Previous versions page, both views
        await pg.evaluate("localStorage.removeItem('agora.versions.view')")
        await pg.evaluate("T.openVersions()"); await pg.wait_for_timeout(1500)
        txt = await pg.inner_text('.page:last-of-type')
        check('brusque' in txt and 'deleted' in txt and 'tags changed' in txt, 'each-item view lists the changes')
        await ph.shot(f'{out}/3-versions-items.png')
        await pg.click('.page:last-of-type [data-p="vview"]'); await pg.wait_for_timeout(500)
        txt = await pg.inner_text('.page:last-of-type')
        check('Restore' in txt and 'moment' in txt, f'by-moment view: {txt[:200]!r}')
        await ph.shot(f'{out}/4-versions-moments.png')
        await pg.click('.page:last-of-type [data-p="vview"]'); await pg.wait_for_timeout(400)
        # restore brusque from its row
        rows = await pg.evaluate("[...document.querySelectorAll('.page:last-of-type .hrow')].map(b => b.innerText)")
        i = next(i for i, r in enumerate(rows) if 'brusque' in r)
        await pg.click(f'.page:last-of-type .hrow[data-ver="{i}"]'); await pg.wait_for_timeout(500)
        await ph.shot(f'{out}/5-restore-sheet.png')
        await pg.click('#sheet [data-act="yes"]'); await pg.wait_for_timeout(1800)
        c = await pg.evaluate("(() => { const c = T.cards.find(x => x.id === 'test-brusque'); return c && c.defIds.length; })()")
        check(c == 2, 'the deleted card is back with both definitions')
        await ph.back(); await pg.wait_for_timeout(400)
        check(await pg.evaluate("T.pages.length") == 0, 'Back closes Previous versions')
        await pg.evaluate(IDLE)
        files = await pg.evaluate(LIST)
        check('Agora/Cards/Example Show/brusque/card.json' in files, 'the restored card is written back to the folder')

        # an item's own previous versions: a card from the study view, a bookmark
        await ph.open_card('test-candor')
        await pg.click('.study [data-s="edit"]'); await pg.wait_for_timeout(400)
        await pg.click('#sheet [data-act="vers"]'); await pg.wait_for_timeout(1500)
        txt = await pg.inner_text('#sheet')
        check('Tags changed' in txt, f'the card\'s own previous versions: {txt!r}')
        await ph.shot(f'{out}/6-card-versions.png')
        await pg.click('#sheet [data-act="v0"]'); await pg.wait_for_timeout(400)
        await pg.click('#sheet [data-act="yes"]'); await pg.wait_for_timeout(1500)
        tags = await pg.evaluate("T.cards.find(x => x.id === 'test-candor').tags")
        check('Favourite' not in tags, f'restoring the card brings back its old tags: {tags}')
        await ph.back(); await pg.wait_for_timeout(300)
        await pg.evaluate("T.itemVersions('marks', 'A renamed page', 'bm-test1')"); await pg.wait_for_timeout(1500)
        txt = await pg.inner_text('#sheet')
        check('An example page' in txt, f'the bookmark\'s own previous versions: {txt!r}')
        await pg.click('#sheet [data-act="v0"]'); await pg.wait_for_timeout(400)
        await pg.click('#sheet [data-act="yes"]'); await pg.wait_for_timeout(1200)
        check(await pg.evaluate("T.BM.recs.get('bm-test1').title") == 'An example page', 'the bookmark is restored')
        await pg.evaluate(IDLE)

        # the folder not allowed (Android after a reopen): changes wait, with one line on home
        await pg.evaluate("T.FX.ready = false")
        await pg.evaluate("() => { const c = T.cards.find(x => x.id === 'test-reticent'); c.tags = [...c.tags, 'Later']; return T.saveCards([c]); }")
        await pg.wait_for_timeout(300)
        await pg.evaluate("document.querySelector('#home .agslot').innerHTML = ''; T.agFlush()"); await pg.wait_for_timeout(300)
        line = await pg.inner_text('#home .agslot')
        check('Save to My Files' in line and '1 change waiting' in line, f'changes waiting line: {line!r}')
        await ph.shot(f'{out}/7-home-waiting.png')
        await pg.click('#home [data-ag]'); await pg.evaluate(IDLE)
        rj = await pg.evaluate("async () => JSON.parse(await (await (await (await (await (await (await (await navigator.storage.getDirectory()).getDirectoryHandle('Agora')).getDirectoryHandle('Cards')).getDirectoryHandle('Example Show')).getDirectoryHandle('reticent')).getFileHandle('card.json')).getFile()).text()).card.tags")
        check('Later' in rj, 'one tap saves what waited')
        state = await pg.evaluate("({cards: T.cards.length, notes: T.NT.notes.size, marks: T.BM.recs.size, study: T.SD.recs.size, hist: T.HI.recs.size})")
        dump = await pg.evaluate(DUMP)
        print('phone A', state, len(dump), 'files')
        errs_a = list(ph.errors)

    # a fresh phone: only the folder
    async with Phone(app) as ph:
        pg = ph.pg
        await pg.evaluate(LOAD, {k: v for k, v in dump.items()})
        await pg.wait_for_timeout(500)
        check(await pg.evaluate("T.cards.length") == 0, 'the new phone starts empty')
        await pg.evaluate("async () => { window.showDirectoryPicker = async () => navigator.storage.getDirectory(); await T.connectFiles(true); }")
        check(await pg.evaluate(IDLE), 'reading the folder finished')
        await pg.wait_for_timeout(800)
        st2 = await pg.evaluate("({cards: T.cards.length, notes: T.NT.notes.size, marks: T.BM.recs.size, study: T.SD.recs.size, hist: T.HI.recs.size})")
        check(st2 == state and state['study'] == 1, f'the new phone has everything: {st2} vs {state}')
        files_b = await pg.evaluate(LIST)
        new = [k for k in files_b if k.startswith('Agora/Previous versions') and k not in dump]
        check(not new, f'bringing everything back changes nothing in the folder: {new}')
        await ph.shot(f'{out}/8-new-phone-home.png')
        await ph.open_card('test-heuristic'); await ph.swipe(-300); await ph.shot(f'{out}/9-new-phone-meaning.png'); await ph.back(); await ph.back()
        await pg.evaluate("T.openNote('n-test1')"); await pg.wait_for_timeout(1200)
        check('bread' in await pg.inner_text('.page:last-of-type'), 'the note came back')
        await ph.shot(f'{out}/10-new-phone-note.png'); await ph.back()
        t = await ph.imp([LIB_ZIP])
        check('up to date' in t, f're-import: {t!r}')
        errs_b = list(ph.errors)
    errs = [e for e in errs_a + errs_b if 'favicon' not in e]
    check(not errs, f'no JavaScript errors: {errs}')
    print('\n' + ('ALL OK' if not fails else f'{len(fails)} FAILED: {fails}'))
    return not fails


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('app'); ap.add_argument('--out', default='shots/folder')
    a = ap.parse_args()
    sys.exit(0 if asyncio.run(main(a.app, a.out)) else 1)
