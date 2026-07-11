# 9,999 Eyes

A seeded anthology. Every number becomes a word, every word becomes a life — told through the eyes of a soul who's lived them all.

**Live site:** _add your GitHub Pages link here once deployed_

## How it works

1. A number is chosen.
2. That number seeds a random word generator against an English wordlist.
3. The word becomes the muse for a short story — any era, any place, real or invented — written in first person, through that life's eyes.
4. Each life gets a chapter title, a tombstone-style header image, and its own page in the archive.
5. Some lives get eyes carved into their stone. Some don't.

## Structure

The site is `index.html` plus a small `icons/` folder and `manifest.json` for the home-screen/app icon. HTML, CSS, and JavaScript for the story engine itself all live inside `index.html` — no build step, no other dependencies.

```
9999Eyes/
├── index.html
├── manifest.json
└── icons/
    ├── favicon-16.png
    ├── favicon-32.png
    ├── apple-touch-icon.png
    ├── icon-192.png
    └── icon-512.png
```

Chapter artwork (tombstones) stays embedded as base64 inside `index.html` — only the app icon needs to be a real, fetchable file, since Android's "Add to Home Screen" fetches the manifest and icons over the network to build the app icon; a base64 data URI can't be fetched that way and silently falls back to a generic icon.

Chapters live in the `CHAPTERS` array near the bottom of the file. Each entry looks like this:

```js
{
  num: 1,
  title: "CHAPTER TITLE",
  seed: 7482,
  word: "propellent",
  era: "Year — Place",
  image: "",              // path, URL, or base64 data URI
  farewell: "See you in another life.",
  story: [
    "First paragraph…",
    "Second paragraph…"
  ]
}
```

Order of display = order in the array. New chapters get appended to the end.

## Deploying

1. Push `index.html`, `manifest.json`, and the `icons/` folder (all of it, keeping the folder structure) to the repo root.
2. In repo Settings → Pages, set the source to the `main` branch, root folder.
3. GitHub will publish it at `https://<username>.github.io/<repo-name>/`.

No `assets/` folder needed beyond `icons/` — chapter artwork is embedded as base64 directly in each chapter's `image` field to keep the story engine single-file.

## Adding a new life

**Manual:** get a number, seed a word generator with it, write the story, generate tombstone artwork, append an entry to `CHAPTERS`.

**Automatic:** a GitHub Action runs daily, picks an unused seed, writes the story via the Claude API, generates the tombstone art via Gemini, and commits the new chapter for you. Setup:

1. Get an Anthropic API key from [console.anthropic.com](https://console.anthropic.com) and a Gemini API key from [Google AI Studio](https://aistudio.google.com).
2. In the repo: **Settings → Secrets and variables → Actions → New repository secret**. Add two secrets: `ANTHROPIC_API_KEY` and `GEMINI_API_KEY`.
3. Push `.github/workflows/daily-life.yml` and `scripts/` (both files inside it) to the repo, keeping the folder structure.
4. That's it — it runs daily at 13:00 UTC (9 AM Eastern). Edit the `cron` line in the workflow file to change the time. You can also trigger it manually anytime from the **Actions** tab → **New Life Daily** → **Run workflow**.

Cost is roughly $0.05–$0.10 per day (a few cents of Claude API for the story, ~$0.04 of Gemini for the image). Each run checks which seeds are already used and picks a new one, so no life repeats until all 9,999 are told.
