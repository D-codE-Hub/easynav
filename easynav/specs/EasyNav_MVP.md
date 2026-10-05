# EasyNav — MVP Specification for Frappe

## 1. App Overview

**App Name:** EasyNav  
**Package Name:** `easynav`

EasyNav is a custom Frappe application that provides a **global floating navigation button** across all Frappe Desk pages.

The main goal of the MVP is to provide users with quick access to configured:

- DocTypes
- Pages
- Reports
- External URLs

Navigation items are configured through a Frappe **Setup DocType**, so administrators can change the navigation without modifying code.

---

# 2. Core Concept

The app adds a single floating navigation icon globally across the Frappe Desk.

Example:

```text
                         ┌─────────────────────┐
                         │ 🔹 EasyNav           │
                         ├─────────────────────┤
                         │ 📊 Sales Dashboard   │
                         │ 👥 Customers         │
                         │ 🧾 Sales Invoice      │
                         │ 📦 Stock              │
                         │ 📈 Sales Report       │
                         └─────────────────────┘
                                  ↑
                           Mouse over / click
```

The administrator configures these navigation items through a **Setup DocType**.

---

# 3. MVP Features

## A. Global Navigation Button

Add one floating button that appears on **all Desk pages**.

Example:

```text
┌───────────────────────────────┐
│                               │
│        ERPNext Page           │
│                               │
│                               │
│                         ┌───┐ │
│                         │ ☰ │ │
│                         └───┘ │
└───────────────────────────────┘
```

The button should:

- Be globally available
- Stay fixed on the screen
- Work across all Desk pages
- Have configurable position later
- Open the navigation menu on hover/click
- Not interfere with the standard Frappe UI

For the MVP, use **click + hover support**, but make click the primary interaction because hover-only navigation can be awkward on touch devices.

---

# 4. Navigation Setup DocType

Create:

```text
EasyNav Settings
```

This is a **Single DocType**.

## Fields

```text
EasyNav Settings
────────────────────────────────

Enable EasyNav       [✓]

Button Label         [EasyNav]

Button Icon          [menu]

Position             [Bottom Right ▼]

────────────────────────────────
Navigation Items
────────────────────────────────
```

The navigation items are stored in a child table:

```text
EasyNav Item
```

---

# 5. EasyNav Item

The child table contains the actual navigation buttons.

## Fields

| Field | Type |
|---|---|
| Enabled | Check |
| Label | Data |
| Icon | Data |
| Type | Select |
| Target | Dynamic |
| Open in New Tab | Check |
| Order | Int |

## Type

Initially support only:

```text
DocType
Page
Report
URL
```

Example configuration:

```text
Navigation Items

┌───────┬──────────────────┬─────────┬────────────────────┐
│ Order │ Label            │ Type    │ Target             │
├───────┼──────────────────┼─────────┼────────────────────┤
│ 1     │ Customers        │ DocType │ Customer           │
│ 2     │ Sales Invoice    │ DocType │ Sales Invoice      │
│ 3     │ Sales Dashboard  │ Page    │ sales-dashboard    │
│ 4     │ Sales Analytics  │ Report  │ Sales Analytics    │
│ 5     │ Company Website  │ URL     │ https://...        │
└───────┴──────────────────┴─────────┴────────────────────┘
```

---

# 6. Navigation Types

For the MVP, support exactly these four types.

## 6.1 DocType

```text
Type: DocType
Target: Customer
```

Click should navigate to the corresponding Frappe DocType route.

---

## 6.2 Page

```text
Type: Page
Target: sales-dashboard
```

Navigate to:

```text
/app/sales-dashboard
```

---

## 6.3 Report

```text
Type: Report
Target: Sales Analytics
```

Navigate to the configured report.

Later, if required, add:

```text
Report Type
Reference DocType
```

---

## 6.4 URL

```text
Type: URL
Target: https://example.com
```

This allows external links.

---

# 7. UI Behaviour

The MVP UI can look like a floating action menu.

```text
                         ┌───────────────┐
                         │ 📊 Dashboard  │
                         │ 👤 Customers  │
                         │ 🧾 Invoices   │
                         │ 📦 Stock      │
                         │ 📈 Reports    │
                         └───────────────┘
                                │
                                ▼
                              ┌───┐
                              │ + │
                              └───┘
```

When the user clicks the button:

```text
                         ┌─────────────────────┐
                         │ 📊 Dashboard        │
                         │ 👤 Customers        │
                         │ 🧾 Sales Invoice    │
                         │ 📦 Stock            │
                         │ 📈 Sales Report     │
                         └─────────────────────┘
                                      │
                                      ▼
                                    ┌───┐
                                    │ + │
                                    └───┘
```

Each item should contain:

```text
Icon + Label
```

Examples:

```text
📊 Dashboard
👥 Customer
🧾 Sales Invoice
📦 Stock Entry
📈 Sales Analytics
```

---

# 8. Frappe Architecture

Keep the architecture simple for the MVP.

```text
easynav/
│
├── easynav/
│   ├── hooks.py
│   │
│   ├── easynav/
│   │   └── doctype/
│   │       │
│   │       ├── easynav_settings/
│   │       │   ├── easynav_settings.json
│   │       │   ├── easynav_settings.py
│   │       │   └── easynav_settings.js
│   │       │
│   │       └── easynav_item/
│   │           └── easynav_item.json
│   │
│   ├── api/
│   │   └── navigation.py
│   │
│   └── public/
│       ├── js/
│       │   └── easynav.js
│       │
│       └── css/
│           └── easynav.css
│
└── hooks.py
```

A separate `EasyNav Item` DocType is **not required** if it is implemented as a child table.

Recommended relationship:

```text
EasyNav Settings
       │
       └── EasyNav Item
             ├── Label
             ├── Icon
             ├── Type
             ├── Target
             ├── Enabled
             └── Order
```

---

# 9. Global JS

The most important part of the MVP is loading the JavaScript globally.

In `hooks.py`:

```python
app_include_js = [
    "/assets/easynav/js/easynav.js"
]

app_include_css = [
    "/assets/easynav/css/easynav.css"
]
```

Then initialize the navigation component:

```javascript
frappe.ready(() => {
    easynav.init();
});
```

Because Frappe Desk is a SPA, also account for route changes.

For example:

```javascript
$(document).on("page-change", function () {
    easynav.refresh();
});
```

The exact event handling should be tested against the Frappe version being targeted.

---

# 10. Do Not Store Navigation Configuration in JavaScript

Do not hard-code navigation configuration like:

```javascript
const navigation = [
    {
        label: "Customer",
        route: "/app/customer"
    }
];
```

Instead use a data-driven approach:

```text
EasyNav Settings
        ↓
Frappe API
        ↓
Navigation JSON
        ↓
easynav.js
        ↓
Navigation UI
```

This allows administrators to change navigation without modifying code.

---

# 11. API

Create an API such as:

```text
easynav.api.navigation.get_navigation
```

Example response:

```json
{
    "enabled": true,
    "position": "bottom-right",
    "items": [
        {
            "label": "Customers",
            "icon": "users",
            "type": "DocType",
            "target": "Customer"
        },
        {
            "label": "Sales Invoice",
            "icon": "file-text",
            "type": "DocType",
            "target": "Sales Invoice"
        },
        {
            "label": "Sales Dashboard",
            "icon": "bar-chart",
            "type": "Page",
            "target": "sales-dashboard"
        }
    ]
}
```

The frontend should only need this data to render the navigation.

---

# 12. Permissions

For the MVP, do **not** build a complicated permission system.

Frappe already has permissions.

For example, if EasyNav contains:

```text
Customer
```

but the current user does not have permission to access Customer, Frappe should still enforce its normal permission rules.

However, a future version can add:

```text
Visible For Roles
```

For example:

```text
Navigation Item

Customers

Roles:
☑ Sales User
☑ Sales Manager
☐ Purchase User
☐ Stock User
```

This should be a **V2 feature**, not part of the initial MVP.

---

# 13. Important MVP Security Rule

Do not blindly allow arbitrary URLs or arbitrary routes from user input.

Avoid logic such as:

```javascript
window.location = item.target;
```

for every navigation type.

Instead use explicit handling:

```javascript
switch (item.type) {

    case "DocType":
        // Frappe route
        break;

    case "Page":
        // Frappe route
        break;

    case "Report":
        // Frappe route
        break;

    case "URL":
        // validated URL
        break;
}
```

This keeps navigation behaviour predictable and safer.

---

# 14. MVP Database Design

Only two logical DocTypes are needed.

## Single DocType

```text
EasyNav Settings
```

Fields:

```text
enabled
button_icon
button_label
position
items
```

## Child Table

```text
EasyNav Item
```

Fields:

```text
label
icon
type
target
enabled
open_in_new_tab
order
```

---

# 15. Suggested MVP UI

Use a floating action menu similar to:

```text
                              ┌──────────────┐
                              │ 📊 Dashboard │
                              ├──────────────┤
                              │ 👥 Customer  │
                              ├──────────────┤
                              │ 🧾 Invoice   │
                              ├──────────────┤
                              │ 📦 Stock     │
                              └──────────────┘
                                      │
                                   ┌─────┐
                                   │ ☰   │
                                   └─────┘
```

When the mouse moves over the button:

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

Use a small animation:

```text
scale
opacity
translate
```

rather than a large popup/modal.

---

# 16. MVP Scope

## Include

- [x] Global floating navigation button
- [x] Works on all Desk pages
- [x] EasyNav Settings
- [x] Navigation child table
- [x] Enable/disable EasyNav
- [x] Enable/disable individual items
- [x] Label
- [x] Icon
- [x] Ordering
- [x] DocType navigation
- [x] Page navigation
- [x] Report navigation
- [x] External URL
- [x] Open in new tab
- [x] Basic responsive UI
- [x] Frappe permission enforcement
- [x] Route-independent global component

## Do Not Include Initially

- [ ] Role-based navigation
- [ ] User-specific navigation
- [ ] Multiple navigation groups
- [ ] Drag-and-drop builder
- [ ] Nested menus
- [ ] Analytics
- [ ] Navigation usage statistics
- [ ] Keyboard shortcuts
- [ ] Favorites
- [ ] Recent pages
- [ ] Mobile-specific navigation
- [ ] Marketplace/integration features

These can be added in **V2/V3**.

---

# 17. Future Architecture

If EasyNav eventually becomes a full Frappe navigation utility, it can evolve like this:

```text
                         EasyNav
                            │
              ┌─────────────┴─────────────┐
              │                           │
        Navigation Config            User Context
              │                           │
       ┌──────┼──────┐             ┌──────┼──────┐
       │      │      │             │      │      │
     Page   DocType Report        Role   User   Permission
       │      │      │
       └──────┼──────┘
              │
        Navigation UI
              │
       ┌──────┼─────────┐
       │      │         │
    Floating  Search   Keyboard
      Menu             Shortcut
```

The key architectural decision is to make **navigation configuration data-driven** from the beginning. This will allow roles, groups, favorites, search, shortcuts, and other features to be added later without redesigning the core app.

---

# 18. Final Naming

Use the following naming consistently throughout the project:

```text
App Name:       EasyNav
Package Name:   easynav

Settings DocType:
EasyNav Settings

Child Table:
EasyNav Item

Main JavaScript:
easynav.js

Main CSS:
easynav.css

API:
easynav.api.navigation.get_navigation
```

---

# 19. Recommended MVP User Flow

```text
Administrator
      │
      ▼
Open EasyNav Settings
      │
      ▼
Enable EasyNav
      │
      ▼
Add Navigation Items
      │
      ├── Customer → DocType
      ├── Sales Invoice → DocType
      ├── Sales Dashboard → Page
      ├── Sales Analytics → Report
      └── Company Website → URL
      │
      ▼
Save
      │
      ▼
EasyNav loads configuration
      │
      ▼
Floating button appears globally
      │
      ▼
User clicks / hovers
      │
      ▼
Navigation items appear
      │
      ▼
User selects item
      │
      ▼
Frappe navigates to target
```

---

# 20. MVP Goal

The first release of **EasyNav** should solve one problem extremely well:

> **Give Frappe users a simple, configurable, globally available navigation button for quickly accessing important pages, DocTypes, reports, and URLs.**

Keep the first release small, stable, and data-driven. Once this foundation is working reliably across Frappe Desk, additional functionality can be introduced incrementally.
