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

## Source policy (research, 2026-10-28)

For a downloadable public HACS integration, prioritize:
1. **Unsplash free photos**: the standard Unsplash License explicitly grants rights to copy, modify and distribute for commercial use. Do not use Unsplash+ paid or sponsored assets. Do not build a photo-distribution or competing image library. Retain source and creator credits voluntarily.
   - License: https://unsplash.com/license
2. **Wikimedia Commons / Openverse**: use verified CC0, CC BY or CC BY-SA originals, complying with credits and ShareAlike requirements. Avoid NC/ND.
   - https://commons.wikimedia.org/wiki/Commons:Reusing_content_outside_Wikimedia
   - https://openverse.org/
3. **Pixabay**: under Section 4 of its terms, the image must have a **Published date** before 2019-01-09 to be considered CC0. Exclude later images from the bundled asset pipeline unless separate distribution permission is obtained.
   - https://pixabay.com/service/terms/
4. **Pexels**: its free commercial-use license does not resolve its Terms of Service standalone file distribution restriction; do not bundle untransformed standalone photos without further clearance.
   - https://help.pexels.com/hc/en-us/articles/900005880463-What-are-the-Terms-and-Conditions

Each individual image must be reviewed for licensing and third-party architectural/property and model rights. These candidates have not been downloaded or bundled.

### Initial Unsplash source candidates (not yet accepted assets)

| Mosque | Candidate photo | Photographer | Page license statement |
|---|---|---|---|
| Masjid al-Haram, Makkah | https://unsplash.com/photos/kaaba-in-mecca-with-crowd-66Tu10CxYY0 | Ishan (@seefromthesky) | Free to use under the Unsplash License |
| Masjid an-Nabawi, Madinah | https://unsplash.com/photos/al-masjid-an-nabawi-mosque-in-medina-Qec3HPaHWTI | Haidan | Free to use under the Unsplash License |
| Sheikh Zayed Grand Mosque, Abu Dhabi | https://unsplash.com/photos/sheikh-zayed-grand-mosque-in-abu-dhabi-kZ1zThg6G40 | David Rodrigo | Free to use under the Unsplash License |
| Sultan Ahmed Mosque, Istanbul | https://unsplash.com/photos/a-walkway-leading-to-a-large-building-with-many-spires-bs1Nu9x7bNc | Max van den Oetelaar | Free to use under the Unsplash License |
| Badshahi Mosque, Lahore | https://unsplash.com/photos/brown-concrete-building-under-cloudy-sky-during-daytime-ayAl0D6mxHM | Sohail Chaudhry | Free to use under the Unsplash License |
| Hassan II Mosque, Casablanca | https://unsplash.com/photos/green-and-white-concrete-building-under-blue-sky-during-daytime-EJSGszHvVGI | Ajmal MK | Free to use under the Unsplash License |
| Great Mosque of Kairouan | https://unsplash.com/photos/great-mosque-of-kairouan-in-tunisia-0-Sn6xvf3BM | Malek Boukhris | Free to use under the Unsplash License |
| Baiturrahman Grand Mosque, Aceh | https://unsplash.com/photos/white-concrete-building-during-daytime-2lbcJYnxvqw | Sangga Rima Roman Selia | Free to use under the Unsplash License |

Avoid misleadingly naming a Dome of the Rock photograph as the Al-Qibli Mosque; the wider Al-Aqsa compound can be represented with precise descriptive labels.
