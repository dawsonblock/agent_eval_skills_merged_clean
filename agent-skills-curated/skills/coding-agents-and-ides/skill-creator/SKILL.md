---
name: skill-creator
description: Create, refactor, and package high-quality agent skills with strong trigger metadata, concise SKILL.md instructions, and reusable scripts/references/assets. Use when users ask to build a new skill, improve an existing skill, fix trigger behavior, or prepare a distributable package.
---

# Skill Creator

Design skills that are easy to trigger, cheap in context cost, and reliable in execution.

## Scope

domains or tasks—they transform Claude from a general-purpose agent into a specialized agent
equipped with procedural knowledge that no model can fully possess.
- In scope: authoring SKILL.md, structuring resources, packaging, and iteration.
- Out of scope: adding non-essential documentation files or process artifacts.

## Core Principles

1. Keep SKILL.md concise and action-oriented.
2. Put details in references/scripts/assets, not in long prose.
3. Make trigger descriptions explicit so invocation is predictable.
4. Prefer deterministic scripts for repetitive or fragile operations.

## Required Structure

```
skill-name/
    SKILL.md
    scripts/       (optional)
    references/    (optional)
    assets/        (optional)
```

Only SKILL.md is required.

## SKILL.md Contract

Frontmatter must include:
- name
- description

Description should include:
- what the skill does
- when to use it
- trigger phrases and relevant task categories

Body should include:
- workflow steps
- decision rules and boundaries
- references to bundled resources when needed

## Progressive Disclosure Pattern

- Keep SKILL.md focused on core flow.
- Move deep examples/specs to references/.
- Keep scripts executable and deterministic.
- Store output artifacts/templates in assets/.

## What Not To Add

Do not add extra docs that are not required by task execution, such as:
- README.md
- INSTALLATION_GUIDE.md
- CHANGELOG.md
- QUICK_REFERENCE.md

## Creation Workflow

1. Collect concrete user examples and trigger phrases.
2. Define reusable resources (scripts, references, assets).
3. Initialize structure via scripts/init_skill.py when creating a new skill.
4. Implement SKILL.md and resources.
5. Package via scripts/package_skill.py.
6. Iterate based on real usage feedback.

## Practical Heuristics

- If instructions are fragile: reduce freedom and provide exact steps.
- If task variability is high: provide goals and guardrails, not rigid scripts.
- If the same code is written repeatedly: move it to scripts/.
- If large background knowledge is needed: move it to references/.

## Packaging

Use:

```bash
scripts/package_skill.py <path/to/skill-folder>
```

The package command validates first; fix validation issues before distributing.

## Output Contract

When asked to create or update a skill, return:
- final directory structure
- final SKILL.md
- summary of reusable resources added
- packaging result and any validation findings

