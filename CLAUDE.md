# Subtext: notes for Claude

Subtext is a vocabulary flashcard app: a single-file web app (PWA) installed on the owner's Android phone. Every card has a **word**, a **scene** (where the word was met), one or more **definitions**, **tags**, and a **source** page.

This repo is the app. `main` is published by GitHub Pages at https://hexnix.github.io/subtext/, so **merging into `main` is what ships a new version** to the phone.

## Who you're working with

- **The owner is not a programmer.** They have good intuition and a clear eye for design.
  - Explain in plain words what changed and what they'll see on the phone. No code talk unless asked.
  - End with one clear action (usually "merge the pull request").
- **Visual choices come with previews first.** For anything judged by looking (fonts, sizes, spacing, layouts, icons, wording on screen):
  - show numbered options as phone-sized screenshots of the real app with the test cards (see Testing);
  - let them pick or tweak ("option 3, 1px smaller"), then build;
  - never commit to a look on your own.
- **Ask when a request is ambiguous and the build is big.** Read their answers carefully, including answers that weren't one of your options.
- **Never:**
  - ask for or handle GitHub tokens or passwords;
  - tell them to clear the app's site data or storage (it deletes all their cards);
  - commit their real cards, screenshots or backup zips. **This repo is public.** Test only with `tools/app-test/fixtures/test-library.zip`.

## What happens where

- **App changes** (screens, gestures, look, import/export, storage) happen here, in cloud sessions on this repo.
- **Card work** (adding vocabulary, definition text, tags, sources, import zips) happens in the owner's Claude chat project, which can reach the screenshots on their Mac. It can't be done from this repo.
- If an app change adds or changes a card field, say so in the pull request, so the card side can be updated to use it.

## Files

- `index.html`: everything. CSS in one `<style>`, all code in one `<script>` that runs as a single closure `(() => { … })()`. About 130 KB: grep for section markers (`/* ===== … ===== */`) and function names, then read only the parts you need.
- `sw.js`: the service worker that keeps the app working offline.
- `manifest.webmanifest`, `icon-192.png`, `icon-512.png`, `maskable-512.png`, `apple-touch-icon.png`.
- `tools/app-test/`: the phone-view test kit (not part of the app; the service worker never loads it).

**Outside libraries** (loaded only when needed):
- From cdnjs: JSZip 3.10.1 (backup and import) and pdf.js 3.11.174 (magazine pages; its worker is made from a blob URL fetched through the service worker).
- From Google Fonts: IBM Plex Mono (300/400/500/600, 400 italic) and Merriweather (300/700 with italics).
- `sw.js` caches the app's own files plus `fonts.googleapis.com`, `fonts.gstatic.com` and `cdnjs.cloudflare.com`. A new outside host must be added there, or it won't work offline.

**Service worker (`sw.js`):**
- `VERSION = 'subtext-vN'`. **Bump it with every change to `index.html`.** A new VERSION is what makes phones take the update.
- The app's own files are served from the cache and refreshed from the network in the background. After a merge, the first open fetches the new version and the next open shows it.

## Storage

IndexedDB database `subtext`, version 1, with four stores:

| Store | Key | Holds |
|---|---|---|
| `decks` | `id` | `{id, name, sort, createdAt, coverId?, coverCard?, subs?, srcNames?, srcHidden?}` |
| `cards` | `id`, index `deckId` | see the card fields below |
| `blobs` | `id` | `{id, blob}`: every image, thumbnail and PDF |
| `meta` | `k` | flags: `seeded`, `reviewRules2` |

- `localStorage` only remembers small things, such as `hinted2` (the first-run gesture hint has been seen).
- Adding a store means a database version bump plus an upgrade step. **Never drop or rewrite the owner's data.** They have hundreds of cards on the phone and only a backup zip.

**Card fields:**
- `id` (`imp-<timestamp of the first definition screenshot>` for imported cards), `deckId`, `seq`, `word`, `addedAt`.
- `shotAt` and `sceneTime`: drive the deck order.
- Scene:
  - `frameId`: the scene image blob; `thumbId`: its 560-px JPEG thumbnail. Only thumbnails are made smaller; images keep their original size.
  - `sceneText: {paras}`: an article as text. `**bold**`, `*italic*`, `==the word==`; a paragraph starting `# ` is a heading.
  - `sceneCaption`: a short subtitle cue under a video frame, with `==word==` and `\n` for line breaks.
  - `pdf: {id: 'pdf-<key>', page, w, h, marks: [[x0, y0, x1, y1], …]}`: a magazine page (marks are fractions of the page). One PDF blob can be shared by several cards.
- Definitions:
  - `defIds[]`: definition images, `''` when a definition is text only. `defId` is `defIds[0]`, kept for old code.
  - `defText[]`, one entry per definition:
    - `null`: show the image;
    - `{src, kind, blocks: [...]}`: text blocks (`headword`, `meta`, `pron`, `rule`, `def`, `ex`, `list`, `words`, `heading`, `p`, `label`, `quote`, `tag`);
    - `{src, kind: 'youtube', video: {vid, title}}`: a video explaining the word. Shows the thumbnail (the definition image) and title, and opens the video when tapped.
- Source (swipe down): `ref`, one of `{kind: 'transcript', lines: [{text, hit?}]}`, `{kind: 'video', vid, t, title, thumbId?}`, `{kind: 'article', title, site, url}`.
- `tags[]`: stored in path order.
- Review: `review` (marked for review), `streak`, `peeks` (times the meaning was opened), `seen`, `lastSeen`.
- `sceneKind(c)`: `pdf` if `c.pdf`, otherwise `art` if `sceneText`, otherwise `img` (with a caption if `sceneCaption`).

## Screens

- **Home:** "Your decks", a grid with the newest deck first.
  - Each tile has a cover (a chosen photo, a chosen card, or the deck's first card) and "N cards · N to review".
  - The ⋯ menu on a tile: Study, Add cards, Browse cards, Rename, Cover image, Merge into another deck, Delete deck.
  - **Merge into another deck** (`mergeSheet` / `doMerge`, v18) moves every card (tags, review marks and progress kept) into a chosen deck or a new one, then removes the empty deck.
  - **Decks are kinds of content, not sources.** All vocabulary lives in one deck, "Vocabulary"; the source (show, film, channel, book) is in the tags. The owner plans to grow Subtext into a place to find anything in their digital life, with more decks over time (a finance tracker, concepts with detailed explanations, pictures and files).
  - The top ⋯ menu is Backup: "Back up everything" (one zip), "Import a backup", "Remove screenshots behind text".
  - Search covers words, meanings and tags; tapping a tag in the study view opens search pinned to that tag. The search bar (v20) is one grey pill: Back, the pinned tags as soft-blue filled chips (tap one to remove it), the field, and × to clear all.
- **Deck pages (v19–v20):** tapping a deck tile opens its decks (page 2), then a deck's cards (page 3), then the study view; Back steps out one page at a time (`openDeck`, `pages`, `renderPage`).
  - **Page 2** shows tiles only (no list view). Two kinds of deck, newest activity first:
    - **Sources** (`sourcesOf` / `srcOf`), automatic from tags: a show, film or book by its name tag; all YouTube cards as "YouTube"; articles and magazines as "Articles".
    - **Decks the owner makes** (`d.subs = [{id, name, cards: [ids], createdAt}]`): a fixed list of cards, made from search ("Create deck" beside the result count, `deckFromSearch`) or from selected cards ("Add to deck › New deck…"). New matching cards don't join on their own.
    - Each tile's ⋯ (`srcMenu`): "Rename", "Delete deck only" (cards stay; a source is hidden via `d.srcHidden`, a renamed source is in `d.srcNames`), "Delete deck and cards" (asks first).
    - A deck with one source, nothing made and nothing hidden, skips page 2.
  - **The top bar** (v21, `pageBar`) on pages 2 and 3: "<", then the title (20px), locked at the top while the page scrolls (a hairline appears under it once scrolled). The count ("7 decks · 22 cards", "2 cards · order of appearance") sits just below and scrolls away. While selecting, the bar becomes "× N selected ⋯".
  - **Names in parts:** a deck made from tags is named "The 48 Laws of Power · Law 1" by default. Its tile reads "The 48 Laws of Power | Law 1"; page 3's bar shows "The 48 Laws of Power" with a small "Law 1" tag beside it (`nameHTML`, `pageBar`). This applies to any name with " · ".
  - **Page 3, a deck's cards:** a gallery, two across, no other view; the sort icon at the top right, the sort in grey under the title. **Hold a card** to select: small boxes appear on every card (selecting only repaints the boxes and the bar, `paintSel`, so nothing flickers); the bar shows × , "N selected" and ⋯ (`selMenu`): Select all, Add to deck, Move to deck and Remove from deck (in a made deck), Mark for review / Clear review mark, Delete cards.
  - **Sort** (`SORTS`, `storySort`, `sortOf`): "Order of appearance" only when every card (in a source or a made deck) is from one show, film, book or YouTube video (episode then `sceneTime`; a book by `shotAt`, which follows reading order; one video by `ref.t`), otherwise newest first. Also Newest first, Oldest first, A to Z. A choice sticks per deck and source (`localStorage` `sort.<deckId>.<sourceKey>`).
  - The study view opened from page 3 shows exactly that page's cards in that order (`openStudy(d, id, order)`); no review-first.
- **Browse cards:** a thumbnail grid. Select lets the owner move or delete cards; tapping a card opens a preview sheet.
- **Study view**, the heart of the app:
  - The header band has the word (hold it to rename), ✎ (the edit menu) and tags. The footer band has "i / n" and the blue "Review" mark.
  - Pages sit in the band between them (`.stage`, sized by `--hd` / `--ft`).
  - Layers: `-1` is the source page, `0` the scene, `1…n` the definitions. `openLevel` / `openRef` / `go` / `beginMove` / `dragMove` / `finishMove` move between them. The incoming page's content starts right at the band edge and follows the finger 1:1; the outgoing page fades.
  - Swipe left or right changes card.
  - **A single tap does nothing.** The old "bare mode" was removed on purpose. Double-tap or pinch zooms the scene; a PDF page zooms and scrolls.
  - **Hold** the scene or a definition to mark or unmark it for review. Opening the meaning only counts a "peek"; it never marks a card by itself.
  - ✎ edit menu (`studyEditSheet`): Replace scene/definition image, Add tag, Mark for review, Delete card.
  - Tags show in path order (category, source, episode, chatbot product; `tagRank`). Three are visible and the rest sit behind a **"+N ›"** text link (`‹` when open). Hold a tag to show a × on each plus a **+** pill to add one; tapping a tag opens search for it.
- **Deck order** (`defaultOrder` / `buildOrder`): a deck that is mostly TV or Movie cards **from one show or film** goes by episode (the `S01 E03` tag), then `sceneTime`. Other decks, including a mixed deck like Vocabulary, show the newest `shotAt` first. Cards marked for review always come first.
- **Android Back button:** every overlay (sheet, study view, page layer, search) calls `pushLayer(onPop)` and closes through `back()`, so Back undoes one step at a time. New overlays must do the same.
- **UI helpers:** `sheet(html, actions)` for bottom sheets (with `item(...)` rows), `askSheet({...})` for one line of text (a floating card: grey field with a blue underline, "Cancel" / blue text button), `toast(msg)`, `progressSheet` / `progress`.
- **The keyboard** doesn't resize the page on Android; `--kb` (from `visualViewport`) lifts every sheet above it.
- **No pull-to-refresh** (`html{overscroll-behavior:none}`, and pages are always a pixel scrollable): a reload dropped the owner on the home screen.

## Import and export

The only way cards get in and out of the app.
- A zip holds `manifest.json` plus images: `{app: 'subtext', version: 1, decks: [{id?, name, cover?, coverCard?, cards: [...]}]}`.
- A card is matched **by id**, never by word. A new card needs a `scene` plus `definition(s)`.
- For an existing card, only the fields present change: `word`, `tags`, `reference` (null removes it), `definitionText`, `shotAt`, `sceneTime`, `sceneText`, `sceneCaption`, `pdf` (null removes any of these). `update: 'scene'` replaces only the scene image; `update: true` replaces everything.
- Both update modes skip cards that are already identical, so re-importing reports "already up to date". Review progress is always kept.
- A deck is found by id, then by name, and created only if a new card needs it.
- Export writes the same format, so a backup is also an import file.
- A deck entry may also carry `subdecks: [{id, name, cards: [card ids], createdAt}]`, `sourceNames: {key: name}` and `hiddenSources: [keys]` (v20). Import only adds what's missing, never undoes a change made in the app.
- **Rules:** never break older zips or backups. New fields are optional. An import must be safe to repeat.

## Design system (keep it unless the owner changes it)

**Colours:**
- Black background, white text, grey only for secondary text (`--muted #8D9096`, `--faint`).
- One accent: blue `#0086FF`, with lighter `#4DA8FF` for blue text on black. The CSS variable is named `--gold` for historical reasons; it is blue.
- Allowed exceptions: the **magenta** highlight of the word in article text (`#84024C` background), and the pink box on magazine PDF pages (`rgba(214,18,122,.3)` with a `#E0187F` outline).
- No other colours.

**Fonts:**
- **IBM Plex Mono** for the whole interface (`--sans` and `--serif` both point to it).
- **Merriweather** only for reading text: article scenes (300, 16px/1.66, `#E4E4E4`) and video titles on source and definition pages (light italic 16px/1.6, `#D8D8D8`, 22px side padding).

**Components:**
- **YouTube source page:** thumbnail, then title. No "starts at 12:34" label, no blue line.
- **Video scene subtitle cue:** a clean frame with **no text on the picture**. A short one- or two-line cue (never a full sentence) goes **under** the frame: Plex Mono Light 14px, 18px below the frame, centred, balanced lines, `#E4E4E4`; the word in `#4DA8FF` with no background; no timestamp. Chosen from about 20 previews ("Style M2"); don't reopen it casually.
- **Tags:** blue outlined pills (1px blue border, blue text); the extra-tags control is a plain "+N ›" text link. The owner disliked a dotted-border version.
- **Definition text** (`.dtext`, Plex Mono 15px): headword 34px blue; examples italic blue; rules and headings with light dividers.

**Motion:** pages follow the finger and settle with an ease-out; no gimmicks. A tap never does anything unexpected. Haptic buzz on long-press actions.

**Tone:** minimal and elegant. Black space, few words, no badges or clutter. Plain-English labels ("Marked for review", "Import a backup").

## Making a change

1. **Restate the request** in one or two plain sentences. Settle any open design choice with numbered phone-sized previews.
2. **Work on a new branch.** Make small, targeted edits to `index.html`. Keep the code's style: short plain-English comments that say *why*. Reuse existing CSS variables and components instead of inventing new ones.
3. **Bump `VERSION`** in `sw.js` to `subtext-v(N+1)`.
4. **Test on a phone-sized view** (below), and look at the screenshots yourself.
5. **Open a pull request** with a plain-English description:
   - what changed and what the owner will see;
   - what to try on the phone;
   - whether card data needs updating (new or changed card fields).
6. **Tell the owner:** "Merge the pull request on GitHub. After a minute, open the app, close it, and open it again to see the new version."

## Testing

The kit in `tools/app-test/` runs the app in a 412×915 phone view with Playwright. It works offline: JSZip, pdf.js and the fonts are in the kit.

```bash
pip install playwright --break-system-packages   # if missing; Chromium is usually preinstalled
python3 tools/app-test/harness.py . --zips tools/app-test/fixtures/test-library.zip --out shots/
```

- The smoke test imports the test library, then screenshots home, a scene, its meaning and its source, and the next card, and reports any JavaScript errors.
- **The test library** has 6 made-up cards in two decks covering every scene, definition and source kind: `test-candor`, `test-brusque` (marked for review; two definitions), `test-reticent`, `test-ephemeral` (article text), `test-palimpsest` (magazine PDF), `test-heuristic` (YouTube source and video definition).
- For a specific change, write a short script with `from harness import Phone` (see the docstring in `harness.py`: `imp`, `open_card`, `open_deck`, `swipe`, `hold`, `back`, `level`, `shot`, and `window.T` for the app's internals).
- Always check: the Back behaviour, re-importing the zip reports "already up to date", and there are no JavaScript errors.
- Merriweather italics look upright in test screenshots (the test font has no true italic); the phone shows real italics.
- Don't commit `shots/`.
- **When the app learns a new card field,** add a card using it to `tools/app-test/make_test_library.py` and rebuild the zip (`python3 tools/app-test/make_test_library.py`).

## Things that bite

- **The script is one closure**, so its functions aren't reachable from the page console. The harness patches in `window.T` for tests; never ship that patch.
- **Tests run with service workers blocked.** For a change to `sw.js` itself, reason carefully about how an update rolls out: phones keep the old cache until they get the new VERSION.
- **Replacing an image:** store the new blob, point the card at it, then `forget(oldIds)`. PDFs are shared, so use `dropPdf(id)`, which only deletes a PDF no card uses.
- **Anything slow belongs in the background.** Keep the study view smooth: preload the next card (`preload`), render PDFs lazily.
- **Target:** Android Chrome, installed as an app. Respect safe-area insets, use `pointer` events (not mouse), keep pinch and double-tap working.
- **No sample card:** the start-up code looks for `sample/frame.jpg` and `sample/definition.jpg`, which aren't in the repo, so a fresh install starts empty (it logs "sample skipped"). That's expected.

## Version notes

- **v12–v16:** article scenes as text; magazine PDF scenes; YouTube frames with a cue below; tags in path order with "+N ›"; Add tag; source page title style.
- **v17:** video definitions (`defText` entry `{kind: 'youtube', video: {vid, title}}`); `update: true` skips identical cards.
- **v18:** "Merge into another deck" in the deck ⋯ menu; story order only for a deck of one show or film.
- **v19:** deck pages: tapping a deck opens its sources (tiles or list), then a source's cards (gallery, pinch for two or three across, or a compact list) with a remembered sort; Back steps out one page at a time.
- **v20:** decks made from search or selected cards; ⋯ on page 2 decks (Rename, Delete deck only, Delete deck and cards); hold to select cards on page 3; page 2 tiles only and page 3 gallery only (no pinch); names in parts ("A · B"); new search bar; name box as a floating card above the keyboard; no pull-to-refresh.
- **v21:** page titles sit beside "<" in a bar locked at the top; selecting cards no longer flickers (loaded pictures show at once on any redraw).

Add a line here with every version you ship.
