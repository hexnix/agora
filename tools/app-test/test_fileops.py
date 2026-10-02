"""Changing files in My Files (v32): move, rename, edit text, new folder, delete, each one restorable.

    python3 tools/app-test/test_fileops.py . --out shots/fileops/

A made-up folder in the origin private file system stands in for the phone's My Files (as in test_files.py).
Checks: Move and Delete beside ⋯ while selecting (pick A2); moving on folder pages with "Move here" (pick B2), keeping tags;
renaming (only the name is selected, so the extension stays); editing a text file; a new folder; deleting into Previous
versions; bringing back a deleted, an edited and a moved file; Back; and JavaScript errors. Everything here is made up.
"""
import argparse, asyncio, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import Phone

fails = []


def check(ok, what):
    print(('ok   ' if ok else 'FAIL ') + what)
    if not ok: fails.append(what)


TREE = {'Documents/notes.txt': 'Passport renewal: book in May.', 'Documents/receipt.txt': 'Receipt 42',
        'Documents/letter.txt': 'Dear bank', 'Documents/Bank/statement.txt': 'March', 'Work/plan.txt': 'Q4 plan'}
SETUP = """async tree => {
  const root = await navigator.storage.getDirectory();
  for (const [path, data] of Object.entries(tree)) { const parts = path.split('/'); let d = root;
    for (const p of parts.slice(0, -1)) d = await d.getDirectoryHandle(p, {create: true});
    const w = await (await d.getFileHandle(parts.at(-1), {create: true})).createWritable(); await w.write(data); await w.close(); }
  window.showDirectoryPicker = async () => root; await T.connectFiles(true); await T.rescan();
}"""
LIST = """async () => { const out = {}; const root = await navigator.storage.getDirectory();
  const walk = async (d, p) => { for await (const [n, h] of d.entries()) { const q = p ? p + '/' + n : n;
    if (h.kind === 'directory') { out[q + '/'] = 1; await walk(h, q); } else out[q] = await (await h.getFile()).text(); } };
  await walk(root, ''); return out; }"""
top = '.page:last-of-type'


async def main(app, out):
    os.makedirs(out, exist_ok=True)
    async with Phone(app) as ph:
        pg = ph.pg
        await pg.evaluate(SETUP, TREE); await pg.wait_for_timeout(2500)
        await pg.evaluate("T.setFileTags(['Documents/receipt.txt'], () => ['Tax'])")
        await pg.evaluate("T.openFolder('Documents')"); await pg.wait_for_timeout(800)

        # A2: select two files; Move and Delete sit beside ⋯
        await ph.hold(f'{top} [data-fp="Documents/receipt.txt"]'); await pg.click(f'{top} [data-fp="Documents/letter.txt"]'); await pg.wait_for_timeout(300)
        check(await pg.locator(f'{top} [data-p="fmove"]').count() == 1 and await pg.locator(f'{top} [data-p="fdel"]').count() == 1, 'Move and Delete beside ⋯ while selecting')
        await ph.shot(f'{out}/1-selected.png')

        # B2: move to Documents › Bank on folder pages
        await pg.click(f'{top} [data-p="fmove"]'); await pg.wait_for_timeout(700)
        txt = await pg.inner_text(top)
        check('Moving 2 files' in txt and 'Move here' in txt and 'notes.txt' not in txt, 'the move page shows folders only')
        await ph.shot(f'{out}/2-moving-root.png')
        await pg.click(f'{top} [data-fd="Documents"]'); await pg.wait_for_timeout(500)
        check(await pg.locator(f'{top} [data-p="mhere"][disabled]').count() == 1, '"Move here" is off where the files already are')
        await pg.click(f'{top} [data-fd="Documents/Bank"]'); await pg.wait_for_timeout(500)
        await ph.shot(f'{out}/3-moving-bank.png')
        await pg.click(f'{top} [data-p="mhere"]'); await pg.wait_for_timeout(1500)
        fs = await pg.evaluate(LIST)
        check('Documents/Bank/receipt.txt' in fs and 'Documents/receipt.txt' not in fs and 'Documents/Bank/letter.txt' in fs, 'files moved on the phone')
        tags = await pg.evaluate("(T.fidx.get('Documents/Bank/receipt.txt') || {}).tags")
        check(tags == ['Tax'], f'a moved file keeps its tags: {tags}')
        check(await pg.evaluate("T.pages.map(p => p.dir).join('|')") == 'Documents', 'after moving, back on the folder it started from')
        await ph.shot(f'{out}/4-after-move.png')

        # rename: only the name is selected
        await ph.hold(f'{top} [data-fp="Documents/notes.txt"]'); await pg.click(f'{top} [data-p="selmenu"]'); await pg.wait_for_timeout(400)
        await pg.click('#sheet [data-act="ren"]'); await pg.wait_for_timeout(800)
        sel = await pg.evaluate("(() => { const i = document.querySelector('#askIn'); return [i.selectionStart, i.selectionEnd]; })()")
        check(sel == [0, 5], f'only the name is picked out: {sel}')
        await ph.shot(f'{out}/5-rename.png')
        await pg.fill('#askIn', 'passport.txt'); await pg.press('#askIn', 'Enter'); await pg.wait_for_timeout(1200)
        fs = await pg.evaluate(LIST)
        check('Documents/passport.txt' in fs and 'Documents/notes.txt' not in fs, 'renamed on the phone')

        # edit text
        await ph.hold(f'{top} [data-fp="Documents/passport.txt"]'); await pg.click(f'{top} [data-p="selmenu"]'); await pg.wait_for_timeout(400)
        await pg.click('#sheet [data-act="edit"]'); await pg.wait_for_timeout(1000)
        await pg.fill(f'{top} .fedit', 'Passport renewal: booked for 12 May.')
        await ph.shot(f'{out}/6-edit.png')
        await pg.click(f'{top} [data-p="tsave"]'); await pg.wait_for_timeout(1000)
        await ph.back(); await pg.wait_for_timeout(500)
        fs = await pg.evaluate(LIST)
        check(fs.get('Documents/passport.txt') == 'Passport renewal: booked for 12 May.', 'the edited text is saved')
        check(any(k.endswith('My Files/Documents/passport.txt') and v == 'Passport renewal: book in May.' for k, v in fs.items()), 'the earlier text is in Previous versions')

        # new folder
        await pg.click(f'{top} [data-p="fmore"]'); await pg.wait_for_timeout(400)
        await pg.click('#sheet [data-act="newf"]'); await pg.wait_for_timeout(300)
        await pg.fill('#askIn', 'Travel'); await pg.press('#askIn', 'Enter'); await pg.wait_for_timeout(1200)
        fs = await pg.evaluate(LIST)
        check('Documents/Travel/' in fs and await pg.evaluate("T.pages.at(-1).dir") == 'Documents/Travel', 'a new folder is made and opened')
        await ph.back(); await pg.wait_for_timeout(400)

        # delete with the bar's icon
        await ph.hold(f'{top} [data-fp="Documents/passport.txt"]'); await pg.click(f'{top} [data-p="fdel"]'); await pg.wait_for_timeout(400)
        await ph.shot(f'{out}/7-delete.png')
        await pg.click('#sheet [data-act="yes"]'); await pg.wait_for_timeout(1200)
        fs = await pg.evaluate(LIST)
        check('Documents/passport.txt' not in fs and await pg.evaluate("!T.fidx.has('Documents/passport.txt')"), 'deleted from the phone and the list')

        # Previous versions: bring back the deleted file, the earlier text, and undo the move
        await pg.evaluate("localStorage.setItem('agora.versions.view', 'items')")
        await pg.evaluate("T.openVersions()"); await pg.wait_for_timeout(1500)
        txt = await pg.inner_text(top)
        check('passport.txt' in txt and 'deleted' in txt and 'moved from Documents' in txt, f'Previous versions lists the file changes')
        await ph.shot(f'{out}/8-versions.png')
        await pg.click(f'{top} [data-p="vview"]'); await pg.wait_for_timeout(400)
        await ph.shot(f'{out}/9-versions-moments.png')
        await pg.click(f'{top} [data-p="vview"]'); await pg.wait_for_timeout(400)
        rows = await pg.evaluate(f"[...document.querySelectorAll('{top} .hrow')].map(b => b.innerText)")
        i = next(i for i, r in enumerate(rows) if 'deleted' in r)
        await pg.click(f'{top} .hrow[data-ver="{i}"]'); await pg.wait_for_timeout(300); await pg.click('#sheet [data-act="yes"]'); await pg.wait_for_timeout(1500)
        fs = await pg.evaluate(LIST)
        check(fs.get('Documents/passport.txt') == 'Passport renewal: booked for 12 May.', 'the deleted file is back')
        i = next(i for i, r in enumerate(rows) if 'edited' in r)
        await pg.click(f'{top} .hrow[data-ver="{i}"]'); await pg.wait_for_timeout(300); await pg.click('#sheet [data-act="yes"]'); await pg.wait_for_timeout(1500)
        fs = await pg.evaluate(LIST)
        check(fs.get('Documents/passport.txt') == 'Passport renewal: book in May.', 'the earlier text is back')
        i = next(i for i, r in enumerate(rows) if 'receipt' in r and 'moved' in r)
        await pg.click(f'{top} .hrow[data-ver="{i}"]'); await pg.wait_for_timeout(300); await pg.click('#sheet [data-act="yes"]'); await pg.wait_for_timeout(1500)
        fs = await pg.evaluate(LIST)
        check('Documents/receipt.txt' in fs and 'Documents/Bank/receipt.txt' not in fs, 'the moved file went back')
        check(await pg.evaluate("(T.fidx.get('Documents/receipt.txt') || {}).tags") == ['Tax'], 'with its tags')
        await ph.back(); await ph.back(); await pg.wait_for_timeout(400)
        check(await pg.evaluate("T.pages.length") == 0, 'Back steps out to home')
        await pg.evaluate("T.rescan()"); await pg.wait_for_timeout(1500)
        idx = sorted(await pg.evaluate("[...T.fidx.keys()]"))
        check(idx == sorted(['Documents', 'Documents/Bank', 'Documents/Bank/statement.txt', 'Documents/Bank/letter.txt', 'Documents/receipt.txt', 'Documents/passport.txt', 'Documents/Travel', 'Work', 'Work/plan.txt']), f'a refresh agrees with the list: {idx}')
        errs = [e for e in ph.errors if 'favicon' not in e]
        check(not errs, f'no JavaScript errors: {errs}')
    print('\n' + ('ALL OK' if not fails else f'{len(fails)} FAILED: {fails}'))
    return not fails


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('app'); ap.add_argument('--out', default='shots/fileops')
    a = ap.parse_args()
    sys.exit(0 if asyncio.run(main(a.app, a.out)) else 1)
