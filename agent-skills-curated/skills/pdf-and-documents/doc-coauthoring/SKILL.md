---
name: doc-coauthoring
description: Collaborative document editing workflows for merging changes, resolving comments, managing versions, and coordinating review cycles. Use when the user asks to coauthor, merge edits, handle tracked changes, resolve review comments, or run a multi-author doc review process. Trigger phrases include "coauthor", "document collaboration", "merge edits", "track changes", "document review", and "resolve comments".
---

# Doc Coauthoring

Collaborative document editing — merging changes, resolving reviews, and version management.

## Coauthoring Workflow

### Phases

```
Draft → Review → Revise → Approve → Publish
```

| Phase | Owner | Duration | Deliverable |
|-------|-------|----------|-------------|
| Draft | Author | Varies | First draft |
| Review | Reviewers | 2–3 days | Comments/tracked changes |
| Revise | Author | 1–2 days | Revised draft |
| Approve | Approver | 1 day | Signed-off final |
| Publish | Author/Publisher | — | Published doc |

## Version Naming

Use semantic versioning for formal documents:

```
v0.1  — initial draft
v0.2  — after author self-edit
v1.0  — first version sent for review
v1.1  — after first round of revisions
v2.0  — major structural rework
```

Store versions as: `document-name-v1.0-YYYY-MM-DD.docx`

## Comment Resolution

When resolving reviewer comments, categorize each:

| Category | Action |
|----------|--------|
| **Accept** | Make the change as suggested |
| **Accept-Modified** | Incorporate the intent, adjusted |
| **Reject-Explained** | Decline with a clear reason in the reply |
| **Discuss** | Flag for synchronous conversation |

Reply to every comment before resolving. Unresolved comments = open decisions.

## Merge Strategies

### Google Docs / Office 365 (simultaneous editing)

- Turn on **Suggesting mode** (Google) or **Track Changes** (Word) before editing
- Use `@mentions` to route questions to specific collaborators
- Resolve all suggestions before marking review complete
- Use document outline headings to assign sections per author

### Markdown / Git-based Docs

```bash
# Author A branches
git checkout -b docs/section-3-update

# Author B branches from same base
git checkout -b docs/section-5-update

# After review: merge A first, then B rebases
git checkout main
git merge --no-ff docs/section-3-update

git checkout docs/section-5-update
git rebase main   # resolve any conflicts
git checkout main
git merge --no-ff docs/section-5-update
```

**Conflict resolution for prose** — when Git marks a conflict in a text block:
1. Read both versions in context
2. Identify the best version or blend the intent of both
3. Never auto-accept without reading; prose merges require judgment

## Review Request Template

```
Subject: Review request: [Document Title] — due [Date]

Hi [Reviewers],

Please review the attached document by [Date].

Focus areas:
- [Section A]: Is the logic sound?
- [Section B]: Does the tone match our audience?
- Any errors of fact in section C?

Please use Suggesting mode (or add comments) rather than direct edits.

Thanks
```

## Document Handoff Checklist

Before marking a document final:

- [ ] All comments resolved or explicitly deferred
- [ ] Track changes accepted or rejected — no open markups
- [ ] Version number updated in filename and header
- [ ] Changelog entry added (date, author, summary of changes)
- [ ] Approved by designated approver
- [ ] Stored in canonical location (Drive folder, Confluence page, etc.)
- [ ] Stakeholders notified

## Changelog Format

At the top of long-lived documents:

```markdown
## Changelog

| Version | Date | Author | Summary |
|---------|------|--------|---------|
| v1.2 | 2024-06-01 | Jane | Added security section |
| v1.1 | 2024-05-15 | John | Revised scope per feedback |
| v1.0 | 2024-05-01 | Jane | Initial release |
```
