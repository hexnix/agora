"""Builds fixtures/test-library.zip: a small, made-up Agora library for testing.

Everything in it is invented (abstract pictures, our own example sentences and definitions),
so it is safe to keep in a public repo. The user's real cards never go in the repo.

It covers every kind of card the app knows:
  - video frame scene + subtitle cue under it, transcript source, episode tags   (deck "Example Show")
  - a card marked for review, a card with two definitions (text + image)
  - article scene as text, article source                                      (deck "Example Reading")
  - magazine PDF page scene with a highlight box
  - YouTube scene with a video source page and a video definition

When the app learns a new card field, add a card that uses it here and rebuild:
    python3 make_test_library.py            (needs Pillow and reportlab)
"""
import io, json, os, zipfile
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'fixtures', 'test-library.zip')


def frame(seed, w=1600, h=900):
    """An abstract 'film still': a dark gradient with a few soft shapes. No text on the picture."""
    im = Image.new('RGB', (w, h))
    px = im.load()
    a = [(30, 40, 70), (70, 30, 50), (20, 60, 55), (60, 50, 25), (35, 35, 80), (55, 25, 30)][seed % 6]
    for y in range(h):
        k = y / h
        row = (int(a[0] * (1 - k) + 8 * k), int(a[1] * (1 - k) + 8 * k), int(a[2] * (1 - k) + 12 * k))
        for x in range(0, w):
            px[x, y] = row
    d = ImageDraw.Draw(im, 'RGBA')
    for i in range(5):
        cx, cy, r = (seed * 397 + i * 311) % w, (seed * 211 + i * 173) % h, 80 + (seed * 37 + i * 53) % 220
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 255, 255, 18 + i * 6))
    return jpg(im)


def definition_image(word, lines):
    """A plain 'dictionary screenshot' style image (used where a definition is an image, not text)."""
    im = Image.new('RGB', (1080, 900), (250, 250, 250))
    d = ImageDraw.Draw(im)
    big, small = ImageFont.load_default(size=72), ImageFont.load_default(size=40)
    d.text((60, 70), word, fill=(10, 60, 140), font=big)
    for i, t in enumerate(lines):
        d.text((60, 200 + i * 60), t, fill=(30, 30, 30), font=small)
    return jpg(im)


def jpg(im):
    b = io.BytesIO(); im.save(b, 'JPEG', quality=82); return b.getvalue()


def magazine_pdf():
    """One A4 page of made-up magazine text. Returns (bytes, width, height, mark box for 'palimpsest')."""
    b = io.BytesIO(); W, H = A4
    c = canvas.Canvas(b, pagesize=A4)
    c.setFont('Helvetica-Bold', 22); c.drawString(60, H - 90, 'The City Beneath the City')
    c.setFont('Helvetica', 11)
    body = [
        'Walk through the old quarter and you are reading a page that has been written over many times.',
        'Shop signs from three different centuries share a single wall, each one painted on top of the last.',
        'Historians call the street a palimpsest: the newest layer never quite hides the ones below it.',
        'Builders who dig a new foundation still find tiles, coins and the outline of a forgotten well.',
        'Nothing here is ever fully erased; it is only covered, and covering is a kind of keeping.',
    ]
    y = H - 140
    mark = None
    for line in body:
        c.drawString(60, y, line)
        if 'palimpsest' in line:
            x0 = 60 + c.stringWidth(line.split('palimpsest')[0], 'Helvetica', 11)
            x1 = x0 + c.stringWidth('palimpsest', 'Helvetica', 11)
            # marks are fractions of the page: [left, top, right, bottom], measured from the top
            mark = [round((x0 - 2) / W, 4), round((H - y - 11) / H, 4), round((x1 + 2) / W, 4), round((H - y + 4) / H, 4)]
        y -= 22
    c.showPage(); c.save()
    return b.getvalue(), int(W), int(H), mark


def text_def(word, kind_of_word, pron, defs, examples):
    blocks = [{'t': 'headword', 'text': word}, {'t': 'meta', 'text': f'*{kind_of_word}*'},
              {'t': 'pron', 'items': [['US', pron]]}, {'t': 'rule'}]
    for i, d in enumerate(defs):
        blocks.append({'t': 'def', 'text': d, **({'n': str(i + 1)} if len(defs) > 1 else {})})
    blocks += [{'t': 'ex', 'text': e} for e in examples]
    return {'mode': 'text', 'kind': 'test', 'source': f'test-{word}', 'blocks': blocks}


def build():
    files, T0 = {}, 1767225600000  # 2026-01-01, a fixed time so the zip is the same every run

    def put(path, data):
        files[path] = data; return path

    show = {'id': 'test-deck-show', 'name': 'Example Show', 'cards': []}
    reading = {'id': 'test-deck-reading', 'name': 'Example Reading', 'cards': []}

    # --- Example Show: video frames with a subtitle cue, transcript sources, episode tags
    show['cards'].append({
        'id': 'test-candor', 'seq': 1, 'word': 'candor', 'addedAt': T0, 'shotAt': T0, 'sceneTime': 312.4,
        'scene': put('images/test-candor-scene.jpg', frame(1)),
        'definitions': [None],
        'definitionText': [text_def('candor', 'noun', '/ˈkæn·dər/',
                                    ['the quality of being honest and saying openly what you think'],
                                    ['She answered every question with surprising candor.'])],
        'sceneCaption': 'I appreciate your ==candor==,\nbut not your timing.',
        'tags': ['TV', 'Example Show', 'S01 E01'],
        'reference': {'kind': 'transcript', 'lines': [
            {'text': 'You could have told me last week.'},
            {'text': 'I appreciate your **candor**, but not your timing.', 'hit': True},
            {'text': 'Would you rather I had waited?'}]},
    })
    show['cards'].append({
        'id': 'test-brusque', 'seq': 2, 'word': 'brusque', 'addedAt': T0 + 1000, 'shotAt': T0 + 1000, 'sceneTime': 905.0,
        'review': True,
        'scene': put('images/test-brusque-scene.jpg', frame(2)),
        'definitions': [None, put('images/test-brusque-definition-2.jpg',
                                  definition_image('brusque', ['adjective', 'short and abrupt in manner;', 'not unkind, just in a hurry']))],
        'definitionText': [text_def('brusque', 'adjective', '/brʌsk/',
                                    ['quick and short in the way you speak or act, sometimes seeming rude'],
                                    ['His brusque reply ended the conversation.']), None],
        'sceneCaption': 'Sorry to be ==brusque==.\nWe are out of time.',
        'tags': ['TV', 'Example Show', 'S01 E01'],
        'reference': {'kind': 'transcript', 'lines': [
            {'text': 'Sorry to be **brusque**.', 'hit': True}, {'text': 'We are out of time.'}]},
    })
    show['cards'].append({
        'id': 'test-reticent', 'seq': 3, 'word': 'reticent', 'addedAt': T0 + 2000, 'shotAt': T0 + 2000, 'sceneTime': 140.2,
        'scene': put('images/test-reticent-scene.jpg', frame(3)),
        'definitions': [None],
        'definitionText': [text_def('reticent', 'adjective', '/ˈret·ə·sənt/',
                                    ['unwilling to share your thoughts or feelings', 'slow to speak about a particular subject'],
                                    ['He was reticent about his years abroad.'])],
        'sceneCaption': 'Why are you so ==reticent==\nabout the house?',
        'tags': ['TV', 'Example Show', 'S01 E02'],
        'reference': {'kind': 'transcript', 'lines': [
            {'text': 'Why are you so **reticent** about the house?', 'hit': True}, {'text': 'Some doors stay shut.'}]},
    })

    # --- Example Reading: article text, magazine PDF page, YouTube
    reading['cards'].append({
        'id': 'test-ephemeral', 'seq': 1, 'word': 'ephemeral', 'addedAt': T0 + 3000, 'shotAt': T0 + 3000,
        'scene': put('images/test-ephemeral-scene.jpg', frame(4)),
        'definitions': [None],
        'definitionText': [text_def('ephemeral', 'adjective', '/ɪˈfem·ər·əl/',
                                    ['lasting for only a short time'], ['Fame on the internet is often ephemeral.'])],
        'sceneText': {'paras': [
            '# Notes on a Summer Market',
            'Every Saturday the car park turns into a market, and by Sunday morning there is no sign it was ever there.',
            'The stalls are **built** in an hour and gone in less. Regulars say that is the charm: the whole thing is ==ephemeral==, a town that exists for one afternoon.',
            '*Some* traders have come for twenty years and still pack everything into a single van.']},
        'tags': ['Article', 'Example Magazine'],
        'reference': {'kind': 'article', 'title': 'Notes on a Summer Market', 'site': 'Example Magazine', 'url': 'https://example.com/summer-market'},
    })
    pdf, pw, ph, mark = magazine_pdf()
    put('pdfs/test-city.pdf', pdf)
    reading['cards'].append({
        'id': 'test-palimpsest', 'seq': 2, 'word': 'palimpsest', 'addedAt': T0 + 4000, 'shotAt': T0 + 4000,
        'scene': put('images/test-palimpsest-scene.jpg', frame(5)),
        'definitions': [None],
        'definitionText': [text_def('palimpsest', 'noun', '/ˈpæl·ɪmp·sest/',
                                    ['something that has been changed many times but still shows signs of its earlier forms'],
                                    ['The old wall was a palimpsest of faded signs.'])],
        'pdf': {'key': 'test-city', 'file': 'pdfs/test-city.pdf', 'page': 1, 'w': pw, 'h': ph, 'marks': [mark]},
        'tags': ['Magazine', 'Example Magazine'],
    })
    reading['cards'].append({
        'id': 'test-heuristic', 'seq': 3, 'word': 'heuristic', 'addedAt': T0 + 5000, 'shotAt': T0 + 5000,
        'scene': put('images/test-heuristic-scene.jpg', frame(6)),
        'definitions': [None, put('images/test-heuristic-definition-2.jpg', frame(7, 1280, 720))],
        'definitionText': [text_def('heuristic', 'noun', '/hjʊˈrɪs·tɪk/',
                                    ['a simple rule or shortcut that helps you decide or solve a problem quickly'],
                                    ['"Measure twice, cut once" is a useful heuristic.']),
                           {'source': 'test-heuristic-video', 'video': {'vid': 'TESTVIDEO01', 'title': 'Heuristics, explained in five minutes'}}],
        'sceneCaption': 'It is just a ==heuristic==,\nnot a law of nature.',
        'tags': ['YouTube', 'Example Channel'],
        'reference': {'kind': 'video', 'vid': 'TESTVIDEO02', 't': 95, 'title': 'How we make quick decisions',
                      'thumb': put('images/test-heuristic-reference.jpg', frame(8, 480, 270))},
    })

    for d in (show, reading):
        for c in d['cards']:
            c['definition'] = c['definitions'][0]
    man = {'app': 'agora', 'version': 1, 'decks': [show, reading]}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('manifest.json', json.dumps(man, ensure_ascii=False, indent=2))
        for p, data in files.items():
            z.writestr(zipfile.ZipInfo(p, (2026, 1, 1, 0, 0, 0)), data)
    print('wrote', OUT, f'({os.path.getsize(OUT) // 1024} KB, {sum(len(d["cards"]) for d in (show, reading))} cards)')


if __name__ == '__main__':
    build()
