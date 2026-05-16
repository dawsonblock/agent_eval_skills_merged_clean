---
name: pm-skills
description: Project management workflows — planning, tracking, and coordination for software and product teams. Use when the user wants to create a project plan, write a PRD, create tickets, define sprint goals, write a RACI matrix, run a retrospective, or manage project scope. Trigger phrases include "project plan", "project management", "sprint planning", "PRD", "product requirements", "roadmap", "milestone", "retro", "standup", "RACI", "risk register", "project timeline".
---

# PM Skills

Project management workflows for software and product teams.

## Document Templates

### Product Requirements Document (PRD)

```markdown
# PRD: [Feature Name]

## Overview
One-paragraph summary of what we're building and why.

## Problem Statement
What user problem or business need does this solve?
Why does it matter now?

## Goals & Success Metrics
| Goal | Metric | Target |
|------|--------|--------|
| ...  | ...    | ...    |

## Non-Goals
What is explicitly out of scope for this version.

## User Stories
- As a [user type], I want to [action] so that [outcome].

## Functional Requirements
1. The system must...
2. Users can...

## Non-Functional Requirements
- Performance: ...
- Security: ...
- Accessibility: ...

## Technical Considerations
Known constraints, dependencies, or architectural notes.

## Open Questions
- [ ] Decision needed by [date]: ...

## Timeline
| Milestone | Date |
|-----------|------|
| Design complete | ... |
| Engineering complete | ... |
| QA complete | ... |
| Launch | ... |
```

### Sprint Planning Template

```markdown
## Sprint [N] — [Dates]

**Goal**: [One sentence describing the sprint's primary objective]

### Committed Work
| Ticket | Title | Points | Owner |
|--------|-------|--------|-------|
| ...    | ...   | ...    | ...   |

**Total Points**: X

### Definition of Done
- [ ] Code reviewed and merged
- [ ] Tests written and passing
- [ ] Deployed to staging
- [ ] QA sign-off
```

### RACI Matrix

```markdown
## RACI: [Project Name]

| Task | PM | Eng Lead | Designer | Stakeholder |
|------|----|----------|----------|-------------|
| Requirements | R/A | C | C | I |
| Design | I | C | R/A | I |
| Implementation | I | R/A | I | I |
| QA | A | R | I | I |
| Launch | A | R | R | I |

R = Responsible, A = Accountable, C = Consulted, I = Informed
```

### Risk Register

```markdown
## Risk Register

| Risk | Likelihood | Impact | Mitigation | Owner |
|------|------------|--------|------------|-------|
| API dependency delayed | Medium | High | Stub API early | Eng Lead |
| Scope creep | High | Medium | Weekly scope review | PM |
```

## Sprint Ceremonies

### Daily Standup (async or sync)

Format:
- **Yesterday**: What did I complete?
- **Today**: What will I work on?
- **Blockers**: What is blocking me?

### Retrospective

**Start / Stop / Continue**:
- Start doing: [what should we add?]
- Stop doing: [what isn't working?]
- Continue doing: [what's working well?]

**4Ls**:
- Liked: What went well?
- Learned: What did we learn?
- Lacked: What was missing?
- Longed For: What do we wish we had?

## Estimation

**Story points (Fibonacci)**: 1, 2, 3, 5, 8, 13, 21

| Points | Description |
|--------|-------------|
| 1 | Trivial, < 1 hour |
| 2 | Small, half-day |
| 3 | Clear, ~1 day |
| 5 | Medium complexity, 2–3 days |
| 8 | Large, needs breakdown |
| 13+ | Too big — split it |

## Project Status Report

```markdown
## [Project] — Status Update [Date]

**Status**: 🟢 On Track / 🟡 At Risk / 🔴 Off Track

**Summary**: [2–3 sentences on progress]

**Completed this week**: ...
**Planned next week**: ...
**Risks / Blockers**: ...
**Decisions needed**: ...
```
