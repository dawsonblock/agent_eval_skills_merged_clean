# Toolathlon Profiles

## smoke

Release-gated profile.

Targets:
- rail_12306
- filesystem
- google_calendar

Claims allowed:
- local import/start smoke validation
- profile-aware MCP target availability for smoke targets

Claims not allowed:
- full benchmark validity
- production integration safety

## full

Experimental, non-release-gated profile.

Targets:
- rail_12306
- filesystem
- google_calendar
- canvas
- howtocook
- memory
- google_forms
- fetch
- notion
- woocommerce
- youtube
- youtube_transcript

Claims allowed only when full-profile validation logs are present and linked to the exact artifact pair being claimed.
