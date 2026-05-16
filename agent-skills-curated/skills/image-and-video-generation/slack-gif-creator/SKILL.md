---
name: slack-gif-creator
description: Create GIFs optimized for Slack — reactions, status animations, team memes, and custom emoji. Use when the user wants to create a Slack GIF, custom Slack emoji, animated reaction, loop animation, or team meme GIF. Trigger phrases include "slack gif", "slack emoji", "create gif", "animated gif", "reaction gif", "custom emoji", "team gif", "gif for slack".
---

# Slack GIF Creator

Create GIFs for Slack — custom emoji, reactions, and team animations.

## Slack GIF/Emoji Specs

| Type | Size | Dimensions | Format |
|------|------|------------|--------|
| Custom emoji | < 128 KB | 128 × 128 px (max) | GIF, PNG, JPG |
| Message GIF | < 10 MB | Any (Slack scales) | GIF |
| Status emoji | < 128 KB | 128 × 128 px | GIF, PNG |

**GIF tips for Slack emoji**:
- Keep under 128 KB — palettize aggressively
- 128 × 128 or smaller
- 4–8 frames @ 150ms/frame for subtle loops
- Transparent background preferred

## FFmpeg → GIF Pipeline

### Video Clip to GIF

```bash
# Step 1: generate optimized palette
ffmpeg -i input.mp4 -vf "fps=15,scale=480:-1:flags=lanczos,palettegen" palette.png

# Step 2: apply palette to produce high-quality GIF
ffmpeg -i input.mp4 -i palette.png \
  -lavfi "fps=15,scale=480:-1:flags=lanczos[x];[x][1:v]paletteuse" \
  output.gif
```

### Make a Slack Emoji GIF (128×128)

```bash
ffmpeg -i input.mp4 -ss 00:00:02 -t 2 \
  -vf "fps=10,scale=128:128:flags=lanczos,palettegen=stats_mode=diff" palette.png

ffmpeg -i input.mp4 -i palette.png -ss 00:00:02 -t 2 \
  -lavfi "fps=10,scale=128:128:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=5" \
  emoji.gif
```

### Optimize Existing GIF (Gifsicle)

```bash
# Install: brew install gifsicle
gifsicle -O3 --colors 64 input.gif -o output.gif
```

## Python: Pillow GIF Creation

```python
from PIL import Image, ImageDraw, ImageFont
import os

frames = []
colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96E6A1']

for i, color in enumerate(colors):
    img = Image.new('RGBA', (128, 128), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([16, 16, 112, 112], fill=color)
    draw.text((64, 64), '🎉', anchor='mm', font_size=48)
    frames.append(img.convert('P', palette=Image.ADAPTIVE))

frames[0].save(
    'party.gif',
    save_all=True,
    append_images=frames[1:],
    loop=0,
    duration=200,   # ms per frame
    optimize=True,
    transparency=0,
)
```

## Core Workflow

1. **Source**: choose a video clip, image sequence, or draw frames in code
2. **Trim**: extract just the best 2–4 seconds for a smooth loop
3. **Scale**: set target dimensions (128px for emoji, up to 480px for messages)
4. **Palette optimize**: use two-pass FFmpeg or Gifsicle for crisp colors
5. **Size check**: verify < 128 KB for emoji, < 10 MB for messages
6. **Upload**: Slack → Customize Workspace → Custom Emoji → Add Emoji

## Helper Scripts

`core/` contains reusable helpers:
- `core/video_to_gif.sh` — two-pass FFmpeg GIF from any video
- `core/optimize_gif.sh` — Gifsicle optimization wrapper
- `core/emoji_gif.py` — Pillow-based code-drawn animated emoji
