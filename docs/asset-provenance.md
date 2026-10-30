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
