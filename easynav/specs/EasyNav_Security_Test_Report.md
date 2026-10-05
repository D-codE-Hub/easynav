# EasyNav — Phase 10 Security Test Report

Run: `bench --site wahub.com run-tests --app easynav` (Frappe 17.0.0-dev, 2026-10-05) — 18 tests, all passing.
Automated tests: `easynav/easynav/doctype/easynav_settings/test_security.py`.

## Test users

| User | Roles | Purpose |
|---|---|---|
| C (limited) | none | Minimal access |
| A (sales) | Sales User | Customer access |
| B (manager) | System Manager | Settings/report access |

Configured items: System Settings (DocType), Customer (DocType), a Report Builder report restricted to System Manager (Report), https://example.com (URL).

## Results

| Requirement | Result |
|---|---|
| Restricted user sees no permissioned items (only URL) | Pass |
| Sales User sees Customer, not System Settings / Report | Pass |
| System Manager sees Settings, Report, URL — **not** Customer (no ERPNext permission) | Pass |
| API never returns more than Frappe would allow; session user restored after check | Pass |
| Payload exposes only `enabled/position/button/items`; no doc names/owners | Pass |
| Normal users cannot read or write EasyNav Settings directly | Pass |
| `get_navigation` is not a guest method; Guest gets an empty menu | Pass |
| Unsafe URLs stored in the DB (`javascript:`, `data:`, `//host`, `ftp:`) are never returned | Pass |
| Save-time validation rejects unsafe URLs / missing targets (Phase 3 tests) | Pass |

## Notes

- EasyNav reads the Settings single without a permission check by design; it returns only items the current user may open. Destination routes are still enforced by Frappe.
- URL items are not permission controlled (any logged-in user sees them).
- Page-type filtering uses `Page.is_permitted()`; not covered by an automated test (creating a Page requires developer-mode file output). Verify manually.
- Client-side routing/URL checks (`easynav.js`) were unit-checked in Node but not exercised in a browser.
