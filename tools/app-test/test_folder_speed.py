"""The first copy into My Files › Agora (v34): fast even when each folder step is slow, as on Android.

    python3 tools/app-test/test_folder_speed.py . --out shots/folder-speed/

Adds 60 made-up copies of the test cards, half of them sharing a name, slows every folder operation by 40 ms
(Android's folder access takes about that long per step), then connects a made-up My Files and times the copy.
Checks: everything is copied, each card has its own folder, same-named cards get "candor 2" and so on, it runs
far faster than one card at a time did (46 cards a minute in v33), and no JavaScript errors.
"""
import argparse, asyncio, os, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import Phone

KIT = os.path.dirname(os.path.abspath(__file__))
fails = []


def check(ok, what):
    print(('ok   ' if ok else 'FAIL ') + what)
    if not ok: fails.append(what)


async def main(app, out):
    os.makedirs(out, exist_ok=True)
    async with Phone(app) as ph:
        pg = ph.pg
        await ph.imp([os.path.join(KIT, 'fixtures', 'test-library.zip')])
        await pg.evaluate("""async () => { const src = T.cards.filter(c => !c.pdf); const out = [];
          for (let i = 0; i < 60; i++) { const c = src[i % src.length]; out.push({...c, id: c.id + '-copy' + i, word: i % 2 ? c.word : c.word + ' ' + i, named: true}); }
          T.cards.push(...out); await T.saveCards(out); }""")
        await pg.evaluate("""ms => { const slow = (P, m) => { const f = P[m]; P[m] = async function (...a) { await new Promise(r => setTimeout(r, ms)); return f.apply(this, a); }; };
          slow(FileSystemDirectoryHandle.prototype, 'getDirectoryHandle'); slow(FileSystemDirectoryHandle.prototype, 'getFileHandle');
          slow(FileSystemDirectoryHandle.prototype, 'removeEntry'); slow(FileSystemFileHandle.prototype, 'createWritable');
          slow(FileSystemFileHandle.prototype, 'getFile'); slow(FileSystemWritableFileStream.prototype, 'close'); }""", 40)
        t = time.time()
        await pg.evaluate("async () => { const root = await navigator.storage.getDirectory(); window.showDirectoryPicker = async () => root; await T.connectFiles(true); }")
        done = await pg.evaluate("""async () => { for (let i = 0; i < 3000; i++) { await new Promise(r => setTimeout(r, 100));
          if (!T.AG.linking && !T.AG.run && !T.AG.dirty.size) return true; } return false; }""")
        dt = time.time() - t
        check(done, 'the first copy finished')
        dirs = await pg.evaluate("""async () => { const out = {}; const walk = async (d, p) => { for await (const [n, h] of d.entries()) {
            if (h.kind === 'directory') await walk(h, p + n + '/'); else out[p + n] = 1; } };
          await walk(await (await navigator.storage.getDirectory()).getDirectoryHandle('Agora'), ''); return Object.keys(out); }""")
        cardDirs = {p.rsplit('/', 1)[0] for p in dirs if p.endswith('/card.json')}
        n = await pg.evaluate("T.cards.length")
        check(len(cardDirs) == n, f'each of the {n} cards has its own folder: {len(cardDirs)}')
        check(any(d.endswith('/candor 2') for d in cardDirs), 'a card sharing a name gets "candor 2"')
        per_min = n / dt * 60
        check(per_min > 300, f'{per_min:.0f} cards a minute with slow folder steps (one at a time managed 46)')
        await ph.shot(f'{out}/home.png')
        errs = [e for e in ph.errors if 'favicon' not in e]
        check(not errs, f'no JavaScript errors: {errs}')
    print('\n' + ('ALL OK' if not fails else f'{len(fails)} FAILED: {fails}'))
    return not fails


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('app'); ap.add_argument('--out', default='shots/folder-speed')
    a = ap.parse_args()
    sys.exit(0 if asyncio.run(main(a.app, a.out)) else 1)
