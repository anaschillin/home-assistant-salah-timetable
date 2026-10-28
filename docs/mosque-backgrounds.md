# Mosque background implementation

Status: implementation in progress; no image is approved for redistribution until its individual file page is reviewed.

## Scope
- Optional background, disabled if no bundled asset is available.
- Default opacity 7%, configurable 0–20%.
- Fixed selection or deterministic daily rotation; avoid repeating before a full cycle.
- Responsive cover positioning and an opaque enough surface to preserve contrast in dark/light themes.
- Local WebP assets, no runtime remote requests, no impact on prayer calculations.
- Each asset requires source URL, photographer, license URL, modifications, and verified attribution.
- Target up to 20 geographically diverse mosques; ship only images with verified compatible licenses.

## Asset acceptance
1. Search Wikimedia Commons file namespace, using its MediaSearch UI or MediaWiki API.
2. Check original file page and license, not just search snippets or API metadata.
3. Exclude NC, ND, unknown, disputed and third-party-restricted assets; check ShareAlike obligations.
4. Download selected photographs and optimise to WebP, preserving subject and focal point.
5. Record credits in a machine-readable manifest and visible credits in card help/documentation.
6. Review each photograph's architecture and name; distinguish Al-Qibli Mosque from the wider Al-Aqsa compound.

## Validation
- Frontend unit tests for config bounds, deterministic selection, invalid asset fallback.
- Browser tests for light/dark, mobile/tablet, compact/expanded, contrast and reduced motion.
- Verify offline loading, HACS package inclusion, and attribution links.
- Run frontend formatting/tests and HA smoke checks; keep PR unmerged for device testing.

## Wikimedia metadata
Use MediaWiki `action=query&prop=imageinfo&iiprop=url|extmetadata` and inspect each file page.
See https://commons.wikimedia.org/wiki/Commons:Machine-readable_data .

## Pixabay eligibility filter
- Accept only images demonstrably **first published on Pixabay before 2019-01-09** (strictly earlier than 9 January 2019).
- Require a verifiable original publication timestamp and evidence that the particular photograph was released under CC0; a current page label of “free” is insufficient.
- Reject images dated 2019-01-09 or later, missing publication timestamps, reuploads with uncertain provenance, and images with unclear third-party rights.
- Record original Pixabay image ID, source URL, timestamp, CC0 evidence URL, author and verification date in the manifest.
- Pixabay's current Content License alone is not treated as permission to redistribute standalone assets in this repository.
