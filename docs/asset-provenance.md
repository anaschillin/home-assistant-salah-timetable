# REV-04 — Asset provenance and public redistribution gate

The machine-readable [inventory](asset-provenance.json) covers binary PDF fixtures,
derived CSV oracles, the integration brand icon and public documentation
screenshots. It records the known owner/source and the current basis for
redistribution; **pending is not permission**. This is separate from the
repository's MIT licence for original code and generated synthetic assets.

Run `python scripts/check_asset_provenance.py` to ensure that all currently
tracked assets are accounted for, with known SHA-256 digests checked for the two
contributed publisher PDFs. Normal CI performs this inventory check. Run
`python scripts/check_asset_provenance.py --require-cleared` as the **release
gate**: this intentionally exits nonzero while public-repository rights remain
unverified. Draft release preparation invokes the same check on the exact tag.

## Outstanding maintainer/legal evidence

- **Nuneaton Muslim Society:** `nms ramadhan.pdf` and the factual oracle
  `nms_monthly_2022.expected.csv`. Confirm who holds rights and whether
  publicly hosting the PDF and its transcribed oracle is permitted.
- **Zakariyya Jaam'e Masjid:** `zak.pdf` plus the annual and Ramadan
  factual oracles. Seek express redistribution permission or a defensible
  separately documented alternative for each asset.
- **Branding:** Identify the artist/licensor of
  `custom_components/salah_timetable/brand/icon.png`, and obtain proof
  that distributing it in HACS installs and the public repository is allowed.
- **Documentation screenshots:** Confirm author/origin and the rights to
  reproduce any visible third-party materials for all four screenshots.

The synthetic `sample_table` and `nms_synthetic_2026` assets are generated
by code in the repository and attributed to the repository's MIT licence;
their prayer times are fictional. The real contributed publications have
recorded hashes and must not be treated as MIT-licensed merely because they
are checked into an MIT repository.

## Safe resolution

1. Secure the copyright holder's written grant identifying the file(s), the
   public GitHub repository/HACS distribution, modifications (if any), and
   any attribution requirements. Store a suitable **public, non-sensitive**
   permission record in `docs/` and update the inventory entry to
   `permission_documented` with its evidence path. Do not post private
   correspondence or personal addresses without permission.
2. For author-owned artwork/screenshots, record actual author evidence and
   a verifiable MIT/compatible licence or explicit permission. A generic
   maintainer assertion is not a substitute for evidence.
3. Where permission cannot be obtained, **replace** the fixture with an
   independently authored, synthetic equivalent and update expected-value
   tests. Removing a file from the latest commit does **not** remove its
   older copies from public Git history or forks. Decide on Git-history
   remediation with the affected rightsholder before claiming resolved.
4. Re-run the inventory and tests, confirm no unresolved distribution rights,
   and record the clearance review in `docs/validation.md`.

The release ZIP already excludes fixture PDFs, but **public repository
redistribution remains an open issue** until the above is resolved. Do not
publish a release, even a draft, as an assertion that the missing rights exist.
