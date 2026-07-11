"""
9,999 Eyes — daily life generator.

Picks an unused seed, derives a muse word from it, asks Claude to write the
life, asks Gemini (Nano Banana) to carve the tombstone art, and inserts the
finished chapter into index.html right above the AUTO-INSERT marker.

Requires env vars: ANTHROPIC_API_KEY, GEMINI_API_KEY
Requires packages: requests, pillow, english-words
"""

import base64
import json
import os
import random
import re
import sys
from io import BytesIO

import requests
from PIL import Image

REPO_INDEX = "index.html"
MARKER = "// AUTO-INSERT-NEW-CHAPTER-ABOVE-THIS-LINE"
TOTAL_LIVES = 9999

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

ANTHROPIC_MODEL = "claude-sonnet-5"
GEMINI_IMAGE_MODEL = "gemini-2.5-flash-image"

SYSTEM_PROMPT = """You are the ghostwriter for "9,999 Eyes," a seeded anthology.
The conceit: a single soul has lived 9,999 lives. Each life is unlocked by a
number; that number seeds a random word generator; the word becomes the muse
for the story. Lives can land in any era, place, or circumstance — real
history, invented history, or something stranger — but should feel grounded
and specific, never generic. First person, through that life's eyes.

Style notes, matched to the anthology's existing voice:
- Sensory, specific, unhurried. Real names, places, dates, and technical
  detail where the setting calls for it. When you use real historical events,
  get the facts right.
- Length varies by what the life needs — roughly 600 to 1800 words. Never
  rush a life that deserves room, never pad a life that doesn't.
- Each life ends with a closing line in that life's own voice or language —
  a version of "see you in another life" that fits the character and culture
  rather than a stock phrase repeated verbatim every time.
- The muse word should shape the story's central image, occupation, object,
  or metaphor — not just appear as a vocabulary word.

You will be given a seed number and a muse word. Respond with ONLY raw JSON
(no markdown fences, no commentary) matching exactly this schema:

{
  "title": "CHAPTER TITLE IN CAPS",
  "era": "Year — Place",
  "farewell": "closing line in this life's voice",
  "story": ["paragraph one", "paragraph two", "..."],
  "image_prompt": "a prompt for an AI image generator describing tombstone bas-relief art for this chapter"
}

For image_prompt: describe a carved granite headstone relief, arched top,
depicting the central image/scene of the story, in the visual language of a
memorial engraving — muted verdigris and bone tones on dark charcoal granite,
dramatic side lighting, no text or lettering in the image itself. Keep it
specific to this life's story, not generic."""


def load_html():
    with open(REPO_INDEX, "r", encoding="utf-8") as f:
        return f.read()


def existing_seeds_and_nums(html):
    seeds = set(int(x) for x in re.findall(r"seed:\s*(\d+)", html))
    nums = [int(x) for x in re.findall(r"num:\s*(\d+)", html)]
    return seeds, nums


def pick_seed(existing_seeds):
    available = [n for n in range(0, TOTAL_LIVES) if n not in existing_seeds]
    if not available:
        raise SystemExit("All 9,999 seeds have been used. The book is complete.")
    return random.choice(available)


def seed_to_word(seed):
    from english_words import get_english_words_set

    words = sorted(get_english_words_set(["web2"], lower=True, alpha=True))
    rnd = random.Random(seed)
    return rnd.choice(words)


def generate_story(seed, word):
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": ANTHROPIC_MODEL,
            "max_tokens": 4000,
            "system": SYSTEM_PROMPT,
            "messages": [
                {
                    "role": "user",
                    "content": f'Seed: {seed}\nMuse word: "{word}"\n\nWrite this life.',
                }
            ],
        },
        timeout=180,
    )
    resp.raise_for_status()
    data = resp.json()
    text = "".join(b["text"] for b in data["content"] if b.get("type") == "text").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(json)?", "", text).rstrip("`").strip()
    return json.loads(text)


def generate_image(image_prompt):
    resp = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_IMAGE_MODEL}:generateContent",
        headers={"x-goog-api-key": GEMINI_API_KEY, "content-type": "application/json"},
        json={"contents": [{"parts": [{"text": image_prompt}]}]},
        timeout=180,
    )
    resp.raise_for_status()
    data = resp.json()
    parts = data["candidates"][0]["content"]["parts"]
    for part in parts:
        if "inlineData" in part:
            img_bytes = base64.b64decode(part["inlineData"]["data"])
            return Image.open(BytesIO(img_bytes))
    raise RuntimeError("Gemini returned no image: " + json.dumps(data)[:800])


def process_image(im):
    im = im.convert("RGB")
    w, h = im.size
    side = min(w, h)
    left, top = (w - side) // 2, (h - side) // 2
    im = im.crop((left, top, left + side, top + side))
    buf = BytesIO()
    im.save(buf, "WEBP", quality=85)
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/webp;base64,{b64}"


def js_escape(s):
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def build_chapter_js(num, seed, word, story_data, image_data_uri):
    story_lines = ",\n      ".join(f'"{js_escape(p)}"' for p in story_data["story"])
    return f"""  {{
    num: {num},
    title: "{js_escape(story_data['title'])}",
    seed: {seed},
    word: "{js_escape(word)}",
    era: "{js_escape(story_data['era'])}",
    image: "{image_data_uri}",
    farewell: "{js_escape(story_data['farewell'])}",
    story: [
      {story_lines}
    ]
  }},
"""


def main():
    html = load_html()
    seeds, nums = existing_seeds_and_nums(html)
    seed = pick_seed(seeds)
    word = seed_to_word(seed)
    num = (max(nums) + 1) if nums else 1

    print(f"Life {num}: seed={seed} word={word!r}", file=sys.stderr)

    story_data = generate_story(seed, word)
    print(f"Title: {story_data['title']}", file=sys.stderr)

    im = generate_image(story_data["image_prompt"])
    image_data_uri = process_image(im)

    chapter_js = build_chapter_js(num, seed, word, story_data, image_data_uri)

    if MARKER not in html:
        raise SystemExit(f"Marker not found in {REPO_INDEX}: {MARKER}")

    html = html.replace(MARKER, chapter_js + "  " + MARKER)

    with open(REPO_INDEX, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Inserted Life {num}: {story_data['title']}", file=sys.stderr)


if __name__ == "__main__":
    main()
