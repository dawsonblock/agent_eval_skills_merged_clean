---
name: humanizer
description: Rewrite AI-generated text to sound natural, human, and engaging. Use when the user wants to humanize copy, remove AI writing patterns, make text less robotic, improve readability, or pass AI detectors. Trigger phrases include "humanize", "make this sound human", "rewrite this", "remove AI tone", "AI detection", "less robotic", "improve copy", "natural writing", "human tone".
---

# Humanizer

Rewrite AI-generated text to sound natural, engaging, and authentically human.

## Why AI Text Sounds Robotic

Common AI writing patterns to eliminate:

| AI Pattern | Human Alternative |
|------------|-------------------|
| "In conclusion," / "In summary," | Just conclude — don't announce it |
| "It is important to note that..." | Cut the throat-clearing — state the point |
| "Delve into", "Leverage", "Navigate" | Use simpler, concrete verbs |
| Perfect parallel structure everywhere | Vary sentence rhythm deliberately |
| Excessive hedging ("may", "might", "could") | Be direct when you mean something |
| No contractions | Use contractions (don't, it's, you'll) |
| Every paragraph ~same length | Short punchy paragraphs + longer ones |
| Overuse of em-dashes and colons | Use sparingly; not in every sentence |
| Generic openers ("As an AI...") | Start with substance |

## Humanization Workflow

### Step 1: Diagnose the Issues

Read the draft and tag problems:
- `[CLICHÉ]` — buzzword or hollow phrase
- `[STIFF]` — formal phrasing that no person would say aloud
- `[ROBOTIC]` — pattern that signals AI origin
- `[HEDGE]` — unnecessary qualification

### Step 2: Rewrite with These Principles

1. **Read aloud test** — would a person actually say this sentence?
2. **Specificity** — replace vague adjectives with concrete details
3. **Rhythm** — mix short and long sentences; break patterns
4. **Voice** — match the brand/person voice (formal/casual/witty)
5. **Contractions** — use them in conversational copy
6. **Active voice** — prefer "We built X" over "X was built"
7. **First person** — "I", "we", "you" create connection
8. **Anecdotes/examples** — ground abstract claims in specifics

### Step 3: Final Check

- Remove any remaining filler openers
- Ensure topic sentences carry weight
- Vary paragraph lengths (1–4 sentences; occasional 1-line para for punch)
- Spot-check: does it sound like a real person wrote this?

## Tone Variants

| Tone | Characteristics |
|------|----------------|
| **Conversational** | Short sentences, contractions, "you", casual vocab |
| **Professional** | Clear, direct, no filler, active voice, no slang |
| **Storytelling** | Scene-setting, tension/resolution, sensory details |
| **Technical** | Precise vocab, fewer metaphors, evidence-forward |
| **Witty** | Unexpected word choices, light humor, subverted expectations |

## Example Transformation

**Before (AI):**
> "It is important to note that leveraging cutting-edge technologies can significantly enhance your ability to navigate the complex landscape of digital transformation."

**After (Human):**
> "New tools won't save a bad strategy. But the right ones can cut weeks of work down to hours."

## Prompting for Humanization

When asking an LLM to humanize text, give it constraints:
- Specify the target tone and audience
- Tell it to avoid specific words (e.g., "do not use: leverage, delve, navigate, crucial")
- Ask it to preserve any technical accuracy while changing the register
- Request a version at a specific reading level (e.g., Grade 8 Flesch–Kincaid)
