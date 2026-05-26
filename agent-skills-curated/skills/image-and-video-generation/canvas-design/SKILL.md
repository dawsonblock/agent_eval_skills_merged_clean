---
name: canvas-design
description: Design and render visual assets using HTML5 Canvas or node-canvas. Use when users request banners, posters, social graphics, composited images, or canvas-based visuals with explicit dimensions and export formats. Trigger phrases include "canvas design", "html canvas", "draw on canvas", "create banner", "generate graphic", "social image", and "canvas animation".
---

# Canvas Design

Produce high-quality raster visuals with deterministic, reproducible canvas code.

## Scope

- In scope: static compositions, typography layouts, image compositing, simple animation frames, server-side rendering.
- Out of scope: vector authoring pipelines, 3D engines, and full interactive design tools.

## Workflow

### 1. Lock Output Spec

Define before coding:
- width x height
- target platform (OG, Instagram, YouTube, print)
- output format (PNG/JPEG/WebP/PDF via downstream tool)
- text hierarchy and brand constraints

### 2. Build Composition Layers

Order layers explicitly:
- background (solid, gradient, texture)
- structural shapes
- imagery
- typography
- overlays/effects

### 3. Validate Readability

Confirm:
- text remains legible at target display size
- key content stays inside safe margins
- contrast is acceptable for body and headline text

### 4. Export With Deterministic Naming

Include output path and format decisions in the final response.

## Canvas Fundamentals

```javascript
const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');

// Set dimensions (always set via JS, not CSS alone)
canvas.width = 1200;
canvas.height = 630;   // Open Graph / Twitter card size
```

## Reusable Building Blocks

### Social Banner (1200x630)

```javascript
// Background gradient
const grad = ctx.createLinearGradient(0, 0, 1200, 630);
grad.addColorStop(0, '#6366f1');
grad.addColorStop(1, '#a855f7');
ctx.fillStyle = grad;
ctx.fillRect(0, 0, 1200, 630);

// Title text
ctx.fillStyle = '#ffffff';
ctx.font = 'bold 72px Inter, sans-serif';
ctx.textAlign = 'center';
ctx.fillText('Your Title', 600, 280);

// Subtitle
ctx.font = '32px Inter, sans-serif';
ctx.fillStyle = 'rgba(255,255,255,0.8)';
ctx.fillText('Your subtitle here', 600, 360);
```

### Rounded Card Primitive

```javascript
function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.lineTo(x + w - r, y);
  ctx.quadraticCurveTo(x + w, y, x + w, y + r);
  ctx.lineTo(x + w, y + h - r);
  ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
  ctx.lineTo(x + r, y + h);
  ctx.quadraticCurveTo(x, y + h, x, y + h - r);
  ctx.lineTo(x, y + r);
  ctx.quadraticCurveTo(x, y, x + r, y);
  ctx.closePath();
}
```

### Image Compositing (Node.js)

```javascript
const { createCanvas, loadImage } = require('canvas');
const canvas = createCanvas(1200, 630);
const ctx = canvas.getContext('2d');
const img = await loadImage('https://example.com/photo.jpg');
ctx.drawImage(img, 0, 0, 1200, 630);
```

## Typography And Fonts

Load custom fonts explicitly to avoid fallback drift:

```javascript
// Browser
const font = new FontFace('Inter', 'url(/canvas-fonts/Inter-Regular.ttf)');
await font.load();
document.fonts.add(font);

// Node (node-canvas)
const { registerFont } = require('canvas');
registerFont('./canvas-fonts/Inter-Regular.ttf', { family: 'Inter' });
```

## Export Patterns

```javascript
// Browser — PNG download
const link = document.createElement('a');
link.download = 'design.png';
link.href = canvas.toDataURL('image/png');
link.click();

// Node — write to file
const fs = require('fs');
const out = fs.createWriteStream('design.png');
canvas.createPNGStream().pipe(out);
```

## Standard Sizes

| Format | Dimensions |
|--------|------------|
| Open Graph / Twitter card | 1200 × 630 |
| Instagram square | 1080 × 1080 |
| Instagram story | 1080 × 1920 |
| LinkedIn banner | 1584 × 396 |
| YouTube thumbnail | 1280 × 720 |
| A4 @ 96dpi | 794 × 1123 |

## Library Selection

- Fabric.js -> interactive object editing.
- Konva.js -> staged layers and event-heavy canvases.
- node-canvas -> server-side deterministic rendering.
- OffscreenCanvas -> worker-based rendering for performance.

## Output Contract

When responding, include:
- final dimensions and rationale
- complete runnable code block
- explicit dependency notes (if any)
- export command or write path

## Validation Checklist

Before delivering canvas output:
- [ ] Width and height set via `canvas.width` / `canvas.height`, not CSS alone.
- [ ] Layer order is explicit: background → shapes → images → typography → overlays.
- [ ] Text contrast is verified against its background layer.
- [ ] Font is loaded (registered) before `ctx.fillText` calls.
- [ ] Export path and format are documented in the response.
- [ ] All async operations (`loadImage`, font loading) are awaited before draw calls.
- [ ] Output dimensions match the target platform spec.

## Failure Modes

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Canvas renders blank | `ctx` operations before `canvas.width/height` set | Set dimensions before any draw calls |
| Text appears pixelated | CSS size used instead of JS canvas dimensions | `canvas.width = W; canvas.height = H` in JS before drawing |
| Font fallback renders | Font not loaded/registered before `fillText` | Await `font.load()` and `document.fonts.add(font)` or `registerFont()` |
| Async image not drawn | `loadImage` not awaited | Always `await loadImage(...)` before `drawImage` |
| PNG appears transparent on some viewers | Background layer omitted | Always fill a background rect before compositing layers |
| Node-canvas SIGSEGV | Native binary mismatch | `npm rebuild canvas` after Node version change |

## Anti-Patterns

- **CSS-only sizing**: Setting dimensions only via CSS scales the rendering context but keeps the internal resolution at default (300×150), producing blurry output.
- **Hardcoded coordinates without constants**: Magic numbers spread throughout draw calls make composition changes fragile; define `W`, `H`, `MARGIN`, `SAFE_X` constants.
- **Skipping safe zones**: Content near canvas edges clips on some platforms; apply a consistent inset (e.g., 60px for social formats).
- **Blocking the main thread with synchronous image I/O**: All image operations must be async in both browser and Node environments.
- **Omitting format in the response**: Always state the output path, format (PNG/JPEG/WebP), and quality setting so the user can reproduce results.
