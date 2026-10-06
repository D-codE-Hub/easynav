# EasyNav

EasyNav is a custom Frappe app that adds one **global floating navigation button** to every Desk page. Administrators configure the menu in a Setup DocType, so no code changes are needed to change the navigation.

![EasyNav menu open on the Desk home](docs/images/menu-open.jpg)

- Quick access to **DocTypes, Pages, Reports and external URLs**
- Configured in **EasyNav Settings** (enable/disable, position, items, order, open in new tab)
- **Respects Frappe permissions**: users only see items they are allowed to open

## Using the menu

The floating button appears on every Desk page for logged-in users.

| Action | Result |
|---|---|
| Click the button | Opens the menu and keeps it open |
| Click the button again, click outside, or press `Esc` | Closes the menu |
| Hover the button (mouse only) | Opens the menu; it closes when the pointer leaves |
| `ArrowDown` / `ArrowUp` | Moves through the menu items |
| Click an item | Opens it, in the same tab or a new tab as configured |
| Ctrl/Cmd-click or middle-click an item | Opens it in a new browser tab |

The menu closes automatically when you move to another Desk page. The button is not shown on printed pages, and it sits behind open dialogs.

The button is hidden when:

- EasyNav is disabled in the settings,
- no navigation items are configured, or
- the user is not permitted to open any of the configured items.

## Configuration

Open **EasyNav Settings** (`/desk/easynav-settings`, System Manager only).

![EasyNav Settings](docs/images/settings.jpg)

| Field | Purpose |
|---|---|
| Enable EasyNav | Turns the button on or off for everyone |
| Button Label | Tooltip / accessible name of the button (defaults to `EasyNav`) |
| Button Icon | Icon of the floating button (defaults to `menu`) |
| Position | Bottom Right (default), Bottom Left, Top Right, Top Left |
| Navigation Items | The menu entries (below) |

Saved changes show up immediately for the person who saved them. Other users see them the next time they load Desk.

### Navigation items

| Field | Notes |
|---|---|
| Enabled | Disabled rows are never shown and are not validated, so you can keep drafts |
| Label | Text shown in the menu |
| Icon | Optional icon name (letters, digits, `_`, `-`). Falls back to a default per type |
| Type | `DocType`, `Page`, `Report` or `URL` |
| Target | DocType name, Page name, Report name, or URL |
| Open in New Tab | Opens in a new browser tab |
| Order | Lower first. Items with no order (blank or `0`) follow in row order |

Where each type takes the user:

| Type | Opens |
|---|---|
| DocType | The list view, or the form for Single DocTypes |
| Page | The Desk page |
| Report | The report view (Query/Script reports and Report Builder reports) |
| URL | The URL, either an external site or a path on this site |

### Validation

Settings are checked on save, and the row with the problem is named in the error:

- Enabled rows need a label and a target.
- DocType, Page and Report targets must exist. Child-table DocTypes are rejected.
- URLs must be `http(s)://...` or a path starting with a single `/`.
- Icon names must be a plain name; Order cannot be negative.

If a target is deleted or renamed after the settings were saved, that item is left out of the menu and the rest keep working.

## Permissions

EasyNav is not a permission system. It only hides menu items the current user cannot open, and Frappe still enforces access at the destination.

| Type | Shown to a user when |
|---|---|
| DocType | They have read permission on the DocType |
| Page | Their roles are allowed to open the Page |
| Report | Their roles are allowed to open the Report and they have report permission on its DocType |
| URL | Always |

- Only System Managers can view or change EasyNav Settings.
- Guests never see the button.
- Links using `javascript:`, `data:` and similar schemes are blocked.

## License

mit
