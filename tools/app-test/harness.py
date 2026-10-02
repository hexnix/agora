"""Agora phone test harness (Playwright, 412x915 phone view).

Works offline: JSZip, pdf.js and the fonts come from this folder, so nothing is fetched
from cdnjs or Google Fonts. The app is served from APP_DIR on a local port.

Quick smoke test (imports the zips in order, then screenshots home, a study scene,
its meaning page and its source page, and reports any JavaScript errors):

    python3 harness.py APP_DIR --zips "ZIPDIR/[0-9]*.zip" --out shots/

In the repo, test with the made-up library (6 cards covering every kind of scene, definition
and source; card ids test-candor, test-brusque, test-reticent, test-ephemeral, test-palimpsest,
test-heuristic):

    python3 tools/app-test/harness.py . --zips tools/app-test/fixtures/test-library.zip --out shots/

Use from your own script:

    from harness import Phone
    async with Phone(APP_DIR) as ph:
        print(await ph.imp([...zips]))
        await ph.open_card('imp-20260704_123202')
        await ph.swipe(-300)                      # finger moves up = go to the meaning
        await ph.shot('shots/meaning.png')
        print(ph.errors)

Inside the page, `T` exposes: T.cards, T.decks, T.S (study state), T.openStudy(deck, cardId),
T.layer(L), T.extent(L), T.back(); for the Study deck: T.SD (progress), T.studyToday, T.queueOrder, T.dayNo, T.openStudyPage,
T.openQueue, T.openDeck, T.studyDeck (see test_study.py); for History, names and tiles: T.HI, T.openHistory, T.nameOf,
T.refreshTiles, T.thumbKeyOf (see test_history.py); for My Files: T.FX, T.fidx, T.FV, T.pages, T.connectFiles, T.rescan, T.openFolder,
T.openViewer, T.openSearch, T.setFileTags, T.saveTagsFile, T.store, T.blobURL; for Bookmarks: T.BM, T.openMarks (see test_bookmarks.py). The phone's folder picker can't be clicked
in a test: fill the origin private file system (navigator.storage.getDirectory()) with made-up files and hand it to the
app as "My Files" with  window.showDirectoryPicker = async () => dir; await T.connectFiles(true)  (see test_files.py).  Fonts: Plex Mono is exact; the Merriweather test font has no true italic, so italic text shows upright
in test screenshots (the phone shows real italics).
Setup once per workspace:
    pip install playwright --break-system-packages   (Chromium is usually preinstalled)
"""
import asyncio, glob, http.server, os, socketserver, sys, threading, functools, argparse

KIT = os.path.dirname(os.path.abspath(__file__))
LIB, FONTS = os.path.join(KIT, 'lib'), os.path.join(KIT, 'fonts')


def _serve(root):
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a): pass
    srv = socketserver.ThreadingTCPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=root))
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]


def _fonts_css(port):
    u = f'http://127.0.0.1:{port}/__fonts/'
    faces = [('normal', 300, 'plex-300-normal'), ('italic', 400, 'plex-400-italic'), ('normal', 400, 'plex-400-normal'),
             ('normal', 500, 'plex-500-normal'), ('normal', 600, 'plex-600-normal')]
    css = ''.join(f"@font-face{{font-family:'IBM Plex Mono';font-style:{s};font-weight:{w};src:url({u}{f}.woff2) format('woff2');}}" for s, w, f in faces)
    for s in ('normal', 'italic'):  # one variable file stands in for light/bold and italic
        css += f"@font-face{{font-family:'Merriweather';font-style:{s};font-weight:300 700;src:url({u}merri.woff2) format('woff2');}}"
    return css


class Phone:
    def __init__(self, app_dir, width=412, height=915):
        self.app_dir, self.w, self.h = os.path.abspath(app_dir), width, height
        self.errors = []

    async def __aenter__(self):
        from playwright.async_api import async_playwright
        self.srv, self.port = _serve(self.app_dir)
        self.base = f'http://127.0.0.1:{self.port}/'
        self.pw = await async_playwright().start()
        exe = '/opt/pw-browsers/chromium' if os.path.exists('/opt/pw-browsers/chromium') and os.path.isfile('/opt/pw-browsers/chromium') else None
        self.browser = await self.pw.chromium.launch(**({'executable_path': exe} if exe else {}))
        ctx = self.ctx = await self.browser.new_context(viewport={'width': self.w, 'height': self.h}, device_scale_factor=2,
                                                        has_touch=True, is_mobile=True, service_workers='block', accept_downloads=True)
        js = {'jszip.min.js': 'jszip.min.js', 'pdf.min.js': 'pdf.min.js', 'pdf.worker.min.js': 'pdf.worker.min.js'}

        async def cdn(r):
            name = r.request.url.rsplit('/', 1)[-1]
            if name in js:
                await r.fulfill(path=os.path.join(LIB, js[name]), content_type='application/javascript', headers={'access-control-allow-origin': '*'})
            else:
                await r.abort()
        await ctx.route('**/cdnjs.cloudflare.com/**', cdn)
        await ctx.route('**/fonts.googleapis.com/**', lambda r: r.fulfill(body=_fonts_css(self.port), content_type='text/css'))
        await ctx.route('**/fonts.gstatic.com/**', lambda r: r.abort())
        await ctx.route('**/i.ytimg.com/**', lambda r: r.abort())
        await ctx.route('**/__fonts/**', lambda r: r.fulfill(path=os.path.join(FONTS, r.request.url.rsplit('/', 1)[-1]), content_type='font/woff2', headers={'access-control-allow-origin': '*'}))

        async def page(r):  # expose the app's internals as window.T (the app is one closure)
            html = open(os.path.join(self.app_dir, 'index.html'), encoding='utf-8').read()
            i = html.rindex('})();')
            html = html[:i] + ("window.T={get cards(){return cards},get decks(){return decks},openStudy,get S(){return S},layer,extent,back,"
                               # My Files: the index, the folder and its screens
                               # (getters, so an older index.html without these still loads)
                               "get FX(){return FX},"
                               # Study: progress records, today's cards, the queue (getters: older versions don't have them)
                               "get SD(){return SD},get studyToday(){return studyToday},get queueOrder(){return queueOrder},get dayNo(){return dayNo},get openStudyPage(){return openStudyPage},get openQueue(){return openQueue},get openDeck(){return openDeck},get studyDeck(){return studyDeck},"
                               # History, card names and tile pictures (v27)
                               "get HI(){return HI},get openHistory(){return openHistory},get nameOf(){return nameOf},get refreshTiles(){return refreshTiles},get thumbKeyOf(){return thumbKeyOf},"
                               # Bookmarks (v29)
                               "get BM(){return BM},get openMarks(){return openMarks},"
                               "get FX(){return FX},get fidx(){return fidx},get FV(){return FV},get pages(){return pages},get connectFiles(){return connectFiles},get rescan(){return rescan},get openFolder(){return openFolder},get openViewer(){return openViewer},get openSearch(){return openSearch},get setFileTags(){return setFileTags},get saveTagsFile(){return saveTagsFile},get store(){return store},get fstore(){return fstore},get blobURL(){return blobURL}};\n") + html[i:]
            await r.fulfill(body=html, content_type='text/html')
        # also with a query, as when Android's share menu opens the app at ./?url=…
        await ctx.route(lambda u: u.split('?')[0] in (self.base, self.base + 'index.html'), page)
        self.pg = await ctx.new_page()
        self.pg.on('pageerror', lambda e: self.errors.append(str(e)))
        self.pg.on('console', lambda m: self.errors.append('console: ' + m.text)
                   if m.type == 'error' and 'net::' not in m.text and 'Failed to load' not in m.text else None)
        await self.pg.goto(self.base)
        await self.pg.wait_for_timeout(800)
        return self

    async def __aexit__(self, *a):
        await self.browser.close(); await self.pw.stop(); self.srv.shutdown()

    async def imp(self, files, timeout=600000):
        """Import zips through the app's own Import (all in one go, in the order given). Returns the toast text."""
        await self.pg.evaluate("{const t=document.querySelector('#toast');t.textContent='';t.classList.remove('show')}")
        await self.pg.set_input_files('#zipPicker', list(files))
        await self.pg.wait_for_function("document.querySelector('#toast').classList.contains('show') && document.querySelector('#toast').textContent", timeout=timeout)
        t = await self.pg.inner_text('#toast'); await self.pg.wait_for_timeout(2800); return t

    async def open_card(self, cid):
        await self.pg.evaluate("id=>{const c=T.cards.find(x=>x.id===id); T.openStudy(T.decks.find(d=>d.id===c.deckId), id)}", cid)
        await self.pg.wait_for_timeout(900)

    async def open_deck(self, name):
        await self.pg.evaluate("n=>T.openStudy(T.decks.find(d=>d.name===n))", name)
        await self.pg.wait_for_timeout(900)

    async def swipe(self, dy, dx=0, x=206, y=450, steps=12):
        """A finger drag in the study view. dy<0: finger moves up (meaning pages). dy>0: down (source). dx<0: next card."""
        await self.pg.evaluate("""([x,y,dx,dy,steps])=>{const el=document.querySelector('.study');const o={pointerId:7,pointerType:'touch',isPrimary:true,bubbles:true};
          el.dispatchEvent(new PointerEvent('pointerdown',{...o,clientX:x,clientY:y}));
          return new Promise(r=>{let i=0;const f=()=>{i++;el.dispatchEvent(new PointerEvent('pointermove',{...o,clientX:x+dx*i/steps,clientY:y+dy*i/steps}));
            if(i<steps) setTimeout(f,16); else {el.dispatchEvent(new PointerEvent('pointerup',{...o,clientX:x+dx,clientY:y+dy}));r();}};setTimeout(f,16);});}""", [x, y, dx, dy, steps])
        await self.pg.wait_for_timeout(650)

    async def hold(self, sel_or_xy, ms=700):
        """Long-press an element (CSS selector) or a point (x, y)."""
        if isinstance(sel_or_xy, str):
            bb = await self.pg.locator(sel_or_xy).first.bounding_box(); x, y = bb['x'] + bb['width'] / 2, bb['y'] + bb['height'] / 2
        else:
            x, y = sel_or_xy
        await self.pg.evaluate("""([x,y,ms])=>{const t=document.elementFromPoint(x,y);const o={pointerId:9,pointerType:'touch',isPrimary:true,bubbles:true,clientX:x,clientY:y};
          t.dispatchEvent(new PointerEvent('pointerdown',o)); return new Promise(r=>setTimeout(()=>{t.dispatchEvent(new PointerEvent('pointerup',o)); t.dispatchEvent(new MouseEvent('click',{bubbles:true,clientX:x,clientY:y})); r();},ms));}""", [x, y, ms])
        await self.pg.wait_for_timeout(400)

    async def back(self):
        """Like the phone's Back button. On the scene page (level 0) this closes the study view."""
        await self.pg.evaluate("T.back()"); await self.pg.wait_for_timeout(600)

    async def level(self):
        return await self.pg.evaluate("T.S ? T.S.level : null")

    async def shot(self, path):
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        await self.pg.screenshot(path=path)


async def smoke(app_dir, zips, out):
    async with Phone(app_dir) as ph:
        if zips:
            print('import:', await ph.imp(zips))
        await ph.shot(f'{out}/1-home.png')
        n = await ph.pg.evaluate("T.cards.length")
        print('cards:', n, '| decks:', await ph.pg.evaluate("T.decks.map(d=>d.name).join(', ')"))
        if n:
            await ph.pg.evaluate("T.openStudy(T.decks.find(d=>T.cards.some(c=>c.deckId===d.id)))"); await ph.pg.wait_for_timeout(900)
            await ph.shot(f'{out}/2-scene.png')
            await ph.swipe(-320); print('after swipe up, level =', await ph.level()); await ph.shot(f'{out}/3-meaning.png')
            if await ph.level(): await ph.back()
            await ph.swipe(320); print('after swipe down, level =', await ph.level(), '(-1 = source page; 0 = card has no source)'); await ph.shot(f'{out}/4-source.png')
            if await ph.level(): await ph.back()
            await ph.swipe(0, dx=-260); await ph.shot(f'{out}/5-next-card.png')
        print('JS errors:', ph.errors or 'none')


if __name__ == '__main__':
    a = argparse.ArgumentParser()
    a.add_argument('app_dir'); a.add_argument('--zips', default=''); a.add_argument('--out', default='shots')
    o = a.parse_args()
    zips = sorted(glob.glob(o.zips)) if o.zips else []
    asyncio.run(smoke(o.app_dir, zips, o.out))
