---
name: brand-guidelines
description: Extract, document, and apply brand guidelines from existing assets. Use when a user wants to create a brand guidelines document, extract brand colors/fonts/tone from a website or design files, enforce consistent brand identity across components, or generate brand-compliant UI. Trigger phrases include "brand guidelines", "brand identity", "brand colors", "brand consistency", "brand kit", "style guide".
---

# Brand Guidelines

Capture and apply a brand's visual and tonal identity across all outputs.

## Workflow

### 1. Extract Brand Identity

**From a URL** — scrape and analyze:
- CSS custom properties (`--color-*`, `--font-*`)
- Fonts loaded via `<link>` or `@font-face`
- Dominant colors via screenshot color sampling
- Logo, favicon, and icon assets

**From uploaded files** (Figma exports, PDFs, images):
- Identify hex colors from visual samples
- Note font families and weights used
- Capture spacing and layout patterns

### 2. Document the Brand Kit

Produce a concise `BRAND.md` or inline summary with:

```markdown
## Colors
- Primary: #XXXXXX
- Secondary: #XXXXXX
- Accent: #XXXXXX
- Background: #XXXXXX
- Text: #XXXXXX

## Typography
- Display: [FontName], weight [N]
- Body: [FontName], weight [N]
- Mono: [FontName] (if applicable)

## Voice & Tone
- [Adjective]: [one-line explanation]
- Avoid: [patterns to avoid]

## Logo Usage
- Minimum size, clear space, prohibited variations

## Spacing & Layout
- Base unit, grid, breakpoints
```

### 3. Apply to Output

When generating UI or copy:
- Pull exact hex values — never approximate brand colors
- Use only documented font families
- Match the documented voice/tone
- Flag deviations: if a brand color is inaccessible (contrast < 4.5:1 for body text), note it and suggest an accessible alternative

## Design Token Export

Generate a design-token-compatible JSON when requested:

```json
{
  "color": {
    "primary": { "value": "#XXXXXX" },
    "secondary": { "value": "#XXXXXX" }
  },
  "font": {
    "display": { "value": "FontName" },
    "body": { "value": "FontName" }
  }
}
```

## Best Practices

- Never invent brand colors — derive or ask
- Preserve existing brand decisions even if opinionated
- Accessibility trumps brand only when legal risk exists; otherwise document the tension
- Keep `BRAND.md` the single source of truth for the session
