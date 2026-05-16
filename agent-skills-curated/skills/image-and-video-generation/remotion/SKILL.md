---
name: remotion
description: Generate programmatic video using Remotion — React-based video generation. Use when the user wants to create videos with code, animate React components to video, render data-driven video, generate explainer animations, or produce MP4/GIF outputs from JSX. Trigger phrases include "remotion", "programmatic video", "react video", "animate to video", "code video", "render video from code", "data driven video", "video generation", "animated explainer".
---

# Remotion

Create videos programmatically using React components.

## Quick Start

```bash
npx create-video@latest
cd my-video
npm start          # opens Remotion Studio at localhost:3000
npm run build      # renders to out/video.mp4
```

## Core Concepts

### Composition

```tsx
// src/Root.tsx
import { Composition } from 'remotion';
import { MyVideo } from './MyVideo';

export const RemotionRoot = () => (
  <>
    <Composition
      id="MyVideo"
      component={MyVideo}
      durationInFrames={150}   // 5s at 30fps
      fps={30}
      width={1920}
      height={1080}
      defaultProps={{ title: 'Hello' }}
    />
  </>
);
```

### Animation with `useCurrentFrame`

```tsx
import { useCurrentFrame, interpolate, spring, useVideoConfig } from 'remotion';

export const MyVideo: React.FC<{ title: string }> = ({ title }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Linear interpolation: fade in over first 20 frames
  const opacity = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: 'clamp' });

  // Spring animation
  const scale = spring({ frame, fps, config: { damping: 200 } });

  return (
    <div style={{ opacity, transform: `scale(${scale})`, width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <h1 style={{ fontSize: 80, color: 'white' }}>{title}</h1>
    </div>
  );
};
```

### Sequences and Timing

```tsx
import { Sequence } from 'remotion';

// Sequence: offset child's time by `from` frames
<Sequence from={30} durationInFrames={60}>
  <SubtitleText text="Second scene" />
</Sequence>
```

### Audio and Video Assets

```tsx
import { Audio, Video, staticFile } from 'remotion';

<Audio src={staticFile('background.mp3')} volume={0.5} />
<Video src={staticFile('clip.mp4')} startFrom={0} endAt={90} />
```

## Rendering

```bash
# Render with CLI
npx remotion render MyVideo out/video.mp4

# Render with custom props
npx remotion render MyVideo out/video.mp4 --props='{"title":"Custom"}'

# Render still (single frame)
npx remotion still MyVideo out/thumb.png --frame=30

# Render GIF
npx remotion render MyVideo out/animation.gif
```

## Common Compositions

### Instagram Reel (9:16, 30fps)

```tsx
<Composition id="Reel" component={Reel}
  durationInFrames={900} fps={30} width={1080} height={1920} />
```

### YouTube Thumbnail Reveal (16:9)

```tsx
<Composition id="Thumbnail" component={ThumbnailReveal}
  durationInFrames={60} fps={30} width={1280} height={720} />
```

## Lambda Rendering (Scale)

```bash
npx remotion lambda functions deploy
npx remotion lambda render MyVideo
```

## Key Packages

| Package | Purpose |
|---------|---------|
| `@remotion/shapes` | SVG shape primitives |
| `@remotion/motion-blur` | Per-frame motion blur |
| `@remotion/gif` | Render GIFs |
| `@remotion/lambda` | Cloud render on AWS Lambda |
| `@remotion/google-fonts` | Web font loading |
| `@remotion/noise` | Perlin noise utilities |
