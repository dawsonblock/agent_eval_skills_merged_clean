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
