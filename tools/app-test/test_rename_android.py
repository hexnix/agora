"""Renaming and tagging in My Files the way Android behaves (v40).

    python3 tools/app-test/test_rename_android.py . --out shots/rename-android/

On the phone a file in My Files has no real move: Chrome copies it, and copying a film of a few GB fails part-way, leaving
an empty file under the new name. v32–v39 then left one more empty file on every try ("Oppenheimer.mkv",
"Oppenheimer 2.mkv"…). This test makes the made-up folder behave like that (move() creates the new name empty and fails;
writing more than a few bytes fails for the "big" file) and checks:
  - a failed rename leaves no empty file, the film keeps its name, and a clear message says why;
  - a name typed without its ending keeps the file's own (".mkv");
  - a second tap while renaming doesn't start a second rename;
  - a small file still renames (copied, then the old one removed);
  - typing a new tag and tapping Done adds it;
  - empty files left by older versions are removed once, kept in Previous versions, and text files are left alone.
Everything here is made up.
"""
import argparse, asyncio, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import Phone

fails = []


def check(ok, what):
    print(('ok   ' if ok else 'FAIL ') + what)
    if not ok: fails.append(what)


# "9137.mkv" stands in for a film (its size is faked as 3 GB); the empty ones are what v39 left behind
TREE = {'9137.mkv': 'FILM' * 64, 'scan.pdf': '%PDF-1.4 made up', 'Oppenheimer.mkv': '', 'Oppenheimer 2.mkv': '',
        'Oppenheimer 4': '', 'Docs/empty note.txt': '', 'Docs/letter.txt': 'Dear bank'}
SETUP = """async tree => {
  const root = await navigator.storage.getDirectory();
  for (const [path, data] of Object.entries(tree)) { const parts = path.split('/'); let d = root;
    for (const p of parts.slice(0, -1)) d = await d.getDirectoryHandle(p, {create: true});
    const w = await (await d.getFileHandle(parts.at(-1), {create: true})).createWritable(); await w.write(data); await w.close(); }
  // Android: move() is a copy that fails for a big file after making the new name (empty)
  const fakeMove = async function (a, b) {
    const parent = typeof a === 'string' ? null : a, name = typeof a === 'string' ? a : b;
    const dir = parent || root; await dir.getFileHandle(name, {create: true});
    throw new DOMException('move is a copy here', 'InvalidModificationError');
  };
  for (const P of [FileSystemHandle.prototype, FileSystemFileHandle.prototype, FileSystemDirectoryHandle.prototype]) P.move = fakeMove;
  // and a big film can't be written through Chrome's cache
  const getFile = FileSystemFileHandle.prototype.getFile;
  FileSystemFileHandle.prototype.getFile = async function () {
    const f = await getFile.call(this);
    if (this.name === '9137.mkv') Object.defineProperty(f, 'size', {value: 3e9});
    return f;
  };
  window.__writes = 0;
  window.showDirectoryPicker = async () => root; await T.connectFiles(true); await T.rescan();
}"""
LIST = """async () => { const out = {}; const root = await navigator.storage.getDirectory();
  const walk = async (d, p) => { for await (const [n, h] of d.entries()) { const q = p ? p + '/' + n : n;
    if (h.kind === 'directory') { if (n !== 'Agora') await walk(h, q); } else out[q] = (await h.getFile()).size; } };
  await walk(root, ''); return out; }"""
top = '.page:last-of-type'


async def rename(ph, path, typed, enter_twice=False):
    pg = ph.pg
    await ph.hold(f'{top} [data-fp="{path}"]'); await pg.click(f'{top} [data-p="selmenu"]'); await pg.wait_for_timeout(400)
    await pg.click('#sheet [data-act="ren"]'); await pg.wait_for_timeout(800)
    await pg.fill('#askIn', typed)
    await pg.press('#askIn', 'Enter')
    if enter_twice: await pg.click('#sheet button[type=submit]', timeout=1000, force=True, no_wait_after=True)
    await pg.wait_for_timeout(1500)


async def main(app, out):
    os.makedirs(out, exist_ok=True)
    async with Phone(app) as ph:
        pg = ph.pg
        toasts = []
        await pg.expose_function('__toast', lambda t: toasts.append(t))
        await pg.evaluate("""new MutationObserver(() => { const t = document.querySelector('#toast'); if (t && t.textContent && t.textContent !== window.__last) { window.__last = t.textContent; __toast(t.textContent); } })
          .observe(document.body, {subtree: true, childList: true, characterData: true})""")
        await pg.evaluate(SETUP, TREE); await pg.wait_for_timeout(3000)

        # older versions' leftovers go, once; an empty text file stays
        fs = await pg.evaluate(LIST)
        check('Oppenheimer.mkv' not in fs and 'Oppenheimer 2.mkv' not in fs and 'Oppenheimer 4' not in fs, f'empty leftovers removed: {sorted(fs)}')
        check('Docs/empty note.txt' in fs and '9137.mkv' in fs and 'scan.pdf' in fs, 'real files and an empty text file are left alone')
        check(any('empty file' in t for t in toasts), f'a message says so: {toasts[-1:] }')
        kept = await pg.evaluate("""async () => { const root = await navigator.storage.getDirectory(); const out = [];
          const walk = async (d, p) => { for await (const [n, h] of d.entries()) { const q = p ? p + '/' + n : n; if (h.kind === 'directory') await walk(h, q); else out.push(q); } };
          try { await walk(await root.getDirectoryHandle('Agora'), ''); } catch {} return out; }""")
        check(any(k.endswith('My Files/Oppenheimer.mkv') for k in kept), 'each one is kept in Previous versions')
        await pg.evaluate("T.rescan()"); await pg.wait_for_timeout(1500)
        n = sum('empty file' in t for t in toasts)
        await pg.evaluate("T.openFolder('')"); await pg.wait_for_timeout(800)
        await ph.shot(f'{out}/1-after-cleanup.png')

        # the film: the rename fails cleanly, once, and says why
        await rename(ph, '9137.mkv', 'Oppenheimer', enter_twice=True)
        fs = await pg.evaluate(LIST)
        check('9137.mkv' in fs, 'the film keeps its name when Android can\'t rename it')
        check(not any(k.startswith('Oppenheimer') for k in fs), f'no empty file left behind: {sorted(fs)}')
        check(any('Files app' in t for t in toasts), f'a clear message: {toasts[-1:]}')
        await ph.shot(f'{out}/2-film-rename.png')
        await pg.wait_for_timeout(3500)
        await ph.back(); await pg.wait_for_timeout(400)  # out of selecting

        # a small file still renames by copying, and the ending is kept when left off
        await rename(ph, 'scan.pdf', 'Passport')
        fs = await pg.evaluate(LIST)
        check('Passport.pdf' in fs and 'scan.pdf' not in fs and fs['Passport.pdf'] > 0, f'small file renamed, ending kept: {sorted(fs)}')
        check(await pg.evaluate("!!T.fidx.get('Passport.pdf')"), 'the list follows it')

        # tags: type a new one, tap Done
        await ph.hold(f'{top} [data-fp="Passport.pdf"]'); await pg.click(f'{top} [data-p="selmenu"]'); await pg.wait_for_timeout(400)
        await pg.click('#sheet [data-act="tag"]'); await pg.wait_for_timeout(600)
        await pg.fill('#ftagIn', 'Travel'); await ph.shot(f'{out}/3-tag-typed.png')
        await pg.click('#sheet [data-act="done"]'); await pg.wait_for_timeout(900)
        tags = await pg.evaluate("(T.fidx.get('Passport.pdf') || {}).tags")
        check(tags == ['Travel'], f'typing a tag and tapping Done adds it: {tags}')
        await pg.wait_for_timeout(1200)
        await ph.shot(f'{out}/4-tagged.png')
        await pg.evaluate("T.rescan()"); await pg.wait_for_timeout(1200)
        check(sum('empty file' in t for t in toasts) == n, 'the clean-up runs only once')
        check(not ph.errors, f'no JavaScript errors: {ph.errors}')
    print('\n' + ('ALL OK' if not fails else f'{len(fails)} FAILED'))
    return not fails


if __name__ == '__main__':
    a = argparse.ArgumentParser(); a.add_argument('app'); a.add_argument('--out', default='shots/rename-android')
    x = a.parse_args()
    sys.exit(0 if asyncio.run(main(x.app, x.out)) else 1)
