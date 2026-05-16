# Mintlify Docs Updater — References

## mint.json Full Schema Reference

Key fields:
- `name` — site display name
- `logo` — `{ "dark": "/logo/dark.svg", "light": "/logo/light.svg" }`
- `favicon` — path to favicon
- `colors` — `{ "primary": "#hex", "light": "#hex", "dark": "#hex" }`
- `topbarLinks` — `[{ "name": "GitHub", "url": "..." }]`
- `topbarCtaButton` — `{ "name": "Get Started", "url": "..." }`
- `anchors` — sidebar section anchors with icons (from Font Awesome)
- `navigation` — array of groups with pages
- `footerSocials` — social links in footer
- `api` — `{ "baseUrl": "https://api.example.com" }` for playground

## MDX Frontmatter Fields

| Field | Description |
|-------|-------------|
| `title` | Page title (H1 and `<title>`) |
| `description` | Meta description and search subtitle |
| `icon` | Lucide/Font Awesome icon for nav |
| `api` | `METHOD URL` for auto API page |
| `openapi` | Path to operation in OpenAPI spec |
| `sidebarTitle` | Override title shown in sidebar |

## Useful Mintlify CLI Commands

```bash
mintlify dev               # local preview
mintlify broken-links      # detect broken internal links
```
