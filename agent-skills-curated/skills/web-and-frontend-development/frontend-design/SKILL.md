---
name: frontend-design
description: Design and implement distinctive, production-grade frontend interfaces for web pages, components, and apps. Use when users ask for UI design, layout polish, landing pages, dashboards, React components, HTML/CSS styling, or visual redesign. Trigger phrases include "design this UI", "build a landing page", "make this look better", "frontend component", "dashboard UI", and "polish the interface".
---

# Frontend Design

Create memorable interfaces with clear artistic direction and production-ready implementation.

## Scope

- In scope: UI direction, layout systems, typography, motion, design tokens, responsive implementation.
- Out of scope: backend architecture, data modeling, and non-frontend infra decisions.

## Workflow

### 1. Define Creative Direction

Before coding, choose:
- audience and product intent
- visual tone (editorial, brutalist, luxury, playful, etc.)
- one memorable differentiator (motion signature, type treatment, composition style)

### 2. Establish System Constraints

Specify:
- type scale and font pairing
- color roles via CSS variables or theme tokens
- spacing rhythm and breakpoints
- accessibility targets

### 3. Implement In Code

Ship real working UI code with:
- semantic markup
- responsive layout behavior
- focused interaction states
- coherent component hierarchy

### 4. Refine High-Impact Details

Prioritize:
- first-load reveal choreography
- strong hero or focal section
- consistent micro-typography (line length, rhythm, contrast)

## Design Rules

- Avoid generic defaults and interchangeable templates.
- Choose expressive fonts; avoid default system-like stacks unless explicitly required.
- Use intentional color hierarchy; avoid flat monochrome without purpose.
- Prefer a few meaningful animations over noisy motion everywhere.
- Build backgrounds with depth (gradients, texture, shape language) where appropriate.

## Responsive Requirements

- Desktop and mobile both render without layout breakage.
- Touch targets remain usable.
- Typography scales cleanly across breakpoints.

## Output Contract

Deliver:
- concise design rationale (tone, constraints, differentiator)
- complete runnable frontend code
- any required assets/config snippets
- brief accessibility and responsiveness notes

## When Working In Existing Systems

- Preserve established design language, component patterns, and token naming.
- Introduce boldness through composition and detail, not by breaking system conventions.

## Validation Checklist

Before delivering frontend design output:
- [ ] Creative direction is stated (visual tone and differentiator).
- [ ] CSS variables or theme tokens are used for colors and spacing (no inline ad-hoc values).
- [ ] Markup is semantic (landmark elements, heading hierarchy).
- [ ] Responsive behavior is tested at ≥ 2 breakpoints.
- [ ] All interactive elements have visible focus states.
- [ ] Touch targets are ≥ 44×44 px.
- [ ] Accessibility target (WCAG AA minimum) is met for color contrast.

## Failure Modes

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Layout breaks on mobile | Fixed pixel widths without responsive breakpoints | Replace with `max-width`, `clamp()`, or flex/grid fractions |
| Typography inconsistent across components | Ad-hoc `font-size` per element | Define and apply a type scale via CSS variables or Tailwind config |
| Interactive states missing | Hover/focus not defined | Add `:hover`, `:focus-visible`, `:active` to all interactive elements |
| Colors clash or feel random | No color role hierarchy | Define semantic roles (primary/surface/text/border) and reference only those |
| Animation feels jarring | No `prefers-reduced-motion` guard | Wrap all motion in `@media (prefers-reduced-motion: no-preference)` |

## Anti-Patterns

- **Template cloning without differentiation**: Delivering a generic hero + card layout without applying the stated creative direction wastes the skill's purpose.
- **Inline styles for theming**: Inline styles can't be overridden by CSS variables; use class-level or variable-based styling.
- **Div soup**: Non-semantic markup breaks screen readers and SEO; use `<nav>`, `<main>`, `<section>`, `<article>`, `<header>`, `<footer>`.
- **Motion without purpose**: Gratuitous transitions on every element reduce performance and distract; each animation should serve the UX intent.
- **Ignoring the existing system**: When working inside an existing codebase, introducing new design tokens or components not already in the system creates divergence; extend, don't replace.

## Examples

**Good trigger**: "Design a modern SaaS landing page with a dark editorial feel and a bold typographic hero."
**Good trigger**: "Polish this dashboard — the metrics cards look too flat and generic."
**Poor trigger (too vague)**: "Make it look nicer." — Ask for clarifying intent before proceeding.
