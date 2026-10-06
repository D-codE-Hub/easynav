# EasyNav V2 — Per-User Navigation Items

> **Status (2026-10-06):** Plan only, nothing implemented. Branch: `feat/user-navigation-items` (from `develop`). Target: Frappe `17.0.0-dev`.
> Builds on the MVP described in `EasyNav_MVP.md` and `EasyNav_MVP_Phase_by_Phase_Implementation_Plan.md`.

---

# 1. Goal

In the MVP, one System Manager maintains a single list of navigation items in **EasyNav Settings**, and every user gets the same menu (filtered by permission).

In V2, **each user owns their own list of shortcuts**:

- A user creates, edits, reorders and removes their own items.
- A user's items are shown only to that user.
- A user can never read or change another user's items. System Managers are the exception: they can view and fix any user's list for support.
- Everyone starts with an empty menu. The existing global items are not carried over.
- The **Navigation Items** table moves out of EasyNav Settings into a new per-user DocType.

EasyNav Settings stays, but only for site-wide options (enable switch, button label, icon, position).

## Out of scope for V2

- Admin-defined default, starter or shared items.
- Per-user button position, label or icon.
- Role-based item visibility, groups, separators, nested menus.
- A custom editor dialog. V2 uses the standard Frappe form.

---

# 2. Current State (what V2 changes)

| Area | MVP today | File |
|---|---|---|
| Item storage | `items` table (child `EasyNav Item`) on the single `EasyNav Settings` | `easynav/easynav/doctype/easynav_settings/easynav_settings.json` |
| Who can edit | System Manager only | same |
| Item validation | `EasyNavSettings.validate` calls `get_item_error` per enabled row | `easynav_settings.py`, `easynav/easynav/validation.py` |
| Payload | `build_navigation()` reads `settings.items`, resolves and permission-filters each row | `easynav/api/navigation.py` |
| Delivery | `frappe.boot.easynav` via `extend_bootinfo`; `get_navigation` for refresh | `easynav/boot.py`, `easynav/hooks.py` |
| Cache | `EasyNavSettings.on_update` calls `frappe.clear_cache()` (whole site) | `easynav_settings.py` |
| Form script | `set_query` for `link_to` / `kanban_board`, reset handlers on `EasyNav Item` | `easynav_settings.js` |
| Frontend | Renders nothing when there are no items | `easynav/public/js/easynav.bundle.js` |
| Tests | 3 files, all configure items through `EasyNav Settings` | `easynav_settings/test_*.py` |

What stays unchanged: the `EasyNav Item` child DocType and its fields, `validation.py`, the per-type resolvers and permission filtering in `navigation.py`, the payload shape, routing and URL safety in the bundle.

---

# 3. Design Decisions

## 3.1 New DocType: `EasyNav User Navigation`

One document per user, named after the user. This is the same pattern Frappe uses for `Dashboard Settings`.

| Property | Value |
|---|---|
| Module | EasyNav |
| Naming | `autoname: field:user` (document name = user id) |
| `in_create` | 1 (no "New" button; documents are created by the API) |
| `track_changes` | 1 |

Fields:

| Fieldname | Type | Notes |
|---|---|---|
| `user` | Link → User | `reqd`, `unique`, `read_only`, `set_only_once` |
| `items_section` | Section Break | Label "My Shortcuts" |
| `items` | Table → `EasyNav Item` | The table moved from EasyNav Settings |

The child DocType `EasyNav Item` is reused as is. No field changes.

## 3.2 Permissions

Role permissions alone cannot express "only your own document", so access is enforced in two layers.

1. **Role permission** in the DocType JSON: role `Desk User` gets `read` and `write`. No `create`, no `delete`.
2. **Ownership hooks** in `hooks.py`:
   - `has_permission`: allow only when `doc.name == user`, or the user is a support user.
   - `permission_query_conditions`: restrict list and report queries to `` `tabEasyNav User Navigation`.name = <user> ``. Return no condition for support users, so they see every row.

A **support user** is `Administrator` or anyone with the `System Manager` role. One helper, `_is_support_user(user)`, is used by both hooks and by the controller guard, so the rule is defined in one place.

The DocType JSON also gives `System Manager` `read`, `write` and `delete`. Support users can open, edit and delete an existing list. They cannot create one for another user: a document is only ever created by `get_user_navigation()` for the session user (3.5), so a user who has never opened the editor has nothing to fix.

The controller adds a third guard that does not depend on hooks: `validate` throws if `self.user != frappe.session.user` and the session user is not a support user. `user` is `set_only_once`, so a document cannot be reassigned.

Ownership is checked against the `user` field (the document name), not the `owner` column. `track_changes` records who made each edit, which matters now that support users can change someone else's list.

## 3.3 Global items are removed

The `items` field and its section are deleted from `EasyNav Settings`. There is no site-wide list in V2. Existing global items are deleted by a patch (section 3.7) and every user starts empty.

## 3.4 Navigation payload

`build_navigation()` keeps its signature and payload keys (`enabled`, `position`, `button`, `items`). Only the source of the rows changes:

```python
def _get_user_rows(user: str) -> list:
	if not frappe.db.exists("EasyNav User Navigation", user):
		return []
	return frappe.get_cached_doc("EasyNav User Navigation", user).items
```

Rows are read without a permission check, as today, but the lookup key is always `frappe.session.user`. No parameter of any whitelisted method accepts a user id.

Per-item resolution and permission filtering are unchanged. This still matters: a user can save an item for a DocType they cannot read, and it must not appear as a dead link.

## 3.5 Opening the editor

A user needs a way into their own document, including before it exists.

- New whitelisted method `easynav.api.navigation.get_user_navigation() -> str`: creates the session user's document if missing (`insert(ignore_permissions=True)`), returns its name. Guests are rejected.
- The menu gets a footer entry **"Edit shortcuts"**. Clicking it calls the method, then `frappe.set_route("Form", "EasyNav User Navigation", name)`.
- **Empty state:** this is what every user sees after the upgrade, and what every new user sees. When EasyNav is enabled and the user has no items, the button is still rendered and the menu shows only the footer entry. Today `render()` returns early when `items` is empty; that check is reduced to `!config.enabled`.

## 3.6 Caching

- `get_cached_doc` on the user document is invalidated automatically when it is saved.
- Boot info is cached per user in `frappe.cache.hget("bootinfo", user)`, so `EasyNavUserNavigation.on_update` and `on_trash` must call `frappe.cache.hdel("bootinfo", self.user)`. Without this a page reload shows the old menu. The key is `self.user`, not the session user, so a support user's fix reaches the owner on their next page load.
- The site-wide `frappe.clear_cache()` in `EasyNavSettings.on_update` stays. It is correct there, because settings affect everyone, and wrong for a per-user save.

## 3.7 Cleanup of existing data

Global items are not migrated. Removing the `items` field from the Settings JSON does not delete the rows, though. They stay in `tabEasyNav Item` with `parenttype = "EasyNav Settings"` as orphans.

New patch `easynav.patches.remove_global_items` (post model sync, after `split_item_target`) deletes every `EasyNav Item` row with `parenttype = "EasyNav Settings"`. It is idempotent: a second run finds nothing to delete.

This is a one-way change. After the upgrade the old global menu is gone and cannot be restored from the app, so the release notes must say so.

## 3.8 Link search for non-admin users

**This is the main technical risk.** `link_to` is a Dynamic Link to `DocType`, `Page`, `Report` or `Dashboard`. Standard link search requires read or select permission on the linked DocType, and in Frappe 17:

| Linked DocType | Roles with read |
|---|---|
| DocType | System Manager, Administrator |
| Page | System Manager, Administrator |
| Report | Desk User (and above) |
| Dashboard | Desk User (and above) |
| Kanban Board | Desk User (and above) |

> **Correction found in Phase 4:** Frappe's link search special-cases `DocType` and runs it without a permission check, so a normal user does get DocType suggestions, but for every DocType, including ones they cannot read. Only Pages return nothing. The custom search below is still used for both: it is required for Pages, and for DocTypes it limits the suggestions to what the user can open.

V2 adds a custom search:

- New module `easynav/api/search.py` with `search_targets(doctype, txt, searchfield, start, page_len, filters)`, registered with `@frappe.whitelist()` and `@frappe.validate_and_sanitize_search_inputs`.
- It returns only targets the session user may open: DocTypes with `istable = 0` and `frappe.has_permission(name, "read")`; Pages where `is_permitted()` is true.
- `easynav_user_navigation.js` points `set_query("link_to", "items", ...)` at it for types `DocType` and `Page`. Report, Dashboard and Kanban Board keep the standard search.

When a support user edits someone else's list, the search shows what the support user may open, not what the owner may open. That is safe: items are permission-filtered for the owner at render time (3.4), so an item the owner cannot open is simply not shown to them.

Link validation on save must also be checked for these two types (Phase 4, task 3).

## 3.9 Limits

A user may save at most **30 items** (`MAX_ITEMS` in `validation.py`, checked in the controller). Any Desk User can now write this data and it is sent on every boot, so the payload needs a bound.

## 3.10 User lifecycle

Registered through `doc_events` on `User`:

- `on_trash`: delete the user's `EasyNav User Navigation`. Otherwise the Link field blocks user deletion.
- `after_rename`: rename the settings document to the new user id, so the `name == user` rule keeps holding.

---

# 4. Implementation Phases

## Phase 1 — New DocType and permissions

**Objective:** `EasyNav User Navigation` exists, a normal user can only reach their own document, and a System Manager can reach all of them.

Tasks:

1. Hand-author `easynav/easynav/doctype/easynav_user_navigation/` (`__init__.py`, `.json`, `.py`, `.js`) per section 3.1.
2. Controller:
   - `validate`: ownership guard (3.2), item limit (3.9), and the per-row `get_item_error` loop moved from `EasyNavSettings.validate`.
   - `on_update` / `on_trash`: clear the user's boot cache (3.6).
   - Module-level `_is_support_user`, `has_permission` and `get_permission_query_conditions`.
3. `hooks.py`: add `has_permission`, `permission_query_conditions`, and the `User` `doc_events` (3.10).
4. `bench --site <site> migrate`.

**Deliverable:** as normal user A, opening `/app/easynav-user-navigation/<user B>` is denied and the list view shows only A's row. As a System Manager, the list view shows every row and B's document can be edited.

## Phase 2 — Backend API

**Objective:** the payload comes from the session user's document.

Tasks:

1. `navigation.py`: add `_get_user_rows`, use it in `build_navigation` in place of `settings.items`. Update the docstring, which currently explains the Settings read.
2. Add `get_user_navigation() -> str` (3.5). Type annotations are required (`require_type_annotated_api_methods = True`).
3. `boot.py`: no change.

**Deliverable:** two users with different items get different `frappe.boot.easynav.items`.

## Phase 3 — Remove items from EasyNav Settings

**Objective:** Settings holds only site-wide options; the old global rows are cleaned up.

Tasks:

1. `easynav_settings.json`: remove `items_section` and `items` from `field_order` and `fields`.
2. `easynav_settings.py`: remove `validate`, the `get_item_error` import and the `items` type annotation. Keep `on_update`.
3. `easynav_settings.js`: remove the `set_query` calls and the whole `EasyNav Item` handler block. Keep `after_save`.
4. Add the cleanup patch (3.7) and register it in `patches.txt` under `[post_model_sync]`.

**Deliverable:** after `migrate` on a site with MVP data, no `EasyNav Item` row has `parenttype = "EasyNav Settings"`, no `EasyNav User Navigation` document has been created, and every user sees the empty-state menu.

## Phase 4 — Editor form

**Objective:** a normal Desk User can build their list without admin help.

Tasks:

1. `easynav_user_navigation.js`: move the `EasyNav Item` handlers (`type`, `link_to`, `doc_view`) and the `kanban_board` query from `easynav_settings.js`. Add `after_save` → `window.easynav.refresh()` (see task 5).
2. Add `easynav/api/search.py` and wire `link_to` to it (3.8).
3. Verify as a user with only a business role (no System Manager): pick a DocType, a Page, a Report, a Dashboard and a Kanban Board, then save. If link validation rejects a DocType or Page target on save, set `ignore_user_permissions` on `link_to`. If that is not enough, validate the target in the controller only, where `get_item_error` already checks existence.
4. Form polish: when the document belongs to the session user, hide the `user` field and title the form "My Shortcuts". When a support user opens someone else's document, show the `user` field and an intro line naming whose shortcuts are being edited.
5. `after_save` refreshes the floating menu only when the saved document is the session user's own.

**Deliverable:** a non-admin user adds one item of each type and saves without errors.

## Phase 5 — Frontend

**Objective:** users can reach the editor from the menu, and the menu updates after a save.

Tasks in `easynav.bundle.js`:

1. `render()`: stop returning early on an empty item list (3.5).
2. `build_menu()`: append a divider and the "Edit shortcuts" footer entry. It is a `menuitem`, so the existing arrow-key handling in `on_keydown` covers it.
3. New `customize()` method: call `get_user_navigation`, close the menu, route to the form.
4. `easynav.bundle.scss`: styles for the divider, the footer entry and the empty state, using the same Frappe theme tokens as the existing items.

**Deliverable:** a new user sees the button, opens "Edit shortcuts", adds an item, saves, and the item appears without a page reload.

## Phase 6 — Tests and docs

**Objective:** isolation between users is covered by automated tests.

Tasks:

1. Move the three test files to `easynav_user_navigation/` and change their setup from `EasyNav Settings.items` to a user document. The validation and routing assertions stay the same.
2. Keep a small `test_easynav_settings.py` for the site-wide switch (disabled → empty payload).
3. New isolation tests:
   - A's payload contains A's items and none of B's.
   - Normal user A cannot read, write or delete B's document (`frappe.has_permission` and `frappe.get_doc(...).save()` raise `PermissionError`).
   - `frappe.get_list("EasyNav User Navigation")` as A returns only A's row.
   - A System Manager can read and save B's document, and `get_list` returns every row.
   - After a System Manager edits B's document, B's cached boot info is cleared and the System Manager's own payload is unchanged.
   - Nobody, including a System Manager, can create a document with `user = B` through the normal insert path.
   - `get_user_navigation()` creates once, returns the same name on the second call, and rejects Guest.
   - Saving A's document clears A's cached boot info.
   - More than 30 items is rejected.
   - Deleting a user removes their document.
4. Patch test: seed rows under `EasyNav Settings` and one user document with items, run `execute()` twice, assert the global rows are gone and the user document's rows are untouched.
5. Update `README.md` (configuration section) and add a V2 section to `EasyNav_Security_Test_Report.md`.

**Deliverable:** `bench --site <site> run-tests --app easynav` passes.

---

# 5. File Change Summary

| File | Change |
|---|---|
| `easynav/easynav/doctype/easynav_user_navigation/*` | New DocType, controller, form script, tests |
| `easynav/api/search.py` | New: permitted-target search |
| `easynav/patches/remove_global_items.py` | New patch: delete orphaned global rows |
| `easynav/patches.txt` | Register patch |
| `easynav/hooks.py` | `has_permission`, `permission_query_conditions`, `doc_events` for `User` |
| `easynav/api/navigation.py` | Read rows from the user document; add `get_user_navigation` |
| `easynav/easynav/validation.py` | Add `MAX_ITEMS` |
| `easynav/easynav/doctype/easynav_settings/*` | Remove `items`, its validation, its form handlers; tests reduced |
| `easynav/public/js/easynav.bundle.js` | Empty state, footer entry, `customize()` |
| `easynav/public/scss/easynav.bundle.scss` | Footer and empty-state styles |
| `README.md`, `specs/EasyNav_Security_Test_Report.md` | Docs |
| `easynav/easynav/doctype/easynav_item/*` | No change |

---

# 6. Security Checklist

| Risk | Mitigation |
|---|---|
| Reading another user's items | `has_permission` hook, `permission_query_conditions`, payload keyed on `frappe.session.user` only. Support users are allowed by design |
| Writing another user's items | Same hooks, `validate` ownership guard, `user` is `set_only_once`. Support-user edits are recorded by `track_changes` |
| A support user adding items the owner should not see | Items are permission-filtered for the owner at render time |
| Creating a document for someone else | No `create` role permission; only `get_user_navigation()` creates, always for the session user |
| Items pointing at records the user cannot open | Existing per-item permission filter in `_resolve_item` |
| Unsafe URLs | Existing `is_safe_url` at save and at render. Items are now self-authored, so the exposure is lower than in the MVP, but the check stays |
| Target search leaking DocType or Page names | `search_targets` returns only permitted records |
| Large payloads on boot | 30-item limit |
| Guest access | `get_navigation` and `get_user_navigation` are not `allow_guest`; `build_navigation` returns the empty payload for Guest |

---

# 7. Decisions

Decided by the product owner on 2026-10-06:

| Topic | Decision |
|---|---|
| Existing global items | Not migrated. Deleted on upgrade; everyone starts empty. |
| New users | Start with an empty menu and the "Edit shortcuts" entry. No starter set. |
| Admin access | System Managers can view and fix any user's existing list. |
| Item limit | 30 items per user, fixed (not configurable). |
| DocType name | `EasyNav User Navigation`. |

No open questions remain.
