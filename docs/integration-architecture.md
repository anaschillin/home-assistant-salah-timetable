# Integration module boundaries

This document describes runtime ownership and the contracts between modules. It is not a replacement for the import review guide.

| Module | Responsibility | Contract |
| --- | --- | --- |
| `import_flow.py` | CSV upload, mapping, staged review and comparison UI | Never activate an import without the user's explicit approval |
| `source_flow.py` | HTTPS/PDF source configuration and source-management options | Validate inputs before staging; notify the source manager after source removal |
| `pdf_parser.py`, `csv_parser.py` | Parse and validate bounded publications | Preserve printed dates and reject ambiguous layouts |
| `download.py` | Constrained HTTPS fetching | Preserve DNS/IP/redirect protections and size/time limits |
| `storage.py` | Per-entry durable approved, staged and source metadata | Atomic writes, exact stage identity and approval compare-and-swap |
| `source_updates.py` | Background and manual remote checks | Never auto-approve; reschedule after source-profile changes and stop timers on unload |
| `coordinator.py` | Resolve current effective day and upcoming events | Boundary refresh plus one-minute fallback; cache coverage by input snapshot |
| `calendar.py`, `sensor.py` | Read-only entities for approved data | Calendar display intervals do not imply prayer duration |
| `frontend.py` | Register bundled card resource once per HA instance | Preserve user-owned YAML resources; remove component-loaded listener at HA shutdown |

## Change propagation

1. Import flows parse and stage a candidate; review and comparison use the current approved baseline.
2. Only explicit approval changes approved timetables. The coordinator refreshes after state changes; sensors and calendar read the approved snapshot.
3. Source checks can stage new candidates but cannot activate them. Source profile removal recalculates the next scheduled check.
4. Each configuration entry owns its storage and coordinator; frontend static assets and dashboard resource registration are shared per Home Assistant instance.
5. Unload cancels source checks and coordinator boundary callbacks; Home Assistant shutdown releases the frontend event listener.

## Refactoring guardrails

PDF upload and URL imports now share parser inspection preparation in `source_flow.py`; CSV upload retains its dedicated path. Any further shared import refactoring requires parity tests for CSV, PDF, URL, staged review, rejection, approval and multiple mosque instances. Avoid merging download security, parsing and storage into a single abstraction. The legacy `TimetableStorage.for_date` returns an annual-only row and must not be used for effective Ramadan selection; use `ramadan.resolve_day` instead.
