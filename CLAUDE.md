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
- `tools/app-test/`: the phone-view test kit (not part of the app; the service worker never loads it). `test_files.py` tests My Files, `test_study.py` the Study deck.

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

IndexedDB database `agora-study` (v25), version 1, holds Study progress (see "Study"): store `cards` (key `id`, the card's id): `{id, step, due, first, last, at, done?}` for a card studied at least once, or `{id, front, at}` for a new card brought to the front of the queue; store `meta` (key `k`): `daily` `{v}` new cards a day (default 20), `extra` `{day, n}` more new cards asked for today. Days are whole local days starting at 4 am (`dayNo`). It loads after the decks are on screen.

- `localStorage` only remembers small things under `agora.` keys (older `subtext.` keys are still read), such as `hinted2` (the first-run gesture hint has been seen), `files.view` (`list` / `grid`) and `files.sort`.
- **Never upgrade `subtext`** (no version bump, no new stores there). A new kind of data gets a new database of its own, opened after the decks are on screen. **Never drop or rewrite the owner's data.** They have over a thousand cards on the phone and only a backup zip.
- If the cards' database takes more than 2.5 s to open, the home screen says "Opening your cards… If Agora is also open in a Chrome tab, close that tab and Agora will carry on." instead of staying black.

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
- Review: `peeks` (times the meaning was opened), `seen`, `lastSeen`. The old `review` mark and `streak` stay in the data (and in backups) but the app no longer shows or uses them (v25); Study progress lives in `agora-study`, not on the card.
- `sceneKind(c)`: `pdf` if `c.pdf`, otherwise `art` if `sceneText`, otherwise `img` (with a caption if `sceneCaption`).

## Screens

- **Home:** "Your decks", a grid with the newest deck first.
  - Each tile has a cover (a chosen photo, a chosen card, or the deck's first card) and "N cards".
  - The ⋯ menu on a tile: Study, Add cards, Browse cards, Rename, Cover image, Merge into another deck, Delete deck.
  - **Merge into another deck** (`mergeSheet` / `doMerge`, v18) moves every card (tags, review marks and progress kept) into a chosen deck or a new one, then removes the empty deck.
  - **Decks are kinds of content, not sources.** All vocabulary lives in one deck, "Vocabulary"; the source (show, film, channel, book) is in the tags. The owner plans to grow Agora into a place to find anything in their digital life, with more decks over time (a finance tracker, concepts with detailed explanations, pictures and files).
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
  - **Page 3, a deck's cards:** a gallery, two across, no other view; the sort icon at the top right, the sort in grey under the title. **Hold a card** to select: small boxes appear on every card (selecting only repaints the boxes and the bar, `paintSel`, so nothing flickers); the bar shows × , "N selected" and ⋯ (`selMenu`): Select all, Add to deck, Move to deck and Remove from deck (in a made deck), Delete cards.
  - **Sort** (`SORTS`, `storySort`, `sortOf`): "Order of appearance" only when every card (in a source or a made deck) is from one show, film, book or YouTube video (episode then `sceneTime`; a book by `shotAt`, which follows reading order; one video by `ref.t`), otherwise newest first. Also Newest first, Oldest first, A to Z. A choice sticks per deck and source (`localStorage` `sort.<deckId>.<sourceKey>`).
  - The study view opened from page 3 shows exactly that page's cards in that order (`openStudy(d, id, order)`); no review-first.
- **My Files** (v23): see "My Files" below. Its tile sits after the decks, before "New deck".
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
- **The queue** (4A + 4B, `openQueue` / `renderQueue`): every new card numbered in the order Study brings them, as a list or a grid (toggle, `queue.view`). Default order (`queueOrder`): oldest `shotAt` first, with each show's, film's or book's cards taking their places in story order (episode, then `sceneTime`). Search (words, meanings, tags; typed text suggests tags to pin), Select all, or hold a card to select; **Bring to front** puts them first in their order (a later batch goes ahead of an earlier one, `front`).
- **Removed in v25:** "Mark for review" (hold, ✎ menu, select menu, Browse cards' card sheet) and every blue "N to review" count; review marks no longer move cards to the front of a deck.
- **Backups** carry `study: {daily, cards: [records]}`; import takes a record only when it is newer (`at`) than the phone's, so a re-import changes nothing.

## My Files (v23)

The owner keeps important files (documents, PDFs, photos, anything) in a folder called **My Files** in the phone's internal storage, in subfolders of their choosing. Agora browses it, tags files, finds them with the cards' search, and opens them.

**Rules that never change:**
- Agora **never moves, renames, changes or deletes the owner's files.** The only thing it writes in the folder is `.agora/file-tags.json`.
- **No pop-up on launch.** The app opens without touching the folder. Android asks for the folder again every time the app is reopened (`queryPermission()` says "prompt"), so only an action that needs the folder asks, with one tap: the first connect, Refresh, opening or sharing a file. The tap that opens a file is also the tap that reconnects. When Agora becomes a real Android app, that tap is the only thing that goes away.
- The **File System Access API** (`showDirectoryPicker`) is in Chrome on Android, not in Brave. Without it the file features hide and the home screen shows one line: "My Files needs Chrome: this browser doesn't let Agora open folders."

**The index** (database `agora-files`, store `files`, in memory `fidx`, written through `fstore`): `{path, kind: 'dir' | 'file', name, dir, size, mtime, ext, tags, tagsAt, thumbId, thumbKey, noThumb}`. `path` is inside the folder ("Documents/Bank/x.pdf"), `dir` the folder's path ('' for the top). Browsing and search work from the index alone, before the folder is connected.
- **Refresh** (`rescan`): walks the whole folder in the background (the count updates on the page; Chrome froze on huge folders, so nothing blocks the screen), skips hidden names (starting with "."), then `reconcile`: new, removed and changed files. A renamed or moved file keeps its tags and picture: same name + size + date, else same name + size, else same size + date (only when exactly one file matches). A tagged file that has gone is kept aside in `fileTagsPending`, so its tags come back if it does.
- **Thumbnails** (`makeFileThumbs`): 400-px JPEGs of images and of a PDF's first page, made one at a time after a refresh, the folder on screen first; originals are read only when opened or shared.
- **Tags are saved twice:** in the index at once, and in `.agora/file-tags.json` (`{app: 'agora', kind: 'file-tags', version: 1, files: [{path, name, size, mtime, tags, at, missing?}]}`), written whenever tags change while connected (`tagsChanged` → `saveTagsFile`, one small write) and read back on every connect (`readTagsFile`). In every merge (`mergeTagEntries`: the folder's copy, a backup, the set-aside list) the newer change (`at` / `tagsAt`) wins.
- **Connecting** (`connectFiles`): must run straight from a tap. The folder handle is kept in `agora-files` `meta.filesRoot`; "Choose a different folder" picks again.

**Screens:**
- **Home tile** "My Files" after the decks: a mosaic of the four newest pictures (or a folder), "N files · N folders", or "Tap to connect" before the first connect. Its ⋯ (`filesMenu`): Refresh the list / Connect My Files, Choose a different folder.
- **Folder pages** (`openFolder`, kind `files` in `pages`, `renderFiles`): the same locked bar as deck pages ("<", the folder's name), then the path in grey ("My Files › Documents › Bank", each part tappable, `goCrumb`), then "4 folders · 8 files · newest first". Tools: the **list/grid toggle** (`files.view`), sort (Newest first, Oldest first, A to Z, Largest first; folders always first, A to Z), ⋯ (Refresh, Quick tagging, Select files, Choose a different folder).
  - **List** (the owner's pick B1): a 56-px picture, the name, "PDF · 1.2 MB · 14 Sep 2026", up to two tags as small blue pills and "+N".
  - **Grid** (B2): two across like a deck's cards; tags as blue text under the name.
  - **Connect line** (E1): "• Connect My Files · to refresh and open" (blue, then grey) under the count, only while not connected.
- **Tagging** (D1 + D3):
  - **Hold a file** to select (boxes, "× N selected ⋯", like page 3). ⋯ (`fileSelMenu`): Select all, Add tags, Share / Open with…
  - **The tag sheet** (`fileTagSheet`, also for one file): a field "Add a tag"; "On these files · tap to remove" as filled pills with "1 of 3" when only some have it; "Your tags · tap to add to all 3" as outlined pills (tags used on files first, then the cards' tags). A new tag takes the spelling the cards or files already use (`spellTag`).
  - **Quick tagging** (⋯ → Quick tagging, `startTagMode`): pick one tag; the bar becomes "× Tagging [Home]"; each tap on a file adds or removes it (boxes show which have it); folders still open. Back steps out of folders, then ends the mode.
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
- **Rules:** never break older zips or backups. New fields are optional. An import must be safe to repeat.

## Design system (keep it unless the owner changes it)

**My Files choices (v23, picked from numbered previews):** A1 tile after the decks; B1 list + B2 grid with a toggle in the bar; B4 path above the count; C2 cards then files in search; D1 hold-to-select + tag sheet and D3 quick tagging; E1 one quiet "Connect My Files" line; F viewer like the study view. Folders are a grey outlined folder; files without a picture are a grey page with the extension (no colours per file type).


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
- **Study:** `python3 tools/app-test/test_study.py . --out shots/study/`. It turns the test library into one 30-card "Vocabulary" deck (made-up copies) and checks the banner, today's 20, the queue order, list/grid, search and Bring to front, Continue / Repeat / Tomorrow / Pass and the gaps, no swiping past a card, Done for today and Learn 10 more, that browsing changes nothing, Back, and the backup.
- **My Files:** `python3 tools/app-test/test_files.py . --out shots/files/`. The folder picker can't be clicked in a test, so it fills the origin private file system (`navigator.storage.getDirectory()`) with made-up folders and files and hands it to the app as My Files (`window.showDirectoryPicker = async () => dir`). It checks the index, list and grid, the path, tagging (sheet and quick tagging), `.agora/file-tags.json`, search, the viewer, Share (stubbed), a moved file keeping its tags, Back, the backup, re-imports, and updating from older versions: the new version must open the cards while v22 is still open in another tab (the v23 black screen), and must carry over a My Files index v23 saved. Never put real files in the repo.
- **When the app learns a new card field,** add a card using it to `tools/app-test/make_test_library.py` and rebuild the zip (`python3 tools/app-test/make_test_library.py`).

## Things that bite

- **The script is one closure**, so its functions aren't reachable from the page console. The harness patches in `window.T` for tests; never ship that patch.
- **IndexedDB upgrades can hang forever** on the phone: an older copy of Agora in a frozen background Chrome tab never closes its connection. Never call `indexedDB.open('subtext', N)`; see Storage.
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

- **v26:** a single tap in the study view hides the header and footer, and the next tap brings them back; the pages stay where they were.

Add a line here with every version you ship.
