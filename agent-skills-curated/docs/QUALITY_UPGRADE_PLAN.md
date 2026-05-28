# Quality Upgrade Plan

This smoke release uses two gates:

- structural_gate: required to pass
- quality_gate: warn-only for smoke release

Current release claim is limited to structural validity plus explicit quality warnings.

## Priority List

| Skill | Current Score | Required Score | Missing Sections (expected) | Priority | Owner/Status |
| --- | ---: | ---: | --- | --- | --- |
| web-and-frontend-development/brand-guidelines | 25 | 70 | clearer trigger phrases, deterministic steps, examples, constraints | P0 | unassigned / planned |
| web-and-frontend-development/theme-factory | 43 | 70 | workflow granularity, validation criteria, failure handling | P0 | unassigned / planned |
| image-and-video-generation/canvas-design | 47 | 70 | task decomposition, explicit deliverables, quality rubric | P1 | unassigned / planned |
| web-and-frontend-development/frontend-design | 55 | 70 | stronger input/output contract, accessibility checklist | P1 | unassigned / planned |
| communication/internal-comms | 58 | 70 | role framing, edge-case handling, examples | P1 | unassigned / planned |
| coding-agents-and-ides/skill-creator | 62 | 70 | stricter evaluation loop, measurable acceptance checks | P2 | unassigned / planned |

## Execution Notes

- Keep structural validation green for all skills while upgrading quality.
- Raise each skill to at least 70 before removing warn-only messaging.
- Track temporary quality exceptions and expiry dates in policy files.