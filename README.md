# EasyNav

EasyNav is a custom Frappe app that adds one **global floating navigation button** to every Desk page. Every user builds their own menu of shortcuts from the button itself, so no code changes or administrator help are needed.

![EasyNav menu open on the Desk home](docs/images/menu-open.jpg)

- Quick access to **DocTypes, Pages, Reports, Dashboards and external URLs**
- **Personal**: each user adds, edits and orders their own shortcuts, and nobody else sees them
- Site-wide options (enable/disable, button label, icon, position) are set in **EasyNav Settings**
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
| Right-click the button (press and hold on touch screens) | Opens your own list of shortcuts |
| Ctrl/Cmd-click or middle-click an item | Opens it in a new browser tab |

The menu closes automatically when you move to another Desk page. The button is not shown on printed pages, and it sits behind open dialogs.

The button is hidden only when EasyNav is disabled in the settings. A user with no shortcuts still sees it: the menu then says **No shortcuts yet** and explains how to add some.

## Your shortcuts

Right-click the floating button, or press and hold it on a touch screen. There is no separate edit button; the floating button's tooltip is the reminder. This opens **My Shortcuts**, your own list. Add rows to the table and save; the menu updates straight away.

- The list belongs to you. Other users cannot see or change it, and you cannot see theirs.
- You can keep up to **30** items.
- The fields of each row are described under [Navigation items](#navigation-items).

## Site-wide settings

Open **EasyNav Settings** (`/desk/easynav-settings`, System Manager only).

![EasyNav Settings](docs/images/settings.jpg)

| Field | Purpose |
|---|---|
| Enable EasyNav | Turns the button on or off for everyone |
| Button Label | Tooltip / accessible name of the button (defaults to `EasyNav`) |
| Button Icon | Icon of the floating button (defaults to `menu`) |
| Position | Bottom Right (default), Bottom Left, Top Right, Top Left |

These options apply to everyone. Saved changes show up immediately for the person who saved them. Other users see them the next time they load Desk.

System Managers can also open **EasyNav User Navigation** (`/desk/easynav-user-navigation`) to view or fix any user's existing list. A list is created the first time its user opens the editor, so there is nothing to fix before that.

## Navigation items

| Field | Notes |
|---|---|
| Enabled | Disabled rows are never shown and may be left incomplete, so you can keep drafts |
| Label | Text shown in the menu |
| Icon | Optional icon name (letters, digits, `_`, `-`). Falls back to a default per type |
| Type | `DocType`, `Page`, `Report`, `Dashboard` or `URL` |
| Link To | Shown for `DocType`, `Page`, `Report` and `Dashboard`: pick the record of that type to open. Only records you are allowed to open are suggested |
| DocType View | Shown for `DocType` only: `List`, `Report Builder`, `Dashboard`, `Tree`, `New`, `Calendar`, `Kanban` or `Image`. Blank opens the default view |
| Kanban Board | Shown when DocType View is `Kanban`: optional board to open |
| URL | Shown for `URL` only: the address to open |
| Open in New Tab | Opens in a new browser tab |
| Order | Lower first. Items with no order (blank or `0`) follow in row order |

Where each type takes the user:

| Type | Opens |
|---|---|
| DocType | The chosen DocType View (the list view when blank), or the form for Single DocTypes |
| Page | The Desk page |
| Report | The report view (Query/Script reports and Report Builder reports) |
| Dashboard | The dashboard view |
| URL | The URL, either an external site or a path on this site |

### Validation

A list is checked on save, and the row with the problem is named in the error:

- Enabled rows need a label, plus a Link To (or a URL for `URL` rows).
- The DocType, Page, Report or Dashboard in Link To must exist. Child-table DocTypes are rejected.
- The Tree view needs a tree DocType, and a Kanban Board must belong to the selected DocType.
- URLs must be `http(s)://...` or a path starting with a single `/`.
- Icon names must be a plain name; Order cannot be negative.
- A list can hold at most 30 items.

If a target is deleted or renamed after the list was saved, that item is left out of the menu and the rest keep working.

## Permissions

EasyNav is not a permission system. It only hides menu items the current user cannot open, and Frappe still enforces access at the destination.

| Type | Shown to a user when |
|---|---|
| DocType | They have read permission on the DocType (create permission for the `New` view, report permission for `Report Builder`) |
| Page | Their roles are allowed to open the Page |
| Report | Their roles are allowed to open the Report and they have report permission on its DocType |
| Dashboard | They have read permission on the Dashboard |
| URL | Always |

- Only System Managers can view or change EasyNav Settings.
- A user can only read and change their own shortcuts. System Managers can view, change and delete any user's list, and those edits are recorded in the document history.
- If someone else adds an item to your list that you are not allowed to open, it is not shown to you.
- Guests never see the button.
- Links using `javascript:`, `data:` and similar schemes are blocked.

## Upgrading from the shared menu

Earlier versions had one menu for everyone, configured in EasyNav Settings. That shared list is **not carried over**: `bench migrate` deletes it, and every user starts with an empty menu. Note down the old items before upgrading if users will want to re-create them.

## License

mit
