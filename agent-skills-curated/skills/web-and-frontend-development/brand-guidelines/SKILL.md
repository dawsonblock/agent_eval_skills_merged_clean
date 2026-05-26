---
name: brand-guidelines
description: Extract, normalize, and apply a brand system across UI, docs, and assets. Use when users ask for a brand kit, style guide, design tokens, tone rules, or brand-consistent output. Trigger phrases include "brand guidelines", "brand identity", "brand kit", "style guide", "brand colors", "brand fonts", "design tokens", and "make this on-brand".
---

# Brand Guidelines

Build a reliable brand system from source material, then enforce it in generated output.

## Scope

- In scope: colors, typography, spacing, icon/logo usage, voice/tone, token export, compliance checks.
- Out of scope: legal trademark advice, original logo design, or fabricated brand values without source material.

## Inputs To Request If Missing

- Primary source: website URL, design files, or existing docs.
- Target surface: web app, slide deck, docs, emails, or full cross-channel kit.
- Accessibility target: WCAG AA or AAA.

## Workflow

### 1. Extract Signals

From URL:
- collect CSS variables and typography declarations
- capture dominant palette and accent usage
- identify logo treatment and icon style

From files (Figma/PDF/images):
- sample canonical hex values
- record font family, weight, and hierarchy
- infer spacing rhythm and corner radius patterns

### 2. Normalize Into Canonical Rules

Resolve conflicts into one standard:
- choose one primary and one secondary family
- limit color roles (primary, secondary, accent, neutral, status)
- define spacing scale and component density

### 3. Publish A Single Source Of Truth

Write a concise BRAND.md:

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

### 4. Apply And Enforce

- Use exact token names and values, not approximations.
- Reject ad-hoc colors and undeclared fonts.
- Match documented tone in copy outputs.
- If contrast fails, propose corrected alternatives and explain the delta.

## Output Contract

Return these sections in order:
- Brand Summary (3-5 lines)
- Token Table (colors, type, spacing)
- Usage Rules (do/don't)
- Accessibility Notes
- Optional machine-readable tokens (if requested)

## Token Export (When Requested)

Produce JSON compatible with token pipelines:

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

## Quality Checklist

- No invented brand values without an explicit assumption block.
- Typography hierarchy is explicit (display/body/mono or display/body only).
- Color roles are semantic and non-overlapping.
- At least one contrast check is documented.
- BRAND.md remains the authoritative source for the session.
