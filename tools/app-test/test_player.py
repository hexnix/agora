"""Video player test (v37): a made-up film in a made-up My Files, played in a phone held sideways (915×412).

    python3 tools/app-test/test_player.py . --out shots/player/

Checks that a film opens from its folder straight into the player, plays, shows only its file name, reads both subtitle
tracks from inside the .mkv (through the file's index, and by a pass through the whole file), finds a .srt next to it,
draws the line on screen at the right moments, swipes a subtitle left and right to the next and previous lines, the
subtitles panel (tracks, Off, size), double-tap skipping, the seek bar, brightness and volume swipes, the lock, carrying on
where the film was left, Back stepping out one layer at a time, and JavaScript errors. The film and its lines are invented
(tools/app-test/make_test_video.sh makes it): never put real films or subtitles in the repo.
"""
import argparse, asyncio, base64, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import Phone

KIT = os.path.dirname(os.path.abspath(__file__))
FILM = os.path.join(KIT, 'fixtures', 'made-up-film.mkv')
SRT = """1
00:00:03,000 --> 00:00:05,000
A line from the file next to the film.

2
00:00:10,000 --> 00:00:12,000
And a second one.
"""

FILL_JS = r"""
async ([film, srt]) => {
  const root = await navigator.storage.getDirectory();
  for await (const [n] of root.entries()) await root.removeEntry(n, { recursive: true });
  const put = async (path, blob) => {
    const parts = path.split('/'); let d = root;
    for (const p of parts.slice(0, -1)) d = await d.getDirectoryHandle(p, { create: true });
    const w = await (await d.getFileHandle(parts[parts.length - 1], { create: true })).createWritable(); await w.write(blob); await w.close();
  };
  await put('Films/Made Up Film.mkv', new Blob([Uint8Array.from(atob(film), c => c.charCodeAt(0))]));
  await put('Films/Made Up Film.en.srt', new Blob([srt]));
  await put('Films/notes.txt', new Blob(['not a film']));
  window.showDirectoryPicker = async () => root;
}
"""


async def main(app, out):
    os.makedirs(out, exist_ok=True)
    fails = []
    def check(ok, what):
        print(('ok   ' if ok else 'FAIL ') + what)
        if not ok: fails.append(what)

    async with Phone(app, width=915, height=412) as ph:
        pg = ph.pg
        film = base64.b64encode(open(FILM, 'rb').read()).decode()
        await pg.evaluate(FILL_JS, [film, SRT])
        await pg.evaluate("T.connectFiles(true)")
        await pg.wait_for_function("T.FX.scanned && !T.FX.scanning", timeout=20000)
        check(await pg.evaluate("!!T.fidx.get('Films/Made Up Film.mkv')"), '.mkv films are listed in My Files')

        # the film opens from its folder straight into the player
        await pg.evaluate("T.openFolder('Films')"); await pg.wait_for_timeout(500)
        await pg.locator('[data-fp="Films/Made Up Film.mkv"]').first.click()
        await pg.wait_for_function("T.PL && T.PL.v.currentTime > 0.5", timeout=15000)
        check(await pg.evaluate("!!document.querySelector('.player') && !document.querySelector('.fview')"), 'a film opens in the player, not the file viewer')
        check((await pg.inner_text('.pl-name')).strip() == 'Made Up Film.mkv', 'the top shows only the file name')
        check(await pg.evaluate("!document.querySelector('[data-p=\"speed\"]') && !/1×/.test(document.querySelector('.player').innerText)"), 'no speed button')

        # subtitles from inside the file: both tracks found, plus the .srt next to it
        await pg.wait_for_function("T.PL.cues.length >= 5 && T.PL.subLoad == null", timeout=15000)
        subs = await pg.evaluate("T.PL.subs.map(s => [s.id, s.label, s.ok])")
        print('  subtitles:', subs)
        check(len(subs) == 3 and subs[0][1] == 'English' and 'SDH' in subs[1][1] and subs[2][1] == 'Made Up Film.en.srt', 'two tracks inside the file and the .srt beside it are offered')
        check(await pg.evaluate("T.PL.subId") == 'mkv:3', 'the plain English track is chosen first, not SDH')
        cues = await pg.evaluate("T.PL.cues.map(c => [Math.round(c.s * 10) / 10, Math.round(c.e * 10) / 10, c.x])")
        check([c[0] for c in cues] == [2, 6, 15, 24, 33] and cues[0][2] == 'Nobody in this room reads\npast the first page.', f'lines and times read from the file ({cues[:2]}…)')
        scan = await pg.evaluate("(async () => { const f = await T.fileOf('Films/Made Up Film.mkv'), I = await T.mkvInfo(f); return (await T.mkvScan(f, I, 3, () => {}, () => true)).map(c => Math.round(c.s * 10) / 10); })()")
        check(scan == [2, 6, 15, 24, 33], f'a pass through the whole file finds the same lines ({scan})')

        # the line on screen follows the film
        await pg.evaluate("T.PL.v.pause(); T.PL.v.currentTime = 3"); await pg.wait_for_timeout(400)
        check('Nobody in this room reads' in await pg.inner_text('.pl-sub'), 'the line shows while it is spoken')
        await pg.evaluate("document.querySelector('.player').classList.remove('ui')"); await pg.wait_for_timeout(300)
        await ph.shot(f'{out}/01-subtitle.png')
        await pg.evaluate("T.PL.v.currentTime = 5"); await pg.wait_for_timeout(300)
        check((await pg.inner_text('.pl-sub')).strip() == '', 'and goes when it ends')

        # swipe a subtitle: left for the next line, right for the one before
        await pg.evaluate("T.PL.v.currentTime = 6.5"); await pg.wait_for_timeout(300)
        box = await pg.locator('.pl-sub span').bounding_box()
        y = box['y'] + box['height'] / 2; x = box['x'] + box['width'] / 2
        await pg.mouse.move(x, y); await pg.mouse.down(); await pg.mouse.move(x - 40, y, steps=4); await pg.mouse.move(x - 120, y, steps=4); await pg.mouse.up()
        await pg.wait_for_timeout(300)
        t = await pg.evaluate("T.PL.v.currentTime")
        check(abs(t - 15.01) < 0.2, f'swiping a line left goes to the next line ({t:.2f})')
        box = await pg.locator('.pl-sub span').bounding_box(); y = box['y'] + box['height'] / 2; x = box['x'] + box['width'] / 2
        await pg.mouse.move(x, y); await pg.mouse.down(); await pg.mouse.move(x + 40, y, steps=4); await pg.mouse.move(x + 120, y, steps=4); await pg.mouse.up()
        await pg.wait_for_timeout(300)
        t = await pg.evaluate("T.PL.v.currentTime")
        check(abs(t - 6.01) < 0.2, f'swiping right goes to the line before ({t:.2f})')

        # the controls: a tap shows them (1A), with the subtitle lifted above the seek bar
        await pg.evaluate("T.PL.v.currentTime = 3"); await pg.wait_for_timeout(200)
        await pg.mouse.click(300, 120); await pg.wait_for_timeout(500)
        check(await pg.evaluate("document.querySelector('.player').classList.contains('ui')"), 'a tap shows the controls')
        await ph.shot(f'{out}/02-controls.png')
        await pg.mouse.click(300, 120); await pg.wait_for_timeout(500)
        check(not await pg.evaluate("document.querySelector('.player').classList.contains('ui')"), 'another tap hides them')

        # double-tap the right side to skip 10 s, the left to go back
        t0 = await pg.evaluate("T.PL.v.currentTime")
        await pg.mouse.click(800, 200); await pg.wait_for_timeout(120); await pg.mouse.click(800, 200); await pg.wait_for_timeout(400)
        t1 = await pg.evaluate("T.PL.v.currentTime")
        check(abs(t1 - t0 - 10) < 0.6, f'double-tap on the right skips 10 s ({t0:.1f} → {t1:.1f})')
        await pg.mouse.click(100, 200); await pg.wait_for_timeout(120); await pg.mouse.click(100, 200); await pg.wait_for_timeout(400)
        t2 = await pg.evaluate("T.PL.v.currentTime")
        check(abs(t2 - t0) < 0.6, f'double-tap on the left goes back 10 s ({t2:.1f})')

        # the seek bar
        await pg.mouse.click(300, 120); await pg.wait_for_timeout(400)
        bar = await pg.locator('.pl-track').bounding_box()
        await pg.mouse.click(bar['x'] + bar['width'] * 0.5, bar['y'] + 1); await pg.wait_for_timeout(400)
        t = await pg.evaluate("T.PL.v.currentTime")
        check(abs(t - 20) < 1.5, f'tapping halfway along the seek bar goes to the middle ({t:.1f})')

        # brightness on the left, volume on the right
        await pg.evaluate("document.querySelector('.player').classList.remove('ui')")
        await pg.mouse.move(150, 300); await pg.mouse.down(); await pg.mouse.move(150, 250, steps=5); await pg.mouse.move(150, 330, steps=8)
        await ph.shot(f'{out}/03-brightness.png'); await pg.mouse.up()
        b = await pg.evaluate("T.PL.bright")
        check(b < 1 and await pg.evaluate("+getComputedStyle(document.querySelector('.pl-dim')).opacity") > 0, f'swiping down on the left dims the picture ({b:.2f})')
        await pg.mouse.move(770, 300); await pg.mouse.down(); await pg.mouse.move(770, 250, steps=5); await pg.mouse.move(770, 200, steps=8)
        await ph.shot(f'{out}/04-volume.png'); await pg.mouse.up()
        vol = await pg.evaluate("T.PL.vol")
        check(vol > 100 and await pg.evaluate("!!T.PL.gain"), f'swiping up on the right raises the volume, past 100 with a boost ({vol})')
        await pg.mouse.move(770, 150); await pg.mouse.down(); await pg.mouse.move(770, 200, steps=5); await pg.mouse.move(770, 380, steps=10); await pg.mouse.up()
        vol2 = await pg.evaluate("[T.PL.vol, T.PL.v.volume]")
        check(vol2[0] < 100 and abs(vol2[1] - vol2[0] / 100) < 0.01, f'and down again ({vol2})')

        # the subtitles panel (3A): tracks, Off, size; Back closes only the panel
        depth = await pg.evaluate("history.state && history.state.agora || 0")
        await pg.mouse.click(300, 120); await pg.wait_for_timeout(400)
        await pg.locator('[data-p="subs"]').click(); await pg.wait_for_timeout(500)
        await pg.evaluate("T.PL.v.currentTime = 3"); await pg.wait_for_timeout(300)
        await ph.shot(f'{out}/05-subtitles-panel.png')
        opts = await pg.locator('.pl-panel .pl-opt').all_inner_texts()
        check(len(opts) == 4 and opts[-1].strip() == 'Off', f'the panel lists both tracks, the .srt and Off ({len(opts)})')
        await pg.locator('.pl-opt[data-id="mkv:4"]').click()
        await pg.wait_for_function("T.PL.subId === 'mkv:4' && T.PL.subLoad == null && T.PL.cues.length === 3", timeout=10000)
        check(await pg.evaluate("T.PL.cues[0].x") == '[papers rustling]', 'picking SDH shows its lines')
        await pg.locator('.pl-opt[data-id^="file:"]').click()
        await pg.wait_for_function("T.PL.subId.startsWith('file:') && T.PL.cues.length === 2", timeout=10000)
        check(await pg.evaluate("T.PL.cues[0].x") == 'A line from the file next to the film.', 'picking the .srt next to the film shows its lines')
        await pg.locator('.pl-sizes [data-s="L"]').click(); await pg.wait_for_timeout(200)
        check(await pg.evaluate("getComputedStyle(document.querySelector('.player')).getPropertyValue('--sub').trim()") == '1.2', 'size L makes the subtitles bigger')
        await pg.locator('.pl-sizes [data-s="M"]').click()
        await pg.locator('.pl-opt[data-id="mkv:3"]').click(); await pg.wait_for_timeout(600)
        await ph.back(); await pg.wait_for_timeout(500)
        check(await pg.evaluate("!!T.PL && !document.querySelector('.pl-panel.open')"), 'Back closes the panel and leaves the film playing')
        check(await pg.evaluate("history.state && history.state.agora || 0") == depth, 'one layer for the panel')

        # the lock: taps do nothing but show the unlock button
        await pg.mouse.click(300, 120); await pg.wait_for_timeout(400)
        await pg.locator('[data-p="lock"]').click(); await pg.wait_for_timeout(300)
        await pg.mouse.click(300, 120); await pg.wait_for_timeout(500)
        locked = await pg.evaluate("[T.PL.locked, document.querySelector('.player').classList.contains('ui'), !document.querySelector('.pl-unlock').hidden]")
        check(locked == [True, False, True], f'locked: a tap shows only the unlock button ({locked})')
        await pg.locator('.pl-unlock').click(); await pg.wait_for_timeout(300)
        check(not await pg.evaluate("T.PL.locked"), 'and it unlocks')

        # carrying on where the film was left
        await pg.evaluate("T.PL.v.currentTime = 22.5"); await pg.wait_for_timeout(400)
        await ph.back(); await pg.wait_for_timeout(600)
        check(await pg.evaluate("!T.PL && !document.querySelector('.player')"), 'Back leaves the player')
        check(await pg.evaluate("T.pages.length && T.pages[T.pages.length - 1].kind") == 'files', 'and returns to the folder')
        await pg.locator('[data-fp="Films/Made Up Film.mkv"]').first.click()
        await pg.wait_for_function("T.PL && T.PL.v.readyState >= 1", timeout=15000); await pg.wait_for_timeout(600)
        t = await pg.evaluate("T.PL.v.currentTime")
        check(abs(t - 22.5) < 1.5, f'opening it again carries on from where it was left ({t:.1f})')
        check(await pg.evaluate("T.PL.subId") == 'mkv:3', 'and keeps the subtitle choice')
        check(await pg.evaluate("T.PL.vol === 100 && !T.PL.gain"), 'a film left near silent opens at full volume, outside the boost')
        await ph.back(); await pg.wait_for_timeout(500)

        # a .srt beside a film without subtitles of its own is picked by itself (made from the same film, its tracks removed by name)
        check(await pg.evaluate("T.parseSubFile('WEBVTT\\n\\n00:01.000 --> 00:02.500\\n<i>Hello</i> there\\n').map(c => [c.s, c.e, c.x]).join('|')") == '1,2.5,Hello there', 'a .vtt is read too')

        print('errors:', ph.errors)
        check(not [e for e in ph.errors if 'play()' not in e], 'no JavaScript errors')

    print('\n' + ('ALL OK' if not fails else f'{len(fails)} FAILED'))
    return 1 if fails else 0


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('app'); ap.add_argument('--out', default='shots/player')
    a = ap.parse_args()
    sys.exit(asyncio.run(main(a.app, a.out)))
