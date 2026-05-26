---
name: theme-factory
description: Generate production-ready UI themes and token systems for CSS, Tailwind, and shadcn/ui. Use when users ask to apply a theme, theme an existing app, change colors and fonts, map dark/light mode tokens, or turn a palette into semantic variables. Trigger phrases include "apply a theme", "theme this app", "change the colors", and "re-theme this UI". Do not use for brand identity extraction, logo work, or full UI redesigns; use brand-guidelines or frontend-design instead.
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

## Validation Checklist

Before delivering a theme:
- [ ] All anchor colors are defined (primary, secondary, accent, neutral, destructive).
- [ ] Semantic token mapping is provided for both light and dark modes.
- [ ] At minimum three contrast pairs are checked (fg/bg, primary/primary-fg, muted/card).
- [ ] At least one export snippet is included in the requested format.
- [ ] Hue count is justified if more than 2 anchors are used.
- [ ] Auto-corrected values include before/after ratios.

## Failure Modes

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Dark mode looks washed out | Neutral scale not inverted properly | Swap luminance poles: light bg (neutral-50) → dark bg (neutral-950) |
| Primary button text unreadable | Insufficient primary/primary-fg contrast | Adjust primary-foreground to nearest value with ≥ 4.5:1 |
| Theme feels incoherent | Too many anchor hues (>3) | Consolidate: one primary, one accent, neutral scale |
| Tailwind class names not resolving | Colors not registered under `extend.colors` | Add entries inside `theme.extend.colors`, not `theme.colors` |
| shadcn/ui component overrides ignored | Variables missing HSL format | shadcn expects `H S% L%` format without `hsl()` wrapper |

## Anti-Patterns

- **Raw hex in semantic tokens**: Semantic tokens must reference the scale, not direct hex values; otherwise dark-mode toggle breaks.
- **Skipping scale steps**: Jumping from 100 to 900 without intermediate stops limits UI depth; produce at minimum 100/200/300/500/700/900.
- **Copying palette without checking contrast**: A palette that looks good in design tools often fails WCAG at actual font sizes.
- **Over-animating theme transitions**: CSS variable transitions on every element tank performance; scope transitions to `background-color` and `color` only.
- **Ignoring input mode**: Applying a "calm fintech" palette to a user-supplied brand palette silently overrides their intent.

## Examples

- "Apply a theme to this dashboard and give me matching Tailwind tokens."
- "Theme this app for dark mode and export shadcn/ui variables."
- "Change the colors and fonts, but keep the existing layout."
