# Toolathlon Profiles

## smoke

Release-gated profile.

Servers:
- rail_12306
- filesystem

Purpose:
- fast local validation
- release smoke testing
- reproducible MCP launch checks

## full

Experimental profile.

The full profile includes additional local MCP server scaffolds. It is not
release-gated until every server has deterministic install/build/smoke
coverage.

Known incomplete full-profile servers:
- canvas
- google_calendar
- google_forms
- howtocook
- memory
- notion
- fetch
- woocommerce
- youtube
- youtube_transcript
