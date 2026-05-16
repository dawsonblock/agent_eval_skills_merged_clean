---
name: instagram-reel-editor
description: Create, edit, and produce Instagram Reels — short-form vertical video content. Use when the user wants to create Reels, edit video clips, add captions or music to vertical video, generate Reel scripts, or automate Reel production with FFmpeg or Remotion. Trigger phrases include "instagram reel", "reel", "short video", "vertical video", "reels editor", "create a reel", "video captions", "video montage".
---

# Instagram Reel Editor

Create and edit Instagram Reels (vertical short-form video, 9:16, up to 90s).

## Reel Specifications

| Property | Value |
|----------|-------|
| Aspect ratio | 9:16 (1080 × 1920) |
| Duration | 3–90 seconds |
| Frame rate | 30fps recommended |
| Format | MP4 (H.264 + AAC) |
| Max file size | 4 GB |
| Safe zone for UI | 250px top, 400px bottom |

## FFmpeg Workflows

### Convert Landscape to Vertical (Crop Center)

```bash
ffmpeg -i input.mp4 \
  -vf "crop=ih*9/16:ih,scale=1080:1920" \
  -c:v libx264 -crf 23 -preset fast \
  -c:a aac -b:a 128k \
  output_reel.mp4
```

### Add Burn-In Captions

```bash
ffmpeg -i input.mp4 \
  -vf "subtitles=captions.srt:force_style='FontName=Arial,FontSize=24,PrimaryColour=&Hffffff,Bold=1'" \
  output_captioned.mp4
```

### Trim a Clip

```bash
ffmpeg -i input.mp4 -ss 00:00:05 -to 00:00:35 -c copy trimmed.mp4
```

### Concatenate Multiple Clips

```bash
# Create concat list
printf "file 'clip1.mp4'\nfile 'clip2.mp4'\nfile 'clip3.mp4'" > list.txt
ffmpeg -f concat -safe 0 -i list.txt -c copy final.mp4
```

### Add Music (Mix with Original Audio)

```bash
ffmpeg -i video.mp4 -i music.mp3 \
  -filter_complex "[0:a]volume=0.3[a0];[1:a]volume=0.8[a1];[a0][a1]amix=inputs=2[aout]" \
  -map 0:v -map "[aout]" -shortest output.mp4
```

## Reel Script Structure

A typical 30-second Reel:
1. **Hook** (0–3s): Bold statement or question — grab attention immediately
2. **Content** (3–25s): 3–5 quick tips / scenes / beats
3. **CTA** (25–30s): "Follow for more" / "Link in bio" / question for comments

## Caption Generation (Python + Whisper)

```python
import whisper, json

model = whisper.load_model("base")
result = model.transcribe("video.mp4", word_timestamps=True)

# Export SRT
with open("captions.srt", "w") as f:
    for i, seg in enumerate(result["segments"], 1):
        start = format_timestamp(seg["start"])
        end   = format_timestamp(seg["end"])
        f.write(f"{i}\n{start} --> {end}\n{seg['text'].strip()}\n\n")
```

## Programmatic Reel (Remotion)

For code-driven Reels, use the `remotion` skill. Key config for Reels:

```tsx
// remotion.config.ts
Config.setVideoImageFormat("jpeg");
Config.setPixelFormat("yuv420p");
// Composition props: width=1080, height=1920, fps=30
```

## Tools & References

- `scripts/` — helper bash scripts for common FFmpeg recipes
- `references/reel-checklist.md` — pre-publish checklist
- **CapCut** / **DaVinci Resolve** for manual editing
- **Remotion** for React-based programmatic video
