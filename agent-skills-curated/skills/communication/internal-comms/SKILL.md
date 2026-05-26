---
name: internal-comms
description: Draft high-clarity internal communication for announcements, incident updates, org changes, all-hands notes, policy rollouts, and leadership messages. Use when users request internal copy for teams or company-wide audiences. Trigger phrases include "internal announcement", "team update", "all-hands", "incident update", "staff update", "org change", and "leadership message".
---

# Internal Comms

Write clear, accountable internal messages that are easy to act on.

## Scope

- In scope: internal announcements, incident/status updates, recaps, policy changes, organization changes.
- Out of scope: external PR statements, legal counsel, or investor communications unless explicitly requested.

## Message Types

| Type | Audience | Tone | Length |
|------|----------|------|--------|
| General announcement | All company | Neutral/positive | 150–300 words |
| Incident update | Affected teams | Factual, calm | 100–200 words |
| Org change | Affected teams | Empathetic, clear | 200–400 words |
| All-hands recap | All company | Energetic, inclusive | 300–500 words |
| Team newsletter | Team | Casual, conversational | 400–700 words |
| Policy change | All company | Direct, professional | 200–400 words |

## Decision Rules

- If urgency is high: lead with status, impact, and next update time.
- If change is sensitive: lead with empathy, then specifics.
- If action is required: include explicit owner, deadline, and channel.
- If uncertainty exists: state what is known, unknown, and when next update arrives.

## Announcement Template

```markdown
Subject: [Clear, specific subject line — no clickbait]

Hi team,

[Opening: context or hook — 1–2 sentences. Why are you writing this now?]

[Body: the key information — what changed, what it means, when it takes effect]

[Impact: what this means for the reader specifically]

[Action items if any:
- By [date]: [what someone needs to do]
]

[Closing: where to ask questions / who to contact]

[Name / Team]
```

## Incident Communication Template

Use during and after service incidents or operational issues.

### Initial Notification

```markdown
**[INCIDENT] [Brief description]**

We're currently investigating an issue affecting [what/who].

**Status**: Investigating
**Impact**: [What users/systems are affected and how]
**Started**: [Time and timezone]

We'll post updates every [15/30/60] minutes.

— [Team Name]
```

## Policy Or Process Change Template

```markdown
Subject: [Policy/Process] update effective [Date]

Hi team,

We're updating [policy/process] effective [date].

**What's changing**
- [change 1]
- [change 2]

**Why now**
[1-2 lines of rationale]

**What you need to do**
- By [date]: [action]

Questions: [channel or owner]
```

### Resolution Update

```markdown
**[RESOLVED] [Brief description]**

The issue affecting [what] has been resolved.

**Root cause**: [Plain language explanation]
**Duration**: [Start time] – [End time] ([X] hours)
**Impact**: [Who/what was affected]
**Fix**: [What we did to resolve it]
**Next steps**: [Post-mortem scheduled for X / monitoring for recurrence]

We apologize for the disruption. Full post-mortem will follow by [date].

— [Team Name]
```

## Org Change Communication

When announcing reorgs, role changes, or leadership changes:

1. **Lead with the person/people**, not the structure
2. **Explain the reasoning** — people need "why"
3. **Be concrete** about what changes and what stays the same
4. **Give a timeline** — when is this effective?
5. **Invite questions** — name a specific way to reach out

```markdown
Subject: Update on our team structure

Hi [Team],

I want to share an update about how [Team/Org] is organized.

Effective [Date], [Name] will be [new role/responsibility]. [1–2 sentences on why this change makes sense — business context, strategic focus, etc.]

**What this means:**
- [Specific change 1]
- [Specific change 2]

**What isn't changing:**
- [Thing 1]

[Name]'s focus will be on [priorities]. [Any reporting changes if relevant.]

Please reach out to me directly with any questions.

[Signature]
```

## All-Hands / Town Hall Recap

```markdown
**[Company/Team] All-Hands — [Month Year] Recap**

Thanks to everyone who joined [live/async]. Here's what we covered:

**Highlights**
- [Key announcement 1]
- [Key announcement 2]
- [Metric or milestone worth celebrating]

**What's coming**
- [Upcoming initiative or milestone]
- [Q[N] focus area]

**Q&A themes**
The most common questions were around [topic]. [Answer or pointer to more info.]

**Recording & slides**: [Link]
**Questions?** Drop them in [channel].
```

## Tone Guide

| Situation | Tone |
|-----------|------|
| Celebration / milestone | Warm, energetic, genuine |
| Bad news (layoffs, incident) | Direct, empathetic, no spin |
| Policy/process change | Clear, respectful, factual |
| Routine update | Efficient, friendly |

Always avoid:
- jargon-heavy corp-speak
- vague reassurances without facts
- passive accountability language ("mistakes were made")

## Output Contract

Include in every draft:
- clear subject line
- audience-appropriate body
- explicit timeline and ownership
- call to action (or explicit no-action-needed)
- escalation/contact channel

## Examples

`examples/general-announcement.md` — product launch announcement
`examples/incident-resolved.md` — service incident resolution notice
`examples/org-change.md` — team restructure message
