# Agora: notes for Claude

Agora (called Subtext until v22) is a vocabulary flashcard app: a single-file web app (PWA) installed on the owner's Android phone. Every card has a **word**, a **scene** (where the word was met), one or more **definitions**, **tags**, and a **source** page. Since v23 it is also a file manager for the phone's **My Files** folder, with the same tags and search (see "My Files").

This repo is the app. `main` is published by GitHub Pages at https://hexnix.github.io/agora/, so **merging into `main` is what ships a new version** to the phone.

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
- `tools/app-test/`: the phone-view test kit (not part of the app; the service worker never loads it). `test_files.py` tests My Files, `test_study.py` the Study deck, `test_player.py` the video player.

**Outside libraries** (loaded only when needed):
- From cdnjs: JSZip 3.10.1 (backup and import) and pdf.js 3.11.174 (magazine pages; its worker is made from a blob URL fetched through the service worker).
- From Google Fonts: IBM Plex Mono (300/400/500/600, 400 italic) and Merriweather (300/700 with italics).
- `sw.js` caches the app's own files plus `fonts.googleapis.com`, `fonts.gstatic.com` and `cdnjs.cloudflare.com`. A new outside host must be added there, or it won't work offline.

**Service worker (`sw.js`):**
- `VERSION = 'agora-vN'`. **Bump it with every change to `index.html`.** A new VERSION is what makes phones take the update.
- The app's own files are served from the cache and refreshed from the network in the background. After a merge, the first open fetches the new version and the next open shows it.

## Storage

IndexedDB database `subtext` holds the cards. It keeps the app's old name on purpose: renaming it would leave every saved card behind. **It is opened without a version number and is never upgraded** (v24): an upgrade waits until every other copy of Agora lets go of the database, and an older copy left in a background Chrome tab never does, so v23 (which upgraded it to version 2) opened to a black screen. On the phone it may be at version 1 or 2; both open the same way. New kinds of data get **their own database** instead.

| Store | Key | Holds |
|---|---|---|
| `decks` | `id` | `{id, name, sort, createdAt, coverId?, coverCard?, subs?, srcNames?, srcHidden?}` |
| `cards` | `id`, index `deckId` | see the card fields below |
| `blobs` | `id` | `{id, blob}`: every image, thumbnail and PDF (My Files thumbnails are `ft-…`) |
| `meta` | `k` | flags: `seeded`, `reviewRules2` |
| (`files`) | `path` | only in a database v23 upgraded: its My Files index, copied once into `agora-files` and no longer used |

IndexedDB database `agora-files` (v24), version 1, holds My Files: store `files` (key `path`, the index, see "My Files") and store `meta` (key `k`: `filesRoot` `{h}` the folder handle, `fileTagsPending` `{v: [entries]}` tags of files not found right now, `moved` the v23 index has been copied over). It loads after the decks are on screen, so My Files can never hold them up.

IndexedDB database `agora-history` (v27), version 1, holds History: store `visits` (key `id`, the card's id): `{id, at, ans?, ansAt?}`, one entry per card opened in the study view (`ans`: New, Repeat, Tomorrow or Pass when it was studied that day). Not in backups. It loads after the decks are on screen.

IndexedDB database `agora-notes` (v29), version 1, holds Notes (see "Notes"): store `notes` (key `id`, `n-…`): `{id, title, html, imgs: [picture ids], createdAt, updatedAt}`; store `images` (key `id`, `ni-…`): `{id, blob}`, each picture at its original size plus a 480-px copy `<id>-t` for the list. It loads after the decks are on screen.

IndexedDB database `agora-study` (v25), version 1, holds Study progress (see "Study"): store `cards` (key `id`, the card's id): `{id, step, due, first, last, at, done?}` for a card studied at least once, or `{id, front, at}` for a new card brought to the front of the queue; store `meta` (key `k`): `daily` `{v}` new cards a day (default 20), `extra` `{day, n}` more new cards asked for today. Days are whole local days starting at 4 am (`dayNo`). It loads after the decks are on screen.

IndexedDB database `agora-bookmarks` (v30), version 1, holds Bookmarks: store `marks` (key `id`, `bm-…`): `{id, url, title, site, tags, addedAt, at}`, or `{id, gone: true, at}` for a deleted one (so an older backup can't bring it back). It loads after the decks are on screen.

IndexedDB database `agora-media` (v37), version 1, holds the video player's memory (see "Video player"): store `videos` (key `id` = `v:<size>:<name>`, so a moved film keeps its place): `{id, name, size, path, pos, dur, at, sub}` (`sub`: the chosen subtitles, `mkv:<track number>`, `file:<path>` or `off`); store `subs` (key `k` = `<video id>|<subtitle id>`): `{k, cues: [{s, e, x}], at, mtime}`, subtitles already read, so a film's second opening shows them at once. Opened on the first film, not at start-up. Not yet in backups or the Agora folder (it holds only places and a cache; phase 2's notes will go there).

**The Agora folder** (v32, database `agora-sync`): everything above is also kept as plain files in **My Files › Agora**, the real home of the data. The databases stay as a quick-start copy, because Android forgets the folder each time the app closes (the cards must show at once, before any tap).
- Layout: `Read me.txt`; `Cards/<deck>/deck.json` (+ `cover.jpg`); `Cards/<deck>/cards.json` (v35, the owner's pick "per deck": every card of the deck, one per line, `{name, card, files: {picture: blob id}}`, the card exactly as stored); `Cards/<deck>/Pictures/<name> scene.jpg`, `<name> definition.jpg`, `<name> definition 2.jpg`…, `<name> source.jpg`. No tiles (v36): every file is a slow trip on Android, and a card brought in without its tile gets one drawn from its scene (`agCardIn` sets `thumbKey: 'redraw'`, then `refreshTiles`). `.nomedia` keeps the pictures out of the phone's Gallery. v32–v34 kept a folder per card (`Cards/<deck>/<name>/card.json` + pictures); such cards move over on the next save (`loadSync` marks them, `agCardTo` writes them anew and removes the old folder), and a new phone still reads that layout; `Magazines/<key>.pdf`; `Notes/<title>.html` (a page any browser opens; the note's details in a `<script type="application/json" id="agora-note">` block, its text in `<main id="agora-note-text">`) and `Notes/pictures/<id>.jpg`; `Bookmarks.json`, `Study progress.json`, `History.json`; `Previous versions/<YYYY-MM-DD HH.00>/<same path>` with `changes.json`.
- Every `put` / `del` on the cards', Study, History, Notes and Bookmarks databases goes through `tracked(store, db)` and marks a unit as waiting (`card:<id>`, `deck:<id>`, `note:<id>`, `study`, `history`, `marks`; `agora-sync` store `dirty`). `agFlush` writes what waits (decks, then 8 cards at a time, then the rest) whenever the folder is allowed (`agOn`), a few seconds after the last change (20 s when only Study or History changed) and when the app goes to the background. Where each unit sits is in store `paths` (`{k, dir, base, nm, label, files, sum}`; a card's has `flat: true` and `dir` = `<deck>/Pictures/<name>`); a card whose name or deck changes gets new picture names, a note a new file. A deck's `cards.json` is read once per save (`agDeckFile`), changed in memory and written every 100 cards, every 15 s and at the end (`agDeckWrite`); a card counts as saved (record kept, old pictures removed, name claim released) only once that file is written.
- **Previous versions:** before Agora changes or deletes a file there, its earlier copy goes to `Previous versions/<this hour>/` (the first copy of each hour stays), listed in that hour's `changes.json` (`{k, kind, label, what, dir, at, run, why}`; for a card also `card` and `files`, the card as it was, since cards.json itself isn't copied). Folders older than 30 days are removed (`agPrune`). Tile pictures aren't kept (they are redrawn). Restoring goes through the normal saving, so what it replaces is kept in turn.
- **Linking** (`agLink`, the first time a folder is connected, store `meta` `linked`): what the folder already has comes in first (`agMerge`: cards and decks the phone lacks, newer study, history, bookmark and note records), then everything is checked against the folder and written where it differs. So a new phone needs only Agora installed and My Files chosen. The Agora folder is left out of the My Files list and search.
- The old databases are never removed: they are the quick-start copy.
- `localStorage` only remembers small things under `agora.` keys (older `subtext.` keys are still read), such as `hinted2` (the first-run gesture hint has been seen), `files.view` (`list` / `grid`) and `files.sort`.
- **Never upgrade `subtext`** (no version bump, no new stores there). A new kind of data gets a new database of its own, opened after the decks are on screen. **Never drop or rewrite the owner's data.** They have over a thousand cards on the phone and only a backup zip.
- If the cards' database takes more than 2.5 s to open, the home screen says "Opening your cards… If Agora is also open in a Chrome tab, close that tab and Agora will carry on." instead of staying black.

**Card fields:**
- `id` (`imp-<timestamp of the first definition screenshot>` for imported cards), `deckId`, `seq`, `word`, `addedAt`.
- `shotAt` and `sceneTime`: drive the deck order.
- Scene:
  - `frameId`: the scene image blob; `thumbId`: its tile picture (a 560-px JPEG). Only thumbnails are made smaller; images keep their original size.
  - `thumbKey` (v27, kept on the phone, not in backups): what the tile was drawn from when the scene is article text or a magazine page. A tile that doesn't match its scene is redrawn in the background (`refreshTiles`: text as text, a magazine page around its pink box, else from the screenshot), after start-up and after every import.
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
- **The card's name** (`nameOf`, v27): the headword of its first text definition, shown everywhere (study header, tiles, the queue, History, search). A word typed in the app (hold the title, or Edit word) wins and sets `named` (kept on the phone, not in backups). Search finds a card by its name and by its stored `word`.
- Review: `peeks` (times the meaning was opened), `seen`, `lastSeen`. The old `review` mark and `streak` stay in the data (and in backups) but the app no longer shows or uses them (v25); Study progress lives in `agora-study`, not on the card.
- `sceneKind(c)`: `pdf` if `c.pdf`, otherwise `art` if `sceneText`, otherwise `img` (with a caption if `sceneCaption`).

## Screens

- **Home:** "Your decks", a grid with the newest deck first.
  - Each tile has a cover (a chosen photo, a chosen card, or the deck's first card) and "N cards". Vocabulary (`studyDeck`) shows its logo instead, a white "A" with a blue "a" (`LOGO_VOCAB`, v26), and its ⋯ has no "Cover image".
  - The ⋯ menu on a tile: Study, Add cards, Browse cards, Rename, Cover image, Merge into another deck, Delete deck.
  - **Merge into another deck** (`mergeSheet` / `doMerge`, v18) moves every card (tags, review marks and progress kept) into a chosen deck or a new one, then removes the empty deck.
  - **Decks are kinds of content, not sources.** All vocabulary lives in one deck, "Vocabulary"; the source (show, film, channel, book) is in the tags. The owner plans to grow Agora into a place to find anything in their digital life, with more decks over time (a finance tracker, concepts with detailed explanations, pictures and files).
  - The title "Your decks" is 24px, weight 500 (v27, pick 1C), at the same height as every page title with its count right under it (v28).
  - The top ⋯ menu is Backup: "Back up everything" (one zip), "Import a backup", "Previous versions" (once the Agora folder is set up), "Remove screenshots behind text".
  - **The Agora folder line** (v32, `agLine`, under the count): "• Keep everything in My Files · tap to start" before the first copy; "Saving to My Files · 120 of 1,040" while writing; "• Save to My Files · N changes waiting" when the folder needs a tap again (Android, after a reopen). Nothing when all is saved.
  - **Previous versions** (v32, the owner's pick 2A + 2B with a toggle, `renderVersions`): grouped by day; each item that changed (its picture, "Card · tags changed", the time) or, with the toggle, each moment (one save: "Imported a backup", "Deleted 3 cards", the items, "Restore all"). Tapping one asks, then restores. A card (✎ menu), a note (⋯) and one selected bookmark (⋯) have their own "Previous versions" sheet (`itemVersions`).
  - Search covers words, meanings and tags; its box says "Search anything" and an empty search shows nothing (v27); tapping a tag in the study view opens search pinned to that tag. The search bar (v20) is one grey pill: Back, the pinned tags as soft-blue filled chips (tap one to remove it), the field, and × to clear all.
- **Deck pages (v19–v20):** tapping a deck tile opens its decks (page 2), then a deck's cards (page 3), then the study view; Back steps out one page at a time (`openDeck`, `pages`, `renderPage`).
  - **Page 2** shows tiles only (no list view). Two kinds of deck, newest activity first:
    - **Sources** (`sourcesOf` / `srcOf`), automatic from tags: a show, film or book by its name tag; all YouTube cards as "YouTube"; articles and magazines as "Articles".
    - **Decks the owner makes** (`d.subs = [{id, name, cards: [ids], createdAt}]`): a fixed list of cards, made from search ("Create deck" beside the result count, `deckFromSearch`) or from selected cards ("Add to deck › New deck…"). New matching cards don't join on their own.
    - Each tile's ⋯ (`srcMenu`): "Rename", "Delete deck only" (cards stay; a source is hidden via `d.srcHidden`, a renamed source is in `d.srcNames`), "Delete deck and cards" (asks first).
    - A deck with one source, nothing made and nothing hidden, skips page 2.
    - **Search inside a deck** (v28): the first page a deck opens on (page 2, or page 3 when page 2 is skipped) has a search icon. It opens the usual search limited to that deck's cards (`openSearch(pins, deck)`): "Search Vocabulary", "N cards in Vocabulary", each row showing the card's tags instead of the deck name, no files. My Files (every folder page) and Notes have the same icon (v31, `openSearch(null, null, 'files' | 'notes')`): "Search My Files" finds only files and folders; "Search Notes" matches a note's title and every line in it and shows rows like the Notes page (`noteSearch`). Bookmarks has its own search on its page.
  - **The top bar** (v21, `pageBar`) on pages 2 and 3: "<", then the title (20px), locked at the top while the page scrolls (a hairline appears under it once scrolled). The count ("7 decks · 22 cards", "2 cards · order of appearance") sits right under the title, starting where the title's text does (32px in; v27, pick 2A), and scrolls away. The same goes for Study, New cards, History and My Files folders (the path line too). While selecting, the bar becomes "× N selected ☑ ⋯".
  - **Select all is an icon** (v28, the owner's pick 1): a box with a tick (`ICON_ALL`, `allBtn`) in the selection bar of every page that selects (a deck's cards, My Files, New cards, History, Browse cards, Notes). It turns solid blue when everything is selected, and a tap then clears the selection (`toggleAll`, `selPool`). It is no longer in the ⋯ menus. In New cards with a search open, it sits on the count line until a card is selected.
  - **Names in parts:** a deck made from tags is named "The 48 Laws of Power · Law 1" by default. Its tile reads "The 48 Laws of Power | Law 1"; page 3's bar shows "The 48 Laws of Power" with a small "Law 1" tag beside it (`nameHTML`, `pageBar`). This applies to any name with " · ".
  - **Page 3, a deck's cards:** a gallery, two across, no other view; the sort icon at the top right, the sort in grey under the title. **Hold a card** to select: small boxes appear on every card (selecting only repaints the boxes and the bar, `paintSel`, so nothing flickers); the bar shows × , "N selected" and ⋯ (`selMenu`): Select all, Add to deck, Move to deck and Remove from deck (in a made deck), Delete cards.
  - **Sort** (`SORTS`, `storySort`, `sortOf`): "Order of appearance" only when every card (in a source or a made deck) is from one show, film, book or YouTube video (episode then `sceneTime`; a book by `shotAt`, which follows reading order; one video by `ref.t`), otherwise newest first. Also Newest first, Oldest first, A to Z. A choice sticks per deck and source (`localStorage` `sort.<deckId>.<sourceKey>`).
  - The study view opened from page 3 shows exactly that page's cards in that order (`openStudy(d, id, order)`); no review-first.
- **My Files** (v23): see "My Files" below. Its tile sits after the decks, before "New deck".
- **Bookmarks** (v30, the owner's picks 1, A, C): a tile after the decks, before My Files, with its logo (a white page with a solid blue ribbon, `LOGO_MARKS`) and "N bookmarks".
  - **Sharing a link in:** `manifest.webmanifest` has a `share_target` (GET, `./?title=…&text=…&url=…`), so Agora is in Android's share menu. `SHARED` reads the link (from `url` or inside `text`) and clears the address; `takeShared` opens the Bookmarks page and the save sheet.
  - **The save sheet** (`markSheet`): the title (a YouTube link without one gets it from YouTube's oEmbed when online), the tags, "Add a tag", then "Your tags". Suggested tags (`suggestTags`: the site's own tag from `SITES`, the tags that site's earlier links got, tags in use that the title or link mentions) **start out added** (pick C), so saving in a hurry is one tap. Sharing a saved link again edits it ("saved on …"), never a copy.
  - **The page** (`renderMarks`, kind `marks` in `pages`): "N bookmarks · newest first"; tools: search inside Bookmarks, the list/grid toggle (`marks.view`), ⋯ (Add a link, Select bookmarks). **List** (pick A): a 56-px picture (a YouTube link shows its video's picture from i.ytimg.com, other links a grey link glyph), the title on up to two lines, "site · 2 Oct", up to two tag pills and "+N". **Grid**: two across, the site's name on links without a picture, tags as blue text.
  - Tapping a bookmark opens its link. Hold to select; the bar has the select-all icon, and ⋯ (`markSelMenu`): Edit (one), Add tags, Share, Delete.
  - The main search lists bookmarks after the cards and files (title, link, pinned tags).
- **Notes** (v29): see "Notes" below. Its tile sits after My Files.
- **Browse cards:** a thumbnail grid. Select lets the owner move or delete cards; tapping a card opens a preview sheet.
- **Study view**, the heart of the app:
  - The header band has the word (hold it to rename), ✎ (the edit menu) and tags. The footer band has "i / n".
  - Pages sit in the band between them (`.stage`, sized by `--hd` / `--ft`).
  - Layers: `-1` is the source page, `0` the scene, `1…n` the definitions. `openLevel` / `openRef` / `go` / `beginMove` / `dragMove` / `finishMove` move between them. The incoming page's content starts right at the band edge and follows the finger 1:1; the outgoing page fades.
  - Swipe left or right changes card.
  - **A single tap hides the header and footer** (word, ✎, tags, "i / n"); the next tap brings them back (v26, `.study.bare`, set in `handleTap` 320 ms after the tap so a double tap isn't mistaken for it). The pages don't move or grow: they stay in the band between where the header and footer were. It lasts across cards until tapped again; Study's answer buttons stay. Double-tap or pinch zooms the scene; a PDF page zooms and scrolls.
  - Holding the scene or a definition does nothing (the hold-to-mark-for-review was removed in v25). Opening the meaning only counts a "peek".
  - ✎ edit menu (`studyEditSheet`): Replace scene/definition image, Add tag, Delete card.
  - Opened from a deck page, search or the queue, the study view is for looking only: it never moves a card along its Study cycle.
  - Tags show in path order (category, source, episode, chatbot product; `tagRank`). Three are visible and the rest sit behind a **"+N ›"** text link (`‹` when open). Hold a tag to show a × on each plus a **+** pill to add one; tapping a tag opens search for it.
- **Deck order** (`defaultOrder` / `buildOrder`): a deck that is mostly TV or Movie cards **from one show or film** goes by episode (the `S01 E03` tag), then `sceneTime`. Other decks, including a mixed deck like Vocabulary, show the newest `shotAt` first.
- **Android Back button:** every overlay (sheet, study view, page layer, search) calls `pushLayer(onPop)` and closes through `back()`, so Back undoes one step at a time. New overlays must do the same.
- **UI helpers:** `sheet(html, actions)` for bottom sheets (with `item(...)` rows), `askSheet({...})` for one line of text (a floating card: grey field with a blue underline, "Cancel" / blue text button), `toast(msg)`, `progressSheet` / `progress`.
- **The keyboard** doesn't resize the page on Android; `--kb` (from `visualViewport`) lifts every sheet above it.
- **No pull-to-refresh** (`html{overscroll-behavior:none}`, and pages are always a pixel scrollable): a reload dropped the owner on the home screen.

## Study (v25)

The spaced-repetition deck. It sits inside the deck named **Vocabulary** (`studyDeck`), as a wide banner (the owner's pick 1B) above the sources on its page; Vocabulary always opens on that page.
- **The cycle:** a card is new, waiting in the queue and never overdue, until the day it is first studied. Then it comes back after 1, 3, 7, 14, 30, 60 and 120 days (`GAPS`), each gap counted from the day it was passed, and then it is done (`done: true`). `step` is how many gaps it has passed.
- **Each day** (A2): 20 new cards (`SD.daily`, "New cards a day" in the Study ⋯) plus every review that is due, overdue first (`studyToday`). "Learn 10 more new cards" adds 10 for today (`learnMore`, meta `extra`). A day starts at 4 am.
- **Answers** (3C, one bar under the card, each button saying when the card returns; `showAnswer` / `answer`):
  - a new card: **Continue** only ("back in 1 day"), which starts its cycle;
  - a card seen before: **Repeat** (to the end of today's list; nothing saved, its place in the cycle stays), **Tomorrow** (due tomorrow, same step), **Pass** (next step; "done" after the 120-day gap).
  - The buttons show at once, on every page of the card. In a session a card can't be swiped past (`S.drill`); up and down still open meaning and source. No gesture hint there.
- **The Study page** (2B, `renderStudyPage`): "12 of 46 left today · 1,032 new in queue", a blue Start / Continue (or "Learn 10 more new cards" when done), then today's cards in study order: done ones dimmed, the rest labelled Review or New. Tapping one starts there; a done one just opens to look at. Tools: the queue icon and ⋯ (New cards in queue, New cards a day, Learn 10 more).
- **Done for today** (`studyOver`): "N cards · N repeated", "Tomorrow: N cards", "Learn 10 more new cards".
- **History** (v27, pick 4A): the clock icon at the top right of Vocabulary's page opens every card opened in the study view, from anywhere, newest first and one entry per card, grouped by day ("Today", "Yesterday", "Monday, 28 Sep") with the time; a studied card's line starts "Studied · Pass" in blue (`renderHistory`). ⋯: Select cards, Clear the last hour, day (24 h), month (30 days), Clear all history. Hold a card to select ("× N selected · Remove", Select all on the count line). Tapping a card opens it to look at, in History's order. The cards and Study progress never change.
- **The queue** (4A + 4B, `openQueue` / `renderQueue`): every new card numbered in the order Study brings them, as a list or a grid (toggle, `queue.view`). Default order (`queueOrder`): oldest `shotAt` first, with each show's, film's or book's cards taking their places in story order (episode, then `sceneTime`). Search (words, meanings, tags; typed text suggests tags to pin), Select all, or hold a card to select (only the boxes, the bar and the count line repaint, and the count line keeps its height, so the list never moves: `paintQueueSel`, `.cline`); **Bring to front** puts them first in their order (a later batch goes ahead of an earlier one, `front`).
- **Removed in v25:** "Mark for review" (hold, ✎ menu, select menu, Browse cards' card sheet) and every blue "N to review" count; review marks no longer move cards to the front of a deck.
- **Backups** carry `study: {daily, cards: [records]}`; import takes a record only when it is newer (`at`) than the phone's, so a re-import changes nothing.

## Notes (v29)

A very simple notebook. The owner asked for only this much and will ask for more when they need it: build only what they ask for.
- **Home tile** "Notes" after My Files: logo 1A (a white page with a blue title line, `LOGO_NOTES`), "N notes". Its ⋯: New note.
- **The Notes page** (`renderNotes`, kind `notes` in `pages`; pick 2A, a list only): the locked bar "< Notes" with + (new note), "N notes · last edited first", then each note: its title (or its first line), the lines after it joined with " · " (two lines at most), the date (the time if today), and a 56-px picture when it has one. Hold a note to select (× N selected, the Select all icon, Delete, asks first).
- **Writing** (`openNote` / `renderNote`, kind `note`): a title line (22px) and the text (Plex Mono 15px/1.65, pick 3A), saved half a second after typing stops and on Back; a note left empty is never kept, and pictures taken out of a note are deleted when it closes. One row of tools above the keyboard (`ntools`, bottom `--kb`): Heading, Bold, Italic, Underline, Bullets, Numbers, Checklist (tap the box to tick), Quote, Picture; a tool lights up blue where the cursor is. Pasted text comes in plain; a pasted picture is added like a picked one. ⋯: Add a picture, Delete note. The page keeps the phone's copy and paste menu (no `contextmenu` block).
- A note's text is HTML from a short list (`cleanNoteHTML`: p, h2, b, i, u, s, ul (class `checks`), ol, li (class `done`), blockquote, img `data-img`); everything else is dropped, so an imported note can't carry a script. Chrome sometimes puts a new list inside its paragraph; `unnestLists` lifts it out.
- **Backups** carry `notes: {items: [{id, title, html, createdAt, updatedAt, images: ['notes/<picture id>.jpg']}]}` with the pictures in `notes/`. Import takes a note only when it is newer (`updatedAt`) than the phone's, so a re-import changes nothing.

## My Files (v23)

The owner keeps important files (documents, PDFs, photos, anything) in a folder called **My Files** in the phone's internal storage, in subfolders of their choosing. Agora browses it, tags files, finds them with the cards' search, and opens them.

**Rules that never change:**
- Agora **changes the owner's files only when they ask** (v32: move, rename, edit text, new folder, delete), and **every change can be undone** from Previous versions: a deleted or edited file's earlier copy goes to `Agora/Previous versions/<hour>/My Files/<path>` first; a move or rename is noted so it can be moved back. Otherwise it writes only `.agora/file-tags.json` and its own `Agora` folder (see Storage).
- **No pop-up on launch.** The app opens without touching the folder. Android asks for the folder again every time the app is reopened (`queryPermission()` says "prompt"), so only an action that needs the folder asks, with one tap: the first connect, Refresh, opening or sharing a file. The tap that opens a file is also the tap that reconnects. When Agora becomes a real Android app, that tap is the only thing that goes away.
- The **File System Access API** (`showDirectoryPicker`) is in Chrome on Android, not in Brave. Without it the file features hide and the home screen shows one line: "My Files needs Chrome: this browser doesn't let Agora open folders."

**The index** (database `agora-files`, store `files`, in memory `fidx`, written through `fstore`): `{path, kind: 'dir' | 'file', name, dir, size, mtime, ext, tags, tagsAt, thumbId, thumbKey, noThumb}`. `path` is inside the folder ("Documents/Bank/x.pdf"), `dir` the folder's path ('' for the top). Browsing and search work from the index alone, before the folder is connected.
- **Refresh** (`rescan`): walks the whole folder in the background (the count updates on the page; Chrome froze on huge folders, so nothing blocks the screen), skips hidden names (starting with "."), then `reconcile`: new, removed and changed files. A renamed or moved file keeps its tags and picture: same name + size + date, else same name + size, else same size + date (only when exactly one file matches). A tagged file that has gone is kept aside in `fileTagsPending`, so its tags come back if it does.
- **Thumbnails** (`makeFileThumbs`): 400-px JPEGs of images and of a PDF's first page, made one at a time after a refresh, the folder on screen first; originals are read only when opened or shared.
- **Tags are saved twice:** in the index at once, and in `.agora/file-tags.json` (`{app: 'agora', kind: 'file-tags', version: 1, files: [{path, name, size, mtime, tags, at, missing?}]}`), written whenever tags change while connected (`tagsChanged` → `saveTagsFile`, one small write) and read back on every connect (`readTagsFile`). In every merge (`mergeTagEntries`: the folder's copy, a backup, the set-aside list) the newer change (`at` / `tagsAt`) wins.
- **Connecting** (`connectFiles`): must run straight from a tap. The folder handle is kept in `agora-files` `meta.filesRoot`; "Choose a different folder" picks again.

**Video player** (v37, `openPlayer`, the owner's picks 1A, 3A, 4A; no speed button, at their request):
- Opening a video (`.mp4`, `.webm`, `.mov`, `.m4v`, `.3gp`, `.mkv`) from a folder or search goes straight to the player, full screen and sideways (`plFull`: Fullscreen API + `screen.orientation.lock('landscape')`; Chrome allows it only from a tap, so any tap on the film tries again). The film is a blob URL of the file itself: never copied, however big. Swiping onto a video inside the file viewer shows a Play button.
- Controls (1A): `<` and **only the file name** on top (up to two lines, then cut with …), CC and ⋯ (Share / Open with…, Show in folder); −10 s, play/pause, +10 s in the middle; the time, the seek bar (drag anywhere along it) and the length; the lock and the picture button at the bottom. A tap shows them, they fade 3.5 s later while playing. Double-tap the left or right side to skip 10 s, the middle to pause.
- **The picture** (v39, `PL_MODES`, `plApplyView`): the corner button goes Fit to screen → Crop to fill → Stretch to fill, naming each as it changes. **Pinch** zooms (50–500%) around the fingers, and moving both fingers shifts the picture; it snaps back to 100% near it. Kept per film in `agora-media` `videos` (`view: {m, z, x, y}`, x and y as fractions of the screen).
- Swipes (4A): up or down on the left half for brightness, on the right half for volume; each bar shows on the **other** side, away from the finger (v39). Both are remembered (`player.bright`, `player.vol2`).
  - **Brightness 10–200** (v39): below 100 a black layer darkens the film (a web page can't change the phone's brightness), above 100 the picture itself is brightened with a CSS `brightness()` filter, up to 2×.
  - **Volume 0–100** (v39, the owner's ask after 2× was too quiet and 4× too loud): like VLC (its Android `VolumeSet`: gain = volume³) and mpv, loudness follows the cube of the slider (`plAmp`), so the steps sound even; 100 is 3× the film's own level (+9.5 dB, `PL_AMAX`), the film's own level is at 69 (the default). Above it the sound goes through Web Audio: a gain, then a limiter (`DynamicsCompressor` at −3 dB) so loud scenes don't crackle. **The boost must not silence the film** (v38): once a video goes through Web Audio it can't come back out, and a sound context Chrome didn't start from a touch stays silent. So the context is made on a touch (`plAudioWake`, also from the tap that opens the film), and the sound moves over only once it is running; until then it plays at its own level (`boostWait`).
- **Subtitles** look like the owner's screenshot of their phone's player: Roboto (the phone's own font) 600, `4.73vmin` (19.5px when the phone is sideways), line-height 1.15, white with a soft shadow, `3.2vmin` above the bottom edge, lifted above the seek bar while the controls show. Sizes S/M/L/XL (`player.sub`). **Swipe a line left** for the next line, **right** for the one before (`plSubStep`). **Hold a line and drag it** up or down to move the subtitles (v39): two heights are kept, one while the controls show and one without (`player.suby` `{bare, ui}`, fractions of the screen's height, as `--sy0` / `--sy1`). Holding a line will later need another way to start a note (phase 2).
- Where they come from (`plSubsFound`): text tracks inside an .mkv (SRT, ASS/SSA, WebVTT), and `.srt`/`.vtt` files beside the video whose name starts with the video's name (`Film.srt`, `Film.en.srt`). Picture tracks (PGS, VobSub) are listed greyed out, with a note to put a .srt beside the film. English plain first, then SDH; never a forced-only track.
- **Reading subtitles inside an .mkv** (`mkvInfo`, `mkvCues`, `mkvBlockAt`, `mkvScan`): Chrome doesn't give a page the subtitles inside a file, so Agora reads the Matroska structure itself. The track list is near the start (first 2 MB). The file's index (Cues) usually lists every subtitle line (the owner's Oppenheimer file: 3,397 for its English track), so each line is read with one small read at its cluster, 6 at a time, the lines around the current time first. Clusters often start with a CRC-32 before their timecode. Without an index for that track, `mkvScan` walks the whole file once, reading only element headers (about 25 s for a 3 GB film at the phone's 130 MB/s). Either way the lines are kept in `agora-media` `subs`; reading through the index saves its progress every 300 lines and on closing (`partial: true`, `raw: [[cue index, line]]`), so the next opening shows what was read at once and reads only the rest (v39).
- The subtitles panel (3A, `plPanel`) slides in from the right; Back or a tap on the film closes it. Back from the player saves the place; reopening carries on from it (if past 10 s and not near the end) and says so. Leaving full screen with the phone's Back button also closes the player, so Back still takes one step.
- Sound Chrome can't decode (AC3, E-AC3, DTS, TrueHD) plays as silence: after 3.5 s with no sound decoded (`webkitAudioDecodedByteCount`) a toast names the codec. Chrome picks the first audio track it can play; a page can't choose the track (the owner's films with a Hindi E-AC3 track and an English AAC one play English). Hindi would need the phone to decode E-AC3 for Agora itself (WebCodecs `AudioDecoder`): the "Agora Video Check" artifact has a Dolby check for that.
- Decoder switches (MX Player's HW / HW+ / SW) aren't possible in a web app worth the cost: WebCodecs has a hardware/software preference but would mean building the whole pipeline and adds no formats. Left for when Agora becomes a real Android app.

**Screens:**
- **Home tile** "My Files" after the decks: its logo (a white folder with a blue tab, v26), "N files · N folders", or "Tap to connect" before the first connect. Its ⋯ (`filesMenu`): Refresh the list / Connect My Files, Choose a different folder.
- **Folder pages** (`openFolder`, kind `files` in `pages`, `renderFiles`): the same locked bar as deck pages ("<", the folder's name), then the path in grey ("My Files › Documents › Bank", each part tappable, `goCrumb`), then "4 folders · 8 files · newest first". Tools: the **list/grid toggle** (`files.view`), sort (Newest first, Oldest first, A to Z, Largest first; folders always first, A to Z), ⋯ (Refresh, Quick tagging, Select files, Choose a different folder).
  - **List** (the owner's pick B1): a 56-px picture, the name, "PDF · 1.2 MB · 14 Sep 2026", up to two tags as small blue pills and "+N".
  - **Grid** (B2): two across like a deck's cards; tags as blue text under the name.
  - **Connect line** (E1): "• Connect My Files · to refresh and open" (blue, then grey) under the count, only while not connected.
- **Tagging** (D1 + D3):
  - **Hold a file** to select (boxes, "× N selected ⋯", like page 3). ⋯ (`fileSelMenu`): Select all, Add tags, Share / Open with…
  - **The tag sheet** (`fileTagSheet`, also for one file): a field "Add a tag"; "On these files · tap to remove" as filled pills with "1 of 3" when only some have it; "Your tags · tap to add to all 3" as outlined pills (tags used on files first, then the cards' tags). A new tag takes the spelling the cards or files already use (`spellTag`).
  - **Quick tagging** (⋯ → Quick tagging, `startTagMode`): pick one tag; the bar becomes "× Tagging [Home]"; each tap on a file adds or removes it (boxes show which have it); folders still open. Back steps out of folders, then ends the mode.
- **Changing files** (v32, the owner's picks A2 + B2): while selecting, **Move** and **Delete** icons sit beside ⋯ (`fmove`, `fdel`); ⋯ adds Rename and Edit text for one file. **Moving** opens full folder pages showing only folders ("× Moving 2 files", the path as plain text, a bar at the bottom "To: Bank · New folder · Move here", `startMove`, `v.moving`). Rename picks out only the name, so the extension stays (`fileRenameSheet`). **Edit text** (txt, md, csv, json, log) is a page in Plex Mono with Save, also saved on Back (`openTextEdit`, kind `ftext`). A folder's ⋯: New folder, Rename this folder, Delete this folder (only when empty). The viewer's ⋯: Rename, Edit text, Move to…, Previous versions, Delete file. Delete asks first and says the file is kept 30 days. A move uses the phone's own `move()` when it has one, else copy then remove; the index follows (`idxMove`), keeping tags and pictures. Log lines: `changes.json` `{kind: 'file', op: 'delete' | 'edit' | 'move', path, to?, tags?, dir}`; `fileRestore` brings a file back.
- **Opening a file** (F, `openViewer`), built like the study view: the name, ⋯ and tags on top (three show, "+N ›"; hold a tag for × and +; tap a tag to search it); the file in the middle; "5 / 8", the size or "page 2 of 6", and blue "Share / Open with…" at the bottom. Swipe left or right for the next file in the list it was opened from.
  - Pictures: pinch, double-tap and drag to zoom. PDFs (pdf.js): all pages, fit the width, scroll, pinch or double-tap to zoom, drawn sharper after a zoom. Text files show as text, videos and audio play. Anything else: its name and a big "Share / Open with…".
  - **Share / Open with…** (`shareFiles`) uses Web Share with the file itself, so WhatsApp, Drive or a PDF app can take it.
  - ⋯: Tags, Share / Open with…, Show in folder.
- **Search** (C2): typing searches file and folder names and file tags as well as cards. Cards come first ("N cards · Create deck"), then "1 folder · 3 files" with a thumbnail, the name and "PDF · Bank". A pinned tag shows the cards and the files with it. Tapping a file opens it, a folder opens its page.

## Import and export

The only way cards get in and out of the app.
- A zip holds `manifest.json` plus images: `{app: 'agora', version: 1, decks: [{id?, name, cover?, coverCard?, cards: [...]}]}`.
  - Older zips say `app: 'subtext'`; the import doesn't check `app`, so they keep working.
- A card is matched **by id**, never by word. A new card needs a `scene` plus `definition(s)`.
- For an existing card, only the fields present change: `word`, `tags`, `reference` (null removes it), `definitionText`, `shotAt`, `sceneTime`, `sceneText`, `sceneCaption`, `pdf` (null removes any of these). `update: 'scene'` replaces only the scene image; `update: true` replaces everything.
- Both update modes skip cards that are already identical, so re-importing reports "already up to date". Review progress is always kept.
- A deck is found by id, then by name, and created only if a new card needs it.
- Export writes the same format, so a backup is also an import file.
- A deck entry may also carry `subdecks: [{id, name, cards: [card ids], createdAt}]`, `sourceNames: {key: name}` and `hiddenSources: [keys]` (v20). Import only adds what's missing, never undoes a change made in the app.
- The manifest may also carry `files: {tags: [{path, name, size, mtime, tags, at, missing?}]}` (v23): the tags of files in My Files, never the files. Import merges them (the newer change wins); tags for files this phone hasn't listed yet wait until My Files is connected. Older zips have no `files` and import exactly as before.
- A video definition is exported with its `src` (fixed in v23), so re-importing a backup reports "already up to date".
- The manifest may also carry `bookmarks: [{id, url, title, site, tags, addedAt, at}]` (v30). Import takes one only when it is newer (`at`) than the phone's copy or its deletion.
- **Rules:** never break older zips or backups. New fields are optional. An import must be safe to repeat.

## Design system (keep it unless the owner changes it)

**Previews:** send each option as its own full-size phone screenshot in `/mnt/project-files/<topic>/` and link each one in the reply; the owner found one combined sheet too small.

**My Files choices (v23, picked from numbered previews):** A1 tile after the decks; B1 list + B2 grid with a toggle in the bar; B4 path above the count; C2 cards then files in search; D1 hold-to-select + tag sheet and D3 quick tagging; E1 one quiet "Connect My Files" line; F viewer like the study view. **Home tile logos (v26, the owner's pick 2B):** Vocabulary is "Aa" in Plex Mono Light 46px, the "A" white and the "a" blue; My Files is a white outlined folder with a solid blue tab (`LOGO_VOCAB`, `LOGO_FILES`). Folders inside My Files are a grey outlined folder; files without a picture are a grey page with the extension (no colours per file type).


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
3. **Bump `VERSION`** in `sw.js` to `agora-v(N+1)`.
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
- **Notes (v29):** `python3 tools/app-test/test_notes.py . --out shots/notes/`. It writes notes with every kind of formatting and a made-up picture, and checks the tile, the list, saving, reloading, select and delete, Back, the backup on a fresh phone, re-imports, and that an imported note can't carry a script.
- **v28 + v31 (home title, select-all icon, search inside a deck, My Files and Notes):** `python3 tools/app-test/test_v28.py . --out shots/v28/`.
- **v27 (History, names, tiles, headings):** `python3 tools/app-test/test_history.py . --out shots/history/`.
- **Study:** `python3 tools/app-test/test_study.py . --out shots/study/`. It turns the test library into one 30-card "Vocabulary" deck (made-up copies) and checks the banner, today's 20, the queue order, list/grid, search and Bring to front, Continue / Repeat / Tomorrow / Pass and the gaps, no swiping past a card, Done for today and Learn 10 more, that browsing changes nothing, Back, and the backup.
- **Agora folder speed (v34, v36):** `python3 tools/app-test/test_folder_speed.py . --out shots/folder-speed/`: 66 cards with Android's folder access modelled as Chrome uses it: one step at a time, 8 ms each, and finding a name reads the whole folder (+0.05 ms an entry). Running steps side by side doesn't help on the phone; only fewer steps do. Checks the steps a card takes, each card under its own name, no tiles.
- **Folder per deck (v35):** `python3 tools/app-test/test_folder_layout.py . --out shots/folder-layout/`: rewrites the folder the way v32–v34 kept it, reopens, and checks everything moves over (and a new phone reads the old layout); then a renamed card, a card moved to another deck, a renamed deck and a restore.
- **The Agora folder (v32):** `python3 tools/app-test/test_folder.py . --out shots/folder/`. Connects a made-up OPFS My Files, checks the first copy, previous versions after a change, a delete and a rename, restoring (page, card, bookmark), the "changes waiting" line, and a fresh phone bringing everything back from the folder alone.
- **Changing files (v32):** `python3 tools/app-test/test_fileops.py . --out shots/fileops/`: move (folder pages, tags kept), rename, edit text, new folder, delete, and bringing each back from Previous versions.
- **Bookmarks:** `python3 tools/app-test/test_bookmarks.py . --out shots/bookmarks/`. Made-up links only. Opens the app at `./?title=…&text=…` the way Android's share menu does (the harness patches `T` in with a query too).
- **Video player (v37):** `python3 tools/app-test/test_player.py . --out shots/player/`, with the phone held sideways (915×412). Uses `fixtures/made-up-film.mkv` (40 s, VP9 + Opus because the test browser can't play H.264, two invented English subtitle tracks, the second "SDH"; `tools/app-test/make_test_video.sh` makes it) plus a made-up `.en.srt` beside it. Checks the player opening from the folder, the file name only, both tracks read through the index and by a whole-file pass, the .srt, lines showing and going on time, subtitle swipes, taps, double-taps, the seek bar, brightness and volume (with the boost), the panel, the lock, carrying on, Back. Subtitles show in a fallback font in screenshots (no Roboto in the test browser).
- **My Files:** `python3 tools/app-test/test_files.py . --out shots/files/`. The folder picker can't be clicked in a test, so it fills the origin private file system (`navigator.storage.getDirectory()`) with made-up folders and files and hands it to the app as My Files (`window.showDirectoryPicker = async () => dir`). It checks the index, list and grid, the path, tagging (sheet and quick tagging), `.agora/file-tags.json`, search, the viewer, Share (stubbed), a moved file keeping its tags, Back, the backup, re-imports, and updating from older versions: the new version must open the cards while v22 is still open in another tab (the v23 black screen), and must carry over a My Files index v23 saved. Never put real files in the repo.
- **When the app learns a new card field,** add a card using it to `tools/app-test/make_test_library.py` and rebuild the zip (`python3 tools/app-test/make_test_library.py`).

## Things that bite

- **The script is one closure**, so its functions aren't reachable from the page console. The harness patches in `window.T` for tests; never ship that patch.
- **IndexedDB upgrades can hang forever** on the phone: an older copy of Agora in a frozen background Chrome tab never closes its connection. Never call `indexedDB.open('subtext', N)`; see Storage.
- **Every page under `/agora/` is the app.** `sw.js` answers every navigation with the cached `index.html`, and stores whatever the network returns under that key. So never add a second page to the repo (a check page, a test page): opening it on the phone would cache it as the app. Put such pages elsewhere (a claude.ai artifact).
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
- **v22:** the app is renamed from Subtext to Agora (home-screen name, page title, messages, backup file name `agora-backup-…zip`, manifest `app: 'agora'`). The database keeps its old name so every card stays; older Subtext backups and import zips still import.

- **v23:** My Files: a tile after the decks opens the phone's My Files folder (list or grid, path, sort); tag files one at a time, many at once, or with Quick tagging; search finds files and folders under the cards; images, PDFs, text, video and audio open inside Agora, and Share / Open with… sends any file to another app. Database version 2 adds the `files` store; file tags are also kept in `.agora/file-tags.json` and in backups. Backups keep a video definition's `src`. (Opened to a black screen when an older copy was open in a Chrome tab: the database upgrade waited for it.)
- **v24:** fix for the v23 black screen: the cards' database is opened as it is and never upgraded; My Files moves to its own database `agora-files` (a v23 index is copied over) and loads after the decks show; a plain message replaces a black screen if the cards ever take long to open.

- **v25:** Study: a Study deck inside Vocabulary with 20 new cards a day plus reviews on a 1-3-7-14-30-60-120 day cycle; Continue, then Repeat / Tomorrow / Pass; a queue of new cards (list or grid, search, Bring to front). Progress in its own database `agora-study` and in backups. "Mark for review" and the "to review" counts are gone.
- **v26:** logos on the home tiles: Vocabulary shows a white "A" with a blue "a", My Files a white folder with a blue tab (instead of a card picture and the four newest photos).

- **v26:** a single tap in the study view hides the header and footer, and the next tap brings them back; the pages stay where they were.
- **v27:** "Your decks" smaller (1C); the count sits right under every page title (2A); search says "Search anything" with no "words saved" line; History on Vocabulary's page (4A, database `agora-history`); New cards no longer jumps when a card is held; a card's name is its dictionary headword everywhere; tiles of text and magazine cards are redrawn from what the card shows.
- **v28:** "Your decks" sits where every page title does, with its count right under it; Select all is an icon (a box with a tick) in every selection bar, and tapping it again clears the selection; a search icon on a deck's first page searches only that deck.

- **v29 (Notes):** a Notes tile after My Files opens a simple notebook (list, last edited first; 1A logo, 2A list, 3A Plex Mono); notes have headings, bold, italic, underline, lists, checklists, quotes and pictures; database `agora-notes`; backups carry notes.
- **v30:** Bookmarks: share a link from any app into Agora (it's in Android's share menu), suggested tags already added, one tap Save, edit later; a list or grid page with search; bookmarks in the main search and in backups (database `agora-bookmarks`).
- **v31:** a search icon in My Files and in Notes, searching only there, like the one on a deck's first page.

- **v32:** everything Agora holds is also kept as files in My Files › Agora (cards with their pictures, notes as pages, bookmarks, study progress, history); a new phone brings it all back from there; the earlier copy of anything changed or deleted is kept 30 days, with a Previous versions page (each item or by moment) and per-card, per-note and per-bookmark restore (database `agora-sync`). My Files can move, rename, edit text, make folders and delete, each change restorable.
- **v33:** fix: the "Keep everything in My Files · tap to start" line now shows on a phone updated from v31 (it waited for a change to be made first, so the Agora folder never started).

- **v34:** the first copy into My Files › Agora is about 14 times faster: folders are found once per save instead of once per picture (`agDirs`, only while saving), and 8 cards are written side by side (`AG_SIDE`, folder names reserved in `AG.claim`).

- **v35:** My Files › Agora keeps one `cards.json` and one Pictures folder per deck instead of a folder per card (the owner's pick); cards saved the old way move over by themselves.

- **v36:** the first copy writes about a third fewer files: no tile pictures (redrawn from the scene on a new phone), and `.nomedia` keeps Agora's pictures out of the Gallery.

- **v37:** a video player for films in My Files (full screen, sideways): skip and double-tap skipping, a seek bar, brightness and volume swipes, the lock, fill/fit, carrying on where a film was left; subtitles read from inside .mkv files (or a .srt beside them), drawn like the phone's own player, a panel to pick them and their size, swipe a line for the next or previous one. Database `agora-media`.

- **v38:** fix: the video player played no sound when the volume had been swiped above 100 (the boost's sound context was started without a touch, so Chrome kept it silent); the boost is now up to 4 times as loud, with a limiter.

- **v39:** the player: volume 0–100 with a gentler boost (3×, VLC-style curve); brightness up to 200; the volume bar on the left and the brightness bar on the right; Fit / Crop / Stretch; pinch to zoom and shift the picture (kept per film); long file names on two lines; hold a subtitle and drag it up or down (one height with the controls, one without); subtitles read from inside a film are kept as they are read, so closing early loses nothing.

Add a line here with every version you ship.
