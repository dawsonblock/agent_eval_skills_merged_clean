---
name: theme-factory
description: Generate complete, cohesive UI themes (CSS custom properties, Tailwind config, shadcn/ui theme tokens) from a description, reference image, or brand kit. Use when the user asks to create a theme, generate a color palette, customize Tailwind colors, style shadcn components, or produce a dark/light mode pair. Trigger phrases include "create a theme", "generate a color palette", "tailwind theme", "shadcn theme", "design tokens", "dark mode", "light mode".
---

# Theme Factory

Generate production-ready UI themes from any starting point.

## Input Modes

| Input | What to do |
|-------|------------|
| Description ("a calm fintech app") | Generate palette from semantic intent |
| Brand colors (hex values) | Derive full palette via lightness/saturation scaling |
| Reference image URL | Sample dominant and accent colors |
| Existing CSS/Tailwind config | Extend or harmonize with existing values |

## Process

### Step 1 — Establish Core Palette

Pick or derive 5 anchor colors:
- `primary` — main action/brand color
- `secondary` — supporting action or brand
- `accent` — highlight, badge, tag
- `neutral` — backgrounds, borders, text
- `destructive` — errors, deletions

### Step 2 — Generate Shades

For each anchor, produce a 50–950 shade scale (or 9-step 100–900):
- Lighten by adjusting L in HSL, keeping H/S stable
- Ensure each step has sufficient contrast from adjacent steps

### Step 3 — Map Semantic Tokens

```
background    → neutral-50 (light) / neutral-950 (dark)
foreground    → neutral-950 (light) / neutral-50 (dark)
card          → neutral-100 (light) / neutral-900 (dark)
border        → neutral-200 (light) / neutral-800 (dark)
input         → neutral-200 (light) / neutral-800 (dark)
ring          → primary-500
muted         → neutral-100 (light) / neutral-800 (dark)
muted-fg      → neutral-500
```

### Step 4 — Output Formats

**CSS Custom Properties (default)**
```css
:root {
  --background: 0 0% 100%;
  --foreground: 240 10% 3.9%;
  --primary: 221 83% 53%;
  --primary-foreground: 210 40% 98%;
  /* ... */
}
.dark {
  --background: 240 10% 3.9%;
  --foreground: 0 0% 98%;
  /* ... */
}
```

**Tailwind `theme.extend.colors` (on request)**
```js
colors: {
  primary: {
    50: '#eff6ff',
    500: '#3b82f6',
    950: '#1e3a5f',
  },
}
```

**shadcn/ui `globals.css` drop-in (on request)** — produces the full `:root` + `.dark` block compatible with shadcn conventions.

## Contrast Validation

After generating, check critical pairs:
- `foreground` on `background`: ≥ 7:1 (AAA body text)
- `primary-foreground` on `primary`: ≥ 4.5:1 (AA)
- Muted text on card: ≥ 3:1 (AA large text minimum)

Report any failures and auto-fix by adjusting lightness.

## Bundled Themes

The `themes/` directory contains ready-to-use starting points:
- `themes/ocean.css` — cool blues and teals
- `themes/forest.css` — greens and earthy neutrals
- `themes/dusk.css` — warm purples and rose
- `themes/mono.css` — grayscale with single accent
