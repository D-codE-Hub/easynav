# EasyNav — Phase-by-Phase MVP Implementation Plan

> **Revision note (2026-10-05):** Updated after reviewing `EasyNav_MVP.md` against the installed bench (Frappe `17.0.0-dev`, site `wahub.com`). See **Section 0 — Review Findings and Plan Changes**. Where Section 0 conflicts with a later phase, Section 0 wins.

---

# 0. Review Findings and Plan Changes

## 0.1 Current state

| Item | Status |
|---|---|
| Phase 0 (planning) | Done — this document + MVP spec |
| Phase 1 (create/install app) | **Done** — app scaffolded in `apps/easynav`, installed on the bench. Skip `bench new-app` / `install-app`. |
| Git | Active branch is `develop` (plan below says `dev`; use `develop`). `specs/` is still untracked. |
| Module | `modules.txt` = `EasyNav`; DocTypes go in `easynav/easynav/doctype/` (matches spec). |
| Scaffolded `hooks.py` | Has `require_type_annotated_api_methods = True` (see 0.2 #1). |
| Not yet created | DocTypes, API, JS/CSS, `app_include_*` hooks, tests. |

Target Frappe version is decided: **v17 (develop)**. Phase 0 "decide Frappe version" is closed. Verify on the other bench apps (erpnext, hrms, etc.) only if EasyNav must run on v15/v16 too.

## 0.2 Corrections to the MVP spec (must-fix)

1. **API must be type-annotated.** `hooks.py` sets `require_type_annotated_api_methods = True`. A whitelisted method without annotations is rejected. Write:
   ```python
   @frappe.whitelist()
   def get_navigation() -> dict: ...
   ```
2. **`frappe.ready` is a website/portal hook, not Desk.** Spec §9 uses `frappe.ready(() => easynav.init())`. In Desk, initialise from `$(document).ready(...)` and guard with `frappe.session.user !== "Guest"` and an `if (window.easynav?._mounted) return;` idempotency check. `app_include_js` is Desk-only, so the login/website pages are unaffected.
3. **`page-change` is confirmed in v17** (`views/container.js` triggers it), so the spec's event is valid. But EasyNav is appended to `document.body`, so it does **not** need to re-render per route. Use `page-change` only to close an open menu (and optionally mark the active item). Do not call `refresh()` that refetches.
4. **"Target = Dynamic" needs a concrete design.** A `Dynamic Link` cannot point at `URL`, and Page/Report/DocType need different link doctypes. Decision for MVP: `target` is a plain **Data** field, plus **server-side validation on save** (`frappe.db.exists` for DocType/Page/Report; URL validation for URL). Optional polish: a `settings.js` autocomplete for `target` based on the row's `type`.
5. **Routing is not just `/app/<slug>`.** Resolve the route **on the server in the API** and return it, so JS contains no routing guesswork:
   | Type | Route |
   |---|---|
   | DocType (normal) | `["List", doctype]` → `/app/<slug>` |
   | DocType (`issingle`) | `["Form", doctype]` → `/app/<slug>` (the single's form) |
   | DocType (`istable`) | invalid — child tables have no list; reject on save |
   | Page | `["<page-name>"]` → `/app/<page-name>` |
   | Report (Script/Query) | `["query-report", report_name]` |
   | Report (Report Builder) | `["List", ref_doctype, "Report", report_name]` |
   The spec's "later add Report Type / Reference DocType" is not needed as fields — read them from the `Report` doc at API time.
6. **Permission contradiction in Phase 10.** Spec §12 and Phase 10 say "no server-side permission work" yet also want users not to see dead links. Resolution (still no role system, no bypass of Frappe's rules): the API **filters out items the current user cannot open** using the standard checks — `frappe.has_permission(doctype, "read")` for DocType, the Report's `get_permission`/`has_permission`, and the Page's roles (`frappe.get_doc("Page", name).is_permitted()`). Frappe still enforces on the destination route; this only avoids showing links that would 403. "Visible For Roles" stays V2.
7. **Reading the Settings single as a normal user.** Normal users lack read on `EasyNav Settings`. The API reads it with `ignore_permissions` internally (e.g. `frappe.get_cached_doc(...)`) and returns only the filtered, resolved payload. This is the one deliberate, narrow permission exception — Phase 10's "no bypass" wording means "never return data the user couldn't otherwise reach". The DocType's own permissions: **System Manager only**.
8. **`order` vs child-table `idx`.** Child rows already have drag-to-reorder (`idx`). Keep `order` per the spec, but sort by `(order or 9999, idx)` so unset `order` falls back to row position.
9. **Icons.** `lucide`-style names (`users`, `file-text`, `bar-chart`) in the spec example are not guaranteed to exist in Frappe's SVG sprite. Use Frappe's icon helper (`frappe.utils.icon(name)`), choose defaults from icons that exist in v17, and **fall back to a generic icon** when a name is unknown. Verify the available names during Phase 6.
10. **Tests.** Use `frappe.tests.IntegrationTestCase` (the v17 base class). `FrappeTestCase` is in `deprecation_dumpster.py` — do not use it.

## 0.3 Suggestions (recommended, still MVP-sized)

1. **Serve config via `extend_bootinfo` first, API second.** Add a `boot_session`/`extend_bootinfo` hook that puts the resolved navigation into `frappe.boot.easynav`. This gives **zero extra requests** on page load (Phase 15 goal). Keep `easynav.api.navigation.get_navigation` as the contract (spec §11) and use it to refresh after the settings are saved. Both call one shared function `build_navigation(user)`.
2. **Cache and invalidate.** Cache the global config, apply per-user permission filtering after. Clear cache in `EasyNavSettings.on_update`. Users pick up changes on next reload (acceptable for MVP; realtime push is V2).
3. **Validate on save, not only at render.** Phase 11 only says "don't render invalid items". Also add `EasyNavSettings.validate()` that throws on empty label/target, bad type, non-existent DocType/Page/Report, and unsafe URLs, so admins get immediate feedback. Keep the render-time skip as a safety net.
4. **URL rules (concrete).** Allow only `http:`/`https:` absolute URLs and same-origin relative paths starting with a single `/` (reject `//host`). Reject `javascript:`, `data:`, `vbscript:`, `file:`. Enforce on server (save + API) **and** client (`new URL()`). For new-tab opens use `window.open(url, "_blank", "noopener,noreferrer")`.
5. **XSS.** Labels and targets are admin-entered but must still be rendered with `textContent`/escaped values — never string-concatenated into `innerHTML`. Only the icon SVG from `frappe.utils.icon` may be injected as HTML.
6. **Use real `<button>`/`<a>` elements.** Gives keyboard focus, Enter/Space activation and screen-reader support for free. `Esc` closes the menu and returns focus to the button — this is accessibility, not the "keyboard shortcuts" feature that is out of scope.
7. **Hover only where hover exists.** Enable hover-open under `@media (hover: hover) and (pointer: fine)`; click/tap always works. Add a short close delay (~150 ms) so moving the pointer from button to menu doesn't flicker.
8. **z-index and placement.** Bootstrap modal backdrop/modal are 1040/1050 and Frappe's navbar is sticky. Put the button **below modals** (≈1030–1035) so dialogs cover it, and offset the "Top" positions by the navbar height. Use CSS classes per position (`easynav--bottom-right`, …) rather than inline styles; prefix all classes with `easynav-` to avoid clashes. Respect `prefers-reduced-motion` and Frappe's dark theme via CSS variables (`var(--card-bg)`, `var(--text-color)`, `var(--border-color)`).
9. **Empty/disabled behaviour.** If disabled or the user has zero visible items, render nothing (no empty button).
10. **Unique instance.** Mount a single root `#easynav-root`; on init remove any existing node before creating one.
11. **Optional (cheap) quality-of-life:** add `description`/`hint` text on the settings fields, and a "Preview" is *not* needed.

## 0.4 Phase map after changes

| Phase | Status / change |
|---|---|
| 0 | Closed (v17 chosen) |
| 1 | **Done** — skip |
| 2–3 | Create `EasyNav Settings` (single, System Manager only) and `EasyNav Item` (child, `istable`) — hand-author JSON (no `bench new-doctype` in this version); add `validate()` (0.3 #3) |
| 4 | API with type annotations; shared `build_navigation(user)`; server-resolved routes; per-user filtering; `extend_bootinfo` (0.2 #1, #5–7; 0.3 #1) |
| 5 | Hooks: `app_include_js`, `app_include_css`, `extend_bootinfo` |
| 6–8 | Idempotent mount; click-primary UI; `switch(type)` routing driven by server-resolved `route`; URL safety (0.3 #4–5) |
| 9 | `page-change` only closes the menu; no refetch (0.2 #3) |
| 10–11 | Permission filtering test + save-time validation |
| 12–13 | Per 0.3 #6–8 |
| 14 | Tests with `IntegrationTestCase`; unit-test `build_navigation`, URL validator, route resolver |
| 15 | Boot payload, no extra request on load |
| 16–17 | README; `bench build --app easynav`, `bench --site wahub.com migrate`, `bench restart` |

## 0.5 Open questions for the product owner

1. Should items the user cannot access be **hidden** (recommended, 0.2 #6) or shown and let Frappe return "Not Permitted"?
2. Should Workspaces be a navigation type? Not in the spec; a Workspace can currently be reached only as a `Page`-type target if its route slug is entered. Recommend deferring to V2.
3. Should `EasyNav Settings` ship with default items (e.g. empty + disabled) via `after_install`? Recommend: enabled, empty, so nothing renders until configured.
4. Per-user hide/relocate of the button is out of scope; confirm.

---

## 1. Project Overview

**App Name:** EasyNav  
**Package Name:** `easynav`

EasyNav is a custom Frappe application that provides a **globally available floating navigation button** across Frappe Desk pages.

The MVP allows administrators to configure navigation items through a **Quick Setup / Settings DocType** and lets users navigate quickly to:

- DocTypes
- Pages
- Reports
- External URLs

The implementation should be kept modular so that future features such as role-based navigation, favorites, search, nested menus, and keyboard shortcuts can be added without redesigning the core architecture.

---

# 2. MVP Architecture

```text
                         Frappe Desk
                              │
                              │ Global JS/CSS
                              ▼
                         EasyNav Frontend
                              │
                              │ API
                              ▼
                      EasyNav Settings
                              │
                              ▼
                       EasyNav Item Table
                              │
                ┌─────────────┼─────────────┐
                │             │             │
             DocType         Page         Report
                │
                └────────────── URL
```

Main components:

```text
EasyNav Settings
       │
       └── EasyNav Item
              ├── Label
              ├── Icon
              ├── Type
              ├── Target
              ├── Enabled
              ├── Open in New Tab
              └── Order

Global Frontend
       │
       ├── easynav.js
       └── easynav.css

Backend
       │
       └── navigation API
```

---

# 3. Implementation Phases

## Phase 0 — Project Planning and Technical Decisions

### Objective

Finalize the MVP architecture, Frappe version, naming, and technical approach before writing code.

### Tasks

- Confirm application name as `EasyNav`.
- Confirm package name as `easynav`.
- Decide the target Frappe version.
- Decide whether the MVP supports only Frappe Desk.
- Define supported navigation types:
  - DocType
  - Page
  - Report
  - URL
- Define the initial floating-button position.
- Define the initial UI behaviour:
  - Click
  - Hover
  - Expand/collapse
- Define the initial API response format.
- Define permission expectations.
- Define browser support.

### Decisions

Use:

```text
App Name:
EasyNav

Package:
easynav

Settings:
EasyNav Settings

Child Table:
EasyNav Item
```

### Deliverable

A short technical design document containing:

```text
Architecture
Data Model
API Contract
Frontend Behaviour
Navigation Rules
Security Rules
```

---

# Phase 1 — Create the Frappe Application

## Objective

Create a clean Frappe application skeleton.

### Tasks

Create the application:

```bash
bench new-app easynav
```

Install it on the development site:

```bash
bench --site <site-name> install-app easynav
```

Start the development environment:

```bash
bench start
```

### Verify

Check:

```bash
bench --site <site-name> list-apps
```

Expected:

```text
frappe
erpnext
easynav
```

### Basic application structure

```text
easynav/
├── easynav/
│   ├── hooks.py
│   ├── modules.txt
│   ├── api/
│   ├── easynav/
│   │   └── doctype/
│   └── public/
│       ├── js/
│       └── css/
├── pyproject.toml
└── README.md
```

### Deliverable

A working Frappe app that installs successfully.

---

# Phase 2 — Create EasyNav Settings

## Objective

Create the main configuration DocType.

Create:

```text
EasyNav Settings
```

This should be a **Single DocType**.

### Initial fields

```text
enabled
button_label
button_icon
position
items
```

Recommended field configuration:

| Field | Type | Purpose |
|---|---|---|
| Enabled | Check | Enable/disable EasyNav |
| Button Label | Data | Optional button label |
| Button Icon | Icon | Floating button icon |
| Position | Select | Button position |
| Navigation Items | Table | Navigation configuration |

### Position options

For MVP:

```text
Bottom Right
Bottom Left
Top Right
Top Left
```

Although the initial default should be:

```text
Bottom Right
```

### Deliverable

Administrator can open:

```text
EasyNav Settings
```

and save basic configuration.

---

# Phase 3 — Create EasyNav Item Child Table

## Objective

Create the navigation configuration table.

Create child table:

```text
EasyNav Item
```

### Fields

```text
enabled
label
icon
type
target
open_in_new_tab
order
```

### Field details

| Field | Type | Description |
|---|---|---|
| Enabled | Check | Enable/disable item |
| Label | Data | Text shown to user |
| Icon | Icon/Data | Navigation icon |
| Type | Select | DocType/Page/Report/URL |
| Target | Dynamic/Data | Navigation target |
| Open in New Tab | Check | Open target in another tab |
| Order | Int | Display order |

### Type options

```text
DocType
Page
Report
URL
```

### Example

```text
EasyNav Settings

Enabled: ✓
Button Label: EasyNav
Position: Bottom Right

Navigation Items:

1. Customers
   Type: DocType
   Target: Customer

2. Sales Invoice
   Type: DocType
   Target: Sales Invoice

3. Sales Dashboard
   Type: Page
   Target: sales-dashboard

4. Sales Analytics
   Type: Report
   Target: Sales Analytics

5. Company Website
   Type: URL
   Target: https://example.com
```

### Deliverable

Administrator can create, edit, reorder, enable, and disable navigation items.

---

# Phase 4 — Backend Navigation API

## Objective

Provide a controlled API for the frontend to retrieve the active EasyNav configuration.

Recommended API:

```text
easynav.api.navigation.get_navigation
```

### API responsibilities

The API should:

1. Load EasyNav Settings.
2. Check whether EasyNav is enabled.
3. Read navigation items.
4. Remove disabled items.
5. Sort items by order.
6. Return configuration in a frontend-friendly structure.

### Example response

```json
{
    "enabled": true,
    "position": "bottom-right",
    "button": {
        "label": "EasyNav",
        "icon": "menu"
    },
    "items": [
        {
            "label": "Customers",
            "icon": "users",
            "type": "DocType",
            "target": "Customer",
            "open_in_new_tab": false
        },
        {
            "label": "Sales Invoice",
            "icon": "file-text",
            "type": "DocType",
            "target": "Sales Invoice",
            "open_in_new_tab": false
        },
        {
            "label": "Sales Dashboard",
            "icon": "bar-chart",
            "type": "Page",
            "target": "sales-dashboard",
            "open_in_new_tab": false
        }
    ]
}
```

### API security

Use Frappe's authentication/session mechanism.

The API should not expose configuration unnecessarily to unauthenticated users.

### Deliverable

A working API returning valid EasyNav configuration.

---

# Phase 5 — Global Asset Integration

## Objective

Load EasyNav JavaScript and CSS globally throughout Frappe Desk.

Update:

```text
hooks.py
```

with:

```python
app_include_js = [
    "/assets/easynav/js/easynav.js"
]

app_include_css = [
    "/assets/easynav/css/easynav.css"
]
```

### Tasks

Create:

```text
easynav/public/js/easynav.js
easynav/public/css/easynav.css
```

### Verify

Open multiple Frappe pages:

```text
/app
/app/customer
/app/sales-invoice
/app/report
```

Verify the EasyNav assets are loaded globally.

### Deliverable

EasyNav frontend assets are available on all Frappe Desk pages.

---

# Phase 6 — Build the Floating Navigation Button

## Objective

Create the primary EasyNav UI.

### Initial UI

```text
┌───────────────────────────────┐
│                               │
│        Frappe Desk            │
│                               │
│                               │
│                         ┌───┐ │
│                         │ ☰ │ │
│                         └───┘ │
└───────────────────────────────┘
```

### Requirements

The button should:

- Be fixed to the viewport.
- Remain visible during scrolling.
- Not affect page layout.
- Work across Desk pages.
- Use a configurable icon.
- Use the configured position.
- Have a high enough z-index.
- Avoid blocking normal Frappe controls.

### CSS considerations

Use:

```css
position: fixed;
z-index: appropriate-value;
```

Do not hard-code excessive z-index values without testing against Frappe dialogs, dropdowns, and modals.

### Deliverable

A floating EasyNav button visible on Frappe Desk.

---

# Phase 7 — Build Navigation Menu

## Objective

Display configured navigation items when the user interacts with the EasyNav button.

### Initial behaviour

Click:

```text
                    ┌──────────────┐
                    │ 📊 Dashboard │
                    │ 👥 Customer  │
                    │ 🧾 Invoice   │
                    │ 📦 Stock     │
                    └──────────────┘
                           │
                        ┌─────┐
                        │ ☰   │
                        └─────┘
```

### Hover behaviour

Support hover on desktop:

```text
                 Dashboard ───────┐
                 Customer ────────┤
                 Invoice ─────────┤
                 Stock ───────────┤
                                  │
                               ┌──────┐
                               │  ☰   │
                               └──────┘
```

### Important UX rule

Click should remain the primary interaction.

Hover should be an enhancement rather than the only way to access navigation.

### Menu requirements

- Show only enabled items.
- Preserve configured order.
- Display icon.
- Display label.
- Highlight hovered item.
- Close when appropriate.
- Avoid blocking important page controls.
- Support keyboard focus where practical.

### Deliverable

A functional floating navigation menu.

---

# Phase 8 — Implement Navigation Routing

## Objective

Make each navigation type work correctly.

---

## 8.1 DocType Navigation

Example:

```text
Type: DocType
Target: Customer
```

Use Frappe routing rather than manually constructing unsafe URLs.

Expected destination:

```text
/app/customer
```

or the equivalent Frappe route.

---

## 8.2 Page Navigation

Example:

```text
Type: Page
Target: sales-dashboard
```

Expected route:

```text
/app/sales-dashboard
```

Use Frappe's routing mechanism.

---

## 8.3 Report Navigation

Example:

```text
Type: Report
Target: Sales Analytics
```

Navigate to the configured report using the appropriate Frappe route.

---

## 8.4 URL Navigation

Example:

```text
Type: URL
Target: https://example.com
```

If:

```text
Open in New Tab = ✓
```

open the URL in a new browser tab.

Otherwise navigate in the current tab.

### URL validation

Validate external URLs before using them.

At minimum, consider:

```text
https://
http://
```

and reject unsafe schemes such as:

```text
javascript:
data:
```

### Deliverable

All four MVP navigation types work.

---

# Phase 9 — Handle Frappe SPA Route Changes

## Objective

Make sure EasyNav continues to work when Frappe changes pages without a full browser reload.

Frappe Desk behaves as a single-page application.

Therefore, test:

```text
Customer
   ↓
Sales Invoice
   ↓
Stock Entry
   ↓
Report
   ↓
Dashboard
```

The EasyNav component should remain functional throughout.

### Tasks

- Detect Frappe route changes.
- Prevent duplicate EasyNav components.
- Refresh configuration only when necessary.
- Ensure event listeners are not registered repeatedly.
- Ensure the component survives Desk page transitions.

### Example concept

```javascript
$(document).on("page-change", function () {
    easynav.refresh();
});
```

The exact event should be verified against the target Frappe version.

### Deliverable

EasyNav works correctly through SPA navigation.

---

# Phase 10 — Permission and Security Validation

## Objective

Ensure EasyNav does not bypass Frappe permissions.

### Principle

EasyNav is a navigation utility, not a permission system.

If a user does not have access to a DocType or report, EasyNav must not provide a way to bypass Frappe's normal authorization.

### Tests

Create users with different permissions:

```text
User A
- Customer access

User B
- Customer access
- Sales Invoice access

User C
- Limited access
```

Test navigation.

### Requirements

- Frappe permissions remain authoritative.
- EasyNav must not expose protected data.
- EasyNav must not use unsafe server-side permission bypasses.
- URL navigation must be validated.
- API should require normal authenticated access.

### Deliverable

A basic security test report.

---

# Phase 11 — Configuration Validation

## Objective

Prevent bad navigation configuration from breaking the UI.

### Validate

For every navigation item:

```text
Label
Icon
Type
Target
Enabled
Order
```

### Examples

Invalid:

```text
Label: empty
Type: DocType
Target: empty
```

Invalid:

```text
Type: URL
Target: javascript:...
```

Invalid:

```text
Type: Page
Target: empty
```

### Recommended behaviour

If an item is invalid:

```text
Do not render the invalid item.
```

Optionally log a useful error for administrators/developers.

### Deliverable

EasyNav continues working even when one navigation item is incorrectly configured.

---

# Phase 12 — UI/UX Refinement

## Objective

Make the MVP visually polished without adding unnecessary functionality.

### Tasks

- Improve button size.
- Improve icon alignment.
- Improve menu spacing.
- Add subtle animation.
- Add hover state.
- Add active/focus state.
- Improve typography.
- Improve mobile/touch behaviour.
- Ensure the menu does not overflow the viewport.

### Suggested animation

Use:

```text
opacity
scale
translate
```

Example concept:

```text
Closed
  ↓
opacity: 0
scale: 0.95

Open
  ↓
opacity: 1
scale: 1
```

Avoid large or distracting animations.

### Deliverable

A clean production-ready MVP UI.

---

# Phase 13 — Responsive Behaviour

## Objective

Ensure EasyNav works across different screen sizes.

### Desktop

```text
Floating button
       ↓
Expandable navigation
```

### Tablet

Use a compact layout.

### Mobile

Although the MVP is primarily for Frappe Desk, ensure the UI does not break if a smaller viewport is used.

The interaction should be:

```text
Tap
 ↓
Open menu
 ↓
Select item
```

Do not rely exclusively on hover.

### Deliverable

Responsive EasyNav UI.

---

# Phase 14 — Testing

## Objective

Perform functional and regression testing.

## Test Matrix

### Global visibility

Test:

```text
Desk Home
List View
Form View
Report
Dashboard
Workspace
Settings
```

Expected:

```text
EasyNav available globally.
```

---

## Configuration tests

Test:

```text
EasyNav disabled
EasyNav enabled
Item disabled
Item enabled
Different order
Empty item list
Invalid item
```

---

## Navigation tests

Test:

```text
DocType
Page
Report
URL
```

---

## Tab tests

Test:

```text
Open in New Tab = false
Open in New Tab = true
```

---

## Route tests

Test:

```text
Full browser refresh
Desk route change
List → Form
Form → List
Report → Form
Dashboard → List
```

---

## Permission tests

Test:

```text
Administrator
System Manager
Normal User
Restricted User
```

---

## UI tests

Test:

```text
Click
Hover
Outside click
Scrolling
Dialog open
Dropdown open
Mobile/touch
Small screen
Large screen
```

### Deliverable

MVP test checklist completed.

---

# Phase 15 — Performance Optimization

## Objective

Make EasyNav lightweight because it loads globally.

### Requirements

Avoid:

- Large frontend libraries.
- Heavy dependencies.
- Repeated API requests.
- Repeated DOM creation.
- Multiple global event handlers.

### Recommended approach

Load configuration once:

```text
Page Load
   ↓
Get EasyNav Configuration
   ↓
Cache in frontend
   ↓
Render
```

Refresh configuration only when necessary.

### Example

```text
Frappe Desk
     │
     ▼
EasyNav JS
     │
     ▼
API call
     │
     ▼
Configuration
     │
     ▼
Frontend cache
     │
     ▼
Render navigation
```

### Deliverable

EasyNav has minimal impact on Frappe Desk performance.

---

# Phase 16 — Developer Documentation

## Objective

Document the app so another developer can maintain it.

Create:

```text
README.md
```

Include:

```text
Project Overview
Installation
Configuration
Architecture
DocTypes
API
Frontend
Navigation Types
Security
Development
Testing
Deployment
```

### Example installation

```bash
bench get-app <repository-url>
bench --site <site-name> install-app easynav
bench build --app easynav
bench restart
```

The exact deployment commands should be adapted to the deployment environment.

### Deliverable

Complete developer documentation.

---

# Phase 17 — Production Build and Deployment

## Objective

Deploy the MVP to a production Frappe environment.

### Pre-deployment checklist

```text
[ ] App installs successfully
[ ] DocTypes migrate correctly
[ ] Assets build successfully
[ ] JS has no console errors
[ ] CSS has no conflicts
[ ] API works
[ ] Navigation works
[ ] Permissions work
[ ] External URL validation works
[ ] SPA route changes work
[ ] Production build tested
```

### Build

```bash
bench build --app easynav
```

### Migration

```bash
bench --site <site-name> migrate
```

### Restart

Use the appropriate process manager/deployment method for the Frappe installation.

### Deliverable

EasyNav running in a production Frappe environment.

---

# 18. Recommended Implementation Order

The actual development order should be:

```text
Phase 0
Planning
   │
   ▼
Phase 1
Create Frappe App
   │
   ▼
Phase 2
EasyNav Settings
   │
   ▼
Phase 3
EasyNav Item
   │
   ▼
Phase 4
Backend API
   │
   ▼
Phase 5
Global JS/CSS
   │
   ▼
Phase 6
Floating Button
   │
   ▼
Phase 7
Navigation Menu
   │
   ▼
Phase 8
Navigation Routing
   │
   ▼
Phase 9
SPA Route Handling
   │
   ▼
Phase 10
Permissions/Security
   │
   ▼
Phase 11
Validation
   │
   ▼
Phase 12
UI Refinement
   │
   ▼
Phase 13
Responsive UI
   │
   ▼
Phase 14
Testing
   │
   ▼
Phase 15
Performance
   │
   ▼
Phase 16
Documentation
   │
   ▼
Phase 17
Production Deployment
```

---

# 19. Suggested Git Branch Strategy

For a small EasyNav project:

```text
main
 │
 └── develop
      │
      ├── feature/settings
      ├── feature/navigation-api
      ├── feature/global-ui
      ├── feature/routing
      ├── feature/security
      └── feature/testing
```

Recommended workflow:

```text
feature/*
    ↓
develop
    ↓
Testing
    ↓
main
```

Keep each feature focused.

---

# 20. Suggested Commit Structure

Use clear commits such as:

```text
feat: initialize easynav app

feat: add EasyNav Settings doctype

feat: add EasyNav Item child table

feat: add navigation configuration API

feat: add global EasyNav assets

feat: add floating navigation button

feat: add navigation menu

feat: add DocType navigation

feat: add page navigation

feat: add report navigation

feat: add URL navigation

feat: handle Desk route changes

fix: prevent duplicate navigation instances

fix: validate external URLs

feat: add responsive navigation UI

test: add EasyNav navigation tests

docs: add EasyNav documentation
```

---

# 21. MVP Definition of Done

The EasyNav MVP is complete when all of the following are true:

```text
[ ] EasyNav installs as a normal Frappe app.

[ ] EasyNav Settings exists as a Single DocType.

[ ] EasyNav Item exists as a child table.

[ ] Administrator can enable/disable EasyNav.

[ ] Administrator can configure the button.

[ ] Administrator can configure navigation items.

[ ] Navigation items can be ordered.

[ ] Navigation items can be enabled/disabled.

[ ] DocType navigation works.

[ ] Page navigation works.

[ ] Report navigation works.

[ ] External URL navigation works.

[ ] Open-in-new-tab works.

[ ] EasyNav is visible globally across Desk.

[ ] EasyNav survives Frappe SPA route changes.

[ ] EasyNav does not create duplicate UI instances.

[ ] Frappe permissions remain enforced.

[ ] Unsafe URL schemes are rejected.

[ ] Invalid configuration does not break the menu.

[ ] UI works on desktop.

[ ] UI is usable on smaller screens.

[ ] No major JavaScript console errors.

[ ] No major CSS conflicts with Frappe.

[ ] Global performance impact is minimal.

[ ] Developer documentation is complete.

[ ] Production deployment is tested.
```

---

# 22. Future Roadmap After MVP

Do not implement these in the MVP, but design the architecture so they can be added later.

## V2

```text
Role-based navigation
User-specific navigation
Navigation groups
Nested menus
Search navigation
Favorites
Recent pages
Keyboard shortcuts
```

## V3

```text
Drag-and-drop navigation builder
Conditional navigation
Workspace-specific navigation
User preferences
Navigation analytics
Usage statistics
Import/export configuration
```

## V4

```text
Navigation marketplace
Custom navigation widgets
Dynamic navigation
Context-aware navigation
Mobile navigation
Command palette
Global Frappe search integration
```

---

# 23. Final MVP Architecture

The final MVP should remain intentionally simple:

```text
                     ┌─────────────────────┐
                     │   EasyNav Settings  │
                     │      Single DocType │
                     └──────────┬──────────┘
                                │
                                │
                     ┌──────────▼──────────┐
                     │    EasyNav Item     │
                     │     Child Table     │
                     ├─────────────────────┤
                     │ Label               │
                     │ Icon                │
                     │ Type                │
                     │ Target              │
                     │ Enabled             │
                     │ New Tab             │
                     │ Order               │
                     └──────────┬──────────┘
                                │
                                ▼
                     ┌─────────────────────┐
                     │ Navigation API      │
                     │ get_navigation()    │
                     └──────────┬──────────┘
                                │
                                ▼
                     ┌─────────────────────┐
                     │   easynav.js        │
                     │   easynav.css       │
                     └──────────┬──────────┘
                                │
                                ▼
                     ┌─────────────────────┐
                     │ Global Floating UI  │
                     └──────────┬──────────┘
                                │
                  ┌─────────────┼─────────────┐
                  │             │             │
                  ▼             ▼             ▼
               DocType        Page         Report
                  │
                  └───────────────┬───────────────┐
                                  │               │
                                  ▼               ▼
                                URL        External Website
```

---

# 24. Final Product Goal

The first version of **EasyNav** should solve one problem extremely well:

> **Give Frappe users a simple, configurable, globally available navigation button for quickly accessing important pages, DocTypes, reports, and URLs.**

The implementation should prioritize:

1. Simplicity
2. Reliability
3. Frappe compatibility
4. Minimal performance impact
5. Permission safety
6. Clean architecture
7. Easy future extension

The MVP should **not** try to become a complete navigation framework immediately. Build the global navigation foundation first, then expand it based on actual user requirements.
