"""Makes the made-up book the reader test uses (fixtures/made-up-book.epub): "The Salt Ledger" by M. A. Invented, an EPUB 3
with a nav page and an EPUB 2 toc.ncx, a cover page drawn as an svg, five chapters of invented prose (one with a picture, one with
a note linking to the notes at the end), and its own stylesheet and script, which the reader must leave out. Every word is invented.

    python3 tools/app-test/make_test_book.py
"""
import io, os, random, zipfile
from PIL import Image, ImageDraw

KIT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(KIT, 'fixtures', 'made-up-book.epub')

CHAPTERS = ['The Last Ferry', 'A Box of Letters', 'The Harbour Office', 'Low Water', 'The Marigold']
WORDS = ("harbour ledger tide clerk gull rope lantern salt pencil anchor ferry mud boat net letter cupboard window morning "
         "evening quay rain wind oranges ink page margin crease shadow door stair lamp coat").split()
SENT = ["The {a} by the {b} had not moved since the {c} came in.", "Wren watched the {a} for a long while and said nothing.",
        "Somebody had left a {a} on the {b}, as if they meant to come back for it.", "It was the kind of {a} that only a {b} would notice.",
        "Nobody remembered why the {a}; the clerk said it had always been there, the way the {b} had always been there.",
        "Outside, the {a} argued over the {b}, and the {c} went on regardless.", "She wrote the word *{a}* in her notebook and underlined it twice."]


def para(rng, n=4):
    out = []
    for _ in range(n):
        s = rng.choice(SENT).format(a=rng.choice(WORDS), b=rng.choice(WORDS), c=rng.choice(WORDS))
        out.append(s.replace('*', '<i>', 1).replace('*', '</i>', 1) if '*' in s else s)
    return ' '.join(out)


def picture(w, h, seed):
    im = Image.new('RGB', (w, h)); d = ImageDraw.Draw(im)
    for y in range(h): d.line([(0, y), (w, y)], fill=(15 + y * 40 // h, 27 + y * 30 // h, 51 - y * 20 // h))
    r = random.Random(seed)
    for _ in range(4):
        x, y, s = r.randint(0, w), r.randint(0, h), r.randint(w // 10, w // 4)
        d.ellipse([x - s, y - s, x + s, y + s], outline=(138, 75, 42), width=3)
    b = io.BytesIO(); im.save(b, 'JPEG', quality=80); return b.getvalue()


def page(title, body):
    return f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"><head><title>{title}</title>
<link rel="stylesheet" type="text/css" href="../css/book.css"/><style>p {{ color: red; }}</style><script>window.pwned = 1;</script></head>
<body>{body}</body></html>"""


def main():
    rng = random.Random(7)
    files = {}
    files['OEBPS/images/cover.jpg'] = picture(600, 900, 1)
    files['OEBPS/images/harbour.jpg'] = picture(900, 500, 2)
    files['OEBPS/css/book.css'] = 'body { font-family: "Comic Sans MS"; background: yellow; } .x { color: green; }'
    files['OEBPS/text/cover.xhtml'] = page('Cover', '<div class="cover"><svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 600 900">'
                                          '<image width="600" height="900" xlink:href="../images/cover.jpg"/></svg></div>')
    for i, name in enumerate(CHAPTERS, 1):
        body = f'<h1 id="c{i}">Chapter {i}<br/>{name}</h1>'
        n = 9 if i != 4 else 3  # chapter 4 is short, so it fits on one screen
        for k in range(n):
            p = para(rng, 5)
            if i == 2 and k == 2: body += '<figure><img src="../images/harbour.jpg" alt="The harbour"/><figcaption>The harbour at low water</figcaption></figure>'
            if i == 3 and k == 1: p += ' The line in pencil read <i>the Marigold, outbound, no cargo declared</i>.<a id="r1" href="notes.xhtml#n1" epub:type="noteref"><sup>1</sup></a>'
            if i == 3 and k == 4: body += f'<h2 id="c3b">The clerk</h2>'
            body += f'<p class="x" style="color:green" onclick="window.pwned=2">{p}</p>'
        if i == 5: body += '<p>More about tides at <a href="https://example.com/tides">a made-up page</a>.</p>'
        files[f'OEBPS/text/ch{i}.xhtml'] = page(name, body)
    files['OEBPS/text/notes.xhtml'] = page('Notes', '<h1>Notes</h1><p id="n1">1. Pencil fades faster than ink. <a href="ch3.xhtml#r1">Back</a></p>')
    nav = ''.join(f'<li><a href="ch{i}.xhtml">{n}</a>' + ('<ol><li><a href="ch3.xhtml#c3b">The clerk</a></li></ol>' if i == 3 else '') + '</li>'
                  for i, n in enumerate(CHAPTERS, 1)) + '<li><a href="notes.xhtml">Notes</a></li>'
    files['OEBPS/text/nav.xhtml'] = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html><html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"><head><title>Contents</title></head>
<body><nav epub:type="toc" id="toc"><h1>Contents</h1><ol>{nav}</ol></nav></body></html>"""
    pts = ''.join(f'<navPoint id="p{i}" playOrder="{i}"><navLabel><text>{n}</text></navLabel><content src="text/ch{i}.xhtml"/></navPoint>' for i, n in enumerate(CHAPTERS, 1))
    files['OEBPS/toc.ncx'] = f"""<?xml version="1.0" encoding="utf-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1"><head/><docTitle><text>The Salt Ledger</text></docTitle><navMap>{pts}</navMap></ncx>"""
    man = ''.join(f'<item id="ch{i}" href="text/ch{i}.xhtml" media-type="application/xhtml+xml"/>' for i in range(1, 6))
    spine = ''.join(f'<itemref idref="ch{i}"/>' for i in range(1, 6))
    files['OEBPS/content.opf'] = f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
<dc:identifier id="uid">made-up-salt-ledger</dc:identifier><dc:title>The Salt Ledger</dc:title><dc:creator>M. A. Invented</dc:creator><dc:language>en</dc:language></metadata>
<manifest><item id="nav" href="text/nav.xhtml" media-type="application/xhtml+xml" properties="nav"/><item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
<item id="cover" href="text/cover.xhtml" media-type="application/xhtml+xml"/><item id="cimg" href="images/cover.jpg" media-type="image/jpeg" properties="cover-image"/>
<item id="himg" href="images/harbour.jpg" media-type="image/jpeg"/><item id="css" href="css/book.css" media-type="text/css"/>{man}
<item id="notes" href="text/notes.xhtml" media-type="application/xhtml+xml"/></manifest>
<spine toc="ncx"><itemref idref="cover"/>{spine}<itemref idref="notes"/></spine></package>"""
    files['META-INF/container.xml'] = """<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>"""
    with zipfile.ZipFile(OUT, 'w') as z:
        z.writestr(zipfile.ZipInfo('mimetype'), 'application/epub+zip')  # stored, first, as the format asks
        for k, v in files.items(): z.writestr(k, v, compress_type=zipfile.ZIP_DEFLATED)
    print('wrote', OUT, os.path.getsize(OUT), 'bytes')


if __name__ == '__main__':
    main()
