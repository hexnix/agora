"""Study deck test: 30 made-up cards in a deck called "Vocabulary" (the test library's 6 cards plus copies of them).

    python3 tools/app-test/test_study.py . --out shots/study/

Checks the Study banner on Vocabulary's page, today's cards (20 new a day plus every review due), the queue order (oldest
first, a show's cards in episode order), the queue page (list, grid, search, select all, bring to front), a session
(Continue on a new card; Repeat, Tomorrow and Pass on a card seen before; no swiping past a card), the cycle's gaps,
"Done for today" and "Learn 10 more new cards", that browsing elsewhere moves nothing, that holding a card no longer marks it,
Back, the backup carrying the progress, re-imports reporting "already up to date", and JavaScript errors. Screenshots go to --out.
"""
import argparse, asyncio, copy, json, os, sys, tempfile, zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import Phone

KIT = os.path.dirname(os.path.abspath(__file__))
LIB_ZIP = os.path.join(KIT, 'fixtures', 'test-library.zip')
WORDS = ['ardent', 'brazen', 'callow', 'dour', 'effete', 'fatuous', 'garrulous', 'hapless', 'insipid', 'jejune', 'kitsch', 'lurid',
         'maudlin', 'nebulous', 'obtuse', 'pallid', 'quixotic', 'rancid', 'sallow', 'turgid', 'unctuous', 'vapid', 'wan', 'zealous']


def vocab_zip(path):
    """The test library as one deck, Vocabulary, with 24 copies so a day has more than 20 new cards.
    The copies of the show cards are spread over episodes and dated out of episode order, to test the queue order."""
    src = zipfile.ZipFile(LIB_ZIP)
    man = json.loads(src.read('manifest.json'))
    cards = [c for d in man['decks'] for c in d['cards']]
    for i, w in enumerate(WORDS):
        c = copy.deepcopy(cards[i % len(cards)])
        c['id'] = f'test-copy-{i:02d}'; c['word'] = w
        if 'Example Show' in c.get('tags', []):
            ep = [3, 1, 2, 4][i % 4]  # later episodes dated earlier: the queue must still go by episode
            c['tags'] = ['TV', 'Example Show', f'S01 E0{ep}']
            c['shotAt'] = 1700000000000 + (5 - ep) * 1000 + i
        else:
            c['shotAt'] = 1690000000000 + i * 1000
        cards.append(c)
    man['decks'] = [{'id': 'test-deck-vocab', 'name': 'Vocabulary', 'cards': cards}]
    with zipfile.ZipFile(path, 'w') as z:
        for n in src.namelist():
            if n != 'manifest.json': z.writestr(n, src.read(n))
        z.writestr('manifest.json', json.dumps(man))


async def main(app, out):
    os.makedirs(out, exist_ok=True)
    fails = []
    def check(ok, what):
        print(('PASS ' if ok else 'FAIL ') + what)
        if not ok: fails.append(what)
    tmp = tempfile.mkdtemp(); vz = os.path.join(tmp, 'vocab.zip'); vocab_zip(vz)
    async with Phone(app) as ph:
        pg = ph.pg
        async def tap(sel): await pg.locator(sel).first.click(); await pg.wait_for_timeout(450)
        today = lambda: pg.evaluate("(() => { const t = T.studyToday(); return {due: t.due.length, fresh: t.fresh.length, done: t.done.length, left: t.left, queue: t.queue.length} })()")
        print('import:', await ph.imp([vz]))
        await pg.wait_for_function("T.SD.loaded")

        # Vocabulary opens on its page with the Study banner first
        await pg.evaluate("T.openDeck(T.studyDeck())"); await pg.wait_for_timeout(500)
        check(await pg.locator('.page:last-child .sban').count() == 1, 'Vocabulary shows the Study banner')
        meta = await pg.inner_text('.page:last-child .sban .m')
        check('20 of 20 left today' in meta and '10 new in queue' in meta, f'banner: {meta!r}')
        check(await pg.locator('.page:last-child .due').count() == 0, 'no blue "to review" counts')
        await ph.shot(f'{out}/01-vocabulary.png')

        # the queue: oldest first, the show's cards in episode order
        q = await pg.evaluate("T.queueOrder().map(c => ({id: c.id, tags: c.tags, shot: c.shotAt}))")
        eps = [int(c['tags'][2][-2:]) for c in q if 'Example Show' in (c['tags'] or [])]
        check(eps == sorted(eps) and len(eps) > 4, f'the show\'s cards come in episode order: {eps}')
        rest = [c['shot'] for c in q if 'Example Show' not in (c['tags'] or [])]
        check(rest == sorted(rest), 'other cards come oldest first')

        # the Study page: today's 20, all new
        await tap('.page:last-child .sban')
        check(await pg.locator('.page:last-child .gcard .lbl').count() == 20, 'today shows 20 new cards')
        await ph.shot(f'{out}/02-study-page.png')

        # the queue page: list, grid, search, select all, bring to front
        await tap('.page:last-child [data-p="queue"]')
        check(await pg.locator('.page:last-child .qrow').count() == 30, 'the queue lists every new card')
        await ph.shot(f'{out}/03-queue-list.png')
        await tap('.page:last-child [data-p="view"]')
        check(await pg.locator('.page:last-child .gcard .qn').count() == 30, 'the grid view numbers every card')
        await ph.shot(f'{out}/04-queue-grid.png')
        await tap('.page:last-child [data-p="view"]')
        await tap('.page:last-child [data-p="qsearch"]')
        await pg.fill('#qq', 'example mag'); await pg.wait_for_timeout(300)
        await ph.shot(f'{out}/05-queue-search-typing.png')
        await tap('.page:last-child .sugg button')  # pins "Example Magazine"
        n_hit = await pg.locator('.page:last-child .qrow').count()
        check(n_hit == 10, f'the pinned tag finds its 10 cards ({n_hit})')
        await ph.shot(f'{out}/06-queue-search-tag.png')
        await tap('.page:last-child [data-p="all"]')
        check(await pg.inner_text('.page:last-child .selcount') == '10 selected', 'Select all selects the 10')
        await ph.shot(f'{out}/07-queue-selected.png')
        await tap('.page:last-child [data-p="front"]'); await pg.wait_for_timeout(400)
        first = await pg.evaluate("T.queueOrder().slice(0, 10).map(c => c.tags[1])")
        check(all(t == 'Example Magazine' for t in first), 'Bring to front puts them first')
        check(await pg.locator('.page:last-child #qq').count() == 0 and await pg.locator('.page:last-child .qrow .i').first.inner_text() == '1', 'and the queue shows again from the top')
        await ph.shot(f'{out}/08-queue-after.png')
        await pg.evaluate("T.back()"); await pg.wait_for_timeout(400)  # back to the Study page

        # a session: a new card has only Continue; swiping does not move on
        await tap('.page:last-child [data-p="start"]')
        check(await pg.evaluate("!!T.S && !!T.S.drill"), 'Start opens a Study session')
        check(await pg.locator('.answer button').count() == 1 and 'Continue' in await pg.inner_text('.answer'), 'a new card shows Continue only')
        check(await pg.locator('.hint').count() == 0, 'no gesture hint in a session')
        await ph.shot(f'{out}/09-new-card.png')
        await ph.swipe(0, -300); i = await pg.evaluate("T.S.i")
        check(i == 0, 'swiping left does not skip the card')
        marks = "JSON.stringify(T.cards.map(c => !!c.review))"; m0 = await pg.evaluate(marks)
        await ph.hold((206, 450), 800)
        check(await pg.evaluate(marks) == m0 and not await pg.locator('#toast.show').count(), 'holding the card marks nothing')
        await ph.swipe(-300); await ph.shot(f'{out}/10-new-card-meaning.png')
        first_id = await pg.evaluate("T.S.order[0].id")
        await tap('.answer [data-a="continue"]')
        r = await pg.evaluate(f"T.SD.recs.get('{first_id}')"); d0 = await pg.evaluate("T.dayNo()")
        check(r and r['step'] == 0 and r['due'] == d0 + 1 and r['first'] == d0, f'Continue starts the cycle: back in 1 day {r}')
        check(await pg.evaluate("T.S.i") == 1 and await pg.evaluate("T.S.level") == 0, 'and moves to the next card, on its scene')
        check(await pg.inner_text('.foot .count') == '2 / 20', 'the count reads 2 / 20')
        for k in range(19):
            await pg.locator('.answer [data-a="continue"]').click(); await pg.wait_for_timeout(430)
        check(await pg.locator('.sdone').count() == 1, 'Done for today after 20')
        await ph.shot(f'{out}/11-done.png')
        t = await today(); check(t['done'] == 20 and t['left'] == 0 and t['queue'] == 10, f'today: {t}')
        await tap('.sdone [data-s="more"]')
        check(await pg.locator('.sdone').count() == 0 and await pg.inner_text('.foot .count') == '21 / 30', 'Learn 10 more carries on at 21 / 30')
        await pg.evaluate("T.back()"); await pg.wait_for_timeout(500)
        check(await pg.evaluate("!T.S") and 'Study' in await pg.inner_text('.page:last-child .pt'), 'Back leaves the session for the Study page')
        await ph.shot(f'{out}/12-study-page-progress.png')

        # browsing elsewhere moves nothing: open a card from the queue's deck page and swipe through
        before = await pg.evaluate("JSON.stringify([...T.SD.recs.values()])")
        await pg.evaluate("T.openStudy(T.studyDeck())"); await pg.wait_for_timeout(500)
        await ph.swipe(0, -300); await ph.swipe(-300)
        check(await pg.locator('.answer').count() == 0 and await pg.evaluate("T.S.i") == 1, 'a plain deck view swipes freely, no answer bar')
        await pg.evaluate("T.back()"); await pg.wait_for_timeout(400); await pg.evaluate("T.back()"); await pg.wait_for_timeout(400)
        check(await pg.evaluate("JSON.stringify([...T.SD.recs.values()])") == before, 'browsing does not change Study progress')

        # the next day: make every card look studied yesterday
        await pg.evaluate("T.SD.recs.forEach(r => { if (r.step != null) { r.first--; r.last--; r.due--; } })")
        await pg.evaluate("T.openStudyPage(T.studyDeck())"); await pg.wait_for_timeout(400)
        t = await today(); check(t['due'] == 20 and t['fresh'] == 10, f'next day: 20 reviews due and 10 new: {t}')
        last = await pg.evaluate("(() => { const c = T.studyToday().due[3]; T.SD.recs.get(c.id).step = 6; return c.id; })()")  # at its 120-day gap
        await tap('.page:last-child [data-p="start"]')
        labels = await pg.locator('.answer button').all_inner_texts()
        check([l.split('\n')[0] for l in labels] == ['Repeat', 'Tomorrow', 'Pass'] and '3 days' in labels[2], f'a card seen before: {labels}')
        await ph.shot(f'{out}/13-review-card.png')
        await ph.swipe(-300); await ph.shot(f'{out}/14-review-meaning.png')
        a, b, c = await pg.evaluate("T.S.order.slice(0, 3).map(c => c.id)")
        n0 = await pg.evaluate("T.S.order.length")
        await tap('.answer [data-a="repeat"]')
        check(await pg.evaluate("T.S.order.length") == n0 + 1 and await pg.evaluate(f"T.S.order[T.S.order.length - 1].id === '{a}'"), 'Repeat puts the card at the end of today')
        check(await pg.evaluate(f"T.SD.recs.get('{a}').step") == 0, 'Repeat keeps its place in the cycle')
        await tap('.answer [data-a="tomorrow"]')
        rb = await pg.evaluate(f"T.SD.recs.get('{b}')"); check(rb['step'] == 0 and rb['due'] == d0 + 1, f'Tomorrow: back tomorrow, same step {rb}')
        await tap('.answer [data-a="pass"]')
        rc = await pg.evaluate(f"T.SD.recs.get('{c}')"); check(rc['step'] == 1 and rc['due'] == d0 + 3, f'Pass: on to the 3-day gap {rc}')
        lbl = await pg.inner_text('.answer [data-a="pass"]')
        check('done' in lbl, f'a card at its last gap: Pass says done ({lbl!r})')
        await tap('.answer [data-a="pass"]')
        rl = await pg.evaluate(f"T.SD.recs.get('{last}')"); check(rl.get('done') and 'due' not in rl, f'after 120 days it is done {rl}')
        check(await pg.inner_text('.foot .count') == '5 / 31', 'the count goes on (with the repeated card added)')
        await pg.evaluate("T.back()"); await pg.wait_for_timeout(500)

        # Back steps out one page at a time: Study page, Vocabulary, home
        for k in range(3):
            await pg.evaluate("T.back()"); await pg.wait_for_timeout(350)
        check(await pg.locator('.page').count() == 0, 'Back steps out to the home screen')
        await ph.shot(f'{out}/15-home.png')
        check(await pg.locator('#home .due').count() == 0, 'no "to review" on the home screen')

        # the ✎ menu has no Mark for review
        await pg.evaluate("T.openStudy(T.studyDeck())"); await pg.wait_for_timeout(500)
        await tap('.study [data-s="edit"]')
        check('review' not in (await pg.inner_text('#sheet')).lower(), 'the edit menu has no Mark for review')
        await pg.evaluate("T.back()"); await pg.wait_for_timeout(300); await pg.evaluate("T.back()"); await pg.wait_for_timeout(400)

        # backup carries the progress; re-importing it changes nothing
        await pg.click('#appMenu'); await pg.wait_for_timeout(500)
        async with pg.expect_download() as dl:
            await pg.click('#sheet [data-act="export"]')
        d = await dl.value; bpath = os.path.join(tmp, 'backup.zip'); await d.save_as(bpath)
        man = json.loads(zipfile.ZipFile(bpath).read('manifest.json'))
        st = man.get('study', {}); nrec = await pg.evaluate("T.SD.recs.size")
        check(len(st.get('cards', [])) == nrec >= 20 and st.get('daily') == 20, f'the backup carries Study progress ({len(st.get("cards", []))} cards)')
        await pg.wait_for_timeout(2500)
        t = await ph.imp([bpath]); print('re-import backup:', t)
        check('already up to date' in t and 'Study' not in t and 'Imported' not in t, 're-importing the backup: already up to date')
        t = await ph.imp([LIB_ZIP]); print('re-import library:', t)
        check(t == '6 already up to date', 're-importing the test library: already up to date')
        print('JS errors:', ph.errors or 'none')
        check(not ph.errors, 'no JavaScript errors')

    # a fresh phone: importing the backup brings the progress with it
    async with Phone(app) as ph:
        t = await ph.imp([bpath]); print('fresh import:', t)
        await ph.pg.wait_for_function("T.SD.loaded")
        check(f'Study progress for {nrec} cards' in t, 'a backup restores Study progress on a fresh phone')
        n = await ph.pg.evaluate("T.SD.recs.size"); check(n == nrec, f'{n} records restored')
        check(not ph.errors, 'no JavaScript errors (fresh phone)')
    print('\n' + ('ALL PASSED' if not fails else f'{len(fails)} FAILED: ' + '; '.join(fails)))
    return not fails


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('app'); ap.add_argument('--out', default='shots/study')
    a = ap.parse_args()
    sys.exit(0 if asyncio.run(main(a.app, a.out)) else 1)
