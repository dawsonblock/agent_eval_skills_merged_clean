---
name: instagram-posting
description: Create, schedule, and publish Instagram posts — captions, hashtags, image prep, and automation. Use when the user wants to write Instagram captions, generate hashtags, resize images for Instagram, schedule posts, or automate Instagram publishing. Trigger phrases include "instagram post", "instagram caption", "post to instagram", "hashtags", "instagram content", "schedule instagram", "instagram automation", "social media post".
---

# Instagram Posting

Create and publish Instagram content — images, captions, hashtags, and scheduling.

## Post Types & Dimensions

| Type | Dimensions | Aspect Ratio |
|------|------------|-------------|
| Square post | 1080 × 1080 | 1:1 |
| Portrait post | 1080 × 1350 | 4:5 |
| Landscape post | 1080 × 566 | 1.91:1 |
| Story | 1080 × 1920 | 9:16 |
| Reel cover | 1080 × 1920 | 9:16 |

**Recommended**: 4:5 portrait (1080 × 1350) — takes up most feed real estate.

## Caption Formula

```
[Hook — first line visible without "more"]
[Body — value, story, or detail]
[CTA — question, call to action, or directive]
.
.
.
[Hashtags — 3–15 relevant tags]
```

**First-line hook patterns**:
- Question: "Ever wondered why your posts get no traction?"
- Bold claim: "Most captions fail in the first 3 words."
- Number: "5 things I stopped doing to 10x engagement:"
- Story open: "I almost quit Instagram last year. Here's what happened."

## Hashtag Strategy

- Use 3–15 hashtags (quality > quantity)
- Mix tiers: 1–2 large (1M+), 3–4 medium (100K–1M), 5–8 niche (<100K)
- Put hashtags at the end of the caption or first comment
- Avoid banned hashtags

```python
# Generate hashtag groups from topic
HASHTAG_TIERS = {
    "design": {
        "large": ["#design", "#graphicdesign", "#branding"],
        "medium": ["#designinspiration", "#visualdesign", "#brandidentity"],
        "niche": ["#designprocess", "#branddesigner", "#logodesigner"]
    }
}
```

## Image Resizing (Python + Pillow)

```python
from PIL import Image

def resize_for_instagram(input_path: str, output_path: str, size=(1080, 1350)):
    img = Image.open(input_path)
    img = img.convert('RGB')
    # Crop to aspect ratio first
    target_ratio = size[0] / size[1]
    w, h = img.size
    current_ratio = w / h
    if current_ratio > target_ratio:
        new_w = int(h * target_ratio)
        offset = (w - new_w) // 2
        img = img.crop((offset, 0, offset + new_w, h))
    else:
        new_h = int(w / target_ratio)
        offset = (h - new_h) // 2
        img = img.crop((0, offset, w, offset + new_h))
    img = img.resize(size, Image.LANCZOS)
    img.save(output_path, 'JPEG', quality=95)
```

## Scheduling & Publishing

### Meta Content Publishing API (official)

```python
import requests

IG_USER_ID = "your_ig_user_id"
ACCESS_TOKEN = "your_access_token"  # load from env, never hardcode

def create_media_container(image_url: str, caption: str) -> str:
    """Step 1: Upload media"""
    r = requests.post(
        f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media",
        params={"image_url": image_url, "caption": caption, "access_token": ACCESS_TOKEN}
    )
    r.raise_for_status()
    return r.json()["id"]

def publish_media(container_id: str) -> dict:
    """Step 2: Publish"""
    r = requests.post(
        f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media_publish",
        params={"creation_id": container_id, "access_token": ACCESS_TOKEN}
    )
    r.raise_for_status()
    return r.json()
```

**Required env vars**: `INSTAGRAM_USER_ID`, `META_ACCESS_TOKEN`

### Buffer / Later / Hootsuite

For scheduled posting without the API:
1. Prepare image + caption in a CSV or content calendar
2. Import into scheduling tool
3. Review and queue

## Content Calendar Template

```
| Date | Type | Visual | Caption draft | Hashtags | Status |
|------|------|--------|---------------|----------|--------|
| Mon  | Feed | photo  | "..."         | #tag...  | Draft  |
```

## Scripts

`scripts/resize_images.py` — batch resize folder of images for Instagram formats
