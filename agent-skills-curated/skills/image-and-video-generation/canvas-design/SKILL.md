---
name: canvas-design
description: Generate and edit visual designs using HTML5 Canvas. Use when the user wants to create banners, graphics, image compositions, charts, or visual assets using Canvas API or canvas-based libraries. Trigger phrases include "canvas design", "html canvas", "create a banner", "generate image", "draw on canvas", "canvas animation", "generate a graphic", "create visual asset".
---

# Canvas Design

Create visual designs, graphics, and image compositions using HTML5 Canvas.

## Canvas Fundamentals

```javascript
const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');

// Set dimensions (always set via JS, not CSS alone)
canvas.width = 1200;
canvas.height = 630;   // Open Graph / Twitter card size
```

## Common Design Tasks

### Social Media Banner (1200×630 / OG)

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

### Rounded Rectangle (Card)

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

### Draw Image from URL (Node.js with canvas package)

```javascript
const { createCanvas, loadImage } = require('canvas');
const canvas = createCanvas(1200, 630);
const ctx = canvas.getContext('2d');
const img = await loadImage('https://example.com/photo.jpg');
ctx.drawImage(img, 0, 0, 1200, 630);
```

## Canvas Fonts

Bundled web-safe fonts for canvas rendering are in `canvas-fonts/`. Load custom fonts:

```javascript
// Browser
const font = new FontFace('Inter', 'url(/canvas-fonts/Inter-Regular.ttf)');
await font.load();
document.fonts.add(font);

// Node (node-canvas)
const { registerFont } = require('canvas');
registerFont('./canvas-fonts/Inter-Regular.ttf', { family: 'Inter' });
```

## Export

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

## Common Canvas Sizes

| Format | Dimensions |
|--------|------------|
| Open Graph / Twitter card | 1200 × 630 |
| Instagram square | 1080 × 1080 |
| Instagram story | 1080 × 1920 |
| LinkedIn banner | 1584 × 396 |
| YouTube thumbnail | 1280 × 720 |
| A4 @ 96dpi | 794 × 1123 |

## Libraries

- **Fabric.js** — object-oriented canvas (draggable/selectable objects)
- **Konva.js** — layers, groups, events
- **node-canvas** — server-side Canvas for Node.js
- **OffscreenCanvas** — Web Worker canvas rendering
