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

---

# EasyNav — V2 Security Test Report (Per-User Navigation Items)

Run: `bench --site wahub.com run-tests --app easynav` (Frappe 17.0.0-dev, 2026-10-06) — 51 tests, all passing.
Automated tests: `easynav/easynav/doctype/easynav_user_navigation/` (`test_easynav_user_navigation.py`, `test_navigation_api.py`, `test_security.py`, `test_search.py`, `test_item_validation.py`) and `easynav/patches/test_remove_global_items.py`.

In V2 each user owns one `EasyNav User Navigation` document. The MVP results above still hold, but the items are now read from the session user's own document, and the MVP test files moved to the folder named here.

## Test users

| User | Roles | Purpose |
|---|---|---|
| A, B | Script Manager | Two ordinary Desk users, each with their own list |
| Manager | System Manager | Support user |
| Limited | none | Minimal access |

## Results

| Requirement | Result |
|---|---|
| A's menu contains A's items and none of B's | Pass |
| A cannot read, write or delete B's document | Pass |
| A's list view returns only A's row | Pass |
| A cannot create a document, and cannot delete their own | Pass |
| Ownership guard holds even when code saves with `ignore_permissions` | Pass |
| A document cannot be reassigned to another user | Pass |
| System Manager can list, read, edit and delete any user's existing document | Pass |
| System Manager cannot create a document for another user | Pass |
| A System Manager's edit changes the owner's menu, not the System Manager's | Pass |
| Saving clears only the owner's cached boot info | Pass |
| `get_user_navigation` creates the session user's document once, and only theirs | Pass |
| `get_user_navigation` is not a guest method and rejects Guest | Pass |
| Reading the menu never creates a document | Pass |
| More than 30 items is rejected | Pass |
| Item validation (unsafe URLs, missing or child-table targets, bad icons) applies to user documents | Pass |
| Items the owner cannot open are left out of their menu | Pass |
| Target search returns only DocTypes the user can read and Pages they are permitted to open | Pass |
| Target search refuses any DocType other than `DocType` and `Page` | Pass |
| A user without System Manager can save one item of each type | Pass |
| Deleting a user deletes their document; renaming a user renames it | Pass |
| Upgrade patch deletes the old site-wide items only, and is safe to run twice | Pass |

## Notes

- `user` is a read-only field. An attempt to change it is not rejected with an error: Frappe restores the stored value on save. The outcome (no reassignment) is what the test asserts.
- No whitelisted method takes a user id. The menu and the editor entry point are always keyed on `frappe.session.user`.
- A System Manager editing another user's list is offered targets by the System Manager's own permissions. This does not leak access: each item is permission-checked for the owner when their menu is built.
- Frappe's standard link search lists every DocType to every user. EasyNav's search is narrower than that, so it exposes nothing new.
- A user with no desk role (Website User) can still own a document through the API, but cannot reach Desk, where the menu and the form live.
- **Not verified in a browser:** the floating menu's empty state and "Edit shortcuts" entry, the form title and banner, and the "Link To" dropdown. The bundle was syntax-checked and built only.
- One test run failed with a MariaDB "Record has changed since last read" error on the User table, immediately after a migrate. Three later runs passed. Treated as a transient conflict with another connection, not a defect.
