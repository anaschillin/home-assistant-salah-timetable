# Asset provenance and redistribution checks

The repository now uses **original, fictional PDF fixtures** for its two example formats, **Mosque A** and **Mosque B**, rather than distributing scans from identifiable mosque publishers. Renaming or removing marks alone does not grant redistribution rights: the replaced PDF pages and fictional prayer-time series were generated afresh.

The source code and synthetic fixture generator scripts are MIT-licensed. Run `python scripts/check_asset_provenance.py` to validate the inventory and `python scripts/check_asset_provenance.py --require-cleared` before publishing. The release gate **still blocks** while the icon and documentation screenshots need an independent rights check.

**Historical caveat:** earlier public Git commits contained the original publisher files and their transcriptions. This change deletes them from the current branch but does not remove earlier commits, forks, downloads or release artifacts. A history rewrite would require separate coordinated action and might affect contributors and tags.

Never publish further third-party PDF examples without permission or a documented redistribution licence; prefer independently generated test data.
