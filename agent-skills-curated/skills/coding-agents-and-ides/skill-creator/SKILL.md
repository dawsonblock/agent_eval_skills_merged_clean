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


## Validation Checklist

Before delivering a skill package:
- [ ] Frontmatter includes `name` and `description`.
- [ ] Description contains: what the skill does, when to use it, and trigger phrases.
- [ ] SKILL.md body includes: workflow steps, decision rules, and scope boundaries.
- [ ] No unnecessary files added (no README.md, CHANGELOG.md, QUICK_REFERENCE.md).
- [ ] Scripts are executable and deterministic (no side effects requiring human intervention).
- [ ] References are linked from SKILL.md, not duplicated inline.
- [ ] Trigger phrases are concrete and distinct from other skills in the package.

## Failure Modes

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Skill never invoked | Trigger description too vague or missing key phrases | Expand description with 5–10 specific trigger phrases |
| Skill invoked for wrong tasks | Overlap with another skill's trigger domain | Add explicit "DO NOT USE FOR" list in description |
| SKILL.md too long to read in context | Deep examples embedded in body | Move examples to `references/` and link from SKILL.md |
| Scripts fail on different machines | Hardcoded absolute paths in scripts | Use `$(dirname "$0")` or `__file__` relative paths |
| Packaging fails silently | Missing `scripts/package_skill.py` or wrong entry point | Run `python scripts/package_skill.py --validate` before delivering |

## Anti-Patterns

- **Over-documenting SKILL.md**: Embedding long reference tables, full API docs, or exhaustive examples in SKILL.md inflates context cost. Put depth in `references/`.
- **Ambiguous trigger phrases**: "help me" or "do this" are too broad; triggers must map to a specific domain or action pattern.
- **Missing scope boundaries**: Without an explicit "out of scope" section, the skill is invoked for adjacent tasks it can't handle well.
- **Non-deterministic scripts**: Scripts that require interactive prompts or depend on session state break automated packaging; make all inputs explicit arguments.
- **Duplicate content across files**: If a decision rule exists in SKILL.md, it must not also appear verbatim in `references/`; a single source of truth prevents drift.

## Examples

**Good description excerpt**: "Use when users ask to build a new skill, improve an existing skill, fix trigger behavior, or prepare a distributable package. Trigger phrases include 'create a skill', 'new agent skill', 'write a SKILL.md', 'package this skill', 'fix skill triggers'."
**Bad description excerpt**: "Helps with skill-related tasks and creating things." (too vague, no trigger phrases)
