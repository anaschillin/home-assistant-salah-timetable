# Asset provenance and redistribution

The authoritative asset inventory is [asset-provenance.json](asset-provenance.json).
It records individual paths, SHA-256 hashes, ownership claims, licence basis and
source/evidence references. The bundled [background catalogue](../custom_components/salah_timetable/frontend/mosque-backgrounds.js)
also supplies photographer credits and source links to the Home Assistant card.
There is no separately maintained credits table.

## Maintainer attestation

The brand icon was AI-generated for this project, as attested by the maintainer
on 29 October 2026. Current PDF/CSV/JSON fixture data was independently
generated using fictional mosque names and times. This statement is retained
because the brand icon's inventory entry refers to it as evidence.

The original interface screenshots in [docs/screenshots](screenshots/) were supplied by the
project maintainer on 30 October 2026 for README and dashboard documentation.
They reproduce the project's own Home Assistant UI and show example mosque
names and published timetable values; the screenshots do not grant rights to
the original mosque publications or imply mosque endorsement. The main and
Yesterday screenshots include the bundled Jama Masjid,
Delhi photograph by Naveed Ahmed (whose separate Unsplash source and licence
are recorded in the inventory). Those photo rights are not converted into
MIT rights by including the image in a screenshot. The screenshot files
are checksummed in the same inventory and included in its integrity check.

Additional setup, import, settings and desktop/mobile dashboard captures were
supplied by the maintainer on 1 November 2026 for the guides. Dashboard captures
have AI-assisted privacy redactions and image resampling: mosque names and
identifying entity IDs are obscured. They are illustrative interface examples,
not authoritative timetable publications. Unredacted uploads are not added by
the documentation update; earlier Git history may contain unredacted captures.
The new dashboard previews retain the bundled National Mosque
of Malaysia photograph by The Simple Travel and the Sultan Omar Ali Saifuddien
Mosque photograph by Jimmy Whitson; their separate source and licence entries
remain authoritative. See the inventory for each capture's hash and rights basis.

A further 16 desktop, mobile and tablet screenshots were supplied by the
maintainer on 4 November 2026 after the card-editor and monthly-action redesign.
They are stored as optimised WebP files in
[the device gallery](screenshots/showcase/) and linked from the dashboard guide.
Unlike the previously anonymised captures, these show the configured public
mosque name and published times; no personal identifiers, authentication details
or original timetable PDFs are supplied with them. The background in these
captures reproduces the bundled Masjid an-Nabawi photograph by Haidan. Its
original Unsplash source, licence basis and checksum remain recorded in
[the asset inventory](asset-provenance.json). Converting screenshots to WebP
does not change rights in the underlying background photograph. All new images
have their own SHA-256 inventory entries.

The maintainer approved a further kiosk-mode screenshot on 6 November 2026.
It depicts the v3.0 Home Assistant wall-display layout, including the compact
fullscreen icon. The original 1920 × 1080 PNG was converted to an optimised
WebP at the same resolution for
[the desktop kiosk showcase](screenshots/showcase/desktop/kiosk-v3.webp).
The screenshot uses the maintainer's configured public mosque and published
time data; the visible mosque photograph remains subject to its underlying
photographer/source licence and does not become MIT-licensed through the capture.
Its asset hash is included in the inventory.

The 20 bundled backgrounds come from reviewed free Unsplash photograph listings.
Their named photographers and source pages are recorded individually in the
inventory and card catalogue. The [Unsplash License](https://unsplash.com/license)
is separate from the repository's MIT licence; external image, publicity and
trademark permissions still require human review. Do not assume Unsplash+ images
carry the same terms.

## Governance checks

Run `python scripts/check_asset_provenance.py` to validate inventory membership,
checksums and the presence of evidence. Use
`python scripts/check_asset_provenance.py --require-cleared` for the stricter
release gate that rejects unresolved entries. A passing check **does not**
authenticate external licence pages or prove exclusive ownership.

Fixture CSVs are checked out with LF line endings through `.gitattributes`
so their byte checksums remain stable on Windows and Linux. Do not change the
inventory hashes merely to accept line-ending conversion.

When replacing or adding media, verify provenance and redistribution rights,
then update the inventory hashes. Do not classify a modified publisher image
or PDF as original merely because it was reformatted or anonymised.

Earlier repository commits may still contain publisher material; removing it
from the current tree does not erase Git history or third-party copies.
