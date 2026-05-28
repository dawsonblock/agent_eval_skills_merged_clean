# Agent Skills Quality Upgrade Plan

This smoke release gates structural validity, not final quality.

Known low-scoring skills:

| Skill | Current issue | Required action |
|---|---|---|
| brand-guidelines | Very low quality score | Expand concrete procedures, examples, constraints, and failure checks |
| theme-factory | Low quality and package defect | Fix package ZIP and expand usage/test guidance |
| canvas-design | Low quality | Add concrete workflow and validation examples |
| frontend-design | Warning | Add stronger implementation standards |
| internal-comms | Warning | Add examples and review checklist |
| skill-creator | Warning | Add package validation and anti-pattern guidance |

Release policy:
- Structural validation must pass.
- Quality warnings are allowed for smoke release.
- No production-quality claim is allowed until warnings are resolved.