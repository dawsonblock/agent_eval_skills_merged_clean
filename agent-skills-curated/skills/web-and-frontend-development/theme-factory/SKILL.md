---
name: theme-factory
description: Generate production-ready UI themes and token systems for CSS, Tailwind, and shadcn/ui. Use when users ask for a palette, design tokens, dark/light mode mapping, or visual re-theming of an existing app. Trigger phrases include "create a theme", "generate palette", "tailwind theme", "shadcn theme", "design tokens", "dark mode", "light mode", and "re-theme this UI".
---

# Theme Factory

Create coherent themes with explicit semantic mapping and accessibility checks.

## Scope

- In scope: palette creation, semantic token mapping, mode pairing, export snippets.
- Out of scope: complete product redesign, illustration generation, or logo design.

## Input Modes

- Description ("calm fintech dashboard") -> infer mood and contrast strategy.
- Brand colors -> derive systematic scales.
- Reference image -> sample dominant/accent clusters.
- Existing config -> preserve structure and re-theme safely.

## Process

### 1. Establish Anchor Colors

Define anchors:
- `primary` — main action/brand color
- `secondary` — supporting action or brand
- `accent` — highlight, badge, tag
- `neutral` — backgrounds, borders, text
- `destructive` — errors, deletions

### 2. Build Scales

For each anchor, produce consistent steps (50-950 or 100-900). Preserve hue identity while varying luminance for usable UI depth.

### 3. Map Semantic Tokens

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

### 4. Export In Requested Format

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

**Tailwind theme.extend.colors (on request)**
```js
colors: {
  primary: {
    50: '#eff6ff',
    500: '#3b82f6',
    950: '#1e3a5f',
  },
}
```

**shadcn/ui globals.css block (on request)** -> provide :root plus .dark with semantic variables.

## Output Contract

Always return:
- Theme intent (2-3 lines)
- Anchor palette with rationale
- Semantic mapping table
- Export snippet(s)
- Accessibility report and any auto-fixes

## Contrast Validation

Check at minimum:
- `foreground` on `background`: ≥ 7:1 (AAA body text)
- `primary-foreground` on `primary`: ≥ 4.5:1 (AA)
- Muted text on card: ≥ 3:1 (AA large text minimum)

If a pair fails, adjust and re-report corrected values.

## Practical Rules

- Keep hue count controlled; too many primaries reduces coherence.
- Prefer semantic tokens over raw color references in component code.
- Preserve existing project conventions when extending a live codebase.
- Use the `themes/` directory presets only as starting points, not hard constraints.
