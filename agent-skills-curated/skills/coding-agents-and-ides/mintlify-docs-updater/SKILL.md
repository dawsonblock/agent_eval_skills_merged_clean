---
name: mintlify-docs-updater
description: Update, reorganize, and maintain Mintlify documentation sites. Use when the user wants to update API reference docs, add new pages to a Mintlify site, refactor navigation, sync docs with code changes, or publish documentation updates. Trigger phrases include "update docs", "mintlify", "docs site", "documentation site", "API reference docs", "update navigation", "add doc page", "sync docs".
---

# Mintlify Docs Updater

Maintain and update Mintlify documentation sites efficiently.

## Mintlify Project Structure

```
docs/                    ← or repo root
├── mint.json            ← site config: nav, colors, anchors
├── index.mdx            ← landing page
├── api-reference/
│   ├── openapi.yaml     ← OpenAPI spec (auto-generates endpoint pages)
│   └── introduction.mdx
├── guides/
│   └── quickstart.mdx
└── components/          ← reusable MDX snippets
```

## Common Tasks

### Add a New Page

1. Create `your-section/page-name.mdx`
2. Add YAML frontmatter:
   ```mdx
   ---
   title: 'Page Title'
   description: 'One-line description for search and meta'
   ---
   ```
3. Add to `mint.json` navigation under the appropriate group:
   ```json
   {
     "group": "Your Section",
     "pages": ["your-section/page-name"]
   }
   ```

### Update Navigation (`mint.json`)

```json
{
  "navigation": [
    {
      "group": "Getting Started",
      "pages": ["introduction", "quickstart", "installation"]
    },
    {
      "group": "API Reference",
      "pages": [
        "api-reference/introduction",
        {
          "group": "Endpoints",
          "pages": ["api-reference/endpoint/get", "api-reference/endpoint/post"]
        }
      ]
    }
  ]
}
```

### Sync API Reference with OpenAPI Spec

When the OpenAPI spec changes, update `api-reference/openapi.yaml` in place. Mintlify auto-generates endpoint pages from it — no manual page creation needed.

For manual endpoint pages (non-OpenAPI):
```mdx
---
title: 'Get User'
api: 'GET https://api.example.com/users/{id}'
description: 'Retrieve a user by ID'
---

<ParamField path="id" type="string" required>
  The user's unique identifier
</ParamField>

<ResponseField name="id" type="string">
  The user ID
</ResponseField>
```

### Mintlify MDX Components

| Component | Use case |
|-----------|----------|
| `<Note>` | Important callouts |
| `<Warning>` | Caution / breaking changes |
| `<Tip>` | Best practices |
| `<CodeGroup>` | Multi-language code tabs |
| `<Steps>` | Numbered step lists |
| `<Card>` / `<CardGroup>` | Visual navigation cards |
| `<Accordion>` | Collapsible sections |
| `<ParamField>` | API parameter docs |
| `<ResponseField>` | API response docs |

## Workflow for Bulk Updates

1. **Inventory**: `find . -name "*.mdx" | head -50` to understand scope
2. **Read `mint.json`** to understand current nav structure
3. **Make edits** — batch related changes together
4. **Validate links**: check all `pages:` entries in `mint.json` have corresponding `.mdx` files
5. **Preview**: `npx mintlify dev` (port 3000) to verify rendering

## Local Preview

```bash
npm i -g mintlify   # one-time install
mintlify dev        # starts at http://localhost:3000
```

## Common Gotchas

- Page paths in `mint.json` are **relative, no extension** — `"guides/quickstart"` not `"guides/quickstart.mdx"`
- Broken nav entries (path with no file) will cause build errors
- Images go in `public/` or `images/` and reference as `/images/screenshot.png`
- Custom domains require changes in Mintlify dashboard, not the repo
