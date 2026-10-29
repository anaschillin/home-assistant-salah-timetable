# Asset provenance and redistribution checks

The inventory in [`asset-provenance.json`](asset-provenance.json) records the
redistribution classification and **SHA-256 checksum of every tracked asset** in
the audited directories. The check is intentionally separate from a legal
determination that each rightsholder has granted the necessary permissions.

## Inventory scope (29 October 2026)

| Classification | Count | Notes |
| --- | ---: | --- |
| Original independently produced assets (`original_mit`) | 17 | 12 fictional fixtures, the AI-generated brand icon and four generated synthetic-card screenshots |
| Unsplash License photographs (`permission_documented`) | 20 | Resized WebP mosque backgrounds with source/photographer links |
| Rights review pending | 0 | No known outstanding entries in this inventory |
| **Total** | **37** | All 37 files have checksums and recorded provenance |

The auditor scans test data under `tests/fixtures/` (including CSV and JSON),
documentation images under `docs/images/`, brand assets under
`custom_components/salah_timetable/brand/`, and image/font media in the
bundled frontend directory. It rejects unlisted or missing assets, malformed
ownership/basis declarations, absent local evidence files, symlinks, and files
whose content differs from their recorded SHA-256. It also requires an evidence
reference before an asset can be marked as cleared.

An evidence URL is **not downloaded or authenticated by this offline check**.
A matching checksum establishes asset identity, **not** ownership or licence
validity. The maintainer must independently verify source pages, grant scope,
photographer attribution and (where relevant) rights in depicted people, marks
or other works before setting or retaining a cleared status.

**Maintainer origin attestation (29 October 2026):** The brand icon was generated with AI for this project. The four tracked `docs/images/card-*.png` illustrations were captured from synthetic test rendering, not from the original publishers' PDF files. The current tracked PDF/CSV/JSON fixtures are independently generated fictional data. These statements are maintainer-supplied provenance, recorded here for auditability; the checker can verify checksums and the presence of this record but cannot independently prove authorship, image-generation provenance, exclusive rights or absence of third-party rights. Reassess an asset if its origin changes or contrary evidence appears.

The 20 mosque photographs were reviewed against the free-photo listings on
Unsplash; see [photographer credits](mosque-background-credits.md). They are
covered by the [Unsplash License](https://unsplash.com/license), **not Creative
Commons or the repository's MIT licence**. Unsplash's licence allows broad
redistribution but excludes compiling images into a competing image service;
third-party publicity, trademark and artwork rights can still apply. An
Unsplash+ image is a distinct subscription licence and must not be silently
treated as a free-photo listing.

## What a successful CI check means

Run from the repository root:

```sh
python scripts/check_asset_provenance.py
python scripts/check_asset_provenance.py --require-cleared
```

The first command runs in ordinary PR CI and checks **inventory integrity**.
It can exit successfully **while listing unresolved assets**. This is not
permission to publish.

The second command is used by draft-release preparation and **must fail**
whenever an inventory entry is unresolved. Following the maintainer's
29 October origin attestation, no currently tracked entry is pending.
The strict audit should therefore pass on this branch once CI checks it;
public-repository documentation screenshots remain in scope even though
the runtime ZIP excludes `docs/`. Neither the normal nor strict audit is
a substitute for independently verifying external-photo licence terms.

When replacing an image or fixture, update the checksum and verify licensing
separately. Never mark an asset `original_mit` just because the hosting
repository uses MIT; creating an anonymised or reformatted copy does not
automatically remove third-party copyright.

## Historical distribution caveat

Earlier public Git commits contained published mosque files and transcriptions.
The repository now uses independently generated fictional PDF fixtures for
Mosque A and Mosque B. Removing publisher assets from the current tree does
**not** remove historical commits, forks, downloads or release artifacts; a
history rewrite would require a separate coordinated decision.

Never publish new third-party timetable examples without the appropriate
redistribution rights. Prefer newly generated fictional test data.
