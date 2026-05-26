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

## Validation Checklist

Before delivering brand output:
- [ ] All color values are sourced from the input material, not invented.
- [ ] Typography hierarchy is explicit (at minimum: display, body).
- [ ] Color roles are semantic (primary/secondary/accent/neutral/status) with no overlaps.
- [ ] At least one contrast ratio is documented (foreground/background ≥ 4.5:1 AA).
- [ ] BRAND.md is produced and treated as the session's single source of truth.
- [ ] Token export (if requested) is valid JSON and pipeline-compatible.
- [ ] Voice/tone rules include at least one "avoid" pattern.

## Failure Modes

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Colors look inconsistent across surfaces | Skipped semantic role normalization | Re-run step 2: resolve conflicts into one role per color |
| Typography feels generic | Used system-ui fallback without checking source material | Extract actual font declarations from source URL or files |
| Contrast check absent | Skipped accessibility validation | Compute ratios for foreground/background and primary/primary-fg pairs |
| Brand BRAND.md drifts mid-session | Edited values without updating source of truth | Recreate BRAND.md and announce the update |
| Token export causes pipeline errors | Embedded metadata or non-standard nesting | Use flat `{ "key": { "value": "..." } }` structure; strip comments |

## Anti-Patterns

- **Inventing brand values**: Never fabricate colors, fonts, or tone without source material. If no source exists, make assumptions explicit.
- **Overly complex token hierarchies**: More than 4 color roles (primary/secondary/accent/neutral) adds confusion without value for most projects.
- **Skipping contrast for secondary/muted pairs**: Low-contrast muted text is a common accessibility failure; always check.
- **Treating screenshots as canonical**: Screenshot colors shift due to compression. Extract from CSS or design files when possible.
- **Per-output ad hoc values**: Using raw hex values directly in component code instead of token references makes the brand ungovernable.
