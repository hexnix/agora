"""Moving the Agora folder to one folder per deck (v35): cards saved by v32–v34 in a folder each move over by themselves.

    python3 tools/app-test/test_folder_layout.py . --out shots/folder-layout/

Saves the test library in the new layout, rewrites it the way v32–v34 kept it (Cards/<deck>/<word>/card.json and pictures,
with the app's records to match), then reopens the app. Checks: every card moves to its deck's cards.json and Pictures folder,
the old card folders go, moving makes no Previous versions, nothing on the phone changes, a fresh phone brings cards back
from a folder still in the old layout (and moves it over), and no JavaScript errors. Everything here is made up.
"""
import argparse, asyncio, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import Phone
from test_folder import IDLE, LIST, DUMP, LOAD, READ

KIT = os.path.dirname(os.path.abspath(__file__))
fails = []


def check(ok, what):
    print(('ok   ' if ok else 'FAIL ') + what)
    if not ok: fails.append(what)


# rewrite the folder and the app's records the way v32–v34 kept cards: a folder each
TO_OLD = """async () => {
  const root = await (await navigator.storage.getDirectory()).getDirectoryHandle('Agora');
  const dirOf = async (path, create) => { let d = root; for (const p of path.split('/').filter(Boolean)) d = await d.getDirectoryHandle(p, {create}); return d; };
  const db = await new Promise((ok, no) => { const r = indexedDB.open('agora-sync'); r.onsuccess = () => ok(r.result); r.onerror = no; });
  const all = await new Promise(ok => { const r = db.transaction('paths').objectStore('paths').getAll(); r.onsuccess = () => ok(r.result); });
  const out = [];
  for (const rec of all.filter(r => r.flat)) {
    const deck = await dirOf(rec.base), pics = await deck.getDirectoryHandle('Pictures');
    const cj = JSON.parse(await (await (await deck.getFileHandle('cards.json')).getFile()).text());
    const e = cj.cards.find(x => 'card:' + x.card.id === rec.k), name = rec.dir.split('/').pop();
    const cdir = await deck.getDirectoryHandle(name, {create: true}), files = {};
    for (const [n, bid] of Object.entries(rec.files)) {
      const f = await (await pics.getFileHandle(n)).getFile(), nn = n.slice(name.length + 1);
      const w = await (await cdir.getFileHandle(nn, {create: true})).createWritable(); await w.write(f); await w.close(); files[nn] = bid;
    }
    const w = await (await cdir.getFileHandle('card.json', {create: true})).createWritable();
    await w.write(JSON.stringify({app: 'agora', kind: 'card', version: 1, card: e.card, files}, null, 1)); await w.close();
    out.push({k: rec.k, dir: rec.base + '/' + name, base: rec.base, nm: rec.nm, label: rec.label, files, sum: ''});
  }
  for (const base of new Set(all.filter(r => r.flat).map(r => r.base))) { const d = await dirOf(base); await d.removeEntry('cards.json'); await d.removeEntry('Pictures', {recursive: true}); }
  await new Promise(ok => { const t = db.transaction('paths', 'readwrite'); out.forEach(r => t.objectStore('paths').put(r)); t.oncomplete = ok; });
  db.close(); return out.length;
}"""
DIRS = """async () => { const out = []; const walk = async (d, p) => { for await (const [n, h] of d.entries()) if (h.kind === 'directory') { out.push(p + n); await walk(h, p + n + '/'); } };
  await walk(await (await navigator.storage.getDirectory()).getDirectoryHandle('Agora'), ''); return out.filter(d => d.startsWith('Cards/')).sort(); }"""
NEW_DIRS = ['Cards/Example Reading', 'Cards/Example Reading/Pictures', 'Cards/Example Show', 'Cards/Example Show/Pictures']
CONNECT = "async () => { window.showDirectoryPicker = async () => navigator.storage.getDirectory(); await T.connectFiles(true); }"


async def main(app, out):
    os.makedirs(out, exist_ok=True)
    async with Phone(app) as ph:
        pg = ph.pg
        await ph.imp([os.path.join(KIT, 'fixtures', 'test-library.zip')])
        await pg.evaluate(CONNECT)
        check(await pg.evaluate(IDLE), 'first copy finished')
        n = await pg.evaluate(TO_OLD)
        old_dirs = await pg.evaluate(DIRS)
        check(n == 6 and 'Cards/Example Show/candor' in old_dirs and 'Cards/Example Show/Pictures' not in old_dirs, f'the folder is laid out as v34 kept it: {old_dirs}')
        dump = await pg.evaluate(DUMP)
        before = await pg.evaluate("JSON.stringify(T.cards.map(c => [c.id, c.tags, c.defIds]).sort())")

        # the app reopens: cards saved a folder each move over
        await pg.reload(); await pg.wait_for_timeout(300)
        await pg.evaluate(CONNECT)
        check(await pg.evaluate(IDLE), 'moving finished')
        dirs = await pg.evaluate(DIRS)
        check(dirs == NEW_DIRS, f'one folder per deck, the old card folders gone: {dirs}')
        files = await pg.evaluate(LIST)
        check(not any(k.startswith('Agora/Previous versions') for k in files), 'moving makes no previous versions')
        ids = []
        for d in ('Example Show', 'Example Reading'): ids += [e['card']['id'] for e in json.loads(await pg.evaluate(READ, f'Cards/{d}/cards.json'))['cards']]
        check(len(ids) == 6, f'every card is in its deck\'s cards.json: {ids}')
        check('Agora/Cards/Example Show/Pictures/brusque definition 2.jpg' in files, 'pictures moved into Pictures')
        check(await pg.evaluate("JSON.stringify(T.cards.map(c => [c.id, c.tags, c.defIds]).sort())") == before, 'nothing on the phone changed')
        check(await pg.evaluate("[...T.AG.map.values()].filter(r => r.k.startsWith('card:')).every(r => r.flat)"), 'every card\'s record is in the new layout')

        # in the new layout: a renamed card, a card moved to the other deck, a renamed deck
        await pg.evaluate("""() => { const c = T.cards.find(x => x.id === 'test-candor'); c.word = 'frankness'; c.named = true;
          const r = T.cards.find(x => x.id === 'test-reticent'); r.deckId = T.decks.find(d => d.name === 'Example Reading').id; return T.saveCards([c, r]); }""")
        check(await pg.evaluate(IDLE), 'saving the rename and move finished')
        files = await pg.evaluate(LIST)
        check('Agora/Cards/Example Show/Pictures/frankness scene.jpg' in files and not any('Pictures/candor' in k and not k.startswith('Agora/Previous') for k in files), 'a renamed card\'s pictures take its new name')
        check('Agora/Cards/Example Reading/Pictures/reticent scene.jpg' in files and 'Agora/Cards/Example Show/Pictures/reticent scene.jpg' not in files, 'a moved card\'s pictures move with it')
        show = await pg.evaluate(READ, 'Cards/Example Show/cards.json'); reading = await pg.evaluate(READ, 'Cards/Example Reading/cards.json')
        check('test-reticent' not in show and 'test-reticent' in reading and 'frankness' in show, 'cards.json follows')
        ch = await pg.evaluate("async () => (await T.agVersions()).map(x => [x.k, x.what])")
        check(['card:test-candor', 'renamed from “candor”'] in ch and ['card:test-reticent', 'moved to another deck'] in ch, f'both are in the list of changes: {ch}')
        await pg.evaluate("() => { const d = T.decks.find(x => x.name === 'Example Show'); d.name = 'Example Series'; return T.store.put('decks', [d]); }")
        check(await pg.evaluate(IDLE), 'saving the renamed deck finished')
        dirs = await pg.evaluate(DIRS)
        check(dirs == ['Cards/Example Reading', 'Cards/Example Reading/Pictures', 'Cards/Example Series', 'Cards/Example Series/Pictures'], f'a renamed deck\'s folder takes its new name: {dirs}')
        files = await pg.evaluate(LIST)
        check('Agora/Cards/Example Series/Pictures/brusque definition 2.jpg' in files and 'test-brusque' in await pg.evaluate(READ, 'Cards/Example Series/cards.json'), 'with its cards and pictures')
        # restore the renamed card from the list of changes
        x = await pg.evaluate("async () => { const x = (await T.agVersions()).find(x => x.k === 'card:test-candor'); return await T.agRestore(x); }")
        check(x and await pg.evaluate("T.nameOf(T.cards.find(c => c.id === 'test-candor'))") == 'candor', 'restoring brings back the old name')
        errs_a = list(ph.errors)

    # a fresh phone with a folder still in the old layout
    async with Phone(app) as ph:
        pg = ph.pg
        await pg.evaluate(LOAD, dump)
        await pg.evaluate(CONNECT)
        check(await pg.evaluate(IDLE), 'reading and moving finished')
        check(await pg.evaluate("T.cards.length") == 6, 'a fresh phone brings back every card from the old layout')
        check(await pg.evaluate(DIRS) == NEW_DIRS, 'and moves the folder over')
        await ph.open_card('test-brusque'); await ph.swipe(-300); await ph.swipe(-300)
        await ph.shot(f'{out}/fresh-phone-definition-2.png')
        check(await ph.level() == 2, 'the second definition opens')
        errs_b = list(ph.errors)
    errs = [e for e in errs_a + errs_b if 'favicon' not in e]
    check(not errs, f'no JavaScript errors: {errs}')
    print('\n' + ('ALL OK' if not fails else f'{len(fails)} FAILED: {fails}'))
    return not fails


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('app'); ap.add_argument('--out', default='shots/folder-layout')
    a = ap.parse_args()
    sys.exit(0 if asyncio.run(main(a.app, a.out)) else 1)
