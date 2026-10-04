"""Caption + hashtag generation. Simple local templates, no external AI calls (works fully offline)."""
from __future__ import annotations

import random
import re

HASHTAG_BANK = {
    "motivation": ["motivation", "motivationalquotes", "dailymotivation", "staymotivated", "motivationnation", "inspirationdaily"],
    "success": ["success", "successmindset", "successquotes", "hustle", "entrepreneurlife", "goalgetter"],
    "mindset": ["mindset", "mindsetiseverything", "growthmindset", "positivemindset", "mindsetmatters", "shiftyourmindset"],
    "self_growth": ["selfgrowth", "selfimprovement", "personaldevelopment", "growthjourney", "bettereveryday", "levelup"],
    "life": ["lifequotes", "lifelessons", "lifegoals", "goodvibes", "liveyourlife", "lifestyle"],
    "discipline": ["discipline", "disciplineoverfeelings", "consistency", "buildinghabits", "stayfocused", "workethic"],
    "confidence": ["confidence", "selfworth", "believeinyourself", "confidencequotes", "innerstrength", "youvegotthis"],
    "productivity": ["productivity", "productivitytips", "focusmode", "getthingsdone", "timemanagement", "productivehabits"],
}

OPENERS = [
    "Some days all you need is a reminder:",
    "Read this until it sinks in:",
    "A little nudge for today:",
    "For anyone who needs to hear this:",
    "Save this for the days you doubt yourself:",
    "Screenshot this and come back to it:",
]
MIDDLES = [
    "You don't have to have it all figured out to keep moving.",
    "Progress doesn't ask for perfect - it just asks you to show up again.",
    "The next step is the only one that actually needs your attention right now.",
    "Small, steady action beats waiting for the perfect moment.",
    "You're allowed to grow at your own pace.",
    "Every version of you got you here. Trust the next one too.",
]
CLOSERS = ["Keep going. \U0001F49B", "One more step. \U0001F4AA", "You've got this. \u2728", "Save this for later. \U0001F4CC", "Tag someone who needs this. \U0001F447"]


def _category_for(quote: dict) -> str:
    cat = (quote.get("category") or "").lower()
    if cat in HASHTAG_BANK:
        return cat
    text = quote.get("text", "").lower()
    for key, words in {
        "discipline": ["discipline", "habit", "consisten", "work"], "confidence": ["confiden", "worth", "believe"],
        "success": ["success", "goal", "achiev", "hustle"], "productivity": ["focus", "productiv", "time"],
        "self_growth": ["grow", "heal", "outgrow", "becom"],
    }.items():
        if any(w in text for w in words):
            return key
    return "motivation"


def generate_caption(quote: dict, rng: random.Random | None = None, brand_name: str = "") -> str:
    rng = rng or random.Random()
    text = quote.get("text", "").strip().strip('"\u201c\u201d')
    parts = [rng.choice(OPENERS), "", text, "", rng.choice(MIDDLES), "", rng.choice(CLOSERS)]
    caption = "\n".join(parts)
    tags = generate_hashtags(quote, 8, rng, brand_name)
    return caption + "\n\n" + " ".join(f"#{t}" for t in tags)


def generate_hashtags(quote: dict, count: int, rng: random.Random | None = None, brand_name: str = "") -> list[str]:
    rng = rng or random.Random()
    primary = _category_for(quote)
    others = [c for c in HASHTAG_BANK if c != primary]
    rng.shuffle(others)
    pool = HASHTAG_BANK[primary][:] + [t for c in others for t in HASHTAG_BANK[c]]
    seen, tags = set(), []
    if brand_name:
        b = re.sub(r"[^a-z0-9]", "", brand_name.lower())
        if b:
            tags.append(b)
            seen.add(b)
    for t in pool:
        if t not in seen:
            tags.append(t)
            seen.add(t)
        if len(tags) >= count:
            break
    return tags[:count]
