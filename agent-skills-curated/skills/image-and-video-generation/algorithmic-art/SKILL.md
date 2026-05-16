---
name: algorithmic-art
description: Generate algorithmic and generative art using code — creative visuals produced programmatically. Use when the user wants to create generative art, procedural patterns, animated canvas sketches, L-systems, fractals, particle systems, noise-based textures, or code-driven visual art. Trigger phrases include "generative art", "algorithmic art", "p5.js", "canvas art", "procedural art", "fractal", "L-system", "particle system", "creative coding", "generative pattern".
---

# Algorithmic Art

Generate creative, visually compelling art through code.

## Technology Choices

| Approach | Best for |
|----------|----------|
| **p5.js** (JS) | Interactive sketches, animations, beginners |
| **HTML5 Canvas** (raw JS) | Lightweight, no deps, embeddable |
| **SVG + JS** | Scalable outputs, print-ready |
| **Python + matplotlib/PIL** | Static images, notebooks |
| **Python + turtle** | Simple patterns, educational |

Default to **p5.js** for interactive/animated work and **HTML Canvas** for single-file artifacts.

## Core Patterns

### Noise-Based Textures (Perlin/Simplex)

```javascript
// p5.js — flow field
function setup() { createCanvas(800, 800); }
function draw() {
  for (let x = 0; x < width; x += 20) {
    for (let y = 0; y < height; y += 20) {
      let angle = noise(x * 0.005, y * 0.005) * TWO_PI * 2;
      let v = p5.Vector.fromAngle(angle);
      stroke(0, 30);
      line(x, y, x + v.x * 15, y + v.y * 15);
    }
  }
}
```

### Fractal / L-System

```javascript
// Recursive tree (Canvas)
function drawTree(ctx, x, y, angle, depth) {
  if (depth === 0) return;
  const len = depth * 10;
  const x2 = x + Math.cos(angle) * len;
  const y2 = y - Math.sin(angle) * len;
  ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x2, y2); ctx.stroke();
  drawTree(ctx, x2, y2, angle - 0.4, depth - 1);
  drawTree(ctx, x2, y2, angle + 0.4, depth - 1);
}
```

### Particle System

```javascript
class Particle {
  constructor() { this.reset(); }
  reset() { this.x = random(width); this.y = random(height); this.vx = random(-1,1); this.vy = random(-2,0); this.life = 255; }
  update() { this.x += this.vx; this.y += this.vy; this.life -= 3; if (this.life <= 0) this.reset(); }
  draw() { stroke(255, this.life); point(this.x, this.y); }
}
```

## Templates

The `templates/` directory contains starter sketches:
- `templates/flow-field.js` — Perlin noise flow field
- `templates/fractal-tree.js` — recursive branching tree
- `templates/particle-system.js` — animated particle emitter
- `templates/voronoi.js` — Voronoi diagram generator

## Design Principles for Algorithmic Art

- **Seed control**: expose a `seed` parameter for reproducibility
- **Palette first**: choose 3–5 colors before writing draw logic
- **Iteration**: start simple, add one generative element at a time
- **Aspect ratio**: common choices are 1:1, 4:5, 2:3 for social; A4 for print
- **Export**: for static output, use `saveCanvas()` (p5.js) or write to file (PIL)

## Output Formats

- **Interactive**: single `.html` file with embedded p5.js via CDN
- **Static image**: PNG via `saveCanvas()` or `PIL.Image.save()`
- **SVG**: use `createGraphics(w, h, SVG)` in p5.js with p5.svg library
